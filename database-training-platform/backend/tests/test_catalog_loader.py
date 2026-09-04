import json

import pytest

from app.catalog import ScenarioCatalogError, load_scenarios


def test_loader_discovers_json_scenarios(tmp_path):
    scenario = {"slug": "example-scenario", "provisioning": {}, "evaluation": {}}
    (tmp_path / "example-scenario.json").write_text(
        json.dumps(scenario), encoding="utf-8"
    )

    loaded = load_scenarios(tmp_path)
    assert loaded == {"example-scenario": scenario}


def test_loader_rejects_filename_slug_mismatch(tmp_path):
    (tmp_path / "wrong-name.json").write_text(
        json.dumps({"slug": "actual-slug"}), encoding="utf-8"
    )

    with pytest.raises(ScenarioCatalogError, match="must match slug"):
        load_scenarios(tmp_path)


def test_loader_rejects_invalid_json(tmp_path):
    (tmp_path / "broken.json").write_text("{not-json", encoding="utf-8")

    with pytest.raises(ScenarioCatalogError, match="Invalid JSON"):
        load_scenarios(tmp_path)


def test_loader_rejects_empty_directory(tmp_path):
    with pytest.raises(ScenarioCatalogError, match="No scenario JSON files"):
        load_scenarios(tmp_path)
