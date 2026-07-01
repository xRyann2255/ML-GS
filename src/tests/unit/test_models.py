"""Tests for model implementations.

Validates:
1. HAR-family har_family: fit/predict round-trip on synthetic data
2. Model coefficients have correct dimensions
3. LightGBM QLIKE gradient/hessian correctness (numerical check)
4. Ridge/Lasso regularization affects coefficients as expected
"""

import numpy as np
import pandas as pd
import pytest

from volforecast.models.har_family import (
    HARModel,
    HARQModel,
    LassoHARModel,
    RidgeHARModel,
    SHARModel,
)


class TestHARModelFitPredict:
    """Basic fit/predict round-trip for HAR model."""

    def test_fit_sets_coefficients(self, sample_feature_df, sample_target):
        X = sample_feature_df[["log_rv_d", "log_rv_w", "log_rv_m"]]
        model = HARModel().fit(X, sample_target)
        assert model.coefficients_ is not None
        assert len(model.coefficients_) == 3
        assert model.intercept_ is not None

    def test_predict_shape(self, sample_feature_df, sample_target):
        X = sample_feature_df[["log_rv_d", "log_rv_w", "log_rv_m"]]
        model = HARModel().fit(X, sample_target)
        preds = model.predict(X)
        assert len(preds) == len(X)

    def test_predict_before_fit_raises(self, sample_feature_df):
        model = HARModel()
        X = sample_feature_df[["log_rv_d", "log_rv_w", "log_rv_m"]]
        with pytest.raises(RuntimeError, match="not been fitted"):
            model.predict(X)

    def test_predictions_correlate_with_target(self, sample_feature_df, sample_target):
        """Predictions should have positive correlation with target."""
        X = sample_feature_df[["log_rv_d", "log_rv_w", "log_rv_m"]]
        model = HARModel().fit(X, sample_target)
        preds = model.predict(X)
        corr = np.corrcoef(preds, sample_target.values)[0, 1]
        assert corr > 0.5  # should be highly correlated on synthetic data

    def test_summary_dict(self, sample_feature_df, sample_target):
        X = sample_feature_df[["log_rv_d", "log_rv_w", "log_rv_m"]]
        model = HARModel().fit(X, sample_target)
        s = model.summary
        assert "intercept" in s
        assert "log_rv_d" in s
        assert "log_rv_w" in s
        assert "log_rv_m" in s


class TestHARQModel:
    def test_fit_with_rq_features(self, sample_feature_df, sample_target):
        X = sample_feature_df.rename(
            columns={
                "rq_rv_interaction": "rq_rv_interaction_d",
            }
        )[["log_rv_d", "log_rv_w", "log_rv_m", "rq_rv_interaction_d"]]
        model = HARQModel().fit(X, sample_target)
        assert model.coefficients_ is not None
        assert len(model.coefficients_) == 4


class TestSHARModel:
    def test_fit_predict(self, sample_feature_df, sample_target):
        rng = np.random.default_rng(55)
        n = len(sample_feature_df)
        X = pd.DataFrame(
            {
                "log_rs_positive_d": -10 + 0.5 * rng.standard_normal(n),
                "log_rs_positive_w": -10 + 0.4 * rng.standard_normal(n),
                "log_rs_positive_m": -10 + 0.3 * rng.standard_normal(n),
                "log_rs_negative_d": -10 + 0.5 * rng.standard_normal(n),
                "log_rs_negative_w": -10 + 0.4 * rng.standard_normal(n),
                "log_rs_negative_m": -10 + 0.3 * rng.standard_normal(n),
            },
            index=sample_feature_df.index,
        )
        model = SHARModel().fit(X, sample_target)
        preds = model.predict(X)
        assert len(preds) == len(X)


class TestRidgeHAR:
    def test_ridge_shrinks_coefficients(self, sample_feature_df, sample_target):
        """Ridge with high alpha should shrink coefficients toward zero."""
        X = sample_feature_df[["log_rv_d", "log_rv_w", "log_rv_m"]]
        ols_model = HARModel().fit(X, sample_target)
        ridge_model = RidgeHARModel(alpha=100.0).fit(X, sample_target)

        ols_norm = np.linalg.norm(ols_model.coefficients_)
        ridge_norm = np.linalg.norm(ridge_model.coefficients_)
        assert ridge_norm < ols_norm

    def test_ridge_still_predicts(self, sample_feature_df, sample_target):
        X = sample_feature_df[["log_rv_d", "log_rv_w", "log_rv_m"]]
        model = RidgeHARModel(alpha=1.0).fit(X, sample_target)
        preds = model.predict(X)
        assert np.all(np.isfinite(preds))


class TestLassoHAR:
    def test_lasso_can_zero_coefficients(self, sample_feature_df, sample_target):
        """Lasso with high alpha may zero out some coefficients."""
        X = sample_feature_df[["log_rv_d", "log_rv_w", "log_rv_m", "rq", "rq_rv_interaction"]]
        model = LassoHARModel(alpha=1.0).fit(X, sample_target)
        # At least one coefficient should be zero (or near-zero) with high alpha
        assert np.any(np.abs(model.coefficients_) < 0.01)

    def test_lasso_predicts(self, sample_feature_df, sample_target):
        X = sample_feature_df[["log_rv_d", "log_rv_w", "log_rv_m"]]
        model = LassoHARModel(alpha=0.01).fit(X, sample_target)
        preds = model.predict(X)
        assert len(preds) == len(X)


class TestFeatureSelection:
    """Verify each model selects only its theoretical features from a full matrix."""

    @pytest.fixture
    def full_feature_df(self):
        """DataFrame with ALL possible feature columns (har_core + asymmetry)."""
        rng = np.random.default_rng(42)
        n = 200
        dates = pd.bdate_range("2020-01-02", periods=n)

        return pd.DataFrame(
            {
                # HAR core
                "log_rv_d": -9 + 0.5 * rng.standard_normal(n),
                "log_rv_w": -9 + 0.4 * rng.standard_normal(n),
                "log_rv_m": -9 + 0.3 * rng.standard_normal(n),
                # HARQ
                "sqrt_rq_d": np.abs(rng.standard_normal(n)) * 1e-4,
                "rq_rv_interaction_d": rng.standard_normal(n) * 1e-4,
                # Asymmetry (semivariances)
                "log_rs_positive_d": -10 + 0.5 * rng.standard_normal(n),
                "log_rs_positive_w": -10 + 0.4 * rng.standard_normal(n),
                "log_rs_positive_m": -10 + 0.3 * rng.standard_normal(n),
                "log_rs_negative_d": -10 + 0.5 * rng.standard_normal(n),
                "log_rs_negative_w": -10 + 0.4 * rng.standard_normal(n),
                "log_rs_negative_m": -10 + 0.3 * rng.standard_normal(n),
                # BPV
                "log_bpv_d": -9 + 0.4 * rng.standard_normal(n),
                "log_bpv_w": -9 + 0.3 * rng.standard_normal(n),
                # Jump / continuous
                "log_jump_d": -15 + rng.standard_normal(n),
                "log_cont_d": -9 + 0.5 * rng.standard_normal(n),
                "log_cont_w": -9 + 0.4 * rng.standard_normal(n),
                # Other
                "signed_return_d": 0.001 * rng.standard_normal(n),
                "overnight_return": 0.001 * rng.standard_normal(n),
                # IV features
                "log_atm_iv_d": -3 + 0.3 * rng.standard_normal(n),
                "log_atm_iv_1w_d": -3 + 0.3 * rng.standard_normal(n),
                "log_atm_iv_0dte_d": -3 + 0.35 * rng.standard_normal(n),
                "log_atm_iv_w": -3 + 0.25 * rng.standard_normal(n),
                "log_atm_iv_m": -3 + 0.2 * rng.standard_normal(n),
                # Noise-robust
                "noise_gap_d": rng.standard_normal(n) * 1e-5,
            },
            index=dates,
        )

    @pytest.fixture
    def full_target(self, full_feature_df):
        rng = np.random.default_rng(77)
        n = len(full_feature_df)
        return pd.Series(
            -9 + 0.5 * rng.standard_normal(n),
            index=full_feature_df.index,
        )

    def test_har_uses_only_3_features(self, full_feature_df, full_target):
        from volforecast.models.har_family import HARModel

        model = HARModel().fit(full_feature_df, full_target)
        assert model._feature_names == ["log_rv_d", "log_rv_w", "log_rv_m"]

    def test_harq_uses_4_features(self, full_feature_df, full_target):
        from volforecast.models.har_family import HARQModel

        model = HARQModel().fit(full_feature_df, full_target)
        assert model._feature_names == [
            "log_rv_d",
            "log_rv_w",
            "log_rv_m",
            "rq_rv_interaction_d",
        ]

    def test_shar_uses_semivariances(self, full_feature_df, full_target):
        from volforecast.models.har_family import SHARModel

        model = SHARModel().fit(full_feature_df, full_target)
        assert model._feature_names == [
            "log_rs_positive_d",
            "log_rs_negative_d",
            "log_rv_w",
            "log_rv_m",
        ]

    def test_har_j_uses_har_plus_jump(self, full_feature_df, full_target):
        from volforecast.models.har_family import HARJModel

        model = HARJModel().fit(full_feature_df, full_target)
        assert model._feature_names == [
            "log_rv_d",
            "log_rv_w",
            "log_rv_m",
            "log_jump_d",
        ]

    def test_har_cj_uses_cont_and_jump(self, full_feature_df, full_target):
        from volforecast.models.har_family import HARCJModel

        model = HARCJModel().fit(full_feature_df, full_target)
        assert model._feature_names == [
            "log_cont_d",
            "log_cont_w",
            "log_rv_m",
            "log_jump_d",
        ]

    def test_ridge_uses_18_har_features(self, full_feature_df, full_target):
        from volforecast.models.har_family import RidgeHARModel

        model = RidgeHARModel().fit(full_feature_df, full_target)
        assert len(model._feature_names) == 18

    def test_lasso_uses_18_har_features(self, full_feature_df, full_target):
        from volforecast.models.har_family import LassoHARModel

        model = LassoHARModel().fit(full_feature_df, full_target)
        assert len(model._feature_names) == 18

    def test_har_ignores_extra_columns(self, full_feature_df, full_target):
        """HAR predictions should be same whether extra columns present or not."""
        from volforecast.models.har_family import HARModel

        model_full = HARModel().fit(full_feature_df, full_target)
        model_slim = HARModel().fit(
            full_feature_df[["log_rv_d", "log_rv_w", "log_rv_m"]], full_target
        )
        preds_full = model_full.predict(full_feature_df)
        preds_slim = model_slim.predict(full_feature_df[["log_rv_d", "log_rv_w", "log_rv_m"]])
        np.testing.assert_allclose(preds_full, preds_slim)

    def test_shar_different_from_har(self, full_feature_df, full_target):
        """SHAR and HAR should produce different predictions on full feature set."""
        from volforecast.models.har_family import HARModel, SHARModel

        har = HARModel().fit(full_feature_df, full_target)
        shar = SHARModel().fit(full_feature_df, full_target)
        preds_har = har.predict(full_feature_df)
        preds_shar = shar.predict(full_feature_df)
        # They use different features, so predictions should differ
        assert not np.allclose(preds_har, preds_shar)

    # --- New hybrid HAR variants ---

    def test_shar_iv_uses_5_features(self, full_feature_df, full_target):
        from volforecast.models.har_family import SHARIVModel

        model = SHARIVModel().fit(full_feature_df, full_target)
        assert model._feature_names == [
            "log_rs_positive_d",
            "log_rs_negative_d",
            "log_rv_w",
            "log_rv_m",
            "log_atm_iv_d",
        ]

    def test_shar_iv_1w_uses_5_features(self, full_feature_df, full_target):
        from volforecast.models.har_family import SHARIV1wModel

        model = SHARIV1wModel().fit(full_feature_df, full_target)
        assert model._feature_names == [
            "log_rs_positive_d",
            "log_rs_negative_d",
            "log_rv_w",
            "log_rv_m",
            "log_atm_iv_1w_d",
        ]

    def test_shar_iv_0dte_uses_5_features(self, full_feature_df, full_target):
        from volforecast.models.har_family import SHARIV0dteModel

        model = SHARIV0dteModel().fit(full_feature_df, full_target)
        assert model._feature_names == [
            "log_rs_positive_d",
            "log_rs_negative_d",
            "log_rv_w",
            "log_rv_m",
            "log_atm_iv_0dte_d",
        ]

    def test_harq_iv_uses_5_features(self, full_feature_df, full_target):
        from volforecast.models.har_family import HARQIVModel

        model = HARQIVModel().fit(full_feature_df, full_target)
        assert model._feature_names == [
            "log_rv_d",
            "log_rv_w",
            "log_rv_m",
            "rq_rv_interaction_d",
            "log_atm_iv_d",
        ]

    def test_harq_iv_1w_uses_5_features(self, full_feature_df, full_target):
        from volforecast.models.har_family import HARQIV1wModel

        model = HARQIV1wModel().fit(full_feature_df, full_target)
        assert model._feature_names == [
            "log_rv_d",
            "log_rv_w",
            "log_rv_m",
            "rq_rv_interaction_d",
            "log_atm_iv_1w_d",
        ]

    def test_har_iv_2tenor_uses_5_features(self, full_feature_df, full_target):
        from volforecast.models.har_family import HARIV2TenorModel

        model = HARIV2TenorModel().fit(full_feature_df, full_target)
        assert model._feature_names == [
            "log_rv_d",
            "log_rv_w",
            "log_rv_m",
            "log_atm_iv_1w_d",
            "log_atm_iv_d",
        ]

    def test_har_iv_noise_uses_5_features(self, full_feature_df, full_target):
        from volforecast.models.har_family import HARIVNoiseModel

        model = HARIVNoiseModel().fit(full_feature_df, full_target)
        assert model._feature_names == [
            "log_rv_d",
            "log_rv_w",
            "log_rv_m",
            "log_atm_iv_d",
            "noise_gap_d",
        ]

    def test_har_cj_iv_0dte_uses_5_features(self, full_feature_df, full_target):
        from volforecast.models.har_family import HARCJIVOdteModel

        model = HARCJIVOdteModel().fit(full_feature_df, full_target)
        assert model._feature_names == [
            "log_cont_d",
            "log_cont_w",
            "log_rv_m",
            "log_jump_d",
            "log_atm_iv_0dte_d",
        ]

    def test_shar_iv_different_from_har_iv(self, full_feature_df, full_target):
        """SHAR-IV and HAR-IV should produce different predictions."""
        from volforecast.models.har_family import HARIVModel, SHARIVModel

        har_iv = HARIVModel().fit(full_feature_df, full_target)
        shar_iv = SHARIVModel().fit(full_feature_df, full_target)
        preds_har_iv = har_iv.predict(full_feature_df)
        preds_shar_iv = shar_iv.predict(full_feature_df)
        assert not np.allclose(preds_har_iv, preds_shar_iv)

    def test_shar_cj_iv_0dte_uses_6_features(self, full_feature_df, full_target):
        from volforecast.models.har_family import SHARCJIVOdteModel

        model = SHARCJIVOdteModel().fit(full_feature_df, full_target)
        assert model._feature_names == [
            "log_rs_positive_d",
            "log_rs_negative_d",
            "log_cont_w",
            "log_rv_m",
            "log_jump_d",
            "log_atm_iv_0dte_d",
        ]

    def test_sharq_cj_iv_0dte_uses_7_features(self, full_feature_df, full_target):
        from volforecast.models.har_family import SHARQCJIVOdteModel

        model = SHARQCJIVOdteModel().fit(full_feature_df, full_target)
        assert model._feature_names == [
            "log_rs_positive_d",
            "log_rs_negative_d",
            "log_cont_w",
            "log_rv_m",
            "log_jump_d",
            "rq_rv_interaction_d",
            "log_atm_iv_0dte_d",
        ]

    def test_new_variants_registered(self):
        from volforecast.registry import MODEL_REGISTRY, ensure_registered

        ensure_registered()
        for name in [
            "shar_iv", "shar_iv_1w", "shar_iv_0dte",
            "harq_iv", "harq_iv_1w",
            "har_iv_2tenor", "har_iv_noise",
            "har_cj_iv_0dte",
            "shar_cj_iv_0dte", "sharq_cj_iv_0dte",
        ]:
            assert name in MODEL_REGISTRY, f"{name} not registered"

    def test_regularized_variants_registered(self):
        from volforecast.registry import MODEL_REGISTRY, ensure_registered

        ensure_registered()
        bases = [
            "shar_iv", "shar_iv_1w", "shar_iv_0dte",
            "harq_iv", "harq_iv_1w",
            "har_iv_2tenor", "har_iv_noise",
            "har_cj_iv_0dte",
            "shar_cj_iv_0dte", "sharq_cj_iv_0dte",
        ]
        for base in bases:
            for prefix in ["ridge", "lasso", "elasticnet"]:
                reg_name = f"{prefix}_{base}"
                assert reg_name in MODEL_REGISTRY, f"{reg_name} not registered"

    def test_ridge_shar_iv_fits_and_predicts(self, full_feature_df, full_target):
        from volforecast.registry import MODEL_REGISTRY, ensure_registered

        ensure_registered()
        cls = MODEL_REGISTRY["ridge_shar_iv"]
        model = cls().fit(full_feature_df, full_target)
        preds = model.predict(full_feature_df)
        assert len(preds) == len(full_feature_df)
        assert model._feature_names == [
            "log_rs_positive_d",
            "log_rs_negative_d",
            "log_rv_w",
            "log_rv_m",
            "log_atm_iv_d",
        ]


class TestNaiveModels:
    """Verify naive baseline models implement the pipeline interface correctly."""

    @pytest.fixture
    def feature_df(self):
        rng = np.random.default_rng(42)
        n = 100
        return pd.DataFrame(
            {
                "log_rv_d": -9 + 0.5 * rng.standard_normal(n),
                "log_rv_w": -9 + 0.4 * rng.standard_normal(n),
                "log_rv_m": -9 + 0.3 * rng.standard_normal(n),
            },
            index=pd.bdate_range("2020-01-02", periods=n),
        )

    @pytest.fixture
    def target(self, feature_df):
        rng = np.random.default_rng(77)
        return pd.Series(
            -9 + 0.5 * rng.standard_normal(len(feature_df)),
            index=feature_df.index,
        )

    def test_random_walk_predicts_log_rv_d(self, feature_df, target):
        from volforecast.models.naive import RandomWalkModel

        model = RandomWalkModel().fit(feature_df, target)
        preds = model.predict(feature_df)
        np.testing.assert_array_equal(preds, feature_df["log_rv_d"].values)

    def test_same_day_rv_predicts_log_rv_d(self, feature_df, target):
        from volforecast.models.naive import SameDayRVModel

        model = SameDayRVModel().fit(feature_df, target)
        preds = model.predict(feature_df)
        np.testing.assert_array_equal(preds, feature_df["log_rv_d"].values)

    def test_historical_mean_predicts_constant(self, feature_df, target):
        from volforecast.models.naive import HistoricalMeanModel

        model = HistoricalMeanModel().fit(feature_df, target)
        preds = model.predict(feature_df)
        expected = target.mean()
        assert np.allclose(preds, expected)

    def test_rolling_mean_predicts_log_rv_m(self, feature_df, target):
        from volforecast.models.naive import RollingMeanModel

        model = RollingMeanModel().fit(feature_df, target)
        preds = model.predict(feature_df)
        np.testing.assert_array_equal(preds, feature_df["log_rv_m"].values)

    def test_naive_models_registered(self):
        from volforecast.registry import MODEL_REGISTRY, ensure_registered

        ensure_registered()
        assert "random_walk" in MODEL_REGISTRY
        assert "same_day_rv" in MODEL_REGISTRY
        assert "historical_mean" in MODEL_REGISTRY
        assert "rolling_mean" in MODEL_REGISTRY
        assert "median_rv" in MODEL_REGISTRY
        assert "ewma" in MODEL_REGISTRY
        assert "ar1" in MODEL_REGISTRY
        assert "vix_implied" in MODEL_REGISTRY

    def test_median_rv_predicts_median(self, feature_df, target):
        from volforecast.models.naive import MedianRVModel

        model = MedianRVModel().fit(feature_df, target)
        preds = model.predict(feature_df)
        expected = float(target.median())
        assert np.allclose(preds, expected)

    def test_ewma_predicts_recursively(self, feature_df, target):
        from volforecast.models.naive import EWMAModel

        model = EWMAModel(lam=0.94).fit(feature_df, target)
        preds = model.predict(feature_df)
        # First prediction should be the last EWMA of training set
        assert preds.shape == (len(feature_df),)
        # EWMA should produce smooth predictions (no NaN)
        assert not np.any(np.isnan(preds))
        # Verify recursion: pred[1] = 0.94 * pred[0] + 0.06 * log_rv_d[0]
        log_rv_d = feature_df["log_rv_d"].values
        expected_1 = 0.94 * preds[0] + 0.06 * log_rv_d[0]
        assert np.isclose(preds[1], expected_1)

    def test_ar1_fits_ols(self, feature_df, target):
        from volforecast.models.naive import AR1Model

        model = AR1Model().fit(feature_df, target)
        preds = model.predict(feature_df)
        assert preds.shape == (len(feature_df),)
        # Should have phi ~0 and intercept ~ mean(target) for random data
        assert model._phi != 0.0 or model._intercept != 0.0
        # Verify: pred = intercept + phi * log_rv_d
        expected = model._intercept + model._phi * feature_df["log_rv_d"].values
        np.testing.assert_allclose(preds, expected)

    def test_vix_implied_fallback_without_vix(self, feature_df, target):
        from volforecast.models.naive import VIXImpliedModel

        # No log_vix_d in features — should fall back to training mean
        model = VIXImpliedModel().fit(feature_df, target)
        preds = model.predict(feature_df)
        expected = float(target.mean())
        assert np.allclose(preds, expected)

    def test_vix_implied_with_vix_feature(self, target):
        from volforecast.models.naive import VIXImpliedModel

        n = len(target)
        # VIX ~20 -> log(20) ~ 3.0
        df_with_vix = pd.DataFrame(
            {
                "log_rv_d": -9 + 0.5 * np.random.default_rng(42).standard_normal(n),
                "log_vix_d": np.full(n, np.log(20.0)),
            },
            index=target.index,
        )
        model = VIXImpliedModel().fit(df_with_vix, target)
        preds = model.predict(df_with_vix)
        # VIX=20 -> daily var = (20/100)^2 / 252 = 0.04/252
        # log(0.04/252) = log(0.04) - log(252) ~ -3.219 - 5.529 ~ -8.748
        expected = 2 * (np.log(20.0) - np.log(100)) - np.log(252)
        assert np.allclose(preds, expected)


class TestQLIKEObjectiveGradients:
    """Verify custom QLIKE objective gradient/hessian via numerical differentiation."""

    def test_gradient_direction(self):
        """Gradient of QLIKE w.r.t. y_pred.

        d/dy_pred [exp(y_true - y_pred) - (y_true - y_pred) - 1]
        = -exp(y_true - y_pred) + 1

        When y_pred < y_true (under-prediction): gradient < 0 (push pred up)
        When y_pred > y_true (over-prediction): gradient > 0 (push pred down)
        """
        from volforecast.models.lightgbm import qlike_objective

        y_true = np.array([-8.0, -9.0, -10.0])

        # Under-predict (y_pred < y_true)
        y_pred_under = y_true - 1.0

        class _FakeDS:
            def get_label(self):
                return y_true

        grad, _ = qlike_objective(y_pred_under, _FakeDS())
        # Gradient should be negative (push prediction up)
        assert np.all(grad < 0)

    def test_hessian_positive(self):
        """Hessian of QLIKE w.r.t. y_pred should be positive (convex).

        d²/dy_pred² = exp(y_true - y_pred) > 0 always.
        """
        from volforecast.models.lightgbm import qlike_objective

        y_true = np.array([-8.0, -9.0, -10.0])
        y_pred = np.array([-8.5, -8.8, -10.5])

        class _FakeDS:
            def get_label(self):
                return y_true

        _, hess = qlike_objective(y_pred, _FakeDS())
        assert np.all(hess > 0)

    def test_numerical_gradient_check(self):
        """Numerical gradient check: finite differences ≈ analytic gradient."""
        from volforecast.models.lightgbm import qlike_objective

        y_true = np.array([-8.5, -9.2, -10.1, -8.8])
        y_pred = np.array([-8.3, -9.5, -9.8, -9.0])

        class _FakeDS:
            def get_label(self):
                return y_true

        grad, _ = qlike_objective(y_pred, _FakeDS())

        # Numerical gradient via central differences
        eps = 1e-5
        numerical_grad = np.zeros_like(y_pred)
        for i in range(len(y_pred)):
            y_plus = y_pred.copy()
            y_minus = y_pred.copy()
            y_plus[i] += eps
            y_minus[i] -= eps
            # Per-element QLIKE
            loss_plus = np.exp(y_true[i] - y_plus[i]) - (y_true[i] - y_plus[i]) - 1
            loss_minus = np.exp(y_true[i] - y_minus[i]) - (y_true[i] - y_minus[i]) - 1
            numerical_grad[i] = (loss_plus - loss_minus) / (2 * eps)

        np.testing.assert_allclose(grad, numerical_grad, atol=1e-4)


# ---------------------------------------------------------------------------
# Composite model regression tests
# ---------------------------------------------------------------------------

lgb = pytest.importorskip("lightgbm")


@pytest.fixture
def composite_data():
    """Synthetic tabular data suitable for composite models (HAR + LightGBM).

    Uses HAR features (log_rv_d/w/m) with a linear + nonlinear DGP so both
    sub-models have signal. 2000 rows ensures enough data for holdout splits.
    """
    rng = np.random.default_rng(42)
    n = 2000
    log_rv_d = rng.normal(-8, 1, n)
    log_rv_w = rng.normal(-8, 0.5, n)
    log_rv_m = rng.normal(-8, 0.3, n)

    y = (
        0.4 * log_rv_d
        + 0.2 * log_rv_w
        + 0.1 * log_rv_m
        + 0.05 * np.abs(log_rv_d - log_rv_w)
        + rng.normal(0, 0.2, n)
    )

    X = pd.DataFrame(
        {"log_rv_d": log_rv_d, "log_rv_w": log_rv_w, "log_rv_m": log_rv_m},
        index=pd.bdate_range("2016-01-04", periods=n),
    )
    return X, pd.Series(y, index=X.index, name="target")


@pytest.fixture(autouse=True)
def _register():
    from volforecast.registry import ensure_registered

    ensure_registered()


class TestStackingHARLightGBM:
    def test_fit_predict_roundtrip(self, composite_data):
        from volforecast.models.stacking import StackingHARLightGBM

        X, y = composite_data
        model = StackingHARLightGBM(
            blend_fraction=0.20,
            blend_purge_gap=5,
            n_estimators=20,
            val_fraction=0.0,
        )
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == len(X)
        assert np.all(np.isfinite(preds))

    def test_fallback_on_small_data(self, composite_data):
        from volforecast.models.stacking import StackingHARLightGBM

        X, y = composite_data
        # Use only 50 rows — too small for blend holdout
        X_small, y_small = X.iloc[:50], y.iloc[:50]
        model = StackingHARLightGBM(
            blend_fraction=0.20,
            blend_purge_gap=10,
            n_estimators=10,
            val_fraction=0.0,
        )
        model.fit(X_small, y_small)
        assert getattr(model, "_fallback", False) is True
        preds = model.predict(X_small)
        assert len(preds) == len(X_small)


class TestCalibratedLightGBM:
    def test_fit_predict_roundtrip(self, composite_data):
        from volforecast.models.calibrated import CalibratedLightGBM

        X, y = composite_data
        model = CalibratedLightGBM(
            cal_fraction=0.15,
            cal_purge_gap=5,
            n_estimators=20,
            val_fraction=0.0,
        )
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == len(X)
        assert np.all(np.isfinite(preds))

    def test_calibration_adjusts_slope(self, composite_data):
        from volforecast.models.calibrated import CalibratedLightGBM

        X, y = composite_data
        model = CalibratedLightGBM(
            cal_fraction=0.15,
            cal_purge_gap=5,
            n_estimators=20,
            val_fraction=0.0,
        )
        model.fit(X, y)
        # Calibration slope should be near 1.0 (not exactly 1.0 unless skipped)
        assert model._cal_slope != 1.0 or model._cal_intercept != 0.0


class TestRegimeBlendModel:
    def test_fit_predict_roundtrip(self, composite_data):
        from volforecast.models.regime_blend import RegimeBlendModel

        X, y = composite_data
        model = RegimeBlendModel(
            blend_strategy="fixed_regime",
            n_estimators=20,
            val_fraction=0.0,
        )
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == len(X)
        assert np.all(np.isfinite(preds))

    def test_val_calibrated_strategy(self, composite_data):
        from volforecast.models.regime_blend import RegimeBlendModel

        X, y = composite_data
        model = RegimeBlendModel(
            blend_strategy="val_calibrated",
            val_fraction=0.20,
            val_purge_gap=5,
            n_estimators=20,
        )
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == len(X)
        # Calibrated weights should have been set
        assert model._calibrated_w_low is not None
        assert model._calibrated_w_high is not None


# ---------------------------------------------------------------------------
# HAR-IV + Cross-Asset Models (trial-031c)
# ---------------------------------------------------------------------------


class TestHARIVXAssetModels:
    """Test har_iv_xasset and ridge_har_iv_xasset models."""

    @pytest.fixture
    def xasset_df(self):
        """DataFrame with HAR core + IV + cross-asset columns."""
        rng = np.random.default_rng(42)
        n = 500
        dates = pd.bdate_range("2018-01-02", periods=n)
        return pd.DataFrame(
            {
                "log_rv_d": -9.0 + 0.5 * rng.standard_normal(n),
                "log_rv_w": -9.0 + 0.4 * rng.standard_normal(n),
                "log_rv_m": -9.0 + 0.3 * rng.standard_normal(n),
                "log_atm_iv_d": -3.0 + 0.3 * rng.standard_normal(n),
                "treasury_slope_d": 0.01 * rng.standard_normal(n),
                "treasury_slope_w": 0.01 * rng.standard_normal(n),
                "log_fx_vol_d": -4.0 + 0.2 * rng.standard_normal(n),
                "log_fx_vol_w": -4.0 + 0.2 * rng.standard_normal(n),
                "log_commodity_vol_cl_d": -3.5 + 0.3 * rng.standard_normal(n),
                "log_vix_d": 2.8 + 0.3 * rng.standard_normal(n),
                "log_vix_w": 2.8 + 0.3 * rng.standard_normal(n),
                "log_vix_m": 2.8 + 0.2 * rng.standard_normal(n),
                "log_vix_rv_ratio_d": 0.5 + 0.4 * rng.standard_normal(n),
            },
            index=dates,
        )

    @pytest.fixture
    def xasset_target(self, xasset_df):
        rng = np.random.default_rng(77)
        n = len(xasset_df)
        target = (
            -1.0
            + 0.4 * xasset_df["log_rv_d"].values
            + 0.3 * xasset_df["log_rv_w"].values
            + 0.2 * xasset_df["log_rv_m"].values
            + 0.1 * xasset_df["log_atm_iv_d"].values
            + 0.2 * rng.standard_normal(n)
        )
        return pd.Series(target, index=xasset_df.index, name="log_rv_target")

    def test_har_iv_xasset_fit_predict(self, xasset_df, xasset_target):
        from volforecast.models.har_family import HARIVXAssetModel

        features = [
            "log_rv_d",
            "log_rv_w",
            "log_rv_m",
            "log_atm_iv_d",
            "treasury_slope_d",
            "log_fx_vol_d",
            "log_commodity_vol_cl_d",
            "log_vix_rv_ratio_d",
        ]
        X = xasset_df[features]
        model = HARIVXAssetModel().fit(X, xasset_target)
        preds = model.predict(X)
        assert len(preds) == len(X)
        assert model.coefficients_ is not None
        assert len(model.coefficients_) == 8

    def test_ridge_har_iv_xasset_fit_predict(self, xasset_df, xasset_target):
        from volforecast.models.har_family import RidgeHARIVXAssetModel

        features = [
            "log_rv_d",
            "log_rv_w",
            "log_rv_m",
            "log_atm_iv_d",
            "treasury_slope_d",
            "treasury_slope_w",
            "log_fx_vol_d",
            "log_fx_vol_w",
            "log_commodity_vol_cl_d",
            "log_vix_d",
            "log_vix_w",
            "log_vix_m",
            "log_vix_rv_ratio_d",
        ]
        X = xasset_df[features]
        model = RidgeHARIVXAssetModel(alpha=1.0).fit(X, xasset_target)
        preds = model.predict(X)
        assert len(preds) == len(X)
        assert np.all(np.isfinite(preds))

    def test_registered_in_model_registry(self):
        from volforecast.models import MODEL_REGISTRY

        assert "har_iv_xasset" in MODEL_REGISTRY
        assert "ridge_har_iv_xasset" in MODEL_REGISTRY


class TestRegularizedHARIV:
    """Tests for Ridge/Lasso/ElasticNet HAR-IV models."""

    @pytest.fixture
    def iv_feature_df(self):
        """Feature DataFrame with HAR core + IV columns."""
        rng = np.random.default_rng(42)
        n = 500
        dates = pd.bdate_range("2019-01-02", periods=n)
        log_rv_d = -9.0 + 0.5 * rng.standard_normal(n)
        log_rv_w = -9.0 + 0.4 * rng.standard_normal(n)
        log_rv_m = -9.0 + 0.3 * rng.standard_normal(n)
        log_atm_iv_d = -3.0 + 0.3 * rng.standard_normal(n)
        log_atm_iv_1w_d = -3.0 + 0.3 * rng.standard_normal(n)
        log_atm_iv_0dte_d = -3.0 + 0.4 * rng.standard_normal(n)
        return pd.DataFrame(
            {
                "log_rv_d": log_rv_d,
                "log_rv_w": log_rv_w,
                "log_rv_m": log_rv_m,
                "log_atm_iv_d": log_atm_iv_d,
                "log_atm_iv_1w_d": log_atm_iv_1w_d,
                "log_atm_iv_0dte_d": log_atm_iv_0dte_d,
            },
            index=dates,
        )

    @pytest.fixture
    def iv_target(self, iv_feature_df):
        rng = np.random.default_rng(77)
        n = len(iv_feature_df)
        target = (
            -1.0
            + 0.3 * iv_feature_df["log_rv_d"].values
            + 0.2 * iv_feature_df["log_rv_w"].values
            + 0.1 * iv_feature_df["log_rv_m"].values
            + 0.4 * iv_feature_df["log_atm_iv_d"].values
            + 0.2 * rng.standard_normal(n)
        )
        return pd.Series(target, index=iv_feature_df.index, name="log_rv_target")

    def test_har_iv_0dte_fit_predict(self, iv_feature_df, iv_target):
        from volforecast.models.har_family import HARIV0dteModel

        model = HARIV0dteModel().fit(iv_feature_df, iv_target)
        assert model.coefficients_ is not None
        assert len(model.coefficients_) == 4
        preds = model.predict(iv_feature_df)
        assert len(preds) == len(iv_feature_df)
        assert np.all(np.isfinite(preds))
        # Verify it uses 0DTE IV, not 1m or 1w
        assert "log_atm_iv_0dte_d" in model._feature_names
        assert "log_atm_iv_d" not in model._feature_names
        assert "log_atm_iv_1w_d" not in model._feature_names

    def test_ridge_har_iv_fit_predict(self, iv_feature_df, iv_target):
        from volforecast.models.har_family import RidgeHARIVModel

        model = RidgeHARIVModel(alpha=1.0).fit(iv_feature_df, iv_target)
        assert model.coefficients_ is not None
        assert len(model.coefficients_) == 4
        preds = model.predict(iv_feature_df)
        assert len(preds) == len(iv_feature_df)
        assert np.all(np.isfinite(preds))

    def test_ridge_har_iv_1w_fit_predict(self, iv_feature_df, iv_target):
        from volforecast.models.har_family import RidgeHARIV1wModel

        model = RidgeHARIV1wModel(alpha=1.0).fit(iv_feature_df, iv_target)
        assert model.coefficients_ is not None
        assert len(model.coefficients_) == 4
        preds = model.predict(iv_feature_df)
        assert len(preds) == len(iv_feature_df)
        assert np.all(np.isfinite(preds))

    def test_lasso_har_iv_fit_predict(self, iv_feature_df, iv_target):
        from volforecast.models.har_family import LassoHARIVModel

        model = LassoHARIVModel(alpha=0.01).fit(iv_feature_df, iv_target)
        assert model.coefficients_ is not None
        assert len(model.coefficients_) == 4
        preds = model.predict(iv_feature_df)
        assert len(preds) == len(iv_feature_df)
        assert np.all(np.isfinite(preds))

    def test_lasso_har_iv_1w_fit_predict(self, iv_feature_df, iv_target):
        from volforecast.models.har_family import LassoHARIV1wModel

        model = LassoHARIV1wModel(alpha=0.01).fit(iv_feature_df, iv_target)
        assert model.coefficients_ is not None
        assert len(model.coefficients_) == 4
        preds = model.predict(iv_feature_df)
        assert len(preds) == len(iv_feature_df)
        assert np.all(np.isfinite(preds))

    def test_elasticnet_har_iv_fit_predict(self, iv_feature_df, iv_target):
        from volforecast.models.har_family import ElasticNetHARIVModel

        model = ElasticNetHARIVModel(alpha=0.01, l1_ratio=0.5).fit(iv_feature_df, iv_target)
        assert model.coefficients_ is not None
        assert len(model.coefficients_) == 4
        preds = model.predict(iv_feature_df)
        assert len(preds) == len(iv_feature_df)
        assert np.all(np.isfinite(preds))

    def test_elasticnet_har_iv_1w_fit_predict(self, iv_feature_df, iv_target):
        from volforecast.models.har_family import ElasticNetHARIV1wModel

        model = ElasticNetHARIV1wModel(alpha=0.01, l1_ratio=0.5).fit(iv_feature_df, iv_target)
        assert model.coefficients_ is not None
        assert len(model.coefficients_) == 4
        preds = model.predict(iv_feature_df)
        assert len(preds) == len(iv_feature_df)
        assert np.all(np.isfinite(preds))

    def test_ridge_shrinks_vs_ols_har_iv(self, iv_feature_df, iv_target):
        """Ridge with high alpha should shrink coefficients vs OLS HAR-IV."""
        from volforecast.models.har_family import HARIVModel, RidgeHARIVModel

        ols = HARIVModel().fit(iv_feature_df, iv_target)
        ridge = RidgeHARIVModel(alpha=100.0).fit(iv_feature_df, iv_target)
        assert np.linalg.norm(ridge.coefficients_) < np.linalg.norm(ols.coefficients_)

    def test_lasso_can_zero_coefficients(self, iv_feature_df, iv_target):
        """Lasso with high alpha should zero out some coefficients."""
        from volforecast.models.har_family import LassoHARIVModel

        model = LassoHARIVModel(alpha=1.0).fit(iv_feature_df, iv_target)
        assert np.any(np.abs(model.coefficients_) < 0.001)

    def test_elasticnet_between_ridge_and_lasso(self, iv_feature_df, iv_target):
        """ElasticNet (l1_ratio=0.5) should produce coefficients between pure Ridge and Lasso."""
        from volforecast.models.har_family import (
            ElasticNetHARIVModel,
            LassoHARIVModel,
            RidgeHARIVModel,
        )

        ridge = RidgeHARIVModel(alpha=0.01).fit(iv_feature_df, iv_target)
        lasso = LassoHARIVModel(alpha=0.01).fit(iv_feature_df, iv_target)
        enet = ElasticNetHARIVModel(alpha=0.01, l1_ratio=0.5).fit(iv_feature_df, iv_target)
        # ElasticNet norm should be between Ridge and Lasso norms
        ridge_norm = np.linalg.norm(ridge.coefficients_)
        lasso_norm = np.linalg.norm(lasso.coefficients_)
        enet_norm = np.linalg.norm(enet.coefficients_)
        lo = min(ridge_norm, lasso_norm)
        hi = max(ridge_norm, lasso_norm)
        assert lo <= enet_norm <= hi * 1.1  # small tolerance

    def test_ridge_har_iv_0dte_fit_predict(self, iv_feature_df, iv_target):
        from volforecast.models.har_family import RidgeHARIV0dteModel

        model = RidgeHARIV0dteModel(alpha=1.0).fit(iv_feature_df, iv_target)
        assert model.coefficients_ is not None
        assert len(model.coefficients_) == 4
        preds = model.predict(iv_feature_df)
        assert len(preds) == len(iv_feature_df)
        assert np.all(np.isfinite(preds))
        assert "log_atm_iv_0dte_d" in model._feature_names

    def test_lasso_har_iv_0dte_fit_predict(self, iv_feature_df, iv_target):
        from volforecast.models.har_family import LassoHARIV0dteModel

        model = LassoHARIV0dteModel(alpha=0.01).fit(iv_feature_df, iv_target)
        assert model.coefficients_ is not None
        assert len(model.coefficients_) == 4
        preds = model.predict(iv_feature_df)
        assert len(preds) == len(iv_feature_df)
        assert np.all(np.isfinite(preds))
        assert "log_atm_iv_0dte_d" in model._feature_names

    def test_elasticnet_har_iv_0dte_fit_predict(self, iv_feature_df, iv_target):
        from volforecast.models.har_family import ElasticNetHARIV0dteModel

        model = ElasticNetHARIV0dteModel(alpha=0.01, l1_ratio=0.5).fit(iv_feature_df, iv_target)
        assert model.coefficients_ is not None
        assert len(model.coefficients_) == 4
        preds = model.predict(iv_feature_df)
        assert len(preds) == len(iv_feature_df)
        assert np.all(np.isfinite(preds))
        assert "log_atm_iv_0dte_d" in model._feature_names

    def test_registered_in_model_registry(self):
        from volforecast.models import MODEL_REGISTRY

        for name in [
            "har_iv_0dte",
            "ridge_har_iv",
            "ridge_har_iv_1w",
            "ridge_har_iv_0dte",
            "lasso_har_iv",
            "lasso_har_iv_1w",
            "lasso_har_iv_0dte",
            "elasticnet_har_iv",
            "elasticnet_har_iv_1w",
            "elasticnet_har_iv_0dte",
        ]:
            assert name in MODEL_REGISTRY, f"{name} not in MODEL_REGISTRY"


class TestHARXIvRich:
    """Tests for HAR-X IV Rich models (tenor-matched, trial-035)."""

    @pytest.fixture
    def harx_feature_df(self):
        """DataFrame with all features needed by HAR-X IV Rich models."""
        rng = np.random.default_rng(42)
        n = 500
        dates = pd.bdate_range("2019-01-02", periods=n)
        return pd.DataFrame(
            {
                "log_rv_d": -9.0 + 0.5 * rng.standard_normal(n),
                "log_rv_w": -9.0 + 0.4 * rng.standard_normal(n),
                "log_rv_m": -9.0 + 0.3 * rng.standard_normal(n),
                "log_vix_d": 2.8 + 0.3 * rng.standard_normal(n),
                "vvix_innovation_d": 0.5 * rng.standard_normal(n),
                "signed_return_d": 0.001 * rng.standard_normal(n),
                "vrp_d": 0.02 + 0.01 * rng.standard_normal(n),
                "log_atm_iv_0dte_d": -3.0 + 0.4 * rng.standard_normal(n),
                "log_atm_iv_1w_d": -3.0 + 0.3 * rng.standard_normal(n),
                "log_atm_iv_d": -3.0 + 0.25 * rng.standard_normal(n),
            },
            index=dates,
        )

    @pytest.fixture
    def harx_target(self, harx_feature_df):
        rng = np.random.default_rng(77)
        n = len(harx_feature_df)
        target = (
            -1.0
            + 0.3 * harx_feature_df["log_rv_d"].values
            + 0.2 * harx_feature_df["log_rv_w"].values
            + 0.4 * harx_feature_df["log_atm_iv_d"].values
            + 0.2 * rng.standard_normal(n)
        )
        return pd.Series(target, index=harx_feature_df.index, name="log_rv_target")

    @pytest.mark.parametrize(
        "model_name",
        [
            "harx_iv_h1",
            "ridge_harx_iv_h1",
            "lasso_harx_iv_h1",
            "elasticnet_harx_iv_h1",
            "harx_iv_h5",
            "ridge_harx_iv_h5",
            "lasso_harx_iv_h5",
            "elasticnet_harx_iv_h5",
            "harx_iv_h22",
            "ridge_harx_iv_h22",
            "lasso_harx_iv_h22",
            "elasticnet_harx_iv_h22",
        ],
    )
    def test_fit_predict(self, harx_feature_df, harx_target, model_name):
        from volforecast.models import MODEL_REGISTRY

        assert model_name in MODEL_REGISTRY
        model_cls = MODEL_REGISTRY[model_name]
        model = model_cls().fit(harx_feature_df, harx_target)
        assert model.coefficients_ is not None
        assert len(model.coefficients_) == 8
        preds = model.predict(harx_feature_df)
        assert len(preds) == len(harx_feature_df)
        assert np.all(np.isfinite(preds))

    def test_h1_uses_0dte_iv(self, harx_feature_df, harx_target):
        from volforecast.models.har_family import HARXIvH1Model

        model = HARXIvH1Model().fit(harx_feature_df, harx_target)
        assert "log_atm_iv_0dte_d" in model._feature_names
        assert "log_atm_iv_1w_d" not in model._feature_names

    def test_h5_uses_1w_iv(self, harx_feature_df, harx_target):
        from volforecast.models.har_family import HARXIvH5Model

        model = HARXIvH5Model().fit(harx_feature_df, harx_target)
        assert "log_atm_iv_1w_d" in model._feature_names
        assert "log_atm_iv_0dte_d" not in model._feature_names

    def test_h22_uses_1m_iv(self, harx_feature_df, harx_target):
        from volforecast.models.har_family import HARXIvH22Model

        model = HARXIvH22Model().fit(harx_feature_df, harx_target)
        assert "log_atm_iv_d" in model._feature_names
        assert "log_atm_iv_0dte_d" not in model._feature_names

    def test_ridge_shrinks_vs_ols(self, harx_feature_df, harx_target):
        from volforecast.models.har_family import HARXIvH22Model, RidgeHARXIvH22Model

        ols = HARXIvH22Model().fit(harx_feature_df, harx_target)
        ridge = RidgeHARXIvH22Model(alpha=100.0).fit(harx_feature_df, harx_target)
        assert np.linalg.norm(ridge.coefficients_) < np.linalg.norm(ols.coefficients_)


class TestHARIVRateVolModels:
    """Test har_iv_ratevol, ridge_har_iv_ratevol, and lasso_har_iv_ratevol."""

    @pytest.fixture
    def ratevol_df(self):
        """DataFrame with HAR core + IV + xasset_rate_vol."""
        rng = np.random.default_rng(42)
        n = 500
        dates = pd.bdate_range("2018-01-02", periods=n)
        return pd.DataFrame(
            {
                "log_rv_d": -9.0 + 0.5 * rng.standard_normal(n),
                "log_rv_w": -9.0 + 0.4 * rng.standard_normal(n),
                "log_rv_m": -9.0 + 0.3 * rng.standard_normal(n),
                "log_atm_iv_d": -3.0 + 0.3 * rng.standard_normal(n),
                "log_atm_iv_1w_d": -3.0 + 0.3 * rng.standard_normal(n),
                "xasset_rate_vol": -4.5 + 0.4 * rng.standard_normal(n),
            },
            index=dates,
        )

    @pytest.fixture
    def ratevol_target(self, ratevol_df):
        rng = np.random.default_rng(77)
        n = len(ratevol_df)
        target = (
            -1.0
            + 0.35 * ratevol_df["log_rv_d"].values
            + 0.25 * ratevol_df["log_rv_w"].values
            + 0.15 * ratevol_df["log_rv_m"].values
            + 0.15 * ratevol_df["log_atm_iv_d"].values
            + 0.10 * ratevol_df["xasset_rate_vol"].values
            + 0.2 * rng.standard_normal(n)
        )
        return pd.Series(target, index=ratevol_df.index, name="log_rv_target")

    def test_har_iv_ratevol_fit_predict(self, ratevol_df, ratevol_target):
        from volforecast.models.har_family import HARIVRateVolModel

        model = HARIVRateVolModel().fit(ratevol_df, ratevol_target)
        preds = model.predict(ratevol_df)
        assert len(preds) == len(ratevol_df)
        assert model.coefficients_ is not None
        assert len(model.coefficients_) == 5
        assert "xasset_rate_vol" in model._feature_names

    def test_har_iv_1w_ratevol_fit_predict(self, ratevol_df, ratevol_target):
        from volforecast.models.har_family import HARIV1wRateVolModel

        model = HARIV1wRateVolModel().fit(ratevol_df, ratevol_target)
        preds = model.predict(ratevol_df)
        assert len(preds) == len(ratevol_df)
        assert "log_atm_iv_1w_d" in model._feature_names
        assert "xasset_rate_vol" in model._feature_names

    def test_ridge_har_iv_ratevol_fit_predict(self, ratevol_df, ratevol_target):
        from volforecast.models.har_family import RidgeHARIVRateVolModel

        model = RidgeHARIVRateVolModel(alpha=1.0).fit(ratevol_df, ratevol_target)
        preds = model.predict(ratevol_df)
        assert len(preds) == len(ratevol_df)
        assert not np.isnan(preds).any()

    def test_lasso_har_iv_ratevol_fit_predict(self, ratevol_df, ratevol_target):
        from volforecast.models.har_family import LassoHARIVRateVolModel

        model = LassoHARIVRateVolModel(alpha=0.01).fit(ratevol_df, ratevol_target)
        preds = model.predict(ratevol_df)
        assert len(preds) == len(ratevol_df)
        assert not np.isnan(preds).any()

    def test_ridge_shrinks_vs_ols(self, ratevol_df, ratevol_target):
        from volforecast.models.har_family import HARIVRateVolModel, RidgeHARIVRateVolModel

        ols = HARIVRateVolModel().fit(ratevol_df, ratevol_target)
        ridge = RidgeHARIVRateVolModel(alpha=100.0).fit(ratevol_df, ratevol_target)
        assert np.linalg.norm(ridge.coefficients_) < np.linalg.norm(ols.coefficients_)
