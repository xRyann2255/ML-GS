"""Tests for evaluation metrics.

Validates:
1. QLIKE properties: minimum at truth, non-negative, penalizes asymmetrically
2. MSE/MAE/R² correctness
3. qlike_improvement_bps computation
4. Edge cases: zero variance, identical predictions
"""

import numpy as np
import pytest

from volforecast.evaluation.metrics import (
    compute_all,
    mae,
    mse,
    qlike,
    qlike_improvement_bps,
    r_squared,
)


class TestQLIKE:
    def test_minimum_at_truth(self):
        """QLIKE should be 0 when prediction equals truth."""
        y = np.array([-9.0, -8.5, -10.0, -9.2, -8.8])
        loss = qlike(y, y, log_space=True)
        assert loss == pytest.approx(0.0, abs=1e-12)

    def test_non_negative(self):
        """QLIKE >= 0 for any prediction."""
        rng = np.random.default_rng(42)
        y_true = -9.0 + 0.5 * rng.standard_normal(100)
        y_pred = -9.0 + 0.5 * rng.standard_normal(100)
        loss = qlike(y_true, y_pred, log_space=True)
        assert loss >= 0.0

    def test_asymmetric_penalty(self):
        """QLIKE should penalize under-prediction more than over-prediction."""
        y_true = np.array([-9.0] * 10)
        # Under-predict by 1 unit (predict lower vol than realized)
        y_under = y_true - 1.0
        # Over-predict by 1 unit (predict higher vol than realized)
        y_over = y_true + 1.0

        loss_under = qlike(y_true, y_under, log_space=True)
        loss_over = qlike(y_true, y_over, log_space=True)
        assert loss_under > loss_over

    def test_variance_space(self):
        """QLIKE in variance space: mean(RV/h - log(RV/h) - 1)."""
        rv = np.array([0.0001, 0.0002, 0.00015])
        h = np.array([0.00012, 0.00018, 0.00016])
        expected = np.mean(rv / h - np.log(rv / h) - 1.0)
        loss = qlike(rv, h, log_space=False)
        assert loss == pytest.approx(expected, rel=1e-10)

    def test_log_space_equivalence(self):
        """Log-space and variance-space QLIKE should give same result."""
        rv = np.array([0.0001, 0.0002, 0.00015, 0.0003])
        h = np.array([0.00012, 0.00018, 0.00016, 0.00025])
        loss_var = qlike(rv, h, log_space=False)
        loss_log = qlike(np.log(rv), np.log(h), log_space=True)
        assert loss_var == pytest.approx(loss_log, rel=1e-10)

    def test_rejects_nan(self):
        y = np.array([1.0, np.nan, 3.0])
        with pytest.raises(ValueError, match="NaN"):
            qlike(y, y, log_space=True)

    def test_rejects_length_mismatch(self):
        with pytest.raises(ValueError, match="same length"):
            qlike(np.array([1.0, 2.0]), np.array([1.0]), log_space=True)

    def test_larger_deviation_larger_loss(self):
        """Larger forecast errors should produce larger QLIKE."""
        y_true = np.zeros(50)
        y_small_err = y_true + 0.1
        y_large_err = y_true + 1.0
        assert qlike(y_true, y_small_err) < qlike(y_true, y_large_err)


class TestMSE:
    def test_zero_when_perfect(self):
        y = np.array([1.0, 2.0, 3.0])
        assert mse(y, y) == 0.0

    def test_known_value(self):
        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([1.5, 2.5, 3.5])
        assert mse(y_true, y_pred) == pytest.approx(0.25)

    def test_symmetric(self):
        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([1.5, 2.5, 3.5])
        assert mse(y_true, y_pred) == mse(y_pred, y_true)


class TestMAE:
    def test_zero_when_perfect(self):
        y = np.array([1.0, 2.0, 3.0])
        assert mae(y, y) == 0.0

    def test_known_value(self):
        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([1.5, 2.5, 3.5])
        assert mae(y_true, y_pred) == pytest.approx(0.5)


class TestRSquared:
    def test_perfect_prediction(self):
        y = np.array([1.0, 2.0, 3.0, 4.0])
        assert r_squared(y, y) == pytest.approx(1.0)

    def test_mean_prediction(self):
        """Predicting the mean should give R² = 0."""
        y_true = np.array([1.0, 2.0, 3.0, 4.0])
        y_pred = np.full_like(y_true, y_true.mean())
        assert r_squared(y_true, y_pred) == pytest.approx(0.0, abs=1e-10)

    def test_negative_for_bad_model(self):
        """Worse-than-mean predictions give negative R²."""
        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([10.0, 20.0, 30.0])  # wildly off
        assert r_squared(y_true, y_pred) < 0.0


class TestQLIKEImprovementBps:
    def test_improvement_positive_when_better(self):
        """Model with lower QLIKE should show positive improvement."""
        bps = qlike_improvement_bps(qlike_baseline=0.10, qlike_model=0.09)
        assert bps > 0

    def test_improvement_negative_when_worse(self):
        bps = qlike_improvement_bps(qlike_baseline=0.10, qlike_model=0.11)
        assert bps < 0

    def test_zero_when_same(self):
        bps = qlike_improvement_bps(qlike_baseline=0.10, qlike_model=0.10)
        assert bps == pytest.approx(0.0)


class TestComputeAll:
    def test_returns_all_keys(self):
        y = np.array([-9.0, -8.5, -10.0, -9.2])
        p = np.array([-9.1, -8.4, -10.1, -9.3])
        results = compute_all(y, p)
        assert "qlike" in results
        assert "mse" in results
        assert "mae" in results
        assert "r_squared" in results

    def test_with_model_name_prefix(self):
        y = np.array([-9.0, -8.5, -10.0])
        p = np.array([-9.1, -8.4, -10.1])
        results = compute_all(y, p, model_name="har")
        assert "har_qlike" in results
        assert "har_mse" in results

    def test_perfect_predictions(self):
        rng = np.random.default_rng(42)
        y_true = rng.normal(-4.0, 0.5, 50)
        results = compute_all(y_true, y_true)
        assert results["qlike"] == pytest.approx(0.0, abs=1e-12)
        assert results["mse"] == pytest.approx(0.0, abs=1e-12)
        assert results["mae"] == pytest.approx(0.0, abs=1e-12)
        assert results["r_squared"] == pytest.approx(1.0)


class TestQLIKEImprovementBpsExtended:
    """Additional qlike_improvement_bps edge cases."""

    def test_known_value_1000bps(self):
        # (0.10 - 0.09) / 0.10 * 10000 = 1000 bps
        assert qlike_improvement_bps(0.10, 0.09) == pytest.approx(1000.0)

    def test_zero_baseline_returns_zero(self):
        assert qlike_improvement_bps(0.0, 0.05) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Issue #7: Retransformation bias correction
# ---------------------------------------------------------------------------


class TestRetransformLogToLevel:
    """Tests for retransform_log_to_level (Duan 1995 smearing)."""

    def test_parametric_known_value(self):
        """Parametric fallback: retransform(0, variance=1.0) = exp(0.5) ≈ 1.6487."""
        from volforecast.evaluation.metrics import retransform_log_to_level

        result = retransform_log_to_level(np.array([0.0]), residual_variance=1.0)
        assert result[0] == pytest.approx(np.exp(0.5), rel=1e-10)

    def test_zero_variance_identity(self):
        """retransform(x, variance=0) = exp(x) — no correction needed."""
        from volforecast.evaluation.metrics import retransform_log_to_level

        log_preds = np.array([-9.0, -8.5, -10.0])
        result = retransform_log_to_level(log_preds, residual_variance=0.0)
        expected = np.exp(log_preds)
        np.testing.assert_allclose(result, expected, rtol=1e-10)

    def test_array_input_shape(self):
        """Output shape matches input."""
        from volforecast.evaluation.metrics import retransform_log_to_level

        log_preds = np.array([-9.0, -8.5, -10.0, -9.2, -8.8])
        result = retransform_log_to_level(log_preds, residual_variance=0.3)
        assert result.shape == log_preds.shape

    def test_positive_variance_inflates(self):
        """Positive residual variance should inflate predictions (bias correction up)."""
        from volforecast.evaluation.metrics import retransform_log_to_level

        log_preds = np.array([-9.0, -8.5])
        no_corr = np.exp(log_preds)
        with_corr = retransform_log_to_level(log_preds, residual_variance=0.5)
        assert np.all(with_corr > no_corr)

    def test_nonparametric_with_residuals(self):
        """Non-parametric: uses mean(exp(residuals)) as smearing factor."""
        from volforecast.evaluation.metrics import retransform_log_to_level

        log_preds = np.array([-9.0, -8.5])
        residuals = np.array([0.1, -0.2, 0.3, -0.1, 0.0])
        result = retransform_log_to_level(log_preds, residuals=residuals)
        expected_factor = float(np.mean(np.exp(residuals)))
        expected = np.exp(log_preds) * expected_factor
        np.testing.assert_allclose(result, expected, rtol=1e-10)

    def test_nonparametric_beats_parametric_fat_tails(self):
        """Non-parametric should give larger correction for fat-tailed residuals."""
        from volforecast.evaluation.metrics import retransform_log_to_level

        rng = np.random.default_rng(42)
        # Fat-tailed residuals (Student-t with 3 df)
        residuals = rng.standard_t(df=3, size=1000) * 0.3
        log_preds = np.array([-9.0])
        var_resid = float(np.var(residuals))

        parametric = retransform_log_to_level(log_preds, residual_variance=var_resid)
        nonparametric = retransform_log_to_level(log_preds, residuals=residuals)
        # For fat tails, E[exp(e)] > exp(Var(e)/2)
        assert nonparametric[0] > parametric[0]

    def test_nonparametric_zero_mean_residuals(self):
        """With zero-mean normal residuals, non-parametric ≈ parametric."""
        from volforecast.evaluation.metrics import retransform_log_to_level

        rng = np.random.default_rng(123)
        residuals = rng.normal(0, 0.3, size=100_000)
        log_preds = np.array([-9.0])
        var_resid = float(np.var(residuals))

        parametric = retransform_log_to_level(log_preds, residual_variance=var_resid)
        nonparametric = retransform_log_to_level(log_preds, residuals=residuals)
        # Should be approximately equal for normal residuals
        np.testing.assert_allclose(nonparametric, parametric, rtol=0.01)

    def test_residuals_takes_precedence_over_variance(self):
        """When both residuals and residual_variance given, residuals wins."""
        from volforecast.evaluation.metrics import retransform_log_to_level

        log_preds = np.array([-9.0])
        residuals = np.array([0.5, 0.5, 0.5])  # mean(exp(0.5)) = exp(0.5)
        result = retransform_log_to_level(log_preds, residuals=residuals, residual_variance=999.0)
        expected = np.exp(log_preds) * np.exp(0.5)
        np.testing.assert_allclose(result, expected, rtol=1e-10)


# ---------------------------------------------------------------------------
# QLIKE mathematical proof tests (Task A: sign convention verification)
# ---------------------------------------------------------------------------


class TestQLIKEMathProperties:
    """Mathematical proof tests verifying QLIKE sign convention.

    Formula: mean(exp(y_true - y_pred) - (y_true - y_pred) - 1)
    This is correct per Patton (2011). These tests prove it.
    """

    def test_minimization_at_truth(self):
        """QLIKE(y, y) == 0 and QLIKE(y, y+offset) > 0 for all nonzero offsets."""
        y = np.array([-9.0, -8.5, -10.0, -9.2, -8.8])
        offsets = [-2.0, -1.0, -0.5, -0.1, 0.0, 0.1, 0.5, 1.0, 2.0]
        losses = []
        for offset in offsets:
            losses.append(qlike(y, y + offset, log_space=True))

        # Minimum at offset=0
        min_idx = np.argmin(losses)
        assert offsets[min_idx] == 0.0
        # Value at minimum is zero
        assert losses[min_idx] == pytest.approx(0.0, abs=1e-12)
        # All other offsets produce strictly positive loss
        for i, (offset, loss) in enumerate(zip(offsets, losses)):
            if offset != 0.0:
                assert loss > 0.0, f"Expected loss > 0 at offset={offset}, got {loss}"

    def test_asymmetry_under_prediction_penalized_more(self):
        """QLIKE(y, y-delta) > QLIKE(y, y+delta) for positive delta.

        Under-prediction (y_pred < y_true) is penalized more heavily than
        over-prediction — correct for risk management convention.
        """
        y = np.array([-9.0, -8.5, -10.0, -9.2, -8.8])
        for delta in [0.5, 1.0, 2.0]:
            loss_under = qlike(y, y - delta, log_space=True)  # under-predict
            loss_over = qlike(y, y + delta, log_space=True)  # over-predict
            assert loss_under > loss_over, (
                f"delta={delta}: under={loss_under:.6f} should be > over={loss_over:.6f}"
            )

    def test_convexity(self):
        """QLIKE is convex: second finite differences are non-negative.

        For fixed y_true, compute QLIKE at grid of y_pred values.
        f''(x) >= 0 verified via (f(x-h) - 2f(x) + f(x+h)) / h^2 >= 0.
        """
        y = np.array([-9.0, -8.5, -10.0, -9.2, -8.8])
        h_step = 0.05
        pred_offsets = np.arange(-3.0, 3.0, h_step)
        losses = np.array([qlike(y, y + off, log_space=True) for off in pred_offsets])

        # Second finite differences
        for i in range(1, len(losses) - 1):
            second_diff = losses[i - 1] - 2 * losses[i] + losses[i + 1]
            assert second_diff >= -1e-10, (
                f"Non-convex at offset={pred_offsets[i]:.2f}: second_diff={second_diff:.2e}"
            )

    def test_cross_space_consistency(self):
        """Log-space and variance-space QLIKE produce the same model ranking.

        Three models (good/medium/bad) ranked identically in both spaces.
        """
        rng = np.random.default_rng(99)
        n = 200
        log_rv_true = -9.0 + 0.5 * rng.standard_normal(n)
        rv_true = np.exp(log_rv_true)

        # Good model: small noise around truth
        log_pred_good = log_rv_true + 0.1 * rng.standard_normal(n)
        # Medium model: medium noise
        log_pred_med = log_rv_true + 0.5 * rng.standard_normal(n)
        # Bad model: large noise
        log_pred_bad = log_rv_true + 1.5 * rng.standard_normal(n)

        # Log-space rankings
        q_log_good = qlike(log_rv_true, log_pred_good, log_space=True)
        q_log_med = qlike(log_rv_true, log_pred_med, log_space=True)
        q_log_bad = qlike(log_rv_true, log_pred_bad, log_space=True)

        # Variance-space rankings
        q_var_good = qlike(rv_true, np.exp(log_pred_good), log_space=False)
        q_var_med = qlike(rv_true, np.exp(log_pred_med), log_space=False)
        q_var_bad = qlike(rv_true, np.exp(log_pred_bad), log_space=False)

        # Same ranking in both spaces
        assert q_log_good < q_log_med < q_log_bad
        assert q_var_good < q_var_med < q_var_bad
