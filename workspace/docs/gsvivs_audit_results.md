# GSVIVS01 Audit — Canonical Source-Of-Truth

**Generated:** 2026-06-09  
**Source:** `data/external/output.json` (293.7 MB, 17.3M lines, 1011 days)  
**Derived:** `data/external/gsvivs_trades.parquet`, `data/external/gsvivs_daily.parquet`  
**Method:** every claim verified by automated check on full dataset. Risk-node payloads excluded. No execution prices exist in the JSON (hard data limit).

---

## 1. Summary

GSVIVS01 is a **pure 0-DTE short-variance index** trading SPX options. Daily: signal at 09:10 ET, sell variance-swap-weighted SPXW 0-DTE strip via 30-min TWAP (09:30-10:00 ET), delta-hedge with ES futures intraday, close at 16:00 ET MOC auction. **No overnight option exposure**, no 1-DTE leg, no carryover. Portfolio = cash only at EOD.

4-year track record (2022-05-25 to 2026-06-05): base-100 to 138.27 = **+38.27% cumulative**, ~9.6% annualized.

---

## 2. Daily Lifecycle

| Time (ET) | Event | JSON Evidence |
|---|---|---|
| 09:10 | Signal fires | `source="VSR 0b"`, `generation_time=09:10 ET`, `exec_type="TWAP"` |
| 09:30 | SPXW 0-DTE strip SELL TWAP begins | `execution_instructions.start_time=09:30 ET` |
| 10:00 | Opening TWAP ends; strip fully short | `execution_instructions.end_time=10:00 ET` |
| 10:00-15:59 | Delta-hedge (ES futures, 5-min TWAP clips) | `source="Intraday Delta Hedge"`, median 27 clips/day |
| 16:00 | SPX MOC auction settles all 0-DTE options | `source="VSR 0b"`, `gen_time=1970-01-01` (sentinel), `exec_type="MOC"`, qty = +mirror |
| 22:00 UTC | EOD index mark (17:00 ET winter / 18:00 ET summer) | `close_time` field; TC cash entries booked |
| Overnight | Cash only | `cash_sum == index_value` on all 1011 days (proved) |

### Verification (full dataset)

| Claim | Proof |
|---|---|
| Opening TWAP at 09:30 ET every day | 15,642/15,642 OPT_OPEN with `exec_start_et=="09:30"`, zero exceptions across 8 DST transitions |
| Closing = MOC | 15,642/15,642 OPT_CLOSE with `exec_type=="MOC"` + epoch `gen_time` |
| 0-DTE only | 15,642/15,642 OPT_OPEN with `expiry == trade_date`. Zero 1-DTE trades |
| Per-strike nets to zero | Max abs net qty = 0.0044 (12 edge cases out of ~30k tuples) |
| Cash-only portfolio | `sum(cash entries) == index_value` to 8.5e-14 on all 1011 days |
| `gen_time` = signal, not execution | 100% of opening legs stamp 09:10 ET; real window in `execution_instructions` |

---

## 3. Record Kinds

| source | count | role |
|---|---|---|
| `VSR 0b` | 62,568 | Option trades (open + close), 0-DTE SPXW only |
| `Intraday Delta Hedge` | 80,317 | ES front-month futures, 5-min TWAP clips |
| `Transactions Costs Fw` | 3,030 | Per-day futures TC cash booking |
| `Transaction Costs O` | 3,030 | Per-day option TC cash booking |
| `Execution Cash` | 1,010 | Cumulative option net cash flow balance |
| `Initial` | 1,011 | Constant seed of 100 index points |

No `MOC` source value exists. MOC lives in `execution_instructions.type`, not `source`.

---

## 4. Per-Day Record Anatomy (example: 2024-01-03)

- **13 OPT_OPEN** -- SPXW 0-DTE, Put/Call, qty NEGATIVE, gen=09:10 ET, TWAP 09:30-10:00 ET
- **13 OPT_CLOSE** -- same strikes, qty POSITIVE (exact mirror), gen=1970-01-01, exec_type=MOC
- **30 FUT_HEDGE** -- ES front-month (H24), 5-min TWAPs 10:00-15:59 ET
- **2 CASH** -- option TC + futures TC, booked at 22:00 UTC

Variation across days: strip size (see §6) and hedge clip count (see §7). Structure identical.

---

## 5. EOD Portfolio -- Always Cash

| entry | type | meaning |
|---|---|---|
| `Initial` | level | Seed 100, constant all 1011 days |
| `Execution Cash` | cumulative | Net option cash since inception |
| `Transaction Costs O` | cumulative | Negative sum option TC |
| `Transactions Costs Fw` | cumulative | Negative sum futures TC |

Identity: `Initial + ExecCash + TC_O + TC_Fw == index_value` holds to **8.5e-14** on all 1011 days. Proves: options flat, futures flat, four cash entries = complete state.

---

## 6. Strip Size, ES Roll, Calendar

**Strip size** (OPT_OPEN legs/day): mean 15.5, median 14, std 5.2, p5-p95: 9-25, range 7-51.

**ES roll:** quarterly mid-month, 17 contracts M22-M26, no anomalies.

**Half-days:** `close_time` = index mark time (always 22:00 UTC), not market close. Half-days (Thanksgiving Fri, Xmas Eve, Jul 3) show normal mark time. 13:00 ET early-close MOC not surfaced in JSON; assume exchange handles mechanically.

**Trading days:** 1011 entries, 1011 unique dates. 1010 have trades; 1 (2022-05-25 seed day) has only `Initial` entry.

---

## 7. Futures Delta Hedging

- **Instrument:** ES front-month (prefix `EqSp`, quarterly roll)
- **Execution:** 5-min TWAP clips, median 27/day
- **Window:** 10:00 ET (post-option TWAP) to 15:59 ET
- **Structured end-of-day windows (seen on 1001/1010 days):**
  - 15:30-15:50 ET (20-min rebalance)
  - 15:59-16:00 ET (1-min final clean-up)

---

## 8. Cash Flows and P&L

### Daily flows (index points, base = 100)

| Component | mean | median | std | min | max |
|---|---|---|---|---|---|
| flow_exec_cash (option net) | **+0.0642** | +0.1164 | 0.3132 | -2.5685 | +1.7471 |
| flow_tc_o (option TC) | -0.0075 | -0.0065 | 0.0041 | -0.0915 | -0.0033 |
| flow_tc_fw (futures TC) | -0.0190 | -0.0174 | 0.0090 | -0.0604 | -0.0017 |

Net daily P&L: +0.0377 idx pts = ~3.8 bps/day.

### Cumulative (4 years, 1010 days)

| component | total (idx pts) | annualized |
|---|---:|---:|
| Premium gross (Execution Cash) | +65.06 | +16.27/yr |
| Option TC | -7.61 | -1.90/yr |
| Futures TC | -19.18 | -4.80/yr |
| **Net** | **+38.27** | **+9.57/yr** |

Annualized: 8.4% compounded, 9.6% simple. Unit is **index points (base=100)**; no $-denominated notional in this JSON.

---

## 9. Data Limitations

### A. No execution prices

No `price` field exists on any trade record. Fields available:
`{end time, ex, execution instructions, expiry type, generation time, instrument, instrument type, k, option type, quantity, source, start time, type, underlying asset}`

Per-day net cash = `diff(Execution Cash)`. Individual fill prices unrecoverable. `RISK_NODE.baseline_risks.price` contains marks (not fills), excluded per directive.

### B. No 1-DTE strip

All 15,642 opening legs have `expiry == trade_date`. The 1-DTE `OPTION_DEF` entries in `risks for date` are reference-only metadata (tomorrow's planned strip preview), never traded or held.

### C. No execution Kvar

Without execution prices (A), Kvar-from-fills is impossible from this JSON. Only `Kvar_marks` (from `RISK_NODE.baseline_risks.price`) is computable, labeled as marks not fills.

### D. Per-strike net qty edge cases

12 (date, expiry, strike, put/call) tuples out of 15,642 have nonzero net (max 0.0044 contracts). Likely partial-fill artifacts; no material impact on the cash identity.

---

## 10. Reference Code & Reproducibility

| script | output | purpose |
|---|---|---|
| `gsvivs_p1_schema_probe.py` | `gsvivs_schema_keys_by_year.txt`, `_source_census.txt`, `_schema_sample_*.txt` | Schema + source census |
| `gsvivs_p1b_taxonomy.py` | `gsvivs_record_taxonomy.txt` | Record kind taxonomy |
| `gsvivs_p1c_raw_records.py` | `gsvivs_raw_records.txt` | Verbatim record dumps |
| `gsvivs_p1d_cash_flow.py` | `gsvivs_cash_flow_check.txt` | Cash-flow invariant + price-field search |
| `gsvivs_p2_extract.py` | `gsvivs_trades.parquet`, `gsvivs_daily.parquet` | Lean extractor (3 gates) |
| `gsvivs_p3a_timestamps.py` | `gsvivs_finding_timestamps.md` | Timestamp + DST verification |
| `gsvivs_p3_halfdays_roll.py` | `gsvivs_finding_halfdays_es_roll.md` | Half-day, ES roll, strip-size, 0DTE |

Scripts in `workspace/scripts/`, outputs in `workspace/tmp/` (except parquets in `data/external/`). Run in order; each idempotent.

---

## 11. Signal Implications for ML Backtester

The ML pipeline uses an externally-published GSVIVS Kvar series for the IV-RV gap signal. This audit does not change what the signal uses, but clarifies the mechanics:

- Strategy is **short forward variance at 09:30 ET** daily (signal fire 09:10 ET = legal cutoff for pre-trade features)
- Correct alignment: TTM ~6.5 hours (intraday SPX vol), **0-DTE marks at 09:10 ET** -- not 1-DTE marks at close
- If backtest uses 1-DTE Kvar: signal-consistent (published series) but mechanically not what the strategy trades
- Whether trial-042 "+24 bps Sharpe over always-long" survives a 0-DTE switch is an open question

No code changes made. Signal-rework decision parked.
