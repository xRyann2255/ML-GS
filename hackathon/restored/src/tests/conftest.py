"""Shared pytest fixtures for volforecast tests.

Provides reusable synthetic data generators for pipeline, feature, and evaluation tests.
Uses deterministic seeds for reproducibility.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def _skip_pyslang_session():
    """Prevent tests from starting a real pyslang subprocess."""
    import volforecast.data.chunk_store as _cs

    with patch.object(_cs, "_session_started", True):
        yield


@pytest.fixture(autouse=True)
def _mock_processor_if_missing():
    """Ensure _processor is not None so fetch_bars tests can exercise logic.

    On machines without pytickclient (e.g., Linux CI), the module-level
    `from pytickclient import processor` sets _processor = None.
    Tests that patch `query` also need _processor to be non-None.
    """
    from unittest.mock import MagicMock

    import volforecast.data.chunk_store as _cs

    with patch.object(_cs, "_processor", _cs._processor or MagicMock()):
        yield


@pytest.fixture
def synthetic_log_prices() -> np.ndarray:
    """Simulate GBM log-prices for one trading day (23400 ticks, no jumps).

    Returns n_ticks+1 log-prices (so n_ticks log-returns).
    True daily annualized vol = 0.20.
    """
    n_ticks = 23400
    sigma_annual = 0.20
    dt_fraction = 1.0 / 252.0
    rng = np.random.default_rng(42)
    dt_per_tick = dt_fraction / n_ticks
    sigma_per_tick = sigma_annual * np.sqrt(dt_per_tick)
    increments = sigma_per_tick * rng.standard_normal(n_ticks)
    log_prices = np.zeros(n_ticks + 1)
    log_prices[0] = np.log(100.0)
    log_prices[1:] = log_prices[0] + np.cumsum(increments)
    return log_prices


@pytest.fixture
def synthetic_daily_rv_series() -> pd.Series:
    """Generate synthetic daily log-RV series (500 business days).

    Mimics realistic HAR dynamics with daily/weekly/monthly persistence.
    """
    rng = np.random.default_rng(123)
    n_days = 500
    dates = pd.bdate_range(start="2022-01-03", periods=n_days)

    # AR(1) with mean-reversion in log-RV space
    log_rv = np.zeros(n_days)
    log_rv[0] = np.log(0.02)  # ~20% annualized vol
    for i in range(1, n_days):
        log_rv[i] = -4.0 + 0.4 * log_rv[i - 1] + 0.3 * rng.standard_normal()

    return pd.Series(log_rv, index=dates, name="log_rv")


@pytest.fixture
def synthetic_predictions_actuals() -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic prediction/actual pairs for evaluation tests.

    Returns (predictions, actuals) in RV space (not log).
    """
    rng = np.random.default_rng(456)
    n = 200
    actuals = np.exp(-4.0 + 0.3 * rng.standard_normal(n))  # realistic RV values
    noise = 0.2 * rng.standard_normal(n)
    predictions = actuals * np.exp(noise)  # predictions with multiplicative noise
    return predictions, actuals


def make_synthetic_ticks(
    trade_date: date = date(2024, 1, 2),
    n_ticks: int = 5000,
    price_start: float = 450.0,
    sigma: float = 0.0005,
    seed: int = 42,
) -> pd.DataFrame:
    """Create synthetic tick DataFrame matching fetch_trades output format.

    Parameters
    ----------
    trade_date : date
        Trading day to simulate.
    n_ticks : int
        Number of ticks to generate.
    price_start : float
        Starting price level.
    sigma : float
        Per-tick return volatility.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    pd.DataFrame
        Tick DataFrame with DatetimeIndex (tz=America/New_York),
        columns: price, size.
    """
    rng = np.random.default_rng(seed)

    market_open = datetime(trade_date.year, trade_date.month, trade_date.day, 9, 30, 0)
    market_close = datetime(trade_date.year, trade_date.month, trade_date.day, 16, 0, 0)
    total_seconds = (market_close - market_open).total_seconds()

    offsets = np.sort(rng.uniform(0, total_seconds, n_ticks))
    timestamps = pd.to_datetime(
        [market_open + timedelta(seconds=float(s)) for s in offsets]
    ).tz_localize("America/New_York")

    log_returns = rng.normal(0, sigma, n_ticks)
    log_prices = np.log(price_start) + np.cumsum(log_returns)
    prices = np.exp(log_prices)
    sizes = rng.integers(1, 500, n_ticks)

    return pd.DataFrame({"price": prices, "size": sizes}, index=timestamps)


@pytest.fixture
def synthetic_tick_df() -> pd.DataFrame:
    """Create synthetic tick DataFrame with timestamps, prices, sizes."""
    return make_synthetic_ticks()


@pytest.fixture
def synthetic_ohlcv_df() -> pd.DataFrame:
    """Generate synthetic OHLCV daily data (252 trading days)."""
    rng = np.random.default_rng(789)
    n_days = 252
    dates = pd.bdate_range(start="2023-01-03", periods=n_days)

    close = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, n_days)))
    high = close * (1 + rng.uniform(0, 0.02, n_days))
    low = close * (1 - rng.uniform(0, 0.02, n_days))
    open_ = close * (1 + rng.normal(0, 0.005, n_days))
    volume = rng.integers(1_000_000, 50_000_000, n_days)

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


# ---------------------------------------------------------------------------
# GBM fixtures used by test_rv_pipeline.py (and available to all tests)
# ---------------------------------------------------------------------------


def _simulate_gbm_prices(
    n_ticks: int = 23400,
    sigma_annual: float = 0.20,
    dt_fraction: float = 1.0 / 252.0,
    seed: int = 42,
) -> np.ndarray:
    """Simulate log-prices from a GBM (no jumps) for one trading day."""
    rng = np.random.default_rng(seed)
    dt_per_tick = dt_fraction / n_ticks
    sigma_per_tick = sigma_annual * np.sqrt(dt_per_tick)
    increments = sigma_per_tick * rng.standard_normal(n_ticks)
    log_prices = np.zeros(n_ticks + 1)
    log_prices[0] = np.log(100.0)
    log_prices[1:] = log_prices[0] + np.cumsum(increments)
    return log_prices


def _simulate_gbm_with_jump(
    n_ticks: int = 23400,
    sigma_annual: float = 0.20,
    jump_size: float = 0.03,
    jump_index: int = 10000,
    seed: int = 42,
) -> np.ndarray:
    """Simulate log-prices with one injected jump."""
    log_prices = _simulate_gbm_prices(n_ticks, sigma_annual, seed=seed)
    log_prices[jump_index:] += jump_size
    return log_prices


def _sample_returns(log_prices: np.ndarray, freq: int) -> np.ndarray:
    """Sample returns at a given tick frequency."""
    sampled_prices = log_prices[::freq]
    return np.diff(sampled_prices)


@pytest.fixture
def gbm_log_prices():
    """23401 log-prices from GBM with sigma=20%, no jumps."""
    return _simulate_gbm_prices(n_ticks=23400, sigma_annual=0.20, seed=42)


@pytest.fixture
def gbm_5min_returns(gbm_log_prices):
    """78 five-minute returns (23400 ticks / 300 ticks per 5min)."""
    return _sample_returns(gbm_log_prices, freq=300)


@pytest.fixture
def jump_log_prices():
    """Log-prices with one 3% jump injected at tick 10000."""
    return _simulate_gbm_with_jump(n_ticks=23400, sigma_annual=0.20, jump_size=0.03, seed=42)


@pytest.fixture
def jump_5min_returns(jump_log_prices):
    """5-min returns from the jump path."""
    return _sample_returns(jump_log_prices, freq=300)


@pytest.fixture
def synthetic_rv_series():
    """~500 days of daily RV with realistic autocorrelation."""
    rng = np.random.default_rng(123)
    n_days = 500
    log_rv = np.zeros(n_days)
    log_rv[0] = np.log(1e-4)
    for t in range(1, n_days):
        log_rv[t] = -0.5 + 0.6 * log_rv[t - 1] + 0.3 * rng.standard_normal()
    dates = pd.bdate_range("2020-01-02", periods=n_days)
    return pd.Series(np.exp(log_rv), index=dates, name="rv")


# ---------------------------------------------------------------------------
# Feature matrix fixtures for model/CV tests
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_feature_df():
    """1000-row feature DataFrame mimicking HAR + extra features."""
    rng = np.random.default_rng(99)
    n = 1000
    dates = pd.bdate_range("2018-01-02", periods=n)
    log_rv_d = -9.0 + 0.5 * rng.standard_normal(n)
    log_rv_w = -9.0 + 0.4 * rng.standard_normal(n)
    log_rv_m = -9.0 + 0.3 * rng.standard_normal(n)
    rq = np.abs(rng.standard_normal(n)) * 1e-8
    return pd.DataFrame(
        {
            "log_rv_d": log_rv_d,
            "log_rv_w": log_rv_w,
            "log_rv_m": log_rv_m,
            "rq": rq,
            "rq_rv_interaction": rq * np.exp(log_rv_d),
        },
        index=dates,
    )


@pytest.fixture
def sample_target(sample_feature_df):
    """Target series (log RV_{t+1}) aligned with sample_feature_df."""
    rng = np.random.default_rng(77)
    n = len(sample_feature_df)
    target = (
        -1.0
        + 0.4 * sample_feature_df["log_rv_d"].values
        + 0.3 * sample_feature_df["log_rv_w"].values
        + 0.2 * sample_feature_df["log_rv_m"].values
        + 0.2 * rng.standard_normal(n)
    )
    return pd.Series(target, index=sample_feature_df.index, name="log_rv_target")


# ---------------------------------------------------------------------------
# Workspace fixtures for CLI / pipeline tests
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Temporary project root with workspace sub-directories pre-created."""
    for sub in ("data/raw/ticks", "data/models", "workspace/tmp"):
        (tmp_path / sub).mkdir(parents=True)
    return tmp_path
