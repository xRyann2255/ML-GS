"""CLI entry point for VIX futures continuous term structure ingestion.

Fetches VX1/VX2/VX3 continuous futures from TSDB by rolling monthly contracts.
Stores cache in data/raw/iv/_VIX_FUTURES.parquet.

Usage:
    vol ingest-vix-futures
    vol ingest-vix-futures --start 2015-01-02 --end 2025-01-03
    vol ingest-vix-futures --force
"""

from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)


def run(
    start_date: date,
    end_date: date,
    force: bool = False,
) -> int:
    """Run VIX futures continuous term structure ingestion.

    Parameters
    ----------
    start_date : date
        Start of fetch range.
    end_date : date
        End of fetch range.
    force : bool
        If True, re-fetch even if cache covers the date range.

    Returns
    -------
    int
        Exit code (0 = success).
    """
    from volforecast.data.vix_futures import (
        fetch_vix_futures_continuous,
        load_vix_futures_cache,
        save_vix_futures_cache,
    )

    logger.info(
        "VIX futures ingest: fetching VX1/VX2/VX3 %s to %s",
        start_date,
        end_date,
    )

    # Check cache unless forced
    existing = load_vix_futures_cache()
    if not force and existing is not None and len(existing) > 0:
        cached_start = existing.index.min().date()
        cached_end = existing.index.max().date()
        if cached_start <= start_date and cached_end >= end_date:
            logger.info(
                "VIX futures cache covers requested range (%s to %s). Use --force to re-fetch.",
                cached_start,
                cached_end,
            )
            print(
                f"Cache covers {cached_start} to {cached_end} ({len(existing)} rows). "
                "Use --force to re-fetch."
            )
            return 0

    # Fetch from TSDB
    df = fetch_vix_futures_continuous(start_date, end_date)

    if df.empty:
        logger.warning("No VIX futures data returned for %s to %s", start_date, end_date)
        print("ERROR: No data returned from TSDB for VIX futures.")
        return 1

    # Merge with existing cache if not forcing
    if not force and existing is not None and len(existing) > 0:
        import pandas as pd

        df = pd.concat([existing, df]).drop_duplicates().sort_index()

    # Save to cache
    save_vix_futures_cache(df)
    print(
        f"Saved {len(df)} rows to cache ({df.index.min().date()} "
        f"to {df.index.max().date()})"
    )

    return 0


def register(subparsers) -> None:
    """Register the ingest-vix-futures subcommand."""
    parser = subparsers.add_parser(
        "ingest-vix-futures",
        help="Fetch VIX futures continuous term structure (VX1/VX2/VX3) from TSDB",
    )
    parser.add_argument(
        "--start", type=str, default="2015-01-02", help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end", type=str, default=None, help="End date (YYYY-MM-DD, default: yesterday)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even if cache covers the date range",
    )
    parser.set_defaults(func=handle)


def handle(args) -> int:
    """Execute ingest-vix-futures command. Return exit code."""
    from datetime import date, timedelta

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end if args.end else (date.today() - timedelta(days=1)).isoformat())
    return run(start, end, force=args.force)
