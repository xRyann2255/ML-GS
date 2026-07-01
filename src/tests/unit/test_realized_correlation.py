"""Tests for RealizedCorrelationLayer — cross-symbol panel correlation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from volforecast.features.realized_correlation import (
    RealizedCorrelationLayer,
    _compute_panel_corr_features,
    _load_panel_returns,
    _rolling_mean_pairwise_corr,
)


@pytest.fixture
def synthetic_ohlcv_cache(tmp_path: Path) -> Path:
    """Create a synthetic ohlcv cache with 8 symbols, controlled correlation.

    Returns 7 'correlated' symbols (shared factor) and 1 'independent'.
    Correlation should be high but well below 1.
    """
    rng = np.random.default_rng(2026)
    n_days = 400
    dates = pd.bdate_range("2020-01-02", periods=n_days, freq="B")
    factor = rng.normal(0, 0.01, n_days)
    for i, sym in enumerate(["A", "B", "C", "D", "E", "F", "G"]):
        idio = rng.normal(0, 0.005, n_days)
        log_ret = factor + idio
        close = 100.0 * np.exp(np.cumsum(log_ret))
        df = pd.DataFrame({"close": close}, index=pd.Index(dates, name="date"))
        df.to_parquet(tmp_path / f"{sym}.parquet")
    # One independent symbol
    indep_ret = rng.normal(0, 0.01, n_days)
    indep_close = 100.0 * np.exp(np.cumsum(indep_ret))
    df = pd.DataFrame({"close": indep_close}, index=pd.Index(dates, name="date"))
    df.to_parquet(tmp_path / "INDEP.parquet")
    # An underscore-prefixed market file that MUST be skipped
    df = pd.DataFrame({"close": [1.0] * n_days}, index=pd.Index(dates, name="date"))
    df.to_parquet(tmp_path / "_VIX.parquet")
    return tmp_path


class TestLoadPanelReturns:
    def test_loads_only_non_underscore_files(self, synthetic_ohlcv_cache: Path):
        wide = _load_panel_returns(synthetic_ohlcv_cache)
        # 8 real symbols (A-G + INDEP), _VIX excluded
        assert wide.shape[1] == 8
        assert "_VIX" not in wide.columns
        # First row is NaN (log diff)
        assert wide.iloc[0].isna().all()

    def test_empty_cache_returns_empty(self, tmp_path: Path):
        wide = _load_panel_returns(tmp_path)
        assert wide.empty


class TestRollingMeanPairwiseCorr:
    def test_high_correlation_detected(self, synthetic_ohlcv_cache: Path):
        wide = _load_panel_returns(synthetic_ohlcv_cache)
        corr_22d = _rolling_mean_pairwise_corr(wide, window=22)
        # 7 correlated + 1 independent => average pairwise should be moderate
        mean_corr = corr_22d.dropna().mean()
        assert 0.2 < mean_corr < 0.95, f"unexpected mean corr {mean_corr:.3f}"

    def test_first_window_is_nan(self, synthetic_ohlcv_cache: Path):
        wide = _load_panel_returns(synthetic_ohlcv_cache)
        corr_22d = _rolling_mean_pairwise_corr(wide, window=22)
        # Loop starts at i=window-1 -> positions 0..20 are NaN, position 21 is first valid
        assert corr_22d.iloc[:21].isna().all()
        assert corr_22d.iloc[22:].notna().any()


class TestComputePanelCorrFeatures:
    def test_produces_expected_columns(self, synthetic_ohlcv_cache: Path):
        # Clear cache to avoid pollution across tests
        _compute_panel_corr_features.cache_clear()
        out = _compute_panel_corr_features(str(synthetic_ohlcv_cache))
        assert list(out.columns) == [
            "panel_corr_22d",
            "panel_corr_5d",
            "panel_corr_d",
            "panel_corr_z",
        ]
        assert len(out) > 0

    def test_zscore_eventually_nonzero(self, synthetic_ohlcv_cache: Path):
        _compute_panel_corr_features.cache_clear()
        out = _compute_panel_corr_features(str(synthetic_ohlcv_cache))
        # After 60d zscore window + 22d corr window, z should have non-NaN values
        z_valid = out["panel_corr_z"].dropna()
        assert len(z_valid) > 0
        assert (z_valid != 0).any()


class TestRealizedCorrelationLayer:
    def test_layer_registered(self):
        from volforecast.registry import FEATURE_REGISTRY, ensure_registered

        ensure_registered()
        assert "realized_correlation" in FEATURE_REGISTRY

    def test_reindexes_to_daily_data(self, monkeypatch, synthetic_ohlcv_cache: Path):
        # Redirect ohlcv_cache_dir to synthetic cache
        _compute_panel_corr_features.cache_clear()
        monkeypatch.setattr(
            "volforecast.features.realized_correlation.ohlcv_cache_dir",
            lambda: synthetic_ohlcv_cache,
        )
        dates = pd.bdate_range("2020-06-01", periods=20, freq="B")
        daily = pd.DataFrame({"rv": np.zeros(len(dates))}, index=pd.Index(dates, name="date"))
        layer = RealizedCorrelationLayer()
        result = layer.compute(daily)
        assert len(result) == len(daily)
        assert list(result.columns) == [
            "panel_corr_22d",
            "panel_corr_5d",
            "panel_corr_d",
            "panel_corr_z",
        ]
        # All requested dates should map (synthetic cache covers them)
        assert result["panel_corr_22d"].notna().sum() > 10

    def test_empty_cache_returns_empty_columns(self, monkeypatch, tmp_path: Path):
        _compute_panel_corr_features.cache_clear()
        monkeypatch.setattr(
            "volforecast.features.realized_correlation.ohlcv_cache_dir",
            lambda: tmp_path,
        )
        dates = pd.bdate_range("2020-01-02", periods=10, freq="B")
        daily = pd.DataFrame({"rv": np.zeros(10)}, index=pd.Index(dates, name="date"))
        layer = RealizedCorrelationLayer()
        result = layer.compute(daily)
        # Empty cache: layer should return DataFrame with the daily index and no columns
        assert len(result) == 10
        assert result.shape[1] == 0
