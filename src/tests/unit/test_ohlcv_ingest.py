"""Tests for OHLCV ingestion from TSDB.

TDD: Tests written first, implementation follows.
Mocks all external API calls (TSDB).
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers: synthetic data generators
# ---------------------------------------------------------------------------


def _make_tsdb_series(
    start: str = "2024-01-02",
    end: str = "2024-01-31",
    base: float = 150.0,
    noise_scale: float = 2.0,
) -> pd.Series:
    """Create a synthetic TSDB-like price series."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    values = base + np.cumsum(rng.normal(0, noise_scale, len(idx)))
    return pd.Series(values, index=idx)


def _make_volume_series(
    start: str = "2024-01-02",
    end: str = "2024-01-31",
) -> pd.Series:
    """Create a synthetic volume series."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(99)
    values = rng.integers(1_000_000, 50_000_000, len(idx)).astype(float)
    return pd.Series(values, index=idx)


# ---------------------------------------------------------------------------
# Tests: fetch_ohlcv
# ---------------------------------------------------------------------------


class TestFetchOhlcv:
    """Test the OHLCV fetch function."""

    @patch("volforecast.data.ohlcv._get_tsdb_data")
    def test_returns_dataframe_with_five_columns(self, mock_tsdb):
        from volforecast.data.ohlcv import fetch_ohlcv

        # Mock: 3 raw prices + 1 adj close + 1 volume = 5 calls
        mock_tsdb.return_value = _make_tsdb_series()

        result = fetch_ohlcv("AAPL", date(2024, 1, 2), date(2024, 1, 31))

        assert isinstance(result, pd.DataFrame)
        assert set(result.columns) == {"open", "high", "low", "close", "volume"}

    @patch("volforecast.data.ohlcv._get_tsdb_data")
    def test_index_is_datetimeindex(self, mock_tsdb):
        from volforecast.data.ohlcv import fetch_ohlcv

        mock_tsdb.return_value = _make_tsdb_series()

        result = fetch_ohlcv("AAPL", date(2024, 1, 2), date(2024, 1, 31))

        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index.name == "date"

    @patch("volforecast.data.ohlcv._get_tsdb_data")
    def test_adjustment_applied_to_open_high_low(self, mock_tsdb):
        """Verify adjusted prices use the adj_close/raw_close factor."""
        from volforecast.data.ohlcv import fetch_ohlcv

        idx = pd.bdate_range("2024-01-02", "2024-01-05")
        raw_open = pd.Series([100.0, 102.0, 104.0, 106.0], index=idx)
        raw_high = pd.Series([105.0, 107.0, 109.0, 111.0], index=idx)
        raw_low = pd.Series([98.0, 100.0, 102.0, 104.0], index=idx)
        raw_close = pd.Series([103.0, 105.0, 107.0, 109.0], index=idx)
        # Simulate a 2:1 split on day 3: adj_close = raw_close * 0.5 for first 2 days
        adj_close = pd.Series([51.5, 52.5, 107.0, 109.0], index=idx)
        volume = pd.Series([1e6, 2e6, 3e6, 4e6], index=idx)

        def side_effect(symbol, start, end):
            if "open" in symbol and "adj" not in symbol:
                return raw_open
            elif "high" in symbol:
                return raw_high
            elif "low" in symbol:
                return raw_low
            elif "close.adj" in symbol:
                return adj_close
            elif "close" in symbol:
                return raw_close
            elif "volume" in symbol:
                return volume
            return pd.Series(dtype=float)

        mock_tsdb.side_effect = side_effect

        result = fetch_ohlcv("AAPL", date(2024, 1, 2), date(2024, 1, 5))

        # Adjustment factor = adj_close / raw_close
        factor = adj_close / raw_close
        expected_open = raw_open * factor
        expected_high = raw_high * factor
        expected_low = raw_low * factor

        pd.testing.assert_series_equal(result["open"], expected_open, check_names=False)
        pd.testing.assert_series_equal(result["high"], expected_high, check_names=False)
        pd.testing.assert_series_equal(result["low"], expected_low, check_names=False)
        pd.testing.assert_series_equal(result["close"], adj_close, check_names=False)

    @patch("volforecast.data.ohlcv._get_tsdb_data")
    def test_volume_is_unadjusted(self, mock_tsdb):
        """Volume should NOT be adjusted for splits."""
        from volforecast.data.ohlcv import fetch_ohlcv

        idx = pd.bdate_range("2024-01-02", "2024-01-05")
        price = pd.Series([100.0, 102.0, 104.0, 106.0], index=idx)
        volume = pd.Series([1e6, 2e6, 3e6, 4e6], index=idx)

        def side_effect(symbol, start, end):
            if "volume" in symbol:
                return volume
            return price

        mock_tsdb.side_effect = side_effect

        result = fetch_ohlcv("AAPL", date(2024, 1, 2), date(2024, 1, 5))

        pd.testing.assert_series_equal(result["volume"], volume, check_names=False)

    def test_futures_raises_valueerror(self):
        """Futures symbols (ES) have no eqpad_ RIC and should raise."""
        from volforecast.data.ohlcv import fetch_ohlcv

        with pytest.raises(ValueError, match="No RIC mapping"):
            fetch_ohlcv("ES", date(2024, 1, 2), date(2024, 1, 31))

    @patch("volforecast.data.ohlcv._get_tsdb_data")
    def test_empty_tsdb_returns_empty_dataframe(self, mock_tsdb):
        from volforecast.data.ohlcv import fetch_ohlcv

        mock_tsdb.return_value = pd.Series(dtype=float)

        result = fetch_ohlcv("AAPL", date(2024, 1, 2), date(2024, 1, 31))

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        assert set(result.columns) == {"open", "high", "low", "close", "volume"}


# ---------------------------------------------------------------------------
# Tests: save/load cache
# ---------------------------------------------------------------------------


class TestOhlcvCache:
    """Test save/load roundtrip and cache coverage check."""

    def test_save_load_roundtrip(self, tmp_path):
        from volforecast.data.ohlcv import load_ohlcv_cache, save_ohlcv_cache

        idx = pd.bdate_range("2024-01-02", "2024-01-31")
        df = pd.DataFrame(
            {
                "open": np.random.default_rng(1).uniform(100, 200, len(idx)),
                "high": np.random.default_rng(2).uniform(100, 200, len(idx)),
                "low": np.random.default_rng(3).uniform(100, 200, len(idx)),
                "close": np.random.default_rng(4).uniform(100, 200, len(idx)),
                "volume": np.random.default_rng(5).integers(1e6, 5e7, len(idx)).astype(float),
            },
            index=idx,
        )
        df.index.name = "date"

        mock_path = tmp_path / "AAPL.parquet"
        with patch("volforecast.data.ohlcv.ohlcv_cache_path", return_value=mock_path):
            save_ohlcv_cache("AAPL", df)
            loaded = load_ohlcv_cache("AAPL")

        assert loaded is not None
        pd.testing.assert_frame_equal(loaded, df, check_freq=False)

    def test_load_missing_returns_none(self, tmp_path):
        from volforecast.data.ohlcv import load_ohlcv_cache

        mock_path = tmp_path / "MISSING.parquet"
        with patch("volforecast.data.ohlcv.ohlcv_cache_path", return_value=mock_path):
            result = load_ohlcv_cache("MISSING")

        assert result is None

    def test_cache_covers_range_true(self, tmp_path):
        from volforecast.data.ohlcv import cache_covers_range, save_ohlcv_cache

        idx = pd.bdate_range("2024-01-02", "2024-03-29")
        df = pd.DataFrame(
            {
                "open": np.ones(len(idx)),
                "high": np.ones(len(idx)),
                "low": np.ones(len(idx)),
                "close": np.ones(len(idx)),
                "volume": np.ones(len(idx)),
            },
            index=idx,
        )
        df.index.name = "date"

        path = tmp_path / "SPY.parquet"
        with patch("volforecast.data.ohlcv.ohlcv_cache_path", return_value=path):
            save_ohlcv_cache("SPY", df)
            assert cache_covers_range("SPY", date(2024, 1, 5), date(2024, 3, 15)) is True

    def test_cache_covers_range_false_no_file(self, tmp_path):
        from volforecast.data.ohlcv import cache_covers_range

        mock_path = tmp_path / "NOPE.parquet"
        with patch("volforecast.data.ohlcv.ohlcv_cache_path", return_value=mock_path):
            assert cache_covers_range("NOPE", date(2024, 1, 2), date(2024, 3, 29)) is False

    def test_cache_covers_range_false_partial(self, tmp_path):
        from volforecast.data.ohlcv import cache_covers_range, save_ohlcv_cache

        # Cache only covers Jan, but we ask for Jan-Mar
        idx = pd.bdate_range("2024-01-02", "2024-01-31")
        df = pd.DataFrame(
            {
                "open": np.ones(len(idx)),
                "high": np.ones(len(idx)),
                "low": np.ones(len(idx)),
                "close": np.ones(len(idx)),
                "volume": np.ones(len(idx)),
            },
            index=idx,
        )
        df.index.name = "date"

        path = tmp_path / "SPY.parquet"
        with patch("volforecast.data.ohlcv.ohlcv_cache_path", return_value=path):
            save_ohlcv_cache("SPY", df)
            assert cache_covers_range("SPY", date(2024, 1, 2), date(2024, 3, 29)) is False


# ---------------------------------------------------------------------------
# Tests: CLI run function
# ---------------------------------------------------------------------------


class TestIngestOhlcvRun:
    """Test the CLI run orchestration."""

    @patch("volforecast.cli.ingest_ohlcv.fetch_ohlcv")
    @patch("volforecast.cli.ingest_ohlcv.save_ohlcv_cache")
    @patch("volforecast.cli.ingest_ohlcv.cache_covers_range", return_value=False)
    @patch("volforecast.cli.ingest_ohlcv.record_ingestion_yaml")
    def test_run_ingests_symbols(self, mock_manifest, mock_covers, mock_save, mock_fetch):
        from volforecast.cli.ingest_ohlcv import run

        idx = pd.bdate_range("2024-01-02", "2024-01-31")
        df = pd.DataFrame(
            {
                "open": np.ones(len(idx)),
                "high": np.ones(len(idx)),
                "low": np.ones(len(idx)),
                "close": np.ones(len(idx)),
                "volume": np.ones(len(idx)),
            },
            index=idx,
        )
        df.index.name = "date"
        mock_fetch.return_value = df

        result = run(date(2024, 1, 2), date(2024, 1, 31), symbols=["AAPL", "SPY"])

        assert result == 0
        assert mock_fetch.call_count == 2
        assert mock_save.call_count == 2
        assert mock_manifest.call_count == 2

    @patch("volforecast.cli.ingest_ohlcv.fetch_ohlcv")
    @patch("volforecast.cli.ingest_ohlcv.save_ohlcv_cache")
    @patch("volforecast.cli.ingest_ohlcv.cache_covers_range", return_value=True)
    @patch("volforecast.cli.ingest_ohlcv.record_ingestion_yaml")
    def test_run_skips_cached(self, mock_manifest, mock_covers, mock_save, mock_fetch):
        from volforecast.cli.ingest_ohlcv import run

        result = run(date(2024, 1, 2), date(2024, 1, 31), symbols=["AAPL"])

        assert result == 0
        mock_fetch.assert_not_called()
        mock_save.assert_not_called()

    @patch("volforecast.cli.ingest_ohlcv.fetch_ohlcv")
    @patch("volforecast.cli.ingest_ohlcv.save_ohlcv_cache")
    @patch("volforecast.cli.ingest_ohlcv.cache_covers_range", return_value=True)
    @patch("volforecast.cli.ingest_ohlcv.record_ingestion_yaml")
    def test_run_force_refetches(self, mock_manifest, mock_covers, mock_save, mock_fetch):
        from volforecast.cli.ingest_ohlcv import run

        idx = pd.bdate_range("2024-01-02", "2024-01-31")
        df = pd.DataFrame(
            {
                "open": np.ones(len(idx)),
                "high": np.ones(len(idx)),
                "low": np.ones(len(idx)),
                "close": np.ones(len(idx)),
                "volume": np.ones(len(idx)),
            },
            index=idx,
        )
        df.index.name = "date"
        mock_fetch.return_value = df

        result = run(date(2024, 1, 2), date(2024, 1, 31), symbols=["AAPL"], force=True)

        assert result == 0
        mock_fetch.assert_called_once()
        mock_save.assert_called_once()

    @patch("volforecast.cli.ingest_ohlcv.fetch_ohlcv")
    @patch("volforecast.cli.ingest_ohlcv.save_ohlcv_cache")
    @patch("volforecast.cli.ingest_ohlcv.cache_covers_range", return_value=False)
    @patch("volforecast.cli.ingest_ohlcv.record_ingestion_yaml")
    def test_run_handles_failure_gracefully(
        self,
        mock_manifest,
        mock_covers,
        mock_save,
        mock_fetch,
    ):
        """One symbol failure should not abort the rest."""
        from volforecast.cli.ingest_ohlcv import run

        idx = pd.bdate_range("2024-01-02", "2024-01-31")
        df = pd.DataFrame(
            {
                "open": np.ones(len(idx)),
                "high": np.ones(len(idx)),
                "low": np.ones(len(idx)),
                "close": np.ones(len(idx)),
                "volume": np.ones(len(idx)),
            },
            index=idx,
        )
        df.index.name = "date"

        # First call fails, second succeeds
        mock_fetch.side_effect = [ConnectionError("TSDB down"), df]

        result = run(date(2024, 1, 2), date(2024, 1, 31), symbols=["AAPL", "SPY"])

        # Non-zero exit due to failure
        assert result == 1
        # But SPY should still be saved
        assert mock_save.call_count == 1
        assert mock_manifest.call_count == 1
