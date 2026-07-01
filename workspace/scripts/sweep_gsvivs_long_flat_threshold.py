"""Sweep long_flat threshold to find optimal Sharpe for GSVIVS01 strategy.

Approach
--------
1. Monkey-patch ``volforecast.evaluation.economic_value.kvar_rv_gap_signal`` and
   ``gsvivs_signal_pnl`` to capture (kvar, rv_forecast, gsvivs_index_levels)
   per model × horizon × IV-source during a trial-036 champion tournament run.
2. After the run, replay each capture through ``kvar_rv_sized_signal`` with
   sizing_mode="long_flat" at 21 threshold values spanning [-0.005, +0.050].
3. Write results to CSV and identify the optimal threshold.

For long_flat mode:
  - signal = +1 (short vol / collect premium) when gap >= -threshold
  - signal =  0 (flat / skip day)              when gap <  -threshold

So:
  - threshold > 0: more conservative (go flat even with slightly positive gap)
  - threshold < 0: more aggressive (only flat when strongly negative gap)
  - threshold = 0: flat only when gap < 0 (current default)

Run via: ``./vol bg python workspace/scripts/sweep_gsvivs_long_flat_threshold.py``
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

# Track the main process PID so atexit doesn't fire in multiprocessing workers
_MAIN_PID = os.getpid()

# ---- Configure paths ----
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# ---- Threshold grid (variance-space units) ----
THRESHOLDS: list[float] = sorted(set(
    list(np.arange(-0.005, 0.0, 0.001).round(4))
    + list(np.arange(0.0, 0.011, 0.001).round(4))
    + list(np.arange(0.015, 0.051, 0.005).round(4))
))

CONFIG_PATH = str(ROOT / "workspace" / "configs" / "trial_036_CHAMPION.yaml")
OUT_CSV = ROOT / "workspace" / "tmp" / "gsvivs_long_flat_threshold_sweep.csv"
OUT_PIVOT = ROOT / "workspace" / "tmp" / "gsvivs_long_flat_threshold_sweep_pivot.txt"

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

# ---- Storage for captured inputs ----
_captures: list[dict[str, Any]] = []

# ---- Apply monkey patches ----
from volforecast.evaluation import economic_value as ev  # noqa: E402

_orig_signal = ev.kvar_rv_gap_signal
_orig_sized_signal = ev.kvar_rv_sized_signal
_orig_pnl = ev.gsvivs_signal_pnl


def _pull_caller_context() -> dict[str, Any]:
    """Walk the stack and pull loop variables from _compute_gsvivs_stats."""
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


_last_signal_inputs: dict[str, Any] = {}


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


def _do_sweep_and_dump() -> None:
    """After the run, sweep thresholds with long_flat sizing and write CSV."""
    if os.getpid() != _MAIN_PID:
        return  # skip in multiprocessing workers
    if not _captures:
        print("[sweep-lf] no captures collected — nothing to sweep", flush=True)
        return

    rows: list[dict[str, Any]] = []
    for cap in _captures:
        for t in THRESHOLDS:
            # Generate long_flat signal at this threshold
            sig = _orig_sized_signal(
                cap["iv_arr"],
                cap["pred_arr"],
                sizing_mode="long_flat",
                space=cap["signal_space"],
                threshold=t,
                is_calendar_ann=cap["is_calendar_ann"],
            )
            m = _orig_pnl(cap["gsvivs_common"], sig)

            # Compute position stats
            n_total = len(sig)
            n_long = int(np.sum(sig > 0))
            n_flat = int(np.sum(sig == 0))
            position_rate_short_pct = n_long / n_total * 100  # "short vol" days

            rows.append(
                {
                    "model": cap["model"],
                    "iv_label": cap["iv_label"],
                    "h": cap["h"],
                    "sizing_mode": "long_flat",
                    "threshold": t,
                    "n_long": n_long,
                    "n_flat": n_flat,
                    "position_rate_pct": position_rate_short_pct,
                    **m,
                }
            )

        # Also compute binary at the config's default threshold for comparison
        sig_binary = _orig_signal(
            cap["iv_arr"],
            cap["pred_arr"],
            space=cap["signal_space"],
            threshold=cap["default_threshold"],
            is_calendar_ann=cap["is_calendar_ann"],
        )
        m_binary = _orig_pnl(cap["gsvivs_common"], sig_binary)
        rows.append(
            {
                "model": cap["model"],
                "iv_label": cap["iv_label"],
                "h": cap["h"],
                "sizing_mode": "binary (config default)",
                "threshold": cap["default_threshold"],
                "n_long": int(np.sum(sig_binary > 0)),
                "n_flat": 0,
                "position_rate_pct": float(np.sum(sig_binary > 0)) / len(sig_binary) * 100,
                **m_binary,
            }
        )

        # Always-short baseline (signal = +1 every day in GSVIVS01 terms)
        # gsvivs_signal_pnl expects signal of same length as index_levels
        sig_always = np.ones(len(cap["gsvivs_common"]), dtype=np.float64)
        m_always = _orig_pnl(cap["gsvivs_common"], sig_always)
        rows.append(
            {
                "model": cap["model"],
                "iv_label": cap["iv_label"],
                "h": cap["h"],
                "sizing_mode": "always_short (baseline)",
                "threshold": float("nan"),
                "n_long": len(sig_always),
                "n_flat": 0,
                "position_rate_pct": 100.0,
                **m_always,
            }
        )

    df = pd.DataFrame(rows)
    df.to_csv(OUT_CSV, index=False)
    print(f"[sweep-lf] wrote {len(df)} rows to {OUT_CSV}", flush=True)

    # Print focused pivot: lgbm_hariv0dte_init at h=1
    try:
        focus = df[
            (df["model"] == "lgbm_hariv0dte_init")
            & (df["h"] == 1)
            & (df["sizing_mode"] == "long_flat")
        ]
        if not focus.empty:
            pivot_sharpe = focus.pivot_table(
                index="iv_label",
                columns="threshold",
                values="sharpe_0rf",
                aggfunc="first",
            )
            pivot_pos = focus.pivot_table(
                index="iv_label",
                columns="threshold",
                values="position_rate_pct",
                aggfunc="first",
            )

            with open(OUT_PIVOT, "w") as f:
                f.write("=" * 72 + "\n")
                f.write("GSVIVS01 long_flat Threshold Sweep — lgbm_hariv0dte_init @ h=1\n")
                f.write("=" * 72 + "\n\n")

                f.write("=== Sharpe (0% RF) vs Threshold ===\n")
                f.write(pivot_sharpe.to_string())

                f.write("\n\n=== Position Rate (% days short vol) vs Threshold ===\n")
                f.write(pivot_pos.to_string())

                # Find optimal per IV label
                f.write("\n\n=== OPTIMAL THRESHOLD (max Sharpe per IV source) ===\n")
                for iv_label in focus["iv_label"].unique():
                    sub = focus[focus["iv_label"] == iv_label]
                    best_idx = sub["sharpe_0rf"].idxmax()
                    best = sub.loc[best_idx]
                    f.write(
                        f"  {iv_label}: threshold={best['threshold']:.4f}"
                        f"  Sharpe={best['sharpe_0rf']:.4f}"
                        f"  position_rate={best['position_rate_pct']:.1f}%\n"
                    )

                # Three-way comparison
                f.write("\n\n=== THREE-WAY COMPARISON (lgbm_hariv0dte_init, h=1) ===\n")
                all_models = df[
                    (df["model"] == "lgbm_hariv0dte_init") & (df["h"] == 1)
                ]
                for iv_label in all_models["iv_label"].unique():
                    f.write(f"\n  IV: {iv_label}\n")
                    sub = all_models[all_models["iv_label"] == iv_label]

                    # Best long_flat
                    lf = sub[sub["sizing_mode"] == "long_flat"]
                    if not lf.empty:
                        best_lf = lf.loc[lf["sharpe_0rf"].idxmax()]
                        f.write(
                            f"    long_flat(t={best_lf['threshold']:.4f}): "
                            f"Sharpe={best_lf['sharpe_0rf']:.4f}\n"
                        )

                    # Binary at config default
                    bn = sub[sub["sizing_mode"] == "binary (config default)"]
                    if not bn.empty:
                        f.write(
                            f"    binary(t={bn.iloc[0]['threshold']:.4f}): "
                            f"Sharpe={bn.iloc[0]['sharpe_0rf']:.4f}\n"
                        )

                    # Always short
                    al = sub[sub["sizing_mode"] == "always_short (baseline)"]
                    if not al.empty:
                        f.write(
                            f"    always_short: "
                            f"Sharpe={al.iloc[0]['sharpe_0rf']:.4f}\n"
                        )

            print(f"[sweep-lf] wrote pivot to {OUT_PIVOT}", flush=True)
            print("\n" + "=" * 72, flush=True)
            print("Sharpe vs Threshold (lgbm_hariv0dte_init @ h=1):", flush=True)
            print(pivot_sharpe.to_string(), flush=True)
            print("\nPosition Rate vs Threshold:", flush=True)
            print(pivot_pos.to_string(), flush=True)
    except Exception as e:
        print(f"[sweep-lf] pivot failed (non-fatal): {e}", flush=True)
        traceback.print_exc()


atexit.register(_do_sweep_and_dump)


def _safety_dump_on_crash(exc_type, exc_value, exc_tb):
    print("[sweep-lf] CRASH — dumping any captures collected so far", flush=True)
    traceback.print_exception(exc_type, exc_value, exc_tb)
    try:
        _do_sweep_and_dump()
    except Exception:
        traceback.print_exc()


sys.excepthook = _safety_dump_on_crash


# ---- Invoke the tournament ----
def main() -> int:
    print(f"[sweep-lf] long_flat threshold sweep on trial-036 champion", flush=True)
    print(f"[sweep-lf] config: {CONFIG_PATH}", flush=True)
    print(f"[sweep-lf] thresholds ({len(THRESHOLDS)}): {THRESHOLDS}", flush=True)
    print(f"[sweep-lf] cwd: {os.getcwd()}", flush=True)

    from volforecast.__main__ import main as vol_main

    return vol_main(["run", "--config", CONFIG_PATH, "--skip-ingest", "--force-retrain"])


if __name__ == "__main__":
    rc = main()
    print(f"[sweep-lf] vol main returned rc={rc}", flush=True)
    sys.exit(rc)
