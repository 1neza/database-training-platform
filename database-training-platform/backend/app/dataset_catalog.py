import json
import re
from pathlib import Path


_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


class DatasetCatalogError(RuntimeError):
    pass


DATASET_DIRECTORY = Path(__file__).resolve().parent.parent / "datasets"


def load_datasets(directory: Path = DATASET_DIRECTORY) -> dict[str, dict]:
    if not directory.exists() or not directory.is_dir():
        raise DatasetCatalogError(f"Dataset directory does not exist: {directory}")

    datasets: dict[str, dict] = {}
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise DatasetCatalogError(f"No dataset JSON files found in {directory}")

    for path in paths:
        try:
            dataset = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DatasetCatalogError(
                f"Invalid JSON in dataset file {path.name}: {exc}"
            ) from exc

        if not isinstance(dataset, dict):
            raise DatasetCatalogError(f"Dataset file {path.name} must contain an object")

        slug = dataset.get("slug")
        version = dataset.get("version")
        setup_sql = dataset.get("setup_sql")

        if not isinstance(slug, str) or not slug.strip():
            raise DatasetCatalogError(f"Dataset file {path.name} is missing a slug")
        if path.stem != slug:
            raise DatasetCatalogError(f"Dataset file {path.name} must match slug {slug!r}")
        if slug in datasets:
            raise DatasetCatalogError(f"Duplicate dataset slug: {slug}")
        if not isinstance(version, str) or not _SEMVER.fullmatch(version):
            raise DatasetCatalogError(
                f"Dataset {slug!r} version must use MAJOR.MINOR.PATCH"
            )
        if not isinstance(setup_sql, list) or not setup_sql:
            raise DatasetCatalogError(f"Dataset {slug!r} requires non-empty setup_sql")
        if any(not isinstance(sql, str) or not sql.strip() for sql in setup_sql):
            raise DatasetCatalogError(
                f"Dataset {slug!r} setup_sql entries must be non-empty strings"
            )

        datasets[slug] = dataset

    return datasets


DATASETS = load_datasets()
