"""Build structured match context for adjustment layers."""

from __future__ import annotations

from datetime import datetime, timezone

from fifa26_engine.data.provider import Fixture, FixtureProvider, MatchResult, PitchType
from fifa26_engine.data.stadiums import enrich_fixture, resolve_stadium
from fifa26_engine.data.weather_provider import WeatherProvider, create_weather_provider
from fifa26_engine.models.adjustments import MatchContext
from fifa26_engine.models.temporal import filter_results_before, resolve_as_of_utc


def _is_knockout_stage(stage: str) -> bool:
    lowered = stage.lower()
    keywords = ("round of", "quarter", "semi", "final", "knockout")
    return any(keyword in lowered for keyword in keywords)


def _ensure_aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def compute_days_rest(
    team_id: str,
    cutoff: datetime,
    results: list[MatchResult],
) -> int | None:
    """Days since the team's most recent match strictly before ``cutoff``."""
    cutoff_aware = _ensure_aware(cutoff)
    prior = [
        result
        for result in results
        if (
            _ensure_aware(result.date) < cutoff_aware
            and team_id in (result.home_team_id, result.away_team_id)
        )
    ]
    if not prior:
        return None
    last_match = max(prior, key=lambda item: _ensure_aware(item.date))
    delta = cutoff_aware - _ensure_aware(last_match.date)
    return max(0, int(delta.total_seconds() // 86_400))


async def build_match_context(
    fixture: Fixture,
    provider: FixtureProvider | None = None,
    weather_provider: WeatherProvider | None = None,
    *,
    team_results: list[MatchResult] | None = None,
    as_of_utc: datetime | None = None,
) -> MatchContext:
    """Assemble match context with stadium, weather, and rest days."""
    enriched = enrich_fixture(fixture)
    stadium = resolve_stadium(enriched)
    weather = None
    wp = weather_provider or create_weather_provider()

    if stadium.lat is not None and stadium.lon is not None:
        weather = await wp.get_forecast(
            stadium.lat,
            stadium.lon,
            enriched.kickoff_utc,
        )

    pitch_type: PitchType = stadium.pitch_type
    cutoff = resolve_as_of_utc(enriched.kickoff_utc, enriched.status, as_of_utc)

    results = team_results
    if results is None and provider is not None:
        home_batch = await provider.get_team_results(enriched.home_team_id, limit=30)
        away_batch = await provider.get_team_results(enriched.away_team_id, limit=30)
        combined: dict[str, MatchResult] = {}
        for item in [*home_batch, *away_batch]:
            combined[item.match_id] = item
        results = filter_results_before(list(combined.values()), cutoff, strict=True)

    home_days_rest = None
    away_days_rest = None
    if results:
        home_days_rest = compute_days_rest(enriched.home_team_id, cutoff, results)
        away_days_rest = compute_days_rest(enriched.away_team_id, cutoff, results)

    return MatchContext(
        home_missing_key_players=0,
        away_missing_key_players=0,
        home_days_rest=home_days_rest,
        away_days_rest=away_days_rest,
        is_knockout=_is_knockout_stage(enriched.stage),
        weather=weather,
        pitch_type=pitch_type,
    )
