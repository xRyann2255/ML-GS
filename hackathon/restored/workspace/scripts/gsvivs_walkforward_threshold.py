"""Walk-forward adaptive threshold for long_flat GSVIVS01 signal.

At each day t (after warm-up), find the threshold that maximized Sharpe on the
trailing window, then apply that threshold for day t+1. This eliminates the
look-ahead bias from the static sweep.

Comparison:
  - walk_forward: adaptive threshold recalibrated daily on trailing 252d window
  - no_threshold: long_flat with threshold=0 (flat only when gap < 0)
  - always_short: signal=+1 every day (baseline carry trade)

Run via: ./vol bg python <absolute_path_to_this_script>
"""

from __future__ import annotations

import atexit
import inspect
import os
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_MAIN_PID = os.getpid()

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# ---- Parameters ----
LOOKBACK = 252  # trailing window for threshold optimization (1 year)
THRESHOLD_GRID = np.round(np.arange(-0.005, 0.011, 0.001), 4)  # 16 candidates
CONFIG_PATH = str(ROOT / "workspace" / "configs" / "trial_036_CHAMPION.yaml")
OUT_CSV = ROOT / "workspace" / "tmp" / "gsvivs_walkforward_threshold.csv"
OUT_SUMMARY = ROOT / "workspace" / "tmp" / "gsvivs_walkforward_threshold_summary.txt"

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

# ---- Capture infrastructure (same as sweep script) ----
_captures: list[dict[str, Any]] = []

from volforecast.evaluation import economic_value as ev  # noqa: E402

_orig_signal = ev.kvar_rv_gap_signal
_orig_sized_signal = ev.kvar_rv_sized_signal
_orig_pnl = ev.gsvivs_signal_pnl

_last_signal_inputs: dict[str, Any] = {}


def _pull_caller_context() -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    for frame_info in inspect.stack()[1:8]:
        loc = frame_info.frame.f_locals
        if "m" in loc and isinstance(loc.get("m"), str) and "model" not in ctx:
            ctx["model"] = loc["m"]
        if "iv_label" in loc and "iv_label" not in ctx:
            ctx["iv_label"] = loc["iv_label"]
        if "h" in loc and isinstance(loc.get("h"), (int, np.integer)) and "h" not in ctx:
            ctx["h"] = int(loc["h"])
        if "is_cal_ann" in loc and "is_cal_ann" not in ctx:
            ctx["is_cal_ann"] = bool(loc["is_cal_ann"])
        if "signal_space" in loc and "signal_space" not in ctx:
            ctx["signal_space"] = loc["signal_space"]
    return ctx


def _patched_signal(kvar, rv_forecast, **kw):
    sig = _orig_signal(kvar, rv_forecast, **kw)
    _last_signal_inputs.clear()
    _last_signal_inputs["kvar"] = np.asarray(kvar, dtype=np.float64).copy()
    _last_signal_inputs["rv"] = np.asarray(rv_forecast, dtype=np.float64).copy()
    _last_signal_inputs["space"] = kw.get("space", "vol")
    _last_signal_inputs["threshold"] = kw.get("threshold", 0.0)
    _last_signal_inputs["is_calendar_ann"] = kw.get("is_calendar_ann", True)
    return sig


def _patched_pnl(index_levels, signal):
    metrics = _orig_pnl(index_levels, signal)
    if _last_signal_inputs:
        ctx = _pull_caller_context()
        _captures.append(
            {
                "model": ctx.get("model", "?"),
                "iv_label": ctx.get("iv_label", "?"),
                "h": ctx.get("h", -1),
                "signal_space": _last_signal_inputs["space"],
                "is_calendar_ann": _last_signal_inputs["is_calendar_ann"],
                "default_threshold": _last_signal_inputs["threshold"],
                "iv_arr": _last_signal_inputs["kvar"],
                "pred_arr": _last_signal_inputs["rv"],
                "gsvivs_common": np.asarray(index_levels, dtype=np.float64).copy(),
                "default_metrics": dict(metrics),
            }
        )
        _last_signal_inputs.clear()
    return metrics


ev.kvar_rv_gap_signal = _patched_signal
ev.gsvivs_signal_pnl = _patched_pnl


# ---- Walk-forward logic ----

def _compute_gap(kvar: np.ndarray, rv: np.ndarray, space: str, is_cal_ann: bool) -> np.ndarray:
    """Compute the Kvar-RV gap (same logic as kvar_rv_gap_signal)."""
    kvar = np.asarray(kvar, dtype=np.float64)
    rv = np.asarray(rv, dtype=np.float64)
    if is_cal_ann:
        cal_to_trading = np.sqrt(252.0 / 365.0)
        kvar_dec = kvar / 100.0 * cal_to_trading
    else:
        kvar_dec = kvar / 100.0
    if space == "variance":
        return kvar_dec**2 - rv**2
    return kvar_dec - rv


def _long_flat_signal(gap: np.ndarray, threshold: float) -> np.ndarray:
    """Generate long_flat signal: +1 when gap >= -threshold, 0 otherwise."""
    sig = np.ones(len(gap), dtype=np.float64)
    sig[gap < -threshold] = 0.0
    return sig


def _sharpe_from_signal(index_levels: np.ndarray, signal: np.ndarray) -> float:
    """Compute annualized Sharpe (0% RF) from signal and index levels.

    Convention: signal[t] determines position for the t→t+1 return.
    So len(signal) == len(index_levels) - 1 (signal aligns with returns).
    """
    daily_returns = index_levels[1:] / index_levels[:-1] - 1.0
    # signal should have same length as daily_returns
    daily_pnl = signal * daily_returns
    if len(daily_pnl) < 2 or np.std(daily_pnl) < 1e-12:
        return 0.0
    return float(np.mean(daily_pnl) / np.std(daily_pnl) * np.sqrt(252))


def _walk_forward_threshold(
    gap: np.ndarray,
    index_levels: np.ndarray,
    lookback: int,
    threshold_grid: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Walk-forward threshold selection.

    At each day t >= lookback, pick the threshold that maximized Sharpe on
    days [t-lookback, t), then apply for day t.

    Returns
    -------
    signal : np.ndarray
        The walk-forward adaptive signal (length = len(gap)).
    chosen_thresholds : np.ndarray
        The threshold chosen at each day (NaN for warm-up period).
    """
    n = len(gap)
    signal = np.full(n, np.nan, dtype=np.float64)
    chosen_thresholds = np.full(n, np.nan, dtype=np.float64)

    for t in range(lookback, n):
        # Trailing window: gap[t-lookback:t] has `lookback` elements
        # Returns need lookback+1 prices: index_levels[t-lookback:t+1]
        # Signal for returns: signal[i] * return[i→i+1], so signal has `lookback` elements
        window_gap = gap[t - lookback:t]
        window_idx = index_levels[t - lookback:t + 1]  # lookback+1 prices → lookback returns

        best_sharpe = -np.inf
        best_threshold = 0.0

        for thr in threshold_grid:
            sig_window = _long_flat_signal(window_gap, thr)
            sharpe = _sharpe_from_signal(window_idx, sig_window)
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_threshold = thr

        # Apply chosen threshold for day t
        chosen_thresholds[t] = best_threshold
        signal[t] = 1.0 if gap[t] >= -best_threshold else 0.0

    # Warm-up period: use threshold=0 (no lookahead, just the natural cutpoint)
    for t in range(lookback):
        signal[t] = 1.0 if gap[t] >= 0 else 0.0
        chosen_thresholds[t] = 0.0

    return signal, chosen_thresholds


def _do_walkforward() -> None:
    """After the run, compute walk-forward threshold and compare to baselines."""
    if os.getpid() != _MAIN_PID:
        return
    if not _captures:
        print("[wf] no captures collected — nothing to compute", flush=True)
        return

    rows: list[dict[str, Any]] = []
    summary_lines: list[str] = []

    summary_lines.append("=" * 72)
    summary_lines.append("GSVIVS01 Walk-Forward Threshold vs No-Threshold (long_flat)")
    summary_lines.append("=" * 72)
    summary_lines.append(f"Lookback: {LOOKBACK} trading days")
    summary_lines.append(f"Threshold grid: {THRESHOLD_GRID.tolist()}")
    summary_lines.append("")

    for cap in _captures:
        model = cap["model"]
        iv_label = cap["iv_label"]
        h = cap["h"]

        gap = _compute_gap(cap["iv_arr"], cap["pred_arr"], cap["signal_space"], cap["is_calendar_ann"])
        idx = cap["gsvivs_common"]

        # 1. Walk-forward adaptive threshold
        sig_wf, chosen_t = _walk_forward_threshold(gap, idx, LOOKBACK, THRESHOLD_GRID)
        # Evaluate only post-warmup period for fair comparison
        # sig_wf[t] is the signal for day t. PnL = sig[t] * return[t→t+1].
        # So we need idx[eval_start:] which has (n - eval_start) prices → (n - eval_start - 1) returns
        # And signal[eval_start:-1] to align with those returns.
        eval_start = LOOKBACK
        sig_wf_eval = sig_wf[eval_start:-1]  # signal for each return period
        idx_eval = idx[eval_start:]           # prices for computing returns

        sharpe_wf = _sharpe_from_signal(idx_eval, sig_wf_eval)
        n_long_wf = int(np.sum(sig_wf_eval > 0))
        n_flat_wf = int(np.sum(sig_wf_eval == 0))
        pos_rate_wf = n_long_wf / len(sig_wf_eval) * 100

        # Compute ann return and max DD for walk-forward
        daily_ret_wf = idx_eval[1:] / idx_eval[:-1] - 1.0  # len = n_eval_prices - 1 = len(sig_wf_eval)
        pnl_wf = sig_wf_eval * daily_ret_wf
        wealth_wf = np.cumprod(1.0 + pnl_wf)
        ann_ret_wf = float((wealth_wf[-1] ** (252 / len(pnl_wf)) - 1) * 100)
        max_dd_wf = float((wealth_wf / np.maximum.accumulate(wealth_wf) - 1).min() * 100)

        # 2. No-threshold baseline (threshold=0)
        sig_no_t = _long_flat_signal(gap, 0.0)
        sig_no_t_eval = sig_no_t[eval_start:-1]  # align with returns
        sharpe_no_t = _sharpe_from_signal(idx_eval, sig_no_t_eval)
        n_long_no_t = int(np.sum(sig_no_t_eval > 0))
        pos_rate_no_t = n_long_no_t / len(sig_no_t_eval) * 100

        pnl_no_t = sig_no_t_eval * daily_ret_wf
        wealth_no_t = np.cumprod(1.0 + pnl_no_t)
        ann_ret_no_t = float((wealth_no_t[-1] ** (252 / len(pnl_no_t)) - 1) * 100)
        max_dd_no_t = float((wealth_no_t / np.maximum.accumulate(wealth_no_t) - 1).min() * 100)

        # 3. Always-short baseline
        sig_always = np.ones(len(sig_wf_eval), dtype=np.float64)  # same length as returns
        sharpe_always = _sharpe_from_signal(idx_eval, sig_always)
        pnl_always = sig_always * daily_ret_wf
        wealth_always = np.cumprod(1.0 + pnl_always)
        ann_ret_always = float((wealth_always[-1] ** (252 / len(pnl_always)) - 1) * 100)
        max_dd_always = float((wealth_always / np.maximum.accumulate(wealth_always) - 1).min() * 100)

        # Threshold stability stats
        valid_t = chosen_t[eval_start:]
        t_mean = float(np.nanmean(valid_t))
        t_std = float(np.nanstd(valid_t))
        t_median = float(np.nanmedian(valid_t))

        # Record rows
        for label, sharpe, pos_rate, ann_ret, max_dd in [
            ("walk_forward", sharpe_wf, pos_rate_wf, ann_ret_wf, max_dd_wf),
            ("no_threshold (t=0)", sharpe_no_t, pos_rate_no_t, ann_ret_no_t, max_dd_no_t),
            ("always_short", sharpe_always, 100.0, ann_ret_always, max_dd_always),
        ]:
            rows.append({
                "model": model,
                "iv_label": iv_label,
                "h": h,
                "strategy": label,
                "sharpe_0rf": sharpe,
                "position_rate_pct": pos_rate,
                "ann_return_pct": ann_ret,
                "max_dd_pct": max_dd,
                "threshold_mean": t_mean if label == "walk_forward" else float("nan"),
                "threshold_std": t_std if label == "walk_forward" else float("nan"),
                "threshold_median": t_median if label == "walk_forward" else float("nan"),
                "eval_days": len(sig_wf_eval),
            })

        # Summary
        summary_lines.append(f"--- {model} | {iv_label} | h={h} ---")
        summary_lines.append(f"  Eval period: {len(sig_wf_eval)} days (post-{LOOKBACK}d warmup)")
        summary_lines.append(f"  {'Strategy':<25} {'Sharpe':>8} {'Pos%':>7} {'AnnRet%':>8} {'MaxDD%':>8}")
        summary_lines.append(f"  {'walk_forward':<25} {sharpe_wf:>8.4f} {pos_rate_wf:>6.1f}% {ann_ret_wf:>7.2f}% {max_dd_wf:>7.2f}%")
        summary_lines.append(f"  {'no_threshold (t=0)':<25} {sharpe_no_t:>8.4f} {pos_rate_no_t:>6.1f}% {ann_ret_no_t:>7.2f}% {max_dd_no_t:>7.2f}%")
        summary_lines.append(f"  {'always_short':<25} {sharpe_always:>8.4f} {'100.0':>6}% {ann_ret_always:>7.2f}% {max_dd_always:>7.2f}%")
        summary_lines.append(f"  Threshold stability: mean={t_mean:.4f} std={t_std:.4f} median={t_median:.4f}")
        summary_lines.append("")

    # Write outputs
    df = pd.DataFrame(rows)
    df.to_csv(OUT_CSV, index=False)
    print(f"[wf] wrote {len(df)} rows to {OUT_CSV}", flush=True)

    summary_text = "\n".join(summary_lines)
    with open(OUT_SUMMARY, "w") as f:
        f.write(summary_text)
    print(f"[wf] wrote summary to {OUT_SUMMARY}", flush=True)
    print(summary_text, flush=True)


atexit.register(_do_walkforward)


def _safety_dump(exc_type, exc_value, exc_tb):
    print("[wf] CRASH — dumping partial results", flush=True)
    traceback.print_exception(exc_type, exc_value, exc_tb)
    try:
        _do_walkforward()
    except Exception:
        traceback.print_exc()


sys.excepthook = _safety_dump


def main() -> int:
    print(f"[wf] walk-forward threshold on trial-036 champion", flush=True)
    print(f"[wf] config: {CONFIG_PATH}", flush=True)
    print(f"[wf] lookback: {LOOKBACK}, grid: {THRESHOLD_GRID.tolist()}", flush=True)

    from volforecast.__main__ import main as vol_main

    return vol_main(["run", "--config", CONFIG_PATH, "--skip-ingest", "--force-retrain"])


if __name__ == "__main__":
    rc = main()
    print(f"[wf] vol main returned rc={rc}", flush=True)
    sys.exit(rc)
