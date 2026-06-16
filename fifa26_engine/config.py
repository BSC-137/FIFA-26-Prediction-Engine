"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the prediction engine."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_football_key: str = Field(
        default="",
        description="API-Football API key; empty enables mock/offline mode.",
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        ge=0,
        description="Default TTL for in-memory cache entries in seconds.",
    )
    world_cup_competition_id: int = Field(
        default=1,
        description="API-Football competition/league ID for the World Cup.",
    )
    world_cup_season: int = Field(
        default=2026,
        description="Season year for World Cup fixtures.",
    )
    log_level: str = Field(
        default="INFO",
        description="Root logging level.",
    )
    api_football_base_url: str = Field(
        default="https://v3.football.api-sports.io",
        description="Base URL for the API-Football HTTP API.",
    )

    @property
    def has_api_key(self) -> bool:
        """Return True when a non-empty API-Football key is configured."""
        return bool(self.api_football_key.strip())


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings (singleton per process)."""
    return Settings()
