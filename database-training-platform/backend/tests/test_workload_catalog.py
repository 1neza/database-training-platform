import json

import pytest

from app.workload_catalog import WorkloadCatalogError, load_workloads


def test_workload_loader_reads_versioned_statements(tmp_path):
    path = tmp_path / "demo.json"
    path.write_text(
        json.dumps(
            {
                "slug": "demo",
                "version": "1.2.3",
                "description": "Fixture workload",
                "statements": {"lookup": "SELECT 1"},
            }
        ),
        encoding="utf-8",
    )

    workloads = load_workloads(tmp_path)
    assert workloads["demo"]["statements"]["lookup"] == "SELECT 1"


def test_workload_loader_rejects_bad_version(tmp_path):
    path = tmp_path / "demo.json"
    path.write_text(
        json.dumps(
            {
                "slug": "demo",
                "version": "latest",
                "statements": {"lookup": "SELECT 1"},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(WorkloadCatalogError, match="MAJOR.MINOR.PATCH"):
        load_workloads(tmp_path)


def test_workload_loader_rejects_empty_statements(tmp_path):
    path = tmp_path / "demo.json"
    path.write_text(
        json.dumps({"slug": "demo", "version": "1.0.0", "statements": {}}),
        encoding="utf-8",
    )

    with pytest.raises(WorkloadCatalogError, match="requires named statements"):
        load_workloads(tmp_path)
