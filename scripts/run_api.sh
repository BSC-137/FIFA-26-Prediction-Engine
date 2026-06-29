#!/usr/bin/env bash
# Run the FIFA 26 Prediction Engine API (macOS / Linux)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate
pip install -e . -q

echo "Starting API on http://127.0.0.1:8000"
exec uvicorn fifa26_engine.api.main:app --reload --host 0.0.0.0 --port 8000
