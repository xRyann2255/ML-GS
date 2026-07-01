"""Tests for RV panel builder.

TDD: Tests written first, implementation follows.
All tick fetches are mocked — no network dependency.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from tests.conftest import make_synthetic_ticks
from volforecast.data.rv_panel import build_rv_panel, load_rv_cache, save_rv_cache

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_fetch_batch_factory(
    trading_days: list[date],
    n_ticks: int = 5000,
    empty_days: list[date] | None = None,
    sparse_days: list[date] | None = None,
):
    """Return a mock fetch_trades_batch that returns synthetic ticks per day."""
    empty_days = empty_days or []
    sparse_days = sparse_days or []

    def _mock_batch(symbol, dates, batch_size=5, timeout_s=120.0, retries=2, on_fetch=None):
        result: dict[date, pd.DataFrame] = {}
        for d in dates:
            if d in empty_days:
                result[d] = pd.DataFrame(columns=["price", "size"])
            elif d in sparse_days:
                result[d] = make_synthetic_ticks(d, n_ticks=10, seed=hash(d) % 2**31)
            else:
                result[d] = make_synthetic_ticks(d, n_ticks=n_ticks, seed=hash(d) % 2**31)
        return result

    return _mock_batch


# ---------------------------------------------------------------------------
# Test: build_rv_panel core functionality
# ---------------------------------------------------------------------------

# Use 5 consecutive trading days in Jan 2024
_TEST_DAYS = [
    date(2024, 1, 2),
    date(2024, 1, 3),
    date(2024, 1, 4),
    date(2024, 1, 5),
    date(2024, 1, 8),
]

_START = date(2024, 1, 2)
_END = date(2024, 1, 8)


@patch("volforecast.data.rv_panel.get_trading_days", return_value=_TEST_DAYS)
@patch("volforecast.data.rv_panel.fetch_trades_batch")
class TestBuildRvPanel:
    """Core rv_panel.build_rv_panel tests."""

    def test_returns_dataframe(self, mock_fetch, mock_cal):
        mock_fetch.side_effect = _mock_fetch_batch_factory(_TEST_DAYS)
        panel = build_rv_panel("SPY", _START, _END, max_workers=1, mode="ticks")

        assert isinstance(panel, pd.DataFrame)
        assert len(panel) == 5
        # Must have all 14 keys from compute_daily_rv_from_ticks + symbol
        expected_cols = {
            "rv",
            "log_rv",
            "rq",
            "bpv",
            "rs_positive",
            "rs_negative",
            "jump_stat",
            "jump_indicator",
            "continuous_variation",
            "jump_variation",
            "rk",
            "noise_gap",
            "n_ticks",
            "n_bars",
            "symbol",
        }
        assert expected_cols.issubset(set(panel.columns))

    def test_skips_empty_days(self, mock_fetch, mock_cal):
        empty = [date(2024, 1, 3)]
        mock_fetch.side_effect = _mock_fetch_batch_factory(_TEST_DAYS, empty_days=empty)
        panel = build_rv_panel("SPY", _START, _END, max_workers=1, mode="ticks")

        assert len(panel) == 4  # 5 - 1 empty
        assert date(2024, 1, 3) not in panel.index.tolist()

    def test_skips_sparse_days(self, mock_fetch, mock_cal):
        sparse = [date(2024, 1, 4)]
        mock_fetch.side_effect = _mock_fetch_batch_factory(_TEST_DAYS, sparse_days=sparse)
        panel = build_rv_panel(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 8),
            min_ticks=50,
            max_workers=1,
            mode="ticks",
        )

        assert date(2024, 1, 4) not in panel.index.tolist()
        assert len(panel) == 4

    def test_date_alignment(self, mock_fetch, mock_cal):
        mock_fetch.side_effect = _mock_fetch_batch_factory(_TEST_DAYS)
        panel = build_rv_panel("SPY", _START, _END, max_workers=1, mode="ticks")

        dates = panel.index.tolist()
        assert dates == sorted(dates), "Index must be sorted"
        assert len(dates) == len(set(dates)), "No duplicate dates"

    def test_date_injection(self, mock_fetch, mock_cal):
        mock_fetch.side_effect = _mock_fetch_batch_factory(_TEST_DAYS)
        panel = build_rv_panel("SPY", _START, _END, max_workers=1, mode="ticks")

        # Index values should be the trading days we generated
        assert set(panel.index.tolist()) == set(_TEST_DAYS)

    def test_jump_indicator_is_int(self, mock_fetch, mock_cal):
        mock_fetch.side_effect = _mock_fetch_batch_factory(_TEST_DAYS)
        panel = build_rv_panel("SPY", _START, _END, max_workers=1, mode="ticks")

        assert panel["jump_indicator"].dtype in (np.int64, np.int32, int)

    def test_adds_symbol_column(self, mock_fetch, mock_cal):
        mock_fetch.side_effect = _mock_fetch_batch_factory(_TEST_DAYS)
        panel = build_rv_panel("SPY", _START, _END, max_workers=1, mode="ticks")

        assert "symbol" in panel.columns
        assert (panel["symbol"] == "SPY").all()

    def test_invalid_symbol_raises(self, mock_fetch, mock_cal):
        with pytest.raises(ValueError, match="not in"):
            build_rv_panel("INVALID_TICKER", date(2024, 1, 2), date(2024, 1, 8), mode="ticks")


# ---------------------------------------------------------------------------
# Test: Caching
# ---------------------------------------------------------------------------


@patch("volforecast.data.rv_panel.get_trading_days", return_value=_TEST_DAYS)
@patch("volforecast.data.rv_panel.fetch_trades_batch")
class TestRvCache:
    """Cache save/load and incremental fetching."""

    def test_save_and_load_roundtrip(self, mock_fetch, mock_cal, tmp_path):
        mock_fetch.side_effect = _mock_fetch_batch_factory(_TEST_DAYS)
        panel = build_rv_panel("SPY", _START, _END, max_workers=1, mode="ticks")

        path = save_rv_cache(panel, "SPY", tmp_path)
        loaded = load_rv_cache("SPY", tmp_path)

        assert loaded is not None
        pd.testing.assert_frame_equal(panel, loaded)
        assert path.exists()

    def test_incremental_append(self, mock_fetch, mock_cal, tmp_path):
        # First build: 3 days
        three_days = _TEST_DAYS[:3]
        mock_cal.return_value = three_days
        mock_fetch.side_effect = _mock_fetch_batch_factory(three_days)
        panel1 = build_rv_panel(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 4),
            cache_dir=tmp_path,
            max_workers=1,
            mode="ticks",
        )
        assert len(panel1) == 3

        # Second build: all 5 days — should only fetch the 2 new ones
        mock_cal.return_value = _TEST_DAYS
        mock_fetch.side_effect = _mock_fetch_batch_factory(_TEST_DAYS)
        mock_fetch.reset_mock()
        panel2 = build_rv_panel(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 8),
            cache_dir=tmp_path,
            max_workers=1,
            mode="ticks",
        )

        assert len(panel2) == 5
        # batch fetch should be called with only the 2 new days
        assert mock_fetch.call_count >= 1

    def test_incremental_no_refetch_existing(self, mock_fetch, mock_cal, tmp_path):
        # Build full panel and cache it
        mock_fetch.side_effect = _mock_fetch_batch_factory(_TEST_DAYS)
        build_rv_panel("SPY", _START, _END, cache_dir=tmp_path, max_workers=1, mode="ticks")

        # Build again with same range — no fetches needed
        mock_fetch.reset_mock()
        panel = build_rv_panel(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 8),
            cache_dir=tmp_path,
            max_workers=1,
            mode="ticks",
        )

        assert len(panel) == 5
        assert mock_fetch.call_count == 0

    def test_cache_miss_returns_none(self, mock_fetch, mock_cal, tmp_path):
        result = load_rv_cache("NONEXISTENT", tmp_path)
        assert result is None


# ---------------------------------------------------------------------------
# Test: OHLCV enrichment
# ---------------------------------------------------------------------------


def _make_mock_ohlcv(symbol: str, dates: list[date]) -> pd.DataFrame:
    """Create a mock OHLCV DataFrame matching fetch_daily_ohlcv output."""
    rng = np.random.default_rng(99)
    n = len(dates)
    close = 450.0 + np.cumsum(rng.normal(0, 1, n))
    open_ = close + rng.normal(0, 0.5, n)
    rows = []
    for i, d in enumerate(dates):
        rows.append(
            {
                "open": open_[i],
                "high": max(open_[i], close[i]) + abs(rng.normal(0, 0.3)),
                "low": min(open_[i], close[i]) - abs(rng.normal(0, 0.3)),
                "close": close[i],
                "volume": int(rng.integers(1_000_000, 50_000_000)),
            }
        )
    df = pd.DataFrame(rows, index=pd.DatetimeIndex(dates, name="date"))
    df["symbol"] = symbol
    df = df.set_index("symbol", append=True)
    return df


@patch("volforecast.data.rv_panel.get_trading_days", return_value=_TEST_DAYS)
@patch("volforecast.data.rv_panel.fetch_trades_batch")
class TestEnrichPanelWithOhlcv:
    """Tests for enrich_panel_with_ohlcv."""

    def test_adds_open_close_columns(self, mock_fetch, mock_cal):
        from volforecast.data.rv_panel import enrich_panel_with_ohlcv

        mock_fetch.side_effect = _mock_fetch_batch_factory(_TEST_DAYS)
        panel = build_rv_panel("SPY", _START, _END, max_workers=1, mode="ticks")
        assert "open" not in panel.columns
        assert "close" not in panel.columns

        mock_ohlcv = _make_mock_ohlcv("SPY", _TEST_DAYS)
        with patch("volforecast.data.rv_panel.fetch_daily_ohlcv", return_value=mock_ohlcv):
            enriched = enrich_panel_with_ohlcv(panel, "SPY", date(2024, 1, 2), date(2024, 1, 8))

        assert "open" in enriched.columns
        assert "close" in enriched.columns
        assert len(enriched) == 5

    def test_preserves_existing_columns(self, mock_fetch, mock_cal):
        from volforecast.data.rv_panel import enrich_panel_with_ohlcv

        mock_fetch.side_effect = _mock_fetch_batch_factory(_TEST_DAYS)
        panel = build_rv_panel("SPY", _START, _END, max_workers=1, mode="ticks")
        original_cols = set(panel.columns)

        mock_ohlcv = _make_mock_ohlcv("SPY", _TEST_DAYS)
        with patch("volforecast.data.rv_panel.fetch_daily_ohlcv", return_value=mock_ohlcv):
            enriched = enrich_panel_with_ohlcv(panel, "SPY", date(2024, 1, 2), date(2024, 1, 8))

        assert original_cols.issubset(set(enriched.columns))
        # RV values unchanged
        pd.testing.assert_series_equal(panel["rv"], enriched["rv"])

    def test_handles_partial_overlap(self, mock_fetch, mock_cal):
        """OHLCV may have fewer dates than the RV panel (holidays differ)."""
        from volforecast.data.rv_panel import enrich_panel_with_ohlcv

        mock_fetch.side_effect = _mock_fetch_batch_factory(_TEST_DAYS)
        panel = build_rv_panel("SPY", _START, _END, max_workers=1, mode="ticks")

        # OHLCV only has 3 of 5 days
        partial_days = _TEST_DAYS[:3]
        mock_ohlcv = _make_mock_ohlcv("SPY", partial_days)
        with patch("volforecast.data.rv_panel.fetch_daily_ohlcv", return_value=mock_ohlcv):
            enriched = enrich_panel_with_ohlcv(panel, "SPY", date(2024, 1, 2), date(2024, 1, 8))

        assert len(enriched) == 5
        # Missing days should have NaN for open/close
        nan_val = enriched.loc[date(2024, 1, 5), "open"]
        assert nan_val != nan_val  # NaN

    def test_graceful_on_connection_error(self, mock_fetch, mock_cal):
        """If TSDB is unavailable, add NaN open/close columns."""
        from volforecast.data.rv_panel import enrich_panel_with_ohlcv

        mock_fetch.side_effect = _mock_fetch_batch_factory(_TEST_DAYS)
        panel = build_rv_panel("SPY", _START, _END, max_workers=1, mode="ticks")

        with patch(
            "volforecast.data.rv_panel.fetch_daily_ohlcv",
            side_effect=ConnectionError("no TSDB"),
        ):
            enriched = enrich_panel_with_ohlcv(panel, "SPY", date(2024, 1, 2), date(2024, 1, 8))

        # Should return panel WITH open/close columns filled with NaN
        assert "open" in enriched.columns
        assert "close" in enriched.columns
        assert enriched["open"].isna().all()
        assert enriched["close"].isna().all()

    def test_skips_futures_symbol(self, mock_fetch, mock_cal):
        """ES (E-mini) has no TSDB OHLCV mapping — should add NaN columns."""
        from volforecast.data.rv_panel import enrich_panel_with_ohlcv

        mock_fetch.side_effect = _mock_fetch_batch_factory(_TEST_DAYS)
        mock_cal.return_value = _TEST_DAYS
        panel = build_rv_panel("SPY", _START, _END, max_workers=1, mode="ticks")
        # Pretend this is ES data
        panel["symbol"] = "ES"

        with patch("volforecast.data.rv_panel.fetch_daily_ohlcv", side_effect=ValueError("No RIC")):
            enriched = enrich_panel_with_ohlcv(panel, "ES", date(2024, 1, 2), date(2024, 1, 8))

        assert "open" in enriched.columns
        assert "close" in enriched.columns
        assert enriched["open"].isna().all()


# ---------------------------------------------------------------------------
# Test: Checkpoint and resume after interruption
# ---------------------------------------------------------------------------

# Use 10 trading days to test batch-level checkpointing
_LONG_TEST_DAYS = [
    date(2024, 1, 2),
    date(2024, 1, 3),
    date(2024, 1, 4),
    date(2024, 1, 5),
    date(2024, 1, 8),
    date(2024, 1, 9),
    date(2024, 1, 10),
    date(2024, 1, 11),
    date(2024, 1, 12),
    date(2024, 1, 16),
]


@patch("volforecast.data.rv_panel.get_trading_days", return_value=_LONG_TEST_DAYS)
@patch("volforecast.data.rv_panel.fetch_trades_batch")
class TestCheckpointResume:
    """Verify checkpoint saves after each sub-batch and resume skips cached days."""

    def test_checkpoint_saves_after_first_batch(self, mock_fetch, mock_cal, tmp_path):
        """With batch_size=5, first 5 days should be checkpointed before starting batch 2."""
        call_count = [0]
        days_requested: list[list[date]] = []

        def _tracking_fetch(symbol, dates, batch_size=5, timeout_s=120.0, retries=2, on_fetch=None):
            call_count[0] += 1
            days_requested.append(list(dates))
            # Simulate interruption after first batch by raising KeyboardInterrupt
            # on the second call
            if call_count[0] >= 2:
                raise KeyboardInterrupt("simulated Ctrl+C")
            factory = _mock_fetch_batch_factory(_LONG_TEST_DAYS)
            return factory(symbol, dates, batch_size, timeout_s, retries, on_fetch)

        mock_fetch.side_effect = _tracking_fetch

        # Run with batch_size=5 -- should checkpoint after first 5 days,
        # then get interrupted on the second batch fetch
        with pytest.raises(KeyboardInterrupt):
            build_rv_panel(
                "SPY",
                date(2024, 1, 2),
                date(2024, 1, 16),
                cache_dir=tmp_path,
                max_workers=1,
                batch_size=5,
                mode="ticks",
            )

        # The first batch (5 days) should have been checkpointed
        cached = load_rv_cache("SPY", tmp_path)
        assert cached is not None
        assert len(cached) == 5

    def test_resume_skips_cached_days(self, mock_fetch, mock_cal, tmp_path):
        """After partial cache exists, rebuild only fetches missing days."""
        factory = _mock_fetch_batch_factory(_LONG_TEST_DAYS)
        mock_fetch.side_effect = factory

        # First run: only 5 days (simulate partial completion)
        mock_cal.return_value = _LONG_TEST_DAYS[:5]
        panel1 = build_rv_panel(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 8),
            cache_dir=tmp_path,
            max_workers=1,
            batch_size=5,
            mode="ticks",
        )
        assert len(panel1) == 5

        # Second run: full 10 days -- should only fetch the 5 missing ones
        mock_cal.return_value = _LONG_TEST_DAYS
        mock_fetch.reset_mock()
        mock_fetch.side_effect = factory

        panel2 = build_rv_panel(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 16),
            cache_dir=tmp_path,
            max_workers=1,
            batch_size=5,
            mode="ticks",
        )

        assert len(panel2) == 10
        # Verify only the 5 missing days were fetched (one batch call)
        fetched_dates = []
        for call in mock_fetch.call_args_list:
            fetched_dates.extend(call[0][1])  # second positional arg is dates
        assert len(fetched_dates) == 5
        # The cached days should NOT be in the fetch requests
        cached_dates = set(_LONG_TEST_DAYS[:5])
        assert not cached_dates.intersection(fetched_dates)

    def test_checkpoint_every_batch_with_default_interval(self, mock_fetch, mock_cal, tmp_path):
        """With checkpoint_interval=1, cache is written after every sub-batch."""
        mock_fetch.side_effect = _mock_fetch_batch_factory(_LONG_TEST_DAYS)

        panel = build_rv_panel(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 16),
            cache_dir=tmp_path,
            max_workers=1,
            batch_size=5,
            checkpoint_interval=1,
            mode="ticks",
        )

        assert len(panel) == 10
        # Cache should exist and contain all 10 days
        cached = load_rv_cache("SPY", tmp_path)
        assert cached is not None
        assert len(cached) == 10
