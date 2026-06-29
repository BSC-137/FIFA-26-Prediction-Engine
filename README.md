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

The FastAPI application entry point is a placeholder. Once implemented, start the server with:

```bash
uvicorn fifa26_engine.api.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs` for interactive API documentation.

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
