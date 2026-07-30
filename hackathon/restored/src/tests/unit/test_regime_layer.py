"""Tests for features/regime.py — RegimeLayer (2-state Markov-switching).

TDD: Tests written BEFORE implementation.

Validates:
1. Output columns and value ranges
2. Rolling-mean relationship between regime_prob_d and regime_prob_w
3. Convergence failure handling (no surprise NaN after first successful fit)
4. PIT leakage: filtered (not smoothed) probabilities
5. PIT leakage: frozen-parameter forward filtering (no param re-estimation)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Synthetic data fixture — regime-switching process
# ---------------------------------------------------------------------------

def _make_regime_data(n_days: int = 400, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic daily RV with regime switching."""
    rng = np.random.default_rng(seed)
    rv = np.empty(n_days)
    state = 0  # 0=calm, 1=stress
    for i in range(n_days):
        if rng.random() < 0.05:
            state = 1 - state
        rv[i] = np.exp(rng.normal(-8 if state == 0 else -5, 0.3 if state == 0 else 0.8))
    return pd.DataFrame(
        {"rv": rv},
        index=pd.bdate_range("2020-01-01", periods=n_days),
    )


@pytest.fixture
def daily_data() -> pd.DataFrame:
    return _make_regime_data()


# ---------------------------------------------------------------------------
# Fast tests
# ---------------------------------------------------------------------------

class TestRegimeLayerBasic:
    """Basic output contract tests."""

    def test_output_columns(self, daily_data: pd.DataFrame) -> None:
        from volforecast.features.regime import RegimeLayer

        layer = RegimeLayer()
        result = layer.compute(daily_data)
        assert list(result.columns) == ["regime_prob_d", "regime_prob_w"]
        assert len(result) == len(daily_data)

    def test_regime_prob_range(self, daily_data: pd.DataFrame) -> None:
        from volforecast.features.regime import RegimeLayer

        layer = RegimeLayer()
        result = layer.compute(daily_data)
        valid = result["regime_prob_d"].dropna()
        assert len(valid) > 0, "Expected some non-NaN regime probabilities"
        assert (valid >= 0.0).all(), "regime_prob_d has values < 0"
        assert (valid <= 1.0).all(), "regime_prob_d has values > 1"

    def test_regime_prob_d_lagged(self, daily_data: pd.DataFrame) -> None:
        """regime_prob_d at date t is based on lagged endog (shift(1)),
        so it does NOT use rv[t] itself — only rv[:t-1]."""
        from volforecast.features.regime import RegimeLayer

        layer = RegimeLayer()
        result = layer.compute(daily_data)
        # The endog is log(rv).diff().shift(1) — so date t's endog uses rv[t-2] and rv[t-1].
        # regime_prob_d at date t is filtered on endog[:t], which only uses rv up to t-1.
        # This is verified more rigorously in the PIT tests below.
        # Here we just check it's not all NaN and has the right index alignment.
        assert result.index.equals(daily_data.index)
        # First min_history entries should be NaN (warmup)
        warmup_nans = result["regime_prob_d"].iloc[:252].isna().sum()
        assert warmup_nans >= 250, "Expected most of warmup period to be NaN"

    def test_regime_prob_w_is_rolling_mean(self, daily_data: pd.DataFrame) -> None:
        from volforecast.features.regime import RegimeLayer

        layer = RegimeLayer()
        result = layer.compute(daily_data)
        expected_w = result["regime_prob_d"].rolling(5).mean()
        # Compare where both are non-NaN
        mask = result["regime_prob_w"].notna() & expected_w.notna()
        if mask.sum() > 0:
            pd.testing.assert_series_equal(
                result["regime_prob_w"][mask],
                expected_w[mask],
                check_names=False,
                atol=1e-12,
            )

    def test_convergence_failure_no_nan(self) -> None:
        """With adversarial data, after the first successful fit,
        regime_prob_d should never go back to NaN (reuses old params)."""
        from volforecast.features.regime import RegimeLayer

        # Create data that's mostly constant (hard for MS model) then normal
        rng = np.random.default_rng(99)
        n = 400
        rv = np.empty(n)
        # First 260 days: near-constant (will likely cause convergence issues)
        rv[:260] = np.exp(-7.0 + rng.normal(0, 0.001, 260))
        # Remaining days: normal regime-switching
        state = 0
        for i in range(260, n):
            if rng.random() < 0.05:
                state = 1 - state
            rv[i] = np.exp(rng.normal(-8 if state == 0 else -5, 0.3 if state == 0 else 0.8))
        df = pd.DataFrame({"rv": rv}, index=pd.bdate_range("2020-01-01", periods=n))

        layer = RegimeLayer()
        result = layer.compute(df)

        # Find first non-NaN position
        first_valid = result["regime_prob_d"].first_valid_index()
        if first_valid is not None:
            after_first = result["regime_prob_d"].loc[first_valid:]
            nan_after = after_first.isna().sum()
            assert nan_after == 0, (
                f"Found {nan_after} NaN values after first successful fit at {first_valid}"
            )


# ---------------------------------------------------------------------------
# PIT leakage tests (CRITICAL)
# ---------------------------------------------------------------------------

class TestRegimeLayerPIT:
    """Point-in-time leakage tests — the core deliverable."""

    def test_pit_filtered_not_smoothed(self) -> None:
        """Perturb rv at dates t+1..t+5. Regime prob at date t must be
        INVARIANT. Smoothed probabilities use future data; filtered don't."""
        from volforecast.features.regime import RegimeLayer

        base = _make_regime_data(n_days=400, seed=42)
        layer = RegimeLayer(refit_every=21, min_history=252)
        result_base = layer.compute(base)

        # Pick a test date well after warmup and not at a refit boundary
        # min_history=252, so first non-NaN around index 252
        # Pick index 300 — solidly after warmup
        test_idx = 300
        test_date = base.index[test_idx]

        # Perturb rv at dates t+1..t+5 (the FUTURE from test_date's perspective)
        perturbed = base.copy()
        perturbed.iloc[test_idx + 1 : test_idx + 6, 0] *= 10.0  # 10x spike

        layer2 = RegimeLayer(refit_every=21, min_history=252)
        result_perturbed = layer2.compute(perturbed)

        base_prob = result_base.loc[test_date, "regime_prob_d"]
        pert_prob = result_perturbed.loc[test_date, "regime_prob_d"]

        # Both should be non-NaN
        assert not np.isnan(base_prob), f"Base prob is NaN at {test_date}"
        assert not np.isnan(pert_prob), f"Perturbed prob is NaN at {test_date}"
        # Must be exactly equal (filtered probs don't look ahead)
        assert base_prob == pytest.approx(pert_prob, abs=1e-10), (
            f"PIT VIOLATION (smoothed?): regime_prob_d at {test_date} changed "
            f"from {base_prob:.6f} to {pert_prob:.6f} when future data was perturbed"
        )

    def test_pit_frozen_params(self) -> None:
        """Perturb data AFTER the next refit date R+refit_every.
        Regime prob at date t (between R and R+refit_every) must be INVARIANT.
        This catches parameter leakage from the extended window."""
        from volforecast.features.regime import RegimeLayer

        refit_every = 21
        min_hist = 252
        base = _make_regime_data(n_days=450, seed=42)

        layer = RegimeLayer(refit_every=refit_every, min_history=min_hist)
        result_base = layer.compute(base)

        # Refit dates are at indices min_hist, min_hist+refit_every, ...
        # Pick a test date in the first refit block: between min_hist and min_hist+refit_every
        test_idx = min_hist + 10  # 10 days into the first refit block
        test_date = base.index[test_idx]

        # Perturb data well AFTER the next refit (min_hist + refit_every)
        perturb_start = min_hist + refit_every + 5
        perturbed = base.copy()
        perturbed.iloc[perturb_start : perturb_start + 20, 0] *= 100.0

        layer2 = RegimeLayer(refit_every=refit_every, min_history=min_hist)
        result_perturbed = layer2.compute(perturbed)

        base_prob = result_base.loc[test_date, "regime_prob_d"]
        pert_prob = result_perturbed.loc[test_date, "regime_prob_d"]

        assert not np.isnan(base_prob), f"Base prob is NaN at {test_date}"
        assert not np.isnan(pert_prob), f"Perturbed prob is NaN at {test_date}"
        assert base_prob == pytest.approx(pert_prob, abs=1e-10), (
            f"PIT VIOLATION (param leakage): regime_prob_d at {test_date} changed "
            f"from {base_prob:.6f} to {pert_prob:.6f} when data after next refit was perturbed"
        )
