"""Model hyperparameters loaded from environment variables."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fifa26_engine.config.settings import Settings

DEFAULT_DIXON_COLES_RHO = -0.13
DEFAULT_KNOCKOUT_DIXON_COLES_RHO = -0.08
DEFAULT_MODEL_VERSION = "1.1.0"
DEFAULT_TOURNAMENT_MIN_TOTAL_XG = 2.0
DEFAULT_KNOCKOUT_MIN_TOTAL_XG = 2.4
DEFAULT_ELO_BLEND_WEIGHT = 0.25
DEFAULT_HOST_NATION_BOOST = 0.12
DEFAULT_TOURNAMENT_SCORING_PRIOR_WEIGHT = 0.20
DEFAULT_TIME_DECAY_HALF_LIFE_DAYS = 21.0


@dataclass(frozen=True)
class ModelConfig:
    """Prediction pipeline hyperparameters (env-overridable via ``Settings``)."""

    team_history_limit: int = 30
    shrinkage_prior_matches: float = 8.0
    dixon_coles_rho: float = DEFAULT_DIXON_COLES_RHO
    weather_delta_scale: float = 0.35
    weather_min_bucket_samples: int = 5
    intercept_prior_goals: float = 1.45
    time_decay_half_life_days: float = DEFAULT_TIME_DECAY_HALF_LIFE_DAYS
    tournament_min_total_xg: float = DEFAULT_TOURNAMENT_MIN_TOTAL_XG
    knockout_min_total_xg: float = DEFAULT_KNOCKOUT_MIN_TOTAL_XG
    knockout_dixon_coles_rho: float = DEFAULT_KNOCKOUT_DIXON_COLES_RHO
    tournament_scoring_prior_weight: float = DEFAULT_TOURNAMENT_SCORING_PRIOR_WEIGHT
    elo_blend_weight: float = DEFAULT_ELO_BLEND_WEIGHT
    host_nation_boost: float = DEFAULT_HOST_NATION_BOOST
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
            tournament_min_total_xg=settings.tournament_min_total_xg,
            knockout_min_total_xg=settings.knockout_min_total_xg,
            knockout_dixon_coles_rho=settings.knockout_dixon_coles_rho,
            tournament_scoring_prior_weight=settings.tournament_scoring_prior_weight,
            elo_blend_weight=settings.elo_blend_weight,
            host_nation_boost=settings.host_nation_boost,
            model_version=settings.model_version,
        )

    def with_overrides(self, **kwargs: object) -> ModelConfig:
        """Return a copy with selected fields replaced (for tuning scripts)."""
        return replace(self, **kwargs)  # type: ignore[arg-type]
