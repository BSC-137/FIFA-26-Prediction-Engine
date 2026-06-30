"""Model hyperparameters loaded from environment variables."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fifa26_engine.config.settings import Settings

DEFAULT_DIXON_COLES_RHO = -0.13
DEFAULT_MODEL_VERSION = "0.2.0"


@dataclass(frozen=True)
class ModelConfig:
    """Prediction pipeline hyperparameters (env-overridable via ``Settings``)."""

    team_history_limit: int = 30
    shrinkage_prior_matches: float = 8.0
    dixon_coles_rho: float = DEFAULT_DIXON_COLES_RHO
    weather_delta_scale: float = 0.35
    weather_min_bucket_samples: int = 5
    intercept_prior_goals: float = 1.35
    time_decay_half_life_days: float = 0.0
    model_version: str = DEFAULT_MODEL_VERSION

    @classmethod
    def from_settings(cls, settings: Settings) -> ModelConfig:
        """Build config from application settings."""
        rho = settings.dixon_coles_rho
        return cls(
            team_history_limit=settings.team_history_limit,
            shrinkage_prior_matches=settings.shrinkage_prior_matches,
            dixon_coles_rho=rho if rho is not None else DEFAULT_DIXON_COLES_RHO,
            weather_delta_scale=settings.weather_delta_scale,
            weather_min_bucket_samples=settings.weather_min_bucket_samples,
            intercept_prior_goals=settings.intercept_prior_goals,
            time_decay_half_life_days=settings.time_decay_half_life_days,
            model_version=settings.model_version,
        )

    def with_overrides(self, **kwargs: object) -> ModelConfig:
        """Return a copy with selected fields replaced (for tuning scripts)."""
        return replace(self, **kwargs)  # type: ignore[arg-type]
