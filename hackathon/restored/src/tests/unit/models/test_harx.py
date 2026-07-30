"""Tests pinning the HARXModel contract (generic HAR with YAML-driven extras).

These tests define the API for the new generic HAR-X model whose feature list
is set at construction via ``extra_features`` (HAR core + extras). They MUST
FAIL on first run — ``HARXModel`` / ``RidgeHARXModel`` / ``LassoHARXModel`` /
``ElasticNetHARXModel`` and their registry keys (``harx`` / ``ridge_harx`` /
``lasso_harx`` / ``elasticnet_harx``) do not exist yet. Plan reference: §3
Tests in ``workspace/plans/generic-harx-model.md``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.config import ExperimentConfig, ModelConfig
from volforecast.models.har_family import (
    ElasticNetHARXModel,
    HARXModel,
    LassoHARXModel,
    RidgeHARXModel,
)
from volforecast.registry import MODEL_REGISTRY, ensure_registered

_HAR_CORE = ["log_rv_d", "log_rv_w", "log_rv_m"]


def _make_synthetic_panel(
    n: int = 200,
    extras: list[str] | None = None,
    seed: int = 0,
) -> tuple[pd.DataFrame, pd.Series]:
    """Deterministic HAR-shaped panel with optional extra columns."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-02", periods=n)
    log_rv_d = -9.0 + 0.5 * rng.standard_normal(n)
    log_rv_w = -9.0 + 0.4 * rng.standard_normal(n)
    log_rv_m = -9.0 + 0.3 * rng.standard_normal(n)
    data: dict[str, np.ndarray] = {
        "log_rv_d": log_rv_d,
        "log_rv_w": log_rv_w,
        "log_rv_m": log_rv_m,
    }
    for i, name in enumerate(extras or []):
        data[name] = 0.2 * rng.standard_normal(n) + 0.1 * (i + 1)
    X = pd.DataFrame(data, index=dates)
    target = (
        -1.0
        + 0.4 * X["log_rv_d"].to_numpy()
        + 0.3 * X["log_rv_w"].to_numpy()
        + 0.2 * X["log_rv_m"].to_numpy()
        + 0.1 * rng.standard_normal(n)
    )
    y = pd.Series(target, index=dates, name="log_rv_target")
    return X, y


# ---------------------------------------------------------------------------
# Test 1 — None / empty extras behaves as plain HAR
# ---------------------------------------------------------------------------
def test_harx_default_features_are_har_core() -> None:
    """HARXModel(extra_features=None) must expose the plain HAR core."""
    model = HARXModel(extra_features=None)
    assert model._FEATURES == _HAR_CORE


# ---------------------------------------------------------------------------
# Test 2 — extras appended in the order the YAML supplies them
# ---------------------------------------------------------------------------
def test_harx_appends_extras_in_order() -> None:
    """Extras are appended after HAR core, preserving YAML order."""
    extras = ["log_atm_iv_0dte_d", "gex_zscore_d"]
    model = HARXModel(extra_features=extras)
    assert model._FEATURES == _HAR_CORE + extras


# ---------------------------------------------------------------------------
# Test 3 — fit / predict on a synthetic panel yields finite predictions
# ---------------------------------------------------------------------------
def test_harx_fit_predict_produces_finite_output() -> None:
    """HARXModel with extras fits and predicts finite values on 200 rows."""
    extras = ["log_atm_iv_0dte_d", "gex_zscore_d"]
    X, y = _make_synthetic_panel(n=200, extras=extras, seed=7)
    model = HARXModel(extra_features=extras).fit(X, y)
    preds = model.predict(X)
    assert len(preds) == len(X)
    assert np.all(np.isfinite(preds))


# ---------------------------------------------------------------------------
# Test 4 — get_params round-trips for OLS + all regularized variants
# ---------------------------------------------------------------------------
def test_harx_get_params_roundtrip() -> None:
    """get_params() output must reconstruct an equivalent estimator.

    - HARXModel:            {extra_features}
    - RidgeHARXModel:       {extra_features, alpha}
    - LassoHARXModel:       {extra_features, alpha, l1_ratio}
    - ElasticNetHARXModel:  {extra_features, alpha, l1_ratio}
    """
    extras = ["log_atm_iv_0dte_d"]

    # Plain OLS: extra_features must round-trip
    ols = HARXModel(extra_features=extras)
    ols_params = ols.get_params()
    assert ols_params.get("extra_features") == extras
    ols_clone = HARXModel(**ols_params)
    assert ols_clone._FEATURES == ols._FEATURES

    # Ridge: alpha + extra_features
    ridge = RidgeHARXModel(extra_features=extras, alpha=0.5)
    ridge_params = ridge.get_params()
    assert ridge_params.get("extra_features") == extras
    assert ridge_params.get("alpha") == 0.5
    ridge_clone = RidgeHARXModel(**ridge_params)
    assert ridge_clone._FEATURES == ridge._FEATURES
    assert ridge_clone.alpha == ridge.alpha

    # Lasso: alpha + l1_ratio + extra_features
    lasso = LassoHARXModel(extra_features=extras, alpha=0.02, l1_ratio=0.95)
    lasso_params = lasso.get_params()
    assert lasso_params.get("extra_features") == extras
    assert lasso_params.get("alpha") == 0.02
    assert lasso_params.get("l1_ratio") == 0.95
    lasso_clone = LassoHARXModel(**lasso_params)
    assert lasso_clone._FEATURES == lasso._FEATURES
    assert lasso_clone.alpha == lasso.alpha
    assert lasso_clone.l1_ratio == lasso.l1_ratio

    # ElasticNet: alpha + l1_ratio + extra_features
    enet = ElasticNetHARXModel(extra_features=extras, alpha=0.02, l1_ratio=0.5)
    enet_params = enet.get_params()
    assert enet_params.get("extra_features") == extras
    assert enet_params.get("alpha") == 0.02
    assert enet_params.get("l1_ratio") == 0.5
    enet_clone = ElasticNetHARXModel(**enet_params)
    assert enet_clone._FEATURES == enet._FEATURES
    assert enet_clone.alpha == enet.alpha
    assert enet_clone.l1_ratio == enet.l1_ratio


# ---------------------------------------------------------------------------
# Test 5 — missing extra column at fit-time raises ValueError with column name
# ---------------------------------------------------------------------------
def test_harx_missing_extra_feature_raises_on_fit() -> None:
    """Construction must succeed; fit must raise ValueError naming the column."""
    extras = ["log_atm_iv_0dte_d", "gex_zscore_d"]
    # Instantiation itself succeeds — the check fires on fit.
    model = HARXModel(extra_features=extras)

    # Panel missing 'gex_zscore_d' should trigger a targeted ValueError.
    X, y = _make_synthetic_panel(n=200, extras=["log_atm_iv_0dte_d"], seed=1)
    with pytest.raises(ValueError, match="gex_zscore_d"):
        model.fit(X, y)


# ---------------------------------------------------------------------------
# Test 6 — regularized variants accept extras + regularization kwargs together
# ---------------------------------------------------------------------------
def test_regularized_harx_accept_extras_plus_alpha() -> None:
    """ridge / lasso / elasticnet HARX variants accept extra_features + alpha."""
    extras = ["foo"]

    ridge = RidgeHARXModel(extra_features=extras, alpha=0.5)
    assert "foo" in ridge._FEATURES
    assert ridge.alpha == 0.5

    lasso = LassoHARXModel(extra_features=extras, alpha=0.02, l1_ratio=0.9)
    assert "foo" in lasso._FEATURES
    assert lasso.alpha == 0.02
    assert lasso.l1_ratio == 0.9

    enet = ElasticNetHARXModel(extra_features=extras, alpha=0.02, l1_ratio=0.4)
    assert "foo" in enet._FEATURES
    assert enet.alpha == 0.02
    assert enet.l1_ratio == 0.4

    # And they must be registered under their expected keys.
    ensure_registered()
    for key in ("harx", "ridge_harx", "lasso_harx", "elasticnet_harx"):
        assert key in MODEL_REGISTRY, f"missing registry entry {key!r}"


# ---------------------------------------------------------------------------
# Test 7 — horizon-override plumbing for extra_features
# ---------------------------------------------------------------------------
def test_harx_horizon_override_swaps_extra_features() -> None:
    """horizon_overrides[h].model.params.extra_features must replace the base list."""
    config = ExperimentConfig(
        name="harx_horizon_test",
        universe=["SPY"],
        date_range=("2020-01-02", "2020-12-31"),
        horizons=[1, 5],
        feature_layers=["har_core"],
        model=ModelConfig(name="harx", params={"extra_features": ["a"]}),
        horizon_overrides={
            5: {"model": {"params": {"extra_features": ["b", "c"]}}},
        },
    )

    assert config.model_params_for_horizon(1)["extra_features"] == ["a"]
    assert config.model_params_for_horizon(5)["extra_features"] == ["b", "c"]
