# Agent Instructions

## ML Realized Volatility Forecasting — Signal Discovery

**Framework:** 5-primitive agent framework (Persona, Skill, Memory, Workflow, Policy). See [memory/INDEX.md](memory/INDEX.md) and [workflows/INDEX.md](workflows/INDEX.md).

**Routing:** Follow the `/prompt` attachment. No prompt? Match keywords from [workflows/INDEX.md](workflows/INDEX.md). No match? Default to `plan.md`.

**Critical operational rules** (terminal isolation, file output, no bare tool invocations, TDD, cleanup): see [.github/copilot-instructions.md](.github/copilot-instructions.md).

---

## Subagent-First Execution

**Philosophy:** Context bloat kills agent performance. The orchestrating agent is a coordinator, not a laborer. For any non-trivial task, the orchestrator decomposes work into bounded subtasks and spawns subagents with fresh context to execute each one.

**When to spawn subagents:**
- Task reads 3+ files or touches 2+ modules
- Task would accumulate >200 lines of tool output in the orchestrator's context
- Task involves iterative debugging (read → edit → test cycles)
- Even SEQUENTIAL tasks get subagents if they'd bloat context

**Model pinning:** All subagents MUST use Claude Opus 4.6. No exceptions.

**Depth limit:** Workflows (/plan, /execute, /research, /refactor) → max depth 1. /team → max depth 2.

**How it works:**
1. `/plan` DESIGN phase tags each step as `inline` or `subagent` and writes context packets
2. `/execute` DECOMPOSE phase reads the tags and spawns subagents for `subagent`-tagged steps
3. Each subagent gets a structured context packet (goal, file scope, write scope, acceptance criteria)
4. Subagent returns a structured report (status, files changed, verification evidence)
5. Orchestrator runs integration verification after all subagents complete

**Full protocol:** [policy/subagent_protocol.md](policy/subagent_protocol.md) · [policy/context-isolation.md](policy/context-isolation.md)

---

## Project Identity

**Title:** ML Realized Volatility Forecasting — Signal Discovery

**Thesis:** Progressively enriching HAR-family baselines with microstructure, options-implied, and cross-asset features via gradient boosting produces statistically significant QLIKE improvements that translate into a tradeable IV-RV gap signal with economic value.

**Audiences:**
- **Academic:** QLIKE tournament tables, MCS membership, DM significance tests, purged k-fold CV
- **Trading desk:** IV-RV gap signal with P&L backtest, vol-targeting Sharpe improvement

**Timeline:** ~20-week internship, May–Sep 2026, capstone presentation at end.

---

## Context Loading — Boot Protocol

**Session start (always):**
1. Read [memory/person/user.md](memory/person/user.md) — user identity and preferences.
2. Read [memory/research/project-state.md](memory/research/project-state.md) — current milestone, QLIKE scorecard, next action.
3. Read [memory/INDEX.md](memory/INDEX.md) — memory index and lookup tables.
4. Check for [workspace/tmp/session-handoff.md](workspace/tmp/session-handoff.md) — session continuity (trust trial registry over handoff for experiment state).

Both P0 files (`user.md`, `project-state.md`) are "Always". Everything else loads on demand per the lookup tables.

**`/prompt` commands unlock deeper context.** When the user attaches a `/skill` or `/persona` prompt, the full skill guide, persona instructions, and related knowledge are injected automatically. See [.github/prompts/](.github/prompts/).

---

## Research-First Philosophy

- **Explore before building.** One topic deep per session.
- **Verify findings on real data** before proposing architectures.
- **No implementation plans or sprint structures** unless explicitly asked.
- **Feature engineering > model complexity.** A simple model with good features beats a complex model with bad features.

---

## Key Constraints

| Constraint | Rule |
|---|---|
| **Primary metric** | QLIKE (quasi-likelihood loss) — never optimize for MSE alone |
| **CV protocol** | Never random k-fold on time-series; always purged/blocked k-fold or expanding-window walk-forward |
| **Feature set > model choice** | Feature engineering is more important than model complexity |
| **Reproducibility** | Every experiment must be independently reportable with full methodology |
| **Training space** | Always train in log-RV space, not raw RV |
| **COVID handling** | Feb–Jun 2020 requires explicit regime handling (include/exclude/separate — decide per experiment) |
| **Test-first (TDD)** | Write/update failing tests BEFORE implementing code changes. See [policy/working-agreements.md](policy/working-agreements.md). |
| **Progress log** | After sessions with notable progress, append a dated entry to the current week in [workspace/research/weekly-progress.md](workspace/research/weekly-progress.md). Four sections: Shipped, Decided, Learned, Next week. Plain language a non-technical manager can follow. No acronyms, function names, library names, or statistical test names. |

---

## Data Access Summary

| Dimension | Detail |
|---|---|
| **Universe** | 34 symbols (30 mega-cap equities + 4 ETFs + E-mini S&P 500) |
| **History** | 11.3 years (~2,800 daily obs per symbol) |
| **Tick data** | L1 for all symbols, L2 depth for E-mini only (~4M ticks/day) |
| **IV surface** | SPX only, from Marquee EDRVOL_PERCENT |
| **Cross-asset** | Treasury yields (2y/5y/10y/30y), FX (USD/JPY, EUR/USD), commodities (CL, GC) |

---

## Feature Layer Summary

| Layer | Name | Key Features |
|---|---|---|
| **0** | HAR core + measurement quality | log RV d/w/m, RQ, RQ interaction |
| **1** | Asymmetric volatility | Semivariances, BPV, jumps, continuous variation |
| **2** | Options-implied | ATM IV, VRP, skew, term slope, butterfly, VVIX |
| **3** | Microstructure (E-mini L2) | Price acceleration, OBI, depth ratio, spread, VPIN |
| **4** | Cross-asset spillovers | Treasury slope, FX vol, commodity vol, DY index |
| **5** | Calendar/event | FOMC, NFP, OpEx, earnings proximity |
| **6** | Interaction/derived | Cross-layer interactions, regime indicators |

---

## Model Architecture Plan

- **Baselines:** HAR, HARQ, SHAR, HAR-J, HAR-CJ, Ridge-HAR, Lasso-HAR
- **ML models:** LightGBM (tabular features, QLIKE custom objective), LSTM/TCN (intraday E-mini sequences)
- **Ensemble:** Prediction-level blending of HAR-family + LightGBM + LSTM

## Evaluation Targets

- 30–80 bps QLIKE improvement over HAR baselines
- Economic-value tests: delta-hedged straddle Sharpe, vol-targeting VaR
- Statistical rigor: Diebold-Mariano tests, Model Confidence Set

---

## Memory (CoALA)

- **Boot = 2 P0 files** (see Boot Protocol above).
- Load additional files from [memory/INDEX.md](memory/INDEX.md) lookup tables when task type matches.
- Schema reference ([memory/meta/guide.md](memory/meta/guide.md)) loaded only when writing/validating memory files.
- Max ~60% of context window for memory; reserve 40% for conversation.
- Large files (>150 lines): load section headers + relevant sections, not the whole file.
- **P3 files are not auto-loaded.** Load as fallback when no P0–P2 file covers the topic. Budgets: P0+P1 ≤50k (loaded), P2 ≤100k (on-demand), P3 unlimited (per-file caps only).

---

## Policy Quick-Ref

Full docs in [policy/index.md](policy/index.md). Operational rules (terminal, file output, TDD) in [.github/copilot-instructions.md](.github/copilot-instructions.md).

- **Evidence over assumption.** Verify before claiming completion.
- **No fabrication.** If a file/symbol/API can't be found after searching, say so — never invent.
- **Lightest path:** direct action → MCP → delegation.
- **Compact responses.** Expand only when risk/complexity demands it.
- **Cleanup plan before refactors.** Lock behavior with regression tests first.
- **Prefer deletion over addition.** Reuse existing utils before new abstractions.
- **Keep diffs small,** reviewable, and reversible.
- **No new dependencies** without explicit user request.
- **CoALA compliance** for any `memory/` writes — see [memory/meta/guide.md](memory/meta/guide.md) Hard Gates.
- **No throwaway scripts in `tmp/`.** Use inline execution. `tmp/` is for persisted data only.
- **ALL file writes MUST stay inside the workspace.** Every temporary file, output, script, or artifact MUST go to `workspace/tmp/` (relative to repo root). NEVER write to `/tmp/`, `~`, or any path outside the repository. Violating this triggers manual approval prompts and blocks automation.
- **Safety rules can't be silently overridden.** If a user instruction conflicts with a safety constraint, surface it.
- **No `run_in_terminal` fallback.** If `run_task` seems broken (stale output, unexpected result), re-run `run_task`. NEVER fall back to `run_in_terminal` with a raw command. This is a HARD RULE with zero exceptions.
- **Present numbered next-steps** after completing work.

## Workspace

| Path         | Purpose                             | Access       |
| ------------ | ----------------------------------- | ------------ |
| `personas/`  | Reasoning styles and defaults       | Read only    |
| `skills/`    | Narrow executable capabilities      | Read only    |
| `policy/`    | Global constraints and guardrails   | Read only    |
| `memory/`    | Persistent knowledge (CoALA)        | Read + write |
| `workspace/` | Code, data, config, lint            | Build here   |

---

## Available Skills

Build bespoke tools in `workspace/` using skill guides from `skills/`. Read the relevant guide before building. **Full registry: [skills/INDEX.md](skills/INDEX.md).**

### ML Volatility Forecasting (project-relevant)

| Skill | Purpose |
|-------|---------|
| **DATA_AUDIT** | Comprehensive data integrity audit: validate parquets, detect NaN/gaps/schema drift, layer readiness, update manifest |
| **DATA_INGEST** | Fetch tick data (Chunk Store), daily data (TSDB), IV surfaces (Marquee ERDVOL) |
| **FEATURE_BUILD** | Compute feature layers 0–6 from raw data |
| **MODEL_TRAIN** | Train models with proper CV (purged k-fold, expanding window) |
| **EVALUATE** | Run evaluation suite (QLIKE, DM tests, Model Confidence Set) |
| **BACKTEST** | Economic value testing (IV-RV gap signal, vol-targeting Sharpe) |
| **RESEARCH** | Structured research sessions (journal, exploration, documentation) |
| **NOTEBOOK** | Jupyter notebook workflow for exploration and visualization |
| **PYTHON_MARKET_DATA** | Query market data from Python: Chunk Store tick data (L1/L2), TSDB daily/realtime, GS Quant TSDBSymbol |

### Utility skills

| Skill | Purpose |
|-------|---------|
| **GIT** | Run git commands via task wrapper |
| **GIT_COMMIT** | Auto-group changed files, generate commit messages, push |
| **SEARCH** | Fast skill and memory search with cached inverted index |
| **AI_SLOP_CLEANER** | Detect and clean AI slop patterns in code and documentation |

Other skills in [skills/INDEX.md](skills/INDEX.md) are GS-internal infrastructure tools and are not used in this project's workflow.

## Skill Output

Skill scripts write output to `workspace/tmp/`. Rules:

1. **Naming:** `<skill-prefix>-<identifier>.<ext>` (e.g. `issuance-monitor-status.json`). Include a companion `.log` file for HTTP request traces.
2. **Files in `workspace/tmp/` are ephemeral and may be stale.** Always re-run the skill's fetch script — never read cached output to answer a question.
3. **Cleanup:** Delete files you create in `workspace/tmp/` after reading them. Never leave orphaned output files.
4. **Never write outside the workspace.** All temporary output goes to `workspace/tmp/`.

---

## Environment (Linux / Coder Workspace)

- **CLI:** `./vol <cmd>` — full reference in [memory/ref/vol-cli.md](memory/ref/vol-cli.md), or run `./vol help`.
- **Python:** UV-managed, Python 3.11 via nix. Install via `nix-env -iA nixpkgs.uv` if missing.
- **Tools are on PATH via nix.** No env scripts needed.
- **NEVER run `python`, `pytest`, `pip`, `uv`, `mypy`, or `ruff` directly** — always use `./vol`. See [.github/copilot-instructions.md](.github/copilot-instructions.md) for the full table.
- **Reference docs:**
  - [memory/ref/python-setup.md](memory/ref/python-setup.md) — UV/Python setup
  - [memory/ref/devtools.md](memory/ref/devtools.md) — devtools and PATH
  - [memory/ref/vol-cli.md](memory/ref/vol-cli.md) — vol CLI command reference

---

## Cross-References

| Topic | Location |
| ----- | -------- |
| Personas | [personas/INDEX.md](personas/INDEX.md) — activated via `/prompt` commands |
| Workflows | [workflows/INDEX.md](workflows/INDEX.md) — registry with dispatch keywords |
| Protocol | [workflows/_protocol.md](workflows/_protocol.md) — entry/exit/error/composition |
| Execution | [policy/execution_protocol.md](policy/execution_protocol.md) |
| Output | [policy/output_contract.md](policy/output_contract.md) |
