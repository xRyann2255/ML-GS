"""Tests for models/ensemble.py.

Validates:
1. SimpleAverageEnsemble computes equal-weight mean of predictions
2. InverseQLIKEEnsemble weights inversely by QLIKE performance
3. LinearBlendEnsemble produces valid constrained weights
4. StackingEnsemble fits meta-learner on OOF predictions
5. All ensembles raise NotImplementedError (current stub state)
"""

import numpy as np
import pytest

from volforecast.models.ensemble import (
    InverseQLIKEEnsemble,
    LinearBlendEnsemble,
    SimpleAverageEnsemble,
    StackingEnsemble,
)


class TestSimpleAverageEnsemble:
    def test_name(self):
        ens = SimpleAverageEnsemble()
        assert ens.name == "simple_average"

    def test_predict_raises_not_implemented(self):
        ens = SimpleAverageEnsemble()
        predictions = {
            "har": np.array([1.0, 2.0, 3.0]),
            "lgbm": np.array([1.5, 2.5, 3.5]),
        }
        with pytest.raises(NotImplementedError):
            ens.predict(predictions)


class TestInverseQLIKEEnsemble:
    def test_name(self):
        ens = InverseQLIKEEnsemble()
        assert ens.name == "inverse_qlike"

    def test_initial_weights_none(self):
        ens = InverseQLIKEEnsemble()
        assert ens.weights_ is None

    def test_fit_raises_not_implemented(self):
        ens = InverseQLIKEEnsemble()
        predictions = {"har": np.array([1.0, 2.0]), "lgbm": np.array([1.5, 2.5])}
        y_true = np.array([1.1, 2.1])
        with pytest.raises(NotImplementedError):
            ens.fit(predictions, y_true)

    def test_predict_raises_not_implemented(self):
        ens = InverseQLIKEEnsemble()
        predictions = {"har": np.array([1.0, 2.0])}
        with pytest.raises(NotImplementedError):
            ens.predict(predictions)


class TestLinearBlendEnsemble:
    def test_name(self):
        ens = LinearBlendEnsemble()
        assert ens.name == "linear_blend"

    def test_initial_state(self):
        ens = LinearBlendEnsemble()
        assert ens.weights_ is None
        assert ens.model_names_ is None

    def test_fit_raises_not_implemented(self):
        ens = LinearBlendEnsemble()
        predictions = {"har": np.array([1.0, 2.0]), "lgbm": np.array([1.5, 2.5])}
        y_true = np.array([1.1, 2.1])
        with pytest.raises(NotImplementedError):
            ens.fit(predictions, y_true)

    def test_predict_raises_not_implemented(self):
        ens = LinearBlendEnsemble()
        predictions = {"har": np.array([1.0, 2.0])}
        with pytest.raises(NotImplementedError):
            ens.predict(predictions)


class TestStackingEnsemble:
    def test_name(self):
        ens = StackingEnsemble()
        assert ens.name == "stacking"

    def test_default_alpha(self):
        ens = StackingEnsemble()
        assert ens.meta_alpha == 1.0

    def test_custom_alpha(self):
        ens = StackingEnsemble(meta_alpha=0.5)
        assert ens.meta_alpha == 0.5

    def test_initial_state(self):
        ens = StackingEnsemble()
        assert ens.meta_model_ is None
        assert ens.model_names_ is None

    def test_fit_raises_not_implemented(self):
        ens = StackingEnsemble()
        oof = {"har": np.array([1.0, 2.0]), "lgbm": np.array([1.5, 2.5])}
        y_true = np.array([1.1, 2.1])
        with pytest.raises(NotImplementedError):
            ens.fit(oof, y_true)

    def test_predict_raises_not_implemented(self):
        ens = StackingEnsemble()
        predictions = {"har": np.array([1.0, 2.0])}
        with pytest.raises(NotImplementedError):
            ens.predict(predictions)
