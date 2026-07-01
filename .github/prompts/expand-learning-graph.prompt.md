---
description: "Add concepts, merge checklists, or add new feature layers to the learning dependency graph"
argument-hint: "mode: merge <filepath> | add \"<description>\" | layer <N>"
model: Claude Opus 4.6
---

You are in **expand-learning-graph mode**. Dispatch a subagent to read the graph, perform expansion with robust deduplication (exact ID, semantic similarity, subset, structural validation, coverage), and present proposed changes for user approval before writing.

- `skills/expand-learning-graph.md`
- `workspace/learning/graph.yaml`
- `workspace/learning/mastery-state.json`
