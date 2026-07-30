"""Build 5-minute sequence parquets from existing 10-second bar parquets.

Reads data/raw/micro/sequences/{SYMBOL}.parquet, aggregates 10s bars into
5-min bars with enriched features, saves to data/raw/micro/sequences_5min/.

Usage: ./vol shell workspace/scripts/build_5min_sequences.py
"""
from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from volforecast.data.micro import _build_5min_sequences_df, save_sequences_cache
from volforecast.utils.paths import micro_sequences_dir

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    src_dir = micro_sequences_dir()  # data/raw/micro/sequences/
    if not src_dir.exists():
        log.error("Source directory does not exist: %s", src_dir)
        sys.exit(1)

    parquets = sorted(src_dir.glob("*.parquet"))
    # Filter out staging directories etc
    parquets = [p for p in parquets if p.is_file()]

    if not parquets:
        log.error("No parquet files found in %s", src_dir)
        sys.exit(1)

    log.info("Found %d symbol parquets in %s", len(parquets), src_dir)

    for pq_path in parquets:
        symbol = pq_path.stem
        log.info("Processing %s ...", symbol)

        df = pd.read_parquet(pq_path)

        # Reconstruct bars_by_date
        df["date"] = pd.to_datetime(df["date"]).dt.date
        bars_by_date: dict[date, pd.DataFrame] = {}
        for d, group in df.groupby("date"):
            # Keep only the columns needed by _build_5min_sequences_df
            bars_by_date[d] = group[["buy_vol", "sell_vol", "vwap", "n_trades"]].reset_index(drop=True)

        # Build 5-min sequences
        result = _build_5min_sequences_df(bars_by_date)

        if result.empty:
            log.warning("  %s: no output rows", symbol)
            continue

        # Save with bar_interval=300 for 5-min directory resolution
        out_path = save_sequences_cache(symbol, result, bar_interval=300)

        # Stats
        n_dates = result["date"].nunique()
        bars_per_day = result.groupby("date").size()
        log.info(
            "  %s: %d dates, %d total bars, bars/day: mean=%.1f min=%d max=%d → %s",
            symbol, n_dates, len(result),
            bars_per_day.mean(), bars_per_day.min(), bars_per_day.max(),
            out_path,
        )

    log.info("Done.")


if __name__ == "__main__":
    main()
