---
created: 2026-05-07
updated: 2026-05-07
tags: [bibliography, papers, references, literature]
status: active
priority: P2
source: workspace/research/bibliography.md
relates: [volatility, har-components, evaluation-framework, project-design]
---

# Bibliography — Summary

~80 entries across 11 categories. Quality ratings: essential / recommended / optional.

## Category Index

| Category | Topic | Key Papers |
|----------|-------|-----------|
| A | RV Estimators & Theory | Andersen-Bollerslev (2003), BNS (2002), BNHLS (2008), Hansen-Lunde (2006), Liu-Patton-Sheppard (2015) |
| B | HAR Family & Baselines | Corsi (2009), ABD (2007), BPQ (2016) HARQ, Patton-Sheppard (2015) SHAR, Hansen-Huang-Shek (2012) |
| C | Rough Volatility | Gatheral-Jaisson-Rosenbaum (2018), Cont-Das (2024), Bennedsen-Lunde-Pakkanen (2022) |
| D | ML for Vol — Empirical | CSV (2023), Rahimikia-Poon (2020), Bucci (2020), "HARd to Beat" (2024) |
| E | LOB Deep Learning | Optiver solutions, DeepVol, Sirignano-Cont (2019), Chen-Robert (2022) |
| F | VRP and Options | BTZ (2009), Bekaert-Hoerova (2014), Fouhy (2024), Bollerslev-Todorov (2015) |
| G | Forecast Evaluation | Patton (2011), DM (1995), Hansen-Lunde-Nason (2011) MCS, Bailey-LdP (2014) DSR |
| H | Rashomon & Optimal Trees | TreeFARMS (2022), GOSDT (2020), STreeD (2023-24), SPLIT (2025) |
| I | Modern Deep TS Forecasting | TiDE, N-BEATS, PatchTST — limited RV evidence |
| J | Code Repos & Data Sources | Oxford-Man, arch package, LightGBM, PyTorch Geometric |
| K | Practitioner & Industry | Optiver Kaggle docs, mlcontests meta-analysis |

## Essential Papers (Must-Read)

1. **Corsi (2009)** — HAR model (2,100+ citations). The benchmark.
2. **BPQ (2016)** — HARQ: RQ interaction gives 6% QLIKE and 8% MSE improvement
3. **Patton-Sheppard (2015)** — SHAR: signed semivariances, 2-4% QLIKE
4. **Patton (2011)** — QLIKE is the only robust loss for ranking vol forecasters
5. **Hansen-Lunde-Nason (2011)** — Model Confidence Set
6. **CSV (2023)** — Tree models beat HAR with rich features (our project extends this)
7. **BTZ (2009)** — VRP predicts returns; operationalizes IV-RV gap
8. **Liu-Patton-Sheppard (2015)** — 5-min RV very hard to beat across estimators
9. **Lopez de Prado (2018)** — Purged CV, fractional differencing, DSR

## Topic Tags

rv-estimators, har, har-extensions, harq, jump-detection, leverage-effect, microstructure-noise, rough-vol, ml-vol, lightgbm, lstm, tcn, transformer, graph-nn, vrp, options-implied, evaluation, qlike, mcs, dm-test, purged-cv, dsr, rashomon, optimal-trees, long-memory, cross-asset, spillover
