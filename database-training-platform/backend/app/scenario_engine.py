from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from .catalog import SCENARIOS
from .evaluator import evaluate_blocked_payment, evaluate_slow_checkout
from .lab import LabCredentials, provision_blocked_payment, provision_slow_checkout

Provisioner = Callable[[str], Awaitable[LabCredentials]]
Evaluator = Callable[[str], Awaitable[dict]]


class ScenarioConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScenarioRuntime:
    provisioner: Provisioner
    evaluator: Evaluator


PROVISIONERS: dict[str, Provisioner] = {
    "slow_checkout": provision_slow_checkout,
    "blocked_payment": provision_blocked_payment,
}

EVALUATORS: dict[str, Evaluator] = {
    "slow_checkout": evaluate_slow_checkout,
    "blocked_payment": evaluate_blocked_payment,
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
    evaluator_name = runtime.get("evaluator")

    try:
        provisioner = PROVISIONERS[provisioner_name]
    except KeyError as exc:
        raise ScenarioConfigurationError(
            f"Scenario {scenario_slug!r} references unknown provisioner {provisioner_name!r}"
        ) from exc

    try:
        evaluator = EVALUATORS[evaluator_name]
    except KeyError as exc:
        raise ScenarioConfigurationError(
            f"Scenario {scenario_slug!r} references unknown evaluator {evaluator_name!r}"
        ) from exc

    return ScenarioRuntime(provisioner=provisioner, evaluator=evaluator)


async def provision_scenario(scenario_slug: str, session_short_id: str) -> LabCredentials:
    runtime = get_scenario_runtime(scenario_slug)
    return await runtime.provisioner(session_short_id)


async def evaluate_scenario(scenario_slug: str, database: str) -> dict:
    runtime = get_scenario_runtime(scenario_slug)
    return await runtime.evaluator(database)


def validate_scenario_catalog() -> None:
    for scenario_slug in SCENARIOS:
        get_scenario_runtime(scenario_slug)
