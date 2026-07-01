"""RV panel builder -- ticks to Pipeline-ready daily DataFrame.

Orchestrates: trading calendar -> batch-fetch ticks -> compute daily RV -> cache.
Output is directly compatible with Pipeline.run().

Architecture: streaming batch pipeline.
  For each sub-batch: fetch -> compute (optionally parallel) -> checkpoint -> release.
  Peak memory is bounded to one sub-batch of tick data at a time.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd

from volforecast.constants import SYMBOL_UNIVERSE
from volforecast.data.chunk_store import fetch_bars, fetch_trades_batch
from volforecast.data.resample import compute_daily_rv_from_bars, compute_daily_rv_from_ticks
from volforecast.data.trading_calendar import get_trading_days
from volforecast.data.tsdb import fetch_daily_ohlcv

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers: compute records from day frames
# ---------------------------------------------------------------------------


# Sentinel for skipped days — returned instead of None so callers can
# distinguish "skipped with reason" from unexpected errors.
_SKIP_NO_TICKS = "no_ticks"
_SKIP_LOW_TICKS = "low_ticks"


def _compute_day_record(
    day: date,
    trades: pd.DataFrame,
    symbol: str,
    freq: str,
    min_ticks: int,
) -> dict | tuple[date, str]:
    """Compute RV measures for a single day's trades.

    Returns a measures dict ready for panel appending, or a
    (date, reason) tuple if the day should be skipped.
    """
    if trades.empty:
        logger.warning("No ticks for %s on %s -- skipping", symbol, day)
        return (day, _SKIP_NO_TICKS)

    measures = compute_daily_rv_from_ticks(trades, freq=freq)

    if measures["n_ticks"] < min_ticks:
        logger.warning(
            "%s on %s: only %d ticks (min=%d) -- skipping",
            symbol,
            day,
            measures["n_ticks"],
            min_ticks,
        )
        return (day, _SKIP_LOW_TICKS)

    measures["date"] = day
    measures["jump_indicator"] = int(measures["jump_indicator"])
    measures["symbol"] = symbol
    return measures


def _compute_batch_records(
    day_trades: dict[date, pd.DataFrame],
    symbol: str,
    freq: str,
    min_ticks: int,
    max_workers: int = 1,
) -> tuple[list[dict], int, list[tuple[date, str]], float]:
    """Compute RV records for a batch of day frames.

    Parameters
    ----------
    day_trades : dict[date, DataFrame]
        Tick data keyed by date.
    symbol, freq, min_ticks : ...
        Passed through to _compute_day_record.
    max_workers : int
        If > 1, compute days in parallel using threads.

    Returns
    -------
    records : list[dict]
        Successfully computed day records (may be fewer than input days).
    skipped : int
        Number of skipped days (empty or below min_ticks).
    skipped_dates : list[tuple[date, str]]
        List of (date, reason) for each skipped day.
    elapsed_s : float
        Wall-clock time for the batch compute.
    """
    t0 = time.perf_counter()
    sorted_days = sorted(day_trades.keys())
    records: list[dict] = []
    skipped = 0
    skipped_dates: list[tuple[date, str]] = []

    if max_workers <= 1 or len(sorted_days) <= 1:
        for day in sorted_days:
            result = _compute_day_record(
                day,
                day_trades[day],
                symbol,
                freq,
                min_ticks,
            )
            if isinstance(result, tuple):
                skipped += 1
                skipped_dates.append(result)
            else:
                records.append(result)
    else:
        with ThreadPoolExecutor(max_workers=min(max_workers, len(sorted_days))) as pool:
            futures = {
                pool.submit(
                    _compute_day_record,
                    day,
                    day_trades[day],
                    symbol,
                    freq,
                    min_ticks,
                ): day
                for day in sorted_days
            }
            day_results: dict[date, dict | tuple[date, str] | None] = {}
            for future in as_completed(futures):
                day = futures[future]
                try:
                    day_results[day] = future.result()
                except Exception:  # noqa: BLE001
                    logger.error(
                        "%s: compute failed for %s",
                        symbol,
                        day,
                        exc_info=True,
                    )
                    day_results[day] = None
            # Maintain deterministic order
            for day in sorted_days:
                result = day_results.get(day)
                if result is None:
                    skipped += 1
                    skipped_dates.append((day, "compute_error"))
                elif isinstance(result, tuple):
                    skipped += 1
                    skipped_dates.append(result)
                else:
                    records.append(result)

    return records, skipped, skipped_dates, time.perf_counter() - t0


def _compute_bar_batch_records(
    day_bars: dict[date, pd.DataFrame],
    symbol: str,
    min_bars: int = 10,
) -> tuple[list[dict], int, list[tuple[date, str]], float]:
    """Compute RV records from pre-aggregated bars for a batch of days.

    Parameters
    ----------
    day_bars : dict[date, DataFrame]
        Bar data keyed by date (from fetch_bars).
    symbol : str
        Ticker symbol.
    min_bars : int
        Minimum number of bars required per day.

    Returns
    -------
    records, skipped, skipped_dates, elapsed_s
    """
    t0 = time.perf_counter()
    records: list[dict] = []
    skipped = 0
    skipped_dates: list[tuple[date, str]] = []

    for day in sorted(day_bars.keys()):
        bars = day_bars[day]
        if bars.empty or len(bars) < 2:
            logger.warning("No bars for %s on %s -- skipping", symbol, day)
            skipped += 1
            skipped_dates.append((day, _SKIP_NO_TICKS))
            continue

        if len(bars) < min_bars:
            logger.warning(
                "%s on %s: only %d bars (min=%d) -- skipping",
                symbol,
                day,
                len(bars),
                min_bars,
            )
            skipped += 1
            skipped_dates.append((day, _SKIP_LOW_TICKS))
            continue

        try:
            measures = compute_daily_rv_from_bars(bars)
        except (ValueError, ZeroDivisionError) as exc:
            logger.error("%s: bar compute failed for %s: %s", symbol, day, exc)
            skipped += 1
            skipped_dates.append((day, "compute_error"))
            continue

        measures["date"] = day
        measures["jump_indicator"] = int(measures["jump_indicator"])
        measures["symbol"] = symbol
        records.append(measures)

    return records, skipped, skipped_dates, time.perf_counter() - t0


def build_rv_panel(
    symbol: str,
    start_date: date,
    end_date: date,
    freq: str = "5min",
    min_ticks: int = 100,
    cache_dir: Path | None = None,
    progress=None,
    max_workers: int = 4,
    batch_size: int = 5,
    checkpoint_interval: int = 1,
    timeout_s: float = 120.0,
    retries: int = 2,
    compute_workers: int | None = None,
    mode: str = "bars",
    throttle_s: float = 0.0,
) -> pd.DataFrame:
    """Build a daily RV panel for a single symbol.

    Streaming architecture: fetches tick data in sub-batches, computes
    RV measures immediately per batch, checkpoints, and releases tick
    memory before fetching the next batch.

    Parameters
    ----------
    symbol : str
        Ticker symbol (must be in SYMBOL_UNIVERSE).
    start_date, end_date : date
        Date range (inclusive).
    freq : str
        Bar sampling frequency (default: '5min').
    min_ticks : int
        Minimum number of raw ticks required per day (default: 100).
    cache_dir : Path, optional
        Directory for parquet cache.
    progress : ExperimentProgress | StageProgress | None
        Progress display handle for day-level subtask updates.
    max_workers : int
        Number of parallel threads for batch fetching (default: 4).
    batch_size : int
        Max trading days per single API call (default: 5).
    checkpoint_interval : int
        Save cache every N processed days (default: 1).
    timeout_s : float
        Timeout per API call in seconds (default: 120).
    retries : int
        Retries per failed API call (default: 2).
    compute_workers : int, optional
        Number of threads for parallel compute within a batch.
        Defaults to max_workers if not set.
    mode : str
        Fetch mode: 'bars' (default, fast -- server-side aggregation) or
        'ticks' (legacy -- raw tick fetch + client-side resampling).
        'bars' does NOT compute rk or noise_gap (returns NaN for those).
    throttle_s : float
        Seconds to sleep between API batches to avoid rate limiting (default: 0).

    Returns
    -------
    pd.DataFrame
        Daily RV panel. Index: date-based (name='date').
    """
    if symbol not in SYMBOL_UNIVERSE:
        raise ValueError(
            f"Symbol '{symbol}' not in the universe. Valid symbols: {sorted(SYMBOL_UNIVERSE)}"
        )

    if compute_workers is None:
        compute_workers = max_workers

    trading_days = get_trading_days(start_date, end_date)

    # Load cache if available
    cached_panel = None
    if cache_dir is not None:
        cached_panel = load_rv_cache(symbol, cache_dir)

    # Determine which dates need fetching
    if cached_panel is not None:
        cached_dates = set(cached_panel.index.tolist())
        missing_days = [d for d in trading_days if d not in cached_dates]
        n_cached = len(trading_days) - len(missing_days)
        if n_cached > 0:
            logger.info(
                "%s: %d/%d days already cached, fetching %d missing",
                symbol,
                n_cached,
                len(trading_days),
                len(missing_days),
            )
    else:
        missing_days = trading_days

    total = len(missing_days)
    if total == 0:
        logger.info("%s: fully cached (%d days), nothing to fetch", symbol, len(trading_days))
        panel = cached_panel if cached_panel is not None else pd.DataFrame()
        if not panel.empty:
            panel = panel.loc[(panel.index >= start_date) & (panel.index <= end_date)]
        panel.attrs["skipped_dates"] = []
        return panel

    # Set up subtask progress
    _sub_key: str | None = None
    n_cached = len(trading_days) - total
    desc_prefix = f"{symbol} ({n_cached} cached, " if n_cached > 0 else f"{symbol} ("
    if progress is not None:
        from volforecast.cli.progress import ExperimentProgress

        if isinstance(progress, ExperimentProgress):
            _sub_key = progress.add_subtask(
                "INGEST", total=total, description=f"{desc_prefix}0/{total} fetching)"
            )
        else:
            _sub_key = progress.add_subtask(
                total=total, description=f"{desc_prefix}0/{total} fetching)"
            )

    # ── Streaming pipeline: fetch -> compute -> checkpoint per batch ──
    # Each sub-batch (batch_size days) is an atomic unit:
    #   fetch -> compute -> checkpoint -> release memory.
    # This ensures interruption loses at most one sub-batch of work.
    sub_batches = [missing_days[i : i + batch_size] for i in range(0, total, batch_size)]

    records: list[dict] = []
    all_skipped_dates: list[tuple[date, str]] = []
    total_fetch_s = 0.0
    total_compute_s = 0.0
    days_processed = 0
    skipped = 0
    batch_times: list[float] = []
    batches_since_checkpoint = 0

    # Detail subtask: pulsing row for live API call status (created lazily on first fetch)
    _detail_key: str | None = None

    def _on_chunk_status(
        event: str,
        chunk_dates: list[date],
        n_ticks: int,
        elapsed_s: float,
    ) -> None:
        """Update the pulsing detail row below the progress bar."""
        nonlocal _detail_key
        if progress is None:
            return
        # Lazily create the detail bar on the first callback
        if _detail_key is None:
            from volforecast.cli.progress import ExperimentProgress as _EP

            if isinstance(progress, _EP):
                _detail_key = progress.add_subtask(
                    "INGEST",
                    total=None,
                    description="",
                    indent=2,
                )
            else:
                _detail_key = progress.add_subtask(
                    total=None,
                    description="",
                    indent=2,
                )
        if _detail_key is None:
            return
        first, last = chunk_dates[0], chunk_dates[-1]
        if first == last:
            range_str = first.strftime("%b %d")
        else:
            range_str = f"{first.strftime('%b %d')}\u2013{last.strftime('%b %d')}"

        if event == "start":
            progress.update_subtask(
                _detail_key,
                f"[dim]querying {range_str}[/dim]",
                indent=2,
            )
        elif event == "done":
            progress.update_subtask(
                _detail_key,
                f"[dim]fetched {range_str} ({n_ticks:,} ticks, {elapsed_s:.0f}s)[/dim]",
                indent=2,
            )

    for batch_idx, sb in enumerate(sub_batches):
        # Throttle between batches to avoid Chunk Store rate limits
        if batch_idx > 0 and throttle_s > 0:
            time.sleep(throttle_s)

        t0 = time.perf_counter()
        _on_fetch = _on_chunk_status if progress is not None else None

        if mode == "bars":
            # ── Fast path: server-side aggregation ────────────────────
            batch_day_bars = fetch_bars(
                symbol,
                sb,
                batch_size=batch_size,
                timeout_s=timeout_s,
                retries=retries,
            )
            fetch_elapsed = time.perf_counter() - t0
            total_fetch_s += fetch_elapsed

            batch_records, batch_skipped, batch_skipped_dates, compute_elapsed = (
                _compute_bar_batch_records(batch_day_bars, symbol)
            )
            del batch_day_bars
        else:
            # ── Legacy path: raw tick fetch + client resample ─────────
            batch_day_trades = fetch_trades_batch(
                symbol,
                sb,
                batch_size=batch_size,
                timeout_s=timeout_s,
                retries=retries,
                on_fetch=_on_fetch,
            )
            fetch_elapsed = time.perf_counter() - t0
            total_fetch_s += fetch_elapsed

            batch_records, batch_skipped, batch_skipped_dates, compute_elapsed = (
                _compute_batch_records(
                    batch_day_trades,
                    symbol,
                    freq,
                    min_ticks,
                    max_workers=compute_workers,
                )
            )
            del batch_day_trades
        total_compute_s += compute_elapsed
        skipped += batch_skipped
        all_skipped_dates.extend(batch_skipped_dates)
        records.extend(batch_records)
        days_processed += len(sb)

        # Track timing for ETA
        per_day = (fetch_elapsed + compute_elapsed) / max(len(sb), 1)
        batch_times.append(per_day)

        # ── Update progress ───────────────────────────────────────────
        if _sub_key is not None and progress is not None:
            avg_per_day = sum(batch_times) / len(batch_times)
            remaining = total - days_processed
            eta_str = _format_eta(avg_per_day * remaining)
            status = (
                f"{symbol} ({days_processed}/{total} days, "
                f"avg {avg_per_day:.1f}s/day, ETA {eta_str})"
            )
            _update_progress_desc(progress, _sub_key, status)
            progress.advance(_sub_key, advance=len(sb))

        # ── Checkpoint ────────────────────────────────────────────────
        batches_since_checkpoint += 1
        if (
            cache_dir is not None
            and (len(records) > 0 or len(all_skipped_dates) > 0)
            and batches_since_checkpoint >= checkpoint_interval
        ):
            _save_checkpoint(records, all_skipped_dates, cached_panel, symbol, cache_dir)
            batches_since_checkpoint = 0

    # Remove progress bars after symbol completes
    if _detail_key is not None and progress is not None:
        progress.remove_subtask(_detail_key)
    if _sub_key is not None and progress is not None:
        progress.remove_subtask(_sub_key)

    # Log timing breakdown
    avg_day = f"{sum(batch_times) / len(batch_times):.2f}s" if batch_times else "n/a"
    logger.info(
        "%s: %d days processed (%d skipped) -- fetch %.1fs, compute %.1fs, avg/day %s",
        symbol,
        len(records),
        skipped,
        total_fetch_s,
        total_compute_s,
        avg_day,
    )

    # P2 guard: fail loudly if RECENT days returned no data (connectivity issue).
    # Only considers the last 20 attempted days — scattered historical misses
    # (e.g. old futures contracts not in Chunk Store) are normal.
    if total > 2 and skipped > 0:
        recent_window = min(20, total)
        recent_days = missing_days[-recent_window:]
        recent_skipped_dates = {d for d, _ in all_skipped_dates}
        recent_failures = sum(1 for d in recent_days if d in recent_skipped_dates)
        recent_ratio = recent_failures / recent_window
        if recent_ratio > 0.8:
            raise RuntimeError(
                f"{symbol}: {recent_failures}/{recent_window} recent days "
                f"({recent_ratio:.0%}) returned no data. "
                f"Likely cause: pyslang session died or Chunk Store connectivity lost. "
                f"Refusing to save an incomplete panel."
            )

    # Build new panel from fetched records + NaN sentinels for skipped dates.
    # Sentinel rows (rv=NaN) mark dates as "attempted, no data" so they
    # won't be re-fetched on subsequent runs.
    new_panel = pd.DataFrame(records).set_index("date") if records else pd.DataFrame()
    if all_skipped_dates:
        sentinel_dates = [
            d for d, reason in all_skipped_dates if reason in (_SKIP_NO_TICKS, _SKIP_LOW_TICKS)
        ]
        if sentinel_dates and not new_panel.empty:
            sentinel_rows = pd.DataFrame(
                {col: float("nan") for col in new_panel.columns},
                index=sentinel_dates,
            )
            sentinel_rows.index.name = "date"
            # Mark sentinels so we can identify them later
            sentinel_rows["n_ticks"] = 0
            sentinel_rows["n_bars"] = 0
            new_panel = pd.concat([new_panel, sentinel_rows])
            new_panel = new_panel[~new_panel.index.duplicated(keep="first")]
            new_panel = new_panel.sort_index()
        elif sentinel_dates and new_panel.empty:
            # All days were skipped — still record sentinels
            cols = [
                "rv",
                "log_rv",
                "rq",
                "rtq",
                "bpv",
                "rs_positive",
                "rs_negative",
                "jump_stat",
                "jump_indicator",
                "continuous_variation",
                "jump_variation",
                "j_positive",
                "j_negative",
                "realized_skewness",
                "realized_kurtosis",
                "rk",
                "noise_gap",
                "n_ticks",
                "n_bars",
            ]
            sentinel_rows = pd.DataFrame(
                {col: float("nan") for col in cols},
                index=sentinel_dates,
            )
            sentinel_rows.index.name = "date"
            sentinel_rows["n_ticks"] = 0
            sentinel_rows["n_bars"] = 0
            new_panel = sentinel_rows

    # Merge with cache
    if cached_panel is not None and not new_panel.empty:
        panel = pd.concat([cached_panel, new_panel]).sort_index()
    elif cached_panel is not None:
        panel = cached_panel
    else:
        panel = new_panel

    # Filter to requested date range (cache may have wider range)
    if not panel.empty:
        panel = panel.loc[(panel.index >= start_date) & (panel.index <= end_date)]

    # Save updated cache (includes sentinels for skipped dates)
    if cache_dir is not None and not panel.empty:
        full_panel = panel
        if cached_panel is not None and not new_panel.empty:
            full_panel = pd.concat([cached_panel, new_panel]).sort_index()
            full_panel = full_panel[~full_panel.index.duplicated(keep="last")]
        save_rv_cache(full_panel, symbol, cache_dir)
    elif cache_dir is not None and not new_panel.empty:
        # Panel is empty after date filter but new_panel has sentinels
        full_panel = new_panel
        if cached_panel is not None:
            full_panel = pd.concat([cached_panel, new_panel]).sort_index()
            full_panel = full_panel[~full_panel.index.duplicated(keep="last")]
        save_rv_cache(full_panel, symbol, cache_dir)

    # Attach skipped-date metadata for downstream manifest recording
    panel.attrs["skipped_dates"] = all_skipped_dates

    # Return only rows with actual data (exclude NaN sentinel rows)
    if not panel.empty and "rv" in panel.columns:
        panel = panel[panel["rv"].notna()]

    return panel


def _format_eta(seconds: float) -> str:
    """Format seconds into a human-readable ETA string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        m, s = divmod(int(seconds), 60)
        return f"{m}m{s:02d}s"
    h, remainder = divmod(int(seconds), 3600)
    m, _ = divmod(remainder, 60)
    return f"{h}h{m:02d}m"


def _update_progress_desc(progress, sub_key: str | None, description: str) -> None:
    """Update subtask description text without advancing."""
    if sub_key is None or progress is None:
        return
    progress.update_subtask(sub_key, description)


def _save_checkpoint(
    records: list[dict],
    skipped_dates: list[tuple[date, str]],
    cached_panel: pd.DataFrame | None,
    symbol: str,
    cache_dir: Path,
) -> None:
    """Save partial progress to parquet cache (includes NaN sentinels for skipped days)."""
    if records:
        new_panel = pd.DataFrame(records).set_index("date")
    else:
        new_panel = pd.DataFrame()

    # Add NaN sentinel rows for skipped dates
    sentinel_dates = [
        d for d, reason in skipped_dates if reason in (_SKIP_NO_TICKS, _SKIP_LOW_TICKS)
    ]
    if sentinel_dates:
        if not new_panel.empty:
            sentinel_rows = pd.DataFrame(
                {col: float("nan") for col in new_panel.columns},
                index=sentinel_dates,
            )
            sentinel_rows["n_ticks"] = 0
            sentinel_rows["n_bars"] = 0
        elif cached_panel is not None and not cached_panel.empty:
            sentinel_rows = pd.DataFrame(
                {col: float("nan") for col in cached_panel.columns},
                index=sentinel_dates,
            )
            sentinel_rows["n_ticks"] = 0
            sentinel_rows["n_bars"] = 0
        else:
            sentinel_rows = pd.DataFrame()

        if not sentinel_rows.empty:
            new_panel = (
                pd.concat([new_panel, sentinel_rows]) if not new_panel.empty else sentinel_rows
            )
            new_panel = new_panel[~new_panel.index.duplicated(keep="first")]
            new_panel = new_panel.sort_index()

    if new_panel.empty and cached_panel is None:
        return

    if cached_panel is not None and not new_panel.empty:
        full = pd.concat([cached_panel, new_panel]).sort_index()
        full = full[~full.index.duplicated(keep="last")]
    elif cached_panel is not None:
        full = cached_panel
    else:
        full = new_panel
    save_rv_cache(full, symbol, cache_dir)
    logger.debug("Checkpoint: saved %d rows for %s", len(full), symbol)


def load_rv_cache(symbol: str, cache_dir: Path) -> pd.DataFrame | None:
    """Load cached RV panel from parquet.

    Parameters
    ----------
    symbol : str
        Ticker symbol.
    cache_dir : Path
        Directory containing cache files.

    Returns
    -------
    pd.DataFrame or None
        Cached panel, or None if no cache exists.
    """
    path = Path(cache_dir) / f"{symbol}.parquet"
    if not path.exists():
        return None
    panel = pd.read_parquet(path)
    # Ensure index is date objects (not Timestamps)
    if hasattr(panel.index, "date"):
        panel.index = panel.index.date
    panel.index.name = "date"
    return panel


def save_rv_cache(panel: pd.DataFrame, symbol: str, cache_dir: Path) -> Path:
    """Save RV panel to parquet cache.

    Parameters
    ----------
    panel : pd.DataFrame
        RV panel to cache.
    symbol : str
        Ticker symbol (used for filename).
    cache_dir : Path
        Directory to write cache file.

    Returns
    -------
    Path
        Path to the written parquet file.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{symbol}.parquet"
    panel.to_parquet(path)
    return path


def enrich_panel_with_ohlcv(
    panel: pd.DataFrame,
    symbol: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Merge TSDB daily open/close prices into an RV panel.

    Fetches daily OHLCV from TSDB and joins open/close columns onto
    the panel by date index. If TSDB is unavailable or the symbol has
    no RIC mapping (e.g. futures), returns the panel unchanged.

    Parameters
    ----------
    panel : pd.DataFrame
        Daily RV panel (index: date objects).
    symbol : str
        Ticker symbol.
    start_date, end_date : date
        Date range for the TSDB query.

    Returns
    -------
    pd.DataFrame
        Panel with 'open' and 'close' columns added (NaN where TSDB
        data is missing).
    """
    if panel.empty:
        return panel

    try:
        ohlcv = fetch_daily_ohlcv([symbol], start_date, end_date)
    except (ConnectionError, ValueError):
        logger.warning("%s: TSDB OHLCV unavailable -- adding NaN open/close columns", symbol)
        panel = panel.copy()
        panel["open"] = float("nan")
        panel["close"] = float("nan")
        return panel

    if ohlcv.empty:
        panel = panel.copy()
        panel["open"] = float("nan")
        panel["close"] = float("nan")
        return panel

    # Extract single-symbol slice and align to date index
    sym_data = ohlcv.xs(symbol, level="symbol")
    # Convert DatetimeIndex to date objects to match panel index
    sym_data.index = sym_data.index.date

    panel = panel.copy()
    panel["open"] = sym_data["open"].reindex(panel.index)
    panel["close"] = sym_data["close"].reindex(panel.index)
    return panel
