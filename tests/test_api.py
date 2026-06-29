"""Tests for FastAPI product endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from fifa26_engine.api.deps import build_app_state
from fifa26_engine.api.main import app
from fifa26_engine.config import Settings
from fifa26_engine.data.mock_provider import MockFixtureProvider
from fifa26_engine.services.prediction_service import PredictionService


@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        use_mock_data=True,
        weather_provider="mock",
        refresh_enabled=False,
    )
    provider = MockFixtureProvider()
    service = PredictionService(
        provider=provider,
        settings=settings,
    )
    state = build_app_state(settings)
    state.prediction_service = service
    app.state.app_state = state
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["source"] == "mock"


def test_fixtures_returns_scheduled_and_finished(client: TestClient) -> None:
    response = client.get("/fixtures", params={"limit": 100})
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "refreshed_at" in body
    assert body["source"] == "mock"
    statuses = {item["status"] for item in body["items"]}
    assert "scheduled" in statuses
    assert "finished" in statuses


def test_fixtures_refresh_busts_cache(client: TestClient) -> None:
    first = client.get("/fixtures")
    refreshed = client.get("/fixtures/refresh")
    assert first.status_code == 200
    assert refreshed.status_code == 200
    assert refreshed.json()["refreshed_at"] >= first.json()["refreshed_at"]


def test_predict_fixture_id(client: TestClient) -> None:
    response = client.get("/predict/wc26-005")
    assert response.status_code == 200
    body = response.json()

    probs = body["probabilities"]
    total_1x2 = probs["home_win"] + probs["draw"] + probs["away_win"]
    assert total_1x2 == pytest.approx(1.0, abs=0.02)

    assert "expected_goals" in body
    assert body["expected_goals"]["adjusted_home"] > 0
    assert "weather" in body
    assert isinstance(body["adjustments_applied"], list)
    assert "model_version" in body
    assert "as_of_utc" in body


def test_predict_finished_fixture_includes_actual_score(client: TestClient) -> None:
    response = client.get("/predict/wc26-001")
    assert response.status_code == 200
    fixture = response.json()["fixture"]
    assert fixture["status"] == "finished"
    assert fixture["home_goals"] is not None
    assert fixture["away_goals"] is not None


def test_predict_manual_matchup(client: TestClient) -> None:
    response = client.get(
        "/predict",
        params={
            "home_team_id": "2001",
            "away_team_id": "2003",
            "kickoff_utc": "2026-07-13T19:00:00+00:00",
            "home_team_name": "Brazil",
            "away_team_name": "France",
            "venue": "MetLife Stadium",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fixture"]["home_team_name"] == "Brazil"
    assert body["probabilities"]["home_win"] >= 0.0


def test_predict_unknown_fixture_404(client: TestClient) -> None:
    response = client.get("/predict/does-not-exist")
    assert response.status_code == 404


def test_status_endpoint(client: TestClient) -> None:
    response = client.get("/status")
    assert response.status_code == 200
    body = response.json()
    assert body["provider_mode"] == "mock"
    assert body["refresh_enabled"] is False
    assert "fixture_counts" in body
    assert body["refresh_interval_seconds"] >= 30
