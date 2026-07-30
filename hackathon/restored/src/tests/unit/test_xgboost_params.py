"""Regression test: params.pop('drop_features') must not mutate internal state.

The bug: _clean_inputs() used params.pop("drop_features"), which removed
the key from self.params on the first fit() call. Subsequent fit() calls
(e.g., from cached params in the pipeline runner) silently lost the setting.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

xgb = pytest.importorskip("xgboost")

from volforecast.models.xgboost import XGBoostVolModel  # noqa: E402


@pytest.fixture
def synthetic_data_with_extra_col():
    """Synthetic data with a column that should be dropped."""
    rng = np.random.default_rng(99)
    n = 200
    X = pd.DataFrame(
        {
            "log_rv_d": rng.normal(-8, 1, n),
            "log_rv_w": rng.normal(-8, 0.5, n),
            "log_rv_m": rng.normal(-8, 0.3, n),
            "noisy_junk": rng.normal(0, 10, n),  # to be dropped
        }
    )
    y = pd.Series(X["log_rv_d"] * 0.5 + X["log_rv_w"] * 0.3 + rng.normal(0, 0.5, n))
    return X, y


class TestDropFeaturesParamSurvival:
    """drop_features must persist across multiple fit() calls."""

    def test_drop_features_survives_fit(self, synthetic_data_with_extra_col):
        """get_params() still contains drop_features after fit()."""
        X, y = synthetic_data_with_extra_col
        model = XGBoostVolModel(
            n_estimators=5,
            early_stopping_rounds=2,
            drop_features=["noisy_junk"],
        )

        # First fit
        model.fit(X, y)
        params_after_first = model.get_params()
        assert "drop_features" in params_after_first, (
            "drop_features lost from params after first fit()"
        )
        assert params_after_first["drop_features"] == ["noisy_junk"]

    def test_drop_features_survives_two_fits(self, synthetic_data_with_extra_col):
        """drop_features still present and functional after two fit() calls."""
        X, y = synthetic_data_with_extra_col
        model = XGBoostVolModel(
            n_estimators=5,
            early_stopping_rounds=2,
            drop_features=["noisy_junk"],
        )

        # First fit
        model.fit(X, y)
        # Second fit (simulates runner reusing cached params)
        model.fit(X, y)

        params_after_second = model.get_params()
        assert "drop_features" in params_after_second, (
            "drop_features lost from params after second fit()"
        )
        assert params_after_second["drop_features"] == ["noisy_junk"]
        # The feature should NOT be in the trained model's feature list
        assert "noisy_junk" not in model._feature_names

    def test_reconstruct_from_get_params_preserves_drop(
        self, synthetic_data_with_extra_col
    ):
        """Reconstructing a model from get_params() preserves drop_features."""
        X, y = synthetic_data_with_extra_col
        model = XGBoostVolModel(
            n_estimators=5,
            early_stopping_rounds=2,
            drop_features=["noisy_junk"],
        )
        model.fit(X, y)

        # Simulate runner: reconstruct from cached params
        cached_params = model.get_params()
        model2 = XGBoostVolModel(**cached_params)
        model2.fit(X, y)

        assert "noisy_junk" not in model2._feature_names
        assert "drop_features" in model2.get_params()
