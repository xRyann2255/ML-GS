"""CLI entry point for EDRVS_EXPIRY_INTRADAY prev-close 1-DTE ingestion.

Fetches the previous day's close (~16:00 ET) of the varswap expiring today
from Marquee EDRVS_EXPIRY_INTRADAY dataset. This is the correct IV for
GSVIVS01 signal decisions at 09:10 ET — no lookahead bias.

Stores cache in data/raw/iv/SPX_edrvs_0dte.parquet.

Usage:
    vol ingest-edrvs
    vol ingest-edrvs --start 2022-05-01 --end 2025-01-03
    vol ingest-edrvs --force
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
    """Run EDRVS_EXPIRY 0DTE variance swap strike ingestion.

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
    from volforecast.data.edrvol import (
        fetch_edrvs_0dte,
        load_edrvs_cache,
        save_edrvs_cache,
    )

    logger.info(
        "EDRVS ingest: fetching SPX 0DTE var-swap strike %s to %s",
        start_date,
        end_date,
    )

    # Check cache unless forced
    if not force:
        cached = load_edrvs_cache()
        if cached is not None and len(cached) > 0:
            cached_start = cached.index.min().date()
            cached_end = cached.index.max().date()
            if cached_start <= start_date and cached_end >= end_date:
                logger.info(
                    "EDRVS cache covers requested range (%s to %s). Use --force to re-fetch.",
                    cached_start,
                    cached_end,
                )
                print(
                    f"Cache covers {cached_start} to {cached_end} ({len(cached)} rows). "
                    "Use --force to re-fetch."
                )
                return 0

    # Fetch from Marquee
    series = fetch_edrvs_0dte(start_date, end_date)

    if series.empty:
        logger.warning("No EDRVS data returned for SPX %s to %s", start_date, end_date)
        print("ERROR: No data returned from EDRVS_EXPIRY. Check entitlement.")
        return 1

    # Save to cache
    save_edrvs_cache(series)
    print(
        f"Saved {len(series)} rows to cache ({series.index.min().date()} "
        f"to {series.index.max().date()})"
    )

    return 0


def register(subparsers) -> None:
    """Register the ingest-edrvs subcommand."""
    parser = subparsers.add_parser(
        "ingest-edrvs",
        help="Fetch SPX prev-close 1-DTE varswap fair vol from EDRVS_EXPIRY_INTRADAY",
    )
    parser.add_argument(
        "--start", type=str, default="2022-05-01", help="Start date (YYYY-MM-DD)"
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
    """Execute ingest-edrvs command. Return exit code."""
    from datetime import date, timedelta

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end if args.end else (date.today() - timedelta(days=1)).isoformat())
    return run(start, end, force=args.force)
