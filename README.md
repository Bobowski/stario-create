# Stario skills

Agent and human guidance for building apps with [Stario](https://stario.dev). This repo tracks Stario 4. The framework itself lives at [bobowski/stario](https://github.com/bobowski/stario).

Two kinds of files:

- `AGENTS.md` is the always-on guide. Copy it to the root of a Stario app. It states the layout, the CQRS default, how to render from state, what a signal holds, the code shape, and the test shape. An agent reads it before it writes code.
- `skills/<name>/SKILL.md` are on-demand procedures for optional stacks. An agent loads one when the task matches its description.

## New app

```bash
curl -fsSL https://stario.dev/setup.sh | sh -s -- my-app
```

`setup.sh` creates a runnable app: `uv` project on Python 3.14, the layout from the guide with one static screen, `AGENTS.md`, a `CLAUDE.md` that imports it, the lint and test config, and the skills under `.agents/skills/` when `npx` is present.

## Existing app

```bash
curl -o AGENTS.md https://stario.dev/AGENTS.md
npx skills add bobowski/stario-skills
```

The second line copies every skill into the skill folder of your agent (`.agents/skills/`, `.cursor/skills/`, `.claude/skills/`, and so on). Without Node, copy a `skills/<name>/` folder by hand. Keep app notes in the `## This app` section at the end of `AGENTS.md`, so a newer guide can replace the text above it.

## Skills

| Skill | Use it when |
| --- | --- |
| `stario-feature` | You add or remove one screen: a page or a resource with its own URL. |
| `stario-auth` | The app needs login: a signed session cookie, `c.state["user"]`, protected screens. |
| `stario-litewriter` | The app stores data in SQLite. `litewriter` is one writer thread, and `watch` repaints a live screen from a commit. |
| `stario-tailwind-daisyui` | The app is styled with Tailwind v4 and DaisyUI through the standalone binary. No Node. |

## Served copies

`stario.dev` serves these files: `/AGENTS.md`, `/setup.sh`, `/llms.txt`, `/llms-full.txt` (the guide and the skills in one file), `/skills/`, and `/skills/<name>/SKILL.md`.

## Changing the guide

The guide is checked against real code. `examples/chat-room` in the stario repo follows it. When a rule changes here, change the example there, and run its tests. A code snippet in `AGENTS.md` must run as written; build it in a throwaway project before you commit.
