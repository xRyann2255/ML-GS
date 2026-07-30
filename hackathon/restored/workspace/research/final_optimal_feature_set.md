# Feature Catalog — Realized Volatility Forecasting

**Date:** 2026-06-01  
**Status:** Comprehensive audit of discovered data vs current feature set  
**Verdict:** Current pipeline uses ~128 features (trial-023). Cross-asset layer now wired (trial-031). Verified-accessible sources support 150–180+ features across 10 layers.

---

## Summary

| Layer | Name | Features (Impl / Avail) | Status | Priority |
|-------|------|------------------------|--------|----------|
| L0 | HAR Core + Measurement Quality | 5 / 5 | Complete | — |
| L1 | Asymmetric Volatility | 5 / 6 | Near-complete | — |
| L2 | Options-Implied | 9 / 25+ | Partial | P0–P1 |
| L3 | Microstructure | 0 / 20+ | All stubs | P1–P3 |
| L4 | Cross-Asset Spillovers | 9 / 18+ | **Wired (trial-031)** | P1–P2 |
| L5 | Calendar/Event | 8 / 15+ | Partial | P1–P2 |
| L6 | Long-Memory / Return-Activity | 4 / 8 | Partial | P3 |
| L7 | Correlation & Dispersion | 0 / 6 | NEW LAYER | P0 |
| L8 | Positioning & Sentiment | 0 / 4 | NEW LAYER | P3 |
| — | Tree Expansion | Working | Doubles base | — |

---

## Code Reality Check (Best Configs: trial-020/023)

Active layers (trial-023): `iv_surface` → `har_core` → `asymmetry` → `noise_robust` → `options` → `calendar` → `tree_expansion`  
Active layers (trial-031): `iv_surface` → `har_core` → `asymmetry` → `noise_robust` → `options` → `calendar` → `cross_asset` → `tree_expansion`  
Total active: **~128 features** (trial-023) / **~146+ features** (trial-031, base + 9 cross-asset + tree expansion of cross-asset)

| Layer | Code File | Status | In Best Config? |
|-------|-----------|--------|-----------------|
| L0: har_core | `har.py` | Working | YES |
| L1: asymmetry | `asymmetry.py` | Working (excl. leverage_ratio) | YES |
| L2: iv_surface + options | `iv_surface.py`, `options.py` | Working (per-symbol) | YES |
| L3: microstructure | `microstructure.py` | ALL STUBS (NotImplementedError) | NO |
| L4: cross_asset | `cross_asset.py` | Working, wired via tournament context | YES (trial-031) |
| L5: calendar | `calendar.py` | Working | YES |
| L6: long_memory | `long_memory.py` | Working (used in trial-014) | NO |
| noise_robust | `noise_robust.py` | Working | YES |
| tree_expansion | `tree_expansion.py` | Working | YES |

---

## Gap Analysis

| Category | Currently Implemented | Available (Verified Access) | Gap |
|----------|----------------------|----------------------------|-----|
| L0: HAR core | Working | Same | None |
| L1: Asymmetry | Working (excl. leverage_ratio) | Same | Minimal |
| L2: Options-implied | Per-symbol ATM + SPX surface | Per-symbol full surface (35 fields/sym) + variance swaps | Large |
| L3: Microstructure | ALL STUBS | LeeReady for all 34 symbols + BMLL L2 (2023+) | Large |
| L4: Cross-asset | 9 features wired (trial-031) | 22 Marquee datasets + ETF proxies | Medium (credit, ETF IV, interactions) |
| L5: Calendar/event | FOMC/NFP/OpEx implemented | + earnings IV, dividends, short interest | Medium |
| L6: Long-memory | Return/activity features (trial-023) | + frac diff, Hurst (derivable) | Small |
| L7: Correlation/Dispersion | Not in pipeline | EDR_INDEX_IMPLIEDCORR (10yr+) | NEW |
| L8: Positioning/Sentiment | Not in pipeline | FX positioning, risk barometer | NEW |

---

## Table of Contents

- [Layer 0 — HAR Core](#layer-0--har-core--measurement-quality)
- [Layer 1 — Asymmetric Volatility](#layer-1--asymmetric-volatility)
- [Layer 2 — Options-Implied](#layer-2--options-implied)
- [Layer 3 — Microstructure](#layer-3--microstructure)
- [Layer 4 — Cross-Asset Spillovers](#layer-4--cross-asset-spillovers)
- [Layer 5 — Calendar/Event](#layer-5--calendarevent)
- [Layer 6 — Long-Memory / Return-Activity](#layer-6--long-memory--return-activity)
- [Layer 7 — Correlation & Dispersion](#layer-7--correlation--dispersion)
- [Layer 8 — Positioning & Sentiment](#layer-8--positioning--sentiment)
- [Tree Expansion Layer](#tree-expansion-layer)
- [Priority Implementation Order](#priority-implementation-order)
- [Horizon-Specific Feature Rankings](#horizon-specific-feature-rankings)
- [Critical Interaction Effects](#critical-interaction-effects)

---

## Layer 0 — HAR Core + Measurement Quality

**5 features | Complete | Unchanged**

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| log_rv_d | log(RV_1d) | Tick data (Chunk Store EQ) | 2015-01-02 to 2024-12-31 (25 symbols cached) | Implemented | All |
| log_rv_w | log(RV_5d) | Tick data | 2015-01-02 to 2024-12-31 | Implemented | All |
| log_rv_m | log(RV_22d) | Tick data | 2015-01-02 to 2024-12-31 | Implemented | All |
| rq | (n/3) * sum(r^4) — Realized Quarticity | Tick data | 2015-01-02 to 2024-12-31 | Implemented | All |
| rq_interaction | sqrt(RQ) * RV_d | Derived | 2015-01-02 to 2024-12-31 | Implemented | All |

---

## Layer 1 — Asymmetric Volatility

**6 features | Near-complete (1 stub)**

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| rs_minus | sum(r^2 * 1{r<0}) — negative semivariance | Tick data (Chunk Store EQ) | 2015-01-02 to 2024-12-31 | Implemented | All |
| rs_plus | sum(r^2 * 1{r>0}) — positive semivariance | Tick data | 2015-01-02 to 2024-12-31 | Implemented | All |
| bpv | (pi/2) * sum(\|r_i\| * \|r_{i-1}\|) — bipower variation | Tick data | 2015-01-02 to 2024-12-31 | Implemented | All |
| jump_var | max(RV - BPV, 0) | Derived | 2015-01-02 to 2024-12-31 | Implemented | All |
| continuous_var | max(BPV, 0) | Derived | 2015-01-02 to 2024-12-31 | Implemented | All |
| leverage_ratio | rs_minus / (rs_minus + rs_plus) | Derived | 2015-01-02 to 2024-12-31 | **STUB** | All |

---

## Layer 2 — Options-Implied

**9 implemented / 25+ available | Largest expansion opportunity**

Critical gap: Original spec had 9 SPX-only features. Verified per-symbol IV access for all 25 equities (35 TSDB fields each + full surface via Marquee).

### 2A: Per-Symbol IV (via TSDB `edrvol_{ric}@{field}`)

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| atm_iv_1m | Direct read | `edrvol_{ric}@1matms` | 2010-01 to present (all 25 symbols) | **Implemented** | All |
| atm_iv_3m | Direct read | `edrvol_{ric}@3matms` | 2010-01 to present | Available | h=5, h=22 |
| atm_iv_1w | Direct read | `edrvol_{ric}@1watms` | 2010-01 to present | Available | h=1 |
| term_slope_1m3m | iv_3m - iv_1m | Derived | 2010-01 to present | **Implemented** | h=22 |
| term_slope_1w1m | iv_1m - iv_1w | Derived | 2010-01 to present | Available | h=1 |
| skew_25d | 25dp - 25dc | `edrvol_{ric}@1m25dp/1m25dc` | 2010-01 to present | Available | h=1 |
| butterfly_25d | 0.5*(25dp + 25dc) - atms | Derived | 2010-01 to present | Available | h=1 |
| deep_tail_premium | 5dp - 25dp | `edrvol_{ric}@1m5dp/1m25dp` | 2010-01 to present | Available | h=1 (tail) |
| iv_momentum | atm_1m - SMA(atm_1m, 5d) | Derived | 2010-01 to present | Available | h=1 |
| iv_acceleration | d(atm_iv)/dt (1-day change) | Derived | 2010-01 to present | Available | h=1 |

### 2B: VRP Features

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| vrp_har | atm_iv_1m - HAR_h22_forecast | Derived | 2015-01 to present (limited by RV) | **Implemented** | h=5, h=22 |
| vrp_varswap | varswap_fair_1m - RV_realized | **EDRVS dataset** (per-symbol) | 2015+ to present (31 tenors/day/symbol) | **Available** | h=5, h=22 |
| iv_rv_gap | atm_iv_1m - sqrt(252 * RV_22d) | Derived | 2015-01 to present | **Implemented** | All |

Key insight: Per-symbol variance swap VRP from EDRVS is model-free (market-implied expectation), unlike HAR-based VRP which is model-dependent. Strictly superior signal.

### 2C: VVIX and Vol-of-Vol

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| vvix | Direct read | `eqsp_s_.vvix@close` | 2016-06 to present | **Implemented** | h=22 (p=0.007) |
| vvix_change | d(VVIX)/dt | Derived | 2016-06 to present | **Implemented** | h=22 |
| vvix_zscore | (VVIX - SMA_22) / std_22 | Derived | 2016-06 to present | **Implemented** | h=22 |

### 2D: Earnings IV Premium

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| earnings_iv_premium | iv_nearest_expiry - iv_next_week_expiry | EDRVOL_PERCENT_EXPIRY | 2013-01-02 to present (all 25 symbols) | **Available** | h=1 (very strong) |

11.6pp IV gap confirmed for AAPL around earnings. Verified data-driven earnings proximity signal — no static file needed.

---

## Layer 3 — Microstructure

**0 implemented / 20+ available | All stubs**

Critical gap: Original spec assumed E-mini-only. LeeReady processor enables per-symbol features for ALL 34 symbols. BMLL provides full equity L2 from 2023+.

### 3A: All-Symbol via LeeReady (Chunk Store server-side)

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| signed_volume_ratio | buy_vol / (buy_vol + sell_vol) | `LeeReady` processor | 2014–2025 (~11.3 yrs, all 34 symbols) | Available | h=1 |
| vpin | abs(buy_vol - sell_vol) / total_vol (in volume buckets) | `LeeReadySumVolume` | 2014–2025 (all 34 symbols) | Available | h=1 |
| order_flow_imbalance | net_signed_vol / total_vol (daily) | `LeeReady` aggregated | 2014–2025 (all 34 symbols) | Available | h=1 |
| odd_lot_ratio | odd_lot_trades / total_trades | `COND_CODE` field filtering | 2014–2025 (all 34 symbols) | Available | h=1 |
| auction_volume_ratio | auction_vol / total_vol | `MMTFlags` processor | 2014–2025 (all 34 symbols) | Available | h=1 |

### 3B: E-mini L2 Features (stubs)

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| price_acceleration | log-return-of-log-return | E-mini L2 tick data | 2020+ (STS Prod store) | STUB | h=1 |
| obi | (bid_size - ask_size) / sum | E-mini L2 depth (5 levels) | 2020+ (STS Prod store) | STUB | h=1 |
| depth_ratio | total_bid_size / total_ask_size | E-mini L2 depth | 2020+ (STS Prod store) | STUB | h=1 |
| spread_dynamics | time-weighted spread | E-mini L1 quotes | 2014–2025 (Chunk Store EQ) | STUB | h=1 |
| sub_window_rv_ratio | RV(first_hour) / RV(last_hour) | E-mini tick data | 2014–2025 (Chunk Store EQ) | STUB | h=1 |

### 3C: BMLL Full-Depth Equity (2023+ only)

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| depth_imbalance_5lvl | (bid_qty_1:5 - ask_qty_1:5) / sum | BMLL L2 Quotes (Snowflake) | 2023-01-01 to present | Available | h=1 |
| hidden_liquidity | volume beyond BBO / BBO volume | BMLL L2 Quotes | 2023-01-01 to present | Available | h=1 |
| price_impact_1min | markout return after aggressive trade | BMLL Trades Plus | 2023-01-01 to present | Available | h=1 |
| resting_time | avg time orders sit at each level | BMLL Analytics (ANA) | 2023-01-01 to present | Available | h=1 |
| auction_imbalance | open/close auction order imbalance | BMLL IMB data | 2023-01-01 to present | Available | h=1 |

Constraint: BMLL data starts 2023-01-01. Useful for recent training, not full history.

### 3D: OPRA Options Flow

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| put_call_ratio | put_volume / call_volume (daily) | Chunk Store `OPRA` database | Unknown start to present (unverified depth) | Available (unverified) | h=1 |
| options_volume_surprise | today_vol / SMA_20(vol) | OPRA ticks | Unknown start to present | Available (unverified) | h=1 |

---

## Layer 4 — Cross-Asset Spillovers

**9 features IMPLEMENTED and WIRED (trial-031) | 18+ available total**

The core cross-asset features are now live: treasury slope (d/w), FX vol (d/w), commodity vol, VIX level (d/w/m), VIX/RV ratio, DY spillover. Tournament context loader (`_build_tournament_context`) loads `data/raw/cross_asset/` parquets automatically when `cross_asset` is in `feature_layers`. Data ingested via `vol ingest-xasset` (rates, fx_vol, commodity, credit parquets).

**Implemented features (from `cross_asset.py`):**
| # | Feature | Formula | Source | Status |
|---|---------|---------|--------|--------|
| 1 | `treasury_slope_d` | 10Y yield - 5Y yield | rates.parquet | Implemented |
| 2 | `treasury_slope_w` | rolling(5d) mean of slope | rates.parquet | Implemented |
| 3 | `log_fx_vol_d` | log(realized_vol(FX, 22d)) | fx_vol.parquet | Implemented |
| 4 | `log_fx_vol_w` | rolling(5d) mean of log FX vol | fx_vol.parquet | Implemented |
| 5 | `log_commodity_vol_cl_d` | log(OVX) or log(realized_vol(CL)) | commodity.parquet | Implemented |
| 6 | `log_vix_d` | log(VIX) | IV cache (_VIX.parquet) | Implemented |
| 7 | `log_vix_w` | rolling(5d) mean of log VIX | IV cache | Implemented |
| 8 | `log_vix_m` | rolling(22d) mean of log VIX | IV cache | Implemented |
| 9 | `log_vix_rv_ratio_d` | log((VIX/100)^2 / (RV*252)) | Derived | Implemented |
| — | `dy_spillover_d` | DY (2012) total connectedness | rv_panel (not yet wired) | Available |

**Note:** `credit.parquet` is ingested and loaded into context but `CrossAssetLayer.compute()` does not yet consume it. Credit features require adding a `credit` branch to the layer.

### 4A: Cross-Asset Implied Volatility (Marquee)

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| fx_vol_usdjpy | ATM 1m USDJPY vol | FXIMPLIEDVOL_PREMIUM | ~2010+ to present (60 FX pairs) | **Implemented** (realized proxy via `fx_vol.parquet`) | h=5, h=22 |
| fx_vol_eurusd | ATM 1m EURUSD vol | FXIMPLIEDVOL_PREMIUM | ~2010+ to present | Available (implied; realized ingested) | h=5, h=22 |
| rate_vol_1y10y | 1y into 10y swaption vol | IR_SWAPTION_VOLS_STANDARD | 2010+ to present (336 instruments) | Available | h=22 |
| commodity_vol_cl | WTI crude ATM vol | COMMODVOL_STANDARD | Unknown start to present | Available | h=5, h=22 |
| credit_vol_cdx | CDX.NA.IG ATM vol | CDSIVOL | Unknown start to present (5 CDS indices) | Available | h=22 |

### 4B: Yield Curve and Rates

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| yield_slope_10y5y | 10Y - 5Y yield | `data/raw/cross_asset/rates.parquet` | 2013+ to present | **Implemented** (`treasury_slope_d/w`) | h=22 |
| yield_level_10y | 10Y yield | `data/raw/cross_asset/rates.parquet` | 2013+ to present | Ingested (not yet a feature) | h=22 |
| yield_slope_change | d(slope)/dt | Derived | 2013+ to present | Available (via tree_expansion `_change`) | h=22 |
| rate_level_ir | 10y swap rate (cleaner) | IR_SWAP_RATES_STANDARD | 2010+ to present (230 instruments) | Available | h=22 |

### 4C: ETF Proxies

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| gold_vol | RV(GLD) or GVZ | `eqpad_GLD.P` / `eqpad_.GVZ@close` | GLD: 2013+ / GVZ: 2015+ | Available | h=22 |
| oil_vol | OVX (implied) or RV(USO) | `commodity.parquet` (OVX field) | 2015+ | **Implemented** (`log_commodity_vol_cl_d`) | h=22 |
| credit_stress | HYG returns (credit spread proxy) | `credit.parquet` (ingested) | 2013+ to present | Ingested, not consumed by layer | h=22 |
| dollar_strength | DXY level or change | `eqsp_s_.dxy@close` | 2013+ to present | Available | h=22 |
| em_risk | EEM returns | `eqpad_EEM.P` | 2013+ to present | Available | h=5, h=22 |

### 4D: Cross-Asset IV via edrvol (ETF IV)

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| hyg_iv | HYG 1M ATM implied vol | `edrvol_hyg.p@1matms` | 2010+ to present | Available | h=22 (credit) |
| gld_iv | GLD 1M ATM implied vol | `edrvol_gld.p@1matms` | 2010+ to present | Available | h=22 (safe haven) |
| eem_iv | EEM 1M ATM implied vol | `edrvol_eem.p@1matms` | 2010+ to present | Available | h=5, h=22 |
| xlf_iv | XLF 1M ATM implied vol | `edrvol_xlf.p@1matms` | 2010+ to present | Available | h=1 (financials) |

---

## Layer 5 — Calendar/Event

**8 implemented / 15+ available**

### 5A: Implemented

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| days_to_fomc | Days until next FOMC | Static list (hardcoded 2015–2026) | Full coverage | Implemented | All |
| fomc_week | Binary: FOMC this week | Static list | Full coverage | Implemented | All |
| fomc_day | Binary: FOMC today | Static list | Full coverage | Implemented | All |
| days_to_nfp | Days until next NFP | Rule-based (first Fri of month) | Full coverage | Implemented | All |
| nfp_week | Binary: NFP this week | Rule-based | Full coverage | Implemented | All |
| days_to_opex | Days until next OpEx | Rule-based (3rd Fri of month) | Full coverage | Implemented | All |
| opex_week | Binary: OpEx this week | Rule-based | Full coverage | Implemented | All |
| day_of_week | Weekday encoding | DatetimeIndex | Full coverage | Implemented | All |
| month | Month encoding | DatetimeIndex | Full coverage | Implemented | All |
| quarter_end | Binary: quarter-end | DatetimeIndex | Full coverage | Implemented | All |
| year_end | Binary: year-end | DatetimeIndex | Full coverage | Implemented | All |

### 5B: Available (Not Implemented)

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| earnings_iv_premium | nearest_expiry_iv - next_week_iv | EDRVOL_PERCENT_EXPIRY | 2013-01-02 to present | Available | h=1 (strongest event) |
| days_to_exdiv | Proximity to ex-dividend | `eqpad_{RIC}@div` (25/30 confirmed) | 2015–2025 (25/30 symbols) | Available | h=1 |
| short_interest_change | d(short_interest)/dt | `eqpad_{RIC}@shortint` | 2015–2025 (30/30 symbols) | Available | h=1 (tail event) |
| fed_rate_level | Current FFTQ value | TSDB `FFTQ` | 2015–2025 (daily) | Available | h=22 (regime) |
| fed_rate_change_1m | Rate delta last 30d | Derived from FFTQ | 2015–2025 | Available | h=22 |
| is_quarterly_opex | month in {3,6,9,12} | Rule-based | Full coverage | Trivial to add | h=1 |
| holiday_proximity | Days to 3-day weekend | trading_calendar.py | Full coverage | Trivial to add | h=1 |

---

## Layer 6 — Long-Memory / Return-Activity

**4 implemented / 8 available**

### 6A: Memory Features (not implemented)

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| frac_diff_rv | (1-L)^d RV, d~0.35 | Derived from RV | 2015-01-02 to 2024-12-31 (derivable) | Not implemented | h=22 |
| rolling_hurst | Hurst exponent (22d window) | Derived from RV | 2015-01-02 to 2024-12-31 (derivable) | Not implemented | h=22 |
| vol_of_vol | std(RV_d) over 22d | Derived from RV | 2015-01-02 to 2024-12-31 (derivable) | Not implemented | h=5, h=22 |
| regime_duration | Days since last 2-sigma spike | Derived from RV | 2015-01-02 to 2024-12-31 (derivable) | Not implemented | h=22 |

### 6B: Return/Activity Features (trial-023 — NEW BEST)

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| abs_ret_w | abs(5d return) | OHLCV | 2015-01-02 to 2024-12-31 | **Implemented** | h=1 (+149 bps) |
| abs_ret_d | abs(1d return) | OHLCV | 2015-01-02 to 2024-12-31 | **Implemented** | h=5, h=22 |
| ret_5d | Signed 5d return | OHLCV | 2015-01-02 to 2024-12-31 | **Implemented** | h=5, h=22 |
| vol_anomaly | RV_d / SMA(RV_d, 22) | Derived from RV | 2015-01-02 to 2024-12-31 | **Implemented** | All |

---

## Layer 7 — Correlation & Dispersion

**0 implemented / 6 available | ENTIRELY NEW LAYER**

Verified via Marquee with 10+ years of history. Correlation spikes precede vol spikes (systemic risk channel). Potentially highest-priority missing layer for monthly horizon. Requires verification against De Nard et al. (2021) and Buss & Vilkov (2012) for construction methodology.

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| implied_corr_spx_1m | SPX 1m implied correlation | EDR_INDEX_IMPLIEDCORR | 2010+ to present | Available | h=22 (regime) |
| realized_corr_spx_1m | SPX 1m realized correlation | EDR_INDEX_REALIZEDCORR | 2010+ to present | Available | h=22 |
| corr_risk_premium | implied_corr - realized_corr | Derived | 2010+ to present (derivable) | Available | h=22 (systemic risk) |
| dispersion_signal | index_iv - avg(single_stock_iv) | EDR_INDEX_AVG_IMPLIED_VOL + EDRVOL | 2010+ to present | Available | h=22 |
| corr_momentum | d(implied_corr)/dt | Derived | 2010+ to present (derivable) | Available | h=5, h=22 |
| corr_zscore | (impl_corr - SMA_60) / std_60 | Derived | 2010+ to present (derivable) | Available | h=22 |

---

## Layer 8 — Positioning & Sentiment

**0 implemented / 4 available | ENTIRELY NEW LAYER**

Cross-sectional regime signals. Unlikely to help much in pooled per-symbol training but may add value at h=22 where regime detection is critical. Low priority until higher layers are verified and tested.

| Feature | Formula | Source | Dates | Status | Horizon |
|---------|---------|--------|-------|--------|---------|
| fx_positioning_jpy | Speculative positioning USDJPY | FX_POSITIONING_DAILY | Verified (dates unspecified) | Available | h=5, h=22 |
| risk_barometer | Composite risk indicator | EQUITY_RISK_BAROMETER_V1_STANDARD | Verified (dates unspecified) | Available | h=22 |
| social_sentiment | Economic sentiment index | GS_SOCIAL_MEDIA_ECONOMIC_SENTIMENT | Verified (dates unspecified) | Available | h=22 |
| equity_risk_premium | SPX ERP level | EQUITY_RISK_PREMIUM_INDEX | Verified (dates unspecified) | Available | h=22 |

---

## Tree Expansion Layer

Applied to all base features in L0–L4. For each base quantity, compute:
- `{feature}_change` = feature[t] - feature[t-1]
- `{feature}_zscore` = (feature[t] - SMA_22) / std_22

This doubles the effective feature count. Currently implemented for ~70 features. With expanded base features, could reach 200+ total inputs. Status: **Working** (proven +31.5 bps in trial-009).

---

## Priority Implementation Order

| Priority | Feature Group | Effort | Data Verified? |
|----------|--------------|--------|----------------|
| **P0** | Per-symbol variance swap VRP (EDRVS) | Low | YES |
| **P0** | Implied correlation + CRP (EDR_INDEX_IMPLIEDCORR) | Low | YES |
| **P1** | Per-symbol skew/butterfly/term (edrvol_ TSDB) | Low | YES |
| ~~P1~~ | ~~Cross-asset vol spillover (FX, rates, credit, commodity)~~ | ~~Low-Medium~~ | **DONE (trial-031)** |
| **P1** | LeeReady signed volume + VPIN (all 34 symbols) | Low | YES (server-side) |
| **P1** | Earnings IV premium signal (EDRVOL_PERCENT_EXPIRY) | Medium | YES |
| **P2** | Cross-asset IV (HYG, GLD, EEM, XLF via edrvol_) | Low | YES |
| **P2** | Fed rate regime features (FFTQ) | Low | YES |
| **P2** | Short interest change proxy | Low | YES |
| **P2** | Dividend proximity | Low | YES |
| **P3** | BMLL equity L2 depth features (2023+ only) | Medium-High | YES (2023+ only) |
| **P3** | OPRA options put/call ratio | Medium | Partially verified |
| **P3** | Long-memory features (frac diff, Hurst) | Medium | Derivable |
| **P3** | Positioning/sentiment signals | Low | YES |

**Reminder:** Each feature requires passing the Formula Verification Gate (see `data-ingestion-architecture.md`) before implementation.

---

## Horizon-Specific Feature Rankings

### h=1 (daily) — Microstructure + return activity + event proximity

| Rank | Feature | Layer |
|------|---------|-------|
| 1 | abs_ret_w (smoothed absolute return) | L6 |
| 2 | LeeReady VPIN (all symbols) | L3 |
| 3 | Earnings IV premium | L2/L5 |
| 4 | Per-symbol skew + butterfly | L2 |
| 5 | OPRA put/call ratio | L3 |
| 6 | BMLL depth imbalance | L3 |

### h=5 (weekly) — VRP + cross-asset vol + momentum

| Rank | Feature | Layer |
|------|---------|-------|
| 1 | Per-symbol varswap VRP (EDRVS) | L2 |
| 2 | Cross-asset vol (FX, rates, credit) | L4 |
| 3 | Per-symbol term slope (multitenor) | L2 |
| 4 | Correlation momentum | L7 |
| 5 | EEM/FXI implied vol | L4 |

### h=22 (monthly) — Correlation + regime + macro

| Rank | Feature | Layer |
|------|---------|-------|
| 1 | Implied correlation + CRP | L7 |
| 2 | VVIX (proven, p=0.007 in trial-011) | L2 |
| 3 | Per-symbol varswap VRP | L2 |
| 4 | Cross-asset vol spillover | L4 |
| 5 | Fed rate regime | L5 |
| 6 | Dispersion signal | L7 |
| 7 | Equity risk premium | L8 |

---

## Critical Interaction Effects

Based on experimental evidence from trials 009–023:

1. **Variance swap VRP × per-symbol IV** — VRP from market-implied expectations (EDRVS) interacted with current IV level should be stronger than model-based VRP × IV.
2. **Implied correlation × VIX level** — When VIX is high AND correlation is rising, vol spikes are systemic (not idiosyncratic). Should dominate h=22.
3. **LeeReady VPIN × IV skew** — When informed flow (VPIN > 0.7) coincides with extreme put skew, next-day vol spike probability is very high.
4. **Earnings IV premium × abs_ret_w** — Smoothed return activity + elevated IV premium should compound the earnings event signal.
5. **Cross-asset vol (credit/rates) × per-symbol beta** — Market-wide vol signals only work in pooled training when interacted with per-symbol characteristics (proven: pure market-wide features HURT).

### Architecture Decision: Feature Interaction Strategy

- Trees find per-symbol interactions (IV × RV, VVIX × RV) well
- Trees CANNOT find cross-layer interactions requiring temporal memory (tree_expansion proved +31.5 bps in trial-009)
- Market-wide features MUST be interacted with per-symbol data before entering the model (pure market-wide hurts)

**Pre-computation rules:**
1. Cross-asset vol features × per-symbol beta → `fx_vol_x_beta`, `credit_vol_x_beta`
2. Correlation features × sector dummy → `implied_corr_x_tech`, `implied_corr_x_finance`
3. All base features → tree_expansion (change + zscore) → doubles dimensionality but trees prune unused
