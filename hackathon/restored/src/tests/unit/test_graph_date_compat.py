"""Regression test: datetime.date vs pd.Timestamp mismatch in graph fold lookup.

When RV parquet files store dates as datetime.date (dtype=object), the graph
pipeline converts dates to pd.Timestamp via pd.DatetimeIndex, but fold dates
extracted from X_panel.index remain datetime.date.  Dict lookup fails because
hash(datetime.date) != hash(pd.Timestamp) — producing empty train_graphs and
the misleading error "No valid graphs for training (all have NaN targets)".

This test constructs a minimal panel with datetime.date index and verifies the
graph fold loop correctly maps fold dates to graph-dict keys.
"""
from __future__ import annotations

import datetime

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")


def _make_panel_with_date_index(n_dates: int = 120, symbols: list[str] | None = None):
    """Build (X_panel, y_panel) with datetime.date index — mimics parquet load."""
    symbols = symbols or ["A", "B", "C"]
    # Use datetime.date objects (not Timestamps) — this is what parquet loads produce
    dates = [
        datetime.date(2024, 1, 1) + datetime.timedelta(days=i)
        for i in range(n_dates)
    ]
    idx = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
    rng = np.random.default_rng(42)
    X = pd.DataFrame(
        rng.normal(size=(len(idx), 3)),
        index=idx,
        columns=["log_rv_d", "log_rv_w", "log_rv_m"],
    )
    y = pd.Series(rng.normal(size=len(idx)), index=idx, name="target")
    return X, y, dates, symbols


def test_by_date_lookup_with_datetime_date_index():
    """Fold dates from X_panel (datetime.date) must be normalized to Timestamps for by_date lookup."""
    X, y, raw_dates, symbols = _make_panel_with_date_index()

    # This is what _run_one_horizon_graphs does to build 'dates':
    dates = list(
        pd.DatetimeIndex(
            X.index.get_level_values("date").unique()
        ).sort_values()
    )
    assert isinstance(dates[0], pd.Timestamp)

    # by_date dict has Timestamp keys
    by_date = {d: f"graph_{i}" for i, d in enumerate(dates)}

    # Fold dates come from X_panel.index — they're datetime.date
    fold_dates_raw = sorted(X.index.get_level_values("date").unique()[:60])
    assert isinstance(fold_dates_raw[0], datetime.date)
    assert not isinstance(fold_dates_raw[0], pd.Timestamp)

    # BUG (before fix): direct lookup fails due to hash mismatch
    direct_hits = [by_date[d] for d in fold_dates_raw if d in by_date]
    assert len(direct_hits) == 0, "hash(datetime.date) != hash(Timestamp) -> no matches"

    # FIX: normalize fold dates to Timestamps (what the fix does)
    normalized = pd.DatetimeIndex(fold_dates_raw)
    normalized_hits = [by_date[d] for d in normalized if d in by_date]
    assert len(normalized_hits) == 60


def test_run_one_horizon_graphs_datetime_date_panel(monkeypatch):
    """End-to-end: _run_one_horizon_graphs works with datetime.date panel index."""
    from volforecast.config import (
        CVConfig,
        ExperimentConfig,
        GraphConfig,
        ModelConfig,
    )
    from volforecast.pipeline.runner import Pipeline

    # Build panel data with datetime.date index (mimics real parquet load)
    n_dates = 200
    symbols = ["A", "B", "C"]
    raw_dates = [
        datetime.date(2024, 1, 1) + datetime.timedelta(days=i)
        for i in range(n_dates)
    ]

    # Simulate panel_data as dict[sym -> DataFrame] with datetime.date index
    rng = np.random.default_rng(42)
    panel_data = {}
    for sym in symbols:
        df = pd.DataFrame(
            {
                "rv": np.abs(rng.normal(0.01, 0.005, n_dates)),
                "log_rv": rng.normal(-5, 0.5, n_dates),
                "close": 100 + rng.normal(0, 1, n_dates).cumsum(),
                "open": 100 + rng.normal(0, 1, n_dates).cumsum(),
                "high": 101 + rng.normal(0, 1, n_dates).cumsum(),
                "low": 99 + rng.normal(0, 1, n_dates).cumsum(),
                "rq": np.abs(rng.normal(0.001, 0.0005, n_dates)),
                "bpv": np.abs(rng.normal(0.008, 0.004, n_dates)),
                "rs_positive": np.abs(rng.normal(0.005, 0.003, n_dates)),
                "rs_negative": np.abs(rng.normal(0.005, 0.003, n_dates)),
            },
            index=pd.Index(raw_dates, name="date"),
        )
        df["rv"] = df["rv"].clip(lower=1e-10)
        panel_data[sym] = df

    cfg = ExperimentConfig(
        name="test_date_compat",
        universe=symbols,
        date_range=("2024-01-01", "2024-07-18"),
        horizons=[1],
        feature_layers=["har_core"],
        model=ModelConfig(name="gnn", params={
            "hidden_dim": 4, "n_heads": 1, "max_epochs": 2,
            "learning_rate": 0.01, "seed": 42,
        }),
        cv=CVConfig(
            method="expanding_window",
            purge_gap=1,
            train_size=60,
            test_size=30,
        ),
        training_mode="pooled",
        graph=GraphConfig(
            method="identity",
            input="log_rv",
            window=20,
            refit_every=5,
            min_history=20,
        ),
    )

    pipeline = Pipeline(cfg)

    # This should NOT raise "No valid graphs for training (all have NaN targets)"
    results = pipeline.run_pooled(panel_data)
    assert 1 in results
    assert results[1]["predictions"].notna().any()


def test_graph_cv_fold_count_matches_date_based_splitting():
    """CV on graph path must split by unique dates, not (date, symbol) tuples.

    Regression: PanelExpandingWindowCV.split was called with a MultiIndex
    DataFrame, so unique() returned N*S tuples instead of N dates, producing
    ~S times too many folds.
    """
    from volforecast.utils.cv import PanelExpandingWindowCV

    n_dates = 300
    symbols = ["A", "B", "C"]
    dates = pd.bdate_range("2024-01-01", periods=n_dates)
    idx = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
    X_multi = pd.DataFrame({"f": np.zeros(len(idx))}, index=idx)

    # Date-flattened (correct) — what the fix does
    X_dates = pd.DataFrame(
        {"_dummy": np.zeros(len(idx))},
        index=idx.get_level_values("date"),
    )

    cv = PanelExpandingWindowCV(
        min_train_dates=60, test_dates=30, step_dates=30, purge_gap=5,
    )

    folds_correct = len(list(cv.split(X_dates)))
    # Rebuild CV (iterator consumed)
    cv2 = PanelExpandingWindowCV(
        min_train_dates=60, test_dates=30, step_dates=30, purge_gap=5,
    )
    folds_multi = len(list(cv2.split(X_multi)))

    # The MultiIndex path would produce ~3x more folds (3 symbols)
    assert folds_multi > folds_correct, "MultiIndex should produce more folds (the bug)"
    # Correct fold count should be based on ~300 dates, not ~900 tuples
    expected_approx = (n_dates - 60 - 5 - 30) // 30 + 1  # ~7-8 folds
    assert abs(folds_correct - expected_approx) <= 1, (
        f"Expected ~{expected_approx} folds, got {folds_correct}"
    )
