"""CLI entry point for SPX mark Kvar ingestion (gross, pre-friction).

Computes the "morning mark Kvar" from output.json execution data using the
CBOE formula WITHOUT transaction costs. This gives the fair variance swap level
at GSVIVS01's 09:10 ET decision time, free from execution slippage.

The mark Kvar uses the actual option prices at trade time but removes the
friction component (transaction costs), making it the correct theoretical
reference for IV-RV signal comparison.

Stores cache in data/raw/iv/SPX_allday_vols.parquet.

Usage:
    vol ingest-allday
    vol ingest-allday --start 2022-05-01 --end 2025-01-03
    vol ingest-allday --force
"""

from __future__ import annotations

import logging
from datetime import date

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def run(start_date: date, end_date: date, force: bool = False) -> int:
    """Compute mark Kvar (gross, pre-friction) from output.json. Returns exit code."""
    from volforecast.data.gsvivs_kvar import (
        _find_forward_for_day,
        _T_0DTE_DEFAULT,
        compute_kvar_from_legs,
        parse_day_opening_legs,
    )
    from volforecast.data.spx_allday_vols import (
        load_allday_cache,
        save_allday_cache,
    )
    from volforecast.utils.paths import data_path

    import json

    json_path = data_path("external", "output.json")
    if not json_path.exists():
        print(f"ERROR: output.json not found at {json_path}")
        return 1

    with open(json_path) as f:
        data = json.load(f)

    # Check existing cache
    existing_cache = None if force else load_allday_cache()
    if existing_cache is not None and not force:
        cached_dates = set(existing_cache.index.normalize())
    else:
        cached_dates = set()

    results: list[dict] = []
    skipped_cached = 0
    skipped_insufficient = 0
    skipped_failed = 0

    for day_record in data:
        trade_date_str = day_record.get("date")
        if not trade_date_str:
            continue

        trade_date_obj = date.fromisoformat(trade_date_str)

        # Date range filter
        if trade_date_obj < start_date or trade_date_obj > end_date:
            continue

        # Skip if already cached
        if pd.Timestamp(trade_date_obj) in cached_dates:
            skipped_cached += 1
            continue

        value = day_record.get("value", {})
        risks = value.get("risks for date", [])
        if not risks:
            continue

        # Parse opening legs
        legs = parse_day_opening_legs(risks)
        if len(legs) < 3:
            skipped_insufficient += 1
            continue

        # Find forward
        forward = _find_forward_for_day(risks, trade_date_str, legs=legs)
        if forward is None:
            skipped_failed += 1
            continue

        # Compute GROSS Kvar (mark = no transaction costs)
        result = compute_kvar_from_legs(legs, forward, T=_T_0DTE_DEFAULT, r=0.05, tc_cash=0.0)
        if result is None:
            skipped_failed += 1
            continue

        # Use the cash_gross variant as primary (accounts for quantity weighting)
        kvar_vol = result.get("kvar_cash_gross_vol_pct")
        kvar_var = result.get("kvar_cash_gross_variance_ann")

        # Fallback to curve variant if cash-gross not available
        if not np.isfinite(kvar_vol or np.nan):
            kvar_vol = result.get("kvar_curve_vol_pct")
            kvar_var = result.get("kvar_curve_variance_ann")

        if not np.isfinite(kvar_vol or np.nan):
            skipped_failed += 1
            continue

        results.append({
            "trade_date": trade_date_obj,
            "kvar_vol_pct": kvar_vol,
            "kvar_variance_ann": kvar_var,
            "n_strikes": result.get("n_strikes", len(legs)),
            "forward": forward,
        })

    if not results and skipped_cached == 0:
        print(f"No data in range [{start_date}, {end_date}].")
        return 0

    if not results:
        total = skipped_cached + skipped_insufficient + skipped_failed
        print(
            f"All {total} dates handled ({skipped_cached} cached, "
            f"{skipped_insufficient} insufficient legs, {skipped_failed} failed). "
            "Use --force to recompute."
        )
        return 0

    # Build DataFrame
    new_df = pd.DataFrame(results).set_index("trade_date")
    new_df.index = pd.DatetimeIndex(new_df.index)

    # Merge with existing cache
    if existing_cache is not None:
        combined = pd.concat([existing_cache, new_df])
        combined = combined[~combined.index.duplicated(keep="last")]
        combined = combined.sort_index()
    else:
        combined = new_df.sort_index()

    # Save
    save_allday_cache(combined)

    date_min = combined.index.min().date()
    date_max = combined.index.max().date()
    print(
        f"Saved {len(combined)} rows to cache ({date_min} to {date_max}). "
        f"New: {len(results)}, skipped: {skipped_cached} cached, "
        f"{skipped_insufficient} insufficient, {skipped_failed} failed."
    )
    return 0


def register(subparsers) -> None:
    """Register the ingest-allday subcommand."""
    parser = subparsers.add_parser(
        "ingest-allday",
        help="Compute SPX mark Kvar (gross, pre-friction) from output.json execution data",
    )
    parser.add_argument("--start", type=str, default="2022-05-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default=None, help="End date (YYYY-MM-DD, default: yesterday)")
    parser.add_argument("--force", action="store_true", help="Recompute even if cache exists")
    parser.set_defaults(func=handle)


def handle(args) -> int:
    """Execute ingest-allday command. Return exit code."""
    from datetime import timedelta

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end if args.end else (date.today() - timedelta(days=1)).isoformat())
    return run(start, end, force=args.force)
