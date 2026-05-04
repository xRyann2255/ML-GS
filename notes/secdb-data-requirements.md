# SecDB Data Requirements — Complete Entitlements Checklist

Use this document during the Phase 0 Data Access Audit (Task 2). For each row, attempt to pull 5 business days of sample data and record: accessible (Y/N), frequency, history depth, timestamp semantics, and any notes.

---

## 1. Primary Risk Cube Data (Must-Have)

These are non-negotiable. You need **(a)** and at least one of **(b)** to pass the Minimum Viable Data Gate and proceed past Phase 0.

### (a) VaR & Component VaR

| Data Point | Granularity | Frequency | Used For | Accessible? | Notes |
|---|---|---|---|---|---|
| Firm-level total VaR | Firm or desk | Daily EOD | VaR dynamics features, delta VaR | | |
| Component VaR — Rates | Asset class | Daily EOD | Cross-asset flow, panel extension | | |
| Component VaR — Equities | Asset class | Daily EOD | Cross-asset flow, panel extension | | |
| Component VaR — FX | Asset class | Daily EOD | Cross-asset flow, panel extension | | |
| Component VaR — Credit | Asset class | Daily EOD | Cross-asset flow, panel extension | | |
| Component VaR — Commodities | Asset class | Daily EOD | Cross-asset flow, panel extension | | |

### (b) At Least One of These Three

#### Factor-VaR Decomposition

| Data Point | Granularity | Frequency | Used For | Accessible? | Notes |
|---|---|---|---|---|---|
| Factor-VaR contributions per risk factor | Per factor | Daily EOD | Herfindahl index, top-3 factor share, concentration features | | |
| Factor identities/names | Per factor | Static/daily | Identifying dominant factors, labeling SHAP | | |
| Number of active factors | Firm or desk | Daily | Normalization for concentration metrics | | |

#### Scenario P&L

| Data Point | Granularity | Frequency | Used For | Accessible? | Notes |
|---|---|---|---|---|---|
| Stress scenario P&L results | Per scenario | Daily EOD | Rank, dispersion, worst-case identity | | |
| Scenario definitions/names | Per scenario | Static | Identifying worst-case scenario, detecting regime shifts | | |
| Number of active scenarios | Firm or desk | Daily | Normalization | | |

#### VaR Utilization

| Data Point | Granularity | Frequency | Used For | Accessible? | Notes |
|---|---|---|---|---|---|
| VaR usage (actual current VaR) | Firm or desk | Daily EOD | Utilization % numerator | | |
| VaR limit | Firm or desk | Daily or periodic | Utilization % denominator | | |
| History of limit changes | Firm or desk | Event-based | Avoid spurious signals from limit resets | | |

---

## 2. Risk Data Metadata

Record these during the data audit — they affect how you build the pipeline and whether your features are valid.

| Data Point | Why You Need It | Finding |
|---|---|---|
| **Timestamp semantics** — when is each risk run finalized? (T EOD? T+1 pre-open?) | Point-in-time stamping to prevent lookahead bias | |
| **VaR model methodology** — historical sim vs. Monte Carlo, window length | Structural breaks in methodology create spurious features | |
| **Dates of any methodology changes** in the lookback period | Need to control for model regime shifts in your signal | |
| **Desk/book hierarchy** — which books roll up to XA, which to other desks | Understand aggregation level of what you're reading | |
| **Asset class taxonomy** — how does SecDB classify instruments into rates/eq/FX/credit/commod | Align component VaR labels with your panel structure | |

---

## 3. Market Data for Prediction Targets

These construct the four prediction targets. May come from SecDB, Marquee, gs-quant `Dataset`, or a market data feed.

| Data Point | Frequency | Target It Feeds | Accessible? | Source | Notes |
|---|---|---|---|---|---|
| **VIX index** (CBOE VIX) | Daily close | VIX innovation | | | |
| **Rates futures/index** (UST 10Y, 2s10s, SOFR futures) | Daily close | Realized vol, drawdown, momentum reversal | | | |
| **Equity index** (SPX, EURO STOXX, Nikkei) | Daily close | Drawdown, realized vol | | | |
| **G10 FX spot rates** (EUR, GBP, JPY, CHF, AUD, NZD, CAD, NOK, SEK) | Daily close | Cross-asset momentum reversal, realized vol | | | |
| **Credit index levels** (CDX IG, CDX HY, iTraxx Main, iTraxx Crossover) | Daily close | Drawdown, realized vol | | | |
| **Commodity index/prices** (BCOM, WTI, Gold) | Daily close | Cross-asset panel | | | |
| **Momentum factor returns** by asset class | Daily | Momentum reversal target | | | |

---

## 4. Market Data for Confound Controls

Needed in Phase 2 to verify your signal isn't redundant with publicly available information. Every signal that shows IC > 0 is re-tested with these added as controls.

| Data Point | Frequency | Why | Accessible? | Notes |
|---|---|---|---|---|
| **VIX level** | Daily | Primary confound — "isn't this just VIX?" | | |
| **Credit spread** (CDX IG or IG-HY spread) | Daily | Credit stress confound | | |
| **Term slope** (2s10s or 3m10y) | Daily | Yield curve shape confound | | |
| **Realized cross-asset correlation** (rolling) | Daily (computed) | Correlation regime confound | | |
| **USD index** (DXY or trade-weighted) | Daily | Dollar regime confound | | |

---

## 5. Book-Level Greeks (Project 2 / Hybrid Path Only)

Only needed if the Week 13 checkpoint triggers a pivot to Project 2 (Book-Gamma Intraday Momentum) or a hybrid approach. These are deeper entitlements — you're reading individual book positions, not just aggregated risk.

### Greeks by Position/Book

| Data Point | Granularity | Frequency | Used For | Accessible? | Notes |
|---|---|---|---|---|---|
| **Book-level gamma** | Per position or per book | Daily or intraday | Net dealer gamma aggregation | | |
| **Book-level vega** | Per position or per book | Daily or intraday | Volatility exposure | | |
| **Book-level vanna** (dVega/dSpot) | Per position or per book | Daily | FOMC/CPI-day response prediction | | |
| **Book-level charm** (dDelta/dTime) | Per position or per book | Daily | End-of-day drift prediction | | |
| **Instrument identifiers with dealer side** (long/short) | Per position | Daily | Correct sign aggregation (the core advantage over public GEX) | | |
| **Instrument class mapping** | Static | Static | Group into rates futures, G10 FX options, credit index options | | |

### Instrument Classes for Greeks Aggregation

| Instrument Class | Examples | Priority |
|---|---|---|
| Rates futures and options | UST, Eurodollar/SOFR, Bund | High |
| G10 FX options | EUR/USD, USD/JPY, GBP/USD | High |
| Credit index options | CDX, iTraxx | Medium |
| Equity index options | SPX, EURO STOXX | If accessible |

---

## 6. Capacity Analysis Data (Phase 4A)

| Data Point | Frequency | Used For | Accessible? | Notes |
|---|---|---|---|---|
| **Bid-ask spreads** for traded instruments (futures, swaps, options) | Daily or intraday | Transaction cost modeling | | |
| **Daily trading volumes** by instrument | Daily | Market impact estimation | | |
| **Open interest** (for listed derivatives) | Daily | Capacity sizing | | |

---

## 7. Nice-to-Have (Not Critical)

| Data Point | Why | Accessible? | Notes |
|---|---|---|---|
| **Desk-level VaR** for multiple desks (not just firm-level) | Finer-grained cross-desk flow analysis | | |
| **Intraday VaR snapshots** | Higher-frequency signal construction | | |
| **Historical limit change log** | Control for limit resets vs. real utilization changes | | |
| **Short interest / borrow cost data** | Muravyev-Pearson-Pollet (2022) confound control if touching equities | | |
| **Repo rate / funding cost** | Adrian-Shin (2010) channel — dealer repo positions | | |
| **CoVaR or systemic risk measures** | Adrian-Brunnermeier (2016) extension | | |

---

## Phase-by-Phase Summary

| Phase | Sections Required |
|---|---|
| **Phase 0 (Weeks 1-2)** | Sections 1 + 2 — confirm you can pull them, record metadata |
| **Phase 1 (Weeks 3-5)** | Sections 1 + 2 — build pipeline against real schema |
| **Phase 2 (Weeks 6-12)** | Sections 1 + 2 + 3 + 4 — features, targets, confound controls |
| **Phase 4A (Weeks 14-17)** | Everything above + Section 6 — capacity analysis |
| **Phase 4B (Weeks 14-17)** | Everything above + Section 5 — book-level Greeks |

---

## How to Use This Document

1. **During Phase 0 Data Audit:** Walk through every row in Sections 1-4. For each, try to pull 5 business days via Slang or the Python-SecDB bridge. Fill in the "Accessible?" and "Notes" columns.
2. **Check the Data Gate:** After the audit, confirm you pass the minimum: Section 1(a) + at least one of Section 1(b). If not, discuss with sponsor before proceeding.
3. **Flag entitlement gaps early:** If anything in Sections 1-4 requires additional desk sign-off, start that process immediately — entitlement requests can take days to weeks.
4. **Revisit at Week 13:** If you're considering a pivot or hybrid path, audit Section 5 (Greeks) at that point.
