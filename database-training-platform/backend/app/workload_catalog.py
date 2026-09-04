import json
import re
from pathlib import Path


_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


class WorkloadCatalogError(RuntimeError):
    pass


WORKLOAD_DIRECTORY = Path(__file__).resolve().parent.parent / "workloads"


def load_workloads(directory: Path = WORKLOAD_DIRECTORY) -> dict[str, dict]:
    if not directory.exists() or not directory.is_dir():
        raise WorkloadCatalogError(f"Workload directory does not exist: {directory}")

    workloads: dict[str, dict] = {}
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise WorkloadCatalogError(f"No workload JSON files found in {directory}")

    for path in paths:
        try:
            workload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise WorkloadCatalogError(
                f"Invalid JSON in workload file {path.name}: {exc}"
            ) from exc

        if not isinstance(workload, dict):
            raise WorkloadCatalogError(f"Workload file {path.name} must contain an object")

        slug = workload.get("slug")
        version = workload.get("version")
        statements = workload.get("statements")

        if not isinstance(slug, str) or not slug.strip():
            raise WorkloadCatalogError(f"Workload file {path.name} is missing a slug")
        if path.stem != slug:
            raise WorkloadCatalogError(f"Workload file {path.name} must match slug {slug!r}")
        if slug in workloads:
            raise WorkloadCatalogError(f"Duplicate workload slug: {slug}")
        if not isinstance(version, str) or not _SEMVER.fullmatch(version):
            raise WorkloadCatalogError(
                f"Workload {slug!r} version must use MAJOR.MINOR.PATCH"
            )
        if not isinstance(statements, dict) or not statements:
            raise WorkloadCatalogError(f"Workload {slug!r} requires named statements")
        for name, sql in statements.items():
            if not isinstance(name, str) or not name.strip():
                raise WorkloadCatalogError(f"Workload {slug!r} has an invalid statement name")
            if not isinstance(sql, str) or not sql.strip():
                raise WorkloadCatalogError(
                    f"Workload {slug!r} statement {name!r} must contain SQL"
                )

        workloads[slug] = workload

    return workloads


WORKLOADS = load_workloads()
