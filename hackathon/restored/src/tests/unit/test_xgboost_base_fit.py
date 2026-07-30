"""Test that _fit_base_model does NOT train on validation data.

Regression test for the bug where _fit_base_model was called with the full
training set (including the early-stopping validation tail), causing optimistic
base-model predictions on val rows and biased early stopping.
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

xgb = pytest.importorskip("xgboost")

from volforecast.models.xgboost import XGBoostVolModel  # noqa: E402


class RecordingModel:
    """A minimal base model that records the size of data it was fit on."""

    fit_n_rows: int | None = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "RecordingModel":
        RecordingModel.fit_n_rows = len(X)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.full(len(X), float(np.mean([-8.0])))


@pytest.fixture
def synthetic_data_with_base():
    """Synthetic log-RV data sized to make val split obvious."""
    rng = np.random.default_rng(99)
    n = 200
    X = pd.DataFrame(
        {
            "log_rv_d": rng.normal(-8, 1, n),
            "log_rv_w": rng.normal(-8, 0.5, n),
            "log_rv_m": rng.normal(-8, 0.3, n),
        }
    )
    y = pd.Series(X["log_rv_d"] * 0.5 + X["log_rv_w"] * 0.3 + rng.normal(0, 0.5, n))
    return X, y


class TestBaseModelDoesNotSeeValData:
    """Verify _fit_base_model receives only pre-validation rows."""

    def test_base_model_fit_excludes_val_rows(self, synthetic_data_with_base):
        """Base model trains on len(X) - val_size rows, not the full set."""
        X, y = synthetic_data_with_base
        n = len(X)
        val_fraction = 0.15

        # Expected: base model should see only the training portion
        expected_split_idx = int(n * (1.0 - val_fraction))

        # Patch MODEL_REGISTRY so "recording" resolves to our RecordingModel
        fake_registry = {"recording": RecordingModel}
        RecordingModel.fit_n_rows = None

        with patch("volforecast.registry.MODEL_REGISTRY", fake_registry), \
             patch("volforecast.registry.ensure_registered", lambda: None):
            model = XGBoostVolModel(
                n_estimators=10,
                early_stopping_rounds=5,
                val_fraction=val_fraction,
                val_purge_gap=0,
                base_model="recording",
            )
            model.fit(X, y)

        # The base model must NOT have been fit on the full dataset
        assert RecordingModel.fit_n_rows is not None, "Base model was never fit"
        assert RecordingModel.fit_n_rows == expected_split_idx, (
            f"Base model fit on {RecordingModel.fit_n_rows} rows, "
            f"expected {expected_split_idx} (full={n}, val excluded)"
        )

    def test_init_score_vector_covers_full_dataset(self, synthetic_data_with_base):
        """init_score_vector must still cover all rows for val base margins."""
        X, y = synthetic_data_with_base
        n = len(X)

        fake_registry = {"recording": RecordingModel}
        RecordingModel.fit_n_rows = None

        with patch("volforecast.registry.MODEL_REGISTRY", fake_registry), \
             patch("volforecast.registry.ensure_registered", lambda: None):
            model = XGBoostVolModel(
                n_estimators=10,
                early_stopping_rounds=5,
                val_fraction=0.15,
                val_purge_gap=0,
                base_model="recording",
            )
            model.fit(X, y)

        # init_score_vector must span the full cleaned dataset
        assert model._init_score_vector is not None
        assert len(model._init_score_vector) == n
