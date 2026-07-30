---
created: 2026-04-10
updated: 2026-07-29
tags: [python, tsdb, time-series, market-data, eqpad, TSDBSymbol]
status: active
relates:
  - ref/python-pyslang.md
  - ref/python-chunk.md
  - ref/python-tsdb-fields.md
---

# TSDB — Time Series Database Reference

Daily EOD and real-time series for the 34-symbol US universe. Two access
paths:

1. **`TSDBSymbol`** (`gs_quant_internal.tsdb`) — the path used everywhere in
   `src/volforecast/data/tsdb.py`. Requires an active `GsSession`.
2. **Slang wrappers** — thin Python fns bound after `pyslang.start()`; legacy
   path, kept here for shape reference only.

> Full field/dataset dictionary: `memory/ref/python-tsdb-fields.md`
> (P2 — load on lookup only).

---

## 1. TSDBSymbol (GS Quant) — primary path

### 1.1 Setup

```python
from gs_quant.session import GsSession
from gs_quant_internal.tsdb import TSDBSymbol

GsSession.use()   # thread-safe wrapper in tsdb.py: _ensure_session()
```

### 1.2 Basic query

```python
close = TSDBSymbol("eqpad_SPY@close").get_data(start="2025-01-01", end="2025-04-01")
```

Returns a `pd.Series` indexed by date strings (parse with `pd.DatetimeIndex`).

### 1.3 Symbol naming — US universe

| Pattern | Example | Notes |
|---|---|---|
| `eqpad_{RIC}@close` | `eqpad_SPY@close` | Raw close |
| `eqpad_{RIC}@close.adj.allincdiv` | `eqpad_AAPL.OQ@close.adj.allincdiv` | Splits + dividends |
| `eqpad_{RIC}@{open\|high\|low}[.adj.allincdiv]` | `eqpad_MSFT.OQ@high.adj.allincdiv` | OHLC family |
| `eqpad_{RIC}@volume` | `eqpad_SPY@volume` | Always unadjusted |
| `eqpad_.{INDEX}@{field}` | `eqpad_.SPX@close`, `eqpad_.VIX@close` | Leading `.` for indices |
| `eqpad_{FUT_CODE}@settle` | `eqpad_CLM26@settle`, `eqpad_VXH26@settle` | Front-month futures |
| `eqpad_{RIC}@close` | `eqpad_US10YT=RR@close` | Treasury RICs |
| `eqpad_usd/{ccy}@close` | `eqpad_usd/jpy@close` | FX pairs (CME convention) |

**RIC mapping (34 US symbols):** `TICKER_TO_RIC` in `volforecast/constants.py`:

- NASDAQ names → `.OQ` suffix (e.g. `AAPL.OQ`, `MSFT.OQ`).
- NYSE names → `.N` suffix (e.g. `JPM.N`, `BAC.N`; `BRK.B` → `BRKb.N`).
- ETFs (`SPY`, `QQQ`, `IWM`, `DIA`) and indices (`.SPX`, `.VIX`) are bare.
- E-mini S&P 500 (`ES`) uses quarterly contracts (see `python-chunk.md`).

> **CME FX quirk:** Marquee only carries the CME-convention leg. Use
> `eqpad_usd/jpy@close` for USD/JPY, and **`eqpad_usd/eur@close` for EUR/USD**
> — invert the returned series if you need the direct EUR→USD quote. See
> `_PAIR_TO_TSDB` in `src/volforecast/data/tsdb.py`.

### 1.4 Adjusted vs raw close

```python
adj = TSDBSymbol("eqpad_SPY@close.adj.allincdiv").get_data(start=s, end=e)
raw = TSDBSymbol("eqpad_SPY@close").get_data(start=s, end=e)
adj_factor = adj / raw     # per-day corporate-action factor
```

### 1.5 Futures — settle prices

Generic front-month tickers (`CLv1`, `GCv1`) **do not work** in TSDB. Resolve
the exact contract using CME month codes `FGHJKMNQUVXZ`:

```python
# CL front-month for 2026-06 → CLM26
cl = TSDBSymbol("eqpad_CLM26@settle").get_data(start=s, end=e)
```

`_resolve_front_contract(commodity, ref_date)` in `tsdb.py` does this
automatically; `_resolve_vx_contracts(ref_date, n=3)` returns the VX1/VX2/VX3
chain used by `fetch_vix_futures`.

---

## 2. Slang TSDB wrappers (legacy — bind after `pyslang.start()`)

Two shape-only functions returning `pd.Series`. The project no longer imports
them (all daily data flows through `TSDBSymbol`), but they still work if the
Slang library that defines them is loaded.

### 2.1 Daily — `<daily_tsdb_fn>`

```python
daily = tsdb_fn(symbol, field, start_date, end_date)   # date, date
# 2026-04-06  557.20
# 2026-04-07  560.15
# dtype: float64
```

Use for close/open/volume series (one point per business day).

### 2.2 Real-time — `<realtime_tsdb_fn>`

```python
rt = tsdb_fn_rt(symbol, field, start_datetime, end_datetime)   # tz-aware
# 2026-04-06 13:30:00.400000+00:00  557.10
# 2026-04-06 13:30:00.800000+00:00  557.15
# dtype: float64
```

Use for tick-level or aggregated intraday (`td.` / `tick.` field families —
see `python-tsdb-fields.md`). Full order book + trade sides → Chunk Store
(`python-chunk.md`).

---

## 3. Real project call patterns (`src/volforecast/data/tsdb.py`)

`_get_tsdb_data(symbol, start, end)` wraps `TSDBSymbol(...).get_data()` with:

- Thread-safe `_ensure_session()` — a double-checked lock around
  `GsSession.use()` guards against a concurrent init corrupting the base URL.
- One-shot retry on `MqUninitialisedError` after re-initializing.

Public fetchers:

| Function | TSDB symbol shape | Returns |
|---|---|---|
| `fetch_daily_ohlcv(symbols, start, end, adjusted=True)` | `eqpad_{RIC}@{field}[.adj.allincdiv]` | `pd.DataFrame`, MultiIndex `(date, symbol)`, columns `OHLCV_FIELDS` |
| `fetch_treasury_yields(start, end, tenors)` | `eqpad_US{2,5,10,30}YT=RR@close` | `pd.DataFrame` — bond **prices**, not yield % |
| `fetch_fx_rates(start, end, pairs)` | `eqpad_usd/{jpy,eur}@close` | `pd.DataFrame`, CME convention |
| `fetch_commodity_prices(start, end, symbols)` | `eqpad_{CL\|GC}{code}{YY}@settle` | Front-month settle; range midpoint resolves the contract |
| `fetch_vix(start, end)` | `eqpad_.VIX@close` | `pd.Series`, name `"vix"` |
| `fetch_vix_futures(start, end, n=3)` | `eqpad_VX{code}{YY}@settle` × n | `pd.DataFrame`, cols `VX1..VXn` |
| `fetch_spx_index(start, end, fields)` | `eqpad_.SPX@{field}` | `pd.DataFrame`, cols = requested fields |

`OHLCV_FIELDS` order: `["open", "high", "low", "close", "volume"]`.

Gotchas:

- **All symbols validated up front** against `SYMBOL_UNIVERSE` (34 US names).
  Adding a name means editing `EQUITY_SYMBOLS` in `constants.py`.
- **Volume is never adjusted** — `_PRICE_FIELDS = {"open","high","low","close"}`
  gates the `.adj.allincdiv` suffix in `_tsdb_symbol`.
- **Treasury columns are prices**, not yield percentages. Downstream code
  computes yields from these.
- **Commodity roll boundaries:** ranges spanning a roll must be split by the
  caller; `fetch_commodity_prices` resolves one contract per call, using the
  range midpoint.

---

## 4. Marquee ERDVOL — IV surface (SPX)

Options-implied features use the Marquee **`ERDVOL_PERCENT_STANDARD`** dataset
(see `memory/research/data-access.md` for the tenor / strike grid and history
trade-offs against its longer-history sibling). Access is via
`gs_quant.data.Dataset`, not `TSDBSymbol`:

```python
from gs_quant.data import Dataset
df = Dataset("ERDVOL_PERCENT_STANDARD").get_data(start=s, end=e, bbid="SPX")
```

Rate limit is roughly one month per call. Filter to
`strikeReference="forward"` before using ATM IV (there are three rows per
tenor / day otherwise, one per `strikeReference`).

---

## 5. Quick reference

```python
# Daily close via TSDBSymbol (project path)
close = TSDBSymbol("eqpad_SPY@close.adj.allincdiv").get_data(start=s, end=e)

# SPX index OHLC
spx = TSDBSymbol("eqpad_.SPX@close").get_data(start=s, end=e)

# VIX + VIX futures
vix = TSDBSymbol("eqpad_.VIX@close").get_data(start=s, end=e)
vx1 = TSDBSymbol("eqpad_VXM26@settle").get_data(start=s, end=e)

# Treasury 10y (price, not yield)
t10 = TSDBSymbol("eqpad_US10YT=RR@close").get_data(start=s, end=e)

# FX (CME convention — invert EUR/USD if you need the direct quote)
usdjpy = TSDBSymbol("eqpad_usd/jpy@close").get_data(start=s, end=e)

# Front-month WTI settle for 2026-06 (contract midpoint = CLM26)
cl = TSDBSymbol("eqpad_CLM26@settle").get_data(start=s, end=e)
```

Field / dataset lookups → `memory/ref/python-tsdb-fields.md`.
