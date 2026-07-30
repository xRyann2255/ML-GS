"""Realized Moments (Skewness and Kurtosis) formula verification.

Paper: Amaya, D., Christoffersen, P., Jacobs, K. & Vasquez, A. (2015)
       "Does Realized Skewness Predict the Cross-Section of Equity Returns?"
       Journal of Financial Economics, 118(1), pp. 135-167

Equations:
    Realized Skewness = sqrt(N) * mean(r^3) / mean(r^2)^{3/2}
    Realized Kurtosis = N * mean(r^4) / mean(r^2)^2

Note: These are standardized by realized variance (not a separate vol estimate).
      GAP: Could not verify exact equation numbering from original paper.
      The formulas above are the standard definitions used in realized moments
      literature and match the implementation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.data.measures import compute_realized_moments

pytestmark = pytest.mark.formula


class TestRealizedMoments:
    """Realized Skewness = sqrt(N) * mean(r^3) / mean(r^2)^{3/2}
    Realized Kurtosis = N * mean(r^4) / mean(r^2)^2

    Paper: Amaya, Christoffersen, Jacobs & Vasquez (2015)
           "Does Realized Skewness Predict the Cross-Section of Equity Returns?"
           Journal of Financial Economics, 118(1), pp. 135-167

    GAP: Exact equation number from paper not verified. Formulas match
    standard realized moments definitions in the literature.
    """

    def test_symmetric_returns_zero_skewness(self, load_gold):
        """Perfectly symmetric returns -> skewness = 0.

        Proof: For symmetric r_i, mean(r^3) = 0, so sqrt(N)*0/... = 0.
        """
        gold = load_gold("realized_moments.json")
        case = gold["symmetric_returns"]
        returns = pd.Series(case["input"])
        moments = compute_realized_moments(returns)
        assert moments["realized_skewness"] == pytest.approx(case["expected_skewness"], abs=1e-10)

    def test_kurtosis_formula(self, load_gold):
        """Manual kurtosis: N * mean(r^4) / mean(r^2)^2.

        For [0.01, -0.02, 0.03]:
        mean(r^2) = (1e-4 + 4e-4 + 9e-4)/3 = 4.667e-4
        mean(r^4) = (1e-8 + 16e-8 + 81e-8)/3 = 32.67e-8
        Kurt = 3 * 32.67e-8 / (4.667e-4)^2
        """
        gold = load_gold("realized_moments.json")
        case = gold["kurtosis_three_returns"]
        returns = pd.Series(case["input"])
        moments = compute_realized_moments(returns)

        # Verify against hand computation
        r = np.array(case["input"])
        n = len(r)
        mean_r2 = np.mean(r**2)
        mean_r4 = np.mean(r**4)
        expected_kurt = n * mean_r4 / mean_r2**2
        assert moments["realized_kurtosis"] == pytest.approx(expected_kurt, rel=1e-10)

    def test_skewness_formula(self):
        """Verify skewness = sqrt(N) * mean(r^3) / mean(r^2)^{3/2}."""
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.01, 78))
        moments = compute_realized_moments(returns)

        r = returns.values
        n = len(r)
        mean_r2 = np.mean(r**2)
        mean_r3 = np.mean(r**3)
        expected_skew = np.sqrt(n) * mean_r3 / mean_r2 ** (3.0 / 2.0)
        assert moments["realized_skewness"] == pytest.approx(expected_skew, rel=1e-10)

    def test_gaussian_kurtosis_scales_with_n(self):
        """For Gaussian returns, realized kurtosis = N * mean(r^4) / mean(r^2)^2.

        For N(0,sigma^2): E[r^4] = 3*sigma^4, E[r^2] = sigma^2.
        So realized kurtosis = N * 3*sigma^4 / sigma^4 = 3*N.
        This is NOT the standard kurtosis (which would be 3); this is
        the intraday-scaled version from Amaya et al. (2015).
        """
        rng = np.random.default_rng(42)
        n = 10000
        returns = pd.Series(rng.normal(0, 0.01, n))
        moments = compute_realized_moments(returns)
        # Should be close to 3*N = 30000
        assert abs(moments["realized_kurtosis"] / n - 3.0) < 0.2
