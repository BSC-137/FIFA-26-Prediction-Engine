"""Tests for leakage-safe accuracy evaluation."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from fifa26_engine.data.provider import Fixture
from fifa26_engine.models.evaluation import evaluate_predictions
from fifa26_engine.storage.prediction_store import PredictionRecord

UTC = timezone.utc


def _record(
    fixture_id: str,
    p_home: float,
    p_draw: float,
    p_away: float,
    adj_home: float = 1.5,
    adj_away: float = 1.0,
) -> PredictionRecord:
    return PredictionRecord(
        fixture_id=fixture_id,
        generated_at_utc=datetime(2026, 6, 1, tzinfo=UTC),
        as_of_utc=datetime(2026, 6, 10, 12, tzinfo=UTC),
        kickoff_utc=datetime(2026, 6, 11, 19, tzinfo=UTC),
        home_team_id="h1",
        away_team_id="a1",
        base_home_xg=adj_home,
        base_away_xg=adj_away,
        adj_home_xg=adj_home,
        adj_away_xg=adj_away,
        p_home=p_home,
        p_draw=p_draw,
        p_away=p_away,
        top_score_json="[]",
        weather_json=None,
        adjustments_json="{}",
        model_version="test-v1",
    )


def _finished_fixture(fixture_id: str, home: int, away: int) -> Fixture:
    return Fixture(
        fixture_id=fixture_id,
        home_team_id="h1",
        away_team_id="a1",
        home_team_name="Home",
        away_team_name="Away",
        kickoff_utc=datetime(2026, 6, 11, 19, tzinfo=UTC),
        status="finished",
        competition="FIFA World Cup 2026",
        stage="Group",
        venue="Test",
        home_goals=home,
        away_goals=away,
    )


def test_evaluation_computes_metrics() -> None:
    records = [
        _record("fx-1", 0.7, 0.2, 0.1),
        _record("fx-2", 0.2, 0.3, 0.5),
    ]
    fixtures = {
        "fx-1": _finished_fixture("fx-1", 2, 0),
        "fx-2": _finished_fixture("fx-2", 1, 1),
    }
    summary, evaluated = evaluate_predictions(records, fixtures)

    assert summary.n_matches == 2
    assert summary.accuracy_1x2 == 0.5
    assert 0.0 <= summary.brier_score <= 2.0
    assert summary.log_loss > 0.0
    assert summary.mae_total_goals >= 0.0
    assert len(evaluated) == 2


def test_evaluation_skips_unfinished_fixtures() -> None:
    records = [_record("fx-3", 0.4, 0.3, 0.3)]
    fixtures = {
        "fx-3": Fixture(
            fixture_id="fx-3",
            home_team_id="h1",
            away_team_id="a1",
            home_team_name="Home",
            away_team_name="Away",
            kickoff_utc=datetime(2026, 6, 20, tzinfo=UTC),
            status="scheduled",
            competition="WC",
            stage="Group",
            venue=None,
            home_goals=None,
            away_goals=None,
        ),
    }
    summary, evaluated = evaluate_predictions(records, fixtures)
    assert summary.n_matches == 0
    assert evaluated == []


@pytest.mark.asyncio
async def test_ledger_sync_skips_finished_fixtures(tmp_path) -> None:
    from fifa26_engine.api.deps import build_app_state
    from fifa26_engine.config import Settings
    from fifa26_engine.data.mock_provider import MockFixtureProvider

    settings = Settings(use_mock_data=True, predictions_db_path=str(tmp_path / "ledger.db"))
    state = build_app_state(settings)
    state.prediction_service = state.prediction_service  # use mock via settings

    fixtures = await state.prediction_service.provider.get_fixtures(limit=100)
    finished_before = state.prediction_store.count_predictions()

    stored = await state.ledger_service.sync_ledger(fixtures)
    assert stored >= 0

    # Re-sync finished-only fixtures must not add ledger rows
    finished_fixtures = [fixture for fixture in fixtures if fixture.status == "finished"]
    count_before = state.prediction_store.count_predictions()
    await state.ledger_service.sync_ledger(finished_fixtures)
    assert state.prediction_store.count_predictions() == count_before
