# Memory Index

Organized by domain. See [meta/guide.md](meta/guide.md) for naming conventions.

**Priority:** P0 = always loaded at boot · P1 = loaded on demand per task type · P2 = loaded only on specific query · P3 = archive-tier reference

**Decision tree:** meta → person → research? `research/` → Python/data? `ref/` → Slang `.s`? `slang/`

**Dormant files:** 37 files in `memory/_dormant/` (Slang/SecDB/sys). Restore if Slang work resumes.

---

## meta — Memory system

| File | Description | Pri | ~Tokens | Load Trigger |
|------|-------------|-----|---------|--------------|
| [design.md](design.md) | Memory Design — structure & rules | P1 | 890 | Writing/validating memory files |
| [meta/guide.md](meta/guide.md) | Memory System — Governance Guide | P1 | 1020 | Writing/validating memory files |
| [meta/skill-usage.md](meta/skill-usage.md) | Skill Usage Tracking — log, aggregation, anti-patterns | P2 | 255 | Skill usage questions |

## person — People

| File | Description | Pri | ~Tokens | Load Trigger |
|------|-------------|-----|---------|--------------|
| [person/user.md](person/user.md) | The User (Profile) | P0 | 280 | Always (boot) |

## research — ML Volatility Forecasting

**P0 — Always loaded at boot:**

| File | Description | Pri | ~Tokens | Load Trigger |
|------|-------------|-----|---------|--------------|
| [research/project-state.md](research/project-state.md) | Project State — milestone, QLIKE scorecard, blockers, next action | P0 | 255 | Always (boot) |

**P1 — Load on cue:**

| File | Description | Pri | ~Tokens | Load Trigger |
|------|-------------|-----|---------|--------------|
| [research/research-journal.md](research/research-journal.md) | Research Journal — session log, findings, decisions | P1 | 1290 | Research session start, continuity |
| [research/optimal-feature-set.md](research/optimal-feature-set.md) | Optimal Feature Set — 7 layers, architecture, diminishing returns | P1 | 1240 | Feature engineering, layer design |
| [research/data-access.md](research/data-access.md) | Data Access Inventory — sources, constraints, GS edge | P1 | 1630 | Data queries, pipeline setup |
| [research/project-design.md](research/project-design.md) | Project Design — architecture, interfaces, pooling, package structure | P1 | 810 | Architecture decisions, package design |
| [research/evaluation-framework.md](research/evaluation-framework.md) | Evaluation Framework — QLIKE, DM, MCS, purged CV, walk-forward | P1 | 700 | Model evaluation, validation protocol |
| [research/volatility.md](research/volatility.md) | Volatility Landscape — estimators, baselines, ML methods, VRP | P1 | 580 | Literature context, model selection |
| [research/project-scope-and-data.md](research/project-scope-and-data.md) | Project Scope — universe, targets, success criteria, data edge | P1 | 510 | Project framing, data constraints |
| [research/feature-composition.md](research/feature-composition.md) | Feature Composition — L5-L7, diminishing returns, horizon priority | P1 | 520 | Feature selection, horizon-specific work |
| [research/complete-pipeline.md](research/complete-pipeline.md) | Complete Pipeline — end-to-end system, implementation order | P1 | 485 | Pipeline architecture, implementation planning |
| [research/lgbm-pooled-lessons.md](research/lgbm-pooled-lessons.md) | LightGBM Pooled Lessons — per-symbol vs market-wide features, hyperparams | P1 | 890 | LightGBM tuning, pooled training, feature selection |
| [research/qlike-defense.md](research/qlike-defense.md) | QLIKE Defense — why QLIKE over MSE, Patton 2011 proxy robustness | P1 | 2490 | QLIKE rationale, loss function choice |
| workspace/research/feature-engineering-status.md | Feature Engineering Status — implemented, stubbed, test counts per layer | P1 | 1980 | Implementation status, layer status |
| workspace/docs/vol-project-ref/INDEX.md | Vol Project Reference Index — 18 chapters | P1 | 720 | Project spec, milestones, feature formulas |
| workspace/docs/vol-learning-guide/INDEX.md | Vol Learning Guide Index — 17 chapters of theory | P1 | 730 | Equation derivation, theory |
| workspace/docs/data-audit.md | Data Audit — runnable query recipes for every feature layer | P1 | 7350 | Data queries, feature implementation |
| workspace/docs/user-manual.md | User Manual — CLI reference, YAML config schema, tournament | P1 | 5420 | CLI commands, vol run, config, tournament |

**P2 — Load on demand:**

| File | Description | Pri | ~Tokens | Load Trigger |
|------|-------------|-----|---------|--------------|
| [research/layer01-gap-analysis.md](research/layer01-gap-analysis.md) | Layer 0-1 Gap Analysis — PDF cross-reference, missing features | P2 | 2250 | Layer 0-1 implementation, feature gaps |
| [research/har-components.md](research/har-components.md) | HAR Components — decomposition, long memory, ML horizon findings | P2 | 325 | HAR baseline work, Layer 0 |
| [research/jump-detection.md](research/jump-detection.md) | Jump Detection — BPV, BNS test, Lee-Mykland, persistence | P2 | 295 | Layer 1 jumps, HAR-J/CJ |
| [research/leverage-effect.md](research/leverage-effect.md) | Leverage Effect — semivariances, SHAR, 3-8% QLIKE improvement | P2 | 350 | Layer 1 asymmetry, SHAR baseline |
| [research/microstructure.md](research/microstructure.md) | Microstructure — Optiver evidence, E-mini L2 features | P2 | 350 | Layer 3, E-mini work |
| [research/cross-asset.md](research/cross-asset.md) | Cross-Asset — DY spillover, GNN findings, treasury/FX/commodities | P2 | 385 | Layer 4, spillover features |
| [research/implied-vol.md](research/implied-vol.md) | Implied Vol & VRP — construction, horizon impact, Marquee features | P2 | 1120 | Layer 2, options features, VRP signal |
| [research/calendar-events.md](research/calendar-events.md) | Calendar Events — FOMC, earnings, OpEx, macro releases | P2 | 350 | Layer 5, event features |
| [research/bibliography.md](research/bibliography.md) | Bibliography — ~80 papers, 11 categories | P2 | 490 | Literature lookup, citation needs |
| workspace/docs/architecture-audit.md | Architecture Audit — package structure, modularity | P2 | 2810 | Architecture, refactoring |

**P3 — Archive:**

| File | Description | Pri | ~Tokens | Load Trigger |
|------|-------------|-----|---------|--------------|
| [research/deep-research-decision-trees.md](research/deep-research-decision-trees.md) | Decision Trees Survey — Rashomon sets, scaling | P3 | 385 | Interpretability work |
| [research/research-index.md](research/research-index.md) | Research Index — provenance tracking | P3 | 305 | Research audit, source tracing |
| [research/weekly-progress.md](research/weekly-progress.md) | Weekly Progress Log | P3 | 100 | Progress log, weekly update |

## slang — Slang language & tooling (3 active files)

Policy-protected (referenced by `policy/preflight-gates.md`). 16 additional files in `memory/_dormant/slang/`.

| File | Description | Pri | ~Tokens | Load Trigger |
|------|-------------|-----|---------|--------------|
| [slang/best-practices.md](slang/best-practices.md) | Best Practices — lambdas, structures, types, LintPragma | P1 | 2515 | Slang .s file work |
| [slang/formatting.md](slang/formatting.md) | Formatting Rules — alignment, braces, multi-line | P1 | 1550 | Slang .s file work |
| [slang/lint-edit.md](slang/lint-edit.md) | Lint & Edit — secexpr patterns, edit.py, overlays | P1 | 3240 | Slang .s file work |

## ref — Technical reference (11 active files)

12 additional files in `memory/_dormant/ref/`.

| File | Description | Pri | ~Tokens | Load Trigger |
|------|-------------|-----|---------|--------------|
| [ref/terminal-commands.md](ref/terminal-commands.md) | Terminal Commands — vol wrapper, project state | P1 | 1130 | Terminal/CLI commands |
| [ref/vol-cli.md](ref/vol-cli.md) | vol CLI Reference — mirrors `./vol help` | P1 | 540 | vol wrapper command lookup |
| [ref/devtools.md](ref/devtools.md) | devtools — GS developer tooling, PATH setup | P1 | 210 | Environment/setup issues |
| [ref/python-setup.md](ref/python-setup.md) | Python Project Setup — uv, venv, dependencies | P1 | 990 | Python project setup |
| [ref/python-pyslang.md](ref/python-pyslang.md) | PySlang — imports, S3, boilerplate | P1 | 990 | Python + Slang data access |
| [ref/python-tsdb.md](ref/python-tsdb.md) | TSDB — daily/RT wrappers, TSDBSymbol, field dictionary | P1 | 4130 | Python TSDB queries |
| [ref/python-chunk.md](ref/python-chunk.md) | Chunk Store — tick data, L1/L2, timezone handling | P1 | 1825 | Python tick/intraday data |
| [ref/git-workflow.md](ref/git-workflow.md) | Git Workflow — ml-vol-estimator repo conventions | P1 | 1120 | Git/MR work |
| [ref/vscode-tasks.md](ref/vscode-tasks.md) | VS Code Task Policy — definitions, wrappers, execution rules | P1 | 1385 | VS Code task work |
| [ref/skill-routing.md](ref/skill-routing.md) | Skill Routing — discovery rule, hostname mapping | P1 | 390 | Host lookup, skill discovery |
| [ref/skill-scripts.md](ref/skill-scripts.md) | Skill Script Conventions | P1 | 450 | Building skill scripts |
| [ref/skill-authoring.md](ref/skill-authoring.md) | SKILL.md Authoring — frontmatter, link validation | P2 | 370 | Creating/editing SKILL.md files |

## learning — Vol Learning Framework

| File | Description | Pri | ~Tokens | Load Trigger |
|------|-------------|-----|---------|--------------|
| workspace/learning/graph.yaml | Volatility concept dependency graph (28+ nodes) | P2 | 26530 | /study, /quiz, /teach, /learning-status, /expand-learning-graph |
| workspace/learning/mastery-state.json | Per-concept mastery tier, spaced repetition schedule | P2 | 1585 | /study, /quiz, /teach, /learning-status |
| workspace/docs/vol-learning-framework-design.md | Learning framework design spec | P2 | 12570 | Learning framework design questions |

## workspace — Experiment Registry

| File | Description | Pri | ~Tokens | Load Trigger |
|------|-------------|-----|---------|--------------|
| workspace/research/trials.yaml | Experiment Trial Registry — structured log (append-only) | P1 | varies | /bootup (last 5 + NOT_STARTED), /experiment |
