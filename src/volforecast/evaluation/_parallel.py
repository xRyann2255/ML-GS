"""Parallel model execution for pooled tournaments.

ALL models (HAR-family and ML) run in parallel via ProcessPoolExecutor.
Progress events are communicated from worker processes to the main process
via a multiprocessing.Queue, consumed by a daemon thread that dispatches
to Rich progress callbacks.
"""

from __future__ import annotations

import logging
import multiprocessing as mp
import os
import threading
from dataclasses import dataclass
from typing import Any

import pandas as pd

from volforecast.config import (
    BaseModelConfig,
    CVConfig,
    ExperimentConfig,
    FeatureStackConfig,
    ModelConfig,
    TuningConfig,
)
from volforecast.pipeline.runner import Pipeline

logger = logging.getLogger(__name__)


@dataclass
class ProgressEvent:
    """Cross-process progress event posted to multiprocessing.Queue.

    Picklable dataclass — no closures or lambdas.
    """

    event_type: str  # "fold_complete" | "train_progress" | "model_complete" | "tuning_progress"
    model_label: str = ""
    horizon: int = 0
    fold_num: int = 0
    current_round: int = 0
    total_rounds: int = 0
    n_complete: int = 0
    n_trials: int = 0


def _consume_progress_queue(
    queue: mp.Queue,
    *,
    on_model_start: Any | None = None,
    on_fold_complete: Any | None = None,
    on_train_progress: Any | None = None,
    on_model_complete: Any | None = None,
    on_tuning_progress: Any | None = None,
) -> None:
    """Consume progress events from the queue until sentinel (None) is received.

    Dispatches each event to the appropriate callback. Designed to run in a
    daemon thread in the main process.
    """
    while True:
        try:
            event = queue.get(timeout=1.0)
        except Exception:
            continue

        if event is None:
            break

        if event.event_type == "fold_complete" and on_fold_complete is not None:
            on_fold_complete(event.model_label, event.horizon, event.fold_num)
        elif event.event_type == "train_progress" and on_train_progress is not None:
            on_train_progress(event.model_label, event.current_round, event.total_rounds)
        elif event.event_type == "model_complete" and on_model_complete is not None:
            on_model_complete(event.model_label)
        elif event.event_type == "tuning_progress" and on_tuning_progress is not None:
            on_tuning_progress(event.model_label, event.n_complete, event.n_trials)


def build_tournament_model_config(
    *,
    model_label: str,
    universe: list[str],
    date_range: tuple[str, str],
    horizons: list[int],
    feature_layers: list[str] | None,
    cv_config: CVConfig,
    tuning_config: TuningConfig | None,
    model_params: dict[str, dict] | None,
    model_configs: dict[str, dict] | None,
    horizon_overrides: dict[int, dict] | None,
    sequences: Any | None,
    base_model: BaseModelConfig | None,
    num_threads_override: int | None = None,
    n_gpus: int = 1,
    fold_cache_enabled: bool = True,
    fold_cache_dir: str | None = None,
    feature_stack: FeatureStackConfig | None = None,
    blend: Any | None = None,
) -> tuple[str, str, ExperimentConfig]:
    """Construct the synthetic ``ExperimentConfig`` a pooled tournament worker
    builds for one model.

    Returned tuple is ``(registry_name, display_label, config)``. Centralising
    this here lets the CLI (e.g. ``vol cache-status --config``) enumerate the
    exact configs the runner will fingerprint, instead of duplicating the
    construction logic and drifting.

    Mirrors the inline builder used inside ``_run_single_model_pooled`` and
    the sequential fallback in ``run_models_pooled``.
    """
    import volforecast.evaluation.tournament as _tournament

    _resolve_model = _tournament._resolve_model
    _feature_layers_for_model = _tournament._feature_layers_for_model

    registry_name, display_label, resolved_params = _resolve_model(
        model_label, model_params=model_params, model_configs=model_configs
    )

    _THREAD_AWARE_MODELS = {"lightgbm"}
    if num_threads_override is not None and registry_name in _THREAD_AWARE_MODELS:
        if "num_threads" not in resolved_params:
            resolved_params = dict(resolved_params)
            resolved_params["num_threads"] = num_threads_override
        elif resolved_params.get("num_threads", 8) > num_threads_override:
            resolved_params = dict(resolved_params)
            resolved_params["num_threads"] = num_threads_override

    # Resolve per-model feature_stack override from model_configs.
    # Only models explicitly in model_configs get feature_stack; bare labels
    # (e.g. "har", "harq") are baselines that don't use LSTM features.
    per_model_fs: FeatureStackConfig | None = None
    if model_configs and model_label in model_configs:
        entry = model_configs[model_label]
        fs_outputs_override = entry.get("feature_stack_outputs")
        if fs_outputs_override is not None and feature_stack is not None:
            if len(fs_outputs_override) == 0:
                # Empty list explicitly means "no LSTM features for this model"
                per_model_fs = None
            else:
                from dataclasses import replace as _dc_replace
                per_model_fs = _dc_replace(feature_stack, outputs=list(fs_outputs_override))
        elif feature_stack is not None and fs_outputs_override is None:
            # Model is in model_configs but doesn't override — gets full feature_stack
            per_model_fs = feature_stack

    # Strip model.params from horizon_overrides for tournament comparison
    # models that don't have their own explicit config. The horizon_overrides
    # model.params (e.g. base_model) are specific to the primary model and
    # would cause TypeError when passed to unrelated models (e.g. EWMAModel).
    effective_overrides = horizon_overrides or {}
    if effective_overrides and not (model_configs and model_label in model_configs):
        sanitized: dict[int, dict] = {}
        for h_key, h_val in effective_overrides.items():
            if "model" in h_val:
                # Keep cv and other non-model overrides; drop model.params
                stripped = {k: v for k, v in h_val.items() if k != "model"}
                if stripped:
                    sanitized[h_key] = stripped
            else:
                sanitized[h_key] = h_val
        effective_overrides = sanitized

    config = ExperimentConfig(
        name=f"tournament_pooled_{display_label}",
        universe=list(universe),
        date_range=date_range,
        horizons=horizons,
        feature_layers=feature_layers or _feature_layers_for_model(registry_name),
        model=ModelConfig(name=registry_name, params=resolved_params),
        cv=cv_config,
        tuning=tuning_config or TuningConfig(),
        training_mode="pooled",
        horizon_overrides=effective_overrides,
        sequences=sequences,
        base_model=base_model,
        n_gpus=n_gpus,
        fold_cache_enabled=fold_cache_enabled,
        fold_cache_dir=fold_cache_dir,
        feature_stack=per_model_fs,
        blend=blend,
    )
    return registry_name, display_label, config


def _run_single_model_pooled(
    model_label: str,
    panel_data: dict[str, pd.DataFrame],
    date_range: tuple[str, str],
    horizons: list[int],
    feature_layers: list[str] | None,
    cv_config: CVConfig,
    tuning_config: TuningConfig | None,
    model_params: dict[str, dict] | None,
    model_configs: dict[str, dict] | None,
    num_threads_override: int | None = None,
    horizon_overrides: dict[int, dict] | None = None,
    progress_queue: mp.Queue | None = None,
    sequences: Any | None = None,
    base_model: BaseModelConfig | None = None,
    n_gpus: int = 1,
    fold_cache_enabled: bool = True,
    fold_cache_dir: str | None = None,
    feature_stack: FeatureStackConfig | None = None,
    blend: Any | None = None,
) -> tuple[str, dict[int, pd.Series], dict[int, pd.Series]]:
    """Run a single model in pooled mode — designed for multiprocessing.

    Returns (display_label, {h: predictions_series}, {h: actuals_series}).
    This function is picklable (module-level, no closures/callbacks).
    Posts progress events to progress_queue if provided.
    """
    import volforecast.evaluation.tournament as _tournament

    _build_tournament_context = _tournament._build_tournament_context

    registry_name, display_label, config = build_tournament_model_config(
        model_label=model_label,
        universe=list(panel_data.keys()),
        date_range=date_range,
        horizons=horizons,
        feature_layers=feature_layers,
        cv_config=cv_config,
        tuning_config=tuning_config,
        model_params=model_params,
        model_configs=model_configs,
        horizon_overrides=horizon_overrides,
        sequences=sequences,
        base_model=base_model,
        num_threads_override=num_threads_override,
        n_gpus=n_gpus,
        fold_cache_enabled=fold_cache_enabled,
        fold_cache_dir=fold_cache_dir,
        feature_stack=feature_stack,
        blend=blend,
    )

    # Build context in the subprocess
    context = _build_tournament_context([registry_name], feature_layers=feature_layers)

    # Create local callbacks that post events to the queue
    on_fold_complete = None
    on_train_progress = None
    if progress_queue is not None:

        def on_fold_complete(h: int, fold_num: int) -> None:
            progress_queue.put(
                ProgressEvent(
                    event_type="fold_complete",
                    model_label=display_label,
                    horizon=h,
                    fold_num=fold_num,
                )
            )

        def on_train_progress(current_round: int, total_rounds: int) -> None:
            progress_queue.put(
                ProgressEvent(
                    event_type="train_progress",
                    model_label=display_label,
                    current_round=current_round,
                    total_rounds=total_rounds,
                )
            )

        # Wire tuning progress callback via queue (picklable in-process closure)
        if config.tuning.enabled:
            n_trials_total = config.tuning.n_trials

            def _on_trial_complete_queue(n_complete: int) -> None:
                progress_queue.put(
                    ProgressEvent(
                        event_type="tuning_progress",
                        model_label=display_label,
                        n_complete=n_complete,
                        n_trials=n_trials_total,
                    )
                )

            def _on_train_progress_queue(cur: int, total: int) -> None:
                progress_queue.put(
                    ProgressEvent(
                        event_type="train_progress",
                        model_label=display_label,
                        current_round=cur,
                        total_rounds=total,
                    )
                )

            config.tuning._on_trial_complete = _on_trial_complete_queue
            config.tuning._on_train_progress = _on_train_progress_queue

    pipeline = Pipeline(config)
    results = pipeline.run_pooled(
        panel_data,
        context=context,
        on_fold_complete=on_fold_complete,
        on_train_progress=on_train_progress,
    )

    preds: dict[int, pd.Series] = {}
    actuals: dict[int, pd.Series] = {}
    models: dict[int, Any] = {}
    for h, res in results.items():
        preds[h] = res["predictions"]
        actuals[h] = res["actuals"]
        if res.get("model") is not None:
            models[h] = res["model"]

    # Signal model completion
    if progress_queue is not None:
        progress_queue.put(ProgressEvent(event_type="model_complete", model_label=display_label))

    return display_label, preds, actuals, models


def run_models_pooled(
    models: list[str],
    ml_model_names: list[str],
    panel_data: dict[str, pd.DataFrame],
    date_range: tuple[str, str],
    horizons: list[int],
    feature_layers: list[str] | None,
    cv_config: CVConfig,
    tuning_config: TuningConfig | None,
    context: dict[str, Any] | None,
    model_params: dict[str, dict] | None,
    model_configs: dict[str, dict] | None,
    parallel_models: int,
    horizon_overrides: dict[int, dict] | None,
    on_model_start: Any | None = None,
    on_model_complete: Any | None = None,
    on_fold_complete: Any | None = None,
    on_train_progress: Any | None = None,
    on_tuning_progress: Any | None = None,
    on_batch_progress: Any | None = None,
    on_tuning_hpo: Any | None = None,
    sequences: Any | None = None,
    base_model: BaseModelConfig | None = None,
    n_gpus: int = 1,
    fold_cache_enabled: bool = True,
    fold_cache_dir: str | None = None,
    feature_stack: FeatureStackConfig | None = None,
    blend: Any | None = None,
) -> tuple[dict[str, dict[int, pd.Series]], dict[int, pd.Series]]:
    """Execute ALL models in pooled mode via ProcessPoolExecutor.

    All models (HAR-family and ML) are treated uniformly — dispatched to
    worker processes when parallel_models > 1. Progress is communicated
    via multiprocessing.Queue and consumed by a daemon thread that invokes
    the callback functions.

    Parameters
    ----------
    models : list[str]
        Model labels to execute.
    ml_model_names : list[str]
        Registry names considered CPU-heavy (used for thread budget only).
    panel_data : dict[str, DataFrame]
        Symbol -> daily data mapping.
    parallel_models : int
        Max number of parallel workers (1 = sequential, 4 = default).

    Returns
    -------
    (all_model_preds, all_actuals, trained_models, all_test_data)
        all_model_preds: {display_label: {horizon: predictions_series}}
        all_actuals: {horizon: actuals_series}
        trained_models: {display_label: {horizon: model_object}} or None
            Only populated in sequential mode; None in parallel mode.
        all_test_data: {display_label: {horizon: X_test DataFrame}} or None
            Last-fold test features; only populated in sequential mode.
    """
    import volforecast.evaluation.tournament as _tournament

    _resolve_model = _tournament._resolve_model

    all_model_preds: dict[str, dict[int, pd.Series]] = {}
    all_actuals: dict[int, pd.Series] = {}
    all_trained_models: dict[str, dict[int, Any]] | None = None
    all_test_data: dict[str, dict[int, Any]] | None = None

    if not models:
        return all_model_preds, all_actuals, all_trained_models, all_test_data

    symbols = list(panel_data.keys())
    effective_parallel = min(parallel_models, len(models))

    if effective_parallel > 1:
        # ─── Parallel execution: all models via ProcessPoolExecutor ───
        from concurrent.futures import ProcessPoolExecutor

        cpu_count = os.cpu_count() or 8
        threads_per_model = max(2, cpu_count // effective_parallel)

        logger.info(
            "Running %d models in parallel (%d workers × %d threads each, %d CPUs)",
            len(models),
            effective_parallel,
            threads_per_model,
            cpu_count,
        )

        # Notify UI of all models starting (for concurrent progress bars)
        if on_model_start is not None:
            for m in models:
                _, dl, _ = _resolve_model(m, model_params=model_params, model_configs=model_configs)
                on_model_start(dl, symbols)

        # Set up progress queue + consumer thread
        # Use Manager().Queue() — its proxy objects are picklable and can be
        # passed as arguments to spawned processes (unlike raw mp.Queue which
        # requires inheritance and can't be pickled).
        ctx = mp.get_context("spawn")
        manager = mp.Manager()
        progress_queue = manager.Queue()

        # Wrap callbacks to include model_label in on_fold_complete signature
        consumer_thread = threading.Thread(
            target=_consume_progress_queue,
            args=(progress_queue,),
            kwargs={
                "on_model_start": None,  # already called above
                "on_fold_complete": on_fold_complete,
                "on_train_progress": on_train_progress,
                "on_model_complete": on_model_complete,
                "on_tuning_progress": on_tuning_progress,
            },
            daemon=True,
        )
        consumer_thread.start()

        # Submit all models to the pool
        # Strip unpicklable callbacks from tuning_config before sending to workers
        picklable_tuning = tuning_config
        if tuning_config is not None and (
            tuning_config._on_trial_complete is not None
            or tuning_config._on_train_progress is not None
        ):
            from dataclasses import replace

            picklable_tuning = replace(
                tuning_config,
                _on_trial_complete=None,
                _on_train_progress=None,
            )

        futures_map = {}
        with ProcessPoolExecutor(max_workers=effective_parallel, mp_context=ctx) as executor:
            for model_label in models:
                future = executor.submit(
                    _run_single_model_pooled,
                    model_label=model_label,
                    panel_data=panel_data,
                    date_range=date_range,
                    horizons=horizons,
                    feature_layers=feature_layers,
                    cv_config=cv_config,
                    tuning_config=picklable_tuning,
                    model_params=model_params,
                    model_configs=model_configs,
                    num_threads_override=threads_per_model,
                    horizon_overrides=horizon_overrides,
                    progress_queue=progress_queue,
                    sequences=sequences,
                    base_model=base_model,
                    n_gpus=n_gpus,
                    fold_cache_enabled=fold_cache_enabled,
                    fold_cache_dir=fold_cache_dir,
                    feature_stack=feature_stack,
                    blend=blend,
                )
                futures_map[future] = model_label

            # Collect results as they complete
            for future in futures_map:
                display_label, preds, actuals, models = future.result()
                all_model_preds[display_label] = preds
                for h, act in actuals.items():
                    if h not in all_actuals:
                        all_actuals[h] = act
                if models:
                    if all_trained_models is None:
                        all_trained_models = {}
                    all_trained_models[display_label] = models

        # Signal consumer thread to stop
        progress_queue.put(None)
        consumer_thread.join(timeout=5.0)
        manager.shutdown()

    else:
        # ─── Sequential fallback (parallel_models=1 or single model) ───
        for model_label in models:
            registry_name, display_label, config = build_tournament_model_config(
                model_label=model_label,
                universe=symbols,
                date_range=date_range,
                horizons=horizons,
                feature_layers=feature_layers,
                cv_config=cv_config,
                tuning_config=tuning_config,
                model_params=model_params,
                model_configs=model_configs,
                horizon_overrides=horizon_overrides,
                sequences=sequences,
                base_model=base_model,
                n_gpus=n_gpus,
                fold_cache_enabled=fold_cache_enabled,
                fold_cache_dir=fold_cache_dir,
                feature_stack=feature_stack,
                blend=blend,
            )
            if on_model_start is not None:
                on_model_start(display_label, symbols)

            logger.info("Running pooled %s on %d symbols", display_label, len(panel_data))

            pipeline = Pipeline(config)
            results = pipeline.run_pooled(
                panel_data,
                context=context,
                on_fold_complete=(
                    (lambda h, fold_num: on_fold_complete(display_label, h, fold_num))
                    if on_fold_complete
                    else None
                ),
                on_train_progress=(
                    (lambda cur, total: on_train_progress(display_label, cur, total))
                    if on_train_progress
                    else None
                ),
                on_batch_progress=(
                    (
                        lambda cur_batch, total_batch, cur_epoch, total_epoch:
                            on_batch_progress(
                                display_label, cur_batch, total_batch, cur_epoch, total_epoch
                            )
                    )
                    if on_batch_progress
                    else None
                ),
                on_tuning_hpo=on_tuning_hpo,
            )

            model_horizon_preds: dict[int, pd.Series] = {}
            model_horizon_models: dict[int, Any] = {}
            model_horizon_test_data: dict[int, Any] = {}
            for h, res in results.items():
                model_horizon_preds[h] = res["predictions"]
                if h not in all_actuals:
                    all_actuals[h] = res["actuals"]
                if res.get("model") is not None:
                    model_horizon_models[h] = res["model"]
                if res.get("X_test") is not None:
                    model_horizon_test_data[h] = res["X_test"]

            all_model_preds[display_label] = model_horizon_preds
            if model_horizon_models:
                if all_trained_models is None:
                    all_trained_models = {}
                all_trained_models[display_label] = model_horizon_models
            if model_horizon_test_data:
                if all_test_data is None:
                    all_test_data = {}
                all_test_data[display_label] = model_horizon_test_data

            if on_model_complete is not None:
                on_model_complete(display_label)

    return all_model_preds, all_actuals, all_trained_models, all_test_data
