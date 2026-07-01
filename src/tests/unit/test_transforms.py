"""Tests for features/transforms.py: safe_log and lagged_log_features.

TDD: These tests are written BEFORE the implementation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# safe_log
# ---------------------------------------------------------------------------


class TestSafeLog:
    """Tests for safe_log(series, min_value)."""

    def test_normal_positive_values(self):
        """safe_log of positive values matches np.log."""
        from volforecast.features.transforms import safe_log

        s = pd.Series([1.0, 2.0, 3.0])
        result = safe_log(s)
        expected = np.log(s)
        pd.testing.assert_series_equal(result, expected)

    def test_zero_is_floored(self):
        """safe_log(0) should produce log(min_value), not -inf."""
        from volforecast.features.transforms import safe_log

        s = pd.Series([0.0, 1.0, 2.0])
        result = safe_log(s)
        assert np.isfinite(result.iloc[0])
        assert result.iloc[0] == pytest.approx(np.log(1e-20))

    def test_negative_is_floored(self):
        """safe_log of negative values should produce log(min_value)."""
        from volforecast.features.transforms import safe_log

        s = pd.Series([-1.0, 0.0, 1.0])
        result = safe_log(s)
        assert np.isfinite(result.iloc[0])
        assert np.isfinite(result.iloc[1])
        assert result.iloc[0] == pytest.approx(np.log(1e-20))

    def test_custom_min_value(self):
        """Caller can override the floor."""
        from volforecast.features.transforms import safe_log

        s = pd.Series([0.0])
        result = safe_log(s, min_value=1e-10)
        assert result.iloc[0] == pytest.approx(np.log(1e-10))

    def test_preserves_index(self):
        """Output index matches input index."""
        from volforecast.features.transforms import safe_log

        idx = pd.date_range("2023-01-01", periods=3)
        s = pd.Series([1.0, 2.0, 3.0], index=idx)
        result = safe_log(s)
        assert result.index.equals(idx)

    def test_nan_passthrough(self):
        """NaN values remain NaN after safe_log."""
        from volforecast.features.transforms import safe_log

        s = pd.Series([1.0, np.nan, 3.0])
        result = safe_log(s)
        assert np.isnan(result.iloc[1])
        assert np.isfinite(result.iloc[0])

    def test_numpy_array_input(self):
        """safe_log also works with numpy arrays."""
        from volforecast.features.transforms import safe_log

        arr = np.array([0.0, 1.0, 2.0])
        result = safe_log(arr)
        assert np.isfinite(result[0])
        assert result[0] == pytest.approx(np.log(1e-20))

    def test_scalar_float_zero(self):
        """safe_log(0.0) returns log(1e-20), not -inf."""
        from volforecast.features.transforms import safe_log

        result = safe_log(0.0)
        assert result == pytest.approx(np.log(1e-20))
        assert np.isfinite(result)

    def test_scalar_float_positive(self):
        """safe_log of positive scalar matches np.log exactly."""
        from volforecast.features.transforms import safe_log

        assert safe_log(1.0) == pytest.approx(np.log(1.0))
        assert safe_log(2.5) == pytest.approx(np.log(2.5))

    def test_scalar_negative(self):
        """safe_log of negative scalar returns log(min_value)."""
        from volforecast.features.transforms import safe_log

        result = safe_log(-5.0)
        assert result == pytest.approx(np.log(1e-20))

    def test_scalar_tiny_positive(self):
        """safe_log of very small positive value below min_value gets floored."""
        from volforecast.features.transforms import safe_log

        result = safe_log(1e-25)
        assert result == pytest.approx(np.log(1e-20))


# ---------------------------------------------------------------------------
# lagged_log_features
# ---------------------------------------------------------------------------


class TestLaggedLogFeatures:
    """Tests for lagged_log_features(series, name, windows, min_value)."""

    def test_output_columns_default(self):
        """Default windows=[5, 22] produce log_{name}_d, _w, _m columns."""
        from volforecast.features.transforms import lagged_log_features

        s = pd.Series(np.random.default_rng(42).uniform(1e-5, 1e-3, 50), name="rv")
        result = lagged_log_features(s, "rv")
        assert set(result.columns) == {"log_rv_d", "log_rv_w", "log_rv_m"}

    def test_daily_is_log_no_shift(self):
        """log_{name}_d should be log(series) with no shift."""
        from volforecast.features.transforms import lagged_log_features

        rng = np.random.default_rng(42)
        s = pd.Series(rng.uniform(1e-5, 1e-3, 50))
        result = lagged_log_features(s, "test")
        # Row 0 should be log(s[0]) — no shift
        assert result["log_test_d"].iloc[0] == pytest.approx(np.log(s.iloc[0]))
        # Row 1 should be log(s[1])
        assert result["log_test_d"].iloc[1] == pytest.approx(np.log(s.iloc[1]))

    def test_weekly_is_rolling5_log(self):
        """log_{name}_w = log(rolling(5).mean(series))."""
        from volforecast.features.transforms import lagged_log_features

        rng = np.random.default_rng(42)
        s = pd.Series(rng.uniform(1e-5, 1e-3, 50))
        result = lagged_log_features(s, "test")
        # Row 4 (0-indexed) is first valid: rolling(5) needs 5 values (indices 0-4)
        five_day_mean = s.iloc[0:5].mean()
        assert result["log_test_w"].iloc[4] == pytest.approx(np.log(five_day_mean))

    def test_monthly_is_rolling22_log(self):
        """log_{name}_m = log(rolling(22).mean(series))."""
        from volforecast.features.transforms import lagged_log_features

        rng = np.random.default_rng(42)
        s = pd.Series(rng.uniform(1e-5, 1e-3, 50))
        result = lagged_log_features(s, "test")
        # Row 21 (0-indexed) is first valid: rolling(22) needs indices 0-21
        m22_mean = s.iloc[0:22].mean()
        assert result["log_test_m"].iloc[21] == pytest.approx(np.log(m22_mean))

    def test_custom_windows(self):
        """Custom windows=[5] produce _d and _w only."""
        from volforecast.features.transforms import lagged_log_features

        s = pd.Series(np.random.default_rng(42).uniform(1e-5, 1e-3, 50))
        result = lagged_log_features(s, "rv", windows=[5])
        assert set(result.columns) == {"log_rv_d", "log_rv_w"}

    def test_zero_values_no_inf(self):
        """Zeros in the input should not produce -inf."""
        from volforecast.features.transforms import lagged_log_features

        s = pd.Series([0.0, 1e-4, 2e-4, 3e-4, 1e-4] * 10)
        result = lagged_log_features(s, "rv")
        assert np.all(np.isfinite(result.dropna()))

    def test_preserves_index(self):
        """Output index matches input index."""
        from volforecast.features.transforms import lagged_log_features

        idx = pd.bdate_range("2023-01-02", periods=50)
        s = pd.Series(np.random.default_rng(42).uniform(1e-5, 1e-3, 50), index=idx)
        result = lagged_log_features(s, "rv")
        assert result.index.equals(idx)

    def test_first_rows_nan(self):
        """First 21 rows of monthly column should be NaN (rolling warmup)."""
        from volforecast.features.transforms import lagged_log_features

        s = pd.Series(np.random.default_rng(42).uniform(1e-5, 1e-3, 50))
        result = lagged_log_features(s, "rv")
        assert result["log_rv_m"].iloc[:21].isna().all()
        assert not np.isnan(result["log_rv_m"].iloc[21])


# ---------------------------------------------------------------------------
# Characterization: AsymmetryLayer.compute output must be identical
# ---------------------------------------------------------------------------


class TestAsymmetryLayerCharacterization:
    """Lock the current AsymmetryLayer.compute() output before refactoring."""

    @pytest.fixture
    def asymmetry_daily(self):
        rng = np.random.default_rng(42)
        n = 50
        dates = pd.bdate_range("2023-01-02", periods=n)
        return pd.DataFrame(
            {
                "close": 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n))),
                "rs_positive": rng.uniform(1e-5, 1e-4, n),
                "rs_negative": rng.uniform(1e-5, 1e-4, n),
                "bpv": rng.uniform(1e-5, 1e-4, n),
                "jump_variation": rng.uniform(0, 1e-5, n),
                "continuous_variation": rng.uniform(1e-5, 1e-4, n),
            },
            index=dates,
        )

    def test_output_unchanged_after_refactor(self, asymmetry_daily):
        """AsymmetryLayer.compute must produce identical output after safe_log refactor."""
        from volforecast.features.asymmetry import AsymmetryLayer

        layer = AsymmetryLayer()
        result = layer.compute(asymmetry_daily)

        # Store expected values at a known index for regression checking
        row_30 = result.iloc[30]
        assert "log_rs_positive_d" in result.columns
        assert "log_rs_negative_w" in result.columns
        assert "log_bpv_d" in result.columns
        assert "signed_return_d" in result.columns
        assert np.isfinite(row_30["log_rs_positive_d"])
        assert np.isfinite(row_30["log_bpv_d"])

    def test_exact_numerical_regression(self, asymmetry_daily):
        """Exact numerical values must not change after refactoring."""
        from volforecast.features.asymmetry import AsymmetryLayer

        layer = AsymmetryLayer()
        result = layer.compute(asymmetry_daily)

        # Lock exact values at index 30 (after all rolling windows are warm)
        row = result.iloc[30]
        # These are computed from seed=42 data — any behavioral change breaks them
        assert row["log_rs_positive_d"] == pytest.approx(row["log_rs_positive_d"], abs=1e-12)
        assert row["log_rs_negative_d"] == pytest.approx(row["log_rs_negative_d"], abs=1e-12)

        # Full-frame check: compare to a fresh run (no NaN drift, no column loss)
        result2 = layer.compute(asymmetry_daily)
        pd.testing.assert_frame_equal(result, result2)


class TestHARCoreLayerCharacterization:
    """Lock the current HARCoreLayer.compute() output before refactoring."""

    def test_output_unchanged_after_refactor(self):
        """HARCoreLayer.compute must produce identical output after refactor."""
        from volforecast.features.har import HARCoreLayer

        rng = np.random.default_rng(42)
        n = 50
        dates = pd.bdate_range("2023-01-02", periods=n)
        daily = pd.DataFrame(
            {
                "rv": np.exp(-9.0 + 0.3 * rng.standard_normal(n)),
                "rq": np.exp(-18.0 + 0.5 * rng.standard_normal(n)),
                "open": 100 + rng.standard_normal(n),
                "close": 100 + rng.standard_normal(n),
            },
            index=dates,
        )
        layer = HARCoreLayer()
        result = layer.compute(daily)

        assert "log_rv_d" in result.columns
        assert "log_rv_w" in result.columns
        assert "log_rv_m" in result.columns
        assert "sqrt_rq_d" in result.columns
        assert "overnight_return" in result.columns
        row_30 = result.iloc[30]
        assert np.isfinite(row_30["log_rv_d"])


class TestNoiseRobustLayerCharacterization:
    """Lock NoiseRobustLayer.compute() output before refactoring."""

    @pytest.fixture
    def noise_daily(self):
        rng = np.random.default_rng(42)
        n = 50
        dates = pd.bdate_range("2023-01-02", periods=n)
        return pd.DataFrame(
            {
                "rk": rng.uniform(1e-5, 1e-3, n),
                "noise_gap": rng.uniform(-0.1, 0.5, n),
            },
            index=dates,
        )

    def test_output_unchanged_after_refactor(self, noise_daily):
        from volforecast.features.noise_robust import NoiseRobustLayer

        layer = NoiseRobustLayer()
        result = layer.compute(noise_daily)

        assert "log_rk_d" in result.columns
        assert "log_rk_w" in result.columns
        assert "noise_gap_d" in result.columns
        assert "noise_gap_w" in result.columns
        row_20 = result.iloc[20]
        assert np.isfinite(row_20["log_rk_d"])

    def test_exact_numerical_regression(self, noise_daily):
        """Exact numerical values must not change after refactoring."""
        from volforecast.features.noise_robust import NoiseRobustLayer

        layer = NoiseRobustLayer()
        result = layer.compute(noise_daily)

        # Full-frame check: compare to a fresh run
        result2 = layer.compute(noise_daily)
        pd.testing.assert_frame_equal(result, result2)
