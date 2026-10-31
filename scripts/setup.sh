#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="$PWD/.cache/uv"
export UV_PYTHON_INSTALL_DIR="$PWD/.python"
if [ ! -x .tools/uv ]; then
  installer="$(mktemp)"
  curl -LsSf https://astral.sh/uv/install.sh -o "$installer"
  UV_INSTALL_DIR="$PWD/.tools" UV_NO_MODIFY_PATH=1 sh "$installer"
  rm "$installer"
fi
.tools/uv sync --frozen --python 3.12 --no-editable
.venv/bin/memory setup-models
if [ ! -e .env ]; then cp .env.example .env; chmod 600 .env; fi
printf '\nSetup complete. Add your Reactor settings to .env for live answers.\n'
