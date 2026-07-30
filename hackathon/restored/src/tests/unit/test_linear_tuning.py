"""Tests for deterministic linear-model alpha grid search (trial-077 infra)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.config import CVConfig


class _FakeRidge:
    """Minimal _BaseOLS-shaped model: predict = shrunken OLS on one feature.

    alpha=0 -> pure OLS slope; alpha -> inf -> slope shrunk to 0 (intercept only).
    Mimics sklearn Ridge on standardized X closely enough for ranking tests.
    """

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self._slope = 0.0
        self._intercept = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series):
        x = X.iloc[:, 0].values
        xc = x - x.mean()
        self._slope = float((xc @ (y.values - y.values.mean())) / (xc @ xc + self.alpha * len(x)))
        self._intercept = float(y.values.mean() - self._slope * x.mean())
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self._intercept + self._slope * X.iloc[:, 0].values


@pytest.fixture
def signal_data():
    """y strongly driven by x -> small alpha must win."""
    rng = np.random.default_rng(42)
    n = 400
    x = rng.normal(-8.0, 1.0, n)
    y = 0.9 * x + rng.normal(0.0, 0.1, n)
    return pd.DataFrame({"f": x}), pd.Series(y)


@pytest.fixture
def inner_cv():
    return CVConfig(method="expanding_window", purge_gap=5, train_size=150, test_size=50)


class TestDuanCorrection:
    def test_matches_runner_formula(self):
        from volforecast.models.linear_tuning import duan_correction

        resid = np.array([0.1, -0.2, 0.3, np.nan])
        valid = resid[~np.isnan(resid)]
        expected = float(np.log(np.mean(np.exp(np.clip(valid, -10.0, 10.0)))))
        assert duan_correction(resid) == pytest.approx(expected)

    def test_empty_returns_zero(self):
        from volforecast.models.linear_tuning import duan_correction

        assert duan_correction(np.array([np.nan, np.nan])) == 0.0


class TestTuneLinearAlpha:
    def test_prefers_small_alpha_on_strong_signal(self, signal_data, inner_cv):
        from volforecast.models.linear_tuning import tune_linear_alpha

        X, y = signal_data
        result = tune_linear_alpha(
            _FakeRidge, X, y, {"alpha": [1e-6, 1e6]}, inner_cv
        )
        assert result is not None
        assert result.best_params["alpha"] == 1e-6

    def test_one_grid_entry_per_combo(self, signal_data, inner_cv):
        from volforecast.models.linear_tuning import tune_linear_alpha

        X, y = signal_data
        result = tune_linear_alpha(
            _FakeRidge, X, y, {"alpha": [0.001, 1.0, 1000.0]}, inner_cv
        )
        assert len(result.grid_results) == 3
        assert all(np.isfinite(r["inner_qlike"]) for r in result.grid_results)
        assert all(r["n_folds"] >= 1 for r in result.grid_results)

    def test_deterministic(self, signal_data, inner_cv):
        from volforecast.models.linear_tuning import tune_linear_alpha

        X, y = signal_data
        r1 = tune_linear_alpha(_FakeRidge, X, y, {"alpha": [0.01, 1.0, 100.0]}, inner_cv)
        r2 = tune_linear_alpha(_FakeRidge, X, y, {"alpha": [0.01, 1.0, 100.0]}, inner_cv)
        assert r1.best_params == r2.best_params
        assert r1.best_inner_qlike == r2.best_inner_qlike

    def test_tie_breaks_toward_larger_alpha(self, inner_cv):
        from volforecast.models.linear_tuning import tune_linear_alpha

        # Pure-noise y with zero slope signal: shrinkage level is irrelevant,
        # so scores tie (or near-tie); ranking must still be deterministic and
        # documented: ties go to MORE regularization.
        rng = np.random.default_rng(0)
        n = 400
        X = pd.DataFrame({"f": np.zeros(n)})  # constant feature -> slope irrelevant
        y = pd.Series(rng.normal(-8.0, 0.5, n))
        result = tune_linear_alpha(_FakeRidge, X, y, {"alpha": [0.01, 100.0]}, inner_cv)
        assert result.best_params["alpha"] == 100.0

    def test_too_small_returns_none(self, inner_cv):
        from volforecast.models.linear_tuning import tune_linear_alpha

        X = pd.DataFrame({"f": np.zeros(50)})
        y = pd.Series(np.full(50, -8.0))
        # train_size=150 > 50 rows -> zero inner folds
        assert tune_linear_alpha(_FakeRidge, X, y, {"alpha": [1.0]}, inner_cv) is None

    def test_on_trial_complete_called_per_combo(self, signal_data, inner_cv):
        from volforecast.models.linear_tuning import tune_linear_alpha

        X, y = signal_data
        calls: list[int] = []
        grid = {"alpha": [0.01, 1.0, 100.0]}
        tune_linear_alpha(
            _FakeRidge, X, y, grid, inner_cv, on_trial_complete=calls.append
        )
        assert len(calls) == 3
        assert calls == [1, 2, 3]


def _make_tunable_cls():
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline as SKPipeline
    from sklearn.preprocessing import StandardScaler

    from volforecast.models._base import _BaseOLS

    class TunableRidge(_BaseOLS):
        _FEATURES = None
        _ALPHA_GRID = [1e-6, 1e6]

        supports_tuning = True

        def __init__(self, alpha: float = 1.0):
            pipe = SKPipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
            super().__init__(model=pipe)
            self.alpha = alpha

        def fit(self, X, y):
            self._fit(X, y)
            return self

    return TunableRidge


class TestBaseOLSTuneAndFit:
    def test_base_ols_not_tunable_by_default(self):
        from volforecast.models._base import _BaseOLS

        assert _BaseOLS.supports_tuning is False
        assert _BaseOLS._ALPHA_GRID is None

    def test_get_params_roundtrip(self):
        cls = _make_tunable_cls()
        m = cls(alpha=3.5)
        assert m.get_params() == {"alpha": 3.5}
        m2 = cls(**m.get_params())
        assert m2.alpha == 3.5

    def test_plain_ols_get_params_empty(self):
        from volforecast.models._base import _BaseOLS

        assert _BaseOLS().get_params() == {}

    def test_tune_and_fit_picks_grid_winner(self, signal_data, inner_cv):
        from volforecast.config import TuningConfig

        cls = _make_tunable_cls()
        X, y = signal_data
        cfg = TuningConfig(enabled=True, inner_cv=inner_cv)
        model = cls.tune_and_fit(X, y, cfg)
        assert model.alpha == 1e-6                      # strong signal -> min shrinkage
        assert model.coefficients_ is not None          # refit on full outer train
        assert model.tuning_result_ is not None
        assert len(model.tuning_result_.grid_results) == 2

    def test_search_space_override(self, signal_data, inner_cv):
        from volforecast.config import TuningConfig

        cls = _make_tunable_cls()
        X, y = signal_data
        cfg = TuningConfig(
            enabled=True,
            inner_cv=inner_cv,
            search_space={"alpha": {"values": [7.0]}},
        )
        model = cls.tune_and_fit(X, y, cfg)
        assert model.alpha == 7.0

    def test_fallback_to_defaults_when_train_too_small(self, inner_cv):
        from volforecast.config import TuningConfig

        cls = _make_tunable_cls()
        rng = np.random.default_rng(1)
        X = pd.DataFrame({"f": rng.normal(-8, 1, 60)})
        y = pd.Series(rng.normal(-8, 1, 60))
        cfg = TuningConfig(enabled=True, inner_cv=inner_cv)  # train_size=150 > 60
        model = cls.tune_and_fit(X, y, cfg)
        assert model.alpha == 1.0                       # constructor default
        assert model.tuning_result_ is None


class TestRegistryTuningFlags:
    @pytest.fixture(autouse=True)
    def _register(self):
        from volforecast.registry import ensure_registered

        ensure_registered()

    def test_factory_variants_accept_and_store_alpha(self):
        from volforecast.models import MODEL_REGISTRY

        m = MODEL_REGISTRY["ridge_har_cj_iv_0dte"](alpha=42.0)
        assert m.alpha == 42.0
        assert m.get_params() == {"alpha": 42.0}
        # alpha actually reaches the sklearn estimator
        assert m._model.named_steps["ridge"].alpha == 42.0

        m2 = MODEL_REGISTRY["lasso_shar_iv_0dte"](alpha=0.05, l1_ratio=0.9)
        assert m2.get_params() == {"alpha": 0.05, "l1_ratio": 0.9}

    def test_factory_defaults_unchanged(self):
        from volforecast.models import MODEL_REGISTRY

        assert MODEL_REGISTRY["ridge_har_cj_iv_0dte"]().alpha == 1.0
        lasso = MODEL_REGISTRY["lasso_shar_iv_0dte"]()
        assert (lasso.alpha, lasso.l1_ratio) == (0.01, 0.95)
        enet = MODEL_REGISTRY["elasticnet_shar_cj_iv_0dte"]()
        assert (enet.alpha, enet.l1_ratio) == (0.01, 0.5)

    def test_all_regularized_variants_flagged(self):
        from volforecast.models import MODEL_REGISTRY
        from volforecast.models._base import _BaseOLS
        from volforecast.models.linear_tuning import (
            ENET_L1_RATIO_GRID,
            RIDGE_ALPHA_GRID,
            SPARSE_ALPHA_GRID,
        )

        checked = 0
        for name, cls in MODEL_REGISTRY.items():
            if not (isinstance(cls, type) and issubclass(cls, _BaseOLS)):
                continue
            prefix = name.split("_", 1)[0]
            if prefix == "ridge":
                assert cls.supports_tuning is True, name
                assert cls._ALPHA_GRID == RIDGE_ALPHA_GRID, name
                assert cls._L1_RATIO_GRID is None, name
            elif prefix == "lasso":
                assert cls.supports_tuning is True, name
                assert cls._ALPHA_GRID == SPARSE_ALPHA_GRID, name
                assert cls._L1_RATIO_GRID is None, name
            elif prefix == "elasticnet":
                assert cls.supports_tuning is True, name
                assert cls._ALPHA_GRID == SPARSE_ALPHA_GRID, name
                assert cls._L1_RATIO_GRID == ENET_L1_RATIO_GRID, name
            else:
                assert cls.supports_tuning is False, f"OLS model {name} must stay untunable"
                continue
            # every tunable class round-trips its constructor
            inst = cls()
            cls(**inst.get_params())
            checked += 1
        assert checked >= 80  # 60 factory + >=20 manual regularized variants

    def test_elasticnet_fit_is_deterministic(self):
        from volforecast.models import MODEL_REGISTRY

        rng = np.random.default_rng(3)
        n = 300
        X = pd.DataFrame(
            {
                "log_rs_positive_d": rng.normal(-9, 0.5, n),
                "log_rs_negative_d": rng.normal(-9, 0.5, n),
                "log_rv_w": rng.normal(-8, 0.4, n),
                "log_rv_m": rng.normal(-8, 0.3, n),
                "log_atm_iv_0dte_d": rng.normal(-2, 0.2, n),
            }
        )
        y = pd.Series(X["log_rv_w"] * 0.6 + rng.normal(0, 0.3, n))
        m1 = MODEL_REGISTRY["lasso_shar_iv_0dte"]().fit(X, y)
        m2 = MODEL_REGISTRY["lasso_shar_iv_0dte"]().fit(X, y)
        np.testing.assert_array_equal(m1.coefficients_, m2.coefficients_)


class TestRunnerIntegration:
    @pytest.fixture(autouse=True)
    def _register(self):
        from volforecast.registry import ensure_registered

        ensure_registered()

    @pytest.fixture
    def hariv_panel(self):
        """Synthetic X with ridge_har_iv's exact _FEATURES + log-RV target."""
        rng = np.random.default_rng(7)
        n = 400
        X = pd.DataFrame(
            {
                "log_rv_d": rng.normal(-8, 1.0, n),
                "log_rv_w": rng.normal(-8, 0.5, n),
                "log_rv_m": rng.normal(-8, 0.3, n),
                "log_atm_iv_d": rng.normal(-2, 0.2, n),
            },
            index=pd.bdate_range("2022-01-03", periods=n),
        )
        y = pd.Series(
            0.5 * X["log_rv_d"] + 0.3 * X["log_rv_w"] + rng.normal(0, 0.3, n),
            index=X.index,
        )
        return X, y

    def test_capability_flags_on_tree_models(self):
        lgbm = pytest.importorskip("lightgbm")  # noqa: F841
        from volforecast.models.lightgbm import LightGBMVolModel

        assert LightGBMVolModel.supports_fit_progress is True
        assert LightGBMVolModel.supports_shap_selection is True
        assert LightGBMVolModel.accepts_gpu_device is True

    def test_capability_flags_on_xgboost(self):
        xgb = pytest.importorskip("xgboost")  # noqa: F841
        from volforecast.models.xgboost import XGBoostVolModel

        assert XGBoostVolModel.supports_fit_progress is True
        assert XGBoostVolModel.supports_shap_selection is True
        assert XGBoostVolModel.accepts_gpu_device is True

    def test_linear_models_do_not_accept_gpu(self):
        from volforecast.models import MODEL_REGISTRY

        cls = MODEL_REGISTRY["ridge_har_cj_iv_0dte"]
        assert cls.accepts_gpu_device is False
        assert cls.supports_fit_progress is False
        assert cls.supports_shap_selection is False
