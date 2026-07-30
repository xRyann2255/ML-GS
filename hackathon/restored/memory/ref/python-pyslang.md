---
created: 2026-04-10
updated: 2026-04-15
tags: [python, pyslang, secdb, slang, setup, data-access]
status: active
relates:
  - ref/python-tsdb.md
  - ref/python-chunk.md
---

# PySlang — Setup & Usage Guide

PySlang is the Python bridge to the Slang/SecDB environment. It provides access to Slang user functions (stored in the Slang database), TSDB time-series data, and Chunk Store tick data.

---

## 1. Installation & Import

```python
import goldmansachs.pyslang as pyslang
```

PySlang is pre-installed in the GS environment. No `pip install` needed.

---

## 2. Starting PySlang

You **must** call `pyslang.start()` before importing any Slang user functions. The call accepts optional keyword arguments that control which databases are loaded.

### 2.1 Common Start Patterns

```python
# ── Minimal (default source database) ────────────────────────────────────
pyslang.start()

# ── With object_database only ────────────────────────────────────────────
pyslang.start(object_database="Equity")

# ── Subprocess mode with explicit source & object databases ──────────────
# This is the most common pattern for PySlang notebooks.
pyslang.start(
    subprocess=True,
    object_database="Equity",
    # you can put your source db source_database="~lourel!commit;Source"  
)

```

### 2.2 Parameter Reference

| Parameter          | Type   | Description                                                                                            |
| ------------------ | ------ | ------------------------------------------------------------------------------------------------------ |
| `subprocess`       | `bool` | Run Slang in a subprocess (recommended for notebooks, avoids memory issues). Default `False`.          |
| `object_database`  | `str`  | The object database to connect to (e.g. `"Equity"`).                                                   |
| `source_database`  | `str`  | The Slang source database path. Format: `"~user!branch;Source"` or `"!NYC Source"`.                    |

### 2.3 Stopping PySlang

```python
pyslang.stop()
```

Call `pyslang.stop()` before `pyslang.start()` if you need to restart with different parameters (common in library files).

---

## 3. Importing Slang User Functions

After `pyslang.start()`, you can import functions that live in the Slang source database as if they were Python modules. The module name maps to the Slang library name, and functions are prefixed according to convention.

```python
# ── From _lib_eq1d_brazil_tsdb_fns (TSDB wrappers) ──────────────────────
from _lib_eq1d_brazil_tsdb_fns import eq1d_brazil__tsdb_rt   # realtime TSDB
from _lib_eq1d_brazil_tsdb_fns import eq1d_brazil__tsdb      # daily TSDB

# ── From _lib_eq1d_brazil_s3_fns (S3 load/save) ─────────────────────────
from _lib_eq1d_brazil_s3_fns import eq1d_latam_s3__load_data
from _lib_eq1d_brazil_s3_fns import eq1d_latam_s3__save_data

# ── From _lib_eq1d_brazil_etf_fns (interest rates, ETF helpers) ──────────
from _lib_eq1d_brazil_etf_fns import eq1d_brazil__cache_interest_rates_list

# ── From _LIB_Eq1D_Brazil_ETF_Fns ───────────────────────────────────────
from _LIB_Eq1D_Brazil_ETF_Fns import eq1d_brazil_etf__get_etf_composition
from _LIB_Eq1D_Brazil_ETF_Fns import eq1d_brazil_etf__get_index_composition
```

> **Note:** These are `pyslang.functions.SlangUserFunction` objects. They are NOT local `.py` files — they live inside the Slang database and are resolved at runtime via `pyslang.start()`.

---

## 4. Slang Date Conversion

Many Slang functions expect dates in Slang format: `"DDMonYY"` (e.g., `"15Apr25"`).

```python
import calendar, pandas as pd

def convert_date_to_slang(date):
    date = pd.Timestamp(date)
    day   = date.day
    month = calendar.month_name[date.month][:3]
    year  = str(date.year)[2:]
    return f"{day}{month}{year}"

# Example: convert_date_to_slang("2025-04-15") → "15Apr25"
```

---

## 5. Exchange Dates

```python
# Get business days for a given exchange
dates = expose2python__exchange_dates(
    convert_date_to_slang(start_date),
    convert_date_to_slang(end_date),
    exchange="SAOE"           # Brazil equities. Others: "NYSE", "CME", "IMM", "MXN"
)
# Returns: list of date strings
```

---

## 6. S3 Data Load / Save (via Slang)

```python
S3Credentials = "ECS OBS V2 Latam Dashboard"
Bucket        = "eqlatam"
S3Db          = "Equity"

# Load
data = eq1d_latam_s3__load_data("Array", S3Credentials, Bucket, "key_name", db=S3Db)

# Save
eq1d_latam_s3__save_data(["DIJF37"], S3Credentials, Bucket, "key_name", db=S3Db)
```

---

## 7. Interest Rate Contract Universe

```python
rates = eq1d_brazil__cache_interest_rates_list()

# rates is a dict with keys:
#   rates['liquidity']  → dict of product families → { expiry_date: ric_code }
#                          e.g. rates['liquidity']['dij dij'] → {datetime(2026,1,1): 'DIJF26', ...}
#                               rates['liquidity']['ddi dap'] → {datetime(2026,1,1): 'DAPF26', ...}
#   rates['risk']       → flat dict keyed by lowercase product code
#                          e.g. { 'diju26': {'brr': ..., 'ipa': -0.57, ...}, ... }
#   rates['all']        → same structure as liquidity but includes illiquid contracts
```

---

## 8. Flask / API Pattern

The backtest server exposes Slang functions via a generic REST endpoint:

```python
# POST /api/call_slang_function
# Body: { "lib": "LIB_NAME", "routine": "function_name" }
# The server dynamically imports the Slang library and calls the function.
slang = __import__(lib, fromlist=[routine])
result = getattr(slang, routine)(content)
```

---

## 9. Common Boilerplate (Copy-Paste Ready)

```python
import datetime, warnings, os, time
import pandas as pd
import numpy as np
import holidays
from datetime import date, datetime, timedelta
import pytz
import goldmansachs.pyslang as pyslang

pyslang.start(subprocess=True, object_database="Equity",
              source_database="~lourel!commit;Source")

pd.options.display.float_format = '{:,.4f}'.format
warnings.filterwarnings('ignore')

br_holidays = holidays.BR()
local = pytz.timezone("America/Sao_Paulo")
chunkdb = "Eq"

# Import Slang functions as needed:
from _lib_eq1d_brazil_tsdb_fns import eq1d_brazil__tsdb_rt, eq1d_brazil__tsdb
from _lib_eq1d_brazil_s3_fns  import eq1d_latam_s3__load_data, eq1d_latam_s3__save_data
from _lib_eq1d_brazil_etf_fns import eq1d_brazil__cache_interest_rates_list

print("✅ PySlang ready")
```

---

## 10. GS Quant TSDB (Alternative Path)

Some scripts use `gs_quant_internal.tsdb.TSDBSymbol` directly (requires `GsSession.use()`):

```python
from gs_quant.session import GsSession
GsSession.use()
from gs_quant_internal.tsdb import TSDBSymbol

data = TSDBSymbol("eqpad_PETR4.SA@close").get_data(start="2025-01-01", end="2025-04-01")
```

See `ref/python-tsdb.md` for the full TSDB reference.
