"""Tests for economic value functions (vol-targeting, delta-hedged straddle)."""

from __future__ import annotations

import numpy as np
import pytest

from volforecast.evaluation.economic_value import (
    compute_max_drawdown,
    compute_sharpe,
    delta_hedged_sharpe,
    delta_hedged_straddle_pnl,
    iv_rv_gap_signal,
    vol_targeting_pnl,
    vol_targeting_sharpe,
)


class TestVolTargetingPnl:
    """Tests for vol_targeting_pnl."""

    def test_constant_vol_produces_constant_weight(self):
        """With constant vol forecast, weight = target/forecast."""
        returns = np.array([0.01, -0.005, 0.02, -0.01, 0.015])
        vol_forecast = np.full(5, 0.20)  # 20% annualized
        target = 0.10

        result = vol_targeting_pnl(returns, vol_forecast, target_vol=target)
        expected_weight = target / 0.20  # 0.5
        expected = returns * expected_weight
        np.testing.assert_allclose(result, expected, rtol=1e-10)

    def test_leverage_cap_enforced(self):
        """Weight should never exceed max_leverage."""
        returns = np.array([0.01, 0.02])
        # Very low vol -> would need huge leverage
        vol_forecast = np.array([0.01, 0.01])
        target = 0.10
        max_lev = 2.0

        result = vol_targeting_pnl(returns, vol_forecast, target_vol=target, max_leverage=max_lev)
        # target/vol = 10.0, but capped at 2.0
        expected = returns * max_lev
        np.testing.assert_allclose(result, expected, rtol=1e-10)

    def test_high_vol_reduces_position(self):
        """High forecast vol reduces weight below 1."""
        returns = np.array([0.01])
        vol_forecast = np.array([0.30])  # 30% annual
        target = 0.10

        result = vol_targeting_pnl(returns, vol_forecast, target_vol=target)
        weight = target / 0.30  # ~0.333
        assert result[0] == pytest.approx(0.01 * weight, rel=1e-10)

    def test_zero_vol_handled(self):
        """Zero vol forecast should not produce inf (clamped)."""
        returns = np.array([0.01])
        vol_forecast = np.array([0.0])

        result = vol_targeting_pnl(returns, vol_forecast, target_vol=0.10, max_leverage=2.0)
        # Should be capped at max_leverage
        assert result[0] == pytest.approx(0.01 * 2.0, rel=1e-10)

    def test_negative_returns_preserved(self):
        """Negative returns remain negative after weighting."""
        returns = np.array([-0.02, -0.01])
        vol_forecast = np.array([0.15, 0.15])

        result = vol_targeting_pnl(returns, vol_forecast, target_vol=0.10)
        assert all(r < 0 for r in result)


class TestComputeSharpe:
    """Tests for compute_sharpe."""

    def test_zero_vol_returns_zero(self):
        """Constant returns (zero std) -> Sharpe = 0."""
        returns = np.full(100, 0.001)
        assert compute_sharpe(returns) == 0.0

    def test_positive_sharpe(self):
        """Positive mean excess return -> positive Sharpe."""
        rng = np.random.default_rng(42)
        # Generate returns with positive drift
        returns = rng.normal(0.0004, 0.01, 1000)  # ~10% annual, 16% vol
        sharpe = compute_sharpe(returns)
        assert sharpe > 0

    def test_annualization(self):
        """Sharpe should scale with sqrt(annualization)."""
        rng = np.random.default_rng(7)
        returns = rng.normal(0.001, 0.02, 500)

        s252 = compute_sharpe(returns, annualization=252)
        s1 = compute_sharpe(returns, annualization=1)
        assert s252 == pytest.approx(s1 * np.sqrt(252), rel=1e-10)

    def test_risk_free_rate(self):
        """Non-zero risk-free rate reduces Sharpe."""
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.01, 500)

        s_no_rf = compute_sharpe(returns, risk_free_rate=0.0)
        s_with_rf = compute_sharpe(returns, risk_free_rate=0.05)
        assert s_with_rf < s_no_rf

    def test_single_observation(self):
        """Single observation -> Sharpe = 0."""
        assert compute_sharpe(np.array([0.01])) == 0.0

    def test_nan_in_returns_ignored(self):
        """NaN values in returns should be excluded, not propagate NaN."""
        rng = np.random.default_rng(42)
        returns = rng.normal(0.0004, 0.01, 1000)
        # Inject NaN at boundaries (mimics shift(-1) last obs per symbol)
        returns[249] = np.nan
        returns[499] = np.nan
        returns[999] = np.nan
        sharpe = compute_sharpe(returns)
        assert np.isfinite(sharpe)
        assert sharpe > 0  # positive drift should still produce positive Sharpe


class TestComputeMaxDrawdown:
    """Tests for compute_max_drawdown."""

    def test_monotonically_increasing(self):
        """No drawdown in a monotonically increasing series."""
        cumret = np.array([1.0, 1.01, 1.02, 1.03, 1.04])
        assert compute_max_drawdown(cumret) == 0.0

    def test_known_drawdown(self):
        """50% peak-to-trough drawdown."""
        cumret = np.array([1.0, 2.0, 1.0, 1.5])
        # Peak = 2.0, trough = 1.0 -> DD = (1-2)/2 = -0.5
        assert compute_max_drawdown(cumret) == pytest.approx(-0.5, rel=1e-10)

    def test_single_point(self):
        """Single point -> no drawdown."""
        assert compute_max_drawdown(np.array([1.0])) == 0.0

    def test_negative_result(self):
        """Drawdown is always <= 0."""
        rng = np.random.default_rng(42)
        cumret = np.cumprod(1 + rng.normal(0.0001, 0.01, 500))
        dd = compute_max_drawdown(cumret)
        assert dd <= 0.0


class TestVolTargetingSharpe:
    """Tests for vol_targeting_sharpe (end-to-end)."""

    def test_better_forecast_higher_sharpe(self):
        """A perfect vol forecast should produce higher Sharpe than a noisy one."""
        rng = np.random.default_rng(42)
        n = 1000
        # Generate daily returns with time-varying vol
        true_daily_vol = 0.01 + 0.005 * np.sin(np.arange(n) * 2 * np.pi / 252)
        returns = rng.normal(0.0004, true_daily_vol)

        # True log-RV: log(daily_vol^2) since RV ≈ daily_vol^2
        true_log_rv = np.log(true_daily_vol**2)

        # Noisy log-RV: add significant noise
        noisy_log_rv = true_log_rv + rng.normal(0, 1.0, n)

        sharpe_good = vol_targeting_sharpe(true_log_rv, returns)
        sharpe_noisy = vol_targeting_sharpe(noisy_log_rv, returns)

        # Perfect forecast should give better risk-adjusted returns
        assert sharpe_good > sharpe_noisy

    def test_returns_finite(self):
        """Output should always be a finite number."""
        rng = np.random.default_rng(99)
        log_rv_preds = rng.normal(-9.0, 1.0, 200)
        daily_returns = rng.normal(0, 0.01, 200)

        sharpe = vol_targeting_sharpe(log_rv_preds, daily_returns)
        assert np.isfinite(sharpe)

    def test_flat_forecast(self):
        """A constant forecast should produce a valid Sharpe."""
        rng = np.random.default_rng(42)
        n = 500
        log_rv_preds = np.full(n, -9.0)  # constant prediction
        daily_returns = rng.normal(0.0003, 0.01, n)

        sharpe = vol_targeting_sharpe(log_rv_preds, daily_returns)
        assert np.isfinite(sharpe)

    def test_nan_in_returns_produces_finite_sharpe(self):
        """NaN in daily_returns (from shift(-1) last obs) should not propagate."""
        rng = np.random.default_rng(42)
        n = 500
        log_rv_preds = rng.normal(-9.0, 0.5, n)
        daily_returns = rng.normal(0.0003, 0.01, n)
        # Simulate pooled multi-symbol: last obs per symbol is NaN
        daily_returns[249] = np.nan
        daily_returns[499] = np.nan

        sharpe = vol_targeting_sharpe(log_rv_preds, daily_returns)
        assert np.isfinite(sharpe)


class TestIVRVGapSignal:
    """Tests for iv_rv_gap_signal."""

    def test_sell_when_iv_exceeds_rv(self):
        """Signal = +1 when IV > RV forecast."""
        iv = np.array([0.25, 0.20, 0.15])
        rv = np.array([0.20, 0.20, 0.20])
        signal = iv_rv_gap_signal(iv, rv, threshold=0.0)
        assert signal[0] == 1.0  # IV > RV -> sell
        assert signal[1] == 0.0  # IV == RV -> flat
        assert signal[2] == -1.0  # IV < RV -> buy

    def test_threshold_creates_dead_zone(self):
        """With threshold > 0, small gaps produce signal = 0."""
        iv = np.array([0.22, 0.20, 0.18])
        rv = np.array([0.20, 0.20, 0.20])
        signal = iv_rv_gap_signal(iv, rv, threshold=0.03)
        # gap = [+0.02, 0.0, -0.02], all within threshold of 0.03
        np.testing.assert_array_equal(signal, [0.0, 0.0, 0.0])

    def test_large_gap_exceeds_threshold(self):
        """Large gaps exceed threshold."""
        iv = np.array([0.30, 0.10])
        rv = np.array([0.20, 0.20])
        signal = iv_rv_gap_signal(iv, rv, threshold=0.05)
        assert signal[0] == 1.0  # gap = +0.10 > 0.05
        assert signal[1] == -1.0  # gap = -0.10 < -0.05

    def test_output_in_valid_range(self):
        """Signal should only be in {-1, 0, +1}."""
        rng = np.random.default_rng(42)
        iv = rng.uniform(0.10, 0.40, 100)
        rv = rng.uniform(0.10, 0.40, 100)
        signal = iv_rv_gap_signal(iv, rv)
        assert set(np.unique(signal)).issubset({-1.0, 0.0, 1.0})

    def test_short_threshold_asymmetric(self):
        """short_threshold raises the bar for -1 signals (buy vol)."""
        iv = np.array([0.25, 0.20, 0.15, 0.10])
        rv = np.array([0.20, 0.20, 0.20, 0.20])
        # gap = [+0.05, 0.0, -0.05, -0.10]
        # threshold=0 for +1, short_threshold=0.08 for -1
        signal = iv_rv_gap_signal(iv, rv, threshold=0.0, short_threshold=0.08)
        assert signal[0] == 1.0  # gap +0.05 > 0 → sell vol
        assert signal[1] == 0.0  # gap 0 → flat
        assert signal[2] == 0.0  # gap -0.05 > -0.08 → NOT enough to buy vol
        assert signal[3] == -1.0  # gap -0.10 < -0.08 → buy vol

    def test_short_threshold_none_uses_threshold(self):
        """When short_threshold is None, symmetric behavior (uses threshold)."""
        iv = np.array([0.25, 0.15])
        rv = np.array([0.20, 0.20])
        signal_sym = iv_rv_gap_signal(iv, rv, threshold=0.03)
        signal_asym = iv_rv_gap_signal(iv, rv, threshold=0.03, short_threshold=None)
        np.testing.assert_array_equal(signal_sym, signal_asym)


class TestDeltaHedgedStraddlePnl:
    """Tests for delta_hedged_straddle_pnl."""

    def test_flat_signal_produces_zero_pnl(self):
        """Signal = 0 should produce zero (or near-zero) P&L."""
        n = 50
        signal = np.zeros(n)
        rv = np.full(n, 0.0002)  # daily var
        iv = np.full(n, 0.20)  # 20% annualized
        spot = np.full(n, 100.0)
        pnl = delta_hedged_straddle_pnl(signal, rv, iv, spot)
        np.testing.assert_allclose(pnl, 0.0, atol=1e-10)

    def test_sell_vol_profits_when_rv_below_iv(self):
        """Selling vol (signal=+1) profits when realized < implied."""
        n = 100
        signal = np.ones(n)
        # IV = 20% annualized -> daily implied var = (0.20^2)/252 ≈ 0.000159
        iv = np.full(n, 0.20)
        # RV is lower than implied: daily var = 0.0001 (≈ 15.9% annualized)
        rv = np.full(n, 0.0001)
        spot = np.full(n, 100.0)
        pnl = delta_hedged_straddle_pnl(signal, rv, iv, spot, cost_vol_points=0.0)
        # Should have positive P&L (sold vol at 20%, realized only 15.9%)
        assert np.mean(pnl) > 0

    def test_buy_vol_profits_when_rv_above_iv(self):
        """Buying vol (signal=-1) profits when realized > implied."""
        n = 100
        signal = -np.ones(n)
        iv = np.full(n, 0.15)  # 15% implied
        # RV is higher: daily var = 0.0003 (~27.5% annualized)
        rv = np.full(n, 0.0003)
        spot = np.full(n, 100.0)
        pnl = delta_hedged_straddle_pnl(signal, rv, iv, spot, cost_vol_points=0.0)
        assert np.mean(pnl) > 0

    def test_transaction_costs_reduce_pnl(self):
        """Adding cost should reduce average P&L."""
        n = 100
        signal = np.ones(n)
        iv = np.full(n, 0.20)
        rv = np.full(n, 0.0001)
        spot = np.full(n, 100.0)

        pnl_no_cost = delta_hedged_straddle_pnl(signal, rv, iv, spot, cost_vol_points=0.0)
        pnl_with_cost = delta_hedged_straddle_pnl(signal, rv, iv, spot, cost_vol_points=0.5)
        assert np.mean(pnl_no_cost) > np.mean(pnl_with_cost)

    def test_output_finite(self):
        """P&L should always be finite."""
        rng = np.random.default_rng(42)
        n = 200
        signal = rng.choice([-1, 0, 1], n)
        iv = rng.uniform(0.10, 0.40, n)
        rv = rng.uniform(0.00005, 0.001, n)
        spot = rng.uniform(50, 500, n)
        pnl = delta_hedged_straddle_pnl(signal, rv, iv, spot)
        assert np.all(np.isfinite(pnl))


class TestDeltaHedgedSharpe:
    """Tests for delta_hedged_sharpe (end-to-end)."""

    def test_better_forecast_higher_sharpe(self):
        """A model that correctly predicts RV should get higher DH Sharpe."""
        rng = np.random.default_rng(42)
        n = 500
        # Simulate daily RV that varies between low and high vol regimes
        true_daily_var = 0.00015 + 0.00005 * np.sin(np.arange(n) * 2 * np.pi / 252)
        true_log_rv = np.log(true_daily_var)

        # IV = constant at 20% -> daily implied var = 0.04/252 ≈ 0.000159
        iv = np.full(n, 0.20)
        spot = np.full(n, 100.0)

        # Perfect forecast
        dh_good = delta_hedged_sharpe(true_log_rv, iv, true_daily_var, spot)

        # Very noisy forecast
        noisy_log_rv = true_log_rv + rng.normal(0, 2.0, n)
        dh_noisy = delta_hedged_sharpe(noisy_log_rv, iv, true_daily_var, spot)

        # Perfect forecast should exploit the gap better
        assert dh_good["dh_sharpe"] > dh_noisy["dh_sharpe"]

    def test_returns_all_keys(self):
        """Output dict should have all expected keys."""
        n = 200
        log_rv = np.full(n, -8.5)
        iv = np.full(n, 0.20)
        rv = np.full(n, 0.0002)
        spot = np.full(n, 100.0)

        result = delta_hedged_sharpe(log_rv, iv, rv, spot)
        assert "dh_sharpe" in result
        assert "dh_pnl" in result
        assert "dh_max_dd" in result
        assert "dh_hit_rate" in result

    def test_hit_rate_between_zero_and_one(self):
        """Hit rate should be in [0, 1]."""
        rng = np.random.default_rng(7)
        n = 300
        log_rv = rng.normal(-8.5, 0.5, n)
        iv = rng.uniform(0.15, 0.25, n)
        rv = np.exp(log_rv)
        spot = rng.uniform(90, 110, n)

        result = delta_hedged_sharpe(log_rv, iv, rv, spot)
        assert 0.0 <= result["dh_hit_rate"] <= 1.0

    def test_finite_outputs(self):
        """All metrics should be finite."""
        rng = np.random.default_rng(99)
        n = 200
        log_rv = rng.normal(-9.0, 1.0, n)
        iv = rng.uniform(0.10, 0.30, n)
        rv = np.exp(log_rv)
        spot = rng.uniform(80, 120, n)

        result = delta_hedged_sharpe(log_rv, iv, rv, spot)
        for k, v in result.items():
            assert np.isfinite(v), f"{k} is not finite: {v}"


class TestIVTimeAlignment:
    """Tests that IV is correctly lagged (no look-ahead) in signal generation.

    The tournament pipeline applies .shift(1) to IV before passing it to
    delta_hedged_sharpe. These tests verify that:
    1. Using same-day IV (look-ahead) produces DIFFERENT results than lagged IV
    2. The signal at time t only depends on information available at t-1
    3. A jump in IV on day t should NOT affect the signal on day t
    """

    def test_iv_shift_changes_signal(self):
        """Shifted vs unshifted IV must produce different signals.

        Construct data where IV has a regime change (low -> high).
        With shift(1), the signal on the transition day uses YESTERDAY's low IV.
        Without shift, it would use TODAY's high IV.
        """
        n = 100
        # IV jumps from 15% to 40% on day 50
        iv_unshifted = np.where(np.arange(n) < 50, 0.15, 0.40)
        iv_shifted = np.roll(iv_unshifted, 1)
        iv_shifted[0] = iv_unshifted[0]  # fill first day

        # Forecast = constant 20% vol -> annualized forecast
        forecast_ann_vol = np.full(n, 0.20)

        # Signal with shifted IV (correct -- no look-ahead)
        signal_correct = iv_rv_gap_signal(iv_shifted, forecast_ann_vol, threshold=0.0)
        # Signal with unshifted IV (wrong -- look-ahead)
        signal_lookahead = iv_rv_gap_signal(iv_unshifted, forecast_ann_vol, threshold=0.0)

        # On day 50: unshifted IV=0.40 > forecast=0.20 -> signal=+1 (sell vol)
        #            shifted IV=0.15 < forecast=0.20 -> signal=-1 (buy vol)
        assert signal_lookahead[50] == 1.0, "Look-ahead: +1 (IV=40% > forecast)"
        assert signal_correct[50] == -1.0, (
            "Correct signal should be -1 (IV_yesterday=15% < forecast=20%)"
        )

        # Overall: the signals should differ on at least the transition day
        assert not np.array_equal(signal_correct, signal_lookahead)

    def test_iv_jump_not_exploitable_same_day(self):
        """A sudden IV spike on day t must not generate profit on day t.

        If signal uses IV[t] (look-ahead), it can exploit the spike.
        If signal uses IV[t-1] (correct), it was decided BEFORE the spike.
        """
        n = 200

        # Stable IV at 18%, with a spike to 50% on day 100
        iv_raw = np.full(n, 0.18)
        iv_raw[100] = 0.50  # sudden spike

        # Apply shift (correct behavior)
        iv_shifted = np.roll(iv_raw, 1)
        iv_shifted[0] = iv_raw[0]

        # RV is constant (forecast = 15%)
        forecast = np.full(n, 0.15)
        rv_daily = np.full(n, 0.15**2 / 252)  # constant realized vol
        spot = np.full(n, 100.0)

        # With correct shift: signal on day 100 uses IV[99]=0.18
        signal_correct = iv_rv_gap_signal(iv_shifted, forecast, threshold=0.0)
        # Signal on day 100: IV_shifted[100] = IV_raw[99] = 0.18 > forecast=0.15 -> +1
        assert signal_correct[100] == 1.0

        # With look-ahead: signal on day 100 uses IV[100]=0.50
        signal_wrong = iv_rv_gap_signal(iv_raw, forecast, threshold=0.0)
        # Both give +1 here (IV > forecast in both cases), but PnL differs because
        # the gamma formula uses IV for pricing:
        pnl_correct = delta_hedged_straddle_pnl(signal_correct, rv_daily, iv_shifted, spot)
        pnl_wrong = delta_hedged_straddle_pnl(signal_wrong, rv_daily, iv_raw, spot)
        # The look-ahead version uses the spiked IV=50% in the gamma formula on day 100,
        # which produces a larger PnL magnitude (because gamma uses IV in denominator
        # and the (RV - IV^2/252) gap is much larger)
        assert abs(pnl_wrong[100]) > abs(pnl_correct[100]), (
            "Look-ahead should produce larger PnL on spike day (exploiting future IV info)"
        )

    def test_signal_deterministic_given_lagged_inputs(self):
        """Signal at t depends only on IV[t-1] and prediction[t], not IV[t]."""
        n = 50
        rng = np.random.default_rng(456)

        iv_series = rng.uniform(0.12, 0.25, n)
        forecast = rng.uniform(0.10, 0.22, n)

        # Compute signal with shift (as tournament does)
        iv_shifted = np.roll(iv_series, 1)
        iv_shifted[0] = iv_series[0]
        signal = iv_rv_gap_signal(iv_shifted, forecast, threshold=0.0)

        # Verify: changing IV[t] does NOT change signal[t]
        iv_modified = iv_series.copy()
        iv_modified[25] = 0.99  # extreme change on day 25
        iv_modified_shifted = np.roll(iv_modified, 1)
        iv_modified_shifted[0] = iv_modified[0]
        signal_after = iv_rv_gap_signal(iv_modified_shifted, forecast, threshold=0.0)

        # Signal on day 25 should be unchanged (it uses IV[24], not IV[25])
        assert signal[25] == signal_after[25], (
            "Signal at t must not depend on IV[t] -- only IV[t-1]"
        )
        # But signal on day 26 SHOULD change (it uses the modified IV[25])
        # iv_modified_shifted[26] = iv_modified[25] = 0.99 (huge, > any forecast)
        assert signal_after[26] == 1.0, "Signal at t+1 should reflect the IV change on day t"


class TestIVTenorForHorizon:
    """Tests for iv_tenor_for_horizon helper."""

    def test_h1_uses_0dte_tenor(self):
        """h=1 should use 0DTE variance swap strike (correct measure for GSVIVS)."""
        from volforecast.evaluation.economic_value import iv_tenor_for_horizon

        col, days = iv_tenor_for_horizon(1)
        assert col == "iv_vs_0dte"
        assert days == 1

    def test_h5_uses_1w_tenor(self):
        """h=5 should use 1w ATM IV (natural match: 5 trading days)."""
        from volforecast.evaluation.economic_value import iv_tenor_for_horizon

        col, days = iv_tenor_for_horizon(5)
        assert col == "iv_1w_atm"
        assert days == 5

    def test_h22_uses_1m_tenor(self):
        """h=22 should use 1m ATM IV (natural match: ~22 trading days)."""
        from volforecast.evaluation.economic_value import iv_tenor_for_horizon

        col, days = iv_tenor_for_horizon(22)
        assert col == "iv_1m_atm"
        assert days == 22

    def test_h10_uses_2w_interpolation(self):
        """h=10 (between 1w and 1m) should use 1m tenor."""
        from volforecast.evaluation.economic_value import iv_tenor_for_horizon

        col, days = iv_tenor_for_horizon(10)
        assert col == "iv_1m_atm"
        assert days == 22

    def test_shorter_tenor_increases_gamma(self):
        """Weekly straddle should have ~2.4x higher gamma than monthly.

        This verifies the economic rationale: if model forecasts 1-day RV
        and you trade a weekly straddle, you capture more gamma P&L per unit
        of mispricing than with a monthly straddle.
        """
        n = 100
        signal = np.ones(n)
        iv = np.full(n, 0.20)
        rv = np.full(n, 0.0001)  # realized < implied -> profit for short vol
        spot = np.full(n, 100.0)

        pnl_weekly = delta_hedged_straddle_pnl(
            signal, rv, iv, spot, tenor_days=5, cost_vol_points=0.0
        )
        pnl_monthly = delta_hedged_straddle_pnl(
            signal, rv, iv, spot, tenor_days=22, cost_vol_points=0.0
        )
        # Weekly gamma = 2/(S*IV*sqrt(5/252)), Monthly = 2/(S*IV*sqrt(22/252))
        # Ratio: sqrt(22)/sqrt(5) ≈ 2.097
        ratio = np.mean(np.abs(pnl_weekly)) / np.mean(np.abs(pnl_monthly))
        expected_ratio = np.sqrt(22.0 / 5.0)
        assert ratio == pytest.approx(expected_ratio, rel=0.01)
