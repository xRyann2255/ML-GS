---
name: EVALUATE
description: "Run evaluation suite on trained volatility models. USE FOR: QLIKE/MSE computation, Diebold-Mariano tests, Model Confidence Set, tournament tables, overfitting detection. DO NOT USE FOR: model training (use MODEL_TRAIN), economic value testing (use BACKTEST), data fetching (use DATA_INGEST)."
---

# EVALUATE — Model Evaluation Suite

> **Purpose:** Run the full evaluation suite on trained volatility forecasting models. Computes QLIKE (primary) and MSE (secondary), runs Diebold-Mariano pairwise significance tests, determines Model Confidence Set membership, and formats results as tournament tables.

**Out of scope:** Model training (use MODEL_TRAIN), economic value testing (use BACKTEST), feature computation (use FEATURE_BUILD).

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `EVALUATE` |
| **Scope** | Statistical evaluation and model comparison |
| **Inputs** | JSON args: model path(s), test data, metrics list |
| **Outputs** | QLIKE/MSE tables, DM test results, MCS membership in `workspace/tmp/` |
| **Authority** | Read-only — reads model predictions, writes evaluation reports |

## When to Use

- Computing QLIKE and MSE for a trained model against test data
- Running Diebold-Mariano tests between model pairs
- Determining Model Confidence Set (MCS) membership
- Generating tournament tables for model comparison
- Checking for overfitting (deflated Sharpe ratio, in-sample vs out-of-sample gap)

## When NOT to Use

- Training models — use MODEL_TRAIN
- Testing economic value of signals — use BACKTEST
- Exploring data or features — use RESEARCH or NOTEBOOK

## Memory References

| File | Content |
|------|--------|
| `workspace/docs/vol-project-ref/INDEX.md` | Authoritative project spec — ch13 has definitive evaluation methodology, QLIKE formula, DM/MCS protocols, purged CV specs |
| `workspace/docs/vol-learning-guide/INDEX.md` | Comprehensive theory & equations — Ch16 has full QLIKE derivation, Patton (2011) proxy robustness proof, DM test statistic derivation, MCS algorithm, HAC variance, purged CV rationale |
| `memory/research/evaluation-framework.md` | QLIKE formula, DM/MCS methodology, success targets (30-80 bps) |
| `memory/research/volatility.md` | Model rankings, where ML wins/loses |
| `memory/research/complete-pipeline.md` | Evaluation position in the pipeline |

## Args File Format

Write JSON to `workspace/tmp/eval_args.json`:

```json
{
  "models": [
    { "name": "HAR", "predictions_file": "workspace/tmp/models/har_preds.parquet" },
    { "name": "HARQ", "predictions_file": "workspace/tmp/models/harq_preds.parquet" },
    { "name": "LightGBM_L012", "predictions_file": "workspace/tmp/models/lgbm_preds.parquet" }
  ],
  "actuals_file": "workspace/tmp/features/test_actuals.parquet",
  "target": "log_rv_1d",
  "metrics": ["qlike", "mse", "mae", "r2"],
  "tests": ["dm", "mcs"],
  "dm_params": {
    "benchmark": "HAR",
    "loss_function": "qlike",
    "significance": 0.05
  },
  "mcs_params": {
    "alpha": 0.1,
    "bootstrap_reps": 1000
  },
  "out_dir": "workspace/tmp/evaluation",
  "out_file": "workspace/tmp/eval_out.txt"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `models` | Yes | Array of model entries with name and predictions file path |
| `actuals_file` | Yes | Path to actual RV values (Parquet) |
| `target` | Yes | Target variable name in actuals |
| `metrics` | Yes | Array of metrics: `qlike`, `mse`, `mae`, `r2` |
| `tests` | No | Statistical tests: `dm` (Diebold-Mariano), `mcs` (Model Confidence Set) |
| `dm_params` | No | DM test config: benchmark model, loss function, significance level |
| `mcs_params` | No | MCS config: significance level, bootstrap repetitions |
| `out_dir` | No | Output directory (default: `workspace/tmp/evaluation`) |
| `out_file` | No | Path for evaluation log |

## Metrics

### QLIKE (Primary)

$$QLIKE = \frac{1}{T} \sum_{t=1}^{T} \left( \frac{RV_t}{\hat{\sigma}_t^2} - \log\frac{RV_t}{\hat{\sigma}_t^2} - 1 \right)$$

- Penalizes underestimation more than overestimation (asymmetric)
- Robust to proxy noise in RV
- Lower is better
- **Target improvement:** 30–80 bps over HAR baseline

### MSE (Secondary)

$$MSE = \frac{1}{T} \sum_{t=1}^{T} (RV_t - \hat{\sigma}_t^2)^2$$

- Symmetric loss — reported for comparison only
- Not used as primary optimization target

### Additional Metrics

- **MAE:** Mean absolute error
- **R²:** Coefficient of determination (out-of-sample)

## Statistical Tests

### Diebold-Mariano (DM)

- Pairwise test for equal predictive accuracy
- Uses QLIKE loss differentials
- HAC standard errors for serial correlation
- Reports: test statistic, p-value, significance at 1%/5%/10%

### Model Confidence Set (MCS)

- Hansen et al. (2011) procedure
- Identifies the set of models with statistically indistinguishable performance
- Reports: MCS p-value for each model, included/excluded status
- `alpha = 0.1` by default

## Output Artifacts

| File | Content |
|------|---------|
| `tournament_table.md` | Markdown table of all models ranked by QLIKE |
| `dm_results.json` | Pairwise DM test statistics and p-values |
| `mcs_results.json` | MCS p-values and membership |
| `eval_out.txt` | Human-readable evaluation summary |

### Tournament Table Format

```
| Rank | Model         | QLIKE  | ΔQLIKE vs HAR | MSE    | MCS p-val | MCS Member |
|------|---------------|--------|---------------|--------|-----------|------------|
| 1    | LightGBM_L012 | 0.4523 | -65 bps       | 0.0312 | 1.000     | ✓          |
| 2    | HARQ          | 0.4588 | -0 bps        | 0.0335 | 0.342     | ✓          |
| 3    | HAR           | 0.4588 | baseline      | 0.0341 | 0.118     | ✓          |
```

## Overfitting Checks

This skill also checks for:

1. **In-sample vs out-of-sample gap:** Flag if in-sample QLIKE is >20% better than OOS
2. **Deflated Sharpe ratio (DSR):** For signal-based models, compute DSR to account for multiple testing
3. **Feature importance stability:** Flag if top-5 features vary >50% across CV folds

## Task-Based Execution

1. **Write args file** to `workspace/tmp/eval_args.json`
2. **Run task:** `run_task("evaluate", workspaceFolder: "h:\ml-vol-estimator")`
3. **Read output:** Check `workspace/tmp/eval_out.txt` for results

## Links

- memory/research/evaluation-framework.md — QLIKE, DM tests, MCS, purged CV
