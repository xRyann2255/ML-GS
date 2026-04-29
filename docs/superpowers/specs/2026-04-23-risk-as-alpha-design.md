# Risk as Alpha: ML Signal Discovery from SecDB Risk-System Outputs

## Project Overview

**Thesis:** Intermediary asset pricing theory (He-Krishnamurthy 2013, Adrian-Etula-Muir 2014, He-Kelly-Manela 2017) proves that dealer balance-sheet constraints price risk across asset classes. External researchers reconstruct these signals from stale quarterly Fed Z.1 tables. SecDB provides the real thing — daily, cross-asset, with correct dealer sign. This project tests whether internal risk-system outputs predict returns, volatility, and drawdowns across asset classes.

**Duration:** 20 weeks (~5 months), internship active now (April 2026)

**Desk:** Cross-asset (XA) — ideal alignment with the intermediary asset pricing literature

**Access:** Read access to risk cubes (VaR, scenario P&L, factor decompositions) confirmed

**Structure:** Layered build — Project 1 ("Risk as Alpha") as the primary deliverable with shared infrastructure enabling Project 2 ("Book-Gamma Intraday Momentum") as fallback or extension. Data-driven checkpoint at week 13.

---

## Phase 0: Pitch & Alignment (Weeks 1-2)

### Goal
Get sponsor buy-in before building anything.

### Pitch Narrative
> "Intermediary asset pricing theory proves that dealer balance-sheet constraints price risk across asset classes. Every external test of this uses stale quarterly Fed Z.1 data or Compstat leverage. We sit on the real thing — daily, cross-asset, with correct dealer sign. I want to test whether our internal risk-system outputs predict the same dynamics the theory says they should, using rigorous ML methodology with proper validation."

### Deliverables
- 1-2 page pitch document for sponsor
- Data access audit: confirm exactly which risk cube outputs are pullable
  - Delta VaR, component VaR by asset class
  - Factor-VaR concentration (Herfindahl)
  - Scenario P&L rank and dispersion
  - VaR utilization %
- Entitlements map: read-accessible vs. needs desk sign-off
- Initial data pull to confirm pipeline feasibility
- Identify any compliance constraints on documentation/output
- Confirm Python package availability in compute environment (mlfinlab, shap, lightgbm, etc.)
- Schedule Week 13 checkpoint meeting with sponsor; identify backup reviewer

### Minimum Viable Data Gate
To proceed to Phase 1, you need confirmed read access to at least: (a) daily firm-level or desk-level VaR with component breakdown by asset class, and (b) at least one of scenario P&L, factor-VaR decomposition, or VaR utilization. If none of these are pullable, reassess project direction before investing in infrastructure.

### Why This Phase Matters
Risk cube entitlements are desk-scoped. Publication or external pitch requires desk sign-off. Getting explicit alignment early avoids building on data you can't use or results you can't present.

---

## Phase 1: Shared Infrastructure (Weeks 3-5)

### Goal
Build the validation and backtesting layer that both Project 1 and Project 2 will use. This is the ~25% infrastructure investment that separates credible work from "intern ran a GBM."

### 1.1 Data Pipeline
- Slang (GS's proprietary scripting language for SecDB) / Python bridge to pull risk cube time series into clean tabular format
- Daily frequency for risk-system outputs; intraday capability for Greeks (Project 2)
- **Point-in-time discipline:** every feature stamped with when it was *known*, not when it *applied* — prevents lookahead bias
- **True out-of-sample holdout:** reserve the most recent 3-6 months of data at the start; do not touch until Phase 5 walk-forward test
- Use `gs-quant` patterns (`PricingContext`, `HistoricalPricingContext`, `Dataset`) as the API layer
- Versioned feature store so experiments are reproducible

### 1.2 Label Construction
- **Triple-barrier labeling** (Lopez de Prado AFML Ch. 3) with volatility-scaled thresholds
- Configurable per asset class — what counts as a "move" differs across rates, FX, equities, credit
- Meta-labeling scaffold (primary model for side, secondary for size) — build the interface now, use later
- Standard return labels (1d, 5d, 21d) as comparison targets

### 1.3 Validation Stack
- **Purged K-fold CV with embargo** — break temporal autocorrelation between train/test splits
- **Combinatorial Purged Cross-Validation (CPCV)** — produce a *distribution* of Sharpes from a single history
- **Deflated Sharpe Ratio** (Bailey-Lopez de Prado 2014) on every reported number — adjusts for selection bias, non-normality, sample length
- **Harvey-Liu Haircut Sharpe** — Bonferroni/Holm/BHY-FDR multiple-testing correction as cross-check
- **Ridge/elastic-net baseline on identical features** — if GBM doesn't beat this, you haven't learned anything (Kozak-Nagel-Santosh 2020)
- Experiment tracker logging every configuration tried (for honest DSR adjustment)

### 1.4 Backtesting Engine
- Transaction-cost-aware P&L with parameterized spread/slippage per asset class
- Reporting suite: IC, Sharpe, Sortino, hit rate, turnover, max drawdown
- P&L decomposed by regime (once regime model exists)
- SHAP integration for feature interpretation
- One-chart-per-claim artifact generation for presentations

### Why Shared
Every component works identically for Project 1 (risk-system features → cross-asset returns) and Project 2 (Greeks features → intraday momentum). Built once, used by both.

### Smoke Test
Before moving to Phase 2, validate the infrastructure on a toy problem — e.g., run purged CV + DSR on a known factor (momentum or value on public equity data via `gs-quant`) to confirm the validation stack produces sensible numbers. A broken purged-CV implementation discovered in Week 9 would be costly.

### Tooling
- `mlfinlab` (Hudson & Thames) for triple-barrier, purged CV, CPCV — double-check implementations against bugs
- `alphalens` for factor evaluation (IC, quantile returns, turnover)
- `pyfolio` for tear-sheets
- `shap` for interpretation
- MLflow or Weights & Biases for experiment tracking
- **Note:** Confirm package availability in the GS compute environment during Phase 0. Bank IT may require approvals for external Python packages. Identify internal equivalents if needed.

---

## Phase 2: Project 1 Core — Risk as Alpha (Weeks 6-12)

### Goal
Build and test the core hypothesis: do internal risk-system outputs predict cross-asset returns, volatility, or drawdowns?

### 2.1 Feature Engineering (Weeks 6-8)

**Priority order:** Start with VaR utilization and factor concentration first — these have the strongest direct theoretical backing (Coval-Stafford fire sales, He-Kelly-Manela crowding). If these show signal, expand to the remaining families. If they don't, the others are unlikely to either.

Extract daily time series from risk cubes, organized into signal families:

| Signal Family | Features | Theoretical Proxy |
|---|---|---|
| **VaR dynamics** | Firm-level delta VaR, component VaR by asset class, VaR rate-of-change | Aggregate dealer risk appetite |
| **Factor concentration** | Factor-VaR Herfindahl index, top-3 factor share | Crowding indicator — low dispersion = hidden concentration |
| **Scenario P&L** | Stress-scenario P&L rank and dispersion, worst-case scenario identity | Tail risk awareness, directional exposure |
| **VaR utilization** | VaR usage as % of limit, rate of change of utilization | Forced-deleveraging pressure (Coval-Stafford fire sales) |
| **Cross-asset flow** | Component VaR shifts between asset classes over time | Capital rotation, balance-sheet reallocation |

Each feature family is tested independently before combining, to avoid confounding.

### 2.2 Prediction Targets (Weeks 8-10, overlapping with late feature engineering)

Start broad, narrow based on evidence:

1. **VIX innovations** — Adrian-Shin (2010) shows dealer repos forecast this; cleanest single target
2. **Drawdowns in the most-concentrated asset class** — if factor concentration is high in rates, do rates draw down next?
3. **Cross-asset momentum reversals** — does VaR utilization spike predict mean-reversion in crowded factors?
4. **Realized volatility across asset classes** — simpler target than returns, higher signal-to-noise ratio

### 2.3 Modeling (Weeks 9-12, overlapping — modeling begins on early features while remaining families are finalized)

1. **Ridge baseline first** on all features — establish the linear benchmark
2. **LightGBM on identical features** — measure marginal lift over ridge
3. **Feature importance** via SHAP + MDI/MDA stability across CV folds
4. **Confound check:** if any signal family dominates, test it standalone to confirm it's not just correlated with a known public factor (VIX level, credit spread, term slope)
5. **Panel structure** with asset-class fixed effects for cross-asset tests

### Key Risk: Sample Size
Firm-level VaR is one observation per day. With 5 years of history: ~1,250 rows. Bailey-Borwein-Lopez de Prado (2014) show ~45 independent trials exhaust a Sharpe of 1.0 on 5 years of data. Discipline required:
- Track every experiment for honest DSR adjustment
- Prefer fewer, theory-motivated features over data-mining
- Panel structure (multiple asset classes × time) increases effective sample size

---

## Phase 3: Checkpoint & Decision (Week 13)

### Goal
Data-driven go/no-go assessment.

### Continue Deepening Project 1 If:
- At least one signal family produces IC significantly above zero after purged CV
- GBM beats ridge baseline (ML is adding nonlinear signal, not just overfitting)
- DSR-adjusted Sharpe remains positive
- Feature importance is stable across CV folds (MDA doesn't flip sign)

### Pivot to Project 2 (Book-Gamma) If:
- All signal families are flat or unstable
- GBM doesn't beat ridge (features are linear or just noise)
- DSR kills the Sharpe — trial budget exhausted

### Hybrid Path If:
- One or two signal families work, others don't — keep the working Project 1 features as a base feature set, then add Project 2's Greeks-based features (dealer gamma, vanna, charm) as *additional inputs* into the same LightGBM model. This is a combined model, not an ensemble of two separate models. Weeks 14-17 would split roughly: 2 weeks adding Greeks features, 2 weeks on regime overlay and capacity analysis.

### Deliverable
Short internal memo (1-2 pages) documenting what worked, what didn't, and the decision rationale. This becomes part of the final write-up regardless — documented negative results are valuable.

---

## Phase 4A: Deepen Project 1 (Weeks 14-17)

*Taken if checkpoint passes.*

### 4A.1 Regime Overlay (Weeks 14-15)
- Fit GMM on macro features (VIX, credit spread, term slope, USD, realized correlation) following the Two Sigma regime-modeling template (Two Sigma, "A Machine Learning Approach to Regime Modeling," twosigma.com) — 3-4 regimes (Crisis, Steady State, Inflation, Walking on Ice)
- Decompose signal performance by regime
- If regime-conditional: this is a finding worth reporting, not a failure
- Asness et al. (2017) "Contrarian Factor Timing" caveat: timing net of existing exposures often subtracts value — document honestly
- Optional: ADWIN on prediction errors as concept-drift trigger for retraining

### 4A.2 Cross-Asset Panel Extension (Weeks 15-16)
- Move from firm-level aggregates to asset-class-level risk outputs
- Test within-class prediction (rates component VaR → rates returns) vs. cross-prediction (rates VaR → equity drawdowns)
- Panel regression with asset-class fixed effects, clustered standard errors by time
- This is the He-Kelly-Manela (2017) "single pricing kernel across asset classes" test with real data

### 4A.3 Capacity & Transaction Cost Sensitivity (Week 17)
- Signal degradation as position size increases
- Turnover analysis — daily-flipping signals may be eaten by transaction costs
- Capacity estimates per asset class
- This is what the trading floor asks about first

---

## Phase 4B: Pivot to Book-Gamma Intraday Momentum (Weeks 14-17)

*Taken if checkpoint fails.*

### 4B.1 Feature Engineering (Weeks 14-15)
- Daily aggregate dealer gamma, vega, vanna, charm across rates futures, G10 FX, credit indices
- SecDB advantage: real book-level sign (public GEX assumes dealer side and is ~30% wrong)
- Gamma-flip level as regime boundary, distance-to-flip as continuous feature
- Vanna exposure for FOMC/CPI-day response, charm for end-of-day drift

### 4B.2 Signal Construction (Weeks 15-16)
- Test whether aggregate net gamma sign predicts last-30-minute intraday momentum vs. mean-reversion per instrument class (Baltussen-Da-Lammers-Martens 2021)
- GBM + ridge on Greeks features, panel with asset fixed effects
- Cross-instrument linkage: does the signal in rates futures predict anything in FX?

### 4B.3 Validation (Weeks 16-17)
- Same validation stack from Phase 1
- Muravyev-Pearson-Pollet (2022) caveat: control for short interest and borrow cost if touching equities
- Compare against published Baltussen et al. result — does real book data improve or just confirm?

---

## Phase 5: Consolidation & Presentation (Weeks 18-20)

### 5.1 Final Robustness (Week 18)
- Walk-forward out-of-sample test on most recent 3-6 months held out entirely from development
- Stability check: retrain on rolling windows, confirm feature importance doesn't rotate
- Full DSR and Haircut Sharpe on final reported numbers
- If hybrid path: test combined model vs. each component standalone

### 5.2 Documentation (Weeks 18-19)

Research report structured for the desk:

1. **Hypothesis** — one paragraph: what theory predicts, what you tested
2. **Data** — what was pulled, time range, point-in-time discipline
3. **Methodology** — validation framework and why it's rigorous
4. **Results** — IC, Sharpe, Sortino, hit rate, turnover, max drawdown, P&L by regime. One chart per claim. Ridge baseline alongside GBM on every chart.
5. **What didn't work** — documented negative results (builds credibility)
6. **Capacity and transaction-cost sensitivity**
7. **Next steps** — what a full-time quant could do with 6-12 more months

SHAP waterfall plots for top predictions. Always include ridge-vs-GBM comparison.

### 5.3 Presentation (Week 20)

- Frame as causal hypothesis testing: "theory X predicts Y, we tested with proprietary data"
- Lead with IC and Sharpe, not model accuracy
- One slide per claim, one chart per slide
- Prepare for desk questions: capacity, turnover, transaction-cost survival, crisis behavior
- Have ridge-vs-GBM ready for "why not just a linear model?"

---

## Timeline Summary

| Weeks | Phase | Key Deliverable |
|---|---|---|
| 1-2 | Pitch & Alignment | Sponsor buy-in, data access confirmed |
| 3-5 | Shared Infrastructure | Validation stack, data pipeline, backtester |
| 6-12 | Project 1 Core | Risk-as-alpha tested across 5 feature families |
| 13 | Checkpoint | Go/pivot memo with documented evidence |
| 14-17 | 4A (deepen) or 4B (pivot) | Regime overlay + cross-asset panel OR book-gamma signal |
| 18-20 | Consolidation | Research report, walk-forward OOS, final presentation |

---

## Key Literature

### Essential (read first)
- Lopez de Prado, *AFML* (2018) — validation bible: triple-barrier, purged CV, CPCV, meta-labeling
- Gu, Kelly, Xiu (2020 RFS) — canonical ML horse-race, 60yr US equity panel
- Kelly, Xiu (2023 NBER WP 31502) — most comprehensive current ML-finance survey
- Bailey, Lopez de Prado (2014) — Deflated Sharpe Ratio
- Harvey, Liu (2015) — Haircut Sharpe methodology

### Project 1 Foundations
- He, Krishnamurthy (2013 AER) — intermediary asset pricing theory
- Adrian, Etula, Muir (2014 JF) — single-factor intermediary-leverage SDF, R²=77%
- He, Kelly, Manela (2017 JFE) — single kernel across equity/options/CDS/bonds/FX/commodities
- Adrian, Shin (2010 JFI) — dealer repos forecast VIX innovations
- Adrian, Brunnermeier (2016 AER) — CoVaR as systemic-risk signal
- Coval, Stafford (2007 JFE) — forced selling predicts 5-day reversals

### Project 2 Foundations (if pivot)
- Baltussen, Da, Lammers, Martens (2021 JFE) — dealer gamma determines intraday momentum
- Barbon, Buraschi (2021) — "Gamma Fragility," gamma imbalance × illiquidity
- Ni, Pearson, Poteshman (2005/2021) — delta-rehedging and pinning at expiry

### Validation & Anti-Overfitting
- Bailey, Borwein, Lopez de Prado, Zhu (2014) — Probability of Backtest Overfitting
- Harvey, Liu, Zhu (2016 RFS) — t>3 hurdle for new factors
- Kozak, Nagel, Santosh (2020 JFE) — ridge on PCs matches nonlinear ML
- Asness et al. (2017) — "Contrarian Factor Timing is Deceptively Difficult"

### Caveats
- Muravyev, Pearson, Pollet (2022) — IVS and skew partly proxy for borrow fees; control for short interest
- Published signals decay 30-50% post-publication (McLean-Pontiff 2016)

---

## Risk Register

| Risk | Mitigation |
|---|---|
| Signal doesn't exist in risk-system outputs | Week 13 checkpoint; Project 2 fallback |
| Sample size too small for ML | Panel structure across asset classes; prefer theory-motivated features over mining |
| Overfitting / data snooping | DSR on every number; experiment tracking; ridge baseline; purged CV |
| Entitlements block key data | Phase 0 audit before building anything |
| Desk doesn't care about the framing | Lead with practical (capacity, cost, drawdown), ground in theory for credibility |
| Feature importance unstable | MDA across folds as stability check; drop unstable features |
| Transaction costs eat the signal | Cost-aware backtesting from day 1; turnover as a first-class metric |
| Risk-model methodology changes in lookback period | Interview risk team about VaR model changes (historical sim → Monte Carlo, window-length shifts) — structural breaks in features could produce spurious signals |
| Compliance review delays final output | Start compliance review process in Week 16, not Week 20; identify early what constraints apply to internal-only vs. broader presentation |
| Sponsor unavailability at checkpoint | Identify backup reviewer during Phase 0; schedule Week 13 checkpoint meeting in advance |
| Package/compute restrictions in bank environment | Audit available Python packages and compute environment in Phase 0; identify internal equivalents for any blocked external libraries |
