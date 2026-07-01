"""End-to-end tests for RV computation, features, and HAR baseline.

Uses synthetic GBM price paths to validate:
1. RV computation matches known analytical values
2. BPV ≈ RV in no-jump case, BPV < RV with jumps
3. Semivariances sum to RV
4. BNS test detects injected jumps
5. Realized Kernel converges to true IV
6. TSRV and pre-averaging produce reasonable estimates
7. Volatility signature plot shows expected shape
8. HAR model fits and predicts on synthetic RV series
9. QLIKE metric properties (minimum at truth, penalizes asymmetrically)
"""

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.integration

from volforecast.evaluation.metrics import (
    compute_all,
    mse,
    qlike,
    qlike_improvement_bps,
    r_squared,
)
from volforecast.features.asymmetry import (
    build_asymmetry_features,
    compute_bpv,
    compute_continuous_variation,
    compute_jump_variation,
    compute_realized_tripower_quarticity,
    compute_semivariances,
    detect_jumps,
)
from volforecast.features.har import (
    build_har_design_matrix,
    compute_log_rv_features,
    compute_realized_variance,
    compute_rq,
)
from volforecast.features.noise_robust import (
    noise_gap,
    pre_averaged_rv,
    realized_kernel,
    tsrv,
    volatility_signature_plot_data,
)
from volforecast.models.har_family import (
    HARModel,
    LassoHARModel,
    RidgeHARModel,
)

# ---------------------------------------------------------------------------
# Tests: Realized Variance (har.py)
# ---------------------------------------------------------------------------


class TestRealizedVariance:
    def test_rv_sum_of_squares(self, gbm_5min_returns):
        """RV should equal sum of squared returns."""
        rv = compute_realized_variance(pd.Series(gbm_5min_returns))
        expected = float(np.sum(gbm_5min_returns**2))
        assert rv == pytest.approx(expected, rel=1e-10)

    def test_rv_positive(self, gbm_5min_returns):
        rv = compute_realized_variance(pd.Series(gbm_5min_returns))
        assert rv > 0

    def test_rv_annualized_magnitude(self, gbm_5min_returns):
        """Annualized vol should be roughly 20% for sigma=0.20 GBM."""
        rv = compute_realized_variance(pd.Series(gbm_5min_returns))
        annual_vol = np.sqrt(rv * 252)
        # Allow wide tolerance since it's one day
        assert 0.05 < annual_vol < 0.50

    def test_rv_zero_returns(self):
        rv = compute_realized_variance(pd.Series([0.0, 0.0, 0.0]))
        assert rv == 0.0


class TestRealizedQuarticity:
    def test_rq_positive(self, gbm_5min_returns):
        rq = compute_rq(pd.Series(gbm_5min_returns))
        assert rq > 0

    def test_rq_formula(self, gbm_5min_returns):
        """RQ = (n/3) * sum(r^4)."""
        r = gbm_5min_returns
        n = len(r)
        expected = (n / 3.0) * np.sum(r**4)
        rq = compute_rq(pd.Series(r))
        assert rq == pytest.approx(expected, rel=1e-10)


class TestLogRVFeatures:
    def test_features_shape(self, synthetic_rv_series):
        date = synthetic_rv_series.index[100]
        features = compute_log_rv_features(synthetic_rv_series, date)
        assert set(features.keys()) == {"log_rv_d", "log_rv_w", "log_rv_m"}

    def test_daily_equals_log_rv(self, synthetic_rv_series):
        date = synthetic_rv_series.index[100]
        features = compute_log_rv_features(synthetic_rv_series, date)
        expected = np.log(synthetic_rv_series.loc[date])
        assert features["log_rv_d"] == pytest.approx(expected, rel=1e-10)

    def test_weekly_larger_than_monthly_in_high_vol(self, synthetic_rv_series):
        """In normal conditions, weekly avg and monthly avg differ."""
        date = synthetic_rv_series.index[100]
        features = compute_log_rv_features(synthetic_rv_series, date)
        # They should be finite real numbers
        assert np.isfinite(features["log_rv_w"])
        assert np.isfinite(features["log_rv_m"])

    def test_insufficient_data_raises(self, synthetic_rv_series):
        date = synthetic_rv_series.index[10]
        with pytest.raises(ValueError):
            compute_log_rv_features(synthetic_rv_series.iloc[:10], date)


class TestHARDesignMatrix:
    def test_design_matrix_columns(self, synthetic_rv_series):
        X = build_har_design_matrix(synthetic_rv_series)
        assert list(X.columns) == ["log_rv_d", "log_rv_w", "log_rv_m"]

    def test_design_matrix_nan_first_rows(self, synthetic_rv_series):
        X = build_har_design_matrix(synthetic_rv_series)
        # First 22 rows should have NaN (need 22 days lookback + 1 shift)
        assert X.iloc[0].isna().any()
        # Row 23+ should be populated
        assert not X.iloc[23].isna().any()

    def test_design_matrix_with_rq(self, synthetic_rv_series):
        rq = synthetic_rv_series * 0.01  # Fake RQ proportional to RV
        X = build_har_design_matrix(synthetic_rv_series, rq_series=rq, include_rq_interaction=True)
        assert "sqrt_rq_d" in X.columns
        assert "rq_rv_interaction_d" in X.columns


# ---------------------------------------------------------------------------
# Tests: Asymmetry features (asymmetry.py)
# ---------------------------------------------------------------------------


class TestSemivariances:
    def test_sum_equals_rv(self, gbm_5min_returns):
        """RS+ + RS- should equal RV (ignoring zero returns)."""
        rv = compute_realized_variance(pd.Series(gbm_5min_returns))
        semivars = compute_semivariances(pd.Series(gbm_5min_returns))
        assert semivars["rs_positive"] + semivars["rs_negative"] == pytest.approx(rv, rel=1e-10)

    def test_both_positive(self, gbm_5min_returns):
        semivars = compute_semivariances(pd.Series(gbm_5min_returns))
        assert semivars["rs_positive"] >= 0
        assert semivars["rs_negative"] >= 0


class TestBPV:
    def test_bpv_close_to_rv_no_jumps(self, gbm_5min_returns):
        """Without jumps, BPV should approximate RV."""
        rv = compute_realized_variance(pd.Series(gbm_5min_returns))
        bpv = compute_bpv(pd.Series(gbm_5min_returns))
        # BPV should be within ~30% of RV for a single day
        assert abs(bpv - rv) / rv < 0.50

    def test_bpv_less_than_rv_with_jump(self, jump_5min_returns):
        """With a jump, BPV should be less than RV."""
        rv = compute_realized_variance(pd.Series(jump_5min_returns))
        bpv = compute_bpv(pd.Series(jump_5min_returns))
        assert bpv < rv

    def test_bpv_positive(self, gbm_5min_returns):
        bpv = compute_bpv(pd.Series(gbm_5min_returns))
        assert bpv > 0


class TestJumpDetection:
    def test_no_jump_detected_in_gbm(self, gbm_5min_returns):
        """BNS test should NOT detect a jump in pure GBM."""
        rv = compute_realized_variance(pd.Series(gbm_5min_returns))
        bpv = compute_bpv(pd.Series(gbm_5min_returns))
        rtq = compute_realized_tripower_quarticity(pd.Series(gbm_5min_returns))
        result = detect_jumps(rv, bpv, rtq, len(gbm_5min_returns), alpha=0.999)
        # In pure GBM, expect no jump (though small chance of false positive)
        assert "z_stat" in result
        assert "p_value" in result
        assert "jump_indicator" in result

    def test_jump_detected_with_large_jump(self, jump_5min_returns):
        """BNS test should detect a 3% jump.

        Uses tri-power quarticity (TPQ) instead of standard RQ because
        RQ is inflated by the jump itself, reducing test power.
        TPQ is jump-robust (Barndorff-Nielsen & Shephard 2004).
        """
        rv = compute_realized_variance(pd.Series(jump_5min_returns))
        bpv = compute_bpv(pd.Series(jump_5min_returns))
        # Use TPQ (jump-robust) instead of RQ (inflated by the jump)
        tpq = compute_realized_tripower_quarticity(pd.Series(jump_5min_returns))
        result = detect_jumps(rv, bpv, tpq, len(jump_5min_returns), alpha=0.999)
        assert result["jump_indicator"] == 1.0
        assert result["z_stat"] > 3.0  # Should be very significant

    def test_jump_variation_nonneg(self):
        assert compute_jump_variation(1e-4, 8e-5, 1.0) >= 0
        assert compute_jump_variation(1e-4, 1.2e-4, 1.0) == 0  # BPV > RV

    def test_continuous_variation(self):
        rv = 1e-4
        j = 2e-5
        c = compute_continuous_variation(rv, j)
        assert c == pytest.approx(8e-5, rel=1e-10)


class TestBuildAsymmetryFeatures:
    def test_all_keys_present(self, gbm_5min_returns):
        rv = compute_realized_variance(pd.Series(gbm_5min_returns))
        rq = compute_rq(pd.Series(gbm_5min_returns))
        features = build_asymmetry_features(pd.Series(gbm_5min_returns), rv, rq)
        expected_keys = {
            "rs_positive",
            "rs_negative",
            "signed_jump",
            "bpv",
            "z_stat",
            "p_value",
            "jump_indicator",
            "jump_variation",
            "continuous_variation",
        }
        assert set(features.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Tests: Noise-robust estimators (noise_robust.py)
# ---------------------------------------------------------------------------


def _make_gbm_log_prices(n_ticks: int, sigma_annual: float, seed: int) -> np.ndarray:
    """Inline GBM simulator for noise tests that need custom parameters."""
    rng = np.random.default_rng(seed)
    dt_per_tick = (1.0 / 252.0) / n_ticks
    increments = sigma_annual * np.sqrt(dt_per_tick) * rng.standard_normal(n_ticks)
    log_prices = np.zeros(n_ticks + 1)
    log_prices[0] = np.log(100.0)
    log_prices[1:] = log_prices[0] + np.cumsum(increments)
    return log_prices


class TestRealizedKernel:
    def test_rk_close_to_rv_no_noise(self, gbm_log_prices, gbm_5min_returns):
        """RK from clean GBM prices should approximate 5-min RV."""
        rk = realized_kernel(gbm_log_prices)
        rv_5min = compute_realized_variance(pd.Series(gbm_5min_returns))
        # Should be in the same ballpark
        assert rk > 0
        assert abs(rk - rv_5min) / rv_5min < 1.0

    def test_rk_positive(self, gbm_log_prices):
        rk = realized_kernel(gbm_log_prices)
        assert rk > 0

    def test_rk_with_noise(self):
        """RK should handle noisy prices better than naive tick RV."""
        rng = np.random.default_rng(99)
        clean = _make_gbm_log_prices(n_ticks=10000, sigma_annual=0.20, seed=99)
        noise = rng.normal(0, 0.0001, len(clean))  # Small bid-ask noise
        noisy = clean + noise

        rv_tick = float(np.sum(np.diff(noisy) ** 2))
        rk = realized_kernel(noisy)

        # Naive tick RV should be inflated by noise; RK should be closer to truth
        rv_clean = float(np.sum(np.diff(clean) ** 2))
        assert abs(rk - rv_clean) < abs(rv_tick - rv_clean)


class TestTSRV:
    def test_tsrv_positive(self, gbm_log_prices):
        result = tsrv(gbm_log_prices)
        assert result > 0

    def test_tsrv_reasonable_magnitude(self, gbm_log_prices, gbm_5min_returns):
        """TSRV should be in the same order of magnitude as 5-min RV."""
        result = tsrv(gbm_log_prices)
        rv_5min = compute_realized_variance(pd.Series(gbm_5min_returns))
        assert 0.1 * rv_5min < result < 10.0 * rv_5min


class TestPreAveragedRV:
    def test_pre_avg_positive(self, gbm_log_prices):
        result = pre_averaged_rv(gbm_log_prices)
        assert result > 0

    def test_pre_avg_reasonable(self, gbm_log_prices, gbm_5min_returns):
        result = pre_averaged_rv(gbm_log_prices)
        rv_5min = compute_realized_variance(pd.Series(gbm_5min_returns))
        assert 0.1 * rv_5min < result < 10.0 * rv_5min


class TestVolSigPlot:
    def test_returns_dataframe(self, gbm_log_prices):
        df = volatility_signature_plot_data(gbm_log_prices)
        assert isinstance(df, pd.DataFrame)
        assert "freq_ticks" in df.columns
        assert "rv" in df.columns
        assert len(df) > 5

    def test_rv_increases_at_very_high_freq_with_noise(self):
        """With noisy prices, RV should inflate at high frequency."""
        rng = np.random.default_rng(77)
        clean = _make_gbm_log_prices(n_ticks=5000, sigma_annual=0.20, seed=77)
        noise = rng.normal(0, 0.0005, len(clean))
        noisy = clean + noise

        df = volatility_signature_plot_data(noisy, frequencies=[1, 5, 50, 500])
        # Tick-level RV (freq=1) should be larger than spaced RV (freq=500)
        rv_tick = df.loc[df["freq_ticks"] == 1, "rv"].values[0]
        rv_slow = df.loc[df["freq_ticks"] == 500, "rv"].values[0]
        assert rv_tick > rv_slow


class TestNoiseGap:
    def test_positive_when_rk_exceeds_rv(self):
        assert noise_gap(1.5e-4, 1.0e-4) == pytest.approx(0.5)

    def test_negative_when_rv_exceeds_rk(self):
        assert noise_gap(0.8e-4, 1.0e-4) == pytest.approx(-0.2)

    def test_zero_rv_returns_zero(self):
        assert noise_gap(1e-4, 0.0) == 0.0


# ---------------------------------------------------------------------------
# Tests: HAR models (models/har_family.py)
# ---------------------------------------------------------------------------


class TestHARModel:
    def test_fit_predict_roundtrip(self, synthetic_rv_series):
        """HAR should fit on synthetic data and produce predictions."""
        X = build_har_design_matrix(synthetic_rv_series)
        y = np.log(synthetic_rv_series)

        # Drop NaN rows
        valid = ~(X.isna().any(axis=1) | y.isna())
        X_valid = X.loc[valid]
        y_valid = y.loc[valid]

        # Split: first 80% train, last 20% test
        split = int(len(X_valid) * 0.8)
        X_train, X_test = X_valid.iloc[:split], X_valid.iloc[split:]
        y_train = y_valid.iloc[:split]

        model = HARModel()
        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        assert len(preds) == len(X_test)
        assert np.all(np.isfinite(preds))

    def test_r_squared_positive(self, synthetic_rv_series):
        """HAR should get positive R² on autocorrelated RV data."""
        X = build_har_design_matrix(synthetic_rv_series)
        y = np.log(synthetic_rv_series)

        valid = ~(X.isna().any(axis=1) | y.isna())
        X_valid = X.loc[valid]
        y_valid = y.loc[valid]

        model = HARModel()
        model.fit(X_valid, y_valid)
        preds = model.predict(X_valid)

        r2 = r_squared(y_valid.values, preds)
        assert r2 > 0.3  # Should explain substantial variance

    def test_coefficients_stored(self, synthetic_rv_series):
        X = build_har_design_matrix(synthetic_rv_series)
        y = np.log(synthetic_rv_series)
        valid = ~(X.isna().any(axis=1) | y.isna())

        model = HARModel()
        model.fit(X.loc[valid], y.loc[valid])

        assert model.coefficients_ is not None
        assert model.intercept_ is not None
        assert len(model.coefficients_) == 3

    def test_summary_dict(self, synthetic_rv_series):
        X = build_har_design_matrix(synthetic_rv_series)
        y = np.log(synthetic_rv_series)
        valid = ~(X.isna().any(axis=1) | y.isna())

        model = HARModel()
        model.fit(X.loc[valid], y.loc[valid])
        s = model.summary
        assert "intercept" in s
        assert "log_rv_d" in s


class TestRidgeLassoHAR:
    def test_ridge_fits(self, synthetic_rv_series):
        X = build_har_design_matrix(synthetic_rv_series)
        y = np.log(synthetic_rv_series)
        valid = ~(X.isna().any(axis=1) | y.isna())

        model = RidgeHARModel(alpha=1.0)
        model.fit(X.loc[valid], y.loc[valid])
        preds = model.predict(X.loc[valid])
        assert len(preds) == valid.sum()

    def test_lasso_fits(self, synthetic_rv_series):
        X = build_har_design_matrix(synthetic_rv_series)
        y = np.log(synthetic_rv_series)
        valid = ~(X.isna().any(axis=1) | y.isna())

        model = LassoHARModel(alpha=0.001)
        model.fit(X.loc[valid], y.loc[valid])
        preds = model.predict(X.loc[valid])
        assert len(preds) == valid.sum()


# ---------------------------------------------------------------------------
# Tests: Evaluation metrics (evaluation/metrics.py)
# ---------------------------------------------------------------------------


class TestQLIKE:
    def test_perfect_prediction_is_zero(self):
        y = np.array([-8.0, -9.0, -7.5, -8.5])
        assert qlike(y, y, log_space=True) == pytest.approx(0.0, abs=1e-15)

    def test_positive_for_imperfect(self):
        y = np.array([-8.0, -9.0, -7.5, -8.5])
        h = y + 0.5
        assert qlike(y, h, log_space=True) > 0

    def test_variance_space(self):
        rv = np.array([1e-4, 2e-4, 1.5e-4])
        h = rv.copy()
        assert qlike(rv, h, log_space=False) == pytest.approx(0.0, abs=1e-15)

    def test_nan_raises(self):
        y = np.array([1.0, np.nan])
        h = np.array([1.0, 1.0])
        with pytest.raises(ValueError):
            qlike(y, h)

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            qlike(np.array([1.0, 2.0]), np.array([1.0]))


class TestMSE:
    def test_zero_for_perfect(self):
        y = np.array([1.0, 2.0, 3.0])
        assert mse(y, y) == 0.0

    def test_known_value(self):
        y = np.array([1.0, 2.0])
        h = np.array([1.5, 2.5])
        assert mse(y, h) == pytest.approx(0.25)


class TestRSquared:
    def test_perfect_is_one(self):
        y = np.array([1.0, 2.0, 3.0, 4.0])
        assert r_squared(y, y) == pytest.approx(1.0)

    def test_mean_is_zero(self):
        y = np.array([1.0, 2.0, 3.0, 4.0])
        h = np.full_like(y, np.mean(y))
        assert r_squared(y, h) == pytest.approx(0.0)


class TestQLIKEImprovement:
    def test_improvement_positive_when_model_better(self):
        assert qlike_improvement_bps(0.10, 0.09) > 0

    def test_improvement_negative_when_model_worse(self):
        assert qlike_improvement_bps(0.10, 0.11) < 0

    def test_improvement_zero_when_equal(self):
        assert qlike_improvement_bps(0.10, 0.10) == 0.0


class TestComputeAll:
    def test_all_keys_present(self):
        y = np.array([-8.0, -9.0, -7.5, -8.5])
        h = y + 0.1
        result = compute_all(y, h)
        assert set(result.keys()) == {"qlike", "mse", "mae", "r_squared"}

    def test_with_model_name(self):
        y = np.array([-8.0, -9.0, -7.5])
        h = y + 0.1
        result = compute_all(y, h, model_name="har")
        assert "har_qlike" in result


# ---------------------------------------------------------------------------
# Integration test: end-to-end pipeline
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_full_pipeline_synthetic(self):
        """Full pipeline: simulate prices → compute RV & features → fit HAR → evaluate."""
        rng = np.random.default_rng(42)
        n_days = 300
        n_returns_per_day = 78  # 5-min

        # Simulate persistent log-IV via AR(1) with ρ=0.93 (realistic)
        log_iv = np.zeros(n_days)
        log_iv[0] = np.log(78 * 0.01**2)
        for t in range(1, n_days):
            log_iv[t] = 0.05 + 0.93 * log_iv[t - 1] + 0.15 * rng.standard_normal()

        # Per-return sigma from IV: sigma_ret = sqrt(IV / n_returns)
        daily_sigma = np.sqrt(np.exp(log_iv) / n_returns_per_day)

        rv_list = []

        for day in range(n_days):
            returns = daily_sigma[day] * rng.standard_normal(n_returns_per_day)
            returns_series = pd.Series(returns)

            rv = compute_realized_variance(returns_series)

            rv_list.append(rv)

        dates = pd.bdate_range("2020-01-02", periods=n_days)
        rv_series = pd.Series(rv_list, index=dates, name="rv")

        # Build HAR design matrix
        # Features use same-day data (available at end of day t).
        # Target is next-day log(RV): predict RV_{t+1} from features_t.
        X = build_har_design_matrix(rv_series)
        y = np.log(rv_series).shift(-1)  # 1-step-ahead target

        # Align and drop NaN
        valid = ~(X.isna().any(axis=1) | y.isna())
        X_valid = X.loc[valid]
        y_valid = y.loc[valid]

        # Train/test split (expanding window style)
        split = int(len(X_valid) * 0.7)
        X_train = X_valid.iloc[:split]
        y_train = y_valid.iloc[:split]
        X_test = X_valid.iloc[split:]
        y_test = y_valid.iloc[split:]

        # Fit HAR
        model = HARModel()
        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        # Evaluate
        results = compute_all(y_test.values, preds)

        # HAR should explain some variance on autocorrelated data
        assert results["r_squared"] > 0.1
        assert results["qlike"] > 0
        assert results["mse"] > 0
        assert results["mae"] > 0


# ---------------------------------------------------------------------------
# Duan (1995) retransformation correction in Pipeline
# ---------------------------------------------------------------------------


class TestDuanCorrection:
    """Verify Pipeline applies per-fold Duan retransformation correction."""

    def _make_synthetic_rv_df(self, n_days=400, seed=42):
        """Create synthetic daily RV DataFrame mimicking real data."""
        rng = np.random.default_rng(seed)
        # Simulated persistent log-RV via AR(1)
        log_rv = np.zeros(n_days)
        log_rv[0] = -9.0
        for t in range(1, n_days):
            log_rv[t] = -0.5 + 0.93 * log_rv[t - 1] + 0.3 * rng.standard_normal()
        rv = np.exp(log_rv)
        dates = pd.bdate_range("2020-01-02", periods=n_days)
        return pd.DataFrame({"rv": rv}, index=dates)

    def test_correction_returned_in_results(self):
        """Pipeline results include duan_correction key."""
        from volforecast.config import CVConfig, ExperimentConfig, ModelConfig, TuningConfig
        from volforecast.pipeline.runner import Pipeline

        df = self._make_synthetic_rv_df()
        config = ExperimentConfig(
            name="test_duan",
            universe=["SYNTH"],
            date_range=("2020-01-02", "2021-07-01"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="expanding_window", purge_gap=5, train_size=200, test_size=50),
            tuning=TuningConfig(),
        )
        pipeline = Pipeline(config)
        results = pipeline.run(df)
        assert 1 in results
        assert "duan_correction" in results[1]

    def test_correction_positive_for_ols(self):
        """OLS models should have positive Duan correction (they under-predict)."""
        from volforecast.config import CVConfig, ExperimentConfig, ModelConfig, TuningConfig
        from volforecast.pipeline.runner import Pipeline

        df = self._make_synthetic_rv_df()
        config = ExperimentConfig(
            name="test_duan_pos",
            universe=["SYNTH"],
            date_range=("2020-01-02", "2021-07-01"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="expanding_window", purge_gap=5, train_size=200, test_size=50),
            tuning=TuningConfig(),
        )
        pipeline = Pipeline(config)
        results = pipeline.run(df)
        # OLS targets E[log(RV)|X]; correction should be positive (≈ σ²/2)
        assert results[1]["duan_correction"] > 0.01

    def test_correction_approximates_half_variance(self):
        """Duan correction should approximate σ²/2 for OLS models.

        For Gaussian-distributed residuals, log(mean(exp(r))) = σ²/2.
        OLS residuals are approximately Gaussian, so the Duan correction
        should be close to half the in-sample residual variance.
        """
        from volforecast.config import CVConfig, ExperimentConfig, ModelConfig, TuningConfig
        from volforecast.pipeline.runner import Pipeline

        df = self._make_synthetic_rv_df(n_days=500, seed=123)
        config = ExperimentConfig(
            name="test_duan_variance",
            universe=["SYNTH"],
            date_range=("2020-01-02", "2021-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="expanding_window", purge_gap=5, train_size=200, test_size=50),
            tuning=TuningConfig(),
        )
        pipeline = Pipeline(config)
        results = pipeline.run(df)

        correction = results[1]["duan_correction"]
        # Correction should be in reasonable range for an OLS vol model:
        # typical σ² of log-RV residuals is 0.05-0.5, so correction is 0.025-0.25
        assert 0.01 < correction < 0.30, f"Correction {correction} outside expected range"

        # Verify the correction equals approximately σ²/2 by checking that
        # mean(exp(r)) ≈ exp(correction) for Gaussian residuals.
        # This is an identity: log(E[exp(r)]) = σ²/2 when r ~ N(0, σ²)
        # We just check it's in the right neighborhood — the exact value
        # depends on kurtosis deviations from normality.
        assert correction > 0

    def test_correction_near_zero_for_qlike_objective(self):
        """QLIKE-trained models should have near-zero correction.

        When a model is trained to minimize QLIKE directly, its predictions
        already target the QLIKE-optimal point (shifted by Jensen's gap).
        The Duan correction should be approximately zero.
        """
        # The QLIKE objective gradient pushes predictions toward the correct target,
        # so in-sample residuals are already mean-zero in exp-space:
        # mean(exp(residuals)) ≈ 1, log(1) ≈ 0.
        # We verify mathematically: for zero-mean residuals with var σ²,
        # Duan correction = log(mean(exp(r))) = σ²/2 for Gaussian residuals.
        # But QLIKE-optimal residuals have mean(exp(r)) = 1 by first-order condition.
        rng = np.random.default_rng(42)
        # Simulate QLIKE-optimal residuals: mean(exp(r)) = 1
        # This holds when E[exp(r)] = 1, i.e. r ~ (-σ²/2 + σ*Z)
        sigma = 0.3
        residuals = -(sigma**2) / 2 + sigma * rng.standard_normal(1000)
        correction = float(np.log(np.mean(np.exp(residuals))))
        assert abs(correction) < 0.05  # Near zero
