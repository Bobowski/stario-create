#!/bin/sh
# Create a Stario app. The real entry point is the stario-create CLI:
#
#   uvx stario-create new my-app
#
# This shim keeps the curl endpoint working:
#
#   curl -fsSL https://stario.dev/setup.sh | sh -s -- my-app
#
# It builds the CLI from the git repo, so it works before any release is on
# PyPI. Once stario-create is published, this can become
# `exec uvx stario-create new "$@"`.
set -eu

command -v uv >/dev/null 2>&1 || {
    echo "setup: install uv first: https://docs.astral.sh/uv/" >&2
    exit 1
}

exec uvx --from "git+https://github.com/bobowski/stario-create" stario-create new "$@"
