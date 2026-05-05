# Vol Learning Guide: Practitioner Gap Additions — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 9 practitioner-oriented sections to the vol-learning-guide, filling gaps between academic theory and trading-floor practice.

**Architecture:** Each task writes one LaTeX section into an existing chapter file, adds any new bib entries to `references.bib`, and verifies the PDF compiles. Full-treatment sections (~3-4 pages) use all box environments; bridge sections (~1 page) use 1-2 boxes max.

**Tech Stack:** LaTeX (report class, tcolorbox, natbib, booktabs, tikz/pgfplots), pdflatex + bibtex on MiKTeX.

**Spec:** `docs/superpowers/specs/2026-05-05-vol-guide-practitioner-gaps-design.md`

---

## Chunk 1: Ch 8 — Local Vol and Var Swap Sections

### Task 1: Add Dupire Local Volatility section to Ch 8

**Files:**
- Modify: `vol-learning-guide/chapters/08-options-vol-surface.tex` (insert after line 554, before `\section{Model-Free Implied Variance and the VIX}`)
- Modify: `vol-learning-guide/references.bib` (add Dupire1994 entry)

- [ ] **Step 1: Add bib entry for Dupire (1994)**

Add to `references.bib`:
```bibtex
@article{Dupire1994,
  author  = {Bruno Dupire},
  title   = {Pricing with a Smile},
  journal = {Risk},
  volume  = {7},
  number  = {1},
  pages   = {18--20},
  year    = {1994},
}
```

- [ ] **Step 2: Write the Local Volatility section**

Insert into `08-options-vol-surface.tex` after line 554 (after the PCA `keyidea` box, before the `\section{Model-Free Implied Variance and the VIX}`). The section should contain:

1. Section header: `\section{Local Volatility}\label{sec:local-vol}`
2. `prereq` box: requires Black-Scholes formula (Section~\ref{sec:bs}), partial derivatives, IV surface concept (Section~\ref{sec:iv-surface})
3. Motivation paragraph: "You have a surface of implied vols. How do you interpolate and extrapolate consistently, without arbitrage?"
4. Derivation of Dupire formula from Fokker-Planck / Breeden-Litzenberger:
   ```
   \sigma_{\text{loc}}^2(K,T) = \frac{\frac{\partial C}{\partial T} + rK\frac{\partial C}{\partial K}}{\frac{1}{2}K^2 \frac{\partial^2 C}{\partial K^2}}
   ```
5. `intuition` box: "Local vol is the instantaneous volatility the market assigns to a specific price level at a specific future time. It is the unique diffusion coefficient that reproduces all observed option prices simultaneously."
6. `workedexample`: Toy surface with 3 strikes (90, 100, 110) and 2 maturities (0.25, 0.50). Compute partial derivatives numerically (finite differences), plug into Dupire formula, get local vol at each (K,T) node. Present as a booktabs table.
7. `warning` box: "Local vol is NOT a forecast. It perfectly fits today's prices but has no predictive content about future vol dynamics. It generates flat forward smiles, which contradicts observed behavior. Use it as an interpolation/arbitrage-free tool, not as a model of reality."
8. `application` (project connection): "Local vol extractions at specific moneyness levels (e.g., 90% and 110% of spot) can serve as features for ML models. They encode the market's current pricing of tail risk at different horizons, complementing backward-looking RV."

- [ ] **Step 3: Compile and verify**

Run: `cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex`
Expected: No errors, PDF output. Warnings about undefined citations are OK at this stage (bibtex not yet rerun).

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/chapters/08-options-vol-surface.tex vol-learning-guide/references.bib
git commit -m "feat(ch8): add Dupire local volatility section"
```

---

### Task 2: Add Variance Swap Mechanics section to Ch 8

**Files:**
- Modify: `vol-learning-guide/chapters/08-options-vol-surface.tex` (insert after existing VIX warning box, ~line 672, before `\section{Connecting the Vol Surface to Volatility Forecasting}`)

- [ ] **Step 1: Write the Variance Swap Mechanics section**

Insert after the VIX `workedexample` (line 671) and before `\section{Connecting the Vol Surface to Volatility Forecasting}` (line 674). The section should contain:

1. Section header: `\section{Variance Swaps: Trading Realized Volatility}\label{sec:var-swap}`
2. `prereq` box: requires model-free implied variance integral (Section~\ref{sec:model-free}), VIX (Section~\ref{sec:vix}), realized variance (Chapter~\ref{ch:rv})
3. Opening motivation: "VIX tells you the fair price of future variance. But how do you actually trade it? The variance swap is the instrument that lets you take a direct position on realized vol."
4. Definition of variance swap: notional, strike K_var, settlement at expiry = notional * (RV^2 - K_var). Define variance notional vs vega notional (vega-notional = var-notional * 2*K_var).
5. Log-contract replication argument (1 paragraph): "The key theoretical result: if you hold a portfolio of OTM options weighted by 1/K^2, its payoff at expiry replicates -2*log(S_T/S_0). The realized P&L of continuously delta-hedging this portfolio equals the realized variance. Therefore, the cost of this portfolio (= the integral from the model-free section) equals K_var. Back-reference to Equation in Section~\ref{sec:model-free}."
6. `workedexample`: Discretize with 5 OTM puts (strikes 90-98) and 5 OTM calls (strikes 102-110), given specific prices. Compute K_var via the discrete sum. Compare to VIX^2/100^2. Show the truncation error from missing deep OTM strikes.
   - Present strikes, prices, weights (1/K^2), weighted prices in a booktabs table
   - Sum to get K_var
   - Note: "If VIX = 20, then VIX^2/10000 = 0.04. Our discrete approximation gives 0.0387. The gap is truncation error from missing strikes below 90 and above 110."
7. `intuition` box: "A variance swap lets you trade your RV forecast directly. If you believe RV will be 20% but K_var = 18%, you buy the swap and profit if realized vol exceeds the strike. Your P&L at expiry is simply notional * (sigma_realized^2 - sigma_strike^2). No path dependence, no Greeks to manage -- just a pure bet on realized variance."
8. `warning` box: "Convexity adjustment: a vol swap (payoff = sigma_realized - K_vol) is NOT the same as a var swap. Because E[sigma] < sqrt(E[sigma^2]) (Jensen's inequality), a vol swap strike is lower than sqrt(var swap strike). The gap depends on vol-of-vol. Also: before expiry, var swaps have mark-to-market risk as implied vol moves."
9. `application` (project connection): "VIX^2/10000 minus your forecast of 30-day RV = variance risk premium. This is the key signal for Project 5 (VRP ML trader). The variance swap makes VRP a tradeable quantity: if your ML model predicts RV more accurately than the market, you can systematically harvest the mispricing."

- [ ] **Step 2: Compile and verify**

Run: `cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add vol-learning-guide/chapters/08-options-vol-surface.tex
git commit -m "feat(ch8): add variance swap mechanics section"
```

---

## Chunk 2: Ch 9 — Gamma P&L Formula

### Task 3: Add Gamma P&L and Delta-Hedging Economics section to Ch 9

**Files:**
- Modify: `vol-learning-guide/chapters/09-variance-risk-premium.tex` (insert after line 322, before `\section{Vol-of-Vol}`)

- [ ] **Step 1: Write the Gamma P&L section**

Insert after the `keyidea[Most of VRP Is About Crash Fear]` box (line 322) and before `\section{Vol-of-Vol}` (line 326). The section should contain:

1. Section header: `\section{The Gamma P\&L Formula: From Forecast to Money}\label{sec:gamma-pnl}`
2. `prereq` box: requires delta and gamma (Chapter~\ref{ch:volsurface}, Section~\ref{sec:bs}), variance swap strike (Section~\ref{sec:var-swap}), VRP definition (Section~\ref{sec:vrp-definition} earlier in this chapter)
3. Opening motivation: "You have built an ML model that forecasts RV more accurately than the options market implies. How much money does that improved forecast generate? This section derives the exact formula."
4. Setup: "Consider a trader who buys an option at implied vol sigma_i and delta-hedges continuously. Each day, the option's value changes due to two effects: (a) the delta-hedged P&L from the stock's realized move, and (b) time decay (theta)."
5. Key derivation:
   - From Black-Scholes PDE: Theta + 0.5*Gamma*S^2*sigma_i^2 = r*V (for a delta-hedged position, the stock component nets out)
   - Actual P&L per day: dP&L = 0.5*Gamma*S^2*(r_t^2 - sigma_i^2 * dt)
   - Over a full period: total P&L = sum of 0.5*Gamma_t * S_t^2 * (sigma_r,t^2 - sigma_i^2) * dt
   - Simplification for ATM (Gamma roughly constant): P&L approx 0.5*Gamma*S^2*(RV^2 - IV^2)*T
6. `keyidea` box with the formula prominently displayed:
   ```
   \text{Daily Hedging P\&L} = \frac{1}{2}\,\Gamma\,S^2\,\bigl(\sigma_{\text{realized}}^2 - \sigma_{\text{implied}}^2\bigr)\,\Delta t
   ```
   "Positive gamma profits when realized vol exceeds implied vol. Negative gamma profits when realized vol is below implied vol. The VRP (IV > RV on average) means selling gamma is systematically profitable."
7. `workedexample`: Buy a 30-day ATM straddle on a stock at S=100, IV=18%. Delta-hedge daily. Over 5 days, stock path: 100, 101.2, 99.8, 100.5, 102.1, 101.0. Compute daily squared returns, compare to (0.18)^2/252. Show daily P&L = 0.5*Gamma*S^2*(r_t^2 - sigma_i^2/252). Use Gamma = 0.04 (approximate ATM gamma for this option). Present as a table:
   | Day | S | r_t | r_t^2 | sigma_i^2*dt | Gamma P&L |
   After 5 days, net P&L = sum. "The realized vol over these 5 days was 22% annualized, above the 18% we paid. The cumulative gamma P&L is positive."
8. `intuition` box: "Think of it as renting a magnifying glass (gamma). Each day you earn the difference between what actually happened (r^2) and what you paid for (sigma_i^2 * dt). On average, if your vol forecast is right and the market's is wrong, you accumulate profit proportional to the forecast error times your gamma exposure."
9. `warning` box: "Path dependence: gamma is NOT constant. As the stock moves away from the strike, gamma falls. Two stock paths with identical 30-day realized vol can produce very different hedging P&L because gamma was high during the low-vol days and low during the high-vol days. This is why forecasting WHEN vol occurs (intraday patterns, jump timing) matters, not just the average level."
10. `application` box: "For your internship evaluation: a 5% QLIKE improvement in your RV forecast means you can identify days when the market misprices vol by more. In a vol-trading context, this translates to approximately 2-5 bps per unit of vega exposure per day (order of magnitude). The exact number depends on your Gamma profile and hedging frequency. Section~\ref{sec:vol-targeting} quantifies this via a simpler mechanism (vol-targeting Sharpe)."

- [ ] **Step 2: Compile and verify**

Run: `cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add vol-learning-guide/chapters/09-variance-risk-premium.tex
git commit -m "feat(ch9): add gamma P&L formula and delta-hedging economics"
```

---

## Chunk 3: Bridge Sections (Ch 3, Ch 7)

### Task 4: Add Adverse Selection bridge to Ch 3

**Files:**
- Modify: `vol-learning-guide/chapters/03-microstructure-noise.tex` (insert after line 63, before `\subsection{Quantifying the Bias}`)
- Modify: `vol-learning-guide/references.bib` (add GlostenMilgrom1985, Kyle1985)

- [ ] **Step 1: Add bib entries**

Add to `references.bib`:
```bibtex
@article{GlostenMilgrom1985,
  author  = {Lawrence R. Glosten and Paul R. Milgrom},
  title   = {Bid, Ask and Transaction Prices in a Specialist Market with Heterogeneously Informed Traders},
  journal = {Journal of Financial Economics},
  volume  = {14},
  number  = {1},
  pages   = {71--100},
  year    = {1985},
  doi     = {10.1016/0304-405X(85)90044-3},
}

@article{Kyle1985,
  author  = {Albert S. Kyle},
  title   = {Continuous Auctions and Insider Trading},
  journal = {Econometrica},
  volume  = {53},
  number  = {6},
  pages   = {1315--1335},
  year    = {1985},
  doi     = {10.2307/1913210},
}
```

- [ ] **Step 2: Write the adverse selection bridge**

Insert after the `intuition[Why Noise Kills High-Frequency RV]` box (line 63) and before `\subsection{Quantifying the Bias}` (line 65). Content:

1. Paragraph header: `\paragraph{Source 4: Adverse selection (information asymmetry).}`
2. Content (~15 lines): "Beyond mechanical noise, spreads reflect a deeper economic force. \citet{GlostenMilgrom1985} showed that market makers widen spreads because some counterparties possess private information. The bid-ask spread must compensate for losses to informed traders:
   ```
   s_t \propto \alpha \cdot \sigma_v
   ```
   where alpha is the probability the counterparty is informed and sigma_v is the volatility of the information signal. When volatility is high, information asymmetry increases (there is more to know), so spreads widen mechanically. This creates a feedback loop: high vol -> wider spreads -> more noise in transaction prices -> more biased RV estimates."
3. One-line connection: "This means microstructure noise is not merely a nuisance to filter; it carries information about market quality and informed-trading intensity that can itself predict future volatility (Chapter~\ref{ch:features})."
4. Brief reference to autocovariance interpretation: "A related insight from \citet{Kyle1985}: the first-order autocovariance of price changes satisfies Cov(dp_t, dp_{t+1}) = -s^2/4. This connects the noise-robust estimators developed later in this chapter (which exploit autocovariance structure) to a liquidity interpretation."

- [ ] **Step 3: Compile and verify**

Run: `cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex`

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/chapters/03-microstructure-noise.tex vol-learning-guide/references.bib
git commit -m "feat(ch3): add adverse selection bridge section"
```

---

### Task 5: Add Path-Dependence bridge to Ch 7

**Files:**
- Modify: `vol-learning-guide/chapters/07-rough-volatility.tex` (insert after line 19, before `\section{What Is Roughness?}`)

- [ ] **Step 1: Write the path-dependence bridge**

Insert after the paragraph ending "what kind of stochastic process would generate the autocorrelation structure we observe?" (line 19) and before `\section{What Is Roughness?}` (line 22). Content:

1. Section header: `\section{Why Path Shape Matters: A Hedging Motivation}\label{sec:path-dependence}`
2. Opening (2 paragraphs): "Before diving into the mathematics of roughness, consider a practical puzzle that motivates the entire chapter.

An options trader buys a 30-day ATM straddle and delta-hedges daily. Over the month, realized vol comes in at exactly 20%. But the trader's P\&L depends on \emph{when} the moves happened, not just their aggregate size."

3. `intuition` box [Two Paths, Same RV, Different P&L]: "Path A: stock drifts quietly for 25 days then has 5 days of extreme moves. Path B: moves are spread evenly across all 30 days. Both paths have identical 30-day RV = 20\%. But the trader's cumulative gamma P\&L (Section~\ref{sec:gamma-pnl}) differs because:
   - Gamma varies with moneyness: it is highest when the stock is near the strike.
   - On Path A, most of the vol occurs after the stock has moved away from the strike (gamma is low), so the trader captures less.
   - On Path B, moves happen while gamma is still high, so the trader captures more.
   
   The conclusion: forecasting *average* realized vol is necessary but not sufficient. The *texture* of the path -- how vol is distributed across time and price levels -- also determines economic outcomes."

4. Connection paragraph: "This is exactly what rough volatility (H << 0.5) captures: rough paths have more fine-grained variation at short time scales, meaning the vol arrives in frequent small bursts rather than rare large moves. For a delta-hedger, rough paths produce more predictable P\&L (the vol arrives continuously rather than in lumps). \citet{RosenbaumZhang2022} showed that both the universal LSTM and the parametric rough-vol model converge on this same characterization of the volatility process -- one from data, one from theory."

- [ ] **Step 2: Compile and verify**

Run: `cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex`

- [ ] **Step 3: Commit**

```bash
git add vol-learning-guide/chapters/07-rough-volatility.tex
git commit -m "feat(ch7): add path-dependence bridge motivating roughness"
```

---

## Chunk 4: Ch 10 — Feature Engineering Additions

### Task 6: Add Microprice and Volume Features subsection to Ch 10

**Files:**
- Modify: `vol-learning-guide/chapters/10-feature-engineering.tex` (insert at end of Section "Microstructure and LOB Features", after line 308, before `\section{Options-Implied Features}`)
- Modify: `vol-learning-guide/references.bib` (add CarteaJaimungalPenalva2015)

- [ ] **Step 1: Add bib entry**

Add to `references.bib`:
```bibtex
@book{CarteaJaimungalPenalva2015,
  author    = {Cartea, {\'A}lvaro and Jaimungal, Sebastian and Penalva, Jos{\'e}},
  title     = {Algorithmic and High-Frequency Trading},
  publisher = {Cambridge University Press},
  year      = {2015},
  isbn      = {978-1-107-09114-3},
}
```

- [ ] **Step 2: Write microprice and volume features subsection**

Insert after the `warning[Microstructure features are asset-specific]` box (line 308) and before `\section{Options-Implied Features}` (line 311). Content:

1. Subsection header: `\subsection{Microprice and Volume Features}\label{sec:feat-microprice}`
2. **Microprice** paragraph: "The simple midprice $(P_{\text{bid}} + P_{\text{ask}})/2$ assigns equal weight to both sides of the book regardless of depth. The \textbf{microprice} \citep{CarteaJaimungalPenalva2015} corrects for this:"
   ```
   S^*_t = \frac{V_t^{\text{ask}} \cdot P_t^{\text{bid}} + V_t^{\text{bid}} \cdot P_t^{\text{ask}}}{V_t^{\text{bid}} + V_t^{\text{ask}}}
   ```
   "When bid volume dominates (buyers are eager), the microprice shifts toward the ask (fair value is higher). Computing returns from microprice rather than midprice reduces bid-ask-bounce noise in your RV estimate without needing a formal noise-robust estimator."
3. **Volume features** paragraph: "Daily trading volume is highly correlated with daily volatility -- this is the well-known volume-volatility relationship (Karpoff 1987). More usefully for forecasting, volume is \emph{persistent}: high-volume days tend to cluster, just like high-vol days. This means volume features can serve as leading indicators:
   - log(volume / MA20\_volume): normalized volume, >0 means above-average activity
   - Volume acceleration: change in log-volume over the past 3 days
   - Microprice--midprice deviation: |S^* - S\_mid| as a measure of book imbalance pressure"
4. `keyidea` box [Volume Predicts Vol]: "Abnormal volume today predicts elevated RV tomorrow, even after controlling for lagged RV. The intuition: volume spikes reflect new information arriving (earnings whispers, large block trades, portfolio rebalancing) that has not yet fully resolved into price moves. Include at least one volume feature in any feature set."

- [ ] **Step 3: Compile and verify**

Run: `cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex`

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/chapters/10-feature-engineering.tex vol-learning-guide/references.bib
git commit -m "feat(ch10): add microprice and volume features subsection"
```

---

### Task 7: Add Event-Driven Vol Features subsection to Ch 10

**Files:**
- Modify: `vol-learning-guide/chapters/10-feature-engineering.tex` (insert at end of Section "Calendar and Event Features", after line 504, before `\section{Sentiment and Text Features}`)

- [ ] **Step 1: Write event-driven vol features subsection**

Insert after the `warning[Calendar features are supplements, not drivers]` box (line 504) and before `\section{Sentiment and Text Features}` (line 507). Content:

1. Subsection header: `\subsection{Event-Driven Volatility: Beyond Binary Dummies}\label{sec:feat-event-vol}`
2. Opening paragraph: "The basic calendar dummies above capture whether an event occurs. But events affect volatility in richer ways that better feature engineering can exploit."
3. **Term structure kinks**: "Before a known event (e.g., FOMC on Wednesday), the IV term structure shows a characteristic kink: the option expiring just after the event has elevated IV (it straddles the uncertainty), while the option expiring just before has lower IV (the event is not included). The magnitude of this kink -- the 'event-implied vol' -- quantifies how much extra vol the market expects from the event. Extract it as: sigma\_event = sqrt((T2*IV2^2 - T1*IV1^2) / (T2 - T1)) for expiries bracketing the event."
4. **Historical event-day RV ratios**: "Compute the ratio RV(event day) / RV(surrounding days) historically for each event type. FOMC days typically show 1.5-2x normal RV; NFP days show 1.3-1.5x. Use these ratios as multiplicative adjustments to your baseline forecast on event days."
5. **Days-to-next-event features**: "Rather than a binary 'is today an event,' encode continuous distance: days\_to\_FOMC, days\_since\_FOMC, days\_to\_earnings. This lets the model learn the anticipation buildup and post-event decay."
6. `warning` box [Look-Ahead Risk with Events]: "Earnings dates are announced approximately 2-4 weeks before the event. FOMC dates are published annually. These are safe to use. But some events (emergency Fed meetings, unscheduled news) cannot be known in advance. Never include an event indicator for a date that was not knowable at time $t-1$. For earnings, use the \emph{announced} date, not the ex-post actual date (companies occasionally reschedule)."

- [ ] **Step 2: Compile and verify**

Run: `cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex`

- [ ] **Step 3: Commit**

```bash
git add vol-learning-guide/chapters/10-feature-engineering.tex
git commit -m "feat(ch10): add event-driven vol features subsection"
```

---

## Chunk 5: Ch 17 — Applications (Vol Targeting + Dealer Gamma)

### Task 8: Write Ch 17 skeleton + Vol Targeting section

**Files:**
- Modify: `vol-learning-guide/chapters/17-applications-projects.tex` (replace TODO with full chapter content)
- Modify: `vol-learning-guide/references.bib` (add MoreiraMuir2017, MoskowitzOoiPedersen2012)

- [ ] **Step 1: Add bib entries**

Add to `references.bib`:
```bibtex
@article{MoreiraMuir2017,
  author  = {Alan Moreira and Tyler Muir},
  title   = {Volatility-Managed Portfolios},
  journal = {The Journal of Finance},
  volume  = {72},
  number  = {4},
  pages   = {1611--1644},
  year    = {2017},
  doi     = {10.1111/jofi.12513},
}

@article{MoskowitzOoiPedersen2012,
  author  = {Tobias J. Moskowitz and Yao Hua Ooi and Lasse Heje Pedersen},
  title   = {Time Series Momentum},
  journal = {Journal of Financial Economics},
  volume  = {104},
  number  = {2},
  pages   = {228--250},
  year    = {2012},
  doi     = {10.1016/j.jfineco.2011.11.003},
}
```

- [ ] **Step 2: Write Ch 17 intro + Vol Targeting section**

Replace the entire content of `17-applications-projects.tex` with:

1. Chapter header and intro:
   ```latex
   \chapter{Practical Applications and Project Directions}
   \label{ch:applications}
   
   \begin{application}[Why This Chapter]
   The preceding chapters built a toolkit: estimators, forecasters, features, and evaluation methods.
   This chapter answers the question every trading desk asks: ``so what?''
   It translates statistical forecast accuracy into economic value -- the language that gets a model deployed.
   \end{application}
   
   A model that beats HAR by 8\% on QLIKE is scientifically interesting.
   But a desk head wants to know: how much Sharpe does that buy me?
   How much P\&L does it add to my book?
   This chapter provides the frameworks for answering those questions.
   ```

2. `\section{Volatility Targeting: The Simplest Economic Value Test}\label{sec:vol-targeting}`

3. `prereq` box: requires portfolio returns, Sharpe ratio, RV forecasts from Chapters~\ref{ch:har}--\ref{ch:hybrid}

4. Opening: "Volatility targeting is the simplest and most widely used application of a vol forecast in systematic investing. The idea: size your position inversely proportional to forecast vol, so that portfolio risk stays roughly constant over time."

5. EWMA baseline:
   ```
   \hat\sigma^2_t = (1-\delta)\,r_{t-1}^2 + \delta\,\hat\sigma^2_{t-1}
   ```
   "where delta is chosen so the half-life matches approximately 20-60 trading days. This is what most funds actually use for position sizing -- not GARCH, not HAR, just exponential smoothing."

6. Vol-targeting formula:
   ```
   w_t = \frac{\sigma_{\text{target}}}{\hat\sigma_t}
   ```
   "The portfolio return is r_t^{\text{VT}} = w_t * r_t. When forecast vol is high, w_t < 1 (reduce position). When forecast vol is low, w_t > 1 (lever up)."

7. `intuition` box: "\citet{MoreiraMuir2017} showed that vol-targeting adds approximately 0.3 Sharpe ratio across equity indices, currencies, and commodities. The mechanism: by reducing exposure before drawdowns, vol-targeting truncates the left tail. A better vol forecast means you cut exposure earlier and more precisely."

8. `workedexample` [Vol-Targeting the S&P 500]:
   "Target: sigma_target = 10% annualized. Compare three forecasts:
   (a) EWMA (half-life 20 days): the baseline every fund already uses
   (b) HAR: three-component model from Chapter~\ref{ch:har}
   (c) ML (best model from Chapter~\ref{ch:trees} or \ref{ch:deep}): your contribution

   Setup: 20 trading days. Present a table with columns: Day, r_t (%), sigma_EWMA, w_EWMA, r_VT_EWMA, sigma_HAR, w_HAR, r_VT_HAR, sigma_ML, w_ML, r_VT_ML.

   Use a realistic scenario: days 1-15 are calm (realized ~12%), then days 16-20 see a sell-off (realized ~35% annualized). The ML model detects the regime change on day 14 (before the sell-off starts); EWMA reacts slowly.

   Bottom row: annualized Sharpe, max drawdown for each. Show that the ML forecast produces a higher Sharpe (avoids the drawdown) and lower max drawdown."

9. TSMOM connection paragraph: "\citet{MoskowitzOoiPedersen2012} use a related framework for time-series momentum across 58 futures: signal = sign(12-month return), position size = 40\%/sigma\_t. The vol forecast enters the denominator. Every percentage improvement in your forecast precision tightens the position-sizing, reducing both crash risk and unnecessary leverage."

10. `warning` box: "Vol targeting assumes volatility is predictable but returns are not. If your forecast systematically underpredicts during crises (all ML models trained on normal data underpredict COVID-style jumps), vol targeting will keep positions too large going into the drawdown. Mitigation: ensemble your ML forecast with a simple max(ML, EWMA*1.5) floor during high-uncertainty regimes, or cap w\_t at a maximum leverage ratio."

11. `application` box: "For your internship deliverable, the key table is: (1) run vol-targeted long-SPX using each model; (2) report annualized return, vol, Sharpe, max drawdown, and Calmar ratio; (3) compute Sharpe improvement per 1\% QLIKE improvement. This single table communicates economic value in the language every systematic desk speaks."

- [ ] **Step 3: Compile and verify**

Run: `cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex`

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/chapters/17-applications-projects.tex vol-learning-guide/references.bib
git commit -m "feat(ch17): write chapter intro + vol targeting section"
```

---

### Task 9: Add Structured Products / Dealer Gamma section to Ch 17

**Files:**
- Modify: `vol-learning-guide/chapters/17-applications-projects.tex` (append after vol targeting section)
- Modify: `vol-learning-guide/references.bib` (add Bennett2014)

- [ ] **Step 1: Add bib entry**

Add to `references.bib`:
```bibtex
@book{Bennett2014,
  author    = {Colin Bennett},
  title     = {Trading Volatility: Trading Volatility, Correlation, Term Structure and Skew},
  publisher = {Self-published},
  year      = {2014},
}
```

- [ ] **Step 2: Write dealer gamma section**

Append to end of `17-applications-projects.tex`:

1. Section header: `\section{Dealer Gamma and Structured Products Feedback}\label{sec:dealer-gamma}`

2. Opening paragraph: "Beyond statistical forecasting, volatility is shaped by the mechanical hedging behavior of options dealers. When dealers hold large gamma positions, their hedging creates predictable effects on realized vol. Understanding this mechanism gives you both a novel feature and a deeper appreciation for what your model is capturing."

3. Paragraph on dealer long gamma: "When dealers are \emph{long} gamma (they own options), they delta-hedge by selling into rallies and buying dips. This mean-reversion pressure suppresses realized volatility below what pure news flow would generate. Conversely, when dealers are \emph{short} gamma (common after selling structured products like autocallables), they hedge by buying into rallies and selling into dips -- amplifying moves and increasing realized vol."

4. `keyidea` box [GEX as a Feature]: "Gamma Exposure (GEX) estimates the net dealer gamma across all strikes from publicly available options open interest data. The estimate is approximate but directionally informative:
   ```
   \text{GEX} \approx \sum_{\text{strikes}} \text{OI}_K \times \Gamma_K \times 100 \times S
   ```
   Positive GEX (dealers long gamma): expect lower-than-forecast RV (mean reversion).
   Negative GEX (dealers short gamma): expect higher-than-forecast RV (momentum/amplification).
   Adding sign(GEX) or GEX-quintile as a feature to HAR-X is a novel extension not yet thoroughly explored in the academic literature \citep{Bennett2014}."

5. Paragraph on structured products: "The primary source of dealer short-gamma exposure is structured products (autocallables, barrier options, worst-of notes). These products embed knock-in/knock-out barriers near current spot levels. As spot approaches a barrier, the product's gamma becomes very negative, forcing dealers to hedge aggressively. The systematic issuance of these products (estimated at hundreds of billions of notional globally) creates a permanent structural short-gamma overhang in equity index markets."

6. Paragraph on pin risk: "Near options expiry, large open interest at specific strikes creates 'pinning' effects: the stock gravitates toward the strike as dealers' gamma hedging intensifies near that level. This suppresses realized vol on expiry days -- a calendar effect (Section~\ref{sec:feat-calendar}) with a mechanical explanation."

7. `application` box: "Dealer positioning features (GEX, distance to nearest barrier level, net open interest by strike) represent a genuinely novel addition to standard HAR-X feature sets. They are publicly computable from options market data and capture a mechanism (mechanical hedging feedback) that is distinct from any feature based on past returns or past RV. For your internship, including a GEX feature and documenting its incremental predictive power would demonstrate awareness of market microstructure that goes beyond the academic literature."

- [ ] **Step 3: Compile and verify**

Run: `cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex`

- [ ] **Step 4: Commit**

```bash
git add vol-learning-guide/chapters/17-applications-projects.tex vol-learning-guide/references.bib
git commit -m "feat(ch17): add dealer gamma and structured products section"
```

---

## Chunk 6: Final Compilation and Verification

### Task 10: Full rebuild with bibtex and cross-reference resolution

**Files:**
- All modified files from Tasks 1-9

- [ ] **Step 1: Full compilation cycle**

```bash
cd vol-learning-guide
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

Expected: PDF compiles with no errors. Only warnings should be cosmetic (overfull hboxes, etc.). All citations resolve. No "undefined reference" warnings for labels defined in this plan.

- [ ] **Step 2: Check page count and verify new sections appear**

Run: `pdflatex -interaction=nonstopmode main.tex 2>&1 | grep "Output written"`
Expected: ~220-230 pages (up from 201).

- [ ] **Step 3: Verify no duplicate labels**

Run: `grep -c "multiply defined" main.log`
Expected: 0 (or only pre-existing duplicate from `eq:rq` which was there before)

- [ ] **Step 4: Final commit**

```bash
git add -A vol-learning-guide/
git commit -m "chore: final compilation pass, resolve all cross-references"
```
