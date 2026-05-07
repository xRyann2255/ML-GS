# Vol Project Reference Guide -- Design Spec

**Date:** 2026-05-07
**Status:** Draft
**Location:** `guides/vol-project-ref/`

---

## Purpose

A self-contained, plain-English reference for the realized volatility forecasting project. Written before any code exists. Covers every piece of the project -- features, models, pipeline, evaluation -- in a way that is directly applicable to implementation.

**Not a textbook.** No derivations, no proofs, no "here's why this is theoretically interesting." Every sentence passes the test: *does this help me build or defend a specific piece of the project?*

## Constraints

- **Audience:** Self (pre-implementation personal reference)
- **Length:** ~50-60 pages
- **Voice:** Direct, factual, forward-looking ("we use X because Y")
- **Self-contained:** No cross-references to the vol learning guide required
- **Primary source:** `notes/features/optimal-feature-set.md`
- **LaTeX class:** `report` [11pt, a4paper], reuse vol learning guide preamble and tcolorbox environments
- **Diagrams:** Encouraged throughout -- pipeline flows, architecture diagrams, decision diagrams
- **Implementation pitfalls:** Surfaced as `warning` boxes within relevant chapters, not buried at the end

## Writing Rules

1. State decisions, not arguments. "We use LightGBM" not "Here's why trees beat neural networks."
2. Every feature gets: name, what it is (one sentence), what it does for our forecast, which data source it uses, which horizon it matters for.
3. No general finance/statistics background. Assume the reader understands returns, variance, regression, gradient boosting, LSTMs.
4. Tables over prose for reference information.
5. Diagrams for any data flow or architecture.
6. `warning` boxes for pitfalls that could waste weeks (lookahead bias, QLIKE vs MSE, log-RV space, timestamp alignment).
7. `keyidea` boxes for the single most important takeaway per section.
8. `projectconnection` boxes are unnecessary -- everything is already project-specific. Do not use.
9. No em dashes.

---

## Structure

### Part I: The Project

#### Chapter 1: What We're Forecasting

~3 pages. Sets up the entire document.

- **Target:** log RV_{t+h} for h = 1 day, 5 days, 22 days
- **RV definition:** One sentence. Sum of squared intraday returns over a day.
- **Universe:** 30 mega-cap equities + 4 ETFs + E-mini S&P 500 (34 symbols, 11.3 years)
- **Success criteria:** 30-80 bps QLIKE improvement over HARQ baselines, plus economic-value test
- **High-level pipeline diagram:** data -> feature engineering -> models -> forecast -> evaluation
- **The thesis:** "The feature set you choose matters more than the model you choose"

Does NOT include:
- Why vol forecasting matters to GS (the reader knows)
- History of volatility modeling
- General motivation

#### Chapter 2: Our Data

~4 pages. Pure reference.

| Data Source | What It Enables | Key Constraint |
|---|---|---|
| Tick-level RV (34 symbols, 11.3y) | RV at any frequency, RQ, jumps, semivariances | -- |
| Daily OHLCV (34 symbols + VIX) | HAR baselines, ML training | No intraday structure |
| E-mini L2 depth (~4M ticks/day) | OBI, depth ratio, VPIN, LSTM input | E-mini ONLY, not equities |
| SPX IV surface (Marquee ERDVOL) | VRP, skew, term structure, butterfly | SPX only, no single-name IV |
| VIX term structure | Regime detection, contango/backwardation | -- |
| Cross-asset (treasuries, FX, commodities) | Spillover features, macro regime | Daily for some, tick for others |

- **GS vs. public data table:** What we have that academics don't (tick-level for 34 symbols, full IV surface, L2 depth, synchronized cross-asset)
- **Constraints that shape decisions:** L2 is E-mini only (so microstructure depth features only for the index). IV surface is SPX only (so options features are market-wide regime signals, not stock-specific). These constraints directly determine which features apply to which assets.

---

### Part II: The Feature Set

#### Chapter 3: HAR Core and Measurement Quality (Layer 0)

~5 pages. The non-negotiable foundation.

**Features (table):**

| Feature | What It Is | What It Does |
|---|---|---|
| log RV daily | log(RV_t) | Strongest single predictor; log transform gaussianizes |
| log RV weekly | log(mean of last 5 days RV) | Medium-memory component |
| log RV monthly | log(mean of last 22 days RV) | Long-memory regime anchor |
| Realized Quarticity (RQ) | (n/3) * sum(r^4) | Measures how noisy today's RV estimate is |
| RQ interaction | sqrt(RQ) * RV_daily | Shrinks daily weight on noisy days; single most impactful HAR extension (5-15% QLIKE) |

- **Diagram:** The HARQ shrinkage mechanism. On a noisy day (high RQ), the model trusts weekly/monthly averages more. On a clean day (low RQ), it trusts the daily reading.
- **Baseline performance:** These 5 features alone explain 40-60% of next-day log-RV variation. HARQ with 5 features consistently beats ML models that use dozens of features without noise-awareness.
- **What to compute from our data:** RQ requires tick-level returns (we have them for all 34 symbols).

`warning` box: Model in log-RV space, not raw RV. Raw RV is right-skewed with heavy tails; log-RV is approximately Gaussian. This affects loss functions, residual diagnostics, and model comparison.

`keyidea` box: RQ interaction is the single most important extension beyond baseline HAR. 5-15% QLIKE gain from one feature.

#### Chapter 4: Asymmetric Volatility (Layer 1)

~4 pages.

**Features (table):**

| Feature | What It Is | What It Does | Horizon |
|---|---|---|---|
| RS- daily | Sum of squared negative intraday returns | 2x predictive weight of RS+ | 1d |
| RS+ daily | Sum of squared positive intraday returns | Weaker but provides contrast | 1d |
| RS- weekly | 5-day average of RS- | Persistent downside memory | 1d-5d |
| Signed negative jumps (J-) | Large negative moves beyond threshold | 1-3% QLIKE beyond unsigned jumps | 1d-5d |
| Continuous variation (C) | max(BPV, 0) | Highly persistent (ACF ~0.6-0.7) | All |
| Jump variation (J) | max(RV - BPV, 0) | Nearly unpredictable (ACF ~0.0-0.1), signals regime breaks | Event |

- **The fact:** Negative returns increase future volatility more than positive returns. This is strongest for equity indices and E-mini; varies by sector for individual stocks.
- **Cumulative performance:** Layers 0+1 together = ~70% of achievable forecast accuracy with 11 features.
- **What to compute:** Semivariances and jumps from tick-level data at 5-min frequency. Jump threshold via Lee-Mykland test on our data.

#### Chapter 5: Options-Implied Features (Layer 2)

~5 pages. The forward-looking layer.

**Features (table):**

| Feature | What It Is | Horizon Impact |
|---|---|---|
| ATM IV (30-day) | 50-delta put/call average from Marquee | All horizons |
| Variance Risk Premium (VRP) | IV^2 - E[RV over next 30d] | 1w-1m (strongest) |
| 25-delta Risk Reversal | IV_25D_call - IV_25D_put | 1-5d |
| Term Structure Slope | IV_3m - IV_1m | 1w-1m |
| Butterfly (Wing Premium) | IV_25D_put + IV_25D_call - 2*ATM_IV | Crisis detection |
| VVIX | Implied vol of VIX options | 1-5d |
| VIX Term Structure | VIX_Futures_3m / VIX_Spot | Regime signal |
| IV-RV Gap | ATM_IV - sqrt(RV_22d * 252) | 1-5d |
| Event-Implied Vol | Extracted from surface around event dates | Pre-event |

- **The critical horizon dependence:** At 1-day, options add only 1-3% QLIKE. At 1w-1m, they add 5-10%. Options embed information about future events (FOMC, earnings, macro) that past RV cannot see.
- **Cumulative:** Layers 0-2 = ~85% of achievable accuracy with 20 features.
- **What to compute:** Full surface from Marquee ERDVOL_PERCENT_STANDARD. Can compute any surface-derived feature (arbitrary delta, tenor interpolation, curvature).
- **Constraint:** SPX surface only. For single-stock vol, options features are market-wide regime signals, not stock-specific predictors.

`keyidea` box: ML's genuine advantage over HAR grows with forecast horizon. At h=1, HAR ties ML. At h=5 and h=22, ML with options features gives 10-20% QLIKE improvement.

#### Chapter 6: Microstructure Features (Layer 3)

~5 pages. E-mini L2 territory.

**Features (table):**

| Feature | What It Is | Evidence |
|---|---|---|
| Price acceleration | Sum of (delta-log-return)^2 | Single most predictive micro feature (Optiver) |
| WAP log returns | Returns from volume-weighted avg price | Less bid-ask bounce contamination |
| Order Book Imbalance (OBI) | (bid_size - ask_size) / (bid_size + ask_size) at L1-L5 | Directional pressure signal |
| Depth Ratio | sum(bid depths) / sum(ask depths) | Structural imbalance beyond best quote |
| Market Urgency | spread * OBI | Wide spread + imbalanced book = imminent move |
| Bid-Ask Spread dynamics | Level, volatility, momentum of spread | Spread increasing is predictive |
| Signed volume flow | Volume * sign(trade direction) | Net buying/selling pressure |
| Sub-window RV ratio | RV_last_5min / RV_first_5min | Acceleration within window |
| VPIN | Volume-synced prob of informed trading | Flash crash leading indicator |

- **Engineering principle:** For each base quantity, compute {level, change, z-score}. Trees handle the redundancy via splits.
- **Data constraint:** L2 depth is E-mini only. For the 30 equities + 4 ETFs, only L1 features (price acceleration, WAP returns, spread dynamics).
- **Connection to LSTM:** This is the data that feeds the intraday deep learning module (Ch 10). Raw tick sequences are too rich for hand-engineered aggregations alone.

`warning` box: Lookahead bias. Microstructure features computed on the full day use information up to market close. Features for predicting RV_{t+1} must use only information available at time t. Timestamp alignment is critical.

#### Chapter 7: Cross-Asset Spillovers (Layer 4)

~4 pages.

**Features (table):**

| Feature | What It Is | Mechanism |
|---|---|---|
| Treasury slope change | Delta(10y - 2y yield) | Rate inversion precedes equity vol spikes by days |
| Credit spread momentum | Delta IG/HY spread or TY futures vol | Credit stress leads equity vol |
| FX vol (USD/JPY) | RV of USD/JPY | Yen carry unwind = risk-off = equity vol spike |
| Commodity vol (CL, GC) | RV of crude + gold | Oil = macro uncertainty; gold = flight-to-safety |
| DY Spillover Index | VAR(5) variance decomposition on 34-asset RV | Fraction of vol from cross-asset contagion |
| Sector-mean RV | Average RV across same-sector names | Filters idiosyncratic noise |
| VIX-equity corr regime | Rolling 20d corr(VIX changes, SPX returns) | Near -1 normally; breaks during regime shifts |
| Cross-asset RV rank | Each asset's RV percentile vs peers | Detects outlier dispersion regimes |

- **Impact:** 1-5% QLIKE improvement, concentrated in regime transitions (exactly when forecasts are most valuable and hardest to get right).
- **Graph-HAR:** Neighbor-weighted RV term captures how AAPL's vol tomorrow depends on MSFT's vol today. Weight matrix can be correlation-based (simple) or learned (GNN).
- **GS advantage:** Synchronized tick data across asset classes. Intraday lead-lag relationships invisible at daily frequency.

#### Chapter 8: Feature Composition and Selection

~6-7 pages. The synthesis chapter. Includes Layers 5-7 as a section, plus the composition/selection framework.

**Section: Calendar, Memory, and Sentiment (Layers 5-7)**

Calendar: FOMC indicator, NFP/CPI, options expiry, quarter-end, earnings proximity, event-implied vol, time-of-day, day-of-week. Trees pick these up naturally from dummy/relative-day encoding.

Memory: Fractionally differenced RV (d ~ 0.35-0.45, preserves long memory while stationary), rolling Hurst exponent (low H < 0.15 = rough/fast mean-reversion), vol-of-vol (instability of vol process), regime duration (days since last 2-sigma spike).

Sentiment: FinBERT news sentiment, negative news count. 1-3% QLIKE in crises only. Include if data pipeline effort is justified.

These layers are individually weak but collectively additive. They are the last 5% of achievable accuracy.

**Section: The Diminishing Returns Curve**

Diagram showing cumulative accuracy by layer:
- Layer 0 (5 features): ~55%
- + Layer 1 (11 features): ~70%
- + Layer 2 (20 features): ~85%
- + Layers 3-4 (40 features): ~95%
- + Layers 5-7 (80-120 features): 100%

**Section: Feature Priority by Forecast Horizon**

| Horizon | Dominant Features | Where ML Adds Value |
|---|---|---|
| Intraday (10min-1hr) | Microstructure (L3): price acceleration, OBI, spread | Trees with 600+ features |
| 1 day | HAR core (L0) + RQ + asymmetry (L1) | HARQ nearly optimal; ML adds ~5% |
| 1 week | Options (L2) + cross-asset (L4) eclipse micro | VRP + skew give 5-10% over pure RV |
| 1 month | VRP (L2) + macro regime (L4) + Hurst (L6) | Options have max informational advantage |

**Section: Feature Engineering Principles**

- For each base quantity, compute {level, change, z-score} systematically. This triples feature count and captures state, direction, and unusualness.
- Horizon-dependent feature selection: drop microstructure features at monthly horizon, drop calendar at intraday.
- Trees handle redundancy naturally via splits. Do not worry about multicollinearity.

`keyidea` box: "The feature set you choose matters more than the model you choose." Layers 0-2 get 85% of the way there with 20 features and a Ridge regression. The remaining 15% requires 60-100 more features and careful model architecture.

---

### Part III: Models

#### Chapter 9: LightGBM for Tabular Volatility

~4 pages.

- **Input:** ~80-120 engineered features from Layers 0-7
- **Reference config (from Optiver 91st place, well-documented):** lr=0.05, max_leaves=255, min_data_per_leaf=255, 10k estimators, 400 early stopping rounds, DART mode
- **Loss function:** Train with QLIKE, not MSE. Zhang et al. (2025) confirms this matters substantially. MSE is dominated by extreme vol days. Note: QLIKE is not a built-in LightGBM objective; requires implementing a custom objective and eval function.
- **Interpretability:** SHAP values for feature importance and interaction effects. Required for GS presentation and model defense.
- **Feature importance stability:** Single-model importance (gain, permutation, SHAP) is unstable across refits due to feature redundancy (VIX, VVIX, ATM IV, IV-RV spread are near-substitutes). This motivates the Rashomon analysis in Ch 12.

`warning` box: Choice of fitting scheme for HAR matters more than ML model choice (Wilms et al. 2024 "HARd to Beat"). A properly-fitted HAR baseline is essential before claiming ML improvement. Use OLS with Newey-West standard errors as the benchmark.

#### Chapter 10: LSTM for Intraday Sequences

~4 pages.

- **Input:** Full-day E-mini L2 tick sequences (5-min or 1-min return bars with LOB snapshots)
- **Why this specific component:** 4M ticks/day of E-mini is too rich for hand-engineered aggregations alone. Temporal order within the day matters (acceleration patterns, depth shifts). This is where DL genuinely adds value over trees.
- **Architecture:**
  1. Small LSTM or TCN on intraday E-mini sequences
  2. Input: 5-min return bars within each trading day, with LOB snapshot features
  3. Output: independent next-day RV forecast
  4. This forecast is blended with LightGBM's forecast at the prediction level (Ch 11)
  5. Alternative to test: extract last-layer hidden state as embedding and feed into LightGBM as additional features (feature-level stacking). Competition evidence favors prediction-level blending, but both should be compared on our data.
- **Diagram:** E-mini L2 ticks -> 5-min bars + LOB snapshots -> LSTM -> next-day RV forecast -> blend with LightGBM
- **Key difference from Optiver:** Optiver had 10-min windows (short sequences where hand-engineered aggregations captured most info). We have full-day tick sequences for next-day prediction -- much longer, richer sequences.

#### Chapter 11: The Ensemble

~3 pages.

- **Architecture diagram:** The complete system from optimal-feature-set.md
  - LightGBM branch: Layers 0-7 tabular features (~80-120 features) -> forecast
  - LSTM branch: E-mini L2 raw sequences -> embedding -> forecast
  - Blend: prediction-level weighted average of the two forecasts -> final sigma^2_{t+h}
- **Prediction-level blending, NOT feature-level stacking.** Optiver and AmEx competition evidence: blending model outputs beats feeding NN embeddings as tree inputs.
- **Why two branches:** LightGBM dominates tabular features. LSTM adds value on sequential microstructure data. Each model gets the data format it handles best.

#### Chapter 12: Interpretable Trees and Rashomon Analysis

~4 pages. The novel contribution.

- **What to build:** Optimal decision trees (`STreeDPiecewiseLinearRegressor`, depth 4-5, elastic-net leaves, 8-32 leaves) trained on the same feature set as LightGBM
- **Expected accuracy:** ~2-5% higher MSE than tuned LightGBM, but comfortably beats HAR (~10% better). A single inspectable tree.
- **Rashomon analysis pipeline:**
  1. TreeFARMS/RESPLIT to construct the set of all near-optimal trees (within epsilon=2% MSE of optimum)
  2. RID (Donnelly et al. 2023) for stable feature importance across the Rashomon set
  3. Variable Importance Clouds to identify: essential features (in every near-optimal tree), interchangeable features (substitutable), useless features (in no near-optimal tree)
  4. Rolling-window Rashomon sets intersected across regimes for regime-stable model selection
- **What this tells us:**
  - Which features are genuinely important vs. accidentally selected by a single greedy tree
  - Which features are substitutes (VIX, VVIX, ATM IV, IV-RV spread are near-substitutes -- Rashomon analysis reveals this)
  - Prediction multiplicity at any input: range of forecasts across all defensible models (useful for risk reporting)
  - Can enforce constraints post-hoc (monotone in VIX, exclude flagged features) without retraining
- **Novelty:** No published paper has applied Rashomon methods to any financial time-series problem. Closest applications are credit risk (FICO HELOC) and criminal justice (COMPAS).
- **Evaluation:** Walk-forward MSE, QLIKE, MAE; DM tests vs HAR/HARQ/LightGBM; Rashomon prediction range during regime breaks (Mar-2020, Volmageddon)

`keyidea` box: The Rashomon analysis is not just for interpretability. It answers: "are my features robustly important, or did my model just pick one out of several interchangeable options?" This is the novel research contribution of the project.

---

### Part IV: Making It Work

#### Chapter 13: Evaluation

~4 pages.

**Metrics (table):**

| Metric | What It Measures | Role |
|---|---|---|
| QLIKE | Quasi-likelihood loss; penalizes under-prediction of vol | Primary metric |
| MSE | Mean squared error on log-RV | Secondary (dominated by extremes on raw RV) |
| MAE | Mean absolute error on log-RV | Robustness check |
| Diebold-Mariano test | Statistical significance of pairwise forecast differences | "Is model A significantly better than B?" |
| Model Confidence Set | Multi-model comparison; identifies the set of models not significantly worse than the best | "Which models are in the top tier?" |

**Validation protocol:**
- Purged k-fold CV with embargo (standard CV leaks in time series; purge removes observations near the train/test boundary; embargo adds a gap)
- Walk-forward evaluation: train on rolling 5-year window, forecast next period, step forward
- Target improvement: 30-80 bps QLIKE over HARQ baseline

`warning` box: Train with QLIKE loss, not MSE. MSE is dominated by extreme vol days and penalizes proportionally to squared error, which over-weights outliers. QLIKE penalizes relative forecast errors, which is what matters for risk management. Zhang et al. (2025) confirms this matters substantially for model ranking.

#### Chapter 14: The Complete Pipeline

~4 pages.

- **End-to-end system diagram:** Raw data sources -> feature computation (tick-level, daily, surface, cross-asset) -> feature store -> LightGBM + LSTM branches -> ensemble blend -> forecast -> evaluation loop
- **Implementation order (each step independently reportable):**
  1. HARQ + SHAR baseline (Layers 0-1, 11 features, OLS/Ridge)
  2. Add options layer (Layer 2, 20 total features, LightGBM)
  3. Add cross-asset + spillover (Layer 4, 30 features)
  4. E-mini microstructure LSTM module (Layer 3, separate component)
  5. Polish: calendar + roughness + sentiment (Layers 5-7, full 80-120 features)
  6. Rashomon analysis on final feature set
- **Re-training:** Weekly on rolling 5-year window. Monitor Rashomon-set drift.
- **Lookahead bias checklist:**
  - Realized measures use intraday returns up to time t; features for predicting RV_{t+1} must use only information <= t
  - Microstructure features computed on the full day require careful timestamp alignment
  - Options surface features: use end-of-day surface for next-day prediction, not intraday
  - Cross-asset features: ensure synchronization (some are daily, some are tick)

`warning` box: Lookahead bias is the single most common error in financial ML research. Every feature must be computable strictly before the forecast target period begins. When in doubt, add a one-day lag.

---

## File Structure

```
guides/vol-project-ref/
  main.tex          # document root
  preamble.tex      # copied/symlinked from vol-learning-guide
  references.bib    # shared or copied
  chapters/
    ch01-what-we-forecast.tex
    ch02-our-data.tex
    ch03-har-core.tex
    ch04-asymmetry-jumps.tex
    ch05-options-implied.tex
    ch06-microstructure.tex
    ch07-cross-asset.tex
    ch08-feature-composition.tex
    ch09-lightgbm.tex
    ch10-lstm-intraday.tex
    ch11-ensemble.tex
    ch12-rashomon.tex
    ch13-evaluation.tex
    ch14-complete-pipeline.tex
```

## Style Notes

- Reuse vol learning guide preamble (report class, tcolorbox environments)
- Box types used: `keyidea`, `warning`, `workedexample` (for concrete feature computation examples only)
- `intuition` NOT used (guide assumes existing knowledge; no need for plain-English analogies)
- `projectconnection` NOT used (everything is already project-specific)
- `prereq` NOT used (no prerequisites; the guide assumes existing knowledge)
- **Citations:** Use `\citep{}` and `\citet{}` inline throughout. Include `\bibliography{references}` at the end. Every feature layer and model choice should cite its primary source paper(s). No separate "Key Papers" appendix; citations live where the claim is made.
- Heavy use of tables for feature reference
- Diagrams for: high-level pipeline (Ch 1), HARQ mechanism (Ch 3), horizon dependence (Ch 5/8), LSTM pipeline (Ch 10), ensemble architecture (Ch 11), Rashomon pipeline (Ch 12), end-to-end system (Ch 14)
- No em dashes

---

## Per-Chapter Quality Pipeline

Each chapter goes through these checks after drafting. The write-chapter skill's 4-pass pipeline is designed for the teaching-heavy vol learning guide. This guide needs a different pipeline tuned for brevity and visual correctness.

### Pass 1: Write

Main agent writes the chapter following this spec's style rules (tables over prose, decisions not arguments, every sentence project-applicable).

### Pass 2: Brevity Agent (sub-agent)

More aggressive than the write-chapter skill's condenser. Prompt:

> Read the draft chapter at [path]. This is a condensed project reference, not a textbook. Every sentence must be directly applicable to building or defending the vol forecasting project.
>
> Flag and suggest cuts for:
> - **Theory creep:** Any sentence that explains WHY something is true in general, rather than stating the fact and moving on. Example: "The leverage effect arises because firms with declining equity become more leveraged, amplifying..." should be "Negative returns increase future vol (leverage effect)."
> - **Justification bloat:** Sentences that argue for a decision rather than stating it. Example: "We choose LightGBM because extensive evidence from competitions and academic benchmarks shows that gradient-boosted trees dominate..." should be "We use LightGBM. Trees outperform NNs 4:1 on tabular financial data."
> - **Redundancy:** Same fact stated twice in different words, or a table entry repeated in prose.
> - **Hedge words and filler:** "It is worth noting that," "Interestingly," "In particular," "It should be mentioned that," "As previously discussed."
> - **Scope creep:** Content that is true and interesting but not needed to build THIS project.
>
> For each flag, output: location, the offending text, a tightened replacement (or "cut entirely").

### Pass 3: Visual Diagram Check (sub-agent, after LaTeX compilation)

Prompt:

> The chapter at [path] has been compiled to PDF. Read the PDF and inspect every diagram and figure. Check for:
> - **Overlapping text:** Labels, arrows, or annotations that collide or overlap
> - **Readability:** Text too small to read comfortably, or cramped spacing
> - **Missing labels:** Arrows or boxes without labels, or labels that reference undefined terms
> - **Layout:** Diagrams that are too wide for the page margins, or too tall relative to their information content
> - **Flow clarity:** For pipeline/flow diagrams, is the direction of data flow unambiguous? Can you trace the path without backtracking?
> - **Consistency:** Do diagrams use consistent styling (arrow types, box shapes, colors) across the chapter and with other chapters?
>
> For each issue, output: figure number/description, what the problem is, suggested fix.

### Pass 4: Cross-referencer (sub-agent, parallel with Pass 2)

Same as the write-chapter skill's Pass 2:

> Read the draft chapter at [path]. Search `reference/project-papers/` and `reference/papers/` for papers relevant to claims in the chapter. For each paper found, suggest the citation command. Flag any factual errors.

### Consolidation

Main agent applies brevity edits, adds citations, recompiles, then runs the visual check. Iterate if visual issues are found.
