from app.learning_engine import build_learning_path
from app.models import SessionStatus, TrainingSession


def _attempt(slug: str, status: SessionStatus) -> TrainingSession:
    return TrainingSession(
        learner_name="Learner",
        track_slug="postgresql-dba",
        scenario_slug=slug,
        status=status,
        database_name=f"lab_{slug[:12]}",
        database_user=f"user_{slug[:12]}",
        database_password="",
    )


def _by_slug(path: dict) -> dict[str, dict]:
    return {item["scenario_slug"]: item for item in path["scenarios"]}


def test_new_learner_has_foundational_scenarios_ready():
    path = build_learning_path([], "postgresql-dba")
    scenarios = _by_slug(path)

    assert scenarios["stale-reporting-transaction"]["state"] == "ready"
    assert scenarios["slow-checkout-query"]["state"] == "ready"
    assert scenarios["blocked-payment-transaction"]["state"] == "locked"
    assert scenarios["connection-pool-exhaustion"]["state"] == "locked"
    assert scenarios["deadlock-transfer-procedures"]["state"] == "locked"
    assert scenarios["stale-reporting-transaction"]["recommended"] is True


def test_stale_reporting_unlocks_activity_based_incidents():
    attempts = [_attempt("stale-reporting-transaction", SessionStatus.PASSED)]
    path = build_learning_path(attempts, "postgresql-dba")
    scenarios = _by_slug(path)

    assert scenarios["stale-reporting-transaction"]["state"] == "completed"
    assert scenarios["blocked-payment-transaction"]["state"] == "ready"
    assert scenarios["connection-pool-exhaustion"]["state"] == "ready"
    assert scenarios["deadlock-transfer-procedures"]["state"] == "locked"


def test_blocked_payment_unlocks_deadlock_after_foundation():
    attempts = [
        _attempt("stale-reporting-transaction", SessionStatus.PASSED),
        _attempt("blocked-payment-transaction", SessionStatus.PASSED),
    ]
    path = build_learning_path(attempts, "postgresql-dba")
    scenarios = _by_slug(path)

    assert scenarios["deadlock-transfer-procedures"]["state"] == "ready"
    assert "postgresql.locking" in {skill["slug"] for skill in path["mastered_skills"]}


def test_failed_attempt_does_not_master_skills():
    attempts = [_attempt("stale-reporting-transaction", SessionStatus.FAILED)]
    path = build_learning_path(attempts, "postgresql-dba")
    scenarios = _by_slug(path)

    assert scenarios["blocked-payment-transaction"]["state"] == "locked"
    assert path["mastered_skills"] == []
