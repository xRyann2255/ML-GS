# Implementation Plan: Fix Bug 3 — IV-Context Path UnboundLocalError

**Source:** `workspace/docs/lstm-performance-deep-dive.md` Section 3, Bug #3  
**Status:** Ready to execute  
**Blocking:** Trial-075 (IV context vector into LSTM head) — has never validly run  

---

## Problem Statement

`runner.py:2520` writes `model_params["context_dim"] = len(context_features)` **before** `model_params` is bound at line 2535 (`model_params = dict(self.config.model_params_for_horizon(h))`). This causes an `UnboundLocalError` whenever `sequences.context_features` is non-empty.

Additionally, the parallel fold path (`_execute_fold` at line 178) never receives the `context_arr`, never slices it into train/test, and never passes `context` to `model.fit()` or `model.predict()`. The LSTM's `fit` method raises `ValueError("fit: model has context_dim>0 but no context array provided")` when `context_dim > 0` without context.

The sequential path (line ~3021-3070) correctly threads context through fit/predict. The parallel path is the gap.

---

## Root Cause (code walkthrough)

```
Line 2500-2520:  context_arr built, model_params["context_dim"] assigned
Line 2525-2533:  PanelExpandingWindowCV built (uses cv_cfg)
Line 2535:       model_params = dict(self.config.model_params_for_horizon(h))  ← REBINDS, overwriting the context_dim assignment
```

The `context_dim` assignment at 2520 writes to a **not-yet-existing** local `model_params`. Python raises `UnboundLocalError` because the function body has a later assignment to `model_params` (line 2535), making it a local variable for the entire function scope.

Even if the ordering were fixed, the parallel path at line 2791 (`pool.submit(_execute_fold, ...)`) passes no `context_arr`, and `_execute_fold`'s signature (line 178) has no `context` parameter.

---

## Acceptance Criteria

1. `UnboundLocalError` no longer raised when `sequences.context_features` is set
2. `model_params["context_dim"]` is correctly set AFTER `model_params` is bound
3. `_execute_fold` accepts a `context_arr` parameter, slices train/test, passes to `fit()` and `predict()`
4. Parallel fold path (`pool.submit`) passes `context_arr` to `_execute_fold`
5. Integration test: a 2-feature context vector runs through the full LSTM pipeline (both sequential and parallel paths) without error
6. Existing LSTM tests (`TestContextVector`, unit suite) still pass
7. No trial-075 number is trusted until rerun (document in plan output)

---

## Execution Plan

### Dependency Graph

```
Step 1 (test) → Step 2 (runner fix) → Step 3 (verify) → Step 4 (doc)
```

All steps are sequential (each depends on the prior).

---

### Step 1: Write failing integration test [subagent]

```yaml
subtask_id: "execute-1"
goal: "Write an integration test that exercises the LSTM context path through the runner's parallel and sequential fold execution, asserting no UnboundLocalError and that predictions are finite."
file_scope:
  - src/tests/unit/test_lstm.py  # pattern for synthetic data helpers
  - src/tests/integration/test_pipeline.py  # pattern for runner integration tests
  - src/volforecast/pipeline/runner.py  # lines 178-220 (_execute_fold sig), 2500-2560 (context block)
  - src/volforecast/models/lstm.py  # lines 821-910 (fit signature, context validation)
  - src/volforecast/config.py  # SequenceConfig.context_features field
  - src/volforecast/data/sequence_cache.py  # SequenceTensor dataclass
write_scope:
  - src/tests/integration/test_lstm_context_pipeline.py
acceptance_criteria:
  - "Test file exists at src/tests/integration/test_lstm_context_pipeline.py"
  - "Test uses a 2-feature context vector (e.g. ['feat_a', 'feat_b'])"
  - "Test exercises the runner sequence path end-to-end with context_features set"
  - "Test FAILS on the current codebase (UnboundLocalError or ValueError)"
  - "./vol test -x -q -k test_lstm_context passes after fix is applied (Step 2)"
memory_refs: []
constraints:
  - "TDD: test must fail on current code"
  - "Use synthetic data — no real parquets or GPU required"
  - "Test must work with device='cpu'"
  - "Do NOT modify any source files — only create the test file"
  - "All file writes to workspace (src/tests/integration/)"
context_summary: |
  Bug 3 in the LSTM deep-dive audit: runner.py assigns model_params["context_dim"]
  at line 2520 before model_params is bound at line 2535, causing UnboundLocalError
  when sequences.context_features is non-empty. The parallel fold path (_execute_fold)
  also never receives or threads context. The LSTM model's fit() raises ValueError
  when context_dim>0 but no context array is provided. The sequential path (line 3021+)
  correctly threads context. The test should trigger the UnboundLocalError by configuring
  an ExperimentConfig with sequences.context_features=['feat_a','feat_b'] and running
  the sequence tournament or _run_sequence_horizon method.
depends_on: []
```

---

### Step 2: Fix the runner — reorder binding + thread context through parallel path [subagent]

```yaml
subtask_id: "execute-2"
goal: "Fix the UnboundLocalError by moving model_params['context_dim'] assignment after model_params binding, and thread context_arr through _execute_fold for the parallel fold path (signature, submit call, slicing, fit_kwargs, predict calls)."
file_scope:
  - src/volforecast/pipeline/runner.py  # full file — need lines 178-420 and 2490-2840
  - src/volforecast/models/lstm.py  # lines 821-910 (fit/predict context interface)
write_scope:
  - src/volforecast/pipeline/runner.py
acceptance_criteria:
  - "model_params['context_dim'] assignment occurs AFTER `model_params = dict(...)` at line 2535"
  - "_execute_fold signature includes `context_arr: np.ndarray | None = None` parameter"
  - "_execute_fold slices context_arr into context_train and context_test using train_idx_arr/test_idx_arr"
  - "_execute_fold passes context_train to model.fit() via fit_kwargs['context']"
  - "_execute_fold passes context_test/context_train to model.predict() calls"
  - "pool.submit(...) call passes context_arr=context_arr to _execute_fold"
  - "Sequential path remains unchanged (already works)"
  - "When context_arr is None, behavior is identical to before (no regression)"
memory_refs: []
constraints:
  - "Minimal diff — only fix the bug, do not refactor surrounding code"
  - "Do not change the sequential path (lines 3010-3070) — it already works"
  - "context_arr is the full array; _execute_fold slices by train_idx_arr/test_idx_arr"
  - "Match the pattern of the sequential path for fit/predict context threading"
  - "Do NOT change public APIs or config schema"
context_summary: |
  Three fixes needed in runner.py:
  1. REORDER: Move `model_params["context_dim"] = len(context_features)` to AFTER
     `model_params = dict(self.config.model_params_for_horizon(h))` (currently at ~2535).
     The assignment should be appended after the model_params block (after n_symbols setdefault).
  2. SIGNATURE: Add `context_arr: np.ndarray | None = None` to _execute_fold (line 178).
  3. THREAD: Inside _execute_fold, slice context_arr[train_idx_arr] and context_arr[test_idx_arr],
     add to fit_kwargs and predict calls. Pattern to follow: the sequential path at lines 3021-3070
     does `context_train = context_arr[train_idx_arr] if context_arr is not None else None` then
     passes `**({"context": context_train} if context_train is not None else {})`.
  4. SUBMIT: Add `context_arr=context_arr` to the pool.submit() call at line 2791.
depends_on: ["execute-1"]
```

---

### Step 3: Run tests and verify [inline]

Orchestrator executes directly:
- Run `./vol test -x -q -k test_lstm_context` — the new integration test must pass
- Run `./vol test -x -q -k TestContextVector` — existing unit tests must pass
- Run `./vol test -x -q -k test_lstm` — full LSTM test suite must pass
- Run `./vol test -x -q -k test_phase4_cleanup` — _execute_fold tests must pass

```yaml
subtask_id: "execute-3"
goal: "Verify all tests pass after the fix"
depends_on: ["execute-2"]
acceptance_criteria:
  - "test_lstm_context_pipeline passes (new integration test)"
  - "TestContextVector passes (existing unit tests)"
  - "No regressions in LSTM or pipeline test suites"
```

---

### Step 4: Document trust boundary for trial-075 [inline]

Orchestrator executes directly:
- Add a note to trial-075 in the experiment record marking all prior numbers as INVALID (context was never actually provided to the model)
- No re-run needed as part of this fix — just mark the existing number as untrusted

```yaml
subtask_id: "execute-4"
goal: "Mark trial-075 results as invalid pending rerun with the fixed context path"
depends_on: ["execute-3"]
acceptance_criteria:
  - "Trial-075 is marked invalid/untrusted in the experiment record or in a workspace doc"
```

---

## Detailed Code Changes (reference for subagents)

### Change 1: Reorder `model_params["context_dim"]` (runner.py ~2520 → after 2540)

**Before** (simplified):
```python
# Line 2520: context_arr built
model_params["context_dim"] = len(context_features)  # ← UnboundLocalError

# Line 2535:
model_params = dict(self.config.model_params_for_horizon(h))
model_params.setdefault("input_dim", tensor.shape[2])
```

**After:**
```python
# Line 2520: context_arr built (no model_params assignment here)

# Line 2535:
model_params = dict(self.config.model_params_for_horizon(h))
model_params.setdefault("input_dim", tensor.shape[2])
if model_params.get("symbol_embed_dim", 0) > 0:
    model_params.setdefault("n_symbols", n_symbols)
# Inject context_dim from the materialized context array
if context_arr is not None:
    model_params["context_dim"] = context_arr.shape[1]
```

### Change 2: `_execute_fold` signature (runner.py line 178)

Add after `norm_mode`:
```python
    context_arr: np.ndarray | None = None,
```

### Change 3: `_execute_fold` body — slice and thread context (runner.py ~line 359)

After fit_kwargs is initialized, before `model.fit(...)`:
```python
    # Slice context for this fold
    context_train = context_arr[train_idx_arr] if context_arr is not None else None
    context_test = context_arr[test_idx_arr] if context_arr is not None else None
    
    if context_train is not None:
        fit_kwargs["context"] = context_train
```

For predict calls, add `**({"context": context_test} if context_test is not None else {})` to each `model.predict()` invocation, mirroring the sequential path pattern.

### Change 4: `pool.submit()` call (runner.py ~line 2791)

Add to the submit kwargs:
```python
    context_arr=context_arr,
```

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Parallel path shares context_arr across processes (copy-on-write safety) | numpy arrays in spawn-context are serialized per-worker; no shared mutation risk |
| Large context_arr serialization cost with ProcessPoolExecutor | Context is O(n_samples × n_features), typically <1MB; negligible vs tensor serialization |
| Regression in non-context LSTM runs | context_arr defaults to None; all conditional paths only activate when non-None |
| Cache fingerprint gap (Bug 7) | Out of scope for this fix; noted in deep-dive as separate Tier 0 item |

---

## What This Does NOT Fix

- Bug 1 (dead HPO search) — separate fix
- Bug 2 (early-stopping val leakage) — separate fix  
- Trial-075 rerun — separate experiment, requires this fix first
- Trial-077 (extended IV context vector experiment) — requires this fix + data availability

---

## Execution Mode Summary

| Step | Mode | Rationale |
|------|------|-----------|
| 1 (test) | subagent | Reads 6 files, creates new test module, needs pattern matching from existing tests |
| 2 (fix) | subagent | Modifies runner.py in 4 locations, needs full understanding of both execution paths |
| 3 (verify) | inline | Simple command execution, orchestrator validates |
| 4 (doc) | inline | Single-file annotation, trivial |
