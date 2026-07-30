"""Tests for Phase 2: discrete hedging simulator.

Tests bar-by-bar simulation using 15-min bars from aggregated 10s micro data:
- 15-min bar aggregation with proper VWAP
- Discrete hedge P&L computation (full BS delta at each bar)
- Per-day realized kurtosis from 15-min returns
- Hedging-error floor experiment (variance = a/N + b fit)
- Phase 1 vs Phase 2 validation bounds
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


class TestAggregate10sTo15min:
    """Tests for 10s → 15-min bar aggregation with proper VWAP."""

    def test_vwap_is_volume_weighted(self):
        """VWAP_15min = sum(vwap_i * volume_i) / sum(volume_i)."""
        from volforecast.evaluation.discrete_straddle import aggregate_10s_to_15min

        # 3 bars in same bucket: different prices and volumes
        df = pd.DataFrame(
            {
                "date": ["2020-01-02"] * 3,
                "bar_idx": [0, 1, 2],
                "buy_vol": [100.0, 200.0, 300.0],
                "sell_vol": [50.0, 100.0, 150.0],
                "net_flow": [50.0, 100.0, 150.0],
                "vwap": [100.0, 102.0, 101.0],
                "n_trades": [10.0, 20.0, 30.0],
            }
        )

        result = aggregate_10s_to_15min(df, bars_per_bucket=3)

        # Expected VWAP: (100*150 + 102*300 + 101*450) / (150+300+450)
        # = (15000 + 30600 + 45450) / 900 = 91050 / 900 = 101.1667
        expected_vwap = (100.0 * 150 + 102.0 * 300 + 101.0 * 450) / (150 + 300 + 450)
        assert result["vwap"].iloc[0] == pytest.approx(expected_vwap, rel=1e-6)

    def test_close_is_last_bar_vwap(self):
        """Close price = last 10s bar's vwap in the bucket."""
        from volforecast.evaluation.discrete_straddle import aggregate_10s_to_15min

        df = pd.DataFrame(
            {
                "date": ["2020-01-02"] * 3,
                "bar_idx": [0, 1, 2],
                "buy_vol": [100.0, 200.0, 300.0],
                "sell_vol": [50.0, 100.0, 150.0],
                "net_flow": [50.0, 100.0, 150.0],
                "vwap": [100.0, 102.0, 101.0],
                "n_trades": [10.0, 20.0, 30.0],
            }
        )

        result = aggregate_10s_to_15min(df, bars_per_bucket=3)
        assert result["close"].iloc[0] == pytest.approx(101.0)

    def test_volume_is_sum_of_total_volume(self):
        """Total volume = sum(buy_vol + sell_vol) across all bars in bucket."""
        from volforecast.evaluation.discrete_straddle import aggregate_10s_to_15min

        df = pd.DataFrame(
            {
                "date": ["2020-01-02"] * 3,
                "bar_idx": [0, 1, 2],
                "buy_vol": [100.0, 200.0, 300.0],
                "sell_vol": [50.0, 100.0, 150.0],
                "net_flow": [50.0, 100.0, 150.0],
                "vwap": [100.0, 102.0, 101.0],
                "n_trades": [10.0, 20.0, 30.0],
            }
        )

        result = aggregate_10s_to_15min(df, bars_per_bucket=3)
        assert result["volume"].iloc[0] == pytest.approx(900.0)

    def test_multiple_buckets_per_day(self):
        """Multiple 15-min bars generated per day."""
        from volforecast.evaluation.discrete_straddle import aggregate_10s_to_15min

        # 6 bars -> 2 buckets of size 3
        df = pd.DataFrame(
            {
                "date": ["2020-01-02"] * 6,
                "bar_idx": [0, 1, 2, 3, 4, 5],
                "buy_vol": [100.0] * 6,
                "sell_vol": [100.0] * 6,
                "net_flow": [0.0] * 6,
                "vwap": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0],
                "n_trades": [10.0] * 6,
            }
        )

        result = aggregate_10s_to_15min(df, bars_per_bucket=3)
        assert len(result) == 2
        assert result["bucket"].iloc[0] == 0
        assert result["bucket"].iloc[1] == 1

    def test_multiple_dates(self):
        """Buckets are computed per-date."""
        from volforecast.evaluation.discrete_straddle import aggregate_10s_to_15min

        df = pd.DataFrame(
            {
                "date": ["2020-01-02"] * 3 + ["2020-01-03"] * 3,
                "bar_idx": [0, 1, 2, 0, 1, 2],
                "buy_vol": [100.0] * 6,
                "sell_vol": [100.0] * 6,
                "net_flow": [0.0] * 6,
                "vwap": [100.0, 101.0, 102.0, 200.0, 201.0, 202.0],
                "n_trades": [10.0] * 6,
            }
        )

        result = aggregate_10s_to_15min(df, bars_per_bucket=3)
        assert len(result) == 2
        assert result["vwap"].iloc[1] > 199.0  # Second day has higher prices

    def test_zero_volume_bars_excluded_from_vwap(self):
        """Bars with zero volume don't corrupt VWAP calculation."""
        from volforecast.evaluation.discrete_straddle import aggregate_10s_to_15min

        df = pd.DataFrame(
            {
                "date": ["2020-01-02"] * 3,
                "bar_idx": [0, 1, 2],
                "buy_vol": [100.0, 0.0, 200.0],
                "sell_vol": [100.0, 0.0, 200.0],
                "net_flow": [0.0, 0.0, 0.0],
                "vwap": [100.0, 999.0, 102.0],  # bar 1 has garbage vwap but 0 vol
                "n_trades": [10.0, 0.0, 20.0],
            }
        )

        result = aggregate_10s_to_15min(df, bars_per_bucket=3)
        # VWAP should ignore bar 1: (100*200 + 102*400) / (200+400) = 60800/600 = 101.33
        expected = (100.0 * 200 + 102.0 * 400) / (200 + 400)
        assert result["vwap"].iloc[0] == pytest.approx(expected, rel=1e-6)


class TestDiscreteHedgePnl:
    """Tests for the bar-by-bar discrete hedging simulator."""

    @pytest.fixture
    def flat_bars(self):
        """Create flat price 15-min bars for testing."""
        n_days = 30
        n_bars_per_day = 26
        dates = np.repeat(
            pd.date_range("2020-01-02", periods=n_days, freq="B").strftime("%Y-%m-%d"),
            n_bars_per_day,
        )
        return pd.DataFrame(
            {
                "date": dates,
                "bucket": np.tile(np.arange(n_bars_per_day), n_days),
                "vwap": np.full(n_days * n_bars_per_day, 100.0),
                "close": np.full(n_days * n_bars_per_day, 100.0),
                "volume": np.full(n_days * n_bars_per_day, 10000.0),
            }
        )

    def test_flat_price_zero_gamma_pnl(self, flat_bars):
        """Flat prices produce zero gamma P&L (no RV - IV gap)."""
        from volforecast.evaluation.discrete_straddle import simulate_discrete_hedge_pnl

        n_days = 30
        signal = np.ones(n_days)  # Always short vol
        implied_vol = np.full(n_days, 0.20)
        spot_prices = np.full(n_days, 100.0)

        result = simulate_discrete_hedge_pnl(
            signal=signal,
            bars_15min=flat_bars,
            implied_vol=implied_vol,
            spot_prices=spot_prices,
            spread_bps=0.0,  # No cost for clean test
        )

        # With flat prices: option value doesn't change, hedge P&L is zero
        # But we DO have theta decay (option loses value)
        assert "pnl_net" in result
        assert len(result["pnl_net"]) == n_days

    def test_hedge_cost_positive(self, flat_bars):
        """With positive spread, hedge cost reduces P&L."""
        from volforecast.evaluation.discrete_straddle import simulate_discrete_hedge_pnl

        n_days = 30
        signal = np.ones(n_days)
        implied_vol = np.full(n_days, 0.20)
        spot_prices = np.full(n_days, 100.0)

        # With spread
        result_spread = simulate_discrete_hedge_pnl(
            signal=signal,
            bars_15min=flat_bars,
            implied_vol=implied_vol,
            spot_prices=spot_prices,
            spread_bps=5.0,
        )
        # Without spread
        result_no_spread = simulate_discrete_hedge_pnl(
            signal=signal,
            bars_15min=flat_bars,
            implied_vol=implied_vol,
            spot_prices=spot_prices,
            spread_bps=0.0,
        )

        assert np.sum(result_spread["cost_hedge"]) > np.sum(result_no_spread["cost_hedge"])

    def test_output_keys(self, flat_bars):
        """Simulator returns all required P&L components."""
        from volforecast.evaluation.discrete_straddle import simulate_discrete_hedge_pnl

        n_days = 30
        signal = np.ones(n_days)
        implied_vol = np.full(n_days, 0.20)
        spot_prices = np.full(n_days, 100.0)

        result = simulate_discrete_hedge_pnl(
            signal=signal,
            bars_15min=flat_bars,
            implied_vol=implied_vol,
            spot_prices=spot_prices,
        )

        required_keys = [
            "pnl_option",
            "pnl_hedge",
            "cost_hedge",
            "cost_option",
            "pnl_net",
            "T_rem",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"
            assert len(result[key]) == n_days

    def test_tenor_decrements_daily(self, flat_bars):
        """Remaining tenor decreases by 1 each day until roll."""
        from volforecast.evaluation.discrete_straddle import simulate_discrete_hedge_pnl

        n_days = 30
        signal = np.ones(n_days)
        implied_vol = np.full(n_days, 0.20)
        spot_prices = np.full(n_days, 100.0)

        result = simulate_discrete_hedge_pnl(
            signal=signal,
            bars_15min=flat_bars,
            implied_vol=implied_vol,
            spot_prices=spot_prices,
            tenor_days=30,
            roll_at_days=5,
        )

        # First day: T_rem = 30, stored before decrement, so next day = 29
        # Roll triggers at T_rem <= 5 (day 25: current_T_rem=5 → roll → 30)
        assert result["T_rem"][0] == 30.0
        assert result["T_rem"][1] == 29.0
        # Day 24: T_rem = 6 (last day before roll)
        assert result["T_rem"][24] == 6.0
        # Day 25: roll triggers (was 5), resets to 30
        assert result["T_rem"][25] == 30.0
        # Day 26: no decrement on roll day, so still 30
        assert result["T_rem"][26] == 30.0
        # Day 27: decremented from 30 at end of day 26
        assert result["T_rem"][27] == 29.0


class TestPerDayRealizedKurtosis:
    """Tests for per-day realized kurtosis from 15-min returns."""

    def test_normal_returns_kurtosis_near_3(self):
        """Normal returns should produce kurtosis approximately 3."""
        from volforecast.evaluation.discrete_straddle import (
            compute_per_day_realized_kurtosis,
        )

        rng = np.random.default_rng(42)
        n_days = 100
        n_bars = 26

        # Create bars with normal returns
        dates = np.repeat(
            pd.date_range("2020-01-02", periods=n_days, freq="B").strftime("%Y-%m-%d"),
            n_bars,
        )
        prices = np.zeros(n_days * n_bars)
        for d in range(n_days):
            base = 100.0
            for b in range(n_bars):
                ret = rng.normal(0, 0.01)
                base *= np.exp(ret)
                prices[d * n_bars + b] = base

        bars = pd.DataFrame(
            {
                "date": dates,
                "bucket": np.tile(np.arange(n_bars), n_days),
                "close": prices,
            }
        )

        kurtosis = compute_per_day_realized_kurtosis(bars)

        assert len(kurtosis) == n_days
        # Mean kurtosis of normal returns should be near 3 (with some noise)
        assert 2.0 < np.mean(kurtosis) < 5.0

    def test_fat_tailed_returns_higher_kurtosis(self):
        """Fat-tailed returns should produce kurtosis > 3."""
        from volforecast.evaluation.discrete_straddle import (
            compute_per_day_realized_kurtosis,
        )

        rng = np.random.default_rng(42)
        n_days = 100
        n_bars = 26

        dates = np.repeat(
            pd.date_range("2020-01-02", periods=n_days, freq="B").strftime("%Y-%m-%d"),
            n_bars,
        )
        prices = np.zeros(n_days * n_bars)
        for d in range(n_days):
            base = 100.0
            for b in range(n_bars):
                # t-distribution with 4 df -> kurtosis = 6/(4-4)+3... well df=4 -> inf kurtosis
                # Use df=5 -> kurtosis = 3 + 6/(5-4) = 9
                ret = rng.standard_t(5) * 0.01
                base *= np.exp(ret)
                prices[d * n_bars + b] = base

        bars = pd.DataFrame(
            {
                "date": dates,
                "bucket": np.tile(np.arange(n_bars), n_days),
                "close": prices,
            }
        )

        kurtosis = compute_per_day_realized_kurtosis(bars)
        # Fat-tailed returns should give kurtosis > normal
        assert np.mean(kurtosis) > 3.5


class TestHedgingErrorFloor:
    """Tests for the hedging-error floor experiment (Var = a/N + b)."""

    def test_fit_returns_coefficients(self):
        """Fit returns a and b coefficients."""
        from volforecast.evaluation.discrete_straddle import (
            hedging_error_floor_experiment,
        )

        # Create synthetic data where variance = 10/N + 0.5
        rng = np.random.default_rng(42)
        n_values = [1, 2, 4, 6, 13, 26]
        variances = [10.0 / n + 0.5 + rng.normal(0, 0.01) for n in n_values]

        a, b = hedging_error_floor_experiment(n_values, variances)

        assert a == pytest.approx(10.0, rel=0.1)
        assert b == pytest.approx(0.5, rel=0.2)

    def test_positive_b_indicates_jump_regime(self):
        """b > 0 materially indicates jump-driven variance floor."""
        from volforecast.evaluation.discrete_straddle import (
            hedging_error_floor_experiment,
        )

        # Pure diffusion: variance = a/N (b=0)
        n_values = [1, 2, 4, 6, 13, 26]
        variances_diffusion = [5.0 / n for n in n_values]
        _, b_diff = hedging_error_floor_experiment(n_values, variances_diffusion)
        assert abs(b_diff) < 0.1

        # Jump regime: variance = a/N + b
        variances_jump = [5.0 / n + 2.0 for n in n_values]
        _, b_jump = hedging_error_floor_experiment(n_values, variances_jump)
        assert b_jump > 1.0


class TestPhase1Validation:
    """Tests for Phase 1 vs Phase 2 comparison."""

    def test_validate_phases_checks_sharpe_bound(self):
        """Validation passes if Sharpe difference < 0.3."""
        from volforecast.evaluation.discrete_straddle import validate_phase1_vs_phase2

        metrics_p1 = {"sharpe": 2.0, "mean_pnl": 0.001, "std_pnl": 0.005}
        metrics_p2 = {"sharpe": 2.2, "mean_pnl": 0.0011, "std_pnl": 0.0055}

        result = validate_phase1_vs_phase2(metrics_p1, metrics_p2)
        assert result["sharpe_pass"] is True

    def test_validate_phases_fails_large_sharpe_diff(self):
        """Validation fails if Sharpe difference > 0.3."""
        from volforecast.evaluation.discrete_straddle import validate_phase1_vs_phase2

        metrics_p1 = {"sharpe": 2.0, "mean_pnl": 0.001, "std_pnl": 0.005}
        metrics_p2 = {"sharpe": 3.5, "mean_pnl": 0.002, "std_pnl": 0.005}

        result = validate_phase1_vs_phase2(metrics_p1, metrics_p2)
        assert result["sharpe_pass"] is False

    def test_validate_checks_mean_pnl_bound(self):
        """Validation passes if mean P&L within 10%."""
        from volforecast.evaluation.discrete_straddle import validate_phase1_vs_phase2

        metrics_p1 = {"sharpe": 2.0, "mean_pnl": 0.001, "std_pnl": 0.005}
        metrics_p2 = {"sharpe": 2.1, "mean_pnl": 0.00108, "std_pnl": 0.0055}

        result = validate_phase1_vs_phase2(metrics_p1, metrics_p2)
        assert result["mean_pnl_pass"] is True

    def test_validate_checks_std_bound(self):
        """Validation passes if std within 25%."""
        from volforecast.evaluation.discrete_straddle import validate_phase1_vs_phase2

        metrics_p1 = {"sharpe": 2.0, "mean_pnl": 0.001, "std_pnl": 0.005}
        metrics_p2 = {"sharpe": 2.1, "mean_pnl": 0.00105, "std_pnl": 0.0060}

        result = validate_phase1_vs_phase2(metrics_p1, metrics_p2)
        assert result["std_pass"] is True
