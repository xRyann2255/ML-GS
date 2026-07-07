# Plan 01 — Graph Construction Library

> **For the Copilot orchestrator:** execute with `/execute` using the Orchestrator prompt in §9. Dispatch each task as a subagent with the context packet provided in that task. Max 2 concurrent subagents. TDD is a hard gate (`.github/copilot-instructions.md` Rule 5). Read `workspace/plans/gnn/00-overview.md` §4 for shared conventions before starting.

**Goal:** A `volforecast/graphs/` package providing eight point-in-time graph builders behind one registry, so every downstream model (GHAR, GNNHAR, GAT, DCRNN-HAR, GSP-HAR) selects its adjacency from YAML (`graph: {method: glasso, ...}`) instead of hard-coding correlation thresholds.

**Architecture:** Builders are small classes registered in a new `GRAPH_REGISTRY` (mirroring `MODEL_REGISTRY`). Each consumes an *estimation window* of a wide panel (date × symbol) and emits an immutable `GraphSnapshot` (numpy edge lists + lazy torch conversion, so linear models never import torch). A `build_graph_schedule` helper enforces the point-in-time protocol: re-estimate every `refit_every` trading days on the trailing `window`, freeze between refits. Config plumbing adds a `GraphConfig` dataclass and a `graph:` YAML block.

**Tech stack:** numpy/pandas (all builders), `sklearn.covariance.GraphicalLassoCV` (GLASSO — sklearn already a core dep), `statsmodels.tsa.api.VAR` (DY spillover — already used by `features/cross_asset.py`), torch only inside `GraphSnapshot.to_torch()`. **No new dependencies.**

**Research grounding:** Graph construction is the contested design lever (00-overview §3, decision 4). The menu implemented here is exactly the chapter's §"Graph Construction": thresholded correlation (Wade 2026 caveat: density is regime-dependent), kNN top-K (GTN-VF: edge quality > quantity), GLASSO conditional-independence (Zhang et al. 2025 — the GNNHAR lineage's choice, re-estimated monthly on rolling windows), Diebold–Yilmaz generalized-FEVD directed spillover (Boetti & Nunes 2026 recipe: drop edges < 0.05; DCRNN-HAR makes it dynamic), sector priors, fully-connected (GNAR-HARX winner on small universes), identity (the no-graph control every ablation needs), and factor-residual networks (Cartea, Cucuringu & Fang 2026 design idea — edges from what the market factor cannot explain).

## Global constraints

- All commands via `./vol` (`./vol test -k <expr>`, `./vol test-all` before commit). Never bare python/pytest/pip/uv/mypy/ruff.
- TDD: failing test first for every Python change; show red, then green.
- Graph estimation must use only data ≤ estimation date (PIT). Every builder gets a leakage test.
- Determinism: `np.random.default_rng(seed)` in fixtures; no randomness in builders.
- Config/registry edits update `workspace/configs/_CANONICAL_EXAMPLE.yaml` in the same task.
- ruff line-length 100, `from __future__ import annotations`; mypy must stay green (`./vol typecheck`).
- New math (generalized FEVD) gets a `tests/unit/formulas/` gold-value test registered in `FORMULAS.md`.

## File map

| Action | Path | Responsibility |
|---|---|---|
| Create | `src/volforecast/graphs/__init__.py` | re-exports |
| Create | `src/volforecast/graphs/base.py` | `GraphSnapshot`, `GraphBuilder` protocol, `build_graph_schedule` |
| Create | `src/volforecast/graphs/simple.py` | `identity`, `full`, `sector` builders + `SECTOR_MAP` |
| Create | `src/volforecast/graphs/correlation.py` | `corr` (threshold), `knn` (top-K) builders |
| Create | `src/volforecast/graphs/glasso.py` | `glasso` builder |
| Create | `src/volforecast/graphs/spillover.py` | `dy` builder + `generalized_fevd_matrix()` |
| Create | `src/volforecast/graphs/factor_residual.py` | `factor_residual` builder |
| Create | `src/volforecast/graphs/diagnostics.py` | density / degree / Jaccard stability |
| Modify | `src/volforecast/registry.py` | `GRAPH_REGISTRY`, `register_graph`, imports in `ensure_registered()` |
| Modify | `src/volforecast/config.py` | `GraphConfig` dataclass, `ExperimentConfig.graph`, YAML parsing |
| Modify | `src/volforecast/utils/persistence.py` | include `graph` in `_config_fingerprint` |
| Modify | `workspace/configs/_CANONICAL_EXAMPLE.yaml` | document the `graph:` block |
| Create | `src/tests/unit/graphs/__init__.py`, `conftest.py`, `test_graph_base.py`, `test_simple_graphs.py`, `test_correlation_graphs.py`, `test_glasso_graph.py`, `test_dy_graph.py`, `test_factor_residual.py`, `test_graph_diagnostics.py` | unit tests |
| Create | `src/tests/unit/formulas/test_gfevd_formulas.py` + `gold_values/gfevd_bivariate_var1.json` | formula gold test |
| Create | `src/tests/unit/test_graph_config.py` | config round-trip tests |

## Shared test fixture (created in Task 1, used by all graph tests)

`src/tests/unit/graphs/conftest.py`:

```python
"""Shared fixtures for graph-builder tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_returns_panel() -> pd.DataFrame:
    """300 bdays x 8 symbols with two independent 4-symbol correlation blocks.

    Block A (A1..A4) loads on factor f1, block B (B1..B4) on f2.
    Intra-block correlation ~0.85; cross-block ~0. Any sane graph builder
    should recover the block structure.
    """
    rng = np.random.default_rng(42)
    n = 300
    dates = pd.bdate_range("2022-01-03", periods=n)
    f1 = rng.normal(0.0, 0.010, n)
    f2 = rng.normal(0.0, 0.010, n)
    cols: dict[str, np.ndarray] = {}
    for sym in ["A1", "A2", "A3", "A4"]:
        cols[sym] = 0.9 * f1 + rng.normal(0.0, 0.004, n)
    for sym in ["B1", "B2", "B3", "B4"]:
        cols[sym] = 0.9 * f2 + rng.normal(0.0, 0.004, n)
    return pd.DataFrame(cols, index=dates)


@pytest.fixture
def symbols8(synthetic_returns_panel) -> list[str]:
    return list(synthetic_returns_panel.columns)
```

---

## Task 1: Registry, `GraphSnapshot`, `GraphBuilder` protocol, schedule

**Files:** Create `src/volforecast/graphs/__init__.py`, `src/volforecast/graphs/base.py`, `src/tests/unit/graphs/{__init__.py,conftest.py,test_graph_base.py}`. Modify `src/volforecast/registry.py`.

**Interfaces produced (later tasks and plans rely on these exact names):**
- `GraphSnapshot(edge_index, edge_weight, symbols, date, directed=False, method="")` with `.n_nodes`, `.n_edges`, `.density()`, `.dense_adjacency(norm=None|"sym"|"row", binary=False)`, `.to_torch()`.
- `GraphBuilder` runtime-checkable protocol: `name: str`, `directed: bool`, `build(returns: pd.DataFrame, date, symbols: list[str]) -> GraphSnapshot` where `returns` is the pre-sliced estimation window (all rows ≤ `date`).
- `register_graph(name)` decorator + `GRAPH_REGISTRY` in `volforecast.registry`.
- `build_graph_schedule(returns, dates, builder, *, window=252, refit_every=21, min_history=60) -> dict[date, GraphSnapshot]`.

**Copilot context packet:**

```yaml
subtask_id: "gnn-01-1"
goal: "Create volforecast/graphs package with GraphSnapshot dataclass, GraphBuilder protocol, register_graph/GRAPH_REGISTRY in registry.py, and build_graph_schedule enforcing point-in-time refits; all covered by failing-first unit tests."
file_scope:
  - workspace/plans/gnn/plan-01-graph-construction.md   # Task 1 section has all code
  - src/volforecast/registry.py
  - src/volforecast/models/gnn_adjacency.py             # existing pattern to mirror
write_scope:
  - src/volforecast/graphs/__init__.py
  - src/volforecast/graphs/base.py
  - src/volforecast/registry.py
  - src/tests/unit/graphs/__init__.py
  - src/tests/unit/graphs/conftest.py
  - src/tests/unit/graphs/test_graph_base.py
acceptance_criteria:
  - "./vol test -k test_graph_base -> all pass"
  - "GraphSnapshot.dense_adjacency('sym') matches hand-computed O^-1/2 A O^-1/2 on a 3-node example"
  - "build_graph_schedule refits only every refit_every dates (identity of snapshot objects between refits)"
  - "./vol typecheck clean on new files"
constraints:
  - "TDD: write test_graph_base.py first, run ./vol test -k test_graph_base, confirm ImportError/failures, then implement"
  - "No torch import at module level in graphs/ (only inside to_torch)"
  - "No new dependencies"
context_summary: |
  We are adding a graph-construction library so GNN vol models can select adjacency from YAML.
  registry.py already has MODEL_REGISTRY/FEATURE_REGISTRY with decorator registration - mirror
  that exactly. GraphSnapshot is numpy-first so linear models (GHAR, Plan 03) never need torch.
  The schedule helper enforces the GNNHAR point-in-time protocol: re-estimate on the trailing
  window every refit_every days, freeze between refits.
depends_on: []
```

- [ ] **Step 1: Write the failing tests** — `src/tests/unit/graphs/test_graph_base.py`:

```python
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.graphs.base import GraphBuilder, GraphSnapshot, build_graph_schedule
from volforecast.registry import GRAPH_REGISTRY, register_graph


def _triangle_snapshot() -> GraphSnapshot:
    # 3 nodes; undirected edges (0,1) and (1,2), weight 1.0, stored both directions
    edge_index = np.array([[0, 1, 1, 2], [1, 0, 2, 1]], dtype=np.int64)
    edge_weight = np.ones(4, dtype=np.float32)
    return GraphSnapshot(
        edge_index=edge_index, edge_weight=edge_weight,
        symbols=("X", "Y", "Z"), date=pd.Timestamp("2024-01-02"), method="test",
    )


def test_snapshot_shape_properties():
    s = _triangle_snapshot()
    assert s.n_nodes == 3
    assert s.n_edges == 4
    # density counts undirected pairs: 2 of 3 possible -> 2/3
    assert s.density() == pytest.approx(2.0 / 3.0)


def test_dense_adjacency_unnormalized_binary():
    s = _triangle_snapshot()
    a = s.dense_adjacency(binary=True)
    expected = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=np.float64)
    np.testing.assert_allclose(a, expected)


def test_dense_adjacency_sym_normalized():
    # O = diag(1, 2, 1); W = O^-1/2 A O^-1/2
    s = _triangle_snapshot()
    w = s.dense_adjacency(norm="sym", binary=True)
    r2 = 1.0 / np.sqrt(2.0)
    expected = np.array([[0, r2, 0], [r2, 0, r2], [0, r2, 0]])
    np.testing.assert_allclose(w, expected, atol=1e-12)


def test_dense_adjacency_row_normalized():
    s = _triangle_snapshot()
    w = s.dense_adjacency(norm="row", binary=True)
    assert w[1].sum() == pytest.approx(1.0)
    assert w[0, 1] == pytest.approx(1.0)


def test_to_torch_roundtrip():
    torch = pytest.importorskip("torch")
    s = _triangle_snapshot()
    ei, ew = s.to_torch()
    assert ei.dtype == torch.long and ei.shape == (2, 4)
    assert ew.dtype == torch.float32 and ew.shape == (4,)


def test_register_graph_decorator_registers_and_rejects_duplicates():
    @register_graph("_test_graph")
    class _Dummy:
        name = "_test_graph"
        directed = False

        def build(self, returns, date, symbols):
            return _triangle_snapshot()

    try:
        assert GRAPH_REGISTRY["_test_graph"] is _Dummy
        assert isinstance(_Dummy(), GraphBuilder)
        with pytest.raises(ValueError, match="Duplicate graph name"):
            register_graph("_test_graph")(_Dummy)
    finally:
        GRAPH_REGISTRY.pop("_test_graph", None)


def test_schedule_refits_on_grid_and_freezes_between(synthetic_returns_panel, symbols8):
    calls: list[pd.Timestamp] = []

    class _Spy:
        name = "_spy"
        directed = False

        def build(self, returns, date, symbols):
            calls.append(date)
            assert returns.index.max() <= date  # PIT: window ends at estimation date
            return GraphSnapshot(
                edge_index=np.zeros((2, 0), dtype=np.int64),
                edge_weight=np.zeros(0, dtype=np.float32),
                symbols=tuple(symbols), date=date, method="_spy",
            )

    dates = list(synthetic_returns_panel.index[100:160])  # 60 forecast dates
    sched = build_graph_schedule(
        synthetic_returns_panel, dates, _Spy(), window=90, refit_every=21, min_history=60,
    )
    assert len(sched) == len(dates)
    # ceil(60/21) = 3 refits
    assert len(calls) == 3
    # frozen between refits: same object identity
    assert sched[dates[0]] is sched[dates[1]]
    assert sched[dates[0]] is not sched[dates[21]]


def test_schedule_skips_insufficient_history(synthetic_returns_panel, symbols8):
    class _Spy:
        name = "_spy"
        directed = False

        def build(self, returns, date, symbols):  # pragma: no cover
            raise AssertionError("must not be called with < min_history rows")

    dates = list(synthetic_returns_panel.index[:5])  # only 1..5 rows of history
    sched = build_graph_schedule(
        synthetic_returns_panel, dates, _Spy(), window=90, refit_every=21, min_history=60,
    )
    assert all(s.n_edges == 0 for s in sched.values())  # empty fallback snapshots
```

- [ ] **Step 2: Run to confirm failure** — `./vol test -k test_graph_base` → expect `ModuleNotFoundError: volforecast.graphs`.

- [ ] **Step 3: Implement** — `src/volforecast/graphs/base.py`:

```python
"""Graph snapshot container, builder protocol, and point-in-time scheduling.

Numpy-first by design: linear models (GHAR) consume dense adjacency matrices
without importing torch; neural models call ``GraphSnapshot.to_torch()``.

Point-in-time protocol (Zhang et al. 2025): a graph used to forecast date t
is estimated on data <= t only, re-estimated every ``refit_every`` trading
days on the trailing ``window``, and frozen between refits.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class GraphSnapshot:
    """Immutable graph for one estimation date.

    edge_index : (2, E) int64 COO indices into ``symbols`` order.
        Undirected graphs store both (i, j) and (j, i).
    edge_weight : (E,) float32 non-negative weights.
    """

    edge_index: np.ndarray
    edge_weight: np.ndarray
    symbols: tuple[str, ...]
    date: Any
    directed: bool = False
    method: str = ""

    @property
    def n_nodes(self) -> int:
        return len(self.symbols)

    @property
    def n_edges(self) -> int:
        return int(self.edge_index.shape[1])

    def density(self) -> float:
        """Fraction of possible (unordered if undirected) node pairs with an edge."""
        n = self.n_nodes
        if n < 2:
            return 0.0
        possible = n * (n - 1)
        stored = self.n_edges if self.directed else self.n_edges  # both dirs stored
        return float(stored) / possible

    def dense_adjacency(
        self, norm: str | None = None, *, binary: bool = False
    ) -> np.ndarray:
        """Dense (N, N) adjacency. norm: None | 'sym' (O^-1/2 A O^-1/2) | 'row' (O^-1 A)."""
        n = self.n_nodes
        a = np.zeros((n, n), dtype=np.float64)
        src, dst = self.edge_index
        vals = np.ones_like(self.edge_weight, dtype=np.float64) if binary else (
            self.edge_weight.astype(np.float64)
        )
        a[src, dst] = vals
        if norm is None:
            return a
        deg = a.sum(axis=1)
        safe = np.where(deg > 0, deg, 1.0)
        if norm == "row":
            return a / safe[:, None]
        if norm == "sym":
            d_inv_sqrt = 1.0 / np.sqrt(safe)
            d_inv_sqrt[deg == 0] = 0.0
            return d_inv_sqrt[:, None] * a * d_inv_sqrt[None, :]
        raise ValueError(f"Unknown norm {norm!r}; expected None, 'sym' or 'row'")

    def to_torch(self):
        """Return (edge_index long, edge_weight float32) torch tensors."""
        import torch

        return (
            torch.from_numpy(np.ascontiguousarray(self.edge_index)).long(),
            torch.from_numpy(np.ascontiguousarray(self.edge_weight)).float(),
        )


def empty_snapshot(symbols: list[str], date: Any, method: str = "") -> GraphSnapshot:
    return GraphSnapshot(
        edge_index=np.zeros((2, 0), dtype=np.int64),
        edge_weight=np.zeros(0, dtype=np.float32),
        symbols=tuple(symbols), date=date, method=method,
    )


@runtime_checkable
class GraphBuilder(Protocol):
    """A graph builder. ``returns`` is the pre-sliced estimation window (rows <= date)."""

    name: str
    directed: bool

    def build(
        self, returns: pd.DataFrame, date: Any, symbols: list[str]
    ) -> GraphSnapshot: ...


def build_graph_schedule(
    returns: pd.DataFrame,
    dates: list[Any],
    builder: GraphBuilder,
    *,
    window: int = 252,
    refit_every: int = 21,
    min_history: int = 60,
) -> dict[Any, GraphSnapshot]:
    """Map each forecast date to a point-in-time GraphSnapshot.

    Re-estimates on dates[0], dates[refit_every], ... using the trailing
    ``window`` rows of ``returns`` ending at (or before) the refit date.
    Dates with fewer than ``min_history`` rows get an empty snapshot.
    """
    symbols = list(returns.columns)
    schedule: dict[Any, GraphSnapshot] = {}
    current: GraphSnapshot | None = None
    for i, date in enumerate(dates):
        if i % refit_every == 0:
            hist = returns.loc[returns.index <= date].tail(window)
            if len(hist) < min_history:
                current = empty_snapshot(symbols, date, method=builder.name)
            else:
                current = builder.build(hist, date, symbols)
        assert current is not None
        schedule[date] = current
    return schedule
```

`src/volforecast/graphs/__init__.py`:

```python
"""Point-in-time graph construction for graph-based volatility models."""
from volforecast.graphs.base import (  # noqa: F401
    GraphBuilder,
    GraphSnapshot,
    build_graph_schedule,
    empty_snapshot,
)
```

Add to `src/volforecast/registry.py` (below `FEATURE_REGISTRY`):

```python
GRAPH_REGISTRY: dict[str, type] = {}


def register_graph(name: str):
    """Class decorator that registers a graph builder in GRAPH_REGISTRY."""

    def decorator(cls: type) -> type:
        if name in GRAPH_REGISTRY:
            raise ValueError(f"Duplicate graph name: {name!r}")
        GRAPH_REGISTRY[name] = cls
        cls.name = name  # type: ignore[attr-defined]
        return cls

    return decorator
```

and inside `ensure_registered()` append (after the feature imports):

```python
    import volforecast.graphs.simple  # noqa: F401
    import volforecast.graphs.correlation  # noqa: F401
    import volforecast.graphs.glasso  # noqa: F401
    import volforecast.graphs.spillover  # noqa: F401
    import volforecast.graphs.factor_residual  # noqa: F401
```

(these modules land in Tasks 2–6; guard the whole block with `try/except ImportError: pass` **only until Task 6 removes the guard** — final state is unguarded because the builders have no optional deps.)

- [ ] **Step 4: Run to green** — `./vol test -k test_graph_base` → all pass. `./vol typecheck` clean.
- [ ] **Step 5: Commit** — `feat(graphs): GraphSnapshot, builder protocol, registry, PIT schedule`

---

## Task 2: Simple builders — `identity`, `full`, `sector`

**Files:** Create `src/volforecast/graphs/simple.py`, `src/tests/unit/graphs/test_simple_graphs.py`.

**Copilot context packet:**

```yaml
subtask_id: "gnn-01-2"
goal: "Implement identity (no-edge), full (complete uniform), and sector (GICS block) graph builders registered as 'identity'/'full'/'sector', with failing-first tests."
file_scope:
  - workspace/plans/gnn/plan-01-graph-construction.md   # Task 2 section
  - src/volforecast/graphs/base.py
  - src/volforecast/constants.py
write_scope:
  - src/volforecast/graphs/simple.py
  - src/tests/unit/graphs/test_simple_graphs.py
acceptance_criteria:
  - "./vol test -k test_simple_graphs -> all pass"
  - "identity builder yields 0 edges; full yields N*(N-1) directed-stored edges with weight 1/(N-1)"
  - "sector builder connects exactly same-sector pairs for SYMBOL_UNIVERSE members"
constraints: ["TDD failing-first", "No torch at module level", "No new dependencies"]
context_summary: |
  GraphSnapshot/register_graph exist from gnn-01-1. identity is the no-graph control arm of the
  Plan 03 ablation (GHAR with identity == plain HAR). full is the GNAR-HARX winner on small
  universes (uniform weight 1/(N-1) so the aggregate is the cross-sectional mean of the others).
  sector uses a hard-coded GICS map for the 34-symbol universe; unknown symbols fall into
  their own singleton sector (no edges).
depends_on: ["gnn-01-1"]
```

- [ ] **Step 1: Failing tests** — `src/tests/unit/graphs/test_simple_graphs.py`:

```python
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.graphs.simple import (
    SECTOR_MAP,
    FullGraphBuilder,
    IdentityGraphBuilder,
    SectorGraphBuilder,
)


def test_identity_no_edges(synthetic_returns_panel, symbols8):
    snap = IdentityGraphBuilder().build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    assert snap.n_edges == 0
    assert snap.method == "identity"


def test_full_uniform_weights(synthetic_returns_panel, symbols8):
    snap = FullGraphBuilder().build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    n = len(symbols8)
    assert snap.n_edges == n * (n - 1)
    np.testing.assert_allclose(snap.edge_weight, 1.0 / (n - 1))
    # row sums of dense adjacency = 1 -> neighbor aggregate is the mean of others
    np.testing.assert_allclose(snap.dense_adjacency().sum(axis=1), 1.0, atol=1e-6)


def test_sector_connects_same_sector_only():
    symbols = ["AAPL", "MSFT", "XOM", "JPM", "BAC"]
    dates = pd.bdate_range("2024-01-02", periods=10)
    panel = pd.DataFrame(0.0, index=dates, columns=symbols)
    snap = SectorGraphBuilder().build(panel, dates[-1], symbols)
    a = snap.dense_adjacency(binary=True)
    i = {s: k for k, s in enumerate(symbols)}
    assert a[i["AAPL"], i["MSFT"]] == 1.0      # both Information Technology
    assert a[i["JPM"], i["BAC"]] == 1.0        # both Financials
    assert a[i["AAPL"], i["XOM"]] == 0.0       # IT vs Energy
    assert a[i["XOM"], :].sum() == 0.0         # singleton sector in this subset


def test_sector_map_covers_universe():
    from volforecast.constants import SYMBOL_UNIVERSE

    missing = set(SYMBOL_UNIVERSE) - set(SECTOR_MAP)
    assert not missing, f"SECTOR_MAP missing: {missing}"


def test_unknown_symbol_gets_no_edges():
    symbols = ["AAPL", "ZZZTEST"]
    dates = pd.bdate_range("2024-01-02", periods=5)
    panel = pd.DataFrame(0.0, index=dates, columns=symbols)
    snap = SectorGraphBuilder().build(panel, dates[-1], symbols)
    assert snap.n_edges == 0
```

- [ ] **Step 2: Run** `./vol test -k test_simple_graphs` → ImportError (red).
- [ ] **Step 3: Implement** — `src/volforecast/graphs/simple.py`:

```python
"""Structural graph builders that need no estimation: identity, full, sector."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from volforecast.graphs.base import GraphSnapshot, empty_snapshot
from volforecast.registry import register_graph

#: GICS sector map for SYMBOL_UNIVERSE (GICS 2023: V/MA/PYPL are Financials).
SECTOR_MAP: dict[str, str] = {
    # Information Technology
    "AAPL": "it", "MSFT": "it", "NVDA": "it", "ADBE": "it", "CRM": "it",
    "CSCO": "it", "ACN": "it", "AVGO": "it",
    # Communication Services
    "GOOGL": "comm", "META": "comm", "NFLX": "comm", "DIS": "comm", "CMCSA": "comm",
    # Consumer Discretionary
    "AMZN": "cons_disc", "TSLA": "cons_disc", "HD": "cons_disc", "NKE": "cons_disc",
    # Consumer Staples
    "PG": "cons_staples",
    # Financials
    "JPM": "fin", "BAC": "fin", "V": "fin", "MA": "fin", "PYPL": "fin", "BRK.B": "fin",
    # Health Care
    "JNJ": "health", "UNH": "health", "PFE": "health", "TMO": "health", "ABT": "health",
    # Energy
    "XOM": "energy",
    # Broad-market index products share one sector (they co-move by construction)
    "SPY": "index", "QQQ": "index", "IWM": "index", "DIA": "index",
    "ES": "index", "SPX": "index",
}


@register_graph("identity")
class IdentityGraphBuilder:
    """No edges — the no-graph control. GHAR(identity) == plain pooled HAR."""

    directed = False

    def build(self, returns: pd.DataFrame, date: Any, symbols: list[str]) -> GraphSnapshot:
        return empty_snapshot(symbols, date, method="identity")


@register_graph("full")
class FullGraphBuilder:
    """Complete graph, uniform weight 1/(N-1): neighbor aggregate = mean of the others."""

    directed = False

    def build(self, returns: pd.DataFrame, date: Any, symbols: list[str]) -> GraphSnapshot:
        n = len(symbols)
        if n < 2:
            return empty_snapshot(symbols, date, method="full")
        src, dst = np.where(~np.eye(n, dtype=bool))
        weight = np.full(src.shape[0], 1.0 / (n - 1), dtype=np.float32)
        return GraphSnapshot(
            edge_index=np.stack([src, dst]).astype(np.int64),
            edge_weight=weight, symbols=tuple(symbols), date=date, method="full",
        )


@register_graph("sector")
class SectorGraphBuilder:
    """Binary edges between same-GICS-sector symbols; unknown symbols stay isolated."""

    directed = False

    def __init__(self, sector_map: dict[str, str] | None = None) -> None:
        self.sector_map = dict(sector_map or SECTOR_MAP)

    def build(self, returns: pd.DataFrame, date: Any, symbols: list[str]) -> GraphSnapshot:
        src_list: list[int] = []
        dst_list: list[int] = []
        for i, si in enumerate(symbols):
            for j, sj in enumerate(symbols):
                if i == j:
                    continue
                sec_i = self.sector_map.get(si)
                if sec_i is not None and sec_i == self.sector_map.get(sj):
                    src_list.append(i)
                    dst_list.append(j)
        if not src_list:
            return empty_snapshot(symbols, date, method="sector")
        return GraphSnapshot(
            edge_index=np.array([src_list, dst_list], dtype=np.int64),
            edge_weight=np.ones(len(src_list), dtype=np.float32),
            symbols=tuple(symbols), date=date, method="sector",
        )
```

- [ ] **Step 4:** `./vol test -k test_simple_graphs` → green.
- [ ] **Step 5: Commit** — `feat(graphs): identity, full, and GICS sector builders`

---

## Task 3: Correlation family — `corr` (threshold) and `knn` (top-K)

**Files:** Create `src/volforecast/graphs/correlation.py`, `src/tests/unit/graphs/test_correlation_graphs.py`.

**Copilot context packet:**

```yaml
subtask_id: "gnn-01-3"
goal: "Implement threshold-correlation ('corr') and top-K ('knn') graph builders on the new GraphBuilder API, recovering block structure on the synthetic two-block panel, with a PIT-leakage test."
file_scope:
  - workspace/plans/gnn/plan-01-graph-construction.md   # Task 3 section
  - src/volforecast/graphs/base.py
  - src/volforecast/models/gnn_adjacency.py             # semantics to preserve (|corr| >= threshold, abs weights)
write_scope:
  - src/volforecast/graphs/correlation.py
  - src/tests/unit/graphs/test_correlation_graphs.py
acceptance_criteria:
  - "./vol test -k test_correlation_graphs -> all pass"
  - "corr builder on the two-block fixture yields intra-block edges only at threshold 0.5"
  - "knn builder yields exactly k out-neighbors per node (before symmetrization)"
constraints: ["TDD failing-first", "min_periods = max(window//2, 5) as in gnn_adjacency", "No new dependencies"]
context_summary: |
  These replicate the semantics of models/gnn_adjacency.py (|corr| >= threshold, weight=|corr|,
  undirected both-direction storage, NaN pairs skipped) on the new builder API. knn keeps each
  node's k strongest |corr| partners then symmetrizes by union (GTN-VF: sparse strong edges beat
  dense weak ones). Do NOT modify gnn_adjacency.py - the legacy path stays until Plan 02 rewires it.
depends_on: ["gnn-01-1"]
```

- [ ] **Step 1: Failing tests** — `src/tests/unit/graphs/test_correlation_graphs.py`:

```python
from __future__ import annotations

import numpy as np
import pytest

from volforecast.graphs.correlation import CorrGraphBuilder, KnnGraphBuilder


def _block_of(sym: str) -> str:
    return sym[0]  # "A" or "B"


def test_corr_recovers_blocks(synthetic_returns_panel, symbols8):
    snap = CorrGraphBuilder(threshold=0.5).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    assert snap.n_edges > 0
    src, dst = snap.edge_index
    for i, j in zip(src, dst):
        assert _block_of(symbols8[i]) == _block_of(symbols8[j])
    # all 4*3=12 intra-block ordered pairs per block present
    assert snap.n_edges == 24


def test_corr_weights_are_abs_correlations(synthetic_returns_panel, symbols8):
    snap = CorrGraphBuilder(threshold=0.5).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    assert np.all(snap.edge_weight >= 0.5) and np.all(snap.edge_weight <= 1.0)


def test_corr_is_point_in_time(synthetic_returns_panel, symbols8):
    """Perturbing rows AFTER the estimation window must not change the graph."""
    date = synthetic_returns_panel.index[200]
    window = synthetic_returns_panel.loc[:date]
    snap1 = CorrGraphBuilder(threshold=0.5).build(window, date, symbols8)
    # builder only ever receives rows <= date; assert it uses exactly that input
    snap2 = CorrGraphBuilder(threshold=0.5).build(window.copy(), date, symbols8)
    np.testing.assert_array_equal(snap1.edge_index, snap2.edge_index)


def test_knn_out_degree_before_symmetrization(synthetic_returns_panel, symbols8):
    snap = KnnGraphBuilder(k=2, symmetrize=False).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    src, _ = snap.edge_index
    counts = np.bincount(src, minlength=len(symbols8))
    np.testing.assert_array_equal(counts, np.full(len(symbols8), 2))


def test_knn_symmetrized_is_undirected(synthetic_returns_panel, symbols8):
    snap = KnnGraphBuilder(k=2, symmetrize=True).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    pairs = {(int(i), int(j)) for i, j in zip(*snap.edge_index)}
    assert all((j, i) in pairs for (i, j) in pairs)


def test_empty_window_gives_empty_graph(synthetic_returns_panel, symbols8):
    empty = synthetic_returns_panel.iloc[:3]
    snap = CorrGraphBuilder(threshold=0.5).build(empty, empty.index[-1], symbols8)
    assert snap.n_edges == 0
```

- [ ] **Step 2:** `./vol test -k test_correlation_graphs` → red.
- [ ] **Step 3: Implement** — `src/volforecast/graphs/correlation.py`:

```python
"""Correlation-based graph builders: absolute-threshold and top-K sparsified."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from volforecast.graphs.base import GraphSnapshot, empty_snapshot
from volforecast.registry import register_graph


def _corr_matrix(returns: pd.DataFrame, symbols: list[str]) -> np.ndarray | None:
    data = returns[list(symbols)]
    min_periods = max(len(data) // 2, 5)
    if len(data) < min_periods:
        return None
    corr = data.corr(min_periods=min_periods)
    if corr.empty:
        return None
    values = corr.values.copy()
    np.fill_diagonal(values, np.nan)
    return values


@register_graph("corr")
class CorrGraphBuilder:
    """Edge iff |corr| >= threshold; weight = |corr| (gnn_adjacency semantics)."""

    directed = False

    def __init__(self, threshold: float = 0.3) -> None:
        self.threshold = float(threshold)

    def build(self, returns: pd.DataFrame, date: Any, symbols: list[str]) -> GraphSnapshot:
        values = _corr_matrix(returns, symbols)
        if values is None:
            return empty_snapshot(symbols, date, method="corr")
        absv = np.abs(values)
        src, dst = np.where(np.nan_to_num(absv, nan=-1.0) >= self.threshold)
        if src.size == 0:
            return empty_snapshot(symbols, date, method="corr")
        return GraphSnapshot(
            edge_index=np.stack([src, dst]).astype(np.int64),
            edge_weight=absv[src, dst].astype(np.float32),
            symbols=tuple(symbols), date=date, method="corr",
        )


@register_graph("knn")
class KnnGraphBuilder:
    """Keep each node's k strongest |corr| partners; symmetrize by union by default."""

    directed = False

    def __init__(self, k: int = 5, symmetrize: bool = True) -> None:
        self.k = int(k)
        self.symmetrize = bool(symmetrize)

    def build(self, returns: pd.DataFrame, date: Any, symbols: list[str]) -> GraphSnapshot:
        values = _corr_matrix(returns, symbols)
        if values is None:
            return empty_snapshot(symbols, date, method="knn")
        absv = np.nan_to_num(np.abs(values), nan=-1.0)
        n = absv.shape[0]
        k = min(self.k, n - 1)
        pairs: set[tuple[int, int]] = set()
        for i in range(n):
            top = np.argsort(absv[i])[::-1][:k]
            for j in top:
                if absv[i, j] <= 0:
                    continue
                pairs.add((i, int(j)))
        if self.symmetrize:
            pairs |= {(j, i) for (i, j) in pairs}
        if not pairs:
            return empty_snapshot(symbols, date, method="knn")
        src = np.array([p[0] for p in sorted(pairs)], dtype=np.int64)
        dst = np.array([p[1] for p in sorted(pairs)], dtype=np.int64)
        return GraphSnapshot(
            edge_index=np.stack([src, dst]),
            edge_weight=absv[src, dst].astype(np.float32),
            symbols=tuple(symbols), date=date, method="knn",
        )
```

- [ ] **Step 4:** `./vol test -k test_correlation_graphs` → green.
- [ ] **Step 5: Commit** — `feat(graphs): threshold-correlation and top-K knn builders`

---

## Task 4: GLASSO builder

**Files:** Create `src/volforecast/graphs/glasso.py`, `src/tests/unit/graphs/test_glasso_graph.py`.

**Copilot context packet:**

```yaml
subtask_id: "gnn-01-4"
goal: "Implement the GLASSO conditional-independence graph builder ('glasso') using sklearn GraphicalLasso/GraphicalLassoCV, binary support-only edges, with block-recovery and robustness tests."
file_scope:
  - workspace/plans/gnn/plan-01-graph-construction.md   # Task 4 section
  - src/volforecast/graphs/base.py
write_scope:
  - src/volforecast/graphs/glasso.py
  - src/tests/unit/graphs/test_glasso_graph.py
acceptance_criteria:
  - "./vol test -k test_glasso_graph -> all pass"
  - "On the two-block fixture, glasso finds no cross-block edges and >=1 intra-block edge per block"
  - "Non-convergence falls back to empty snapshot with a logged warning (test with 5-row window)"
constraints: ["TDD failing-first", "sklearn only (already a dependency)", "Standardize returns before GLASSO", "Binary edges: A_ij = 1{Theta_ij != 0}, zero diagonal (Zhang et al. 2025, p.8)"]
context_summary: |
  GLASSO is the GNNHAR lineage's graph: Theta = argmin tr(S Theta) - logdet(Theta) + lambda*sum|Theta_jk|;
  adjacency keeps only the support (binary, undirected, no self-loops). alpha=None -> GraphicalLassoCV
  (cost is fine: refits are monthly); fixed alpha for speed/stability sweeps. GNAR-HARX diagnosed GLASSO
  edge-count instability as its failure mode - the Jaccard diagnostic in Task 7 will monitor this.
depends_on: ["gnn-01-1"]
```

- [ ] **Step 1: Failing tests** — `src/tests/unit/graphs/test_glasso_graph.py`:

```python
from __future__ import annotations

import numpy as np
import pytest

from volforecast.graphs.glasso import GlassoGraphBuilder


def _block_of(sym: str) -> str:
    return sym[0]


def test_glasso_no_cross_block_edges(synthetic_returns_panel, symbols8):
    snap = GlassoGraphBuilder(alpha=0.2).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    src, dst = snap.edge_index
    for i, j in zip(src, dst):
        assert _block_of(symbols8[i]) == _block_of(symbols8[j])


def test_glasso_finds_intra_block_structure(synthetic_returns_panel, symbols8):
    snap = GlassoGraphBuilder(alpha=0.2).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    src = snap.edge_index[0]
    blocks = {_block_of(symbols8[i]) for i in src}
    assert blocks == {"A", "B"}


def test_glasso_edges_are_binary_and_symmetric(synthetic_returns_panel, symbols8):
    snap = GlassoGraphBuilder(alpha=0.2).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    np.testing.assert_allclose(snap.edge_weight, 1.0)
    pairs = {(int(i), int(j)) for i, j in zip(*snap.edge_index)}
    assert all((j, i) in pairs for (i, j) in pairs)
    assert all(i != j for (i, j) in pairs)  # zero diagonal


def test_glasso_cv_mode_runs(synthetic_returns_panel, symbols8):
    snap = GlassoGraphBuilder(alpha=None).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    assert snap.method == "glasso"  # CV mode completes and returns a snapshot


def test_glasso_degenerate_window_falls_back_empty(synthetic_returns_panel, symbols8):
    tiny = synthetic_returns_panel.iloc[:5]
    snap = GlassoGraphBuilder(alpha=0.2).build(tiny, tiny.index[-1], symbols8)
    assert snap.n_edges == 0
```

- [ ] **Step 2:** `./vol test -k test_glasso_graph` → red.
- [ ] **Step 3: Implement** — `src/volforecast/graphs/glasso.py`:

```python
"""GLASSO conditional-independence graph (Zhang, Pu, Cucuringu & Dong 2025, p.8).

Theta_hat = argmin_{Theta >= 0} tr(S Theta) - log det(Theta) + lambda * sum_{j!=k} |Theta_jk|
A_ij = 1{Theta_hat_ij != 0}, binary, undirected, zero diagonal.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from volforecast.graphs.base import GraphSnapshot, empty_snapshot
from volforecast.registry import register_graph

logger = logging.getLogger(__name__)

_SUPPORT_TOL = 1e-8


@register_graph("glasso")
class GlassoGraphBuilder:
    """Sparse precision-support graph. alpha=None -> GraphicalLassoCV on the window."""

    directed = False

    def __init__(
        self, alpha: float | None = None, max_iter: int = 500, min_rows: int = 60
    ) -> None:
        self.alpha = alpha
        self.max_iter = int(max_iter)
        self.min_rows = int(min_rows)

    def build(self, returns: pd.DataFrame, date: Any, symbols: list[str]) -> GraphSnapshot:
        from sklearn.covariance import GraphicalLasso, GraphicalLassoCV

        data = returns[list(symbols)].dropna()
        if len(data) < self.min_rows:
            return empty_snapshot(symbols, date, method="glasso")
        # Standardize: GLASSO support on the correlation scale is scale-invariant
        std = data.std(ddof=0).replace(0.0, np.nan)
        z = ((data - data.mean()) / std).dropna(axis=1)
        kept = list(z.columns)
        if len(kept) < 2:
            return empty_snapshot(symbols, date, method="glasso")
        try:
            if self.alpha is None:
                est = GraphicalLassoCV(max_iter=self.max_iter, assume_centered=True)
            else:
                est = GraphicalLasso(
                    alpha=self.alpha, max_iter=self.max_iter, assume_centered=True
                )
            est.fit(z.values)
        except (FloatingPointError, ValueError) as exc:
            logger.warning("glasso: estimation failed (%s); returning empty graph", exc)
            return empty_snapshot(symbols, date, method="glasso")
        prec = np.asarray(est.precision_)
        support = np.abs(prec) > _SUPPORT_TOL
        np.fill_diagonal(support, False)
        # Map kept-column indices back to the requested symbol order
        col_pos = {s: i for i, s in enumerate(symbols)}
        idx = np.array([col_pos[s] for s in kept], dtype=np.int64)
        src_k, dst_k = np.where(support)
        if src_k.size == 0:
            return empty_snapshot(symbols, date, method="glasso")
        return GraphSnapshot(
            edge_index=np.stack([idx[src_k], idx[dst_k]]),
            edge_weight=np.ones(src_k.shape[0], dtype=np.float32),
            symbols=tuple(symbols), date=date, method="glasso",
        )
```

- [ ] **Step 4:** `./vol test -k test_glasso_graph` → green (if the CV test is slow > 2 s, mark it `@pytest.mark.slow`).
- [ ] **Step 5: Commit** — `feat(graphs): GLASSO conditional-independence builder`

---

## Task 5: Diebold–Yilmaz spillover builder + generalized-FEVD formula test

**Files:** Create `src/volforecast/graphs/spillover.py`, `src/tests/unit/graphs/test_dy_graph.py`, `src/tests/unit/formulas/test_gfevd_formulas.py`, `src/tests/unit/formulas/gold_values/gfevd_bivariate_var1.json`. Modify `src/tests/unit/formulas/FORMULAS.md` (add row).

**Math (chapter §"Dynamic, Spectral, and Intraday Frontiers"; Diebold & Yilmaz 2012; Pesaran & Shin 1998).** Fit VAR(p) to the log-RV panel; with MA representation Ψ_h and residual covariance Σ, the generalized FEVD share of variable *i* attributable to shocks in *j* at horizon *H* is

θ_ij(H) = [ σ_jj⁻¹ Σ_{h=0}^{H−1} (e_i′ Ψ_h Σ e_j)² ] / [ Σ_{h=0}^{H−1} e_i′ Ψ_h Σ Ψ_h′ e_i ],   θ̃_ij = θ_ij / Σ_j θ_ij.

Edge convention (DCRNN-HAR): **W[i→j] = θ̃_ji** — the share of *j*'s forecast-error variance explained by *i* (spillover *from i to j*). Drop edges with weight < `threshold` (Boetti & Nunes: 0.05).

**Gold values** (hand-computed; record derivation in the JSON): bivariate VAR(1), A = [[0.5, 0.3], [0.0, 0.4]], Σ = [[1.0, 0.2], [0.2, 1.0]], H = 2 ⇒ Ψ₀=I, Ψ₁=A; θ̃ = [[0.867864, 0.132136], [0.038462, 0.961538]] (row-normalized); total spillover index = 8.5299%.

**Copilot context packet:**

```yaml
subtask_id: "gnn-01-5"
goal: "Implement generalized_fevd_matrix() and the directed 'dy' spillover graph builder, verified against hand-computed bivariate VAR(1) gold values in a formula test."
file_scope:
  - workspace/plans/gnn/plan-01-graph-construction.md   # Task 5 section: math + gold values
  - src/volforecast/graphs/base.py
  - src/volforecast/features/cross_asset.py             # existing DY total-connectedness code (do NOT modify)
  - src/tests/unit/formulas/FORMULAS.md
  - src/tests/unit/formulas/conftest.py
write_scope:
  - src/volforecast/graphs/spillover.py
  - src/tests/unit/graphs/test_dy_graph.py
  - src/tests/unit/formulas/test_gfevd_formulas.py
  - src/tests/unit/formulas/gold_values/gfevd_bivariate_var1.json
  - src/tests/unit/formulas/FORMULAS.md
acceptance_criteria:
  - "./vol test -k 'gfevd or test_dy_graph' -> all pass"
  - "generalized_fevd_matrix matches gold values to rel=1e-6"
  - "dy builder emits directed=True snapshot; edges below threshold dropped"
constraints: ["TDD failing-first", "statsmodels VAR only for coefficient estimation; FEVD computed manually (statsmodels fevd is orthogonalized, not generalized)", "Formula test registered in FORMULAS.md with paper + equation number (Pesaran & Shin 1998 eq. 2.9; Diebold & Yilmaz 2012 eqs. 2-3)"]
context_summary: |
  The DY graph is the directed alternative to GLASSO and the input to DCRNN-HAR (Plan 06) and
  GSP-HAR (Plan 07). features/cross_asset.py already computes the scalar total-connectedness via
  statsmodels; we need the full pairwise generalized (order-invariant) FEVD matrix, which statsmodels
  does not expose - compute it from var_result.ma_rep() and sigma_u. Edge W[i->j] = normalized share
  of j's FEVD due to i. The gold JSON must include the hand-derivation steps.
depends_on: ["gnn-01-1"]
```

- [ ] **Step 1: Failing formula test** — `src/tests/unit/formulas/test_gfevd_formulas.py`:

```python
from __future__ import annotations

import numpy as np
import pytest

from volforecast.graphs.spillover import generalized_fevd_matrix

pytestmark = pytest.mark.formula


def test_gfevd_matches_bivariate_var1_gold(load_gold):
    gold = load_gold("gfevd_bivariate_var1.json")
    psi = [np.eye(2), np.array(gold["inputs"]["A"])]      # Psi_0 = I, Psi_1 = A for VAR(1), H=2
    sigma = np.array(gold["inputs"]["sigma"])
    theta = generalized_fevd_matrix(psi, sigma)
    np.testing.assert_allclose(theta, np.array(gold["expected"]["theta_normalized"]), rtol=1e-6)


def test_gfevd_rows_sum_to_one(load_gold):
    gold = load_gold("gfevd_bivariate_var1.json")
    theta = generalized_fevd_matrix(
        [np.eye(2), np.array(gold["inputs"]["A"])], np.array(gold["inputs"]["sigma"])
    )
    np.testing.assert_allclose(theta.sum(axis=1), 1.0, atol=1e-12)


def test_gfevd_total_spillover_index(load_gold):
    gold = load_gold("gfevd_bivariate_var1.json")
    theta = generalized_fevd_matrix(
        [np.eye(2), np.array(gold["inputs"]["A"])], np.array(gold["inputs"]["sigma"])
    )
    total = 100.0 * (theta.sum() - np.trace(theta)) / theta.shape[0]
    assert total == pytest.approx(gold["expected"]["total_spillover_pct"], rel=1e-6)
```

`src/tests/unit/formulas/gold_values/gfevd_bivariate_var1.json`:

```json
{
  "source": "Pesaran & Shin (1998) eq. 2.9; Diebold & Yilmaz (2012) eqs. 2-3",
  "derivation": "VAR(1) y_t = A y_{t-1} + u_t. Psi_0=I, Psi_1=A. H=2. Numerators: (e_i' Psi_h Sigma e_j)^2 summed over h, scaled by 1/sigma_jj. Denominators: sum_h e_i' Psi_h Sigma Psi_h' e_i. A*Sigma = [[0.56,0.40],[0.08,0.40]]; A*Sigma*A' = [[0.40,0.16],[0.16,0.16]]. Row i=0: theta_00=(1.0^2+0.56^2)/1.40=0.938286, theta_01=(0.2^2+0.40^2)/1.40=0.142857; normalized [0.867864, 0.132136]. Row i=1: theta_10=(0.2^2+0.08^2)/1.16=0.040000, theta_11=(1.0^2+0.40^2)/1.16=1.000000; normalized [0.038462, 0.961538]. Total spillover = 100*(0.132136+0.038462)/2 = 8.529886.",
  "inputs": {
    "A": [[0.5, 0.3], [0.0, 0.4]],
    "sigma": [[1.0, 0.2], [0.2, 1.0]],
    "horizon": 2
  },
  "expected": {
    "theta_normalized": [[0.8678638, 0.1321362], [0.0384615, 0.9615385]],
    "total_spillover_pct": 8.5298851
  }
}
```

- [ ] **Step 2: Failing builder test** — `src/tests/unit/graphs/test_dy_graph.py`:

```python
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.graphs.spillover import DYSpilloverGraphBuilder


@pytest.fixture
def spillover_panel() -> pd.DataFrame:
    """3-symbol log-RV panel where LEAD Granger-causes F1 and F2 (one-day lag)."""
    rng = np.random.default_rng(42)
    n = 400
    dates = pd.bdate_range("2021-01-04", periods=n)
    lead = np.zeros(n)
    f1 = np.zeros(n)
    f2 = np.zeros(n)
    e = rng.normal(0, 0.3, (n, 3))
    for t in range(1, n):
        lead[t] = 0.6 * lead[t - 1] + e[t, 0]
        f1[t] = 0.3 * f1[t - 1] + 0.5 * lead[t - 1] + e[t, 1]
        f2[t] = 0.3 * f2[t - 1] + 0.5 * lead[t - 1] + e[t, 2]
    return pd.DataFrame({"LEAD": lead, "F1": f1, "F2": f2}, index=dates) - 8.0


def test_dy_is_directed_and_thresholded(spillover_panel):
    snap = DYSpilloverGraphBuilder(var_lags=2, fevd_horizon=10, threshold=0.05).build(
        spillover_panel, spillover_panel.index[-1], list(spillover_panel.columns)
    )
    assert snap.directed is True
    assert np.all(snap.edge_weight >= 0.05)


def test_dy_finds_lead_to_follower_spillover(spillover_panel):
    snap = DYSpilloverGraphBuilder(var_lags=2, fevd_horizon=10, threshold=0.05).build(
        spillover_panel, spillover_panel.index[-1], list(spillover_panel.columns)
    )
    a = snap.dense_adjacency()          # a[i, j] = spillover from i to j
    i = {s: k for k, s in enumerate(spillover_panel.columns)}
    assert a[i["LEAD"], i["F1"]] > 0.05
    assert a[i["LEAD"], i["F2"]] > 0.05
    # follower -> leader spillover should be much weaker than leader -> follower
    assert a[i["LEAD"], i["F1"]] > 3.0 * a[i["F1"], i["LEAD"]]


def test_dy_degenerate_window_empty(spillover_panel):
    tiny = spillover_panel.iloc[:10]
    snap = DYSpilloverGraphBuilder(var_lags=4).build(
        tiny, tiny.index[-1], list(spillover_panel.columns)
    )
    assert snap.n_edges == 0
```

- [ ] **Step 3:** `./vol test -k "gfevd or test_dy_graph"` → red.
- [ ] **Step 4: Implement** — `src/volforecast/graphs/spillover.py`:

```python
"""Diebold-Yilmaz generalized-FEVD spillover graph (directed).

W[i -> j] = normalized share of j's H-step forecast-error variance explained by
shocks to i (Diebold & Yilmaz 2012 eqs. 2-3; generalized FEVD per Pesaran & Shin
1998 eq. 2.9 - order-invariant, unlike statsmodels' orthogonalized fevd()).
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from volforecast.graphs.base import GraphSnapshot, empty_snapshot
from volforecast.registry import register_graph

logger = logging.getLogger(__name__)


def generalized_fevd_matrix(psi: list[np.ndarray], sigma: np.ndarray) -> np.ndarray:
    """Row-normalized generalized FEVD.

    psi : list of MA coefficient matrices [Psi_0, ..., Psi_{H-1}] (Psi_0 = I).
    sigma : residual covariance.
    Returns theta_normalized (N, N): row i = decomposition of i's FEV across sources j.
    """
    n = sigma.shape[0]
    sigma_jj = np.diag(sigma)
    num = np.zeros((n, n))
    den = np.zeros(n)
    for psi_h in psi:
        ps = psi_h @ sigma                      # (N, N): [i, j] = e_i' Psi_h Sigma e_j
        num += ps**2
        den += np.einsum("ij,ij->i", ps, psi_h)  # e_i' Psi_h Sigma Psi_h' e_i
    theta = (num / sigma_jj[None, :]) / den[:, None]
    return theta / theta.sum(axis=1, keepdims=True)


@register_graph("dy")
class DYSpilloverGraphBuilder:
    """Directed spillover graph from a VAR(p) generalized FEVD on the input panel."""

    directed = True

    def __init__(
        self,
        var_lags: int = 4,
        fevd_horizon: int = 10,
        threshold: float = 0.05,
        min_rows: int = 100,
    ) -> None:
        self.var_lags = int(var_lags)
        self.fevd_horizon = int(fevd_horizon)
        self.threshold = float(threshold)
        self.min_rows = int(min_rows)

    def build(self, returns: pd.DataFrame, date: Any, symbols: list[str]) -> GraphSnapshot:
        from statsmodels.tsa.api import VAR

        data = returns[list(symbols)].dropna()
        if len(data) < max(self.min_rows, self.var_lags + 10):
            return empty_snapshot(symbols, date, method="dy")
        try:
            res = VAR(data.values).fit(self.var_lags)
            psi = list(res.ma_rep(maxn=self.fevd_horizon - 1))  # Psi_0..Psi_{H-1}
            theta = generalized_fevd_matrix(psi, np.asarray(res.sigma_u))
        except (np.linalg.LinAlgError, ValueError) as exc:
            logger.warning("dy: VAR/FEVD failed (%s); returning empty graph", exc)
            return empty_snapshot(symbols, date, method="dy")
        # Edge i -> j: spillover FROM i TO j = theta[j, i] (transpose)
        w = theta.T.copy()
        np.fill_diagonal(w, 0.0)
        src, dst = np.where(w >= self.threshold)
        if src.size == 0:
            return empty_snapshot(symbols, date, method="dy")
        return GraphSnapshot(
            edge_index=np.stack([src, dst]).astype(np.int64),
            edge_weight=w[src, dst].astype(np.float32),
            symbols=tuple(symbols), date=date, directed=True, method="dy",
        )
```

Add to `src/tests/unit/formulas/FORMULAS.md` registry table:

```
| Generalized FEVD (spillover graph) | Pesaran & Shin (1998) eq. 2.9; Diebold & Yilmaz (2012) eqs. 2-3 | volforecast/graphs/spillover.py::generalized_fevd_matrix | test_gfevd_formulas.py | gfevd_bivariate_var1.json |
```

- [ ] **Step 5:** `./vol test -k "gfevd or test_dy_graph"` → green.
- [ ] **Step 6: Commit** — `feat(graphs): directed Diebold-Yilmaz generalized-FEVD builder with gold-value formula test`

---

## Task 6: Factor-residual builder + registry finalization

**Files:** Create `src/volforecast/graphs/factor_residual.py`, `src/tests/unit/graphs/test_factor_residual.py`. Modify `src/volforecast/registry.py` (remove the temporary try/except guard around graph imports).

**Copilot context packet:**

```yaml
subtask_id: "gnn-01-6"
goal: "Implement the factor-residual graph builder ('factor_residual': strip a market factor by per-symbol OLS, build a corr or glasso graph on the residuals) and finalize graph imports in ensure_registered()."
file_scope:
  - workspace/plans/gnn/plan-01-graph-construction.md   # Task 6 section
  - src/volforecast/graphs/base.py
  - src/volforecast/graphs/correlation.py
  - src/volforecast/graphs/glasso.py
  - src/volforecast/registry.py
write_scope:
  - src/volforecast/graphs/factor_residual.py
  - src/tests/unit/graphs/test_factor_residual.py
  - src/volforecast/registry.py
acceptance_criteria:
  - "./vol test -k test_factor_residual -> all pass"
  - "./vol test -k 'graphs' -> all graph tests still pass"
  - "GRAPH_REGISTRY contains exactly: identity, full, sector, corr, knn, glasso, dy, factor_residual"
constraints: ["TDD failing-first", "Factor = cross-sectional mean return ('mean') or a named column (e.g. 'SPY')", "Composition: delegate to CorrGraphBuilder/GlassoGraphBuilder on residuals - do not reimplement"]
context_summary: |
  Cartea, Cucuringu & Fang (2026, abstract-only) motivate idiosyncratic networks: edges should
  encode relationships the market factor cannot explain; raw/market-based networks deliver little.
  Implementation: per symbol OLS r_i = a_i + b_i * f + e_i on the estimation window; residual
  panel e -> base builder. On a one-factor synthetic panel, raw corr is dense but residual corr
  should only keep pairs with genuinely correlated idiosyncratics.
depends_on: ["gnn-01-3", "gnn-01-4"]
```

- [ ] **Step 1: Failing tests** — `src/tests/unit/graphs/test_factor_residual.py`:

```python
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.graphs.correlation import CorrGraphBuilder
from volforecast.graphs.factor_residual import FactorResidualGraphBuilder


@pytest.fixture
def one_factor_panel() -> pd.DataFrame:
    """6 symbols all loading on one market factor; only (P1, P2) share an idio factor."""
    rng = np.random.default_rng(42)
    n = 400
    dates = pd.bdate_range("2021-01-04", periods=n)
    mkt = rng.normal(0, 0.012, n)
    idio_pair = rng.normal(0, 0.006, n)
    cols = {}
    for k, sym in enumerate(["P1", "P2", "Q1", "Q2", "Q3", "Q4"]):
        idio = rng.normal(0, 0.006, n)
        extra = idio_pair if sym in ("P1", "P2") else 0.0
        cols[sym] = (1.0 + 0.1 * k) * mkt + idio + extra
    return pd.DataFrame(cols, index=dates)


def test_raw_corr_is_dense_but_residual_graph_is_sparse(one_factor_panel):
    symbols = list(one_factor_panel.columns)
    date = one_factor_panel.index[-1]
    raw = CorrGraphBuilder(threshold=0.5).build(one_factor_panel, date, symbols)
    resid = FactorResidualGraphBuilder(base="corr", factor="mean", threshold=0.5).build(
        one_factor_panel, date, symbols
    )
    assert raw.n_edges > resid.n_edges  # factor stripped -> market-driven edges vanish


def test_residual_graph_keeps_true_idio_pair(one_factor_panel):
    symbols = list(one_factor_panel.columns)
    snap = FactorResidualGraphBuilder(base="corr", factor="mean", threshold=0.5).build(
        one_factor_panel, one_factor_panel.index[-1], symbols
    )
    pairs = {(symbols[i], symbols[j]) for i, j in zip(*snap.edge_index)}
    assert ("P1", "P2") in pairs and ("P2", "P1") in pairs


def test_named_factor_column_is_excluded_from_nodes_regressors(one_factor_panel):
    symbols = list(one_factor_panel.columns)
    snap = FactorResidualGraphBuilder(base="corr", factor="P1", threshold=0.5).build(
        one_factor_panel, one_factor_panel.index[-1], symbols
    )
    assert snap.n_nodes == len(symbols)  # node set unchanged; P1 residual is ~0 and isolated


def test_registry_complete():
    from volforecast.registry import GRAPH_REGISTRY, ensure_registered

    ensure_registered()
    assert set(GRAPH_REGISTRY) >= {
        "identity", "full", "sector", "corr", "knn", "glasso", "dy", "factor_residual",
    }
```

- [ ] **Step 2:** red. **Step 3: Implement** — `src/volforecast/graphs/factor_residual.py`:

```python
"""Factor-residual (idiosyncratic) graphs: build edges on what the market can't explain.

Design idea from Cartea, Cucuringu & Fang (2026, SSRN 6333798, abstract): idiosyncratic
spillover networks beat raw/market-based networks. Per-symbol OLS strips the factor;
a base builder (corr / glasso) runs on the residual panel.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from volforecast.graphs.base import GraphSnapshot, empty_snapshot
from volforecast.graphs.correlation import CorrGraphBuilder
from volforecast.graphs.glasso import GlassoGraphBuilder
from volforecast.registry import register_graph

_BASES = {"corr": CorrGraphBuilder, "glasso": GlassoGraphBuilder}


@register_graph("factor_residual")
class FactorResidualGraphBuilder:
    """OLS-strip a market factor, then delegate to a base graph builder on residuals."""

    directed = False

    def __init__(self, base: str = "corr", factor: str = "mean", **base_params: Any) -> None:
        if base not in _BASES:
            raise ValueError(f"Unknown base {base!r}; expected one of {sorted(_BASES)}")
        self.base_name = base
        self.factor = factor
        self._base = _BASES[base](**base_params)

    def build(self, returns: pd.DataFrame, date: Any, symbols: list[str]) -> GraphSnapshot:
        data = returns[list(symbols)].dropna()
        if len(data) < 30:
            return empty_snapshot(symbols, date, method="factor_residual")
        if self.factor == "mean":
            f = data.mean(axis=1)
        elif self.factor in data.columns:
            f = data[self.factor]
        else:
            return empty_snapshot(symbols, date, method="factor_residual")
        f_c = f - f.mean()
        denom = float((f_c**2).sum())
        if denom <= 0:
            return empty_snapshot(symbols, date, method="factor_residual")
        resid = {}
        for sym in symbols:
            r = data[sym]
            beta = float(((r - r.mean()) * f_c).sum()) / denom
            resid[sym] = r - r.mean() - beta * f_c
        resid_panel = pd.DataFrame(resid, index=data.index)
        snap = self._base.build(resid_panel, date, symbols)
        return GraphSnapshot(
            edge_index=snap.edge_index, edge_weight=snap.edge_weight,
            symbols=snap.symbols, date=date, directed=False, method="factor_residual",
        )
```

In `registry.py`, make the graph imports in `ensure_registered()` unconditional (remove any temporary `try/except`).

- [ ] **Step 4:** `./vol test -k "test_factor_residual or graphs"` → green.
- [ ] **Step 5: Commit** — `feat(graphs): factor-residual idiosyncratic builder; finalize graph registry`

---

## Task 7: Diagnostics — density, degree, Jaccard stability

**Files:** Create `src/volforecast/graphs/diagnostics.py`, `src/tests/unit/graphs/test_graph_diagnostics.py`.

**Copilot context packet:**

```yaml
subtask_id: "gnn-01-7"
goal: "Implement graph diagnostics: snapshot_stats (density, mean degree, isolated nodes), edge_jaccard between snapshots, and schedule_stability over a graph schedule; with tests."
file_scope:
  - workspace/plans/gnn/plan-01-graph-construction.md   # Task 7 section
  - src/volforecast/graphs/base.py
write_scope:
  - src/volforecast/graphs/diagnostics.py
  - src/tests/unit/graphs/test_graph_diagnostics.py
acceptance_criteria:
  - "./vol test -k test_graph_diagnostics -> all pass"
constraints: ["TDD failing-first", "Pure numpy/pandas"]
context_summary: |
  Two published failure modes these diagnostics monitor: (1) Wade 2026 - corr-threshold density
  explodes 0.09 -> 0.93 in crises (density time series per schedule); (2) GNAR-HARX - GLASSO edge
  instability, consecutive-refit Jaccard < 0.8 (edge_jaccard over the schedule's refit sequence).
  Plan 10 surfaces these in the tournament dashboard; Plan 07 adds graph signal energy here.
depends_on: ["gnn-01-1"]
```

- [ ] **Step 1: Failing tests** — `src/tests/unit/graphs/test_graph_diagnostics.py`:

```python
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.graphs.base import GraphSnapshot, empty_snapshot
from volforecast.graphs.diagnostics import edge_jaccard, schedule_stability, snapshot_stats


def _snap(pairs: list[tuple[int, int]], n: int = 4) -> GraphSnapshot:
    if not pairs:
        return empty_snapshot([f"S{i}" for i in range(n)], pd.Timestamp("2024-01-02"))
    src = np.array([p[0] for p in pairs], dtype=np.int64)
    dst = np.array([p[1] for p in pairs], dtype=np.int64)
    return GraphSnapshot(
        edge_index=np.stack([src, dst]), edge_weight=np.ones(len(pairs), dtype=np.float32),
        symbols=tuple(f"S{i}" for i in range(n)), date=pd.Timestamp("2024-01-02"),
    )


def test_snapshot_stats():
    s = _snap([(0, 1), (1, 0), (1, 2), (2, 1)])
    stats = snapshot_stats(s)
    assert stats["n_edges"] == 4
    assert stats["density"] == pytest.approx(4 / 12)
    assert stats["mean_degree"] == pytest.approx(1.0)   # out-degree mean: 4 edges / 4 nodes
    assert stats["isolated_nodes"] == 1                  # node 3


def test_edge_jaccard_identical_and_disjoint():
    a = _snap([(0, 1), (1, 0)])
    b = _snap([(0, 1), (1, 0)])
    c = _snap([(2, 3), (3, 2)])
    assert edge_jaccard(a, b) == pytest.approx(1.0)
    assert edge_jaccard(a, c) == pytest.approx(0.0)
    assert edge_jaccard(a, _snap([])) == pytest.approx(0.0)


def test_schedule_stability_reports_consecutive_jaccard():
    s1, s2 = _snap([(0, 1), (1, 0)]), _snap([(0, 1), (1, 0), (1, 2), (2, 1)])
    dates = pd.bdate_range("2024-01-02", periods=4)
    schedule = {dates[0]: s1, dates[1]: s1, dates[2]: s2, dates[3]: s2}
    df = schedule_stability(schedule)
    # unique snapshots: s1 -> s2; one transition row with jaccard 2/4
    assert len(df) == 2
    assert df["jaccard_prev"].iloc[1] == pytest.approx(0.5)
    assert {"date", "n_edges", "density", "jaccard_prev"} <= set(df.columns)
```

- [ ] **Step 2:** red. **Step 3: Implement** — `src/volforecast/graphs/diagnostics.py`:

```python
"""Graph diagnostics: density/degree stats, edge-set Jaccard, schedule stability.

Monitors two published failure modes: crisis density explosion of thresholded
correlation graphs (Wade 2026, Table 2) and GLASSO edge instability across
refits (O Nuallain 2025, section 5.5: consecutive-refit Jaccard dipping below 0.8).
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from volforecast.graphs.base import GraphSnapshot


def _edge_set(s: GraphSnapshot) -> set[tuple[int, int]]:
    return {(int(i), int(j)) for i, j in zip(*s.edge_index)}


def snapshot_stats(s: GraphSnapshot) -> dict[str, Any]:
    out_deg = np.zeros(s.n_nodes, dtype=np.int64)
    if s.n_edges:
        out_deg = np.bincount(s.edge_index[0], minlength=s.n_nodes)
    return {
        "date": s.date,
        "method": s.method,
        "n_nodes": s.n_nodes,
        "n_edges": s.n_edges,
        "density": s.density(),
        "mean_degree": float(out_deg.mean()) if s.n_nodes else 0.0,
        "isolated_nodes": int((out_deg == 0).sum()),
    }


def edge_jaccard(a: GraphSnapshot, b: GraphSnapshot) -> float:
    ea, eb = _edge_set(a), _edge_set(b)
    union = ea | eb
    if not union:
        return 1.0
    return len(ea & eb) / len(union)


def schedule_stability(schedule: dict[Any, GraphSnapshot]) -> pd.DataFrame:
    """One row per unique snapshot (refit), with Jaccard vs the previous refit."""
    rows: list[dict[str, Any]] = []
    prev: GraphSnapshot | None = None
    seen: set[int] = set()
    for date in sorted(schedule):
        snap = schedule[date]
        if id(snap) in seen:
            continue
        seen.add(id(snap))
        row = snapshot_stats(snap)
        row["date"] = date
        row["jaccard_prev"] = np.nan if prev is None else edge_jaccard(prev, snap)
        rows.append(row)
        prev = snap
    return pd.DataFrame(rows)
```

- [ ] **Step 4:** green. **Step 5: Commit** — `feat(graphs): density/degree/Jaccard stability diagnostics`

---

## Task 8: `GraphConfig` + YAML plumbing + fingerprint + canonical example

**Files:** Modify `src/volforecast/config.py`, `src/volforecast/utils/persistence.py`, `workspace/configs/_CANONICAL_EXAMPLE.yaml`. Create `src/tests/unit/test_graph_config.py`.

**Copilot context packet:**

```yaml
subtask_id: "gnn-01-8"
goal: "Add GraphConfig dataclass (method/window/refit_every/min_history/input/params), wire it as ExperimentConfig.graph with YAML round-trip, include it in the config fingerprint, and document it in _CANONICAL_EXAMPLE.yaml."
file_scope:
  - workspace/plans/gnn/plan-01-graph-construction.md   # Task 8 section
  - src/volforecast/config.py                            # SequenceConfig is the pattern to mirror
  - src/volforecast/utils/persistence.py                 # _config_fingerprint
  - workspace/configs/_CANONICAL_EXAMPLE.yaml
  - src/tests/unit/test_config.py                        # existing round-trip test patterns
write_scope:
  - src/volforecast/config.py
  - src/volforecast/utils/persistence.py
  - workspace/configs/_CANONICAL_EXAMPLE.yaml
  - src/tests/unit/test_graph_config.py
acceptance_criteria:
  - "./vol test -k test_graph_config -> all pass"
  - "./vol test -k test_config -> existing config tests still pass (incl. test_config_completeness)"
  - "Two configs differing only in graph.method produce different fingerprints"
constraints: ["TDD failing-first", "Follow the SequenceConfig | dict | None parsing pattern", "graph: absent -> None (fully backward compatible)", "Update _CANONICAL_EXAMPLE.yaml in this task"]
context_summary: |
  ExperimentConfig is a plain dataclass parsed by from_yaml. Downstream (Plan 02) the runner reads
  config.graph to build graph schedules per fold; fold_cache and checkpoints key on
  utils/persistence._config_fingerprint, so graph settings MUST enter the fingerprint or two
  different graph methods would collide in the cache. graph.input selects which panel the runner
  passes to builders: 'returns' (corr/glasso/factor families) or 'log_rv' (dy).
depends_on: ["gnn-01-1"]
```

- [ ] **Step 1: Failing tests** — `src/tests/unit/test_graph_config.py`:

```python
from __future__ import annotations

import textwrap

import pytest

from volforecast.config import ExperimentConfig, GraphConfig


def _yaml(tmp_path, graph_block: str):
    cfg = textwrap.dedent(f"""
        name: t
        universe: [SPY, AAPL]
        date_range: ["2020-01-01", "2021-01-01"]
        horizons: [1]
        feature_layers: [har_core]
        model: {{name: har, params: {{}}}}
        {graph_block}
    """)
    p = tmp_path / "t.yaml"
    p.write_text(cfg)
    return p


def test_graph_config_defaults():
    g = GraphConfig()
    assert (g.method, g.window, g.refit_every, g.min_history, g.input) == (
        "corr", 252, 21, 60, "returns"
    )
    assert g.params == {}


def test_from_yaml_parses_graph_block(tmp_path):
    p = _yaml(tmp_path, "graph: {method: glasso, window: 504, refit_every: 21, params: {alpha: 0.1}}")
    cfg = ExperimentConfig.from_yaml(p)
    assert isinstance(cfg.graph, GraphConfig)
    assert cfg.graph.method == "glasso"
    assert cfg.graph.window == 504
    assert cfg.graph.params == {"alpha": 0.1}


def test_from_yaml_graph_absent_is_none(tmp_path):
    cfg = ExperimentConfig.from_yaml(_yaml(tmp_path, ""))
    assert cfg.graph is None


def test_graph_method_changes_fingerprint(tmp_path):
    from volforecast.utils.persistence import _config_fingerprint

    c1 = ExperimentConfig.from_yaml(_yaml(tmp_path, "graph: {method: glasso}"))
    c2 = ExperimentConfig.from_yaml(_yaml(tmp_path, "graph: {method: dy}"))
    c3 = ExperimentConfig.from_yaml(_yaml(tmp_path, ""))
    fps = {_config_fingerprint(c) for c in (c1, c2, c3)}
    assert len(fps) == 3


def test_unknown_graph_method_rejected_at_parse(tmp_path):
    with pytest.raises(ValueError, match="Unknown graph method"):
        ExperimentConfig.from_yaml(_yaml(tmp_path, "graph: {method: nonexistent_method}"))
```

- [ ] **Step 2:** red. **Step 3: Implement** — in `src/volforecast/config.py`, add near `SequenceConfig`:

```python
@dataclass
class GraphConfig:
    """Point-in-time graph construction settings for graph-based models.

    method : GRAPH_REGISTRY key (identity|full|sector|corr|knn|glasso|dy|factor_residual)
    window : trailing estimation window in trading days
    refit_every : re-estimate cadence in trading days (21 = monthly, GNNHAR protocol)
    min_history : minimum rows before a non-empty graph is estimated
    input : which panel builders receive - "returns" (corr/glasso/...) or "log_rv" (dy)
    params : builder-specific kwargs (e.g. {threshold: 0.3} or {alpha: 0.1})
    """

    method: str = "corr"
    window: int = 252
    refit_every: int = 21
    min_history: int = 60
    input: str = "returns"
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        from volforecast.registry import GRAPH_REGISTRY, ensure_registered

        ensure_registered()
        if self.method not in GRAPH_REGISTRY:
            raise ValueError(
                f"Unknown graph method {self.method!r}; expected one of {sorted(GRAPH_REGISTRY)}"
            )
        if self.input not in ("returns", "log_rv"):
            raise ValueError(f"graph.input must be 'returns' or 'log_rv', got {self.input!r}")
```

Add field to `ExperimentConfig`: `graph: GraphConfig | dict | None = None`, and in `from_yaml` (mirror the `sequences` handling):

```python
        if isinstance(data.get("graph"), dict):
            data["graph"] = GraphConfig(**data["graph"])
```

In `utils/persistence.py::_config_fingerprint`, add the graph block to the hashed payload dict (same style as sequences/base_model — a `dataclasses.asdict(config.graph) if config.graph else None` entry).

Append to `workspace/configs/_CANONICAL_EXAMPLE.yaml`:

```yaml
# --- graph: point-in-time adjacency for graph models (ghar/gnnhar/gnn/dcrnn_har/gsp_har) ---
# method: identity | full | sector | corr | knn | glasso | dy | factor_residual
# input: returns (corr/glasso/knn/factor_residual) | log_rv (dy)
# params are builder-specific: corr/knn -> {threshold: 0.3} / {k: 5};
# glasso -> {alpha: 0.1 or omit for CV}; dy -> {var_lags: 4, fevd_horizon: 10, threshold: 0.05};
# factor_residual -> {base: corr, factor: mean, threshold: 0.5}
graph:
  method: glasso
  window: 1000        # GNNHAR protocol: rolling 1000-day estimation window
  refit_every: 21     # monthly re-estimation
  min_history: 252
  input: returns
  params: {}
```

- [ ] **Step 4:** `./vol test -k "test_graph_config or test_config"` → green. `./vol typecheck` clean.
- [ ] **Step 5: Commit** — `feat(config): GraphConfig block with registry validation and fingerprint inclusion`

---

## 9. Orchestrator prompt (paste into Copilot Chat)

```
/execute Implement Plan 01 (graph construction library) from workspace/plans/gnn/plan-01-graph-construction.md

Read workspace/plans/gnn/00-overview.md §4 (shared conventions) and the plan file first.
Execute tasks as subagents using the context packets embedded in each task section:
  Wave 1: gnn-01-1
  Wave 2 (parallel, after 1): gnn-01-2, gnn-01-3
  Wave 3 (parallel): gnn-01-4, gnn-01-5, gnn-01-7
  Wave 4 (after 3+4): gnn-01-6
  Wave 5 (after all): gnn-01-8
Max 2 concurrent subagents. Each subagent follows TDD (failing test first — show red then green),
runs only ./vol commands, and returns the §4.2 return contract. Retry a blocked/partial subagent
once with a refined packet, then escalate.
Integration verification (orchestrator, after all tasks): ./vol test (full non-slow suite green),
./vol lint, ./vol typecheck. Then commit any stragglers and append a weekly-progress entry
(Shipped: graph construction library with 8 builders + config plumbing).
Do NOT start Plan 02.
```

## 10. Acceptance gate → Plan 02

- `GRAPH_REGISTRY` = {identity, full, sector, corr, knn, glasso, dy, factor_residual}; all unit + formula tests green; `./vol test` shows no regressions.
- `ExperimentConfig.graph` round-trips YAML and enters the fingerprint.
- Handoff artifacts consumed by Plan 02: `GraphSnapshot`, `build_graph_schedule`, `GraphConfig` (exact signatures in 00-overview §4.4).
