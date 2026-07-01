---
created: 2026-05-07
updated: 2026-05-28
tags: [features, layers, horizon, selection, composition, diminishing-returns]
status: active
priority: P1
source: workspace/research/feature-composition.md (archived)
relates: [optimal-feature-set, project-design, har-components, calendar-events]
---

# Feature Composition and Selection — Summary

## Layers 5-7 (Calendar, Memory, Sentiment)

Individually weak but collectively additive — the last 5% of accuracy.

**Layer 5 — Calendar:**
- FOMC indicator (-1, 0, +1, +2 days): vol compression before, expansion after
- NFP/CPI, options expiry (monthly/quarterly), quarter-end rebalancing
- Earnings proximity (single names only), time-of-day (U-shape), day-of-week (weakening)

**Layer 6 — Memory:**
- Fractionally differenced RV: (1-L)^d with d ~ 0.35-0.45 (preserves long memory, ensures stationarity)
- Rolling Hurst exponent: H < 0.15 = rough/fast reversion; H > 0.3 = trending
- Vol-of-vol: std(RV) over 22 days
- Regime duration: days since last 2σ spike (mean-reversion clock)

**Layer 7 — Sentiment:**
- FinBERT + negative news count: 1-3% QLIKE in crises only (Audrino 2020)
- Include only if data pipeline effort justified; less value for index than single names

## Diminishing Returns Table

| Stage | Features | Cumulative |
|-------|----------|-----------|
| L0 (HAR core) | 5 | 55% |
| +L1 (jumps, asymmetry) | 11 | 70% |
| +L2 (options) | 20 | **85%** |
| +L3-L4 (micro, cross-asset) | 40 | 95% |
| +L5-L7 (calendar, memory, sentiment) | 80-120 | 100% |

**85% threshold achievable with L0-L2 + Ridge regression alone.**

## Feature Priority by Horizon

| Horizon | Dominant | ML Value-Add |
|---------|----------|-------------|
| Intraday (10min-1hr) | Microstructure (L3): price accel, OBI, spread | Trees + 600 features |
| 1 day | HAR core (L0) + RQ + asymmetry (L1) + abs_ret_w + vol_anomaly | HAR-IV init_score + return/activity features: +149 bps (trial-023) |
| 1 week | Options (L2) + ret_5d + signed_return expansion | VRP + momentum: +329 bps (trial-020) |
| 1 month | VRP (L2) + vol_anomaly + vix_change_x_abs_ret + ret_5d | +33 bps over trial-020 (trial-023) |

**1-day horizon is no longer hardest to beat.** HAR-IV init_score + return/activity features (abs_ret_w, vol_anomaly) deliver the largest absolute improvement (+149 bps at h=1). Key insight: smoothed absolute return (weekly) outperforms daily at h=1.

## Feature Engineering Principles

1. **Triple expansion:** For each base quantity compute {level, change, z-score} — captures state, direction, unusualness
2. **Horizon-dependent selection:** Drop micro at monthly (noise); drop calendar at intraday (known)
3. **Trees handle redundancy:** No need to pre-decorrelate — splits handle multicollinearity
4. **Single-model importance is unstable:** Correlated features → noisy rankings. Use Rashomon analysis for reliable importance.
