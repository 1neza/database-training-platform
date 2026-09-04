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
    version="0.2.0",
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
    # Fail fast if a scenario references a provisioner/evaluator that is not
    # registered. A broken catalogue should never reach a learner session.
    validate_scenario_catalog()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def session_to_out(row: TrainingSession) -> SessionOut:
    return SessionOut(
        id=row.id,
        learner_name=row.learner_name,
        track_slug=row.track_slug,
        scenario_slug=row.scenario_slug,
        status=row.status.value,
        started_at=row.started_at,
        deadline_at=row.deadline_at,
        score=row.score,
        result=row.result,
        connection={
            "host": settings.lab_public_host,
            "port": settings.lab_public_port,
            "database": row.database_name,
            "username": row.database_user,
            "password": row.database_password,
            "sslmode": "disable",
        },
    )


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
        await db.commit()
        await db.refresh(row)

    return session_to_out(row)


@app.post("/sessions/{session_id}/evaluate", response_model=EvaluationOut)
async def evaluate(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    row = await db.get(TrainingSession, session_id)
    if not row:
        raise HTTPException(404, "Session not found")

    result = await evaluate_scenario(row.scenario_slug, row.database_name)

    row.score = result["score"]
    row.result = result
    row.status = SessionStatus.PASSED if result["passed"] else SessionStatus.FAILED
    await db.commit()
    return result


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    row = await db.get(TrainingSession, session_id)
    if not row:
        raise HTTPException(404, "Session not found")

    await teardown_lab(row.database_name, row.database_user)
    await db.delete(row)
    await db.commit()
    return {"deleted": True}
