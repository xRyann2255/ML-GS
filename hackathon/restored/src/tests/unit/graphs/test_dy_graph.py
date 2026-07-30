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
