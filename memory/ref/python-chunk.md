---
created: 2026-04-10
updated: 2026-04-15
tags: [python, chunk-store, tick-data, market-data, pytickclient, L1, L2]
status: active
relates:
  - ref/python-tsdb.md
  - ref/python-pyslang.md
---

# Chunk Store — Tick Data Query Reference

The Chunk Store is the tick-level market data system accessed via `pytickclient`. It provides intraday Level 1 (BBO + trades) and Level 2 (depth-of-book) data.

---

## 1. Setup & Import

```python
from pytickclient import query
import pytz

chunkdb = "Eq"                                  # Chunk database name (always "Eq" for equities/rates)
local   = pytz.timezone("America/Sao_Paulo")    # Timezone for Sao Paulo
```

> **Note:** `pyslang.start()` must be called before `query.chunk_query()` works, because pyslang initializes the connection to the tick data infrastructure.

---

## 2. Core Function: `query.chunk_query`

```python
result = query.chunk_query(symbols, start_time, end_time, chunkdb, fields=fields)
df = pd.DataFrame(result)
```

### 2.1 Parameters

| Parameter    | Type              | Description                                                                    |
| ------------ | ----------------- | ------------------------------------------------------------------------------ |
| `symbols`    | `list[str]`       | List of RIC symbols, e.g. `["WINJ25"]`, `["PETR4.SA"]`, `["DIJF26"]`          |
| `start_time` | `datetime` (tz-aware) | Start of query window. **Must be timezone-aware** (use `pytz.localize`).   |
| `end_time`   | `datetime` (tz-aware) | End of query window. **Must be timezone-aware**.                           |
| `chunkdb`    | `str`             | Chunk database name. Always `"Eq"` for equities/futures/rates.                 |
| `fields`     | `list[str]`       | List of field names to retrieve (see field reference below).                   |

### 2.2 Return Value

Returns a dict-of-lists that converts to a DataFrame with `pd.DataFrame(result)`. The DataFrame always contains a `Time` column plus the requested fields.

---

## 3. Timezone Handling (CRITICAL)

Start and end times **must** be timezone-aware. Use `pytz.localize()`:

```python
import pytz
from datetime import datetime

local = pytz.timezone("America/Sao_Paulo")

# ✅ Correct — localize then query
st = local.localize(datetime(2025, 4, 15, 9, 0, 0))
et = local.localize(datetime(2025, 4, 15, 18, 0, 0))
df = pd.DataFrame(query.chunk_query(["WINJ25"], st, et, "Eq", fields=fields))

# ❌ Wrong — naive datetime will fail or return wrong data
st = datetime(2025, 4, 15, 9, 0, 0)  # NOT timezone-aware!
```

For multiple days, loop through each trading day individually:

```python
for td in trading_days:
    st = local.localize(datetime(td.year, td.month, td.day, 9, 0, 0))
    et = local.localize(datetime(td.year, td.month, td.day, 18, 0, 0))
    df = pd.DataFrame(query.chunk_query([sym], st, et, chunkdb, fields=fields))
```

---

## 4. Field Reference

### 4.1 Level 1 Fields (BBO + Trades)

Standard field set for top-of-book and trade data:

```python
fields = [
    "TRDPRC_1",      # Last trade price
    "TRDVOL_1",      # Last trade volume
    "ASKSIZE",        # Best ask size
    "ASK",            # Best ask price
    "BIDSIZE",        # Best bid size
    "BID",            # Best bid price
]
```

Extended Level 1 fields (include trade counterparties and tick direction):

```python
fields = [
    "TRDPRC_1",      # Last trade price
    "TRDVOL_1",      # Last trade volume
    "TRDBUYERID",    # Trade buyer broker ID
    "TRDSELLRID",    # Trade seller broker ID
    "PRCTCK_1",      # Price tick direction: 1=up, 2=down, 3=unchanged
    "PRC_QL_CD",     # Price qualifier code
    "ASKSIZE",        # Best ask size
    "ASK",            # Best ask price
    "BIDSIZE",        # Best bid size
    "BID",            # Best bid price
]
```

### 4.2 Level 2 / Depth-of-Book Fields

For depth-of-book data, use the **deep-book symbol** (append `m` to the symbol) and depth fields:

```python
fields_dp = [
    'BEST_BSIZ1', 'BEST_BSIZ2', 'BEST_BSIZ3', 'BEST_BSIZ4', 'BEST_BSIZ5',  # Bid sizes L1–L5
    'BEST_ASIZ1', 'BEST_ASIZ2', 'BEST_ASIZ3', 'BEST_ASIZ4', 'BEST_ASIZ5',  # Ask sizes L1–L5
    'BEST_BID1',  'BEST_BID2',  'BEST_BID3',  'BEST_BID4',  'BEST_BID5',   # Bid prices L1–L5
    'BEST_ASK1',  'BEST_ASK2',  'BEST_ASK3',  'BEST_ASK4',  'BEST_ASK5',   # Ask prices L1–L5
]
```

---

## 5. Symbol Naming Conventions

| Asset Type              | L1 Symbol           | L2 (Deep) Symbol     | Examples                                     |
| ----------------------- | ------------------- | -------------------- | -------------------------------------------- |
| Mini IBOV future        | `WINJ25`            | `WINJ25m`            | WIN + month code + year                      |
| Full IBOV future        | `INDJ25`            | `INDJ25m`            | IND + month code + year                      |
| Mini Dollar future      | `WDOJ25`            | `WDOJ25m`            | WDO + month code + year                      |
| Full Dollar future      | `DOLJ25`            | `DOLJ25m`            | DOL + month code + year                      |
| Brazilian equities      | `PETR4.SA`          | `PETR4.SAp`          | RIC + `.SA`, deep adds `p`                   |
| ETFs                    | `BOVA11.SA`         | `BOVA11.SAp`         | Same pattern                                 |
| ETFs (alternate)        | `SMAC11.SA`         | `SMAC11.SAp`         |                                              |
| Fixed Income ETFs       | `IRFM11=SA`         | `IRFM11=SAp`         | Note `=` instead of `.` for some ETFs        |
| DI futures (pre-fixed)  | `DIJF26`            | —                    | DIJ + month code + year                      |
| DAP futures (cupom)     | `DAPQ40`            | —                    | DAP + month code + year                      |
| IPA/IR futures          | `IPAQ26`            | —                    | IPA + month code + year                      |
| Mexican IPC future      | `IPCM25`            | —                    | IPC + month code + year                      |
| Mexican Peso future     | `MPM25`             | —                    | MP + month code + year                       |
| S&P E-mini              | `ESM25`             | —                    | ES + month code + year                       |

### Month Codes (B3 / CME)

| Code | Month | Code | Month |
| ---- | ----- | ---- | ----- |
| F    | Jan   | N    | Jul   |
| G    | Feb   | Q    | Aug   |
| H    | Mar   | U    | Sep   |
| J    | Apr   | V    | Oct   |
| K    | May   | X    | Nov   |
| M    | Jun   | Z    | Dec   |

> **WIN/IND** only use bi-monthly codes: G, J, M, Q, V, Z (Feb, Apr, Jun, Aug, Oct, Dec).

---

## 6. Common Post-Processing Patterns

### 6.1 Forward-Fill Missing Fields

After fetching tick data, fields may contain NaN between updates. Always forward-fill:

```python
df = pd.DataFrame(query.chunk_query(symbols, st, et, chunkdb, fields=fields))
for f in fields:
    df[f] = df[f].ffill()
df['Time'] = pd.to_datetime(df['Time'])
```

### 6.2 Extract Date Column

```python
df['Date'] = df['Time'].dt.date
```

### 6.3 Compute Mid Price

```python
valid = df[(df['BID'] > 0) & (df['ASK'] > 0)].copy()
valid['Mid'] = (valid['BID'] + valid['ASK']) / 2.0
```

### 6.4 Get Last Trade per Day

```python
trades = df[df['TRDPRC_1'] > 0].copy()
trades['Date'] = trades['Time'].dt.date
daily_close = trades.groupby('Date')['TRDPRC_1'].last()
```

### 6.5 Get Last Mid per Day

```python
valid['Date'] = valid['Time'].dt.date
daily_mid = valid.groupby('Date')['Mid'].last()
```

### 6.6 Log Returns

```python
df['TRDPRC_1'] = df['TRDPRC_1'].ffill()
df['Log_Return'] = np.log(df['TRDPRC_1'] / df['TRDPRC_1'].shift(1))
```

### 6.7 Merge L1 + L2 Data

```python
result    = pd.DataFrame(query.chunk_query(["WINJ25"],  st, et, "Eq", fields=fields))
result_dp = pd.DataFrame(query.chunk_query(["WINJ25m"], st, et, "Eq", fields=fields_dp))

for f in fields:    result[f]    = result[f].ffill()
for f in fields_dp: result_dp[f] = result_dp[f].ffill()

result['Time']    = pd.to_datetime(result['Time'])
result_dp['Time'] = pd.to_datetime(result_dp['Time'])

merged = pd.merge(result, result_dp, on='Time', how='outer')
```

---

## 7. Helper Function: `chunk_data` (in `libs/lib_intraday_prices.py`)

A convenience wrapper:

```python
from lib_intraday_prices import chunk_data

df = chunk_data(
    symbols=["WINJ25"],
    start=datetime(2025, 4, 15, 9, 0, 0),      # naive datetime OK here (localized internally)
    end=datetime(2025, 4, 15, 18, 0, 0),
    fields=["TRDPRC_1", "TRDVOL_1", "ASK", "BID", "ASKSIZE", "BIDSIZE"],
    dp=False,                                     # True for depth-of-book
    chunkdb="Eq",
    local_tz="America/Sao_Paulo"
)
```

When `dp=True`, it overrides `fields` with the L2 depth fields automatically.

---

## 8. Multi-Day Fetch Pattern (Production)

Fetching multiple days of tick data for multiple symbols:

```python
import holidays
from datetime import date, datetime, timedelta
import pytz

br_holidays = holidays.BR()
local = pytz.timezone("America/Sao_Paulo")
chunkdb = "Eq"

fields = ["TRDPRC_1", "TRDVOL_1", "ASKSIZE", "ASK", "BIDSIZE", "BID"]

def trading_days(start, end):
    """Generate list of Brazilian business days."""
    days, cur = [], start
    while cur <= end:
        if cur.weekday() < 5 and cur not in br_holidays:
            days.append(cur)
        cur += timedelta(days=1)
    return days

t_days = trading_days(date(2025, 1, 2), date(2025, 4, 15))

raw_data = {}
daily_close = {}

for sym in all_symbols:
    frames = []
    for td in t_days:
        try:
            st = local.localize(datetime(td.year, td.month, td.day, 9, 0, 0))
            et = local.localize(datetime(td.year, td.month, td.day, 18, 0, 0))
            df = pd.DataFrame(
                query.chunk_query([sym], st, et, chunkdb, fields=fields)
            )
            if len(df) > 0:
                for f_ in fields:
                    df[f_] = df[f_].ffill()
                df['Time'] = pd.to_datetime(df['Time'])
                df['Date'] = df['Time'].dt.date
                frames.append(df)
        except Exception:
            pass

    if frames:
        combined = pd.concat(frames, ignore_index=True)
        raw_data[sym] = combined
        # Extract daily close
        trades = combined[combined['TRDPRC_1'] > 0].copy()
        if len(trades) > 0:
            trades['Date'] = trades['Time'].dt.date
            daily_close[sym] = trades.groupby('Date')['TRDPRC_1'].last()
```

---

## 9. Quick Reference

```python
# ── Single-day L1 query ──────────────────────────────────────────────────
from pytickclient import query
import pytz
local = pytz.timezone("America/Sao_Paulo")

st = local.localize(datetime(2025, 4, 15, 9, 0, 0))
et = local.localize(datetime(2025, 4, 15, 18, 0, 0))

fields = ["TRDPRC_1", "TRDVOL_1", "ASKSIZE", "ASK", "BIDSIZE", "BID"]
df = pd.DataFrame(query.chunk_query(["PETR4.SA"], st, et, "Eq", fields=fields))

# ── Single-day L2 (depth) query ──────────────────────────────────────────
fields_dp = ['BEST_BSIZ1','BEST_BSIZ2','BEST_BSIZ3','BEST_BSIZ4','BEST_BSIZ5',
             'BEST_ASIZ1','BEST_ASIZ2','BEST_ASIZ3','BEST_ASIZ4','BEST_ASIZ5',
             'BEST_BID1','BEST_BID2','BEST_BID3','BEST_BID4','BEST_BID5',
             'BEST_ASK1','BEST_ASK2','BEST_ASK3','BEST_ASK4','BEST_ASK5']
df_dp = pd.DataFrame(query.chunk_query(["PETR4.SAp"], st, et, "Eq", fields=fields_dp))
```
