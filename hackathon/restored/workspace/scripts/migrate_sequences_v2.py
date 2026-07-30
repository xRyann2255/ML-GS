"""One-time migration: add v2 stationary features to existing sequence parquets.

Reads each symbol's sequences parquet, computes v2 features from existing v1
columns (vwap, buy_vol, sell_vol, n_trades), and writes them back in-place.

V2 features added:
  - log_ret: log(vwap_t / vwap_{t-1}), first bar of day = 0
  - vol_share: (buy_vol + sell_vol) / daily_total
  - buy_ratio: buy_vol / (buy_vol + sell_vol + eps)
  - log_n_trades: log1p(n_trades) - median_day(log1p(n_trades))
  - abs_ret: |log_ret|

Usage:
    ./vol shell workspace/scripts/migrate_sequences_v2.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

# Resolve relative to repo root (parent of src/)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SEQUENCES_DIR = _REPO_ROOT / "data" / "raw" / "micro" / "sequences"


def migrate_symbol(parquet: Path) -> None:
    """Add v2 columns to a single symbol's parquet."""
    sym = parquet.stem
    df = pd.read_parquet(parquet)

    if "log_ret" in df.columns:
        print(f"  {sym}: already migrated, skipping")
        return

    if df.empty:
        print(f"  {sym}: empty parquet, skipping")
        return

    # Ensure date is proper type for groupby
    df["date"] = pd.to_datetime(df["date"])

    # Compute v2 features per day
    log_ret_all = np.empty(len(df), dtype=np.float64)
    vol_share_all = np.empty(len(df), dtype=np.float64)
    buy_ratio_all = np.empty(len(df), dtype=np.float64)
    log_n_trades_all = np.empty(len(df), dtype=np.float64)
    abs_ret_all = np.empty(len(df), dtype=np.float64)

    for _day, grp in df.groupby("date"):
        idx = grp.index
        buy = grp["buy_vol"].values.astype(np.float64)
        sell = grp["sell_vol"].values.astype(np.float64)
        mid = grp["vwap"].values.astype(np.float64)
        nt = grp["n_trades"].values.astype(np.float64) if "n_trades" in grp.columns else np.zeros(len(grp))

        # 1. log_ret
        with np.errstate(divide="ignore", invalid="ignore"):
            lr = np.log(mid[1:] / mid[:-1])
        lr = np.concatenate([[0.0], lr])
        lr = np.nan_to_num(lr, nan=0.0, posinf=0.0, neginf=0.0)

        # 2. vol_share
        total_vol = buy + sell
        daily_total = total_vol.sum()
        vs = total_vol / (daily_total + 1e-10)

        # 3. buy_ratio
        br = buy / (total_vol + 1e-10)

        # 4. log_n_trades (detrended)
        log_nt = np.log1p(nt)
        lnt = log_nt - np.median(log_nt)

        # 5. abs_ret
        ar = np.abs(lr)

        log_ret_all[idx] = lr
        vol_share_all[idx] = vs
        buy_ratio_all[idx] = br
        log_n_trades_all[idx] = lnt
        abs_ret_all[idx] = ar

    df["log_ret"] = log_ret_all
    df["vol_share"] = vol_share_all
    df["buy_ratio"] = buy_ratio_all
    df["log_n_trades"] = log_n_trades_all
    df["abs_ret"] = abs_ret_all

    # Convert date back to date objects for consistency
    df["date"] = df["date"].dt.date

    df.to_parquet(parquet, index=False)
    print(f"  {sym}: migrated ({len(df)} rows, {df['date'].nunique()} days)")


def main() -> None:
    if not SEQUENCES_DIR.exists():
        print(f"ERROR: {SEQUENCES_DIR} does not exist")
        return

    parquets = sorted(SEQUENCES_DIR.glob("*.parquet"))
    print(f"Migrating {len(parquets)} sequence parquets to v2 schema...")

    for p in parquets:
        migrate_symbol(p)

    print("Done.")


if __name__ == "__main__":
    main()
