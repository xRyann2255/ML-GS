---
created: 2026-07-29
updated: 2026-07-29
tags: [python, tsdb, fields, dictionary, eqpad, reference]
status: active
relates:
  - ref/python-tsdb.md
---

# TSDB Field Dictionary (P2 — load on field/dataset lookup only)

Companion to `python-tsdb.md` (API patterns live there). This file is the full
field/dataset reference; load it only when resolving a specific field or
dataset id.

All fields below are the `Field` argument passed to the TSDB functions. The
symbol resolved internally is `eqpad_<RIC>@<Field>` (see `python-tsdb.md` §1.3
for the RIC mapping used by this project's 34-symbol US universe).

Fields are grouped by category. The **Data Mode** column indicates which
access path to use:

| Data Mode | Access path | Return Type | When to Use |
|---|---|---|---|
| **Daily** | `TSDBSymbol` / `<daily_tsdb_fn>` | `pd.Series` (Curve) | End-of-day values, historical series over date ranges |
| **RT**    | `<realtime_tsdb_fn>`               | `pd.Series` (RTCurve) | Intraday / real-time values over time ranges within a day |

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

These fields aggregate tick data over a time window. **Use the real-time TSDB fn only.**

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

Individual tick-level prices. **Use the real-time TSDB fn only.**

| Field | Description | Data Mode |
|---|---|---|
| `tick` | Individual tick price (generic) | **RT** |
| `tick.ask` | Individual tick ask price | **RT** |
| `tick.bid` | Individual tick bid price | **RT** |
| `tick.trd` | Individual tick trade price | **RT** |
