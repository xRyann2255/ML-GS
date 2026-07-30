"""Refresh split-adjusted open/close in existing RV parquets.

Re-fetches daily open/close from TSDB with full corporate-action adjustment
and overwrites the (potentially corrupted) columns in cached parquets.

The original ingest stored unadjusted open prices alongside split-adjusted
close prices, corrupting overnight_return for any symbol with stock splits.
This command fixes that by re-fetching both fields with adjustment enabled.

Optimizations:
- Symbol-level parallelism: --symbol-workers N processes N symbols concurrently.
- Skip-if-clean: detects corruption via overnight_return magnitude check;
  skips symbols where open/close are already correctly adjusted.
- Minimal TSDB fetch: only open + close (2 fields), not full OHLCV (5 fields).

Usage:
    vol refresh-ohlcv --dry-run
    vol refresh-ohlcv --symbol-workers 4
    vol refresh-ohlcv --symbols SPY,AAPL --force
"""

from __future__ import annotations

import argparse
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Corruption threshold: |log(open_t / close_{t-1})| > this means split artifact.
# Genuine overnight moves rarely exceed 50% (log(1.5) ≈ 0.405).
# NOTE: Data is already refreshed as of 2026-05-20. All 25 symbols pass at 0.5.
# Volatile stocks (NFLX, TSLA, NVDA) legitimately hit 15-35% overnight on
# earnings; these are NOT corruption artifacts.
_CORRUPTION_THRESHOLD = 0.5


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="volforecast refresh-ohlcv",
        description="Re-fetch split-adjusted open/close into existing RV parquets",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated symbol subset (default: all cached parquets)",
    )
    parser.add_argument(
        "--symbol-workers",
        type=int,
        default=4,
        help="Number of symbols to fetch concurrently (default: 4)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show corruption status without fetching",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch all symbols even if open/close appear clean",
    )
    return parser.parse_args(argv)


def _discover_symbols(cache_dir: Path) -> list[str]:
    """Find all symbols with existing .parquet cache files."""
    return sorted(p.stem for p in cache_dir.glob("*.parquet") if p.stat().st_size > 0)


def _needs_refresh(panel: pd.DataFrame) -> tuple[bool, int]:
    """Detect whether a panel's open/close columns are corrupted.

    Returns
    -------
    (needs_fix, n_corrupt) : tuple[bool, int]
        needs_fix is True if columns are missing, all-NaN, or have
        overnight returns exceeding the corruption threshold.
        n_corrupt is the count of corrupted rows (0 if columns missing).
    """
    if "open" not in panel.columns or "close" not in panel.columns:
        return True, 0
    if panel["open"].isna().all() or panel["close"].isna().all():
        return True, 0

    # Compute overnight return: log(open_t / close_{t-1})
    close_prev = panel["close"].shift(1)
    mask = panel["open"].notna() & close_prev.notna() & (close_prev > 0)
    overnight = np.log(panel["open"][mask] / close_prev[mask])
    n_corrupt = int((overnight.abs() > _CORRUPTION_THRESHOLD).sum())
    return n_corrupt > 0, n_corrupt


def _fetch_adjusted_open_close(
    symbol: str, start_date: date, end_date: date
) -> tuple[pd.Series, pd.Series]:
    """Fetch split-adjusted open and close from TSDB.

    TSDB only provides adjusted close (close.adj.allincdiv) — there is no
    adjusted open field. We derive adjusted open by applying the same
    corporate-action adjustment factor: adj_open = raw_open * (adj_close / raw_close).

    Returns
    -------
    (open_series, close_series) : tuple[pd.Series, pd.Series]
        Both indexed by DatetimeIndex, fully split-adjusted.

    Raises
    ------
    ConnectionError
        If TSDB is unavailable.
    ValueError
        If symbol is not in the universe.
    """
    from volforecast.data.tsdb import _get_tsdb_data, _ticker_to_ric, _tsdb_symbol

    ric = _ticker_to_ric(symbol)
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    # Fetch all three series needed to derive adjusted open
    raw_open_sym = _tsdb_symbol(ric, "open", adjusted=False)
    raw_close_sym = _tsdb_symbol(ric, "close", adjusted=False)
    adj_close_sym = _tsdb_symbol(ric, "close", adjusted=True)

    raw_open = _get_tsdb_data(raw_open_sym, start_str, end_str)
    raw_close = _get_tsdb_data(raw_close_sym, start_str, end_str)
    adj_close = _get_tsdb_data(adj_close_sym, start_str, end_str)

    # Compute adjustment factor and apply to open
    # factor = adj_close / raw_close (e.g., 0.1 for a 10:1 split pre-split date)
    adj_factor = adj_close / raw_close
    adj_open = raw_open * adj_factor

    return adj_open, adj_close


def _refresh_one_symbol(
    symbol: str,
    cache_dir: Path,
    force: bool = False,
) -> tuple[str, str]:
    """Refresh open/close for one symbol.

    Returns
    -------
    (symbol, status_message) : tuple[str, str]
    """
    from volforecast.cli.progress import _format_elapsed

    t0 = time.time()
    path = cache_dir / f"{symbol}.parquet"
    if not path.exists():
        return symbol, "no cache file"

    panel = pd.read_parquet(path)
    if hasattr(panel.index, "date") and hasattr(panel.index[0], "date"):
        panel.index = panel.index.date
    panel.index.name = "date"

    if not force:
        needs_fix, n_corrupt = _needs_refresh(panel)
        if not needs_fix:
            return symbol, "skipped (clean)"

    # Determine date range from panel index
    dates = sorted(panel.index)
    start = dates[0] if isinstance(dates[0], date) else date.fromisoformat(str(dates[0]))
    end = dates[-1] if isinstance(dates[-1], date) else date.fromisoformat(str(dates[-1]))

    try:
        open_series, close_series = _fetch_adjusted_open_close(symbol, start, end)
    except (ConnectionError, ValueError) as exc:
        return symbol, f"FAILED: {exc}"

    # Convert TSDB DatetimeIndex to date objects to align with panel
    if hasattr(open_series.index, "date"):
        open_series.index = open_series.index.date
    if hasattr(close_series.index, "date"):
        close_series.index = close_series.index.date

    # Overwrite columns in the existing panel
    panel["open"] = open_series.reindex(panel.index)
    panel["close"] = close_series.reindex(panel.index)

    # Save back
    panel.to_parquet(path)

    elapsed = _format_elapsed(time.time() - t0)
    n_rows = int(panel["open"].notna().sum())
    return symbol, f"{n_rows:,} days refreshed [{elapsed}]"


def _refresh_symbol_wrapper(
    symbol: str,
    cache_dir: Path,
    force: bool,
    progress: object | None,
    lock: threading.Lock,
    sym_task_key: str | None,
) -> tuple[str, str]:
    """Wrapper for parallel symbol execution with progress updates."""
    from volforecast.cli.progress import StageProgress

    sym, status = _refresh_one_symbol(symbol, cache_dir, force)

    with lock:
        if isinstance(progress, StageProgress) and sym_task_key is not None:
            progress.advance(sym_task_key)
            progress.log(f"{sym}: {status}")

    return sym, status


def run(
    symbols: list[str] | None = None,
    symbol_workers: int = 4,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, str]:
    """Run OHLCV refresh for all cached symbols.

    Parameters
    ----------
    symbols : list[str] | None
        Subset of symbols to process (default: all cached).
    symbol_workers : int
        Number of symbols to fetch concurrently (default: 4).
    dry_run : bool
        If True, show corruption status without fetching.
    force : bool
        If True, re-fetch even if data appears clean.

    Returns
    -------
    dict[str, str]
        Mapping of symbol → status message.
    """
    from volforecast.cli.console import console
    from volforecast.cli.progress import StageProgress, _format_elapsed
    from volforecast.constants import TICKER_TO_RIC
    from volforecast.utils.paths import rv_cache_dir

    cache = rv_cache_dir()
    all_symbols = _discover_symbols(cache)

    if symbols:
        target = [s for s in symbols if s in all_symbols]
        missing = [s for s in symbols if s not in all_symbols]
        if missing:
            logger.warning("Symbols not found in cache: %s", missing)
    else:
        target = all_symbols

    # Filter out futures symbols — they have no TSDB RIC mapping for daily OHLCV.
    # Futures use tick-based overnight_return computed from intraday data, not TSDB.
    futures_skipped = [s for s in target if s not in TICKER_TO_RIC]
    target = [s for s in target if s in TICKER_TO_RIC]

    if not target:
        logger.error("No symbols to process")
        return {s: "skipped (futures — no TSDB path)" for s in futures_skipped}

    # Pre-scan: detect corruption per symbol
    sym_status: dict[str, tuple[bool, int]] = {}
    total_corrupt = 0
    needs_refresh_count = 0
    for sym in target:
        panel = pd.read_parquet(cache / f"{sym}.parquet")
        if hasattr(panel.index, "date") and hasattr(panel.index[0], "date"):
            panel.index = panel.index.date
        needs_fix, n_corrupt = _needs_refresh(panel)
        sym_status[sym] = (needs_fix, n_corrupt)
        total_corrupt += n_corrupt
        if needs_fix:
            needs_refresh_count += 1

    if dry_run:
        console.print(f"\n[bold]OHLCV Refresh — Dry Run[/bold]  ({len(target)} symbols)\n")
        for sym in target:
            needs_fix, n_corrupt = sym_status[sym]
            if needs_fix:
                if n_corrupt > 0:
                    console.print(
                        f"  [red]✗[/red] {sym:8s}: {n_corrupt:5,} corrupt overnight returns"
                    )
                else:
                    console.print(f"  [red]✗[/red] {sym:8s}: open/close missing or all-NaN")
            else:
                console.print(f"  [green]✓[/green] {sym:8s}: clean")

        console.print(f"\n  [bold]Need refresh: {needs_refresh_count}/{len(target)} symbols[/bold]")
        console.print(f"  Total corrupt rows: {total_corrupt:,}")
        if force:
            console.print("  [yellow]--force: would refresh ALL symbols[/yellow]")
        console.print()
        return {}

    # Determine which symbols to actually process
    if force:
        to_process = target
    else:
        to_process = [s for s in target if sym_status[s][0]]

    if not to_process:
        console.print("[green]All symbols already have clean open/close data.[/green]")
        return {s: "skipped (clean)" for s in target}

    if futures_skipped:
        console.print(
            f"[dim]Skipping futures (no TSDB daily path): {', '.join(futures_skipped)}[/dim]"
        )

    # Use StageProgress for rich display
    with StageProgress("refresh-ohlcv", "ohlcv-refresh", to_process) as sp:
        sym_task_key = sp.add_task(total=len(to_process), description="symbols")

        sp.log(
            f"{len(to_process)} symbols to refresh "
            f"({total_corrupt:,} corrupt rows detected) "
            f"| {symbol_workers} workers"
        )

        results: dict[str, str] = {}
        overall_t0 = time.time()

        # Pre-initialize GsSession in the main thread before spawning workers.
        # GsSession.use() is not thread-safe — concurrent calls race and produce
        # corrupted session state (base URL = "PROD" instead of actual endpoint).
        from volforecast.data.tsdb import _ensure_session

        try:
            _ensure_session()
        except ConnectionError as exc:
            sp.finish(f"FAILED: {exc}")
            return {s: f"FAILED: {exc}" for s in to_process}

        if symbol_workers <= 1:
            # Sequential: simple loop with per-symbol log
            for sym in to_process:
                _, status = _refresh_one_symbol(sym, cache, force)
                results[sym] = status
                sp.advance(sym_task_key)
                sp.log(f"{sym}: {status}")
        else:
            # Parallel: ThreadPoolExecutor
            lock = threading.Lock()

            with ThreadPoolExecutor(max_workers=symbol_workers) as pool:
                futures = {
                    pool.submit(
                        _refresh_symbol_wrapper,
                        sym,
                        cache,
                        force,
                        sp,
                        lock,
                        sym_task_key,
                    ): sym
                    for sym in to_process
                }
                for future in as_completed(futures):
                    sym = futures[future]
                    try:
                        _, status = future.result()
                        results[sym] = status
                    except Exception as exc:
                        logger.error("%s: refresh failed: %s", sym, exc)
                        results[sym] = f"FAILED: {exc}"
                        with lock:
                            sp.advance(sym_task_key)
                            sp.log(f"{sym}: FAILED: {exc}")

        # Add skipped symbols to results
        for sym in target:
            if sym not in results:
                results[sym] = "skipped (clean)"

        overall_elapsed = time.time() - overall_t0
        n_refreshed = sum(1 for s in results.values() if "refreshed" in s)
        n_failed = sum(1 for s in results.values() if "FAILED" in s)
        n_skipped = sum(1 for s in results.values() if "skipped" in s)

        summary_parts = [f"{n_refreshed} refreshed"]
        if n_skipped:
            summary_parts.append(f"{n_skipped} skipped")
        if n_failed:
            summary_parts.append(f"{n_failed} failed")

        sp.finish(f"{', '.join(summary_parts)} [{_format_elapsed(overall_elapsed)}]")

    # Include futures that were filtered out
    for sym in futures_skipped:
        results[sym] = "skipped (futures — no TSDB path)"

    return results


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    from volforecast.cli.console import setup_logging

    setup_logging()

    args = parse_args(argv)
    symbols = args.symbols.split(",") if args.symbols else None

    try:
        run(
            symbols=symbols,
            symbol_workers=args.symbol_workers,
            dry_run=args.dry_run,
            force=args.force,
        )
    except ConnectionError as exc:
        logger.error("Connection error: %s", exc)
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130

    return 0


def register(subparsers) -> None:
    """Register the refresh-ohlcv subcommand."""
    parser = subparsers.add_parser(
        "refresh-ohlcv",
        help="Re-fetch split-adjusted open/close into existing RV parquets",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated symbols (default: all cached)",
    )
    parser.add_argument(
        "--symbol-workers",
        type=int,
        default=4,
        help="Number of symbols to fetch concurrently (default: 4)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show corruption status without fetching",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch all symbols even if open/close appear clean",
    )
    parser.set_defaults(func=handle)


def handle(args) -> int:
    """Execute refresh-ohlcv command. Return exit code."""
    symbols = args.symbols.split(",") if args.symbols else None
    run(
        symbols=symbols,
        symbol_workers=args.symbol_workers,
        dry_run=args.dry_run,
        force=args.force,
    )
    return 0
