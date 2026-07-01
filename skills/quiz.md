---
name: quiz
description: "Interactive spaced-repetition quiz session for vol-learning-guide concepts. USE FOR: testing mastery of volatility concepts, spaced repetition reviews, gap-driven quizzing, tier advancement. DO NOT USE FOR: teaching new concepts (use learn), checking progress dashboard (use learning-status), expanding the graph (use expand-learning-graph)."
---

# /quiz — Interactive Assessment Session

> **Purpose:** The core learning loop. Quizzes you on volatility concepts from `workspace/learning/graph.yaml` using tier-appropriate techniques, tracks mastery via spaced repetition, and handles gaps by teaching then retesting.

## Data Files

| File | Purpose | Access |
|------|---------|--------|
| `workspace/learning/graph.yaml` | Dependency graph (nodes, edges, key_points, misconceptions) | Read |
| `workspace/learning/mastery-state.json` | Per-node tier, next_review, consecutive_passes | Read + Write (via subagent) |
| `workspace/learning/session-context.json` | Concepts from last `/teach` session to prioritize | Read |

## Concept Selection Priority

Select the next concept to quiz in this order:

1. **Overdue spaced repetition reviews** — nodes where `next_review` < now
2. **Mid-session retests** — concepts taught earlier this session (gap handling retest)
3. **Frontier nodes by downstream impact** — nodes whose prerequisites are all >= "understood", sorted by how many other nodes they unlock (count descendants in `requires` DAG)

Only quiz concepts whose `requires` are ALL at least "understood." Never quiz a concept with unmet prerequisites.

## Subagent: Select Next Concept

Before each quiz interaction, dispatch an **Opus 4.6** subagent:

```
Prompt: You are a learning framework data agent. Read workspace/learning/graph.yaml
and workspace/learning/mastery-state.json. Also read workspace/learning/session-context.json
if it exists (for mid-session retests).

Compute the next concept to quiz using this priority:
1. Overdue reviews (next_review < current date/time)
2. Mid-session retests (from session-context.json retest_queue)
3. Frontier nodes sorted by downstream impact (count of transitive dependents)

Return ONLY a JSON object:
{
  "node_id": "...",
  "name": "...",
  "tier": "current tier (untested/recognized/understood/mastered)",
  "target_tier": "tier being tested toward",
  "key_points": [...],
  "misconceptions": [...],
  "why_it_matters": "...",
  "connects_to": [...],
  "technique": "one of: feynman_prompt, chain_of_why, contrastive, spot_the_mistake, scenario",
  "selection_reason": "overdue_review | mid_session_retest | frontier"
}

If no concepts are quizzable (all mastered or no prerequisites met), return:
{ "status": "all_complete", "message": "..." }
```

## Tier-Appropriate Techniques

| Target tier | Technique | Pass criteria |
|---|---|---|
| Recognized -> Understood | Feynman prompt: "Explain X to a new intern" | Hits all `key_points`, avoids `misconceptions` |
| Understood (chain-of-why) | Follow-up "Why?" drilling on their answer | Reaches bedrock without stalling or contradicting |
| Understood -> Mastered | Contrastive: "What's the difference between X and Y?" (using `connects_to` with "easily confused") | Correctly discriminates both concepts |
| Understood -> Mastered | Spot-the-mistake: "A colleague says [misconception]. What's wrong?" | Identifies the specific error and explains the correct reasoning |
| Understood -> Mastered | Scenario: present a realistic project situation | Connects concept to project decision unprompted |

## Spaced Repetition Intervals

| Consecutive passes | Next review |
|---|---|
| 1st pass | Later same day (2-3 hours) |
| 2nd pass | Next day |
| 3rd pass | 3 days |
| 4th pass | 7 days |
| 5th pass | 14 days (considered stable) |

**On any fail:** reset `consecutive_passes` to 0, schedule review for later same day.

## Gap Handling Flow

When the user fails a quiz question or reveals a gap:

1. **Teach intuitively** — plain English using `key_points` + `why_it_matters`, no formulas unless user asks
2. **Continue to the next 2-3 concepts** — don't get stuck; keep session momentum
3. **Circle back with a rephrased version** of the original question (mid-session retest)
4. **If pass on retest:** schedule for spaced repetition (1st pass -> review in 2-3 hours)
5. **If fail on retest:** flag concept for a `/teach` deep-dive, move on

## Confidence Calibration

Before mastery-tier questions (Understood -> Mastered), ask:

> "On a scale of 1-5, how confident are you on [concept name]?"

Track calibration over time to reveal blind spots (overconfident = high confidence + fail).

## Subagent: Update Mastery State

After EVERY concept interaction (pass or fail), dispatch an **Opus 4.6** subagent:

```
Prompt: You are a learning framework data agent. Read workspace/learning/mastery-state.json.
Update the entry for node_id "[node_id]" with:
- tier: "[new_tier]"
- consecutive_passes: [new_count]
- last_tested: "[ISO date]"
- next_review: "[computed from spaced repetition table]"

Spaced repetition schedule:
- 1 consecutive pass: same day, 2-3 hours from now
- 2 passes: next day
- 3 passes: 3 days
- 4 passes: 7 days
- 5 passes: 14 days

On fail: consecutive_passes = 0, next_review = later same day.

Write the updated JSON back to workspace/learning/mastery-state.json.
Return a one-line confirmation of the change made.
```

## Layer Completion

When all nodes in a given layer reach "mastered":
- Announce: "Layer [N] complete! All [count] concepts mastered."
- Suggest: "Run `/expand-learning-graph layer [N+1]` to add the next layer."

## Session Flow

1. Dispatch subagent to select next concept
2. Present the quiz question using the appropriate technique
3. Evaluate the user's response against `key_points` and `misconceptions`
4. Announce pass/fail with brief feedback including mastery state: concept name, new tier, consecutive passes, and next review date (e.g., "**Pass** — `bpv_jump_robustness`: recognized → understood (2/5 passes, next review: May 21)")
5. Dispatch subagent to update mastery state
6. If gap found: enter gap handling flow
7. Repeat from step 1

## Interruption Handling

Session can be stopped at any point. All progress is already persisted via subagent writes after each interaction. Next `/quiz` picks up from the current state.
