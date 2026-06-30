"""Tests for openfootball WC 2026 data provider."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fifa26_engine.config import Settings
from fifa26_engine.data.openfootball_loader import load_openfootball_payload
from fifa26_engine.data.openfootball_provider import OpenFootballProvider
from fifa26_engine.data.team_ids import slugify_team_name
from fifa26_engine.data.team_metrics import compute_all_team_stats, compute_team_stats
from fifa26_engine.data.wc2026_store import WC2026Store

SAMPLE_PATH = Path(__file__).parent / "fixtures" / "openfootball_wc2026_sample.json"


@pytest.fixture
def sample_payload() -> dict:
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


def test_slugify_team_name_aliases() -> None:
    assert slugify_team_name("Korea Republic") == "south-korea"
    assert slugify_team_name("Côte d'Ivoire") == "ivory-coast"
    assert slugify_team_name("United States") == "united-states"


def test_load_openfootball_payload(sample_payload: dict) -> None:
    fixtures, team_results = load_openfootball_payload(sample_payload)
    assert len(fixtures) == 4
    assert sum(fixture.status == "finished" for fixture in fixtures) == 3
    assert "mexico" in team_results
    assert team_results["mexico"][0].competition == "FIFA World Cup 2026"


def test_compute_team_stats(sample_payload: dict) -> None:
    _, team_results = load_openfootball_payload(sample_payload)
    stats = compute_team_stats("mexico", team_results["mexico"], team_name="Mexico")
    assert stats.played == 1
    assert stats.wins == 1
    assert stats.goals_for == 2
    assert stats.form == "W"


@pytest.mark.asyncio
async def test_openfootball_provider_from_sample(tmp_path: Path, sample_payload: dict) -> None:
    data_path = tmp_path / "worldcup.json"
    data_path.write_text(json.dumps(sample_payload), encoding="utf-8")
    settings = Settings(
        data_provider="openfootball",
        wc2026_data_path=str(data_path),
        wc2026_auto_sync=False,
        use_mock_data=False,
    )
    provider = OpenFootballProvider(settings=settings, auto_sync=False)
    fixtures = await provider.get_fixtures()
    assert len(fixtures) == 4

    finished = await provider.get_fixtures(status="finished")
    assert len(finished) == 3

    mexico_results = await provider.get_team_results("mexico")
    assert len(mexico_results) == 1
    assert all(result.competition == "FIFA World Cup 2026" for result in mexico_results)

    fixture = await provider.get_fixture_by_id("wc26-001")
    assert fixture is not None
    assert fixture.venue == "Estadio Azteca"


def test_compute_all_team_stats_from_store(tmp_path: Path, sample_payload: dict) -> None:
    data_path = tmp_path / "worldcup.json"
    data_path.write_text(json.dumps(sample_payload), encoding="utf-8")
    store = WC2026Store(data_path=data_path)
    store.load()
    stats = compute_all_team_stats(store)
    assert len(stats) == 5
    assert stats[0].points >= stats[-1].points
