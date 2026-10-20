# Changelog

All notable changes to stario-create are documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Changed

- The guide proves a live update from the next SSE event (`timeout=2` on
  `client.stream`, so a missing repaint fails in two seconds). Playwright, in
  the `stario-feature` skill, checks that Datastar morphed that HTML. A
  computer-use session is for a visual judgment the assertion cannot make.

## 5.1.0

### Added

- `stario-create new --orjson` adds `orjson` to the app's dependencies and
  sets it as the `stario.json` codec in the scaffolded `main.py`.

### Changed

- The guide (`AGENTS.md`) is rewritten and much shorter, so it fits the rule
  budget of an agent. It sorts every user action into three kinds — go
  somewhere, ask for something only this tab needs, change shared state — and
  shows when a screen needs a stream. A stream route is `/live`, not
  `/subscribe`.
- Signals are for inputs, forms, and client-only state. Per-tab view state
  (sort, filter, page) lives in the URL query, and one signal per field plus
  `editing_id` replaces one signal per row. `data.indicator` covers request
  state; `data.preserve_attr` keeps a user-opened dialog open across a morph.
- `sync` now replaces the guide (`## This app` is kept byte for byte) and
  installs the skills and their `.claude/skills` links. `sync --check` exits 1
  when the guide or a skill is stale.
- A handler that needs nothing is a plain `async def`. A factory exists only
  to close over dependencies.
- New apps require `stario>=5.1,<6`. The scaffold's `bootstrap` applies
  `same_origin()` and `security_headers()`. The guide and the skills use 5.1:
  leading-underscore signal names, `relay.subscribe(..., latest=True)` for
  repaint streams, and the `httponly`/`samesite` cookie defaults.
- The `stario-litewriter` skill targets litewriter 0.3 (`uv add
  "litewriter>=0.3,<0.4"`): `schema=` on `LiteWriter`, `await db.write`,
  build-once statements with name lists (`columns=`, `set=`), the positional
  row builder, `ClaimBusy`, and `apsw.ConstraintError` for a taken unique
  value. The auth skill and the eval fixture use the same API.
- The scaffolded `justfile` sets `dotenv-load`, so a local `.env` is loaded
  for `just` recipes.
- Skills:
  - `stario-feature` also covers changes to a screen: a button, a dialog, a
    search box, a job, a page that does not repaint. It holds the complete
    example files.
  - `stario-auth` shows the store functions in litewriter form and has a
    section for adding accounts to an app that already has screens: keep the
    URLs, ask what happens to rows that exist before accounts, and filter
    every query by `c.state["user"]`.
  - `stario-tailwind-daisyui` pins the downloaded versions and adds a
    light/dark theme switch recipe.

### Added

- `evals/` — a harness that runs headless agents against the guide and the
  skills on twelve tasks and checks the result (`setup.sh`, `batch.sh`,
  `check.py`, `summary.py`).
- `tests/test_guide.py` — checks the guide size, the syntax and formatting of
  its Python blocks, and that it ends with `## This app`.

### Removed

- **Breaking:** the `init`, `screen`, `skills`, `guide`, `dev`, `serve`,
  `check`, `fix`, `test`, and `version` subcommands. Only `new`, `sync`, and
  `--version` remain. The `justfile` runs development and quality tasks; the
  `stario-feature` skill replaces `screen`.
- **Breaking:** the `--json`, `--text`, and `--dry-run` flags. Output is plain
  text.
- The screen templates and `tasks.py`.

## 5.0.1

- Dev reload runs the app as `watchfiles`' direct child.
- `uvx stario-create` is the one entry point; `setup.sh` is gone.
- Publish to PyPI on GitHub releases through trusted publishing.

## 5.0.0

- First public release: `new`, `init`, `screen`, `skills`, `guide`, task
  commands, the `AGENTS.md` guide, and the four skills.
