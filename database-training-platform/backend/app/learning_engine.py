from collections.abc import Iterable

from .catalog import SCENARIOS
from .models import SessionStatus, TrainingSession
from .skill_catalog import SKILLS


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


def build_learning_path(attempts: list[TrainingSession], track_slug: str) -> dict:
    mastered = mastered_skills(attempts)
    passed_scenarios = {
        attempt.scenario_slug
        for attempt in attempts
        if attempt.status == SessionStatus.PASSED
    }

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

        readiness.append({
            "scenario_slug": scenario["slug"],
            "scenario_title": scenario["title"],
            "scenario_version": scenario["version"],
            "state": state,
            "skills": scenario.get("skills", []),
            "prerequisites": prerequisites,
            "missing_prerequisites": missing,
            "recommended": False,
        })

    candidates = [item for item in readiness if item["state"] == "ready"]
    if candidates:
        candidates.sort(
            key=lambda item: (
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

    readiness.sort(
        key=lambda item: (
            {"ready": 0, "locked": 1, "completed": 2}[item["state"]],
            item["scenario_title"],
        )
    )

    return {
        "track_slug": track_slug,
        "mastered_skills": mastered_out,
        "scenarios": readiness,
    }
