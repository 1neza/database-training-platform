import json

import pytest

from app.dataset_catalog import DatasetCatalogError, load_datasets


def test_dataset_loader_reads_versioned_template(tmp_path):
    path = tmp_path / "demo.json"
    path.write_text(
        json.dumps(
            {
                "slug": "demo",
                "version": "1.2.3",
                "description": "Fixture dataset",
                "setup_sql": ["CREATE TABLE demo(id integer primary key)"],
            }
        ),
        encoding="utf-8",
    )

    datasets = load_datasets(tmp_path)
    assert datasets["demo"]["version"] == "1.2.3"


def test_dataset_loader_rejects_bad_version(tmp_path):
    path = tmp_path / "demo.json"
    path.write_text(
        json.dumps(
            {
                "slug": "demo",
                "version": "v1",
                "setup_sql": ["SELECT 1"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(DatasetCatalogError, match="MAJOR.MINOR.PATCH"):
        load_datasets(tmp_path)


def test_dataset_loader_rejects_filename_slug_mismatch(tmp_path):
    path = tmp_path / "wrong-name.json"
    path.write_text(
        json.dumps(
            {
                "slug": "demo",
                "version": "1.0.0",
                "setup_sql": ["SELECT 1"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(DatasetCatalogError, match="must match slug"):
        load_datasets(tmp_path)
