---
created: 2026-04-10
updated: 2026-04-15
tags: [python, tsdb, time-series, market-data, eqpad, TSDBSymbol]
status: active
relates:
  - ref/python-pyslang.md
  - ref/python-chunk.md
---

# TSDB — Time Series Database Reference

TSDB provides daily (end-of-day) and real-time time series data for assets. There are **two access methods**: Slang wrapper functions and the direct `TSDBSymbol` API.

---

## 1. Slang TSDB Wrappers

These are Slang user functions imported after `pyslang.start()`. They return `pd.Series` objects.

### 1.1 Daily TSDB — `eq1d_brazil__tsdb`

Returns a **daily** time series (one value per business day).

```python
from _lib_eq1d_brazil_tsdb_fns import eq1d_brazil__tsdb

daily_data = eq1d_brazil__tsdb(symbol, field, start_date, end_date)
```

| Parameter    | Type           | Description                                          |
| ------------ | -------------- | ---------------------------------------------------- |
| `symbol`     | `str`          | Asset RIC/code, e.g. `"DAPQ40"`, `"DIJF26"`         |
| `field`      | `str`          | Data field: `"close"`, `"open"`, `"high"`, `"low"`, `"volume"` |
| `start_date` | `date`         | Python `date` object — start of range                |
| `end_date`   | `date`         | Python `date` object — end of range                  |

**Returns:** `pd.Series` indexed by date.

```python
from datetime import date, timedelta

daily = eq1d_brazil__tsdb("DAPQ40", "close", date.today() - timedelta(days=7), date.today())
# 2026-04-06   7.2400
# 2026-04-07   7.2650
# 2026-04-08   7.1350
# 2026-04-09   7.1350
# dtype: float64
```

### 1.2 Real-Time TSDB — `eq1d_brazil__tsdb_rt`

Returns **intraday/tick-level** time series from the real-time TSDB.

```python
from _lib_eq1d_brazil_tsdb_fns import eq1d_brazil__tsdb_rt

realtime_data = eq1d_brazil__tsdb_rt(symbol, field, start_datetime, end_datetime)
```

| Parameter         | Type       | Description                                              |
| ----------------- | ---------- | -------------------------------------------------------- |
| `symbol`          | `str`      | Asset RIC/code, e.g. `"DAPQ40"`                         |
| `field`           | `str`      | Data field: `"tick"`, etc.                               |
| `start_datetime`  | `datetime` | Python `datetime` object — start of range                |
| `end_datetime`    | `datetime` | Python `datetime` object — end of range                  |

**Returns:** `pd.Series` indexed by UTC timestamp.

```python
from datetime import datetime, timedelta

rt = eq1d_brazil__tsdb_rt("DAPQ40", "tick", datetime.now() - timedelta(days=7), datetime.now())
# 2026-04-06 12:13:12.404000+00:00   7.2350
# 2026-04-06 18:44:43.394000+00:00   7.2350
# ...
# 2026-04-09 20:57:35.176000+00:00   7.1350
# Length: 139, dtype: float64
```

### 1.3 When to Use Which

| Need                              | Function               |
| --------------------------------- | ---------------------- |
| End-of-day close/open/volume      | `eq1d_brazil__tsdb`    |
| Intraday tick-by-tick             | `eq1d_brazil__tsdb_rt` |
| Full order book + trade details   | Chunk Store (see `python-chunk.md`) |

---

## 2. Direct TSDBSymbol API (GS Quant)

An alternative path via `gs_quant_internal.tsdb`. Requires a GS Quant session.

### 2.1 Setup

```python
from gs_quant.session import GsSession
GsSession.use()
from gs_quant_internal.tsdb import TSDBSymbol
```

### 2.2 Basic Query

```python
data = TSDBSymbol(symbol_string).get_data(start=start_date, end=end_date)
```

**Returns:** `pd.Series` indexed by date strings.

### 2.3 Symbol Naming Conventions

| Pattern                              | Description                                    | Example                               |
| ------------------------------------ | ---------------------------------------------- | ------------------------------------- |
| `eqpad_{RIC}@close`                  | Unadjusted close price                         | `eqpad_PETR4.SA@close`               |
| `eqpad_{RIC}@close.adj.allincdiv`    | Close adjusted for dividends/splits/inplits    | `eqpad_PETR4.SA@close.adj.allincdiv` |
| `eqpad_{RIC}@open`                   | Open price                                     | `eqpad_VALE3.SA@open`                |
| `eqpad_{RIC}@volume`                 | Raw volume                                     | `eqpad_PETR4.SA@volume`              |
| `eqpad_{RIC}@volume.adj.all`         | Adjusted volume                                | `eqpad_PETR4.SA@volume.adj.all`      |
| `{RIC}@CLOSE`                        | Alternative close (used in `lib_intraday_prices`) | `PETR4.SA@CLOSE`                   |
| `{RIC}@VOLUME`                       | Alternative volume                             | `PETR4.SA@VOLUME`                    |
| `{RIC}@RETURN`                       | Returns series                                 | `PETR4.SA@RETURN`                    |
| `{RIC}@HIGH`                         | High price                                     | `PETR4.SA@HIGH`                      |
| `{RIC}@LOW`                          | Low price                                      | `PETR4.SA@LOW`                       |
| `{ticker}_sdb`                       | SecDB futures fallback                         | `WINJ25_sdb`                         |
| `brl_cdi`                            | CDI rate                                       | `brl_cdi`                            |
| `BRL_CDI`                            | CDI rate (× 100)                               | `BRL_CDI`                            |
| `FFTQ`                               | Fed Funds                                      | `FFTQ`                               |
| `eq1d_brazil_onoff@{N}m`             | BRL/USD On/Off spread (tenor in months)        | `eq1d_brazil_onoff@3m`               |
| `eq1d_brazil_sprd@{N}m`              | BRL/USD Spread Over (tenor in months)          | `eq1d_brazil_sprd@1m`                |
| `eq1d_brazil_xccy@{N}m`              | BRL/USD Cross-Currency basis (tenor in months) | `eq1d_brazil_xccy@6m`                |
| `brl/usd`                            | FX rate BRL/USD                                | `brl/usd`                            |
| `mxn/usd`                            | FX rate MXN/USD                                | `mxn/usd`                            |

> **DI futures:** For `DIJ` contracts the TSDB symbol is typically just the code itself (no `@field` suffix needed): `TSDBSymbol("DIJF26").get_data(...)`.

### 2.4 Adjusted vs. Raw Prices

```python
# Adjusted close
adj_close = TSDBSymbol("eqpad_PETR4.SA@close.adj.allincdiv").get_data(start="2025-01-01", end="2025-04-01")

# Raw close
raw_close = TSDBSymbol("eqpad_PETR4.SA@close").get_data(start="2025-01-01", end="2025-04-01")

# Compute adjustment factor
adj_factor = adj_close / raw_close
```

### 2.5 Handling Futures

```python
# Direct futures lookup
close = TSDBSymbol("eqpad_WINJ25@close").get_data(start="2025-01-01", end="2025-04-01")

# Fallback: SecDB naming
close = TSDBSymbol("WINJ25_sdb").get_data(start="2025-01-01", end="2025-04-01")

# Fallback: compressed name (e.g., WINK5 for WINK25)
close = TSDBSymbol("eqpad_WINK5").get_data(start="2025-01-01", end="2025-04-01")
```

---

## 3. Helper Function: `data_curve` (in `pyslang_lib.py`)

A unified wrapper that handles equities, futures, and FX with automatic fallback logic.

```python
from pyslang_lib import data_curve

# Equity close (adjusted)
curve = data_curve("PETR4.SA", "2025-01-01", "2025-04-01", field="close_adj")

# Equity close (raw)
curve = data_curve("PETR4.SA", "2025-01-01", "2025-04-01", field="close_raw")

# Futures
curve = data_curve("WINJ25", "2025-01-01", "2025-04-01", field="close_raw")

# FX
curve = data_curve("brl/usd", "2025-01-01", "2025-04-01")

# DI futures (no field suffix needed)
curve = data_curve("DIJF26", "2025-01-01", "2025-04-01")
```

Allowed `field` values: `"close_adj"`, `"close_raw"`, `"open_adj"`, `"open_raw"`, `"volume_adj"`, `"volume_raw"`.

---

## 4. Field Dictionary

All fields below are the `Field` argument passed to the Slang TSDB functions. The symbol resolved internally is `eqpad_<Ticker>@<Field>`.

Fields are grouped by category. The **Data Mode** column indicates which function to use:

| Data Mode | Function | Return Type | When to Use |
|---|---|---|---|
| **Daily** | `eq1d_brazil__tsdb` | `pd.Series` (Curve) | End-of-day values, historical series over date ranges |
| **RT** | `eq1d_brazil__tsdb_rt` | `pd.Series` (RTCurve) | Intraday / real-time values over time ranges within a day |

---

### Price — Close

| Field | Description | Data Mode |
|---|---|---|
| `close` | Raw closing price (unadjusted) | Daily |
| `close.adj` | Closing price adjusted for corporate actions | Daily |
| `close.adj.all` | Fully adjusted close (splits, dividends, capital changes) | Daily |
| `close.adj.all.pershare` | Fully adjusted close per share | Daily |
| `close.adj.all.rfactor` | Adjusted close using ratio factor | Daily |
| `close.adj.all.rfactor.usd` | Adjusted close ratio factor in USD | Daily |
| `close.adj.all.usd` | Fully adjusted close in USD | Daily |
| `close.adj.allexrcxdiv` | Adjusted close excluding recent ex-dividend | Daily |
| `close.adj.allexrcxdiv.usd` | Adjusted close (ex-div) in USD | Daily |
| `close.adj.allincdiv` | Adjusted close including reinvested dividends | Daily |
| `close.adj.allincdiv.usd` | Adjusted close (inc-div) in USD | Daily |
| `close.adj.fx` | Closing price adjusted for FX | Daily |
| `close.adj.split` | Closing price adjusted for splits only | Daily |
| `close.source` | Data source identifier for close | Daily |
| `close.update.date` | Last update date for close | Daily |
| `close.update.time` | Last update time for close | Daily |
| `close.usd` | Raw closing price in USD | Daily |
| `adjclose` | Adjusted closing price (splits + dividends) | Daily |

### Price — Open

| Field | Description | Data Mode |
|---|---|---|
| `open` | Raw daily opening price | Daily |
| `open.adj` | Adjusted daily opening price | Daily |
| `open.adj.all` | Fully adjusted opening price | Daily |
| `open.adj.all.pershare` | Fully adjusted open per share | Daily |
| `open.adj.all.rfactor` | Adjusted open using ratio factor | Daily |
| `open.adj.all.rfactor.usd` | Adjusted open ratio factor in USD | Daily |
| `open.adj.all.usd` | Fully adjusted open in USD | Daily |
| `open.adj.allexrcxdiv` | Adjusted open excluding ex-dividend | Daily |
| `open.adj.fx` | Opening price adjusted for FX | Daily |
| `open.adj.split` | Opening price adjusted for splits only | Daily |
| `open.source` | Data source for open | Daily |
| `open.update.date` | Last update date for open | Daily |
| `open.update.time` | Last update time for open | Daily |
| `open.usd` | Raw opening price in USD | Daily |
| `adjopen` | Adjusted opening price | Daily |

### Price — High

| Field | Description | Data Mode |
|---|---|---|
| `high` | Raw daily high price | Daily |
| `high.adj` | Adjusted daily high price | Daily |
| `high.adj.all` | Fully adjusted daily high | Daily |
| `high.adj.all.pershare` | Fully adjusted high per share | Daily |
| `high.adj.all.rfactor` | Adjusted high using ratio factor | Daily |
| `high.adj.all.rfactor.usd` | Adjusted high ratio factor in USD | Daily |
| `high.adj.all.usd` | Fully adjusted high in USD | Daily |
| `high.adj.allexrcxdiv` | Adjusted high excluding ex-dividend | Daily |
| `high.adj.fx` | High price adjusted for FX | Daily |
| `high.adj.split` | High adjusted for splits only | Daily |
| `high.source` | Data source for high | Daily |
| `high.update.date` | Last update date for high | Daily |
| `high.update.time` | Last update time for high | Daily |
| `high.usd` | Raw high in USD | Daily |
| `adjhigh` | Adjusted daily high price | Daily |

### Price — Low

| Field | Description | Data Mode |
|---|---|---|
| `low` | Raw daily low price | Daily |
| `low.adj` | Adjusted daily low price | Daily |
| `low.adj.all` | Fully adjusted daily low | Daily |
| `low.adj.all.pershare` | Fully adjusted low per share | Daily |
| `low.adj.all.rfactor` | Adjusted low using ratio factor | Daily |
| `low.adj.all.rfactor.usd` | Adjusted low ratio factor in USD | Daily |
| `low.adj.all.usd` | Fully adjusted low in USD | Daily |
| `low.adj.allexrcxdiv` | Adjusted low excluding ex-dividend | Daily |
| `low.adj.fx` | Low price adjusted for FX | Daily |
| `low.adj.split` | Low adjusted for splits only | Daily |
| `low.source` | Data source for low | Daily |
| `low.update.date` | Last update date for low | Daily |
| `low.update.time` | Last update time for low | Daily |
| `low.usd` | Raw low in USD | Daily |
| `adjlow` | Adjusted daily low price | Daily |

### HLOC Composite

| Field | Description | Data Mode |
|---|---|---|
| `hloc` | High, Low, Open, Close composite dataset | Daily |
| `hloc.usd` | HLOC dataset in USD | Daily |

### Volume

| Field | Description | Data Mode |
|---|---|---|
| `volume` | Raw trading volume | Daily |
| `volume.adj` | Adjusted trading volume | Daily |
| `volume.adj.all` | Fully adjusted volume | Daily |
| `volume.adj.all.pershare` | Fully adjusted volume per share | Daily |
| `volume.adj.all.rfactor` | Adjusted volume using ratio factor | Daily |
| `volume.adj.split` | Volume adjusted for splits only | Daily |
| `volume.source` | Data source for volume | Daily |
| `volume.update.date` | Last update date for volume | Daily |
| `volume.update.time` | Last update time for volume | Daily |
| `adjvolume` | Trading volume adjusted for splits | Daily |
| `volall` | Total volume across all venues | Daily |
| `volalladj` | Adjusted total volume across all venues | Daily |

### Returns

| Field | Description | Data Mode |
|---|---|---|
| `return` | Total return | Daily |
| `return.log` | Logarithmic return | Daily |
| `return.log.usd` | Log return in USD | Daily |
| `return.simple.usd` | Simple return in USD | Daily |

### Dividends

| Field | Description | Data Mode |
|---|---|---|
| `div` | Dividend amount per share | Daily |
| `div.adj.all` | Fully adjusted dividend | Daily |
| `div.adj.all.usd` | Fully adjusted dividend in USD | Daily |
| `div.gross` | Gross dividend (before tax) | Daily |
| `div.gross.adj.all` | Fully adjusted gross dividend | Daily |
| `div.gross.adj.all.usd` | Fully adjusted gross dividend in USD | Daily |
| `div.net` | Net dividend (after tax) | Daily |
| `div.taxrate` | Applicable dividend tax rate | Daily |

### Earnings

| Field | Description | Data Mode |
|---|---|---|
| `eps` | Earnings Per Share | Daily |
| `eps.adj` | Adjusted EPS | Daily |
| `eps.adj.split` | EPS adjusted for splits | Daily |

### Shares & Market Cap

| Field | Description | Data Mode |
|---|---|---|
| `shares.float` | Shares available for public trading (float) | Daily |
| `shares.outstanding` | Total shares outstanding | Daily |
| `shares.outstanding_mult_class` | Shares outstanding across multiple classes | Daily |
| `shares.outstanding_real` | Actual shares outstanding (verified) | Daily |
| `shares.raw.float` | Unprocessed float shares | Daily |
| `shares.raw.outstanding` | Unprocessed total shares outstanding | Daily |
| `shares.raw.outstanding_mult_clas` | Unprocessed multi-class shares outstanding | Daily |
| `shares.raw.outstanding_real` | Unprocessed actual shares outstanding | Daily |
| `shrout` | Shares outstanding (standard) | Daily |
| `rawshrout` | Unprocessed shares outstanding | Daily |
| `mktcap` | Market capitalization | Daily |
| `curmktcap` | Current market capitalization | Daily |
| `nav` | Net Asset Value | Daily |

### Fund Data

| Field | Description | Data Mode |
|---|---|---|
| `fund_class_assets` | Total assets for a fund class | Daily |
| `fund_total_assets` | Total AUM for the fund | Daily |

### FX & USD Rates

| Field | Description | Data Mode |
|---|---|---|
| `fx` | Foreign exchange rate for conversion | Daily |
| `fxadj` | FX adjustment factor | Daily |
| `db_usdrate` | Database-stored USD exchange rate | Daily |
| `usdrate` | Current USD exchange rate | Daily |

### Corporate Actions & Adjustments

| Field | Description | Data Mode |
|---|---|---|
| `split` | Stock split ratio | Daily |
| `splitadj` | Adjusted split ratio | Daily |
| `spin` | Spinoff adjustment factor | Daily |
| `spinadj` | Adjusted spinoff factor | Daily |
| `spec` | Special corporate action factor | Daily |
| `specadj` | Adjusted special corporate action factor | Daily |
| `rts` | Rights to subscribe | Daily |
| `rtsadj` | Adjusted rights to subscribe | Daily |
| `rcxdiv` | Recent capital/dividend change factor | Daily |
| `rcxdivadj` | Adjusted recent capital/dividend change factor | Daily |
| `rfact_padj` | Price adjustment ratio factor | Daily |
| `rfact_vadj` | Volume adjustment ratio factor | Daily |

### Short Interest

| Field | Description | Data Mode |
|---|---|---|
| `shortint` | Short interest (shares shorted) | Daily |
| `shortint.adj.all` | Fully adjusted short interest | Daily |
| `shortint.adj.split` | Short interest adjusted for splits | Daily |

### Composite / Derived Price

| Field | Description | Data Mode |
|---|---|---|
| `prca_ex_rcxd` | Price excluding recent capital/dividend changes | Daily |
| `prca_ex_rcxdadj` | Adjusted price excluding recent capital changes | Daily |
| `prca_inc_divadj` | Adjusted price including dividends | Daily |
| `prcall` | All-inclusive price | Daily |
| `prcalladj` | Adjusted all-inclusive price | Daily |
| `quote` | Current market quote | Daily |
| `quoteadj` | Adjusted market quote | Daily |
| `quotelots` | Standard lot size for quotes | Daily |

### Settlement & Open Interest

| Field | Description | Data Mode |
|---|---|---|
| `settle` | Settlement price | Daily |
| `settle.source` | Data source for settlement | Daily |
| `settle.update.date` | Last settlement update date | Daily |
| `settle.update.time` | Last settlement update time | Daily |
| `settlement_date` | Official settlement date | Daily |
| `openint` | Open interest (derivatives) | Daily |
| `openint.source` | Data source for open interest | Daily |
| `openint.update.date` | Last open interest update date | Daily |
| `openint.update.time` | Last open interest update time | Daily |

### Calendar & Trading Days

| Field | Description | Data Mode |
|---|---|---|
| `holidays` | Market holiday schedule | Daily |
| `rawholidays` | Unprocessed holiday data | Daily |
| `rawnontradedays` | Unprocessed non-trading day data | Daily |
| `tradedays` | Number of trading days in the period | Daily |
| `tradedays.exholidays` | Trading days excluding holidays | Daily |

### Index Fundamentals

| Field | Description | Data Mode |
|---|---|---|
| `index.bookval` | Index-level book value | Daily |
| `index.div.points` | Dividend points in the index | Daily |
| `index.div.yield` | Index dividend yield | Daily |
| `index.eps` | Index-level EPS | Daily |
| `index.eps.before_xo` | Index EPS before extraordinary items | Daily |
| `index.eps.est` | Estimated index EPS | Daily |
| `index.ratio.pe` | Index P/E ratio | Daily |
| `index.ratio.pe.est` | Estimated index P/E | Daily |
| `index.ratio.pos_pe` | Positive P/E (excluding loss-makers) | Daily |
| `index.ratio.pos_pe.est` | Estimated positive P/E | Daily |
| `index.ratio.sales` | Index Price-to-Sales ratio | Daily |
| `index.volume.advc` | Index advancing volume | Daily |
| `index.volume.decl` | Index declining volume | Daily |
| `index.volume.unch` | Index unchanged volume | Daily |

---

### Intraday Aggregated (`td.`) — Real-Time Only

These fields aggregate tick data over a time window. **Use `eq1d_brazil__tsdb_rt` only.**

| Field | Description | Data Mode |
|---|---|---|
| `td.ask` | Current ask price (tick data) | **RT** |
| `td.asksize` | Current ask size (tick data) | **RT** |
| `td.bid` | Current bid price (tick data) | **RT** |
| `td.bidsize` | Current bid size (tick data) | **RT** |
| `td.numticks` | Number of ticks in the period | **RT** |
| `td.numticks.orderbook` | Number of order book ticks | **RT** |
| `td.numticks.pp` | Number of price-point ticks | **RT** |
| `td.spread` | Bid-ask spread (tick data) | **RT** |
| `td.vol` | Tick-level volume | **RT** |
| `td.volume.auction` | Volume traded during auction phases | **RT** |
| `td.volume.auction.close` | Closing auction volume | **RT** |
| `td.volume.auction.open` | Opening auction volume | **RT** |
| `td.volume.orderbook` | Volume traded via order book | **RT** |
| `td.volume.pp` | Volume at specific price points | **RT** |
| `td.vwap` | Volume Weighted Average Price (VWAP) | **RT** |
| `td.vwap.pp` | VWAP at specific price points | **RT** |
| `td.vwstdevp` | Standard deviation of VWAP | **RT** |
| `td.vwstdevp.pp` | Std dev of VWAP at price points | **RT** |

### Tick-by-Tick (`tick.`) — Real-Time Only

Individual tick-level prices. **Use `eq1d_brazil__tsdb_rt` only.**

| Field | Description | Data Mode |
|---|---|---|
| `tick` | Individual tick price (generic) | **RT** |
| `tick.ask` | Individual tick ask price | **RT** |
| `tick.bid` | Individual tick bid price | **RT** |
| `tick.trd` | Individual tick trade price | **RT** |

---

## 5. Quick Reference

```python
# ── Daily close via Slang wrapper ─────────────────────────────────────────
from _lib_eq1d_brazil_tsdb_fns import eq1d_brazil__tsdb
daily = eq1d_brazil__tsdb("DAPQ40", "close", date.today() - timedelta(days=30), date.today())

# ── Real-time ticks via Slang wrapper ─────────────────────────────────────
from _lib_eq1d_brazil_tsdb_fns import eq1d_brazil__tsdb_rt
ticks = eq1d_brazil__tsdb_rt("DAPQ40", "tick", datetime.now() - timedelta(days=7), datetime.now())

# ── Daily close via TSDBSymbol ────────────────────────────────────────────
from gs_quant_internal.tsdb import TSDBSymbol
close = TSDBSymbol("eqpad_PETR4.SA@close").get_data(start="2025-01-01", end="2025-04-01")

# ── CDI rate via TSDBSymbol ───────────────────────────────────────────────
cdi = TSDBSymbol("BRL_CDI").get_data(start="2025-01-01", end="2025-04-01") * 100
```
