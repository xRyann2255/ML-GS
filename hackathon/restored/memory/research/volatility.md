---
created: 2026-05-07
updated: 2026-05-08
tags: [volatility, RV, estimators, HAR, ML, landscape, rough-vol, GARCH]
status: active
priority: P1
source: workspace/research/volatility.md (archived)
relates: [har-components, evaluation-framework, project-design, optimal-feature-set]
---

# Volatility Forecasting Landscape — Summary

## Core Definitions

- **Realized Variance:** RV_t = Σ r²_{t,i} from intraday returns. Converges to quadratic variation as Δt→0.
- **5-min RV** is the practical standard (Liu-Patton-Sheppard 2015: ~400 estimators tested, 5-min very hard to beat)
- **Noise-robust alternatives:** Realized Kernel (BNHLS 2008), TSRV, pre-averaging — use when going sub-5-min
- **Jump detection:** BPV (BNS 2004), Lee-Mykland intraday test, threshold/truncation (Corsi-Pirino-Renò)

## Econometric Baselines (What ML Must Beat)

**HAR** (Corsi 2009): RV_t = β₀ + β_d·RV_{t-1} + β_w·RV_w + β_m·RV_m + ε
Extensions: HAR-J/CJ (jump decomp), **SHAR** (semivariances), **HARQ** (RQ-adaptive weights), HAR-X (leverage, VIX, macro), **Ridge-HAR/Lasso-HAR** (penalized regression baselines)

**GARCH family:** GARCH, EGARCH, GJR-GARCH, FIGARCH, Realized GARCH (Hansen-Huang-Shek 2012)

**Rough volatility:** H ≈ 0.1 across assets (Gatheral-Jaisson-Rosenbaum 2018). But Cont-Das (2024): observed roughness partly microstructure noise artefact.

## Where ML Wins (Honest Assessment)

| Setting | ML vs HAR |
|---------|-----------|
| Daily, only past RV | ML's gains small and fragile ("HARd to Beat" 2024) |
| Daily, rich exogenous features | **ML wins 5-20% QLIKE** (CSV 2023, Rahimikia-Poon 2020) |
| Intraday with LOB data | **ML necessary** — HAR not applicable |
| Weekly-monthly | ML gains widen |
| Multi-asset / cross-sectional | Graph/panel networks beat univariate HAR |
| Stress regimes (COVID, GFC) | **ML under-performs HAR** — ensembles needed |

## ML Methods Ranked for Vol Forecasting

1. **LightGBM/XGBoost** — most consistently effective for tabular RV. Dominates Optiver. Feature engineering > model architecture.
2. **LSTM/GRU** — pooled across tickers, sequential data, non-linear persistence. Fragile on small samples.
3. **TCN/DeepVol** — dilated causal convolutions on 1-min returns. Parameter-efficient alternative to LSTM.
4. **Transformers** — mixed evidence for vol; work with LOB inputs + cross-sectional structure.
5. **Hybrid econometric+ML** — almost universally strongest: HAR structure + ML residuals or ensemble.

## Feature Engineering (Highest-Leverage Area)

- **Lagged RV transforms:** daily/weekly/monthly, log-RV, √RV, fractional differences
- **Asymmetric:** RS⁺, RS⁻, signed jumps (RS⁻ dominates)
- **RQ:** measurement error variance estimator — key HARQ feature
- **Options-implied:** ATM IV, VRP, skew, VVIX, term structure
- **Microstructure:** OBI, spread, WAP vol, VPIN, price acceleration
- **Cross-asset:** DY spillover, sector-mean RV, credit spreads
- **Engineering principle:** {level, change, z-score} for each base quantity

## VRP (Variance Risk Premium)

VRP = E^Q[RV] − E^P[RV] ≈ VIX² − forecast next-30-day RV
- Predicts S&P 500 quarterly excess returns (R² > 15%, BTZ 2009)
- Also forecasts future RV through mean reversion
- VVIX measures uncertainty about vol itself
