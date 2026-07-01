"""Pipeline orchestration: config-driven experiment execution.

The Pipeline class resolves models and feature layers from registries,
loops over forecast horizons, trains, evaluates, and returns results.
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from volforecast.config import ExperimentConfig
from volforecast.evaluation.metrics import mse, qlike, r_squared
from volforecast.registry import FEATURE_REGISTRY, MODEL_REGISTRY, ensure_registered
from volforecast.utils.cv import (
    BlockedKFoldCV,
    ExpandingWindowCV,
    PanelExpandingWindowCV,
    PurgedKFoldCV,
    RollingWindowCV,
)
from volforecast.utils.targets import forward_log_rv

# Exposed at module level for testability (patching in tests).
from volforecast.data.sequence_cache import (  # noqa: E402
    SequenceTensor as SequenceTensor,
    apply_normaliser as apply_normaliser,
    fit_seq_normaliser as fit_seq_normaliser,
)

logger = logging.getLogger(__name__)

# Bump on any structural change to feature-stack cache format.
FEATURE_STACK_CACHE_VERSION = 2


# ---------------------------------------------------------------------------
# Tabular fold worker — module-level for picklability (ProcessPoolExecutor)
# ---------------------------------------------------------------------------


def _execute_tabular_fold(
    fold_num: int,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    model_cls_name: str,
    model_params: dict[str, Any],
    device_id: int | None = None,
) -> dict[str, Any]:
    """Execute a single CV fold for a tabular model (XGBoost/LightGBM).

    Self-contained, designed for ProcessPoolExecutor workers.
    Each worker trains one fold on a pinned GPU device (or CPU).

    Parameters
    ----------
    fold_num : int
        Fold number (1-indexed).
    X_train, y_train : DataFrame, Series
        Training data for this fold.
    X_test : DataFrame
        Test features for this fold.
    model_cls_name : str
        Registry name of the model (e.g. "xgboost").
    model_params : dict
        Model hyperparameters.
    device_id : int or None
        GPU device index. When provided, sets device="cuda:{device_id}".

    Returns
    -------
    dict with keys: fold_num, preds, duan_correction
    """
    from volforecast.registry import MODEL_REGISTRY, ensure_registered

    ensure_registered()
    model_cls = MODEL_REGISTRY[model_cls_name]

    # Build per-fold params with GPU pinning and seed offset
    fold_params = dict(model_params)
    if device_id is not None:
        fold_params["device"] = f"cuda:{device_id}"
    # Per-fold seed for reproducibility regardless of execution order
    base_seed = fold_params.get("seed", 42)
    fold_params["seed"] = base_seed + fold_num

    model = model_cls(**fold_params)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)

    # Duan (1995) retransformation correction
    train_preds = model.predict(X_train)
    train_residuals = y_train.values - train_preds
    valid_resid = train_residuals[~np.isnan(train_residuals)]
    if len(valid_resid) > 0:
        correction = float(np.log(np.mean(np.exp(np.clip(valid_resid, -10.0, 10.0)))))
    else:
        correction = 0.0

    return {
        "fold_num": fold_num,
        "preds": preds + correction,
        "duan_correction": correction,
    }


# ---------------------------------------------------------------------------
# GNN fold worker — module-level for picklability (ProcessPoolExecutor)
# ---------------------------------------------------------------------------


def _execute_gnn_fold(
    fold_num: int,
    train_graph_dicts: list[dict],
    test_graph_dicts: list[dict],
    model_cls_name: str,
    model_params: dict,
    device_id: int,
    requested_outputs: list[str],
    n_rows: int,
    progress_queue=None,
) -> dict:
    """Worker for parallel GNN feature-stack fold execution.

    Runs in a spawned process — must be module-level (picklable).
    """
    import numpy as np

    from volforecast.registry import MODEL_REGISTRY, ensure_registered

    ensure_registered()
    model_cls = MODEL_REGISTRY[model_cls_name]

    params = dict(model_params)
    params["device"] = f"cuda:{device_id}"

    def _on_progress(epoch, max_epochs):
        if progress_queue is not None:
            progress_queue.put(
                {"type": "epoch", "fold": fold_num, "epoch": epoch, "max_epochs": max_epochs}
            )

    gnn = model_cls(**params)
    gnn.fit(train_graph_dicts, on_progress=_on_progress)

    all_graphs = train_graph_dicts + test_graph_dicts
    extracted = gnn.extract_features(all_graphs, outputs=requested_outputs)

    # Build result columns aligned by row indices embedded in each graph dict
    result_cols = {}
    for key, arr in extracted.items():
        col_name = f"gnn_{key}"
        full_col = np.full(n_rows, np.nan, dtype=np.float32)
        offset = 0
        for g in all_graphs:
            n_nodes = g["x"].shape[0] if hasattr(g["x"], "shape") else len(g["x"])
            row_indices_g = g["_row_indices"]
            full_col[row_indices_g] = arr[offset : offset + n_nodes]
            offset += n_nodes
        result_cols[col_name] = full_col

    return {"fold_num": fold_num, "result_cols": result_cols}


# ---------------------------------------------------------------------------
# Sequence fold worker — module-level for picklability (ProcessPoolExecutor)
# ---------------------------------------------------------------------------


def _execute_fold(
    fold_num: int,
    h: int,
    train_idx_arr: np.ndarray,
    test_idx_arr: np.ndarray,
    tensor,  # torch.Tensor (shared memory)
    lengths,  # torch.Tensor (shared memory)
    symbol_ids_tensor,  # torch.Tensor (shared memory)
    idx: pd.MultiIndex,
    y_values: np.ndarray,
    model_cls_name: str,
    model_params: dict[str, Any],
    spec_features: tuple[str, ...],
    base_cfg_dict: dict | None,
    base_X: pd.DataFrame | None,
    base_y: pd.Series | None,
    config_dict: dict,
    cache_enabled: bool,
    cache_root: str | None,
    device_id: int | None,
    seed_offset: int,
    norm_mode: str = "pooled",
    progress_queue=None,  # mp.Manager().Queue() for epoch progress events
) -> dict[str, Any]:
    """Execute a single CV fold — self-contained, no shared mutable state.

    Designed for use in ProcessPoolExecutor workers. Each worker trains one
    fold on a pinned GPU device (or CPU). Returns a dict with fold results.
    """
    import torch

    from volforecast.data.sequence_cache import SequenceTensor, apply_normaliser, fit_seq_normaliser
    from volforecast.pipeline.fold_cache import compute_fold_cache_key, load_fold_cache, save_fold_cache
    from volforecast.registry import MODEL_REGISTRY, ensure_registered

    # Spawned workers don't auto-import model modules; trigger registration.
    ensure_registered()

    config = config_dict  # Actually an ExperimentConfig (picklable dataclass)
    model_cls = MODEL_REGISTRY[model_cls_name]
    _cache_root = Path(cache_root) if cache_root else None

    fold_train_idx = idx[train_idx_arr]
    fold_test_idx = idx[test_idx_arr]
    fold_train_dates = pd.DatetimeIndex(fold_train_idx.get_level_values("date").unique())
    fold_test_dates = pd.DatetimeIndex(fold_test_idx.get_level_values("date").unique())

    # ---- Per-fold base-model fit + alignment ---
    base_preds_train: np.ndarray | None = None
    base_preds_test: np.ndarray | None = None
    if base_cfg_dict is not None and base_X is not None and base_y is not None:
        from volforecast.config import BaseModelConfig

        base_cfg = BaseModelConfig(
            name=base_cfg_dict["name"],
            feature_layers=base_cfg_dict.get("feature_layers", []),
            params=base_cfg_dict.get("params", {}),
        )
        base_cls = MODEL_REGISTRY[base_cfg.name]
        max_train_date = pd.Timestamp(fold_train_idx.get_level_values("date").max())
        base_date = pd.DatetimeIndex(base_X.index.get_level_values("date"))
        base_train_mask = base_date <= max_train_date
        base_X_train = base_X.loc[base_train_mask]
        base_y_train = base_y.loc[base_train_mask]
        if base_X_train.empty:
            raise RuntimeError(
                f"h={h} fold={fold_num}: base_model has no training "
                f"rows on or before {max_train_date}"
            )
        base_inst = base_cls(**base_cfg.params)
        base_inst.fit(base_X_train, base_y_train)

        all_base_preds_arr = np.asarray(base_inst.predict(base_X), dtype=np.float64)
        all_base_preds = pd.Series(all_base_preds_arr, index=base_X.index)
        train_pred_slice = all_base_preds.loc[base_train_mask]
        fallback = float(np.nanmean(train_pred_slice.values))
        if not np.isfinite(fallback):
            fallback = 0.0

        def _lookup(seq_idx: pd.MultiIndex) -> np.ndarray:
            aligned = all_base_preds.reindex(seq_idx).values.astype(np.float64)
            nan_mask = np.isnan(aligned)
            if nan_mask.any():
                aligned[nan_mask] = fallback
            return aligned.astype(np.float32)

        base_preds_train = _lookup(fold_train_idx)
        base_preds_test = _lookup(fold_test_idx)

    # ---- Cache lookup ---
    cache_key = compute_fold_cache_key(
        config, h, fold_num, fold_train_dates, fold_test_dates,
        base_preds_train=base_preds_train, base_preds_test=base_preds_test,
    )
    if cache_enabled:
        cache_hit = load_fold_cache(config=config, key=cache_key, cache_root=_cache_root)
        if cache_hit is not None and cache_hit.preds.shape[0] == len(test_idx_arr):
            return {
                "fold_num": fold_num,
                "test_idx_arr": test_idx_arr,
                "preds": cache_hit.preds,
                "duan_correction": cache_hit.duan_correction,
                "model_path": cache_hit.model_path,
                "cache_hit": True,
            }

    # ---- Normalise + train ---
    tr_pos = torch.from_numpy(np.ascontiguousarray(train_idx_arr)).to(torch.long)
    te_pos = torch.from_numpy(np.ascontiguousarray(test_idx_arr)).to(torch.long)
    X_tr = tensor.index_select(0, tr_pos)
    L_tr = lengths.index_select(0, tr_pos)
    y_tr_arr = y_values[train_idx_arr]
    X_te = tensor.index_select(0, te_pos)
    L_te = lengths.index_select(0, te_pos)
    sym_ids_tr = symbol_ids_tensor.index_select(0, tr_pos)
    sym_ids_te = symbol_ids_tensor.index_select(0, te_pos)

    if norm_mode == "per_symbol":
        from volforecast.pipeline.norm import (
            apply_per_symbol_normaliser,
            fit_per_symbol_normaliser,
        )

        normalisers = fit_per_symbol_normaliser(X_tr, L_tr, sym_ids_tr)
        tr_normed_tensor = apply_per_symbol_normaliser(X_tr, L_tr, sym_ids_tr, normalisers)
        te_normed_tensor = apply_per_symbol_normaliser(X_te, L_te, sym_ids_te, normalisers)
        tr_synth = pd.DatetimeIndex(pd.bdate_range("2000-01-01", periods=int(X_tr.shape[0])))
        tr_normed = SequenceTensor(
            symbol="_pooled_train",
            tensor=tr_normed_tensor,
            lengths=L_tr,
            dates=tr_synth,
            feature_names=spec_features,
        )
        te_synth = pd.DatetimeIndex(pd.bdate_range("2000-01-01", periods=int(X_te.shape[0])))
        te_normed = SequenceTensor(
            symbol="_pooled_test",
            tensor=te_normed_tensor,
            lengths=L_te,
            dates=te_synth,
            feature_names=spec_features,
        )
    else:
        tr_synth = pd.DatetimeIndex(pd.bdate_range("2000-01-01", periods=int(X_tr.shape[0])))
        tr_pseudo = SequenceTensor(
            symbol="_pooled_train",
            tensor=X_tr,
            lengths=L_tr,
            dates=tr_synth,
            feature_names=spec_features,
        )
        mean, std = fit_seq_normaliser(tr_pseudo, tr_synth)
        tr_normed = apply_normaliser(tr_pseudo, mean, std)

        te_synth = pd.DatetimeIndex(pd.bdate_range("2000-01-01", periods=int(X_te.shape[0])))
        te_pseudo = SequenceTensor(
            symbol="_pooled_test",
            tensor=X_te,
            lengths=L_te,
            dates=te_synth,
            feature_names=spec_features,
        )
        te_normed = apply_normaliser(te_pseudo, mean, std)

    # Override device to the assigned GPU
    fold_model_params = dict(model_params)
    if device_id is not None:
        fold_model_params["device"] = f"cuda:{device_id}"
    # Per-fold seed for reproducibility regardless of execution order
    fold_model_params["seed"] = fold_model_params.get("seed", 42) + seed_offset

    model = model_cls(**fold_model_params)
    # Only pass symbol_ids when the model supports embedding.
    _use_sym_ids = getattr(model, "n_symbols", 0) > 0

    # Build on_progress callback that posts epoch events to the queue.
    _on_progress = None
    if progress_queue is not None:
        def _on_progress(epoch: int, max_epochs: int) -> None:
            progress_queue.put({"type": "epoch", "fold": fold_num, "epoch": epoch, "max_epochs": max_epochs})

    fit_kwargs: dict[str, Any] = {}
    if _use_sym_ids:
        fit_kwargs["symbol_ids"] = sym_ids_tr
    if base_preds_train is not None:
        fit_kwargs["base_preds"] = base_preds_train
    if _on_progress is not None:
        fit_kwargs["on_progress"] = _on_progress
    model.fit(tr_normed, y_tr_arr, **fit_kwargs)

    if _use_sym_ids:
        if base_preds_test is not None:
            preds = np.asarray(model.predict(te_normed, base_preds=base_preds_test, symbol_ids=sym_ids_te), dtype=np.float64)
            train_preds = np.asarray(model.predict(tr_normed, base_preds=base_preds_train, symbol_ids=sym_ids_tr), dtype=np.float64)
        else:
            preds = np.asarray(model.predict(te_normed, symbol_ids=sym_ids_te), dtype=np.float64)
            train_preds = np.asarray(model.predict(tr_normed, symbol_ids=sym_ids_tr), dtype=np.float64)
    else:
        if base_preds_test is not None:
            preds = np.asarray(model.predict(te_normed, base_preds=base_preds_test), dtype=np.float64)
            train_preds = np.asarray(model.predict(tr_normed, base_preds=base_preds_train), dtype=np.float64)
        else:
            preds = np.asarray(model.predict(te_normed), dtype=np.float64)
            train_preds = np.asarray(model.predict(tr_normed), dtype=np.float64)

    # Duan retransformation
    train_residuals = y_tr_arr - train_preds
    valid_resid = train_residuals[~np.isnan(train_residuals)]
    if len(valid_resid) > 0:
        correction = float(np.log(np.mean(np.exp(np.clip(valid_resid, -10.0, 10.0)))))
    else:
        correction = 0.0
    preds = preds + correction

    # Save to cache (best-effort) and capture model_path for the caller
    model_path = None
    if cache_enabled:
        try:
            cache_dir = save_fold_cache(
                config=config, key=cache_key, preds=preds,
                duan_correction=correction, model=model,
                train_dates=fold_train_dates, test_dates=fold_test_dates,
                h=h, fold_num=fold_num, cache_root=_cache_root,
            )
            saved = cache_dir / "model.pt"
            if saved.exists():
                model_path = str(saved)
        except Exception:  # noqa: BLE001
            pass

    return {
        "fold_num": fold_num,
        "test_idx_arr": test_idx_arr,
        "preds": preds,
        "duan_correction": correction,
        "model_path": model_path,
        "cache_hit": False,
    }


def _build_cv_splitter(cv_config, purge_gap_override: int | None = None) -> Any:
    """Resolve CV splitter from config."""
    method = cv_config.method
    purge_gap = purge_gap_override if purge_gap_override is not None else cv_config.purge_gap
    embargo = getattr(cv_config, "embargo", 0)
    if method == "purged_kfold":
        return PurgedKFoldCV(n_splits=cv_config.n_splits, purge_gap=purge_gap, embargo=embargo)
    elif method == "expanding_window":
        return ExpandingWindowCV(
            min_train_size=cv_config.train_size or 252,
            test_size=cv_config.test_size or 63,
            purge_gap=purge_gap,
            embargo=embargo,
        )
    elif method == "rolling_window":
        return RollingWindowCV(
            train_size=cv_config.train_size or 756,
            test_size=cv_config.test_size or 63,
            purge_gap=purge_gap,
            embargo=embargo,
        )
    elif method == "blocked_kfold":
        return BlockedKFoldCV(n_splits=cv_config.n_splits, embargo=embargo)
    else:
        raise ValueError(f"Unknown CV method: {method!r}")


class Pipeline:
    """Config-driven experiment pipeline.

    Usage::

        config = ExperimentConfig.from_yaml("configs/baseline.yaml")
        results = Pipeline(config).run(daily_data)
    """

    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        ensure_registered()

    def _run_horizon(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        cv,
        model_cls,
        h: int,
        on_fold_complete: Any | None = None,
        *,
        X_for_cv: pd.DataFrame | None = None,
        on_train_progress: Any | None = None,
        gpu_device_id: int | None = None,
        feature_stack_fn: Any | None = None,
    ) -> dict[str, Any]:
        """Single-horizon walk-forward: fit/predict/evaluate across CV folds.

        Applies per-fold Duan (1995) retransformation correction to predictions.
        OLS-trained models (HAR, Ridge, Lasso) target E[log(RV)|X], but QLIKE
        is minimized at E[log(RV)|X] + correction where correction =
        log(mean(exp(train_residuals))). This is the non-parametric smearing
        estimator, distribution-free and correct for fat-tailed residuals.

        Parameters
        ----------
        feature_stack_fn : callable, optional
            If provided, called as ``feature_stack_fn(train_idx, test_idx, h)``
            per fold. Returns a DataFrame with the same index as X, containing
            extra columns to append to X_train/X_test for this fold.
        """
        cv_input = X_for_cv if X_for_cv is not None else X
        all_preds = pd.Series(dtype=float, index=y.index)
        fold_num = 0
        fold_splits_stored: list[tuple[np.ndarray, np.ndarray]] = []
        model = None
        duan_corrections: list[float] = []

        tuning_enabled = self.config.tuning.enabled and getattr(model_cls, "supports_tuning", False)
        tune_every = self.config.tuning.tune_every_n_folds
        cached_params: dict | None = None

        # SHAP feature selection state
        fs_config = self.config.feature_selection
        fs_enabled = (
            fs_config is not None
            and fs_config.enabled
            and getattr(model_cls, "supports_tuning", False)
        )
        fold_selection_results: list = []

        # Ensure internal validation purge gap covers the forecast horizon
        # to prevent label leakage in early stopping (h=22 targets overlap).
        model_params = self.config.model_params_for_horizon(h)
        if "val_purge_gap" in model_params:
            model_params["val_purge_gap"] = max(model_params["val_purge_gap"], h)

        # Pin this horizon to a specific GPU (for multi-GPU parallelism).
        # Only inject gpu_device_id for models that support tuning (LightGBM),
        # since linear models (HAR, EWMA, Ridge) don't accept GPU params.
        if gpu_device_id is not None and getattr(model_cls, "supports_tuning", False):
            model_params["gpu_device_id"] = gpu_device_id

        # ── GPU fold-level parallelism for tabular models (XGBoost) ──────
        # When device=cuda + n_gpus > 1 + model is tabular tree, dispatch
        # all CV folds to a ProcessPoolExecutor with GPU pinning.
        device_str = model_params.get("device", "cpu")
        n_gpus = getattr(self.config, "n_gpus", 1)
        use_gpu_parallel = (
            n_gpus > 1
            and device_str.startswith("cuda")
            and getattr(model_cls, "family", "") in ("xgboost",)
            and not tuning_enabled  # HPO handles its own parallelism
            and not fs_enabled  # SHAP selection needs sequential fold state
            and feature_stack_fn is None  # Feature stacking not supported in parallel
        )

        if use_gpu_parallel:
            return self._run_horizon_gpu_parallel(
                X, y, cv, model_cls, h, model_params, n_gpus,
                X_for_cv=X_for_cv,
                on_fold_complete=on_fold_complete,
            )

        for train_idx, test_idx in cv.split(cv_input):
            fold_num += 1
            fold_splits_stored.append((train_idx, test_idx))
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]

            # Inject feature-stack columns (e.g. LSTM predictions) if configured
            if feature_stack_fn is not None:
                fs_cols = feature_stack_fn(train_idx, test_idx, h)
                if fs_cols is not None and not fs_cols.empty:
                    # Align by index — fs_cols covers full panel, select fold rows
                    fs_train = fs_cols.reindex(X_train.index)
                    fs_test = fs_cols.reindex(X_test.index)
                    X_train = pd.concat([X_train, fs_train], axis=1)
                    X_test = pd.concat([X_test, fs_test], axis=1)
            y_train = y.iloc[train_idx]

            # SHAP feature selection: run per-fold to prevent leakage
            if fs_enabled:
                from volforecast.pipeline.feature_selection import select_features

                sel_result = select_features(
                    model_cls=model_cls,
                    model_params=model_params,
                    X_train=X_train,
                    y_train=y_train,
                    config=fs_config,
                    seed=self.config.seed + fold_num,
                )
                fold_selection_results.append(sel_result)
                # Filter to selected features for this fold
                X_train = X_train[sel_result.selected_features]
                X_test = X_test[sel_result.selected_features]
                logger.info(
                    "Fold %d (h=%d): SHAP selection kept %d/%d features",
                    fold_num, h, len(sel_result.selected_features),
                    len(sel_result.selected_features) + len(sel_result.dropped_features),
                )

            should_tune = (
                tuning_enabled
                and len(X_train) >= self.config.tuning.min_train_size
                and (fold_num - 1) % tune_every == 0
            )

            if should_tune:
                logger.info(
                    "Fold %d (h=%d): tuning %s with %d trials on %d rows",
                    fold_num,
                    h,
                    model_cls.__name__,
                    self.config.tuning.n_trials,
                    len(X_train),
                )
                model = model_cls.tune_and_fit(
                    X_train,
                    y_train,
                    self.config.tuning,
                    base_params=model_params,
                )
                cached_params = model.get_params()
            elif cached_params is not None:
                model = model_cls(**cached_params)
                if on_train_progress and getattr(model_cls, "supports_tuning", False):
                    model.fit(X_train, y_train, on_progress=on_train_progress)
                else:
                    model.fit(X_train, y_train)
            else:
                model = model_cls(**model_params)
                if on_train_progress and getattr(model_cls, "supports_tuning", False):
                    model.fit(X_train, y_train, on_progress=on_train_progress)
                else:
                    model.fit(X_train, y_train)

            preds = model.predict(X_test)

            # Duan (1995) non-parametric retransformation correction.
            # Compute in-sample residuals and derive the log smearing factor.
            # This shifts predictions toward the QLIKE-optimal point:
            #   corrected = raw_pred + log(mean(exp(residuals)))
            # For QLIKE-trained models (LightGBM), correction ≈ 0.
            # For MSE-trained models (OLS/Ridge/Lasso), correction ≈ σ²/2.
            train_preds = model.predict(X_train)
            train_residuals = y_train.values - train_preds
            # Only use valid (non-NaN) residuals for the correction
            valid_resid = train_residuals[~np.isnan(train_residuals)]
            if len(valid_resid) > 0:
                correction = float(np.log(np.mean(np.exp(np.clip(valid_resid, -10.0, 10.0)))))
            else:
                correction = 0.0
            duan_corrections.append(correction)
            preds = preds + correction

            all_preds.iloc[test_idx] = preds

            if on_fold_complete is not None:
                on_fold_complete(h, fold_num)

        valid_mask = all_preds.notna()
        y_eval = y[valid_mask].values
        p_eval = all_preds[valid_mask].values

        # Conditional (heteroscedastic) Duan correction post-processing
        cond_duan_raw = self.config.conditional_duan
        if cond_duan_raw and cond_duan_raw.get("enabled"):
            from volforecast.pipeline.conditional_duan import (
                ConditionalDuanConfig,
                apply_conditional_duan,
            )

            cond_cfg = ConditionalDuanConfig.from_dict(cond_duan_raw)
            all_preds = apply_conditional_duan(
                all_preds, y, X, fold_splits_stored, cond_cfg,
            )
            valid_mask = all_preds.notna()
            y_eval = y[valid_mask].values
            p_eval = all_preds[valid_mask].values

        metrics = {
            "qlike": qlike(y_eval, p_eval),
            "mse": mse(y_eval, p_eval),
            "r_squared": r_squared(y_eval, p_eval),
        }

        mean_correction = float(np.mean(duan_corrections)) if duan_corrections else 0.0
        if abs(mean_correction) > 0.01:
            logger.info(
                "h=%d: Duan correction mean=%.4f across %d folds",
                h,
                mean_correction,
                len(duan_corrections),
            )

        result = {
            "metrics": metrics,
            "predictions": all_preds[valid_mask],
            "actuals": y[valid_mask],
            "model": model,
            "X_test": X_test if model is not None else None,
            "duan_correction": mean_correction,
        }

        # Attach SHAP feature selection metadata
        if fs_enabled and fold_selection_results:
            from volforecast.pipeline.feature_selection import aggregate_fold_selections

            result["feature_selection"] = aggregate_fold_selections(
                fold_selection_results,
                stability_threshold=fs_config.stability_threshold,
            )
            # Also store on the model object for dashboard access
            if model is not None:
                model._selection_metadata = result["feature_selection"]
                model._selected_features = result["feature_selection"]["stable_features"]

        return result

    def _run_horizon_gpu_parallel(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        cv,
        model_cls,
        h: int,
        model_params: dict[str, Any],
        n_gpus: int,
        *,
        X_for_cv: pd.DataFrame | None = None,
        on_fold_complete: Any | None = None,
    ) -> dict[str, Any]:
        """GPU-parallel fold execution for tabular tree models (XGBoost).

        Dispatches each CV fold to a separate GPU via ProcessPoolExecutor.
        Fold i trains on cuda:{i % n_gpus}. Results are collected and
        assembled identically to the sequential path.
        """
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor

        cv_input = X_for_cv if X_for_cv is not None else X

        # Pre-compute all fold splits
        fold_splits = list(cv.split(cv_input))
        n_folds = len(fold_splits)
        effective_gpus = min(n_gpus, n_folds)

        logger.info(
            "h=%d: GPU parallel tabular dispatch — %d folds across %d GPUs (%s)",
            h, n_folds, effective_gpus, model_cls.name,
        )

        # Build fold data upfront (serialized to workers via pickle)
        fold_tasks = []
        for fold_num_0, (train_idx, test_idx) in enumerate(fold_splits):
            fold_tasks.append({
                "fold_num": fold_num_0 + 1,
                "X_train": X.iloc[train_idx],
                "y_train": y.iloc[train_idx],
                "X_test": X.iloc[test_idx],
                "test_idx": test_idx,
                "device_id": fold_num_0 % effective_gpus,
            })

        ctx = mp.get_context("spawn")
        all_preds = pd.Series(dtype=float, index=y.index)
        duan_corrections: list[float] = []

        with ProcessPoolExecutor(max_workers=effective_gpus, mp_context=ctx) as executor:
            futures = {}
            for task in fold_tasks:
                future = executor.submit(
                    _execute_tabular_fold,
                    fold_num=task["fold_num"],
                    X_train=task["X_train"],
                    y_train=task["y_train"],
                    X_test=task["X_test"],
                    model_cls_name=model_cls.name,
                    model_params=model_params,
                    device_id=task["device_id"],
                )
                futures[future] = task

            for future in futures:
                result = future.result()
                task = futures[future]
                test_idx = task["test_idx"]
                all_preds.iloc[test_idx] = result["preds"]
                duan_corrections.append(result["duan_correction"])

                if on_fold_complete is not None:
                    on_fold_complete(h, result["fold_num"])

        valid_mask = all_preds.notna()
        y_eval = y[valid_mask].values
        p_eval = all_preds[valid_mask].values

        # Conditional (heteroscedastic) Duan correction post-processing
        cond_duan_raw = self.config.conditional_duan
        if cond_duan_raw and cond_duan_raw.get("enabled"):
            from volforecast.pipeline.conditional_duan import (
                ConditionalDuanConfig,
                apply_conditional_duan,
            )

            cond_cfg = ConditionalDuanConfig.from_dict(cond_duan_raw)
            all_preds = apply_conditional_duan(
                all_preds, y, X, fold_splits, cond_cfg,
            )
            valid_mask = all_preds.notna()
            y_eval = y[valid_mask].values
            p_eval = all_preds[valid_mask].values

        metrics = {
            "qlike": qlike(y_eval, p_eval),
            "mse": mse(y_eval, p_eval),
            "r_squared": r_squared(y_eval, p_eval),
        }

        mean_correction = float(np.mean(duan_corrections)) if duan_corrections else 0.0
        if abs(mean_correction) > 0.01:
            logger.info(
                "h=%d: GPU parallel Duan correction mean=%.4f across %d folds",
                h, mean_correction, len(duan_corrections),
            )

        return {
            "metrics": metrics,
            "predictions": all_preds[valid_mask],
            "actuals": y[valid_mask],
            "model": None,  # No single model in parallel mode
            "X_test": None,
            "duan_correction": mean_correction,
        }

    def run(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict[str, pd.DataFrame] | None = None,
        on_fold_complete: Any | None = None,
        on_horizon_start: Any | None = None,
    ) -> dict[int, Any]:
        """Execute the experiment across all configured horizons.

        Parameters
        ----------
        daily_data : pd.DataFrame
            Daily DataFrame with at minimum 'rv' column. May also contain
            rq, bpv, rs_positive, rs_negative, rk, noise_gap, etc.
            Index must be a DatetimeIndex or date-based index.
        on_fold_complete : callable, optional
            Called as on_fold_complete(horizon, fold_number) after each CV fold.
        on_horizon_start : callable, optional
            Called as on_horizon_start(horizon) at the start of each horizon.

        Returns
        -------
        dict
            Keys are horizon integers. Each value is a dict with:
            - "metrics": dict of {qlike, mse, r_squared}
            - "predictions": pd.Series of OOS predictions
            - "model": the fitted model instance
        """
        if "rv" not in daily_data.columns:
            raise ValueError("daily_data must have an 'rv' column")
        if (daily_data["rv"] <= 0).any():
            raise ValueError(
                "Target RV contains non-positive values. "
                "Pipeline expects raw RV; log transform is applied internally."
            )

        # Build feature matrix by composing registered feature layers.
        # Each layer's output is merged into enriched_data so downstream
        # layers can reference upstream columns (e.g. OptionsLayer reads
        # iv_1m_atm which IVSurfaceLayer produced).
        feature_frames = []
        enriched_data = daily_data
        for layer_name in self.config.feature_layers:
            if layer_name not in FEATURE_REGISTRY:
                raise ValueError(
                    f"Unknown feature layer: {layer_name!r}. "
                    f"Available: {list(FEATURE_REGISTRY.keys())}"
                )
            layer_cls = FEATURE_REGISTRY[layer_name]
            layer = layer_cls()
            # Expansion layers need prior layer outputs as base_features
            if getattr(layer, "_needs_base_features", False):
                base_df = pd.concat(feature_frames, axis=1) if feature_frames else None
                output = layer.compute(enriched_data, context=context, base_features=base_df)
            else:
                output = layer.compute(enriched_data, context=context)
            # Merge output into enriched_data for downstream layers
            if not output.empty:
                enriched_data = pd.concat([enriched_data, output], axis=1)
            # Only include in feature matrix if not enrichment-only
            if not getattr(layer, "_enrichment_only", False):
                feature_frames.append(output)

        X_all = pd.concat(feature_frames, axis=1)

        model_name = self.config.model.name
        if model_name not in MODEL_REGISTRY:
            raise ValueError(
                f"Unknown model: {model_name!r}. Available: {list(MODEL_REGISTRY.keys())}"
            )
        model_cls = MODEL_REGISTRY[model_name]

        results: dict[int, Any] = {}

        def _process_horizon(h: int) -> tuple[int, dict | None]:
            """Prepare data and run one horizon (thread-safe: read-only on X_all)."""
            if on_horizon_start is not None:
                on_horizon_start(h)

            # Enforce purge_gap >= forecast horizon to prevent label leakage
            cv_cfg = self.config.cv_for_horizon(h)
            effective_purge = max(cv_cfg.purge_gap, h)
            if effective_purge > cv_cfg.purge_gap:
                logger.warning(
                    "Purge gap increased from %d to %d for horizon h=%d",
                    cv_cfg.purge_gap,
                    effective_purge,
                    h,
                )
            override = effective_purge if effective_purge > cv_cfg.purge_gap else None
            h_cv = _build_cv_splitter(cv_cfg, purge_gap_override=override)

            # Target: log(average RV over next h days) — Corsi (2009) spec
            log_target = forward_log_rv(daily_data["rv"], h)

            aligned = pd.concat([X_all, log_target.rename("target")], axis=1)
            aligned = aligned.replace([np.inf, -np.inf], np.nan)
            # Drop columns that are entirely NaN (e.g. noise_robust with no tick data)
            aligned = aligned.dropna(axis=1, how="all")
            aligned = aligned.dropna()
            X = aligned.drop(columns=["target"])
            y = aligned["target"]

            n_before = len(X_all)
            n_after = len(X)
            if n_before != n_after:
                logger.info(
                    "h=%d: %d rows -> %d after dropna (%.0f%% dropped)",
                    h,
                    n_before,
                    n_after,
                    100 * (n_before - n_after) / n_before,
                )
            if cv_cfg.train_size and cv_cfg.test_size:
                min_required = cv_cfg.train_size + cv_cfg.test_size
                if n_after < min_required:
                    logger.warning(
                        "h=%d: only %d clean rows, need %d for CV. Skipping.",
                        h,
                        n_after,
                        min_required,
                    )
                    return h, None

            return h, self._run_horizon(X, y, h_cv, model_cls, h, on_fold_complete)

        n_horizons = len(self.config.horizons)
        if n_horizons > 1:
            max_workers = min(n_horizons, os.cpu_count() or 1)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(_process_horizon, h): h for h in self.config.horizons}
                for future in futures:
                    h, res = future.result()
                    if res is not None:
                        results[h] = res
        else:
            for h in self.config.horizons:
                _, res = _process_horizon(h)
                if res is not None:
                    results[h] = res

        return results

    def run_pooled(
        self,
        panel_data: dict[str, pd.DataFrame],
        *,
        context: dict[str, pd.DataFrame] | None = None,
        on_fold_complete: Any | None = None,
        on_horizon_start: Any | None = None,
        on_train_progress: Any | None = None,
        on_batch_progress: Any | None = None,
        on_tuning_hpo: Any | None = None,
    ) -> dict[int, Any]:
        """Execute pooled (multi-symbol) experiment across all horizons.

        Stacks all symbols' features and targets into one panel, then
        fits a single model per CV fold on the combined data. CV splits
        are date-based (all symbols for a given date in the same fold).

        Parameters
        ----------
        panel_data : dict[str, pd.DataFrame]
            Mapping from symbol name to daily DataFrame. Each must have
            at minimum an 'rv' column with DatetimeIndex.
        context, on_fold_complete, on_horizon_start : optional
            Same semantics as run().

        Returns
        -------
        dict
            Keys are horizon integers. Each value is a dict with:
            - "metrics": dict of {qlike, mse, r_squared}
            - "predictions": pd.Series with MultiIndex (date, symbol)
            - "actuals": pd.Series with MultiIndex (date, symbol)
            - "model": the fitted model instance (last fold)
        """
        for sym, df in panel_data.items():
            if "rv" not in df.columns:
                raise ValueError(f"{sym}: daily_data must have an 'rv' column")
            if (df["rv"] <= 0).any():
                raise ValueError(
                    f"{sym}: Target RV contains non-positive values. "
                    "Pipeline expects raw RV; log transform is applied internally."
                )

        # Build features and targets per symbol, then stack
        model_name = self.config.model.name
        if model_name not in MODEL_REGISTRY:
            raise ValueError(
                f"Unknown model: {model_name!r}. Available: {list(MODEL_REGISTRY.keys())}"
            )
        model_cls = MODEL_REGISTRY[model_name]

        # Blend dispatch — prediction-level blending of multiple sub-models.
        # Must come before the sequence dispatch since blend model itself is
        # not a sequence model but may contain sequence sub-models.
        if self.config.blend is not None:
            return self._run_pooled_blend(
                panel_data,
                on_fold_complete=on_fold_complete,
                on_horizon_start=on_horizon_start,
                on_train_progress=on_train_progress,
            )

        # Sequence-first models (LSTM/TCN) take a SequenceTensor, not a
        # DataFrame. Dispatch once here so the tabular path below stays
        # completely unchanged.
        if getattr(model_cls, "requires_sequences", False):
            return self._run_pooled_sequences(
                panel_data,
                model_cls,
                on_fold_complete=on_fold_complete,
                on_horizon_start=on_horizon_start,
                on_train_progress=on_train_progress,
                on_batch_progress=on_batch_progress,
                on_tuning_hpo=on_tuning_hpo,
            )

        # Feature stacking: load LSTM sequence tensors once (reused across horizons)
        _fs_sym_seqs: dict[str, Any] = {}
        _fs_is_graph_model = False
        if self.config.feature_stack is not None:
            # Check if source model is graph-based (doesn't need sequences)
            from volforecast.registry import MODEL_REGISTRY as _MR
            _fs_source = self.config.feature_stack.source_model
            _fs_source_cls = _MR.get(_fs_source)
            _fs_is_graph_model = getattr(_fs_source_cls, "requires_graph", False)

            if not _fs_is_graph_model:
                _fs_sym_seqs = self._load_feature_stack_sequences(panel_data)
                if _fs_sym_seqs:
                    logger.info(
                        "Feature stacking: loaded sequences for %d/%d symbols",
                        len(_fs_sym_seqs),
                        len(panel_data),
                    )
            else:
                logger.info("Feature stacking: graph-mode model (%s), no sequences needed", _fs_source)

        results: dict[int, Any] = {}

        def _build_and_run_horizon(h: int) -> tuple[int, dict[str, Any]]:
            """Build panel and run one horizon."""
            if on_horizon_start is not None:
                on_horizon_start(h)

            symbol_frames = []
            logger.info("h=%d: building features for %d symbols...", h, len(panel_data))
            for sym, daily_data in panel_data.items():
                # Inject symbol into context for per-symbol layers (e.g. IVSurfaceLayer)
                sym_context = dict(context) if context else {}
                sym_context["symbol"] = sym
                feature_frames = []
                enriched_data = daily_data
                for layer_name in self.config.feature_layers:
                    if layer_name not in FEATURE_REGISTRY:
                        raise ValueError(
                            f"Unknown feature layer: {layer_name!r}. "
                            f"Available: {list(FEATURE_REGISTRY.keys())}"
                        )
                    layer_cls = FEATURE_REGISTRY[layer_name]
                    layer = layer_cls()
                    if getattr(layer, "_needs_base_features", False):
                        base_df = pd.concat(feature_frames, axis=1) if feature_frames else None
                        output = layer.compute(
                            enriched_data, context=sym_context, base_features=base_df
                        )
                    else:
                        output = layer.compute(enriched_data, context=sym_context)
                    # Merge output for downstream layers
                    if not output.empty:
                        enriched_data = pd.concat([enriched_data, output], axis=1)
                    # Only include in feature matrix if not enrichment-only
                    if not getattr(layer, "_enrichment_only", False):
                        feature_frames.append(output)

                X_sym = pd.concat(feature_frames, axis=1)

                # Build target for this symbol (no cross-symbol contamination)
                log_target = forward_log_rv(daily_data["rv"], h)

                # Align features and target; only require non-NaN target.
                # Feature NaN is preserved for tree models that handle it
                # natively (e.g. LightGBM). OLS models do their own dropna.
                aligned = pd.concat([X_sym, log_target.rename("target")], axis=1)
                aligned = aligned.replace([np.inf, -np.inf], np.nan)
                # Drop rows where target is NaN or ALL features are NaN
                feature_cols = [c for c in aligned.columns if c != "target"]
                mask = aligned["target"].notna() & ~aligned[feature_cols].isna().all(axis=1)
                aligned = aligned.loc[mask]
                X_clean = aligned[feature_cols]
                y_clean = aligned["target"]

                n_before = len(X_sym)
                n_after = len(X_clean)
                if n_before != n_after:
                    logger.info(
                        "%s h=%d: %d rows -> %d after dropna (%.0f%% dropped)",
                        sym,
                        h,
                        n_before,
                        n_after,
                        100 * (n_before - n_after) / n_before,
                    )
                if n_after == 0:
                    logger.warning("%s h=%d: no clean rows, skipping symbol", sym, h)
                    continue

                # Add symbol identifier to the index
                mi = pd.MultiIndex.from_arrays(
                    [X_clean.index, [sym] * len(X_clean)],
                    names=["date", "symbol"],
                )
                X_clean.index = mi
                y_clean.index = mi
                symbol_frames.append((X_clean, y_clean))

            # Column strategy: union (fill missing with NaN for tree models)
            # vs intersection (drop columns not in all symbols for OLS safety).
            # Tree-based models (LightGBM) handle NaN natively; OLS models
            # select their own feature subset and dropna internally.
            all_cols: set[str] = set()
            for sf in symbol_frames:
                all_cols |= set(sf[0].columns)
            common_cols: set[str] = set(symbol_frames[0][0].columns)
            for sf in symbol_frames[1:]:
                common_cols &= set(sf[0].columns)
            extra_cols = sorted(all_cols - common_cols)
            if extra_cols:
                logger.info(
                    "Pooled h=%d: %d features not in all symbols (NaN-filled): %s",
                    h,
                    len(extra_cols),
                    extra_cols,
                )
            union_cols_sorted = sorted(all_cols)

            # Stack all symbols using union columns; missing cols become NaN
            X_panel = pd.concat([sf[0].reindex(columns=union_cols_sorted) for sf in symbol_frames])
            y_panel = pd.concat([sf[1] for sf in symbol_frames])

            # Sort by date (primary) for proper time-based CV
            X_panel = X_panel.sort_index(level="date", kind="mergesort")
            y_panel = y_panel.loc[X_panel.index]

            # Build panel CV splitter (date-based expanding window)
            cv_cfg = self.config.cv_for_horizon(h)
            effective_purge = max(cv_cfg.purge_gap, h)
            if effective_purge > cv_cfg.purge_gap:
                logger.debug(
                    "Purge gap increased from %d to %d for horizon h=%d",
                    cv_cfg.purge_gap,
                    effective_purge,
                    h,
                )

            # Use date-level index for CV splitting
            date_index = X_panel.index.get_level_values("date")
            X_for_cv = X_panel.set_index(date_index)

            cv_cfg = self.config.cv_for_horizon(h)
            panel_cv = PanelExpandingWindowCV(
                min_train_dates=cv_cfg.train_size or 252,
                test_dates=cv_cfg.test_size or 63,
                step_dates=cv_cfg.test_size or 63,
                purge_gap=effective_purge,
                embargo=getattr(cv_cfg, "embargo", 0),
            )

            # Build feature-stack callback if configured
            fs_fn = None
            if _fs_sym_seqs or _fs_is_graph_model:
                fs_fn = self._make_feature_stack_fn(
                    X_panel, y_panel, _fs_sym_seqs, h,
                    on_train_progress=on_train_progress,
                    on_fold_complete=on_fold_complete,
                    cv=panel_cv,
                    X_for_cv=X_for_cv,
                )

            return h, self._run_horizon(
                X_panel,
                y_panel,
                panel_cv,
                model_cls,
                h,
                on_fold_complete,
                X_for_cv=X_for_cv,
                on_train_progress=on_train_progress,
                feature_stack_fn=fs_fn,
            )

        # Parallel horizon execution when multi-process tuning is active.
        # With n_workers processes per horizon and 8 threads each, we can run
        # all 3 horizons concurrently: 3 × n_workers × 8 threads ≤ CPU cores.
        n_workers = self.config.tuning.n_workers if self.config.tuning.enabled else 1
        n_horizons = len(self.config.horizons)

        if n_workers > 1 and n_horizons > 1:
            # Parallel: each horizon in a separate process

            # Check if callbacks are set — they're not picklable across processes
            # Fall back to sequential if callbacks are present
            if on_fold_complete or on_train_progress:
                logger.info(
                    "Running %d horizons sequentially (progress callbacks active)",
                    n_horizons,
                )
                for h in self.config.horizons:
                    _, res = _build_and_run_horizon(h)
                    results[h] = res
            else:
                logger.info(
                    "Running %d horizons in parallel (n_workers=%d per horizon)",
                    n_horizons,
                    n_workers,
                )
                from concurrent.futures import ThreadPoolExecutor

                # Use threads here (not processes) since _build_and_run_horizon
                # already spawns worker processes for tuning internally.
                # ThreadPool avoids double-pickling the large DataFrames.
                with ThreadPoolExecutor(max_workers=n_horizons) as executor:
                    future_map = {
                        executor.submit(_build_and_run_horizon, h): h for h in self.config.horizons
                    }
                    for future in future_map:
                        h_result, res = future.result()
                        results[h_result] = res
        else:
            for h in self.config.horizons:
                _, res = _build_and_run_horizon(h)
                results[h] = res

        return results

    # ------------------------------------------------------------------
    # Prediction blending (independent sub-models → weighted average)
    # ------------------------------------------------------------------

    def _run_pooled_blend(
        self,
        panel_data: dict[str, pd.DataFrame],
        *,
        on_fold_complete: Any | None = None,
        on_horizon_start: Any | None = None,
        on_train_progress: Any | None = None,
    ) -> dict[int, Any]:
        """Execute prediction blending across all horizons.

        Builds features from the union of all sub-model feature layers,
        then dispatches to _run_horizon with PredictionBlendModel which
        handles sub-model training and weight calibration internally.
        """
        from volforecast.models.blend import PredictionBlendModel

        blend_config = self.config.blend

        # Determine union of feature layers across all sub-models
        all_layers: list[str] = []
        seen: set[str] = set()
        for sub_cfg in blend_config.models:
            for layer in sub_cfg.feature_layers:
                if layer not in seen:
                    all_layers.append(layer)
                    seen.add(layer)
        # Also include top-level feature_layers from the experiment config
        for layer in self.config.feature_layers:
            if layer not in seen:
                all_layers.append(layer)
                seen.add(layer)

        results: dict[int, Any] = {}

        for h in self.config.horizons:
            if on_horizon_start is not None:
                on_horizon_start(h)

            # Build panel with union of all feature layers
            symbol_frames = []
            context: dict[str, Any] = {}
            for sym, daily_data in panel_data.items():
                sym_context = {"symbol": sym}
                feature_frames = []
                enriched_data = daily_data
                for layer_name in all_layers:
                    if layer_name not in FEATURE_REGISTRY:
                        raise ValueError(
                            f"Unknown feature layer: {layer_name!r}. "
                            f"Available: {list(FEATURE_REGISTRY.keys())}"
                        )
                    layer_cls = FEATURE_REGISTRY[layer_name]
                    layer = layer_cls()
                    if getattr(layer, "_needs_base_features", False):
                        base_df = (
                            pd.concat(feature_frames, axis=1)
                            if feature_frames
                            else None
                        )
                        output = layer.compute(
                            enriched_data, context=sym_context, base_features=base_df
                        )
                    else:
                        output = layer.compute(enriched_data, context=sym_context)
                    if not output.empty:
                        enriched_data = pd.concat([enriched_data, output], axis=1)
                    if not getattr(layer, "_enrichment_only", False):
                        feature_frames.append(output)

                X_sym = pd.concat(feature_frames, axis=1)
                log_target = forward_log_rv(daily_data["rv"], h)

                aligned = pd.concat([X_sym, log_target.rename("target")], axis=1)
                aligned = aligned.replace([np.inf, -np.inf], np.nan)
                feature_cols = [c for c in aligned.columns if c != "target"]
                mask = aligned["target"].notna() & ~aligned[feature_cols].isna().all(
                    axis=1
                )
                aligned = aligned.loc[mask]
                X_clean = aligned[feature_cols]
                y_clean = aligned["target"]

                if len(X_clean) == 0:
                    logger.warning("%s h=%d: no clean rows, skipping", sym, h)
                    continue

                mi = pd.MultiIndex.from_arrays(
                    [X_clean.index, [sym] * len(X_clean)],
                    names=["date", "symbol"],
                )
                X_clean.index = mi
                y_clean.index = mi
                symbol_frames.append((X_clean, y_clean))

            if not symbol_frames:
                raise ValueError(f"h={h}: no symbols produced valid data")

            # Stack all symbols using union columns
            all_cols_sorted = sorted(
                set().union(*(set(sf[0].columns) for sf in symbol_frames))
            )
            X_panel = pd.concat(
                [sf[0].reindex(columns=all_cols_sorted) for sf in symbol_frames]
            )
            y_panel = pd.concat([sf[1] for sf in symbol_frames])
            X_panel = X_panel.sort_index(level="date", kind="mergesort")
            y_panel = y_panel.loc[X_panel.index]

            # Build CV splitter
            cv_cfg = self.config.cv_for_horizon(h)
            effective_purge = max(cv_cfg.purge_gap, h)
            date_index = X_panel.index.get_level_values("date")
            X_for_cv = X_panel.set_index(date_index)

            panel_cv = PanelExpandingWindowCV(
                min_train_dates=cv_cfg.train_size or 252,
                test_dates=cv_cfg.test_size or 63,
                step_dates=cv_cfg.test_size or 63,
                purge_gap=effective_purge,
                embargo=getattr(cv_cfg, "embargo", 0),
            )

            # Use PredictionBlendModel as a standard tabular model in _run_horizon.
            # It resolves sub-models from registry and handles weight calibration
            # internally during fit(). blend_config is injected via
            # ExperimentConfig.model_params_for_horizon().
            results[h] = self._run_horizon(
                X_panel,
                y_panel,
                panel_cv,
                PredictionBlendModel,
                h,
                on_fold_complete,
                X_for_cv=X_for_cv,
                on_train_progress=on_train_progress,
            )

        return results

    # ------------------------------------------------------------------
    # Feature stacking (LSTM → features → tabular model)
    # ------------------------------------------------------------------

    def _load_feature_stack_sequences(
        self,
        panel_data: dict[str, pd.DataFrame],
    ) -> dict[str, Any]:
        """Load per-symbol SequenceTensors for feature stacking.

        Resolves the feature_stack.sequences config (or falls back to
        top-level sequences config) and loads cached tensors from disk.
        Supports both "parquet" (intraday) and "daily_lookback" sources.
        """
        from volforecast.config import SequenceConfig
        from volforecast.data.sequence_cache import (
            SequenceSpec,
            build_daily_lookback_tensor,
            load_sequence_tensor,
        )

        fs_cfg = self.config.feature_stack
        if fs_cfg is None:
            return {}

        # Resolve sequence config: feature_stack.sequences overrides top-level
        seq_raw = fs_cfg.sequences
        if seq_raw is None:
            seq_raw = self.config.sequences
        if seq_raw is None:
            seq_raw = SequenceConfig()
        if isinstance(seq_raw, dict):
            seq_raw = SequenceConfig(**seq_raw)

        source = seq_raw.source
        features = tuple(seq_raw.features)
        max_bars = seq_raw.max_bars
        bar_interval = getattr(seq_raw, "bar_interval", 10)

        sym_seqs: dict[str, Any] = {}

        if source == "daily_lookback":
            # Build lookback tensors from enriched daily panel (same as _run_pooled_sequences)
            for sym, daily_data in panel_data.items():
                enriched = daily_data
                for layer_name in self.config.feature_layers:
                    if layer_name in FEATURE_REGISTRY:
                        layer = FEATURE_REGISTRY[layer_name]()
                        output = layer.compute(enriched, context={"symbol": sym})
                        if not output.empty:
                            enriched = pd.concat([enriched, output], axis=1)
                missing_cols = [f for f in features if f not in enriched.columns]
                if missing_cols:
                    logger.warning(
                        "%s: daily_lookback missing columns %s; skipping", sym, missing_cols
                    )
                    continue
                seq = build_daily_lookback_tensor(sym, enriched, features, max_bars)
                if len(seq) > 0:
                    sym_seqs[sym] = seq
                else:
                    logger.warning("%s: daily_lookback produced empty tensor; skipping", sym)
        else:
            # Default parquet path (intraday sequences)
            spec = SequenceSpec(features=features, max_bars=max_bars, bar_interval=bar_interval)
            sequences_dir = Path(seq_raw.sequences_dir) if seq_raw.sequences_dir else None
            cache_dir = Path(seq_raw.cache_dir) if seq_raw.cache_dir else None
            for sym in panel_data:
                try:
                    sym_seqs[sym] = load_sequence_tensor(
                        sym, spec, sequences_dir=sequences_dir, cache_dir=cache_dir
                    )
                except FileNotFoundError:
                    logger.warning("%s: no sequence cache for feature stacking; skipping", sym)

        return sym_seqs

    def _make_feature_stack_fn(
        self,
        X_panel: pd.DataFrame,
        y_panel: pd.Series,
        sym_seqs: dict[str, Any],
        h: int,
        *,
        on_train_progress: Any | None = None,
        on_fold_complete: Any | None = None,
        cv: Any | None = None,
        X_for_cv: pd.DataFrame | None = None,
    ):
        """Build a per-fold feature-stack callback for _run_horizon.

        Returns a callable ``fn(train_idx, test_idx, h)`` that:
        1. Cross-fits K inner-fold LSTMs to produce OOF predictions on train rows
        2. Trains a final LSTM on the full train block for test-row predictions
        3. Returns a DataFrame aligned to X_panel.index

        This prevents the classic stacking leakage where in-sample LSTM
        predictions are fed to the downstream model's training set.

        Supports fold caching: if ``fold_cache_enabled`` is True, the
        extracted features are persisted per fold and reused on subsequent runs.
        """
        import hashlib
        import json

        import torch as _torch

        from volforecast.config import FeatureStackConfig

        fs_cfg = self.config.feature_stack_for_horizon(h)
        if fs_cfg is None:
            return None

        # Resolve source model class
        source_model_name = fs_cfg.source_model
        if source_model_name not in MODEL_REGISTRY:
            raise ValueError(
                f"feature_stack.source_model={source_model_name!r} not in registry"
            )
        source_model_cls = MODEL_REGISTRY[source_model_name]

        # Dispatch: graph-mode models use a different feature_stack path
        if getattr(source_model_cls, "requires_graph", False):
            return self._make_gnn_feature_stack_fn(
                X_panel, y_panel, sym_seqs, h, fs_cfg,
                on_train_progress=on_train_progress,
                on_fold_complete=on_fold_complete,
                cv=cv,
                X_for_cv=X_for_cv,
            )

        # Sequence-based models require loaded sequence tensors
        if not sym_seqs:
            return None

        # Get sequence feature count from first available tensor
        first_seq = next(iter(sym_seqs.values()))
        n_features = first_seq.n_features

        # Build pooled sequence tensor aligned to X_panel index
        # X_panel has MultiIndex (date, symbol)
        all_dates = X_panel.index.get_level_values("date")
        all_symbols = X_panel.index.get_level_values("symbol")

        # Build row-level sequence arrays aligned to X_panel
        max_bars = first_seq.max_bars
        n_rows = len(X_panel)

        # Pre-build lookup: for each (date, symbol) in X_panel, find the
        # corresponding row in the symbol's SequenceTensor.
        # This is done once, then sliced per fold.
        seq_tensor_full = _torch.zeros(n_rows, max_bars, n_features, dtype=_torch.float32)
        seq_lengths_full = _torch.zeros(n_rows, dtype=_torch.int64)
        valid_mask = np.zeros(n_rows, dtype=bool)

        for sym, seq in sym_seqs.items():
            # Rows in X_panel for this symbol
            sym_mask = all_symbols == sym
            sym_indices = np.where(sym_mask)[0]
            sym_dates_panel = all_dates[sym_mask]

            # Map panel dates to sequence tensor row indices.
            # Normalize seq.dates (pd.Timestamp) to match panel date type
            # (may be datetime.date when loaded from parquet with date32 dtype).
            seq_date_to_idx: dict = {}
            for i, d in enumerate(seq.dates):
                seq_date_to_idx[d] = i
                # Also store as datetime.date for cross-type matching
                if hasattr(d, "date"):
                    seq_date_to_idx[d.date()] = i
            for panel_pos, panel_date in zip(sym_indices, sym_dates_panel):
                seq_idx = seq_date_to_idx.get(panel_date)
                if seq_idx is not None:
                    seq_tensor_full[panel_pos] = seq.tensor[seq_idx]
                    seq_lengths_full[panel_pos] = seq.lengths[seq_idx]
                    valid_mask[panel_pos] = True

        requested_outputs = fs_cfg.outputs
        # Always extract ALL outputs for cache efficiency — different tournament
        # models can share the same LSTM training + extraction cache entry.
        _ALL_OUTPUTS = ["prediction", "attention_entropy", "attention_peak_time", "embedding"]
        model_params = dict(fs_cfg.model_params)
        model_params["input_dim"] = n_features
        embedding_dim = fs_cfg.embedding_dim  # PCA target dim for embedding (None = raw)
        n_inner_folds = fs_cfg.n_inner_folds
        is_independent = fs_cfg.independent

        # Fold caching setup
        cache_enabled = self.config.fold_cache_enabled
        cache_dir: Path | None = None
        if cache_enabled:
            base_cache = Path(self.config.fold_cache_dir or "data/models/lstm_cache")
            cache_dir = base_cache / f"feature_stack_h{h}"
            cache_dir.mkdir(parents=True, exist_ok=True)

        # Stable hash for model config — includes all relevant fields for
        # cache invalidation (Phase 3 fix).
        config_str = json.dumps(
            {
                "cache_version": FEATURE_STACK_CACHE_VERSION,
                "source_model": source_model_name,
                "model_params": model_params,
                "features": list(first_seq.feature_names),
                "embedding_dim": embedding_dim,
                "n_inner_folds": n_inner_folds,
                "independent": is_independent,
            },
            sort_keys=True,
        )
        config_hash = hashlib.sha256(config_str.encode()).hexdigest()[:12]

        def _fold_cache_key(train_idx) -> str:
            """Deterministic cache key from train indices."""
            idx_hash = hashlib.sha256(
                np.array(sorted(train_idx), dtype=np.int64).tobytes()
            ).hexdigest()[:12]
            return f"fs_{config_hash}_{idx_hash}"

        def _filter_to_requested_outputs(df: pd.DataFrame) -> pd.DataFrame:
            """Keep only lstm_* columns matching requested_outputs."""
            keep_prefixes = set()
            for out in requested_outputs:
                if out == "embedding":
                    keep_prefixes.add("lstm_embedding_")
                else:
                    keep_prefixes.add(f"lstm_{out}")
            cols_to_keep = [
                c for c in df.columns
                if any(c == p or c.startswith(p) for p in keep_prefixes)
            ]
            return df[cols_to_keep]

        def _build_seq_tensor(row_indices: np.ndarray) -> SequenceTensor:
            """Build a SequenceTensor from panel row indices."""
            return SequenceTensor(
                symbol="__pooled__",
                tensor=seq_tensor_full[row_indices],
                lengths=seq_lengths_full[row_indices],
                dates=pd.DatetimeIndex(all_dates[row_indices]),
                feature_names=first_seq.feature_names,
            )

        def _normalise_seq(
            seq_t: SequenceTensor, train_dates: pd.DatetimeIndex
        ) -> SequenceTensor:
            """Fit normaliser on train_dates only, apply to full tensor."""
            mean, std = fit_seq_normaliser(seq_t, train_dates)
            return apply_normaliser(seq_t, mean, std)

        def _train_and_extract(
            train_rows: np.ndarray,
            predict_rows: np.ndarray,
            targets: np.ndarray,
            base_preds_train: np.ndarray | None = None,
            base_preds_predict: np.ndarray | None = None,
        ) -> dict[str, np.ndarray]:
            """Train one LSTM on train_rows, extract features on predict_rows.

            Handles normalization (fit on train, apply to both) and base_preds
            for residual stacking (independent=False).
            """
            # Build sequence tensors
            all_involved = np.union1d(train_rows, predict_rows)
            full_seq = _build_seq_tensor(all_involved)

            # Normalise: fit on train dates only
            train_dates = pd.DatetimeIndex(all_dates[train_rows])
            normed_seq = _normalise_seq(full_seq, train_dates)

            # Split normalised tensor back into train and predict parts
            # Map: position in all_involved -> row index
            pos_map = {row: i for i, row in enumerate(all_involved)}
            train_positions = np.array([pos_map[r] for r in train_rows])
            predict_positions = np.array([pos_map[r] for r in predict_rows])

            train_seq = SequenceTensor(
                symbol="__pooled__",
                tensor=normed_seq.tensor[train_positions],
                lengths=normed_seq.lengths[train_positions],
                dates=pd.DatetimeIndex(all_dates[train_rows]),
                feature_names=first_seq.feature_names,
            )
            predict_seq = SequenceTensor(
                symbol="__pooled__",
                tensor=normed_seq.tensor[predict_positions],
                lengths=normed_seq.lengths[predict_positions],
                dates=pd.DatetimeIndex(all_dates[predict_rows]),
                feature_names=first_seq.feature_names,
            )

            # Train
            lstm_model = source_model_cls(**model_params)
            fit_kwargs: dict[str, Any] = {}
            if not is_independent and base_preds_train is not None:
                fit_kwargs["base_preds"] = base_preds_train
            lstm_model.fit(train_seq, targets, **fit_kwargs)

            # Extract on predict rows
            extract_kwargs: dict[str, Any] = {"outputs": _ALL_OUTPUTS}
            if not is_independent and base_preds_predict is not None:
                extract_kwargs["base_preds"] = base_preds_predict
            extracted = lstm_model.extract_features(predict_seq, **extract_kwargs)
            return extracted

        def _feature_stack_fold(train_idx, test_idx, h_inner):
            """OOF cross-fitted LSTM feature extraction.

            1. Split train_idx into K inner folds
            2. For each inner fold: train on K-1, predict on held-out → OOF train predictions
            3. Train final LSTM on full train → predict on test rows
            4. Combine: train rows get OOF, test rows get full-train predictions
            """
            # Check fold cache
            if cache_enabled and cache_dir is not None:
                cache_key = _fold_cache_key(train_idx)
                cache_path = cache_dir / f"{cache_key}.parquet"
                if cache_path.exists():
                    try:
                        cached_df = pd.read_parquet(cache_path)
                        if len(cached_df) == n_rows:
                            cached_df.index = X_panel.index
                            logger.debug("Feature stack fold cache hit: %s", cache_key)
                            return _filter_to_requested_outputs(cached_df)
                        else:
                            logger.warning(
                                "Feature stack cache %s has %d rows (expected %d); recomputing",
                                cache_key, len(cached_df), n_rows,
                            )
                    except Exception:
                        logger.warning("Feature stack cache %s unreadable; recomputing", cache_key)

            # Only use rows that have valid sequence data
            train_valid = np.array([i for i in train_idx if valid_mask[i]])
            test_valid = np.array([i for i in test_idx if valid_mask[i]])
            if len(train_valid) < 10:
                logger.warning("Feature stack: <10 valid train sequences, skipping fold")
                return None

            train_targets = y_panel.iloc[train_valid].values.astype(np.float32)

            # --- Phase 1: OOF cross-fitting on train rows ---
            # Split train_valid into K time-ordered inner folds
            inner_fold_indices = np.array_split(
                np.arange(len(train_valid)), n_inner_folds
            )

            # Accumulate OOF predictions for each output
            oof_results: dict[str, np.ndarray] = {}
            for out in _ALL_OUTPUTS:
                if out == "embedding":
                    # Will be filled after we know the dimension
                    pass
                else:
                    oof_results[out] = np.full(len(train_valid), np.nan, dtype=np.float32)
            oof_embedding: np.ndarray | None = None

            for k, inner_test_positions in enumerate(inner_fold_indices):
                if len(inner_test_positions) == 0:
                    continue
                inner_train_positions = np.concatenate(
                    [inner_fold_indices[j] for j in range(n_inner_folds) if j != k]
                )

                inner_train_rows = train_valid[inner_train_positions]
                inner_predict_rows = train_valid[inner_test_positions]
                inner_train_targets = train_targets[inner_train_positions]

                # Base preds for inner fold (only when independent=False)
                inner_base_train = None
                inner_base_predict = None
                if not is_independent:
                    # Use y_panel values as a simple proxy for base predictions
                    # In the full implementation, this would re-fit the tabular base model
                    # For now, use the mean of inner train targets as a constant base
                    mean_base = float(np.nanmean(inner_train_targets))
                    inner_base_train = np.full(len(inner_train_rows), mean_base, dtype=np.float32)
                    inner_base_predict = np.full(len(inner_predict_rows), mean_base, dtype=np.float32)

                extracted = _train_and_extract(
                    inner_train_rows,
                    inner_predict_rows,
                    inner_train_targets,
                    base_preds_train=inner_base_train,
                    base_preds_predict=inner_base_predict,
                )

                # Fill OOF positions
                for key, arr in extracted.items():
                    if arr.ndim == 1:
                        oof_results[key][inner_test_positions] = arr
                    else:
                        # Embedding: initialize on first encounter
                        if oof_embedding is None:
                            oof_embedding = np.full(
                                (len(train_valid), arr.shape[1]),
                                np.nan,
                                dtype=np.float32,
                            )
                        oof_embedding[inner_test_positions] = arr

            # --- Final LSTM on full train → predict on test rows ---
            final_base_train = None
            final_base_test = None
            if not is_independent:
                mean_base = float(np.nanmean(train_targets))
                final_base_train = np.full(len(train_valid), mean_base, dtype=np.float32)
                final_base_test = np.full(len(test_valid), mean_base, dtype=np.float32) if len(test_valid) > 0 else None

            if len(test_valid) > 0:
                test_extracted = _train_and_extract(
                    train_valid,
                    test_valid,
                    train_targets,
                    base_preds_train=final_base_train,
                    base_preds_predict=final_base_test,
                )
            else:
                test_extracted = {}

            # --- Assemble result DataFrame ---
            result_cols: dict[str, np.ndarray] = {}
            train_set = set(train_valid)
            test_set = set(test_valid)

            for key in _ALL_OUTPUTS:
                if key == "embedding":
                    continue
                col_name = f"lstm_{key}"
                full_col = np.full(n_rows, np.nan, dtype=np.float32)
                # Train rows: OOF predictions
                if key in oof_results:
                    full_col[train_valid] = oof_results[key]
                # Test rows: full-train predictions
                if key in test_extracted and test_extracted[key].ndim == 1:
                    full_col[test_valid] = test_extracted[key]
                result_cols[col_name] = full_col

            # Handle embedding with PCA
            if oof_embedding is not None or ("embedding" in test_extracted and test_extracted.get("embedding") is not None):
                test_emb = test_extracted.get("embedding")
                raw_dim = (
                    oof_embedding.shape[1] if oof_embedding is not None
                    else test_emb.shape[1] if test_emb is not None
                    else 0
                )
                if raw_dim > 0:
                    if embedding_dim is not None and raw_dim > embedding_dim:
                        from sklearn.decomposition import PCA
                        pca = PCA(n_components=embedding_dim, random_state=42)
                        # Fit PCA on train OOF embeddings only
                        if oof_embedding is not None:
                            # Use non-NaN rows for PCA fit
                            valid_oof_mask = ~np.isnan(oof_embedding[:, 0])
                            pca.fit(oof_embedding[valid_oof_mask])
                            oof_embedding = pca.transform(oof_embedding).astype(np.float32)
                        if test_emb is not None:
                            test_emb = pca.transform(test_emb).astype(np.float32)
                        actual_dim = embedding_dim
                    else:
                        actual_dim = raw_dim

                    for dim_i in range(actual_dim):
                        col_name = f"lstm_embedding_{dim_i}"
                        full_col = np.full(n_rows, np.nan, dtype=np.float32)
                        if oof_embedding is not None:
                            full_col[train_valid] = oof_embedding[:, dim_i]
                        if test_emb is not None:
                            full_col[test_valid] = test_emb[:, dim_i]
                        result_cols[col_name] = full_col

            result_df = pd.DataFrame(result_cols, index=X_panel.index)

            # Persist full extraction to fold cache
            if cache_enabled and cache_dir is not None:
                cache_key = _fold_cache_key(train_idx)
                cache_path = cache_dir / f"{cache_key}.parquet"
                try:
                    result_df.reset_index(drop=True).to_parquet(cache_path)
                    logger.debug("Feature stack fold cached: %s", cache_key)
                except Exception as exc:
                    logger.warning("Failed to cache feature stack fold: %s", exc)

            return _filter_to_requested_outputs(result_df)

        return _feature_stack_fold

    # ------------------------------------------------------------------
    # GNN graph-mode feature stacking
    # ------------------------------------------------------------------

    def _make_gnn_feature_stack_fn(
        self,
        X_panel: pd.DataFrame,
        y_panel: pd.Series,
        sym_seqs: dict[str, Any],
        h: int,
        fs_cfg: Any,
        *,
        on_train_progress: Any | None = None,
        on_fold_complete: Any | None = None,
        cv: Any | None = None,
        X_for_cv: pd.DataFrame | None = None,
    ):
        """Build per-fold GNN feature-stack callback for graph models.

        Unlike the LSTM path which operates on temporal SequenceTensors,
        the GNN path builds graph snapshots (one per date) where nodes
        are symbols and edges come from rolling realized correlation.

        Returns a callable fn(train_idx, test_idx, h) compatible with
        _run_horizon's feature_stack_fn interface.
        """
        import torch as _torch

        from volforecast.models.gnn_adjacency import build_adjacency, panel_returns_from_ohlcv
        from volforecast.utils.paths import ohlcv_cache_dir

        source_model_name = fs_cfg.source_model
        source_model_cls = MODEL_REGISTRY[source_model_name]
        model_params = dict(fs_cfg.model_params)
        requested_outputs = fs_cfg.outputs

        # Panel metadata
        all_dates = X_panel.index.get_level_values("date")
        all_symbols = X_panel.index.get_level_values("symbol")
        n_rows = len(X_panel)

        # Get unique symbols and their order
        unique_symbols = list(dict.fromkeys(all_symbols))
        symbol_to_idx = {s: i for i, s in enumerate(unique_symbols)}
        n_symbols = len(unique_symbols)

        # Load panel returns for adjacency computation
        panel_returns = panel_returns_from_ohlcv(ohlcv_cache_dir())

        # Keep only columns in our universe
        available = [s for s in unique_symbols if s in panel_returns.columns]
        panel_returns = panel_returns[available]

        # GNN node features: use the same features from sequences config
        # Each node gets its daily feature vector from the X_panel
        seq_cfg = fs_cfg.sequences
        if seq_cfg is not None:
            feature_names = list(seq_cfg.features) if hasattr(seq_cfg, "features") else None
        else:
            feature_names = None

        # Adjacency params
        adj_window = model_params.pop("adj_window", 60)
        adj_threshold = model_params.pop("adj_threshold", 0.3)

        # Determine input_dim from the feature columns we'll use
        # Use the sequence features if specified, else default HAR features
        if feature_names is None:
            feature_names = [
                "log_rv_d", "log_rv_w", "log_rv_m", "signed_return_d",
                "abs_ret_d", "log_rs_negative_d", "log_jump_d", "log_bpv_d", "log_cont_d",
            ]

        # Find which feature columns are available in X_panel
        available_features = [f for f in feature_names if f in X_panel.columns]
        if not available_features:
            logger.warning("GNN feature stack: no sequence features found in X_panel columns")
            return None

        model_params["input_dim"] = len(available_features)

        # Pre-compute ALL graph snapshots once (keyed by date)
        unique_dates = sorted(set(all_dates))
        all_graphs_by_date: dict = {}
        panel_col_list = list(panel_returns.columns)
        for date in unique_dates:
            # Find all rows for this date
            date_mask = all_dates == date
            date_row_indices = np.where(date_mask)[0]
            date_symbols_arr = all_symbols[date_row_indices]

            # Node features
            node_features = X_panel.iloc[date_row_indices][available_features].values
            node_features = np.nan_to_num(node_features, nan=0.0)

            # Adjacency
            sym_in_adj = [s for s in date_symbols_arr if s in panel_returns.columns]
            if len(sym_in_adj) < 2 or date not in panel_returns.index:
                edge_index = _torch.zeros(2, 0, dtype=_torch.long)
                edge_attr = _torch.zeros(0, dtype=_torch.float32)
            else:
                full_edge_index, full_edge_attr = build_adjacency(
                    panel_returns, date, window=adj_window, threshold=adj_threshold
                )
                # Remap edges to local node ordering (vectorized)
                panel_to_local = np.full(len(panel_col_list), -1, dtype=np.int64)
                for local_i, sym in enumerate(date_symbols_arr):
                    if sym in panel_col_list:
                        panel_to_local[panel_col_list.index(sym)] = local_i

                if full_edge_index.shape[1] > 0:
                    src_arr = full_edge_index[0].numpy()
                    dst_arr = full_edge_index[1].numpy()
                    # Vectorized lookup: -1 means node not in our local universe
                    src_local = panel_to_local[src_arr]
                    dst_local = panel_to_local[dst_arr]
                    # Keep only edges where BOTH endpoints are in our universe
                    valid_mask = (src_local >= 0) & (dst_local >= 0)
                    if valid_mask.any():
                        edge_index = _torch.tensor(
                            np.stack([src_local[valid_mask], dst_local[valid_mask]]),
                            dtype=_torch.long,
                        )
                        edge_attr = full_edge_attr[valid_mask]
                    else:
                        edge_index = _torch.zeros(2, 0, dtype=_torch.long)
                        edge_attr = _torch.zeros(0, dtype=_torch.float32)
                else:
                    edge_index = _torch.zeros(2, 0, dtype=_torch.long)
                    edge_attr = _torch.zeros(0, dtype=_torch.float32)

            # Targets
            targets = y_panel.iloc[date_row_indices].values.astype(np.float32)

            all_graphs_by_date[date] = {
                "x": node_features.astype(np.float32),
                "edge_index": edge_index,
                "edge_attr": edge_attr,
                "date": date,
                "_row_indices": date_row_indices,
                "y": targets,
            }

        logger.info("GNN feature stack: pre-built %d graph snapshots", len(all_graphs_by_date))

        # ── Multi-GPU parallel dispatch ──────────────────────────────
        import torch as _torch_gpu_check

        n_gpus = getattr(self.config, "n_gpus", 1)
        available_gpus = _torch_gpu_check.cuda.device_count() if _torch_gpu_check.cuda.is_available() else 0
        effective_gpus = min(n_gpus, available_gpus) if available_gpus > 0 else 0
        use_parallel = effective_gpus > 1 and cv is not None

        if use_parallel:
            import threading

            import torch.multiprocessing as _mp
            from concurrent.futures import ProcessPoolExecutor, as_completed

            cv_input = X_for_cv if X_for_cv is not None else X_panel
            fold_splits = list(cv.split(cv_input))
            n_folds = len(fold_splits)
            effective_gpus = min(effective_gpus, n_folds)

            logger.info(
                "GNN feature stack: parallel dispatch — %d folds across %d GPUs (cuda:0..%d)",
                n_folds, effective_gpus, effective_gpus - 1,
            )

            ctx = _mp.get_context("spawn")
            _manager = _mp.Manager()
            _progress_queue = _manager.Queue()
            _consumer_stop = threading.Event()

            def _consume_epoch_progress():
                while not _consumer_stop.is_set():
                    try:
                        event = _progress_queue.get(timeout=0.5)
                    except Exception:  # noqa: BLE001
                        continue
                    if event is None:
                        break
                    if on_train_progress is not None and event.get("type") == "epoch":
                        on_train_progress(event["epoch"], event["max_epochs"])

            _consumer_thread = threading.Thread(target=_consume_epoch_progress, daemon=True)
            _consumer_thread.start()

            _fold_results_cache: dict[int, pd.DataFrame] = {}

            with ProcessPoolExecutor(max_workers=effective_gpus, mp_context=ctx) as pool:
                futures = {}
                for fold_num_0, (train_idx, test_idx) in enumerate(fold_splits):
                    fold_num = fold_num_0 + 1
                    device_id = fold_num_0 % effective_gpus

                    # Select graphs for this fold
                    train_dates_set = set(all_dates[train_idx])
                    test_dates_set = set(all_dates[test_idx])
                    train_graphs = [
                        all_graphs_by_date[d]
                        for d in sorted(train_dates_set)
                        if d in all_graphs_by_date
                    ]
                    test_graphs = [
                        all_graphs_by_date[d]
                        for d in sorted(test_dates_set)
                        if d in all_graphs_by_date
                    ]

                    if not train_graphs:
                        continue

                    future = pool.submit(
                        _execute_gnn_fold,
                        fold_num=fold_num,
                        train_graph_dicts=train_graphs,
                        test_graph_dicts=test_graphs,
                        model_cls_name=source_model_name,
                        model_params=model_params,
                        device_id=device_id,
                        requested_outputs=requested_outputs,
                        n_rows=n_rows,
                        progress_queue=_progress_queue,
                    )
                    futures[future] = fold_num

                for future in as_completed(futures):
                    result = future.result()
                    fn = result["fold_num"]
                    result_df = pd.DataFrame(result["result_cols"], index=X_panel.index)
                    _fold_results_cache[fn] = result_df
                    if on_fold_complete is not None:
                        on_fold_complete(h, fn)

            # Cleanup progress consumer
            _progress_queue.put(None)
            _consumer_stop.set()
            _consumer_thread.join(timeout=5.0)
            _manager.shutdown()

            logger.info(
                "GNN feature stack: parallel dispatch complete — %d folds cached",
                len(_fold_results_cache),
            )

            # Return a fold callback that looks up pre-computed results
            _fold_counter = [0]

            def _gnn_feature_stack_fold(train_idx, test_idx, h_inner):
                _fold_counter[0] += 1
                return _fold_results_cache.get(_fold_counter[0])

            return _gnn_feature_stack_fold

        # ── Sequential fallback (n_gpus <= 1) ────────────────────────
        def _gnn_feature_stack_fold(train_idx, test_idx, h_inner):
            """GNN feature stacking: select pre-built graphs, train, extract."""
            # Get dates for train/test rows
            train_dates_set = set(all_dates[train_idx])
            test_dates_set = set(all_dates[test_idx])

            train_graphs = [all_graphs_by_date[d] for d in sorted(train_dates_set) if d in all_graphs_by_date]
            test_graphs = [all_graphs_by_date[d] for d in sorted(test_dates_set) if d in all_graphs_by_date]

            if not train_graphs:
                return None

            # Train GNN
            gnn_model = source_model_cls(**model_params)
            gnn_model.fit(train_graphs)

            # Extract features on both train and test
            all_graphs = train_graphs + test_graphs
            extracted = gnn_model.extract_features(all_graphs, outputs=requested_outputs)

            # Build result DataFrame aligned to X_panel
            result_cols: dict[str, np.ndarray] = {}
            for key, arr in extracted.items():
                col_name = f"gnn_{key}"
                full_col = np.full(n_rows, np.nan, dtype=np.float32)

                offset = 0
                for g in all_graphs:
                    n_nodes = g["x"].shape[0]
                    row_indices_g = g["_row_indices"]
                    full_col[row_indices_g] = arr[offset : offset + n_nodes]
                    offset += n_nodes

                result_cols[col_name] = full_col

            result_df = pd.DataFrame(result_cols, index=X_panel.index)
            return result_df

        return _gnn_feature_stack_fold

    # ------------------------------------------------------------------
    # Sequence-first path (LSTM / TCN)
    # ------------------------------------------------------------------

    def _build_pooled_tabular_panel(
        self,
        panel_data: dict[str, pd.DataFrame],
        feature_layers: list[str],
        h: int,
        *,
        context: dict | None = None,
    ) -> tuple[pd.DataFrame, pd.Series]:
        """Build a pooled (date, symbol)-indexed feature panel + target.

        Mirrors the per-symbol feature-build loop inside
        ``_build_and_run_horizon`` but is callable from the base-model path
        without dragging in CV / GPU / Duan logic. Used by
        ``_run_one_horizon_sequences`` to construct the tabular panel its
        base model is trained on.
        """
        symbol_frames: list[tuple[pd.DataFrame, pd.Series]] = []
        for sym, daily_data in panel_data.items():
            sym_context = dict(context) if context else {}
            sym_context["symbol"] = sym
            feature_frames: list[pd.DataFrame] = []
            enriched_data = daily_data
            for layer_name in feature_layers:
                if layer_name not in FEATURE_REGISTRY:
                    raise ValueError(
                        f"Unknown feature layer (base_model): {layer_name!r}. "
                        f"Available: {list(FEATURE_REGISTRY.keys())}"
                    )
                layer_cls = FEATURE_REGISTRY[layer_name]
                layer = layer_cls()
                if getattr(layer, "_needs_base_features", False):
                    base_df = pd.concat(feature_frames, axis=1) if feature_frames else None
                    output = layer.compute(
                        enriched_data, context=sym_context, base_features=base_df
                    )
                else:
                    output = layer.compute(enriched_data, context=sym_context)
                if not output.empty:
                    enriched_data = pd.concat([enriched_data, output], axis=1)
                if not getattr(layer, "_enrichment_only", False):
                    feature_frames.append(output)

            if feature_frames:
                X_sym = pd.concat(feature_frames, axis=1)
            else:
                # Layers may all be enrichment-only; fall back to enriched_data
                # minus the original rv column to avoid leaking the target.
                X_sym = enriched_data.drop(columns=["rv"], errors="ignore")
            log_target = forward_log_rv(daily_data["rv"], h)
            aligned = pd.concat([X_sym, log_target.rename("target")], axis=1)
            aligned = aligned.replace([np.inf, -np.inf], np.nan)
            feature_cols = [c for c in aligned.columns if c != "target"]
            if feature_cols:
                mask = aligned["target"].notna() & ~aligned[feature_cols].isna().all(axis=1)
            else:
                mask = aligned["target"].notna()
            aligned = aligned.loc[mask]
            if len(aligned) == 0:
                continue
            X_clean = aligned[feature_cols]
            y_clean = aligned["target"]
            mi = pd.MultiIndex.from_arrays(
                [X_clean.index, [sym] * len(X_clean)],
                names=["date", "symbol"],
            )
            X_clean.index = mi
            y_clean.index = mi
            symbol_frames.append((X_clean, y_clean))

        if not symbol_frames:
            return pd.DataFrame(), pd.Series(dtype=float)

        all_cols: set[str] = set()
        for sf in symbol_frames:
            all_cols |= set(sf[0].columns)
        union_cols_sorted = sorted(all_cols)
        X_panel = pd.concat(
            [sf[0].reindex(columns=union_cols_sorted) for sf in symbol_frames]
        )
        y_panel = pd.concat([sf[1] for sf in symbol_frames])
        X_panel = X_panel.sort_index(level="date", kind="mergesort")
        y_panel = y_panel.loc[X_panel.index]
        return X_panel, y_panel

    def _resolve_sequence_config(self):
        """Return ``(features, max_bars, sequences_dir, cache_dir, norm_mode, source, bar_interval, lookback_days)`` from config."""
        from pathlib import Path as _Path

        from volforecast.config import SequenceConfig

        raw = self.config.sequences
        if raw is None:
            seq_cfg = SequenceConfig()
        elif isinstance(raw, dict):
            seq_cfg = SequenceConfig(**raw)
        else:
            seq_cfg = raw
        features = tuple(seq_cfg.features)
        max_bars = int(seq_cfg.max_bars)
        sequences_dir = _Path(seq_cfg.sequences_dir) if seq_cfg.sequences_dir else None
        cache_dir = _Path(seq_cfg.cache_dir) if seq_cfg.cache_dir else None
        norm_mode = getattr(seq_cfg, "norm_mode", "pooled")
        source = getattr(seq_cfg, "source", "parquet")
        bar_interval = getattr(seq_cfg, "bar_interval", 10)
        lookback_days = getattr(seq_cfg, "lookback_days", 20)
        return features, max_bars, sequences_dir, cache_dir, norm_mode, source, bar_interval, lookback_days

    def _run_pooled_sequences(
        self,
        panel_data: dict[str, pd.DataFrame],
        model_cls,
        *,
        on_fold_complete: Any | None = None,
        on_horizon_start: Any | None = None,
        on_train_progress: Any | None = None,
        on_batch_progress: Any | None = None,
        on_tuning_hpo: Any | None = None,
    ) -> dict[int, Any]:
        """Sequence-model pooled training across all configured horizons.

        Loads per-symbol ``SequenceTensor`` caches once (lazy build via
        ``load_sequence_tensor``), aligns by date with each horizon's target,
        runs expanding-window CV with per-fold normalisation (train-only stats
        — no leakage), and returns the same result dict as the tabular path.
        """
        import torch as _torch

        from volforecast.data.sequence_cache import (
            SequenceSpec,
            SequenceTensor,
            apply_normaliser,
            build_5min_sequence_tensor,
            build_daily_lookback_tensor,
            build_multiday_5min_sequence_tensor,
            fit_seq_normaliser,
            load_sequence_tensor,
        )

        features, max_bars, sequences_dir, cache_dir, norm_mode, source, bar_interval, lookback_days = self._resolve_sequence_config()
        spec = SequenceSpec(features=features, max_bars=max_bars, bar_interval=bar_interval)

        # Load each symbol's cached tensor once (built on first use).
        sym_seqs: dict[str, SequenceTensor] = {}
        skipped: list[str] = []
        if source == "daily_lookback":
            # Enrich panel with feature layers so daily sequences can reference
            # computed columns like log_rv_d, signed_return_d, etc.
            enriched_panel: dict[str, pd.DataFrame] = {}
            for sym, daily_data in panel_data.items():
                enriched = daily_data
                for layer_name in self.config.feature_layers:
                    if layer_name in FEATURE_REGISTRY:
                        layer = FEATURE_REGISTRY[layer_name]()
                        output = layer.compute(enriched, context={"symbol": sym})
                        if not output.empty:
                            enriched = pd.concat([enriched, output], axis=1)
                enriched_panel[sym] = enriched
            for sym, enriched in enriched_panel.items():
                missing_cols = [f for f in features if f not in enriched.columns]
                if missing_cols:
                    skipped.append(sym)
                    logger.warning(
                        "%s: daily_lookback missing columns %s; excluded", sym, missing_cols
                    )
                    continue
                seq = build_daily_lookback_tensor(sym, enriched, features, max_bars)
                if len(seq) > 0:
                    sym_seqs[sym] = seq
                else:
                    skipped.append(sym)
        elif source == "parquet_5min_multiday":
            for sym in panel_data:
                try:
                    sym_seqs[sym] = build_multiday_5min_sequence_tensor(
                        sym,
                        spec,
                        lookback_days=lookback_days,
                        sequences_dir=sequences_dir,
                    )
                except FileNotFoundError as exc:
                    skipped.append(sym)
                    logger.warning("%s: no sequence parquet (%s); excluded from run", sym, exc)
        elif source == "parquet_5min":
            for sym in panel_data:
                try:
                    sym_seqs[sym] = build_5min_sequence_tensor(
                        sym,
                        spec,
                        sequences_dir=sequences_dir,
                    )
                except FileNotFoundError as exc:
                    skipped.append(sym)
                    logger.warning("%s: no sequence parquet (%s); excluded from run", sym, exc)
        else:
            for sym in panel_data:
                try:
                    sym_seqs[sym] = load_sequence_tensor(
                        sym,
                        spec,
                        sequences_dir=sequences_dir,
                        cache_dir=cache_dir,
                    )
                except FileNotFoundError as exc:
                    skipped.append(sym)
                    logger.warning("%s: no sequence cache (%s); excluded from run", sym, exc)
        if not sym_seqs:
            if source == "daily_lookback":
                raise RuntimeError(
                    "No symbols have the required daily columns for daily_lookback sequences. "
                    f"Ensure panel_data contains columns: {list(features)}"
                )
            raise RuntimeError(
                "No symbols have sequence data on disk. Run `vol ingest-micro` "
                "first or check the sequences_dir setting."
            )
        if skipped:
            logger.info(
                "Sequence run: %d/%d symbols excluded (no cache)", len(skipped), len(panel_data)
            )

        results: dict[int, Any] = {}
        for h in self.config.horizons:
            if on_horizon_start is not None:
                on_horizon_start(h)
            base_cfg = self.config.base_model_for_horizon(h)
            results[h] = self._run_one_horizon_sequences(
                panel_data,
                sym_seqs,
                spec,
                h,
                model_cls,
                base_cfg=base_cfg,
                on_fold_complete=on_fold_complete,
                on_train_progress=on_train_progress,
                on_batch_progress=on_batch_progress,
                on_tuning_hpo=on_tuning_hpo,
                norm_mode=norm_mode,
                _torch=_torch,
                _SequenceTensor=SequenceTensor,
                _fit_seq_normaliser=fit_seq_normaliser,
                _apply_normaliser=apply_normaliser,
            )
        return results

    def _run_one_horizon_sequences(
        self,
        panel_data: dict[str, pd.DataFrame],
        sym_seqs: dict,
        spec,
        h: int,
        model_cls,
        *,
        base_cfg=None,
        on_fold_complete: Any | None = None,
        on_train_progress: Any | None = None,
        on_batch_progress: Any | None = None,
        on_tuning_hpo: Any | None = None,
        norm_mode: str = "pooled",
        _torch,
        _SequenceTensor,
        _fit_seq_normaliser,
        _apply_normaliser,
    ) -> dict[str, Any]:
        """One-horizon sequence-pooled CV — see :meth:`_run_pooled_sequences`."""
        rows_tensor: list = []
        rows_lengths: list = []
        rows_index: list[tuple] = []
        rows_target: list[float] = []
        rows_symbol_id: list[int] = []

        # Deterministic symbol→int mapping (sorted universe, stable across folds).
        all_symbols = sorted(sym_seqs.keys())
        symbol_to_id = {sym: i for i, sym in enumerate(all_symbols)}
        n_symbols = len(symbol_to_id)

        for sym, daily_data in panel_data.items():
            seq = sym_seqs.get(sym)
            if seq is None:
                continue
            rv = daily_data["rv"]
            log_target = forward_log_rv(rv, h)
            target_aligned = log_target.reindex(seq.dates)
            valid_mask = target_aligned.notna().values
            if not valid_mask.any():
                logger.warning(
                    "%s h=%d: no overlap between target dates and sequence cache", sym, h
                )
                continue
            valid_pos = _torch.from_numpy(np.ascontiguousarray(np.where(valid_mask)[0])).to(
                _torch.long
            )
            rows_tensor.append(seq.tensor.index_select(0, valid_pos))
            rows_lengths.append(seq.lengths.index_select(0, valid_pos))
            kept_dates = seq.dates[valid_mask]
            rows_index.extend([(d, sym) for d in kept_dates])
            rows_target.extend(target_aligned.values[valid_mask].astype(np.float32).tolist())
            sym_id = symbol_to_id[sym]
            rows_symbol_id.extend([sym_id] * int(valid_mask.sum()))

        if not rows_tensor:
            raise RuntimeError(f"h={h}: no (date, symbol) rows survived sequence/target alignment")

        tensor = _torch.cat(rows_tensor, dim=0)
        lengths = _torch.cat(rows_lengths, dim=0)
        idx = pd.MultiIndex.from_tuples(rows_index, names=["date", "symbol"])
        y = pd.Series(rows_target, index=idx, name="target", dtype=np.float32)
        symbol_ids_arr = np.array(rows_symbol_id, dtype=np.int64)

        # Sort by date primary for time-aware CV.
        sort_pos = np.argsort(idx.get_level_values("date").values, kind="mergesort")
        sort_pos_t = _torch.from_numpy(np.ascontiguousarray(sort_pos)).to(_torch.long)
        tensor = tensor.index_select(0, sort_pos_t)
        lengths = lengths.index_select(0, sort_pos_t)
        idx = idx[sort_pos]
        y = y.iloc[sort_pos]
        symbol_ids_arr = symbol_ids_arr[sort_pos]
        symbol_ids_t = _torch.from_numpy(symbol_ids_arr).to(_torch.long)

        # ---- Build context array (daily features for LSTM conditioning) ----
        context_features = getattr(spec, 'context_features', []) or []
        context_arr: np.ndarray | None = None
        if context_features:
            ctx_cols = []
            for feat_name in context_features:
                col_values = np.full(len(idx), np.nan, dtype=np.float32)
                for sym, daily_df in panel_data.items():
                    if feat_name not in daily_df.columns:
                        continue
                    # Find row positions in idx where symbol matches
                    sym_mask = idx.get_level_values("symbol") == sym
                    sym_dates = idx.get_level_values("date")[sym_mask]
                    # Reindex the feature column to the needed dates
                    aligned = daily_df[feat_name].reindex(sym_dates)
                    col_values[sym_mask] = aligned.values.astype(np.float32)
                ctx_cols.append(col_values)
            context_arr = np.column_stack(ctx_cols)
            logger.info(
                "h=%d: built context array shape=%s from features=%s",
                h, context_arr.shape, context_features,
            )
            model_params["context_dim"] = len(context_features)

        # Date-based panel splitter.
        cv_cfg = self.config.cv_for_horizon(h)
        effective_purge = max(cv_cfg.purge_gap, h)
        panel_cv = PanelExpandingWindowCV(
            min_train_dates=cv_cfg.train_size or 252,
            test_dates=cv_cfg.test_size or 63,
            step_dates=cv_cfg.test_size or 63,
            purge_gap=effective_purge,
            embargo=getattr(cv_cfg, "embargo", 0),
        )
        date_index = idx.get_level_values("date")
        X_for_cv = pd.DataFrame({"_dummy": np.zeros(len(idx))}, index=date_index)

        model_params = dict(self.config.model_params_for_horizon(h))
        # Auto-fill input_dim from the spec if the user didn't override.
        model_params.setdefault("input_dim", tensor.shape[2])
        # Auto-fill n_symbols from the pooled universe (runner knows the count).
        if model_params.get("symbol_embed_dim", 0) > 0:
            model_params.setdefault("n_symbols", n_symbols)

        # Base-model residual setup (trial-052 / stacked sequence models).
        # When ``base_cfg`` is set, we build the base's tabular panel once,
        # then per fold fit the base on the fold's training dates and align
        # predictions back to (date, symbol) sequence rows.
        base_X: pd.DataFrame | None = None
        base_y: pd.Series | None = None
        base_cls = None
        if base_cfg is not None:
            if base_cfg.name not in MODEL_REGISTRY:
                raise ValueError(
                    f"base_model.name={base_cfg.name!r} not in registry. "
                    f"Available: {list(MODEL_REGISTRY.keys())}"
                )
            base_cls = MODEL_REGISTRY[base_cfg.name]
            base_X, base_y = self._build_pooled_tabular_panel(
                panel_data, base_cfg.feature_layers, h
            )
            if base_X.empty:
                raise RuntimeError(
                    f"h={h}: base_model {base_cfg.name!r} produced an empty "
                    "panel (no rows survived feature build + target alignment)"
                )
            logger.info(
                "h=%d: base_model=%s built panel rows=%d cols=%d (layers=%s)",
                h,
                base_cfg.name,
                len(base_X),
                base_X.shape[1],
                base_cfg.feature_layers,
            )

        all_preds = pd.Series(np.nan, index=idx, dtype=float)
        duan_corrections: list[float] = []
        last_model = None
        fold_num = 0

        # Fold-level training cache (skip retrain when an identical fold has
        # already been trained for this config + dates + base preds).
        from volforecast.pipeline.fold_cache import (
            compute_fold_cache_key,
            load_fold_cache,
            save_fold_cache,
        )

        cache_enabled = bool(getattr(self.config, "fold_cache_enabled", True))
        cache_root_cfg = getattr(self.config, "fold_cache_dir", None)
        cache_root = Path(cache_root_cfg) if cache_root_cfg else None

        # Pre-enumerate folds for parallel dispatch.
        fold_splits = list(panel_cv.split(X_for_cv))
        n_folds = len(fold_splits)

        # Serialise base_cfg for pickling to worker processes.
        base_cfg_dict: dict | None = None
        if base_cfg is not None:
            base_cfg_dict = {
                "name": base_cfg.name,
                "feature_layers": list(base_cfg.feature_layers),
                "params": dict(base_cfg.params),
            }

        # ---- LSTM HPO (Optuna) ------------------------------------------
        # If tuning is enabled and the model supports it, run multi-GPU HPO
        # before the fold loop. The best params override model_params for all
        # subsequent folds.
        tuning_enabled = (
            getattr(self.config, "tuning", None) is not None
            and getattr(self.config.tuning, "enabled", False)
            and getattr(model_cls, "supports_tuning", False)
        )
        if tuning_enabled:
            from volforecast.models.lstm_tuning import tune_lstm_hyperparameters

            import multiprocessing as _tune_mp

            tuning_cfg = self.config.tuning
            _tune_n_gpus = getattr(self.config, "n_gpus", 1)

            # Build a progress queue for HPO events
            _tune_manager = _tune_mp.Manager()
            _tune_queue = _tune_manager.Queue()

            # Prepare symbol_ids as numpy for the tuning module
            _tune_sym_ids = symbol_ids_arr.copy()

            # Fixed params = everything in model_params that isn't in the search space
            _tune_fixed = dict(model_params)
            # Ensure input_dim is set
            _tune_fixed["input_dim"] = int(tensor.shape[2])

            # Inner CV config
            inner_cv = tuning_cfg.inner_cv
            if inner_cv is None:
                from volforecast.config import CVConfig
                inner_cv = CVConfig(
                    method="expanding_window",
                    purge_gap=max(10, h),
                    train_size=756,
                    test_size=126,
                )

            logger.info(
                "h=%d: LSTM HPO starting — %d trials across %d GPUs",
                h, tuning_cfg.n_trials, _tune_n_gpus,
            )

            # Forward HPO progress to the on_tuning_hpo callback
            import threading as _tune_threading

            _tune_stop = _tune_threading.Event()

            def _consume_tuning_progress() -> None:
                """Consumer thread: read HPO events and forward to callbacks."""
                while not _tune_stop.is_set():
                    try:
                        event = _tune_queue.get(timeout=0.5)
                    except Exception:
                        continue
                    if event is None:
                        break
                    if on_tuning_hpo is not None:
                        on_tuning_hpo(event)
                    elif on_train_progress is not None:
                        if event.get("type") == "tuning_epoch":
                            on_train_progress(event["epoch"], event["max_epochs"])

            _tune_consumer = _tune_threading.Thread(
                target=_consume_tuning_progress, daemon=True
            )
            _tune_consumer.start()

            best_params = tune_lstm_hyperparameters(
                tensor=tensor,
                lengths=lengths,
                y_values=y.values.astype(np.float64),
                symbol_ids=_tune_sym_ids,
                idx=idx,
                spec_features=tuple(spec.features),
                cv_config=inner_cv,
                n_trials=tuning_cfg.n_trials,
                n_gpus=_tune_n_gpus,
                timeout=tuning_cfg.timeout,
                seed=model_params.get("seed", 42),
                base_cfg_dict=base_cfg_dict,
                base_X=base_X,
                base_y=base_y,
                norm_mode=norm_mode,
                fixed_params=_tune_fixed,
                storage_dir=Path(tuning_cfg.storage_dir) if tuning_cfg.storage_dir else None,
                progress_queue=_tune_queue,
            )

            # Stop the consumer thread
            _tune_queue.put(None)
            _tune_stop.set()
            _tune_consumer.join(timeout=5.0)
            _tune_manager.shutdown()

            # Merge HPO-found params into model_params for all folds
            model_params.update(best_params)
            logger.info("h=%d: LSTM HPO complete — best params merged: %s", h, best_params)

        n_gpus = getattr(self.config, "n_gpus", 1)
        use_parallel = (
            n_gpus > 1
            and n_folds > 1
            and _torch.cuda.is_available()
            and _torch.cuda.device_count() >= 2
        )

        if use_parallel:
            import threading

            import torch.multiprocessing as _mp

            # Ensure tensors can be shared across forked processes.
            tensor.share_memory_()
            lengths.share_memory_()
            symbol_ids_t.share_memory_()

            available_gpus = _torch.cuda.device_count()
            effective_gpus = min(n_gpus, available_gpus)
            logger.info(
                "h=%d: parallel fold dispatch — %d folds across %d GPUs",
                h, n_folds, effective_gpus,
            )

            ctx = _mp.get_context("spawn")
            from concurrent.futures import ProcessPoolExecutor, as_completed

            # Strip unpicklable callbacks from config before sending to workers
            _picklable_config = self.config
            if (
                hasattr(self.config, "tuning")
                and self.config.tuning is not None
                and (
                    getattr(self.config.tuning, "_on_trial_complete", None) is not None
                    or getattr(self.config.tuning, "_on_train_progress", None) is not None
                )
            ):
                from dataclasses import replace as _dc_replace
                _picklable_config = _dc_replace(
                    self.config,
                    tuning=_dc_replace(
                        self.config.tuning,
                        _on_trial_complete=None,
                        _on_train_progress=None,
                    ),
                )

            # Set up cross-process progress queue so GPU workers can report
            # epoch progress back to the main process's Rich progress bar.
            _manager = _mp.Manager()
            _progress_queue = _manager.Queue()
            _consumer_stop = threading.Event()

            def _consume_epoch_progress() -> None:
                """Consumer thread: read epoch events and forward to callback."""
                while not _consumer_stop.is_set():
                    try:
                        event = _progress_queue.get(timeout=0.5)
                    except Exception:  # noqa: BLE001  — queue.Empty or closed
                        continue
                    if event is None:
                        break
                    if on_train_progress is not None and event.get("type") == "epoch":
                        on_train_progress(event["epoch"], event["max_epochs"])

            _consumer_thread = threading.Thread(target=_consume_epoch_progress, daemon=True)
            _consumer_thread.start()

            with ProcessPoolExecutor(
                max_workers=effective_gpus, mp_context=ctx,
            ) as pool:
                futures = {}
                for fold_num_0, (train_idx_arr, test_idx_arr) in enumerate(fold_splits, start=1):
                    device_id = (fold_num_0 - 1) % effective_gpus
                    future = pool.submit(
                        _execute_fold,
                        fold_num=fold_num_0,
                        h=h,
                        train_idx_arr=train_idx_arr,
                        test_idx_arr=test_idx_arr,
                        tensor=tensor,
                        lengths=lengths,
                        symbol_ids_tensor=symbol_ids_t,
                        idx=idx,
                        y_values=y.values,
                        model_cls_name=model_cls.name,
                        model_params=model_params,
                        spec_features=tuple(spec.features),
                        base_cfg_dict=base_cfg_dict,
                        base_X=base_X,
                        base_y=base_y,
                        config_dict=_picklable_config,
                        cache_enabled=cache_enabled,
                        cache_root=str(cache_root) if cache_root else None,
                        device_id=device_id,
                        seed_offset=fold_num_0,
                        norm_mode=norm_mode,
                        progress_queue=_progress_queue,
                    )
                    futures[future] = fold_num_0

                for future in as_completed(futures):
                    result = future.result()
                    fn = result["fold_num"]
                    all_preds.iloc[result["test_idx_arr"]] = result["preds"]
                    duan_corrections.append(result["duan_correction"])
                    if on_fold_complete is not None:
                        on_fold_complete(h, fn)
                    # Keep last_model from last fold (by number)
                    if result.get("model_path") and hasattr(model_cls, "load"):
                        try:
                            last_model = model_cls.load(result["model_path"])
                        except Exception:  # noqa: BLE001
                            pass

            # Shut down progress consumer.
            _progress_queue.put(None)
            _consumer_stop.set()
            _consumer_thread.join(timeout=5.0)
            _manager.shutdown()

        else:
            # Sequential path — preserves progress callbacks.
            for train_idx_arr, test_idx_arr in fold_splits:
                fold_num += 1

                # Hoisted: fold-level (date, symbol) MultiIndex slices. Needed
                # for both the base-model fit (max_train_date filter) and the
                # cache key (train/test date hashes).
                fold_train_idx = idx[train_idx_arr]
                fold_test_idx = idx[test_idx_arr]
                fold_train_dates = pd.DatetimeIndex(
                    fold_train_idx.get_level_values("date").unique()
                )
                fold_test_dates = pd.DatetimeIndex(
                    fold_test_idx.get_level_values("date").unique()
                )

                # ---- Per-fold base-model fit + alignment (computed first so the
                # cache key can include the base-preds hash; a change in the base
                # model auto-invalidates the LSTM cache). ----------------------
                base_preds_train: np.ndarray | None = None
                base_preds_test: np.ndarray | None = None
                if base_cfg is not None and base_X is not None and base_y is not None:
                    max_train_date = pd.Timestamp(fold_train_idx.get_level_values("date").max())
                    base_date = pd.DatetimeIndex(base_X.index.get_level_values("date"))
                    base_train_mask = base_date <= max_train_date
                    base_X_train = base_X.loc[base_train_mask]
                    base_y_train = base_y.loc[base_train_mask]
                    if base_X_train.empty:
                        raise RuntimeError(
                            f"h={h} fold={fold_num}: base_model has no training "
                            f"rows on or before {max_train_date}"
                        )
                    base_inst = base_cls(**base_cfg.params)
                    base_inst.fit(base_X_train, base_y_train)

                    all_base_preds_arr = np.asarray(base_inst.predict(base_X), dtype=np.float64)
                    all_base_preds = pd.Series(all_base_preds_arr, index=base_X.index)
                    # Train-only mean as NaN fallback (no leakage).
                    train_pred_slice = all_base_preds.loc[base_train_mask]
                    fallback = float(np.nanmean(train_pred_slice.values))
                    if not np.isfinite(fallback):
                        fallback = 0.0

                    def _lookup(seq_idx: pd.MultiIndex) -> np.ndarray:
                        aligned = all_base_preds.reindex(seq_idx).values.astype(np.float64)
                        nan_mask = np.isnan(aligned)
                        if nan_mask.any():
                            logger.warning(
                                "h=%d fold=%d: %d/%d seq rows missing base preds; using fallback %.4f",
                                h,
                                fold_num,
                                int(nan_mask.sum()),
                                len(aligned),
                                fallback,
                            )
                            aligned[nan_mask] = fallback
                        return aligned.astype(np.float32)

                    base_preds_train = _lookup(fold_train_idx)
                    base_preds_test = _lookup(fold_test_idx)

                # ---- Cache lookup ---------------------------------------------
                cache_key = compute_fold_cache_key(
                    self.config,
                    h,
                    fold_num,
                    fold_train_dates,
                    fold_test_dates,
                    base_preds_train=base_preds_train,
                    base_preds_test=base_preds_test,
                )
                cache_hit = None
                if cache_enabled:
                    cache_hit = load_fold_cache(
                        config=self.config, key=cache_key, cache_root=cache_root
                    )
                    if cache_hit is not None and cache_hit.preds.shape[0] != len(test_idx_arr):
                        logger.warning(
                            "h=%d fold=%d: cache preds length %d != expected %d; retraining",
                            h,
                            fold_num,
                            cache_hit.preds.shape[0],
                            len(test_idx_arr),
                        )
                        cache_hit = None

                if cache_hit is not None:
                    logger.info(
                        "h=%d fold=%d: training cache HIT (key=%s); skipping fit",
                        h,
                        fold_num,
                        cache_key,
                    )
                    duan_corrections.append(cache_hit.duan_correction)
                    all_preds.iloc[test_idx_arr] = cache_hit.preds
                    if cache_hit.model_path is not None and hasattr(model_cls, "load"):
                        try:
                            last_model = model_cls.load(cache_hit.model_path)
                        except Exception as exc:  # noqa: BLE001 — model load is best-effort
                            logger.warning(
                                "h=%d fold=%d: cached model load failed (%s); leaving last_model unset",
                                h,
                                fold_num,
                                exc,
                            )
                    if on_fold_complete is not None:
                        on_fold_complete(h, fold_num)
                    continue

                # ---- Cache miss: per-fold normaliser + training ---------------
                tr_pos = _torch.from_numpy(np.ascontiguousarray(train_idx_arr)).to(_torch.long)
                te_pos = _torch.from_numpy(np.ascontiguousarray(test_idx_arr)).to(_torch.long)
                X_tr = tensor.index_select(0, tr_pos)
                L_tr = lengths.index_select(0, tr_pos)
                y_tr_arr = y.values[train_idx_arr]
                X_te = tensor.index_select(0, te_pos)
                L_te = lengths.index_select(0, te_pos)
                sym_ids_tr = symbol_ids_t.index_select(0, tr_pos)
                sym_ids_te = symbol_ids_t.index_select(0, te_pos)

                # Per-fold normalisation (mode-dependent).
                if norm_mode == "per_symbol":
                    from volforecast.pipeline.norm import (
                        apply_per_symbol_normaliser,
                        fit_per_symbol_normaliser,
                    )

                    normalisers = fit_per_symbol_normaliser(X_tr, L_tr, sym_ids_tr)
                    tr_normed_tensor = apply_per_symbol_normaliser(
                        X_tr, L_tr, sym_ids_tr, normalisers
                    )
                    te_normed_tensor = apply_per_symbol_normaliser(
                        X_te, L_te, sym_ids_te, normalisers
                    )
                    tr_synth = pd.DatetimeIndex(
                        pd.bdate_range("2000-01-01", periods=int(X_tr.shape[0]))
                    )
                    tr_normed = _SequenceTensor(
                        symbol="_pooled_train",
                        tensor=tr_normed_tensor,
                        lengths=L_tr,
                        dates=tr_synth,
                        feature_names=spec.features,
                    )
                    te_synth = pd.DatetimeIndex(
                        pd.bdate_range("2000-01-01", periods=int(X_te.shape[0]))
                    )
                    te_normed = _SequenceTensor(
                        symbol="_pooled_test",
                        tensor=te_normed_tensor,
                        lengths=L_te,
                        dates=te_synth,
                        feature_names=spec.features,
                    )
                else:
                    # Pooled normaliser (default): single (mean, std) across all symbols.
                    tr_synth = pd.DatetimeIndex(
                        pd.bdate_range("2000-01-01", periods=int(X_tr.shape[0]))
                    )
                    tr_pseudo = _SequenceTensor(
                        symbol="_pooled_train",
                        tensor=X_tr,
                        lengths=L_tr,
                        dates=tr_synth,
                        feature_names=spec.features,
                    )
                    mean, std = _fit_seq_normaliser(tr_pseudo, tr_synth)

                    tr_normed = _apply_normaliser(tr_pseudo, mean, std)
                    te_synth = pd.DatetimeIndex(
                        pd.bdate_range("2000-01-01", periods=int(X_te.shape[0]))
                    )
                    te_pseudo = _SequenceTensor(
                        symbol="_pooled_test",
                        tensor=X_te,
                        lengths=L_te,
                        dates=te_synth,
                        feature_names=spec.features,
                    )
                    te_normed = _apply_normaliser(te_pseudo, mean, std)

                # ---- Context slicing for this fold -------------------------
                context_train = context_arr[train_idx_arr] if context_arr is not None else None
                context_test = context_arr[test_idx_arr] if context_arr is not None else None

                model = model_cls(**model_params)
                # Only pass symbol_ids when the model supports embedding.
                _use_sym_ids = getattr(model, "n_symbols", 0) > 0
                if _use_sym_ids:
                    model.symbol_to_id = symbol_to_id
                if on_train_progress is not None and getattr(
                    model_cls, "requires_sequences", False
                ):
                    fit_kwargs: dict[str, Any] = {"on_progress": on_train_progress}
                    if on_batch_progress is not None:
                        fit_kwargs["on_batch_progress"] = on_batch_progress
                    if base_preds_train is not None:
                        fit_kwargs["base_preds"] = base_preds_train
                    if _use_sym_ids:
                        fit_kwargs["symbol_ids"] = sym_ids_tr
                    if context_train is not None:
                        fit_kwargs["context"] = context_train
                    model.fit(tr_normed, y_tr_arr, **fit_kwargs)
                else:
                    if base_preds_train is not None:
                        if _use_sym_ids:
                            model.fit(tr_normed, y_tr_arr, base_preds=base_preds_train, symbol_ids=sym_ids_tr, **({"context": context_train} if context_train is not None else {}))
                        else:
                            model.fit(tr_normed, y_tr_arr, base_preds=base_preds_train, **({"context": context_train} if context_train is not None else {}))
                    else:
                        if _use_sym_ids:
                            model.fit(tr_normed, y_tr_arr, symbol_ids=sym_ids_tr, **({"context": context_train} if context_train is not None else {}))
                        else:
                            model.fit(tr_normed, y_tr_arr, **({"context": context_train} if context_train is not None else {}))

                if base_preds_test is not None:
                    if _use_sym_ids:
                        preds = np.asarray(
                            model.predict(te_normed, base_preds=base_preds_test, symbol_ids=sym_ids_te, **({"context": context_test} if context_test is not None else {})), dtype=np.float64
                        )
                        train_preds = np.asarray(
                            model.predict(tr_normed, base_preds=base_preds_train, symbol_ids=sym_ids_tr, **({"context": context_train} if context_train is not None else {})), dtype=np.float64
                        )
                    else:
                        preds = np.asarray(
                            model.predict(te_normed, base_preds=base_preds_test, **({"context": context_test} if context_test is not None else {})), dtype=np.float64
                        )
                        train_preds = np.asarray(
                            model.predict(tr_normed, base_preds=base_preds_train, **({"context": context_train} if context_train is not None else {})), dtype=np.float64
                        )
                else:
                    if _use_sym_ids:
                        preds = np.asarray(model.predict(te_normed, symbol_ids=sym_ids_te, **({"context": context_test} if context_test is not None else {})), dtype=np.float64)
                        train_preds = np.asarray(model.predict(tr_normed, symbol_ids=sym_ids_tr, **({"context": context_train} if context_train is not None else {})), dtype=np.float64)
                    else:
                        preds = np.asarray(model.predict(te_normed, **({"context": context_test} if context_test is not None else {})), dtype=np.float64)
                        train_preds = np.asarray(model.predict(tr_normed, **({"context": context_train} if context_train is not None else {})), dtype=np.float64)

                # Duan retransformation — mirror tabular path.
                train_residuals = y_tr_arr - train_preds
                valid_resid = train_residuals[~np.isnan(train_residuals)]
                if len(valid_resid) > 0:
                    correction = float(np.log(np.mean(np.exp(np.clip(valid_resid, -10.0, 10.0)))))
                else:
                    correction = 0.0
                duan_corrections.append(correction)
                preds = preds + correction

                all_preds.iloc[test_idx_arr] = preds
                last_model = model

                # ---- Persist fold artifacts -----------------------------------
                if cache_enabled:
                    try:
                        save_fold_cache(
                            config=self.config,
                            key=cache_key,
                            preds=preds,
                            duan_correction=correction,
                            model=model,
                            train_dates=fold_train_dates,
                            test_dates=fold_test_dates,
                            h=h,
                            fold_num=fold_num,
                            cache_root=cache_root,
                        )
                    except Exception as exc:  # noqa: BLE001 — cache is best-effort
                        logger.warning(
                            "h=%d fold=%d: cache save failed (%s)", h, fold_num, exc
                        )

                if on_fold_complete is not None:
                    on_fold_complete(h, fold_num)

        valid_mask = all_preds.notna()
        if not valid_mask.any():
            logger.warning("h=%d: no test predictions produced (insufficient folds)", h)
            return {
                "metrics": {"qlike": float("nan"), "mse": float("nan"), "r_squared": float("nan")},
                "predictions": all_preds[valid_mask],
                "actuals": y[valid_mask],
                "model": last_model,
                "duan_correction": 0.0,
            }

        y_eval = y[valid_mask].values
        p_eval = all_preds[valid_mask].values
        metrics = {
            "qlike": qlike(y_eval, p_eval),
            "mse": mse(y_eval, p_eval),
            "r_squared": r_squared(y_eval, p_eval),
        }
        mean_correction = float(np.mean(duan_corrections)) if duan_corrections else 0.0
        if abs(mean_correction) > 0.01:
            logger.info(
                "h=%d sequence path: Duan correction mean=%.4f across %d folds",
                h,
                mean_correction,
                len(duan_corrections),
            )

        return {
            "metrics": metrics,
            "predictions": all_preds[valid_mask],
            "actuals": y[valid_mask],
            "model": last_model,
            "duan_correction": mean_correction,
        }
