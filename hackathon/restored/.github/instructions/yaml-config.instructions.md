---
applyTo: "workspace/configs/**"
description: "Use when creating, editing, or reviewing ML experiment configuration YAML files. Provides the full schema reference, valid enum values, ordering constraints, and points to the canonical example config."
---

# Experiment Config YAML Rules

## Quick Start

**Before writing or modifying any experiment config**, read the canonical example:

- workspace/configs/_CANONICAL_EXAMPLE.yaml — Fully-commented reference showing ALL fields, valid values, types, and defaults

Copy that file and modify only what you need. Delete sections you don't use.

---

## Required Fields

| Field | Type | Example |
|-------|------|---------|
| `name` | string | `"trial_011_h22_ablation"` |
| `universe` | list[str] | `[SPY, AAPL, MSFT, ...]` |
| `date_range` | [str, str] | `["2015-01-02", "2024-12-31"]` |
| `horizons` | list[int] | `[1, 5, 22]` |
| `feature_layers` | list[str] | `[har_core, asymmetry, options]` |
| `model.name` | string | `"lightgbm"` |

## Optional Fields (with defaults)

| Field | Default | Notes |
|-------|---------|-------|
| `model.params` | `{}` | Model-specific hyperparameters |
| `cv.method` | `"expanding_window"` | See valid methods below |
| `cv.n_splits` | `5` | Number of CV folds (used by kfold methods; expanding_window auto-derives) |
| `cv.purge_gap` | `5` | Date embargo between train/test |
| `cv.embargo` | `0` | Post-test date embargo — indices in `[test_end, test_end + embargo)` dropped from all subsequent folds' train sets (valid; used by no trial config to date) |
| `cv.train_size` | `null` | Initial train window (trading days) |
| `cv.test_size` | `null` | Test window per fold |
| `training_mode` | `"pooled"` | `pooled` or `per_symbol` |
| `seed` | `42` | Random seed |
| `output_dir` | `"workspace/tmp/results"` | Results path |
| `n_gpus` | `1` | GPU fold parallelism (LSTM/TCN only) |
| `fold_cache_enabled` | `true` | Cache sequence model fold training |
| `fold_cache_dir` | `null` | Override fold cache path |
| `sequences` | `null` | Sequence tensor config (LSTM/TCN only) |
| `base_model` | `null` | Tabular base for residual learning |
| `feature_stack` | `null` | LSTM feature stacking into tabular model |
| `feature_selection` | `null` | SHAP-based Boruta-style feature elimination per outer CV fold (`FeatureSelectionConfig`) |
| `blend` | `null` | Prediction-level blend of >=2 sub-models (`BlendConfig`) |
| `conditional_duan` | `null` | Free-form dict for the trial-068 heteroscedastic Duan correction (`enabled`, `n_estimators`, `max_leaves`, `max_depth`, `learning_rate`, `min_child_weight`, `subsample`, `colsample_bytree`, `reg_lambda`, `max_var`, `min_folds_for_training`) |
| `graph` | `null` | Point-in-time adjacency config (`GraphConfig`) — required by graph models (`ghar`/`gnn`/`gnnhar`/`dcrnn_har`/`stid`/`gsp_har`/`gnn_learned`) |
| `horizon_overrides` | `{}` | Per-horizon model/CV/base_model/feature_stack overrides |
| `tuning` | disabled | Omit section entirely if not using |
| `tournament` | empty | Omit if single-model run |

## Valid Enum Values

### `feature_layers` (order matters!)

| Layer | Features | Notes |
|-------|----------|-------|
| `iv_surface` | 0 (enrichment) | **Must come before `options`** — loads IV data |
| `har_core` | 6 | Log RV daily/weekly/monthly |
| `asymmetry` | 12 | Semivariances, signed jumps |
| `noise_robust` | 4 | RQ, BPV, continuous variation |
| `options` | ~18 | ATM IV, VRP, skew, term slope |
| `calendar` | 11 | FOMC, earnings, OpEx, DOW |
| `cross_asset` | variable | Treasury slope, FX/commodity vol |
| `cross_asset_momentum` | variable | Daily changes/z-scores of cross-asset signals |
| `microstructure` | variable | E-mini L2: OBI, depth, VPIN |
| `realized_correlation` | variable | Realized correlation with market |
| `implied_correlation` | variable | Cross-symbol implied correlation from IV surfaces (SPX + constituents) |
| `long_memory` | variable | Long-memory / fractional-difference features |
| `vol_of_vol` | variable | Rolling volatility of realized volatility |
| `dealer_gamma` | variable | Dealer gamma exposure proxies |
| `gsvivs_signals` | variable | GSVIVS01 variance-swap signals (IV-RV gap, Kvar) |
| `regime` | variable | Regime indicators (crisis/COVID/high-vol dummies) |
| `tree_expansion` | 2x base | **Must come last** — expands preceding layers |

### `model.name`

- **HAR family:** `har`, `harq`, `shar`, `har_j`, `har_cj`, `ridge_har`, `lasso_har`
- **HAR-IV:** `har_iv`, `har_iv_1w`, `har_iv_0dte`, `har_iv_1dte`, `har_iv_0dte_1dte`, `har_iv_vvix`, `har_iv_skew`, `har_iv_term`, `har_iv_rich`, `har_iv_vrp`, `har_iv_kitchen`, `har_iv_freq`, `har_iv_freq_vrp`, `har_iv_optimal`, `har_iv_xasset`, `har_iv_ratevol`, `har_iv_1w_ratevol`, `har_iv_2tenor`, `har_iv_noise`
- **HAR-IV regularized:** `ridge_har_iv`, `ridge_har_iv_1w`, `ridge_har_iv_0dte`, `ridge_har_iv_xasset`, `ridge_har_iv_ratevol`, `lasso_har_iv`, `lasso_har_iv_1w`, `lasso_har_iv_0dte`, `lasso_har_iv_ratevol`, `elasticnet_har_iv`, `elasticnet_har_iv_1w`, `elasticnet_har_iv_0dte`
- **SHAR-IV:** `shar_iv`, `shar_iv_1w`, `shar_iv_0dte`, `shar_iv_freq`, `shar_cj_iv_0dte`, `shar_cj_iv_freq`, `shar_cj_iv_freq_vrp`
- **HARQ-IV:** `harq_iv`, `harq_iv_1w`
- **HAR-CJ-IV:** `har_cj_iv_0dte`, `har_cj_iv_freq`, `har_cj_iv_freq_vrp`
- **SHARQ-CJ-IV:** `sharq_cj_iv_0dte`, `sharq_cj_iv_freq`, `sharq_cj_iv_freq_vrp`
- **HARX-IV:** `harx_iv_h1`, `harx_iv_h5`, `harx_iv_h22`, `ridge_harx_iv_h1`, `ridge_harx_iv_h5`, `ridge_harx_iv_h22`, `lasso_harx_iv_h1`, `lasso_harx_iv_h5`, `lasso_harx_iv_h22`, `elasticnet_harx_iv_h1`, `elasticnet_harx_iv_h5`, `elasticnet_harx_iv_h22`
- **Generic HAR-X (config-driven):** `harx`, `ridge_harx`, `lasso_harx`, `elasticnet_harx` — requires `model.params.extra_features: list[str]` (may be `[]` for pure HAR core). Any listed column must be present in the feature matrix at fit time or `HARXModel` raises. Template: [workspace/configs/example_harx.yaml](../../workspace/configs/example_harx.yaml).
- **ML:** `lightgbm`, `lightgbm_dart`, `lightgbm_bagged`, `lightgbm_calibrated`, `xgboost`
- **Ensemble:** `stacking_har_lgbm`, `regime_blend`, `blend` (prediction-level blend of >=2 sub-models — see `blend` optional section)
- **Graph:** `ghar`, `gnn`, `gnn_learned`, `gnnhar`, `dcrnn_har`, `stid`, `gsp_har` — require the `graph:` block; `gnn`, `gnn_learned`, `gnnhar`, `dcrnn_har`, `stid`, `gsp_har` additionally require the `torch-geometric` extra (import is lazy inside `models/gnn.py`; its absence surfaces at GNN construction).
- **Deep:** `lstm`, `tcn`
- **Naive:** `ewma`, `same_day_rv`, `random_walk`, `vix_implied`, `atm_iv_implied`, `historical_mean`, `rolling_mean`, `median_rv`, `ar1`

### `cv.method`

`expanding_window` | `purged_kfold` | `rolling_window` | `blocked_kfold`

### `training_mode`

`pooled` | `per_symbol`

## Ordering Constraints

1. `iv_surface` **MUST** appear before `options` (provides IV data consumed by options layer)
2. `tree_expansion` **MUST** be the last layer (expands features from all preceding layers)
3. Other layers can be in any order

## Common Patterns

**HAR baseline (no ML):**
```yaml
feature_layers: [har_core]
model:
  name: har
  params: {}
```

**LightGBM tournament (standard):**
```yaml
feature_layers: [iv_surface, har_core, asymmetry, noise_robust, options, calendar, tree_expansion]
model:
  name: lightgbm
  params: { ... }
tournament:
  models: [ewma, har, har_j, ridge_har, lightgbm]
```

**LSTM residual (stacked on LightGBM base):**
```yaml
feature_layers: [iv_surface, har_core, asymmetry, noise_robust, options, calendar, tree_expansion]
model:
  name: lstm
  params:
    hidden_dim: 128
    n_layers: 2
    dropout: 0.2
    max_epochs: 50
    batch_size: 1024
    loss: qlike
    device: auto
    precision: auto
sequences:
  features: [log_ret, vol_share, buy_ratio, log_n_trades, abs_ret]
  max_bars: 2340
base_model:
  name: lightgbm
  feature_layers: [iv_surface, har_core, asymmetry, noise_robust, options, calendar, tree_expansion]
  params: { ... }
n_gpus: 8
```

**Per-horizon LightGBM init (CHAMPION pattern):**
```yaml
horizon_overrides:
  1:
    model:
      params:
        base_model: har_iv_0dte
  22:
    model:
      params:
        base_model: har_iv
```

**Tournament with SHAP/ALE explainability:**
```yaml
tournament:
  models: [har, har_iv, lightgbm]
  explainability:
    enabled: true
    methods: [treeshap, ale]
    treeshap_max_samples: 500
    treeshap_interaction: false
    ale_features: top_20
    ale_grid_size: 50
    models: [lightgbm]
```

### `tournament.explainability` fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `enabled` | bool | `false` | Master switch for explainability computation |
| `methods` | list[str] | `[treeshap, ale]` | Which methods to compute. Valid: `treeshap`, `ale` |
| `treeshap_max_samples` | int | `500` | Subsample OOS data for speed. `null` = use all |
| `treeshap_interaction` | bool | `false` | Compute SHAP interaction values (expensive) |
| `ale_features` | str or list | `"top_20"` | `"top_N"` or explicit list of feature names or `"all"` |
| `ale_grid_size` | int | `50` | Number of quantile bins for ALE |
| `models` | list[str] or null | `null` | Which models get explainability. `null` = all tree-based |

**LSTM feature stacking (LSTM features → LightGBM):**
```yaml
feature_layers: [iv_surface, har_core, asymmetry, noise_robust, options, microstructure, calendar, tree_expansion]
model:
  name: lightgbm
  params: { ... }
feature_stack:
  source_model: lstm
  outputs: [prediction, attention_entropy]
  independent: true
  model_params:
    hidden_dim: 128
    n_layers: 2
    dropout: 0.2
    bidirectional: true
    learning_rate: 3.0e-4
    max_epochs: 50
    batch_size: 256
    loss: qlike
    device: auto
  sequences:
    features: [log_ret, vol_share, buy_ratio, log_n_trades, abs_ret, rolling_vpin, price_accel]
    max_bars: 2340
```

### `model.params` — LSTM-specific knobs

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `length_bucket_n_buckets` | int | `16` | Length-bucketed shuffle bucket count for the training sampler. Reduces per-batch length variance so `pack_padded_sequence` does less work. Set to `1` to recover pure random shuffle (legacy behaviour). |
| `num_workers` | int | `0` | **Deprecated** — manual batching is used; non-zero values emit `DeprecationWarning` and have no effect. Will be removed in a future release. |

### `feature_stack` fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `source_model` | str | **required** | Model registry key (e.g. `"lstm"`) |
| `outputs` | list[str] | `["prediction"]` | Features to extract (see valid values below) |
| `embedding_dim` | int\|null | `null` | PCA-reduce embedding dimension |
| `independent` | bool | `true` | If false, LSTM also gets tabular base_preds |
| `model_params` | dict | `{}` | Source model hyperparameters |
| `sequences` | SequenceConfig\|null | `null` | Override top-level sequences config |

### `feature_stack.outputs` valid values

| Value | Columns produced | Description | Source model |
|-------|-----------------|-------------|--------------|
| `prediction` | `<src>_prediction` | Scalar log-RV prediction | lstm/tcn/gnn |
| `attention_entropy` | `lstm_attention_entropy` | Shannon entropy of attention weights | lstm only |
| `attention_peak_time` | `lstm_attention_peak_time` | Normalized argmax of attention | lstm only |
| `node_attention` | `gnn_node_attention` | Mean attention weight received per graph node | gnn only (requires the `torch-geometric` extra) |
| `embedding` | `<src>_embedding_0..N` | Pooled hidden state (N = hidden_dim or embedding_dim) | lstm/tcn/gnn |

### `sequences.features` valid values (v2 + v3) — `source: parquet` / `parquet_5min` / `parquet_5min_multiday`

| Feature | Source | Description |
|---------|--------|-------------|
| `log_ret` | v2 | Log return per 10s bar |
| `vol_share` | v2 | Volume share of session total |
| `buy_ratio` | v2 | Buy volume / total volume |
| `log_n_trades` | v2 | Log number of trades |
| `abs_ret` | v2 | Absolute return |
| `rolling_vpin` | v3 | 50-bar rolling VPIN (order flow toxicity) |
| `price_accel` | v3 | Return second-difference (momentum change) |
| `cum_rv` | v3 | Cumulative intraday realized variance |
| `session_frac` | v3 | Normalized session position [0, 1] |

### `sequences.features` valid values — `source: daily_lookback`

Daily-panel columns pulled from the feature matrix, one row per trading day, packed into a rolling `lookback_days` window (see `trial_068_gnn_standalone.yaml`).

| Feature | Description |
|---------|-------------|
| `log_rv_d` | Log realized variance, daily |
| `log_rv_w` | Log realized variance, weekly (5-day mean) |
| `log_rv_m` | Log realized variance, monthly (22-day mean) |
| `signed_return_d` | Daily signed close-to-close return |
| `abs_ret_d` | Daily absolute return |
| `log_rs_negative_d` | Log realized semivariance (negative side) |
| `log_jump_d` | Log daily jump component |
| `log_bpv_d` | Log daily bipower variation |
| `log_cont_d` | Log daily continuous variation |

### `sequences.source` enum

| Value | Bar interval | Panel width | Notes |
|-------|--------------|-------------|-------|
| `parquet` | 10s (default) | one RTH day | Legacy — pre-built intraday bar parquets |
| `parquet_5min` | 5-min | one RTH day | 10s bars aggregated on-the-fly to 5-min |
| `parquet_5min_multiday` | 5-min | `lookback_days` days | 5-min bars concatenated across trailing days (default 20 → 20×78 = 1,560 timesteps) |
| `daily_lookback` | one bar / day | `lookback_days` days | Rolling window built from daily panel columns — used by trial-068 GNN family |

### `sequences` top-level fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `features` | list[str] | `[log_ret, vol_share, buy_ratio, log_n_trades, abs_ret]` | Per-bar feature columns; see `sequences.features` tables above |
| `max_bars` | int | `2340` | Padding / truncation target per day (10s bars: 2340 = 6.5h × 360) |
| `bar_interval` | int | `10` | Bar interval in seconds (10 = 10s; 300 = 5-min) |
| `sequences_dir` | str \| null | `null` | Source parquet directory (default `data/raw/micro/sequences`) |
| `cache_dir` | str \| null | `null` | Tensor cache directory (default `data/processed/sequences`) |
| `norm_mode` | str | `"pooled"` | `pooled` \| `per_symbol` (see below) |
| `source` | str | `"parquet"` | See `sequences.source` enum table above |
| `lookback_days` | int | `20` | Trading days concatenated per sequence for `parquet_5min_multiday` / `daily_lookback` |
| `context_features` | list[str] | `[]` | Extra static per-day scalars injected alongside the sequence tensor |

### `sequences.norm_mode` (Phase 2.7+)

| Value | Default | Description |
|-------|---------|-------------|
| `pooled` | yes | Single (mean, std) across all symbols per fold. |
| `per_symbol` | no | Per-symbol (mean, std) fit on each symbol's training rows only (no leakage). Recommended for the production LSTM trials (51, 52, 53, 54, 57, 58). |

**Incompatibility:** `feature_stack` + `sequences.norm_mode: per_symbol` raises
`ValueError` at config construction. The feature-stack code path does NOT yet
thread `norm_mode` through to the stacked sequence model (planned for Phase
3.12). Either keep `norm_mode: pooled` when `feature_stack` is set, or drop
`feature_stack`.

### `tournament.model_configs` per-model `feature_stack_outputs`

When a top-level `feature_stack` is configured, tournament models can override
which LSTM outputs they see via `feature_stack_outputs` in their `model_configs` entry:

| Value | Behavior |
|-------|----------|
| `feature_stack_outputs: [prediction]` | Model only gets `lstm_prediction` column |
| `feature_stack_outputs: [prediction, attention_entropy]` | Model gets prediction + entropy |
| `feature_stack_outputs: []` | Model gets NO LSTM features (control) |
| *(field omitted)* | Model gets ALL outputs from top-level `feature_stack.outputs` |

**Rules:**
- Models NOT in `model_configs` (bare labels like `har`) never get feature_stack features
- The LSTM trains once per fold (output-agnostic cache) and columns are filtered per model
- `feature_stack_outputs` values must be a subset of the top-level `feature_stack.outputs`

**Example:**
```yaml
feature_stack:
  source_model: lstm
  outputs: [prediction, attention_entropy, attention_peak_time, embedding]
  # ...

tournament:
  models: [har, lgbm_control, lgbm_pred, lgbm_all]
  model_configs:
    lgbm_control:
      name: lightgbm
      params: { ... }
      feature_stack_outputs: []              # No LSTM features (control)
    lgbm_pred:
      name: lightgbm
      params: { ... }
      feature_stack_outputs: [prediction]    # Only scalar prediction
    lgbm_all:
      name: lightgbm
      params: { ... }
      # No feature_stack_outputs → gets ALL from feature_stack.outputs
```

**Optuna HPO:**
```yaml
tuning:
  enabled: true
  n_trials: 200
  n_jobs: 4
  inner_cv:
    method: expanding_window
    train_size: 252
    test_size: 63
```

---

## Schema Maintenance Rule

**When you modify any of the following, you MUST also update `workspace/configs/_CANONICAL_EXAMPLE.yaml`:**

- `src/volforecast/config.py` — any new field, renamed field, or changed default
- `src/volforecast/features/*.py` — any new `@register_feature_layer` decorator (new layer name)
- `src/volforecast/models/*.py` — any new `@register_model` decorator (new model name)

Update the relevant section in the canonical example: add the new field/value with a comment explaining it. This keeps the example as the single source of truth for agents writing configs.

---

## Source of Truth

- Schema dataclasses: src/volforecast/config.py
- Feature registry: `src/volforecast/features/*.py` (look for `@register_feature_layer`)
- Model registry: `src/volforecast/models/*.py` (look for `@register_model`)
