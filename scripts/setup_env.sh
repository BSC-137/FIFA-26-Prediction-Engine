#!/usr/bin/env bash
# Run from the project root to create a local .env for API keys (macOS / Linux).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ENV_FILE="$ROOT/.env"
EXAMPLE_FILE="$ROOT/.env.example"

if [ -f "$ENV_FILE" ]; then
  echo ".env already exists at: $ENV_FILE"
elif [ -f "$EXAMPLE_FILE" ]; then
  cp "$EXAMPLE_FILE" "$ENV_FILE"
  echo "Created .env from .env.example at: $ENV_FILE"
else
  echo "error: .env.example not found in $ROOT" >&2
  exit 1
fi

cat <<EOF

Next steps:
  1. Open $ENV_FILE
  2. Paste your API-Football key:
       API_FOOTBALL_KEY=your_key_here
  3. Get a key at https://www.api-football.com/
  4. Set USE_MOCK_DATA=false to use live fixture data

Verify after starting the API:
  GET http://localhost:8000/health   -> source should be api-football
  GET http://localhost:8000/status   -> provider_mode should be api

Never commit .env — it is listed in .gitignore.
EOF
