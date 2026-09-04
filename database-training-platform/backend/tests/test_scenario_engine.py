import copy

import pytest

from app.catalog import SCENARIOS
from app.evaluation_engine import EvaluationConfigurationError
from app.provisioning_engine import ProvisioningConfigurationError
from app.scenario_engine import (
    ScenarioConfigurationError,
    get_scenario_definition,
    validate_scenario_catalog,
)


def _valid_scenario(slug: str) -> dict:
    return {
        "slug": slug,
        "version": "1.0.0",
        "track_slug": "postgresql-dba",
        "title": "Validation Fixture",
        "level": "beginner",
        "difficulty": 2,
        "skills": ["postgresql.safe-operations"],
        "prerequisites": [],
        "duration_minutes": 10,
        "summary": "A valid scenario used by validation tests.",
        "incident": "A database incident needs investigation.",
        "objectives": ["Diagnose the issue."],
        "hints": ["Inspect PostgreSQL state."],
        "provisioning": {
            "setup_sql": ["SELECT 1"],
            "roles": [],
            "faults": [],
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
    }


def test_every_catalog_scenario_has_valid_metadata_provisioning_and_evaluation():
    validate_scenario_catalog()

    for slug, scenario in SCENARIOS.items():
        assert get_scenario_definition(slug) is scenario
        assert "version" in scenario
        assert 1 <= scenario["difficulty"] <= 5
        assert scenario["skills"]
        assert "prerequisites" in scenario
        assert "provisioning" in scenario
        assert "evaluation" in scenario


def test_unknown_scenario_raises_key_error():
    with pytest.raises(KeyError):
        get_scenario_definition("does-not-exist")


def test_invalid_metadata_fails_catalog_validation(monkeypatch):
    scenario = _valid_scenario("broken-metadata")
    scenario["duration_minutes"] = 0
    monkeypatch.setitem(SCENARIOS, scenario["slug"], scenario)

    with pytest.raises(ScenarioConfigurationError, match="duration_minutes"):
        validate_scenario_catalog()


def test_invalid_version_fails_catalog_validation(monkeypatch):
    scenario = _valid_scenario("broken-version")
    scenario["version"] = "v1"
    monkeypatch.setitem(SCENARIOS, scenario["slug"], scenario)

    with pytest.raises(ScenarioConfigurationError, match="MAJOR.MINOR.PATCH"):
        validate_scenario_catalog()


def test_invalid_difficulty_fails_catalog_validation(monkeypatch):
    scenario = _valid_scenario("broken-difficulty")
    scenario["difficulty"] = 6
    monkeypatch.setitem(SCENARIOS, scenario["slug"], scenario)

    with pytest.raises(ScenarioConfigurationError, match="difficulty"):
        validate_scenario_catalog()


def test_unknown_track_fails_catalog_validation(monkeypatch):
    scenario = _valid_scenario("broken-track")
    scenario["track_slug"] = "missing-track"
    monkeypatch.setitem(SCENARIOS, scenario["slug"], scenario)

    with pytest.raises(ScenarioConfigurationError, match="unknown track"):
        validate_scenario_catalog()


def test_unknown_skill_fails_catalog_validation(monkeypatch):
    scenario = _valid_scenario("broken-skill")
    scenario["skills"] = ["postgresql.not-real"]
    monkeypatch.setitem(SCENARIOS, scenario["slug"], scenario)

    with pytest.raises(ScenarioConfigurationError, match="unknown skill"):
        validate_scenario_catalog()


def test_unknown_prerequisite_skill_fails_catalog_validation(monkeypatch):
    scenario = _valid_scenario("broken-prerequisite")
    scenario["prerequisites"] = ["postgresql.not-real"]
    monkeypatch.setitem(SCENARIOS, scenario["slug"], scenario)

    with pytest.raises(ScenarioConfigurationError, match="unknown prerequisite skill"):
        validate_scenario_catalog()


def test_missing_provisioning_fails_catalog_validation(monkeypatch):
    scenario = _valid_scenario("broken-scenario")
    del scenario["provisioning"]
    monkeypatch.setitem(SCENARIOS, scenario["slug"], scenario)

    with pytest.raises(ScenarioConfigurationError, match="provisioning"):
        validate_scenario_catalog()


def test_invalid_provisioning_fails_catalog_validation(monkeypatch):
    scenario = _valid_scenario("broken-provisioning")
    scenario["provisioning"]["faults"] = [
        {
            "type": "connection_pool",
            "role": "missing",
            "count": 2,
        }
    ]
    monkeypatch.setitem(SCENARIOS, scenario["slug"], scenario)

    with pytest.raises(ProvisioningConfigurationError):
        validate_scenario_catalog()


def test_invalid_evaluation_fails_catalog_validation(monkeypatch):
    scenario = copy.deepcopy(_valid_scenario("broken-evaluation"))
    scenario["evaluation"]["checks"][0]["points"] = 10
    monkeypatch.setitem(SCENARIOS, scenario["slug"], scenario)

    with pytest.raises(EvaluationConfigurationError):
        validate_scenario_catalog()
