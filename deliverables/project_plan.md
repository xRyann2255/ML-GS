# Risk as Alpha: ML Signal Discovery from SecDB Risk-System Outputs

**Author:** Ryan Vincent
**Date:** April 2026
**Duration:** 20 weeks (~5 months)
**Desk:** Cross-Asset (XA)

## 1. Project Overview

Intermediary asset pricing theory proves that dealer balance-sheet constraints drive risk premia across asset classes. Every external test of this theory uses stale quarterly data from the Federal Reserve's Z.1 tables or Compustat leverage. We sit on the real thing: daily, cross-asset risk-system outputs from SecDB, with correct dealer sign and no publication lag.

This project tests whether internal risk-system outputs (VaR, component VaR, factor-VaR decompositions, scenario P&L, VaR utilization) predict cross-asset returns, volatility, and drawdowns. The approach is rigorous: every signal is benchmarked against a ridge regression baseline on identical features, validated with purged cross-validation and the Deflated Sharpe Ratio, and tested for redundancy against publicly available factors.

The project is structured as a layered build. Project 1 ("Risk as Alpha") is the primary deliverable. A data-driven checkpoint at week 13 determines whether to deepen Project 1 or pivot to Project 2 ("Book-Gamma Intraday Momentum"), which reuses the same infrastructure. Both paths produce a desk-ready research report and presentation.

---

## 2. Theoretical Foundation

The core thesis rests on a well-established body of academic work. The logic runs in four steps:

**Step 1: Dealers are the marginal investors in most markets.**
Classical asset pricing assumes a representative household whose consumption drives risk premia. This fails empirically (the equity premium puzzle). The intermediary approach replaces the household with the financial intermediary: in derivatives, credit, FX, and fixed income, broker-dealers hold the inventory, provide liquidity, and absorb order-flow imbalances. Their constraints, not household preferences, determine the pricing kernel.

**Step 2: When dealer constraints bind, risk premia spike.**
He and Krishnamurthy (2013, AER) show that risk premia are a nonlinear function of the intermediary's capital ratio. When capital is ample, risk premia are low and stable. When the constraint boundary approaches, risk premia spike sharply. The same market shock produces radically different risk-premium responses depending on how constrained the dealer is at the time.

**Step 3: This is empirically verified across multiple asset classes.**
- Adrian, Etula, and Muir (2014, JF) show that a single broker-dealer leverage factor prices 41 equity, momentum, and bond portfolios with a cross-sectional R-squared of 77%, outperforming the CAPM (24%) and matching Fama-French (73%).
- He, Kelly, and Manela (2017, JFE) extend this result across seven asset classes (equities, government and corporate bonds, sovereign bonds, options, CDS, commodities, and FX) using a single primary-dealer capital ratio. The capital risk premium is approximately 9% per year.
- Adrian and Shin (2010, JFI) demonstrate that growth in dealer repo positions forecasts VIX innovations, raising the VIX forecasting R-squared from 8.9% to 11.6% at weekly frequency.
- Coval and Stafford (2007, JFE) show that stocks subject to flow-driven forced selling experience cumulative abnormal returns of approximately -10% during the selling period, with partial reversals over the following year.

**Step 4: Every academic test used low-frequency, lagged, aggregate data.**
The theory is strong and empirically supported. The bottleneck has always been data quality. SecDB provides the same economic information that the academics proxy with quarterly Fed data, but at daily frequency, with no publication lag, and at desk-level granularity.

---

## 3. The Data Edge

The table below summarizes the data advantage:

| Paper | Data Source | Frequency | Publication Lag | Granularity |
|---|---|---|---|---|
| Adrian, Etula, Muir (2014) | Fed Z.1 | Quarterly | ~2 months | Sector aggregate |
| He, Kelly, Manela (2017) | CRSP/Compustat | Quarterly | ~1 month | Firm (holding co.) |
| Adrian, Shin (2010) | Fed Z.1 | Weekly | ~1 week | Sector aggregate |
| **This project** | **SecDB** | **Daily** | **T+1 morning** | **Desk / position** |

The advantage is threefold:

1. **Frequency:** Daily vs. quarterly provides roughly 60x more observations per year. For ML methods that require data volume, this matters substantially.
2. **Timeliness:** We observe today's risk state tomorrow morning. The academics observe last quarter's risk state two months later. Any predictive signal in intermediary constraints has likely dissipated by the time public data is released.
3. **Granularity:** We observe risk decomposed by desk, factor, scenario, and position. The academics observe a single aggregate number for the entire broker-dealer sector. Disaggregation allows us to identify which constraints matter and where pressure is building.

**Important caveats:** We observe a single firm, not the entire dealer sector. History may span only 5-10 years (vs. 40+ year academic samples). The correct framing is "better data that should contain more signal, pending rigorous validation," not "the signal is guaranteed."

---

## 4. Feature Families

Five signal families are extracted from SecDB risk cube outputs. Each maps to a specific theoretical prediction. VaR utilization and factor concentration are tested first (strongest theoretical backing).

### 4.1 VaR Utilization (Priority)

**What it measures:** Current VaR as a percentage of the desk's VaR limit, capturing how much of the risk budget is deployed.

**Theoretical basis:** This is the most direct proxy for the binding constraint in He and Krishnamurthy (2013). When utilization approaches 100%, the desk must reduce positions regardless of fundamental value. Adrian and Shin (2014) show that dealer leverage is procyclical and constrained by VaR limits. Coval and Stafford (2007) demonstrate that forced selling creates predictable price pressure and subsequent reversals.

**Features:** Utilization level (%), 1/5/21-day rate of change, z-score relative to rolling 63-day window. The z-score distinguishes chronic high utilization from acute spikes (the fire-sale-imminent case).

### 4.2 Factor Concentration (Priority)

**What it measures:** How concentrated the portfolio's risk is across underlying factors, using the Herfindahl-Hirschman Index (HHI) on factor-VaR shares.

**Theoretical basis:** When many dealers crowd into the same factor, concentration rises. If that factor reverses, concentrated dealers must all deleverage simultaneously, triggering fire sales (Coval and Stafford, 2007) and predictable return reversals. He, Kelly, and Manela (2017) show that a single intermediary-capital factor prices risk across asset classes; high concentration means the pricing kernel is exposed to a single point of failure.

**Features:** HHI on factor-VaR shares, top-3 factor share, rolling HHI change (5d, 21d).

### 4.3 VaR Dynamics

**What it measures:** How the aggregate risk number is evolving over time, capturing balance-sheet expansion or contraction.

**Theoretical basis:** Adrian and Shin (2010) show that changes in dealer balance-sheet size (measured by repo growth) forecast VIX innovations. Rising VaR indicates the desk is absorbing more risk; falling VaR indicates pullback.

**Features:** Daily change in total VaR, component VaR by asset class (rates, credit, equity, FX, commodities), VaR momentum (5-day rolling change with sign-preserving square root compression).

### 4.4 Scenario P&L

**What it measures:** Portfolio vulnerability under stress scenarios, providing forward-looking information that complements VaR's backward-looking nature.

**Theoretical basis:** Scenario analysis captures tail-risk awareness and directional exposure. Changes in the worst-case scenario identity reveal qualitative shifts in portfolio vulnerability before they appear in VaR.

**Features:** Worst-case scenario identity (categorical), scenario P&L dispersion (standard deviation across scenarios), worst-case identity flip indicator (binary), scenario P&L skewness.

### 4.5 Cross-Asset Flow

**What it measures:** How risk is migrating between asset classes over time, tracking dealer balance-sheet reallocation.

**Theoretical basis:** He, Kelly, and Manela (2017) show that a single intermediary factor prices all asset classes simultaneously. If the rates desk absorbs more risk while the credit desk sheds it, the resulting capital reallocation should predict relative returns between those asset classes.

**Features:** Component VaR share shifts by asset class (5d, 21d horizons), rolling cross-asset VaR correlation for key asset-class pairs.

---

## 5. Prediction Targets

Four targets are tested, each motivated by specific findings in the literature:

| Target | Motivation | Signal-to-Noise |
|---|---|---|
| **VIX innovations** | Adrian and Shin (2010) show dealer repos forecast VIX changes; cleanest single target | High |
| **Drawdowns in the most-concentrated asset class** | If factor HHI is high in rates, do rates draw down next? Direct Coval-Stafford prediction | Medium |
| **Cross-asset momentum reversals** | Does a VaR utilization spike predict mean-reversion in crowded factors? | Medium |
| **Realized volatility** | Simpler target than returns, higher signal-to-noise; broader applicability | High |

Each feature family is tested against each target independently before combining, to avoid confounding.

---

## 6. Validation Framework

Validation is non-negotiable. The framework is designed to prevent overfitting and ensure that any reported signal is genuine.

### Ridge Baseline on Identical Features
Every model is benchmarked against a ridge regression (L2-regularized linear model) trained on the exact same features. If LightGBM does not beat ridge, the ML is adding overfitting, not nonlinear signal. This is motivated by Kozak, Nagel, and Santosh (2020, JFE), who show that ridge on principal components matches or exceeds nonlinear ML in many financial settings.

### Purged K-Fold Cross-Validation with Embargo
Standard cross-validation leaks information through temporal autocorrelation. Purged CV removes training observations whose labels overlap with the test period and adds an embargo buffer after each test fold. This follows Lopez de Prado (2018, Ch. 7).

### Combinatorial Purged Cross-Validation (CPCV)
CPCV generates a full distribution of Sharpe ratios from a single history by exhaustively combining test folds. This provides a confidence interval on Sharpe rather than a single point estimate.

### Deflated Sharpe Ratio (DSR)
Bailey and Lopez de Prado (2014) show that running multiple experiments inflates the best observed Sharpe. DSR adjusts for the number of trials attempted, non-normality of returns, and sample length. Every experiment is logged to an experiment tracker, and the total trial count feeds the DSR adjustment. With approximately 1,250 daily observations (5 years), roughly 45 independent trials exhaust a Sharpe of 1.0.

### Harvey-Liu Haircut Sharpe
A complementary multiple-testing correction (Bonferroni, Holm, BHY-FDR) applied to all reported Sharpe ratios.

### Confound Checks Against Public Factors
Any signal family that shows positive IC is retested with public factors as controls (VIX level/change, credit spread, term slope, equity market return, dollar index). A feature that vanishes after adding controls is a noisy proxy for publicly available information, not a new signal.

### Transaction-Cost-Aware Backtesting
All backtests include parameterized spread/slippage per asset class from day one. The breakeven cost level (where Sharpe reaches zero) is reported alongside gross metrics.

---

## 7. Project Phases and Timeline

### Phase 0: Pitch and Alignment (Weeks 1-2)

**Goal:** Get sponsor buy-in and confirm data access before building anything.

**Deliverables:**
- 1-2 page pitch document for sponsor
- Data access audit: confirm which risk cube outputs are pullable (delta VaR, component VaR, factor-VaR concentration, scenario P&L, VaR utilization)
- Environment and package audit: confirm Python packages and compute constraints
- Risk-model methodology change investigation (dates of any VaR model changes in the lookback period)
- Holdout reservation: set aside the most recent 3-6 months as true out-of-sample data
- Experiment tracking log initialized

**Minimum viable data gate:** Confirmed read access to (a) daily VaR with component breakdown by asset class, and (b) at least one of scenario P&L, factor-VaR decomposition, or VaR utilization. If these are not pullable, the project direction is reassessed.

### Phase 1: Shared Infrastructure (Weeks 3-5)

**Goal:** Build the validation and backtesting layer that both Project 1 and Project 2 will use. This is the infrastructure investment that separates credible work from "intern ran a GBM."

**Components:**
- **Data pipeline** with point-in-time stamping (VaR for date T is available at T+1 morning, not T close) and holdout enforcement
- **Label construction:** triple-barrier labeling (Lopez de Prado, AFML Ch. 3), meta-labeling scaffold, standard return labels (1d, 5d, 21d)
- **Validation stack:** purged K-fold CV with embargo, CPCV, Deflated Sharpe Ratio, Harvey-Liu Haircut Sharpe, ridge baseline
- **Backtesting engine:** transaction-cost-aware P&L, full reporting suite (IC, Sharpe, Sortino, hit rate, turnover, max drawdown), SHAP integration
- **Experiment tracker:** logs every configuration tried for honest DSR adjustment
- **Smoke test:** validate the full stack on a synthetic toy problem before proceeding to real data

**Why shared:** Every component works identically for Project 1 (risk-system features predicting cross-asset returns) and Project 2 (Greeks features predicting intraday momentum). Built once, used by both.

### Phase 2: Project 1 Core (Weeks 6-12)

**Goal:** Build and test the core hypothesis across all five feature families and four prediction targets.

**Approach:**
1. **Priority features first (Weeks 6-8):** VaR utilization and factor concentration, tested against all targets. If these show no signal, the remaining families are unlikely to either.
2. **Remaining features (Weeks 8-10):** VaR dynamics, scenario P&L, cross-asset flow.
3. **Modeling (Weeks 9-12):** Ridge baseline first on all features; LightGBM on identical features to measure marginal lift; SHAP and MDA stability across CV folds; confound checks against public factors; panel structure with asset-class fixed effects.

**Key risk:** Sample size. Firm-level VaR produces approximately 1,250 daily observations over 5 years. Discipline required: track every experiment for DSR, prefer theory-motivated features over data-mining, and use panel structure to increase effective sample size.

### Phase 3: Checkpoint and Decision (Week 13)

**Goal:** Data-driven go/no-go assessment with sponsor.

**Decision criteria:**

| Path | Criteria |
|---|---|
| **Continue Project 1** | At least one signal family has IC > 0 after purged CV; GBM beats ridge; DSR-adjusted Sharpe remains positive; feature importance stable across folds |
| **Pivot to Project 2** | All signal families flat or unstable; GBM does not beat ridge; DSR kills the Sharpe |
| **Hybrid** | Partial success: keep working features from Project 1 as a base, add Project 2's Greeks-based features as additional inputs into the same model |

**Deliverable:** 1-2 page checkpoint memo documenting what worked, what did not, and the decision rationale.

### Phase 4A: Deepen Project 1 (Weeks 14-17)

*Taken if the checkpoint passes.*

- **Regime overlay (Weeks 14-15):** Fit a Gaussian Mixture Model on macro features (VIX, credit spread, term slope, USD, realized correlation) to classify 3-4 regimes. Decompose signal performance by regime. If the signal is regime-conditional, that is a finding worth reporting.
- **Cross-asset panel extension (Weeks 15-16):** Move from firm-level aggregates to asset-class-level risk outputs. Test within-class prediction (rates component VaR predicting rates returns) vs. cross-prediction (rates VaR predicting equity drawdowns). This is the He-Kelly-Manela "single pricing kernel" test with real data.
- **Capacity and transaction cost sensitivity (Week 17):** Signal degradation as position size increases, turnover analysis, capacity estimates. This is what the trading floor asks about first.
- **Compliance review (Weeks 16-17):** Initiate compliance review to ensure final output can be presented.

### Phase 4B: Pivot to Book-Gamma (Weeks 14-17)

*Taken if the checkpoint fails.*

- Aggregate dealer gamma, vega, vanna, and charm from SecDB book Greeks across rates futures, G10 FX, and credit indices
- Test whether net gamma sign predicts last-30-minute intraday momentum (Baltussen, Da, Lammers, and Martens, 2021, JFE)
- SecDB advantage: real book-level sign (public GEX estimates assume the dealer side and are approximately 30% wrong)
- Same validation stack from Phase 1; control for short interest if touching equities (Muravyev, Pearson, and Pollet, 2022)

### Phase 5: Consolidation and Presentation (Weeks 18-20)

- **Walk-forward out-of-sample test (Week 18):** Unfreeze the reserved holdout (3-6 months). Retrain on all pre-holdout data, predict into holdout, report metrics. One shot only; no iteration.
- **Rolling-window stability check:** Retrain on 6-month rolling windows, confirm feature importance does not rotate.
- **Final DSR and Haircut Sharpe** on all reported numbers using the full trial count from the experiment log.
- **Research report (Weeks 18-19):** Hypothesis, data, methodology, results (one chart per claim, ridge alongside GBM on every chart), documented negatives, capacity analysis, next steps.
- **Presentation (Week 20):** Framed as causal hypothesis testing ("theory X predicts Y, we tested with proprietary data"). Lead with IC and Sharpe. One slide per claim. Prepared for desk Q&A on capacity, turnover, crisis behavior, and "why not just a linear model?"

---

## 8. Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Signal does not exist in risk-system outputs | Medium | Week 13 checkpoint; Project 2 fallback uses same infrastructure |
| Sample size too small for ML | Medium | Panel structure across asset classes; prefer theory-motivated features over mining |
| Overfitting / data snooping | High | DSR on every number; experiment tracking; ridge baseline; purged CV |
| Entitlements block key data | Low | Phase 0 data access audit before building anything |
| Feature importance unstable across folds | Medium | MDA stability check; drop unstable features |
| Transaction costs eat the signal | Medium | Cost-aware backtesting from day 1; turnover as a first-class metric |
| Risk-model methodology changes create structural breaks | Medium | Interview risk team in Phase 0; document change dates; include as control variables or restrict training to single methodology regime |
| Compliance review delays final output | Low | Initiate review at Week 16, not Week 20 |
| Sponsor unavailability at checkpoint | Low | Backup reviewer identified in Phase 0; checkpoint meeting pre-scheduled |
| Package or compute restrictions in bank environment | Low | Package audit in Phase 0; identify internal equivalents for blocked libraries |

---

## 9. Deliverables Summary

| Week | Deliverable | Format |
|---|---|---|
| 2 | Pitch document | 1-2 page memo |
| 2 | Data access audit | Documentation with sample pulls |
| 5 | Validated infrastructure | Code: data pipeline, validation stack, backtester, experiment tracker |
| 5 | Smoke test | Notebook confirming full stack on synthetic data |
| 12 | Signal test results | Notebooks with IC, Sharpe, SHAP for all feature-target combinations |
| 13 | Checkpoint memo | 1-2 page memo with decision rationale |
| 17 | Extended analysis | Regime decomposition, cross-asset panel, capacity analysis |
| 19 | Research report | Full desk-ready report with charts (one chart per claim) |
| 20 | Presentation | Slides with Q&A preparation |

---

## 10. Key References

**Intermediary Asset Pricing Theory:**
- He, Krishnamurthy (2013, AER). Intermediary asset pricing.
- Adrian, Etula, Muir (2014, JF). Financial intermediaries and the cross-section of asset returns.
- He, Kelly, Manela (2017, JFE). Intermediary asset pricing: new evidence from many asset classes.
- Adrian, Shin (2010, JFI). Liquidity and leverage.
- Adrian, Brunnermeier (2016, AER). CoVaR.
- Coval, Stafford (2007, JFE). Asset fire sales (and purchases) in equity markets.

**Validation and Anti-Overfitting:**
- Lopez de Prado (2018). Advances in Financial Machine Learning.
- Bailey, Lopez de Prado (2014). The Deflated Sharpe Ratio.
- Harvey, Liu (2015). Backtesting. (Haircut Sharpe methodology.)
- Kozak, Nagel, Santosh (2020, JFE). Shrinking the cross-section.

**ML Methods:**
- Gu, Kelly, Xiu (2020, RFS). Empirical asset pricing via machine learning.
- Kelly, Xiu (2023, NBER WP 31502). Financial machine learning. (Survey.)

**Project 2 (if pivot):**
- Baltussen, Da, Lammers, Martens (2021, JFE). Hedging demand and market intraday momentum.
- Barbon, Buraschi (2021). Gamma fragility.

**Caveats:**
- McLean, Pontiff (2016). Does academic research destroy stock return predictability? (30-50% post-publication decay.)
- Muravyev, Pearson, Pollet (2022). Is there a risk premium in the stock lending market? (Control for short interest.)
