from .catalog import SCENARIOS
from .evaluation_engine import evaluate_checks, validate_evaluation_spec
from .lab import LabCredentials
from .provisioning_engine import provision_from_spec, validate_provisioning_spec


class ScenarioConfigurationError(RuntimeError):
    pass


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
