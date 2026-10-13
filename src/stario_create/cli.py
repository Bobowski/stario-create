"""stario-create command line.

Conventions (same as `yard`): writer commands take `--dry-run` and `--force`.
Output is text on a terminal and JSON when piped, with `--json` / `--text` to
force. Errors print `stario-create: <code>: <message>` to stderr and exit 1.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from stario_create import TRACKS_STARIO, __version__
from stario_create.data import guide_text, resource, skill_names
from stario_create.scaffold import (
    DEV_REQS,
    STARIO_REQ,
    ScaffoldError,
    check_name,
    register_screen,
    scaffold_files,
    screen_files,
)
from stario_create.tasks import TASKS, run_task

_THIS_APP = "## This app"


def _want_json(args: argparse.Namespace) -> bool:
    if getattr(args, "json", False):
        return True
    if getattr(args, "text", False):
        return False
    return not sys.stdout.isatty()


def _emit(args: argparse.Namespace, payload: dict[str, Any], text_lines: list[str]) -> None:
    if _want_json(args):
        print(json.dumps({"ok": True, **payload}, indent=2))
    else:
        for line in text_lines:
            print(line)


def _fail(args: argparse.Namespace, err: ScaffoldError) -> int:
    if _want_json(args):
        print(
            json.dumps(
                {"ok": False, "error": {"code": err.code, "message": str(err), "hint": err.hint}},
                indent=2,
            )
        )
    else:
        print(f"stario-create: {err.code}: {err}", file=sys.stderr)
        if err.hint:
            print(f"hint: {err.hint}", file=sys.stderr)
    return 1


def _run(argv: list[str], cwd: Path, *, dry: bool) -> None:
    if dry:
        return
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-3:]
        raise ScaffoldError(
            "command-failed",
            f"`{' '.join(argv)}` failed",
            "\n".join(tail) or f"exit {proc.returncode}",
        )


def _uv_init(dest: Path, *, dry: bool) -> None:
    if (dest / "pyproject.toml").exists():
        return
    _run(["uv", "init", "--app", "--python", "3.14", str(dest)], dest, dry=dry)


def _scaffold(args: argparse.Namespace, dest: Path, name: str) -> dict[str, Any]:
    check_name(name)
    dry = args.dry_run
    if (
        dest.exists()
        and any(dest.iterdir())
        and not dest.joinpath("pyproject.toml").exists()
        and not args.force
    ):
        raise ScaffoldError(
            "not-empty",
            f"{dest} is not empty and has no pyproject.toml",
            "pass --force to scaffold anyway",
        )
    if not dry:
        dest.mkdir(parents=True, exist_ok=True)

    _uv_init(dest, dry=dry)
    if not dry and (dest / "main.py").exists():
        (dest / "main.py").unlink()
    _run(["uv", "add", STARIO_REQ], dest, dry=dry)
    _run(["uv", "add", "--dev", *DEV_REQS], dest, dry=dry)

    created = scaffold_files(dest, name, force=args.force) if not dry else _planned_files()

    if not args.no_verify and not dry:
        for step in run_task("test", cwd=str(dest)):
            if not step.ok:
                raise ScaffoldError(
                    "verify-failed",
                    "the new app's tests failed",
                    step.output.strip() or step.command,
                )

    next_steps = [
        "just dev                     # http://127.0.0.1:8000, reloads on change",
        "just check                   # lint, types, tests — before done",
        "stario-create screen NAME --live   # add a live screen",
    ]
    return {
        "name": name,
        "path": str(dest),
        "created": created,
        "next": next_steps,
        "dry_run": dry,
    }


def _planned_files() -> list[str]:
    return [
        "app/__init__.py",
        "app/config.py",
        "app/assets.py",
        "app/common/__init__.py",
        "app/common/shell.py",
        "app/features/__init__.py",
        "app/features/home/__init__.py",
        "app/features/home/urls.py",
        "app/features/home/views.py",
        "app/features/home/handlers.py",
        "app/main.py",
        "static/css/style.css",
        "static/js/datastar.js",
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/test_home.py",
        "justfile",
        "CLAUDE.md",
        "AGENTS.md",
        *[f".agents/skills/{s}/SKILL.md" for s in skill_names()],
    ]


def cmd_new(args: argparse.Namespace) -> dict[str, Any]:
    base = Path(args.dir).expanduser() if args.dir else Path.cwd()
    return _scaffold(args, base / args.name, args.name)


def cmd_init(args: argparse.Namespace) -> dict[str, Any]:
    dest = Path.cwd()
    return _scaffold(args, dest, args.name or dest.name.replace("-", "_"))


def cmd_screen(args: argparse.Namespace) -> dict[str, Any]:
    root = Path.cwd()
    check_name(args.name)
    if not (root / "app").is_dir():
        raise ScaffoldError(
            "no-app", "no app/ directory here", "run from a stario app root, or `new` first"
        )
    files = [
        f"app/features/{args.name}/__init__.py",
        f"app/features/{args.name}/urls.py",
        f"app/features/{args.name}/views.py",
        f"app/features/{args.name}/handlers.py",
        f"tests/test_{args.name}.py",
        *(f"app/features/{args.name}/data.py" if args.live else ()),
    ]
    if args.dry_run:
        return {"screen": args.name, "live": args.live, "created": files, "dry_run": True}
    created = screen_files(root, args.name, live=args.live, force=args.force)
    manual = register_screen(root, args.name, live=args.live)
    return {
        "screen": args.name,
        "live": args.live,
        "created": created,
        "patched": "app/main.py" if not manual else None,
        "manual_steps": manual,
    }


def cmd_skills(args: argparse.Namespace) -> dict[str, Any]:
    if args.skills_command != "install":
        return {"skills": skill_names()}
    names = args.names or skill_names()
    unknown = [n for n in names if n not in skill_names()]
    if unknown:
        raise ScaffoldError(
            "unknown-skill",
            f"unknown skill(s): {', '.join(unknown)}",
            f"available: {', '.join(skill_names())}",
        )
    target = Path.cwd() / args.to / "skills"
    written: list[str] = []
    for name in names:
        dest = target / name / "SKILL.md"
        written.append(str(dest))
        if not args.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(resource(f"skills/{name}/SKILL.md").read_text())
    return {"installed": names, "to": str(target), "written": written, "dry_run": args.dry_run}


def cmd_guide(args: argparse.Namespace) -> dict[str, Any]:
    bundled = guide_text()
    path = Path.cwd() / "AGENTS.md"
    if args.check:
        head = bundled.split(_THIS_APP)[0].strip()
        local_head = path.read_text().split(_THIS_APP)[0].strip() if path.exists() else ""
        return {"current": local_head == head}
    if args.write:
        if path.exists() and _THIS_APP not in path.read_text() and not args.force:
            raise ScaffoldError(
                "no-this-app",
                "AGENTS.md has no '## This app' section",
                "pass --force to overwrite the whole file",
            )
        if not args.dry_run:
            if path.exists() and _THIS_APP in path.read_text():
                tail = path.read_text().split(_THIS_APP, 1)[1]
                path.write_text(bundled.split(_THIS_APP)[0] + _THIS_APP + tail)
            else:
                path.write_text(bundled)
        return {"written": str(path), "dry_run": args.dry_run}
    return {"guide": bundled}


def cmd_task(args: argparse.Namespace) -> dict[str, Any]:
    name = args.command
    steps = run_task(name, cwd=str(Path.cwd()))
    ok = all(s.ok for s in steps)
    payload = {
        "task": name,
        "ok": ok,
        "steps": [
            {"command": s.command, "ok": s.ok, **({"output": s.output} if not s.ok else {})}
            for s in steps
        ],
    }
    return payload


def cmd_version(args: argparse.Namespace) -> dict[str, Any]:
    return {"version": __version__, "tracks_stario": TRACKS_STARIO}


def _add_output_flags(p: argparse.ArgumentParser, *, suppress: bool = False) -> None:
    default = argparse.SUPPRESS if suppress else False
    out = p.add_mutually_exclusive_group()
    out.add_argument("--json", action="store_true", default=default, help="print JSON")
    out.add_argument("--text", action="store_true", default=default, help="print human text")
    p.add_argument(
        "--no-color", action="store_true", default=default, help="accepted; output has no color"
    )


def build_parser() -> argparse.ArgumentParser:
    # Same flags work before and after the subcommand. SUPPRESS keeps a
    # subparser default from overwriting a flag given before the command.
    common = argparse.ArgumentParser(add_help=False)
    _add_output_flags(common, suppress=True)

    write_flags = argparse.ArgumentParser(add_help=False)
    write_flags.add_argument("--dry-run", action="store_true", help="list files, write nothing")
    write_flags.add_argument("--force", action="store_true", help="overwrite existing files")

    parser = argparse.ArgumentParser(
        prog="stario-create",
        description="Create and grow Stario apps.",
    )
    _add_output_flags(parser)
    parser.add_argument("--version", action="store_true", help="print version and exit")
    sub = parser.add_subparsers(dest="command", metavar="command")

    p = sub.add_parser("new", parents=[common, write_flags], help="create a new project")
    p.add_argument("name")
    p.add_argument("--dir", default=None, help="parent directory (default: ./<name>)")
    p.add_argument("--no-verify", action="store_true", help="skip the post-scaffold test run")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("init", parents=[common, write_flags], help="scaffold the current directory")
    p.add_argument("--name", default=None)
    p.add_argument("--no-verify", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("screen", parents=[common, write_flags], help="add a screen")
    p.add_argument("name")
    p.add_argument("--live", action="store_true", help="stream + command routes, not just GET")
    p.set_defaults(func=cmd_screen)

    p = sub.add_parser("skills", parents=[common], help="list or install bundled skills")
    p.add_argument("skills_command", nargs="?", choices=["list", "install"], default="list")
    p.add_argument("names", nargs="*")
    p.add_argument("--to", default=".agents", help="agent dir (default: .agents)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_skills)

    p = sub.add_parser("guide", parents=[common, write_flags], help="print or update AGENTS.md")
    p.add_argument("--write", action="store_true", help="update AGENTS.md, keep '## This app'")
    p.add_argument("--check", action="store_true", help="exit 1 when AGENTS.md is stale")
    p.set_defaults(func=cmd_guide)

    for name, task in TASKS.items():
        p = sub.add_parser(name, parents=[common], help=task.doc)
        p.set_defaults(func=cmd_task)

    p = sub.add_parser("version", parents=[common], help="print version")
    p.set_defaults(func=cmd_version)
    return parser


def _human_lines(command: str, payload: dict[str, Any]) -> list[str]:
    if command in ("new", "init"):
        lines = [
            f"created {payload['path']} ({len(payload['created'])} files)",
            "next:",
            f"  cd {payload['path']}",
            *[f"  {s}" for s in payload["next"]],
        ]
        return lines
    if command == "screen":
        lines = [f"screen {payload['screen']} ({len(payload['created'])} files)"]
        lines += [f"manual: {s}" for s in payload.get("manual_steps", [])]
        return lines
    if command == "version":
        return [f"stario-create {payload['version']} (stario {payload['tracks_stario']})"]
    if command in TASKS:
        lines: list[str] = []
        for s in payload["steps"]:
            lines.append(f"[{'ok' if s['ok'] else 'FAILED'}] {s['command']}")
            if s.get("output"):
                lines.append(s["output"].rstrip())
        return lines
    if command == "guide":
        if "guide" in payload:
            return payload["guide"].splitlines()
        if "current" in payload:
            return [
                "AGENTS.md is current"
                if payload["current"]
                else "AGENTS.md is stale — run: stario-create guide --write"
            ]
        return [f"wrote {payload['written']}"]
    if command == "skills":
        if "skills" in payload:
            return payload["skills"]
        return [f"installed {', '.join(payload['installed'])} -> {payload['to']}"]
    return [json.dumps(payload, indent=2)]


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.version:
        print(f"stario-create {__version__} (stario {TRACKS_STARIO})")
        return
    if args.command is None:
        parser.print_help()
        return
    func = cast(Callable[[argparse.Namespace], dict[str, Any] | None], args.func)
    try:
        payload = func(args)
    except ScaffoldError as e:
        sys.exit(_fail(args, e))
    if payload is not None:
        _emit(args, payload, _human_lines(args.command, payload))
    if args.command == "guide" and args.check and payload is not None and not payload["current"]:
        sys.exit(1)
    if args.command in TASKS and payload is not None and not payload.get("ok", True):
        sys.exit(1)


if __name__ == "__main__":
    main()
