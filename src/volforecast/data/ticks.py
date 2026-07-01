"""Per-symbol tick-derived RV panel — public data layer.

Wraps rv_panel.build_rv_panel() with a standard cache-aware API matching
the ohlcv.py pattern: fetch, save, load, cache_covers_range.

Public API:
    ingest_symbol       — Fetch + compute + save for one symbol
    save_ticks_cache    — Persist per-symbol RV DataFrame to parquet
    load_ticks_cache    — Load cached per-symbol RV (or None if missing)
    cache_covers_range  — Check if cached data covers requested date range
"""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

from volforecast.utils.paths import ticks_cache_dir, ticks_cache_path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ingest_symbol(
    symbol: str,
    start_date: date,
    end_date: date,
    *,
    mode: str = "bars",
    workers: int = 4,
    batch_size: int = 5,
    compute_workers: int | None = None,
    cache_dir: Path | None = None,
    progress=None,
    throttle_s: float = 0.0,
) -> pd.DataFrame:
    """Fetch tick data and compute daily RV panel for one symbol.

    Delegates to rv_panel.build_rv_panel() for the actual computation,
    then enriches with OHLCV open/close prices.

    Parameters
    ----------
    symbol : str
        Ticker symbol (must be in SYMBOL_UNIVERSE).
    start_date, end_date : date
        Inclusive date range.
    mode : str
        'bars' (fast, server-side aggregation, no RK) or
        'ticks' (slow, raw tick fetch, full RK + noise_gap).
    workers : int
        Parallel fetch threads per symbol.
    batch_size : int
        Trading days per API call.
    compute_workers : int, optional
        Threads for parallel compute within a batch.
    cache_dir : Path, optional
        Override cache directory (default: data/raw/ticks/).
    progress : optional
        Progress display handle.

    Returns
    -------
    pd.DataFrame
        Daily RV panel (21 columns). Index: date objects.

    Raises
    ------
    ValueError
        If symbol is not in SYMBOL_UNIVERSE.
    ConnectionError
        If ChunkStore is unavailable.
    """
    from volforecast.data.rv_panel import build_rv_panel, enrich_panel_with_ohlcv

    if cache_dir is None:
        cache_dir = ticks_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    panel = build_rv_panel(
        symbol,
        start_date,
        end_date,
        cache_dir=cache_dir,
        progress=progress,
        max_workers=workers,
        batch_size=batch_size,
        compute_workers=compute_workers,
        mode=mode,
        throttle_s=throttle_s,
    )

    # Enrich with OHLCV open/close
    panel = enrich_panel_with_ohlcv(panel, symbol, start_date, end_date)

    # Save final panel
    if not panel.empty:
        save_ticks_cache(symbol, panel, cache_dir=cache_dir)

    return panel


def save_ticks_cache(
    symbol: str,
    df: pd.DataFrame,
    *,
    cache_dir: Path | None = None,
) -> Path:
    """Persist per-symbol RV DataFrame to parquet (atomic write).

    Merges new data with any existing cache — new rows take priority
    for overlapping dates. Never discards existing history.

    Parameters
    ----------
    symbol : str
        Ticker symbol.
    df : pd.DataFrame
        Daily RV panel with date index.
    cache_dir : Path, optional
        Override directory (default: data/raw/ticks/).

    Returns
    -------
    Path
        Path to the written parquet file.
    """
    if cache_dir is None:
        path = ticks_cache_path(symbol)
    else:
        path = cache_dir / f"{symbol}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)

    # Merge with existing cache (never discard old data)
    if path.exists():
        try:
            existing = pd.read_parquet(path)
            merged = pd.concat([existing, df])
            merged = merged[~merged.index.duplicated(keep="last")]
            merged = merged.sort_index()
            df = merged
            logger.info(
                "Merged %s: %d existing + %d new -> %d total rows",
                symbol,
                len(existing),
                len(df) - len(existing) + len(df.index.intersection(existing.index)),
                len(df),
            )
        except Exception:  # noqa: BLE001
            logger.warning("Could not read existing cache for %s, writing new data only", symbol)

    # Atomic write: temp file then rename
    fd, tmp = tempfile.mkstemp(suffix=".parquet", dir=str(path.parent))
    try:
        os.close(fd)
        df.to_parquet(tmp)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

    return path


def load_ticks_cache(
    symbol: str,
    cache_dir: Path | None = None,
) -> pd.DataFrame | None:
    """Load cached per-symbol RV panel, or return None if missing.

    Parameters
    ----------
    symbol : str
        Ticker symbol.
    cache_dir : Path, optional
        Override directory (default: data/raw/ticks/).

    Returns
    -------
    pd.DataFrame or None
        RV panel if cache exists, None otherwise.
    """
    if cache_dir is None:
        path = ticks_cache_path(symbol)
    else:
        path = cache_dir / f"{symbol}.parquet"

    if not path.exists():
        return None
    return pd.read_parquet(path)


def cache_covers_range(
    symbol: str,
    start: date,
    end: date,
    *,
    cache_dir: Path | None = None,
) -> bool:
    """Check whether cached tick data covers the requested date range.

    Parameters
    ----------
    symbol : str
        Ticker symbol.
    start, end : date
        Requested date range.
    cache_dir : Path, optional
        Override directory.

    Returns
    -------
    bool
        True if cache exists and covers [start, end], False otherwise.
    """
    df = load_ticks_cache(symbol, cache_dir=cache_dir)
    if df is None or df.empty:
        return False

    idx = df.index
    if hasattr(idx, "date"):
        cached_start = idx.min().date() if hasattr(idx.min(), "date") else idx.min()
        cached_end = idx.max().date() if hasattr(idx.max(), "date") else idx.max()
    else:
        cached_start = idx.min()
        cached_end = idx.max()

    return cached_start <= start and cached_end >= end
