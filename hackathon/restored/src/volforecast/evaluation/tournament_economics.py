"""Economic enrichment of tournament tables.

Appends vol-targeting (VT) and delta-hedged straddle (DH) metrics — plus
naive DH baseline rows — to a stats-only tournament table produced by
`volforecast.evaluation.statistical_tests.tournament_table`.

Split from `statistical_tests.py` so the pure statistical core (QLIKE, MSE,
DM, MCS, MZ) has zero coupling to economic-value code.

Public API:
    enrich_tournament_economics(stats_table, predictions, y_true, ...) -> DataFrame

Usage:
    >>> from volforecast.evaluation.statistical_tests import tournament_table
    >>> from volforecast.evaluation.tournament_economics import enrich_tournament_economics
    >>> stats = tournament_table(preds, y_true, baseline="har", mcs_bootstrap=10_000)
    >>> table = enrich_tournament_economics(
    ...     stats, preds, y_true,
    ...     daily_returns=ret, symbol_lengths=lens,
    ...     implied_vol=iv, spot_prices=spot, dh_mode="realistic", horizon=1,
    ... )
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def enrich_tournament_economics(
    stats_table: pd.DataFrame,
    predictions: dict[str, np.ndarray],
    y_true: np.ndarray,
    *,
    daily_returns: np.ndarray | None = None,
    symbol_lengths: list[int] | None = None,
    implied_vol: np.ndarray | None = None,
    spot_prices: np.ndarray | None = None,
    dh_mode: str = "realistic",
    horizon: int = 1,
) -> pd.DataFrame:
    """Append vol-targeting / delta-hedged metrics to a stats tournament table.

    The input ``stats_table`` (from ``tournament_table``) is never mutated; a
    copy is returned with additional columns and, when DH args are provided,
    five naive baseline rows appended.

    Parameters
    ----------
    stats_table : pd.DataFrame
        Output of ``tournament_table`` (12 stats columns, one row per model,
        sorted by qlike ascending).
    predictions : dict[str, np.ndarray]
        Same predictions used to build ``stats_table`` (LOG space).
    y_true : np.ndarray
        True log(RV) values, aligned to predictions.
    daily_returns : np.ndarray, optional
        Daily simple returns aligned to predictions. Triggers VT metrics.
    symbol_lengths : list[int], optional
        Number of observations per symbol in concatenated arrays. Required
        for per-symbol PnL averaging. If None, all data treated as a single
        stream.
    implied_vol : np.ndarray, optional
        ATM implied volatility (annualized decimal). Together with
        ``spot_prices`` triggers DH metrics + naive DH baseline rows.
    spot_prices : np.ndarray, optional
        Underlying spot prices aligned to predictions.
    dh_mode : str
        ``"simple"``, ``"discrete"``, or ``"realistic"`` (default).
    horizon : int
        Forecast horizon; controls IV tenor selection.

    Returns
    -------
    pd.DataFrame
        Copy of ``stats_table`` with appended columns:
        - VT (if daily_returns): vt_sharpe, vt_pnl, vt_max_dd, vt_ann_ret, vt_ann_vol
        - DH (if implied_vol+spot_prices): dh_sharpe, dh_pnl, dh_max_dd,
          dh_hit_rate, dh_ann_ret, dh_ann_vol
        - Plus 5 ``[baseline] *`` rows when DH is active.
    """
    y_true = np.asarray(y_true, dtype=np.float64)
    df = stats_table.copy()

    if daily_returns is not None:
        df = _append_vt_metrics(df, predictions, daily_returns, symbol_lengths)

    if implied_vol is not None and spot_prices is not None:
        df = _append_dh_metrics(
            df,
            predictions,
            y_true,
            implied_vol,
            spot_prices,
            symbol_lengths,
            dh_mode,
            horizon,
        )
        df = _append_naive_dh_baselines(
            df,
            y_true,
            implied_vol,
            spot_prices,
            symbol_lengths,
            dh_mode,
            horizon,
        )

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Private helpers — moved verbatim from statistical_tests.tournament_table.
# Behavior must remain bit-identical to the legacy combined implementation;
# the corresponding golden parquets in tests/data/tournament_golden/ enforce this.
# ---------------------------------------------------------------------------


def _append_vt_metrics(
    df: pd.DataFrame,
    predictions: dict[str, np.ndarray],
    daily_returns: np.ndarray,
    symbol_lengths: list[int] | None,
) -> pd.DataFrame:
    """Append vol-targeting Sharpe + per-symbol cumulative PnL columns."""
    from volforecast.evaluation.economic_value import (
        compute_max_drawdown,
        vol_targeting_pnl,
        vol_targeting_sharpe,
    )

    daily_returns_arr = np.asarray(daily_returns, dtype=np.float64)

    if symbol_lengths is not None:
        boundaries = np.cumsum([0] + list(symbol_lengths))
    else:
        boundaries = np.array([0, len(daily_returns_arr)])

    vt_cols = {"vt_sharpe": [], "vt_pnl": [], "vt_max_dd": [], "vt_ann_ret": [], "vt_ann_vol": []}

    for name in df["model"].tolist():
        pred = np.asarray(predictions[name], dtype=np.float64)
        sharpe = vol_targeting_sharpe(pred, daily_returns_arr)
        sym_pnls = []
        sym_max_dds = []
        sym_ann_rets = []
        sym_ann_vols = []
        for i in range(len(boundaries) - 1):
            start, end = boundaries[i], boundaries[i + 1]
            sym_ret = daily_returns_arr[start:end]
            sym_pred = pred[start:end]
            ann_vol = np.sqrt(252.0 * np.exp(sym_pred))
            vt_ret = vol_targeting_pnl(sym_ret, ann_vol, target_vol=0.10, max_leverage=2.0)
            valid = ~np.isnan(vt_ret)
            if valid.any():
                vt_ret_clean = np.where(valid, vt_ret, 0.0)
                cum_wealth = np.cumprod(1.0 + vt_ret_clean)
                sym_pnls.append(float((cum_wealth[-1] - 1.0) * 100))
                sym_max_dds.append(compute_max_drawdown(cum_wealth) * 100)
                sym_ann_rets.append(float(np.mean(vt_ret_clean) * 252 * 100))
                sym_ann_vols.append(float(np.std(vt_ret_clean, ddof=1) * np.sqrt(252) * 100))
        vt_cols["vt_sharpe"].append(sharpe)
        vt_cols["vt_pnl"].append(float(np.mean(sym_pnls)) if sym_pnls else 0.0)
        vt_cols["vt_max_dd"].append(float(np.mean(sym_max_dds)) if sym_max_dds else 0.0)
        vt_cols["vt_ann_ret"].append(float(np.mean(sym_ann_rets)) if sym_ann_rets else 0.0)
        vt_cols["vt_ann_vol"].append(float(np.mean(sym_ann_vols)) if sym_ann_vols else 0.0)

    for col, vals in vt_cols.items():
        df[col] = vals
    return df


def _append_dh_metrics(
    df: pd.DataFrame,
    predictions: dict[str, np.ndarray],
    y_true: np.ndarray,
    implied_vol: np.ndarray,
    spot_prices: np.ndarray,
    symbol_lengths: list[int] | None,
    dh_mode: str,
    horizon: int,
) -> pd.DataFrame:
    """Append delta-hedged straddle metrics for each model row."""
    from volforecast.evaluation.economic_value import (
        compute_sharpe,
        delta_hedged_straddle_pnl,
        iv_rv_gap_signal,
        iv_tenor_for_horizon,
    )

    _, tenor_days_val = iv_tenor_for_horizon(horizon)

    iv_arr = np.asarray(implied_vol, dtype=np.float64)
    spot_arr = np.asarray(spot_prices, dtype=np.float64)
    actual_daily_var = np.exp(y_true)

    if symbol_lengths is not None:
        dh_boundaries = np.cumsum([0] + list(symbol_lengths))
    else:
        dh_boundaries = np.array([0, len(iv_arr)])

    dh_cols: dict[str, list[float]] = {
        "dh_sharpe": [],
        "dh_pnl": [],
        "dh_max_dd": [],
        "dh_hit_rate": [],
        "dh_ann_ret": [],
        "dh_ann_vol": [],
    }

    for name in df["model"].tolist():
        pred = np.asarray(predictions[name], dtype=np.float64)

        pooled_pnl_parts = []
        pooled_he_var_parts = []

        for i in range(len(dh_boundaries) - 1):
            start, end = dh_boundaries[i], dh_boundaries[i + 1]
            sym_iv = iv_arr[start:end]
            sym_spot = spot_arr[start:end]
            sym_rv = actual_daily_var[start:end]
            sym_pred = pred[start:end]

            valid_iv = ~np.isnan(sym_iv) & ~np.isnan(sym_spot)
            if valid_iv.sum() < 30:
                continue

            forecast_ann_vol = np.sqrt(252.0 * np.exp(sym_pred[valid_iv]))
            signal = iv_rv_gap_signal(sym_iv[valid_iv], forecast_ann_vol)

            sym_iv_v = sym_iv[valid_iv]
            sym_spot_v = sym_spot[valid_iv]

            if dh_mode == "simple":
                sym_pnl = delta_hedged_straddle_pnl(
                    signal,
                    sym_rv[valid_iv],
                    sym_iv_v,
                    sym_spot_v,
                    tenor_days=tenor_days_val,
                )
                sym_pnl = np.where(np.isnan(sym_pnl), 0.0, sym_pnl)
                pooled_pnl_parts.append(sym_pnl)
                from volforecast.evaluation.realistic_straddle import (
                    compute_hedge_error_variance,
                )

                T_val = tenor_days_val / 252.0
                iv_safe = np.maximum(sym_iv_v, 1e-8)
                gamma = 2.0 / (sym_spot_v * iv_safe * np.sqrt(T_val))
                he_var = compute_hedge_error_variance(
                    gamma,
                    sym_spot_v,
                    sym_iv_v,
                    kappa=4.0,
                    N=26,
                )
                pooled_he_var_parts.append(he_var * signal**2)
            elif dh_mode == "discrete":
                sym_pnl = delta_hedged_straddle_pnl(
                    signal,
                    sym_rv[valid_iv],
                    sym_iv_v,
                    sym_spot_v,
                    tenor_days=tenor_days_val,
                )
                T_val = tenor_days_val / 252.0
                iv_safe = np.maximum(sym_iv_v, 1e-8)
                gamma = 2.0 / (sym_spot_v * iv_safe * np.sqrt(T_val))
                dt_rebal = 1.0 / (252.0 * 26)
                sqrt_2_pi = np.sqrt(2.0 / np.pi)
                exp_abs_dd = gamma * sym_spot_v * iv_safe * np.sqrt(dt_rebal) * sqrt_2_pi
                hedge_cost = 26 * exp_abs_dd * sym_spot_v * (2.0 / 10000.0)
                hedge_cost_norm = hedge_cost / np.maximum(sym_spot_v, 1e-8)
                sym_pnl = sym_pnl - np.abs(signal) * hedge_cost_norm
                sym_pnl = np.where(np.isnan(sym_pnl), 0.0, sym_pnl)
                pooled_pnl_parts.append(sym_pnl)
                from volforecast.evaluation.realistic_straddle import (
                    compute_hedge_error_variance,
                )

                he_var = compute_hedge_error_variance(
                    gamma,
                    sym_spot_v,
                    sym_iv_v,
                    kappa=4.0,
                    N=26,
                )
                pooled_he_var_parts.append(he_var * signal**2)
            else:
                from volforecast.evaluation.realistic_straddle import _compute_signal
                from volforecast.evaluation.realistic_straddle import (
                    realistic_straddle_pnl as _rst_pnl,
                )

                sym_spot_v = sym_spot[valid_iv]
                sym_iv_v = sym_iv[valid_iv]
                delta_spot = np.zeros(len(sym_spot_v))
                delta_spot[1:] = np.diff(sym_spot_v)
                delta_iv = np.zeros(len(sym_iv_v))
                delta_iv[1:] = np.diff(sym_iv_v)

                sig = _compute_signal(
                    sym_iv_v,
                    forecast_ann_vol,
                    "difference",
                    "binary",
                    0.0,
                    63,
                    2.0,
                )
                rst_result = _rst_pnl(
                    signal=sig,
                    realized_var=sym_rv[valid_iv],
                    implied_vol=sym_iv_v,
                    spot_prices=sym_spot_v,
                    delta_spot=delta_spot,
                    delta_iv=delta_iv,
                    tenor_days=tenor_days_val,
                )
                sym_pnl = np.where(np.isnan(rst_result["pnl_net"]), 0.0, rst_result["pnl_net"])
                pooled_pnl_parts.append(sym_pnl)
                pooled_he_var_parts.append(rst_result["hedge_error_var"])

        if pooled_pnl_parts:
            pooled_pnl = np.concatenate(pooled_pnl_parts)

            if pooled_he_var_parts:
                pooled_he_var = np.concatenate(pooled_he_var_parts)
                observed_var = np.var(pooled_pnl, ddof=1)
                mean_he_var = float(np.mean(pooled_he_var))
                total_std = np.sqrt(observed_var + mean_he_var)
                mean_pnl = float(np.mean(pooled_pnl))
                dh_sharpe = (
                    float(mean_pnl / total_std * np.sqrt(252.0)) if total_std > 1e-12 else 0.0
                )
            else:
                dh_sharpe = compute_sharpe(pooled_pnl)

            sym_cum_pnls = []
            sym_max_dds = []
            for sym_pnl_arr in pooled_pnl_parts:
                cum_curve = np.cumsum(sym_pnl_arr)
                sym_cum_pnls.append(float(cum_curve[-1] * 100))
                peak = np.maximum.accumulate(cum_curve)
                sym_max_dds.append(float(np.min(cum_curve - peak) * 100))
            dh_pnl = float(np.mean(sym_cum_pnls))
            dh_max_dd = float(np.mean(sym_max_dds))

            active = pooled_pnl != 0.0
            dh_hit_rate = float(np.mean(pooled_pnl[active] > 0)) if active.any() else 0.0
            dh_ann_ret = float(np.mean(pooled_pnl) * 252 * 100)

            if pooled_he_var_parts:
                pooled_he_var = np.concatenate(pooled_he_var_parts)
                obs_var = np.var(pooled_pnl, ddof=1)
                dh_ann_vol = float(
                    np.sqrt(obs_var + float(np.mean(pooled_he_var))) * np.sqrt(252) * 100
                )
            else:
                dh_ann_vol = float(np.std(pooled_pnl, ddof=1) * np.sqrt(252) * 100)
        else:
            dh_sharpe = 0.0
            dh_pnl = 0.0
            dh_max_dd = 0.0
            dh_hit_rate = 0.0
            dh_ann_ret = 0.0
            dh_ann_vol = 0.0

        dh_cols["dh_sharpe"].append(dh_sharpe)
        dh_cols["dh_pnl"].append(dh_pnl)
        dh_cols["dh_max_dd"].append(dh_max_dd)
        dh_cols["dh_hit_rate"].append(dh_hit_rate)
        dh_cols["dh_ann_ret"].append(dh_ann_ret)
        dh_cols["dh_ann_vol"].append(dh_ann_vol)

    for col, vals in dh_cols.items():
        df[col] = vals
    return df


def _append_naive_dh_baselines(
    df: pd.DataFrame,
    y_true: np.ndarray,
    implied_vol: np.ndarray,
    spot_prices: np.ndarray,
    symbol_lengths: list[int] | None,
    dh_mode: str,
    horizon: int,
) -> pd.DataFrame:
    """Append 5 naive DH baseline rows: always_long/short/flat/random/random_no_flip."""
    from volforecast.evaluation.economic_value import (
        _compute_naive_pnl,
        _pnl_to_metrics,
        iv_tenor_for_horizon,
    )

    _, tenor_days_val = iv_tenor_for_horizon(horizon)

    iv_arr = np.asarray(implied_vol, dtype=np.float64)
    spot_arr = np.asarray(spot_prices, dtype=np.float64)
    actual_daily_var = np.exp(y_true)

    if symbol_lengths is not None:
        dh_boundaries = np.cumsum([0] + list(symbol_lengths))
    else:
        dh_boundaries = np.array([0, len(iv_arr)])

    baseline_pnl_parts: dict[str, list[np.ndarray]] = {}
    baseline_he_var_parts: dict[str, list[np.ndarray]] = {}
    baseline_signal_parts: dict[str, list[np.ndarray]] = {}

    for i in range(len(dh_boundaries) - 1):
        start, end = dh_boundaries[i], dh_boundaries[i + 1]
        sym_iv = iv_arr[start:end]
        sym_spot = spot_arr[start:end]
        sym_rv = actual_daily_var[start:end]

        valid_iv = ~np.isnan(sym_iv) & ~np.isnan(sym_spot)
        if valid_iv.sum() < 30:
            continue

        n_valid = int(valid_iv.sum())
        rng = np.random.default_rng(42)
        signals_map = {
            "always_long": np.ones(n_valid, dtype=np.float64),
            "always_short": np.full(n_valid, -1.0, dtype=np.float64),
            "always_flat": np.zeros(n_valid, dtype=np.float64),
            "random": rng.choice([-1.0, 1.0], size=n_valid),
        }

        for bname, sig in signals_map.items():
            pnl_clean, he_var = _compute_naive_pnl(
                sig,
                sym_rv[valid_iv],
                sym_iv[valid_iv],
                sym_spot[valid_iv],
                dh_mode,
                tenor_days=tenor_days_val,
            )
            baseline_pnl_parts.setdefault(bname, []).append(pnl_clean)
            baseline_signal_parts.setdefault(bname, []).append(sig)
            if he_var is not None:
                baseline_he_var_parts.setdefault(bname, []).append(he_var)

    if "always_long" in baseline_pnl_parts and "always_short" in baseline_pnl_parts:
        for long_pnl, short_pnl in zip(
            baseline_pnl_parts["always_long"], baseline_pnl_parts["always_short"]
        ):
            avg_pnl = 0.5 * (long_pnl + short_pnl)
            baseline_pnl_parts.setdefault("random_no_flip", []).append(avg_pnl)
            baseline_signal_parts.setdefault("random_no_flip", []).append(
                np.ones(len(avg_pnl), dtype=np.float64)
            )

    new_rows = []
    for bname in ["always_long", "always_short", "always_flat", "random", "random_no_flip"]:
        brow = {
            "model": f"[baseline] {bname}",
            "qlike": float("nan"),
            "qlike_bps": float("nan"),
            "mse": float("nan"),
            "r_squared": float("nan"),
            "mz_alpha": float("nan"),
            "mz_beta": float("nan"),
            "mz_f_pvalue": float("nan"),
            "dm_stat": float("nan"),
            "dm_pvalue": float("nan"),
            "mcs_included": False,
            "mcs_pvalue": float("nan"),
        }

        if bname in baseline_pnl_parts and baseline_pnl_parts[bname]:
            pnl_parts = baseline_pnl_parts[bname]
            pooled_pnl = np.concatenate(pnl_parts)
            pooled_signal = np.concatenate(baseline_signal_parts[bname])
            he_var = None
            if bname in baseline_he_var_parts and baseline_he_var_parts[bname]:
                he_var = np.concatenate(baseline_he_var_parts[bname])
            metrics = _pnl_to_metrics(
                pooled_pnl,
                pooled_signal,
                he_var,
                per_symbol_pnl_parts=pnl_parts,
            )
            for key in (
                "dh_sharpe",
                "dh_pnl",
                "dh_max_dd",
                "dh_hit_rate",
                "dh_ann_ret",
                "dh_ann_vol",
            ):
                brow[key] = metrics[key]
        else:
            for key in (
                "dh_sharpe",
                "dh_pnl",
                "dh_max_dd",
                "dh_hit_rate",
                "dh_ann_ret",
                "dh_ann_vol",
            ):
                brow[key] = 0.0

        new_rows.append(brow)

    baselines_df = pd.DataFrame(new_rows)
    return pd.concat([df, baselines_df], ignore_index=True)
