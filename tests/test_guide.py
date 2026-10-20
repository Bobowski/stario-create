import ast
import re
import subprocess
import sys

from stario_create.data import guide_text


def _python_blocks(text: str) -> list[str]:
    return re.findall(r"```python\n(.*?)```", text, re.S)


def test_guide_fits_rule_loader_budget():
    # Rule loaders (Devin) cut always-on rules at 16 KB, and each app's
    # `## This app` notes must still fit inside that limit.
    assert len(guide_text().encode()) <= 12_000


def test_guide_python_blocks_parse():
    blocks = _python_blocks(guide_text())
    assert blocks
    for block in blocks:
        ast.parse(block)


def test_guide_python_blocks_are_formatted(tmp_path):
    copy = tmp_path / "AGENTS.md"
    copy.write_text(guide_text())
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


def test_guide_ends_with_this_app_section():
    assert guide_text().rstrip().rsplit("## ", 1)[-1].startswith("This app")
