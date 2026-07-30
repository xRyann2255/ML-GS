"""Discover full EDRVOL universe coverage from Marquee + TSDB.

Queries:
1. EDRVOL_PERCENT → get_coverage() → all bbids with IV data
2. EDRVOL_PERCENT_STOCK_STANDARD → curated single-stock subset (49 assets)
3. EDRVOL_PERCENT_SINGLESTOCK_HISTORY → historical single-stock (591 assets)
4. EDRVOL_PERCENT_INDEX_US → US index subset (44 assets)
5. EDRVS_SINGLESTOCK → var swap strikes for single stocks
6. TSDB edrvol_ namespace probe → which RICs respond to 1matms query

Outputs results to workspace/tmp/edrvol_universe_discovery.json

Usage:
    ./vol shell workspace/scripts/discover_edrvol_universe.py
    (Must run on GS desktop with active Marquee session)
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("workspace/tmp")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "edrvol_universe_discovery.json"


def _init_session():
    """Initialize GsSession."""
    from gs_quant.session import GsSession

    try:
        _ = GsSession.current
        logger.info("GsSession already active")
    except Exception:
        GsSession.use()
        logger.info("GsSession initialized")


def _query_dataset_coverage(dataset_id: str) -> list[dict]:
    """Query get_coverage() for a Marquee dataset. Returns list of coverage entries."""
    from gs_quant.data import Dataset

    logger.info(f"Querying coverage for {dataset_id}...")
    try:
        ds = Dataset(dataset_id)
        coverage = ds.get_coverage()
        if isinstance(coverage, pd.DataFrame):
            records = coverage.to_dict("records")
        elif isinstance(coverage, list):
            records = coverage
        else:
            records = []
        logger.info(f"  → {len(records)} entries")
        return records
    except Exception as exc:
        logger.error(f"  → FAILED: {exc}")
        return []


def _extract_symbols_from_coverage(records: list[dict]) -> list[dict]:
    """Extract unique symbols with metadata from coverage records."""
    symbols = {}
    for rec in records:
        # Try multiple key patterns (Marquee is inconsistent)
        bbid = rec.get("bbid") or rec.get("ticker") or rec.get("name") or ""
        asset_id = rec.get("assetId", "")
        name = rec.get("name", "")

        # Skip NaN/None/empty
        if not bbid or (isinstance(bbid, float) and pd.isna(bbid)):
            continue
        bbid = str(bbid)

        if bbid not in symbols:
            symbols[bbid] = {
                "bbid": bbid,
                "assetId": str(asset_id) if asset_id else "",
                "name": str(name) if name else "",
            }
    return sorted(symbols.values(), key=lambda x: x["bbid"])


def _probe_tsdb_edrvol(rics: list[str], field: str = "1matms") -> dict[str, bool]:
    """Probe TSDB edrvol_ namespace for each RIC. Returns {ric: has_data}."""
    try:
        from gs_quant_internal.tsdb import TSDBSymbol
    except ImportError:
        logger.warning("gs_quant_internal not available — skipping TSDB probe")
        return {}

    end = date.today()
    start = end - timedelta(days=30)
    results = {}

    for i, ric in enumerate(rics):
        sym = f"edrvol_{ric}@{field}"
        try:
            data = TSDBSymbol(sym).get_data(start=start.isoformat(), end=end.isoformat())
            has_data = data is not None and len(data) > 0
            results[ric] = has_data
            if has_data:
                logger.info(f"  [{i+1}/{len(rics)}] {sym} → {len(data)} rows")
            else:
                logger.debug(f"  [{i+1}/{len(rics)}] {sym} → empty")
        except Exception as exc:
            results[ric] = False
            logger.debug(f"  [{i+1}/{len(rics)}] {sym} → ERROR: {exc}")

        # Rate limit
        if (i + 1) % 50 == 0:
            time.sleep(1.0)

    return results


def _get_sp500_constituents() -> list[str]:
    """Get S&P 500 constituent tickers for cross-referencing.

    Falls back to a hardcoded top-150 by weight if data unavailable.
    """
    # Top 150 S&P 500 by market cap (as of mid-2026, approximate)
    return [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B",
        "AVGO", "JPM", "LLY", "V", "UNH", "MA", "COST", "HD", "PG", "JNJ",
        "NFLX", "ABBV", "CRM", "BAC", "ORCL", "WMT", "MRK", "AMD", "CVX",
        "XOM", "KO", "PEP", "ACN", "LIN", "ADBE", "TMO", "MCD", "CSCO",
        "ABT", "WFC", "DHR", "ISRG", "PM", "MS", "GE", "NOW", "DIS",
        "TXN", "IBM", "CAT", "VZ", "INTU", "AMGN", "NEE", "QCOM", "AMAT",
        "PFE", "GS", "BKNG", "RTX", "HON", "SPGI", "T", "UNP", "BLK",
        "UBER", "SYK", "LOW", "AXP", "CMCSA", "COP", "TJX", "PANW",
        "ELV", "SBUX", "LRCX", "BA", "PLD", "DE", "MDLZ", "ADI",
        "VRTX", "GILD", "ADP", "MMC", "BMY", "NKE", "KLAC", "FI",
        "REGN", "C", "SCHW", "MU", "INTC", "CI", "SO", "SHW", "ICE",
        "CME", "EQIX", "SNPS", "CDNS", "PGR", "ZTS", "MCO", "MO",
        "APD", "USB", "DUK", "WM", "CL", "TT", "MSI", "ETN", "BDX",
        "TGT", "EMR", "PNC", "NOC", "PYPL", "FDX", "AZO", "CTAS",
        "GD", "APH", "HCA", "ORLY", "SLB", "WELL", "AON", "ITW",
        "TDG", "CMG", "CARR", "ROP", "MCK", "MCHP", "ADSK", "AJG",
        "PCAR", "PSA", "NSC", "OXY", "MRNA", "MPC", "ECL", "MNST",
        "NXPI", "KDP", "AEP", "DXCM", "ROST", "FTNT", "F", "GM",
        "ABNB", "DASH", "CRWD", "SNOW", "COIN", "PLTR", "ARM", "SMCI",
    ]


def main():
    """Main discovery flow."""
    _init_session()

    results = {
        "generated_at": date.today().isoformat(),
        "datasets": {},
    }

    # 1. EDRVOL_PERCENT (main dataset — 5,935 assets)
    edrvol_cov = _query_dataset_coverage("EDRVOL_PERCENT")
    if edrvol_cov:
        logger.info(f"  Raw record keys: {list(edrvol_cov[0].keys())}")
        logger.info(f"  Sample record: {edrvol_cov[0]}")
    edrvol_symbols = _extract_symbols_from_coverage(edrvol_cov)
    results["datasets"]["EDRVOL_PERCENT"] = {
        "total_assets": len(edrvol_cov),
        "unique_symbols": len(edrvol_symbols),
        "symbols": edrvol_symbols,
        "raw_sample": edrvol_cov[:5] if edrvol_cov else [],
    }

    # 2. EDRVOL_PERCENT_STOCK_STANDARD (curated single stocks — 49)
    stock_std_cov = _query_dataset_coverage("EDRVOL_PERCENT_STOCK_STANDARD")
    stock_std_symbols = _extract_symbols_from_coverage(stock_std_cov)
    results["datasets"]["EDRVOL_PERCENT_STOCK_STANDARD"] = {
        "total_assets": len(stock_std_cov),
        "unique_symbols": len(stock_std_symbols),
        "symbols": stock_std_symbols,
    }

    # 3. EDRVOL_PERCENT_SINGLESTOCK_HISTORY (591 stocks)
    ss_hist_cov = _query_dataset_coverage("EDRVOL_PERCENT_SINGLESTOCK_HISTORY")
    ss_hist_symbols = _extract_symbols_from_coverage(ss_hist_cov)
    results["datasets"]["EDRVOL_PERCENT_SINGLESTOCK_HISTORY"] = {
        "total_assets": len(ss_hist_cov),
        "unique_symbols": len(ss_hist_symbols),
        "symbols": ss_hist_symbols,
    }

    # 4. EDRVOL_PERCENT_INDEX_US (44 US indices)
    idx_us_cov = _query_dataset_coverage("EDRVOL_PERCENT_INDEX_US")
    idx_us_symbols = _extract_symbols_from_coverage(idx_us_cov)
    results["datasets"]["EDRVOL_PERCENT_INDEX_US"] = {
        "total_assets": len(idx_us_cov),
        "unique_symbols": len(idx_us_symbols),
        "symbols": idx_us_symbols,
    }

    # 5. EDRVS_SINGLESTOCK (var swap on single stocks)
    edrvs_cov = _query_dataset_coverage("EDRVS_SINGLESTOCK")
    edrvs_symbols = _extract_symbols_from_coverage(edrvs_cov)
    results["datasets"]["EDRVS_SINGLESTOCK"] = {
        "total_assets": len(edrvs_cov),
        "unique_symbols": len(edrvs_symbols),
        "symbols": edrvs_symbols,
    }

    # 6. EDRVOL_PERCENT_FORWARD_US (forward vol surface)
    fwd_cov = _query_dataset_coverage("EDRVOL_PERCENT_FORWARD_US")
    fwd_symbols = _extract_symbols_from_coverage(fwd_cov)
    results["datasets"]["EDRVOL_PERCENT_FORWARD_US"] = {
        "total_assets": len(fwd_cov),
        "unique_symbols": len(fwd_symbols),
        "symbols": fwd_symbols,
    }

    # 7. Cross-reference with S&P 500
    sp500 = _get_sp500_constituents()
    edrvol_bbids = {s["bbid"] for s in edrvol_symbols}
    ss_hist_bbids = {s["bbid"] for s in ss_hist_symbols}
    stock_std_bbids = {s["bbid"] for s in stock_std_symbols}

    sp500_in_edrvol = sorted(t for t in sp500 if t in edrvol_bbids)
    sp500_not_in_edrvol = sorted(t for t in sp500 if t not in edrvol_bbids)

    results["cross_reference"] = {
        "sp500_sample_size": len(sp500),
        "sp500_in_edrvol_percent": len(sp500_in_edrvol),
        "sp500_in_edrvol_percent_list": sp500_in_edrvol,
        "sp500_not_in_edrvol_percent": len(sp500_not_in_edrvol),
        "sp500_not_in_edrvol_percent_list": sp500_not_in_edrvol,
        "sp500_in_singlestock_history": len([t for t in sp500 if t in ss_hist_bbids]),
        "sp500_in_stock_standard": len([t for t in sp500 if t in stock_std_bbids]),
    }

    # 8. TSDB edrvol_ probe for top symbols (if gs_quant_internal available)
    # Generate RIC candidates for S&P 500 names
    # Common patterns: ticker.oq (NASDAQ), ticker.n (NYSE), ticker.p (Arca)
    nasdaq_tickers = {"AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",
                      "AVGO", "COST", "NFLX", "ADBE", "AMD", "INTC", "QCOM",
                      "INTU", "CSCO", "AMGN", "GILD", "ISRG", "REGN", "VRTX",
                      "BKNG", "PANW", "LRCX", "KLAC", "SNPS", "CDNS", "AMAT",
                      "MU", "MCHP", "NXPI", "DXCM", "CRWD", "FTNT", "ABNB",
                      "DASH", "SNOW", "COIN", "PLTR", "ARM", "SMCI", "ORCL",
                      "PEP", "MNST", "MRNA", "PYPL"}
    arca_tickers = {"SPY", "QQQ", "IWM", "DIA", "HYG", "GLD", "EEM", "XLF",
                    "TLT", "USO"}

    probe_rics = []
    for t in sp500[:80]:  # Top 80 by cap
        if t in nasdaq_tickers:
            probe_rics.append(f"{t.lower()}.oq")
        elif t in arca_tickers:
            probe_rics.append(f"{t.lower()}.p")
        elif "." in t:
            # BRK.B -> brk-b.n (special case)
            probe_rics.append(f"{t.lower().replace('.', '-')}.n")
        else:
            probe_rics.append(f"{t.lower()}.n")

    logger.info(f"Probing TSDB edrvol_ for {len(probe_rics)} RICs...")
    tsdb_results = _probe_tsdb_edrvol(probe_rics)
    tsdb_working = sorted(r for r, ok in tsdb_results.items() if ok)
    tsdb_failed = sorted(r for r, ok in tsdb_results.items() if not ok)

    results["tsdb_edrvol_probe"] = {
        "probed": len(probe_rics),
        "working": len(tsdb_working),
        "failed": len(tsdb_failed),
        "working_rics": tsdb_working,
        "failed_rics": tsdb_failed,
    }

    # 9. Summary statistics
    results["summary"] = {
        "edrvol_percent_total_assets": len(edrvol_cov),
        "edrvol_percent_unique_bbids": len(edrvol_symbols),
        "singlestock_history_count": len(ss_hist_symbols),
        "stock_standard_count": len(stock_std_symbols),
        "index_us_count": len(idx_us_symbols),
        "varswap_singlestock_count": len(edrvs_symbols),
        "forward_vol_count": len(fwd_symbols),
        "sp500_coverage_pct": round(100 * len(sp500_in_edrvol) / len(sp500), 1),
        "tsdb_edrvol_working_count": len(tsdb_working),
    }

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"\nResults written to {OUTPUT_FILE}")
    logger.info(f"\n{'='*60}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"EDRVOL_PERCENT total assets:       {len(edrvol_cov)}")
    logger.info(f"EDRVOL_PERCENT unique bbids:       {len(edrvol_symbols)}")
    logger.info(f"Singlestock History:               {len(ss_hist_symbols)}")
    logger.info(f"Stock Standard (curated):          {len(stock_std_symbols)}")
    logger.info(f"Index US:                          {len(idx_us_symbols)}")
    logger.info(f"Var Swap Single Stock:             {len(edrvs_symbols)}")
    logger.info(f"Forward Vol US:                    {len(fwd_symbols)}")
    logger.info(f"S&P 500 top-{len(sp500)} in EDRVOL:   {len(sp500_in_edrvol)} ({results['summary']['sp500_coverage_pct']}%)")
    logger.info(f"TSDB edrvol_ working:              {len(tsdb_working)}/{len(probe_rics)}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()
