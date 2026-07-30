"""BNS Jump Detection formula verification.

Paper: Barndorff-Nielsen, O.E. & Shephard, N. (2006)
       "Econometrics of Testing for Jumps in Financial Economics Using
        Bipower Variation"
       Journal of Financial Econometrics, 4(1), pp. 1-30
Equation: Theorem 2:
    Z_BNS = (RV - BPV) / sqrt(theta * RTQ / M)
    where theta = pi^2/4 + pi - 5
    Under H0 (no jumps): Z_BNS ~ N(0,1) as M -> infinity
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.data.measures import (
    compute_bpv,
    compute_realized_tripower_quarticity,
    compute_realized_variance,
    detect_jumps,
)

pytestmark = pytest.mark.formula


class TestJumpDetection:
    """Z_BNS = (RV - BPV) / sqrt(theta * RTQ / M), theta = pi^2/4 + pi - 5.

    Paper: Barndorff-Nielsen & Shephard (2006)
           "Econometrics of Testing for Jumps..."
           Journal of Financial Econometrics, 4(1), pp. 1-30
    Equation: Theorem 2

    The test exploits the fact that under the null of no jumps,
    RV and BPV are both consistent for IV. Under the alternative (jumps present),
    RV - BPV > 0 (because RV captures jump variation but BPV doesn't).
    """

    def test_no_jump_gaussian(self):
        """Pure Gaussian returns (no jump) should not trigger jump indicator.

        Under H0, Z_BNS ~ N(0,1), so with alpha=0.999 (z_crit=3.09)
        false positive rate is 0.1%.
        """
        rng = np.random.default_rng(42)
        n = 78  # One trading day of 5-min bars
        sigma = 0.01  # ~16% annualized
        returns = pd.Series(rng.normal(0, sigma / np.sqrt(n), n))

        rv = compute_realized_variance(returns)
        bpv = compute_bpv(returns)
        rtq = compute_realized_tripower_quarticity(returns)

        result = detect_jumps(rv, bpv, rtq, n, alpha=0.999)
        assert result["jump_indicator"] == 0.0

    def test_single_large_jump_detected(self):
        """78 normal returns + one 50x-sigma return should trigger detection.

        A 5% jump on top of 0.1% intraday vol is unambiguous.
        """
        rng = np.random.default_rng(42)
        n = 78
        sigma = 0.001
        normal_returns = rng.normal(0, sigma, n - 1)
        jump = np.array([0.05])  # 50x sigma
        returns = pd.Series(np.concatenate([normal_returns, jump]))

        rv = compute_realized_variance(returns)
        bpv = compute_bpv(returns)
        rtq = compute_realized_tripower_quarticity(returns)

        result = detect_jumps(rv, bpv, rtq, n, alpha=0.999)
        assert result["jump_indicator"] == 1.0
        assert result["z_stat"] > 3.0

    def test_theta_constant(self, load_gold):
        """Verify theta = pi^2/4 + pi - 5.

        Hand: pi^2/4 = 9.8696/4 = 2.4674, + pi = +3.1416, - 5.
        Total = 2.4674 + 3.1416 - 5 = 0.6090
        """
        gold = load_gold("jump_detection.json")
        case = gold["theta_constant"]
        theta = (np.pi**2 / 4.0) + np.pi - 5.0
        assert theta == pytest.approx(case["expected"], abs=case.get("tolerance", 0.001))

    def test_z_stat_formula(self, load_gold):
        """Manually verify Z = (RV - BPV) / sqrt(theta * RTQ / M).

        Using exact inputs from gold values to verify formula implementation.
        """
        gold = load_gold("jump_detection.json")
        case = gold["z_stat_manual"]
        rv = case["rv"]
        bpv = case["bpv"]
        rtq = case["rtq"]
        n = case["n"]
        theta = (np.pi**2 / 4.0) + np.pi - 5.0

        result = detect_jumps(rv, bpv, rtq, n)
        expected_z = (rv - bpv) / np.sqrt(theta * rtq / n)
        assert result["z_stat"] == pytest.approx(expected_z, rel=1e-10)
