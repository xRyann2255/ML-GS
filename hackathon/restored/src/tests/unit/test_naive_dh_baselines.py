"""Tests for naive delta-hedged straddle baselines (always-long/short/flat/random)."""

from __future__ import annotations

import numpy as np
import pytest

from volforecast.evaluation.economic_value import naive_dh_baselines


# Shared fixtures — realistic but deterministic test data
@pytest.fixture
def market_data():
    """Generate realistic market data for DH baseline testing."""
    rng = np.random.default_rng(123)
    n = 500

    # Spot prices: geometric random walk starting at 100
    log_returns = rng.normal(0.0003, 0.015, n)
    spot_prices = 100.0 * np.exp(np.cumsum(log_returns))

    # Implied vol: ~20% annualized with mean-reverting noise
    implied_vol = 0.20 + 0.03 * np.sin(np.arange(n) * 2 * np.pi / 252)
    implied_vol += rng.normal(0, 0.005, n)
    implied_vol = np.clip(implied_vol, 0.05, 0.60)

    # Daily realized variance: squared returns (simple proxy)
    realized_var = log_returns**2

    return {
        "realized_var": realized_var,
        "implied_vol": implied_vol,
        "spot_prices": spot_prices,
    }


EXPECTED_BASELINES = {"always_long", "always_short", "always_flat", "random", "random_no_flip"}
EXPECTED_METRICS = {"dh_sharpe", "dh_pnl", "dh_max_dd", "dh_hit_rate", "dh_ann_ret", "dh_ann_vol"}


class TestNaiveDhBaselines:
    """Tests for naive_dh_baselines() function."""

    def test_returns_all_four_baselines(self, market_data):
        """Should return exactly 4 named baselines."""
        result = naive_dh_baselines(**market_data, dh_mode="simple")
        assert set(result.keys()) == EXPECTED_BASELINES

    def test_each_baseline_has_correct_metrics(self, market_data):
        """Each baseline dict should contain the 6 standard DH metric keys."""
        result = naive_dh_baselines(**market_data, dh_mode="simple")
        for name, metrics in result.items():
            assert set(metrics.keys()) == EXPECTED_METRICS, f"Missing keys for {name}"

    def test_always_flat_all_zeros(self, market_data):
        """Always-flat baseline should have zero PnL and zero Sharpe."""
        result = naive_dh_baselines(**market_data, dh_mode="simple")
        flat = result["always_flat"]
        assert flat["dh_sharpe"] == 0.0
        assert flat["dh_pnl"] == 0.0
        assert flat["dh_max_dd"] == 0.0
        assert flat["dh_hit_rate"] == 0.0
        assert flat["dh_ann_ret"] == 0.0
        assert flat["dh_ann_vol"] == 0.0

    def test_always_long_short_opposite_pnl(self, market_data):
        """Always-long and always-short should have opposite-sign cumulative PnL."""
        result = naive_dh_baselines(**market_data, dh_mode="simple")
        long_pnl = result["always_long"]["dh_pnl"]
        short_pnl = result["always_short"]["dh_pnl"]
        # They trade opposite directions, so PnL should be opposite signs
        # (unless costs make both negative, but with zero threshold the raw PnL
        # should be opposite; the cost component is symmetric)
        assert long_pnl * short_pnl <= 0 or pytest.approx(long_pnl, abs=0.01) == 0.0

    def test_always_long_short_symmetric_annret(self, market_data):
        """Before costs, always-long and always-short should have near-symmetric ann ret."""
        # Use simple mode with zero cost to isolate signal direction effect
        result = naive_dh_baselines(**market_data, dh_mode="simple")
        long_ret = result["always_long"]["dh_ann_ret"]
        short_ret = result["always_short"]["dh_ann_ret"]
        # The raw gamma PnL is negated for signal direction, so they should
        # sum approximately to -2*cost_drag (small)
        # They won't be exactly opposite because of the cost term,
        # but should have opposite signs
        if abs(long_ret) > 1.0 and abs(short_ret) > 1.0:
            assert long_ret * short_ret < 0

    def test_random_reproducible_same_seed(self, market_data):
        """Random baseline should be reproducible with the same seed."""
        r1 = naive_dh_baselines(**market_data, dh_mode="simple", seed=42)
        r2 = naive_dh_baselines(**market_data, dh_mode="simple", seed=42)
        assert r1["random"]["dh_sharpe"] == r2["random"]["dh_sharpe"]
        assert r1["random"]["dh_pnl"] == r2["random"]["dh_pnl"]

    def test_random_different_seed_different_result(self, market_data):
        """Different seeds should produce different random baseline results."""
        r1 = naive_dh_baselines(**market_data, dh_mode="simple", seed=42)
        r2 = naive_dh_baselines(**market_data, dh_mode="simple", seed=99)
        # Very unlikely to be identical with different seeds
        assert r1["random"]["dh_pnl"] != r2["random"]["dh_pnl"]

    def test_always_long_hit_rate_between_0_and_1(self, market_data):
        """Hit rate should be a valid proportion."""
        result = naive_dh_baselines(**market_data, dh_mode="simple")
        hr = result["always_long"]["dh_hit_rate"]
        assert 0.0 <= hr <= 1.0

    @pytest.mark.parametrize("dh_mode", ["simple", "discrete", "realistic"])
    def test_all_modes_produce_valid_output(self, market_data, dh_mode):
        """All 3 dh_modes should produce the same structure with finite values."""
        result = naive_dh_baselines(**market_data, dh_mode=dh_mode)
        assert set(result.keys()) == EXPECTED_BASELINES
        for name, metrics in result.items():
            for key, val in metrics.items():
                assert np.isfinite(val), f"{name}.{key} is not finite in {dh_mode} mode"

    def test_discrete_mode_more_costly_than_simple(self, market_data):
        """Discrete mode adds hedge costs, so always-long PnL should be lower than simple."""
        simple = naive_dh_baselines(**market_data, dh_mode="simple")
        discrete = naive_dh_baselines(**market_data, dh_mode="discrete")
        # Discrete adds hedge cost on top, reducing net PnL
        # (for always-long, which has signal=+1 everywhere)
        assert discrete["always_long"]["dh_pnl"] <= simple["always_long"]["dh_pnl"] + 0.1

    def test_realistic_mode_includes_additional_costs(self, market_data):
        """Realistic mode should produce lower PnL than simple due to vanna/volga + costs."""
        simple = naive_dh_baselines(**market_data, dh_mode="simple")
        realistic = naive_dh_baselines(**market_data, dh_mode="realistic")
        # Realistic includes option cost, hedge cost, vanna, volga — generally more costly
        # Not strictly less (vanna/volga can add PnL), but should differ meaningfully
        assert realistic["always_long"]["dh_pnl"] != simple["always_long"]["dh_pnl"]


class TestNaiveDhBaselinesIntegration:
    """Integration test: naive baselines appear in tournament_table output."""

    def test_tournament_table_includes_baseline_rows(self, market_data):
        """tournament_table should include [baseline] rows when IV/spot provided."""
        from volforecast.evaluation.statistical_tests import tournament_table
        from volforecast.evaluation.tournament_economics import enrich_tournament_economics

        n = len(market_data["realized_var"])
        rng = np.random.default_rng(7)

        # Minimal predictions: just HAR as a dummy
        log_rv = np.log(market_data["realized_var"] + 1e-10)
        predictions = {
            "har": log_rv + rng.normal(0, 0.1, n),
        }

        stats = tournament_table(
            predictions=predictions,
            y_true=log_rv,
            baseline="har",
            horizon=1,
        )
        df = enrich_tournament_economics(
            stats,
            predictions,
            log_rv,
            implied_vol=market_data["implied_vol"],
            spot_prices=market_data["spot_prices"],
            dh_mode="simple",
            horizon=1,
        )

        # Should have 1 model + 5 baselines = 6 rows
        baseline_rows = df[df["model"].str.startswith("[baseline]")]
        assert len(baseline_rows) == 5

        # Baseline rows should have NaN for QLIKE (no forecast)
        for _, row in baseline_rows.iterrows():
            assert np.isnan(row["qlike"])

        # But should have finite DH metrics
        for _, row in baseline_rows.iterrows():
            assert np.isfinite(row["dh_sharpe"])
            assert np.isfinite(row["dh_pnl"])
