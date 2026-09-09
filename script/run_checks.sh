#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"

cd "$ROOT_DIR"

echo "==> Installing project dependencies"
"$PYTHON_BIN" -m pip install \
    --root-user-action=ignore \
    -e ".[cli]"

if ! "$PYTHON_BIN" -m ruff --version >/dev/null 2>&1; then
    echo "==> Installing Ruff"
    "$PYTHON_BIN" -m pip install \
        --root-user-action=ignore \
        "ruff>=0.15,<0.17"
fi

if ! "$PYTHON_BIN" -c "import pytest, pytest_asyncio" >/dev/null 2>&1; then
    echo "==> Installing test dependencies"
    "$PYTHON_BIN" -m pip install \
        --root-user-action=ignore \
        "pytest>=8" \
        "pytest-asyncio>=0.24"
fi

if ! "$PYTHON_BIN" -c "import build" >/dev/null 2>&1; then
    echo "==> Installing build"
    "$PYTHON_BIN" -m pip install \
        --root-user-action=ignore \
        build
fi

echo "==> Checking formatting"
"$PYTHON_BIN" -m ruff format --check .

echo "==> Running Ruff"
"$PYTHON_BIN" -m ruff check .

echo "==> Compiling sources"
"$PYTHON_BIN" -m compileall -q src tests script

echo "==> Running tests"
"$PYTHON_BIN" -m pytest

echo "==> Building package"
rm -rf "$ROOT_DIR/dist"
"$PYTHON_BIN" -m build

echo "==> All checks passed"
