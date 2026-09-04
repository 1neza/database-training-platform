import pytest

from app.catalog import SCENARIOS
from app.scenario_engine import (
    EVALUATORS,
    PROVISIONERS,
    ScenarioConfigurationError,
    get_scenario_runtime,
    validate_scenario_catalog,
)


def test_every_catalog_scenario_has_registered_runtime():
    validate_scenario_catalog()

    for slug, scenario in SCENARIOS.items():
        runtime = scenario["runtime"]
        assert runtime["provisioner"] in PROVISIONERS
        assert runtime["evaluator"] in EVALUATORS
        resolved = get_scenario_runtime(slug)
        assert callable(resolved.provisioner)
        assert callable(resolved.evaluator)


def test_unknown_scenario_raises_key_error():
    with pytest.raises(KeyError):
        get_scenario_runtime("does-not-exist")


def test_invalid_runtime_fails_fast(monkeypatch):
    monkeypatch.setitem(
        SCENARIOS,
        "broken-scenario",
        {
            "slug": "broken-scenario",
            "runtime": {"provisioner": "missing", "evaluator": "missing"},
        },
    )

    with pytest.raises(ScenarioConfigurationError):
        get_scenario_runtime("broken-scenario")
