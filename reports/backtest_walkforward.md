# Walk-Forward Backtest Report

Computed at: 2026-07-01T03:40:30.062326+00:00
Model version: walkforward-1.0.0-rc1

> **Limitation:** Mock weather history may be synthetic; observed kickoff weather is used when present on a MatchResult, otherwise a weather-provider forecast at kickoff.

## Overall metrics

- Fixtures evaluated: 78
- 1X2 accuracy: 35.9%
- Brier score: 0.7090
- Log loss: 1.1558
- O/U 2.5 hit rate: 43.6%
- BTTS hit rate: 43.6%
- MAE total goals: 2.193

## Breakdown by stage

### Group

- Fixtures: 72
- 1X2 accuracy: 34.7%
- Brier score: 0.7218
- Log loss: 1.1745
- O/U 2.5 hit rate: 43.1%
- BTTS hit rate: 44.4%
- MAE total goals: 2.300

### Knockout

- Fixtures: 6
- 1X2 accuracy: 50.0%
- Brier score: 0.5546
- Log loss: 0.9309
- O/U 2.5 hit rate: 50.0%
- BTTS hit rate: 33.3%
- MAE total goals: 0.906

## Per-fixture results

| Fixture | Kickoff | Stage | Pred 1X2 | Actual | O/U 2.5 | BTTS |
|---------|---------|-------|----------|--------|---------|------|
| wc26-2026-06-11-mexico-south-africa | 2026-06-11 | group | home_win | home_win | N | N |
| wc26-2026-06-11-south-korea-czech-republic | 2026-06-12 | group | draw | home_win | N | N |
| wc26-2026-06-12-canada-bosnia-herzegovina | 2026-06-12 | group | draw | draw | Y | N |
| wc26-2026-06-12-united-states-paraguay | 2026-06-13 | group | draw | home_win | N | N |
| wc26-2026-06-13-qatar-switzerland | 2026-06-13 | group | draw | draw | Y | N |
| wc26-2026-06-13-brazil-morocco | 2026-06-13 | group | draw | draw | Y | N |
| wc26-2026-06-13-haiti-scotland | 2026-06-14 | group | draw | away_win | Y | Y |
| wc26-2026-06-13-australia-turkey | 2026-06-14 | group | draw | home_win | Y | Y |
| wc26-2026-06-14-germany-curacao | 2026-06-14 | group | draw | home_win | N | N |
| wc26-2026-06-14-netherlands-japan | 2026-06-14 | group | draw | draw | N | N |
| wc26-2026-06-14-ivory-coast-ecuador | 2026-06-14 | group | draw | home_win | Y | Y |
| wc26-2026-06-14-sweden-tunisia | 2026-06-15 | group | draw | home_win | N | N |
| wc26-2026-06-15-spain-cape-verde | 2026-06-15 | group | draw | draw | Y | Y |
| wc26-2026-06-15-belgium-egypt | 2026-06-15 | group | draw | draw | Y | N |
| wc26-2026-06-15-saudi-arabia-uruguay | 2026-06-15 | group | draw | draw | Y | N |
| wc26-2026-06-15-iran-new-zealand | 2026-06-16 | group | draw | draw | N | N |
| wc26-2026-06-16-france-senegal | 2026-06-16 | group | draw | home_win | N | N |
| wc26-2026-06-16-iraq-norway | 2026-06-16 | group | draw | away_win | N | N |
| wc26-2026-06-16-argentina-algeria | 2026-06-17 | group | draw | home_win | N | Y |
| wc26-2026-06-16-austria-jordan | 2026-06-17 | group | draw | home_win | N | N |
| wc26-2026-06-17-portugal-dr-congo | 2026-06-17 | group | draw | draw | Y | N |
| wc26-2026-06-17-england-croatia | 2026-06-17 | group | draw | home_win | N | N |
| wc26-2026-06-17-ghana-panama | 2026-06-17 | group | draw | home_win | Y | Y |
| wc26-2026-06-17-uzbekistan-colombia | 2026-06-18 | group | draw | away_win | N | N |
| wc26-2026-06-18-czech-republic-south-africa | 2026-06-18 | group | draw | draw | Y | N |
| wc26-2026-06-18-switzerland-bosnia-herzegovina | 2026-06-18 | group | draw | home_win | N | N |
| wc26-2026-06-18-canada-qatar | 2026-06-18 | group | draw | home_win | N | Y |
| wc26-2026-06-18-mexico-south-korea | 2026-06-19 | group | draw | home_win | Y | Y |
| wc26-2026-06-19-united-states-australia | 2026-06-19 | group | draw | home_win | Y | Y |
| wc26-2026-06-19-scotland-morocco | 2026-06-19 | group | draw | away_win | Y | Y |
| wc26-2026-06-19-brazil-haiti | 2026-06-20 | group | draw | home_win | N | Y |
| wc26-2026-06-19-turkey-paraguay | 2026-06-20 | group | draw | away_win | Y | Y |
| wc26-2026-06-20-netherlands-sweden | 2026-06-20 | group | draw | home_win | N | N |
| wc26-2026-06-20-germany-ivory-coast | 2026-06-20 | group | draw | home_win | N | N |
| wc26-2026-06-20-ecuador-curacao | 2026-06-21 | group | draw | draw | Y | Y |
| wc26-2026-06-20-tunisia-japan | 2026-06-21 | group | draw | away_win | N | Y |
| wc26-2026-06-21-spain-saudi-arabia | 2026-06-21 | group | draw | home_win | N | Y |
| wc26-2026-06-21-belgium-iran | 2026-06-21 | group | draw | draw | Y | Y |
| wc26-2026-06-21-uruguay-cape-verde | 2026-06-21 | group | draw | draw | N | N |
| wc26-2026-06-21-new-zealand-egypt | 2026-06-22 | group | draw | away_win | N | N |
| wc26-2026-06-22-argentina-austria | 2026-06-22 | group | draw | home_win | Y | Y |
| wc26-2026-06-22-france-iraq | 2026-06-22 | group | draw | home_win | N | Y |
| wc26-2026-06-22-norway-senegal | 2026-06-23 | group | draw | home_win | N | N |
| wc26-2026-06-22-jordan-algeria | 2026-06-23 | group | draw | away_win | N | N |
| wc26-2026-06-23-portugal-uzbekistan | 2026-06-23 | group | draw | home_win | N | Y |
| wc26-2026-06-23-england-ghana | 2026-06-23 | group | draw | draw | Y | Y |
| wc26-2026-06-23-panama-croatia | 2026-06-23 | group | draw | away_win | Y | Y |
| wc26-2026-06-23-colombia-dr-congo | 2026-06-24 | group | draw | home_win | Y | Y |
| wc26-2026-06-24-switzerland-canada | 2026-06-24 | group | draw | home_win | N | N |
| wc26-2026-06-24-bosnia-herzegovina-qatar | 2026-06-24 | group | draw | home_win | N | N |
| wc26-2026-06-24-scotland-brazil | 2026-06-24 | group | draw | away_win | N | Y |
| wc26-2026-06-24-morocco-haiti | 2026-06-24 | group | home_win | home_win | N | N |
| wc26-2026-06-24-czech-republic-mexico | 2026-06-25 | group | away_win | away_win | N | Y |
| wc26-2026-06-24-south-africa-south-korea | 2026-06-25 | group | draw | home_win | Y | Y |
| wc26-2026-06-25-curacao-ivory-coast | 2026-06-25 | group | draw | away_win | Y | Y |
| wc26-2026-06-25-ecuador-germany | 2026-06-25 | group | draw | home_win | N | N |
| wc26-2026-06-25-japan-sweden | 2026-06-25 | group | draw | draw | Y | N |
| wc26-2026-06-25-tunisia-netherlands | 2026-06-25 | group | draw | away_win | N | N |
| wc26-2026-06-25-turkey-united-states | 2026-06-26 | group | away_win | home_win | N | N |
| wc26-2026-06-25-paraguay-australia | 2026-06-26 | group | draw | draw | Y | Y |
| wc26-2026-06-26-norway-france | 2026-06-26 | group | draw | away_win | N | N |
| wc26-2026-06-26-senegal-iraq | 2026-06-26 | group | draw | home_win | N | Y |
| wc26-2026-06-26-cape-verde-saudi-arabia | 2026-06-27 | group | draw | draw | Y | Y |
| wc26-2026-06-26-uruguay-spain | 2026-06-27 | group | away_win | away_win | Y | Y |
| wc26-2026-06-26-egypt-iran | 2026-06-27 | group | draw | draw | Y | N |
| wc26-2026-06-26-new-zealand-belgium | 2026-06-27 | group | draw | away_win | N | N |
| wc26-2026-06-27-panama-england | 2026-06-27 | group | draw | away_win | Y | Y |
| wc26-2026-06-27-croatia-ghana | 2026-06-27 | group | draw | home_win | N | N |
| wc26-2026-06-27-colombia-portugal | 2026-06-27 | group | draw | draw | Y | Y |
| wc26-2026-06-27-dr-congo-uzbekistan | 2026-06-27 | group | draw | home_win | N | N |
| wc26-2026-06-27-algeria-austria | 2026-06-28 | group | draw | draw | N | N |
| wc26-2026-06-27-jordan-argentina | 2026-06-28 | group | away_win | away_win | N | N |
| wc26-073 | 2026-06-28 | knockout | away_win | away_win | Y | Y |
| wc26-076 | 2026-06-29 | knockout | draw | home_win | N | N |
| wc26-074 | 2026-06-29 | knockout | home_win | draw | Y | N |
| wc26-075 | 2026-06-30 | knockout | draw | draw | Y | N |
| wc26-078 | 2026-06-30 | knockout | draw | away_win | N | N |
| wc26-077 | 2026-06-30 | knockout | home_win | home_win | N | Y |
