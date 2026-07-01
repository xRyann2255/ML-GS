"""Tests for the triple expansion utility (features/expansion.py).

Validates:
1. Output shape: 3 columns per input series
2. Known values: change and z-score correctness
3. NaN handling at edges
4. Custom window parameter
5. Constant series: z-score NaN (zero std)
6. TreeExpansionLayer prefix filtering (calendar exclusion)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.features.expansion import triple_expand
from volforecast.features.tree_expansion import _EXPANDABLE_PREFIXES, TreeExpansionLayer


class TestTripleExpandShape:
    """Output shape must be 3 columns with correct names."""

    def test_output_shape_3x(self):
        s = pd.Series(np.arange(100, dtype=float), name="log_rv_d")
        result = triple_expand(s)
        assert result.shape == (100, 3)

    def test_column_names(self):
        s = pd.Series(np.arange(50, dtype=float), name="sqrt_rq")
        result = triple_expand(s)
        assert list(result.columns) == ["sqrt_rq_level", "sqrt_rq_change", "sqrt_rq_zscore"]

    def test_index_preserved(self):
        idx = pd.bdate_range("2023-01-02", periods=60)
        s = pd.Series(np.random.default_rng(1).normal(size=60), index=idx, name="bpv")
        result = triple_expand(s)
        assert result.index.equals(idx)


class TestTripleExpandKnownValues:
    """Verify change and z-score against hand computation."""

    def test_change_known(self):
        s = pd.Series([1.0, 3.0, 6.0, 10.0], name="x")
        result = triple_expand(s, window=3)
        # change = x_t - x_{t-1}
        expected_change = [np.nan, 2.0, 3.0, 4.0]
        pd.testing.assert_series_equal(
            result["x_change"], pd.Series(expected_change, name="x_change"), check_names=True
        )

    def test_zscore_known(self):
        # 5 values with window=3: z = (x - rolling_mean) / rolling_std
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], name="v")
        result = triple_expand(s, window=3)
        # At index 2 (first valid): mean=2.0, std=1.0, z=(3-2)/1 = 1.0
        assert result["v_zscore"].iloc[2] == pytest.approx(1.0)
        # At index 3: mean=3.0, std=1.0, z=(4-3)/1 = 1.0
        assert result["v_zscore"].iloc[3] == pytest.approx(1.0)

    def test_level_equals_input(self):
        s = pd.Series([2.5, 3.5, 4.5], name="foo")
        result = triple_expand(s)
        pd.testing.assert_series_equal(
            result["foo_level"], pd.Series([2.5, 3.5, 4.5], name="foo_level")
        )


class TestTripleExpandNaN:
    """NaN handling at edges."""

    def test_change_first_row_nan(self):
        s = pd.Series(np.ones(30), name="a")
        result = triple_expand(s, window=5)
        assert np.isnan(result["a_change"].iloc[0])

    def test_zscore_nan_before_window(self):
        s = pd.Series(np.arange(30, dtype=float), name="b")
        result = triple_expand(s, window=10)
        # First 9 rows (0..8) should be NaN for z-score (need 10 obs)
        assert result["b_zscore"].iloc[:9].isna().all()
        # Row 9 should be valid
        assert not np.isnan(result["b_zscore"].iloc[9])


class TestTripleExpandCustomWindow:
    """Custom window parameter affects z-score computation."""

    def test_window_5_vs_20(self):
        rng = np.random.default_rng(42)
        s = pd.Series(rng.normal(0, 1, 100), name="x")
        r5 = triple_expand(s, window=5)
        r20 = triple_expand(s, window=20)
        # Different windows produce different z-scores
        valid_idx = 20  # both valid at this point
        assert r5["x_zscore"].iloc[valid_idx] != pytest.approx(
            r20["x_zscore"].iloc[valid_idx], abs=1e-6
        )


class TestTripleExpandConstant:
    """Constant series: zero std → NaN z-score."""

    def test_constant_series_zscore_nan(self):
        s = pd.Series([5.0] * 30, name="c")
        result = triple_expand(s, window=10)
        # std = 0 → NaN z-score for all valid-window rows
        assert result["c_zscore"].iloc[10:].isna().all()

    def test_constant_series_change_zero(self):
        s = pd.Series([5.0] * 30, name="c")
        result = triple_expand(s, window=10)
        # change should be 0 after first row
        assert (result["c_change"].iloc[1:] == 0.0).all()


class TestTreeExpansionLayerFiltering:
    """TreeExpansionLayer should exclude calendar/categorical columns."""

    @pytest.fixture
    def mixed_base_features(self) -> pd.DataFrame:
        """Base features mixing continuous (expandable) and calendar (excluded)."""
        n = 50
        rng = np.random.default_rng(99)
        idx = pd.bdate_range("2023-01-02", periods=n)
        return pd.DataFrame(
            {
                # Expandable: match _EXPANDABLE_PREFIXES
                "log_rv_d": rng.normal(-8, 1, n),
                "log_rv_w": rng.normal(-8, 0.8, n),
                "sqrt_rq_d": rng.uniform(0.001, 0.01, n),
                "overnight_return": rng.normal(0, 0.005, n),
                # Calendar: should NOT be expanded
                "days_to_fomc": rng.integers(0, 30, n).astype(float),
                "fomc_week": rng.choice([0, 1], n).astype(float),
                "fomc_day": rng.choice([0, 1], n).astype(float),
                "day_of_week": rng.integers(0, 5, n).astype(float),
                "month": rng.integers(1, 13, n).astype(float),
                "quarter_end": rng.choice([0, 1], n).astype(float),
                "nfp_week": rng.choice([0, 1], n).astype(float),
                "opex_week": rng.choice([0, 1], n).astype(float),
            },
            index=idx,
        )

    def test_calendar_columns_excluded_from_expansion(self, mixed_base_features):
        """Calendar features must not appear as _change or _zscore."""
        layer = TreeExpansionLayer()
        result = layer.compute(mixed_base_features, base_features=mixed_base_features)
        calendar_names = [
            "days_to_fomc",
            "fomc_week",
            "fomc_day",
            "day_of_week",
            "month",
            "quarter_end",
            "nfp_week",
            "opex_week",
        ]
        for cal_col in calendar_names:
            assert f"{cal_col}_change" not in result.columns
            assert f"{cal_col}_zscore" not in result.columns

    def test_continuous_columns_are_expanded(self, mixed_base_features):
        """Continuous features matching prefix list are expanded."""
        layer = TreeExpansionLayer()
        result = layer.compute(mixed_base_features, base_features=mixed_base_features)
        assert "log_rv_d_change" in result.columns
        assert "log_rv_d_zscore" in result.columns
        assert "log_rv_w_change" in result.columns
        assert "sqrt_rq_d_change" in result.columns
        assert "overnight_return_change" in result.columns

    def test_only_expandable_prefixes_produce_output(self, mixed_base_features):
        """All output columns should trace back to expandable prefix features."""
        layer = TreeExpansionLayer()
        result = layer.compute(mixed_base_features, base_features=mixed_base_features)
        for col in result.columns:
            # Strip suffix to get base name
            base = (
                col.rsplit("_change", 1)[0]
                if col.endswith("_change")
                else col.rsplit("_zscore", 1)[0]
            )
            assert any(base.startswith(p) for p in _EXPANDABLE_PREFIXES), (
                f"Column {col} (base={base}) not in expandable prefixes"
            )

    def test_empty_when_only_calendar_features(self):
        """If base_features has only calendar columns, result is empty."""
        n = 30
        idx = pd.bdate_range("2023-06-01", periods=n)
        calendar_only = pd.DataFrame(
            {"day_of_week": range(n), "fomc_day": [0] * n, "month": [6] * n},
            index=idx,
        )
        layer = TreeExpansionLayer()
        result = layer.compute(calendar_only, base_features=calendar_only)
        assert result.shape[1] == 0
