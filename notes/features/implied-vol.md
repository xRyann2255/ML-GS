# Implied Volatility and VRP

What we've learned about options-implied information and the variance risk premium.

## Findings

(To be filled as we explore data)

## Questions to Answer

- What does the VIX-RV spread look like over time? Mean, distribution, regime dependence?
- How much does IV surface information improve RV forecasts beyond the ATM level?
- Is the variance risk premium a useful predictor of future RV, or just of returns?
- What's the right way to construct the IV-RV gap signal for our assets?

## Deep Research Findings (2026-05-06)

**VRP construction and predictiveness:**
- Variance risk premium: VRP = IV^2 - RV^2 (approximated as VIX^2 - E_t[RV_{t+1,t+30}])
- Bollerslev, Tauchen & Zhou (2009, RFS): VRP explains >15% of S&P 500 quarterly excess return variation 1990-2005 (`bollerslev-tauchen-zhou-2009` in bibliography)
- Bekaert & Hoerova (2014, J. Econometrics): VRP decomposition into risk and uncertainty components
- VRP is predictive of both returns and future vol, but relatively under-explored with ML methods

**VIX term structure features:**
- VIX level, VIX term structure slope and curvature as features
- Risk-neutral skewness from Bakshi, Kapadia & Madan (2003) -- captures tail risk expectations
- VVIX (vol-of-vol): direct CBOE index; matters for delta-neutral options strategies (gamma scalping P&L variance)

**Rough vol and VRP:**
- Rough volatility models naturally generate steep IV skew and large VRP
- Cont & Das (2024) critique is the frontier -- observed roughness may be a microstructure noise artefact, not a property of true vol (`cont-das-2024` in bibliography)

**ML on VRP:**
- Relatively under-explored. Bali, Hu, Murray (2019) and others use RF/XGBoost on VRP-conditioned features for return prediction, but not VRP forecasting itself -- potential gap to exploit

## Deep Research Findings (2026-05-31): options-implied vol is the strongest univariate QLIKE win

Full brief: `notes/deep-research/2026-05-31-what-beats-har-2024-26.md`.

- **Rough-Heston / options-implied spot vol augmenting HAR is the most credible univariate QLIKE win found in the 2024-26 sweep**: HAR-RV 0.0428 -> HAR-RHeston 0.0403 QLIKE (**+5.8%**), MAE -9%, DM stat -3.12 (p<0.01), robust across h=1-22 (arXiv 2604.02743, 2026). Caveat: single asset (S&P 500), 6-month COVID-spanning test window, and it needs an options surface + parametric calibration -- not pure ML. Directly motivates building out our Tier-2 options/VRP feature layer with a concrete spot-vol estimator.
- Reinforces the project's through-line: for HAR, the biggest wins come from the **information set** (options/VRP), not the model architecture. Paper worth ingesting into `reference/project-papers/`.
