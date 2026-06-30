"""Parse openfootball/worldcup.json into engine domain models."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from fifa26_engine.data.provider import Fixture, FixtureStatus, MatchResult
from fifa26_engine.data.stadiums import ground_to_stadium, enrich_fixture
from fifa26_engine.data.team_ids import slugify_team_name

WC2026 = "FIFA World Cup 2026"
_UTC_OFFSET_RE = re.compile(r"UTC([+-]\d+)")


def _parse_kickoff_utc(date_str: str, time_str: str | None) -> datetime:
    """Best-effort UTC kickoff from openfootball date and time fields."""
    if not time_str:
        return datetime.fromisoformat(f"{date_str}T12:00:00").replace(tzinfo=timezone.utc)

    hour_min = time_str.split()[0]
    hour, minute = (int(part) for part in hour_min.split(":"))
    offset_match = _UTC_OFFSET_RE.search(time_str)
    offset_hours = int(offset_match.group(1)) if offset_match else 0

    local = datetime.fromisoformat(f"{date_str}T{hour:02d}:{minute:02d}")
    return (local - timedelta(hours=offset_hours)).replace(tzinfo=timezone.utc)


def _fixture_status(match: dict[str, Any]) -> FixtureStatus:
    score = match.get("score")
    if not score or score.get("ft") is None:
        return "scheduled"
    return "finished"


def _stage_label(match: dict[str, Any]) -> str:
    round_name = match.get("round") or "Unknown"
    group = match.get("group")
    if group:
        return f"{group} - {round_name}"
    return round_name


def _fixture_id(match: dict[str, Any]) -> str:
    if match.get("num") is not None:
        return f"wc26-{int(match['num']):03d}"
    home = slugify_team_name(match["team1"])
    away = slugify_team_name(match["team2"])
    return f"wc26-{match['date']}-{home}-{away}"


def parse_openfootball_match(match: dict[str, Any]) -> tuple[Fixture, MatchResult | None]:
    """Map one openfootball match record to a Fixture and optional MatchResult."""
    home_name = match["team1"]
    away_name = match["team2"]
    home_id = slugify_team_name(home_name)
    away_id = slugify_team_name(away_name)
    status = _fixture_status(match)
    ground = match.get("ground")
    venue = ground_to_stadium(ground) if ground else None

    home_goals: int | None = None
    away_goals: int | None = None
    if status == "finished":
        ft = match["score"]["ft"]
        home_goals = int(ft[0])
        away_goals = int(ft[1])

    fixture = enrich_fixture(
        Fixture(
            fixture_id=_fixture_id(match),
            home_team_id=home_id,
            away_team_id=away_id,
            home_team_name=home_name,
            away_team_name=away_name,
            kickoff_utc=_parse_kickoff_utc(match["date"], match.get("time")),
            status=status,
            competition=WC2026,
            stage=_stage_label(match),
            venue=venue,
            home_goals=home_goals,
            away_goals=away_goals,
        ),
    )

    result: MatchResult | None = None
    if status == "finished" and home_goals is not None and away_goals is not None:
        result = MatchResult(
            match_id=fixture.fixture_id,
            date=fixture.kickoff_utc,
            home_team_id=home_id,
            away_team_id=away_id,
            home_goals=home_goals,
            away_goals=away_goals,
            is_neutral=True,
            competition=WC2026,
            pitch_type=fixture.pitch_type if fixture.pitch_type != "unknown" else None,
        )

    return fixture, result


def load_openfootball_payload(payload: dict[str, Any]) -> tuple[list[Fixture], dict[str, list[MatchResult]]]:
    """Parse a full openfootball worldcup.json document."""
    matches = payload.get("matches", [])
    fixtures: list[Fixture] = []
    team_results: dict[str, list[MatchResult]] = {}

    for match in matches:
        fixture, result = parse_openfootball_match(match)
        fixtures.append(fixture)
        if result is None:
            continue
        for team_id in (fixture.home_team_id, fixture.away_team_id):
            team_results.setdefault(team_id, []).append(result)

    fixtures.sort(key=lambda item: item.kickoff_utc)
    for results in team_results.values():
        results.sort(key=lambda item: item.date, reverse=True)

    return fixtures, team_results
