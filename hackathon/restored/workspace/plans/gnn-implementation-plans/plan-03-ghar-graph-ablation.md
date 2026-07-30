# Plan 03 — GHAR + the Graph Ablation (the gate experiment)

> **For the Copilot orchestrator:** execute with `/execute` using the Orchestrator prompt in §7. TDD hard gate. Requires Plans 01–02 merged. This plan ends with a **decision gate** that determines how much of Plans 04–07 is worth running.

**Goal:** Implement GHAR — the linear graph-HAR of Zhang, Pu, Cucuringu & Dong (2025, eq. 6) — as a registered `requires_graph` model, add per-label graph overrides to the tournament so one experiment compares four adjacencies on identical observations, and ship the ablation experiment the chapter calls "the single best experiment": GHAR × {identity, full, glasso, dy} vs rolling HAR at h ∈ {1, 5, 22} under QLIKE + panel-DM + MCS.

**Architecture:** `GHARVolModel` is pooled OLS on the design row `[asset one-hot α | own HAR features x_i | neighbor aggregate (W x)_i]` per (date, node), where `W = O^{-1/2} A O^{-1/2}` (undirected) or `D^{-1} A` (directed DY). It consumes the same graph-dict lists as `gnn` (Plan 02 path) — zero runner changes. `A = 0` (identity graph) makes the γ block vanish: GHAR nests pooled HAR exactly, so the ablation isolates *the graph* and nothing else.

**Tech stack:** numpy `lstsq` — **no torch needed** (GraphSnapshot is numpy-first by Plan-01 design; graph dicts carry torch edge tensors, converted with `.numpy()`).

**Research grounding (expected results — calibrate!):**
- GHAR vs HAR on 27 DJIA stocks: MSE ratio 0.927, QLIKE ratio 0.983 at h=1 — the graph term alone earns **~1–2% QLIKE**, roughly half the total GNN gain (Zhang et al. 2025, Table 1). Six pooled slopes regardless of N; "estimable by OLS in milliseconds".
- Graph contest priors: GLASSO won on 27 single names; fully-connected won on 10 indices (GNAR-HARX, QLIKE FC −8.5891 vs GLASSO "consistently rank lower"); DY-weighted graphs beat binary Granger at long horizons (Boetti & Nunes 2026). **No published study runs this ablation on a mid-sized cross-asset universe — this experiment is publishable-internally either way.**
- Our repo trains in **log-RV space** (hard constraint) with the standard Corsi overlapping d/w/m features, so GHAR here is the log-space analogue of the paper's level-space model; the nesting logic (HAR ⊂ GHAR) is preserved because both channels use the same features. Note this deviation in the trial hypothesis.

**The gate (from the chapter's Project Blueprint, Step 1):**
> Does the best graph beat identity, DM-significant at 5%, at h=1 or h=5?
> **NO** → ship the spillover features (the `W x` columns are three extra HAR regressors), record the null in trials.yaml, and demote Plans 04–07 to "run only the GNNHAR replication for the writeup". A null here is a legitimate, reportable outcome.
> **YES** → the winning graph method becomes the default `graph:` block for Plans 04–07.

## Global constraints

As 00-overview §4.1. Plan-specific:
- GHAR must be exactly nested: with `method: identity`, predictions must match pooled OLS-HAR on the same design (unit-tested to 1e-8).
- OLS via `np.linalg.lstsq` (min-norm solution keeps γ = 0 when the graph is empty — do not add ridge here; regularized variants are a later experiment).
- All ablation arms score on **identical observations** — this is why per-label graph overrides in one tournament matter (index intersection is already enforced by `tournament.py`).

## File map

| Action | Path | Responsibility |
|---|---|---|
| Create | `src/volforecast/models/ghar.py` | `GHARVolModel` |
| Modify | `src/volforecast/registry.py` | import in `ensure_registered()` |
| Modify | `src/volforecast/evaluation/_parallel.py` | per-label `graph` override in `build_tournament_model_config` |
| Modify | `workspace/configs/_CANONICAL_EXAMPLE.yaml` | document `tournament.model_configs.<label>.graph` |
| Create | `src/tests/unit/test_ghar.py` | model unit tests |
| Create | `src/tests/unit/test_tournament_graph_override.py` | override plumbing tests |
| Create | `workspace/configs/trial_080_ghar_graph_ablation.yaml` | the gate experiment |
| Create | `workspace/configs/trial_081_ghar_factor_residual.yaml` | follow-up arm (optional run) |

## Interfaces

- **Consumes:** graph-dict contract (`{"x", "edge_index", "edge_attr", "y", "date"}`), Plan-02 native path, `MODEL_REGISTRY`.
- **Produces:** `GHARVolModel` — `@register_model("ghar")`, `requires_graph = True`, `family = "gnn"`, `__init__(*, input_dim: int, w_norm: str = "sym", seed: int = 42)`, `fit(graphs, y=None, *, on_progress=None)`, `predict(graphs) -> np.ndarray` (node-major flatten), `get_params()`, `summary` (dict: `alpha_mean`, `beta_<feature>`, `gamma_<feature>`), `coef_beta_ (F,)`, `coef_gamma_ (F,)`, `intercepts_ (N,)`.
- **Produces:** tournament `model_configs.<label>.graph` override (dict merged into the per-model synthetic `ExperimentConfig.graph`).

---

## Task 1: `GHARVolModel`

**Files:** Create `src/volforecast/models/ghar.py`, `src/tests/unit/test_ghar.py`. Modify `src/volforecast/registry.py`.

**Copilot context packet:**

```yaml
subtask_id: "gnn-03-1"
goal: "Implement GHARVolModel (pooled OLS with per-asset intercepts, own-feature betas, and graph-neighbor gammas; sym/row W normalization) registered as 'ghar', with nesting, recovery, and flatten-order tests."
file_scope:
  - workspace/plans/gnn/plan-03-ghar-graph-ablation.md   # Task 1 section: math + full code
  - src/volforecast/models/_base.py
  - src/volforecast/models/gnn.py                        # graph-dict contract + flags pattern
  - src/volforecast/registry.py
write_scope:
  - src/volforecast/models/ghar.py
  - src/volforecast/registry.py
  - src/tests/unit/test_ghar.py
acceptance_criteria:
  - "./vol test -k test_ghar -> all pass"
  - "GHAR(identity graphs) predictions match direct lstsq on [one-hot | x] to atol 1e-8"
  - "On planted-spillover data, fitted gamma within 0.05 of the true coefficient"
  - "test_protocols.py and test_registry.py still green (contract auto-covers the new class)"
constraints: ["TDD failing-first", "No torch import at module level (call .numpy() on edge tensors inside fit/predict)", "np.linalg.lstsq with rcond=None", "Rows with non-finite y excluded from the fit; predict outputs for ALL nodes"]
context_summary: |
  GHAR (Zhang et al. 2025 eq. 6): RV_t = alpha + V beta + W V gamma + u, W = O^-1/2 A O^-1/2,
  beta/gamma pooled across assets, alpha per-asset. Our version runs in log-RV space on the
  node-feature matrix x from the Plan-02 graph dicts (F features, default 9 -> for the ablation
  configs we restrict node_features to [log_rv_d, log_rv_w, log_rv_m]). Design row for node i at
  date t: [e_i | x_i | (W_t x_t)_i] with W_t built dense from edge_index/edge_attr per graph.
  Directed graphs (dy) use row normalization D^-1 A instead of symmetric.
depends_on: []
```

- [ ] **Step 1: Failing tests** — `src/tests/unit/test_ghar.py`:

```python
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

from volforecast.models.ghar import GHARVolModel


def _mk_graph(x, y, edges, weights, date):
    return {
        "x": np.asarray(x, dtype=np.float32),
        "edge_index": torch.tensor(edges, dtype=torch.long).reshape(2, -1),
        "edge_attr": torch.tensor(weights, dtype=torch.float32),
        "y": np.asarray(y, dtype=np.float64),
        "date": date,
    }


@pytest.fixture
def identity_graphs():
    """60 dates x 3 nodes, no edges; y = alpha_i + 0.6*x0 + 0.2*x1 + eps."""
    rng = np.random.default_rng(42)
    alphas = np.array([-1.0, 0.0, 1.0])
    graphs = []
    for t in range(60):
        x = rng.normal(size=(3, 2))
        y = alphas + 0.6 * x[:, 0] + 0.2 * x[:, 1] + rng.normal(0, 0.01, 3)
        graphs.append(_mk_graph(x, y, [[], []], [], pd.Timestamp("2024-01-01") + pd.Timedelta(days=t)))
    return graphs


@pytest.fixture
def spillover_graphs():
    """Ring graph; y depends on own x AND neighbor aggregate with gamma=0.3."""
    rng = np.random.default_rng(7)
    n = 4
    edges = [[0, 1, 1, 2, 2, 3, 3, 0], [1, 0, 2, 1, 3, 2, 0, 3]]
    w = [1.0] * 8
    graphs = []
    for t in range(200):
        x = rng.normal(size=(n, 1))
        a = np.zeros((n, n))
        a[edges[0], edges[1]] = 1.0
        deg = a.sum(1)
        wn = (a / np.sqrt(deg)[:, None]) / np.sqrt(deg)[None, :]
        y = 0.5 * x[:, 0] + 0.3 * (wn @ x)[:, 0] + rng.normal(0, 0.01, n)
        graphs.append(_mk_graph(x, y, edges, w, pd.Timestamp("2024-01-01") + pd.Timedelta(days=t)))
    return graphs


def test_identity_nests_pooled_har(identity_graphs):
    m = GHARVolModel(input_dim=2).fit(identity_graphs)
    # direct pooled OLS on [one-hot | x] (gamma block absent)
    rows, ys = [], []
    for g in identity_graphs:
        for i in range(3):
            onehot = np.eye(3)[i]
            rows.append(np.concatenate([onehot, g["x"][i]]))
            ys.append(g["y"][i])
    beta_direct, *_ = np.linalg.lstsq(np.array(rows), np.array(ys), rcond=None)
    preds = m.predict(identity_graphs[:5])
    direct = np.array(rows[:15]) @ beta_direct
    np.testing.assert_allclose(preds, direct, atol=1e-8)
    np.testing.assert_allclose(m.coef_gamma_, 0.0, atol=1e-8)  # min-norm: empty graph -> gamma 0


def test_recovers_planted_spillover(spillover_graphs):
    m = GHARVolModel(input_dim=1).fit(spillover_graphs)
    assert m.coef_beta_[0] == pytest.approx(0.5, abs=0.05)
    assert m.coef_gamma_[0] == pytest.approx(0.3, abs=0.05)


def test_predict_is_node_major_flatten(identity_graphs):
    m = GHARVolModel(input_dim=2).fit(identity_graphs)
    preds = m.predict(identity_graphs[:2])
    assert preds.shape == (6,)
    single = m.predict(identity_graphs[:1])
    np.testing.assert_allclose(preds[:3], single)


def test_nan_targets_excluded_from_fit(identity_graphs):
    identity_graphs[0]["y"][1] = np.nan
    m = GHARVolModel(input_dim=2).fit(identity_graphs)
    assert np.isfinite(m.predict(identity_graphs[:1])).all()  # still predicts all nodes


def test_row_norm_for_directed(spillover_graphs):
    m = GHARVolModel(input_dim=1, w_norm="row").fit(spillover_graphs)
    assert np.isfinite(m.coef_gamma_).all()


def test_summary_names(identity_graphs):
    m = GHARVolModel(input_dim=2).fit(identity_graphs)
    s = m.summary
    assert {"alpha_mean", "beta_f0", "beta_f1", "gamma_f0", "gamma_f1"} <= set(s)


def test_registered():
    from volforecast.registry import MODEL_REGISTRY, ensure_registered

    ensure_registered()
    assert "ghar" in MODEL_REGISTRY
    assert MODEL_REGISTRY["ghar"].requires_graph is True
```

- [ ] **Step 2:** `./vol test -k test_ghar` → red.
- [ ] **Step 3: Implement** — `src/volforecast/models/ghar.py`:

```python
"""GHAR: linear graph-HAR (Zhang, Pu, Cucuringu & Dong 2025, eq. 6).

log-RV variant on the repo's pooled panel: per (date, node) design row
    [ asset one-hot alpha | own features x_i | neighbor aggregate (W x)_i ]
with W = O^-1/2 A O^-1/2 (undirected, 'sym') or D^-1 A ('row', for directed DY
graphs). beta/gamma are pooled across assets (2F slopes total); only the
intercept is asset-specific. A = 0 recovers pooled HAR exactly — the nesting
that makes the Plan-03 graph ablation attributable to the graph alone.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from volforecast.models._base import _BaseModel
from volforecast.registry import register_model


def _dense_w(edge_index, edge_attr, n: int, norm: str) -> np.ndarray:
    a = np.zeros((n, n), dtype=np.float64)
    if edge_index.numel():
        src = edge_index[0].numpy()
        dst = edge_index[1].numpy()
        a[src, dst] = edge_attr.numpy().astype(np.float64)
    deg = a.sum(axis=1)
    safe = np.where(deg > 0, deg, 1.0)
    if norm == "row":
        return a / safe[:, None]
    d_inv_sqrt = np.where(deg > 0, 1.0 / np.sqrt(safe), 0.0)
    return d_inv_sqrt[:, None] * a * d_inv_sqrt[None, :]


@register_model("ghar")
class GHARVolModel(_BaseModel):
    """Pooled-OLS graph HAR. Consumes Plan-02 graph-dict lists."""

    REQUIRED_LAYERS: list[str] = ["har_core"]
    requires_sequences = False
    requires_graph = True
    supports_tuning = False
    family = "gnn"
    description = "Linear graph HAR: pooled own + neighbor-aggregate features (OLS)"

    def __init__(self, *, input_dim: int, w_norm: str = "sym", seed: int = 42) -> None:
        if w_norm not in ("sym", "row"):
            raise ValueError(f"w_norm must be 'sym' or 'row', got {w_norm!r}")
        self.input_dim = int(input_dim)
        self.w_norm = w_norm
        self.seed = int(seed)  # unused (deterministic) — accepted for runner parity
        self.intercepts_: np.ndarray | None = None
        self.coef_beta_: np.ndarray | None = None
        self.coef_gamma_: np.ndarray | None = None
        self._n_nodes: int | None = None

    # ------------------------------------------------------------------
    def _design(self, graphs: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
        n = graphs[0]["x"].shape[0]
        f = self.input_dim
        rows, ys = [], []
        eye = np.eye(n)
        for g in graphs:
            x = np.asarray(g["x"], dtype=np.float64)[:, :f]
            w = _dense_w(g["edge_index"], g["edge_attr"], n, self.w_norm)
            wx = w @ x
            y = np.asarray(g["y"], dtype=np.float64)
            for i in range(n):
                rows.append(np.concatenate([eye[i], x[i], wx[i]]))
                ys.append(y[i])
        return np.asarray(rows), np.asarray(ys)

    def fit(
        self, graphs: list[dict[str, Any]], y: Any | None = None, *, on_progress=None
    ) -> "GHARVolModel":
        if not graphs:
            raise ValueError("GHAR: no graphs to fit")
        self._n_nodes = graphs[0]["x"].shape[0]
        design, target = self._design(graphs)
        valid = np.isfinite(target)
        coefs, *_ = np.linalg.lstsq(design[valid], target[valid], rcond=None)
        n, f = self._n_nodes, self.input_dim
        self.intercepts_ = coefs[:n]
        self.coef_beta_ = coefs[n : n + f]
        self.coef_gamma_ = coefs[n + f : n + 2 * f]
        if on_progress is not None:
            on_progress(1, 1)
        return self

    def predict(self, graphs: list[dict[str, Any]]) -> np.ndarray:
        if self.coef_beta_ is None:
            raise RuntimeError("predict called before fit")
        design, _ = self._design(graphs)
        coefs = np.concatenate([self.intercepts_, self.coef_beta_, self.coef_gamma_])
        return design @ coefs

    # ------------------------------------------------------------------
    def get_params(self) -> dict[str, Any]:
        return {"input_dim": self.input_dim, "w_norm": self.w_norm, "seed": self.seed}

    @property
    def summary(self) -> dict[str, float]:
        if self.coef_beta_ is None:
            return {}
        out: dict[str, float] = {"alpha_mean": float(np.mean(self.intercepts_))}
        for k in range(self.input_dim):
            out[f"beta_f{k}"] = float(self.coef_beta_[k])
            out[f"gamma_f{k}"] = float(self.coef_gamma_[k])
        return out
```

Add `import volforecast.models.ghar  # noqa: F401` to `ensure_registered()` (unguarded — no optional deps; note `_design` touches torch tensors only via `.numpy()`, and graph dicts always carry torch tensors per the Plan-02 contract, so keep the import inside the models list right after `gnn`'s guarded import... **if torch is genuinely absent this module still imports fine** — the tensors arrive at runtime from the graph path which requires torch anyway).

- [ ] **Step 4:** `./vol test -k "test_ghar or test_protocols or test_registry"` → green.
- [ ] **Step 5: Commit** — `feat(models): GHAR linear graph-HAR with sym/row W normalization`

---

## Task 2: Per-label graph overrides in the tournament

**Files:** Modify `src/volforecast/evaluation/_parallel.py` (and `evaluation/_model_utils.py` if label resolution lives there). Create `src/tests/unit/test_tournament_graph_override.py`. Modify `workspace/configs/_CANONICAL_EXAMPLE.yaml`.

**Copilot context packet:**

```yaml
subtask_id: "gnn-03-2"
goal: "Allow tournament.model_configs.<label> entries to carry a 'graph' dict that overrides the experiment-level graph block in that label's synthetic per-model ExperimentConfig, so one tournament can race the same model over different adjacencies."
file_scope:
  - workspace/plans/gnn/plan-03-ghar-graph-ablation.md   # Task 2 section
  - src/volforecast/evaluation/_parallel.py              # build_tournament_model_config (~line 84)
  - src/volforecast/evaluation/_model_utils.py           # resolve_model
  - src/volforecast/config.py                            # GraphConfig
  - workspace/configs/_CANONICAL_EXAMPLE.yaml
write_scope:
  - src/volforecast/evaluation/_parallel.py
  - src/volforecast/evaluation/_model_utils.py
  - src/tests/unit/test_tournament_graph_override.py
  - workspace/configs/_CANONICAL_EXAMPLE.yaml
acceptance_criteria:
  - "./vol test -k test_tournament_graph_override -> all pass"
  - "A model_configs entry {name: ghar, graph: {method: glasso}} yields a synthetic config with config.graph.method == 'glasso' while another label inherits the experiment-level graph"
  - "Entries without 'graph' behave exactly as before (characterization: existing tournament tests green)"
constraints: ["TDD failing-first", "Parse the override through GraphConfig(**dict) so method validation fires at config time", "Read build_tournament_model_config's actual signature first and follow its existing merge style"]
context_summary: |
  The graph block is experiment-level, but the Plan-03 ablation needs five tournament entries
  (har + 4 ghar variants) differing ONLY in adjacency, scored on intersected indices so the
  existing panel-DM/MCS machinery applies directly. build_tournament_model_config already builds
  a synthetic ExperimentConfig per label from model_configs[label]; extend it to pop an optional
  'graph' key and set it (via GraphConfig(**value)) on the synthetic config. This also serves
  every later plan's model-vs-graph sensitivity runs.
depends_on: []
```

- [ ] **Step 1: Failing tests** — `src/tests/unit/test_tournament_graph_override.py`:

```python
from __future__ import annotations

import pytest

from volforecast.config import ExperimentConfig, GraphConfig, ModelConfig, TournamentConfig
from volforecast.evaluation._parallel import build_tournament_model_config


def _base_config() -> ExperimentConfig:
    return ExperimentConfig(
        name="abl", universe=["A", "B"], date_range=("2020-01-01", "2021-01-01"),
        horizons=[1], feature_layers=["har_core"],
        model=ModelConfig(name="har", params={}),
        graph=GraphConfig(method="corr"),
        tournament=TournamentConfig(
            models=["ghar_glasso", "ghar_full"],
            model_configs={
                "ghar_glasso": {"name": "ghar", "params": {},
                                "graph": {"method": "glasso", "window": 1000}},
                "ghar_full": {"name": "ghar", "params": {}},
            },
        ),
    )


def test_label_graph_override_applied():
    cfg = build_tournament_model_config(_base_config(), "ghar_glasso")
    assert cfg.graph.method == "glasso"
    assert cfg.graph.window == 1000


def test_label_without_override_inherits_experiment_graph():
    cfg = build_tournament_model_config(_base_config(), "ghar_full")
    assert cfg.graph.method == "corr"


def test_invalid_override_method_raises():
    base = _base_config()
    base.tournament.model_configs["ghar_glasso"]["graph"]["method"] = "bogus"
    with pytest.raises(ValueError, match="Unknown graph method"):
        build_tournament_model_config(base, "ghar_glasso")
```

(Adjust the call signature to the real `build_tournament_model_config` after reading it — it may take `(config, label, model_params, ...)`; keep the assertions identical.)

- [ ] **Step 2:** red. **Step 3: Implement** — inside `build_tournament_model_config`, where the `model_configs[label]` dict is consumed, add:

```python
    graph_override = (model_cfg_entry or {}).get("graph")
    if graph_override is not None:
        from volforecast.config import GraphConfig

        synthetic_config.graph = (
            graph_override if isinstance(graph_override, GraphConfig)
            else GraphConfig(**graph_override)
        )
```

and make sure `resolve_model` tolerates (ignores) the `graph` key when extracting `name`/`params`. Document in `_CANONICAL_EXAMPLE.yaml` under `tournament.model_configs`:

```yaml
#   model_configs:
#     ghar_glasso:            # same model, different adjacency — per-label graph override
#       name: ghar
#       params: {}
#       graph: {method: glasso, window: 1000, refit_every: 21}
```

- [ ] **Step 4:** `./vol test -k "test_tournament_graph_override or test_tournament"` → green.
- [ ] **Step 5: Commit** — `feat(eval): per-label graph overrides in tournament model_configs`

---

## Task 3: The ablation experiment configs + trial registration

**Files:** Create `workspace/configs/trial_080_ghar_graph_ablation.yaml`, `workspace/configs/trial_081_ghar_factor_residual.yaml`. Modify `workspace/research/trials.yaml`.

**Copilot context packet:**

```yaml
subtask_id: "gnn-03-3"
goal: "Create the GHAR four-graph ablation tournament config (trial_080) and the factor-residual follow-up (trial_081), register both in trials.yaml with hypotheses, gates, and COVID statements; validate configs parse; print (not run) the launch commands."
file_scope:
  - workspace/plans/gnn/plan-03-ghar-graph-ablation.md   # Task 3 section: full YAML inline
  - workspace/configs/trial_079_gnn_native.yaml
  - workspace/research/trials.yaml
write_scope:
  - workspace/configs/trial_080_ghar_graph_ablation.yaml
  - workspace/configs/trial_081_ghar_factor_residual.yaml
  - workspace/research/trials.yaml
acceptance_criteria:
  - "Both configs parse via ExperimentConfig.from_yaml (verify with ./vol shell one-liner)"
  - "trials.yaml has trial-080/trial-081 NOT_STARTED entries with hypothesis, baseline_config, COVID note, and the explicit gate criterion"
constraints: ["Do NOT run vol run", "Take the next free trial numbers from ./vol experiments if 080/081 are taken", "Non-code task: TDD exempt, but config parse check is mandatory evidence"]
context_summary: |
  This is the chapter's Step-1 gate experiment: GHAR over identity/full/glasso/dy adjacencies
  vs rolling pooled HAR, h in {1,5,22}, QLIKE + panel-DM vs baseline + MCS over the arms.
  node_features restricted to the three HAR log-RV columns so GHAR is exactly the paper's shape.
  Expected: best graph earns ~1-2% QLIKE at h=1/h=5 if graphs help at all; identity arm must
  match plain har to numerical noise (built-in sanity check of the whole Plan 01-03 stack).
depends_on: ["gnn-03-1", "gnn-03-2"]
```

- [ ] **Step 1: Create** `workspace/configs/trial_080_ghar_graph_ablation.yaml`:

```yaml
# Trial-080: GHAR graph ablation — THE gate experiment for the GNN program.
#
# Hypothesis: linear neighbor-aggregate HAR terms (GHAR, Zhang et al. 2025 eq. 6) improve
# pooled rolling HAR under QLIKE at h=1/h=5, and the adjacency choice (identity vs full vs
# GLASSO vs directed DY) is the dominant design lever. Expected ~1-2% QLIKE for the best
# graph; ghar_identity must tie har (nesting sanity check).
# Gate: best arm beats ghar_identity with DM p < 0.05 -> proceed to Plan 04 (GNNHAR).
# COVID handling: included; expanding window; regime-split QLIKE reported in Plan 10 rerun.
# Deviation from paper: log-RV space + overlapping Corsi d/w/m features (repo constraints).

name: trial_080_ghar_graph_ablation
n_gpus: 1                      # GHAR is OLS; GPUs irrelevant here

universe: [SPY, AAPL, MSFT, NVDA, AVGO, GOOGL, AMZN, V, MA, XOM, PG,
           JNJ, HD, NFLX, TSLA, CRM, UNH, BAC, ADBE, IWM, DIA]

date_range: ["2015-01-02", "2026-05-30"]
horizons: [1, 5, 22]

feature_layers: [har_core]

model:
  name: ghar
  params: {}

# Experiment-level default graph (inherited by arms without overrides)
graph:
  method: glasso
  input: returns
  window: 1000                 # GNNHAR protocol: rolling 1000-day window
  refit_every: 21              # monthly re-estimation
  min_history: 252
  node_features: [log_rv_d, log_rv_w, log_rv_m]
  params: {}

cv:
  method: expanding_window
  purge_gap: 10
  train_size: 504
  test_size: 126

tournament:
  models: [har, ghar_identity, ghar_full, ghar_glasso, ghar_dy]
  baseline: har
  mcs_bootstrap: 10000
  parallel_models: 4
  dh_enabled: false
  vt_enabled: false
  model_configs:
    ghar_identity:
      name: ghar
      params: {}
      graph: {method: identity, input: returns, window: 1000, refit_every: 21,
              node_features: [log_rv_d, log_rv_w, log_rv_m]}
    ghar_full:
      name: ghar
      params: {}
      graph: {method: full, input: returns, window: 1000, refit_every: 21,
              node_features: [log_rv_d, log_rv_w, log_rv_m]}
    ghar_glasso:
      name: ghar
      params: {}
      graph: {method: glasso, input: returns, window: 1000, refit_every: 21,
              min_history: 252, node_features: [log_rv_d, log_rv_w, log_rv_m]}
    ghar_dy:
      name: ghar
      params: {w_norm: row}    # directed graph -> in-flow row normalization
      graph: {method: dy, input: log_rv, window: 252, refit_every: 21,
              node_features: [log_rv_d, log_rv_w, log_rv_m],
              params: {var_lags: 4, fevd_horizon: 10, threshold: 0.05}}

training_mode: pooled
seed: 42
output_dir: data/models/trial_080_ghar_graph_ablation
```

- [ ] **Step 2: Create** `workspace/configs/trial_081_ghar_factor_residual.yaml` — clone of trial_080 with `tournament.models: [har, ghar_glasso, ghar_factor_residual]` and:

```yaml
    ghar_factor_residual:
      name: ghar
      params: {}
      graph: {method: factor_residual, input: returns, window: 1000, refit_every: 21,
              node_features: [log_rv_d, log_rv_w, log_rv_m],
              params: {base: corr, factor: mean, threshold: 0.4}}
```

(hypothesis: idiosyncratic edges beat raw-correlation edges — Cartea et al. 2026 design idea; run only if trial_080 gates through.)

- [ ] **Step 3:** Validate both parse (`./vol shell` one-liner), register `trial-080`/`trial-081` in `workspace/research/trials.yaml` (`status: NOT_STARTED`, `baseline_config: trial_080` baseline arm `har`).
- [ ] **Step 4: Commit** — `chore(config): trial_080 GHAR graph ablation + trial_081 factor-residual arm`
- [ ] **Step 5:** Print launch commands for the user (do not run):
  `./vol run --config workspace/configs/trial_080_ghar_graph_ablation.yaml --skip-ingest`

---

## Interpreting trial_080 (orchestrator writes this into the final report)

1. `./vol compare` per arm vs `har`; read `metrics.json` → per-horizon QLIKE + `dm_pvalue` + `mcs_included`.
2. Sanity: `ghar_identity` QLIKE must equal `har` within ~1 bp (they are the same regression up to pooling details). If not — bug hunt before any interpretation (likely node-feature mismatch or Duan asymmetry).
3. Gate: best of {full, glasso, dy} vs identity, DM p < 0.05 at h=1 or h=5 → record verdict PASS in trials.yaml, set the winning method as the default `graph:` block in Plans 04–07 configs. Else verdict FAIL → record the null; the deliverable is the spillover features; Plans 04–07 shrink to the GNNHAR replication arm.
4. Diagnostics regardless of outcome: `schedule_stability` (Plan 01) on the glasso and dy schedules — report consecutive-refit Jaccard (GNAR-HARX instability check) and density time series (Wade crisis-density check) into `workspace/research/research-journal.md`.

## 7. Orchestrator prompt (paste into Copilot Chat)

```
/execute Implement Plan 03 (GHAR + graph ablation) from workspace/plans/gnn/plan-03-ghar-graph-ablation.md

Precondition: ./vol test -k "test_runner_graphs or test_graph_data" green (Plan 02 merged).
Read workspace/plans/gnn/00-overview.md §4 first.
Tasks: gnn-03-1 and gnn-03-2 in parallel (max 2 subagents), then gnn-03-3.
Each subagent: TDD red->green evidence, ./vol only, return contract per 00-overview §4.2.
Integration verification: ./vol test-all, ./vol lint, ./vol typecheck.
Weekly-progress entry (Shipped: linear graph-HAR model + the four-graph ablation experiment,
ready to run). Print the trial_080 launch command; do NOT run it. Do NOT start Plan 04.
```

## 8. Acceptance gate → Plan 04

- All tests green; `ghar` registered; per-label graph overrides work.
- **Science gate (user runs trial_080 on the GS machine):** decision recorded in trials.yaml per §"Interpreting trial_080". Plans 04–07 configs adopt the winning graph method as their default `graph:` block.
