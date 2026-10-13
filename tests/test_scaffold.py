import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from stario_create.data import guide_text, skill_names
from stario_create.scaffold import (
    ScaffoldError,
    _pascal,
    register_screen,
    scaffold_files,
    screen_files,
)
from stario_create.tasks import TASKS, render_justfile

CLI = [sys.executable, "-m", "stario_create.cli"]


def _subs(screen: str) -> dict[str, str]:
    return {
        "screen": screen,
        "Screen": _pascal(screen),
        "SCREEN": screen.upper(),
        "path": screen.replace("_", "-"),
        "title": _pascal(screen),
    }


def _compile_dir(root: Path) -> list[str]:
    """Compile every .py under root. Returns file names that fail."""
    bad = []
    for py in root.rglob("*.py"):
        try:
            compile(py.read_text(), str(py), "exec")
        except SyntaxError:
            bad.append(str(py))
    return bad


def test_justfile_lists_tasks():
    text = render_justfile()
    for name in TASKS:
        assert f"{name}:" in text
    assert "uv run watchfiles" in text
    assert "uv run pytest" in text


def test_scaffold_files_compile(tmp_path: Path):
    created = scaffold_files(tmp_path, "demo")
    assert "app/main.py" in {str(Path(p).relative_to(tmp_path)) for p in created}
    assert _compile_dir(tmp_path) == []
    assert (tmp_path / "AGENTS.md").read_text() == guide_text()
    assert (tmp_path / "CLAUDE.md").read_text() == "@AGENTS.md\n"
    assert (tmp_path / "static/js/datastar.js").exists()
    assert "*.sqlite3*" in (tmp_path / ".gitignore").read_text()
    for skill in skill_names():
        assert (tmp_path / ".agents/skills" / skill / "SKILL.md").exists()


def test_scaffold_is_idempotent(tmp_path: Path):
    scaffold_files(tmp_path, "demo")
    assert scaffold_files(tmp_path, "demo") == []


def test_screen_static(tmp_path: Path):
    scaffold_files(tmp_path, "demo")
    created = screen_files(tmp_path, "settings")
    assert register_screen(tmp_path, "settings", live=False) == []
    assert _compile_dir(tmp_path) == []
    main = (tmp_path / "app/main.py").read_text()
    assert "register_settings(app)" in main
    assert "from app.features.settings.handlers import register_settings" in main
    assert any("settings/urls.py" in p for p in created)


def test_screen_live(tmp_path: Path):
    scaffold_files(tmp_path, "demo")
    screen_files(tmp_path, "notes", live=True)
    assert register_screen(tmp_path, "notes", live=True) == []
    assert _compile_dir(tmp_path) == []
    main = (tmp_path / "app/main.py").read_text()
    assert "import sqlite3" in main
    assert "Relay" in main
    assert "conn.executescript(notes_data.SCHEMA)" in main
    assert "register_notes(app, conn, relay)" in main
    assert "conn.close()" in main
    assert (tmp_path / "app/features/notes/data.py").exists()


def test_screen_refuses_existing(tmp_path: Path):
    scaffold_files(tmp_path, "demo")
    screen_files(tmp_path, "settings")
    with pytest.raises(ScaffoldError):
        screen_files(tmp_path, "settings")


def test_register_screen_missing_main(tmp_path: Path):
    (tmp_path / "app/features/x").mkdir(parents=True)
    with pytest.raises(ScaffoldError):
        register_screen(tmp_path, "x", live=False)


def test_cli_version_json():
    out = subprocess.run([*CLI, "--json", "version"], capture_output=True, text=True)
    assert out.returncode == 0
    payload = json.loads(out.stdout)
    assert payload["ok"] is True
    assert payload["tracks_stario"] == "5"


def test_cli_skills_list():
    out = subprocess.run([*CLI, "--json", "skills"], capture_output=True, text=True)
    payload = json.loads(out.stdout)
    assert set(payload["skills"]) == {
        "stario-feature",
        "stario-auth",
        "stario-litewriter",
        "stario-tailwind-daisyui",
    }


def test_cli_error_json():
    with tempfile.TemporaryDirectory() as d:
        out = subprocess.run(
            [*CLI, "--json", "screen", "Bad-Name"], cwd=d, capture_output=True, text=True
        )
    assert out.returncode == 1
    payload = json.loads(out.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "bad-name"


def test_guide_write_preserves_this_app(tmp_path: Path):
    local = tmp_path / "AGENTS.md"
    local.write_text("OLD HEAD\n\n## This app\n\nkeep me\n")
    out = subprocess.run(
        [*CLI, "--json", "guide", "--write"], cwd=tmp_path, capture_output=True, text=True
    )
    assert out.returncode == 0, out.stderr
    text = local.read_text()
    assert "keep me" in text
    assert text.startswith(guide_text().split("## This app")[0][:50])


def test_guide_check_detects_stale(tmp_path: Path):
    (tmp_path / "AGENTS.md").write_text("stale\n\n## This app\n\nmine\n")
    out = subprocess.run(
        [*CLI, "--json", "guide", "--check"], cwd=tmp_path, capture_output=True, text=True
    )
    assert out.returncode == 1
    assert json.loads(out.stdout)["current"] is False
