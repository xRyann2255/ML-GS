"""Evaluation metrics for realized volatility forecasting.

Primary metric: QLIKE (quasi-likelihood loss).
Secondary: MSE, MAE, R-squared.

QLIKE penalizes underestimation more severely than overestimation,
aligning with the economic asymmetry of volatility forecasting.
"""

from __future__ import annotations

import numpy as np


def qlike(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    log_space: bool = True,
) -> float:
    """Compute QLIKE (quasi-likelihood) loss.

    In variance space: QLIKE = mean(RV/h - log(RV/h) - 1)
    In log space: QLIKE = mean(exp(y_true - y_pred) - (y_true - y_pred) - 1)

    Raises ValueError if arrays differ in length or contain NaN.
    """
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)

    if len(y_true) != len(y_pred):
        raise ValueError(f"Arrays must have same length: {len(y_true)} vs {len(y_pred)}")
    if np.any(np.isnan(y_true)) or np.any(np.isnan(y_pred)):
        raise ValueError("Inputs must not contain NaN")

    if log_space:
        # y_true = log(RV), y_pred = log(h)
        # QLIKE = mean(exp(log(RV) - log(h)) - (log(RV) - log(h)) - 1)
        #       = mean(RV/h - log(RV/h) - 1)
        # Per Patton (2011, "Volatility Forecast Comparison Using Imperfect
        # Volatility Proxies", JBES). Log-space and variance-space are
        # algebraically equivalent; log-space avoids numerical issues.
        diff = y_true - y_pred
        # Symmetric clip at [-10, 10]: overflow protection only.
        # exp(10) ~ 22026, well within float64. Real data diffs are < 5.
        # Log-variance equivalence holds exactly within this range.
        return float(np.mean(np.exp(np.clip(diff, -10.0, 10.0)) - diff - 1.0))
    else:
        # Variance space: QLIKE = mean(RV/h - log(RV/h) - 1)
        # Floor predictions to prevent division by zero (ch11 guide:
        # "Clip predictions to a small positive floor")
        y_pred = np.maximum(y_pred, 1e-8)
        ratio = y_true / y_pred
        return float(np.mean(ratio - np.log(ratio) - 1.0))


def mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute mean squared error."""
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    return float(np.mean((y_true - y_pred) ** 2))


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute mean absolute error."""
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    return float(np.mean(np.abs(y_true - y_pred)))


def r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute R-squared (coefficient of determination)."""
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return 0.0
    return float(1.0 - ss_res / ss_tot)


def compute_all(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_name: str = "",
) -> dict[str, float]:
    """Compute all evaluation metrics.

    If model_name is provided, keys are prefixed (e.g., 'har_qlike').
    """
    results = {
        "qlike": qlike(y_true, y_pred, log_space=True),
        "mse": mse(y_true, y_pred),
        "mae": mae(y_true, y_pred),
        "r_squared": r_squared(y_true, y_pred),
    }
    if model_name:
        results = {f"{model_name}_{k}": v for k, v in results.items()}
    return results


def retransform_log_to_level(
    log_rv_pred: np.ndarray,
    residuals: np.ndarray | None = None,
    residual_variance: float | None = None,
) -> np.ndarray:
    """Apply Duan (1995) retransformation bias correction.

    Non-parametric (preferred): RV_hat = exp(log_RV_hat) * mean(exp(residuals))
    Parametric (fallback):      RV_hat = exp(log_RV_hat + sigma^2 / 2)

    The non-parametric version is distribution-free and correct for
    fat-tailed residuals where the parametric formula underestimates.

    Parameters
    ----------
    log_rv_pred : array
        Log-space predictions.
    residuals : array, optional
        In-sample residuals (y_true - y_pred in log-space). If provided,
        non-parametric smearing is used: mean(exp(residuals)).
    residual_variance : float, optional
        Variance of residuals. Used only when residuals is None
        (parametric fallback: exp(sigma^2/2)).

    Without this, exp(log-predictions) are systematically biased low
    because E[exp(X)] > exp(E[X]) for non-degenerate X.
    """
    log_rv_pred = np.asarray(log_rv_pred, dtype=np.float64)
    if residuals is not None:
        residuals = np.asarray(residuals, dtype=np.float64)
        smearing_factor = float(np.mean(np.exp(residuals)))
        return np.exp(log_rv_pred) * smearing_factor
    if residual_variance is None:
        residual_variance = 0.0
    return np.exp(log_rv_pred + residual_variance / 2.0)


def conditional_duan_correction(
    log_preds: np.ndarray,
    conditional_variance: np.ndarray,
    max_var: float = 1.0,
) -> np.ndarray:
    """Apply per-sample Duan correction using conditional variance estimates.

    corrected = log_preds + clip(conditional_variance, 0, max_var) / 2

    When forecast uncertainty varies across samples (heteroscedastic residuals),
    the QLIKE-optimal point forecast requires a LARGER correction on high-uncertainty
    days. This generalizes the global Duan scalar to a per-sample vector.

    Parameters
    ----------
    log_preds : array
        Log-space predictions from the base model.
    conditional_variance : array
        Per-sample estimated residual variance σ²(x). Must be same length
        as log_preds.
    max_var : float
        Upper clip for variance estimates (prevents extreme corrections
        from noisy variance model). Default 1.0.

    Returns
    -------
    ndarray (float64)
        Corrected log-space predictions.
    """
    log_preds = np.asarray(log_preds, dtype=np.float64)
    conditional_variance = np.asarray(conditional_variance, dtype=np.float64)
    if len(log_preds) != len(conditional_variance):
        raise ValueError(
            f"Arrays must have same length: {len(log_preds)} vs {len(conditional_variance)}"
        )
    clipped_var = np.clip(conditional_variance, 0.0, max_var)
    return log_preds + clipped_var / 2.0


def qlike_improvement_bps(
    qlike_baseline: float,
    qlike_model: float,
) -> float:
    """Compute QLIKE improvement in basis points.

    bps = (qlike_baseline - qlike_model) / qlike_baseline * 10000
    Positive = model is better.
    """
    if qlike_baseline == 0:
        return 0.0
    return (qlike_baseline - qlike_model) / qlike_baseline * 10000.0
