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
        stored = self.n_edges
        return float(stored) / possible

    def dense_adjacency(
        self, norm: str | None = None, *, binary: bool = False
    ) -> np.ndarray:
        """Dense (N, N) adjacency. norm: None | 'sym' (D^-1/2 A D^-1/2) | 'row' (D^-1 A)."""
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
    on_progress: Any | None = None,
) -> dict[Any, GraphSnapshot]:
    """Map each forecast date to a point-in-time GraphSnapshot.

    Re-estimates on dates[0], dates[refit_every], ... using the trailing
    ``window`` rows of ``returns`` ending at (or before) the refit date.
    Dates with fewer than ``min_history`` rows get an empty snapshot.

    Parameters
    ----------
    on_progress : callable, optional
        Called as ``on_progress(n_built, n_total)`` after each graph build.
    """
    import logging as _logging

    _logger = _logging.getLogger(__name__)

    symbols = list(returns.columns)
    schedule: dict[Any, GraphSnapshot] = {}
    current: GraphSnapshot | None = None
    n_refits = sum(1 for i in range(len(dates)) if i % refit_every == 0)
    n_built = 0
    _logger.info(
        "build_graph_schedule: %d dates, %d refits (%s builder, window=%d)",
        len(dates), n_refits, getattr(builder, "name", type(builder).__name__), window,
    )
    for i, date in enumerate(dates):
        if i % refit_every == 0:
            hist = returns.loc[returns.index <= date].tail(window)
            if len(hist) < min_history:
                current = empty_snapshot(symbols, date, method=builder.name)
            else:
                current = builder.build(hist, date, symbols)
            n_built += 1
            if on_progress is not None:
                on_progress(n_built, n_refits)
        assert current is not None
        schedule[date] = current
    _logger.info("build_graph_schedule: done (%d graphs built)", n_built)
    return schedule
