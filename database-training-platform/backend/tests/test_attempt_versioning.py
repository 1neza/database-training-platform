import uuid
from datetime import datetime, timedelta, timezone

from app.main import _attempt_meta, _attempt_scenario, _new_attempt_envelope
from app.models import SessionStatus, TrainingSession


def _scenario(version: str = "1.0.0") -> dict:
    return {
        "slug": "snapshot-test",
        "version": version,
        "track_slug": "postgresql-dba",
        "title": "Snapshot Test",
        "level": "beginner",
        "duration_minutes": 10,
        "summary": "Snapshot fixture.",
        "incident": "Test incident.",
        "objectives": ["Inspect state."],
        "hints": ["Use SQL."],
        "provisioning": {"setup_sql": ["SELECT 1"], "roles": [], "faults": []},
        "evaluation": {
            "checks": [
                {
                    "type": "scalar_equals",
                    "name": "healthy",
                    "sql": "SELECT 1",
                    "expected": 1,
                    "points": 100,
                }
            ]
        },
    }


def _row(envelope: dict) -> TrainingSession:
    now = datetime.now(timezone.utc)
    return TrainingSession(
        id=uuid.uuid4(),
        learner_name="Learner",
        track_slug="postgresql-dba",
        scenario_slug="snapshot-test",
        status=SessionStatus.ACTIVE,
        database_name="lab_snapshot",
        database_user="student_snapshot",
        database_password="secret",
        started_at=now,
        deadline_at=now + timedelta(minutes=10),
        result=envelope,
    )


def test_attempt_envelope_snapshots_scenario_definition():
    sid = uuid.uuid4()
    scenario = _scenario()
    envelope = _new_attempt_envelope(
        scenario=scenario,
        attempt_number=1,
        session_id=sid,
    )

    scenario["version"] = "2.0.0"
    scenario["evaluation"]["checks"][0]["expected"] = 2

    assert envelope["meta"]["scenario_version"] == "1.0.0"
    assert envelope["scenario_snapshot"]["version"] == "1.0.0"
    assert envelope["scenario_snapshot"]["evaluation"]["checks"][0]["expected"] == 1


def test_attempt_scenario_reads_snapshot_not_mutable_catalog_state():
    envelope = _new_attempt_envelope(
        scenario=_scenario("1.2.3"),
        attempt_number=2,
        session_id=uuid.uuid4(),
        replay_of_session_id=uuid.uuid4(),
    )
    row = _row(envelope)

    snapshot = _attempt_scenario(row)
    meta = _attempt_meta(row)

    assert snapshot["version"] == "1.2.3"
    assert meta["attempt_number"] == 2
    assert meta["replay_of_session_id"] is not None
    assert meta["lab_active"] is True
