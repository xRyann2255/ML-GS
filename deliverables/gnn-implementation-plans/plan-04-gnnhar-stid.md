# Plan 04 — GNNHAR (one nonlinear hop) + STID deflation control

> **For the Copilot orchestrator:** execute with `/execute` using the Orchestrator prompt in §7. TDD hard gate. Requires Plans 01–03 merged **and trial_080's gate passed** (if the gate failed, execute only Task 1 + the `gnnhar` replication config and mark the rest deferred).

**Goal:** Implement the canonical vol-GNN — GNNHAR (Zhang, Pu, Cucuringu & Dong 2025, eqs. 7–8): a GCN-style propagation **without self-loops** feeding a graph channel next to a linear HAR channel, trained under QLIKE with seed-ensembling — plus the mandatory deflation control, STID (Shao et al. 2022): per-symbol identity embeddings + MLP, no graph. The experiment gates the whole neural program: **GNNHAR must beat both GHAR and STID under QLIKE + DM, or the honest conclusion is "pooling plus asset identity" / "linear graphs suffice".**

**Architecture:**
- `GNNHARVolModel` (`models/gnnhar.py`): per date, dense `W = O^{-1/2} A O^{-1/2}` (zero diagonal — the graph channel models *only* spillovers; own dynamics stay linear, per Zhang et al. footnote 8). `H^{(l+1)} = ReLU(W H^{(l)} Θ^{(l)})`, `H^{(0)} = X`. Readout `ŷ = α + X β + H^{(L)} γ` with per-asset intercept `α ∈ R^N`, pooled `β ∈ R^F`, `γ ∈ R^D`. Hidden dim **9** (the paper's tuned value), `n_layers ∈ {1,2,3}` (default 1), Adam, temporal val split + early stopping, QLIKE loss in log-RV space, **`n_seeds` ensemble** (predictions averaged over seed-varied fits — the paper's protocol). Dense matmul, pure torch — at N ≤ 34 PyG buys nothing here.
- `STIDVolModel` (`models/stid.py`): `ŷ_i = MLP([x_i ‖ e_i])` with a learned `nn.Embedding(N, embed_dim)`; consumes the same graph dicts but **ignores edges entirely** — so it runs through the identical Plan-02 harness, folds, and features. Optional day-of-week embedding.

**Tech stack:** torch only (no torch-geometric import in either model). No new dependencies.

**Research grounding (calibrate expectations):**
- GNNHAR1L_Q vs rolling HAR (27 DJIA): **0.867 MSE / 0.961 QLIKE at h=1; 0.855 / 0.913 at h=5; gains gone at h=22** (Table 1). 1L and 2L retained in the 5% MCS at h=1.
- Depth is dead weight: 2L vs 1L DM-significant for 1 of 27 stocks; 3L degrades outright (over-smoothing; MSE ratio 1.210). Default `n_layers: 1`; 2L only as an experiment arm.
- Loss lever: QLIKE-trained beats MSE-trained on QLIKE at all horizons — but costs 30–50% MSE at h=22. We train QLIKE everywhere (QLIKE is the project's primary metric at every horizon); note the MSE caveat in the trial hypothesis.
- STID deflation: identity embeddings + MLP beat DCRNN/GraphWaveNet/MTGNN on standard benchmarks at 5–20× less cost. "The graph must beat the embedding."
- Parameter budget: "thousands of parameters, not millions" — hidden 9, F=3 HAR features → GNNHAR1L ≈ N + 3 + 9 + 3·9 ≈ 70 parameters.

## Global constraints

As 00-overview §4.1. Plan-specific:
- No self-loops in the propagation matrix (unit-tested: diagonal of W is zero even if the snapshot contains them).
- Same-seed determinism: two fits with identical seeds produce identical predictions (unit-tested).
- Both models implement the exact Plan-02/03 graph-dict `fit/predict` contract, `get_params`, torch-payload `save/load` (lstm.py pattern), `summary`.

## File map

| Action | Path | Responsibility |
|---|---|---|
| Create | `src/volforecast/models/gnnhar.py` | `GNNHARVolModel` (+ `_GNNHARModule`) |
| Create | `src/volforecast/models/stid.py` | `STIDVolModel` (+ `_STIDModule`) |
| Modify | `src/volforecast/registry.py` | imports in `ensure_registered()` |
| Create | `src/tests/unit/test_gnnhar.py`, `src/tests/unit/test_stid.py` | unit tests |
| Create | `workspace/configs/trial_082_gnnhar_vs_ghar_stid.yaml` | the neural gate experiment |

## Interfaces

- **Consumes:** graph-dict contract; `MODEL_REGISTRY`; trial_080's winning graph method (placeholder `glasso` in configs — orchestrator substitutes the recorded winner from trials.yaml).
- **Produces:**
  - `GNNHARVolModel` — `@register_model("gnnhar")`, `requires_graph = True`, `family = "gnn"`, `__init__(*, input_dim, hidden_dim=9, n_layers=1, learning_rate=1e-3, weight_decay=1e-4, max_epochs=300, early_stopping_rounds=25, val_fraction=0.15, loss="qlike", n_seeds=3, device="auto", precision="auto", seed=42)`, `fit(graphs, y=None, *, on_progress=None)`, `predict(graphs)`, `extract_features(graphs, outputs=["prediction"])` (Plan 09 adds `"embedding"`), `save/load`, `get_params`, `summary`.
  - `STIDVolModel` — `@register_model("stid")`, same contract, `__init__(*, input_dim, n_nodes: int | None = None, embed_dim=16, hidden_dim=64, dow_embed=False, ...same training kwargs..., seed=42)` (`n_nodes` inferred from the first graph when None).

---

## Task 1: `GNNHARVolModel`

**Files:** Create `src/volforecast/models/gnnhar.py`, `src/tests/unit/test_gnnhar.py`. Modify `src/volforecast/registry.py`.

**Copilot context packet:**

```yaml
subtask_id: "gnn-04-1"
goal: "Implement GNNHARVolModel: dense no-self-loop GCN propagation + linear HAR channel readout, QLIKE/MSE losses, temporal-val early stopping, n_seeds ensembling, torch save/load; registered as 'gnnhar' with failing-first tests."
file_scope:
  - workspace/plans/gnn/plan-04-gnnhar-stid.md          # Task 1: math + module code + tests
  - src/volforecast/models/gnn.py                        # training-loop conventions to mirror (losses, device, precision, early stop)
  - src/volforecast/models/ghar.py                       # _dense_w to reuse (import it)
  - src/volforecast/models/_base.py
write_scope:
  - src/volforecast/models/gnnhar.py
  - src/volforecast/registry.py
  - src/tests/unit/test_gnnhar.py
acceptance_criteria:
  - "./vol test -k test_gnnhar -> all pass (mark training tests slow if >2s and verify via ./vol test-all -k test_gnnhar)"
  - "Empty-graph fit: graph channel output is exactly 0; model reduces to QLIKE-trained pooled HAR"
  - "Same seed -> bit-identical predictions across two fits; different seeds -> different, and n_seeds=3 predictions == mean of the three single-seed fits"
  - "W diagonal is zero even when input edges contain self-loops"
constraints: ["TDD failing-first", "Pure torch (no torch_geometric import)", "Reuse _qlike_loss/_mse_loss/_resolve_device/_resolve_precision from models/gnn.py by import, do not copy", "hidden_dim default 9 (paper's tuned value)"]
context_summary: |
  GNNHAR (Zhang et al. 2025 eqs. 7-8): H^{l+1} = ReLU(O^-1/2 A O^-1/2 H^l Theta^l), H^0 = X,
  A with ZERO diagonal (spillover-only channel); readout y = alpha + X beta + H^L gamma with
  per-asset alpha, pooled beta/gamma. Paper protocol: Adam, early stopping, hidden dim 9,
  predictions averaged over several random seeds. Our graphs arrive as Plan-02 dicts; W is built
  dense per date (N<=34 so dense matmul beats sparse ops). Nesting: empty graph -> W=0 ->
  H=ReLU(0)=0 -> y = alpha + X beta, i.e. a QLIKE-trained pooled HAR (HAR_Q in the paper).
depends_on: []
```

- [ ] **Step 1: Failing tests** — `src/tests/unit/test_gnnhar.py` (key cases; first move the `_mk_graph` helper and the `identity_graphs`/`spillover_graphs` fixtures out of `test_ghar.py` into `src/tests/unit/conftest.py` so this file, `test_ghar.py`, `test_stid.py`, and the Plan 05–07 test files all consume the same fixtures — update `test_ghar.py` imports in the same commit):

```python
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

from volforecast.models.gnnhar import GNNHARVolModel, _build_w_batch


def _fast_params(**over):
    p = dict(input_dim=1, hidden_dim=4, max_epochs=30, early_stopping_rounds=30,
             n_seeds=1, device="cpu", learning_rate=0.03, val_fraction=0.2, seed=42)
    p.update(over)
    return p


def test_w_has_zero_diagonal_even_with_self_loops():
    ei = torch.tensor([[0, 1, 0], [1, 0, 0]], dtype=torch.long)  # includes (0,0)
    ea = torch.ones(3)
    w = _build_w_batch([{"edge_index": ei, "edge_attr": ea}], n=2)[0]
    assert w[0, 0] == 0.0 and w[1, 1] == 0.0
    assert w[0, 1] > 0


def test_empty_graph_nests_qlike_har(identity_graphs):
    m = GNNHARVolModel(**_fast_params(input_dim=2)).fit(identity_graphs)
    g0 = identity_graphs[0]
    # graph channel contribution must be exactly zero on empty graphs
    contrib = m._graph_channel(identity_graphs[:1])
    np.testing.assert_allclose(contrib, 0.0, atol=1e-12)
    assert np.isfinite(m.predict([g0])).all()


def test_seed_determinism_and_ensemble_mean(spillover_graphs):
    p1 = GNNHARVolModel(**_fast_params()).fit(spillover_graphs).predict(spillover_graphs[:5])
    p2 = GNNHARVolModel(**_fast_params()).fit(spillover_graphs).predict(spillover_graphs[:5])
    np.testing.assert_allclose(p1, p2)                       # same seed, bit-identical
    singles = [
        GNNHARVolModel(**_fast_params(seed=s)).fit(spillover_graphs).predict(spillover_graphs[:5])
        for s in (42, 43, 44)
    ]
    ens = GNNHARVolModel(**_fast_params(n_seeds=3)).fit(spillover_graphs).predict(spillover_graphs[:5])
    np.testing.assert_allclose(ens, np.mean(singles, axis=0), atol=1e-6)


@pytest.mark.slow
def test_learns_planted_spillover_better_than_own_only(spillover_graphs):
    """QLIKE on data with true neighbor effect: gnnhar(graph) < gnnhar(empty graph)."""
    from volforecast.models.gnn import _qlike_loss

    train, test = spillover_graphs[:160], spillover_graphs[160:]
    with_g = GNNHARVolModel(**_fast_params(max_epochs=150)).fit(train)
    empty = [dict(g, edge_index=torch.zeros(2, 0, dtype=torch.long),
                  edge_attr=torch.zeros(0)) for g in train]
    empty_test = [dict(g, edge_index=torch.zeros(2, 0, dtype=torch.long),
                       edge_attr=torch.zeros(0)) for g in test]
    no_g = GNNHARVolModel(**_fast_params(max_epochs=150)).fit(empty)
    y = np.concatenate([g["y"] for g in test])
    q_with = float(_qlike_loss(torch.tensor(with_g.predict(test)), torch.tensor(y)))
    q_without = float(_qlike_loss(torch.tensor(no_g.predict(empty_test)), torch.tensor(y)))
    assert q_with < q_without


def test_n_layers_two_runs_and_param_count_small(spillover_graphs):
    m = GNNHARVolModel(**_fast_params(n_layers=2)).fit(spillover_graphs[:50])
    assert m.get_arch_summary()["param_count"] < 2000


def test_save_load_roundtrip(tmp_path, spillover_graphs):
    m = GNNHARVolModel(**_fast_params()).fit(spillover_graphs[:50])
    p = m.predict(spillover_graphs[:3])
    m.save(tmp_path / "m.pt")
    m2 = GNNHARVolModel.load(tmp_path / "m.pt")
    np.testing.assert_allclose(m2.predict(spillover_graphs[:3]), p, atol=1e-6)


def test_on_progress_counts_across_seeds(spillover_graphs):
    calls: list[tuple[int, int]] = []
    GNNHARVolModel(**_fast_params(n_seeds=2, max_epochs=10)).fit(
        spillover_graphs[:40], on_progress=lambda c, t: calls.append((c, t)))
    assert calls and calls[-1][1] == 2 * 10       # total = n_seeds * max_epochs
    assert calls[-1][0] <= calls[-1][1]
```

- [ ] **Step 2:** `./vol test -k test_gnnhar` → red.
- [ ] **Step 3: Implement** — `src/volforecast/models/gnnhar.py` (core shown; training loop mirrors `gnn.py` conventions — AdamW→plain Adam per paper, temporal val split, best-state restore):

```python
"""GNNHAR: one-hop nonlinear graph HAR (Zhang, Pu, Cucuringu & Dong 2025, eqs. 7-8).

H^{l+1} = ReLU(W H^l Theta^l),  W = O^-1/2 A O^-1/2 with ZERO diagonal,  H^0 = X
y-hat   = alpha + X beta + H^L gamma      (alpha per asset; beta, gamma pooled)

The graph channel models spillovers only; own-lag dynamics stay linear (paper
footnote 8: nonlinearity in the own channel was found unhelpful). Empty graph
=> W = 0 => the model IS a QLIKE-trained pooled HAR — the nesting that lets the
Plan-04 experiment attribute gains to (a) the graph and (b) the nonlinearity.
Protocol extras from the paper: hidden dim 9, Adam + early stopping, and
prediction averaging over ``n_seeds`` seed-varied fits.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from volforecast.models._base import _BaseModel
from volforecast.models.gnn import _LOSSES, _resolve_device, _resolve_precision
from volforecast.registry import register_model


def _build_w_batch(graphs: list[dict[str, Any]], n: int) -> torch.Tensor:
    """(T, N, N) stack of sym-normalized, zero-diagonal dense propagation matrices."""
    ws = torch.zeros(len(graphs), n, n)
    for t, g in enumerate(graphs):
        ei, ea = g["edge_index"], g["edge_attr"]
        if ei.numel() == 0:
            continue
        a = torch.zeros(n, n)
        a[ei[0], ei[1]] = ea.float()
        a.fill_diagonal_(0.0)                       # spillover-only channel
        deg = a.sum(1)
        inv_sqrt = torch.where(deg > 0, deg.rsqrt(), torch.zeros(()))
        ws[t] = inv_sqrt[:, None] * a * inv_sqrt[None, :]
    return ws


class _GNNHARModule(nn.Module):
    def __init__(self, n_nodes: int, input_dim: int, hidden_dim: int, n_layers: int) -> None:
        super().__init__()
        dims = [input_dim] + [hidden_dim] * n_layers
        self.thetas = nn.ModuleList(
            nn.Linear(dims[k], dims[k + 1], bias=False) for k in range(n_layers)
        )
        self.alpha = nn.Parameter(torch.zeros(n_nodes))
        self.beta = nn.Linear(input_dim, 1, bias=False)
        self.gamma = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, x: torch.Tensor, w: torch.Tensor) -> torch.Tensor:
        # x: (T, N, F); w: (T, N, N)
        h = x
        for theta in self.thetas:
            h = torch.relu(torch.bmm(w, theta(h)))
        return self.alpha[None, :] + self.beta(x).squeeze(-1) + self.gamma(h).squeeze(-1)


@register_model("gnnhar")
class GNNHARVolModel(_BaseModel):
    REQUIRED_LAYERS: list[str] = ["har_core"]
    requires_sequences = False
    requires_graph = True
    supports_tuning = False           # Plan 08 flips this with gnn_tuning.py
    family = "gnn"
    description = "GNNHAR: no-self-loop GCN spillover channel + linear HAR channel"

    def __init__(self, *, input_dim: int, hidden_dim: int = 9, n_layers: int = 1,
                 learning_rate: float = 1e-3, weight_decay: float = 1e-4,
                 max_epochs: int = 300, early_stopping_rounds: int = 25,
                 val_fraction: float = 0.15, loss: str = "qlike", n_seeds: int = 3,
                 device: str = "auto", precision: str = "auto", seed: int = 42) -> None:
        ...  # store all kwargs (gnn.py style); self._modules_: list[_GNNHARModule] = []

    def fit(self, graphs, y=None, *, on_progress=None) -> "GNNHARVolModel":
        # 1. n = graphs[0]["x"].shape[0]; stack X (T,N,F) float32, Y (T,N), mask finite
        # 2. W = _build_w_batch(graphs, n); move X/Y/W to device once
        # 3. temporal split: last ceil(T*val_fraction) dates = validation
        # 4. for s in range(n_seeds):
        #        torch.manual_seed(self.seed + s); np.random.seed(self.seed + s)
        #        module = _GNNHARModule(...).to(device)
        #        opt = torch.optim.Adam(module.parameters(), lr, weight_decay)  # plain Adam per paper
        #        full-batch epochs: pred = module(X_tr, W_tr); loss = _LOSSES[self.loss](pred[m], Y_tr[m])
        #        early stopping on val loss (patience early_stopping_rounds), best-state restore
        #        on_progress(global_epoch, n_seeds * max_epochs) per epoch (global counter)
        #        self._modules_.append(module)
        # 5. record epochs_run_, best_val_loss_ (mean over seeds)
        ...

    def _graph_channel(self, graphs) -> np.ndarray:
        """Gamma-channel output only — zero on empty graphs (tested)."""
        ...

    def predict(self, graphs) -> np.ndarray:
        # mean over seed modules of module(X, W), flattened node-major (T*N,)
        ...

    def extract_features(self, graphs, *, outputs=None) -> dict[str, np.ndarray]:
        # "prediction" only in this plan; Plan 09 adds "embedding" (= final H^L, mean over seeds)
        ...

    # save/load: torch payload {schema_version: 1, init_kwargs, state_dicts: [..n_seeds..]}
    # get_params / summary / get_arch_summary: gnn.py style (+ n_seeds, param_count)
```

The subagent fills the elided bodies following `gnn.py`'s fit loop verbatim conventions (autocast via `_resolve_precision`, grad-clip 1.0, best-state dict on CPU). Register `import volforecast.models.gnnhar` in `ensure_registered()` **inside the same try/except as gnn** is NOT needed (pure torch) — import unconditionally after `lstm`.

- [ ] **Step 4:** `./vol test -k test_gnnhar` then `./vol test-all -k test_gnnhar` → green.
- [ ] **Step 5: Commit** — `feat(models): GNNHAR one-hop spillover GNN with seed ensembling`

---

## Task 2: `STIDVolModel` — the deflation control

**Files:** Create `src/volforecast/models/stid.py`, `src/tests/unit/test_stid.py`. Modify `src/volforecast/registry.py`.

**Copilot context packet:**

```yaml
subtask_id: "gnn-04-2"
goal: "Implement STIDVolModel (per-node identity embedding + MLP on node features; edges ignored) registered as 'stid', with tests proving it learns per-node effects and is graph-invariant."
file_scope:
  - workspace/plans/gnn/plan-04-gnnhar-stid.md          # Task 2 section
  - src/volforecast/models/gnnhar.py                    # training-loop pattern to mirror
  - src/volforecast/models/gnn.py                       # shared helpers
write_scope:
  - src/volforecast/models/stid.py
  - src/volforecast/registry.py
  - src/tests/unit/test_stid.py
acceptance_criteria:
  - "./vol test -k test_stid -> all pass"
  - "Graph-invariance: predictions identical (atol 1e-12) when all edges are deleted from the input graphs"
  - "Planted per-node bias is recovered: node-mean predictions ordered like the true node means"
constraints: ["TDD failing-first", "Pure torch", "Reuse _LOSSES/_resolve_device/_resolve_precision from gnn.py", "requires_graph = True (deliberately - identical harness/folds as the GNNs; document this in the class docstring)"]
context_summary: |
  STID (Shao et al. 2022) is the mandatory deflation control from the skeptic's checklist:
  a per-node learned identity vector + MLP matches spatio-temporal GNNs on standard benchmarks.
  If STID matches GNNHAR on our data, the honest conclusion is 'pooling + asset identity', not
  'spillovers'. Architecture: concat(x_i, embed[i]) -> MLP(hidden_dim, ReLU, dropout) -> scalar;
  optional day-of-week embedding from the graph dict's date. Ignores edge_index/edge_attr by
  construction — assert that in a test.
depends_on: ["gnn-04-1"]
```

- [ ] **Step 1: Failing tests** — `src/tests/unit/test_stid.py`:

```python
from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from volforecast.models.stid import STIDVolModel


def _fast(**over):
    p = dict(input_dim=1, embed_dim=4, hidden_dim=16, max_epochs=60,
             early_stopping_rounds=60, device="cpu", learning_rate=0.05, seed=42)
    p.update(over)
    return p


def test_graph_invariance(spillover_graphs):
    m = STIDVolModel(**_fast()).fit(spillover_graphs)
    stripped = [dict(g, edge_index=torch.zeros(2, 0, dtype=torch.long),
                     edge_attr=torch.zeros(0)) for g in spillover_graphs[:5]]
    np.testing.assert_allclose(
        m.predict(spillover_graphs[:5]), m.predict(stripped), atol=1e-12
    )


def test_learns_per_node_bias(identity_graphs):
    """identity_graphs plant alphas (-1, 0, 1): node-mean preds must be ordered."""
    m = STIDVolModel(**_fast(input_dim=2)).fit(identity_graphs)
    preds = m.predict(identity_graphs).reshape(len(identity_graphs), 3)
    means = preds.mean(axis=0)
    assert means[0] < means[1] < means[2]


def test_seed_determinism(identity_graphs):
    a = STIDVolModel(**_fast(input_dim=2)).fit(identity_graphs).predict(identity_graphs[:3])
    b = STIDVolModel(**_fast(input_dim=2)).fit(identity_graphs).predict(identity_graphs[:3])
    np.testing.assert_allclose(a, b)


def test_registered_and_contract():
    from volforecast.registry import MODEL_REGISTRY, ensure_registered

    ensure_registered()
    cls = MODEL_REGISTRY["stid"]
    assert cls.requires_graph is True and cls.family == "gnn"
```

- [ ] **Step 2:** red. **Step 3: Implement** `models/stid.py` — module:

```python
class _STIDModule(nn.Module):
    def __init__(self, n_nodes, input_dim, embed_dim, hidden_dim, dropout=0.1, dow_embed=False):
        super().__init__()
        self.node_embed = nn.Embedding(n_nodes, embed_dim)
        self.dow_embed = nn.Embedding(5, embed_dim) if dow_embed else None
        in_dim = input_dim + embed_dim + (embed_dim if dow_embed else 0)
        self.mlp = nn.Sequential(
            nn.Linear(in_dim, hidden_dim), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x, node_ids, dow=None):          # x: (T, N, F)
        e = self.node_embed(node_ids).expand(x.shape[0], -1, -1)
        parts = [x, e]
        if self.dow_embed is not None and dow is not None:
            parts.append(self.dow_embed(dow)[:, None, :].expand(-1, x.shape[1], -1))
        return self.mlp(torch.cat(parts, dim=-1)).squeeze(-1)
```

`STIDVolModel` wraps it with the same fit/predict/save/load skeleton as `gnnhar` (single seed by default, `n_seeds=1`), never touching `edge_index`/`edge_attr`. Register in `ensure_registered()`.

- [ ] **Step 4:** green. **Step 5: Commit** — `feat(models): STID identity-embedding deflation control`

---

## Task 3: The neural gate experiment

**Files:** Create `workspace/configs/trial_082_gnnhar_vs_ghar_stid.yaml`. Modify `workspace/research/trials.yaml`.

**Copilot context packet:**

```yaml
subtask_id: "gnn-04-3"
goal: "Create trial_082: one tournament racing har / ghar(best graph) / gnnhar_1l / gnnhar_2l / stid at h=1/5/22 under QLIKE, register it with hypothesis + gates; substitute the trial_080 winning graph method from trials.yaml."
file_scope:
  - workspace/plans/gnn/plan-04-gnnhar-stid.md          # Task 3: YAML inline
  - workspace/configs/trial_080_ghar_graph_ablation.yaml
  - workspace/research/trials.yaml                       # read trial-080 verdict for the winning graph
write_scope:
  - workspace/configs/trial_082_gnnhar_vs_ghar_stid.yaml
  - workspace/research/trials.yaml
acceptance_criteria:
  - "Config parses via ExperimentConfig.from_yaml"
  - "graph.method equals the trial-080 recorded winner (fallback glasso with a TODO comment if 080 hasn't run)"
  - "trials.yaml trial-082 NOT_STARTED with the two-gate criterion spelled out"
constraints: ["Do NOT run vol run", "Non-code task: config parse evidence required"]
context_summary: |
  The two-gate experiment: (1) gnnhar_1l beats ghar under DM at h<=5 -> nonlinearity earns its
  keep; (2) gnnhar_1l beats stid -> the GRAPH earns its keep beyond asset identity. Expected
  honest outcome: ~2% incremental QLIKE over GHAR at h=1, ~4-8% total over HAR at h=1/5, nothing
  at h=22. gnnhar_2l is included ONLY to reproduce the depth null (expect no DM significance).
depends_on: ["gnn-04-1", "gnn-04-2"]
```

- [ ] **Step 1: Create** `workspace/configs/trial_082_gnnhar_vs_ghar_stid.yaml`:

```yaml
# Trial-082: GNNHAR vs GHAR vs STID — the neural gate.
# Gate 1 (nonlinearity): gnnhar_1l < ghar, DM p<0.05 at h=1 or h=5.
# Gate 2 (graph vs identity-embedding): gnnhar_1l < stid, DM p<0.05.
# Depth null replication: gnnhar_2l expected NOT to beat gnnhar_1l (DM n.s.).
# COVID: included, expanding window.

name: trial_082_gnnhar_vs_ghar_stid
n_gpus: 8

universe: [SPY, AAPL, MSFT, NVDA, AVGO, GOOGL, AMZN, V, MA, XOM, PG,
           JNJ, HD, NFLX, TSLA, CRM, UNH, BAC, ADBE, IWM, DIA]
date_range: ["2015-01-02", "2026-05-30"]
horizons: [1, 5, 22]
feature_layers: [har_core]

model: {name: gnnhar, params: {}}

graph:                       # <- SUBSTITUTE trial_080 winner (placeholder: glasso)
  method: glasso
  input: returns
  window: 1000
  refit_every: 21
  min_history: 252
  node_features: [log_rv_d, log_rv_w, log_rv_m]
  params: {}

cv: {method: expanding_window, purge_gap: 10, train_size: 504, test_size: 126}

tournament:
  models: [har, ghar, stid, gnnhar_1l, gnnhar_2l]
  baseline: har
  mcs_bootstrap: 10000
  parallel_models: 1          # GPU models run sequentially, each owning the 8 GPUs
  model_configs:
    gnnhar_1l:
      name: gnnhar
      params: {hidden_dim: 9, n_layers: 1, loss: qlike, n_seeds: 5, max_epochs: 300,
               early_stopping_rounds: 25, learning_rate: 0.001, device: auto, seed: 42}
    gnnhar_2l:
      name: gnnhar
      params: {hidden_dim: 9, n_layers: 2, loss: qlike, n_seeds: 5, max_epochs: 300,
               early_stopping_rounds: 25, learning_rate: 0.001, device: auto, seed: 42}
    stid:
      name: stid
      params: {embed_dim: 16, hidden_dim: 64, loss: qlike, max_epochs: 300,
               early_stopping_rounds: 25, device: auto, seed: 42}

training_mode: pooled
seed: 42
output_dir: data/models/trial_082_gnnhar_vs_ghar_stid
```

- [ ] **Step 2:** Parse-check; register `trial-082` (baseline_config: trial_080; hypothesis + both gates + depth-null expectation). Print launch command. **Commit** — `chore(config): trial_082 GNNHAR/GHAR/STID gate tournament`

## 7. Orchestrator prompt

```
/execute Implement Plan 04 (GNNHAR + STID) from workspace/plans/gnn/plan-04-gnnhar-stid.md

Precondition: Plans 01-03 merged (./vol test -k "test_ghar or test_runner_graphs" green).
Check workspace/research/trials.yaml for trial-080's verdict: if FAIL, execute Task 1 only
(replication arm) and stop with a note. Otherwise run gnn-04-1 -> gnn-04-2 -> gnn-04-3
(1 and 2 may overlap after gnn-04-1's fixtures module lands; max 2 subagents).
TDD red->green evidence per task; ./vol only; return contracts per 00-overview §4.2.
Integration: ./vol test-all, lint, typecheck; weekly-progress entry.
Print the trial_082 launch command; do NOT run. Do NOT start Plan 05.
```

## 8. Acceptance gate → Plans 05–07

- Tests green; `gnnhar`/`stid` registered; empty-graph nesting + graph-invariance proven.
- **Science gates (user runs trial_082):** record PASS/FAIL of Gate 1 (vs GHAR) and Gate 2 (vs STID) in trials.yaml. Both PASS → Plans 05–07 proceed as designed. Gate 2 FAIL (STID matches) → frontier plans run as *replication* arms only; the internal finding is written up in Plan 10. Either way, Plan 08 (GPU infra) proceeds — it accelerates whatever survives.
