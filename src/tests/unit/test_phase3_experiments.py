"""Tests for Phase 3: Evaluation rigor experiments.

Tests the experiment runner functions:
- Cost-band Sharpe verification (Step 16)
- Statistical-to-economic link regression (Step 17)
- Sharpe aggregation + deflation reporting (Step 18)
- Hedging-error floor from simulator (Step 19)
"""

from __future__ import annotations

import numpy as np


class TestCostBandExperiment:
    """Tests for Step 16: Cost-band Sharpe experiment."""

    def test_returns_three_bands(self):
        """Returns Sharpe at timing_aware, effective, and quoted levels."""
        from volforecast.evaluation.phase3_experiments import run_cost_band_experiment

        rng = np.random.default_rng(42)
        n = 500
        pnl_net = rng.normal(0.001, 0.01, n)
        T_rem = np.full(n, 20.0)
        gamma = np.full(n, 0.05)
        spot = np.full(n, 100.0)
        iv = np.full(n, 0.20)

        result = run_cost_band_experiment(pnl_net, gamma, spot, iv, T_rem)

        assert "timing_aware" in result
        assert "effective" in result
        assert "quoted" in result

    def test_monotonic_sharpe_decrease(self):
        """Sharpe decreases as cost band widens: timing > effective > quoted."""
        from volforecast.evaluation.phase3_experiments import run_cost_band_experiment

        rng = np.random.default_rng(42)
        n = 500
        # Strong positive edge so all bands stay positive
        pnl_net = rng.normal(0.005, 0.01, n)
        T_rem = np.full(n, 20.0)
        gamma = np.full(n, 0.05)
        spot = np.full(n, 100.0)
        iv = np.full(n, 0.20)

        result = run_cost_band_experiment(pnl_net, gamma, spot, iv, T_rem)

        assert result["timing_aware"] >= result["effective"]
        assert result["effective"] >= result["quoted"]

    def test_pass_criterion_effective(self):
        """Reports whether strategy passes at effective level (SR > 0.5)."""
        from volforecast.evaluation.phase3_experiments import run_cost_band_experiment

        rng = np.random.default_rng(42)
        n = 500
        pnl_net = rng.normal(0.005, 0.01, n)
        T_rem = np.full(n, 20.0)
        gamma = np.full(n, 0.05)
        spot = np.full(n, 100.0)
        iv = np.full(n, 0.20)

        result = run_cost_band_experiment(pnl_net, gamma, spot, iv, T_rem)

        assert "pass_effective" in result
        assert isinstance(result["pass_effective"], bool)


class TestStatisticalEconomicLink:
    """Tests for Step 17: Statistical-to-economic link regression."""

    def test_returns_regression_coefficients(self):
        """Returns alpha, beta_gap, beta_error coefficients."""
        from volforecast.evaluation.phase3_experiments import (
            statistical_economic_link,
        )

        rng = np.random.default_rng(42)
        n = 500
        pnl = rng.normal(0.001, 0.01, n)
        realized_var = np.abs(rng.normal(0.0002, 0.0001, n))
        iv = np.full(n, 0.20)
        forecast_var = realized_var + rng.normal(0, 0.00005, n)

        result = statistical_economic_link(pnl, realized_var, iv, forecast_var)

        assert "alpha" in result
        assert "beta_gap" in result
        assert "beta_error" in result

    def test_positive_beta_gap_when_edge_exists(self):
        """When P&L is driven by the RV-IV gap, beta_gap should be positive."""
        from volforecast.evaluation.phase3_experiments import (
            statistical_economic_link,
        )

        n = 1000
        rng = np.random.default_rng(42)
        realized_var = np.abs(rng.normal(0.0002, 0.00005, n))
        iv = np.full(n, 0.15)
        iv_var_daily = iv**2 / 252.0
        gap = realized_var - iv_var_daily
        # P&L = positive_coefficient * gap + noise
        pnl = 0.5 * gap + rng.normal(0, 0.0001, n)
        forecast_var = realized_var + rng.normal(0, 0.00002, n)

        result = statistical_economic_link(pnl, realized_var, iv, forecast_var)

        assert result["beta_gap"] > 0

    def test_returns_t_statistics(self):
        """Returns t-stats for each coefficient."""
        from volforecast.evaluation.phase3_experiments import (
            statistical_economic_link,
        )

        rng = np.random.default_rng(42)
        n = 500
        pnl = rng.normal(0.001, 0.01, n)
        realized_var = np.abs(rng.normal(0.0002, 0.0001, n))
        iv = np.full(n, 0.20)
        forecast_var = realized_var + rng.normal(0, 0.00005, n)

        result = statistical_economic_link(pnl, realized_var, iv, forecast_var)

        assert "t_gap" in result
        assert "t_error" in result


class TestSharpeAggregation:
    """Tests for Step 18: Pooled + per-symbol Sharpe with DSR."""

    def test_pooled_sharpe(self):
        """Pooled Sharpe concatenates all symbol P&L."""
        from volforecast.evaluation.phase3_experiments import (
            compute_sharpe_aggregation,
        )

        rng = np.random.default_rng(42)
        pnl_by_symbol = {
            "AAPL": rng.normal(0.001, 0.01, 250),
            "MSFT": rng.normal(0.002, 0.01, 250),
            "GOOGL": rng.normal(0.0005, 0.01, 250),
        }

        result = compute_sharpe_aggregation(pnl_by_symbol, N_trials=10)

        assert "pooled_sharpe" in result
        assert "per_symbol_sharpes" in result
        assert "mean_per_symbol_sharpe" in result

    def test_per_symbol_sharpes(self):
        """Per-symbol Sharpe computed for each symbol."""
        from volforecast.evaluation.phase3_experiments import (
            compute_sharpe_aggregation,
        )

        rng = np.random.default_rng(42)
        pnl_by_symbol = {
            "AAPL": rng.normal(0.001, 0.01, 250),
            "MSFT": rng.normal(0.002, 0.01, 250),
        }

        result = compute_sharpe_aggregation(pnl_by_symbol, N_trials=10)

        assert "AAPL" in result["per_symbol_sharpes"]
        assert "MSFT" in result["per_symbol_sharpes"]

    def test_dsr_reported(self):
        """DSR is reported for pooled Sharpe."""
        from volforecast.evaluation.phase3_experiments import (
            compute_sharpe_aggregation,
        )

        rng = np.random.default_rng(42)
        pnl_by_symbol = {
            "SPY": rng.normal(0.001, 0.01, 500),
        }

        result = compute_sharpe_aggregation(pnl_by_symbol, N_trials=10)

        assert "dsr" in result
        assert 0.0 <= result["dsr"] <= 1.0

    def test_bootstrap_ci_reported(self):
        """Block-bootstrap CI is reported."""
        from volforecast.evaluation.phase3_experiments import (
            compute_sharpe_aggregation,
        )

        rng = np.random.default_rng(42)
        pnl_by_symbol = {
            "SPY": rng.normal(0.001, 0.01, 500),
        }

        result = compute_sharpe_aggregation(pnl_by_symbol, N_trials=10, n_bootstrap=200)

        assert "bootstrap_ci" in result
        ci_low, ci_high = result["bootstrap_ci"]
        assert ci_low < ci_high


class TestHedgingErrorFloor:
    """Tests for Step 19: Hedging-error floor experiment."""

    def test_returns_a_b_and_jump_flag(self):
        """Returns a, b coefficients and whether jump floor exists."""
        from volforecast.evaluation.phase3_experiments import (
            run_hedging_error_floor_experiment,
        )

        # Synthetic: variance decreases with N (pure diffusion)
        n_values = [1, 2, 4, 6, 13, 26]
        variances = {n: 10.0 / n + 0.01 for n in n_values}

        result = run_hedging_error_floor_experiment(variances)

        assert "a" in result
        assert "b" in result
        assert "jump_floor_detected" in result

    def test_no_jump_floor_for_pure_diffusion(self):
        """Pure 1/N scaling → no jump floor detected."""
        from volforecast.evaluation.phase3_experiments import (
            run_hedging_error_floor_experiment,
        )

        n_values = [1, 2, 4, 6, 13, 26]
        variances = {n: 5.0 / n for n in n_values}

        result = run_hedging_error_floor_experiment(variances)
        assert result["jump_floor_detected"] is False

    def test_jump_floor_detected_with_constant_term(self):
        """Var = a/N + b with b>0 → jump floor detected."""
        from volforecast.evaluation.phase3_experiments import (
            run_hedging_error_floor_experiment,
        )

        n_values = [1, 2, 4, 6, 13, 26]
        variances = {n: 5.0 / n + 2.0 for n in n_values}

        result = run_hedging_error_floor_experiment(variances)
        assert result["jump_floor_detected"] is True

    def test_kappa_sensitivity_reported(self):
        """Reports DSR stability across kappa values."""
        from volforecast.evaluation.phase3_experiments import (
            run_kappa_sensitivity,
        )

        rng = np.random.default_rng(42)
        n = 500
        pnl = rng.normal(0.001, 0.01, n)
        gamma = np.full(n, 0.05)
        spot = np.full(n, 100.0)
        iv = np.full(n, 0.20)
        signal = np.ones(n)

        result = run_kappa_sensitivity(pnl, gamma, spot, iv, signal, N_trials=10)

        assert "kappa_3" in result
        assert "kappa_4" in result
        assert "kappa_6" in result
        # Each should have sharpe_adjusted and dsr
        assert "sharpe_adjusted" in result["kappa_4"]
        assert "dsr" in result["kappa_4"]


class TestFullPhase3Report:
    """Integration test for Phase 3 report generation."""

    def test_generate_phase3_report_returns_dict(self):
        """Phase 3 report assembles all experiments into a summary dict."""
        from volforecast.evaluation.phase3_experiments import (
            generate_phase3_report,
        )

        rng = np.random.default_rng(42)
        n = 300
        pnl_by_symbol = {
            "SPY": rng.normal(0.001, 0.01, n),
            "AAPL": rng.normal(0.0008, 0.01, n),
        }
        realized_var = np.abs(rng.normal(0.0002, 0.0001, n))
        iv = np.full(n, 0.20)
        forecast_var = realized_var + rng.normal(0, 0.00003, n)
        gamma = np.full(n, 0.05)
        spot = np.full(n, 100.0)
        T_rem = np.full(n, 20.0)
        signal = np.ones(n)

        result = generate_phase3_report(
            pnl_by_symbol=pnl_by_symbol,
            realized_var=realized_var,
            iv=iv,
            forecast_var=forecast_var,
            gamma=gamma,
            spot=spot,
            T_rem=T_rem,
            signal=signal,
            N_trials=10,
            n_bootstrap=100,
        )

        assert "cost_band" in result
        assert "stat_econ_link" in result
        assert "sharpe_aggregation" in result
        assert "kappa_sensitivity" in result
