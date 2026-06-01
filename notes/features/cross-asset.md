# Cross-Asset Features

What we've learned about volatility spillovers and correlations.

## Findings

(To be filled as we explore data)

## Questions to Answer

- How correlated is RV across our 34-symbol universe?
- Are there clear lead-lag relationships in volatility?
- Does sector/asset-class structure show up in the correlation matrix?
- How much does cross-asset information improve single-asset RV forecasts?

## Deep Research Findings (2026-05-06)

**Volatility spillover framework:**
- Diebold & Yilmaz (2009, 2012, 2014): generalized forecast-error variance decomposition from a VAR of realized vols. Total connectedness index spikes during crises (`diebold-yilmaz-2012` in bibliography)
- Key cross-asset features: VIX, MOVE (rates vol), CDX/iTraxx credit spreads, USD index vol, gold vol

**GNN cross-asset findings:**
- Zhang, Pu, Cucuringu & Dong (2025, Int. J. Forecasting): graph attention networks for multivariate RV. Key findings: multi-hop spillovers add little; nonlinear one-hop spillover effects help short-horizon (<=1 week) forecasts; training with QLIKE loss substantially outperforms MSE training (`zhang-pu-cucuringu-dong-2025` in bibliography)
- SpotV2Net (Brini & Toscano 2025): vol-of-vol-informed graph attention for intraday spot vol (`brini-toscano-2025` in bibliography)

**Factor models for volatility:**
- Herskovic, Kelly, Lustig & Van Nieuwerburgh (2016, JFE): "common idiosyncratic volatility" -- can decompose realized vol into systematic and idiosyncratic components
- Andersen, Bollerslev, Diebold & Ebens (2001): factor structure in daily equity vol

**Realized covariance estimation:**
- BNHLS (2011) multivariate realized kernels; Hayashi-Yoshida (2005) refresh-time sampling for asynchronous assets
- HEAVY-MV (Noureldin, Shephard & Sheppard 2012) for multivariate realized measures

## Deep Research Findings (2026-05-31): graph methods win on covariance, not univariate RV

Full brief: `notes/deep-research/2026-05-31-what-beats-har-2024-26.md`.

- **The cleanest, significance-backed graph win is on realized COVARIANCE, not univariate RV.** GHAR + Graphical-LASSO: QLIKE **-1.8%** vs HAR-DRD, Frobenius -2.5%, **MCS p=1.000**, 27 DJIA names, rolling 1,000-obs windows 2011-2021 (`chaozhang-ox/GNNHAR` on GitHub implements it, with HAR as the identity-adjacency special case and MCS testing built in).
- Cross-market spatial-temporal GNN-HAR (DCRNN-HAR, 8 global indices) shows MSE gains that grow with horizon (-13% at h=1 -> -54% at h=22) but **never computes QLIKE** -- treat the horizon-scaling pattern as real, the QLIKE transfer as unproven.
- **Strategic implication:** if the project targets the covariance problem (portfolio risk), graphs demonstrably help and there is a ready harness to port. If it stays univariate daily RV, graphs are not yet justified. This is now a flagged open decision in `open-questions.md`.
