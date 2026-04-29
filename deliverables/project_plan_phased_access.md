# Risk as Alpha: ML Signal Discovery from Dealer Constraint Proxies

## A Phased Approach: Public Data Proof of Concept, then Proprietary Validation

**Author:** Ryan Vincent
**Date:** April 2026
**Duration:** 20 weeks (~5 months)
**Desk:** Cross-Asset (XA)

---

## 1. Project Overview

Intermediary asset pricing theory proves that dealer balance-sheet constraints drive risk premia across asset classes. Every external test of this theory uses low-frequency, lagged public data. The results are strong (cross-sectional R-squared of 77% from a single dealer-leverage factor), but the data has always been the bottleneck.

This project proceeds in two stages:

**Stage 1 (Weeks 1-13): Proof of concept with public data.** Build the full methodology and test it using the best available public proxies for dealer constraints (NY Fed primary dealer statistics, He-Kelly-Manela capital ratio, dealer CDS spreads, market-implied risk measures). This validates the approach, produces baseline results, and requires no proprietary data access.

**Stage 2 (Weeks 14-20): Proprietary validation with SecDB data (if access approved).** Rerun the identical methodology using daily risk cube outputs from SecDB (VaR, component VaR, factor-VaR, scenario P&L, VaR utilization). Compare directly against the Stage 1 baseline. The comparison itself is the key deliverable: it quantifies exactly what proprietary daily data adds over public quarterly data.

If SecDB access is not approved, Stage 2 pivots to deepening the public-data analysis (regime decomposition, cross-asset panel extension, capacity analysis) or to Project 2 (book-gamma intraday momentum using SecDB Greeks, which may have different access requirements).

The methodology is fully reproducible: someone at another bank could follow the same steps with their own internal risk data. The public-data baseline ensures the approach works independently of any proprietary system.

---

## 2. Theoretical Foundation

The core thesis rests on a well-established body of academic work. The logic runs in four steps:

**Step 1: Dealers are the marginal investors in most markets.**
Classical asset pricing assumes a representative household whose consumption drives risk premia. This fails empirically (the equity premium puzzle). The intermediary approach replaces the household with the financial intermediary: in derivatives, credit, FX, and fixed income, broker-dealers hold the inventory, provide liquidity, and absorb order-flow imbalances. Their constraints, not household preferences, determine the pricing kernel.

**Step 2: When dealer constraints bind, risk premia spike.**
He and Krishnamurthy (2013, AER) show that risk premia are a nonlinear function of the intermediary's capital ratio. When capital is ample, risk premia are low and stable. When the constraint boundary approaches, risk premia spike sharply. The same market shock produces radically different risk-premium responses depending on how constrained the dealer is at the time.

**Step 3: This is empirically verified across multiple asset classes.**
- Adrian, Etula, and Muir (2014, JF) show that a single broker-dealer leverage factor prices 41 equity, momentum, and bond portfolios with a cross-sectional R-squared of 77%.
- He, Kelly, and Manela (2017, JFE) extend this across seven asset classes (equities, government and corporate bonds, sovereign bonds, options, CDS, commodities, and FX) using a single primary-dealer capital ratio. The capital risk premium is approximately 9% per year.
- Adrian and Shin (2010, JFI) demonstrate that growth in dealer repo positions forecasts VIX innovations, raising the VIX forecasting R-squared from 8.9% to 11.6% at weekly frequency.
- Coval and Stafford (2007, JFE) show that stocks subject to flow-driven forced selling experience cumulative abnormal returns of approximately -10%, with partial reversals over the following year.

**Step 4: Every academic test used low-frequency, lagged data. Better data should improve the signal.**
The theory is proven. The question is whether higher-frequency, more granular data (daily from SecDB vs. quarterly from the Fed) produces a stronger, more timely signal. Stage 1 establishes the public-data baseline. Stage 2 answers the question.

---

## 3. The Two-Stage Data Strategy

### Stage 1: Public Data Proxies

| Feature Family | Public Proxy | Source | Frequency |
|---|---|---|---|
| **VaR Utilization** (dealer constraint level) | He-Kelly-Manela intermediary capital ratio | Manela's website / CRSP+Compustat | Quarterly |
| | Dealer CDS spreads (GS, JPM, MS average) | Bloomberg / Markit | Daily |
| | Primary dealer leverage from bank holding company filings | FR Y-9C / Fed | Quarterly |
| **Factor Concentration** (crowding/diversification) | Construct factor model from public returns; compute HHI on factor risk contributions | FRED, Bloomberg, Yahoo Finance | Daily (constructed) |
| | Cross-asset realized correlation matrix | Public returns data | Daily (constructed) |
| **VaR Dynamics** (balance-sheet expansion/contraction) | NY Fed primary dealer net positions by asset class | NY Fed | Weekly |
| | MOVE index (bond vol), VIX (equity vol) | ICE/CBOE, via FRED | Daily |
| | Realized volatility across asset classes | Public returns data | Daily (constructed) |
| **Scenario P&L** (stress vulnerability) | Construct scenario analysis using public factor exposures and defined stress moves | Self-constructed | Daily (constructed) |
| **Cross-Asset Flow** (risk migration between asset classes) | CFTC Commitments of Traders (dealer/asset manager positions) | CFTC | Weekly |
| | NY Fed primary dealer positions by asset class | NY Fed | Weekly |

**Controls (same in both stages):** VIX level/change, credit spread (IG/HY OAS), term slope (10y-2y), S&P 500 trailing returns, dollar index (DXY).

**Targets (same in both stages):** VIX innovations, asset-class drawdowns, realized volatility, cross-asset momentum reversals. All are publicly available.

### Stage 2: SecDB Risk Cube Data (if access approved)

| Feature Family | SecDB Data | Frequency | Advantage over Public |
|---|---|---|---|
| **VaR Utilization** | Actual VaR / VaR limit at desk level | Daily | Direct constraint measure vs. quarterly proxy; 60x more observations |
| **Factor Concentration** | Factor-VaR decomposition with exact HHI | Daily | Exact risk attribution vs. estimated factor model |
| **VaR Dynamics** | Total VaR, component VaR by asset class | Daily | Actual dealer risk state vs. aggregate position data |
| **Scenario P&L** | Portfolio P&L under standard stress scenarios | Daily | Full repricing vs. linear factor approximation |
| **Cross-Asset Flow** | Component VaR share shifts between asset classes | Daily | Exact risk rotation vs. weekly position snapshots |

**The comparison between Stage 1 and Stage 2 results is itself the primary finding.** If SecDB data materially outperforms public proxies, that quantifies the value of proprietary risk data for alpha generation. If it doesn't, that's equally valuable to know.

---

## 4. Feature Families

Five signal families, each mapping to a specific theoretical prediction. In Stage 1, these are constructed from public data. In Stage 2, they are extracted directly from SecDB. The feature definitions are identical; only the data source changes.

### 4.1 Dealer Constraint Level (Priority)

**What it measures:** How constrained dealers are. In Stage 2, this is VaR utilization (VaR / limit). In Stage 1, we proxy with the He-Kelly-Manela capital ratio, dealer CDS spreads, and bank leverage.

**Theoretical basis:** He and Krishnamurthy (2013) predict that risk premia spike when the intermediary constraint binds. VaR utilization is the most direct measure of this constraint. Dealer CDS spreads reflect the market's view of dealer stress. The He-Kelly-Manela capital ratio captures the same economics at lower frequency.

**Stage 1 features:** HKM capital ratio level and innovation (quarterly, interpolated), dealer CDS spread composite (daily), CDS rate of change, CDS z-score.

**Stage 2 features:** VaR utilization level (%), 1/5/21-day rate of change, z-score relative to rolling 63-day window.

### 4.2 Risk Concentration (Priority)

**What it measures:** How concentrated dealer risk is across factors or asset classes. High concentration signals crowding and fire-sale vulnerability.

**Theoretical basis:** Coval and Stafford (2007) show that forced selling creates predictable price pressure. He, Kelly, and Manela (2017) show a single factor prices all asset classes; high concentration means the pricing kernel is exposed to a single point of failure.

**Stage 1 features:** HHI on factor risk contributions from a public factor model (rates, credit, equity, FX, commodities), cross-asset realized correlation, top-3 factor share.

**Stage 2 features:** HHI on factor-VaR shares (exact from SecDB decomposition), top-3 factor share, rolling HHI change.

### 4.3 Balance-Sheet Dynamics

**What it measures:** Whether dealers are expanding or contracting their risk-taking.

**Theoretical basis:** Adrian and Shin (2010) show that changes in dealer balance-sheet size forecast VIX. Rising risk-taking signals building vulnerability; contraction signals deleveraging.

**Stage 1 features:** Weekly change in NY Fed primary dealer net positions, MOVE/VIX rate of change, cross-asset realized volatility momentum.

**Stage 2 features:** Daily change in total VaR, component VaR by asset class, VaR momentum (5-day rolling).

### 4.4 Stress Vulnerability

**What it measures:** How the portfolio would perform under stress scenarios. Forward-looking, unlike backward-looking volatility measures.

**Stage 1 features:** Construct scenarios (rates +200bp, equities -25%, credit +150bp, FX USD +10%) and compute P&L impact using public factor exposures. Track worst-case scenario identity, dispersion, and flips.

**Stage 2 features:** Actual scenario P&L from SecDB risk engine. Same metrics (worst-case identity, dispersion, skewness, flip indicator).

### 4.5 Cross-Asset Risk Rotation

**What it measures:** How risk is migrating between asset classes, capturing dealer balance-sheet reallocation.

**Theoretical basis:** He, Kelly, and Manela (2017) show that a single intermediary factor prices all asset classes. Risk rotation from one asset class to another should predict relative performance.

**Stage 1 features:** CFTC positioning shifts by asset class (weekly), NY Fed primary dealer position changes by asset class (weekly), relative volatility shifts.

**Stage 2 features:** Component VaR share shifts between asset classes (daily), rolling cross-asset VaR correlation.

---

## 5. Prediction Targets

Same in both stages (all publicly available):

| Target | Motivation | Source |
|---|---|---|
| **VIX innovations** | Adrian and Shin (2010) show dealer repos forecast VIX changes; cleanest single target | CBOE via FRED |
| **Drawdowns in the most-concentrated asset class** | If factor concentration is high in rates, do rates draw down next? Direct Coval-Stafford prediction | Public index returns |
| **Cross-asset momentum reversals** | Does a dealer constraint spike predict mean-reversion in crowded factors? | Public index returns |
| **Realized volatility** | Simpler target than returns, higher signal-to-noise; broader applicability | Computed from public returns |

---

## 6. Validation Framework

Identical in both stages. This rigor is what makes the public-to-proprietary comparison valid.

**Ridge baseline on identical features:** Every model is benchmarked against ridge regression. If LightGBM does not beat ridge, the ML is overfitting. Motivated by Kozak, Nagel, and Santosh (2020, JFE).

**Purged K-fold cross-validation with embargo:** Prevents temporal information leakage. Follows Lopez de Prado (2018, Ch. 7).

**Combinatorial Purged Cross-Validation (CPCV):** Produces a distribution of Sharpe ratios from a single history, giving confidence intervals rather than point estimates.

**Deflated Sharpe Ratio (DSR):** Adjusts for the number of trials attempted, non-normality, and sample length (Bailey and Lopez de Prado, 2014). Every experiment is logged; the total trial count feeds the DSR.

**Harvey-Liu Haircut Sharpe:** Complementary multiple-testing correction (Bonferroni/Holm/BHY-FDR).

**Confound checks against public factors:** Features tested with and without public controls (VIX, credit spread, term slope, equity returns, dollar index). Features that vanish after adding controls are flagged as redundant.

**Transaction-cost-aware backtesting:** All backtests include parameterized costs from day one. Breakeven cost level reported alongside gross metrics.

---

## 7. Project Phases and Timeline

### Phase 0: Pitch, Alignment, and Data Sourcing (Weeks 1-2)

**Goal:** Get sponsor buy-in on the two-stage approach and source all public data.

**Deliverables:**
- 1-2 page pitch document for sponsor explaining the two-stage strategy
- Public data sourced and loaded: NY Fed primary dealer statistics, HKM capital ratio, dealer CDS spreads, CFTC Commitments of Traders, VIX/MOVE, credit spreads, yields, equity indices
- Environment and package audit (Python packages, compute constraints)
- Holdout reservation (most recent 3-6 months of public data set aside)
- Experiment tracking log initialized
- If possible: begin SecDB access request in parallel (the approval process may take weeks)

### Phase 1: Shared Infrastructure (Weeks 3-5)

**Goal:** Build the validation and backtesting layer. This infrastructure is data-source agnostic: it works identically on public data (Stage 1) and SecDB data (Stage 2).

**Components:**
- **Data pipeline** with point-in-time stamping and holdout enforcement. Modular source adapters for public data and SecDB.
- **Label construction:** triple-barrier labeling (Lopez de Prado, AFML Ch. 3), meta-labeling scaffold, standard return labels (1d, 5d, 21d)
- **Validation stack:** purged K-fold CV with embargo, CPCV, Deflated Sharpe Ratio, Harvey-Liu Haircut Sharpe, ridge baseline
- **Backtesting engine:** transaction-cost-aware P&L, full reporting suite (IC, Sharpe, Sortino, hit rate, turnover, max drawdown), SHAP integration
- **Experiment tracker:** logs every configuration tried for honest DSR adjustment
- **Smoke test:** validate the full stack on a synthetic toy problem before proceeding

### Phase 2: Stage 1 Core, Public Data (Weeks 6-12)

**Goal:** Build and test all five feature families using public proxies against all four targets.

**Approach:**
1. **Priority features first (Weeks 6-8):** Dealer constraint level (HKM ratio, CDS spreads) and risk concentration (constructed HHI), tested against all targets.
2. **Remaining features (Weeks 8-10):** Balance-sheet dynamics (NY Fed positions, vol measures), stress vulnerability (constructed scenario P&L), cross-asset flow (CFTC positions).
3. **Modeling (Weeks 9-12):** Ridge baseline first; LightGBM on identical features; SHAP and MDA stability; confound checks; panel structure with asset-class fixed effects.

**Key question to answer by Week 12:** Do public proxies for dealer constraints predict returns/volatility/drawdowns using our methodology? What's the IC, Sharpe, and DSR-adjusted Sharpe?

### Phase 3: Checkpoint and Access Decision (Week 13)

**Goal:** Present Stage 1 results and make the case for SecDB access.

**If Stage 1 shows signal (IC > 0, GBM beats ridge, DSR positive):**
- Present results to sponsor: "The public-data methodology works. Here are the baseline numbers. The theory predicts that daily proprietary data should improve these results. Granting SecDB access lets us quantify exactly how much."
- Request SecDB access for Stage 2.
- If access already approved: proceed to Stage 2 immediately.

**If Stage 1 shows no signal:**
- Document negative results honestly.
- Pivot options: (a) investigate why (data frequency too low? wrong proxies?), (b) pivot to Project 2 (book-gamma with SecDB Greeks, which may have different access requirements), (c) deepen the public-data analysis with regime decomposition and cross-asset panel work.

**Deliverable:** 1-2 page checkpoint memo with Stage 1 results, comparison to published academic benchmarks, and recommendation for Stage 2.

### Phase 4: Stage 2, SecDB Validation (Weeks 14-17)

*If SecDB access is granted.*

**4A: SecDB Feature Engineering (Weeks 14-15)**
- Extract the same five feature families from SecDB risk cube outputs
- Map each public proxy to its SecDB equivalent (e.g., HKM capital ratio maps to VaR utilization; constructed HHI maps to factor-VaR HHI)
- Run identical pipeline, validation, and backtesting code on SecDB data

**4B: Head-to-Head Comparison (Weeks 15-16)**
- Compare IC, Sharpe, DSR for every feature-target combination: public data vs. SecDB data
- Quantify the incremental value of proprietary data
- Test whether daily frequency alone explains the improvement (by downsampling SecDB data to weekly/monthly)
- SHAP comparison: do the same features matter, or does SecDB reveal different drivers?

**4C: Extensions (Weeks 16-17)**
- Regime overlay (GMM on macro features; decompose signal by regime)
- Cross-asset panel (within-class vs. cross-class prediction)
- Capacity and transaction cost sensitivity
- Initiate compliance review

*If SecDB access is not granted, Weeks 14-17 are spent on:*
- Regime decomposition on public-data results
- Cross-asset panel extension
- Deeper investigation of which public proxies carry the most signal
- Capacity analysis
- Or: pivot to Project 2 (book-gamma) if SecDB Greeks access is available

### Phase 5: Consolidation and Presentation (Weeks 18-20)

- **Walk-forward out-of-sample test (Week 18):** Unfreeze the reserved holdout. One-shot test on both public and (if available) SecDB models.
- **Final DSR and Haircut Sharpe** on all reported numbers.
- **Research report (Weeks 18-19):** Hypothesis, data, methodology, Stage 1 results, Stage 2 results (if applicable), the public-vs-proprietary comparison, documented negatives, capacity, next steps.
- **Presentation (Week 20):** Framed as causal hypothesis testing. If both stages completed: "public data gives X, proprietary data gives Y, the incremental value of internal risk data is Z." If only Stage 1: "here's what the methodology finds on public data, and here's the case for why internal data should do better."

---

## 8. Timeline Summary

| Weeks | Phase | Key Deliverable |
|---|---|---|
| 1-2 | Pitch and data sourcing | Sponsor buy-in, public data loaded, SecDB access request initiated |
| 3-5 | Shared infrastructure | Data-source-agnostic pipeline, validation stack, backtester |
| 6-12 | Stage 1: public data | All feature families tested on public proxies; baseline results |
| 13 | Checkpoint | Stage 1 memo; case for SecDB access |
| 14-17 | Stage 2: SecDB (if approved) | Head-to-head comparison; regime overlay; capacity analysis |
| 14-17 | Alternative: deepen Stage 1 | Regime analysis, cross-asset panel, or Project 2 pivot |
| 18-20 | Consolidation | Walk-forward OOS, research report, presentation |

---

## 9. Risk Register

| Risk | Mitigation |
|---|---|
| Public proxies too noisy to detect signal | Expected; Stage 1 is the baseline, not the final result. Even null results on public data are informative (matches published work limitations). |
| SecDB access never granted | Stage 1 alone produces a valid internship deliverable. Alternative paths available: deepen public analysis, pivot to Project 2 with Greeks. |
| Stage 1 shows signal but Stage 2 doesn't improve it | This is a genuine finding worth reporting: proprietary daily data doesn't add value over public quarterly data for this application. |
| Sample size too small for ML | Panel structure; theory-motivated features; DSR adjustment. |
| Overfitting / data snooping | DSR on every number; experiment tracking; ridge baseline; purged CV. |
| Feature importance unstable across folds | MDA stability check; drop unstable features. |
| Transaction costs eat the signal | Cost-aware backtesting from day 1. |
| Risk-model methodology changes (Stage 2) | Interview risk team; document change dates; include as control variables. |
| Compliance review delays | Initiate at Week 16, not Week 20. |

---

## 10. Why This Two-Stage Approach Benefits Everyone

**For the supervisor:**
- No upfront commitment to proprietary data access. Stage 1 runs entirely on public data.
- The methodology is reproducible and compliance-safe from day one.
- The decision to grant SecDB access is informed by concrete results, not a speculative pitch.

**For the desk:**
- If Stage 2 happens, the head-to-head comparison directly quantifies the value of internal risk data for alpha generation. This is useful beyond the internship.
- If Stage 2 doesn't happen, the desk still gets a rigorously validated public-data analysis and a portable methodology.

**For the project:**
- Stage 1 is a forcing function: it proves the methodology works before adding data complexity.
- The public-data baseline makes any Stage 2 improvement credible (it's a controlled comparison, not a standalone claim).
- Every outcome is a finding. Signal in public data: methodology works. No signal in public data but signal in SecDB: proprietary data is the edge. No signal in either: the theory doesn't translate to tradeable signals at this sample size.

---

## 11. Deliverables Summary

| Week | Deliverable | Format |
|---|---|---|
| 2 | Pitch document (two-stage approach) | 1-2 page memo |
| 2 | Public data sourced and loaded | Notebook with summary statistics |
| 5 | Validated infrastructure | Code: data pipeline, validation stack, backtester, tracker |
| 5 | Smoke test | Notebook confirming stack on synthetic data |
| 12 | Stage 1 signal test results | Notebooks with IC, Sharpe, SHAP for all public-proxy features |
| 13 | Checkpoint memo with case for SecDB access | 1-2 page memo with baseline results |
| 17 | Stage 2 results (if approved) or deepened Stage 1 | Head-to-head comparison or extended analysis |
| 19 | Research report | Full desk-ready report with charts |
| 20 | Presentation | Slides with Q&A preparation |

---

## 12. Key References

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
