"""SHAP-based feature selection for LightGBM models.

Implements Boruta-style shadow-feature thresholding using TreeSHAP values
computed on out-of-sample validation data. Runs inside each outer CV fold
to prevent data leakage.

Algorithm:
1. Fit full-feature LightGBM on training data
2. Compute TreeSHAP on validation split (OOS from trees)
3. Generate shadow features (random permutations of real columns)
4. threshold = max(shadow mean|SHAP|) * threshold_multiplier
5. Keep features where mean|SHAP| > threshold (subject to min_features)
6. (RFE) Repeat on pruned set up to max_rounds until stable
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SelectionResult:
    """Result of SHAP feature selection for one CV fold."""

    selected_features: list[str]
    dropped_features: list[str]
    feature_importances: dict[str, float]  # mean |SHAP| per feature
    shadow_threshold: float
    n_rounds: int
    round_history: list[dict[str, Any]] = field(default_factory=list)


def select_features(
    model_cls: type,
    model_params: dict[str, Any],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    config: Any,
    seed: int = 42,
) -> SelectionResult:
    """Run SHAP-based feature selection on a single CV fold.

    Parameters
    ----------
    model_cls : type
        LightGBM model class (must have fit/predict/_model/_feature_names).
    model_params : dict
        Model hyperparameters for instantiation.
    X_train : pd.DataFrame
        Full training features for this fold.
    y_train : pd.Series
        Training target for this fold.
    config : FeatureSelectionConfig
        Selection configuration.
    seed : int
        Random seed for shadow feature generation and SHAP subsampling.

    Returns
    -------
    SelectionResult
        Selected/dropped features with metadata.
    """
    max_rounds = 1 if config.method == "boruta_shap" else config.max_rounds
    current_features = list(X_train.columns)
    round_history: list[dict[str, Any]] = []
    rng = np.random.default_rng(seed)

    for round_num in range(1, max_rounds + 1):
        X_round = X_train[current_features]

        # Split into train/val for SHAP computation (use last 20% as val,
        # respecting time order for panel data)
        n = len(X_round)
        val_size = max(50, int(n * 0.2))
        train_end = n - val_size
        X_fit = X_round.iloc[:train_end]
        y_fit = y_train.iloc[:train_end]
        X_val = X_round.iloc[train_end:]

        # Fit model on training portion
        model = model_cls(**model_params)
        model.fit(X_fit, y_fit)

        # Compute TreeSHAP on validation set
        shap_values = _compute_shap(model, X_val, config.shap_samples, seed)
        if shap_values is None:
            logger.warning("SHAP computation failed in round %d — keeping all features", round_num)
            break

        # Compute mean |SHAP| for real features
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        feature_importances = dict(zip(current_features, mean_abs_shap.tolist()))

        # Generate shadow features and compute their SHAP importance
        shadow_threshold = _compute_shadow_threshold(
            model_cls=model_cls,
            model_params=model_params,
            X_fit=X_fit,
            y_fit=y_fit,
            X_val=X_val,
            current_features=current_features,
            n_shadow=config.shadow_features,
            shap_samples=config.shap_samples,
            threshold_multiplier=config.threshold_multiplier,
            rng=rng,
            seed=seed,
        )

        # Apply selection rule
        kept = [f for f in current_features if feature_importances[f] > shadow_threshold]
        dropped = [f for f in current_features if f not in kept]

        # Enforce min_features floor
        if len(kept) < config.min_features:
            # Keep top min_features by importance
            sorted_feats = sorted(current_features, key=lambda f: -feature_importances[f])
            kept = sorted_feats[: config.min_features]
            dropped = [f for f in current_features if f not in kept]

        round_history.append({
            "round": round_num,
            "n_features_in": len(current_features),
            "n_features_out": len(kept),
            "n_dropped": len(dropped),
            "threshold": shadow_threshold,
            "dropped": dropped,
        })

        logger.info(
            "SHAP selection round %d: %d → %d features (threshold=%.6f, dropped %d)",
            round_num,
            len(current_features),
            len(kept),
            shadow_threshold,
            len(dropped),
        )

        # Check convergence
        if len(dropped) == 0:
            break
        current_features = kept

    # Final importances (from last round)
    all_dropped = [f for f in X_train.columns if f not in current_features]

    return SelectionResult(
        selected_features=current_features,
        dropped_features=all_dropped,
        feature_importances=feature_importances if round_history else {},
        shadow_threshold=shadow_threshold if round_history else 0.0,
        n_rounds=len(round_history),
        round_history=round_history,
    )


def _compute_shap(
    model: Any,
    X_val: pd.DataFrame,
    max_samples: int,
    seed: int,
) -> np.ndarray | None:
    """Compute TreeSHAP values, returning array of shape (n_samples, n_features)."""
    try:
        import shap
    except ImportError:
        logger.error("shap package not installed — cannot perform feature selection")
        return None

    booster = getattr(model, "_model", None)
    feature_names = getattr(model, "_feature_names", None)
    if booster is None or feature_names is None:
        return None

    X = X_val[feature_names].copy()
    if max_samples is not None and len(X) > max_samples:
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(X), size=max_samples, replace=False)
        idx.sort()
        X = X.iloc[idx].reset_index(drop=True)

    explainer = shap.TreeExplainer(booster)
    shap_values = explainer.shap_values(X)
    return shap_values


def _compute_shadow_threshold(
    model_cls: type,
    model_params: dict[str, Any],
    X_fit: pd.DataFrame,
    y_fit: pd.Series,
    X_val: pd.DataFrame,
    current_features: list[str],
    n_shadow: int,
    shap_samples: int,
    threshold_multiplier: float,
    rng: np.random.Generator,
    seed: int,
) -> float:
    """Compute the Boruta shadow-feature threshold.

    Generates n_shadow random permutation features, fits a model with
    real + shadow features, computes SHAP, and returns:
        threshold = max(shadow mean|SHAP|) * threshold_multiplier

    Parameters
    ----------
    model_cls, model_params : model class and params for fitting
    X_fit, y_fit : training data for shadow model
    X_val : validation data for SHAP
    current_features : real feature names
    n_shadow : number of shadow features to generate
    shap_samples : max SHAP samples
    threshold_multiplier : scale factor on max shadow importance
    rng : numpy random Generator
    seed : random seed

    Returns
    -------
    float
        The shadow-based importance threshold.
    """
    # Generate shadow features by permuting random real features
    shadow_names = []
    X_fit_shadow = X_fit.copy()
    X_val_shadow = X_val.copy()

    source_features = rng.choice(current_features, size=min(n_shadow, len(current_features)), replace=False)
    for i, src_feat in enumerate(source_features):
        shadow_name = f"__shadow_{i}__"
        shadow_names.append(shadow_name)
        # Permute the training column
        X_fit_shadow[shadow_name] = rng.permutation(X_fit[src_feat].values)
        # Permute the validation column independently
        X_val_shadow[shadow_name] = rng.permutation(X_val[src_feat].values)

    # Fit model with real + shadow features
    all_features = current_features + shadow_names
    model = model_cls(**model_params)
    model.fit(X_fit_shadow[all_features], y_fit)

    # Compute SHAP on val with shadow features included
    shap_values = _compute_shap(model, X_val_shadow[all_features], shap_samples, seed)
    if shap_values is None:
        # Fallback: use 0 threshold (keep everything)
        return 0.0

    mean_abs = np.abs(shap_values).mean(axis=0)
    feature_names_all = list(model._feature_names) if model._feature_names else all_features

    # Extract shadow feature importances
    shadow_importances = []
    for sn in shadow_names:
        if sn in feature_names_all:
            idx = feature_names_all.index(sn)
            shadow_importances.append(mean_abs[idx])

    if not shadow_importances:
        return 0.0

    threshold = float(np.max(shadow_importances)) * threshold_multiplier
    return threshold


def aggregate_fold_selections(
    fold_results: list[SelectionResult],
    stability_threshold: float = 0.8,
) -> dict[str, Any]:
    """Aggregate feature selection results across CV folds.

    Parameters
    ----------
    fold_results : list of SelectionResult
        One result per outer CV fold.
    stability_threshold : float
        Fraction of folds a feature must be selected in to be "stable".

    Returns
    -------
    dict
        {
            "stable_features": list[str],  # kept in >= stability_threshold folds
            "unstable_features": list[str],  # kept in some but not enough folds
            "always_dropped": list[str],  # never selected in any fold
            "per_feature_selection_rate": dict[str, float],  # fraction of folds selected
            "mean_importances": dict[str, float],  # avg mean|SHAP| across folds
            "n_folds": int,
        }
    """
    if not fold_results:
        return {
            "stable_features": [],
            "unstable_features": [],
            "always_dropped": [],
            "per_feature_selection_rate": {},
            "mean_importances": {},
            "n_folds": 0,
        }

    n_folds = len(fold_results)
    all_features = set()
    selection_counts: dict[str, int] = {}
    importance_sums: dict[str, float] = {}
    importance_counts: dict[str, int] = {}

    for result in fold_results:
        for f in result.selected_features:
            all_features.add(f)
            selection_counts[f] = selection_counts.get(f, 0) + 1
        for f in result.dropped_features:
            all_features.add(f)
        for f, imp in result.feature_importances.items():
            importance_sums[f] = importance_sums.get(f, 0.0) + imp
            importance_counts[f] = importance_counts.get(f, 0) + 1

    selection_rate = {f: selection_counts.get(f, 0) / n_folds for f in all_features}
    mean_importances = {
        f: importance_sums.get(f, 0.0) / importance_counts[f]
        for f in all_features
        if f in importance_counts and importance_counts[f] > 0
    }

    stable = sorted([f for f, rate in selection_rate.items() if rate >= stability_threshold])
    unstable = sorted([f for f, rate in selection_rate.items() if 0 < rate < stability_threshold])
    always_dropped = sorted([f for f, rate in selection_rate.items() if rate == 0])

    return {
        "stable_features": stable,
        "unstable_features": unstable,
        "always_dropped": always_dropped,
        "per_feature_selection_rate": selection_rate,
        "mean_importances": mean_importances,
        "n_folds": n_folds,
        "stability_threshold": stability_threshold,
    }
