"""QLIKE loss function formula verification.

Paper: Patton, A.J. (2011)
       "Volatility Forecast Comparison Using Imperfect Volatility Proxies"
       Journal of Econometrics, 160(1), pp. 246-256
Equation: Eq. (5): QLIKE(sigma2, h) = log(h) + sigma2/h
    where sigma2 = actual variance (proxy), h = forecast variance.
    QLIKE is minimized when h = sigma2.

Note: Implementation clips log-ratio at [-10, 10] for overflow protection.
      Equivalent within this range (covers variance ratios from e^{-10} to e^{10}).
"""

from __future__ import annotations

import numpy as np
import pytest

from volforecast.evaluation.metrics import qlike, qlike_improvement_bps

pytestmark = pytest.mark.formula


class TestQLIKE:
    """QLIKE(sigma2, h) = log(h) + sigma2/h.

    Paper: Patton, A.J. (2011)
           "Volatility Forecast Comparison Using Imperfect Volatility Proxies"
           Journal of Econometrics, 160(1), pp. 246-256
    Equation: Eq. (5)

    Key properties:
    - Minimized at h = sigma2 (d/dh = 1/h - sigma2/h^2 = 0 => h = sigma2)
    - Convex in h (d^2/dh^2 = -1/h^2 + 2*sigma2/h^3 > 0 at h=sigma2)
    - Robust to noise in the proxy (unlike MSE)
    - Penalizes under-prediction more than over-prediction (asymmetric)
    """

    def test_minimum_at_truth(self):
        """QLIKE is minimized when prediction = actual.

        Proof: d/dh[log(h) + sigma2/h] = 1/h - sigma2/h^2 = 0 => h = sigma2.
        """
        actual = np.array([0.0001, 0.0002, 0.0003, 0.0004])
        perfect = actual.copy()
        perturbed_up = actual * 1.1
        perturbed_down = actual * 0.9

        q_perfect = qlike(actual, perfect)
        q_up = qlike(actual, perturbed_up)
        q_down = qlike(actual, perturbed_down)

        assert q_perfect < q_up
        assert q_perfect < q_down

    def test_asymmetric_penalty(self):
        """Under-prediction penalized more than over-prediction.

        At h = sigma2*(1-eps): QLIKE = log(sigma2*(1-eps)) + 1/(1-eps)
        At h = sigma2*(1+eps): QLIKE = log(sigma2*(1+eps)) + 1/(1+eps)
        The second derivative sigma2/h^2 is larger at h < sigma2.
        """
        actual = np.array([0.0001] * 10)
        under = actual * 0.5  # 50% under-prediction
        over = actual * 1.5  # 50% over-prediction (same magnitude)

        q_under = qlike(actual, under)
        q_over = qlike(actual, over)

        # Under-prediction should be penalized more
        assert q_under > q_over

    def test_zero_at_truth(self):
        """QLIKE = 0 when prediction equals actual (log-space form).

        In log-space: QLIKE = mean(exp(y-yhat) - (y-yhat) - 1).
        When y = yhat: diff = 0, so QLIKE = mean(exp(0) - 0 - 1) = mean(0) = 0.
        This is the minimum (any deviation increases loss).
        """
        actual = np.array([0.001, 0.002, 0.003])
        # In log-space mode (default), pass log-values
        log_actual = np.log(actual)
        q_at_truth = qlike(log_actual, log_actual)
        assert q_at_truth == pytest.approx(0.0, abs=1e-15)

    def test_improvement_bps(self):
        """qlike_improvement_bps = (qlike_base - qlike_model) / qlike_base * 10000.

        Function takes two scalar QLIKE values (pre-computed), not arrays.
        Positive bps = model has lower QLIKE than baseline.
        """
        # Base model has higher QLIKE (worse)
        qlike_base = 0.05
        # New model has lower QLIKE (better)
        qlike_model = 0.045

        bps = qlike_improvement_bps(qlike_base, qlike_model)
        expected = (0.05 - 0.045) / 0.05 * 10000  # = 1000 bps
        assert bps == pytest.approx(expected, rel=1e-12)
        assert bps > 0
