"""GLASSO conditional-independence graph (Zhang, Pu, Cucuringu & Dong 2025, p.8).

Theta_hat = argmin_{Theta >= 0} tr(S Theta) - log det(Theta) + lambda * sum_{j!=k} |Theta_jk|
A_ij = 1{Theta_hat_ij != 0}, binary, undirected, zero diagonal.
"""
from __future__ import annotations

import logging
import warnings
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
        self,
        alpha: float | None = None,
        max_iter: int = 200,
        min_rows: int = 60,
        n_refinements: int = 2,
        cv: int = 3,
    ) -> None:
        self.alpha = alpha
        self.max_iter = int(max_iter)
        self.min_rows = int(min_rows)
        self.n_refinements = int(n_refinements)
        self.cv = int(cv)

    def build(self, returns: pd.DataFrame, date: Any, symbols: list[str]) -> GraphSnapshot:
        from sklearn.covariance import GraphicalLasso, GraphicalLassoCV
        from sklearn.exceptions import ConvergenceWarning

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
                est = GraphicalLassoCV(
                    max_iter=self.max_iter,
                    assume_centered=True,
                    n_refinements=self.n_refinements,
                    cv=self.cv,
                )
            else:
                est = GraphicalLasso(
                    alpha=self.alpha, max_iter=self.max_iter, assume_centered=True
                )
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=ConvergenceWarning)
                warnings.filterwarnings("ignore", category=RuntimeWarning)
                est.fit(z.values)
        except (FloatingPointError, ValueError) as exc:
            logger.warning("glasso: estimation failed (%s); returning empty graph", exc)
            return empty_snapshot(symbols, date, method="glasso")
        prec = np.asarray(est.precision_)
        # Non-converged fits can produce NaN/Inf precision — fall back to empty
        if not np.all(np.isfinite(prec)):
            logger.warning("glasso: non-finite precision at %s; returning empty graph", date)
            return empty_snapshot(symbols, date, method="glasso")
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
