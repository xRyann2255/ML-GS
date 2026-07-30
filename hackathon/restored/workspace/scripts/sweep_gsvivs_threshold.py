"""Sweep gsvivs_short_threshold over {0, 0.0005, 0.001, 0.002} (variance units) on trial-036 champion.

Approach
--------
1. Monkey-patch ``volforecast.evaluation.economic_value.kvar_rv_gap_signal`` and
   ``gsvivs_signal_pnl`` so each call captures (iv_arr, pred_arr, gsvivs_common)
   plus caller-frame context (model name, IV source label, horizon, signal space,
   is_calendar_ann).
2. Invoke ``volforecast.__main__.main(["run", "--config", <trial_036>, "--skip-ingest"])``.
3. After the run finishes, re-evaluate the captured inputs at every sweep threshold
   and write a CSV at ``workspace/tmp/gsvivs_threshold_sweep.csv``.

This is a one-shot research script. Predictions are not cached for trial-036,
so a full pooled tournament re-train is required to obtain the prediction arrays.

Run via: ``./vol bg python workspace/scripts/sweep_gsvivs_threshold.py``
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

# ---- Configure paths so the script can be launched from repo root ----
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# ---- Thresholds to sweep (variance-space units, gsvivs_signal_space='variance') ----
THRESHOLDS: list[float] = [0.0, 0.0005, 0.001, 0.002]
CONFIG_PATH = str(ROOT / "workspace" / "configs" / "trial_036_CHAMPION.yaml")
OUT_CSV = ROOT / "workspace" / "tmp" / "gsvivs_threshold_sweep.csv"
OUT_PIVOT = ROOT / "workspace" / "tmp" / "gsvivs_threshold_sweep_pivot.txt"

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

# ---- Storage for captured inputs ----
# Each entry: (model, iv_label, horizon, signal_space, is_cal_ann, iv_arr, pred_arr, gsvivs_common)
_captures: list[dict[str, Any]] = []

# ---- Apply monkey patches ----
from volforecast.evaluation import economic_value as ev  # noqa: E402

_orig_signal = ev.kvar_rv_gap_signal
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


# Per-call cache to glue signal() inputs to the following pnl() call
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
    """After the run, sweep thresholds across captures and write CSV."""
    if not _captures:
        print("[sweep] no captures collected — nothing to sweep", flush=True)
        return

    rows: list[dict[str, Any]] = []
    for cap in _captures:
        for t in THRESHOLDS:
            sig = _orig_signal(
                cap["iv_arr"],
                cap["pred_arr"],
                space=cap["signal_space"],
                threshold=t,
                is_calendar_ann=cap["is_calendar_ann"],
            )
            m = _orig_pnl(cap["gsvivs_common"], sig)
            rows.append(
                {
                    "model": cap["model"],
                    "iv_label": cap["iv_label"],
                    "h": cap["h"],
                    "threshold": t,
                    "default_threshold": cap["default_threshold"],
                    **m,
                }
            )

    df = pd.DataFrame(rows)
    df.to_csv(OUT_CSV, index=False)
    print(f"[sweep] wrote {len(df)} rows to {OUT_CSV}", flush=True)

    # Print a focused pivot: lgbm_hariv0dte_init at h=1, Sharpe vs threshold per iv_label
    try:
        focus = df[(df["model"] == "lgbm_hariv0dte_init") & (df["h"] == 1)]
        if not focus.empty:
            pivot = focus.pivot_table(
                index="iv_label",
                columns="threshold",
                values="sharpe_0rf",
                aggfunc="first",
            )
            with open(OUT_PIVOT, "w") as f:
                f.write("=== Sharpe (0% RF) — lgbm_hariv0dte_init @ h=1 ===\n")
                f.write(pivot.to_string())
                f.write("\n\n=== Precision — lgbm_hariv0dte_init @ h=1 ===\n")
                f.write(
                    focus.pivot_table(
                        index="iv_label",
                        columns="threshold",
                        values="precision",
                        aggfunc="first",
                    ).to_string()
                )
                f.write("\n\n=== F1 — lgbm_hariv0dte_init @ h=1 ===\n")
                f.write(
                    focus.pivot_table(
                        index="iv_label",
                        columns="threshold",
                        values="f1",
                        aggfunc="first",
                    ).to_string()
                )
                f.write("\n\n=== Annualized Return — lgbm_hariv0dte_init @ h=1 ===\n")
                f.write(
                    focus.pivot_table(
                        index="iv_label",
                        columns="threshold",
                        values="ann_return",
                        aggfunc="first",
                    ).to_string()
                )
            print(f"[sweep] wrote pivot to {OUT_PIVOT}", flush=True)
            print(pivot.to_string(), flush=True)
    except Exception as e:
        print(f"[sweep] pivot failed (non-fatal): {e}", flush=True)


atexit.register(_do_sweep_and_dump)


def _safety_dump_on_crash(exc_type, exc_value, exc_tb):
    print("[sweep] CRASH — dumping any captures collected so far", flush=True)
    traceback.print_exception(exc_type, exc_value, exc_tb)
    try:
        _do_sweep_and_dump()
    except Exception:
        traceback.print_exc()


sys.excepthook = _safety_dump_on_crash


# ---- Invoke the tournament ----
def main() -> int:
    print(f"[sweep] invoking trial-036 with monkey-patched signal/pnl", flush=True)
    print(f"[sweep] config: {CONFIG_PATH}", flush=True)
    print(f"[sweep] thresholds: {THRESHOLDS}", flush=True)
    print(f"[sweep] cwd: {os.getcwd()}", flush=True)

    from volforecast.__main__ import main as vol_main

    return vol_main(["run", "--config", CONFIG_PATH, "--skip-ingest", "--force-retrain"])


if __name__ == "__main__":
    rc = main()
    print(f"[sweep] vol main returned rc={rc}", flush=True)
    sys.exit(rc)
