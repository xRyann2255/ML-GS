"""Smoke test: GSVIVS01 PnL section appears in tournament dashboard.

Patches fetch_gsvivs_index to return synthetic data, runs a minimal HAR
tournament on SPY, and verifies the dashboard HTML contains the GSVIVS section.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def output_dir(tmp_path):
    """Clean output directory for dashboard artifacts."""
    out = tmp_path / "dashboard_out"
    out.mkdir()
    return out


@pytest.fixture
def fake_gsvivs(monkeypatch):
    """Patch fetch_gsvivs_index to return synthetic data without TSDB."""
    dates = pd.bdate_range("2014-01-02", "2024-12-31", freq="B")
    rng = np.random.default_rng(42)
    daily_ret = 0.08 / 252 + 0.12 / np.sqrt(252) * rng.standard_normal(len(dates))
    levels = 100.0 * np.exp(np.cumsum(daily_ret))
    series = pd.Series(levels, index=dates, name="gsvivs01")
    series.index = pd.DatetimeIndex(series.index)
    series.index.name = "date"

    def _fake_fetch(start_date=None, end_date=None):
        return series

    monkeypatch.setattr("volforecast.data.edrvol.fetch_gsvivs_index", _fake_fetch)
    return series


@pytest.mark.skipif(
    not Path("/home/vincry/ceph-storage/ml-vol-estimator/data/raw/ticks/SPY.parquet").exists(),
    reason="SPY data not available",
)
def test_gsvivs_appears_in_dashboard(output_dir, fake_gsvivs, monkeypatch):
    """GSVIVS section appears in dashboard when cache is seeded and enabled."""
    from volforecast.evaluation.tournament import run_har_tournament

    # Run minimal tournament: 1 symbol, 1 horizon, HAR-only
    results = run_har_tournament(
        symbols=["SPY"],
        date_range=("2022-06-01", "2024-12-31"),
        horizons=[1],
        models=["har"],
        output_dir=output_dir,
        mcs_bootstrap=100,
        gsvivs_enabled=True,
    )

    # Verify tournament ran
    assert 1 in results
    assert len(results[1]) >= 1

    # Find dashboard HTML
    html_files = list(output_dir.rglob("*.html"))
    assert len(html_files) >= 1, f"No HTML dashboard in {output_dir}"

    html_content = html_files[0].read_text()

    # Check GSVIVS section is present
    assert "GSVIVS01" in html_content or "gsvivs" in html_content, (
        "GSVIVS section not found in dashboard HTML"
    )
    assert "Variance Swap Signal" in html_content, "Variance Swap Signal heading not found"
