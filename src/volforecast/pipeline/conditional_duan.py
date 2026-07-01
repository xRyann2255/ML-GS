"""Conditional (heteroscedastic) Duan correction — two-stage pipeline.

Replaces the global Duan scalar with per-sample corrections estimated
from a lightweight variance model trained on OOS residuals.

Walk-forward protocol:
  For fold k, the variance model trains on OOS residuals from folds 1..k-1.
  This ensures no information leakage — the variance estimate for a sample
  uses only temporally prior data.

Usage:
  Called as a post-processing step AFTER all folds complete and OOS
  predictions are assembled. Does NOT modify the main fold execution path.

Mathematical basis:
  For a QLIKE-trained model (XGBoost with custom objective), the predictions
  target E[log RV | X] ≈ conditional median of log-RV. But the QLIKE-optimal
  forecast requires:
    pred_optimal = E[log RV | X] + Var[log RV | X] / 2
  The σ²(x)/2 term is the Jensen gap under conditional heteroscedasticity.
  When Var[log RV | X] varies by day (calm vs spike), a global scalar under-
  corrects high-uncertainty days and over-corrects calm days.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from volforecast.evaluation.metrics import conditional_duan_correction, qlike

logger = logging.getLogger(__name__)


@dataclass
class ConditionalDuanConfig:
    """Configuration for the conditional Duan correction stage."""

    enabled: bool = False
    # Variance model hyperparameters (lightweight XGBoost)
    n_estimators: int = 500
    max_leaves: int = 8
    max_depth: int = 3
    learning_rate: float = 0.05
    min_child_weight: int = 200
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    reg_lambda: float = 5.0
    # Safety clipping
    max_var: float = 1.0
    # Minimum folds of residual data before variance model can train
    min_folds_for_training: int = 2
    # VVIX-based direct proxy mode (no second model needed)
    # When set, uses VVIX directly as σ² proxy: correction = alpha * (vvix/100)^2
    # Calibrated alpha is learned from prior-fold residuals vs VVIX relationship
    use_vvix_proxy: bool = False

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> ConditionalDuanConfig:
        if raw is None:
            return cls()
        return cls(
            enabled=bool(raw.get("enabled", False)),
            n_estimators=int(raw.get("n_estimators", 500)),
            max_leaves=int(raw.get("max_leaves", 8)),
            max_depth=int(raw.get("max_depth", 3)),
            learning_rate=float(raw.get("learning_rate", 0.05)),
            min_child_weight=int(raw.get("min_child_weight", 200)),
            subsample=float(raw.get("subsample", 0.8)),
            colsample_bytree=float(raw.get("colsample_bytree", 0.8)),
            reg_lambda=float(raw.get("reg_lambda", 5.0)),
            max_var=float(raw.get("max_var", 1.0)),
            min_folds_for_training=int(raw.get("min_folds_for_training", 2)),
            use_vvix_proxy=bool(raw.get("use_vvix_proxy", False)),
        )


def apply_conditional_duan(
    all_preds: pd.Series,
    y: pd.Series,
    X: pd.DataFrame,
    fold_splits: list[tuple[np.ndarray, np.ndarray]],
    config: ConditionalDuanConfig,
) -> pd.Series:
    """Apply conditional Duan correction using walk-forward variance estimation.

    For each fold k, trains a variance model on squared OOS residuals from
    folds 1..k-1, then predicts σ²(x) for fold k's test samples and applies:

        pred_corrected = pred_original + σ²_hat(x) / 2

    This redistributes the correction across samples based on estimated
    conditional variance: high-uncertainty days get more, calm days get less.

    Parameters
    ----------
    all_preds : pd.Series
        OOS predictions (already with global Duan applied). Index aligned with y.
    y : pd.Series
        Actual log-RV values.
    X : pd.DataFrame
        Feature matrix (same index as y). Used as input to variance model.
        If VVIX proxy mode is enabled, must contain a 'vvix' column.
    fold_splits : list of (train_idx, test_idx)
        The CV fold splits used in Stage 1.
    config : ConditionalDuanConfig
        Variance model configuration.

    Returns
    -------
    pd.Series
        Corrected predictions (same index as input all_preds, NaN where
        original was NaN).
    """
    import xgboost as xgb

    logger.info(
        "Conditional Duan: enabled=%s, use_vvix_proxy=%s, "
        "n_folds=%d, X_shape=%s, n_preds_valid=%d",
        config.enabled, config.use_vvix_proxy,
        len(fold_splits), X.shape,
        int(all_preds.notna().sum()),
    )

    # VVIX direct proxy mode: skip second model, use VVIX as σ² proxy
    if config.use_vvix_proxy:
        # Look for vvix column (raw or decimal)
        vvix_col = None
        if "vvix" in X.columns:
            vvix_col = "vvix"
        elif "vvix_d" in X.columns:
            vvix_col = "vvix_d"
        if vvix_col is not None:
            return _apply_vvix_proxy(all_preds, y, X, fold_splits, config, vvix_col)
        else:
            logger.warning(
                "use_vvix_proxy=True but no VVIX column found in features. "
                "Available vix-related: %s. Falling back to XGBoost variance model.",
                [c for c in X.columns if "vvix" in c.lower() or "vix" in c.lower()],
            )

    valid_mask = all_preds.notna()
    if valid_mask.sum() == 0:
        return all_preds

    n_folds = len(fold_splits)
    corrected = all_preds.copy()

    # Compute OOS residuals per fold
    # Squared residuals = conditional variance targets for the variance model
    fold_residuals: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    # Each entry: (test_indices, squared_residuals, features_at_test_indices)

    for fold_num, (train_idx, test_idx) in enumerate(fold_splits):
        # Only consider test samples that received predictions
        test_mask = all_preds.iloc[test_idx].notna()
        valid_test_idx = test_idx[test_mask.values]

        if len(valid_test_idx) == 0:
            fold_residuals.append((np.array([]), np.array([]), np.array([])))
            continue

        preds_fold = all_preds.iloc[valid_test_idx].values
        actuals_fold = y.iloc[valid_test_idx].values
        residuals_sq = (actuals_fold - preds_fold) ** 2

        fold_residuals.append((
            valid_test_idx,
            residuals_sq,
            X.iloc[valid_test_idx].values,
        ))

    # Walk-forward variance estimation
    for fold_k in range(n_folds):
        test_idx_k = fold_residuals[fold_k][0]
        if len(test_idx_k) == 0:
            continue

        # Collect training data from all PRIOR folds (walk-forward)
        prior_folds = range(0, fold_k)
        available_folds = [
            i for i in prior_folds if len(fold_residuals[i][0]) > 0
        ]

        if len(available_folds) < config.min_folds_for_training:
            # Not enough prior data — use simple global correction for this fold
            # Compute mean squared residual from available priors as fallback
            if available_folds:
                all_sq = np.concatenate([fold_residuals[i][1] for i in available_folds])
                global_sigma2 = float(np.mean(all_sq))
                global_correction = np.clip(global_sigma2, 0.0, config.max_var) / 2.0
                corrected.iloc[test_idx_k] = all_preds.iloc[test_idx_k].values + global_correction
                logger.debug(
                    "Fold %d: using global fallback correction %.4f",
                    fold_k + 1, global_correction,
                )
            continue

        # Assemble training data for variance model
        X_var_train_parts = []
        y_var_train_parts = []
        for i in available_folds:
            _, sq_resid, features = fold_residuals[i]
            X_var_train_parts.append(features)
            y_var_train_parts.append(sq_resid)

        X_var_train = np.vstack(X_var_train_parts)
        y_var_train = np.concatenate(y_var_train_parts)

        # Clip extreme variance targets for robustness
        y_var_train = np.clip(y_var_train, 0.0, config.max_var * 2)

        # Train lightweight variance model
        X_var_test = X.iloc[test_idx_k].values

        dtrain = xgb.DMatrix(X_var_train, label=y_var_train)
        dtest = xgb.DMatrix(X_var_test)

        xgb_params = {
            "max_leaves": config.max_leaves,
            "max_depth": config.max_depth,
            "learning_rate": config.learning_rate,
            "min_child_weight": config.min_child_weight,
            "subsample": config.subsample,
            "colsample_bytree": config.colsample_bytree,
            "reg_lambda": config.reg_lambda,
            "objective": "reg:squarederror",
            "tree_method": "hist",
            "verbosity": 0,
        }

        var_model = xgb.train(
            xgb_params,
            dtrain,
            num_boost_round=config.n_estimators,
            verbose_eval=False,
        )

        # Predict conditional variance σ²(x) for test samples
        sigma2_hat = var_model.predict(dtest)

        # Clip to [0, max_var] for safety
        sigma2_hat = np.clip(sigma2_hat, 0.0, config.max_var)

        # Apply correction as DELTA from the predicted mean:
        # The global Duan already captures the AVERAGE σ²/2 (≈0 for QLIKE models).
        # We redistribute: samples with higher predicted σ² get more correction,
        # samples with lower predicted σ² get less.
        # This works because the variance model's predictions DIFFER across samples
        # (unlike a constant which gives delta=0).
        mean_sigma2_pred = float(np.mean(sigma2_hat))
        delta = (sigma2_hat - mean_sigma2_pred) / 2.0

        # Clip delta for safety
        delta = np.clip(delta, -config.max_var / 2, config.max_var / 2)

        corrected.iloc[test_idx_k] = all_preds.iloc[test_idx_k].values + delta

        logger.debug(
            "Fold %d: conditional correction mean_delta=%.5f, std=%.4f, "
            "sigma2_range=[%.4f, %.4f], n_samples=%d",
            fold_k + 1,
            float(np.mean(delta)),
            float(np.std(delta)),
            float(np.min(sigma2_hat)),
            float(np.max(sigma2_hat)),
            len(test_idx_k),
        )

    # Report improvement
    valid_mask_post = corrected.notna() & y.notna()
    if valid_mask_post.sum() > 0:
        qlike_before = qlike(
            y[valid_mask_post].values, all_preds[valid_mask_post].values
        )
        qlike_after = qlike(
            y[valid_mask_post].values, corrected[valid_mask_post].values
        )
        improvement_bps = (qlike_before - qlike_after) / qlike_before * 10000
        logger.info(
            "Conditional Duan: QLIKE %.5f → %.5f (%+.1f bps)",
            qlike_before, qlike_after, improvement_bps,
        )

    return corrected


def _apply_vvix_proxy(
    all_preds: pd.Series,
    y: pd.Series,
    X: pd.DataFrame,
    fold_splits: list[tuple[np.ndarray, np.ndarray]],
    config: ConditionalDuanConfig,
    vvix_col: str = "vvix",
) -> pd.Series:
    """VVIX direct proxy mode: use VVIX as conditional variance estimate.

    VVIX (vol-of-vol) directly measures how uncertain the vol forecast is.
    Instead of training a second model, we calibrate a simple linear mapping:
        σ²(x) = alpha * vvix_squared

    where alpha is calibrated walk-forward from prior-fold residuals.
    The correction is then: delta_i = (σ²_hat_i - mean(σ²_hat)) / 2

    This avoids the risk of the variance model overfitting or not splitting.
    """
    vvix = X[vvix_col].values
    # Normalize to squared decimal form
    if vvix_col == "vvix":
        # Raw VVIX in index points (80-200), normalize to decimal
        vvix_normalized = (vvix / 100.0) ** 2
    else:
        # Already decimal (vvix_d = vvix/100)
        vvix_normalized = vvix ** 2

    corrected = all_preds.copy()
    n_folds = len(fold_splits)

    # Walk-forward alpha calibration
    for fold_k in range(n_folds):
        _, test_idx = fold_splits[fold_k]
        test_mask = all_preds.iloc[test_idx].notna()
        valid_test_idx = test_idx[test_mask.values]

        if len(valid_test_idx) == 0:
            continue

        # Collect prior fold residuals and VVIX for calibration
        prior_sq_resid = []
        prior_vvix_sq = []
        for i in range(fold_k):
            _, prior_test = fold_splits[i]
            prior_mask = all_preds.iloc[prior_test].notna()
            prior_valid = prior_test[prior_mask.values]
            if len(prior_valid) == 0:
                continue
            resid = y.iloc[prior_valid].values - all_preds.iloc[prior_valid].values
            prior_sq_resid.append(resid ** 2)
            prior_vvix_sq.append(vvix_normalized[prior_valid])

        if len(prior_sq_resid) == 0:
            continue

        all_sq_resid = np.concatenate(prior_sq_resid)
        all_vvix_sq = np.concatenate(prior_vvix_sq)

        # Calibrate alpha via simple OLS: σ² = alpha * vvix_normalized
        # alpha = cov(σ², vvix) / var(vvix) (regression through zero would
        # give E[σ²]/E[vvix], but OLS with intercept is more robust)
        valid = ~(np.isnan(all_sq_resid) | np.isnan(all_vvix_sq))
        if valid.sum() < 50:
            continue

        sq_r = all_sq_resid[valid]
        vvix_v = all_vvix_sq[valid]

        # Simple scaling: alpha = mean(σ²) / mean(vvix_normalized)
        # This maps VVIX scale to residual variance scale
        mean_vvix = float(np.mean(vvix_v))
        if mean_vvix < 1e-8:
            continue
        alpha = float(np.mean(sq_r)) / mean_vvix

        # Predict conditional σ² for this fold's test samples
        sigma2_hat = alpha * vvix_normalized[valid_test_idx]
        sigma2_hat = np.clip(sigma2_hat, 0.0, config.max_var)

        # Delta from mean (redistribute correction)
        mean_sigma2 = float(np.mean(sigma2_hat))
        delta = (sigma2_hat - mean_sigma2) / 2.0
        delta = np.clip(delta, -config.max_var / 2, config.max_var / 2)

        corrected.iloc[valid_test_idx] = all_preds.iloc[valid_test_idx].values + delta

        logger.debug(
            "Fold %d (VVIX proxy): alpha=%.4f, mean_delta=%.5f, "
            "sigma2_range=[%.4f, %.4f]",
            fold_k + 1, alpha, float(np.mean(delta)),
            float(np.min(sigma2_hat)), float(np.max(sigma2_hat)),
        )

    # Report
    valid_mask = corrected.notna() & y.notna()
    if valid_mask.sum() > 0:
        qlike_before = qlike(y[valid_mask].values, all_preds[valid_mask].values)
        qlike_after = qlike(y[valid_mask].values, corrected[valid_mask].values)
        improvement_bps = (qlike_before - qlike_after) / qlike_before * 10000
        logger.info(
            "Conditional Duan (VVIX proxy): QLIKE %.5f → %.5f (%+.1f bps)",
            qlike_before, qlike_after, improvement_bps,
        )

    return corrected
