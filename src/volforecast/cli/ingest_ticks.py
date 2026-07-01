"""CLI entry point for standalone tick-derived RV panel ingestion.

Fetches tick data from Chunk Store and builds daily RV panels for
the requested symbols. Stores per-symbol parquets in data/raw/ticks/.

No experiment config required — fully standalone with sensible defaults.

Usage:
    vol ingest-ticks
    vol ingest-ticks --symbols SPY,AAPL
    vol ingest-ticks --start 2014-01-02 --end 2024-12-31
    vol ingest-ticks --force
    vol ingest-ticks --mode ticks --symbols SPY  # Full RK computation
    vol ingest-ticks --recompute  # Re-derive from bars without re-fetching
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from volforecast.constants import SYMBOL_UNIVERSE
from volforecast.data.ticks import cache_covers_range, ingest_symbol, load_ticks_cache
from volforecast.utils.manifest import record_ingestion, record_ingestion_yaml

logger = logging.getLogger(__name__)

# Default symbols: full universe
_DEFAULT_SYMBOLS = sorted(SYMBOL_UNIVERSE)


def run(
    start_date: date,
    end_date: date,
    symbols: list[str] | None = None,
    force: bool = False,
    recompute: bool = False,
    mode: str = "bars",
    workers: int = 4,
    symbol_workers: int = 1,
    batch_size: int = 5,
    throttle_s: float = 0.0,
) -> int:
    """Run standalone tick ingestion pipeline.

    Parameters
    ----------
    start_date : date
        Start of fetch range.
    end_date : date
        End of fetch range.
    symbols : list[str], optional
        Subset of symbols to fetch. Defaults to full SYMBOL_UNIVERSE (34).
    force : bool
        If True, re-fetch even if cache covers the date range.
    recompute : bool
        If True, re-derive RV measures from cached bars without re-fetching.
    mode : str
        'bars' (fast, no RK) or 'ticks' (slow, full RK + noise_gap).
    workers : int
        Parallel fetch threads per symbol.
    symbol_workers : int
        Number of symbols to ingest concurrently.
    batch_size : int
        Trading days per API call.
    throttle_s : float
        Seconds to sleep between API batches (default: 0). Use 2-5 for
        high-volume symbols like SPY to avoid Chunk Store rate limits.

    Returns
    -------
    int
        Exit code (0 = success, 1 = partial failure).
    """
    from volforecast.cli.console import setup_logging
    from volforecast.cli.progress import StageProgress

    setup_logging()

    target_symbols = symbols or _DEFAULT_SYMBOLS

    if force:
        import sys

        print(
            "\n\033[33m⚠  WARNING: --force will OVERWRITE existing parquet files "
            "for the selected symbols.\033[0m\n"
            "   If you are debugging, restore originals afterward with:\n"
            "     git checkout HEAD -- data/raw/ticks/\n",
            file=sys.stderr,
        )

    with StageProgress("ingest", "ticks", target_symbols) as sp:
        task = sp.add_task(total=len(target_symbols), description="symbols")

        fetched = 0
        skipped = 0
        failed: list[str] = []
        _lock = threading.Lock()

        def _ingest_one(sym: str) -> tuple[str, str, int]:
            """Ingest a single symbol. Returns (symbol, status, n_rows).

            status: 'fetched' | 'skipped' | 'failed'
            """
            # Check cache unless force or recompute
            if not force and not recompute:
                if cache_covers_range(sym, start_date, end_date):
                    sp.log(f"{sym}: fully cached, skipping")
                    sp.advance(task)
                    return (sym, "skipped", 0)

            try:
                # Report cached vs missing days
                existing = load_ticks_cache(sym)
                if existing is not None and not existing.empty:
                    n_cached = len(existing)
                    cache_start = existing.index.min()
                    cache_end = existing.index.max()
                    sp.log(
                        f"{sym}: {n_cached} days cached ({cache_start} to {cache_end}), "
                        f"fetching missing days in {start_date} to {end_date} (mode={mode})..."
                    )
                else:
                    sp.log(f"{sym}: no cache, fetching {start_date} to {end_date} (mode={mode})...")
                panel = ingest_symbol(
                    sym,
                    start_date,
                    end_date,
                    mode=mode,
                    workers=workers,
                    batch_size=batch_size,
                    progress=sp,
                    throttle_s=throttle_s,
                )
                if panel.empty:
                    sp.log(f"{sym}: no data returned")
                    sp.advance(task)
                    return (sym, "failed", 0)

                # Record in manifest (needs lock — shared JSON file)
                n_rows = len(panel)
                skipped_dates = panel.attrs.get("skipped_dates", [])
                with _lock:
                    record_ingestion("rv", sym, start_date, end_date, n_rows, skipped_dates)
                    record_ingestion_yaml("ticks", sym, start_date, end_date, n_rows)
                sp.log(f"{sym}: {n_rows} rows")
                sp.advance(task)
                return (sym, "fetched", n_rows)
            except Exception as exc:  # noqa: BLE001
                sp.log(f"{sym}: FAILED -- {exc}")
                sp.advance(task)
                return (sym, "failed", 0)

        if symbol_workers <= 1:
            # Sequential path (original behavior)
            for sym in target_symbols:
                _, status, _ = _ingest_one(sym)
                if status == "fetched":
                    fetched += 1
                elif status == "skipped":
                    skipped += 1
                else:
                    failed.append(sym)
        else:
            # Parallel symbol ingestion
            with ThreadPoolExecutor(max_workers=symbol_workers) as executor:
                futures = {executor.submit(_ingest_one, sym): sym for sym in target_symbols}
                for future in as_completed(futures):
                    sym = futures[future]
                    try:
                        _, status, _ = future.result()
                    except Exception as exc:  # noqa: BLE001
                        sp.log(f"{sym}: FAILED (unexpected) -- {exc}")
                        status = "failed"
                    if status == "fetched":
                        fetched += 1
                    elif status == "skipped":
                        skipped += 1
                    else:
                        failed.append(sym)

        # Summary
        summary = f"Fetched: {fetched}, Skipped: {skipped}, Failed: {len(failed)}"
        sp.log(summary)
        if failed:
            sp.log(f"Failed symbols: {', '.join(failed)}")

    return 0 if not failed else 1


def register(subparsers) -> None:
    """Register the ingest-ticks subcommand."""
    parser = subparsers.add_parser(
        "ingest-ticks",
        help="Fetch tick data from Chunk Store and build daily RV panels (standalone)",
    )
    parser.add_argument(
        "--start", type=str, default="2014-01-02", help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end", type=str, default=None, help="End date (YYYY-MM-DD, default: yesterday)"
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated symbols (default: full 34-symbol universe)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even if cache covers the date range",
    )
    parser.add_argument(
        "--recompute",
        action="store_true",
        help="Re-derive RV measures from cached bars without re-fetching",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="bars",
        choices=["bars", "ticks"],
        help="'bars' (fast, no RK) or 'ticks' (slow, full RK + noise_gap)",
    )
    parser.add_argument(
        "--workers", type=int, default=4, help="Parallel fetch threads per symbol"
    )
    parser.add_argument(
        "--symbol-workers",
        type=int,
        default=1,
        help="Symbols to ingest concurrently (try 4-8 for parallel fetching)",
    )
    parser.add_argument("--batch-size", type=int, default=5, help="Trading days per API call")
    parser.add_argument(
        "--throttle",
        type=float,
        default=0.0,
        help="Seconds to sleep between API batches to avoid rate limiting (default: 0)",
    )
    parser.set_defaults(func=handle)


def handle(args) -> int:
    """Execute ingest-ticks command. Return exit code."""
    from datetime import date, timedelta

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end if args.end else (date.today() - timedelta(days=1)).isoformat())
    symbols = args.symbols.split(",") if args.symbols else None
    return run(
        start,
        end,
        symbols=symbols,
        force=args.force,
        recompute=args.recompute,
        mode=args.mode,
        workers=args.workers,
        symbol_workers=getattr(args, "symbol_workers", 1),
        batch_size=args.batch_size,
        throttle_s=args.throttle,
    )
