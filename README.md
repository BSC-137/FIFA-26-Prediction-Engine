# FIFA 26 Prediction Engine

A modular Python engine for predicting FIFA World Cup 2026 match outcomes. The project is structured for production use: configurable data providers, caching, typed schemas, and a FastAPI surface (placeholder) for serving predictions.

## Features (scaffold)

- **Data providers** — abstract `FixtureProvider` with API-Football and offline mock implementations
- **Configuration** — environment-driven settings via `pydantic-settings`
- **Caching** — in-memory TTL cache for provider responses
- **Prediction pipeline** — service layer ready for model integration (strength, simulator, adjustments)

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

- Business logic (strength models, simulation, adjustments) is not implemented yet — only scaffolding, config, logging, cache, and provider interfaces.
- Use type hints and docstrings when extending public APIs.

## License

MIT
