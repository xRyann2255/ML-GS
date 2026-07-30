# Memory Index

Organized by domain. See [meta/guide.md](meta/guide.md) for naming conventions.

**Priority:** P0 = always loaded at boot · P1 = loaded on demand per task type · P2 = loaded only on specific query · P3 = archive-tier reference

**Decision tree:** meta → person → research? `research/` → Python/data? `ref/` → Slang `.s`? `slang/`

**Dormant files:** 37 files in `memory/_dormant/` (Slang/SecDB/sys) — parked, not active. Skill-referenced dormant files carry P3 rows below (Status `dormant`) so `lint_broken_refs` sees a valid target; the rest sit outside the domain scan. Restore by moving them out of `_dormant/` and clearing the `status: dormant` tag. Lifecycle: [meta/guide.md](meta/guide.md) §Dormant files.

**Table format.** Header per domain: `File | Description | Priority | ~Tokens | Status | Updated | Load Trigger`. Every `~Tokens` cell is `round(bytes/4)` of the file it names — measured, not estimated. `Status` and `Updated` come from each file's frontmatter (`—` where the file has none, e.g. `trials.yaml`). Cross-tree rows (paths starting with `workspace/`, `src/`, `.github/`) resolve from repo root. Description column kept between File and Priority so `lint_memory_priority._INDEX_ROW` parses rows (Plan-04 regex expects a description column before the priority column).

---

## meta — Memory system

| File | Description | Priority | ~Tokens | Status | Updated | Load Trigger |
|------|-------------|----------|---------|--------|---------|--------------|
| [design.md](design.md) | Memory Design — structure & rules | P1 | 1167 | — | — | Writing/validating memory files |
| [meta/guide.md](meta/guide.md) | Memory System — Governance Guide | P1 | 1679 | active | 2026-04-16 | Writing/validating memory files |
| [meta/skill-usage.md](meta/skill-usage.md) | Skill Usage Tracking — log, aggregation, anti-patterns | P2 | 353 | active | 2026-04-24 | Skill usage questions |

## person — People

| File | Description | Priority | ~Tokens | Status | Updated | Load Trigger |
|------|-------------|----------|---------|--------|---------|--------------|
| [person/user.md](person/user.md) | The User (Profile) | P0 | 734 | active | 2026-07-29 | Always (boot) |

## research — ML Volatility Forecasting

**P1 — Load on cue** (`project-state.md` is boot-loaded via the AGENTS.md §Context Loading protocol; it sits at P1 to keep the P0 budget honest).

| File | Description | Priority | ~Tokens | Status | Updated | Load Trigger |
|------|-------------|----------|---------|--------|---------|--------------|
| [research/project-state.md](research/project-state.md) | Project State — milestone, QLIKE scorecard, blockers, next action | P1 | 1589 | active | 2026-07-29 | Boot per AGENTS.md §Context Loading (loaded first substantive step) |
| [research/optimal-feature-set.md](research/optimal-feature-set.md) | Optimal Feature Set — 7 layers, architecture, diminishing returns | P1 | 1635 | active | 2026-05-11 | Feature engineering, layer design |
| [research/data-access.md](research/data-access.md) | Data Access Inventory — sources, constraints, GS edge | P1 | 2855 | active | 2026-07-07 | Data queries, pipeline setup |
| [research/project-design.md](research/project-design.md) | Project Design — architecture, interfaces, pooling, package structure | P1 | 1144 | active | 2026-05-11 | Architecture decisions, package design |
| [research/evaluation-framework.md](research/evaluation-framework.md) | Evaluation Framework — QLIKE, DM, MCS, purged CV, walk-forward | P1 | 1294 | active | 2026-06-01 | Model evaluation, validation protocol |
| [research/volatility.md](research/volatility.md) | Volatility Landscape — estimators, baselines, ML methods, VRP | P1 | 822 | active | 2026-05-08 | Literature context, model selection |
| [research/project-scope-and-data.md](research/project-scope-and-data.md) | Project Scope — universe, targets, success criteria, data edge | P1 | 610 | active | 2026-05-07 | Project framing, data constraints |
| [research/feature-composition.md](research/feature-composition.md) | Feature Composition — L5-L7, diminishing returns, horizon priority | P1 | 722 | active | 2026-05-28 | Feature selection, horizon-specific work |
| [research/complete-pipeline.md](research/complete-pipeline.md) | Complete Pipeline — end-to-end system, implementation order | P1 | 724 | active | 2026-05-07 | Pipeline architecture, implementation planning |
| [research/qlike-defense.md](research/qlike-defense.md) | QLIKE Defense — why QLIKE over MSE, Patton 2011 proxy robustness | P1 | 2931 | active | 2026-05-19 | QLIKE rationale, loss function choice |
| workspace/research/feature-engineering-status.md | Feature Engineering Status — implemented, stubbed, test counts per layer | P1 | 2873 | — | — | Implementation status, layer status |
| workspace/docs/vol-project-ref/INDEX.md | Vol Project Reference Index — 18 chapters | P1 | 987 | — | — | Project spec, milestones, feature formulas |
| workspace/docs/vol-learning-guide/INDEX.md | Vol Learning Guide Index — 17 chapters of theory | P1 | 1248 | — | — | Equation derivation, theory |

**P2 — Load on demand:**

| File | Description | Priority | ~Tokens | Status | Updated | Load Trigger |
|------|-------------|----------|---------|--------|---------|--------------|
| [research/lgbm-pooled-lessons.md](research/lgbm-pooled-lessons.md) | LightGBM Pooled Lessons — per-symbol vs market-wide features, hyperparams | P2 | 9453 | active | 2026-06-01 | LightGBM tuning, pooled training, feature selection (demoted from P1 wfo-06-8: 9.5k t + reachability-orphaned) |
| [research/layer01-gap-analysis.md](research/layer01-gap-analysis.md) | Layer 0-1 Gap Analysis — PDF cross-reference, missing features | P2 | 3013 | archived | 2026-05-11 | historical only — gaps all implemented (banner :13) |
| [research/har-components.md](research/har-components.md) | HAR Components — decomposition, long memory, ML horizon findings | P2 | 448 | active | 2026-05-07 | HAR baseline work, Layer 0 |
| [research/jump-detection.md](research/jump-detection.md) | Jump Detection — BPV, BNS test, Lee-Mykland, persistence | P2 | 410 | active | 2026-05-07 | Layer 1 jumps, HAR-J/CJ |
| [research/leverage-effect.md](research/leverage-effect.md) | Leverage Effect — semivariances, SHAR, 3-8% QLIKE improvement | P2 | 458 | active | 2026-05-08 | Layer 1 asymmetry, SHAR baseline |
| [research/microstructure.md](research/microstructure.md) | Microstructure — Optiver evidence, E-mini L2 features | P2 | 493 | active | 2026-05-07 | Layer 3, E-mini work |
| [research/cross-asset.md](research/cross-asset.md) | Cross-Asset — DY spillover, GNN findings, treasury/FX/commodities | P2 | 526 | active | 2026-05-07 | Layer 4, spillover features |
| [research/implied-vol.md](research/implied-vol.md) | Implied Vol & VRP — construction, horizon impact, Marquee features | P2 | 3065 | active | 2026-07-07 | Layer 2, options features, VRP signal |
| [research/calendar-events.md](research/calendar-events.md) | Calendar Events — FOMC, earnings, OpEx, macro releases | P2 | 448 | active | 2026-05-07 | Layer 5, event features |
| [research/bibliography.md](research/bibliography.md) | Bibliography — ~80 papers, 11 categories | P2 | 654 | active | 2026-05-07 | Literature lookup, citation needs |
| workspace/research/research-journal.md | Research Journal — session log, findings, decisions (active file) | P2 | 14257 | — | — | Research continuity, session recovery, historical browse (repointed from memory pointer card wfo-06-8) |
| workspace/docs/data-audit.md | Data Audit — runnable query recipes for every feature layer | P2 | 9693 | — | — | Data queries, feature implementation (demoted from P1 wfo-06-8: 9.7k t; on-demand data recipe lookup) |
| workspace/docs/user-manual.md | User Manual — CLI reference, YAML config schema, tournament | P2 | 9031 | — | — | CLI commands, vol run, config, tournament (demoted from P1 wfo-06-8: 9.0k t; on-demand CLI reference) |
| workspace/research/trials.yaml | Experiment Trial Registry — structured log (append-only) | P3 | 37390 | — | — | /experiment loop, trial registry lookup (re-tiered from P1 wfo-06-8: 37k t; loaded on demand — sits at P3 to stay under P2 aggregate cap of 100k) |

**P3 — Archive:**

| File | Description | Priority | ~Tokens | Status | Updated | Load Trigger |
|------|-------------|----------|---------|--------|---------|--------------|
| [research/research-journal.md](research/research-journal.md) | Research Journal — pointer card to workspace/research/research-journal.md | P3 | 139 | active | 2026-07-29 | pointer only — active journal is workspace/research/research-journal.md |
| [research/deep-research-decision-trees.md](research/deep-research-decision-trees.md) | Decision Trees Survey — Rashomon sets, scaling | P3 | 538 | active | 2026-05-07 | Interpretability work |
| [research/research-index.md](research/research-index.md) | Research Index — provenance tracking | P3 | 476 | active | 2026-05-07 | Research audit, source tracing |
| [research/weekly-progress.md](research/weekly-progress.md) | Weekly Progress Log | P3 | 156 | active | 2026-05-08 | Progress log, weekly update |

## slang — Slang language & tooling (3 active files)

Policy-protected (referenced by `policy/preflight-gates.md`). 16 additional files in `memory/_dormant/slang/`.

| File | Description | Priority | ~Tokens | Status | Updated | Load Trigger |
|------|-------------|----------|---------|--------|---------|--------------|
| [slang/best-practices.md](slang/best-practices.md) | Best Practices — lambdas, structures, types, LintPragma | P1 | 3176 | active | 2026-04-30 | Slang .s file work |
| [slang/formatting.md](slang/formatting.md) | Formatting Rules — alignment, braces, multi-line | P1 | 2029 | active | 2026-04-30 | Slang .s file work |
| [slang/lint-edit.md](slang/lint-edit.md) | Lint & Edit — secexpr patterns, edit.py, overlays | P1 | 4070 | active | 2026-04-30 | Slang .s file work |

## ref — Technical reference (13 active files)

12 additional files in `memory/_dormant/ref/`.

| File | Description | Priority | ~Tokens | Status | Updated | Load Trigger |
|------|-------------|----------|---------|--------|---------|--------------|
| [ref/terminal-commands.md](ref/terminal-commands.md) | Terminal Commands — vol wrapper, project state | P1 | 1611 | active | 2026-05-19 | Terminal/CLI commands |
| [ref/vol-cli.md](ref/vol-cli.md) | vol CLI Reference — mirrors ./vol help | P1 | 2908 | active | 2026-07-27 | vol wrapper command lookup |
| [ref/devtools.md](ref/devtools.md) | devtools — GS developer tooling, PATH setup | P1 | 277 | active | 2026-05-19 | Environment/setup issues |
| [ref/python-setup.md](ref/python-setup.md) | Python Project Setup — uv, venv, dependencies | P1 | 1389 | active | 2026-05-19 | Python project setup |
| [ref/python-pyslang.md](ref/python-pyslang.md) | PySlang — imports, S3, boilerplate | P1 | 1807 | active | 2026-04-15 | Python + Slang data access |
| [ref/python-tsdb.md](ref/python-tsdb.md) | TSDB — TSDBSymbol + Slang wrappers, US-universe patterns | P1 | 1888 | active | 2026-07-29 | Python TSDB queries |
| [ref/python-tsdb-fields.md](ref/python-tsdb-fields.md) | TSDB Field Dictionary — full field/dataset lookup companion | P2 | 3386 | active | 2026-07-29 | TSDB field/dataset lookup |
| [ref/python-chunk.md](ref/python-chunk.md) | Chunk Store — tick data, L1/L2, America/New_York timezone | P1 | 1927 | active | 2026-07-29 | Python tick/intraday data |
| [ref/git-workflow.md](ref/git-workflow.md) | Git Workflow — ml-vol-estimator repo conventions | P1 | 1528 | active | 2026-04-09 | Git/MR work |
| [ref/vscode-tasks.md](ref/vscode-tasks.md) | VS Code Task Policy — definitions, wrappers, execution rules | P1 | 1936 | active | 2026-04-29 | VS Code task work |
| [ref/skill-routing.md](ref/skill-routing.md) | Skill Routing — discovery rule, hostname mapping | P1 | 544 | active | 2026-04-24 | Host lookup, skill discovery |
| [ref/skill-scripts.md](ref/skill-scripts.md) | Skill Script Conventions | P1 | 614 | active | 2026-04-30 | Building skill scripts |
| [ref/skill-authoring.md](ref/skill-authoring.md) | SKILL.md Authoring — frontmatter, link validation | P2 | 496 | active | 2026-04-22 | Creating/editing SKILL.md files |

## learning — Vol Learning Framework

| File | Description | Priority | ~Tokens | Status | Updated | Load Trigger |
|------|-------------|----------|---------|--------|---------|--------------|
| workspace/learning/graph.yaml | Volatility concept dependency graph (28+ nodes) | P3 | 47891 | — | — | /study, /quiz, /teach, /learning-status, /expand-learning-graph — 48k t; sits at P3 to stay under P2 aggregate cap of 100k |
| workspace/learning/mastery-state.json | Per-concept mastery tier, spaced repetition schedule | P2 | 5292 | — | — | /study, /quiz, /teach, /learning-status |
| workspace/learning/vol-learning-framework-design.md | Learning framework design spec | P2 | 16740 | — | — | Learning framework design questions (path repointed wfo-06-8: was workspace/docs/, actual location is workspace/learning/) |

## _dormant — Skill-referenced dormant files

Skill-referenced dormant files (see [meta/guide.md](meta/guide.md) §Dormant files). Not loaded by domain scans; skills that reference them do so lazily. Listed here so `lint_broken_refs` sees a valid target for the dormant path.

| File | Description | Priority | ~Tokens | Status | Updated | Load Trigger |
|------|-------------|----------|---------|--------|---------|--------------|
| _dormant/ref/confluence-auth.md | Confluence auth notes (dormant) | P3 | 945 | dormant | 2026-04-14 | Skill ref — CONFLUENCE auth notes |
| _dormant/ref/forward-network.md | Forward Network reference (dormant) | P3 | 1895 | dormant | 2026-04-22 | Skill ref — FORWARD_NETWORK |
| _dormant/ref/gssso-auth.md | GSSSO auth reference (dormant) | P3 | 805 | dormant | 2026-03-04 | Skill ref — GSSSO_AUTH |
| _dormant/ref/secdb-position-pnl.md | SecDB position PnL reference (dormant) | P3 | 2220 | dormant | 2026-04-15 | Skill ref — SECDB_POSITION |
| _dormant/ref/secdb-trade-model.md | SecDB trade model reference (dormant) | P3 | 1365 | dormant | 2026-04-14 | Skill ref — SECDB_TRANSLOG trade model |
| _dormant/ref/secdb-ufo-diddles.md | SecDB UFO diddles reference (dormant) | P3 | 2010 | dormant | 2026-04-14 | Skill ref — SECDB UFO diddles |
| _dormant/ref/slop-smells.md | AI slop smells reference (dormant) | P3 | 1735 | dormant | 2026-04-14 | Skill ref — AI_SLOP_CLEANER |
| _dormant/ref/symphony-bot-framework.md | Symphony bot framework reference (dormant) | P3 | 722 | dormant | 2026-04-14 | Skill ref — SYMPHONY bot framework |
| _dormant/slang/glimpse-reference.md | Slang glimpse reference (dormant) | P3 | 858 | dormant | 2026-05-12 | Skill ref — SLANG_GLIMPSE |
| _dormant/slang/headers.md | Slang headers reference (dormant) | P3 | 1093 | dormant | 2026-04-15 | Skill ref — Slang headers |
| _dormant/slang/language.md | Slang language guide (dormant) | P3 | 3678 | dormant | 2026-04-16 | Skill ref — Slang language guide |
| _dormant/slang/regtest.md | Slang regtest reference (dormant) | P3 | 5523 | dormant | 2026-04-30 | Skill ref — SLANG_REGTEST_FIX |
| _dormant/slang/research.md | Slang research notes (dormant) | P3 | 888 | dormant | 2026-04-16 | Skill ref — Slang research |
| _dormant/slang/review-api.md | Slang review API reference (dormant) | P3 | 1048 | dormant | 2026-05-12 | Skill ref — SLANG_REVIEW API |
| _dormant/slang/review.md | Slang review reference (dormant) | P3 | 1288 | dormant | 2026-04-20 | Skill ref — SLANG_REVIEW |
| _dormant/slang/run.md | Slang run reference (dormant) | P3 | 603 | dormant | 2026-04-14 | Skill ref — Slang run |
| _dormant/slang/secexpr-gotchas.md | Slang secexpr gotchas reference (dormant) | P3 | 1525 | dormant | 2026-04-17 | Skill ref — Slang secexpr gotchas |
| _dormant/slang/utility-libs.md | Slang utility libs reference (dormant) | P3 | 690 | dormant | 2026-04-15 | Skill ref — Slang utility libs |
| _dormant/sys/canvas-appdir.md | Canvas appdir reference (dormant) | P3 | 632 | dormant | 2026-04-14 | Skill ref — CANVAS appdir |
| _dormant/sys/enghub-repos.md | Enghub repos reference (dormant) | P3 | 1350 | dormant | 2026-04-14 | Skill ref — ENGHUB repos |
| _dormant/sys/etask.md | ETASK reference (dormant) | P3 | 3086 | dormant | 2026-04-16 | Skill ref — ETASK |
