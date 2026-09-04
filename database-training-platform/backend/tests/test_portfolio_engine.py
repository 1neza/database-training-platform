import copy
import uuid
from datetime import datetime, timezone

from app.catalog import SCENARIOS
from app.models import SessionStatus, TrainingSession
from app.portfolio_engine import build_portfolio


def _attempt(
    slug: str,
    status: SessionStatus,
    score: int,
    *,
    title: str | None = None,
    version: str | None = None,
    started_at: datetime | None = None,
) -> TrainingSession:
    scenario = copy.deepcopy(SCENARIOS[slug])
    if title is not None:
        scenario["title"] = title
    if version is not None:
        scenario["version"] = version

    return TrainingSession(
        id=uuid.uuid4(),
        learner_name="Learner",
        track_slug=scenario["track_slug"],
        scenario_slug=slug,
        status=status,
        score=score,
        started_at=started_at or datetime(2026, 9, 4, tzinfo=timezone.utc),
        database_name=f"lab_{uuid.uuid4().hex[:10]}",
        database_user=f"user_{uuid.uuid4().hex[:10]}",
        database_password="",
        result={
            "meta": {
                "scenario_version": scenario["version"],
                "attempt_number": 1,
                "lab_active": False,
            },
            "scenario_snapshot": scenario,
            "evaluation": {
                "passed": status == SessionStatus.PASSED,
                "score": score,
                "checks": [
                    {
                        "name": "Deterministic verification",
                        "passed": status == SessionStatus.PASSED,
                        "detail": "database state verified",
                    }
                ],
                "feedback": ["Evidence recorded from the live database."],
            },
        },
    )


def test_portfolio_ignores_failed_attempts():
    portfolio = build_portfolio(
        [_attempt("slow-checkout-query", SessionStatus.FAILED, 50)]
    )

    assert portfolio["scenarios_demonstrated"] == 0
    assert portfolio["skills_demonstrated"] == 0
    assert portfolio["evidence"] == []


def test_portfolio_keeps_strongest_passed_attempt_per_scenario():
    attempts = [
        _attempt("slow-checkout-query", SessionStatus.PASSED, 80),
        _attempt("slow-checkout-query", SessionStatus.PASSED, 100),
    ]
    portfolio = build_portfolio(attempts)

    assert portfolio["scenarios_demonstrated"] == 1
    assert len(portfolio["evidence"]) == 1
    assert portfolio["evidence"][0]["score"] == 100
    assert "1/1 deterministic verification checks passed" in portfolio["evidence"][0]["evidence_summary"]


def test_portfolio_uses_immutable_scenario_snapshot():
    attempt = _attempt(
        "slow-checkout-query",
        SessionStatus.PASSED,
        100,
        title="Historical Checkout Incident",
        version="9.4.2",
    )
    portfolio = build_portfolio([attempt])
    evidence = portfolio["evidence"][0]

    assert evidence["scenario_title"] == "Historical Checkout Incident"
    assert evidence["scenario_version"] == "9.4.2"


def test_portfolio_collects_demonstrated_skills_and_checks():
    attempts = [
        _attempt("slow-checkout-query", SessionStatus.PASSED, 100),
        _attempt("stale-reporting-transaction", SessionStatus.PASSED, 100),
    ]
    portfolio = build_portfolio(attempts)
    skill_slugs = {item["slug"] for item in portfolio["demonstrated_skills"]}

    assert portfolio["scenarios_demonstrated"] == 2
    assert "postgresql.indexing" in skill_slugs
    assert "postgresql.activity-monitoring" in skill_slugs
    assert all(item["checks"][0]["passed"] for item in portfolio["evidence"])
