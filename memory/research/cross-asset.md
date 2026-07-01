---
created: 2026-05-07
updated: 2026-05-07
tags: [cross-asset, spillover, DY-index, GNN, graph, treasury, FX, commodities]
status: active
priority: P2
source: workspace/research/cross-asset.md (archived)
relates: [optimal-feature-set, data-access, project-design]
---

# Cross-Asset Features — Summary

## Diebold-Yilmaz Spillover Framework

- Generalized forecast-error variance decomposition from VAR of realized vols
- Total connectedness index spikes during crises
- Key cross-asset features: VIX, MOVE (rates vol), CDX/iTraxx credit spreads, USD index vol, gold vol
- 1-5% QLIKE improvement, concentrated in **regime transitions** (exactly when forecasts most valuable)

## GNN Cross-Asset Findings

**Zhang-Pu-Cucuringu-Dong (2025, Int. J. Forecasting):**
- Graph attention networks for multivariate RV
- Multi-hop spillovers add little
- Nonlinear one-hop spillover effects help short-horizon (≤1 week)
- Training with **QLIKE loss substantially outperforms MSE training** (even for GNNs)

**SpotV2Net (Brini-Toscano 2025):** vol-of-vol-informed graph attention for intraday spot vol

## Factor Models for Volatility

- Herskovic-Kelly-Lustig-Van Nieuwerburgh (2016): "common idiosyncratic volatility" — decompose RV into systematic + idiosyncratic
- Sector-mean RV as common factor captures co-movement (Graph-HAR, Ch.14)
- Graph-HAR: γ × Σ W_{jk} × RV_{k,t} — neighbor-weighted RV captures how AAPL vol depends on MSFT vol

## Our Available Cross-Asset Data

| Asset Class | Instruments |
|-------------|------------|
| Treasuries | 2y, 5y, 10y, 30y yields |
| FX | USD/JPY, EUR/USD |
| Commodities | CL (crude), GC (gold) |
| Bond futures | TY (10y Treasury) |

## Key Feature Constructions

- Treasury slope change: Δ(10y − 2y) — inversion precedes equity vol spikes
- FX vol (USD/JPY): yen carry unwind = global risk-off = equity vol spike
- Commodity vol (CL, GC): oil vol → macro uncertainty; gold vol → flight-to-safety
- DY Spillover Index: VAR(5) on 34-asset panel → variance decomposition
- VIX-equity correlation regime: rolling 20-day corr(ΔVIX, SPX returns)
