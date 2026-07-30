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
