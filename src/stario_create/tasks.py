"""Dev task table. One source feeds the generated justfile and the CLI.

Each task is a list of commands run in order at the project root. Recipes in
the justfile carry the same strings, so `just check` and
`stario-create check` do the same thing and a project never depends on this
tool being installed.
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Task:
    doc: str
    commands: tuple[tuple[str, ...], ...]


TASKS: dict[str, Task] = {
    "dev": Task(
        "run the app with hot reload",
        # `python`, not `uv run python`: the app must be watchfiles' direct
        # child. A nested `uv run` wrapper swallows watchfiles' kill and
        # leaves an orphan that holds the litewriter claim forever.
        (("uv", "run", "watchfiles", "python -m app.main", "app/", "static/"),),
    ),
    "serve": Task(
        "run the app once, no reload",
        (("uv", "run", "python", "-m", "app.main"),),
    ),
    "check": Task(
        "lint, typecheck, test - run before done",
        (
            ("uv", "run", "ruff", "check", "."),
            ("uv", "run", "ruff", "format", "--check", "."),
            ("uv", "run", "pyright"),
            ("uv", "run", "pytest", "-q"),
        ),
    ),
    "fix": Task(
        "auto-fix lint and format",
        (
            ("uv", "run", "ruff", "check", "--fix", "."),
            ("uv", "run", "ruff", "format", "."),
        ),
    ),
    "test": Task(
        "run the tests",
        (("uv", "run", "pytest", "-q"),),
    ),
}


def render_justfile() -> str:
    """The generated justfile. Comments become `just --list` documentation."""
    lines = [
        "# `just` lists the targets. Install: uv tool install rust-just",
        "",
    ]
    for name, task in TASKS.items():
        lines.append(f"# {task.doc}")
        lines.append(f"{name}:")
        for command in task.commands:
            lines.append(f"    {shlex.join(command)}")
        lines.append("")
    return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class TaskStep:
    command: str
    ok: bool
    output: str


_STREAMING = {"dev", "serve"}


def run_task(name: str, cwd: str = ".") -> list[TaskStep]:
    """Run every command of a task in order. Never raises on a failed step.

    `dev` and `serve` are long-running: their output streams to the terminal
    instead of being captured.
    """
    task = TASKS[name]
    stream = name in _STREAMING
    steps: list[TaskStep] = []
    for command in task.commands:
        proc = subprocess.run(
            list(command),
            cwd=cwd,
            capture_output=not stream,
            text=True,
            check=False,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        steps.append(TaskStep(shlex.join(command), proc.returncode == 0, output))
        if proc.returncode != 0 and name != "check":
            # A failing dev server or fix step stops the task. `check` runs all
            # steps so one report covers lint, types, and tests together.
            break
    return steps
