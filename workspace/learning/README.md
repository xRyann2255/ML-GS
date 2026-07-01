# Vol-Knowledge Learning Framework

A dependency-graph-driven spaced-repetition system for mastering volatility forecasting concepts. Tracks what you know, identifies gaps, teaches new material in prerequisite order, and locks knowledge through timed retrieval practice.

---

## Table of Contents

- [Architecture](#architecture)
- [Data Files](#data-files)
- [Mastery Tiers](#mastery-tiers)
- [Spaced Repetition](#spaced-repetition)
- [Commands](#commands)
- [Session Flow](#session-flow)
- [Graph Structure](#graph-structure)
- [Examples](#examples)

---

## Architecture

The system is built on six VS Code slash commands, each backed by a skill file that defines behavior. All data-heavy operations (graph traversal, scheduling, state updates) are delegated to Opus 4.6 subagents so the main conversation context stays clean.

```
┌─────────────────────────────────────────────────┐
│  VS Code Chat                                   │
│  User types: /study, /teach, /quiz, etc.        │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│  Skill File (e.g. skills/study.md)              │
│  Defines: routing logic, interaction protocol   │
└──────────────────────┬──────────────────────────┘
                       │ dispatches
                       ▼
┌─────────────────────────────────────────────────┐
│  Subagent (Opus 4.6)                            │
│  Reads: graph.yaml, mastery-state.json          │
│  Returns: decisions, formatted output           │
│  Writes: mastery-state.json, session-context    │
└─────────────────────────────────────────────────┘
```

Key design principles:
- **Prerequisite gating:** A concept cannot be quizzed until all its `requires` dependencies are at least "understood"
- **Persistence after every interaction:** State is saved after each teach/quiz exchange, so interruptions are safe
- **Separation of concerns:** `/teach` explains, `/quiz` assesses, `/study` orchestrates

---

## Data Files

All learning state lives in `workspace/learning/`:

| File | Purpose |
|------|---------|
| `graph.yaml` | Dependency graph of all concepts (nodes, edges, metadata) |
| `mastery-state.json` | Per-node mastery tier, review schedule, and pass history |
| `session-context.json` | Bridge between teach and quiz within a single session |
| `session-log.md` | Historical log of completed sessions |
| `weekly-goals.md` | Weekly learning priorities and progress tracking |

### graph.yaml — Node Schema

```yaml
- id: har_model                        # unique snake_case identifier
  name: "The HAR Model"                # human-readable name
  layer: 0                             # feature layer (0, 1, 2, ..., 99 for evaluation)
  chapter: "ch06"                      # reference to vol-learning-guide chapter
  requires: [rv_construction, log_rv_transform, heterogeneous_market_hypothesis]
  connects_to: [harq_model, shar_model, har_j_model]
  key_points:                          # what "understood" means for this concept
    - "Decomposes volatility into daily, weekly, monthly components"
    - "Approximates long-memory via three additive terms"
  misconceptions:                      # common errors to test against
    - "HAR captures true long memory (it doesn't — it approximates)"
  why_it_matters: "Primary baseline model; everything else is measured against HAR"
```

- `requires` = hard prerequisite gate (must be understood before this node can be quizzed)
- `connects_to` = soft link suggesting conversational flow (not a gate)

### mastery-state.json — Entry Schema

```json
{
  "har_model": {
    "tier": "recognized",
    "next_review": "2026-05-22",
    "consecutive_passes": 1,
    "last_tested": "2026-05-21"
  }
}
```

---

## Mastery Tiers

```
untested → recognized → understood → mastered
```

| Tier | Meaning | How to Promote |
|------|---------|----------------|
| **untested** | Never quizzed | Engage with the concept (teach or quiz) |
| **recognized** | Can identify and engage meaningfully | Pass a Feynman-style explanation |
| **understood** | Can explain simply and survive why-drilling | Pass two separate mastery-tier sessions (contrastive, scenario, or spot-the-mistake) |
| **mastered** | Can connect, discriminate, and apply without hints | Stable — enters long-interval maintenance reviews |

Promotion is never automatic. Every tier change requires demonstrated performance in a quiz interaction.

---

## Spaced Repetition

After each successful quiz pass, the review interval increases:

| Consecutive Passes | Next Review |
|---|---|
| 1 | Same day (2-3 hours later) |
| 2 | Next day |
| 3 | 3 days |
| 4 | 7 days |
| 5+ | 14 days (stable) |

**On any fail:** `consecutive_passes` resets to 0 and the concept is scheduled for same-day review.

A concept is "overdue" when `next_review` is today or earlier. Overdue concepts take priority in quiz selection.

---

## Commands

### `/study` — Adaptive Session Orchestrator

**What it does:** Assesses your current state and automatically routes to `/teach` or `/quiz` based on what's most productive right now.

**Arguments:** None.

**Routing logic:**
1. 3+ overdue reviews → starts with `/quiz` (review mode)
2. Recent teaches in last 24h not yet quiz-tested → starts with `/quiz` (retest mode)
3. Otherwise → starts with `/teach` (new material)

**Mid-session pivot commands:**
- "quiz me" / "test me" → switch to quiz on current session concepts
- "teach me X" / "explain X" → switch to teach for concept X
- "I don't understand X" → drop to prerequisites for X
- "skip" / "next" → continue to next concept
- "done" / "stopping" → exit with session summary

---

### `/teach` — Guided Instruction

**What it does:** Explains volatility concepts from the dependency graph, adapting depth to your level.

**Arguments:**
- `/teach bpv` — teach a specific concept (matches node ID or name)
- `/teach jumps` — teach a thread (follows `connects_to` and `requires` chains)
- `/teach` — auto-selects the highest-impact frontier concept

**Teaching approach:**
1. Verify prerequisites are solid
2. Plain English explanation first
3. Then the formula/math
4. Then the project connection (how it's used in the vol forecasting pipeline)
5. Lightweight comprehension check after each concept

After 4-5 concepts, suggests switching to `/quiz` to lock the material.

**Auto-select logic (no argument):**
1. Pick a recognized concept whose prerequisites are understood and that unlocks the most dependents
2. If all frontier nodes are untested, start from root foundations
3. If stale understood concepts are overdue, refresh those first

---

### `/quiz` — Spaced-Repetition Assessment

**What it does:** Runs an interactive quiz session with tier-appropriate techniques and automatic scheduling.

**Arguments:** None (concept selection is automatic based on priority).

**Selection priority:**
1. Overdue reviews (by oldest first)
2. Mid-session retests (concepts just taught in this session)
3. Frontier nodes (sorted by downstream impact)

**Techniques by tier transition:**

| Transition | Technique |
|---|---|
| recognized → understood | Feynman explanation ("explain X as if to a colleague") |
| understood → mastered | Contrastive ("how does X differ from Y?"), spot-the-mistake, or scenario application |

**Chain-of-why drilling:** After the initial explanation, follows up with "why?" questions to probe depth.

**Confidence calibration:** Before mastery-tier questions, asks for a 1-5 confidence rating.

**Gap handling:** If you fail, the system teaches the gap intuitively, continues with 2-3 other concepts, then circles back with a rephrased question.

---

### `/learning-status` — Progress Dashboard

**What it does:** Displays a formatted dashboard of your current mastery state.

**Arguments:** None.

**Sections displayed:**
1. Per-layer progress bars (e.g., "Layer 0: ████░░░░ 12/24 mastered")
2. Due today (concepts needing review)
3. Due this week
4. Frontier nodes (next concepts eligible for learning)
5. Stale alerts (understood nodes not reviewed for 14+ days)
6. Recommendation (actionable next step)

---

### `/weekly-learning-goals` — Weekly Priorities

**What it does:** Generates 5-8 prioritized learning targets for the week, balancing review and new material.

**Arguments:** None.

**Prioritization:**
1. Concepts blocking the most downstream nodes
2. Concepts stuck at "recognized" for 7+ days
3. Review backlog (if 5+ reviews are due)

**Target mix:** ~40% review/advancement, ~60% new frontier concepts.

**Output includes:**
- Last week's score (e.g., "5/7 goals met")
- Category labels: REVIEW, ADVANCE, NEW
- Layer-completion alerts when close to finishing a layer

When rerun later in the same week, shows achieved vs planned and rolls unfinished goals forward.

---

### `/expand-learning-graph` — Graph Expansion

**What it does:** Adds new concepts to the dependency graph with robust deduplication and validation.

**Arguments:**
- `merge <filepath>` — merge a checklist or concept list from a file
- `add "<concept description>"` — create one new concept node
- `layer <N>` — add an entire feature layer's concepts

**Safety:** Never writes to `graph.yaml` without explicit user approval. Presents proposed changes (additions, merges, edges, duplicates found, validation warnings) for review first.

**Validation checks:**
1. Exact ID match (no duplicates)
2. Semantic similarity (60%+ shared key points = potential merge)
3. Structural validation (no orphans, no cycles, max 5 `requires` edges per node)
4. Coverage check (layer mode ensures every guide section maps to at least one node)

---

## Session Flow

A typical learning session follows this pattern:

```
1. /learning-status          → See what's due, what's next
2. /study                    → Auto-routes to quiz or teach
   ├── [quiz mode]           → Reviews overdue concepts
   │   └── pass/fail         → Updates mastery-state.json
   └── [teach mode]          → Explains new frontier concepts
       └── after 4-5 items   → Suggests switching to /quiz
3. /quiz                     → Lock taught material via retrieval practice
4. "done"                    → Session summary with tier changes
```

**State is persisted after every interaction.** You can stop at any time and resume later without losing progress. The system picks up where you left off based on `mastery-state.json` and `session-context.json`.

---

## Graph Structure

The concept graph is organized by feature layer, mirroring the vol-forecasting project's architecture:

| Layer | Description | Nodes |
|-------|-------------|-------|
| **0** | Foundations + HAR core (returns, RV, HAR model, log transforms) | 24 |
| **1** | Noise-robust estimators + asymmetry + jumps (RK, HARQ, SHAR, BPV, signed jumps) | 21 |
| **99** | Evaluation (QLIKE, DM test, MCS, Mincer-Zarnowitz, purged CV) | 8 |

**Total:** 53 concepts.

Layer 0 forms the foundation — you must understand returns, variance, and RV construction before progressing to HAR models, which in turn gate Layer 1's extensions (HARQ, SHAR, HAR-J).

Layer 99 (evaluation) depends on HAR model understanding plus feature alignment concepts, ensuring you can assess models before building complex ones.

---

## Examples

### Example 1: First-time session (fresh start)

```
You: /learning-status

Agent: 
  Layer 0: ░░░░░░░░ 0/24 mastered
  Layer 1: ░░░░░░░░ 0/21 mastered
  ...
  Due today: 0 reviews
  Frontier: log_returns, variance_as_spread, simple_returns
  Recommendation: Start with /teach to build foundations.

You: /study

Agent: No reviews due. 0 recent teaches. 24 frontier nodes available.
       Starting mode: teach (foundations).
       
       Let's start with log returns...
```

### Example 2: Daily review session (concepts due)

```
You: /study

Agent: 4 reviews overdue. Starting mode: quiz (reviews).
       
       [Quiz] Explain "realized quarticity" as if to a colleague
       who knows what realized variance is but hasn't seen RQ.

You: RQ is the sum of fourth powers of intraday returns, scaled by N/3...

Agent: ✓ Pass. Key points hit: scaling factor, measurement quality proxy.
       Scheduling next review: May 24.
       
       [Quiz] Next: What's the relationship between BPV and RV 
       when there are no jumps?
```

### Example 3: Teaching a specific concept

```
You: /teach bpv_jump_robustness

Agent: Before we dive into BPV's jump robustness, let me verify 
       prerequisites...
       
       ✓ jumps_vs_diffusion: understood
       ✓ rv_construction: understood
       
       [Teach] Bipower Variation and Jump Robustness
       
       Plain English: BPV estimates the "smooth" part of volatility
       by using products of adjacent absolute returns instead of 
       squared returns...
       
       Formula: BPV = (π/2) × (N/(N-1)) × Σ|r_i| × |r_{i+1}|
       
       Project connection: In our pipeline, BPV is computed in 
       features/asymmetry.py and used to decompose RV into 
       continuous variation (C = BPV) and jump variation (J = RV - BPV).
       
       📖 Vol Learning Guide — Ch.4, §4.2: "Bipower Variation"
```

### Example 4: Expanding the graph with a new layer

```
You: /expand-learning-graph layer 2

Agent: Scanning vol-learning-guide chapters for Layer 2 concepts...
       
       Proposed additions (7 nodes):
       1. atm_implied_vol (requires: har_model)
       2. variance_risk_premium (requires: atm_implied_vol, rv_construction)
       3. iv_skew (requires: atm_implied_vol)
       ...
       
       Duplicates found: 0
       Validation: ✓ No orphans, ✓ No cycles
       
       Approve these additions? [y/n]
```

### Example 5: Weekly goal setting

```
You: /weekly-learning-goals

Agent: Last week: 3/5 goals met (variance_as_spread ✓, vol_clustering ✓, 
       triple_expansion ✓, har_model ✗, rv_construction ✗)
       
       This week's goals:
       1. [REVIEW] variance_as_spread — due May 21, reinforce foundations
       2. [ADVANCE] rv_construction — blocked har_model and 5 downstream
       3. [ADVANCE] har_model — gates all Layer 1 extensions
       4. [NEW] log_rv_transform — prerequisite for har_model
       5. [NEW] five_min_convention — prerequisite for rv_construction
       6. [NEW] integrated_variance — theoretical foundation for RV
       
       Rationale: Prioritizing rv_construction and har_model because 
       they gate 12 downstream concepts across Layers 0-1.
```

---

## Further Reading

- Design Spec — canonical source of truth for all behavior rules, quiz techniques, and promotion criteria
- Vol Learning Guide — the 17-chapter theory reference that concepts map to
- Vol Project Reference — implementation spec that connects concepts to code
