# stario-create

The project tool and agent guidance for building apps with [Stario](https://stario.dev). This repo tracks Stario 5. The framework itself lives at [bobowski/stario](https://github.com/bobowski/stario).

Two things ship from here:

- The `stario-create` CLI (`uvx stario-create`, or `uv tool install stario-create`). It scaffolds apps, adds screens, installs the skills, updates the guide, and runs the dev tasks.
- The files it installs: `AGENTS.md` (the always-on guide an app keeps at its root) and `skills/<name>/SKILL.md` (on-demand procedures an agent loads when the task matches).

## New app

```bash
uvx stario-create new my-app
cd my-app
just dev     # http://127.0.0.1:8000, reloads on change
just check   # lint, format, types, tests — run before done
```

`new` creates a uv project on Python 3.14, adds `stario>=5,<6` and the dev tools, writes the feature-folder layout with one static `home` screen, vendors `static/js/datastar.js`, writes `AGENTS.md`, a `CLAUDE.md` that imports it, and a `justfile` (`dev`, `serve`, `check`, `fix`, `test`), installs the four skills into `.agents/skills/`, and runs the tests once. Without `just`, the recipes in the justfile are plain commands — run them directly.

From git instead of PyPI:

```bash
uvx --from git+https://github.com/bobowski/stario-create stario-create new my-app
```

## Growing an app

Run these at the app root:

```bash
stario-create screen settings            # static page
stario-create screen notes --live        # GET + live stream + one command
stario-create skills install             # skills into .agents/skills/
stario-create guide --check              # is AGENTS.md stale?
stario-create guide --write              # update it, keep '## This app'
stario-create check                      # ruff, format, pyright, pytest
stario-create dev                        # hot reload, no `just` needed
```

Every command prints JSON when stdout is piped, takes `--json` or `--text`, and writer commands take `--dry-run` and `--force`.

## Skills

| Skill | Use it when |
| --- | --- |
| `stario-feature` | You add or remove one screen: a page or a resource with its own URL. |
| `stario-auth` | The app needs login: a signed session cookie, `c.state["user"]`, protected screens. |
| `stario-litewriter` | The app stores data in SQLite through `litewriter`: one writer thread, `watch` repaints a live screen from a commit. |
| `stario-tailwind-daisyui` | The app is styled with Tailwind v4 and DaisyUI through the standalone binary. No Node. |

`npx skills add bobowski/stario-create` also works — it reads the `skills/` tree at this repo root.

## Served copies

`stario.dev` serves these files: `/AGENTS.md`, `/llms.txt`, `/llms-full.txt` (the guide and the skills in one file), `/skills/`, and `/skills/<name>/SKILL.md`.

## Repo layout

`AGENTS.md`, `llms.txt`, and `skills/` sit at the root — `npx skills`, `stario.dev`, and repo browsing all read them there. The wheel embeds copies under `stario_create/_data/` (hatchling `force-include`), so `uvx` works without a checkout. In a checkout, the CLI reads the root files directly, so there is one canonical copy of each file.

## Changing the guide

The guide is checked against real code. `examples/chat-room` in the stario repo follows it. When a rule changes here, change the example there, and run its tests. A code snippet in `AGENTS.md` must run as written; the package tests scaffold a project and compile every generated file, and `stario-create new` runs the new app's tests.
