"""Weather forecast providers for match context."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

import httpx

from fifa26_engine.config import Settings, get_settings
from fifa26_engine.data.provider import WeatherConditions
from fifa26_engine.utils.cache import TTLCache
from fifa26_engine.utils.logging import get_logger

logger = get_logger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


@runtime_checkable
class WeatherProvider(Protocol):
    """Protocol for fetching kickoff weather forecasts."""

    async def get_forecast(
        self,
        lat: float,
        lon: float,
        kickoff_utc: datetime,
    ) -> WeatherConditions:
        """Return weather conditions expected at kickoff."""
        ...


def _bucket_weather_code(
    temperature_c: float | None,
    precipitation_mm: float | None,
) -> str | None:
    if temperature_c is None and precipitation_mm is None:
        return None
    precip = precipitation_mm or 0.0
    if precip > 1.0:
        return "rain"
    if temperature_c is not None and temperature_c > 24.0:
        return "heat"
    if temperature_c is not None and temperature_c < 12.0:
        return "cold"
    return "clear"


def _nearest_hourly_index(times: list[str], kickoff_utc: datetime) -> int:
    kickoff = kickoff_utc.astimezone(timezone.utc)
    best_index = 0
    best_delta = float("inf")
    for index, time_str in enumerate(times):
        hour = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        if hour.tzinfo is None:
            hour = hour.replace(tzinfo=timezone.utc)
        else:
            hour = hour.astimezone(timezone.utc)
        delta = abs((hour - kickoff).total_seconds())
        if delta < best_delta:
            best_delta = delta
            best_index = index
    return best_index


class MockWeatherProvider:
    """Deterministic offline weather forecasts keyed by location and kickoff."""

    async def get_forecast(
        self,
        lat: float,
        lon: float,
        kickoff_utc: datetime,
    ) -> WeatherConditions:
        seed = hashlib.sha256(f"{lat:.3f}:{lon:.3f}:{kickoff_utc.date()}".encode()).hexdigest()
        bucket = int(seed[:8], 16) % 5
        profiles = [
            (28.0, 65.0, 12.0, 0.0, "heat"),
            (18.0, 55.0, 8.0, 0.0, "clear"),
            (8.0, 70.0, 15.0, 0.2, "cold"),
            (22.0, 80.0, 10.0, 3.5, "rain"),
            (16.0, 60.0, 20.0, 0.0, "clear"),
        ]
        temp, humidity, wind, precip, code = profiles[bucket]
        return WeatherConditions(
            temperature_c=temp,
            humidity_pct=humidity,
            wind_speed_kmh=wind,
            precipitation_mm=precip,
            weather_code=code,
            is_indoor=False,
            fetched_at_utc=datetime.now(timezone.utc),
        )


class OpenMeteoWeatherProvider:
    """Free Open-Meteo hourly forecast provider (no API key required)."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
        cache: TTLCache[str, WeatherConditions] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client
        self._owns_client = client is None
        self._cache = cache or TTLCache(
            default_ttl_seconds=self._settings.weather_cache_ttl_seconds,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=20.0)
        return self._client

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get_forecast(
        self,
        lat: float,
        lon: float,
        kickoff_utc: datetime,
    ) -> WeatherConditions:
        kickoff = kickoff_utc.astimezone(timezone.utc)
        cache_key = f"{lat:.4f}:{lon:.4f}:{kickoff.date().isoformat()}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        client = await self._get_client()
        try:
            response = await client.get(
                OPEN_METEO_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
                    "start_date": kickoff.date().isoformat(),
                    "end_date": kickoff.date().isoformat(),
                    "timezone": "UTC",
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Open-Meteo forecast unavailable for %s: %s", cache_key, exc)
            return WeatherConditions(
                temperature_c=None,
                humidity_pct=None,
                wind_speed_kmh=None,
                precipitation_mm=None,
                weather_code=None,
                fetched_at_utc=datetime.now(timezone.utc),
            )
        payload = response.json()
        hourly = payload.get("hourly", {})
        times = hourly.get("time", [])
        if not times:
            logger.warning("Open-Meteo returned no hourly data for %s", cache_key)
            return WeatherConditions(
                temperature_c=None,
                humidity_pct=None,
                wind_speed_kmh=None,
                precipitation_mm=None,
                weather_code=None,
                fetched_at_utc=datetime.now(timezone.utc),
            )

        index = _nearest_hourly_index(times, kickoff)
        temp = hourly.get("temperature_2m", [None])[index]
        humidity = hourly.get("relative_humidity_2m", [None])[index]
        precip = hourly.get("precipitation", [None])[index]
        wind = hourly.get("wind_speed_10m", [None])[index]

        conditions = WeatherConditions(
            temperature_c=float(temp) if temp is not None else None,
            humidity_pct=float(humidity) if humidity is not None else None,
            wind_speed_kmh=float(wind) if wind is not None else None,
            precipitation_mm=float(precip) if precip is not None else None,
            weather_code=_bucket_weather_code(
                float(temp) if temp is not None else None,
                float(precip) if precip is not None else None,
            ),
            fetched_at_utc=datetime.now(timezone.utc),
        )
        self._cache.set(cache_key, conditions)
        return conditions


def create_weather_provider(settings: Settings | None = None) -> WeatherProvider:
    """Factory for configured weather provider."""
    resolved = settings or get_settings()
    if resolved.weather_provider == "mock":
        return MockWeatherProvider()
    return OpenMeteoWeatherProvider(settings=resolved)
