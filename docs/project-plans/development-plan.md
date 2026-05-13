# ML Realized Volatility Forecasting: Development Plan

**Project:** GS ML Internship, ~20 weeks (May--Sep 2026)
**Priority ordering:** Trading signal > Academic rigor > Model novelty
**Dev universe:** SPY, AAPL, MSFT, NVDA, XOM, JPM, IWM, ES (8 symbols)
**Full universe:** 35 instruments (30 equities + 4 ETFs + 1 E-mini)

---

## Milestone Overview

| M# | Milestone | Deps | Category |
|----|-----------|------|----------|
| M0 | Research & Scoping | --- | Foundation |
| M1 | Data Infrastructure | M0 | Foundation |
| M2 | Feature Engine & Baselines | M1 | Foundation |
| M3 | LightGBM | M2 | MVP |
| M4 | Tournament | M3 | MVP |
| M5 | Layer 2 Options | M2 | MVP |
| M6 | Layers 4-5 Cross-Asset & Calendar | M2 | MVP |
| M7 | Signal | M4, M5 | MVP |
| M8 | Ensemble | M4 | Upside |
| M9 | Microstructure & Sequences | M2 | Upside |
| M10 | Stretch | M4-M9 | Upside |

**Critical path:** M3 -> M4 -> M8 -> M10
**Minimum viable deliverable:** M3-M7

---

## M0: Research & Scoping

**Objective:** Build deep understanding of the realized volatility forecasting literature and define the project scope before writing any code.

**Prerequisites:** None.

### Acceptance Criteria

- Literature survey complete (80+ papers reviewed)
- Project scope defined: ML forecasting for realized volatility
- Feature layer taxonomy designed (Layers 0-5)
- Primary metric chosen (QLIKE)
- ML model selected (LightGBM for tabular, LSTM stretch for sequences)
- Universe defined (34 symbols: 30 mega-cap equities + 4 ETFs + ES)
- Evaluation framework chosen (QLIKE primary, DM tests, MCS, purged CV)

### Key Tasks

- 0.1 Literature survey across realized volatility, HAR variants, ML applications
- 0.2 Define feature layer taxonomy from literature (L0: HAR core through L5: calendar)
- 0.3 Select primary metric (QLIKE) and evaluation protocol
- 0.4 Select ML model family (LightGBM) based on Optiver 2021 evidence
- 0.5 Define symbol universe and data requirements

**Papers:** Corsi (2009), Patton (2011), Bollerslev et al. (2016), Bucci (2020), Optiver Kaggle 2021.

---

## M1: Data Infrastructure

**Objective:** Build the data access layer so that raw market data can flow from GS systems into a pipeline-ready daily DataFrame.

**Prerequisites:** M0.

### Acceptance Criteria

- Tick data accessible via Chunk Store for all 34 symbols (L1 trades + L2 depth for ES)
- Daily data from TSDB (OHLCV, treasury yields, FX, commodities, VIX, VIX futures, SPX)
- IV surface from Marquee (ERDVOL_PERCENT_STANDARD, SPX tenors and strikes)
- Tick-to-bar resampling produces 78 bars/day (5-min frequency, previous-tick interpolation)
- RV panel builder outputs 18 daily measures with parquet caching and checkpoint resume
- Config system operational (ExperimentConfig, ModelConfig, CVConfig via YAML)

### Key Tasks

#### 1.1 Scaffold Python package

- `volforecast` package with registry/protocol pattern
- `VolModel` and `FeatureLayer` as `@runtime_checkable` protocols
- `@register_model` and `@register_feature_layer` decorators
- Lazy CLI dispatch via `__main__.py`

#### 1.2 Implement Chunk Store integration

- **File:** `src/volforecast/data/chunk_store.py`
- L1 trades: `fetch_trades(symbol, start, end)`, `fetch_trades_batch(symbol, dates, batch_size)`
- L1 quotes: `fetch_quotes(symbol, start, end)`
- L2 depth: `fetch_depth(start, end, levels=5)` (E-mini only)
- Thread-safe lazy session init, exponential backoff, parallel fetch

#### 1.3 Implement TSDB integration

- **File:** `src/volforecast/data/tsdb.py`
- `fetch_daily_ohlcv`, `fetch_treasury_yields`, `fetch_fx_rates`, `fetch_commodity_prices`, `fetch_vix`, `fetch_vix_futures`, `fetch_spx_index`
- Ticker-to-RIC mapping for all 34 universe symbols

#### 1.4 Implement Marquee integration

- **File:** `src/volforecast/data/marquee.py`
- `fetch_iv_surface`, `fetch_atm_iv`, `fetch_skew`, `fetch_vvix`
- DataSetAPI access to ERDVOL_PERCENT_STANDARD

#### 1.5 Implement resampling pipeline

- **File:** `src/volforecast/data/resample.py`
- `resample_trades_to_bars(trades, freq='5min')`: tick dedup, regular grid, forward-fill, log returns
- `compute_daily_rv_from_ticks(trades, freq='5min')`: orchestrates all 18 daily measures

#### 1.6 Implement RV panel builder

- **File:** `src/volforecast/data/rv_panel.py`
- `build_rv_panel(symbol, start, end, ...)`: batch-parallel fetch, per-day RV computation, parquet caching
- `enrich_panel_with_ohlcv(panel, symbol, start, end)`: merge TSDB daily data
- Incremental caching, checkpoint resume, date filtering

#### 1.7 Implement config and path system

- **Files:** `config.py`, `utils/paths.py`
- ExperimentConfig, ModelConfig, CVConfig dataclasses
- YAML serialization/deserialization
- CWD-independent path resolution via `resolve_project_root()`

#### 1.8 Implement trading calendar

- **File:** `src/volforecast/data/trading_calendar.py`
- NYSE holiday calendar (10 holidays)
- `get_trading_days(start, end) -> list[date]`

---

## M2: Feature Engine & HAR Baselines

**Objective:** Build the feature computation engine and all baseline models. Includes correctness fixes for purge gap and QLIKE sign.

**Prerequisites:** M1.

### Acceptance Criteria

- Layer 0-1 features computed with no look-ahead (shift(1) enforced)
- 7 HAR family models fit and predict
- QLIKE evaluation operational with correct sign convention (Patton 2011)
- Purge gap >= h enforced in all CV splitters
- End-to-end pipeline runs (ingest -> train -> evaluate)
- 390+ tests pass

### Key Tasks

#### 2.1 Implement Layer 0: HAR Core

- **File:** `src/volforecast/features/har.py`
- `compute_realized_variance`, `compute_rq`, `compute_log_rv_features`, `compute_harq_features`
- `build_har_design_matrix`: vectorized rolling d/w/m computation
- `HARCoreLayer` (registry: `"har_core"`): log_rv_d/w/m, sqrt_rq_d, rq_rv_interaction, overnight_return

#### 2.2 Implement Layer 1: Asymmetric Volatility

- **File:** `src/volforecast/features/asymmetry.py`
- Semivariances (RS+, RS-), BPV, BNS jump detection, jump/continuous variation
- Lee-Mykland intraday jump detection, signed jumps (J+, J-)
- Realized moments (skewness, kurtosis)
- `AsymmetryLayer` (registry: `"asymmetry"`): lagged log features at d/w/m horizons

#### 2.3 Implement noise-robust estimators

- **File:** `src/volforecast/features/noise_robust.py`
- Realized kernel (Parzen flat-top), TSRV (two-scales), pre-averaged RV
- Noise gap: (RK - RV_5min) / RV_5min
- `NoiseRobustLayer` (registry: `"noise_robust"`): log_rk_d/w, noise_gap_d/w

#### 2.4 Implement feature utilities

- **File:** `src/volforecast/features/transforms.py`
- `safe_log(series, min_value=1e-20)`: prevents -inf
- `lagged_log_features(series, name, windows)`: standard HAR-style d/w/m features
- **File:** `src/volforecast/features/expansion.py`
- `triple_expand(series, window=20)`: level, change, z-score for tree models

#### 2.5 Implement 7 HAR family models

- **File:** `src/volforecast/models/har_family.py`
- Template Method via `_BaseHAR`: HAR, HARQ, SHAR, HAR-J, HAR-CJ, Ridge-HAR, Lasso-HAR
- Shared interface: `.fit(X, y)`, `.predict(X)`, `.summary`, `.save()/.load()`

#### 2.6 Implement core evaluation metrics

- **File:** `src/volforecast/evaluation/metrics.py`
- `qlike(y_true, y_pred, log_space=True)`, `mse`, `mae`, `r_squared`, `compute_all`
- `retransform_log_to_level(log_pred, var)`: Duan (1995) smearing
- `qlike_improvement_bps(baseline, model)`

#### 2.7 Implement CV splitters

- **File:** `src/volforecast/utils/cv.py`
- PurgedKFoldCV, BlockedKFoldCV, ExpandingWindowCV, RollingWindowCV
- Custom implementations, no sklearn dependency

#### 2.8 Implement CLI pipeline

- **File:** `src/volforecast/__main__.py`, `cli/`, `pipeline/runner.py`
- Subcommands: ingest, train, evaluate, run-pipeline, report
- Pipeline orchestration: feature composition -> model training -> evaluation
- Rich progress display (PipelineProgress, StageProgress)

#### 2.9 Fix CV purge gap enforcement

- **File:** `src/volforecast/utils/cv.py`
- Add validation in each splitter that enforces `purge_gap = max(purge_gap, h)` per horizon. Applied dynamically inside the training loop, not as a global config.
- **Tests:**
  - `purge_gap=5, horizon=22` produces splits with gap >= 22
  - `purge_gap=30, horizon=5` keeps gap at 30 (does not shrink)
  - No train sample appears within h days of any test sample
  - All existing CV tests still pass
- **Done when:** Impossible to create a split where train data is within h days of test data.

#### 2.10 Verify and fix QLIKE log-space sign convention

- **File:** `src/volforecast/evaluation/metrics.py`
- Derive correct log-space QLIKE from Patton (2011). Current code has `exp(y - y_hat) - (y - y_hat) - 1`. Correct Patton derivation: `exp(y_hat - y) - (y_hat - y) - 1`. Verify which the code implements, fix if wrong.
- **Tests:**
  - QLIKE minimized when y_hat = y
  - Over-prediction penalized more heavily than under-prediction (Patton convention)
  - Synthetic data with known correct ranking
- **Done when:** QLIKE matches Patton (2011), documented in code comment.

#### 2.11 Add context kwarg to FeatureLayer protocol

- **File:** `src/volforecast/protocols.py`, all Layer 0-1 compute methods
- Extend `FeatureLayer.compute(daily_data)` to `compute(daily_data, *, context=None)`. Update HARCoreLayer, AsymmetryLayer, NoiseRobustLayer to accept and ignore the kwarg.
- Backward-compatible (context=None default). Layer 2+ will use context to receive IV surface, L2 depth, Treasury data.
- **Tests:**
  - All existing Layer 0-1 tests pass unchanged
  - Calling `.compute(data, context={"iv_surface": df})` works without error
  - Protocol check: layer with context still satisfies `isinstance(layer, FeatureLayer)`
- **Done when:** Layer 2 can be implemented using `context["iv_surface"]` without changing the protocol.

#### 2.12 Consolidate safe_log and zero-floor handling

- **File:** `src/volforecast/features/transforms.py` (safe_log already exists here)
- Audit all feature modules for duplicated safe_log or ad-hoc `log(max(x, eps))` patterns. Replace with single `safe_log` import. Ensure consistent `min_value=1e-20`.
- **Tests:**
  - Grep for all `log(` and `np.log(` calls in features/; each should use safe_log or have explicit reason
  - `safe_log(0)` returns `log(1e-20)`, not `-inf`
  - All existing tests pass
- **Done when:** No duplicated log-safety patterns in features/.

**Papers:** Corsi (2009), Patton & Sheppard (2015), Barndorff-Nielsen & Shephard (2004), Lee & Mykland (2008), Bollerslev et al. (2016), Patton (2011).

---

## M3: LightGBM with Custom QLIKE Objective

**Objective:** First ML model. Produces genuine ML-vs-baseline comparison.

**Prerequisites:** M2.

### Tasks

#### 3.1 Implement custom QLIKE objective

- **File:** `src/volforecast/models/lightgbm.py`
- **What to build:** `QLIKEObjective` class with `.gradient(y_pred, y_true)` and `.hessian(y_pred, y_true)` methods returning arrays. Both operate in log-RV space.
- **Key decision:** Gradient = `exp(y_hat - y) - 1`, hessian = `exp(y_hat - y)`. Derived from Patton (2011) log-space QLIKE (as fixed in M2).
- **Tests:**
  - Numerical gradient check: analytical vs finite-difference (tol 1e-5)
  - Same for hessian
  - Objective is convex (hessian > 0 everywhere)
  - Train on synthetic data where true relationship is known; model converges
- **Done when:** LightGBM trains with custom QLIKE and converges.

#### 3.2 Implement LightGBMVolModel

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

#### 3.3 Wire Optuna hyperparameter tuning

- **File:** `src/volforecast/models/lightgbm.py` or new `models/tuning.py`
- **What to build:** Optuna study tuning learning_rate, num_leaves, min_data_in_leaf, n_estimators, reg_alpha, reg_lambda. SQLite storage at `workspace/experiments.db`.
- **Tests:**
  - 10-trial study completes on synthetic data
  - Best trial has lower QLIKE than defaults
  - SQLite DB contains trial records
- **Done when:** `vol run tune --config ...` finds improved hyperparameters.

#### 3.4 Implement walk-forward evaluation loop

- **File:** `src/volforecast/pipeline/runner.py` (extend existing)
- **What to build:** Rolling 5-year train window, step forward by test_size days, collect all OOS predictions. May already be partially implemented via expanding_window CV splitter.
- **Tests:**
  - Windows don't overlap illegally
  - Total OOS predictions cover expected date range
  - No look-ahead: max train date < min test date - purge_gap for each fold
- **Done when:** Walk-forward produces OOS predictions for all 3 horizons on dev universe.

#### 3.5 Select 8-symbol dev universe

- **File:** `src/volforecast/constants.py`
- **What to build:** `DEV_UNIVERSE = ["SPY", "AAPL", "MSFT", "NVDA", "XOM", "JPM", "IWM", "ES"]`
- **Key decision:** Use DEV_UNIVERSE for all iteration. Full 34-symbol universe only for final tournament.
- **Tests:** All 8 symbols have cached RV panels. Dev runs complete in <25% of full-universe time.
- **Done when:** Constant exists, baseline experiment runs on dev universe.

**Data sources:** Chunk Store L1 (confirmed), cached RV panels.
**Fallback:** If custom QLIKE objective is numerically unstable, fall back to MSE objective with QLIKE as eval metric only.
**Papers:** Patton (2011), Ke et al. (2017), Optiver 2021.

---

## M4: QLIKE Tournament

**Objective:** The most important deliverable. Definitive model comparison across all baselines and horizons.

**Prerequisites:** M3.

### Tasks

#### 4.1 Run full baseline tournament

- **What to build:** Script/CLI command that trains all 8 models (HAR, HARQ, SHAR, HAR-J, HAR-CJ, Ridge-HAR, Lasso-HAR, LightGBM) on dev universe across 3 horizons using walk-forward.
- **Key decision:** 8 models x 8 symbols x 3 horizons = 192 runs. Save all predictions.
- **Tests:**
  - All 192 runs complete
  - OOS predictions exist for every model/symbol/horizon
  - QLIKE scores finite and positive
- **Done when:** All predictions saved to workspace/models/.

#### 4.2 Implement Diebold-Mariano test

- **File:** `src/volforecast/evaluation/statistical_tests.py`
- **What to build:** `diebold_mariano_test(loss_1, loss_2, horizon)` returning test statistic and p-value. HAC standard errors (Newey-West) for h > 1. Harvey-Leybourne-Newbold small-sample correction.
- **Tests:**
  - Identical loss series returns p=1.0
  - loss_1 = loss_2 + large constant returns p~0
  - HAC correction differs from OLS for h=22
- **Done when:** `diebold_mariano_test()` passes all tests.

#### 4.3 Implement Mincer-Zarnowitz efficiency test

- **File:** `src/volforecast/evaluation/statistical_tests.py`
- **What to build:** `mincer_zarnowitz(y_true, y_pred)`: regress actual = alpha + beta * forecast. Tests H0: alpha=0, beta=1 jointly.
- Returns: dict with intercept, slope, R-squared, F-pvalue.
- **Done when:** MZ regression runs for all models in tournament.

#### 4.4 Build tournament_table output

- **File:** `src/volforecast/evaluation/statistical_tests.py`
- **What to build:** `tournament_table(predictions_dict, y_true, baseline_key)` producing DataFrame with QLIKE scores, improvement bps vs baseline, DM p-values, and MZ efficiency.
- **Key decision:** Baseline = HARQ. Columns: QLIKE (h=1/5/22), bps improvement (h=1/5/22), DM p-value vs HARQ (h=1/5/22).
- **Tests:**
  - Table dimensions correct (8 models x columns)
  - Baseline row shows 0 bps improvement
  - p-values between 0 and 1
- **Done when:** Tournament table prints cleanly for dev universe.

**Fallback:** If DM is slow, use simplified version without HAC for h=1.
**Papers:** Diebold & Mariano (1995), Patton (2011), Mincer & Zarnowitz (1969).

---

## M5: Layer 2 Options Features

**Objective:** Add the most impactful feature layer and unblock the tradeable signal.

**Prerequisites:** M2 (FeatureLayer context arg).

### Tasks

#### 5.1 Implement OptionsLayer.compute()

- **File:** `src/volforecast/features/options.py`
- **What to build:** Fill in stubbed `compute()`. Use `context["iv_surface"]` for Marquee data. Compute: atm_iv (1m, 3m), vrp, skew, term_slope, butterfly, iv_rv_gap. Single-stock: stock_atm_iv, stock_vrp via EDRVOL_PERCENT.
- **Key decision:** SPX features = market-wide regime signals. Single-stock IV confirmed working for all 34 symbols.
- **Tests:**
  - Features produce daily values for 1-year test period
  - VRP sign correct on average (IV > RV)
  - No NaN propagation from missing surface days
  - shift(1) applied to all features
- **Done when:** `OptionsLayer.compute(data, context={"iv_surface": df})` returns features.

#### 5.2 Wire IV surface fetching into pipeline

- **File:** `src/volforecast/pipeline/runner.py`
- **What to build:** Before calling feature layers, fetch IV surface via `marquee.fetch_iv_surface()` and single-stock IV via `marquee.fetch_atm_iv()`. Pass as context dict.
- **Key decision:** Fetch once per pipeline run.
- **Tests:**
  - Pipeline runs with `feature_layers: [har_core, asymmetry, options]`
  - Context dict contains expected DataFrames
- **Done when:** Full pipeline runs with Layer 2 active.

#### 5.3 Validate QLIKE improvement

- Run LightGBM with and without Layer 2 on dev universe. Compute QLIKE lift.
- **Key decision:** Expect 5-10% QLIKE improvement at h=5 and h=22 based on ch08 horizon priority table.
- **Done when:** QLIKE comparison documented.

**Data sources:** Marquee IV surface (confirmed), EDRVOL_PERCENT single-stock (confirmed for all 34 symbols).
**Fallback:** If single-stock IV has gaps, fall back to SPX-only IV as market-regime signal.
**Papers:** Christensen et al. (2023), Bollerslev et al. (2009), Bekaert & Hoerova (2014).

---

## M6: Layers 4-5 Cross-Asset & Calendar

**Objective:** Add cross-asset spillover features and calendar/event indicators. These use data sources already wired in M1 (TSDB treasury/FX/commodity) and pure date arithmetic.

**Prerequisites:** M2.

### Tasks

#### 6.1 Implement Layer 4: Cross-Asset features

- **File:** `src/volforecast/features/cross_asset.py`
- **What to build:** Fill in stubbed functions:
  - `compute_treasury_slope(yields, short, long)`: 10y - 2y spread in bps
  - `compute_fx_vol(fx_rates, window=22)`: annualized rolling RV of FX returns (USD/JPY, EUR/USD)
  - `compute_commodity_vol(prices, window=22)`: annualized rolling RV of commodities (CL, GC)
  - `compute_dy_spillover(rv_matrix, h=10, p=4)`: Diebold-Yilmaz VAR FEVD total spillover index
  - `build_cross_asset_features(...)`: orchestrator
- Wire TSDB fetching into pipeline context: `context["treasury"]`, `context["fx"]`, `context["commodity"]`
- **Tests:**
  - Treasury slope matches expected sign and magnitude
  - FX/commodity vol annualizes correctly
  - DY spillover index in [0, 1]
  - All features shifted by 1 (no look-ahead)
- **Done when:** `CrossAssetLayer.compute(data, context=...)` returns features.

#### 6.2 Implement Layer 5: Calendar/Event features

- **File:** `src/volforecast/features/calendar.py`
- **What to build:** Fill in stubbed functions:
  - `compute_fomc_proximity(date, fomc_dates)`: days_to_fomc, fomc_week binary
  - `compute_nfp_proximity(date, nfp_dates)`: days_to_nfp, nfp_week binary
  - `compute_opex_proximity(date)`: days_to_opex (3rd Friday), opex_week binary
  - `compute_earnings_proximity(date, symbol, earn_dates)`: days_to_earnings, earnings_week binary
  - `build_calendar_features(...)`: all above + day_of_week + month dummies
- Hardcode FOMC dates (public) and earnings calendar for 30 names.
- **Tests:**
  - FOMC proximity correct for known dates
  - OPEX always falls on 3rd Friday
  - day_of_week is 0-4 only (trading days)
- **Done when:** `CalendarLayer.compute(data, context=...)` returns features.

#### 6.3 Validate QLIKE lift from Layers 4-5

- Run LightGBM with L0-L2 vs L0-L2+L4-L5 on dev universe.
- Expect 1-5% marginal QLIKE improvement, concentrated in regime transitions.
- **Done when:** QLIKE comparison documented.

**Papers:** Diebold & Yilmaz (2012, 2014), Patton & Sheppard (2015).

---

## M7: Tradeable Signal

**Objective:** The priority deliverable. Prove the forecasts can make money.

**Prerequisites:** M4 (RV forecasts), M5 (options features for IV-RV gap).

### Tasks

#### 7.1 Implement IV-RV gap signal

- **File:** `src/volforecast/evaluation/economic_value.py`
- **What to build:** `iv_rv_gap_signal(iv_forecast, rv_forecast, threshold)` returning signal in {-1, 0, +1}. Long vol when RV forecast > IV (vol cheap). Short when IV > RV forecast (vol expensive).
- **Key decision:** Use ATM 1m IV. Threshold calibrated on training data (1 sigma of historical gap).
- **Tests:**
  - Signal direction matches expected
  - Signal is -1, 0, or +1 only
  - Random forecasts produce ~zero P&L
- **Done when:** Signal function produces daily signals for dev universe.

#### 7.2 Implement P&L backtesting

- **File:** `src/volforecast/evaluation/economic_value.py`
- **What to build:** `delta_hedged_straddle_pnl(signal, rv, iv, spot)` and `vol_targeting_pnl(returns, vol_forecast, target)`. Both return daily P&L series.
- **Key decision:** Straddle P&L primary. Vol-targeting secondary/simpler. Gamma recomputation daily (Black-Scholes, not constant). Transaction costs amortized over 22-day holding.
- **Tests:**
  - P&L zero when signal always neutral
  - Cumulative P&L monotonically increasing on synthetic correct-signal data
  - Transaction cost sensitivity: P&L positive under 1-2 bps costs
- **Done when:** P&L series computed for dev universe.

#### 7.3 Implement performance metrics and equity curve

- **File:** `src/volforecast/evaluation/economic_value.py`
- **What to build:** `compute_sharpe(returns)`, `compute_max_drawdown(cum_returns)`, `economic_value_summary(...)` (Sharpe, max_dd, Calmar, DSR, win rate). Equity curve matplotlib plot.
- **Tests:**
  - Sharpe of zero-mean returns is ~0
  - Max drawdown of monotonically increasing series is 0
  - Plot renders without error
- **Done when:** Sharpe > 0 OOS, equity curve saved.

**Fallback:** If straddle P&L weak, fall back to vol-targeting overlay. Negative result is still publishable.
**Papers:** Bollerslev et al. (2009), Corsi (2009), Moreira & Muir (2017).

---

## M8: Ensemble Experiments

**Objective:** Test whether combining models improves forecasts.

**Prerequisites:** M4 (tournament baseline). Does NOT depend on M7.

### Tasks

#### 8.1 Implement residual stacking

- **File:** `src/volforecast/models/ensemble.py`
- **What to build:** Script/class that: (a) loads HAR OOS predictions, (b) computes residuals, (c) trains LightGBM on residuals with full feature set, (d) sums forecasts.
- **Key decision:** Residual stacking is primary. Train models separately, blend post-hoc.
- **Tests:**
  - Stage 1 residuals have approximately zero mean
  - Stage 2 QLIKE on residuals is positive (model captures signal)
  - Combined forecast QLIKE <= best standalone QLIKE
- **Done when:** Residual stacking forecast exists for dev universe.

#### 8.2 Implement prediction blending

- **File:** `src/volforecast/models/ensemble.py`
- **What to build:** `InverseQLIKEEnsemble` weighting predictions inversely proportional to validation QLIKE. Fallback: equal-weight average.
- **Key decision:** Horizon-specific strategy: inverse-QLIKE at h=1, linear blend at h=5, simple average at h=22 (confirmed in research journal 2026-05-12).
- **Tests:**
  - Weights sum to 1
  - Lower QLIKE model gets higher weight
  - Blended QLIKE <= worst individual QLIKE
- **Done when:** Blended forecast exists for dev universe.

#### 8.3 Re-run tournament with ensemble entries

- Add residual stacking and prediction blending to tournament table.
- **Done when:** Tournament table has 10 rows (8 standalone + 2 ensemble), DM tests run.

**Fallback:** If neither ensemble beats standalone, document the finding.
**Papers:** Bucci (2020).

---

## M9: Microstructure & Sequences

**Objective:** Exploit E-mini L2 order book data and intraday sequences. Both use the same intraday data source.

**Prerequisites:** M2 (data infrastructure for E-mini L2).

### Tasks

#### 9.1 Implement Layer 3: Microstructure features

- **File:** `src/volforecast/features/microstructure.py`
- **What to build:** Fill in stubbed functions:
  - `compute_price_acceleration(mid, window=50)`: 2nd derivative of mid-price (log-return-of-log-return)
  - `compute_obi(bid_sizes, ask_sizes, levels=5)`: order book imbalance (sum_bid - sum_ask) / (sum_bid + sum_ask)
  - `compute_depth_ratio(bid_depth, ask_depth)`: log(bid_depth / ask_depth)
  - `compute_spread(bid, ask)`: spread stats in bps (mean, median, std, max)
  - `compute_vpin(trades, bucket_size, n_buckets)`: Volume-Synchronized Probability of Informed Trading
  - `build_microstructure_features(...)`: orchestrator
- Wire L2 depth fetching into pipeline context for E-mini.
- Equities get L1-only features (spread, OBI from BBO, signed volume).
- **Tests:**
  - OBI values in [-1, 1]
  - VPIN values in [0, 1]
  - Spread positive and in reasonable bps range
  - All features shifted by 1
- **Done when:** `MicrostructureLayer.compute(data, context={"l2_depth": df})` returns features.

#### 9.2 Implement LSTM sequential model

- **File:** `src/volforecast/models/lstm.py`
- **What to build:** `LSTMVolModel`: sequence-to-scalar model on E-mini intraday bars.
  - Input shape: (n_samples, 78, input_dim) -- 78 bars/day, 4-10 features per bar
  - Architecture: 2 layers, 64 hidden units, dropout 0.2
  - Loss: QLIKE on log-RV
  - Optimizer: AdamW with cosine learning rate schedule
- Register as `"lstm"` in MODEL_REGISTRY.
- **Tests:**
  - Forward pass produces correct output shape
  - Loss decreases over training on synthetic sequences
  - `.save()` / `.load()` round-trips
- **Done when:** LSTM produces daily RV forecasts for E-mini.

#### 9.3 Evaluate LSTM scalar forecast as LightGBM feature

- Train LSTM on E-mini, extract scalar point forecast.
- Add as 1 extra feature to LightGBM. Evaluate QLIKE lift.
- Do NOT use high-dimensional embeddings (confirmed decision from research journal 2026-05-12).
- **Done when:** QLIKE comparison documented for E-mini with/without LSTM feature.

#### 9.4 (Optional) Implement TCN alternative

- **File:** `src/volforecast/models/lstm.py`
- `TCNVolModel`: dilated causal convolutions, channels [64, 64, 32], dropout 0.2.
- Same input/output contract as LSTM. Drop-in replacement for comparison.
- **Done when:** TCN runs as LSTM alternative.

**Papers:** Cont, Kukanov & Stoikov (2014), Cartea, Jaimungal & Penalva (2015), Bucci (2020).

---

## M10: Stretch Goals

**Objective:** Polish, extend, and add novel contributions. Ordered by impact-per-effort.

**Prerequisites:** M4-M9 (varies by task).

### Tasks (each independent)

#### 10.1 Regime-conditional QLIKE

Split walk-forward evaluation by VIX regime (low/medium/high terciles). Show how model rankings change across regimes. Evaluate whether ensemble benefits concentrate in crisis periods. **Deps:** M8.

#### 10.2 Model Confidence Set

Hansen, Lunde & Nason (2011) block bootstrap. Stationary bootstrap with 5,000 reps, mean block length = embargo period. Returns set of models not significantly worse than the best. **Deps:** M8.

#### 10.3 Rashomon analysis

Full 4-step pipeline for interpretability:
1. **Enumerate Rashomon set**: TreeFARMS or RESPLIT, enumerate all trees within epsilon=2% MSE of optimum
2. **Rashomon Importance Distributions (RID)**: stable feature importance across entire Rashomon set + bootstrap
3. **Variable Importance Clouds (VIC)**: map each feature to [min, max] importance range; classify as essential/interchangeable/useless
4. **Regime-stable feature selection**: train Rashomon sets on rolling windows, intersect across regimes

**Deps:** M4.

#### 10.4 Optimal Decision Trees (STreeD)

STreeDPiecewiseLinearRegressor from pystreed. Max depth 4-5, 8-32 leaves, elastic-net per leaf. Interpretable alternative to LightGBM. **Deps:** M4.

#### 10.5 Layer 6: Memory features

Fractionally differenced RV (d ~ 0.35-0.45), rolling Hurst exponent, vol-of-vol (std of RV over 22 days), regime duration (days since last 2-sigma RV spike). **Deps:** M2.

#### 10.6 Layer 7: Sentiment

FinBERT news sentiment (daily score), negative news count. 1-3% QLIKE improvement concentrated in crises; worth it for single names with idiosyncratic flow. **Deps:** M2.

#### 10.7 HTML reporting & visualization

Complete the 7 stubbed report section renderers (summary, forecast_vs_actual, qlike_analysis, statistical_tests, economic_value, diagnostics) and 8 stubbed visualization functions (rv_plots, evaluation_plots, feature_plots). Integrate the 10 existing standalone plots. **Deps:** M4, M7.

#### 10.8 Full 34-symbol tournament

Re-run M4 on full universe. Cross-sectional analysis of which stocks benefit most from ML. **Deps:** M4.

#### 10.9 Presentation figures

4-5 key plots: QLIKE table, forecast vs actual, P&L curve, feature importance bar chart, Rashomon VIC clouds. **Deps:** M7, M10.3.

---

## Architecture Decisions Log

| Decision | Choice | Rationale |
|---|---|---|
| Ensemble approach | Residual stacking (primary), prediction blending (fallback) | No RV paper supports feature stacking. Residual stacking gives each model a distinct role. |
| Blending strategy | Inverse-QLIKE at h=1, linear at h=5, simple average at h=22 | Confirmed in research journal 2026-05-12. |
| Dev universe | 8 symbols (SPY, AAPL, MSFT, NVDA, XOM, JPM, IWM, ES) | ~75% speedup. Full 34 for final tournament only. |
| Experiment tracking | SQLite `experiments.db` | Lightweight, Optuna native storage. |
| FeatureLayer protocol | Add `context` kwarg | Backward-compatible. Data-fetching stays in orchestrator. |
| LSTM scope | E-mini only, scalar forecast, stretch goal | Only 1 symbol has L2 depth. High effort, moderate gain. |
| LSTM output | Scalar point forecast, NOT high-dim embeddings | Confirmed in research journal 2026-05-12. Embedding instability risk too high. |
| QLIKE convention | Patton (2011) log-space derivation | Industry standard. |
| Pipeline architecture | Standalone blend stage | Train models independently, blend post-hoc. Maximum flexibility. |
| Priority ordering | Trading signal > academic rigor > model novelty | Desk cares about P&L first. |
| Milestone structure | M0-M2 foundation, M3-M7 MVP, M8-M10 upside | Captures completed work and provides comprehensive forward plan. |
