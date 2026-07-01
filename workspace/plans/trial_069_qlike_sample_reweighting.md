# Plan: Trial-069 — QLIKE-Importance Sample Reweighting

## Scope

Add infrastructure to pass per-sample weights to XGBoost (and LightGBM) training, then run an experiment where the second-pass model trains with weights derived from the first-pass conditional QLIKE residuals.

**Acceptance Criteria:**
1. `sample_weight` config key accepted in YAML and threaded through config → runner → model → DMatrix/Dataset
2. Two-pass "reweight" mode: first-pass model scores training set, computes per-sample conditional QLIKE, applies `weight = qlike_i^α`
3. Tests cover: weight passthrough, two-pass logic, edge cases (all-zero weights, NaN protection)
4. Trial-069 config runs without errors for h=1, reports QLIKE + DM test vs trial-067 baseline
5. Three α variants tested: 0.5, 1.0, 2.0

---

## Design

### Architecture

The reweighting is **NOT** a second XGBoost pass from scratch. It's a **fold-internal two-pass**:

```
Per fold:
  1. Fit model_pass1 on (X_train, y_train) — no weights (standard)
  2. Predict on X_train → train_preds
  3. Compute per-sample conditional QLIKE:
       qlike_i = exp(y_train_i - train_pred_i) - (y_train_i - train_pred_i) - 1
     This is the RESIDUAL QLIKE after the base model (HAR-IV init + first pass),
     so it measures "how badly did the tree correct this sample?"
  4. sample_weight_i = qlike_i^α  (with floor clipping to avoid zero/negative)
  5. Fit model_pass2 on (X_train, y_train, sample_weight) — same hyperparams
  6. Predict X_test with model_pass2 → fold OOS predictions
```

**Why conditional QLIKE (not raw)?** Raw QLIKE includes the part explained by HAR-IV init. A sample might have high raw QLIKE because it's a black swan (init was wrong), but the tree can't help with that. Conditional QLIKE isolates samples where the tree *should* do better — the correctable hard cases.

### Config Schema Extension

```yaml
model:
  params:
    sample_reweight:
      enabled: true
      alpha: 1.0               # weight = qlike_i^alpha
      source: "conditional"    # "conditional" (residual after pass1) or "raw" (from init only)
      clip_max: 10.0           # cap weights to prevent outlier dominance
      normalize: true          # rescale weights to mean=1 (preserve effective sample size)
```

This goes in `model.params` (open dict) so no config schema dataclass changes needed — just parsed inside the model `fit()` method.

### Key Design Decisions

1. **Weight in model, not runner:** The two-pass logic lives inside `XGBoostVolModel.fit()` (and analogously `LightGBMVolModel.fit()`). The runner doesn't need to know about it — it just calls `model.fit(X_train, y_train)` as before. The model internally runs pass 1, computes weights, and retrains.

2. **DMatrix weight support:** XGBoost's `xgb.DMatrix(..., weight=w)` is the native API. No gradient hacking needed — this changes the split criterion (weighted gain), not the objective.

3. **Normalization:** Weights are rescaled to `mean=1` so that the effective regularization strength doesn't change. Without this, large α inflates total weight and makes `min_child_weight` effectively smaller.

4. **Floor clip:** `max(qlike_i, 1e-4)` before raising to α, to avoid zero-weight samples that would be completely ignored. Ceiling clip at `clip_max` to cap outlier influence.

---

## Implementation Steps

### Step 1: XGBoost `sample_weight` support (model layer)
**Mode: subagent**

```yaml
subtask_id: "execute-1"
goal: "Add two-pass QLIKE reweighting to XGBoostVolModel.fit()"
file_scope:
  - src/volforecast/models/xgboost.py
write_scope:
  - src/volforecast/models/xgboost.py
acceptance_criteria:
  - "XGBoostVolModel.fit() parses sample_reweight from self.params"
  - "When enabled: fit pass1, compute conditional QLIKE per sample, compute weights, refit pass2 with DMatrix weight= arg"
  - "When disabled (default): no behavior change — single-pass as today"
  - "Weight normalization (mean=1) and clipping (floor 1e-4, ceiling clip_max) applied"
  - "Val set does NOT get reweighted (only training rows)"
  - "Init score (base_margin) carried to pass2 identically"
memory_refs: []
constraints:
  - "Do not change the fit() signature (X, y, on_progress only)"
  - "Do not change any behavior when sample_reweight is absent or disabled"
  - "Weights go into DMatrix constructor weight= param, NOT into the objective"
context_summary: "XGBoostVolModel.fit() at xgboost.py:281 trains one pass with custom QLIKE objective. DMatrix is created at line 321/353. Init scores (base_margin) set at lines 325-326. The model stores params in self.params dict. The reweight config will be nested under self.params['sample_reweight']."
depends_on: []
```

### Step 2: LightGBM `sample_weight` support (model layer)
**Mode: subagent**

```yaml
subtask_id: "execute-2"
goal: "Add two-pass QLIKE reweighting to LightGBMVolModel.fit()"
file_scope:
  - src/volforecast/models/lightgbm.py
write_scope:
  - src/volforecast/models/lightgbm.py
acceptance_criteria:
  - "LightGBMVolModel.fit() parses sample_reweight from self.params"
  - "When enabled: fit pass1, compute conditional QLIKE per sample, compute weights, refit pass2 with lgb.Dataset weight= arg"
  - "When disabled (default): no behavior change"
  - "Same normalization/clipping logic as XGBoost"
  - "Val set does NOT get reweighted"
  - "Init score carried to pass2 identically"
memory_refs: []
constraints:
  - "Do not change the fit() signature"
  - "lgb.Dataset(..., weight=weights) is the native API"
context_summary: "LightGBMVolModel.fit() at lightgbm.py:420. Dataset created at line 470/501. Init score set at lines 470-471. Same pattern as XGBoost but with LightGBM Dataset API."
depends_on: []
```

### Step 3: Unit tests for reweighting
**Mode: subagent**

```yaml
subtask_id: "execute-3"
goal: "Write tests for two-pass QLIKE reweighting in both XGBoost and LightGBM"
file_scope:
  - src/tests/
  - src/volforecast/models/xgboost.py
  - src/volforecast/models/lightgbm.py
write_scope:
  - src/tests/test_sample_reweight.py
acceptance_criteria:
  - "Test: XGBoost with sample_reweight disabled produces same results as before"
  - "Test: XGBoost with sample_reweight enabled produces different predictions (weights have effect)"
  - "Test: weights are normalized to mean=1"
  - "Test: weights are clipped at floor and ceiling"
  - "Test: conditional mode computes QLIKE from pass1 residuals (not raw target)"
  - "Test: LightGBM same suite"
  - "All tests pass via ./vol test -k test_sample_reweight"
memory_refs: []
constraints:
  - "Use synthetic data (small N, fast) to avoid needing real parquets"
  - "TDD: write tests BEFORE step 1/2 implementation if running sequentially, otherwise verify after"
context_summary: "Tests go in src/tests/. Use pytest. Models need small DataFrames with ~200 rows to fit quickly. The test should verify that weights actually change the model output (fit with uniform weights vs QLIKE-derived weights should produce different predictions on the same data)."
depends_on: ["execute-1", "execute-2"]
```

### Step 4: Experiment config for trial-069
**Mode: inline**

```yaml
subtask_id: "execute-4"
goal: "Create trial_069 YAML configs (3 alpha variants) for QLIKE sample reweighting"
file_scope:
  - workspace/configs/trial_063_xgboost_champion.yaml
write_scope:
  - workspace/configs/trial_069a_xgb_reweight_alpha05.yaml
  - workspace/configs/trial_069b_xgb_reweight_alpha10.yaml
  - workspace/configs/trial_069c_xgb_reweight_alpha20.yaml
acceptance_criteria:
  - "Each config is a copy of trial-063 XGBoost champion with sample_reweight added"
  - "Three variants: alpha=0.5, alpha=1.0, alpha=2.0"
  - "All use source='conditional', clip_max=10.0, normalize=true"
  - "h=1 only (fastest to validate, matches trial-067 champion)"
  - "Horizon override for h=1: base_model=har_iv_0dte (same as champion)"
  - "Tournament includes har_iv baseline for DM comparison"
memory_refs: []
constraints:
  - "Follow yaml-config.instructions.md ordering and enum rules"
  - "universe and date_range identical to trial-063"
context_summary: "Trial-063 YAML is the XGBoost champion config. Copy it, add sample_reweight block under model.params, restrict to horizons=[1] for speed."
depends_on: ["execute-1"]
```

### Step 5: Trial registry entry
**Mode: inline**

```yaml
subtask_id: "execute-5"
goal: "Add trial-069 entries to workspace/research/trials.yaml"
file_scope:
  - workspace/research/trials.yaml
write_scope:
  - workspace/research/trials.yaml
acceptance_criteria:
  - "trial-069a/b/c entries added with hypothesis, motivation, status=NOT_STARTED"
  - "Baseline = trial-067 (XGBoost h=1 champion)"
memory_refs: []
constraints:
  - "Append at end of trials list"
context_summary: "Trial registry is a YAML list. Each entry has id, date, config, hypothesis, motivation, horizons, baseline_config, status, priority, depends_on, key_insight fields."
depends_on: ["execute-4"]
```

---

## Dependency Graph

```
Step 1 (XGBoost reweight) ─────┐
                                ├──→ Step 3 (tests) ──→ Step 5 (registry)
Step 2 (LightGBM reweight) ────┘         │
                                          │
Step 4 (configs) ─── depends on Step 1 ───┘
```

Steps 1 & 2 are parallel (independent models).
Step 3 depends on 1 + 2 (needs the implementation to test).
Step 4 depends on 1 (config references XGBoost feature).
Step 5 depends on 4 (needs config file names).

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| α=2.0 overfits to outlier days (COVID spikes) | clip_max=10 caps any single weight; normalize=true preserves effective N |
| Two-pass doubles training time per fold | Acceptable: XGBoost h=1 trains in ~2min/fold, so +2min/fold × 8 folds = 16min total overhead |
| Pass1 in-sample predictions are overfit (low bias) → conditional QLIKE is artificially low | Use val_fraction split: pass1 trains on train[:split], scores train[split:] for weights. OR accept that in-sample residuals are a floor estimate — still directionally correct for reweighting |
| Weight explosion for extreme α on fat-tailed QLIKE distribution | normalize=true + clip_max. Also test α=0.5 as conservative variant |

---

## Expected Outcome

- **Base case (α=1.0):** 10–30 bps improvement at h=1 (forces splits on high-QLIKE regimes: earnings, FOMC, VIX spikes)
- **Conservative (α=0.5):** 5–15 bps, lower risk of overfitting
- **Aggressive (α=2.0):** 15–40 bps potential, higher variance — may degrade if outlier days are uncorrectable

**Success criterion:** Any α variant beats trial-067 (0.1292) with DM p < 0.05.
**Fail criterion:** All variants degrade or show < 5 bps improvement without significance.

---

## Recommended Execution

`/execute` with this plan. Steps 1+2 in parallel → Step 3 → Steps 4+5 in parallel.
