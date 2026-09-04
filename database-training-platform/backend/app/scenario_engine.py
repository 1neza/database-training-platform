from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from .catalog import SCENARIOS
from .evaluation_engine import evaluate_checks, validate_evaluation_spec
from .lab import (
    LabCredentials,
    provision_blocked_payment,
    provision_connection_pressure,
    provision_slow_checkout,
)

Provisioner = Callable[[str], Awaitable[LabCredentials]]


class ScenarioConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScenarioRuntime:
    provisioner: Provisioner


PROVISIONERS: dict[str, Provisioner] = {
    "slow_checkout": provision_slow_checkout,
    "blocked_payment": provision_blocked_payment,
    "connection_pressure": provision_connection_pressure,
}


def get_scenario_definition(scenario_slug: str) -> dict:
    scenario = SCENARIOS.get(scenario_slug)
    if scenario is None:
        raise KeyError(scenario_slug)
    return scenario


def get_scenario_runtime(scenario_slug: str) -> ScenarioRuntime:
    scenario = get_scenario_definition(scenario_slug)
    runtime = scenario.get("runtime")
    if not isinstance(runtime, dict):
        raise ScenarioConfigurationError(
            f"Scenario {scenario_slug!r} is missing a runtime configuration"
        )

    provisioner_name = runtime.get("provisioner")
    try:
        provisioner = PROVISIONERS[provisioner_name]
    except KeyError as exc:
        raise ScenarioConfigurationError(
            f"Scenario {scenario_slug!r} references unknown provisioner {provisioner_name!r}"
        ) from exc

    return ScenarioRuntime(provisioner=provisioner)


async def provision_scenario(scenario_slug: str, session_short_id: str) -> LabCredentials:
    runtime = get_scenario_runtime(scenario_slug)
    return await runtime.provisioner(session_short_id)


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
        get_scenario_runtime(scenario_slug)
        evaluation = scenario.get("evaluation")
        if not isinstance(evaluation, dict):
            raise ScenarioConfigurationError(
                f"Scenario {scenario_slug!r} is missing an evaluation configuration"
            )
        validate_evaluation_spec(evaluation)
