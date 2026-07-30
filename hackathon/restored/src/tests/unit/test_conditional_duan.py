"""Tests for conditional (heteroscedastic) Duan correction.

Validates:
1. Basic formula: log_preds + conditional_variance / 2
2. Zero variance degenerates to identity (no correction)
3. Extreme variance is clipped to max_var
4. Array shapes are preserved
5. Conditional correction outperforms global correction on heteroscedastic data
6. Negative variance values are clipped to zero
"""

from __future__ import annotations

import numpy as np
import pytest

from volforecast.evaluation.metrics import conditional_duan_correction, qlike


class TestConditionalDuanBasicMath:
    """Verify the formula: corrected = log_preds + clip(cond_var, 0, max_var) / 2."""

    def test_basic_correction(self):
        """Correction adds half the conditional variance."""
        log_preds = np.array([-9.0, -8.5, -10.0, -9.2])
        cond_var = np.array([0.1, 0.2, 0.05, 0.3])
        result = conditional_duan_correction(log_preds, cond_var)
        expected = log_preds + cond_var / 2.0
        np.testing.assert_allclose(result, expected, rtol=1e-10)

    def test_zero_variance_is_identity(self):
        """When conditional variance is zero everywhere, output equals input."""
        log_preds = np.array([-9.0, -8.5, -10.0])
        cond_var = np.zeros(3)
        result = conditional_duan_correction(log_preds, cond_var)
        np.testing.assert_array_equal(result, log_preds)

    def test_uniform_variance_matches_global(self):
        """Uniform conditional variance gives same result as global sigma^2/2."""
        log_preds = np.array([-9.0, -8.5, -10.0, -9.2, -8.8])
        sigma2 = 0.15
        cond_var = np.full(5, sigma2)
        result = conditional_duan_correction(log_preds, cond_var)
        expected = log_preds + sigma2 / 2.0
        np.testing.assert_allclose(result, expected, rtol=1e-10)


class TestConditionalDuanClipping:
    """Verify safety clipping of variance estimates."""

    def test_extreme_variance_clipped(self):
        """Variance above max_var is clipped."""
        log_preds = np.array([-9.0, -8.5])
        cond_var = np.array([0.1, 5.0])  # 5.0 exceeds default max_var=1.0
        result = conditional_duan_correction(log_preds, cond_var, max_var=1.0)
        # Second element should use max_var=1.0, not 5.0
        expected = np.array([-9.0 + 0.1 / 2.0, -8.5 + 1.0 / 2.0])
        np.testing.assert_allclose(result, expected, rtol=1e-10)

    def test_negative_variance_clipped_to_zero(self):
        """Negative variance estimates are clipped to zero (no correction)."""
        log_preds = np.array([-9.0, -8.5, -10.0])
        cond_var = np.array([-0.1, 0.2, -0.5])
        result = conditional_duan_correction(log_preds, cond_var)
        expected = np.array([-9.0, -8.5 + 0.2 / 2.0, -10.0])
        np.testing.assert_allclose(result, expected, rtol=1e-10)

    def test_custom_max_var(self):
        """Custom max_var parameter is respected."""
        log_preds = np.array([-9.0])
        cond_var = np.array([0.8])
        result_low = conditional_duan_correction(log_preds, cond_var, max_var=0.5)
        result_high = conditional_duan_correction(log_preds, cond_var, max_var=2.0)
        # Low max_var clips 0.8 to 0.5; high max_var keeps 0.8
        assert result_low[0] == pytest.approx(-9.0 + 0.5 / 2.0)
        assert result_high[0] == pytest.approx(-9.0 + 0.8 / 2.0)


class TestConditionalDuanShapes:
    """Verify array shape handling."""

    def test_output_shape_matches_input(self):
        """Output has same shape as input log_preds."""
        for n in [1, 10, 100, 1000]:
            log_preds = np.random.default_rng(42).standard_normal(n) - 9.0
            cond_var = np.abs(np.random.default_rng(42).standard_normal(n)) * 0.2
            result = conditional_duan_correction(log_preds, cond_var)
            assert result.shape == (n,), f"Failed for n={n}"

    def test_mismatched_shapes_raises(self):
        """Mismatched array lengths raise ValueError."""
        log_preds = np.array([-9.0, -8.5, -10.0])
        cond_var = np.array([0.1, 0.2])  # wrong length
        with pytest.raises(ValueError):
            conditional_duan_correction(log_preds, cond_var)

    def test_output_dtype_is_float64(self):
        """Output is always float64."""
        log_preds = np.array([-9.0, -8.5], dtype=np.float32)
        cond_var = np.array([0.1, 0.2], dtype=np.float32)
        result = conditional_duan_correction(log_preds, cond_var)
        assert result.dtype == np.float64


class TestConditionalDuanQLIKEImprovement:
    """Verify conditional correction outperforms global on heteroscedastic data."""

    def test_beats_global_on_heteroscedastic_synthetic(self):
        """On data with known heteroscedastic structure, conditional beats global.

        Setup: simulate log-RV with two regimes:
        - Calm regime: low residual variance (σ²=0.05)
        - Spike regime: high residual variance (σ²=0.40)

        A global correction uses mean σ² ≈ 0.13, which:
        - Over-corrects calm days (adds too much)
        - Under-corrects spike days (adds too little)

        Conditional correction uses the TRUE σ² per sample → lower QLIKE.
        """
        rng = np.random.default_rng(2026)
        n = 500

        # Generate regime indicator (80% calm, 20% spike)
        is_spike = rng.random(n) < 0.20
        true_sigma2 = np.where(is_spike, 0.40, 0.05)

        # True log-RV (what we're predicting)
        mu = -9.0  # mean log-RV
        true_log_rv = mu + np.sqrt(true_sigma2) * rng.standard_normal(n)

        # "Perfect" model predictions (no bias, just noise)
        # Model predicts mu for everyone (like a simple constant model)
        log_preds = np.full(n, mu)

        # Global Duan: uses average residual variance
        residuals = true_log_rv - log_preds
        global_sigma2 = float(np.var(residuals))
        preds_global = log_preds + global_sigma2 / 2.0

        # Conditional Duan: uses true per-sample variance
        preds_conditional = conditional_duan_correction(log_preds, true_sigma2)

        # QLIKE comparison
        qlike_global = qlike(true_log_rv, preds_global, log_space=True)
        qlike_conditional = qlike(true_log_rv, preds_conditional, log_space=True)

        # Conditional should be strictly better
        assert qlike_conditional < qlike_global, (
            f"Conditional ({qlike_conditional:.6f}) should beat "
            f"global ({qlike_global:.6f})"
        )

    def test_improvement_meaningful_on_realistic_scale(self):
        """Improvement should be >5 bps on realistic heteroscedastic data.

        This tests the economic significance of the correction.
        """
        rng = np.random.default_rng(123)
        n = 2000

        # Realistic regime structure
        is_spike = rng.random(n) < 0.05  # 5% spike days
        true_sigma2 = np.where(is_spike, 0.35, 0.06)

        mu = np.linspace(-9.5, -8.5, n)  # slowly varying mean
        true_log_rv = mu + np.sqrt(true_sigma2) * rng.standard_normal(n)

        # Model with some skill (HAR-like: captures 60% of variance)
        model_noise = 0.4 * np.sqrt(true_sigma2) * rng.standard_normal(n)
        log_preds = mu + model_noise  # imperfect model

        # Global correction
        residuals = true_log_rv - log_preds
        global_sigma2 = float(np.var(residuals))
        preds_global = log_preds + global_sigma2 / 2.0

        # Conditional correction with known variance
        preds_conditional = conditional_duan_correction(log_preds, true_sigma2)

        qlike_global = qlike(true_log_rv, preds_global, log_space=True)
        qlike_conditional = qlike(true_log_rv, preds_conditional, log_space=True)

        # Improvement in bps
        improvement_bps = (qlike_global - qlike_conditional) / qlike_global * 10000
        assert improvement_bps > 5, (
            f"Improvement {improvement_bps:.1f} bps too small (need >5 bps)"
        )
