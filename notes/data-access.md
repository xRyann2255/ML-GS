# Data Access Inventory

Documented 2026-05-06. This is the binding constraint on which project directions are feasible.

---

## 1. Tick-Level Realized Volatility

**Universe:** 30 mega-cap equities + 4 ETFs + E-mini S&P 500 futures (34 symbols total)
**Granularity:** L1 tick data
**History:** Back to Chunk Store retention window (minimum)
**Enables:** RV computation at any intraday frequency (5-min, 1-min, tick-by-tick), kernel-based estimators, jump detection, realized quarticity for HARQ

## 2. Daily Model Training Data

**Universe:** All 34 symbols + VIX + indices + breadth indicators
**History:** 11.3 years of OHLCV + returns + market cap
**Enables:** HAR/HARQ/SHAR baselines, ML training with sufficient history for purged k-fold CV, cross-sectional panel studies

## 3. Microstructure Features (E-mini Only)

**Symbol:** E-mini S&P 500
**Volume:** ~4M ticks/day
**Granularity:** L2 depth + tick direction
**Enables:** Order flow imbalance, depth ratio, signed volume features at the index level
**Limitation:** L2 depth is E-mini only; the 30 equities + 4 ETFs have L1 only

## 4. Vol Regime Signals

**Data:** VIX index + 3-month VIX futures term structure
**Enables:** Direct observable vol expectations, contango/backwardation regime detection, VIX innovation features

## 5. Implied Volatility Surfaces

**Source:** Marquee ERDVOL_PERCENT_STANDARD
**Coverage:** Full SPX vol surface history (tenor x strike grid)
**Enables:** IV-RV spread (variance risk premium), term structure slope, skew dynamics (25-delta put/call spread), surface-level features
**Limitation:** SPX only, not individual equity names

## 6. Cross-Asset Signals

| Asset Class | Instruments | Source |
|---|---|---|
| Treasuries | 2y, 5y, 10y, 30y yields | GS data |
| Commodities | CL (crude), GC (gold) | Futures |
| Bonds | TY (10y Treasury futures) | Futures |
| FX | USD/JPY, EUR/USD | Marquee |

**Enables:** Macro regime conditioning, cross-asset spillover features, term spread signals

---

## Direction Feasibility Matrix

| Direction | Data Status | Notes |
|---|---|---|
| 1. HARQ-X + ML residual | Fully enabled | 34-symbol panel, 11.3yr history, tick-level RV |
| 2. Intraday RV from LOB | E-mini only | L2 depth limited to one symbol; single-asset study |
| 3. Multivariate RC + GNNs | Fully enabled | 34 symbols + cross-asset signals for graph structure |
| 4. Rough vol vs deep learning | SPX only | IV surface for calibration is SPX only |
| 5. VRP ML trader | Viable (SPX) | IV surface + RV = VRP directly; VIX term structure for regime |
| 1+5 hybrid | Fully enabled | HAR panel backbone + VRP/IV features from surface |
