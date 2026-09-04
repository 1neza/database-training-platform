import pytest

from app.catalog import SCENARIOS
from app.evaluation_engine import EvaluationConfigurationError
from app.scenario_engine import (
    PROVISIONERS,
    ScenarioConfigurationError,
    get_scenario_runtime,
    validate_scenario_catalog,
)


def test_every_catalog_scenario_has_registered_runtime_and_evaluation():
    validate_scenario_catalog()

    for slug, scenario in SCENARIOS.items():
        runtime = scenario["runtime"]
        assert runtime["provisioner"] in PROVISIONERS
        assert "evaluation" in scenario
        resolved = get_scenario_runtime(slug)
        assert callable(resolved.provisioner)


def test_unknown_scenario_raises_key_error():
    with pytest.raises(KeyError):
        get_scenario_runtime("does-not-exist")


def test_invalid_runtime_fails_fast(monkeypatch):
    monkeypatch.setitem(
        SCENARIOS,
        "broken-scenario",
        {
            "slug": "broken-scenario",
            "runtime": {"provisioner": "missing"},
            "evaluation": {
                "checks": [
                    {
                        "type": "scalar_equals",
                        "name": "placeholder",
                        "sql": "SELECT 1",
                        "expected": 1,
                        "points": 100,
                    }
                ]
            },
        },
    )

    with pytest.raises(ScenarioConfigurationError):
        get_scenario_runtime("broken-scenario")


def test_invalid_evaluation_fails_catalog_validation(monkeypatch):
    monkeypatch.setitem(
        SCENARIOS,
        "broken-evaluation",
        {
            "slug": "broken-evaluation",
            "runtime": {"provisioner": "slow_checkout"},
            "evaluation": {
                "checks": [
                    {
                        "type": "scalar_equals",
                        "name": "underweighted",
                        "sql": "SELECT 1",
                        "expected": 1,
                        "points": 10,
                    }
                ]
            },
        },
    )

    with pytest.raises(EvaluationConfigurationError):
        validate_scenario_catalog()
