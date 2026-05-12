# ML Realized Volatility Forecasting: Development Plan

**Project:** GS ML Internship, ~20 weeks (May--Sep 2026)
**Priority ordering:** Trading signal > Academic rigor > Model novelty
**Dev universe:** SPY, AAPL, MSFT, NVDA, XOM, JPM, IWM, ES (8 symbols)
**Full universe:** 35 instruments (30 equities + 4 ETFs + 1 E-mini)

---

## M1: Fix Foundation

**Objective:** Eliminate correctness bugs that invalidate all downstream results. Unblock Layer 2--5 implementation.

**Prerequisites:** None.

### Tasks

#### 1.1 Fix CV purge gap enforcement

- **File:** `src/volforecast/utils/cv.py`
- **Change:** Add validation in each splitter that enforces `purge_gap = max(purge_gap, h)` per horizon. Applied dynamically inside the training loop, not as a global config.
- **Tests:**
  - `purge_gap=5, horizon=22` produces splits with gap >= 22
  - `purge_gap=30, horizon=5` keeps gap at 30 (does not shrink)
  - No train sample appears within h days of any test sample
  - All existing CV tests still pass
- **Done when:** Impossible to create a split where train data is within h days of test data.

#### 1.2 Verify and fix QLIKE log-space sign convention

- **File:** `src/volforecast/evaluation/metrics.py`
- **Change:** Derive correct log-space QLIKE from Patton (2011). Current code has `exp(y - y_hat) - (y - y_hat) - 1`. Correct Patton derivation: `exp(y_hat - y) - (y_hat - y) - 1`. Verify which the code implements, fix if wrong.
- **Key decision:** Must match Patton (2011) so results are comparable to literature.
- **Tests:**
  - QLIKE minimized when y_hat = y
  - Over-prediction penalized more heavily than under-prediction (Patton convention)
  - Synthetic data with known correct ranking
- **Done when:** QLIKE matches Patton (2011), documented in code comment.

#### 1.3 Add context kwarg to FeatureLayer protocol

- **File:** `src/volforecast/protocols.py`, all Layer 0--1 compute methods
- **Change:** Extend `FeatureLayer.compute(daily_data)` to `compute(daily_data, *, context=None)`. Update HARCoreLayer, AsymmetryLayer, NoiseRobustLayer to accept and ignore the kwarg.
- **Key decision:** Backward-compatible (context=None default). Layer 2+ will use context to receive IV surface, L2 depth, Treasury data.
- **Tests:**
  - All existing Layer 0--1 tests pass unchanged
  - Calling `.compute(data, context={"iv_surface": df})` works without error
  - Protocol check: layer with context still satisfies `isinstance(layer, FeatureLayer)`
- **Done when:** Layer 2 can be implemented using `context["iv_surface"]` without changing the protocol.

#### 1.4 Extract shared safe_log and consolidate zero-floor handling

- **File:** `src/volforecast/features/transforms.py` (safe_log already exists here)
- **Change:** Audit all feature modules for duplicated safe_log or ad-hoc `log(max(x, eps))` patterns. Replace with single `safe_log` import. Ensure consistent `min_value=1e-20`.
- **Tests:**
  - Grep for all `log(` and `np.log(` calls in features/; each should use safe_log or have explicit reason
  - `safe_log(0)` returns `log(1e-20)`, not `-inf`
  - All existing tests pass
- **Done when:** No duplicated log-safety patterns in features/.

**Fallback:** None. These are mandatory correctness fixes.
**Papers:** Patton (2011) for QLIKE.

---

## M2: LightGBM with Custom QLIKE Objective

**Objective:** First ML model. Produces genuine ML-vs-baseline comparison.

**Prerequisites:** M1.

### Tasks

#### 2.1 Implement custom QLIKE objective

- **File:** `src/volforecast/models/lightgbm.py`
- **What to build:** `QLIKEObjective` class with `.gradient(y_pred, y_true)` and `.hessian(y_pred, y_true)` methods returning arrays. Both operate in log-RV space.
- **Key decision:** Gradient = `exp(y_hat - y) - 1`, hessian = `exp(y_hat - y)`. Derived from Patton (2011) log-space QLIKE (as fixed in M1).
- **Tests:**
  - Numerical gradient check: analytical vs finite-difference (tol 1e-5)
  - Same for hessian
  - Objective is convex (hessian > 0 everywhere)
  - Train on synthetic data where true relationship is known; model converges
- **Done when:** LightGBM trains with custom QLIKE and converges.

#### 2.2 Implement LightGBMVolModel

- **File:** `src/volforecast/models/lightgbm.py`
- **What to build:** Model class satisfying `VolModel` protocol. Wraps `lgb.train()` with custom objective, early stopping, DART boosting. Config from ch09 Table 9.2 as defaults.
- **Key decision:** Register as `"lightgbm"` in MODEL_REGISTRY. DART boosting. Early stopping on validation QLIKE.
- **Tests:**
  - `.fit(X, y)` runs on 1000-row synthetic data
  - `.predict(X)` returns correct-length array
  - `.save()` / `.load()` round-trips
  - Predictions improve over training (QLIKE decreases)
  - Satisfies `isinstance(model, VolModel)`
- **Done when:** `vol run train --config lightgbm_config.yaml` completes.

#### 2.3 Wire Optuna hyperparameter tuning

- **File:** `src/volforecast/models/lightgbm.py` or new `models/tuning.py`
- **What to build:** Optuna study tuning learning_rate, num_leaves, min_data_in_leaf, n_estimators, reg_alpha, reg_lambda. SQLite storage at `workspace/experiments.db`.
- **Tests:**
  - 10-trial study completes on synthetic data
  - Best trial has lower QLIKE than defaults
  - SQLite DB contains trial records
- **Done when:** `vol run tune --config ...` finds improved hyperparameters.

#### 2.4 Implement walk-forward evaluation loop

- **File:** `src/volforecast/pipeline/runner.py` (extend existing)
- **What to build:** Rolling 5-year train window, step forward by test_size days, collect all OOS predictions. May already be partially implemented via expanding_window CV splitter.
- **Tests:**
  - Windows don't overlap illegally
  - Total OOS predictions cover expected date range
  - No look-ahead: max train date < min test date - purge_gap for each fold
- **Done when:** Walk-forward produces OOS predictions for all 3 horizons on dev universe.

#### 2.5 Select 8-symbol dev universe

- **File:** `src/volforecast/constants.py`
- **What to build:** `DEV_UNIVERSE = ["SPY", "AAPL", "MSFT", "NVDA", "XOM", "JPM", "IWM", "ES"]`
- **Key decision:** Use DEV_UNIVERSE for all iteration. Full 34-symbol universe only for final tournament.
- **Tests:** All 8 symbols have cached RV panels. Dev runs complete in <25% of full-universe time.
- **Done when:** Constant exists, baseline experiment runs on dev universe.

**Data sources:** Chunk Store L1 (confirmed), cached RV panels.
**Fallback:** If custom QLIKE objective is numerically unstable, fall back to MSE objective with QLIKE as eval metric only.
**Papers:** Patton (2011), Ke et al. (2017), Optiver 2021.

---

## M3: QLIKE Tournament

**Objective:** The most important deliverable. Definitive model comparison across all baselines and horizons.

**Prerequisites:** M2.

### Tasks

#### 3.1 Run full baseline tournament

- **What to build:** Script/CLI command that trains all 8 models (HAR, HARQ, SHAR, HAR-J, HAR-CJ, Ridge-HAR, Lasso-HAR, LightGBM) on dev universe across 3 horizons using walk-forward.
- **Key decision:** 8 models x 8 symbols x 3 horizons = 192 runs. Save all predictions.
- **Tests:**
  - All 192 runs complete
  - OOS predictions exist for every model/symbol/horizon
  - QLIKE scores finite and positive
- **Done when:** All predictions saved to workspace/models/.

#### 3.2 Implement Diebold-Mariano test

- **File:** `src/volforecast/evaluation/statistical_tests.py`
- **What to build:** `diebold_mariano_test(loss_1, loss_2, horizon)` returning test statistic and p-value. HAC standard errors (Newey-West) for h > 1.
- **Tests:**
  - Identical loss series returns p=1.0
  - loss_1 = loss_2 + large constant returns p~0
  - HAC correction differs from OLS for h=22
- **Done when:** `diebold_mariano_test()` passes all tests.

#### 3.3 Build tournament_table output

- **File:** `src/volforecast/evaluation/statistical_tests.py`
- **What to build:** `tournament_table(predictions_dict, y_true, baseline_key)` producing DataFrame with QLIKE scores, improvement bps vs baseline, and DM p-values.
- **Key decision:** Baseline = HARQ. Columns: QLIKE (h=1/5/22), bps improvement (h=1/5/22), DM p-value vs HARQ (h=1/5/22).
- **Tests:**
  - Table dimensions correct (8 models x 9 columns)
  - Baseline row shows 0 bps improvement
  - p-values between 0 and 1
- **Done when:** Tournament table prints cleanly for dev universe.

**Fallback:** If DM is slow, use simplified version without HAC for h=1.
**Papers:** Diebold & Mariano (1995), Patton (2011).

---

## M4: Layer 2 Options Features

**Objective:** Add the most impactful feature layer and unblock the tradeable signal.

**Prerequisites:** M1 (FeatureLayer context arg).

### Tasks

#### 4.1 Implement OptionsLayer.compute()

- **File:** `src/volforecast/features/options.py`
- **What to build:** Fill in stubbed `compute()`. Use `context["iv_surface"]` for Marquee data. Compute: atm_iv (1m, 3m), vrp, skew, term_slope, butterfly, iv_rv_gap. Single-stock: stock_atm_iv, stock_vrp via EDRVOL_PERCENT.
- **Key decision:** SPX features = market-wide regime signals. Single-stock IV confirmed working for all 34 symbols.
- **Tests:**
  - Features produce daily values for 1-year test period
  - VRP sign correct on average (IV > RV)
  - No NaN propagation from missing surface days
  - shift(1) applied to all features
- **Done when:** `OptionsLayer.compute(data, context={"iv_surface": df})` returns features.

#### 4.2 Wire IV surface fetching into pipeline

- **File:** `src/volforecast/pipeline/runner.py`
- **What to build:** Before calling feature layers, fetch IV surface via `marquee.fetch_iv_surface()` and single-stock IV via `marquee.fetch_atm_iv()`. Pass as context dict.
- **Key decision:** Fetch once per pipeline run.
- **Tests:**
  - Pipeline runs with `feature_layers: [har_core, asymmetry, options]`
  - Context dict contains expected DataFrames
- **Done when:** Full pipeline runs with Layer 2 active.

#### 4.3 Validate QLIKE improvement

- Run LightGBM with and without Layer 2 on dev universe. Compute QLIKE lift.
- **Key decision:** Expect 5--10% QLIKE improvement at h=5 and h=22 based on ch08 horizon priority table.
- **Done when:** QLIKE comparison documented.

**Data sources:** Marquee IV surface (confirmed), EDRVOL_PERCENT single-stock (confirmed for all 34 symbols).
**Fallback:** If single-stock IV has gaps, fall back to SPX-only IV as market-regime signal.
**Papers:** Christensen et al. (2023), Bollerslev et al. (2009).

---

## M5: Tradeable Signal

**Objective:** The priority deliverable. Prove the forecasts can make money.

**Prerequisites:** M3 (RV forecasts), M4 (options features for IV-RV gap).

### Tasks

#### 5.1 Implement IV-RV gap signal

- **File:** `src/volforecast/evaluation/economic_value.py`
- **What to build:** `iv_rv_gap_signal(iv_forecast, rv_forecast, threshold)` returning signal in {-1, 0, +1}. Long vol when RV forecast > IV (vol cheap). Short when IV > RV forecast (vol expensive).
- **Key decision:** Use ATM 1m IV. Threshold calibrated on training data (1 sigma of historical gap).
- **Tests:**
  - Signal direction matches expected
  - Signal is -1, 0, or +1 only
  - Random forecasts produce ~zero P&L
- **Done when:** Signal function produces daily signals for dev universe.

#### 5.2 Implement P&L backtesting

- **File:** `src/volforecast/evaluation/economic_value.py`
- **What to build:** `delta_hedged_straddle_pnl(signal, rv, iv, spot)` and `vol_targeting_pnl(returns, vol_forecast, target)`. Both return daily P&L series.
- **Key decision:** Straddle P&L primary. Vol-targeting secondary/simpler.
- **Tests:**
  - P&L zero when signal always neutral
  - Cumulative P&L monotonically increasing on synthetic correct-signal data
  - Transaction cost sensitivity: P&L positive under 1--2 bps costs
- **Done when:** P&L series computed for dev universe.

#### 5.3 Implement performance metrics and equity curve

- **File:** `src/volforecast/evaluation/economic_value.py`
- **What to build:** `compute_sharpe(returns)`, `compute_max_drawdown(cum_returns)`, equity curve matplotlib plot.
- **Tests:**
  - Sharpe of zero-mean returns is ~0
  - Max drawdown of monotonically increasing series is 0
  - Plot renders without error
- **Done when:** Sharpe > 0 OOS, equity curve saved.

**Fallback:** If straddle P&L weak, fall back to vol-targeting overlay. Negative result is still publishable.
**Papers:** Bollerslev et al. (2009), Corsi (2009), Moreira & Muir (2017).

---

## M6: Ensemble Experiments

**Objective:** Test whether combining models improves forecasts.

**Prerequisites:** M3 (tournament baseline). Does NOT depend on M5.

### Tasks

#### 6.1 Implement residual stacking

- **File:** `src/volforecast/models/ensemble.py`
- **What to build:** Script/class that: (a) loads HAR OOS predictions, (b) computes residuals, (c) trains LightGBM on residuals with full feature set, (d) sums forecasts.
- **Key decision:** Residual stacking is primary. Train models separately, blend post-hoc.
- **Tests:**
  - Stage 1 residuals have approximately zero mean
  - Stage 2 QLIKE on residuals is positive (model captures signal)
  - Combined forecast QLIKE <= best standalone QLIKE
- **Done when:** Residual stacking forecast exists for dev universe.

#### 6.2 Implement prediction blending

- **File:** `src/volforecast/models/ensemble.py`
- **What to build:** `InverseQLIKEEnsemble` weighting predictions inversely proportional to validation QLIKE. Fallback: equal-weight average.
- **Tests:**
  - Weights sum to 1
  - Lower QLIKE model gets higher weight
  - Blended QLIKE <= worst individual QLIKE
- **Done when:** Blended forecast exists for dev universe.

#### 6.3 Re-run tournament with ensemble entries

- Add residual stacking and prediction blending to tournament table.
- **Done when:** Tournament table has 10 rows (8 standalone + 2 ensemble), DM tests run.

**Fallback:** If neither ensemble beats standalone, document the finding.
**Papers:** Bucci (2020).

---

## M7: Stretch Goals

**Objective:** Polish and extend. Ordered by impact-per-effort.

### Tasks (each independent)

#### 7.1 Regime-conditional QLIKE

Split walk-forward evaluation by VIX regime (low/medium/high terciles). Show how model rankings change across regimes. **Deps:** M6.

#### 7.2 Model Confidence Set

Hansen et al. (2011) block bootstrap. Returns set of models not significantly worse than the best. **Deps:** M6.

#### 7.3 LSTM scalar forecast as LightGBM feature

Train LSTM on E-mini intraday sequences. Scalar point forecast as 1 extra LightGBM feature. Requires `SequenceModel` protocol. **Deps:** M2.

#### 7.4 Full 34-symbol tournament

Re-run M3 on full universe. Cross-sectional analysis of which stocks benefit most from ML. **Deps:** M3.

#### 7.5 Presentation figures

4--5 key plots: QLIKE table, forecast vs actual, P&L curve, feature importance bar chart. **Deps:** M5.

#### 7.6 Rashomon analysis

Interpretable trees on same feature set. Feature importance stability across near-optimal model set. **Deps:** M3.

---

## Architecture Decisions Log

| Decision | Choice | Rationale |
|---|---|---|
| Ensemble approach | Residual stacking (primary), prediction blending (fallback) | No RV paper supports feature stacking. Residual stacking gives each model a distinct role. |
| Dev universe | 8 symbols (SPY, AAPL, MSFT, NVDA, XOM, JPM, IWM, ES) | ~75% speedup. Full 34 for final tournament only. |
| Experiment tracking | SQLite `experiments.db` | Lightweight, Optuna native storage. |
| FeatureLayer protocol | Add `context` kwarg | Backward-compatible. Data-fetching stays in orchestrator. |
| LSTM scope | E-mini only, scalar forecast, stretch goal | Only 1 symbol has L2 depth. High effort, moderate gain. |
| QLIKE convention | Patton (2011) log-space derivation | Industry standard. |
| Pipeline architecture | Standalone blend stage | Train models independently, blend post-hoc. Maximum flexibility. |
| Priority ordering | Trading signal > academic rigor > model novelty | Desk cares about P&L first. |
