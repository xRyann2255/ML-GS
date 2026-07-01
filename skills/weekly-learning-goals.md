---
name: weekly-learning-goals
description: "Generate and track gap-driven weekly learning goals for vol concepts. USE FOR: setting prioritized weekly targets, reviewing progress against last week's goals, identifying stuck concepts, layer completion tracking. DO NOT USE FOR: quizzing (use quiz), teaching (use learn), checking current status (use learning-status)."
---

# /weekly-learning-goals — Gap-Driven Weekly Planning

> **Purpose:** Generate prioritized weekly learning goals based on mastery state analysis. Balances review/advancement with new frontier exploration. Tracks week-over-week progress.

## Data Files

| File | Purpose | Access |
|------|---------|--------|
| `workspace/learning/graph.yaml` | Dependency graph (nodes, edges, layers) | Read (via subagent) |
| `workspace/learning/mastery-state.json` | Per-node tier, next_review, consecutive_passes | Read (via subagent) |
| `workspace/learning/weekly-goals.md` | Current + historical weekly goals | Read + Write (via subagent) |

## Implementation

Dispatch an **Opus 4.6** subagent to analyze the graph and mastery state, generate goals, and write to `workspace/learning/weekly-goals.md`.

### Subagent Prompt

```
Prompt: You are a learning framework data agent. Read workspace/learning/graph.yaml,
workspace/learning/mastery-state.json, and workspace/learning/weekly-goals.md (if it exists).

TASK: Generate this week's learning goals.

PRIORITIZATION LOGIC (in order):
1. Concepts blocking the most downstream nodes (highest unlock impact) —
   count transitive dependents in the requires DAG
2. Concepts stuck at "recognized" for 7+ days without advancing to "understood"
   (check last_tested date)
3. Spaced repetition backlog — if the review queue (next_review < today) has 5+
   items, prioritize clearing it

MIX: ~40% review/advancement of existing concepts, ~60% new frontier concepts.

LAYER COMPLETION AWARENESS: If the user is within 3 concepts of completing a layer,
call this out explicitly: "You're [N] concepts away from completing Layer [X].
Prioritizing those this week."

OUTPUT:
1. If previous goals exist in weekly-goals.md, first compute achieved vs planned:
   - Mark each prior goal as ACHIEVED (reached target tier) or ROLLED OVER
   - Show: "Last week: X/Y goals met"

2. Generate 5-8 prioritized concepts for this week. For each:
   - node_id and name
   - Current tier -> target tier
   - Rationale (why this concept this week)
   - Category: REVIEW | ADVANCE | NEW

3. Write the new week's goals to workspace/learning/weekly-goals.md under a dated
   section header (## Week of YYYY-MM-DD). Preserve all historical sections.

Return the formatted goals as markdown for display to the user.
```

## Output Format

Example output:

```
## Weekly Learning Goals — Week of 2026-05-20

### Last Week's Results
5/7 goals met. Rolling over: bpv_jump_robustness, jump_component.

### This Week's Targets (7 concepts)

| # | Concept | Current → Target | Category | Rationale |
|---|---------|-----------------|----------|-----------|
| 1 | rv_is_noisy | recognized → understood | ADVANCE | Blocks 6 downstream nodes (HARQ branch) |
| 2 | microstructure_noise_concept | recognized → understood | ADVANCE | Stuck at recognized for 9 days |
| 3 | har_model | understood → mastered | REVIEW | Due for 3rd spaced repetition pass |
| 4 | bpv_jump_robustness | untested → recognized | NEW | Highest-impact Layer 1 frontier (unlocks 4) |
| 5 | semivariances | untested → recognized | NEW | Enables SHAR model understanding |
| 6 | jump_component | untested → recognized | NEW | Completes jump decomposition thread |
| 7 | harq_model | understood → mastered | REVIEW | Overdue review by 3 days |

**Layer alert:** You're 3 concepts away from completing Layer 0. Prioritizing har_approximates_long_memory, har_hard_to_beat, and harq_model.

### Recommended Daily Split
- Mon/Wed: Review sessions (/quiz on items 3, 7)
- Tue/Thu: New concept learning (/teach on items 4-6)
- Fri: Advancement (/quiz on items 1-2 to push to understood)
```

## Week-End Review

When run again after goals are already set for the current week:
- Show achieved vs planned
- Roll over unfinished goals with updated priority
- Track week-over-week trend: "Last week: 6/8 goals met. This week: [new goals]."

## Session Flow

1. User invokes `/weekly-learning-goals`
2. Dispatch Opus 4.6 subagent with all three file paths
3. Display returned goals verbatim
4. No follow-up actions unless user asks
