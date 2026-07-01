"""LSTM hyperparameter tuning via Optuna with multi-GPU parallel trials.

Each trial trains an LSTM on an inner expanding-window CV (2-3 folds) and
reports the mean QLIKE. Multiple trials run simultaneously — one per GPU —
coordinated via Optuna JournalStorage (append-only, process-safe).

Usage (from the runner or LSTM model class)::

    best_params = tune_lstm_hyperparameters(
        tensor=shared_tensor,       # (N, T, F) float32, share_memory_()
        lengths=shared_lengths,     # (N,) int64, share_memory_()
        y_values=y_arr,             # (N,) float64
        symbol_ids=sym_ids_arr,     # (N,) int64
        idx=panel_idx,              # pd.MultiIndex (date, symbol)
        spec_features=("log_ret", ...),
        cv_config=inner_cv_cfg,
        n_trials=40,
        n_gpus=8,
        seed=42,
        base_cfg_dict=...,
        base_X=...,
        base_y=...,
        norm_mode="pooled",
        fixed_params={"bidirectional": True, "max_epochs": 80, ...},
        progress_queue=queue,       # mp.Manager().Queue() for progress events
    )
"""

from __future__ import annotations

import logging
import math
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Search space definition
# ---------------------------------------------------------------------------

LSTM_SEARCH_SPACE = {
    "hidden_dim": {"type": "categorical", "choices": [32, 64, 128]},
    "n_layers": {"type": "categorical", "choices": [1, 2, 3]},
    "learning_rate": {"type": "float", "low": 3e-4, "high": 5e-3, "log": True},
    "dropout": {"type": "float", "low": 0.05, "high": 0.4},
    "weight_decay": {"type": "float", "low": 1e-5, "high": 1e-3, "log": True},
    "batch_size": {"type": "categorical", "choices": [256, 512, 1024]},
}


def _suggest_params(trial) -> dict[str, Any]:  # noqa: ANN001 (optuna.Trial)
    """Sample LSTM hyperparameters from Optuna trial."""
    params: dict[str, Any] = {}
    for name, spec in LSTM_SEARCH_SPACE.items():
        if spec["type"] == "categorical":
            params[name] = trial.suggest_categorical(name, spec["choices"])
        elif spec["type"] == "float":
            params[name] = trial.suggest_float(
                name, spec["low"], spec["high"], log=spec.get("log", False)
            )
        elif spec["type"] == "int":
            params[name] = trial.suggest_int(
                name, spec["low"], spec["high"], log=spec.get("log", False)
            )
    return params


# ---------------------------------------------------------------------------
# Inner CV objective
# ---------------------------------------------------------------------------


def _make_lstm_objective(
    tensor: torch.Tensor,
    lengths: torch.Tensor,
    y_values: np.ndarray,
    symbol_ids: np.ndarray,
    idx: pd.MultiIndex,
    spec_features: tuple[str, ...],
    cv_config_dict: dict[str, Any],
    device_id: int,
    seed: int,
    base_cfg_dict: dict | None,
    base_X_values: np.ndarray | None,
    base_X_index: Any | None,
    base_X_columns: list[str] | None,
    base_y_values: np.ndarray | None,
    base_y_index: Any | None,
    norm_mode: str,
    fixed_params: dict[str, Any],
    progress_queue: Any | None = None,
):
    """Build an Optuna objective closure for LSTM QLIKE tuning.

    Returns a callable ``objective(trial) -> float`` that trains an LSTM on
    inner CV folds and returns the mean QLIKE.
    """
    import optuna

    from volforecast.config import CVConfig
    from volforecast.data.sequence_cache import SequenceTensor, apply_normaliser, fit_seq_normaliser
    from volforecast.evaluation.metrics import qlike
    from volforecast.models.lstm import LSTMVolModel
    from volforecast.registry import MODEL_REGISTRY
    from volforecast.utils.cv import PanelExpandingWindowCV

    cv_cfg = CVConfig(**cv_config_dict)

    def objective(trial: optuna.Trial) -> float:
        # Sample hyperparameters
        sampled = _suggest_params(trial)
        # Merge with fixed params (fixed override sampled for safety)
        model_kwargs = {**sampled, **fixed_params}
        model_kwargs["device"] = f"cuda:{device_id}"
        model_kwargs["input_dim"] = int(tensor.shape[2])
        model_kwargs["seed"] = seed + trial.number

        # Rebuild base_X/base_y DataFrames in this process (passed as numpy for pickling)
        base_X: pd.DataFrame | None = None
        base_y: pd.Series | None = None
        if base_cfg_dict is not None and base_X_values is not None:
            base_X = pd.DataFrame(base_X_values, index=base_X_index, columns=base_X_columns)
            base_y = pd.Series(base_y_values, index=base_y_index)

        # Build panel CV splitter for inner folds
        date_index = idx.get_level_values("date")
        X_for_cv = pd.DataFrame({"_dummy": np.zeros(len(idx))}, index=date_index)

        effective_purge = max(cv_cfg.purge_gap, 1)
        panel_cv = PanelExpandingWindowCV(
            min_train_dates=cv_cfg.train_size or 756,
            test_dates=cv_cfg.test_size or 126,
            step_dates=cv_cfg.test_size or 126,
            purge_gap=effective_purge,
        )

        fold_splits = list(panel_cv.split(X_for_cv))
        # Limit to 3 inner folds max for speed
        if len(fold_splits) > 3:
            # Take evenly-spaced folds
            indices_to_use = np.linspace(0, len(fold_splits) - 1, 3, dtype=int)
            fold_splits = [fold_splits[i] for i in indices_to_use]

        scores: list[float] = []
        for fold_idx, (train_idx_arr, test_idx_arr) in enumerate(fold_splits):
            # Slice tensors
            tr_pos = torch.from_numpy(np.ascontiguousarray(train_idx_arr)).to(torch.long)
            te_pos = torch.from_numpy(np.ascontiguousarray(test_idx_arr)).to(torch.long)
            X_tr = tensor.index_select(0, tr_pos)
            L_tr = lengths.index_select(0, tr_pos)
            y_tr_arr = y_values[train_idx_arr]
            X_te = tensor.index_select(0, te_pos)
            L_te = lengths.index_select(0, te_pos)
            sym_ids_tr = torch.from_numpy(symbol_ids[train_idx_arr]).to(torch.long)
            sym_ids_te = torch.from_numpy(symbol_ids[test_idx_arr]).to(torch.long)

            # Base-model predictions for this inner fold
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

                fold_train_idx = idx[train_idx_arr]
                max_train_date = pd.Timestamp(fold_train_idx.get_level_values("date").max())
                base_date = pd.DatetimeIndex(base_X.index.get_level_values("date"))
                base_train_mask = base_date <= max_train_date
                base_X_train = base_X.loc[base_train_mask]
                base_y_train = base_y.loc[base_train_mask]

                if not base_X_train.empty:
                    base_inst = base_cls(**base_cfg.params)
                    base_inst.fit(base_X_train, base_y_train)
                    all_base_preds_arr = np.asarray(
                        base_inst.predict(base_X), dtype=np.float64
                    )
                    all_base_preds = pd.Series(all_base_preds_arr, index=base_X.index)
                    fallback = float(np.nanmean(all_base_preds.loc[base_train_mask].values))
                    if not np.isfinite(fallback):
                        fallback = 0.0

                    fold_train_mi = idx[train_idx_arr]
                    fold_test_mi = idx[test_idx_arr]

                    def _lookup(seq_idx: pd.MultiIndex) -> np.ndarray:
                        aligned = all_base_preds.reindex(seq_idx).values.astype(np.float64)
                        nan_mask = np.isnan(aligned)
                        if nan_mask.any():
                            aligned[nan_mask] = fallback
                        return aligned.astype(np.float32)

                    base_preds_train = _lookup(fold_train_mi)
                    base_preds_test = _lookup(fold_test_mi)

            # Normalise sequences
            if norm_mode == "per_symbol":
                from volforecast.pipeline.norm import (
                    apply_per_symbol_normaliser,
                    fit_per_symbol_normaliser,
                )

                normalisers = fit_per_symbol_normaliser(X_tr, L_tr, sym_ids_tr)
                X_tr = apply_per_symbol_normaliser(X_tr, L_tr, sym_ids_tr, normalisers)
                X_te = apply_per_symbol_normaliser(X_te, L_te, sym_ids_te, normalisers)

            tr_synth = pd.DatetimeIndex(pd.bdate_range("2000-01-01", periods=int(X_tr.shape[0])))
            tr_seq = SequenceTensor(
                symbol="_tuning_train",
                tensor=X_tr,
                lengths=L_tr,
                dates=tr_synth,
                feature_names=spec_features,
            )

            if norm_mode != "per_symbol":
                mean, std = fit_seq_normaliser(tr_seq, tr_synth)
                tr_seq = apply_normaliser(tr_seq, mean, std)
                te_synth = pd.DatetimeIndex(
                    pd.bdate_range("2000-01-01", periods=int(X_te.shape[0]))
                )
                te_seq = SequenceTensor(
                    symbol="_tuning_test",
                    tensor=X_te,
                    lengths=L_te,
                    dates=te_synth,
                    feature_names=spec_features,
                )
                te_seq = apply_normaliser(te_seq, mean, std)
            else:
                te_synth = pd.DatetimeIndex(
                    pd.bdate_range("2000-01-01", periods=int(X_te.shape[0]))
                )
                te_seq = SequenceTensor(
                    symbol="_tuning_test",
                    tensor=X_te,
                    lengths=L_te,
                    dates=te_synth,
                    feature_names=spec_features,
                )

            # Build and train model
            model = LSTMVolModel(**model_kwargs)
            use_sym = model.n_symbols > 0

            fit_kwargs: dict[str, Any] = {}
            if use_sym:
                fit_kwargs["symbol_ids"] = sym_ids_tr
            if base_preds_train is not None:
                fit_kwargs["base_preds"] = base_preds_train

            # Epoch progress callback for the progress queue
            if progress_queue is not None:
                def _on_progress(epoch: int, max_epochs: int, _trial=trial) -> None:
                    progress_queue.put({
                        "type": "tuning_epoch",
                        "trial_num": _trial.number,
                        "epoch": epoch,
                        "max_epochs": max_epochs,
                        "device_id": device_id,
                    })
                fit_kwargs["on_progress"] = _on_progress

            try:
                model.fit(tr_seq, y_tr_arr, **fit_kwargs)
            except Exception as e:
                logger.warning("Trial %d fold %d failed: %s", trial.number, fold_idx, e)
                raise optuna.TrialPruned()

            # Predict and score
            pred_kwargs: dict[str, Any] = {}
            if use_sym:
                pred_kwargs["symbol_ids"] = sym_ids_te
            if base_preds_test is not None:
                pred_kwargs["base_preds"] = base_preds_test

            preds = np.asarray(model.predict(te_seq, **pred_kwargs), dtype=np.float64)
            y_test = y_values[test_idx_arr]

            # Filter finite targets
            finite_mask = np.isfinite(y_test) & np.isfinite(preds)
            if finite_mask.sum() < 10:
                raise optuna.TrialPruned()

            fold_qlike = qlike(y_test[finite_mask], preds[finite_mask])
            scores.append(fold_qlike)

            # Report to Optuna for pruning
            trial.report(float(np.mean(scores)), fold_idx)
            if trial.should_prune():
                raise optuna.TrialPruned()

            # Free GPU memory between folds
            del model
            torch.cuda.empty_cache()

        mean_qlike = float(np.mean(scores))
        return mean_qlike

    return objective


# ---------------------------------------------------------------------------
# Worker process (1 per GPU)
# ---------------------------------------------------------------------------


def _make_trial_done_callback(progress_queue: Any | None, device_id: int):
    """Create an Optuna callback that fires on every trial (completed or pruned)."""

    def callback(study, frozen_trial) -> None:  # noqa: ANN001
        if progress_queue is None:
            return
        params = frozen_trial.params
        state = frozen_trial.state.name  # COMPLETE, PRUNED, FAIL
        qlike = frozen_trial.value if frozen_trial.value is not None else float("inf")
        progress_queue.put({
            "type": "tuning_trial_complete",
            "trial_num": frozen_trial.number,
            "qlike": qlike,
            "params": params,
            "device_id": device_id,
            "state": state,
        })

    return callback


def _lstm_optuna_worker(
    worker_id: int,
    n_trials_per_worker: int,
    tensor: torch.Tensor,
    lengths: torch.Tensor,
    y_values: np.ndarray,
    symbol_ids: np.ndarray,
    idx_tuples: list[tuple],
    idx_names: list[str],
    spec_features: tuple[str, ...],
    cv_config_dict: dict[str, Any],
    device_id: int,
    seed: int,
    base_cfg_dict: dict | None,
    base_X_values: np.ndarray | None,
    base_X_index_tuples: list[tuple] | None,
    base_X_index_names: list[str] | None,
    base_X_columns: list[str] | None,
    base_y_values: np.ndarray | None,
    base_y_index_tuples: list[tuple] | None,
    base_y_index_names: list[str] | None,
    norm_mode: str,
    fixed_params: dict[str, Any],
    journal_path: str,
    progress_queue: Any | None = None,
) -> int:
    """Single Optuna worker — runs n_trials on a pinned GPU.

    Isolated process with its own CUDA context. All workers share the same
    JournalStorage file.
    """
    import optuna

    from volforecast.registry import ensure_registered

    ensure_registered()

    # Reconstruct MultiIndex from tuples (pickling-safe)
    idx = pd.MultiIndex.from_tuples(idx_tuples, names=idx_names)
    base_X_index = None
    base_y_index = None
    if base_X_index_tuples is not None:
        base_X_index = pd.MultiIndex.from_tuples(base_X_index_tuples, names=base_X_index_names)
    if base_y_index_tuples is not None:
        base_y_index = pd.MultiIndex.from_tuples(base_y_index_tuples, names=base_y_index_names)

    # Pin this worker to its GPU
    torch.cuda.set_device(device_id)

    objective = _make_lstm_objective(
        tensor=tensor,
        lengths=lengths,
        y_values=y_values,
        symbol_ids=symbol_ids,
        idx=idx,
        spec_features=spec_features,
        cv_config_dict=cv_config_dict,
        device_id=device_id,
        seed=seed,
        base_cfg_dict=base_cfg_dict,
        base_X_values=base_X_values,
        base_X_index=base_X_index,
        base_X_columns=base_X_columns,
        base_y_values=base_y_values,
        base_y_index=base_y_index,
        norm_mode=norm_mode,
        fixed_params=fixed_params,
        progress_queue=progress_queue,
    )

    # Connect to shared journal storage
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    journal_backend = optuna.storages.journal.JournalFileBackend(journal_path)
    storage = optuna.storages.JournalStorage(journal_backend)

    study = optuna.create_study(
        direction="minimize",
        study_name="lstm_qlike",
        storage=storage,
        load_if_exists=True,
        sampler=optuna.samplers.TPESampler(
            seed=seed + worker_id, n_startup_trials=8
        ),
        pruner=optuna.pruners.MedianPruner(
            n_startup_trials=8,
            n_warmup_steps=1,
        ),
    )

    study.optimize(
        objective,
        n_trials=n_trials_per_worker,
        n_jobs=1,
        catch=(Exception,),
        callbacks=[_make_trial_done_callback(progress_queue, device_id)],
    )
    return n_trials_per_worker


# ---------------------------------------------------------------------------
# Orchestrator (called from runner or tune_and_fit)
# ---------------------------------------------------------------------------


def tune_lstm_hyperparameters(
    tensor: torch.Tensor,
    lengths: torch.Tensor,
    y_values: np.ndarray,
    symbol_ids: np.ndarray,
    idx: pd.MultiIndex,
    spec_features: tuple[str, ...],
    cv_config: Any,
    n_trials: int = 40,
    n_gpus: int = 8,
    timeout: int | None = 7200,
    seed: int = 42,
    base_cfg_dict: dict | None = None,
    base_X: pd.DataFrame | None = None,
    base_y: pd.Series | None = None,
    norm_mode: str = "pooled",
    fixed_params: dict[str, Any] | None = None,
    storage_dir: Path | None = None,
    progress_queue: Any | None = None,
) -> dict[str, Any]:
    """Tune LSTM hyperparameters across multiple GPUs.

    Parameters
    ----------
    tensor : torch.Tensor
        Shared-memory sequence tensor (N, T, F).
    lengths : torch.Tensor
        Shared-memory lengths (N,).
    y_values : np.ndarray
        Target values (N,) float64.
    symbol_ids : np.ndarray
        Symbol ID array (N,) int64.
    idx : pd.MultiIndex
        Panel index (date, symbol).
    spec_features : tuple[str, ...]
        Feature names.
    cv_config : CVConfig
        Inner CV configuration.
    n_trials : int
        Total number of Optuna trials.
    n_gpus : int
        Number of GPUs to use (1 trial per GPU in parallel).
    timeout : int or None
        Maximum seconds for the entire HPO run.
    seed : int
        Base seed.
    base_cfg_dict : dict or None
        Base model config for residual learning.
    base_X : pd.DataFrame or None
        Base model features.
    base_y : pd.Series or None
        Base model targets.
    norm_mode : str
        Normalisation mode ("pooled" or "per_symbol").
    fixed_params : dict or None
        Parameters to fix (not searched), e.g. bidirectional, max_epochs.
    storage_dir : Path or None
        Directory for Optuna journal storage.
    progress_queue : mp.Queue or None
        Queue for progress events to the UI.

    Returns
    -------
    dict[str, Any]
        Best hyperparameters found.
    """
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor, as_completed

    import optuna

    if fixed_params is None:
        fixed_params = {}

    # Determine available GPUs
    available_gpus = torch.cuda.device_count() if torch.cuda.is_available() else 0
    effective_gpus = min(n_gpus, available_gpus) if available_gpus > 0 else 1
    if effective_gpus < 1:
        effective_gpus = 1
        logger.warning("No GPUs available — LSTM HPO will run on CPU (slow)")

    logger.info(
        "LSTM HPO: %d trials across %d GPUs (%.1f trials/GPU avg)",
        n_trials, effective_gpus, n_trials / effective_gpus,
    )

    # Ensure tensor/lengths are in shared memory for cross-process access
    if not tensor.is_shared():
        tensor.share_memory_()
    if not lengths.is_shared():
        lengths.share_memory_()

    # Storage setup
    if storage_dir is None:
        storage_dir = Path(tempfile.mkdtemp()) / "lstm_optuna"
    storage_dir = Path(storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    journal_path = str(storage_dir / "lstm_study.journal")

    # Serialise pandas objects for pickling
    cv_config_dict = {
        "method": cv_config.method,
        "n_splits": getattr(cv_config, "n_splits", 5),
        "purge_gap": cv_config.purge_gap,
        "train_size": cv_config.train_size,
        "test_size": cv_config.test_size,
    }

    idx_tuples = list(idx)
    idx_names = list(idx.names)

    base_X_values_np = None
    base_X_index_tuples = None
    base_X_index_names = None
    base_X_columns = None
    base_y_values_np = None
    base_y_index_tuples = None
    base_y_index_names = None

    if base_X is not None:
        base_X_values_np = base_X.values
        base_X_index_tuples = list(base_X.index)
        base_X_index_names = list(base_X.index.names)
        base_X_columns = list(base_X.columns)
    if base_y is not None:
        base_y_values_np = base_y.values
        base_y_index_tuples = list(base_y.index)
        base_y_index_names = list(base_y.index.names)

    # Check how many trials already exist in the journal (resume support)
    existing_trials = 0
    if Path(journal_path).exists():
        try:
            _jb = optuna.storages.journal.JournalFileBackend(journal_path)
            _st = optuna.storages.JournalStorage(_jb)
            _existing_study = optuna.create_study(
                direction="minimize",
                study_name="lstm_qlike",
                storage=_st,
                load_if_exists=True,
            )
            existing_trials = len(_existing_study.trials)
            if existing_trials > 0:
                logger.info(
                    "LSTM HPO: found %d existing trials in journal — need %d more to reach target %d",
                    existing_trials, max(0, n_trials - existing_trials), n_trials,
                )
        except Exception:
            pass  # Fresh start if journal is corrupt

    remaining_trials = max(0, n_trials - existing_trials)

    # Signal HPO start
    if progress_queue is not None:
        progress_queue.put({
            "type": "tuning_start",
            "n_trials": remaining_trials,
            "n_gpus": effective_gpus,
            "max_epochs": fixed_params.get("max_epochs", 80),
            "existing_trials": existing_trials,
            "target_trials": n_trials,
        })

    if remaining_trials == 0:
        logger.info("LSTM HPO: target %d trials already met (%d in journal) — skipping", n_trials, existing_trials)
    else:
        # Distribute remaining trials across workers (1 worker per GPU)
        ctx = mp.get_context("spawn")
        trials_per_worker = remaining_trials // effective_gpus
        remainder = remaining_trials % effective_gpus

        futures = {}
        with ProcessPoolExecutor(max_workers=effective_gpus, mp_context=ctx) as executor:
            for i in range(effective_gpus):
                worker_trials = trials_per_worker + (1 if i < remainder else 0)
                if worker_trials == 0:
                    continue
                device_id = i
                future = executor.submit(
                    _lstm_optuna_worker,
                    worker_id=i,
                    n_trials_per_worker=worker_trials,
                    tensor=tensor,
                    lengths=lengths,
                    y_values=y_values,
                    symbol_ids=symbol_ids,
                    idx_tuples=idx_tuples,
                    idx_names=idx_names,
                    spec_features=spec_features,
                    cv_config_dict=cv_config_dict,
                    device_id=device_id,
                    seed=seed,
                    base_cfg_dict=base_cfg_dict,
                    base_X_values=base_X_values_np,
                    base_X_index_tuples=base_X_index_tuples,
                    base_X_index_names=base_X_index_names,
                    base_X_columns=base_X_columns,
                    base_y_values=base_y_values_np,
                    base_y_index_tuples=base_y_index_tuples,
                    base_y_index_names=base_y_index_names,
                    norm_mode=norm_mode,
                    fixed_params=fixed_params,
                    journal_path=journal_path,
                    progress_queue=progress_queue,
                )
                futures[future] = i

            # Wait for all workers
            for future in as_completed(futures):
                worker_id = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error("LSTM HPO worker %d failed: %s", worker_id, e)

    # Read best params from the study
    journal_backend = optuna.storages.journal.JournalFileBackend(journal_path)
    storage = optuna.storages.JournalStorage(journal_backend)
    study = optuna.create_study(
        direction="minimize",
        study_name="lstm_qlike",
        storage=storage,
        load_if_exists=True,
    )

    completed_trials = [t for t in study.trials if t.state.name == "COMPLETE"]
    if len(completed_trials) == 0:
        logger.error(
            "LSTM HPO: no trials completed (all %d pruned/failed) — returning fixed_params",
            len(study.trials),
        )
        if progress_queue is not None:
            progress_queue.put({
                "type": "tuning_complete",
                "best_qlike": float("inf"),
                "best_trial": -1,
                "best_params": {},
                "n_completed": 0,
                "n_pruned": len(study.trials),
            })
        return fixed_params if fixed_params else {}

    best = study.best_trial
    best_params = {**best.params}
    logger.info(
        "LSTM HPO complete: best QLIKE=%.5f (trial %d) params=%s",
        best.value, best.number, best_params,
    )

    # Signal HPO complete
    if progress_queue is not None:
        progress_queue.put({
            "type": "tuning_complete",
            "best_qlike": best.value,
            "best_trial": best.number,
            "best_params": best_params,
            "n_completed": len(completed_trials),
            "n_pruned": len([t for t in study.trials if t.state.name == "PRUNED"]),
        })

    return best_params
