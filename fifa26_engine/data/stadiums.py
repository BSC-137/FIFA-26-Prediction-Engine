"""World Cup 2026 stadium metadata and venue resolution."""

from __future__ import annotations

from dataclasses import dataclass

from fifa26_engine.data.provider import Fixture, PitchType

# Approximate coordinates and default pitch surfaces for WC 2026 host venues.
WC2026_STADIUMS: dict[str, dict[str, str | float]] = {
    "estadio azteca": {
        "city": "Mexico City",
        "country": "Mexico",
        "lat": 19.3029,
        "lon": -99.1506,
        "pitch_type": "grass",
    },
    "estadio akron": {
        "city": "Guadalajara",
        "country": "Mexico",
        "lat": 20.6816,
        "lon": -103.4617,
        "pitch_type": "grass",
    },
    "bmo field": {
        "city": "Toronto",
        "country": "Canada",
        "lat": 43.6332,
        "lon": -79.4186,
        "pitch_type": "grass",
    },
    "metlife stadium": {
        "city": "East Rutherford",
        "country": "USA",
        "lat": 40.8128,
        "lon": -74.0742,
        "pitch_type": "hybrid",
    },
    "sofi stadium": {
        "city": "Inglewood",
        "country": "USA",
        "lat": 33.9534,
        "lon": -118.3390,
        "pitch_type": "grass",
    },
    "at&t stadium": {
        "city": "Arlington",
        "country": "USA",
        "lat": 32.7473,
        "lon": -97.0945,
        "pitch_type": "artificial",
    },
    "levi's stadium": {
        "city": "Santa Clara",
        "country": "USA",
        "lat": 37.4030,
        "lon": -121.9697,
        "pitch_type": "grass",
    },
    "lumen field": {
        "city": "Seattle",
        "country": "USA",
        "lat": 47.5952,
        "lon": -122.3316,
        "pitch_type": "artificial",
    },
    "mercedes-benz stadium": {
        "city": "Atlanta",
        "country": "USA",
        "lat": 33.7553,
        "lon": -84.4006,
        "pitch_type": "artificial",
    },
    "hard rock stadium": {
        "city": "Miami Gardens",
        "country": "USA",
        "lat": 25.9580,
        "lon": -80.2389,
        "pitch_type": "grass",
    },
    "nrg stadium": {
        "city": "Houston",
        "country": "USA",
        "lat": 29.6847,
        "lon": -95.4107,
        "pitch_type": "artificial",
    },
    "lincoln financial field": {
        "city": "Philadelphia",
        "country": "USA",
        "lat": 39.9008,
        "lon": -75.1675,
        "pitch_type": "grass",
    },
    "gillette stadium": {
        "city": "Foxborough",
        "country": "USA",
        "lat": 42.0909,
        "lon": -71.2643,
        "pitch_type": "grass",
    },
    "bc place": {
        "city": "Vancouver",
        "country": "Canada",
        "lat": 49.2768,
        "lon": -123.1120,
        "pitch_type": "artificial",
    },
    "estadio bbva": {
        "city": "Guadalupe",
        "country": "Mexico",
        "lat": 25.6866,
        "lon": -100.2455,
        "pitch_type": "grass",
    },
    "estadio banorte": {
        "city": "Monterrey",
        "country": "Mexico",
        "lat": 25.6866,
        "lon": -100.2455,
        "pitch_type": "grass",
    },
    "arrowhead stadium": {
        "city": "Kansas City",
        "country": "USA",
        "lat": 39.0489,
        "lon": -94.4839,
        "pitch_type": "grass",
    },
}

# openfootball uses host-city labels in the ``ground`` field.
WC2026_GROUNDS: dict[str, str] = {
    "mexico city": "Estadio Azteca",
    "guadalajara (zapopan)": "Estadio Akron",
    "monterrey (guadalupe)": "Estadio BBVA",
    "toronto": "BMO Field",
    "vancouver": "BC Place",
    "los angeles (inglewood)": "SoFi Stadium",
    "san francisco bay area (santa clara)": "Levi's Stadium",
    "seattle": "Lumen Field",
    "boston (foxborough)": "Gillette Stadium",
    "new york/new jersey (east rutherford)": "MetLife Stadium",
    "philadelphia": "Lincoln Financial Field",
    "miami (miami gardens)": "Hard Rock Stadium",
    "atlanta": "Mercedes-Benz Stadium",
    "houston": "NRG Stadium",
    "dallas (arlington)": "AT&T Stadium",
    "kansas city": "Arrowhead Stadium",
}


def ground_to_stadium(ground: str | None) -> str | None:
    """Map an openfootball ground label to a stadium name (exact or fuzzy)."""
    if not ground:
        return None
    normalized = ground.strip().lower()
    exact = WC2026_GROUNDS.get(normalized)
    if exact:
        return exact

    fuzzy_tokens = (
        ("monterrey", "Estadio Banorte"),
        ("guadalupe", "Estadio BBVA"),
        ("banorte", "Estadio Banorte"),
        ("bbva", "Estadio BBVA"),
        ("inglewood", "SoFi Stadium"),
        ("east rutherford", "MetLife Stadium"),
        ("foxborough", "Gillette Stadium"),
        ("santa clara", "Levi's Stadium"),
        ("arlington", "AT&T Stadium"),
        ("miami gardens", "Hard Rock Stadium"),
    )
    for token, stadium in fuzzy_tokens:
        if token in normalized:
            return stadium

    for key, stadium in WC2026_GROUNDS.items():
        if key in normalized or normalized in key:
            return stadium
    return None


@dataclass(frozen=True)
class StadiumInfo:
    """Resolved stadium metadata for a fixture."""

    name: str | None
    city: str | None
    country: str | None
    lat: float | None
    lon: float | None
    pitch_type: PitchType


def _lookup_venue(venue_name: str | None) -> dict[str, str | float] | None:
    if not venue_name:
        return None
    return WC2026_STADIUMS.get(venue_name.strip().lower())


def resolve_stadium(fixture: Fixture) -> StadiumInfo:
    """Resolve stadium coordinates and pitch type from fixture fields or static map."""
    record = _lookup_venue(fixture.venue)
    pitch: PitchType = fixture.pitch_type
    if pitch == "unknown" and record:
        pitch = record["pitch_type"]  # type: ignore[assignment]

    return StadiumInfo(
        name=fixture.venue,
        city=fixture.venue_city or (str(record["city"]) if record else None),
        country=fixture.venue_country or (str(record["country"]) if record else None),
        lat=fixture.stadium_lat if fixture.stadium_lat is not None else (
            float(record["lat"]) if record else None
        ),
        lon=fixture.stadium_lon if fixture.stadium_lon is not None else (
            float(record["lon"]) if record else None
        ),
        pitch_type=pitch,
    )


def enrich_fixture(fixture: Fixture) -> Fixture:
    """Return a copy of ``fixture`` with stadium metadata filled when missing."""
    if fixture.stadium_lat is not None and fixture.pitch_type != "unknown":
        return fixture
    stadium = resolve_stadium(fixture)
    if stadium.lat is None:
        return fixture
    return Fixture(
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
        home_goals=fixture.home_goals,
        away_goals=fixture.away_goals,
        venue_city=stadium.city,
        venue_country=stadium.country,
        stadium_lat=stadium.lat,
        stadium_lon=stadium.lon,
        pitch_type=stadium.pitch_type,
    )
