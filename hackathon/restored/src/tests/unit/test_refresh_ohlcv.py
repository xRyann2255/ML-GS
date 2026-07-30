"""Tests for vol refresh-ohlcv command.

Tests corruption detection logic and the refresh workflow using
synthetic panels (no TSDB calls).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from volforecast.cli.refresh_ohlcv import (
    _discover_symbols,
    _needs_refresh,
    run,
)


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Create a temporary cache directory."""
    cache = tmp_path / "rv"
    cache.mkdir()
    return cache


@pytest.fixture
def clean_panel() -> pd.DataFrame:
    """Panel with correctly adjusted open/close (no split artifacts)."""
    rng = np.random.default_rng(42)
    n = 100
    dates = pd.bdate_range("2020-01-02", periods=n).date

    rv = np.exp(-9.0 + 0.5 * rng.standard_normal(n))
    # Simulate a stock with gradual price changes (no splits)
    close = 100 * np.exp(np.cumsum(0.001 * rng.standard_normal(n)))
    # Open is close_{t-1} ± small overnight gap
    open_prices = np.roll(close, 1) * np.exp(0.002 * rng.standard_normal(n))
    open_prices[0] = close[0] * 0.999

    return pd.DataFrame(
        {"rv": rv, "open": open_prices, "close": close, "symbol": "CLEAN"},
        index=dates,
    )


@pytest.fixture
def corrupt_panel() -> pd.DataFrame:
    """Panel mimicking split-corrupted data (unadjusted open vs adjusted close)."""
    rng = np.random.default_rng(42)
    n = 100
    dates = pd.bdate_range("2020-01-02", periods=n).date

    rv = np.exp(-9.0 + 0.5 * rng.standard_normal(n))
    # Adjusted close (smooth)
    close = 100 * np.exp(np.cumsum(0.001 * rng.standard_normal(n)))
    # Unadjusted open: 10x higher for first 50 days (simulates a 10:1 split at day 50)
    open_prices = np.roll(close, 1) * np.exp(0.002 * rng.standard_normal(n))
    open_prices[0] = close[0] * 0.999
    open_prices[:50] *= 10  # Pre-split: unadjusted open is 10x the adjusted close

    return pd.DataFrame(
        {"rv": rv, "open": open_prices, "close": close, "symbol": "CORRUPT"},
        index=dates,
    )


class TestNeedsRefresh:
    def test_clean_panel_does_not_need_refresh(self, clean_panel):
        needs_fix, n_corrupt = _needs_refresh(clean_panel)
        assert not needs_fix
        assert n_corrupt == 0

    def test_corrupt_panel_needs_refresh(self, corrupt_panel):
        needs_fix, n_corrupt = _needs_refresh(corrupt_panel)
        assert needs_fix
        assert n_corrupt > 0
        # Should detect ~50 corrupt rows (the pre-split dates)
        assert n_corrupt >= 40

    def test_missing_open_column_needs_refresh(self, clean_panel):
        panel = clean_panel.drop(columns=["open"])
        needs_fix, n_corrupt = _needs_refresh(panel)
        assert needs_fix
        assert n_corrupt == 0

    def test_missing_close_column_needs_refresh(self, clean_panel):
        panel = clean_panel.drop(columns=["close"])
        needs_fix, n_corrupt = _needs_refresh(panel)
        assert needs_fix
        assert n_corrupt == 0

    def test_all_nan_open_needs_refresh(self, clean_panel):
        panel = clean_panel.copy()
        panel["open"] = np.nan
        needs_fix, n_corrupt = _needs_refresh(panel)
        assert needs_fix
        assert n_corrupt == 0

    def test_all_nan_close_needs_refresh(self, clean_panel):
        panel = clean_panel.copy()
        panel["close"] = np.nan
        needs_fix, n_corrupt = _needs_refresh(panel)
        assert needs_fix
        assert n_corrupt == 0


class TestDiscoverSymbols:
    def test_finds_parquet_files(self, cache_dir, clean_panel):
        clean_panel.to_parquet(cache_dir / "SPY.parquet")
        clean_panel.to_parquet(cache_dir / "AAPL.parquet")
        symbols = _discover_symbols(cache_dir)
        assert symbols == ["AAPL", "SPY"]

    def test_ignores_empty_files(self, cache_dir):
        (cache_dir / "EMPTY.parquet").write_bytes(b"")
        symbols = _discover_symbols(cache_dir)
        assert symbols == []

    def test_empty_dir(self, cache_dir):
        symbols = _discover_symbols(cache_dir)
        assert symbols == []


class TestRunDryRun:
    def test_dry_run_returns_empty_dict(self, monkeypatch, cache_dir, corrupt_panel, clean_panel):
        """Dry run scans for corruption but fetches nothing."""
        corrupt_panel.to_parquet(cache_dir / "NVDA.parquet")
        clean_panel.to_parquet(cache_dir / "SPY.parquet")

        monkeypatch.setattr("volforecast.utils.paths.rv_cache_dir", lambda: cache_dir)

        result = run(dry_run=True)
        assert result == {}

    def test_dry_run_with_symbols_filter(self, monkeypatch, cache_dir, corrupt_panel):
        """Dry run respects --symbols filter."""
        corrupt_panel.to_parquet(cache_dir / "NVDA.parquet")
        corrupt_panel.to_parquet(cache_dir / "AAPL.parquet")

        import volforecast.utils.paths

        monkeypatch.setattr(volforecast.utils.paths, "rv_cache_dir", lambda: cache_dir)

        result = run(symbols=["NVDA"], dry_run=True)
        assert result == {}


class TestRunRefresh:
    def test_skips_clean_symbols(self, monkeypatch, cache_dir, clean_panel):
        """Clean symbols are skipped without TSDB calls."""
        clean_panel.to_parquet(cache_dir / "SPY.parquet")

        import volforecast.utils.paths

        monkeypatch.setattr(volforecast.utils.paths, "rv_cache_dir", lambda: cache_dir)

        result = run(symbols=["SPY"])
        assert "skipped" in result.get("SPY", "")

    def test_force_processes_clean_symbol(self, monkeypatch, cache_dir, clean_panel):
        """--force processes even clean symbols."""
        clean_panel.to_parquet(cache_dir / "SPY.parquet")

        import volforecast.utils.paths

        monkeypatch.setattr(volforecast.utils.paths, "rv_cache_dir", lambda: cache_dir)
        monkeypatch.setattr("volforecast.data.tsdb._ensure_session", lambda: None)

        # Mock the TSDB fetch to return synthetic adjusted data
        rng = np.random.default_rng(99)
        n = len(clean_panel)
        dates = pd.DatetimeIndex(clean_panel.index)
        new_open = pd.Series(
            100 * np.exp(np.cumsum(0.001 * rng.standard_normal(n))),
            index=dates,
        )
        new_close = pd.Series(
            100 * np.exp(np.cumsum(0.001 * rng.standard_normal(n))),
            index=dates,
        )

        monkeypatch.setattr(
            "volforecast.cli.refresh_ohlcv._fetch_adjusted_open_close",
            lambda sym, start, end: (new_open, new_close),
        )

        result = run(symbols=["SPY"], force=True)
        assert "refreshed" in result.get("SPY", "")

        # Verify the parquet was actually updated
        updated = pd.read_parquet(cache_dir / "SPY.parquet")
        # Close should now match our mock data (not the original)
        assert not np.allclose(updated["close"].values, clean_panel["close"].values, rtol=1e-5)

    def test_refreshes_corrupt_symbol(self, monkeypatch, cache_dir, corrupt_panel):
        """Corrupt symbols are refreshed and saved."""
        corrupt_panel.to_parquet(cache_dir / "NVDA.parquet")

        import volforecast.utils.paths

        monkeypatch.setattr(volforecast.utils.paths, "rv_cache_dir", lambda: cache_dir)
        monkeypatch.setattr("volforecast.data.tsdb._ensure_session", lambda: None)

        # Mock fetch to return properly adjusted prices
        rng = np.random.default_rng(99)
        n = len(corrupt_panel)
        dates = pd.DatetimeIndex(corrupt_panel.index)
        # Clean prices: no split artifacts
        new_close = pd.Series(
            100 * np.exp(np.cumsum(0.001 * rng.standard_normal(n))),
            index=dates,
        )
        new_open = pd.Series(
            np.roll(new_close.values, 1) * np.exp(0.002 * rng.standard_normal(n)),
            index=dates,
        )

        monkeypatch.setattr(
            "volforecast.cli.refresh_ohlcv._fetch_adjusted_open_close",
            lambda sym, start, end: (new_open, new_close),
        )

        result = run(symbols=["NVDA"])
        assert "refreshed" in result.get("NVDA", "")

        # Verify the parquet was updated and is now clean
        updated = pd.read_parquet(cache_dir / "NVDA.parquet")
        needs_fix, n_corrupt = _needs_refresh(updated)
        assert not needs_fix
        assert n_corrupt == 0

        # Verify RV column was NOT modified
        assert np.allclose(updated["rv"].values, corrupt_panel["rv"].values)
