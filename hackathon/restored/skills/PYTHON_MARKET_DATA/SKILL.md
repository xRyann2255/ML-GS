---
name: PYTHON_MARKET_DATA
description: "Query market data from Python: Chunk Store tick data (L1/L2), TSDB daily/realtime time series, GS Quant TSDBSymbol (no pyslang needed), PySlang setup. USE FOR: intraday tick queries, daily OHLCV, depth-of-book, VWAP, multi-day fetches, futures/equities/FX/rates data, pyslang.start lifecycle, TSDBSymbol lookups, quick price checks. DO NOT USE FOR: Slang script editing, SecDB positions, trade booking."
---

# PYTHON_MARKET_DATA — Query Market Data via Python

> **Purpose:** Fetch and analyze market data from Python using four APIs: GS Quant TSDBSymbol (lightweight, no pyslang), Slang TSDB wrappers (daily/realtime), Chunk Store (tick-level), and PySlang (Slang bridge). Covers US equities, futures, FX, and rates.

**Out of scope:** Slang script editing, SecDB position sourcing, trade booking, portfolio construction.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `PYTHON_MARKET_DATA` |
| **Scope** | Market data retrieval and processing via Python |
| **Inputs** | Symbols, date ranges, fields, asset type |
| **Outputs** | DataFrames (prices, volumes, BBO, depth, time series) |
| **Authority** | Read-only (no DB writes) |

## When to Use

- **Quick price check** for a single symbol — use GS Quant TSDBSymbol (no pyslang needed)
- Fetch **intraday tick data** (trades, BBO, depth-of-book) via Chunk Store
- Fetch **daily time series** (close, open, high, low, volume) via TSDB
- Fetch **realtime intraday series** via TSDB RT
- Compute VWAP, daily close, mid prices, log returns from tick data
- Multi-day or multi-symbol fetch loops for backtests or analysis
- Look up correct symbol naming (RIC, deep-book, TSDB symbol conventions)
- Initialize PySlang session (`pyslang.start()`) for any Slang-dependent Python work

---

## Memory References

Load these before writing code:

| File | Content |
|------|---------|
| memory/ref/python-pyslang.md | PySlang lifecycle, Slang function imports, S3 data, boilerplate |
| memory/ref/python-tsdb.md | TSDB daily/RT wrappers, TSDBSymbol API, field dictionary |
| memory/ref/python-chunk.md | Chunk Store tick data, L1/L2 fields, timezone handling, patterns |

---

## API Decision Tree

| Need | API | Requires pyslang? | Function |
|------|-----|--------------------|----------|
| Quick price / single symbol | **GS Quant TSDBSymbol** | No | `TSDBSymbol("eqpad_RIC@field").get_data(start, end)` |
| Adjusted prices, FX, CDI | **GS Quant TSDBSymbol** | No | `TSDBSymbol("eqpad_RIC@close.adj.allincdiv").get_data(...)` |
| End-of-day OHLCV (batch) | TSDB Daily | Yes | `eq1d_brazil__tsdb(symbol, field, start_date, end_date)` |
| Intraday tick series | TSDB RT | Yes | `eq1d_brazil__tsdb_rt(symbol, field, start_dt, end_dt)` |
| Full tick data (trades + BBO) | Chunk Store | Yes | `query.chunk_query(symbols, st, et, chunkdb, fields)` |
| Depth-of-book (L2) | Chunk Store | Yes | `query.chunk_query([sym+"m"], st, et, chunkdb, fields_dp)` |

**Prefer GS Quant TSDBSymbol** for simple lookups — it's faster, lighter, and doesn't need a pyslang subprocess. Use pyslang-based APIs when you need Slang user functions, Chunk Store access, or batch workflows.

---

## Procedure

### 1. GS Quant TSDBSymbol (Standalone — No PySlang)

For quick price checks or daily time series, use `TSDBSymbol` directly. No `pyslang.start()` needed.

```python
from gs_quant.session import GsSession
GsSession.use()
from gs_quant_internal.tsdb import TSDBSymbol
from datetime import date, timedelta

end = date.today()
start = end - timedelta(days=10)

# Raw close
data = TSDBSymbol("eqpad_PETR4.SA@close").get_data(start=str(start), end=str(end))
print(f"Latest close: {data.iloc[-1]:.2f}")

# Adjusted close (splits + dividends)
adj = TSDBSymbol("eqpad_PETR4.SA@close.adj.allincdiv").get_data(start=str(start), end=str(end))

# FX
fx = TSDBSymbol("brl/usd").get_data(start=str(start), end=str(end))

# DI futures (no prefix needed)
di = TSDBSymbol("DIJF26").get_data(start=str(start), end=str(end))
```

**Key rules:**
- `GsSession.use()` must be called once before any `TSDBSymbol` call
- `start`/`end` are date strings `"YYYY-MM-DD"` or `date` objects cast to `str()`
- Returns `pd.Series` indexed by date strings
- Pre-installed in GS environment — no `pip install` needed

### 2. Initialize PySlang (for Slang wrappers / Chunk Store)

Only needed when using `eq1d_brazil__tsdb`, `eq1d_brazil__tsdb_rt`, `query.chunk_query`, or any Slang user function.

```python
import goldmansachs.pyslang as pyslang
pyslang.start(subprocess=True, object_database="Equity")
```

- Use `subprocess=True` in notebooks to avoid memory issues
- Call `pyslang.stop()` before `pyslang.start()` if restarting with different params
- **If pyslang subprocess crashes** (ret_code 255, ConnectionResetError) → fall back to GS Quant TSDBSymbol

### 3. Choose the Right Data Source

- **Quick single-symbol price check** → GS Quant TSDBSymbol (no pyslang)
- **Daily historical prices** → TSDB (`eq1d_brazil__tsdb`) or TSDBSymbol
- **Intraday ticks / real-time** → TSDB RT (`eq1d_brazil__tsdb_rt`)
- **Full tick data with BBO, trade sizes, buyer/seller IDs** → Chunk Store
- **Depth-of-book (5 levels)** → Chunk Store with deep-book symbol (append `m` or `p`)

### 3. Timezone Handling (Chunk Store — CRITICAL)

Start/end times **must** be timezone-aware:

```python
import pytz
local = pytz.timezone("America/Sao_Paulo")
st = local.localize(datetime(2025, 4, 15, 9, 0, 0))
et = local.localize(datetime(2025, 4, 15, 18, 0, 0))
```

Naive datetimes will fail or return wrong data.

### 4. Multi-Day Fetch

Loop through each trading day individually — Chunk Store does not support cross-day ranges well:

```python
for td in trading_days:
    st = local.localize(datetime(td.year, td.month, td.day, 9, 0, 0))
    et = local.localize(datetime(td.year, td.month, td.day, 18, 0, 0))
    df = pd.DataFrame(query.chunk_query([sym], st, et, "Eq", fields=fields))
```

### 5. Post-Process

Always forward-fill fields after fetch (NaN between updates):

```python
for f in fields:
    df[f] = df[f].ffill()
df['Time'] = pd.to_datetime(df['Time'])
```

---

## Symbol Quick Reference

| Asset | L1 Symbol | L2 (Deep) | TSDBSymbol (GS Quant) | Slang TSDB field |
|-------|-----------|-----------|----------------------|------------------|
| BR equity | `PETR4.SA` | `PETR4.SAp` | `eqpad_PETR4.SA@close` | `"close"` |
| BR equity (adj) | — | — | `eqpad_PETR4.SA@close.adj.allincdiv` | `"close.adj.allincdiv"` |
| Mini IBOV future | `WINJ25` | `WINJ25m` | `eqpad_WINJ25@close` | `"close"` |
| Mini Dollar future | `WDOJ25` | `WDOJ25m` | `eqpad_WDOJ25@close` | `"close"` |
| DI futures | `DIJF26` | — | `DIJF26` (no prefix) | `"close"` |
| FX BRL/USD | — | — | `brl/usd` | — |
| CDI rate | — | — | `brl_cdi` | — |

**Month codes:** F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| pyslang subprocess crashes (ret_code 255) | Fall back to GS Quant `TSDBSymbol` — no pyslang needed |
| Naive datetimes in Chunk Store | Always `pytz.localize()` — never pass naive `datetime` |
| Cross-day Chunk Store query | Loop through each trading day individually |
| Missing `pyslang.start()` | Must call before `query.chunk_query()` or Slang imports (not needed for TSDBSymbol) |
| NaN gaps in tick data | Forward-fill all fields after fetch |
| Wrong chunkdb name | Always `"Eq"` for equities, futures, rates |
| Deep-book symbol wrong suffix | Futures: append `m` (e.g. `WINJ25m`). Equities: append `p` (e.g. `PETR4.SAp`) |
| TSDB returns empty | Check symbol format — try `eqpad_` prefix, `_sdb` suffix, or raw code |
| TSDBSymbol returns nothing | Ensure `GsSession.use()` was called; check symbol string format |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| TSDB returns empty | Symbol format mismatch | Check symbol format — try `eqpad_` prefix, `_sdb` suffix, or raw code |
| TSDBSymbol returns nothing | Session not initialized | Ensure `GsSession.use()` was called; check symbol string format |

## Links

- memory/ref/python-tsdb.md — TSDB daily/RT wrappers, TSDBSymbol, field dictionary
- memory/ref/python-chunk.md — Chunk Store tick data, L1/L2, timezone handling
- memory/ref/python-pyslang.md — PySlang setup and imports
