from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from .catalog import SCENARIOS
from .models import SessionStatus, TrainingSession
from .skill_catalog import SKILLS


RETRY_BOOST = 80
FAILURE_BOOST = 12
WEAK_SKILL_BOOST = 18
REVIEW_DUE_BOOST = 55
LOW_SCORE_THRESHOLD = 80
REVIEW_INTERVALS_DAYS = (7, 21, 60, 120)


def mastered_skills(attempts: Iterable[TrainingSession]) -> set[str]:
    mastered: set[str] = set()
    for attempt in attempts:
        if attempt.status != SessionStatus.PASSED:
            continue
        scenario = SCENARIOS.get(attempt.scenario_slug)
        if not scenario:
            continue
        mastered.update(scenario.get("skills", []))
    return mastered


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _attempt_evidence(attempts: list[TrainingSession]) -> dict[str, dict]:
    evidence: dict[str, dict] = defaultdict(
        lambda: {
            "attempts": 0,
            "failures": 0,
            "passes": 0,
            "scores": [],
            "pass_dates": [],
        }
    )
    for attempt in attempts:
        scenario = SCENARIOS.get(attempt.scenario_slug)
        if not scenario:
            continue
        item = evidence[attempt.scenario_slug]
        item["attempts"] += 1
        if attempt.status == SessionStatus.PASSED:
            item["passes"] += 1
            passed_at = _normalize_datetime(attempt.started_at)
            if passed_at is not None:
                item["pass_dates"].append(passed_at)
        elif attempt.status in {SessionStatus.FAILED, SessionStatus.EXPIRED}:
            item["failures"] += 1
        if attempt.score is not None:
            item["scores"].append(attempt.score)

    for item in evidence.values():
        item["best_score"] = max(item["scores"]) if item["scores"] else None
        item["average_score"] = (
            sum(item["scores"]) / len(item["scores"]) if item["scores"] else None
        )
        item["last_pass_at"] = max(item["pass_dates"]) if item["pass_dates"] else None
    return dict(evidence)


def _weak_skill_evidence(
    attempts: list[TrainingSession], mastered: set[str]
) -> dict[str, dict]:
    evidence: dict[str, dict] = defaultdict(
        lambda: {"attempts": 0, "failures": 0, "scores": []}
    )
    for attempt in attempts:
        scenario = SCENARIOS.get(attempt.scenario_slug)
        if not scenario:
            continue
        for skill_slug in scenario.get("skills", []):
            item = evidence[skill_slug]
            item["attempts"] += 1
            if attempt.status in {SessionStatus.FAILED, SessionStatus.EXPIRED}:
                item["failures"] += 1
            if attempt.score is not None:
                item["scores"].append(attempt.score)

    weak: dict[str, dict] = {}
    for skill_slug, item in evidence.items():
        average_score = (
            sum(item["scores"]) / len(item["scores"]) if item["scores"] else None
        )
        if skill_slug in mastered:
            continue
        if item["failures"] > 0 or (
            average_score is not None and average_score < LOW_SCORE_THRESHOLD
        ):
            weak[skill_slug] = {
                "attempts": item["attempts"],
                "failures": item["failures"],
                "average_score": average_score,
            }
    return weak


def _review_schedule(
    scenario_evidence: dict | None,
    now: datetime,
) -> dict:
    if not scenario_evidence or scenario_evidence.get("passes", 0) <= 0:
        return {
            "review_due": False,
            "review_due_at": None,
            "review_interval_days": None,
            "days_overdue": 0,
        }

    last_pass_at = scenario_evidence.get("last_pass_at")
    if last_pass_at is None:
        return {
            "review_due": False,
            "review_due_at": None,
            "review_interval_days": None,
            "days_overdue": 0,
        }

    pass_count = scenario_evidence["passes"]
    interval = REVIEW_INTERVALS_DAYS[min(pass_count - 1, len(REVIEW_INTERVALS_DAYS) - 1)]
    if scenario_evidence.get("failures", 0) > 0:
        interval = max(3, interval // 2)

    due_at = last_pass_at + timedelta(days=interval)
    overdue_seconds = max(0, (now - due_at).total_seconds())
    return {
        "review_due": now >= due_at,
        "review_due_at": due_at,
        "review_interval_days": interval,
        "days_overdue": int(overdue_seconds // 86400),
    }


def _recommendation_score(
    scenario: dict,
    scenario_evidence: dict | None,
    weak_skills: dict[str, dict],
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    if scenario_evidence and scenario_evidence["passes"] == 0:
        score += RETRY_BOOST
        reasons.append("retry an unresolved incident")
        failures = scenario_evidence["failures"]
        if failures:
            score += failures * FAILURE_BOOST
            reasons.append(f"strengthen after {failures} unsuccessful attempt(s)")
        best_score = scenario_evidence.get("best_score")
        if best_score is not None and best_score < 100:
            score += max(0, (100 - best_score) // 5)
            reasons.append(f"improve the previous best score of {best_score}/100")

    trained_weak_skills = [
        skill for skill in scenario.get("skills", []) if skill in weak_skills
    ]
    if trained_weak_skills:
        score += len(trained_weak_skills) * WEAK_SKILL_BOOST
        reasons.append("practice currently weak skills")

    if not reasons:
        reasons.append("advance to a ready skill area")

    return score, reasons


def build_learning_path(
    attempts: list[TrainingSession],
    track_slug: str,
    *,
    now: datetime | None = None,
) -> dict:
    now = _normalize_datetime(now) or datetime.now(timezone.utc)
    mastered = mastered_skills(attempts)
    passed_scenarios = {
        attempt.scenario_slug
        for attempt in attempts
        if attempt.status == SessionStatus.PASSED
    }
    attempt_evidence = _attempt_evidence(attempts)
    weak_evidence = _weak_skill_evidence(attempts, mastered)

    readiness: list[dict] = []
    for scenario in SCENARIOS.values():
        if scenario["track_slug"] != track_slug:
            continue

        prerequisites = scenario.get("prerequisites", [])
        missing = [slug for slug in prerequisites if slug not in mastered]
        if scenario["slug"] in passed_scenarios:
            state = "completed"
        elif missing:
            state = "locked"
        else:
            state = "ready"

        scenario_evidence = attempt_evidence.get(scenario["slug"])
        review = _review_schedule(scenario_evidence, now)
        priority = 0
        reasons: list[str] = []
        if state == "ready":
            priority, reasons = _recommendation_score(
                scenario,
                scenario_evidence,
                weak_evidence,
            )
        elif state == "completed" and review["review_due"]:
            priority = REVIEW_DUE_BOOST + min(review["days_overdue"], 30)
            reasons = [
                f"review this skill after {review['review_interval_days']} day(s)",
            ]
            if review["days_overdue"] > 0:
                reasons.append(f"review is {review['days_overdue']} day(s) overdue")

        readiness.append({
            "scenario_slug": scenario["slug"],
            "scenario_title": scenario["title"],
            "scenario_version": scenario["version"],
            "state": state,
            "skills": scenario.get("skills", []),
            "prerequisites": prerequisites,
            "missing_prerequisites": missing,
            "recommended": False,
            "recommendation_priority": priority,
            "recommendation_reasons": reasons,
            "review_due": review["review_due"],
            "review_due_at": review["review_due_at"],
            "review_interval_days": review["review_interval_days"],
        })

    candidates = [
        item
        for item in readiness
        if item["state"] == "ready" or item["review_due"]
    ]
    if candidates:
        candidates.sort(
            key=lambda item: (
                -item["recommendation_priority"],
                0 if item["state"] == "ready" else 1,
                len(item["prerequisites"]),
                SCENARIOS[item["scenario_slug"]]["duration_minutes"],
                item["scenario_title"],
            )
        )
        candidates[0]["recommended"] = True

    mastered_out = [
        {
            "slug": slug,
            "name": SKILLS[slug]["name"],
            "description": SKILLS[slug]["description"],
        }
        for slug in sorted(mastered)
        if slug in SKILLS
    ]
    weak_out = [
        {
            "slug": slug,
            "name": SKILLS[slug]["name"],
            "description": SKILLS[slug]["description"],
            **weak_evidence[slug],
        }
        for slug in sorted(weak_evidence)
        if slug in SKILLS
    ]

    readiness.sort(
        key=lambda item: (
            0 if item["recommended"] else 1,
            {"ready": 0, "locked": 1, "completed": 2}[item["state"]],
            -item["recommendation_priority"],
            item["scenario_title"],
        )
    )

    return {
        "track_slug": track_slug,
        "mastered_skills": mastered_out,
        "weak_skills": weak_out,
        "scenarios": readiness,
    }
