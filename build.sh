#!/usr/bin/env bash
set -euo pipefail

git submodule update --init --depth 1 --recursive

curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

uv run python -m scale_library.website
