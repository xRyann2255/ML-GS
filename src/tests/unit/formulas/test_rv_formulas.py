"""Realized Variance formula verification.

Paper: Andersen, T.G., Bollerslev, T., Diebold, F.X. & Labys, P. (2003)
       "Modeling and Forecasting Realized Volatility"
       Econometrica, 71(2), pp. 579-625
Equation: Eq. (1): RV_t = sum_{i=1}^{M} r_{t,i}^2
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.data.measures import compute_realized_variance

pytestmark = pytest.mark.formula


class TestRealizedVariance:
    """RV_t = sum_{i=1}^{M} r_{t,i}^2. No mean subtraction.

    Paper: Andersen, T.G., Bollerslev, T., Diebold, F.X. & Labys, P. (2003)
           "Modeling and Forecasting Realized Volatility"
           Econometrica, 71(2), pp. 579-625
    Equation: Eq. (1)
    """

    def test_exact_three_returns(self, load_gold):
        """Hand: 0.01^2 + (-0.02)^2 + 0.03^2 = 0.0001 + 0.0004 + 0.0009 = 0.0014"""
        gold = load_gold("rv.json")
        case = gold["three_returns"]
        returns = pd.Series(case["input"])
        assert compute_realized_variance(returns) == pytest.approx(case["expected"], abs=1e-15)

    def test_single_return(self, load_gold):
        """Single return: RV = r^2 = 0.05^2 = 0.0025"""
        gold = load_gold("rv.json")
        case = gold["single_return"]
        returns = pd.Series(case["input"])
        assert compute_realized_variance(returns) == pytest.approx(case["expected"], abs=1e-15)

    def test_zero_returns(self, load_gold):
        """All zero returns: RV = 0."""
        gold = load_gold("rv.json")
        case = gold["four_zeros"]
        returns = pd.Series(case["input"])
        assert compute_realized_variance(returns) == case["expected"]

    def test_sign_invariance(self):
        """RV is sign-invariant: r^2 = (-r)^2 for all i."""
        r = pd.Series([0.01, -0.02, 0.03, -0.01])
        r_neg = pd.Series([-0.01, 0.02, -0.03, 0.01])
        assert compute_realized_variance(r) == pytest.approx(
            compute_realized_variance(r_neg), abs=1e-15
        )

    def test_scaling(self, load_gold):
        """If returns scale by c, RV scales by c^2.

        Proof: sum (c*r_i)^2 = c^2 * sum r_i^2
        """
        gold = load_gold("rv.json")
        case = gold["scaling_base"]
        r = pd.Series(case["input"])
        c = case["scale_factor"]
        r_scaled = r * c
        assert compute_realized_variance(r_scaled) == pytest.approx(
            case["scaled_expected"], rel=1e-12
        )

    def test_convergence_to_iv(self):
        """As M -> inf, RV -> integrated variance for continuous semimartingale.

        Generate GBM with known sigma^2 = 0.04 (20% annualized), verify
        RV from many intraday returns is close to daily IV = sigma^2/252.
        """
        rng = np.random.default_rng(42)
        sigma = 0.20
        dt = 1.0 / (252 * 4680)  # 1-second returns
        n = 4680
        returns = rng.normal(0, sigma * np.sqrt(dt), n)
        rv = compute_realized_variance(pd.Series(returns))
        expected_daily_iv = sigma**2 / 252
        # With 4680 obs, should be within 10% of true IV
        assert abs(rv - expected_daily_iv) / expected_daily_iv < 0.10
