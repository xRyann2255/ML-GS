# GNN Expansion for ml-vol-estimator — Plan Set Overview

**Date:** 2026-07-07 · **Status:** planning complete, execution not started
**Scope:** Expand `ml-vol-estimator` from one GATv2 feature-stack model to the full state-of-the-art GNN roster for realized-volatility forecasting, with first-class `vol run` integration, 8-GPU training, nested Rich progress, and a rigorously gated experiment program.

**How to use this set.** Copy this folder to the GS machine as `ml-vol-estimator/workspace/plans/gnn/`. Each plan is executed in its own GitHub Copilot session: paste the plan's **Orchestrator prompt** (last section of each plan) into Copilot Chat with `/execute`. The orchestrator dispatches one subagent per task using the **context packets** embedded in the plan; packets reference plan sections by anchor so subagents read only what they need. Plans are sequential; do not start plan N+1 before plan N's acceptance gate passes.

---

## 1. The ten plans

| # | Plan | Deliverable | New registry keys | Gate to proceed |
|---|------|-------------|-------------------|-----------------|
| 01 | Graph construction library | `volforecast/graphs/` package: 8 point-in-time graph builders + diagnostics + config plumbing | `GRAPH_REGISTRY`: identity, full, corr, knn, glasso, dy, sector, factor_residual | All builders pass PIT-leakage tests |
| 02 | Standalone graph-model pipeline | `_run_pooled_graphs` runner path: any `requires_graph` model is a first-class tournament entry | — (infra) | `model: {name: gnn}` runs end-to-end on synthetic data |
| 03 | GHAR + the graph ablation | Linear GHAR model + the 4-adjacency ablation experiment (the literature's single highest-value experiment) | `ghar` | Best graph beats identity, DM-significant (else: ship spillover features, deprioritize neural plans) |
| 04 | GNNHAR + STID control | One-hop nonlinear GNNHAR (1L/2L/3L) + the identity-embedding deflation control | `gnnhar`, `stid` | GNNHAR beats GHAR **and** STID under QLIKE+DM |
| 05 | Attention upgrades | Edge-feature GATv2 (vol-of-vol edges), UniMP/Transformer conv option, attention→spillover export | `gnn` extensions (`conv_type`, `edge_features`) | Attention ≥ fixed weights under DM (hypothesis test, may fail honestly) |
| 06 | Dynamic-graph recurrent model | DCRNN-HAR: diffusion convolution GRU over daily-refreshed directed DY graphs + HAR skip | `dcrnn_har` | QLIKE re-scoring vs GNNHAR at h∈{1,5,22} |
| 07 | Spectral + learned adjacency | GSP-HAR (magnetic Laplacian) + MTGNN-style learned-adjacency GNN + graph-signal-energy diagnostic | `gsp_har`, `gnn_learned` | Same harness comparison |
| 08 | 8-GPU orchestration + progress | Fold×GPU and seed×GPU parallelism for all graph models, multi-GPU Optuna HPO, per-GPU nested bars | — (infra) | 8-GPU run ≥5× faster than 1-GPU on synthetic benchmark; bars render correctly |
| 09 | Hybrid arms + regime fusion | Blending vs embedding-stacking arms; filtered-regime-probability features; regime-blended graphs | `extract_features` embeddings; regime graph blend | Purged-CV QLIKE + DM on both arms; blending is the prior |
| 10 | Grand GNN tournament | Full model×graph×horizon matrix, turbulence-split QLIKE, spillover dashboards, docs, trial registry | — (configs/eval) | Skeptic's-checklist sign-off, capstone-ready tables |

Dependency graph:

```
01 ──► 02 ──► 03 ──► 04 ──► 05 ─┐
              │       │      06 ─┼──► 09 ──► 10
              │       │      07 ─┘      ▲
              └───────┴──► 08 ──────────┘   (08 can start any time after 02)
```

---

## 2. What already exists (do not rebuild)

Verified against the 2026-07-06 GS snapshot. **Every plan extends these; duplicating them is a defect.**

- **`src/volforecast/models/gnn.py`** — `GNNVolModel` (`@register_model("gnn")`): 2-layer GATv2 + per-node MLP head, `requires_graph = True`, QLIKE/MSE losses in log-RV space (`_qlike_loss`: `mean(exp(clamp(y−ŷ)) − (y−ŷ) − 1)`), temporal val split, early stopping, AdamW + OneCycleLR, bf16 autocast, mega-batch-on-GPU optimization, `fit(graphs, on_progress=...)`, `predict(graphs)`, `extract_features(graphs, outputs=["prediction","node_attention"])`, torch.save persistence. Graph dict contract: `{"x": (N,F) np, "edge_index": (2,E) torch.long, "edge_attr": (E,) torch.float, "y": (N,) np, "date": Timestamp}`; pre-built PyG `Data` objects also accepted.
- **`src/volforecast/models/gnn_adjacency.py`** — `build_adjacency(panel_returns, date, window=60, threshold=0.3) -> (edge_index, edge_weight)` rolling-|corr| threshold graph, in-memory cache, causal (window ends at `date`); `build_adjacency_series`, `panel_returns_from_ohlcv(ohlcv_cache_dir)`.
- **Runner GNN plumbing** — `pipeline/runner.py`: `_make_gnn_feature_stack_fn` (line ~1914) builds per-fold graph snapshots and stacks `gnn_prediction`/`gnn_node_attention` into a downstream tree model; `_execute_gnn_fold` worker + GPU fold pool (lines ~2055–2149); dispatch via `getattr(model_cls, "requires_graph", False)` at line ~1546. **There is no standalone graph-model path** — today GNN output must pass through `feature_stack` into XGBoost (trial_068). Plan 02 fixes this.
- **8-GPU precedent** — `n_gpus: 8` in trial_063/068/077; fold→`cuda:{i % n_gpus}` via `ProcessPoolExecutor(spawn)`; tensors via shared memory; progress via `mp.Manager().Queue()` + daemon consumer; callbacks stripped with `dataclasses.replace(...)` before pickling and reattached as queue-posters in workers. Multi-GPU Optuna HPO precedent in `models/lstm_tuning.py` (JournalStorage, per-GPU workers, `tuning_epoch` events → per-GPU bars).
- **Progress system** — `cli/progress.py` (`StageProgress`, flat key-space, `add_subtask(indent=…)` visual nesting), `cli/console.py` singleton, `_run_tournament` callback wiring in `__main__.py` (~15 closures, one `threading.Lock`), `ProgressEvent` dataclass in `evaluation/_parallel.py`. Canonical model hook: `fit(..., on_progress=cb)` firing `cb(epoch, max_epochs)` per epoch.
- **Evaluation** — `evaluation/metrics.py` (log-space QLIKE, Duan retransformation), `statistical_tests.py` (panel-aware DM with date-averaged differentials, MCS block bootstrap with early stop, MZ, `tournament_table`), `tournament.py` + `_parallel.py` (pooled tournament, checkpoints), Plotly dashboard, `metrics.json`.
- **CV** — `utils/cv.py::PanelExpandingWindowCV` splits on **unique dates** (all symbols of a date share a fold — exactly right for graph snapshots); horizon-aware purge `effective_purge = max(purge_gap, h)`.
- **Data** — per-symbol RV parquets (`data/raw/ticks/{SYM}.parquet`), 34-symbol `SYMBOL_UNIVERSE` (21–29 used in trials), MultiIndex `(date, symbol)` pooled panel built in `run_pooled`, target `utils/targets.py::forward_log_rv` (log mean RV over next h days), `features/realized_correlation.py` (panel corr), `features/cross_asset.py::compute_dy_spillover` (rolling VAR(4) generalized FEVD — reuse for the `dy` graph builder).
- **Config** — dataclasses in `config.py` (`ExperimentConfig`, `ModelConfig`, `CVConfig`, `TuningConfig`, `FeatureStackConfig`, `SequenceConfig`, `TournamentConfig`, `n_gpus`), YAML in `workspace/configs/trial_NNN_*.yaml`, canonical example `_CANONICAL_EXAMPLE.yaml` (**must be updated whenever config/registry code changes** — repo instruction), trial registry `workspace/research/trials.yaml`, `./vol new-experiment`.
- **Deps** — `src/pyproject.toml` optional extras already include `graph = [torch, torch-geometric>=2.4]`. New deps require explicit listing in the plan (repo policy) — the only ones this set adds: none mandatory; `torch-geometric-temporal` is deliberately avoided (unmaintained; Plan 06 implements diffusion convolution directly, ~40 lines).
- **Also registered** (read before touching hybrids/regimes): `models/blend.py`, `models/stacking.py`, `models/regime_blend.py`, `models/calibrated.py`, `models/ensemble.py`.

---

## 3. Research grounding (what we implement and why — with expected gains)

Full citations in `reference/project-papers/README.md` §D and `notes/deep-research/2026-07-06-gnn-cross-asset-vol.md`, `notes/deep-research/spx-rv-gnn-regime-pipeline.md`; chapter: `guides/vol-learning-guide/markdown/ch16-graph-neural-networks.md`.

**Honest priors (calibrate every expectation to these):**

| Component | Realistic win vs rolling HAR (QLIKE, h=1) | Source |
|---|---|---|
| QLIKE-trained HAR | ~1–2% | Zhang et al. 2025 Table 1 |
| GHAR spillover terms | ~1–2% | ibid. (GHAR 0.983 QLIKE ratio) |
| GNNHAR1L (QLIKE-trained) | ~3–4% total (~8.7% at h=5; ~0 at h=22) | ibid. (0.961 / 0.913 / 0.965) |
| Attention over fixed weights | unproven under QLIKE+DM anywhere | chapter §Attention |
| Hybrid stacking over blending | ≈0 until proven | chapter §Three Wirings |
| Regime-conditioned graphs | unknown; no credible incumbent | Brief B |

“If a run of ours shows 20%, the first hypothesis is a bug or a leak, not brilliance.”

**Key architecture decisions locked by the evidence:**
1. **One nonlinear hop is the optimum.** Depth 2 is DM-significant for 1/27 stocks; depth 3 degrades (over-smoothing; MSE ratio 1.210). GNNHAR default `n_layers: 1`, hidden dim ~9, parameter budgets small (34 nodes × ~2 800 days).
2. **Train under QLIKE for h≤5; the loss is a bigger lever than the architecture.** At h=22 QLIKE-training costs 30–50% MSE — configs set per-horizon loss via `horizon_overrides`.
3. **Graph channel models spillovers only** — no self-loops in propagation; own dynamics stay in the linear HAR channel (Zhang et al. footnote 8).
4. **Graph construction is the contested lever** (GLASSO wins on 27 stocks; fully-connected wins on 10 indices; learned wins on crypto) — hence Plan 03's ablation *before* any neural work, and `graph.method` as a first-class config axis.
5. **Deflation controls are mandatory**: STID identity-embedding MLP (Plan 04) — “the graph must beat the embedding”; rolling re-estimated HAR is the baseline, never a stale one.
6. **Leakage hygiene priorities**: adjacency/scalers estimated on train windows only (clean template: re-estimate monthly on the rolling train window, freeze for the test block). Graph look-ahead is second-order (Sharpe +0.0–0.4) vs temporal-feature/execution leaks (+4 to +26) — spend the paranoia accordingly, but PIT graphs cost nothing here.
7. **Blend before stack; regime features before regime graphs.** Repo verdict since 2026-05 stands.
8. **Asynchronous closes**: cross-asset legs in graphs estimated on lagged/synchronized data; when in doubt lag foreign legs one day (our current universe is US-only, so this bites only if HYG/GLD/EEM/XLF/TLT/USO nodes are added).

**Model→paper map:** GHAR/GNNHAR (Zhang, Pu, Cucuringu & Dong 2025 IJF, `d-graph-gnn/zhang-et-al-2023-gnnhar-realized-volatility.pdf`, code `chaozhang-ox/GNNHAR`) · covariance GHAR (Zhang et al. 2024 JFEC) · DCRNN-HAR (Chi, Gao & Wang 2026 J. Forecasting, `MikeZChi/DCRNN-HAR`) · GSP-HAR (Chi et al. 2024, `MikeZChi/GSPHAR`) · SpotV2Net edge features (Brini & Toscano 2024) · UniMP/GTN-VF (Chen & Robert 2022 ICAIF) · STID (Shao et al. 2022 CIKM, `GestaltCogTeam/STID`) · MTGNN-style learned adjacency + EMGNN evolving (Zhou et al. 2025 Financial Innovation) · GNAR-HARX FC-vs-GLASSO counter-evidence (Ó Nualláin 2025) · GNHAR DY-graph linear (Boetti & Nunes 2026) · factor-residual edges (Cartea, Cucuringu & Fang 2026, abstract-only — design idea adopted, numbers not cited) · BGNN joint GBDT+GNN (Ivanov & Prokhorenkova ICLR 2021 — studied, not implemented) · regime exemplar Fang & Ślepaczuk 2026 (filtered MS prob, −5.1% QLIKE) · jump-model detector (Shu, Yu & Mulvey 2024, `Yizhan-Oliver-Shu/jump-models`) · negative exemplars: Kumar et al. 2026 (regime-GNN impostor), Cho & Lee 2025 (Hurst trigger loses to periodic retrain), Mallory 2026 (cross-asset null).

---

## 4. Shared conventions for every plan (the orchestrator repeats these to every subagent)

### 4.1 Global constraints (verbatim in every context packet's `constraints`)

- **TDD hard gate**: write the failing test first, run it, show it fail, implement minimum to pass, show it pass. Python changes only (configs/docs exempt).
- **All Python via `./vol`**: `./vol test -k <expr>` inner loop, `./vol test-all` before commit, `./vol lint`/`./vol typecheck` pre-commit only. Never bare `python`/`pytest`/`pip`/`uv`/`mypy`/`ruff`.
- **Execution isolation**: `./vol exec <cmd>` (blocking) or `./vol bg <cmd>` (fire-and-forget, poll for `EXIT_CODE=` sentinel); read the printed `OUTPUT_FILE`, never trust the terminal buffer; `isBackground=true` on every terminal call; kill every spawned terminal before returning.
- **File writes**: repo files in-place; every temp/output/artifact under `workspace/tmp/` only.
- **ML guardrails**: QLIKE primary; log-RV space; `PanelExpandingWindowCV`/purged CV only; features use t and earlier (`.shift(1)` before rolling); adjacency estimated on train windows only; explicit COVID statement per experiment; seeds everywhere (`np.random.default_rng(seed)`, `torch.manual_seed`).
- **No new dependencies** beyond those the plan explicitly adds to `src/pyproject.toml`.
- **Formula tests**: any new mathematical formula gets a `tests/unit/formulas/` gold-value test registered in `FORMULAS.md` (source paper + equation number + hand-computed JSON gold values).
- **Registry/config edits** must update `workspace/configs/_CANONICAL_EXAMPLE.yaml` in the same task.
- **Commit style**: conventional commits, lowercase, ≤72 chars, scope by path (`feat(models):`, `feat(graphs):`, `feat(pipeline):`, `test:`, `chore(config):`); source first, tests second, docs/config last; never `git add -A`.
- **Return contract**: `status: complete|blocked|partial`, files changed with line ranges, verification evidence (pasted test output), blockers, notes. Blocked/partial → orchestrator retries once with refined packet, then escalates.

### 4.2 Context packet template (repo schema, `policy/subagent_protocol.md`)

```yaml
subtask_id: "gnn-<plan>-<task>"        # e.g. "gnn-03-2"
goal: "<one testable sentence>"
file_scope:                             # files the subagent may READ (keep minimal)
  - workspace/plans/gnn/plan-NN-*.md    # its own task section — the code lives there
  - src/volforecast/...                 # integration points only
write_scope:                            # ONLY files the subagent may create/modify
  - src/volforecast/...
  - src/tests/...
acceptance_criteria:                    # machine-verifiable
  - "./vol test -k <expr> → N passed"
constraints: [<§4.1 items relevant to the task>]
context_summary: |
  <2–5 sentences; replaces reading conversation history>
depends_on: [<subtask_ids>]
```

### 4.3 Experiment conventions

- Configs cloned via `./vol new-experiment --base <yaml> --name trial_NNN_<desc> --set key=val`; numbers in these plans (079+) are **indicative — take the next free number from `./vol experiments` at execution time**.
- Every experiment registered in `workspace/research/trials.yaml` (`status: NOT_STARTED`) with hypothesis + baseline_config; verdict gate = **DM p < 0.05 AND QLIKE improvement**; COVID handling stated explicitly.
- Copilot **never auto-runs `vol run`** — it prints the command; the user launches training (8-GPU runs are long).
- Standard run: `./vol run --config workspace/configs/trial_NNN_<desc>.yaml` (add `--skip-ingest` when data is already cached).

### 4.4 Interface ledger (authoritative names used across plans)

| Symbol | Defined in | Signature (summary) |
|---|---|---|
| `GraphConfig` | Plan 01 → `config.py` | dataclass: `method="corr"`, `window=252`, `refit_every=21`, `min_history=60`, `input="returns"|"log_rv"`, `params={}`; Plan 02 adds `node_features: list[str]|None`; Plan 05 adds `edge_features: "weight"|"volofvol"` |
| `GraphBuilder` protocol | Plan 01 → `graphs/base.py` | `name`, `directed`, `build(returns: pd.DataFrame, date, symbols: list[str]) -> GraphSnapshot` (`returns` = pre-sliced estimation window) |
| `GraphSnapshot` | Plan 01 → `graphs/base.py` | frozen dataclass: `edge_index (2,E) int64 np`, `edge_weight (E,) float32 np`, `symbols`, `date`, `directed`, `method`; `.dense_adjacency(norm, binary)`, `.to_torch()` |
| `build_graph_schedule` | Plan 01 → `graphs/base.py` | `(returns, dates, builder, *, window=252, refit_every=21, min_history=60) -> dict[date, GraphSnapshot]` |
| `GRAPH_REGISTRY` / `@register_graph(name)` | Plan 01 → `registry.py` | mirrors `MODEL_REGISTRY` pattern |
| `DEFAULT_NODE_FEATURES` | Plan 02 → `pipeline/graph_data.py` | trial_068's 9 columns |
| `build_graph_dataset` | Plan 02 → `pipeline/graph_data.py` | `(X_panel, y_panel, dates, schedule, node_feature_cols, symbols) -> list[dict]` (gnn.py graph-dict contract) |
| `graph_input_panel` | Plan 02 → `pipeline/graph_data.py` | `(panel_data, graph_cfg, ohlcv_dir=None) -> wide date×symbol DataFrame` |
| `Pipeline._run_pooled_graphs` / `_run_one_horizon_graphs` | Plan 02 → `pipeline/runner.py` | standalone fold loop for `requires_graph` models; sequence-path return contract |
| `GHARVolModel` | Plan 03 → `models/ghar.py` | `@register_model("ghar")`, `__init__(*, input_dim, w_norm="sym"|"row", seed=42)`, pooled OLS, `coef_beta_`/`coef_gamma_`/`intercepts_` |
| per-label graph override | Plan 03 → `evaluation/_parallel.py` | `tournament.model_configs.<label>.graph: {…}` → synthetic config's `graph` |
| `GNNHARVolModel` | Plan 04 → `models/gnnhar.py` | `@register_model("gnnhar")`, `hidden_dim=9`, `n_layers∈{1,2,3}`, `n_seeds=3`, `_graph_channel()`, empty-graph nests QLIKE-HAR |
| `STIDVolModel` | Plan 04 → `models/stid.py` | `@register_model("stid")`, `embed_dim=16`, edges ignored (`requires_graph=True` for harness parity) |
| `GNNVolModel` extensions | Plan 05 → `models/gnn.py` | `conv_type: "gatv2"|"transformer"`, dynamic `edge_dim`, `spillover_matrix(graphs, *, symbols=None)`; edge features selected via `GraphConfig.edge_features` |
| `augment_edge_features` | Plan 05 → `pipeline/graph_data.py` | `(graphs, vov_idx) -> graphs` with `(E,3)` edge_attr |
| `VolOfVolLayer` | Plan 05 → `features/vol_of_vol.py` | `@register_feature_layer("vol_of_vol")` → `vov_d`, `vov_w` |
| `DCRNNHARVolModel` | Plan 06 → `models/dcrnn_har.py` | `@register_model("dcrnn_har")`, `k=2`, `seq_len=22`, `self.warmup = seq_len-1`, HAR skip; runner warmup splice `getattr(model, "warmup", 0)` |
| `GSPHARVolModel` | Plan 07 → `models/gsp_har.py` | `@register_model("gsp_har")`, magnetic Laplacian `q`, cached eigendecomposition per snapshot |
| `GNNLearnedAdjModel` | Plan 07 → `models/gnn_learned.py` | `@register_model("gnn_learned")`, `embed_dim=8`, `top_k=5`, `learned_adjacency()` |
| `magnetic_laplacian` / `graph_signal_energy` / `energy_series` | Plan 07 → `graphs/diagnostics.py` | `L^(q)`; `E(x) = Re(xᴴ L x)` |
| `_execute_graph_fold` / `_run_graphs_gpu_parallel` | Plan 08 → `pipeline/runner.py` | fold×GPU + seed×GPU pool; `graph_fold_*` progress events via `on_tuning_hpo` pipe |
| `tune_gnn_hyperparameters` | Plan 08 → `models/gnn_tuning.py` | multi-GPU Optuna (mirrors `lstm_tuning`) |
| `extract_features` `embedding` output | Plan 09 → `models/gnn*.py` | `outputs=["embedding"]` → `(total_nodes, hidden_dim)`; feature-stack columns `gnn_emb_NN` |
| `RegimeLayer` | Plan 09 → `features/regime.py` | `@register_feature_layer("regime")` → `regime_prob_d/w`, filtered + frozen-params PIT |
| `RegimeBlendGraphBuilder` | Plan 09 → `graphs/regime_blend.py` | `@register_graph("regime_blend")`, observable-state calm/stress blend |
| `conditional_qlike_split` / `conditional_dm` | Plan 10 → `evaluation/statistical_tests.py` | turbulence-split QLIKE (top-decile market RV) + bucketed panel-DM |

Any deviation from this table during execution must be recorded in the plan file and back-ported here.

---

## 5. GPU topology (the 8-GPU machine)

Three nested levels of GPU parallelism, all already patterned in the repo, generalized to graph models in Plan 08:

1. **Fold × GPU** (primary): `n_gpus: 8` → CV folds dispatched round-robin `cuda:{fold % 8}` via `ProcessPoolExecutor(spawn)`; ~17 folds/horizon × 3 horizons on trial-scale data → near-linear speedup to 8 GPUs.
2. **Seed × GPU** (GNNHAR seed-ensembling): `n_seeds: 5` per fold trained as independent jobs in the same pool (fold-major ordering preserves cache keys).
3. **HPO trial × GPU**: Optuna JournalStorage + one worker per GPU (the `lstm_tuning.py` pattern), `tuning_epoch` events → per-GPU nested bars (`GPU 3: trial 17 · epoch 44/200`).

Progress invariants (repeated in Plan 08 packets): Rich renders only in the main process; workers post picklable events to `mp.Manager().Queue()`; a daemon thread drains it under the progress lock; callbacks are stripped from configs before pickling and reattached as queue-posters inside workers.

---

## 6. Execution order and session budget

One plan ≈ one to three Copilot sessions (4–8 tasks each, ≤2 concurrent subagents, retry-once policy). Suggested calendar: Plans 01–02 (week 1), 03–04 + gates (week 2), 05–07 (weeks 3–4, parallelizable across sessions), 08 (any time after 02; before large trainings), 09 (week 5), 10 (week 6). Every session ends with `./vol test-all`, a conventional commit series, and a `workspace/research/weekly-progress.md` entry (Shipped/Decided/Learned/Next week — plain language).
