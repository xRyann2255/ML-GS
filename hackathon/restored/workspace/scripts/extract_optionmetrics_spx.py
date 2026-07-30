"""ISG OptionMetrics data extraction for GEX computation.

Run this on a GS-hosted machine (desktop/jump host) that can reach:
  - d440120-002.dc.gs.com:10000 (HiveServer2)
  - d440120-002.dc.gs.com:9083  (Hive Metastore)

Prerequisites:
  pip install pyhive[hive] thrift sasl thrift-sasl pandas pyarrow

Your entitlement: isg-marketdata-accessor (permitResource)
HIVE principal: dchive/d440120-002.dc.gs.com@GS.COM

Usage:
  # 1. Get a Kerberos ticket first:
  kinit vincry@GS.COM

  # 2. Run this script:
  python extract_optionmetrics_spx.py

  # 3. Copy the output parquet to your Coder workspace:
  scp spx_option_chain_*.parquet vincry@<coder-host>:/home/vincry/ceph-storage/ml-vol-estimator/data/raw/options_oi/

Output: spx_option_chain_{start}_{end}.parquet
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HIVE_HOST = "d440120-002.dc.gs.com"
HIVE_PORT = 10000
KERBEROS_SERVICE_NAME = "p2epda"  # From Confluence entitlement page

# SPX underlier filter — adjust if the table uses different identifiers
SPX_FILTERS = ["SPX", ".SPX", "SPXW", "SPX Index"]

# Date range to extract (adjust as needed)
START_DATE = "2015-01-02"
END_DATE = "2026-07-01"

# Output
OUTPUT_DIR = Path(".")
OUTPUT_PREFIX = "spx_option_chain"


# ---------------------------------------------------------------------------
# Step 1: Discover available databases and tables
# ---------------------------------------------------------------------------

def discover_schema(cursor) -> dict:
    """Discover what databases/tables are available for option_metrics."""
    print("\n=== SCHEMA DISCOVERY ===\n")
    
    # List all databases
    cursor.execute("SHOW DATABASES")
    databases = [row[0] for row in cursor.fetchall()]
    print(f"All databases ({len(databases)}):")
    
    # Filter for option-related
    relevant_dbs = []
    for db in databases:
        if any(kw in db.lower() for kw in ["option", "ivy", "isg", "qis", "quantum", "market"]):
            relevant_dbs.append(db)
            print(f"  ★ {db}")
        elif len(databases) < 30:  # Print all if few
            print(f"    {db}")
    
    if not relevant_dbs:
        print("  (no obviously relevant DBs found, listing all)")
        for db in databases[:30]:
            print(f"    {db}")
        relevant_dbs = databases  # Try all
    
    # For each relevant DB, list tables
    schema_info = {}
    for db in relevant_dbs[:10]:  # Cap at 10 DBs to avoid timeout
        try:
            cursor.execute(f"SHOW TABLES IN `{db}`")
            tables = [row[0] for row in cursor.fetchall()]
            if tables:
                schema_info[db] = tables
                print(f"\n  Database: {db}")
                for t in tables[:20]:
                    print(f"    - {t}")
                    # If it looks like option_price, show columns
                    if any(kw in t.lower() for kw in ["option_price", "option_metric", "ivydb"]):
                        try:
                            cursor.execute(f"DESCRIBE `{db}`.`{t}`")
                            cols = cursor.fetchall()
                            print(f"      Columns ({len(cols)}):")
                            for col in cols:
                                print(f"        {col[0]:30s} {col[1]}")
                        except Exception as e:
                            print(f"      (DESCRIBE failed: {str(e)[:80]})")
        except Exception as e:
            print(f"  {db}: SHOW TABLES failed: {str(e)[:80]}")
    
    return schema_info


# ---------------------------------------------------------------------------
# Step 2: Extract SPX option chain data
# ---------------------------------------------------------------------------

def extract_spx_data(cursor, database: str, table: str, start: str, end: str):
    """Extract SPX per-strike option data from the discovered table."""
    import pandas as pd
    
    print(f"\n=== EXTRACTING SPX DATA ===")
    print(f"  Source: {database}.{table}")
    print(f"  Date range: {start} to {end}")
    
    # First, get column names
    cursor.execute(f"DESCRIBE `{database}`.`{table}`")
    columns = [row[0] for row in cursor.fetchall()]
    print(f"  Columns: {columns}")
    
    # Identify key columns (they may have different names across versions)
    date_col = next((c for c in columns if c.lower() in ("date", "closingdate", "trade_date", "observation_date")), None)
    strike_col = next((c for c in columns if "strike" in c.lower()), None)
    oi_col = next((c for c in columns if c.lower() in ("open_interest", "openinterest", "oi")), None)
    gamma_col = next((c for c in columns if c.lower() in ("gamma",)), None)
    delta_col = next((c for c in columns if c.lower() in ("delta",)), None)
    iv_col = next((c for c in columns if c.lower() in ("impl_volatility", "impliedvolatility", "implied_volatility", "iv")), None)
    volume_col = next((c for c in columns if c.lower() in ("volume", "trade_volume")), None)
    expiry_col = next((c for c in columns if c.lower() in ("exdate", "expiration", "expirationdate", "expiry_date")), None)
    cp_col = next((c for c in columns if c.lower() in ("cp_flag", "isput", "is_put", "option_type", "call_put")), None)
    ticker_col = next((c for c in columns if c.lower() in ("ticker", "symbol", "underlier", "underlying_ticker", "underliersecurityticker")), None)
    
    print(f"\n  Mapped columns:")
    print(f"    date:    {date_col}")
    print(f"    strike:  {strike_col}")
    print(f"    OI:      {oi_col}")
    print(f"    gamma:   {gamma_col}")
    print(f"    delta:   {delta_col}")
    print(f"    IV:      {iv_col}")
    print(f"    volume:  {volume_col}")
    print(f"    expiry:  {expiry_col}")
    print(f"    cp_flag: {cp_col}")
    print(f"    ticker:  {ticker_col}")
    
    if not date_col:
        print("  ERROR: Cannot identify date column. Manual mapping needed.")
        print(f"  Available columns: {columns}")
        return None
    
    # Build SELECT with available columns
    select_cols = [c for c in [date_col, strike_col, oi_col, gamma_col, delta_col, 
                               iv_col, volume_col, expiry_col, cp_col, ticker_col] if c]
    if not select_cols:
        select_cols = ["*"]
    
    select_clause = ", ".join(f"`{c}`" for c in select_cols)
    
    # Build WHERE clause
    where_parts = [f"`{date_col}` >= '{start}'", f"`{date_col}` <= '{end}'"]
    
    if ticker_col:
        spx_filter = " OR ".join(f"`{ticker_col}` = '{s}'" for s in SPX_FILTERS)
        where_parts.append(f"({spx_filter})")
    
    where_clause = " AND ".join(where_parts)
    
    query = f"SELECT {select_clause} FROM `{database}`.`{table}` WHERE {where_clause}"
    
    # First try a small sample
    sample_query = query + " LIMIT 100"
    print(f"\n  Running sample query (LIMIT 100)...")
    print(f"  {sample_query[:200]}...")
    
    try:
        cursor.execute(sample_query)
        rows = cursor.fetchall()
        if not rows:
            print("  WARNING: 0 rows returned. Trying without ticker filter...")
            # Try without ticker filter
            where_clause_no_ticker = " AND ".join(where_parts[:2])
            sample_query2 = f"SELECT {select_clause} FROM `{database}`.`{table}` WHERE {where_clause_no_ticker} LIMIT 100"
            cursor.execute(sample_query2)
            rows = cursor.fetchall()
        
        if rows:
            col_names = [desc[0] for desc in cursor.description]
            df_sample = pd.DataFrame(rows, columns=col_names)
            print(f"\n  ✓ Sample: {len(df_sample)} rows")
            print(f"    Columns: {list(df_sample.columns)}")
            print(f"    Dtypes:\n{df_sample.dtypes}")
            print(f"\n    First 5 rows:")
            print(df_sample.head().to_string())
            
            # Check if there's ticker/underlier info to filter on
            if ticker_col and ticker_col in df_sample.columns:
                unique_tickers = df_sample[ticker_col].unique()
                print(f"\n    Unique tickers in sample: {list(unique_tickers)[:20]}")
            
            return df_sample
        else:
            print("  ERROR: No data returned even without ticker filter.")
            return None
            
    except Exception as e:
        print(f"  QUERY ERROR: {e}")
        return None


# ---------------------------------------------------------------------------
# Step 3: Full extraction (chunked by month)
# ---------------------------------------------------------------------------

def full_extraction(cursor, database: str, table: str, start: str, end: str,
                    date_col: str, ticker_col: str | None, ticker_value: str | None):
    """Extract full SPX data in monthly chunks to avoid timeouts."""
    import pandas as pd
    from datetime import datetime
    
    print(f"\n=== FULL EXTRACTION (monthly chunks) ===")
    
    start_dt = datetime.strptime(start, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end, "%Y-%m-%d").date()
    
    all_chunks = []
    current = start_dt.replace(day=1)
    
    while current <= end_dt:
        # Month boundary
        if current.month == 12:
            next_month = current.replace(year=current.year + 1, month=1)
        else:
            next_month = current.replace(month=current.month + 1)
        
        chunk_start = max(current, start_dt).isoformat()
        chunk_end = min(next_month - timedelta(days=1), end_dt).isoformat()
        
        # Build query
        where_parts = [f"`{date_col}` >= '{chunk_start}'", f"`{date_col}` <= '{chunk_end}'"]
        if ticker_col and ticker_value:
            where_parts.append(f"`{ticker_col}` = '{ticker_value}'")
        
        query = f"SELECT * FROM `{database}`.`{table}` WHERE {' AND '.join(where_parts)}"
        
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            if rows:
                col_names = [desc[0] for desc in cursor.description]
                chunk_df = pd.DataFrame(rows, columns=col_names)
                all_chunks.append(chunk_df)
                print(f"  {chunk_start} to {chunk_end}: {len(chunk_df):,} rows")
            else:
                print(f"  {chunk_start} to {chunk_end}: 0 rows")
        except Exception as e:
            print(f"  {chunk_start} to {chunk_end}: ERROR — {str(e)[:100]}")
        
        current = next_month
    
    if all_chunks:
        result = pd.concat(all_chunks, ignore_index=True)
        print(f"\n  Total: {len(result):,} rows")
        return result
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("  ISG OptionMetrics — SPX Per-Strike Data Extraction")
    print(f"  Date: {date.today().isoformat()}")
    print(f"  Target: {HIVE_HOST}:{HIVE_PORT}")
    print(f"  Entitlement: isg-marketdata-accessor")
    print("=" * 70)
    
    # Check prerequisites
    try:
        from pyhive import hive
    except ImportError:
        print("\nERROR: pyhive not installed.")
        print("  Install with: pip install 'pyhive[hive]' thrift sasl thrift-sasl")
        sys.exit(1)
    
    try:
        import pandas as pd
    except ImportError:
        print("\nERROR: pandas not installed.")
        print("  Install with: pip install pandas pyarrow")
        sys.exit(1)
    
    # Connect to HIVE
    print(f"\nConnecting to HiveServer2 at {HIVE_HOST}:{HIVE_PORT}...")
    print(f"  Auth: Kerberos (service={KERBEROS_SERVICE_NAME})")
    print(f"  Make sure you have a valid ticket (run: kinit vincry@GS.COM)")
    
    try:
        conn = hive.Connection(
            host=HIVE_HOST,
            port=HIVE_PORT,
            auth="KERBEROS",
            kerberos_service_name=KERBEROS_SERVICE_NAME,
        )
        cursor = conn.cursor()
        print("  ✓ Connected!")
    except Exception as e:
        print(f"\n  ✗ Connection failed: {e}")
        print("\n  Troubleshooting:")
        print("    1. Run: kinit vincry@GS.COM")
        print("    2. Run: klist  (verify ticket is valid)")
        print("    3. Check network: nc -zv d440120-002.dc.gs.com 10000")
        print("    4. If port refused, try alternative host (check with ISG team)")
        print("\n  Alternative: try the Hive Metastore on port 9083 for schema discovery only")
        sys.exit(1)
    
    # Phase 1: Discover schema
    schema_info = discover_schema(cursor)
    
    if not schema_info:
        print("\nNo tables found. Your entitlement may not cover HIVE queries.")
        print("Contact: gs-pwm-quantum-isg-support")
        conn.close()
        sys.exit(1)
    
    # Phase 2: Try to extract data
    # Look for the most promising table
    target_db = None
    target_table = None
    
    for db, tables in schema_info.items():
        for t in tables:
            if "option_price" in t.lower() or "option_metric" in t.lower():
                target_db = db
                target_table = t
                break
        if target_db:
            break
    
    if not target_db:
        # Fall back to first table in first relevant DB
        for db, tables in schema_info.items():
            if tables:
                target_db = db
                target_table = tables[0]
                break
    
    if target_db and target_table:
        sample = extract_spx_data(cursor, target_db, target_table, START_DATE, END_DATE)
        
        if sample is not None and not sample.empty:
            # Save sample
            sample_path = OUTPUT_DIR / f"{OUTPUT_PREFIX}_sample.parquet"
            sample.to_parquet(sample_path, index=False)
            print(f"\n  Sample saved to: {sample_path}")
            
            # Ask user if they want full extraction
            print("\n" + "=" * 70)
            print("  SAMPLE EXTRACTION SUCCESSFUL")
            print("  Review the sample above. To do full extraction,")
            print("  uncomment the full_extraction() call below and re-run.")
            print("=" * 70)
            
            # Uncomment below for full extraction after verifying sample looks correct:
            # ---------------------------------------------------------------
            # date_col = ...  # fill from sample discovery
            # ticker_col = ...  # fill from sample discovery  
            # ticker_value = "SPX"  # or whatever the sample showed
            # full_df = full_extraction(cursor, target_db, target_table, 
            #                           START_DATE, END_DATE,
            #                           date_col, ticker_col, ticker_value)
            # if full_df is not None:
            #     out_path = OUTPUT_DIR / f"{OUTPUT_PREFIX}_{START_DATE}_{END_DATE}.parquet"
            #     full_df.to_parquet(out_path, index=False)
            #     print(f"\n  Full data saved to: {out_path}")
            #     print(f"  Size: {out_path.stat().st_size / 1024 / 1024:.1f} MB")
            # ---------------------------------------------------------------
    else:
        print("\nCould not identify target table. Review schema discovery output above.")
    
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
