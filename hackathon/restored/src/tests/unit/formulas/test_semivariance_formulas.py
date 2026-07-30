"""Semivariance formula verification.

Paper: Barndorff-Nielsen, O.E., Kinnebrock, S. & Shephard, N. (2010)
       "Measuring Downside Risk - Realised Semivariance"
       in Bollerslev, T., Russell, J. & Watson, M. (eds)
       Volatility and Time Series Econometrics: Essays in Honor of Robert Engle
       Oxford University Press
Equation: Eq. (2.1):
    RS+_t = sum_{i=1}^{M} r_{t,i}^2 * I(r_{t,i} >= 0)
    RS-_t = sum_{i=1}^{M} r_{t,i}^2 * I(r_{t,i} < 0)
Key identity: RS+_t + RS-_t = RV_t
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.data.measures import compute_realized_variance, compute_semivariances

pytestmark = pytest.mark.formula


class TestSemivariances:
    """RS+ = sum(r_i^2 * I(r_i >= 0)), RS- = sum(r_i^2 * I(r_i < 0)).

    Paper: Barndorff-Nielsen, Kinnebrock & Shephard (2010)
    Equation: Eq. (2.1)

    Key property: RS+ + RS- = RV always (exhaustive partition of return space).
    """

    def test_exhaustive_partition(self):
        """RS+ + RS- = RV must always hold.

        This is the defining identity from BKS (2010): since I(r>=0) + I(r<0) = 1,
        sum(r^2 * I(r>=0)) + sum(r^2 * I(r<0)) = sum(r^2) = RV.
        """
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.01, 100))
        rv = compute_realized_variance(returns)
        semivars = compute_semivariances(returns)
        assert semivars["rs_positive"] + semivars["rs_negative"] == pytest.approx(rv, rel=1e-12)

    def test_zero_return_goes_positive(self, load_gold):
        """r=0 classified as positive (>= 0 indicator) per BKS (2010).

        Hand: r=0 -> 0^2=0 to RS+, r=0.01 -> 0.0001 to RS+, r=-0.01 -> 0.0001 to RS-
        """
        gold = load_gold("semivariances.json")
        case = gold["mixed_returns"]
        returns = pd.Series(case["input"])
        semivars = compute_semivariances(returns)
        assert semivars["rs_positive"] == pytest.approx(case["rs_positive"], abs=1e-15)
        assert semivars["rs_negative"] == pytest.approx(case["rs_negative"], abs=1e-15)

    def test_all_positive_returns(self, load_gold):
        """All positive: RS- = 0, RS+ = RV."""
        gold = load_gold("semivariances.json")
        case = gold["all_positive"]
        returns = pd.Series(case["input"])
        semivars = compute_semivariances(returns)
        assert semivars["rs_negative"] == case["rs_negative"]
        assert semivars["rs_positive"] == pytest.approx(case["rs_positive"], rel=1e-12)

    def test_all_negative_returns(self, load_gold):
        """All negative: RS+ = 0, RS- = RV."""
        gold = load_gold("semivariances.json")
        case = gold["all_negative"]
        returns = pd.Series(case["input"])
        semivars = compute_semivariances(returns)
        assert semivars["rs_positive"] == case["rs_positive"]
        assert semivars["rs_negative"] == pytest.approx(case["rs_negative"], rel=1e-12)

    def test_large_sample_partition(self):
        """Large sample: RS+ + RS- = RV for many returns (stress test identity)."""
        rng = np.random.default_rng(123)
        returns = pd.Series(rng.normal(0, 0.005, 1000))
        rv = compute_realized_variance(returns)
        semivars = compute_semivariances(returns)
        assert semivars["rs_positive"] + semivars["rs_negative"] == pytest.approx(rv, rel=1e-12)

    def test_naive_reference(self):
        """Cross-check: naive loop vs vectorized implementation."""
        rng = np.random.default_rng(7)
        returns = pd.Series(rng.normal(0, 0.003, 78))
        r = returns.values

        rs_pos = sum(ri**2 for ri in r if ri >= 0)
        rs_neg = sum(ri**2 for ri in r if ri < 0)

        semivars = compute_semivariances(returns)
        assert semivars["rs_positive"] == pytest.approx(rs_pos, rel=1e-12)
        assert semivars["rs_negative"] == pytest.approx(rs_neg, rel=1e-12)
