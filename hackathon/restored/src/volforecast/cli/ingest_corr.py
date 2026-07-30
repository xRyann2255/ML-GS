"""CLI entry point for correlation data ingestion (Layer 7).

Usage:
    vol ingest-corr
    vol ingest-corr --start 2015-01-02 --end 2024-12-31
    vol ingest-corr --force
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
    """Run correlation data ingestion.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).
    force : bool
        Re-fetch even if cache covers the date range.

    Returns
    -------
    int
        Exit code (0 = success, 1 = failure).
    """
    from volforecast.cli.console import setup_logging
    from volforecast.cli.progress import StageProgress
    from volforecast.data.correlation_ingest import ingest_correlation

    setup_logging()

    # Pre-initialize Marquee session
    try:
        from volforecast.data.marquee import _ensure_session

        _ensure_session()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Marquee session pre-init failed (will retry): %s", exc)

    sources = ["implied_corr", "realized_corr", "avg_member_iv", "derive"]

    with StageProgress("ingest", "correlation", sources) as sp:
        task = sp.add_task(total=len(sources), description="sources")

        def _on_step(msg: str) -> None:
            sp.log(msg)
            sp.advance(task)

        try:
            result = ingest_correlation(
                start_date, end_date, force=force, on_step=_on_step
            )
            if result.skipped:
                sp.log("correlation: cached, skipped")
            else:
                sp.log(f"correlation: {result.rows} rows -> {result.path.name}")
            sp.finish(f"{result.rows} rows" if not result.skipped else "cached")
            return 0
        except Exception as exc:  # noqa: BLE001
            sp.log(f"correlation: FAILED ({exc})")
            logger.exception("Correlation ingestion failed: %s", exc)
            return 1


def register(subparsers) -> None:
    """Register the ingest-corr subcommand."""
    parser = subparsers.add_parser(
        "ingest-corr",
        help="Fetch SPX implied/realized correlation from Marquee EDR_INDEX datasets",
    )
    parser.add_argument(
        "--start", type=str, default="2010-01-02", help="Start date (YYYY-MM-DD)"
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
    """Execute ingest-corr command. Return exit code."""
    from datetime import date, timedelta

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(
        args.end if args.end else (date.today() - timedelta(days=1)).isoformat()
    )
    return run(start, end, force=args.force)
