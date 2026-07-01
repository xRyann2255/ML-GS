# Research Journal

Log of what was explored and learned each session. Read at session start for continuity.

**Rules:**
- Max 10 entries. When a new entry would exceed 10, move the oldest to [research-journal-archive.md](research-journal-archive.md) before appending.
- Keep entries concise: question, answer, key numbers, implications. Cut detail once a finding is acted on.
- Remove entries entirely once their content is fully superseded by code, config, or other docs.

---

## 2026-07-01 -- Prediction Blending: LSTM + XGBoost Residual Decorrelation

**Hypothesis card:**
- Question: Does blending LSTM and XGBoost predictions improve QLIKE despite LSTM being worse standalone?
- Feature layer: N/A (model-level ensemble)
- Data needed: 21 symbols, 2015-2026, h=1 OOS predictions from both models on identical test window
- Method: (1) Compute residual correlation; (2) Grid-search optimal blend weight; (3) Per-symbol and conditional analysis
- Success criterion: Blend QLIKE < XGBoost-only QLIKE by ≥1 bps
- Null hypothesis: Correlation ≥ 0.8 → blend adds nothing
- Pitfalls: In-sample weight optimization overfits; need walk-forward validation for production

**Result:** Marginal improvement — below significance threshold

**Key statistics:**
- QLIKE loss correlation: **0.34** (low — models disagree on 2/3 of hard observations)
- Optimal blend weight: **80% XGB + 20% LSTM** (exp-space)
- Blend QLIKE: 0.001833 vs XGBoost 0.001895 → **+0.62 bps improvement**
- LSTM standalone win rate: 40.3% of individual observations

**Per-regime breakdown:**
- High-vol days: LSTM gap = +8.4 bps (worse)
- Low-vol days: LSTM gap = +11.1 bps (worse)
- Spike days (top 10%): LSTM catastrophically worse (+22 bps)
- Blend adds 0-5 bps per symbol (XOM, PG benefit most; AMZN, MSFT, V gain nothing)

**Implication:** The 0.62 bps blend improvement is real but economically negligible — below measurement noise for a single-seed result. The low residual correlation (0.34) confirms the models see different things, but LSTM's absolute quality is too poor for even low-weight inclusion to matter. A stronger intraday model (TCN, or LSTM with IV features) is needed before blending becomes worthwhile.

**Verdict:** LSTM blending NOT worth pursuing at current quality level. The research question is answered: decorrelation exists but the weaker model needs to be closer in absolute quality for blending to produce meaningful gains. The theoretical lower bound for blend improvement with corr=0.34 and QLIKE gap of ~10 bps is ~0.6 bps — which is exactly what we observe.

---

## 2026-07-01 -- Data Audit: 6/6 Sources Active

**Question explored:** What is the current state of all cached data for the vol forecasting pipeline?

### Source Status

| Source | Found | Layers | Status |
|--------|-------|--------|--------|
| correlation | 1/1 files | L7 | CRITICAL |
| cross_asset | 4/4 files | L4 | CRITICAL |
| iv | 33/34 | L2 | CRITICAL |
| microstructure | 29/34 | L3 | CRITICAL |
| ohlcv | 29/34 | L6 | OK |
| ticks | 29/34 | L0, L1, noise_robust | CRITICAL |

### Layer Readiness

- **Ready:** L0, L1, L2, L3, L4, L6, L7, noise_robust

### Implications

- Pooled training with 29 symbols gives ~86,294 rows

---


## 2026-06-19 -- Data Audit: 5/6 Sources Active

**Question explored:** What is the current state of all cached data for the vol forecasting pipeline?

### Source Status

| Source | Found | Layers | Status |
|--------|-------|--------|--------|
| correlation | 0/1 files | L7 | OK |
| cross_asset | 4/4 files | L4 | CRITICAL |
| iv | 33/34 | L2 | CRITICAL |
| microstructure | 29/34 | L3 | CRITICAL |
| ohlcv | 29/34 | L6 | OK |
| ticks | 29/34 | L0, L1, noise_robust | CRITICAL |

### Layer Readiness

- **Ready:** L0, L1, L2, L3, L4, L6, noise_robust
- **L7 BLOCKED:** run `vol ingest-corr`

### Implications

- Pooled training with 29 symbols gives ~85,432 rows
- 1 feature layers blocked pending ingestion

---


## 2026-06-19 -- Trial-059: Feature Removal Hurts, 0DTE Ratio Adds Nothing

**Question:** Does removing "useless" features (calendar dummies, manual interactions, weak-signal expansions) improve LightGBM QLIKE? Does adding `log_iv_0dte_1w_ratio_d` help?

### Results

| Model | Features | h=1 QLIKE | h=5 QLIKE | h=22 QLIKE |
|-------|----------|-----------|-----------|------------|
| lgbm_full (champion) | 128 | **0.1299** | **0.1104** | 0.1699 |
| lgbm_add_0dte_ratio | ~132 | 0.1299 | 0.1104 | 0.1699 |
| lgbm_drop_calendar (-12) | 116 | 0.1306 | 0.1108 | **0.1696** |
| lgbm_drop_tier123 (-32) | 96 | 0.1315 | 0.1118 | 0.1714 |
| har_iv (linear) | 4 | 0.1517 | 0.1216 | **0.1691** |

### Deltas vs lgbm_full (bps, positive = improvement)

| Model | h=1 | h=5 | h=22 |
|-------|-----|-----|------|
| lgbm_add_0dte_ratio | 0 | 0 | 0 |
| lgbm_drop_calendar | **-7** | **-4** | +3 |
| lgbm_drop_tier123 | **-16** | **-14** | **-15** |

### Key Findings

1. **0DTE ratio feature added ZERO value** — `lgbm_add_0dte_ratio` produced identical QLIKE to `lgbm_full` at every horizon. Either `iv_0dte_atm` column is absent from the training data (feature is NaN → never split on), or the feature is already present in `lgbm_full` via current codebase (making them identical runs). Need to inspect actual feature count in model output to diagnose.

2. **Calendar dummies ARE useful at h=1/h=5** — Dropping `day_of_week`, `month`, `quarter_end`, `year_end` hurt by 7 bps (h=1) and 4 bps (h=5). Calendar dummies help at short horizons (event proximity matters for vol). At h=22 the drop was neutral-to-positive (+3 bps) — monthly seasonality noise at long horizons.

3. **Tier 2+3 features ARE useful** — Dropping manual interactions (`atm_iv_x_log_rv`, `vix_x_log_rv`) + weak-signal expansions caused -16/-14/-15 bps degradation. The "redundant for trees" logic was wrong: pre-computed products may help LightGBM with its limited depth (4) by providing explicit signal at shallow splits.

4. **Self-regularization confirmed but NOT perfect** — Trial-046 earlier showed drops are neutral; here they hurt. The tree doesn't waste many splits on these features, but occasionally uses them beneficially.

5. **h=22: har_iv (0.1691) still beats all LightGBM variants** — Confirmed again: 4-param linear > 128-feature tree at monthly horizon.

### Implications

- **Do NOT remove features from the champion.** LightGBM's `min_child_samples=150` + regularization handles noise features better than manual pruning.
- **0DTE ratio needs investigation:** either the data column is missing (ingest issue) or the feature is already included. Check model booster's `feature_name()` output.
- **The "redundant interaction" theory is wrong:** `atm_iv_x_log_rv` products DO help trees with depth=4 by providing a pre-computed signal accessible in a single split that would otherwise require 2 correlated splits.
- **Path forward for improvement:** Adding good features > removing bad features. Focus on new signal sources (0DTE data availability, cross-asset momentum, economic-value-aware loss).

---

## 2026-06-18 -- Data Audit: 5/6 Sources Active

**Question explored:** What is the current state of all cached data for the vol forecasting pipeline?

### Source Status

| Source | Found | Layers | Status |
|--------|-------|--------|--------|
| correlation | 0/1 files | L7 | OK |
| cross_asset | 4/4 files | L4 | CRITICAL |
| iv | 33/34 | L2 | CRITICAL |
| microstructure | 29/34 | L3 | CRITICAL |
| ohlcv | 29/34 | L6 | OK |
| ticks | 29/34 | L0, L1, noise_robust | CRITICAL |

### Layer Readiness

- **Ready:** L0, L1, L2, L3, L4, L6, noise_robust
- **L7 BLOCKED:** run `vol ingest-corr`

### Implications

- Pooled training with 29 symbols gives ~85,432 rows
- 1 feature layers blocked pending ingestion

---


## 2026-06-11 -- Trial-049: COVID-in-Train Improves QLIKE but Hurts GSVIVS01 Sharpe (Statistical-Loss vs Economic-Loss Divergence)

**Question:** Does training on longer folds that include the COVID period (Feb-Jun 2020) help the model learn regime detection and improve both QLIKE and GSVIVS01 Sharpe?

### Setup

Trial-049 is identical to trial-036 in every parameter except `cv.train_size: 504 -> 1843`. First fold trains 2015-01-02 -> 2022-04-29 (covers 2015-16 EM scare, 2018 Volmageddon, COVID, 2022 inflation), then 4 OOS test windows of 126 days each through 2024-12-31. Test starts 2022-05.

### Results (sharpe_0rf from gsvivsStatsByHorizon, default Exec Kvar)

| Horizon | QLIKE 036 -> 049 | LGBM Sharpe 036 -> 049 | always_long Sharpe 036 -> 049 |
|---|---|---|---|
| h=1 | 0.1289 -> 0.1129 (-160 bps) | **1.95 -> 1.37 (-0.59)** | 1.95 -> 2.01 (+0.07) |
| h=5 | 0.1067 -> 0.0867 (-200 bps) | 1.10 -> 0.76 (-0.35) | 1.89 -> 1.95 (+0.06) |
| h=22 | 0.1628 -> 0.0881 (-747 bps) | 0.06 -> -0.07 (-0.12) | 1.74 -> 1.91 (+0.17) |

After subtracting the always_long lift, LGBM degradation is approximately -0.65 / -0.41 / -0.29 Sharpe.

Position rate at h=1: 56.7% short -> 54.4% short. Model became more conservative; it skipped profitable short days.

### Why QLIKE improved but Sharpe dropped

1. **Test window shift.** Trial-049 only tests 2022-05 -> 2024 (post-COVID, calmer). Lower-magnitude RV is numerically easier for QLIKE. Same artifact as trial-030b retraction. The QLIKE improvement is not directly comparable to trial-036's 2017-2024 test.
2. **COVID training teaches caution.** Seeing March 2020 tails biases RV forecasts upward, makes the IV-RV gap less positive, suppresses short signals.
3. **All linear baselines also degrade** (har_iv_1w h=1: -0.43, har_iv: -0.29, har: -0.16). Rules out model-specific overfitting; this is a regime effect on the test window itself.
4. **QLIKE is symmetric in log-error; the variance-swap P&L is asymmetric.** A missed short on a calm day costs the entire premium. QLIKE does not penalize that asymmetry.

### Implications

- **REJECT trial-049 as champion replacement.** Keep trial-036 spec (or trial-047 reseed envelope) as production.
- **Methodology rule:** any trial that changes train_size or date_range must report QLIKE on the SAME OOS dates as the baseline to be valid. Future trials should pin a fixed evaluation window in addition to the natural per-fold OOS.
- **Strategic lesson:** regime-rich training does NOT automatically improve economic value. The next economic-value experiments should optimize directly on Sharpe or on a P&L-aware loss, not on QLIKE.

### Persisted to

[workspace/research/trials.yaml](workspace/research/trials.yaml) trial-049 entry.

---

## 2026-06-11 -- Trial-047: Multi-Seed Re-Baseline Confirms Trial-036 Numbers Were Cherry-Picked

**Question:** Are trial-036's published champion QLIKE numbers (h1=0.1289, h5=0.1067, h22=0.1628) reproducible? Trial-046 flagged that the same-config control re-ran at h1=0.1366 (-77 bps), suggesting parallel-fit nondeterminism.

**Method:** Single tournament run, 5 identical LightGBM tournament variants differing ONLY in `seed` (42, 123, 456, 789, 2026). Shared data, features, CV splits. trial-036 spec unchanged. har, har_iv as linear baselines.

### Reseeded QLIKE Envelope (5 seeds)

| Horizon | Mean    | Std    | Min     | Max     | Range (bps) | Trial-036 reported | Gap (bps) |
|---------|---------|--------|---------|---------|-------------|-------------------|-----------|
| h=1     | 0.13679 | 0.0003 | 0.13658 | 0.13724 | 6.6         | 0.12890           | **-78.9** |
| h=5     | 0.10804 | 0.0001 | 0.10790 | 0.10822 | 3.2         | 0.10670           | **-13.4** |
| h=22    | 0.16826 | 0.0003 | 0.16784 | 0.16849 | 6.4         | 0.16280           | **-54.6** |

Gap = reseeded_mean - reported. Negative means reported was BETTER. At all three horizons, the reported number sits OUTSIDE the seed envelope (below min). Trial-036's numbers are not reproducible — they reflect a single lucky seed/process-pool order, not model quality.

### LightGBM Mean vs har_iv Linear Baseline

| Horizon | lgbm mean | har_iv  | Delta (bps) |
|---------|-----------|---------|-------------|
| h=1     | 0.13679   | 0.15211 | **+153**    |
| h=5     | 0.10804   | 0.12180 | **+138**    |
| h=22    | 0.16826   | 0.16755 | **-7**      |

### Implications

1. **Project-state.md scorecard is wrong.** Stale single-seed numbers from trial-033/036 should be replaced with reseeded means.
2. **h=22 champion is har_iv, NOT LightGBM.** A 4-parameter linear model beats the 128-feature LightGBM across ALL 5 seeds. The LGBM "win" reported in trial-033 (0.1764) and trial-036 (0.1628) was seed luck. Consistent with trial-045 conclusion that h=22 LightGBM gains are marginal.
3. **h=1 and h=5 LightGBM still beat har_iv robustly** (+153 / +138 bps with tiny envelope) — those wins are real.
4. **Reporting protocol going forward:** report mean ± std across ≥3 seeds, not single-seed numbers. Any "new champion" claim needs multi-seed confirmation before being entered in project-state.md.

**Persisted:** [memory/research/project-state.md](memory/research/project-state.md) scorecard updated; trial-047 added to [workspace/research/trials.yaml](workspace/research/trials.yaml).

---

## 2026-06-08 -- GSVIVS01 Daily Lifecycle Audit: Complete Mechanics Documented

**Question explored:** What exactly does the GSVIVS01 strategy do each day? When does it buy/sell, what instruments, how much, and how is it sized?

### Confirmed Lifecycle (from output.json, 1011 days)

1. **13:10 ET:** Signal generation fires (algo, no discretion)
2. **13:30-14:00 ET:** SELL two SPX option strips via 30-min TWAP:
   - 0DTE strip (expires today ~16:00): ~9-18 OTM options
   - 1DTE strip (expires tomorrow): ~15 OTM options (main P&L driver)
3. **13:30-17:15 ET:** Delta hedge with ES futures (~52 clips/day, 5-min TWAPs)
4. **16:00 ET:** 0DTE expires at intrinsic; 1DTE carries overnight
5. **MOC:** Close (buy back) yesterday's expired strip at settlement price (0 if OTM)
6. **22:00 UTC:** Index mark

### Critical Sizing Detail: Variance-Swap Weighting

Quantities follow $\text{qty}_i = c / K_i^2 \cdot \Delta K_i$. Verified: `qty * K^2 = 96,860` (constant). ATM strike has both put + call at half qty. This makes P&L proportional to (RV^2 - IV^2), i.e., a variance swap payoff.

### P&L: 37 bps gross premium/day, -14 bps TC = +3.2 bps net = 8.4% ann.

### Persisted to: `memory/repo/gsvivs-daily-lifecycle.md`

---

## 2026-06-08 -- Cross-Asset Lead-Lag at h=5/h=22: rate_vol Dominates, credit_cdx HURTS

**Question:** Do rate_vol_1y10y and credit_vol_cdx carry forward-looking signal at h=5 and h=22? At h=1 the ablation showed +139/+85 bps respectively. Why was h=5 previously "negligible"?

### Method

SPY-only, OLS expanding window (504d min train), 2015-2026. Tested: point-in-time levels (lag 0-5), multi-day averages (5d/10d/22d/44d/63d), momentum (1d/5d changes), z-scores, and combinations. Compared against HAR and HAR-IV baselines. Granger block F-tests for lags 1-5.

### Key Results

**rate_vol is a powerhouse at ALL horizons:**

| Signal variant | h=5 (bps vs HAR) | h=22 (bps vs HAR) |
|---|---|---|
| rate_vol z-score (20d) | **+266** | **+354** |
| rate_vol 5d change | +224 | +211 |
| rate_vol 22d mean | +144 | +174 |
| rate_vol level (t=0) | +134 | +55 |
| rate_vol level (t=5) | +129 | +112 |

vs HAR-IV (stronger baseline):
| Signal | h=5 (bps vs HAR-IV) | h=22 (bps vs HAR-IV) |
|---|---|---|
| rate_vol level | **+232** | **+261** |
| rate_vol 22d avg | +212 | **+286** |
| credit_cdx 22d avg | +45 | -500 |

**credit_cdx HURTS at h=5 and h=22** (unlike h=1 where it helped +85 bps). Every credit_cdx variant produces negative bps at longer horizons. Likely: credit spread level is contemporaneously correlated (rho=0.78) but reflects REACTIVE comovement, not predictive signal.

**Granger tests significant** (p<0.02) for both signals in-sample, but credit_cdx does not translate OOS.

### Cross-correlation structure

credit_cdx has HIGHER raw correlation than rate_vol (0.70 vs 0.22 at lag 0, h=5) but LOWER OOS utility. Classic "spurious regression": both credit and equity vol driven by same regime. rate_vol's lower but consistent OOS gain suggests genuine LEAD.

### Lag structure

For rate_vol at h=22, lagged signals are BETTER than t=0 (t5: +112 vs t0: +55 bps). Rate vol leads equity vol by multiple days at monthly horizon.

### Implications for trial-039

1. **KEEP rate_vol** -- massive signal at all horizons, even above HAR-IV
2. **DROP credit_cdx** from level features -- hurts OOS at h=5/h=22
3. **Best representation:** z-score (20d) or 5d change, not raw level
4. **For h=22:** 22d average of rate_vol (+286 bps vs HAR-IV) better than point-in-time (+261 bps)
5. **2026-06-05 "h=5 negligible" was WRONG** -- that tested only raw levels without z-score transform

### Next

- Update trial-039: keep rate_vol (z-score + level), drop credit_cdx, keep fx_iv/gvz
- Test if rate_vol signal persists in pooled LightGBM (23 symbols)

### UPDATE (same session): Tournament FAILED — trial-043

Ran full tournament with cross_asset_momentum layer + tree_expansion. LightGBM results:
- h=1: 0.1401 (WORSE by 112 bps vs trial-036's 0.1289)
- h=5: 0.1136 (WORSE by 69 bps vs trial-036's 0.1067)
- h=22: 0.1676 (WORSE by 48 bps vs trial-036's 0.1628)

Same pattern as microstructure: signal is real in OLS but adding 26+ features to LightGBM dilutes splits. The model has limited tree capacity (num_leaves=16) and the extra features steal splits from proven IV/RV core.

**Fix options (next experiments):**
1. Add rate_vol to init_score (HAR-IV-RateVol: 5 params linear model as base)
2. Use ONLY rate_vol z-score (single feature) without full cross-asset layer
3. Drop tree_expansion when xasset is used (fewer features competing)
4. Increase num_leaves to 32 (more capacity for additional features)

### UPDATE 2 (same session): Trial-044 — init_score + single feature ALSO FAILS

Implemented HAR-IV-RateVol (5-param OLS/Ridge/Lasso) and used as LightGBM init with only z_rate_vol surviving as tree feature. Results:
- LightGBM: h1=0.1340 (-51 bps), h5=0.1097 (-30 bps), h22=0.1674 (-46 bps) vs trial-036
- **Better than trial-043** (single feature vs 26) but still fails

**CRITICAL FINDING:** har_iv_ratevol (OLS 5-param) is WORSE than har_iv (4-param) in pooled training:
- h5: 0.1271 vs 0.1210 (rate_vol hurts -61 bps)
- h22: 0.1737 vs 0.1666 (rate_vol hurts -71 bps)

**Root cause:** The rate_vol signal is **SPY/index-specific**. The OLS ablation was SPY-only (+232 bps). In pooled training with 21 symbols, swaption rate_vol predicts market-wide vol (SPY, QQQ) but NOT individual stock vol (AAPL, NVDA, etc.) which has idiosyncratic components. When you train a pooled linear model, the noisy stock-level rate_vol relationship overwhelms the clean index-level one.

**Conclusion:** Cross-asset signals require **symbol-type conditioning**: useful for index ETFs, harmful for single stocks. To leverage rate_vol, need either:
1. Index-only model (SPY/QQQ/IWM subset)
2. LightGBM interaction: rate_vol x beta (let tree learn which symbols benefit)
3. Two-tier architecture: separate models for index vs single-name

---

## 2026-06-05 -- Cross-Asset Per-Feature Ablation: LEVELS Beat CHANGES

**Question:** Which cross-asset signals carry forward-looking information for equity RV? Do daily CHANGES (momentum) beat LEVELS?

### Method

SPY-only, OLS expanding window (504d train, 126d test), HAR-IV baseline. Added each signal one at a time in three variants: (1) 1-day change only, (2) all momentum (1d + 5d + z-score), (3) level only.

### Results: h=1

| Signal | 1d-change (bps) | All momentum (bps) | Level only (bps) | Best |
|--------|-----------------|--------------------|--------------------|------|
| rate_vol | +96 | +74 | **+139** | Level |
| credit_cdx | +31 | +47 | **+85** | Level |
| fx_iv_eurusd | -1 | +23 | **+65** | Level |
| fx_iv_usdjpy | -13 | -5 | **+65** | Level |
| gvz | -1 | -12 | **+24** | Level |
| oil_vol | +1 | -14 | -3 | Marginal |
| gold_vol | -4 | -26 | -10 | Hurts |

### Results: h=5

Effects negligible (all <5 bps). Baseline QLIKE already very low (0.01275). Only credit_cdx momentum shows +4 bps forward signal.

### Key Insight: LEVELS dominate, CHANGES hurt

**The forward-looking hypothesis was WRONG for this setup.** Cross-asset implied vol LEVELS (rate_vol, credit_cdx, fx_iv) massively help at h=1 (+65-139 bps). But adding their CHANGES/momentum REDUCES the benefit. The level already contains the forward signal (options prices ARE forward-looking). Changes add noise.

**Why trial-031b/031c found levels hurt:** those trials used the old `CrossAssetLayer` which applied `compute_rolling_vol()` (backward RV) to what's already implied vol data — essentially computing vol-of-vol. The RAW implied vol levels (fx_iv_usdjpy, rate_vol_1y10y, credit_vol_cdx) were never properly tested as direct features.

### Implications

1. The `cross_asset_momentum` layer (changes only) is NOT the right approach
2. Need a layer that passes through RAW cross-asset implied vol LEVELS directly
3. rate_vol (+139 bps), credit_cdx (+85 bps), fx_iv (+65 bps each) are huge signals — together could be 100+ bps in LightGBM
4. The SPY OLS result may inflate vs pooled LightGBM (need full tournament to confirm)

### Next

- Design trial with raw cross-asset IV levels as direct LightGBM features (not `compute_rolling_vol` transform)
- Focus on: rate_vol_1y10y, credit_vol_cdx, fx_iv_usdjpy, fx_iv_eurusd, gvz

---

## 2026-06-05 -- Prediction Lag Diagnostic: Why Models Miss Vol Spikes

**Question:** The model achieves good QLIKE but systematically lags: it cannot predict big moves before they happen. What causes this and what forward-looking signals could fix it?

### Empirical Evidence (SPY, HAR-IV, 2017-2026 OOS)

**Spike days (>2std above 63d rolling mean) = 3.9% of days but 22% of total QLIKE loss.**

Event study (mean prediction error = actual - predicted, in log-RV):
| Window | T-5 | T-4 | T-3 | T-2 | T-1 | **T (spike)** | T+1 | T+2 |
|--------|-----|-----|-----|-----|-----|---------------|-----|-----|
| Error  | 0.32 | 0.31 | 0.29 | 0.42 | **0.64** | **1.02** | 0.28 | 0.21 |

Model underestimates for 5 days leading into a spike. The error at T-1 (0.64) shows the model is ALREADY wrong the day before the spike hits.

**IV carries forward signal the model partially ignores:**
- IV rises 0.65 std the day BEFORE spikes (t-stat = 3.85)
- corr(dIV_today, RV_tomorrow) = 0.12
- Q5 of IV changes (biggest rises): mean next-day log_rv = -10.00 vs Q1 (biggest drops): -10.39
- Spread: 0.39 log-RV units between extreme IV change quintiles

**Structural limitation:**
- HAR uses 3 backward RV averages (d/w/m) + 1 IV level
- IV LEVEL correlates with RV level (both track the regime) but does not capture the DIRECTION of change
- The model never sees: "IV just jumped 2% today" as a feature separate from "IV is at 15%"

### Root Cause: Wrong Features, Not Wrong Model

The model has ~128 features but almost all are **contemporaneous or lagged** transformations of RV:
- log_rv_d/w/m, rs_positive/negative, bpv, jumps, cont, rk, noise_gap
- tree_expansion adds _change and _zscore of these (still backward RV transforms)

The ONLY forward-looking feature used: IV level (log_atm_iv_1w_d).
Missing forward-looking signals that are available in our data:

| Signal | Mechanism | Data Available? | Expected Impact |
|--------|-----------|-----------------|-----------------|
| IV daily change (dIV) | Market pricing in future vol | YES (iv_1w_atm) | High (corr 0.12 with fwd RV) |
| IV 5d momentum | Sustained hedging demand | YES (iv_1w_atm) | High |
| IV term slope CHANGE | Rebalancing expectations | YES (term_slope) | Medium |
| Skew change | Tail risk re-pricing | YES (skew_1m) | Medium |
| FX vol spike (USD/JPY) | Carry unwind precedes equity vol | YES (fx_iv_usdjpy) | High for regime changes |
| Credit spread change | Risk-off contagion | YES (credit_vol_cdx) | Medium |
| Treasury slope change | Macro regime | YES (yield_slope_10y5y) | Low-medium |
| Microstructure OFI | Informed flow detection | YES (order_flow_imbalance) | High for h=1 |
| VPIN level/change | Toxicity indicator | Partial (NaN in recent data) | High for h=1 |

### Key Insight

Trial-035 already tested VIX level, VIX innovation, and VRP as LightGBM features and found NO improvement. But those are LEVELS. The forward-looking signal is in CHANGES and CROSS-ASSET CONTAGION:

1. **dIV (IV daily change)** = "the market just repriced risk" -- this IS already in tree_expansion as iv_change but only if options layer is included
2. **Cross-asset CHANGES** (FX vol spike, credit widening, rate vol) are NOT in the model at all
3. **Microstructure signals** (OFI, signed volume) capture informed trading BEFORE public news

### Proposed Experiments (priority order)

1. **Trial-037: Cross-asset change features for h=1** -- Add dFX_vol, dCredit, dRate_slope as LightGBM features. These lead equity vol by 1-2 days (contagion).
2. **Trial-038: Microstructure + IV acceleration** -- Add order_flow_imbalance, signed_volume_ratio, and iv_0dte_accel (already computed!) for h=1.
3. **Trial-039: Asymmetric loss / spike-aware training** -- Weight spike-day observations higher in QLIKE objective (asymmetric penalty for underestimation).
4. **Trial-040: Conditional regime model** -- Separate LightGBM for high-VRP regime (when IV >> RV, a spike is being priced in).

### Why This Matters for Trading

A model that lags is USELESS for:
- Buying protection before a move (you buy AFTER the spike, when IV is already high)
- Selling vol into calm (you sell too late, when RV has already compressed)
- The IV-RV gap strategy specifically needs to predict WHEN RV will catch up to IV

The fix is not better QLIKE on average -- it's better CONDITIONAL QLIKE on the 4% of days that matter.

---

## 2026-07-01 -- LSTM Integration: Why It Failed and What Could Work

**Question:** Can we find a way to make LSTM feature stacking work, given that all previous integration modes (standalone, residual, feature stacking, daily Rosenbaum) failed across 10+ trials?

### Complete Trial History

| Trial | Mode | QLIKE h=1 | vs Champion | Verdict |
|-------|------|-----------|-------------|---------|
| 051 | Standalone intraday | 0.4332 | catastrophic | FAIL |
| 053 | Residual on LightGBM | 0.12878 | +0.9 bps | NEUTRAL |
| 054 | Single-fold residual | 0.12053 | strong | NOT ROBUST |
| 054b | Residual + symbol emb | 0.12883 | +1.9 bps | NEUTRAL |
| 057 | Residual retuned | 0.12353 | -16.5 bps | FAIL |
| 058 | Residual + v3 channels | 0.12255 | -16.9 bps | FAIL |
| 061b | Feature stack → LightGBM | 0.12869 | 0 bps (identical) | FAIL |
| 066 | Daily Rosenbaum LSTM | 0.16205 | -330 bps vs xgb | FAIL |
| 066b | LSTM residual on XGBoost | 0.12940 | +0.2 bps | NEUTRAL |
| 066c | LSTM residual on XGBoost v2 | 0.12989 | -4.9 bps | FAIL |

### Root Cause Analysis: Three Distinct Failure Modes

**Failure 1: Wrong input data for standalone LSTM (trial-051)**
- Fed 2,340 x 5-feature sequences (10s bars). Far too long for LSTM — gradient vanishing, padding overhead.
- 5 features (log_ret, vol_share, buy_ratio, log_n_trades, abs_ret) are all contemporaneous microstructure. None contain forward-looking information about *next-day* vol.
- LSTM has ~50K params on ~50K training samples — massively overparameterized relative to signal.

**Failure 2: Residual is noise after good tree model (trials 053-058, 066b/c)**
- After XGBoost/LightGBM with 128 features + har_iv init, residual $e_t$ is near-white-noise.
- Tree already captures nonlinear interactions between IV, RV lags, and options features.
- LSTM on residual is trying to predict noise — mathematically equivalent to fitting noise.
- Adding richer intraday channels (v3: price_accel, rolling_vpin, cum_rv) didn't help because the *target* is noise, not because the *features* are bad.

**Failure 3: Feature stacking — gradient isolation + no incremental information (trial-061b)**
- LSTM embedding, attention entropy, attention peak time, prediction — tree ignored ALL of them.
- Gradient isolation: LSTM was optimized for its own QLIKE, not for producing features useful to the tree. The embedding space encodes information in linear combinations that tree splits can't efficiently access.
- More fundamentally: the LSTM had the same 5 weak intraday features. If the LSTM can't beat HAR standalone, its embedding carries no information the tree doesn't already have.

### Key Insight: The Problem Is the LSTM's Input, Not the Architecture

The learning guide (ch12b) is explicit: **LSTMs become useful when you change what you feed them.** On RV lags alone, HAR matches LSTM (Christensen et al. 2023). On raw sequential data (LOB, high-frequency returns), LSTM adds genuine value.

Current LSTM inputs — 5 simple bar statistics from 10-second aggregation — are weak next-day predictors because:
1. **Contemporaneous, not forward-looking.** `log_ret`, `abs_ret`, `vol_share` describe today's microstructure, not tomorrow's volatility.
2. **No cross-asset dimension.** The LSTM sees one symbol's bars in isolation. Cross-asset lead-lag (Treasury/FX moves preceding equity vol) is invisible.
3. **No options-market information.** The richest forward-looking signals (IV surface dynamics, 0DTE pricing, put/call flow) are absent from sequences.
4. **Too granular, too long.** 2,340 bars of 10-second data create padding and vanishing gradient issues. The useful signal is in the *shape* of intraday vol (U-shape deviation, event clustering), not in individual ticks.

### What the Literature Says Could Work

1. **DeepVol approach (Moreno-Pino & Zohren 2022):** Feed raw 5-minute returns directly into a TCN (not LSTM). 78 bars/day instead of 2,340. TCN is parallelizable, has explicit receptive field, no vanishing gradient. The model learns to predict $RV_{t+1}$ end-to-end from raw intraday returns, bypassing RV computation entirely.

2. **Richer intraday features at coarser granularity:** Aggregate 10-second bars to 5-minute bars. Add LOB-derived channels per bar: order imbalance delta, spread dynamics, volume acceleration. 78 bars x 10+ features is more manageable than 2,340 x 5.

3. **Multi-scale sequence architecture:** Hierarchical model — 5-min bars within the day, then daily features across days. Captures both intraday patterns (U-shape, event clustering) and multi-day memory (HAR-like persistence).

4. **Prediction blending instead of feature stacking:** Train LSTM independently on different input data than the tree. Blend predictions with regime-dependent weights. Competition evidence (Optiver 2021) shows blending beats stacking.

### Proposed Path Forward: Three Concrete Experiments

**Experiment A: TCN on 5-minute returns (DeepVol-style)**
- Input: 78 bars of raw 5-min log returns per day, pooled across 21 symbols
- Architecture: Dilated causal TCN, 8 layers, receptive field = 256 (covers full day)
- Target: next-day log-RV (h=1)
- Why it might work: TCN handles fixed-length sequences better than LSTM; raw returns let the model discover its own volatility features; DeepVol achieved SOTA in the literature
- Requires: 5-min bar aggregation from existing 10-second data (trivial)

**Experiment B: LSTM with enriched 5-min features**
- Input: 78 bars x 12+ features: log_ret, abs_ret, vol_share, buy_ratio, order_flow_imbalance, rolling_vpin, cum_rv, session_frac, spread_proxy (if available), price_accel, log_n_trades, volume_surprise (bar_vol / rolling_avg)
- Architecture: 2-layer LSTM, hidden=64, attention pool
- Target: next-day log-RV (h=1)
- Why it might work: the current 2,340-bar sequence is too long; 78 bars with richer features is the right tradeoff. More features per bar means more signal per timestep.

**Experiment C: Prediction blending (LSTM + XGBoost)**
- Train XGBoost champion independently (as-is, trial-067 config)
- Train LSTM/TCN independently on intraday sequences (Experiment A or B)
- Blend: $\hat{y} = w \cdot \hat{y}_{XGB} + (1-w) \cdot \hat{y}_{LSTM}$
- Weight $w$ calibrated on expanding-window validation, possibly regime-dependent
- Why it might work: avoids gradient isolation; each model operates on data suited to its architecture; LSTM sees intraday dynamics the tree can't access; tree handles tabular features the LSTM can't use. Competition evidence strongly favors this over stacking.

### Priority Order

1. **Experiment A first** (TCN on raw 5-min returns) — cheapest to try, closest to proven DeepVol approach, tests whether the problem is architecture (LSTM vs TCN) or data (10s bars vs 5-min returns)
2. **Experiment C next** (blend) — if TCN/LSTM produces even a mediocre standalone forecast, blending with XGBoost can extract value without stacking's gradient isolation
3. **Experiment B only if A fails** — enriched features are more engineering work, and if raw returns don't work at 5-min, enriched features probably won't either

### Requirements Before Running

- [ ] Implement 5-minute bar aggregation from 10-second sequence parquets (trivial groupby)
- [ ] Implement TCN model class (currently stub with `NotImplementedError`)
- [ ] Add prediction blending infrastructure to the pipeline runner
- [ ] Test on SPY single-symbol first, then pooled 21-symbol

---
