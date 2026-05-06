# Risk as Alpha -- Pitch Presentation Design Spec

## Context

- **Audience:** Head of trading for the floor. Deep understanding of risk systems, SecDB internals, and markets.
- **Format:** Slides (PowerPoint/Google Slides), projected on screen.
- **Duration:** 1 hour total. ~15-18 minutes of presenting, 40+ minutes of Q&A.
- **Goal:** Get buy-in for 20-week internship project. Secondary goal: secure read access to risk cube outputs from SecDB.
- **Date:** April 30, 2026

## Presentation Structure

10 slides. Approach: "Insight-first" -- open with the punchline, back it up with theory and data edge, close with the ask.

---

### Slide 1 -- Title

**Content:**
- Project title: "Risk as Alpha: ML Signal Discovery from Risk-System Outputs"
- Your name
- Date
- Cross-Asset (XA) desk

No clutter. No subtitle paragraph. Just identification.

---

### Slide 2 -- The Thesis

**Headline:** "The risk system already contains predictive signals that theory says should exist."

**Body -- three points:**

1. Intermediary asset pricing theory proves that dealer balance-sheet constraints price risk across asset classes (He-Krishnamurthy 2013, Adrian-Etula-Muir 2014, He-Kelly-Manela 2017).

2. Every external test of this theory uses stale quarterly Fed Z.1 data -- 3-month lag, wrong dealer sign. SecDB produces the real measurement daily, cross-asset, with correct dealer sign.

3. This is a hypothesis test, not a fishing expedition. Every feature has a pre-registered theoretical prediction before any model is trained.

**Delivery notes:** This slide is the entire pitch in 30 seconds. If they interrupt here, you can have the full conversation from this foundation. Don't rush past it.

---

### Slide 3 -- The Theory is Settled

**Headline:** "The theory is settled. The data has been the bottleneck."

**Body -- three papers, one line each:**

- He-Krishnamurthy (2013 AER): risk premia rise nonlinearly when dealer balance-sheet constraints bind
- Adrian-Etula-Muir (2014 JF): single-factor intermediary-leverage SDF, R-squared = 77% on 41 test portfolios
- He-Kelly-Manela (2017 JFE): single pricing kernel across equities, options, CDS, bonds, FX, commodities

**Kicker:**
> "Every one of these papers reconstructs dealer constraints from quarterly Fed Flow-of-Funds tables or Compustat leverage. They proved the theory works with bad data. I want to test it with the real thing."

**Delivery notes:** Don't explain the papers. The head of trading doesn't need an asset pricing lecture. Name-drop to show you've done the reading, then move to the point: data quality is the bottleneck, and you're sitting on the solution.

---

### Slide 4 -- What the Risk System Measures and Why Each Feature Matters

**Headline:** "Five feature families. Each one maps to a specific theoretical mechanism."

**Body -- table:**

| Feature Family | What It Measures | Why It Should Predict |
|---|---|---|
| VaR utilization *(priority)* | How constrained the balance sheet is | Coval-Stafford (2007): when utilization hits the limit, forced selling creates predictable reversals |
| Factor concentration *(priority)* | How crowded risk exposures are | He-Kelly-Manela (2017): low dispersion = hidden concentration, predicts correlated drawdowns |
| VaR dynamics | Risk appetite direction and speed | Adrian-Shin (2010): change in dealer risk exposure forecasts VIX innovations |
| Scenario P&L | Tail exposure asymmetry | Change in worst-case scenario identity signals a regime shift |
| Cross-asset flow | Capital rotation between asset classes | Component VaR migration = balance-sheet reallocation across markets |

**Key line at the bottom:**
> "These aren't proxies. VaR utilization literally *is* the constraint the theory says drives prices. This is the direct measurement."

**Delivery notes:** Spend time here. This is the intellectual core. The head of trading will immediately connect "VaR utilization near the limit" with real experiences of forced deleveraging they've seen. Let that connection happen.

---

### Slide 5 -- What the Model Outputs

**Headline:** "Four prediction targets, each tied to a specific theoretical prediction."

**Body -- table:**

| Target | Why This Target | How It Drives P&L |
|---|---|---|
| VIX innovations | Adrian-Shin (2010) directly shows dealer repos forecast this -- most replicated result | Trade VIX futures, variance swaps, or time hedges -- buying protection before vol spikes instead of after |
| Drawdowns in most-concentrated asset class | Tests the Coval-Stafford fire-sale mechanism specifically | Reduce exposure or go short ahead of forced selling -- front-run the deleveraging you can see coming |
| Cross-asset momentum reversals | He-Kelly-Manela: constraints bind, crowded trades unwind together | Fade crowded momentum at the right time -- the reversal signal tells you *when*, not just *if* |
| Realized volatility | Lowest bar, highest signal-to-noise -- if risk outputs predict anything, this is it | If predicted RV diverges from implied vol, trade the spread -- sell overpriced options, buy underpriced ones |

**Framing line underneath:**
> "These outputs have dual value. As alpha: trade them directly through liquid futures, variance swaps, and options. As risk management: use them to time hedges and size exposures on positions the desk already holds. A signal that tells you to cut your most-concentrated position two days before a forced-selling cascade isn't just alpha -- it's better risk management."

**Additional note:**
> "Even a modest edge on any of these -- IC of 0.03-0.05 -- is tradeable through liquid instruments with real capacity."

**Delivery notes:** Frame as risk management first, alpha second. The head of trading trusts "I can help you see the stress event coming earlier" more than "my model finds alpha." Same outputs, different framing.

---

### Slide 6 -- Two Paths, One Project

**Headline:** "I can execute this two ways. One is dramatically better."

**Body -- two columns or two blocks:**

**Path A -- I calculate risk metrics myself**
- Build historical VaR from position data and market returns I can access
- Compute my own component VaR breakdowns, rolling factor exposures, concentration metrics
- This is doable. I'm prepared to do it.
- But: I spend 3-4 weeks building a crude approximation of what the risk system already does better. My VaR won't match the desk's VaR. I can't compute real utilization without knowing the limits. I'll be testing the theory with a proxy -- which is exactly what the external researchers do with Fed Z.1 data.

**Path B -- Read access to the nightly risk cube outputs**
- The risk system already computes everything I need every night
- I'd be reading outputs, not writing anything, not touching production
- Zero engineering cost to the desk -- the data already exists
- This is the version that tests the theory with the real measurement
- This is the version that can't be done anywhere else

**Delivery notes:** Don't present Path A as a failure mode. Present it as "I have a plan either way" and let the contrast speak for itself. The head of trading will see that Path B is obviously better without you having to argue for it.

---

### Slide 7 -- What I'm Asking For

**Headline:** "A bounded, specific data request."

**The request:**
- Read access to daily firm-level or desk-level VaR with component breakdown by asset class
- At least one of: scenario P&L, factor-VaR decomposition, or VaR utilization (usage vs. limit)
- Historical depth: as far back as available (5 years ideal, 2-3 workable)
- Frequency: daily (end-of-day, after the nightly risk run)
- No write access. No production changes. No real-time feeds. Just a historical pull.

**Addressing sensitivity proactively:**

> "I understand this data is sensitive. Three things that might help:"
> 1. I don't need positions, trades, or P&L. VaR is already an aggregated output -- it reveals nothing about individual strategies or holdings.
> 2. I can work at whatever level of aggregation you're comfortable with. Firm-level is ideal, but asset-class-level component VaR without the firm total is still useful.
> 3. Raw numbers never appear in any deliverable. The output is "factor concentration predicts drawdowns with IC = 0.04 and Sharpe = 0.8." Not "VaR was $X on date Y." I can work in a sandboxed environment.

**The single most valuable feature:**
> "If I get utilization data specifically -- usage vs. limit -- that's the single highest-value feature. It's the direct measurement of the constraint the theory says drives everything. Without it, I can test VaR dynamics and factor concentration, which are still valuable. But utilization is the one you can't approximate from the outside."

**Graceful fallback:**
> "If access isn't workable, I completely understand, and I'll build my own risk metrics and test the same hypothesis. If the self-calculated version shows something promising, that could be a reason to revisit access later."

**Delivery notes:** Be matter-of-fact, not pleading. You're presenting options and letting the senior person decide. The fallback plants a seed -- if you show results with crude data, they might volunteer the real data themselves.

---

### Slide 8 -- How I Make Sure the Results Are Real

**Headline:** "What kills most intern ML projects, and how this one avoids each failure mode."

**Body -- table:**

| What kills projects | How this project handles it |
|---|---|
| Data snooping / p-hacking | Every experiment logged. Deflated Sharpe Ratio (Bailey-Lopez de Prado 2014) adjusts for the total number of things tried. |
| Overfitting to noise | Ridge regression baseline on every test. If LightGBM doesn't beat a simple linear model on the same features, the ML added nothing -- and I report that honestly. |
| Lookahead bias | Point-in-time stamping on every feature. Data stamped with when it was *known*, not when it applied. Holdout period reserved on day one, not touched until the final test. |
| "Impressive backtest, can you trade it?" | Transaction costs baked into every backtest from the start. Sharpe reported gross and net. Breakeven cost level calculated explicitly. |
| Unstable features | Feature importance checked across all CV folds. If a feature flips sign between folds, it gets flagged and dropped. |

**Bottom line:**
> "The validation infrastructure is ~25% of the total project time. I build it before touching any signals. A broken validation stack discovered in week 9 would be fatal."

**Delivery notes:** This slide builds trust. The head of trading has seen plenty of backtests that fell apart. You're telling them you've seen the same thing and you've planned for it. Keep it crisp -- don't explain purged CV unless asked.

---

### Slide 9 -- 20-Week Plan with a Built-In Kill Switch

**Headline:** "Phased plan. Hard checkpoint at Week 13. Pivot option built in."

**Body -- timeline:**

| Weeks | Phase | What You Get |
|---|---|---|
| 1-2 | Pitch & data access | This meeting. Data audit. Aligned on direction. |
| 3-5 | Validation infrastructure | Backtesting engine, validation stack, smoke-tested on synthetic data |
| 6-12 | Signal testing | Each feature family tested independently, ridge vs. LightGBM, SHAP analysis |
| **13** | **Checkpoint** | **Memo with results. Data-driven go/pivot decision. We meet again.** |
| 14-20 | Deepen or pivot, then final report | Regime analysis, cross-asset panel, capacity analysis, presentation |

**Week 13 emphasis:**
> "Week 13 is a hard checkpoint, not a status update. If the signals are flat, I pivot to a second project direction -- book-level Greeks as intraday momentum signals (Baltussen et al. 2021) -- that uses the same infrastructure I've already built. Either way you get a documented result and a rigorous methodology. No sunk cost."

**Delivery notes:** The pivot option is one of the strongest things you can say. It tells the head of trading you won't waste their time. Experienced researchers have backup plans. Interns who are married to one idea are risky.

---

### Slide 10 -- What I Need

**Headline:** The ask, concrete and bounded.

**From you:**
- Sign-off on this project direction
- Data access (or guidance on what's available)
- A 30-minute check-in every 2-3 weeks
- Week 13 checkpoint meeting on the calendar now

**What you get back:**
- Week 13: memo documenting what worked, what didn't, and why
- Week 20: research report with every claim backed by a chart, ridge baseline on every result, transaction-cost analysis, honest negatives included

**What this won't be:**
- Not a black box. Every prediction explained with SHAP.
- Not a fishing expedition. Every feature has a theoretical hypothesis before any model is trained.
- Not an overfit backtest. Deflated Sharpe on every reported number.

**Delivery notes:** End here. No "thank you" slide, no "questions?" slide. Stop on the ask and let the conversation begin. The Q&A is where you'll win or lose -- the slides just set the table.

---

## Presentation Flow Summary

| Slide | Time | Purpose |
|---|---|---|
| 1. Title | 15 sec | Identification |
| 2. Thesis | 2 min | The entire pitch in 30 seconds, then pause for reactions |
| 3. Theory | 2 min | Credibility -- you've read the literature |
| 4. Features | 3-4 min | Intellectual core -- what the risk system measures and why |
| 5. Outputs | 2-3 min | What you're predicting and why it's tradeable |
| 6. Two paths | 2 min | Data situation -- honest about both paths |
| 7. The ask | 2-3 min | Specific, bounded data request with sensitivity addressed |
| 8. Rigor | 2 min | Trust-building -- you know what kills projects |
| 9. Plan | 1-2 min | Timeline with checkpoint |
| 10. What I need | 1 min | Close on the ask |
| **Total** | **~17 min** | **Leaves 43 min for Q&A** |
