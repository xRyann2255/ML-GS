"""Verify ISG OptionMetrics access via isg-marketdata-accessor entitlement.

Probes:
1. TSDB ivyt_ namespace for SPX options data (IV, OI, Greeks)
2. TSDB ivyt_ for sample equity (OXY — known to work from docs)
3. Quantum API endpoints if accessible

Output: workspace/tmp/isg_access_verification.txt
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "workspace" / "tmp"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "isg_access_verification.txt"

results: list[str] = []


def log(msg: str) -> None:
    results.append(msg)
    print(msg)


def section(title: str) -> None:
    log(f"\n{'=' * 70}")
    log(f"  {title}")
    log(f"{'=' * 70}\n")


def main() -> None:
    log("ISG OptionMetrics Access Verification")
    log(f"Date: {date.today().isoformat()}")
    log(f"Entitlement: isg-marketdata-accessor")

    # -------------------------------------------------------------------
    # 1. TSDB ivyt_ namespace — probe known pattern + variations
    # -------------------------------------------------------------------
    section("1. TSDB ivyt_ NAMESPACE — SPX + Sample Equity")

    try:
        from gs_quant_internal.tsdb import TSDBSymbol
        log("  TSDBSymbol available ✓")
    except ImportError:
        log("  ERROR: gs_quant_internal.tsdb not available")
        OUT_FILE.write_text("\n".join(results))
        return

    # Known working pattern from Confluence: ivyt_OXY@impliedvol.1m.50c
    # Try variations for SPX
    tsdb_symbols = [
        # Known pattern (from Ivy FDS page)
        ("ivyt_OXY@impliedvol.1m.50c", "OXY 1m 50-delta call IV (documented example)"),
        ("ivyt_SPX@impliedvol.1m.50c", "SPX 1m 50-delta call IV"),
        ("ivyt_SPX@impliedvol.1m.50p", "SPX 1m 50-delta put IV"),
        ("ivyt_SPX@impliedvol.1m.25p", "SPX 1m 25-delta put IV"),

        # Open interest patterns
        ("ivyt_SPX@openinterest", "SPX total open interest"),
        ("ivyt_SPX@oi", "SPX OI (short form)"),
        ("ivyt_SPX@openinterest.call", "SPX call OI"),
        ("ivyt_SPX@openinterest.put", "SPX put OI"),
        ("ivyt_SPX@oi.total", "SPX total OI"),

        # Greeks patterns
        ("ivyt_SPX@gamma", "SPX gamma"),
        ("ivyt_SPX@delta", "SPX delta"),
        ("ivyt_SPX@gamma.net", "SPX net gamma"),
        ("ivyt_SPX@gamma.1m.50c", "SPX 1m 50-delta call gamma"),

        # Volume
        ("ivyt_SPX@volume", "SPX options volume"),
        ("ivyt_SPX@volume.call", "SPX call volume"),
        ("ivyt_SPX@volume.put", "SPX put volume"),
        ("ivyt_SPX@pcr", "SPX put-call ratio"),

        # SPY (might be under different root)
        ("ivyt_SPY@impliedvol.1m.50c", "SPY 1m 50-delta call IV"),
        ("ivyt_SPY@openinterest", "SPY open interest"),

        # Alternative namespace patterns
        ("ivy_SPX@impliedvol.1m.50c", "SPX (ivy_ prefix)"),
        ("eqopt_SPX@impliedvol.1m.50c", "SPX (eqopt_ prefix)"),
        ("ivydb_SPX@impliedvol.1m.50c", "SPX (ivydb_ prefix)"),

        # Full ticker variations for SPX index
        ("ivyt_.SPX@impliedvol.1m.50c", "SPX with dot prefix"),
        ("ivyt_SPXW@impliedvol.1m.50c", "SPXW weeklies"),
    ]

    working_symbols = []
    forbidden_symbols = []
    error_symbols = []

    for sym, desc in tsdb_symbols:
        try:
            data = TSDBSymbol(sym).get_data(start="2024-06-01", end="2024-06-10")
            if data is not None and (hasattr(data, '__len__') and len(data) > 0):
                n = len(data)
                working_symbols.append((sym, desc, n))
                log(f"  ✓ {sym}: {n} points — {desc}")
                # Show sample values
                if hasattr(data, 'head'):
                    sample = data.head(3)
                    log(f"    Sample: {sample.to_dict()}")
                elif hasattr(data, 'iloc'):
                    log(f"    Sample: {data.iloc[:3].tolist()}")
            else:
                pass  # Silent skip for empty/None
        except Exception as e:
            err = str(e)[:120]
            if "403" in err or "forbidden" in err.lower() or "not authorized" in err.lower():
                forbidden_symbols.append((sym, desc, err))
                log(f"  ✗ {sym}: 403 FORBIDDEN — {desc}")
            elif "500" in err:
                pass  # Expected for nonexistent symbols
            elif "empty" in err.lower() or "no data" in err.lower():
                pass
            else:
                error_symbols.append((sym, desc, err))
                log(f"  ? {sym}: {err[:80]} — {desc}")

    # -------------------------------------------------------------------
    # 2. Try Quantum PrestoDB access
    # -------------------------------------------------------------------
    section("2. QUANTUM / PRESTO ACCESS CHECK")

    log("  Quantum PrestoDB access requires JDBC/Kerberos connection.")
    log("  HDFS paths (from Confluence):")
    log("    PROD: /appdata/99461_qis_bigdata/data/store/option_metrics")
    log("    PROD: /appdata/99461_qis_bigdata/data/store/level_2/option_metrics")
    log("")
    log("  To query via PrestoDB:")
    log("    1. Need PrestoDB client + Kerberos keytab")
    log("    2. Or use HIVE: dchive/d440120-002.dc.gs.com@GS.COM")
    log("    3. Or access via Quantum API (optionMetricsQuantumApiProcessor.py)")
    log("")
    log("  GitLab repo: pwm/pwm-quantum-product-portfolio/pwm-quantum-external-data-adapter")

    # -------------------------------------------------------------------
    # 3. Try Marquee datasets that might now be accessible
    # -------------------------------------------------------------------
    section("3. MARQUEE DATASETS — Re-probe with new entitlement")

    try:
        from gs_quant.data import Dataset
        from gs_quant.session import GsSession
        try:
            _ = GsSession.current
        except Exception:
            GsSession.use()
        log("  GsSession active ✓")
    except ImportError:
        log("  ERROR: gs_quant not available")
        OUT_FILE.write_text("\n".join(results))
        return

    # Re-probe datasets that previously returned 403
    marquee_probes = [
        "EDRVS_EXPIRY",            # Variance swap by expiry (was 403)
        "EDRVOL_PERCENT_INTRADAY", # Intraday IV (was 403)
        "EQEQ_IMPLIED_CORRELATION",# Equity implied correlation (was 403)
    ]

    for ds_name in marquee_probes:
        try:
            ds = Dataset(ds_name)
            data = ds.get_data(start=date(2024, 6, 3), end=date(2024, 6, 5), bbid="SPX")
            if data is not None and not data.empty:
                log(f"  ✓ {ds_name}: {len(data)} rows!")
                log(f"    Columns: {list(data.columns)[:15]}")
                log(f"    Sample:\n{data.head(3).to_string()}")
            else:
                log(f"  ~ {ds_name}: empty result (accessible but no data for query)")
        except Exception as e:
            err = str(e)[:120]
            if "403" in err or "not authorized" in err.lower():
                log(f"  ✗ {ds_name}: STILL 403 (isg-marketdata-accessor doesn't cover this)")
            elif "404" in err:
                log(f"  ✗ {ds_name}: 404 Not Found")
            else:
                log(f"  ? {ds_name}: {err[:100]}")

    # -------------------------------------------------------------------
    # 4. Summary
    # -------------------------------------------------------------------
    section("SUMMARY")
    log(f"  Working TSDB symbols: {len(working_symbols)}")
    for sym, desc, n in working_symbols:
        log(f"    ✓ {sym} ({n} pts) — {desc}")

    log(f"\n  Forbidden (403): {len(forbidden_symbols)}")
    for sym, desc, err in forbidden_symbols[:5]:
        log(f"    ✗ {sym} — {desc}")

    log(f"\n  Other errors: {len(error_symbols)}")
    for sym, desc, err in error_symbols[:5]:
        log(f"    ? {sym}: {err[:60]}")

    if working_symbols:
        log("\n  NEXT STEPS:")
        log("  1. Explore the working ivyt_ namespace systematically")
        log("  2. Find OI + Greeks fields via tsdbsymbolinfo() or pattern probing")
        log("  3. Build ingestion pipeline for SPX per-strike data")
    else:
        log("\n  NEXT STEPS:")
        log("  1. isg-marketdata-accessor may cover HIVE/PrestoDB, not TSDB")
        log("  2. Try Quantum API directly (clone pwm-quantum-external-data-adapter)")
        log("  3. Try HIVE query for option_metrics table")
        log("  4. Check if equities.volprop UDB entitlement is also needed for ivyt_")

    OUT_FILE.write_text("\n".join(results), encoding="utf-8")
    log(f"\n  Results saved to: {OUT_FILE}")


if __name__ == "__main__":
    main()
