# Vol Learning Guide: Practitioner Gap Additions

**Date:** 2026-05-05
**Status:** Approved
**Scope:** Add practitioner-oriented content from reference papers (Bennett 2014, Moskowitz 2012, Cartea 2015, Natenberg 1994) to fill gaps identified by systematic analysis.

---

## Summary

Add 9 sections to the vol-learning-guide: 4 full-treatment sections (3-4 pages each with prereq/intuition/worked-example boxes) and 5 lighter bridge sections (1-1.5 pages each). Total: ~25-30 new pages.

## Implementation Order (Narrative Chain)

Ordered by pedagogical dependency so each section can reference prior ones:

1. Ch 8: Dupire local vol
2. Ch 8: Variance swap replication + VIX construction
3. Ch 9: Gamma P&L formula
4. Ch 3: Adverse selection bridge
5. Ch 7: Path-dependence bridge
6. Ch 10: Microprice + volume features
7. Ch 10: Event-driven vol features
8. Ch 17: Vol targeting + economic value
9. Ch 17: Structured products feedback / dealer gamma

---

## Full-Treatment Sections (4)

### 1. Ch 8: Local Volatility (Dupire Formula)

**Location:** After Section 5 (PCA of the Volatility Surface, ends ~line 555) and before Section 6 (Model-Free Implied Variance and the VIX). Label: `\label{sec:local-vol}`
**Length:** ~4 pages

**Structure:**
- Prereq box: Black-Scholes, partial derivatives, implied vol surface from earlier in chapter
- Motivation: "You have a surface of IVs - how do you interpolate/extrapolate consistently?"
- Dupire formula derivation: sigma_local^2(K,T) = (dC/dT + rK*dC/dK) / (0.5*K^2 * d^2C/dK^2)
- Intuition box: local vol as "the vol the market assigns to a specific price level at a specific time"
- Worked example: compute local vol at 3 strikes from a toy call surface
- Warning box: local vol is NOT a forecast of future vol - it's a mathematical construct for consistent pricing
- Project connection: local vol extractions can serve as features for ML vol forecasting

### 2. Ch 8: Variance Swap Mechanics and Replication

**Location:** After existing Section 6 (Model-Free Implied Variance and the VIX, ends ~line 720) and before Section 7 (Connecting the Vol Surface to Volatility Forecasting). Label: `\label{sec:var-swap}`
**Length:** ~3 pages

NOTE: Ch 8 already derives the model-free implied variance integral and VIX construction in Section 6. This new section does NOT re-derive VIX. Instead it focuses on (a) variance swap mechanics as a tradeable instrument and (b) a discretization worked example. It back-references the existing VIX integral via "recall Equation~\ref{eq:vix}".

**Structure:**
- Prereq box: model-free implied variance integral (Section 6 of this chapter), log-returns, options payoffs
- Motivation: "The VIX formula gives you fair variance. How do you actually TRADE it?"
- Variance swap contract: payoff = notional * (RV^2 - K_var), settlement, conventions (variance notional vs vega notional, annualization)
- Log-contract argument: brief (1 paragraph) on why replicating a log-payoff gives you realized variance; back-reference to existing integral
- Worked example: given 5 OTM puts and 5 OTM calls with specific prices and strikes, discretize the replication integral, compute K_var, compare to VIX^2. Show where truncation error enters.
- Intuition box: "A variance swap lets you trade your RV forecast directly: if you believe RV will be 20% but K_var = 18%, you buy the swap and profit if you're right."
- Warning box: convexity adjustment between vol swaps and var swaps (E[sigma] < sqrt(E[sigma^2])); mark-to-market risk before expiry
- Project connection: VIX^2/100^2 minus your RV forecast = VRP; this section makes VRP a tradeable quantity, not just a statistical construct

### 3. Ch 9: Gamma P&L Formula and Delta-Hedging Economics

**Location:** After Section 5 (Decomposing VRP, ends ~line 320) and before Section 6 (Vol-of-Vol, starts ~line 326). Label: `\label{sec:gamma-pnl}`
**Length:** ~3-4 pages

**Structure:**
- Prereq box: delta, gamma (from Ch 8), variance swap payoff (from new Ch 8 section), VRP definition (earlier in Ch 9)
- Motivation: "You forecast RV better than the market. How much money does that make you?"
- Setup: buy an option at implied vol sigma_i, delta-hedge continuously
- Key derivation: daily P&L = 0.5 * Gamma * S^2 * (sigma_r^2 - sigma_i^2) * dt
- Intuition box: "Your P&L is proportional to how wrong the market's vol estimate is, weighted by your gamma exposure"
- Worked example: buy 30-day ATM straddle at IV=18%, hedge daily, realized vol = 22%. Walk through P&L over 5 days with concrete stock price path and gamma values.
- Connection to VRP: systematic IV > RV means systematic short-gamma profit
- Warning box: path-dependence (gamma varies with spot); discrete hedging introduces slippage
- Project connection: "A 5% QLIKE improvement translates to X bps of improved delta-hedging P&L per unit gamma"

### 4. Ch 17: Volatility Targeting and Economic Value Translation

**Location:** Ch 17 is currently empty (only a TODO comment). These additions form the initial content of the chapter. Write a brief chapter intro (2-3 paragraphs motivating "translating statistical accuracy into economic value") before this section. Label: `\label{sec:vol-targeting}`
**Length:** ~3-4 pages

**Structure:**
- Prereq box: portfolio returns, Sharpe ratio, RV forecast from HAR/ML
- Motivation: "You beat HAR by 8% QLIKE. So what? How much Sharpe does that buy you?"
- EWMA baseline: sigma_t^2 = (1-delta)*r_{t-1}^2 + delta*sigma_{t-1}^2
- Vol-targeting formula: w_t = sigma_target / sigma_forecast_t
- Worked example: vol-target long S&P at 10% target. Compare Sharpe using EWMA vs HAR vs ML. 20-day window with concrete numbers.
- Intuition box: "Vol targeting is the simplest possible use of a vol forecast: size up when calm, size down when volatile. Moreira-Muir (2017) show this adds ~0.3 Sharpe."
- TSMOM connection: Moskowitz et al. use sign(past return) * (40%/sigma_t)
- Warning box: if forecast is wrong in crises, vol targeting increases drawdowns
- Project connection: "Run vol-targeted S&P with each model's forecast. Report Sharpe, max drawdown, Sharpe improvement per 1% QLIKE improvement."

---

## Bridge Sections (5)

### 5. Ch 3: Adverse Selection and Spread-Vol (~1 page)

**Location:** After the three noise-source paragraphs (bid-ask bounce, tick sizes, staleness, lines 39-56 in Ch 3) and before the "Quantifying the Bias" subsection (~line 65). Label: `\label{sec:adverse-selection}`

- Glosten-Milgrom: spread = f(probability counterparty is informed). High vol increases information asymmetry, so spreads widen.
- Key formula: bid-ask spread proportional to alpha * sigma_v
- Autocovariance-as-liquidity: Cov(dp_t, dp_{t+1}) = -S^2/4
- "So what": noise carries information about market quality

### 6. Ch 7: Hedging P&L Path-Dependence (~1 page)

**Location:** New subsection between the chapter intro text (lines 10-18) and Section 1 (What Is Roughness?, line 22). Label: `\label{sec:path-dependence}`

- Two paths with identical RV but different hedging P&L (trendy vs mean-reverting)
- Gamma varies with spot, so WHEN vol occurs matters
- Rough paths have more jaggedness at short scales, meaning hedging slippage is worse
- One sentence connecting to Rosenbaum-Zhang universality finding

### 7. Ch 10: Microprice and Volume Features (~1.5 pages)

**Location:** New subsection in microstructure/order-flow features area

- Microprice: S* = (V_ask * P_bid + V_bid * P_ask) / (V_bid + V_ask)
- Volume features: volume persistence predicts vol persistence; abnormal volume as early warning
- Concrete feature list: log(volume/MA20_volume), microprice-midprice deviation, volume acceleration

### 8. Ch 10: Event-Driven Vol Features (~1 page)

**Location:** After calendar/event subsection

- Known-event vol bumps: FOMC, NFP, CPI, earnings, options expiry
- Term structure kinks at event-straddling expiries
- Feature engineering: binary indicators, days-to-next-event, historical event-day RV ratios
- Warning: look-ahead risk with event dates

### 9. Ch 17: Structured Products Feedback and Dealer Gamma (~1.5 pages)

**Location:** After vol-targeting section in Ch 17 (which is being written as part of this spec). Label: `\label{sec:dealer-gamma}`

- Autocallable/barrier products create systematic dealer short gamma
- Dealer gamma exposure as predictive feature: short gamma amplifies vol, long gamma suppresses
- GEX (Gamma Exposure) estimable from options open interest
- Pin risk at large OI strikes near expiry
- Project connection: dealer positioning as novel HAR-X feature

---

## Style Requirements

All additions follow existing guide conventions:
- `tcolorbox` environments: intuition (green), keyidea (blue/orange), warning (red), workedexample (teal), projectconnection (teal), prereq (purple)
- `booktabs` tables only, no vertical rules
- Citations via `\citep{}` / `\citet{}` from references.bib
- Bold-define every term on first use
- No em dashes

## Bibliography

New citations needed (to add to references.bib):
- Dupire (1994) "Pricing with a Smile" - *Risk* magazine
- Moreira & Muir (2017) "Volatility-Managed Portfolios" - *Journal of Finance*
- Moskowitz, Ooi & Pedersen (2012) "Time Series Momentum" - *Journal of Financial Economics*
- Glosten & Milgrom (1985) "Bid, Ask and Transaction Prices" - *Journal of Financial Economics*
- Kyle (1985) "Continuous Auctions and Insider Trading" - *Econometrica*
- Cartea, Jaimungal & Penalva (2015) "Algorithmic and High-Frequency Trading" - Cambridge UP (for microprice/adverse selection)
- Bennett (2014) "Trading Volatility" - self-published (for var swap mechanics, dealer gamma)

Already in references.bib (verify before implementation):
- CBOE VIX methodology (CBOE2019) - already cited in Ch 8
- Bollerslev, Tauchen & Zhou (2009) BTZ - already present
- Patton & Sheppard (2015) - already present

---

## Success Criteria

1. PDF compiles cleanly with no unresolved citations
2. Each full-treatment section has: prereq box, at least one intuition box, one worked example, one project connection
3. Bridge sections are self-contained and don't require reading the reference papers
4. A reader of Ch 8 + Ch 9 understands how a vol forecast converts to trading P&L
5. Ch 17 vol-targeting section provides a concrete framework for the internship evaluation
