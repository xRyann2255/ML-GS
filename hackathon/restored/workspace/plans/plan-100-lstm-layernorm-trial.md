# Plan: LSTM In-Network LayerNorm + Stacking Trial

**Date:** 2026-07-28
**Status:** EXECUTED — GATE FAIL (QLIKE 0.2174, gate was < 0.195)
**Trial ID:** trial-101 (trial-100 was already taken in registry)

---

## Correction: Pipeline-Level Normalisation Already Exists

Investigation revealed that **per-fold z-score normalisation IS applied** to LSTM sequences at the pipeline runner level:

- `_run_lstm_fold` (runner.py:483–524) calls `fit_seq_normaliser` on train-only dates, then `apply_normaliser` on train+test tensors before passing to `LSTMVolModel.fit()`.
- Two modes supported: `pooled` (global per-feature stats) and `per_symbol` (per-symbol stats).
- Trial-073 (best LSTM, QLIKE 0.1998) ran with `norm_mode: per_symbol`.
- The `fit_seq_normaliser` + `apply_normaliser` functions live in `src/volforecast/data/sequence_cache.py:644–740`.

**What does NOT exist:** In-network normalisation (LayerNorm/BatchNorm) inside the LSTM architecture module itself.

---

## Scope

### What's missing and what this plan addresses:

1. **In-network LayerNorm** — add optional `nn.LayerNorm` on LSTM input and/or hidden output within the `_VolLSTM` module. Benefits:
   - Stabilises hidden state magnitudes across long sequences (78 5-min bars)
   - Improves gradient flow through the recurrent stack
   - Provides per-sample adaptive normalisation that pipeline z-score cannot (e.g. handles within-sequence non-stationarity)
   - Standard practice in modern sequence models (Ba et al. 2016)

2. **New trial (trial-100)** — test LayerNorm addition against the current best LSTM (trial-073, QLIKE 0.1998) using same config except architecture change.

3. **Secondary trial (trial-101)** — LSTM stacking with XGBoost h=1 champion. If LayerNorm helps, use it in the stacking architecture.

---

## Acceptance Criteria

- [ ] `_VolLSTM` gains an optional `layer_norm: bool` parameter (default `False` for backward compat)
- [ ] When `layer_norm=True`, `nn.LayerNorm(input_dim)` is applied to input, and `nn.LayerNorm(hidden_dim * directions)` to LSTM output before pooling
- [ ] Existing tests pass unchanged (no regressions)
- [ ] New unit test verifies forward pass shapes with `layer_norm=True`
- [ ] New unit test verifies that normalised output has approximately zero mean and unit variance
- [ ] Trial-100 config YAML created
- [ ] Trial-100 executed: single-seed QLIKE reported at h=1
- [ ] Gate: if single-seed QLIKE < 0.195 (> 5 bps improvement over 0.1998), promote to 5-seed

---

## Implementation Plan

### Step 1: Add LayerNorm to `_VolLSTM` architecture (subagent)

```yaml
subtask_id: "execute-1"
goal: "Add optional LayerNorm to _VolLSTM input and LSTM output"
file_scope:
  - src/volforecast/models/lstm.py (lines 100-260, _VolLSTM class)
write_scope:
  - src/volforecast/models/lstm.py
acceptance_criteria:
  - "_VolLSTM.__init__ accepts layer_norm: bool = False"
  - "When layer_norm=True, nn.LayerNorm(lstm_input_dim) applied to x before pack"
  - "When layer_norm=True, nn.LayerNorm(out_dim) applied to LSTM output before pooling"
  - "Existing forward pass unchanged when layer_norm=False (default)"
  - "No new external dependencies"
memory_refs: []
constraints:
  - "TDD: write failing test first"
  - "Do not modify public API of LSTMVolModel"
  - "Use ./vol test to run tests"
  - "layer_norm=False must produce bitwise-identical output to current code"
context_summary: "_VolLSTM is a nn.Module (lines 130-260) with _encode → _pool → forward. The LSTM input is (B, T, F) after optional symbol embedding concat. Output is packed → padded → pooled via attention or last_hidden → head MLP/linear → scalar."
depends_on: []
```

### Step 2: Thread `layer_norm` parameter through `LSTMVolModel` (subagent)

```yaml
subtask_id: "execute-2"
goal: "Thread layer_norm config param from LSTMVolModel.__init__ through to _VolLSTM instantiation"
file_scope:
  - src/volforecast/models/lstm.py (lines 440-560, LSTMVolModel.__init__)
  - src/volforecast/models/lstm.py (lines 950-1050, model instantiation in fit)
write_scope:
  - src/volforecast/models/lstm.py
acceptance_criteria:
  - "LSTMVolModel.__init__ accepts layer_norm: bool = False"
  - "self.layer_norm stored and passed to _VolLSTM constructor"
  - "get_params() includes layer_norm"
  - "Existing configs without layer_norm still work (default False)"
memory_refs: []
constraints:
  - "TDD: write failing test first"
  - "Backward-compatible: omitting layer_norm from config must not break"
context_summary: "LSTMVolModel wraps _VolLSTM. It accepts hyperparams in __init__, stores them, and instantiates _VolLSTM during fit(). The _module attribute holds the nn.Module. Config YAML params map 1:1 to __init__ kwargs."
depends_on: ["execute-1"]
```

### Step 3: Write unit tests (subagent)

```yaml
subtask_id: "execute-3"
goal: "Write unit tests for LayerNorm LSTM — shape correctness and normalisation effect"
file_scope:
  - src/tests/test_lstm_val_purge.py (for test patterns)
  - src/volforecast/models/lstm.py (modified code from steps 1-2)
write_scope:
  - src/tests/test_lstm_layernorm.py
acceptance_criteria:
  - "test_forward_shape_with_layernorm: forward pass produces correct (B,) output"
  - "test_layernorm_reduces_output_scale: verify output hidden states have lower variance than without LayerNorm on synthetic extreme-scale input"
  - "test_backward_compat_no_layernorm: model with layer_norm=False matches old behaviour"
  - "All tests pass via ./vol test -k layernorm"
memory_refs: []
constraints:
  - "Use synthetic data (random tensors) — no disk dependencies"
  - "Tests must be fast (<5s total)"
context_summary: "Existing LSTM tests use synthetic SequenceTensor fixtures with small dims. Pattern: construct SequenceTensor with random data, instantiate LSTMVolModel, call fit/predict, assert shapes and value ranges."
depends_on: ["execute-2"]
```

### Step 4: Create trial-100 config YAML (inline)

```yaml
subtask_id: "execute-4"
goal: "Create trial_100_lstm_layernorm_h1.yaml config for LayerNorm ablation"
file_scope:
  - workspace/configs/trial_073_lstm_5min_train2000_h1.yaml (base config to copy)
write_scope:
  - workspace/configs/trial_100_lstm_layernorm_h1.yaml
acceptance_criteria:
  - "Config identical to trial-073 except: model.params.layer_norm=true, name=trial_100_lstm_layernorm_h1, output_dir updated"
  - "YAML valid and parseable by ExperimentConfig"
memory_refs: []
constraints:
  - "Change ONLY layer_norm and metadata fields — keep all other hyperparams identical for clean ablation"
context_summary: "Trial-073 is the best standalone LSTM (QLIKE 0.1998 at h=1). It uses hidden=128, bidirectional, 5-min enriched sequences (78×12), train_size=2000, per_symbol norm. This trial adds ONLY layer_norm=True to measure the isolated effect."
depends_on: ["execute-2"]
```

### Step 5: Run trial-100 (subagent)

```yaml
subtask_id: "execute-5"
goal: "Execute trial-100 single-seed and report QLIKE at h=1"
file_scope:
  - workspace/configs/trial_100_lstm_layernorm_h1.yaml
  - src/volforecast/pipeline/runner.py (to debug if needed)
write_scope:
  - data/models/trial_100_lstm_layernorm/ (output artifacts)
  - workspace/research/trials.yaml (append result)
acceptance_criteria:
  - "Trial completes without error"
  - "QLIKE h=1 reported with DM test vs HAR baseline"
  - "Result appended to trials.yaml with verdict"
memory_refs:
  - memory/research/project-state.md
constraints:
  - "Use ./vol exec to run"
  - "Single seed (42) only — multi-seed if gate passes"
  - "Gate: QLIKE < 0.195 → PASS (promote to 5-seed)"
context_summary: "The pipeline runner handles normalisation, CV, and evaluation. Run via the standard tournament CLI. Compare against trial-073 (0.1998) and HAR (0.1601)."
depends_on: ["execute-3", "execute-4"]
```

### Step 6: Register trial-100 in registry and update state (inline)

```yaml
subtask_id: "execute-6"
goal: "Add trial-100 entry to trials.yaml before execution, update project-state if champion"
file_scope:
  - workspace/research/trials.yaml (tail)
  - memory/research/project-state.md
write_scope:
  - workspace/research/trials.yaml
  - memory/research/project-state.md (only if new champion)
acceptance_criteria:
  - "trial-100 registered with hypothesis, gate, config, status"
  - "If QLIKE < 0.195: status=completed, verdict=PASS, promote note added"
  - "If QLIKE >= 0.195: status=completed, verdict=FAIL, key_insight documented"
memory_refs: []
constraints:
  - "Do not modify existing trial entries"
  - "project-state.md updated ONLY if new champion crowned"
context_summary: "Trial registry is append-only YAML. Each entry needs id, date, config, hypothesis, gate, horizons, status. project-state.md QLIKE scorecard updated only on validated new champions."
depends_on: ["execute-5"]
```

---

## Dependency Graph

```
execute-1 (LayerNorm arch)
    ↓
execute-2 (thread param)
    ↓
  ┌─────────────┐
  ↓             ↓
execute-3     execute-4
(tests)       (config YAML)
  ↓             ↓
  └──────┬──────┘
         ↓
    execute-5 (run trial)
         ↓
    execute-6 (register result)
```

Steps 3 and 4 are independent and can execute in parallel after step 2.

---

## Execution Mode Summary

| Step | Mode | Rationale |
|------|------|-----------|
| execute-1 | **subagent** | Modifies complex nn.Module code, needs full context of _VolLSTM |
| execute-2 | **subagent** | Touches LSTMVolModel __init__ + fit, needs step 1 context |
| execute-3 | **subagent** | Creates new test file, reads patterns from existing tests |
| execute-4 | **inline** | Single file copy+edit, trivial |
| execute-5 | **subagent** | Runs experiment, interprets output, may debug |
| execute-6 | **inline** | Append to YAML, conditional state update |

---

## Risk / Contingency

| Risk | Mitigation |
|------|-----------|
| LayerNorm hurts QLIKE (regularisation too aggressive for small model) | Trial gate catches it; fail-fast at single-seed |
| LayerNorm + pack_padded_sequence incompatibility | Apply LN before packing (on padded input); re-zero pads after |
| Minimal improvement (<3 bps) | Document as finding; proceed to trial-101 (stacking) which is higher-value |
| LSTM training unstable with LN | Lower learning rate in follow-up if needed |

---

## Future (trial-101, contingent on trial-100 outcome)

If trial-100 shows any improvement, trial-101 will stack the LayerNorm LSTM with XGBoost h=1 champion:
- LSTM produces embedding/prediction features
- XGBoost consumes as additional columns alongside tabular features
- Expected synergy: LSTM captures intraday temporal patterns, XGBoost handles cross-sectional and daily signals

If trial-100 fails, trial-101 proceeds with the existing LSTM (trial-073 architecture) for stacking.
