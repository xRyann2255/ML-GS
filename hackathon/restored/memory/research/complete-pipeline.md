---
created: 2026-05-07
updated: 2026-05-07
tags: [pipeline, architecture, implementation, steps, lookahead, monitoring]
status: active
priority: P1
source: workspace/research/complete-pipeline.md (archived)
relates: [project-design, optimal-feature-set, evaluation-framework, data-access]
---

# Complete Pipeline — Summary

## End-to-End System

```
Data Sources:
  Tick RV, RQ        → Layers 0-1 (HAR + Jumps)          \
  Daily OHLCV        → Layers 0-1                         \
  E-mini L2 Depth    → Layer 3 (Microstructure)            → Feature Store (~80-120)
  SPX IV Surface     → Layer 2 (Options)                  /       |
  VIX Term Structure → Layer 2                           /    +---+---+
  Cross-Asset        → Layers 4-7                       /     |   |   |
                                                           LGBM LSTM Trees
                                                              \  |  /
                                                         Ensemble Blend
                                                               |
                                                      log(RV_{t+h}) forecast
                                                               |
                                                      Evaluation (QLIKE, DM, MCS)
```

LSTM also receives raw intraday bar sequences directly from E-mini L2.

## Implementation Order (Each Step = Standalone Result)

| Step | Features | Model | Deliverable |
|------|----------|-------|-------------|
| 1 | HARQ + SHAR (L0-L1, 11 features) | OLS/Ridge | Walk-forward QLIKE baseline table |
| 2 | +Options layer (~20 total) | LightGBM | QLIKE lift vs Step 1; SHAP |
| 3 | +Cross-asset (~30 total) | LightGBM | Spillover contribution analysis |
| 4 | E-mini microstructure (separate) | LSTM/TCN | Standalone intraday forecast |
| 5 | Full feature set (L5-L7, 80-120) | Ensemble | Final QLIKE; DM; MCS |
| 6 | Rashomon analysis | Optimal Trees | Variable importance stability |

**Steps 1-2 are critical path.** If Step 1 baseline is weak, all subsequent comparisons misleading. Step 2 = first genuine ML-vs-baseline comparison.

## Re-training & Monitoring

- Retrain weekly on rolling 5-year window
- Track feature importance Jaccard similarity (top-10) across retrains; drop below 0.6 = investigate
- Monitor trailing 20-day OOS QLIKE; alert if >10% degradation vs 60-day average

## Lookahead Bias Checklist

| Source | Rule |
|--------|------|
| Realized measures | Features for RV_{t+1} use only info ≤ t |
| Microstructure | Truncate intraday at t-ε; strict timestamp alignment |
| Options surface | Use end-of-day surface from day t for day t+1 |
| Cross-asset | Synchronize all inputs to same EOD cutoff |

> **Single most common error in financial ML.** When in doubt, add a one-day lag. Lookahead contamination shows excellent in-sample QLIKE that vanishes OOS.
