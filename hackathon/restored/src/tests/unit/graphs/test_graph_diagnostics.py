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
