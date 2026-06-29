"""Tests for SQLite prediction ledger store."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from fifa26_engine.storage.prediction_store import PredictionRecord, PredictionStore

UTC = timezone.utc


def _record(fixture_id: str, as_of_day: int, kickoff_day: int) -> PredictionRecord:
    return PredictionRecord(
        fixture_id=fixture_id,
        generated_at_utc=datetime(2026, 6, 1, tzinfo=UTC),
        as_of_utc=datetime(2026, 6, as_of_day, 12, tzinfo=UTC),
        kickoff_utc=datetime(2026, 6, kickoff_day, 19, tzinfo=UTC),
        home_team_id="h1",
        away_team_id="a1",
        base_home_xg=1.4,
        base_away_xg=1.0,
        adj_home_xg=1.5,
        adj_away_xg=0.9,
        p_home=0.45,
        p_draw=0.28,
        p_away=0.27,
        top_score_json='[{"score":"1-0","probability":0.12}]',
        weather_json=None,
        adjustments_json='{"adjustments_applied":[]}',
        model_version="test-v1",
    )


@pytest.fixture
def store(tmp_path: Path) -> PredictionStore:
    return PredictionStore(tmp_path / "test_predictions.db")


def test_save_and_get_prediction(store: PredictionStore) -> None:
    saved = store.save_prediction(_record("fx-1", 10, 11))
    loaded = store.get_prediction_for_fixture("fx-1", "test-v1")
    assert loaded is not None
    assert loaded.fixture_id == "fx-1"
    assert loaded.id == saved.id
    assert loaded.p_home == pytest.approx(0.45)


def test_save_is_idempotent_per_fixture(store: PredictionStore) -> None:
    first = store.save_prediction(_record("fx-2", 10, 11))
    second = store.save_prediction(_record("fx-2", 10, 12))
    assert second.id == first.id
    assert store.count_predictions("test-v1") == 1


def test_rejects_as_of_after_kickoff(store: PredictionStore) -> None:
    with pytest.raises(ValueError, match="as_of_utc"):
        store.save_prediction(_record("fx-bad", 15, 11))


def test_list_predictions_ordered_by_kickoff(store: PredictionStore) -> None:
    store.save_prediction(_record("fx-a", 8, 10))
    store.save_prediction(_record("fx-b", 9, 12))
    rows = store.list_predictions(limit=10, model_version="test-v1")
    assert [row.fixture_id for row in rows] == ["fx-b", "fx-a"]
