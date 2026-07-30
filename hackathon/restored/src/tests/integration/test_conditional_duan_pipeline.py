"""Integration tests for conditional Duan correction pipeline.

Verifies:
1. Pipeline runs end-to-end with conditional_duan enabled
2. Conditional correction is larger for high-variance samples
3. Conditional-corrected QLIKE < global-corrected QLIKE on heteroscedastic data
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.evaluation.metrics import qlike
from volforecast.pipeline.conditional_duan import (
    ConditionalDuanConfig,
    apply_conditional_duan,
)


class TestConditionalDuanPipeline:
    """Integration tests for the conditional Duan two-stage pipeline."""

    def _make_heteroscedastic_data(
        self, n_days: int = 400, seed: int = 42
    ) -> tuple[pd.DataFrame, pd.Series, pd.Series, list[tuple[np.ndarray, np.ndarray]]]:
        """Create synthetic heteroscedastic log-RV data with fold splits.

        Returns (X, y_true, initial_preds, fold_splits) where initial_preds
        are "global-Duan-corrected" predictions that a conditional correction
        should improve upon.
        """
        rng = np.random.default_rng(seed)
        dates = pd.bdate_range("2020-01-02", periods=n_days)

        # Create regime: 15% spike days with higher variance
        is_spike = rng.random(n_days) < 0.15
        true_sigma2 = np.where(is_spike, 0.35, 0.06)

        # Features that correlate with regime (variance model can learn from)
        # Feature 1: lagged realized vol (higher before spikes)
        feat_vol = np.where(is_spike, -8.0 + 0.5 * rng.standard_normal(n_days),
                           -9.5 + 0.2 * rng.standard_normal(n_days))
        # Feature 2: VIX-like feature
        feat_vix = np.where(is_spike, 3.0 + 0.3 * rng.standard_normal(n_days),
                           2.5 + 0.2 * rng.standard_normal(n_days))
        # Feature 3: noise
        feat_noise = rng.standard_normal(n_days)

        X = pd.DataFrame({
            "log_rv_d": feat_vol,
            "vix_level": feat_vix,
            "noise": feat_noise,
        }, index=dates)

        # True log-RV
        mu = -9.0 + 0.3 * feat_vol  # model can partially predict mean
        y_true = pd.Series(
            mu + np.sqrt(true_sigma2) * rng.standard_normal(n_days),
            index=dates,
            name="log_rv",
        )

        # Simulate "Stage 1" predictions with global Duan already applied
        # A decent model that captures ~60% of the signal
        model_pred = mu + 0.4 * np.sqrt(true_sigma2) * rng.standard_normal(n_days)
        global_residuals = y_true.values - model_pred
        global_duan = float(np.log(np.mean(np.exp(
            np.clip(global_residuals, -10, 10)
        ))))
        initial_preds = pd.Series(model_pred + global_duan, index=dates)

        # Create 4 expanding-window fold splits (100 train, 75 test each)
        fold_splits = []
        fold_size = 75
        for i in range(4):
            train_end = 100 + i * fold_size
            test_start = train_end
            test_end = min(test_start + fold_size, n_days)
            if test_end <= test_start:
                break
            train_idx = np.arange(0, train_end)
            test_idx = np.arange(test_start, test_end)
            fold_splits.append((train_idx, test_idx))

        return X, y_true, initial_preds, fold_splits

    def test_pipeline_runs_end_to_end(self):
        """apply_conditional_duan runs without error and returns a Series."""
        X, y_true, initial_preds, fold_splits = self._make_heteroscedastic_data()
        config = ConditionalDuanConfig(enabled=True, min_folds_for_training=1)

        result = apply_conditional_duan(
            initial_preds, y_true, X, fold_splits, config,
        )

        assert isinstance(result, pd.Series)
        assert len(result) == len(initial_preds)
        assert result.notna().sum() > 0

    def test_correction_differs_by_regime(self):
        """Conditional correction should be larger for spike-regime samples."""
        rng = np.random.default_rng(123)
        n = 1200
        dates = pd.bdate_range("2020-01-02", periods=n)

        # Clear regime separation
        is_spike = np.zeros(n, dtype=bool)
        is_spike[::5] = True  # every 5th day is a spike (20%)

        true_sigma2 = np.where(is_spike, 0.40, 0.04)

        # Features that perfectly indicate regime (best-case scenario for test)
        X = pd.DataFrame({
            "regime_indicator": is_spike.astype(float),
            "noise": rng.standard_normal(n),
        }, index=dates)

        mu = -9.0
        y_true = pd.Series(
            mu + np.sqrt(true_sigma2) * rng.standard_normal(n),
            index=dates,
        )

        # Global-corrected predictions
        global_var = float(np.mean(true_sigma2))
        initial_preds = pd.Series(np.full(n, mu + global_var / 2), index=dates)

        # 4 folds: expanding window with larger training sets
        fold_splits = [
            (np.arange(0, 300), np.arange(300, 500)),
            (np.arange(0, 500), np.arange(500, 700)),
            (np.arange(0, 700), np.arange(700, 900)),
            (np.arange(0, 900), np.arange(900, 1200)),
        ]

        config = ConditionalDuanConfig(
            enabled=True, min_folds_for_training=1,
            n_estimators=200, max_leaves=4,
            min_child_weight=10,  # Small for this test
        )

        result = apply_conditional_duan(
            initial_preds, y_true, X, fold_splits, config,
        )

        # Compare corrections for spike vs calm days in fold 4 (has 3 prior folds)
        fold4_test = fold_splits[3][1]
        spike_in_fold4 = fold4_test[is_spike[fold4_test]]
        calm_in_fold4 = fold4_test[~is_spike[fold4_test]]

        assert len(spike_in_fold4) > 0 and len(calm_in_fold4) > 0
        spike_delta = float(np.mean(
            result.iloc[spike_in_fold4].values - initial_preds.iloc[spike_in_fold4].values
        ))
        calm_delta = float(np.mean(
            result.iloc[calm_in_fold4].values - initial_preds.iloc[calm_in_fold4].values
        ))
        # Spike days should get LARGER positive correction than calm days
        assert spike_delta > calm_delta, (
            f"Spike delta ({spike_delta:.4f}) should exceed "
            f"calm delta ({calm_delta:.4f})"
        )

    def test_improves_qlike_on_heteroscedastic_data(self):
        """Conditional correction improves QLIKE over global on heteroscedastic data.

        The variance model must actually learn differential predictions for
        this to work. Use large data, low min_child_weight, and strong signal.
        """
        rng = np.random.default_rng(2026)
        n = 2000
        dates = pd.bdate_range("2018-01-02", periods=n)

        # Strong heteroscedasticity with CLEAR feature signal
        is_spike = rng.random(n) < 0.15
        true_sigma2 = np.where(is_spike, 0.40, 0.04)

        # Feature that perfectly predicts regime
        regime_feat = is_spike.astype(float)
        # Add noise but keep signal strong
        X = pd.DataFrame({
            "regime_feat": regime_feat + 0.05 * rng.standard_normal(n),
            "log_rv_lag": -9.0 + np.sqrt(true_sigma2) * rng.standard_normal(n),
            "noise": rng.standard_normal(n),
        }, index=dates)

        mu = -9.0
        y_true = pd.Series(
            mu + np.sqrt(true_sigma2) * rng.standard_normal(n),
            index=dates,
        )

        # Simulate QLIKE-trained predictions (global Duan ≈ 0)
        # These are "raw" predictions with no global correction
        initial_preds = pd.Series(np.full(n, mu), index=dates)

        # 5 expanding folds with large training sets
        fold_splits = [
            (np.arange(0, 400), np.arange(400, 700)),
            (np.arange(0, 700), np.arange(700, 1000)),
            (np.arange(0, 1000), np.arange(1000, 1300)),
            (np.arange(0, 1300), np.arange(1300, 1600)),
            (np.arange(0, 1600), np.arange(1600, 2000)),
        ]

        config = ConditionalDuanConfig(
            enabled=True, min_folds_for_training=1,
            n_estimators=200, max_leaves=4,
            min_child_weight=10,  # Low to allow splits on small subsets
            colsample_bytree=1.0,  # Use all features
        )

        corrected = apply_conditional_duan(
            initial_preds, y_true, X, fold_splits, config,
        )

        # Evaluate on folds that had conditional correction (2+ prior folds)
        eval_idx = np.concatenate([
            fold_splits[2][1], fold_splits[3][1], fold_splits[4][1]
        ])
        eval_mask = pd.Series(False, index=dates)
        eval_mask.iloc[eval_idx] = True

        y_eval = y_true[eval_mask].values
        p_global = initial_preds[eval_mask].values
        p_conditional = corrected[eval_mask].values

        qlike_global = qlike(y_eval, p_global)
        qlike_conditional = qlike(y_eval, p_conditional)

        assert qlike_conditional < qlike_global, (
            f"Conditional QLIKE ({qlike_conditional:.5f}) should beat "
            f"global ({qlike_global:.5f})"
        )

    def test_no_change_with_no_prior_folds(self):
        """When all folds lack prior data AND no fallback available, predictions stay unchanged."""
        X, y_true, initial_preds, fold_splits = self._make_heteroscedastic_data()
        # Use only first fold (no prior data, no fallback)
        single_fold = [fold_splits[0]]
        config = ConditionalDuanConfig(
            enabled=True, min_folds_for_training=99,  # impossibly high
        )

        result = apply_conditional_duan(
            initial_preds, y_true, X, single_fold, config,
        )
        # First fold has no prior data and min_folds is impossibly high → no changes
        valid = result.notna() & initial_preds.notna()
        np.testing.assert_array_almost_equal(
            result[valid].values,
            initial_preds[valid].values,
        )

    def test_early_folds_get_global_fallback(self):
        """Folds without enough prior data for a model get global fallback correction."""
        X, y_true, initial_preds, fold_splits = self._make_heteroscedastic_data()
        config = ConditionalDuanConfig(
            enabled=True, min_folds_for_training=3,  # need 3 prior folds
        )

        result = apply_conditional_duan(
            initial_preds, y_true, X, fold_splits, config,
        )

        # First fold: zero prior folds, stays unchanged
        fold1_test = fold_splits[0][1]
        np.testing.assert_array_almost_equal(
            result.iloc[fold1_test].values,
            initial_preds.iloc[fold1_test].values,
        )

        # Second fold: 1 prior fold (< 3 needed), gets global fallback
        # (positive correction since there IS 1 prior fold)
        fold2_test = fold_splits[1][1]
        fold2_delta = result.iloc[fold2_test].values - initial_preds.iloc[fold2_test].values
        # Should all be the same positive value (global scalar)
        assert np.all(fold2_delta >= 0), "Global fallback should be non-negative"
        assert np.std(fold2_delta) < 1e-10, "Global fallback should be uniform"
