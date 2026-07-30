"""Bipower Variation formula verification.

Paper: Barndorff-Nielsen, O.E. & Shephard, N. (2004)
       "Power and Bipower Variation with Stochastic Volatility and Jumps"
       Journal of Financial Econometrics, 2(1), pp. 1-37
Equation: Eq. (3): BPV_t = (pi/2) * sum_{i=2}^{M} |r_{t,i}| * |r_{t,i-1}|
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from volforecast.data.measures import compute_bpv, compute_realized_variance

pytestmark = pytest.mark.formula


class TestBipowerVariation:
    """BPV = (pi/2) * sum_{i=2}^{M} |r_i| * |r_{i-1}|.

    Paper: Barndorff-Nielsen, O.E. & Shephard, N. (2004)
           "Power and Bipower Variation with Stochastic Volatility and Jumps"
           Journal of Financial Econometrics, 2(1), pp. 1-37
    Equation: Eq. (3)

    Key property: Under no-jump null, BPV -> IV (consistent for integrated
    variance). Under jumps, BPV < RV (robust to jumps).
    """

    def test_exact_three_returns(self, load_gold):
        """Hand: |r2|*|r1| + |r3|*|r2| = 0.02*0.01 + 0.03*0.02 = 0.0008.
        BPV = (pi/2) * 0.0008"""
        gold = load_gold("bpv.json")
        case = gold["three_returns"]
        returns = pd.Series(case["input"])
        bpv = compute_bpv(returns)
        expected = (math.pi / 2.0) * case["expected_products_sum"]
        assert bpv == pytest.approx(expected, rel=1e-12)

    def test_consecutive_pairs_not_overlapping(self, load_gold):
        """BPV sums |r_i|*|r_{i-1}| for EACH i from 2 to M (sliding window).

        NOT non-overlapping blocks: (1,2), (3,4), etc.
        """
        gold = load_gold("bpv.json")
        case = gold["four_returns"]
        returns = pd.Series(case["input"])
        bpv = compute_bpv(returns)
        # Products: |r2|*|r1| + |r3|*|r2| + |r4|*|r3| = 0.0002 + 0.0006 + 0.0012
        expected = (math.pi / 2.0) * case["expected_products_sum"]
        assert bpv == pytest.approx(expected, rel=1e-12)

    def test_two_returns_single_product(self, load_gold):
        """Minimum case: 2 returns -> 1 product."""
        gold = load_gold("bpv.json")
        case = gold["two_returns"]
        returns = pd.Series(case["input"])
        bpv = compute_bpv(returns)
        expected = (math.pi / 2.0) * case["expected_products_sum"]
        assert bpv == pytest.approx(expected, rel=1e-12)

    def test_jump_robustness(self):
        """BPV is less affected by a single large return (jump) than RV.

        Intuition: BPV uses products of adjacent |r|. A single jump inflates
        only 2 products (those adjacent to the jump), while RV inflates by r^2.
        """
        rng = np.random.default_rng(42)
        normal_returns = rng.normal(0, 0.001, 77)
        jump = np.array([0.05])  # Large jump: 50x sigma
        returns = pd.Series(np.concatenate([normal_returns, jump]))

        rv = compute_realized_variance(returns)
        bpv = compute_bpv(returns)
        # BPV should be much closer to the continuous variation
        assert bpv < rv * 0.5

    def test_naive_reference_implementation(self):
        """Cross-check: naive loop vs vectorized implementation."""
        rng = np.random.default_rng(123)
        returns = pd.Series(rng.normal(0, 0.002, 78))

        # Naive loop implementation
        abs_r = np.abs(returns.values)
        products_sum = sum(abs_r[i] * abs_r[i - 1] for i in range(1, len(abs_r)))
        expected = (math.pi / 2.0) * products_sum

        bpv = compute_bpv(returns)
        assert bpv == pytest.approx(expected, rel=1e-12)
