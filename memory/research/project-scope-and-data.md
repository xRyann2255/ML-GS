---
created: 2026-05-07
updated: 2026-05-07
tags: [scope, data, universe, success-criteria, pipeline, constraints]
status: active
priority: P1
source: workspace/research/project-scope-and-data.md
relates: [data-access, project-design, evaluation-framework, optimal-feature-set]
---

# Project Scope and Data — Summary

## What We Forecast

- **Target:** log(RV_{t+h}) for h ∈ {1, 5, 22} trading days
- **Multi-day aggregation:** RV_{t+1:t+h} = h⁻¹ × Σ_{j=1}^h RV_{t+j}
- **RV estimation:** 5-min returns using realized kernel estimator (BNHLS 2008)

## Universe

| Category | Count | Examples |
|----------|-------|---------|
| Mega-cap US equities | 30 | AAPL, MSFT, JPM, JNJ, XOM, AMZN |
| Broad-market ETFs | 4 | SPY, QQQ, IWM, DIA |
| Equity index futures | 1 | E-mini S&P 500 (ES) |
| **Total** | **35** | |

History: 11.3 years (Jan 2012 – Mar 2023), ~2,800 daily obs per symbol.

## Success Criteria

| Priority | Metric | Requirement |
|----------|--------|-------------|
| Primary | QLIKE | 30-80 bps improvement over HARQ baseline |
| Secondary | DM test | p < 0.05 vs each baseline |
| Tertiary | Economic value | OOS utility gain in vol-targeting portfolio |

## Pipeline Architecture

```
Raw Data (6 sources) → Feature Eng (Layers 0-7) → LightGBM  \
                                                    LSTM      → Ensemble → log(RV_{t+h}) → QLIKE
```

## GS Data Edge

| Capability | Our Data | Public | Edge |
|-----------|----------|--------|------|
| RV quality | Tick-level, 34 symbols | 5-min TAQ/Oxford-Man | Precise RQ, kernel estimators |
| Options surface | Full SPX tenor×strike | VIX only | Skew, butterfly, slope, event-implied |
| Micro depth | E-mini L2 (4M ticks/day) | L1 only | True depth imbalance levels 2-5 |
| Cross-asset sync | Same tick timestamp | Daily closes | Intraday lead-lag |
| Panel breadth | 30 + 4 + 1 | Typically 1 index | Graph models, cross-sectional features |

## Critical Constraints

- **L2 depth = E-mini only** — depth features are index-level market regime signals
- **IV surface = SPX only** — options features function as market-wide regime signals
- **Do NOT treat these as stock-level predictors** — creates spurious constant signal

## Key Insight

> "Features Over Models": Layers 0-2 (~20 features) achieve 85% of attainable accuracy. The feature set matters more than the model choice. HARQ with 5 features often beats ML with dozens of features.
