---
created: 2026-05-07
updated: 2026-06-11
tags: [implied-vol, VRP, VIX, options, skew, VVIX, term-structure, per-symbol-iv, EDRVS, GSVIVS, variance-swap, signal-time-contract]
status: active
priority: P2
source: workspace/research/implied-vol.md (archived)
relates: [optimal-feature-set, data-access, feature-composition]
---

# Implied Volatility and VRP — Summary

## Implementation Status (2026-05-21)

Layer 2 is ~85% complete for SPX-level scope. Core pipeline shipped; VRP upgraded to HAR-forecast-based.

### Shipped

| Component | Module | Notes |
|-----------|--------|-------|
| Raw IV ingestion | `data/iv_ingest.py` | Marquee EDRVOL_PERCENT, 2015-2025, 2567 daily rows |
| Feature computation | `data/iv_features.py` | 12 features with shift(1) causality |
| Model-facing layer | `features/options.py` | `OptionsLayer` registered, 15 model columns |
| CLI integration | `cli/ingest_iv.py` | Incremental cache, parallel chunk fetch |
| Tests | test_iv_ingest + test_iv_features + test_options | 28 passing |

### Remaining Gaps

| Feature | Blocker | Priority |
|---------|---------|----------|
| VIX futures term slope/curvature | No generic continuation symbols; must stitch monthly contracts | P2 |
| Direct VVIX | **RESOLVED: `eqsp_s_.vvix@close` works (2016+)** | P0 (swap in) |
| Event-implied vol | Requires Layer 5 calendar | P3 |
| Triple expansion (level/delta/z-score) | Mechanical; no data dependency | P2 |
| Per-symbol VRP via EDRVS | **SHIPPED (2026-06-05):** `fetch_edrvs_0dte()`, `iv_vs_0dte` column, `vol ingest-edrvs` CLI | Done |
| Per-symbol skew (25dc-25dp) | Data confirmed (edrvol_ 7 tenors); needs feature expansion | P1 |

### Strike Semantics (CRITICAL)

EDRVOL_PERCENT uses **positive call-delta convention** (0.05-0.95):
- `relativeStrike=0.75` with `strikeReference="delta"` = 25-delta PUT (ITM call)
- `relativeStrike=0.25` with `strikeReference="delta"` = 25-delta CALL (OTM call)
- `relativeStrike=1.0` with `strikeReference="forward"` = ATM

## VRP Construction

- **Variance Risk Premium:** VRP = IV² - E_t[RV_{t+1:t+22}]
- Bollerslev-Tauchen-Zhou (2009, RFS): VRP explains >15% of S&P 500 quarterly excess return variation (1990-2005)
- Bekaert-Hoerova (2014): VRP decomposes into risk and uncertainty components
- VRP predicts **both returns and future vol** (through mean reversion)
- Relatively under-explored with ML methods -- potential gap to exploit
- **2026-05-21:** Upgraded from backward-looking RV to HAR h=22 forecast as E[RV]. The forward-looking expectation captures the actual risk premium investors are pricing.

## VIX Term Structure Features

- VIX level, slope, curvature as features
- Risk-neutral skewness (Bakshi-Kapadia-Madan 2003): captures tail risk expectations
- VVIX (vol-of-vol): matters for delta-neutral strategies (gamma scalping P&L variance)
- **VVIX AVAILABLE** via `eqsp_s_.vvix@close` (2016+, daily close). Previous 13 eqpad/mqd variants failed but eqsp_s_ namespace works.
- COVID peak: 138.8. Normal range: 75-100.

## Rough Vol and VRP

- Rough vol models naturally generate steep IV skew and large VRP
- Cont-Das (2024): observed roughness may be microstructure noise artefact (frontier debate)

## Key Features from Marquee ERDVOL

| Feature | Construction | Horizon Impact | Status |
|---------|-------------|---------------|--------|
| ATM IV (30-day) | relativeStrike=1.0, strikeRef=forward | All horizons | Shipped |
| VRP | IV^2 - RV_22d*252 | 1w-1m (strongest) | Shipped |
| 25d Risk Reversal | IV(delta=0.75) - IV(delta=0.25) | 1-5 days | Shipped |
| Term Slope | IV^{3m} - IV^{1m} | 1w-1m | Shipped |
| Butterfly | 0.5*(put_25d + call_25d) - ATM | Crisis detection | Shipped |
| VVIX proxy | sqrt(252 * rolling_var(log_ret_vix, 22)) | 1-5 days | Shipped |
| IV-RV Gap | ATM IV - sqrt(RV_22d * 252) | 1-5 days | Shipped |
| VIX term slope | VX2_settle - VX1_settle | Regime signal | TODO |
| Event-implied vol | IV decomposition around events | Pre-event | TODO (needs L5) |

## Critical Nuance

- At 1-day horizon: options add only **1-3% QLIKE**
- At weekly-to-monthly: **5-10% QLIKE** (options embed future events: FOMC, earnings)
- GS edge: full tenor x strike grid per symbol via TSDB edrvol_ namespace (not just VIX)
- **Per-symbol IV now available** for 27 symbols (all universe equities + ETFs + SPX) via `edrvol_{ric}@{field}` (TSDB). Mapping in `constants.TICKER_TO_EDRVOL_RIC`.
- **Per-symbol full surface also available** via Marquee `EDRVOL_PERCENT` with `ric=AAPL.OQ` (2852 rows/day/symbol, 31 tenors x 49 strikes). Key: use `ric=` not `bbid=`.
- **Per-symbol variance swaps via `EDRVS`** with `ric=AAPL.OQ` (31 tenors/symbol/day). Clean VRP without jump contamination.
- Architecture: `IVSurfaceLayer` loads per-symbol parquets from `data/raw/iv/{symbol}.parquet`, applies shift(1), then `OptionsLayer` computes derived features from the merged columns.
- Market-wide signals (VVIX, iv_dispersion) are shared across all symbols via `_VVIX.parquet` and `_MARKET.parquet`.
- Legacy SPX-only Marquee path retained as fallback in `OptionsLayer._compute_from_context()`.

## Per-Symbol IV Field Reference (2026-05-28)

**TSDB pattern:** `edrvol_{ric}@{tenor}{strike}`

| Tenor | ATM (atms) | 25d put (25dp) | 25d call (25dc) | 5d put (5dp) | 5d call (5dc) |
|-------|-----------|----------------|-----------------|--------------|---------------|
| 1w | OK | OK (SPX) | OK (SPX) | -- | -- |
| 2w | OK | OK (SPX) | -- | -- | -- |
| 1m | OK | OK | OK | OK | OK |
| 2m | OK | -- | -- | -- | -- |
| 3m | OK | OK | OK | OK | OK |
| 6m | OK | OK | OK | OK | OK |
| 9m | OK | -- | -- | -- | -- |
| 1y+ | EMPTY | -- | -- | -- | -- |

**Known working RICs:** aapl.oq, msft.oq, nvda.oq, avgo.oq, googl.oq, meta.oq, nflx.oq, tsla.oq, adbe.oq, qqq.oq, spy.p, iwm.p, dia.p, bac.n, crm.n, hd.n, jnj.n, jpm.n, ma.n, pg.n, unh.n, v.n, xom.n, spx

## Additional Vol Indices Discovered (2026-05-28)

| Index | Symbol | History | Use |
|-------|--------|---------|-----|
| VVIX | `eqsp_s_.vvix@close` | 2016+ | Vol-of-vol (replace proxy) |
| RVX | `eqpad_.RVX@close` | 2015+ | Russell 2000 vol |
| VXN | `eqpad_.VXN@close` | 2015+ | Nasdaq 100 vol |
| GVZ | `eqpad_.GVZ@close` | 2015+ | Gold vol |
| VXEEM | `eqpad_.VXEEM@close` | 2015+ | EM vol |
| JNIV | `eqpad_.JNIV@close` | 2015+ | Nikkei vol |

## EDRVS_EXPIRY — 0DTE Variance Swap Strike (2026-06-05)

**Why this matters:** The GSVIVS01 signal compares IV against predicted RV to decide position. The original signal used ATM 0DTE IV, but GSVIVS01 sells a weighted OTM strip replicating a variance swap. The correct IV is the variance swap strike, which is always above ATM due to skew premium (empirically ~2-3 vol pts for SPX).

**Dataset:** `EDRVS_EXPIRY` (Marquee) — GS Equity Variance Swap Levels by Listed Expiry.
- **Columns:** `fairVariance` (vol%², e.g. 184.08), `fairVolatility` (vol%, e.g. 13.57), `expirationDate`, `bbid`
- **Coverage:** SPX (assetId `MA4B66MW5E27U8P32SB`), daily expiries Mon-Fri post-2022
- **Access:** Requires Marquee entitlement (was 403 Forbidden, now approved)
- **TSDB:** `edrvs_SPX@{tenor}` for tenor-based (1w shortest). No 0d/1d tenor exists.

**Implementation:**
- Fetcher: `edrvol.fetch_edrvs_0dte()` returns `pd.Series` named `"iv_vs_0dte"` = sqrt(fairVariance) in vol%
- Cache: `data/raw/iv/SPX_edrvs_0dte.parquet`
- CLI: `vol ingest-edrvs`
- Feature pipeline: `IVSurfaceLayer` loads cache, `OptionsLayer` uses for VRP when available
- Signal: `iv_tenor_for_horizon(1)` returns `"iv_vs_0dte"` (replaces `"iv_0dte_atm"`)

**Reconstruction fallback:** When EDRVS_EXPIRY unavailable, compute from EDRVOL_PERCENT_EXPIRY full strike chain via CBOE VIX discrete formula. Module: `data/varswap_reconstruct.py`. Caveat: at T=1/252 with sparse grid, numerical precision degrades; use T>=30/252 for stable results in tests.

**Key insight:** VRP = (iv_vs_0dte/100)^2 - rv*252 is tighter and more centered than ATM-based VRP. Days where var-swap strike drops near predicted RV are genuine danger zones for GSVIVS.

## "Knowable at 09:10" Contract for Signal-Time Proxies (2026-06-11)

**Principle:** A reverse-engineered IV proxy stays signal-time-valid if every
component is a deterministic function of (strip design x fee schedule x
pre-trade market data). Path-dependent components (anything that depends on the
realized intraday SPX trajectory) are out of contract.

**The strip itself is deterministic at 09:10.** Strike grid {K_i}, put/call
assignment, and replication weights |q_i| proportional to dK_i / K_i^2 are
mechanical outputs of the published GSVIVS rules -- not realized data.

**Inside the contract (safe to fold into Kvar):**
- Opening option fill prices (proxy for surface mids)
- Option TC: deterministic = strip notional x (commission + half-spread)
- Futures hedge TC: deterministic = |Delta_0| x ES_notional x per-clip TC bps
- Reading realized TCs from the ledger is equivalent to using an unbiased
  estimator of the expectation. Lower variance, same conditional mean, no
  lookahead.

**Outside the contract (NEVER fold in):**
- Realized ES hedge cash (path-dependent)
- Realized option close/expiry cash (= variance-swap payoff)
- Inverting Kvar from a bucket containing these collapses to
  K_realized^2 approximately RV^2 +/- (hedge tracking error)^2, making the
  IV-RV gap zero by identity. Beyond lookahead, this is mechanically circular.

**Current implementation:** `kvar_vol_pct` (full-friction strike) is maximally
informed within this contract. See
workspace/docs/gsvivs_exec_kvar_effective.md
for the full derivation.

**Generalization:** This contract applies to any future signal-time proxy
(surface-based Kvar, expected-TC variant, peer-strategy implied vols). Test:
"is this component a deterministic function of pre-trade information?" If yes,
include. If it depends on the realized path, exclude.

## LightGBM Underperformance -- Root Causes (2026-05-21)

### BUG: Calendar layer index type mismatch (FIXED)

`CalendarLayer.compute()` converted index to `pd.DatetimeIndex` but returned Timestamp-indexed DataFrame while other layers used `datetime.date`. `pd.concat(axis=1)` created a UNION instead of alignment, doubling rows from 2516 to 5032. Half had NaN calendar features, half had NaN for everything else. LightGBM trained on half-garbage matrix.

- Fix: `result.index = daily_data.index` after computing calendar features.
- Impact: LightGBM now gets 2515 clean rows per symbol in pooled mode.

### WEAKNESS: VRP used backward-looking RV, not HAR forecast (FIXED)

- Spec: VRP = IV^2 - E_t[RV_{t+1:t+22}] using HAR forecast.
- Was: VRP = IV^2 - rolling(22).mean(rv) * 252 (backward-looking).
- Fix: Generate HAR h=22 forecast in `build_iv_feature_panel`, use as E[RV].

### WEAKNESS: VVIX is a noisy realized proxy (RESOLVED 2026-05-28)

- Spec: VVIX index (implied vol of VIX options).
- Was: sqrt(252 * rolling(22).mean(log_ret_vix^2)) -- realized VIX vol.
- **FIX AVAILABLE:** `eqsp_s_.vvix@close` works in TSDB (2016+). Swap into fetch_vvix().
- Blocker removed. Previous 13 `eqpad_`/`mqd_` variants returned 500/403 but `eqsp_s_` namespace works.

### WEAKNESS: Missing rolling-window variants for key signals

- IV-RV gap, butterfly, term slope only have `_d` (daily level).
- Adding `_w` variants gives LightGBM smoother signals for splitting.

### GAP: Event-implied vol not implemented

- Calendar layer has fomc/nfp dummies but no implied vol decomposition.
- Priority: P3 (requires term structure interpolation around event dates).
