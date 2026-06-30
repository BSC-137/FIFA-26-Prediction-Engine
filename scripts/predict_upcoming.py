"""Run predictions on real upcoming World Cup fixtures (date-based API)."""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fifa26_engine.config import ModelConfig, get_settings
from fifa26_engine.config.paths import PROJECT_ROOT
from fifa26_engine.data.api_football import ApiFootballProvider
from fifa26_engine.data.mappers import map_api_fixture
from fifa26_engine.data.weather_provider import create_weather_provider
from fifa26_engine.services.prediction_service import predict_fixture_markets

UTC = timezone.utc
ALLOWED_DATES = ("2026-06-29", "2026-06-30", "2026-07-01")
REPORT_PATH = PROJECT_ROOT / "reports" / "upcoming_predictions.json"


def _is_world_cup_national(item: dict) -> bool:
    league = item.get("league", {})
    name = (league.get("name") or "").lower()
    return "world cup" in name


def _status_short(item: dict) -> str:
    return item.get("fixture", {}).get("status", {}).get("short", "")


async def fetch_upcoming_world_cup(provider: ApiFootballProvider, limit: int = 6) -> list:
    """Return upcoming World Cup fixtures using the provider's cached date window."""
    await provider._load_wc_date_items()
    seen: set[int] = set()
    upcoming: list = []
    for item in provider._wc_date_items or []:
        if "world cup" not in (item.get("league", {}).get("name") or "").lower():
            continue
        if _status_short(item) not in ("NS", "TBD"):
            continue
        fx_id = item["fixture"]["id"]
        if fx_id in seen:
            continue
        seen.add(fx_id)
        upcoming.append(item)
    upcoming.sort(key=lambda i: i["fixture"]["date"])
    return upcoming[:limit]


async def prewarm_team_histories(provider: ApiFootballProvider, team_ids: set[str]) -> None:
    """Fetch team histories sequentially to stay within free-tier rate limits."""
    for index, team_id in enumerate(sorted(team_ids)):
        try:
            await provider.get_team_results(team_id, limit=30)
        except Exception as exc:
            print(f"  WARN: team {team_id} history partial/failed: {exc}")
        if index + 1 < len(team_ids):
            await asyncio.sleep(4.0)


async def main() -> int:
    settings = get_settings()
    if not settings.has_api_key:
        print("ERROR: API_FOOTBALL_KEY not set in project_root/.env", file=sys.stderr)
        return 1

    model_config = ModelConfig.from_settings(settings)
    provider = ApiFootballProvider(settings=settings)
    weather = create_weather_provider(settings)

    try:
        raw_items = await fetch_upcoming_world_cup(provider, limit=6)
        if not raw_items:
            print("No upcoming World Cup fixtures found in free-tier date window.")
            print(f"Tried dates: {', '.join(ALLOWED_DATES)}")
            return 1

        fixtures = [map_api_fixture(item) for item in raw_items]
        team_ids = {fixture.home_team_id for fixture in fixtures} | {
            fixture.away_team_id for fixture in fixtures
        }
        print(f"Pre-warming history for {len(team_ids)} teams...")
        try:
            await prewarm_team_histories(provider, team_ids)
        except Exception as exc:
            print(f"WARN: team pre-warm incomplete ({exc}); continuing with cached data.")

        print(f"Found {len(raw_items)} upcoming World Cup match(es)\n")
        results = []

        for fixture in fixtures:
            home = fixture.home_team_name
            away = fixture.away_team_name
            kickoff = fixture.kickoff_utc.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")

            await asyncio.sleep(1.0)
            try:
                breakdown = await predict_fixture_markets(
                    fixture,
                    provider,
                    model_config=model_config,
                    weather_provider=weather,
                )
                markets = breakdown.simulation.markets
                prob_sum = markets["home_win"] + markets["draw"] + markets["away_win"]
                row = {
                    "fixture_id": fixture.fixture_id,
                    "match": f"{home} vs {away}",
                    "kickoff_utc": fixture.kickoff_utc.isoformat(),
                    "venue": fixture.venue,
                    "stage": fixture.stage,
                    "probabilities": {
                        "home_win": round(markets["home_win"], 4),
                        "draw": round(markets["draw"], 4),
                        "away_win": round(markets["away_win"], 4),
                        "btts_yes": round(markets["btts_yes"], 4),
                        "over_2_5": round(markets["over_2_5"], 4),
                    },
                    "expected_goals": {
                        "base_home": round(breakdown.base_home_xg, 3),
                        "base_away": round(breakdown.base_away_xg, 3),
                        "adjusted_home": round(breakdown.adjusted_home_xg, 3),
                        "adjusted_away": round(breakdown.adjusted_away_xg, 3),
                    },
                    "weather": {
                        "temperature_c": (
                            breakdown.weather_conditions.temperature_c
                            if breakdown.weather_conditions
                            else None
                        ),
                        "precipitation_mm": (
                            breakdown.weather_conditions.precipitation_mm
                            if breakdown.weather_conditions
                            else None
                        ),
                        "weather_code": (
                            breakdown.weather_conditions.weather_code
                            if breakdown.weather_conditions
                            else None
                        ),
                    },
                    "adjustments": breakdown.adjustments_applied,
                    "weather_labels": breakdown.weather_labels,
                    "prob_sum": round(prob_sum, 4),
                    "status": "ok",
                }
                print(f"--- {home} vs {away} ({kickoff}) ---")
                print(f"  1X2: H {markets['home_win']:.1%} | D {markets['draw']:.1%} | A {markets['away_win']:.1%}")
                print(
                    f"  xG:  {breakdown.adjusted_home_xg:.2f} - {breakdown.adjusted_away_xg:.2f} "
                    f"(base {breakdown.base_home_xg:.2f}-{breakdown.base_away_xg:.2f})"
                )
                print(f"  BTTS yes: {markets['btts_yes']:.1%} | Over 2.5: {markets['over_2_5']:.1%}")
                if breakdown.weather_labels:
                    print(f"  Weather affinity: {', '.join(breakdown.weather_labels)}")
                if breakdown.adjustments_applied:
                    print(f"  Adjustments: {', '.join(breakdown.adjustments_applied)}")
                print()
            except Exception as exc:
                row = {
                    "fixture_id": fixture.fixture_id,
                    "match": f"{home} vs {away}",
                    "status": "error",
                    "error": str(exc),
                }
                print(f"FAIL {home} vs {away}: {exc}\n")
            results.append(row)

        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "model_version": model_config.model_version,
            "api_dates_queried": list(ALLOWED_DATES),
            "n_fixtures": len(results),
            "predictions": results,
        }
        REPORT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Report written to {REPORT_PATH}")

        errors = sum(1 for r in results if r.get("status") == "error")
        return 1 if errors else 0
    finally:
        await provider.close()
        if hasattr(weather, "close"):
            await weather.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
