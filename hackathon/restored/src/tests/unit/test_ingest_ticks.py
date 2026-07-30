"""Tests for standalone vol ingest-ticks CLI.

TDD: Tests written first, implementation follows.
Mocks all external API calls (ChunkStore, TSDB).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rv_panel(
    start: str = "2024-01-02",
    end: str = "2024-01-31",
) -> pd.DataFrame:
    """Create a synthetic RV panel matching the ticks output schema."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(42)
    n = len(idx)
    rv = rng.uniform(0.0001, 0.005, n)
    return pd.DataFrame(
        {
            "rv": rv,
            "log_rv": np.log(rv),
            "rq": rng.uniform(1e-8, 1e-6, n),
            "rtq": rng.uniform(1e-8, 1e-6, n),
            "bpv": rv * rng.uniform(0.8, 1.0, n),
            "rs_positive": rv * 0.5,
            "rs_negative": rv * 0.5,
            "jump_stat": rng.normal(0, 1, n),
            "jump_indicator": rng.choice([0, 1], n, p=[0.9, 0.1]),
            "continuous_variation": rv * 0.95,
            "jump_variation": rv * 0.05,
            "j_positive": rv * 0.03,
            "j_negative": rv * 0.02,
            "realized_skewness": rng.normal(0, 0.5, n),
            "realized_kurtosis": rng.uniform(3, 10, n),
            "rk": rv * rng.uniform(0.9, 1.1, n),
            "noise_gap": rng.uniform(-0.1, 0.1, n),
            "n_ticks": rng.integers(5000, 50000, n),
            "n_bars": np.full(n, 78),
            "open": rng.uniform(100, 200, n),
            "close": rng.uniform(100, 200, n),
        },
        index=idx,
    )


# ---------------------------------------------------------------------------
# Tests: data layer (data/ticks.py)
# ---------------------------------------------------------------------------


class TestTicksDataLayer:
    """Test the public API of volforecast.data.ticks."""

    def test_save_and_load_cache(self, tmp_path: Path):
        """save_ticks_cache + load_ticks_cache roundtrip."""
        from volforecast.data.ticks import load_ticks_cache, save_ticks_cache

        df = _make_rv_panel()
        save_ticks_cache("SPY", df, cache_dir=tmp_path)
        loaded = load_ticks_cache("SPY", cache_dir=tmp_path)

        assert loaded is not None
        assert len(loaded) == len(df)
        assert set(loaded.columns) == set(df.columns)

    def test_load_cache_returns_none_if_missing(self, tmp_path: Path):
        """load_ticks_cache returns None when no file exists."""
        from volforecast.data.ticks import load_ticks_cache

        assert load_ticks_cache("AAPL", cache_dir=tmp_path) is None

    def test_cache_covers_range(self, tmp_path: Path):
        """cache_covers_range returns True when data spans requested dates."""
        from volforecast.data.ticks import cache_covers_range, save_ticks_cache

        df = _make_rv_panel("2024-01-02", "2024-01-31")
        save_ticks_cache("SPY", df, cache_dir=tmp_path)

        assert cache_covers_range("SPY", date(2024, 1, 2), date(2024, 1, 31), cache_dir=tmp_path)
        # Outside range should return False
        assert not cache_covers_range(
            "SPY", date(2024, 1, 2), date(2024, 2, 28), cache_dir=tmp_path
        )

    def test_output_has_21_columns(self, tmp_path: Path):
        """Output parquet must have exactly 21 columns per manifest contract."""
        from volforecast.data.ticks import save_ticks_cache

        df = _make_rv_panel()
        save_ticks_cache("SPY", df, cache_dir=tmp_path)

        loaded = pd.read_parquet(tmp_path / "SPY.parquet")
        assert len(loaded.columns) == 21


# ---------------------------------------------------------------------------
# Tests: CLI (cli/ingest_ticks.py)
# ---------------------------------------------------------------------------


class TestIngestTicksCLI:
    """Test the standalone CLI entry point."""

    @pytest.mark.slow
    @patch("volforecast.cli.ingest_ticks.cache_covers_range", return_value=False)
    @patch("volforecast.cli.ingest_ticks.ingest_symbol")
    def test_default_symbols_is_full_universe(self, mock_ingest, mock_cache):
        """When --symbols is omitted, processes full SYMBOL_UNIVERSE."""
        from volforecast.cli.ingest_ticks import run
        from volforecast.constants import SYMBOL_UNIVERSE

        mock_ingest.return_value = _make_rv_panel()

        run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 31),
            symbols=None,
            force=False,
            recompute=False,
        )

        called_symbols = {call.args[0] for call in mock_ingest.call_args_list}
        assert called_symbols == SYMBOL_UNIVERSE

    @patch("volforecast.cli.ingest_ticks.cache_covers_range", return_value=False)
    @patch("volforecast.cli.ingest_ticks.ingest_symbol")
    def test_symbols_flag_filters(self, mock_ingest, mock_cache):
        """--symbols limits processing to requested symbols only."""
        from volforecast.cli.ingest_ticks import run

        mock_ingest.return_value = _make_rv_panel()

        run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 31),
            symbols=["SPY", "AAPL"],
            force=False,
            recompute=False,
        )

        called_symbols = {call.args[0] for call in mock_ingest.call_args_list}
        assert called_symbols == {"SPY", "AAPL"}

    @patch("volforecast.cli.ingest_ticks.cache_covers_range", return_value=True)
    @patch("volforecast.cli.ingest_ticks.ingest_symbol")
    def test_skip_cached_unless_force(self, mock_ingest, mock_cache):
        """Cached symbols are skipped when force=False."""
        from volforecast.cli.ingest_ticks import run

        run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 31),
            symbols=["SPY"],
            force=False,
            recompute=False,
        )

        mock_ingest.assert_not_called()

    @patch("volforecast.cli.ingest_ticks.cache_covers_range", return_value=True)
    @patch("volforecast.cli.ingest_ticks.ingest_symbol")
    def test_force_refetches_cached(self, mock_ingest, mock_cache):
        """--force re-fetches even when cache covers range."""
        from volforecast.cli.ingest_ticks import run

        mock_ingest.return_value = _make_rv_panel()

        run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 31),
            symbols=["SPY"],
            force=True,
            recompute=False,
        )

        mock_ingest.assert_called_once()

    @patch("volforecast.cli.ingest_ticks.ingest_symbol")
    def test_partial_failure_continues(self, mock_ingest):
        """One symbol failure doesn't abort processing of others."""
        from volforecast.cli.ingest_ticks import run

        def side_effect(symbol, *args, **kwargs):
            if symbol == "AAPL":
                raise ConnectionError("ChunkStore down")
            return _make_rv_panel()

        mock_ingest.side_effect = side_effect

        result = run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 31),
            symbols=["AAPL", "SPY"],
            force=True,
            recompute=False,
        )

        # Should return 1 (partial failure) but SPY was still processed
        assert result == 1
