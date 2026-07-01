"""Tests for the features module: HAR computation, build orchestration, calendar stubs.

Focuses on:
- HAR feature edge cases not covered by test_rv_pipeline.py
- Semivariance additivity and BPV properties
- Jump detection on synthetic paths
- Build layer validation
- Calendar module interface contracts
- CLI entry point (__main__.py)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from volforecast.cli.build_features import build_layer
from volforecast.features.asymmetry import (
    compute_bpv,
    compute_jump_variation,
    compute_realized_tripower_quarticity,
    compute_semivariances,
    detect_jumps,
)
from volforecast.features.calendar import (
    compute_fomc_proximity,
    compute_nfp_proximity,
    compute_opex_proximity,
)
from volforecast.features.har import (
    build_har_design_matrix,
    compute_harq_features,
    compute_realized_variance,
    compute_rq,
)


class TestComputeRealizedVariance:
    """Tests for compute_realized_variance edge cases."""

    def test_known_value(self):
        """RV = sum of squared returns."""
        returns = pd.Series([0.01, -0.02, 0.015])
        expected = 0.01**2 + 0.02**2 + 0.015**2
        assert compute_realized_variance(returns) == pytest.approx(expected)

    def test_single_return(self):
        returns = pd.Series([0.05])
        assert compute_realized_variance(returns) == pytest.approx(0.0025)

    def test_empty_returns_zero(self):
        returns = pd.Series([], dtype=float)
        assert compute_realized_variance(returns) == pytest.approx(0.0)


class TestComputeRQ:
    """Tests for compute_rq."""

    def test_rq_positive(self):
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.001, 78))
        assert compute_rq(returns) > 0

    def test_rq_formula(self):
        """RQ = (N/3) * sum(r^4)."""
        returns = pd.Series([0.01, -0.01, 0.02])
        n = 3
        expected = (n / 3.0) * (0.01**4 + 0.01**4 + 0.02**4)
        assert compute_rq(returns) == pytest.approx(expected)


class TestHARQFeatures:
    """Tests for HARQ feature computation."""

    def test_harq_includes_rq_interaction(self, synthetic_daily_rv_series):
        """HARQ features include sqrt_rq and interaction term."""
        rv_series = np.exp(synthetic_daily_rv_series)  # convert log-RV to RV
        rq_series = rv_series**2 * 3  # synthetic RQ proportional to RV^2
        target_date = rv_series.index[50]

        features = compute_harq_features(rv_series, rq_series, target_date)
        assert "sqrt_rq_d" in features
        assert "rq_rv_interaction_d" in features
        assert features["sqrt_rq_d"] > 0

    def test_harq_insufficient_rq_raises(self, synthetic_daily_rv_series):
        """HARQ raises ValueError if no RQ data available."""
        rv_series = np.exp(synthetic_daily_rv_series)
        rq_series = pd.Series([], dtype=float)
        target_date = rv_series.index[50]

        with pytest.raises(ValueError, match="RQ observation"):
            compute_harq_features(rv_series, rq_series, target_date)


class TestBuildHARDesignMatrix:
    """Tests for build_har_design_matrix."""

    def test_columns_basic(self, synthetic_daily_rv_series):
        rv_series = np.exp(synthetic_daily_rv_series)
        dm = build_har_design_matrix(rv_series)
        assert list(dm.columns) == ["log_rv_d", "log_rv_w", "log_rv_m"]

    def test_columns_with_rq(self, synthetic_daily_rv_series):
        rv_series = np.exp(synthetic_daily_rv_series)
        rq_series = rv_series**2 * 3
        dm = build_har_design_matrix(rv_series, rq_series, include_rq_interaction=True)
        assert "sqrt_rq_d" in dm.columns
        assert "rq_rv_interaction_d" in dm.columns

    def test_first_rows_nan(self, synthetic_daily_rv_series):
        """First 21 rows should have NaN due to monthly rolling window."""
        rv_series = np.exp(synthetic_daily_rv_series)
        dm = build_har_design_matrix(rv_series)
        # rolling(22) produces NaN for rows 0-20, first valid at row 21
        assert dm["log_rv_m"].iloc[:21].isna().all()
        assert not np.isnan(dm["log_rv_m"].iloc[21])

    def test_index_preserved(self, synthetic_daily_rv_series):
        rv_series = np.exp(synthetic_daily_rv_series)
        dm = build_har_design_matrix(rv_series)
        assert dm.index.equals(rv_series.index)


class TestBuildLayer:
    """Tests for build_layer validation."""

    def test_invalid_layer_raises(self):
        """build_layer raises ValueError for layer outside 0-6."""
        with pytest.raises((ValueError, NotImplementedError)):
            build_layer(
                layer=99,
                symbol="SPY",
                start_date="2023-01-01",
                end_date="2023-12-31",
                data_dir=Path("/nonexistent"),
            )


class TestCalendarStubs:
    """Tests verifying calendar module basic interface contracts."""

    def test_fomc_proximity_returns_dataframe(self):
        dates = pd.bdate_range("2024-01-15", periods=5, freq="B")
        result = compute_fomc_proximity(dates)
        assert isinstance(result, pd.DataFrame)
        assert "days_to_fomc" in result.columns

    def test_nfp_proximity_returns_dataframe(self):
        dates = pd.bdate_range("2024-01-15", periods=5, freq="B")
        result = compute_nfp_proximity(dates)
        assert isinstance(result, pd.DataFrame)
        assert "days_to_nfp" in result.columns

    def test_opex_proximity_returns_dataframe(self):
        dates = pd.bdate_range("2024-01-15", periods=5, freq="B")
        result = compute_opex_proximity(dates)
        assert isinstance(result, pd.DataFrame)
        assert "days_to_opex" in result.columns


class TestCLI:
    """Tests for __main__.py CLI."""

    def test_help_returns_zero(self):
        from volforecast.__main__ import main

        assert main([]) == 0


# ---------------------------------------------------------------------------
# Asymmetry features: semivariance, BPV, jump detection
# ---------------------------------------------------------------------------


class TestSemivarianceAdditivity:
    """RS+ + RS- must equal RV (exhaustive partition of returns)."""

    def test_semivariances_sum_to_rv(self, gbm_5min_returns):
        rv = compute_realized_variance(pd.Series(gbm_5min_returns))
        svs = compute_semivariances(pd.Series(gbm_5min_returns))
        assert svs["rs_positive"] + svs["rs_negative"] == pytest.approx(rv, rel=1e-10)

    def test_both_positive(self, gbm_5min_returns):
        svs = compute_semivariances(pd.Series(gbm_5min_returns))
        assert svs["rs_positive"] > 0
        assert svs["rs_negative"] > 0

    def test_signed_jump_definition(self, gbm_5min_returns):
        svs = compute_semivariances(pd.Series(gbm_5min_returns))
        assert svs["signed_jump"] == pytest.approx(
            svs["rs_positive"] - svs["rs_negative"], rel=1e-10
        )

    def test_all_positive_returns(self):
        """When all returns are positive, RS- = 0."""
        r = pd.Series([0.01, 0.02, 0.03])
        svs = compute_semivariances(r)
        assert svs["rs_negative"] == 0.0
        assert svs["rs_positive"] == pytest.approx(0.01**2 + 0.02**2 + 0.03**2)

    def test_semivariance_decomposition_with_zeros(self):
        """Returns containing exact zeros: RS+ + RS- must still equal RV."""
        r = pd.Series([0.01, 0.0, -0.02, 0.0, 0.015, 0.0])
        rv = compute_realized_variance(r)
        svs = compute_semivariances(r)
        assert svs["rs_positive"] + svs["rs_negative"] == pytest.approx(rv, abs=1e-15)

    def test_semivariance_zeros_go_to_positive(self):
        """Zero returns contribute to RS+ (via >= 0 indicator), not RS-."""
        r = pd.Series([0.0, 0.0, 0.0])
        svs = compute_semivariances(r)
        # All returns are zero, so both semivariances should be zero
        assert svs["rs_positive"] == 0.0
        assert svs["rs_negative"] == 0.0
        # With a mix: zero returns squared contribute to RS+ bucket
        r2 = pd.Series([0.0, -0.01])
        svs2 = compute_semivariances(r2)
        # 0^2 goes to RS+ (indicator r>=0), (-0.01)^2 goes to RS-
        assert svs2["rs_positive"] == pytest.approx(0.0, abs=1e-15)
        assert svs2["rs_negative"] == pytest.approx(0.01**2, abs=1e-15)


class TestRealizedTripowerQuarticity:
    """Tests for compute_realized_tripower_quarticity."""

    def test_rtq_positive(self, gbm_5min_returns):
        """RTQ must be positive for any non-degenerate return series."""
        rtq = compute_realized_tripower_quarticity(pd.Series(gbm_5min_returns))
        assert rtq > 0

    def test_rtq_smaller_than_rq_with_jumps(self, jump_5min_returns):
        """RTQ is jump-robust; with jumps present RTQ < RQ."""
        rtq = compute_realized_tripower_quarticity(pd.Series(jump_5min_returns))
        rq = compute_rq(pd.Series(jump_5min_returns))
        assert rtq < rq


class TestBPV:
    def test_bpv_positive(self, gbm_5min_returns):
        bpv = compute_bpv(pd.Series(gbm_5min_returns))
        assert bpv > 0

    def test_bpv_close_to_rv_no_jumps(self, gbm_5min_returns):
        """Under continuous GBM, BPV should be close to RV."""
        rv = compute_realized_variance(pd.Series(gbm_5min_returns))
        bpv = compute_bpv(pd.Series(gbm_5min_returns))
        assert bpv == pytest.approx(rv, rel=0.30)

    def test_bpv_less_than_rv_with_jump(self, jump_5min_returns):
        """BPV should be < RV when jumps are present."""
        rv = compute_realized_variance(pd.Series(jump_5min_returns))
        bpv = compute_bpv(pd.Series(jump_5min_returns))
        assert bpv < rv


class TestJumpDetection:
    def test_detects_jump_in_synthetic(self, jump_5min_returns):
        """BNS test should detect the injected jump.

        Uses TPQ (jump-robust) instead of RQ because RQ is inflated
        by the jump itself, reducing test power.
        """
        rv = compute_realized_variance(pd.Series(jump_5min_returns))
        bpv = compute_bpv(pd.Series(jump_5min_returns))
        tpq = compute_realized_tripower_quarticity(pd.Series(jump_5min_returns))
        n_obs = len(jump_5min_returns)
        result = detect_jumps(rv, bpv, tpq, n_obs, alpha=0.999)
        assert result["jump_indicator"] == 1.0
        # Jump variation should be positive
        jv = compute_jump_variation(rv, bpv, result["jump_indicator"])
        assert jv > 0

    def test_no_false_positive_on_gbm(self, gbm_5min_returns):
        """Pure GBM: if detected, jump variation should be small relative to RV."""
        rv = compute_realized_variance(pd.Series(gbm_5min_returns))
        bpv = compute_bpv(pd.Series(gbm_5min_returns))
        rtq = compute_realized_tripower_quarticity(pd.Series(gbm_5min_returns))
        n_obs = len(gbm_5min_returns)
        result = detect_jumps(rv, bpv, rtq, n_obs)
        if result["jump_indicator"] == 1.0:
            jv = compute_jump_variation(rv, bpv, result["jump_indicator"])
            assert jv < 0.3 * rv


# ---------------------------------------------------------------------------
# Lee-Mykland intraday jump detection
# ---------------------------------------------------------------------------


class TestLeeMykland:
    """Tests for lee_mykland_test intraday jump detection."""

    def test_known_large_return_detected(self):
        """Inject a 5-sigma return into GBM — should be flagged as jump."""
        from volforecast.features.asymmetry import lee_mykland_test

        rng = np.random.default_rng(42)
        # Simulate 78 five-min returns (one day), inject jump at index 40
        returns = pd.Series(rng.normal(0, 0.001, 78))
        returns.iloc[40] = 0.05  # huge relative to sigma=0.001

        result = lee_mykland_test(returns, local_window=20, alpha=0.01)
        assert result["is_jump"].iloc[40]
        assert result["jump_sign"].iloc[40] > 0

    def test_small_returns_not_flagged(self):
        """Pure GBM path: very few or no jumps detected."""
        from volforecast.features.asymmetry import lee_mykland_test

        rng = np.random.default_rng(123)
        returns = pd.Series(rng.normal(0, 0.001, 78))

        result = lee_mykland_test(returns, local_window=20, alpha=0.01)
        # In a pure GBM path, expect very few jumps (at 1% level)
        assert result["is_jump"].sum() <= 3

    def test_short_series_raises(self):
        """Series shorter than local_window should raise ValueError."""
        from volforecast.features.asymmetry import lee_mykland_test

        returns = pd.Series([0.001] * 10)
        with pytest.raises(ValueError, match="local_window"):
            lee_mykland_test(returns, local_window=20)

    def test_output_columns(self):
        """Output DataFrame has required columns."""
        from volforecast.features.asymmetry import lee_mykland_test

        rng = np.random.default_rng(7)
        returns = pd.Series(rng.normal(0, 0.001, 78))

        result = lee_mykland_test(returns, local_window=20)
        expected_cols = {"return", "test_stat", "threshold", "is_jump", "jump_size", "jump_sign"}
        assert expected_cols == set(result.columns)
        assert len(result) == len(returns)

    def test_negative_jump_detected(self):
        """Large negative return should be detected with negative sign."""
        from volforecast.features.asymmetry import lee_mykland_test

        rng = np.random.default_rng(55)
        returns = pd.Series(rng.normal(0, 0.001, 78))
        returns.iloc[50] = -0.04

        result = lee_mykland_test(returns, local_window=20, alpha=0.01)
        assert result["is_jump"].iloc[50]
        assert result["jump_sign"].iloc[50] < 0


# ---------------------------------------------------------------------------
# Signed jumps (J+, J-)
# ---------------------------------------------------------------------------


class TestSignedJumps:
    """Tests for compute_signed_jumps."""

    def test_j_pos_plus_j_neg_equals_total(self):
        """J+ + J- should equal total jump variation from flagged returns."""
        from volforecast.features.asymmetry import compute_signed_jumps

        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.001, 78))
        returns.iloc[20] = 0.03  # positive jump
        returns.iloc[60] = -0.02  # negative jump
        flags = pd.Series([False] * 78)
        flags.iloc[20] = True
        flags.iloc[60] = True

        result = compute_signed_jumps(returns, flags)
        total = result["j_positive"] + result["j_negative"]
        expected_total = returns.iloc[20] ** 2 + returns.iloc[60] ** 2
        assert total == pytest.approx(expected_total, rel=1e-10)

    def test_positive_jump_only(self):
        """Only positive jump flagged → j_positive > 0, j_negative == 0."""
        from volforecast.features.asymmetry import compute_signed_jumps

        returns = pd.Series([0.001, 0.05, -0.001, 0.002])
        flags = pd.Series([False, True, False, False])

        result = compute_signed_jumps(returns, flags)
        assert result["j_positive"] == pytest.approx(0.05**2)
        assert result["j_negative"] == 0.0

    def test_no_jumps_both_zero(self):
        """No jumps flagged → both components zero."""
        from volforecast.features.asymmetry import compute_signed_jumps

        returns = pd.Series([0.001, -0.001, 0.002])
        flags = pd.Series([False, False, False])

        result = compute_signed_jumps(returns, flags)
        assert result["j_positive"] == 0.0
        assert result["j_negative"] == 0.0

    def test_negative_jump_only(self):
        """Only negative jump flagged → j_negative > 0, j_positive == 0."""
        from volforecast.features.asymmetry import compute_signed_jumps

        returns = pd.Series([0.001, -0.04, 0.001])
        flags = pd.Series([False, True, False])

        result = compute_signed_jumps(returns, flags)
        assert result["j_negative"] == pytest.approx(0.04**2)
        assert result["j_positive"] == 0.0


# ---------------------------------------------------------------------------
# Issue #4: Lagged signed daily return (AsymmetryLayer)
# ---------------------------------------------------------------------------


class TestLaggedSignedReturn:
    """Tests for signed_return_d in AsymmetryLayer.compute()."""

    def test_signed_return_present_when_close_exists(self):
        """AsymmetryLayer emits signed_return_d when 'close' is in daily_data."""
        from volforecast.features.asymmetry import AsymmetryLayer

        rng = np.random.default_rng(42)
        n = 50
        dates = pd.bdate_range("2023-01-02", periods=n)
        daily = pd.DataFrame(
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
        layer = AsymmetryLayer()
        result = layer.compute(daily)
        assert "signed_return_d" in result.columns

    def test_signed_return_positive_when_price_rises(self):
        """Positive close-to-close return → positive signed_return_d at same row."""
        from volforecast.features.asymmetry import AsymmetryLayer

        dates = pd.bdate_range("2023-01-02", periods=5)
        daily = pd.DataFrame(
            {
                "close": [100.0, 105.0, 103.0, 108.0, 106.0],
                "rs_positive": [1e-4] * 5,
                "rs_negative": [1e-4] * 5,
                "bpv": [1e-4] * 5,
                "jump_variation": [0.0] * 5,
                "continuous_variation": [1e-4] * 5,
            },
            index=dates,
        )
        layer = AsymmetryLayer()
        result = layer.compute(daily)
        # Return from day 0 to day 1 is log(105/100) > 0, available at day 1
        assert result["signed_return_d"].iloc[1] > 0

    def test_signed_return_shift_alignment(self):
        """signed_return_d at row t uses return from t-1 to t (log(close_t/close_{t-1}))."""
        from volforecast.features.asymmetry import AsymmetryLayer

        dates = pd.bdate_range("2023-01-02", periods=5)
        closes = [100.0, 110.0, 90.0, 95.0, 100.0]
        daily = pd.DataFrame(
            {
                "close": closes,
                "rs_positive": [1e-4] * 5,
                "rs_negative": [1e-4] * 5,
                "bpv": [1e-4] * 5,
                "jump_variation": [0.0] * 5,
                "continuous_variation": [1e-4] * 5,
            },
            index=dates,
        )
        layer = AsymmetryLayer()
        result = layer.compute(daily)
        # Row 0: NaN (no prior close)
        assert np.isnan(result["signed_return_d"].iloc[0])
        # Row 1: log(110/100) = log(1.1)
        expected = float(np.log(110.0 / 100.0))
        assert result["signed_return_d"].iloc[1] == pytest.approx(expected, rel=1e-10)


# ---------------------------------------------------------------------------
# Issue #5: Standalone sqrt_rq always exposed (HARCoreLayer)
# ---------------------------------------------------------------------------


class TestStandaloneSqrtRQ:
    """Tests for sqrt_rq_d always present in HARCoreLayer output when rq exists."""

    def test_sqrt_rq_present_with_rq_column(self):
        """HARCoreLayer emits sqrt_rq_d when daily_data has 'rq' column."""
        from volforecast.features.har import HARCoreLayer

        rng = np.random.default_rng(42)
        n = 50
        dates = pd.bdate_range("2023-01-02", periods=n)
        daily = pd.DataFrame(
            {
                "rv": np.exp(-9.0 + 0.3 * rng.standard_normal(n)),
                "rq": np.exp(-18.0 + 0.5 * rng.standard_normal(n)),
            },
            index=dates,
        )
        layer = HARCoreLayer()
        result = layer.compute(daily)
        assert "sqrt_rq_d" in result.columns

    def test_sqrt_rq_correct_value(self):
        """sqrt_rq_d should be sqrt(rq) shifted by 1."""
        from volforecast.features.har import HARCoreLayer

        dates = pd.bdate_range("2023-01-02", periods=30)
        rv = np.full(30, 1e-4)
        rq = np.full(30, 4e-8)  # sqrt = 2e-4
        daily = pd.DataFrame({"rv": rv, "rq": rq}, index=dates)
        layer = HARCoreLayer()
        result = layer.compute(daily)
        # Row 1: sqrt(4e-8) = 2e-4, shifted by 1 from row 0
        assert result["sqrt_rq_d"].iloc[1] == pytest.approx(2e-4, rel=1e-10)

    def test_sqrt_rq_absent_without_rq(self):
        """No rq column → no sqrt_rq_d in output."""
        from volforecast.features.har import HARCoreLayer

        rng = np.random.default_rng(42)
        n = 50
        dates = pd.bdate_range("2023-01-02", periods=n)
        daily = pd.DataFrame(
            {"rv": np.exp(-9.0 + 0.3 * rng.standard_normal(n))},
            index=dates,
        )
        layer = HARCoreLayer()
        result = layer.compute(daily)
        assert "sqrt_rq_d" not in result.columns


# ---------------------------------------------------------------------------
# Issue #8: Overnight return (HARCoreLayer)
# ---------------------------------------------------------------------------


class TestOvernightReturn:
    """Tests for overnight_return in HARCoreLayer.compute()."""

    def test_overnight_return_present(self):
        """HARCoreLayer emits overnight_return when open and close exist."""
        from volforecast.features.har import HARCoreLayer

        rng = np.random.default_rng(42)
        n = 50
        dates = pd.bdate_range("2023-01-02", periods=n)
        close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
        open_ = close * (1 + rng.normal(0, 0.003, n))
        daily = pd.DataFrame(
            {
                "rv": np.exp(-9.0 + 0.3 * rng.standard_normal(n)),
                "open": open_,
                "close": close,
            },
            index=dates,
        )
        layer = HARCoreLayer()
        result = layer.compute(daily)
        assert "overnight_return" in result.columns

    def test_overnight_return_sign(self):
        """open > prior close → positive overnight return."""
        from volforecast.features.har import HARCoreLayer

        dates = pd.bdate_range("2023-01-02", periods=5)
        daily = pd.DataFrame(
            {
                "rv": [1e-4] * 5,
                "open": [100.0, 102.0, 104.0, 99.0, 101.0],
                "close": [101.0, 103.0, 100.0, 100.0, 102.0],
            },
            index=dates,
        )
        layer = HARCoreLayer()
        result = layer.compute(daily)
        # overnight at day 1 = log(open_1 / close_0) = log(102/101) > 0
        # shifted by 1, so available at row 2
        assert result["overnight_return"].iloc[2] > 0

    def test_overnight_return_nan_first_rows(self):
        """First row should be NaN (needs prior close)."""
        from volforecast.features.har import HARCoreLayer

        dates = pd.bdate_range("2023-01-02", periods=5)
        daily = pd.DataFrame(
            {
                "rv": [1e-4] * 5,
                "open": [100.0, 102.0, 104.0, 99.0, 101.0],
                "close": [101.0, 103.0, 100.0, 100.0, 102.0],
            },
            index=dates,
        )
        layer = HARCoreLayer()
        result = layer.compute(daily)
        assert np.isnan(result["overnight_return"].iloc[0])
        # Row 1: log(102/101) > 0 — valid
        assert not np.isnan(result["overnight_return"].iloc[1])

    def test_overnight_absent_without_open(self):
        """No open column → no overnight_return."""
        from volforecast.features.har import HARCoreLayer

        rng = np.random.default_rng(42)
        n = 50
        dates = pd.bdate_range("2023-01-02", periods=n)
        daily = pd.DataFrame(
            {"rv": np.exp(-9.0 + 0.3 * rng.standard_normal(n))},
            index=dates,
        )
        layer = HARCoreLayer()
        result = layer.compute(daily)
        assert "overnight_return" not in result.columns

    def test_overnight_return_dropped_when_corrupted(self):
        """Corrupted overnight return (split mismatch) is NaN-masked, not dropped."""
        from volforecast.features.har import HARCoreLayer

        rng = np.random.default_rng(42)
        n = 50
        dates = pd.bdate_range("2023-01-02", periods=n)
        close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
        # Simulate a 10:1 split at day 25: open jumps down by 10x relative to
        # split-adjusted close → log(open/close_{t-1}) ≈ log(1/10) = -2.3
        open_ = close * (1 + rng.normal(0, 0.003, n))
        open_[25] = close[24] / 10  # split-mismatch corruption
        daily = pd.DataFrame(
            {
                "rv": np.exp(-9.0 + 0.3 * rng.standard_normal(n)),
                "open": open_,
                "close": close,
            },
            index=dates,
        )
        layer = HARCoreLayer()
        result = layer.compute(daily)
        # Column is kept but corrupt value is NaN-masked
        assert "overnight_return" in result.columns
        # The corrupt row (index 25) should be NaN (it uses shift(1) so row 25
        # computes log(open[25] / close[24]) which is the corrupt value)
        assert pd.isna(result["overnight_return"].iloc[25])
        # Non-corrupt values should still be present
        valid_mask = result["overnight_return"].notna()
        # At least some values must be valid (all except first row + corrupt row)
        assert valid_mask.sum() >= n - 3


# ---------------------------------------------------------------------------
# Issue #6: Realized skewness and kurtosis
# ---------------------------------------------------------------------------


class TestRealizedMoments:
    """Tests for compute_realized_moments (Amaya et al. 2015)."""

    def test_known_values_formula(self):
        """Verify against hand computation on small array."""
        from volforecast.features.asymmetry import compute_realized_moments

        r = pd.Series([0.01, -0.02, 0.015])
        n = 3
        mean_r2 = np.mean(r**2)
        mean_r3 = np.mean(r**3)
        mean_r4 = np.mean(r**4)

        expected_skew = np.sqrt(n) * mean_r3 / mean_r2 ** (3 / 2)
        expected_kurt = n * mean_r4 / mean_r2**2

        result = compute_realized_moments(r)
        assert result["realized_skewness"] == pytest.approx(expected_skew, rel=1e-10)
        assert result["realized_kurtosis"] == pytest.approx(expected_kurt, rel=1e-10)

    def test_skew_sign_all_positive(self):
        """All-positive returns → positive skew."""
        from volforecast.features.asymmetry import compute_realized_moments

        r = pd.Series([0.01, 0.02, 0.03, 0.015, 0.025])
        result = compute_realized_moments(r)
        assert result["realized_skewness"] > 0

    def test_skew_sign_all_negative(self):
        """All-negative returns → negative skew."""
        from volforecast.features.asymmetry import compute_realized_moments

        r = pd.Series([-0.01, -0.02, -0.03, -0.015, -0.025])
        result = compute_realized_moments(r)
        assert result["realized_skewness"] < 0

    def test_kurtosis_positive(self):
        """Kurtosis ratio is always positive."""
        from volforecast.features.asymmetry import compute_realized_moments

        rng = np.random.default_rng(42)
        r = pd.Series(rng.normal(0, 0.001, 78))
        result = compute_realized_moments(r)
        assert result["realized_kurtosis"] > 0

    def test_output_keys(self):
        """Output dict has exactly the expected keys."""
        from volforecast.features.asymmetry import compute_realized_moments

        r = pd.Series([0.01, -0.01, 0.02, -0.02, 0.005])
        result = compute_realized_moments(r)
        assert set(result.keys()) == {"realized_skewness", "realized_kurtosis"}


# ---------------------------------------------------------------------------
# New residual-signal features (abs_ret, ret_5d, vol_anomaly, vix_change_x_abs_ret)
# ---------------------------------------------------------------------------


class TestAbsRetFeature:
    """Tests for abs_ret_d in AsymmetryLayer."""

    def test_abs_ret_present(self):
        """AsymmetryLayer emits abs_ret_d when 'close' is in daily_data."""
        from volforecast.features.asymmetry import AsymmetryLayer

        rng = np.random.default_rng(42)
        n = 50
        dates = pd.bdate_range("2023-01-02", periods=n)
        daily = pd.DataFrame(
            {"close": 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))},
            index=dates,
        )
        layer = AsymmetryLayer()
        result = layer.compute(daily)
        assert "abs_ret_d" in result.columns

    def test_abs_ret_equals_abs_signed_return(self):
        """abs_ret_d == |signed_return_d| everywhere."""
        from volforecast.features.asymmetry import AsymmetryLayer

        dates = pd.bdate_range("2023-01-02", periods=5)
        daily = pd.DataFrame(
            {"close": [100.0, 110.0, 90.0, 95.0, 100.0]},
            index=dates,
        )
        layer = AsymmetryLayer()
        result = layer.compute(daily)
        pd.testing.assert_series_equal(
            result["abs_ret_d"],
            result["signed_return_d"].abs(),
            check_names=False,
        )

    def test_abs_ret_always_nonnegative(self):
        """abs_ret_d is always >= 0."""
        from volforecast.features.asymmetry import AsymmetryLayer

        rng = np.random.default_rng(7)
        n = 100
        dates = pd.bdate_range("2023-01-02", periods=n)
        daily = pd.DataFrame(
            {"close": 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n)))},
            index=dates,
        )
        layer = AsymmetryLayer()
        result = layer.compute(daily)
        assert (result["abs_ret_d"].dropna() >= 0).all()


class TestRet5dFeature:
    """Tests for ret_5d in AsymmetryLayer."""

    def test_ret_5d_present(self):
        """AsymmetryLayer emits ret_5d when 'close' is in daily_data."""
        from volforecast.features.asymmetry import AsymmetryLayer

        rng = np.random.default_rng(42)
        n = 50
        dates = pd.bdate_range("2023-01-02", periods=n)
        daily = pd.DataFrame(
            {"close": 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))},
            index=dates,
        )
        layer = AsymmetryLayer()
        result = layer.compute(daily)
        assert "ret_5d" in result.columns

    def test_ret_5d_equals_5day_cumulative_return(self):
        """ret_5d at row t == sum of log returns from t-4 to t."""
        from volforecast.features.asymmetry import AsymmetryLayer

        dates = pd.bdate_range("2023-01-02", periods=10)
        closes = [100, 102, 101, 103, 105, 104, 106, 108, 107, 110]
        daily = pd.DataFrame({"close": closes}, index=dates, dtype=float)
        layer = AsymmetryLayer()
        result = layer.compute(daily)
        # First 4 rows: NaN (need 5 returns but rolling(5) needs 5 valid)
        # Row 5 (idx=5): sum of log returns at positions 1..5
        log_rets = np.log(np.array(closes[1:6]) / np.array(closes[0:5]))
        expected = log_rets.sum()
        assert result["ret_5d"].iloc[5] == pytest.approx(expected, rel=1e-10)


class TestVolAnomalyFeature:
    """Tests for vol_anomaly in NoiseRobustLayer."""

    def test_vol_anomaly_present(self):
        """NoiseRobustLayer emits vol_anomaly when 'n_ticks' is in daily_data."""
        from volforecast.features.noise_robust import NoiseRobustLayer

        rng = np.random.default_rng(42)
        n = 50
        dates = pd.bdate_range("2023-01-02", periods=n)
        daily = pd.DataFrame(
            {"n_ticks": rng.integers(1000, 10000, n)},
            index=dates,
        )
        layer = NoiseRobustLayer()
        result = layer.compute(daily)
        assert "vol_anomaly" in result.columns

    def test_vol_anomaly_mean_near_zero(self):
        """vol_anomaly is a demeaned series, should average near zero."""
        from volforecast.features.noise_robust import NoiseRobustLayer

        rng = np.random.default_rng(42)
        n = 200
        dates = pd.bdate_range("2023-01-02", periods=n)
        daily = pd.DataFrame(
            {"n_ticks": rng.integers(5000, 6000, n)},
            index=dates,
        )
        layer = NoiseRobustLayer()
        result = layer.compute(daily)
        # After warm-up (22 days), mean should be near zero
        mean_val = result["vol_anomaly"].iloc[22:].mean()
        assert abs(mean_val) < 0.05

    def test_vol_anomaly_spike_positive(self):
        """A spike in tick count produces positive vol_anomaly."""
        from volforecast.features.noise_robust import NoiseRobustLayer

        dates = pd.bdate_range("2023-01-02", periods=30)
        ticks = [5000] * 29 + [15000]  # spike on last day
        daily = pd.DataFrame({"n_ticks": ticks}, index=dates)
        layer = NoiseRobustLayer()
        result = layer.compute(daily)
        # Last row should be positive (above 22-day mean)
        assert result["vol_anomaly"].iloc[-1] > 0


class TestVixChangeXAbsRet:
    """Tests for vix_change_x_abs_ret in OptionsLayer."""

    def test_interaction_present(self):
        """OptionsLayer emits vix_change_x_abs_ret when vix and abs_ret_d available."""
        from volforecast.features.options import OptionsLayer

        rng = np.random.default_rng(42)
        n = 50
        dates = pd.bdate_range("2023-01-02", periods=n)
        daily = pd.DataFrame(
            {
                "iv_1m_atm": 20 + rng.normal(0, 2, n),
                "rv": np.exp(-9.0 + 0.3 * rng.standard_normal(n)),
                "vix": 20 + np.cumsum(rng.normal(0, 0.5, n)),
                "abs_ret_d": rng.uniform(0, 0.03, n),
            },
            index=dates,
        )
        layer = OptionsLayer()
        result = layer.compute(daily)
        assert "vix_change_x_abs_ret" in result.columns

    def test_interaction_value(self):
        """vix_change_x_abs_ret == (VIX_t - VIX_{t-1}) * abs_ret_d_t."""
        from volforecast.features.options import OptionsLayer

        dates = pd.bdate_range("2023-01-02", periods=5)
        daily = pd.DataFrame(
            {
                "iv_1m_atm": [20.0, 21.0, 19.0, 22.0, 20.0],
                "rv": [1e-4] * 5,
                "vix": [18.0, 20.0, 19.0, 22.0, 21.0],
                "abs_ret_d": [0.01, 0.02, 0.015, 0.03, 0.01],
            },
            index=dates,
        )
        layer = OptionsLayer()
        result = layer.compute(daily)
        # Row 1: vix_change = 20-18=2, abs_ret = 0.02, product = 0.04
        assert result["vix_change_x_abs_ret"].iloc[1] == pytest.approx(0.04)
        # Row 2: vix_change = 19-20=-1, abs_ret = 0.015, product = -0.015
        assert result["vix_change_x_abs_ret"].iloc[2] == pytest.approx(-0.015)
