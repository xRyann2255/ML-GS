# ISG OptionMetrics / Quantum API — Comprehensive Data Source Audit

**Date:** 2026-07-06
**Entitlement:** `isg-marketdata-accessor` (permitResource: `isg-marketdata-accessor`)
**Status:** Access granted — probing required to determine working access paths

---

## 1. Data Source Overview

**Vendor:** OptionMetrics (IvyDB product family)
**Internal owner:** ISG (Investment Strategy Group) via PWM Quantum platform
**Coverage:** US, APAC, EU options data (we need IVYUS — SPX/SPY)
**History:** 1996–present (daily EOD frequency)
**Update cadence:** Daily (T+1), with patch files for historical corrections

### What OptionMetrics IvyDB Contains (per the vendor schema)

| Table | Content | Relevance to Us |
|-------|---------|-----------------|
| **OPTION_PRICE** | Per-strike daily: bid, ask, mid, volume, OI, IV, delta, gamma, vega, theta | **PRIMARY** — GEX, dealer gamma, put-call ratios |
| **SECURITY_PRICE** | Underlying daily: close, high, low, volume, returns | Useful for join/validation |
| **SECURITY_METADATA** | Security master: ticker, CUSIP, exchange, option type | Reference data for filtering |
| **IVYOPTOI** | Dedicated open interest file (US) | **PRIMARY** — per-strike OI for GEX |
| **DIVIDEND** | Dividend history | Greeks computation accuracy |
| **DISTRIBUTION** | Distributions/splits | Adjustment factor |
| **ZERO_COUPON** | Yield curve (for risk-free rate in BS) | Greeks computation |

---

## 2. Access Paths (3 routes, ordered by preference)

### Path A: TSDB `ivyt_` Namespace (Sybase → TSDB bridge)

**Status:** Requires `equities.volprop` UDB entitlement (separate from `isg-marketdata-accessor`)

| Property | Value |
|----------|-------|
| Symbol pattern | `ivyt_{TICKER}@{modifier}` |
| Example | `ivyt_OXY@impliedvol.1m.50c` |
| SymbolTable | NYIVYP05 (Production), NYIVYP03 (Backup) |
| Driver | `ctsql` (Sybase) |
| Entitlement | `equities.volprop` (UDB) |
| QSAR library | `_LIB QSAR OptionMetrics` |

**Known modifiers (from Ivy FDS page):**
- `impliedvol.{tenor}.{delta}{type}` — e.g., `impliedvol.1m.50c`, `impliedvol.1m.25p`

**What we need to discover:**
- Modifier pattern for OI: `openinterest.{expiry}` or `oi.{strike}` ?
- Modifier pattern for Greeks: `gamma.{tenor}.{delta}` ?
- Whether per-strike data is exposed via TSDB at all (likely aggregate only)

**QSAR access (alternative to TSDB):**
```
Link("_LIB QSAR OptionMetrics");
data = @QSAR::OptionMetrics Get Option Price(Date("25Jun26"), ["57904"])
```
The `"57904"` is a securityId from the OptionMetrics security master.

### Path B: Quantum API / HDFS / HIVE (Full per-strike data)

**Status:** `isg-marketdata-accessor` entitlement should cover this path.

| Property | Value |
|----------|-------|
| HDFS paths (PROD) | `/appdata/99461_qis_bigdata/data/store/option_metrics` |
| | `/appdata/99461_qis_bigdata/data/store/level_2/option_metrics` |
| | `/appdata/99461_qis_bigdata/data/store/gdd_csi_options_isg` |
| HDFS paths (UAT) | `/appdata/99461_qis_bigdata/data/store/uat/option_metrics` |
| | `/appdata/99461_qis_bigdata/data/store/uat/level_2/option_metrics` |
| HIVE principal | `dchive/d440120-002.dc.gs.com@GS.COM` |
| Kerberos realm | `GS.COM` |
| KrbHostFQDN | `d440120-002.dc.gs.com` |
| KrbServiceName | `p2epda` |
| HDFS NameNode | `http://d440120-002.dc.gs.com:50070` |
| GitLab repo | `pwm/pwm-quantum-product-portfolio/pwm-quantum-external-data-adapter` |
| Python script | `optionMetricsQuantumApiProcessor.py` |
| Product key | `'108105'` |

**Quantum API datasets (Python enum):**
```python
OptionMetricsBatchDataIngestionDatasets.OPTION_PRICES
OptionMetricsBatchDataIngestionDatasets.SECURITY_PRICES
OptionMetricsBatchDataIngestionDatasets.SECURITY_METADATA
```

**NRT Flow URLs (production):**
- V5: `https://prod.neartime.quantum.url.gs.com/Quantum/OPTION_METRICS_V5_DAP_FLOW/status`
- V6: `https://prod.neartime.quantum.url.gs.com/Quantum/OPTION_METRICS_V6_DAP_FLOW/status`
- GI: `https://prod.neartime.quantum.url.gs.com/Quantum/OPTION_METRICS_GI_DAP_FLOW/status`

**Data versions:**
- V5 model → version 3
- V6 model → version 4
- GI (Global/International) → version 3

**Architecture:**
```
Vendor FTP → SFX Mirror → Netra (Level 1, owned by QIS)
    → Level 2 + Data Storage + QSP Services (owned by Quantum)
        → HDFS parquet / MemSQL
            → PrestoDB queryable
```

### Path C: Sybase Direct (GIR/FDS team infrastructure)

**Status:** Separate infrastructure from Quantum. Used by GIR calculations.

| Property | Value |
|----------|-------|
| Prod servers | NYIVYP05 (Primary), NYIVYP03 (Backup) |
| QA server | NYIVYD01 |
| Version | Prod/Backup = Ivy 5.0; QA = Ivy 6.0 |
| Procmon jobs | `gir/NYC/Ivy/d` |
| SFX Mirror job | `eqpad/mirror/SFXMirroringClone~ivydb_gs3_sfx` |
| Data path | `/data/eq/pad_data12/SFX_MIRROR/EP_RPG_DATA/rpg_data_pull/ivydb_gs3/` |
| IT support DL | `gs-am-qis-data-support` |
| Quantum support DL | `gs-pwm-quantum-isg-support` |

**Vendor file patterns (IVYUS v5.0):**
- Daily update: `IVYDB.yyyymmddD.zip` at `/IvyDBUS/v5.0/Update/`
- Patch: `ptcivydb.yyyymmdd.zip` at `/IvyDBUS/v5.0/Patch/`
- Open Interest: `IVYOPTOI.yyyymmddD.zip` at `/IvyDBUS/v3.1/OpenInterest/`

---

## 3. Schema: OPTION_PRICE Table (Primary Target)

Based on OptionMetrics IvyDB v5/v6 documentation and the Quantum API page:

| Column | Type | Description | Feature Use |
|--------|------|-------------|-------------|
| `securityId` | int | OptionMetrics security ID | Join key |
| `date` | date | Observation date | Time index |
| `expirationDate` / `expiration` | date | Option expiry | Tenor bucketing |
| `strike` | float | Raw strike price | GEX computation |
| `strikeAdjusted` | float | Adjusted strike (÷1000 for index, ÷100 for equity) | Moneyness |
| `isPut` | bool | Put flag | Call/put split |
| `optionType` | str | From IssueType in Security Metadata | Filtering |
| `bid` | float | Bid price | Spread features |
| `ask` | float | Ask price | Spread features |
| `volume` | int | Daily trading volume | Volume features |
| `openInterest` | int | **Open interest** | **GEX PRIMARY INPUT** |
| `impliedVolatility` | float | OptionMetrics IV | IV surface features |
| `delta` | float | Option delta | GEX sign convention |
| `gamma` | float | **Option gamma** | **GEX PRIMARY INPUT** |
| `vega` | float | Option vega | Vanna features |
| `theta` | float | Option theta | Decay features |
| `underlierSecurityId` | int | Underlying security ID | SPX filter |
| `underlierSecurityTicker` | str | Underlying ticker | SPX filter |
| `underlierSecurityCusip` | str | Underlying CUSIP | Join key |
| `optionId` | int | Vendor option ID | Dedup |
| `ric` | str | Reuters Instrument Code | Cross-reference |
| `symbol` | str | Vendor-provided symbol | Human-readable |
| `expirationCycle` | str | Weekly/monthly/quarterly | Expiry classification |
| `dataSourceName` | str | Feed identifier | Provenance |
| `frequency` | str | Data frequency | Validation |

---

## 4. Features Extractable for Vol Forecasting

### 4.1 Dealer Gamma / GEX (PRIMARY TARGET)

**Formula:**
$$\text{GEX}_{\text{net}} = \sum_K \left[ -\text{OI}_{K,\text{call}} \cdot \Gamma_{K,\text{call}} + \text{OI}_{K,\text{put}} \cdot \Gamma_{K,\text{put}} \right] \times 100 \times S$$

**Features derivable:**

| Feature | Description | Mechanism |
|---------|-------------|-----------|
| `gex_sign_d` | Sign of net GEX (+1/-1) | Long gamma suppresses vol; short amplifies |
| `gex_zscore_d` | Z-score of net GEX (63-day rolling) | Magnitude of positioning imbalance |
| `gex_quintile_d` | Rolling quintile rank (252-day) | Relative positioning |
| `gex_regime_d` | Binary: 1=long gamma, 0=short gamma | Regime feature |
| `gex_momentum_d` | 5-day change in GEX z-score | Positioning flow |
| `gex_flip_count_w` | Number of sign flips in trailing week | Instability indicator |
| `gex_concentration_d` | Herfindahl of gamma across strikes | How concentrated is dealer risk |

### 4.2 Open Interest Features

| Feature | Description | Mechanism |
|---------|-------------|-----------|
| `oi_total_d` | Total SPX OI (calls + puts) | Market depth proxy |
| `oi_pcr_d` | Put/Call OI ratio | Sentiment/hedging demand |
| `oi_pcr_change_5d` | 5-day change in PCR | Flow direction |
| `oi_near_atm_d` | OI concentration within ±2% of spot | Pin risk magnitude |
| `oi_max_strike_dist_d` | Distance (%) from spot to max-OI strike | Magnetic strike |
| `oi_weighted_strike_d` | OI-weighted average strike / spot | Center of gravity |
| `oi_skew_d` | Put OI / Call OI in OTM region | Tail hedging demand |
| `oi_term_slope_d` | Near-term OI / Far-term OI | Positioning horizon |
| `oi_weekly_pct_d` | Weekly expiry OI / Total OI | 0-DTE activity |

### 4.3 Volume Features

| Feature | Description | Mechanism |
|---------|-------------|-----------|
| `vol_pcr_d` | Put/Call volume ratio | Intraday sentiment |
| `vol_oi_ratio_d` | Volume / OI ratio | Turnover intensity |
| `vol_atm_share_d` | ATM volume / total volume | Hedging vs speculation |
| `vol_0dte_share_d` | 0-DTE volume / total | Short-dated activity |

### 4.4 IV Surface Features (from per-strike IV)

| Feature | Description | Mechanism |
|---------|-------------|-----------|
| `iv_skew_25d_d` | 25Δ put IV - 25Δ call IV | Tail risk pricing |
| `iv_butterfly_d` | 25Δ avg - ATM IV | Wing demand |
| `iv_term_slope_d` | 1M IV - 1W IV | Term structure steepness |
| `iv_atm_d` | ATM IV level | Baseline fear gauge |
| `iv_smile_slope_d` | dIV/dK at ATM | Local skew |
| `iv_rr_10d_change_d` | 10-day change in risk reversal | Skew momentum |

### 4.5 Greeks-Derived Positioning Features

| Feature | Description | Mechanism |
|---------|-------------|-----------|
| `vanna_exposure_d` | Net vanna across strikes × OI | Spot-vol correlation sensitivity |
| `charm_exposure_d` | Net charm across strikes × OI | Time decay of delta hedging |
| `volga_indicator_d` | Concentration of OI at high-vega strikes | Kurtosis positioning |
| `pin_strike_d` | Distance to nearest high-OI strike (days to expiry < 5) | Pin risk proximity |
| `delta_imbalance_d` | Net dealer delta from options | Directional hedge flow |

### 4.6 Cross-Asset Dealer Positioning

| Feature | Description | Mechanism |
|---------|-------------|-----------|
| `gex_spy_vs_spx_d` | SPY GEX / SPX GEX ratio | Retail vs institutional positioning |
| `oi_spy_spx_ratio_d` | SPY OI / SPX OI ratio | Retail participation |

---

## 5. Priority Ranking for Implementation

| Priority | Feature Group | Data Required | Expected Signal Strength |
|----------|--------------|---------------|--------------------------|
| **P0** | GEX sign + z-score | OI + Gamma per strike | Strong — academic evidence (Bennett 2014, Healy 2020) |
| **P1** | OI put-call ratio + changes | OI per strike | Moderate — sentiment proxy |
| **P1** | Pin risk (max-OI distance) | OI + strike proximity | Moderate — mechanical at expiry |
| **P2** | Vanna exposure | Vega + Delta + OI per strike | Novel — untested in HAR-X |
| **P2** | IV skew from per-strike IV | Per-strike IV | Incremental over EDRVOL |
| **P3** | Volume ratios | Volume per strike | Weak alone, useful in interaction |
| **P3** | Charm/decay exposure | Theta + OI | Slow-moving, likely redundant |

---

## 6. Access Verification Results (2026-07-07)

### Path D: Quantum QSP REST API — VERIFIED WORKING (PRIMARY)

| Property | Value |
|----------|-------|
| Base URL | `https://pwm.qsp.url.gs.com:7070/quantumServicePortal/rest/api/{endpoint}/4` |
| Auth | GSSSO cookie (`authn.web.gs.com` → `.gs.com` domain) |
| SPY securityId | `109820` (American exercise, CUSIP 78462F10, equity ETF) |
| SPX securityId | `108105` (European-style, cash-settled, indexFlag=1, issueType=A, CBOE S&P 500 INDEX) |
| Records/day | ~14K contracts, ~9.6K with valid gamma + OI |
| Pagination | `scrollId` cursor, page size 30K |
| Timeout needed | 120s (some queries are slow) |
| Invalid marker | `-99.99` for gamma/delta/vega/theta = not computed |

**Verified endpoints (2026-07-07):**

| Endpoint | Status | Response |
|----------|--------|----------|
| `OptionPrices` | ✅ 200 | Full per-strike chain: gamma, delta, vega, theta, OI, IV, volume, strike, callPut, expiration |
| `OptionMetricsSecurityTimeseries` | ✅ 200 | Spot close ($746.77 on 2026-06-30), volume, shares outstanding |
| `OptionMetricsSecurityMeta` | ✅ 200 | Ticker→securityId resolution (SPY→109820) |
| `OpenInterest` | ✅ 200 | Dedicated OI by optionSymbol |

**GEX computation validated (2026-06-30 data):**
- Net dealer GEX: $2.1M
- Gamma flip zone: $735-$750
- Top GEX strike: $750 (+$1.5M)
- Call GEX: $24.8M, Put GEX: $22.7M

**Strike format:** milli-dollars (e.g., 680000 = $680.00)

**This is now the PRIMARY access path.** It provides everything needed for GEX without requiring additional entitlements.

### Legacy Paths (superseded)

#### Verified from GS Desktop (LDN)

| Path | Result | Details |
|------|--------|---------|
| **TSDB `ivyt_`** | 403 | Missing `equities.volprop` UDB entitlement |
| **HiveServer2 (10000)** | REFUSED | Port firewalled from LDN desktop subnet |
| **Hive Metastore (9083)** | Open | Requires SASL auth (not tested further) |
| **WebHDFS (50070)** | **WORKING** | SPNEGO/Kerberos auth via `FIRMWIDE.CORP.GS.COM` realm |
| **HDFS RPC (8020)** | Open | Needs libhdfs (not available) |

### What We Can Read (via WebHDFS)

| Table | Content | Access | Use for GEX? |
|-------|---------|--------|--------------|
| **IVYOPVOL** | Per-SecurityID daily OI + Volume | ✅ Full read | **PRIMARY** — OI weights |
| **IVYIDXDV** | Index dividend yields | ✅ Full read | BS Greeks computation |
| **IVYZEROC** | Zero coupon rate curve | ✅ Full read | Risk-free rate for BS |

### What We Cannot Read (ACL denied)

| Table | Content | Needed for |
|-------|---------|------------|
| IVYOPPRC | Option prices + strike + expiry | Per-strike identification |
| IVYSTDOP | Standardized options + Greeks | Pre-computed delta/gamma |
| IVYVSURF | Volatility surface | IV per strike |
| IVYSECPR | Security prices | Underlying spot |
| IVYHVOL | Historical volatility | Validation |
| IVYFWDPR | Forward prices | Greeks accuracy |

### Tables with Different Partition Scheme (need exploration)

| Table | Content | Directory listing | File read |
|-------|---------|-------------------|-----------|
| IVYOPINF | Option info (strike, expiry mapping) | ✅ 2021-2026 | 404 (wrong path) |
| IVYSECUR | Securities master | ✅ 2021-2026 | 404 (wrong path) |
| IVYSECNM | Security names | ✅ 2021-2026 | 404 (wrong path) |

### Entitlements Status

| Entitlement | Covers | Status |
|-------------|--------|--------|
| `isg-marketdata-accessor` | WebHDFS + IVYOPVOL/IVYIDXDV/IVYZEROC | **Working** |
| `equities.volprop` (UDB) | TSDB `ivyt_` namespace | **403 — need to request** |
| HDFS ACL for IVYOPPRC/IVYSTDOP | Per-strike prices + Greeks | **403 — need to request** |

### GEX Strategy Given Current Access

**We CAN compute GEX** with a hybrid approach:
1. **OI from IVYOPVOL** — per-SecurityID daily open interest (what we have)
2. **SecurityID → (strike, expiry)** mapping from IVYOPINF (need to resolve partition scheme)
3. **Gamma via Black-Scholes** from our existing EDRVOL_PERCENT_EXPIRY IV surface
4. **Risk-free rate from IVYZEROC** (what we have)
5. **Dividend yield from IVYIDXDV** (what we have)

This hybrid approach gives us **proper OI-weighted GEX** without needing IVYSTDOP.

---

## 7. Confluence Pages Index

| Page ID | Title | Space | Relevance |
|---------|-------|-------|-----------|
| 811415159 | ISG Option Metrics Data Loader API | PWMTech | Quantum API schema, Python script details |
| 925556743 | ISG Option Metrics PrestoDB Integration | PWMTech | PrestoDB query setup |
| 4872885335 | ISG- QUANTUM \| NOTES | PwmDataPlat | Architecture overview, NRT flow URLs |
| 1448101188 | Ivy (FDS) | FDS | TSDB interface, `ivyt_` pattern, UDB entitlement |
| 4334923178 | GS IvyDB Implementation | FDS | Sybase servers, data integrity, IVY_TSDB_MIGRATION |
| 339160620 | IVYDB Options Feed | GSAM | Feed file patterns, procmon jobs, OI files |
| 5097685559 | Access/Entitlements need for ISG | ~thsaic | Full entitlement list, HDFS paths |
| 337595676 | GDD ISG CSI Options Data Contract | GSAM | CSI options API contract (separate dataset) |
| 2318725392 | Investment Strategy Group \| Quantum Dependancy | PwmDataPlat | Master page linking all OptionMetrics sub-pages |
| 4584334794 | OptionMetrics V6 Dap Flow \|NRT | PwmDataPlat | V6 NRT pipeline details |
| 4334510979 | OptionMetrics IVYUS V6 Migration | PwmDataPlat | V5→V6 migration details |
| 2371719441 | OptionMetrics GI V3 - Dataset Analysis | PwmDataPlat | GI dataset schema (APAC/EU) |
| 6219849137 | OPRA | EQUITIES | Real-time options tick data (separate from OptionMetrics) |

---

## 8. Comparison: OptionMetrics vs Current Data Sources

| Dimension | Current (EDRVOL_PERCENT_EXPIRY) | OptionMetrics IvyDB |
|-----------|---------------------------------|---------------------|
| **Granularity** | ~23 relative strikes per expiry | **Every listed strike** |
| **Open Interest** | Not available | **Yes — per strike daily** |
| **Greeks** | Must compute via BS | **Vendor-computed (dividend-adjusted)** |
| **Volume** | Not available | **Yes — per strike daily** |
| **GEX computable** | No (no OI) | **Yes — full computation** |
| **Bid/Ask** | Not available | **Yes — per strike** |
| **History** | 2005–present (SPX via Marquee) | **1996–present** |
| **Frequency** | EOD | EOD |
| **Update lag** | T+0 (same day) | T+1 (next day) |
| **Access proven** | Yes (working) | Probing needed |

---

## 9. Risk & Limitations

| Risk | Impact | Mitigation |
|------|--------|------------|
| T+1 lag | GEX signal is stale by 1 day | Use previous-day GEX as predictor (acceptable for daily RV forecast) |
| HIVE/PrestoDB access may require Kerberos from Coder workspace | Can't query directly | Clone Quantum adapter, use batch extract to parquet |
| `equities.volprop` may not be auto-granted with `isg-marketdata-accessor` | TSDB path blocked | Fall back to HIVE/Quantum API path |
| Data volume (all SPX strikes × all expiries × daily) | Large parquet files | Filter to: front-month + weekly expiries, strikes within ±15% of spot |
| Dealer position assumption (calls short, puts long) is approximate | GEX is noisy | Use sign/regime only, not absolute magnitude |

---

## 10. Implementation Plan

### Phase 1: Access Verification (this session)
- [ ] Run `verify_isg_access.py` with proper GsSession
- [ ] Probe `ivyt_SPX@impliedvol.1m.50c` via TSDB
- [ ] Attempt HIVE query via Kerberos

### Phase 2: Data Extraction Script
- [ ] Clone `pwm-quantum-external-data-adapter` for API reference
- [ ] Write extraction script for SPX OPTION_PRICE table (2015–2026)
- [ ] Filter to useful strike range (0.85–1.15 relative strike)
- [ ] Store as daily parquet in `data/raw/options_oi/`

### Phase 3: Feature Engineering
- [ ] Implement proper GEX with real OI weights (upgrade `options_oi.py`)
- [ ] Add put-call ratio features
- [ ] Add pin risk features
- [ ] Add vanna exposure
- [ ] Integrate into Layer 5 feature pipeline

### Phase 4: Model Integration
- [ ] Add GEX features to LightGBM experiment config
- [ ] Run ablation study: GEX alone, GEX + PCR, full options features
- [ ] Measure QLIKE improvement over Layer 0–4 baseline

---

## 11. Key Contacts

| Role | Contact |
|------|---------|
| Quantum ISG Support | `gs-pwm-quantum-isg-support` |
| QIS Data Support | `gs-am-qis-data-support` |
| Vendor | `support@optionmetrics.com` |
| IvyDB licensing | See Ivy FDS page |

---

## 12. Related Code in This Repo

| File | Purpose | Status |
|------|---------|--------|
| `src/volforecast/data/options_oi.py` | GEX computation + synthetic chain fallback | Implemented (no real OI yet) |
| `workspace/scripts/probe_options_oi_greeks.py` | Marquee/TSDB/OPRA probe | Written, needs re-run |
| `workspace/scripts/verify_isg_access.py` | ISG entitlement verification | Ran (GsSession issue) |
| `workspace/scripts/search_confluence_options_oi.py` | Confluence page discovery | Ran successfully |
| `workspace/scripts/read_isg_confluence_pages.py` | Deep-read key Confluence pages | Ran successfully |
