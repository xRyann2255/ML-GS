"""TDD tests for ImpliedCorrelationLayer (module does not exist yet).

Tests define expected behavior for volforecast.features.implied_correlation.
All tests should FAIL until the implementation is written.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_COLUMNS = [
    "implied_corr_spx_1m",
    "realized_corr_spx_1m",
    "corr_risk_premium",
    "dispersion_signal",
    "corr_momentum",
    "corr_zscore",
]


def _make_correlation_parquet(
    tmp_path: Path, start: str = "2020-01-02", end: str = "2024-12-31"
) -> Path:
    """Write a synthetic spx_correlation.parquet for testing."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    n = len(idx)
    impl = 0.5 + rng.uniform(-0.05, 0.05, n)
    real = 0.45 + rng.uniform(-0.05, 0.05, n)
    df = pd.DataFrame(
        {
            "implied_corr_spx_1m": impl,
            "realized_corr_spx_1m": real,
            "corr_risk_premium": impl - real,
            "dispersion_signal": 0.20 + rng.uniform(-0.02, 0.02, n),
            "corr_momentum": np.concatenate([[np.nan], np.diff(impl)]),
            "corr_zscore": rng.normal(0, 1, n),
        },
        index=idx,
    )
    df.index.name = "date"
    outpath = tmp_path / "spx_correlation.parquet"
    df.to_parquet(outpath)
    return outpath


def _make_daily_data(start: str = "2020-01-02", end: str = "2024-12-31") -> pd.DataFrame:
    """Create a minimal daily_data DataFrame with business-day index."""
    idx = pd.bdate_range(start, end)
    return pd.DataFrame({"close": 100.0}, index=idx)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestImpliedCorrelationLayer:
    """Tests for ImpliedCorrelationLayer.compute()."""

    @patch("volforecast.features.implied_correlation.correlation_cache_dir")
    def test_compute_returns_six_columns(self, mock_cache_dir, tmp_path):
        """Given a valid cached parquet, compute returns all 6 expected columns."""
        _make_correlation_parquet(tmp_path)
        mock_cache_dir.return_value = tmp_path

        from volforecast.features.implied_correlation import ImpliedCorrelationLayer

        layer = ImpliedCorrelationLayer()
        daily_data = _make_daily_data()
        result = layer.compute(daily_data)

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == EXPECTED_COLUMNS

    @patch("volforecast.features.implied_correlation.correlation_cache_dir")
    def test_reindexes_onto_daily_data(self, mock_cache_dir, tmp_path):
        """Output index matches daily_data.index exactly."""
        _make_correlation_parquet(tmp_path)
        mock_cache_dir.return_value = tmp_path

        from volforecast.features.implied_correlation import ImpliedCorrelationLayer

        layer = ImpliedCorrelationLayer()
        daily_data = _make_daily_data("2021-06-01", "2023-06-30")
        result = layer.compute(daily_data)

        pd.testing.assert_index_equal(result.index, daily_data.index)

    @patch("volforecast.features.implied_correlation.correlation_cache_dir")
    def test_missing_parquet_returns_empty(self, mock_cache_dir, tmp_path):
        """When parquet is missing, returns empty DataFrame with correct columns."""
        # tmp_path exists but contains no parquet file
        mock_cache_dir.return_value = tmp_path

        from volforecast.features.implied_correlation import ImpliedCorrelationLayer

        layer = ImpliedCorrelationLayer()
        daily_data = _make_daily_data()
        result = layer.compute(daily_data)

        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert list(result.columns) == EXPECTED_COLUMNS

    def test_layer_name(self):
        """Instance has name attribute == 'implied_correlation'."""
        from volforecast.features.implied_correlation import ImpliedCorrelationLayer

        layer = ImpliedCorrelationLayer()
        assert layer.name == "implied_correlation"

    @patch("volforecast.features.implied_correlation.correlation_cache_dir")
    def test_forward_fills_missing_dates(self, mock_cache_dir, tmp_path):
        """Dates in daily_data not in parquet get forward-filled (not NaN)."""
        # Create parquet with only Mon/Wed/Fri (skip Tue/Thu)
        idx = pd.bdate_range("2023-01-02", "2023-03-31")
        sparse_idx = idx[idx.dayofweek.isin([0, 2, 4])]  # Mon, Wed, Fri
        rng = np.random.default_rng(99)
        n = len(sparse_idx)
        df = pd.DataFrame(
            {
                "implied_corr_spx_1m": 0.5 + rng.uniform(-0.05, 0.05, n),
                "realized_corr_spx_1m": 0.45 + rng.uniform(-0.05, 0.05, n),
                "corr_risk_premium": rng.uniform(0, 0.1, n),
                "dispersion_signal": 0.20 + rng.uniform(-0.02, 0.02, n),
                "corr_momentum": rng.uniform(-0.01, 0.01, n),
                "corr_zscore": rng.normal(0, 1, n),
            },
            index=sparse_idx,
        )
        df.index.name = "date"
        (tmp_path / "spx_correlation.parquet").unlink(missing_ok=True)
        df.to_parquet(tmp_path / "spx_correlation.parquet")
        mock_cache_dir.return_value = tmp_path

        from volforecast.features.implied_correlation import ImpliedCorrelationLayer

        layer = ImpliedCorrelationLayer()
        # daily_data has ALL business days (including Tue/Thu)
        daily_data = _make_daily_data("2023-01-02", "2023-03-31")
        result = layer.compute(daily_data)

        # After the first observation, there should be no NaN (ffill covers gaps)
        first_valid = result.first_valid_index()
        after_first = result.loc[first_valid:]
        assert not after_first.isna().any().any(), "Forward-fill should eliminate NaN after first observation"

    @patch("volforecast.features.implied_correlation.correlation_cache_dir")
    def test_registered_name(self, mock_cache_dir, tmp_path):
        """Layer is accessible via FEATURE_REGISTRY lookup."""
        _make_correlation_parquet(tmp_path)
        mock_cache_dir.return_value = tmp_path

        # Importing the module triggers registration
        import volforecast.features.implied_correlation  # noqa: F401
        from volforecast.registry import FEATURE_REGISTRY

        assert "implied_correlation" in FEATURE_REGISTRY
        layer_cls = FEATURE_REGISTRY["implied_correlation"]
        assert layer_cls.name == "implied_correlation"
