"""Project root and environment file paths."""

from __future__ import annotations

from pathlib import Path

# fifa26_engine/config/paths.py -> project root is two levels up from this package
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
