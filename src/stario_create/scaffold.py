"""Write project files: the app skeleton and the agent files it keeps in sync.

Templates live in ``templates/`` as ``*.tmpl`` files so linters never see them.
``string.Template`` fills ``$app_name``. All writes are idempotent: a file that
already holds the target content counts as kept, not created.
"""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Iterable
from pathlib import Path
from string import Template

from stario_create.data import guide_text, resource, skill_names, template

STARIO_REQ = "stario>=5.1,<6"
DEV_REQS = ["ruff", "pyright", "pytest", "pytest-asyncio", "watchfiles"]

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_THIS_APP = "\n## This app"
_VENDOR = Path(__file__).resolve().parent / "vendor"


class ScaffoldError(Exception):
    def __init__(self, code: str, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.hint = hint


def check_name(name: str) -> None:
    if not NAME_RE.fullmatch(name):
        raise ScaffoldError(
            "bad-name",
            f"'{name}' is not a valid feature name",
            "use lowercase snake_case, e.g. my_board",
        )


def _write(path: Path, text: str, created: list[str], *, force: bool = False) -> None:
    if path.exists():
        if path.read_text() == text:
            return
        if not force:
            raise ScaffoldError(
                "exists",
                f"{path} exists with different content",
                "pass --force to overwrite",
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    created.append(str(path))


def _fill(name: str, **subs: str) -> str:
    return Template(template(name).read_text()).safe_substitute(subs)


def scaffold_files(root: Path, app_name: str, *, force: bool = False) -> list[str]:
    """Write the app tree under root. Returns the files written."""
    created: list[str] = []

    def w(rel: str, text: str) -> None:
        _write(root / rel, text, created, force=force)

    w("app/__init__.py", "")
    w("app/config.py", _fill("app/config.py.tmpl", app_name=app_name))
    w("app/assets.py", _fill("app/assets.py.tmpl"))
    w("app/common/__init__.py", "")
    w("app/common/shell.py", _fill("app/common/shell.py.tmpl"))
    w("app/features/__init__.py", "")
    w("app/features/home/__init__.py", "")
    w("app/features/home/urls.py", _fill("app/features/home/urls.py.tmpl"))
    w("app/features/home/views.py", _fill("app/features/home/views.py.tmpl"))
    w("app/features/home/handlers.py", _fill("app/features/home/handlers.py.tmpl"))
    w("app/main.py", _fill("app/main.py.tmpl"))
    w("static/css/style.css", _fill("app/style.css.tmpl"))

    target = root / "static/js/datastar.js"
    if not target.exists() or force:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_VENDOR / "datastar.js", target)
        created.append(str(target))

    w("tests/__init__.py", "")
    w("tests/conftest.py", _fill("tests/conftest.py.tmpl"))
    w("tests/test_home.py", _fill("tests/test_home.py.tmpl"))

    w("justfile", template("justfile").read_text())

    guide = sync_guide(root, force=force)
    if guide is not None:
        created.append(guide)
    created.extend(sync_skill_files(root, force=force))

    _append_once(root / ".gitignore", "*.sqlite3*", created)
    _append_pyproject_extras(root / "pyproject.toml", created)
    return created


def link_skills(root: Path, names: Iterable[str], *, force: bool = False) -> list[str]:
    """Link .claude/skills/<name> to the copy in .agents/skills/.

    Claude Code reads skills from .claude/skills/ only. A symlink keeps one
    canonical copy; when os.symlink is unavailable the skill dir is copied.
    Returns the destination paths written.
    """
    linked: list[str] = []
    for name in names:
        dest = root / ".claude" / "skills" / name
        target = os.path.join("..", "..", ".agents", "skills", name)
        if dest.is_symlink():
            if os.readlink(dest) == target:
                continue
            dest.unlink()
        elif dest.exists():
            if not force:
                continue
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(target, dest, target_is_directory=True)
        except OSError:
            shutil.copytree(root / ".agents" / "skills" / name, dest)
        linked.append(str(dest))
    return linked


def _append_once(path: Path, line: str, created: list[str]) -> None:
    if path.exists() and line in path.read_text().splitlines():
        return
    with path.open("a") as f:
        f.write(line + "\n")
    created.append(str(path))


def _append_pyproject_extras(path: Path, created: list[str]) -> None:
    if not path.exists():
        return
    if "[tool.pyright]" in path.read_text():
        return
    with path.open("a") as f:
        f.write(template("pyproject_extras.toml").read_text())
    created.append(str(path))


def sync_guide(root: Path, *, force: bool = False) -> str | None:
    """Write the bundled guide to AGENTS.md. Returns the path, or None if current.

    An existing file keeps everything from its `## This app` heading on. A file
    without that section needs `force`.
    """
    path = root / "AGENTS.md"
    bundled = guide_text()
    if path.exists():
        text = path.read_text()
        if _THIS_APP in text:
            target = bundled.split(_THIS_APP)[0] + _THIS_APP + text.split(_THIS_APP, 1)[1]
        elif force:
            target = bundled
        else:
            raise ScaffoldError(
                "no-this-app",
                "AGENTS.md has no '## This app' section",
                "pass --force to overwrite the whole file",
            )
        if text == target:
            return None
    else:
        target = bundled
    path.write_text(target)
    return str(path)


def sync_skill_files(root: Path, *, force: bool = False) -> list[str]:
    """Copy bundled skills to .agents/skills/ and link them from .claude/skills/."""
    written: list[str] = []
    for name in skill_names():
        dest = root / ".agents" / "skills" / name / "SKILL.md"
        text = resource(f"skills/{name}/SKILL.md").read_text()
        if dest.is_file() and dest.read_text() == text:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
        written.append(str(dest))
    written.extend(link_skills(root, skill_names(), force=force))
    return written


def stale_files(root: Path) -> list[str]:
    """Paths that differ from the bundle. Empty means the app is in sync."""
    stale: list[str] = []
    bundled_head = guide_text().split(_THIS_APP)[0].strip()
    path = root / "AGENTS.md"
    local_head = path.read_text().split(_THIS_APP)[0].strip() if path.exists() else ""
    if local_head != bundled_head:
        stale.append("AGENTS.md")
    for name in skill_names():
        dest = root / ".agents" / "skills" / name / "SKILL.md"
        if (
            not dest.is_file()
            or dest.read_text() != resource(f"skills/{name}/SKILL.md").read_text()
        ):
            stale.append(f".agents/skills/{name}/SKILL.md")
        link = root / ".claude" / "skills" / name
        if not link.is_symlink() or os.readlink(link) != os.path.join(
            "..", "..", ".agents", "skills", name
        ):
            stale.append(f".claude/skills/{name}")
    return stale
