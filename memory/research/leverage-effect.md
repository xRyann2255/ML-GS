---
created: 2026-05-07
updated: 2026-05-08
tags: [leverage-effect, semivariance, SHAR, asymmetry, signed-jumps]
status: active
priority: P2
source: workspace/research/leverage-effect.md (archived)
relates: [optimal-feature-set, har-components, jump-detection]
---

# Leverage Effect — Summary

## Core Finding

**Patton & Sheppard (2015, "Good Volatility, Bad Volatility"):**
- Negative semivariance RS⁻ has **substantially more predictive power** than RS⁺ for future RV
- Negative jumps raise future RV; positive jumps lower it
- "Significantly better out-of-sample forecast performance"
- **3-8% QLIKE improvement** per the vol learning guide
- One of the **most robust and replicable findings** in vol forecasting

## Formulas

- RS⁺_t = Σ r²_{t,i} × 1(r_{t,i} > 0) — positive semivariance
- RS⁻_t = Σ r²_{t,i} × 1(r_{t,i} < 0) — negative semivariance (dominates)
- RS⁻_w = (1/5) × Σ RS⁻_{t-i}, i=0..4 — weekly negative semivariance (persistent downside memory)
- RS⁺_w = weekly positive semivariance (weaker, provides contrast)
- Signed jump variation: J = RS⁺ − RS⁻ (directional decomposition)
- Signed negative jumps: J⁻_t = Σ r²_{t,i} × 1(r_{t,i} < 0, |r_{t,i}| > θ_t) — 1-3% QLIKE beyond unsigned

## Implications

- The asymmetry is strongest for equity indices (leverage effect most pronounced)
- For individual stocks: varies by sector (financials > tech)
- SHAR (HAR with signed semivariances) is a **stronger baseline** than plain HAR
- ML models should be benchmarked against SHAR, not just HAR

## Open Questions for Our Data

- How asymmetric is the return-vol relationship across 34 symbols?
- Do RS⁺ and RS⁻ diverge in predictive power as expected?
- Is leverage effect stronger intraday or at daily frequency?
- Does signed jump variation add beyond semivariances?
