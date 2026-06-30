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

   Local secrets live in **`project_root/.env`** (same folder as `pyproject.toml`). This file is **gitignored** — never commit it.

   Create it from the template:

   ```bash
   # Windows
   .\scripts\setup_env.ps1

   # macOS / Linux
   chmod +x scripts/setup_env.sh && ./scripts/setup_env.sh
   ```

   Or copy manually:

   ```bash
   cp .env.example .env        # macOS / Linux
   copy .env.example .env      # Windows
   ```

   Edit `.env` and paste your [API-Football](https://www.api-football.com/) key:

   ```env
   API_FOOTBALL_KEY=your_key_here
   USE_MOCK_DATA=false
   ```

   Settings load from `project_root/.env` automatically, even when uvicorn is started from another working directory.

   **Verify configuration** after `.\scripts\run_api.ps1` or `./scripts/run_api.sh`:

   | Endpoint | Expected (live API) |
   |----------|---------------------|
   | `GET /health` | `"source": "api-football"` |
   | `GET /status` | `"provider_mode": "api"` |

   With no key (or `USE_MOCK_DATA=true`), `/health` returns `"source": "mock"`.

   **Mock data works without an API key.** Leave `API_FOOTBALL_KEY` empty to develop offline.

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
| `GET` | `/model/info` | Active model hyperparameters and version |

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

Check `GET /status` for `last_fixture_refresh_utc`, `fixture_counts`, `ledger_prediction_count`, and any `last_refresh_error`.

## Model Evaluation

Walk-forward backtesting retrains the model on every finished fixture in chronological order with strict temporal guards:

1. **`as_of = kickoff_utc`** for the target fixture
2. **Training pool** — all `MatchResult` rows with `date < as_of` (via `filter_results_before`)
3. **Context** — weather and pitch from kickoff-time information only; observed kickoff weather is used when present on a `MatchResult`
4. **No ledger** — research backtests do not read or write `predictions.db`

Run the CLI (mock data works offline):

```bash
python -m fifa26_engine.scripts.backtest_walkforward --mock
```

Outputs land in `reports/backtest_walkforward.json` and `reports/backtest_walkforward.md` with 1X2 accuracy, Brier score, log loss, O/U 2.5 and BTTS hit rates, goal MAE, and stage breakdowns.

**Limitation:** mock weather history may be synthetic; treat offline backtest weather as illustrative rather than observed stadium conditions.

Tune core hyperparameters offline (grid search over `dixon_coles_rho`, `shrinkage_prior_matches`, `team_history_limit`):

```bash
python -m fifa26_engine.scripts.tune_hyperparams --mock
```

Results are written to `reports/tuning_results.json` ranked by walk-forward log loss.

## Hyperparameters

Model settings live in `fifa26_engine/config/model_config.py` and are overridable via `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `TEAM_HISTORY_LIMIT` | `30` | Max recent NT results per team used for fitting |
| `SHRINKAGE_PRIOR_MATCHES` | `8.0` | Pseudo-match count for rating shrinkage |
| `DIXON_COLES_RHO` | `-0.13` | Low-score correlation in the simulator (empty = default) |
| `WEATHER_DELTA_SCALE` | `0.35` | Scale for weather affinity xG modifiers |
| `WEATHER_MIN_BUCKET_SAMPLES` | `5` | Min samples before full weather bucket weight |
| `INTERCEPT_PRIOR_GOALS` | `1.35` | Baseline scoring rate when no training data |
| `TIME_DECAY_HALF_LIFE_DAYS` | `0` | Exponential decay half-life for match weights (`0` = off) |
| `MODEL_VERSION` | `0.2.0` | Version tag in ledger rows and API responses |

Inspect the active configuration at runtime:

```
GET /model/info
```

Adjustment-rule constants (injuries, rest, knockout caps) are **not** tuned by the grid-search script.

## Accuracy & Leakage Policy

The engine maintains a **prediction ledger** (`predictions.db`) of pre-kickoff forecasts:

1. **Before kickoff** — `LedgerService` stores one canonical row per fixture (`as_of_utc <= kickoff_utc`)
2. **Training cutoff** — strength model uses only matches with `result.date < as_of_utc`
3. **After full-time** — accuracy evaluation reads **stored** predictions only; never refits including that match
4. **Finished fixtures** — `sync_ledger` skips generation; `/accuracy/*` compares ledger vs actual scores

### Accuracy endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/accuracy/summary` | 1X2 accuracy, Brier, log loss, goal MAE, calibration bins |
| `GET` | `/accuracy/fixtures` | Per-finished-match prediction vs actual |
| `POST` | `/accuracy/recompute` | Recompute metrics from ledger (optional `X-Admin-Key`) |

Ledger sync runs automatically during background fixture refresh and on `GET /fixtures/refresh`.

## Project layout

```
fifa26_engine/
  config/                # Settings and ModelConfig hyperparameters
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
