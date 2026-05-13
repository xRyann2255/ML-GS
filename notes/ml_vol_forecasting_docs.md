# ML Realized Volatility Forecasting — Complete Codebase Documentation

## 1. Project Overview

### Project Phases

| 6 | ML model training and evaluation | NOT STARTED |
| 7 | Economic value and signal backtest | NOT STARTED |

### Universe

- **34 symbols:** 30 mega-cap equities + 4 ETFs (SPY, QQQ, IWM, DIA) + E-mini S&P 500 (ES)
- **History:** 11.3 years (~2,800 daily obs per symbol)
- **Tick data:** L1 for all symbols, L2 depth for E-mini only (~4M ticks/day)
- **IV surface:** SPX only, from Marquee ERDVOL_PERCENT_STANDARD
- **Cross-asset:** Treasury yields (2y/5y/10y/30y), FX (USD/JPY, EUR/USD), commodities (CL, GC)

---

## 2. Repository Structure

```
h:\ml-vol-estimator\
├── AGENTS.md                    # Project identity, constraints, boot protocol
├── vol.cmd                      # CLI wrapper (env setup → venv → dispatch)
├── README.md                    # Repo overview
├── ml-vol-estimator.code-workspace  # VS Code workspace

├── .github/prompts/             # 48 slash commands for Copilot Chat routing

├── src/                         # Python package source
│   ├── pyproject.toml           # Build config, dependencies, entry points
│   └── volforecast/             # Main package (9 subpackages)
│       ├── __init__.py          # v0.2.0, triggers registration imports
│       ├── __main__.py          # CLI entry point (argparse + Rich)
│       ├── config.py            # ExperimentConfig dataclass
│       ├── constants.py         # Universe, fields, timezone
│       ├── protocols.py         # VolModel + FeatureLayer protocols
│       ├── registry.py          # MODEL_REGISTRY + FEATURE_REGISTRY
│       ├── cli/                 # CLI subcommands
│       ├── data/                # Data access (Chunk Store, TSDB, Marquee)
│       ├── features/            # Feature layers 0-5
│       ├── models/              # HAR family + ML stubs
│       ├── evaluation/          # Metrics + statistical tests
│       ├── pipeline/            # End-to-end runner
│       ├── reporting/           # HTML report generation
│       ├── visualization/       # Plot functions
│       ├── scripts/             # Standalone scripts
│       └── utils/               # Paths, persistence, CV splitters
├── tests/                       # 390 tests (20 files)
├── inspect_rv.py                # Quick RV data inspector
├── plot_rv.py                   # 5 exploratory RV plots
└── plot_har_forecast.py         # 5 HAR forecast performance plots

├── memory/                      # CoALA knowledge base (56 files)
│   ├── INDEX.md                 # Master map with lookup tables
│   ├── person/user.md           # User profile (P0, always loaded)
│   ├── slang/                   # 19 Slang language references
│   ├── ref/                     # 22 technical references
│   ├── sys/                     # 9 GS system references
│   ├── research/                # 25 ML vol research cards
│   └── meta/                    # Memory system governance

├── personas/                    # 16 reasoning personas
├── skills/                      # 46 executable capabilities
├── workflows/                   # 16 orchestration workflows
└── policy/                      # 11 global constraint files

└── workspace/                   # Active workspace
    ├── configs/                 # Experiment YAML configs
    ├── docs/                    # Data audit, user manual, PDFs
    ├── research/                # Journal, open questions, progress
    ├── plans/                   # Planning artifacts
    ├── tmp/                     # Ephemeral outputs (not committed)
    ├── raw/                     # Cached parquet data (gitignored)
    ├── bin/                     # secexpr-safe.cmd
    └── lint/                    # Ruff config
```

---

## 3. Development History

### Commit Log (23 commits)

```
f3194aa feat: implement tsdb VIX/SPX/VIX-futures + marquee IV surface functions
394e75e refactor: simplify agentic workflow framework
0bdb6b7 Enforce TDD across workflows: test-first gates in execute/fix
788ad4b feat: agentic workflow improvements - all phases
636502f feat: implement data pipeline – Chunk Store access, tick resampling, daily RV
42c3f65 fix: correct research path refs
4e392bb chore: transformation cleanup — memory, skills, docs, workspace updates
f7e4242 chore: clean up workspace/tmp
a481748 docs: final transformation summary and handoff cleanup
6b83962 fix(index): correct memory/skills INDEX counts
a80d28f feat(src): scaffold Python package skeleton and ML workflow prompts
8c8f178 chore: session 3 checkpoint
3c7bd3a feat(instructions): expand Python instructions with ML vol constraints
bb696b6 feat(skills): create 7 ML vol forecasting skills
a0fa163 docs: update session-3-handoff
363f2c8 fix(memory): patch research card gaps
01dc5b6 feat(memory): import tiered research cards
2eaaee8 docs: update session-2-handoff
8274f3f refactor(personas): adapt 4 major personas for ML vol forecasting
f3186eb docs: rewrite AGENTS.md for ML vol forecasting
e55e7ba docs: update session-1-handoff
a0c8e5b fix: remove straggler LatAm references
4a85d13 refactor: strip LatAm content, rebrand to ml-vol-estimator
d823ab9 test: repository access permissions
d8b8903 Init commit
476107c Initial commit
```

### Weekly Progress

| Week | Dates | Key Accomplishments |
|------|-------|---------------------|
| 1 | Apr 21-25 | Repo setup, learning guide written, project selected |
| 2 | Apr 28-May 2 | 80 papers reviewed, scope defined, feature layers designed, QLIKE chosen |
| 3 | May 5-9 | Core math engine (56 tests), 7 baselines, research-first pivot, LightGBM selected |
| 4 | May 12-16 | CLI pipeline, model persistence, Layer 0-1 completion (390 tests), triple expansion, Lee-Mykland jumps |

---

## 4. Agentic Workflow Framework

### Architecture: 5-Primitive Agent System

The project uses a structured agent framework with five primitives:

1. **Personas** — Reasoning styles that govern how the agent thinks (16 personas)
2. **Skills** — Narrow executable capabilities (46 skills)
3. **Memory** — Persistent knowledge organized in tiers (CoALA framework)
4. **Workflows** — State-machine orchestration of complex tasks (16 workflows)
5. **Policy** — Global constraints that override all other instructions (11 policy files)

### Prompt Routing Model

```
User types /command
    → .github/prompts/{command}.prompt.md loaded
    → Prompt specifies: workflow file + persona file
    → Workflow state machine executes with persona active
    → Memory loaded on-demand per INDEX.md lookup tables
```

**48 slash commands** available in `.github/prompts/`:
`/bootup`, `/research`, `/execute`, `/plan`, `/fix`, `/debug`, `/review`, `/refactor`, `/housekeep`, `/progress`, `/train`, `/evaluate`, `/backtest`, `/feature`, `/slang`, `/lint`, `/glimpse`, etc.

### Workflow State Machines (16 total)

| Workflow | Personas Used | State Machine | Purpose |
|----------|---------------|---------------|---------|
| **plan.md** | STRATEGOS | SCOPE → DESIGN → ROUTE → DONE | Task scoping and planning |
| **execute.md** | MODEL-BUILDER | RECON → IMPLEMENT → VERIFY → REPORT → DONE | Build and ship code |
| **research.md** | VOL-RESEARCHER | ORIENT → FOCUS → EXPLORE → DOCUMENT → DONE | Research exploration |
| **debug.md** | TRACEHOUND | SYMPTOM → HYPOTHESIZE → OBSERVE → NARROW → RECON → FIX → VERIFY → REPORT | Root-cause diagnosis |
| **fix.md** | TRACEHOUND → MODEL-BUILDER | DIAGNOSE → RECON → PRESCRIBE → IMPLEMENT → TEST → REVIEW → AUDIT → REPORT | Bug fixes |
| **bootup.md** | — | 7-step sequential | Session initialization |
| **progress.md** | — | GATHER → SYNTHESIZE → WRITE → DONE | Progress reporting |
| **review.md** | EVAL-SENTINEL | — | Code review |
| **refactor.md** | STRATEGOS → MODEL-BUILDER | Lock tests → restructure | Restructuring |
| **housekeep.md** | MODEL-BUILDER | — | Lint, cleanup, memory |
| **cure.md** | DOCTOR → MODEL-BUILDER | — | Design violations |
| **learn.md** | DATA-ORACLE | — | Persist knowledge |
| **interview.md** | — | — | Clarification for risky tasks |
| **lightweight.md** | BUDGETEER | — | Quick answers (minimal context) |
| **team.md** | MAESTRO | — | Parallel orchestration (3+ streams) |

### Workflow Composition Rules

- Workflows can yield to each other (e.g., `execute` yields to `plan` for scope resolution)
- **Max nesting depth: 2** — prevents infinite loops
- Yield-in inputs carry the yielding workflow's context
- First-match-wins condition evaluation at each state transition

### Protocol Contract (`_protocol.md`)

Every workflow follows a common contract:
- **Entry:** Load memory → do work state-by-state → transition on conditions
- **Exit:** Verify with evidence → offer numbered next-steps
- **Errors:** Retry once, then escalate
- **Composition:** Max 2 levels of yield nesting

### Example: How `/execute` Works

1. User types `/execute implement OHLCV enrichment`
2. `.github/prompts/execute.prompt.md` loaded → specifies `workflows/execute.md` + `personas/model-builder.md`
3. **RECON state:** Agent reads relevant source files, understands current implementation
4. **IMPLEMENT state:** Agent writes tests first (TDD gate), then implements code
5. **VERIFY state:** Runs tests, checks lint, confirms no regressions
6. **REPORT state:** Summarizes what was done, offers numbered next-steps

---

## 5. Memory System (CoALA)

### Tier Structure

| Priority | Scope | When Loaded | Budget |
|----------|-------|-------------|--------|
| **P0** | Always | Boot | ≤50k tokens (with P1) |
| **P1** | On demand per task type | Task match | ≤50k tokens (with P0) |
| **P2** | Specific queries only | Explicit need | ≤100k tokens |
| **P3** | Archive/deep reference | Fallback only | Per-file caps only |

### Domain Organization (56 files)

| Domain | Files | Content |
|--------|-------|---------|
| `meta/` | 2 | Memory governance rules |
| `person/` | 1 | User profile (always loaded) |
| `slang/` | 19 | Slang language & tooling reference |
| `ref/` | 22 | Technical references (Python setup, devtools, SecDB, Git) |
| `sys/` | 9 | GS platform references (Canvas, EngHub, SecDB ecosystem) |
| `research/` | 25 | ML vol research cards (features, evaluation, data, design) |

### Boot Protocol (Every Session)

1. Read `memory/person/user.md` — user identity, preferences, tone
2. Read `memory/INDEX.md` — master file map with lookup tables
3. Check for `workspace/tmp/session-*-handoff.md` — session continuity
4. Done. Additional memory loaded on-demand per task type matching.

---

## 6. Skills Registry

### ML Volatility Forecasting Skills (7)

| Skill | Purpose | Status |
|-------|---------|--------|
| DATA_INGEST | Fetch tick data, daily data, IV surfaces | Active |
| FEATURE_BUILD | Compute feature layers 0-6 from raw data | Active |
| MODEL_TRAIN | Train models with proper CV | Active |
| EVALUATE | Run evaluation suite (QLIKE, DM, MCS) | Active |
| BACKTEST | Economic value testing (IV-RV gap, vol-targeting) | Planned |
| RESEARCH | Structured research sessions | Active |
| NOTEBOOK | Jupyter notebook workflow | Planned |

### Other Skills (39)

Slang/SecDB (15), Infrastructure/Auth (8), Operations (4), Messaging (2), Documentation (6), Python Data Access (1), Agent Customization (1).

---

## 7. Policy Layer

### Non-Negotiable Constraints

| Constraint | Rule |
|------------|------|
| **Primary metric** | QLIKE — never optimize for MSE alone |
| **CV protocol** | Never random k-fold on time series; always purged/blocked or expanding-window |
| **Training space** | Always log-RV (exponentiate only for final QLIKE evaluation) |
| **COVID handling** | Feb–Jun 2020 requires explicit regime treatment per experiment |
| **Test-first (TDD)** | Write failing tests BEFORE implementing. No exceptions. |
| **Feature set > model** | Feature engineering more important than model complexity |
| **Reproducibility** | Every experiment independently reportable with full methodology |
| **No look-ahead** | Feature at time t uses only data ≤ t |

### Working Agreements

- Cleanup plan before refactors — lock behavior with regression tests first
- Prefer deletion over addition — reuse existing utilities before new abstractions
- No new dependencies without explicit user request
- Keep diffs small, reviewable, and reversible
- Run lint after all changes

---

## 8. Python Package Architecture

### Package Layout

```
src/volforecast/             # Main package
├── __init__.py              # v0.2.0, triggers registration
├── __main__.py              # CLI entry (argparse), subcommand dispatch
├── config.py                # ExperimentConfig, ModelConfig, CVConfig
├── constants.py             # Universe, fields, timezone
├── protocols.py             # VolModel + FeatureLayer (runtime_checkable)
├── registry.py              # MODEL_REGISTRY + FEATURE_REGISTRY
├── cli/                     # 10 CLI modules
├── data/                    # 8 data access modules
├── features/                # 10 feature modules
├── models/                  # 5 model modules
├── evaluation/              # 4 evaluation modules
├── pipeline/                # 2 pipeline modules
├── reporting/               # Report generation (Jinja2)
├── visualization/           # 4 visualization modules
├── scripts/                 # 4 standalone scripts
└── utils/                   # 4 utility modules
```

### Key Design Patterns

1. **Registry + Protocol:** Models and feature layers register via `@register_model("name")` / `@register_feature_layer("name")` decorators. `VolModel` and `FeatureLayer` are `@runtime_checkable` structural typing protocols — no ABC inheritance required.

2. **Composable Progress:** CLI modules work standalone (`StageProgress`) or composed into `run-pipeline` via injected `PipelineProgress` handles. Progress displays use Rich panels with nested subtasks.

3. **Lazy Imports:** Each CLI subcommand imports its handler only when dispatched. Keeps startup fast (~50ms).

4. **CWD-Independent Paths:** `resolve_project_root()` walks up from `__file__` looking for marker files (`AGENTS.md` or `vol.cmd`). Prevents path breakage from `vol.cmd`'s directory change.

5. **Side-Effect Registration:** `__init__.py` imports `volforecast.features` and `volforecast.models` which triggers all `@register_*` decorators. Without this, registries appear empty.

### Dependency Graph

```
CLI (__main__.py)
└── Pipeline (runner.py)
    ├── FEATURE_REGISTRY → features/*.py
    ├── MODEL_REGISTRY → models/*.py
    ├── CV Splitters → utils/cv.py
    └── Evaluation → evaluation/metrics.py
         ↑
Data Layer (rv_panel.py → chunk_store.py → resample.py → measures.py → features/)
```

---

## 9. Configuration System

### Dataclass Hierarchy

```python
@dataclass
class ModelConfig:
    name: str           # Registry key (e.g., "har", "harq", "lightgbm")
    params: dict[str, Any] = field(default_factory=dict)

@dataclass
class CVConfig:
    method: str = "expanding_window"  # or purged_kfold, rolling_window, blocked_kfold
    n_splits: int = 5
    purge_gap: int = 5
    train_size: int | None = None
    test_size: int | None = None

@dataclass
class ExperimentConfig:
    name: str
    universe: list[str]
    date_range: tuple[str, str]
    horizons: list[int]
    feature_layers: list[str]
    model: ModelConfig
    cv: CVConfig
    training_mode: str = "per_symbol"
    seed: int = 42
    output_dir: Path = Path("workspace/models")
```

### Example YAML (`workspace/configs/baseline_har.yaml`)

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
training_mode: per_symbol
seed: 42
output_dir: workspace/models/baseline_har
```

### Path Resolution

`utils/paths.py` provides absolute path helpers that never break regardless of CWD:

| Function | Returns |
|----------|---------|
| `resolve_project_root()` | Walks up from `__file__` looking for `AGENTS.md` / `vol.cmd` |
| `raw_dir()` | `{root}/workspace/raw/` |
| `models_dir()` | `{root}/workspace/models/` |
| `configs_dir()` | `{root}/workspace/configs/` |
| `tmp_dir()` | `{root}/workspace/tmp/` |

---

## 10. CLI & End-to-End Pipeline

### Experiment Lifecycle — Start to Finish

An ML experiment takes raw market ticks from a database and produces a volatility forecast evaluation table. Here's the full chain:

```
STAGE 1: CONFIG
User writes a YAML file specifying:
  - symbols (e.g. SPY)
  - date range (e.g. 2015-2024)
  - forecast horizons (1, 5, 22 days ahead)
  - feature layers to use
  - model (e.g. "har", "harq", "shar")
  - cross-validation method

          ▼

STAGE 2: INGEST  (./vol run ingest --config ...)

For each symbol × each trading day:
  1. Chunk Store DB query → raw tick DataFrame
     (price, size, bid, ask at irregular timestamps)
  2. Previous-tick interpolation → regular 5-min bars
  3. Compute 18 daily measures from those bars:
     RV, RQ, BPV, semivariances, jumps, signed jumps,
     realized skewness/kurtosis, realized kernel, ...
  4. Save as workspace/raw/{SYMBOL}_rv_daily.parquet

Output: one row per trading day, ~18 columns of measures

          ▼

STAGE 3: TRAIN  (./vol run train --config ...)

  1. Load the daily parquet from Stage 2
  2. Feature layers transform raw measures into predictors:
     e.g. HARCoreLayer produces log_rv_d, log_rv_w,
     log_rv_m (rolling 1/5/22-day averages in log space)
  3. Target = log(RV) shifted forward by h days
  4. Time-aware CV splits the data (expanding window or
     purged k-fold — never random shuffle)
  5. Model fits on train fold, predicts on test fold
  6. Repeat across all folds → collect OOS predictions
  7. Save model + predictions to workspace/models/

          ▼

STAGE 4: EVALUATE  (./vol run evaluate --config ...)

Compare predictions to actual future RV using:
  - QLIKE (primary — quasi-likelihood loss)
  - MSE, MAE, R²
Output: tournament table ranking models

          ▼

STAGE 5: COMPARE (future)

Diebold-Mariano statistical tests between models
Model Confidence Set membership
→ "Is Model A significantly better than Model B?"
```

### Where Data Lives at Each Step

| Stage | Location | Format |
|-------|----------|--------|
| Raw ticks | GS Chunk Store (remote database) | In-memory DataFrame from `pytickclient` |
| Daily measures | `workspace/raw/{SYMBOL}_rv_daily.parquet` | Parquet, one row per trading day |
| Features + predictions | `workspace/models/{experiment_name}/` | Parquet + joblib |
| Metrics | `workspace/models/{experiment_name}/metrics.json` | JSON |

### Wrapper Script (`vol.cmd`)

```batch
# What vol.cmd does:
1. Resolves project root from its own location
2. Sources H:\uv-env.cmd for PATH setup (Python, uv)
3. Changes to src/ (where pyproject.toml lives)
4. Creates/syncs venv on first run (uv sync)
5. Dispatches subcommands:
   - vol test        → pytest
   - vol testlf      → pytest --lf (last failed)
   - vol run <args>  → python -m volforecast <args>
   - vol lint        → ruff check
   - vol fmt         → ruff format
   - vol typecheck   → mypy
   - vol sync        → uv sync
   - vol notebook    → jupyter lab
   - vol shell       → activate + shell
```

### CLI Entry Point (`__main__.py`)

```
vol run run-pipeline --config workspace/configs/baseline_har.yaml [--symbols SPY AAPL]
vol run ingest --config workspace/configs/baseline_har.yaml
vol run train --config workspace/configs/baseline_har.yaml
vol run evaluate --config workspace/configs/baseline_har.yaml
vol run report --config workspace/configs/baseline_har.yaml --open
```

### The `run-pipeline` Orchestration

When `run-pipeline` is invoked, it chains all three stages in sequence:

```python
# Simplified __main__.py logic for run-pipeline:
with PipelineProgress() as progress:
    # Stage 1: INGEST
    ingest_results = ingest.run(config, symbols, progress)
    # Stage 2: TRAIN
    train_results = train.run(config, symbols, progress)
    # Stage 3: EVALUATE
    evaluate_results = evaluate.run(config, progress)
```

Each stage can also run standalone (`vol run ingest`, `vol run train`, etc.).

### Progress Display System

Two Rich-based progress classes:

- **`PipelineProgress`** — Full 3-stage display with colored panels:
  - INGEST (blue), TRAIN (green), EVALUATE (yellow)
  - Nested subtasks (per-symbol, per-fold progress bars)
  - ETA calculation from rolling averages
  - Summary panels at stage completion

- **`StageProgress`** — Single-stage display for standalone commands

### Pipeline Runner Internals (`pipeline/runner.py`)

The `Pipeline` class orchestrates feature composition → model training → evaluation:

```python
class Pipeline:
    def __init__(self, config: ExperimentConfig): ...

    def run(self, daily_data, on_fold_complete=None, on_horizon_start=None) -> dict[int, Any]:
        # 1. Validate: 'rv' column exists and positive
        # 2. Compose features: iterate config.feature_layers,
        #    resolve from FEATURE_REGISTRY, call .compute(daily_data)
        # 3. Resolve model class from MODEL_REGISTRY
        # 4. Build CV splitter from config
        # 5. For each horizon h in config.horizons:
        #    a) Target = log(RV).shift(-h)  [forward-looking log-RV]
        #    b) Align X/y, drop NaN
        #    c) Walk-forward CV: fit on train, predict on test
        #    d) Collect OOS predictions
        #    e) Evaluate: qlike, mse, r_squared
        # 6. Return {horizon: {"metrics", "predictions", "model"}}
```

### Artifact Layout

```
workspace/models/{experiment_name}/
├── config.yaml           # Snapshot of experiment config
├── metrics.json          # Consolidated metrics (all symbols, horizons)
├── {symbol}/
│   ├── model_h1.joblib   # Fitted model for horizon 1
│   ├── model_h5.joblib   # Fitted model for horizon 5
│   ├── model_h22.joblib  # Fitted model for horizon 22
│   ├── predictions_h1.csv
│   ├── predictions_h5.csv
│   └── predictions_h22.csv
```

### Persistence Module (`utils/persistence.py`)

| Function | Purpose |
|----------|---------|
| `experiment_dir(config)` | `models_dir() / config.name` |
| `save_experiment_results(results, config, symbol)` | Saves joblib + CSV + updates metrics.json |
| `load_predictions(config, symbol, horizon)` | Reads predictions CSV |
| `load_all_metrics(config)` | Reads consolidated metrics.json |

Metrics.json uses append pattern: load existing → update → rewrite.

---

## 11. Data Access Layer

### Architecture

```
rv_panel.py (orchestrator)
├── trading_calendar.py → NYSE trading days
├── chunk_store.py → L1/L2 tick data via pytickclient
├── resample.py → tick → 5-min bars → daily RV (18 measures)
│   └── measures.py (re-export facade) → features/*.py (canonical math)
├── tsdb.py → daily OHLCV, treasury, FX, commodities, VIX
└── marquee.py → SPX IV surface, VVIX
```

### Chunk Store (`data/chunk_store.py`) — L1/L2 Tick Data

**Source:** GS pytickclient (Chunk Store REST API). Returns raw tick-level data.

| Function | What It Fetches |
|----------|----------------|
| `fetch_trades(symbol, start, end)` | L1 trade ticks: `{price, size}` per tick |
| `fetch_trades_batch(symbol, dates, batch_size=5)` | Multi-day batch: returns `dict[date, DataFrame]` |
| `fetch_quotes(symbol, start, end)` | L1 BBO: `{bid_price, ask_price, bid_size, ask_size}` |
| `fetch_depth(start, end, levels=5)` | L2 order book depth (E-mini only, up to 5 levels) |

**Key implementation details:**
- **Thread-safe lazy init:** `_ensure_session()` uses double-checked locking to call `pyslang.start()` once
- **E-mini contract roll:** `_resolve_es_symbol(date)` maps dates to correct front-month contract (H=Mar, M=Jun, U=Sep, Z=Dec)
- **Exponential backoff:** `_chunk_query_with_timeout()` retries with increasing delays on failure
- **Batch grouping:** `_group_contiguous_dates()` groups sorted dates into contiguous runs for efficient multi-day API calls
- **Parallel fetch:** `fetch_trades_batch` uses ThreadPoolExecutor for concurrent sub-batch fetching

**Fields used:**

```python
L1_FIELDS = ["TRDPRC_1", "TRDVOL_1", "ASK", "BID", "ASKSIZE", "BIDSIZE"]
L2_FIELDS = [f"{side}{i}" for side in ["BID", "ASK"] for i in range(1, 6)]
           + [f"{side}SIZE{i}" for side in ["BID", "ASK"] for i in range(1, 6)]
```

### TSDB (`data/tsdb.py`) — Daily Data

**Source:** GS `TSDBSymbol` API (gs_quant_internal). No pyslang needed.

| Function | Data Returned |
|----------|--------------|
| `fetch_daily_ohlcv(symbols, start, end)` | Open, High, Low, Close, Volume per symbol/date |
| `fetch_treasury_yields(start, end, tenors)` | 2y/5y/10y/30y Treasury yields |
| `fetch_fx_rates(start, end, pairs)` | USD/JPY, EUR/USD daily rates |
| `fetch_commodity_prices(start, end, symbols)` | CL (crude), GC (gold) daily prices |
| `fetch_vix(start, end)` | VIX daily close |
| `fetch_vix_futures(start, end, n_contracts=3)` | Front 3 VIX futures (VX1/VX2/VX3) |
| `fetch_spx_index(start, end, fields)` | S&P 500 OHLCV |

**Ticker-to-RIC mapping:** Internal `_ticker_to_ric()` maps 34 universe symbols to Reuters Instrument Codes. Contract roll logic handles commodity futures (CL, GC) and VIX futures month codes.

### Marquee (`data/marquee.py`) — IV Surface

**Source:** GS Marquee ERDVOL_PERCENT_STANDARD dataset (via `gs_quant` DataSetAPI).

| Function | Data Returned |
|----------|--------------|
| `fetch_iv_surface(start, end, tenors, strikes)` | Full IV surface (multi-index: date × tenor) |
| `fetch_atm_iv(start, end, tenors)` | ATM IV by tenor (1m, 2m, 3m, 6m, 1y) |
| `fetch_skew(start, end, tenors)` | 25-delta put-call IV spread by tenor |
| `fetch_vvix(start, end)` | VIX-of-VIX daily close (from TSDBSymbol) |

**Constants:** `_ATM_STRIKE = 1.0`, `_SKEW_STRIKES = (0.75, 1.25)`, default tenors `['1m','2m','3m','6m','1y']`.

### Trading Calendar (`data/trading_calendar.py`)

**Source:** pandas `bdate_range` minus NYSE holidays.

```python
class _NYSEHolidayCalendar(AbstractHolidayCalendar):
    # 10 holidays: New Year, MLK, Presidents', Good Friday, Memorial,
    # Juneteenth, July 4, Labor Day, Thanksgiving, Christmas
```

`get_trading_days(start, end) -> list[date]` returns all valid NYSE trading days.

### RV Panel Builder (`data/rv_panel.py`) — The Orchestrator

This is the primary data pipeline entry point. It transforms raw ticks into a Pipeline-ready daily DataFrame.

**Full signature:**
```python
def build_rv_panel(
    symbol: str,              # Must be in SYMBOL_UNIVERSE (34 symbols)
    start_date: date,
    end_date: date,
    freq: str = "5min",       # Bar sampling frequency
    min_ticks: int = 100,     # Minimum ticks per day (filter threshold)
    cache_dir: Path | None = None,   # Parquet cache directory
    progress=None,            # Rich progress handle
    max_workers: int = 4,     # Parallel fetch threads
    batch_size: int = 5,      # Days per API call
    checkpoint_interval: int = 50,   # Save cache every N days
    timeout_s: float = 120.0, # API timeout
    retries: int = 2,         # Retries per failed call
) -> pd.DataFrame
```

**Algorithm:**
1. Validate symbol in universe
2. Get NYSE trading days via `get_trading_days()`
3. Load parquet cache (if exists)
4. Determine missing days (days not yet in cache)
5. **Phase A — Batch-Parallel Fetch:**
   - Group missing days into super-chunks (`batch_size × max_workers`)
   - Fetch via `fetch_trades_batch()` with ThreadPoolExecutor
   - Per-batch progress + ETA updates
6. **Phase B — Compute RV:**
   - For each fetched day: `compute_daily_rv_from_ticks(trades)` → 18 measures
   - Skip empty days (no ticks) or sparse days (< `min_ticks`)
   - Checkpoint save every `checkpoint_interval` days
7. Merge new records with cache, filter to requested date range
8. Save updated cache

**Performance features:**
- Multi-day batch API calls (~5x round-trip reduction)
- Parallel ThreadPoolExecutor fetch
- Per-day timing with rolling-average ETA
- Periodic checkpoint saves so interrupted runs resume
- Cache deduplication (only fetches days missing from cache)

**Additional function:**
```python
def enrich_panel_with_ohlcv(panel, symbol, start_date, end_date) -> pd.DataFrame:
    """Merge TSDB daily open/close into RV panel. Graceful on ConnectionError."""
```

### Resampling (`data/resample.py`)

Two functions that bridge ticks to daily measures:

**`resample_trades_to_bars(trades, freq='5min')`:**
1. Deduplicate timestamps (keep last = previous-tick convention)
2. Build regular grid from market_open to market_close at given frequency
3. Reindex tick prices onto grid with forward-fill (previous-tick interpolation)
4. Backfill any leading NaNs
5. Compute log returns: `log(P_t / P_{t-1})`
6. Returns DataFrame with columns: `price`, `log_return`

**`compute_daily_rv_from_ticks(trades, freq='5min')`:**

Orchestrates ALL daily measure computations in one call:

```python
# Step 1: Resample ticks → 5-min bars
bars = resample_trades_to_bars(trades, freq)
returns = bars["log_return"].dropna()

# Step 2: Core volatility measures from bar returns
rv = compute_realized_variance(returns)        # Sum of squared returns
rq = compute_rq(returns)                       # Realized quarticity
bpv = compute_bpv(returns)                     # Bipower variation
semivars = compute_semivariances(returns)      # RS+, RS-

# Step 3: Jump detection from core measures
jump_test = detect_jumps(rv, bpv, rq, n_obs)  # BNS z-test
j_var = compute_jump_variation(rv, bpv, jump_test["jump_indicator"])
c_var = compute_continuous_variation(rv, j_var)

# Step 4: Noise-robust estimators from tick-level log prices
tick_log_prices = np.log(trades["price"].values)
rk_value = realized_kernel(tick_log_prices)    # Parzen-kernel RV
gap = noise_gap(rk_value, rv)                  # (RK - RV_5min) / RV_5min

# Step 5: Lee-Mykland intraday jump detection + signed jumps
lm_result = lee_mykland_test(returns, local_window=min(156, n_obs-1))
signed_jumps = compute_signed_jumps(returns, lm_result["is_jump"])

# Step 6: Higher moments
moments = compute_realized_moments(returns)    # Skewness, kurtosis
```

**Output (18 fields per day):**

| Field | Formula | Source |
|-------|---------|--------|
| `rv` | $\sum r_i^2$ | Layer 0 |
| `log_rv` | $\log(RV)$ | Layer 0 |
| `rq` | $(N/3)\sum r_i^4$ | Layer 0 |
| `bpv` | $(\pi/2)\sum|r_i||r_{i-1}|$ | Layer 1 |
| `rs_positive` | $\sum r_i^2 \cdot \mathbf{1}(r_i > 0)$ | Layer 1 |
| `rs_negative` | $\sum r_i^2 \cdot \mathbf{1}(r_i < 0)$ | Layer 1 |
| `jump_stat` | BNS z-statistic | Layer 1 |
| `jump_indicator` | 1 if z > Φ⁻¹(0.999), else 0 | Layer 1 |
| `continuous_variation` | $\max(RV - J^2, 0)$ | Layer 1 |
| `jump_variation` | $\max(RV - BPV, 0) \cdot \mathbf{1}_{\text{jump}}$ | Layer 1 |
| `j_positive` | $\sum r_i^2 \cdot \mathbf{1}(r_i>0, \text{jump})$ | Layer 1 |
| `j_negative` | $\sum r_i^2 \cdot \mathbf{1}(r_i<0, \text{jump})$ | Layer 1 |
| `realized_skewness` | $\sqrt{N}\cdot\bar{r^3}/\bar{r^2}^{3/2}$ | Layer 1 |
| `realized_kurtosis` | $N \cdot \bar{r^4}/\bar{r^2}^2$ | Layer 1 |
| `rk` | Parzen-kernel realized kernel | Noise-robust |
| `noise_gap` | $(RK - RV_{5m})/RV_{5m}$ | Noise-robust |
| `n_ticks` | Raw tick count for the day | Metadata |
| `n_bars` | 5-min bar count for the day | Metadata |

### Measures Facade (`data/measures.py`)

Re-export file that narrows coupling. All canonical implementations live in `features/*.py`:

```python
from volforecast.features.asymmetry import (compute_bpv, compute_continuous_variation,
    compute_jump_variation, compute_realized_moments, compute_semivariances,
    compute_signed_jumps, detect_jumps, lee_mykland_test)
from volforecast.features.har import compute_realized_variance, compute_rq
from volforecast.features.noise_robust import noise_gap, realized_kernel
```

---

## 12. Feature Engineering — Layer 0: HAR Core

#### `compute_realized_variance(intraday_returns: pd.Series) -> float`

#### `compute_log_rv_features(rv_series: pd.Series, date) -> dict`

Computes HAR's signature multi-horizon log-RV features:

$$\log(\overline{RV}_t^{(d)}) = \log(RV_t)$$
$$\log(\overline{RV}_t^{(w)}) = \log\left(\frac{1}{5}\sum_{j=0}^{4} RV_{t-j}\right)$$
$$\log(\overline{RV}_t^{(m)}) = \log\left(\frac{1}{22}\sum_{j=0}^{21} RV_{t-j}\right)$$

Returns: `{log_rv_d, log_rv_w, log_rv_m}`

#### `compute_rq(intraday_returns: pd.Series) -> float`

Realized Quarticity — measures variability of volatility:

$$RQ_t = \frac{N}{3}\sum_{i=1}^{N} r_{t,i}^4$$

Used in HARQ as a measurement-quality indicator: high RQ = unreliable RV estimate.

#### `compute_harq_features(rv_series, rq_series, date) -> dict`

Full HARQ feature set (Bollerslev et al. 2016):

Returns: `{log_rv_d, log_rv_w, log_rv_m, sqrt_rq_d, rq_rv_interaction}`

Where `rq_rv_interaction = sqrt(RQ_d) × log(RV_d)`.

#### `build_har_design_matrix(rv_series, rq_series=None, include_rq_interaction=False) -> pd.DataFrame`

Vectorized rolling computation of the full design matrix.

- Computing weekly/monthly in variance space before log transform (correct per Corsi 2009)
- All features shifted by 1 to prevent look-ahead bias
- First 21 rows are NaN (minimum history for monthly window)

### `HARCoreLayer` (registered as `"har_core"`)

`.compute(daily_data: pd.DataFrame) -> pd.DataFrame`

1. Calls `build_har_design_matrix()` using daily_data's `rv` and `rq` columns
2. Adds `sqrt_rq_d` as standalone column (for tree model splits)
3. Adds `overnight_return = log(open_t / close_{t-1}).shift(1)` if OHLCV columns present

---

## 13. Feature Engineering — Layer 1: Asymmetric Volatility

**File:** `features/asymmetry.py`
**Registry key:** `"asymmetry"`
**Status:** Fully implemented

### Functions

#### `compute_semivariances(intraday_returns: pd.Series) -> dict`

Patton & Sheppard (2015): separate upside vs downside volatility.

$$RS_t^+ = \sum_{i=1}^{N} r_{t,i}^2 \cdot \mathbf{1}(r_{t,i} > 0)$$
$$RS_t^- = \sum_{i=1}^{N} r_{t,i}^2 \cdot \mathbf{1}(r_{t,i} < 0)$$
$$\text{signed\_jump} = RS^+ - RS^-$$

Returns: `{rs_positive, rs_negative, signed_jump}`

#### `compute_bpv(intraday_returns: pd.Series) -> float`

Bipower Variation (Barndorff-Nielsen & Shephard 2004) — jump-robust integrated variance:

$$BPV_t = \frac{\pi}{2} \sum_{i=2}^{N} |r_{t,i}| \cdot |r_{t,i-1}|$$

Under no-jump conditions, BPV consistently estimates integrated variance.

#### `compute_realized_tripower_quarticity(intraday_returns: pd.Series) -> float`

RTQ — used for the variance of the BNS jump test statistic:

$$RTQ = N \cdot \mu_{4/3}^{-3} \sum_{i=3}^{N} |r_i|^{4/3} |r_{i-1}|^{4/3} |r_{i-2}|^{4/3}$$

where $\mu_{4/3} = 2^{2/3} \Gamma(7/6) / \Gamma(1/2)$.

#### `detect_jumps(rv, bpv, rq, n_obs, alpha=0.999) -> dict`

BNS Jump Test — tests whether realized variance exceeds bipower variation beyond what noise allows:

$$Z_t = \frac{RV_t - BPV_t}{\sqrt{\theta \cdot RQ_t / N}}$$

where $\theta = (\pi^2/4 + \pi - 5) \approx 0.609$.

Jump detected if $Z > \Phi^{-1}(\alpha)$ (default: one-sided at 99.9%).

Returns: `{z_stat, critical_value, jump_indicator}`

#### `compute_jump_variation(rv, bpv, jump_indicator) -> float`

$$J_t^2 = \max(RV_t - BPV_t, 0) \cdot \mathbf{1}_{\text{jump},t}$$

Clamped to zero (can't have negative jump variation). Only non-zero on detected jump days.

#### `compute_continuous_variation(rv, jump_variation) -> float`

$$C_t = \max(RV_t - J_t^2, 0)$$

The "smooth" component of realized variance after removing jumps.

#### `lee_mykland_test(intraday_returns, local_window=156, alpha=0.01) -> pd.DataFrame`

Lee-Mykland (2008) intraday jump detection — identifies which specific returns within a day are jumps.

**Algorithm:**
1. For each return $r_i$, estimate local volatility $\hat{\sigma}_i$ from BPV over a window of $K$ surrounding returns (excluding current)
2. Standardize: $L_i = r_i / \hat{\sigma}_i$
3. Compare $|L_i|$ to Gumbel extreme-value threshold:
   - $C_n = \sqrt{2\log n}$
   - $\text{threshold} = C_n - \frac{\log\pi + \log\log n}{2C_n}$
4. Flag as jump if $|L_i| > \text{threshold}$

Returns DataFrame with columns: `return, test_stat, threshold, is_jump, jump_size, jump_sign`

Default `local_window=156` ≈ 2 hours at 5-min frequency.

#### `compute_signed_jumps(intraday_returns, jump_flags) -> dict`

Partitions Lee-Mykland-detected jumps by direction:

$$J_t^+ = \sum_{i=1}^{N} r_i^2 \cdot \mathbf{1}(r_i > 0) \cdot \mathbf{1}(\text{jump}_i)$$
$$J_t^- = \sum_{i=1}^{N} r_i^2 \cdot \mathbf{1}(r_i < 0) \cdot \mathbf{1}(\text{jump}_i)$$

**Predictive rationale:** Negative jumps predict higher future volatility (leverage effect at the intraday level).

Returns: `{j_positive, j_negative}`

#### `compute_realized_moments(intraday_returns) -> dict`

Amaya, Christoffersen, Jacobs & Vasquez (2015) realized higher moments:

$$RSK_t = \sqrt{N} \cdot \frac{\frac{1}{N}\sum r_i^3}{\left(\frac{1}{N}\sum r_i^2\right)^{3/2}}$$

$$RKU_t = N \cdot \frac{\frac{1}{N}\sum r_i^4}{\left(\frac{1}{N}\sum r_i^2\right)^2}$$

Returns: `{realized_skewness, realized_kurtosis}`

#### `build_asymmetry_features(intraday_returns, rv, rq) -> dict`

Convenience function that computes all Layer 1 features for a single day in one call.

Returns 9 keys: `{rs_positive, rs_negative, signed_jump, bpv, jump_stat, jump_indicator, continuous_variation, jump_variation, n_obs}`

### `AsymmetryLayer` (registered as `"asymmetry"`)

`.compute(daily_data: pd.DataFrame) -> pd.DataFrame`

Produces lagged log-transformed features at d/w/m horizons:
- `log_rs_positive_d/w/m` — log semivariance (positive)
- `log_rs_negative_d/w/m` — log semivariance (negative)
- `log_bpv_d/w` — log bipower variation
- `log_jump_variation_d` — log jump variation
- `log_continuous_variation_d/w` — log continuous variation
- `signed_return_d` — lagged daily return (leverage asymmetry proxy)

All features shifted by 1 for forecasting (no look-ahead).

---

## 14. Feature Engineering — Noise-Robust Estimators

**File:** `features/noise_robust.py`
**Registry key:** `"noise_robust"`
**Status:** Fully implemented

These are computed from **tick-level log prices** (not 5-min bars) and serve as features alongside 5-min RV — not target replacements (per Liu et al. 2015).

### Functions

#### `realized_kernel(log_prices, bandwidth=None) -> float`

Barndorff-Nielsen, Hansen, Lunde & Shephard (2008). Uses Parzen flat-top kernel:

$$RK = \sum_{h=-H}^{H} k\left(\frac{h}{H+1}\right) \hat\gamma_h$$

where $\hat\gamma_h = \sum_{i=|h|+1}^{n} (r_i)(r_{i-|h|})$ and $k(x)$ is the Parzen kernel:

$$k(x) = \begin{cases} 1 - 6x^2 + 6x^3 & 0 \le x \le 0.5 \\ 2(1-x)^3 & 0.5 < x \le 1 \\ 0 & x > 1 \end{cases}$$

Optimal bandwidth: $H \propto n^{3/5}$. Rate: $n^{-1/4}$.

#### `tsrv(log_prices, slow_scale=None) -> float`

Two-Scales RV (Zhang 2005). Bias-corrected subsampled estimator:

$$TSRV = \overline{RV}_{slow} - \frac{\bar{n}}{n} RV_{all}$$

where $\overline{RV}_{slow}$ averages over $K$ subsampled grids.

Optimal slow scale: $K \propto n^{2/3}$.

#### `pre_averaged_rv(log_prices, block_length=None) -> float`

Jacod, Li, Mykland, Podolskij & Vetter (2009). Pre-averages prices with triangular weights before computing RV:

$$\overline{Y}_i = \sum_{j=0}^{L-1} g(j/L) \Delta_{i+j} Y$$

where $g(x) = \min(x, 1-x)$ (triangular weight).

Optimal block: $L \propto \sqrt{n}$.

#### `volatility_signature_plot_data(log_prices, frequencies=None) -> pd.DataFrame`

Computes subsampled RV at multiple frequencies for diagnostic visualization:
- Default frequencies: [1, 2, 5, 10, 15, 30, 60, 120, 300] seconds
- Flat signature → noise negligible
- Increasing at high frequency → noise dominates

#### `noise_gap(rk_value, rv_5min) -> float`

Liquidity/noise intensity proxy:

$$\text{noise\_gap} = \frac{RK - RV_{5m}}{RV_{5m}}$$

Large gap → more microstructure noise → RV less reliable → model should downweight.

### `NoiseRobustLayer` (registered as `"noise_robust"`)

`.compute(daily_data: pd.DataFrame) -> pd.DataFrame`

Builds lagged log features from pre-computed noise-robust columns:
- `log_rk_d` — daily log realized kernel
- `log_rk_w` — weekly average log RK
- `noise_gap_d` — daily noise gap
- `noise_gap_w` — weekly average noise gap

---

## 15. Feature Engineering — Shared Utilities

### `features/transforms.py`

#### `safe_log(series, min_value=1e-20)`

$$\text{safe\_log}(x) = \log(\max(x, 10^{-20}))$$

Prevents $-\infty$ on zero values. Used throughout all log-RV computations.

#### `lagged_log_features(series, name, windows=[5, 22], min_value=1e-20) -> pd.DataFrame`

Produces the standard HAR-style multi-horizon feature set:
- `log_{name}_d` = safe_log(series).shift(1) — daily, lagged
- `log_{name}_w` = safe_log(rolling_mean_5).shift(1) — weekly average, lagged
- `log_{name}_m` = safe_log(rolling_mean_22).shift(1) — monthly average, lagged

The `.shift(1)` ensures no look-ahead bias (feature at time $t$ uses only data ≤ $t-1$).

### `features/expansion.py`

#### `triple_expand(series: pd.Series, window: int = 20) -> pd.DataFrame`

Systematic expansion for gradient-boosted tree models (LightGBM):

- `{name}_level` — raw value (identity)
- `{name}_change` — first difference: $x_t - x_{t-1}$
- `{name}_zscore` — rolling z-score: $(x_t - \mu_{20d}) / \sigma_{20d}$

**Design rationale:** Trees handle redundancy naturally via feature splits. Pre-decorrelation not needed. This gives LightGBM 3× more split candidates per base feature.

Not wired into HAR-family OLS baselines (would cause collinearity).

---

## 16. Feature Engineering — Stubbed Layers 2-5

All layers below have complete API contracts (function signatures, docstrings, type hints, registry decorators) but raise `NotImplementedError`. They define the interface for future implementation.

### Layer 2: Options-Implied (`features/options.py`, registry: `"options"`)

| Function | Formula | Required Data |
|----------|---------|---------------|
| `compute_atm_iv(iv_surface, tenor)` | ATM IV from Marquee surface | `marquee.fetch_atm_iv()` |
| `compute_vrp(atm_iv, rv)` | $VRP = IV^2 - RV$ | ATM IV + realized vol |
| `compute_skew(iv_surface, tenor)` | $IV(25\delta P) - IV(25\delta C)$ | `marquee.fetch_skew()` |
| `compute_term_slope(iv_surface, short, long)` | $ATM_{3m} - ATM_{1m}$ | IV surface |
| `compute_butterfly(iv_surface, tenor)` | $0.5(IV_{25dP} + IV_{25dC}) - IV_{ATM}$ | IV surface |
| `build_options_features(...)` | All Layer 2 features | All above |

### Layer 3: Microstructure (`features/microstructure.py`, registry: `"microstructure"`)

| Function | Formula | Required Data |
|----------|---------|---------------|
| `compute_price_acceleration(mid, window=50)` | 2nd derivative of mid-price | E-mini L2 depth |
| `compute_obi(bid_sizes, ask_sizes, levels=5)` | $(\sum bid - \sum ask) / (\sum bid + \sum ask)$ | E-mini L2 depth |
| `compute_depth_ratio(bid_depth, ask_depth)` | $\log(bid/ask)$ | E-mini L2 depth |
| `compute_spread(bid, ask)` | Spread stats in bps (mean/median/std/max) | L1 BBO |
| `compute_vpin(trades, bucket_size, n_buckets)` | VPIN ∈ [0,1] | Trade flow |
| `build_microstructure_features(...)` | All Layer 3 features | L2 + trades |

### Layer 4: Cross-Asset (`features/cross_asset.py`, registry: `"cross_asset"`)

| Function | Formula | Required Data |
|----------|---------|---------------|
| `compute_treasury_slope(yields, short, long)` | 10y – 2y spread (bps) | `tsdb.fetch_treasury_yields()` |
| `compute_fx_vol(fx_rates, window=22)` | Annualized rolling RV of FX | `tsdb.fetch_fx_rates()` |
| `compute_commodity_vol(prices, window=22)` | Annualized rolling RV of commodities | `tsdb.fetch_commodity_prices()` |
| `compute_dy_spillover(rv_matrix, h=10, p=4)` | Diebold-Yilmaz total spillover (VAR FEVD) | Panel of RVs |
| `build_cross_asset_features(...)` | All Layer 4 features | All above |

### Layer 5: Calendar/Event (`features/calendar.py`, registry: `"calendar"`)

| Function | Description | Required Data |
|----------|-------------|---------------|
| `compute_fomc_proximity(date, fomc_dates)` | days_to_fomc, fomc_week flag | FOMC calendar |
| `compute_nfp_proximity(date, nfp_dates)` | days_to_nfp, nfp_week flag | NFP calendar |
| `compute_opex_proximity(date)` | days_to_opex (3rd Friday), opex_week flag | Calendar math |
| `compute_earnings_proximity(date, symbol, earn_dates)` | days_to_earnings, earnings_week flag | Earnings calendar |
| `build_calendar_features(...)` | All above + day_of_week + month | All above |

---

## 17. Raw Data Sources for Layers 0-1

This section details the complete data flow from raw source to computed feature — the "ground truth" of what actually runs today.

### Primary Data Source: Chunk Store L1 Trades

**What we fetch:** Trade-level price and size data for each trading day.

```python
# Source: pytickclient.query.chunk_query
# Fields: TRDPRC_1 (price), TRDVOL_1 (size)
# Database: "Eq" (equities, futures, rates)
# Time range: 09:30-16:00 ET (tz-aware, mandatory)
# Frequency: Irregular (every trade execution)
```

**Universe coverage:**

| Symbol Type | Count | Tick Rate | L1 Fields | L2 Fields |
|-------------|-------|-----------|-----------|-----------|
| Mega-cap equities | 30 | 679-281K ticks/day | ✓ | ✗ |
| ETFs (SPY, QQQ, IWM, DIA) | 4 | 50K-281K ticks/day | ✓ | ✗ |
| E-mini S&P 500 (ES) | 1 | ~488K ticks/day | ✓ | ✓ (5 levels) |

**Data characteristics:**
- Timestamps are irregular (trade-by-trade, microsecond precision)
- Multiple trades can share the same timestamp
- Market hours: 09:30-16:00 ET only (pre/post-market excluded)
- E-mini uses rolling front-month contracts (H/M/U/Z cycle)

### Transformation: Ticks → 5-Minute Bars

```
Raw ticks (irregular, ~5K-280K per day)
   ↓  resample_trades_to_bars(trades, freq="5min")
5-min bars (regular grid, 78 bars per day)
   ↓  Log returns: log(P_t / P_{t-1})
5-min log returns (77 returns per day)
```

**Previous-tick interpolation algorithm:**
1. Deduplicate: if multiple trades at same timestamp, keep last price
2. Build regular grid: 09:30, 09:35, 09:40, ..., 16:00 (78 points)
3. Merge tick prices with grid timestamps
4. Forward-fill: each bar gets the most recent trade price at or before it
5. Backfill leading NaNs (if first trade is after 09:30)
6. Compute log returns between consecutive bars

### Layer 0 Feature Computation from 5-Min Returns

| Feature | Input | Computation |
|---------|-------|-------------|
| `rv` | 77 log returns | $\sum_{i=1}^{77} r_i^2$ |
| `log_rv` | rv | $\log(rv)$ |
| `rq` | 77 log returns | $(77/3) \sum_{i=1}^{77} r_i^4$ |
| `log_rv_d` | Series of daily log_rv | $\log(RV_t)$, shifted by 1 |
| `log_rv_w` | Series of daily rv | $\log(\frac{1}{5}\sum_{j=0}^{4} RV_{t-j})$, shifted by 1 |
| `log_rv_m` | Series of daily rv | $\log(\frac{1}{22}\sum_{j=0}^{21} RV_{t-j})$, shifted by 1 |
| `sqrt_rq_d` | Series of daily rq | $\sqrt{RQ_t}$, shifted by 1 |
| `rq_rv_interaction` | rq, rv series | $\sqrt{RQ_t} \times \log(RV_t)$, shifted by 1 |
| `overnight_return` | OHLCV (from TSDB) | $\log(open_t / close_{t-1})$, shifted by 1 |

### Layer 1 Feature Computation from 5-Min Returns

| Feature | Input | Computation |
|---------|-------|-------------|
| `rs_positive` | 77 log returns | $\sum r_i^2 \cdot \mathbf{1}(r_i > 0)$ |
| `rs_negative` | 77 log returns | $\sum r_i^2 \cdot \mathbf{1}(r_i < 0)$ |
| `bpv` | 77 log returns | $(\pi/2) \sum_{i=2}^{77} |r_i| \cdot |r_{i-1}|$ |
| `jump_stat` | rv, bpv, rq, n_obs | BNS z-test statistic |
| `jump_indicator` | jump_stat vs Φ⁻¹(0.999) | Binary: 1=jump day, 0=no jump |
| `continuous_variation` | rv, jump_variation | $\max(RV - J^2, 0)$ |
| `jump_variation` | rv, bpv, jump_indicator | $\max(RV - BPV, 0) \cdot \mathbf{1}_{\text{jump}}$ |
| `j_positive` | Lee-Mykland flagged returns | $\sum r_i^2 \cdot \mathbf{1}(r_i > 0, \text{jump}_i)$ |
| `j_negative` | Lee-Mykland flagged returns | $\sum r_i^2 \cdot \mathbf{1}(r_i < 0, \text{jump}_i)$ |
| `realized_skewness` | 77 log returns | $\sqrt{N} \cdot \bar{r^3} / \bar{r^2}^{3/2}$ |
| `realized_kurtosis` | 77 log returns | $N \cdot \bar{r^4} / \bar{r^2}^2$ |

### Noise-Robust Feature Computation from Raw Tick-Level Log Prices

| Feature | Input | Computation |
|---------|-------|-------------|
| `rk` | log(price) vector (~5K-280K points) | Parzen-kernel weighted autocovariances, $H \propto n^{3/5}$ |
| `noise_gap` | rk, rv | $(RK - RV_{5m}) / RV_{5m}$ |

Note: These use the **full tick-level** log-price vector, not 5-min bars. This is because noise-robust estimators are designed to work optimally at the highest available frequency.

### OHLCV Enrichment (from TSDB, optional)

For the `overnight_return` feature, the RV panel can be enriched with daily OHLCV from TSDB:

```python
# Source: TSDBSymbol API (gs_quant_internal)
# Fields: open, high, low, close, volume (adjusted for dividends)
# Symbol format: eqpad_{RIC}@{field}.adj.allincdiv
# Example: eqpad_SPY.AQ@close.adj.allincdiv
```

`enrich_panel_with_ohlcv()` merges open/close columns for overnight return calculation. Handles partial overlap (NaN for missing days) and is fail-safe (returns panel unchanged on ConnectionError or missing RIC mapping for futures).

### Complete Data Pipeline: Source to Feature Matrix

```
pytickclient (Chunk Store)          TSDBSymbol (TSDB)
        ↓                                   ↓
L1 trades: price, size              Daily OHLCV: open, close
    (per day, per symbol)               (adjusted, all history)
        ↓                                   ↓
resample_trades_to_bars()           enrich_panel_with_ohlcv()
    5-min bars (78 per day)                 ↓
        ↓                           overnight_return feature
compute_daily_rv_from_ticks()
    18 daily scalar measures
        ↓
build_rv_panel() → parquet cache
        ↓
HARCoreLayer.compute()      → log_rv_d/w/m, sqrt_rq, rq_interaction, overnight_return
AsymmetryLayer.compute()    → log_rs±_d/w/m, log_bpv_d/w, log_jump_d, log_cont_d/w, signed_return
NoiseRobustLayer.compute()  → log_rk_d/w, noise_gap_d/w
        ↓
Pipeline.run() → design matrix X (all features concatenated)
        ↓
Model.fit(X_train, y_train)     [y = log(RV).shift(-h)]
Model.predict(X_test)           → OOS predictions
        ↓
evaluation.metrics.qlike()      → primary loss metric
```

### Cache Architecture

```
workspace/raw/
├── SPY_rv_daily.parquet    # RV panel: DatetimeIndex, 18 measure columns + symbol
├── AAPL_rv_daily.parquet
├── MSFT_rv_daily.parquet
└── ...                     # One file per symbol (34 total when fully populated)
```

Cache features:
- **Incremental:** Only fetches days not already in cache
- **Checkpoint-resumable:** Saves every 50 processed days
- **Deduplication:** Drops duplicate dates on merge (keep last)
- **Date filtering:** Returns only requested date range (cache may span wider)

---

## 18. Models

### HAR Family (7 models — all fully implemented)

**File:** `models/har_family.py`
**Pattern:** Template Method via `_BaseHAR` base class

| Model | Registry Key | Features Used | Formula |
|-------|-------------|---------------|---------|
| HAR | `"har"` | log_rv_d, log_rv_w, log_rv_m | $\hat{y} = \beta_0 + \beta_d x_d + \beta_w x_w + \beta_m x_m$ |
| HARQ | `"harq"` | HAR + sqrt_rq_d + rq_rv_interaction | HAR + measurement quality |
| SHAR | `"shar"` | log_rs_positive_d, log_rs_negative_d, log_rv_w, log_rv_m | Asymmetric HAR |
| HAR-J | `"har_j"` | HAR + log_jump_variation_d | HAR + jump component |
| HAR-CJ | `"har_cj"` | log_continuous_variation_d, log_jump_variation_d, log_rv_w, log_rv_m | Decomposed HAR |
| Ridge-HAR | `"ridge_har"` | All available features | L2-regularized (alpha=1.0) |
| Lasso-HAR | `"lasso_har"` | All available features | L1-regularized (alpha=0.01) |

**Shared interface:**
- `.fit(X: pd.DataFrame, y: pd.Series) -> Self` — NaN rows auto-dropped
- `.predict(X: pd.DataFrame) -> np.ndarray`
- `.summary -> dict[str, float]` — {intercept, feature: coef}
- `.save(path) / .load(path)` — joblib serialization

### LightGBM (`models/lightgbm.py`) — STUBBED

Custom QLIKE objective for gradient boosting:
- `QLIKEObjective.gradient(y_pred, y_true)` — $\partial$ QLIKE / $\partial \hat{y}$ in log-space
- `QLIKEObjective.hessian(y_pred, y_true)` — second derivative
- `LightGBMVolModel` — wraps lgb.train with early stopping, feature importance, Optuna hyperparameter tuning

### LSTM / TCN (`models/lstm.py`) — STUBBED

Sequence models for intraday E-mini data:
- `LSTMVolModel` — input shape: (n_samples, seq_len, input_dim), hidden_dim=64, 2 layers
- `TCNVolModel` — dilated causal convolutions, channels [64, 64, 32]

### Ensemble (`models/ensemble.py`) — STUBBED

4 strategies:
- `SimpleAverageEnsemble` — equal-weight mean
- `InverseQLIKEEnsemble` — weights inversely proportional to QLIKE
- `LinearBlendEnsemble` — constrained optimization (weights ≥ 0, sum = 1)
- `StackingEnsemble` — Ridge meta-learner on out-of-fold predictions

---

## 19. Evaluation Suite

### Implemented: Core Metrics (`evaluation/metrics.py`)

| Function | Formula | Status |
|----------|---------|--------|
| `qlike(y_true, y_pred, log_space=True)` | Log-space: $\text{mean}(e^{y-\hat{y}} - (y-\hat{y}) - 1)$ | ✅ |
| `mse(y_true, y_pred)` | $\text{mean}((y-\hat{y})^2)$ | ✅ |
| `mae(y_true, y_pred)` | $\text{mean}(|y-\hat{y}|)$ | ✅ |
| `r_squared(y_true, y_pred)` | $1 - SS_{res}/SS_{tot}$ (can be negative for bad models) | ✅ |
| `compute_all(y_true, y_pred)` | All 4 metrics in one dict | ✅ |
| `retransform_log_to_level(log_pred, var)` | Duan (1995): $\exp(\hat{y} + \sigma^2/2)$ | ✅ |
| `qlike_improvement_bps(baseline, model)` | $(Q_b - Q_m)/Q_b \times 10000$ | ✅ |

**QLIKE details:** Supports both log-space (train-space) and variance-space (final evaluation) modes. Input validation raises `ValueError` for NaN or mismatched lengths.

### Stubbed: Statistical Tests (`evaluation/statistical_tests.py`)

| Function | Purpose |
|----------|---------|
| `diebold_mariano_test(loss_1, loss_2, horizon)` | Tests H₀: equal predictive accuracy. HAC standard errors for h > 1. |
| `model_confidence_set(losses, alpha=0.10, n_bootstrap=10000)` | Hansen et al. (2011) MCS. Block bootstrap. Returns membership set. |
| `mincer_zarnowitz(y_true, y_pred)` | Efficiency regression: tests α=0, β=1 jointly. |
| `tournament_table(predictions, y_true, baseline)` | Multi-model QLIKE comparison with DM p-values + MCS membership. |

### Stubbed: Economic Value (`evaluation/economic_value.py`)

| Function | Purpose |
|----------|---------|
| `iv_rv_gap_signal(iv_forecast, rv_forecast)` | Signal ∈ {-1, 0, +1} based on IV vs RV gap |
| `delta_hedged_straddle_pnl(signal, rv, iv, spot)` | P&L of vol trading strategy |
| `vol_targeting_pnl(returns, vol_forecast, target=0.10)` | Position sizing by forecast |
| `compute_sharpe(returns)` | Annualized Sharpe ratio |
| `compute_max_drawdown(cum_returns)` | Peak-to-trough max drawdown |
| `economic_value_summary(...)` | Full economic report bundle |

---

## 20. Visualization & Reporting

### Working Standalone Plots (10 total)

**`src/plot_rv.py`** (5 plots):
1. RV time series + VIX overlay (dual axis, COVID shading)
2. RV distribution histogram (raw + log-RV)
3. ACF long-memory structure (with HAR lag markers at 1/5/22)
4. RV estimator comparison (Parkinson/GK/C2C/Yang-Zhang)
5. Rolling vol-of-vol and VRP

**`src/plot_har_forecast.py`** (5 plots):
6. Predicted vs actual RV time series (walk-forward OOS)
7. Scatter + Mincer-Zarnowitz regression (slope, intercept, R², 45° line)
8. Forecast error over time (over/under-predict shading, rolling 22d MAE)
9. Model comparison QLIKE bar chart (by horizon)
10. Cumulative QLIKE over time (regime degradation)

**Plot conventions:**
- matplotlib Agg backend (headless)
- 150 dpi PNG output
- Figure size: (14, 5) for time series
- Colors: steelblue, orange, red palette
- COVID shading: light red band Feb-Jun 2020
- Grid: alpha=0.3
- Output: `workspace/tmp/rv_plots/`

### Stubbed Visualization Module (`visualization/`)

8 functions stubbed across 3 files:
- `rv_plots.py`: time series, ACF, volatility signature plot
- `evaluation_plots.py`: QLIKE heatmap, forecast fan chart, MCS visualization
- `feature_plots.py`: feature importance bar, SHAP beeswarm

### HTML Report System (`reporting/`)

**Architecture:**
```
reporting/
├── html_report.py          # Orchestrator: load artifacts → render sections → assemble HTML
├── templates/base.html     # Jinja2 layout (IMPLEMENTED): Plotly CDN, nav, section loop
└── sections/               # 6 section renderers (ALL STUBBED)
    ├── summary.py          # Experiment metadata + metric table
    ├── forecast_vs_actual.py  # Plotly time-series
    ├── qlike_analysis.py   # Heatmap + improvement bars + rolling
    ├── statistical_tests.py   # DM matrix + MCS + MZ
    ├── economic_value.py   # Signal P&L + vol-targeting
    └── diagnostics.py      # Residuals, ACF, feature importance
```

The `base.html` template is fully implemented with:
- Plotly.js v2.35.0 CDN
- CSS custom properties (dark/light)
- Sticky nav with section anchor links
- Section iteration: `{% for section_id, section_html in sections %}`
- Footer with timestamp and version

---

## 21. Test Suite

### Overview

- **390 tests** across 20 test files
- **All synthetic data** — zero network dependency
- **Framework:** pytest with conftest.py shared fixtures
- **Markers:** `unit`, `slow` (custom)

### Test Files

| File | Tests | Covers |
|------|-------|--------|
| `test_features.py` | ~40 | HAR core + asymmetry functions |
| `test_expansion.py` | 11 | Triple expand utility |
| `test_transforms.py` | 18 | safe_log, lagged_log_features |
| `test_data_pipeline.py` | 14 | Resample + daily RV orchestration |
| `test_rv_panel.py` | 17 | RV panel builder + caching + OHLCV enrichment |
| `test_trading_calendar.py` | ~8 | NYSE holiday calendar |
| `test_tsdb.py` | ~10 | TSDB fetch functions (mocked) |
| `test_marquee.py` | ~8 | Marquee IV surface (mocked) |
| `test_models.py` | ~8 | HAR family fit/predict/save/load |
| `test_metrics.py` | ~23 | QLIKE, MSE, MAE, R², retransform |
| `test_cv_splitters.py` | ~20 | PurgedKFold, Expanding, Rolling, Blocked |
| `test_pipeline.py` | ~15 | Pipeline runner end-to-end |
| `test_cli_pipeline.py` | 15 | CLI ingest/train/evaluate integration |
| `test_config.py` | ~10 | YAML serialization, path resolution |
| `test_paths.py` | ~8 | resolve_project_root, path helpers |
| `test_registry.py` | ~8 | Model/feature registration |
| `test_protocols.py` | ~6 | Protocol conformance (isinstance checks) |
| `test_reporting.py` | ~5 | Report stub behavior |

### Core Fixtures (`tests/conftest.py`)

| Fixture | Description | Used By |
|---------|-------------|---------|
| `_skip_pyslang_session` (autouse) | Patches `_session_started=True` to prevent real pyslang subprocess | All tests |
| `synthetic_log_prices` | GBM log-prices: 23,400 ticks, σ=20%, seed=42 | Noise-robust tests |
| `synthetic_daily_rv_series` | 500 business days, AR(1) log-RV | Feature/model tests |
| `synthetic_predictions_actuals` | 200 pairs in RV space | Evaluation tests |
| `synthetic_tick_df` | Tick DataFrame via `make_synthetic_ticks()` | Data pipeline tests |
| `synthetic_ohlcv_df` | 252 days OHLCV | Feature tests |
| `gbm_log_prices` | 23,401 GBM prices (no jumps) | Noise-robust tests |
| `gbm_5min_returns` | Returns at 5-min frequency | Feature tests |

**Helper functions:**
```python
make_synthetic_ticks(trade_date, n_ticks=5000, price_start=450.0, sigma=0.0002, seed=42)
    → DataFrame[price, size] with tz-aware DatetimeIndex (US/Eastern)
```

### Mocking Strategy

1. **Network isolation:** `_skip_pyslang_session` autouse fixture prevents GS API calls
2. **Path isolation:** Tests use `monkeypatch` to override `resolve_project_root()` → `tmp_path`
3. **Data source mocking:** `@patch("volforecast.data.rv_panel.fetch_trades_batch")` returns synthetic ticks
4. **Calendar mocking:** `@patch("volforecast.data.rv_panel.get_trading_days")` returns fixed 5-day list
5. **Integration tests:** Pre-create directory structure in `tmp_path`, assert correct artifacts written

### Example Test Pattern (from `test_rv_panel.py`)

```python
@patch("volforecast.data.rv_panel.get_trading_days", return_value=_TEST_DAYS)
@patch("volforecast.data.rv_panel.fetch_trades_batch")
class TestBuildRvPanel:
    def test_returns_dataframe(self, mock_fetch, mock_cal):
        mock_fetch.side_effect = _mock_fetch_batch_factory(_TEST_DAYS)
        panel = build_rv_panel("SPY", date(2024, 1, 2), date(2024, 1, 8), max_workers=1)
        assert isinstance(panel, pd.DataFrame)
        assert len(panel) == 5
        expected_cols = {"rv", "log_rv", "rq", "bpv", ...}
        assert expected_cols.issubset(set(panel.columns))
```

---

## 22. Open Questions & Research Roadmap

### Data Understanding (Phase 3-4 — do next)

- [ ] What does the distribution of daily RV look like for our 34 symbols? Heavy tails? Log-normal?
- [ ] How does 5-min RV compare to tick-level RV on the same asset? (volatility signature plot validation)
- [ ] What's the autocorrelation structure of RV? Does the 1/5/22-day HAR decomposition fit?
- [ ] How do jumps show up in our data? Frequency, magnitude, which assets?
- [ ] What does the intraday volatility pattern look like? U-shape? How strong?
- [ ] How correlated is RV across our asset universe? Sector structure? Lead-lag?

### Feature Understanding (Phase 5)

- [ ] Does the leverage effect show up clearly? How asymmetric?
- [ ] Do RS+ and RS- differ in predictive power? (Patton-Sheppard: RS- dominates)
- [ ] Does RQ actually predict HAR residual size? (HARQ assumption)
- [ ] VIX-RV gap over time: stable or regime-dependent?
- [ ] Do overnight returns predict next-day RV?

### Methodological Questions

- [ ] How sensitive are QLIKE rankings to evaluation window? (regime dependency)
- [ ] Purged k-fold vs expanding-window in practice?
- [ ] COVID period handling: include, exclude, or separate regime?

### Ensemble Architecture (Phase 6)

- [ ] Feature stacking (LSTM embeddings → LightGBM) vs prediction blending?
  - **Decision:** Stacking at h=1/h=5, blending at h=22
  - **Rationale:** LSTM captures full-day microstructure state (~78 bars). At h=22 overfitting risk dominates.
- [ ] Does LSTM embedding add information beyond Layer 6 features (vol-of-vol, regime duration, Hurst)?
- [ ] Embedding stability across walk-forward retraining windows?
- [ ] Optimal embedding dimensionality: 16 vs 32 vs 64 vs PCA-reduced?

### Implementation Gaps for Next Phases

| Gap | Needed By Phase |
|-----|----------------|
| Real tick data connectivity (no more mocks) | Phase 3 |
| QLIKE custom objective for LightGBM (gradient + Hessian) | Phase 6 |
| Walk-forward evaluation as reusable module | Phase 4 |
| Statistical tests (DM, MCS, MZ) | Phase 6 |
| Economic value functions | Phase 7 |
| Report generation | Phase 6 |
| Regime-conditional QLIKE evaluation | Phase 5-6 |

### Key Research Findings (from journal)

1. **5-min RV is the right target** — Liu et al. (2015): noise-robust estimators rarely improve forecasts. Use them as features, not targets.
2. **LightGBM is the primary ML model** — Optiver 2021 Kaggle: trees dominated all top solutions. Deep learning only for intraday E-mini sequences.
3. **Feature engineering > model complexity** — The right features with a simple model beat complex models with bad features.
4. **COVID requires explicit handling** — No default; must justify include/exclude/separate per experiment.
5. **HAR long-memory is real** — ACF decay matches theoretical heterogeneous-agent structure (1d/5d/22d decomposition).

---

## Appendix A: Module Status Summary

| Module | Files | Functions | Implemented | Stubbed |
|--------|-------|-----------|-------------|---------|
| `data/` | 8 | ~30 | 30 | 0 |
| `features/` (L0-1 + noise) | 5 | 20 | 20 | 0 |
| `features/` (L2-5) | 4 | 24 | 0 | 24 |
| `models/har_family.py` | 1 | 7 models | 7 | 0 |
| `models/` (ML + ensemble) | 3 | 7 models | 0 | 7 |
| `evaluation/metrics.py` | 1 | 7 | 7 | 0 |
| `evaluation/` (tests + econ) | 2 | 10 | 0 | 10 |
| `pipeline/` | 1 | 2 | 2 | 0 |
| `cli/` | 10 | ~15 | 10 | 5 |
| `utils/` | 4 | ~15 | 15 | 0 |
| `visualization/` | 3 | 8 | 0 | 8 |
| `reporting/` | 8 | 8 | 1 (template) | 7 |
| **Total** | **50** | **~150** | **~92** | **~61** |

---

## Appendix B: Cross-Validation Splitters

| Splitter | Description | Parameters |
|----------|-------------|-----------|
| `PurgedKFoldCV` | K-fold with purge gap at train/test boundary | n_splits=5, purge_gap=5 |
| `BlockedKFoldCV` | Contiguous temporal blocks, no purge | n_splits=5 |
| `ExpandingWindowCV` | Walk-forward, expanding train set | min_train_size=500, test_size=63, step_size=63, purge_gap=5 |
| `RollingWindowCV` | Fixed rolling window | train_size=756, test_size=63, step_size=63, purge_gap=5 |

All implement `.split(X, y) -> Generator[tuple[np.ndarray, np.ndarray]]`. Custom implementations — no sklearn dependency.

---

## Appendix C: Constants

```python
TZ = pytz.timezone("America/New_York")
CHUNKDB = "Eq"
EQUITY_SYMBOLS = frozenset({"AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "BRK.B",
    "TSLA", "UNH", "JNJ", "JPM", "V", "XOM", "PG", "MA", "HD", "CVX", "MRK", "ABBV",
    "LLY", "PEP", "KO", "COST", "AVGO", "WMT", "MCD", "CSCO", "ACN", "TMO", "ABT"})
ETF_SYMBOLS = frozenset({"SPY", "QQQ", "IWM", "DIA"})
FUTURES_SYMBOLS = frozenset({"ES"})
SYMBOL_UNIVERSE = EQUITY_SYMBOLS | ETF_SYMBOLS | FUTURES_SYMBOLS  # 34 total
```

---

## Appendix D: Command Guide & Quickstart

### Setup (one-time)

Add the project root to your user PATH so `vol` works from any directory:

```powershell
[Environment]::SetEnvironmentVariable("PATH", "$([Environment]::GetEnvironmentVariable('PATH', 'User'));H:\ml-vol-estimator", "User")
```

Restart your terminal after running this. Without this step, you must use `.\vol` instead of `vol` in PowerShell.

### vol.cmd Subcommands

| Command | What it runs | Notes |
|---------|-------------|-------|
| `vol test [args]` | `pytest tests/` | Extra args forwarded (e.g. `-k`, `-v`, `--tb=short`) |
| `vol testlf` | `pytest --lf` | Re-run only last-failed tests |
| `vol run [args]` | `python -m volforecast` | Main CLI entry point |
| `vol lint` | `ruff check` | Non-destructive, reports issues only |
| `vol fmt` | `ruff format` | Auto-fixes formatting in place |
| `vol typecheck` | `mypy` | Static type checking |
| `vol sync` | `uv sync` | Creates venv if needed, installs all deps |
| `vol notebook` | `jupyter notebook` | Jupyter installed on-the-fly, not in project deps |
| `vol shell` | `python` | Interactive REPL with package importable |

### Pipeline Commands

```bash
# Run all 3 stages end-to-end:
vol run run-pipeline --config workspace/configs/baseline_har.yaml

# Or individually:
vol run ingest   --config workspace/configs/baseline_har.yaml
vol run train    --config workspace/configs/baseline_har.yaml
vol run evaluate --config workspace/configs/baseline_har.yaml
```

### Agentic Slash Commands

| Command | What it does | Persona |
|---------|-------------|---------|
| `/research` | Structured vol research on real data | VOL-RESEARCHER |
| `/feature` | Compute and validate a feature layer (0-6) | VOL-RESEARCHER |
| `/train` | Train RV model with proper CV and QLIKE | MODEL-BUILDER |
| `/evaluate` | QLIKE tournament, DM tests, MCS | EVAL-SENTINEL |
| `/backtest` | Economic value testing (IV-RV gap, vol-targeting Sharpe) | EVAL-SENTINEL |
| `/plan` | Decompose task, define acceptance criteria | STRATEGOS |
| `/execute` | Implement, verify, and finish | MODEL-BUILDER |
| `/debug` | Root-cause analysis and regression isolation | TRACEHOUND |
| `/review` | Severity-rated code and documentation review | EVAL-SENTINEL |
| `/learn` | Distill session knowledge into persistent memory | DATA-ORACLE |
| `/investigate` | Read-only research: find, explain, summarize | DATA-ORACLE |
| `/lightweight` | Quick answer, minimal context, no persona swaps | BUDGETEER |
| `/housekeep` | Lint, schema, and structural cleanup | OPERATIVE |
| `/cure` | Design-compliance audit (deeper than housekeep) | DOCTOR |
| `/bootup` | Session start: loads context, reads handoffs | (meta) |

### Choosing the Right Command

| I want to... | Use |
|-------------|-----|
| Understand a volatility topic or data pattern | `/research` |
| Find or explain something in the codebase | `/investigate` |
| Build or implement something | `/plan` then `/execute` |
| Implement a specific feature layer (0-6) | `/feature` |
| Fix a bug or diagnose unexpected behavior | `/debug` |
| Get a quick answer or make a small edit | `/lightweight` |
| Check quality of existing code or results | `/review` |
| Clean up lint, schema, or structural issues | `/housekeep` |
| Save what I learned this session | `/learn` |

### Typical Session Patterns

1. **Research Day:** `/bootup` → `/research` → `/learn`
2. **Build Day:** `/bootup` → `/plan` → `/execute` → `/review`
3. **Quick Task:** `/lightweight`
4. **Debug:** `/bootup` → `/debug` (diagnose only, no speculative fixes)
5. **Mixed Session:** `/bootup` → `/research` → `/plan` → `/execute`

---

## Appendix E: Architecture Debt Register

Audit performed 2026-05-11 against `src/volforecast/` (40+ Python files, 370 tests at audit time).

### P0 — Fix Before Phase 3 Real-Data Work

| # | Issue | Finding | Impact |
|---|-------|---------|--------|
| 1 | **No shared `safe_log` utility** | `har.py` logs raw RV without clipping; `asymmetry.py` and `noise_robust.py` use `.clip(lower=1e-20)`. If RV is exactly 0 (possible with sparse tick data), `har.py` produces `-inf`. | Latent bug that surfaces on real illiquid data |
| 2 | **Duplicated log/lag/rolling pattern** | Three feature layers independently implement the same transformation: take a daily series, compute lagged d/w/m rolling averages, log-transform, align with `.shift(1)`. Windows `5` and `22` are hardcoded in each file. ~50 lines of duplicated transformation code. | Every new feature layer will copy-paste this pattern |

### P1 — Fix During Next Refactor

| # | Issue | Finding | Impact |
|---|-------|---------|--------|
| 3 | **5 dead re-export shims** | `data/ingest.py`, `evaluation/evaluate.py`, `models/train.py`, `pipeline/notebook.py`, `pipeline/research.py` exist solely to re-export from `cli/`. Zero in-repo importers found. | Cognitive overhead, false impression of logic in wrong modules |
| 4 | **Dual-path constant access** | `config.py` re-exports all 17 constants from `constants.py` as top-level names. Some modules import from `config`, others from `constants`. Two public entry points for the same data. | Grep-based auditing unreliable |
| 5 | **Duplicated test files** | `test_evaluation.py` and `test_metrics.py` both test `evaluation/metrics.py` with overlapping assertions (QLIKE, MSE, MAE, R-squared, `compute_all`). | Maintenance confusion about where to add new tests |
| 6 | **Duplicated `_make_synthetic_ticks` helper** | Same helper function copy-pasted in `test_data_pipeline.py` and `test_rv_panel.py`; `conftest.py` already has a nearly identical `synthetic_tick_df`. | If tick schema changes, three places need updating |
| 7 | **Monolithic `__main__.py`** | 93 lines of `run-pipeline` orchestration that belongs in `pipeline/runner.py`. Two divergent execution modes: inline orchestration vs. `cli/*.py` forwarding. | Single most coupled module in the package (imports from 6 subpackages) |

### P2 — Fix When Implementing Sequence Models

| # | Issue | Finding | Impact |
|---|-------|---------|--------|
| 8 | **VolModel protocol too narrow** | `VolModel.fit(X: pd.DataFrame, y: pd.Series)` assumes tabular input. LSTM/TCN need `np.ndarray` with 3D sequences. Registry stores `dict[str, type]` (untyped), so no check catches this mismatch. Requesting "lstm" or "tcn" in YAML config will fail at runtime. | Runtime failure with no static warning |
| 9 | **Inconsistent zero-floor protection** | `har.py` logs raw (relies on RV > 0 validation), `asymmetry.py` and `noise_robust.py` clip. No shared `safe_log`. | Different layers produce different outputs for edge-case inputs |

### P3 — Cleanup When Convenient

| # | Issue | Finding | Impact |
|---|-------|---------|--------|
| 10 | **Loose top-level scripts** | `plot_har_forecast.py` (200 lines manually rebuilding HAR), `inspect_rv.py`, `plot_rv.py` with hardcoded paths. Duplicate package logic. | Confusion for anyone reading the repo |
| 11 | **Stale `__pycache__` files** | `.pyc` files for renamed/deleted modules (`baselines.cpython-314.pyc`, `lightgbm_model.cpython-314.pyc`, `time_series.cpython-314.pyc`). | Negligible, but signals incomplete cleanup |
| 12 | **`data/measures.py` facade** | Re-exports 12 functions from `features/` so `data/resample.py` only needs one import. Creates circular conceptual dependency (`data/` imports from `features/`). | Working as designed but architecturally odd. Needs docstring explaining intent. |
| 13 | **CV splitter structural duplication** | `PurgedKFoldCV`/`BlockedKFoldCV` share fold logic; `ExpandingWindowCV`/`RollingWindowCV` share walk-forward logic. | Manageable at 4 classes; extract shared helpers when adding a 5th+ variant |

### What's Actually Good

- Registry + decorator pattern: clean plugin architecture for models and feature layers
- Protocol definitions: right abstraction level (just needs tightening)
- Constants centralization: one file, pure data, no logic
- Feature layer consistency: all layers follow `compute(daily_data) -> DataFrame`
- HAR family `_BaseHAR`: proper base class factoring for 7 model variants
- CLI/pipeline separation: composable ingest/train/evaluate steps
- Persistence layer: structured experiment output with config snapshot

---

## Appendix F: Data-Access Recipes & Known Gaps

### Environment Preamble

All queries below require this session initialization:

```python
import goldmansachs.pyslang as pyslang
pyslang.start(subprocess=True, object_database="Equity")

from gs_quant.session import GsSession
GsSession.use()

import numpy as np, pandas as pd, pytz
from datetime import date, datetime

TZ = pytz.timezone("America/New_York")
```

### Recipe 1: Fetch L1 Trade Ticks (Single Day)

```python
from volforecast.data.chunk_store import fetch_trades
trades = fetch_trades("AAPL", date(2026, 5, 4), date(2026, 5, 4))
# Returns: DataFrame with columns [price, size], tz-aware DatetimeIndex, ~100K rows
```

**Direct pytickclient version:**

```python
from pytickclient import query
st = TZ.localize(datetime(2026, 5, 4, 9, 30, 0))
et = TZ.localize(datetime(2026, 5, 4, 16, 0, 0))
raw = query.chunk_query(["AAPL.OQ"], st, et, "Eq",
      fields=["TRDPRC_1", "TRDVOL_1", "ASK", "BID", "ASKSIZE", "BIDSIZE"])
df = pd.DataFrame(raw)
```

### Recipe 2: Compute All Daily RV Measures (End-to-End)

```python
from volforecast.data.resample import compute_daily_rv_from_ticks
measures = compute_daily_rv_from_ticks(trades)
# Returns dict: rv, log_rv, rq, bpv, rs_positive, rs_negative,
#   jump_stat, jump_indicator, continuous_variation, jump_variation,
#   rk, noise_gap, n_ticks, n_bars
```

### Recipe 3: Multi-Day RV Panel

```python
import exchange_calendars as xcals
nyse = xcals.get_calendar("XNYS")
sessions = nyse.sessions_in_range("2026-01-02", "2026-05-04")

records = []
for session in sessions:
    d = session.date()
    trades = fetch_trades("AAPL", d, d)
    if trades.empty:
        continue
    measures = compute_daily_rv_from_ticks(trades)
    measures["date"] = d
    records.append(measures)

daily = pd.DataFrame(records).set_index("date")
# ~84 rows x 14 cols (one row per trading day)
```

### Recipe 4: TSDB Daily Data (Two Methods)

**Slang wrapper (requires pyslang):**

```python
from _lib_eq1d_brazil_tsdb_fns import eq1d_brazil__tsdb
close = eq1d_brazil__tsdb("AAPL.OQ", "close", date(2015, 1, 2), date(2026, 5, 4))
volume = eq1d_brazil__tsdb("AAPL.OQ", "volume", date(2015, 1, 2), date(2026, 5, 4))
```

**GS Quant TSDBSymbol (no pyslang):**

```python
from gs_quant_internal.tsdb import TSDBSymbol
data = TSDBSymbol("eqpad_AAPL.OQ@close.adj.allincdiv").get_data(
    start="2015-01-02", end="2026-05-04")
```

### Recipe 5: SPX IV Surface (Marquee)

```python
from gs_quant.data import Dataset
ds = Dataset("EDRVOL_PERCENT_STANDARD")
iv_data = ds.get_data(start=date(2026, 4, 24), end=date(2026, 5, 4), bbid="SPX")
# ~3,549 rows for 10 days. Columns: tenor, relativeStrike, impliedVolatility, ...
```

**Single-stock IV (use `ric`, not `bbid`):**

```python
ds = Dataset("EDRVOL_PERCENT")
iv_aapl = ds.get_data(start=date(2026, 5, 1), end=date(2026, 5, 9), ric=".AAPL.O")
```

### Recipe 6: Cross-Asset Data

```python
# Treasury prices (note: prices, not yields)
ust_2y  = eq1d_brazil__tsdb("US2YT=RR", "close", date(2015, 1, 2), date(2026, 5, 4))
ust_10y = eq1d_brazil__tsdb("US10YT=RR", "close", date(2015, 1, 2), date(2026, 5, 4))
slope = ust_10y - ust_2y  # Price-based proxy

# FX
usdjpy = eq1d_brazil__tsdb("usd/jpy", "close", date(2015, 1, 2), date(2026, 5, 4))

# VIX
vix = eq1d_brazil__tsdb(".VIX", "close", date(2015, 1, 2), date(2026, 5, 4))

# VIX futures term structure
vx1 = eq1d_brazil__tsdb("VXM26", "settle", date(2026, 1, 2), date(2026, 5, 4))
vx2 = eq1d_brazil__tsdb("VXN26", "settle", date(2026, 1, 2), date(2026, 5, 4))
term_slope = vx2 - vx1  # contango > 0, backwardation < 0
```

### Recipe 7: E-mini L2 Depth

```python
from volforecast.data.chunk_store import fetch_depth
depth = fetch_depth(date(2026, 5, 4), date(2026, 5, 4), levels=3)
# ~488K rows: BEST_BID1, BEST_ASK1, BEST_BSIZ1, BEST_ASIZ1, ...
```

### RIC Naming Rules

| Exchange | Pattern | Example |
|----------|---------|---------|
| NASDAQ | `TICKER.OQ` | `AAPL.OQ` |
| NYSE | `TICKER.N` | `JPM.N` |
| Arca | `TICKER.P` | `SPY.P` |
| CME futures | `XXMYY` | `ESM26` |
| E-mini L2 | `XXMYY` + `m` | `ESM26m` |
| Marquee ric | `.TICKER.O` | `.AAPL.O` |

### TSDB Symbol Reference

| Data | TSDB Symbol Pattern |
|------|---------------------|
| Equity close | `eqpad_AAPL.OQ@close` |
| Adjusted close | `eqpad_AAPL.OQ@close.adj.allincdiv` |
| Volume | `eqpad_AAPL.OQ@volume` |
| Log return | `eqpad_AAPL.OQ@return.log` |
| S&P 500 | `eqpad_.SPX@close` |
| VIX | `eqpad_.VIX@close` |
| E-mini settle | `eqpad_ESM26@settle` |
| Treasury price | `eqpad_US10YT=RR@close` |
| Single-stock IV | `mqd_AAPL.OQ@impliedVolatility.EDRVOL_PERCENT` |

### Known Data Gaps

| Data | Status | Impact | Workaround |
|------|--------|--------|-----------|
| Broker trade attribution | Structurally impossible (SEC regs) | No broker HHI/flow features | Volume imbalance from anonymous ticks |
| L2 depth for equities | Not in Chunk Store | No equity LOB features | E-mini L2 as index proxy; equities L1 only |
| Pre-computed VWAP/spread (`td.*`) | Not for US equities | Must compute manually | Raw `tick.trd`/`tick.bid`/`tick.ask` confirmed |
| Micro E-mini (MES) | Empty in Chunk Store | — | Use full E-mini (ES) |
| Fed Funds rate (FFTQ) | Not in TSDB | No short-rate feature | 2Y Treasury as proxy |
| EUR/USD, GBP/USD | Not in TSDB | Limited FX features | Marquee FXIVOL works for EURUSD |
| Dollar Index (DXY) | Not in TSDB | No USD breadth feature | Compute from component pairs |
| Generic front futures (CLv1, GCv1) | Not in TSDB | Must roll manually | Use specific contracts (CLM26, GCM26) |
| Single-stock IV | **RESOLVED** | Per-name IV-RV spread available | `Dataset("EDRVOL_PERCENT").get_data(ric=".AAPL.O")` |
| Earnings calendar | No automated source | Earnings proximity feature manual | Hard-code for 30 names |

---

## Appendix G: Dependency Manifest

From `src/pyproject.toml`. Build system: **hatchling**.

### Core Dependencies

| Package | Version Constraint | Role |
|---------|-------------------|------|
| numpy | >=1.21 | Array operations, all computation |
| pandas | >=1.4 | DataFrames, time-series indexing |
| scipy | >=1.7 | Statistical distributions, optimization |
| statsmodels | >=0.13 | OLS in HAR models, statistical tests |
| scikit-learn | >=1.0 | CV splitters, Ridge/Lasso, metrics |
| pytz | >=2026.2 | NYSE timezone handling |
| pyarrow | >=24.0.0 | Parquet I/O for daily RV panels |
| pyyaml | >=6.0 | Experiment config files |
| matplotlib | >=3.5 | Static plots (RV time series, diagnostics) |
| plotly | >=5.18 | Interactive HTML plots |
| rich | >=13.0 | Console progress bars, styled output |
| jinja2 | >=3.1 | HTML report templates |
| tqdm | >=4.60 | Simple progress bars (used in data loops) |
| pypdf | >=6.10.2 | PDF reading utility |

### Optional: GPU

| Package | Version Constraint | Role |
|---------|-------------------|------|
| lightgbm | >=3.3 | Gradient boosting with QLIKE custom objective |
| torch | >=1.12 | LSTM/TCN sequence models |

Install with: `uv sync --extra gpu`

### Dev Dependencies

| Package | Version Constraint | Role |
|---------|-------------------|------|
| pytest | >=8.0 | Test runner |
| pytest-cov | >=4.0 | Coverage reporting |
| mypy | >=1.5 | Static type checking |
| ruff | >=0.4 | Linting and formatting |
| pre-commit | >=3.5 | Git hook management |

### Tool Configuration (in pyproject.toml)

| Tool | Key Settings |
|------|-------------|
| ruff | `target-version = "py310"`, `line-length = 100`, selects `E,F,W,I,UP` |
| mypy | `python_version = "3.10"`, `ignore_missing_imports = true`, `check_untyped_defs = true` |
| pytest | `testpaths = ["tests"]`, `addopts = "--cov=volforecast --cov-report=term-missing"`, `cache_dir = "../workspace/tmp/.pytest_cache"` |

### Python Version

`requires-python = ">=3.10,<3.13"` — Uses Python 3.10+ features (match statements, `X | Y` union types). Upper bound excludes 3.13 for ecosystem compatibility.

### Entry Point

`volforecast = "volforecast.__main__:main"` — Allows `python -m volforecast` or the installed `volforecast` console script.

---

## Appendix H: Test Optimization Guide

### Current State

- **390 tests**, all synthetic data, no network dependency
- Parallel execution via **pytest-xdist** (`-n auto` in addopts)
- Last-failed shortcut: `vol testlf` (runs `pytest --lf`)
- Cache at `workspace/tmp/.pytest_cache` for cross-session re-run support

### Shared Fixtures (conftest.py)

Session-scoped fixtures avoid recreating expensive data each test:

| Fixture | Scope | What it provides |
|---------|-------|-----------------|
| `gbm_log_prices` | session | Synthetic GBM price series |
| `gbm_5min_returns` | session | 5-min log returns from GBM prices |
| `sample_config` | session | Pre-built pipeline `ExperimentConfig` |
| `sample_trades_df` | session | Synthetic trade DataFrame |
| `tmp_workspace` | function | Temporary directory, cleaned up after test |

### Markers

Registered in `pyproject.toml`:

| Marker | Purpose | Default Behavior |
|--------|---------|-----------------|
| `@pytest.mark.unit` | Fast tests using only synthetic data | Included in all runs |
| `@pytest.mark.slow` | Integration tests, real data stubs, or network | Included in all runs |

**Future plan:** Add `-m "not slow"` as default for quick dev runs once integration tests exist.

### Speed Tips

1. **Run targeted tests only:** `vol test -k test_har -v` — never run the full suite after a single change
2. **Use last-failed:** `vol testlf` — re-run only tests that failed in the previous run
3. **Parallel execution:** Already configured via `-n auto` (xdist); scales with CPU cores
4. **Session fixtures:** Use the shared fixtures in `conftest.py` instead of creating data per-test
5. **Coverage threshold:** Set low (`--cov-fail-under=10`) intentionally — allows running subsets without CI failure

### Remaining Optimization (TODO)

- Tag existing tests with `@pytest.mark.unit` and `@pytest.mark.slow` markers
- Add `-m "not slow"` to default `addopts` once slow tests exist
- Consolidate duplicated helpers (`_make_synthetic_ticks` appears in 2 test files and `conftest.py`)

---

*Document generated 2026-05-12. Reflects commit f3194aa on develop branch.*
