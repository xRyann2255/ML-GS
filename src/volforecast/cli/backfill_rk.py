"""Backfill realized kernel (RK) and noise_gap for all cached symbols.

Reads existing parquet cache, identifies dates where rk is NaN, fetches raw
ticks from Chunk Store for those dates, computes realized_kernel from tick
log-prices, and updates the parquet in-place.

Optimizations
-------------
- Multi-day batching: fetches 5 days per API call (5x fewer round-trips).
- Symbol-level parallelism: ``--symbol-workers N`` processes N symbols concurrently.
- Minimal field fetch: only requests TRDPRC_1 (not full L1) — ~3x less data.
- Uses existing ``rv`` from panel for noise_gap denominator (no tick resample).
- Non-blocking timeout: hung chunk_query calls don't block the caller.

Usage (overnight job):
    vol backfill-rk --symbol-workers 4 --batch-days 50
    vol backfill-rk --symbols SPY,AAPL --batch-days 20
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Only fetch trade price — RK computation needs nothing else.
# L1_FIELDS has 6 columns (BID, ASK, sizes, volume) which triples payload.
_RK_FIELDS = ["TRDPRC_1"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="volforecast backfill-rk",
        description="Backfill realized kernel and noise_gap into existing RV parquets",
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
        default=1,
        help="Number of symbols to process concurrently (default: 1)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="(Deprecated, kept for compat) Day-level parallelism is no longer used; "
        "multi-day batching is faster. Symbol-level parallelism via --symbol-workers.",
    )
    parser.add_argument(
        "--batch-days",
        type=int,
        default=10,
        help="Days per checkpoint batch (default: 10)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="Timeout per chunk_query call in seconds (default: 180)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List symbols and NaN counts without fetching",
    )
    return parser.parse_args(argv)


def _discover_symbols(cache_dir: Path) -> list[str]:
    """Find all symbols with existing .parquet cache files."""
    return sorted(p.stem for p in cache_dir.glob("*.parquet") if p.stat().st_size > 0)


def _get_nan_rk_dates(panel: pd.DataFrame) -> list[date]:
    """Return sorted list of dates where rk is NaN (needs backfill)."""
    if "rk" not in panel.columns:
        return sorted(panel.index.tolist())
    mask = panel["rk"].isna()
    return sorted(panel.index[mask].tolist())


def _fetch_and_compute_rk_one_day(
    symbol: str,
    day: date,
    rv_5min: float | None,
    timeout_s: float = 120.0,
) -> dict | None:
    """Fetch raw ticks for one day and compute RK + noise_gap.

    Parameters
    ----------
    symbol : str
        Ticker symbol.
    day : date
        Trading day to process.
    rv_5min : float | None
        Pre-computed 5-min RV from the panel. If None, noise_gap is computed
        from tick-resampled 5-min bars as fallback.
    timeout_s : float
        Timeout for the API call.

    Returns dict with keys: date, rk, noise_gap, n_ticks
    or None if fetch fails / no data.
    """
    from volforecast.data.chunk_store import (
        CHUNKDB,
        TICKER_TO_RIC,
        TZ,
        _chunk_query_with_timeout,
        _ensure_session,
        _resolve_es_symbol,
        query,
    )
    from volforecast.data.measures import noise_gap as compute_noise_gap
    from volforecast.data.measures import realized_kernel

    if query is None:
        raise ConnectionError("pytickclient not available.")
    _ensure_session()

    chunk_symbol = _resolve_es_symbol(day) if symbol == "ES" else TICKER_TO_RIC.get(symbol, symbol)

    st = TZ.localize(datetime(day.year, day.month, day.day, 9, 30, 0))
    et = TZ.localize(datetime(day.year, day.month, day.day, 16, 0, 0))

    raw = _chunk_query_with_timeout(
        [chunk_symbol],
        st,
        et,
        CHUNKDB,
        _RK_FIELDS,
        timeout_s=timeout_s,
        retries=2,
    )

    # raw can be a numpy recarray (not a plain dict) — avoid bool check on arrays.
    # Convert to DataFrame immediately; empty dict/array → empty DataFrame.
    df = pd.DataFrame(raw)
    if df.empty:
        logger.debug("%s %s: no ticks", symbol, day)
        return None

    if "TRDPRC_1" not in df.columns:
        return None
    df["TRDPRC_1"] = pd.to_numeric(df["TRDPRC_1"], errors="coerce")
    df = df[df["TRDPRC_1"] > 0]
    if len(df) < 10:
        logger.debug("%s %s: only %d ticks, skipping", symbol, day, len(df))
        return None

    prices = df["TRDPRC_1"].values.astype(np.float64)
    log_prices = np.log(prices)

    rk_value = realized_kernel(log_prices)

    # noise_gap denominator: prefer panel's pre-computed rv (avoids resample)
    if rv_5min is not None and rv_5min > 0:
        gap = compute_noise_gap(rk_value, rv_5min)
    else:
        # Fallback: resample ticks to 5-min bars
        df["Time"] = pd.to_datetime(df["Time"])
        df = df.set_index("Time")
        bars_5min = df["TRDPRC_1"].resample("5min").last().dropna()
        if len(bars_5min) >= 2:
            log_returns_5min = np.diff(np.log(bars_5min.values))
            rv_from_ticks = float(np.sum(log_returns_5min**2))
        else:
            rv_from_ticks = rk_value
        gap = compute_noise_gap(rk_value, rv_from_ticks)

    return {
        "date": day,
        "rk": rk_value,
        "noise_gap": gap,
        "n_ticks": len(prices),
    }


def _fetch_and_compute_rk_batch(
    symbol: str,
    days: list[date],
    rv_lookup: dict[date, float | None],
    timeout_s: float = 120.0,
) -> list[dict]:
    """Fetch raw ticks for multiple days in ONE chunk_query and compute RK per day.

    Batching N days into a single API call eliminates N-1 round-trips worth of
    TCP/session overhead. For TRDPRC_1-only payloads this is safe up to ~5 days.

    Returns a list of result dicts (same schema as _fetch_and_compute_rk_one_day).
    """
    from volforecast.data.chunk_store import (
        CHUNKDB,
        TICKER_TO_RIC,
        TZ,
        _chunk_query_with_timeout,
        _ensure_session,
        _resolve_es_symbol,
        query,
    )
    from volforecast.data.measures import noise_gap as compute_noise_gap
    from volforecast.data.measures import realized_kernel

    if query is None:
        raise ConnectionError("pytickclient not available.")
    _ensure_session()

    chunk_symbol = (
        _resolve_es_symbol(days[0]) if symbol == "ES" else TICKER_TO_RIC.get(symbol, symbol)
    )

    # Span the full date range in one query
    first_day = days[0]
    last_day = days[-1]
    st = TZ.localize(datetime(first_day.year, first_day.month, first_day.day, 9, 30, 0))
    et = TZ.localize(datetime(last_day.year, last_day.month, last_day.day, 16, 0, 0))

    # Scale timeout with batch size — more days = bigger payload.
    # Base timeout covers 1 day; each extra day adds 50% more time.
    scaled_timeout = timeout_s * (1 + 0.5 * (len(days) - 1))

    raw = _chunk_query_with_timeout(
        [chunk_symbol],
        st,
        et,
        CHUNKDB,
        _RK_FIELDS,
        timeout_s=scaled_timeout,
        retries=2,
    )

    df = pd.DataFrame(raw)
    if df.empty and len(days) > 1:
        # Multi-day call returned nothing (likely timeout) — fall back to per-day
        logger.info(
            "%s %s-%s: multi-day fetch empty, falling back to per-day",
            symbol,
            first_day,
            last_day,
        )
        all_results: list[dict] = []
        for day in days:
            single = _fetch_and_compute_rk_one_day(symbol, day, rv_lookup.get(day), timeout_s)
            if single is not None:
                all_results.append(single)
        return all_results

    if df.empty:
        logger.debug("%s %s-%s: no ticks", symbol, first_day, last_day)
        return []

    if "TRDPRC_1" not in df.columns:
        return []

    df["TRDPRC_1"] = pd.to_numeric(df["TRDPRC_1"], errors="coerce")
    df = df[df["TRDPRC_1"] > 0]
    if df.empty:
        return []

    # Parse timestamps and split by date
    df["Time"] = pd.to_datetime(df["Time"])
    if df["Time"].dt.tz is None:
        df["Time"] = df["Time"].dt.tz_localize("UTC").dt.tz_convert(TZ)
    else:
        df["Time"] = df["Time"].dt.tz_convert(TZ)
    df["_date"] = df["Time"].dt.date

    results: list[dict] = []
    requested_dates = set(days)

    for day, grp in df.groupby("_date"):
        if day not in requested_dates:
            continue
        # Filter to market hours
        mask = (grp["Time"].dt.time >= pd.Timestamp("09:30").time()) & (
            grp["Time"].dt.time <= pd.Timestamp("16:00").time()
        )
        grp = grp[mask]
        if len(grp) < 10:
            logger.debug("%s %s: only %d ticks, skipping", symbol, day, len(grp))
            continue

        prices = grp["TRDPRC_1"].values.astype(np.float64)
        log_prices = np.log(prices)
        rk_value = realized_kernel(log_prices)

        rv_5min = rv_lookup.get(day)
        if rv_5min is not None and rv_5min > 0:
            gap = compute_noise_gap(rk_value, rv_5min)
        else:
            # Fallback: resample ticks to 5-min bars
            grp_ts = grp.set_index("Time")
            bars_5min = grp_ts["TRDPRC_1"].resample("5min").last().dropna()
            if len(bars_5min) >= 2:
                log_returns_5min = np.diff(np.log(bars_5min.values))
                rv_from_ticks = float(np.sum(log_returns_5min**2))
            else:
                rv_from_ticks = rk_value
            gap = compute_noise_gap(rk_value, rv_from_ticks)

        results.append(
            {
                "date": day,
                "rk": rk_value,
                "noise_gap": gap,
                "n_ticks": len(prices),
            }
        )

    return results


def backfill_symbol(
    symbol: str,
    cache_dir: Path,
    workers: int = 4,
    batch_days: int = 10,
    timeout_s: float = 120.0,
    progress: object | None = None,
) -> int:
    """Backfill RK for one symbol. Returns number of days filled.

    Parameters
    ----------
    progress : StageProgress | None
        If provided, updates nested subtask bars for live progress display.
    """
    from volforecast.cli.progress import StageProgress, _format_elapsed

    panel = pd.read_parquet(cache_dir / f"{symbol}.parquet")
    if hasattr(panel.index, "date"):
        panel.index = panel.index.date
    panel.index.name = "date"

    nan_dates = _get_nan_rk_dates(panel)
    if not nan_dates:
        logger.info("%s: no NaN rk dates — already complete", symbol)
        return 0

    total = len(nan_dates)

    # Ensure columns exist
    if "rk" not in panel.columns:
        panel["rk"] = np.nan
    if "noise_gap" not in panel.columns:
        panel["noise_gap"] = np.nan

    # Pre-extract rv values for noise_gap (avoids per-day tick resample)
    rv_lookup: dict[date, float | None] = {}
    if "rv" in panel.columns:
        for d in nan_dates:
            val = panel.at[d, "rv"] if d in panel.index else None
            try:
                fval = float(val)  # type: ignore[arg-type]
                rv_lookup[d] = fval if not np.isnan(fval) else None
            except (TypeError, ValueError):
                rv_lookup[d] = None
    else:
        rv_lookup = {d: None for d in nan_dates}

    # Progress: add symbol-level subtask bar
    sym_sub_key: str | None = None
    detail_key: str | None = None
    sp: StageProgress | None = progress if isinstance(progress, StageProgress) else None

    if sp is not None:
        sym_sub_key = sp.add_subtask(
            total=total,
            description=f"{symbol} (0/{total} days)",
        )

    filled = 0
    errors = 0
    t0 = time.time()

    # Process in batches with checkpointing.
    # Each "batch" is a checkpoint interval (batch_days).
    # Within each batch, we issue multi-day API calls (_FETCH_BATCH_SIZE days each)
    # to minimize round-trips. The secexpr subprocess serializes internally, so
    # day-level thread parallelism is counterproductive — sequential multi-day
    # calls are faster and more reliable.
    #
    # Adaptive sub-batch size: high-volume symbols (SPY ~280K ticks/day) need
    # smaller sub-batches to avoid payload timeouts. Low-volume symbols can
    # batch more aggressively.
    _HIGH_VOLUME = {"SPY", "QQQ", "IWM", "DIA", "AAPL", "NVDA", "TSLA", "AMZN", "META", "MSFT"}
    _FETCH_BATCH_SIZE = 2 if symbol in _HIGH_VOLUME else 5
    batches = [nan_dates[i : i + batch_days] for i in range(0, total, batch_days)]

    for batch_idx, batch in enumerate(batches):
        results: list[dict] = []

        # Show detail bar for batch
        if sp is not None and sym_sub_key is not None:
            batch_desc = (
                f"[dim]batch {batch_idx + 1}/{len(batches)}: "
                f"{batch[0]}\u2212{batch[-1]} ({len(batch)} days)[/dim]"
            )
            if detail_key is not None:
                sp.update_subtask(detail_key, batch_desc, indent=2)
            else:
                detail_key = sp.add_subtask(
                    total=None,
                    description=batch_desc,
                    indent=2,
                )

        # Split batch into sub-batches of _FETCH_BATCH_SIZE for multi-day API calls
        sub_batches = [
            batch[i : i + _FETCH_BATCH_SIZE] for i in range(0, len(batch), _FETCH_BATCH_SIZE)
        ]

        for sub_batch in sub_batches:
            try:
                sub_results = _fetch_and_compute_rk_batch(
                    symbol,
                    sub_batch,
                    rv_lookup,
                    timeout_s,
                )
                results.extend(sub_results)
                # Days with no data in the response are counted as errors
                errors += len(sub_batch) - len(sub_results)
            except Exception as exc:
                logger.warning(
                    "%s: sub-batch %s-%s failed: %s",
                    symbol,
                    sub_batch[0],
                    sub_batch[-1],
                    exc,
                )
                errors += len(sub_batch)

            # Update detail bar with progress within batch
            if sp is not None and detail_key is not None:
                sp.update_subtask(
                    detail_key,
                    f"[dim]batch {batch_idx + 1}/{len(batches)}: "
                    f"{len(results)}/{len(batch)} days done[/dim]",
                    indent=2,
                )

        # Merge results into panel
        for r in results:
            d = r["date"]
            if d in panel.index:
                panel.at[d, "rk"] = r["rk"]
                panel.at[d, "noise_gap"] = r["noise_gap"]
                filled += 1

        # Checkpoint after each batch
        panel.to_parquet(cache_dir / f"{symbol}.parquet")

        # Advance symbol subtask bar
        if sp is not None and sym_sub_key is not None:
            sp.advance(sym_sub_key, advance=len(batch))
            sp.update_subtask(
                sym_sub_key,
                f"{symbol} ({min(filled + errors, total)}/{total} days, {filled} ok, {errors} err)",
            )

    # Remove detail subtask
    if sp is not None and detail_key is not None:
        sp.remove_subtask(detail_key)

    elapsed_total = time.time() - t0
    # Log completion
    if sp is not None:
        if sym_sub_key is not None:
            sp.remove_subtask(sym_sub_key)
        sp.log(
            f"{symbol}: {filled}/{total} days filled, "
            f"{errors} errors [{_format_elapsed(elapsed_total)}]"
        )

    return filled


def _backfill_symbol_wrapper(
    symbol: str,
    cache_dir: Path,
    workers: int,
    batch_days: int,
    timeout_s: float,
    progress: object | None,
    lock: threading.Lock,
    sym_task_key: str | None,
    counter: dict,
    total_symbols: int,
) -> tuple[str, int]:
    """Wrapper for parallel symbol execution with progress updates."""
    from volforecast.cli.progress import StageProgress

    filled = backfill_symbol(symbol, cache_dir, workers, batch_days, timeout_s, progress)
    with lock:
        counter["done"] += 1
        if isinstance(progress, StageProgress) and sym_task_key is not None:
            progress.advance(sym_task_key)
    return symbol, filled


def run(
    symbols: list[str] | None = None,
    symbol_workers: int = 1,
    workers: int = 4,
    batch_days: int = 10,
    timeout_s: float = 120.0,
    dry_run: bool = False,
) -> dict[str, int]:
    """Run RK backfill for all symbols.

    Parameters
    ----------
    symbols : list[str] | None
        Subset of symbols to process (default: all cached).
    symbol_workers : int
        Number of symbols to process concurrently (default: 1).
    workers : int
        Parallel day-fetch threads *per symbol* (default: 4).
    batch_days : int
        Days per checkpoint batch (default: 10).
    timeout_s : float
        Timeout per API call (default: 120).
    dry_run : bool
        If True, show NaN counts without fetching.
    """
    from volforecast.cli.console import console
    from volforecast.cli.progress import StageProgress, _format_elapsed
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

    if not target:
        logger.error("No symbols to process")
        return {}

    # Pre-scan: count NaN dates per symbol
    sym_nan_counts: dict[str, int] = {}
    total_nan = 0
    for sym in target:
        panel = pd.read_parquet(cache / f"{sym}.parquet")
        if hasattr(panel.index, "date"):
            panel.index = panel.index.date
        nan_count = len(_get_nan_rk_dates(panel))
        sym_nan_counts[sym] = nan_count
        total_nan += nan_count

    if dry_run:
        console.print(f"\n[bold]RK Backfill — Dry Run[/bold]  ({len(target)} symbols)\n")
        for sym in target:
            nan_count = sym_nan_counts[sym]
            console.print(f"  {sym:8s}: {nan_count:5,} days need backfill")
        console.print(f"\n  [bold]TOTAL: {total_nan:,} day-symbol pairs[/bold]")
        console.print(f"  Fields: {_RK_FIELDS} (minimal fetch)")
        console.print(
            f"  Config: symbol_workers={symbol_workers}, "
            f"workers={workers}, batch_days={batch_days}\n"
        )
        return {}

    # Use StageProgress for rich display
    with StageProgress("backfill-rk", "rk-backfill", target) as sp:
        # Top-level bar: symbols
        sym_task_key = sp.add_task(total=len(target), description="symbols")

        sp.log(
            f"{total_nan:,} total days across {len(target)} symbols "
            f"| {symbol_workers} sym-workers × {workers} day-workers"
        )

        results: dict[str, int] = {}
        overall_t0 = time.time()

        if symbol_workers <= 1:
            # Sequential: get nice nested bars per symbol
            for sym in target:
                if sym_nan_counts[sym] == 0:
                    sp.advance(sym_task_key)
                    sp.log(f"{sym}: already complete")
                    results[sym] = 0
                    continue
                filled = backfill_symbol(
                    sym,
                    cache,
                    workers,
                    batch_days,
                    timeout_s,
                    progress=sp,
                )
                results[sym] = filled
                sp.advance(sym_task_key)
        else:
            # Parallel: subtask bars managed per-symbol inside backfill_symbol
            lock = threading.Lock()
            counter = {"done": 0}

            with ThreadPoolExecutor(max_workers=symbol_workers) as pool:
                futures = {
                    pool.submit(
                        _backfill_symbol_wrapper,
                        sym,
                        cache,
                        workers,
                        batch_days,
                        timeout_s,
                        sp,
                        lock,
                        sym_task_key,
                        counter,
                        len(target),
                    ): sym
                    for sym in target
                }
                for future in as_completed(futures):
                    sym = futures[future]
                    try:
                        _, filled = future.result()
                        results[sym] = filled
                    except Exception as exc:
                        logger.error("%s: symbol backfill failed: %s", sym, exc)
                        results[sym] = 0
                        with lock:
                            counter["done"] += 1
                            sp.advance(sym_task_key)

        overall_elapsed = time.time() - overall_t0
        total_filled = sum(results.values())
        total_errors = total_nan - total_filled

        sp.finish(
            f"{total_filled:,} days filled across {len(target)} symbols, "
            f"{total_errors:,} errors [{_format_elapsed(overall_elapsed)}]"
        )

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
            workers=args.workers,
            batch_days=args.batch_days,
            timeout_s=args.timeout,
            dry_run=args.dry_run,
        )
    except ConnectionError as e:
        from volforecast.cli.console import console

        console.print(f"[red bold]ERROR:[/] {e}")
        return 1
    except KeyboardInterrupt:
        from volforecast.cli.console import console

        console.print("\n[yellow]Interrupted by user. Progress has been checkpointed.[/yellow]")
        return 130

    return 0


def register(subparsers) -> None:
    """Register the backfill-rk subcommand."""
    parser = subparsers.add_parser(
        "backfill-rk",
        help="Backfill realized kernel (RK) and noise_gap from raw ticks",
    )
    parser.add_argument(
        "--symbols", type=str, default=None, help="Comma-separated symbols (default: all cached)"
    )
    parser.add_argument(
        "--symbol-workers",
        type=int,
        default=1,
        help="Number of symbols to process concurrently (default: 1)",
    )
    parser.add_argument(
        "--workers", type=int, default=4, help="Parallel fetch threads per symbol (default: 4)"
    )
    parser.add_argument(
        "--batch-days", type=int, default=10, help="Days per checkpoint batch (default: 10)"
    )
    parser.add_argument(
        "--timeout", type=float, default=120.0, help="Timeout per API call in seconds"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show NaN counts without fetching"
    )
    parser.set_defaults(func=handle)


def handle(args) -> int:
    """Execute backfill-rk command. Return exit code."""
    symbols = args.symbols.split(",") if args.symbols else None
    run(
        symbols=symbols,
        symbol_workers=args.symbol_workers,
        workers=args.workers,
        batch_days=args.batch_days,
        timeout_s=args.timeout,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
