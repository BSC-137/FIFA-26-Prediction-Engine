# Walk-Forward Backtest — Last 5 Finished Matches

**Computed at:** 2026-07-01T15:04:30.497766+00:00
**Model version:** walkforward-1.1.0
**Fixtures:** 5

## Leakage guards

- Training pool uses only matches with `date < kickoff_utc` (strict cutoff).
- Target fixture score is **never** in the training set for its own prediction.
- Team strength, Elo, and weather affinity are fit on pre-kickoff history only.
- Context uses kickoff-time weather (observed or forecast), not post-match data.

> Mock weather history may be synthetic; observed kickoff weather is used when present on a MatchResult, otherwise a weather-provider forecast at kickoff.

## Aggregate metrics (last 5)

- **1X2 accuracy:** 40.0%
- **Brier score:** 0.6039
- **Log loss:** 1.0125
- **O/U 2.5 hit rate:** 40.0%
- **BTTS hit rate:** 20.0%
- **MAE total goals:** 0.527
- **MAE home goals:** 0.576
- **MAE away goals:** 0.404

## Prediction vs actual

| Match | Training n | Pred 1X2 | Actual 1X2 | 1X2 | Pred xG (H–A) | Actual (H–A) | Total xG err | O/U 2.5 | BTTS |
|-------|------------|----------|------------|-----|---------------|--------------|--------------|---------|------|
| Brazil vs Japan | 73 | Home win | Home win | ✓ | 1.31–1.05 | 2–1 | 0.63 | Under/Over ✗ | No/Yes ✗ |
| Germany vs Paraguay | 74 | Home win | Draw | ✗ | 1.29–1.08 | 1–1 | 0.37 | Under/Under ✓ | No/Yes ✗ |
| Netherlands vs Morocco | 75 | Home win | Draw | ✗ | 1.22–1.18 | 1–1 | 0.40 | Under/Under ✓ | No/Yes ✗ |
| Ivory Coast vs Norway | 76 | Home win | Away win | ✗ | 1.24–1.12 | 1–2 | 0.63 | Under/Over ✗ | No/Yes ✗ |
| France vs Sweden | 77 | Home win | Home win | ✓ | 1.56–0.84 | 3–0 | 0.60 | Under/Over ✗ | No/No ✓ |

## Per-match goal breakdown

### Brazil vs Japan (`wc26-076`)

- **Kickoff:** 2026-06-29 17:00:00+00:00
- **Stage:** Round of 32
- **Training matches used:** 73 (all strictly before kickoff)

| Metric | Predicted | Actual | Error |
|--------|-----------|--------|-------|
| Home goals (xG) | 1.315 | 2 | 0.685 |
| Away goals (xG) | 1.053 | 1 | 0.053 |
| Total goals | 2.367 | 3 | 0.633 |

- **1X2 probabilities:** H 41.5% · D 29.7% · A 28.8%
- **O/U 2.5:** pred Under · actual Over
- **BTTS:** pred No · actual Yes

### Germany vs Paraguay (`wc26-074`)

- **Kickoff:** 2026-06-29 20:30:00+00:00
- **Stage:** Round of 32
- **Training matches used:** 74 (all strictly before kickoff)

| Metric | Predicted | Actual | Error |
|--------|-----------|--------|-------|
| Home goals (xG) | 1.291 | 1 | 0.291 |
| Away goals (xG) | 1.076 | 1 | 0.076 |
| Total goals | 2.367 | 2 | 0.367 |

- **1X2 probabilities:** H 40.4% · D 29.8% · A 29.9%
- **O/U 2.5:** pred Under · actual Under
- **BTTS:** pred No · actual Yes

### Netherlands vs Morocco (`wc26-075`)

- **Kickoff:** 2026-06-30 01:00:00+00:00
- **Stage:** Round of 32
- **Training matches used:** 75 (all strictly before kickoff)

| Metric | Predicted | Actual | Error |
|--------|-----------|--------|-------|
| Home goals (xG) | 1.222 | 1 | 0.222 |
| Away goals (xG) | 1.178 | 1 | 0.178 |
| Total goals | 2.400 | 2 | 0.400 |

- **1X2 probabilities:** H 36.2% · D 29.7% · A 34.0%
- **O/U 2.5:** pred Under · actual Under
- **BTTS:** pred No · actual Yes

### Ivory Coast vs Norway (`wc26-078`)

- **Kickoff:** 2026-06-30 17:00:00+00:00
- **Stage:** Round of 32
- **Training matches used:** 76 (all strictly before kickoff)

| Metric | Predicted | Actual | Error |
|--------|-----------|--------|-------|
| Home goals (xG) | 1.241 | 1 | 0.241 |
| Away goals (xG) | 1.125 | 2 | 0.875 |
| Total goals | 2.365 | 3 | 0.635 |

- **1X2 probabilities:** H 37.9% · D 29.9% · A 32.2%
- **O/U 2.5:** pred Under · actual Over
- **BTTS:** pred No · actual Yes

### France vs Sweden (`wc26-077`)

- **Kickoff:** 2026-06-30 21:00:00+00:00
- **Stage:** Round of 32
- **Training matches used:** 77 (all strictly before kickoff)

| Metric | Predicted | Actual | Error |
|--------|-----------|--------|-------|
| Home goals (xG) | 1.561 | 3 | 1.439 |
| Away goals (xG) | 0.839 | 0 | 0.839 |
| Total goals | 2.400 | 3 | 0.600 |

- **1X2 probabilities:** H 53.4% · D 27.4% · A 19.2%
- **O/U 2.5:** pred Under · actual Over
- **BTTS:** pred No · actual No

