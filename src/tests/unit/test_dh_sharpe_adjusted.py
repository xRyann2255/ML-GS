"""Tests for DH Sharpe adjusted computation and pooled metrics.

Verifies:
1. Realistic mode reports dh_sharpe_adjusted as the primary Sharpe
2. Metrics are computed from pooled PnL stream (not averaged per-symbol)
3. Naive baselines in realistic mode also use adjusted Sharpe
4. Pooled Sharpe = compute_sharpe(concatenated daily PnL)
5. AnnRet and Sharpe have consistent signs
"""

from __future__ import annotations

import numpy as np
import pytest

from volforecast.evaluation.economic_value import (
    _compute_naive_pnl,
    compute_sharpe,
    naive_dh_baselines,
)


@pytest.fixture
def two_symbol_data():
    """Two symbols of realistic market data for pooling tests."""
    rng = np.random.default_rng(456)
    n_per_sym = 500

    data = {}
    for sym, start_price in [("A", 100.0), ("B", 200.0)]:
        log_returns = rng.normal(0.0003, 0.015, n_per_sym)
        spot = start_price * np.exp(np.cumsum(log_returns))
        iv = 0.20 + 0.03 * np.sin(np.arange(n_per_sym) * 2 * np.pi / 252)
        iv += rng.normal(0, 0.005, n_per_sym)
        iv = np.clip(iv, 0.05, 0.60)
        rv = log_returns**2
        data[sym] = {"realized_var": rv, "implied_vol": iv, "spot_prices": spot}

    return data


class TestPooledMetrics:
    """Tests for pooled PnL computation (not per-symbol averaging)."""

    def test_pooled_sharpe_differs_from_averaged_sharpe(self, two_symbol_data):
        """Pooled Sharpe (from concatenated PnL) != mean of per-symbol Sharpes."""
        # Compute per-symbol
        sharpes = []
        all_pnl = []
        for sym_data in two_symbol_data.values():
            pnl, _ = _compute_naive_pnl(
                np.ones(len(sym_data["realized_var"])),
                sym_data["realized_var"],
                sym_data["implied_vol"],
                sym_data["spot_prices"],
                dh_mode="simple",
            )
            sharpes.append(compute_sharpe(pnl))
            all_pnl.append(pnl)

        avg_sharpe = np.mean(sharpes)
        pooled_pnl = np.concatenate(all_pnl)
        pooled_sharpe = compute_sharpe(pooled_pnl)

        # They shouldn't be identical (different aggregation methods)
        # The pooled approach is more statistically valid
        assert pooled_sharpe != pytest.approx(avg_sharpe, abs=0.01)

    def test_pooled_annret_and_sharpe_sign_consistent(self, two_symbol_data):
        """Pooled AnnRet and Sharpe must have the same sign (no paradox)."""
        all_pnl = []
        for sym_data in two_symbol_data.values():
            pnl, _ = _compute_naive_pnl(
                np.ones(len(sym_data["realized_var"])),
                sym_data["realized_var"],
                sym_data["implied_vol"],
                sym_data["spot_prices"],
                dh_mode="simple",
            )
            all_pnl.append(pnl)

        pooled_pnl = np.concatenate(all_pnl)
        sharpe = compute_sharpe(pooled_pnl)
        ann_ret = float(np.mean(pooled_pnl) * 252 * 100)

        # Signs must match (both positive, both negative, or both zero)
        if abs(sharpe) > 0.01 and abs(ann_ret) > 0.1:
            assert np.sign(sharpe) == np.sign(ann_ret)


class TestAdjustedSharpe:
    """Tests for hedge-error-adjusted Sharpe in realistic mode."""

    def test_adjusted_sharpe_lower_than_raw(self):
        """dh_sharpe_adjusted must be <= dh_sharpe (inflated denominator)."""
        from volforecast.evaluation.realistic_straddle import realistic_straddle_pnl

        rng = np.random.default_rng(789)
        n = 500
        log_returns = rng.normal(0.0003, 0.015, n)
        spot = 100.0 * np.exp(np.cumsum(log_returns))
        iv = np.full(n, 0.20)
        rv = log_returns**2
        signal = np.ones(n)

        delta_spot = np.zeros(n)
        delta_spot[1:] = np.diff(spot)
        delta_iv = np.zeros(n)

        result = realistic_straddle_pnl(
            signal=signal,
            realized_var=rv,
            implied_vol=iv,
            spot_prices=spot,
            delta_spot=delta_spot,
            delta_iv=delta_iv,
        )

        pnl = result["pnl_net"]
        valid = ~np.isnan(pnl)
        pnl_clean = np.where(valid, pnl, 0.0)

        raw_sharpe = compute_sharpe(pnl_clean)

        # Adjusted: inflate std with hedge error variance
        observed_var = np.var(pnl_clean, ddof=1)
        mean_he_var = np.mean(result["hedge_error_var"])
        total_std = np.sqrt(observed_var + mean_he_var)
        mean_pnl = np.mean(pnl_clean)
        adj_sharpe = float(mean_pnl / total_std * np.sqrt(252.0)) if total_std > 1e-12 else 0.0

        # Adjusted must be closer to zero than raw (larger denominator)
        assert abs(adj_sharpe) <= abs(raw_sharpe) + 1e-6
        # And materially different (hedge error adds something)
        assert abs(adj_sharpe) < abs(raw_sharpe) - 1e-4

    def test_naive_baselines_realistic_uses_adjusted_sharpe(self):
        """naive_dh_baselines with dh_mode='realistic' should use adjusted Sharpe.

        Verify by comparing the reported Sharpe against a manually computed
        raw Sharpe from the same PnL — the reported one should be closer to zero.
        """
        rng = np.random.default_rng(101)
        n = 500
        log_returns = rng.normal(0.0003, 0.015, n)
        spot = 100.0 * np.exp(np.cumsum(log_returns))
        iv = 0.20 + rng.normal(0, 0.005, n)
        iv = np.clip(iv, 0.05, 0.60)
        rv = log_returns**2

        result = naive_dh_baselines(
            realized_var=rv,
            implied_vol=iv,
            spot_prices=spot,
            dh_mode="realistic",
        )

        # Get the raw PnL to compute raw Sharpe (without adjustment)
        pnl_clean, he_var = _compute_naive_pnl(
            np.ones(n),
            rv,
            iv,
            spot,
            dh_mode="realistic",
        )
        raw_sharpe = compute_sharpe(pnl_clean)

        # The reported Sharpe uses adjusted denominator, so should be
        # closer to zero than raw Sharpe
        reported_sharpe = result["always_long"]["dh_sharpe"]
        assert abs(reported_sharpe) < abs(raw_sharpe)
        # And hedge_error_var should be non-None (realistic mode provides it)
        assert he_var is not None


class TestBaselineSignalFeeding:
    """Tests that baselines feed correct signals to realistic engine."""

    def test_always_long_feeds_signal_plus_one(self):
        """always_long should pass signal=+1 (sell vol) to the engine."""
        rng = np.random.default_rng(202)
        n = 100
        log_returns = rng.normal(0.0003, 0.015, n)
        spot = 100.0 * np.exp(np.cumsum(log_returns))
        iv = np.full(n, 0.20)
        rv = log_returns**2

        # Manually compute with signal=+1
        from volforecast.evaluation.realistic_straddle import realistic_straddle_pnl

        delta_spot = np.zeros(n)
        delta_spot[1:] = np.diff(spot)
        delta_iv = np.zeros(n)

        manual_result = realistic_straddle_pnl(
            signal=np.ones(n),
            realized_var=rv,
            implied_vol=iv,
            spot_prices=spot,
            delta_spot=delta_spot,
            delta_iv=delta_iv,
        )

        # Compare with what naive_dh_baselines produces
        baseline_pnl, _ = _compute_naive_pnl(np.ones(n), rv, iv, spot, dh_mode="realistic")

        # Should be identical (same signal, same engine)
        np.testing.assert_allclose(baseline_pnl, manual_result["pnl_net"], atol=1e-12)

    def test_always_short_feeds_signal_minus_one(self):
        """always_short should pass signal=-1 (buy vol) to the engine."""
        rng = np.random.default_rng(303)
        n = 100
        log_returns = rng.normal(0.0003, 0.015, n)
        spot = 100.0 * np.exp(np.cumsum(log_returns))
        iv = np.full(n, 0.20)
        rv = log_returns**2

        from volforecast.evaluation.realistic_straddle import realistic_straddle_pnl

        delta_spot = np.zeros(n)
        delta_spot[1:] = np.diff(spot)
        delta_iv = np.zeros(n)

        manual_result = realistic_straddle_pnl(
            signal=np.full(n, -1.0),
            realized_var=rv,
            implied_vol=iv,
            spot_prices=spot,
            delta_spot=delta_spot,
            delta_iv=delta_iv,
        )

        baseline_pnl, _ = _compute_naive_pnl(np.full(n, -1.0), rv, iv, spot, dh_mode="realistic")

        np.testing.assert_allclose(baseline_pnl, manual_result["pnl_net"], atol=1e-12)
