import subprocess
import sys
import tempfile
from pathlib import Path

from stario_create.data import guide_text, skill_names, template
from stario_create.scaffold import scaffold_files

CLI = [sys.executable, "-m", "stario_create.cli"]


def _compile_dir(root: Path) -> list[str]:
    """Compile every .py under root. Returns file names that fail."""
    bad = []
    for py in root.rglob("*.py"):
        try:
            compile(py.read_text(), str(py), "exec")
        except SyntaxError:
            bad.append(str(py))
    return bad


def test_justfile_template_lists_recipes():
    text = template("justfile").read_text()
    for name in ("dev", "serve", "check", "fix", "test"):
        assert f"\n{name}:" in text
    assert "set dotenv-load := true" in text
    assert "uv run watchfiles" in text
    assert "uv run pytest" in text


def test_scaffold_files_compile(tmp_path: Path):
    created = scaffold_files(tmp_path, "demo")
    assert "app/main.py" in {str(Path(p).relative_to(tmp_path)) for p in created}
    assert _compile_dir(tmp_path) == []
    assert (tmp_path / "AGENTS.md").read_text() == guide_text()
    assert not (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / "static/js/datastar.js").exists()
    assert "*.sqlite3*" in (tmp_path / ".gitignore").read_text()
    justfile = (tmp_path / "justfile").read_text()
    assert "\ndev:" in justfile
    assert "\ncheck:" in justfile
    for skill in skill_names():
        skill_md = tmp_path / ".agents/skills" / skill / "SKILL.md"
        assert skill_md.exists()
        link = tmp_path / ".claude/skills" / skill
        assert link.is_symlink()
        assert (link / "SKILL.md").read_text() == skill_md.read_text()


def test_scaffold_is_idempotent(tmp_path: Path):
    scaffold_files(tmp_path, "demo")
    assert scaffold_files(tmp_path, "demo") == []


def test_cli_version():
    out = subprocess.run([*CLI, "--version"], capture_output=True, text=True)
    assert out.returncode == 0
    assert out.stdout.startswith("stario-create ")
    assert "(stario 5)" in out.stdout


def test_cli_error_text():
    with tempfile.TemporaryDirectory() as d:
        out = subprocess.run([*CLI, "new", "Bad-Name", "--dir", d], capture_output=True, text=True)
    assert out.returncode == 1
    assert out.stderr.startswith("stario-create: ")
    assert "hint: " in out.stderr


def test_cli_sync_fresh_dir(tmp_path: Path):
    out = subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "AGENTS.md" in out.stdout
    assert (tmp_path / "AGENTS.md").read_text() == guide_text()
    for skill in skill_names():
        skill_md = tmp_path / ".agents/skills" / skill / "SKILL.md"
        assert skill_md.exists()
        link = tmp_path / ".claude/skills" / skill
        assert link.is_symlink()
        assert (link / "SKILL.md").read_text() == skill_md.read_text()
    again = subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    assert again.returncode == 0, again.stderr
    assert again.stdout.strip() == "up to date"


def test_cli_sync_preserves_this_app(tmp_path: Path):
    local = tmp_path / "AGENTS.md"
    local.write_text("OLD HEAD\n\n## This app\n\nkeep me\n")
    out = subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    text = local.read_text()
    assert text.split("\n## This app", 1)[1] == "\n\nkeep me\n"
    assert text.startswith(guide_text().split("## This app")[0][:50])


def test_cli_sync_refuses_without_this_app(tmp_path: Path):
    local = tmp_path / "AGENTS.md"
    local.write_text("no marker here\n")
    out = subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 1
    assert "stario-create:" in out.stderr
    assert "hint:" in out.stderr
    assert local.read_text() == "no marker here\n"
    forced = subprocess.run([*CLI, "sync", "--force"], cwd=tmp_path, capture_output=True, text=True)
    assert forced.returncode == 0, forced.stderr
    assert local.read_text() == guide_text()


def test_cli_sync_check(tmp_path: Path):
    out = subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    check = subprocess.run([*CLI, "sync", "--check"], cwd=tmp_path, capture_output=True, text=True)
    assert check.returncode == 0, check.stdout

    # Only '## This app' notes differ: still in sync.
    guide = tmp_path / "AGENTS.md"
    guide.write_text(guide.read_text() + "\nmy app notes\n")
    ok = subprocess.run([*CLI, "sync", "--check"], cwd=tmp_path, capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout


def test_cli_sync_check_detects_stale_skill(tmp_path: Path):
    subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    skill_md = tmp_path / ".agents/skills/stario-feature/SKILL.md"
    skill_md.write_text(skill_md.read_text() + "\nextra\n")
    out = subprocess.run([*CLI, "sync", "--check"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 1
    assert ".agents/skills/stario-feature/SKILL.md" in out.stdout


def test_cli_sync_check_detects_stale_guide(tmp_path: Path):
    subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    guide = tmp_path / "AGENTS.md"
    head, _, tail = guide.read_text().partition("\n## This app")
    guide.write_text(head + "\nstale line\n" + "\n## This app" + tail)
    out = subprocess.run([*CLI, "sync", "--check"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 1
    assert "AGENTS.md" in out.stdout


def test_cli_sync_check_detects_missing_link(tmp_path: Path):
    subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    (tmp_path / ".claude/skills/stario-auth").unlink()
    out = subprocess.run([*CLI, "sync", "--check"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 1
    assert ".claude/skills/stario-auth" in out.stdout
