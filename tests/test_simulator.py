"""Tests for vectorized match simulation and market aggregation."""

from __future__ import annotations

import numpy as np
import pytest

from fifa26_engine.data.mock_provider import MockFixtureProvider
from fifa26_engine.models.simulator import MatchSimulator
from fifa26_engine.services.prediction_service import predict_fixture_markets


def _simulator(home_xg: float, away_xg: float, **kwargs: object) -> MatchSimulator:
    return MatchSimulator(home_xg=home_xg, away_xg=away_xg, **kwargs)  # type: ignore[arg-type]


def test_score_matrix_is_vectorized_outer_product() -> None:
    simulator = _simulator(1.4, 1.1, max_goals=6)
    matrix = simulator.score_matrix()

    assert matrix.shape == (6, 6)
    assert matrix.sum() == pytest.approx(1.0, abs=0.01)  # truncation tail at max_goals=6
    # Independence: P(1,0) = P_h(1) * P_a(0)
    from scipy.stats import poisson

    assert matrix[1, 0] == pytest.approx(poisson.pmf(1, 1.4) * poisson.pmf(0, 1.1))


def test_dixon_coles_matrix_sums_to_one() -> None:
    simulator = _simulator(1.3, 1.2)
    raw = simulator.score_matrix()
    adjusted = simulator.apply_dixon_coles(raw)
    assert adjusted.sum() == pytest.approx(1.0, abs=1e-9)


def test_symmetric_teams_draw_near_highest_1x2() -> None:
    simulator = _simulator(1.25, 1.25)
    simulation = simulator.simulate()
    markets = simulation.markets

    outcomes = {
        "home_win": markets["home_win"],
        "draw": markets["draw"],
        "away_win": markets["away_win"],
    }
    # Dixon–Coles breaks exact symmetry but draw stays competitive for equal xG.
    assert markets["draw"] >= max(outcomes.values()) - 0.06
    assert abs(markets["home_win"] - markets["away_win"]) < 0.01


def test_strong_home_favorite_home_win_above_half() -> None:
    simulator = _simulator(2.8, 0.6)
    simulation = simulator.simulate()
    assert simulation.markets["home_win"] > 0.5
    assert simulator.most_likely_1x2_outcome(simulation.matrix) == "home_win"


def test_market_probabilities_within_unit_interval() -> None:
    simulator = _simulator(1.6, 1.0)
    simulation = simulator.simulate()
    markets = simulation.markets

    scalar_keys = [
        "home_win",
        "draw",
        "away_win",
        "btts_yes",
        "btts_no",
        "over_1_5",
        "under_1_5",
        "over_2_5",
        "under_2_5",
        "over_3_5",
        "under_3_5",
    ]
    for key in scalar_keys:
        value = markets[key]  # type: ignore[literal-required]
        assert 0.0 <= value <= 1.0, f"{key}={value}"

    assert markets["btts_yes"] + markets["btts_no"] == pytest.approx(1.0)
    assert markets["over_2_5"] + markets["under_2_5"] == pytest.approx(1.0)


def test_top_scores_returns_five_entries() -> None:
    simulator = _simulator(1.5, 1.2)
    simulation = simulator.simulate()
    top_scores = simulation.markets["top_scores"]

    assert len(top_scores) == 5
    assert all("score" in entry and "probability" in entry for entry in top_scores)
    assert top_scores[0]["probability"] >= top_scores[-1]["probability"]


def test_simulation_result_fields() -> None:
    simulator = _simulator(1.4, 1.0, dixon_coles_rho=-0.10)
    result = simulator.simulate()

    assert result.home_xg == 1.4
    assert result.away_xg == 1.0
    assert result.dixon_coles_rho == -0.10
    assert isinstance(result.matrix, np.ndarray)
    assert result.matrix.shape == (10, 10)


@pytest.mark.asyncio
async def test_predict_fixture_markets_integration() -> None:
    provider = MockFixtureProvider()
    fixture = await provider.get_fixture_by_id("wc26-005")
    assert fixture is not None

    simulation = await predict_fixture_markets(fixture, provider)
    assert simulation.base_home_xg > 0
    assert simulation.adjusted_home_xg > 0
    assert simulation.simulation.matrix.sum() == pytest.approx(1.0, abs=1e-9)
    assert 0.0 < simulation.simulation.markets["home_win"] < 1.0
