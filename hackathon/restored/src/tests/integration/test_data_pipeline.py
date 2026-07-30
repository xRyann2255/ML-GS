"""Tests for the data pipeline: Chunk Store access, tick resampling, daily RV computation.

TDD: Tests written first, implementations follow.
Uses mocked Chunk Store (pytickclient not available outside GS network).
"""

from __future__ import annotations

import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.integration

from tests.conftest import make_synthetic_ticks
from volforecast.data.chunk_store import (
    SYMBOL_UNIVERSE,
    _generate_trading_days,
    _group_contiguous_dates,
    _resolve_es_symbol,
    fetch_depth,
    fetch_quotes,
    fetch_trades,
    fetch_trades_batch,
)
from volforecast.data.resample import (
    compute_daily_rv_from_ticks,
    resample_trades_to_bars,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_ticks():
    return make_synthetic_ticks(date(2024, 1, 2))


@pytest.fixture
def synthetic_ticks_sparse():
    """Very few ticks to test edge cases."""
    return make_synthetic_ticks(date(2024, 1, 2), n_ticks=50, seed=99)


# ---------------------------------------------------------------------------
# Tests: Symbol Universe & E-mini Contract Rolling
# ---------------------------------------------------------------------------


class TestSymbolUniverse:
    def test_universe_has_34_plus_es(self):
        assert "SPY" in SYMBOL_UNIVERSE
        assert "AAPL" in SYMBOL_UNIVERSE
        assert "ES" in SYMBOL_UNIVERSE
        assert len(SYMBOL_UNIVERSE) >= 35  # 30 equities + 4 ETFs + ES

    def test_unknown_symbol_raises(self):
        with pytest.raises(ValueError, match="not in.*universe"):
            fetch_trades("FAKE_TICKER", date(2024, 1, 2), date(2024, 1, 2))


class TestESContractRolling:
    def test_jan_uses_h_contract(self):
        # Jan -> front month is March (H)
        symbol = _resolve_es_symbol(date(2024, 1, 15))
        assert symbol.startswith("ES")
        assert "H" in symbol

    def test_mar_early_still_h(self):
        # March 1 2024 is before 3rd Friday (Mar 15) -> still H (March) contract
        symbol = _resolve_es_symbol(date(2024, 3, 1))
        assert symbol == "ESH24"

    def test_mar_after_roll_uses_m(self):
        # 3rd Friday of Mar 2024 = Mar 15. Roll date = Mar 14 (Thursday).
        # On Mar 14 or after, front contract is M (June).
        symbol = _resolve_es_symbol(date(2024, 3, 14))
        assert symbol == "ESM24"

    def test_jun_early_still_m(self):
        # June 1 2024 is before 3rd Friday (Jun 21) -> still M (June) contract
        symbol = _resolve_es_symbol(date(2024, 6, 1))
        assert symbol == "ESM24"

    def test_jun_after_roll_uses_u(self):
        # 3rd Friday of Jun 2024 = Jun 21. Roll date = Jun 20.
        symbol = _resolve_es_symbol(date(2024, 6, 20))
        assert symbol == "ESU24"

    def test_sep_after_roll_uses_z(self):
        # 3rd Friday of Sep 2024 = Sep 20. Roll = Sep 19.
        symbol = _resolve_es_symbol(date(2024, 9, 19))
        assert symbol == "ESZ24"

    def test_dec_after_roll_uses_next_year_h(self):
        # 3rd Friday of Dec 2024 = Dec 20. Roll = Dec 19.
        symbol = _resolve_es_symbol(date(2024, 12, 19))
        assert symbol == "ESH25"

    def test_dec_early_still_z(self):
        # December 1 is before roll (Dec 19) -> still Z24
        symbol = _resolve_es_symbol(date(2024, 12, 1))
        assert symbol == "ESZ24"

    def test_feb_uses_current_h(self):
        # Feb 15th -> still in March (H) contract
        symbol = _resolve_es_symbol(date(2024, 2, 15))
        assert symbol == "ESH24"


class TestTradingDays:
    def test_excludes_weekends(self):
        # Jan 6 2024 is Saturday, Jan 7 is Sunday
        days = _generate_trading_days(date(2024, 1, 5), date(2024, 1, 8))
        dates_list = list(days)
        for d in dates_list:
            assert d.weekday() < 5

    def test_single_day(self):
        # Jan 2 2024 is Tuesday
        days = list(_generate_trading_days(date(2024, 1, 2), date(2024, 1, 2)))
        assert len(days) == 1
        assert days[0] == date(2024, 1, 2)

    def test_empty_for_weekend_only(self):
        # Saturday to Sunday
        days = list(_generate_trading_days(date(2024, 1, 6), date(2024, 1, 7)))
        assert len(days) == 0


# ---------------------------------------------------------------------------
# Tests: fetch_trades with mocked Chunk Store
# ---------------------------------------------------------------------------


def _mock_chunk_query(symbols, st, et, chunkdb, fields=None):
    """Return synthetic Chunk Store response dict."""
    n = 100
    base_time = st
    times = [base_time + timedelta(seconds=i * 10) for i in range(n)]
    rng = np.random.default_rng(42)

    result = {
        "Time": times,
        "TRDPRC_1": list(450.0 + rng.normal(0, 0.5, n)),
        "TRDVOL_1": list(rng.integers(1, 500, n).astype(float)),
        "BID": list(449.5 + rng.normal(0, 0.5, n)),
        "ASK": list(450.5 + rng.normal(0, 0.5, n)),
        "BIDSIZE": list(rng.integers(10, 200, n).astype(float)),
        "ASKSIZE": list(rng.integers(10, 200, n).astype(float)),
    }
    return result


class TestFetchTrades:
    @patch("volforecast.data.chunk_store.query")
    def test_returns_dataframe(self, mock_query_module):
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query)
        df = fetch_trades("SPY", date(2024, 1, 2), date(2024, 1, 2))
        assert isinstance(df, pd.DataFrame)
        assert "price" in df.columns
        assert "size" in df.columns

    @patch("volforecast.data.chunk_store.query")
    def test_timestamps_are_tz_aware(self, mock_query_module):
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query)
        df = fetch_trades("SPY", date(2024, 1, 2), date(2024, 1, 2))
        assert df.index.tz is not None

    @patch("volforecast.data.chunk_store.query")
    def test_prices_positive(self, mock_query_module):
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query)
        df = fetch_trades("SPY", date(2024, 1, 2), date(2024, 1, 2))
        assert (df["price"] > 0).all()

    @patch("volforecast.data.chunk_store.query")
    def test_multiday_concatenation(self, mock_query_module):
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query)
        # Tue Jan 2 + Wed Jan 3
        df = fetch_trades("SPY", date(2024, 1, 2), date(2024, 1, 3))
        # Should have data from 2 days
        assert len(df) > 100

    @patch("volforecast.data.chunk_store.query")
    def test_es_symbol_resolves(self, mock_query_module):
        """Fetching 'ES' should resolve to the correct contract and call chunk_query."""
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query)
        df = fetch_trades("ES", date(2024, 1, 2), date(2024, 1, 2))
        assert isinstance(df, pd.DataFrame)
        # Should have called chunk_query with the resolved contract name
        call_args = mock_query_module.chunk_query.call_args
        symbols_arg = call_args[0][0]
        assert symbols_arg[0].startswith("ES")
        assert symbols_arg[0] != "ES"  # Should be resolved (e.g., ESH24)


class TestFetchQuotes:
    @patch("volforecast.data.chunk_store.query")
    def test_returns_quote_columns(self, mock_query_module):
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query)
        df = fetch_quotes("SPY", date(2024, 1, 2), date(2024, 1, 2))
        assert isinstance(df, pd.DataFrame)
        assert "bid_price" in df.columns
        assert "ask_price" in df.columns
        assert "bid_size" in df.columns
        assert "ask_size" in df.columns


class TestFetchDepth:
    @patch("volforecast.data.chunk_store.query")
    def test_returns_depth_data(self, mock_query_module):
        """fetch_depth should return L2 book data for E-mini."""

        # Mock depth query
        def depth_mock(symbols, st, et, chunkdb, fields=None):
            n = 50
            base_time = st
            times = [base_time + timedelta(seconds=i * 10) for i in range(n)]
            rng = np.random.default_rng(42)
            result = {"Time": times}
            for lvl in range(1, 6):
                result[f"BEST_BID{lvl}"] = list(450.0 - lvl * 0.25 + rng.normal(0, 0.1, n))
                result[f"BEST_ASK{lvl}"] = list(450.0 + lvl * 0.25 + rng.normal(0, 0.1, n))
                result[f"BEST_BSIZ{lvl}"] = list(rng.integers(10, 200, n).astype(float))
                result[f"BEST_ASIZ{lvl}"] = list(rng.integers(10, 200, n).astype(float))
            return result

        mock_query_module.chunk_query = MagicMock(side_effect=depth_mock)
        df = fetch_depth(date(2024, 1, 2), date(2024, 1, 2), levels=5)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0


# ---------------------------------------------------------------------------
# Tests: Tick Resampling
# ---------------------------------------------------------------------------


class TestResampleTradesToBars:
    def test_output_columns(self, synthetic_ticks):
        bars = resample_trades_to_bars(synthetic_ticks)
        assert "price" in bars.columns
        assert "log_return" in bars.columns

    def test_frequency_default_5min(self, synthetic_ticks):
        bars = resample_trades_to_bars(synthetic_ticks)
        # 6.5h trading session / 5min = 78 bars
        assert 70 <= len(bars) <= 80

    def test_custom_frequency(self, synthetic_ticks):
        bars = resample_trades_to_bars(synthetic_ticks, freq="1min")
        # 6.5h / 1min = 390 bars
        assert 380 <= len(bars) <= 395

    def test_no_nans_in_prices(self, synthetic_ticks):
        bars = resample_trades_to_bars(synthetic_ticks)
        assert bars["price"].notna().all()

    def test_first_return_is_nan(self, synthetic_ticks):
        """First bar has no prior bar, so log_return should be NaN."""
        bars = resample_trades_to_bars(synthetic_ticks)
        assert pd.isna(bars["log_return"].iloc[0])

    def test_returns_finite(self, synthetic_ticks):
        bars = resample_trades_to_bars(synthetic_ticks)
        returns = bars["log_return"].dropna()
        assert np.all(np.isfinite(returns.values))

    def test_sparse_ticks_still_works(self, synthetic_ticks_sparse):
        """Even with very few ticks, resampling should produce bars via ffill."""
        bars = resample_trades_to_bars(synthetic_ticks_sparse)
        assert len(bars) > 0
        assert bars["price"].notna().all()

    def test_market_hours_filter(self, synthetic_ticks):
        """All bars should be within market hours."""
        bars = resample_trades_to_bars(synthetic_ticks)
        for ts in bars.index:
            t = ts.time()
            assert t >= pd.Timestamp("09:30").time()
            assert t <= pd.Timestamp("16:00").time()


# ---------------------------------------------------------------------------
# Tests: Daily RV from Ticks
# ---------------------------------------------------------------------------


class TestComputeDailyRVFromTicks:
    def test_returns_all_measures(self, synthetic_ticks):
        result = compute_daily_rv_from_ticks(synthetic_ticks)
        expected_keys = {
            "rv",
            "log_rv",
            "rq",
            "bpv",
            "rs_positive",
            "rs_negative",
            "jump_stat",
            "jump_indicator",
            "rk",
            "noise_gap",
            "n_ticks",
            "n_bars",
        }
        assert expected_keys.issubset(set(result.keys()))

    def test_rv_positive(self, synthetic_ticks):
        result = compute_daily_rv_from_ticks(synthetic_ticks)
        assert result["rv"] > 0

    def test_log_rv_finite(self, synthetic_ticks):
        result = compute_daily_rv_from_ticks(synthetic_ticks)
        assert np.isfinite(result["log_rv"])

    def test_rk_positive(self, synthetic_ticks):
        result = compute_daily_rv_from_ticks(synthetic_ticks)
        assert result["rk"] > 0

    def test_n_ticks_matches_input(self, synthetic_ticks):
        result = compute_daily_rv_from_ticks(synthetic_ticks)
        assert result["n_ticks"] == len(synthetic_ticks)

    def test_custom_frequency(self, synthetic_ticks):
        result_5m = compute_daily_rv_from_ticks(synthetic_ticks, freq="5min")
        result_1m = compute_daily_rv_from_ticks(synthetic_ticks, freq="1min")
        # Both should produce valid results
        assert result_5m["rv"] > 0
        assert result_1m["rv"] > 0
        # 1-min RV should differ from 5-min RV (more noise at higher freq)
        assert result_5m["rv"] != result_1m["rv"]

    def test_semivariances_sum_to_rv(self, synthetic_ticks):
        result = compute_daily_rv_from_ticks(synthetic_ticks)
        assert result["rs_positive"] + result["rs_negative"] == pytest.approx(
            result["rv"], rel=1e-6
        )

    def test_bpv_close_to_rv_no_jumps(self, synthetic_ticks):
        """Synthetic GBM ticks have no jumps, so BPV should approximate RV."""
        result = compute_daily_rv_from_ticks(synthetic_ticks)
        ratio = result["bpv"] / result["rv"]
        assert 0.5 < ratio < 2.0

    def test_rtq_in_output(self, synthetic_ticks):
        """compute_daily_rv_from_ticks output must include 'rtq' key."""
        result = compute_daily_rv_from_ticks(synthetic_ticks)
        assert "rtq" in result

    def test_rtq_positive(self, synthetic_ticks):
        """RTQ must be a positive float."""
        result = compute_daily_rv_from_ticks(synthetic_ticks)
        assert result["rtq"] > 0
        assert isinstance(result["rtq"], float)


# ---------------------------------------------------------------------------
# Tests: Contiguous date grouping
# ---------------------------------------------------------------------------


class TestGroupContiguousDates:
    def test_single_date(self):
        groups = _group_contiguous_dates([date(2024, 1, 2)])
        assert groups == [[date(2024, 1, 2)]]

    def test_contiguous_weekdays(self):
        dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]
        groups = _group_contiguous_dates(dates)
        assert len(groups) == 1
        assert groups[0] == dates

    def test_weekend_gap_stays_contiguous(self):
        # Fri Jan 5 -> Mon Jan 8: no weekday gap, just weekend
        dates = [date(2024, 1, 5), date(2024, 1, 8)]
        groups = _group_contiguous_dates(dates)
        assert len(groups) == 1

    def test_weekday_gap_splits(self):
        # Tue Jan 2, Thu Jan 4: Wed Jan 3 is a gap
        dates = [date(2024, 1, 2), date(2024, 1, 4)]
        groups = _group_contiguous_dates(dates)
        assert len(groups) == 2

    def test_empty_list(self):
        assert _group_contiguous_dates([]) == []


# ---------------------------------------------------------------------------
# Tests: Batch Fetch
# ---------------------------------------------------------------------------


def _mock_chunk_query_multiday(symbols, st, et, chunkdb, fields=None):
    """Return synthetic data spanning the full st->et range (multi-day)."""
    rng = np.random.default_rng(42)
    all_times: list[datetime] = []
    cur = st
    while cur < et:
        if 9 * 60 + 30 <= cur.hour * 60 + cur.minute < 16 * 60:
            all_times.append(cur)
        cur += timedelta(seconds=10)
    if not all_times:
        return {
            "Time": [],
            "TRDPRC_1": [],
            "TRDVOL_1": [],
            "BID": [],
            "ASK": [],
            "BIDSIZE": [],
            "ASKSIZE": [],
        }
    n = len(all_times)
    return {
        "Time": all_times,
        "TRDPRC_1": list(450.0 + rng.normal(0, 0.5, n)),
        "TRDVOL_1": list(rng.integers(1, 500, n).astype(float)),
        "BID": list(449.5 + rng.normal(0, 0.5, n)),
        "ASK": list(450.5 + rng.normal(0, 0.5, n)),
        "BIDSIZE": list(rng.integers(10, 200, n).astype(float)),
        "ASKSIZE": list(rng.integers(10, 200, n).astype(float)),
    }


class TestFetchTradesBatch:
    @patch("volforecast.data.chunk_store.query")
    def test_returns_dict_of_date_to_df(self, mock_query_module):
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query_multiday)
        dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]
        result = fetch_trades_batch("SPY", dates)
        assert isinstance(result, dict)
        for d in dates:
            assert d in result
            assert isinstance(result[d], pd.DataFrame)
            assert "price" in result[d].columns

    @patch("volforecast.data.chunk_store.query")
    def test_batch_one_api_call_per_day(self, mock_query_module):
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query_multiday)
        dates = [
            date(2024, 1, 2),
            date(2024, 1, 3),
            date(2024, 1, 4),
            date(2024, 1, 5),
            date(2024, 1, 8),
        ]
        fetch_trades_batch("SPY", dates, batch_size=5)
        # Each day gets its own API call (per-day queries avoid timeout on large payloads)
        assert mock_query_module.chunk_query.call_count == 5

    @patch("volforecast.data.chunk_store.query")
    def test_batch_matches_requested_dates(self, mock_query_module):
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query_multiday)
        dates = [date(2024, 1, 2), date(2024, 1, 3)]
        result = fetch_trades_batch("SPY", dates)
        assert set(result.keys()) == set(dates)

    @patch("volforecast.data.chunk_store.query")
    def test_empty_dates_returns_empty_dict(self, mock_query_module):
        result = fetch_trades_batch("SPY", [])
        assert result == {}

    @patch("volforecast.data.chunk_store.query")
    def test_non_contiguous_dates_split_into_batches(self, mock_query_module):
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query_multiday)
        # Tue Jan 2, Thu Jan 4 -- Wed missing = gap = 2 batches
        dates = [date(2024, 1, 2), date(2024, 1, 4)]
        result = fetch_trades_batch("SPY", dates, batch_size=5)
        assert date(2024, 1, 2) in result
        assert date(2024, 1, 4) in result
        assert mock_query_module.chunk_query.call_count == 2

    @patch("volforecast.data.chunk_store.query")
    def test_es_resolves_contracts(self, mock_query_module):
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query_multiday)
        dates = [date(2024, 1, 2), date(2024, 1, 3)]
        result = fetch_trades_batch("ES", dates)
        assert date(2024, 1, 2) in result

    @patch("volforecast.data.chunk_store.query")
    def test_handles_empty_response(self, mock_query_module):
        def _empty_mock(symbols, st, et, chunkdb, fields=None):
            return {
                "Time": [],
                "TRDPRC_1": [],
                "TRDVOL_1": [],
                "BID": [],
                "ASK": [],
                "BIDSIZE": [],
                "ASKSIZE": [],
            }

        mock_query_module.chunk_query = MagicMock(side_effect=_empty_mock)
        dates = [date(2024, 1, 2)]
        result = fetch_trades_batch("SPY", dates)
        assert date(2024, 1, 2) in result
        assert result[date(2024, 1, 2)].empty


# ---------------------------------------------------------------------------
# Tests: Build RV Panel (checkpoint saves)
# ---------------------------------------------------------------------------


class TestBuildRvPanelCheckpoint:
    @patch("volforecast.data.chunk_store.query")
    def test_checkpoint_writes_cache(self, mock_query_module):
        """Checkpoint saves should write cache mid-run."""
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query_multiday)
        from volforecast.data.rv_panel import build_rv_panel

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            panel = build_rv_panel(
                "SPY",
                date(2024, 1, 2),
                date(2024, 1, 4),
                cache_dir=cache_dir,
                checkpoint_interval=2,
                max_workers=1,
                mode="ticks",
            )
            assert len(panel) > 0
            assert (cache_dir / "SPY.parquet").exists()

    @patch("volforecast.data.chunk_store.query")
    def test_resume_from_cache(self, mock_query_module):
        """A second run should skip already-cached dates."""
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query_multiday)
        from volforecast.data.rv_panel import build_rv_panel

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            # First run: 2 days
            panel1 = build_rv_panel(
                "SPY",
                date(2024, 1, 2),
                date(2024, 1, 3),
                cache_dir=cache_dir,
                max_workers=1,
                mode="ticks",
            )
            assert len(panel1) > 0

            # Second run: same dates -- should not fetch again
            mock_query_module.chunk_query.reset_mock()
            panel2 = build_rv_panel(
                "SPY",
                date(2024, 1, 2),
                date(2024, 1, 3),
                cache_dir=cache_dir,
                max_workers=1,
                mode="ticks",
            )
            assert mock_query_module.chunk_query.call_count == 0
            assert len(panel2) == len(panel1)


# ---------------------------------------------------------------------------
# Tests: on_fetch callback
# ---------------------------------------------------------------------------


class TestFetchTradesBatchCallback:
    @patch("volforecast.data.chunk_store.query")
    def test_callback_fires_start_and_done(self, mock_query_module):
        """on_fetch should fire 'start' then 'done' for each chunk query."""
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query_multiday)
        dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]
        events: list[tuple] = []

        def recorder(event, chunk_dates, n_ticks, elapsed_s):
            events.append((event, list(chunk_dates), n_ticks, elapsed_s))

        fetch_trades_batch("SPY", dates, batch_size=5, on_fetch=recorder)

        # 3 contiguous dates -> 1 chunk -> 1 start + 1 done
        assert len(events) == 2
        assert events[0][0] == "start"
        assert events[0][2] == 0  # n_ticks=0 on start
        assert events[0][3] == 0.0  # elapsed=0 on start
        assert events[1][0] == "done"
        assert events[1][2] > 0  # got ticks
        assert events[1][3] > 0  # took time

    @patch("volforecast.data.chunk_store.query")
    def test_callback_gets_correct_dates(self, mock_query_module):
        """Callback chunk_dates should match the actual dates queried."""
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query_multiday)
        # Two non-contiguous dates -> two separate chunks
        dates = [date(2024, 1, 2), date(2024, 1, 4)]
        events: list[tuple] = []

        def recorder(event, chunk_dates, n_ticks, elapsed_s):
            events.append((event, list(chunk_dates), n_ticks, elapsed_s))

        fetch_trades_batch("SPY", dates, batch_size=5, on_fetch=recorder)

        # 2 chunks -> 4 events (start/done each)
        assert len(events) == 4
        start_dates = [e[1] for e in events if e[0] == "start"]
        assert [date(2024, 1, 2)] in start_dates
        assert [date(2024, 1, 4)] in start_dates

    @patch("volforecast.data.chunk_store.query")
    def test_no_callback_is_default(self, mock_query_module):
        """Without on_fetch, behavior is identical (no error)."""
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query_multiday)
        dates = [date(2024, 1, 2)]
        result = fetch_trades_batch("SPY", dates)
        assert date(2024, 1, 2) in result
        assert not result[date(2024, 1, 2)].empty

    @patch("volforecast.data.chunk_store.query")
    def test_callback_exception_does_not_crash(self, mock_query_module):
        """A failing callback should not prevent fetch from completing."""
        mock_query_module.chunk_query = MagicMock(side_effect=_mock_chunk_query_multiday)
        dates = [date(2024, 1, 2), date(2024, 1, 3)]

        def bad_callback(event, chunk_dates, n_ticks, elapsed_s):
            raise RuntimeError("callback boom")

        result = fetch_trades_batch("SPY", dates, batch_size=5, on_fetch=bad_callback)
        # Fetch should still succeed despite callback errors
        assert date(2024, 1, 2) in result
        assert not result[date(2024, 1, 2)].empty
