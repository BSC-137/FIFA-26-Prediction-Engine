# Walk-Forward Backtest Report

Computed at: 2026-06-30T15:19:20.248204+00:00
Model version: walkforward-v1

> **Limitation:** Mock weather history may be synthetic; observed kickoff weather is used when present on a MatchResult, otherwise a weather-provider forecast at kickoff.

## Overall metrics

- Fixtures evaluated: 5
- 1X2 accuracy: 40.0%
- Brier score: 0.7629
- Log loss: 1.2167
- O/U 2.5 hit rate: 40.0%
- BTTS hit rate: 40.0%
- MAE total goals: 1.996

## Breakdown by stage

### Group

- Fixtures: 5
- 1X2 accuracy: 40.0%
- Brier score: 0.7629
- Log loss: 1.2167
- O/U 2.5 hit rate: 40.0%
- BTTS hit rate: 40.0%
- MAE total goals: 1.996

## Per-fixture results

| Fixture | Kickoff | Stage | Pred 1X2 | Actual | O/U 2.5 | BTTS |
|---------|---------|-------|----------|--------|---------|------|
| wc26-001 | 2026-06-11 | group | draw | home_win | N | N |
| wc26-002 | 2026-06-12 | group | draw | home_win | N | Y |
| wc26-010 | 2026-06-16 | group | draw | draw | Y | N |
| wc26-007 | 2026-06-20 | group | draw | draw | N | N |
| wc26-008 | 2026-06-21 | group | draw | away_win | Y | Y |
