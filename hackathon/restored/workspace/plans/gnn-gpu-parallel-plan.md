# Plan: GNN Multi-GPU Parallel Training + Optimizations

**Date:** 2026-06-30  
**Status:** READY FOR EXECUTION — subagent-driven implementation plan below  
**Scope:** GNN feature-stacking pipeline — GPU parallelism, progress reporting, training optimizations  

---

## Problem Statement

The GNN feature stacker currently has three deficiencies:

1. **No GPU parallelism.** `_gnn_feature_stack_fold` trains sequentially inside `_run_horizon`'s fold loop. With 8 GPUs available and ~10 CV folds, each GNN trains on a single GPU one at a time.

2. **No progress reporting.** Unlike LSTM (epoch progress → Rich bar via cross-process Queue) and XGBoost (boosting round progress), GNN training emits no events. The `on_progress` callback exists on `GNNVolModel.fit()` but is never wired to the pipeline's progress infrastructure.

3. **Avoidable redundant compute.** Graph snapshots (adjacency matrices, node features) are rebuilt from scratch for every fold even though most dates overlap between folds. Adjacency computation (rolling correlation → threshold) is the most expensive preprocessing step.

---

## Architecture Context

### Current execution flow (feature-stacking path)

```
__main__.py → tournament.run_models_pooled()
  → _parallel.run_models_pooled()           [ProcessPoolExecutor: 1 process per model]
    → Pipeline.run_pooled()                  [per model process]
      → _build_and_run_horizon(h)            [per horizon]
        → _make_feature_stack_fn()           [detects GNN → _make_gnn_feature_stack_fn()]
          → _gnn_feature_stack_fold()        [called per CV fold, SEQUENTIAL]
            → GNNVolModel.fit(train_graphs)  [SINGLE GPU, NO progress]
            → GNNVolModel.extract_features() 
          ← returns DataFrame of GNN features to augment X_train/X_test
        → XGBoost.fit(X + gnn_features)     [base model, can run GPU parallel]
```

### Why the current design blocks parallelism

- `_run_horizon` calls `feature_stack_fn(train_idx, test_idx, h)` inside the **sequential fold loop** (line ~504 of runner.py).
- The GPU-parallel path (`_run_horizon_gpu_parallel`) is gated by `feature_stack_fn is None` — it refuses to parallelize when feature stacking is active.
- Result: GNN folds run one at a time on whatever GPU `auto` resolves to (typically `cuda:0`).

### How LSTM/XGBoost achieve parallelism (reference pattern)

- LSTM: `_run_one_horizon_sequences` → `ProcessPoolExecutor(max_workers=effective_gpus)` with `device_id = (fold_num - 1) % effective_gpus`. Cross-process `Queue` → consumer thread → `on_train_progress` callback → Rich bar.
- XGBoost: `_run_horizon_gpu_parallel` → same ProcessPool pattern, per-fold GPU pinning.

---

## Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | GNN folds train across all available GPUs (round-robin assignment) | `nvidia-smi` shows utilization on multiple GPUs during GNN fold execution |
| AC-2 | Rich progress bar shows GNN epoch progress (like LSTM) | Visual inspection of CLI output during run |
| AC-3 | `on_fold_complete` fires per GNN fold (fold bar advances) | Visual inspection of fold progress bar |
| AC-4 | Graph snapshots are built once and shared across folds (not rebuilt per fold) | Logging shows single graph-build phase; timing comparison shows speedup |
| AC-5 | No regression in GNN prediction quality | QLIKE on smoke test within ±1% of sequential baseline |
| AC-6 | Adjacency matrices are cached per date (not recomputed) | Cache hit logging in adjacency builder |
| AC-7 | All existing LSTM/XGBoost parallel paths remain unaffected | Existing trial configs still pass |

---

## Design

### Step 1: Pre-compute all graph snapshots once (before fold loop)

**Problem:** `_build_graphs_for_rows` is called twice per fold (train + test). Across 10 folds, the same date's graph is rebuilt ~18 times (it appears in ~9 train sets and ~1 test set).

**Solution:** Build all graph snapshots once for all dates in the panel, store in a dict keyed by date. Per-fold callbacks just select subsets from the pre-built cache.

**Changes:**
- Restructure `_make_gnn_feature_stack_fn` to build `all_graphs: dict[Timestamp, dict]` upfront
- `_gnn_feature_stack_fold` selects graphs by date from pre-built dict
- Adjacency computation happens once per date (not per fold)

**Impact:** ~10× fewer calls to `build_adjacency`. Graph building goes from O(n_folds × n_dates) to O(n_dates).

### Step 2: Parallelize GNN fold training across GPUs

**Problem:** Feature-stacking folds run sequentially inside `_run_horizon`'s fold loop.

**Solution:** Add `_run_gnn_feature_stack_parallel` — a new method that:
1. Pre-computes all fold splits
2. Dispatches each GNN fold to a different GPU via `ProcessPoolExecutor(max_workers=effective_gpus)`
3. Each worker receives: (a) shared graph snapshots (pre-built), (b) train/test date indices, (c) `device_id` for GPU pinning
4. Workers train GNN, extract features, and return the result DataFrame
5. Collect all fold results, then pass pre-computed GNN features to the base model (XGBoost)

**Key design decision:** The GNN feature columns need to be injected into X_train/X_test **per fold** (different GNN model per fold to prevent leakage). The approach is:
- Phase 1: Train all GNN folds in parallel → collect `{fold_num: DataFrame}` with per-fold GNN features
- Phase 2: Run XGBoost fold loop with cached GNN features (no live GNN training needed)

This two-phase approach decouples GNN and XGBoost parallelism.

**Changes:**
- New method `Pipeline._run_gnn_stacked_horizon_parallel(X, y, cv, h, n_gpus, ...)`
- New top-level worker function `_execute_gnn_fold(fold_num, graphs, train_dates, test_dates, model_params, device_id, progress_queue)`
- Modify `_make_gnn_feature_stack_fn` to detect `n_gpus > 1` and return a pre-populated fold cache instead of a live callback
- Wire into `_run_horizon` dispatch logic

**GPU assignment:**
```python
device_id = (fold_num - 1) % effective_gpus  # same pattern as LSTM
model_params["device"] = f"cuda:{device_id}"
```

### Step 3: Wire progress reporting through cross-process Queue

**Problem:** `GNNVolModel.fit()` has an `on_progress` callback but it's never connected.

**Solution:** Follow the exact LSTM pattern:
1. Create `multiprocessing.Manager().Queue()` for epoch progress events
2. Each GPU worker passes epoch events to the queue via `on_progress` lambda
3. Consumer thread in main process reads events and forwards to `on_train_progress` callback
4. `on_fold_complete` fires when each worker returns

**Event format** (matches existing `ProgressEvent` schema):
```python
{"type": "epoch", "fold": fold_num, "epoch": current, "max_epochs": total}
```

**Changes:**
- In `_run_gnn_stacked_horizon_parallel`: set up Manager Queue + consumer thread (copy from LSTM path)
- In `_execute_gnn_fold`: wire `on_progress` to push to the queue
- The Rich progress bar already handles epoch events — no CLI changes needed

### Step 4: GNN training-loop optimizations (no quality sacrifice)

These optimizations speed up each individual GNN training run:

#### 4a: Pre-convert PyG Data objects once

**Current:** `_to_pyg()` converts numpy → torch tensors every time. In parallel mode, this happens in workers.

**Fix:** Convert to `torch_geometric.data.Data` objects during graph pre-computation (Step 1), store them. Workers receive ready-to-batch Data objects.

#### 4b: Use PyG DataLoader for mini-batching

**Current:** Manual loop with `Batch.from_data_list(batch_list).to(device)` per batch per epoch.

**Fix:** Use `torch_geometric.loader.DataLoader` with `pin_memory=True` and `num_workers=2`. This:
- Prefetches next batch while GPU processes current batch
- Handles batching and collation efficiently
- Pin-memory enables async CPU→GPU transfer

```python
from torch_geometric.loader import DataLoader
train_loader = DataLoader(train_data, batch_size=self.batch_size, shuffle=True, 
                          pin_memory=True, num_workers=2)
```

#### 4c: Learning rate scheduler (OneCycleLR)

**Current:** Fixed learning rate throughout training.

**Fix:** Add `torch.optim.lr_scheduler.OneCycleLR` — reaches target loss faster (fewer epochs before early stopping triggers), no quality sacrifice. This is a standard optimization that typically reduces epoch count by 20-40%.

#### 4d: Gradient accumulation for effective larger batch size

**Current:** Each mini-batch of 32 graphs updates weights independently.

**Fix:** Accumulate gradients over 2-4 mini-batches before stepping, giving an effective batch size of 64-128. Improves gradient stability without requiring more GPU memory. Configurable via `grad_accumulation_steps` param.

#### 4e: `torch.compile()` for the GATModule (PyTorch 2.x)

**Current:** Eager mode execution.

**Fix:** Wrap the module with `torch.compile(mode="reduce-overhead")` on CUDA. This fuses operations and reduces kernel launch overhead. Especially effective for small models with many small ops (attention, ELU, dropout). Gated behind a `compile: bool` config param defaulting to `True` on CUDA.

### Step 5: Adjacency caching

**Problem:** `build_adjacency(panel_returns, date, window=60, threshold=0.3)` computes a rolling 60-day correlation matrix for each date. With 21 symbols, this is a 21×21 correlation per date — not expensive individually but wasteful when repeated.

**Solution:** Cache adjacency results in memory keyed by `(date, window, threshold)`. Since Step 1 pre-computes all graphs, this naturally happens. But also add an LRU cache to `build_adjacency` itself for safety.

**Changes:**
- Add `@functools.lru_cache` or manual dict cache to `build_adjacency` (requires making inputs hashable)
- Alternative: compute all adjacency matrices vectorized in one pass using `pandas.DataFrame.rolling().corr()`

---

## Execution Plan

### Dependency Graph

```
Step 1 (graph pre-compute) ──┐
                              ├──→ Step 2 (fold parallelism) ──→ Step 3 (progress wiring)
Step 5 (adjacency caching) ──┘                                         │
                                                                       ↓
Step 4a-4e (training optimizations) ← independent, can run in parallel
```

Summary: Steps 1+5 parallel → Step 2 (needs 1,5) → Step 3 (needs 2) → Step 4 (independent)

### Step-level execution tags

#### execute-1: Pre-compute all graph snapshots
- **Mode:** `subagent`
- **Context packet:**
  ```yaml
  subtask_id: "execute-1"
  goal: "Restructure _make_gnn_feature_stack_fn to pre-build all graph snapshots once (keyed by date) before the fold loop, and have _gnn_feature_stack_fold select from pre-built cache"
  file_scope:
    - src/volforecast/pipeline/runner.py  # lines 1620-1830 (_make_gnn_feature_stack_fn)
    - src/volforecast/models/gnn_adjacency.py  # build_adjacency, panel_returns_from_ohlcv
  write_scope:
    - src/volforecast/pipeline/runner.py
  acceptance_criteria:
    - "_build_graphs_for_rows is replaced by a single pre-computation pass"
    - "Each date's graph (node features, edge_index, edge_attr) is built exactly once"
    - "_gnn_feature_stack_fold selects train/test graphs from pre-built dict by date"
    - "Graph dict includes _row_indices for result alignment"
    - "Pre-built graphs stored as PyG Data objects (not raw dicts) for zero-copy batching"
  constraints:
    - "No changes to _run_horizon or XGBoost paths"
    - "Maintain identical GNN features output for sequential execution"
  depends_on: []
  ```

#### execute-2: Parallel GNN fold dispatch across GPUs
- **Mode:** `subagent`
- **Context packet:**
  ```yaml
  subtask_id: "execute-2"
  goal: "Add _run_gnn_stacked_horizon_parallel method and _execute_gnn_fold top-level worker to dispatch GNN feature-stack folds across multiple GPUs via ProcessPoolExecutor"
  file_scope:
    - src/volforecast/pipeline/runner.py  # _run_horizon, _run_horizon_gpu_parallel (reference pattern), _make_gnn_feature_stack_fn
    - src/volforecast/models/gnn.py  # GNNVolModel.fit(), device handling
    - src/volforecast/evaluation/_parallel.py  # ProgressEvent schema
  write_scope:
    - src/volforecast/pipeline/runner.py
    - src/volforecast/models/gnn.py  # ensure device param is respected in fit()
  acceptance_criteria:
    - "New _execute_gnn_fold top-level function (picklable for ProcessPoolExecutor)"
    - "New _run_gnn_stacked_horizon_parallel dispatches folds with device_id = (fold-1) % n_gpus"
    - "_make_gnn_feature_stack_fn detects n_gpus > 1 and pre-runs all GNN folds in parallel"
    - "Returns a fold-keyed cache: {fold_num: DataFrame} so _run_horizon consumes pre-computed features"
    - "Falls back to sequential if n_gpus <= 1"
    - "Uses spawn context for CUDA safety"
  constraints:
    - "Must not break sequential (single-GPU) path"
    - "Graph data must be picklable for cross-process transfer"
    - "Must pin each worker to specific GPU via model_params['device']"
  depends_on: ["execute-1"]
  ```

#### execute-3: Progress bar wiring
- **Mode:** `subagent`
- **Context packet:**
  ```yaml
  subtask_id: "execute-3"
  goal: "Wire GNN fold training to Rich progress bar via cross-process Queue, matching LSTM epoch progress pattern"
  file_scope:
    - src/volforecast/pipeline/runner.py  # LSTM progress queue pattern (~lines 2340-2400)
    - src/volforecast/evaluation/_parallel.py  # ProgressEvent, _consume_progress_queue
    - src/volforecast/cli/progress.py  # StageProgress / ExperimentProgress
    - src/volforecast/__main__.py  # _on_train_progress, _on_fold_complete wiring
  write_scope:
    - src/volforecast/pipeline/runner.py  # Add Queue setup in GNN parallel path
  acceptance_criteria:
    - "Manager().Queue() created before GNN fold dispatch"
    - "Consumer thread reads epoch events and forwards to on_train_progress"
    - "on_fold_complete fires when each GNN fold worker returns"
    - "Queue + consumer thread cleaned up after all folds complete"
    - "Rich progress bar shows 'GNN epoch X/Y' during training"
  constraints:
    - "Event format matches existing ProgressEvent schema"
    - "No changes to cli/progress.py or __main__.py (they already handle epoch events)"
  depends_on: ["execute-2"]
  ```

#### execute-4: Training loop optimizations
- **Mode:** `subagent`
- **Context packet:**
  ```yaml
  subtask_id: "execute-4"
  goal: "Apply five training-loop speedups to GNNVolModel: PyG DataLoader, OneCycleLR, gradient accumulation, torch.compile, pre-converted Data objects"
  file_scope:
    - src/volforecast/models/gnn.py  # full file
    - src/volforecast/models/lstm.py  # reference for on_batch_progress throttling pattern
  write_scope:
    - src/volforecast/models/gnn.py
  acceptance_criteria:
    - "fit() uses torch_geometric.loader.DataLoader with pin_memory=True"
    - "OneCycleLR scheduler added (optional, enabled by default)"
    - "Gradient accumulation with configurable grad_accumulation_steps (default=1)"
    - "torch.compile() applied when device is CUDA and PyTorch >= 2.0"
    - "fit() accepts pre-built Data objects (list[Data]) in addition to list[dict]"
    - "No regression in prediction quality (same QLIKE within ±1%)"
  constraints:
    - "All optimizations gated behind config params with safe defaults"
    - "CPU path must still work (torch.compile and DataLoader num_workers=0 on CPU)"
    - "Do not change the public API signature (backward compatible)"
  depends_on: []
  ```

#### execute-5: Adjacency caching
- **Mode:** `inline`
- **Context packet:**
  ```yaml
  subtask_id: "execute-5"
  goal: "Add in-memory caching to build_adjacency to avoid redundant correlation matrix computation"
  file_scope:
    - src/volforecast/models/gnn_adjacency.py
  write_scope:
    - src/volforecast/models/gnn_adjacency.py
  acceptance_criteria:
    - "build_adjacency results cached in module-level dict keyed by (date, window, threshold)"
    - "Second call with same args returns cached result without recomputation"
    - "Cache is process-local (no cross-process sharing needed)"
  depends_on: []
  ```

#### execute-6: Integration test
- **Mode:** `subagent`
- **Context packet:**
  ```yaml
  subtask_id: "execute-6"
  goal: "Run GNN feature-stack trial with n_gpus=8 and verify multi-GPU utilization, progress bar output, and prediction quality"
  file_scope:
    - workspace/configs/  # GNN trial config
    - src/volforecast/pipeline/runner.py
    - src/volforecast/models/gnn.py
  write_scope:
    - workspace/configs/  # may need config updates
    - tests/  # smoke test if needed
  acceptance_criteria:
    - "Trial runs to completion without error"
    - "nvidia-smi shows multiple GPUs active during GNN fold phase"
    - "Progress bar displays GNN epoch progress and fold completion"
    - "QLIKE within ±1% of sequential baseline"
  depends_on: ["execute-1", "execute-2", "execute-3", "execute-4", "execute-5"]
  ```

---

## Estimated Impact

| Optimization | Speedup Source | Expected Impact |
|---|---|---|
| Graph pre-computation (Step 1) | Eliminate ~18× redundant graph builds per fold set | ~30% faster graph construction |
| Fold parallelism (Step 2) | 10 folds across 8 GPUs vs sequential | ~6-8× faster GNN feature extraction |
| PyG DataLoader (Step 4b) | Async data loading, prefetch | ~10-20% faster per fold |
| OneCycleLR (Step 4c) | Fewer epochs to convergence | ~20-40% fewer epochs |
| torch.compile (Step 4e) | Kernel fusion, reduced overhead | ~10-30% faster per epoch |
| Adjacency caching (Step 5) | Eliminate redundant correlation computation | Minor (seconds saved) |
| **Combined** | | **~8-12× total speedup** |

---

## Risks

| Risk | Mitigation |
|---|---|
| PyG Data objects not picklable across processes | Convert to raw tensors for IPC, reconstruct Data in worker |
| torch.compile incompatible with GATv2Conv | Gate behind try/except, fall back to eager mode |
| Memory pressure from 8 concurrent GNN models | GNN is tiny (~50K params × 8 = ~1.6MB); negligible |
| Graph pre-computation memory | ~2800 dates × 21 nodes × 9 features × 4 bytes = ~2MB; negligible |
| CUDA context overhead per worker process | Each spawned process initializes CUDA context (~200MB); 8 workers = ~1.6GB overhead. Acceptable with 8 GPUs. |

---

## Files Touched

| File | Changes |
|---|---|
| `src/volforecast/pipeline/runner.py` | Restructure `_make_gnn_feature_stack_fn`, add `_run_gnn_stacked_horizon_parallel`, add `_execute_gnn_fold` top-level function, add progress Queue wiring |
| `src/volforecast/models/gnn.py` | DataLoader, OneCycleLR, grad accumulation, torch.compile, accept pre-built Data objects |
| `src/volforecast/models/gnn_adjacency.py` | Add LRU cache to `build_adjacency` |
| `workspace/configs/` | Update GNN trial config with `n_gpus: 8` |

No changes needed to:
- `src/volforecast/cli/progress.py` (already handles epoch events)
- `src/volforecast/__main__.py` (already wires `on_train_progress`)
- `src/volforecast/evaluation/_parallel.py` (ProgressEvent schema already sufficient)

---

## Subagent Execution Plan

### Execution Order

```
Wave 1 (parallel):  execute-5 (inline) + execute-4 (subagent) + execute-1 (subagent)
Wave 2 (sequential): execute-2 (subagent) — depends on execute-1
Wave 3 (sequential): execute-3 (subagent) — depends on execute-2
                     (merge with execute-2 into one subagent since execute-3 only touches runner.py)
Wave 4:             execute-6 (subagent) — integration test, depends on all
```

**Optimization:** Steps 2+3 both touch `runner.py` and are strictly sequential (3 depends on 2). Merge them into a single subagent `execute-2+3` to avoid a second subagent reading the same large file. This reduces 6 subagent spawns to 4.

### Revised execution sequence

| Wave | Step(s) | Mode | Parallelizable |
|------|---------|------|----------------|
| 1a | execute-5 (adjacency cache) | inline | Yes — trivial, orchestrator does it |
| 1b | execute-4 (GNN training optimizations) | subagent | Yes — touches only gnn.py |
| 1c | execute-1 (graph pre-computation) | subagent | Yes — touches only runner.py |
| 2 | execute-2+3 (fold parallelism + progress) | subagent | No — depends on 1c |
| 3 | execute-6 (integration test) | subagent | No — depends on all |

Wave 1: Spawn execute-1 and execute-4 in parallel, do execute-5 inline. Three changes in three different files simultaneously.
Wave 2: After Wave 1 completes, spawn execute-2+3.
Wave 3: After Wave 2 completes, spawn execute-6.

---

### Subagent Prompt: execute-5 (INLINE — orchestrator does this)

Orchestrator reads `gnn_adjacency.py`, adds a module-level `_ADJACENCY_CACHE: dict = {}` and wraps `build_adjacency` with a cache lookup. ~10 lines of code change.

---

### Subagent Prompt: execute-1

```
You are implementing Step 1 of the GNN multi-GPU plan: pre-computing all graph snapshots once before the CV fold loop.

## Context

The `_make_gnn_feature_stack_fn` method in `src/volforecast/pipeline/runner.py` (starting ~line 1620) currently:
1. Defines `_build_graphs_for_rows(row_indices, include_targets)` which builds graph snapshots by iterating over dates in the given row indices
2. For each date: extracts node features from X_panel, calls `build_adjacency()` to get edge_index/edge_attr, assembles a graph dict
3. `_gnn_feature_stack_fold(train_idx, test_idx, h)` calls `_build_graphs_for_rows` twice (once for train, once for test) per CV fold

Problem: With 10 CV folds, each date's graph gets rebuilt ~18 times (appears in ~9 train sets + ~1 test set). The adjacency computation (rolling 60-day correlation) is the expensive part.

## Goal

Restructure `_make_gnn_feature_stack_fn` to:
1. Build ALL graph snapshots once upfront — one graph per unique date in X_panel — and store in `all_graphs_by_date: dict[Timestamp, dict]`
2. Each graph dict has keys: "x" (node features), "edge_index", "edge_attr", "date", "_row_indices", and "y" (targets from y_panel)
3. Modify `_gnn_feature_stack_fold` to select graphs from this pre-built cache instead of calling `_build_graphs_for_rows`

## File Scope (READ)
- `src/volforecast/pipeline/runner.py` lines 1620-1830 (_make_gnn_feature_stack_fn, _build_graphs_for_rows, _gnn_feature_stack_fold)
- `src/volforecast/models/gnn_adjacency.py` (build_adjacency signature)

## Write Scope
- `src/volforecast/pipeline/runner.py` — ONLY the `_make_gnn_feature_stack_fn` method body

## Acceptance Criteria
1. `_build_graphs_for_rows` is removed or replaced by a single upfront loop over all unique dates
2. Each date's graph is built exactly once (not per-fold)
3. `_gnn_feature_stack_fold` selects train/test graphs by looking up dates from the pre-built dict
4. Targets ("y") are always included in pre-built graphs (the fold callback can ignore them for test)
5. `_row_indices` mapping is preserved for result alignment
6. Sequential (single-GPU) execution produces identical output

## Constraints
- Do NOT change anything outside `_make_gnn_feature_stack_fn` method
- Do NOT change `_run_horizon`, XGBoost paths, or LSTM paths
- Do NOT add new imports at module level
- Keep the function signature of `_gnn_feature_stack_fold(train_idx, test_idx, h_inner)` unchanged — the returned function must be drop-in compatible
- Use `./vol exec` or `./vol bg` for ALL terminal commands (never bare python/pytest)
- Use `isBackground=true` for ALL `run_in_terminal` calls
- Kill all terminals before returning

## Implementation Notes

The key change: instead of `_build_graphs_for_rows` being called per fold, compute once:

```python
# Pre-compute all graphs (once, before returning fold callback)
unique_dates = sorted(all_dates.unique())
all_graphs_by_date = {}
for date in unique_dates:
    # ... same per-date logic as current _build_graphs_for_rows ...
    all_graphs_by_date[date] = graph
logger.info("GNN: pre-built %d graph snapshots", len(all_graphs_by_date))

def _gnn_feature_stack_fold(train_idx, test_idx, h_inner):
    # Get dates for train/test rows
    train_dates = set(all_dates[train_idx])
    test_dates = set(all_dates[test_idx])
    train_graphs = [all_graphs_by_date[d] for d in sorted(train_dates) if d in all_graphs_by_date]
    test_graphs = [all_graphs_by_date[d] for d in sorted(test_dates) if d in all_graphs_by_date]
    # ... rest unchanged ...
```

## Return Contract
Report: status, files changed with line ranges, verification evidence.
```

---

### Subagent Prompt: execute-4

```
You are implementing Step 4 of the GNN multi-GPU plan: training-loop optimizations for GNNVolModel.

## Context

`src/volforecast/models/gnn.py` contains GNNVolModel — a 2-layer GATv2 graph attention network for multi-symbol realized volatility forecasting. The `fit()` method currently:
1. Converts graph dicts to PyG Data objects via `_to_pyg()`
2. Manually batches with `Batch.from_data_list()` and `.to(device)` per batch per epoch
3. Uses fixed learning rate (AdamW)
4. No gradient accumulation
5. No torch.compile()

## Goal

Apply five training-loop speedups to GNNVolModel without sacrificing prediction quality:

### 4a: Accept pre-built Data objects
- `fit()` should accept `list[Data]` (PyG Data objects) directly, in addition to `list[dict]`
- If input is already Data objects, skip the `_to_pyg()` conversion
- Detection: check if first element is a `Data` instance

### 4b: Use PyG DataLoader for mini-batching
- Replace the manual `for batch_start in range(...)` loop with `torch_geometric.loader.DataLoader`
- Use `pin_memory=True` when device is CUDA
- Use `num_workers=2` when device is CUDA, `num_workers=0` on CPU
- This handles batching, collation, and async prefetch automatically
- Apply to both train and validation loops

### 4c: OneCycleLR learning rate scheduler
- Add `torch.optim.lr_scheduler.OneCycleLR` after optimizer creation
- `max_lr = self.learning_rate` (the configured LR becomes the peak)
- `epochs = self.max_epochs`, `steps_per_epoch = len(train_loader)`
- Call `scheduler.step()` after each batch (OneCycleLR is per-step, not per-epoch)
- Gate behind `use_scheduler: bool = True` constructor param

### 4d: Gradient accumulation
- Add `grad_accumulation_steps: int = 1` constructor param
- Accumulate gradients over N batches before calling `optimizer.step()`
- Scale loss by `1/grad_accumulation_steps` during accumulation
- Handle the final incomplete accumulation window at end of epoch

### 4e: torch.compile()
- After building the module, call `torch.compile(self._module, mode="reduce-overhead")`
- Only when: device is CUDA AND torch version >= 2.0
- Wrap in try/except — fall back to eager mode if compile fails (some PyG ops may not be compilable)
- Gate behind `compile: bool = True` constructor param
- Log whether compile succeeded or fell back

## File Scope (READ)
- `src/volforecast/models/gnn.py` (full file — ~650 lines)
- `src/volforecast/models/lstm.py` lines 1020-1120 (reference for on_batch_progress throttling, BUT do not copy — GNN doesn't need batch-level progress)

## Write Scope
- `src/volforecast/models/gnn.py` ONLY

## Acceptance Criteria
1. `fit()` accepts `list[Data]` without conversion (isinstance check)
2. Train/val loops use `DataLoader` with `pin_memory=True` on CUDA
3. OneCycleLR scheduler steps per batch (gated by `use_scheduler` param, default True)
4. Gradient accumulation works with configurable `grad_accumulation_steps` (default 1 = no accumulation)
5. `torch.compile()` applied on CUDA with graceful fallback (gated by `compile` param, default True)
6. All new params added to `__init__`, `get_params()`, and `get_arch_summary()`
7. `predict()` and `extract_features()` also use DataLoader for inference
8. CPU path still works (no CUDA-only assumptions)

## Constraints
- Do NOT change the public API signatures (backward compatible — new params have defaults)
- Do NOT add module-level imports for torch_geometric (keep lazy imports inside methods)
- Do NOT change `_GATModule` forward() or architecture
- Do NOT change save/load format (add new params to init_kwargs dict in get_params())
- Use `./vol exec` or `./vol bg` for ALL terminal commands
- Use `isBackground=true` for ALL `run_in_terminal` calls
- Kill all terminals before returning

## Implementation Notes

For DataLoader conversion in fit():
```python
from torch_geometric.loader import DataLoader as PyGLoader

# Convert inputs to Data objects if needed
if train_data and not isinstance(train_data[0], Data):
    train_data = [_to_pyg(g) for g in train_data]
    val_data = [_to_pyg(g) for g in val_data]

pin = self.device.startswith("cuda")
nw = 2 if pin else 0
train_loader = PyGLoader(train_data, batch_size=self.batch_size, shuffle=True, pin_memory=pin, num_workers=nw)
val_loader = PyGLoader(val_data, batch_size=self.batch_size, shuffle=False, pin_memory=pin, num_workers=nw)
```

For gradient accumulation:
```python
for batch_idx, batch in enumerate(train_loader):
    batch = batch.to(self.device)
    with torch.autocast(...):
        pred, _ = self._module(batch.x, batch.edge_index, batch.edge_attr)
        loss = criterion(pred[batch.mask], batch.y[batch.mask])
        loss = loss / self.grad_accumulation_steps
    loss.backward()
    if (batch_idx + 1) % self.grad_accumulation_steps == 0 or (batch_idx + 1) == len(train_loader):
        torch.nn.utils.clip_grad_norm_(self._module.parameters(), 1.0)
        optimizer.step()
        if self.use_scheduler:
            scheduler.step()
        optimizer.zero_grad()
```

## Return Contract
Report: status, files changed with line ranges, verification evidence.
```

---

### Subagent Prompt: execute-2+3 (merged)

```
You are implementing Steps 2+3 of the GNN multi-GPU plan: fold-parallel GPU dispatch + progress bar wiring.

## Context

The GNN feature stacker currently runs inside `_run_horizon`'s sequential fold loop via `feature_stack_fn`. Each fold trains a GNN model sequentially on a single GPU. We need to:

1. Pre-run ALL GNN folds in parallel across 8 GPUs (Phase 1)
2. Feed cached GNN features into the XGBoost fold loop (Phase 2)
3. Wire progress reporting so Rich progress bar shows GNN epoch progress

### Current architecture (after execute-1)
- `_make_gnn_feature_stack_fn` returns `_gnn_feature_stack_fold(train_idx, test_idx, h)` 
- Pre-built graph snapshots exist in `all_graphs_by_date` (one graph per date)
- `_gnn_feature_stack_fold` selects graphs by date, trains GNN, extracts features
- The returned feature DataFrame has per-fold GNN predictions aligned to X_panel

### Reference patterns (existing in runner.py)
- **LSTM parallel folds** (~line 2340): `ProcessPoolExecutor(max_workers=effective_gpus)` with `device_id = (fold_num-1) % effective_gpus`. Cross-process `Manager().Queue()` for epoch progress. Consumer thread reads queue and forwards to `on_train_progress` callback.
- **XGBoost parallel folds** (~line 620): `_run_horizon_gpu_parallel` + `_execute_tabular_fold` top-level worker function.
- Both patterns use `mp.get_context("spawn")` for CUDA safety.

### Two-phase approach
**Phase 1:** Before the main fold loop, detect `n_gpus > 1` and `feature_stack_fn is GNN-type`. Pre-run all GNN folds in parallel. Each worker: receives pre-built graphs (as dicts, not PyG Data — for pickle safety), trains GNN on assigned GPU, extracts features, returns DataFrame.

**Phase 2:** `_gnn_feature_stack_fold` becomes a simple dict lookup — returns pre-cached DataFrame for the current fold. No live GNN training during the XGBoost fold loop.

## Goal

1. Add `_execute_gnn_fold()` as a module-level top-level function (picklable for ProcessPoolExecutor)
2. Add pre-dispatch logic in `_make_gnn_feature_stack_fn` that detects `n_gpus > 1` and runs all GNN folds in parallel before returning the fold callback
3. Wire `Manager().Queue()` + consumer thread for epoch progress (matching LSTM pattern)
4. `on_fold_complete` fires when each GNN fold worker returns
5. If `n_gpus <= 1`, fall back to current sequential behavior

## File Scope (READ)
- `src/volforecast/pipeline/runner.py`:
  - `_make_gnn_feature_stack_fn` (~line 1620-1830) — current GNN feature stack 
  - `_run_one_horizon_sequences` (~line 2300-2420) — LSTM parallel pattern with progress queue (REFERENCE)
  - `_run_horizon_gpu_parallel` (~line 620-730) — XGBoost parallel pattern (REFERENCE)
  - `_execute_fold` (~line 51) and `_execute_tabular_fold` (~line 124) — top-level worker functions (REFERENCE)
  - `_run_horizon` (~line 400-480) — where feature_stack_fn is consumed
- `src/volforecast/models/gnn.py` — GNNVolModel.fit() signature, device param handling
- `src/volforecast/evaluation/_parallel.py` — ProgressEvent dataclass (lines ~50-70)

## Write Scope
- `src/volforecast/pipeline/runner.py` ONLY

## Acceptance Criteria
1. New `_execute_gnn_fold(fold_num, train_graph_dicts, test_graph_dicts, model_cls_name, model_params, device_id, requested_outputs, n_rows, panel_index_tuples, progress_queue)` at module level
2. Worker function: creates GNN model with `device=f"cuda:{device_id}"`, trains, extracts features, returns `{fold_num, result_df, ...}`
3. Worker sends epoch progress to queue: `{"type": "epoch", "fold": fold_num, "epoch": e, "max_epochs": max_epochs}`
4. `_make_gnn_feature_stack_fn` detects `n_gpus > 1` → pre-runs all folds via ProcessPoolExecutor
5. Manager Queue + consumer thread set up before dispatch, cleaned up after
6. Consumer thread forwards epoch events to `on_train_progress` callback
7. `on_fold_complete` called when each future completes
8. Pre-computed results stored in `_fold_cache: dict[int, DataFrame]`
9. Returned `_gnn_feature_stack_fold` simply does `return _fold_cache.get(fold_num)` when cache exists
10. Sequential fallback (n_gpus <= 1) works unchanged
11. Uses `mp.get_context("spawn")` for CUDA safety

## Constraints
- Do NOT modify `_run_horizon`, `_run_horizon_gpu_parallel`, or LSTM paths
- The fold callback signature `(train_idx, test_idx, h)` is UNCHANGED — fold_num must be inferred from (train_idx, test_idx) ordering or tracked internally
- Worker function must be at module-level (not a nested closure) for pickling
- Graph data passed to workers as raw dicts with tensors (not PyG Data objects — they may not pickle cleanly across spawn contexts)
- Worker reconstructs PyG Data objects from dicts inside the worker process
- `on_train_progress` and `on_fold_complete` callbacks need to be threaded through — check how `_make_gnn_feature_stack_fn` receives them (may need to add params)
- Use `./vol exec` or `./vol bg` for ALL terminal commands
- Use `isBackground=true` for ALL `run_in_terminal` calls
- Kill all terminals before returning

## Implementation Sketch

Module-level worker:
```python
def _execute_gnn_fold(
    fold_num: int,
    train_graph_dicts: list[dict],
    test_graph_dicts: list[dict],
    model_cls_name: str,
    model_params: dict,
    device_id: int,
    requested_outputs: list[str],
    progress_queue: Any | None = None,
) -> dict:
    from volforecast.registry import MODEL_REGISTRY
    model_cls = MODEL_REGISTRY[model_cls_name]
    params = dict(model_params)
    params["device"] = f"cuda:{device_id}"
    
    def _on_progress(epoch, max_epochs):
        if progress_queue is not None:
            progress_queue.put({"type": "epoch", "fold": fold_num, "epoch": epoch, "max_epochs": max_epochs})
    
    gnn = model_cls(**params)
    gnn.fit(train_graph_dicts, on_progress=_on_progress)
    
    all_graphs = train_graph_dicts + test_graph_dicts
    extracted = gnn.extract_features(all_graphs, outputs=requested_outputs)
    return {"fold_num": fold_num, "extracted": extracted, "all_graphs": all_graphs}
```

In `_make_gnn_feature_stack_fn`, after pre-building graphs:
```python
n_gpus = getattr(self.config, "n_gpus", 1)
if n_gpus > 1 and torch.cuda.device_count() > 1:
    # Phase 1: parallel GNN training
    import threading
    import torch.multiprocessing as _mp
    ctx = _mp.get_context("spawn")
    manager = _mp.Manager()
    progress_queue = manager.Queue()
    # ... consumer thread setup ...
    # ... ProcessPoolExecutor dispatch ...
    # Store results in _fold_cache
    
    fold_counter = [0]
    def _gnn_feature_stack_fold(train_idx, test_idx, h_inner):
        fold_counter[0] += 1
        return _fold_cache[fold_counter[0]]
    return _gnn_feature_stack_fold
```

## Important: Threading on_train_progress through

`_make_gnn_feature_stack_fn` currently receives `(self, X_panel, y_panel, sym_seqs, h, fs_cfg)`. The `on_train_progress` and `on_fold_complete` callbacks are NOT currently passed to this method. You need to either:
- Add them as parameters (preferred — check how `_make_feature_stack_fn` is called from `_build_and_run_horizon`)
- Or access them from `self` (check if pipeline stores them)

Read the call site (~line 1259) to determine how to thread them through.

## Return Contract
Report: status, files changed with line ranges, verification evidence.
```

---

### Subagent Prompt: execute-6

```
You are implementing Step 6 of the GNN multi-GPU plan: integration testing.

## Context

Steps 1-5 have been implemented:
1. Graph snapshots pre-computed once (not per-fold)
2. GNN folds dispatched across multiple GPUs via ProcessPoolExecutor
3. Progress bar wired via cross-process Queue
4. Training optimizations (DataLoader, OneCycleLR, grad accumulation, torch.compile)
5. Adjacency caching

## Goal

Verify the full GNN feature-stack pipeline works end-to-end with multi-GPU:
1. Ensure the GNN trial config has `n_gpus: 8` 
2. Run a quick smoke test (2 folds, 2 epochs max) to verify:
   - Multiple GPUs are utilized
   - Progress bar shows GNN epoch progress
   - No errors in the full pipeline
3. If errors occur, diagnose and fix them iteratively

## File Scope (READ)
- workspace/configs/ — find the GNN feature-stack trial config
- src/volforecast/pipeline/runner.py — GNN parallel dispatch code
- src/volforecast/models/gnn.py — GNN model
- src/volforecast/models/gnn_adjacency.py — adjacency builder

## Write Scope
- workspace/configs/ — update trial config if needed
- src/volforecast/pipeline/runner.py — bug fixes if needed
- src/volforecast/models/gnn.py — bug fixes if needed
- src/tests/ — smoke test if needed

## Acceptance Criteria
1. Trial runs to completion without error
2. Log output confirms multiple GPUs assigned to GNN folds
3. No regressions in existing LSTM/XGBoost trial configs

## Constraints
- Use `./vol exec` or `./vol bg` for ALL terminal commands
- Use `isBackground=true` for ALL `run_in_terminal` calls
- Kill all terminals before returning
- Do not make changes beyond what's needed to fix integration issues

## Return Contract
Report: status, files changed with line ranges, verification evidence (command output).
```
