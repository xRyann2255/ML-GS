"""CLI entry point for per-symbol microstructure ingestion.

Fetches tick data from ChunkStore with server-side LeeReady trade
classification, computes daily signed-volume aggregates + VPIN + 10-second
bar sequences. Stores per-symbol parquets in data/raw/micro/.

Usage:
    vol ingest-micro
    vol ingest-micro --symbols SPY,AAPL
    vol ingest-micro --start 2015-01-02 --end 2024-12-31
    vol ingest-micro --force
    vol ingest-micro --recompute  # Re-derive dailies from cached sequences
    vol ingest-micro --symbol-workers 8  # Parallel symbol ingestion
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

from volforecast.constants import SYMBOL_UNIVERSE
from volforecast.data.micro import ingest_symbol_micro
from volforecast.utils.manifest import record_ingestion_yaml

logger = logging.getLogger(__name__)

# Default symbols: full universe
_DEFAULT_SYMBOLS = sorted(SYMBOL_UNIVERSE)


def _format_eta(seconds: float) -> str:
    """Human-readable ETA string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        m, s = divmod(int(seconds), 60)
        return f"{m}m{s:02d}s"
    else:
        h, remainder = divmod(int(seconds), 3600)
        m, _ = divmod(remainder, 60)
        return f"{h}h{m:02d}m"


def run(
    start_date: date,
    end_date: date,
    symbols: list[str] | None = None,
    force: bool = False,
    recompute: bool = False,
    fill_gaps: bool = False,
    workers: int = 4,
    symbol_workers: int = 4,
    batch_size: int = 20,
    bucket_volume: int | None = None,
    cache_dir: Path | None = None,
    sequences_dir: Path | None = None,
) -> int:
    """Run per-symbol microstructure ingestion pipeline.

    Parameters
    ----------
    start_date : date
        Start of fetch range.
    end_date : date
        End of fetch range.
    symbols : list[str], optional
        Subset of symbols. Defaults to full 34-symbol universe.
    force : bool
        Re-fetch even if cache covers the date range.
    recompute : bool
        Re-derive dailies from cached sequences (no network).
    workers : int
        Fetch threads per symbol (unused currently — server-side processing).
    symbol_workers : int
        Concurrent symbols to ingest (default 4).
    batch_size : int
        Trading days per API call.
    bucket_volume : int, optional
        VPIN bucket volume override. None = auto per symbol.
    cache_dir : Path, optional
        Override daily cache directory.
    sequences_dir : Path, optional
        Override sequences directory.

    Returns
    -------
    int
        Exit code (0 = success, 1 = partial failure).
    """
    from volforecast.cli.console import setup_logging
    from volforecast.cli.progress import StageProgress
    from volforecast.utils.paths import micro_cache_dir, micro_sequences_dir

    setup_logging()

    target_symbols = symbols or _DEFAULT_SYMBOLS

    if cache_dir is None:
        cache_dir = micro_cache_dir()
    if sequences_dir is None:
        sequences_dir = micro_sequences_dir()

    if force and not recompute:
        import sys

        print(
            "\n\033[33m⚠  WARNING: --force will OVERWRITE existing parquet files "
            "for the selected symbols.\033[0m\n"
            "   Restore originals afterward with:\n"
            "     git checkout HEAD -- data/raw/micro/\n",
            file=sys.stderr,
        )

    with StageProgress("ingest", "micro", target_symbols) as sp:
        task = sp.add_task(total=len(target_symbols), description="symbols")

        fetched = 0
        skipped = 0
        failed: list[str] = []
        _lock = threading.Lock()

        # Track per-symbol timing for ETA
        symbol_times: list[float] = []

        def _ingest_one(sym: str) -> tuple[str, str, int, int]:
            """Ingest one symbol. Returns (symbol, status, daily_rows, seq_rows)."""
            t0 = time.perf_counter()

            try:
                if not recompute:
                    sp.log(f"{sym}: checking cache and fetching missing data...")
                else:
                    sp.log(f"{sym}: recomputing from cached sequences...")

                daily_df, seq_df = ingest_symbol_micro(
                    sym,
                    start_date,
                    end_date,
                    force=force,
                    recompute=recompute,
                    fill_gaps=fill_gaps,
                    batch_size=batch_size,
                    bucket_volume=bucket_volume,
                    cache_dir=cache_dir,
                    sequences_dir=sequences_dir,
                    progress=sp,
                )

                if daily_df.empty:
                    sp.log(f"{sym}: no data returned")
                    sp.advance(task)
                    return (sym, "failed", 0, 0)

                n_daily = len(daily_df)
                n_seq = len(seq_df) if seq_df is not None else 0
                elapsed = time.perf_counter() - t0

                with _lock:
                    record_ingestion_yaml(
                        "micro",
                        sym,
                        start_date,
                        end_date,
                        n_daily,
                    )
                    symbol_times.append(elapsed)

                # Log with timing and ETA
                avg_per_sym = sum(symbol_times) / len(symbol_times)
                remaining_syms = len(target_symbols) - (fetched + skipped + len(failed) + 1)
                eta_str = _format_eta(avg_per_sym * remaining_syms) if remaining_syms > 0 else "0s"
                sp.log(
                    f"{sym}: {n_daily} days, {n_seq:,} seq bars "
                    f"[{elapsed:.0f}s] (ETA remaining: {eta_str})"
                )
                sp.advance(task)
                return (sym, "fetched", n_daily, n_seq)

            except Exception as exc:  # noqa: BLE001
                sp.log(f"{sym}: FAILED -- {exc}")
                sp.advance(task)
                return (sym, "failed", 0, 0)

        if symbol_workers <= 1:
            for sym in target_symbols:
                _, status, _, _ = _ingest_one(sym)
                if status == "fetched":
                    fetched += 1
                elif status == "skipped":
                    skipped += 1
                else:
                    failed.append(sym)
        else:
            with ThreadPoolExecutor(max_workers=symbol_workers) as executor:
                futures = {executor.submit(_ingest_one, sym): sym for sym in target_symbols}
                for future in as_completed(futures):
                    sym = futures[future]
                    try:
                        _, status, _, _ = future.result()
                    except Exception as exc:  # noqa: BLE001
                        sp.log(f"{sym}: FAILED (unexpected) -- {exc}")
                        status = "failed"
                    if status == "fetched":
                        fetched += 1
                    elif status == "skipped":
                        skipped += 1
                    else:
                        failed.append(sym)

        # Final summary
        total_time = sum(symbol_times)
        summary = (
            f"Fetched: {fetched}, Skipped: {skipped}, Failed: {len(failed)} "
            f"[total: {_format_eta(total_time)}]"
        )
        sp.log(summary)
        if failed:
            sp.log(f"Failed symbols: {', '.join(failed)}")

    return 0 if not failed else 1


def register(subparsers) -> None:
    """Register the ingest-micro subcommand."""
    parser = subparsers.add_parser(
        "ingest-micro",
        help="Fetch LeeReady signed-volume bars, build VPIN/OFI + 10s sequences",
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
        help="Re-derive dailies from cached sequences (no network)",
    )
    parser.add_argument(
        "--fill-gaps",
        action="store_true",
        help="Also fetch missing dates within existing cached range (historical gaps)",
    )
    parser.add_argument("--workers", type=int, default=4, help="Fetch threads per symbol")
    parser.add_argument(
        "--symbol-workers",
        type=int,
        default=4,
        help="Symbols to ingest concurrently (default 4)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=20, help="Trading days per API call"
    )
    parser.add_argument(
        "--bucket-volume",
        type=int,
        default=None,
        help="VPIN bucket volume (default: auto from median daily volume)",
    )
    parser.add_argument(
        "--detect-gaps",
        action="store_true",
        help="Dry run: report missing dates without fetching",
    )
    parser.set_defaults(func=handle)


def handle(args) -> int:
    """Execute ingest-micro command. Return exit code."""
    from datetime import date, timedelta

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end if args.end else (date.today() - timedelta(days=1)).isoformat())
    symbols = args.symbols.split(",") if args.symbols else None

    if getattr(args, "detect_gaps", False):
        return _handle_detect_gaps(start, end, symbols)

    return run(
        start,
        end,
        symbols=symbols,
        force=args.force,
        recompute=args.recompute,
        fill_gaps=getattr(args, "fill_gaps", False),
        workers=args.workers,
        symbol_workers=getattr(args, "symbol_workers", 4),
        batch_size=args.batch_size,
        bucket_volume=getattr(args, "bucket_volume", None),
    )


def _handle_detect_gaps(start_date: date, end_date: date, symbols: list[str] | None) -> int:
    """Print gap report without fetching any data."""
    from volforecast.data.micro import _format_date_ranges, detect_gaps

    target_symbols = symbols or _DEFAULT_SYMBOLS
    has_gaps = False

    for sym in sorted(target_symbols):
        gaps = detect_gaps(sym, start_date, end_date)
        if gaps:
            has_gaps = True
            print(f"{sym}: {len(gaps)} missing days — {_format_date_ranges(gaps)}")
        else:
            print(f"{sym}: complete (no gaps)")

    return 1 if has_gaps else 0
