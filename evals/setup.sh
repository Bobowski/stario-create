#!/bin/sh
# setup.sh — scaffold the eval base apps into $EVAL_DIR (default /tmp/stario-eval).
# evalapp tracks the released stario; evalapp-local adds an editable STARIO_PATH
# source (skipped when STARIO_PATH is unset). evalapp-todos/-bug derive from
# evalapp-local when it exists, else from evalapp, for the edit tasks T8–T10.
set -eu
root=${EVAL_DIR:-/tmp/stario-eval}
here=$(cd "$(dirname "$0")" && pwd)
sc="$here/.."

uv run --project "$sc" --package stario-create stario-create new evalapp --dir "$root"
cd "$root/evalapp"
git init -q && git add -A && git commit -qm base
rm -rf .venv

base=evalapp
if [ -n "${STARIO_PATH:-}" ]; then
    cp -R "$root/evalapp" "$root/evalapp-local"
    printf '\n[tool.uv.sources]\nstario = { path = "%s", editable = true }\n' "$STARIO_PATH" \
        >>"$root/evalapp-local/pyproject.toml"
    cd "$root/evalapp-local"
    uv sync -q
    git add -A && git commit -qm "local stario"
    rm -rf .venv
    base=evalapp-local
fi

cp -R "$root/$base" "$root/evalapp-todos"
cp -R "$here/fixtures/todos/app" "$root/evalapp-todos/"
cp -R "$here/fixtures/todos/tests" "$root/evalapp-todos/"
cd "$root/evalapp-todos"
if [ -n "${LITEWRITER_PATH:-}" ]; then
    grep -q '^\[tool.uv.sources\]' pyproject.toml || printf '\n[tool.uv.sources]\n' >>pyproject.toml
    printf 'litewriter = { path = "%s", editable = true }\n' "$LITEWRITER_PATH" >>pyproject.toml
fi
uv add -q "litewriter>=0.3,<0.4"
uv run pytest -q
git add -A && git commit -qm "todos screen"

cp -R "$root/evalapp-todos" "$root/evalapp-todos-bug"
cd "$root/evalapp-todos-bug"
uv run python "$here/fixtures/plant_bug.py"
uv run pytest -q
git add -A && git commit -qm "relay for live updates"

rm -rf "$root/evalapp-todos/.venv" "$root/evalapp-todos-bug/.venv"
