"""Probe Marquee + TSDB for SPX per-strike open interest and Greeks data.

Goal: Discover which GS-internal datasets provide per-strike OI and Greeks
(delta, gamma, vega, theta) for SPX options — required for GEX computation.

Approach:
1. Probe candidate Marquee dataset names via get_coverage() + get_data()
2. Probe TSDB namespace candidates for options OI
3. Probe OPRA Chunk Store with possible SPX option RIC formats
4. Check Quantum data catalog if accessible

Usage:
    ./vol shell workspace/scripts/probe_options_oi_greeks.py

Output:
    workspace/tmp/options_oi_probe_results.txt
"""

from __future__ import annotations

import sys
import traceback
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "workspace" / "tmp"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "options_oi_probe_results.txt"

results: list[str] = []


def log(msg: str) -> None:
    results.append(msg)
    print(msg)


def section(title: str) -> None:
    log(f"\n{'=' * 70}")
    log(f"  {title}")
    log(f"{'=' * 70}\n")


# ---------------------------------------------------------------------------
# 1. Marquee Dataset API — probe candidate dataset names
# ---------------------------------------------------------------------------

# These are educated guesses for internal OptionMetrics / options OI datasets.
# At GS, OptionMetrics IvyDB data may be surfaced under different dataset names.
MARQUEE_CANDIDATES = [
    # OptionMetrics / IvyDB style names
    "OPTIONMETRICS",
    "OPTIONMETRICS_IVYDB",
    "IVYDB",
    "IVYDB_US",
    "ISG_OPTIONMETRICS",
    "ISG_OPTIONS",
    "ISG_OPTION_METRICS",
    # Options open interest
    "OPTIONS_OPEN_INTEREST",
    "EQUITY_OPTIONS_OI",
    "EQUITY_OPTIONS",
    "OPTION_CHAIN",
    "OPTION_CHAIN_SPX",
    "LISTED_OPTIONS",
    "LISTED_OPTIONS_EOD",
    "OPTIONS_EOD",
    "OPTIONS_DAILY",
    # Options Greeks
    "OPTIONS_GREEKS",
    "OPTION_GREEKS",
    "OPTIONS_ANALYTICS",
    "OPTION_ANALYTICS",
    # GS-specific naming patterns (from known datasets like EDRVOL, EDRVS)
    "EDR_OPTIONS_OI",
    "EDR_OPTION_OI",
    "EDR_OPTIONS_CHAIN",
    "EDROPTIONS",
    "EQOPTIONS",
    "EQ_OPTIONS",
    "EQ_OPTION_OI",
    "EQ_OPTIONS_DAILY",
    "EQ_OPTIONS_EOD",
    # Positioning / flow (may contain OI)
    "OPTIONS_POSITIONING",
    "OPTION_FLOW",
    "OPTIONS_FLOW",
    "EQ_OPTION_FLOW",
    # CBOE-specific
    "CBOE_OPTIONS",
    "CBOE_SPX_OPTIONS",
    "CBOE_OPEN_INTEREST",
    # ISG data services
    "ISG_EQUITY_OPTIONS",
    "ISG_OPTIONS_ANALYTICS",
    "ISG_OPTIONS_DATA",
    # Quantum-catalog style
    "OPTIONS_REFERENCE_DATA",
    "OPTION_REFERENCE",
    # Bloomberg/Refinitiv style
    "OPTION_PRICES",
    "OPTION_VALUATION",
]


def probe_marquee_datasets() -> None:
    section("1. MARQUEE DATASET PROBES — Options OI + Greeks")

    try:
        from gs_quant.data import Dataset
        from gs_quant.session import GsSession

        try:
            _ = GsSession.current
        except Exception:
            GsSession.use()
        log("GsSession active ✓")
    except ImportError:
        log("ERROR: gs_quant not available. Cannot probe Marquee datasets.")
        return
    except Exception as e:
        log(f"ERROR: GsSession init failed: {e}")
        return

    # Probe each candidate
    for name in MARQUEE_CANDIDATES:
        try:
            ds = Dataset(name)
            # Try get_coverage first (cheaper, no auth needed sometimes)
            try:
                cov = ds.get_coverage()
                n_assets = len(cov) if cov is not None else 0
                cols = list(cov.columns) if cov is not None and hasattr(cov, "columns") else []
                log(f"  ✓ {name}: coverage OK ({n_assets} assets)")
                log(f"    Columns: {cols[:10]}")

                # If coverage works, try a small data query for SPX
                try:
                    data = ds.get_data(
                        start=date(2024, 6, 1),
                        end=date(2024, 6, 5),
                        bbid="SPX",
                    )
                    if data is not None and not data.empty:
                        log(f"    DATA OK: {len(data)} rows, cols={list(data.columns)[:15]}")
                    else:
                        log("    DATA: empty (try different query params)")
                except Exception as e:
                    err_str = str(e)[:100]
                    if "403" in err_str:
                        log(f"    DATA: 403 Forbidden (needs entitlement)")
                    elif "400" in err_str:
                        log(f"    DATA: 400 (needs different query params)")
                    else:
                        log(f"    DATA error: {err_str}")
            except Exception as e:
                err_str = str(e)[:80]
                if "404" in err_str or "not found" in err_str.lower():
                    pass  # Silent skip for 404
                elif "403" in err_str:
                    log(f"  ? {name}: coverage 403 (exists but needs entitlement)")
                elif "400" in err_str:
                    log(f"  ? {name}: coverage 400 (exists, needs params)")
                else:
                    log(f"  ? {name}: coverage error: {err_str}")
        except Exception as e:
            err_str = str(e)[:80]
            if "404" not in err_str and "not found" not in err_str.lower():
                log(f"  ? {name}: {err_str}")


# ---------------------------------------------------------------------------
# 2. TSDB — probe option-related namespaces
# ---------------------------------------------------------------------------

TSDB_CANDIDATES = [
    # Options OI patterns
    "eqopt_spx@oi",
    "eqopt_.spx@oi",
    "eqopt_spx@openinterest",
    "eqoption_spx@oi",
    "option_spx@oi",
    "opt_spx@oi",
    # OptionMetrics / IvyDB patterns
    "ivydb_spx@oi",
    "ivydb_.spx@oi",
    "om_spx@oi",
    "optmet_spx@oi",
    # ISG patterns
    "isg_spx@oi",
    "isg_option_spx@oi",
    # Delta/Gamma patterns
    "eqopt_spx@delta",
    "eqopt_spx@gamma",
    "eqopt_spx@gex",
    # Volume patterns
    "eqopt_spx@volume",
    "eqopt_spx@putvol",
    "eqopt_spx@callvol",
    # Put-call ratio
    "eqopt_spx@pcr",
    "eqopt_.spx@pcr",
    # Aggregate gamma
    "eqvol_spx@gex",
    "eqvol_.spx@gex",
    "eqvolrt_spx@gex",
    # Listed options
    "eqpad_.spx@oi_total",
    "eqpad_.spx@openinterest",
    "eqpad_spy.p@oi",
]


def probe_tsdb_symbols() -> None:
    section("2. TSDB SYMBOL PROBES — Options OI + Greeks")

    try:
        from gs_quant_internal.tsdb import TSDBSymbol

        log("TSDBSymbol available ✓")
    except ImportError:
        log("ERROR: gs_quant_internal.tsdb not available")
        return

    for sym in TSDB_CANDIDATES:
        try:
            data = TSDBSymbol(sym).get_data(
                start="2024-06-01", end="2024-06-05"
            )
            if data is not None:
                n = len(data) if hasattr(data, "__len__") else "?"
                log(f"  ✓ {sym}: {n} points")
                if hasattr(data, "head"):
                    log(f"    Sample: {data.head(2).to_dict()}")
            else:
                pass  # Silent skip for None
        except Exception as e:
            err_str = str(e)[:80]
            if "500" in err_str or "error" in err_str.lower():
                pass  # Expected for nonexistent symbols
            elif "403" in err_str or "forbidden" in err_str.lower():
                log(f"  ? {sym}: 403 Forbidden (exists but needs entitlement)")
            elif "empty" not in err_str.lower():
                log(f"  ? {sym}: {err_str}")


# ---------------------------------------------------------------------------
# 3. OPRA Chunk Store — try SPX option RIC formats
# ---------------------------------------------------------------------------

# Known option RIC formats (Thomson Reuters / LSEG conventions):
# Format 1: {UL}{MONTH_CODE}{STRIKE}{YEAR} e.g. "SPX G5500 4" (Jun 5500 call 2024)
# Format 2: OSI standard: {UL} {YYMMDD}{C/P}{STRIKE*1000}
#            e.g. "SPXW240605C05500000"
# Format 3: Chunk Store may use: ".SPX240605C5500" or "SPXW240605C5500"

OPRA_RIC_CANDIDATES = [
    # OSI-style (padded)
    "SPXW240605C05500000",
    "SPXW 240605C05500000",
    "SPX  240605C05500000",
    "SPX 240605C05500000",
    # Shorter variants
    "SPXW240605C5500",
    ".SPXW240605C5500",
    "SPX240605C5500",
    ".SPX240605C5500",
    # Reuters-style
    "SPX.OC",  # SPX call option root
    "SPX.OP",  # SPX put option root
    "SPXW.OC",
    "SPXW.OP",
    # Exchange-specific
    ".SPX240605C5500.CB",  # CBOE
    "SPXW240605C5500.CB",
]


def probe_opra_chunk_store() -> None:
    section("3. OPRA CHUNK STORE — SPX Option RIC Formats")

    try:
        from pytickclient import query
        import pytz
        from datetime import datetime

        TZ = pytz.timezone("America/New_York")
        log("pytickclient available ✓")
    except ImportError:
        log("ERROR: pytickclient not available (requires system Python)")
        return

    # Try to get symbol list (may hang for OPRA)
    log("  Attempting symbol list query (timeout risk)...")

    st = TZ.localize(datetime(2024, 6, 5, 9, 30, 0))
    et = TZ.localize(datetime(2024, 6, 5, 16, 0, 0))

    for ric in OPRA_RIC_CANDIDATES:
        try:
            raw = query.chunk_query(
                [ric], st, et, "OPRA",
                fields=["TRDPRC_1", "BID", "ASK", "TRDVOL_1"],
            )
            if raw and any(len(v) > 0 for v in raw.values()):
                n_rows = max(len(v) for v in raw.values())
                log(f"  ✓ {ric}: {n_rows} ticks!")
                log(f"    Fields: {list(raw.keys())}")
            # else: silent skip (0 rows = wrong RIC format)
        except Exception as e:
            err_str = str(e)[:80]
            if "timeout" in err_str.lower() or "hung" in err_str.lower():
                log(f"  ! {ric}: TIMEOUT")
                break
            # Silent skip for connection errors on invalid RICs


# ---------------------------------------------------------------------------
# 4. Quantum data catalog — check if accessible
# ---------------------------------------------------------------------------


def probe_quantum_catalog() -> None:
    section("4. QUANTUM DATA CATALOG — Options Data Discovery")

    log("  Quantum is GS's data discovery/catalog platform.")
    log("  GitLab: quantumeng/quantum-data-discovery/quantum-docs")
    log("  Web UI: https://quantum.gs.com (if accessible)")
    log("")
    log("  To search Quantum for OptionMetrics / options OI data:")
    log("  1. Clone quantum docs: skills/ENGHUB/src/clone-one.sh quantumeng/quantum-data-discovery/quantum-docs")
    log("  2. Or visit https://quantum.gs.com and search for:")
    log("     - 'OptionMetrics'")
    log("     - 'IvyDB'")
    log("     - 'options open interest SPX'")
    log("     - 'options greeks'")
    log("     - 'ISG options'")
    log("     - 'gamma exposure'")
    log("")
    log("  NOTE: ISG (Information Services Group) at GS curates third-party")
    log("  vendor data (Bloomberg, OptionMetrics, etc.) and exposes it via")
    log("  internal APIs. The Quantum catalog should show lineage and")
    log("  entitlement requirements.")


# ---------------------------------------------------------------------------
# 5. Check EDRVOL_PERCENT_EXPIRY for multi-strike data (already accessible)
# ---------------------------------------------------------------------------


def probe_edrvol_multistrike() -> None:
    section("5. EDRVOL_PERCENT_EXPIRY — Full Strike Chain (Existing Access)")

    log("  We already have access to EDRVOL_PERCENT_EXPIRY.")
    log("  This provides IV by (expiry, strike) but NOT open interest or Greeks.")
    log("  However, we CAN compute delta/gamma from IV + spot + time-to-expiry")
    log("  using Black-Scholes.")
    log("")
    log("  What EDRVOL_PERCENT_EXPIRY gives us:")
    log("    - impliedVolatility per (date, expiry, relativeStrike)")
    log("    - expirationDate")
    log("    - absoluteStrike")
    log("    - relativeStrike")
    log("")
    log("  What we CANNOT get from it:")
    log("    - Open Interest (OI) per strike ← NEED SEPARATE SOURCE")
    log("    - Volume per strike")
    log("    - Bid/ask quotes per strike")
    log("")
    log("  WORKAROUND for GEX without OI data:")
    log("    1. Use EDRVOL_PERCENT_EXPIRY IV chain → compute delta/gamma via BS")
    log("    2. ASSUME uniform or proportional OI distribution")
    log("    3. Better: use aggregate GEX from vendor (SqueezeMetrics, SpotGamma)")
    log("")
    log("  For PROPER GEX we need per-strike OI. Sources:")
    log("    a) OptionMetrics IvyDB (via ISG/Quantum) — daily EOD OI + Greeks")
    log("    b) OPRA Chunk Store (tick data) — intraday, if RIC format is resolved")
    log("    c) CBOE DataShop — external, requires separate subscription")
    log("    d) OCC cleared data — aggregated, no per-strike")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    log("=" * 70)
    log("  OPTIONS OI + GREEKS DATA SOURCE PROBE")
    log(f"  Date: {date.today().isoformat()}")
    log("  Goal: Find SPX per-strike OI + Greeks for GEX computation")
    log("=" * 70)

    probe_marquee_datasets()
    probe_tsdb_symbols()
    probe_opra_chunk_store()
    probe_quantum_catalog()
    probe_edrvol_multistrike()

    section("SUMMARY & NEXT STEPS")
    log("  1. If any Marquee dataset returned data → adapt loader immediately")
    log("  2. If datasets return 403 → file entitlement request via TMD/Marquee team")
    log("  3. If nothing found → search Quantum catalog (clone docs or web UI)")
    log("  4. If Quantum shows ISG OptionMetrics → request ISG data entitlement")
    log("  5. Fallback: compute synthetic Greeks from EDRVOL_PERCENT_EXPIRY IV chain")
    log("     (gives us delta/gamma per strike but NOT actual OI for GEX weights)")

    # Write results
    OUT_FILE.write_text("\n".join(results), encoding="utf-8")
    log(f"\n  Results saved to: {OUT_FILE}")


if __name__ == "__main__":
    main()
