"""Write project files: the app skeleton, a new screen, agent files.

Templates live in ``templates/`` as ``*.tmpl`` files so linters never see them.
``string.Template`` fills ``$app_name`` / ``$screen`` / ``$Screen`` /
``$SCREEN`` / ``$path`` / ``$title``. All writes are idempotent: a file that
already holds the target content counts as kept, not created.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from string import Template

from stario_create.data import guide_text, resource, skill_names, template
from stario_create.tasks import render_justfile

STARIO_REQ = "stario>=5,<6"
DEV_REQS = ["ruff", "pyright", "pytest", "pytest-asyncio", "watchfiles"]

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
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


def _pascal(screen: str) -> str:
    return "".join(part.title() for part in screen.split("_"))


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

    w("justfile", render_justfile())
    w("CLAUDE.md", "@AGENTS.md\n")
    w("AGENTS.md", guide_text())

    for skill in skill_names():
        w(
            f".agents/skills/{skill}/SKILL.md",
            resource(f"skills/{skill}/SKILL.md").read_text(),
        )

    _append_once(root / ".gitignore", "*.sqlite3*", created)
    _append_pyproject_extras(root / "pyproject.toml", created)
    return created


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


def screen_files(root: Path, screen: str, *, live: bool = False, force: bool = False) -> list[str]:
    """Write one feature folder and its test. Returns the files written."""
    check_name(screen)
    feature = root / "app" / "features" / screen
    if feature.exists() and any(feature.iterdir()) and not force:
        raise ScaffoldError(
            "exists",
            f"app/features/{screen} already exists",
            "pass --force to overwrite",
        )
    subs = {
        "screen": screen,
        "Screen": _pascal(screen),
        "SCREEN": screen.upper(),
        "path": screen.replace("_", "-"),
        "title": _pascal(screen),
    }
    kind = "screen-live" if live else "screen"
    created: list[str] = []

    def w(rel: str, text: str) -> None:
        _write(root / rel, text, created, force=force)

    w(f"app/features/{screen}/__init__.py", "")
    w(f"app/features/{screen}/urls.py", _fill(f"{kind}/urls.py.tmpl", **subs))
    w(f"app/features/{screen}/views.py", _fill(f"{kind}/views.py.tmpl", **subs))
    w(f"app/features/{screen}/handlers.py", _fill(f"{kind}/handlers.py.tmpl", **subs))
    w(f"tests/test_{screen}.py", _fill(f"{kind}/test.py.tmpl", **subs))
    if live:
        w(f"app/features/{screen}/data.py", _fill("screen-live/data.py.tmpl", **subs))
    return created


def register_screen(root: Path, screen: str, *, live: bool) -> list[str]:
    """Patch app/main.py to wire the screen. Returns manual steps left over.

    Lines are inserted in plausible spots, then ruff sorts the imports. A
    main.py that does not match the scaffolded shape is left untouched and
    the steps come back as manual instructions.
    """
    main_py = root / "app" / "main.py"
    if not main_py.is_file():
        raise ScaffoldError("no-main", "app/main.py not found", "run from the project root")
    text = main_py.read_text()
    call = (
        f"register_{screen}(app, conn, relay)" if live else f"register_{screen}(app)"
    )
    if call in text:
        return []

    if "\n    yield" not in text:
        return [f"register the screen in bootstrap before yield: {call}"]

    # Imports land at the end of the import block; ruff sorts them after.
    head, _, rest = text.partition("\n\n")
    import_lines = [f"from app.features.{screen}.handlers import register_{screen}"]
    if live:
        import_lines.append(f"from app.features.{screen} import data as {screen}_data")
        if "import sqlite3" not in text:
            head = "import sqlite3\n" + head
        if ", Relay" not in head and "import Relay" not in head:
            head = head + "\nfrom stario import Relay"
    text = head + "\n" + "\n".join(import_lines) + "\n\n" + rest

    if live:
        if "sqlite3.connect(" not in text:
            text = text.replace(
                "config = Config.from_env()",
                "config = Config.from_env()\n    conn = sqlite3.connect(config.db_path)",
                1,
            )
        marker = f"conn.executescript({screen}_data.SCHEMA)"
        if marker not in text:
            text = text.replace(
                "sqlite3.connect(config.db_path)",
                f"sqlite3.connect(config.db_path)\n    {marker}",
                1,
            )
        if "Relay()" not in text:
            text = text.replace(
                "config = Config.from_env()",
                "config = Config.from_env()\n    relay: Relay[str] = Relay()",
                1,
            )
        if "conn.close()" not in text:
            text = text.replace("\n    yield", "\n    yield\n    conn.close()", 1)

    text = text.replace("\n    yield", f"\n    {call}\n    yield", 1)
    main_py.write_text(text)

    subprocess.run(
        ["uv", "run", "ruff", "check", "--fix", "--select", "I", "app/main.py"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    subprocess.run(
        ["uv", "run", "ruff", "format", "app/main.py"], cwd=root, capture_output=True, check=False
    )
    return []
