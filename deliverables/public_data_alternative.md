# Public Data Alternative: What Changes Without SecDB Access

This page documents only the differences from the [main project plan](project_plan.md). The theoretical foundation, prediction targets, validation framework, and deliverable structure remain identical.

---

## Data Substitutions

Each SecDB feature family is replaced with the best available public proxy:

| Feature Family | SecDB Source | Public Substitute | Source | Frequency | What You Lose |
|---|---|---|---|---|---|
| **Dealer Constraint Level** | VaR utilization (VaR / limit) | He-Kelly-Manela intermediary capital ratio | Manela's website (CRSP + Compustat) | Quarterly | 60x fewer observations; no limit data; 1-month publication lag |
| | | Dealer CDS spreads (GS, JPM, MS composite) | Bloomberg / Markit | Daily | Market-implied, not actual constraint; noisy during idiosyncratic events |
| | | Primary dealer leverage (FR Y-9C filings) | Federal Reserve | Quarterly | Same limitations as HKM; different leverage definition |
| **Risk Concentration** | Factor-VaR decomposition (exact HHI) | Self-constructed factor model on public returns; compute HHI on estimated factor risk contributions | FRED, Bloomberg, Yahoo Finance | Daily (constructed) | Estimated, not exact; depends on factor model quality; no internal risk attribution |
| | | Cross-asset realized correlation matrix | Public returns data | Daily (constructed) | Captures co-movement, not the actual risk decomposition |
| **Balance-Sheet Dynamics** | Total VaR, component VaR by asset class | NY Fed primary dealer net positions | NY Fed | Weekly | Positions, not risk; no vol-weighting; weekly not daily |
| | | VIX (equity vol), MOVE (bond vol) | CBOE, ICE via FRED | Daily | Market-implied vol, not dealer-specific risk state |
| **Stress Vulnerability** | Scenario P&L from SecDB risk engine | Self-constructed: define scenarios, compute P&L impact using public factor exposures | Self-constructed | Daily (constructed) | Linear approximation vs. full repricing; no options/nonlinear payoff capture |
| **Cross-Asset Flow** | Component VaR share shifts | CFTC Commitments of Traders (dealer/asset manager positions) | CFTC | Weekly | Positions not risk; 3-day publication lag; weekly not daily |
| | | NY Fed primary dealer positions by asset class | NY Fed | Weekly | Same frequency limitation |

---

## What You Gain

- **No data access dependencies.** Stage 1 can start immediately.
- **Reproducibility.** Anyone can replicate the full analysis with publicly available data.
- **Compliance simplicity.** No proprietary data in the project means no restrictions on discussing methodology externally.
- **Longer history.** Some public series (HKM capital ratio, VIX, Treasury yields) go back 30-50 years vs. 5-10 years for SecDB.

## What You Lose

- **Frequency.** The strongest public proxies for dealer constraints (HKM ratio, Fed Z.1, FR Y-9C) are quarterly. You drop from ~252 observations per year to ~4. Daily proxies exist (dealer CDS, VIX) but measure market perception of dealer stress, not the actual constraint state.
- **Granularity.** Public data is sector-aggregate or firm-level at best. You cannot observe desk-level constraints, within-firm risk allocation, or position-level risk attribution.
- **Directness.** VaR utilization directly measures "how close is the desk to its limit." No public proxy measures this. Dealer CDS and the HKM ratio are correlated with constraints but are several steps removed from the actual mechanism.
- **Novelty.** The public proxies are exactly what the published academic papers already used. The project becomes a methodological contribution (better ML/validation on known data) rather than a data contribution (new data on known theory).

---

## Timeline Adjustments

| Phase | Original (with SecDB) | Public Data Version |
|---|---|---|
| Phase 0 (Weeks 1-2) | Data access audit of SecDB risk cubes | Source and load all public datasets; no access audit needed |
| Phase 1 (Weeks 3-5) | Infrastructure with SecDB bridge | Same infrastructure, but data pipeline connects to FRED/Bloomberg/CSV instead of SecDB |
| Phase 2 (Weeks 6-12) | Feature engineering from risk cube outputs | Feature engineering from public proxies; self-constructed factor models and scenario analysis require additional build time |
| Phase 3 (Week 13) | Checkpoint: continue or pivot | Same checkpoint, but also: present results as the case for SecDB access if signal exists |
| Phase 4 (Weeks 14-17) | Deepen Project 1 or pivot to Project 2 | If SecDB access now granted: run Stage 2 comparison. If not: regime overlay, cross-asset panel, capacity analysis on public data. |
| Phase 5 (Weeks 18-20) | Consolidation | Same. If both stages completed, the public-vs-proprietary comparison becomes the headline finding. |

The main additional work in the public-data version is **constructing** features that would come pre-computed from SecDB:

- Building a factor model from public returns data (for the concentration/HHI features)
- Defining and computing scenario P&L from factor exposures (for the stress vulnerability features)
- Interpolating quarterly data for use alongside daily features

This adds roughly 1-2 weeks of feature engineering effort in Phase 2, which is absorbed by the fact that you no longer need the SecDB data access audit in Phase 0.

---

## Recommended Public Data Sources

| Dataset | What It Provides | URL / Access |
|---|---|---|
| NY Fed Primary Dealer Statistics | Weekly dealer positions and financing by asset class | newyorkfed.org/markets/primarydealers |
| He-Kelly-Manela Capital Ratio | Quarterly intermediary capital factor (updated) | Asaf Manela's faculty page |
| FRED (Federal Reserve Economic Data) | VIX, credit spreads, Treasury yields, term slope, dollar index | fred.stlouisfed.org |
| CFTC Commitments of Traders | Weekly positioning by trader type and asset class | cftc.gov/MarketReports |
| CBOE | VIX daily, VIX term structure | cboe.com |
| ICE | MOVE index (bond volatility) | Via Bloomberg or data vendors |
| Yahoo Finance / public APIs | Equity index returns, ETF prices for asset-class proxies | finance.yahoo.com |
| Markit / Bloomberg | Dealer CDS spreads (may require terminal access) | Bloomberg terminal |

---

## The Path Back to SecDB

If Stage 1 produces positive results on public data, the pitch for SecDB access becomes straightforward:

> "The methodology works. Public data with quarterly frequency and two-month lag produces [X] IC and [Y] Sharpe for predicting [target]. Theory and the data frequency difference both suggest that daily internal data should improve this. Granting read access to risk cube outputs lets us run the identical analysis on better data and quantify the improvement. The methodology, validation, and infrastructure are already built."

The public-data stage is not a fallback. It is the control group that makes any SecDB result credible.
