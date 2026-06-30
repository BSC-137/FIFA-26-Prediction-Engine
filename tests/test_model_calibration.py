"""Tests for WC 2026 model calibration (draw inflation fixes)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from fifa26_engine.config.model_config import ModelConfig
from fifa26_engine.data.provider import Fixture, MatchResult
from fifa26_engine.models.calibration import apply_host_boost, calibrate_base_xg
from fifa26_engine.models.knockout import compute_knockout_markets
from fifa26_engine.models.simulator import MatchSimulator
from fifa26_engine.models.strength import TeamStrengthModel, infer_fixture_is_neutral

UTC = timezone.utc
BASE = datetime(2026, 6, 1, tzinfo=UTC)
WC = "FIFA World Cup 2026"


def _wc_result(
    match_id: str,
    day: int,
    home_id: str,
    away_id: str,
    home_goals: int,
    away_goals: int,
) -> MatchResult:
    return MatchResult(
        match_id=match_id,
        date=BASE + timedelta(days=day),
        home_team_id=home_id,
        away_team_id=away_id,
        home_goals=home_goals,
        away_goals=away_goals,
        is_neutral=True,
        competition=WC,
    )


def _build_france_dominant_pool() -> list[MatchResult]:
    results: list[MatchResult] = []
    day = 0
    for opponent, hg, ag in [
        ("sweden", 3, 0),
        ("poland", 4, 1),
        ("austria", 2, 0),
    ]:
        results.append(_wc_result(f"fr-{opponent}", day, "france", opponent, hg, ag))
        day += 1
    for opponent, hg, ag in [
        ("sweden", 0, 3),
        ("poland", 1, 4),
        ("austria", 0, 2),
    ]:
        results.append(_wc_result(f"{opponent}-fr", day, opponent, "france", hg, ag))
        day += 1
    results.extend(
        [
            _wc_result("mx-1", day, "mexico", "south-africa", 2, 0),
            _wc_result("mx-2", day + 1, "mexico", "south-korea", 3, 1),
            _wc_result("mx-3", day + 2, "mexico", "czech-republic", 2, 0),
        ],
    )
    return results


def _fixture(home_id: str, away_id: str, home_name: str, away_name: str, stage: str) -> Fixture:
    return Fixture(
        fixture_id="test-fixture",
        home_team_id=home_id,
        away_team_id=away_id,
        home_team_name=home_name,
        away_team_name=away_name,
        kickoff_utc=datetime(2026, 6, 30, tzinfo=UTC),
        status="scheduled",
        competition=WC,
        stage=stage,
        venue="MetLife Stadium",
        home_goals=None,
        away_goals=None,
        stadium_lat=40.8128,
        stadium_lon=-74.0742,
        pitch_type="hybrid",
    )


def test_france_vs_weak_gets_realistic_xg_after_calibration() -> None:
    results = _build_france_dominant_pool()
    config = ModelConfig(
        tournament_min_total_xg=1.6,
        elo_blend_weight=0.25,
        host_nation_boost=0.12,
    )
    model = TeamStrengthModel.from_results(results, model_config=config)
    fixture = _fixture("france", "sweden", "France", "Sweden", "Round of 32")
    prediction = model.predict_fixture(fixture)
    home_xg, away_xg, labels, _ = calibrate_base_xg(prediction, fixture, results, config)

    assert home_xg > 1.0
    assert home_xg > away_xg
    assert "tournament_scoring_floor_applied" in labels or home_xg + away_xg >= 1.6

    sim = MatchSimulator(home_xg=home_xg, away_xg=away_xg).simulate()
    assert sim.markets["draw"] < 0.45
    assert sim.markets["home_win"] > sim.markets["draw"]


def test_mexico_host_boost_increases_home_xg() -> None:
    results = _build_france_dominant_pool()
    config = ModelConfig(host_nation_boost=0.12, elo_blend_weight=0.0, tournament_min_total_xg=0.0)
    model = TeamStrengthModel.from_results(results, model_config=config)
    fixture = _fixture("mexico", "ecuador", "Mexico", "Ecuador", "Group A - Matchday 3")
    prediction = model.predict_fixture(fixture)

    neutral_home, neutral_away, _, _ = calibrate_base_xg(
        prediction,
        _fixture("mexico", "ecuador", "Mexico", "Ecuador", "Group A - Matchday 3"),
        results,
        ModelConfig(host_nation_boost=0.0, elo_blend_weight=0.0, tournament_min_total_xg=0.0),
    )
    host_home, host_away, labels, applied = calibrate_base_xg(prediction, fixture, results, config)

    assert applied > 0.0
    assert "host_nation_boost" in "".join(labels)
    assert host_home > neutral_home
    assert host_away == pytest.approx(neutral_away)


def test_knockout_advance_probs_sum_to_one() -> None:
    markets = compute_knockout_markets(1.4, 1.1)
    assert markets.advance_home + markets.advance_away == pytest.approx(1.0, abs=1e-6)
    assert markets.regulation_home_win + markets.regulation_draw + markets.regulation_away_win == pytest.approx(
        1.0,
        abs=1e-6,
    )


def test_low_xg_floor_reduces_draw_inflation() -> None:
    low_home, low_away = 0.38, 0.21
    sim_before = MatchSimulator(home_xg=low_home, away_xg=low_away).simulate()
    from fifa26_engine.models.calibration import apply_tournament_scoring_floor

    floored_home, floored_away, applied = apply_tournament_scoring_floor(
        low_home,
        low_away,
        is_neutral=True,
        floor=1.6,
    )
    sim_after = MatchSimulator(home_xg=floored_home, away_xg=floored_away).simulate()

    assert applied is True
    assert sim_after.markets["draw"] < sim_before.markets["draw"]


@pytest.mark.asyncio
async def test_predict_upcoming_import_runs_without_attribute_error() -> None:
    import importlib.util
    from pathlib import Path

    script = Path(__file__).resolve().parents[1] / "scripts" / "predict_upcoming.py"
    spec = importlib.util.spec_from_file_location("predict_upcoming", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "_build_prediction_entry")
    assert callable(module.main)


def test_infer_fixture_is_neutral_for_wc2026() -> None:
    fixture = _fixture("france", "sweden", "France", "Sweden", "Round of 32")
    assert infer_fixture_is_neutral(fixture) is True
