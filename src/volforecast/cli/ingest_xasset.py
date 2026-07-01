"""CLI entry point for cross-asset data ingestion.

Usage:
    vol ingest-xasset
    vol ingest-xasset --start 2015-01-02 --end 2024-12-31
    vol ingest-xasset --force
    vol ingest-xasset --groups rates,fx_vol
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from volforecast.data.cross_asset_ingest import (
    IngestResult,
    ingest_commodity,
    ingest_credit,
    ingest_fx_vol,
    ingest_rates,
)

logger = logging.getLogger(__name__)

_GROUP_FUNCS = {
    "rates": ingest_rates,
    "fx_vol": ingest_fx_vol,
    "credit": ingest_credit,
    "commodity": ingest_commodity,
}

ALL_GROUPS = list(_GROUP_FUNCS.keys())


def run(
    start_date: date,
    end_date: date,
    force: bool = False,
    groups: list[str] | None = None,
) -> int:
    """Run cross-asset data ingestion for selected groups.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).
    force : bool
        Re-fetch even if cache covers the date range.
    groups : list[str], optional
        Subset of groups to ingest. Default: all 4.

    Returns
    -------
    int
        Exit code (0 = success, 1 = partial failure).
    """
    from volforecast.cli.console import setup_logging
    from volforecast.cli.progress import StageProgress

    setup_logging()

    target_groups = groups or ALL_GROUPS
    invalid = set(target_groups) - set(ALL_GROUPS)
    if invalid:
        logger.error("Unknown groups: %s. Valid: %s", invalid, ALL_GROUPS)
        return 1

    # Pre-initialize GsSession before spawning threads to avoid race conditions
    # (concurrent session init corrupts the base URL → "Invalid URL 'PROD/v1/tsdb'")
    try:
        from volforecast.data.tsdb import _ensure_session as _tsdb_ensure

        _tsdb_ensure()
    except Exception as exc:  # noqa: BLE001
        logger.warning("TSDB session pre-init failed (will retry per-thread): %s", exc)

    try:
        from volforecast.data.marquee import _ensure_session as _mq_ensure

        _mq_ensure()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Marquee session pre-init failed (will retry per-thread): %s", exc)

    results: dict[str, IngestResult | Exception] = {}

    with StageProgress("ingest", "xasset", target_groups) as sp:
        task = sp.add_task(total=len(target_groups), description="groups")

        # ThreadPoolExecutor for parallelism across sub-groups
        with ThreadPoolExecutor(max_workers=min(4, len(target_groups))) as executor:
            futures = {
                executor.submit(_GROUP_FUNCS[g], start_date, end_date, force): g
                for g in target_groups
            }
            for future in as_completed(futures):
                group_name = futures[future]
                try:
                    result = future.result()
                    results[group_name] = result
                    if result.skipped:
                        sp.log(f"{group_name}: cached, skipped")
                    else:
                        sp.log(f"{group_name}: {result.rows} rows -> {result.path.name}")
                except Exception as exc:  # noqa: BLE001
                    results[group_name] = exc
                    sp.log(f"{group_name}: FAILED ({exc})")
                    logger.exception("Error ingesting %s", group_name)
                sp.advance(task)

    # Summary
    succeeded = sum(1 for r in results.values() if isinstance(r, IngestResult))
    failed = sum(1 for r in results.values() if isinstance(r, Exception))
    logger.info(
        "Cross-asset ingestion complete: %d succeeded, %d failed out of %d groups",
        succeeded,
        failed,
        len(target_groups),
    )

    return 1 if failed > 0 else 0


def register(subparsers) -> None:
    """Register the ingest-xasset subcommand."""
    parser = subparsers.add_parser(
        "ingest-xasset",
        help="Fetch cross-asset data (rates, FX vol, credit, commodity) from TSDB + Marquee",
    )
    parser.add_argument(
        "--start", type=str, default="2015-01-02", help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end", type=str, default=None, help="End date (YYYY-MM-DD, default: yesterday)"
    )
    parser.add_argument(
        "--groups",
        type=str,
        default=None,
        help="Comma-separated groups: rates,fx_vol,credit,commodity (default: all)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even if cache covers the date range",
    )
    parser.set_defaults(func=handle)


def handle(args) -> int:
    """Execute ingest-xasset command. Return exit code."""
    from datetime import date, timedelta

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end if args.end else (date.today() - timedelta(days=1)).isoformat())
    groups = args.groups.split(",") if args.groups else None
    return run(start, end, force=args.force, groups=groups)
