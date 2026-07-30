"""Extract IVYOPVOL (Open Interest) + IVYIDXDV + IVYZEROC via WebHDFS.

Run from a GS desktop with valid Kerberos ticket (kinit vincry@FIRMWIDE.CORP.GS.COM).

This script:
1. Lists available partition files for IVYOPVOL (per-SecurityID daily OI)
2. Downloads parquet files month-by-month
3. Also downloads IVYIDXDV (dividend yields) and IVYZEROC (risk-free rates)
4. Explores IVYOPINF to find SecurityID → (strike, expiry) mapping
5. Saves everything as local parquet files

Prerequisites:
    pip install requests requests-kerberos pandas pyarrow

Usage:
    kinit vincry@FIRMWIDE.CORP.GS.COM
    python extract_webhdfs_optionmetrics.py

    # Options:
    python extract_webhdfs_optionmetrics.py --start-year 2020 --end-year 2026
    python extract_webhdfs_optionmetrics.py --tables IVYOPVOL,IVYIDXDV
    python extract_webhdfs_optionmetrics.py --explore-only  # Just discover schema
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq
import requests
from requests_kerberos import HTTPKerberosAuth, OPTIONAL


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WEBHDFS_BASE = "http://d440120-002.dc.gs.com:50070/webhdfs/v1"
HDFS_ROOT = "/appdata/99461_qis_bigdata/data/store"
L2_ROOT = f"{HDFS_ROOT}/level_2/option_metrics/ivyus_v5"
L1_ROOT = f"{HDFS_ROOT}/option_metrics/ivyus_v5"

# Tables we can read
READABLE_TABLES = {
    "IVYOPVOL": "Option Volume & Open Interest (per SecurityID, daily)",
    "IVYIDXDV": "Index Dividend Yields",
    "IVYZEROC": "Zero Coupon Rate Curve",
}

# Tables with security master info (different partition scheme)
SECURITY_MASTER_TABLES = ["IVYOPINF", "IVYSECUR", "IVYSECNM"]

# SPX SecurityIDs (we'll discover these from the data)
# From OptionMetrics docs: SPX index has secid around 108105
# Individual options have their own secids
SPX_UNDERLYING_SECIDS: list[int] = []  # Will be populated during discovery

OUTPUT_DIR = Path("optionmetrics_extract")
RATE_LIMIT_SECONDS = 0.3  # Be gentle with WebHDFS


# ---------------------------------------------------------------------------
# WebHDFS Client
# ---------------------------------------------------------------------------

class WebHDFSClient:
    """Simple WebHDFS client with Kerberos SPNEGO auth."""

    def __init__(self, base_url: str = WEBHDFS_BASE):
        self.base_url = base_url
        self.auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)
        self.session = requests.Session()
        self.session.auth = self.auth

    def list_dir(self, path: str) -> list[dict[str, Any]]:
        """List directory contents. Returns FileStatus entries."""
        url = f"{self.base_url}{path}?op=LISTSTATUS"
        resp = self.session.get(url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("FileStatuses", {}).get("FileStatus", [])
        elif resp.status_code == 403:
            return []  # Access denied
        elif resp.status_code == 404:
            return []  # Not found
        else:
            print(f"  WARNING: {resp.status_code} for {path}")
            return []

    def read_file(self, path: str) -> bytes | None:
        """Read file contents via WebHDFS OPEN operation."""
        url = f"{self.base_url}{path}?op=OPEN"
        resp = self.session.get(url, timeout=60, allow_redirects=True)
        if resp.status_code == 200:
            return resp.content
        else:
            print(f"  WARNING: {resp.status_code} reading {path}")
            return None

    def read_parquet(self, path: str) -> pd.DataFrame | None:
        """Read a parquet file from HDFS and return as DataFrame."""
        content = self.read_file(path)
        if content is None:
            return None
        try:
            table = pq.read_table(io.BytesIO(content))
            return table.to_pandas()
        except Exception as e:
            print(f"  ERROR parsing parquet {path}: {e}")
            return None


# ---------------------------------------------------------------------------
# Discovery Functions
# ---------------------------------------------------------------------------

def discover_partition_scheme(client: WebHDFSClient, table_path: str, table_name: str) -> str:
    """Discover how a table is partitioned (year=/month= vs flat vs other)."""
    entries = client.list_dir(table_path)
    if not entries:
        return "ACCESS_DENIED"

    names = [e["pathSuffix"] for e in entries]

    # Check for year= partition
    if any(n.startswith("year=") for n in names):
        years = [n for n in names if n.startswith("year=")]
        return f"year_month ({len(years)} years: {years[0]}...{years[-1]})"

    # Check for date-like partitions
    if any(n.startswith("20") or n.startswith("19") for n in names):
        return f"date_folders ({len(names)} entries)"

    # Flat files
    if any(n.endswith(".parquet") or n.endswith(".snappy.parquet") for n in names):
        return f"flat_files ({len(names)} files)"

    return f"unknown ({names[:5]})"


def explore_table_schemas(client: WebHDFSClient) -> None:
    """Explore all tables and their partition schemes."""
    print("\n" + "=" * 70)
    print("  TABLE SCHEMA DISCOVERY")
    print("=" * 70)

    # L2 tables
    print(f"\n--- Level 2 ({L2_ROOT}) ---")
    entries = client.list_dir(L2_ROOT)
    for entry in entries:
        name = entry["pathSuffix"]
        path = f"{L2_ROOT}/{name}"
        scheme = discover_partition_scheme(client, path, name)
        status = "✓" if scheme != "ACCESS_DENIED" else "✗"
        print(f"  {status} {name:20s} → {scheme}")

    # Explore security master tables specifically
    print(f"\n--- Security Master Tables (need for SecurityID mapping) ---")
    for table in SECURITY_MASTER_TABLES:
        path = f"{L2_ROOT}/{table}"
        entries = client.list_dir(path)
        if entries:
            print(f"\n  {table}/:")
            for e in entries[:10]:
                sub_name = e["pathSuffix"]
                sub_path = f"{path}/{sub_name}"
                print(f"    {sub_name}/")
                # Go one level deeper
                sub_entries = client.list_dir(sub_path)
                for se in sub_entries[:5]:
                    print(f"      {se['pathSuffix']} ({se.get('length', 0):,} bytes)")
                time.sleep(RATE_LIMIT_SECONDS)
        else:
            print(f"  {table}: ACCESS DENIED or NOT FOUND")
        time.sleep(RATE_LIMIT_SECONDS)


# ---------------------------------------------------------------------------
# Extraction Functions
# ---------------------------------------------------------------------------

def extract_table_month(
    client: WebHDFSClient,
    table_name: str,
    year: int,
    month: int,
) -> pd.DataFrame | None:
    """Extract one month of data from a year=/month= partitioned table."""
    path = f"{L2_ROOT}/{table_name}/year={year}/month={month:02d}"
    entries = client.list_dir(path)

    if not entries:
        return None

    # Find parquet files
    parquet_files = [
        e for e in entries
        if e["pathSuffix"].endswith(".parquet") and not e["pathSuffix"].startswith("_")
    ]

    if not parquet_files:
        return None

    chunks = []
    for pf in parquet_files:
        file_path = f"{path}/{pf['pathSuffix']}"
        df = client.read_parquet(file_path)
        if df is not None and not df.empty:
            chunks.append(df)
        time.sleep(RATE_LIMIT_SECONDS)

    if chunks:
        result = pd.concat(chunks, ignore_index=True)
        return result
    return None


def extract_table(
    client: WebHDFSClient,
    table_name: str,
    start_year: int,
    end_year: int,
    output_dir: Path,
) -> Path | None:
    """Extract full table across year range, save as single parquet."""
    print(f"\n{'=' * 70}")
    print(f"  EXTRACTING: {table_name}")
    print(f"  Range: {start_year} to {end_year}")
    print(f"{'=' * 70}")

    all_chunks = []
    total_rows = 0

    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            # Skip future months
            if year == date.today().year and month > date.today().month:
                break

            df = extract_table_month(client, table_name, year, month)
            if df is not None:
                all_chunks.append(df)
                total_rows += len(df)
                print(f"  {year}-{month:02d}: {len(df):>10,} rows (total: {total_rows:,})")
            else:
                # Check if it's access denied vs not exists
                pass  # Silent skip

    if not all_chunks:
        print(f"  ERROR: No data extracted for {table_name}")
        return None

    result = pd.concat(all_chunks, ignore_index=True)
    out_path = output_dir / f"{table_name.lower()}_{start_year}_{end_year}.parquet"
    result.to_parquet(out_path, index=False)
    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"\n  ✓ Saved: {out_path} ({len(result):,} rows, {size_mb:.1f} MB)")
    return out_path


# ---------------------------------------------------------------------------
# SecurityID Discovery
# ---------------------------------------------------------------------------

def discover_spx_securityids(
    client: WebHDFSClient,
    opvol_sample: pd.DataFrame,
) -> None:
    """Try to identify which SecurityIDs belong to SPX options.

    Strategy: The IVYIDXDV table has index-level SecurityIDs with dividend rates.
    Cross-reference with OptionMetrics docs where SPX = secid 108105.
    """
    print("\n--- SecurityID Discovery ---")

    # Check IVYIDXDV for index-level IDs
    idxdv_path = f"{L2_ROOT}/IVYIDXDV/year=2024/month=01"
    entries = client.list_dir(idxdv_path)
    if entries:
        pf = next((e for e in entries if e["pathSuffix"].endswith(".parquet")), None)
        if pf:
            df = client.read_parquet(f"{idxdv_path}/{pf['pathSuffix']}")
            if df is not None:
                unique_ids = sorted(df["SecurityID"].unique())
                print(f"  Index SecurityIDs (from IVYIDXDV): {unique_ids[:20]}")
                print(f"  (These are underlying index IDs, not option contract IDs)")

    # In IVYOPVOL, show the distribution of SecurityIDs
    if opvol_sample is not None and "SecurityID" in opvol_sample.columns:
        unique_opvol = opvol_sample["SecurityID"].nunique()
        print(f"  Unique SecurityIDs in IVYOPVOL sample: {unique_opvol:,}")
        # Show top-OI contracts
        if "OpenInterest" in opvol_sample.columns:
            top_oi = (
                opvol_sample.groupby("SecurityID")["OpenInterest"]
                .sum()
                .sort_values(ascending=False)
                .head(20)
            )
            print(f"  Top 20 SecurityIDs by total OI:")
            for sid, oi in top_oi.items():
                print(f"    SecurityID={sid:>10d}  OI={oi:>12,}")


# ---------------------------------------------------------------------------
# IVYOPINF Exploration (security master)
# ---------------------------------------------------------------------------

def explore_ivyopinf(client: WebHDFSClient) -> pd.DataFrame | None:
    """Explore IVYOPINF table to find the SecurityID → option mapping.

    IVYOPINF likely has: SecurityID, UnderlyingSecurityID, Strike, Expiration, CallPut
    But it uses a different partition scheme than year=/month=.
    """
    print("\n--- Exploring IVYOPINF (Option Info / Security Master) ---")

    # Try L2 path
    for root in [L2_ROOT, L1_ROOT]:
        path = f"{root}/IVYOPINF"
        entries = client.list_dir(path)
        if entries:
            print(f"  Found at: {path}")
            print(f"  Top-level entries ({len(entries)}):")
            for e in entries[:10]:
                suffix = e["pathSuffix"]
                etype = e["type"]
                print(f"    {etype:10s} {suffix}")

                # If it's a directory, go deeper
                if etype == "DIRECTORY":
                    sub_entries = client.list_dir(f"{path}/{suffix}")
                    for se in sub_entries[:5]:
                        print(f"      {se['type']:10s} {se['pathSuffix']} ({se.get('length', 0):,} bytes)")
                        # Try to read if it's a parquet
                        if se["pathSuffix"].endswith(".parquet") and se.get("length", 0) > 0:
                            df = client.read_parquet(f"{path}/{suffix}/{se['pathSuffix']}")
                            if df is not None:
                                print(f"      ✓ Schema: {list(df.columns)}")
                                print(f"      ✓ Rows: {len(df)}")
                                print(f"      ✓ Sample:\n{df.head(3).to_string()}")
                                return df
                    time.sleep(RATE_LIMIT_SECONDS)
            break

    # Also try v6/v7 paths which might have different structure
    for version in ["ivyus_v6", "ivyus_v7"]:
        path = f"{HDFS_ROOT}/level_2/option_metrics/{version}/IVYOPINF"
        entries = client.list_dir(path)
        if entries:
            print(f"\n  Also found at: {path}")
            for e in entries[:5]:
                print(f"    {e['type']:10s} {e['pathSuffix']}")

    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Extract OptionMetrics data via WebHDFS")
    parser.add_argument("--start-year", type=int, default=2015, help="Start year (default: 2015)")
    parser.add_argument("--end-year", type=int, default=2026, help="End year (default: 2026)")
    parser.add_argument("--tables", type=str, default="IVYOPVOL,IVYIDXDV,IVYZEROC",
                        help="Comma-separated tables to extract")
    parser.add_argument("--explore-only", action="store_true",
                        help="Only explore schema, don't extract")
    parser.add_argument("--output-dir", type=str, default="optionmetrics_extract",
                        help="Output directory")
    parser.add_argument("--sample-only", action="store_true",
                        help="Only extract 1 month sample per table")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  ISG OptionMetrics — WebHDFS Extraction")
    print(f"  Date: {date.today().isoformat()}")
    print(f"  Output: {output_dir.resolve()}")
    print(f"  Mode: {'explore' if args.explore_only else 'extract'}")
    print("=" * 70)

    # Initialize client
    client = WebHDFSClient()

    # Test connectivity
    print("\nTesting WebHDFS connectivity...")
    test_entries = client.list_dir(f"{HDFS_ROOT}/option_metrics")
    if not test_entries:
        print("ERROR: Cannot list HDFS root. Check Kerberos ticket (kinit)")
        sys.exit(1)
    print(f"  ✓ Connected! ({len(test_entries)} entries in option_metrics/)")

    # Phase 1: Explore
    if args.explore_only:
        explore_table_schemas(client)
        explore_ivyopinf(client)
        return

    # Phase 2: Explore IVYOPINF for security master
    print("\n--- Phase 1: Security Master Discovery ---")
    opinfo_df = explore_ivyopinf(client)
    if opinfo_df is not None:
        opinfo_path = output_dir / "ivyopinf_sample.parquet"
        opinfo_df.to_parquet(opinfo_path, index=False)
        print(f"  Saved security master sample: {opinfo_path}")

    # Phase 3: Extract readable tables
    print("\n--- Phase 2: Data Extraction ---")
    tables = [t.strip() for t in args.tables.split(",")]

    for table_name in tables:
        if table_name not in READABLE_TABLES:
            print(f"  SKIP: {table_name} (not in readable set)")
            continue

        if args.sample_only:
            # Just get one month
            sample_year = 2024
            sample_month = 6
            print(f"\n  Sampling {table_name} ({sample_year}-{sample_month:02d})...")
            df = extract_table_month(client, table_name, sample_year, sample_month)
            if df is not None:
                out_path = output_dir / f"{table_name.lower()}_sample_{sample_year}_{sample_month:02d}.parquet"
                df.to_parquet(out_path, index=False)
                print(f"  ✓ Saved: {out_path} ({len(df):,} rows)")
                print(f"  Columns: {list(df.columns)}")
                print(f"  Sample:\n{df.head(5).to_string()}")

                # SecurityID discovery
                if table_name == "IVYOPVOL":
                    discover_spx_securityids(client, df)
            else:
                print(f"  ✗ No data for {table_name} {sample_year}-{sample_month:02d}")
        else:
            extract_table(client, table_name, args.start_year, args.end_year, output_dir)

    print("\n" + "=" * 70)
    print("  EXTRACTION COMPLETE")
    print(f"  Output: {output_dir.resolve()}")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Copy parquets to Coder workspace:")
    print(f"     scp -r {output_dir}/ vincry@<coder>:/home/vincry/ceph-storage/ml-vol-estimator/data/raw/options_oi/")
    print("  2. If IVYOPINF was readable, you have the SecurityID→strike mapping")
    print("  3. If not, filter IVYOPVOL by SecurityIDs that match SPX options")
    print("     (from OptionMetrics docs, SPX underlying secid = 108105)")


if __name__ == "__main__":
    main()
