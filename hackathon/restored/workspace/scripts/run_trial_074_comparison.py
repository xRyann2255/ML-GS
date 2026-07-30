"""Trial-074: LSTM vs XGBoost apples-to-apples comparison.

Runs both models with identical CV (train_size=2200, test_size=252)
on the same universe [SPY, AAPL], ensuring same OOS dates.
Reports QLIKE for both + Diebold-Mariano test.

Usage: ./vol shell ../workspace/scripts/run_trial_074_comparison.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from volforecast.config import ExperimentConfig
from volforecast.pipeline.runner import Pipeline
from volforecast.utils.paths import rv_cache_path


def qlike(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Compute QLIKE loss: mean(actual/predicted - log(actual/predicted) - 1)."""
    ratio = actual / predicted
    return float(np.mean(ratio - np.log(ratio) - 1))


def diebold_mariano(loss1: np.ndarray, loss2: np.ndarray) -> tuple[float, float]:
    """Two-sided DM test. Returns (stat, p_value)."""
    from scipy import stats

    d = loss1 - loss2
    n = len(d)
    d_mean = d.mean()
    # HAC variance (Newey-West with bandwidth ~ n^(1/3))
    bw = max(1, int(n ** (1 / 3)))
    gamma_0 = np.var(d, ddof=1)
    gamma_sum = 0.0
    for k in range(1, bw + 1):
        gamma_k = np.cov(d[k:], d[:-k], ddof=1)[0, 1]
        gamma_sum += 2 * (1 - k / (bw + 1)) * gamma_k
    var_d = (gamma_0 + gamma_sum) / n
    if var_d <= 0:
        return 0.0, 1.0
    dm_stat = d_mean / np.sqrt(var_d)
    p_value = 2 * (1 - stats.norm.cdf(abs(dm_stat)))
    return float(dm_stat), float(p_value)


def qlike_losses(actual: np.ndarray, predicted: np.ndarray) -> np.ndarray:
    """Per-observation QLIKE losses."""
    ratio = actual / predicted
    return ratio - np.log(ratio) - 1


def main() -> None:
    configs_dir = Path(__file__).resolve().parent.parent / "configs"
    output_dir = Path(__file__).resolve().parent.parent / "tmp"
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Load panel data ---
    symbols = [
        "SPY", "AAPL", "MSFT", "NVDA", "AVGO", "GOOGL", "AMZN",
        "V", "MA", "XOM", "PG", "JNJ", "HD", "NFLX",
        "TSLA", "CRM", "UNH", "BAC", "ADBE", "IWM", "DIA",
    ]
    panel_data: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        path = rv_cache_path(sym)
        if not path.exists():
            print(f"ERROR: No data for {sym} at {path}")
            sys.exit(1)
        panel_data[sym] = pd.read_parquet(path)
    print(f"Loaded panel data: {', '.join(symbols)}")
    for sym, df in panel_data.items():
        first = df.index[0]
        last = df.index[-1]
        d0 = first.date() if hasattr(first, 'date') and callable(first.date) else first
        d1 = last.date() if hasattr(last, 'date') and callable(last.date) else last
        print(f"  {sym}: {len(df)} rows, {d0} to {d1}")

    # --- Run XGBoost ---
    print("\n" + "=" * 60)
    print("Running XGBoost (trial-067 architecture, single fold)...")
    print("=" * 60)
    xgb_config = ExperimentConfig.from_yaml(configs_dir / "trial_074_xgb_maxwin_h1.yaml")
    xgb_pipeline = Pipeline(xgb_config)
    t0 = time.time()
    xgb_results = xgb_pipeline.run_pooled(panel_data)
    xgb_time = time.time() - t0
    print(f"XGBoost done in {xgb_time:.1f}s")

    # --- Run LSTM ---
    print("\n" + "=" * 60)
    print("Running LSTM (trial-073 architecture, train_size=2200)...")
    print("=" * 60)
    lstm_config = ExperimentConfig.from_yaml(configs_dir / "trial_074_lstm_maxwin_h1.yaml")
    lstm_pipeline = Pipeline(lstm_config)
    t0 = time.time()
    lstm_results = lstm_pipeline.run_pooled(panel_data)
    lstm_time = time.time() - t0
    print(f"LSTM done in {lstm_time:.1f}s")

    # --- Compare on same OOS dates ---
    print("\n" + "=" * 60)
    print("COMPARISON (h=1, same OOS dates)")
    print("=" * 60)

    h = 1
    xgb_preds = xgb_results[h]["predictions"]
    xgb_actuals = xgb_results[h]["actuals"]
    lstm_preds = lstm_results[h]["predictions"]
    lstm_actuals = lstm_results[h]["actuals"]

    # Find common dates (intersection)
    common_idx = xgb_preds.index.intersection(lstm_preds.index)
    print(f"\nXGBoost OOS points: {len(xgb_preds)}")
    print(f"LSTM OOS points:    {len(lstm_preds)}")
    print(f"Common OOS points:  {len(common_idx)}")

    if len(common_idx) == 0:
        print("ERROR: No overlapping OOS dates! Check CV settings.")
        sys.exit(1)

    # Filter to common dates
    xgb_p = xgb_preds.loc[common_idx].values
    lstm_p = lstm_preds.loc[common_idx].values
    actuals = xgb_actuals.loc[common_idx].values

    # Verify actuals match
    lstm_act = lstm_actuals.loc[common_idx].values
    if not np.allclose(actuals, lstm_act, rtol=1e-6):
        print("WARNING: Actuals differ between models (unexpected)")

    # Date range of evaluation
    dates = common_idx.get_level_values("date") if common_idx.nlevels > 1 else common_idx
    date_min = pd.Timestamp(dates.min()).date()
    date_max = pd.Timestamp(dates.max()).date()
    print(f"Evaluation window: {date_min} to {date_max}")

    # Compute QLIKE
    xgb_qlike = qlike(actuals, xgb_p)
    lstm_qlike = qlike(actuals, lstm_p)
    gap_bps = (lstm_qlike - xgb_qlike) * 10000

    print(f"\n{'Model':<15} {'QLIKE':<12} {'vs XGBoost (bps)'}")
    print(f"{'-'*45}")
    print(f"{'XGBoost':<15} {xgb_qlike:<12.5f} {'—'}")
    print(f"{'LSTM':<15} {lstm_qlike:<12.5f} {gap_bps:+.1f}")

    # Diebold-Mariano test
    xgb_losses = qlike_losses(actuals, xgb_p)
    lstm_losses = qlike_losses(actuals, lstm_p)
    dm_stat, dm_p = diebold_mariano(lstm_losses, xgb_losses)
    print(f"\nDiebold-Mariano test (LSTM vs XGBoost):")
    print(f"  DM stat: {dm_stat:.3f}  (positive = LSTM worse)")
    print(f"  p-value: {dm_p:.4f}")
    if dm_p < 0.05:
        winner = "XGBoost" if dm_stat > 0 else "LSTM"
        print(f"  → Statistically significant difference (p<0.05). {winner} wins.")
    else:
        print(f"  → Not statistically significant (p≥0.05).")

    # HAR-IV baseline for reference
    print(f"\n{'='*60}")
    print("HAR-IV baseline (from same OOS window):")
    # Build HAR-IV on same dates for reference
    from volforecast.models.har_family import HARIV
    from volforecast.features.registry import FEATURE_REGISTRY, ensure_registered
    ensure_registered()
    har_iv_config = ExperimentConfig.from_yaml(configs_dir / "trial_074_xgb_maxwin_h1.yaml")
    # Override model to har_iv
    har_iv_config.model.name = "har_iv"
    har_iv_config.model.params = {}
    har_iv_pipe = Pipeline(har_iv_config)
    har_iv_results = har_iv_pipe.run_pooled(panel_data)
    har_iv_preds = har_iv_results[h]["predictions"]
    har_common = har_iv_preds.index.intersection(common_idx)
    if len(har_common) > 0:
        har_p = har_iv_preds.loc[har_common].values
        har_act = xgb_actuals.loc[har_common].values
        har_qlike = qlike(har_act, har_p)
        print(f"  HAR-IV QLIKE: {har_qlike:.5f}")
        print(f"  XGBoost vs HAR-IV: {(har_qlike - xgb_qlike)*10000:+.1f} bps")
        print(f"  LSTM vs HAR-IV:    {(har_qlike - lstm_qlike)*10000:+.1f} bps")

    # Save results
    results = {
        "trial": "074",
        "horizon": h,
        "universe": symbols,
        "oos_dates": {"start": str(date_min), "end": str(date_max)},
        "n_oos_points": len(common_idx),
        "cv": {"method": "expanding_window", "train_size": 2200, "test_size": 252, "purge_gap": 10},
        "xgboost": {"qlike": xgb_qlike, "time_s": xgb_time},
        "lstm": {"qlike": lstm_qlike, "time_s": lstm_time},
        "gap_bps": gap_bps,
        "dm_test": {"stat": dm_stat, "p_value": dm_p},
    }
    out_path = output_dir / "trial_074_comparison.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()
