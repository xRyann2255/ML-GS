"""Trial-074 Blend Analysis: residual correlation and optimal blend weight.

Re-runs both models with identical CV, then computes:
1. Residual correlation (corr of per-obs QLIKE losses)
2. Optimal blend weight w via grid search on QLIKE
3. Blend improvement in bps

Usage: ./vol shell ../workspace/scripts/blend_analysis_074.py
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
    """QLIKE: mean(actual/predicted - log(actual/predicted) - 1)."""
    ratio = actual / predicted
    return float(np.mean(ratio - np.log(ratio) - 1))


def qlike_losses(actual: np.ndarray, predicted: np.ndarray) -> np.ndarray:
    """Per-observation QLIKE losses."""
    ratio = actual / predicted
    return ratio - np.log(ratio) - 1


def main() -> None:
    configs_dir = Path(__file__).resolve().parent.parent / "configs"
    output_dir = Path(__file__).resolve().parent.parent / "tmp"
    output_dir.mkdir(parents=True, exist_ok=True)

    symbols = [
        "SPY", "AAPL", "MSFT", "NVDA", "AVGO", "GOOGL", "AMZN",
        "V", "MA", "XOM", "PG", "JNJ", "HD", "NFLX",
        "TSLA", "CRM", "UNH", "BAC", "ADBE", "IWM", "DIA",
    ]

    # Load panel data
    panel_data: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        path = rv_cache_path(sym)
        if not path.exists():
            print(f"WARNING: No data for {sym}, skipping")
            continue
        panel_data[sym] = pd.read_parquet(path)
    print(f"Loaded {len(panel_data)} symbols")

    # Run XGBoost
    print("\n--- Running XGBoost ---")
    xgb_config = ExperimentConfig.from_yaml(configs_dir / "trial_074_xgb_maxwin_h1.yaml")
    xgb_pipe = Pipeline(xgb_config)
    xgb_results = xgb_pipe.run_pooled(panel_data)
    xgb_preds = xgb_results[1]["predictions"]
    xgb_actuals = xgb_results[1]["actuals"]
    print(f"XGBoost: {len(xgb_preds)} OOS predictions")

    # Run LSTM
    print("\n--- Running LSTM ---")
    lstm_config = ExperimentConfig.from_yaml(configs_dir / "trial_074_lstm_maxwin_h1.yaml")
    lstm_pipe = Pipeline(lstm_config)
    lstm_results = lstm_pipe.run_pooled(panel_data)
    lstm_preds = lstm_results[1]["predictions"]
    lstm_actuals = lstm_results[1]["actuals"]
    print(f"LSTM: {len(lstm_preds)} OOS predictions")

    # Align to common OOS dates
    common_idx = xgb_preds.index.intersection(lstm_preds.index)
    print(f"\nCommon OOS points: {len(common_idx)}")

    xgb_p = xgb_preds.loc[common_idx].values
    lstm_p = lstm_preds.loc[common_idx].values
    actuals = xgb_actuals.loc[common_idx].values

    # --- 1. Residual correlation ---
    print("\n" + "=" * 60)
    print("1. RESIDUAL CORRELATION ANALYSIS")
    print("=" * 60)

    # Log-space residuals (predictions are in exp-space, targets are RV)
    xgb_log_resid = np.log(actuals) - np.log(xgb_p)
    lstm_log_resid = np.log(actuals) - np.log(lstm_p)

    corr_log_resid = np.corrcoef(xgb_log_resid, lstm_log_resid)[0, 1]
    print(f"\nCorrelation of log-residuals: {corr_log_resid:.4f}")

    # Per-obs QLIKE losses
    xgb_losses = qlike_losses(actuals, xgb_p)
    lstm_losses = qlike_losses(actuals, lstm_p)
    corr_losses = np.corrcoef(xgb_losses, lstm_losses)[0, 1]
    print(f"Correlation of QLIKE losses:  {corr_losses:.4f}")

    # Rank correlation (Spearman) of residuals
    from scipy.stats import spearmanr
    spearman_rho, spearman_p = spearmanr(xgb_log_resid, lstm_log_resid)
    print(f"Spearman correlation (log-resid): {spearman_rho:.4f} (p={spearman_p:.4e})")

    # Interpretation
    print(f"\n--- Interpretation ---")
    if corr_log_resid < 0.5:
        print("LOW correlation (<0.5): models disagree substantially → blend likely adds value")
    elif corr_log_resid < 0.8:
        print("MODERATE correlation (0.5-0.8): some complementarity → blend may help marginally")
    else:
        print("HIGH correlation (>0.8): models agree on same observations → blend unlikely to help")

    # --- 2. Optimal blend weight ---
    print("\n" + "=" * 60)
    print("2. OPTIMAL BLEND WEIGHT (grid search)")
    print("=" * 60)

    # Blend in exp-space: pred_blend = w * xgb + (1-w) * lstm
    weights = np.linspace(0.0, 1.0, 101)
    blend_qlikes = []
    for w in weights:
        blend_pred = w * xgb_p + (1.0 - w) * lstm_p
        blend_qlikes.append(qlike(actuals, blend_pred))

    blend_qlikes = np.array(blend_qlikes)
    best_idx = np.argmin(blend_qlikes)
    best_w = weights[best_idx]
    best_blend_qlike = blend_qlikes[best_idx]

    xgb_qlike = qlike(actuals, xgb_p)
    lstm_qlike = qlike(actuals, lstm_p)

    print(f"\nXGBoost QLIKE:        {xgb_qlike:.6f}")
    print(f"LSTM QLIKE:           {lstm_qlike:.6f}")
    print(f"Best blend QLIKE:     {best_blend_qlike:.6f}")
    print(f"Best blend weight w:  {best_w:.2f} (w*XGB + (1-w)*LSTM)")
    print(f"\nBlend vs XGBoost:     {(xgb_qlike - best_blend_qlike) * 10000:+.2f} bps")
    print(f"Blend vs LSTM:        {(lstm_qlike - best_blend_qlike) * 10000:+.2f} bps")

    # Blend in log-space too
    print("\n--- Log-space blend ---")
    log_blend_qlikes = []
    for w in weights:
        blend_log = w * np.log(xgb_p) + (1.0 - w) * np.log(lstm_p)
        blend_pred_log = np.exp(blend_log)
        log_blend_qlikes.append(qlike(actuals, blend_pred_log))

    log_blend_qlikes = np.array(log_blend_qlikes)
    best_log_idx = np.argmin(log_blend_qlikes)
    best_log_w = weights[best_log_idx]
    best_log_blend_qlike = log_blend_qlikes[best_log_idx]

    print(f"Best log-blend QLIKE: {best_log_blend_qlike:.6f}")
    print(f"Best log-blend w:     {best_log_w:.2f}")
    print(f"Log-blend vs XGBoost: {(xgb_qlike - best_log_blend_qlike) * 10000:+.2f} bps")

    # --- 3. Per-symbol breakdown ---
    print("\n" + "=" * 60)
    print("3. PER-SYMBOL RESIDUAL CORRELATION")
    print("=" * 60)

    # If MultiIndex (date, symbol)
    if common_idx.nlevels > 1:
        sym_corrs = {}
        sym_blend_gains = {}
        for sym in symbols:
            try:
                sym_mask = common_idx.get_level_values("symbol") == sym
                if sym_mask.sum() < 10:
                    continue
                xr = xgb_log_resid[sym_mask]
                lr = lstm_log_resid[sym_mask]
                sym_corrs[sym] = np.corrcoef(xr, lr)[0, 1]

                # Per-symbol optimal blend
                xp = xgb_p[sym_mask]
                lp = lstm_p[sym_mask]
                ac = actuals[sym_mask]
                xq = qlike(ac, xp)
                best_sym_q = xq
                for w in [0.7, 0.8, 0.85, 0.9, 0.95, 1.0]:
                    bq = qlike(ac, w * xp + (1 - w) * lp)
                    if bq < best_sym_q:
                        best_sym_q = bq
                sym_blend_gains[sym] = (xq - best_sym_q) * 10000
            except Exception:
                continue

        if sym_corrs:
            print(f"\n{'Symbol':<8} {'Corr(resid)':<14} {'Blend gain (bps)'}")
            print(f"{'-'*40}")
            for sym in sorted(sym_corrs.keys()):
                gain = sym_blend_gains.get(sym, 0.0)
                print(f"{sym:<8} {sym_corrs[sym]:<14.4f} {gain:+.2f}")
            print(f"\nMean correlation: {np.mean(list(sym_corrs.values())):.4f}")
            print(f"Min correlation:  {min(sym_corrs.values()):.4f} ({min(sym_corrs, key=sym_corrs.get)})")
            print(f"Max correlation:  {max(sym_corrs.values()):.4f} ({max(sym_corrs, key=sym_corrs.get)})")

    # --- 4. Conditional analysis: when does LSTM beat XGBoost? ---
    print("\n" + "=" * 60)
    print("4. CONDITIONAL ANALYSIS: When does LSTM beat XGBoost?")
    print("=" * 60)

    lstm_wins = xgb_losses > lstm_losses
    print(f"\nLSTM wins on {lstm_wins.sum()}/{len(lstm_wins)} observations ({100*lstm_wins.mean():.1f}%)")

    # Is LSTM better on high-vol days?
    rv_median = np.median(actuals)
    high_vol = actuals > rv_median
    low_vol = ~high_vol

    xgb_q_highvol = qlike(actuals[high_vol], xgb_p[high_vol])
    lstm_q_highvol = qlike(actuals[high_vol], lstm_p[high_vol])
    xgb_q_lowvol = qlike(actuals[low_vol], xgb_p[low_vol])
    lstm_q_lowvol = qlike(actuals[low_vol], lstm_p[low_vol])

    print(f"\nHigh-vol days (above median RV):")
    print(f"  XGBoost: {xgb_q_highvol:.6f}, LSTM: {lstm_q_highvol:.6f}, gap: {(lstm_q_highvol - xgb_q_highvol)*10000:+.1f} bps")
    print(f"Low-vol days (below median RV):")
    print(f"  XGBoost: {xgb_q_lowvol:.6f}, LSTM: {lstm_q_lowvol:.6f}, gap: {(lstm_q_lowvol - xgb_q_lowvol)*10000:+.1f} bps")

    # Top/bottom quantile
    rv_q90 = np.quantile(actuals, 0.9)
    rv_q10 = np.quantile(actuals, 0.1)
    spike = actuals > rv_q90
    calm = actuals < rv_q10

    if spike.sum() > 10:
        print(f"\nSpike days (top 10% RV, n={spike.sum()}):")
        print(f"  XGBoost: {qlike(actuals[spike], xgb_p[spike]):.6f}")
        print(f"  LSTM:    {qlike(actuals[spike], lstm_p[spike]):.6f}")
        blend_spike = 0.85 * xgb_p[spike] + 0.15 * lstm_p[spike]
        print(f"  Blend85: {qlike(actuals[spike], blend_spike):.6f}")

    if calm.sum() > 10:
        print(f"\nCalm days (bottom 10% RV, n={calm.sum()}):")
        print(f"  XGBoost: {qlike(actuals[calm], xgb_p[calm]):.6f}")
        print(f"  LSTM:    {qlike(actuals[calm], lstm_p[calm]):.6f}")

    # --- Save results ---
    results = {
        "corr_log_residuals": corr_log_resid,
        "corr_qlike_losses": corr_losses,
        "spearman_rho": spearman_rho,
        "xgb_qlike": xgb_qlike,
        "lstm_qlike": lstm_qlike,
        "best_blend_qlike_exp": best_blend_qlike,
        "best_blend_weight_exp": best_w,
        "blend_vs_xgb_bps_exp": (xgb_qlike - best_blend_qlike) * 10000,
        "best_blend_qlike_log": best_log_blend_qlike,
        "best_blend_weight_log": best_log_w,
        "blend_vs_xgb_bps_log": (xgb_qlike - best_log_blend_qlike) * 10000,
        "lstm_win_rate": float(lstm_wins.mean()),
        "n_common_oos": len(common_idx),
    }
    out_path = output_dir / "trial_074_blend_analysis.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()
