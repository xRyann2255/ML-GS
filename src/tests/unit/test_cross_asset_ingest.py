"""Tests for cross-asset data ingestion.

Mocks all external API calls (TSDB, edrvol, Marquee).
Verifies: cache logic, parquet output, column structure, context loader.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from volforecast.data.cross_asset_ingest import (
    IngestResult,
    _cache_covers_range,
    ingest_commodity,
    ingest_credit,
    ingest_fx_vol,
    ingest_rates,
    load_cross_asset_context,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_price_series(start: str, end: str, base: float = 100.0) -> pd.Series:
    """Synthetic adjusted close series."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, len(idx))
    prices = base * np.exp(np.cumsum(returns))
    return pd.Series(prices, index=idx, name="price")


def _make_marquee_iv(start: str, end: str, value: float = 0.12) -> pd.Series:
    """Synthetic Marquee implied vol series."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    vals = value + rng.uniform(-0.01, 0.01, len(idx))
    return pd.Series(vals, index=idx, name="impliedVolatility")


def _make_edrvol_df(start: str, end: str, iv_value: float = 15.0) -> pd.DataFrame:
    """Synthetic edrvol DataFrame with iv_1m_atm column."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    vals = iv_value + rng.uniform(-1.0, 1.0, len(idx))
    return pd.DataFrame({"iv_1m_atm": vals}, index=idx)


def _make_treasury_df(start: str, end: str) -> pd.DataFrame:
    """Synthetic treasury data with divergent tenors (post-rename format)."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "yield_5y": 4.2 + rng.uniform(-0.1, 0.1, len(idx)),
            "yield_10y": 4.5 + rng.uniform(-0.1, 0.1, len(idx)),
            "yield_30y": 4.8 + rng.uniform(-0.1, 0.1, len(idx)),
        },
        index=idx,
    )


# ---------------------------------------------------------------------------
# Cache logic
# ---------------------------------------------------------------------------


class TestCacheCoversRange:
    def test_missing_file(self, tmp_path: Path) -> None:
        assert not _cache_covers_range(
            tmp_path / "missing.parquet", date(2024, 1, 2), date(2024, 3, 29)
        )

    def test_cached_covers(self, tmp_path: Path) -> None:
        p = tmp_path / "test.parquet"
        df = pd.DataFrame({"a": [1, 2, 3]}, index=pd.bdate_range("2024-01-02", periods=3))
        df.to_parquet(p)
        assert _cache_covers_range(p, date(2024, 1, 2), date(2024, 1, 4))

    def test_cached_does_not_cover(self, tmp_path: Path) -> None:
        p = tmp_path / "test.parquet"
        df = pd.DataFrame({"a": [1]}, index=pd.bdate_range("2024-01-02", periods=1))
        df.to_parquet(p)
        assert not _cache_covers_range(p, date(2024, 1, 2), date(2024, 3, 29))


# ---------------------------------------------------------------------------
# ingest_rates
# ---------------------------------------------------------------------------


class TestIngestRates:
    @patch("volforecast.data.cross_asset_ingest._fetch_etf_prices")
    @patch("volforecast.data.cross_asset_ingest._fetch_marquee_series")
    @patch("volforecast.data.cross_asset_ingest._fetch_treasury_yields")
    @patch("volforecast.data.cross_asset_ingest.cross_asset_cache_dir")
    def test_writes_parquet(
        self, mock_dir, mock_yields, mock_marquee, mock_prices, tmp_path
    ) -> None:
        mock_dir.return_value = tmp_path
        mock_yields.return_value = _make_treasury_df("2024-01-02", "2024-03-29")

        # Marquee rate vol
        mock_marquee.return_value = _make_marquee_iv("2024-01-02", "2024-03-29", value=6.5)

        # TLT price for realized vol
        tlt_prices = pd.DataFrame(
            {"TLT": _make_price_series("2024-01-02", "2024-03-29", base=95.0).values},
            index=pd.bdate_range("2024-01-02", "2024-03-29"),
        )
        mock_prices.return_value = tlt_prices

        result = ingest_rates(date(2024, 1, 2), date(2024, 3, 29), force=True)
        assert isinstance(result, IngestResult)
        assert result.rows > 0
        assert not result.skipped
        assert result.path == tmp_path / "rates.parquet"

        df = pd.read_parquet(result.path)
        assert "yield_5y" in df.columns
        assert "yield_10y" in df.columns
        assert "yield_slope_10y5y" in df.columns
        assert "rate_vol_1y10y" in df.columns
        assert "tlt_rv_22d" in df.columns

    @patch("volforecast.data.cross_asset_ingest._fetch_treasury_yields")
    @patch("volforecast.data.cross_asset_ingest.cross_asset_cache_dir")
    def test_cache_skip(self, mock_dir, mock_yields, tmp_path) -> None:
        mock_dir.return_value = tmp_path
        # Pre-populate cache covering full range
        df = pd.DataFrame(
            {"yield_5y": range(64)},
            index=pd.bdate_range("2024-01-02", periods=64),
        )
        df.to_parquet(tmp_path / "rates.parquet")

        result = ingest_rates(date(2024, 1, 2), date(2024, 3, 29), force=False)
        assert result.skipped
        mock_yields.assert_not_called()


# ---------------------------------------------------------------------------
# ingest_fx_vol
# ---------------------------------------------------------------------------


class TestIngestFxVol:
    @patch("volforecast.data.cross_asset_ingest._fetch_tsdb_series")
    @patch("volforecast.data.cross_asset_ingest._fetch_marquee_series")
    @patch("volforecast.data.cross_asset_ingest.cross_asset_cache_dir")
    def test_writes_parquet(self, mock_dir, mock_marquee, mock_tsdb, tmp_path) -> None:
        mock_dir.return_value = tmp_path
        mock_marquee.return_value = _make_marquee_iv("2024-01-02", "2024-03-29", value=0.10)

        dxy = pd.Series(
            102.0 + np.arange(62) * 0.1,
            index=pd.bdate_range("2024-01-02", periods=62),
        )
        mock_tsdb.return_value = dxy

        result = ingest_fx_vol(date(2024, 1, 2), date(2024, 3, 29), force=True)
        assert result.rows > 0

        df = pd.read_parquet(result.path)
        assert "fx_iv_usdjpy" in df.columns or "fx_iv_eurusd" in df.columns
        assert "dollar_strength" in df.columns


# ---------------------------------------------------------------------------
# ingest_credit
# ---------------------------------------------------------------------------


class TestIngestCredit:
    @patch("volforecast.data.cross_asset_ingest._fetch_etf_prices")
    @patch("volforecast.data.cross_asset_ingest._fetch_etf_iv")
    @patch("volforecast.data.cross_asset_ingest._fetch_marquee_series")
    @patch("volforecast.data.cross_asset_ingest.cross_asset_cache_dir")
    def test_writes_parquet(
        self, mock_dir, mock_marquee, mock_etf_iv, mock_prices, tmp_path
    ) -> None:
        mock_dir.return_value = tmp_path
        mock_marquee.return_value = _make_marquee_iv("2024-01-02", "2024-03-29", value=42.0)
        mock_etf_iv.return_value = pd.Series(
            15.0 + np.zeros(62), index=pd.bdate_range("2024-01-02", periods=62), name="iv"
        )

        idx = pd.bdate_range("2024-01-02", "2024-03-29")
        prices = pd.DataFrame(
            {
                "HYG": _make_price_series("2024-01-02", "2024-03-29", base=75.0).values,
                "TLT": _make_price_series("2024-01-02", "2024-03-29", base=95.0).values,
                "EEM": _make_price_series("2024-01-02", "2024-03-29", base=40.0).values,
            },
            index=idx,
        )
        mock_prices.return_value = prices

        result = ingest_credit(date(2024, 1, 2), date(2024, 3, 29), force=True)
        assert result.rows > 0

        df = pd.read_parquet(result.path)
        assert "credit_vol_cdx" in df.columns
        assert "credit_stress" in df.columns
        assert "em_risk" in df.columns


# ---------------------------------------------------------------------------
# ingest_commodity
# ---------------------------------------------------------------------------


class TestIngestCommodity:
    @patch("volforecast.data.cross_asset_ingest._fetch_etf_prices")
    @patch("volforecast.data.cross_asset_ingest._fetch_etf_iv")
    @patch("volforecast.data.cross_asset_ingest._fetch_marquee_series")
    @patch("volforecast.data.cross_asset_ingest._fetch_tsdb_series")
    @patch("volforecast.data.cross_asset_ingest.cross_asset_cache_dir")
    def test_writes_parquet(
        self, mock_dir, mock_tsdb, mock_marquee, mock_etf_iv, mock_prices, tmp_path
    ) -> None:
        mock_dir.return_value = tmp_path
        mock_marquee.return_value = _make_marquee_iv("2024-01-02", "2024-03-29", value=0.30)
        mock_tsdb.return_value = pd.Series(
            15.0 + np.zeros(62), index=pd.bdate_range("2024-01-02", periods=62)
        )
        mock_etf_iv.return_value = pd.Series(
            14.0 + np.zeros(62), index=pd.bdate_range("2024-01-02", periods=62)
        )

        idx = pd.bdate_range("2024-01-02", "2024-03-29")
        prices = pd.DataFrame(
            {
                "GLD": _make_price_series("2024-01-02", "2024-03-29", base=185.0).values,
                "USO": _make_price_series("2024-01-02", "2024-03-29", base=72.0).values,
            },
            index=idx,
        )
        mock_prices.return_value = prices

        result = ingest_commodity(date(2024, 1, 2), date(2024, 3, 29), force=True)
        assert result.rows > 0

        df = pd.read_parquet(result.path)
        assert "commodity_vol_cl" in df.columns
        assert "gvz" in df.columns
        assert "gold_vol" in df.columns


# ---------------------------------------------------------------------------
# load_cross_asset_context
# ---------------------------------------------------------------------------


class TestLoadContext:
    def test_raises_when_no_files(self, tmp_path: Path) -> None:
        with patch(
            "volforecast.data.cross_asset_ingest.cross_asset_cache_dir", return_value=tmp_path
        ):
            with pytest.raises(FileNotFoundError, match="No cross-asset data found"):
                load_cross_asset_context()

    def test_returns_dict_with_parquets(self, tmp_path: Path) -> None:
        # Create minimal parquets
        idx = pd.bdate_range("2024-01-02", periods=5)
        for name in ("rates", "fx_vol", "credit", "commodity"):
            df = pd.DataFrame({"col": range(5)}, index=idx)
            df.to_parquet(tmp_path / f"{name}.parquet")

        with (
            patch(
                "volforecast.data.cross_asset_ingest.cross_asset_cache_dir", return_value=tmp_path
            ),
            patch("volforecast.utils.paths.iv_cache_dir", return_value=tmp_path),
        ):
            ctx = load_cross_asset_context()
            assert "treasury" in ctx
            assert "fx" in ctx
            assert "credit" in ctx
            assert "commodity" in ctx
            assert "vix" in ctx
            assert len(ctx["treasury"]) == 5
