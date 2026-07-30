---
created: 2026-05-22
updated: 2026-06-01
tags: [lightgbm, pooled-training, feature-engineering, hyperparameters, per-symbol, threading, gpu, optuna, h22-campaign, har-iv, atm-iv-benchmark, init-score, base-model, return-features, vol-anomaly, per-horizon-cv, expanded-universe]
status: active
priority: P1
relates: [optimal-feature-set, implied-vol, evaluation-framework]
---

# LightGBM Pooled Training — Lessons Learned

Hard-won insights from multi-session debugging of LightGBM vs HAR-family baselines.

## Critical Insight: Per-Symbol vs Market-Wide Features

In pooled training (21 symbols stacked into one training matrix), **per-symbol features provide 21x more signal variation** than market-wide features.

- `atm_iv_x_log_rv_d` = per-symbol ATM IV * log(RV) — varies across all 21 rows on the same date
- `vix_x_log_rv_d` = market-wide VIX * log(RV) — identical for all 21 rows on the same date

The tree can split on per-symbol features to distinguish individual stock behavior. Market-wide features only provide date-level variation, which is far less useful for a pooled model.

**Impact:** Replacing per-symbol ATM IV interaction with market-wide VIX degraded QLIKE from 0.1556 to >0.16 (commit `4cb070f`). Restoring it recovered to 0.1574.

## cross_asset Layer Hurts h=1

The cross_asset layer produces market-wide features (log_vix_d/w/m, log_vix_rv_ratio_d, treasury_slope). Adding it degraded h=1 from 0.1574 to 0.1603. These features are identical across all symbols on the same date, providing no cross-sectional signal and competing for splits with more informative per-symbol features.

**Recommendation:** Exclude cross_asset from the main LightGBM config. If market-wide features are needed, create interactions with per-symbol data (e.g., `treasury_slope * symbol_beta`).

## Winning Hyperparameters (h=1)

Result: **QLIKE 0.1574, DM stat 2.85, p=0.0044** (statistically significant over HAR at h=1).

```yaml
model:
  params:
    n_estimators: 5000
    early_stopping_rounds: 150
    learning_rate: 0.01
    num_leaves: 16
    max_depth: 4
    min_child_samples: 150
    feature_fraction: 0.8
    bagging_fraction: 0.8
    bagging_freq: 3
    reg_lambda: 5.0
    reg_alpha: 0.1
    val_fraction: 0.15
    val_purge_gap: 10
cv:
  purge_gap: 10
  train_size: 504
  test_size: 126
feature_layers: [iv_surface, har_core, asymmetry, noise_robust, options, calendar]
training_mode: pooled
```

Key design choices:
- **Low capacity** (16 leaves, depth 4): prevents overfitting with ~51 features and 504*21 = ~10k training rows
- **Short training window** (504 days = ~2 years): keeps model adaptive to regime changes
- **Strong regularization**: lambda=5, alpha=0.1, min_child=150
- **No cross_asset layer**: simpler feature set, all high-signal per-symbol features

## h=5 and h=22 Still Underperform

LightGBM loses to HAR at h=5 (-1237 bps) and h=22 (-1601 bps).

### Root Causes (diagnosed 2026-05-22, research session)

1. **Training window too short (MOST IMPACTFUL):** train_size=504 gives first fold only 10,584 rows for 54 features (ratio 196:1). CSV (2023) trains on 145K rows. HAR with 3 features has ratio 3,528:1 and is far more stable. Fix: train_size=1260 for h=22 gives 26,460+ rows.

> **UPDATE (2026-05-27):** train_size=1260 tested in trial-010 -- ALL variants worse (best 0.2387 vs HAR 0.2086). The root cause was feature noise, not data quantity. train_size=504 remains optimal. See "h=22 Optimization Campaign" section below.

2. **No horizon-specific feature selection:** Same 54 features used for all horizons. Ch10 Table 1 shows h=22 is dominated by VRP/term slope (not daily jumps/skew). Many daily features are pure noise at h=22, diluting tree splits away from the real signal.

3. **Missing monthly IV x RV interactions:** Only `atm_iv_x_log_rv_d` (daily) is computed. Missing `atm_iv_x_log_rv_m` which has r=-0.635 with h=22 target and captures "IV elevated relative to monthly volatility regime." This is THE feature trees need to split on at h=22.

4. **VRP signal diluted by feature count:** VRP partial r with h=22 target controlling for log_rv_m = 0.32. That's strong incremental signal. But with 54 features and min_child=150, the tree rarely gets to exploit this split in early folds.

5. **Missing standard features (volume, momentum):** No volume ratio or lagged equity returns (available from OHLCV data already in parquets). CSV (2023) includes these.

### Data Integrity: Better Than Expected

- RK is fully populated (0% NaN, backfill completed).
- Overnight return is clean (split-adjustment issue fixed, max |0.23| on NVDA).
- Per-symbol IV for all 21 symbols (not proxied from SPX).
- Total pooled rows: 52,811. Adequate for train_size=1260.
- No proxies detected anywhere.

## IV Alignment Fix (2026-05-27)

- Prediction point = close of day T (rv[T] is used as feature, only available at close T)
- IV[T] is available at close T (options + equities close same time)
- Original shift(1) was overcautious: caused VRP to mix IV[T-1] with rv[T]
- Fix: removed shift(1) from IVSurfaceLayer. All IV features now use same-day IV[T].
- Impact by horizon: strongest at h=1 (IV freshness matters for short-term forecast), weakest at h=22 (autocorrelation of IV makes T-1 a good proxy anyway)
- Combined with tree_expansion: QLIKE dropped from 0.1574 to 0.1489 at h=1 (+85 bps)
- Affected features: all 25 options-layer columns, plus VRP/interaction alignment now correct

## tree_expansion Layer (2026-05-27)

**Result: +31.5 bps mean QLIKE improvement, 5/5 seeds win.** Added to LOCKED config.

### What It Does

Applies two transformations to 35 expandable base features (those matching prefixes like `log_rv_`, `log_rs_`, `vrp_`, `iv_skew_`, `iv_term_`, etc.):
1. `_change` = X[t] - X[t-1] (daily difference)
2. `_zscore` = (X[t] - rolling_mean_63d) / rolling_std_63d (standardized level)

Total: 70 new features (35 base x 2 transforms), taking model from 58 to 128 features.

### Why It Works (Theoretical Foundation)

**Trees cannot construct these features from raw levels.** A decision tree only sees X[t] at each split point. It cannot compute X[t] - X[t-1] (requires memory of yesterday) or (X[t] - mean) / std (requires distributional context). These are mathematically unreachable transformations for any tree-based model, yet they carry real volatility-forecasting signal:
- "IV dropped 2 z-scores today" predicts mean-reversion
- "RV changed by +0.3 log-units" captures momentum/regime transitions

### Empirical Evidence

**Multi-seed pooled test (21 symbols, train<=2022-06-30, test>2022-06-30):**

| Seed | Base QLIKE (58 feats) | Expanded QLIKE (128 feats) | Delta (bps) |
|------|----------------------|---------------------------|-------------|
| 42 | 0.140495 | 0.138601 | +18.9 |
| 123 | 0.140983 | 0.136251 | +47.3 |
| 456 | 0.139500 | 0.137122 | +23.8 |
| 789 | 0.142592 | 0.139395 | +32.0 |
| 2024 | 0.140537 | 0.136963 | +35.7 |
| **Mean** | **0.140821** | **0.137667** | **+31.5** |

**Feature importance breakdown (seed=42):**
- Expansion features = 8.8% of total model gain (proportional to 55% of columns)
- All 70/70 expansion features used (>0 gain) — diffuse but non-zero contribution
- Top expansion features: `vix_x_log_rv_d_zscore`, `vix_x_log_rv_w_change`, `log_atm_iv_m_change`
- Fewer boosting iterations needed (6084 vs 6534) — expansion HELPS generalization

**Pipeline CV results (trial-009, proper expanding-window):**

| Horizon | Trial-009 | Old LOCKED | HAR | vs Old | vs HAR |
|---------|-----------|-----------|-----|--------|--------|
| h=1 | 0.1489 | 0.1574 | 0.1601 | +85 bps | +112 bps |
| h=5 | 0.1377 | 0.1527 | 0.1390 | +150 bps | +13 bps |
| h=22 | 0.2171 | 0.2420 | 0.2100 | +249 bps | -71 bps |

### Key Insight: h=5 Fix

The old LOCKED config LOST to HAR at h=5 by 1237 bps. Trial-009 now WINS by +13 bps. The zscore features capture mean-reversion dynamics that matter at weekly horizons — a regime where daily features are noisy but the standardized version (how far from normal?) is highly predictive.

### Cost

~17% more rows lost to warm-up (zscore uses 63-day rolling window). Training sample: 43.5k rows (vs 52k without expansion). Acceptable tradeoff.

### Configuration

```yaml
feature_layers: [iv_surface, har_core, asymmetry, noise_robust, options, calendar, tree_expansion]
# tree_expansion must be LAST (needs base_features from prior layers)
# _needs_base_features = True flag triggers the pipeline to pass base features
```

### Recommended Fix: Horizon-Specific Tournament

```yaml
# h=5 config changes:
cv:
  train_size: 756  # 3 years
model:
  params:
    num_leaves: 16
    min_child_samples: 100

# h=22 config changes:
cv:
  train_size: 1260  # 5 years
feature_layers: [iv_surface, har_core, asymmetry, noise_robust, options, calendar]
# Plus: add atm_iv_x_log_rv_w, atm_iv_x_log_rv_m in options layer
# Plus: feature pre-selection (drop daily-noise features at h=22)
model:
  params:
    num_leaves: 8  # Extremely conservative for smooth targets
    min_child_samples: 200
    max_depth: 3
```

## GPU Is Useless for Custom Objectives (2026-05-27)

**Critical finding:** LightGBM's GPU acceleration (CUDA or OpenCL) provides ZERO benefit when using a custom objective function (like our QLIKE). The reason:

1. Custom objectives compute gradients/hessians **in Python on CPU** (numpy)
2. Tree building happens on GPU
3. Every boosting round requires a CPU-to-GPU data transfer (gradients) and GPU-to-CPU transfer (predictions)
4. This sync barrier per round completely negates GPU tree-building speedup
5. On a 208-core machine, CPU-only training is significantly FASTER than GPU

**Rule:** Never use `device_type='cuda'` or `device_type='gpu'` with custom objectives. GPU only helps with built-in objectives (`regression`, `binary`, etc.) where gradients are also computed on GPU.

**Evidence:** H100 experiment hung for hours with `device_type='cuda'`. Removing GPU and using CPU-only completed training in seconds.

## Thread Count: 8 is Optimal (2026-05-27)

**Critical finding:** On a 208-core H100 node, `num_threads=8` is empirically optimal for LightGBM with custom QLIKE objective, across ALL tested data sizes from 500 to 25,000 rows.

### Benchmark Results (custom QLIKE objective, 200-500 boosting rounds)

| Data size | 4 threads | 8 threads | 16 threads | 32 threads | 64 threads | 208 threads |
|-----------|-----------|-----------|------------|------------|------------|-------------|
| 500 rows  | 0.20s     | **0.18s** | 0.21s      | 0.40s      | 0.78s      | 30s+        |
| 1,500 rows| **0.56s** | 0.61s     | 0.68s      | 0.71s      | 1.01s      | minutes     |
| 2,000 rows| 0.59s     | **0.42s** | 0.59s      | 0.74s      | -          | 4+ min      |
| 5,000 rows| 0.63s     | **0.54s** | 0.59s      | 0.63s      | 1.00s      | -           |
| 15,000 rows| 0.61s    | **0.45s** | 0.48s      | 0.65s      | 1.37s      | -           |
| 25,000 rows| 0.67s    | **0.54s** | 0.78s      | 0.81s      | -          | -           |

**Why more threads hurts:** OpenMP barrier synchronization. With 208 threads on 2000 rows, each thread gets ~10 rows per histogram bin. The sync cost between threads completely dominates the computation. The relationship is inverse-U: performance peaks at 4-8 threads then degrades steeply.

**Custom vs built-in objective:** Similar scaling behavior. The custom objective itself adds negligible overhead (vectorized numpy). The bottleneck is tree building parallelism, not gradient computation.

**Rule:** Always set `num_threads=8` in LightGBM params. NEVER use `os.cpu_count()`.

## Optuna Parallelism: n_jobs=4 Max (2026-05-27)

**Finding:** On a 208-core system with 8 threads/trial:
- `n_jobs=4` (32 cores total): **works reliably**, ~25s/trial
- `n_jobs=8` (64 cores total): runs but is slower due to L3 cache contention
- `n_jobs=20` (160 cores total): **segfaults** (EXIT:139) due to OpenMP thread pool explosion

**Root cause of segfault:** Each LightGBM instance creates its own OpenMP thread pool. With n_jobs=20 and 8 threads each, that's 160 OpenMP threads plus Python + Optuna threads. The system's `ulimit -u` or libgomp stack reservation exceeds available resources and the process is killed.

**Rule:** Use `n_jobs=4` for Optuna HPO with LightGBM custom objectives. Theoretical max is `cores // 8 = 26` but cache and memory contention make anything above 4-8 counterproductive.

**Performance projection (200 trials, n_jobs=4):**
- Single trial with 3-fold inner CV: ~25s (3 fits of 0.5s each + overhead)
- 200 trials / 4 parallel: ~1250s / 4 = ~5 minutes (with pruning, faster)
- Previous state: infinite hang at `num_threads=208`

## LightGBM Thread Safety (2026-05-27)

**Critical finding:** `lgb.train()` is NOT thread-safe for parallel instances sharing the same process. Concurrent calls can trigger fatal C++ assertions that call `abort()`:

```
LightGBM Fatal: [LightGBM] [Fatal] num_features > 0
```

These assertions kill the calling thread without raising a Python exception. In Optuna's ThreadPoolExecutor, this silently deadlocks the entire trial pool (worker dies, future never completes, `study.optimize()` hangs forever).

**Mitigation:**
1. `feature_pre_filter=False` prevents the most common assertion
2. `catch=(Exception,)` in `study.optimize()` catches Python-level errors but NOT C++ aborts
3. Guard against impossible param combos: check `min_child_samples < n_train` before fitting
4. Keep n_jobs moderate (4) to reduce collision probability

## Optuna 4.x API Change (2026-05-27)

`JournalFileBackend` was renamed to `JournalFileStorage` in Optuna 4.8.0. The old name was removed entirely (not deprecated). Use:

```python
# Correct (Optuna 4.8+):
journal_backend = optuna.storages.JournalFileStorage(str(journal_path))
storage = optuna.storages.JournalStorage(journal_backend)
```

## h=22 Optimization Campaign (Trials 010-014, 2026-05-27)

Systematic ablation and feature engineering campaign to beat HAR at the monthly horizon. 5 trials, ~40 LightGBM variants tested.

### What Worked

| Finding | Evidence | Impact |
|---------|----------|--------|
| Feature ablation methodology | trial-011 (8 variants, drop-one-group) | Identified noise vs signal definitively |
| Drop calendar features | trial-011: +61 bps when removed | Calendar is pure noise at h=22 |
| Drop IV interactions (atm_iv_x_log_rv_*) | trial-011: +25 bps when removed | Per-symbol IV interactions are h=1/h=5 signal but h=22 noise |
| Slow learning (lr=0.005) | trial-012: pruned_slow = 0.2068 vs control pruned = 0.2084 | Consistent +16 bps from patience |
| Combined pruning | trial-012: 0.2068 (+18 bps vs HAR, first LightGBM h=22 win) | Removing two noise groups stacks additively |
| path_smooth=5 | trial-012: 0.2078 (+8 bps vs HAR) | Monotone constraint regularization helps slightly |

### What Did NOT Work

| Finding | Evidence | Impact |
|---------|----------|--------|
| Longer training window (train_size=1260) | trial-010: ALL 4 variants WORSE than HAR (best 0.2387) | More data does not help for nonstationary vol |
| Long-memory features (60d/90d lags) | trial-014: best = 0.2086 (ties HAR), control = 0.2160 (-74 bps) | Extra features add noise; 60d/90d redundant with HAR monthly lag |
| Deep models (31 leaves) at h=22 | trial-014: lgbm_deep_slow = 0.2230, DM p=0.039 SIGNIFICANTLY worse | More capacity = more overfitting on noisy monthlies |
| Uniform feature config across horizons | trial-013: h=1 FAIL (-44 bps), h=5 FAIL (-79 bps) using h=22 pruning | IV interactions and calendar are h=1/h=5 signal but h=22 noise |
| Aggressive daily feature removal (monthly-only) | trial-012: lgbm_monthly_features = 0.2208 (-122 bps vs HAR) | Too few features; trees need some daily signal even at h=22 |

### Key Signals at h=22 (from trial-011 ablation)

| Feature Group | Drop Cost (bps) | DM p-value | Interpretation |
|---------------|-----------------|------------|----------------|
| VVIX (vvix_level, vvix_rv_ratio) | +72 bps lost | 0.007 | STRONGEST signal -- vol-of-vol predicts monthly regime |
| noise_robust (rk_rv5_gap, noise_ratio) | +34 bps lost | 0.12 | Microstructure quality matters for longer horizons |
| har_core (log_rv_d/w/m, rq) | +36 bps lost | varies | Baseline features still dominant |
| options (vrp, skew, term_slope) | +15 bps lost | >0.2 | VRP signal but diluted by other options features |
| calendar (fomc, earnings, opex) | -61 bps GAINED | n/a | Pure noise at h=22 -- ALWAYS drop |
| IV interactions (atm_iv_x_log_rv_*) | -25 bps GAINED | >0.3 | Noise at h=22 -- drop for monthly horizon |

### Corrected Root Cause Analysis

Original hypothesis (pre-trial-010): "train_size too short" and "need more features for h=22."

**Both wrong.** The actual bottleneck is:
1. **Feature noise** -- too many irrelevant features dilute tree splits (calendar, IV interactions add ~86 bps of noise)
2. **Model speed** -- lr=0.01 is too aggressive for the smoother h=22 target; lr=0.005 gives trees more granular steps
3. **Non-stationarity** -- longer windows include more regime changes, confusing the model (train_size=504 is correct)

### Best h=22 Config (pruned_slow)

```yaml
feature_layers: [iv_surface, har_core, asymmetry, noise_robust, options, tree_expansion]
# NOTE: NO calendar, NO long_memory
drop_features: [atm_iv_x_log_rv_d, atm_iv_x_log_rv_w, atm_iv_x_log_rv_m]
model:
  params:
    learning_rate: 0.005
    n_estimators: 5000
    num_leaves: 16
    min_child_samples: 150
    early_stopping_rounds: 150
    path_smooth: 5  # optional, +8 bps
```

### Horizon-Specific Strategy (Updated 2026-06-01, corrected for COVID bias)

| Horizon | Config | Key Features | Best QLIKE |
|---------|--------|-------------|------------|
| h=1 | trial-023 (23sym, 504d) | All layers + base_model=har_iv, drop abs_ret_d | **0.1391** (full OOS incl COVID) |
| h=5 | trial-023 (23sym, 504d) | All layers + base_model=har_iv | **0.1148** (full OOS incl COVID) |
| h=22 | trial-029b (23sym, 504d) | Pruned calendar/IV interactions, lr=0.005, n_est=8000 | **0.1833** (+39 bps vs trial-023) |

## HAR-IV Dominance: LightGBM Failure Diagnosed (2026-05-27)

### The Breakthrough

A 4-parameter OLS model (`har_iv`) beats 128-feature LightGBM at all horizons:

| Model | h=1 | h=5 | h=22 | Params |
|-------|-----|-----|------|--------|
| atm_iv_implied | 0.1997 | 0.1447 | 0.1925 | 0 |
| har | 0.1602 | 0.1359 | 0.2087 | 3 |
| **har_iv** | **0.1498** | **0.1187** | **0.1844** | **4** |
| lightgbm | 0.1489 | 0.1365 | 0.2079 | 128 feat, ~6k trees |

`har_iv` = `y = c + b1*log_rv_d + b2*log_rv_w + b3*log_rv_m + b4*log_atm_iv_d` (OLS)

Implementation: `src/volforecast/models/har_family.py`, registered as `har_iv`.
Requires: `iv_surface` + `options` layers (for `log_atm_iv_d`).

### Why LightGBM Fails to Learn the HAR-IV Pattern

LightGBM HAS `log_atm_iv_d` as one of 128 features yet cannot replicate the simple linear combination. Root causes:

1. **Split dilution:** With 128 candidate features and `feature_fraction=0.8`, each tree only sees ~102 features. `log_atm_iv_d` competes with 101 correlated alternatives for top splits. In a linear model, IV gets its optimal weight directly.

2. **Piecewise-constant approximation:** Trees approximate the continuous linear relationship `b4*log_atm_iv_d` with step functions (16 leaves, depth 4). Each step introduces quantization error. The more features, the coarser each individual feature's approximation.

3. **Bagging averages away the signal:** `bagging_fraction=0.8` means each tree trains on 80% of data. Across 5000 trees, IV's contribution is averaged/smoothed rather than optimally weighted.

4. **min_child_samples=150:** Forces each leaf to represent 150+ obs. For the IV signal (continuous, linear), this is crude binning that loses resolution.

5. **Interaction features compete:** The tree has `atm_iv_x_log_rv_d/w/m` interactions that partially capture what the linear IV term does, further reducing IV's marginal importance in pure-split terms.

### ATM IV Is the Correct h=22 Benchmark

Naive ATM IV (zero parameters, formula: `2*log(iv/100) - log(252)`) achieves:
- h=1: 0.1997 (worst — IV is blunt for daily forecasts)
- h=5: 0.1447 (beats LightGBM 0.1365 by... wait no, HAR beats IV at h=5)
- h=22: **0.1925** (beats HAR 0.2087 by 775 bps, beats LightGBM 0.2079 by 800 bps)

**Why IV wins at h=22:** 1-month ATM IV IS the option market's consensus on 22-day realized vol. It aggregates all information (order flow, positioning, events, cross-asset) better than any backward-looking model. The VRP bias (IV > RV) helps under QLIKE's asymmetric penalty.

**Model hierarchy at h=22:** HAR-IV (0.1844) > atm_iv (0.1925) > har (0.2087) ≈ lightgbm (0.2079)

### Implications for LightGBM Strategy

Prior approach: throw 128 features at LightGBM and hope it finds the signal.
Correct approach: **start from HAR-IV and only add tree corrections for residuals.**

Concrete fixes:
1. Use `init_score = HAR-IV prediction` (LightGBM starts from optimal linear forecast, learns nonlinear corrections)
2. Reduce feature set to residual-predictive features only (remove HAR lags and raw IV that the init_score already captures)
3. For h=22: HAR-IV captures 90%+ of the signal. Trees should only add 5-10% correction (regime shifts, tail events)

### Ensemble Blending (Also Superseded by HAR-IV)

Walk-forward 50/50 blend (HAR + LightGBM) at h=22: QLIKE 0.2108 (+DM p=0.000 vs HAR). Regime-dependent: low-vol → 95% LightGBM, high-vol → 80% HAR. But HAR-IV alone (0.1844) beats the best blend (0.2108) by 1264 bps. The blend research is academically interesting but practically superseded.

### Updated Horizon Strategy (Corrected 2026-06-01 — post COVID-bias discovery)

| Horizon | Best Model | QLIKE | Architecture |
|---------|-----------|-------|--------------|
| h=1 | lgbm_hariv_init (23sym, 504d) | 0.1391 | HAR-IV init_score + tree corrections, 2yr window (trial-023) |
| h=5 | lgbm_hariv_init (23sym, 504d) | 0.1148 | HAR-IV init_score + tree corrections, 2yr window (trial-023) |
| h=22 | lgbm_hariv_init (23sym, 504d) | 0.1833 | HAR-IV init + pruned features + slow lr, 2yr window |

> Note: trial-030b results (0.1155/0.0700) are RETRACTED. They measured COVID exclusion, not model improvement. The correct best h=1 QLIKE is 0.1391 (trial-023, includes COVID in test).
> On the COVID-free common period (2022-2024), both 504d and 1764d achieve 0.1155.

## init_score Architecture: HAR-IV as LightGBM Starting Point (Trial-020, 2026-05-27)

### The Pattern

LightGBM's `init_score` parameter provides a per-row starting prediction. Instead of boosting from the training mean (scalar), the tree starts from HAR-IV predictions (vector). The tree then learns ONLY the residual -- nonlinear corrections that HAR-IV cannot capture.

**Implementation:** `base_model` parameter in `LightGBMVolModel.__init__()` (`src/volforecast/models/lightgbm.py`):
- `fit()`: fits the base model on training data, generates per-row init_score vector
- `predict()`: returns `base_model.predict(X) + tree.predict(X)`
- NaN fallback: where base model returns NaN (missing IV), substitutes scalar mean
- Configurable: `base_model` accepts any registered model name (e.g. `har_iv`, `har_iv_vvix`)

**YAML config:**
```yaml
model:
  name: lightgbm
  params:
    base_model: har_iv       # <-- only addition needed
    learning_rate: 0.005     # lower LR -- tree needs smaller corrections
    # ... rest unchanged from trial-015
```

### Results (Trial-020)

| Model | h=1 | h=5 | h=22 |
|-------|-----|-----|------|
| har | 0.1602 | 0.1359 | 0.2087 |
| har_iv | 0.1498 | 0.1187 | 0.1844 |
| lgbm_standalone | 0.1489 | 0.1365 | 0.2079 |
| **lgbm_hariv_init** | **0.1412** | **0.1148** | 0.1878 |

### Why It Works at h=1/h=5

1. HAR-IV captures the linear signal (70-80% of variance)
2. Tree learns threshold interactions (e.g., "when IV drops 2 sigma AND RV is elevated, mean reversion")
3. Tree learns regime effects (calm vs crisis produce different correction magnitudes)
4. Tree corrects HAR-IV's systematic biases (e.g., post-earnings under-reaction)
5. Lower learning rate (0.005) prevents overshooting the small residual corrections

### Why It Fails at h=22

1. HAR-IV captures 95%+ of the signal at monthly horizons (IV IS the market's 22-day forecast)
2. The remaining 5% residual is small relative to tree estimation noise
3. More boosting rounds on tiny residuals = overfitting (-184 bps)
4. Monthly noise floor: DM tests on h=22 LightGBM are never significant (trial-017: all p > 0.6)
5. Correct h=22 strategy: pure HAR-IV, or regime-conditional blend (HAR-IV in crisis, tree in calm)

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| Keep all 128 features visible to tree | Tree can learn nonlinear interactions even with features in HAR-IV |
| Use lr=0.005 (not 0.01) | Smaller corrections needed on good baseline; prevents overshooting |
| NaN fallback to scalar mean | HAR-IV returns NaN when IV missing; tree must still train on those rows |
| No separate registry model | Simpler: one new param in existing LightGBMVolModel class |
| Configurable base_model string | Can swap to `har_iv_vvix` or other variants without code changes |

## Return/Activity Features Discovery (Trial-023, 2026-05-28)

**Hypothesis:** HAR-IV residual correlates with 5 missing features (|r| > 0.05 at h=1).
**Method:** Leave-one-out ablation with 7 LightGBM variants (all using base_model=har_iv).
**Result:** QLIKE 0.1391 at h=1 -- NEW BEST (+149 bps over trial-020).

### Feature Contributions (bps cost of dropping)

| Feature | h=1 | h=5 | h=22 | Verdict |
|---------|-----|-----|------|---------|
| vol_anomaly (tick count deviation) | +55 | +42 | +29 | HELPS all horizons |
| ret_5d (5-day cumulative return) | +1 | +54 | +45 | HELPS h=5/h=22 |
| signed_return expansion (_change/_zscore) | -18 | +61 | +45 | HELPS h=5/h=22 |
| abs_ret (daily + weekly) | +21 | -12 | +7 | Helps h=1/h=22 |
| vix_change_x_abs_ret | +3 | -22 | +66 | h=22 only |

### Key Architectural Findings

- **abs_ret_w (weekly smoothed) > abs_ret_d (daily) at h=1** by +34 bps. The daily version adds noise that tree expansion cannot compensate for. At h=22 the opposite holds (-67 bps) -- daily granularity matters for longer horizons.
- **vol_anomaly is the strongest universal new feature** -- helps at ALL three horizons. Encodes "today's tick activity is unusual relative to recent history" which predicts next-day volatility spikes.
- **Horizon-specific inclusion needed for vix_change_x_abs_ret** -- pure h=22 signal (+66 bps) but slightly hurts h=5 (-22 bps).
- **signed_return expansion HURTS at h=1** (-18 bps) -- the tree was already using signed_return_d as a raw level feature. Adding _change and _zscore derivatives introduces noise at short horizons but helps at h=5/h=22 where mean-reversion dynamics dominate.

### Implementation Location

- `abs_ret_d`, `abs_ret_w`, `ret_5d` --> `features/asymmetry.py` (AsymmetryLayer)
- `vol_anomaly` --> `features/noise_robust.py` (NoiseRobustLayer)
- `vix_change_x_abs_ret` --> `features/options.py` (OptionsLayer)
- Tree expansion prefixes added: `signed_return`, `abs_ret`, `ret_5d`, `vol_anomaly`, `vix_change_x_abs_ret`

### Interaction Effect: Feature Drops NOT Additive (Trial-024)

Combining two individually beneficial h=1 drops (abs_ret_d + signed_return expansion) produced WORSE results than either alone:

| Variant | h=1 QLIKE |
|---------|-----------|
| lgbm_abs_ret_w_only (drop abs_ret_d only) | 0.1391 |
| lgbm_drop_signed_ret (drop expansion only) | 0.1393 |
| lgbm_combined_best (drop both) | 0.1397 |
| lgbm_all_new (control, drop neither) | 0.1396 |

**Lesson:** signed_return_d and abs_ret_d are complementary -- the tree uses whichever is present as fallback for the other. Removing both creates a blind spot. Do NOT assume feature ablation improvements compose additively.

## Expanded Universe + Per-Horizon CV (Trials 025-029, 2026-06-01)

### Universe Expansion: 21 -> 23 Symbols

Added JPM, QQQ to pooled training (META excluded due to tick/IV date mismatch: 644 tick rows vs 2609 IV rows).

**Finding:** More symbols improve LightGBM, but ONLY when paired with longer training windows. With train_size=504 (2yr), adding symbols HURTS because the signal-per-fold is diluted. With train_size>=756, the extra cross-sectional variation helps.

### Per-Horizon CV train_size: The Breakthrough (Trial-029)

**Problem:** h=1/h=5 benefit monotonically from longer windows (more data = better generalization). h=22 collapses with long windows (fewer OOS folds = high variance, regime confusion).

**Solution:** Implemented `cv_for_horizon(h)` method in `ExperimentConfig` (`config.py`). The `horizon_overrides` YAML key now supports per-horizon `cv` settings (train_size, test_size, purge_gap, n_splits, method).

**Implementation:** `config.py:cv_for_horizon(h)` + 3 call sites in `runner.py` (pooled purge_gap, pooled CV construction, non-pooled CV construction).

### train_size Scaling Law (Complete Sweep, 2026-06-01)

> **RETRACTED (2026-06-01): The "scaling law" below is a COVID exclusion artifact.**
> On the common test period (2022-01-20 to 2024-07-24), 504d and 1764d produce
> IDENTICAL QLIKE (0.1155 for h=1). The apparent improvement was entirely because
> longer train_size pushes the first OOS test date past COVID (Feb-Jun 2020).
> COVID inflates 504d full-OOS QLIKE by ~52 bps. The "monotonic improvement" was
> measuring test-set composition, not model quality.
>
> Transition point: train_size >= 1512 excludes COVID from test entirely.
> Fair comparison (same 2022-2024 period): 504d = 1764d = 0.1155.

| train_size | h=1 QLIKE | h=5 QLIKE | h=22 QLIKE | ~Folds | 1st Test Date | COVID in Test? |
|------------|-----------|-----------|------------|--------|---------------|----------------|
| 504d (2yr) | 0.1391* | 0.1148* | 0.1872 | ~15 | 2017-01-18 | YES |
| 756d (3yr) | 0.1358* | 0.1141* | 0.2009 | ~12 | 2018-01-18 | YES |
| 1008d (4yr) | 0.1339* | 0.1041* | 0.2016 | ~10 | 2019-01-18 | YES |
| 1260d (5yr) | 0.1271* | 0.0990* | n/a | ~8 | 2020-01-21 | YES (edge) |
| 1512d (6yr) | 0.1230* | 0.0819* | n/a | ~6 | 2021-01-20 | NO |
| 1764d (7yr) | 0.1155* | 0.0700* | n/a | ~4-5 | 2022-01-20 | NO |
| 2016d (8yr) | 0.1216* | 0.0693* | n/a | ~2-3 | 2023-01-20 | NO |

*These QLIKE numbers are NOT comparable across rows. Each row evaluates on a DIFFERENT test period. Rows with COVID in test have inflated QLIKE (harder test). Numbers marked * are confounded.

**CORRECT interpretation:** train_size does NOT improve model quality on a fixed test period. The "scaling law" is a measurement artifact from non-overlapping test sets. On the common 2022-2024 period, all configs produce the same QLIKE (~0.1155 for h=1).

**Implication:** train_size=504 remains the correct default. More training data provides no benefit for LightGBM with HAR-IV init_score (the linear signal is stable, and tree corrections do not improve with more historical context).

**COVID impact quantified:**
- COVID period (Feb-Dec 2020) QLIKE: 0.1815 (5335 rows)
- Non-COVID QLIKE: 0.1393 (38133 rows)
- COVID inflates 504d full-OOS QLIKE by: 51.8 bps (0.1393 -> 0.1445)

### Optimal h=22 train_size

| train_size | h=22 QLIKE | vs baseline |
|------------|-----------|-------------|
| 504d | **0.1833** | +39 bps |
| 756d | 0.1844 | +28 bps |
| 1008d | 0.2016 | -144 bps |

**Optimal: 504d (2 years).** Shorter windows keep the model adaptive to recent volatility regimes. Monthly targets are inherently noisier -- more data amplifies regime confusion rather than helping.

### Corrected Root Cause: train_size=1260 Appeared to Work (RETRACTED)

Earlier finding (trial-010, 2026-05-27): "train_size=1260 ALL variants WORSE (best 0.2387 vs HAR 0.2086)."
Later finding (trial-029b/030b, 2026-06-01): "1260d/1764d improves h=1/h=5 with har_iv init_score."

**RETRACTION:** The apparent improvement from longer windows was a COVID exclusion artifact. On the same test period (2022-2024), train_size=504 and train_size=1764 produce identical QLIKE. The init_score theory was a rationalization of a measurement error.

**Updated rule:** train_size=504 remains correct for ALL horizons. Longer windows do NOT improve model quality; they only change WHICH dates are in the test set.

### LOCKED Config: trial_030b_7yr_short_horizons_LOCKED.yaml (RETRACTED)

> **RETRACTED:** This config's apparent superiority was a COVID exclusion artifact.
> On the common test period (2022-2024), it matches train_size=504 exactly.
> Reverted to trial-029b (1260d) or trial-023 (504d) as the true best.
> The per-horizon CV mechanism is still valid; only the 1764d window is debunked.

```yaml
cv:
  train_size: 1764  # 7yr for h=1/h=5 (optimal from scaling sweep)
  test_size: 126
horizon_overrides:
  22:
    cv:
      train_size: 504  # 2yr for h=22
    model:
      params:
        n_estimators: 8000
        early_stopping_rounds: 250
        learning_rate: 0.005
        drop_features: [abs_ret_d, abs_ret_d_change, abs_ret_d_zscore,
                       day_of_week, month, days_to_fomc, days_to_nfp, days_to_opex]
```

### Key Lessons

1. **Per-horizon CV is essential.** A single train_size cannot serve all horizons. Short horizons want maximum data; monthly wants regime-freshness.
2. **Universe expansion helps with sufficient data.** 23 symbols + longer windows = more rows/fold for h=1/h=5. The extra cross-sectional variation provides unique signal.
3. **RETRACTED: "train_size scaling plateaus at data boundary."** The apparent monotonic improvement was a COVID exclusion artifact. On a fixed test period, all train_sizes produce equivalent QLIKE. train_size=504 remains the default.
4. **DM significance achieved at h=22** (p=1.4e-06). LightGBM now beats HAR-IV at h=22 with the right config. This overturns the earlier finding that "tree corrections hurt at h=22."
5. **Minimum fold threshold: 4-5 folds.** Below this, QLIKE estimates are unreliable. This sets a hard ceiling on train_size given dataset length.
6. **COVID is the dominant test-set confound.** Feb-Jun 2020 inflates QLIKE by ~52 bps. Any evaluation that compares configs with different OOS periods is invalid unless COVID coverage is controlled for.

## CV Integrity Audit (2026-06-01)

Full lookahead bias audit performed and passed. Key findings:

| Vector | Verdict | Evidence |
|--------|---------|----------|
| Outer purge gap | CLEAN | `effective_purge = max(cv_cfg.purge_gap, h)` |
| init_score (outer) | CLEAN | base_model fit within fold on X_train only |
| Feature computation | CLEAN | All rolling/shift operations are backward-looking |
| Val split ordering | CLEAN | Temporal split, not random |
| Val purge gap | CLEAN | Bumped to max(val_purge_gap, h) per horizon |
| DM test | CLEAN | Computed on true OOS predictions only |
| Expanding window | CLEAN | Starts at min_train_size, expands forward only |
| **Test-period comparability** | **CONFOUNDED** | Different train_sizes evaluate on different date ranges. COVID excluded for train_size >= 1512. Cross-config QLIKE comparisons invalid unless restricted to common dates. |

**Minor issue (low severity):** HAR-IV base model is fit on full fold-training data including the 15% val portion before the train/val split. Impact: negligible (4-param OLS coefficients change by <0.1% with 15% more data). Only affects early-stopping round selection, not OOS evaluation.

**Major issue (discovered post-audit):** Expanding-window CV with different train_sizes produces non-overlapping test sets. Comparing QLIKE across configs with different train_sizes is invalid because each config is tested on a different time period with different difficulty. COVID (Feb-Jun 2020) is the dominant confound: its 52 bps QLIKE penalty only applies to configs where it falls in the test set.

**Conclusion:** The pipeline itself is mechanically correct (no lookahead), but cross-config comparisons require restricting to a common test period. The "scaling law" finding was invalidated by this oversight.

## Feature Removal: Don't Do It (Trial-059, 2026-06-19)

**Hypothesis tested:** Removing "useless" features (sparse calendar dummies, pre-computed interactions redundant for trees, weak-signal expansions) would improve or maintain QLIKE by reducing noise.

**Result: Feature removal HURTS at h=1 and h=5. Neutral-to-harmful at h=22.**

| Removed | Count | h=1 delta (bps) | h=5 delta (bps) | h=22 delta (bps) |
|---------|-------|-----------------|-----------------|------------------|
| Calendar dummies (day_of_week, month, quarter_end, year_end + expansions) | -12 | **-7** | **-4** | +3 |
| + Manual interactions (atm_iv_x_log_rv, vix_x_log_rv + vix expansions) | -32 total | **-16** | **-14** | **-15** |

### Why the "redundant interactions" theory was wrong

Pre-computed products (`atm_iv_x_log_rv_d`) were expected to be redundant because LightGBM can discover interactions via sequential splits. But with `max_depth=4` and `num_leaves=16`, the tree has limited budget — a pre-computed product is accessible in ONE split, while the equivalent interaction requires 2 correlated splits that may never co-occur at the right depth. The products act as "interaction shortcuts" for shallow trees.

### Rules derived

1. **Never remove features from the champion.** `min_child_samples=150` + `reg_lambda=5` already prevents the tree from overfitting to noise features.
2. **Calendar dummies have horizon-dependent value:** useful at h=1/h=5 (event timing matters for short-term vol), negligible at h=22.
3. **Pre-computed interactions help shallow trees:** With depth ≤ 4, explicit products are NOT redundant — they reduce required split depth for interaction signal.
4. **Adding signal > removing noise.** The 128-feature champion is stable; improvement comes from new informative features, not pruning.

