# GSVIVS IV Comparison Improvement Plan

## The Problem

We want to predict when GSVIVS01 (a short-vol strategy) will have drawdowns, so we can go flat and avoid them. The original approach — an IV-RV gap signal — failed structurally: the gap is persistently positive (85-88% of days) because the Variance Risk Premium exists. The signal never fires a "go short" warning, or fires too late (post-spike recovery).

But beyond the signal design flaw, there is a **measurement flaw**: we are comparing the wrong implied volatility against predicted realized volatility.

## What GSVIVS01 Actually Sells

GSVIVS01 is a **daily variance swap replication (VSR)** via 0DTE SPX options:

- Short ~25 options per day (10 calls + 15 puts)
- Strikes: 95%-101% of forward (OTM strip)
- Execution: TWAP 13:30-14:00 ET
- Expiry: Same day (0DTE "Daily Weekly")
- Source: VSR 0b (Variance Swap Replication bucket 0)
- Strategy tickers: `.GSVIVSR1_DH`, `.GSVIVSR2_DH` (low lag variant)

The strategy does NOT sell a single ATM option. It sells a **weighted strip of OTM options** whose combined premium replicates a variance swap payoff. The fair value of this strip is the **variance swap strike** (model-free implied variance), not the ATM IV.

## Why ATM 0DTE IV Is Wrong

The variance swap strike is derived from the full option chain via:

$$K_{var} = \frac{2}{T} \int_0^\infty \frac{C(K) - \max(S-K, 0)}{K^2} \, dK$$

This integral weights OTM options by $1/K^2$, giving **more weight to OTM puts** (which have higher IV due to skew). Result: the variance swap strike is always ABOVE ATM IV.

**Empirical evidence from our data:**
- SPX iv_0dte (ATM): mean 16.20% annualized in GSVIVS period
- VIX (30-day variance swap strike): mean 18.64%
- Ratio: iv_0dte / VIX = 0.87
- Correlation: 0.79

The gap is ~2.4 vol pts on average. For a 0DTE variance swap, the skew premium is typically 1-3 vol pts above ATM (less than 30-day VIX because 0DTE skew is flatter, but still material).

## What We Need: The 0DTE Variance Swap Strike

The correct IV to compare against predicted RV is the **0DTE model-free implied variance** — the fair strike of the variance swap that GSVIVS replicates daily.

### Data Sources (Ranked by Quality)

| # | Source | Description | Availability | Quality |
|---|--------|-------------|-------------|---------|
| 1 | **EDRVS_EXPIRY** (Marquee) | GS Equity Variance Swap Levels by Listed Expiry | Confirmed available via Marquee API. Dataset ID: `EDRVS_EXPIRY`. Covers SPX with daily expiries. | **Best option** — GS internal variance swap strike by exact listed expiry date |
| 2 | **EDRVS** (Marquee / TSDB) | GS Equity Variance Swap Levels by Tenor | TSDB: `edrvs_SPX@{tenor}` (1w, 1m, etc.). Marquee: `Dataset("EDRVS")`. Var Swap Server runs continuously for SPX/NDX/RUT. | Excellent — GS internal fair variance by tenor |
| 3 | **eqvolrt_vix@basis_spx_listed_market** | Real-time VIX basis signal using listed SPX options (all OTM puts+calls with non-zero bid, mid prices) | TSDB real-time. Calculates variance from actual screen data with wider strike range than vol surface. | Good — model-free from market prices, but 30-day forward, not 0DTE |
| 4 | **VIX0DTE (^VIX0D)** | CBOE 0-Day VIX Index | NOT in TSDB cache. Launched Apr 2024. Try `eqsp_s_.vix0d@close` or `eqpad_.VIX0D@close`. | Perfect if available — but only ~14 months of history |
| 5 | **EDRVOL_PERCENT_EXPIRY full chain** | Reconstruct variance from full strike grid | Already used for ATM. Can query multiple `relativeStrike` values and integrate. | Good — requires numerical integration |
| 6 | **Reconstruct from output.json** | Compute $K_{var}$ from GSVIVS execution prices | Available if full history curve JSON exportable. Currently 5 sample days. | Excellent — actual execution prices |
| 7 | **Scaled ATM proxy** | iv_0dte * scaling_factor | Already have iv_0dte with 1010/1010 coverage | Approximate fallback |

---

## Confluence Research Findings

### Key Discovery: EDRVS_EXPIRY Dataset

From Confluence page ["Data Vertical: Data Services Equity Volatility"](https://confluence.work.gs.com/spaces/MARQUEE/pages/582304966) in MARQUEE space, the following datasets exist:

| Dataset ID | Name | Description |
|-----------|------|-------------|
| `EDRVS` | GS Equity Variance Swap Levels by Tenor | Fair variance by standard tenors (1w, 1m, 3m...) |
| **`EDRVS_EXPIRY`** | **GS Equity Variance Swap Levels by Listed Expiry** | **Fair variance by specific listed expiry date** |
| `EDRVS_EXPIRY_INTRADAY` | GS Equity Variance Swap Levels Intraday by Listed Expiry | Intraday ticking version |
| `EDRVS_TENOR_INTRADAY` | GS Equity Variance Swap Levels Intraday by Tenor | Intraday by tenor |

**`EDRVS_EXPIRY` is the primary candidate.** It provides variance swap levels indexed by listed expiry date. Since SPX has daily 0DTE expiries (Mon-Fri), querying this dataset for the nearest expiry gives us the 0DTE variance swap strike directly.

### TSDB Symbol Format

From ["Marquee TSDB Sync"](https://confluence.work.gs.com/spaces/MARQUEE/pages/1787571224):
- TSDB: `edrvs_SPX@1m` = 1-month SPX variance swap level
- Maps to SecDB object: `edrvs_spx`
- GS Quant equivalent: `Asset.var_swap()`, `Asset.var_term()`, `Asset.forward_var_term()`

### Var Swap Server (Real-Time Pricing)

From ["Sonic Var Swap"](https://confluence.work.gs.com/spaces/EQT/pages/2751359823):
- The **Var Swap Server** runs continuously pricing variance swaps for SPX, NDX, RUT in multiple tenors (1w, 2w, 1m, 2m...)
- Procmon jobs: `eqvol/NYC/volfitter/vs-srv-calc` (regular) and `vs-srv-calc-early` (pre-open)
- Data refreshed by vol marker (implied vol surface), then variance derived
- UI: "Eq Var Swap Server Calcs" container with trader marks
- Tenors calculated: **includes 1w** which is the shortest standard tenor

### VIX Basis Real-Time Signal (Alternative Source)

From ["VIX Basis Calculation"](https://confluence.work.gs.com/spaces/EQS/pages/6375559731):

Three methods compute the 30-day forward variance for VIX basis decomposition:

| Suffix | Method | Strike Range | Data Source |
|--------|--------|-------------|-------------|
| `_spx_vs` | From varswap term structure (includes MTM basis, VPD) | Standard tenors | SecDB varswap pricing |
| `_spx_vol_surface` | From SPX vol surface, 49 strikes (-10NS to +10NS) | Tight (-10 to +10 normal spreads) | Non-parametric vol fitter |
| **`_spx_listed_market`** | **From listed screens, all OTM puts/calls with non-zero bid** | **Wide (all liquid strikes)** | **Live bid/ask mid prices** |

The `_spx_listed_market` variant is closest to what we want because:
- Uses **actual market mid prices** (not model-fitted)
- Includes **all liquid OTM puts** (wider range than vol surface, more OTM put weight)
- This IS the model-free variance calculation from real screen data

**TSDB symbols:**
- Real-time: `eqvolrt_vix@basis_spx_listed_market_1_fwdvsvol` (1st nearby VIX future forward vol)
- EOD: `eqvol_vix@basis_spx_listed_market_1_fwdvsvol` (daily close version)

**Limitation:** This calculates 30-day forward variance (VIX future tenor), not 0DTE. But it confirms the infrastructure exists to compute model-free variance from listed options.

### VIX Replication Formula (From Confluence)

From ["VIX Replication"](https://confluence.work.gs.com/spaces/EQS/pages/5407815010):

The quantity formula for each option in the replication strip:
$$Q_i = \frac{2}{T} \cdot \frac{\Delta K}{K_i^2} \cdot e^{rT} \cdot \frac{100}{2 \cdot \text{volatility}}$$

This is used for VIX futures settlement. The same formula (without the vol normalization) gives the variance swap strike. The implementation uses:
- ATM strike $K_0$ from put-call parity
- All SPX options with positive bid size
- Friday expiry for monthly, various for weekly

### Asset Coverage

From ["Manage Marquee EqVol Asset List"](https://confluence.work.gs.com/spaces/EQT/pages/340526221):
- SPX is in the asset list for EDRVS, EDRVS_EXPIRY, and all intraday variants
- Uploads managed by `eqvol/NYC/marquee/` procmon jobs
- Backfilling available for EOD variance swap datasets

---

## Implementation Plan (Updated 2026-06-05)

### Phase 1: EDRVS_EXPIRY — BLOCKED (403 Forbidden, needs entitlement)

**Status: BLOCKED — requires Marquee entitlement request**

EDRVS_EXPIRY is confirmed as the ideal dataset: SPX is in the coverage (5918 assets), the dataset is uploaded daily by `eqvol/NYC/marquee/` procmon jobs, and it indexes by listed expiry date (meaning daily 0DTE expiries should be available post-2022).

**Query result (2026-06-05):**
```
POST https://marquee.web.gs.com/v1/data/EDRVS_EXPIRY/query
Status: 403 Forbidden
"Not authorized to query resource: DataSet IDs EDRVS_EXPIRY"
```

Coverage works (no auth required): confirms SPX (assetId: `MA4B66MW5E27U8P32SB`, bbid: `SPX`).

**To unblock:** Request Marquee data entitlement for `EDRVS_EXPIRY` dataset. The coverage endpoint works, so the dataset is active and maintained — we just lack query permissions. This is likely an EQD/EQVol team dataset requiring explicit data-sharing approval.

### Phase 1b: EDRVS (Tenor-Based) — WORKS, Shortest Tenor = 1w

**Status: ACCESSIBLE — usable as interim fallback**

`Dataset("EDRVS")` returns SPX variance swap levels successfully:

```
Columns: assetId, tenor, fairVariance, fairVolatility, updateTime, bbid
Units: fairVariance = (vol%)² (e.g., 184.08), fairVolatility = vol% (e.g., 13.57%)
```

**Available tenors (31):** 1w, 2w, 3w, 5w, 6w, 1m, 2m, 3m, 4m, 5m, 6m, 7m, 8m, 9m, 1y, 13m, 14m, 15m, 18m, 21m, 27m, 30m, 2y, 3y, 4y, 5y, 6y, 7y, 8y, 9y, 10y

**Key finding: NO 1d/0d tenor exists.** Querying `tenor="1d"` returns 0 rows. The shortest tenor is `1w`.

**Sample data (2024-06-03 to 2024-06-14, tenor=2w):**
| Date | fairVariance | fairVolatility |
|------|-------------|----------------|
| 2024-06-03 | 184.08 | 13.57% |
| 2024-06-07 | 162.75 | 12.76% |
| 2024-06-12 | 135.45 | 11.64% |

**Implication for GSVIVS signal:** The 1w variance swap strike from EDRVS is usable as an approximation — it captures skew premium and is a fair variance (not model-ATM), but the tenor mismatch (7d vs 0d) means it doesn't match the actual 0DTE strip that GSVIVS sells. It will understate the kurtosis/gamma premium embedded in same-day options.

**Action items:**
1. **Priority: Request EDRVS_EXPIRY entitlement** — this is the game-changer. File TMD ticket or contact EQVol/Marquee data team.
2. **Interim: Use EDRVS 1w** as proxy for variance swap strike (better than ATM IV, captures skew)
3. Also probe TSDB symbol `edrvs_SPX@1w` for historical depth (EDRVS may only retain recent data via Marquee)

### Phase 2: TSDB Direct Access (Parallel — validate historical depth)

```python
from volforecast.data.tsdb import _get_tsdb_data

# EDRVS TSDB namespace — confirmed structure from Marquee sync docs
candidates = [
    "edrvs_SPX@1w",       # 1-week variance swap (shortest confirmed tenor)
    "edrvs_SPX@2w",       # 2-week (backup)
    "edrvs_.SPX@1w",      # Alternative RIC format
    "eqsp_s_.vix0d@close", # VIX0DTE if CBOE index is published
    "eqpad_.VIX0D@close",  # Alternative VIX0DTE symbol
]
for sym in candidates:
    try:
        data = _get_tsdb_data(sym, "2024-01-01", "2024-06-01")
        print(f"{sym}: {len(data)} points")
    except:
        print(f"{sym}: FAILED")
```

### Phase 3: Reconstruct from EDRVOL_PERCENT_EXPIRY (Fallback)

If EDRVS_EXPIRY doesn't have daily expiries for SPX, reconstruct using the implied vol chain:

```python
ds = Dataset("EDRVOL_PERCENT_EXPIRY")

# Fetch full strike grid for 0DTE
strikes = [0.90, 0.92, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99, 1.00, 1.01, 1.02, 1.03, 1.05]
chain = {}
for strike in strikes:
    data = ds.get_data(
        start=..., end=..., ric="SPX",
        strikeReference="forward", relativeStrike=strike,
    )
    chain[strike] = data

# Apply CBOE VIX formula (discrete):
# sigma^2 = (2/T) * sum_i (DeltaK_i / K_i^2) * e^(rT) * Q(K_i)
# where Q = put for K < K_0, call for K > K_0
```

### Phase 4: Corrected Signal Construction

Once we have the 0DTE variance swap strike time series:

1. **Corrected VRP:** $VRP_{0dte} = \sigma_{vs,0dte}^2 - \hat{RV}_{1d}$
2. **Signal logic:** Go flat when VRP is abnormally compressed (IV dropping toward RV)
3. **Key insight:** A compressed VRP means the market is under-pricing tail risk. This is when GSVIVS is most vulnerable — selling cheap insurance before a spike.

### Phase 5: Validation

1. Compare corrected VRP signal against historical GSVIVS drawdown dates
2. Backtest: Sharpe of signal-timed vs always-long
3. Statistical tests: DM test for predictive power of corrected IV vs ATM IV

---

## What This Solves

| Problem | Current State | After Fix |
|---------|--------------|-----------|
| Wrong IV number | ATM 0DTE IV (16.2% mean) | Variance swap strike (est. 17-19% mean) |
| Signal never fires | Gap always positive (ATM < RV pred is rare) | Correct gap is tighter, more likely to flip |
| Missing skew info | Single strike comparison | Full-chain information captured |
| Timing | Backward-looking RV | Forward-looking IV-based signal |

The fundamental bet: by using the CORRECT implied volatility (what GSVIVS actually sells) minus predicted RV, the VRP signal becomes tighter and more responsive. Days where the variance swap strike drops close to predicted RV are genuine danger zones — the strategy is selling near-fair-value insurance, with no skew cushion to absorb a spike.

---

## Dependencies and Risks

- **EDRVS_EXPIRY entitlement (BLOCKER):** Dataset exists, SPX is in coverage (5918 assets), but query returns 403 Forbidden. Need to request Marquee data entitlement. This is the single highest-priority unblock — the dataset likely contains daily (0DTE) expiries for SPX post-2022, which gives us the exact variance swap strike GSVIVS sells.
- **EDRVS 1w as interim:** Accessible and returns `fairVariance`/`fairVolatility` for 31 tenors. The 1w var swap strike is a better proxy than ATM IV (captures skew), but 7-day tenor overstates what 0DTE actually prices (kurtosis premium is lower over 7d than 1d annualized).
- **VIX0DTE coverage:** Only from Apr 2024 if available in TSDB at all. For 2022-2024 need EDRVS_EXPIRY or reconstruction.
- **Reconstruction accuracy:** If using EDRVOL_PERCENT_EXPIRY chain, Marquee IV may be model-interpolated (SVI/SABR), not raw mid-prices. The `_spx_listed_market` variant in TSDB uses real screen data but is 30-day only.
- **The signal may still not work:** Even with correct IV, predicting when VRP compresses may be as hard as predicting vol spikes directly. The iv_acceleration signal (Sharpe 2.14) may remain the better approach.

---

## Confluence Sources Referenced

| Page | Space | ID | Key Content |
|------|-------|----|-------------|
| Data Vertical: Data Services Equity Volatility | MARQUEE | 582304966 | Full EDRVS dataset catalog |
| Data Product: GS Equity Variance Swap Levels | MARQUEE | 373812842 | EDRVS product documentation |
| VIX Basis Calculation | EQS | 6375559731 | TSDB symbols, _spx_listed_market method |
| VIX Replication | EQS | 5407815010 | Replication formula, strike selection |
| Sonic Var Swap | EQT | 2751359823 | Var Swap Server (real-time SPX/NDX/RUT) |
| Marquee TSDB Sync | MARQUEE | 1787571224 | TSDB ↔ Marquee symbol mapping |
| VIX Related Subjects | EQS | 363138843 | VIX market data, VarSwap basis marking |
| Strategies Pipeline | EQT | 6142864052 | GSVIVSR1_DH / GSVIVSR2_DH tickers |
| Manage Marquee EqVol Asset List | EQT | 340526221 | SPX confirmed in EDRVS asset list |
