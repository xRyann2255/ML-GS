# ML Vol Estimator — User Manual

> Agentic workflow reference for the ml-vol-estimator repo. Type `/` in Copilot Chat to see all commands.

---

## Execution surfaces

This repo runs on two supported surfaces (see [AGENTS.md](../../AGENTS.md) “Supported Execution Surfaces”):

- **S-B (GS Linux Coder workspace, nix + uv):** the `./vol` bash wrapper covers every arm (`run`, ingest-*, `audit`, `present`, `kvar`, `cache-status`, `cache-clear`, `test`/`test-all`/`testlf`, `lint`, `fmt`, `typecheck`, `exec`, `bg`, `jobs`, …).
- **S-A (GS Windows desktop, VS Code Chat, H: drive):** use `vol.cmd` (dev-loop subset: `test` / `test-all` / `testlf` / `lint` / `fmt` / `typecheck` / `exec` / `bg` / `jobs`) or the predefined VS Code tasks. `./vol` is bash-only and does not run on Windows; long-running compute routes to S-B.
- **S-C (GitHub cloud coding agent):** unsupported — do not dispatch work here.

All paths below use `${ROOT}` for the repo root (`H:\ml-vol-estimator` on S-A, `~/ceph-storage/ml-vol-estimator` on S-B). Substitute your own root when copy-pasting.

---

## Quick Reference

| Command | What it does |
|---------|-------------|
| `/experiment` | Bridge research hypothesis to a logged experiment — config generation, validation gates, result logging |
| `/research` | Structured vol research — explore one topic deep on real data |
| `/feature` | Add and validate a feature layer (0–6) for RV forecasting |
| `/backtest` | Economic value testing — IV-RV gap signal, vol-targeting Sharpe |
| `/plan` | Decompose task, define acceptance criteria, order subtasks |
| `/execute` | Implement, verify, and finish (test-first, ML guardrails) |
| `/debug` | Root-cause analysis and regression isolation (3-state: DIAGNOSE → FIX → VERIFY) |
| `/review` | ML-focused code review with severity framework |
| `/learn` | Distill session knowledge into persistent memory |
| `/status` | Project dashboard — milestones, trial registry, QLIKE scorecard |

---

## Choosing the Right Command

| I want to... | Use | Why |
|-------------|-----|-----|
| Run a new ML experiment from a hypothesis | `/experiment` | Validates hypothesis, generates config, runs pipeline, logs results |
| Understand a volatility topic or data pattern | `/research` | One-topic-deep exploration with real data, produces journal entries |
| Build or implement something | `/plan` → `/execute` | Plan scopes the work, execute implements and verifies |
| Implement a specific feature layer (0-6) | `/feature` | Validates distributions and checks for lookahead bias |
| Compare model results statistically | `./vol compare --experiment X --baseline Y` | Per-horizon bps table with DM stats |
| Test economic value of a signal | `/backtest` | IV-RV gap signal, vol-targeting Sharpe |
| Fix a bug or diagnose unexpected behavior | `/debug` | 3-state root-cause analysis — diagnosis before fix |
| Get a quick answer or make a small edit | `/lightweight` | Budget mode — skips memory loading and persona ceremony |
| Check quality of existing code or results | `/review` | Severity-rated ML audit — data leakage, CV protocol, statistical validity |
| Clean up lint, schema, or structural issues | `/lint-workspace` | Lint suite + housekeeping |
| Fix design-compliance violations | `/cure` | Deeper than lint — audits against design principles |
| Save what I learned this session | `/learn` | Distills findings into persistent memory for future sessions |

> **Tip:** If you're unsure, just describe what you want in plain language. The agent matches keywords to workflows automatically.

---

## Getting Started

### Session Lifecycle

1. **Boot up.** Start a new session with `/bootup`. The agent reads `project-state.md` (current QLIKE scorecard, next action) and the trial registry, then presents the next experiment to run.

2. **Work.** Use slash commands to drive the session. Most sessions use 1–3 commands.

3. **State persists automatically.** The trial registry (`workspace/research/trials.yaml`) and `project-state.md` serve as the primary continuity mechanism between sessions. No manual handoff needed.

4. **Resume.** Next session, `/bootup` picks up where you left off via the trial registry and project state.

### Typical Session Patterns

#### 1. Experiment Day — `/bootup` → `/experiment`

The most common pattern. Bootup identifies the next experiment, `/experiment` validates the hypothesis, generates a config, you run it, and results auto-log to the trial registry.

#### 2. Research Day — `/bootup` → `/research` → `/experiment`

Explore a volatility topic in depth. Once you have a testable hypothesis, `/experiment` bridges it to a logged experiment.

#### 3. Build Day — `/bootup` → `/plan` → `/execute`

`/plan` scopes the work (no code). `/execute` writes failing tests, implements, verifies. Skip `/plan` for small tasks.

#### 4. Quick Task — `/lightweight`

No memory, no persona swaps, ≤20% context window. Good for one-liners, bad for multi-file or ML-specific work.

#### 5. Debug — `/bootup` → `/debug`

3-state workflow: DIAGNOSE → FIX → VERIFY. Circuit breaker after 3 failed attempts. Provide error messages verbatim.

---

## Subagent-Driven Workflows

For complex tasks that span multiple files or modules, the framework uses **subagent decomposition** to prevent context bloat. The orchestrating agent stays lean (plan + coordinate + verify) while spawning subagents with fresh context to do the heavy lifting.

### How It Works

1. `/plan` produces a task decomposition where each step is tagged `inline` or `subagent`
2. `/execute` reads those tags — `subagent` steps get spawned with a structured context packet
3. Each subagent works on fresh context (no conversation history bloat)
4. Orchestrator collects results and runs integration verification

### When Subagents Are Used Automatically

| Signal | Result |
|--------|--------|
| Task reads 3+ files | Subagent spawned |
| Task modifies 2+ modules | Subagent spawned |
| Task would accumulate >200 lines of tool output | Subagent spawned |
| Single file, <50 lines, obvious fix | Executed inline (no subagent) |
| Iterative debug cycles (read → edit → test → repeat) | Subagent gets fresh context per attempt |

### Suggested Multi-Step Patterns

#### Large Feature Implementation — `/plan` → `/execute`

Best for implementing a new feature layer or multi-module change:

```
You: /plan — implement Layer 3 microstructure features (OBI, depth ratio, VPIN)

Agent (plan phase):
  Step 1 [subagent]: Add OBI computation to features/micro.py + tests
  Step 2 [subagent]: Add depth_ratio computation to features/micro.py + tests
  Step 3 [subagent]: Add VPIN computation to features/micro.py + tests
  Step 4 [inline]:   Update feature registry and config schema
  Step 5 [inline]:   Integration test — full pipeline with Layer 3 enabled

Agent (execute phase):
  → Spawns 3 subagents (steps 1-3) in parallel with fresh context each
  → Executes steps 4-5 inline after subagents complete
  → Runs full test suite for integration verification
```

#### Multi-Module Refactor — `/refactor`

Best for restructuring code across several modules while preserving behavior:

```
You: /refactor — split features.py into per-layer submodules

Agent:
  SCOPE: identify invariant (all 147 tests must pass), boundary (features/ directory)
  LOCK: run baseline tests, add characterization tests for uncovered paths
  RESTRUCTURE: spawns one subagent per module (har.py, asymmetry.py, options.py, micro.py)
    - Each subagent gets: source file, target file, test file, invariant definition
  VERIFY: integration tests on merged result
```

#### Multi-Symbol Research — `/research`

Best for exploring a hypothesis across many symbols or horizons:

```
You: /research — does rate_vol predict RV at h=22 across all 21 symbols?

Agent:
  FOCUS: defines hypothesis card, identifies data needed
  EXPLORE: spawns subagents per symbol batch (e.g., 7 symbols each)
    - Each subagent computes OLS expanding-window QLIKE for its symbols
    - Returns: per-symbol QLIKE table, significance tests
  DOCUMENT: orchestrator aggregates into summary table, writes journal entry
```

#### Cross-Horizon Experiment — `/experiment`

Best for running the same hypothesis across multiple horizons with independent computation:

```
You: /experiment — test realized_correlation feature at h=1, h=5, h=22

Agent:
  Validates hypothesis, generates per-horizon configs
  Spawns subagent per horizon (independent: different train/test splits)
  Collects QLIKE results, computes bps vs baseline, logs to trial registry
```

### What You See vs What Happens

From your perspective, nothing changes — you still use the same slash commands. The difference is under the hood:

| Before (monolithic) | After (subagent-driven) |
|---------------------|------------------------|
| Agent reads 10 files, context fills up | Orchestrator delegates, stays lean |
| Long edit → test → fix cycles in one context | Each cycle in fresh subagent context |
| Agent "forgets" early decisions late in session | Orchestrator retains plan, subagents get targeted context |
| Multi-module work drifts | Each subagent has strict write scope |

### Tips for Best Results

1. **Be specific about scope up front.** "Implement Layer 3" is better than "add some features." Clearer scope → better decomposition.
2. **Use `/plan` before `/execute` for anything non-trivial.** The plan phase produces the subagent tags — skipping it means `/execute` must decompose on the fly.
3. **Large tasks benefit most.** For quick single-file edits, subagent overhead isn't worth it — `/lightweight` or just describe the edit directly.
4. **If the agent asks to spawn subagents, let it.** The context isolation is working as designed.
5. **All subagents run on Opus 4.6** — same quality as the orchestrator, just with fresh context.

### When Things Go Wrong

| Problem | What to do |
|---------|------------|
| **Agent drifts from your request** | Say "stop" or "let's refocus on X" |
| **Agent gives generic answers** | Load context: "read data-audit.md" or "load the Layer 2 card" |
| **Session feels stuck** | Start a new chat. Next `/bootup` picks up via trial registry |
| **Wrong workflow activated** | Say "switch to /research" or "use the debug workflow" |
| **Agent asks too many questions** | Use `/lightweight` or be more specific up front |

---

## CLI Reference

The `vol` wrapper at project root handles environment setup (uv, PATH, venv) internally. Every command is self-contained.

### Core Commands

| Command | What it does |
|---------|-------------|
| `vol run --config <yaml>` | Run experiment (tournament + dashboard + metrics) |
| `vol experiments` | List all trials from the registry with QLIKE numbers |
| `vol new-experiment --base <yaml> --name <name> --set key=val` | Create new experiment config from baseline |
| `vol compare --experiment <id> --baseline <id>` | Compare two trials side-by-side (bps table) |
| `vol status` | Show data ingestion manifest |
| `vol test [args]` | Run pytest (args forwarded) |
| `vol lint` | Ruff check (read-only) |
| `vol fmt` | Ruff format (auto-fix) |
| `vol audit` | Data integrity audit, updates manifest |
| `vol present --dashboard-path <rel>` | Generate presentation HTML with swappable dashboard (output: `workspace/presentation/presentation.html`) |
| `vol kvar [--target both\|same-day\|next-day]` | Compare GSVIVS signal results across cached IV sources |
| `vol cache-status [--config <yaml>]` | List cached LSTM fold artifacts (per-fold training cache) |
| `vol cache-clear [--config <yaml> \| --all]` | Delete cached LSTM fold artifacts |

### Experiment Commands (new)

#### `vol experiments` — List all trials

```bash
$ ./vol experiments
ID           Date         Status         h1 QLIKE   h5 QLIKE   h22 QLIKE  Hypothesis
----------------------------------------------------------------------------------------------------
trial-001    2026-05-08   completed      0.1601     0.1390     0.2100     HAR baseline establishes reference QLIKE
trial-004    2026-05-22   completed      0.1574     0.1527     0.2420     Per-symbol IV interactions improve h=1 Q
trial-005    -            NOT_STARTED    -          -          -          train_size=1260 fixes h=22 underfitting

5 completed, 3 pending
```

#### `vol new-experiment` — Create config from baseline

Clone a baseline config, apply parameter overrides, and save:

```bash
# Double the training window
./vol new-experiment \
  --base workspace/configs/tournament_lgbm_iv_v1_LOCKED.yaml \
  --name trial_longer_train \
  --set cv.train_size=1260

# Add regularization
./vol new-experiment \
  --base workspace/configs/tournament_lgbm_iv_v1_LOCKED.yaml \
  --name trial_strong_reg \
  --set model.params.num_leaves=8 \
  --set model.params.min_child_samples=300
```

The command automatically sets `name` and `output_dir` in the generated config.

| Argument | Required | Description |
|----------|----------|-------------|
| `--base` | Yes | Path to baseline YAML config to clone |
| `--name` | Yes | Name for the new config (becomes filename and output_dir) |
| `--set` | No | Key=value overrides in dot-notation (repeatable) |
| `--force` | No | Overwrite existing config file |

#### `vol compare` — Side-by-side trial comparison

```bash
$ ./vol compare --experiment trial-004 --baseline trial-001

Comparing: trial-004 vs trial-001 (baseline)
  Experiment: Per-symbol IV interactions improve h=1 QLIKE
  Baseline:   HAR baseline establishes reference QLIKE for h=1/5/22

Horizon    Experiment   Baseline     Diff (bps)   Verdict
------------------------------------------------------------
h1         0.1574       0.1601           -168     PASS
h5         0.1527       0.1390           +985     FAIL
h22        0.2420       0.2100          +1523     FAIL

Key insight: Per-symbol interaction key for h=1; train_size too short for longer horizons
```

Negative bps = improvement (lower QLIKE is better).

---

### Primary Command: `vol run --config <yaml>`

Every config uses the tournament code path — even single-model configs produce ranked tables and an interactive Plotly HTML dashboard.

```bash
vol run --config <yaml>               # Run experiment
vol run --config <yaml> --skip-ingest # Skip data fetch (use cached)
vol run --config <yaml> --symbols X,Y # Override YAML universe
vol run --config <yaml> --tune        # Enable Optuna hyperparameter tuning
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--config` | *(required)* | Path to experiment YAML config |
| `--symbols` | from config | Comma-separated symbol override |
| `--skip-ingest` | `False` | Skip data ingestion; use cached parquet files |
| `--workers` | from config | Parallel threads for API fetching |
| `--tune` | `False` | Enable Optuna hyperparameter tuning (nested CV) |
| `--no-tune` | - | Disable tuning (override YAML) |
| `--n-trials` | from config | Number of Optuna trials |
| `--force-retrain` | `False` | Force retraining even if cached results exist |

**Output:**
- Tournament table (Rich-formatted, per horizon)
- Interactive dashboard: `{output_dir}/plots/tournament_dashboard.html`
- Structured metrics: `{output_dir}/metrics.json`
- Auto-update of `trials.yaml` if a matching NOT_STARTED trial exists

**Auto-update:** When `vol run` completes, it checks `workspace/research/trials.yaml` for a trial whose `config` field matches the config filename. If found with `status: NOT_STARTED`, it fills in the QLIKE results, computes bps vs baseline, sets verdict, and marks `completed`.

---

### YAML Config Structure

Configs live in `workspace/configs/`. Each experiment is one YAML file.

#### Minimal config (single symbol, one model)

```yaml
name: baseline_har
universe: [SPY]
date_range: ["2015-01-02", "2024-12-31"]
horizons: [1, 5, 22]
feature_layers: [har_core]
model:
  name: har
  params: {}
cv:
  method: expanding_window
  n_splits: 5
  purge_gap: 5
  train_size: 252
  test_size: 63
tournament:
  models: [har]
training_mode: per_symbol
seed: 42
output_dir: data/models/baseline_har
```

#### Config field reference

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Experiment identifier |
| `universe` | list[str] | Symbols (from 34-symbol universe) |
| `date_range` | [start, end] | ISO date strings |
| `horizons` | list[int] | Forecast horizons in trading days (1, 5, 22) |
| `feature_layers` | list[str] | Feature layers: `har_core`, `asymmetry`, `noise_robust`, `options`, `iv_surface`, `calendar` |
| `model.name` | string | Model: `har`, `harq`, `shar`, `har_j`, `har_cj`, `ridge_har`, `lasso_har`, `lightgbm`, `stacking_har_lgbm` |
| `model.params` | dict | Model hyperparameters |
| `cv.method` | string | `expanding_window` or `purged_kfold` |
| `cv.purge_gap` | int | Days purged between train/test (prevents leakage) |
| `cv.train_size` | int | Initial training window (trading days) |
| `cv.test_size` | int | Test window per fold |
| `training_mode` | string | `pooled` or `per_symbol` |
| `tournament.models` | list[str] | Models to compare (if 1, still produces dashboard). Labels in `model_configs` are also valid entries. |
| `tournament.model_configs` | dict | Optional. Maps alias labels to `{name, params}` for variant model configs (e.g. two LightGBM configs). |
| `output_dir` | string | Where to write results |

**Model resolution in tournaments:** When `tournament.models` contains a label:
1. If the label matches `model.name`, the top-level `model.params` are inherited automatically.
2. If the label is in `tournament.model_configs`, uses that entry's `name` (registry key) and `params`.
3. Otherwise, the label is treated as a registry key with empty params.

Example with two LightGBM configs:
```yaml
model:
  name: lightgbm
  params: {num_leaves: 16, max_depth: 4}
tournament:
  models: [har, ridge_har, lightgbm, lgbm_aggressive]
  model_configs:
    lgbm_aggressive:
      name: lightgbm
      params: {num_leaves: 31, max_depth: 6, min_child_samples: 50}
```

#### Generic HAR-X (`harx` family)

The `harx` family — `harx`, `ridge_harx`, `lasso_harx`, `elasticnet_harx` — is a
config-driven HAR model that appends an arbitrary list of feature columns to
the HAR core (`log_rv_d`, `log_rv_w`, `log_rv_m`). The extras are supplied via
`model.params.extra_features: list[str]` (may be `[]` for pure HAR). Any listed
column missing from the training matrix raises a `ValueError` at fit time
rather than being silently dropped, so YAML/data mismatches surface loudly.
Use it for one-off HAR ablations without adding a bespoke model class.

```yaml
feature_layers: [har_core, options]
model:
  name: harx
  params:
    extra_features: [atm_iv_30d, vrp_30d]
```

Full template: [workspace/configs/example_harx.yaml](../configs/example_harx.yaml).

---

## Running an Experiment from Start to Finish

This is the complete workflow for running a new ML experiment in this project:

### Step 1: Formulate a hypothesis

Start with a research finding or intuition. Example:

> "Longer training window (1260 days / 5 years) will fix h=22 underfitting because the current 504-day window is too short for monthly forecasts."

### Step 2: Create the experiment config

Clone the current best config and apply changes:

```bash
./vol new-experiment \
  --base workspace/configs/tournament_lgbm_iv_v1_LOCKED.yaml \
  --name tournament_lgbm_h22_long_window \
  --set cv.train_size=1260 \
  --set horizons.0=22
```

Output:
```
Created: ${ROOT}/workspace/configs/tournament_lgbm_h22_long_window.yaml
Base: ${ROOT}/workspace/configs/tournament_lgbm_iv_v1_LOCKED.yaml
Overrides: cv.train_size=1260, horizons.0=22

Run with: ./vol run --config workspace/configs/tournament_lgbm_h22_long_window.yaml
```

### Step 3: Register the trial (optional — `/experiment` does this automatically)

Add to `workspace/research/trials.yaml`:

```yaml
  - id: "trial-005"
    date: null
    config: "tournament_lgbm_h22_long_window.yaml"
    hypothesis: "train_size=1260 fixes h=22 underfitting"
    motivation: "504 obs leaves 2 years of training for 1-month forecast"
    horizons: {}
    baseline_config: "tournament_lgbm_iv_v1_LOCKED.yaml"
    status: NOT_STARTED
    priority: 1
```

### Step 4: Run the experiment

```bash
./vol run --config workspace/configs/tournament_lgbm_h22_long_window.yaml --skip-ingest
```

The pipeline:
1. Loads cached RV parquets for all symbols
2. Builds feature layers (har_core, asymmetry, options, etc.)
3. Trains LightGBM via expanding-window CV with purge gap
4. Produces OOS predictions across all folds
5. Computes QLIKE tournament table with DM tests
6. Generates interactive dashboard + metrics.json
7. **Auto-updates trials.yaml** (matches config filename → fills in results)

### Step 5: Check results

```bash
# See the updated registry
./vol experiments

# Compare against baseline
./vol compare --experiment trial-005 --baseline trial-001

# Or compare against the best h=1 model
./vol compare --experiment trial-005 --baseline trial-004
```

### Step 6: Interpret and decide next step

| Result | Action |
|--------|--------|
| QLIKE improved + DM p < 0.05 | PASS — lock config, move to next horizon |
| QLIKE improved but DM not significant | MARGINAL — need more data or stronger signal |
| QLIKE worse | FAIL — analyze why, form new hypothesis |

### Full example output

```bash
$ ./vol compare --experiment trial-005 --baseline trial-004

Comparing: trial-005 vs trial-004 (baseline)
  Experiment: train_size=1260 fixes h=22 underfitting
  Baseline:   Per-symbol IV interactions improve h=1 QLIKE

Horizon    Experiment   Baseline     Diff (bps)   Verdict
------------------------------------------------------------
h22        0.1950       0.2420          -1942     PASS
```

---

## Trial Registry

The trial registry (`workspace/research/trials.yaml`) is the single source of truth for experiment state.

**Rules:**
- Append-only (completed entries never overwritten)
- `vol run` auto-fills results when a matching NOT_STARTED trial exists
- `/bootup` reads last 5 completed + all NOT_STARTED entries
- `/experiment` creates new entries with validation gates
- No entry cap

**Schema per trial:**
```yaml
- id: "trial-004"
  date: "2026-05-22"
  config: "tournament_lgbm_iv_v1_LOCKED.yaml"
  hypothesis: "Per-symbol IV interactions improve h=1 QLIKE"
  motivation: "Research finding: cross-asset features hurt but per-symbol IV helped"
  horizons:
    h1: {qlike: 0.1574, vs_har_bps: +27, dm_stat: 2.85, dm_p: 0.004, verdict: PASS}
    h5: {qlike: 0.1527, vs_har_bps: -1237, dm_stat: -3.2, verdict: FAIL}
    h22: {qlike: 0.2420, vs_har_bps: -1601, dm_stat: -4.1, verdict: FAIL}
  baseline_config: "tournament_multi21.yaml"
  key_insight: "Per-symbol interaction key for h=1; train_size too short for longer horizons"
  status: completed
```

---

## Where Data Lives

| Stage | Location | Format |
|-------|----------|--------|
| Raw ticks | GS Chunk Store (remote) | In-memory DataFrame via `pytickclient` |
| Daily RV panels | `data/raw/ticks/{SYMBOL}.parquet` | Parquet, 1 row/trading day, ~22 columns |
| Model artifacts | `data/models/{experiment}/` | Predictions + model objects |
| Metrics | `data/models/{experiment}/metrics.json` | JSON (per-model, per-horizon QLIKE/MSE) |
| Configs | `workspace/configs/` | YAML experiment definitions |
| Trial registry | `workspace/research/trials.yaml` | YAML (append-only experiment log) |
| Project state | `memory/research/project-state.md` | P0 boot file (~500 tokens) |
| Plans | `workspace/plans/` | plan-suite + `/plan` output tree — read-only for subagents |
| Presentation | `workspace/presentation/` | `vol present` generator |

---

## ML Conventions

Enforced automatically. Knowing them helps interpret agent behavior.

| Convention | Rule |
|-----------|------|
| **Training space** | Always log-RV, never raw RV |
| **Primary metric** | QLIKE (quasi-likelihood loss) — not MSE |
| **CV protocol** | Purged/blocked k-fold or expanding-window walk-forward — never random k-fold |
| **Feature priority** | Feature engineering > model complexity |
| **COVID handling** | Feb–Jun 2020 requires explicit regime handling per experiment |
| **Reproducibility** | Every experiment independently reportable |
| **Research-first** | Explore before building |

---

## All Commands

### ML Pipeline

| Command | What it does |
|---------|-------------|
| `/experiment` | Hypothesis → config → run → log results (the full research loop) |
| `/research` | One topic deep on real data. Produces journal entries. |
| `/feature` | Implement and validate a feature layer (0-6). Checks for lookahead bias. |
| `/backtest` | IV-RV gap signal, delta-hedged straddle P&L, vol-targeting Sharpe. |

### Build & Fix

| Command | What it does |
|---------|-------------|
| `/plan` | Scope work, acceptance criteria, subtask ordering. No code. |
| `/execute` | Test-first implementation with ML guardrails. |
| `/debug` | 3-state: DIAGNOSE → FIX → VERIFY. Circuit breaker at 3 failures. |
| `/review` | Severity-rated ML audit: leakage, CV protocol, statistical validity. |
| `/fix it` | Full fix pipeline — diagnose, prescribe, implement, test, audit. |
| `/refactor` | Lock-tests-first restructuring. |

### Meta & Workflow

| Command | What it does |
|---------|-------------|
| `/bootup` | Session start — reads project state, trial registry, presents next action. |
| `/status` | Project dashboard — milestones, QLIKE scorecard, open trials. |
| `/progress` | Generate weekly progress log. |
| `/lightweight` | Budget mode — minimal context, fast execution. |
| `/learn` | Distill session knowledge into persistent memory. |
| `/cure` | Design-compliance healthcheck and remediation. |
| `/team` | Parallel subagent coordination (3+ streams). |
| `/lint-workspace` | Workspace-wide structural and safety checks. |

### Tools & Utilities

| Command | What it does |
|---------|-------------|
| `/slang` | Slang development — full context, language reference. |
| `/slang-review` | Create or update a Slang ScriptReview. |
| `/glimpse` | Search Slang script database for patterns. |
| `/gitlab-search` | Search GitLab code, MRs, commits, issues. |
| `/git-commit` | Auto-group and commit with conventional messages. |
| `/data-audit` | Data integrity — validate parquets, detect NaN/gaps. |
| `/kill-orphans` | Kill orphaned processes. |
| `/lint` | Native Slang lint. |
| `/slop-cleaner` | AI slop cleanup. |

### Learning System

| Command | What it does |
|---------|-------------|
| `/study` | Adaptive study session. |
| `/teach` | Guided concept teaching from the learning graph. |
| `/quiz` | Interactive vol-knowledge quiz with spaced repetition. |
| `/learning-status` | Mastery dashboard — progress, review queue. |
| `/expand-learning-graph` | Add concepts or feature layers to the graph. |
| `/weekly-learning-goals` | Generate gap-driven weekly learning targets. |

---

## Memory System

4-tier CoALA memory. The agent loads the right files per task.

| Tier | When loaded | Contents |
|------|-------------|----------|
| **P0** | Every session (boot) | User profile, memory index, project state |
| **P1** | On demand per task type | Feature layers, evaluation, data access, trial registry |
| **P2** | On specific query | HAR components, jumps, microstructure, bibliography |
| **P3** | Archive / fallback | Deep reference, old research |

---

## Personas (5 active)

Personas are constraint sets, not personalities:

| Persona | Constraints |
|---------|------------|
| **MODEL-BUILDER** | Test-first, log-RV, purged CV, QLIKE primary, scope control |
| **EVAL-SENTINEL** | 3-stage evaluation, severity gates, hard-stop on CRITICAL |
| **TRACEHOUND** | Reproduce-first, 3-failure circuit breaker, hypothesis discipline |
| **BUDGETEER** | Minimal context, no memory loading, scope minimization |
| **VOL-RESEARCHER** | Domain constraints: log-RV, COVID regime, L2=E-mini, IV=SPX, 34+1 symbols |

---

## Graph models

Graph neural network (GNN) and graph-linear (GHAR) arms are first-class tournament entries alongside HAR-family and tree models. Everything below is validated by the tests in [src/tests/unit/graphs/](../../src/tests/unit/graphs/) and the runner path at [src/volforecast/pipeline/runner.py](../../src/volforecast/pipeline/runner.py).

### Model registry — how to add a new graph model

Graph models follow the same `@register_model("<key>")` pattern as every other arm in [src/volforecast/models/](../../src/volforecast/models/). The only extra contract is:

1. Set the class attribute `requires_graph = True` so the runner dispatches through the graph fold path instead of the tabular path.
2. Accept a `fit(graphs, on_progress=None)` and `predict(graphs)` signature where each `graph` is either a PyG `Data` object or the graph dict `{"x": (N,F) np, "edge_index": (2,E) torch.long, "edge_attr": (E,) torch.float, "y": (N,) np, "date": Timestamp}`.
3. Optional: set the class attribute `warmup = <int>` if the model needs preceding graphs for state (e.g. recurrent models like `dcrnn_har`). The runner will splice the last `warmup` train graphs before the first test graph automatically ([runner.py#L285](../../src/volforecast/pipeline/runner.py#L285), [runner.py#L3038](../../src/volforecast/pipeline/runner.py#L3038)).
4. Optional: expose `spillover_matrix(graphs, *, symbols=None) -> pd.DataFrame` to have the runner persist an NxN attention/spillover heatmap next to `metrics.json` for the dashboard ([runner.py#L2715-L2744](../../src/volforecast/pipeline/runner.py#L2715-L2744)).

The registered graph models today are `ghar`, `gnn`, `gnnhar`, `stid`, `dcrnn_har`, `gsp_har`, `gnn_learned` (see the interface ledger in [00-overview.md §4.4](../plans/gnn-implementation-plans/00-overview.md)).

### The `graph:` config block

Every experiment that runs a graph arm needs an experiment-level `graph:` block. The full schema and defaults live on `GraphConfig` in `src/volforecast/config.py`; the canonical example is [workspace/configs/trial_090_gnn_grand_tournament.yaml#L56-L66](../configs/trial_090_gnn_grand_tournament.yaml#L56-L66).

```yaml
graph:
  method: glasso              # identity | full | corr | knn | glasso | dy | sector | factor_residual | regime_blend
  input: returns              # returns | log_rv — what the builder ingests
  window: 1000                # rolling estimation window in trading days
  refit_every: 21             # re-estimate cadence in trading days (21 ≈ monthly)
  min_history: 252            # minimum days of history before the first refit
  node_features: [log_rv_d, log_rv_w, log_rv_m, ...]   # panel columns used as x
  params: {}                  # builder-specific knobs (e.g. GLASSO alpha, k for knn)
```

**Warmup contract:** the first graph snapshot only fires once `min_history` days of the `input` panel are available. The runner will not call any graph arm on a fold whose test block starts before that threshold — this is what keeps the adjacency point-in-time.

### Per-arm overrides via `tournament.model_configs`

The experiment-level `graph:` block sets the default. Any arm listed in `tournament.models` can override it by adding a `graph:` key inside its own `model_configs` entry. This is how a single trial-094 config runs GHAR on GLASSO, DCRNN-HAR on a directed DY graph, and MTGNN-style GNN on `identity` (learned inside the model) in the same tournament.

Example ([trial_090_gnn_grand_tournament.yaml#L182-L189](../configs/trial_090_gnn_grand_tournament.yaml#L182-L189)):

```yaml
tournament:
  models: [har_iv, ghar, gnnhar_1l, dcrnn_har, gnn_learned]
  baseline: har_iv
  model_configs:
    dcrnn_har:
      name: dcrnn_har
      params: {hidden_dim: 16, k: 2, seq_len: 22, loss: qlike, ...}
      graph:                       # per-arm override — daily-refresh directed DY
        method: dy
        input: log_rv
        window: 252
        refit_every: 1
        min_history: 100
        node_features: [log_rv_d, log_rv_w, log_rv_m]
        params: {var_lags: 4, fevd_horizon: 10, threshold: 0.05}
```

STID (`stid`) is a special case: `requires_graph = True` for harness parity but ignores edges internally, giving the identity-embedding deflation control the graph arms must beat.

### GPU knobs

Graph arms train through the same fold×GPU + seed×GPU pools used by LightGBM and the LSTM. The knobs live at the top level of the experiment YAML (see [trial_090_gnn_grand_tournament.yaml#L44-L49](../configs/trial_090_gnn_grand_tournament.yaml#L44-L49) and the tournament block at #L91):

| Knob | Effect |
|---|---|
| `n_gpus: 8` | Round-robin fold dispatch across `cuda:0..cuda:7` via `ProcessPoolExecutor(spawn)` |
| `tournament.parallel_models: 1` | Each GPU arm owns all 8 GPUs via fold parallelism; keep at 1 for long GNN runs so no arm starves |
| `training_mode: pooled` | Every symbol shares one model across all cross-sections (the correct default for graph arms — you need the whole cross-section to build the snapshot) |
| `checkpoint_enabled: true` | Persist per-model per-fold state so an interrupted 8-GPU run resumes without recomputing completed folds |
| `fold_cache_enabled: true` | Cache the per-fold graph dataset on disk so a resume avoids rebuilding the schedule from scratch |
| `seed: 42` | Reproducibility — flows into `np.random.default_rng`, `torch.manual_seed`, and every per-seed re-init inside the graph arms |

### What the dashboard shows for graph arms

When a graph experiment finishes, the runner writes two artifact files next to `metrics.json` in the experiment `output_dir`:

- `graph_diagnostics_h{h}.parquet` — one row per refit with density, consecutive-refit Jaccard, and graph signal energy ([runner.py#L2670-L2712](../../src/volforecast/pipeline/runner.py#L2670-L2712)). The dashboard renders these as three time-series traces titled "Graph quality".
- `spillover_matrix_h{h}.parquet` — NxN heatmap of the winning model's learned attention/spillover when the model exposes `spillover_matrix(...)` ([runner.py#L2715-L2744](../../src/volforecast/pipeline/runner.py#L2715-L2744)). Rendered as a Plotly heatmap with a `not-causal` caveat in the subtitle.

Both panels are opt-in: non-graph experiments skip them silently, and characterization tests protect the golden-file behavior of every other panel ([test_dashboard_graph_panels.py](../../src/tests/unit/test_dashboard_graph_panels.py)).

### PIT hygiene — the leakage checks that gate every graph arm

Point-in-time discipline is enforced by unit tests, not by review:

- Correlation graph: [test_corr_is_point_in_time](../../src/tests/unit/graphs/test_correlation_graphs.py#L32) — perturbing rows after the estimation date must not change the graph.
- Regime-blend graph: [test_pit_classification](../../src/tests/unit/graphs/test_regime_blend_graph.py#L117) — calm/stress labels only from in-window data.
- Regime feature layer: [TestRegimeLayerPIT](../../src/tests/unit/test_regime_layer.py#L134) — filtered (not smoothed) probabilities + frozen-parameter forward filtering.
- Per-symbol normalization: [test_per_symbol_norm_train_only_leakage](../../src/tests/unit/test_per_symbol_norm.py#L431) — scaler stats never see test dates.

Add a new graph builder → add its PIT test in [src/tests/unit/graphs/](../../src/tests/unit/graphs/) following the correlation-graph template. This is a hard gate for any Plan-01-style extension.

### End-to-end quick reference

```bash
# Launch the grand GNN tournament (13 arms × 3 horizons on 8 GPUs)
./vol run --config workspace/configs/trial_090_gnn_grand_tournament.yaml --skip-ingest

# Inspect the tournament table + conditional splits
open data/models/trial_090_gnn_grand_tournament/plots/tournament_dashboard.html

# Compare graph winner against har_iv
./vol compare --experiment trial-094 --baseline trial-081
```

For the full skeptic's-checklist evidence trail behind this config, see [workspace/research/gnn-program-review.md](../research/gnn-program-review.md).
