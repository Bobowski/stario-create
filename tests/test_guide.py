import ast
import re
import subprocess
import sys

import pytest

from stario_create.data import guide_text, skill_text

PROFILES = ["app", "api"]


def _python_blocks(text: str) -> list[str]:
    return re.findall(r"```python\n(.*?)```", text, re.S)


@pytest.mark.parametrize("profile", PROFILES)
def test_guide_fits_rule_loader_budget(profile):
    # Rule loaders (Devin) cut always-on rules at 16 KB, and each app's
    # `## This app` notes must still fit inside that limit.
    assert len(guide_text(profile).encode()) <= 12_000


@pytest.mark.parametrize("profile", PROFILES)
def test_guide_python_blocks_parse(profile):
    blocks = _python_blocks(guide_text(profile))
    assert profile == "api" or blocks
    for block in blocks:
        ast.parse(block)


@pytest.mark.parametrize("profile", PROFILES)
def test_guide_python_blocks_are_formatted(tmp_path, profile):
    copy = tmp_path / "AGENTS.md"
    copy.write_text(guide_text(profile))
    p = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--check",
            "--preview",
            "--line-length",
            "100",
            str(copy),
        ],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stdout + p.stderr


@pytest.mark.parametrize("profile", PROFILES)
def test_guide_ends_with_this_app_section(profile):
    assert guide_text(profile).rstrip().rsplit("## ", 1)[-1].startswith("This app")


def test_guide_proves_a_live_update_from_the_stream():
    text = guide_text()
    assert "timeout=2" in text
    assert "next SSE event" in text
    assert "Playwright" in text
    assert "stario-feature" in text


def test_feature_skill_checks_the_stream_then_playwright():
    text = skill_text("stario-feature")
    assert "timeout=2" in text
    assert "async_playwright" in text
    assert "playwright install chromium" in text
