---
name: MODEL_TRAIN
description: "Train volatility forecasting models with proper cross-validation. USE FOR: HAR/HARQ/SHAR baselines, Ridge/Lasso HAR, LightGBM with QLIKE objective, LSTM/TCN for intraday sequences, ensemble blending. DO NOT USE FOR: data fetching (use DATA_INGEST), feature computation (use FEATURE_BUILD), evaluation (use EVALUATE)."
---

# MODEL_TRAIN — Model Training with Proper CV

> **Purpose:** Train volatility forecasting models with enforced cross-validation protocols. Supports HAR-family baselines, regularized linear models, LightGBM with custom QLIKE objective, LSTM/TCN for intraday sequences, and prediction-level ensemble blending.

**Out of scope:** Data fetching (use DATA_INGEST), feature computation (use FEATURE_BUILD), evaluation suite (use EVALUATE), economic value testing (use BACKTEST).

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `MODEL_TRAIN` |
| **Scope** | Model training with CV protocol enforcement |
| **Inputs** | JSON args: model type, feature config, CV strategy |
| **Outputs** | Trained model artifact + metrics JSON in `workspace/tmp/` |
| **Authority** | Compute-only — reads feature data, writes model artifacts |

## When to Use

- Training any baseline model (HAR, HARQ, SHAR, HAR-J, HAR-CJ)
- Training regularized linear models (Ridge-HAR, Lasso-HAR)
- Training LightGBM with custom QLIKE objective
- Training LSTM/TCN on intraday E-mini sequences
- Building prediction-level ensemble
- Hyperparameter tuning with purged k-fold CV

## When NOT to Use

- Computing features — use FEATURE_BUILD first
- Running evaluation metrics — use EVALUATE after training
- Quick exploration — use RESEARCH or NOTEBOOK

## Non-Negotiable Constraints

These are enforced by this skill and cannot be overridden:

1. **Never random k-fold.** Always purged/blocked k-fold or expanding-window walk-forward. Random k-fold causes catastrophic look-ahead bias on time-series data.
2. **Train in log-RV space.** All targets are $\log(RV)$. Predictions are exponentiated only for final reporting.
3. **QLIKE is the primary objective.** For LightGBM, use custom QLIKE objective. For linear models, QLIKE is evaluated post-training.
4. **COVID regime handling must be explicit.** Every training run states whether Feb–Jun 2020 is included, excluded, or handled as a separate regime.
5. **Full reproducibility.** Log all hyperparameters, random seeds, data splits, and feature lists.

## Memory References

| File | Content |
|------|--------|
| `workspace/docs/vol-project-ref/INDEX.md` | Authoritative project spec — drill into ch09 (LightGBM), ch10 (LSTM), ch11 (ensemble), ch13 (evaluation) for definitive model specs and training protocols |
| `workspace/docs/vol-learning-guide/INDEX.md` | Comprehensive theory & equations — Ch6 (HAR family derivations), Ch11 (LightGBM/custom QLIKE objective), Ch12b (LSTM/TCN/attention), Ch13 (ensemble stacking/blending), Ch16 (QLIKE/DM/MCS formulas) |
| `memory/research/evaluation-framework.md` | QLIKE formula, purged CV protocol, walk-forward |
| `memory/research/optimal-feature-set.md` | Feature layers, model architecture |
| `memory/research/volatility.md` | HAR family specs, where ML wins/loses |
| `memory/research/complete-pipeline.md` | End-to-end diagram, retraining protocol |

## Args File Format

The wrapper is a thin adapter over `skills/_shared/vf_entry.py`, which invokes
`python -m volforecast <argv>` with the argv you supply. All training/tuning knobs
(model type, features, CV, targets, COVID handling) live inside the pipeline YAML
referenced by `--config`, not the args file. See `workspace/configs/` for examples.

Write JSON to `workspace/tmp/train_args.json` (the exact `--args-file` value in
the `model-train` task definition):

```json
{
  "argv": ["run", "--config", "workspace/configs/<trial>.yaml", "--skip-ingest"],
  "out_file": "workspace/tmp/model_train_out.txt"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `argv` | Yes | Argument vector passed verbatim to `volforecast.__main__.main`. See `./vol help` and `python -m volforecast --help` for subcommands (`run`, `experiments`, `compare`, …). |
| `out_file` | Yes | Path where captured stdout+stderr will be written. Final line will be `EXIT_CODE=<rc>`; success iff `EXIT_CODE=0`. |

> **Concurrency caveat (last-writer-wins):** The args file path is fixed per task —
> two concurrent agents writing it race (last writer wins). Keep `out_file` unique
> per run (put a `run_id` slug in its name, e.g. `workspace/tmp/model_train_out_<run_id>.txt`
> where `run_id` matches `[a-z0-9-]+`); the args file itself is not collision-safe.

**Reading results:** `read_file(out_file)`; the run succeeded iff its final line is `EXIT_CODE=0`.

## Model Types

### Baselines (OLS)

| Model | Features | Formula |
|-------|----------|---------|
| `har` | Layer 0 | $\log RV_{t+1} = \beta_0 + \beta_d \log RV_t^{(d)} + \beta_w \log RV_t^{(w)} + \beta_m \log RV_t^{(m)}$ |
| `harq` | Layer 0 | HAR + $\beta_{RQ} \sqrt{RQ_t} \cdot \log RV_t^{(d)}$ |
| `shar` | Layer 0+1 | HAR with $RS^+$ and $RS^-$ replacing $RV^{(d)}$ |
| `har_j` | Layer 0+1 | HAR + jump component $J_t$ |
| `har_cj` | Layer 0+1 | HAR + continuous $C_t$ and jump $J_t$ separation |

### Regularized Linear

| Model | Method |
|-------|--------|
| `ridge` | Ridge regression (L2) on full feature matrix |
| `lasso` | Lasso regression (L1) on full feature matrix |

### ML Models

| Model | Architecture |
|-------|-------------|
| `lightgbm` | Gradient boosting with custom QLIKE objective/gradient |
| `lstm` | LSTM network for intraday E-mini sequences |
| `tcn` | Temporal convolutional network for intraday sequences |

### Ensemble

| Model | Method |
|-------|--------|
| `ensemble` | Prediction-level blending of HAR-family + LightGBM + LSTM |

## CV Strategies

### `purged_kfold`

- Time-aware k-fold with purge gap between train/test folds
- `purge_gap`: Number of days removed between train and test to prevent leakage
- `embargo_pct`: Fraction of test set size to embargo at the end of each train fold

### `expanding_window`

- Walk-forward with growing training window
- `initial_train_pct`: Fraction of data for initial training window
- `step_size`: Number of days to advance test window

### `rolling_window`

- Fixed-size rolling training window
- `window_size`: Number of days in training window
- `step_size`: Number of days to advance

## Output Artifacts

Training produces:

| File | Content |
|------|---------|
| `model_<type>_<timestamp>.pkl` | Serialized model object |
| `metrics_<type>_<timestamp>.json` | QLIKE, MSE, R², feature importances, CV fold results |
| `config_<type>_<timestamp>.json` | Full training config for reproducibility |
| `train_out.txt` | Human-readable training log |

## Task-Based Execution

1. **Write args file** to `workspace/tmp/train_args.json`
2. **Run task:** `run_task("model-train")`
3. **Read output:** `read_file("workspace/tmp/model_train_out.txt")` — success iff last line is `EXIT_CODE=0`.

## Links

- memory/research/evaluation-framework.md — QLIKE, CV protocol, statistical tests
- memory/research/volatility.md — estimators, baselines, ML methods
