---
name: learning-status
description: "Dashboard view of vol-learning mastery progress. USE FOR: checking overall progress, seeing due reviews, identifying frontier nodes, spotting stale concepts, getting recommendations. DO NOT USE FOR: quizzing (use quiz), teaching (use learn), setting goals (use weekly-learning-goals)."
---

# /learning-status — Mastery Dashboard

> **Purpose:** Display a comprehensive dashboard of learning progress across all layers. Shows per-layer completion, review queues, frontier nodes, stale alerts, and actionable recommendations. All computation is done by a subagent to keep the main context clean.

## Data Files

| File | Purpose | Access |
|------|---------|--------|
| `workspace/learning/graph.yaml` | Dependency graph (nodes, edges, layers) | Read (via subagent) |
| `workspace/learning/mastery-state.json` | Per-node tier, next_review, consecutive_passes | Read (via subagent) |

## Implementation

Run the Python dashboard generator with `--text` to produce the markdown status. This is a single script invocation (~<1s) that replaces the previous subagent approach.

### Execution

```bash
python3 workspace/learning/generate_dashboard.py --text
```

This reads `workspace/learning/graph.yaml` and `workspace/learning/mastery-state.json`, computes all metrics, and prints the formatted markdown dashboard to stdout.

The script also regenerates the interactive HTML dashboard (without `--text`):
```bash
python3 workspace/learning/generate_dashboard.py
```

### Output Sections (computed by the script)

1. **PER-LAYER PROGRESS BARS** — Block-character bars with X/Y (Z%) per layer
2. **DUE TODAY** — Nodes where next_review <= today
3. **DUE THIS WEEK** — Nodes where next_review is within 7 days (excluding today)
4. **FRONTIER NODES** — Untested/recognized nodes whose ALL prerequisites are >= understood, sorted by downstream impact
5. **STALE ALERTS** — Understood nodes not reviewed in 14+ days
6. **RECOMMENDATION** — One actionable sentence based on due reviews and frontier availability

## Output Format

The main agent displays the subagent's return verbatim. Example output:

```
## Learning Dashboard

### Per-Layer Progress
Layer 0 (HAR Core):     ████████████░░░  12/15 mastered (80%)
Layer 1 (Noise+Asym):   ████░░░░░░░░░░░   4/13 understood (31%)
Layer 2 (Options):      not yet added

### Due Today
- "Why RV is a noisy estimate" (understood, last tested 3hrs ago)

### Due This Week
- "HAR approximates long memory" (understood, review in 2 days)
- "Signature plot interpretation" (recognized, review tomorrow)

### Frontier Nodes (ready to learn)
1. bpv_jump_robustness — "Why bipower variation ignores jumps" (recognized, unlocks 4 nodes, Layer 1)
2. semivariances — "Measuring downside vs upside vol separately" (untested, unlocks 3 nodes, Layer 1)

### Stale Alerts
- "Vol clustering" — understood but not reviewed in 18 days

### Recommendation
You have 1 review due today and 2 frontier nodes ready. Start with /quiz to lock in your review, then /teach bpv_jump_robustness.
```

## Session Flow

1. User invokes `/learning-status`
2. Run: `python3 workspace/learning/generate_dashboard.py --text` — capture stdout
3. Run: `python3 workspace/learning/generate_dashboard.py` — regenerates HTML dashboard
4. Display the text output verbatim
5. Append: "Interactive dashboard: `workspace/learning/dashboard.html` (open in browser)"
6. No follow-up actions unless user asks
