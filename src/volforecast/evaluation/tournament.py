"""Tournament runner: multi-model HAR baseline comparison.

Runs all HAR-family models across the dev universe with expanding-window CV,
collects OOS predictions, and produces a QLIKE tournament table per horizon.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from volforecast.config import (
    BaseModelConfig,
    CVConfig,
    ExperimentConfig,
    ModelConfig,
    TuningConfig,
)
from volforecast.constants import DEV_UNIVERSE
from volforecast.data.cross_asset_ingest import load_cross_asset_context
from volforecast.data.edrvol import load_edrvs_cache, load_iv_cache
from volforecast.evaluation.economic_value import iv_tenor_for_horizon
from volforecast.evaluation.statistical_tests import tournament_table
from volforecast.evaluation.tournament_economics import enrich_tournament_economics
from volforecast.pipeline.runner import Pipeline
from volforecast.utils.paths import rv_cache_path
from volforecast.utils.persistence import save_experiment_results

_iv_context_cache: dict[str, Any] | None = None


def _clear_iv_context_cache() -> None:
    """Clear the module-level IV context cache (useful for testing)."""
    global _iv_context_cache
    _iv_context_cache = None


logger = logging.getLogger(__name__)


def _default_gsvivs_dashboard_iv_label(
    stats_by_iv: dict[str, dict[int, list[dict]]],
) -> str | None:
    """Select default IV label. Delegates to evaluation.gsvivs."""
    from volforecast.evaluation.gsvivs import default_gsvivs_dashboard_iv_label

    return default_gsvivs_dashboard_iv_label(stats_by_iv)


# Model constants and utilities — canonical source is _model_utils
from volforecast.evaluation._model_utils import (  # noqa: E402
    ALL_MODELS,
    HAR_MODELS,
    ML_MODELS,
    NAIVE_MODELS,
    feature_layers_for_model as _feature_layers_for_model,
    resolve_model as _resolve_model,
)


def _build_tournament_context(
    models: list[str], feature_layers: list[str] | None = None
) -> dict[str, Any] | None:
    """Build context dict for layers that need external data.

    Handles two sources:
    1. Legacy options context (iv_features_spx.parquet) — only when 'options'
       is in layers but 'iv_surface' is NOT (backward compat).
    2. Cross-asset context (rates, fx, commodity, credit, vix parquets) —
       when 'cross_asset' is in feature_layers.

    Returns None if no external data is needed.
    """
    global _iv_context_cache

    needs_cross_asset = feature_layers is not None and "cross_asset" in feature_layers

    # New IV path: IVSurfaceLayer handles IV loading directly — no context needed
    needs_legacy_options = False
    if feature_layers is not None and "iv_surface" not in feature_layers:
        needs_legacy_options = "options" in feature_layers
    elif feature_layers is None:
        needs_legacy_options = any("options" in _feature_layers_for_model(m) for m in models)

    if not needs_legacy_options and not needs_cross_asset:
        return None

    context: dict[str, Any] = {}

    # Load cross-asset data
    if needs_cross_asset:
        try:
            xasset_ctx = load_cross_asset_context()
            context.update(xasset_ctx)
        except FileNotFoundError:
            logger.warning(
                "cross_asset layer requested but no data found. "
                "Run `vol ingest-xasset` to fetch cross-asset data."
            )

    # Load legacy options context
    if needs_legacy_options:
        if _iv_context_cache is not None:
            context.update(_iv_context_cache)
        else:
            from volforecast.data.iv_features import load_iv_features

            iv_features = load_iv_features()
            if iv_features is None:
                logger.warning(
                    "Options layer requested but IV feature cache not found. "
                    "Models requiring options will get no IV features. "
                    "Run `vol ingest-iv` or `vol ingest-edrvol` to generate the cache."
                )
            else:
                _iv_context_cache = {"iv_surface": iv_features}
                context.update(_iv_context_cache)

    return context if context else None


def _generate_dashboard(
    tournament_results: dict[int, pd.DataFrame],
    all_actuals_series: dict[tuple[str, int], pd.Series],
    all_preds_series: dict[tuple[str, str, int], pd.Series],
    symbols: list[str],
    models: list[str],
    horizons: list[int],
    output_dir: Path,
    **kwargs,
) -> None:
    """Generate the tournament dashboard. Delegates to tournament_dashboard module."""
    from volforecast.evaluation.tournament_dashboard import generate_dashboard

    generate_dashboard(
        tournament_results=tournament_results,
        all_actuals_series=all_actuals_series,
        all_preds_series=all_preds_series,
        symbols=symbols,
        models=models,
        horizons=horizons,
        output_dir=output_dir,
        **kwargs,
    )


def run_har_tournament(
    symbols: list[str] | None = None,
    date_range: tuple[str, str] = ("2014-01-02", "2024-12-31"),
    horizons: list[int] | None = None,
    models: list[str] | None = None,
    cv_config: CVConfig | None = None,
    output_dir: Path | None = None,
    mcs_bootstrap: int = 10_000,
    on_model_start: Any | None = None,
    on_model_complete: Any | None = None,
    on_fold_complete: Any | None = None,
    on_stats_start: Any | None = None,
    training_mode: str = "per_symbol",
    tuning_config: TuningConfig | None = None,
    feature_layers: list[str] | None = None,
    on_train_progress: Any | None = None,
    on_dh_start: Any | None = None,
    on_dh_symbol: Any | None = None,
    on_dh_model: Any | None = None,
    config_path: str | None = None,
    model_params: dict[str, dict] | None = None,
    model_configs: dict[str, dict] | None = None,
    parallel_models: int = 1,
    horizon_overrides: dict[int, dict] | None = None,
    dh_mode: str = "realistic",
    dh_enabled: bool = True,
    vt_enabled: bool = True,
    gsvivs_enabled: bool = False,
    gsvivs_short_threshold: float = 0.0,
    gsvivs_default_long: bool = False,
    gsvivs_signal_type: str = "iv_rv_gap",
    gsvivs_flat_percentile: int = 80,
    gsvivs_iv_source: str = "edrvs",
    gsvivs_iv_sources: list[str] | None = None,
    gsvivs_signal_space: str = "variance",
    gsvivs_sizings: Any | None = None,
    on_horizon_start: Any | None = None,
    on_horizon_complete: Any | None = None,
    on_tuning_progress: Any | None = None,
    on_batch_progress: Any | None = None,
    on_tuning_hpo: Any | None = None,
    sequences: Any | None = None,
    base_model: BaseModelConfig | None = None,
    n_gpus: int = 1,
    fold_cache_enabled: bool = True,
    fold_cache_dir: str | None = None,
    feature_stack: Any | None = None,
    blend: Any | None = None,
) -> dict[int, pd.DataFrame]:
    """Run HAR-family tournament and return tables per horizon.

    Parameters
    ----------
    symbols : list[str], optional
        Symbols to evaluate. Defaults to DEV_UNIVERSE.
    date_range : tuple[str, str]
        Start and end date for data.
    horizons : list[int], optional
        Forecast horizons. Defaults to [1, 5, 22].
    models : list[str], optional
        Model names. Defaults to ALL_MODELS.
    cv_config : CVConfig, optional
        CV settings. Defaults to expanding_window with purge_gap=5.
    output_dir : Path, optional
        If set, saves experiment artifacts.
    mcs_bootstrap : int
        Number of bootstrap replicates for MCS.
    training_mode : str
        "per_symbol" (default) fits per symbol and concatenates.
        "pooled" stacks all symbols and fits a single model.

    Returns
    -------
    dict[int, pd.DataFrame]
        Keys are horizons. Values are tournament DataFrames.
    """
    if training_mode == "pooled":
        return _run_tournament_pooled(
            symbols=symbols,
            date_range=date_range,
            horizons=horizons,
            models=models,
            cv_config=cv_config,
            output_dir=output_dir,
            mcs_bootstrap=mcs_bootstrap,
            on_model_start=on_model_start,
            on_model_complete=on_model_complete,
            on_fold_complete=on_fold_complete,
            on_stats_start=on_stats_start,
            tuning_config=tuning_config,
            feature_layers=feature_layers,
            on_train_progress=on_train_progress,
            on_dh_start=on_dh_start,
            on_dh_symbol=on_dh_symbol,
            on_dh_model=on_dh_model,
            config_path=config_path,
            model_params=model_params,
            model_configs=model_configs,
            parallel_models=parallel_models,
            horizon_overrides=horizon_overrides,
            dh_mode=dh_mode,
            dh_enabled=dh_enabled,
            vt_enabled=vt_enabled,
            gsvivs_enabled=gsvivs_enabled,
            gsvivs_short_threshold=gsvivs_short_threshold,
            gsvivs_default_long=gsvivs_default_long,
            gsvivs_signal_type=gsvivs_signal_type,
            gsvivs_flat_percentile=gsvivs_flat_percentile,
            gsvivs_iv_source=gsvivs_iv_source,
            gsvivs_iv_sources=gsvivs_iv_sources,
            gsvivs_signal_space=gsvivs_signal_space,
            gsvivs_sizings=gsvivs_sizings,
            on_horizon_start=on_horizon_start,
            on_horizon_complete=on_horizon_complete,
            on_tuning_progress=on_tuning_progress,
            on_batch_progress=on_batch_progress,
            on_tuning_hpo=on_tuning_hpo,
            sequences=sequences,
            base_model=base_model,
            n_gpus=n_gpus,
            fold_cache_enabled=fold_cache_enabled,
            fold_cache_dir=fold_cache_dir,
            feature_stack=feature_stack,
            blend=blend,
        )
    return _run_tournament_per_symbol(
        symbols=symbols,
        date_range=date_range,
        horizons=horizons,
        models=models,
        cv_config=cv_config,
        output_dir=output_dir,
        mcs_bootstrap=mcs_bootstrap,
        on_model_start=on_model_start,
        on_model_complete=on_model_complete,
        on_fold_complete=on_fold_complete,
        tuning_config=tuning_config,
        feature_layers=feature_layers,
        on_train_progress=on_train_progress,
        on_dh_start=on_dh_start,
        on_dh_symbol=on_dh_symbol,
        on_dh_model=on_dh_model,
        config_path=config_path,
        model_params=model_params,
        model_configs=model_configs,
        horizon_overrides=horizon_overrides,
        dh_mode=dh_mode,
        dh_enabled=dh_enabled,
        vt_enabled=vt_enabled,
        gsvivs_enabled=gsvivs_enabled,
        gsvivs_short_threshold=gsvivs_short_threshold,
        gsvivs_default_long=gsvivs_default_long,
        gsvivs_signal_type=gsvivs_signal_type,
        gsvivs_flat_percentile=gsvivs_flat_percentile,
        gsvivs_iv_source=gsvivs_iv_source,
        gsvivs_iv_sources=gsvivs_iv_sources,
        gsvivs_signal_space=gsvivs_signal_space,
        gsvivs_sizings=gsvivs_sizings,
    )


# Keep old name as an alias for backward compatibility
def run_har_tournament_pooled(**kwargs) -> dict[int, pd.DataFrame]:
    """Alias for run_har_tournament with training_mode='pooled'."""
    return run_har_tournament(**kwargs, training_mode="pooled")


# _resolve_model is now imported from _model_utils above


def _run_tournament_per_symbol(
    symbols: list[str] | None = None,
    date_range: tuple[str, str] = ("2014-01-02", "2024-12-31"),
    horizons: list[int] | None = None,
    models: list[str] | None = None,
    cv_config: CVConfig | None = None,
    output_dir: Path | None = None,
    mcs_bootstrap: int = 10_000,
    on_model_start: Any | None = None,
    on_model_complete: Any | None = None,
    on_fold_complete: Any | None = None,
    tuning_config: TuningConfig | None = None,
    feature_layers: list[str] | None = None,
    on_train_progress: Any | None = None,
    on_dh_start: Any | None = None,
    on_dh_symbol: Any | None = None,
    on_dh_model: Any | None = None,
    config_path: str | None = None,
    model_params: dict[str, dict] | None = None,
    model_configs: dict[str, dict] | None = None,
    horizon_overrides: dict[int, dict] | None = None,
    dh_mode: str = "realistic",
    dh_enabled: bool = True,
    vt_enabled: bool = True,
    gsvivs_enabled: bool = False,
    gsvivs_short_threshold: float = 0.0,
    gsvivs_default_long: bool = False,
    gsvivs_signal_type: str = "iv_rv_gap",
    gsvivs_flat_percentile: int = 80,
    gsvivs_iv_source: str = "edrvs",
    gsvivs_iv_sources: list[str] | None = None,
    gsvivs_signal_space: str = "variance",
    gsvivs_sizings: Any | None = None,
) -> dict[int, pd.DataFrame]:
    """Per-symbol tournament implementation."""
    symbols = sorted(symbols or DEV_UNIVERSE)
    horizons = horizons or [1, 5, 22]
    models = models or ALL_MODELS
    cv_config = cv_config or CVConfig(
        method="expanding_window",
        purge_gap=5,
        train_size=504,
        test_size=63,
    )

    all_preds: dict[tuple[str, str, int], np.ndarray] = {}
    all_preds_series: dict[tuple[str, str, int], pd.Series] = {}
    all_actuals: dict[tuple[str, int], np.ndarray] = {}
    all_actuals_series: dict[tuple[str, int], pd.Series] = {}

    # Resolve registry names for context building (labels may be aliases)
    registry_names = [
        _resolve_model(m, model_params=model_params, model_configs=model_configs)[0] for m in models
    ]

    # Build context for layers that need external data (e.g. options/VIX)
    context = _build_tournament_context(registry_names, feature_layers=feature_layers)

    # Hoist data reads: load each symbol's parquet once, reuse across models
    symbol_data: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        data_path = rv_cache_path(symbol)
        if not data_path.exists():
            logger.warning("No data for %s at %s, skipping", symbol, data_path)
            continue
        symbol_data[symbol] = pd.read_parquet(data_path)

    for model_label in models:
        registry_name, display_label, resolved_params = _resolve_model(
            model_label, model_params=model_params, model_configs=model_configs
        )
        if on_model_start is not None:
            on_model_start(display_label, symbols)

        for symbol in symbols:
            if symbol not in symbol_data:
                continue
            logger.info("Running %s on %s", display_label, symbol)

            daily_data = symbol_data[symbol]

            config = ExperimentConfig(
                name=f"tournament_{display_label}_{symbol}",
                universe=[symbol],
                date_range=date_range,
                horizons=horizons,
                feature_layers=feature_layers or _feature_layers_for_model(registry_name),
                model=ModelConfig(name=registry_name, params=resolved_params),
                cv=cv_config,
                tuning=tuning_config or TuningConfig(),
                horizon_overrides=horizon_overrides or {},
            )

            pipeline = Pipeline(config)
            sym_context = dict(context) if context else {}
            sym_context["symbol"] = symbol
            results = pipeline.run(
                daily_data,
                context=sym_context,
                on_fold_complete=on_fold_complete,
            )

            for h, res in results.items():
                preds = res["predictions"]
                all_preds[(display_label, symbol, h)] = preds.values
                all_preds_series[(display_label, symbol, h)] = preds
                # Store actuals only once per (symbol, h)
                if (symbol, h) not in all_actuals:
                    # Actuals = log(avg RV over next h days), Corsi spec
                    actuals_aligned = res["actuals"]
                    all_actuals[(symbol, h)] = actuals_aligned.values
                    all_actuals_series[(symbol, h)] = actuals_aligned

            if output_dir:
                save_experiment_results(results, config, symbol)

        if on_model_complete is not None:
            on_model_complete(display_label)

    # Build tournament tables per horizon
    tournament_results: dict[int, pd.DataFrame] = {}
    for h in horizons:
        # Use pandas Series to align predictions to a common index per symbol,
        # then concatenate. Different models may produce different OOS counts
        # (due to varying feature NaN requirements), so we intersect indices.
        available_models = [
            m for m in models if any((m, s, h) in all_preds_series for s in symbols)
        ]
        if len(available_models) < 1:
            logger.warning("No models have predictions for h=%d", h)
            continue

        # Per-symbol: find common index across all models that ran
        aligned_preds: dict[str, list[np.ndarray]] = {m: [] for m in available_models}
        aligned_actuals: list[np.ndarray] = []
        aligned_returns: list[np.ndarray] = []
        aligned_iv: list[np.ndarray] = []
        aligned_spot: list[np.ndarray] = []

        for s in symbols:
            # Collect Series for each model on this symbol/horizon
            sym_series = {
                m: all_preds_series[(m, s, h)]
                for m in available_models
                if (m, s, h) in all_preds_series
            }
            if len(sym_series) < len(available_models):
                continue  # skip symbol if not all models produced output

            # Intersect indices across all models
            common_idx = sym_series[available_models[0]].index
            for m in available_models[1:]:
                common_idx = common_idx.intersection(sym_series[m].index)

            if len(common_idx) == 0:
                continue

            # Also intersect with actuals
            if (s, h) not in all_actuals_series:
                continue
            actuals_s = all_actuals_series[(s, h)]
            common_idx = common_idx.intersection(actuals_s.index)

            if len(common_idx) == 0:
                continue

            common_idx = common_idx.sort_values()
            aligned_actuals.append(actuals_s.loc[common_idx].values)
            for m in available_models:
                aligned_preds[m].append(sym_series[m].loc[common_idx].values)

            # Collect daily forward returns for vol-targeting (from close prices).
            # At prediction date T, the forecast is for vol(T+1), so the position
            # earns the return from T to T+1: close[T+1]/close[T] - 1.
            if s in symbol_data and "close" in symbol_data[s].columns:
                close = symbol_data[s]["close"]
                forward_ret = close.shift(-1) / close - 1.0
                ret_aligned = forward_ret.reindex(common_idx)
                aligned_returns.append(ret_aligned.values)

            # Collect IV and spot for delta-hedged straddle metrics
            if s in symbol_data and "close" in symbol_data[s].columns:
                spot_aligned = symbol_data[s]["close"].reindex(common_idx)
                aligned_spot.append(spot_aligned.values)

                # Load per-symbol IV from cache (shift(1) for causality)
                # Select IV tenor based on forecast horizon
                iv_data = load_iv_cache(s)
                # Use per-symbol 0DTE IV for h=1
                # iv_0dte is decimal; convert to vol points for / 100.0 downstream
                if iv_data is not None and "iv_0dte" in iv_data.columns:
                    iv_data = iv_data.copy()
                    iv_data["iv_0dte_atm"] = iv_data["iv_0dte"] * 100.0
                # Load EDRVS var-swap strike for h=1 signal
                if iv_data is not None:
                    edrvs_vs = load_edrvs_cache()
                    if edrvs_vs is not None and not edrvs_vs.empty:
                        if not hasattr(iv_data, "_is_copy"):
                            iv_data = iv_data.copy()
                        edrvs_vs.index = pd.DatetimeIndex(
                            edrvs_vs.index.normalize(), dtype="datetime64[ns]"
                        )
                        iv_data["iv_vs_0dte"] = edrvs_vs.reindex(iv_data.index)
                iv_col, _ = iv_tenor_for_horizon(h)
                if iv_data is not None and iv_col in iv_data.columns:
                    iv_series = iv_data[iv_col].reindex(common_idx).shift(1)
                    # Convert from vol points (e.g. 18.0) to decimal (0.18)
                    aligned_iv.append((iv_series / 100.0).values)
                elif iv_data is not None and "iv_1m_atm" in iv_data.columns:
                    # Fallback to 1m if preferred tenor not available
                    iv_series = iv_data["iv_1m_atm"].reindex(common_idx).shift(1)
                    aligned_iv.append((iv_series / 100.0).values)
                else:
                    aligned_iv.append(np.full(len(common_idx), np.nan))

        if not aligned_actuals:
            logger.warning("No actuals for h=%d, skipping", h)
            continue

        y_all = np.concatenate(aligned_actuals)
        model_preds: dict[str, np.ndarray] = {}
        for m in available_models:
            if aligned_preds[m]:
                model_preds[m] = np.concatenate(aligned_preds[m])

        if len(model_preds) < 1:
            logger.warning("No models have predictions for h=%d", h)
            continue

        # Pass per-symbol returns for vol-targeting metrics
        sym_returns: list[np.ndarray] | None = None
        if aligned_returns and len(aligned_returns) == len(aligned_actuals):
            sym_returns = aligned_returns

        # Pass IV and spot for delta-hedged straddle metrics
        iv_all = None
        spot_all = None
        if aligned_iv and len(aligned_iv) == len(aligned_actuals):
            iv_all = np.concatenate(aligned_iv)
        if aligned_spot and len(aligned_spot) == len(aligned_actuals):
            spot_all = np.concatenate(aligned_spot)

        stats = tournament_table(
            model_preds,
            y_all,
            baseline="har",
            horizon=h,
            mcs_bootstrap=mcs_bootstrap,
        )
        table = enrich_tournament_economics(
            stats,
            model_preds,
            y_all,
            daily_returns=(np.concatenate(sym_returns) if (sym_returns and vt_enabled) else None),
            symbol_lengths=(
                [len(a) for a in sym_returns] if (sym_returns and vt_enabled) else None
            ),
            implied_vol=(iv_all if dh_enabled else None),
            spot_prices=(spot_all if dh_enabled else None),
            dh_mode=dh_mode,
            horizon=h,
        )
        tournament_results[h] = table
        logger.info("h=%d tournament complete: %d models (%d obs)", h, len(table), len(y_all))

    # Auto-generate interactive dashboard
    if output_dir:
        _generate_dashboard(
            tournament_results=tournament_results,
            all_actuals_series=all_actuals_series,
            all_preds_series=all_preds_series,
            symbols=symbols,
            models=models,
            horizons=horizons,
            output_dir=output_dir,
            symbol_data=symbol_data,
            config_path=config_path,
            on_dh_start=on_dh_start,
            on_dh_symbol=on_dh_symbol,
            on_dh_model=on_dh_model,
            dh_mode=dh_mode,
            dh_enabled=dh_enabled,
            gsvivs_enabled=gsvivs_enabled,
            gsvivs_short_threshold=gsvivs_short_threshold,
            gsvivs_default_long=gsvivs_default_long,
            gsvivs_signal_type=gsvivs_signal_type,
            gsvivs_flat_percentile=gsvivs_flat_percentile,
            gsvivs_iv_source=gsvivs_iv_source,
            gsvivs_iv_sources=gsvivs_iv_sources,
            gsvivs_signal_space=gsvivs_signal_space,
            gsvivs_sizings=gsvivs_sizings,
        )

        # Persist structured metrics.json alongside the dashboard
        _save_pooled_metrics(tournament_results, output_dir)

    return tournament_results


def _run_tournament_pooled(
    symbols: list[str] | None = None,
    date_range: tuple[str, str] = ("2014-01-02", "2024-12-31"),
    horizons: list[int] | None = None,
    models: list[str] | None = None,
    cv_config: CVConfig | None = None,
    output_dir: Path | None = None,
    mcs_bootstrap: int = 10_000,
    on_model_start: Any | None = None,
    on_model_complete: Any | None = None,
    on_fold_complete: Any | None = None,
    on_stats_start: Any | None = None,
    tuning_config: TuningConfig | None = None,
    feature_layers: list[str] | None = None,
    on_train_progress: Any | None = None,
    on_dh_start: Any | None = None,
    on_dh_symbol: Any | None = None,
    on_dh_model: Any | None = None,
    config_path: str | None = None,
    model_params: dict[str, dict] | None = None,
    model_configs: dict[str, dict] | None = None,
    parallel_models: int = 1,
    horizon_overrides: dict[int, dict] | None = None,
    dh_mode: str = "realistic",
    dh_enabled: bool = True,
    vt_enabled: bool = True,
    gsvivs_enabled: bool = False,
    gsvivs_short_threshold: float = 0.0,
    gsvivs_default_long: bool = False,
    gsvivs_signal_type: str = "iv_rv_gap",
    gsvivs_flat_percentile: int = 80,
    gsvivs_iv_source: str = "edrvs",
    gsvivs_iv_sources: list[str] | None = None,
    gsvivs_signal_space: str = "variance",
    gsvivs_sizings: Any | None = None,
    on_horizon_start: Any | None = None,
    on_horizon_complete: Any | None = None,
    on_tuning_progress: Any | None = None,
    on_batch_progress: Any | None = None,
    on_tuning_hpo: Any | None = None,
    sequences: Any | None = None,
    base_model: BaseModelConfig | None = None,
    n_gpus: int = 1,
    fold_cache_enabled: bool = True,
    fold_cache_dir: str | None = None,
    feature_stack: Any | None = None,
    blend: Any | None = None,
) -> dict[int, pd.DataFrame]:
    """Pooled tournament implementation."""
    symbols = sorted(symbols or DEV_UNIVERSE)
    horizons = horizons or [1, 5, 22]
    models = models or ALL_MODELS
    cv_config = cv_config or CVConfig(
        method="expanding_window",
        purge_gap=5,
        train_size=504,
        test_size=63,
    )

    # Load all symbol data upfront
    panel_data: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        data_path = rv_cache_path(symbol)
        if not data_path.exists():
            logger.warning("No data for %s at %s, skipping", symbol, data_path)
            continue
        panel_data[symbol] = pd.read_parquet(data_path)

    if len(panel_data) < 2:
        raise ValueError(
            f"Pooled training requires at least 2 symbols with data. "
            f"Found: {list(panel_data.keys())}"
        )

    # Resolve registry names for context building (labels may be aliases)
    registry_names = [
        _resolve_model(m, model_params=model_params, model_configs=model_configs)[0] for m in models
    ]

    # Build context for layers that need external data (e.g. options/VIX)
    context = _build_tournament_context(registry_names, feature_layers=feature_layers)

    # Run all models (sequential HAR + parallel ML) via _parallel module
    from volforecast.evaluation._parallel import run_models_pooled

    all_model_preds, all_actuals, trained_models, all_test_data = run_models_pooled(
        models=models,
        ml_model_names=ML_MODELS,
        panel_data=panel_data,
        date_range=date_range,
        horizons=horizons,
        feature_layers=feature_layers,
        cv_config=cv_config,
        tuning_config=tuning_config,
        context=context,
        model_params=model_params,
        model_configs=model_configs,
        parallel_models=parallel_models,
        horizon_overrides=horizon_overrides,
        on_model_start=on_model_start,
        on_model_complete=on_model_complete,
        on_fold_complete=on_fold_complete,
        on_train_progress=on_train_progress,
        on_tuning_progress=on_tuning_progress,
        on_batch_progress=on_batch_progress,
        on_tuning_hpo=on_tuning_hpo,
        sequences=sequences,
        base_model=base_model,
        n_gpus=n_gpus,
        fold_cache_enabled=fold_cache_enabled,
        fold_cache_dir=fold_cache_dir,
        feature_stack=feature_stack,
        blend=blend,
    )

    # Build tournament tables per horizon (parallel across horizons)
    if on_stats_start is not None:
        on_stats_start()

    def _compute_horizon_table(h: int) -> tuple[int, pd.DataFrame] | None:
        """Compute tournament table for a single horizon (thread-safe)."""
        if h not in all_actuals:
            logger.warning("No actuals for h=%d, skipping", h)
            return None

        available_models = [m for m in models if m in all_model_preds and h in all_model_preds[m]]
        if len(available_models) < 1:
            logger.warning("No models have predictions for h=%d", h)
            return None

        common_idx = all_actuals[h].index
        for m in available_models:
            common_idx = common_idx.intersection(all_model_preds[m][h].index)

        if len(common_idx) == 0:
            logger.warning("No common observations for h=%d, skipping", h)
            return None

        common_idx = common_idx.sort_values()
        y_all = all_actuals[h].loc[common_idx].values
        h_model_preds: dict[str, np.ndarray] = {}
        for m in available_models:
            h_model_preds[m] = all_model_preds[m][h].loc[common_idx].values

        # Compute daily simple returns for vol-targeting from panel data
        ret_all = None
        sym_lengths: list[int] | None = None
        iv_all = None
        spot_all = None
        try:
            if hasattr(common_idx, "get_level_values"):
                symbols_in_idx = common_idx.get_level_values("symbol")
                sym_returns_list: list[np.ndarray] = []
                sym_iv_list: list[np.ndarray] = []
                sym_spot_list: list[np.ndarray] = []
                sym_lengths = []
                for sym in dict.fromkeys(symbols_in_idx):
                    if sym not in panel_data or "close" not in panel_data[sym].columns:
                        continue
                    close = panel_data[sym]["close"]
                    forward_ret = close.shift(-1) / close - 1.0
                    sym_dates = common_idx[symbols_in_idx == sym].get_level_values("date")
                    ret_aligned = forward_ret.reindex(sym_dates)
                    sym_returns_list.append(ret_aligned.values)
                    sym_lengths.append(len(ret_aligned))
                    sym_spot_list.append(close.reindex(sym_dates).values)
                    iv_data = load_iv_cache(sym)
                    if iv_data is not None and "iv_1m_atm" in iv_data.columns:
                        iv_s = iv_data["iv_1m_atm"].reindex(sym_dates).shift(1)
                        sym_iv_list.append((iv_s / 100.0).values)
                    else:
                        sym_iv_list.append(np.full(len(sym_dates), np.nan))
                if sym_returns_list:
                    ret_all = np.concatenate(sym_returns_list)
                if sym_iv_list:
                    iv_all = np.concatenate(sym_iv_list)
                if sym_spot_list:
                    spot_all = np.concatenate(sym_spot_list)
            else:
                for sym, df in panel_data.items():
                    if "close" not in df.columns:
                        continue
                    close = df["close"]
                    forward_ret = close.shift(-1) / close - 1.0
                    ret_aligned = forward_ret.reindex(common_idx)
                    if not ret_aligned.isna().all():
                        ret_all = ret_aligned.values
                        sym_lengths = [len(ret_all)]
                        spot_all = close.reindex(common_idx).values
                        iv_data = load_iv_cache(sym)
                        if iv_data is not None and "iv_1m_atm" in iv_data.columns:
                            iv_s = iv_data["iv_1m_atm"].reindex(common_idx).shift(1)
                            iv_all = (iv_s / 100.0).values
                    break
        except Exception:
            logger.warning(
                "h=%d: failed to align returns/IV for VT/DH metrics, skipping",
                h,
                exc_info=True,
            )

        if on_horizon_start is not None:
            on_horizon_start(h)

        stats = tournament_table(
            h_model_preds,
            y_all,
            baseline="har",
            horizon=h,
            mcs_bootstrap=mcs_bootstrap,
        )
        table = enrich_tournament_economics(
            stats,
            h_model_preds,
            y_all,
            daily_returns=(ret_all if vt_enabled else None),
            symbol_lengths=(sym_lengths if vt_enabled else None),
            implied_vol=(iv_all if dh_enabled else None),
            spot_prices=(spot_all if dh_enabled else None),
            dh_mode=dh_mode,
            horizon=h,
        )
        logger.info(
            "h=%d pooled tournament complete: %d models (%d obs)",
            h,
            len(table),
            len(y_all),
        )

        if on_horizon_complete is not None:
            on_horizon_complete(h)

        return (h, table)

    # Run horizon stats in parallel (ThreadPool — NumPy releases GIL)
    tournament_results: dict[int, pd.DataFrame] = {}
    with ThreadPoolExecutor(max_workers=min(3, len(horizons))) as executor:
        futures = {executor.submit(_compute_horizon_table, h): h for h in horizons}
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                h, table = result
                tournament_results[h] = table

    # Auto-generate interactive dashboard
    if output_dir:
        # Decompose MultiIndex series into per-symbol dicts for the dashboard
        actual_series_by_sym: dict[tuple[str, int], pd.Series] = {}
        pred_series_by_sym: dict[tuple[str, str, int], pd.Series] = {}

        available_symbols = list(panel_data.keys())
        for h in horizons:
            if h not in all_actuals:
                continue
            actuals_mi = all_actuals[h]
            for sym in available_symbols:
                try:
                    sym_slice = actuals_mi.xs(sym, level="symbol")
                    actual_series_by_sym[(sym, h)] = sym_slice
                except KeyError:
                    pass

            for m in models:
                if m not in all_model_preds or h not in all_model_preds[m]:
                    continue
                preds_mi = all_model_preds[m][h]
                for sym in available_symbols:
                    try:
                        sym_slice = preds_mi.xs(sym, level="symbol")
                        pred_series_by_sym[(m, sym, h)] = sym_slice
                    except KeyError:
                        pass

        _generate_dashboard(
            tournament_results=tournament_results,
            all_actuals_series=actual_series_by_sym,
            all_preds_series=pred_series_by_sym,
            symbols=available_symbols,
            models=models,
            horizons=horizons,
            output_dir=output_dir,
            symbol_data=panel_data,
            config_path=config_path,
            on_dh_start=on_dh_start,
            on_dh_symbol=on_dh_symbol,
            on_dh_model=on_dh_model,
            dh_mode=dh_mode,
            dh_enabled=dh_enabled,
            gsvivs_enabled=gsvivs_enabled,
            gsvivs_short_threshold=gsvivs_short_threshold,
            gsvivs_default_long=gsvivs_default_long,
            gsvivs_signal_type=gsvivs_signal_type,
            gsvivs_flat_percentile=gsvivs_flat_percentile,
            gsvivs_iv_source=gsvivs_iv_source,
            gsvivs_iv_sources=gsvivs_iv_sources,
            gsvivs_signal_space=gsvivs_signal_space,
            gsvivs_sizings=gsvivs_sizings,
            trained_models=trained_models,
            test_data=all_test_data,
        )

        # Persist structured metrics.json alongside the dashboard
        _save_pooled_metrics(tournament_results, output_dir)

    return tournament_results


def _save_pooled_metrics(tournament_results: dict[int, pd.DataFrame], output_dir: Path) -> None:
    """Persist metrics.json from pooled tournament results.

    Delegates to evaluation.aggregate.save_pooled_metrics.
    """
    from volforecast.evaluation.aggregate import save_pooled_metrics

    save_pooled_metrics(tournament_results, output_dir)


def display_tournament(results: dict[int, pd.DataFrame]) -> None:
    """Pretty-print tournament tables using Rich. Delegates to tournament_dashboard."""
    from volforecast.evaluation.tournament_dashboard import display_tournament as _display

    _display(results)


def _compute_gsvivs_stats(
    all_preds_series: dict[tuple[str, str, int], pd.Series],
    symbols: list[str],
    models: list[str],
    horizons: list[int],
    symbol_data: dict[str, pd.DataFrame] | None = None,
    short_threshold: float = 0.05,
    default_long: bool = False,
    signal_type: str = "iv_rv_gap",
    flat_percentile: int = 80,
    iv_source: str = "edrvs",
    signal_space: str = "vol",
    signal_sizings: Any | None = None,
    iv_sources: list[str] | None = None,
) -> tuple[dict[str, dict[int, list[dict]]], dict[str, dict[int, list[dict]]]]:
    """Compute GSVIVS01 signal backtest stats. Delegates to evaluation.gsvivs."""
    from volforecast.evaluation.gsvivs import compute_gsvivs_stats

    return compute_gsvivs_stats(
        all_preds_series=all_preds_series,
        symbols=symbols,
        models=models,
        horizons=horizons,
        symbol_data=symbol_data,
        short_threshold=short_threshold,
        default_long=default_long,
        signal_type=signal_type,
        flat_percentile=flat_percentile,
        iv_source=iv_source,
        signal_space=signal_space,
        signal_sizings=signal_sizings,
        iv_sources=iv_sources,
    )
