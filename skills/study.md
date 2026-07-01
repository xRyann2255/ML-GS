---
name: study
description: "Adaptive study session orchestrator for vol-learning concepts. USE FOR: starting a study session that auto-routes between /teach and /quiz based on mastery state, reviews due, and session context. DO NOT USE FOR: only quizzing (use quiz), only teaching a specific concept (use teach), checking dashboard only (use learning-status), expanding the graph (use expand-learning-graph)."
---

# /study — Adaptive Study Session

> **Purpose:** Single entry point for a learning session. Assesses your current state (reviews due, recent teaches, frontier nodes), routes to the right mode (/teach or /quiz), pivots dynamically mid-session, and provides a session summary on exit.

## Data Files

| File | Purpose | Access |
|------|---------|--------|
| `workspace/learning/graph.yaml` | Dependency graph | Read (via subagent) |
| `workspace/learning/mastery-state.json` | Per-node tier, review schedule | Read (via subagent) |
| `workspace/learning/session-context.json` | Concepts covered this session | Read + Write (via subagent) |

## Session Start

1. **Dispatch an Opus 4.6 subagent** to compute a brief session-start summary:

```
Prompt: You are a learning framework data agent. Read workspace/learning/graph.yaml,
workspace/learning/mastery-state.json, and workspace/learning/session-context.json.

Compute and return a JSON object:
{
  "overdue_reviews": [ { "node_id": "...", "tier": "...", "days_overdue": N } ],
  "recent_teaches": [ { "node_id": "...", "timestamp": "..." } ],
  "frontier_nodes": [ { "node_id": "...", "unlock_count": N } ],
  "tier_summary": { "untested": N, "recognized": N, "understood": N, "mastered": N },
  "recommended_mode": "quiz_reviews | quiz_retests | teach",
  "recommendation_reason": "..."
}

Rules for recommended_mode:
- If overdue_reviews has 3+ entries: "quiz_reviews"
- Else if recent_teaches has entries from last 24h not yet quiz-tested: "quiz_retests"
- Else: "teach"
```

2. **Show the user a brief summary** (3-4 lines max):
   - Reviews due: N concepts overdue
   - Frontier: N concepts ready to learn
   - Tier breakdown: N untested / N recognized / N understood / N mastered
   - Mode: "Starting with [quiz reviews / quiz on recent concepts / teaching next concept]"

3. **Enter the recommended mode** — defer to the full `/quiz` or `/teach` skill behavior:
   - `quiz_reviews` → Run `/quiz` logic, targeting overdue review concepts
   - `quiz_retests` → Run `/quiz` logic, targeting concepts from session-context.json
   - `teach` → Run `/teach` Mode C (auto-select), then transition to quiz after 3-4 concepts

## Mid-Session Pivoting

Monitor user behavior and pivot between modes:

| User signal | Action |
|-------------|--------|
| "quiz me" / "test me" | Switch to `/quiz` mode targeting concepts covered so far this session |
| "teach me X" / "explain X" | Switch to `/teach` for concept X |
| "I don't understand X" | Switch to `/teach`, drop to prerequisites for X |
| "skip" / "next" | Stay in current mode, advance to next concept |
| "done" / "stopping" / "that's enough" | Trigger session exit (see below) |

**Automatic pivot (teach → quiz):** After teaching 3-4 concepts consecutively, suggest: "Want to lock these in? I'll quiz you on what we just covered." If the user agrees, switch to `/quiz` targeting session-context concepts.

**Automatic pivot (quiz → teach):** If the user fails 2+ concepts in a row at the same tier, suggest: "Looks like we need to build up [prerequisite]. Let me teach that first." Switch to `/teach` for the missing prerequisite.

## Session Exit

When the user signals "done":

1. **Dispatch an Opus 4.6 subagent** to compute session summary:

```
Prompt: You are a learning framework data agent. Read workspace/learning/mastery-state.json
and workspace/learning/session-context.json.

Compute this session's activity:
- List all concepts in session-context.json covered this session
- For each, compare current tier vs tier at session start (use last_tested dates to infer)
- Identify tier promotions and demotions
- Determine recommended next session focus

Return JSON:
{
  "concepts_covered": [ { "node_id": "...", "name": "...", "action": "taught|quizzed|reviewed" } ],
  "tier_changes": [ { "node_id": "...", "from": "...", "to": "..." } ],
  "next_session_recommendation": "...",
  "next_session_concept": "..."
}
```

2. **Display session summary** to the user:
   - Concepts covered: [list with actions]
   - Tier changes: concept_name: old_tier → new_tier (or "no tier changes" if none)
   - Next session: recommendation with specific concept suggestion

## Delegation Rules

This skill is an **orchestrator only**. It does NOT redefine quiz or teach behavior:

- **Quizzing behavior** (techniques, gap handling, tier promotion rules, spaced repetition): defer entirely to `skills/quiz.md`
- **Teaching behavior** (Feynman method, prerequisite verification, adaptive depth): defer entirely to `skills/teach.md`
- **Dashboard computation**: defer to `skills/learning-status.md` logic
- **State persistence**: all mastery-state.json updates follow `/quiz` conventions (subagent dispatch after every interaction)

## Session Context Reset

At session start, dispatch a subagent to timestamp the session start in `session-context.json` so the exit summary can distinguish this session's activity from previous ones.
