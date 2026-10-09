#!/bin/sh
# Create a Stario app that runs, with AGENTS.md and the skills in place.
#
#   curl -fsSL https://stario.dev/setup.sh | sh -s -- my-app
#
# Result: one static screen at /, the layout from AGENTS.md, tests that pass.
set -eu

name="${1:?usage: setup.sh <app-name>}"
command -v uv >/dev/null 2>&1 || { echo "setup: install uv first: https://docs.astral.sh/uv/" >&2; exit 1; }

uv init --app --python 3.14 "$name"
cd "$name"
rm -f main.py

uv add "stario>=4,<5"
uv add --dev ruff pyright pytest pytest-asyncio

mkdir -p app/common app/features/home static/css static/js tests
touch app/__init__.py app/common/__init__.py app/features/__init__.py app/features/home/__init__.py tests/__init__.py

curl -fsSL -o static/js/datastar.js https://cdn.jsdelivr.net/gh/starfederation/datastar@v1.0.2/bundles/datastar.js
curl -fsSL -o AGENTS.md https://stario.dev/AGENTS.md
printf '@AGENTS.md\n' > CLAUDE.md
printf '*.sqlite3*\n' >> .gitignore

cat >> pyproject.toml <<'EOF'

[tool.ruff]
target-version = "py314"
line-length = 100
src = ["app", "tests"]

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
EOF

cat > static/css/style.css <<'EOF'
body { font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 40rem; line-height: 1.5; }
EOF

cat > app/config.py <<EOF
import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Config:
    app_name: str
    db_path: str

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            app_name=os.environ.get("APP_NAME", "${name}"),
            db_path=os.environ.get("APP_DB_PATH", "app.sqlite3"),
        )
EOF

cat > app/assets.py <<'EOF'
from pathlib import Path

from stario import Assets

ASSETS = Assets(Path(__file__).resolve().parents[1] / "static", url_prefix="/static")
STYLE_CSS = ASSETS.href("css/style.css")
DATASTAR_JS = ASSETS.href("js/datastar.js")
EOF

cat > app/common/shell.py <<'EOF'
from stario.datastar import ModuleScript
from stario.markup import HtmlElement, baked
from stario.markup import html as h

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
EOF

cat > app/features/home/urls.py <<'EOF'
from stario import Route

HOME = Route("GET /")
EOF

cat > app/features/home/views.py <<'EOF'
from stario.markup import HtmlElement
from stario.markup import html as h

from app.common.shell import page


def render(app_name: str) -> HtmlElement:
    return page(
        app_name,
        h.Main(
            {"id": "home"},
            h.H1(app_name),
            h.P("Stario is running. Read AGENTS.md, then add a screen."),
        ),
    )
EOF

cat > app/features/home/handlers.py <<'EOF'
from stario import App, Context, Writer, responses

from app.features.home.urls import HOME
from app.features.home.views import render


def show_home(app_name: str):
    async def handler(c: Context, w: Writer) -> None:
        responses.html(w, render(app_name))

    return handler


def register_home(app: App, app_name: str) -> None:
    app.add(HOME, show_home(app_name))
EOF

cat > app/main.py <<'EOF'
from stario import App, Span

from app.assets import ASSETS
from app.config import Config
from app.features.home.handlers import register_home


async def bootstrap(app: App, span: Span):
    config = Config.from_env()
    span.attrs(await ASSETS.attach(app))
    register_home(app, config.app_name)
    yield
EOF

cat > tests/conftest.py <<'EOF'
import pytest
from stario.testing import TestClient

from app.main import bootstrap


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "app.sqlite3"))
    async with TestClient(bootstrap) as c:
        yield c
EOF

cat > tests/test_home.py <<'EOF'
from app.features.home.urls import HOME


async def test_home_loads(client):
    r = await client.get(HOME.href())
    assert r.status_code == 200
    assert 'id="home"' in r.text
EOF

for skill in stario-feature stario-auth stario-litewriter stario-tailwind-daisyui; do
    mkdir -p ".agents/skills/$skill"
    curl -fsSL -o ".agents/skills/$skill/SKILL.md" "https://stario.dev/skills/$skill/SKILL.md"
done

echo
echo "done. next:"
echo "  skills are in .agents/skills/. For other agent folders: npx skills add bobowski/stario-skills --yes"
echo "  cd $name"
echo "  uv run stario watch app.main:bootstrap   # http://127.0.0.1:8000"
echo "  uv run pytest"
