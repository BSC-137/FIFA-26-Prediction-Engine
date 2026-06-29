"""Build structured match context for adjustment layers."""

from __future__ import annotations

from fifa26_engine.data.provider import Fixture, FixtureProvider, PitchType
from fifa26_engine.data.stadiums import enrich_fixture, resolve_stadium
from fifa26_engine.data.weather_provider import WeatherProvider, create_weather_provider
from fifa26_engine.models.adjustments import MatchContext


def _is_knockout_stage(stage: str) -> bool:
    lowered = stage.lower()
    keywords = ("round of", "quarter", "semi", "final", "knockout")
    return any(keyword in lowered for keyword in keywords)


async def build_match_context(
    fixture: Fixture,
    provider: FixtureProvider | None = None,
    weather_provider: WeatherProvider | None = None,
) -> MatchContext:
    """Assemble match context with stadium, weather, and mock defaults."""
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
    return MatchContext(
        home_missing_key_players=0,
        away_missing_key_players=0,
        home_days_rest=None,
        away_days_rest=None,
        is_knockout=_is_knockout_stage(enriched.stage),
        weather=weather,
        pitch_type=pitch_type,
    )
