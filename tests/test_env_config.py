"""Tests for project-root .env path resolution."""

from __future__ import annotations

from pathlib import Path

from fifa26_engine.config import ENV_FILE, PROJECT_ROOT, Settings


def test_env_file_is_at_project_root() -> None:
    assert ENV_FILE == PROJECT_ROOT / ".env"
    assert (PROJECT_ROOT / "pyproject.toml").is_file()


def test_settings_reads_api_key_from_env_file(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("API_FOOTBALL_KEY=file-key-123\n", encoding="utf-8")

    settings = Settings(_env_file=env_path)

    assert settings.api_football_key == "file-key-123"
    assert settings.has_api_key is True
