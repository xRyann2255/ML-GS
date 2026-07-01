# Research Memory Cards

Tiered summary cards distilled from `workspace/research/` source files. Each card is a 500-1500 token summary of key facts, formulas, and decisions — optimized for context-window loading.

## Tiered Structure

| Tier | Files | Purpose | Load Behavior |
|------|-------|---------|---------------|
| **P1** | 8 | Core project knowledge | Loaded when relevant tasks are active (feature engineering, data access, model design, evaluation, pipeline architecture) |
| **P2** | 9 | Specific feature/topic knowledge | Loaded on demand for specific feature layer work or literature reference |
| **P3** | 5 | Archive/history | Loaded only for research session starts or project history review |

## P1 — Load on Cue (~7,700 tokens total)

| Card | Topic |
|------|-------|
| optimal-feature-set.md | Complete 7-layer feature architecture with formulas and diminishing returns |
| data-access.md | Data sources, constraints, GS edge, feasibility matrix |
| project-design.md | Package architecture, interfaces, pooling decisions, model progression |
| evaluation-framework.md | QLIKE formula, DM/MCS tests, purged CV protocol, success targets |
| volatility.md | Landscape survey: estimators, HAR family, where ML wins, VRP |
| project-scope-and-data.md | Universe (35 instruments), targets, success criteria |
| feature-composition.md | Layers 5-7, diminishing returns table, horizon-dependent selection |
| complete-pipeline.md | End-to-end system diagram, implementation order, lookahead checklist |

## P2 — Load on Demand (~5,800 tokens total)

| Card | Topic |
|------|-------|
| har-components.md | HAR decomposition, long memory, ML horizon findings |
| jump-detection.md | BPV, BNS test, persistence, earnings triggers |
| leverage-effect.md | Semivariances, SHAR baseline, 3-8% QLIKE gain |
| microstructure.md | Optiver evidence, price acceleration, E-mini L2 features |
| cross-asset.md | DY spillover, GNN findings, available cross-asset data |
| implied-vol.md | VRP construction, Marquee features, horizon impact |
| calendar-events.md | FOMC, earnings, OpEx dummies, event-implied vol |
| bibliography.md | ~80 papers indexed by category with quality ratings |
| project-plan.md | Implementation chunks, YAML config, tech stack |

## P3 — Archive (~2,800 tokens total)

| Card | Topic |
|------|-------|
| open-questions.md | Exploration backlog: data, feature, methodology questions |
| research-journal.md | Session history: approach reset, Optiver deep dive |
| deep-research-decision-trees.md | Optimal trees, Rashomon sets, scaling frontiers |
| project-proposals.md | 4 project directions with recommendations |
| research-index.md | Provenance: what was extracted from where |

## Total Budget

- P1: ~7,700 tokens (within 50k CoALA budget for active-load tier)
- P2: ~5,800 tokens (loaded individually on demand)
- P3: ~2,800 tokens (rarely loaded)
- **Grand total: ~16,300 tokens**

## Source Files

All cards reference their source via the `source:` YAML frontmatter field, pointing to `workspace/research/<filename>`. The full source files contain complete details; cards contain the most decision-relevant distillation.
