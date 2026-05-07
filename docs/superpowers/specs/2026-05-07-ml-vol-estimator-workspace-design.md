# Design Spec: Transform eq-latam-ai into ml-vol-estimator

**Date:** 2026-05-07
**Author:** Ryan Vincent
**Status:** Active

---

## 1. Problem Statement

Ryan has an agentic workflow (`eq-latam-ai`) on his GS work machine that teaches GitHub Copilot how to interact with internal systems via a 5-primitive framework: Personas, Skills, Memory (CoALA), Workflows, and Policies. He is pivoting from LatAm equities work to an ML realized volatility forecasting internship project (~20 weeks, May-Sep 2026).

**Goal:** Transform eq-latam-ai into ml-vol-estimator -- strip all LatAm/Slang/desk-specific content, adapt the framework for ML vol forecasting, import research materials from the personal-machine repo, and scaffold the Python ML pipeline.

**Constraints:**
- Work machine has GitHub Copilot (agent mode), not Claude Code
- Files can be sent TO work machine but not FROM it
- Complete pivot: eq-latam-ai gets fully replaced, no LatAm desk-specific content retained
- Fork-and-strip approach: preserve framework infrastructure, gut desk-specific content
- Slang/SecDB content explicitly preserved: these are GS infrastructure tools needed for data access
- Interactive removal: Copilot recommends what to remove, user approves each item

---

## 2. Deliverables

### 2.1 `work-init` Branch

A branch in the personal-machine ML repo containing everything needed to bootstrap the transformation. Transferred manually to the work machine.

```
work-init branch (root)
├── README.md                              # Quick-start: what this is, file placement steps
├── COPILOT_TRANSFORMATION_GUIDE.md        # 22-prompt sequential guide (core deliverable)
│
├── research/                              # Raw research files --> workspace/docs/research/
│   ├── optimal-feature-set.md             # 7-layer feature synthesis (303 lines)
│   ├── data-access.md                     # Binding data constraints (62 lines)
│   ├── research-journal.md                # Session findings log (117 lines)
│   ├── open-questions.md                  # Investigation queue (32 lines)
│   ├── project-design.md                  # Technical architecture spec (559 lines)
│   ├── project-plan.md                    # Implementation roadmap (2,046 lines)
│   ├── volatility.md                      # Foundational pedagogy + lit survey (788 lines)
│   ├── project-proposals.md               # Decision context for project direction (166 lines)
│   ├── bibliography.md                    # Master annotated bibliography (1,665 lines)
│   ├── deep-research-decision-trees.md    # Rashomon set analysis -- novel contribution (227 lines)
│   ├── research-index.md                  # Navigation index for all research (29 lines)
│   ├── har-components.md                  # HAR feature notes (36 lines)
│   ├── jump-detection.md                  # Jump decomposition notes
│   ├── leverage-effect.md                 # Asymmetry notes
│   ├── microstructure.md                  # LOB/microstructure notes
│   ├── cross-asset.md                     # Spillover notes
│   ├── implied-vol.md                     # Options-implied notes
│   └── calendar-events.md                 # Event structure notes
│
├── reference-extracts/                    # Key vol-project-ref chapters as markdown
│   ├── project-scope-and-data.md          # Ch01 + Ch02 combined
│   ├── feature-composition.md             # Ch08 -- how feature layers compose
│   ├── evaluation-framework.md            # Ch13 -- QLIKE, DM, MCS methodology
│   └── complete-pipeline.md               # Ch14 -- end-to-end architecture
│
└── guides/
    ├── vol-project-ref/
    │   └── main.pdf                       # Compiled project reference (500KB, 14 chapters)
    └── vol-learning-guide/
        └── main.pdf                       # Compiled learning guide (2.2MB, 17 chapters)
```

**Transfer size:** ~5MB total

### 2.2 Copilot Transformation Guide

A single markdown document with 22 sequential prompts organized into 4 grouped sessions (6+6+6+4). Each prompt is designed for GitHub Copilot agent mode (can autonomously create/edit/delete files). Includes dedicated verification prompts after every critical step and session handoff summaries between sessions.

---

## 3. File Placement on Work Machine

Before running any prompts, the user manually copies transferred files:

| Source (from branch) | Destination (in eq-latam-ai) |
|---|---|
| `research/*` | `workspace/docs/research/` |
| `reference-extracts/*` | `workspace/docs/research/` |
| `guides/vol-project-ref/main.pdf` | `workspace/docs/vol-project-ref.pdf` |
| `guides/vol-learning-guide/main.pdf` | `workspace/docs/vol-learning-guide.pdf` |
| `COPILOT_TRANSFORMATION_GUIDE.md` | Keep open as reference |

---

## 4. Prompt Architecture

**Approach:** Phase-based with full verification. 22 prompts across 4 grouped Copilot sessions. Each session is a new Copilot chat (no memory of prior sessions), but files on disk persist between sessions. Prompts within a session build on previous context. Each session ends with a handoff summary that documents what changed and preps context for the next session. Critical steps get dedicated verification prompts. All prompts include explicit file paths so Copilot can find resources without relying on prior conversation context.

### Session 1: Audit, Strip, Rename (Prompts 1-6)

**Goal:** Remove LatAm desk-specific content and rebrand. Slang and SecDB content is explicitly KEPT -- it is useful for querying GS internal data systems.

**Prompt 1 -- Full Audit Across All Primitives**

Copilot reads INDEX files for all primitives (skills/INDEX.md, memory/INDEX.md, personas/INDEX.md, workflows/INDEX.md, policy/index.md, .github/prompts/ directory listing). For each file, classifies as KEEP (generic infrastructure), ADAPT (useful but needs domain changes), or REMOVE (LatAm desk-specific only). Copilot classifies independently based on reading each file -- no expected-classification hints. The prompt provides project context (ML vol forecasting) so Copilot can make informed decisions.

**IMPORTANT: The following are explicitly protected from removal (classify as KEEP or ADAPT, never REMOVE):**
- All `skills/SLANG_*` directories (Slang is GS's internal query language for SecDB)
- All `skills/SECDB_*` directories (SecDB data access tools)
- All `memory/slang/*` files (Slang best practices, syntax, built-in functions, etc.)
- All `memory/ref/secdb-*.md` files (SecDB graph, position, trade model, UFO/diddles)
- All `memory/ref/python-*.md` files (Python data access: Chunk Store, pyslang, TSDB, setup)
- `.github/instructions/slang.instructions.md`
- `.github/prompts/slang*.prompt.md` files
- Any persona, workflow, or policy that references Slang/SecDB tooling

**Rationale:** Even though the project is pivoting to ML vol forecasting, SecDB is GS's core data platform. Slang skills are needed to query tick data, positions, and pricing models. The SecDB memory files teach Copilot how to navigate the data graph. These are infrastructure, not desk-specific.

Output: consolidated table across all primitives for user review.

**Prompt 2 -- Execute Approved Removals**

Takes the user-approved removal list. Copilot:
1. Deletes all REMOVE files/directories
2. Updates every INDEX.md to remove deleted entries
3. Removes corresponding .github/prompts/*.prompt.md files
4. Removes corresponding VS Code task definitions from the workspace file

**Prompt 3 -- Post-Removal Verification**

Copilot checks the workspace integrity after deletions:
1. Reads every surviving INDEX.md -- verifies no entries point to deleted files
2. Reads every surviving workflow -- verifies no references to deleted personas or skills
3. Reads every surviving policy -- verifies no references to deleted workflows or personas
4. Reads the workspace file -- verifies no task definitions reference deleted skill src/ directories
5. Searches all surviving .md files for any filename of a deleted file -- catches prose references
6. Reports: table of issues found (file, line, broken reference) or "All clear"

If issues found, user approves fixes and Copilot applies them before proceeding.

**Prompt 4 -- Rename & Rebrand**

1. Renames `latam.code-workspace` to `ml-vol-estimator.code-workspace`
2. Global find-replace: "eq-latam-ai" --> "ml-vol-estimator", "LatAm" --> "ML Vol", "Equity Latin America Strats" --> "ML Realized Volatility Forecasting"
3. Updates `.gs-project.yml` with new project metadata
4. Rewrites `README.md` for ML vol project
5. Strips `.gitlab-ci.yml` (no CI for now)

**Prompt 5 -- Post-Rename Verification**

1. Case-insensitive search across ALL remaining files for: "latam", "brazil", "eq-latam", "LATAM", "LatAm" (NOTE: do NOT flag "slang" or "secdb" -- these are intentionally kept)
2. Verifies the workspace file name change propagated (no references to old filename)
3. Verifies .gs-project.yml has new project name
4. Reports: list of straggler matches with file + line number, or "All clear"

If stragglers found, Copilot fixes them with user approval.

**Prompt 6 -- Session 1 Handoff Summary**

Copilot produces a structured summary for the user to reference when starting Session 2:
1. **Removed**: count of files/directories deleted per primitive type
2. **Surviving**: list of all remaining skills, personas, workflows, policies, memory files, .github/prompts
3. **Marked for adaptation**: list of files classified as ADAPT in Prompt 1
4. **Known issues**: any unresolved stragglers or edge cases
5. **Ready for Session 2**: confirms the workspace is clean and lists the files that need adaptation

Output: saves this summary to `workspace/tmp/session-1-handoff.md` for reference.

### Session 2: Rewrite Core Framework (Prompts 7-12)

**Goal:** Adapt the surviving framework for ML vol forecasting.

**Prompt 7 -- Rewrite AGENTS.md**

The most critical prompt. Copilot reads current AGENTS.md plus `workspace/docs/research/optimal-feature-set.md` and `workspace/docs/research/data-access.md`. Rewrites AGENTS.md with:

- Project identity: ML Realized Volatility Forecasting -- signal discovery
- Boot protocol: Read person/user.md + INDEX.md (unchanged pattern)
- Research-first philosophy: explore before building, one topic deep per session, verify on data before coding
- Key constraints: QLIKE primary metric, never random k-fold on time series, feature set > model choice, every experiment independently reportable, train in log-RV space
- Skill routing table: updated for surviving + new skills (new skills listed as "planned -- created in Session 3")
- Data access summary: 34 symbols, tick RV, E-mini L2, SPX IV surface, cross-asset
- Evaluation targets: 30-80 bps QLIKE improvement + economic-value test (delta-hedged straddle Sharpe, vol-targeting VaR)

The prompt embeds the full project context (thesis, audiences, feature layer summary, model architecture plan) so Copilot can write a comprehensive AGENTS.md.

**Prompt 8 -- AGENTS.md Verification**

Copilot verifies the rewritten AGENTS.md:
1. Boot protocol check: do `memory/person/user.md` and `memory/INDEX.md` actually exist?
2. Skill routing: for every skill listed in the routing table, does the corresponding `skills/<NAME>/` directory exist? (New skills should be marked as "planned")
3. Persona references: does every persona mentioned in AGENTS.md exist in `personas/`?
4. Workflow references: does every workflow mentioned exist in `workflows/`?
5. Ghost check: case-insensitive search of AGENTS.md for "latam", "brazil", "eq-latam" (not "slang" or "secdb" -- those are kept)
6. Content review: does the project description accurately reflect ML vol forecasting? Does it mention QLIKE, the 34-symbol universe, the feature layers, and the research-first philosophy?
7. Reports: checklist of pass/fail for each item

**Prompt 9 -- Adapt Personas**

Reads each surviving persona file and rewrites domain context:
- analyst --> vol-researcher (quantitative RV analysis, feature exploration, baseline testing)
- forge --> model-builder (LightGBM/LSTM/ensemble, QLIKE optimization, hyperparameter tuning)
- sentinel --> eval-sentinel (QLIKE watchdog, overfitting detection, DM/MCS testing, look-ahead bias checking)
- oracle --> data-oracle (Chunk Store, TSDB, Marquee, data quality, tick alignment)
- Others: light-touch adaptation, update references from LatAm to ML vol

Updates personas/INDEX.md.

**Prompt 10 -- Adapt Workflows + Update Surviving .github/prompts**

Workflows:
- `bootup.md` --> ML vol session start (load research journal, check open questions)
- `debug.md` --> ML pipeline debugging (data issues, convergence, feature bugs, look-ahead bias)
- `execute.md` --> ML implementation (feature engineering, model training, evaluation)
- `plan.md` --> research planning (exploration sessions, experiment design)
- `review.md` --> ML code review (data leakage checks, QLIKE validation, statistical testing)
- Creates new `research.md` workflow for structured research sessions

.github/prompts:
- Updates surviving prompt files to reference ML vol context
- Does NOT create new prompt files here (that happens in Prompt 20 to avoid duplication)

Updates workflows/INDEX.md.

**Prompt 11 -- Adapt Policies + Add ML Constraints**

1. Removes LatAm-specific references from existing policies
2. Adds ML-specific constraints (new file or appended to operating-principles.md):
   - Never use random k-fold CV on time-series data (always purged/blocked)
   - QLIKE is the primary loss function, not MSE
   - No model architecture proposals before features are understood
   - Research-first: verify on data before building
   - Feature engineering > model complexity
   - Every experiment must be independently reportable
   - Train in log-RV space, not raw RV
   - COVID period requires explicit regime handling (include/exclude/separate)

**Prompt 12 -- Session 2 Checkpoint + Handoff**

Comprehensive verification of all Session 2 work:
1. Reads AGENTS.md -- verifies boot protocol, routing table, project context are complete
2. Reads every adapted persona -- verifies ML vol context, no LatAm remnants
3. Reads every adapted workflow -- verifies ML pipeline references, no LatAm remnants
4. Reads every adapted policy -- verifies ML constraints are present
5. Cross-references: personas referenced in workflows exist, workflows referenced in AGENTS.md exist
6. Ghost check across all adapted files

Handoff summary saved to `workspace/tmp/session-2-handoff.md`:
- List of all adapted files with one-line description of changes
- State of AGENTS.md (complete/needs-update)
- Files ready for Session 3 (memory import + skill creation)

### Session 3: Import Research & Create ML Content (Prompts 13-18)

**Goal:** Populate the memory system with research and create new ML-specific skills.

**Prompt 13 -- Tiered Research Import**

Implements the tiered memory strategy:
1. Reads all files in `workspace/docs/research/`
2. Creates summary cards in `memory/research/` for each file:
   - YAML frontmatter (created, updated, tags, status, relates)
   - 500-1500 token summary of key facts, formulas, decisions
   - `source:` field pointing to full file in workspace/docs/research/
   - Priority: P1 (optimal-feature-set, data-access, project-design, evaluation-framework, volatility, project-scope-and-data, feature-composition, complete-pipeline), P2 (individual features, model architectures, bibliography, project-plan), P3 (open-questions, journal, decision-trees, project-proposals)
3. Updates memory/INDEX.md with all new entries, load triggers, token budgets
4. Creates memory/research/README.md explaining the tiered structure

**Prompt 14 -- Research Import Verification**

Copilot verifies the memory system integrity:
1. For every entry in `memory/INDEX.md`, verify the file exists at the listed path
2. For every summary card in `memory/research/`, verify the `source:` path points to a real file in `workspace/docs/research/`
3. For every summary card, verify the `status:` field is "active" and the priority tier (P1/P2/P3) in the frontmatter matches what INDEX.md says
4. Count total token budget across all P1 files -- flag if >50k tokens (CoALA budget constraint)
5. Verify `memory/research/README.md` exists and describes the tiered structure
6. Reports: table of (file, status, priority, source-valid, token-estimate) for each memory card

**Prompt 15 -- Context Completeness Review**

Cross-references the research materials against the memory system. Uses the markdown reference-extracts and full research files (not the PDF -- Copilot's PDF parsing is unreliable):
1. Reads all markdown files in `workspace/docs/research/` (research files + reference-extracts)
2. Reads all memory summary cards in `memory/research/`
3. For each major concept in the reference-extracts (feature layers 0-7, model specs, evaluation criteria, data constraints, pipeline architecture), verifies representation in at least one memory card
4. Cross-references the optimal-feature-set.md (all 7 layers, ~50 features) against summary cards -- flags any feature or formula mentioned in the source but absent from memory
5. Reports gaps with specific quotes from source files
6. Creates additional memory cards for any gaps found

Note: The PDFs (vol-project-ref.pdf, vol-learning-guide.pdf) are available in `workspace/docs/` for human reference but are NOT used as Copilot input due to unreliable PDF parsing. The reference-extracts serve as the machine-readable equivalent.

**Prompt 16 -- Create ML Skills (Full Executable Pattern)**

Creates 7 new skills. Each skill follows the eq-latam-ai pattern: `skills/<SKILL_NAME>/SKILL.md` (agent instructions) + `skills/<SKILL_NAME>/src/` (thin wrapper scripts that invoke the top-level `src/ml_vol_estimator/` package) + workspace task definition in the `.code-workspace` file. The per-skill `src/` scripts are `.cmd` wrappers (e.g., `ingest_task.cmd`) that call into `src/ml_vol_estimator/` modules -- they are NOT duplicates of the package code.

1. **DATA_INGEST** -- Fetch tick data (Chunk Store), daily data (TSDB), IV surface (Marquee). Args: symbol list, date range, data type. Output: parquet/CSV to workspace/tmp/
2. **FEATURE_BUILD** -- Compute feature layers from raw data. Args: feature layer (0-7), symbol, date range. Output: feature DataFrame
3. **MODEL_TRAIN** -- Train models with proper CV. Args: model type (HAR/Ridge/LightGBM/LSTM/ensemble), feature config, CV strategy. Output: trained model + metrics
4. **EVALUATE** -- Run evaluation suite. Args: model path, test data, metrics list. Output: QLIKE/MSE tables, DM test results, MCS membership
5. **BACKTEST** -- Economic value testing. Args: signal type (IV-RV gap, vol-targeting), backtest window. Output: P&L series, Sharpe, drawdown
6. **RESEARCH** -- Structured research session. Args: topic, depth (quick/deep). Reads journal, explores topic, prompts user to update findings
7. **NOTEBOOK** -- Jupyter notebook workflow. Args: notebook name, kernel. Creates/runs notebooks for exploration

Each SKILL.md includes: frontmatter, purpose, skill identity table, when-to-use rules, args JSON schema, task-based execution steps, examples.

Updates skills/INDEX.md and workspace task definitions.

**Prompt 17 -- Create Python Instructions**

Creates `.github/instructions/python.instructions.md` with `applyTo: "**/*.{py,ipynb}"`:
- GS Python environment conventions (conda, internal packages)
- Data access patterns (Chunk Store queries, TSDB calls, Marquee API)
- ML constraints: QLIKE loss, purged k-fold CV, log-RV space, no look-ahead bias
- Testing: TDD (failing test --> implement --> pass)
- Import conventions for internal packages

**Prompt 18 -- Session 3 Checkpoint + Handoff**

Comprehensive verification:
1. For every new skill in `skills/`: SKILL.md exists, `src/` directory has at least one .cmd file, workspace file has corresponding task entry
2. Skills/INDEX.md lists all 7 new skills with correct paths
3. `memory/INDEX.md` entries all resolve to existing files
4. `python.instructions.md` has valid `applyTo` pattern
5. AGENTS.md skill routing table -- update "planned" entries to actual now that skills exist
6. Cross-reference: each skill's SKILL.md references `src/ml_vol_estimator/` modules that will be created in Session 4 -- list these as "expected modules" for Prompt 19

Handoff summary saved to `workspace/tmp/session-3-handoff.md`:
- Memory system state (count of P1/P2/P3 cards, total token budget)
- Skills created (list with status)
- Expected src/ modules for Session 4
- Any unresolved gaps from completeness review

### Session 4: Scaffold & Verify (Prompts 19-22)

**Goal:** Create the src/ skeleton and run comprehensive final verification.

**Prompt 19 -- Set Up src/ Structure**

Creates the Python package as a properly named module (`ml_vol_estimator`):

```
src/
├── ml_vol_estimator/
│   ├── __init__.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── chunk_store.py       # Tick data access via pytickclient
│   │   ├── tsdb.py              # Daily data from TSDB
│   │   └── marquee.py           # IV surface from Marquee ERDVOL
│   ├── features/
│   │   ├── __init__.py
│   │   ├── har.py               # HAR/HARQ/SHAR: log RV d/w/m, RQ, RQ interaction
│   │   ├── asymmetry.py         # Semivariances, BPV, jumps, continuous variation
│   │   ├── options.py           # ATM IV, VRP, skew, term slope, butterfly, VVIX
│   │   ├── microstructure.py    # Price accel, OBI, depth ratio, spread, VPIN
│   │   ├── cross_asset.py       # Treasury slope, FX vol, commodity vol, DY spillover
│   │   └── calendar.py          # FOMC, NFP, OpEx, earnings proximity
│   ├── models/
│   │   ├── __init__.py
│   │   ├── baselines.py         # HAR, HARQ, SHAR, Ridge-HAR, Lasso-HAR
│   │   ├── lightgbm_model.py    # LightGBM with QLIKE custom objective
│   │   ├── lstm_model.py        # LSTM/TCN for intraday E-mini sequences
│   │   └── ensemble.py          # Prediction-level blending
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── metrics.py           # QLIKE, MSE, MAE, R-squared
│   │   ├── statistical_tests.py # Diebold-Mariano, Model Confidence Set
│   │   └── economic_value.py    # Delta-hedged straddle, vol-targeting Sharpe
│   ├── pipeline/
│   │   ├── __init__.py
│   │   └── runner.py            # End-to-end orchestration
│   └── utils/
│       ├── __init__.py
│       └── time_series.py       # Purged k-fold CV, walk-forward, expanding window
├── pyproject.toml               # Package config with ml_vol_estimator as the package
└── README.md                    # Package usage instructions
```

Each module file: module docstring, import stubs, class/function signatures with docstrings, `raise NotImplementedError()` bodies. The package is importable as `from ml_vol_estimator.features import har`.

Updates `.gitignore` for Python ML artifacts (`__pycache__/`, `*.pkl`, `*.h5`, `*.csv`, `.ipynb_checkpoints/`, `*.parquet`, `mlruns/`, `wandb/`).

**Prompt 20 -- Create .github/prompts for ML Workflows**

Creates new prompt files:
- `research.prompt.md` -- Start a structured research session
- `feature.prompt.md` -- Feature engineering workflow
- `train.prompt.md` -- Model training workflow
- `evaluate.prompt.md` -- Run evaluation suite
- `backtest.prompt.md` -- Economic value testing

Each follows the existing .prompt.md format with persona reference, context loading instructions, and step-by-step workflow.

**Prompt 21 -- Full Verification Sweep**

Comprehensive final check across the entire workspace:
1. **Reference integrity**: Every INDEX.md entry --> file exists. AGENTS.md references --> exist. Every SKILL.md --> src/ scripts + workspace tasks exist.
2. **No ghosts**: case-insensitive search of all .md files for "latam", "brazil", "eq-latam" --> 0 hits (do NOT flag "slang" or "secdb" -- intentionally kept)
3. **Workspace file**: `ml-vol-estimator.code-workspace` has task entries for ALL skills (surviving + new)
4. **Memory tiering**: every summary card in `memory/research/` has valid `source:` path
5. **Instruction triggers**: `python.instructions.md` has correct `applyTo` pattern
6. **src/ structure**: all `__init__.py` files present, no empty directories, all modules referenced by skill .cmd wrappers exist
7. **Skill-to-src/ mapping**: each skill's .cmd wrapper references a module that exists in `src/ml_vol_estimator/`
8. **Boot protocol test**: simulate the boot sequence -- do the two P0 files exist and are they readable?
9. **Report**: summary table of all checks with pass/fail status

**Prompt 22 -- Final Summary + Next Steps**

Copilot produces the definitive workspace status document:
1. **Transformation complete**: what was removed (count), what was adapted, what was created
2. **Workspace inventory**: count of skills, personas, workflows, policies, memory files, .github/prompts, src/ modules
3. **Memory system**: P1/P2/P3 card counts, total token budget, any gaps flagged in completeness review
4. **Known limitations**: skill .cmd wrappers are stubs (need real environment paths), src/ modules are API stubs (no implementation), evaluation not yet possible
5. **Recommended first session**: suggests starting with a `/research` prompt to explore RV data using the DATA_INGEST skill, which will validate the data access pipeline
6. **Priority order for implementation**: data access first (validate Chunk Store queries), then HAR baseline (Layer 0), then progressive feature layers

Output: saves to `workspace/docs/transformation-complete.md` for permanent reference. Also cleans up `workspace/tmp/session-*-handoff.md` files (no longer needed).

---

## 5. Research Transfer Strategy

### Tiered Memory Architecture

Following the eq-latam-ai CoALA pattern, research materials are stored in two tiers:

**Tier 1: Summary Cards** (`memory/research/`)
- 500-1500 token summaries with YAML frontmatter
- Priority-tagged (P1/P2/P3) for loading strategy
- `source:` field points to full file
- Loaded on-demand by INDEX.md triggers

**Tier 2: Full Documents** (`workspace/docs/research/`)
- Complete research files, unmodified from this repo
- Referenced by summary cards when deeper detail needed
- PDFs stored in `workspace/docs/`

### Priority Assignments

| Priority | Files | Load Trigger |
|---|---|---|
| P1 (on cue) | optimal-feature-set, data-access, project-design, evaluation-framework, volatility, project-scope-and-data (extract), feature-composition (extract), complete-pipeline (extract) | Feature engineering, data access, model design, evaluation tasks, pipeline architecture |
| P2 (on demand) | har-components, jump-detection, leverage-effect, microstructure, cross-asset, implied-vol, calendar-events, bibliography, project-plan | Specific feature layer work, literature reference |
| P3 (archive) | open-questions, research-journal, deep-research-decision-trees, project-proposals | Research session start, project history review |

---

## 6. Chapter Extraction Plan

Convert 4 vol-project-ref LaTeX chapters to clean markdown for agent consumption:

| Extract | Source Chapters | Purpose |
|---|---|---|
| project-scope-and-data.md | ch01 + ch02 | What we're forecasting, universe, data sources, horizons |
| feature-composition.md | ch08 | How the 7 feature layers interact and compose |
| evaluation-framework.md | ch13 | QLIKE, DM tests, MCS, economic value methodology |
| complete-pipeline.md | ch14 | End-to-end architecture from data to signal |

Each extract: clean markdown, formulas as inline LaTeX where possible, tables preserved, tcolorbox content converted to blockquotes or callouts, citations converted to inline references.

---

## 7. Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Repo approach | Fork and strip | Preserves framework infrastructure (VS Code tasks, workspace config, CoALA memory system) |
| Prompt format | Single guide document | User prefers copy-paste from one reference over slash commands |
| Prompt architecture | Phase-based, 22 prompts, 4 sessions (6+6+6+4) | Full verification after every critical step + session handoff summaries |
| Session model | Grouped sessions | Related prompts share context within session; fresh start between sessions |
| Copilot mode | Agent mode | Can autonomously create/edit/delete files |
| Skill pattern | Full executable (SKILL.md + src/ + tasks) | Matches eq-latam-ai convention, enables task-based execution |
| Memory format | Tiered (summaries + full files) | Summary cards for fast loading, full files for deep reference |
| CI | None for now | GitLab repo, CI added later when pipeline stabilizes |
| Audit approach | Copilot classifies independently | More flexible, catches things user might miss |
| Slang/SecDB | Keep all Slang/SecDB skills, memory, instructions | SecDB is GS's core data platform; Slang skills needed for tick data, positions, pricing |

---

## 8. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Copilot context limits on long prompts | May truncate or lose track | Grouped sessions limit context per session; checkpoint prompts verify |
| Research information loss during transfer | Missing context leads to wrong implementation | Context completeness review (Prompt 9) cross-references markdown extracts against memory |
| Interactive audit takes too long | 47 skills + 30+ memory files to review | Consolidated audit (1 prompt not 6) with table format for fast review |
| VS Code task wiring for new skills | Broken task references | Prompt 11 and 14 include verification steps |
| Copilot generates low-quality skill stubs | Skills don't match eq-latam-ai quality | Prompt 10 explicitly references existing skills (e.g., GIT) as templates |
| Copilot refuses bulk file deletions | Audit removals stall | If Copilot declines, user deletes files manually and re-runs the verification portion of Prompt 2 |
| Copilot PDF parsing unreliable | Context completeness review fails | Prompt 9 uses markdown reference-extracts instead of PDFs; PDFs are human-only reference |

---

## 9. Success Criteria

1. Clean workspace: 0 hits for "latam", "brazil", "eq-latam" across active files (Slang/SecDB references are intentionally kept)
2. Working boot: AGENTS.md loads correctly, references resolve, memory INDEX is complete
3. Research available: all P1 memory cards exist with valid source pointers
4. Skills functional: 7 new skills have SKILL.md + src/ + workspace task entries
5. src/ scaffolded: all modules have API stubs with docstrings
6. No orphans: every file is referenced by at least one INDEX or routing table
