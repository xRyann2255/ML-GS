from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.graphs.correlation import CorrGraphBuilder
from volforecast.graphs.factor_residual import FactorResidualGraphBuilder


@pytest.fixture
def one_factor_panel() -> pd.DataFrame:
    """20 symbols all loading on one market factor; only (P1, P2) share an idio factor.

    With 20 symbols, the pair signal is negligible in the cross-sectional mean,
    so OLS cleanly strips the market leaving P1-P2 idio link visible.
    """
    rng = np.random.default_rng(42)
    n = 600
    dates = pd.bdate_range("2020-01-02", periods=n)
    mkt = rng.normal(0, 0.020, n)
    idio_pair = rng.normal(0, 0.012, n)
    syms = ["P1", "P2"] + [f"Q{i}" for i in range(1, 19)]
    cols = {}
    for k, sym in enumerate(syms):
        beta = 0.8 + 0.05 * k
        idio = rng.normal(0, 0.004, n)
        extra = idio_pair if sym in ("P1", "P2") else 0.0
        cols[sym] = beta * mkt + idio + extra
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
