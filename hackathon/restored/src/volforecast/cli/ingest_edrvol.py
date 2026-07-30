"""CLI entry point for per-symbol EDRVOL implied volatility ingestion.

Fetches ATM IV (1m, 3m), 25-delta put IV, and CBOE VVIX from TSDB
for all symbols in TICKER_TO_EDRVOL_RIC. Stores per-symbol parquets
in data/raw/iv/.

Usage:
    vol ingest-edrvol
    vol ingest-edrvol --symbols SPY,AAPL
    vol ingest-edrvol --start 2013-01-02 --end 2025-01-03
    vol ingest-edrvol --force
"""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd

from volforecast.constants import TICKER_TO_EDRVOL_RIC

logger = logging.getLogger(__name__)


def _cache_covers_range(cached: pd.DataFrame, start: date, end: date) -> bool:
    """Check whether the cached data fully covers the requested date range."""
    if cached is None or cached.empty:
        return False
    cached_start = cached.index.min().date()
    cached_end = cached.index.max().date()
    return cached_start <= start and cached_end >= end


def run(
    start_date: date,
    end_date: date,
    symbols: list[str] | None = None,
    force: bool = False,
) -> int:
    """Run per-symbol EDRVOL ingestion pipeline.

    Parameters
    ----------
    start_date : date
        Start of fetch range.
    end_date : date
        End of fetch range.
    symbols : list[str], optional
        Subset of symbols to fetch. Defaults to all in TICKER_TO_EDRVOL_RIC.
    force : bool
        If True, re-fetch even if cache covers the date range.

    Returns
    -------
    int
        Exit code (0 = success).
    """
    from volforecast.cli.console import setup_logging
    from volforecast.cli.progress import StageProgress
    from volforecast.data.edrvol import (
        compute_iv_dispersion,
        fetch_edrvol,
        fetch_ovx,
        fetch_treasury_yields,
        fetch_vix_index,
        fetch_vvix,
        load_iv_cache,
        save_iv_cache,
    )

    setup_logging()

    target_symbols = symbols or sorted(TICKER_TO_EDRVOL_RIC.keys())
    total_steps = (
        len(target_symbols) + 6
    )  # +1 VVIX, +1 VIX, +1 OVX, +1 treasury, +1 dispersion, +1 GSVIVS01

    with StageProgress("ingest", "edrvol-iv", target_symbols) as sp:
        task = sp.add_task(total=total_steps, description="steps")

        # ── Per-symbol IV fetching ──
        fetched = 0
        skipped = 0
        failed: list[str] = []

        for sym in target_symbols:
            if not force:
                cached = load_iv_cache(sym)
                if _cache_covers_range(cached, start_date, end_date):
                    sp.log(f"{sym}: cached ({len(cached)} rows), skipping")
                    skipped += 1
                    sp.advance(task)
                    continue

            try:
                df = fetch_edrvol(sym, start_date, end_date)
                if df.empty:
                    sp.log(f"{sym}: no data returned")
                    failed.append(sym)
                else:
                    save_iv_cache(sym, df)
                    sp.log(f"{sym}: {len(df)} rows fetched")
                    fetched += 1
            except Exception as exc:  # noqa: BLE001
                sp.log(f"{sym}: FAILED -- {exc}")
                failed.append(sym)

            sp.advance(task)

        # ── VVIX (market-wide, fetch once) ──
        if not force:
            vvix_cached = load_iv_cache("_VVIX")
            if _cache_covers_range(vvix_cached, start_date, end_date):
                sp.log(f"VVIX: cached ({len(vvix_cached)} rows), skipping")
            else:
                vvix_cached = None
        else:
            vvix_cached = None

        if vvix_cached is None:
            try:
                vvix = fetch_vvix(start_date, end_date)
                save_iv_cache("_VVIX", vvix)
                sp.log(f"VVIX: {len(vvix)} rows fetched")
            except Exception as exc:
                sp.log(f"VVIX: FAILED -- {exc}")
                failed.append("_VVIX")

        sp.advance(task)

        # ── VIX index (market-wide, fetch once) ──
        if not force:
            vix_cached = load_iv_cache("_VIX")
            if _cache_covers_range(vix_cached, start_date, end_date):
                sp.log(f"VIX: cached ({len(vix_cached)} rows), skipping")
            else:
                vix_cached = None
        else:
            vix_cached = None

        if vix_cached is None:
            try:
                vix = fetch_vix_index(start_date, end_date)
                save_iv_cache("_VIX", vix)
                sp.log(f"VIX: {len(vix)} rows fetched")
            except Exception as exc:
                sp.log(f"VIX: FAILED -- {exc}")
                failed.append("_VIX")

        sp.advance(task)

        # ── OVX — CBOE Crude Oil Volatility Index (market-wide, fetch once) ──
        if not force:
            ovx_cached = load_iv_cache("_OVX")
            if _cache_covers_range(ovx_cached, start_date, end_date):
                sp.log(f"OVX: cached ({len(ovx_cached)} rows), skipping")
            else:
                ovx_cached = None
        else:
            ovx_cached = None

        if ovx_cached is None:
            try:
                ovx = fetch_ovx(start_date, end_date)
                save_iv_cache("_OVX", ovx)
                sp.log(f"OVX: {len(ovx)} rows fetched")
            except Exception as exc:
                sp.log(f"OVX: FAILED -- {exc}")
                failed.append("_OVX")

        sp.advance(task)

        # ── Treasury yields (market-wide, fetch once) ──
        if not force:
            tsy_cached = load_iv_cache("_TREASURY_YIELDS")
            if _cache_covers_range(tsy_cached, start_date, end_date):
                sp.log(f"Treasury yields: cached ({len(tsy_cached)} rows), skipping")
            else:
                tsy_cached = None
        else:
            tsy_cached = None

        if tsy_cached is None:
            try:
                tsy = fetch_treasury_yields(start_date, end_date)
                if not tsy.empty:
                    save_iv_cache("_TREASURY_YIELDS", tsy)
                    sp.log(f"Treasury yields: {len(tsy)} rows fetched")
                else:
                    sp.log("Treasury yields: no data returned")
                    failed.append("_TREASURY_YIELDS")
            except Exception as exc:
                sp.log(f"Treasury yields: FAILED -- {exc}")
                failed.append("_TREASURY_YIELDS")

        sp.advance(task)

        # ── IV dispersion (cross-sectional) ──
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

        # ── GSVIVS01 — Variance Swap Strategy Index ──
        from volforecast.data.edrvol import (
            load_gsvivs_cache,
            save_gsvivs_cache,
        )

        gsvivs_cached = load_gsvivs_cache()
        if not force and gsvivs_cached is not None and len(gsvivs_cached) >= 30:
            sp.log(f"GSVIVS01: cached ({len(gsvivs_cached)} rows), skipping")
        else:
            try:
                from volforecast.data.edrvol import _GSVIVS_SYMBOL, _get_tsdb_data

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

        # ── Summary ──
        summary = f"Fetched: {fetched}, Skipped: {skipped}, Failed: {len(failed)}"
        sp.log(summary)
        if failed:
            sp.log(f"Failed symbols: {', '.join(failed)}")

    return 0 if not failed else 1


def register(subparsers) -> None:
    """Register the ingest-edrvol subcommand (DEPRECATED)."""
    parser = subparsers.add_parser(
        "ingest-edrvol",
        help="Fetch per-symbol IV (ATM, skew) and VVIX from TSDB edrvol_ namespace",
    )
    parser.add_argument(
        "--start", type=str, default="2013-01-02", help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end", type=str, default=None, help="End date (YYYY-MM-DD, default: yesterday)"
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
    parser.set_defaults(func=handle)


def handle(args) -> int:
    """Execute ingest-edrvol (deprecated, delegates to ingest-iv)."""
    import warnings
    from datetime import date, timedelta

    warnings.warn(
        "vol ingest-edrvol is deprecated. Use 'vol ingest-iv' instead.",
        DeprecationWarning,
        stacklevel=1,
    )
    print("DEPRECATION: 'vol ingest-edrvol' is deprecated. Use 'vol ingest-iv' instead.")

    from volforecast.cli.ingest_iv import run as _run_iv

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end if args.end else (date.today() - timedelta(days=1)).isoformat())
    symbols = args.symbols.split(",") if args.symbols else None
    return _run_iv(start, end, symbols=symbols, force=args.force)
