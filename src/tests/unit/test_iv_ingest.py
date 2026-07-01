"""Tests for IV surface ingestion from Marquee.

TDD: Tests written first, implementation follows.
Mocks all external API calls (Marquee Dataset, TSDB).
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Helpers: synthetic data generators
# ---------------------------------------------------------------------------


def _make_raw_erdvol(
    start: str = "2024-01-02",
    end: str = "2024-01-31",
    tenors: list[str] | None = None,
) -> pd.DataFrame:
    """Create synthetic EDRVOL_PERCENT DataFrame matching Marquee schema."""
    if tenors is None:
        tenors = ["1m", "3m"]
    strikes = [0.25, 1.0, 0.75]
    strike_refs = ["delta", "forward", "delta"]

    dates = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    rows = []
    for d in dates:
        for tenor in tenors:
            for strike, ref in zip(strikes, strike_refs):
                # 25d put (0.75) > ATM (1.0) > 25d call (0.25) for SPX skew
                base_iv = 0.15 if strike == 1.0 else (0.22 if strike == 0.75 else 0.10)
                rows.append(
                    {
                        "date": d,
                        "tenor": tenor,
                        "relativeStrike": strike,
                        "strikeReference": ref,
                        "impliedVolatility": base_iv + rng.uniform(-0.02, 0.02),
                        "bbid": "SPX",
                    }
                )
    df = pd.DataFrame(rows)
    df.index = pd.DatetimeIndex(df["date"])
    df.index.name = None
    return df.drop(columns=["date"])


def _make_vix_series(start: str = "2024-01-02", end: str = "2024-01-31") -> pd.Series:
    """Create synthetic VIX series."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    values = 15.0 + np.cumsum(rng.normal(0, 0.3, len(idx)))
    return pd.Series(values, index=idx, name="close")


# ---------------------------------------------------------------------------
# Tests: ingest_iv_surface
# ---------------------------------------------------------------------------


class TestIngestIvSurface:
    """Test the main IV surface ingestion function."""

    @patch("volforecast.data.iv_ingest._fetch_vix_daily")
    @patch("volforecast.data.iv_ingest._fetch_raw_iv_surface")
    def test_returns_dataframe(self, mock_iv, mock_vix):
        from volforecast.data.iv_ingest import ingest_iv_surface

        mock_iv.return_value = _make_raw_erdvol()
        mock_vix.return_value = _make_vix_series()

        result = ingest_iv_surface(date(2024, 1, 2), date(2024, 1, 31))
        assert isinstance(result, pd.DataFrame)

    @patch("volforecast.data.iv_ingest._fetch_vix_daily")
    @patch("volforecast.data.iv_ingest._fetch_raw_iv_surface")
    def test_has_required_columns(self, mock_iv, mock_vix):
        from volforecast.data.iv_ingest import ingest_iv_surface

        mock_iv.return_value = _make_raw_erdvol()
        mock_vix.return_value = _make_vix_series()

        result = ingest_iv_surface(date(2024, 1, 2), date(2024, 1, 31))
        expected_cols = {
            "atm_iv_1m",
            "atm_iv_3m",
            "iv_put_25d_1m",
            "iv_call_25d_1m",
            "skew_1m",
            "vix",
        }
        assert expected_cols.issubset(set(result.columns))

    @patch("volforecast.data.iv_ingest._fetch_vix_daily")
    @patch("volforecast.data.iv_ingest._fetch_raw_iv_surface")
    def test_index_is_datetime(self, mock_iv, mock_vix):
        from volforecast.data.iv_ingest import ingest_iv_surface

        mock_iv.return_value = _make_raw_erdvol()
        mock_vix.return_value = _make_vix_series()

        result = ingest_iv_surface(date(2024, 1, 2), date(2024, 1, 31))
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index.name == "date"

    @patch("volforecast.data.iv_ingest._fetch_vix_daily")
    @patch("volforecast.data.iv_ingest._fetch_raw_iv_surface")
    def test_atm_iv_uses_forward_strike_ref(self, mock_iv, mock_vix):
        """ATM IV must filter strikeReference='forward' to avoid duplicates."""
        from volforecast.data.iv_ingest import ingest_iv_surface

        mock_iv.return_value = _make_raw_erdvol()
        mock_vix.return_value = _make_vix_series()

        result = ingest_iv_surface(date(2024, 1, 2), date(2024, 1, 31))
        # ATM IV should have one value per day (no duplicates from multiple strikeRefs)
        assert not result["atm_iv_1m"].isna().all()
        assert result["atm_iv_1m"].notna().sum() == len(result)

    @patch("volforecast.data.iv_ingest._fetch_vix_daily")
    @patch("volforecast.data.iv_ingest._fetch_raw_iv_surface")
    def test_skew_is_put_minus_call(self, mock_iv, mock_vix):
        """Skew = IV(25d put) - IV(25d call), should be positive for SPX."""
        from volforecast.data.iv_ingest import ingest_iv_surface

        mock_iv.return_value = _make_raw_erdvol()
        mock_vix.return_value = _make_vix_series()

        result = ingest_iv_surface(date(2024, 1, 2), date(2024, 1, 31))
        # Our synthetic data: put IV ~0.22, call IV ~0.12 → skew ~0.10
        expected_skew = result["iv_put_25d_1m"] - result["iv_call_25d_1m"]
        pd.testing.assert_series_equal(result["skew_1m"], expected_skew, check_names=False)

    @patch("volforecast.data.iv_ingest._fetch_vix_daily")
    @patch("volforecast.data.iv_ingest._fetch_raw_iv_surface")
    def test_vix_aligned_to_iv_dates(self, mock_iv, mock_vix):
        from volforecast.data.iv_ingest import ingest_iv_surface

        mock_iv.return_value = _make_raw_erdvol()
        mock_vix.return_value = _make_vix_series()

        result = ingest_iv_surface(date(2024, 1, 2), date(2024, 1, 31))
        # VIX should be present and aligned
        assert result["vix"].notna().sum() > 0

    @patch("volforecast.data.iv_ingest._fetch_vix_daily")
    @patch("volforecast.data.iv_ingest._fetch_raw_iv_surface")
    def test_values_in_decimal(self, mock_iv, mock_vix):
        """IV values should be in decimal (0.15), not percentage (15.0)."""
        from volforecast.data.iv_ingest import ingest_iv_surface

        mock_iv.return_value = _make_raw_erdvol()
        mock_vix.return_value = _make_vix_series()

        result = ingest_iv_surface(date(2024, 1, 2), date(2024, 1, 31))
        # ATM IV should be in [0.05, 0.60] range (not percentage)
        assert result["atm_iv_1m"].max() < 1.0
        assert result["atm_iv_1m"].min() > 0.0


class TestIngestCaching:
    """Test parquet save/load round-trip."""

    @patch("volforecast.data.iv_ingest._fetch_vix_daily")
    @patch("volforecast.data.iv_ingest._fetch_raw_iv_surface")
    def test_save_and_load(self, mock_iv, mock_vix, tmp_path):
        from volforecast.data.iv_ingest import ingest_iv_surface, load_iv_cache, save_iv_cache

        mock_iv.return_value = _make_raw_erdvol()
        mock_vix.return_value = _make_vix_series()

        panel = ingest_iv_surface(date(2024, 1, 2), date(2024, 1, 31))
        cache_path = tmp_path / "iv_surface_spx.parquet"
        save_iv_cache(panel, cache_path)

        loaded = load_iv_cache(cache_path)
        pd.testing.assert_frame_equal(panel, loaded)

    def test_load_nonexistent_returns_none(self, tmp_path):
        from volforecast.data.iv_ingest import load_iv_cache

        result = load_iv_cache(tmp_path / "nonexistent.parquet")
        assert result is None
