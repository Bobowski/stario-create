---
name: stario-browser-check
description: The rare browser check for a Stario app - a Playwright script on its own server - and the TestClient test that answers each question about HTML without a browser. Load before you open a browser, take a screenshot, or use computer use on a Stario page. A browser is only for client JavaScript that holds state (drag, a ruler, viewport handling) or a browser bug that no test reproduces.
---

# Before a browser: the test that answers it

The server renders all the HTML, and Datastar morphs it into the page. Thus a question about HTML is a question about the server answer, and `TestClient` reads that answer. When the test shows the right HTML in the right event, the browser shows it. Load `stario-api` for every signature.

| The question | The test |
| --- | --- |
| Does the other tab update? | Two streams, one command, the change in the next event of both (skill `stario-feature`). |
| Does the button do anything? | `ROUTE.href(...)` is in the page HTML, and a post to it gets 2xx and repaints the stream. |
| Does a repaint lose what I typed? | The stream element has `data-signals__ifmissing`, and the inputs are not patched again. |
| Does `data.init` run again, or the stream reconnect? | The opening tag of the stream element is the same in the page and in the first event (below). |
| Does the dialog close on a repaint? | The `<dialog>` has `data-preserve-attr="open"`, and the server never renders `open`. |
| Does the error or the toast show? | The reply, or the next event of that tab, is `datastar-patch-signals` with the signal name. |
| Does the page go to the new URL? | The reply contains `window.location`. |
| Does the sort survive a reload? | `GET` with the query returns the sorted HTML. |
| Does login protect the page? | `GET` signed out gets 303, and a Datastar request gets `window.location` (skill `stario-auth`). |
| Does a class apply? | The class is a literal in a `.py` file under `app/`, then `just css` (skill `stario-tailwind-daisyui`). |
| Does a JavaScript call exist? | `tests/test_js.py` finds each `app.<name>.<method>` in `static/js/` (skill `stario-client`). |
| Does it look right? | Ask the user. When the user watches the app, the user is the browser. |

```python
# tests/test_todos.py
import re


async def test_the_stream_keeps_the_live_element(client):
    page = (await client.get(TODOS.href())).text
    tag = re.search(r'<main id="todos"[^>]*>', page)
    assert tag is not None
    async with client.stream("GET", TODOS_LIVE.href(), timeout=2) as live:
        first = (await anext(live.iter_events()))["data"]
    assert tag.group(0) in first
```

A tag that changes between renders makes Datastar run `data.init` again, so the page opens a second stream. This test finds that in a second.

When the user says that something does not work, find the cause in this order:

1. `curl` the server of the user: `curl -s localhost:8000/todos`, and `curl -sN localhost:8000/todos/live` for the stream.
2. A failing `TestClient` test that shows the bug. Fix the code until it passes.
3. The browser, only when 1 and 2 show the right HTML and the page is still wrong.

## The browser check

Use it only for client JavaScript that holds state, or a browser bug that steps 1 and 2 cannot show.

The script starts its own server on a free port and stops it in `finally`. It never touches a server it did not start. Keep `playwright` out of the dependencies of the app, so `just check` stays fast. Both pages share one browser context, so they share cookies like two tabs.

```python
# scripts/browser.py
import asyncio
import os
import socket
import subprocess
import sys

from playwright.async_api import async_playwright, expect


async def main() -> None:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = os.environ | {"STARIO_PORT": str(port), "PROJECT_DATA_DIR": "/tmp/browser-check"}
    server = subprocess.Popen([sys.executable, "-m", "app.main"], env=env)
    try:
        await asyncio.sleep(1)
        url = f"http://127.0.0.1:{port}/todos"
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()
            viewer, actor = await context.new_page(), await context.new_page()
            await viewer.goto(url)
            await actor.goto(url)
            await actor.locator("input[type=text]").fill("milk")
            await actor.get_by_role("button", name="Add").click()
            await expect(viewer.get_by_text("milk")).to_be_visible(timeout=5000)
            await viewer.screenshot(path="/tmp/browser-check/todos.png")
            await browser.close()
    finally:
        server.terminate()
        server.wait(5)


asyncio.run(asyncio.wait_for(main(), 60))
```

```bash
uv run --with playwright playwright install chromium
uv run --with playwright python scripts/browser.py
```

Point the URL and the locators at the page you changed. Wait for a visible result with `expect`, not with a sleep. Keep the script when the app has client JavaScript that holds state. Delete it otherwise.
