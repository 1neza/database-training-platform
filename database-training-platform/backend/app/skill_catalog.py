import json
import re
from pathlib import Path


_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
SKILL_DIRECTORY = Path(__file__).resolve().parent.parent / "skills"


class SkillCatalogError(RuntimeError):
    pass


def load_skill_catalog(directory: Path = SKILL_DIRECTORY) -> dict[str, dict]:
    if not directory.exists() or not directory.is_dir():
        raise SkillCatalogError(f"Skill directory does not exist: {directory}")

    skills: dict[str, dict] = {}
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise SkillCatalogError(f"No skill catalog JSON files found in {directory}")

    for path in paths:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SkillCatalogError(f"Invalid JSON in skill file {path.name}: {exc}") from exc

        if not isinstance(document, dict):
            raise SkillCatalogError(f"Skill file {path.name} must contain an object")
        track_slug = document.get("track_slug")
        version = document.get("version")
        entries = document.get("skills")
        if not isinstance(track_slug, str) or not track_slug.strip():
            raise SkillCatalogError(f"Skill file {path.name} requires track_slug")
        if not isinstance(version, str) or not _SEMVER.match(version):
            raise SkillCatalogError(f"Skill file {path.name} requires semantic version")
        if not isinstance(entries, list) or not entries:
            raise SkillCatalogError(f"Skill file {path.name} requires a non-empty skills list")

        for entry in entries:
            if not isinstance(entry, dict):
                raise SkillCatalogError(f"Skill entries in {path.name} must be objects")
            slug = entry.get("slug")
            name = entry.get("name")
            description = entry.get("description")
            prerequisites = entry.get("prerequisites", [])
            if not isinstance(slug, str) or not slug.strip():
                raise SkillCatalogError(f"Skill in {path.name} is missing slug")
            if slug in skills:
                raise SkillCatalogError(f"Duplicate skill slug: {slug}")
            if not isinstance(name, str) or not name.strip():
                raise SkillCatalogError(f"Skill {slug!r} requires name")
            if not isinstance(description, str) or not description.strip():
                raise SkillCatalogError(f"Skill {slug!r} requires description")
            if not isinstance(prerequisites, list) or any(not isinstance(item, str) for item in prerequisites):
                raise SkillCatalogError(f"Skill {slug!r} prerequisites must be a string list")
            skills[slug] = {
                **entry,
                "track_slug": track_slug,
                "catalog_version": version,
            }

    for slug, skill in skills.items():
        for dependency in skill.get("prerequisites", []):
            if dependency not in skills:
                raise SkillCatalogError(f"Skill {slug!r} references unknown prerequisite {dependency!r}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(slug: str) -> None:
        if slug in visited:
            return
        if slug in visiting:
            raise SkillCatalogError(f"Skill prerequisite cycle detected at {slug!r}")
        visiting.add(slug)
        for dependency in skills[slug].get("prerequisites", []):
            visit(dependency)
        visiting.remove(slug)
        visited.add(slug)

    for slug in skills:
        visit(slug)

    return skills


SKILLS = load_skill_catalog()
