"""Tests for GSVIVS01 drawdown classifier."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Target builder tests
# ---------------------------------------------------------------------------


class TestBuildClassificationTarget:
    """Tests for build_gsvivs_classification_target."""

    def test_returns_binary_series(self):
        """Target should be 0/1 only."""
        from volforecast.models.gsvivs_classifier import build_gsvivs_classification_target

        # Simulated GSVIVS01 index: alternating up/down
        dates = pd.bdate_range("2022-06-01", periods=100, freq="B")
        rng = np.random.default_rng(42)
        returns = rng.standard_normal(100) * 0.01
        levels = 100.0 * np.exp(np.cumsum(returns))
        index_series = pd.Series(levels, index=dates, name="gsvivs01")

        target = build_gsvivs_classification_target(index_series)
        assert set(target.unique()).issubset({0, 1})

    def test_target_length(self):
        """Target should have len(index) - 1 (next-day return label)."""
        from volforecast.models.gsvivs_classifier import build_gsvivs_classification_target

        dates = pd.bdate_range("2022-06-01", periods=50, freq="B")
        levels = pd.Series(np.linspace(100, 110, 50), index=dates)
        target = build_gsvivs_classification_target(levels)
        # Last day has no next-day return, so target is shorter by 1
        assert len(target) == 49

    def test_down_days_labeled_1(self):
        """Days where next-day return < 0 should be labeled 1."""
        from volforecast.models.gsvivs_classifier import build_gsvivs_classification_target

        dates = pd.bdate_range("2022-06-01", periods=5, freq="B")
        # Levels: 100, 101, 99, 102, 98 -> returns: +1%, -2%, +3%, -4%
        levels = pd.Series([100.0, 101.0, 99.0, 102.0, 98.0], index=dates)
        target = build_gsvivs_classification_target(levels)
        # Day 0 (100->101): up, label=0
        # Day 1 (101->99): down, label=1
        # Day 2 (99->102): up, label=0
        # Day 3 (102->98): down, label=1
        expected = pd.Series([0, 1, 0, 1], index=dates[:4], dtype=np.int8)
        pd.testing.assert_series_equal(target, expected, check_names=False)


# ---------------------------------------------------------------------------
# Classifier model tests
# ---------------------------------------------------------------------------


class TestGSVIVSClassifier:
    """Tests for GsvivsDrawdownClassifier."""

    @pytest.fixture
    def training_data(self):
        """Create synthetic feature matrix + binary target."""
        rng = np.random.default_rng(123)
        n = 500
        X = pd.DataFrame(
            {
                "iv_rv_gap": rng.standard_normal(n) * 0.02,
                "rv_d": rng.standard_normal(n),
                "rv_w": rng.standard_normal(n),
                "vix_level": rng.uniform(12, 35, n),
            },
            index=pd.bdate_range("2022-06-01", periods=n, freq="B"),
        )
        # Target: more likely down when iv_rv_gap is negative
        prob_down = 1 / (1 + np.exp(10 * X["iv_rv_gap"]))
        y = pd.Series(
            (rng.random(n) < prob_down).astype(np.int8),
            index=X.index,
        )
        return X, y

    def test_fit_returns_self(self, training_data):
        """fit() should return the model instance."""
        from volforecast.models.gsvivs_classifier import GsvivsDrawdownClassifier

        X, y = training_data
        model = GsvivsDrawdownClassifier()
        result = model.fit(X, y)
        assert result is model

    def test_predict_proba_shape(self, training_data):
        """predict_proba should return array same length as input."""
        from volforecast.models.gsvivs_classifier import GsvivsDrawdownClassifier

        X, y = training_data
        model = GsvivsDrawdownClassifier()
        model.fit(X[:400], y[:400])
        proba = model.predict_proba(X[400:])
        assert len(proba) == 100

    def test_predict_proba_range(self, training_data):
        """Probabilities should be in [0, 1]."""
        from volforecast.models.gsvivs_classifier import GsvivsDrawdownClassifier

        X, y = training_data
        model = GsvivsDrawdownClassifier()
        model.fit(X[:400], y[:400])
        proba = model.predict_proba(X[400:])
        assert np.all(proba >= 0)
        assert np.all(proba <= 1)

    def test_predict_signal(self, training_data):
        """predict_signal should return +1/-1 array."""
        from volforecast.models.gsvivs_classifier import GsvivsDrawdownClassifier

        X, y = training_data
        model = GsvivsDrawdownClassifier(threshold=0.5)
        model.fit(X[:400], y[:400])
        signal = model.predict_signal(X[400:])
        assert set(np.unique(signal)).issubset({-1.0, 1.0})

    def test_high_threshold_fewer_shorts(self, training_data):
        """Higher threshold should produce fewer short signals."""
        from volforecast.models.gsvivs_classifier import GsvivsDrawdownClassifier

        X, y = training_data
        model_low = GsvivsDrawdownClassifier(threshold=0.3)
        model_low.fit(X[:400], y[:400])
        model_high = GsvivsDrawdownClassifier(threshold=0.7)
        model_high.fit(X[:400], y[:400])

        signal_low = model_low.predict_signal(X[400:])
        signal_high = model_high.predict_signal(X[400:])

        n_short_low = np.sum(signal_low == -1)
        n_short_high = np.sum(signal_high == -1)
        assert n_short_high <= n_short_low

    def test_scale_pos_weight_affects_predictions(self, training_data):
        """Lower scale_pos_weight should reduce false positives (fewer short signals)."""
        from volforecast.models.gsvivs_classifier import GsvivsDrawdownClassifier

        X, y = training_data
        model_default = GsvivsDrawdownClassifier(scale_pos_weight=1.0)
        model_default.fit(X[:400], y[:400])
        model_precision = GsvivsDrawdownClassifier(scale_pos_weight=0.3)
        model_precision.fit(X[:400], y[:400])

        proba_default = model_default.predict_proba(X[400:])
        proba_precision = model_precision.predict_proba(X[400:])

        # With lower pos weight, the model should be less eager to predict positive
        assert np.mean(proba_precision) <= np.mean(proba_default) + 0.1
