"""Unit tests for vol ingest-micro CLI and integration.

Tests processor construction, mock ChunkStore interaction,
recompute path, and output parquet schema validation.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import numpy as np
import pandas as pd

from volforecast.constants import MICRO_DAILY_COLUMNS


def _make_mock_10s_bars(n_days: int = 3) -> dict[date, pd.DataFrame]:
    """Create synthetic 10s bar data matching expected fetch output."""
    from datetime import timedelta

    rng = np.random.default_rng(42)
    result = {}
    base = date(2024, 1, 2)
    for i in range(n_days):
        d = base + timedelta(days=i)
        n_bars = 2340  # RTH at 10s
        result[d] = pd.DataFrame(
            {
                "buy_vol": rng.uniform(50, 500, size=n_bars),
                "sell_vol": rng.uniform(50, 500, size=n_bars),
                "neutral_vol": rng.uniform(0, 50, size=n_bars),
                "vwap": rng.uniform(190, 210, size=n_bars),
                "n_trades": rng.integers(10, 200, size=n_bars),
            }
        )
    return result


class TestProcessorConstruction:
    """Verify that the AggGroupBy processor chain is built correctly."""

    def test_processor_chain_has_one_element(self):
        """Chain should be [AggGroupBy] (BVC classification is client-side)."""
        from volforecast.data.micro import _build_processors

        procs = _build_processors(interval=10.0)
        assert len(procs) == 1

    def test_processor_is_agggroupby(self):
        """Single processor should be AggGroupBy with correct interval."""
        from volforecast.data.micro import _build_processors

        procs = _build_processors(interval=10.0)
        assert "AggGroupBy" in type(procs[0]).__name__


class TestIngestSymbolMicro:
    """Integration tests for ingest_symbol_micro with mocked ChunkStore."""

    @patch("volforecast.data.micro.fetch_micro_bars")
    def test_daily_output_schema(self, mock_fetch, tmp_path):
        from volforecast.data.micro import ingest_symbol_micro

        mock_fetch.return_value = _make_mock_10s_bars(3)

        daily_df, seq_df = ingest_symbol_micro(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 4),
            cache_dir=tmp_path,
            sequences_dir=tmp_path / "sequences",
        )

        # Daily output
        assert list(daily_df.columns) == MICRO_DAILY_COLUMNS
        assert len(daily_df) == 3
        # All non-NaN values within bounds
        svr = daily_df["signed_volume_ratio"].dropna()
        assert (svr >= 0).all()
        assert (svr <= 1).all()
        ofi = daily_df["order_flow_imbalance"].dropna()
        assert (ofi >= -1).all()
        assert (ofi <= 1).all()
        vpin = daily_df["vpin"].dropna()
        assert (vpin >= 0).all()
        assert (vpin <= 1).all()

    @patch("volforecast.data.micro.fetch_micro_bars")
    def test_sequences_output_schema(self, mock_fetch, tmp_path):
        from volforecast.data.micro import ingest_symbol_micro

        mock_fetch.return_value = _make_mock_10s_bars(3)

        daily_df, seq_df = ingest_symbol_micro(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 4),
            cache_dir=tmp_path,
            sequences_dir=tmp_path / "sequences",
        )

        # Sequences output
        assert "date" in seq_df.columns
        assert "bar_idx" in seq_df.columns
        assert "buy_vol" in seq_df.columns
        assert "sell_vol" in seq_df.columns
        # 3 days × 2340 bars/day
        assert len(seq_df) == 3 * 2340

    @patch("volforecast.data.micro.fetch_micro_bars")
    def test_parquets_written(self, mock_fetch, tmp_path):
        from volforecast.data.micro import ingest_symbol_micro

        mock_fetch.return_value = _make_mock_10s_bars(3)

        ingest_symbol_micro(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 4),
            cache_dir=tmp_path,
            sequences_dir=tmp_path / "sequences",
        )

        assert (tmp_path / "SPY.parquet").exists()
        assert (tmp_path / "sequences" / "SPY.parquet").exists()

    @patch("volforecast.data.micro.fetch_micro_bars")
    def test_recompute_from_sequences(self, mock_fetch, tmp_path):
        """--recompute should re-derive dailies from cached sequences."""
        from volforecast.data.micro import ingest_symbol_micro

        mock_fetch.return_value = _make_mock_10s_bars(3)

        # First run: normal ingestion
        daily1, _ = ingest_symbol_micro(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 4),
            cache_dir=tmp_path,
            sequences_dir=tmp_path / "sequences",
        )

        # Second run: recompute (should NOT call fetch)
        mock_fetch.reset_mock()
        daily2, seq2 = ingest_symbol_micro(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 4),
            cache_dir=tmp_path,
            sequences_dir=tmp_path / "sequences",
            recompute=True,
        )

        mock_fetch.assert_not_called()
        # Results should match
        pd.testing.assert_frame_equal(daily1, daily2)

    @patch("volforecast.data.micro.fetch_micro_bars")
    def test_empty_fetch_returns_empty(self, mock_fetch, tmp_path):
        from volforecast.data.micro import ingest_symbol_micro

        mock_fetch.return_value = {}

        daily_df, seq_df = ingest_symbol_micro(
            "SPY",
            date(2024, 1, 2),
            date(2024, 1, 4),
            cache_dir=tmp_path,
            sequences_dir=tmp_path / "sequences",
        )

        assert daily_df.empty
        assert seq_df.empty


class TestMidSymbolResume:
    """Test mid-symbol resume via staging."""

    def test_staging_write_and_read(self, tmp_path):
        """Staging batch write creates parquet files recoverable by _get_staged_dates."""
        from volforecast.data.micro import _get_staged_dates, _write_staging_batch

        # Monkey-patch micro_staging_dir to use tmp_path
        staging = tmp_path / ".staging" / "SPY"

        import volforecast.data.micro as micro_mod

        orig_fn = micro_mod.micro_staging_dir
        micro_mod.micro_staging_dir = lambda sym: tmp_path / ".staging" / sym

        try:
            bars = _make_mock_10s_bars(2)  # 2 days
            _write_staging_batch("SPY", bars)

            # Staging files should exist
            assert staging.exists()
            parquets = list(staging.glob("*.parquet"))
            assert len(parquets) == 1

            # _get_staged_dates should find both days
            staged = _get_staged_dates("SPY")
            assert date(2024, 1, 2) in staged
            assert date(2024, 1, 3) in staged
        finally:
            micro_mod.micro_staging_dir = orig_fn

    def test_consolidation_merges_batches(self, tmp_path):
        """Multiple staging batches consolidate into one sequences parquet."""
        import volforecast.data.micro as micro_mod
        from volforecast.data.micro import (
            _consolidate_staging,
            _write_staging_batch,
        )

        orig_staging = micro_mod.micro_staging_dir
        orig_seq = micro_mod.micro_sequences_dir
        micro_mod.micro_staging_dir = lambda sym: tmp_path / ".staging" / sym
        micro_mod.micro_sequences_dir = lambda: tmp_path / "sequences"

        try:
            # Write two separate batches
            bars1 = {date(2024, 1, 2): _make_mock_10s_bars(1)[date(2024, 1, 2)]}
            bars2 = {date(2024, 1, 3): _make_mock_10s_bars(2)[date(2024, 1, 3)]}
            _write_staging_batch("SPY", bars1)
            _write_staging_batch("SPY", bars2)

            # Consolidate
            seq_df = _consolidate_staging("SPY", sequences_dir=tmp_path / "sequences")

            assert not seq_df.empty
            assert set(seq_df["date"].unique()) == {date(2024, 1, 2), date(2024, 1, 3)}
            # Final parquet should exist
            assert (tmp_path / "sequences" / "SPY.parquet").exists()
            # Staging dir should be cleaned up
            assert not (tmp_path / ".staging" / "SPY").exists()
        finally:
            micro_mod.micro_staging_dir = orig_staging
            micro_mod.micro_sequences_dir = orig_seq

    @patch("volforecast.data.micro.fetch_micro_bars")
    def test_resume_skips_staged_dates(self, mock_fetch, tmp_path):
        """Resume should only fetch dates not already in staging."""
        import volforecast.data.micro as micro_mod
        from volforecast.data.micro import (
            _write_staging_batch,
            ingest_symbol_micro,
        )

        orig_staging = micro_mod.micro_staging_dir
        micro_mod.micro_staging_dir = lambda sym: tmp_path / ".staging" / sym

        try:
            # Pre-stage day 1 (simulate partial prior run)
            bars_day1 = {date(2024, 1, 2): _make_mock_10s_bars(1)[date(2024, 1, 2)]}
            _write_staging_batch("SPY", bars_day1)

            # Mock fetch returns day 2 and 3 bars
            bars_remaining = {
                date(2024, 1, 3): _make_mock_10s_bars(2)[date(2024, 1, 3)],
            }
            mock_fetch.return_value = bars_remaining

            daily_df, seq_df = ingest_symbol_micro(
                "SPY",
                date(2024, 1, 2),
                date(2024, 1, 3),
                cache_dir=tmp_path,
                sequences_dir=tmp_path / "sequences",
            )

            # fetch_micro_bars should only be called with the remaining date
            call_args = mock_fetch.call_args
            fetched_dates = call_args[0][1]  # second positional arg = dates
            assert date(2024, 1, 2) not in fetched_dates
        finally:
            micro_mod.micro_staging_dir = orig_staging


class TestCLIRun:
    """Test the CLI run function end-to-end with mocks."""

    @patch("volforecast.data.micro.fetch_micro_bars")
    def test_run_returns_zero_on_success(self, mock_fetch, tmp_path):
        from volforecast.cli.ingest_micro import run

        mock_fetch.return_value = _make_mock_10s_bars(3)

        exit_code = run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 4),
            symbols=["SPY"],
            force=True,
            cache_dir=tmp_path,
            sequences_dir=tmp_path / "sequences",
        )
        assert exit_code == 0

    @patch("volforecast.data.micro.fetch_micro_bars")
    def test_run_returns_one_on_failure(self, mock_fetch, tmp_path):
        from volforecast.cli.ingest_micro import run

        mock_fetch.side_effect = ConnectionError("ChunkStore unavailable")

        exit_code = run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 4),
            symbols=["SPY"],
            force=True,
            cache_dir=tmp_path,
            sequences_dir=tmp_path / "sequences",
        )
        assert exit_code == 1
