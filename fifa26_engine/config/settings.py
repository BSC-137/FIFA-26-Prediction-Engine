"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from fifa26_engine.config.model_config import DEFAULT_DIXON_COLES_RHO, DEFAULT_MODEL_VERSION
from fifa26_engine.config.paths import ENV_FILE

# ---------------------------------------------------------------------------
# Competition constants — update here when API-Football publishes the 2026 IDs.
# See https://www.api-football.com/documentation-v3#tag/Leagues
# ---------------------------------------------------------------------------
WORLD_CUP_LEAGUE_ID: int = 1
SEASON: int = 2026


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


class Settings(BaseSettings):
    """Runtime settings for the prediction engine.

    Loads ``project_root/.env`` regardless of the process working directory.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
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
    weather_provider: Literal["openmeteo", "mock"] = Field(
        default="mock",
        description="Weather data source: Open-Meteo (free) or deterministic mock.",
    )
    weather_cache_ttl_seconds: int = Field(
        default=1800,
        ge=0,
        description="TTL for cached weather forecast responses.",
    )
    fixtures_cache_ttl_seconds: int = Field(
        default=300,
        ge=0,
        description="TTL for cached /fixtures API responses (default 5 minutes).",
    )
    predictions_cache_ttl_seconds: int = Field(
        default=600,
        ge=0,
        description="TTL for cached /predict API responses (default 10 minutes).",
    )
    refresh_interval_seconds: int = Field(
        default=300,
        ge=30,
        description="Background fixture cache refresh interval in seconds.",
    )
    refresh_enabled: bool = Field(
        default=True,
        description="Enable automatic background fixture cache refresh.",
    )
    predictions_db_path: str = Field(
        default="predictions.db",
        description="SQLite file path for the prediction ledger.",
    )
    accuracy_admin_key: str = Field(
        default="",
        description="Optional key required for POST /accuracy/recompute (empty = allow in dev).",
    )

    # Model hyperparameters (see ModelConfig)
    team_history_limit: int = Field(
        default=30,
        ge=1,
        le=500,
        description="Max recent NT results per team used for fitting.",
    )
    shrinkage_prior_matches: float = Field(
        default=8.0,
        gt=0.0,
        description="Pseudo-match count for team rating shrinkage toward average.",
    )
    dixon_coles_rho: float | None = Field(
        default=None,
        description=f"Dixon-Coles low-score correlation (default {DEFAULT_DIXON_COLES_RHO}).",
    )
    weather_delta_scale: float = Field(
        default=0.35,
        gt=0.0,
        description="Scale factor for weather affinity xG modifiers.",
    )
    weather_min_bucket_samples: int = Field(
        default=5,
        ge=1,
        description="Minimum bucket samples before full weather affinity weight.",
    )
    intercept_prior_goals: float = Field(
        default=1.35,
        gt=0.0,
        description="Baseline goals rate when no training data is available.",
    )
    time_decay_half_life_days: float = Field(
        default=0.0,
        ge=0.0,
        description="Exponential decay half-life for match weights (0 = disabled).",
    )
    model_version: str = Field(
        default=DEFAULT_MODEL_VERSION,
        description="Version tag stored in predictions and exposed via /model/info.",
    )

    @field_validator("api_football_key", mode="before")
    @classmethod
    def strip_api_key(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("dixon_coles_rho", mode="before")
    @classmethod
    def empty_dixon_coles_rho(cls, value: object) -> float | None:
        if value is None or value == "":
            return None
        return float(value)  # type: ignore[arg-type]

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
