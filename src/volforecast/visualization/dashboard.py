"""Tournament dashboard builder.

Generates a self-contained interactive HTML dashboard from tournament results.
Uses Jinja2 templates with embedded Plotly JS for dark-themed visualization.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from jinja2 import Environment, PackageLoader

# Colors: best = green, worst = red, others from distinguishable palette
_PALETTE = [
    "#4fc3f7",  # cyan
    "#ff7f0e",  # orange
    "#ab47bc",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#bcbd22",  # olive
    "#17becf",  # teal
]
_COLOR_BEST = "#66bb6a"
_COLOR_WORST = "#ef5350"

MODEL_DESCRIPTIONS: dict[str, str] = {
    "random_walk": "Tomorrow's vol = today's vol (no-change forecast)",
    "historical_mean": "Expanding-window mean of all past log-RV",
    "rolling_mean": "Rolling 22-day mean of log-RV",
    "median_rv": "Rolling 22-day median of log-RV",
    "ewma": "Exponentially weighted moving average (lambda=0.94)",
    "ar1": "AR(1) model on log-RV",
    "vix_implied": "VIX-implied volatility forecast",
    "har": "Heterogeneous AR: daily + weekly + monthly RV components",
    "harq": "HAR + realized quarticity interaction (Bollerslev 2016)",
    "shar": "Semi-variance HAR: upside/downside RV decomposition",
    "har_j": "HAR + jump component (significant jumps from BPV)",
    "har_cj": "HAR with continuous + jump components separated",
    "ridge_har": "Ridge-regularized HAR + asymmetry features",
    "lasso_har": "Lasso-regularized HAR + asymmetry features",
}


def build_tournament_dashboard(
    tournament_tables: dict[int, pd.DataFrame],
    actuals: dict[int, dict[str, pd.Series]],
    forecasts: dict[int, dict[str, dict[str, pd.Series]]],
    *,
    experiment_name: str = "HAR Tournament",
    symbol_label: str = "SPY",
    dh_per_symbol: dict[str, dict[int, list[dict]]] | None = None,
    config_path: str | None = None,
    dh_mode: str = "realistic",
    gsvivs_per_horizon: dict[int, list[dict]] | None = None,
    gsvivs_traces: dict[int, list[dict]] | None = None,
    gsvivs_per_iv: dict[str, dict[int, list[dict]]] | None = None,
    gsvivs_traces_per_iv: dict[str, dict[int, list[dict]]] | None = None,
    gsvivs_short_threshold: float = 0.0,
    model_details: dict | None = None,
    trained_models: dict | None = None,
    explainability_results: dict | None = None,
) -> str:
    """Build a self-contained HTML tournament dashboard.

    Parameters
    ----------
    tournament_tables : dict[int, DataFrame]
        Keys are horizons. Values are tournament result DataFrames with
        columns: model, qlike, mse, r_squared, mcs_included, etc.
    actuals : dict[int, dict[str, Series]]
        Per-horizon, per-symbol actual log RV series.
        actuals[horizon][symbol] = Series(date-indexed).
    forecasts : dict[int, dict[str, dict[str, Series]]]
        Per-horizon, per-symbol, per-model prediction series.
        forecasts[horizon][symbol][model_name] = Series(date-indexed).
    experiment_name : str
        Title for the dashboard.
    symbol_label : str
        Symbol(s) label for the footer.
    dh_per_symbol : dict[str, dict[int, list[dict]]], optional
        Per-symbol DH stats: dh_per_symbol[symbol][horizon] = [{name, dh_sharpe, ...}].

    Returns
    -------
    str
        Complete HTML string for the dashboard.
    """
    horizons = sorted(tournament_tables.keys())
    model_names = _get_model_names(tournament_tables, horizons)

    # Derive symbol list from data
    symbol_list: list[str] = []
    for h in horizons:
        for sym in actuals.get(h, {}):
            if sym not in symbol_list:
                symbol_list.append(sym)

    # Assign colors: best=green, worst=red, others from palette
    model_colors = _assign_colors(model_names)

    # Build trace data keyed by symbol and horizon
    # trace_data_by_symbol[symbol][horizon] = [traces...]
    # Special key "__pooled__" for the cross-symbol median view
    trace_data_by_symbol: dict[str, dict[int, list]] = {}

    # Per-symbol traces
    for sym in symbol_list:
        sym_traces: dict[int, list] = {}
        for h in horizons:
            traces = []
            # Actual RV trace for this symbol
            act = actuals.get(h, {}).get(sym)
            if act is not None and not act.empty:
                traces.append(
                    {
                        "x": [d.isoformat()[:10] for d in act.index],
                        "y": act.values.tolist(),
                        "mode": "lines",
                        "name": "Actual RV",
                        "line": {"color": "#ffffff", "width": 2.5},
                        "hovertemplate": "%{x|%Y-%m-%d}<br>Actual: %{y:.6f}<extra></extra>",
                    }
                )

            # Model traces for this symbol. Line color always equals the sidebar
            # swatch (palette-only); width emphasises the best model.
            best_model = _best_model_for_horizon(tournament_tables[h])
            sym_forecasts = forecasts.get(h, {}).get(sym, {})
            for name in model_names:
                if name not in sym_forecasts:
                    continue
                preds = sym_forecasts[name]
                color = model_colors[name]
                width = 2.0 if name == best_model else 1.3
                traces.append(
                    {
                        "x": [d.isoformat()[:10] for d in preds.index],
                        "y": preds.values.tolist(),
                        "mode": "lines",
                        "name": name,
                        "line": {"color": color, "width": width},
                        "hovertemplate": f"%{{x|%Y-%m-%d}}<br>{name}: %{{y:.6f}}<extra></extra>",
                    }
                )
            sym_traces[h] = traces
        trace_data_by_symbol[sym] = sym_traces

    # Pooled view: cross-symbol median per date
    pooled_traces: dict[int, list] = {}
    for h in horizons:
        traces = []
        # Median actual across symbols per date
        act_frames = {
            s: actuals.get(h, {}).get(s)
            for s in symbol_list
            if actuals.get(h, {}).get(s) is not None
        }
        if act_frames:
            act_df = pd.DataFrame(act_frames)
            act_median = act_df.median(axis=1).dropna()
            if not act_median.empty:
                traces.append(
                    {
                        "x": [d.isoformat()[:10] for d in act_median.index],
                        "y": act_median.values.tolist(),
                        "mode": "lines",
                        "name": "Actual RV",
                        "line": {"color": "#ffffff", "width": 2.5},
                        "hovertemplate": (
                            "%{x|%Y-%m-%d}<br>Actual (median): %{y:.6f}<extra></extra>"
                        ),
                    }
                )

        # Pooled (cross-symbol median) traces. Line color always equals the
        # sidebar swatch (palette-only); width emphasises the best model.
        best_model = _best_model_for_horizon(tournament_tables[h])
        for name in model_names:
            pred_frames = {}
            for s in symbol_list:
                sym_f = forecasts.get(h, {}).get(s, {})
                if name in sym_f:
                    pred_frames[s] = sym_f[name]
            if not pred_frames:
                continue
            pred_df = pd.DataFrame(pred_frames)
            pred_median = pred_df.median(axis=1).dropna()
            if pred_median.empty:
                continue
            color = model_colors[name]
            width = 2.0 if name == best_model else 1.3
            traces.append(
                {
                    "x": [d.isoformat()[:10] for d in pred_median.index],
                    "y": pred_median.values.tolist(),
                    "mode": "lines",
                    "name": name,
                    "line": {"color": color, "width": width},
                    "hovertemplate": (
                        f"%{{x|%Y-%m-%d}}<br>{name} (median): %{{y:.6f}}<extra></extra>"
                    ),
                }
            )
        pooled_traces[h] = traces
    trace_data_by_symbol["__pooled__"] = pooled_traces

    # Build stats table data
    stats = _build_stats(tournament_tables, horizons, model_colors)

    # Compute divergence lines (using pooled median forecasts)
    pooled_forecasts_for_div: dict[int, dict[str, pd.Series]] = {}
    for h in horizons:
        h_pf: dict[str, pd.Series] = {}
        for name in model_names:
            pred_frames = {}
            for s in symbol_list:
                sym_f = forecasts.get(h, {}).get(s, {})
                if name in sym_f:
                    pred_frames[s] = sym_f[name]
            if pred_frames:
                h_pf[name] = pd.DataFrame(pred_frames).median(axis=1).dropna()
        pooled_forecasts_for_div[h] = h_pf
    divergence_lines = _compute_divergence_dates(pooled_forecasts_for_div, horizons)

    # Best models per horizon
    best_models = {h: _best_model_for_horizon(tournament_tables[h]) for h in horizons}

    # Model metadata for checkboxes (with descriptions)
    models_meta = [
        {
            "name": name,
            "color": model_colors[name],
            "description": MODEL_DESCRIPTIONS.get(name, ""),
        }
        for name in model_names
    ]

    # Determine observation count (from first symbol or pooled)
    n_obs = 0
    for h in horizons:
        for s in symbol_list:
            act = actuals.get(h, {}).get(s)
            if act is not None:
                n_obs = max(n_obs, len(act))
                break
        if n_obs:
            break

    # Build economic evaluation tables (separate from main stats)
    vt_stats = _build_vt_stats(tournament_tables, horizons, model_colors)
    dh_stats = _build_dh_stats(tournament_tables, horizons, model_colors)

    # Build stat_meta: per-horizon summary info for the sidebar explainer
    stat_meta: dict[int, dict] = {}
    for h in horizons:
        df = tournament_tables[h]
        # Find baseline (HAR or first model)
        baseline_row = df[df["model"] == "har"]
        if baseline_row.empty:
            baseline_row = df.iloc[:1]
        baseline_name = str(baseline_row.iloc[0]["model"])
        baseline_qlike = float(baseline_row.iloc[0]["qlike"])
        mcs_count = int(df["mcs_included"].sum()) if "mcs_included" in df.columns else 0
        stat_meta[h] = {
            "baseline_name": baseline_name,
            "baseline_qlike": baseline_qlike,
            "n_models": len(df),
            "mcs_count": mcs_count,
        }
    # Straddle/VT assumptions (constants from economic_value.py defaults)
    econ_assumptions = {
        "tenor_days": 30,
        "cost_vol_points": 0.5,
        "holding_period": 22,
        "target_vol": 0.10,
        "max_leverage": 2.0,
        "dh_mode": dh_mode,
    }

    has_vt_data = any(bool(rows) for rows in vt_stats.values())
    has_dh_data = any(bool(rows) for rows in dh_stats.values())

    # Per-symbol DH stats for the dropdown (if provided)
    # Format: dh_symbol_stats[symbol][horizon] = [rows...] with color/css added
    dh_symbol_stats: dict[str, dict[int, list[dict]]] = {}
    dh_symbols: list[str] = []
    if dh_per_symbol:
        dh_symbols = sorted(dh_per_symbol.keys())
        for sym, sym_horizons in dh_per_symbol.items():
            dh_symbol_stats[sym] = {}
            for h, rows in sym_horizons.items():
                styled_rows = []
                for rank, row in enumerate(rows, 1):
                    name = row["name"]
                    color = model_colors.get(name, "#888")
                    css_class = ""
                    if rank == 1:
                        css_class = "best"
                        color = _COLOR_BEST
                    elif rank == len(rows):
                        css_class = "worst"
                        color = _COLOR_WORST
                    styled_rows.append(
                        {
                            "rank": rank,
                            "name": name,
                            "dh_sharpe": row.get("dh_sharpe", 0.0),
                            "dh_ann_ret": row.get("dh_ann_ret"),
                            "dh_ann_vol": row.get("dh_ann_vol"),
                            "dh_pnl": row.get("dh_pnl", 0.0),
                            "dh_max_dd": row.get("dh_max_dd", 0.0),
                            "dh_hit_rate": row.get("dh_hit_rate", 0.0),
                            "css_class": css_class,
                            "color": color,
                        }
                    )
                dh_symbol_stats[sym][h] = styled_rows

    # If per-symbol DH data is available, consider it as having DH data too
    if dh_symbol_stats and not has_dh_data:
        has_dh_data = True

    # Build GSVIVS stats with styling
    gsvivs_stats: dict[int, list[dict]] = {}
    has_gsvivs_data = False
    # Track unique sizing labels in the order they first appear so the
    # template can render one toggle button per sizing variant (binary |
    # asym_long L=2 | zscore L=1 by default). Baselines have empty
    # sizing_label and stay visible regardless of which toggle is active.
    gsvivs_sizing_labels: list[str] = []

    def _track_sizing_label(label: str) -> None:
        if label and label not in gsvivs_sizing_labels:
            gsvivs_sizing_labels.append(label)

    if gsvivs_per_horizon:
        for h, rows in gsvivs_per_horizon.items():
            if not rows:
                gsvivs_stats[h] = []
                continue
            styled_rows = []
            for rank, row in enumerate(rows, 1):
                name = row["name"]
                color = model_colors.get(name, "#888")
                css_class = ""
                if name.startswith("[baseline]"):
                    css_class = "baseline"
                elif rank == 1:
                    css_class = "best"
                    color = _COLOR_BEST
                elif rank == len(rows):
                    css_class = "worst"
                    color = _COLOR_WORST
                sizing_label = row.get("sizing_label", "")
                _track_sizing_label(sizing_label)
                styled_rows.append(
                    {
                        "rank": rank,
                        "name": name,
                        "sizing_label": sizing_label,
                        "sharpe_0rf": row.get("sharpe_0rf", 0.0),
                        "sharpe_5rf": row.get("sharpe_5rf", 0.0),
                        "ann_return": row.get("ann_return", 0.0),
                        "ann_vol": row.get("ann_vol", 0.0),
                        "total_return": row.get("total_return", 0.0),
                        "max_drawdown": row.get("max_drawdown", 0.0),
                        "positive_days": row.get("positive_days", "0/0 (0.0%)"),
                        "flat_pct": row.get("flat_pct", 0.0),
                        "precision": row.get("precision", 0.0),
                        "recall": row.get("recall", 0.0),
                        "f1": row.get("f1", 0.0),
                        "mcc": row.get("mcc", 0.0),
                        "css_class": css_class,
                        "color": color,
                    }
                )
            gsvivs_stats[h] = styled_rows
            if styled_rows:
                has_gsvivs_data = True

    # Build multi-IV GSVIVS stats (keyed by iv_source label).
    # Pass through all configured IV sources so the dashboard can show
    # selector buttons when more than one is present.
    gsvivs_iv_stats: dict[str, dict[int, list[dict]]] = {}
    gsvivs_iv_traces_out: dict[str, dict[int, list[dict]]] = {}
    gsvivs_iv_labels: list[str] = []
    if gsvivs_per_iv:
        for iv_label, iv_horizons in gsvivs_per_iv.items():
            gsvivs_iv_labels.append(iv_label)
            gsvivs_iv_stats[iv_label] = {}
            for h, rows in iv_horizons.items():
                if not rows:
                    gsvivs_iv_stats[iv_label][h] = []
                    continue
                styled_rows = []
                for rank, row in enumerate(rows, 1):
                    name = row["name"]
                    color = model_colors.get(name, "#888")
                    css_class = ""
                    if name.startswith("[baseline]"):
                        css_class = "baseline"
                    elif rank == 1:
                        css_class = "best"
                        color = _COLOR_BEST
                    elif rank == len(rows):
                        css_class = "worst"
                        color = _COLOR_WORST
                    sizing_label = row.get("sizing_label", "")
                    _track_sizing_label(sizing_label)
                    styled_rows.append(
                        {
                            "rank": rank,
                            "name": name,
                            "sizing_label": sizing_label,
                            "sharpe_0rf": row.get("sharpe_0rf", 0.0),
                            "sharpe_5rf": row.get("sharpe_5rf", 0.0),
                            "ann_return": row.get("ann_return", 0.0),
                            "ann_vol": row.get("ann_vol", 0.0),
                            "total_return": row.get("total_return", 0.0),
                            "max_drawdown": row.get("max_drawdown", 0.0),
                            "positive_days": row.get("positive_days", "0/0 (0.0%)"),
                            "flat_pct": row.get("flat_pct", 0.0),
                            "precision": row.get("precision", 0.0),
                            "recall": row.get("recall", 0.0),
                            "f1": row.get("f1", 0.0),
                            "mcc": row.get("mcc", 0.0),
                            "css_class": css_class,
                            "color": color,
                        }
                    )
                gsvivs_iv_stats[iv_label][h] = styled_rows
            if not has_gsvivs_data and any(gsvivs_iv_stats[iv_label].values()):
                has_gsvivs_data = True
        # Copy traces as-is (already in Plotly format)
        if gsvivs_traces_per_iv:
            gsvivs_iv_traces_out = gsvivs_traces_per_iv

    # Render template
    env = Environment(
        loader=PackageLoader("volforecast", "reporting/templates"),
        autoescape=False,
    )
    template = env.get_template("tournament_dashboard.html")

    # Build per-horizon model rank maps from GSVIVS stats (Sharpe-sorted).
    # Used to order transition matrix cards best-to-worst.
    import re as _re

    def _build_model_ranks(
        stats_source: dict[int, list[dict]] | dict[str, dict[int, list[dict]]],
    ) -> dict[int, dict[str, int]]:
        """Extract {horizon: {bare_model: rank}} from styled GSVIVS rows."""
        ranks: dict[int, dict[str, int]] = {}
        # Normalize: stats_source may be {h: [rows]} or {iv: {h: [rows]}}
        horizon_rows: dict[int, list[dict]] = {}
        for key, val in stats_source.items():
            if isinstance(val, dict):
                # {iv_label: {h: [rows]}} → use first iv label
                for h, rows in val.items():
                    horizon_rows[h] = rows
                break
            else:
                horizon_rows = stats_source  # type: ignore[assignment]
                break
        for h, rows in horizon_rows.items():
            seen: dict[str, int] = {}
            rank = 0
            for row in rows:
                name = row.get("name", "")
                if name.startswith("[baseline]"):
                    continue
                bare = _re.sub(r"\s*\[[^\]]+\]\s*$", "", name)
                if bare not in seen:
                    rank += 1
                    seen[bare] = rank
            ranks[h] = seen
        return ranks

    ranks_by_horizon = _build_model_ranks(gsvivs_iv_stats or gsvivs_stats)

    # Compute transition matrices from GSVIVS traces
    gsvivs_transition_data: dict[str, dict] = {}
    transition_source = gsvivs_iv_traces_out or (gsvivs_traces if gsvivs_traces else {})
    for iv_label_or_h, iv_data in transition_source.items():
        # transition_source may be {iv_label: {h: [traces]}} or {h: [traces]}
        if isinstance(iv_data, dict):
            for h, traces in iv_data.items():
                h_int = int(h)
                matrices = _compute_transition_matrices(
                    traces,
                    horizon=h_int,
                    sizing_labels=gsvivs_sizing_labels,
                    model_ranks=ranks_by_horizon.get(h_int, {}),
                )
                gsvivs_transition_data.update(matrices)
        elif isinstance(iv_data, list):
            h_int = int(iv_label_or_h)
            matrices = _compute_transition_matrices(
                iv_data,
                horizon=h_int,
                sizing_labels=gsvivs_sizing_labels,
                model_ranks=ranks_by_horizon.get(h_int, {}),
            )
            gsvivs_transition_data.update(matrices)

    subtitle_parts = [
        symbol_label,
        f"Horizons: {', '.join(f'h={h}' for h in horizons)}",
        f"{n_obs} obs/symbol",
    ]
    if config_path:
        subtitle_parts.append(config_path)

    html = template.render(
        title=experiment_name,
        subtitle=" | ".join(subtitle_parts),
        horizons=horizons,
        symbols=symbol_list,
        models=models_meta,
        stats=stats,
        vt_stats=vt_stats,
        dh_stats=dh_stats,
        dh_symbol_stats=dh_symbol_stats,
        dh_symbols=dh_symbols,
        has_vt_data=has_vt_data,
        has_dh_data=has_dh_data,
        has_gsvivs_data=has_gsvivs_data,
        gsvivs_stats=gsvivs_stats,
        gsvivs_traces=json.dumps(gsvivs_traces or {}),
        gsvivs_iv_stats=gsvivs_iv_stats,
        gsvivs_iv_traces=json.dumps(gsvivs_iv_traces_out or {}),
        gsvivs_iv_labels=gsvivs_iv_labels,
        gsvivs_sizing_labels=gsvivs_sizing_labels,
        gsvivs_default_sizing=_default_active_sizing(gsvivs_sizing_labels),
        gsvivs_short_threshold=gsvivs_short_threshold,
        gsvivs_transition_data=json.dumps(gsvivs_transition_data),
        stat_meta=stat_meta,
        econ_assumptions=econ_assumptions,
        trace_data_by_symbol=json.dumps(trace_data_by_symbol),
        model_names=json.dumps(model_names),
        best_models=json.dumps(best_models),
        divergence_lines=json.dumps(divergence_lines),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        symbol_label=symbol_label,
        n_obs=n_obs,
        model_details_json=json.dumps(
            model_details
            if model_details is not None
            else _build_model_details(
                tournament_tables, horizons, model_colors,
                trained_models=trained_models,
                explainability_results=explainability_results,
            )
        ),
    )

    return html


# Public alias for backward compatibility and test discoverability
render_tournament_dashboard = build_tournament_dashboard


def save_tournament_dashboard(html: str, output_dir: str | Path) -> Path:
    """Save dashboard HTML to disk.

    Parameters
    ----------
    html : str
        Complete HTML string.
    output_dir : Path
        Experiment output directory.

    Returns
    -------
    Path
        Path to the saved file.
    """
    plots_dir = Path(output_dir) / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    path = plots_dir / "tournament_dashboard.html"
    path.write_text(html, encoding="utf-8")
    return path


def _get_model_names(tables: dict[int, pd.DataFrame], horizons: list[int]) -> list[str]:
    """Extract unique model names preserving QLIKE-sorted order from first horizon.

    Excludes [baseline] entries — those are only for the GSVIVS01 table.
    """
    if not horizons:
        return []
    first_table = tables[horizons[0]]
    return [m for m in first_table["model"].tolist() if not m.startswith("[baseline]")]


def _best_model_for_horizon(table: pd.DataFrame) -> str:
    """Return model name with lowest QLIKE."""
    return table.iloc[0]["model"]


def _worst_model_for_horizon(table: pd.DataFrame) -> str:
    """Return model name with highest QLIKE."""
    return table.iloc[-1]["model"]


def _assign_colors(model_names: list[str]) -> dict[str, str]:
    """Assign colors to models. Best/worst get special colors per-horizon,
    but for the checkbox legend we use neutral palette colors."""
    colors = {}
    for i, name in enumerate(model_names):
        colors[name] = _PALETTE[i % len(_PALETTE)]
    return colors


def _default_active_sizing(sizing_labels: list[str]) -> str:
    """Pick the initially-active sizing toggle for the GSVIVS table+chart.

    Production default is ``long_flat`` (walk-forward validated optimal in
    trial-062, threshold-aware). Falls back to ``binary`` (also
    threshold-aware), then ``asym_long L=2``, then first available label.
    """
    for preferred in ("[long_flat]", "[binary]", "[asym_long L=2]"):
        if preferred in sizing_labels:
            return preferred
    return sizing_labels[0] if sizing_labels else ""


def _sizing_mode_from_label(sizing_label: str) -> str:
    """Extract the sizing mode name from a sizing label like '[binary]' or '[zscore L=1]'."""
    stripped = sizing_label.strip("[]")
    return stripped.split()[0] if stripped else "binary"


def _discretize_signal(
    signal: list[float], sizing_mode: str
) -> tuple[list[int], list[str]]:
    """Discretize a signal series into integer state indices.

    Returns (state_indices, state_labels) where state_indices[i] is the
    index into state_labels for signal[i].
    """
    if sizing_mode in ("binary",):
        labels = ["Short", "Long"]
        states = [1 if v >= 0 else 0 for v in signal]
    elif sizing_mode in ("long_flat",):
        labels = ["Flat", "Long"]
        states = [1 if v > 0.5 else 0 for v in signal]
    elif sizing_mode == "asym_long":
        # asym_long output: -1 (short) or [+1, +max_leverage] (long).
        # Never produces values between -1 and +1.
        labels = ["Short", "Long \u00d71", "Long Lev"]
        states = []
        for v in signal:
            if v < 0:
                states.append(0)   # Short (-1)
            elif v <= 1.0:
                states.append(1)   # Long ×1 (base position)
            else:
                states.append(2)   # Long Lev (>1, leveraged)
    else:
        # zscore or any other continuous mode → 3 bins at ±0.5
        labels = ["Sell (< -0.5)", "Neutral", "Buy (> +0.5)"]
        states = []
        for v in signal:
            if v < -0.5:
                states.append(0)  # Short
            elif v > 0.5:
                states.append(2)  # Long
            else:
                states.append(1)  # Flat
    return states, labels


def _compute_transition_matrices(
    traces: list[dict],
    *,
    horizon: int,
    sizing_labels: list[str],
    model_ranks: dict[str, int] | None = None,
) -> dict[str, dict]:
    """Compute transition matrices from GSVIVS trace data.

    Returns a dict keyed by ``"{bare_model}|{sizing_label}|{horizon}"``
    with values ``{"labels": [...], "matrix": [[pct, ...], ...], "rank": int}``.
    """
    result: dict[str, dict] = {}
    for trace in traces:
        signal_y = trace.get("_signal_y", [])
        if len(signal_y) < 2:
            continue
        name = trace.get("name", "")
        sizing_label = trace.get("_sizing_label", "")
        if sizing_label and sizing_label not in sizing_labels:
            continue
        # Strip sizing suffix from trace name to get bare model name
        import re

        bare_name = re.sub(r"\s*\[[^\]]+\]\s*$", "", name)
        sizing_mode = _sizing_mode_from_label(sizing_label) if sizing_label else "binary"
        states, labels = _discretize_signal(signal_y, sizing_mode)
        n = len(labels)
        counts = [[0] * n for _ in range(n)]
        for i in range(len(states) - 1):
            counts[states[i]][states[i + 1]] += 1
        # Normalize rows to percentages
        matrix: list[list[float]] = []
        for row in counts:
            row_total = sum(row)
            if row_total > 0:
                matrix.append([round(c / row_total * 100, 1) for c in row])
            else:
                matrix.append([0.0] * n)
        key = f"{bare_name}|{sizing_label}|{horizon}"
        rank = model_ranks.get(bare_name, 999) if model_ranks else 999
        result[key] = {"labels": labels, "matrix": matrix, "rank": rank}
    return result


def _significance_stars(p_value: float) -> str:
    """Convert p-value to significance stars."""
    if p_value < 0.01:
        return "***"
    if p_value < 0.05:
        return "**"
    if p_value < 0.10:
        return "*"
    return ""


def _mz_label(p_value: float) -> str:
    """Convert MZ F-test p-value to Pass/Reject label."""
    if p_value < 0.05:
        return "Reject"
    return "Pass"


def _build_stats(
    tables: dict[int, pd.DataFrame],
    horizons: list[int],
    model_colors: dict[str, str],
) -> dict[int, list[dict]]:
    """Build per-horizon stats for the template."""
    stats: dict[int, list[dict]] = {}
    for h in horizons:
        df = tables[h]
        # Exclude baseline models — they only belong in the GSVIVS01 table
        df = df[~df["model"].str.startswith("[baseline]")].reset_index(drop=True)
        best = _best_model_for_horizon(df)
        worst = _worst_model_for_horizon(df)
        rows = []
        for rank, (_, row) in enumerate(df.iterrows(), 1):
            name = row["model"]
            css_class = ""
            if name == best:
                css_class = "best"
            elif name == worst:
                css_class = "worst"
            color = model_colors.get(name, "#888")
            if name == best:
                color = _COLOR_BEST
            elif name == worst:
                color = _COLOR_WORST

            # Statistical test fields (backward-compatible defaults)
            qlike_bps = float(row.get("qlike_bps", 0.0))
            dm_pvalue = float(row.get("dm_pvalue", 1.0))
            dm_stat = float(row.get("dm_stat", 0.0))
            mcs_included = bool(row.get("mcs_included", False))
            mcs_pvalue = float(row.get("mcs_pvalue", 0.0))
            mz_f_pvalue = float(row.get("mz_f_pvalue", 1.0))
            mz_alpha = float(row.get("mz_alpha", 0.0))
            mz_beta = float(row.get("mz_beta", 1.0))
            row_dict = {
                "rank": rank,
                "name": name,
                "qlike": float(row["qlike"]),
                "qlike_bps": qlike_bps,
                "r_squared": float(row.get("r_squared", 0)),
                "dm_stat": dm_stat,
                "dm_pvalue": dm_pvalue,
                "dm_stars": _significance_stars(dm_pvalue),
                "mcs_included": mcs_included,
                "mcs_pvalue": mcs_pvalue,
                "mz_label": _mz_label(mz_f_pvalue),
                "mz_alpha": mz_alpha,
                "mz_beta": mz_beta,
                "mz_f_pvalue": mz_f_pvalue,
                "mz_tooltip": f"α={mz_alpha:.4f}, β={mz_beta:.4f}, F p={mz_f_pvalue:.4f}",
                "css_class": css_class,
                "color": color,
            }
            rows.append(row_dict)
        stats[h] = rows
    return stats


def _build_vt_stats(
    tables: dict[int, pd.DataFrame],
    horizons: list[int],
    model_colors: dict[str, str],
) -> dict[int, list[dict]]:
    """Build per-horizon vol-targeting stats for the economic value table."""
    stats: dict[int, list[dict]] = {}
    for h in horizons:
        df = tables[h]
        if "vt_sharpe" not in df.columns:
            stats[h] = []
            continue
        # Exclude baseline models — they only belong in the GSVIVS01 table
        df = df[~df["model"].str.startswith("[baseline]")]
        # Sort by vt_sharpe descending (best Sharpe first)
        df_sorted = df.sort_values("vt_sharpe", ascending=False).reset_index(drop=True)
        rows = []
        for rank, (_, row) in enumerate(df_sorted.iterrows(), 1):
            name = row["model"]
            vt_sharpe = float(row.get("vt_sharpe", 0.0))
            vt_ann_ret = float(row.get("vt_ann_ret", 0.0)) if "vt_ann_ret" in row.index else None
            vt_ann_vol = float(row.get("vt_ann_vol", 0.0)) if "vt_ann_vol" in row.index else None
            vt_pnl = float(row.get("vt_pnl", 0.0)) if "vt_pnl" in row.index else None
            vt_max_dd = float(row.get("vt_max_dd", 0.0)) if "vt_max_dd" in row.index else None
            color = model_colors.get(name, "#888")
            css_class = ""
            if rank == 1:
                css_class = "best"
                color = _COLOR_BEST
            elif rank == len(df_sorted):
                css_class = "worst"
                color = _COLOR_WORST
            row_dict = {
                "rank": rank,
                "name": name,
                "vt_sharpe": vt_sharpe,
                "vt_ann_ret": vt_ann_ret,
                "vt_ann_vol": vt_ann_vol,
                "vt_pnl": vt_pnl,
                "vt_max_dd": vt_max_dd,
                "css_class": css_class,
                "color": color,
            }
            rows.append(row_dict)
        stats[h] = rows
    return stats


def _build_dh_stats(
    tables: dict[int, pd.DataFrame],
    horizons: list[int],
    model_colors: dict[str, str],
) -> dict[int, list[dict]]:
    """Build per-horizon delta-hedged straddle stats for the economic value table."""
    stats: dict[int, list[dict]] = {}
    for h in horizons:
        df = tables[h]
        if "dh_sharpe" not in df.columns:
            stats[h] = []
            continue
        # Exclude baseline models — they only belong in the GSVIVS01 table
        df = df[~df["model"].str.startswith("[baseline]")]
        # Sort by dh_sharpe descending (best Sharpe first)
        df_sorted = df.sort_values("dh_sharpe", ascending=False).reset_index(drop=True)
        rows = []
        for rank, (_, row) in enumerate(df_sorted.iterrows(), 1):
            name = row["model"]
            dh_sharpe = float(row.get("dh_sharpe", 0.0))
            dh_ann_ret = float(row.get("dh_ann_ret", 0.0)) if "dh_ann_ret" in row.index else None
            dh_ann_vol = float(row.get("dh_ann_vol", 0.0)) if "dh_ann_vol" in row.index else None
            dh_pnl = float(row.get("dh_pnl", 0.0)) if "dh_pnl" in row.index else None
            dh_max_dd = float(row.get("dh_max_dd", 0.0)) if "dh_max_dd" in row.index else None
            dh_hit_rate = float(row.get("dh_hit_rate", 0.0)) if "dh_hit_rate" in row.index else None
            color = model_colors.get(name, "#888")
            css_class = ""
            if name.startswith("[baseline]"):
                css_class = "baseline"
            elif rank == 1:
                css_class = "best"
                color = _COLOR_BEST
            elif rank == len(df_sorted):
                css_class = "worst"
                color = _COLOR_WORST
            row_dict = {
                "rank": rank,
                "name": name,
                "dh_sharpe": dh_sharpe,
                "dh_ann_ret": dh_ann_ret,
                "dh_ann_vol": dh_ann_vol,
                "dh_pnl": dh_pnl,
                "dh_max_dd": dh_max_dd,
                "dh_hit_rate": dh_hit_rate,
                "css_class": css_class,
                "color": color,
            }
            rows.append(row_dict)
        stats[h] = rows
    return stats


def _compute_divergence_dates(
    forecasts: dict[int, dict[str, pd.Series]],
    horizons: list[int],
    percentile: float = 95.0,
) -> dict[int, list[str]]:
    """Identify dates where model spread exceeds the given percentile.

    Returns dict of horizon -> list of ISO date strings.
    """
    result: dict[int, list[str]] = {}
    for h in horizons:
        h_forecasts = forecasts.get(h, {})
        if len(h_forecasts) < 2:
            result[h] = []
            continue

        # Align all predictions to a common index (normalize to DatetimeIndex)
        df = pd.DataFrame({k: v.set_axis(pd.DatetimeIndex(v.index)) for k, v in h_forecasts.items()})
        df = df.dropna()
        if df.empty:
            result[h] = []
            continue

        # Compute daily spread (max - min across models)
        spread = df.max(axis=1) - df.min(axis=1)
        threshold = np.percentile(spread.values, percentile)
        divergent_dates = spread[spread > threshold].index
        result[h] = [d.isoformat()[:10] for d in divergent_dates]

    return result


def _build_model_details(
    tables: dict[int, pd.DataFrame],
    horizons: list[int],
    model_colors: dict[str, str],
    *,
    model_configs: dict[str, dict] | None = None,
    feature_layers: list[str] | None = None,
    horizon_overrides: dict[int, dict] | None = None,
    feature_stack_config: dict | None = None,
    output_dir: str | Path | None = None,
    trained_models: dict[str, dict[int, object]] | None = None,
    explainability_results: dict | None = None,
) -> dict[int, dict[str, dict]]:
    """Build per-horizon, per-model detail metadata for the detail panel.

    Returns dict[horizon, dict[model_name, detail_dict]].
    """
    from volforecast.registry import MODEL_REGISTRY, ensure_registered
    from volforecast.evaluation._model_utils import resolve_model, feature_layers_for_model
    from volforecast.visualization.lineage import lineage_to_mermaid

    ensure_registered()

    details: dict[int, dict[str, dict]] = {}

    for h in horizons:
        df = tables[h]
        h_details: dict[str, dict] = {}

        for _, row in df.iterrows():
            name = row["model"]
            if name.startswith("[baseline]"):
                continue

            # Resolve model class and params
            registry_name, display_label, params = resolve_model(
                name, model_params=None, model_configs=model_configs
            )

            model_cls = MODEL_REGISTRY.get(registry_name)
            family = getattr(model_cls, "family", "unknown") if model_cls else "unknown"
            description = getattr(model_cls, "description", "") if model_cls else ""

            # Effective params: merge base params with horizon overrides
            effective_params = dict(params)
            if horizon_overrides and h in horizon_overrides:
                h_override = horizon_overrides[h]
                if "model" in h_override and "params" in h_override["model"]:
                    effective_params.update(h_override["model"]["params"])

            # Feature layers
            model_layers = feature_layers_for_model(registry_name)
            active_layers = feature_layers or ["har_core"]
            used_layers = [la for la in active_layers if la in model_layers or model_layers == ["har_core"]]
            if not used_layers:
                used_layers = model_layers

            # Lineage
            lineage = {"base_model": None, "feature_stack": None}
            base_model_name = effective_params.get("base_model")
            if base_model_name:
                base_cls = MODEL_REGISTRY.get(base_model_name)
                base_features = getattr(base_cls, "_FEATURES", []) if base_cls else []
                lineage["base_model"] = {
                    "name": base_model_name,
                    "family": getattr(base_cls, "family", "unknown") if base_cls else "unknown",
                    "description": getattr(base_cls, "description", "") if base_cls else "",
                    "features": base_features or [],
                }

            if feature_stack_config:
                model_cfg = (model_configs or {}).get(name, {})
                fs_outputs = model_cfg.get("feature_stack_outputs", feature_stack_config.get("outputs", []))
                lineage["feature_stack"] = {
                    "source_model": feature_stack_config.get("source_model", "lstm"),
                    "outputs": fs_outputs,
                    "sequence_features": feature_stack_config.get("sequences", {}).get("features", []),
                    "model_params": feature_stack_config.get("model_params", {}),
                }

            # Generate mermaid graph string
            mermaid_graph = lineage_to_mermaid(
                lineage,
                main_model_label=_format_model_label(registry_name, effective_params),
            )

            # Extract family_stats from trained model if available
            family_stats = _extract_family_stats(
                trained_models, name, h, family
            )

            # Resolve true family from trained model object when registry lookup
            # failed (e.g. model_configs aliases like "lgbm_hariv0dte_init")
            resolved_family = family
            if resolved_family == "unknown" and trained_models is not None:
                model_horizons = trained_models.get(name)
                if model_horizons:
                    model_obj = model_horizons.get(h)
                    if model_obj is not None:
                        resolved_family = getattr(model_obj, "family", family)

            # Merge explainability results (SHAP/ALE) into family_stats
            if explainability_results and name in explainability_results:
                explain_h = explainability_results[name].get(h)
                if explain_h:
                    if family_stats is None:
                        family_stats = {}
                    shap_data = explain_h.get("shap")
                    if shap_data is not None:
                        # SHAP summary bar chart data (ALL features)
                        family_stats["shap_summary"] = shap_data["summary"]["mean_abs_shap"]
                        # Beeswarm data: per-sample SHAP values + feature values (ALL features)
                        all_features = [n for n, _ in shap_data["summary"]["mean_abs_shap"]]
                        feat_indices = [
                            shap_data["feature_names"].index(f)
                            for f in all_features
                            if f in shap_data["feature_names"]
                        ]
                        family_stats["shap_beeswarm"] = {
                            "features": all_features,
                            "shap_values": shap_data["shap_values"][:, feat_indices].tolist(),
                            "feature_values": shap_data["feature_values"][:, feat_indices].tolist(),
                        }
                    ale_data = explain_h.get("ale")
                    if ale_data is not None:
                        family_stats["ale_curves"] = ale_data

            h_details[name] = {
                "family": resolved_family,
                "description": description,
                "effective_params": _sanitize_params(effective_params),
                "feature_layers": used_layers,
                "feature_columns": None,
                "n_features": None,
                "lineage": lineage,
                "lineage_mermaid": mermaid_graph,
                "family_stats": family_stats,
                "attribution": None,
            }

        details[h] = h_details

    return details


def _extract_family_stats(
    trained_models: dict[str, dict[int, object]] | None,
    model_name: str,
    horizon: int,
    family: str,
) -> dict | None:
    """Extract family_stats from a trained model object.

    Returns a dict suitable for the dashboard JS rendering, or None if
    the model is not available. Detects model type from object capabilities
    rather than relying solely on the family string (which may be "unknown"
    for model_configs aliases).
    """
    if trained_models is None:
        return None
    model_horizons = trained_models.get(model_name)
    if model_horizons is None:
        return None
    model = model_horizons.get(horizon)
    if model is None:
        return None

    # Detect model family from the object itself (handles "unknown" family)
    obj_family = getattr(model, "family", family)

    if obj_family == "lightgbm" or hasattr(model, "get_feature_importance"):
        # LightGBM: extract top-20 feature importance by gain
        stats: dict = {}
        if hasattr(model, "get_feature_importance"):
            importance = model.get_feature_importance(top_n=20)
            if importance:
                stats["importance_top20"] = importance
        # SHAP feature selection metadata (if model was SHAP-optimised)
        selection_meta = getattr(model, "_selection_metadata", None)
        if selection_meta:
            stats["shap_selection"] = selection_meta
        return stats if stats else None
    elif obj_family == "har" or hasattr(model, "coefficients_"):
        # HAR-family OLS: extract coefficients
        if hasattr(model, "summary"):
            coefficients = dict(model.summary)
            if coefficients:
                intercept = coefficients.pop("intercept", None)
                result: dict = {"coefficients": coefficients}
                if intercept is not None:
                    result["intercept"] = intercept
                return result
    elif obj_family == "lstm":
        # LSTM: extract architecture summary
        stats: dict = {}
        for attr in ("hidden_dim", "n_layers", "seq_len", "dropout", "attention"):
            val = getattr(model, attr, None)
            if val is not None:
                stats[attr] = val
        if stats:
            return stats

    return None


def _format_model_label(registry_name: str, params: dict) -> str:
    """Format a model name + key params for Mermaid node label."""
    if registry_name == "lightgbm":
        n_est = params.get("n_estimators", "")
        leaves = params.get("num_leaves", "")
        if n_est and leaves:
            return f"LightGBM<br/>{n_est} trees, {leaves} leaves"
        return "LightGBM"
    elif registry_name == "lstm":
        hidden = params.get("hidden_dim", "")
        layers = params.get("n_layers", "")
        if hidden and layers:
            return f"LSTM<br/>hidden={hidden}, {layers} layers"
        return "LSTM"
    else:
        return registry_name


def _sanitize_params(params: dict) -> dict:
    """Ensure all param values are JSON-serializable."""
    clean = {}
    for k, v in params.items():
        if isinstance(v, (str, int, float, bool, type(None))):
            clean[k] = v
        elif isinstance(v, (list, tuple)):
            clean[k] = list(v)
        elif isinstance(v, dict):
            clean[k] = _sanitize_params(v)
        else:
            clean[k] = str(v)
    return clean
