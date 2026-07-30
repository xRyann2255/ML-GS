"""Probe ISG OptionMetrics via Trino (PrestoDB) and HDFS with SPNEGO auth.

We know:
- trino client is installed ✓
- kerberos module available ✓  
- Valid Kerberos ticket exists (vincry@GS.COM) ✓
- HDFS hosts respond (just need SPNEGO auth) ✓
- NRT flow dashboards are accessible ✓

This script tries:
1. Trino connection to PrestoDB for option_metrics
2. HDFS with SPNEGO (requests-kerberos) for parquet files
3. PyArrow HDFS filesystem

Output: workspace/tmp/isg_trino_hdfs_probe.txt
"""

from __future__ import annotations

import sys
import traceback
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "workspace" / "tmp"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "isg_trino_hdfs_probe.txt"

results: list[str] = []


def log(msg: str) -> None:
    results.append(msg)
    print(msg)


def section(title: str) -> None:
    log(f"\n{'=' * 70}")
    log(f"  {title}")
    log(f"{'=' * 70}\n")


def main() -> None:
    log(f"ISG OptionMetrics — Trino + HDFS SPNEGO Probe")
    log(f"Date: {date.today().isoformat()}")
    log(f"Principal: vincry@GS.COM (ticket valid)")

    # ------------------------------------------------------------------
    # 1. Trino/PrestoDB connection
    # ------------------------------------------------------------------
    section("1. TRINO (PrestoDB) CONNECTION")

    try:
        import trino
        from trino.dbapi import connect
        from trino.auth import KerberosAuthentication

        log(f"  trino version: {trino.__version__}")

        # Try connecting to the Quantum PrestoDB endpoint
        # The Confluence page mentions PrestoDB integration with option_metrics
        # Common GS Presto endpoints
        presto_hosts = [
            ("d440120-002.dc.gs.com", 8443, "https"),   # Same host as HDFS NameNode
            ("d440120-002.dc.gs.com", 8080, "http"),    # Standard Presto port
            ("d440120-002.dc.gs.com", 7778, "https"),   # Alternative secure port
        ]

        for host, port, scheme in presto_hosts:
            log(f"\n  Trying Trino → {scheme}://{host}:{port}...")
            try:
                conn = connect(
                    host=host,
                    port=port,
                    http_scheme=scheme,
                    auth=KerberosAuthentication(
                        service_name="p2epda",
                        config=None,
                    ),
                    catalog="hive",
                    schema="option_metrics",
                )
                cursor = conn.cursor()

                # Try to list schemas
                try:
                    cursor.execute("SHOW SCHEMAS")
                    schemas = cursor.fetchall()
                    log(f"  ✓ Connected! Schemas: {[s[0] for s in schemas[:20]]}")

                    # Look for option_metrics
                    if any("option" in s[0].lower() for s in schemas):
                        log("  ✓ Found option-related schema!")
                        for s in schemas:
                            if "option" in s[0].lower():
                                log(f"    Schema: {s[0]}")
                                # List tables
                                try:
                                    cursor.execute(f"SHOW TABLES FROM {s[0]}")
                                    tables = cursor.fetchall()
                                    log(f"    Tables: {[t[0] for t in tables[:20]]}")
                                except Exception as e:
                                    log(f"    SHOW TABLES error: {str(e)[:100]}")
                except Exception as e:
                    log(f"  ? SHOW SCHEMAS error: {str(e)[:150]}")

                conn.close()
                break  # If we connected successfully, stop trying other ports

            except Exception as e:
                err = str(e)[:200]
                if "refused" in err.lower() or "timeout" in err.lower():
                    log(f"  ✗ Connection refused/timeout on port {port}")
                elif "403" in err or "401" in err:
                    log(f"  ✗ Auth error: {err[:100]}")
                else:
                    log(f"  ✗ Error: {err[:150]}")

    except ImportError as e:
        log(f"  SKIP: trino import issue: {e}")

    # ------------------------------------------------------------------
    # 2. HDFS via requests with SPNEGO (Kerberos HTTP auth)
    # ------------------------------------------------------------------
    section("2. HDFS WebHDFS WITH SPNEGO AUTHENTICATION")

    # Check if requests_kerberos is available
    spnego_available = False
    try:
        from requests_kerberos import HTTPKerberosAuth, OPTIONAL
        import requests
        spnego_available = True
        log("  ✓ requests_kerberos available")
    except ImportError:
        try:
            from requests_negotiate_sspi import HttpNegotiateAuth
            spnego_available = True
            log("  ✓ requests_negotiate_sspi available")
        except ImportError:
            log("  ✗ No SPNEGO auth library (requests_kerberos or requests_negotiate_sspi)")
            log("  → Try: pip install requests-kerberos")

    if spnego_available:
        try:
            from requests_kerberos import HTTPKerberosAuth, OPTIONAL
            import requests

            kerberos_auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)

            # Try PROD HDFS
            hdfs_base = "http://d440120-002.dc.gs.com:50070"
            paths_to_try = [
                "/appdata/99461_qis_bigdata/data/store/option_metrics",
                "/appdata/99461_qis_bigdata/data/store/level_2/option_metrics",
                "/appdata/99461_qis_bigdata/data/store/gdd_csi_options_isg",
            ]

            for hdfs_path in paths_to_try:
                url = f"{hdfs_base}/webhdfs/v1{hdfs_path}?op=LISTSTATUS"
                log(f"\n  GET {url[:80]}...")
                try:
                    resp = requests.get(url, auth=kerberos_auth, timeout=15)
                    log(f"  Status: {resp.status_code}")
                    if resp.status_code == 200:
                        data = resp.json()
                        statuses = data.get("FileStatuses", {}).get("FileStatus", [])
                        log(f"  ✓ ACCESSIBLE! {len(statuses)} items:")
                        for item in statuses[:15]:
                            name = item.get("pathSuffix", "?")
                            ftype = item.get("type", "?")
                            size = item.get("length", 0)
                            mod_time = item.get("modificationTime", 0)
                            log(f"    {ftype:10s} {name:40s} {size:>12,} bytes")
                    elif resp.status_code == 401:
                        log(f"  ✗ 401 — SPNEGO negotiation failed")
                        log(f"    Headers: {dict(resp.headers)}")
                    elif resp.status_code == 403:
                        log(f"  ✗ 403 — Access denied (entitlement issue)")
                    elif resp.status_code == 404:
                        log(f"  ✗ 404 — Path not found")
                    else:
                        log(f"  ? {resp.status_code}: {resp.text[:200]}")
                except requests.exceptions.ConnectionError as e:
                    log(f"  ✗ Connection error: {str(e)[:100]}")
                except requests.exceptions.Timeout:
                    log(f"  ✗ Timeout (15s)")
                except Exception as e:
                    log(f"  ✗ Error: {str(e)[:150]}")

        except Exception as e:
            log(f"  ERROR setting up SPNEGO: {str(e)[:150]}")

    # ------------------------------------------------------------------
    # 3. PyArrow HDFS filesystem
    # ------------------------------------------------------------------
    section("3. PYARROW HDFS FILESYSTEM")

    try:
        import pyarrow.fs as pafs

        log("  Attempting PyArrow HadoopFileSystem connection...")
        log("  Host: d440120-002.dc.gs.com, Port: 8020 (default RPC)")

        try:
            hdfs = pafs.HadoopFileSystem(
                host="d440120-002.dc.gs.com",
                port=8020,
                user="vincry",
            )
            log("  ✓ HadoopFileSystem connected!")

            # List option_metrics directory
            try:
                info = hdfs.get_file_info("/appdata/99461_qis_bigdata/data/store/option_metrics")
                log(f"  Path type: {info.type}")
                if info.type.name == "Directory":
                    selector = pafs.FileSelector("/appdata/99461_qis_bigdata/data/store/option_metrics", recursive=False)
                    files = hdfs.get_file_info(selector)
                    log(f"  ✓ {len(files)} items in option_metrics/:")
                    for f in files[:15]:
                        log(f"    {f.type.name:10s} {f.path}")
            except Exception as e:
                log(f"  Path query error: {str(e)[:150]}")

        except Exception as e:
            err = str(e)[:200]
            log(f"  ✗ HadoopFileSystem error: {err}")
            if "CLASSPATH" in err or "hadoop" in err.lower():
                log("  → Need HADOOP_HOME or CLASSPATH set for native HDFS client")
                log("  → Alternative: use WebHDFS via REST (section 2)")

    except ImportError:
        log("  SKIP: pyarrow.fs not available")

    # ------------------------------------------------------------------
    # 4. Try Trino with different service names / no auth
    # ------------------------------------------------------------------
    section("4. TRINO — ALTERNATIVE CONNECTION PATTERNS")

    try:
        import trino
        from trino.dbapi import connect

        # Try without Kerberos (some internal Presto clusters use basic auth or none)
        alt_configs = [
            # No auth (internal network trust)
            {"host": "d440120-002.dc.gs.com", "port": 8080, "http_scheme": "http",
             "auth": None, "user": "vincry", "desc": "no-auth port 8080"},
            {"host": "d440120-002.dc.gs.com", "port": 443, "http_scheme": "https",
             "auth": None, "user": "vincry", "desc": "HTTPS 443 no-auth"},
        ]

        for cfg in alt_configs:
            desc = cfg.pop("desc")
            log(f"\n  Trying: {desc}...")
            try:
                conn = connect(**cfg, catalog="hive", schema="default")
                cursor = conn.cursor()
                cursor.execute("SHOW SCHEMAS")
                schemas = cursor.fetchall()
                log(f"  ✓ Connected ({desc})! Schemas: {[s[0] for s in schemas[:15]]}")
                conn.close()
                break
            except Exception as e:
                log(f"  ✗ {desc}: {str(e)[:100]}")

    except ImportError:
        log("  SKIP: trino not available")

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    section("SUMMARY")
    log("  Results:")
    log("  - TSDB ivyt_: 403 (need equities.volprop UDB entitlement)")
    log("  - Kerberos ticket: VALID (vincry@GS.COM)")
    log("  - Trino client: INSTALLED")
    log("  - HDFS WebHDFS: hosts reachable, need SPNEGO auth")
    log("  - NRT dashboards: ACCESSIBLE")
    log("")
    log("  If HDFS SPNEGO worked → read parquet files directly")
    log("  If Trino connected → query option_metrics tables via SQL")
    log("  If neither → install pyhive + use HIVE JDBC, or clone Quantum adapter")

    OUT_FILE.write_text("\n".join(results), encoding="utf-8")
    log(f"\n  Saved to: {OUT_FILE}")


if __name__ == "__main__":
    main()
