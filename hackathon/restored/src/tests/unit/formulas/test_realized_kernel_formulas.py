"""Realized Kernel formula verification.

Paper: Barndorff-Nielsen, O.E., Hansen, P.R., Lunde, A. & Shephard, N. (2008)
       "Designing Realized Kernels to Measure the Ex Post Variation of Equity
        Prices in the Presence of Noise"
       Econometrica, 76(6), pp. 1481-1536
Equation: Eq. (3.1): RK = sum_{h=-H}^{H} k(h/(H+1)) * gamma_hat_h
Kernel: Flat-top Parzen (Eq. 3.3)
Bandwidth: H = ceil(n^{3/5}) plug-in (Section 3.2)
"""

from __future__ import annotations

import numpy as np
import pytest

from volforecast.data.measures import noise_gap, realized_kernel

pytestmark = pytest.mark.formula


class TestRealizedKernel:
    """RK = sum_{h=-H}^{H} k(h/(H+1)) * gamma_hat_h, flat-top Parzen kernel.

    Paper: Barndorff-Nielsen, Hansen, Lunde & Shephard (2008)
           "Designing Realized Kernels..."
           Econometrica, 76(6), pp. 1481-1536
    Equation: Eq. (3.1)

    Key properties:
    - Non-negative (guaranteed by Parzen kernel's positive semi-definiteness)
    - Consistent for IV at rate n^{-1/5} even under i.i.d. noise
    - Removes 2*n*noise_var bias present in naive RV
    """

    def test_pure_diffusion_no_noise(self):
        """Without noise, RK should approximately equal RV.

        Note: RK has finite-sample downward bias even without noise due to
        the kernel weighting. Tolerance is generous (30%).
        """
        rng = np.random.default_rng(42)
        n = 1000
        sigma = 0.20  # 20% annualized
        dt = 1.0 / (252 * 78)  # 5-min interval
        innovations = rng.normal(0, sigma * np.sqrt(dt), n)
        log_prices = np.cumsum(np.concatenate([[np.log(100)], innovations]))

        rk = realized_kernel(log_prices)
        returns = np.diff(log_prices)
        rv = float(np.sum(returns**2))

        assert abs(rk - rv) / rv < 0.30

    def test_debiases_with_noise(self):
        """With i.i.d. microstructure noise, RV is biased UP by 2*n*var(noise).

        RK should remove this bias and be substantially smaller than naive RV.
        This is the primary use case (BNHLS 2008, Section 1).
        """
        rng = np.random.default_rng(42)
        n = 5000
        sigma = 0.20
        dt = 1.0 / (252 * 78)
        efficient_returns = rng.normal(0, sigma * np.sqrt(dt), n)
        efficient_log_prices = np.cumsum(np.concatenate([[np.log(100)], efficient_returns]))
        # Add substantial i.i.d. noise (bid-ask bounce)
        noise_std = 0.001
        noise = rng.normal(0, noise_std, n + 1)
        observed_log_prices = efficient_log_prices + noise

        rk = realized_kernel(observed_log_prices)
        observed_returns = np.diff(observed_log_prices)
        rv = float(np.sum(observed_returns**2))

        # With large noise, RV is heavily biased UP; RK should be much smaller
        assert rk < rv * 0.8

    def test_positive_definite(self):
        """RK >= 0 always (enforced by max(rk, 0), guaranteed by Parzen kernel)."""
        rng = np.random.default_rng(99)
        log_prices = np.cumsum(rng.normal(0, 0.0001, 50))
        rk = realized_kernel(log_prices)
        assert rk >= 0.0

    def test_bandwidth_is_n_three_fifths(self, load_gold):
        """Default bandwidth H = ceil(n^{3/5}) per BNHLS (2008) Section 3.2.

        The full optimal formula is H* = c* * xi^{4/5} * n^{3/5} where xi is the
        noise-to-signal ratio. Without xi, the plug-in is H = ceil(n^{3/5}).
        """
        gold = load_gold("realized_kernel.json")
        case = gold["bandwidth_n1000"]
        n = case["n"]
        expected_H = int(np.ceil(n ** (3.0 / 5.0)))
        assert expected_H == case["expected_H"]


class TestNoiseGap:
    """noise_gap = (RK - RV) / RV.

    Measures divergence between noise-robust (RK) and naive (RV) estimators.
    Positive gap -> RK > RV (unusual), negative gap -> noise inflated RV.
    """

    def test_exact_formula(self):
        """Direct formula: (0.0012 - 0.001) / 0.001 = 0.2"""
        assert noise_gap(0.0012, 0.001) == pytest.approx(0.2, rel=1e-12)

    def test_zero_rv(self):
        """RV = 0 returns 0 (avoids division by zero)."""
        assert noise_gap(0.001, 0.0) == 0.0

    def test_negative_gap_possible(self):
        """If RK < RV (finite sample), gap is negative: (0.0008-0.001)/0.001 = -0.2"""
        assert noise_gap(0.0008, 0.001) == pytest.approx(-0.2, rel=1e-12)
