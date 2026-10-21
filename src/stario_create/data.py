"""Bundled files: the guide, the skills, and the app templates.

Two layouts. In the repo (editable install, tests) the canonical files sit at
the repository root and in ``templates/`` next to this package. In an installed
wheel the root files live under ``stario_create/_data/`` (hatchling
force-include). ``resource()`` resolves both.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

_PACKAGE = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE.parents[1]  # src/stario_create -> repo root


def resource(name: str) -> Path:
    """Path to a bundled file: 'AGENTS.md', 'skills/stario-auth/SKILL.md'."""
    root_file = _REPO_ROOT / name
    if root_file.is_file():
        return root_file
    return Path(str(files("stario_create").joinpath("_data", name)))


def template(name: str) -> Path:
    """Path to a template file: 'app/main.py.tmpl', 'screen/urls.py.tmpl'."""
    return _PACKAGE / "templates" / name


def skill_names() -> list[str]:
    skills_dir = _REPO_ROOT / "skills"
    if not skills_dir.is_dir():
        skills_dir = Path(str(files("stario_create").joinpath("_data", "skills")))
    return sorted(entry.name for entry in skills_dir.iterdir() if (entry / "SKILL.md").is_file())


def skill_text(name: str) -> str:
    return resource(f"skills/{name}/SKILL.md").read_text()


def guide_text(profile: str = "app") -> str:
    """The bundled guide. The "api" profile ships a shorter JSON API guide."""
    return resource("AGENTS-api.md" if profile == "api" else "AGENTS.md").read_text()


def profile_skills(profile: str) -> list[str]:
    """Skill names the profile installs. The "api" profile ships none."""
    if profile == "api":
        return []
    return skill_names()
