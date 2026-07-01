# Feature Engineering: Implementation Status

Current as of 2026-05-13. All ~420+ tests passing.

---

## Implemented (Layers 0-1 + Noise-Robust + Data Pipeline + Models + Evaluation)

### Layer 0: HAR Core + Measurement Quality (`features/har.py`)

| Function | What It Computes |
|---|---|
| `compute_realized_variance` | Sum of squared intraday log returns (no mean subtraction) |
| `compute_log_rv_features` | log RV at daily/weekly/monthly horizons (1, 5, 22-day windows) |
| `compute_rq` | Realized quarticity: (N/3) * sum(r_i^4) |
| `compute_harq_features` | Full HARQ set: log RV d/w/m + sqrt(RQ) + RQ-RV interaction |
| `build_har_design_matrix` | Vectorized rolling design matrix with lag-1 shift for forecasting |
| `HARCoreLayer.compute()` | Layer wrapper: emits sqrt_rq_d standalone + overnight_return |

Design: All features in log-space. Weekly/monthly averages computed in variance space before log transform. First 21 rows NaN (minimum history requirement). `sqrt_rq_d` always exposed as standalone column when rq exists. Overnight return = log(open_t / close_{t-1}).shift(1).

### Layer 1: Asymmetric Volatility (`features/asymmetry.py`)

| Function | What It Computes |
|---|---|
| `compute_semivariances` | RS+, RS-, signed jump (RS+ - RS-) |
| `compute_bpv` | Bipower variation: jump-robust integrated variance (BNS 2004) |
| `compute_realized_tripower_quarticity` | RTQ for BNS test variance estimation |
| `detect_jumps` | BNS z-test at alpha=0.999: Z = (RV-BPV)/sqrt(theta*RQ/n) |
| `compute_jump_variation` | J^2 = max(RV-BPV, 0) * jump_indicator |
| `compute_continuous_variation` | C = max(RV - J^2, 0) |
| `lee_mykland_test` | Lee-Mykland (2008) intraday jump detection via Gumbel threshold |
| `compute_signed_jumps` | J+ = sum(r² × I(r>0, jump)), J- = sum(r² × I(r<0, jump)) |
| `compute_realized_moments` | Realized skewness (Amaya et al. 2015) and kurtosis |
| `build_asymmetry_features` | All Layer 1 features in one call (9 output keys) |
| `AsymmetryLayer.compute()` | Layer wrapper: emits log-transformed daily/weekly/monthly + signed_return_d |

Design: Jump variation clamped >= 0. BNS critical value one-sided at 99.9%. Lee-Mykland uses Gumbel extreme-value threshold on local-BPV-standardized returns. Signed jumps partition Lee-Mykland-detected jumps into positive and negative components. Realized skewness uses Amaya et al. (2015) sqrt(N) normalization.

### Shared Transforms (`features/transforms.py`)

| Function | What It Computes |
|---|---|
| `safe_log` | Log transform with zero-floor protection (prevents -inf on zeros) |
| `lagged_log_features` | d/w/m rolling log-transformed and lagged features (shared utility) |

Design: `safe_log` clips to `min_value=1e-20` before log. `lagged_log_features` produces `log_{name}_d`, `log_{name}_w`, `log_{name}_m` with `.shift(1)`. Used by HARCoreLayer, AsymmetryLayer, and NoiseRobustLayer.

### Triple Expansion Utility (`features/expansion.py`)

| Function | What It Computes |
|---|---|
| `triple_expand` | Expands any series into {level, change, z-score} — LightGBM only |

Design: For each base feature, systematically produces 3 columns. Not wired into HAR-family baselines. Called explicitly by LightGBM pipeline.

### Noise-Robust Estimators (`features/noise_robust.py`)

| Function | What It Computes |
|---|---|
| `realized_kernel` | Parzen-kernel weighted autocovariances; H ~ n^(3/5); n^(-1/4) rate |
| `tsrv` | Two-Scales RV: subsampled slow-scale minus bias; K ~ n^(2/3) |
| `pre_averaged_rv` | Triangular pre-averaging with bias correction; L ~ n^(1/2) |
| `volatility_signature_plot_data` | RV at multiple sampling frequencies for diagnostic |
| `noise_gap` | (RK - RV_5min) / RV_5min: liquidity/noise intensity proxy |

Design: Bandwidths default to theoretically optimal rates. Results clamped >= 0. These are features alongside 5-min RV, not target replacements (citing Liu et al. 2015).

### Data Access (`data/chunk_store.py`)

| Function | What It Does |
|---|---|
| `fetch_trades` | L1 trade ticks via pytickclient for all trading days in range |
| `fetch_quotes` | L1 bid/ask quote ticks |
| `fetch_depth` | L2 order book depth for E-mini S&P 500 (up to 5 levels) |

Design: 34-symbol universe enforced. E-mini front-month contract resolution with roll cycle. Market hours 09:30-16:00 ET. Graceful fallback when pytickclient unavailable (raises ConnectionError).

### Resampling + Daily RV Pipeline (`data/resample.py`)

| Function | What It Does |
|---|---|
| `resample_trades_to_bars` | Previous-tick interpolation to regular OHLCV bars (default 5-min) |
| `compute_daily_rv_from_ticks` | Full pipeline: ticks -> bars -> RV/RQ/BPV/jumps/signed jumps/moments/RK/noise_gap |
| `compute_daily_rv_from_bars` | Same measures from pre-aggregated 5-min bars (rk=NaN, noise_gap=NaN) |

Design: Chains chunk_store -> resample -> all Layer 0-1 + noise-robust computations into a single daily observation (18 output fields). Two paths: `mode="bars"` (default, fast, server-side aggregation via `fetch_bars()`) or `mode="ticks"` (legacy, raw tick fetch via `fetch_trades_batch()`). Bars mode is ~14x faster but does not compute realized kernel or noise gap.

### Bar Fetching (`data/chunk_store.py` -- new)

| Function | What It Does |
|---|---|
| `fetch_bars` | Server-side AggGroupBy: returns ~78 OHLCV bars/day per symbol (5-min interval) |

Design: Uses `processor.AggGroupBy` with 6 operations (first/max/min/last price + sum volume + count ticks). Batches up to 20 days per API call. Handles E-mini contract rolling. Timezone: server returns UTC, converted to ET client-side.

### HAR-Family Baselines (`models/baselines.py`)

| Model | Type |
|---|---|
| `HARModel` | Standard HAR(1,5,22) via OLS |
| `HARQModel` | HAR + realized quarticity interaction |
| `SHARModel` | Semivariance HAR (log RS+, log RS-) |
| `HARJModel` | HAR + jump variation |
| `HARCJModel` | HAR + continuous + jump variation |
| `RidgeHARModel` | L2-regularized HAR |
| `LassoHARModel` | L1-regularized HAR |

All share: `.fit(X, y)`, `.predict(X)`, `.summary` interface. NaN rows auto-dropped before fitting.

### Evaluation (`evaluation/metrics.py`)

| Function | What It Computes |
|---|---|
| `qlike` | QLIKE loss (primary metric): mean(exp(d) - d - 1), supports log/variance space |
| `mse` | Mean squared error |
| `mae` | Mean absolute error |
| `r_squared` | R-squared (can be negative) |
| `qlike_improvement_bps` | (baseline - model) / baseline * 10000 |
| `compute_all` | All metrics in one call |
| `retransform_log_to_level` | Duan (1995) log-normal bias correction: exp(pred + sigma²/2) |

### Statistical Tests (`evaluation/statistical_tests.py`)

| Function | What It Computes |
|---|---|
| `diebold_mariano_test` | DM pairwise test with Newey-West HAC (bandwidth=h-1). Positive stat = model 2 better |
| `mincer_zarnowitz` | Efficiency regression (alpha=0, beta=1 F-test). Inputs: variance space |
| `model_confidence_set` | Hansen 2011 MCS: block bootstrap, T_R range stat, sequential elimination |
| `tournament_table` | Full comparison: QLIKE, MSE, R², DM, MZ, MCS in one sorted DataFrame |

### Tournament Runner (`evaluation/tournament.py`)

| Function | What It Does |
|---|---|
| `run_har_tournament` | Orchestrates 7 HAR models × N symbols × M horizons, returns tables per horizon |
| `_feature_layers_for_model` | Maps model name to required feature layer list |
| `display_tournament` | Rich pretty-print with MCS members bold |

Design: Per-symbol expanding-window pipeline runs; OOS predictions concatenated across symbols before `tournament_table()`. Config: `workspace/configs/tournament_har_dev.yaml`.

---

## Stubbed (NotImplementedError)

| Module | Layer | Planned Functions |
|---|---|---|
| `features/microstructure.py` | Layer 3 | Price acceleration, OBI, depth ratio, spread, VPIN |
| `features/cross_asset.py` | Layer 4 | Treasury slope, FX vol, commodity vol, DY spillover |
| `features/calendar.py` | Layer 5 | FOMC proximity, NFP proximity, OpEx, earnings |

---

## Recently Shipped (2026-05-18): Layer 2 Options-Implied

| Module | What | Status |
|---|---|---|
| `data/iv_ingest.py` | Bulk fetch SPX IV surface from Marquee + VIX from TSDB | Done |
| `data/iv_features.py` | Transform raw IV → 12 model features (VRP, skew, term slope, butterfly, iv_rv_gap, vol_of_vix, vix_innovation) | Done |
| `cli/ingest_iv.py` | CLI subcommand `vol ingest-iv` | Done |
| `features/options.py` | OptionsLayer updated: reads pre-computed cache, outputs 14 feature columns | Done |
| `cli/train.py` | Auto-loads IV cache into context when "options" in feature_layers | Done |
| Tests: `test_iv_ingest.py`, `test_iv_features.py` | 21 new tests | Done |
| `data/edrvol.py` | Added 1w ATM IV (`1watms -> iv_1w_atm`) to default field map, 38/39 symbols ingested | Done |
| `features/options.py` | Added 1w ATM IV features: `log_atm_iv_1w_d`, `iv_term_slope_1w1m_d` (when iv_1w_atm data present) | Done |
| `models/har_family.py` | `har_iv_1w` model: uses 1w ATM IV for tenor-matched forecasting (h=1, h=5) | Done |
| Tests: `test_edrvol.py`, `test_options.py` | 28 + 34 tests covering 1w tenor | Done |

**Remaining Layer 2 work:**
- Run actual ingest on GS desktop (requires Marquee session)
- VIX futures stitching (vix_term_slope, vix_term_curvature) — P2 priority
- End-to-end integration test with tournament

---

## Coverage Summary

| Component | Status | Test Count |
|---|---|---|
| Layer 0 (HAR core + overnight + sqrt_rq) | Done | ~15 tests |
| Layer 1 (asymmetry/jumps/LM/signed/moments) | Done | ~25 tests |
| Layer 2 (options-implied: IV, VRP, skew, butterfly, VIX) | Done | 21 tests |
| Shared transforms (safe_log, lagged_log_features) | Done | 18 tests |
| Triple expansion utility | Done | 11 tests |
| Noise-robust estimators | Done | 10 tests |
| Data access (ChunkStore + Marquee) | Done | 27 tests |
| Resampling + daily RV | Done | 14 tests |
| 7 HAR-family models | Done | 8 tests |
| Evaluation metrics (+ retransformation) | Done | ~23 tests |
| Statistical tests (DM, MZ, MCS, tournament_table) | Done | 21 tests |
| Tournament runner (run_har_tournament, display) | Done | 11 tests |
| **Total** | **~440+ tests passing** | |
| Layers 2-5 | Stubbed | 0 |
| Economic value (evaluation/economic_value.py) | Stubbed | 0 |

---

## What's Missing Before Real-Data Validation

1. ~~**GS network access**~~ -- Resolved. SPY ingest complete (1,695 rows, 2015-2025).
2. ~~**TSDB daily data**~~ -- `data/tsdb.py` implemented (fetch_daily_ohlcv, treasury, FX, commodity)
3. **Marquee API** -- `data/marquee.py` stubbed; needed for SPX IV surface (Layer 2)
4. ~~**Feature orchestrator**~~ -- Pipeline handles feature construction internally via CLI.
