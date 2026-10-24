import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from stario_create.data import guide_text, resource, skill_names, template
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
    for name in ("dev", "serve", "check", "fix", "test", "sync"):
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
    assert not (tmp_path / "Dockerfile").exists()
    assert (tmp_path / ".dockerignore").read_text() == template("dockerignore").read_text()
    env = (tmp_path / ".cursor/environment.json").read_text()
    assert "cloud-install.sh" in env
    assert "enable_testing" not in env
    install = (tmp_path / ".cursor/cloud-install.sh").read_text()
    assert "uv python install 3.14" in install
    assert "uv sync --all-groups --all-extras" in install
    assert "--locked" in install
    assert "just tailwind" in install
    assert "TAILWIND_VERSION" not in install
    for skill in skill_names():
        skill_md = tmp_path / ".agents/skills" / skill / "SKILL.md"
        assert skill_md.exists()
        link = tmp_path / ".claude/skills" / skill
        assert link.is_symlink()
        assert (link / "SKILL.md").read_text() == skill_md.read_text()


def test_scaffold_orjson_adds_the_codec(tmp_path: Path):
    scaffold_files(tmp_path, "demo", orjson=True)
    text = (tmp_path / "app/main.py").read_text()
    assert "import orjson" in text
    assert "from stario import App, Span, json, serve" in text
    assert "json.set_codec(orjson.dumps, orjson.loads)" in text
    assert _compile_dir(tmp_path) == []


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
    assert (tmp_path / ".cursor/environment.json").is_file()
    assert (tmp_path / ".cursor/cloud-install.sh").is_file()


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


def test_cli_sync_writes_missing_cloud_env(tmp_path: Path):
    subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    (tmp_path / ".cursor/environment.json").unlink()
    out = subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert ".cursor/environment.json" in out.stdout
    assert (tmp_path / ".cursor/environment.json").is_file()


def test_cli_sync_keeps_custom_cloud_env(tmp_path: Path):
    subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    custom = '{"snapshot": "keep-me", "enable_testing": false}\n'
    path = tmp_path / ".cursor/environment.json"
    path.write_text(custom)
    out = subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert path.read_text() == custom
    assert ".cursor/environment.json" not in out.stdout


def test_cli_sync_check_detects_missing_cloud_env(tmp_path: Path):
    subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    (tmp_path / ".cursor/cloud-install.sh").unlink()
    out = subprocess.run([*CLI, "sync", "--check"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 1
    assert ".cursor/cloud-install.sh" in out.stdout


def test_cli_sync_check_detects_missing_link(tmp_path: Path):
    subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    (tmp_path / ".claude/skills/stario-auth").unlink()
    out = subprocess.run([*CLI, "sync", "--check"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 1
    assert ".claude/skills/stario-auth" in out.stdout


def test_cli_sync_api_profile(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[tool.stario-create]\nprofile = "api"\n')
    local = tmp_path / "AGENTS.md"
    local.write_text("OLD HEAD\n\n## This app\n\nkeep me\n")
    for name in skill_names():
        skill_dir = tmp_path / ".agents/skills" / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("old skill\n")
        link_dir = tmp_path / ".claude/skills"
        link_dir.mkdir(parents=True, exist_ok=True)
        os.symlink(os.path.join("..", "..", ".agents", "skills", name), link_dir / name)
    custom = tmp_path / ".agents/skills/custom"
    custom.mkdir(parents=True)
    (custom / "SKILL.md").write_text("custom skill\n")

    out = subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    text = local.read_text()
    assert text.split("\n## This app", 1)[1] == "\n\nkeep me\n"
    assert text.startswith(guide_text("api").split("## This app")[0][:50])
    for name in skill_names():
        assert not (tmp_path / ".agents/skills" / name).exists()
        assert not (tmp_path / ".claude/skills" / name).exists()
        assert f"removed .agents/skills/{name}" in out.stdout
    assert (custom / "SKILL.md").read_text() == "custom skill\n"

    check = subprocess.run([*CLI, "sync", "--check"], cwd=tmp_path, capture_output=True, text=True)
    assert check.returncode == 0, check.stdout

    (tmp_path / ".agents/skills" / skill_names()[0]).mkdir(parents=True)
    out = subprocess.run([*CLI, "sync", "--check"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 1
    assert "(not in profile api)" in out.stdout


def test_cli_sync_bad_profile(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[tool.stario-create]\nprofile = "web"\n')
    out = subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 1
    assert "stario-create:" in out.stderr


def test_cli_sync_check_flags_ignored_files(tmp_path: Path):
    subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    (tmp_path / ".gitignore").write_text(".agents/\n")
    out = subprocess.run([*CLI, "sync", "--check"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 1
    for name in skill_names():
        assert f".agents/skills/{name}/SKILL.md (ignored by git)" in out.stdout
    assert "AGENTS.md (ignored by git)" not in out.stdout


def test_cli_sync_check_flags_justfile_without_pytest(tmp_path: Path):
    (tmp_path / "justfile").write_text("check:\n    uv run ruff check .\n    uv run pyright\n")
    out = subprocess.run([*CLI, "sync", "--check"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 1
    assert "justfile (check does not run pytest)" in out.stdout


def test_tailwind_recipe_parses(tmp_path: Path):
    just = shutil.which("just")
    if just is None:
        pytest.skip("just is not on PATH")
    text = resource("skills/stario-tailwind-daisyui/SKILL.md").read_text()
    block = re.search(r"```make\n(.*?)```", text, re.S)
    assert block is not None
    (tmp_path / "justfile").write_text(block.group(1))
    out = subprocess.run([just, "--summary"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    for name in ("tailwind", "css", "css-watch"):
        assert name in out.stdout.split()


def test_cli_sync_rewrites_cloud_install_keeps_environment(tmp_path: Path):
    subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    install = tmp_path / ".cursor/cloud-install.sh"
    install.write_text("# stale\n")
    env_path = tmp_path / ".cursor/environment.json"
    env_path.write_text('{"snapshot": "keep-me"}\n')

    out = subprocess.run([*CLI, "sync", "--check"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 1
    assert ".cursor/cloud-install.sh" in out.stdout

    out = subprocess.run([*CLI, "sync"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert install.read_text() == template("cursor/cloud-install.sh").read_text()
    assert ".cursor/cloud-install.sh" in out.stdout
    assert env_path.read_text() == '{"snapshot": "keep-me"}\n'
