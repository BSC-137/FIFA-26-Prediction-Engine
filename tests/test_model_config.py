"""Tests for ModelConfig wiring and time-decay weighting."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from fifa26_engine.config import ModelConfig, Settings
from fifa26_engine.config.model_config import DEFAULT_DIXON_COLES_RHO
from fifa26_engine.data.provider import MatchResult
from fifa26_engine.models.strength import TeamStrengthModel
from fifa26_engine.services.prediction_service import PredictionService

UTC = timezone.utc
BASE_DATE = datetime(2025, 1, 1, tzinfo=UTC)


def _result(
    match_id: str,
    day_offset: int,
    home_id: str,
    away_id: str,
    home_goals: int,
    away_goals: int,
) -> MatchResult:
    return MatchResult(
        match_id=match_id,
        date=BASE_DATE + timedelta(days=day_offset),
        home_team_id=home_id,
        away_team_id=away_id,
        home_goals=home_goals,
        away_goals=away_goals,
        is_neutral=False,
        competition="Friendly",
    )


def test_model_config_from_settings_uses_env_defaults() -> None:
    settings = Settings(
        team_history_limit=40,
        shrinkage_prior_matches=6.0,
        dixon_coles_rho=None,
        weather_delta_scale=0.4,
        time_decay_half_life_days=90.0,
        model_version="test-v2",
    )
    config = ModelConfig.from_settings(settings)

    assert config.team_history_limit == 40
    assert config.shrinkage_prior_matches == 6.0
    assert config.dixon_coles_rho == DEFAULT_DIXON_COLES_RHO
    assert config.weather_delta_scale == 0.4
    assert config.time_decay_half_life_days == 90.0
    assert config.model_version == "test-v2"


def test_model_config_with_overrides() -> None:
    base = ModelConfig()
    updated = base.with_overrides(dixon_coles_rho=-0.1, team_history_limit=25)
    assert updated.dixon_coles_rho == -0.1
    assert updated.team_history_limit == 25
    assert updated.shrinkage_prior_matches == base.shrinkage_prior_matches


def test_prediction_service_uses_model_config() -> None:
    config = ModelConfig(
        team_history_limit=15,
        shrinkage_prior_matches=5.0,
        dixon_coles_rho=-0.1,
        model_version="wired-test",
    )
    service = PredictionService(model_config=config)
    assert service.model_config.team_history_limit == 15
    assert service.model_config.dixon_coles_rho == -0.1
    assert service.model_config.model_version == "wired-test"


def test_time_decay_weights_favor_recent_matches() -> None:
    old_results = [
        _result("old-1", 0, "A", "B", 0, 3),
        _result("old-2", 1, "A", "C", 0, 3),
        _result("old-3", 2, "A", "D", 0, 3),
    ]
    recent_results = [
        _result("new-1", 200, "A", "B", 3, 0),
        _result("new-2", 201, "A", "C", 3, 0),
        _result("new-3", 202, "A", "D", 3, 0),
        *old_results,
    ]

    chronological = [*old_results, recent_results[0], recent_results[1], recent_results[2]]

    model_uniform = TeamStrengthModel(time_decay_half_life_days=0.0)
    model_uniform.fit(chronological)
    model_decay = TeamStrengthModel(time_decay_half_life_days=30.0)
    model_decay.fit(chronological)

    uniform_weights = model_uniform._compute_match_weights(chronological)
    decay_weights = model_decay._compute_match_weights(chronological)

    assert np.allclose(uniform_weights, 1.0)
    assert decay_weights[-1] > decay_weights[0]

    uniform_attack = model_uniform.get_team_params("A")["attack"]
    decay_attack = model_decay.get_team_params("A")["attack"]
    assert decay_attack > uniform_attack


def test_empty_fit_uses_intercept_prior_goals() -> None:
    prior_goals = 1.6
    model = TeamStrengthModel(intercept_prior_goals=prior_goals)
    model.fit([])
    home_xg, away_xg = model.expected_goals("X", "Y", is_neutral=True)
    assert home_xg == pytest.approx(prior_goals, rel=0.05)
    assert away_xg == pytest.approx(prior_goals, rel=0.05)
