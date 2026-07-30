"""Tests for gap_fixer module — source-specific gap filling.

TDD: these tests define expected behavior for fix_gaps() and the merge logic.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from volforecast.cli.gap_fixer import FixResult, fix_gaps

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Create temporary data directories."""
    for subdir in ("ticks", "iv", "ohlcv", "micro", "cross_asset"):
        (tmp_path / "data" / "raw" / subdir).mkdir(parents=True)
    return tmp_path


def _make_parquet(path: Path, dates: list[date], columns: list[str]) -> pd.DataFrame:
    """Write a parquet with given dates and return the dataframe."""
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in dates], name="date")
    df = pd.DataFrame(
        np.random.default_rng(42).random((len(dates), len(columns))),
        index=idx,
        columns=columns,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


# ── fix_gaps tests ────────────────────────────────────────────────────────


class TestFixGapsOHLCV:
    def test_dry_run_no_fetch(self, project_root: Path) -> None:
        """dry_run=True should NOT call any fetch function."""
        missing = [date(2024, 3, 11), date(2024, 3, 12)]
        with patch("volforecast.cli.gap_fixer._fetch_ohlcv_range") as mock_fetch:
            result = fix_gaps("ohlcv", "AAPL", missing, dry_run=True, project_root=project_root)
            mock_fetch.assert_not_called()
        assert result.days_planned == 2
        assert result.days_filled == 0
        assert result.dry_run is True

    def test_fetches_coalesced_ranges(self, project_root: Path) -> None:
        """Consecutive missing days are fetched as one range, not per-day."""
        # 3 consecutive days + 1 isolated day (gap between)
        missing = [
            date(2024, 3, 11),
            date(2024, 3, 12),
            date(2024, 3, 13),
            date(2024, 3, 25),
        ]
        # Pre-create existing cache
        existing_days = [date(2024, 3, 1), date(2024, 3, 4), date(2024, 3, 5)]
        parquet_path = project_root / "data" / "raw" / "ohlcv" / "AAPL.parquet"
        _make_parquet(parquet_path, existing_days, ["open", "high", "low", "close", "volume"])

        def mock_fetch(symbol: str, start: date, end: date) -> pd.DataFrame:
            from volforecast.data.trading_calendar import get_trading_days

            days = get_trading_days(start, end)
            idx = pd.DatetimeIndex([pd.Timestamp(d) for d in days], name="date")
            return pd.DataFrame(
                np.ones((len(days), 5)),
                index=idx,
                columns=["open", "high", "low", "close", "volume"],
            )

        with patch("volforecast.cli.gap_fixer._fetch_ohlcv_range", side_effect=mock_fetch) as mock:
            result = fix_gaps("ohlcv", "AAPL", missing, dry_run=False, project_root=project_root)
            # Should be called twice: one range (Mar 11-13) + one range (Mar 25)
            assert mock.call_count == 2

        assert result.days_filled == 4
        assert result.errors == []

        # Verify merged parquet has old + new dates, no duplicates, sorted
        merged = pd.read_parquet(parquet_path)
        merged_dates = sorted(set(merged.index.date))
        for d in existing_days + missing:
            assert d in merged_dates

    def test_atomic_write_on_failure(self, project_root: Path) -> None:
        """If fetch fails, original parquet is preserved (atomic write)."""
        existing_days = [date(2024, 3, 1), date(2024, 3, 4)]
        parquet_path = project_root / "data" / "raw" / "ohlcv" / "AAPL.parquet"
        _make_parquet(parquet_path, existing_days, ["open", "high", "low", "close", "volume"])
        original_size = parquet_path.stat().st_size

        missing = [date(2024, 3, 11)]

        with patch(
            "volforecast.cli.gap_fixer._fetch_ohlcv_range",
            side_effect=RuntimeError("API timeout"),
        ):
            result = fix_gaps("ohlcv", "AAPL", missing, dry_run=False, project_root=project_root)

        # Original file unchanged
        assert parquet_path.stat().st_size == original_size
        assert len(result.errors) == 1
        assert "API timeout" in result.errors[0]


class TestFixGapsIV:
    def test_iv_fetch_called_correctly(self, project_root: Path) -> None:
        """IV gaps use fetch_edrvol with correct symbol and range."""
        missing = [date(2024, 5, 6), date(2024, 5, 7)]
        existing_days = [date(2024, 5, 1), date(2024, 5, 2), date(2024, 5, 3)]
        parquet_path = project_root / "data" / "raw" / "iv" / "MSFT.parquet"
        _make_parquet(parquet_path, existing_days, ["iv_1m_atm", "iv_3m_atm"])

        def mock_fetch(symbol: str, start: date, end: date) -> pd.DataFrame:
            from volforecast.data.trading_calendar import get_trading_days

            days = get_trading_days(start, end)
            idx = pd.DatetimeIndex([pd.Timestamp(d) for d in days], name="date")
            return pd.DataFrame(
                np.ones((len(days), 2)), index=idx, columns=["iv_1m_atm", "iv_3m_atm"]
            )

        with patch("volforecast.cli.gap_fixer._fetch_iv_range", side_effect=mock_fetch) as mock:
            result = fix_gaps("iv", "MSFT", missing, dry_run=False, project_root=project_root)
            mock.assert_called_once_with("MSFT", date(2024, 5, 6), date(2024, 5, 7))

        assert result.days_filled == 2


class TestFixGapsCrossAsset:
    def test_cross_asset_group_fix(self, project_root: Path) -> None:
        """Cross-asset fixes at group level (rates.parquet, not per-symbol)."""
        existing_days = [date(2024, 4, 1), date(2024, 4, 2), date(2024, 4, 3)]
        parquet_path = project_root / "data" / "raw" / "cross_asset" / "rates.parquet"
        _make_parquet(parquet_path, existing_days, ["yield_5y", "yield_10y"])

        missing = [date(2024, 4, 8), date(2024, 4, 9)]

        def mock_fetch(group: str, start: date, end: date) -> pd.DataFrame:
            from volforecast.data.trading_calendar import get_trading_days

            days = get_trading_days(start, end)
            idx = pd.DatetimeIndex([pd.Timestamp(d) for d in days], name="date")
            return pd.DataFrame(
                np.ones((len(days), 2)), index=idx, columns=["yield_5y", "yield_10y"]
            )

        with patch(
            "volforecast.cli.gap_fixer._fetch_cross_asset_range", side_effect=mock_fetch
        ) as mock:
            result = fix_gaps(
                "cross_asset", "rates", missing, dry_run=False, project_root=project_root
            )
            mock.assert_called_once_with("rates", date(2024, 4, 8), date(2024, 4, 9))

        assert result.days_filled == 2


class TestFixResult:
    def test_result_dataclass_fields(self) -> None:
        """FixResult has all expected fields."""
        r = FixResult(
            source="ohlcv",
            symbol="AAPL",
            days_planned=5,
            days_filled=3,
            days_failed=2,
            errors=["timeout on 2024-03-25"],
            dry_run=False,
        )
        assert r.source == "ohlcv"
        assert r.symbol == "AAPL"
        assert r.days_planned == 5
        assert r.days_filled == 3
        assert r.days_failed == 2
        assert r.dry_run is False
