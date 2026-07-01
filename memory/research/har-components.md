---
created: 2026-05-07
updated: 2026-05-07
tags: [HAR, HARQ, SHAR, baselines, long-memory, fractional-differencing]
status: active
priority: P2
source: workspace/research/har-components.md (archived)
relates: [optimal-feature-set, volatility, evaluation-framework]
---

# HAR Components — Summary

## Core HAR Decomposition

RV_t = β₀ + β_d·RV_{t-1} + β_w·(1/5)Σ RV_{t-i} + β_m·(1/22)Σ RV_{t-i} + ε

Open empirical questions on our data:
- Does the 1/5/22-day split match autocorrelation structure?
- Which component (d/w/m) carries most predictive weight per asset?
- How stable are HAR coefficients over time / across regimes?

## Key Research Findings

**Realized higher moments as predictors:**
- Amaya-Christoffersen-Jacobs-Vasquez (2015): realized skewness and kurtosis predict future RV beyond HAR components
- Signed jump variation J = RS⁺ − RS⁻ provides directional decomposition

**Long memory and fractional differencing:**
- Lopez de Prado (AFML Ch.5): fractional differencing (d ~ 0.35-0.45) preserves long memory while ensuring stationarity — critical for ML models assuming stationarity
- Long memory is the core mechanism HAR exploits

**ML horizon findings:**
- Daily: HARQ + signed semivariances very hard to beat (≤ few percent QLIKE)
- Weekly/monthly: ML with long memory shows meaningful gains (CSV 2023)
- Intraday (10-30 min): ML + LOB features produce real gains (Optiver/DeepLOB regime)

**Accuracy comparison (CSV 2023, 29 DJIA, 2001-2017):**
- Relative MSE vs HAR=1.000: bagging 0.891, gradient boosting 0.958, RF 0.986, NN ensembles 0.954-0.990
- With full features (IV, EA, VIX): RF 0.901, gradient boosting 0.962, NN 0.885-0.944
- Interpretable optimal trees (depth 4-5): ~2-5% higher MSE than tuned LightGBM, but single inspectable tree
