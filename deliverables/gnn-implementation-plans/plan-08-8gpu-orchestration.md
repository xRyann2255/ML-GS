# Plan 08 — 8-GPU Orchestration + Nested Progress for Graph Models

> **For the Copilot orchestrator:** execute with `/execute` (§7). TDD hard gate. Requires Plan 02 (graph path); independent of Plans 03–07's science — run it any time after 02, ideally before the big trainings. **The training machine has 8 GPUs; every pattern below already exists in this repo for LSTM/XGBoost — this plan generalizes, it does not invent.**

**Goal:** Saturate 8 GPUs for graph-model training under `vol run` with the repo's three proven parallelism levels — **fold × GPU**, **seed × GPU** (GNNHAR ensembles), and **HPO-trial × GPU** (Optuna) — with the same nested Rich progress bars the LSTM/XGBoost paths render (`GPU 3: fold 12 · epoch 44/200`), OOM resilience, and fold-cache/checkpoint compatibility.

**Architecture (mirror, don't invent):**
| Concern | Existing precedent (verbatim pattern to copy) | This plan's twin |
|---|---|---|
| Fold×GPU pool | sequence path `runner.py:2752–2875` — spawn `ProcessPoolExecutor`, fold *i* → `cuda:{i % g}`, shared-memory tensors | `_run_graphs_gpu_parallel` + module-level `_execute_graph_fold` |
| Worker progress | `_execute_fold` posts `{"type":"epoch",...}` to `mp.Manager().Queue()`; daemon consumer forwards | same, with `fold`/`device_id` in the event |
| Per-GPU bars | `_on_tuning_hpo` handler in `__main__.py:520–641` (`GPU 0: trial 7`, indent=2) | new event types `graph_fold_*` through the same `on_tuning_hpo` pipe |
| Callback hygiene | `dataclasses.replace(tuning_config, _on_*=None)` before pickling; reattach queue-posters in worker | identical |
| Multi-GPU HPO | `models/lstm_tuning.py` — Optuna `JournalStorage`, one worker/GPU, `tuning_epoch` events, resume | `models/gnn_tuning.py` |
| OOM resilience | LSTM batch-halving retry `lstm.py:1118–1128` | GNN mega-batch → DataLoader fallback |
| Pool-logic tests without GPUs | `test_gpu_parallel_model_retention.py` patches the executor with a thread-pool subclass | same technique |

**GPU budget math (why fold×GPU is the right primary axis):** trial-scale runs have ~17–18 folds per horizon × 3 horizons ≈ 53 fold-fits per model; with `n_seeds: 5` GNNHAR that is 265 independent trainings per model per experiment — embarrassingly parallel across 8 GPUs, wall-clock ≈ ⅛ of sequential. `dcrnn_har` (recurrent, dynamic graphs) benefits most.

## Global constraints

As 00-overview §4.1. Plan-specific hard rules (the repo's parallel-progress invariants, 00-overview §5):
1. Rich renders **only in the main process**, under the single progress lock.
2. Workers are module-level picklable functions; events are plain dicts/dataclasses — never closures.
3. Callbacks stripped from any config crossing a process boundary; reattached as queue-posters inside the worker.
4. Same results parallel vs sequential: fold seeds derive from fold number (not submission order); a determinism test compares `n_gpus=1` vs mocked-pool outputs.
5. Fold-cache keys are device-independent; cache hits fire `on_fold_complete` exactly as the sequence path does.

## File map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `src/volforecast/pipeline/runner.py` | `_execute_graph_fold` (module level), `_run_graphs_gpu_parallel`, dispatch + seed×GPU flattening |
| Create | `src/volforecast/models/gnn_tuning.py` | multi-GPU Optuna HPO for graph models |
| Modify | `src/volforecast/models/gnn.py`, `gnnhar.py` | `supports_tuning = True`, `tune_and_fit`, OOM fallback (gnn.py) |
| Modify | `src/volforecast/__main__.py` | `graph_fold_*` event rendering (per-GPU bars) |
| Create | `src/tests/unit/test_gpu_graph_parallel.py`, `src/tests/unit/test_gnn_tuning.py`, `src/tests/unit/test_progress_graphs.py` | CPU-mocked tests |
| Create | `src/tests/slow/test_gpu_scaling.py` | real-GPU benchmark (skipped w/o ≥2 CUDA devices) |

---

## Task 1: `_execute_graph_fold` worker + `_run_graphs_gpu_parallel`

**Copilot context packet:**

```yaml
subtask_id: "gnn-08-1"
goal: "Add a module-level picklable _execute_graph_fold worker and _run_graphs_gpu_parallel; _run_one_horizon_graphs dispatches to it when n_gpus>1 and cuda>=2; determinism and callback-hygiene tests with a mocked thread-pool executor."
file_scope:
  - workspace/plans/gnn/plan-08-8gpu-orchestration.md    # Task 1: worker spec
  - src/volforecast/pipeline/runner.py                   # _execute_fold (179-424) + sequence pool (2752-2875) = the template; _run_one_horizon_graphs (Plan 02/06)
  - src/tests/unit/test_gpu_parallel_model_retention.py  # thread-pool mock technique
write_scope:
  - src/volforecast/pipeline/runner.py
  - src/tests/unit/test_gpu_graph_parallel.py
acceptance_criteria:
  - "./vol test -k test_gpu_graph_parallel -> all pass (no GPU needed: executor mocked)"
  - "Mocked-pool predictions bit-identical to sequential n_gpus=1 on the fake graph model"
  - "Worker signature is module-level and picklable (spawn-safe): no closures, no self"
  - "Warmup models (Plan 06) work through the pool (warmup splice happens inside the worker from the shipped graph lists)"
  - "on_fold_complete fires per completed future in the main process; fold-cache hits short-circuit workers"
constraints:
  - "TDD failing-first"
  - "Worker receives: (fold_num, train_payload, test_payload, model_name, model_params, device_id, seed_offset, cache_ctx, progress_queue) where payloads are graph-dict lists whose torch tensors were detached+cpu before submission (pickle-safe)"
  - "Worker: ensure_registered(); params['device'] = f'cuda:{device_id}' (or 'cpu' when device_id is None); params['seed'] += seed_offset; fit; Duan on train residuals (warmup-aligned per Plan 06); returns dict {fold_num, preds, duan_correction, cache_hit}"
  - "Trigger in _run_one_horizon_graphs: n_gpus>1 and n_folds>1 and torch.cuda.is_available() and torch.cuda.device_count()>=2 — same guard as the sequence path; otherwise the Plan-02 sequential loop is untouched"
context_summary: |
  Direct twin of the sequence path's fold pool. Graph datasets are small (2800 dates x 34 nodes)
  so plain pickling to spawn workers is fine — no shared-memory dance needed (unlike LSTM's big
  tensors). All folds' graph dicts are prebuilt in the main process (Plan 02) and sliced per
  fold; workers never touch parquet or the graph builders. Per-fold Duan happens in the worker
  (like _execute_fold); the main process only assembles the prediction series.
depends_on: []
```

Reference worker skeleton (module level in `runner.py`, next to `_execute_fold`):

```python
def _execute_graph_fold(
    fold_num: int,
    train_graphs: list[dict],
    test_graphs: list[dict],
    model_name: str,
    model_params: dict,
    device_id: int | None,
    seed_offset: int,
    cache_ctx: dict | None,
    progress_queue=None,
) -> dict:
    from volforecast.registry import MODEL_REGISTRY, ensure_registered

    ensure_registered()
    model_cls = MODEL_REGISTRY[model_name]
    params = dict(model_params)
    if device_id is not None:
        params["device"] = f"cuda:{device_id}"
    params["seed"] = int(params.get("seed", 42)) + seed_offset

    # fold-cache short-circuit (compute_fold_cache_key/load_fold_cache — Plan 02 keys)
    ...

    model = model_cls(**params)
    warmup = int(getattr(model, "warmup", 0))
    pred_graphs = (train_graphs[-warmup:] + test_graphs) if warmup else test_graphs

    def _on_progress(epoch: int, max_epochs: int) -> None:
        if progress_queue is not None:
            progress_queue.put({
                "type": "graph_fold_epoch", "fold": fold_num,
                "device_id": device_id, "epoch": epoch, "max_epochs": max_epochs,
            })

    model.fit(train_graphs, on_progress=_on_progress)
    train_pred = model.predict(train_graphs)
    train_y = np.concatenate([g["y"] for g in (train_graphs[warmup:] if warmup else train_graphs)])
    valid = np.isfinite(train_y)
    resid = np.clip(train_y[valid] - train_pred[valid], -10.0, 10.0)
    duan = float(np.log(np.mean(np.exp(resid)))) if valid.any() else 0.0
    preds = model.predict(pred_graphs) + duan
    # save_fold_cache best-effort ...
    return {"fold_num": fold_num, "preds": preds, "duan_correction": duan, "cache_hit": False}
```

Pool driver: submit folds round-robin `device_id = (fold_num - 1) % effective_gpus`; strip callbacks from anything pickled; a daemon consumer thread drains `progress_queue` → forwards `graph_fold_epoch` to `on_tuning_hpo` (Task 3) and falls back to `on_train_progress(epoch, max_epochs)`; `on_fold_complete(h, fold)` fires as futures resolve. Commit — `feat(pipeline): fold-parallel multi-GPU execution for graph models`

## Task 2: Seed × GPU flattening for ensemble models

**Copilot context packet:**

```yaml
subtask_id: "gnn-08-2"
goal: "When the model has n_seeds>1 and the GPU pool is active, flatten (fold, seed) into independent jobs (each n_seeds=1, seed=base+seed_idx), then ensemble-average per fold in the main process and apply Duan AFTER averaging; determinism test vs in-process n_seeds ensembling."
file_scope:
  - workspace/plans/gnn/plan-08-8gpu-orchestration.md    # Task 2 spec
  - src/volforecast/pipeline/runner.py                   # Task 1 pool
  - src/volforecast/models/gnnhar.py                     # n_seeds semantics (mean of members)
write_scope:
  - src/volforecast/pipeline/runner.py
  - src/tests/unit/test_gpu_graph_parallel.py
acceptance_criteria:
  - "./vol test -k test_gpu_graph_parallel -> pass"
  - "Mocked-pool (fold,seed)-flattened predictions match sequential GNNHARVolModel(n_seeds=3) to atol 1e-6 (ensemble-then-Duan order preserved)"
  - "Jobs are fold-major ordered so early folds finish first (progressive on_fold_complete)"
constraints:
  - "TDD failing-first"
  - "Detection: n_seeds = int(model_params.get('n_seeds', 1)); flatten only when pool active AND n_seeds > 1"
  - "Worker jobs get params {**model_params, 'n_seeds': 1, 'seed': base_seed + fold_num + 1000 * seed_idx} — the 1000x stride keeps fold-seed and seed-idx offsets disjoint; workers return RAW (no-Duan) train and test predictions for ensemble members"
  - "Main process: mean member predictions per fold -> Duan from averaged train residuals -> apply to averaged test preds -> on_fold_complete when a fold's LAST member lands"
context_summary: |
  GNNHAR's protocol averages predictions over seed-varied fits. In-process that is a loop
  (Plan 04); on 8 GPUs each member is an independent job. Correctness subtlety: Duan must be
  computed on the ENSEMBLE-AVERAGED train residuals, not averaged per-member corrections —
  so seed-member workers return raw preds and the main process finishes the fold. This changes
  the Task-1 worker contract minimally: add return keys train_preds_raw/test_preds_raw when
  ensemble_member=True.
depends_on: ["gnn-08-1"]
```

Commit — `feat(pipeline): seed-ensemble members fan out across GPUs with ensemble-then-Duan`

## Task 3: Nested per-GPU progress bars

**Copilot context packet:**

```yaml
subtask_id: "gnn-08-3"
goal: "Render graph fold-parallel progress as nested per-GPU bars in the tournament display: 'GPU {d}: fold {f} · epoch e/max' subtasks under the model's fold bar, created/updated/removed by graph_fold_start/epoch/complete events through the on_tuning_hpo pipe; unit-tested at the event-handling level."
file_scope:
  - workspace/plans/gnn/plan-08-8gpu-orchestration.md    # Task 3 spec
  - src/volforecast/__main__.py                          # _on_tuning_hpo handler (520-641) = the pattern
  - src/volforecast/cli/progress.py                      # StageProgress API (add_subtask/update_subtask/remove_subtask)
  - src/tests/unit/test_progress.py                      # test style
write_scope:
  - src/volforecast/__main__.py
  - src/volforecast/pipeline/runner.py                   # emit graph_fold_start/complete around worker submits
  - src/tests/unit/test_progress_graphs.py
acceptance_criteria:
  - "./vol test -k test_progress_graphs -> pass"
  - "Handler creates at most one subtask per device_id; fold transitions update the same bar's description; graph_fold_complete removes it when the pool drains"
  - "All Rich mutations under the existing _progress_lock closure"
  - "Sequential (n_gpus=1) path renders exactly as before (characterization: no new bars)"
constraints: ["TDD failing-first: test the handler with a real StageProgress against a StringIO console (rich Console(file=...)), asserting _subtasks keys", "Event schema: {'type': 'graph_fold_start'|'graph_fold_epoch'|'graph_fold_complete', 'fold': int, 'device_id': int|None, 'epoch': int, 'max_epochs': int, 'model': str}"]
context_summary: |
  The tournament UI already renders per-GPU HPO bars from tuning_epoch events; graph
  fold-parallelism reuses the same channel (on_tuning_hpo) with graph_fold_* types so no new
  callback plumbing crosses tournament.py/_parallel.py. Handler shape mirrors __main__.py's
  _on_tuning_hpo: dict device_id -> subtask key; description f"GPU {d}: fold {f} · epoch";
  completed=epoch, total=max_epochs. The result on screen:
    models 2/5
      └─ gnnhar_1l                    27/53 folds
          └─ GPU 0: fold 25 · epoch  112/300
          └─ GPU 1: fold 26 · epoch   88/300
          ... (8 bars)
depends_on: ["gnn-08-1"]
```

Commit — `feat(cli): per-GPU nested progress bars for graph fold parallelism`

## Task 4: Multi-GPU Optuna HPO — `models/gnn_tuning.py`

**Copilot context packet:**

```yaml
subtask_id: "gnn-08-4"
goal: "Create models/gnn_tuning.py::tune_gnn_hyperparameters mirroring lstm_tuning (JournalStorage, one Optuna worker per GPU, tuning_start/tuning_epoch/tuning_trial_complete/tuning_complete events, resume), wire it into _run_one_horizon_graphs when tuning.enabled, and flip supports_tuning=True on gnn/gnnhar with a graph-shaped tune_and_fit."
file_scope:
  - workspace/plans/gnn/plan-08-8gpu-orchestration.md    # Task 4: search space
  - src/volforecast/models/lstm_tuning.py                # THE template — read fully
  - src/volforecast/pipeline/runner.py                   # sequence HPO wiring (2643-2750) to mirror
  - src/volforecast/models/gnn.py
  - src/volforecast/models/gnnhar.py
write_scope:
  - src/volforecast/models/gnn_tuning.py
  - src/volforecast/models/gnn.py
  - src/volforecast/models/gnnhar.py
  - src/volforecast/pipeline/runner.py
  - src/tests/unit/test_gnn_tuning.py
acceptance_criteria:
  - "./vol test -k test_gnn_tuning -> pass (n_trials=3, cpu, tiny synthetic graphs)"
  - "Objective: inner temporal split of the FIRST fold's train graphs (val tail), QLIKE on val; NO test-fold data touched (leakage test asserts date bounds)"
  - "Events flow: a fake queue collects tuning_start -> n x (tuning_epoch..., tuning_trial_complete) -> tuning_complete"
  - "Best params merged into model_params for all folds; search-space keys stripped from fixed params first (lstm_tuning convention)"
constraints:
  - "TDD failing-first"
  - "GNN_SEARCH_SPACE = {hidden_dim: int log [4,64], n_heads: cat {1,2,4} (gnn only), n_layers: cat {1,2}, learning_rate: float log [1e-4,1e-2], dropout: float [0,0.3] (gnn only), weight_decay: float log [1e-6,1e-3]}"
  - "JournalStorage in tuning.storage_dir or tempdir; existing-trials counted for resume; TPESampler(seed)"
  - "effective_gpus = min(n_gpus, torch.cuda.device_count()); cpu fallback = 1 worker"
context_summary: |
  lstm_tuning.py is the proven multi-GPU Optuna harness (per-GPU workers pinning
  torch.cuda.set_device, shared journal, pruning, event queue -> per-GPU bars). gnn_tuning is
  its graph twin: trial objective builds the model from sampled params on the tuning split and
  returns val QLIKE. Runner wiring goes at the top of _run_one_horizon_graphs (before the fold
  loop), guarded by self.config.tuning.enabled, exactly where the sequence path tunes
  (runner.py 2643+). tune_and_fit on the model classes delegates here (graph-shaped signature,
  like LSTM's sequence-shaped one).
depends_on: ["gnn-08-1"]
```

Commit — `feat(models): multi-GPU Optuna HPO for graph models`

## Task 5: OOM fallback, real-GPU scaling benchmark, config sweep

**Copilot context packet:**

```yaml
subtask_id: "gnn-08-5"
goal: "Add OOM fallback to GNNVolModel/GNNHARVolModel mega-batch fits (catch torch.cuda.OutOfMemoryError -> empty_cache -> retry with chunked date-batches), a slow real-GPU scaling test (skipped without >=2 CUDA devices), and verify all gnn trial configs carry n_gpus: 8."
file_scope:
  - workspace/plans/gnn/plan-08-8gpu-orchestration.md
  - src/volforecast/models/gnn.py                        # mega-batch fit (lines ~344-470)
  - src/volforecast/models/gnnhar.py
  - src/volforecast/models/lstm.py                       # OOM retry pattern (1118-1128)
  - workspace/configs/                                    # trial_079..085
write_scope:
  - src/volforecast/models/gnn.py
  - src/volforecast/models/gnnhar.py
  - src/tests/unit/test_gnn_oom.py
  - src/tests/slow/test_gpu_scaling.py
  - workspace/configs/trial_079_gnn_native.yaml           # only if n_gpus missing
acceptance_criteria:
  - "./vol test -k test_gnn_oom -> pass (OOM simulated by monkeypatching the forward to raise torch.cuda.OutOfMemoryError once)"
  - "slow test: pytest.mark.slow + skipif(torch.cuda.device_count() < 2); asserts n_gpus=4 wall time < 0.6x n_gpus=1 on a 12-fold synthetic run"
  - "grep confirms every gnn-family trial config sets n_gpus: 8"
constraints: ["TDD failing-first", "Max 2 OOM retries then re-raise (lstm convention)", "Chunk size halves per retry starting at len(train)/4 dates"]
context_summary: |
  The mega-batch-on-GPU optimization in gnn.py assumes the whole training set fits in VRAM —
  true at 21 nodes but not guaranteed at 34 nodes x wider features x 8 concurrent fold workers
  per GPU pair. Fallback: chunked date-batches (the DataLoader path already exists for >10k
  graphs; reuse it with a forced flag). The scaling benchmark documents the actual speedup for
  the research journal and catches serialization bottlenecks early.
depends_on: ["gnn-08-2"]
```

Commit — `feat(models): OOM fallback for graph fits; test(slow): GPU scaling benchmark`

## 7. Orchestrator prompt

```
/execute Implement Plan 08 (8-GPU orchestration) from workspace/plans/gnn/plan-08-8gpu-orchestration.md
Precondition: Plan 02 merged (Plans 03-07 NOT required — do not block on them).
Waves: gnn-08-1 -> (gnn-08-2, gnn-08-3 in parallel, max 2) -> gnn-08-4 -> gnn-08-5.
Every task touching runner.py or __main__.py finishes with the FULL ./vol test suite.
The parallel-progress invariants in the plan's Global constraints are non-negotiable — verify
each explicitly in the return contract. Integration: ./vol test-all, lint, typecheck.
Weekly-progress entry (Shipped: graph models train fold-, seed-, and trial-parallel across
8 GPUs with per-GPU progress bars). Do NOT start Plan 09.
```

## Acceptance gate → Plans 09–10

- All CPU-mocked parallel tests green; determinism (parallel == sequential) proven for plain and seed-ensemble models; per-GPU bars render (visual check on the GS machine during trial_082's rerun).
- On the GS machine the user re-runs one heavy config (`trial_084`) with `n_gpus: 8` and records the wall-clock vs the sequential baseline in the research journal.
