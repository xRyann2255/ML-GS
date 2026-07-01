"""Tournament dashboard orchestration.

Handles dashboard HTML generation and Rich console display for tournament
results. Separated from tournament.py to isolate visualization concerns
from orchestration logic.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from volforecast.data.edrvol import load_edrvs_cache, load_iv_cache
from volforecast.evaluation.economic_value import iv_tenor_for_horizon
from volforecast.evaluation.gsvivs import (
    compute_gsvivs_stats as _compute_gsvivs_stats,
    default_gsvivs_dashboard_iv_label as _default_gsvivs_dashboard_iv_label,
)

logger = logging.getLogger(__name__)


def generate_dashboard(
    tournament_results: dict[int, pd.DataFrame],
    all_actuals_series: dict[tuple[str, int], pd.Series],
    all_preds_series: dict[tuple[str, str, int], pd.Series],
    symbols: list[str],
    models: list[str],
    horizons: list[int],
    output_dir: Path,
    symbol_data: dict[str, pd.DataFrame] | None = None,
    config_path: str | None = None,
    on_dh_start: Any | None = None,
    on_dh_symbol: Any | None = None,
    on_dh_model: Any | None = None,
    dh_mode: str = "realistic",
    dh_enabled: bool = True,
    gsvivs_enabled: bool = False,
    gsvivs_short_threshold: float = 0.0,
    gsvivs_default_long: bool = False,
    gsvivs_signal_type: str = "iv_rv_gap",
    gsvivs_flat_percentile: int = 80,
    gsvivs_iv_source: str = "edrvs",
    gsvivs_iv_sources: list[str] | None = None,
    gsvivs_signal_space: str = "variance",
    gsvivs_sizings: Any | None = None,
    trained_models: dict[str, dict[int, Any]] | None = None,
    test_data: dict[str, dict[int, Any]] | None = None,
) -> None:
    """Generate the tournament dashboard HTML with per-symbol drill-down.

    Parameters
    ----------
    tournament_results : dict[int, DataFrame]
        Tournament tables keyed by horizon.
    all_actuals_series : dict[(symbol, horizon), Series]
        Per-symbol, per-horizon actual log-RV series.
    all_preds_series : dict[(model, symbol, horizon), Series]
        Per-model, per-symbol, per-horizon prediction series.
    symbols : list[str]
        Symbol list.
    models : list[str]
        Model name list.
    horizons : list[int]
        Horizon list.
    output_dir : Path
        Output directory for artifacts.
    symbol_data : dict[str, DataFrame], optional
        Raw symbol DataFrames (must contain 'close' column for P&L chart).
    """
    try:
        from volforecast.data.edrvol import load_edrvs_cache, load_iv_cache
        from volforecast.visualization.dashboard import (
            build_tournament_dashboard,
            save_tournament_dashboard,
        )

        if dh_mode == "simple":
            from volforecast.evaluation.economic_value import (
                delta_hedged_sharpe as _dh_sharpe_fn,
            )
        elif dh_mode == "discrete":
            from volforecast.evaluation.economic_value import (
                discrete_delta_hedged_sharpe as _dh_sharpe_fn,
            )
        else:
            from volforecast.evaluation.realistic_straddle import (
                realistic_delta_hedged_sharpe as _dh_sharpe_fn,
            )

        # Assemble per-horizon, per-symbol actuals and forecasts
        dash_actuals: dict[int, dict[str, pd.Series]] = {}
        dash_forecasts: dict[int, dict[str, dict[str, pd.Series]]] = {}

        for h in horizons:
            h_actuals: dict[str, pd.Series] = {}
            h_forecasts: dict[str, dict[str, pd.Series]] = {}

            for s in symbols:
                if (s, h) in all_actuals_series:
                    h_actuals[s] = all_actuals_series[(s, h)]

                sym_preds: dict[str, pd.Series] = {}
                for m in models:
                    if (m, s, h) in all_preds_series:
                        sym_preds[m] = all_preds_series[(m, s, h)]
                if sym_preds:
                    h_forecasts[s] = sym_preds

            dash_actuals[h] = h_actuals
            dash_forecasts[h] = h_forecasts

        # Compute per-symbol DH stats for dashboard dropdown
        # dh_per_symbol[symbol][horizon] = [{"name": model, "dh_sharpe": ..., ...}, ...]
        if dh_enabled and on_dh_start is not None:
            on_dh_start(len(symbols), len(horizons), len(models))

        def _compute_symbol_dh(s: str) -> tuple[str, dict[int, list[dict]]] | None:
            """Compute DH stats for a single symbol (thread-safe)."""
            iv_data = load_iv_cache(s)
            if iv_data is None:
                return None
            if "iv_1m_atm" not in iv_data.columns and "iv_1w_atm" not in iv_data.columns:
                return None
            if "iv_0dte" in iv_data.columns:
                iv_data = iv_data.copy()
                iv_data["iv_0dte_atm"] = iv_data["iv_0dte"] * 100.0
            # Load EDRVS var-swap strike for h=1 signal
            edrvs_vs = load_edrvs_cache()
            if edrvs_vs is not None and not edrvs_vs.empty:
                if not hasattr(iv_data, "_is_copy"):
                    iv_data = iv_data.copy()
                edrvs_vs.index = pd.DatetimeIndex(
                    edrvs_vs.index.normalize(), dtype="datetime64[ns]"
                )
                iv_data["iv_vs_0dte"] = edrvs_vs.reindex(iv_data.index)
            spot = symbol_data.get(s) if symbol_data else None
            if spot is None or "close" not in spot.columns:
                return None

            sym_dh: dict[int, list[dict]] = {}
            for h in horizons:
                if (s, h) not in all_actuals_series:
                    continue
                actuals_s = all_actuals_series[(s, h)]
                sym_preds = {
                    m: all_preds_series[(m, s, h)] for m in models if (m, s, h) in all_preds_series
                }
                if not sym_preds:
                    continue

                common_idx = actuals_s.index
                for preds_series in sym_preds.values():
                    common_idx = common_idx.intersection(preds_series.index)
                if len(common_idx) < 30:
                    continue
                common_idx = common_idx.sort_values()

                iv_col, tenor_days = iv_tenor_for_horizon(h)
                if iv_col not in iv_data.columns:
                    iv_col, tenor_days = "iv_1m_atm", 22
                iv_aligned = iv_data[iv_col].reindex(common_idx).shift(1) / 100.0
                spot_aligned = spot["close"].reindex(common_idx)
                actual_daily_var = np.exp(actuals_s.loc[common_idx].values)

                valid_iv = ~iv_aligned.isna()
                if valid_iv.sum() < 30:
                    continue

                iv_arr = iv_aligned.values
                spot_arr = spot_aligned.values

                model_dh_rows = []
                for m_name, m_preds in sym_preds.items():
                    pred_arr = m_preds.loc[common_idx].values
                    mask = valid_iv.values & ~np.isnan(pred_arr) & ~np.isnan(spot_arr)
                    if mask.sum() < 30:
                        continue
                    dh_result = _dh_sharpe_fn(
                        pred_arr[mask],
                        iv_arr[mask],
                        actual_daily_var[mask],
                        spot_arr[mask],
                        tenor_days=tenor_days,
                    )
                    model_dh_rows.append({"name": m_name, **dh_result})

                mask_baseline = valid_iv.values & ~np.isnan(spot_arr)
                if mask_baseline.sum() >= 30:
                    from volforecast.evaluation.economic_value import naive_dh_baselines

                    bl_results = naive_dh_baselines(
                        realized_var=actual_daily_var[mask_baseline],
                        implied_vol=iv_arr[mask_baseline],
                        spot_prices=spot_arr[mask_baseline],
                        dh_mode=dh_mode,
                    )
                    for bl_name, bl_metrics in bl_results.items():
                        model_dh_rows.append({"name": f"[baseline] {bl_name}", **bl_metrics})

                if model_dh_rows:
                    model_dh_rows.sort(key=lambda r: r["dh_sharpe"], reverse=True)
                    sym_dh[h] = model_dh_rows
            if sym_dh:
                return (s, sym_dh)
            return None

        # Run DH computation in parallel (ThreadPool — NumPy releases GIL).
        # Skipped entirely when dh_enabled=False (saves ~20-60s for large universes
        # and removes the DH straddle table from the dashboard).
        dh_per_symbol: dict[str, dict[int, list[dict]]] = {}
        if dh_enabled:
            with ThreadPoolExecutor(max_workers=min(4, len(symbols))) as executor:
                futures = {executor.submit(_compute_symbol_dh, s): s for s in symbols}
                for future in as_completed(futures):
                    if on_dh_symbol is not None:
                        on_dh_symbol(futures[future])
                    result = future.result()
                    if result is not None:
                        sym_name, sym_dh_data = result
                        dh_per_symbol[sym_name] = sym_dh_data

        symbol_label = ", ".join(symbols) if len(symbols) <= 4 else f"{len(symbols)} symbols"

        # Compute GSVIVS01 variance swap signal stats (if enabled)
        gsvivs_per_horizon: dict[int, list[dict]] = {}
        gsvivs_traces: dict[int, list[dict]] = {}
        gsvivs_per_iv: dict[str, dict[int, list[dict]]] = {}
        gsvivs_traces_per_iv: dict[str, dict[int, list[dict]]] = {}
        if gsvivs_enabled:
            gsvivs_per_iv, gsvivs_traces_per_iv = _compute_gsvivs_stats(
                all_preds_series=all_preds_series,
                symbols=symbols,
                models=models,
                horizons=horizons,
                symbol_data=symbol_data,
                short_threshold=gsvivs_short_threshold,
                default_long=gsvivs_default_long,
                signal_type=gsvivs_signal_type,
                flat_percentile=gsvivs_flat_percentile,
                iv_source=gsvivs_iv_source,
                signal_space=gsvivs_signal_space,
                signal_sizings=gsvivs_sizings,
                iv_sources=gsvivs_iv_sources,
            )
            if gsvivs_per_iv:
                default_key = _default_gsvivs_dashboard_iv_label(gsvivs_per_iv)
                if default_key is not None:
                    gsvivs_per_horizon = gsvivs_per_iv[default_key]
                    gsvivs_traces = gsvivs_traces_per_iv.get(default_key, {})

        # Compute SHAP/ALE explainability (if enabled and test_data available)
        explainability_results: dict = {}
        if trained_models and test_data:
            try:
                from volforecast.evaluation.explainability import (
                    ExplainabilityConfig,
                    compute_explainability,
                )

                # Try to load config from YAML via config_path
                explain_cfg = None
                if config_path:
                    try:
                        from volforecast.config import ExperimentConfig
                        exp_cfg = ExperimentConfig.from_yaml(config_path)
                        explain_cfg = exp_cfg.tournament.explainability
                    except Exception:
                        pass
                if explain_cfg is None:
                    explain_cfg = ExplainabilityConfig(enabled=True)
                if explain_cfg.enabled:
                    explainability_results = compute_explainability(
                        trained_models, test_data, explain_cfg
                    )
            except Exception as ex:
                logger.warning("Explainability computation failed: %s", ex)

        html = build_tournament_dashboard(
            tournament_tables=tournament_results,
            actuals=dash_actuals,
            forecasts=dash_forecasts,
            experiment_name="HAR Tournament",
            symbol_label=symbol_label,
            dh_per_symbol=dh_per_symbol,
            config_path=config_path,
            dh_mode=dh_mode,
            gsvivs_per_horizon=gsvivs_per_horizon,
            gsvivs_traces=gsvivs_traces,
            gsvivs_per_iv=gsvivs_per_iv,
            gsvivs_traces_per_iv=gsvivs_traces_per_iv,
            gsvivs_short_threshold=gsvivs_short_threshold,
            trained_models=trained_models,
            explainability_results=explainability_results,
        )
        path = save_tournament_dashboard(html, output_dir)
        print(f"\nDashboard saved: {path}")

    except Exception as e:
        logger.warning("Dashboard generation failed (non-blocking): %s", e, exc_info=True)

# Keep old name as alias for backward compat
_generate_dashboard = generate_dashboard


def display_tournament(results: dict[int, pd.DataFrame]) -> None:
    """Pretty-print tournament tables using Rich."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    for h, df in sorted(results.items()):
        table = Table(title=f"QLIKE Tournament -- h={h}")
        for col in df.columns:
            justify = "left" if col == "model" else "right"
            table.add_column(col, justify=justify)
        for _, row in df.iterrows():
            cells = []
            for col in df.columns:
                v = row[col]
                if isinstance(v, bool):
                    cells.append("*" if v else "")
                elif isinstance(v, float):
                    if abs(v) > 0.001:
                        cells.append(f"{v:.4f}")
                    else:
                        cells.append(f"{v:.2e}")
                else:
                    cells.append(str(v))
            style = "bold" if row.get("mcs_included", False) else None
            table.add_row(*cells, style=style)
        console.print(table)
        console.print()

