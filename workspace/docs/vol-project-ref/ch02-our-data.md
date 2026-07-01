# Chapter 2: Our Data

## Data Sources

The table below inventories every data source available for the project.
All sources span 11.3 years of history.

**Available data sources, what they enable, and their constraints.**

| Data Source | Granularity | What It Enables | Key Constraint |
|---|---|---|---|
| Tick-level RV (34 symbols) | L1 tick | RV at any frequency, RQ, jumps, semivariances | -- |
| Daily OHLCV (34 + VIX) | Daily | HAR baselines, ML training | No intraday structure |
| E-mini L2 depth | L2 (~4M ticks/day) | OBI, depth ratio, VPIN, LSTM input | E-mini only |
| IV surfaces (Marquee ERDVOL) | Full tenor x strike grid | VRP, skew, term structure, butterfly | Full surface SPX only; single-stock ATM IV via EDRVOL_PERCENT |
| VIX term structure | Daily | Regime detection, contango/backwardation | -- |
| Cross-asset (treasuries, FX, commodities) | Mixed (tick to daily) | Spillover features, macro regime | Daily for some instruments |

## GS Edge vs. Public Data

The table below summarizes the capabilities our data provides relative to what is typically available in academic studies.

**Data advantages over standard academic sources.**

| Capability | Our Data | Public Alternative | Edge |
|---|---|---|---|
| RV estimation quality | Tick-level, 34 symbols, 11.3 years | 5-min returns from TAQ / Oxford-Man | Precise RQ, jump detection, kernel estimators |
| Options surface | Full SPX tenor x strike grid (Marquee) | VIX only (model-free 30-day) | Full surface derivatives: skew, butterfly, slope, event-implied |
| Microstructure depth | E-mini L2 (4M ticks/day) | L1 quotes only (TAQ) | OBI at depth levels 2--5, true depth imbalance |
| Cross-asset sync | Same tick timestamp across asset classes | Daily closes only | Intraday lead-lag detection |
| Panel breadth | 30 mega-caps + 4 ETFs + E-mini | Typically 1 index or 29 DJIA | Graph models, sector structure, cross-sectional features |

> **Key Idea: The data advantage is structural, not just bigger**
>
> The tick-level RV, full IV surface, and L2 depth data let us construct features that are mathematically impossible to compute from public data. This is not a matter of having "more data"; public researchers literally cannot replicate the feature set.

## Constraints That Shape Decisions

L2 depth data covers the E-mini only, so microstructure depth features (OBI at levels 2--5, depth ratio) apply exclusively to the index.
Equities receive L1 features only.
The full IV surface is SPX only, so surface-derived features (skew, term structure, butterfly) function as market-wide regime signals.
Single-stock ATM IV is available via Marquee EDRVOL_PERCENT, enabling per-name VRP and IV--RV gap features.
These constraints determine which features apply to which assets in the feature engineering pipeline.

> **Warning: Do not treat depth or surface features as stock-level predictors**
>
> L2 depth and the full IV surface are index-level data. Using them as if they vary across individual equities would introduce look-ahead bias or a constant signal masquerading as stock-specific information.
> Single-stock ATM IV is the exception -- it is genuinely per-name.
