---
created: 2026-04-10
updated: 2026-07-29
tags: [python, chunk-store, tick-data, market-data, pytickclient, L1, L2, us-equities]
status: active
relates:
  - ref/python-tsdb.md
  - ref/python-pyslang.md
---

# Chunk Store — Tick Data Query Reference

Intraday L1 (BBO + trades) and L2 (depth-of-book) tick data via `pytickclient`.
Covers the 34-symbol US universe (30 mega-cap equities + `SPY`/`QQQ`/`IWM`/`DIA`
+ E-mini S&P 500 `ES`). L2 depth is available for E-mini only.

Real project call sites: `src/volforecast/data/chunk_store.py`,
`src/volforecast/data/micro.py`, `src/volforecast/data/spx_allday_vols.py`.

---

## 1. Setup & imports

```python
from pytickclient import query
import pytz
from datetime import datetime

CHUNKDB = "Eq"                              # always "Eq" for equities/futures
TZ      = pytz.timezone("America/New_York") # US session timezone
```

> **`pyslang.start()` must be called before `query.chunk_query()`** — pyslang
> initializes the tick-infra connection. `_ensure_session()` in
> `chunk_store.py` handles this transparently.

---

## 2. Core function: `query.chunk_query`

```python
raw = query.chunk_query(symbols, start_time, end_time, chunkdb, fields=fields)
df  = pd.DataFrame(raw)
```

### 2.1 Parameters

| Parameter    | Type                | Description |
|--------------|---------------------|-------------|
| `symbols`    | `list[str]`         | RICs — e.g. `["SPY"]`, `["AAPL.OQ"]`, `["ESM26"]` |
| `start_time` | tz-aware `datetime` | Start of window; **must** be tz-aware |
| `end_time`   | tz-aware `datetime` | End of window; **must** be tz-aware |
| `chunkdb`    | `str`               | Always `"Eq"` |
| `fields`     | `list[str]`         | Field names (see §4) |

Returns a dict-of-lists — convert with `pd.DataFrame(raw)`. Always contains a
`Time` column plus the requested fields.

---

## 3. Timezone handling (CRITICAL)

Validated on `2020-01-02` in `data-access.md`; a single misuse silently
truncated ~60% of the trading day (RV came out ~60% low).

```python
TZ = pytz.timezone("America/New_York")
st = TZ.localize(datetime(2025, 4, 15,  9, 30, 0))
et = TZ.localize(datetime(2025, 4, 15, 16,  0, 0))
raw = query.chunk_query(["SPY"], st, et, CHUNKDB, fields=fields)
df  = pd.DataFrame(raw)

# Server returns UTC — CONVERT, never LOCALIZE
df["Time"] = pd.to_datetime(df["Time"])
if df["Time"].dt.tz is None:
    df["Time"] = df["Time"].dt.tz_localize("UTC").dt.tz_convert(TZ)
else:
    df["Time"] = df["Time"].dt.tz_convert(TZ)
```

**Never** `tz_localize("America/New_York")` on returned timestamps — that
mis-labels UTC 14:30 as ET 14:30 and shifts data 4–5 hours in EST months.
Multi-day loop: see §8.

---

## 4. Fields

### 4.1 Level 1 (BBO + trades)

`constants.L1_FIELDS`:

```python
L1_FIELDS = ["TRDPRC_1", "TRDVOL_1", "ASK", "BID", "ASKSIZE", "BIDSIZE"]
```

Extended L1 adds `TRDBUYERID`, `TRDSELLRID`, `PRCTCK_1` (1=up, 2=down,
3=unchanged) and `PRC_QL_CD` (price qualifier code).

### 4.2 Level 2 / depth-of-book (E-mini only)

Deep-book symbols append `m` to the L1 RIC (see §5.2). Field shape — five
levels per side:

```python
fields_dp = [f"BEST_{p}{i}"
             for p in ("BID", "ASK", "BSIZ", "ASIZ")
             for i in range(1, 6)]
```

`chunk_store.fetch_l2_depth(...)` builds this list dynamically for a
requested `levels` count (max 5).

---

## 5. Symbol naming — US universe

### 5.1 Equities & ETFs

`TICKER_TO_RIC` in `constants.py`. NASDAQ → `.OQ`, NYSE → `.N`, ETFs bare
(`SPY`, `QQQ`, `IWM`, `DIA`). Deep-book RIC appends `m` (e.g. `AAPL.OQm`,
`JPM.Nm`, `SPYm`) — shape only; only **E-mini `ES`** actually has L2 data in
this project's universe. Compressed NYSE cases: `BRK.B` → `BRKb.N`.

### 5.2 E-mini S&P 500 (`ES`) — quarterly rolling

CME month codes: `H=Mar, M=Jun, U=Sep, Z=Dec`.

Contract symbol shape: `ES{code}{YY}` — e.g. `ESH26`, `ESM26`, `ESU26`, `ESZ26`.
Deep-book symbol appends `m`: `ESM26m`.

Roll rule (`chunk_store._resolve_es_symbol`): the front contract flips to the
next quarter on the **Thursday before the 3rd Friday** of the expiring month.

```python
from datetime import date
from volforecast.data.chunk_store import _resolve_es_symbol

front = _resolve_es_symbol(date(2026, 6, 10))   # 'ESM26'
front = _resolve_es_symbol(date(2026, 6, 12))   # 'ESU26' (post-roll)
```

---

## 6. Post-processing patterns

```python
# Forward-fill NaN between updates
for f in fields:
    df[f] = df[f].ffill()

# Filter to RTH (09:30–16:00 ET)
from datetime import time as dt_time
mask = (df["Time"].dt.time >= dt_time(9, 30)) & (df["Time"].dt.time <= dt_time(16, 0))
df = df[mask]

# Mid price
valid = df[(df["BID"] > 0) & (df["ASK"] > 0)].copy()
valid["Mid"] = (valid["BID"] + valid["ASK"]) / 2.0

# Daily close per date
daily_close = (df[df["TRDPRC_1"] > 0]
               .groupby(df["Time"].dt.date)["TRDPRC_1"].last())

# Log returns
df["TRDPRC_1"]   = df["TRDPRC_1"].ffill()
df["Log_Return"] = np.log(df["TRDPRC_1"] / df["TRDPRC_1"].shift(1))

# Merge L1 + L2 (E-mini)
l1 = pd.DataFrame(query.chunk_query(["ESM26"],  st, et, "Eq", fields=L1_FIELDS))
l2 = pd.DataFrame(query.chunk_query(["ESM26m"], st, et, "Eq", fields=fields_dp))
for f in L1_FIELDS: l1[f] = l1[f].ffill()
for f in fields_dp: l2[f] = l2[f].ffill()
merged = pd.merge(l1, l2, on="Time", how="outer")
```

---

## 7. Fast path — server-side `AggGroupBy`

For daily RV / bar aggregates, use `pytickclient.processor.AggGroupBy` instead
of raw ticks. ~14× faster (78 bars/day vs ~1.2M ticks) and produces identical
RV (0.00% difference, validated 2026-05-14). Eastern-localized `start`/`end`;
the server handles UTC. Batches up to ~20 days per call safely.

```python
from pytickclient import processor
agg = processor.AggGroupBy(
    groupByOperations=[
        "first(TRDPRC_1)", "max(TRDPRC_1)", "min(TRDPRC_1)",
        "last(TRDPRC_1)",  "sum(TRDVOL_1)", "count(TRDPRC_1)",
    ],
    interval=300.0,   # seconds; 300 = 5-min bars
)
raw = query.chunk_query(["SPY"], st, et, "Eq",
                        fields=L1_FIELDS, processors=[agg])
```

---

## 8. Multi-day fetch pattern (US trading days)

```python
import pandas_market_calendars as mcal

nyse   = mcal.get_calendar("XNYS")
t_days = [d.date() for d in nyse.schedule(
    start_date="2025-01-02", end_date="2025-04-15").index]

raw_data = {}
for sym in symbols:
    ric = TICKER_TO_RIC.get(sym, sym)
    frames = []
    for td in t_days:
        symbol = _resolve_es_symbol(td) if sym == "ES" else ric
        st = TZ.localize(datetime(td.year, td.month, td.day,  9, 30, 0))
        et = TZ.localize(datetime(td.year, td.month, td.day, 16,  0, 0))
        df = pd.DataFrame(
            query.chunk_query([symbol], st, et, CHUNKDB, fields=L1_FIELDS))
        if df.empty:
            continue
        for f in L1_FIELDS:
            df[f] = df[f].ffill()
        df["Time"] = (pd.to_datetime(df["Time"])
                        .dt.tz_localize("UTC").dt.tz_convert(TZ))
        frames.append(df)
    if frames:
        raw_data[sym] = pd.concat(frames, ignore_index=True)
```

Batched, timeout-protected version: `chunk_store._chunk_query_with_timeout`.

---

## 9. Quick reference

```python
TZ = pytz.timezone("America/New_York")
st = TZ.localize(datetime(2025, 4, 15,  9, 30, 0))
et = TZ.localize(datetime(2025, 4, 15, 16,  0, 0))

# L1 — SPY trades + BBO
L1 = ["TRDPRC_1", "TRDVOL_1", "ASK", "ASKSIZE", "BID", "BIDSIZE"]
df = pd.DataFrame(query.chunk_query(["SPY"], st, et, "Eq", fields=L1))

# L2 — E-mini depth (only symbol with L2 in this universe)
L2 = [f"BEST_{p}{i}" for p in ("BID","ASK","BSIZ","ASIZ") for i in range(1,6)]
df_dp = pd.DataFrame(query.chunk_query(["ESM26m"], st, et, "Eq", fields=L2))
```
