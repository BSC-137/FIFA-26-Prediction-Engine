"""Map API-Football JSON payloads into domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fifa26_engine.data.provider import Fixture, FixtureStatus, MatchResult, PitchType
from fifa26_engine.data.stadiums import enrich_fixture

# API-Football short status codes (https://www.api-football.com/documentation-v3#tag/Fixtures)
_LIVE_STATUSES = frozenset({"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT"})
_FINISHED_STATUSES = frozenset({"FT", "AET", "PEN", "AWD", "WO"})


def map_api_status(short_status: str) -> FixtureStatus:
    """Map an API-Football short status code to our fixture status."""
    code = short_status.upper()
    if code in _FINISHED_STATUSES:
        return "finished"
    if code in _LIVE_STATUSES:
        return "live"
    return "scheduled"


def _parse_goals(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _is_neutral_venue(league_name: str, league_type: str | None) -> bool:
    """Heuristic: international tournaments and friendlies are typically neutral."""
    name = league_name.lower()
    if "world cup" in name or "euro" in name or "copa america" in name:
        return True
    if league_type and league_type.lower() in {"cup", "friendly"}:
        return True
    return "friendlies" in name


def map_api_fixture(item: dict[str, Any]) -> Fixture:
    """Map one API-Football fixture response item to a ``Fixture``."""
    fixture = item["fixture"]
    league = item["league"]
    teams = item["teams"]
    goals = item.get("goals") or {}
    venue_block = item.get("venue") or fixture.get("venue") or {}

    status = map_api_status(fixture["status"]["short"])
    home_goals = _parse_goals(goals.get("home"))
    away_goals = _parse_goals(goals.get("away"))

    mapped = Fixture(
        fixture_id=str(fixture["id"]),
        home_team_id=str(teams["home"]["id"]),
        away_team_id=str(teams["away"]["id"]),
        home_team_name=teams["home"]["name"],
        away_team_name=teams["away"]["name"],
        kickoff_utc=_parse_datetime(fixture["date"]),
        status=status,
        competition=league.get("name", "Unknown"),
        stage=league.get("round", "Unknown"),
        venue=venue_block.get("name"),
        home_goals=home_goals,
        away_goals=away_goals,
        venue_city=venue_block.get("city"),
        venue_country=venue_block.get("country"),
    )
    return enrich_fixture(mapped)


def map_api_fixture_to_match_result(item: dict[str, Any]) -> MatchResult | None:
    """Map a finished API-Football fixture item to a ``MatchResult``, if applicable."""
    fixture = item["fixture"]
    status = map_api_status(fixture["status"]["short"])
    if status != "finished":
        return None

    league = item["league"]
    teams = item["teams"]
    goals = item.get("goals") or {}
    home_goals = _parse_goals(goals.get("home"))
    away_goals = _parse_goals(goals.get("away"))
    if home_goals is None or away_goals is None:
        return None

    venue_block = item.get("venue") or fixture.get("venue") or {}
    pitch: PitchType = "unknown"

    return MatchResult(
        match_id=str(fixture["id"]),
        date=_parse_datetime(fixture["date"]),
        home_team_id=str(teams["home"]["id"]),
        away_team_id=str(teams["away"]["id"]),
        home_goals=home_goals,
        away_goals=away_goals,
        is_neutral=_is_neutral_venue(
            league.get("name", ""),
            league.get("type"),
        ),
        competition=league.get("name", "Unknown"),
        pitch_type=pitch,
    )
