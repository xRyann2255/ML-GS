# Plan 06 — DCRNN-HAR: Diffusion-Convolution Recurrence over Dynamic DY Graphs

> **For the Copilot orchestrator:** execute with `/execute` (§6). TDD hard gate. Requires Plans 01–05 merged. This model carries the literature's biggest *unadjudicated* claim — DCRNN-HAR's MSE gains **grow** with horizon (−13% h=1 → −54% h=22 on SPX) while GNNHAR's fade to zero — but was never scored under QLIKE. Our experiment is the arbiter the chapter asks for ("regenerate ST-GNN forecasts and re-score under Patton-robust QLIKE with DM tests").

**Goal:** Implement DCRNN-HAR (Chi, Gao & Wang 2026, J. Forecasting 45(3); repo `MikeZChi/DCRNN-HAR`): a GRU whose matrix multiplications are replaced by **bidirectional diffusion convolutions** over the directed, daily-refreshed DY spillover graph, with a jointly-trained **plain-HAR skip connection** added to the network output ("the paper's best design decision"). Run it in our harness at h ∈ {1,5,22} under QLIKE + DM against GNNHAR and HAR.

**Architecture:**
- **Diffusion convolution** (Li et al. 2018, DCRNN): for input `X ∈ R^{N×F}` and directed weighted adjacency `W`,
  `DConv(X) = Σ_{k=0}^{K} ( θ_k^{fwd} (D_O^{-1} W)^k + θ_k^{bwd} (D_I^{-1} Wᵀ)^k ) X Θ_k` — information spreading k hops *along* and *against* spillover direction; `K = 2` default (chapter: learned ζ_k weight each distance).
- **DCGRU cell**: GRU update/reset/candidate gates computed with DConv instead of dense matmul.
- **Sequence**: each sample at date t unrolls the cell over the last `seq_len` (default 22) days of node features, each day paired with **its own** graph snapshot (`refit_every: 1`, 22-day DY look-back — the paper's dynamic protocol).
- **HAR skip**: `ŷ = head(h_T) + Linear(x_T)` where `x_T` holds the HAR triple — trained jointly.
- **Warmup contract**: predicting test dates requires the preceding `seq_len − 1` graphs. New generic mechanism: models expose `self.warmup: int`; `_run_one_horizon_graphs` prepends the last `warmup` **train** graphs to the test list and the model returns predictions only for the non-warmup dates. PIT-safe (warmup graphs are train-period, and their features are lagged anyway).
- Trading-day masks from the paper are **skipped** (single-calendar US universe) — recorded as future work for cross-asset ETF nodes.

**Tech stack:** pure torch, dense matmuls (N ≤ 34; powers of W precomputed per date). `torch-geometric-temporal` deliberately avoided (unmaintained; our DConv is ~40 lines). No new dependencies.

**Research grounding:** DCRNN-HAR best in 48/48 scenarios, 75%-MCS 48/48 vs HAR 12/48; SPX h=1 MSE 0.125 vs 0.136 — **but MSE/MAE only, no QLIKE/DM, single 70/30 split containing COVID, margin vs nearest prior model only 4–11%** (Brief A). Prediction registered in trials.yaml: *h=1 gains shrink to low single digits under QLIKE; the h=22 blowout inverts or vanishes.*

## Global constraints

As 00-overview §4.1. Plan-specific:
- Warmup mechanism must be generic (attribute-driven), tested independently of DCRNN, and inert for `warmup = 0` models (all existing graph models — characterization).
- Gradient flows through both channels (test: HAR-skip weights and DConv weights both move).
- `K`, `seq_len`, `hidden_dim` are config params; parameter count printed in `get_arch_summary` (budget: <20k).

## File map

| Action | Path | Responsibility |
|---|---|---|
| Create | `src/volforecast/models/dcrnn_har.py` | `DiffusionConv`, `DCGRUCell`, `_DCRNNHARModule`, `DCRNNHARVolModel` |
| Modify | `src/volforecast/registry.py` | import |
| Modify | `src/volforecast/pipeline/runner.py` | generic warmup splice in `_run_one_horizon_graphs` |
| Create | `src/tests/unit/test_dcrnn_har.py`, extend `src/tests/unit/test_runner_graphs.py` | tests |
| Create | `workspace/configs/trial_084_dcrnn_har.yaml` | the horizon-conflict arbiter |

---

## Task 1: Diffusion convolution + DCGRU cell (pure modules)

**Copilot context packet:**

```yaml
subtask_id: "gnn-06-1"
goal: "Implement DiffusionConv (bidirectional K-step random-walk convolution over a dense directed W) and DCGRUCell (GRU gates via DiffusionConv) as tested nn.Modules in models/dcrnn_har.py."
file_scope:
  - workspace/plans/gnn/plan-06-dcrnn-har.md      # Task 1: math + code + tests
  - src/volforecast/models/gnnhar.py               # module conventions
write_scope:
  - src/volforecast/models/dcrnn_har.py
  - src/tests/unit/test_dcrnn_har.py
acceptance_criteria:
  - "./vol test -k test_dcrnn_har -> module tests pass"
  - "K=0 DiffusionConv == plain Linear (hand-check)"
  - "Directedness matters: transposing W changes the output (asymmetry test)"
  - "DCGRUCell output shape (N, hidden) and gates bounded (h in tanh range)"
constraints: ["TDD failing-first", "Pure torch, dense ops", "Row-normalize: forward D_O^-1 W (out-degree), backward D_I^-1 W^T (in-degree); zero rows stay zero"]
context_summary: |
  DCRNN's core (Li et al. 2018 eq. 2): bidirectional diffusion so a node hears both who it
  spills to and who spills into it — essential on the directed DY graph. Dense powers are fine
  at N<=34. DCGRUCell replaces each of the three GRU matmuls with a DiffusionConv over
  concat(x, h).
depends_on: []
```

Reference implementation (module half of `dcrnn_har.py`):

```python
class DiffusionConv(nn.Module):
    """Bidirectional K-step diffusion convolution (Li et al. 2018, DCRNN eq. 2)."""

    def __init__(self, in_dim: int, out_dim: int, k: int = 2) -> None:
        super().__init__()
        self.k = k
        # one weight per (direction, step) incl. step 0 identity: (2K+1) matrices
        self.weights = nn.ModuleList(
            nn.Linear(in_dim, out_dim, bias=False) for _ in range(2 * k + 1)
        )
        self.bias = nn.Parameter(torch.zeros(out_dim))

    @staticmethod
    def normalize(w: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """(fwd, bwd) = (D_O^-1 W, D_I^-1 W^T); rows with zero degree stay zero."""
        d_out = w.sum(1, keepdim=True).clamp(min=1e-12)
        d_in = w.sum(0, keepdim=True).clamp(min=1e-12).T
        return w / d_out, w.T / d_in

    def forward(self, x: torch.Tensor, fwd: torch.Tensor, bwd: torch.Tensor) -> torch.Tensor:
        out = self.weights[0](x)                       # k = 0 (identity support)
        xf, xb = x, x
        for step in range(1, self.k + 1):
            xf = fwd @ xf
            xb = bwd @ xb
            out = out + self.weights[2 * step - 1](xf) + self.weights[2 * step](xb)
        return out + self.bias


class DCGRUCell(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int, k: int = 2) -> None:
        super().__init__()
        self.gates = DiffusionConv(in_dim + hidden_dim, 2 * hidden_dim, k)   # r, u
        self.cand = DiffusionConv(in_dim + hidden_dim, hidden_dim, k)

    def forward(self, x, h, fwd, bwd):
        ru = torch.sigmoid(self.gates(torch.cat([x, h], -1), fwd, bwd))
        r, u = ru.chunk(2, dim=-1)
        c = torch.tanh(self.cand(torch.cat([x, r * h], -1), fwd, bwd))
        return u * h + (1.0 - u) * c
```

Key tests: `test_k0_equals_linear`, `test_direction_asymmetry` (W upper-triangular: node 0's fwd output nonzero, bwd path differs; `assert not torch.allclose(conv(x, f, b), conv(x, b, f))`), `test_zero_degree_rows_stable` (no NaN), `test_dcgru_shapes_and_state_update`.

Commit — `feat(models): diffusion convolution + DCGRU cell`

## Task 2: `DCRNNHARVolModel` + generic warmup contract

**Copilot context packet:**

```yaml
subtask_id: "gnn-06-2"
goal: "Implement DCRNNHARVolModel (DCGRU unroll over seq_len days of per-date graphs + jointly-trained HAR skip; warmup attribute) registered as 'dcrnn_har', and add the generic warmup splice to _run_one_horizon_graphs; full test coverage."
file_scope:
  - workspace/plans/gnn/plan-06-dcrnn-har.md      # Task 2 section
  - src/volforecast/models/dcrnn_har.py            # Task 1 modules
  - src/volforecast/models/gnnhar.py               # fit-loop conventions (losses, early stop, seeds)
  - src/volforecast/pipeline/runner.py             # _run_one_horizon_graphs (Plan 02)
write_scope:
  - src/volforecast/models/dcrnn_har.py
  - src/volforecast/registry.py
  - src/volforecast/pipeline/runner.py
  - src/tests/unit/test_dcrnn_har.py
  - src/tests/unit/test_runner_graphs.py
acceptance_criteria:
  - "./vol test -k 'test_dcrnn_har or test_runner_graphs' -> all pass"
  - "predict(graphs) returns len == (len(graphs) - warmup) * N, aligned to graphs[warmup:]"
  - "Runner: for a model with warmup=w, test predictions cover exactly the fold's test dates (warmup graphs spliced from train, never counted)"
  - "warmup=0 models unaffected (existing test_runner_graphs green untouched)"
  - "Joint training: after fit on planted data, both har_skip and DCGRU weights changed from init"
constraints:
  - "TDD failing-first"
  - "Model contract: fit(graphs) builds overlapping windows internally (stride 1); loss only on the final-step prediction of each window (one-step-ahead target, matching our forward_log_rv target)"
  - "self.warmup = seq_len - 1 set in __init__; runner reads getattr(model, 'warmup', 0) AFTER instantiation and splices train_graphs[-warmup:] + test_graphs"
  - "Sequence windows shorter than seq_len at the train start are dropped (not padded)"
context_summary: |
  The recurrent model needs temporal context. Contract: fit receives the fold's ordered train
  graphs and forms rolling windows [t-seq_len+1..t] internally, predicting y_t (the forward-RV
  target attached to date t). predict receives warmup+test graphs and returns predictions for
  the test dates only. Runner change is 6 lines in _run_one_horizon_graphs: instantiate model
  before building test datasets, splice warmup graphs, and slice nothing (model already returns
  only non-warmup predictions). HAR skip: y = head(h_T) + w_skip^T x_T + b — jointly trained.
depends_on: ["gnn-06-1"]
```

Model skeleton (second half of `dcrnn_har.py`):

```python
class _DCRNNHARModule(nn.Module):
    def __init__(self, n_nodes, input_dim, hidden_dim, k):
        super().__init__()
        self.cell = DCGRUCell(input_dim, hidden_dim, k)
        self.head = nn.Linear(hidden_dim, 1)
        self.har_skip = nn.Linear(input_dim, 1)          # jointly-trained plain-HAR channel
        self.alpha = nn.Parameter(torch.zeros(n_nodes))

    def forward(self, xs, fwds, bwds):                   # lists of length seq_len
        h = torch.zeros(xs[0].shape[0], self.head.in_features, device=xs[0].device)
        for x, f, b in zip(xs, fwds, bwds):
            h = self.cell(x, h, f, b)
        return self.alpha + self.head(h).squeeze(-1) + self.har_skip(xs[-1]).squeeze(-1)


@register_model("dcrnn_har")
class DCRNNHARVolModel(_BaseModel):
    REQUIRED_LAYERS = ["har_core"]
    requires_graph = True
    family = "gnn"
    description = "DCRNN-HAR: diffusion-conv GRU over dynamic directed DY graphs + HAR skip"

    def __init__(self, *, input_dim, hidden_dim=16, k=2, seq_len=22,
                 learning_rate=1e-3, weight_decay=1e-4, max_epochs=150,
                 early_stopping_rounds=15, val_fraction=0.15, loss="qlike",
                 batch_dates=64, device="auto", precision="auto", seed=42):
        ...
        self.warmup = seq_len - 1
    # fit: precompute per-date (fwd, bwd) = DiffusionConv.normalize(dense W_t) once;
    #      windows = [(t-seq_len+1 .. t) for t in range(seq_len-1, T)];
    #      minibatch over windows (batch_dates windows per step), loss on final-step preds
    #      masked by finite y; temporal val split on window END dates; early stopping;
    #      gnnhar-style seeding/device/precision.
    # predict: same windowing over (warmup + test) graphs; emit preds for windows whose
    #      end date is a NON-warmup graph; flatten node-major.
```

Runner splice (in `_run_one_horizon_graphs`, replacing the current instantiate-fit-predict block):

```python
            model = model_cls(**fold_params)
            warmup = int(getattr(model, "warmup", 0))
            fit_graphs = train_graphs
            pred_graphs = (train_graphs[-warmup:] + test_graphs) if warmup else test_graphs
            model.fit(fit_graphs, **fit_kwargs)
            ...
            test_flat = model.predict(pred_graphs) + duan_correction
            # test_flat already covers ONLY the test dates (model drops warmup outputs)
```

(For the Duan correction on warmup models: compute train residuals via `model.predict(train_graphs)` which itself drops the first `warmup` train dates — align `train_y` accordingly: `train_y = concat(y of train_graphs[warmup:])`. Test this.)

Commit — `feat(models): DCRNN-HAR with generic warmup contract in the graph runner`

## Task 3: The horizon-conflict arbiter experiment

**Copilot context packet:**

```yaml
subtask_id: "gnn-06-3"
goal: "Create trial_084: dcrnn_har (dynamic daily DY graphs) vs gnnhar_1l (monthly static winner graph) vs har at h=1/5/22 under QLIKE; register with the pre-registered prediction about horizon behavior."
file_scope:
  - workspace/plans/gnn/plan-06-dcrnn-har.md
  - workspace/configs/trial_082_gnnhar_vs_ghar_stid.yaml
  - workspace/research/trials.yaml
write_scope:
  - workspace/configs/trial_084_dcrnn_har.yaml
  - workspace/research/trials.yaml
acceptance_criteria: ["Config parses", "trial-084 registered with the pre-registered prediction verbatim"]
constraints: ["Do NOT run vol run", "dcrnn_har arm uses per-label graph override: {method: dy, input: log_rv, window: 252, refit_every: 1, params: {var_lags: 4, fevd_horizon: 10, threshold: 0.05}}", "n_gpus: 8, parallel_models: 1"]
context_summary: |
  Pre-registered prediction (from Brief A, experiment 2): "h=1 gains shrink to low single digits
  under QLIKE; the h=22 MSE blowout (-54%) inverts or vanishes." If instead DCRNN-HAR's gains
  GROW with horizon under QLIKE + DM, that overturns the GNNHAR horizon-fade result on our data
  and reshapes Plan 10's headline. Either outcome resolves the literature's open conflict on our
  universe. Note in the hypothesis: refit_every: 1 makes graph construction ~2800 VAR fits per
  experiment — the dy builder is ~seconds each; if wall time is prohibitive, fall back to
  refit_every: 5 and record the deviation.
depends_on: ["gnn-06-2"]
```

Config core (scaffold as trial_082; `models: [har, gnnhar_1l, dcrnn_har]`, `baseline: har`):

```yaml
    dcrnn_har:
      name: dcrnn_har
      params: {hidden_dim: 16, k: 2, seq_len: 22, loss: qlike, max_epochs: 150,
               early_stopping_rounds: 15, device: auto, seed: 42}
      graph: {method: dy, input: log_rv, window: 252, refit_every: 1, min_history: 100,
              node_features: [log_rv_d, log_rv_w, log_rv_m],
              params: {var_lags: 4, fevd_horizon: 10, threshold: 0.05}}
```

Commit — `chore(config): trial_084 DCRNN-HAR horizon-conflict arbiter`

## 6. Orchestrator prompt

```
/execute Implement Plan 06 (DCRNN-HAR) from workspace/plans/gnn/plan-06-dcrnn-har.md
Precondition: Plan 05 merged. Sequence: gnn-06-1 -> gnn-06-2 -> gnn-06-3.
gnn-06-2 touches runner.py: rerun the FULL ./vol test suite before its commit, and confirm
test_runner_graphs warmup=0 characterization is untouched.
TDD everywhere; ./vol only; return contracts. Integration: ./vol test-all, lint, typecheck.
Weekly-progress entry. Print trial_084 launch command; do NOT run. Do NOT start Plan 07.
```

## Acceptance gate → Plan 07

Module + model + warmup tests green; no regression in existing graph-path tests; trial_084 registered with the pre-registered prediction. GPU note for Plan 08: `dcrnn_har` is the slowest model in the roster (recurrent, dynamic graphs) — it is the primary beneficiary of fold×GPU parallelism.
