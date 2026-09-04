import pytest

from app.catalog import SCENARIOS
from app.evaluation_engine import EvaluationConfigurationError
from app.provisioning_engine import ProvisioningConfigurationError
from app.scenario_engine import (
    ScenarioConfigurationError,
    get_scenario_definition,
    validate_scenario_catalog,
)


def test_every_catalog_scenario_has_valid_provisioning_and_evaluation():
    validate_scenario_catalog()

    for slug, scenario in SCENARIOS.items():
        assert get_scenario_definition(slug) is scenario
        assert "provisioning" in scenario
        assert "evaluation" in scenario


def test_unknown_scenario_raises_key_error():
    with pytest.raises(KeyError):
        get_scenario_definition("does-not-exist")


def test_missing_provisioning_fails_catalog_validation(monkeypatch):
    monkeypatch.setitem(
        SCENARIOS,
        "broken-scenario",
        {
            "slug": "broken-scenario",
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
        validate_scenario_catalog()


def test_invalid_provisioning_fails_catalog_validation(monkeypatch):
    monkeypatch.setitem(
        SCENARIOS,
        "broken-provisioning",
        {
            "slug": "broken-provisioning",
            "provisioning": {
                "setup_sql": ["SELECT 1"],
                "roles": [],
                "faults": [
                    {
                        "type": "connection_pool",
                        "role": "missing",
                        "count": 2,
                    }
                ],
            },
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

    with pytest.raises(ProvisioningConfigurationError):
        validate_scenario_catalog()


def test_invalid_evaluation_fails_catalog_validation(monkeypatch):
    monkeypatch.setitem(
        SCENARIOS,
        "broken-evaluation",
        {
            "slug": "broken-evaluation",
            "provisioning": {"setup_sql": ["SELECT 1"], "roles": [], "faults": []},
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
