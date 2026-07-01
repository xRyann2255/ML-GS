"""Tests for IV feature computation from raw IV surface cache.

TDD: Tests written first, implementation follows.
Verifies formula correctness, shift(1) causality, and NaN warmup.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_iv_raw_panel(n_days: int = 100) -> pd.DataFrame:
    """Create synthetic raw IV panel (output of ingest_iv_surface)."""
    rng = np.random.default_rng(42)
    idx = pd.bdate_range("2024-01-02", periods=n_days)

    return pd.DataFrame(
        {
            "atm_iv_1m": 0.15 + rng.normal(0, 0.01, n_days),
            "atm_iv_3m": 0.16 + rng.normal(0, 0.01, n_days),
            "iv_put_25d_1m": 0.22 + rng.normal(0, 0.01, n_days),
            "iv_call_25d_1m": 0.12 + rng.normal(0, 0.01, n_days),
            "skew_1m": 0.10 + rng.normal(0, 0.005, n_days),
            "vix": 15.0 + np.cumsum(rng.normal(0, 0.3, n_days)),
        },
        index=pd.DatetimeIndex(idx, name="date"),
    )


def _make_rv_panel(n_days: int = 100) -> pd.DataFrame:
    """Create synthetic daily RV panel (output of build_rv_panel)."""
    rng = np.random.default_rng(123)
    idx = pd.bdate_range("2024-01-02", periods=n_days)

    # RV in daily variance units (annualized ~15% → daily ~0.15²/252 ≈ 0.0000893)
    rv = 0.0001 + np.abs(rng.normal(0, 0.00005, n_days))

    return pd.DataFrame({"rv": rv}, index=pd.DatetimeIndex(idx, name="date"))


# ---------------------------------------------------------------------------
# Tests: build_iv_feature_panel
# ---------------------------------------------------------------------------


class TestBuildIvFeaturePanel:
    """Test the feature transformation pipeline."""

    def test_returns_dataframe(self):
        from volforecast.data.iv_features import build_iv_feature_panel

        iv_raw = _make_iv_raw_panel()
        rv_panel = _make_rv_panel()
        result = build_iv_feature_panel(iv_raw, rv_panel)
        assert isinstance(result, pd.DataFrame)

    def test_has_all_expected_columns(self):
        from volforecast.data.iv_features import build_iv_feature_panel

        iv_raw = _make_iv_raw_panel()
        rv_panel = _make_rv_panel()
        result = build_iv_feature_panel(iv_raw, rv_panel)

        expected = {
            "atm_iv_1m",
            "atm_iv_3m",
            "skew_1m",
            "iv_put_25d",
            "iv_call_25d",
            "vrp",
            "term_slope",
            "butterfly_1m",
            "iv_rv_gap",
            "vix",
            "vix_innovation",
            "vol_of_vix",
            "vts",
            "forward_vol_1m3m",
        }
        assert expected.issubset(set(result.columns)), f"Missing: {expected - set(result.columns)}"

    def test_shift_causality(self):
        """All features at time t must use data from t-1 (shift(1) applied)."""
        from volforecast.data.iv_features import build_iv_feature_panel

        iv_raw = _make_iv_raw_panel()
        rv_panel = _make_rv_panel()
        result = build_iv_feature_panel(iv_raw, rv_panel)

        # First row should be NaN (shifted from nothing)
        assert result.iloc[0].isna().all(), "First row must be NaN due to shift(1)"

    def test_vrp_formula(self):
        """VRP fallback path: (atm_iv)^2 - rolling_rv_22d * 252, then shift(1).

        When data < 100 obs, _har_expected_rv falls back to rolling mean * 252.
        The full Bollerslev et al. (2009, RFS) VRP uses HAR-CJ E_t[RV] as the
        conditional expectation. This test exercises the short-data fallback.
        """
        from volforecast.data.iv_features import build_iv_feature_panel

        iv_raw = _make_iv_raw_panel(50)
        rv_panel = _make_rv_panel(50)
        result = build_iv_feature_panel(iv_raw, rv_panel)

        # Manually compute expected VRP (before shift)
        rv_22d = rv_panel["rv"].rolling(22).mean()
        vrp_unshifted = iv_raw["atm_iv_1m"] ** 2 - rv_22d * 252.0

        # After shift(1), row i of result should equal row i-1 of unshifted
        # Check row 25 (after 22-day warmup + 1 shift)
        idx = 25
        expected_val = vrp_unshifted.iloc[idx - 1]
        actual_val = result["vrp"].iloc[idx]
        np.testing.assert_almost_equal(actual_val, expected_val, decimal=10)

    def test_term_slope_formula(self):
        """term_slope = atm_iv_3m - atm_iv_1m, then shift(1)."""
        from volforecast.data.iv_features import build_iv_feature_panel

        iv_raw = _make_iv_raw_panel(50)
        rv_panel = _make_rv_panel(50)
        result = build_iv_feature_panel(iv_raw, rv_panel)

        slope_unshifted = iv_raw["atm_iv_3m"] - iv_raw["atm_iv_1m"]
        idx = 5
        expected_val = slope_unshifted.iloc[idx - 1]
        actual_val = result["term_slope"].iloc[idx]
        np.testing.assert_almost_equal(actual_val, expected_val, decimal=10)

    def test_butterfly_formula(self):
        """butterfly = 0.5*(put_25d + call_25d) - atm, then shift(1)."""
        from volforecast.data.iv_features import build_iv_feature_panel

        iv_raw = _make_iv_raw_panel(50)
        rv_panel = _make_rv_panel(50)
        result = build_iv_feature_panel(iv_raw, rv_panel)

        bf_unshifted = (
            0.5 * (iv_raw["iv_put_25d_1m"] + iv_raw["iv_call_25d_1m"]) - iv_raw["atm_iv_1m"]
        )
        idx = 5
        expected_val = bf_unshifted.iloc[idx - 1]
        actual_val = result["butterfly_1m"].iloc[idx]
        np.testing.assert_almost_equal(actual_val, expected_val, decimal=10)

    def test_iv_rv_gap_formula(self):
        """iv_rv_gap = atm_iv - sqrt(rv_22d * 252), then shift(1)."""
        from volforecast.data.iv_features import build_iv_feature_panel

        iv_raw = _make_iv_raw_panel(50)
        rv_panel = _make_rv_panel(50)
        result = build_iv_feature_panel(iv_raw, rv_panel)

        rv_22d = rv_panel["rv"].rolling(22).mean()
        gap_unshifted = iv_raw["atm_iv_1m"] - np.sqrt(rv_22d * 252.0)
        idx = 25
        expected_val = gap_unshifted.iloc[idx - 1]
        actual_val = result["iv_rv_gap"].iloc[idx]
        np.testing.assert_almost_equal(actual_val, expected_val, decimal=10)

    def test_vol_of_vix_uses_real_vvix_when_available(self):
        """vol_of_vix uses real VVIX from cache (decimal = index/100), shift(1)."""
        from unittest.mock import patch

        from volforecast.data.iv_features import build_iv_feature_panel

        iv_raw = _make_iv_raw_panel(50)
        rv_panel = _make_rv_panel(50)

        # Create synthetic VVIX cache (index points, e.g. 80-90)
        rng = np.random.default_rng(99)
        vvix_values = 80.0 + rng.normal(0, 3, 50)
        vvix_cache = pd.DataFrame(
            {"vvix": vvix_values},
            index=rv_panel.index,
        )

        with patch("volforecast.data.iv_features.load_iv_cache", return_value=vvix_cache):
            result = build_iv_feature_panel(iv_raw, rv_panel)

        # vol_of_vix should be VVIX/100 (decimal), shifted by 1
        idx = 5
        expected_val = vvix_values[idx - 1] / 100.0
        actual_val = result["vol_of_vix"].iloc[idx]
        np.testing.assert_almost_equal(actual_val, expected_val, decimal=10)

    def test_vol_of_vix_fallback_proxy(self):
        """vol_of_vix falls back to realized proxy when cache unavailable."""
        from unittest.mock import patch

        from volforecast.data.iv_features import build_iv_feature_panel

        iv_raw = _make_iv_raw_panel(50)
        rv_panel = _make_rv_panel(50)

        with patch("volforecast.data.iv_features.load_iv_cache", return_value=None):
            result = build_iv_feature_panel(iv_raw, rv_panel)

        vix = iv_raw["vix"]
        log_ret = np.log(vix / vix.shift(1))
        vov_unshifted = np.sqrt(252.0 * (log_ret**2).rolling(22).mean())
        idx = 30  # after warmup
        expected_val = vov_unshifted.iloc[idx - 1]
        actual_val = result["vol_of_vix"].iloc[idx]
        np.testing.assert_almost_equal(actual_val, expected_val, decimal=10)

    def test_vix_innovation_formula(self):
        """vix_innovation = vix_t - vix_{t-1}, then shift(1)."""
        from volforecast.data.iv_features import build_iv_feature_panel

        iv_raw = _make_iv_raw_panel(50)
        rv_panel = _make_rv_panel(50)
        result = build_iv_feature_panel(iv_raw, rv_panel)

        innov_unshifted = iv_raw["vix"] - iv_raw["vix"].shift(1)
        idx = 5
        expected_val = innov_unshifted.iloc[idx - 1]
        actual_val = result["vix_innovation"].iloc[idx]
        np.testing.assert_almost_equal(actual_val, expected_val, decimal=10)

    def test_vts_formula(self):
        """vts = atm_iv_3m / atm_iv_1m, then shift(1)."""
        from volforecast.data.iv_features import build_iv_feature_panel

        iv_raw = _make_iv_raw_panel(50)
        rv_panel = _make_rv_panel(50)
        result = build_iv_feature_panel(iv_raw, rv_panel)

        vts_unshifted = iv_raw["atm_iv_3m"] / iv_raw["atm_iv_1m"]
        idx = 5
        expected_val = vts_unshifted.iloc[idx - 1]
        actual_val = result["vts"].iloc[idx]
        np.testing.assert_almost_equal(actual_val, expected_val, decimal=10)

    def test_vts_contango_backwardation(self):
        """VTS > 1 when 3m > 1m (contango), < 1 when inverted."""
        from volforecast.data.iv_features import build_iv_feature_panel

        rng = np.random.default_rng(77)
        n = 50
        idx = pd.bdate_range("2024-01-02", periods=n)
        # Normal: 3m > 1m → VTS > 1
        iv_raw = pd.DataFrame(
            {
                "atm_iv_1m": np.full(n, 0.15),
                "atm_iv_3m": np.full(n, 0.18),
                "iv_put_25d_1m": np.full(n, 0.22),
                "iv_call_25d_1m": np.full(n, 0.12),
                "skew_1m": np.full(n, 0.10),
                "vix": 15.0 + np.cumsum(rng.normal(0, 0.2, n)),
            },
            index=pd.DatetimeIndex(idx, name="date"),
        )
        rv_panel = _make_rv_panel(n)
        result = build_iv_feature_panel(iv_raw, rv_panel)
        valid_vts = result["vts"].dropna()
        assert (valid_vts > 1.0).all(), "VTS should be > 1 when 3m > 1m (contango)"

    def test_forward_vol_formula(self):
        """forward_vol_1m3m = sqrt(max(3m^2*T3 - 1m^2*T1, 0) / (T3-T1)), then shift(1)."""
        from volforecast.data.iv_features import build_iv_feature_panel

        iv_raw = _make_iv_raw_panel(50)
        rv_panel = _make_rv_panel(50)
        result = build_iv_feature_panel(iv_raw, rv_panel)

        t_1m = 1.0 / 12.0
        t_3m = 3.0 / 12.0
        total_var_diff = iv_raw["atm_iv_3m"] ** 2 * t_3m - iv_raw["atm_iv_1m"] ** 2 * t_1m
        fwd_unshifted = np.sqrt(np.maximum(total_var_diff, 0.0) / (t_3m - t_1m))
        idx = 5
        expected_val = fwd_unshifted.iloc[idx - 1]
        actual_val = result["forward_vol_1m3m"].iloc[idx]
        np.testing.assert_almost_equal(actual_val, expected_val, decimal=10)

    def test_forward_vol_clamped_to_zero(self):
        """Extreme backwardation: 1m >> 3m should not produce NaN."""
        from volforecast.data.iv_features import build_iv_feature_panel

        n = 50
        idx = pd.bdate_range("2024-01-02", periods=n)
        rng = np.random.default_rng(88)
        # Force backwardation: 1m much higher than 3m
        iv_raw = pd.DataFrame(
            {
                "atm_iv_1m": np.full(n, 0.40),  # very high
                "atm_iv_3m": np.full(n, 0.15),  # much lower
                "iv_put_25d_1m": np.full(n, 0.45),
                "iv_call_25d_1m": np.full(n, 0.35),
                "skew_1m": np.full(n, 0.10),
                "vix": 35.0 + np.cumsum(rng.normal(0, 0.2, n)),
            },
            index=pd.DatetimeIndex(idx, name="date"),
        )
        rv_panel = _make_rv_panel(n)
        result = build_iv_feature_panel(iv_raw, rv_panel)
        valid_fwd = result["forward_vol_1m3m"].dropna()
        # Should be zero (clamped), not NaN
        assert not valid_fwd.isna().any(), "forward_vol should not be NaN even in backwardation"
        assert (valid_fwd == 0.0).all(), "forward_vol should be 0 when variance diff is negative"

    def test_nan_warmup_period(self):
        """First rows should have NaN due to rolling windows + shift(1)."""
        from unittest.mock import patch

        from volforecast.data.iv_features import build_iv_feature_panel

        iv_raw = _make_iv_raw_panel(100)
        rv_panel = _make_rv_panel(100)

        # Mock VVIX cache as unavailable to test proxy warmup behavior
        with patch("volforecast.data.iv_features.load_iv_cache", return_value=None):
            result = build_iv_feature_panel(iv_raw, rv_panel)

        # VRP and iv_rv_gap: rolling(22) produces first valid at idx 21,
        # then shift(1) pushes to idx 22. So first 22 rows are NaN.
        assert result["vrp"].iloc[:22].isna().all()
        assert result["vrp"].iloc[22:25].notna().any()  # valid data appears
        # vol_of_vix (proxy): 1 log-ret NaN + rolling(22) + shift(1) = first 23 NaN
        assert result["vol_of_vix"].iloc[:23].isna().all()
        assert result["vol_of_vix"].iloc[23:26].notna().any()

    def test_vrp_positive_when_iv_exceeds_rv(self):
        """Sanity: VRP should be positive when IV >> realized vol."""
        from volforecast.data.iv_features import build_iv_feature_panel

        # IV ~30% → IV² = 0.09; RV daily ~0.00002 → annualized = 0.00002*252 = 0.005
        # VRP = 0.09 - 0.005 = 0.085 (clearly positive)
        rng = np.random.default_rng(99)
        n = 60
        idx = pd.bdate_range("2024-01-02", periods=n)
        iv_raw = pd.DataFrame(
            {
                "atm_iv_1m": 0.30 + rng.normal(0, 0.005, n),
                "atm_iv_3m": 0.32 + rng.normal(0, 0.005, n),
                "iv_put_25d_1m": 0.38 + rng.normal(0, 0.005, n),
                "iv_call_25d_1m": 0.25 + rng.normal(0, 0.005, n),
                "skew_1m": 0.13 + rng.normal(0, 0.003, n),
                "vix": 25.0 + np.cumsum(rng.normal(0, 0.2, n)),
            },
            index=pd.DatetimeIndex(idx, name="date"),
        )
        rv_panel = pd.DataFrame(
            {"rv": 0.00002 + np.abs(rng.normal(0, 0.000005, n))},
            index=pd.DatetimeIndex(idx, name="date"),
        )

        result = build_iv_feature_panel(iv_raw, rv_panel)
        valid_vrp = result["vrp"].dropna()
        # Most values should be positive given IV >> RV
        assert (valid_vrp > 0).mean() > 0.8

    def test_index_alignment_with_rv(self):
        """Output index should match rv_panel index."""
        from volforecast.data.iv_features import build_iv_feature_panel

        iv_raw = _make_iv_raw_panel(100)
        rv_panel = _make_rv_panel(100)
        result = build_iv_feature_panel(iv_raw, rv_panel)

        pd.testing.assert_index_equal(result.index, rv_panel.index)
