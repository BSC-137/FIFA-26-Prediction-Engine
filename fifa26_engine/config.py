"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Competition constants — update here when API-Football publishes the 2026 IDs.
# See https://www.api-football.com/documentation-v3#tag/Leagues
# ---------------------------------------------------------------------------
WORLD_CUP_LEAGUE_ID: int = 1
SEASON: int = 2026


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


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
    world_cup_league_id: int = Field(
        default=WORLD_CUP_LEAGUE_ID,
        description="API-Football league ID for the FIFA World Cup.",
    )
    season: int = Field(
        default=SEASON,
        description="Season year for World Cup fixtures and team history.",
    )
    use_mock_data: bool | None = Field(
        default=None,
        description=(
            "Force mock provider when True. When unset, mock mode is used if no API key is set."
        ),
    )
    log_level: str = Field(
        default="INFO",
        description="Root logging level.",
    )
    api_football_base_url: str = Field(
        default="https://v3.football.api-sports.io",
        description="Base URL for the API-Football HTTP API.",
    )
    api_football_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        description="HTTP request timeout for API-Football calls.",
    )
    api_football_max_retries: int = Field(
        default=3,
        ge=1,
        description="Maximum retry attempts for transient API-Football failures.",
    )

    @field_validator("api_football_key", mode="before")
    @classmethod
    def strip_api_key(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @property
    def has_api_key(self) -> bool:
        """Return True when a non-empty API-Football key is configured."""
        return bool(self.api_football_key)

    @property
    def effective_use_mock_data(self) -> bool:
        """Return True when the mock provider should be used."""
        if self.use_mock_data is not None:
            return self.use_mock_data
        return not self.has_api_key


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings (singleton per process)."""
    return Settings()
