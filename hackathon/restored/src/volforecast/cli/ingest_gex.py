"""CLI entry point for GEX (Gamma Exposure) ingestion from QSP option chains.

Fetches daily GEX metrics by querying SPX option chain data via QSP,
computing gamma exposure per strike, and aggregating to net/call/put GEX.
Stores results in a parquet cache at data/raw/options_oi/.

Usage:
    vol ingest-gex
    vol ingest-gex --start 2024-01-02 --end 2024-06-30
    vol ingest-gex --security-id 108105
    vol ingest-gex --force
"""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd

from volforecast.data.gex_ingest import (
    fetch_gex_daily,
    get_qsp_session,
    load_gex_cache,
    save_gex_cache,
)
from volforecast.utils.manifest import record_ingestion_yaml

logger = logging.getLogger(__name__)

# Default security ID for SPX options
_DEFAULT_SECURITY_ID = "108105"


def run(
    start_date: date,
    end_date: date,
    security_id: str = _DEFAULT_SECURITY_ID,
    force: bool = False,
) -> int:
    """Run GEX ingestion pipeline.

    Parameters
    ----------
    start_date : date
        Start of fetch range.
    end_date : date
        End of fetch range.
    security_id : str
        QSP security identifier (default: 108105 for SPX).
    force : bool
        If True, re-fetch even if date is already cached.

    Returns
    -------
    int
        Exit code (0 = success, 1 = partial/total failure).
    """
    from volforecast.cli.progress import StageProgress

    # Generate business days in range
    trading_days = pd.bdate_range(start_date, end_date).date.tolist()

    # Load existing cache
    cache_df = load_gex_cache()
    cached_dates: set[date] = set()
    if not cache_df.empty and "date" in cache_df.columns:
        cached_dates = set(pd.to_datetime(cache_df["date"]).dt.date)

    # Determine which dates to fetch
    if force:
        dates_to_fetch = trading_days
    else:
        dates_to_fetch = [d for d in trading_days if d not in cached_dates]

    session = get_qsp_session()

    with StageProgress("ingest", "gex", [security_id]) as sp:
        task = sp.add_task(total=len(dates_to_fetch), description="dates")

        fetched_rows: list[dict] = []
        failed: list[date] = []

        for query_date in dates_to_fetch:
            try:
                result = fetch_gex_daily(query_date, security_id, session)
                if result is None:
                    sp.log(f"{query_date}: no data")
                    failed.append(query_date)
                else:
                    fetched_rows.append(result)
                    sp.log(f"{query_date}: OK")
            except Exception as exc:  # noqa: BLE001
                sp.log(f"{query_date}: FAILED -- {exc}")
                failed.append(query_date)

            sp.advance(task)

        # Merge new rows with cache
        if fetched_rows:
            new_df = pd.DataFrame(fetched_rows)
            if cache_df.empty:
                merged = new_df
            else:
                merged = pd.concat([cache_df, new_df], ignore_index=True)
                # Deduplicate by date, keeping latest
                merged["date"] = pd.to_datetime(merged["date"])
                merged = merged.drop_duplicates(subset=["date"], keep="last")
                merged = merged.sort_values("date").reset_index(drop=True)
            save_gex_cache(merged)
            record_ingestion_yaml(
                "gex",
                security_id,
                start_date,
                end_date,
                len(fetched_rows),
            )

        # Summary
        skipped = len(trading_days) - len(dates_to_fetch)
        summary = (
            f"Fetched: {len(fetched_rows)}, "
            f"Skipped: {skipped}, Failed: {len(failed)}"
        )
        sp.log(summary)

    return 0 if not failed else 1


def register(subparsers) -> None:
    """Register the ingest-gex subcommand."""
    parser = subparsers.add_parser(
        "ingest-gex",
        help="Fetch daily GEX (Gamma Exposure) from QSP option chains",
    )
    parser.add_argument(
        "--start", type=str, default="2024-01-02", help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end", type=str, default=None, help="End date (YYYY-MM-DD, default: yesterday)"
    )
    parser.add_argument(
        "--security-id",
        type=str,
        default=_DEFAULT_SECURITY_ID,
        help="QSP security identifier (default: 108105 for SPX)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even if date is already cached",
    )
    parser.set_defaults(func=handle)


def handle(args) -> int:
    """Execute ingest-gex command. Return exit code."""
    from datetime import timedelta

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(
        args.end if args.end else (date.today() - timedelta(days=1)).isoformat()
    )
    return run(
        start_date=start,
        end_date=end,
        security_id=args.security_id,
        force=args.force,
    )
