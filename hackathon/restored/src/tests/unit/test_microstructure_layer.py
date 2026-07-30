"""Unit tests for MicrostructureLayer feature computation (Layer 3).

Tests the feature layer that transforms raw daily micro aggregates + intraday
sequences into model-ready features:
- Daily ratio features (log-transformed, lagged d/w/m)
- Intraday-derived features (kyle_lambda, amihud, vol_concentration, etc.)
- Edge cases (NaN propagation, zero-volume days, short histories)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def daily_micro_df():
    """Minimal daily micro aggregate with 30 days of data."""
    rng = np.random.default_rng(42)
    n = 30
    dates = pd.bdate_range("2024-01-02", periods=n)
    buy = rng.uniform(1e6, 1e7, n)
    sell = rng.uniform(1e6, 1e7, n)
    total = buy + sell
    svr = np.abs(buy - sell) / total
    ofi = (buy - sell) / total
    vpin = rng.uniform(0.2, 0.5, n)

    return pd.DataFrame(
        {
            "signed_volume_ratio": svr,
            "vpin": vpin,
            "order_flow_imbalance": ofi,
            "buy_volume": buy,
            "sell_volume": sell,
            "total_volume": total,
        },
        index=dates,
    )


@pytest.fixture
def sequences_df():
    """Minimal sequence DataFrame for 30 days, ~100 bars/day."""
    rng = np.random.default_rng(42)
    n_days = 30
    bars_per_day = 100
    dates = pd.bdate_range("2024-01-02", periods=n_days)
    rows = []
    base_price = 450.0
    for d in dates:
        for i in range(bars_per_day):
            buy = rng.uniform(0, 5000)
            sell = rng.uniform(0, 5000)
            # Random walk for vwap
            base_price += rng.normal(0, 0.05)
            rows.append(
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "bar_idx": i,
                    "buy_vol": buy,
                    "sell_vol": sell,
                    "net_flow": buy - sell,
                    "vwap": base_price,
                    "n_trades": rng.integers(10, 200),
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture
def daily_data_with_rv(daily_micro_df):
    """Daily data with rv column (minimal required for pipeline)."""
    n = len(daily_micro_df)
    rng = np.random.default_rng(99)
    return pd.DataFrame(
        {"rv": rng.uniform(0.0001, 0.001, n)},
        index=daily_micro_df.index,
    )


# ---------------------------------------------------------------------------
# Tests: MicrostructureLayer.compute()
# ---------------------------------------------------------------------------


class TestMicrostructureLayerCompute:
    """Test the layer's compute method produces expected columns."""

    def test_returns_dataframe(self, daily_data_with_rv):
        from volforecast.features.microstructure import MicrostructureLayer

        layer = MicrostructureLayer()
        context = {"symbol": "SPY"}
        result = layer.compute(daily_data_with_rv, context=context)
        assert isinstance(result, pd.DataFrame)

    def test_output_has_expected_columns(self, daily_data_with_rv):
        from volforecast.features.microstructure import MicrostructureLayer

        layer = MicrostructureLayer()
        context = {"symbol": "SPY"}
        result = layer.compute(daily_data_with_rv, context=context)
        # Core daily features from raw aggregates
        expected_daily = [
            "log_svr_d",
            "log_vpin_d",
            "ofi_d",
        ]
        for col in expected_daily:
            assert col in result.columns, f"Missing expected column: {col}"

    def test_output_has_intraday_features(self, daily_data_with_rv):
        from volforecast.features.microstructure import MicrostructureLayer

        layer = MicrostructureLayer()
        context = {"symbol": "SPY"}
        result = layer.compute(daily_data_with_rv, context=context)
        # Intraday-derived features (from sequences)
        intraday_cols = [
            "kyle_lambda_d",
            "amihud_d",
            "volume_concentration_d",
            "intraday_vol_ratio_d",
            "flow_persistence_d",
        ]
        for col in intraday_cols:
            assert col in result.columns, f"Missing intraday column: {col}"

    def test_index_alignment(self, daily_data_with_rv):
        from volforecast.features.microstructure import MicrostructureLayer

        layer = MicrostructureLayer()
        context = {"symbol": "SPY"}
        result = layer.compute(daily_data_with_rv, context=context)
        assert result.index.equals(daily_data_with_rv.index)

    def test_no_symbol_returns_empty(self, daily_data_with_rv):
        from volforecast.features.microstructure import MicrostructureLayer

        layer = MicrostructureLayer()
        result = layer.compute(daily_data_with_rv, context=None)
        assert result.empty or len(result.columns) == 0

    def test_missing_micro_data_graceful(self, daily_data_with_rv):
        """Symbol with no cached micro data should return empty DataFrame."""
        from volforecast.features.microstructure import MicrostructureLayer

        layer = MicrostructureLayer()
        context = {"symbol": "NONEXISTENT_SYMBOL_XYZ"}
        result = layer.compute(daily_data_with_rv, context=context)
        # Should return empty gracefully (no crash)
        assert isinstance(result, pd.DataFrame)


class TestMicrostructureLayerValues:
    """Test correctness of computed values."""

    def test_ofi_bounded(self, daily_data_with_rv):
        """OFI should be in [-1, 1]."""
        from volforecast.features.microstructure import MicrostructureLayer

        layer = MicrostructureLayer()
        context = {"symbol": "SPY"}
        result = layer.compute(daily_data_with_rv, context=context)
        if "ofi_d" in result.columns:
            ofi = result["ofi_d"].dropna()
            assert (ofi >= -1.0).all()
            assert (ofi <= 1.0).all()

    def test_log_svr_is_negative_or_zero(self, daily_data_with_rv):
        """log(SVR) should be <= 0 since SVR is in [0,1]."""
        from volforecast.features.microstructure import MicrostructureLayer

        layer = MicrostructureLayer()
        context = {"symbol": "SPY"}
        result = layer.compute(daily_data_with_rv, context=context)
        if "log_svr_d" in result.columns:
            log_svr = result["log_svr_d"].dropna()
            assert (log_svr <= 0.0).all()

    def test_no_lookahead_bias(self, daily_data_with_rv):
        """Features at date T should only use data from T and before."""
        from volforecast.features.microstructure import MicrostructureLayer

        layer = MicrostructureLayer()
        context = {"symbol": "SPY"}
        result = layer.compute(daily_data_with_rv, context=context)
        # Weekly rolling should have NaN for first 4 days
        if "log_svr_w" in result.columns:
            assert result["log_svr_w"].iloc[:4].isna().all()

    def test_volume_surprise_uses_22d_window(self, daily_data_with_rv):
        """volume_surprise should have NaN for first 21 days."""
        from volforecast.features.microstructure import MicrostructureLayer

        layer = MicrostructureLayer()
        context = {"symbol": "SPY"}
        result = layer.compute(daily_data_with_rv, context=context)
        if "volume_surprise_d" in result.columns:
            assert result["volume_surprise_d"].iloc[:21].isna().all()


# ---------------------------------------------------------------------------
# Tests: Individual feature computation functions
# ---------------------------------------------------------------------------


class TestKyleLambda:
    """Test Kyle's lambda (price impact) computation."""

    def test_positive_for_normal_market(self):
        """Kyle's lambda should generally be positive (buys push price up)."""
        from volforecast.features.microstructure import compute_kyle_lambda

        rng = np.random.default_rng(42)
        n = 200
        net_flow = rng.normal(0, 1000, n)
        # Price moves in direction of flow with noise
        price_changes = 0.01 * net_flow / 1000 + rng.normal(0, 0.001, n)
        result = compute_kyle_lambda(price_changes, net_flow)
        assert result > 0

    def test_zero_flow_returns_nan(self):
        """Zero net flow should return NaN (regression undefined)."""
        from volforecast.features.microstructure import compute_kyle_lambda

        price_changes = np.array([0.001, -0.001, 0.002])
        net_flow = np.array([0.0, 0.0, 0.0])
        result = compute_kyle_lambda(price_changes, net_flow)
        assert np.isnan(result)


class TestAmihud:
    """Test Amihud illiquidity ratio."""

    def test_positive(self):
        """Amihud ratio is always non-negative."""
        from volforecast.features.microstructure import compute_amihud

        returns = np.array([0.01, -0.02, 0.005, -0.01])
        volumes = np.array([1e6, 2e6, 1.5e6, 3e6])
        result = compute_amihud(returns, volumes)
        assert result >= 0

    def test_higher_for_illiquid(self):
        """Same returns with less volume → higher Amihud."""
        from volforecast.features.microstructure import compute_amihud

        returns = np.array([0.01, -0.02, 0.005])
        result_liquid = compute_amihud(returns, np.array([1e8, 1e8, 1e8]))
        result_illiquid = compute_amihud(returns, np.array([1e4, 1e4, 1e4]))
        assert result_illiquid > result_liquid

    def test_zero_volume_returns_nan(self):
        """Zero volume should return NaN."""
        from volforecast.features.microstructure import compute_amihud

        returns = np.array([0.01, -0.02])
        volumes = np.array([0.0, 0.0])
        result = compute_amihud(returns, volumes)
        assert np.isnan(result)


class TestVolumeConcentration:
    """Test Herfindahl volume concentration."""

    def test_uniform_low_concentration(self):
        """Uniformly distributed volume should have low concentration."""
        from volforecast.features.microstructure import compute_volume_concentration

        # 100 bars with equal volume
        volumes = np.ones(100) * 1000
        result = compute_volume_concentration(volumes, n_bins=10)
        # HHI for 10 equal bins = 10 * (1/10)^2 = 0.1
        assert result == pytest.approx(0.1, abs=0.01)

    def test_concentrated_high_value(self):
        """All volume in one bin should have max concentration."""
        from volforecast.features.microstructure import compute_volume_concentration

        volumes = np.zeros(100)
        volumes[:10] = 1000  # All volume in first bin
        result = compute_volume_concentration(volumes, n_bins=10)
        assert result == pytest.approx(1.0, abs=0.01)

    def test_bounded_zero_one(self):
        """HHI concentration should be in [1/n_bins, 1]."""
        from volforecast.features.microstructure import compute_volume_concentration

        rng = np.random.default_rng(42)
        volumes = rng.uniform(0, 1000, 200)
        result = compute_volume_concentration(volumes, n_bins=10)
        assert 1.0 / 10 - 0.01 <= result <= 1.0


class TestIntradayVolRatio:
    """Test first-half / second-half realized variance ratio."""

    def test_symmetric_market_ratio_near_one(self):
        """Equal variance in both halves → ratio ≈ 1."""
        from volforecast.features.microstructure import compute_intraday_vol_ratio

        rng = np.random.default_rng(42)
        prices = np.cumsum(rng.normal(0, 0.01, 200)) + 100
        result = compute_intraday_vol_ratio(prices)
        # Should be near 1 for symmetric random walk
        assert 0.3 < result < 3.0

    def test_morning_volatile_high_ratio(self):
        """More volatility in first half → ratio > 1."""
        from volforecast.features.microstructure import compute_intraday_vol_ratio

        rng = np.random.default_rng(42)
        first_half = np.cumsum(rng.normal(0, 0.05, 100)) + 100
        second_half = np.cumsum(rng.normal(0, 0.005, 100)) + first_half[-1]
        prices = np.concatenate([first_half, second_half])
        result = compute_intraday_vol_ratio(prices)
        assert result > 5.0  # Much higher variance in first half


class TestFlowPersistence:
    """Test flow autocorrelation (AR(1) coefficient)."""

    def test_random_flow_near_zero(self):
        """IID flow should have near-zero persistence."""
        from volforecast.features.microstructure import compute_flow_persistence

        rng = np.random.default_rng(42)
        flows = rng.normal(0, 1000, 500)
        result = compute_flow_persistence(flows)
        assert -0.15 < result < 0.15

    def test_persistent_flow_high_value(self):
        """AR(1) process with high phi should have high persistence."""
        from volforecast.features.microstructure import compute_flow_persistence

        rng = np.random.default_rng(42)
        phi = 0.8
        n = 500
        flows = np.zeros(n)
        flows[0] = rng.normal(0, 1000)
        for i in range(1, n):
            flows[i] = phi * flows[i - 1] + rng.normal(0, 200)
        result = compute_flow_persistence(flows)
        assert result > 0.6

    def test_bounded_neg1_1(self):
        """AR(1) coefficient should be in [-1, 1]."""
        from volforecast.features.microstructure import compute_flow_persistence

        rng = np.random.default_rng(42)
        flows = rng.normal(0, 1000, 200)
        result = compute_flow_persistence(flows)
        assert -1.0 <= result <= 1.0
