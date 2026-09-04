from app.learning_engine import build_learning_path
from app.models import SessionStatus, TrainingSession


def _attempt(slug: str, status: SessionStatus, score: int | None = None) -> TrainingSession:
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


def test_new_learner_targets_foundational_difficulty():
    path = build_learning_path([], "postgresql-dba")

    assert path["target_difficulty"] == 2
    assert "foundational" in path["difficulty_reason"]
    assert all("difficulty" in item for item in path["scenarios"])


def test_two_strong_foundational_passes_raise_target_to_three():
    attempts = [
        _attempt("stale-reporting-transaction", SessionStatus.PASSED, 100),
        _attempt("slow-checkout-query", SessionStatus.PASSED, 100),
    ]
    path = build_learning_path(attempts, "postgresql-dba")
    scenarios = _by_slug(path)

    assert path["target_difficulty"] == 3
    assert scenarios["connection-pool-exhaustion"]["difficulty"] == 3
    assert scenarios["connection-pool-exhaustion"]["recommended"] is True
    assert "matches the current target difficulty 3/5" in scenarios["connection-pool-exhaustion"]["recommendation_reasons"]


def test_success_at_three_raises_target_toward_advanced_deadlock():
    attempts = [
        _attempt("stale-reporting-transaction", SessionStatus.PASSED, 100),
        _attempt("slow-checkout-query", SessionStatus.PASSED, 100),
        _attempt("blocked-payment-transaction", SessionStatus.PASSED, 100),
    ]
    path = build_learning_path(attempts, "postgresql-dba")
    scenarios = _by_slug(path)

    assert path["target_difficulty"] == 4
    assert scenarios["deadlock-transfer-procedures"]["state"] == "ready"
    assert scenarios["deadlock-transfer-procedures"]["difficulty"] == 4
    assert scenarios["deadlock-transfer-procedures"]["recommended"] is True


def test_failed_retry_still_outranks_difficulty_fit():
    attempts = [
        _attempt("stale-reporting-transaction", SessionStatus.PASSED, 100),
        _attempt("slow-checkout-query", SessionStatus.PASSED, 100),
        _attempt("blocked-payment-transaction", SessionStatus.FAILED, 45),
    ]
    path = build_learning_path(attempts, "postgresql-dba")
    scenarios = _by_slug(path)

    assert path["target_difficulty"] == 3
    assert scenarios["blocked-payment-transaction"]["recommended"] is True
    assert "retry an unresolved incident" in scenarios["blocked-payment-transaction"]["recommendation_reasons"]
