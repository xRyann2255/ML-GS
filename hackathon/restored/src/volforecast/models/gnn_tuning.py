"""GNN hyperparameter tuning via Optuna with multi-GPU parallel trials.

Each trial trains a GNN (GATv2 or GNNHAR) on an inner expanding-window CV
(2-3 folds) and reports the mean QLIKE. Multiple trials run simultaneously
— one per GPU — coordinated via Optuna JournalStorage.

Mirrors lstm_tuning.py architecture for consistency.
"""

from __future__ import annotations

import logging
import pickle
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

GNN_SEARCH_SPACE = {
    "hidden_dim": {"type": "int", "low": 4, "high": 64, "log": True},
    "n_heads": {"type": "categorical", "choices": [1, 2, 4]},
    "n_layers": {"type": "categorical", "choices": [1, 2]},
    "learning_rate": {"type": "float", "low": 1e-4, "high": 1e-2, "log": True},
    "dropout": {"type": "float", "low": 0.0, "high": 0.3},
    "weight_decay": {"type": "float", "low": 1e-6, "high": 1e-3, "log": True},
}

# GNNHAR doesn't use n_heads or dropout
GNNHAR_SEARCH_SPACE = {
    "hidden_dim": {"type": "int", "low": 4, "high": 64, "log": True},
    "n_layers": {"type": "categorical", "choices": [1, 2]},
    "learning_rate": {"type": "float", "low": 1e-4, "high": 1e-2, "log": True},
    "weight_decay": {"type": "float", "low": 1e-6, "high": 1e-3, "log": True},
}


def _suggest_params(trial, search_space: dict[str, dict] | None = None) -> dict[str, Any]:  # noqa: ANN001 (optuna.Trial)
    """Sample GNN hyperparameters from Optuna trial."""
    space = search_space if search_space is not None else GNN_SEARCH_SPACE
    params: dict[str, Any] = {}
    for name, spec in space.items():
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


def _make_gnn_objective(
    graphs_all: list[dict],
    dates: list,
    y_panel_values: np.ndarray,
    y_panel_index_tuples: list[tuple],
    y_panel_index_names: list[str],
    symbols: list[str],
    node_cols: list[str],
    cv_config_dict: dict[str, Any],
    device_id: int,
    seed: int,
    model_name: str,
    fixed_params: dict[str, Any],
    progress_queue: Any | None = None,
    search_space: dict[str, dict] | None = None,
):
    """Build an Optuna objective closure for GNN QLIKE tuning."""
    import optuna

    from volforecast.config import CVConfig
    from volforecast.evaluation.metrics import qlike
    from volforecast.registry import MODEL_REGISTRY
    from volforecast.utils.cv import PanelExpandingWindowCV

    cv_cfg = CVConfig(**cv_config_dict)
    n_nodes = len(symbols)

    def objective(trial: optuna.Trial) -> float:
        # Determine effective search space based on model type
        effective_space = search_space
        if effective_space is None:
            effective_space = GNNHAR_SEARCH_SPACE if model_name == "gnnhar" else GNN_SEARCH_SPACE

        sampled = _suggest_params(trial, search_space=effective_space)
        # Merge: fixed_params is base, sampled overrides
        model_kwargs = {**fixed_params, **sampled}
        model_kwargs["input_dim"] = len(node_cols)
        model_kwargs["seed"] = seed + trial.number

        if device_id >= 0 and torch.cuda.is_available():
            model_kwargs["device"] = f"cuda:{device_id}"
        else:
            model_kwargs["device"] = "cpu"

        # Build panel CV splitter for inner folds using dates
        y_panel_idx = pd.MultiIndex.from_tuples(y_panel_index_tuples, names=y_panel_index_names)
        date_index = y_panel_idx.get_level_values("date")
        X_for_cv = pd.DataFrame({"_dummy": np.zeros(len(y_panel_idx))}, index=date_index)

        effective_purge = max(cv_cfg.purge_gap, 1)
        panel_cv = PanelExpandingWindowCV(
            min_train_dates=cv_cfg.train_size or 20,
            test_dates=cv_cfg.test_size or 10,
            step_dates=cv_cfg.test_size or 10,
            purge_gap=effective_purge,
        )

        fold_splits = list(panel_cv.split(X_for_cv))
        # Limit to 3 inner folds max
        if len(fold_splits) > 3:
            indices_to_use = np.linspace(0, len(fold_splits) - 1, 3, dtype=int)
            fold_splits = [fold_splits[i] for i in indices_to_use]

        # Build date→graph index mapping
        date_to_idx = {d: i for i, d in enumerate(dates)}

        scores: list[float] = []
        for fold_idx, (train_idx_arr, test_idx_arr) in enumerate(fold_splits):
            # Get unique dates for this fold
            train_dates_fold = sorted(
                y_panel_idx[train_idx_arr].get_level_values("date").unique()
            )
            test_dates_fold = sorted(
                y_panel_idx[test_idx_arr].get_level_values("date").unique()
            )

            # Slice graphs by date
            train_graphs = [graphs_all[date_to_idx[d]] for d in train_dates_fold if d in date_to_idx]
            test_graphs = [graphs_all[date_to_idx[d]] for d in test_dates_fold if d in date_to_idx]

            if len(train_graphs) < 5 or len(test_graphs) < 2:
                raise optuna.TrialPruned()

            # Build and train model
            model_cls = MODEL_REGISTRY[model_name]
            model = model_cls(**model_kwargs)

            try:
                model.fit(train_graphs)
            except Exception as e:
                logger.warning("Trial %d fold %d failed: %s", trial.number, fold_idx, e)
                raise optuna.TrialPruned()

            # Predict and score
            preds = np.asarray(model.predict(test_graphs), dtype=np.float64)
            # Flatten test targets (T_test × N_nodes)
            test_y = np.concatenate([g["y"] for g in test_graphs]).astype(np.float64)

            finite_mask = np.isfinite(test_y) & np.isfinite(preds)
            if finite_mask.sum() < 10:
                raise optuna.TrialPruned()

            fold_qlike = qlike(test_y[finite_mask], preds[finite_mask])
            scores.append(fold_qlike)

            # Report to Optuna for pruning
            trial.report(float(np.mean(scores)), fold_idx)
            if trial.should_prune():
                raise optuna.TrialPruned()

            # Report progress
            if progress_queue is not None:
                progress_queue.put({
                    "type": "tuning_epoch",
                    "trial_num": trial.number,
                    "fold": fold_idx,
                    "n_folds": len(fold_splits),
                    "device_id": device_id,
                })

            # Free GPU memory
            del model
            torch.cuda.empty_cache()

        mean_qlike = float(np.mean(scores))
        return mean_qlike

    return objective


# ---------------------------------------------------------------------------
# Worker process (1 per GPU)
# ---------------------------------------------------------------------------


def _make_trial_done_callback(progress_queue: Any | None, device_id: int):
    """Create an Optuna callback that fires on every completed/pruned trial."""

    def callback(study, frozen_trial) -> None:  # noqa: ANN001
        if progress_queue is None:
            return
        params = frozen_trial.params
        state = frozen_trial.state.name
        qlike_val = frozen_trial.value if frozen_trial.value is not None else float("inf")
        progress_queue.put({
            "type": "tuning_trial_complete",
            "trial_num": frozen_trial.number,
            "qlike": qlike_val,
            "params": params,
            "device_id": device_id,
            "state": state,
        })

    return callback


def _gnn_optuna_worker(
    worker_id: int,
    n_trials_per_worker: int,
    graphs_pickle: bytes,
    dates_pickle: bytes,
    y_panel_values: np.ndarray,
    y_panel_index_tuples: list[tuple],
    y_panel_index_names: list[str],
    symbols: list[str],
    node_cols: list[str],
    cv_config_dict: dict[str, Any],
    device_id: int,
    seed: int,
    model_name: str,
    fixed_params: dict[str, Any],
    journal_path: str,
    progress_queue: Any | None = None,
    search_space: dict[str, dict] | None = None,
) -> int:
    """Single Optuna worker — runs n_trials on a pinned GPU."""
    import optuna

    from volforecast.registry import ensure_registered

    ensure_registered()

    # Unpickle graph data
    graphs_all = pickle.loads(graphs_pickle)  # noqa: S301
    dates = pickle.loads(dates_pickle)  # noqa: S301

    # Pin GPU
    if device_id >= 0 and torch.cuda.is_available():
        torch.cuda.set_device(device_id)

    objective = _make_gnn_objective(
        graphs_all=graphs_all,
        dates=dates,
        y_panel_values=y_panel_values,
        y_panel_index_tuples=y_panel_index_tuples,
        y_panel_index_names=y_panel_index_names,
        symbols=symbols,
        node_cols=node_cols,
        cv_config_dict=cv_config_dict,
        device_id=device_id,
        seed=seed,
        model_name=model_name,
        fixed_params=fixed_params,
        progress_queue=progress_queue,
        search_space=search_space,
    )

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    journal_backend = optuna.storages.journal.JournalFileBackend(journal_path)
    storage = optuna.storages.JournalStorage(journal_backend)

    study = optuna.create_study(
        direction="minimize",
        study_name="gnn_qlike",
        storage=storage,
        load_if_exists=True,
        sampler=optuna.samplers.TPESampler(
            seed=seed + worker_id, n_startup_trials=8,
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
# Orchestrator
# ---------------------------------------------------------------------------


def tune_gnn_hyperparameters(
    graphs_all: list[dict],
    dates: list,
    y_panel: pd.Series,
    symbols: list[str],
    node_cols: list[str],
    cv_config: Any,
    n_trials: int = 40,
    n_gpus: int = 8,
    timeout: int | None = 7200,
    seed: int = 42,
    model_name: str = "gnn",
    fixed_params: dict[str, Any] | None = None,
    storage_dir: Path | None = None,
    progress_queue: Any | None = None,
    search_space: dict[str, dict] | None = None,
) -> dict[str, Any]:
    """Tune GNN hyperparameters across multiple GPUs.

    Parameters
    ----------
    graphs_all : list[dict]
        All graph snapshots (one per date).
    dates : list
        Date list corresponding to graphs_all.
    y_panel : pd.Series
        Target values with (date, symbol) MultiIndex.
    symbols : list[str]
        Symbol list.
    node_cols : list[str]
        Node feature column names.
    cv_config : CVConfig
        Inner CV configuration.
    n_trials : int
        Total Optuna trials.
    n_gpus : int
        Number of GPUs.
    timeout : int or None
        Max seconds for HPO.
    seed : int
        Base seed.
    model_name : str
        "gnn" or "gnnhar".
    fixed_params : dict or None
        Non-tunable parameters.
    storage_dir : Path or None
        Directory for Optuna journal.
    progress_queue : Queue or None
        Progress events queue.
    search_space : dict or None
        Custom search space override.

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
        logger.warning("No GPUs available — GNN HPO will run on CPU (slow)")

    logger.info(
        "GNN HPO (%s): %d trials across %d GPUs (%.1f trials/GPU avg)",
        model_name, n_trials, effective_gpus, n_trials / effective_gpus,
    )

    # Storage setup
    if storage_dir is None:
        storage_dir = Path(tempfile.mkdtemp()) / "gnn_optuna"
    storage_dir = Path(storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    journal_path = str(storage_dir / "gnn_study.journal")

    # Serialise CV config
    cv_config_dict = {
        "method": cv_config.method,
        "n_splits": getattr(cv_config, "n_splits", 5),
        "purge_gap": cv_config.purge_gap,
        "train_size": cv_config.train_size,
        "test_size": cv_config.test_size,
    }

    # Serialise y_panel index for pickling
    y_panel_index_tuples = list(y_panel.index)
    y_panel_index_names = list(y_panel.index.names)
    y_panel_values = y_panel.values.astype(np.float64)

    # Pickle graph data (small enough: ~2800 dates × 34 nodes)
    graphs_pickle = pickle.dumps(graphs_all)
    dates_pickle = pickle.dumps(dates)

    # Check existing trials for resume
    existing_trials = 0
    if Path(journal_path).exists():
        try:
            _jb = optuna.storages.journal.JournalFileBackend(journal_path)
            _st = optuna.storages.JournalStorage(_jb)
            _existing_study = optuna.create_study(
                direction="minimize",
                study_name="gnn_qlike",
                storage=_st,
                load_if_exists=True,
            )
            existing_trials = len(_existing_study.trials)
            if existing_trials > 0:
                logger.info(
                    "GNN HPO: found %d existing trials — need %d more to reach %d",
                    existing_trials, max(0, n_trials - existing_trials), n_trials,
                )
        except Exception:
            pass

    remaining_trials = max(0, n_trials - existing_trials)

    # Signal HPO start
    if progress_queue is not None:
        progress_queue.put({
            "type": "tuning_start",
            "n_trials": remaining_trials,
            "n_gpus": effective_gpus,
            "existing_trials": existing_trials,
            "target_trials": n_trials,
            "model_name": model_name,
        })

    if remaining_trials == 0:
        logger.info("GNN HPO: target %d trials already met — skipping", n_trials)
    else:
        if effective_gpus == 1:
            # Single-worker fast path: run in-process (avoids pickling issues)
            _gnn_optuna_worker(
                worker_id=0,
                n_trials_per_worker=remaining_trials,
                graphs_pickle=graphs_pickle,
                dates_pickle=dates_pickle,
                y_panel_values=y_panel_values,
                y_panel_index_tuples=y_panel_index_tuples,
                y_panel_index_names=y_panel_index_names,
                symbols=symbols,
                node_cols=node_cols,
                cv_config_dict=cv_config_dict,
                device_id=0 if available_gpus > 0 else -1,
                seed=seed,
                model_name=model_name,
                fixed_params=fixed_params,
                journal_path=journal_path,
                progress_queue=progress_queue,
                search_space=search_space,
            )
        else:
            # Multi-worker path: spawn processes (one per GPU)
            ctx = mp.get_context("spawn")
            trials_per_worker = remaining_trials // effective_gpus
            remainder = remaining_trials % effective_gpus

            futures = {}
            with ProcessPoolExecutor(max_workers=effective_gpus, mp_context=ctx) as executor:
                for i in range(effective_gpus):
                    worker_trials = trials_per_worker + (1 if i < remainder else 0)
                    if worker_trials == 0:
                        continue
                    device_id = i if available_gpus > 0 else -1
                    future = executor.submit(
                        _gnn_optuna_worker,
                        worker_id=i,
                        n_trials_per_worker=worker_trials,
                        graphs_pickle=graphs_pickle,
                        dates_pickle=dates_pickle,
                        y_panel_values=y_panel_values,
                        y_panel_index_tuples=y_panel_index_tuples,
                        y_panel_index_names=y_panel_index_names,
                        symbols=symbols,
                        node_cols=node_cols,
                        cv_config_dict=cv_config_dict,
                        device_id=device_id,
                        seed=seed,
                        model_name=model_name,
                        fixed_params=fixed_params,
                        journal_path=journal_path,
                        progress_queue=progress_queue,
                        search_space=search_space,
                    )
                    futures[future] = i

            for future in as_completed(futures):
                worker_id = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error("GNN HPO worker %d failed: %s", worker_id, e)

    # Read best params
    journal_backend = optuna.storages.journal.JournalFileBackend(journal_path)
    storage = optuna.storages.JournalStorage(journal_backend)
    study = optuna.create_study(
        direction="minimize",
        study_name="gnn_qlike",
        storage=storage,
        load_if_exists=True,
    )

    completed_trials = [t for t in study.trials if t.state.name == "COMPLETE"]
    if len(completed_trials) == 0:
        logger.error(
            "GNN HPO: no trials completed (%d pruned/failed) — returning fixed_params",
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
        "GNN HPO complete: best QLIKE=%.5f (trial %d) params=%s",
        best.value, best.number, best_params,
    )

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
