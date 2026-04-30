# Speaker Script -- v2 (Product Pitch)

Read alongside the slides. Not a teleprompter script, but a reference so you never lose your thread. Pause points and delivery cues are marked.

Target time: ~15-17 minutes total.

---

## Slide 1 -- Title
**[~20 seconds]**

"Thank you for taking the time. I want to walk you through an index product I've been developing -- what it does, why the theory says it should work, and why GS is uniquely positioned to run it."

**[Advance to Slide 2]**

---

## Slide 2 -- The Product
**[~4-5 minutes]**

**[Open with the headline]**

"This is a rules-based, daily-rebalanced index that turns risk-system outputs into tradeable predictions. It forecasts volatility events, drawdowns, and momentum reversals across asset classes, and it trades through liquid instruments -- VIX futures, variance swaps, options."

**[Walk through the left column]**

"The mechanics: risk data comes in nightly, features are constructed with point-in-time stamping, a linear model and LightGBM run side by side on identical features, and the output is a set of daily signals that map to specific instruments."

**[Transition to dual value -- spend time here]**

"This index has two uses. First, as a product. It's publishable -- clients buy exposure through structured notes or swaps. There's a public-data version they can audit and verify. Second, and probably the more immediate value, as a risk management tool. It times hedges, sizes exposures, and flags stress events two to three days earlier than you'd otherwise see them."

**[Pause, then deliver the key line]**

"A signal that tells you to cut your most-concentrated exposure two days before a forced-selling cascade isn't just alpha -- it's better risk management for positions the desk already holds."

**[Trace the pipeline strip quickly -- gesture across the flow]**

"The pipeline is straightforward. Risk system to features, features to models, models to predictions, predictions to index. Everything downstream of the risk system is automated and reproducible."

**[Land the IC line]**

"Even a modest edge -- IC of 0.03 to 0.05 -- is tradeable through liquid instruments with real capacity. This isn't a strategy that needs large moves to work."

"So why should this work? The theory is strong, and the features are specific."

**[Advance to Slide 3]**

---

## Slide 3 -- Why It Works
**[~4-5 minutes]**

**[Let the stat cards land before speaking -- give them three to four seconds]**

"The theory behind this index isn't speculative. Three numbers."

**[Point to 77%]**

"A 2014 paper showed that a single factor based on intermediary leverage explains 77% of the cross-section of 41 test portfolios. For one factor, that's remarkable."

**[Point to 6]**

"A follow-up extended this to a single pricing kernel across six asset classes -- equities, options, CDS, bonds, FX, and commodities. That cross-asset result is why the XA desk is the right home for this product."

**[Point to Daily]**

"And this is the gap. Every one of these results used quarterly data. Our risk system produces this daily. That frequency advantage is what this index is built on."

**[Transition to feature table]**

"Five families of features, each backed by published research. Let me focus on the two priorities."

**[Point to VaR utilization row]**

"VaR utilization -- usage as a percentage of the limit. This is the most direct measurement of balance-sheet constraints. When utilization approaches the limit, forced selling follows. There's a well-known 2007 paper showing that forced selling by constrained institutions creates predictable reversals. Utilization measures how close we are to that trigger."

**[Point to factor concentration row]**

"Factor concentration -- a Herfindahl index across the factor-VaR decomposition. When risk is concentrated in a few factors rather than diversified, that's crowding. The literature shows that hidden concentration predicts correlated drawdowns."

**[Gesture to remaining three rows -- don't linger]**

"The remaining three: VaR dynamics captures risk appetite shifts, scenario P&L captures how tail risk is changing, cross-asset flow captures capital rotating between asset classes."

**[Pause, then deliver the key line]**

"These aren't proxies. VaR utilization literally is the constraint the theory says drives prices."

"These signals should exist in any dealer's risk system. But testing them requires the right data -- and there's a massive gap between what's publicly available and what SecDB produces."

**[Advance to Slide 4]**

---

## Slide 4 -- Why Only GS
**[~3-4 minutes]**

**[Gesture to left column]**

"On the left -- what every external researcher works with. Quarterly, three-month lag, aggregated across all banks, no dealer sign."

**[Gesture to right column data edge]**

"On the right -- what SecDB produces every night. Daily, available next morning, desk-level granularity, correct dealer sign."

**[Transition to right side -- two-tier structure]**

"And here's the product structure. The public index is built on public data -- clients can audit it, verify the methodology, buy exposure through notes or swaps. The internal enhanced version uses SecDB inputs -- same methodology, better data. The performance gap between the two is GS's competitive advantage."

**[Mention data access naturally -- NOT as a request, just a statement of fact]**

"And with access to VaR data, the internal version gets even stronger."

**[Pause, then deliver the key line]**

"The theory was proved with quarterly proxies. The internal version uses the real measurement. That gap is the product's moat."

"Here's how I execute this."

**[Advance to Slide 5]**

---

## Slide 5 -- Plan & Rigor
**[~3-4 minutes]**

**[Walk through timeline -- keep it brisk]**

"Twenty weeks, five phases. Weeks one and two, alignment and data audit. Weeks three through five, I build the validation infrastructure and smoke-test it on synthetic data. Weeks six through twelve, core signal testing -- each feature family tested independently, linear baseline alongside the ML."

**[Emphasize the checkpoint]**

"Week thirteen is a hard checkpoint -- not a status update. If the signals are flat, I pivot to a second direction that uses the same infrastructure. Either way you get a documented result."

"Weeks fourteen through twenty, deepen what's working -- regime analysis, cross-asset panel tests, capacity analysis -- and consolidate into the final deliverables."

**[Transition to rigor table -- keep it crisp, one sentence per row]**

"Five things that kill projects like this, and how I handle each."

"Data snooping -- every experiment logged, Deflated Sharpe Ratio adjusts for how many things I tried."

"Overfitting -- a simple linear model runs first on every feature set. If the ML doesn't beat it, the ML added nothing."

"Lookahead -- every feature stamped with when the data was known, not when it applied. Holdout reserved on day one."

"Costs -- baked into every backtest, Sharpe reported gross and net."

"Stability -- if a feature flips sign across validation folds, it gets flagged."

**[Land on deliverables]**

"What you get: a memo at Week 13, and at Week 20 a research report plus a full index specification -- every claim backed by a chart, ridge baseline on all results, transaction costs included."

**[End on "what this won't be" -- deliver with conviction]**

"Three things this won't be. Not a black box -- every prediction explained with SHAP. Not a fishing expedition -- every feature has a hypothesis before any model runs. Not an overfit backtest -- Deflated Sharpe on every reported number."

**[Stop here. Don't say "any questions?" -- just pause and let the conversation happen naturally.]**

---

## General Delivery Notes

- **Pace:** Slightly slower than natural. You have plenty of time.
- **If interrupted early:** Good -- it means they're engaged. Let the conversation flow. Come back to later slides if needed.
- **If asked something you don't know:** "I don't know, but I'll find out and get back to you by [specific time]." Never bluff.
- **If they push back on the index concept:** Explain the two-tier structure -- public for clients, internal for GS's edge. The public version is auditable; the internal version is the competitive advantage.
- **Tone:** Confident, not cocky. "This index" and "this product," not "this project." You're pitching something you've built, not asking permission to start.
- **Data access:** If they ask about data needs, keep it matter-of-fact. You're not requesting -- you're describing what makes the internal version better. If they offer access, great. If not, the public-data version still works.
- **The battle card:** Have `qa_battle_card.md` open in a separate window. You won't read from it, but it's there if a question catches you off guard.
