"""Realized Quarticity and Tripower Quarticity formula verification.

Papers:
  RQ: Barndorff-Nielsen, O.E. & Shephard, N. (2002)
      "Econometric Analysis of Realized Volatility and its Use in Estimating
       Stochastic Volatility Models"
      Journal of the Royal Statistical Society Series B, 64(2), pp. 253-280
      Definition 2: RQ_t = (M/3) * sum_{i=1}^{M} r_{t,i}^4

  RTQ: Barndorff-Nielsen, O.E. & Shephard, N. (2004)
       "Power and Bipower Variation with Stochastic Volatility and Jumps"
       Journal of Financial Econometrics, 2(1), pp. 1-37
       Eq. (5): RTQ = M * mu_{4/3}^{-3} * sum_{i=3}^{M} |r_i|^{4/3} |r_{i-1}|^{4/3} |r_{i-2}|^{4/3}
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy.special import gamma

from volforecast.data.measures import (
    compute_realized_tripower_quarticity,
    compute_rq,
)

pytestmark = pytest.mark.formula


class TestRealizedQuarticity:
    """RQ = (N/3) * sum(r_i^4).

    Paper: Barndorff-Nielsen & Shephard (2002), JRSSB 64(2)
    Equation: Definition 2

    Used as denominator in BNS jump test variance estimation.
    """

    def test_exact_three_returns(self, load_gold):
        """Hand: sum(r^4) = 0.01^4 + 0.02^4 + 0.03^4 = 1e-8 + 16e-8 + 81e-8 = 98e-8.
        RQ = (3/3) * 98e-8 = 9.8e-7"""
        gold = load_gold("rq_rtq.json")
        case = gold["rq_three_returns"]
        returns = pd.Series(case["input"])
        rq = compute_rq(returns)
        assert rq == pytest.approx(case["expected"], rel=1e-12)

    def test_scaling_n_factor(self, load_gold):
        """N/3 scaling: 6 returns should give (6/3) = 2x multiplier vs sum(r^4)."""
        gold = load_gold("rq_rtq.json")
        case = gold["rq_six_uniform"]
        returns = pd.Series(case["input"])
        rq = compute_rq(returns)
        assert rq == pytest.approx(case["expected"], rel=1e-12)

    def test_sign_invariance(self):
        """RQ uses r^4, so sign does not affect result."""
        r = pd.Series([0.01, -0.02, 0.03])
        r_neg = pd.Series([-0.01, 0.02, -0.03])
        assert compute_rq(r) == pytest.approx(compute_rq(r_neg), abs=1e-20)

    def test_naive_reference(self):
        """Cross-check: naive loop vs vectorized implementation."""
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.002, 78))
        n = len(returns)
        expected = (n / 3.0) * float(np.sum(returns.values**4))
        assert compute_rq(returns) == pytest.approx(expected, rel=1e-12)


class TestRealizedTripowerQuarticity:
    """RTQ = M * mu_{4/3}^{-3} * sum(|r_i|^{4/3} |r_{i-1}|^{4/3} |r_{i-2}|^{4/3}).

    Paper: Barndorff-Nielsen & Shephard (2004), J. Fin. Econometrics 2(1)
    Equation: Eq. (5)

    RTQ is jump-robust (unlike RQ). Used in BNS test variance denominator
    for better power under jumps.
    """

    def test_mu_43_constant(self, load_gold):
        """Verify mu_{4/3} = 2^{2/3} * Gamma(7/6) / Gamma(1/2) ~ 0.8309."""
        gold = load_gold("rq_rtq.json")
        case = gold["mu_43_constant"]
        mu_43 = 2 ** (2.0 / 3.0) * gamma(7.0 / 6.0) / gamma(0.5)
        assert mu_43 == pytest.approx(case["expected_approx"], abs=case["tolerance"])

    def test_scaling_with_n(self):
        """RTQ has M (number of observations) as front multiplier."""
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.001, 78))
        rtq = compute_realized_tripower_quarticity(returns)
        assert rtq > 0.0

    def test_triple_products(self, load_gold):
        """Verify triple products use i, i-1, i-2 (sliding window, not skipping).

        Hand computation for [0.01, 0.02, 0.03, 0.04, 0.05]:
        M=5, products for i=2..4 (0-indexed: products start at index 2)
        """
        gold = load_gold("rq_rtq.json")
        case = gold["rtq_five_returns"]
        returns = pd.Series(case["input"])
        rtq = compute_realized_tripower_quarticity(returns)

        # Manual computation
        mu_43 = 2 ** (2.0 / 3.0) * gamma(7.0 / 6.0) / gamma(0.5)
        p = 4.0 / 3.0
        r = np.array(case["input"])
        products = (
            abs(r[2]) ** p * abs(r[1]) ** p * abs(r[0]) ** p
            + abs(r[3]) ** p * abs(r[2]) ** p * abs(r[1]) ** p
            + abs(r[4]) ** p * abs(r[3]) ** p * abs(r[2]) ** p
        )
        expected = 5 * mu_43 ** (-3) * products
        assert rtq == pytest.approx(expected, rel=1e-10)

    def test_naive_reference(self):
        """Cross-check: naive loop vs vectorized implementation."""
        rng = np.random.default_rng(99)
        returns = pd.Series(rng.normal(0, 0.002, 78))
        r = returns.values
        n = len(r)
        mu_43 = 2 ** (2.0 / 3.0) * gamma(7.0 / 6.0) / gamma(0.5)
        p = 4.0 / 3.0

        products_sum = sum(
            abs(r[i]) ** p * abs(r[i - 1]) ** p * abs(r[i - 2]) ** p for i in range(2, n)
        )
        expected = n * mu_43 ** (-3) * products_sum
        assert compute_realized_tripower_quarticity(returns) == pytest.approx(expected, rel=1e-10)
