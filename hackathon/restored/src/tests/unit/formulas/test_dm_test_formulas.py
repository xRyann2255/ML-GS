"""Diebold-Mariano test formula verification.

Paper: Diebold, F.X. & Mariano, R.S. (1995)
       "Comparing Predictive Accuracy"
       Journal of Business & Economic Statistics, 13(3), pp. 253-263
Equation: DM = d_bar / sqrt(LRV/T)
    where d_t = L(e1_t) - L(e2_t), d_bar = mean(d_t)
    LRV = long-run variance of d_t (Newey-West HAC, bandwidth = floor(T^{1/3}))
    Under H0 (equal predictive accuracy): DM ~ N(0,1) as T -> infinity

Note: No Harvey, Leybourne & Newbold (1997) small-sample correction applied.
      Negligible for T > 200 (our typical sample size is 500-2800).
"""

from __future__ import annotations

import numpy as np
import pytest

from volforecast.evaluation.statistical_tests import diebold_mariano_test

pytestmark = pytest.mark.formula


class TestDieboldMariano:
    """DM = d_bar / sqrt(LRV/T), Newey-West HAC variance.

    Paper: Diebold, F.X. & Mariano, R.S. (1995)
           "Comparing Predictive Accuracy"
           Journal of Business & Economic Statistics, 13(3), pp. 253-263

    The test compares predictive accuracy of two forecasts using their
    loss differentials. Under H0 of equal accuracy, the loss differentials
    have zero mean.
    """

    def test_identical_losses(self, load_gold):
        """Identical losses -> d_t = 0 for all t -> DM = 0, p ~ 1.

        When both models produce identical loss sequences, the loss differential
        is exactly zero, so the test statistic is zero.
        """
        gold = load_gold("dm_test.json")
        losses = np.ones(200) * 0.001
        result = diebold_mariano_test(losses, losses)
        assert result["dm_stat"] == pytest.approx(
            gold["identical_losses"]["expected_stat"], abs=1e-10
        )
        assert result["p_value"] == pytest.approx(
            gold["identical_losses"]["expected_p_approx"], abs=0.01
        )

    def test_clearly_dominant_model(self):
        """When model 1 consistently beats model 2, DM >> 0 with p << 0.05.

        d_t = L(e1) - L(e2) < 0 when model 1 is better.
        But convention: positive stat means model 1 is worse. Check implementation.
        """
        rng = np.random.default_rng(42)
        n = 500
        losses1 = rng.uniform(0.0001, 0.0005, n)  # Smaller losses (better)
        losses2 = rng.uniform(0.001, 0.005, n)  # Larger losses (worse)

        result = diebold_mariano_test(losses1, losses2)
        # Should show statistically significant difference
        assert result["p_value"] < 0.05

    def test_stat_symmetry(self):
        """DM(losses1, losses2) should flip sign vs DM(losses2, losses1).

        The loss differential d_t reverses sign when arguments are swapped.
        """
        rng = np.random.default_rng(42)
        n = 300
        losses1 = rng.uniform(0.0001, 0.001, n)
        losses2 = rng.uniform(0.0005, 0.002, n)

        result_12 = diebold_mariano_test(losses1, losses2)
        result_21 = diebold_mariano_test(losses2, losses1)

        # Statistics should be negatives of each other
        assert result_12["dm_stat"] == pytest.approx(-result_21["dm_stat"], rel=1e-10)
        # P-values should be equal
        assert result_12["p_value"] == pytest.approx(result_21["p_value"], rel=1e-10)

    def test_random_noise_not_significant(self):
        """Two equally noisy forecasts should yield p > 0.05 (no difference).

        Under H0, the loss differentials are mean-zero noise, and the test
        should not reject at conventional significance levels.
        """
        rng = np.random.default_rng(123)
        n = 200
        # Both models have same expected loss (just different noise realizations)
        base_loss = 0.001
        losses1 = base_loss + rng.normal(0, 0.0001, n)
        losses2 = base_loss + rng.normal(0, 0.0001, n)

        result = diebold_mariano_test(np.abs(losses1), np.abs(losses2))
        # Should not reject H0 at 5%
        assert result["p_value"] > 0.05
