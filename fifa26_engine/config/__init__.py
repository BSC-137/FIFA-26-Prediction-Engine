"""Configuration package for the FIFA 26 prediction engine."""

from fifa26_engine.config.model_config import DEFAULT_DIXON_COLES_RHO, DEFAULT_MODEL_VERSION, ModelConfig
from fifa26_engine.config.paths import ENV_EXAMPLE, ENV_FILE, PROJECT_ROOT
from fifa26_engine.config.settings import (
    SEASON,
    WORLD_CUP_LEAGUE_ID,
    ConfigError,
    Settings,
    get_settings,
)

__all__ = [
    "DEFAULT_DIXON_COLES_RHO",
    "DEFAULT_MODEL_VERSION",
    "ENV_EXAMPLE",
    "ENV_FILE",
    "PROJECT_ROOT",
    "ConfigError",
    "ModelConfig",
    "SEASON",
    "Settings",
    "WORLD_CUP_LEAGUE_ID",
    "get_settings",
]
