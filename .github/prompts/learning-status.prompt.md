---
description: "Dashboard of mastery progress across feature layers, review queue, and study recommendations"
model: Claude Opus 4.6
---

You are in **learning-status mode**.

1. First, run `python3 workspace/learning/generate_dashboard.py` to regenerate the interactive HTML dashboard.
2. Then dispatch a single subagent to compute the text summary (per-layer progress, due-today queue, frontier nodes, stale alerts, recommendation) and display it.
3. After the text summary, tell the user: **Interactive dashboard:** `workspace/learning/dashboard.html` (open in browser)

- `skills/learning-status.md`
- `workspace/learning/graph.yaml`
- `workspace/learning/mastery-state.json`
