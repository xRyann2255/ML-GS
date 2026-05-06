# Risk as Alpha -- Pitch Presentation v2 Design Spec

## Context

- **Audience:** Head of trading for the floor. Deep understanding of risk systems, SecDB internals, and markets.
- **Format:** HTML slide deck (same technical format as v1), projected on screen.
- **Duration:** 1 hour total. ~15-17 minutes of presenting, 40+ minutes of Q&A.
- **Goal:** Pitch the index product. Convey that this project produces a tradeable, publishable index backed by real theory, and that GS is uniquely positioned to run an enhanced version internally.
- **Secondary:** Data access is mentioned naturally as part of the GS edge story, not as a standalone request.
- **Design:** 5 slides, information-dense. The head of trading can scan multiple pieces of information at once without asking to go back. Same dark visual style as v1.

## Key Framing Shift from v1

v1 framed the presentation as a research proposal: "here's my project, please give me data access." v2 frames it as a product pitch: "here's a tradeable index that makes money, and here's why GS is the only place that can build the best version of it."

The index concept:
- A daily time series tracking the cumulative performance of a systematic strategy built from risk-system signals
- Public-data version: the product clients can audit, buy exposure to through notes or swaps
- Internal enhanced version: same methodology, proprietary SecDB inputs, higher frequency and granularity -- the performance gap is GS's competitive advantage
- The public version proves the economic thesis is real (not a data artifact). The internal version is why GS should run it.

## Deliverables

Three files, all updated:
1. `deliverables/pitch_presentation_v2.html` -- 5-slide deck + backup slides
2. `deliverables/speaker_script_v2.md` -- new script for the 5-slide structure
3. `deliverables/qa_battle_card.md` -- existing content preserved, new index-product questions added

---

## Presentation Structure

5 slides. Approach: "Product-first" -- open with what the index is, back it up with theory and data edge, close with plan and rigor.

---

### Slide 1 -- Title

**Content:**
- Project title: "Risk as Alpha"
- Subtitle: "A tradeable index from risk-system outputs"
- Name: Ryan Vincent
- Desk: XA Strats
- Date

No clutter. The subtitle immediately signals this is a product pitch, not a research proposal.

---

### Slide 2 -- The Product

**Headline:** "A systematic index that trades on dealer balance-sheet constraints"

**Two-column layout:**

**Left column -- "What it does":**
- Rules-based strategy, rebalanced daily, fully mechanical
- Turns risk-system outputs (VaR, factor concentration, scenario P&L) into cross-asset trading signals
- Predicts: VIX innovations, asset-class drawdowns, momentum reversals, realized volatility
- Trades through liquid instruments: VIX futures, variance swaps, asset-class futures, options

**Right column -- "Dual value":**
- **As a product:** Publishable index clients can buy exposure to through notes or swaps. Public-data version they can audit. GS runs the enhanced internal version.
- **As risk management:** Time hedges and size exposures on positions the desk already holds. See the stress event coming 2-3 days earlier.

**Bottom strip -- pipeline in one line:**
Risk System -> Feature Engineering (5 families) -> Ridge + LightGBM -> Predictions -> Index (daily level)

**Key line:**
"Even a modest edge -- IC of 0.03-0.05 -- is tradeable through liquid instruments with real capacity."

**Delivery notes:** This is the "what are you selling me?" slide. Within 30 seconds, the head of trading should know: it's an index, it's systematic, it predicts specific things, it's tradeable, and it has both alpha and risk management value.

---

### Slide 3 -- Why It Works

**Headline:** "Intermediary asset pricing theory predicts these signals should exist. They've never been tested with the right data."

**Top section -- three stat cards in a row:**

| 77% | 6 | Daily |
|---|---|---|
| of cross-sectional returns explained by a single intermediary-leverage factor | asset classes priced by a single kernel: equities, options, CDS, bonds, FX, commodities | frequency of SecDB risk outputs vs. quarterly Fed Z.1 data used in every published test |
| Adrian, Etula & Muir (2014) -- J. Finance | He, Kelly & Manela (2017) -- JFE | The data edge |

**Bottom section -- feature table:**

| Feature Family | What It Measures | Why It Should Predict |
|---|---|---|
| VaR Utilization | Balance-sheet constraint level | Forced selling when utilization hits the limit (Coval-Stafford 2007) |
| Factor Concentration | Crowding in risk exposures | Concentrated risk predicts correlated drawdowns (He-Kelly-Manela 2017) |
| VaR Dynamics | Risk appetite direction | Change in dealer risk forecasts VIX innovations (Adrian-Shin 2010) |
| Scenario P&L | Tail exposure asymmetry | Worst-case scenario shift signals regime change |
| Cross-Asset Flow | Capital rotation | Component VaR migration = balance-sheet reallocation |

**Key line:**
"These aren't proxies. VaR utilization literally is the constraint the theory says drives prices. Every feature has a theoretical prediction before any model is trained."

**Delivery notes:** This compresses what was three slides in v1 (thesis, theory, features) into one. The stat cards land the "settled science" punch. The table gives the "here's specifically what I'm measuring" detail. Spend time here -- this is the intellectual core.

---

### Slide 4 -- Why Only GS

**Headline:** "The public version proves the thesis is real. The internal version is why GS should run it."

**Two-column layout:**

**Left column -- data edge comparison:**

**What external researchers use:**
- Quarterly frequency (Fed Z.1)
- 3-month publication lag
- Aggregated across entire banking sector
- No dealer sign, no VaR limits, no factor decomposition

**What SecDB provides:**
- Daily frequency (nightly risk run)
- Available next morning, no lag
- Desk-level granularity, correct dealer sign
- VaR utilization, factor-VaR decomposition, scenario P&L

**Right column -- two-tier product structure:**

**Public index (the product):**
- Built on public data: HKM capital ratio, dealer CDS, CFTC positioning, CBOE skew
- Clients can audit and verify the methodology independently
- Replicable, publishable, sellable

**Internal enhanced index (GS's edge):**
- Same methodology, daily proprietary inputs from SecDB
- Higher frequency, correct dealer sign, desk-level granularity
- The performance gap between the two versions is GS's competitive advantage

**Key line:**
"The theory was proved with quarterly proxies. The internal version uses the real measurement -- daily, correctly-signed, desk-level. That gap is the product's moat."

**Delivery notes:** Data access comes in naturally here -- not as a request, but as a statement of what makes the internal version better. The speaker can mention VaR access verbally ("and with access to VaR data, the internal version gets even stronger") but the on-slide key line stays in product-pitch mode, not request mode. Don't dwell on it. The two-tier structure is the core message: public version is the sellable product, internal version is why GS wins.

---

### Slide 5 -- Plan & Rigor

**Headline:** "20-week plan. Hard checkpoint at Week 13. Validation built before any signals are tested."

**Two-column layout:**

**Left column -- timeline:**

| Weeks | Phase | What You Get |
|---|---|---|
| 1-2 | Pitch & Data Audit | This meeting. Aligned on direction. |
| 3-5 | Validation Infrastructure | Backtesting engine, validation stack, smoke-tested on synthetic data |
| 6-12 | Signal Testing | Each feature family tested independently, ridge vs. LightGBM, SHAP analysis |
| **13** | **Checkpoint** | **Memo with results. Data-driven go/pivot decision.** |
| 14-17 | Deepen or Pivot | Regime analysis, cross-asset panel, capacity & cost analysis |
| 18-20 | Consolidation | Walk-forward OOS test, research report, index specification |

**Right column -- rigor table:**

| What Kills Projects | How This Handles It |
|---|---|
| Data snooping | Every experiment logged. Deflated Sharpe adjusts for total trials. |
| Overfitting | Ridge baseline on every test. ML must beat linear. |
| Lookahead bias | Point-in-time stamping. Holdout reserved day one. |
| "Can you trade it?" | Transaction costs in every backtest. Breakeven cost calculated. |
| Unstable features | Feature importance checked across all CV folds. |

**Bottom strip:**

**What you get:** Week 13 memo documenting what worked and what didn't. Week 20 research report + index specification with every claim backed by a chart, ridge baseline on all results, transaction-cost analysis.

**What this won't be:** Not a black box (SHAP). Not a fishing expedition (every feature has a hypothesis). Not an overfit backtest (Deflated Sharpe on every number).

**Delivery notes:** End here. No "thank you" slide. Stop on the deliverables and let the conversation begin naturally.

---

## Presentation Flow Summary

| Slide | Time | Purpose |
|---|---|---|
| 1. Title | 15 sec | Frame as index product |
| 2. The Product | 4-5 min | What it is, what it predicts, dual value, pipeline |
| 3. Why It Works | 4-5 min | Theory (stat cards) + feature families (table) |
| 4. Why Only GS | 3-4 min | Public vs. SecDB data edge, two-tier index structure |
| 5. Plan & Rigor | 3-4 min | Timeline, validation, deliverables |
| **Total** | **~15-17 min** | **Leaves 43+ min for Q&A** |

---

## Backup Slides

Carry forward from v1 unchanged. Content remains technically accurate and relevant for deep-dive Q&A. No framing updates needed -- backup slides are reference material the presenter navigates to only when asked, and the head of trading will be asking technical questions where the v1 content is appropriate.

- **Backup 1:** Feature engineering detail (raw inputs, transformations)
- **Backup 2:** Validation stack detail (purged CV, CPCV, DSR, Haircut Sharpe pipeline)
- **Backup 3:** Key references table

---

## Speaker Script

New script for the 5-slide structure. Same style as v1: not a teleprompter script, but a reference so you never lose your thread. Pause points and delivery cues marked. ~15-17 minutes total.

Key tonal shifts from v1:
- Open by framing as a product, not a research proposal
- Data access is mentioned in passing on slide 4, not requested directly
- Close on deliverables, not on "what I need from you"
- Throughout: "this index" and "this product" language, not "this project" or "this research"

Key transition between slide 3 and slide 4: Slide 3 ends on "the theory is proven, the features are specific, every one has a hypothesis." Slide 4 pivots to "so why does this need to happen at GS?" The bridge is: "These signals should exist in any dealer's risk system. But testing them requires the right data -- and there's a massive gap between what's publicly available and what SecDB produces." This transitions from the intellectual argument to the competitive moat.

---

## Q&A Battle Card Updates

All existing v1 questions preserved. New sections added:

### New: Index product questions
- "Why would a client pay for this when they can replicate the public version?" -- They're paying for convenience and for GS's execution. Same reason clients buy index-linked notes on strategies they could theoretically replicate. Plus, the public version is the floor -- GS runs the enhanced version internally, so the product GS offers through notes/swaps can reflect the better-performing internal signals.
- "What's the capacity of this index?" -- Depends on which targets drive the signal. Index-level predictions (VIX, broad drawdowns) trade through liquid futures with large capacity. I build an explicit capacity analysis: Sharpe vs. cost curve at varying cost levels, breakeven cost, capital absorption estimate.
- "How is this different from existing GS research indices?" -- Most GS indices are factor-based (momentum, carry, value) or volatility-based. This one is built on dealer balance-sheet constraints -- a different economic mechanism entirely. It's complementary, not competing.
- "Who maintains the index after the internship?" -- The deliverable is a fully specified, rules-based methodology plus all the code. A strat can take the validated model and run it. The index specification document defines every step mechanically -- no discretion required.
- "What if the public version performs as well as the internal version? Where's the edge?" -- That's still a good outcome. It means the signal is robust and the index is a strong product on its own. The internal version is a bonus, not a requirement. And if public performs as well, it likely means the signal is driven by the economic mechanism, not data granularity -- which makes the thesis stronger.
- "What instruments does the index trade? Are they all liquid enough?" -- VIX futures, SPX variance swaps, asset-class futures (rates, equity index, FX majors), delta-hedged options. All liquid, all instruments the desk already trades. No exotics, no illiquid OTC.

### New: Two-tier structure questions
- "Isn't publishing the methodology giving away the signal?" -- The methodology is public, the data edge is not. Clients can replicate the public version -- that's the point, it builds trust. But they can't replicate the SecDB-enhanced version. Same way a factor index publishes its rules but the manager's execution and data advantage still matter.
- "What stops a client from just building this themselves?" -- Nothing, for the public version. That's by design -- auditability is a feature, not a bug. What they can't build is the internal version. And most clients don't want to build infrastructure; they want exposure through a note or swap.
- "How do you price the index product?" -- Standard for GS research indices: embedded in the note/swap pricing, not a separate fee. The index specification is the product; the pricing is a structuring question for the sales desk.

### New: Replicability questions
- "Which public proxies map to which SecDB features?" -- HKM capital ratio and dealer CDS for constraint level, self-constructed factor model HHI for concentration, NY Fed primary dealer positions for dynamics, self-constructed scenario analysis for stress vulnerability, CFTC CoT for cross-asset flow. Full mapping in the public data alternative document.
- "How much signal degradation do you expect from public vs. proprietary data?" -- Hard to quantify before running both, which is partly the point of the project. Theory suggests the gap should be meaningful: daily vs. quarterly, desk-level vs. sector-aggregate, correct dealer sign vs. unsigned. Quantifying that gap is one of the key deliverables.
- "What if the signal only works on proprietary data and not on public proxies?" -- Then the index product as a public offering is weaker, but the internal risk management application is still valuable. It would also raise questions about whether the signal is real or a data artifact -- which the confound checks are designed to catch.

---

## Design Notes

- Same dark visual style as v1 (dark background, blue accent, Inter font)
- Information density increased: more content per slide, less whitespace
- Tables, stat cards, and comparison panels used to pack information visually
- Head of trading can scan multiple data points simultaneously without asking to go back
- No animations or progressive reveals -- everything visible at once on each slide
