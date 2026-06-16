"""Tests for fixture data providers and API-Football mapping."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from fifa26_engine.config import ConfigError, Settings
from fifa26_engine.data.api_football import ApiFootballProvider
from fifa26_engine.data.mappers import map_api_fixture, map_api_fixture_to_match_result
from fifa26_engine.data.mock_provider import MockFixtureProvider

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_FIXTURE_JSON = FIXTURES_DIR / "api_football_fixture_sample.json"


@pytest.fixture
def sample_api_item() -> dict:
    payload = json.loads(SAMPLE_FIXTURE_JSON.read_text(encoding="utf-8"))
    return payload["response"][0]


@pytest.fixture
def mock_provider() -> MockFixtureProvider:
    return MockFixtureProvider()


@pytest.mark.asyncio
async def test_mock_provider_returns_fixtures(mock_provider: MockFixtureProvider) -> None:
    fixtures = await mock_provider.get_fixtures()
    assert len(fixtures) >= 12
    assert all(fixture.competition == "FIFA World Cup 2026" for fixture in fixtures)


@pytest.mark.asyncio
async def test_mock_provider_filters_by_status(mock_provider: MockFixtureProvider) -> None:
    finished = await mock_provider.get_fixtures(status="finished")
    scheduled = await mock_provider.get_fixtures(status="scheduled")
    live = await mock_provider.get_fixtures(status="live")

    assert all(fixture.status == "finished" for fixture in finished)
    assert all(fixture.status == "scheduled" for fixture in scheduled)
    assert all(fixture.status == "live" for fixture in live)
    assert len(finished) + len(scheduled) + len(live) == len(await mock_provider.get_fixtures())


@pytest.mark.asyncio
async def test_mock_provider_get_fixture_by_id(mock_provider: MockFixtureProvider) -> None:
    fixture = await mock_provider.get_fixture_by_id("wc26-005")
    assert fixture is not None
    assert fixture.home_team_name == "Brazil"
    assert fixture.away_team_name == "Serbia"
    assert fixture.stage.startswith("Group B")


@pytest.mark.asyncio
async def test_mock_provider_team_results_for_eight_teams(
    mock_provider: MockFixtureProvider,
) -> None:
    team_ids = ["1001", "1002", "1003", "1004", "2001", "2003", "3001", "3003"]
    for team_id in team_ids:
        results = await mock_provider.get_team_results(team_id)
        assert len(results) >= 2
        assert all(result.home_goals >= 0 and result.away_goals >= 0 for result in results)


@pytest.mark.asyncio
async def test_mock_provider_team_results_respects_limit(
    mock_provider: MockFixtureProvider,
) -> None:
    results = await mock_provider.get_team_results("2001", limit=2)
    assert len(results) == 2
    dates = [result.date for result in results]
    assert dates == sorted(dates, reverse=True)


def test_map_api_fixture_sample(sample_api_item: dict) -> None:
    fixture = map_api_fixture(sample_api_item)
    assert fixture.fixture_id == "1035037"
    assert fixture.home_team_name == "Qatar"
    assert fixture.away_team_name == "Ecuador"
    assert fixture.status == "finished"
    assert fixture.competition == "World Cup"
    assert fixture.stage == "Group A - 1"
    assert fixture.venue == "Lusail Stadium"
    assert fixture.home_goals == 0
    assert fixture.away_goals == 2


def test_map_api_fixture_to_match_result_sample(sample_api_item: dict) -> None:
    result = map_api_fixture_to_match_result(sample_api_item)
    assert result is not None
    assert result.match_id == "1035037"
    assert result.home_team_id == "1569"
    assert result.away_team_id == "2382"
    assert result.home_goals == 0
    assert result.away_goals == 2
    assert result.is_neutral is True
    assert result.competition == "World Cup"


def test_map_api_fixture_scheduled_status() -> None:
    item = {
        "fixture": {
            "id": 1,
            "date": "2026-06-11T19:00:00+00:00",
            "status": {"short": "NS", "long": "Not Started"},
        },
        "league": {"name": "World Cup", "round": "Group A - 1", "type": "Cup"},
        "teams": {
            "home": {"id": 10, "name": "Mexico"},
            "away": {"id": 11, "name": "Canada"},
        },
        "goals": {"home": None, "away": None},
        "venue": {"name": "Estadio Azteca"},
    }
    fixture = map_api_fixture(item)
    assert fixture.status == "scheduled"
    assert fixture.home_goals is None
    assert map_api_fixture_to_match_result(item) is None


def test_api_football_provider_requires_api_key() -> None:
    settings = Settings(api_football_key="", use_mock_data=False)
    with pytest.raises(ConfigError, match="API_FOOTBALL_KEY"):
        ApiFootballProvider(settings=settings)


@pytest.mark.asyncio
async def test_api_football_provider_get_fixture_by_id_uses_mapping(
    sample_api_item: dict,
) -> None:
    payload = {"response": [sample_api_item], "errors": []}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/fixtures")
        return httpx.Response(200, json=payload)

    settings = Settings(api_football_key="test-key", use_mock_data=False)
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url=settings.api_football_base_url,
    ) as client:
        provider = ApiFootballProvider(settings=settings, client=client)
        fixture = await provider.get_fixture_by_id("1035037")

    assert fixture is not None
    assert fixture.home_team_name == "Qatar"
    assert fixture.status == "finished"


@pytest.mark.asyncio
async def test_api_football_provider_get_team_results_filters_finished(
    sample_api_item: dict,
) -> None:
    scheduled_item = {
        **sample_api_item,
        "fixture": {
            **sample_api_item["fixture"],
            "id": 999,
            "status": {"short": "NS", "long": "Not Started"},
        },
        "goals": {"home": None, "away": None},
    }
    payload = {"response": [sample_api_item, scheduled_item], "errors": []}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    settings = Settings(api_football_key="test-key", use_mock_data=False)
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url=settings.api_football_base_url,
    ) as client:
        provider = ApiFootballProvider(settings=settings, client=client)
        results = await provider.get_team_results("1569", limit=10)

    assert len(results) == 1
    assert results[0].match_id == "1035037"
