"""CLI entry point for per-symbol OHLCV ingestion from TSDB.

Fetches split-adjusted daily OHLCV (open, high, low, close, volume)
from TSDB eqpad_ for all equity/ETF symbols. Stores per-symbol parquets
in data/raw/ohlcv/.

Usage:
    vol ingest-ohlcv
    vol ingest-ohlcv --symbols SPY,AAPL
    vol ingest-ohlcv --start 2015-01-02 --end 2024-12-31
    vol ingest-ohlcv --force
"""

from __future__ import annotations

import logging
from datetime import date

from volforecast.constants import FUTURES_SYMBOLS, TICKER_TO_RIC
from volforecast.data.ohlcv import cache_covers_range, fetch_ohlcv, save_ohlcv_cache
from volforecast.utils.manifest import record_ingestion_yaml

logger = logging.getLogger(__name__)

# Default symbols: all with TSDB RIC mappings, excluding futures
_DEFAULT_SYMBOLS = sorted(set(TICKER_TO_RIC.keys()) - FUTURES_SYMBOLS)


def run(
    start_date: date,
    end_date: date,
    symbols: list[str] | None = None,
    force: bool = False,
) -> int:
    """Run per-symbol OHLCV ingestion pipeline.

    Parameters
    ----------
    start_date : date
        Start of fetch range.
    end_date : date
        End of fetch range.
    symbols : list[str], optional
        Subset of symbols to fetch. Defaults to all equities + ETFs.
    force : bool
        If True, re-fetch even if cache covers the date range.

    Returns
    -------
    int
        Exit code (0 = success, 1 = partial failure).
    """
    from volforecast.cli.console import setup_logging
    from volforecast.cli.progress import StageProgress

    setup_logging()

    target_symbols = symbols or _DEFAULT_SYMBOLS

    with StageProgress("ingest", "ohlcv", target_symbols) as sp:
        task = sp.add_task(total=len(target_symbols), description="symbols")

        fetched = 0
        skipped = 0
        failed: list[str] = []

        for sym in target_symbols:
            # Check cache unless force
            if not force:
                if cache_covers_range(sym, start_date, end_date):
                    sp.log(f"{sym}: cached, skipping")
                    skipped += 1
                    sp.advance(task)
                    continue

            try:
                df = fetch_ohlcv(sym, start_date, end_date)
                if df.empty:
                    sp.log(f"{sym}: no data returned")
                    failed.append(sym)
                else:
                    save_ohlcv_cache(sym, df)
                    record_ingestion_yaml(
                        "ohlcv",
                        sym,
                        start_date,
                        end_date,
                        len(df),
                        file_size_bytes=int(df.memory_usage(deep=True).sum()),
                    )
                    sp.log(f"{sym}: {len(df)} rows fetched")
                    fetched += 1
            except Exception as exc:  # noqa: BLE001
                sp.log(f"{sym}: FAILED -- {exc}")
                failed.append(sym)

            sp.advance(task)

        # Summary
        summary = f"Fetched: {fetched}, Skipped: {skipped}, Failed: {len(failed)}"
        sp.log(summary)
        if failed:
            sp.log(f"Failed symbols: {', '.join(failed)}")

    return 0 if not failed else 1


def register(subparsers) -> None:
    """Register the ingest-ohlcv subcommand."""
    import argparse

    parser = subparsers.add_parser(
        "ingest-ohlcv",
        help="Fetch split-adjusted daily OHLCV from TSDB eqpad_ for all symbols",
    )
    parser.add_argument(
        "--start", type=str, default="2015-01-02", help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end", type=str, default=None, help="End date (YYYY-MM-DD, default: yesterday)"
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated symbols (default: all equities + ETFs)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even if cache covers the date range",
    )
    parser.set_defaults(func=handle)


def handle(args) -> int:
    """Execute ingest-ohlcv command. Return exit code."""
    from datetime import timedelta

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end if args.end else (date.today() - timedelta(days=1)).isoformat())
    symbols = args.symbols.split(",") if args.symbols else None
    return run(start, end, symbols=symbols, force=args.force)
