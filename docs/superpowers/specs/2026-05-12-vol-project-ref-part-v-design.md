# Design Spec: Vol-Project-Ref Part V -- The Build

**Date:** 2026-05-12
**Status:** Draft
**Scope:** Three new chapters (Part V) for `guides/vol-project-ref/` + a detailed development plan file

---

## 1. Overview

### What we're adding

1. **Part V: The Build** in `guides/vol-project-ref/` with three chapters:
   - Ch15: The Data-to-Feature Pipeline
   - Ch16: System Architecture
   - Ch17: The Development Plan

2. **Detailed development plan** at `docs/project-plans/development-plan.md`

### Why

The existing 14-chapter guide covers theory and reference (what everything is, why it matters). Part V adds the practical layer: how data physically flows through the system, how the ensemble architecture works, and what to build next. The detailed plan file provides task-level breakdowns for generating session prompts.

### Design constraints

- **Zero repetition** with chapters 1-14. No measure definitions (ch03-07), no source descriptions (ch02), no feature selection rationale (ch08), no evaluation methodology (ch13), no logical pipeline ordering (ch14), no model internals (ch09-12), no success criteria (ch01 Table 1.2, ch13), no target variable definition (ch01).
- **Same style** as existing chapters: terse, table-driven, booktabs tables, TikZ diagrams, exactly 2 boxes per chapter (keyidea + warning only -- no prereq, workedexample, or projectconnection boxes, which are not used in this guide).
- **No em dashes** in text.
- Existing chapters are the source of truth. New content reflects updated understanding from the codebase audit without calling out contradictions.
- ~100-200 lines per chapter (matching existing chapter lengths).

### What each existing chapter covers (overlap guard)

| Chapter | Covers | New chapters must NOT repeat |
|---|---|---|
| Ch01 | Target variable ($\log RV_{t+h}$, h=1/5/22), universe (35 instruments), success criteria (QLIKE 30-80 bps), high-level pipeline diagram | Target definition, success criteria numbers, universe description |
| Ch02 | Data source inventory (6 sources with capabilities/constraints), GS edge vs public, constraint implications | Source descriptions, capabilities, constraints |
| Ch03 | HAR core features (RV d/w/m, RQ, HARQ interaction), formulas, HARQ shrinkage | Layer 0 measure definitions or formulas |
| Ch04 | Semivariances, BPV, jumps (BNS, Lee-Mykland), signed jumps, realized moments | Layer 1 measure definitions or formulas |
| Ch05 | VRP, skew, term slope, butterfly, VVIX, event IV | Layer 2 feature definitions |
| Ch06 | Price acceleration, OBI, depth ratio, spread, VPIN, Kyle lambda | Layer 3 feature definitions |
| Ch07 | Treasury slope, FX vol, commodity vol, DY spillover | Layer 4 feature definitions |
| Ch08 | Layers 5-7 (calendar, memory, sentiment), diminishing returns curve, horizon-priority table, triple expansion principle, feature engineering principles | Feature selection rationale, diminishing returns analysis, triple expansion explanation |
| Ch09 | LightGBM config, QLIKE objective, SHAP, Table 9.1 (layer/features/count) | Model configuration, feature layer counts |
| Ch10 | LSTM/TCN for E-mini intraday | Sequence model internals |
| Ch11 | Prediction blending architecture (Figure 11.1), "Do Not Stack Features" warning, "Blend Predictions, Not Features" keyidea | Prediction blending details |
| Ch12 | Rashomon analysis, interpretable trees | Interpretability methodology |
| Ch13 | QLIKE formula, MSE/MAE/DM/MCS definitions, purged k-fold CV, walk-forward, success targets | Evaluation methodology, metric definitions |
| Ch14 | End-to-end system diagram (Figure 14.1), 6-step implementation order (Table 14.1), retraining/monitoring, lookahead bias checklist | Logical pipeline diagram, implementation step details, lookahead prevention rules |

---

## 2. Ch15: The Data-to-Feature Pipeline

### Purpose

One-stop lookup for feature lineage. Given any feature name, trace it back to its raw data source and see every transformation step. No theory, no formulas (those live in ch03-08), no source descriptions (ch02). Just the mechanical chain and the complete feature inventory.

### Structure

#### Opening (3-4 lines)

States what this chapter is: the lookup table for feature lineage. Points reader to ch02 for source descriptions, ch03-07 for measure formulas, ch08 for selection rationale. This chapter answers one question: "how does raw data become this feature?"

#### Figure 15.1: Data Lineage Funnel

TikZ diagram showing the shape of data at each transformation stage:

```
6 Raw Sources        ~18 Daily Measures       Lag/Window          Expansion         80-120 Features
(narrow)             (intermediate)           Application         (tree models)     (wide)
                                              d/w/m + shift(1)    level/change/z
```

Annotated with counts at each stage. Color-coded: blue (sources), green (measures), orange (features). This is a data-level diagram, distinct from ch14's system-level diagram (which shows data sources -> feature computation -> models -> ensemble -> evaluation). This diagram zooms into the "feature computation" block of ch14.

#### Table 15.1: Source-to-Measure Map

Small bridging table (~8 rows). Maps ch02's sources to the daily measures they produce, without re-describing sources.

| Source | Daily Measures Produced |
|---|---|
| L1 ticks (34 symbols) | rv, log_rv, rq, bpv, rs_positive, rs_negative, jump_stat, jump_indicator, continuous_variation, jump_variation, j_positive, j_negative, realized_skewness, realized_kurtosis |
| L1 tick-level log prices | rk, noise_gap |
| Daily OHLCV (TSDB) | overnight_return |
| E-mini L2 depth | price_acceleration, obi, depth_ratio, spread_mean/std, vpin |
| SPX IV surface (Marquee) | atm_iv (5 tenors), skew (5 tenors), butterfly, term_slope |
| Single-stock IV (Marquee EDRVOL) | stock_atm_iv, stock_skew |
| Cross-asset (TSDB) | treasury_slope, fx_vol, commodity_vol, vix_level, vix_futures_slope |
| Calendar/event sources | fomc_proximity, nfp_proximity, opex_proximity, earnings_proximity, day_of_week, month |

Columns: Source | Daily Measures Produced. No descriptions, no constraints, no formulas.

#### Table 15.2: Complete Feature Matrix

The backbone of the chapter. One row per feature in the planned optimal feature set, grouped by layer (0-7). Every row traces back from feature name to source.

Columns:

| Feature | Source Measure | Derivation | Expansion | Models |
|---|---|---|---|---|
| log_rv_d | rv | log, shift(1) | -- | HAR, SHAR, HARQ, LGB |
| log_rv_w | rv | log(rolling mean 5d), shift(1) | -- | HAR, SHAR, HARQ, LGB |
| log_rv_m | rv | log(rolling mean 22d), shift(1) | -- | HAR, SHAR, HARQ, LGB |
| sqrt_rq_d | rq | sqrt, shift(1) | -- | HARQ, LGB |
| rq_rv_interaction | rq, rv | sqrt(rq) * log(rv), shift(1) | -- | HARQ, LGB |
| overnight_return | open, close | log(open_t / close_{t-1}), shift(1) | -- | LGB |
| log_rs_positive_d | rs_positive | log, shift(1) | -- | SHAR, LGB |
| log_rs_positive_w | rs_positive | log(rolling mean 5d), shift(1) | -- | SHAR, LGB |
| log_rs_positive_m | rs_positive | log(rolling mean 22d), shift(1) | -- | SHAR, LGB |
| log_rs_negative_d | rs_negative | log, shift(1) | -- | SHAR, LGB |
| log_rs_negative_w | rs_negative | log(rolling mean 5d), shift(1) | -- | SHAR, LGB |
| log_rs_negative_m | rs_negative | log(rolling mean 22d), shift(1) | -- | SHAR, LGB |
| log_bpv_d | bpv | log, shift(1) | -- | HAR-CJ, LGB |
| log_bpv_w | bpv | log(rolling mean 5d), shift(1) | -- | LGB |
| log_jump_variation_d | jump_variation | log, shift(1) | -- | HAR-J, HAR-CJ, LGB |
| log_continuous_variation_d | continuous_variation | log, shift(1) | -- | HAR-CJ, LGB |
| log_continuous_variation_w | continuous_variation | log(rolling mean 5d), shift(1) | -- | LGB |
| signed_return_d | close prices | log(close_t / close_{t-1}), shift(1) | -- | LGB |
| log_rk_d | rk | log, shift(1) | -- | LGB |
| log_rk_w | rk | log(rolling mean 5d), shift(1) | -- | LGB |
| noise_gap_d | noise_gap | shift(1) | -- | LGB |
| noise_gap_w | noise_gap | rolling mean 5d, shift(1) | -- | LGB |
| atm_iv_1m | atm_iv (1m tenor) | shift(1) | level/change/zscore | LGB |
| atm_iv_3m | atm_iv (3m tenor) | shift(1) | level/change/zscore | LGB |
| vrp | atm_iv, rv | IV^2 - RV, shift(1) | level/change/zscore | LGB |
| skew_1m | skew (1m tenor) | shift(1) | level/change/zscore | LGB |
| term_slope | atm_iv (3m, 1m) | ATM_3m - ATM_1m, shift(1) | level/change/zscore | LGB |
| butterfly_1m | skew, atm_iv (1m) | 0.5(IV_25dP + IV_25dC) - IV_ATM, shift(1) | level/change/zscore | LGB |
| iv_rv_gap | atm_iv, rv | IV - sqrt(RV*252), shift(1) | level/change/zscore | LGB |
| stock_atm_iv | stock IV (EDRVOL) | shift(1) | level/change/zscore | LGB |
| stock_vrp | stock_atm_iv, rv | stock IV^2 - RV, shift(1) | level/change/zscore | LGB |
| price_acceleration | E-mini mid-price | 2nd derivative (window=50), daily agg, shift(1) | level/change/zscore | LGB, LSTM |
| obi | E-mini L2 bid/ask sizes | (sum_bid - sum_ask)/(sum_bid + sum_ask), daily agg, shift(1) | level/change/zscore | LGB, LSTM |
| depth_ratio | E-mini L2 depth | log(bid_depth/ask_depth), daily agg, shift(1) | level/change/zscore | LGB, LSTM |
| spread_mean | E-mini bid/ask | mean spread (bps), shift(1) | level/change/zscore | LGB |
| spread_std | E-mini bid/ask | std of spread (bps), shift(1) | level/change/zscore | LGB |
| vpin | E-mini trades | VPIN algorithm, shift(1) | level/change/zscore | LGB |
| treasury_slope | 10y, 2y yields | 10y - 2y (bps), shift(1) | level/change/zscore | LGB |
| fx_vol | USD/JPY, EUR/USD | annualized rolling RV (22d), shift(1) | level/change/zscore | LGB |
| commodity_vol | CL, GC | annualized rolling RV (22d), shift(1) | level/change/zscore | LGB |
| vix_level | VIX close | shift(1) | level/change/zscore | LGB |
| vix_futures_slope | VX1, VX2 | VX2 - VX1, shift(1) | level/change/zscore | LGB |
| fomc_proximity | FOMC calendar | days to next FOMC, shift(1) | -- | LGB |
| nfp_proximity | NFP calendar | days to next NFP, shift(1) | -- | LGB |
| opex_proximity | calendar math | days to next monthly OpEx, shift(1) | -- | LGB |
| earnings_proximity | earnings calendar | days to next earnings, shift(1) | -- | LGB (single-name) |
| day_of_week | date | categorical encoding | -- | LGB |
| month | date | categorical encoding | -- | LGB |
| frac_diff_rv | rv | $(1-L)^d$ with d~0.35-0.45, shift(1) | level/change/zscore | LGB |
| hurst_exponent | rv | rolling Hurst (22d), shift(1) | level/change/zscore | LGB |
| vol_of_vol | rv | std(RV) over 22d, shift(1) | level/change/zscore | LGB |
| regime_duration | rv | days since last 2-sigma spike, shift(1) | -- | LGB |
| finbert_sentiment | news text | daily FinBERT score, shift(1) | level/change/zscore | LGB |
| negative_news_count | news text | count of negative articles, shift(1) | -- | LGB |

**Notes on the table:**
- "Expansion" column shows which features get the {level, change, zscore} triple expansion for LightGBM. Features marked "--" are used as-is.
- "Models" column shows which model families use each feature. HAR/SHAR/HARQ/HAR-J/HAR-CJ use specific subsets (defined in ch09 Table 9.1). LGB uses all. LSTM uses E-mini intraday sequences directly (ch10), not these daily features.
- The actual feature count depends on which layers are active and how many expansion variants are included. With all layers and triple expansion, the matrix reaches ~80-120 columns.
- Features with "rolling mean 5d" or "rolling mean 22d" compute the average in variance space first, then take log (per Corsi 2009 convention).
- noise_gap is a ratio, not log-transformed.

**Distinction from ch09 Table 9.1:** Ch09's table shows layer-level summaries (layer name, feature group, count). This table shows individual features with their derivation chain, making every feature traceable back to raw data.

### Boxes

1. **keyidea: "Every Row Traces Back to Source"** -- The feature matrix is the blueprint. To understand any feature, read across: source measure tells you where the data comes from (ch02 has details), derivation tells you the transformation chain, expansion tells you what LightGBM sees.

2. **warning: "Look-Ahead Lives in the Derivation Column"** -- Every derivation must include shift(1) or equivalent. Any feature whose derivation does not include an explicit lag uses information from the forecast target period. The most subtle violations come from rolling windows that include day t when predicting day t+1.

---

## 3. Ch16: System Architecture

### Purpose

Present two ensemble architecture variants not covered in ch11 (which covers prediction blending). Show how features and predictions flow through each architecture. Enable side-by-side comparison of all three approaches.

### Structure

#### Opening (2-3 lines)

Ch11 presents prediction blending. This chapter presents two alternative architectures: feature stacking and residual stacking. All three are compared at the end.

#### Figure 16.1: Three-Panel Architecture Comparison

Single TikZ figure with three side-by-side panels, same visual language (same node shapes, same color scheme as ch11 and ch14):

**Panel A: Feature Stacking**
```
E-mini L2 Sequences ─→ LSTM ─→ Embedding (k-dim)
                                    ↓
Tabular Features (L0-7) ──────→ LightGBM ─→ Forecast
                                    ↑
                          (embedding joins feature set)
```
- LSTM produces a k-dimensional embedding from intraday sequences
- Embedding vector concatenated with tabular features
- Single LightGBM model produces final forecast

**Panel B: Residual Stacking**
```
Tabular Features ─→ HAR Baseline ─→ Forecast_HAR
                          ↓
                     Residuals_1 = y - Forecast_HAR
                          ↓
Tabular Features ─→ LightGBM ─→ Forecast_LGB (of residuals)
                          ↓
                     Residuals_2 = Residuals_1 - Forecast_LGB
                          ↓ (optional)
E-mini Sequences ──→ LSTM ─→ Forecast_LSTM (of residuals)
                          ↓
              Final = Forecast_HAR + Forecast_LGB [+ Forecast_LSTM]
```
- Each model trains on the residuals of the previous stage
- Each model has a distinct role: HAR captures multi-scale persistence, LightGBM captures nonlinear residual structure, LSTM (optional) captures regime dynamics
- Final forecast is the sum of all stage forecasts

**Panel C: Prediction Blending (Ch.11)**
```
Tabular Features ─→ LightGBM ─→ Forecast_GBM ──┐
                                                  ├─→ Weighted Average ─→ Final
E-mini Sequences ──→ LSTM ────→ Forecast_SEQ ──┘
```
- Reference to ch11 Figure 11.1 -- not re-drawn, just a simplified schematic for comparison
- Independent models, combined at prediction level

**Visual language:** Same color coding as ch14 (blue for data, green for computation, orange for models). Each panel is ~1/3 page width. Labels on every arrow showing what flows.

#### Section: Feature Stacking

Short prose (~8-10 lines):
- What goes into the LSTM: E-mini L2 5-min bars + LOB features, 78 time steps per day
- What comes out: k-dimensional embedding vector (default k=32, or k=1 for scalar forecast)
- How it joins the tree: embedding concatenated with the ~80-120 tabular features
- LightGBM trains on the combined feature set

Pros/cons as a small table:

| | Feature Stacking |
|---|---|
| Pros | Single training pass, LSTM learns representations the tree can exploit |
| Cons | Gradient isolation (LightGBM cannot backprop into LSTM), embedding not optimized for tree objective, debugging harder, no RV literature demonstrates this beating alternatives |

#### Section: Residual Stacking

Short prose (~8-10 lines):
- Stage 1: HAR baseline (OLS) produces forecast and residuals
- Stage 2: LightGBM trains on Stage 1 residuals with full tabular features
- Stage 3 (optional): LSTM trains on Stage 2 residuals from E-mini sequences
- Final forecast: sum of all stage forecasts
- Each model specializes by construction: HAR handles the autoregressive structure, LightGBM handles nonlinearities the HAR misses, LSTM handles whatever pattern remains

Pros/cons as a small table:

| | Residual Stacking |
|---|---|
| Pros | Each model has distinct role, no gradient isolation (clean residual targets), aligns with HARQ-X project proposal, supported by recent RV literature (MDPI 2026) |
| Cons | Sequential training (each stage depends on prior), more moving parts than simple blending, residual signal may be weak at later stages |

#### Table 16.1: Three-Way Comparison

| Dimension | Feature Stacking | Residual Stacking | Prediction Blending (Ch.11) |
|---|---|---|---|
| Complexity | High (joint training) | Moderate (sequential stages) | Low (independent models) |
| Gradient flow | Broken (tree cannot backprop into LSTM) | Clean (each model sees residuals) | N/A (independent) |
| Literature support for RV | Weak (no paper demonstrates this winning) | Strong (MDPI 2026, HARQ-X proposal) | Strong (Optiver, Kaggle, multiple papers) |
| Fallback if LSTM underperforms | Must retrain tree without embedding | Drop Stage 3, keep HAR + LightGBM | Drop one model, keep the other |
| Interpretability | Opaque (embedding features lack meaning) | Clear (each stage's contribution is measurable) | Clear (individual model forecasts are interpretable) |

### Boxes

1. **keyidea: "Residual Stacking Gives Each Model a Distinct Role"** -- HAR captures multi-scale RV persistence. LightGBM captures nonlinear patterns the HAR misses. LSTM (if used) captures whatever regime dynamics remain. Each model trains on residuals from the prior stage, so roles are distinct by construction.

2. **warning: "Feature Stacking Breaks Gradient Isolation"** -- LightGBM cannot back-propagate into the LSTM. The embedding is never optimized for the tree objective. No paper in the RV literature (2023-2026) demonstrates LSTM-embedding-to-GBDT feature stacking beating prediction blending or residual stacking at any forecast horizon.

### Distinction from ch11 and ch14

- **Ch11** covers prediction blending only (Figure 11.1, blend formula, static vs dynamic weights). Ch16 does not re-describe prediction blending; it references ch11 in the comparison table.
- **Ch14** has a system-level pipeline diagram (Figure 14.1: data sources -> feature computation -> model branches -> ensemble -> evaluation). Ch16's diagrams show the internal architecture of the ensemble block at a finer level of detail.

---

## 4. Ch17: The Development Plan

### Purpose

Ordered milestones with acceptance criteria. What to build, in what order, what "done" means. Not the logical feature-layering sequence (ch14 Table 14.1) or the evaluation methodology (ch13). This is the project build order reflecting priorities (trading signal > academic rigor > model novelty) and including foundation work that ch14 does not mention.

### Structure

#### Opening (3-4 lines)

Ch14 gives the logical order for layering features and models (6 conceptual steps). This chapter gives the actual build order: what to implement first given project priorities and foundation work that must happen before anything else. Priority ordering: trading signal > academic rigor > model novelty.

#### Milestones

Each milestone: one-line description, acceptance criteria (testable), dependencies.

**M1: Fix Foundation**
- Fix CV purge gap enforcement (`purge_gap >= h` per horizon), verify QLIKE log-space sign convention against Patton (2011), add `context` kwarg to `FeatureLayer.compute()`, extract shared `safe_log` utility.
- Done when: regression tests exist for each fix; all 390 existing tests still pass; Layer 2 can receive IV surface data through the context argument.
- Dependencies: none.

**M2: LightGBM with Custom QLIKE Objective**
- Implement custom QLIKE gradient/hessian, wire Optuna for hyperparameter tuning with SQLite storage, implement walk-forward evaluation loop, select 8-symbol dev universe.
- Done when: LightGBM trains on dev universe with QLIKE objective, Optuna finds better hyperparameters than defaults, walk-forward produces OOS predictions for all 3 horizons.
- Dependencies: M1.

**M3: QLIKE Tournament**
- Run all 7 HAR variants + LightGBM across 3 horizons on dev universe. Implement Diebold-Mariano pairwise tests. Build tournament_table output.
- Done when: tournament table exists (8 models x 3 horizons) with QLIKE scores and DM p-values. At least one ML model shows statistically significant improvement (p<0.05) over HAR at one horizon.
- Dependencies: M2.

**M4: Layer 2 Options Features**
- Wire Marquee IV surface and single-stock EDRVOL into FeatureLayer. Compute VRP, skew, term slope, butterfly for SPX and all 34 symbols.
- Done when: options features produce daily values with no look-ahead, NaN handling for missing surface days works, features improve QLIKE when added to LightGBM on dev universe.
- Dependencies: M1 (FeatureLayer context arg).

**M5: Tradeable Signal**
- Implement IV-RV gap signal logic, delta-hedged straddle P&L backtest, vol-targeting P&L, compute Sharpe ratio and max drawdown.
- Done when: equity curve plot exists, Sharpe > 0 out-of-sample on dev universe, transaction cost sensitivity tested.
- Dependencies: M3 (working RV forecasts), M4 (options features for IV-RV gap).

**M6: Ensemble Experiments**
- Implement residual stacking (HAR -> LightGBM on residuals). Implement prediction blending (inverse-QLIKE weights). Compare both to standalone models on QLIKE. Re-run tournament with ensemble entries.
- Done when: at least one ensemble strategy matches or beats the best standalone model on QLIKE. If neither beats standalone, document the finding.
- Dependencies: M3 (tournament baseline), M5 (completed signal).

**M7: Stretch Goals (ordered by impact-per-effort)**
1. Regime-conditional QLIKE evaluation (split evaluation by VIX regime)
2. Model Confidence Set (Hansen 2011, block bootstrap)
3. LSTM scalar forecast as 1 extra LightGBM feature (E-mini only)
4. Full 34-symbol tournament run
5. Presentation figures (4-5 key plots: QLIKE table, forecast vs actual, P&L curve, feature importance)
6. Rashomon analysis (interpretable trees, feature importance stability)
- Dependencies: M6 for items 1-2, M2 for item 3, M3 for item 4, M5 for item 5, M3 for item 6.

#### Figure 17.1: Critical Path + Dependency Diagram

TikZ diagram. Critical path highlighted in bold/color:

```
M1 (Foundation) ──→ M2 (LightGBM) ──→ M3 (Tournament) ──→ M6 (Ensemble) ──→ M7 (Stretch)
      │                                       ↑                   ↑
      └──→ M4 (Layer 2 Options) ──→ M5 (Signal) ──────────────────┘
```

- Critical path: M1 -> M2 -> M3 -> M6 -> M7 (bold/colored)
- Parallel track: M4 -> M5 (branches from M1, feeds into M5 which requires both M3 and M4)
- M4 can start as soon as M1 is done, in parallel with M2
- M5 requires both M3 and M4

### Boxes

1. **keyidea: "M1-M5 Is the Minimum Viable Deliverable"** -- A QLIKE tournament (7 HAR + LightGBM, DM tests) plus a tradeable IV-RV signal with P&L backtest is a presentable result. Everything in M6-M7 is upside. If time runs out after M5, the project has a defensible outcome.

2. **warning: "M1 Is Non-Negotiable"** -- The purge gap bug causes silent data leakage for h=22. The QLIKE sign convention determines whether the loss function penalizes over-prediction or under-prediction. All results produced before M1 is complete are potentially invalid. Do not skip ahead.

### Distinction from ch14

- **Ch14 Table 14.1** gives the logical feature-layering order (Step 1: L0-1, Step 2: add L2, Step 3: add L4, etc.) with models and deliverables per step. It is conceptual and assumes no bugs.
- **Ch17** gives the actual build order based on project priorities. It includes foundation fixes (not in ch14), reorders based on priority (trading signal first), identifies the critical path and parallelizable work, and defines a minimum viable deliverable.
- Ch14 says "what features to add in what order." Ch17 says "what to build next and when it's done."

---

## 5. Detailed Development Plan File

**Location:** `docs/project-plans/development-plan.md`

**Purpose:** Task-level breakdowns for each milestone. Detailed enough to generate a session prompt for each task. This is the document Session 3 reads.

### Structure

One section per milestone (M1-M7). Each milestone section contains:

- **Objective:** What this milestone achieves and why it matters
- **Prerequisites:** Which milestones / infrastructure must exist first
- **Tasks:** Numbered list. Each task specifies:
  - What to build (specific functions, classes, files to create or modify)
  - Input/output contract (what it takes, what it produces)
  - Key decisions already made (from the audit, so the session prompt doesn't re-litigate)
  - Testing requirements (what tests to write, what they assert, edge cases)
  - Acceptance criteria (how to know this task is done)
- **Data sources involved:** Which APIs / systems, confirmed access status
- **Fallback plan:** What to do if the primary approach doesn't work
- **Papers / references:** Which papers motivate the approach

### Milestone Details

#### M1: Fix Foundation

**Objective:** Eliminate correctness bugs that invalidate all downstream results. Unblock Layer 2-5 implementation.

**Tasks:**

1. **Fix CV purge gap enforcement**
   - File: `src/volforecast/utils/cv.py`
   - Change: Add validation in each splitter that enforces `purge_gap = max(purge_gap, h)` per horizon
   - Key decision: This is applied dynamically per horizon inside the training loop, not as a global config value
   - Testing: (a) Test that `purge_gap=5, horizon=22` produces splits with gap >= 22. (b) Test that `purge_gap=30, horizon=5` keeps gap at 30 (does not shrink). (c) Test that no train sample appears within h days of any test sample. (d) Regression: all existing CV tests still pass.
   - Done when: impossible to create a split where train data is within h days of test data

2. **Verify and fix QLIKE log-space sign convention**
   - File: `src/volforecast/evaluation/metrics.py`
   - Change: Derive correct log-space QLIKE from Patton (2011) variance-space formula. Current code has `exp(y - y_hat) - (y - y_hat) - 1`. Correct Patton (2011) derivation gives `exp(y_hat - y) - (y_hat - y) - 1`. Verify which the code implements, fix if wrong.
   - Key decision: Must match Patton (2011) so results are comparable to literature
   - Testing: (a) Verify QLIKE is minimized when y_hat = y (both conventions satisfy this). (b) Verify asymmetry direction: over-prediction should be penalized more heavily than under-prediction (Patton convention). (c) Test on synthetic data where correct ranking is known.
   - Done when: QLIKE matches Patton (2011), documented in code comment

3. **Add context kwarg to FeatureLayer protocol**
   - File: `src/volforecast/protocols.py`, all Layer 0-1 compute methods
   - Change: Extend `FeatureLayer.compute(daily_data)` to `compute(daily_data, *, context=None)`. Update HARCoreLayer, AsymmetryLayer, NoiseRobustLayer to accept and ignore the kwarg.
   - Key decision: Backward-compatible (context=None default). Layer 2+ will use context to receive IV surface, L2 depth, Treasury data from the pipeline orchestrator.
   - Testing: (a) All existing Layer 0-1 tests pass unchanged. (b) New test: calling `.compute(data, context={"iv_surface": df})` works without error. (c) Protocol check: a layer that accepts context still satisfies `isinstance(layer, FeatureLayer)`.
   - Done when: Layer 2 can be implemented using `context["iv_surface"]` without changing the protocol

4. **Extract shared safe_log and consolidate zero-floor handling**
   - File: `src/volforecast/features/transforms.py` (already has safe_log)
   - Change: Audit all feature modules for duplicated safe_log or ad-hoc log(max(x, eps)) patterns. Replace with single `safe_log` import. Ensure consistent `min_value=1e-20` everywhere.
   - Key decision: safe_log already exists in transforms.py. This is a deduplication, not a new function.
   - Testing: (a) Grep for all `log(` and `np.log(` calls in features/ -- each should use safe_log or have an explicit reason not to. (b) Test safe_log(0) returns log(1e-20), not -inf. (c) All existing tests pass.
   - Done when: no duplicated log-safety patterns in features/

**Fallback:** None. These are mandatory correctness fixes.

#### M2: LightGBM with Custom QLIKE Objective

**Objective:** First ML model. Produces genuine ML-vs-baseline comparison.

**Tasks:**

1. **Implement custom QLIKE objective**
   - File: `src/volforecast/models/lightgbm.py`
   - What to build: `QLIKEObjective` class with `.gradient(y_pred, y_true)` and `.hessian(y_pred, y_true)` methods returning arrays. Both operate in log-RV space.
   - Key decision: Gradient and hessian derived from the Patton (2011) log-space QLIKE (as fixed in M1). The gradient is `exp(y_hat - y) - 1` and the hessian is `exp(y_hat - y)`.
   - Testing: (a) Numerical gradient check: compare analytical gradient to finite-difference approximation (tolerance 1e-5). (b) Same for hessian. (c) Verify objective is convex (hessian > 0 everywhere). (d) Train on synthetic data where true relationship is known; model should converge.
   - Done when: LightGBM trains with custom QLIKE and converges

2. **Implement LightGBMVolModel**
   - File: `src/volforecast/models/lightgbm.py`
   - What to build: Model class satisfying `VolModel` protocol. Wraps `lgb.train()` with custom objective, early stopping, DART boosting. Configuration from ch09 Table 9.2 as defaults.
   - Key decision: Register as `"lightgbm"` in MODEL_REGISTRY. Use DART boosting type. Early stopping on validation QLIKE.
   - Testing: (a) `.fit(X, y)` runs without error on 1000-row synthetic data. (b) `.predict(X)` returns array of correct length. (c) `.save()` / `.load()` round-trips correctly. (d) Predictions improve over training (QLIKE decreases). (e) Satisfies `isinstance(model, VolModel)`.
   - Done when: `vol run train --config lightgbm_config.yaml` completes successfully

3. **Wire Optuna hyperparameter tuning**
   - File: `src/volforecast/models/lightgbm.py` or new `models/tuning.py`
   - What to build: Optuna study that tunes learning_rate, num_leaves, min_data_in_leaf, n_estimators, reg_alpha, reg_lambda. Uses SQLite storage at `workspace/experiments.db`.
   - Key decision: Use Optuna's native SQLite storage (same DB as experiment tracking). Search space from LightGBM best practices for small tabular datasets.
   - Testing: (a) 10-trial study completes on synthetic data. (b) Best trial has lower QLIKE than default params. (c) SQLite DB contains trial records after study.
   - Done when: `vol run tune --config ...` finds improved hyperparameters

4. **Implement walk-forward evaluation loop**
   - File: `src/volforecast/pipeline/runner.py` (extend existing)
   - What to build: Rolling 5-year train window, step forward by test_size days, collect all OOS predictions. This may already be partially implemented via the expanding_window CV splitter.
   - Key decision: Use the existing CV infrastructure. Walk-forward is the primary evaluation method (ch13).
   - Testing: (a) Windows don't overlap illegally. (b) Total OOS predictions cover the expected date range. (c) No look-ahead: max train date < min test date - purge_gap for each fold.
   - Done when: walk-forward produces OOS predictions for all 3 horizons on dev universe

5. **Select 8-symbol dev universe**
   - File: `src/volforecast/constants.py`
   - What to build: `DEV_UNIVERSE = ["SPY", "AAPL", "MSFT", "NVDA", "XOM", "JPM", "IWM", "ES"]` constant. Covers mega-cap tech, energy, financials, broad ETF, futures.
   - Key decision: Use DEV_UNIVERSE for all iteration. Full 34-symbol universe for final tournament only.
   - Testing: All 8 symbols have cached RV panels. Dev runs complete in <25% of full-universe time.
   - Done when: constant exists, baseline experiment runs on dev universe

**Data sources:** Chunk Store L1 (confirmed working for all symbols), cached RV panels.
**Fallback:** If custom QLIKE objective is numerically unstable, fall back to MSE objective with QLIKE as evaluation metric only. Document the compromise.
**Papers:** Patton (2011) for QLIKE, Ke et al. (2017) for LightGBM, Optiver 2021 for configuration baseline.

#### M3: QLIKE Tournament

**Objective:** The most important deliverable. Definitive model comparison across all baselines and horizons.

**Tasks:**

1. **Run full baseline tournament**
   - What to build: Script or CLI command that trains all 8 models (HAR, HARQ, SHAR, HAR-J, HAR-CJ, Ridge-HAR, Lasso-HAR, LightGBM) on dev universe across all 3 horizons (h=1, 5, 22) using walk-forward evaluation.
   - Key decision: 8 models x 8 symbols x 3 horizons = 192 training runs. Use dev universe. Save all predictions.
   - Testing: (a) All 192 runs complete without error. (b) OOS predictions exist for every model/symbol/horizon combination. (c) QLIKE scores are finite and positive for all entries.
   - Done when: all predictions saved to workspace/models/

2. **Implement Diebold-Mariano test**
   - File: `src/volforecast/evaluation/statistical_tests.py`
   - What to build: `diebold_mariano_test(loss_1, loss_2, horizon)` returning test statistic and p-value. Must use HAC standard errors (Newey-West) for h > 1.
   - Key decision: Use `arch` package if DM implementation is slow. Otherwise implement from scratch (small function).
   - Testing: (a) DM test on identical loss series returns p=1.0 (not significant). (b) DM test on loss_1 = loss_2 + large constant returns p~0 (significant). (c) HAC correction produces different standard errors than OLS for h=22.
   - Done when: `diebold_mariano_test()` passes all tests

3. **Build tournament_table output**
   - File: `src/volforecast/evaluation/statistical_tests.py`
   - What to build: `tournament_table(predictions_dict, y_true, baseline_key)` that produces a DataFrame with QLIKE scores, QLIKE improvement (bps vs baseline), and DM p-values for each model pair.
   - Key decision: Baseline is HARQ (most competitive linear model). Table format: rows = models, columns = QLIKE (h=1/5/22), improvement bps (h=1/5/22), DM p-value vs HARQ (h=1/5/22).
   - Testing: (a) Table dimensions are correct (8 models x 9 metric columns). (b) Baseline row shows 0 bps improvement. (c) p-values are between 0 and 1.
   - Done when: tournament table prints cleanly for dev universe

**Data sources:** Cached predictions from task 1.
**Fallback:** If DM implementation is slow, use `arch.unitroot.cointegration` utilities or implement simplified version without HAC for h=1. For h>1, HAC is essential.
**Papers:** Diebold & Mariano (1995), Patton (2011) for QLIKE.

#### M4: Layer 2 Options Features

**Objective:** Add the most impactful feature layer (options-implied) and unblock the tradeable signal.

**Tasks:**

1. **Implement OptionsLayer.compute()**
   - File: `src/volforecast/features/options.py`
   - What to build: Fill in the stubbed `compute()` method. Use `context["iv_surface"]` to receive Marquee data. Compute: atm_iv (1m, 3m), vrp, skew (1m), term_slope, butterfly, iv_rv_gap. For single-stock: stock_atm_iv, stock_vrp.
   - Key decision: IV surface comes via context arg (M1). SPX features are market-wide regime signals. Single-stock IV via EDRVOL_PERCENT (confirmed working).
   - Testing: (a) Features produce daily values for a 1-year test period. (b) VRP sign is correct on average (IV > RV). (c) No NaN propagation from missing surface days (forward-fill or NaN). (d) shift(1) applied to all features. (e) Features for SPX-only measures don't leak into stock-specific predictions.
   - Done when: `OptionsLayer.compute(data, context={"iv_surface": df})` returns features

2. **Wire IV surface fetching into pipeline**
   - File: `src/volforecast/pipeline/runner.py`
   - What to build: Before calling feature layers, fetch IV surface via `marquee.fetch_iv_surface()` and single-stock IV via `marquee.fetch_atm_iv()` with ric parameter. Pass as context dict.
   - Key decision: Fetch once per pipeline run, not per feature layer call.
   - Testing: (a) Pipeline runs with `feature_layers: [har_core, asymmetry, options]` config. (b) Context dict contains expected DataFrames. (c) Features are computed for symbols that have IV data.
   - Done when: full pipeline runs with Layer 2 active

3. **Validate QLIKE improvement**
   - Run LightGBM with and without Layer 2 features on dev universe. Compute QLIKE lift.
   - Key decision: Expect 5-10% QLIKE improvement at h=5 and h=22 based on ch08 horizon priority table.
   - Testing: (a) QLIKE improves at h=5 or h=22. (b) If no improvement, investigate feature quality before concluding Layer 2 doesn't help.
   - Done when: QLIKE comparison documented

**Data sources:** Marquee IV surface (confirmed), EDRVOL_PERCENT single-stock (confirmed for all 34 symbols).
**Fallback:** If single-stock IV has coverage gaps for some symbols, fall back to SPX-only IV as market-regime signal for those symbols.
**Papers:** Christensen et al. (2023) for VRP, Bollerslev et al. (2009) for IV-RV relationship.

#### M5: Tradeable Signal

**Objective:** The priority deliverable. Prove the forecasts can make money.

**Tasks:**

1. **Implement IV-RV gap signal**
   - File: `src/volforecast/evaluation/economic_value.py`
   - What to build: `iv_rv_gap_signal(iv_forecast, rv_forecast, threshold)` returning signal in {-1, 0, +1}. Long vol when RV forecast > IV (vol is cheap). Short vol when IV > RV forecast (vol is expensive). Neutral within threshold band.
   - Key decision: Use ATM 1m IV for the gap. Threshold calibrated on training data (e.g., 1 sigma of historical gap).
   - Testing: (a) Signal direction matches expected (long when RV forecast > IV). (b) Signal is -1, 0, or +1 only. (c) On random forecasts, signal should produce ~zero P&L (no edge from noise).
   - Done when: signal function produces daily signals for dev universe

2. **Implement P&L backtesting**
   - File: `src/volforecast/evaluation/economic_value.py`
   - What to build: `delta_hedged_straddle_pnl(signal, rv, iv, spot)` and `vol_targeting_pnl(returns, vol_forecast, target)`. Both return daily P&L series.
   - Key decision: Straddle P&L is primary. Vol-targeting is secondary/simpler.
   - Testing: (a) P&L is zero when signal is always neutral. (b) Cumulative P&L is monotonically increasing on a synthetic dataset where the signal is always correct. (c) Transaction cost sensitivity: P&L remains positive under reasonable cost assumptions (e.g., 1-2 bps per trade).
   - Done when: P&L series computed for dev universe

3. **Implement performance metrics and equity curve**
   - File: `src/volforecast/evaluation/economic_value.py`
   - What to build: `compute_sharpe(returns)`, `compute_max_drawdown(cum_returns)`, equity curve matplotlib plot.
   - Testing: (a) Sharpe of zero-mean returns is ~0. (b) Max drawdown of monotonically increasing series is 0. (c) Plot renders without error.
   - Done when: Sharpe > 0 out-of-sample, equity curve plot saved

**Data sources:** IV surface (from M4), RV forecasts (from M3).
**Fallback:** If straddle P&L is weak, fall back to simpler vol-targeting overlay (position sizing inversely proportional to forecast vol). If that's also weak, the negative result is still publishable.
**Papers:** Bollerslev et al. (2009) for VRP trading, Corsi (2009) for vol-targeting.

#### M6: Ensemble Experiments

**Objective:** Test whether combining models improves forecasts.

**Tasks:**

1. **Implement residual stacking**
   - File: `src/volforecast/models/ensemble.py`
   - What to build: Script/class that: (a) loads HAR OOS predictions, (b) computes residuals, (c) trains LightGBM on residuals with full feature set, (d) sums forecasts.
   - Key decision: Residual stacking is primary. Each model trains independently on residuals from the prior stage. Option A architecture (standalone blend stage from audit): train models separately, blend post-hoc.
   - Testing: (a) Stage 1 residuals have approximately zero mean. (b) Stage 2 QLIKE on residuals is positive (model captures signal). (c) Combined forecast QLIKE <= best standalone model QLIKE (ensemble should not hurt).
   - Done when: residual stacking forecast exists for dev universe

2. **Implement prediction blending**
   - File: `src/volforecast/models/ensemble.py`
   - What to build: `InverseQLIKEEnsemble` that weights model predictions inversely proportional to their validation QLIKE. Simple fallback: equal-weight average.
   - Key decision: This is the simpler fallback to residual stacking.
   - Testing: (a) Weights sum to 1. (b) Model with lower QLIKE gets higher weight. (c) Blended QLIKE <= worst individual model QLIKE.
   - Done when: blended forecast exists for dev universe

3. **Re-run tournament with ensemble entries**
   - Add residual stacking and prediction blending to the tournament table alongside the 8 standalone models.
   - Done when: tournament table has 10 rows (8 standalone + 2 ensemble), DM tests run against all pairs.

**Data sources:** Saved predictions from M3.
**Fallback:** If neither ensemble beats the best standalone, report that finding. It's a valid and publishable result (many papers find ensembles don't help for short-horizon vol).
**Papers:** MDPI 2026 (HAR-LSTM-GARCH residual stacking), Bucci 2020 (forecast combinations).

#### M7: Stretch Goals

**Objective:** Polish and extend. Ordered by impact-per-effort.

**Tasks (each independent):**

1. **Regime-conditional QLIKE** -- Split walk-forward evaluation by VIX regime (low/medium/high terciles). Show how model rankings change across regimes. Low effort, high insight.
   - Testing: QLIKE computed separately for each regime. Total observations sum to full sample.

2. **Model Confidence Set** -- Hansen et al. (2011) block bootstrap. Returns set of models not significantly worse than the best.
   - Testing: MCS on identical models returns all models in the set. MCS on one dominant model returns only that model.

3. **LSTM scalar forecast** -- Train LSTM on E-mini intraday sequences. Use scalar point forecast as 1 extra LightGBM feature (dimension 1). Requires implementing `SequenceModel` protocol.
   - Testing: LSTM converges on E-mini data. Scalar forecast added as feature improves LightGBM QLIKE.

4. **Full 34-symbol tournament** -- Re-run M3 tournament on full universe. Takes ~4x longer than dev universe.
   - Testing: All 34 symbols complete. Cross-sectional analysis of which stocks benefit most from ML.

5. **Presentation figures** -- 4-5 key plots: QLIKE comparison table (formatted), forecast vs actual time series, P&L equity curve, feature importance bar chart (LightGBM native).
   - Testing: Plots render, are readable, match presentation format.

6. **Rashomon analysis** -- Interpretable trees on same feature set. Quantify feature importance stability across near-optimal model set.
   - Testing: Multiple near-optimal trees found. Jaccard similarity of top-10 features computed.

**Papers:** Hansen et al. (2011) for MCS, Lundberg (2017) for SHAP.

### Appendix: Architecture Decisions Log

Summary of key decisions from the audit with rationale, so future sessions don't re-debate them:

| Decision | Choice | Rationale |
|---|---|---|
| Ensemble approach | Residual stacking (primary), prediction blending (fallback) | No RV paper supports feature stacking. Residual stacking gives each model a distinct role. |
| Dev universe | 8 symbols (SPY, AAPL, MSFT, NVDA, XOM, JPM, IWM, ES) | ~75% speedup. Full 34 for final tournament only. |
| Experiment tracking | SQLite `experiments.db` | Lightweight, supports cross-experiment queries, Optuna native storage. |
| FeatureLayer protocol | Add `context` kwarg | Backward-compatible. Keeps data-fetching in pipeline orchestrator. |
| LSTM scope | E-mini only, scalar forecast, stretch goal | Only 1 symbol has L2 depth. High effort, moderate gain. |
| QLIKE convention | Patton (2011) log-space derivation | Industry standard. Comparable to literature. |
| Pipeline architecture | Option A: standalone blend stage | Train models independently, blend post-hoc. Maximum flexibility. |
| Priority ordering | Trading signal > academic rigor > model novelty | Desk audience cares about P&L first. |

---

## 6. Diagrams Summary

| Figure | Chapter | Type | What it shows | Distinct from |
|---|---|---|---|---|
| 15.1 | Ch15 | Data lineage funnel | 6 sources -> ~18 measures -> lag/window -> expansion -> 80-120 features | Ch14 Fig 14.1 (system-level pipeline) |
| 16.1 | Ch16 | Three-panel comparison | Feature stacking vs residual stacking vs prediction blending architecture | Ch11 Fig 11.1 (prediction blending only) |
| 17.1 | Ch17 | Critical path + dependencies | M1-M7 milestone ordering with critical path highlighted | Ch14 Table 14.1 (logical feature-layering order) |

---

## 7. Implementation Notes

### LaTeX conventions (matching existing guide)

- `\chapter{Title}` with `\label{ch:short-name}`
- Sections marked with `%% ──────────────` visual dividers
- Tables: booktabs (`\toprule`, `\midrule`, `\bottomrule`), `\small` font, `@{}` column padding
- TikZ diagrams: blue for data, green for computation, orange for models, red for evaluation
- Boxes: `\begin{keyidea}[Title]` and `\begin{warning}[Title]` only
- Citations: `\citep{}` parenthetical, `\citet{}` textual
- Cross-references: `Chapter~\ref{ch:...}`, `Figure~\ref{fig:...}`, `Table~\ref{tab:...}`
- No em dashes

### Files to create

| File | Purpose |
|---|---|
| `guides/vol-project-ref/chapters/ch15-pipeline.tex` | Data-to-feature pipeline chapter |
| `guides/vol-project-ref/chapters/ch16-architecture.tex` | System architecture chapter |
| `guides/vol-project-ref/chapters/ch17-development-plan.tex` | Development plan chapter |
| `docs/project-plans/development-plan.md` | Detailed development plan |

### Files to modify

| File | Change |
|---|---|
| `guides/vol-project-ref/main.tex` | Add Part V and `\input{}` for ch15-17 |

### Subagent diagram review

During implementation, dispatch a subagent to independently review each TikZ diagram for:
- Correctness of data flow (no arrows pointing the wrong way)
- No overlap with existing diagrams (ch11 Figure 11.1, ch14 Figure 14.1)
- Visual consistency with existing diagram style
- Completeness (all nodes labeled, all connections shown)
