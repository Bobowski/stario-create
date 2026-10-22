# Changelog

All notable changes to stario-create are documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added

- A new skill, `stario-client`: server first, then HTML and CSS, then a
  Datastar attribute, then a function in `static/js/<name>.js`. Each file
  is a classic script that defines one `app.<name>` namespace — a plain
  object literal, or a per-element factory only when the element needs
  its own state. Datastar adds every page-wide listener with
  `data.on(..., target="window")`.

### Changed

- The guide drops "No `.js` files". JavaScript lives in
  `static/js/<name>.js`, never in a Python string; the guide points to
  `stario-client` and stays under the 12,000-byte budget.
- `assets.py` gets `SCRIPTS`: a tuple of `ASSETS.href("js/<name>.js")`.
  The shell loads each one with `h.Script({"src": src, "defer": True})`
  before `ModuleScript(DATASTAR_JS)`.
- `new` writes `tests/test_js.py`: every `app.<name>.<method>` call in
  `app/**/*.py` must have its function in `static/js/<name>.js`.
- `stario-feature`'s edit dialog uses `data.ref` (`$_edit.showModal()`),
  not a `getElementById` in the expression.
- `stario-tailwind-daisyui` keeps the one-line theme restore as the only
  inline script and moves the toggle to `theme.js` (`app.theme`).
- `evals/check.py` probes for JavaScript in Python: `addEventListener`,
  `getElementById`, `window` writes and arrow bodies in `app/` strings;
  `h.Script(SafeString(` beyond the theme restore; window/document
  listeners and HTML building in `static/js`.

## 5.1.2

### Added

- `stario_create.data_dir()` returns the folder with `AGENTS.md`,
  `AGENTS-api.md`, `llms.txt`, and `skills/`. A site that serves these
  files reads them from there.

## 5.1.1

### Added

- The `justfile` has a `sync` recipe: `uvx stario-create@latest sync`.
- Cloud Agent files: `.cursor/environment.json` and `.cursor/cloud-install.sh`.
  `new` writes them. `sync` writes a missing `environment.json` and keeps
  `cloud-install.sh` current. The install script puts `uv`, Python 3.14, and
  `just` on the disk.
- `.cursor/cloud-install.sh` installs the dependencies from `uv.lock`
  (`uv sync --all-groups --all-extras --locked`, with a fresh resolve when the lock is
  stale) and runs `just tailwind` when the app has that recipe.
- The guide has a `Cursor Cloud specific instructions` section. The stream
  test is the proof. Use computer use only when that cannot prove the change.
- `stario-feature`, `stario-auth`, and `stario-litewriter` tell the agent to
  prove a change with `TestClient`, not a browser. The feature skill now has
  the live-screen stream test.
- An app profile: `[tool.stario-create] profile = "api"` in the app's
  `pyproject.toml` gives the app the short JSON API guide and no skills.
  `sync` removes the skills the profile excludes.
- `sync --check` also reports agent files that git ignores and a `check`
  recipe that does not run pytest.
- `new` writes a `Dockerfile` and a `.dockerignore`. The image installs
  from `uv.lock` and listens on `0.0.0.0:8000`.

### Changed

- The guide no longer says how to deploy: no "push `main`", no "do not open
  a pull request". That workflow belongs in the app's `## This app` notes.
- `sync` always refreshes `.cursor/cloud-install.sh`; the file is tool-owned.
  `.cursor/environment.json` is still only written when missing.
- The Tailwind skill puts a `tailwind` recipe in the `justfile`. `css` and
  `css-watch` run it first. It downloads the pinned binary once per version
  into `~/.cache/tailwindcss/`.

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
