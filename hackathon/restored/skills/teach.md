---
name: teach
description: "Teaching mode for vol-learning-guide concepts. USE FOR: guided explanation of specific concepts, thread-based teaching through concept chains, auto-selected next-concept teaching, prerequisite verification and remediation. DO NOT USE FOR: testing mastery (use quiz), checking progress (use learning-status), expanding the graph (use expand-learning-graph)."
---

# /teach — Teaching Mode

> **Purpose:** Guided teaching of volatility concepts from the learning graph. Explains intuitively (Feynman method), verifies prerequisites before advancing, adapts depth to the user's understanding, and hands off to `/quiz` for mastery locking.

## Data Files

| File | Purpose | Access |
|------|---------|--------|
| `workspace/learning/graph.yaml` | Dependency graph (nodes, edges, key_points, misconceptions) | Read |
| `workspace/learning/mastery-state.json` | Per-node tier, next_review, consecutive_passes | Read |
| `workspace/learning/session-context.json` | Concepts covered this session (for /quiz handoff) | Write (via subagent) |

## Invocation Modes

### Mode A: `/teach bpv` — Teach Specific Concept

Match the argument against node IDs and node names in `workspace/learning/graph.yaml`. Teach that specific concept.

### Mode B: `/teach jumps` — Teach a Concept Thread

Match the argument, then follow `connects_to` and `requires` edges to teach a natural sequence through related concepts (e.g., "jumps" follows the jump decomposition branch: jumps_vs_diffusion -> bpv_jump_robustness -> jump_component -> har_cj_model).

### Mode C: `/teach` (no argument) — Auto-Select Next Concept

Dispatch an **Opus 4.6** subagent to determine the highest-impact next concept:

```
Prompt: You are a learning framework data agent. Read workspace/learning/graph.yaml
and workspace/learning/mastery-state.json.

Determine the next concept to teach using this logic:
1. If there are "recognized" concepts with all prerequisites "understood":
   pick the one with the most downstream dependents (highest unlock impact)
2. If all frontier nodes are "untested": start from the deepest foundations
   (root nodes: log_returns, variance_as_spread, annualizing_vol, etc.)
3. If there are stale "understood" concepts overdue for review (next_review < today):
   suggest those first with a brief refresher before teaching new material

Return ONLY a JSON object:
{
  "node_id": "...",
  "name": "...",
  "layer": N,
  "tier": "current tier",
  "key_points": [...],
  "misconceptions": [...],
  "why_it_matters": "...",
  "requires": [...],
  "connects_to": [...],
  "selection_reason": "highest_impact_frontier | root_foundation | stale_review",
  "prerequisite_status": { "node_id": "tier", ... }
}
```

## Teaching Approach

1. **Prerequisites first:** Before teaching concept X, verify its `requires` are solid. Quick check: "Can you tell me in one sentence why [prerequisite concept]?" If the user can't, drop to that prerequisite first.

2. **Plain English -> Formula -> Project Connection:**
   - Start with intuitive explanation using `key_points` and `why_it_matters`
   - Separate each chunk with a horizontal rule (`---`) so the user can focus on one thing at a time: intuition block, then `---`, formula block, then `---`, project connection block
   - Introduce the formula only as confirmation of the intuition
   - Connect to the ML vol forecasting project: "In our pipeline, this means..."

3. **Analogies:** Use real-world analogies. Let the user generate their own when possible — self-generated analogies stick better.

4. **PDF cross-reference (after content):** After finishing your intuitive explanation of each section, append a brief reference line pointing to the corresponding chapter and section number in `workspace/docs/vol-learning-guide/` so the user can follow along in the PDF. Format: `📖 *Vol Learning Guide — Ch.X, §X.Y: "Section Title"*`. This comes AFTER your teaching — never let the PDF structure dictate your explanation order or framing.

5. **Lightweight check after each concept:** "Before we move on, explain back to me why [specific key point from the node]." This is not a full quiz — just a comprehension gate.

6. **Tier update:** After engagement (even just active listening + passing a lightweight check), update concept to at least "recognized."

## Adaptive Depth

**When the user struggles:**
- If the user says "I don't understand X" or fails a lightweight check, immediately drop to the relevant prerequisite
- Follow `requires` edges downward until you find solid ground (a concept the user can explain)
- Then build back up toward the original concept

**When the user is breezing:**
- Skip lightweight checks — move faster through the thread
- Offer deeper connections: "Want to see how this connects to [advanced concept]?"

## Session Context Tracking

After each concept is covered, dispatch an **Opus 4.6** subagent to update session context:

```
Prompt: You are a learning framework data agent. Read workspace/learning/session-context.json.
Add the following concept to the "covered" list:
- node_id: "[node_id]"
- name: "[name]"
- timestamp: "[ISO datetime]"
- depth: "taught | refreshed | prerequisite_check"

Write the updated JSON back to workspace/learning/session-context.json.
Return a one-line confirmation.
```

## Quiz Handoff

At natural stopping points (end of a thread, user signals done, or after 4-5 concepts), present:

> "We covered [N] concepts: [list with names]. Want to lock them in? Run `/quiz` and I'll focus on what we just studied."

The session context in `workspace/learning/session-context.json` ensures `/quiz` prioritizes these concepts as mid-session retests.

## Session Flow

1. Determine mode (specific concept, thread, or auto-select)
2. If auto-select: dispatch subagent to find next concept
3. Verify prerequisites are solid (quick check)
4. If prerequisite gap: adaptive depth — drop down, build back up
5. Teach concept: plain English -> formula -> project connection
6. Lightweight check
7. Dispatch subagent to update session-context.json
8. Continue to next concept in thread, or present quiz handoff

## Interruption Handling

Session can be stopped at any point. The session-context.json is updated after each concept, so `/quiz` always knows what was covered. Next `/teach` session starts fresh or continues a thread.
