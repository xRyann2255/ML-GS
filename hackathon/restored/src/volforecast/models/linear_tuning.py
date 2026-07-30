"""Deterministic alpha grid search for regularized linear (HAR-family) models.

Optuna-free hyperparameter search for Ridge/Lasso/ElasticNet HAR variants.
Called from _BaseOLS.tune_and_fit inside each outer CV fold: scores every
(alpha, l1_ratio) combination on an inner expanding-window CV using the same
QLIKE + Duan-correction protocol as the outer evaluation, then returns the
best parameters.

Kept separate from models/_base.py so the scoring logic is unit-testable
without touching the model registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Callable

import numpy as np
import pandas as pd

from volforecast.evaluation.metrics import qlike
from volforecast.utils.cv import ExpandingWindowCV

# Default grids. Features are standardized inside every regularized model's
# sklearn pipeline (StandardScaler) and targets are log-RV. With ~10k pooled
# training rows, meaningful ridge shrinkage needs large alphas; lasso/enet
# alphas live on the coordinate-descent scale where 0.1 already zeroes
# most coefficients.
RIDGE_ALPHA_GRID: list[float] = [
    0.01, 0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, 3000.0, 10000.0,
]
SPARSE_ALPHA_GRID: list[float] = [
    1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1,
]
ENET_L1_RATIO_GRID: list[float] = [0.2, 0.5, 0.8, 0.95]

# Inner folds with fewer scored rows than this are skipped (unstable QLIKE).
MIN_INNER_TEST_ROWS = 30


@dataclass
class LinearTuningResult:
    """Outcome of one grid search (one outer fold, one model class)."""

    best_params: dict[str, float]
    best_inner_qlike: float
    grid_results: list[dict[str, Any]]


def duan_correction(residuals: np.ndarray) -> float:
    """Log smearing factor. MUST match Pipeline._run_horizon (runner.py)."""
    valid = residuals[~np.isnan(residuals)]
    if len(valid) == 0:
        return 0.0
    return float(np.log(np.mean(np.exp(np.clip(valid, -10.0, 10.0)))))


def _score_combo(
    model_cls: type,
    params: dict[str, float],
    X: pd.DataFrame,
    y: pd.Series,
    folds: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[float, int]:
    """Mean inner-fold QLIKE (log space, Duan-corrected) for one param combo."""
    fold_scores: list[float] = []
    for train_idx, test_idx in folds:
        X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
        X_te, y_te = X.iloc[test_idx], y.iloc[test_idx]
        model = model_cls(**params)
        model.fit(X_tr, y_tr)
        corr = duan_correction(y_tr.values - model.predict(X_tr))
        preds = model.predict(X_te) + corr
        mask = ~(np.isnan(preds) | y_te.isna().values)
        if int(mask.sum()) < MIN_INNER_TEST_ROWS:
            continue
        fold_scores.append(qlike(y_te.values[mask], preds[mask]))
    if not fold_scores:
        return float("inf"), 0
    return float(np.mean(fold_scores)), len(fold_scores)


def tune_linear_alpha(
    model_cls: type,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    param_grid: dict[str, list[float]],
    inner_cv_config,
    on_trial_complete: Callable[[int], None] | None = None,
    on_tuning_start: Callable[[int], None] | None = None,
    on_hpo_event: Callable[[dict], None] | None = None,
) -> LinearTuningResult | None:
    """Exhaustive grid search over param_grid on an inner expanding-window CV.

    Returns None when the training window is too small to build any inner
    fold (caller should fall back to class-default parameters). Ties are
    broken toward MORE regularization (larger alpha, then larger l1_ratio):
    when the data cannot distinguish shrinkage levels, prefer the more
    stable model.
    """
    cv = ExpandingWindowCV(
        min_train_size=inner_cv_config.train_size or max(252, len(X_train) // 2),
        test_size=inner_cv_config.test_size or 63,
        step_size=inner_cv_config.test_size or 63,
        purge_gap=inner_cv_config.purge_gap or 10,
    )
    folds = list(cv.split(X_train))
    if not folds:
        return None

    keys = sorted(param_grid)
    combos = [dict(zip(keys, vals)) for vals in product(*(param_grid[k] for k in keys))]

    # Signal HPO start (creates progress bar in UI)
    if on_tuning_start is not None:
        on_tuning_start(len(combos))
    if on_hpo_event is not None:
        on_hpo_event({"type": "tuning_start", "n_trials": len(combos), "n_gpus": 1, "max_epochs": 0})

    grid_results: list[dict[str, Any]] = []
    best_qlike_so_far = float("inf")
    best_trial_idx = 0
    for combo in combos:
        score, n_folds = _score_combo(model_cls, combo, X_train, y_train, folds)
        grid_results.append({"params": combo, "inner_qlike": score, "n_folds": n_folds})
        if on_trial_complete is not None:
            on_trial_complete(len(grid_results))
        if on_hpo_event is not None:
            if score < best_qlike_so_far:
                best_qlike_so_far = score
                best_trial_idx = len(grid_results)
            on_hpo_event({
                "type": "tuning_trial_complete",
                "qlike": score,
                "trial_num": len(grid_results),
                "device_id": 0,
                "params": combo,
                "state": "COMPLETE",
            })

    # Signal HPO complete (removes progress bar, logs summary)
    if on_hpo_event is not None:
        on_hpo_event({
            "type": "tuning_complete",
            "n_completed": len(grid_results),
            "n_pruned": 0,
            "best_qlike": best_qlike_so_far,
            "best_trial": best_trial_idx,
            "best_params": min(grid_results, key=lambda e: e["inner_qlike"])["params"] if grid_results else {},
        })

    def _rank(entry: dict[str, Any]) -> tuple[float, float, float]:
        p = entry["params"]
        return (entry["inner_qlike"], -p.get("alpha", 0.0), -p.get("l1_ratio", 0.0))

    best = min(grid_results, key=_rank)
    if not np.isfinite(best["inner_qlike"]):
        return None
    return LinearTuningResult(
        best_params=dict(best["params"]),
        best_inner_qlike=float(best["inner_qlike"]),
        grid_results=grid_results,
    )
