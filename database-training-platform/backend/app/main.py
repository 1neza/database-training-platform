import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from .catalog import SCENARIOS, TRACKS
from .config import settings
from .db import Base, engine, get_db
from .lab import teardown_lab
from .models import SessionStatus, TrainingSession
from .scenario_engine import evaluate_scenario, provision_scenario, validate_scenario_catalog
from .schemas import EvaluationOut, ScenarioOut, SessionOut, StartSessionIn, TrackOut


app = FastAPI(
    title="Database Training Platform",
    version="0.3.0",
    description="Operate real databases under timed production scenarios.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    validate_scenario_catalog()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def _new_attempt_envelope(
    *,
    scenario_version: str,
    attempt_number: int,
    session_id: uuid.UUID,
    replay_of_session_id: uuid.UUID | None = None,
    root_session_id: uuid.UUID | None = None,
) -> dict:
    return {
        "meta": {
            "scenario_version": scenario_version,
            "attempt_number": attempt_number,
            "replay_of_session_id": str(replay_of_session_id) if replay_of_session_id else None,
            "root_session_id": str(root_session_id or session_id),
            "lab_active": True,
            "ended_early": False,
        },
        "evaluation": None,
    }


def _attempt_meta(row: TrainingSession) -> dict:
    envelope = row.result if isinstance(row.result, dict) else {}
    meta = envelope.get("meta") if isinstance(envelope.get("meta"), dict) else None
    if meta is not None:
        return meta

    # Backward-compatible view for sessions created before attempt envelopes existed.
    scenario = SCENARIOS.get(row.scenario_slug, {})
    return {
        "scenario_version": scenario.get("version", "0.0.0"),
        "attempt_number": 1,
        "replay_of_session_id": None,
        "root_session_id": str(row.id),
        "lab_active": bool(row.database_password),
        "ended_early": False,
    }


def _evaluation_result(row: TrainingSession) -> dict | None:
    if not isinstance(row.result, dict):
        return None
    if "meta" in row.result:
        value = row.result.get("evaluation")
        return value if isinstance(value, dict) else None
    # Legacy rows stored the evaluation directly.
    return row.result


def _set_attempt_state(
    row: TrainingSession,
    *,
    lab_active: bool | None = None,
    ended_early: bool | None = None,
    evaluation: dict | None = None,
) -> None:
    meta = dict(_attempt_meta(row))
    if lab_active is not None:
        meta["lab_active"] = lab_active
    if ended_early is not None:
        meta["ended_early"] = ended_early

    current_evaluation = _evaluation_result(row)
    row.result = {
        "meta": meta,
        "evaluation": evaluation if evaluation is not None else current_evaluation,
    }


def session_to_out(row: TrainingSession) -> SessionOut:
    meta = _attempt_meta(row)
    replay_of = meta.get("replay_of_session_id")
    return SessionOut(
        id=row.id,
        learner_name=row.learner_name,
        track_slug=row.track_slug,
        scenario_slug=row.scenario_slug,
        scenario_version=meta.get("scenario_version", "0.0.0"),
        attempt_number=int(meta.get("attempt_number", 1)),
        replay_of_session_id=uuid.UUID(replay_of) if replay_of else None,
        lab_active=bool(meta.get("lab_active", False)),
        status=row.status.value,
        started_at=row.started_at,
        deadline_at=row.deadline_at,
        score=row.score,
        result=_evaluation_result(row),
        connection={
            "host": settings.lab_public_host,
            "port": settings.lab_public_port,
            "database": row.database_name,
            "username": row.database_user,
            "password": row.database_password,
            "sslmode": "disable",
        },
    )


async def _finish_runtime(row: TrainingSession, db: AsyncSession, *, ended_early: bool) -> None:
    meta = _attempt_meta(row)
    if meta.get("lab_active", False):
        await teardown_lab(row.database_name, row.database_user)
        row.database_password = ""
        _set_attempt_state(row, lab_active=False, ended_early=ended_early)

    if ended_early and row.status == SessionStatus.ACTIVE:
        row.status = SessionStatus.FAILED

    await db.commit()
    await db.refresh(row)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/tracks", response_model=list[TrackOut])
async def list_tracks():
    return TRACKS


@app.get("/scenarios", response_model=list[ScenarioOut])
async def list_scenarios(track: str | None = None):
    scenarios = list(SCENARIOS.values())
    if track:
        scenarios = [s for s in scenarios if s["track_slug"] == track]
    return scenarios


@app.get("/scenarios/{scenario_slug}", response_model=ScenarioOut)
async def get_scenario(scenario_slug: str):
    scenario = SCENARIOS.get(scenario_slug)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    return scenario


@app.get("/scenarios/{scenario_slug}/hints")
async def get_hints(scenario_slug: str):
    scenario = SCENARIOS.get(scenario_slug)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    return {"hints": scenario.get("hints", [])}


@app.post("/sessions", response_model=SessionOut)
async def start_session(payload: StartSessionIn, db: AsyncSession = Depends(get_db)):
    scenario = SCENARIOS.get(payload.scenario_slug)
    if not scenario:
        raise HTTPException(404, "Scenario not found")

    sid = uuid.uuid4()
    short_id = sid.hex[:10]
    creds = await provision_scenario(payload.scenario_slug, short_id)

    now = datetime.now(timezone.utc)
    row = TrainingSession(
        id=sid,
        learner_name=payload.learner_name,
        track_slug=scenario["track_slug"],
        scenario_slug=payload.scenario_slug,
        status=SessionStatus.ACTIVE,
        database_name=creds.database,
        database_user=creds.username,
        database_password=creds.password,
        started_at=now,
        deadline_at=now + timedelta(minutes=scenario["duration_minutes"]),
        result=_new_attempt_envelope(
            scenario_version=scenario["version"],
            attempt_number=1,
            session_id=sid,
        ),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return session_to_out(row)


@app.get("/sessions/{session_id}", response_model=SessionOut)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    row = await db.get(TrainingSession, session_id)
    if not row:
        raise HTTPException(404, "Session not found")

    if row.status == SessionStatus.ACTIVE and datetime.now(timezone.utc) > row.deadline_at:
        row.status = SessionStatus.EXPIRED
        await _finish_runtime(row, db, ended_early=False)

    return session_to_out(row)


@app.post("/sessions/{session_id}/evaluate", response_model=EvaluationOut)
async def evaluate(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    row = await db.get(TrainingSession, session_id)
    if not row:
        raise HTTPException(404, "Session not found")

    if not _attempt_meta(row).get("lab_active", False):
        raise HTTPException(409, "This lab runtime has already been finished")

    if datetime.now(timezone.utc) > row.deadline_at:
        row.status = SessionStatus.EXPIRED
        await _finish_runtime(row, db, ended_early=False)
        raise HTTPException(409, "This attempt has expired")

    result = await evaluate_scenario(row.scenario_slug, row.database_name)

    row.score = result["score"]
    _set_attempt_state(row, evaluation=result)
    row.status = SessionStatus.PASSED if result["passed"] else SessionStatus.FAILED
    await db.commit()
    return result


@app.post("/sessions/{session_id}/finish", response_model=SessionOut)
async def finish_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    row = await db.get(TrainingSession, session_id)
    if not row:
        raise HTTPException(404, "Session not found")

    await _finish_runtime(row, db, ended_early=row.status == SessionStatus.ACTIVE)
    return session_to_out(row)


@app.post("/sessions/{session_id}/replay", response_model=SessionOut)
async def replay_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    source = await db.get(TrainingSession, session_id)
    if not source:
        raise HTTPException(404, "Session not found")

    scenario = SCENARIOS.get(source.scenario_slug)
    if not scenario:
        raise HTTPException(409, "The scenario used by this attempt is no longer available")

    source_meta = _attempt_meta(source)
    if source_meta.get("lab_active", False):
        await _finish_runtime(source, db, ended_early=source.status == SessionStatus.ACTIVE)
        source_meta = _attempt_meta(source)

    sid = uuid.uuid4()
    creds = await provision_scenario(source.scenario_slug, sid.hex[:10])
    now = datetime.now(timezone.utc)
    root_id = uuid.UUID(source_meta.get("root_session_id", str(source.id)))

    row = TrainingSession(
        id=sid,
        learner_name=source.learner_name,
        track_slug=scenario["track_slug"],
        scenario_slug=source.scenario_slug,
        status=SessionStatus.ACTIVE,
        database_name=creds.database,
        database_user=creds.username,
        database_password=creds.password,
        started_at=now,
        deadline_at=now + timedelta(minutes=scenario["duration_minutes"]),
        result=_new_attempt_envelope(
            scenario_version=scenario["version"],
            attempt_number=int(source_meta.get("attempt_number", 1)) + 1,
            session_id=sid,
            replay_of_session_id=source.id,
            root_session_id=root_id,
        ),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return session_to_out(row)


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    row = await db.get(TrainingSession, session_id)
    if not row:
        raise HTTPException(404, "Session not found")

    if _attempt_meta(row).get("lab_active", False):
        await teardown_lab(row.database_name, row.database_user)
    await db.delete(row)
    await db.commit()
    return {"deleted": True}
