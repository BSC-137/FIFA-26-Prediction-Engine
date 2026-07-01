# FIFA 26 Prediction Engine

A modular Python engine for predicting FIFA World Cup 2026 match outcomes — with a weather-aware Poisson model, leakage-safe backtesting, a prediction ledger, and a **Prediction Pitch** web UI that turns forecasts into an easy-to-read football field.

This is a passion-project stack built for transparency: every probability can be traced back through xG layers, adjustments, and simulation — not a black-box ML model.

---

## What makes this different

Most football predictors stop at “team A vs team B” strength ratings. This engine adds layers that matter specifically for a **summer World Cup across North America**:

| Layer | What it does | Why it matters |
|-------|----------------|----------------|
| **Tournament-only training** | Team history comes from WC 2026 matches in the openfootball feed (not stale club form) | Ratings reflect how teams are playing *in this tournament* |
| **Weather & pitch affinity** | Small xG modifiers from historical performance in heat, rain, grass vs artificial | Dallas heat ≠ Seattle cool; surface type affects tempo |
| **Stadium-aware forecasts** | Venue coordinates → Open-Meteo kickoff weather | Conditions are part of the prediction, not an afterthought |
| **Calibration for low xG** | Elo blend, host-nation boost, tournament scoring floor, knockout floor | Prevents “everything is a 70% draw” when ratings are sparse early on |
| **Dixon–Coles simulation** | Full scoreline matrix → 1X2, BTTS, O/U, top scores | One coherent model drives all markets |
| **Knockout markets** | Regulation 1X2 + **to advance** (ET + pens) | Knockout semantics live in `knockout.py`, not hidden xG deflation |
| **Leakage-safe evaluation** | Walk-forward backtests + SQLite ledger with `as_of_utc ≤ kickoff` | You can trust accuracy numbers — future results never train the past |

There is **no bookmaker odds calibration** yet (would need an external odds feed). Injury counts are stubbed at zero until squad data is wired in.

---

## Model architecture

Predictions flow through a fixed pipeline. Each step is inspectable in the API response and the Pitch UI.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Fixture data   │────▶│  TeamStrength    │────▶│  Calibration        │
│  (openfootball) │     │  Poisson atk/def │     │  Elo, host, floors  │
└─────────────────┘     └──────────────────┘     └──────────┬──────────┘
                                                            │
┌─────────────────┐     ┌──────────────────┐               ▼
│  Open-Meteo     │────▶│  WeatherAffinity │────▶┌─────────────────────┐
│  kickoff wx     │     │  ±6% xG buckets  │     │  AdjustmentEngine   │
└─────────────────┘     └──────────────────┘     │  rest, wx, caps     │
                                                  └──────────┬──────────┘
                                                             │
                         ┌──────────────────┐               ▼
                         │  KnockoutMarkets │◀──┌─────────────────────┐
                         │  advance_home/away│   │  Dixon–Coles sim    │
                         └──────────────────┘   │  1X2 BTTS O/U scores│
                                                └─────────────────────┘
```

### 1. Team strength (`strength.py`)

Fits **attack** and **defense** ratings from historical `MatchResult` rows using Poisson negative log-likelihood (L-BFGS-B).

- World Cup fixtures are treated as **neutral** (no home advantage in the log-rate).
- **Shrinkage** pulls sparse teams toward the tournament average; teams with &lt;2 WC matches get stronger shrinkage.
- **Time decay** (21-day half-life by default) weights recent group-stage form more heavily going into knockouts.

Output: raw **strength xG** for home and away.

### 2. Calibration (`calibration.py`)

Post-strength adjustments for WC 2026 realities:

| Step | Effect |
|------|--------|
| **Elo blend** (25%) | Blends Poisson xG with Elo-implied xG from chronological results |
| **Host nation boost** (+0.12 log-rate) | Mexico, USA, Canada when playing at home |
| **Tournament scoring prior** (20%) | Nudges total xG toward observed WC 2026 scoring rate |
| **Scoring floor** | Group: min **2.0** total xG; Knockout: min **2.4** total xG |

Output: **base xG** (after calibration, before weather/context).

### 3. Weather affinity (`weather_affinity.py`)

Buckets historical matches by temperature, precipitation, and pitch type. Applies transparent multipliers (capped at ±6% per team) when kickoff weather matches a team’s profile.

### 4. Context adjustments (`adjustments.py`, `context_builder.py`)

- **Days rest** — computed from each team’s last tournament match before kickoff; short rest (&lt;4 days) slightly reduces xG, long rest (&gt;6 days) gives a small boost.
- **Weather modifiers** — from step 3.
- **Total adjustment cap** — combined context changes cannot move total xG more than ±8% from the calibrated base.

Injuries are reserved for future squad data (currently 0).

### 5. Simulation (`simulator.py`)

Builds a scoreline probability matrix with **Dixon–Coles** low-score correlation:

- **Group / general:** ρ = **-0.13** (default)
- **Knockout:** ρ = **-0.08** (less draw mass when stakes are higher)

From the matrix we derive:

- 1X2 (home / draw / away)
- BTTS yes/no
- Over/under 1.5, 2.5, 3.5
- Top exact scorelines

### 6. Knockout markets (`knockout.py`)

For Round of 32 and beyond:

- **Regulation 1X2** — same as the main simulation.
- **To advance** — models extra time (30 min at boosted xG) plus a logistic penalty shootout edge from relative strength.

---

## Prediction Pitch UI

The web UI (`frontend/`) connects to the FastAPI backend and visualises one match at a time.

### Running the UI

**Option A — API + dev UI (hot reload):**

```powershell
# Terminal 1 — start API first; wait for "Uvicorn running"
.\scripts\run_api.ps1

# Terminal 2
.\scripts\run_ui.ps1
```

Open **http://localhost:5173**

**Option B — single server (production build):**

```powershell
cd frontend
npm install
npm run build
cd ..
.\scripts\run_api.ps1
```

Open **http://localhost:8000**

### Reading the screen

```
┌──────────────────────────────────────────────────────────────────────────┐
│  FIFA 26 Prediction Pitch          [Sync data]  [API docs]               │
├──────────────┬───────────────────────────────────────┬───────────────────┤
│  MATCHES     │           FOOTBALL PITCH              │  MARKETS          │
│  (filters)   │                                       │  (detail panel)   │
│              │   [Home team]    Draw    [Away team]  │                   │
│  scheduled   │      xG bubble   %       xG bubble    │  1X2 bars         │
│  live        │                                       │  xG pipeline      │
│  finished    │   arcs = win strength                │  O/U, BTTS        │
│              │   total xG bar at bottom              │  top scorelines   │
├──────────────┴───────────────────────────────────────┴───────────────────┤
│  LEDGER ACCURACY — 1X2 / O/U 2.5 / BTTS / goal MAE (from stored preds)   │
└──────────────────────────────────────────────────────────────────────────┘
```

#### Left panel — Matches

- **Filters:** `all`, `scheduled`, `live`, `finished`
- **Status chips:** colour-coded match state
- Click a match to load its prediction on the pitch

#### Centre — The pitch

| Visual | Meaning |
|--------|---------|
| **Team name + circle** | Home (left, blue) and away (right, orange) |
| **Large number in circle** | **Adjusted expected goals (xG)** for that team |
| **% under the circle** | **Win probability** (home or away) |
| **Centre circle “Draw”** | Draw probability |
| **Coloured arcs on each half** | Thicker arc = higher win chance on that side |
| **Bottom bar “Total xG”** | Sum of adjusted home + away xG |
| **Model pick (top right)** | Highest of home / draw / away with its probability |
| **Stage pill + venue** | Competition round and stadium |

The pitch is a summary view. Exact probabilities and secondary markets are in the right panel.

#### Right panel — Markets

| Section | What you see |
|---------|----------------|
| **1X2 Outcome** | Bar chart for home / draw / away |
| **Expected goals pipeline** | Strength → Base → **Adjusted** xG (the number used in simulation) |
| **Goal markets** | Over/under 2.5 and BTTS yes/no |
| **Knockout — to advance** | Probability each team wins the tie (incl. ET/pens) |
| **Most likely scorelines** | e.g. `1-0` at 12% |
| **Kickoff conditions** | Temperature, humidity, wind, weather code |
| **Model diagnostics** | Attack/defense ratings, WC matches played, training pool size |
| **Warnings** | e.g. `low_total_xg`, `high_draw_probability`, `sparse_wc_history` |
| **Adjustments** | Tags like `elo_blend:0.25`, `host_nation_boost:0.12` |

#### Bottom — Ledger accuracy

After upcoming fixtures are synced, the engine stores **pre-kickoff** predictions in `predictions.db`. When matches finish, this bar shows how those frozen forecasts performed:

- **1X2** hit rate
- **O/U 2.5** hit rate
- **BTTS** hit rate
- **Goal MAE** — average |predicted total xG − actual goals|

Empty until you have stored predictions and finished results.

---

## Requirements

- **Python 3.11+**
- **Node.js 18+** (only for the Pitch UI dev server / build)

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/BSC-137/FIFA-26-Prediction-Engine.git
cd FIFA-26-Prediction-Engine
python -m venv venv
```

```powershell
# Windows
venv\Scripts\activate
pip install -e .
```

```bash
# macOS / Linux
source venv/bin/activate
pip install -e .
```

### 2. Configure `.env`

Copy the template (never commit `.env`):

```powershell
copy .env.example .env      # Windows
cp .env.example .env       # macOS / Linux
```

**Recommended defaults (no API key required):**

```env
DATA_PROVIDER=openfootball
WEATHER_PROVIDER=openmeteo
MODEL_VERSION=1.1.0
```

- Leave `USE_MOCK_DATA` **empty** or remove the line — empty means “not forced”.
- Set `API_FOOTBALL_KEY` only if you switch to `DATA_PROVIDER=api-football`.

### 3. Sync tournament data

```bash
python -m fifa26_engine.scripts.sync_wc2026_data
```

This downloads [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json) into `data/wc2026/worldcup.json`.

### 4. Verify

```powershell
.\scripts\run_api.ps1
```

In another terminal (PowerShell tip — avoid the `Invoke-WebRequest` prompt):

```powershell
curl.exe http://127.0.0.1:8000/health
```

Expected: `{"status":"ok","source":"openfootball"}`

---

## API

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness + data source |
| `GET` | `/status` | Refresh timestamps, fixture counts, ledger size |
| `GET` | `/model/info` | Active hyperparameters and `model_version` |
| `GET` | `/teams/stats` | WC 2026 W/D/L, goals, form per team |
| `GET` | `/fixtures` | List fixtures (`?status=scheduled\|live\|finished`) |
| `GET` | `/fixtures/refresh` | Bust caches and reload data |
| `GET` | `/predict/{fixture_id}` | Full prediction for one match |
| `GET` | `/predict` | Manual matchup (query params for teams + kickoff) |
| `GET` | `/accuracy/summary` | Ledger accuracy: 1X2, O/U, BTTS, MAE |
| `GET` | `/accuracy/fixtures` | Per-match prediction vs actual |
| `POST` | `/accuracy/recompute` | Refresh accuracy metrics |

Responses are cached in memory (fixtures ~5 min, predictions ~10 min). A background task refreshes data every 5 minutes by default.

---

## CLI tools & reports

| Command | Output | Purpose |
|---------|--------|---------|
| `python scripts/predict_upcoming.py --sync --all` | `reports/upcoming_predictions.json` | Batch forecast for all scheduled fixtures |
| `python -m fifa26_engine.scripts.backtest_walkforward` | `reports/backtest_walkforward.md` | Full-tournament walk-forward backtest |
| `python -m fifa26_engine.scripts.wc2026_team_stats` | `reports/wc2026_team_stats.json` | Tournament table stats |
| `python -m fifa26_engine.scripts.tune_hyperparams` | `reports/tuning_results.json` | Grid search over core hyperparameters |

**Pre-match comparison ledgers** (fill in actual results after matches):

- `reports/predictions_2026-07-01.md` — human-readable matchday sheet
- `reports/predictions_2026-07-01.json` — same data for scripting

**Walk-forward backtest** (last N knockouts example):

- `reports/backtest_last5_walkforward.md`

---

## Evaluation methodology

### Walk-forward backtest

For each finished fixture, in chronological order:

1. **`as_of = kickoff_utc`**
2. **Training pool** = all matches with `date < as_of` (strict — the target match is never included)
3. Full pipeline runs: strength → calibration → weather → adjustments → simulation
4. Predictions compared to actual 1X2, O/U 2.5, BTTS, and goal xG

Research backtests **do not** read or write `predictions.db`.

```bash
python -m fifa26_engine.scripts.backtest_walkforward
```

### Prediction ledger

For live forecasting accountability:

1. Before kickoff, `LedgerService` stores one row per fixture (`as_of_utc ≤ kickoff_utc`)
2. Stored fields include 1X2, BTTS, over 2.5, xG, top scores
3. After full-time, `/accuracy/*` compares **stored** predictions to results — never regenerates

Ledger sync runs on background refresh and `GET /fixtures/refresh`.

---

## Hyperparameters (model `1.1.0`)

All values are overridable in `.env`. Runtime values: `GET /model/info`.

| Variable | Default | Role |
|----------|---------|------|
| `MODEL_VERSION` | `1.1.0` | Tags predictions and ledger rows |
| `TEAM_HISTORY_LIMIT` | `30` | Max tournament results per team in training pool |
| `SHRINKAGE_PRIOR_MATCHES` | `8.0` | Pseudo-match count for rating shrinkage |
| `INTERCEPT_PRIOR_GOALS` | `1.45` | Baseline scoring rate when data is thin |
| `TIME_DECAY_HALF_LIFE_DAYS` | `21` | Recent matches weighted more (`0` = off) |
| `DIXON_COLES_RHO` | `-0.13` | Low-score correlation (group stage) |
| `KNOCKOUT_DIXON_COLES_RHO` | `-0.08` | Less draw inflation in knockouts |
| `TOURNAMENT_MIN_TOTAL_XG` | `2.0` | Minimum total xG floor (group) |
| `KNOCKOUT_MIN_TOTAL_XG` | `2.4` | Minimum total xG floor (knockout) |
| `TOURNAMENT_SCORING_PRIOR_WEIGHT` | `0.20` | Blend toward observed WC scoring rate |
| `ELO_BLEND_WEIGHT` | `0.25` | Elo xG blend weight |
| `HOST_NATION_BOOST` | `0.12` | Log-rate boost for mexico / usa / canada |
| `WEATHER_DELTA_SCALE` | `0.35` | Weather affinity modifier scale |
| `WEATHER_MIN_BUCKET_SAMPLES` | `5` | Min samples before full weather weight |

Adjustment-rule constants (rest penalties, ±8% cap) live in code and are not grid-searched.

---

## Project layout

```
FIFA26 Engine/
├── fifa26_engine/
│   ├── api/              # FastAPI app, schemas, serves built UI at /
│   ├── config/           # Settings + ModelConfig
│   ├── data/             # openfootball, API-Football, mock providers
│   ├── models/           # strength, calibration, simulator, knockout, evaluation
│   ├── services/         # prediction, ledger, refresh, accuracy
│   ├── storage/          # SQLite prediction ledger
│   └── scripts/          # backtest, sync, tune, validate
├── frontend/             # Prediction Pitch UI (Vite + React)
├── scripts/              # run_api, run_ui, predict_upcoming, setup_env
├── data/wc2026/          # Cached openfootball JSON
├── reports/              # Backtests, predictions, team stats
└── predictions.db        # Pre-kickoff forecast ledger (gitignored)
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| UI shows `ECONNREFUSED :8000` | Start `.\scripts\run_api.ps1` first; wait for “Uvicorn running” |
| `use_mock_data` validation error | Pull latest code (empty `USE_MOCK_DATA=` is now allowed) or remove that line from `.env` |
| PowerShell `curl` prompts for confirmation | Use `curl.exe http://127.0.0.1:8000/health` instead |
| No matches in UI | Click **Sync data** or run `sync_wc2026_data`; check filter isn’t hiding fixtures |
| Ledger accuracy empty | Needs finished matches with stored pre-kickoff predictions |

---

## Development

- **Pipeline entry:** `fifa26_engine/services/prediction_service.py` → `predict_fixture_markets()`
- **Leakage guard:** `fifa26_engine/models/temporal.py` → `filter_results_before()`
- **Tests:** `pytest tests/`

---

## License

MIT
