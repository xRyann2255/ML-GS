"""Integration test: GSVIVS signal with execution_kvar iv_source.

Verifies the full path from config → _compute_gsvivs_stats with Kvar IV source
using synthetic data (no external dependencies).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def kvar_cache(tmp_path, monkeypatch):
    """Create kvar parquet and patch processed_dir + load_exec_kvar_cache.

    The legacy Kvar cache (gsvivs_kvar_daily.parquet) is written to disk for
    backward compatibility with other consumers. The Exec Kvar series — which
    is what _compute_gsvivs_stats actually loads — is wired up via a direct
    monkeypatch so we do not depend on the on-disk gsvivs_exec_kvar.parquet
    format here.
    """
    dates = pd.bdate_range("2022-06-01", "2024-12-31", freq="B")
    rng = np.random.default_rng(42)
    n = len(dates)
    kvar = 14.0 + rng.standard_normal(n) * 4.0
    kvar = np.clip(kvar, 5.0, 50.0)

    df = pd.DataFrame(
        {
            "kvar_1dte": kvar,
            "atm_vol_1dte": kvar * 0.97,
            "kvar_0dte": np.nan,
            "atm_vol_0dte": np.nan,
            "forward": 4200.0,
            "index_value": 100.0,
            "daily_return_bps": rng.standard_normal(n) * 20.0,
        },
        index=dates,
    )
    df.index.name = "date"
    path = tmp_path / "gsvivs_kvar_daily.parquet"
    df.to_parquet(path)

    monkeypatch.setattr("volforecast.data.edrvol.processed_dir", lambda: tmp_path)

    exec_kvar = pd.Series(kvar, index=dates, name="kvar_vol_pct")
    monkeypatch.setattr("volforecast.data.edrvol.load_exec_kvar_cache", lambda: exec_kvar)
    return df


@pytest.fixture
def fake_gsvivs(monkeypatch):
    """Patch fetch_gsvivs_index with synthetic data covering the Kvar period."""
    dates = pd.bdate_range("2022-06-01", "2024-12-31", freq="B")
    rng = np.random.default_rng(42)
    daily_ret = 0.06 / 252 + 0.10 / np.sqrt(252) * rng.standard_normal(len(dates))
    levels = 100.0 * np.exp(np.cumsum(daily_ret))
    series = pd.Series(levels, index=dates, name="gsvivs01")
    series.index = pd.DatetimeIndex(series.index)
    series.index.name = "date"

    def _fake_fetch(start_date=None, end_date=None):
        return series

    monkeypatch.setattr("volforecast.data.edrvol.fetch_gsvivs_index", _fake_fetch)
    return series


@pytest.fixture
def fake_iv_cache(monkeypatch):
    """Patch load_iv_cache to return synthetic IV for SPY."""
    dates = pd.bdate_range("2022-06-01", "2024-12-31", freq="B")
    rng = np.random.default_rng(42)
    n = len(dates)
    iv_df = pd.DataFrame(
        {
            "iv_1w_atm": 14.0 + rng.standard_normal(n) * 2.0,
            "iv_1m_atm": 15.0 + rng.standard_normal(n) * 2.0,
            "iv_vs_0dte": 13.0 + rng.standard_normal(n) * 3.0,
        },
        index=dates,
    )
    iv_df.index.name = "date"

    def _fake_load(symbol):
        if symbol == "SPY":
            return iv_df
        return None

    monkeypatch.setattr("volforecast.data.edrvol.load_iv_cache", _fake_load)
    return iv_df


@pytest.fixture
def fake_edrvs(monkeypatch):
    """Patch legacy IV loaders to return None.

    Only the legacy EDRVS prev-close / morning loaders are nulled here.
    Exec Kvar is the sole IV source the dashboard cares about, so it is
    left alone — the kvar_cache fixture wires it up via processed_dir.
    """
    monkeypatch.setattr("volforecast.data.edrvol.load_edrvs_cache", lambda: None)
    monkeypatch.setattr("volforecast.data.edrvol.load_edrvs_morning_cache", lambda: None)


def test_kvar_vol_space_signal(kvar_cache, fake_gsvivs, fake_iv_cache, fake_edrvs):
    """_compute_gsvivs_stats with iv_source='execution_kvar' produces valid results."""
    from volforecast.evaluation.tournament import _compute_gsvivs_stats

    # Create synthetic model predictions (log RV)
    dates = pd.bdate_range("2022-06-01", "2024-12-31", freq="B")
    rng = np.random.default_rng(42)
    n = len(dates)
    # log_rv predictions ~ log(0.12^2 / 252) ≈ -10.5
    log_rv_preds = -10.5 + rng.standard_normal(n) * 0.5
    preds = pd.Series(log_rv_preds, index=dates, name="predictions")

    all_preds = {("har", "SPY", 1): preds}

    results_by_iv, traces_by_iv = _compute_gsvivs_stats(
        all_preds_series=all_preds,
        symbols=["SPY"],
        models=["har"],
        horizons=[1],
        iv_source="execution_kvar",
        signal_space="vol",
        iv_sources=["exec_kvar"],
    )

    # New return type: dict[iv_label, dict[horizon, list[row]]]
    assert len(results_by_iv) >= 1
    first_iv = next(iter(results_by_iv))
    results = results_by_iv[first_iv]
    assert 1 in results
    assert len(results[1]) >= 1  # at least the model row

    # Check that model results have expected keys.
    # The 3-mode sizing toggle suffixes the model name; the binary variant is
    # the legacy-equivalent row.
    model_row = next(r for r in results[1] if r["name"] == "har [binary]")
    assert "sharpe_0rf" in model_row
    assert "hit_rate" in model_row
    assert isinstance(model_row["sharpe_0rf"], float)


def test_kvar_variance_space_signal(kvar_cache, fake_gsvivs, fake_iv_cache, fake_edrvs):
    """_compute_gsvivs_stats with signal_space='variance' works."""
    from volforecast.evaluation.tournament import _compute_gsvivs_stats

    dates = pd.bdate_range("2022-06-01", "2024-12-31", freq="B")
    rng = np.random.default_rng(42)
    n = len(dates)
    log_rv_preds = -10.5 + rng.standard_normal(n) * 0.5
    preds = pd.Series(log_rv_preds, index=dates, name="predictions")

    all_preds = {("har", "SPY", 1): preds}

    results_by_iv, traces_by_iv = _compute_gsvivs_stats(
        all_preds_series=all_preds,
        symbols=["SPY"],
        models=["har"],
        horizons=[1],
        iv_source="execution_kvar",
        signal_space="variance",
        iv_sources=["exec_kvar"],
    )

    assert len(results_by_iv) >= 1
    first_iv = next(iter(results_by_iv))
    results = results_by_iv[first_iv]
    assert 1 in results
    assert len(results[1]) >= 1

    model_row = next(r for r in results[1] if r["name"] == "har [binary]")
    assert "sharpe_0rf" in model_row


def test_no_results_when_kvar_cache_missing(
    fake_gsvivs, fake_iv_cache, fake_edrvs, tmp_path, monkeypatch
):
    """When the Exec Kvar cache is missing, no signal P&L is produced.

    The dashboard standardized on Exec Kvar as the only IV source for the
    GSVIVS signal backtest; the legacy EDRVS / SPX-ATM fallbacks were
    removed. With no Kvar cache available, _compute_gsvivs_stats should
    return without raising and yield an empty model-row list for the
    requested horizon.
    """
    from volforecast.evaluation.tournament import _compute_gsvivs_stats

    # Point to empty directory (no kvar parquet) and null the loader
    # so processed_dir patch from kvar_cache is not inherited.
    monkeypatch.setattr("volforecast.data.edrvol.processed_dir", lambda: tmp_path)
    monkeypatch.setattr("volforecast.data.edrvol.load_exec_kvar_cache", lambda: None)

    dates = pd.bdate_range("2022-06-01", "2024-12-31", freq="B")
    rng = np.random.default_rng(42)
    n = len(dates)
    log_rv_preds = -10.5 + rng.standard_normal(n) * 0.5
    preds = pd.Series(log_rv_preds, index=dates, name="predictions")

    all_preds = {("har", "SPY", 1): preds}

    # Should not crash. Result dict for the horizon may be empty (no IV → no signal).
    results_by_iv, traces_by_iv = _compute_gsvivs_stats(
        all_preds_series=all_preds,
        symbols=["SPY"],
        models=["har"],
        horizons=[1],
        iv_source="execution_kvar",
        signal_space="vol",
        iv_sources=["exec_kvar"],
    )

    # Either no IV-source key, or the single Exec Kvar key with empty rows.
    if results_by_iv:
        assert list(results_by_iv.keys()) == ["Exec Kvar (true fill)"]
        assert results_by_iv["Exec Kvar (true fill)"].get(1, []) == []


def test_execution_kvar_is_horizon_normalized(fake_gsvivs, monkeypatch):
    """Execution Kvar should NOT be scaled by sqrt(h) for longer horizons.

    The cached execution-Kvar series is in annualized vol (24h tenor).
    The RV forecast is also in annualized vol (sqrt(252 * daily_var)).
    Both are in the same units, so no horizon-dependent scaling is needed.
    With Kvar=22% and RV=10%, the signal should be sell-vol (positive P&L)
    at ALL horizons.
    """
    from volforecast.evaluation.tournament import _compute_gsvivs_stats

    dates = pd.bdate_range("2022-06-01", "2024-12-31", freq="B")
    n = len(dates)

    # Constant 24h execution-Kvar series in vol points.
    exec_kvar = pd.Series(22.0, index=dates, name="kvar_vol_pct")

    # Minimal IV cache just to satisfy non-exec IV source loading.
    iv_df = pd.DataFrame(
        {
            "iv_1w_atm": np.full(n, 18.0),
            "iv_1m_atm": np.full(n, 18.0),
            "iv_vs_0dte": np.full(n, 18.0),
        },
        index=dates,
    )
    iv_df.index.name = "date"

    monkeypatch.setattr("volforecast.data.edrvol.load_exec_kvar_cache", lambda: exec_kvar)
    monkeypatch.setattr("volforecast.data.edrvol.load_iv_cache", lambda symbol: iv_df)
    monkeypatch.setattr("volforecast.data.edrvol.load_edrvs_cache", lambda: None)
    monkeypatch.setattr("volforecast.data.edrvol.load_edrvs_morning_cache", lambda: None)

    # Constant 10% annualized RV forecast for each horizon.
    log_rv_pred = np.log((0.10**2) / 252.0)
    all_preds = {
        ("har", "SPY", 1): pd.Series(log_rv_pred, index=dates, name="predictions"),
        ("har", "SPY", 5): pd.Series(log_rv_pred, index=dates, name="predictions"),
        ("har", "SPY", 22): pd.Series(log_rv_pred, index=dates, name="predictions"),
    }

    results_by_iv, _ = _compute_gsvivs_stats(
        all_preds_series=all_preds,
        symbols=["SPY"],
        models=["har"],
        horizons=[1, 5, 22],
        short_threshold=0.0,
        iv_source="execution_kvar",
        signal_space="vol",
        iv_sources=["exec_kvar"],
    )

    exec_results = results_by_iv["Exec Kvar (true fill)"]
    row_h1 = next(r for r in exec_results[1] if r["name"] == "har [binary]")
    row_h5 = next(r for r in exec_results[5] if r["name"] == "har [binary]")
    row_h22 = next(r for r in exec_results[22] if r["name"] == "har [binary]")

    # Kvar=22% (→18.3% in 252-day terms) > RV=10% at all horizons → sell vol
    assert row_h1["ann_return"] > 0.0
    assert row_h5["ann_return"] > 0.0
    assert row_h22["ann_return"] > 0.0


def test_only_exec_kvar_iv_source_is_computed(fake_gsvivs, monkeypatch):
    """The PnL is only computed for Exec Kvar.

    Even when every legacy IV cache (EDRVS morning 1-DTE, EDRVS prev-close 1-DTE,
    SPX ATM IV 1w) is available, _compute_gsvivs_stats must return exactly one
    iv-source key — the Exec Kvar variant. The other three signal P&Ls are
    deliberately not computed.
    """
    from volforecast.evaluation.tournament import _compute_gsvivs_stats

    dates = pd.bdate_range("2022-06-01", "2024-12-31", freq="B")
    n = len(dates)

    exec_kvar = pd.Series(22.0, index=dates, name="kvar_vol_pct")
    edrvs_prev = pd.Series(20.0, index=dates, name="iv_vs_0dte")
    edrvs_morning = pd.Series(21.0, index=dates, name="iv_morning_1dte")
    iv_df = pd.DataFrame(
        {
            "iv_1w_atm": np.full(n, 18.0),
            "iv_1m_atm": np.full(n, 18.0),
        },
        index=dates,
    )
    iv_df.index.name = "date"

    monkeypatch.setattr("volforecast.data.edrvol.load_exec_kvar_cache", lambda: exec_kvar)
    monkeypatch.setattr("volforecast.data.edrvol.load_iv_cache", lambda symbol: iv_df)
    monkeypatch.setattr("volforecast.data.edrvol.load_edrvs_cache", lambda: edrvs_prev)
    monkeypatch.setattr(
        "volforecast.data.edrvol.load_edrvs_morning_cache", lambda: edrvs_morning
    )

    log_rv_pred = np.log((0.10**2) / 252.0)
    all_preds = {("har", "SPY", 1): pd.Series(log_rv_pred, index=dates, name="predictions")}

    results_by_iv, traces_by_iv = _compute_gsvivs_stats(
        all_preds_series=all_preds,
        symbols=["SPY"],
        models=["har"],
        horizons=[1],
        short_threshold=0.0,
        iv_source="execution_kvar",
        signal_space="vol",
        iv_sources=["exec_kvar"],
    )

    assert list(results_by_iv.keys()) == ["Exec Kvar (true fill)"]
    assert list(traces_by_iv.keys()) == ["Exec Kvar (true fill)"]


def test_config_loads_new_fields():
    """ExperimentConfig.from_yaml parses gsvivs_iv_source and gsvivs_signal_space."""
    import tempfile

    import yaml

    from volforecast.config import ExperimentConfig

    config_dict = {
        "name": "test_kvar",
        "universe": ["SPY"],
        "date_range": ["2022-01-01", "2024-12-31"],
        "horizons": [1],
        "feature_layers": ["har_core"],
        "model": {"name": "har", "params": {}},
        "tournament": {
            "gsvivs_enabled": True,
            "gsvivs_iv_source": "execution_kvar",
            "gsvivs_signal_space": "variance",
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_dict, f)
        f.flush()
        config = ExperimentConfig.from_yaml(Path(f.name))

    assert config.tournament.gsvivs_iv_source == "execution_kvar"
    assert config.tournament.gsvivs_signal_space == "variance"
