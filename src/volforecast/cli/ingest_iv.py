"""Unified CLI entry point for IV ingestion.

Subsumes the old `vol ingest-edrvol` (per-symbol TSDB) and the old
SPX-only Marquee path into one command with consistent flags.

Fetches per-symbol ATM IV, 25-delta skew, and market-wide signals
(VVIX, VIX, OVX, Treasury yields, IV dispersion). Computes derived
columns (term_slope, skew_1m) before saving.

Usage:
    vol ingest-iv
    vol ingest-iv --symbols SPY,AAPL
    vol ingest-iv --start 2013-01-02 --end 2024-12-31
    vol ingest-iv --force
    vol ingest-iv --skip-market-wide
    vol ingest-iv --marquee  # Also fetch SPX deep surface from Marquee
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from volforecast.constants import TICKER_TO_EDRVOL_RIC, TICKER_TO_MARQUEE_RIC
from volforecast.data.edrvol import (
    _GSVIVS_SYMBOL,
    _get_tsdb_data,
    load_gsvivs_cache,
    save_gsvivs_cache,
)

logger = logging.getLogger(__name__)

# Default symbols: all with EDRVOL RIC mappings
_DEFAULT_SYMBOLS = sorted(TICKER_TO_EDRVOL_RIC.keys())


def _add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add term_slope and skew_1m to a per-symbol IV DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Must have columns: iv_1m_atm, iv_3m_atm, iv_1m_25dp, iv_1m_25dc.

    Returns
    -------
    pd.DataFrame
        Same DataFrame with term_slope and skew_1m added.
    """
    df = df.copy()
    if "iv_3m_atm" in df.columns and "iv_1m_atm" in df.columns:
        df["term_slope"] = df["iv_3m_atm"] - df["iv_1m_atm"]
    if "iv_1m_25dp" in df.columns and "iv_1m_25dc" in df.columns:
        df["skew_1m"] = df["iv_1m_25dp"] - df["iv_1m_25dc"]
    return df


def _cache_covers_range(cached: pd.DataFrame | None, start: date, end: date) -> bool:
    """Check whether the cached data fully covers the requested date range.

    Tolerates up to 3 calendar days gap between cached end and requested end
    to account for TSDB publication lag (T+1) and weekends.

    Also validates that required columns are present — caches missing columns
    (e.g. iv_1w_atm added after initial fetch) are treated as stale.
    """
    if cached is None or cached.empty:
        return False

    # Required columns for per-symbol IV cache
    _REQUIRED_COLUMNS = {"iv_1w_atm", "iv_1m_atm"}
    if not _REQUIRED_COLUMNS.issubset(cached.columns):
        return False

    cached_start = cached.index.min().date()
    cached_end = cached.index.max().date()
    # Allow up to 3 calendar days of slack at the end (TSDB publication lag)
    end_gap = (end - cached_end).days
    return cached_start <= start and end_gap <= 3


def _incremental_start(cached: pd.DataFrame | None, start: date) -> date:
    """Determine the start date for an incremental fetch.

    If cached data exists and covers the start, returns the day after the
    cached end (fetch only the gap). Otherwise returns the original start.
    """
    from datetime import timedelta

    if cached is None or cached.empty:
        return start
    cached_start = cached.index.min().date()
    cached_end = cached.index.max().date()
    # Only use incremental if cache covers from the requested start
    if cached_start <= start:
        return cached_end + timedelta(days=1)
    return start


def _merge_incremental(
    cached: pd.DataFrame | pd.Series | None,
    new: pd.DataFrame | pd.Series,
    fetch_start: date,
    request_start: date,
) -> pd.DataFrame | pd.Series:
    """Merge new data with cached data for incremental fetch.

    If fetch was incremental (fetch_start > request_start) and cached
    data exists, concatenates old + new and deduplicates by index.
    """
    if cached is None or (hasattr(cached, "empty") and cached.empty):
        return new
    if fetch_start <= request_start:
        return new
    # Normalize: if cached is DataFrame with one column, extract Series for Series new
    if isinstance(new, pd.Series) and isinstance(cached, pd.DataFrame):
        cached = cached.iloc[:, 0]
    elif isinstance(new, pd.DataFrame) and isinstance(cached, pd.Series):
        cached = cached.to_frame()
    combined = pd.concat([cached, new])
    combined = combined[~combined.index.duplicated(keep="last")]
    return combined.sort_index()


def run(
    start_date: date,
    end_date: date,
    symbols: list[str] | None = None,
    force: bool = False,
    skip_market_wide: bool = False,
    marquee: bool = False,
    cache_dir: Path | None = None,
) -> int:
    """Run unified IV ingestion pipeline.

    Parameters
    ----------
    start_date : date
        Start of fetch range.
    end_date : date
        End of fetch range.
    symbols : list[str], optional
        Subset of symbols. Defaults to all 25 with EDRVOL RIC.
    force : bool
        Re-fetch even if cache covers the date range.
    skip_market_wide : bool
        Skip VVIX/VIX/OVX/Treasury/dispersion fetch.
    marquee : bool
        Also fetch SPX deep surface from Marquee (requires entitlements).
    cache_dir : Path, optional
        Override cache directory (for testing).

    Returns
    -------
    int
        Exit code (0 = success, 1 = partial failure).
    """
    from volforecast.cli.console import setup_logging
    from volforecast.cli.progress import StageProgress
    from volforecast.data.edrvol import (
        compute_iv_dispersion,
        fetch_0dte_iv,
        fetch_1dte_iv,
        fetch_edrvol,
        fetch_ovx,
        fetch_treasury_yields,
        fetch_vix_index,
        fetch_vvix,
        load_iv_cache,
        save_iv_cache,
    )

    setup_logging()

    target_symbols = symbols or _DEFAULT_SYMBOLS
    # VVIX, VIX, OVX, treasury, dispersion, GSVIVS01
    market_wide_steps = 0 if skip_market_wide else 6
    total_steps = len(target_symbols) + market_wide_steps

    with StageProgress("ingest", "iv", target_symbols) as sp:
        task = sp.add_task(total=total_steps, description="steps")

        # ── Per-symbol IV ──
        fetched = 0
        skipped = 0
        failed: list[str] = []

        for sym in target_symbols:
            if not force:
                cached = load_iv_cache(sym)
                if _cache_covers_range(cached, start_date, end_date):
                    # Enrich with derived columns if missing
                    enriched = False
                    if cached is not None and "term_slope" not in cached.columns:
                        cached = _add_derived_columns(cached)
                        enriched = True
                    # Enrich with 0DTE IV if missing
                    if (
                        cached is not None
                        and "iv_0dte" not in cached.columns
                        and sym in TICKER_TO_MARQUEE_RIC
                    ):
                        try:
                            iv_0dte = fetch_0dte_iv(sym, start_date, end_date)
                            if not iv_0dte.empty:
                                cached["iv_0dte"] = iv_0dte.reindex(cached.index)
                                enriched = True
                        except Exception:  # noqa: BLE001
                            pass
                    # Enrich with 1DTE IV if missing
                    if (
                        cached is not None
                        and "iv_1dte" not in cached.columns
                        and sym in TICKER_TO_MARQUEE_RIC
                    ):
                        try:
                            iv_1dte = fetch_1dte_iv(sym, start_date, end_date)
                            if not iv_1dte.empty:
                                cached["iv_1dte"] = iv_1dte.reindex(cached.index)
                                enriched = True
                        except Exception:  # noqa: BLE001
                            pass
                    if enriched:
                        save_iv_cache(sym, cached)
                        sp.log(f"{sym}: enriched cache ({len(cached)} rows)")
                    else:
                        sp.log(f"{sym}: cached ({len(cached)} rows), skipping")
                    skipped += 1
                    sp.advance(task)
                    continue
            else:
                cached = None

            # Determine fetch range: incremental if cache covers start
            fetch_start = _incremental_start(cached, start_date)

            try:
                df = fetch_edrvol(sym, fetch_start, end_date)
                if df.empty:
                    if cached is not None and not cached.empty:
                        sp.log(f"{sym}: no new data, keeping cache ({len(cached)} rows)")
                        skipped += 1
                    else:
                        sp.log(f"{sym}: no data returned")
                        failed.append(sym)
                else:
                    df = _add_derived_columns(df)
                    # Fetch 0DTE IV if symbol has Marquee RIC
                    if sym in TICKER_TO_MARQUEE_RIC:
                        try:
                            iv_0dte = fetch_0dte_iv(sym, fetch_start, end_date)
                            if not iv_0dte.empty:
                                df["iv_0dte"] = iv_0dte.reindex(df.index)
                        except Exception:  # noqa: BLE001
                            pass  # 0DTE is best-effort; don't fail the symbol
                    # Fetch 1DTE IV if symbol has Marquee RIC
                    if sym in TICKER_TO_MARQUEE_RIC:
                        try:
                            iv_1dte = fetch_1dte_iv(sym, fetch_start, end_date)
                            if not iv_1dte.empty:
                                df["iv_1dte"] = iv_1dte.reindex(df.index)
                        except Exception:  # noqa: BLE001
                            pass  # 1DTE is best-effort; don't fail the symbol
                    # Concat with cached data if incremental
                    if cached is not None and not cached.empty and fetch_start > start_date:
                        df = pd.concat([cached, df])
                        df = df[~df.index.duplicated(keep="last")]
                        df = df.sort_index()
                    save_iv_cache(sym, df)
                    sp.log(f"{sym}: {len(df)} rows ({fetch_start} to {end_date})")
                    fetched += 1
            except Exception as exc:  # noqa: BLE001
                sp.log(f"{sym}: FAILED -- {exc}")
                failed.append(sym)

            sp.advance(task)

        # ── Market-wide signals ──
        if not skip_market_wide:
            # VVIX
            vvix_skip = False
            if not force:
                vvix_cached = load_iv_cache("_VVIX")
                if _cache_covers_range(vvix_cached, start_date, end_date):
                    sp.log(f"VVIX: cached ({len(vvix_cached)} rows), skipping")
                    vvix_skip = True
            else:
                vvix_cached = None

            if not vvix_skip:
                vvix_fetch_start = _incremental_start(vvix_cached, start_date)
                try:
                    vvix = fetch_vvix(vvix_fetch_start, end_date)
                    result = _merge_incremental(vvix_cached, vvix, vvix_fetch_start, start_date)
                    save_iv_cache("_VVIX", result)
                    sp.log(f"VVIX: {len(result)} rows")
                except Exception as exc:
                    sp.log(f"VVIX: FAILED -- {exc}")
                    failed.append("_VVIX")
            sp.advance(task)

            # VIX
            vix_skip = False
            if not force:
                vix_cached = load_iv_cache("_VIX")
                if _cache_covers_range(vix_cached, start_date, end_date):
                    sp.log(f"VIX: cached ({len(vix_cached)} rows), skipping")
                    vix_skip = True
            else:
                vix_cached = None

            if not vix_skip:
                vix_fetch_start = _incremental_start(vix_cached, start_date)
                try:
                    vix = fetch_vix_index(vix_fetch_start, end_date)
                    result = _merge_incremental(vix_cached, vix, vix_fetch_start, start_date)
                    save_iv_cache("_VIX", result)
                    sp.log(f"VIX: {len(result)} rows")
                except Exception as exc:
                    sp.log(f"VIX: FAILED -- {exc}")
                    failed.append("_VIX")
            sp.advance(task)

            # OVX
            ovx_skip = False
            if not force:
                ovx_cached = load_iv_cache("_OVX")
                if _cache_covers_range(ovx_cached, start_date, end_date):
                    sp.log(f"OVX: cached ({len(ovx_cached)} rows), skipping")
                    ovx_skip = True
            else:
                ovx_cached = None

            if not ovx_skip:
                ovx_fetch_start = _incremental_start(ovx_cached, start_date)
                try:
                    ovx = fetch_ovx(ovx_fetch_start, end_date)
                    result = _merge_incremental(ovx_cached, ovx, ovx_fetch_start, start_date)
                    save_iv_cache("_OVX", result)
                    sp.log(f"OVX: {len(result)} rows")
                except Exception as exc:
                    sp.log(f"OVX: FAILED -- {exc}")
                    failed.append("_OVX")
            sp.advance(task)

            # Treasury yields
            tsy_skip = False
            if not force:
                tsy_cached = load_iv_cache("_TREASURY_YIELDS")
                if _cache_covers_range(tsy_cached, start_date, end_date):
                    sp.log(f"Treasury yields: cached ({len(tsy_cached)} rows), skipping")
                    tsy_skip = True
            else:
                tsy_cached = None

            if not tsy_skip:
                tsy_fetch_start = _incremental_start(tsy_cached, start_date)
                try:
                    tsy = fetch_treasury_yields(tsy_fetch_start, end_date)
                    if not tsy.empty:
                        result = _merge_incremental(tsy_cached, tsy, tsy_fetch_start, start_date)
                        save_iv_cache("_TREASURY_YIELDS", result)
                        sp.log(f"Treasury yields: {len(result)} rows")
                    else:
                        sp.log("Treasury yields: no data returned")
                        failed.append("_TREASURY_YIELDS")
                except Exception as exc:
                    sp.log(f"Treasury yields: FAILED -- {exc}")
                    failed.append("_TREASURY_YIELDS")
            sp.advance(task)

            # IV dispersion (cross-sectional)
            try:
                dispersion = compute_iv_dispersion(target_symbols)
                if not dispersion.empty:
                    save_iv_cache("_MARKET", dispersion.to_frame())
                    sp.log(f"IV dispersion: {len(dispersion)} rows computed")
                else:
                    sp.log("IV dispersion: insufficient data (need >= 2 symbols)")
            except Exception as exc:
                sp.log(f"IV dispersion: FAILED -- {exc}")
            sp.advance(task)

            # GSVIVS01 — Variance Swap Strategy Index
            gsvivs_skip = False
            if not force:
                gsvivs_cached = load_gsvivs_cache()
                if gsvivs_cached is not None and len(gsvivs_cached) >= 30:
                    sp.log(f"GSVIVS01: cached ({len(gsvivs_cached)} rows), skipping")
                    gsvivs_skip = True

            if not gsvivs_skip:
                try:
                    series = _get_tsdb_data(
                        _GSVIVS_SYMBOL,
                        start_date.isoformat(),
                        end_date.isoformat(),
                    )
                    if isinstance(series, pd.DataFrame):
                        series = series.iloc[:, 0]
                    series.index = pd.DatetimeIndex(series.index)
                    series.index.name = "date"
                    series.name = "gsvivs01"
                    save_gsvivs_cache(series)
                    sp.log(f"GSVIVS01: {len(series)} rows fetched")
                except Exception as exc:
                    sp.log(f"GSVIVS01: FAILED -- {exc}")
                    failed.append("_GSVIVS01")
            sp.advance(task)

        # ── Marquee SPX surface (opt-in) ──
        if marquee:
            try:
                from volforecast.data.iv_ingest import (
                    ingest_iv_surface,
                )
                from volforecast.data.iv_ingest import (
                    save_iv_cache as _save_spx,
                )

                sp.log("Fetching SPX deep surface from Marquee...")
                spx_panel = ingest_iv_surface(start_date, end_date)
                if not spx_panel.empty:
                    _save_spx(spx_panel)
                    sp.log(f"SPX Marquee surface: {len(spx_panel)} rows")
                else:
                    sp.log("SPX Marquee surface: no data returned")
            except Exception as exc:
                sp.log(f"SPX Marquee surface: FAILED -- {exc}")
                failed.append("_SPX_SURFACE")

        # ── Summary ──
        summary = f"Fetched: {fetched}, Skipped: {skipped}, Failed: {len(failed)}"
        sp.log(summary)
        if failed:
            sp.log(f"Failed: {', '.join(failed)}")

    return 0


def register(subparsers) -> None:
    """Register the ingest-iv subcommand."""
    parser = subparsers.add_parser(
        "ingest-iv",
        help="Fetch per-symbol IV (ATM, skew) + VVIX/VIX/OVX/Treasury from TSDB",
    )
    parser.add_argument(
        "--start", type=str, default="2013-01-02", help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="End date (YYYY-MM-DD, default: yesterday)",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated symbols (default: all 25 with EDRVOL RIC)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even if cache covers the date range",
    )
    parser.add_argument(
        "--skip-market-wide",
        action="store_true",
        help="Skip VVIX/VIX/OVX/Treasury/dispersion fetch",
    )
    parser.add_argument(
        "--marquee",
        action="store_true",
        help="Also fetch SPX deep surface from Marquee (requires entitlements)",
    )
    parser.set_defaults(func=handle)


def handle(args) -> int:
    """Execute ingest-iv command. Return exit code."""
    from datetime import date, timedelta

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end if args.end else (date.today() - timedelta(days=1)).isoformat())
    symbols = args.symbols.split(",") if args.symbols else None
    return run(
        start,
        end,
        symbols=symbols,
        force=args.force,
        skip_market_wide=args.skip_market_wide,
        marquee=args.marquee,
    )
