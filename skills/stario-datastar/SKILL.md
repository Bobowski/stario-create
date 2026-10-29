---
name: stario-datastar
description: The Datastar API in a Stario app - every data.* attribute, every at.* action, the SSE methods, read_signals, and how a morph treats the page. Use when you write or change data.on, data.bind, data.signals, data.show, data.class_, data.indicator, at.get, at.post, SSE(w).patch_elements, patch_signals, or a Datastar expression, and before you read the stario source for a signature.
---

# Datastar in Stario

This page lists the whole Datastar API of stario 5.x, from its source. Do not read `site-packages` for a signature. Write the call; pyright checks the names and the arguments.

```python
from stario.datastar import SSE, at, data, read_signals
from stario.datastar.format import string_literal  # user text inside an expression
```

## Expressions

A `data.*` value is a Datastar expression: JavaScript with a few extras.

- `$title` reads or writes the signal `title`. `$form.title` is a nested signal.
- A leading `_` makes a signal local: `$_open`. Datastar does not send it to the server. It is not a JS global, so page JS cannot read `$_open`.
- `el` is the element. `evt` is the event inside `data.on`.
- `@get(...)`, `@post(...)`: the actions that `at.*` builds. Write them with `at`, not by hand.
- Statements join with `;`. More than two statements: a function in `static/js/` (skill `stario-client`).
- User text inside an expression goes through `string_literal(text)`. Never paste it into the string.

## Attributes: `data.*`

Each method returns attribute text for an `h.*` element: `h.Button(data.on("click", at.post(ADD.href())), "Add")`.

```text
data.signals({...}, if_missing=False)   # patch signals; if_missing=True keeps typed values
data.signal(name, expr, if_missing=False)
data.computed(key, expr)  data.computeds({key: expr})
data.bind(name, prop=None, event=None)   # bind("done", prop="checked", event="change")
data.text(expr)   data.show(expr)   data.effect(expr)
data.attr(key, expr)   data.attrs({key: expr})
data.class_(name, expr)   data.classes({name: expr})
data.style(prop, expr)   data.styles({prop: expr})
data.ref(name)                           # $name is this element
data.indicator(name)                     # $name is true while this element's request runs
data.init(expr, delay=None, view_transition=False)
data.on(event, expr, once=False, passive=False, capture=False, delay=None,
        debounce=None, throttle=None, view_transition=False,
        target=None,                     # "window" | "document" | "outside"
        prevent=False, stop=False, case="kebab")
data.on_intersect(expr, threshold=None, once=False, exit=False, delay=None,
                  debounce=None, throttle=None, view_transition=False)
data.on_interval(expr, duration="1s", leading=False, view_transition=False)
data.on_signal_patch(expr, delay=None, debounce=None, throttle=None,
                     include=None, exclude=None)
data.preserve_attr("open")  data.preserve_attr(["open", "class"])
data.ignore_morph()                      # server patches skip this subtree
data.ignore(self_only=False)             # Datastar skips this subtree
data.json_signals(include=None, exclude=None, terse=False)   # debug view
```

A time is `200`, `0.2`, or `"200ms"`. `debounce` is a time, or `(time, "leading")`. `throttle` is a time, or `(time, "trailing")`. `include` and `exclude` take a regex string or a list of names.

Datastar Pro only. The app ships the free `datastar.js` (v1.0.x), so these do nothing there: `persist`, `query_string`, `replace_url`, `scroll_into_view`, `match_media`, `on_resize`, `on_raf`, `animate`, `custom_validity`, `view_transition`, and the actions `clipboard`, `intl`, `fit`.

## Actions: `at.*`

```text
at.get(url, queries=None, *, content_type=None, include=None, exclude=None,
       selector=None, headers=None, open_when_hidden=None, payload=None,
       retry=None, retry_interval_ms=None, retry_scaler=None,
       retry_max_wait_ms=None, retry_max_count=None, request_cancellation=None)
at.post / at.put / at.patch / at.delete / at.query   # same arguments as at.get
at.peek(expr)   at.set_all(value, include=None, exclude=None)   at.toggle_all(include=None, exclude=None)
```

- `retry`: `"auto"`, `"error"`, `"always"`, `"never"`. A live stream uses `at.get(LIVE.href(), retry="always")`.
- `content_type`: `"json"` (the default, sends the signals) or `"form"`.
- `include` / `exclude` choose which signals go with the request.
- `request_cancellation`: `"auto"` cancels the previous request of the same element.
- Build the URL with `ROUTE.href(...)`. A value that the user picks travels as a signal; the command reads it with `read_signals`.

A request must come from an action. A plain `fetch` ignores the SSE answer, so its `patch_signals` or `navigate` never reach the page.

## Server side: `read_signals` and `SSE`

```text
signals = await read_signals(c.req)      # dict; a GET sends them in ?datastar=
sse = SSE(w)
sse.patch_elements(part, mode=None, selector=None, namespace=None,
                   view_transition=False, view_transition_selector=None)
sse.patch_signals({...}, only_if_missing=False)
sse.navigate(url)                        # a 303 does not change the URL of a Datastar request
sse.execute_script(code, auto_remove=True)   # trusted code only
sse.remove(selector)
sse.ping()                               # keep proxies awake
```

`mode`: `"outer"` (the default), `"inner"`, `"replace"`, `"prepend"`, `"append"`, `"before"`, `"after"`. `namespace`: `"svg"` or `"mathml"`. A file input bound with `data.bind` arrives as a `FileSignal` dict: `name`, `contents` (base64), `mime`.

## How a morph treats the page

- `patch_elements` finds each top element by `id` and morphs it in place. An element with no `id` and no `selector` has no target.
- A morph keeps the element when its tag and `id` stay. Thus `data.init` does not run again on that element. Put work that must follow each repaint in the rendered HTML, not in `data.init`.
- `data.signals(..., if_missing=True)` on the stream element keeps what the user typed through each repaint.
- An open `<dialog>` or `<details>` needs `data.preserve_attr("open")`. A subtree that the client owns needs `data.ignore_morph()`.
- `data.indicator` goes on the element whose `data.on` sends the request: the `<form>` for a submit, not its button.

Trust the morph. When the stream test shows the new HTML in the next event, Datastar puts it on the page.
