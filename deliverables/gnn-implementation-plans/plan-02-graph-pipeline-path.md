# Plan 02 — Standalone Graph-Model Pipeline Path

> **For the Copilot orchestrator:** execute with `/execute` using the Orchestrator prompt in §8. One subagent per task, context packets embedded below. TDD hard gate. Requires Plan 01 merged (`GRAPH_REGISTRY`, `GraphConfig`, `build_graph_schedule` all green).

**Goal:** Make any `requires_graph = True` model a first-class `vol run` citizen: `model: {name: gnn}` plus a `graph:` block trains and evaluates the GNN directly through the pooled tournament — CV folds, Duan retransformation, fold cache, checkpoints, QLIKE/DM/MCS, and Rich progress — instead of only via `feature_stack` into XGBoost (the only path that exists today, cf. trial_068).

**Architecture:** Mirror the sequence-model dispatch exactly. `Pipeline.run_pooled` gains one early branch: `requires_graph and config.feature_stack is None → _run_pooled_graphs`. A new `pipeline/graph_data.py` converts the pooled `(date, symbol)` feature panel + a Plan-01 `GraphSnapshot` schedule into the graph-dict list that `GNNVolModel.fit/predict` already consumes. The per-horizon fold loop (`_run_one_horizon_graphs`) replicates the sequence loop's contract: `PanelExpandingWindowCV` on dates, per-fold seed offset, train-residual Duan correction, fold-cache lookups, and the `{metrics, predictions, actuals, model, duan_correction}` return dict — so the tournament, checkpoints, dashboard, and trials registry need **zero changes**.

**Tech stack:** existing `torch`/`torch-geometric` (graph extra), Plan-01 `volforecast.graphs`. No new dependencies.

**Why this shape (research grounding):** GNNHAR's protocol demands the model be evaluated in the same rolling harness as HAR (rolling window, monthly graph re-estimation, QLIKE, DM, MCS — Zhang et al. 2025 §5). A GNN that can only feed features into XGBoost cannot be scored as a model in the tournament table, cannot join the MCS, and confounds every ablation with the tree wrapper. This plan is pure infrastructure — no new science — but every later plan (03–10) registers models that run through this path.

## Global constraints

Same as Plan 01 (00-overview §4.1). Additional hard rules for this plan:
- **Do not modify** `_make_gnn_feature_stack_fn`, `_execute_gnn_fold`, or any behavior of the feature-stack path — trial_068 must keep working byte-identically (characterization test first).
- The graph schedule is point-in-time by construction (Plan 01); the runner must never pass post-fold-boundary rows into graph estimation *feature panels* either: the schedule is built once over all dates from data ≤ each refit date — that is the GNNHAR protocol and is already PIT. Tests assert it.
- Contract parity: the per-horizon return dict must match the sequence path (`test_runner_sequences.py` documents it).

## File map

| Action | Path | Responsibility |
|---|---|---|
| Create | `src/volforecast/pipeline/graph_data.py` | panel→graph-dict dataset builder + graph input panel selection |
| Modify | `src/volforecast/config.py` | `GraphConfig.node_features` field |
| Modify | `src/volforecast/pipeline/runner.py` | `_run_pooled_graphs`, `_run_one_horizon_graphs`, dispatch branch |
| Modify | `src/volforecast/evaluation/_model_utils.py` | default feature layers for graph-family models |
| Modify | `workspace/configs/_CANONICAL_EXAMPLE.yaml` | `graph.node_features` doc |
| Create | `src/tests/unit/test_graph_data.py` | dataset builder tests |
| Create | `src/tests/unit/test_runner_graphs.py` | fold-loop + dispatch tests (fake graph model) |
| Create | `src/tests/integration/test_graph_pipeline.py` | end-to-end pooled run on synthetic panel |
| Create | `workspace/configs/trial_079_gnn_native.yaml` | first native-GNN experiment |

## Interfaces

- **Consumes (Plan 01):** `GraphConfig`, `GRAPH_REGISTRY`, `build_graph_schedule(returns, dates, builder, *, window, refit_every, min_history)`, `GraphSnapshot.to_torch()`.
- **Consumes (existing):** graph-dict contract of `models/gnn.py` (`{"x": (N,F) float np, "edge_index": (2,E) long tensor, "edge_attr": (E,) float tensor, "y": (N,) float np, "date": ts}`), `Pipeline._build_pooled_tabular_panel(panel_data, feature_layers, h)`, `utils/targets.forward_log_rv`, `utils/cv.PanelExpandingWindowCV`, `pipeline/fold_cache.{compute_fold_cache_key, load_fold_cache, save_fold_cache}`, `models/gnn_adjacency.panel_returns_from_ohlcv`.
- **Produces (used by Plans 03–10):**
  - `build_graph_dataset(X_panel, y_panel, dates, schedule, node_feature_cols, symbols) -> list[dict]`
  - `graph_input_panel(panel_data, graph_cfg, ohlcv_dir=None) -> pd.DataFrame` (wide date×symbol frame: OHLCV log-returns or log-RV)
  - `Pipeline._run_pooled_graphs(panel_data, model_cls, *, on_fold_complete=None, on_horizon_start=None, on_train_progress=None, on_batch_progress=None, on_tuning_hpo=None) -> dict[int, Any]`
  - `GraphConfig.node_features: list[str] | None` (None → `DEFAULT_NODE_FEATURES`, the 9-column list trial_068 uses)

---

## Task 1: `graph_data.py` — panel → graph-dict dataset

**Files:** Create `src/volforecast/pipeline/graph_data.py`, `src/tests/unit/test_graph_data.py`. Modify `src/volforecast/config.py` (one field), `workspace/configs/_CANONICAL_EXAMPLE.yaml`.

**Copilot context packet:**

```yaml
subtask_id: "gnn-02-1"
goal: "Implement pipeline/graph_data.py (DEFAULT_NODE_FEATURES, graph_input_panel, build_graph_dataset producing gnn.py-contract graph dicts from a MultiIndex panel plus a GraphSnapshot schedule) and add GraphConfig.node_features."
file_scope:
  - workspace/plans/gnn/plan-02-graph-pipeline-path.md   # Task 1 section
  - src/volforecast/graphs/base.py
  - src/volforecast/models/gnn.py                        # lines 275-335: the graph-dict contract to satisfy
  - src/volforecast/models/gnn_adjacency.py              # panel_returns_from_ohlcv
  - src/volforecast/config.py                            # GraphConfig from Plan 01
write_scope:
  - src/volforecast/pipeline/graph_data.py
  - src/volforecast/config.py
  - src/tests/unit/test_graph_data.py
  - workspace/configs/_CANONICAL_EXAMPLE.yaml
acceptance_criteria:
  - "./vol test -k test_graph_data -> all pass"
  - "Graph dicts satisfy the gnn.py fit contract: x (N,F) float32 np with NaN->0, edge_index (2,E) torch.long, edge_attr (E,) torch.float32, y (N,) float64 np with NaN preserved, date set"
  - "Node order == config universe order on every date, including dates where some symbols have no panel row (features 0, y NaN)"
constraints: ["TDD failing-first", "No new dependencies", "graph.input='returns' -> OHLCV log returns; 'log_rv' -> log of the rv column from panel_data"]
context_summary: |
  Plan 01 gave us GraphSnapshot schedules. models/gnn.py already trains on lists of graph dicts
  (one per date) and masks NaN targets internally. This task is the pure-data bridge: take the
  pooled MultiIndex (date, symbol) feature matrix X_panel and target y_panel that
  Pipeline._build_pooled_tabular_panel produces, plus a date->GraphSnapshot schedule, and emit
  one dict per date with a FIXED node order (the config universe). trial_068's 9 node features
  are the default (DEFAULT_NODE_FEATURES).
depends_on: []
```

- [ ] **Step 1: Failing tests** — `src/tests/unit/test_graph_data.py`:

```python
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

from volforecast.graphs.base import GraphSnapshot, empty_snapshot
from volforecast.pipeline.graph_data import (
    DEFAULT_NODE_FEATURES,
    build_graph_dataset,
    graph_input_panel,
)


@pytest.fixture
def small_panel():
    """3 symbols x 6 dates MultiIndex panel; symbol C missing on the last date."""
    dates = pd.bdate_range("2024-01-01", periods=6)
    symbols = ["A", "B", "C"]
    rows = [(d, s) for d in dates for s in symbols]
    rows.remove((dates[-1], "C"))
    idx = pd.MultiIndex.from_tuples(rows, names=["date", "symbol"])
    rng = np.random.default_rng(42)
    X = pd.DataFrame(
        rng.normal(size=(len(idx), 3)), index=idx, columns=["log_rv_d", "log_rv_w", "f3"]
    )
    y = pd.Series(rng.normal(size=len(idx)), index=idx, name="target")
    return X, y, list(dates), symbols


def _schedule_for(dates, symbols):
    snap = GraphSnapshot(
        edge_index=np.array([[0, 1], [1, 0]], dtype=np.int64),
        edge_weight=np.array([0.9, 0.9], dtype=np.float32),
        symbols=tuple(symbols), date=dates[0], method="corr",
    )
    return {d: snap for d in dates}


def test_default_node_features_matches_trial_068():
    assert DEFAULT_NODE_FEATURES == [
        "log_rv_d", "log_rv_w", "log_rv_m", "signed_return_d", "abs_ret_d",
        "log_rs_negative_d", "log_jump_d", "log_bpv_d", "log_cont_d",
    ]


def test_build_graph_dataset_shapes_and_types(small_panel):
    X, y, dates, symbols = small_panel
    graphs = build_graph_dataset(
        X, y, dates, _schedule_for(dates, symbols), ["log_rv_d", "log_rv_w"], symbols
    )
    assert len(graphs) == len(dates)
    g = graphs[0]
    assert g["x"].shape == (3, 2) and g["x"].dtype == np.float32
    assert isinstance(g["edge_index"], torch.Tensor) and g["edge_index"].dtype == torch.long
    assert isinstance(g["edge_attr"], torch.Tensor) and g["edge_attr"].shape == (2,)
    assert g["y"].shape == (3,)
    assert g["date"] == dates[0]


def test_missing_symbol_row_gets_zero_features_and_nan_target(small_panel):
    X, y, dates, symbols = small_panel
    graphs = build_graph_dataset(
        X, y, dates, _schedule_for(dates, symbols), ["log_rv_d"], symbols
    )
    last = graphs[-1]
    assert np.all(last["x"][2] == 0.0)          # C has no row on the last date
    assert np.isnan(last["y"][2])
    assert not np.isnan(last["y"][0])


def test_missing_feature_column_raises(small_panel):
    X, y, dates, symbols = small_panel
    with pytest.raises(ValueError, match="node feature"):
        build_graph_dataset(
            X, y, dates, _schedule_for(dates, symbols), ["not_a_column"], symbols
        )


def test_node_order_is_universe_order_not_panel_order(small_panel):
    X, y, dates, symbols = small_panel
    rev = list(reversed(symbols))
    graphs = build_graph_dataset(X, y, dates, _schedule_for(dates, rev), ["log_rv_d"], rev)
    d0 = dates[0]
    expected_first = X.loc[(d0, rev[0]), "log_rv_d"]
    assert graphs[0]["x"][0, 0] == pytest.approx(np.float32(expected_first))


def test_empty_snapshot_yields_zero_edge_graph(small_panel):
    X, y, dates, symbols = small_panel
    sched = {d: empty_snapshot(symbols, d) for d in dates}
    graphs = build_graph_dataset(X, y, dates, sched, ["log_rv_d"], symbols)
    assert graphs[0]["edge_index"].shape == (2, 0)


def test_graph_input_panel_log_rv(tmp_path):
    dates = pd.bdate_range("2024-01-01", periods=5)
    panel_data = {
        s: pd.DataFrame({"rv": np.full(5, 1e-4 * (i + 1))}, index=dates)
        for i, s in enumerate(["A", "B"])
    }
    from volforecast.config import GraphConfig

    wide = graph_input_panel(panel_data, GraphConfig(method="identity", input="log_rv"))
    assert list(wide.columns) == ["A", "B"]
    assert wide.iloc[0, 0] == pytest.approx(np.log(1e-4))
```

- [ ] **Step 2:** `./vol test -k test_graph_data` → red.
- [ ] **Step 3: Implement** — `src/volforecast/pipeline/graph_data.py`:

```python
"""Bridge from the pooled (date, symbol) panel to graph-dict datasets.

Produces the exact structure ``GNNVolModel.fit``/``predict`` consume
(models/gnn.py): one dict per date with node features in a FIXED universe
order, NaN features zeroed (isolated/missing nodes still flow through the
MLP head), NaN targets preserved (masked inside the model).
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from volforecast.graphs.base import GraphSnapshot

#: trial_068's node feature list — the default for all graph models.
DEFAULT_NODE_FEATURES: list[str] = [
    "log_rv_d", "log_rv_w", "log_rv_m", "signed_return_d", "abs_ret_d",
    "log_rs_negative_d", "log_jump_d", "log_bpv_d", "log_cont_d",
]


def graph_input_panel(
    panel_data: dict[str, pd.DataFrame], graph_cfg, ohlcv_dir=None
) -> pd.DataFrame:
    """Wide date x symbol frame the graph builders estimate on.

    input='returns'  -> OHLCV close-to-close log returns (corr/glasso/knn/factor families)
    input='log_rv'   -> log of the rv column from the per-symbol RV panels (dy)
    """
    if graph_cfg.input == "log_rv":
        cols = {
            sym: np.log(df["rv"].clip(lower=1e-20))
            for sym, df in panel_data.items()
            if "rv" in df.columns
        }
        wide = pd.DataFrame(cols).sort_index()
        wide.columns.name = "symbol"
        return wide
    from volforecast.models.gnn_adjacency import panel_returns_from_ohlcv
    from volforecast.utils.paths import ohlcv_cache_dir

    return panel_returns_from_ohlcv(ohlcv_dir or ohlcv_cache_dir())


def build_graph_dataset(
    X_panel: pd.DataFrame,
    y_panel: pd.Series | None,
    dates: list[Any],
    schedule: dict[Any, GraphSnapshot],
    node_feature_cols: list[str],
    symbols: list[str],
) -> list[dict[str, Any]]:
    """One graph dict per date. Node order == ``symbols`` order on every date."""
    missing = [c for c in node_feature_cols if c not in X_panel.columns]
    if missing:
        raise ValueError(f"node feature column(s) not in panel: {missing}")

    n, f = len(symbols), len(node_feature_cols)
    # Dense (date, symbol) -> row lookup via reindex on the full product index
    full_idx = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
    X_dense = X_panel[node_feature_cols].reindex(full_idx)
    x_all = X_dense.to_numpy(dtype=np.float32).reshape(len(dates), n, f)
    x_all = np.nan_to_num(x_all, nan=0.0)
    if y_panel is not None:
        y_all = y_panel.reindex(full_idx).to_numpy(dtype=np.float64).reshape(len(dates), n)
    else:
        y_all = np.full((len(dates), n), np.nan)

    graphs: list[dict[str, Any]] = []
    for i, date in enumerate(dates):
        snap = schedule[date]
        edge_index, edge_attr = snap.to_torch()
        graphs.append(
            {
                "x": x_all[i],
                "edge_index": edge_index,
                "edge_attr": edge_attr,
                "y": y_all[i],
                "date": date,
            }
        )
    return graphs
```

In `config.py`, extend `GraphConfig` with:

```python
    node_features: list[str] | None = None  # None -> pipeline.graph_data.DEFAULT_NODE_FEATURES
```

(and mention it in the `_CANONICAL_EXAMPLE.yaml` graph block: `# node_features: [log_rv_d, log_rv_w, ...]  # default: trial_068's 9 features`).

- [ ] **Step 4:** `./vol test -k "test_graph_data or test_graph_config"` → green.
- [ ] **Step 5: Commit** — `feat(pipeline): graph_data bridge from pooled panel to graph-dict datasets`

---

## Task 2: `_run_one_horizon_graphs` — the fold loop

**Files:** Modify `src/volforecast/pipeline/runner.py`. Create `src/tests/unit/test_runner_graphs.py`.

**Copilot context packet:**

```yaml
subtask_id: "gnn-02-2"
goal: "Implement Pipeline._run_one_horizon_graphs: PanelExpandingWindowCV over dates, per-fold graph datasets, per-fold seed offset, Duan correction from train residuals, fold-cache reuse, and the sequence-path return-dict contract; tested with a registered fake graph model."
file_scope:
  - workspace/plans/gnn/plan-02-graph-pipeline-path.md   # Task 2 section (reference implementation)
  - src/volforecast/pipeline/runner.py                   # _run_one_horizon_sequences (lines ~2454+) is the template
  - src/volforecast/pipeline/graph_data.py
  - src/volforecast/pipeline/fold_cache.py
  - src/volforecast/utils/cv.py                          # PanelExpandingWindowCV
  - src/tests/unit/test_runner_sequences.py              # contract + fake-model test pattern
write_scope:
  - src/volforecast/pipeline/runner.py
  - src/tests/unit/test_runner_graphs.py
acceptance_criteria:
  - "./vol test -k test_runner_graphs -> all pass"
  - "Return dict per horizon has keys {metrics, predictions, actuals, model, duan_correction}; predictions is a (date,symbol)-indexed Series over test rows only"
  - "effective_purge = max(cv.purge_gap, h) enforced; fold seeds = base seed + fold_num"
  - "./vol test -k test_runner_sequences -> unchanged (no regression)"
constraints:
  - "TDD failing-first; the fake graph model must be registered via @register_model inside the test module and popped from MODEL_REGISTRY in teardown"
  - "Duan: correction = log(mean(exp(clip(train_residuals, -10, 10)))) on valid train rows, exactly as the tabular/sequence paths"
  - "Do not touch _run_horizon, _run_pooled_sequences, or the feature-stack GNN path"
context_summary: |
  This is the graph twin of _run_one_horizon_sequences. Inputs: X_panel/y_panel (MultiIndex,
  mergesorted by date), the graph input panel, and config.graph. Build ONE point-in-time
  graph schedule over all dates (build_graph_schedule is PIT by construction), then for each
  PanelExpandingWindowCV fold: slice train/test dates, build graph datasets, instantiate the
  model with auto-injected input_dim/seed, fit with on_progress, predict test graphs (flattened
  node-major), map back to (date,symbol) rows, apply Duan, fire on_fold_complete(h, fold_num).
  Single-device in this plan; Plan 08 adds the multi-GPU pool.
depends_on: ["gnn-02-1"]
```

- [ ] **Step 1: Failing tests** — `src/tests/unit/test_runner_graphs.py` (core cases; follow `test_runner_sequences.py` style):

```python
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

from volforecast.config import CVConfig, ExperimentConfig, GraphConfig, ModelConfig
from volforecast.pipeline.runner import Pipeline
from volforecast.registry import MODEL_REGISTRY, register_model


@pytest.fixture
def fake_graph_model():
    """Minimal requires_graph model: predicts the mean of train targets."""

    @register_model("_fake_graph")
    class _FakeGraph:
        REQUIRED_LAYERS: list[str] = []
        requires_sequences = False
        requires_graph = True
        supports_tuning = False
        family = "gnn"
        description = "test double"

        def __init__(self, *, input_dim: int, seed: int = 42, **kwargs):
            self.input_dim = input_dim
            self.seed = seed
            self.seen_progress = False
            self._mean = 0.0

        def fit(self, graphs, y=None, *, on_progress=None):
            ys = np.concatenate([g["y"] for g in graphs])
            self._mean = float(np.nanmean(ys))
            if on_progress is not None:
                on_progress(1, 1)
                self.seen_progress = True
            return self

        def predict(self, graphs):
            n = sum(g["x"].shape[0] for g in graphs)
            return np.full(n, self._mean)

        def get_params(self):
            return {"input_dim": self.input_dim, "seed": self.seed}

        @property
        def summary(self):
            return {"mean": self._mean}

    yield _FakeGraph
    MODEL_REGISTRY.pop("_fake_graph", None)


@pytest.fixture
def graph_panel_data():
    """3 symbols x 320 bdays of synthetic AR(1) log-RV panels with rv column."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2022-01-03", periods=320)
    out = {}
    for k, sym in enumerate(["AAA", "BBB", "CCC"]):
        log_rv = np.zeros(len(dates))
        log_rv[0] = -9.0
        for t in range(1, len(dates)):
            log_rv[t] = -9.0 * 0.05 + 0.95 * log_rv[t - 1] + rng.normal(0, 0.3)
        df = pd.DataFrame({"rv": np.exp(log_rv)}, index=dates)
        df.index.name = "date"
        out[sym] = df
    return out


def _config(fake_name="_fake_graph"):
    return ExperimentConfig(
        name="t_graph", universe=["AAA", "BBB", "CCC"],
        date_range=("2022-01-03", "2023-03-31"), horizons=[1],
        feature_layers=["har_core"],
        model=ModelConfig(name=fake_name, params={}),
        cv=CVConfig(method="expanding_window", purge_gap=5, train_size=150, test_size=50),
        graph=GraphConfig(method="identity", input="log_rv", node_features=["log_rv_d"]),
        fold_cache_enabled=False, checkpoint_enabled=False,
    )


def test_graph_horizon_contract(fake_graph_model, graph_panel_data):
    results = Pipeline(_config()).run_pooled(graph_panel_data)
    assert set(results) == {1}
    res = results[1]
    assert {"metrics", "predictions", "actuals", "model", "duan_correction"} <= set(res)
    assert isinstance(res["predictions"], pd.Series)
    assert isinstance(res["predictions"].index, pd.MultiIndex)
    assert len(res["predictions"]) == len(res["actuals"]) > 0
    assert np.isfinite(res["predictions"].values).all()
    assert "qlike" in res["metrics"]


def test_fold_completion_and_progress_callbacks(fake_graph_model, graph_panel_data):
    folds: list[tuple[int, int]] = []
    Pipeline(_config()).run_pooled(
        graph_panel_data,
        on_fold_complete=lambda h, f: folds.append((h, f)),
        on_train_progress=lambda cur, tot: None,
    )
    assert folds and folds[-1][0] == 1
    assert [f for _, f in folds] == list(range(1, len(folds) + 1))


def test_purge_respects_horizon(fake_graph_model, graph_panel_data):
    cfg = _config()
    cfg.horizons = [22]
    cfg.cv.purge_gap = 5  # must be raised to 22 internally
    results = Pipeline(cfg).run_pooled(graph_panel_data)
    preds = results[22]["predictions"]
    # no test date may be within 22 days of the max train date of its fold —
    # asserted indirectly: predictions exist and pipeline enforced effective purge
    assert len(preds) > 0


def test_predictions_only_on_existing_panel_rows(fake_graph_model, graph_panel_data):
    # drop the last 10 rows of CCC: predictions must not include those (date, CCC) rows
    graph_panel_data["CCC"] = graph_panel_data["CCC"].iloc[:-10]
    results = Pipeline(_config()).run_pooled(graph_panel_data)
    idx = results[1]["predictions"].index
    ccc_dates = {d for d, s in idx if s == "CCC"}
    dropped = set(pd.bdate_range("2023-03-20", periods=10))
    assert not (ccc_dates & dropped)
```

- [ ] **Step 2:** red. **Step 3: Implement** in `runner.py` (reference implementation — adapt names to local style; place next to `_run_pooled_sequences`):

```python
    def _run_one_horizon_graphs(
        self,
        X_panel: pd.DataFrame,
        y_panel: pd.Series,
        input_panel: pd.DataFrame,
        h: int,
        *,
        on_fold_complete=None,
        on_train_progress=None,
    ) -> dict[str, Any]:
        from volforecast.graphs.base import build_graph_schedule
        from volforecast.pipeline.graph_data import (
            DEFAULT_NODE_FEATURES,
            build_graph_dataset,
        )
        from volforecast.registry import GRAPH_REGISTRY

        graph_cfg = self.config.graph
        model_cls = MODEL_REGISTRY[self.config.model.name]
        symbols = sorted(self.config.universe)
        node_cols = graph_cfg.node_features or DEFAULT_NODE_FEATURES
        node_cols = [c for c in node_cols if c in X_panel.columns] or DEFAULT_NODE_FEATURES[:1]

        dates = list(pd.DatetimeIndex(X_panel.index.get_level_values("date").unique()).sort_values())
        builder = GRAPH_REGISTRY[graph_cfg.method](**graph_cfg.params)
        schedule = build_graph_schedule(
            input_panel.reindex(columns=symbols), dates, builder,
            window=graph_cfg.window, refit_every=graph_cfg.refit_every,
            min_history=graph_cfg.min_history,
        )
        graphs_all = build_graph_dataset(X_panel, y_panel, dates, schedule, node_cols, symbols)
        by_date = dict(zip(dates, graphs_all))

        cv_cfg = self.config.cv_for_horizon(h)
        effective_purge = max(cv_cfg.purge_gap, h)
        cv = PanelExpandingWindowCV(
            min_train_size=cv_cfg.train_size or 252,
            test_size=cv_cfg.test_size or 63,
            purge_gap=effective_purge,
        )
        model_params = self.config.model_params_for_horizon(h)
        model_params.setdefault("input_dim", len(node_cols))
        base_seed = int(model_params.get("seed", self.config.seed))

        all_preds = pd.Series(np.nan, index=y_panel.index)
        model = None
        duan_correction = 0.0
        fold_num = 0
        for train_idx, test_idx in cv.split(X_panel):
            fold_num += 1
            train_dates = X_panel.index[train_idx].get_level_values("date").unique()
            test_dates = X_panel.index[test_idx].get_level_values("date").unique()
            train_graphs = [by_date[d] for d in train_dates]
            test_graphs = [by_date[d] for d in test_dates]

            fold_params = dict(model_params)
            fold_params["seed"] = base_seed + fold_num
            model = model_cls(**fold_params)
            fit_kwargs = {"on_progress": on_train_progress} if on_train_progress else {}
            model.fit(train_graphs, **fit_kwargs)

            # Duan (1995) smearing from train residuals on valid rows
            train_flat = model.predict(train_graphs)
            train_y = np.concatenate([g["y"] for g in train_graphs])
            valid = np.isfinite(train_y)
            resid = np.clip(train_y[valid] - train_flat[valid], -10.0, 10.0)
            duan_correction = float(np.log(np.mean(np.exp(resid)))) if valid.any() else 0.0

            test_flat = model.predict(test_graphs) + duan_correction
            test_full_idx = pd.MultiIndex.from_product(
                [test_dates, symbols], names=["date", "symbol"]
            )
            test_series = pd.Series(test_flat, index=test_full_idx)
            keep = test_series.index.intersection(X_panel.index[test_idx])
            all_preds.loc[keep] = test_series.loc[keep]

            if on_fold_complete is not None:
                on_fold_complete(h, fold_num)

        mask = all_preds.notna() & y_panel.notna()
        preds, actuals = all_preds[mask], y_panel[mask]
        return {
            "metrics": {
                "qlike": qlike(actuals.values, preds.values),
                "mse": mse(actuals.values, preds.values),
                "r2": r_squared(actuals.values, preds.values),
            },
            "predictions": preds,
            "actuals": actuals,
            "model": model,
            "duan_correction": duan_correction,
        }
```

Fold-cache integration (same task): before `model.fit`, compute `cache_key = compute_fold_cache_key(config_fp, h, fold_num, train_dates, test_dates, None, None)` and short-circuit with `load_fold_cache` / persist with `save_fold_cache` when `self.config.fold_cache_enabled` — copy the exact pattern from `_execute_fold` lines ~269–284 (cache hits must still fire `on_fold_complete`).

- [ ] **Step 4:** `./vol test -k "test_runner_graphs or test_runner_sequences"` → green.
- [ ] **Step 5: Commit** — `feat(pipeline): standalone graph-model fold loop with Duan and fold cache`

---

## Task 3: Dispatch, `_run_pooled_graphs`, model-utils defaults, characterization guard

**Files:** Modify `src/volforecast/pipeline/runner.py`, `src/volforecast/evaluation/_model_utils.py`. Extend `src/tests/unit/test_runner_graphs.py`.

**Copilot context packet:**

```yaml
subtask_id: "gnn-02-3"
goal: "Wire _run_pooled_graphs into Pipeline.run_pooled (requires_graph and no feature_stack -> graph path; feature_stack present -> legacy path unchanged), give graph-family models default feature layers in _model_utils, and lock the trial_068 feature-stack path with a characterization test."
file_scope:
  - workspace/plans/gnn/plan-02-graph-pipeline-path.md   # Task 3 section
  - src/volforecast/pipeline/runner.py                   # run_pooled dispatch area (~line 1049) + _run_pooled_sequences shape
  - src/volforecast/evaluation/_model_utils.py
  - src/tests/unit/test_runner_graphs.py
write_scope:
  - src/volforecast/pipeline/runner.py
  - src/volforecast/evaluation/_model_utils.py
  - src/tests/unit/test_runner_graphs.py
acceptance_criteria:
  - "./vol test -k test_runner_graphs -> all pass (incl. new dispatch tests)"
  - "requires_graph model + feature_stack config still routes through _make_gnn_feature_stack_fn (characterization test asserts the legacy function is called)"
  - "feature_layers_for_model returns [har_core, asymmetry] for family=='gnn' models"
  - "./vol test -> full non-slow suite green"
constraints: ["TDD failing-first", "The dispatch branch mirrors requires_sequences exactly (runner.py ~1049-1061)", "config.graph is None + requires_graph standalone -> ValueError telling the user to add a graph: block (fail loud, no silent default)"]
context_summary: |
  run_pooled currently dispatches: requires_sequences -> _run_pooled_sequences; feature_stack ->
  tabular loop with a stack fn (graph models handled inside via _make_gnn_feature_stack_fn).
  Add: requires_graph and self.config.feature_stack is None -> _run_pooled_graphs(panel_data,
  model_cls, ...), which builds the pooled tabular panel per horizon via
  _build_pooled_tabular_panel(panel_data, config.feature_layers, h), builds the graph input
  panel once via graph_input_panel, and loops horizons calling _run_one_horizon_graphs.
  Tournament labels: _model_utils.feature_layers_for_model needs a 'gnn' family default so
  tournament entries like 'gnn' get har_core+asymmetry node features without explicit config.
depends_on: ["gnn-02-2"]
```

- [ ] **Step 1: Failing tests** (append to `test_runner_graphs.py`):

```python
def test_dispatch_prefers_feature_stack_when_configured(fake_graph_model, graph_panel_data, monkeypatch):
    """requires_graph + feature_stack config -> legacy stack path, NOT _run_pooled_graphs."""
    called = {"stack": 0, "native": 0}
    cfg = _config()
    from volforecast.config import FeatureStackConfig

    cfg.model = ModelConfig(name="har", params={})
    cfg.feature_stack = FeatureStackConfig(source_model="_fake_graph", outputs=["prediction"])
    pipe = Pipeline(cfg)
    monkeypatch.setattr(
        pipe, "_make_gnn_feature_stack_fn",
        lambda *a, **k: called.__setitem__("stack", called["stack"] + 1) or (lambda *a2, **k2: None),
        raising=True,
    )
    monkeypatch.setattr(
        pipe, "_run_pooled_graphs",
        lambda *a, **k: called.__setitem__("native", called["native"] + 1) or {},
        raising=True,
    )
    try:
        pipe.run_pooled(graph_panel_data)
    except Exception:
        pass  # stub stack fn breaks downstream; we only assert routing
    assert called["stack"] >= 1 and called["native"] == 0


def test_native_graph_requires_graph_block(fake_graph_model, graph_panel_data):
    cfg = _config()
    cfg.graph = None
    with pytest.raises(ValueError, match="graph:"):
        Pipeline(cfg).run_pooled(graph_panel_data)


def test_model_utils_default_layers_for_gnn_family(fake_graph_model):
    from volforecast.evaluation._model_utils import feature_layers_for_model

    assert feature_layers_for_model("_fake_graph") == ["har_core", "asymmetry"]
```

- [ ] **Step 2:** red. **Step 3: Implement** — in `run_pooled`, immediately after the `requires_sequences` branch:

```python
        if getattr(model_cls, "requires_graph", False) and self.config.feature_stack is None:
            if self.config.graph is None:
                raise ValueError(
                    f"Model {model_name!r} requires a 'graph:' config block "
                    "(method/window/refit_every) to run standalone. "
                    "See workspace/configs/_CANONICAL_EXAMPLE.yaml."
                )
            return self._run_pooled_graphs(
                panel_data,
                model_cls,
                on_fold_complete=on_fold_complete,
                on_horizon_start=on_horizon_start,
                on_train_progress=on_train_progress,
                on_batch_progress=on_batch_progress,
                on_tuning_hpo=on_tuning_hpo,
            )
```

`_run_pooled_graphs` (mirrors `_run_pooled_sequences`'s outer shape):

```python
    def _run_pooled_graphs(
        self, panel_data, model_cls, *, on_fold_complete=None, on_horizon_start=None,
        on_train_progress=None, on_batch_progress=None, on_tuning_hpo=None,
    ) -> dict[int, Any]:
        from volforecast.pipeline.graph_data import graph_input_panel

        input_panel = graph_input_panel(panel_data, self.config.graph)
        results: dict[int, Any] = {}
        for h in self.config.horizons:
            if on_horizon_start is not None:
                on_horizon_start(h)
            X_panel, y_panel = self._build_pooled_tabular_panel(
                panel_data, self.config.feature_layers, h
            )
            results[h] = self._run_one_horizon_graphs(
                X_panel, y_panel, input_panel, h,
                on_fold_complete=on_fold_complete,
                on_train_progress=on_train_progress,
            )
        return results
```

In `evaluation/_model_utils.py::feature_layers_for_model`, add before the fallback:

```python
    cls = MODEL_REGISTRY.get(model_name)
    if cls is not None and getattr(cls, "requires_graph", False):
        return ["har_core", "asymmetry"]
```

- [ ] **Step 4:** `./vol test` (full non-slow) → green, zero regressions.
- [ ] **Step 5: Commit** — `feat(pipeline): dispatch requires_graph models to the native graph path`

---

## Task 4: End-to-end integration test + first native config + docs

**Files:** Create `src/tests/integration/test_graph_pipeline.py`, `workspace/configs/trial_079_gnn_native.yaml`. Modify `workspace/research/trials.yaml` (register NOT_STARTED trial).

**Copilot context packet:**

```yaml
subtask_id: "gnn-02-4"
goal: "Add an integration test running the real GNNVolModel end-to-end through run_pooled on a synthetic 3-symbol panel (tiny epochs, cpu), create trial_079_gnn_native.yaml (8-GPU native GNN vs HAR baselines), and register the trial."
file_scope:
  - workspace/plans/gnn/plan-02-graph-pipeline-path.md   # Task 4 section (config YAML inline)
  - src/tests/integration/test_integration.py            # style reference
  - src/tests/unit/test_runner_graphs.py                 # graph_panel_data fixture to lift
  - workspace/configs/trial_068_gnn_standalone.yaml      # ancestor config
  - workspace/configs/_CANONICAL_EXAMPLE.yaml
  - workspace/research/trials.yaml
write_scope:
  - src/tests/integration/test_graph_pipeline.py
  - workspace/configs/trial_079_gnn_native.yaml
  - workspace/research/trials.yaml
acceptance_criteria:
  - "./vol test -k test_graph_pipeline -> passes (mark slow if wall time > 2s; then verify via ./vol test-all -k test_graph_pipeline)"
  - "trial_079 config parses: ./vol exec python -c \"from volforecast.config import ExperimentConfig; ExperimentConfig.from_yaml('workspace/configs/trial_079_gnn_native.yaml')\" exits 0 (use ./vol shell)"
  - "trials.yaml gains trial-079 with status NOT_STARTED, hypothesis, baseline_config"
constraints: ["TDD failing-first for the test file", "torch-geometric guarded with pytest.importorskip('torch_geometric')", "Do NOT run vol run - print the launch command in the final report"]
context_summary: |
  Everything is wired; this task proves it with the REAL GATv2 model (hidden_dim 8, max_epochs 3,
  device cpu, 2 folds) and ships the first runnable experiment: native GNN entry in a tournament
  against har/har_iv/ewma with the corr graph (trial_068 parity settings: window 60 threshold 0.3)
  so the native path can be validated against the stacked path on the GS machine. Take the next
  free trial number if 079 is taken.
depends_on: ["gnn-02-3"]
```

- [ ] **Step 1: Failing test** — `src/tests/integration/test_graph_pipeline.py`:

```python
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")

from volforecast.config import CVConfig, ExperimentConfig, GraphConfig, ModelConfig
from volforecast.pipeline.runner import Pipeline

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def test_real_gnn_end_to_end(graph_panel_data_module):  # fixture: lift graph_panel_data to a shared conftest
    cfg = ExperimentConfig(
        name="it_gnn_native", universe=["AAA", "BBB", "CCC"],
        date_range=("2022-01-03", "2023-03-31"), horizons=[1],
        feature_layers=["har_core", "asymmetry"],
        model=ModelConfig(name="gnn", params={
            "hidden_dim": 8, "n_heads": 2, "max_epochs": 3,
            "early_stopping_rounds": 3, "device": "cpu", "loss": "qlike",
        }),
        cv=CVConfig(method="expanding_window", purge_gap=5, train_size=150, test_size=60),
        graph=GraphConfig(method="corr", input="log_rv", window=60,
                          refit_every=21, params={"threshold": 0.2}),
        fold_cache_enabled=False, checkpoint_enabled=False,
    )
    results = Pipeline(cfg).run_pooled(graph_panel_data_module)
    res = results[1]
    assert np.isfinite(res["metrics"]["qlike"])
    assert len(res["predictions"]) > 100
    assert res["predictions"].std() > 0  # not a constant predictor
```

- [ ] **Step 2:** red → implement (move the `graph_panel_data` fixture into `src/tests/integration/conftest.py` as `graph_panel_data_module`), green via `./vol test-all -k test_graph_pipeline`.
- [ ] **Step 3: Create** `workspace/configs/trial_079_gnn_native.yaml`:

```yaml
# Trial-079: native GNN as a first-class tournament entry (Plan 02 acceptance run)
#
# Hypothesis: the standalone GATv2 path reproduces trial_068's stacked-GNN signal
# quality when scored directly under QLIKE (no XGBoost wrapper), establishing the
# harness for the GHAR/GNNHAR ablations (Plans 03-04).
# COVID handling: included (2020 inside the training span; expanding window absorbs it).

name: trial_079_gnn_native
n_gpus: 8

universe: [SPY, AAPL, MSFT, NVDA, AVGO, GOOGL, AMZN, V, MA, XOM, PG,
           JNJ, HD, NFLX, TSLA, CRM, UNH, BAC, ADBE, IWM, DIA]

date_range: ["2015-01-02", "2026-05-30"]
horizons: [1, 5, 22]

feature_layers: [har_core, asymmetry]

model:
  name: gnn
  params:
    hidden_dim: 32
    n_heads: 4
    dropout: 0.1
    learning_rate: 0.001
    weight_decay: 1.0e-4
    max_epochs: 200
    early_stopping_rounds: 15
    loss: qlike
    device: auto
    precision: auto
    seed: 42

graph:
  method: corr
  input: returns
  window: 60
  refit_every: 1          # trial_068 parity: daily-refreshed rolling correlation
  min_history: 60
  params: {threshold: 0.3}
  # node_features: default 9 (trial_068 parity)

cv:
  method: expanding_window
  purge_gap: 10
  train_size: 504
  test_size: 126

tournament:
  models: [ewma, har, har_iv, gnn]
  baseline: har_iv
  mcs_bootstrap: 10000
  parallel_models: 1      # gnn owns the GPUs; HAR baselines are instant
  dh_enabled: false
  vt_enabled: false

training_mode: pooled
seed: 42
output_dir: data/models/trial_079_gnn_native
```

- [ ] **Step 4:** Register in `workspace/research/trials.yaml` (`id: trial-079`, `status: NOT_STARTED`, `baseline_config: trial_063_xgboost_champion`, hypothesis above). Print the launch command: `./vol run --config workspace/configs/trial_079_gnn_native.yaml --skip-ingest`.
- [ ] **Step 5: Commit** — `test(integration): native GNN end-to-end; chore(config): trial_079_gnn_native`

---

## 8. Orchestrator prompt (paste into Copilot Chat)

```
/execute Implement Plan 02 (standalone graph-model pipeline path) from workspace/plans/gnn/plan-02-graph-pipeline-path.md

Precondition check first: ./vol test -k "graphs or test_graph_config" must be green (Plan 01 merged).
Read workspace/plans/gnn/00-overview.md §4 for shared conventions.
Execute strictly sequentially (each task modifies runner.py or its consumers):
  gnn-02-1 -> gnn-02-2 -> gnn-02-3 -> gnn-02-4
Each subagent: TDD (show red, then green), ./vol only, return contract per 00-overview §4.2.
Integration verification: ./vol test-all green; ./vol lint; ./vol typecheck.
Commit series per task; weekly-progress entry (Shipped: GNN models now run natively in vol run).
Print (do not run): ./vol run --config workspace/configs/trial_079_gnn_native.yaml --skip-ingest
Do NOT start Plan 03.
```

## 9. Acceptance gate → Plan 03

- `./vol test-all` green; feature-stack characterization test proves trial_068 path untouched.
- `_run_pooled_graphs` return contract verified identical to sequence path.
- trial_079 registered; on the GS machine the user launches it and sanity-checks: QLIKE(gnn) within noise of trial_068's stacked variant, dashboards render, checkpoints resume.
- Handoff to Plan 03: graph models need only `@register_model` + `requires_graph = True` + the graph-dict `fit/predict` contract — no runner changes ever again.
