---
name: stario-handler
description: What a Stario handler has to work with - App, Route, Context, the request (query, headers, cookies), Writer, Relay, Span, middleware, cookies, h.* tags, and TestClient. Use when you write the logic inside a handler or a test, read the query or a header, set a cookie, publish or subscribe, add a span event, or build HTML with h.*, and before you read the stario source for a signature.
---

# Inside a Stario handler

This page lists the server API of stario 5.x, from its source. Do not read `site-packages` for a signature. Write the call; pyright checks the names and the arguments. The Datastar side (`data.*`, `at.*`, `SSE`) is skill `stario-datastar`.

```python
from stario import App, Context, Relay, Route, Span, Writer, classes, h
from stario.cookies import delete_cookie, set_cookie
from stario.http.middleware import catch_errors, same_origin, security_headers
from stario.markup import baked, render
from stario.testing import TestClient
```

## App and Route

```text
app.add(ROUTE, handler)                 # one method on one path
app.use("/prefix", middleware)          # middleware is (inner: Handler) -> Handler
app.create_task(coro, name=None)        # tracked; Stario waits for it on shutdown
app.shutting_down                       # True while the server drains

ROUTE = Route("GET /rooms/{room_id}")
ROUTE.href(room_id, query={"sort": "title"}, fragment=None)   # "/rooms/7?sort=title"
```

A literal segment beats a parameter: `/rooms/live` and `/rooms/{room_id}` both work, in any order.

## Context: `c`

```text
c.req.method   c.req.path
c.req.query                    # ParsedQuery: .get(key), .get(key, default), .getlist(key),
                               # .items(), .as_dict(), key in c.req.query
c.req.headers                  # .get(name), .get(name, default), .getlist(name)
c.req.headers.get("datastar-request")   # set on a Datastar action
c.req.cookies                  # .get(name), .get(name, default)
c.match.params                 # path captures: dict of str; validate, then convert
c.state                        # dict that middleware fills: c.state["user"]
c.app                          # the App
c.span                         # this request's span
c.alive(source)                # async iterator until the client leaves or the app drains
c.disconnected  c.shutting_down  c.closing
```

Signals come from `await read_signals(c.req)` (skill `stario-datastar`).

## Writer: `w`

A handler answers once:

```text
w.html(render(...))            # str, bytes, or h.* nodes; status=200
w.text("why", status=400)
w.json(value, status=200)      # through stario.json
w.empty()                      # 204
w.redirect(url, status=307)    # a Datastar request needs SSE(w).navigate(url) instead
w.headers.set(name, value)     # before the answer
set_cookie(w, "sid", token, max_age=None, httponly=True, samesite="lax", secure=False)
delete_cookie(w, "sid")
```

## Relay

```text
relay: Relay[dict] = Relay()                       # one, built in bootstrap
relay.publish("todos.changed", {})                 # dotted subject
async with relay.subscribe("todos.changed", f"tab.{tab}", latest=True) as events:
    async for subject, data in c.alive(events): ...
```

A pattern is an exact subject, `prefix.*`, or `*`. `latest=True` keeps only the newest message per subject. Subscribe before the first render.

## Span

```text
c.span.event("todo.added", {"id": 7})   c.span.attrs({...})   c.span.fail("why")
span = c.span.step("report.run")        # a child span for a job; use it as `with span:`
```

## Middleware

- `same_origin()`: a cross-site `POST` gets 403. Keep it on `/`.
- `security_headers()`: `nosniff`, `x-frame-options: DENY`, and a referrer policy. It sets no Content-Security-Policy, so an inline `<script>` and Datastar expressions work.
- `catch_errors(SomeError, respond=fn)`: turns an exception into a response when nothing was sent.

## HTML: `h.*`

Every HTML tag is `h.` plus the tag name with a capital letter: `h.Div`, `h.Button`, `h.Textarea`, `h.Dialog`. Do not look them up; a tag that does not exist fails at once.

- Attributes come first, children after: `h.A({"href": HOME.href(), "class": "link"}, "Home")`.
- Attribute values: a `str` or a number; `True` writes a bare attribute (`{"disabled": True}`); `None` or `False` leaves it out.
- `classes("btn", {"active": is_on})` builds `class`. `data.*` results go in the same place as a dict.
- A child is a string (escaped), a node, a list of nodes, or `None` (skipped).
- `render(node)` returns the HTML string. `@baked` freezes a page shell; each parameter is a whole child or attribute.
- SVG: `from stario.markup import svg` (`svg.Svg`, `svg.Path`, ...).

## TestClient

```text
async with TestClient(bootstrap, request_timeout=5) as client:
    r = await client.get(url, params={"datastar": '{"tab": "t1"}'})
    r = await client.post(url, json={"title": "milk", "tab": "t1"})
    r.status_code  r.text  r.json()  r.headers  r.cookies
    async with client.stream("GET", url, params=TAB, timeout=2) as live:
        events = live.iter_events()            # dicts with "event" and "data"
        first = await anext(events)
    await client.drain_tasks()                 # wait for create_task work
    client.tracer.find_span("report.run")
```

The client keeps cookies across requests. A `navigate` answer is a 200 event stream that contains `window.location`.
