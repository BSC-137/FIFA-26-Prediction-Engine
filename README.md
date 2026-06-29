# FIFA 26 Prediction Engine

A modular Python engine for predicting FIFA World Cup 2026 match outcomes. The project is structured for production use: configurable data providers, caching, typed schemas, and a FastAPI surface (placeholder) for serving predictions.

## Features

- **Data providers** — abstract `FixtureProvider` with API-Football and offline mock implementations
- **Strength model** — Poisson attack/defense ratings with home advantage and shrinkage
- **Simulator** — vectorized Dixon–Coles score matrix and market aggregation
- **Weather & pitch model** — team affinity modifiers from historical conditions (see below)
- **Structured adjustments** — injuries, rest, knockout context (explainable, no NLP)
- **Configuration** — environment-driven settings via `pydantic-settings`

## Weather & Pitch Model

The engine's distinctive layer learns how national teams perform under specific **temperature**, **precipitation**, and **pitch surface** profiles from historical `MatchResult` data. At prediction time:

1. Stadium coordinates are resolved from the WC 2026 venue map (`data/stadiums.py`)
2. Kickoff weather is fetched via Open-Meteo (or deterministic mock offline)
3. `WeatherAffinityEngine` applies small transparent xG multipliers (±6%)
4. `AdjustmentEngine` layers rest, injury, and knockout factors (±8% total cap)

Set `WEATHER_PROVIDER=openmeteo` in `.env` for live forecasts (no API key required).

## Requirements

- Python 3.11+

## Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/BSC-137/FIFA-26-Prediction-Engine.git
   cd FIFA-26-Prediction-Engine
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS / Linux
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -e .
   # or
   pip install -r requirements.txt
   ```

4. **Configure environment**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set `API_FOOTBALL_KEY` if you have an [API-Football](https://www.api-football.com/) key.

   **Mock data works without an API key.** Leave `API_FOOTBALL_KEY` empty to develop offline using `MockFixtureProvider`.

## Running the API

Start the server with the helper script or uvicorn directly:

```bash
# Windows
.\scripts\run_api.ps1

# macOS / Linux
chmod +x scripts/run_api.sh && ./scripts/run_api.sh

# Or manually
uvicorn fifa26_engine.api.main:app --reload --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API documentation.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check + data source (`mock` or `api-football`) |
| `GET` | `/status` | Refresh timestamps, provider mode, fixture counts by status |
| `GET` | `/fixtures` | List fixtures (`?status=scheduled\|live\|finished`, `?limit=100`) |
| `GET` | `/fixtures/refresh` | Bust fixture + prediction caches, return fresh list |
| `GET` | `/predict/{fixture_id}` | Full prediction for a stored fixture |
| `GET` | `/predict` | Manual matchup (`home_team_id`, `away_team_id`, `kickoff_utc`, …) |

Responses are cached in-memory: **fixtures 5 min**, **predictions 10 min** (configurable via `.env`).

### Automatic refresh

A background asyncio task refreshes fixture caches every **5 minutes** by default (`REFRESH_INTERVAL_SECONDS=300`):

- Warms `scheduled`, `live`, and `finished` lists
- Clears stale prediction caches when live scores may have changed
- Never blocks API request handlers; failures are logged and exposed via `GET /status`

Disable with `REFRESH_ENABLED=false` in `.env`.

### Sample prediction response

```json
{
  "fixture": {
    "fixture_id": "wc26-005",
    "home_team_name": "Brazil",
    "away_team_name": "Serbia",
    "status": "scheduled",
    "venue": "SoFi Stadium",
    "pitch_type": "grass"
  },
  "expected_goals": {
    "base_home": 1.42,
    "base_away": 0.98,
    "adjusted_home": 1.45,
    "adjusted_away": 0.96
  },
  "probabilities": {
    "home_win": 0.48,
    "draw": 0.27,
    "away_win": 0.25,
    "btts_yes": 0.52,
    "btts_no": 0.48,
    "over_under": { "over_2_5": 0.44, "under_2_5": 0.56 },
    "top_scores": [{ "score": "1-0", "probability": 0.12 }]
  },
  "weather": {
    "temperature_c": 28.0,
    "weather_code": "heat"
  },
  "pitch_type": "grass",
  "adjustments_applied": [],
  "weather_explanations": ["home_affinity:hot_dry_grass"],
  "model_version": "0.2.0",
  "generated_at": "2026-06-29T12:00:00Z",
  "as_of_utc": "2026-06-13T19:00:00Z"
}
```

Finished fixtures include actual `home_goals` / `away_goals` in the `fixture` block alongside the model prediction.

### Refresh behavior

`GET /fixtures/refresh` manually triggers the same refresh cycle as the background task:

1. API-level fixture list cache cleared
2. API-level prediction cache cleared
3. Underlying provider cache cleared (when using API-Football)
4. Fresh data loaded for all status buckets

Check `GET /status` for `last_fixture_refresh_utc`, `fixture_counts`, and any `last_refresh_error`.

## Project layout

```
fifa26_engine/
  config.py              # Environment configuration
  data/                  # Fixture data providers
  models/                # Prediction models (placeholders)
  api/                   # FastAPI app and schemas
  services/              # Business orchestration
  utils/                 # Cache, logging
```

## Development notes

- Prediction pipeline: `strength → weather affinity → adjustments → simulator`
- Historical results are filtered with `filter_results_before(kickoff)` to prevent leakage
- Use type hints and docstrings when extending public APIs.

## License

MIT
