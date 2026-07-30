# Plan: GNN Per-Fold Feature Normalisation

**Date:** 2026-07-28
**Status:** PLANNED
**Trial ID:** trial-102

---

## Problem Statement

All GNN trials that don't stack into XGBoost produce poor QLIKE scores:

| Trial | Model | h=1 QLIKE | h=5 QLIKE | h=22 QLIKE | Notes |
|-------|-------|-----------|-----------|------------|-------|
| 083 | GNNHAR | 0.1837 | 0.1606 | 0.1348 | Matches HAR but never beats it |
| 084 | GNNHAR variants | 0.1606 | 0.1348 | 0.1837 | Same story |
| 091 | GNNHAR + Glasso | **0.4367** | **0.4135** | **0.3785** | Catastrophic |
| 095 | GNNHAR regime | **0.4427** | **0.3283** | **0.3334** | Catastrophic |

Meanwhile stacked GNN → XGBoost works fine (trial-089: 0.129/0.108/0.177) because XGBoost is scale-invariant.

**Root cause:** The GNN pipeline passes raw unnormalised features to the neural network. Both pipeline paths (`_run_one_horizon_graphs` and the feature-stack GNN builder) zero-fill NaNs but apply NO standardisation. The LSTM path explicitly applies per-fold train-fitted z-score normalisation (`fit_seq_normaliser` / `apply_normaliser`).

**Evidence:**
- `runner.py:2204` — `node_features = np.nan_to_num(node_features, nan=0.0)` (feature-stack path)
- `graph_data.py:73` — `x_all = np.nan_to_num(x_all, nan=0.0)` (native graph path)
- Neither path applies StandardScaler / z-score

---

## Scope

### What this plan addresses:

1. **Per-fold z-score normalisation for GNN node features** — fit scaler on train dates only, apply to train+test graphs (same discipline as LSTM path)
2. **Both GNN pipeline paths** — the native path (`_run_one_horizon_graphs` / `build_graph_dataset`) and the feature-stack path (`_build_gnn_feature_stack_fn`)
3. **Ablation trial** — re-run GNNHAR with normalisation to validate the fix
4. **Backward compatibility** — normalisation controlled by config flag (default: enabled for new trials, disabled for reproducing old results)

### What's OUT of scope:

- In-network normalisation (LayerNorm/BatchNorm inside GNN modules) — trial-100 showed this doesn't help for LSTM; same reasoning applies
- Changing GNN architectures or hyperparameters
- Fixing the stacking path (it already works because XGBoost is scale-invariant)

---

## Acceptance Criteria

- [ ] GNN trials in trials.yaml reset from `status: completed` to `status: rerun_pending` (trials 080, 083, 091, 094, 095)
- [ ] Fold cache cleared for all GNN configs (`vol cache-clear --config <yaml>` for each)
- [ ] New `graph_norm_mode` config field: `"per_fold"` (default) | `"none"` 
- [ ] Native graph path (`_run_one_horizon_graphs`): fits StandardScaler on train-fold node features, applies to train and test graphs
- [ ] Feature-stack GNN path (`_build_gnn_feature_stack_fn`): same per-fold normalisation
- [ ] Scaler fitted on train dates ONLY (no data leakage)
- [ ] Existing tests pass unchanged
- [ ] New unit test verifies normalisation is applied correctly (train mean≈0, std≈1)
- [ ] New unit test verifies scaler is NOT fit on test data
- [ ] Trial-102 config created (GNNHAR + normalisation)
- [ ] Trial-102 executed: QLIKE improvement documented
- [ ] Gate: GNNHAR h=1 QLIKE < 0.170 (> 13 bps improvement over 0.1837)

---

## Implementation Plan

### Step 0a: Reset GNN trial statuses in trials.yaml (inline)

```yaml
subtask_id: "execute-0a"
goal: "Reset GNN trial entries from 'completed' to 'rerun_pending' so vol run re-registers results"
file_scope:
  - workspace/research/trials.yaml (lines for trials 080, 083, 091, 094, 095)
write_scope:
  - workspace/research/trials.yaml
acceptance_criteria:
  - "trial-080 status changed from 'completed' to 'rerun_pending'"
  - "trial-083 status changed from 'completed' to 'rerun_pending'"
  - "trial-091 status changed from 'completed' to 'rerun_pending'"
  - "trial-094 status changed from 'completed' to 'rerun_pending'"
  - "trial-095 status changed from 'completed' to 'rerun_pending'"
  - "No other trials modified"
memory_refs: []
constraints:
  - "Only change status field — do not modify hypothesis, horizons, or other metadata"
  - "rerun_pending status ensures vol run's register_new_trial/update_trial_from_metrics will overwrite with new results"
context_summary: "The CLI's register_new_trial() skips entries with status=='COMPLETED'. Changing to 'rerun_pending' allows the next vol run to re-register fresh results. The trials to reset are: 080 (GNN native), 083 (GNNHAR vs GHAR), 091 (GNNHAR Glasso), 094 (GNN grand tournament), 095 (GNNHAR regime)."
depends_on: []
```

### Step 0b: Clear fold cache for GNN configs (inline)

```yaml
subtask_id: "execute-0b"
goal: "Clear cached fold predictions for all GNN experiment configs so models retrain from scratch"
file_scope:
  - workspace/configs/trial_080_gnn_native.yaml
  - workspace/configs/trial_083_gnnhar_vs_ghar_stid.yaml
  - workspace/configs/trial_091a_gnnhar_glasso.yaml
  - workspace/configs/trial_090_gnn_grand_tournament.yaml
  - workspace/configs/trial_090b_gnnhar_regime.yaml
write_scope: []
acceptance_criteria:
  - "vol cache-clear --config <yaml> --yes executed for each GNN config"
  - "All cached fold entries for these configs removed"
  - "Confirmation output shows N entries cleared per config"
memory_refs: []
constraints:
  - "Use ./vol cache-clear --config <path> --yes for each config"
  - "Do NOT use --all (that would clear non-GNN caches too)"
  - "If a config has no cached folds (never used fold cache), that's fine — 0 entries cleared"
context_summary: "The fold cache (managed by pipeline/fold_cache.py) stores per-fold predictions keyed by config fingerprint. When cache hits exist, the runner skips training and returns cached preds. Clearing forces actual retraining. GNN models that ran before normalisation was added have stale cached results that must be purged."
depends_on: []
```

### Step 1: Add `graph_norm_mode` to config schema (subagent)

```yaml
subtask_id: "execute-1"
goal: "Add graph_norm_mode field to GraphConfig in the config module"
file_scope:
  - src/volforecast/config.py (GraphConfig dataclass / section)
write_scope:
  - src/volforecast/config.py
acceptance_criteria:
  - "GraphConfig has graph_norm_mode: str = 'per_fold' field"
  - "Valid values: 'per_fold', 'none'"
  - "Existing configs without this field default to 'per_fold'"
  - "YAML parser handles missing field gracefully"
memory_refs: []
constraints:
  - "TDD: write failing test first"
  - "Backward-compatible: old configs must still parse"
  - "No new dependencies"
context_summary: "GraphConfig is a dataclass in config.py that holds GNN-specific settings (method, params, window, refit_every, node_features, edge_features, min_history, input). Adding graph_norm_mode extends it with normalisation control."
depends_on: ["execute-0a", "execute-0b"]
```

### Step 2: Implement per-fold normalisation in native graph path (subagent)

```yaml
subtask_id: "execute-2"
goal: "Add per-fold z-score normalisation to _run_one_horizon_graphs in runner.py"
file_scope:
  - src/volforecast/pipeline/runner.py (lines 2747-3060, _run_pooled_graphs + _run_one_horizon_graphs)
  - src/volforecast/pipeline/graph_data.py (build_graph_dataset function)
  - src/volforecast/config.py (GraphConfig for graph_norm_mode access)
write_scope:
  - src/volforecast/pipeline/runner.py
acceptance_criteria:
  - "After graphs_all is built, if graph_norm_mode == 'per_fold': fit StandardScaler on train-fold node features (x arrays), apply to both train and test"
  - "Scaler fitted per-fold inside the fold loop (train dates only)"
  - "Original graph x arrays are NOT mutated in-place (work on copies)"
  - "When graph_norm_mode == 'none', no normalisation applied (old behaviour)"
  - "NaN-to-zero still happens BEFORE normalisation (preserve existing behaviour)"
memory_refs: []
constraints:
  - "TDD: write failing test first"
  - "Use sklearn.preprocessing.StandardScaler (already a project dependency)"
  - "Fit on train graph x only — no data leakage"
  - "Handle edge case: constant features (std=0) → leave as-is (StandardScaler handles this)"
  - "Do not change the multi-GPU parallel path signature — normalisation happens before dispatch or within each fold"
context_summary: "The native graph path builds all graphs upfront (graphs_all), then in the fold loop selects train/test graphs by date. Normalisation must fit on train-fold x matrices, then apply to both train and test x matrices. The fold loop is at runner.py:3000-3060. Each graph dict has 'x' key as (N, F) numpy array."
depends_on: ["execute-1"]
```

### Step 3: Implement per-fold normalisation in feature-stack GNN path (subagent)

```yaml
subtask_id: "execute-3"
goal: "Add per-fold z-score normalisation to _build_gnn_feature_stack_fn in runner.py"
file_scope:
  - src/volforecast/pipeline/runner.py (lines 2130-2260, _build_gnn_feature_stack_fn)
write_scope:
  - src/volforecast/pipeline/runner.py
acceptance_criteria:
  - "Feature-stack GNN fn applies StandardScaler fitted on train-fold node features"
  - "Scaler fit inside the returned callable (per-fold, train-only)"
  - "When graph_norm_mode == 'none', no normalisation (old behaviour)"
  - "NaN-to-zero happens before normalisation"
memory_refs: []
constraints:
  - "TDD: write failing test first"
  - "Same normalisation logic as Step 2 (consistency)"
  - "The returned callable receives (train_idx, test_idx, h) — normalisation must be derived from train_idx dates only"
context_summary: "The feature-stack GNN path builds graph snapshots per-date inside a callable fn(train_idx, test_idx, h). Node features are extracted from X_panel at runner.py:2203-2204 with only nan_to_num. The callable is invoked per-fold by the outer horizon runner. Normalisation should fit scaler on features from train_idx dates and apply to all."
depends_on: ["execute-1"]
```

### Step 4: Write unit tests (subagent)

```yaml
subtask_id: "execute-4"
goal: "Write unit tests for GNN per-fold normalisation"
file_scope:
  - src/tests/ (existing test patterns)
  - src/volforecast/pipeline/runner.py (normalisation code from steps 2-3)
  - src/volforecast/pipeline/graph_data.py
write_scope:
  - src/tests/test_gnn_normalisation.py
acceptance_criteria:
  - "test_graph_norm_train_mean_zero: after normalisation, train node features have mean≈0"
  - "test_graph_norm_train_std_one: after normalisation, train node features have std≈1"
  - "test_graph_norm_no_leakage: scaler stats computed from train only, test features use train stats"
  - "test_graph_norm_mode_none: when mode='none', features unchanged"
  - "test_graph_norm_handles_constant_features: std=0 features don't produce NaN"
  - "All tests pass via ./vol test -k gnn_norm"
memory_refs: []
constraints:
  - "Use synthetic data (random arrays) — no disk dependencies"
  - "Tests must be fast (<5s total)"
  - "Test the normalisation logic directly (extract into testable helper if needed)"
context_summary: "The normalisation logic fits StandardScaler on train-fold node features and applies to all graphs. Tests should verify correctness of the scaling, absence of data leakage, and correct behaviour with graph_norm_mode='none'."
depends_on: ["execute-2", "execute-3"]
```

### Step 5: Create trial-102 config YAML (inline)

```yaml
subtask_id: "execute-5"
goal: "Create trial_102_gnnhar_normalised_h1.yaml config for normalisation ablation"
file_scope:
  - workspace/configs/trial_083_gnnhar_vs_ghar_stid.yaml (base config)
write_scope:
  - workspace/configs/trial_102_gnnhar_normalised.yaml
acceptance_criteria:
  - "Config identical to trial-083 GNNHAR arm except: graph.graph_norm_mode='per_fold', name updated, output_dir updated"
  - "YAML valid and parseable"
  - "All three horizons (1, 5, 22) included for fair comparison"
memory_refs: []
constraints:
  - "Change ONLY normalisation mode and metadata — keep all other hyperparams identical for clean ablation"
context_summary: "Trial-083 GNNHAR produced QLIKE 0.1837/0.1606/0.1348 at h=1/5/22 without normalisation. This trial adds only per-fold z-score to measure the isolated improvement."
depends_on: ["execute-1"]
```

### Step 6: Run trial-102 (subagent)

```yaml
subtask_id: "execute-6"
goal: "Execute trial-102 and report QLIKE at all horizons"
file_scope:
  - workspace/configs/trial_102_gnnhar_normalised.yaml
  - src/volforecast/pipeline/runner.py (to debug if needed)
write_scope:
  - data/models/trial_102_gnnhar_normalised/ (output artifacts)
  - workspace/research/trials.yaml (append result)
acceptance_criteria:
  - "Trial completes without error"
  - "QLIKE at h=1, h=5, h=22 reported"
  - "Result appended to trials.yaml with verdict"
  - "DM test vs HAR baseline computed"
memory_refs:
  - memory/research/project-state.md
constraints:
  - "Use ./vol run --config to execute"
  - "Single seed (42) first"
  - "Gate: h=1 QLIKE < 0.170 → PASS"
context_summary: "Run the normalised GNNHAR and compare against trial-083 baselines (0.1837/0.1606/0.1348). If normalisation helps, expect significant improvement especially at h=1 and h=22 where the un-normalised GNN was worst."
depends_on: ["execute-4", "execute-5"]
```

### Step 7: Register trial-102 and update state (inline)

```yaml
subtask_id: "execute-7"
goal: "Register trial-102 in trials.yaml with full metadata"
file_scope:
  - workspace/research/trials.yaml (tail)
  - memory/research/project-state.md
write_scope:
  - workspace/research/trials.yaml
  - memory/research/project-state.md (only if gate passes)
acceptance_criteria:
  - "trial-102 registered with hypothesis, gate, config, status, key_insight"
  - "If h=1 QLIKE < 0.170: verdict=PASS, document improvement magnitude"
  - "If gate fails: verdict=FAIL, document that normalisation alone is insufficient"
memory_refs: []
constraints:
  - "Do not modify existing trial entries"
  - "project-state.md updated ONLY if normalisation produces a new QLIKE champion at any horizon"
context_summary: "Trial registry is append-only YAML. Gate evaluates whether per-fold z-score normalisation resolves the GNN underperformance."
depends_on: ["execute-6"]
```

---

## Dependency Graph

```
execute-0a (reset trial statuses)     execute-0b (clear fold cache)
    ↓                                      ↓
    └──────────────┬───────────────────────┘
                   ↓
             execute-1 (config schema)
                   ↓
  ┌─────────────────────────────────┐
  ↓              ↓                  ↓
execute-2      execute-3         execute-5
(native path)  (feature-stack)   (config YAML)
  ↓              ↓                  ↓
  └──────┬───────┘                  │
         ↓                          │
    execute-4 (tests)               │
         ↓                          │
         └──────────┬───────────────┘
                    ↓
              execute-6 (run trial)
                    ↓
              execute-7 (register)
```

Steps 0a and 0b are independent and can execute in parallel (no code dependencies).
Steps 2, 3, and 5 are independent after step 1 and can execute in parallel.

---

## Execution Mode Summary

| Step | Mode | Rationale |
|------|------|-----------|
| execute-0a | **inline** | Simple status field edits in YAML |
| execute-0b | **inline** | CLI commands (vol cache-clear) for each config |
| execute-1 | **subagent** | Modifies config dataclass, needs schema context |
| execute-2 | **subagent** | Modifies complex fold loop in runner.py (~100 lines of context) |
| execute-3 | **subagent** | Modifies feature-stack callable, touches same file as step 2 |
| execute-4 | **subagent** | Creates new test file, reads patterns from existing tests |
| execute-5 | **inline** | Single YAML file creation |
| execute-6 | **subagent** | Runs experiment, interprets output, may need debugging |
| execute-7 | **inline** | Append to YAML, conditional state update |

---

## Risk / Contingency

| Risk | Mitigation |
|------|-----------|
| Normalisation helps but GNNHAR still can't beat XGBoost champion | Expected — GNN value is in stacking, not standalone. Document finding. |
| Normalisation creates subtle data leakage if dates overlap | Per-fold fitting using train dates only; unit test explicitly checks no leakage |
| StandardScaler on constant features (all-zero after NaN fill) | StandardScaler handles std=0 gracefully (leaves unchanged); add test |
| Multi-GPU path needs separate normalisation | Normalise graph x arrays before dispatching to GPU workers (pre-fork) |
| trial-091/095 catastrophic results have different root cause (Glasso/regime adjacency bugs) | Plan only claims to fix normalisation; architectural bugs in Glasso/regime builders are separate issues |

---

## Expected Outcomes

**Optimistic (gate PASS):** GNNHAR h=1 drops from 0.1837 → <0.170, approaching XGBoost champion territory. Validates that the architecture was never the problem — just missing input conditioning.

**Realistic:** GNNHAR h=1 drops to ~0.175-0.180. Meaningful improvement but GNN still doesn't beat XGBoost standalone. Value remains in stacking (trial-089/090 path).

**Pessimistic:** Minimal improvement (<3 bps). Would indicate the GNN architecture itself is the bottleneck for this task, and normalisation alone isn't enough. Would close the GNN standalone research line.

---

## Future (conditional on trial-102 outcome)

If normalisation helps significantly:
- Re-run trial-091 (Glasso adjacency) with normalisation — the catastrophic 0.44 QLIKE may have been normalisation + adjacency bug compounding
- Re-run trial-095 (regime blend) with normalisation
- Consider trial-103: normalised GNN-learned (learned adjacency should benefit most from normalised features)

If normalisation doesn't help:
- Close standalone GNN research line
- Focus GNN value exclusively on stacking path (provide embeddings to XGBoost)
