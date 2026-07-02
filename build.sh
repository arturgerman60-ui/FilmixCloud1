#!/usr/bin/env bash
# ==========================================================================
# FunPay AutoResponder — build script (Linux / macOS)
# Creates a standalone bundle in dist/FunPayAutoResponder/
# ==========================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"

echo "==> Creating virtual environment (.venv)"
[ -d .venv ] || "$PY" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Installing dependencies"
pip install --upgrade pip >/dev/null
pip install -r requirements.txt

echo "==> Generating assets (icons + sounds)"
python scripts/generate_assets.py

echo "==> Installing Playwright browser (chromium)"
python -m playwright install chromium || echo "  (skipped — install manually if needed)"

echo "==> Building with PyInstaller"
pyinstaller --noconfirm FunPayAutoResponder.spec

echo ""
echo "Build complete: dist/FunPayAutoResponder/"
