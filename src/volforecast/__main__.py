"""CLI entry point for volforecast.

Primary usage:
    vol run --config workspace/configs/tournament_multi21.yaml

Every `vol run --config` invocation uses the tournament code path and
produces an interactive Plotly HTML dashboard. Works with 1 or N models.

    mode: ingest      — Data ingestion only (early exit, no training)

Optional overrides:
    vol run --config <yaml> --symbols SPY,AAPL   # override universe
    vol run --config <yaml> --skip-ingest        # skip data fetch

Utility commands:
    vol status
    vol ingest-iv
    vol ingest-edrvol
    vol backfill-rk
    vol refresh-ohlcv
    vol audit
"""

from __future__ import annotations

import argparse
import sys
from datetime import date as _today_date


def _today_str() -> str:
    """Return today's date as YYYY-MM-DD string (used as CLI default)."""
    return _today_date.today().isoformat()


def _print_output_summary(output_dir: str, extra_files: dict[str, str] | None = None) -> None:
    """Print a clear output summary with file paths."""
    from pathlib import Path

    from volforecast.cli.console import console

    out = Path(output_dir)
    lines: list[tuple[str, str]] = []

    # Check for dashboard
    dashboard = out / "plots" / "tournament_dashboard.html"
    if dashboard.exists():
        lines.append(("Dashboard", str(dashboard.resolve())))

    # Check for metrics
    metrics_file = out / "metrics.json"
    if metrics_file.exists():
        lines.append(("Metrics", str(metrics_file.resolve())))

    # Check for predictions
    plots_dir = out / "plots"
    if plots_dir.exists():
        lines.append(("Plots dir", str(plots_dir.resolve())))

    # Extra files from caller
    if extra_files:
        for label, path in extra_files.items():
            lines.append((label, path))

    # Always show main output dir
    lines.append(("Output dir", str(out.resolve())))

    if lines:
        console.print("\n[bold cyan]━━━ Output ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")
        for label, path in lines:
            console.print(f"  [dim]{label}:[/dim]  {path}")
        console.print("[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vol",
        description=(
            "ML Realized Volatility Forecasting — Signal Discovery\n\n"
            "Primary command: vol run --config <yaml>\n"
            "Runs tournament (1 or N models) and produces an interactive dashboard."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ─── PRIMARY: vol run --config ───
    run_parser = subparsers.add_parser(
        "run",
        help="Run experiment from YAML config (tournament + dashboard)",
        description=(
            "Unified entry point. Runs all models specified in the config\n"
            "(tournament.models or inferred from model.name) and produces\n"
            "an interactive Plotly dashboard with statistical tests.\n\n"
            "  mode: ingest  — Data ingestion only (early exit)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    run_parser.add_argument(
        "--config",
        required=False,
        default=None,
        help="Path to experiment YAML config (interactive picker if omitted)",
    )
    run_parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated symbol override (replaces YAML universe)",
    )
    run_parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Skip data ingestion (use cached RV panels)",
    )
    run_parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel threads for data fetching",
    )
    run_parser.add_argument(
        "--tune",
        action="store_true",
        default=None,
        help="Enable Optuna hyperparameter tuning (nested CV)",
    )
    run_parser.add_argument(
        "--no-tune",
        action="store_true",
        default=None,
        help="Disable tuning (override YAML)",
    )
    run_parser.add_argument(
        "--n-trials",
        type=int,
        default=None,
        help="Number of Optuna trials (overrides YAML tuning.n_trials)",
    )
    run_parser.add_argument(
        "--force-retrain",
        action="store_true",
        help="Force retraining even if previous results exist with matching config/data",
    )
    run_parser.add_argument(
        "--parallel-models",
        type=int,
        default=None,
        help="Run N ML models concurrently in separate processes",
    )

    # ─── UTILITY: vol status ───
    from volforecast.cli.status import register as _reg_status

    _reg_status(subparsers)

    # ─── UTILITY: vol ingest-iv (unified: per-symbol TSDB + market-wide + Marquee) ───
    from volforecast.cli.ingest_iv import register as _reg_ingest_iv

    _reg_ingest_iv(subparsers)

    # ─── UTILITY: vol backfill-rk ───
    from volforecast.cli.backfill_rk import register as _reg_backfill_rk

    _reg_backfill_rk(subparsers)

    # ─── UTILITY: vol refresh-ohlcv ───
    from volforecast.cli.refresh_ohlcv import register as _reg_refresh_ohlcv

    _reg_refresh_ohlcv(subparsers)

    # ─── audit ───
    from volforecast.cli.audit import register as _reg_audit

    _reg_audit(subparsers)

    # ─── UTILITY: vol ingest-edrvol ───
    from volforecast.cli.ingest_edrvol import register as _reg_ingest_edrvol

    _reg_ingest_edrvol(subparsers)

    # ─── UTILITY: vol ingest-edrvs ───
    from volforecast.cli.ingest_edrvs import register as _reg_ingest_edrvs

    _reg_ingest_edrvs(subparsers)

    # ─── UTILITY: vol ingest-ohlcv ───
    from volforecast.cli.ingest_ohlcv import register as _reg_ingest_ohlcv

    _reg_ingest_ohlcv(subparsers)

    # ─── UTILITY: vol ingest-ticks ───
    from volforecast.cli.ingest_ticks import register as _reg_ingest_ticks

    _reg_ingest_ticks(subparsers)

    # ─── UTILITY: vol ingest-xasset ───
    from volforecast.cli.ingest_xasset import register as _reg_ingest_xasset

    _reg_ingest_xasset(subparsers)

    # ─── UTILITY: vol ingest-corr ───
    from volforecast.cli.ingest_corr import register as _reg_ingest_corr

    _reg_ingest_corr(subparsers)

    # ─── UTILITY: vol ingest-micro ───
    from volforecast.cli.ingest_micro import register as _reg_ingest_micro

    _reg_ingest_micro(subparsers)

    # ─── UTILITY: vol forecast ───
    from volforecast.cli.forecast import register as _reg_forecast

    _reg_forecast(subparsers)

    # ─── UTILITY: vol kvar ───
    from volforecast.cli.kvar import register as _reg_kvar

    _reg_kvar(subparsers)

    # ─── UTILITY: vol cache-status / vol cache-clear ───
    from volforecast.cli.cache import register as _reg_cache

    _reg_cache(subparsers)

    # ─── EXPERIMENT commands ───
    from volforecast.cli.experiment import register_experiment_parsers

    register_experiment_parsers(subparsers)

    return parser


def _estimate_total_folds(
    symbols: list[str],
    horizons: list[int],
    cv_cfg,
) -> int:
    """Estimate total CV folds per model for progress bar display.

    Filters out stub parquet files (fewer rows than train+test minimum),
    uses the longest qualifying symbol as the representative date count.
    """
    import pandas as pd

    from volforecast.utils.paths import rv_cache_path

    train_sz = cv_cfg.train_size or 252
    test_sz = cv_cfg.test_size or 63
    min_rows = train_sz + test_sz

    sym_lengths = (
        [
            n
            for s in symbols
            if rv_cache_path(s).exists()
            for n in [len(pd.read_parquet(rv_cache_path(s)))]
            if n >= min_rows
        ]
        if symbols
        else []
    )
    n_dates_raw = max(sym_lengths) if sym_lengths else 2500

    feature_window = 22  # monthly RV lookback
    total_folds = 0
    for h in horizons:
        n_dates = n_dates_raw - feature_window - h
        purge = max(cv_cfg.purge_gap, h)
        folds = max(0, (n_dates - train_sz - purge - test_sz) // test_sz + 1)
        total_folds += folds
    return total_folds


def _run_tournament(
    config,
    symbols_override: list[str] | None = None,
    config_path: str | None = None,
    parallel_models: int = 4,
) -> int:
    """Execute tournament mode from ExperimentConfig."""
    from pathlib import Path

    from volforecast.cli.console import setup_logging
    from volforecast.cli.progress import StageProgress
    from volforecast.evaluation.tournament import (
        display_tournament,
        run_har_tournament,
        run_har_tournament_pooled,
    )

    setup_logging()

    symbols = symbols_override or config.universe
    models = config.effective_models
    horizons = config.horizons
    date_range = config.date_range
    output_dir = Path(config.output_dir)
    mcs_bootstrap = config.tournament.mcs_bootstrap

    sym_list = symbols if symbols else ["DEV_UNIVERSE"]

    # Pre-compute total folds per model for progress display
    cv_cfg = config.cv
    total_folds_per_model = _estimate_total_folds(symbols, horizons, cv_cfg)

    with StageProgress("tournament", "har_tournament", sym_list) as sp:
        task_key = sp.add_task(total=len(models), description="models")
        import threading

        _progress_lock = threading.Lock()

        # Track per-model subtask keys for concurrent progress bars
        _model_sub_keys: dict[str, str] = {}
        _model_boost_keys: dict[str, str] = {}
        _model_tuning_keys: dict[str, str] = {}

        def _on_model_start(model_name: str, _symbols: list[str]) -> None:
            with _progress_lock:
                total = total_folds_per_model
                key = sp.add_subtask(total=total, description=model_name)
                _model_sub_keys[model_name] = key

        def _on_model_complete(model_name: str) -> None:
            with _progress_lock:
                # Remove boosting subtask for this model
                if model_name in _model_boost_keys:
                    sp.remove_subtask(_model_boost_keys.pop(model_name))
                # Remove tuning subtask for this model
                if model_name in _model_tuning_keys:
                    sp.remove_subtask(_model_tuning_keys.pop(model_name))
                # Remove generic tuning bar (shared key from _on_trial_complete)
                if "_tuning" in _model_tuning_keys:
                    sp.remove_subtask(_model_tuning_keys.pop("_tuning"))
                # Remove the model's fold progress bar
                if model_name in _model_sub_keys:
                    sp.remove_subtask(_model_sub_keys.pop(model_name))
                sp.advance(task_key)
                sp.log(f"{model_name} done")

        def _on_fold_complete(model_name: str, h: int, fold_num: int) -> None:
            with _progress_lock:
                # Remove boosting bar (fold finished → next fold starts fresh)
                if model_name in _model_boost_keys:
                    sp.remove_subtask(_model_boost_keys.pop(model_name))
                # Remove tuning bar
                if model_name in _model_tuning_keys:
                    sp.remove_subtask(_model_tuning_keys.pop(model_name))
                # Advance this model's fold bar
                if model_name in _model_sub_keys:
                    sp.advance(_model_sub_keys[model_name])

        def _on_train_progress(model_name: str, current_round: int, total_rounds: int) -> None:
            # LightGBM emits per-iteration (totals in the hundreds); LSTM emits
            # per-epoch (totals usually under 100). Throttle only when totals
            # are large so small-total runs still get every-step updates.
            if total_rounds > 100 and current_round % 50 != 0 and current_round != 1:
                return
            # Label heuristic: trees boost rounds, neural nets run epochs.
            label = "epoch" if total_rounds <= 200 else "boosting"
            with _progress_lock:
                if model_name not in _model_boost_keys:
                    _model_boost_keys[model_name] = sp.add_subtask(
                        total=total_rounds,
                        description=f"{model_name} {label}",
                        indent=2,
                    )
                sp._progress.update(
                    sp._subtasks[_model_boost_keys[model_name]], completed=current_round
                )

        def _on_trial_complete(n_complete: int) -> None:
            n_trials = config.tuning.n_trials
            with _progress_lock:
                # Use a generic tuning key (tuning is serial within a model process)
                if "_tuning" not in _model_tuning_keys:
                    _model_tuning_keys["_tuning"] = sp.add_subtask(
                        total=n_trials,
                        description="tuning",
                        indent=2,
                    )
                sp._progress.update(
                    sp._subtasks[_model_tuning_keys["_tuning"]], completed=n_complete
                )

        def _on_tuning_progress(model_name: str, n_complete: int, n_trials: int) -> None:
            """Handle tuning progress events from parallel workers via queue."""
            with _progress_lock:
                key = f"_tuning_{model_name}"
                if key not in _model_tuning_keys:
                    _model_tuning_keys[key] = sp.add_subtask(
                        total=n_trials,
                        description=f"{model_name} tuning",
                        indent=2,
                    )
                sp._progress.update(sp._subtasks[_model_tuning_keys[key]], completed=n_complete)

        # Attach tuning callbacks to config (non-serialized runtime fields)
        if config.tuning.enabled:
            config.tuning._on_trial_complete = _on_trial_complete
            # Tuning callback has old signature (current, total) — wrap to add model name
            config.tuning._on_train_progress = lambda cur, total: _on_train_progress(
                config.model.name, cur, total
            )

        tournament_fn = (
            run_har_tournament_pooled if config.training_mode == "pooled" else run_har_tournament
        )

        def _on_stats_start() -> None:
            with _progress_lock:
                # Clean up any remaining model progress bars
                for key in list(_model_boost_keys.values()):
                    sp.remove_subtask(key)
                _model_boost_keys.clear()
                for key in list(_model_sub_keys.values()):
                    sp.remove_subtask(key)
                _model_sub_keys.clear()
            sp.log("Computing tournament statistics (MCS bootstrap, DM tests)...")

        # --- Horizon-parallel stats progress callbacks ---
        _horizon_keys: dict[int, str] = {}

        def _on_horizon_start(h: int) -> None:
            with _progress_lock:
                key = sp.add_subtask(total=None, description=f"h={h} (MCS bootstrap)")
                _horizon_keys[h] = key

        def _on_horizon_complete(h: int) -> None:
            with _progress_lock:
                key = _horizon_keys.pop(h, None)
                if key is not None:
                    sp.remove_subtask(key)
            sp.log(f"   h={h} stats done")

        # --- DH straddle progress callbacks ---
        dh_task_key: str | None = None

        def _on_dh_start(n_symbols: int, n_horizons: int, n_models: int) -> None:
            nonlocal dh_task_key
            # Clean up any remaining horizon/training bars
            with _progress_lock:
                for key in list(_horizon_keys.values()):
                    sp.remove_subtask(key)
                _horizon_keys.clear()
                for key in list(_model_boost_keys.values()):
                    sp.remove_subtask(key)
                _model_boost_keys.clear()
                for key in list(_model_sub_keys.values()):
                    sp.remove_subtask(key)
                _model_sub_keys.clear()
            sp.log(
                f"Computing DH straddle P&L "
                f"({n_symbols} symbols × {n_horizons} horizons × {n_models} models)..."
            )
            dh_task_key = sp.add_subtask(total=n_symbols, description="DH straddle (symbols)")

        def _on_dh_symbol(symbol: str) -> None:
            with _progress_lock:
                if dh_task_key is not None:
                    sp.advance(dh_task_key)

        # --- LSTM HPO progress callbacks ---
        _hpo_trial_key: str | None = None
        _hpo_gpu_keys: dict[int, str] = {}
        _hpo_best_qlike: float = float("inf")
        _hpo_best_trial: int = -1
        _hpo_n_completed: int = 0
        _hpo_n_trials: int = 0

        def _on_tuning_hpo(event: dict) -> None:
            """Handle LSTM HPO progress events from worker GPUs."""
            nonlocal _hpo_trial_key, _hpo_best_qlike, _hpo_best_trial
            nonlocal _hpo_n_completed, _hpo_n_trials
            event_type = event.get("type", "")

            with _progress_lock:
                if event_type == "tuning_start":
                    _hpo_n_trials = event["n_trials"]
                    n_gpus_active = event["n_gpus"]
                    max_epochs = event.get("max_epochs", 80)
                    # Create the main trial progress bar
                    _hpo_trial_key = sp.add_subtask(
                        total=_hpo_n_trials,
                        description=f"HPO trials (×{n_gpus_active} GPUs)",
                        indent=1,
                    )
                    # Create per-GPU subtasks
                    # Tree models (max_epochs=0): show trials per GPU
                    # Sequence models (max_epochs>0): show epoch progress per GPU
                    trials_per_gpu = max(1, _hpo_n_trials // n_gpus_active)
                    for gpu_id in range(n_gpus_active):
                        if max_epochs > 0:
                            key = sp.add_subtask(
                                total=max_epochs,
                                description=f"GPU {gpu_id}: starting",
                                indent=2,
                            )
                        else:
                            key = sp.add_subtask(
                                total=trials_per_gpu,
                                description=f"GPU {gpu_id}: starting",
                                indent=2,
                            )
                        _hpo_gpu_keys[gpu_id] = key

                elif event_type == "tuning_epoch":
                    device_id = event["device_id"]
                    epoch = event["epoch"]
                    max_epochs = event["max_epochs"]
                    trial_num = event["trial_num"]
                    if device_id in _hpo_gpu_keys:
                        task_id = sp._subtasks[_hpo_gpu_keys[device_id]]
                        prefix = "    " + "  └─ "
                        sp._progress.update(
                            task_id,
                            description=f"{prefix}GPU {device_id}: trial {trial_num}",
                            completed=epoch,
                            total=max_epochs,
                        )

                elif event_type == "tuning_trial_complete":
                    _hpo_n_completed += 1
                    qlike = event["qlike"]
                    trial_num = event["trial_num"]
                    device_id = event["device_id"]
                    params = event.get("params", {})
                    state = event.get("state", "COMPLETE")

                    # Update main trial progress bar
                    if _hpo_trial_key is not None:
                        sp._progress.update(
                            sp._subtasks[_hpo_trial_key], completed=_hpo_n_completed
                        )

                    # Track best (only from completed trials, not pruned)
                    if state == "COMPLETE" and qlike < _hpo_best_qlike:
                        _hpo_best_qlike = qlike
                        _hpo_best_trial = trial_num
                        best_lr = params.get("learning_rate", 0)
                        # Model-agnostic summary: show lr + capacity param
                        capacity = params.get("hidden_dim") or params.get("max_leaves") or params.get("num_leaves", "")
                        sp.log(
                            f"HPO new best: QLIKE={qlike:.5f} "
                            f"(trial {trial_num}, capacity={capacity}, lr={best_lr:.1e})"
                        )

                    # Update per-GPU progress bar
                    if device_id in _hpo_gpu_keys:
                        task_id = sp._subtasks[_hpo_gpu_keys[device_id]]
                        prefix = "    " + "  └─ "
                        # For tree models: advance trial count on this GPU
                        # For sequence models: reset epoch bar for next trial
                        is_tree_model = "hidden_dim" not in params
                        if is_tree_model:
                            # Tree model (XGBoost/LightGBM): advance per-GPU trial counter
                            if state == "COMPLETE":
                                qlike_str = f" QLIKE={qlike:.4f}"
                            else:
                                qlike_str = " (pruned)"
                            sp._progress.advance(task_id)
                            sp._progress.update(
                                task_id,
                                description=f"{prefix}GPU {device_id}: trial {trial_num}{qlike_str}",
                            )
                        else:
                            # Sequence model (LSTM): reset epoch bar
                            sp._progress.reset(task_id)
                            sp._progress.update(
                                task_id,
                                description=f"{prefix}GPU {device_id}: waiting",
                            )

                elif event_type == "tuning_complete":
                    # Clean up HPO progress bars
                    for key in list(_hpo_gpu_keys.values()):
                        sp.remove_subtask(key)
                    _hpo_gpu_keys.clear()
                    if _hpo_trial_key is not None:
                        sp.remove_subtask(_hpo_trial_key)
                        _hpo_trial_key = None

                    n_completed = event.get("n_completed", 0)
                    n_pruned = event.get("n_pruned", 0)
                    best_qlike = event.get("best_qlike", 0)
                    best_trial = event.get("best_trial", 0)
                    best_params = event.get("best_params", {})
                    sp.log(
                        f"HPO complete: {n_completed} trials, {n_pruned} pruned. "
                        f"Best QLIKE={best_qlike:.5f} (trial {best_trial}) "
                        f"params={best_params}"
                    )

        # Attach HPO event callback now that _on_tuning_hpo is defined
        if config.tuning.enabled:
            config.tuning._on_hpo_event = _on_tuning_hpo

        results = tournament_fn(
            symbols=symbols,
            date_range=date_range,
            horizons=horizons,
            models=models,
            cv_config=cv_cfg,
            output_dir=output_dir,
            mcs_bootstrap=mcs_bootstrap,
            on_model_start=_on_model_start,
            on_model_complete=_on_model_complete,
            on_fold_complete=_on_fold_complete,
            on_stats_start=_on_stats_start,
            tuning_config=config.tuning,
            feature_layers=config.feature_layers,
            on_train_progress=_on_train_progress,
            on_dh_start=_on_dh_start,
            on_dh_symbol=_on_dh_symbol,
            config_path=config_path,
            model_params={config.model.name: config.model.params} if config.model.params else None,
            model_configs=config.tournament.model_configs or None,
            parallel_models=parallel_models,
            horizon_overrides=config.horizon_overrides or None,
            dh_mode=config.tournament.dh_mode,
            dh_enabled=config.tournament.dh_enabled,
            vt_enabled=config.tournament.vt_enabled,
            gsvivs_enabled=config.tournament.gsvivs_enabled,
            gsvivs_short_threshold=config.tournament.gsvivs_short_threshold,
            gsvivs_default_long=config.tournament.gsvivs_default_long,
            gsvivs_signal_type=config.tournament.gsvivs_signal_type,
            gsvivs_flat_percentile=config.tournament.gsvivs_flat_percentile,
            gsvivs_iv_source=config.tournament.gsvivs_iv_source,
            gsvivs_iv_sources=config.tournament.gsvivs_iv_sources,
            gsvivs_signal_space=config.tournament.gsvivs_signal_space,
            gsvivs_sizings=config.tournament.gsvivs_sizings,
            on_horizon_start=_on_horizon_start,
            on_horizon_complete=_on_horizon_complete,
            on_tuning_progress=_on_tuning_progress,
            on_tuning_hpo=_on_tuning_hpo,
            sequences=config.sequences,
            base_model=config.base_model,
            n_gpus=config.n_gpus,
            fold_cache_enabled=config.fold_cache_enabled,
            fold_cache_dir=config.fold_cache_dir,
            feature_stack=config.feature_stack,
            blend=config.blend,
        )

        if dh_task_key is not None:
            sp.remove_subtask(dh_task_key)
        # Clean up any remaining model progress bars
        with _progress_lock:
            for key in list(_model_boost_keys.values()):
                sp.remove_subtask(key)
            _model_boost_keys.clear()
            for key in list(_model_tuning_keys.values()):
                sp.remove_subtask(key)
            _model_tuning_keys.clear()
            for key in list(_model_sub_keys.values()):
                sp.remove_subtask(key)
            _model_sub_keys.clear()

    display_tournament(results)
    _print_output_summary(str(output_dir))

    # Auto-update trial registry if a matching NOT_STARTED trial exists
    if config_path:
        from volforecast.cli.experiment import update_trial_from_metrics

        metrics_path = output_dir / "metrics.json"
        config_basename = Path(config_path).name
        update_trial_from_metrics(config_basename, metrics_path)

    return 0


def _run_ingest(config, symbols_override: list[str] | None = None, workers: int = 4) -> int:
    """Execute ingest-only mode."""
    from volforecast.cli.console import setup_logging
    from volforecast.cli.ingest import run as ingest_run
    from volforecast.cli.progress import ExperimentProgress

    setup_logging()
    symbols = symbols_override
    universe = symbols or config.universe

    with ExperimentProgress(config.name, universe, ["INGEST"]) as pp:
        pp.start_stage("INGEST")
        try:
            ingest_run(config, symbols, progress=pp, max_workers=workers)
        except ConnectionError as e:
            pp.fail_stage("INGEST")
            pp.log("INGEST", f"ERROR: {e}")
            return 1
        pp.finish_stage("INGEST")

    _print_output_summary(str(config.output_dir))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    # ─── PRIMARY: vol run --config ───
    if args.command == "run":
        if args.config is None:
            from volforecast.cli.config_picker import pick_config

            selected = pick_config()
            if selected is None:
                return 0
            args.config = str(selected)

        from volforecast.config import ExperimentConfig

        config = ExperimentConfig.from_yaml(args.config)
        symbols = args.symbols.split(",") if args.symbols else None
        workers = args.workers or config.ingest.workers

        # Apply tuning CLI overrides
        if getattr(args, "tune", None):
            config.tuning.enabled = True
        if getattr(args, "no_tune", None):
            config.tuning.enabled = False
        if getattr(args, "n_trials", None) is not None:
            config.tuning.n_trials = args.n_trials

        # Ingest-only early exit
        if config.mode == "ingest":
            return _run_ingest(config, symbols_override=symbols, workers=workers)

        # Ingest gate: run ingest for missing symbols unless --skip-ingest
        if not args.skip_ingest:
            from volforecast.utils.paths import rv_cache_path

            universe = symbols or config.universe
            missing = [s for s in universe if not rv_cache_path(s).exists()]
            if missing:
                from volforecast.cli.ingest import run as ingest_run
                from volforecast.cli.progress import ExperimentProgress

                with ExperimentProgress(config.name, missing, ["INGEST"]) as pp:
                    pp.start_stage("INGEST")
                    try:
                        ingest_run(config, missing, progress=pp, max_workers=workers)
                    except ConnectionError as e:
                        pp.fail_stage("INGEST")
                        pp.log("INGEST", f"ERROR: {e}")
                        return 1
                    pp.finish_stage("INGEST")

        # All modes route through tournament
        parallel = getattr(args, "parallel_models", None) or config.tournament.parallel_models
        return _run_tournament(
            config,
            symbols_override=symbols,
            config_path=args.config,
            parallel_models=parallel,
        )

    # ─── All other commands dispatch via args.func ───
    elif hasattr(args, "func"):
        return args.func(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
