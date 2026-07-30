"""SHAP and ALE explainability for tournament dashboard.

Provides TreeSHAP-based feature importance and Accumulated Local Effects
plots for tree-based models (LightGBM). ALE is implemented from scratch
using only numpy/pandas (no external dependency).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Lazy-detect shap availability
try:
    import shap  # noqa: F401

    _SHAP_AVAILABLE = True
except ImportError:
    _SHAP_AVAILABLE = False


@dataclass
class ExplainabilityConfig:
    """Configuration for explainability computation."""

    enabled: bool = False
    methods: list[str] = field(default_factory=lambda: ["treeshap", "ale"])
    treeshap_max_samples: int = 500
    treeshap_interaction: bool = False
    ale_features: str | list[str] = "top_20"
    ale_grid_size: int = 50
    models: list[str] | None = None  # None = all tree-based


def compute_treeshap(
    model: Any,
    X_test: pd.DataFrame,
    max_samples: int | None = 500,
    seed: int = 42,
) -> dict | None:
    """Compute TreeSHAP values for a trained LightGBM model.

    Uses shap.TreeExplainer which calls LightGBM's native C++ SHAP
    implementation for exact Shapley values in polynomial time.

    Parameters
    ----------
    model : object
        Trained model with ``_model`` (LightGBM Booster) and
        ``_feature_names`` attributes.
    X_test : pd.DataFrame
        Test features (OOS data from last CV fold).
    max_samples : int or None
        Subsample X_test to this many rows for speed. None = use all.
    seed : int
        Random seed for subsampling.

    Returns
    -------
    dict or None
        {
            "shap_values": np.ndarray (n_samples, n_features),
            "base_value": float,
            "feature_names": list[str],
            "feature_values": np.ndarray (n_samples, n_features),
            "summary": {
                "mean_abs_shap": [(name, value), ...],  # sorted desc
            },
        }
        Returns None if shap is not installed.
    """
    if not _SHAP_AVAILABLE:
        logger.info("shap package not installed — skipping TreeSHAP computation")
        return None

    booster = getattr(model, "_model", None)
    feature_names = getattr(model, "_feature_names", None)
    if booster is None or feature_names is None:
        logger.warning("Model missing _model or _feature_names — cannot compute SHAP")
        return None

    # Subsample if needed
    X = X_test[feature_names].copy()
    if max_samples is not None and len(X) > max_samples:
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(X), size=max_samples, replace=False)
        idx.sort()
        X = X.iloc[idx].reset_index(drop=True)

    # Compute SHAP values using TreeExplainer
    explainer = shap.TreeExplainer(booster)
    shap_values = explainer.shap_values(X)
    base_value = float(explainer.expected_value)

    # Build summary: mean |SHAP| per feature, sorted descending
    mean_abs = np.abs(shap_values).mean(axis=0)
    pairs = sorted(zip(feature_names, mean_abs.tolist()), key=lambda x: -x[1])

    return {
        "shap_values": shap_values,
        "base_value": base_value,
        "feature_names": feature_names,
        "feature_values": X.values,
        "summary": {
            "mean_abs_shap": pairs,
        },
    }


def compute_ale(
    model: Any,
    X_test: pd.DataFrame,
    features: list[str],
    grid_size: int = 50,
) -> dict[str, dict] | None:
    """Compute 1D Accumulated Local Effects for specified features.

    Pure numpy implementation — no external dependencies beyond numpy/pandas.

    ALE avoids the extrapolation problem of PDP by computing effects only
    within the observed conditional distribution. For each quantile bin of
    feature j, we compute the average change in prediction when moving from
    the bin's lower to upper edge, then accumulate and center.

    Parameters
    ----------
    model : object
        Model with a ``predict(X: pd.DataFrame) -> np.ndarray`` method.
    X_test : pd.DataFrame
        Feature matrix for ALE computation.
    features : list[str]
        Feature names to compute ALE for.
    grid_size : int
        Number of quantile bins.

    Returns
    -------
    dict[str, dict] or None
        {
            "feature_name": {
                "grid": list[float],  # Bin centers
                "ale": list[float],   # Accumulated local effect
                "rug": list[int],     # Sample count per bin
            }
        }
    """
    results = {}

    for feat in features:
        if feat not in X_test.columns:
            logger.warning("Feature %s not in X_test columns — skipping ALE", feat)
            continue

        # Drop NaN rows for this feature
        valid_mask = X_test[feat].notna()
        X_valid = X_test[valid_mask].copy()

        if len(X_valid) < grid_size:
            logger.warning(
                "Feature %s has only %d valid rows (need %d) — skipping",
                feat, len(X_valid), grid_size,
            )
            continue

        # Compute quantile bin edges
        feat_values = X_valid[feat].values
        quantiles = np.linspace(0, 1, grid_size + 1)
        bin_edges = np.quantile(feat_values, quantiles)

        # Ensure unique bin edges (collapse duplicates)
        bin_edges = np.unique(bin_edges)
        if len(bin_edges) < 3:
            # Feature is nearly constant — skip
            results[feat] = {
                "grid": [float(bin_edges[0])] * grid_size,
                "ale": [0.0] * grid_size,
                "rug": [len(X_valid)] + [0] * (grid_size - 1),
            }
            continue

        n_bins = len(bin_edges) - 1

        # Assign each sample to a bin
        bin_indices = np.digitize(feat_values, bin_edges[1:-1], right=False)
        # bin_indices is 0-based: 0 to n_bins-1

        # Compute local effects per bin
        local_effects = np.zeros(n_bins)
        rug_counts = np.zeros(n_bins, dtype=int)

        for k in range(n_bins):
            mask = bin_indices == k
            n_k = mask.sum()
            rug_counts[k] = n_k

            if n_k == 0:
                continue

            # For samples in bin k, compute f(x with feat=upper) - f(x with feat=lower)
            X_lower = X_valid.loc[mask].copy()
            X_upper = X_valid.loc[mask].copy()
            X_lower[feat] = bin_edges[k]
            X_upper[feat] = bin_edges[k + 1]

            pred_lower = model.predict(X_lower)
            pred_upper = model.predict(X_upper)

            # Handle any NaN predictions
            diff = pred_upper - pred_lower
            valid_diff = diff[~np.isnan(diff)]
            if len(valid_diff) > 0:
                local_effects[k] = valid_diff.mean()

        # Accumulate
        ale = np.cumsum(local_effects)

        # Center: subtract weighted mean
        total_samples = rug_counts.sum()
        if total_samples > 0:
            weighted_mean = np.average(ale, weights=rug_counts / total_samples)
            ale = ale - weighted_mean

        # Bin centers for x-axis
        grid_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        # Pad/resample to exactly grid_size points if bin collapsing reduced count
        if len(grid_centers) < grid_size:
            # Interpolate to target grid size
            target_grid = np.linspace(grid_centers[0], grid_centers[-1], grid_size)
            ale_interp = np.interp(target_grid, grid_centers, ale)
            # Distribute rug counts proportionally
            rug_interp = np.zeros(grid_size, dtype=int)
            for i, gc in enumerate(grid_centers):
                closest_idx = np.argmin(np.abs(target_grid - gc))
                rug_interp[closest_idx] += rug_counts[i]
            grid_centers = target_grid
            ale = ale_interp
            rug_counts = rug_interp

        results[feat] = {
            "grid": grid_centers.tolist(),
            "ale": ale.tolist(),
            "rug": rug_counts.tolist(),
        }

    return results if results else None


def compute_explainability(
    trained_models: dict[str, dict[int, Any]],
    test_data: dict[str, dict[int, pd.DataFrame]],
    config: ExplainabilityConfig,
    on_model_start: Any | None = None,
    on_horizon_complete: Any | None = None,
    on_model_complete: Any | None = None,
) -> dict[str, dict[int, dict]]:
    """Orchestrate SHAP and ALE computation for all configured models.

    Parameters
    ----------
    trained_models : dict[str, dict[int, Any]]
        {model_label: {horizon: model_object}}
    test_data : dict[str, dict[int, pd.DataFrame]]
        {model_label: {horizon: X_test DataFrame}}
    config : ExplainabilityConfig
        Explainability settings from YAML.

    Returns
    -------
    dict[str, dict[int, dict]]
        {model_label: {horizon: {"shap": shap_result, "ale": ale_result}}}
    """
    if not config.enabled:
        return {}

    results: dict[str, dict[int, dict]] = {}

    for model_label, horizon_models in trained_models.items():
        # Check if this model is in the configured list
        if config.models is not None and model_label not in config.models:
            continue

        # Check if model is tree-based (LightGBM or XGBoost)
        sample_model = next(iter(horizon_models.values()), None)
        if sample_model is None:
            continue
        booster = getattr(sample_model, "_model", None)
        if booster is None:
            continue
        # Verify it's a supported tree framework
        booster_type = type(booster).__module__
        if "lightgbm" not in booster_type and "xgboost" not in booster_type:
            continue

        model_results: dict[int, dict] = {}

        if on_model_start is not None:
            on_model_start(model_label, len(horizon_models))

        for h, model in horizon_models.items():
            X_test = (test_data.get(model_label) or {}).get(h)
            if X_test is None or X_test.empty:
                logger.info(
                    "No test data for %s h=%d — skipping explainability", model_label, h
                )
                continue

            h_result: dict[str, Any] = {}

            # TreeSHAP
            if "treeshap" in config.methods:
                shap_result = compute_treeshap(
                    model, X_test, max_samples=config.treeshap_max_samples
                )
                h_result["shap"] = shap_result
                if on_horizon_complete is not None:
                    on_horizon_complete(model_label, h, "treeshap")

            # ALE
            if "ale" in config.methods:
                # Determine which features to compute ALE for
                ale_features = _resolve_ale_features(
                    config.ale_features,
                    shap_result=h_result.get("shap"),
                    model=model,
                )
                if ale_features:
                    ale_result = compute_ale(
                        model, X_test, features=ale_features, grid_size=config.ale_grid_size
                    )
                    h_result["ale"] = ale_result
                    if on_horizon_complete is not None:
                        on_horizon_complete(model_label, h, "ale")

            if h_result:
                model_results[h] = h_result

        if model_results:
            results[model_label] = model_results

        if on_model_complete is not None:
            on_model_complete(model_label)

    return results


def _resolve_ale_features(
    config_value: str | list[str],
    shap_result: dict | None = None,
    model: Any = None,
) -> list[str]:
    """Resolve which features to compute ALE for.

    Supports:
    - "top_N" — top N features by SHAP importance (or gain if no SHAP)
    - "all" — all features
    - Explicit list of feature names
    """
    if isinstance(config_value, list):
        return config_value

    if config_value == "all":
        feature_names = getattr(model, "_feature_names", None)
        return feature_names or []

    # "top_N" pattern
    if config_value.startswith("top_"):
        try:
            n = int(config_value.split("_")[1])
        except (IndexError, ValueError):
            n = 10

        # Prefer SHAP-based ranking
        if shap_result is not None and "summary" in shap_result:
            ranked = shap_result["summary"]["mean_abs_shap"]
            return [name for name, _ in ranked[:n]]

        # Fallback to gain importance
        if model is not None and hasattr(model, "get_feature_importance"):
            importance = model.get_feature_importance(top_n=n)
            return [name for name, _ in importance]

    return []
