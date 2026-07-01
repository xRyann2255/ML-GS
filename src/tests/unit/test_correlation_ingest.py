"""Tests for volforecast.data.correlation_ingest."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from volforecast.data.correlation_ingest import (
    ingest_correlation,
    load_correlation_context,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_corr_series(start: str, end: str, base: float = 0.5) -> pd.Series:
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    vals = base + rng.uniform(-0.05, 0.05, len(idx))
    return pd.Series(vals, index=idx, name="correlation")


def _make_vol_series(start: str, end: str, base: float = 0.20) -> pd.Series:
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    vals = base + rng.uniform(-0.02, 0.02, len(idx))
    return pd.Series(vals, index=idx, name="volatility")


PATCH_BASE = "volforecast.data.correlation_ingest"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch(f"{PATCH_BASE}.correlation_cache_dir")
class TestCacheHitSkips:
    def test_cache_hit_skips(self, mock_cache_dir, tmp_path: Path):
        """Existing parquet covers requested date range → skipped=True, no fetch."""
        mock_cache_dir.return_value = tmp_path

        # Pre-populate cache with data covering 2024-01-02 to 2024-03-29
        idx = pd.bdate_range("2024-01-02", "2024-03-29")
        df = pd.DataFrame(
            {
                "implied_corr_spx_1m": np.full(len(idx), 0.5),
                "realized_corr_spx_1m": np.full(len(idx), 0.45),
                "corr_risk_premium": np.full(len(idx), 0.05),
                "corr_momentum": np.full(len(idx), 0.0),
                "corr_zscore": np.full(len(idx), 0.0),
                "dispersion_signal": np.full(len(idx), 0.20),
            },
            index=idx,
        )
        parquet_path = tmp_path / "spx_correlation.parquet"
        df.to_parquet(parquet_path)

        result = ingest_correlation(
            start_date=date(2024, 1, 15), end_date=date(2024, 3, 15), force=False
        )

        assert result.skipped is True
        assert result.rows == 0
        assert result.path == parquet_path


@patch(f"{PATCH_BASE}._fetch_marquee_series")
@patch(f"{PATCH_BASE}.correlation_cache_dir")
class TestFetchesAndWritesParquet:
    def test_fetches_and_writes_parquet(
        self, mock_cache_dir, mock_fetch, tmp_path: Path
    ):
        """Mock marquee returns data → parquet written with correct columns."""
        mock_cache_dir.return_value = tmp_path

        start, end = "2024-01-02", "2024-03-29"
        implied = _make_corr_series(start, end, base=0.55)
        realized = _make_corr_series(start, end, base=0.45)
        avg_iv = _make_vol_series(start, end, base=0.20)

        # _fetch_marquee_series is called 3 times for the 3 datasets
        mock_fetch.side_effect = [implied, realized, avg_iv]

        result = ingest_correlation(
            start_date=date(2024, 1, 2), end_date=date(2024, 3, 29), force=False
        )

        assert result.skipped is False
        assert result.rows > 0

        parquet_path = tmp_path / "spx_correlation.parquet"
        assert parquet_path.exists()

        df = pd.read_parquet(parquet_path)
        expected_cols = {
            "implied_corr_spx_1m",
            "realized_corr_spx_1m",
            "corr_risk_premium",
            "corr_momentum",
            "corr_zscore",
            "dispersion_signal",
        }
        assert set(df.columns) == expected_cols


@patch(f"{PATCH_BASE}._fetch_marquee_series")
@patch(f"{PATCH_BASE}.correlation_cache_dir")
class TestDerivedColumnsCorrect:
    def test_derived_columns_correct(
        self, mock_cache_dir, mock_fetch, tmp_path: Path
    ):
        """CRP = implied - realized, momentum = diff(implied), zscore formula."""
        mock_cache_dir.return_value = tmp_path

        start, end = "2024-01-02", "2024-06-28"
        implied = _make_corr_series(start, end, base=0.55)
        realized = _make_corr_series(start, end, base=0.45)
        avg_iv = _make_vol_series(start, end, base=0.20)

        mock_fetch.side_effect = [implied, realized, avg_iv]

        ingest_correlation(
            start_date=date(2024, 1, 2), end_date=date(2024, 6, 28), force=False
        )

        df = pd.read_parquet(tmp_path / "spx_correlation.parquet")

        # corr_risk_premium = implied - realized
        expected_crp = implied.values - realized.values
        np.testing.assert_allclose(
            df["corr_risk_premium"].values, expected_crp, atol=1e-10
        )

        # corr_momentum = diff(implied, 1) — first value is NaN
        expected_momentum = implied.diff(1)
        np.testing.assert_allclose(
            df["corr_momentum"].values[1:], expected_momentum.values[1:], atol=1e-10
        )
        assert pd.isna(df["corr_momentum"].iloc[0])

        # corr_zscore = (implied - SMA_60) / std_60
        sma60 = implied.rolling(60).mean()
        std60 = implied.rolling(60).std()
        expected_zscore = (implied - sma60) / std60
        # Only compare where we have enough data (row 59+)
        valid = ~expected_zscore.isna()
        np.testing.assert_allclose(
            df["corr_zscore"].values[valid.values],
            expected_zscore.values[valid.values],
            atol=1e-10,
        )


@patch(f"{PATCH_BASE}._fetch_marquee_series")
@patch(f"{PATCH_BASE}.correlation_cache_dir")
class TestEmptyResponseHandlesGracefully:
    def test_empty_response_handles_gracefully(
        self, mock_cache_dir, mock_fetch, tmp_path: Path
    ):
        """One or more datasets return empty Series → handles gracefully."""
        mock_cache_dir.return_value = tmp_path

        start, end = "2024-01-02", "2024-03-29"
        implied = _make_corr_series(start, end, base=0.55)
        realized = pd.Series(dtype=float)  # empty
        avg_iv = _make_vol_series(start, end, base=0.20)

        mock_fetch.side_effect = [implied, realized, avg_iv]

        # Should not raise — graceful handling
        result = ingest_correlation(
            start_date=date(2024, 1, 2), end_date=date(2024, 3, 29), force=False
        )
        assert result is not None


@patch(f"{PATCH_BASE}._fetch_marquee_series")
@patch(f"{PATCH_BASE}.correlation_cache_dir")
class TestForceRefetches:
    def test_force_refetches(
        self, mock_cache_dir, mock_fetch, tmp_path: Path
    ):
        """Even with existing cache, force=True refetches."""
        mock_cache_dir.return_value = tmp_path

        # Pre-populate cache
        idx = pd.bdate_range("2024-01-02", "2024-03-29")
        df = pd.DataFrame(
            {
                "implied_corr_spx_1m": np.full(len(idx), 0.5),
                "realized_corr_spx_1m": np.full(len(idx), 0.45),
                "corr_risk_premium": np.full(len(idx), 0.05),
                "corr_momentum": np.full(len(idx), 0.0),
                "corr_zscore": np.full(len(idx), 0.0),
                "dispersion_signal": np.full(len(idx), 0.20),
            },
            index=idx,
        )
        parquet_path = tmp_path / "spx_correlation.parquet"
        df.to_parquet(parquet_path)

        start, end = "2024-01-02", "2024-03-29"
        implied = _make_corr_series(start, end, base=0.60)
        realized = _make_corr_series(start, end, base=0.40)
        avg_iv = _make_vol_series(start, end, base=0.22)

        mock_fetch.side_effect = [implied, realized, avg_iv]

        result = ingest_correlation(
            start_date=date(2024, 1, 2), end_date=date(2024, 3, 29), force=True
        )

        assert result.skipped is False
        assert result.rows > 0
        assert mock_fetch.call_count == 3


@patch(f"{PATCH_BASE}.correlation_cache_dir")
class TestLoadCorrelationContext:
    def test_load_correlation_context(self, mock_cache_dir, tmp_path: Path):
        """Reads cached parquet correctly."""
        mock_cache_dir.return_value = tmp_path

        idx = pd.bdate_range("2024-01-02", "2024-03-29")
        df = pd.DataFrame(
            {
                "implied_corr_spx_1m": np.full(len(idx), 0.5),
                "realized_corr_spx_1m": np.full(len(idx), 0.45),
                "corr_risk_premium": np.full(len(idx), 0.05),
                "corr_momentum": np.full(len(idx), 0.0),
                "corr_zscore": np.full(len(idx), 0.0),
                "dispersion_signal": np.full(len(idx), 0.20),
            },
            index=idx,
        )
        parquet_path = tmp_path / "spx_correlation.parquet"
        df.to_parquet(parquet_path)

        result = load_correlation_context()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(idx)
        assert set(result.columns) == set(df.columns)

    def test_load_correlation_context_missing_file(
        self, mock_cache_dir, tmp_path: Path
    ):
        """Returns empty DataFrame when no cached file exists."""
        mock_cache_dir.return_value = tmp_path

        result = load_correlation_context()

        assert isinstance(result, pd.DataFrame)
        assert result.empty
