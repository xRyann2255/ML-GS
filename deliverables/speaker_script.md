# Speaker Script

Read alongside the slides. Not a teleprompter script, but a reference so you never lose your thread. Pause points and delivery cues are marked.

Target time: ~17 minutes total.

---

## Slide 1 -- Title
**[~20 seconds]**

"Thank you for taking the time. I know you've had some ideas you wanted to explore -- I'd love to hear about those. Let me first walk you through what I've been developing so you have context, and then we can talk about how to bring things together."

**[Advance to Slide 2]**

---

## Slide 2 -- The Thesis
**[~2 minutes]**

"Here's the idea in one sentence. Intermediary asset pricing theory proves that dealer balance-sheet constraints price risk across asset classes. Our risk system measures those constraints every day. I want to test whether those outputs predict returns, volatility, and drawdowns."

**[Pause -- let them read the slide]**

"The reason this hasn't been tested before is a data problem. Every external researcher has had to reconstruct dealer constraints from quarterly Fed Z.1 tables -- data published with a three-month lag, wrong sign conventions, aggregated across the entire banking sector. They proved the theory works despite bad data. We have the real measurement, daily, cross-asset, with the correct dealer sign."

"This is not a fishing expedition. Every feature I test has a reason from the theory for why it should work. If it doesn't, I document that and move on."

**[Advance to Slide 3]**

---

## Slide 3 -- The Theory is Settled
**[~2 minutes]**

**[Let the three numbers land before speaking]**

"Three numbers tell the story."

**[Point to 77%]**

"Adrian, Etula, and Muir showed that a single factor based on intermediary leverage explains 77% of the cross-section of 41 test portfolios. Remarkable for a single factor."

**[Point to 6]**

"He, Kelly, and Manela extended this to a single pricing kernel across six asset classes -- equities, options, CDS, bonds, FX, and commodities. A cross-asset result, which is why the XA desk is the right home for this."

**[Point to Daily]**

"And this is the gap. Every one of these results used quarterly data. Our risk system produces this daily."

**[Slightly slower]**

"He and Krishnamurthy showed that risk premia rise nonlinearly when dealer constraints bind. Adrian and Shin showed dealer repos forecast VIX moves. Every paper used crude proxies. The theory works with bad data. The question is whether it works better with the real thing."

**[Advance to Slide 4]**

---

## Slide 4 -- The Data Edge
**[~1 minute. The visual does the work -- don't read every bullet.]**

**[Gesture to left column]**

"On the left -- what every external researcher works with. Quarterly, three-month lag, aggregated across all banks, no dealer sign."

**[Gesture to right column]**

"On the right -- what SecDB produces every night. Daily, available next morning, desk-level granularity, correct dealer sign, with utilization, factor decomposition, and scenario P&L."

"This isn't an incremental improvement. The theory was proved with the left column. I want to test it with the right."

**[Advance to Slide 5]**

---

## Slide 5 -- Features
**[~3 minutes. This is the intellectual core -- spend time here.]**

"Five families of features from the risk system, each backed by a specific paper."

**[Point to the top two rows]**

"The two priorities are VaR utilization and factor concentration."

"VaR utilization -- usage as a percentage of the limit -- is the most direct measurement of balance-sheet constraints. When utilization approaches the limit, forced selling follows. Coval and Stafford showed that forced selling creates predictable reversals. Utilization measures how close we are to that trigger."

"Factor concentration -- a Herfindahl index across the factor-VaR decomposition. When risk is concentrated in a few factors rather than diversified, that's crowding. He-Kelly-Manela showed that hidden concentration predicts correlated drawdowns. Low dispersion means everyone is in the same trade."

**[Gesture to the remaining three rows]**

"The remaining three: VaR dynamics captures risk appetite shifts. Scenario P&L captures how tail risk is changing. Cross-asset flow captures capital rotating between asset classes."

**[Pause, then deliver the key line]**

"These aren't proxies. VaR utilization literally is the constraint the theory says drives prices. Each feature is tested independently first, so I can isolate what's actually working."

**[Advance to Slide 6]**

---

## Slide 6 -- Outputs
**[~2-3 minutes]**

**[Start with the dual-value banner]**

"These outputs have two uses. You can trade them directly -- VIX futures, variance swaps, options. But the more practical use is probably as a risk management overlay. If the model says concentration is spiking in rates and utilization is climbing, you might reduce an existing position or add a hedge ahead of the stress event."

**[Pause]**

"A signal that tells you to cut your most-concentrated exposure two days before a forced-selling cascade isn't just alpha. It's better risk management for positions the desk already holds."

**[Walk through the four targets]**

"Four targets. VIX innovations -- unexpected changes in VIX. Adrian and Shin showed dealer positions forecast this directly. If anything in the risk system predicts anything, this should be it."

"Drawdowns in the most-concentrated asset class. If concentration is high in rates and utilization is spiking, does rates draw down next? That's the forced-selling channel."

"Cross-asset momentum reversals. When constraints bind, crowded momentum strategies reverse simultaneously. A utilization spike should predict when."

"And realized volatility -- the simplest target. If the risk outputs predict anything at all, vol should be it."

**[Advance to Slide 7]**

---

## Slide 7 -- Pipeline
**[~1-2 minutes. Walk through left to right, don't dwell.]**

"Here's how it fits together."

**[Trace left to right]**

"Risk system outputs come in nightly. I build five families of features. Those go into two models on identical features -- a simple linear baseline and LightGBM -- so the comparison is clean. Both produce predictions for each target. Everything then goes through evaluation: Sharpe ratios, transaction costs, and SHAP so every prediction is explainable."

**[Point to the four boxes below]**

"Four disciplines run through the whole pipeline. Features are stamped with when the data was known, not when it applied -- so the model can't see the future. The holdout is reserved on day one and untouched until the final test. Validation accounts for time-series dependence. And transaction costs are in every backtest from day one."

**[Advance to Slide 8]**

---

## Slide 8 -- Two Paths
**[~2 minutes]**

"There are two paths for this project."

**[Gesture to left column]**

"Path A: I calculate my own risk metrics from position data and market returns. This is doable. I'm prepared to do it."

**[Gesture to right column]**

"Path B: read access to what the risk system already produces every night. Reading only, not writing, not touching production. Zero engineering cost."

**[Deliver the contrast]**

"The reality is that Path A means three to four weeks building a crude approximation of what the risk system already does better. My VaR won't match the desk's VaR. I can't compute real utilization without the limits. And I'd be testing with a self-built proxy -- which is what external researchers already do. The reason to do this project here is to use the real thing."

**[Advance to Slide 9]**

---

## Slide 9 -- The Ask
**[~2-3 minutes. Matter-of-fact, not pleading.]**

"Here's what I'm asking for. Daily VaR with a component breakdown by asset class, and at least one of scenario P&L, factor-VaR decomposition, or utilization. As much history as available. Just read access -- no writes, no production changes, no real-time feeds."

**[Pause, then address sensitivity]**

"I understand this data is sensitive. I don't need positions, trades, or P&L -- VaR is already an aggregated number that doesn't reveal individual strategies. I'm flexible on granularity. And raw numbers never appear in any deliverable -- every output is a statistical property, not a dollar amount."

**[Deliver the priority line]**

"If I could get one thing, utilization -- usage versus the limit -- would be the single highest-value input. Without it, I can still test the other features. But utilization is the one you can't approximate from the outside."

**[Say this naturally, not scripted]**

"And if access isn't workable, I completely understand. I'll build my own metrics and test the same hypothesis. If the self-calculated version shows something, that's a reason to revisit with evidence instead of theory."

**[Advance to Slide 10]**

---

## Slide 10 -- Rigor
**[~1-2 minutes. Keep this crisp -- don't explain details unless asked.]**

"The fastest way to waste 20 weeks is to come back with an overfit backtest. Five things that kill projects like this, and how I handle each."

"Data snooping: I log every experiment. The Deflated Sharpe Ratio adjusts for how many things I tried. About 45 trials exhaust a Sharpe of 1.0 on five years of data. Every trial is counted."

"Overfitting: a simple linear model runs first on every feature set. If the ML doesn't beat it, the ML added nothing."

"Lookahead: every feature is stamped with when the data was known, not when it applied. Holdout reserved on day one, untouched until the final test."

"Costs: baked into every backtest. Sharpe reported gross and net. Breakeven cost level calculated explicitly."

"Stability: if a feature flips sign across validation folds, it gets flagged."

"This validation stack is about 25% of the project. I build it before testing any signals."

**[Advance to Slide 11]**

---

## Slide 11 -- Timeline and What I Need
**[~2 minutes. Then stop and let the conversation begin.]**

"Twenty weeks, five phases. Weeks one and two -- this meeting, the data audit. Weeks three through five, I build the validation infrastructure and smoke-test it. Weeks six through twelve, core research -- each feature family tested independently, linear baseline alongside the ML. Week thirteen is a hard checkpoint -- not a status update, a data-driven evaluation. We meet and look at the numbers. If the signals are working, I deepen with regime analysis, cross-asset panel tests, and capacity analysis through week twenty."

"What I need. First -- I'd love to hear your ideas. The infrastructure I'm building is flexible. If there are directions you've been thinking about, I'm happy to fold them in."

"Beyond that: data access or guidance on what's available. A thirty-minute check-in every two to three weeks. And the Week 13 checkpoint on the calendar now."

"What you get back: at Week 13, a memo documenting what worked and what didn't. At Week 20, a research report with a chart behind every claim, the linear baseline on every result, transaction costs included, and negatives documented honestly."

**[Gesture to the three items at the bottom]**

"Three things this won't be. A black box -- every prediction is explainable. A fishing expedition -- every feature has a hypothesis before any model runs. An overfit backtest -- statistical corrections applied to every reported number."

**[Stop here. Don't say "any questions?" -- just pause and let the conversation happen naturally.]**

---

## General Delivery Notes

- **Pace:** Slightly slower than natural. You have plenty of time.
- **Eye contact:** Look at the camera for key points, not at the slides.
- **If interrupted early:** Good -- it means they're engaged. Let the conversation flow. Come back to later slides if needed.
- **If asked something you don't know:** "I don't know, but I'll find out and get back to you by [specific time]." Never bluff.
- **If they push back on data access:** Don't argue. Say "I understand" and describe Path A.
- **Tone:** Confident, not cocky. "I want to test whether..." is stronger than "I believe this will..."
- **The battle card:** Have `qa_battle_card.md` open in a separate window. You won't read from it, but it's there if a question catches you off guard.
