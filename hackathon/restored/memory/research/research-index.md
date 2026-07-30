---
created: 2026-05-07
updated: 2026-05-07
tags: [index, research-outputs, extractions, provenance]
status: active
priority: P3
source: workspace/research/research-index.md (archived)
relates: [bibliography, research-journal, deep-research-decision-trees]
---

# Research Index — Summary

Tracks deep research outputs: what was run, extracted, and where it lives.

## 2026-05-06: ML for Realized Volatility Forecasting

- **Raw output:** landscape survey (~80 papers)
- **Extracted to:**
  - bibliography.md: ~80 entries, 11 categories (A-K)
  - project-proposals.md: 4 directions, recommendations, decision benchmarks
  - Feature notes: har-components, implied-vol, microstructure, cross-asset, leverage-effect, jump-detection, optimal-feature-set, calendar-events

## 2026-05-07: State of the Art in Decision Trees

- **Raw output:** optimal trees + Rashomon sets landscape
- **Extracted to:**
  - bibliography.md: ~50 new entries (category H), 12 enriched, 8 new tags
  - project-proposals.md: methodology assessment, implementation roadmap, 10 caveats
  - optimal-feature-set.md: Rashomon pipeline design, feature interchangeability
  - har-components.md: accuracy comparison (optimal trees vs HAR vs LightGBM)

## Coverage Map

| Topic | Primary Card | Backup |
|-------|-------------|--------|
| RV estimation & HAR | volatility.md, har-components.md | bibliography.md (cat A, B) |
| Feature layers 0-6 | optimal-feature-set.md, feature-composition.md | Per-layer cards |
| Evaluation | evaluation-framework.md | bibliography.md (cat G) |
| Data access | data-access.md, project-scope-and-data.md | — |
| Architecture | project-design.md, complete-pipeline.md | project-plan.md |
| ML methods | volatility.md (C.1-C.11) | bibliography.md (cat D, E) |
| Rashomon/trees | deep-research-decision-trees.md | bibliography.md (cat H) |
| Project direction | project-proposals.md | project-design.md |
