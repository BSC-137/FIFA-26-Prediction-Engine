"""Leakage-safe temporal filtering for historical match data."""

from __future__ import annotations

from datetime import datetime, timezone

from fifa26_engine.data.provider import MatchResult


def _ensure_aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def filter_results_before(
    results: list[MatchResult],
    cutoff: datetime,
    *,
    strict: bool = True,
) -> list[MatchResult]:
    """Keep only matches strictly (or weakly) before ``cutoff``.

    Args:
        results: Historical matches to filter.
        cutoff: Reference timestamp (typically fixture kickoff or ``as_of_utc``).
        strict: When True, keep matches with ``date < cutoff`` only.
    """
    cutoff_aware = _ensure_aware(cutoff)
    filtered: list[MatchResult] = []
    for result in results:
        match_date = _ensure_aware(result.date)
        if strict:
            if match_date < cutoff_aware:
                filtered.append(result)
        elif match_date <= cutoff_aware:
            filtered.append(result)
    return filtered


def resolve_as_of_utc(fixture_kickoff: datetime, fixture_status: str, as_of_utc: datetime | None) -> datetime:
    """Resolve the modelling cutoff for a fixture."""
    if as_of_utc is not None:
        return _ensure_aware(as_of_utc)
    if fixture_status == "live":
        return datetime.now(timezone.utc)
    return _ensure_aware(fixture_kickoff)
