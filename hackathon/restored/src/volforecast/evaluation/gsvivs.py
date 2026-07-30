"""GSVIVS01 variance-swap signal computation.

Computes GSVIVS signal backtest statistics from model predictions and IV data.
Separated from tournament.py to isolate economic-value signal logic from
tournament orchestration.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

import numpy as np
import pandas as pd

from volforecast.evaluation.economic_value import (
    DEFAULT_GSVIVS_SIZING_SPECS,
    GsvivsSizingSpec,
    iv_tenor_for_horizon,
)

logger = logging.getLogger(__name__)


def default_gsvivs_dashboard_iv_label(
    stats_by_iv: dict[str, dict[int, list[dict]]],
) -> str | None:
    """Select the default IV source label for the GSVIVS dashboard tab."""
    preferred = "SPX AllDay Mark Kvar (09:10)"
    if preferred in stats_by_iv:
        return preferred
    # Fallback to exec kvar then first available
    if "Exec Kvar (true fill)" in stats_by_iv:
        return "Exec Kvar (true fill)"
    return next(iter(stats_by_iv), None)


# Registry mapping config keys to (dashboard_label, iv_data_column, is_calendar_annualized).
IV_SOURCE_REGISTRY: dict[str, tuple[str, str, bool]] = {
    "spx_allday_vols": ("SPX AllDay Mark Kvar (09:10)", "iv_allday_kvar", True),
    "spx_allday_vols_tc": ("SPX AllDay TC-adj Kvar (09:10)", "iv_allday_kvar_tc", True),
    "exec_kvar": ("Exec Kvar (true fill)", "iv_exec_kvar", True),
    "edrvs_prev_close_1dte": ("EDRVS prev-close 1-DTE", "iv_vs_0dte", True),
    "spx_atm_iv_1d": ("SPX ATM IV (1d)", "iv_0dte_atm", False),
    "spx_atm_iv_1w": ("SPX ATM IV (1w)", "iv_1w_atm", False),
}


def resolve_iv_sources(
    configured_keys: list[str] | None = None,
) -> list[tuple[str, str, bool]]:
    """Resolve config keys to (label, column, is_calendar_ann) tuples.

    Parameters
    ----------
    configured_keys : list of str, optional
        IV source keys from config. Defaults to ``["exec_kvar"]``.

    Returns
    -------
    list of (label, column_name, is_calendar_ann) tuples

    Raises
    ------
    ValueError
        If any key is not in the registry.
    """
    if configured_keys is None:
        configured_keys = ["spx_allday_vols"]
    result = []
    for key in configured_keys:
        if key not in IV_SOURCE_REGISTRY:
            raise ValueError(
                f"Unknown IV source key {key!r}. "
                f"Valid keys: {sorted(IV_SOURCE_REGISTRY)}"
            )
        result.append(IV_SOURCE_REGISTRY[key])
    return result


def compute_gsvivs_stats(
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
    signal_sizings: Iterable[GsvivsSizingSpec] | None = None,
    iv_sources: list[str] | None = None,
) -> tuple[dict[str, dict[int, list[dict]]], dict[str, dict[int, list[dict]]]]:
    """Compute GSVIVS01 signal backtest stats for multiple IV sources.

    For the iv_rv_gap signal type, computes stats using all available IV
    sources (Exec Kvar, EDRVS morning 1-DTE, EDRVS prev-close 1-DTE,
    SPX ATM IV 1w). Other signal types use a single IV source.

    Parameters
    ----------
    signal_sizings : iterable of GsvivsSizingSpec, optional
        Position-sizing variants to compute for the iv_rv_gap signal. Each
        spec emits one extra row per (IV source × horizon × model), with the
        spec's :attr:`~GsvivsSizingSpec.label` appended to the model name.
        Baseline rows are NOT duplicated. Defaults to
        :data:`DEFAULT_GSVIVS_SIZING_SPECS` (binary | asym_long L=2 |
        zscore L=1). Pass an empty iterable to skip sized variants entirely.

    Returns
    -------
    tuple of:
        stats: dict[iv_label, dict[horizon, list[row_dict]]]
        traces: dict[iv_label, dict[horizon, list[trace_dict]]]
    """
    from volforecast.data.edrvol import fetch_gsvivs_index, load_iv_cache
    from volforecast.evaluation.economic_value import (
        gsvivs_baseline_signals,
        gsvivs_baselines,
        gsvivs_signal_pnl,
        kvar_rv_sized_signal,
    )

    sizing_specs: tuple[GsvivsSizingSpec, ...] = (
        DEFAULT_GSVIVS_SIZING_SPECS if signal_sizings is None else tuple(signal_sizings)
    )

    # Load GSVIVS01 index
    try:
        gsvivs_index = fetch_gsvivs_index()
    except Exception:
        logger.warning("Could not load GSVIVS01 index, skipping GSVIVS stats")
        return {}, {}

    if gsvivs_index is None or len(gsvivs_index) < 30:
        return {}, {}

    # RV reference: prefer ES (GSVIVS hedge instrument), then SPX, then SPY
    ref_symbol: str | None = None
    for candidate in ("ES", "SPX", "SPY"):
        if candidate in symbols:
            ref_symbol = candidate
            break
    if ref_symbol is None:
        ref_symbol = symbols[0] if symbols else None
    if ref_symbol is None:
        return {}, {}

    # IV reference: always SPX (GSVIVS options settle on SPX), fallback to SPY
    iv_data = load_iv_cache("SPX")
    if iv_data is None:
        iv_data = load_iv_cache("SPY")
    if iv_data is None:
        logger.warning("No IV data for SPX or SPY, skipping GSVIVS stats")
        return {}, {}

    # Use per-symbol 0DTE IV for h=1 signal
    # iv_0dte is decimal (0.17 = 17%); convert to vol points for / 100.0 downstream
    iv_data = iv_data.copy()
    if "iv_0dte" in iv_data.columns:
        iv_data["iv_0dte_atm"] = iv_data["iv_0dte"] * 100.0

    # Load EDRVS 0DTE variance swap strike (correct IV for GSVIVS signal)
    from volforecast.data.edrvol import load_edrvs_cache

    edrvs_data = load_edrvs_cache()
    if edrvs_data is not None and not edrvs_data.empty:
        edrvs_data.index = pd.DatetimeIndex(edrvs_data.index.normalize(), dtype="datetime64[ns]")
        iv_data["iv_vs_0dte"] = edrvs_data.reindex(iv_data.index)

    # Load additional IV sources for multi-IV comparison
    from volforecast.data.edrvol import load_exec_kvar_cache

    exec_kvar_data = load_exec_kvar_cache()
    if exec_kvar_data is not None and not exec_kvar_data.empty:
        exec_kvar_data.index = pd.DatetimeIndex(
            exec_kvar_data.index.normalize(), dtype="datetime64[ns]"
        )
        iv_data["iv_exec_kvar"] = exec_kvar_data.reindex(iv_data.index)

    # Load SPX AllDay Vols mark Kvar (09:10 ET)
    from volforecast.data.spx_allday_vols import load_allday_cache

    allday_data = load_allday_cache()
    if allday_data is not None and not allday_data.empty and "kvar_vol_pct" in allday_data.columns:
        allday_series = allday_data["kvar_vol_pct"]
        allday_series.index = pd.DatetimeIndex(
            allday_series.index.normalize(), dtype="datetime64[ns]"
        )
        iv_data["iv_allday_kvar"] = allday_series.reindex(iv_data.index)

    # Compute TC-adjusted allday Kvar: mark - rolling_mean_20(mark - exec)
    if "iv_allday_kvar" in iv_data.columns and "iv_exec_kvar" in iv_data.columns:
        tc_gap = iv_data["iv_allday_kvar"] - iv_data["iv_exec_kvar"]
        tc_drag = tc_gap.rolling(20, min_periods=20).mean()
        iv_data["iv_allday_kvar_tc"] = iv_data["iv_allday_kvar"] - tc_drag
    else:
        iv_data["iv_allday_kvar_tc"] = np.nan

    # Normalize all indices to date-only (no time component) for intersection
    # Cast to ns resolution to ensure intersection works across different dtypes
    gsvivs_index = gsvivs_index.copy()
    gsvivs_index.index = pd.DatetimeIndex(gsvivs_index.index.normalize(), dtype="datetime64[ns]")
    iv_data.index = pd.DatetimeIndex(iv_data.index.normalize(), dtype="datetime64[ns]")

    # IV sources for the iv_rv_gap signal P&L computation.
    # Only Exec Kvar (true GSVIVS01 execution prices) is computed; the legacy
    # EDRVS morning / prev-close / SPX ATM variants were dropped from both the
    # dashboard and this computation since the project standardized on the
    # production metric. The iv_vs_0dte column is still loaded above because
    # iv_tenor_for_horizon(1) uses it for the Pass-1 valid-dates filter.
    # Each entry: (label, column_name, is_calendar_ann)
    _IV_SOURCES = resolve_iv_sources(iv_sources)

    results_by_iv: dict[str, dict[int, list[dict]]] = {}
    traces_by_iv: dict[str, dict[int, list[dict]]] = {}

    results: dict[int, list[dict]] = {}
    traces: dict[int, list[dict]] = {}

    for h in horizons:
        # Select IV column for this horizon.
        iv_col, _ = iv_tenor_for_horizon(h)
        if iv_col not in iv_data.columns:
            iv_col = "iv_1m_atm"  # fallback
        # For iv_acceleration signal: override iv_col to a column with full
        # coverage so valid_dates spans the entire GSVIVS period. The signal
        # logic handles NaN in iv_0dte internally (defaults to long).
        if signal_type == "iv_acceleration" and iv_col in ("iv_0dte_atm", "iv_vs_0dte"):
            iv_col = "iv_1w_atm" if "iv_1w_atm" in iv_data.columns else "iv_1m_atm"
        # Fallback: if the selected IV column has insufficient non-NaN coverage
        # in the GSVIVS period, try iv_0dte_atm then iv_1w_atm then iv_1m_atm.
        if iv_col in iv_data.columns:
            iv_in_gsvivs = iv_data[iv_col].loc[iv_data.index.intersection(gsvivs_index.index)]
            if iv_in_gsvivs.notna().sum() < 30:
                for fallback_col in ("iv_0dte_atm", "iv_1w_atm", "iv_1m_atm"):
                    if fallback_col in iv_data.columns and fallback_col != iv_col:
                        fb_check = iv_data[fallback_col].loc[
                            iv_data.index.intersection(gsvivs_index.index)
                        ]
                        if fb_check.notna().sum() >= 30:
                            logger.info(
                                "GSVIVS h=%d: %s has <30 non-NaN in period, falling back to %s",
                                h,
                                iv_col,
                                fallback_col,
                            )
                            iv_col = fallback_col
                            break
        if iv_col not in iv_data.columns:
            results[h] = []
            traces[h] = []
            continue

        model_rows: list[dict] = []
        h_traces: list[dict] = []

        # iv_acceleration is purely IV-based (no model predictions needed).
        # Compute it once over all GSVIVS dates where IV data exists.
        if signal_type == "iv_acceleration":
            # Dates where both GSVIVS and IV exist (no pred requirement)
            accel_idx = iv_data.index.intersection(gsvivs_index.index).sort_values()
            iv_aligned_accel = iv_data[iv_col].loc[accel_idx]
            accel_valid = ~iv_aligned_accel.isna()
            if accel_valid.sum() < 30:
                results[h] = []
                traces[h] = []
                continue
            accel_dates = accel_idx[accel_valid]

            # Build IV acceleration signal
            iv_0dte_col = "iv_0dte"
            if iv_0dte_col in iv_data.columns:
                iv_0dte_series = iv_data[iv_0dte_col].loc[accel_dates]
            else:
                iv_0dte_series = iv_data[iv_col].loc[accel_dates] / 100.0
            iv_0dte_arr = iv_0dte_series.values
            iv_5d_avg = pd.Series(iv_0dte_arr).rolling(5, min_periods=1).mean().values
            iv_accel = iv_0dte_arr - iv_5d_avg
            signal = np.ones(len(iv_accel), dtype=np.float64)
            for i in range(5, len(iv_accel)):
                if np.isnan(iv_accel[i]):
                    continue  # default long when iv_0dte unavailable
                hist = iv_accel[:i]
                thresh = np.nanpercentile(hist, flat_percentile)
                if np.isnan(thresh):
                    continue  # not enough history yet
                if iv_accel[i] > thresh:
                    signal[i] = -1.0  # go short (was flat)

            # GSVIVS levels for signal dates
            gsvivs_aligned = gsvivs_index.loc[accel_dates].values
            metrics = gsvivs_signal_pnl(gsvivs_aligned, signal)

            # Wealth curve
            daily_returns = gsvivs_aligned[1:] / gsvivs_aligned[:-1] - 1.0
            daily_pnl = signal[:-1] * daily_returns
            wealth = np.cumprod(1.0 + daily_pnl)
            trace_dates = [d.isoformat()[:10] for d in accel_dates[1:]]
            signal_dates_iso = [d.isoformat()[:10] for d in accel_dates]

            # Report same result for each model label (signal is model-independent)
            for m in models:
                model_rows.append({"name": m, "sizing_label": "", **metrics})
                h_traces.append(
                    {
                        "x": trace_dates,
                        "y": wealth.tolist(),
                        "mode": "lines",
                        "name": m,
                        "line": {"width": 1.5},
                        "hovertemplate": f"%{{x|%Y-%m-%d}}<br>{m}: %{{y:.4f}}<extra></extra>",
                        "_signal_x": signal_dates_iso,
                        "_signal_y": signal.tolist(),
                        "_sizing_label": "",
                    }
                )

            # Baselines over the SAME dates as the signal
            baseline_levels = gsvivs_aligned
            bl_results = gsvivs_baselines(baseline_levels)
            bl_signals = gsvivs_baseline_signals(len(baseline_levels))
            bl_returns = baseline_levels[1:] / baseline_levels[:-1] - 1.0
            bl_dates = trace_dates
            for bl_name, bl_metrics in bl_results.items():
                model_rows.append(
                    {"name": f"[baseline] {bl_name}", "sizing_label": "", **bl_metrics}
                )
                bl_signal = bl_signals[bl_name]
                bl_pnl = bl_signal[:-1] * bl_returns
                bl_wealth = np.cumprod(1.0 + bl_pnl)
                h_traces.append(
                    {
                        "x": bl_dates,
                        "y": bl_wealth.tolist(),
                        "mode": "lines",
                        "name": f"[baseline] {bl_name}",
                        "line": {"width": 1.5, "dash": "dash"},
                        "hovertemplate": (
                            f"%{{x|%Y-%m-%d}}<br>[baseline] {bl_name}: %{{y:.4f}}<extra></extra>"
                        ),
                        "_signal_x": signal_dates_iso,
                        "_signal_y": np.asarray(bl_signal, dtype=float).tolist(),
                        "_sizing_label": "",
                    }
                )

            # Sort by Sharpe descending
            model_rows.sort(key=lambda r: r.get("sharpe_0rf", 0.0), reverse=True)
            results[h] = model_rows
            traces[h] = h_traces
            continue  # skip the per-model loop below

        # classifier signal type: trains a LightGBM binary classifier on
        # GSVIVS01 down-days using IV-derived features (walk-forward).
        if signal_type == "classifier":
            from volforecast.models.gsvivs_classifier import (
                GsvivsDrawdownClassifier,
                build_gsvivs_classification_target,
            )

            # Build feature matrix from IV data aligned to GSVIVS dates
            clf_dates = iv_data.index.intersection(gsvivs_index.index).sort_values()
            if len(clf_dates) < 60:
                results[h] = model_rows
                traces[h] = h_traces
                continue

            # Features: IV levels, changes, and momentum
            clf_features = pd.DataFrame(index=clf_dates)
            for col in iv_data.columns:
                clf_features[col] = iv_data[col].loc[clf_dates]
            # Add 1d/5d changes for key IV columns
            for col in ("iv_1m_atm", "iv_1w_atm", "iv_0dte"):
                if col in iv_data.columns:
                    series = iv_data[col].loc[clf_dates]
                    clf_features[f"{col}_d1"] = series.diff(1)
                    clf_features[f"{col}_d5"] = series.diff(5)
            # Add GSVIVS01 recent returns as features
            gsvivs_aligned = gsvivs_index.loc[clf_dates]
            clf_features["gsvivs_ret_1d"] = gsvivs_aligned.pct_change(1)
            clf_features["gsvivs_ret_5d"] = gsvivs_aligned.pct_change(5)

            # Target: next-day GSVIVS01 down
            target = build_gsvivs_classification_target(gsvivs_aligned)
            # Align features to target (drop last row)
            clf_features = clf_features.iloc[:-1]
            clf_dates_eval = clf_dates[:-1]

            # Walk-forward: train on first min_train days, retrain every retrain_freq
            min_train = 126  # 6 months minimum
            retrain_freq = 63  # retrain quarterly
            threshold = short_threshold  # reuse threshold param for classifier

            signal = np.full(len(clf_dates_eval), np.nan)
            clf = None
            last_train_idx = 0

            for i in range(min_train, len(clf_dates_eval)):
                # Retrain periodically
                if clf is None or (i - last_train_idx) >= retrain_freq:
                    X_train = clf_features.iloc[:i]
                    y_train = target.iloc[:i]
                    # Drop rows with NaN features for training
                    valid = X_train.notna().all(axis=1) & y_train.notna()
                    clf = GsvivsDrawdownClassifier(
                        threshold=threshold,
                        scale_pos_weight=0.5,
                        n_estimators=1000,
                        early_stopping_rounds=50,
                        val_fraction=0.15,
                    )
                    clf.fit(X_train.loc[valid], y_train.loc[valid])
                    last_train_idx = i

                # Predict for day i
                X_pred = clf_features.iloc[[i]]
                if X_pred.isna().all(axis=1).iloc[0]:
                    signal[i] = 1.0  # default long if no features
                else:
                    signal[i] = clf.predict_signal(X_pred)[0]

            # Trim to valid predictions only
            valid_mask = ~np.isnan(signal)
            eval_dates = clf_dates_eval[valid_mask]
            signal_valid = signal[valid_mask]
            gsvivs_eval = gsvivs_index.loc[eval_dates].values

            if len(eval_dates) < 30:
                results[h] = model_rows
                traces[h] = h_traces
                continue

            # Compute metrics
            metrics = gsvivs_signal_pnl(gsvivs_eval, signal_valid)
            model_rows.append({"name": "classifier", "sizing_label": "", **metrics})

            # Wealth curve
            daily_returns = gsvivs_eval[1:] / gsvivs_eval[:-1] - 1.0
            daily_pnl = signal_valid[:-1] * daily_returns
            wealth = np.cumprod(1.0 + daily_pnl)
            trace_dates = [d.isoformat()[:10] for d in eval_dates[1:]]
            signal_dates_iso = [d.isoformat()[:10] for d in eval_dates]
            h_traces.append(
                {
                    "x": trace_dates,
                    "y": wealth.tolist(),
                    "mode": "lines",
                    "name": "classifier",
                    "line": {"width": 2.0},
                    "hovertemplate": "%{x|%Y-%m-%d}<br>classifier: %{y:.4f}<extra></extra>",
                    "_signal_x": signal_dates_iso,
                    "_signal_y": signal_valid.tolist(),
                    "_sizing_label": "",
                }
            )

            # Add baselines on the same dates
            bl_results = gsvivs_baselines(gsvivs_eval)
            bl_signals = gsvivs_baseline_signals(len(gsvivs_eval))
            bl_returns = daily_returns
            bl_dates = trace_dates
            for bl_name, bl_metrics in bl_results.items():
                model_rows.append(
                    {"name": f"[baseline] {bl_name}", "sizing_label": "", **bl_metrics}
                )
                bl_signal = bl_signals[bl_name]
                bl_pnl = bl_signal[:-1] * bl_returns
                bl_wealth = np.cumprod(1.0 + bl_pnl)
                h_traces.append(
                    {
                        "x": bl_dates,
                        "y": bl_wealth.tolist(),
                        "mode": "lines",
                        "name": f"[baseline] {bl_name}",
                        "line": {"width": 1.5, "dash": "dash"},
                        "hovertemplate": (
                            f"%{{x|%Y-%m-%d}}<br>[baseline] {bl_name}: %{{y:.4f}}<extra></extra>"
                        ),
                        "_signal_x": signal_dates_iso,
                        "_signal_y": np.asarray(bl_signal, dtype=float).tolist(),
                        "_sizing_label": "",
                    }
                )

            model_rows.sort(key=lambda r: r.get("sharpe_0rf", 0.0), reverse=True)
            results[h] = model_rows
            traces[h] = h_traces
            continue

        # --- Two-pass approach: ensures models and baselines use identical dates ---
        # Pass 1: collect valid_dates per model
        model_valid_dates: dict[str, pd.DatetimeIndex] = {}
        for m in models:
            if (m, ref_symbol, h) not in all_preds_series:
                continue
            preds = all_preds_series[(m, ref_symbol, h)].copy()
            if not isinstance(preds.index, pd.DatetimeIndex):
                preds.index = pd.DatetimeIndex(preds.index)
            preds.index = pd.DatetimeIndex(preds.index.normalize(), dtype="datetime64[ns]")
            common_idx = preds.index.intersection(iv_data.index).intersection(gsvivs_index.index)
            if len(common_idx) < 30:
                continue
            common_idx = common_idx.sort_values()
            iv_aligned_check = iv_data[iv_col].loc[common_idx]
            pred_aligned_check = preds.loc[common_idx]
            valid = ~iv_aligned_check.isna() & ~pred_aligned_check.isna()
            if valid.sum() < 30:
                continue
            model_valid_dates[m] = common_idx[valid]

        # Compute intersection of all models' dates (Fix 1 + Fix 2)
        if model_valid_dates:
            date_sets = [set(d.tolist()) for d in model_valid_dates.values()]
            common_set = date_sets[0]
            for s in date_sets[1:]:
                common_set &= s
            common_eval_dates = pd.DatetimeIndex(sorted(common_set), dtype="datetime64[ns]")
        else:
            common_eval_dates = pd.DatetimeIndex([], dtype="datetime64[ns]")

        if len(common_eval_dates) < 30:
            results[h] = model_rows
            traces[h] = h_traces
            continue

        # Pass 2: evaluate all models on the common intersection dates
        gsvivs_common = gsvivs_index.loc[common_eval_dates].values

        # Evaluate each IV source independently
        for iv_label, iv_col_name, is_cal_ann in _IV_SOURCES:
            if iv_col_name not in iv_data.columns:
                continue
            iv_series = iv_data[iv_col_name].loc[common_eval_dates]
            # Skip if too few valid IV values on these dates
            if iv_series.notna().sum() < 30:
                continue

            iv_arr = iv_series.values
            iv_model_rows: list[dict] = []
            iv_h_traces: list[dict] = []

            for m in model_valid_dates:
                preds = all_preds_series[(m, ref_symbol, h)].copy()
                if not isinstance(preds.index, pd.DatetimeIndex):
                    preds.index = pd.DatetimeIndex(preds.index)
                preds.index = pd.DatetimeIndex(preds.index.normalize(), dtype="datetime64[ns]")
                pred_arr = np.sqrt(np.exp(preds.loc[common_eval_dates].values) * 252)

                # Emit one row per sizing spec (binary | asym_long | zscore by
                # default). The spec label is appended to the model name so the
                # dashboard table shows the toggle inline (e.g. "har [binary]",
                # "har [asym_long L=2]", "har [zscore L=1]").
                for spec in sizing_specs:
                    signal = kvar_rv_sized_signal(
                        iv_arr,
                        pred_arr,
                        sizing_mode=spec.mode,
                        space=signal_space,
                        threshold=short_threshold,
                        is_calendar_ann=is_cal_ann,
                        max_leverage=spec.max_leverage,
                        lookback=spec.lookback,
                    )

                    row_name = f"{m} {spec.label}"
                    metrics = gsvivs_signal_pnl(gsvivs_common, signal)
                    iv_model_rows.append(
                        {"name": row_name, "sizing_label": spec.label, **metrics}
                    )

                    daily_returns = gsvivs_common[1:] / gsvivs_common[:-1] - 1.0
                    daily_pnl = signal[:-1] * daily_returns
                    wealth = np.cumprod(1.0 + daily_pnl)
                    trace_dates = [d.isoformat()[:10] for d in common_eval_dates[1:]]
                    signal_dates_iso = [d.isoformat()[:10] for d in common_eval_dates]
                    iv_h_traces.append(
                        {
                            "x": trace_dates,
                            "y": wealth.tolist(),
                            "mode": "lines",
                            "name": row_name,
                            "line": {"width": 1.5},
                            "hovertemplate": (
                                f"%{{x|%Y-%m-%d}}<br>{row_name}: %{{y:.4f}}<extra></extra>"
                            ),
                            "_signal_x": signal_dates_iso,
                            "_signal_y": signal.tolist(),
                            "_sizing_label": spec.label,
                        }
                    )

            # Baselines (same for all IV sources — they don't use IV)
            if iv_model_rows:
                bl_results = gsvivs_baselines(gsvivs_common)
                bl_signals = gsvivs_baseline_signals(len(gsvivs_common))
                bl_returns = gsvivs_common[1:] / gsvivs_common[:-1] - 1.0
                bl_dates = [d.isoformat()[:10] for d in common_eval_dates[1:]]
                bl_signal_dates_iso = [d.isoformat()[:10] for d in common_eval_dates]
                for bl_name, bl_metrics in bl_results.items():
                    iv_model_rows.append(
                        {"name": f"[baseline] {bl_name}", "sizing_label": "", **bl_metrics}
                    )
                    bl_signal = bl_signals[bl_name]
                    bl_pnl = bl_signal[:-1] * bl_returns
                    bl_wealth = np.cumprod(1.0 + bl_pnl)
                    iv_h_traces.append(
                        {
                            "x": bl_dates,
                            "y": bl_wealth.tolist(),
                            "mode": "lines",
                            "name": f"[baseline] {bl_name}",
                            "line": {"width": 1.5, "dash": "dash"},
                            "hovertemplate": (
                                f"%{{x|%Y-%m-%d}}<br>[baseline] {bl_name}: "
                                "%{y:.4f}<extra></extra>"
                            ),
                            "_signal_x": bl_signal_dates_iso,
                            "_signal_y": np.asarray(bl_signal, dtype=float).tolist(),
                            "_sizing_label": "",
                        }
                    )

            iv_model_rows.sort(key=lambda r: r.get("sharpe_0rf", 0.0), reverse=True)
            if iv_label not in results_by_iv:
                results_by_iv[iv_label] = {}
                traces_by_iv[iv_label] = {}
            results_by_iv[iv_label][h] = iv_model_rows
            traces_by_iv[iv_label][h] = iv_h_traces

        # Also store the default (first available) IV source in the flat results
        # for backward-compat with iv_acceleration/classifier paths
        default_iv_label = default_gsvivs_dashboard_iv_label(results_by_iv)
        if default_iv_label is not None and h in results_by_iv.get(default_iv_label, {}):
            results[h] = results_by_iv[default_iv_label][h]
            traces[h] = traces_by_iv[default_iv_label][h]
        else:
            results[h] = model_rows
            traces[h] = h_traces

    # For non-iv_rv_gap signal types, wrap the flat results under a default key
    # For non-iv_rv_gap signal types (iv_acceleration, classifier), wrap the
    # flat results under the Exec Kvar label so the dashboard's
    # default_gsvivs_dashboard_iv_label() selector still finds them.
    if signal_type != "iv_rv_gap" or not results_by_iv:
        default_label = "Exec Kvar (true fill)"
        results_by_iv[default_label] = results
        traces_by_iv[default_label] = traces

    return results_by_iv, traces_by_iv
