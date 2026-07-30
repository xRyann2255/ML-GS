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
