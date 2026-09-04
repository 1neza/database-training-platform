import re

from .catalog import SCENARIOS, TRACKS
from .evaluation_engine import evaluate_checks, validate_evaluation_spec
from .lab import LabCredentials
from .provisioning_engine import provision_from_spec, validate_provisioning_spec


_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


class ScenarioConfigurationError(RuntimeError):
    pass


def _require_nonempty_string(scenario_slug: str, scenario: dict, field: str) -> None:
    value = scenario.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ScenarioConfigurationError(
            f"Scenario {scenario_slug!r} requires non-empty {field!r}"
        )


def _require_string_list(scenario_slug: str, scenario: dict, field: str) -> None:
    value = scenario.get(field)
    if not isinstance(value, list) or not value:
        raise ScenarioConfigurationError(
            f"Scenario {scenario_slug!r} requires a non-empty {field!r} list"
        )
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ScenarioConfigurationError(
            f"Scenario {scenario_slug!r} {field!r} entries must be non-empty strings"
        )


def validate_scenario_metadata(scenario_slug: str, scenario: dict) -> None:
    if scenario.get("slug") != scenario_slug:
        raise ScenarioConfigurationError(
            f"Scenario catalog key {scenario_slug!r} does not match its slug"
        )

    for field in ("slug", "version", "track_slug", "title", "level", "summary", "incident"):
        _require_nonempty_string(scenario_slug, scenario, field)

    if not _SEMVER.fullmatch(scenario["version"]):
        raise ScenarioConfigurationError(
            f"Scenario {scenario_slug!r} version must use MAJOR.MINOR.PATCH"
        )

    duration = scenario.get("duration_minutes")
    if not isinstance(duration, int) or duration <= 0:
        raise ScenarioConfigurationError(
            f"Scenario {scenario_slug!r} requires positive integer duration_minutes"
        )

    _require_string_list(scenario_slug, scenario, "objectives")
    _require_string_list(scenario_slug, scenario, "hints")

    track_slugs = {track["slug"] for track in TRACKS}
    if scenario["track_slug"] not in track_slugs:
        raise ScenarioConfigurationError(
            f"Scenario {scenario_slug!r} references unknown track {scenario['track_slug']!r}"
        )


def get_scenario_definition(scenario_slug: str) -> dict:
    scenario = SCENARIOS.get(scenario_slug)
    if scenario is None:
        raise KeyError(scenario_slug)
    return scenario


async def provision_scenario(scenario_slug: str, session_short_id: str) -> LabCredentials:
    scenario = get_scenario_definition(scenario_slug)
    provisioning = scenario.get("provisioning")
    if not isinstance(provisioning, dict):
        raise ScenarioConfigurationError(
            f"Scenario {scenario_slug!r} is missing a provisioning configuration"
        )
    return await provision_from_spec(session_short_id, provisioning)


async def evaluate_scenario(scenario_slug: str, database: str) -> dict:
    scenario = get_scenario_definition(scenario_slug)
    evaluation = scenario.get("evaluation")
    if not isinstance(evaluation, dict):
        raise ScenarioConfigurationError(
            f"Scenario {scenario_slug!r} is missing an evaluation configuration"
        )
    return await evaluate_checks(database, evaluation)


def validate_scenario_catalog() -> None:
    for scenario_slug, scenario in SCENARIOS.items():
        validate_scenario_metadata(scenario_slug, scenario)

        provisioning = scenario.get("provisioning")
        if not isinstance(provisioning, dict):
            raise ScenarioConfigurationError(
                f"Scenario {scenario_slug!r} is missing a provisioning configuration"
            )
        validate_provisioning_spec(provisioning)

        evaluation = scenario.get("evaluation")
        if not isinstance(evaluation, dict):
            raise ScenarioConfigurationError(
                f"Scenario {scenario_slug!r} is missing an evaluation configuration"
            )
        validate_evaluation_spec(evaluation)
