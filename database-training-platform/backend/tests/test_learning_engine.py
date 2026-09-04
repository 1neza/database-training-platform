from app.learning_engine import build_learning_path
from app.models import SessionStatus, TrainingSession


def _attempt(
    slug: str,
    status: SessionStatus,
    score: int | None = None,
) -> TrainingSession:
    return TrainingSession(
        learner_name="Learner",
        track_slug="postgresql-dba",
        scenario_slug=slug,
        status=status,
        score=score,
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
    assert path["weak_skills"] == []


def test_stale_reporting_unlocks_activity_based_incidents():
    attempts = [_attempt("stale-reporting-transaction", SessionStatus.PASSED, 100)]
    path = build_learning_path(attempts, "postgresql-dba")
    scenarios = _by_slug(path)

    assert scenarios["stale-reporting-transaction"]["state"] == "completed"
    assert scenarios["blocked-payment-transaction"]["state"] == "ready"
    assert scenarios["connection-pool-exhaustion"]["state"] == "ready"
    assert scenarios["deadlock-transfer-procedures"]["state"] == "locked"


def test_blocked_payment_unlocks_deadlock_after_foundation():
    attempts = [
        _attempt("stale-reporting-transaction", SessionStatus.PASSED, 100),
        _attempt("blocked-payment-transaction", SessionStatus.PASSED, 100),
    ]
    path = build_learning_path(attempts, "postgresql-dba")
    scenarios = _by_slug(path)

    assert scenarios["deadlock-transfer-procedures"]["state"] == "ready"
    assert "postgresql.locking" in {skill["slug"] for skill in path["mastered_skills"]}


def test_failed_attempt_does_not_master_skills_and_becomes_weak():
    attempts = [_attempt("stale-reporting-transaction", SessionStatus.FAILED, 40)]
    path = build_learning_path(attempts, "postgresql-dba")
    scenarios = _by_slug(path)

    assert scenarios["blocked-payment-transaction"]["state"] == "locked"
    assert scenarios["stale-reporting-transaction"]["recommended"] is True
    assert "retry an unresolved incident" in scenarios["stale-reporting-transaction"]["recommendation_reasons"]
    assert path["mastered_skills"] == []
    weak = {skill["slug"] for skill in path["weak_skills"]}
    assert "postgresql.activity-monitoring" in weak
    assert "postgresql.transaction-basics" in weak


def test_failed_ready_scenario_is_prioritized_over_untouched_ready_scenario():
    attempts = [_attempt("slow-checkout-query", SessionStatus.FAILED, 50)]
    path = build_learning_path(attempts, "postgresql-dba")
    scenarios = _by_slug(path)

    assert scenarios["slow-checkout-query"]["state"] == "ready"
    assert scenarios["slow-checkout-query"]["recommended"] is True
    assert scenarios["stale-reporting-transaction"]["recommended"] is False
    assert scenarios["slow-checkout-query"]["recommendation_priority"] > 0
    assert "improve the previous best score of 50/100" in scenarios["slow-checkout-query"]["recommendation_reasons"]


def test_passing_retry_clears_weak_skills_for_mastered_area():
    attempts = [
        _attempt("stale-reporting-transaction", SessionStatus.FAILED, 35),
        _attempt("stale-reporting-transaction", SessionStatus.PASSED, 100),
    ]
    path = build_learning_path(attempts, "postgresql-dba")
    scenarios = _by_slug(path)

    assert scenarios["stale-reporting-transaction"]["state"] == "completed"
    weak = {skill["slug"] for skill in path["weak_skills"]}
    assert "postgresql.activity-monitoring" not in weak
    assert "postgresql.transaction-basics" not in weak
    assert scenarios["blocked-payment-transaction"]["state"] == "ready"
    assert scenarios["connection-pool-exhaustion"]["state"] == "ready"
