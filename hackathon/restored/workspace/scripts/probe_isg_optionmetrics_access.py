"""Probe ISG OptionMetrics access with proper session initialization.

Tests:
1. TSDB ivyt_ namespace (requires equities.volprop)
2. Marquee datasets that might be unlocked by isg-marketdata-accessor
3. HIVE/PrestoDB connectivity check
4. HDFS path accessibility

Output: workspace/tmp/isg_optionmetrics_probe.txt
"""

from __future__ import annotations

import sys
import traceback
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "workspace" / "tmp"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "isg_optionmetrics_probe.txt"

results: list[str] = []


def log(msg: str) -> None:
    results.append(msg)
    print(msg)


def section(title: str) -> None:
    log(f"\n{'=' * 70}")
    log(f"  {title}")
    log(f"{'=' * 70}\n")


def main() -> None:
    log(f"ISG OptionMetrics Access Probe — {date.today().isoformat()}")
    log(f"Goal: Verify if isg-marketdata-accessor gives us SPX per-strike OI data")

    # ------------------------------------------------------------------
    # 0. Initialize GsSession
    # ------------------------------------------------------------------
    section("0. SESSION INITIALIZATION")

    try:
        from gs_quant.session import GsSession, Environment
        GsSession.use(Environment.PROD)
        log("  GsSession initialized (PROD) ✓")
    except Exception as e:
        log(f"  GsSession.use(PROD) failed: {e}")
        try:
            GsSession.use()
            log("  GsSession.use() fallback ✓")
        except Exception as e2:
            log(f"  GsSession.use() also failed: {e2}")
            log("  FATAL: Cannot initialize session. Aborting.")
            OUT_FILE.write_text("\n".join(results))
            return

    # ------------------------------------------------------------------
    # 1. TSDB ivyt_ namespace — documented example + SPX
    # ------------------------------------------------------------------
    section("1. TSDB ivyt_ NAMESPACE (requires equities.volprop UDB)")

    try:
        from gs_quant_internal.tsdb import TSDBSymbol
        log("  TSDBSymbol import ✓")

        # Documented working example from Ivy FDS page
        test_symbols = [
            ("ivyt_OXY@impliedvol.1m.50c", "OXY 1m 50d call IV (documented example)"),
            ("ivyt_SPX@impliedvol.1m.50c", "SPX 1m 50d call IV"),
            ("ivyt_SPY@impliedvol.1m.50c", "SPY 1m 50d call IV"),
            ("ivyt_AAPL@impliedvol.1m.50c", "AAPL 1m 50d call IV"),
        ]

        for sym, desc in test_symbols:
            try:
                data = TSDBSymbol(sym).get_data(start="2024-06-01", end="2024-06-05")
                if data is not None and hasattr(data, '__len__') and len(data) > 0:
                    log(f"  ✓ {sym}: {len(data)} points — {desc}")
                    if hasattr(data, 'head'):
                        log(f"    Sample: {data.head(2).to_string()}")
                    elif hasattr(data, 'iloc'):
                        log(f"    Values: {data.iloc[:3].tolist()}")
                elif data is not None:
                    log(f"  ~ {sym}: returned data object but empty — {desc}")
                else:
                    log(f"  ~ {sym}: None returned — {desc}")
            except Exception as e:
                err = str(e)[:150]
                if "403" in err or "forbidden" in err.lower() or "not authorized" in err.lower():
                    log(f"  ✗ {sym}: 403 FORBIDDEN — need equities.volprop entitlement")
                elif "404" in err or "not found" in err.lower():
                    log(f"  ✗ {sym}: 404 — symbol not found")
                else:
                    log(f"  ? {sym}: {err}")
    except ImportError:
        log("  SKIP: gs_quant_internal.tsdb not available")

    # ------------------------------------------------------------------
    # 2. Marquee Dataset API — probe ISG/OptionMetrics dataset names
    # ------------------------------------------------------------------
    section("2. MARQUEE DATASETS — ISG OptionMetrics candidates")

    try:
        from gs_quant.data import Dataset

        # These are the most likely dataset names based on Confluence research
        datasets_to_try = [
            # Direct OptionMetrics names
            ("ISG_OPTIONMETRICS", {"bbid": "SPX"}),
            ("OPTIONMETRICS", {"bbid": "SPX"}),
            ("IVYDB", {"bbid": "SPX"}),
            ("IVYDB_US", {"bbid": "SPX"}),
            # Options-specific
            ("EQUITY_OPTIONS", {"bbid": "SPX"}),
            ("OPTIONS_EOD", {"bbid": "SPX"}),
            ("LISTED_OPTIONS_EOD", {"bbid": "SPX"}),
            ("EQ_OPTIONS_DAILY", {"bbid": "SPX"}),
            ("OPTION_PRICES", {"bbid": "SPX"}),
            # ISG patterns
            ("ISG_OPTION_METRICS", {"bbid": "SPX"}),
            ("ISG_OPTIONS", {"bbid": "SPX"}),
            ("ISG_EQUITY_OPTIONS", {"bbid": "SPX"}),
            # Try ticker variants
            ("ISG_OPTIONMETRICS", {"ticker": "SPX"}),
            ("OPTIONMETRICS", {"ticker": "SPX"}),
            # Open interest specific
            ("OPTIONS_OPEN_INTEREST", {"bbid": "SPX"}),
            ("EQUITY_OPTIONS_OI", {"bbid": "SPX"}),
        ]

        for ds_name, params in datasets_to_try:
            try:
                ds = Dataset(ds_name)
                # Try get_coverage first
                try:
                    cov = ds.get_coverage()
                    if cov is not None and not cov.empty:
                        log(f"  ✓ {ds_name}: COVERAGE OK ({len(cov)} assets)")
                        log(f"    Columns: {list(cov.columns)[:10]}")
                        # Now try data
                        try:
                            data = ds.get_data(
                                start=date(2024, 6, 3),
                                end=date(2024, 6, 5),
                                **params,
                            )
                            if data is not None and not data.empty:
                                log(f"    DATA: {len(data)} rows!")
                                log(f"    Cols: {list(data.columns)[:15]}")
                                log(f"    Sample:\n{data.head(3).to_string()}")
                            else:
                                log(f"    DATA: empty for {params}")
                        except Exception as de:
                            log(f"    DATA error: {str(de)[:100]}")
                    else:
                        log(f"  ~ {ds_name}: coverage empty")
                except Exception as ce:
                    ce_str = str(ce)[:100]
                    if "404" in ce_str or "not found" in ce_str.lower():
                        pass  # Dataset doesn't exist, skip silently
                    elif "403" in ce_str:
                        log(f"  ? {ds_name}: 403 (exists but need entitlement for coverage)")
                    elif "400" in ce_str:
                        log(f"  ? {ds_name}: 400 (exists, needs different params)")
                    else:
                        log(f"  ? {ds_name}: {ce_str}")
            except Exception as e:
                err = str(e)[:80]
                if "404" not in err and "not found" not in err.lower():
                    log(f"  ? {ds_name}: {err}")

    except ImportError:
        log("  SKIP: gs_quant.data not available")

    # ------------------------------------------------------------------
    # 3. Check for PyHive / PrestoDB / HDFS clients
    # ------------------------------------------------------------------
    section("3. HIVE / PRESTO / HDFS CLIENT AVAILABILITY")

    # Check PyHive
    try:
        import pyhive
        log(f"  ✓ pyhive available (version: {getattr(pyhive, '__version__', '?')})")
    except ImportError:
        log("  ✗ pyhive not installed")

    # Check pyhive.hive
    try:
        from pyhive import hive
        log("  ✓ pyhive.hive importable")
    except ImportError:
        log("  ✗ pyhive.hive not available")

    # Check prestodb
    try:
        import prestodb
        log(f"  ✓ prestodb available")
    except ImportError:
        log("  ✗ prestodb not installed")

    # Check trino (modern presto fork)
    try:
        import trino
        log(f"  ✓ trino available")
    except ImportError:
        log("  ✗ trino not installed")

    # Check hdfs client
    try:
        import hdfs
        log(f"  ✓ hdfs client available")
    except ImportError:
        log("  ✗ hdfs client not installed")

    # Check pyarrow for HDFS
    try:
        import pyarrow.fs
        log(f"  ✓ pyarrow.fs available (can access HDFS)")
    except ImportError:
        log("  ✗ pyarrow.fs not available")

    # Check kerberos
    try:
        import kerberos
        log(f"  ✓ kerberos module available")
    except ImportError:
        log("  ✗ kerberos module not installed")

    # Check for kinit
    import subprocess
    try:
        result = subprocess.run(["which", "kinit"], capture_output=True, text=True)
        if result.returncode == 0:
            log(f"  ✓ kinit found: {result.stdout.strip()}")
        else:
            log("  ✗ kinit not on PATH")
    except Exception:
        log("  ✗ kinit check failed")

    # Check for existing Kerberos ticket
    try:
        result = subprocess.run(["klist", "-s"], capture_output=True, text=True)
        if result.returncode == 0:
            log("  ✓ Valid Kerberos ticket exists")
            # Show ticket info
            result2 = subprocess.run(["klist"], capture_output=True, text=True)
            if result2.returncode == 0:
                log(f"    {result2.stdout[:300]}")
        else:
            log("  ~ No valid Kerberos ticket (need kinit)")
    except Exception:
        log("  ✗ klist check failed")

    # ------------------------------------------------------------------
    # 4. Try HIVE connection if pyhive available
    # ------------------------------------------------------------------
    section("4. HIVE CONNECTION ATTEMPT")

    try:
        from pyhive import hive

        # Connection details from Confluence
        hive_host = "d440120-002.dc.gs.com"
        hive_port = 10000  # default HIVE port

        log(f"  Attempting HIVE connection to {hive_host}:{hive_port}...")
        log(f"  Principal: dchive/d440120-002.dc.gs.com@GS.COM")

        try:
            conn = hive.Connection(
                host=hive_host,
                port=hive_port,
                auth="KERBEROS",
                kerberos_service_name="p2epda",
                database="default",
            )
            cursor = conn.cursor()
            log("  ✓ HIVE connection established!")

            # Try to list databases/tables
            try:
                cursor.execute("SHOW DATABASES")
                dbs = cursor.fetchall()
                log(f"  Databases: {[d[0] for d in dbs[:20]]}")
            except Exception as e:
                log(f"  SHOW DATABASES error: {str(e)[:100]}")

            # Try to find option_metrics tables
            try:
                cursor.execute("SHOW TABLES IN option_metrics")
                tables = cursor.fetchall()
                log(f"  option_metrics tables: {[t[0] for t in tables[:20]]}")
            except Exception as e:
                log(f"  SHOW TABLES error: {str(e)[:100]}")

            # Try a sample query
            try:
                cursor.execute("""
                    SELECT * FROM option_metrics.option_price
                    WHERE date = '2024-06-03'
                    LIMIT 5
                """)
                rows = cursor.fetchall()
                if rows:
                    log(f"  ✓ QUERY WORKS! Got {len(rows)} rows")
                    log(f"    Columns: {[d[0] for d in cursor.description]}")
                    for row in rows[:3]:
                        log(f"    Row: {row}")
                else:
                    log("  ~ Query returned 0 rows (table may use different schema)")
            except Exception as e:
                log(f"  Query error: {str(e)[:150]}")

            conn.close()
        except Exception as e:
            err = str(e)[:200]
            if "kerberos" in err.lower() or "gss" in err.lower():
                log(f"  ✗ Kerberos auth failed: {err}")
                log("  → Need: kinit with your keytab first")
            elif "connection refused" in err.lower() or "timeout" in err.lower():
                log(f"  ✗ Connection failed (network): {err}")
                log("  → Host may not be reachable from this workspace")
            else:
                log(f"  ✗ Connection failed: {err}")
    except ImportError:
        log("  SKIP: pyhive not available — cannot attempt HIVE connection")
        log("  → Install with: pip install pyhive[hive] thrift sasl thrift-sasl")

    # ------------------------------------------------------------------
    # 5. Try HDFS access via WebHDFS
    # ------------------------------------------------------------------
    section("5. HDFS WebHDFS ACCESS CHECK")

    import urllib.request
    import json

    hdfs_base = "http://d440120-002.dc.gs.com:50070"
    hdfs_path = "/appdata/99461_qis_bigdata/data/store/option_metrics"

    url = f"{hdfs_base}/webhdfs/v1{hdfs_path}?op=LISTSTATUS"
    log(f"  Trying WebHDFS: {url}")

    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            statuses = data.get("FileStatuses", {}).get("FileStatus", [])
            log(f"  ✓ HDFS accessible! {len(statuses)} items in option_metrics/")
            for item in statuses[:15]:
                name = item.get("pathSuffix", "?")
                ftype = item.get("type", "?")
                size = item.get("length", 0)
                log(f"    {ftype}: {name} ({size:,} bytes)")
    except urllib.error.HTTPError as e:
        log(f"  ✗ HTTP {e.code}: {e.reason}")
        if e.code == 401:
            log("  → Need Kerberos/SPNEGO auth for WebHDFS")
        elif e.code == 403:
            log("  → Access denied (entitlement may not cover WebHDFS)")
    except urllib.error.URLError as e:
        log(f"  ✗ Connection failed: {e.reason}")
        log("  → Host not reachable from this workspace (firewall/network)")
    except Exception as e:
        log(f"  ✗ Error: {str(e)[:150]}")

    # Also try UAT
    hdfs_uat = "http://d400241-002.dc.gs.com:50070"
    url_uat = f"{hdfs_uat}/webhdfs/v1/appdata/99461_qis_bigdata/data/store/uat/option_metrics?op=LISTSTATUS"
    log(f"\n  Trying UAT WebHDFS: {url_uat[:80]}...")

    try:
        req = urllib.request.Request(url_uat, method="GET")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            statuses = data.get("FileStatuses", {}).get("FileStatus", [])
            log(f"  ✓ UAT HDFS accessible! {len(statuses)} items")
            for item in statuses[:10]:
                log(f"    {item.get('type','?')}: {item.get('pathSuffix','?')}")
    except Exception as e:
        err = str(e)[:100]
        log(f"  ✗ UAT HDFS: {err}")

    # ------------------------------------------------------------------
    # 6. Check if we can reach the Quantum NRT dashboard
    # ------------------------------------------------------------------
    section("6. QUANTUM NRT FLOW STATUS CHECK")

    nrt_urls = [
        ("V5", "https://prod.neartime.quantum.url.gs.com/Quantum/OPTION_METRICS_V5_DAP_FLOW/status"),
        ("V6", "https://prod.neartime.quantum.url.gs.com/Quantum/OPTION_METRICS_V6_DAP_FLOW/status"),
        ("GI", "https://prod.neartime.quantum.url.gs.com/Quantum/OPTION_METRICS_GI_DAP_FLOW/status"),
    ]

    for label, url in nrt_urls:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode()[:500]
                log(f"  ✓ {label}: accessible — {body[:100]}")
        except urllib.error.HTTPError as e:
            log(f"  ? {label}: HTTP {e.code} — {e.reason}")
        except Exception as e:
            log(f"  ✗ {label}: {str(e)[:80]}")

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    section("SUMMARY & RECOMMENDED NEXT STEPS")
    log("  Review results above to determine which path is accessible.")
    log("  If TSDB works → use ivyt_ symbols for aggregate vol data")
    log("  If HIVE works → query option_metrics.option_price for per-strike OI")
    log("  If HDFS works → read parquet files directly for bulk historical")
    log("  If nothing works from this workspace → need VPN/network access")

    OUT_FILE.write_text("\n".join(results), encoding="utf-8")
    log(f"\n  Results saved to: {OUT_FILE}")


if __name__ == "__main__":
    main()
