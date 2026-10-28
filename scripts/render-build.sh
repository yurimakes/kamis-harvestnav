#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
python -m pip install -r requirements.txt
python -m pytest -q
npm --prefix frontend ci --include=dev
npm --prefix frontend run build
test -s frontend/dist/index.html
