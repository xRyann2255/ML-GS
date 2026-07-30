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
