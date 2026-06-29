"""Tests for temporal leakage-safe filtering."""

from __future__ import annotations

from datetime import datetime, timezone

from fifa26_engine.data.provider import MatchResult
from fifa26_engine.models.temporal import filter_results_before, resolve_as_of_utc

UTC = timezone.utc


def _result(match_id: str, day: int) -> MatchResult:
    return MatchResult(
        match_id=match_id,
        date=datetime(2026, 6, day, tzinfo=UTC),
        home_team_id="A",
        away_team_id="B",
        home_goals=1,
        away_goals=0,
        is_neutral=True,
        competition="Friendly",
    )


def test_filter_results_before_strict_excludes_cutoff_and_future() -> None:
    results = [_result("r1", 10), _result("r2", 11), _result("r3", 12)]
    cutoff = datetime(2026, 6, 11, tzinfo=UTC)
    filtered = filter_results_before(results, cutoff, strict=True)
    assert [match.match_id for match in filtered] == ["r1"]


def test_filter_results_before_non_strict_includes_cutoff_day() -> None:
    results = [_result("r1", 11), _result("r2", 12)]
    cutoff = datetime(2026, 6, 11, 19, 0, tzinfo=UTC)
    filtered = filter_results_before(results, cutoff, strict=False)
    assert [match.match_id for match in filtered] == ["r1"]


def test_resolve_as_of_utc_defaults_to_kickoff() -> None:
    kickoff = datetime(2026, 6, 13, 19, 0, tzinfo=UTC)
    assert resolve_as_of_utc(kickoff, "scheduled", None) == kickoff
