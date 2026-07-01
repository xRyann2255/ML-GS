# Vol Learning Framework -- Design Spec

**Date:** 2026-05-20
**Purpose:** Skill-based learning framework for mastering the vol-learning-guide, tied to the feature layer progression. Designed for implementation on the GS machine with an agentic workflow.

---

## Overview

A dependency-graph-driven learning system that quizzes, teaches, and tracks mastery of every concept in the vol-learning-guide. Knowledge is tied to feature layers: you master the concepts behind Layer 0 features before Layer 1, and so on.

**Core principles:**
- Feynman method: explain complex things simply, understand all the "whys"
- Three-tier mastery: recognized -> understood -> mastered
- Dependency-gated: never quizzed on a concept before its prerequisites are solid
- Feature-layer-aligned: knowledge tracks the feature set you're implementing
- Gap-driven: weekly goals chase your weakest areas, not a fixed calendar
- Interruption-safe: state persists after every interaction (sessions happen during model training downtime)

---

## 1. Dependency Graph Schema

Each concept is a node. The graph is stored in `learning/graph.yaml`.

```yaml
node:
  id: string                # unique, e.g. "bpv_jump_robustness"
  name: string              # Feynman-friendly, e.g. "Why bipower variation ignores jumps"
  layer: int                # 0-7, for progress tracking by feature layer
  chapter: int              # guide chapter, for PDF cross-reference

  # Graph edges
  requires: [node_id]       # hard gate: must be >= "understood" before this node is quizzable
  connects_to:              # lateral links for natural conversation transitions
    - node_id: string
      how: string           # e.g. "same phenomenon, different measurement"
                            # e.g. "easily confused -- SHAR adds asymmetry, HARQ adds noise"

  # Content -- what the agent needs to quiz, evaluate, and teach
  key_points: [string]      # must-hit points in a correct Feynman explanation
  misconceptions: [string]  # common wrong explanations to catch
  why_it_matters: string    # practical consequence -- motivates the quiz
```

Mastery state is stored separately in `learning/mastery-state.json`:

```json
{
  "bpv_jump_robustness": {
    "tier": "understood",
    "next_review": "2026-05-22",
    "consecutive_passes": 2,
    "last_tested": "2026-05-20"
  }
}
```

**Edge semantics:**
- `requires`: hard gate. The agent will not quiz concept B until all of B's `requires` are at least "understood." This prevents the frustrating experience of being asked about HARQ when you can't yet explain why RV is noisy.
- `connects_to`: soft link. Used for natural conversation transitions, contrastive quizzing ("easily confused" pairs), and thread-based teaching. No gating.

**Why graph and state are separate files:** You can expand the graph (add Layer 2) without resetting progress on Layer 0-1 concepts.

---

## 2. Mastery Tiers

| Tier | What it means | How you get there |
|---|---|---|
| **Untested** | Never quizzed | Default state |
| **Recognized** | Can identify the concept and roughly what it does | Answer a basic identification prompt, or engage meaningfully during `/teach` |
| **Understood** | Can Feynman-explain it simply and survive chain-of-why drilling | Explain it hitting all `key_points`, no `misconceptions`, survive 2-3 "but why?" follow-ups |
| **Mastered** | Can explain, connect to project unprompted, and spot misapplications | Pass contrastive quiz, spot-the-mistake scenario, or scenario-based application without hints |

**Tier promotion rules:**
- Untested -> Recognized: engage with the concept in any quiz or learn session
- Recognized -> Understood: pass a Feynman explanation + chain-of-why drill
- Understood -> Mastered: pass on two separate occasions (different sessions, different question phrasing) using mastery-tier techniques (contrastive, scenario, error-spotting)

---

## 3. Spaced Repetition

Intervals are calibrated for multi-hour daily study sessions:

| Consecutive passes | Next review |
|---|---|
| 1st pass | Later same day (2-3 hours) |
| 2nd pass | Next day |
| 3rd pass | 3 days |
| 4th pass | 7 days |
| 5th pass | 14 days (considered stable) |

**On any fail:** reset `consecutive_passes` to 0, schedule review for later same day.

**Review priority in quiz sessions:**
1. Overdue reviews (past `next_review` date)
2. Same-day retests (concepts taught earlier this session)
3. Frontier nodes (prerequisites met, not yet mastered)

---

## 4. Skill Definitions

### 4.1 `/quiz`

**Purpose:** Interactive assessment session. The core learning loop.

**Concept selection priority:**
1. Overdue spaced repetition reviews
2. Mid-session retests (concepts taught earlier this session)
3. Frontier nodes, prioritized by downstream impact (nodes that unlock the most other nodes)

**Tier-appropriate techniques:**

| Target tier | Technique | Pass criteria |
|---|---|---|
| Recognized -> Understood | Feynman prompt: "Explain X to a new intern" | Hits all `key_points`, avoids `misconceptions` |
| Understood (chain-of-why) | Follow-up "Why?" drilling on their answer | Reaches bedrock without stalling or contradicting |
| Understood -> Mastered | Contrastive: "What's the difference between X and Y?" (using `connects_to` with "easily confused") | Correctly discriminates both concepts |
| Understood -> Mastered | Spot-the-mistake: "A colleague says [misconception]. What's wrong?" | Identifies the specific error and explains the correct reasoning |
| Understood -> Mastered | Scenario: present a realistic project situation | Connects concept to project decision unprompted |

**Gap handling flow:**
1. Gap found -> agent teaches intuitively (plain English, using `key_points` + `why_it_matters`, no formulas unless user asks)
2. Agent continues to the next 2-3 concepts
3. Agent circles back with a rephrased version of the original question
4. If pass on retest: schedule for spaced repetition (1st pass -> review in 2-3 hours)
5. If fail on retest: flag concept for a `/teach` deep-dive, move on

**Confidence calibration:** Before mastery-tier questions, ask "On a scale of 1-5, how confident are you on this?" Track calibration over time to reveal blind spots.

**Layer completion:** When all nodes in a layer reach "mastered", announce it and suggest `/expand-learning-graph` to add the next layer.

**State persistence:** After every concept interaction, dispatch a subagent (Opus 4.6) to update `mastery-state.json`. The main conversation context stays clean.

**Interruption handling:** Session can be stopped at any point. All progress is already persisted. Next `/quiz` picks up from the current state.

### 4.2 `/teach`

**Purpose:** Teaching mode. For studying alongside the PDF, or when you want guided explanation.

**Invocation modes:**
- `/teach bpv` -- teach a specific concept
- `/teach jumps` -- teach a concept thread (follows `connects_to` and `requires` edges through the jump decomposition branch)
- `/teach` (no argument) -- auto-select the next most natural concept to learn

**Auto-selection logic (no argument):**
1. If there are "recognized" concepts with all prerequisites "understood": pick the one with the most downstream dependents (highest unlock impact)
2. If all frontier nodes are "untested": start from the deepest foundation (root nodes first -- returns, variance, etc.)
3. If there are stale "understood" concepts overdue for review: suggest those first with a brief refresher before teaching new material

**Teaching approach:**
- Build from prerequisites upward. If explaining HARQ, first verify: "Quick check -- can you tell me in one sentence why RV is a noisy estimate?" If the user can't, drop down to that prerequisite first.
- Explain intuitively: plain English first, then the formula as confirmation, then project connection
- Use analogies. Let the user generate their own when possible.
- After each concept: lightweight check -- "Before we move on, explain back to me why [specific key point]"
- Update concept to at least "recognized" based on engagement

**Adaptive depth:**
- If the user says "I don't understand X" or struggles with a check, immediately drop to the relevant prerequisite. Follow `requires` edges downward until you find solid ground, then build back up.
- If the user is breezing through, skip lightweight checks and move faster through the thread.

**Quiz handoff:**
- Maintain a session list of concepts covered
- At natural stopping points (end of a thread, or user signals done), suggest:
  > "We covered [N] concepts: [list]. Want to lock them in? Run `/quiz` and I'll focus on what we just studied."
- Write covered-concepts list to `learning/session-context.json` so `/quiz` reads it and prioritizes those concepts first

### 4.3 `/learning-status`

**Purpose:** Dashboard view of mastery progress.

**Output sections:**
1. **Per-layer summary:**
   ```
   Layer 0 (HAR Core):     ████████████░░░  12/15 mastered (80%)
   Layer 1 (Noise+Asym):   ████░░░░░░░░░░░   4/13 understood (31%)
   Layer 2 (Options):      not yet added
   ```
2. **Due today:** concepts scheduled for spaced repetition review
3. **Due this week:** upcoming review queue
4. **Frontier nodes:** concepts ready to learn (all prerequisites >= understood), sorted by downstream impact
5. **Stale alerts:** "understood" concepts not reviewed in 14+ days
6. **Recommendation:** e.g., "You have 3 reviews due and 4 frontier nodes ready. Start with `/quiz` for reviews, then `/teach` on [highest-impact frontier concept]."

**Implementation:** Dispatch a subagent (Opus 4.6) to read `graph.yaml` and `mastery-state.json`, compute the dashboard, return the summary. Keeps main context clean.

### 4.4 `/weekly-learning-goals`

**Purpose:** Generate and track gap-driven weekly learning goals.

**Goal generation logic:**
- Analyze mastery state: what tiers are concepts at, what's due for review, what frontier nodes are ready
- Propose 5-8 concepts to target this week, prioritized by:
  1. Concepts blocking the most downstream nodes (highest unlock impact)
  2. Concepts stuck at "recognized" for 7+ days without advancing
  3. Spaced repetition backlog (if review queue is growing, prioritize reviews)
- Mix: ~40% review/advancement, ~60% new frontier concepts
- Layer completion awareness: "You're 3 concepts away from completing Layer 1. Prioritizing those this week."

**Weekly review:**
- When run again at week end: show achieved vs. planned, roll over unfinished goals
- Track week-over-week progress: "Last week: 6/8 goals met. This week: [new goals]."

**Implementation:** Dispatch a subagent (Opus 4.6) to analyze the graph and mastery state, generate goals, write to `learning/weekly-goals.md`.

### 4.5 `/expand-learning-graph`

**Purpose:** Add new concepts, merge checklists, or add entire layers to the graph.

**Three modes:**
- **Merge checklist:** `/expand-learning-graph merge layer01-learning-checklist.md`
  - Read the checklist file
  - For each item: fuzzy-match against existing nodes (see dedup below)
  - If match found: merge new points into existing node's `key_points` or `misconceptions`
  - If no match: create a new node, propose `requires` edges based on content
  - Present all proposed changes for user approval before committing
- **Add individual concept:** `/expand-learning-graph add "concept description"`
  - Create node following schema, ask user to confirm edges
- **Add layer:** `/expand-learning-graph layer 2`
  - Read relevant chapters from vol-learning-guide (markdown or PDF)
  - Propose nodes (do NOT auto-create)
  - User approves/edits, then nodes are added

**Deduplication and validation (robust):**

The graph must not contain redundant or near-duplicate nodes. On every expansion, run:

1. **Exact ID check:** reject if `id` already exists
2. **Semantic similarity check:** for each proposed node, compare its `name` + `key_points` against ALL existing nodes. Flag if:
   - Two nodes share 60%+ of the same `key_points`
   - Two node names describe the same concept with different wording (e.g., "why we use log returns" vs "log returns vs simple returns")
   - A proposed node's content is a strict subset of an existing node (the existing node already covers it)
3. **Merge-or-split decision:** when a near-duplicate is found, present three options:
   - **Merge:** fold the new content into the existing node's `key_points`/`misconceptions`
   - **Split:** if the existing node is too broad, split it into two focused nodes and redistribute edges
   - **Keep both:** if they're genuinely distinct despite surface similarity (user confirms)
4. **Structural validation:**
   - No orphan nodes (every non-root node has at least one `requires`)
   - No circular dependencies
   - All `requires` and `connects_to` targets exist in the graph
   - No node has more than 5 `requires` edges (if it does, it probably needs intermediate nodes)
5. **Coverage check:** after adding a layer, verify that every section heading in the relevant guide chapter maps to at least one node. Flag uncovered sections.

**Implementation:** Dispatch a subagent (Opus 4.6) to read the graph, perform the expansion and validation, return proposed changes for approval. Only write to `graph.yaml` after user confirms.

---

## 5. Subagent Architecture

To prevent context bloat in the main conversation, all data-heavy operations are dispatched to subagents. Always use Opus 4.6.

| Operation | Subagent task |
|---|---|
| Read mastery state | Fetch `mastery-state.json`, compute what's due, return summary |
| Update mastery state | Write tier/date changes to `mastery-state.json` after each quiz interaction |
| Read graph for quiz | Fetch `graph.yaml`, identify frontier nodes and review queue, return next concepts to quiz |
| Dashboard computation | Read both files, compute per-layer stats, return formatted dashboard |
| Weekly goal generation | Analyze graph + state, generate prioritized goals, write to `weekly-goals.md` |
| Graph expansion | Read graph + input file, perform dedup/validation, return proposed changes |
| Learn auto-selection | Read graph + state, compute highest-impact next concept, return recommendation |

**Subagent prompt pattern:**
```
You are a learning framework data agent. Read [file(s)], perform [operation],
return [specific output format]. Do not engage in conversation. Return only
the requested data.
```

---

## 6. Data Files

```
learning/
  graph.yaml                  # dependency graph (all nodes + edges)
  mastery-state.json          # tier, next_review, consecutive_passes per node
  session-context.json        # concepts covered in current /teach session (for /quiz handoff)
  session-log.md              # append-only log (date, concepts covered, gaps found, taught)
  weekly-goals.md             # current + historical weekly goals
```

---

## 7. Layer 0-1 Starter Graph

The GS agent should bootstrap the graph with 28 nodes (15 Layer 0, 13 Layer 1) defined below. Then merge `layer01-learning-checklist.md` to expand.

### Layer 0: HAR Core (15 nodes)

**Tier 1 -- Foundations (roots, no prerequisites):**

```yaml
- id: log_returns
  name: "Why we use log returns instead of simple returns"
  layer: 0
  chapter: 1
  requires: []
  connects_to:
    - { node_id: rv_construction, how: "log returns are what get squared in RV" }
    - { node_id: annualizing_vol, how: "time-additivity enables the sqrt-T rule" }
  key_points:
    - "Time additivity: multi-period log return = sum of single-period log returns"
    - "ln(AB) = ln(A) + ln(B) makes the math work; simple returns compound multiplicatively"
    - "Approximate symmetry: +5% then -5% nets to zero exactly (simple returns don't)"
    - "For small returns (<5%), log and simple returns are nearly identical"
  misconceptions:
    - "Log returns are more accurate (they're used because the math is cleaner, not more accurate)"
    - "Simple and log returns are interchangeable (they diverge for large moves)"
  why_it_matters: "Every RV computation squares log returns. If you don't understand why log, you can't explain why RV works."

- id: variance_as_spread
  name: "Why variance measures spread via squared deviations"
  layer: 0
  chapter: 1
  requires: []
  connects_to:
    - { node_id: rv_construction, how: "RV is variance applied to intraday data" }
    - { node_id: fat_tails, how: "kurtosis extends squaring logic to 4th power" }
  key_points:
    - "Average squared distance from mean"
    - "Squaring makes negatives positive AND amplifies outliers (by design)"
    - "Bessel's correction (T-1) compensates for estimating mean from same data"
    - "Variance is in squared units; std dev = sqrt(variance) restores original units"
  misconceptions:
    - "We square just to make numbers positive (absolute deviations do that too; squaring has specific mathematical properties tied to QV convergence)"
    - "Variance and standard deviation are the same thing (different units, different scale)"
  why_it_matters: "Variance is literally the quantity you're forecasting in this entire project."

- id: annualizing_vol
  name: "Why we multiply daily vol by sqrt(252)"
  layer: 0
  chapter: 1
  requires: []
  connects_to:
    - { node_id: log_returns, how: "time-additivity enables the rule" }
    - { node_id: vol_clustering, how: "clustering violates the independence assumption behind it" }
  key_points:
    - "Variances add for independent returns (not standard deviations)"
    - "sqrt(252) comes from 252 trading days per year"
    - "Only valid under the independence assumption"
    - "'VIX at 20' means 20% annualized volatility"
  misconceptions:
    - "The square root rule always works (vol clustering violates independence)"
    - "You annualize by multiplying by 252 (that's variance; vol uses sqrt)"
  why_it_matters: "You need this to compare daily RV with VIX and IV benchmarks."
```

**Tier 2 -- Stylized Facts:**

```yaml
- id: vol_clustering
  name: "Why large moves follow large moves"
  layer: 0
  chapter: 1
  requires: [variance_as_spread]
  connects_to:
    - { node_id: heterogeneous_market_hypothesis, how: "HAR exists because of clustering" }
    - { node_id: leverage_effect, how: "both are stylized facts but distinct mechanisms" }
    - { node_id: annualizing_vol, how: "clustering violates independence assumption" }
  key_points:
    - "Returns are uncorrelated but squared/absolute returns show strong positive autocorrelation"
    - "Decay is power-law (~lag^-0.3), not exponential -- much slower"
    - "Cont (2001) documented across all asset classes and decades"
    - "This persistence is what makes vol forecastable at all"
  misconceptions:
    - "Vol clustering means returns are predictable (returns are uncorrelated; only magnitude is predictable)"
    - "Clustering decays quickly (power-law means vol 100 days ago is still informative)"
  why_it_matters: "If vol didn't cluster, HAR wouldn't work and your entire project would be pointless."

- id: fat_tails
  name: "Why extreme returns happen far more often than normal"
  layer: 0
  chapter: 1
  requires: [variance_as_spread]
  connects_to:
    - { node_id: vol_clustering, how: "clustering partially explains fat tails" }
    - { node_id: jumps_vs_diffusion, how: "jumps are one source of fat tails" }
  key_points:
    - "Kurtosis > 3 (excess kurtosis 5-10 for equities)"
    - "4-sigma daily move: once per 63 years under normal, several times per year in reality"
    - "Q-Q plot shows S-shaped departure from normal line"
    - "Mandelbrot (1963) first documented for cotton prices"
  misconceptions:
    - "Fat tails are caused by jumps (stochastic vol also produces them even without jumps)"
    - "You can fix fat tails by using log returns (helps but doesn't eliminate them)"
  why_it_matters: "Any model assuming normality will catastrophically underestimate tail risk."

- id: leverage_effect
  name: "Why negative returns amplify vol more than positive"
  layer: 0
  chapter: 1
  requires: [variance_as_spread]
  connects_to:
    - { node_id: semivariances, how: "same phenomenon measured at intraday frequency" }
    - { node_id: shar_model, how: "SHAR operationalizes this in HAR" }
    - { node_id: vol_clustering, how: "distinct mechanism, same domain" }
  key_points:
    - "Corr(r_t, sigma^2_{t+1}) < 0"
    - "Black (1976) leverage mechanism: price drop -> higher debt/equity -> riskier"
    - "Also driven by margin calls, stop-losses, hedging cascades"
    - "Asymmetric: 'fear is louder than greed'"
    - "Strongest in equities, weaker or reversed in FX/commodities"
  misconceptions:
    - "Leverage effect means financial leverage causes volatility (named after the mechanism but feedback trading and behavioral effects also drive it)"
    - "Positive and negative returns affect vol equally (the entire point is they don't)"
  why_it_matters: "Symmetric models systematically underpredict vol after selloffs."
```

**Tier 3 -- RV Construction:**

```yaml
- id: integrated_variance
  name: "What we're actually trying to measure (IV as the true target)"
  layer: 0
  chapter: 2
  requires: [variance_as_spread]
  connects_to:
    - { node_id: rv_construction, how: "RV is the estimator of IV" }
    - { node_id: rv_is_noisy, how: "RV only approximates IV" }
  key_points:
    - "Integral of instantaneous variance over the day"
    - "Latent: never directly observed"
    - "Speedometer analogy -- IV accumulates total price wiggle"
    - "Distinct from quadratic variation (QV also captures jumps)"
  misconceptions:
    - "'IV' means implied volatility here (no -- integrated variance, confusing terminology)"
    - "You can observe IV directly (no, it's latent; RV is the estimator)"
  why_it_matters: "IV is the theoretical gold standard. Every estimator is trying to get closer to it."

- id: rv_construction
  name: "Why summing squared intraday returns measures volatility"
  layer: 0
  chapter: 2
  requires: [log_returns, variance_as_spread, integrated_variance]
  connects_to:
    - { node_id: five_min_convention, how: "sampling frequency choice for this sum" }
    - { node_id: rv_is_noisy, how: "this sum is an estimate, not truth" }
    - { node_id: log_rv_transform, how: "why we take log of this" }
  key_points:
    - "RV_t = sum of r^2_{t,i} for all intraday returns"
    - "Each squared return approximates local variance because E[epsilon^2]=1"
    - "Converges to quadratic variation as n->infinity (Andersen et al. 2001, BNS 2002)"
    - "No mean subtraction needed (intraday mean is approximately zero)"
    - "With no jumps: QV=IV. With jumps: QV=IV+sum(J^2)"
  misconceptions:
    - "We square returns because we want positive numbers (the deep reason is convergence to quadratic variation)"
    - "More intraday observations always gives better RV (microstructure noise breaks this)"
    - "RV measures direction (no, only magnitude -- squaring removes sign)"
  why_it_matters: "This is the dependent variable (y) in your entire forecasting project."

- id: five_min_convention
  name: "Why 5-minute sampling is the standard"
  layer: 0
  chapter: 2
  requires: [rv_construction]
  connects_to:
    - { node_id: microstructure_noise_concept, how: "noise is why we can't go higher frequency" }
    - { node_id: signature_plot, how: "the diagnostic tool for choosing frequency" }
  key_points:
    - "Bias-variance tradeoff: too fast = noise, too slow = imprecise"
    - "Liu Patton Sheppard (2015) tested ~400 estimators; 5-min RV 'hard to beat'"
    - "Not derived from theory -- empirical finding"
    - "78 observations per 6.5-hour US equity trading day"
  misconceptions:
    - "5 minutes is optimal for all assets (depends on liquidity and noise ratio)"
    - "We should always use the highest frequency available (noise wins at sub-minute)"
  why_it_matters: "Choosing the wrong frequency makes your RV target garbage, poisoning every downstream model."
```

**Tier 4 -- Where RV Breaks:**

```yaml
- id: rv_is_noisy
  name: "Why RV is an estimate with measurable uncertainty"
  layer: 0
  chapter: 2
  requires: [rv_construction]
  connects_to:
    - { node_id: realized_quarticity, how: "RQ quantifies exactly how noisy" }
    - { node_id: harq_model, how: "HARQ exploits this noise information" }
  key_points:
    - "Estimation error shrinks as 1/sqrt(n)"
    - "Error variance involves integrated quarticity (integral of sigma^4)"
    - "Days when vol-of-vol is high have less precise RV estimates"
    - "This means RV is a noisy label for your model to train on"
  misconceptions:
    - "RV is the true volatility (it's an estimator with sampling error)"
    - "All days' RV estimates are equally reliable (high-RQ days are much noisier)"
  why_it_matters: "If you treat all RV values as equally trustworthy, your model trains on noise."

- id: microstructure_noise_concept
  name: "Why transaction prices are contaminated and what that does to RV"
  layer: 0
  chapter: 2-3
  requires: [rv_construction, five_min_convention]
  connects_to:
    - { node_id: signature_plot, how: "diagnostic for visualizing noise" }
    - { node_id: noise_robust_estimators, how: "the family of fixes" }
  key_points:
    - "Three sources: bid-ask bounce, discrete tick sizes, price staleness"
    - "Observed price = true price + noise (additive model)"
    - "Noise has constant variance omega^2 regardless of interval length"
    - "At high frequency, noise dominates signal"
    - "RV diverges to 2*n*omega^2 as n->infinity"
  misconceptions:
    - "Noise can be removed by data cleaning (it's structural -- bid-ask bounce is inherent)"
    - "Noise only matters for tick data (matters at any sub-1-minute frequency)"
  why_it_matters: "This is why you can't just sample every tick."

- id: signature_plot
  name: "How to diagnose the bias-variance tradeoff visually"
  layer: 0
  chapter: 2-3
  requires: [microstructure_noise_concept]
  connects_to:
    - { node_id: five_min_convention, how: "the plot shows why 5-min is the sweet spot" }
    - { node_id: noise_robust_estimators, how: "robust estimators flatten the curve" }
  key_points:
    - "x-axis: sampling interval, y-axis: average RV"
    - "Three regions: noise-inflated (left), flat sweet spot (center), imprecise (right)"
    - "If curve still rising as frequency increases, you're in the noise zone"
    - "First diagnostic to run on any new dataset before computing RV"
  misconceptions:
    - "The flat region means the estimate is perfect (still noisy, just approximately unbiased)"
    - "You only check this once (noise levels change over time)"
  why_it_matters: "This is the first diagnostic you run before computing RV on any new data."

- id: log_rv_transform
  name: "Why we work with ln(RV) instead of RV"
  layer: 0
  chapter: 2, 6
  requires: [rv_construction]
  connects_to:
    - { node_id: har_model, how: "HAR is typically estimated in logs" }
    - { node_id: rv_is_noisy, how: "log stabilizes variance of the estimate" }
  key_points:
    - "Stabilizes variance (variance-of-variance is highly skewed)"
    - "Makes distribution closer to Gaussian (helps OLS)"
    - "Guarantees positive forecasts (exp(x) > 0)"
    - "Most HAR papers use log specification"
  misconceptions:
    - "You must always use log RV (sqrt(RV) also used; depends on loss function)"
    - "Log RV is just a convenience (it fundamentally changes the loss function)"
  why_it_matters: "Without this, HAR residuals are badly behaved and forecasts can go negative."
```

**Tier 5 -- The HAR Model:**

```yaml
- id: heterogeneous_market_hypothesis
  name: "Why different market participants at different speeds create multi-scale dynamics"
  layer: 0
  chapter: 6
  requires: [vol_clustering]
  connects_to:
    - { node_id: har_model, how: "HAR directly implements HMH" }
    - { node_id: har_approximates_long_memory, how: "explains why HAR captures long memory cheaply" }
  key_points:
    - "Muller et al. (1993): market is a superposition of participants at different time scales"
    - "Day traders (daily), portfolio managers (weekly), institutional allocators (monthly)"
    - "Each responds to vol at their own horizon; interactions create multi-scale autocorrelation"
    - "Explains why AR(1) is insufficient for vol forecasting"
  misconceptions:
    - "HMH means there are literally three types of trader (simplification -- represents a continuum)"
    - "HMH is a proven mechanism (it's a hypothesis that motivates HAR; HAR works regardless)"
  why_it_matters: "This is the economic intuition behind HAR's three time scales. Without it, the model looks ad hoc."

- id: har_model
  name: "How HAR forecasts vol from three time scales using OLS"
  layer: 0
  chapter: 6
  requires: [rv_construction, log_rv_transform, heterogeneous_market_hypothesis]
  connects_to:
    - { node_id: har_approximates_long_memory, how: "why 3 coefficients capture 22 lags" }
    - { node_id: har_hard_to_beat, how: "why this simple model is the benchmark" }
    - { node_id: har_j_model, how: "adding jump decomposition" }
    - { node_id: shar_model, how: "adding asymmetry" }
    - { node_id: harq_model, how: "adding noise awareness" }
  key_points:
    - "RV_{t+1} = b0 + b_d*RV_t + b_w*RV^(w)_t + b_m*RV^(m)_t + epsilon"
    - "Estimated by OLS -- no MLE, no iteration, no latent variables"
    - "Typical coefficients ~0.36/0.28/0.28; all three contribute meaningfully"
    - "In-sample R^2 of 0.40-0.60 from just three predictors"
    - "Estimated in log-RV in practice"
  misconceptions:
    - "HAR is an AR(22) (it's a restricted AR(22) where lags share coefficients via averaging)"
    - "The monthly component is less important (its coefficient is similar to daily's)"
  why_it_matters: "THE baseline. Every ML model must beat it. If yours can't beat 3 OLS coefficients, you've overfit."

- id: har_approximates_long_memory
  name: "Why 3 coefficients capture the slow decay of vol autocorrelation"
  layer: 0
  chapter: 6
  requires: [har_model, vol_clustering]
  connects_to:
    - { node_id: heterogeneous_market_hypothesis, how: "the economic motivation" }
  key_points:
    - "Weekly average implicitly includes lags 1-5, monthly includes lags 1-22"
    - "Overlapping averages create smooth decay that mimics power-law autocorrelation"
    - "Achieves similar fit to FIGARCH with much simpler estimation"
  misconceptions:
    - "HAR actually models long memory (it approximates it -- true long memory requires fractional integration)"
  why_it_matters: "Understanding this tells you why HAR works so well with so few parameters."

- id: har_hard_to_beat
  name: "Why HAR is the benchmark despite being dead simple"
  layer: 0
  chapter: 6
  requires: [har_model]
  connects_to:
    - { node_id: harq_model, how: "HARQ is one of the few reliable improvements" }
    - { node_id: rv_is_noisy, how: "low signal-to-noise is one reason" }
  key_points:
    - "Reason 1: vol is highly persistent and approximately linear"
    - "Reason 2: low signal-to-noise means complex models overfit"
    - "Reason 3: with only past RV at h=1, there's little nonlinear structure"
    - "ML gains come from richer features AND/OR longer horizons"
    - "Bollerslev et al. (2024): well-tuned HAR 'hard to beat' at h=1"
  misconceptions:
    - "HAR is easy to beat with enough features (a badly-tuned baseline is a bigger problem than missing features)"
    - "ML should always beat HAR (at h=1 with RV-only features, it often doesn't)"
  why_it_matters: "If you don't understand this, you'll waste weeks trying to beat a badly-tuned baseline."
```

### Layer 1: Noise + Asymmetry (13 nodes)

**Noise Branch:**

```yaml
- id: realized_quarticity
  name: "Why RQ measures how much to trust today's RV"
  layer: 1
  chapter: 2, 6, 10
  requires: [rv_is_noisy, rv_construction]
  connects_to:
    - { node_id: harq_model, how: "HARQ uses RQ to modulate coefficients" }
    - { node_id: harq_feature, how: "sqrt(RQ) as standalone ML feature" }
  key_points:
    - "RQ = (n/3) * sum(r^4) -- fourth power massively upweights extreme moves"
    - "Converges to integral of sigma^4 (integrated quarticity)"
    - "High RQ = vol-of-vol was high within the day = noisy RV estimate"
    - "The asymptotic variance of RV is proportional to RQ"
  misconceptions:
    - "RQ measures volatility (it measures the noise in the volatility estimate -- a meta-quantity)"
    - "High RQ means high vol (high RQ means vol was variable within the day, not necessarily high on average)"
  why_it_matters: "Without RQ, you can't distinguish a trustworthy RV reading from a garbage one."

- id: harq_model
  name: "How HARQ down-weights noisy RV days automatically"
  layer: 1
  chapter: 6
  requires: [har_model, realized_quarticity]
  connects_to:
    - { node_id: harq_feature, how: "ML generalization of HARQ's insight" }
    - { node_id: har_hard_to_beat, how: "HARQ is the strongest univariate RV forecast" }
  key_points:
    - "Effective daily coefficient = beta_d + beta_dQ * sqrt(RQ_t)"
    - "beta_dQ is negative: high noise shrinks coefficient toward zero"
    - "On noisy days, weight shifts to more stable weekly/monthly averages"
    - "Confidence-weighted HAR"
    - "Bollerslev Patton Quaedvlieg (2016): improves QLIKE by 5-15%"
  misconceptions:
    - "HARQ drops noisy days (it reduces their influence, doesn't drop them)"
    - "You need to hard-code the interaction for ML (trees learn it automatically from separate features)"
  why_it_matters: "THE paper your project builds on. Measurement quality should modulate feature weights."

- id: harq_feature
  name: "Why sqrt(RQ) is a standalone feature for ML models"
  layer: 1
  chapter: 10
  requires: [realized_quarticity, harq_model]
  connects_to:
    - { node_id: realized_quarticity, how: "derived from RQ" }
    - { node_id: triple_expansion, how: "apply level/change/z-score to sqrt(RQ)" }
  key_points:
    - "Trees split on sqrt(RQ) to learn adaptive weighting without explicit interactions"
    - "Provides data-quality signal no other feature captures"
    - "Double duty: noise proxy AND regime indicator"
    - "HARQ hard-codes the interaction; ML can discover more general patterns"
  misconceptions:
    - "You need to include RV*sqrt(RQ) as a feature (no -- include both separately; trees discover interactions)"
  why_it_matters: "The single most important extension beyond baseline HAR for your project."

- id: noise_robust_estimators
  name: "Why TSRV, kernel, and pre-averaging exist and when to use them"
  layer: 1
  chapter: 3
  requires: [microstructure_noise_concept, signature_plot]
  connects_to:
    - { node_id: five_min_convention, how: "alternatives to 5-min sampling" }
    - { node_id: rv_construction, how: "they solve the noise problem RV can't" }
  key_points:
    - "TSRV subsamples at two frequencies and subtracts the bias"
    - "Realized kernel uses autocovariance weighting"
    - "Pre-averaging smooths prices before computing returns"
    - "All converge to IV at rates between n^{-1/4} and n^{-1/5}"
    - "Liu Patton Sheppard (2015): none reliably beats 5-min RV for forecasting"
  misconceptions:
    - "Noise-robust estimators are always better (for forecasting, 5-min RV is usually competitive)"
    - "Always use the most sophisticated estimator (complexity adds its own noise in finite samples)"
  why_it_matters: "You need to know these exist even if 5-min RV is your default."
```

**Asymmetry Branch:**

```yaml
- id: semivariances
  name: "Why splitting RV into upside and downside captures the leverage effect"
  layer: 1
  chapter: 6, 10
  requires: [rv_construction, leverage_effect]
  connects_to:
    - { node_id: shar_model, how: "SHAR uses semivariances as inputs" }
    - { node_id: leverage_effect, how: "same phenomenon at intraday frequency" }
    - { node_id: signed_jumps, how: "extends sign-splitting logic to jumps" }
  key_points:
    - "RV+ = sum of r^2 for positive returns, RV- = sum for negative"
    - "RV+ + RV- = RV by construction"
    - "RV- carries ~2x the predictive weight (Patton Sheppard 2015)"
    - "Reduces QLIKE by 3-8%"
  misconceptions:
    - "RV+ and RV- are different estimators (they're the same sum decomposed by sign)"
    - "Upside volatility doesn't matter (matters less, but still carries signal)"
  why_it_matters: "Simplest way to capture asymmetry in your feature set."

- id: shar_model
  name: "How SHAR separates good vol from bad vol in HAR"
  layer: 1
  chapter: 6
  requires: [har_model, semivariances]
  connects_to:
    - { node_id: leverage_effect, how: "the economic mechanism it captures" }
    - { node_id: harq_model, how: "easily confused -- SHAR adds asymmetry, HARQ adds noise awareness" }
  key_points:
    - "Replaces daily RV with RS+ and RS- as separate regressors"
    - "beta_d^- > beta_d^+ (bad vol predicts more future vol)"
    - "Weekly and monthly terms stay as total RV"
    - "Patton and Sheppard (2015): strongest gains on equity indices"
  misconceptions:
    - "SHAR replaces all three terms (only daily is split; weekly/monthly remain total RV)"
    - "SHAR and HARQ are the same idea (orthogonal: asymmetry vs. measurement quality)"
  why_it_matters: "Demonstrates that asymmetric treatment is worth the extra parameter for equity vol."
```

**Jump Branch:**

```yaml
- id: jumps_vs_diffusion
  name: "Why prices have two types of movement"
  layer: 1
  chapter: 4
  requires: [rv_construction]
  connects_to:
    - { node_id: bpv_jump_robustness, how: "BPV separates them" }
    - { node_id: fat_tails, how: "jumps are one source of fat tails" }
  key_points:
    - "Diffusion = smooth continuous price movement"
    - "Jump = sudden discontinuity (earnings, FOMC, flash crash)"
    - "QV = IV + sum(J^2), so RV captures both"
    - "Continuous component is persistent and forecastable; jumps are largely transient"
  misconceptions:
    - "Jumps are just large returns (large return could be high-vol diffusion; jump is specifically a discontinuity)"
    - "All jumps are negative (positive jumps exist -- short squeezes, earnings beats)"
  why_it_matters: "Without separating C from J, your forecast signal is diluted by unpredictable events."

- id: bpv_jump_robustness
  name: "Why multiplying consecutive absolute returns filters out jumps"
  layer: 1
  chapter: 4
  requires: [jumps_vs_diffusion, rv_construction]
  connects_to:
    - { node_id: jump_component_feature, how: "BPV enables C/J decomposition" }
    - { node_id: pi_over_2_scaling, how: "the constant that makes BPV unbiased" }
  key_points:
    - "BPV = (pi/2) * sum(|r_i| * |r_{i-1}|)"
    - "Jump hits one interval but its neighbor is normal-sized, so the product is small"
    - "Converges to IV (not QV) even with jumps"
    - "The 'dilution' mechanism: isolated events get dampened"
    - "Barndorff-Nielsen and Shephard (2004)"
  misconceptions:
    - "BPV uses absolute returns because squared are too noisy (the reason is jump robustness)"
    - "BPV is always better than RV (BPV has higher variance than RV when there are no jumps)"
    - "Two consecutive intervals can't both have jumps (unlikely but possible; assumption works in practice)"
  why_it_matters: "BPV is the workhorse for constructing the continuous component feature."

- id: pi_over_2_scaling
  name: "Where the pi/2 constant in BPV comes from"
  layer: 1
  chapter: 4
  requires: [bpv_jump_robustness]
  connects_to:
    - { node_id: bpv_jump_robustness, how: "makes BPV unbiased for IV" }
  key_points:
    - "E[|Z|] = sqrt(2/pi) for Z~N(0,1)"
    - "So E[|Z|]^2 = 2/pi, not 1"
    - "Multiplying absolute returns introduces this bias vs. squaring"
    - "pi/2 = 1/(2/pi) is the exact correction"
  misconceptions:
    - "pi/2 is arbitrary (it's the precise mathematical correction for absolute-value bias)"
  why_it_matters: "Understanding this shows BPV is a principled estimator, not a hack."

- id: jump_component_feature
  name: "How J_t = max(RV - BPV, 0) becomes a feature"
  layer: 1
  chapter: 4, 6
  requires: [bpv_jump_robustness]
  connects_to:
    - { node_id: har_j_model, how: "HAR-J adds J_t as predictor" }
    - { node_id: har_cj_model, how: "HAR-CJ separates C and J at all horizons" }
    - { node_id: signed_jumps, how: "further decomposing J by sign" }
  key_points:
    - "J_t = max(RV_t - BPV_t, 0)"
    - "max() ensures non-negativity (measurement error can make RV < BPV on jumpless days)"
    - "C_t = BPV_t is the continuous component"
    - "Jumps are transient; continuous component carries the forecasting signal"
  misconceptions:
    - "J_t = 0 means no jumps occurred (could be too small to detect or masked by measurement error)"
    - "max() is just for convenience (without it, negative jump estimates are meaningless)"
  why_it_matters: "This gives you separate C and J features where the model learns that C predicts and J doesn't."

- id: har_j_model
  name: "How HAR-J adds jump info to the forecast"
  layer: 1
  chapter: 6
  requires: [har_model, jump_component_feature]
  connects_to:
    - { node_id: har_cj_model, how: "HAR-CJ extends decomposition to all horizons" }
    - { node_id: shar_model, how: "easily confused -- HAR-J separates jumps, SHAR separates sign" }
  key_points:
    - "Adds J_t as 4th regressor to standard HAR"
    - "beta_J typically negative and small (jumps don't persist)"
    - "Andersen Bollerslev Diebold (2007)"
    - "Most predictive power still from continuous component"
  misconceptions:
    - "HAR-J uses only the jump component (it adds jumps ON TOP of full HAR)"
  why_it_matters: "Demonstrates that explicitly modeling jumps helps, even if the coefficient is small."

- id: har_cj_model
  name: "How HAR-CJ separates C and J at all time scales"
  layer: 1
  chapter: 6
  requires: [har_j_model]
  connects_to:
    - { node_id: jump_component_feature, how: "uses C and J at daily/weekly/monthly" }
    - { node_id: har_j_model, how: "HAR-J is the simpler version" }
  key_points:
    - "6 slope coefficients: C_d, C_w, C_m, J_d, J_w, J_m"
    - "Continuous coefficients large and significant"
    - "Jump coefficients small and often insignificant at weekly/monthly"
    - "Corsi Pirino Reno (2010)"
  misconceptions:
    - "More coefficients always means better (extra parameters can overfit with short samples)"
  why_it_matters: "Most complete linear C/J decomposition -- your ML model is the nonlinear generalization."

- id: signed_jumps
  name: "Why separating positive from negative jumps adds signal"
  layer: 1
  chapter: 4, 10
  requires: [jump_component_feature, leverage_effect]
  connects_to:
    - { node_id: semivariances, how: "same sign-splitting logic applied to diffusion" }
    - { node_id: leverage_effect, how: "negative jumps amplify vol more -- same asymmetry" }
  key_points:
    - "J+ = squared returns from large positive moves > threshold"
    - "J- = squared returns from large negative moves > threshold"
    - "J- substantially more predictive of future vol"
    - "Adds 1-3% QLIKE improvement"
  misconceptions:
    - "Signed jumps = semivariances (semivariances split ALL returns; signed jumps split only large/jump returns)"
  why_it_matters: "Cheap feature capturing asymmetric tail risk beyond what semivariances provide."
```

**Cross-Cutting:**

```yaml
- id: triple_expansion
  name: "Why level/change/z-score triples features for free"
  layer: 1
  chapter: 10
  requires: [rv_construction]
  connects_to:
    - { node_id: harq_feature, how: "apply to sqrt(RQ)" }
    - { node_id: semivariances, how: "apply to RV- and RV+" }
  key_points:
    - "Level = current state, change = momentum, z-score = anomaly"
    - "Same value means different things at different scales (5c spread alarming for 3c stock, normal for 6c)"
    - "Multicollinearity harmless for trees (they pick best split)"
    - "Triples feature count from ~20 base to ~60-80"
  misconceptions:
    - "This introduces multicollinearity problems (only for linear models; trees handle it)"
    - "Z-score is always better than level (sometimes raw level is more informative)"
  why_it_matters: "Primary reason your feature count grows from ~10 base features to ~30-40 model inputs."
```

---

## 8. Checklist Integration Process

The GS agent should execute this on first setup:

1. Bootstrap the graph with the 28 nodes defined above (Section 7)
2. Read `layer01-learning-checklist.md`
3. Run the `/expand-learning-graph merge` flow:
   - Map each checklist item to existing nodes or create new nodes
   - Apply the dedup/validation checks (Section 4.5)
   - Present proposed changes for approval
4. Initialize `mastery-state.json` with all nodes at "untested"
5. Run `/learning-status` to confirm the setup

---

## 9. Session Flow Protocol

How the agent should run sessions using the skills:

**Opening a study session:**
1. Run `/learning-status` (via subagent) to see what's due
2. If reviews are due: start with `/quiz` (2-3 review items)
3. If no reviews: start with `/teach` (auto-selects next concept)

**During a session:**
- Mix review (spaced repetition) with new material
- Use `/teach` for guided study, `/quiz` for assessment
- When `/teach` suggests transitioning to `/quiz`, do it
- Interrupted? Fine -- all state is persisted

**Ending a session:**
- `/quiz` retests anything taught mid-session before wrapping up
- Session log entry written to `session-log.md`

**Weekly cadence:**
- Monday: `/weekly-learning-goals` generates the week's targets
- Daily: `/learning-status` -> `/quiz` and/or `/teach`
- Friday: `/weekly-learning-goals` reviews progress, rolls over

---

## 10. Agent Prompts for GS Machine

Copy-paste these prompts **in order** to the agent on your GS machine (Copilot Chat).
Each prompt references the design spec so the agent always has full context.
Run the verification check after each prompt before moving to the next.

**Important context for the GS agent:** The GS repo (`h:\ml-vol-estimator\`) uses:
- `.github/prompts/{command}.prompt.md` for slash command routing
- `skills/` at repo root for skill definitions (NOT `.claude/skills/`)
- `workflows/` for state machine orchestration
- `memory/INDEX.md` as the CoALA master lookup with load tables
- `workspace/` for active workspace files (configs, research, plans, tmp)
- The agentic framework is documented in `notes/ml_vol_forecasting_docs.md` (local ML repo)
  and the full design spec will be synced to `workspace/docs/vol-learning-framework-design.md`

---

### Prompt 0: Sync the Design Spec

```
I have a design spec for a learning framework that I need to bring into this repo.
I'm going to paste the full contents. Save it to:

  workspace/docs/vol-learning-framework-design.md

This file is the SINGLE SOURCE OF TRUTH for everything in the learning framework.
Every prompt I give you about the learning system will reference this file.
Do not modify it without my explicit approval.

After saving, confirm the file exists and show me the section headings.
```

Then paste the full contents of `docs/superpowers/specs/2026-05-20-vol-learning-framework-design.md`.

---

### Prompt 1: Bootstrap the Learning Framework Data Files

```
Read the design spec at workspace/docs/vol-learning-framework-design.md (the entire file).
Pay close attention to Sections 1 (schema), 6 (data files), and 7 (starter graph).

TASK: Create the learning framework data directory and all data files.

STEP 1 -- Create the directory structure:
  workspace/learning/
    graph.yaml
    mastery-state.json
    session-context.json
    session-log.md
    weekly-goals.md

Place this under workspace/ because it is active workspace data (like workspace/configs/
and workspace/research/), not source code, not a skill, and not memory.

STEP 2 -- Bootstrap graph.yaml:
Copy the 28-node starter graph EXACTLY as defined in Section 7 of the design spec.
Every node must have all fields: id, name, layer, chapter, requires, connects_to,
key_points, misconceptions, why_it_matters.
Do NOT paraphrase, summarize, or rewrite any key_points or misconceptions.
Copy them verbatim from the spec.

STEP 3 -- Initialize mastery-state.json:
Create one entry per node ID from graph.yaml. Every entry should be:
  { "tier": "untested", "next_review": null, "consecutive_passes": 0, "last_tested": null }

STEP 4 -- Initialize other files:
- session-context.json: empty object {}
- session-log.md: header "# Learning Session Log" with a blank line
- weekly-goals.md: header "# Weekly Learning Goals" with a blank line

STEP 5 -- Merge the existing checklist:
Read layer01-learning-checklist.md (should be in workspace/ or workspace/research/).
For each item in the checklist:
  a) Compare against ALL 28 existing nodes. Check if the item's content overlaps
     with an existing node's key_points (60%+ overlap = match) or if the item
     name describes the same concept with different wording.
  b) If it matches an existing node: propose merging the new points into that
     node's key_points or misconceptions. Show me: "MERGE into [node_id]: adding
     key_point '[new point]'"
  c) If it's genuinely new (no match): propose a new node following the schema
     from Section 1. Show me the full proposed node with requires edges.
  d) If you're unsure whether it's a match: flag it as "AMBIGUOUS: [item] might
     match [node_id] because [reason]. Merge or create new?"

Present ALL proposed changes in a single summary. Do NOT write anything to
graph.yaml until I approve.

STEP 6 -- After I approve, write the changes and run validation:
  - Every non-root node has at least one requires edge
  - No circular dependencies (follow requires chains, ensure no loops)
  - All node_ids in requires and connects_to reference nodes that exist in graph.yaml
  - No node has more than 5 requires edges
  - No two nodes share 60%+ of the same key_points (dedup check)
  - Report any violations found

Show me the final output:
  - Total node count (should be 28 + however many new nodes from the checklist)
  - Per-layer breakdown: Layer 0: X nodes, Layer 1: Y nodes
  - A dashboard-style summary: all nodes listed with their tier (all "untested" at this point)
```

**Verification check -- run this after Prompt 1:**
```
Verify the learning framework bootstrap:
1. Read workspace/learning/graph.yaml and count all nodes (lines starting with "- id:").
   Report: "Found N nodes"
2. Read workspace/learning/mastery-state.json and count all keys.
   Report: "Found N entries in mastery state"
3. Confirm these counts match exactly.
4. Pick 3 random nodes from graph.yaml and verify their requires targets all
   exist as defined nodes in the same file.
5. Confirm session-log.md, weekly-goals.md, and session-context.json all exist
   and are properly initialized.

Report pass/fail for each check.
```

---

### Prompt 2: Create the Skills

```
Read the design spec at workspace/docs/vol-learning-framework-design.md (full file).
Pay close attention to Sections 4.1-4.5 (skill definitions), Section 5 (subagent
architecture), and Section 3 (spaced repetition intervals).

Also read notes/ml_vol_forecasting_docs.md Section 4 (Agentic Workflow Framework)
to understand how skills are structured in this repo.

TASK: Create 5 learning skills. Each skill goes in the skills/ directory at repo
root (where the existing 46 skills live), following the repo's existing skill
file format.

IMPORTANT CONVENTIONS:
- Skills in this repo live at: skills/{skill-name}.md (flat files, not subdirectories)
- Each skill file uses YAML frontmatter (name, description) then markdown instructions
- Skills reference data files by path relative to repo root
- All subagents MUST use Opus 4.6 (claude-opus-4-6)
- Data files live at: workspace/learning/ (graph.yaml, mastery-state.json, etc.)
- The vol-learning-guide markdown is at: (synced from ML repo or available locally)
  -- if not available locally, the skill should note it can teach from key_points

Create these 5 skill files:

1. skills/quiz.md
   Full spec: Section 4.1 of the design doc.
   Key behaviors to encode:
   - Concept selection priority: (1) overdue reviews, (2) mid-session retests,
     (3) frontier nodes by downstream impact
   - Tier-appropriate techniques (copy the table from Section 4.1 verbatim)
   - Gap handling: teach -> continue 2-3 concepts -> retest -> schedule if pass
   - Spaced repetition intervals: 1st=same day 2-3hrs, 2nd=next day, 3rd=3d,
     4th=7d, 5th=14d. On fail: reset to same-day.
   - After EVERY concept interaction, dispatch an Opus 4.6 subagent to update
     workspace/learning/mastery-state.json (keeps main context clean)
   - Dispatch an Opus 4.6 subagent to read graph.yaml and compute the next
     concept to quiz (returns: node_id, name, tier, key_points, misconceptions,
     why_it_matters, and the quiz technique to use)
   - When all nodes in a layer reach "mastered", announce it and suggest
     /expand-learning-graph
   - Confidence calibration: ask 1-5 before mastery-tier questions

2. skills/teach.md
   Full spec: Section 4.2 of the design doc.
   Key behaviors to encode:
   - Three invocation modes:
     a) /teach bpv -- teach specific concept (match argument against node IDs and names)
     b) /teach jumps -- teach a concept thread (follow connects_to + requires edges)
     c) /teach (no arg) -- auto-select next concept. Logic: dispatch Opus 4.6
        subagent to read graph + mastery state and return the highest-impact
        frontier node. If all frontier nodes are untested, start from root
        foundations (log_returns, variance_as_spread, etc.)
   - Teaching approach: prerequisites first (verify before teaching), plain
     English -> formula -> project connection, lightweight check after each concept
   - Adaptive depth: if user says "I don't understand X" or fails a check,
     immediately follow requires edges downward to find solid ground, then
     build back up
   - Track all concepts covered in workspace/learning/session-context.json
     (dispatch Opus 4.6 subagent for writes)
   - At stopping points: "We covered [N] concepts: [list]. Want to lock them
     in? Run /quiz and I'll focus on what we just studied."

3. skills/learning-status.md
   Full spec: Section 4.3 of the design doc.
   Key behaviors to encode:
   - Dispatch a SINGLE Opus 4.6 subagent that reads workspace/learning/graph.yaml
     and workspace/learning/mastery-state.json, computes everything, and returns
     the formatted dashboard
   - Dashboard sections: per-layer progress bars, due-today queue, due-this-week,
     frontier nodes (sorted by downstream impact), stale alerts (understood but
     not reviewed in 14+ days), recommendation
   - The main agent just displays what the subagent returns. Zero data processing
     in the main context.

4. skills/weekly-learning-goals.md
   Full spec: Section 4.4 of the design doc.
   Key behaviors to encode:
   - Dispatch Opus 4.6 subagent to analyze graph + mastery state and generate goals
   - Subagent returns: 5-8 prioritized concepts with rationale for each
   - Prioritization: (1) highest downstream unlock impact, (2) stuck at
     recognized 7+ days, (3) review backlog
   - Mix: ~40% review/advancement, ~60% new frontier
   - Layer completion awareness: "3 concepts from completing Layer 1"
   - When run again: show achieved vs planned, roll over unfinished

5. skills/expand-learning-graph.md
   Full spec: Section 4.5 of the design doc.
   Key behaviors to encode:
   - Three modes: merge (file path arg), add (concept description arg),
     layer (layer number arg)
   - ALL expansion work done by Opus 4.6 subagent (reads graph, proposes changes)
   - ROBUST deduplication (copy the 5-point validation from Section 4.5 verbatim):
     exact ID check, semantic similarity (60%+ key_points), subset check,
     merge/split/keep-both options, structural validation
   - NEVER write to graph.yaml without user approval. Always present proposed
     changes first.
   - Coverage check when adding a layer: read the relevant vol-learning-guide
     markdown chapter(s), verify every major section maps to at least one node

After creating each skill file, show me its full path and the first 5 lines
(to confirm format is correct).
```

**Verification check -- run this after Prompt 2:**
```
Verify the learning skills were created correctly:

1. List all files matching skills/*learn* and skills/quiz* and skills/*expand*
   and skills/*weekly* and skills/*status*. Confirm all 5 exist.

2. For each skill file, check:
   a) Has YAML frontmatter with name and description fields
   b) References workspace/learning/graph.yaml and workspace/learning/mastery-state.json
   c) Mentions "Opus 4.6" or "claude-opus-4-6" for subagent dispatch
   d) Does NOT reference .claude/skills/ (wrong path for this repo)

3. Read skills/quiz.md and confirm it contains:
   - The spaced repetition interval table (same-day, 1d, 3d, 7d, 14d)
   - The tier-appropriate techniques table
   - Gap handling flow (teach -> continue -> retest)

4. Read skills/teach.md and confirm it contains:
   - Auto-selection logic for no-argument invocation
   - Adaptive depth behavior (drop to prerequisites)
   - Session-context.json handoff to /quiz

Report pass/fail for each check. If anything fails, fix it.
```

---

### Prompt 3: Register the Slash Commands

```
Read the design spec at workspace/docs/vol-learning-framework-design.md (Sections 4.1-4.5)
and notes/ml_vol_forecasting_docs.md (Section 4: Prompt Routing Model).

TASK: Create .github/prompts/ entries so the 5 learning skills are accessible
as slash commands, matching this repo's routing convention.

Create these 5 files:

1. .github/prompts/quiz.prompt.md
   - Routes to: skills/quiz.md
   - Short description: "Interactive vol-knowledge quiz session with Feynman-style
     prompts, chain-of-why drilling, and spaced repetition tracking"

2. .github/prompts/teach.prompt.md
   - Routes to: skills/teach.md
   - Short description: "Guided teaching of vol concepts. Adapts to your level,
     builds from prerequisites, hands off to /quiz when ready"

3. .github/prompts/learning-status.prompt.md
   - Routes to: skills/learning-status.md
   - Short description: "Dashboard of mastery progress across feature layers,
     review queue, and study recommendations"

4. .github/prompts/weekly-learning-goals.prompt.md
   - Routes to: skills/weekly-learning-goals.md
   - Short description: "Generate and track gap-driven weekly learning goals"

5. .github/prompts/expand-learning-graph.prompt.md
   - Routes to: skills/expand-learning-graph.md
   - Short description: "Add concepts, merge checklists, or add new feature layers
     to the learning dependency graph"

Match the format of existing .github/prompts/ files in this repo (read one or two
to see the convention, then follow it exactly).

After creating all 5, list all .github/prompts/ files that contain "learn" or "quiz"
to confirm they're registered.
```

**Verification check -- run this after Prompt 3:**
```
Verify slash command registration:
1. List all .github/prompts/*.prompt.md files. Confirm the 5 new ones exist
   alongside the existing commands.
2. For each new prompt file, confirm it correctly references the skill file
   path (skills/quiz.md, skills/teach.md, etc.)
3. Try invoking /learning-status. Confirm it dispatches a subagent, reads the
   graph and mastery state, and returns a dashboard showing all nodes as "untested."
   This is the smoke test that the full chain works: slash command -> skill -> subagent -> data.

Report pass/fail. If /learning-status doesn't work end-to-end, diagnose why
before proceeding.
```

---

### Prompt 4: Update memory/INDEX.md

```
Read the design spec at workspace/docs/vol-learning-framework-design.md (Section 6).

TASK: Register the learning framework files in the CoALA memory system so the
agent knows they exist and when to load them.

1. Read memory/INDEX.md to understand the current structure and format.

2. Add a new section or entries (matching the existing format) for:
   - workspace/learning/graph.yaml -- "Volatility concept dependency graph for
     mastery tracking. 28+ nodes across feature layers 0-7."
   - workspace/learning/mastery-state.json -- "Per-concept mastery tier, spaced
     repetition schedule, and pass history."
   - workspace/docs/vol-learning-framework-design.md -- "Complete design spec for
     the learning framework. Single source of truth for all /quiz, /teach,
     /learning-status, /weekly-learning-goals, /expand-learning-graph skills."

3. If INDEX.md has load-table sections (mapping task types to files to load),
   add an entry so that any /quiz, /teach, /learning-status, /weekly-learning-goals,
   or /expand-learning-graph invocation triggers loading of graph.yaml and
   mastery-state.json.

4. Do NOT remove or modify any existing INDEX.md entries. Only add.

Show me the diff of what you changed in INDEX.md.
```

---

### Prompt 5: Update /bootup to Include Learning Progress

```
Read the design spec at workspace/docs/vol-learning-framework-design.md (Section 9:
Session Flow Protocol).

TASK: Modify the /bootup workflow to include a learning progress summary so that
every session starts with awareness of where I am in my study.

1. Read the current bootup workflow file. It is one of:
   - workflows/bootup.md
   - .github/prompts/bootup.prompt.md
   - Or wherever the 7-step boot protocol is defined
   Identify the file and read it.

2. Add a new step to the bootup sequence (after loading memory and checking
   handoffs, but before offering next steps). The new step should:
   - Dispatch an Opus 4.6 subagent to read workspace/learning/mastery-state.json
     and workspace/learning/graph.yaml
   - The subagent computes and returns a BRIEF summary (3-5 lines max):
     * Per-layer mastery: "Layer 0: 12/15 mastered | Layer 1: 4/13 understood"
     * Reviews due today: count and list of concept names
     * Current weekly goal progress (read workspace/learning/weekly-goals.md)
   - The bootup displays this summary under a "Learning Progress" heading

3. Also add to the bootup's "next steps" suggestions:
   - If reviews are due: "You have N reviews due. Consider starting with /quiz."
   - If no reviews but frontier nodes ready: "Ready to learn? Run /teach to
     pick up where you left off."

4. The learning summary should be OPTIONAL -- if workspace/learning/mastery-state.json
   doesn't exist (framework not yet set up), skip this step silently.
   Do NOT break bootup for sessions where learning isn't the focus.

Show me the full diff of the bootup file changes.
```

**Verification check -- run this after Prompt 5:**
```
Verify the bootup integration:
1. Run /bootup and confirm it completes all existing steps normally.
2. Confirm a "Learning Progress" section appears showing all nodes as "untested"
   (since we haven't done any quizzing yet).
3. Confirm the next-steps section includes a learning-related suggestion.
4. If any existing bootup functionality is broken, revert your changes and
   diagnose what went wrong.

Report pass/fail.
```

---

### Prompt 6: Run the First Assessment

```
Read the design spec at workspace/docs/vol-learning-framework-design.md (Sections 2
and 4.1). This is my first quiz session to establish a baseline.

TASK: Run a baseline assessment across all Layer 0 and Layer 1 concepts.

MODE: This is a "baseline sweep," not a deep drill. The goal is to map my current
knowledge quickly so we know where to focus deep study.

PROCEDURE:
1. Dispatch an Opus 4.6 subagent to read workspace/learning/graph.yaml and return
   all Layer 0 nodes sorted by dependency order (roots first, then nodes whose
   requires are all roots, etc.) followed by all Layer 1 nodes in the same order.

2. For each concept, in dependency order:
   - Ask me ONE Feynman-style prompt. Format: "Explain to me, as if I'm a new
     intern who just joined the desk, [concept-specific question based on the
     node's name and why_it_matters]."
   - Wait for my answer.
   - Evaluate my answer against the node's key_points. Assign a tier:
     * "untested" -- I said "I don't know" or "skip"
     * "recognized" -- I got the gist but missed key_points or was vague
     * "understood" -- I hit all key_points clearly in plain English
   - Do NOT assign "mastered" in baseline (that requires two separate sessions).
   - Do NOT do chain-of-why drilling (save that for deep sessions).
   - Do NOT teach gaps (just log them).
   - After evaluating, briefly say: "[concept_name]: [tier]. [1 sentence on what
     was strong or what was missed]." Then move to the next concept.
   - Dispatch an Opus 4.6 subagent to update mastery-state.json with the tier.

3. After all concepts are assessed, dispatch an Opus 4.6 subagent to compute
   the full /learning-status dashboard and return it.

4. Show me:
   a) The full dashboard (per-layer breakdown with tier counts)
   b) A "gaps found" list: all concepts at "untested" or "recognized" with
      the specific key_points I missed
   c) A recommended study plan: which concepts to /teach first, prioritized by
      downstream impact (concepts that unlock the most other nodes)
   d) Suggested first /teach session: "Start with /teach [concept] because
      it unlocks [N] downstream concepts and you scored [tier] on it."

This should take about 30-45 minutes. We'll do deep drilling in follow-up sessions.
```

---

### Prompt 7: Start a Study Session (daily use)

```
Read the design spec at workspace/docs/vol-learning-framework-design.md (Section 9:
Session Flow Protocol).

I have downtime while my models train. Let's study.

1. Dispatch an Opus 4.6 subagent to run the /learning-status computation
   (read graph.yaml + mastery-state.json, compute dashboard). Show me the
   brief summary: reviews due, frontier nodes ready, weekly goal progress.

2. Based on the summary, choose the session type:
   - If 3+ reviews are overdue: start with /quiz focused on those reviews
   - If reviews < 3 but session-context.json has concepts from a recent /teach:
     start with /quiz on those specific concepts (the learn->quiz handoff)
   - Otherwise: start with /teach (auto-select the next most natural concept)

3. During the session:
   - If I say "I don't understand X": immediately drop to prerequisites for X.
     Follow requires edges downward until you find a concept I'm solid on,
     then build back up with /teach.
   - If I say "quiz me" or "test me": switch to /quiz mode.
   - If I say "skip" or "next": move to the next concept without penalizing.
   - Save state after EVERY interaction (dispatch subagent to update mastery-state.json).
     I may need to check on my models at any moment.

4. When I say "done" or "stopping": show me a brief session summary:
   - Concepts covered this session
   - Tier changes (what moved up or down)
   - What's recommended for next session

Let's go.
```
