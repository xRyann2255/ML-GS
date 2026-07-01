# Data Audit: S&P 500 RV Forecasting

> **Purpose:** Single source of truth for every data element needed by the ML vol forecasting pipeline. Organized by feature layer (L0-L6) so an LLM or developer can look up "what raw data does feature X need?" and get a runnable query snippet.
>
> **Last validated:** 2026-05-18 (probe script: `workspace/tmp/sp500_data_probe.py`, 147/206 checks passed; Layer 2 verified via live TSDB + Marquee Dataset API probes)

---

## Quick Navigation

| Section | What it covers |
|---------|---------------|
| [1. Environment Setup](#1-environment-setup) | Session init boilerplate (pyslang, GsSession, pytickclient) |
| [2. Universe](#2-universe) | 34 symbols, RIC conventions, tick counts |
| [3. Layer 0 -- HAR Core](#3-layer-0--har-core--measurement-quality) | RV, RQ from tick data |
| [4. Layer 1 -- Asymmetry](#4-layer-1--asymmetric-volatility) | Semivariances, BPV, jumps |
| [5. Layer 2 -- Options](#5-layer-2--options-implied-spx-only) | IV surface, VRP, VIX term structure |
| [6. Layer 3 -- Microstructure](#6-layer-3--microstructure) | L1 spread, L2 depth, OBI, VPIN |
| [7. Layer 4 -- Cross-Asset](#7-layer-4--cross-asset-spillovers) | Treasuries, FX, commodities |
| [8. Layer 5 -- Calendar](#8-layer-5--calendar--events) | FOMC, NFP, OpEx, earnings |
| [9. Layer 6 -- Long Memory](#9-layer-6--long-memory--roughness) | Frac-diff, Hurst, vol-of-vol |
| [10. Data Gaps](#10-data-gaps--workarounds) | What's missing and alternatives |

---

## 1. Environment Setup

Every query in this doc assumes this session boilerplate has been run first.

### 1.1 Notebook / Script Preamble

```python
# --- Session init (run once per Python process) ---
import goldmansachs.pyslang as pyslang
pyslang.start(subprocess=True, object_database="Equity")

from gs_quant.session import GsSession
GsSession.use()  # kerberos auth via gs_quant_internal

# --- Standard imports ---
import numpy as np
import pandas as pd
import pytz
from datetime import date, datetime

TZ = pytz.timezone("America/New_York")
```

### 1.2 Chunk Store Import

```python
from pytickclient import query

CHUNKDB = "Eq"
L1_FIELDS = ["TRDPRC_1", "TRDVOL_1", "ASK", "BID", "ASKSIZE", "BIDSIZE"]
```

### 1.3 TSDB Import (Slang Wrapper)

```python
from _lib_eq1d_brazil_tsdb_fns import eq1d_brazil__tsdb, eq1d_brazil__tsdb_rt
```

### 1.4 TSDB Import (GS Quant -- No PySlang Needed)

```python
from gs_quant_internal.tsdb import TSDBSymbol
# GsSession.use() must be called first
```

### 1.5 Marquee Import

```python
from gs_quant.data import Dataset
# GsSession.use() must be called first
```

### 1.6 volforecast Module Imports

```python
from volforecast.data.chunk_store import fetch_trades, fetch_quotes, fetch_depth
from volforecast.data.resample import resample_trades_to_bars, compute_daily_rv_from_ticks
from volforecast.data.tsdb import fetch_daily_ohlcv, fetch_treasury_yields, fetch_fx_rates, fetch_commodity_prices
from volforecast.data.marquee import fetch_iv_surface, fetch_atm_iv, fetch_skew, fetch_vvix
```

---

## 2. Universe

### 2.1 Core Equities (30 names)

| # | Company | RIC | Exchange | Ticks/15min |
|---|---------|-----|----------|-------------|
| 1 | Apple | AAPL.OQ | NASDAQ | 104,353 |
| 2 | Microsoft | MSFT.OQ | NASDAQ | 54,860 |
| 3 | NVIDIA | NVDA.OQ | NASDAQ | 164,929 |
| 4 | Amazon | AMZN.OQ | NASDAQ | 90,220 |
| 5 | Meta | META.OQ | NASDAQ | 30,819 |
| 6 | Alphabet A | GOOGL.OQ | NASDAQ | 105,153 |
| 7 | Alphabet C | GOOG.OQ | NASDAQ | 66,217 |
| 8 | Berkshire B | BRKb.N | NYSE | 2,530 |
| 9 | Broadcom | AVGO.OQ | NASDAQ | 20,539 |
| 10 | Eli Lilly | LLY.N | NYSE | 2,759 |
| 11 | JPMorgan | JPM.N | NYSE | 4,989 |
| 12 | Tesla | TSLA.OQ | NASDAQ | 88,286 |
| 13 | UnitedHealth | UNH.N | NYSE | 4,079 |
| 14 | Visa | V.N | NYSE | 4,621 |
| 15 | Exxon Mobil | XOM.N | NYSE | 5,134 |
| 16 | Mastercard | MA.N | NYSE | 3,183 |
| 17 | Procter & Gamble | PG.N | NYSE | 3,930 |
| 18 | Costco | COST.OQ | NASDAQ | 3,777 |
| 19 | Johnson & Johnson | JNJ.N | NYSE | 1,209 |
| 20 | Home Depot | HD.N | NYSE | 3,819 |
| 21 | Walmart | WMT.N | NYSE | 7,353 |
| 22 | AbbVie | ABBV.N | NYSE | 679 |
| 23 | Netflix | NFLX.OQ | NASDAQ | 38,029 |
| 24 | Bank of America | BAC.N | NYSE | 14,232 |
| 25 | Salesforce | CRM.N | NYSE | 3,329 |
| 26 | Adobe | ADBE.OQ | NASDAQ | 7,521 |
| 27 | AMD | AMD.OQ | NASDAQ | 67,142 |
| 28 | Chevron | CVX.N | NYSE | 4,879 |
| 29 | Merck | MRK.N | NYSE | 1,391 |
| 30 | Coca-Cola | KO.N | NYSE | 9,978 |

### 2.2 ETFs

| ETF | RIC | Ticks/15min |
|-----|-----|-------------|
| SPY (S&P 500) | SPY.P | 281,557 |
| QQQ (Nasdaq-100) | QQQ.P | 233,757 |
| IWM (Russell 2000) | IWM.P | 162,329 |
| DIA (Dow Jones) | DIA.P | 73,616 |

### 2.3 Futures

| Contract | RIC | Ticks/15min | L2 Depth |
|----------|-----|-------------|----------|
| E-mini S&P (front) | ESM26 | 6,764,223 (full day) | 488,646 ticks |
| E-mini Nasdaq | NQM26 | 666,529 | -- |
| VIX Front | VXM26 | 10,398 | -- |
| VIX 2nd | VXN26 | 3,886 | -- |
| VIX 3rd | VXQ26 | 2,563 | -- |
| WTI Crude | CLM26 | 56,033 | -- |
| Gold | GCM26 | 44,678 | -- |
| 10Y T-Note | TYM26 | 105,639 | -- |

### 2.4 Indices (TSDB daily only)

| Index | TSDB Symbol | Last Value |
|-------|-------------|------------|
| S&P 500 | `eqpad_.SPX@close` | 7,200.75 |
| VIX | `eqpad_.VIX@close` | 18.29 |
| Russell 2000 | `eqpad_.RUT@close` | 2,796.00 |

### 2.5 RIC Naming Rules

| Exchange | Pattern | Example | Notes |
|----------|---------|---------|-------|
| NASDAQ | `TICKER.OQ` | `AAPL.OQ` | `.O` also works |
| NYSE | `TICKER.N` | `JPM.N` | Bare `JPM` also works |
| Arca | `TICKER.P` | `SPY.P` | Bare `SPY` also works |
| CME futures | `XXMYY` | `ESM26` | Month code + 2-digit year |
| E-mini L2 | `XXMYY` + `m` | `ESM26m` | Append `m` for depth-of-book |
| NASDAQ bare | `AAPL` | -- | **Does NOT work** (returns empty) |

---

## 3. Layer 0 -- HAR Core + Measurement Quality

| Feature | Raw Data | Source | Module | Status |
|---------|----------|--------|--------|--------|
| `log_rv_d` | 5-min returns from L1 ticks | Chunk Store | `features/har.py` | Implemented |
| `log_rv_w` | Rolling 5-day mean of daily RV | (derived from `log_rv_d`) | `features/har.py` | Implemented |
| `log_rv_m` | Rolling 22-day mean of daily RV | (derived from `log_rv_d`) | `features/har.py` | Implemented |
| `rq` | 5-min returns | Chunk Store | `features/har.py` | Implemented |
| `rq_interaction` | sqrt(RQ) x RV_d | (derived) | `features/har.py` | Implemented |

### Query: Fetch L1 Trade Ticks (Single Day)

```python
from pytickclient import query
import pytz
from datetime import datetime

TZ = pytz.timezone("America/New_York")
CHUNKDB = "Eq"
L1_FIELDS = ["TRDPRC_1", "TRDVOL_1", "ASK", "BID", "ASKSIZE", "BIDSIZE"]

st = TZ.localize(datetime(2026, 5, 4, 9, 30, 0))
et = TZ.localize(datetime(2026, 5, 4, 16, 0, 0))

raw = query.chunk_query(["AAPL.OQ"], st, et, CHUNKDB, fields=L1_FIELDS)
df = pd.DataFrame(raw)
# Shape: ~100K rows x 7 cols (Time, TRDPRC_1, TRDVOL_1, ASK, BID, ASKSIZE, BIDSIZE)
```

### Query: Fetch L1 Trade Ticks (volforecast Wrapper)

```python
from volforecast.data.chunk_store import fetch_trades
from datetime import date

trades = fetch_trades("AAPL", date(2026, 5, 4), date(2026, 5, 4))
# Returns: DataFrame with columns [price, size], tz-aware DatetimeIndex
# Shape: ~100K rows
```

### Query: Resample Ticks to 5-min Bars

```python
from volforecast.data.resample import resample_trades_to_bars

bars = resample_trades_to_bars(trades, freq="5min")
# Returns: DataFrame with columns [price, log_return], DatetimeIndex at 5-min intervals
# Shape: 78 rows (6.5 hours / 5 min)
```

### Query: Compute All Daily RV Measures (End-to-End)

```python
from volforecast.data.chunk_store import fetch_trades
from volforecast.data.resample import compute_daily_rv_from_ticks
from datetime import date

trades = fetch_trades("AAPL", date(2026, 5, 4), date(2026, 5, 4))
measures = compute_daily_rv_from_ticks(trades)
# Returns dict with keys:
#   rv, log_rv, rq, bpv, rs_positive, rs_negative,
#   jump_stat, jump_indicator, continuous_variation, jump_variation,
#   rk, noise_gap, n_ticks, n_bars
```

### Query: Multi-Day RV Panel (Loop Pattern)

```python
from volforecast.data.chunk_store import fetch_trades
from volforecast.data.resample import compute_daily_rv_from_ticks
from datetime import date, timedelta
import exchange_calendars as xcals

nyse = xcals.get_calendar("XNYS")
sessions = nyse.sessions_in_range("2026-01-02", "2026-05-04")

records = []
for session in sessions:
    d = session.date()
    trades = fetch_trades("AAPL", d, d)
    if trades.empty:
        continue
    measures = compute_daily_rv_from_ticks(trades)
    measures["date"] = d
    records.append(measures)

daily = pd.DataFrame(records).set_index("date")
# Shape: ~84 rows x 14 cols (one row per trading day)
```

### Query: TSDB Daily OHLCV (Slang Wrapper)

```python
from _lib_eq1d_brazil_tsdb_fns import eq1d_brazil__tsdb
from datetime import date

close = eq1d_brazil__tsdb("AAPL.OQ", "close", date(2015, 1, 2), date(2026, 5, 4))
# Returns: pd.Series, ~2,850 points (11.3 years)

volume = eq1d_brazil__tsdb("AAPL.OQ", "volume", date(2015, 1, 2), date(2026, 5, 4))
log_ret = eq1d_brazil__tsdb("AAPL.OQ", "return.log", date(2015, 1, 2), date(2026, 5, 4))
```

### Query: TSDB Daily OHLCV (TSDBSymbol -- No PySlang)

```python
from gs_quant.session import GsSession
GsSession.use()
from gs_quant_internal.tsdb import TSDBSymbol

data = TSDBSymbol("eqpad_AAPL.OQ@close.adj.allincdiv").get_data(
    start="2015-01-02", end="2026-05-04"
)
# Returns: pd.Series indexed by date strings
```

**Available TSDB daily fields:**

| Field | Description | Confirmed |
|-------|-------------|-----------|
| `close` | Unadjusted close | Yes |
| `close.adj.allincdiv` | Fully adjusted close | Yes |
| `open` | Open | Yes |
| `high` | High | Yes |
| `low` | Low | Yes |
| `volume` | Daily volume | Yes |
| `return.log` | Log return | Yes |
| `return` | Arithmetic return | Yes |
| `mktcap` | Market cap | Yes |
| `shares.outstanding` | Shares outstanding | Yes |
| `shares.float` | Float shares | Yes |

---

## 4. Layer 1 -- Asymmetric Volatility

| Feature | Raw Data | Source | Module | Status |
|---------|----------|--------|--------|--------|
| `rs_positive` | 5-min positive returns | Chunk Store L1 | `features/asymmetry.py` | Implemented |
| `rs_negative` | 5-min negative returns | Chunk Store L1 | `features/asymmetry.py` | Implemented |
| `bpv` | Consecutive absolute returns | Chunk Store L1 | `features/asymmetry.py` | Implemented |
| `jump_variation` | max(RV - BPV, 0) x jump_indicator | (derived from L0) | `features/asymmetry.py` | Implemented |
| `continuous_variation` | RV - jump_variation | (derived from L0) | `features/asymmetry.py` | Implemented |
| `jump_indicator` | BNS test at 99.9% | (derived from L0) | `features/asymmetry.py` | Implemented |

**Data pipeline:** Same as Layer 0. All L1 features are computed from the same 5-min return series. `compute_daily_rv_from_ticks()` already returns `rs_positive`, `rs_negative`, `bpv`, `jump_stat`, `jump_indicator`, `continuous_variation`, `jump_variation`.

No additional query needed beyond L0.

### Query: Compute Semivariances Directly

```python
from volforecast.features.asymmetry import compute_semivariances

# returns = pd.Series of 5-min log returns
semivars = compute_semivariances(returns)
# Returns: dict with keys 'rs_positive', 'rs_negative'
```

### Query: BPV and Jumps Directly

```python
from volforecast.features.asymmetry import compute_bpv, detect_jumps

bpv = compute_bpv(returns)
jump_test = detect_jumps(rv, bpv, rq, n_obs=len(returns))
# Returns: dict with keys 'z_stat', 'jump_indicator' (bool)
```

---

## 5. Layer 2 -- Options-Implied (SPX-level)

> **Last updated:** 2026-05-19. Strike semantics corrected 2026-05-18. EDRVOL_PERCENT uses positive call-delta convention (0.05-0.95).

| Feature | Raw Data | Source | Data Access | Module | Status |
|---------|----------|--------|-------------|--------|--------|
| `atm_iv_1m` | IV at relativeStrike=1.0, strikeRef=forward, tenor=1m | Marquee EDRVOL_PERCENT (`bbid="SPX"`) | `iv_ingest.ingest_iv_surface()` | `data/iv_ingest.py` → `data/iv_features.py` → `features/options.py` | **SHIPPED** |
| `atm_iv_3m` | IV at relativeStrike=1.0, strikeRef=forward, tenor=3m | Marquee EDRVOL_PERCENT | same | same | **SHIPPED** |
| `vrp` | ATM_IV_1m^2 - RV_22d*252 | Marquee + L0 RV | `iv_features.build_iv_feature_panel()` | `data/iv_features.py` | **SHIPPED** |
| `risk_reversal_25d` (skew_1m) | IV(delta=0.75) - IV(delta=0.25) | Marquee EDRVOL_PERCENT | `iv_ingest.ingest_iv_surface()` | `data/iv_ingest.py` | **SHIPPED** |
| `term_slope` | ATM_3m - ATM_1m | Marquee EDRVOL_PERCENT | `iv_features.build_iv_feature_panel()` | `data/iv_features.py` | **SHIPPED** |
| `butterfly` | 0.5*(IV_put25d + IV_call25d) - ATM | Marquee EDRVOL_PERCENT | `iv_features.build_iv_feature_panel()` | `data/iv_features.py` | **SHIPPED** |
| `vol_of_vix` (VVIX proxy) | sqrt(252 * rolling_var(log_ret_vix, 22d)) | Derived from VIX | `iv_features.build_iv_feature_panel()` | `data/iv_features.py` | **SHIPPED** |
| `iv_rv_gap` | ATM_IV - sqrt(RV_22d * 252) | Marquee + L0 RV | `iv_features.build_iv_feature_panel()` | `data/iv_features.py` | **SHIPPED** |
| `vix_level` | VIX close | TSDB `eqpad_.VIX@close` | `iv_ingest.ingest_iv_surface()` | `data/iv_ingest.py` | **SHIPPED** |
| `vix_innovation` | VIX_t - VIX_{t-1} | Derived from VIX | `iv_features.build_iv_feature_panel()` | `data/iv_features.py` | **SHIPPED** |
| `vvix` (direct) | CBOE VVIX index | TSDB | **UNAVAILABLE** (all 13 symbol variants tested 2026-05-18) | — | N/A (proxy above) |
| `vix_term_slope` | VX2 settle - VX1 settle | TSDB `eqpad_VX{X}YY@settle` | (manual stitching needed) | `features/options.py` | TODO |
| `vix_term_curvature` | VX3 - 2*VX2 + VX1 | TSDB | (manual stitching needed) | `features/options.py` | TODO |
| `event_implied_vol` | IV change around scheduled events | Marquee EDRVOL_PERCENT + L5 calendar | `marquee.fetch_iv_surface()` | `features/options.py` | TODO (needs L5) |
| `stock_atm_iv` / `stock_vrp` | Single-stock IV via ric | Marquee EDRVOL_PERCENT | (returned empty in test) | — | TODO (P3) |

### History Depth Probe (2026-05-18)

**Critical finding:** Two Marquee datasets exist with very different coverage:

| Dataset | History | Tenors | Strikes | Rows/day |
|---------|---------|--------|---------|----------|
| `EDRVOL_PERCENT_STANDARD` | **2023-05-22 onward only** (408 days) | 13 (1m–2y) | 28 (0.25–1.5 moneyness) | ~507 |
| `EDRVOL_PERCENT` | **2013-01-02 onward** (full history) | 31 (1w–10y) | 49 (delta-based + moneyness) | ~2,852 |

**Use `EDRVOL_PERCENT`** (non-STANDARD) for this project — it covers the full 2015–2025 RV period.

**`EDRVOL_PERCENT_STANDARD`** is a reduced subset (fewer tenors/strikes, recent history only). The original data probe (May 2026) tested only STANDARD and got 3,549 rows for a 10-day window — correctly identifying coverage but **not** history depth.

**Validated per-year coverage (EDRVOL_PERCENT, bbid="SPX"):**
- 2013: 22 days/month (full)
- 2014: 22 days/month (full)
- 2015: 21 days/month (full) — **aligns with RV start**
- 2016–2025: all confirmed (19–22 days/month)

**Strike semantics differ between datasets:**
- STANDARD: `relativeStrike` in moneyness (0.25–1.5, ATM=1.0)
- NON-STANDARD: mixed delta-based (negative = OTM put delta: -4.0 to -0.25) + moneyness (0.0–4.0, ATM=1.0)

**VVIX: CONFIRMED UNAVAILABLE (exhaustive probe 2026-05-18).** All 13 TSDB symbol variants tested:
- `eqpad_.VVIX@close`, `eqpad_VVIX@close`, `eqpad_.VVIX@settle/last/open/high/low` → 500 Internal Server Error
- `eqpad_VVIX.X@close`, `eqpad_.VVIX.X@close`, `cboe_.VVIX@close` → 500
- `mqd_.VVIX@close` → 403 Forbidden (may need entitlement)
- `eqvol_vix@vvix`, `eqvolrt_vix@vvix` → empty (0 rows)

**Workaround:** Compute realized vol-of-VIX: `rvol_vix = sqrt(252 * log(vix/vix.shift(1))^2.rolling(22).mean())`

**VIX (reference):** `eqpad_.VIX@close` via TSDBSymbol works: 2,537 rows, 2015-01-02 to 2025-01-03, range 9.14–82.69.

**VIX futures:** Individual contracts work via TSDBSymbol (e.g., `eqpad_VXH24@settle`). **Generic continuation symbols (VX.001, VXc1, VX1, UX1) are NOT available.** Must stitch individual monthly contracts with roll logic. Note: expired contracts return HTTP 500, not empty — error handling required.

**Single-stock IV:** `ric=".AAPL.O"` via `EDRVOL_PERCENT` returned empty in this session (may require different entitlements or be intermittent). Not needed for SPX-level features.

### Query: SPX IV Surface (Marquee — USE THIS)

```python
from gs_quant.session import GsSession
GsSession.use()
from gs_quant.data import Dataset
from datetime import date

# --- USE EDRVOL_PERCENT (not STANDARD) for full 2013+ history ---
ds = Dataset("EDRVOL_PERCENT")
iv_data = ds.get_data(
    start=date(2015, 1, 2),
    end=date(2015, 1, 31),
    bbid="SPX",
)
# Returns: ~59,892 rows for 21 business days (~2,852 rows/day)
# Columns: assetId, strikeReference, tenor, relativeStrike,
#           absoluteStrike, impliedVolatility, updateTime, bbid

# --- IMPORTANT: Query max ~1 month at a time (rate limits on full-year) ---
# For bulk historical fetch, chunk by month.

# --- ATM 1m IV extraction ---
atm_1m = iv_data[
    (iv_data["tenor"] == "1m") & (iv_data["relativeStrike"] == 1.0)
]["impliedVolatility"]
# Returns: 1 row per business day (21 rows for Jan 2015)
# Values in decimal (0.12 = 12% annualized IV)
```

**DO NOT USE** `EDRVOL_PERCENT_STANDARD` for historical work — only has data from 2023-05-22.

### Query: SPX IV Surface (STANDARD — recent data only)

```python
# Only use for real-time/recent data (2023-05-22 onward)
ds_std = Dataset("EDRVOL_PERCENT_STANDARD")
iv_recent = ds_std.get_data(
    start=date(2024, 6, 3),
    end=date(2024, 6, 7),
    bbid="SPX",
)
# Returns: ~2,535 rows for 5 days (fewer tenors/strikes than EDRVOL_PERCENT)
```

**Confirmed tenors (EDRVOL_PERCENT):** 31 — 1w, 2w, 3w, 4w, 5w, 6w, 1m–9m, 13m–15m, 18m, 21m, 27m, 30m, 1y–10y.
**Confirmed strikes (EDRVOL_PERCENT):** 49 — delta-based (-4.0 to -0.25) + moneyness (0.0 to 4.0, including 0.975 and 1.025 near ATM).
**Single-stock access:** Use `ric=".AAPL.O"` (not `bbid`). See "Single-Stock IV" query section below. Returned empty in latest probe (may require specific entitlements).

### Query: VIX Index (TSDB — confirmed 2026-05-18)

```python
from _lib_eq1d_brazil_tsdb_fns import eq1d_brazil__tsdb
from datetime import date

vix = eq1d_brazil__tsdb(".VIX", "close", date(2015, 1, 2), date(2025, 1, 3))
# Returns: pd.Series, 2,537 points (9.14 to 82.69)

# Alternative (no pyslang — USE THIS from volforecast):
from gs_quant.session import GsSession
GsSession.use()
from gs_quant_internal.tsdb import TSDBSymbol
vix = TSDBSymbol("eqpad_.VIX@close").get_data(start="2015-01-02", end="2026-05-04")
```

### Query: VIX Futures Term Structure (TSDB)

```python
# Front month
vx1 = eq1d_brazil__tsdb("VXM26", "settle", date(2026, 1, 2), date(2026, 5, 4))
# 2nd month
vx2 = eq1d_brazil__tsdb("VXN26", "settle", date(2026, 1, 2), date(2026, 5, 4))
# 3rd month
vx3 = eq1d_brazil__tsdb("VXQ26", "settle", date(2026, 1, 2), date(2026, 5, 4))

# Term slope (contango > 0, backwardation < 0)
term_slope = vx2 - vx1
# Curvature
curvature = vx3 - 2 * vx2 + vx1
```

**Last confirmed values:** VX1=21.06, VX2=21.99, VX3=22.21 (contango, slope=+0.93)

### Query: FX Implied Vol (Marquee)

```python
from gs_quant.data import Dataset

ds = Dataset("FXIVOL_STANDARD")
fxiv = ds.get_data(
    start=date(2026, 4, 24),
    end=date(2026, 5, 4),
    bbid="EURUSD",
)
# Returns: DataFrame, ~72 rows for 10 days
```

### Query: S&P 500 Breadth (TSDB)

```python
div_yield = eq1d_brazil__tsdb(".SPX", "index.div.yield", date(2015, 1, 2), date(2026, 5, 4))
pe_ratio = eq1d_brazil__tsdb(".SPX", "index.ratio.pe", date(2015, 1, 2), date(2026, 5, 4))
adv_volume = eq1d_brazil__tsdb(".SPX", "index.volume.advc", date(2015, 1, 2), date(2026, 5, 4))
dec_volume = eq1d_brazil__tsdb(".SPX", "index.volume.decl", date(2015, 1, 2), date(2026, 5, 4))
```

### Query: Single-Stock IV Surface (Marquee — RESOLVED)

The `ric` parameter (not `bbid`) is the correct identifier for single-stock queries.
Evidence: Slang production scripts use `@Marquee API::Query Data("EDRVOL_PERCENT", StructureCase("ric", symbols), ...)`.

```python
from gs_quant.session import GsSession
GsSession.use()
from gs_quant.data import Dataset

# --- Method 1: Marquee Dataset API (ric parameter) ---
ds = Dataset("EDRVOL_PERCENT")
iv_aapl = ds.get_data(
    start=date(2026, 5, 1),
    end=date(2026, 5, 9),
    ric=".AAPL.O",        # <-- ric, NOT bbid
)
# Expected: DataFrame with columns including impliedVolatility, tenor, relativeStrike

# --- Method 2: TSDB bridge (confirmed from "Test: TSDB Driver MQ Data" regtest) ---
from gs_quant_internal.tsdb import TSDBSymbol

# ATM IV (all tenors/strikes)
iv_ts = TSDBSymbol("mqd_AAPL.OQ@impliedVolatility.EDRVOL_PERCENT").get_data(
    start="2026-05-01", end="2026-05-09"
)
# Specific tenor + strike + delta
iv_2y = TSDBSymbol("mqd_AAPL.OQ@impliedVolatility.2y.1_25.delta.EDRVOL_PERCENT").get_data(
    start="2026-05-01", end="2026-05-09"
)

# --- Coverage: list all available RICs ---
coverage = ds.get_coverage()
# Returns DataFrame with 'ric' column listing all covered symbols
```

**RIC format mapping:**

| Context | AAPL format | GOOGL format | SPX format |
|---------|-------------|--------------|------------|
| Marquee Dataset `ric=` | `.AAPL.O` | `.GOOGL.O` | `SPX` |
| TSDB bridge `mqd_` | `AAPL.OQ` | `GOOGL.OQ` | `.SPX` |
| Chunk Store | `AAPL` | `GOOGL` | -- |

---

## 6. Layer 3 -- Microstructure

| Feature | Raw Data | Source | Symbols | Module | Status |
|---------|----------|--------|---------|--------|--------|
| `price_acceleration` | Trade prices (log-return-of-log-return) | Chunk Store L1 | All 34 | `features/microstructure.py` | Implemented |
| `effective_spread` | Trade price vs midquote | Chunk Store L1 | All 34 | `features/microstructure.py` | Implemented |
| `signed_volume` | Trade size x tick direction | Chunk Store L1 | All 34 | `features/microstructure.py` | Implemented |
| `obi` (order book imbalance) | Bid/ask sizes (levels 1-3) | Chunk Store L2 | E-mini only | `features/microstructure.py` | Implemented |
| `depth_ratio` | Sum bid depth / sum ask depth | Chunk Store L2 | E-mini only | `features/microstructure.py` | Implemented |
| `vpin` | Volume-synchronized probability | Chunk Store L1 | All 34 | `features/microstructure.py` | Implemented |
| `sub_window_rv_ratio` | Max(RV_subwindow) / RV_full | Chunk Store L1 | All 34 | `features/microstructure.py` | Implemented |
| `market_urgency` | Volume-weighted price impact | Chunk Store L1 | All 34 | `features/microstructure.py` | Implemented |

### Query: Fetch L1 Quotes (Bid/Ask for Spread)

```python
from volforecast.data.chunk_store import fetch_quotes
from datetime import date

quotes = fetch_quotes("AAPL", date(2026, 5, 4), date(2026, 5, 4))
# Returns: DataFrame with columns [bid_price, ask_price, bid_size, ask_size]
# Index: tz-aware DatetimeIndex
# Shape: ~100K rows
```

### Query: Fetch E-mini L2 Depth

```python
from volforecast.data.chunk_store import fetch_depth
from datetime import date

depth = fetch_depth(date(2026, 5, 4), date(2026, 5, 4), levels=3)
# Returns: DataFrame with columns like BEST_BID1, BEST_ASK1, BEST_BSIZ1, BEST_ASIZ1, ...
# Index: tz-aware DatetimeIndex
# Shape: ~488K rows for full day
```

### Query: E-mini L2 Raw (Direct Chunk Store)

```python
from pytickclient import query
import pytz
from datetime import datetime

TZ = pytz.timezone("America/New_York")
st = TZ.localize(datetime(2026, 5, 4, 9, 30, 0))
et = TZ.localize(datetime(2026, 5, 4, 16, 0, 0))

depth_fields = ["BEST_BID1", "BEST_ASK1", "BEST_BSIZ1", "BEST_ASIZ1",
                "BEST_BID2", "BEST_ASK2", "BEST_BSIZ2", "BEST_ASIZ2",
                "BEST_BID3", "BEST_ASK3", "BEST_BSIZ3", "BEST_ASIZ3"]

raw = query.chunk_query(["ESM26m"], st, et, "Eq", fields=depth_fields)
df = pd.DataFrame(raw)
# Shape: ~488K rows, one tick per L2 update
```

### Query: E-mini Tick Direction

```python
# PRCTCK_1 field: 1.0 = uptick, 2.0 = downtick, 0.0 = unchanged
raw = query.chunk_query(["ESM26"], st, et, "Eq",
      fields=["TRDPRC_1", "TRDVOL_1", "PRCTCK_1"])
df = pd.DataFrame(raw)
# PRCTCK_1 distribution: {0.0: 209K, 1.0: 20K, 2.0: 20K}
```

### Query: TSDB Intraday Real-Time Ticks

```python
from _lib_eq1d_brazil_tsdb_fns import eq1d_brazil__tsdb_rt
from datetime import datetime

# Trade ticks
trades = eq1d_brazil__tsdb_rt("AAPL.OQ", "tick.trd",
    datetime(2026, 5, 4, 14, 0, 0), datetime(2026, 5, 4, 14, 15, 0))
# ~10,691 ticks per 15 min for AAPL

# Bid/ask quotes
bids = eq1d_brazil__tsdb_rt("AAPL.OQ", "tick.bid",
    datetime(2026, 5, 4, 14, 0, 0), datetime(2026, 5, 4, 14, 15, 0))
asks = eq1d_brazil__tsdb_rt("AAPL.OQ", "tick.ask",
    datetime(2026, 5, 4, 14, 0, 0), datetime(2026, 5, 4, 14, 15, 0))
```

**Note:** `td.*` aggregated fields (vwap, spread, numticks) are NOT supported for US equities. Compute from raw tick data instead.

---

## 7. Layer 4 -- Cross-Asset Spillovers

| Feature | Raw Data | Source | TSDB Symbol | Module | Status |
|---------|----------|--------|-------------|--------|--------|
| `treasury_slope` | 10Y - 2Y yield | TSDB daily | see below | `features/cross_asset.py` | Implemented |
| `treasury_slope_change` | daily diff of slope | TSDB daily | (derived) | `features/cross_asset.py` | Implemented |
| `fx_vol` | USD/JPY rolling vol | TSDB daily | `usd/jpy` | `features/cross_asset.py` | Implemented |
| `commodity_vol_cl` | WTI rolling vol | Chunk Store / TSDB | `CLM26` | `features/cross_asset.py` | Implemented |
| `commodity_vol_gc` | Gold rolling vol | Chunk Store / TSDB | `GCM26` | `features/cross_asset.py` | Implemented |
| `sector_mean_rv` | Cross-sectional mean RV | (derived from L0) | -- | `features/cross_asset.py` | TODO |
| `vix_equity_corr` | Rolling VIX-RV corr | TSDB VIX + L0 RV | -- | `features/cross_asset.py` | Implemented |
| `cross_asset_rv_rank` | Percentile rank of RV | (derived from L0) | -- | `features/cross_asset.py` | TODO |

### Query: Treasury Prices (TSDB)

```python
from _lib_eq1d_brazil_tsdb_fns import eq1d_brazil__tsdb
from datetime import date

ust_2y  = eq1d_brazil__tsdb("US2YT=RR", "close", date(2015, 1, 2), date(2026, 5, 4))
ust_5y  = eq1d_brazil__tsdb("US5YT=RR", "close", date(2015, 1, 2), date(2026, 5, 4))
ust_10y = eq1d_brazil__tsdb("US10YT=RR", "close", date(2015, 1, 2), date(2026, 5, 4))
ust_30y = eq1d_brazil__tsdb("US30YT=RR", "close", date(2015, 1, 2), date(2026, 5, 4))
# Returns: pd.Series each, ~2,850 points
# NOTE: These are bond PRICES, not yields. Yield = f(price, coupon, maturity).

# Yield curve slope proxy (price-based):
slope = ust_10y - ust_2y
```

### Query: USD/JPY (TSDB)

```python
usdjpy = eq1d_brazil__tsdb("usd/jpy", "close", date(2015, 1, 2), date(2026, 5, 4))
# Returns: pd.Series (~2,850 points). Last confirmed: 0.494
# Note: This is JPY per 1 USD (inverted convention)
```

### Query: Commodity Futures Settle (TSDB)

```python
# Specific contract (must roll manually):
cl_settle = eq1d_brazil__tsdb("CLM26", "settle", date(2026, 1, 2), date(2026, 5, 4))
gc_settle = eq1d_brazil__tsdb("GCM26", "settle", date(2026, 1, 2), date(2026, 5, 4))

# E-mini settle + open interest:
es_settle = eq1d_brazil__tsdb("ESM26", "settle", date(2026, 1, 2), date(2026, 5, 4))
es_oi     = eq1d_brazil__tsdb("ESM26", "openint", date(2026, 1, 2), date(2026, 5, 4))
```

**Generic front-month symbols (CLv1, GCv1) do NOT work in TSDB.** Must use specific contract months and roll manually.

### Query: Commodity/Treasury Futures Tick Data (Chunk Store)

```python
# For computing intraday vol of cross-asset futures:
st = TZ.localize(datetime(2026, 5, 4, 9, 30, 0))
et = TZ.localize(datetime(2026, 5, 4, 16, 0, 0))

cl_ticks = pd.DataFrame(query.chunk_query(["CLM26"], st, et, "Eq",
           fields=["TRDPRC_1", "TRDVOL_1"]))
# ~56K ticks/15min for CL

gc_ticks = pd.DataFrame(query.chunk_query(["GCM26"], st, et, "Eq",
           fields=["TRDPRC_1", "TRDVOL_1"]))
# ~44K ticks/15min for GC

ty_ticks = pd.DataFrame(query.chunk_query(["TYM26"], st, et, "Eq",
           fields=["TRDPRC_1", "TRDVOL_1"]))
# ~106K ticks/15min for TY (10Y T-Note futures)

nq_ticks = pd.DataFrame(query.chunk_query(["NQM26"], st, et, "Eq",
           fields=["TRDPRC_1", "TRDVOL_1"]))
# ~667K ticks/15min for NQ (Nasdaq futures)
```

---

## 8. Layer 5 -- Calendar / Events

| Feature | Raw Data | Source | Module | Status |
|---------|----------|--------|--------|--------|
| `fomc_indicator` | FOMC meeting dates | Hardcoded / Fed website | `features/calendar.py` | Implemented |
| `nfp_indicator` | NFP release dates | Hardcoded / BLS | `features/calendar.py` | Implemented |
| `opex_indicator` | Options expiry dates | exchange_calendars | `features/calendar.py` | Implemented |
| `quarter_end` | Quarter-end rebalancing | exchange_calendars | `features/calendar.py` | TODO |
| `earnings_proximity` | Days to/from earnings | External (not yet sourced) | `features/calendar.py` | TODO |
| `day_of_week` | Monday=0 ... Friday=4 | pd.Timestamp | `features/calendar.py` | Implemented |
| `time_of_day` | Intraday U-shape seasonality weight | pd.Timestamp | `features/calendar.py` | TODO |

### Query: NYSE Trading Calendar

```python
import exchange_calendars as xcals

nyse = xcals.get_calendar("XNYS")
sessions = nyse.sessions_in_range("2026-01-01", "2026-12-31")
# Returns: DatetimeIndex of NYSE trading days

# Check if a date is a trading day:
is_open = nyse.is_session(pd.Timestamp("2026-05-04"))

# CME calendar (for futures):
cme = xcals.get_calendar("us_futures")
```

### Query: FOMC Meeting Dates (Hardcoded 2026)

```python
# Source: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
FOMC_2026 = [
    date(2026, 1, 28), date(2026, 1, 29),   # Jan
    date(2026, 3, 17), date(2026, 3, 18),   # Mar
    date(2026, 5, 5),  date(2026, 5, 6),    # May
    date(2026, 6, 16), date(2026, 6, 17),   # Jun
    date(2026, 7, 28), date(2026, 7, 29),   # Jul
    date(2026, 9, 15), date(2026, 9, 16),   # Sep
    date(2026, 10, 27), date(2026, 10, 28), # Oct
    date(2026, 12, 15), date(2026, 12, 16), # Dec
]

# Build relative-day encoding: -1 = day before, 0 = FOMC day, +1 = day after
def fomc_indicator(trade_date, fomc_dates, window=2):
    for fd in fomc_dates:
        delta = (trade_date - fd).days
        if abs(delta) <= window:
            return delta
    return None  # not near FOMC
```

### Query: Monthly Options Expiry (3rd Friday)

```python
from datetime import date
import calendar

def third_friday(year, month):
    """3rd Friday of given month (standard monthly OpEx)."""
    c = calendar.monthcalendar(year, month)
    # Friday is weekday 4
    fridays = [week[4] for week in c if week[4] != 0]
    return date(year, month, fridays[2])

opex_dates_2026 = [third_friday(2026, m) for m in range(1, 13)]
# Quarterly OpEx (Mar, Jun, Sep, Dec) are higher-impact
```

### Earnings Calendar

**No automated source currently available.** Options:
1. TSDB `eps` field is event-driven and only populated on reporting dates (confirmed empty in short windows)
2. External: Bloomberg corporate actions, Refinitiv earnings calendar
3. Manual: Hard-code earnings dates for the 30 mega-cap names

---

## 9. Layer 6 -- Long Memory / Roughness

| Feature | Raw Data | Source | Module | Status |
|---------|----------|--------|--------|--------|
| `frac_diff_rv` | Daily RV series | Derived from L0 | (not yet built) | TODO |
| `hurst_exponent` | Rolling window of daily RV | Derived from L0 | (not yet built) | TODO |
| `vol_of_vol` | std(RV) over 22 days | Derived from L0 | (not yet built) | TODO |
| `regime_duration` | Days since last 2-sigma spike | Derived from L0 | (not yet built) | TODO |

**No additional raw data query required.** All L6 features are second-order transformations of the daily RV series computed in Layer 0.

### Recipe: Fractionally Differenced RV

```python
# d ~ 0.35-0.45 preserves long memory while ensuring stationarity
# Use fracdiff package or manual implementation:
# (1 - L)^d * log_rv where L is lag operator

import numpy as np

def frac_diff_weights(d, n_weights=100, threshold=1e-5):
    """Compute fractional differencing weights."""
    w = [1.0]
    for k in range(1, n_weights):
        w_k = -w[-1] * (d - k + 1) / k
        if abs(w_k) < threshold:
            break
        w.append(w_k)
    return np.array(w)

def frac_diff(series, d=0.4):
    """Apply fractional differencing to a series."""
    weights = frac_diff_weights(d)
    n = len(weights)
    result = np.full(len(series), np.nan)
    for t in range(n - 1, len(series)):
        result[t] = np.dot(weights, series[t - n + 1:t + 1][::-1])
    return pd.Series(result, index=series.index)
```

### Recipe: Rolling Hurst Exponent

```python
def rolling_hurst(rv_series, window=60):
    """Estimate Hurst exponent via R/S analysis over rolling window."""
    result = pd.Series(np.nan, index=rv_series.index)
    log_rv = np.log(rv_series)
    for i in range(window, len(log_rv)):
        segment = log_rv.iloc[i - window:i].values
        mean_adj = segment - segment.mean()
        cumdev = np.cumsum(mean_adj)
        R = cumdev.max() - cumdev.min()
        S = segment.std(ddof=1)
        if S > 0 and R > 0:
            result.iloc[i] = np.log(R / S) / np.log(window)
    return result
# H < 0.15: rough/fast mean-reversion; H > 0.3: trending
```

---

## 10. Data Gaps & Workarounds

| Data | Status | Impact | Workaround |
|------|--------|--------|------------|
| Broker trade attribution | Structurally impossible (SEC regs) | No broker HHI/flow features | Use volume imbalance from anonymous ticks |
| L2 depth for equities | Not in Chunk Store | No equity LOB features | E-mini L2 as index proxy; equities L1 only |
| Pre-computed VWAP/spread (`td.*`) | Not for US equities | Must compute manually | Raw `tick.trd`/`tick.bid`/`tick.ask` confirmed |
| Micro E-mini (MES) | Empty in Chunk Store | -- | Use full E-mini (ES) |
| Fed Funds rate (FFTQ) | Not in TSDB | No short-rate feature | 2Y Treasury as proxy |
| EUR/USD, GBP/USD | Not in TSDB | Limited FX features | Marquee FXIVOL works for EURUSD |
| Dollar Index (DXY) | Not in TSDB | No USD breadth feature | Compute from component pairs |
| Generic front futures (CLv1, GCv1) | Not in TSDB | Must roll manually | Use specific contracts (CLM26, GCM26) |
| VVIX (vol-of-vol index) | **All TSDB paths return 500/403/empty** (exhaustive 2026-05-18) | No direct VVIX feature | Compute realized vol-of-VIX from `eqpad_.VIX@close` |
| VIX futures generic continuation (VXc1, VX.001) | Not in TSDB | Must roll manually | Use specific contracts (VXH24, VXJ24, etc.) — expired contracts return 500 |
| CDX IG credit spread | Not in TSDB | No credit spread feature | Not critical for RV forecasting |
| Single-stock IV (e.g. AAPL) | **RESOLVED** — use `ric` param (not `bbid`) | Per-name IV-RV spread available | `Dataset("EDRVOL_PERCENT").get_data(ric=".AAPL.O")` or TSDB: `mqd_AAPL.OQ@impliedVolatility.EDRVOL_PERCENT` |
| TREOD (Marquee Treasury) | HTTP error | -- | TSDB treasury prices work |
| Earnings calendar | No automated source | Earnings proximity feature manual | Hard-code for 30 names |

### TSDB Symbol Reference

| Data | TSDB Symbol Pattern | Confirmed |
|------|-------------------|-----------|
| Equity close | `eqpad_AAPL.OQ@close` | Yes |
| Equity adjusted close | `eqpad_AAPL.OQ@close.adj.allincdiv` | Yes |
| Equity volume | `eqpad_AAPL.OQ@volume` | Yes |
| Equity log return | `eqpad_AAPL.OQ@return.log` | Yes |
| S&P 500 index | `eqpad_.SPX@close` | Yes |
| VIX index | `eqpad_.VIX@close` | Yes |
| Index div yield | `eqpad_.SPX@index.div.yield` | Yes |
| Index P/E | `eqpad_.SPX@index.ratio.pe` | Yes |
| E-mini settle | `eqpad_ESM26@settle` | Yes |
| E-mini open interest | `eqpad_ESM26@openint` | Yes |
| VIX future settle | `eqpad_VXM26@settle` | Yes |
| Treasury price | `eqpad_US10YT=RR@close` | Yes |
| FX rate | Slang wrapper: `eq1d_brazil__tsdb("usd/jpy", ...)` | Yes |
| Single-stock IV (ATM) | `mqd_AAPL.OQ@impliedVolatility.EDRVOL_PERCENT` | Regtest-confirmed |
| Single-stock IV (tenor+delta) | `mqd_AAPL.OQ@impliedVolatility.2y.1_25.delta.EDRVOL_PERCENT` | Regtest-confirmed |
| SPX IV (TSDB bridge) | `mqd_.SPX@impliedVolatility.EDRVOL_PERCENT` | Regtest-confirmed |

### Slang Wrapper Symbol Rules

| Data | Slang symbol | Notes |
|------|-------------|-------|
| Equity | `"AAPL.OQ"` | Use RIC with exchange suffix |
| Index | `".VIX"`, `".SPX"` | Leading dot, no `eqpad_` prefix |
| Futures | `"ESM26"`, `"VXM26"` | Direct contract symbol |
| Treasury | `"US10YT=RR"` | Reuters RIC |
| FX | `"usd/jpy"` | Lowercase pair format |

### E-mini Front Month Roll Logic

```python
# E-mini cycles: H (Mar), M (Jun), U (Sep), Z (Dec)
# Roll on 1st of expiry month
_ES_CYCLE = [
    (1, "H"), (2, "H"), (3, "M"), (4, "M"), (5, "M"), (6, "U"),
    (7, "U"), (8, "U"), (9, "Z"), (10, "Z"), (11, "Z"), (12, "H"),
]

def resolve_es_symbol(trade_date):
    month = trade_date.month
    _, code = _ES_CYCLE[month - 1]
    year = trade_date.year
    if month == 12:
        year += 1
    return f"ES{code}{year % 100:02d}"
```

---

## Appendix: volforecast.data Module Status

| Module | Function | Status | Query Source |
|--------|----------|--------|-------------|
| `chunk_store.py` | `fetch_trades(symbol, start, end)` | **Implemented** | Chunk Store L1 |
| `chunk_store.py` | `fetch_quotes(symbol, start, end)` | **Implemented** | Chunk Store L1 |
| `chunk_store.py` | `fetch_depth(start, end, levels)` | **Implemented** | Chunk Store L2 (E-mini) |
| `resample.py` | `resample_trades_to_bars(trades, freq)` | **Implemented** | -- |
| `resample.py` | `compute_daily_rv_from_ticks(trades)` | **Implemented** | -- |
| `tsdb.py` | `fetch_daily_ohlcv(symbols, start, end)` | **TODO** | TSDB daily |
| `tsdb.py` | `fetch_treasury_yields(start, end, tenors)` | **TODO** | TSDB daily |
| `tsdb.py` | `fetch_fx_rates(start, end, pairs)` | **TODO** | TSDB daily |
| `tsdb.py` | `fetch_commodity_prices(start, end, symbols)` | **TODO** | TSDB daily |
| `marquee.py` | `fetch_iv_surface(start, end, tenors, strikes)` | **Implemented** | Marquee EDRVOL_PERCENT |
| `marquee.py` | `fetch_atm_iv(start, end, tenors)` | **Implemented** | Marquee EDRVOL_PERCENT |
| `marquee.py` | `fetch_skew(start, end, tenors)` | **Implemented** | Marquee EDRVOL_PERCENT |
| `marquee.py` | `fetch_vvix(start, end)` | **Implemented** (TSDB unavailable — will use vol-of-VIX proxy) | TSDB |

For TODO functions, use the direct query snippets in each layer section above until the `volforecast.data` wrappers are implemented.
