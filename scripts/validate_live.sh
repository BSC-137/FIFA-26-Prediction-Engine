#!/usr/bin/env bash
# Validate live provider configuration (macOS / Linux).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

exec python -m fifa26_engine.scripts.validate_live "$@"
