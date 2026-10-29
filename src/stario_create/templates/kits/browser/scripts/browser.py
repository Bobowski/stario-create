"""The rare browser check, for client JavaScript that holds state.

Run: uv run --with playwright python scripts/browser.py /todos

It starts the app on a free port with the settings in .env, opens the page
in two tabs, runs `steps`, saves a screenshot, and stops the app. It prints
each console error. Edit `steps` for the change you check. A page that only
renders HTML needs no browser: its TestClient test is the proof.
"""

import asyncio
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.async_api import Page, async_playwright, expect


async def steps(actor: Page, viewer: Page) -> None:
    # Example: drag in one tab, and see the result in the other.
    await expect(viewer.locator("body")).to_be_visible()


def dotenv() -> dict[str, str]:
    """The settings in .env, as `just dev` loads them."""
    path = Path(".env")
    lines = path.read_text().splitlines() if path.is_file() else []
    pairs = [line.split("=", 1) for line in lines if "=" in line and line[0] != "#"]
    return {key.strip(): value.strip().strip("'\"") for key, value in pairs}


async def up(server: subprocess.Popen[bytes], port: int) -> None:
    """Wait until the app listens. Stop when it exits."""
    for _ in range(100):
        if server.poll() is not None:
            raise SystemExit(f"the app exited with {server.returncode}")
        try:
            _, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.close()
            return
        except OSError:
            await asyncio.sleep(0.1)
    raise SystemExit("the app did not listen within 10 seconds")


async def main(path: str) -> None:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    data = tempfile.mkdtemp(prefix="browser-check-")
    env = os.environ | dotenv() | {"STARIO_PORT": str(port), "PROJECT_DATA_DIR": data}
    server = subprocess.Popen([sys.executable, "-m", "app.main"], env=env)
    try:
        await up(server, port)
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()
            actor, viewer = await context.new_page(), await context.new_page()
            for tab in (actor, viewer):
                tab.on("console", lambda m: m.type == "error" and print("console:", m.text))
                await tab.goto(f"http://127.0.0.1:{port}{path}")
            await steps(actor, viewer)
            await viewer.screenshot(path=f"{data}/page.png")
            print(f"screenshot: {data}/page.png")
            await browser.close()
    finally:
        server.terminate()
        server.wait(5)


asyncio.run(asyncio.wait_for(main(sys.argv[1] if len(sys.argv) > 1 else "/"), 60))
