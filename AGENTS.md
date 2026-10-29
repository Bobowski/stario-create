# Stario app guide

How to build a Stario app, unless the developer asks for something else.

Stario is Python hypermedia. A handler writes HTML. Datastar morphs it into the page. One open SSE response keeps a page live. State lives on the server. Docs: https://stario.dev/docs. Datastar: https://data-star.dev.

## Which skill

The skills are in `.agents/skills/`. Load `stario-api` before you write a handler, a view, or a test. Then load the skill for the task:

- A static page (no command): no skill. Write `urls.py`, `views.py`, and a page class with one `show` (Code shape).
- A page that every tab sees change, in SQLite: `stario-feature` and `stario-litewriter`.
- State in memory, a message to one tab, an edit dialog: `stario-relay`.
- A sort, a filter, paging, a search as you type: `stario-view`.
- Work that takes seconds: `stario-jobs`.
- Login and accounts: `stario-auth` and `stario-login`. Styles: `stario-tailwind-daisyui`. JavaScript: `stario-client`.
- Before a browser or a screenshot: `stario-browser-check`.

## Layout

```text
app/
  main.py           bootstrap: config, shared objects, Page(...).register(app)
  config.py         frozen Config dataclass, from_env(); every setting and secret
  assets.py         ASSETS, STYLE_CSS, DATASTAR_JS, SCRIPTS (files in static/)
  common/shell.py   page(title, body): the <html> document, @baked
  features/<page>/
    urls.py         Route values and the View of the query; imports only stario
    views.py        render(state, view, ...) -> the full document
    handlers.py     the page class: dependencies, register(app), one method per route
    data.py         schema, reads, and writes for the tables this page owns
  <name>/           code with no URL (an engine, a parser, an API client); never imports features/
tests/test_<page>.py
```

- A page is one resource: a path and its query. One folder, named after the URL noun: `/rooms/{room_id}` → `room`. Delete the folder with the page.
- A feature may import another feature's `urls.py` (links) and `data.py` (reads and writes), never its views or handlers.
- `common/` holds what every page shares (the shell, the session).
- JavaScript lives in `static/js/<name>.js` as `app.<name>`, never in a Python string (skill `stario-client`).

## Stario rules

- Not ASGI: no Uvicorn, FastAPI, or response objects. `python -m app.main` runs `asyncio.run(serve(bootstrap))`.
- `bootstrap(app: App, span: Span)` is an async generator with one `yield`: build shared objects, `span.attrs(await ASSETS.attach(app))`, register pages, `yield`, clean up. Keep `app.use("/", same_origin(), security_headers())`: cross-site commands get 403.
- A handler is `async def (c: Context, w: Writer) -> None`. It answers once: `w.html`, `w.text`, `w.empty`, `w.redirect`, or `SSE(w)`.
- `Route("GET /rooms/{room_id}")` is one method on one path. `app.add(ROUTE, handler)`; `ROUTE.href(room_id, query={...})` builds the link. No `url_for`, no `app.get`.
- `c.match.params`, `c.req.query`, `c.req.cookies`; `c.state` is filled by middleware `(inner: Handler) -> Handler`, added with `app.use("/prefix", mw)`.
- A stream loop iterates `c.alive(source)`. Background work is `c.app.create_task(coro)`, never bare `asyncio.create_task`.
- One process, one event loop. Shared state is an object built in `bootstrap`. No module-level state. No `os.environ` outside `config.py`. JSON goes through `stario.json`.

## A page is a resource

The path names the resource. When a page has a sort, a filter, or paging, the query holds it: a `View` in `urls.py` (skill `stario-view`). The page `GET` and the stream read the same view, so a reload or a shared link shows the same thing. A page with nothing to choose has no `View`.

Sort every user action:

- **Go somewhere**, including a new view: `<a href>`.
- **A result only this tab needs** while the user types (search as you type, a preview): a `GET` that reads the signals and answers `SSE(w).patch_elements(part)`, or a `POST` when the input is too long for a URL. It changes no state and keeps nothing.
- **Change state** (add, edit, delete, start a job): a command, `POST`.

A page whose state cannot change while it is open is static: `w.html(render(...))`. A page on shared state that can change is live:

```text
GET  /board        the first document
GET  /board/live   an SSE stream that stays open and repaints the page
POST /board/...    a command: read, validate, reply, execute
```

1. `GET /board` renders `data.init(at.get(BOARD_LIVE.href(), retry="always"))` on its top element.
2. The stream subscribes, sends `render(...)`, then again after each change.
3. The stream is the only thing that sends HTML. A command never answers with HTML: other tabs would not see it.

The stream follows one source. Rows in SQLite: `db.watch(query)` (skill `stario-litewriter`), the common case. State in memory: `relay.subscribe(CHANGED, latest=True)` on the one `Relay[dict]`. A command that must tell its own tab something adds a tab id and `tab.<id>` (skill `stario-relay`). Subscribe before the first render. Subjects are constants.

## Commands: read, validate, reply, execute

1. Read: `await read_signals(c.req)`, `c.match.params`, `c.state["user"]`.
2. Validate. Bad, forged, or foreign input gets `w.text("why", status=400)` (or 403, 404) and `return`.
3. Reply: `w.empty()` (204), `SSE(w).patch_signals(...)` to clear an input or show a message, or `SSE(w).navigate(url)`. A 303 to a Datastar request does not change the URL.
4. Execute: change state. A stream on `db.watch` needs nothing more. A stream on a `Relay` needs `relay.publish(CHANGED, {})`.

After the reply, `await db.write(...)`: the browser has its answer, and a failure reaches the span. `db.push` only a write that nothing reads soon after (a counter, a last-seen stamp); a read after a push can run before its commit. A domain outcome is `c.span.event(...)`; a domain failure is `c.span.fail(...)`.

The signals are the state of one tab. A command that tells its tab something after the work publishes signals: `relay.publish(f"tab.{tab}", {"_error": text})`. The stream sends `sse.patch_signals(signals)`. `data.text`, `data.show`, and `data.class_` keep their value through a repaint. A toast is the shell's `_toast` signal.

The page stops empty input before it is sent: `required`, `maxlength`, `data.attr("disabled", ...)`. The server checks again.

Slow work (a model call, a download) is a job that `c.app.create_task` runs in its own span (skill `stario-jobs`). Blocking CPU work (a password hash) runs in `await asyncio.to_thread(fn, ...)`. A delay or a client is a `Config` field.

## Render from state

- `render(...)` returns the whole document from state, and the view, the tab id, or the viewer when the page has them. It does not fetch. Datastar morphs only the changes.
- The element with `data.init(...)` and `data.signals(...)` keeps its tag, `id`, and attribute text in every render.
- Write the tree inline in `render`. A helper view exists for a block in a loop. `page()` is `@baked`: each parameter is a whole child or attribute.

## Signals and UI state

The server renders the state. Signals carry what the user types or picks, the tab id, and client-only state.

- One `data.signals({...}, if_missing=True)` per page, on the element that opens the stream: a repaint keeps what was typed.
- `data.bind("title")` ties an input to a signal. A leading `_` (`_error`) makes it local: Datastar does not send it.
- One signal per field and one for the row being edited (`editing_id`), not one per row. Validate `editing_id` like any input.
- The resource id is in the path, the view in the query, the user in a signed cookie (skill `stario-auth`). None is a signal.
- A form that sends a command shows it is busy: `data.indicator("_saving")` on the `<form>`, and `data.attr("disabled", "$_saving")` on its button.
- A `<dialog>` or `<details>` holds its own open state (`data.preserve_attr("open")`). A subtree the client owns gets `data.ignore_morph()`.

## Storage

Choose with the developer. Do not add a database the app does not need.

- No persistence: an object built in `bootstrap`.
- SQLite: litewriter (skill `stario-litewriter`). A table is `id` plus `data` JSON. A field that a query filters, sorts, or keeps unique becomes a virtual column with an index. Add and drop virtual columns; do not migrate data. A real column is for a key: `id`, `user_id`.
- Files go in `config.data_dir`: `$PROJECT_DATA_DIR` (Yard: `/data`, kept across deploys) or `./data`. The database is `config.db_path`. Tests set `PROJECT_DATA_DIR` to `tmp_path`.

## Code shape

A page is one class in `handlers.py`. Its fields are its dependencies. `register(app)` adds its routes. Each route is one method that reads top to bottom.

```python
@dataclass(frozen=True, slots=True)
class BoardPage:
    db: LiteWriter
    relay: Relay[dict]

    def register(self, app: App) -> None:
        app.add(BOARD, self.show)

    async def show(self, c: Context, w: Writer) -> None:
        view = BoardView.from_query(c.req.query)
        w.html(render(list_tiles(self.db, view), view))
```

Where code goes:

- Logic that one route needs stays in that method.
- A read or a write is a function in `data.py`: `list_*`, `get_*` (one or `None`), `add_*`, `set_*`, `remove_*`.
- A rule with no URL that several pages use is a plain function in `app/<name>/`.

Do not build: service classes, repositories, command or result objects, base pages, a `utils` module, a wrapper around `db`, a helper with one call site.

Read input with these lines, not with a helper:

```python
title = str(signals.get("title", "")).strip()  # text
done = signals.get("done") is True  # bool
editing_id = signals.get("editing_id")  # int: type(editing_id) is int, not isinstance
tile_id = c.match.params["tile_id"]  # path int: tile_id.isdecimal(), then int(tile_id)
tab = str(signals.get("tab", ""))  # tab id: tab.isalnum() and len(tab) <= 32
```

## Tests

Tests run the production `bootstrap` through `TestClient(bootstrap, request_timeout=5)`. Each page: the page loads; the view follows the query; a command repaints the stream; bad input gets 4xx. The next SSE event is the changed HTML; two streams are two tabs:

```python
async def test_paint_repaints_the_stream(client):
    async with client.stream("GET", BOARD_LIVE.href(), timeout=2) as live:
        events = live.iter_events()
        assert 'id="board"' in (await anext(events))["data"]
        r = await client.post(PAINT.href(1), json={"color": "#ff0000"})
        assert r.status_code == 204
        assert "#ff0000" in (await anext(events))["data"]
```

A `GET` sends signals in `params={"datastar": '{"q": "x"}'}`, a `POST` in `json=`. A `navigate` reply contains `window.location`. The client keeps cookies.

## Checks

Check what you changed, at the cost the change needs. A handler, a query, a stream: a `TestClient` test. A style: `just css`. Trust Stario, Datastar, litewriter, and Tailwind: pyright checks each call, and when the stream test shows the new HTML, the browser shows it. Read their source only when pyright or a test fails. After a Python change and before a push: `just check`; fix every failure.

A browser is only for client JS that holds state, or a browser bug that no test reproduces. When the user watches the app, the user is the browser: make the change and say what to look at. When the user says it does not work: `curl` their server, then a failing test. Browser check: skill `stario-browser-check` names the test for each question first.

## Common mistakes

| Avoid | Do |
| --- | --- |
| An error from the work written to shared state | signals to `tab.<id>` |
| Sort or filter in a signal | the query, through `View` |
| Handler factories, a service class | a page class with one method per route |

## Cursor Cloud specific instructions

Install is `.cursor/cloud-install.sh`.

## This app

Notes for this app go below. `stario-create sync` replaces the text above and keeps this section.
