from datetime import datetime

from .catalog import SCENARIOS
from .models import SessionStatus, TrainingSession
from .skill_catalog import SKILLS


def _scenario_snapshot(attempt: TrainingSession) -> dict:
    if isinstance(attempt.result, dict):
        snapshot = attempt.result.get("scenario_snapshot")
        if isinstance(snapshot, dict):
            return snapshot
    return SCENARIOS.get(attempt.scenario_slug, {})


def _evaluation(attempt: TrainingSession) -> dict | None:
    if not isinstance(attempt.result, dict):
        return None
    if "meta" in attempt.result:
        value = attempt.result.get("evaluation")
        return value if isinstance(value, dict) else None
    return attempt.result


def _attempt_sort_key(attempt: TrainingSession) -> tuple[int, datetime]:
    score = attempt.score if attempt.score is not None else -1
    started = attempt.started_at or datetime.min
    if started.tzinfo is not None:
        started = started.replace(tzinfo=None)
    return score, started


def build_portfolio(attempts: list[TrainingSession]) -> dict:
    passed = [attempt for attempt in attempts if attempt.status == SessionStatus.PASSED]

    best_by_scenario: dict[str, TrainingSession] = {}
    for attempt in passed:
        current = best_by_scenario.get(attempt.scenario_slug)
        if current is None or _attempt_sort_key(attempt) > _attempt_sort_key(current):
            best_by_scenario[attempt.scenario_slug] = attempt

    evidence: list[dict] = []
    demonstrated_skill_slugs: set[str] = set()

    for attempt in best_by_scenario.values():
        scenario = _scenario_snapshot(attempt)
        evaluation = _evaluation(attempt) or {}
        skill_slugs = [slug for slug in scenario.get("skills", []) if slug in SKILLS]
        demonstrated_skill_slugs.update(skill_slugs)
        checks = [
            {
                "name": check.get("name", "Verification check"),
                "passed": bool(check.get("passed", False)),
                "detail": check.get("detail", ""),
            }
            for check in evaluation.get("checks", [])
            if isinstance(check, dict)
        ]
        passed_checks = sum(check["passed"] for check in checks)

        evidence.append({
            "attempt_id": attempt.id,
            "scenario_slug": attempt.scenario_slug,
            "scenario_title": scenario.get("title", attempt.scenario_slug),
            "scenario_version": (
                attempt.result.get("meta", {}).get("scenario_version")
                if isinstance(attempt.result, dict)
                else None
            ) or scenario.get("version", "0.0.0"),
            "score": attempt.score,
            "attempted_at": attempt.started_at,
            "skills": [
                {
                    "slug": slug,
                    "name": SKILLS[slug]["name"],
                    "description": SKILLS[slug]["description"],
                }
                for slug in skill_slugs
            ],
            "objectives": scenario.get("objectives", []),
            "checks": checks,
            "feedback": evaluation.get("feedback", []),
            "evidence_summary": (
                f"Resolved {scenario.get('title', attempt.scenario_slug)} with "
                f"{attempt.score if attempt.score is not None else 'unscored'}/100; "
                f"{passed_checks}/{len(checks)} deterministic verification checks passed."
            ),
        })

    evidence.sort(
        key=lambda item: item["attempted_at"] or datetime.min,
        reverse=True,
    )

    demonstrated_skills = [
        {
            "slug": slug,
            "name": SKILLS[slug]["name"],
            "description": SKILLS[slug]["description"],
        }
        for slug in sorted(demonstrated_skill_slugs)
    ]

    return {
        "scenarios_demonstrated": len(evidence),
        "skills_demonstrated": len(demonstrated_skills),
        "demonstrated_skills": demonstrated_skills,
        "evidence": evidence,
    }
