# Plan: Trial-068 — Conditional (Heteroscedastic) Duan Correction

## Problem Statement

The current Duan retransformation uses a **global scalar** per fold:
```python
correction = log(mean(exp(residuals)))  # single number for ALL samples in fold
preds += correction
```

This applies the same additive boost to calm-day and spike-day predictions alike. But the QLIKE-optimal forecast under conditional heteroscedasticity is:

$$h^*(x) = \exp(\hat{\mu}(x) + \sigma^2(x)/2)$$

where σ²(x) varies per sample. When σ²(x) is large (model uncertainty is high — event days, transitions), the correction should be LARGER. The current global correction systematically **under-corrects on the hardest days** that contribute 22% of total QLIKE loss.

## Hypothesis

Replacing the global Duan scalar with a per-sample conditional correction (estimated from a second XGBoost trained on squared OOS residuals) improves QLIKE at h=1 by 15–40 bps over the current champion (trial-067, 0.1292).

## Architecture

Two-stage pipeline (no new model class needed):

```
Stage 1: Champion XGBoost → OOS log-predictions per fold
Stage 2: Variance XGBoost → predicts σ²(x) = E[(y - ŷ)² | X]
Final:   pred_corrected = pred_stage1 + σ²_hat(x) / 2
```

The variance model trains on **OOS residuals** from Stage 1 (NOT in-sample). This avoids information leakage — the variance model learns "when will Stage 1 be uncertain?" from features available at prediction time.

## Acceptance Criteria

1. `./vol test -x -q -k conditional_duan` passes — unit tests for new correction logic
2. Trial-068 config runs end-to-end and produces QLIKE numbers
3. QLIKE at h=1 is compared to trial-067 baseline (0.1292) with DM test
4. If QLIKE improves ≥10 bps: PASS. If <10 bps or regresses: record finding, close.

## Scope Assessment

- **Files to modify:** 2 (runner.py + new variance model or correction module)
- **Files to create:** 3 (trial config YAML, test file, correction module)
- **Risk:** Medium — touches the prediction assembly path in runner.py

---

## Implementation Steps

### Step 1: Write failing tests for conditional Duan correction logic
**Mode:** `subagent`
```yaml
subtask_id: "execute-1"
goal: "Write unit tests for a conditional_duan_correction function that takes log-predictions and per-sample variance estimates and returns corrected predictions"
file_scope:
  - src/volforecast/evaluation/metrics.py  # existing retransform_log_to_level
  - src/volforecast/pipeline/runner.py     # lines 95-115 (current Duan in fold worker)
  - src/tests/integration/test_rv_pipeline.py  # existing Duan tests for pattern
write_scope:
  - src/tests/unit/test_conditional_duan.py
acceptance_criteria:
  - "Test file exists with ≥5 test cases"
  - "Tests cover: basic correction math, zero-variance degenerates to global, clipping extreme variance, array shape correctness, improvement over global on synthetic heteroscedastic data"
  - "Tests import from volforecast.evaluation.metrics (the module where the function will live)"
  - "Tests FAIL when run (function doesn't exist yet) — TDD"
memory_refs: []
constraints:
  - "Use ./vol test to verify tests are syntactically valid (expect ImportError or AttributeError, not SyntaxError)"
  - "Do NOT implement the function — only tests"
context_summary: "Current Duan is global scalar in runner.py:99-107. We're adding a conditional_duan_correction() to metrics.py that accepts per-sample σ²(x) estimates. The function signature: conditional_duan_correction(log_preds: ndarray, conditional_variance: ndarray) -> ndarray."
depends_on: []
```

### Step 2: Implement conditional Duan correction function
**Mode:** `subagent`
```yaml
subtask_id: "execute-2"
goal: "Implement conditional_duan_correction() in metrics.py and make the tests from Step 1 pass"
file_scope:
  - src/volforecast/evaluation/metrics.py  # add function here
  - src/tests/unit/test_conditional_duan.py  # tests to satisfy
write_scope:
  - src/volforecast/evaluation/metrics.py
acceptance_criteria:
  - "Function conditional_duan_correction(log_preds, conditional_variance) -> ndarray exists"
  - "Formula: log_preds + clip(conditional_variance, 0, max_var) / 2"
  - "max_var default = 1.0 (prevents insane corrections on outlier variance estimates)"
  - "./vol test -x -q -k test_conditional_duan passes all tests"
memory_refs: []
constraints:
  - "Pure numpy, no new dependencies"
  - "Add to existing metrics.py, don't create new module"
  - "Clip variance to [0, max_var] for safety — max_var=1.0 default"
context_summary: "metrics.py already has retransform_log_to_level (global version). The new function is a vectorized per-sample alternative. It returns corrected log-predictions (NOT level-space — the runner does the final exp)."
depends_on: ["execute-1"]
```

### Step 3: Implement variance model training in a two-stage pipeline runner mode
**Mode:** `subagent`
```yaml
subtask_id: "execute-3"
goal: "Add a 'two_stage_conditional_duan' mode to the pipeline that trains a second XGBoost on squared OOS residuals from Stage 1, then applies conditional correction"
file_scope:
  - src/volforecast/pipeline/runner.py  # main pipeline, understand fold assembly flow (lines 458-700)
  - src/volforecast/models/xgboost.py   # XGBoost model class
  - src/volforecast/config.py           # ExperimentConfig parsing
  - src/volforecast/evaluation/metrics.py  # the new conditional_duan_correction function
  - workspace/configs/trial_063_xgboost_champion.yaml  # base config pattern
write_scope:
  - src/volforecast/pipeline/conditional_duan.py  # NEW module for two-stage logic
  - src/volforecast/config.py  # add optional 'conditional_duan' config field
acceptance_criteria:
  - "New module conditional_duan.py exists with function run_conditional_duan_pipeline(config, stage1_results) -> corrected_preds"
  - "Function takes Stage 1 OOS predictions + actuals, trains variance XGBoost per fold on (features, squared_residuals), predicts σ²(x) on test set, applies conditional correction"
  - "Config schema accepts optional conditional_duan: {enabled: true, variance_model: {max_leaves: 8, n_estimators: 500, ...}}"
  - "Respects fold boundaries — variance model for fold k trains ONLY on OOS residuals from folds 1..k-1 (walk-forward to avoid leakage)"
  - "Falls back to global Duan if conditional_duan not enabled"
memory_refs:
  - memory/research/project-state.md
constraints:
  - "Do NOT modify the main fold execution path — this is a POST-PROCESSING step that runs AFTER all folds complete"
  - "The variance model uses a SIMPLE XGBoost (max_leaves=8, n_estimators=500) to avoid overfitting on residual targets"
  - "Walk-forward for variance model: fold k's variance estimate uses residuals from folds 1..k-1 as training data"
  - "No new dependencies"
context_summary: "The pipeline assembles OOS predictions across folds in runner.py:630. After all folds, we have the full OOS prediction vector (all_preds) and actuals (y). The conditional Duan module takes these, trains a lightweight variance model on earlier-fold residuals to predict per-sample σ², then replaces the global-corrected predictions with conditionally-corrected ones. The key anti-leakage requirement: fold k's correction uses a variance model trained ONLY on data from previous folds."
depends_on: ["execute-2"]
```

### Step 4: Write integration test for the two-stage pipeline
**Mode:** `subagent`
```yaml
subtask_id: "execute-4"
goal: "Write integration test verifying the conditional Duan pipeline runs end-to-end with synthetic data and produces different corrections for high-variance vs low-variance samples"
file_scope:
  - src/tests/integration/test_rv_pipeline.py  # existing pipeline tests for pattern
  - src/volforecast/pipeline/conditional_duan.py  # the new module
  - src/volforecast/evaluation/metrics.py  # conditional_duan_correction
write_scope:
  - src/tests/integration/test_conditional_duan_pipeline.py
acceptance_criteria:
  - "Test creates synthetic heteroscedastic data (calm regime + spike regime)"
  - "Verifies conditional correction is LARGER for spike-regime samples"
  - "Verifies conditional-corrected QLIKE < global-corrected QLIKE on heteroscedastic data"
  - "./vol test -x -q -k test_conditional_duan_pipeline passes"
memory_refs: []
constraints:
  - "Use small synthetic data (100 samples, 2 folds) for speed"
  - "Don't require GPU — mock or use CPU XGBoost"
context_summary: "The integration test should verify the mathematical claim: when residual variance is heteroscedastic (varies by regime), conditional correction outperforms global correction on QLIKE. Use synthetic log-RV with known conditional variance structure."
depends_on: ["execute-3"]
```

### Step 5: Create trial-068 config YAML and wire into runner
**Mode:** `subagent`
```yaml
subtask_id: "execute-5"
goal: "Create trial_068_conditional_duan.yaml config and wire the conditional_duan post-processing into the main Pipeline._run_horizon flow"
file_scope:
  - workspace/configs/trial_063_xgboost_champion.yaml  # base to copy
  - src/volforecast/pipeline/runner.py  # wire conditional_duan call after fold assembly
  - src/volforecast/pipeline/conditional_duan.py  # the module to call
  - src/volforecast/config.py  # config schema
write_scope:
  - workspace/configs/trial_068_conditional_duan.yaml
  - src/volforecast/pipeline/runner.py  # add ~10 lines after fold assembly
acceptance_criteria:
  - "Config YAML exists, is valid, matches champion settings + conditional_duan enabled"
  - "Runner calls conditional_duan post-processing when config.conditional_duan.enabled == True"
  - "Runner falls back to existing behavior when field absent or disabled"
  - "./vol test -x -q passes (no regression in existing tests)"
memory_refs: []
constraints:
  - "Minimal surgery to runner.py — add at most 15 lines in the post-fold-assembly section"
  - "Config inherits ALL champion hyperparams (trial-063 base)"
  - "horizons: [1] only for first validation"
  - "Variance model params: {max_leaves: 8, n_estimators: 500, learning_rate: 0.05, min_child_weight: 200}"
context_summary: "The wiring point is runner.py after line ~635 where all_preds is assembled. If config has conditional_duan enabled, call the post-processing function to replace all_preds with conditionally-corrected values. The trial config is a copy of trial-063 with the addition of the conditional_duan section."
depends_on: ["execute-3", "execute-4"]
```

### Step 6: Run trial-068 and record results
**Mode:** `inline`
```yaml
subtask_id: "execute-6"
goal: "Execute trial-068 on GPU, compare QLIKE to trial-067 baseline, record in trials.yaml"
depends_on: ["execute-5"]
```

---

## Dependency Graph

```
Step 1 (tests) ─────────────┐
                             ▼
Step 2 (implement function) ─┐
                             ▼
Step 3 (variance pipeline) ──┬──► Step 5 (config + wiring) ──► Step 6 (run)
                             │
Step 4 (integration test) ───┘
```

Steps 1 → 2 → 3 sequential (each depends on prior).
Steps 4 depends on 3 only (can be parallelized with 5 if 3 is done).
Step 5 depends on 3 AND 4. Step 6 depends on 5.

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Variance model overfits to residual noise | Small capacity (max_leaves=8), heavy regularization, walk-forward |
| Conditional correction makes calm-day predictions WORSE | Compare per-regime QLIKE breakdown; if calm-day regresses >5 bps, blend conditional+global |
| Information leakage from variance model | Strict walk-forward: fold k uses only folds 1..k-1 residuals |
| Pipeline regression | Full test suite gate before trial execution |

## Expected Outcome

Conservative: +10–15 bps at h=1 (from spike-day correction alone)
Optimistic: +25–40 bps at h=1 (if variance model accurately predicts forecast uncertainty)

Even the conservative case would push h=1 from 0.1292 to ~0.1277 — a meaningful step toward the 0.12 barrier.
