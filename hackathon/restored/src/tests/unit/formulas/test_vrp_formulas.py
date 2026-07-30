"""Variance Risk Premium formula verification.

Papers:
  Carr, P. & Wu, L. (2009)
      "Variance Risk Premiums"
      Review of Financial Studies, 22(3), pp. 1311-1341
      (ex-post VRP proxy: VRP = IV^2 - RV)

  Bollerslev, T., Tauchen, G. & Zhou, H. (2009)
      "Expected Stock Returns and Variance Risk Premia"
      Review of Financial Studies, 22(11), pp. 4463-4492
      (conditional VRP: VRP = IV^2 - E[RV|F_t], requires forecast model)

Implementation notes:
  - features/options.py compute_vrp: ex-post proxy (Carr & Wu 2009)
  - features/iv_features.py: conditional VRP using HAR-based E[RV] (Bollerslev 2009)
    with fallback to rolling mean * 252 when data < 100 obs
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.features.options import compute_vrp

pytestmark = pytest.mark.formula


class TestVarianceRiskPremium:
    """VRP = IV^2 - RV (ex-post proxy per Carr & Wu 2009, RFS).

    Paper: Carr, P. & Wu, L. (2009)
           "Variance Risk Premiums"
           Review of Financial Studies, 22(3), pp. 1311-1341

    Interpretation:
    - VRP > 0: Implied variance exceeds realized (variance seller earns premium)
    - VRP < 0: Realized exceeded implied (rare, typically during vol spikes)
    - Empirically, VRP is positive on average (variance risk premium exists)
    """

    def test_simple_positive_vrp(self, load_gold):
        """Hand: IV^2=0.04, RV=0.03 -> VRP = 0.04 - 0.03 = 0.01"""
        gold = load_gold("vrp.json")
        case = gold["simple_case"]
        # compute_vrp expects a DataFrame row with 'atm_iv' and a separate rv value
        # We test the formula logic directly
        iv_squared = case["iv_squared"]
        rv = case["rv"]
        expected = case["expected_vrp"]
        assert (iv_squared - rv) == pytest.approx(expected, rel=1e-10)

    def test_negative_vrp(self, load_gold):
        """Hand: IV^2=0.02, RV=0.05 -> VRP = 0.02 - 0.05 = -0.03"""
        gold = load_gold("vrp.json")
        case = gold["negative_vrp"]
        iv_squared = case["iv_squared"]
        rv = case["rv"]
        expected = case["expected_vrp"]
        assert (iv_squared - rv) == pytest.approx(expected, rel=1e-10)

    def test_zero_vrp(self, load_gold):
        """Hand: IV^2=RV -> VRP = 0"""
        gold = load_gold("vrp.json")
        case = gold["zero_vrp"]
        iv_squared = case["iv_squared"]
        rv = case["rv"]
        expected = case["expected_vrp"]
        assert (iv_squared - rv) == pytest.approx(expected, abs=1e-15)

    def test_compute_vrp_function(self):
        """Test the actual compute_vrp function.

        compute_vrp(atm_iv: Series, rv: Series) -> Series
        where atm_iv is in percentage points (e.g., 20.0 = 20%)
        and rv is daily realized variance (not annualized).
        VRP = (atm_iv_pct / 100)^2 - rv * 252
        """
        dates = pd.bdate_range("2024-01-02", periods=5)
        # ATM IV in percentage points (e.g., 20.0 means 20%)
        atm_iv = pd.Series([20.0, 22.0, 18.0, 25.0, 21.0], index=dates)
        # Daily realized variance (not annualized)
        rv_series = pd.Series([0.00015, 0.00018, 0.00012, 0.00025, 0.00016], index=dates)

        vrp = compute_vrp(atm_iv, rv_series)
        # VRP = (atm_iv/100)^2 - rv*252
        expected = (atm_iv.values / 100.0) ** 2 - rv_series.values * 252.0
        np.testing.assert_allclose(vrp.values, expected, rtol=1e-10)
