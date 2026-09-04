import json
from pathlib import Path


TRACKS = [
    {
        "slug": "postgresql-dba",
        "name": "PostgreSQL DBA",
        "description": "Operate PostgreSQL like a production database administrator: performance, reliability, access, recovery and incident response.",
    },
    {
        "slug": "sql-performance",
        "name": "SQL Performance",
        "description": "Diagnose query plans, indexes, joins, cardinality and production SQL regressions.",
    },
    {
        "slug": "database-design",
        "name": "Database Design",
        "description": "Model scalable relational systems with constraints, indexing, partitioning and safe evolution.",
    },
]


class ScenarioCatalogError(RuntimeError):
    pass


SCENARIO_DIRECTORY = Path(__file__).resolve().parent.parent / "scenarios"


def load_scenarios(directory: Path = SCENARIO_DIRECTORY) -> dict[str, dict]:
    if not directory.exists() or not directory.is_dir():
        raise ScenarioCatalogError(f"Scenario directory does not exist: {directory}")

    scenarios: dict[str, dict] = {}
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise ScenarioCatalogError(f"No scenario JSON files found in {directory}")

    for path in paths:
        try:
            scenario = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ScenarioCatalogError(
                f"Invalid JSON in scenario file {path.name}: {exc}"
            ) from exc

        if not isinstance(scenario, dict):
            raise ScenarioCatalogError(f"Scenario file {path.name} must contain an object")

        slug = scenario.get("slug")
        if not isinstance(slug, str) or not slug.strip():
            raise ScenarioCatalogError(f"Scenario file {path.name} is missing a slug")
        if path.stem != slug:
            raise ScenarioCatalogError(
                f"Scenario file {path.name} must match slug {slug!r}"
            )
        if slug in scenarios:
            raise ScenarioCatalogError(f"Duplicate scenario slug: {slug}")

        scenarios[slug] = scenario

    return scenarios


SCENARIOS = load_scenarios()
