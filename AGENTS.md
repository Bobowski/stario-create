# Stario app guide

This file teaches a person or an agent how to build a Stario app. It sits at the root of every Stario app repo. Read it before you write code. It is the whole default. When the developer asks for something else, do that instead. App-specific notes live in the last section, `## This app`.

- Docs: https://stario.dev/docs
- Deeper context: https://stario.dev/llms-full.txt
- Skills (SQLite, auth, Tailwind, adding a screen): `.agents/skills/` in this repo, or `npx skills add bobowski/stario-create`
- Reference app: https://github.com/bobowski/stario/tree/main/examples/chat-room
- This file, the skills, and the project CLI: https://github.com/bobowski/stario-create

Stario is Python hypermedia. A handler writes HTML. Datastar morphs the page in the browser. A long-lived SSE stream keeps a page live. State lives on the server. Each screen is a full document, and a plain link moves between screens.

## Start a project

One command creates a runnable app with one static screen, this file, the skills, and a `justfile` of dev tasks:

```bash
uvx stario-create new my-app
cd my-app
just dev    # http://127.0.0.1:8000, reloads on change (or: uv run watchfiles 'uv run python -m app.main' app/ static/)
```

`stario-create` runs `uv init --app --python 3.14`, removes the root `main.py`, adds `stario` plus the dev tools, writes the `pyproject.toml` blocks below, creates the tree in the next section with a `home` screen, vendors `static/js/datastar.js`, writes `AGENTS.md` and a `CLAUDE.md` that imports it, ignores `*.sqlite3*`, installs the four skills into `.agents/skills/`, writes the `justfile`, and runs the tests once to prove the app works.

Without the CLI, do the same by hand. The `pyproject.toml` needs these blocks:

```toml
[tool.ruff]
target-version = "py314"
line-length = 100
src = ["app", "tests"]
extend-exclude = [".agents", ".claude", ".cursor"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.ruff.lint.isort]
known-first-party = ["app"]

[tool.pyright]
pythonVersion = "3.14"
include = ["app", "tests"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
asyncio_mode = "auto"
```

Check before you call work done — `just check`, or `stario-create check`, or the four steps:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

Stario does not read `.env`. Configure with environment variables; `serve` reads `STARIO_*` through `ServerConfig.from_env()`. `STARIO_PORT` changes the port.

## Where does it go

| You need to add | It goes in |
| --- | --- |
| A URL | `Route` value in `app/features/<screen>/urls.py` |
| A table or a query | `SCHEMA` and a function in `app/features/<screen>/data.py` |
| HTML | the tree inside `render` in `app/features/<screen>/views.py` |
| Input validation | the command handler in `app/features/<screen>/handlers.py` |
| A new screen | a new folder `app/features/<screen>/`, then `register` in `app/main.py` (skill `stario-feature`) |
| The `<html>` document | `page(title, body)` in `app/common/shell.py` |
| Who the user is | a signed cookie read by middleware into `c.state["user"]` (skill `stario-auth`) |
| Which tab sent the action | a signal minted per tab — a visitor id, not a user |
| A setting or a secret | a field on `Config` in `app/config.py`, read from the environment |
| A stylesheet or an image | `static/`, served through `ASSETS` in `app/assets.py` (CSS at scale: skill `stario-tailwind-daisyui`) |
| A small UI behaviour | a Datastar expression on the element: `data.on("click", "el.closest('dialog').showModal()")` |
| A test | `tests/test_<screen>.py` |
| Something another screen needs | a function in that screen's `data.py`, imported by the other screen |

## Layout: one folder per screen

Every screen of the app is one feature folder. A screen is a page or a resource with its own URL: `/`, `/settings`, `/rooms/{room_id}`. The folder owns the URLs, the data, the views, and the handlers of that screen. The number of folders tracks the number of screens. When a screen goes away, delete its folder.

```text
app/
  main.py             bootstrap: build dependencies, register every feature
  config.py           frozen Config dataclass, from_env(), read once in bootstrap
  assets.py           ASSETS = Assets(...), STYLE_CSS, DATASTAR_JS
  common/
    shell.py          page(title, body): the <html> document, @baked
  features/
    <screen>/
      urls.py         Route values for this screen
      data.py         SCHEMA + query functions, when the screen owns tables
      views.py        render(state) -> full document
      handlers.py     handlers + register
static/
  js/datastar.js      vendored client
  css/style.css       stylesheet
tests/
  conftest.py         TestClient(bootstrap) fixture
  test_<screen>.py    one file per screen
justfile              dev tasks: just dev, just check, just test
AGENTS.md             this file
CLAUDE.md             one line: @AGENTS.md
.agents/skills/       installed skills
```

Rules for the tree:

- Use this layout from the first commit, also with one screen. There is no later migration.
- `urls.py`, `views.py`, and `handlers.py` always exist. `data.py` exists when the screen owns tables. Each folder has an `__init__.py`. No other files by default. Add `models.py` or `subjects.py` only when `data.py` or `handlers.py` has become hard to read.
- A feature is self-contained. It owns its tables, its HTML, and its handler logic.
- A feature may import another feature's `urls.py` for links and another feature's `data.py` for reads. Imports flow one way. Do not import views across features.
- `common/` holds behaviour every screen shares: the document shell, the session cookie, time formatting. It does not hold borrowed views or borrowed queries.
- Two screens with similar HTML keep their own copies. Merge later as an optimization, when the copies have proven identical. Do not merge by default.
- `app/db.py` exists only when more than one feature needs the same connection object. Keep it thin: connect, transaction, apply schema.
- No JavaScript files by default. Datastar expressions on elements cover small UI behaviour. A script file is a deliberate exception with a reason in `## This app`.

## Stario invariants

Stario is not ASGI. Do not mount it in Uvicorn, Hypercorn, FastAPI, or Starlette. Do not return response objects. Run the module: `python -m app.main`. `app/main.py` ends with `if __name__ == "__main__": asyncio.run(serve(bootstrap))`.

Default imports:

```python
from stario import App, Context, Relay, Route, Span, Writer, h
from stario.datastar import SSE, at, data, read_signals
from stario.markup import HtmlElement, baked, classes
```

Import order in every file: standard library, then third-party (`stario`, `pytest`), then `app`. The `I` rule in `ruff` enforces it.

Rules:

- `bootstrap` is `async def bootstrap(app: App, span: Span)` with exactly one `yield`. Build dependencies, attach assets, and register routes before `yield`. Clean up after `yield`.
- A handler is `async def handler(c: Context, w: Writer) -> None`. It completes the response through `w.html`, `w.empty`, `w.redirect`, or `SSE(w)`. It completes the response once.
- A `Route` is one method on one path: `Route("GET /rooms/{room_id}")` or `Route("POST", ROOM_PATH + "/send")`. Register with `app.add(route, handler)`. Build links with `route.href(room_id)` or `route.href(room_id=x)`. There is no `url_for`.
- `c.match.params["room_id"]` reads a path capture. `c.req.query` reads the query string. `c.req.cookies` reads cookies. `c.state` is a per-request dict that middleware fills.
- Middleware is `(inner: Handler) -> Handler`. `app.use("/prefix", middleware)` applies it to every route under the prefix, including the 404/405 answers. `app.use` and `app.add` work in any order; the router composes middleware when the app compiles.
- A long-lived loop iterates `c.alive(source)`. The loop ends on disconnect or shutdown. Cleanup after the loop always runs.
- Background work uses `c.app.create_task(...)`, not bare `asyncio.create_task`.
- Write the 4xx and `return` for a malformed request: `w.text("message", status=400)`. A missing row gets `status=404`. A user who may not do this gets `status=403`.
- An exception type that maps to one response everywhere is declared once and mapped with `catch_errors`: `app.use("/", catch_errors(MyError, respond=responder))`. `responder` is `async def responder(c, w, exc)`; import `catch_errors` from `stario.http.middleware`.
- Framework JSON goes through `stario.json`. Do not call `json.dumps` for signal or response data.
- Stario runs on one event loop in one process. Shared state is a plain object passed into the feature. No globals.

## The default architecture

Decide per screen:

- A screen with no action is a static page. One `GET` handler. `w.html(render(state))`. Done.
- A screen with any action is live. Three kinds of routes. This is CQRS over HTTP.

```text
GET  /board         first document
GET  /board/live    SSE stream that stays open and repaints the page
POST /board/...     command: validate, reply 204, change state, publish
```

The stream is the only place that paints. A command never returns HTML. If a command returned HTML, the tab that clicked would race the stream, and other tabs would stay stale.

The loop:

1. `GET /board` renders `render(state)`.
2. The page opens `GET /board/live` on load with `retry="always"`. One stream per page.
3. The stream sends `render(state)` once, then waits for a notification.
4. A command validates the input, replies `w.empty()`, changes the store, publishes a notification.
5. Every open stream wakes, reads state again, sends `render(state)`. Datastar morphs the page.

The `204` means "valid request accepted" — validation always precedes it. Doing the work inline before the reply is fine when it is light; the reply does not carry the UI either way, the state change does.

Every command is a Datastar action: `data.on("click", at.post(ROUTE.href()))` or `data.on("submit", at.post(...), prevent=True)` on a form. Stario has no form-body parser, so a plain HTML `<form method="post">` is not used.

Notifications are `Relay` subjects: dotted strings such as `"board.changed"` or `f"room.{room_id}.message"`. `relay.publish(subject, payload)` wakes every `relay.subscribe(pattern)` whose pattern matches. `"room.*"` matches every event of every room. Define each feature's subjects as constants or small functions at the top of its `handlers.py`. A store with a watch feature can replace `Relay` for row changes (skill `stario-litewriter`). For more than one process, swap `Relay` for a broker and keep the same three routes.

Three kinds of bad input, three replies:

- Honest but empty or unchanged input (blank title, same color): reply `204` and do nothing.
- A domain conflict (name taken, room full): write the outcome to state, publish, and let `render` show the message. Failure is a view of state.
- Malformed or forged input (bad color format, unknown id, another user's row): write the 4xx and `return` — `w.text("why", status=400)`. A real client never sends it. Many handlers with one error shape declare an exception type and map it once with `catch_errors`.

A command that moves the user to another screen does not reply 204. It replies `SSE(w).navigate(ROOM.href(room.id))`. Navigation between screens by the user is a plain `<a href=...>`.

Identity has three kinds. Resource identity (`room_id`, `tile_id`) lives in the URL. A signed-in user lives in a signed cookie, verified by middleware into `c.state["user"]` (skill `stario-auth`). A lighter third kind is the visitor id: minted per tab, kept in `sessionStorage`, sent as a signal. It means "this open tab" — attribution for actions and for own-message highlighting, never authentication. A handler does not treat it as a user. The reference chat-room uses it for its visitors.

## Render from state

Each live screen has one function, `render(state) -> HtmlElement`, that returns the full document. The first `GET` and every stream wake call the same function. `ui = f(state)` stays visible.

- The stream sends the whole document: `sse.patch_elements(render(state))`. Datastar morphs the live DOM. Compression on the open stream makes repeated HTML cheap. Do not start with small targeted patches. Narrow a patch only after you have measured a cost.
- `render` does not fetch. The handler loads state and passes it in. State is a frozen dataclass or the rows the queries return.
- When the page differs per viewer (own messages highlighted, own draft), `render(state, viewer)` takes the viewer too. Each stream renders for its own viewer. The viewer is `c.state["user"]` for a signed-in user, or the per-tab visitor id when the app has no accounts.
- The element that carries `data.init(...)` and `data.signals(...)` keeps the same tag and `id` in every render. Datastar morphs it in place, so the stream is not reopened. A changed tag or `id` would replace the element and reconnect.
- The document shell is `@baked`. A baked function compiles once. Inside a baked function, a parameter is a whole child or a whole attribute value. Loops, conditions, and string formatting happen in the caller.
- Write the HTML tree inline inside `render`. A helper view exists for a block that repeats in a loop. A helper view does not exist for one call site. Do not build a helper per element.
- Repetition inside one feature is merged inside that feature. Repetition across features is left alone until it has proven stable.

## Signals and UI state

Signals are form input. Nothing else by default.

- `data.bind("color")` binds an input to a signal. `await read_signals(c.req)` reads every signal on each `@get` or `@post`.
- One `data.signals({...}, if_missing=True)` block per page, on the element that opens the stream. `if_missing=True` keeps what the user typed when the page morphs again.
- The server never trusts a signal. Every command validates the signal and reads truth from the store.
- Resource identity lives in the URL. A signed-in user lives in the session cookie. A signal holds neither — the per-tab visitor id is the one exception, and it is never trusted as a user.
- The stream patches HTML. It does not patch signals. One exception: after a command consumes an input, the stream or the command may reset that input with `sse.patch_signals({"message": ""})`.
- UI state the user controls must survive a morph. A morph arrives at any moment. If it closes the dialog the user just opened, the app feels broken. Protect that state in the HTML:
  - `data.preserve_attr("open")` on `<dialog>` and `<details>`. The morph keeps the current value.
  - `data.ignore_morph()` on a subtree the client owns, such as a text editor with its own state.
  - Do not render `{"open": True}` from the server for a dialog the user opens.
- Signal names are `snake_case` on the wire. Nested state is a nested object, not a dotted name.

## A complete live screen

The files in build order. Copy them top to bottom and the app runs after the last one.

`app/config.py`:

```python
import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Config:
    db_path: str

    @classmethod
    def from_env(cls) -> Config:
        return cls(db_path=os.environ.get("APP_DB_PATH", "app.sqlite3"))
```

`app/assets.py`:

```python
from pathlib import Path

from stario import Assets

ASSETS = Assets(Path(__file__).resolve().parents[1] / "static", url_prefix="/static")
STYLE_CSS = ASSETS.href("css/style.css")
DATASTAR_JS = ASSETS.href("js/datastar.js")
```

`app/common/shell.py`:

```python
from stario import h
from stario.datastar import ModuleScript
from stario.markup import HtmlElement, baked

from app.assets import DATASTAR_JS, STYLE_CSS


@baked
def page(title: str, body: HtmlElement) -> HtmlElement:
    return h.HtmlDocument(
        {"lang": "en"},
        h.Head(
            h.Meta({"charset": "utf-8"}),
            h.Meta({"name": "viewport", "content": "width=device-width, initial-scale=1"}),
            h.Title(title),
            h.Link({"rel": "stylesheet", "href": STYLE_CSS}),
            ModuleScript(DATASTAR_JS),
        ),
        h.Body(body),
    )
```

`app/features/board/urls.py`:

```python
from stario import Route

BOARD = Route("GET /board")
BOARD_LIVE = Route("GET /board/live")
PAINT = Route("POST /board/{tile_id}/paint")
```

`app/features/board/data.py`:

```python
import sqlite3
from dataclasses import dataclass

SCHEMA = """
CREATE TABLE IF NOT EXISTS tiles (
    id INTEGER PRIMARY KEY,
    color TEXT NOT NULL DEFAULT '#ffffff'
);
INSERT OR IGNORE INTO tiles (id) VALUES (1), (2), (3), (4), (5), (6), (7), (8), (9);
"""


@dataclass(frozen=True, slots=True)
class Tile:
    id: int
    color: str


def list_tiles(conn: sqlite3.Connection) -> list[Tile]:
    rows = conn.execute("SELECT id, color FROM tiles ORDER BY id").fetchall()
    return [Tile(*row) for row in rows]


def set_color(conn: sqlite3.Connection, tile_id: int, color: str) -> None:
    with conn:
        conn.execute("UPDATE tiles SET color = ? WHERE id = ?", (color, tile_id))
```

`app/features/board/views.py`:

```python
from stario import h
from stario.datastar import at, data
from stario.markup import HtmlElement, classes

from app.common.shell import page
from app.features.board.data import Tile
from app.features.board.urls import BOARD_LIVE, PAINT


def render(tiles: list[Tile]) -> HtmlElement:
    return page(
        "Board",
        h.Main(
            {"id": "board"},
            data.signals({"color": "#000000"}, if_missing=True),
            data.init(at.get(BOARD_LIVE.href(), retry="always")),
            h.Label("Color", h.Input({"type": "color"}, data.bind("color"))),
            h.Div(
                classes("grid"),
                *[
                    h.Button(
                        {"style": f"background:{tile.color}", "aria-label": f"Tile {tile.id}"},
                        data.on("click", at.post(PAINT.href(tile.id))),
                    )
                    for tile in tiles
                ],
            ),
        ),
    )
```

`app/features/board/handlers.py`:

```python
import re
import sqlite3

from stario import App, Context, Relay, Writer
from stario.datastar import SSE, read_signals

from app.features.board import data
from app.features.board.urls import BOARD, BOARD_LIVE, PAINT
from app.features.board.views import render

CHANGED = "board.changed"


def show_board(conn: sqlite3.Connection):
    async def handler(c: Context, w: Writer) -> None:
        w.html(render(data.list_tiles(conn)))

    return handler


def board_live(conn: sqlite3.Connection, relay: Relay[str]):
    async def handler(c: Context, w: Writer) -> None:
        async with relay.subscribe(CHANGED) as events:
            sse = SSE(w)
            sse.patch_elements(render(data.list_tiles(conn)))
            async for _ in c.alive(events):
                sse.patch_elements(render(data.list_tiles(conn)))

    return handler


def paint_tile(conn: sqlite3.Connection, relay: Relay[str]):
    async def handler(c: Context, w: Writer) -> None:
        signals = await read_signals(c.req)
        color = str(signals.get("color", ""))
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            w.text("Color must be #rrggbb", status=400)
            return
        w.empty()
        data.set_color(conn, int(c.match.params["tile_id"]), color)
        relay.publish(CHANGED, "paint")

    return handler


def register_board(app: App, conn: sqlite3.Connection, relay: Relay[str]) -> None:
    app.add(BOARD, show_board(conn))
    app.add(BOARD_LIVE, board_live(conn, relay))
    app.add(PAINT, paint_tile(conn, relay))
```

`app/main.py`:

```python
import asyncio
import sqlite3

from stario import App, Relay, Span, serve

from app.assets import ASSETS
from app.config import Config
from app.features.board import data as board_data
from app.features.board.handlers import register_board


async def bootstrap(app: App, span: Span):
    config = Config.from_env()
    conn = sqlite3.connect(config.db_path)
    conn.executescript(board_data.SCHEMA)
    relay: Relay[str] = Relay()

    span.attrs(await ASSETS.attach(app))
    register_board(app, conn, relay)
    yield
    conn.close()


if __name__ == "__main__":
    asyncio.run(serve(bootstrap))
```

Note the two names called `data`. In `handlers.py`, `data` is the feature's `data.py`. In `views.py`, `data` is `stario.datastar.data`. They do not meet in one file.

## Handlers

One shape, whatever the count: a factory per handler, and one `register_<screen>(app, deps)` that adds every route in one place. The factory takes the dependencies the handler needs; the register function takes them all. A static screen's factory may take a config value; a live screen's factories take `conn` and `relay`. Do not wrap handlers in a class.

```python
def show_about(version: str):
    async def handler(c: Context, w: Writer) -> None:
        w.html(render(version))

    return handler


def register_about(app: App, version: str) -> None:
    app.add(ABOUT, show_about(version))
```

Inside a handler:

- Read input first: `c.match.params`, `c.req.query`, `c.state["user"]`, `await read_signals(c.req)`.
- Validate. Write the 4xx and `return` when the request is malformed or forbidden.
- Reply. `w.empty()` once the input validates — the `204` means "accepted". The work may run before or after it; the stream delivers the result.
- Change state. Publish.

A subscribe handler opens the subscription before it publishes anything this connection must see. Cleanup after `async for` runs on disconnect and on shutdown.

## Code shape

Fewer functions, not thinner ones. The work lives where you can read it.

- Inline a function whose body is one call: `return other(...)`, one `sse.patch_elements(...)`, one `w.html(...)`.
- Inline a private alias that exists to rename a call.
- Do not extract a helper because a line is long. Do not extract a helper for one call site.
- Keep a function when it has two or more call sites, when it is a loop body, or when it does I/O you want to test alone. Branches alone do not earn a name. One call site inlines, branches included.
- Do not add a backwards-compatible alias. Rename, then fix the callers.
- No comments that restate the code. A comment explains a non-obvious reason.
- Name query functions after the SQL verb: `list_*` returns many, `get_*` returns one or `None`, `add_*`, `set_*`, `remove_*` mutate.
- Delete code with its screen. A removed page leaves no folder, no route, no test file.

## Tests

Tests run against the production `bootstrap` through `TestClient`, which speaks the real HTTP protocol on an in-memory transport. There is no second composition root.

`tests/conftest.py`:

```python
import pytest
from stario.testing import TestClient

from app.main import bootstrap


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "app.sqlite3"))
    async with TestClient(bootstrap) as c:
        yield c
```

Each screen has one test file with two kinds of tests:

1. The page loads. `GET` the route, assert `200`, assert text the page must show.
2. A command repaints the stream. Open the stream, send the command, read the next event.

```python
from app.features.board.urls import BOARD, BOARD_LIVE, PAINT


async def test_board_loads(client):
    r = await client.get(BOARD.href())
    assert r.status_code == 200
    assert 'id="board"' in r.text


async def test_paint_repaints_the_stream(client):
    headers = {"accept-encoding": "identity"}
    async with client.stream("GET", BOARD_LIVE.href(), headers=headers) as live:
        events = live.iter_events()
        first = await anext(events)
        assert 'id="board"' in first["data"]

        r = await client.post(PAINT.href(1), json={"color": "#ff0000"})
        assert r.status_code == 204

        repaint = await anext(events)
        assert "#ff0000" in repaint["data"]


async def test_paint_rejects_bad_color(client):
    r = await client.post(PAINT.href(1), json={"color": "red"})
    assert r.status_code == 400
```

`client.post(url, json=...)` sends the JSON object as Datastar signals. `client.stream(...)` yields once headers are in. `iter_events()` yields SSE events as dicts with `event` and `data`. Leaving the `async with` disconnects the stream and ends the handler. The client keeps a cookie jar, so a login response sets the cookie for the next request.

Count the events. A stream that publishes on join (presence) repaints once more before the command repaint. Read that event first, then send the command. A command that replies `SSE(w).navigate(url)` returns `200` with `text/event-stream`; assert `"window.location" in r.text` and the target path.

Test the data layer directly only when a query has logic of its own. The `client` fixture points `APP_DB_PATH` at `tmp_path`, and `Config.from_env()` runs inside `bootstrap`, so each test gets its own file.

## Common mistakes

| Avoid | Prefer |
| --- | --- |
| Flat `app/routes.py`, `app/handlers.py` | `app/features/<screen>/` from the first commit |
| A folder named after a layer (`app/views/`) | A folder named after a screen (`app/features/settings/`) |
| FastAPI, Starlette, ASGI response objects | `App`, `Route`, `Context`, `Writer` (`w.html`, `w.empty`, `w.redirect`) |
| `app.get(path, handler)` | `Route("GET /path")` and `app.add(route, handler)` |
| `url_for(...)` | `ROUTE.href(...)` |
| `bootstrap` without `yield` | One async generator with one `yield` |
| A command that returns HTML | A command that replies 204 and publishes |
| `<form method="post">` | `data.on("submit", at.post(...), prevent=True)` |
| `patch_elements(fragment, selector=...)` as the first version | `patch_elements(render(state))` for the whole document |
| A signal that holds a row, a list, an id, or a signed-in user | The row in the store, the id in the URL, the user in the cookie |
| `{"open": True}` rendered for a user-opened dialog | `data.preserve_attr("open")` |
| A `.js` file for a click | `data.on("click", "...")` on the element |
| `Writer.alive(...)` | `c.alive(...)` |
| Bare `asyncio.create_task(...)` | `c.app.create_task(...)` |
| `json.dumps` for signals | `stario.json` through `SSE` and `w.json` |
| A helper function per element | One `render` with the tree written inline |
| Shared `components.py` across features on day one | Each feature keeps its own HTML; merge after it proves stable |
| A second bootstrap for tests | `TestClient(bootstrap)` |
| Python 3.12 idioms | Python 3.14: `type` aliases, PEP 695 generics, `match`, `dataclass(slots=True)` |

## Not in this guide

Each of these has a home. Do not invent a pattern; read the source named here.

- User identity, login, logout, protected prefixes: skill `stario-auth`.
- SQLite with one writer thread and `watch`: skill `stario-litewriter`.
- Tailwind and DaisyUI without Node: skill `stario-tailwind-daisyui`.
- Adding or removing a screen, step by step: skill `stario-feature`.
- File uploads and user files: https://stario.dev/docs/how-tos/user-uploads-and-storage
- Error pages and `app.not_found`: https://stario.dev/docs/how-tos/error-handlers
- Deployment, containers, TLS: https://stario.dev/docs/how-tos/deployment-containers-and-tls
- Telemetry and the SQLite tracer: https://stario.dev/docs/how-tos/traces-in-sqlite
- Datastar attribute reference: https://data-star.dev

Install the skills with `stario-create skills install`, or `npx skills add bobowski/stario-create`, or copy a `skills/<name>/` folder from https://github.com/bobowski/stario-create into `.agents/skills/`.

## This app

Notes for this app go below this line. The text above is the Stario guide. `stario-create guide --check` tells you when it is stale; `stario-create guide --write` replaces the text above this section and keeps your notes.
