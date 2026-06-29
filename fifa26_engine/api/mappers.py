"""Map domain models to API response schemas."""

from __future__ import annotations

from datetime import datetime, timezone

from fifa26_engine.api.schemas import (
    ExpectedGoalsResponse,
    FixtureResponse,
    MarketProbabilitiesResponse,
    MODEL_VERSION,
    PredictionResponse,
    TopScoreResponse,
    WeatherResponse,
)
from fifa26_engine.data.provider import Fixture, PitchType, WeatherConditions
from fifa26_engine.data.stadiums import resolve_stadium
from fifa26_engine.models.simulator import PredictionBreakdown


def fixture_to_response(fixture: Fixture) -> FixtureResponse:
    """Convert a domain ``Fixture`` to an API response."""
    stadium = resolve_stadium(fixture)
    pitch: PitchType = fixture.pitch_type if fixture.pitch_type != "unknown" else stadium.pitch_type
    return FixtureResponse(
        fixture_id=fixture.fixture_id,
        home_team_id=fixture.home_team_id,
        away_team_id=fixture.away_team_id,
        home_team_name=fixture.home_team_name,
        away_team_name=fixture.away_team_name,
        kickoff_utc=fixture.kickoff_utc,
        status=fixture.status,
        competition=fixture.competition,
        stage=fixture.stage,
        venue=fixture.venue,
        venue_city=fixture.venue_city or stadium.city,
        venue_country=fixture.venue_country or stadium.country,
        pitch_type=pitch,
        home_goals=fixture.home_goals,
        away_goals=fixture.away_goals,
    )


def weather_to_response(weather: WeatherConditions | None) -> WeatherResponse | None:
    """Convert domain weather to API response."""
    if weather is None:
        return None
    return WeatherResponse(
        temperature_c=weather.temperature_c,
        humidity_pct=weather.humidity_pct,
        wind_speed_kmh=weather.wind_speed_kmh,
        precipitation_mm=weather.precipitation_mm,
        weather_code=weather.weather_code,
        is_indoor=weather.is_indoor,
        fetched_at_utc=weather.fetched_at_utc,
    )


def markets_to_response(markets: dict) -> MarketProbabilitiesResponse:
    """Convert simulator market dict to API response."""
    return MarketProbabilitiesResponse(
        home_win=markets["home_win"],
        draw=markets["draw"],
        away_win=markets["away_win"],
        btts_yes=markets["btts_yes"],
        btts_no=markets["btts_no"],
        over_under={
            "over_1_5": markets["over_1_5"],
            "under_1_5": markets["under_1_5"],
            "over_2_5": markets["over_2_5"],
            "under_2_5": markets["under_2_5"],
            "over_3_5": markets["over_3_5"],
            "under_3_5": markets["under_3_5"],
        },
        top_scores=[
            TopScoreResponse(score=item["score"], probability=item["probability"])
            for item in markets["top_scores"]
        ],
    )


def breakdown_to_prediction_response(
    fixture: Fixture,
    breakdown: PredictionBreakdown,
    *,
    as_of_utc: datetime,
    pitch_type: PitchType,
) -> PredictionResponse:
    """Build a full ``PredictionResponse`` from a prediction breakdown."""
    return PredictionResponse(
        fixture=fixture_to_response(fixture),
        expected_goals=ExpectedGoalsResponse(
            base_home=breakdown.base_home_xg,
            base_away=breakdown.base_away_xg,
            adjusted_home=breakdown.adjusted_home_xg,
            adjusted_away=breakdown.adjusted_away_xg,
        ),
        probabilities=markets_to_response(breakdown.simulation.markets),
        weather=weather_to_response(breakdown.weather_conditions),
        pitch_type=pitch_type,
        adjustments_applied=breakdown.adjustments_applied,
        weather_explanations=breakdown.weather_labels,
        model_version=MODEL_VERSION,
        generated_at=datetime.now(timezone.utc),
        as_of_utc=as_of_utc,
    )
