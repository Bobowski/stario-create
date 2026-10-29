"""The page check: what a browser would show wrong, read from the server HTML.

It opens `/`, follows every local link, and checks each page:

- each `@get(...)` or `@post(...)` URL has a route;
- each `$signal` an expression reads is defined on the page;
- an element that opens a stream keeps its opening tag in the stream, so
  `data.init` does not run again;
- each `<dialog>` keeps `open` through a repaint;
- no two elements share an `id`.

It sees each page as a new app shows it. Markup that only rows make (a
Rename button in each row) needs data first: a page test adds rows, then
calls `assert not await check(client, url)`.

Add a page that no link reaches to EXTRA.
"""

import json
import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit

from stario import Route

EXTRA: tuple[str, ...] = ()
LIMIT = 50

ACTION = re.compile(r"@(get|post|put|patch|delete)\(\s*'([^']*)'")
SIGNAL = re.compile(r"\$([A-Za-z_]\w*)")
ASSIGN = re.compile(r"\$([A-Za-z_]\w*)\s*=(?!=)")
KEY = re.compile(r"['\"]([A-Za-z_]\w*)['\"]\s*:")
QUOTED = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"")


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, list[tuple[str, str]], str]] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        pairs = [(k, v or "") for k, v in attrs]
        self.tags.append((tag, pairs, self.get_starttag_text() or ""))
        if tag == "a":
            self.links += [v for k, v in pairs if k == "href"]


def parse(html: str) -> Page:
    page = Page()
    page.feed(html)
    return page


def defined(page: Page) -> set[str]:
    names = {"_toast"}
    for _, attrs, _ in page.tags:
        for key, value in attrs:
            base, _, suffix = key.partition(":")
            base = base.split("__")[0]
            if base in ("data-bind", "data-ref", "data-indicator") and not suffix:
                names.add(value)
            elif base in ("data-signals", "data-computed", "data-signal", "data-bind") and suffix:
                names.add(suffix.split("__")[0].replace("-", "_"))
            elif base in ("data-signals", "data-computed"):
                try:
                    names |= set(json.loads(value))
                except ValueError:
                    names |= set(KEY.findall(value))
            if key.startswith("data-"):
                names |= set(ASSIGN.findall(QUOTED.sub("", value)))
    return names


def problems(client, url: str, page: Page) -> list[str]:
    found = []
    names = defined(page)
    ids: set[str] = set()
    for tag, attrs, _ in page.tags:
        for key, value in attrs:
            if key == "id":
                if value in ids:
                    found.append(f"{url}: two elements have id={value!r}")
                ids.add(value)
            if not key.startswith("data-") or key.startswith("data-signals"):
                continue
            for method, target in ACTION.findall(value):
                path = urlsplit(unescape(target)).path
                _, route, _ = client.app.find_handler("localhost", path, method.upper())
                if route is Route.empty():
                    found.append(f"{url}: {method.upper()} {path} has no route")
            for name in SIGNAL.findall(QUOTED.sub("", value)):
                if name not in names:
                    found.append(f"{url}: {key} reads ${name}, which no element defines")
        if tag == "dialog" and "open" not in dict(attrs).get("data-preserve-attr", ""):
            found.append(f'{url}: a <dialog> has no data.preserve_attr("open")')
    return found


def signals(page: Page) -> str:
    """The signals a Datastar request sends: every one without a leading _."""
    values: dict = {}
    for _, attrs, _ in page.tags:
        for key, value in attrs:
            if key.split("__")[0] == "data-signals":
                try:
                    values |= {k: v for k, v in json.loads(value).items() if k[0] != "_"}
                except ValueError:
                    pass
    return json.dumps(values)


async def stream_problems(client, url: str, page: Page) -> list[str]:
    found = []
    for tag, attrs, text in page.tags:
        init = dict(attrs).get("data-init", "")
        match = ACTION.search(init)
        if not match or match[1] != "get":
            continue
        if "id" not in dict(attrs):
            found.append(f"{url}: <{tag} data-init> opens a stream but has no id")
            continue
        live = unescape(match[2])
        async with client.stream(
            "GET", live, params={"datastar": signals(page)}, timeout=2
        ) as response:
            if response.status_code != 200:
                found.append(f"{url}: the stream {live} answers {response.status_code}")
                continue
            first = (await anext(response.iter_events()))["data"]
        if text not in first:
            found.append(f"{url}: the stream {live} changes the tag {text}")
    return found


async def check(client, url: str) -> list[str]:
    """The problems of one page. Empty when the page is not HTML."""
    r = await client.get(url)
    if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
        return []
    page = parse(r.text)
    return problems(client, url, page) + await stream_problems(client, url, page)


async def test_every_page_checks_out(client):
    queue, seen, found = ["/", *EXTRA], set(), []
    while queue and len(seen) < LIMIT:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        found += await check(client, url)
        r = await client.get(url)
        for href in parse(r.text).links if r.status_code == 200 else []:
            parts = urlsplit(href)
            if not parts.scheme and not parts.netloc and parts.path.startswith("/"):
                queue.append(parts.path + (f"?{parts.query}" if parts.query else ""))
    assert not found, "\n".join(found)
