# ml-vol-estimator

ML realized volatility forecasting — signal discovery. Progressively enriches HAR-family baselines with microstructure, options-implied, and cross-asset features via gradient boosting to produce statistically significant QLIKE improvements that translate into a tradeable IV-RV gap signal.

**Timeline:** ~20-week internship, May–Sep 2026.

---

## Quick Start

1. Open `ml-vol-estimator.code-workspace` in VS Code.
2. Boot protocol loads automatically: `memory/person/user.md` + `memory/INDEX.md`.
3. Use `/bootup` to start a session — it reads the research journal and orients you.
4. Drive work with slash commands: `/research`, `/feature`, `/experiment`, `/backtest`.

See [AGENTS.md](AGENTS.md) for the full project spec, and [workspace/docs/user-manual.md](workspace/docs/user-manual.md) for all commands.

---

## CLI

The `vol` wrapper handles uv, PATH, and working directory internally.

### Wrapper Commands

```
vol test [args]               # pytest (extra args forwarded: -k, -v, --tb=short)
vol testlf [args]             # re-run last-failed tests only
vol run --config <yaml>       # primary entry point (see below)
vol status                    # show data ingestion manifest
vol lint                      # ruff check (read-only)
vol fmt                       # ruff auto-format
vol typecheck                 # mypy
vol sync                      # install/update deps
vol shell                     # REPL with volforecast importable
vol notebook                  # jupyter
vol help                      # usage
```

### Primary Command: `vol run --config <yaml>`

Every `vol run --config` invocation uses the tournament code path — even single-model configs produce ranked tables and an interactive Plotly HTML dashboard. The only special case is `mode: ingest` (data ingestion only).

Optional overrides: `--symbols SPY,AAPL` (override YAML universe), `--skip-ingest` (skip data fetch), `--workers 8` (thread count).

### Examples

```bash
# Single-model experiment (ingest + train + evaluate + dashboard)
vol run --config workspace/configs/baseline_har.yaml

# Tournament: 13 models compared with statistical tests
vol run --config workspace/configs/tournament_full_spy.yaml

# Skip ingestion (data already cached), subset of symbols
vol run --config workspace/configs/tournament_har_dev.yaml --skip-ingest --symbols SPY,AAPL

# Ingest only
vol run --config workspace/configs/ingest_full_universe.yaml --workers 8

# Tests
vol test -k test_har -v
vol testlf --tb=short
```

See [workspace/docs/user-manual.md](workspace/docs/user-manual.md) for full argument reference and YAML config structure.

**One-time PATH setup** (so `vol` works from any directory):

```powershell
[Environment]::SetEnvironmentVariable("PATH", "$([Environment]::GetEnvironmentVariable('PATH', 'User'));H:\ml-vol-estimator", "User")
```

Restart terminal after running. Without this, use `.\vol` instead.

---

## Key Docs

| Doc | What |
|-----|------|
| [workspace/docs/data-audit.md](workspace/docs/data-audit.md) | Query recipes for every feature layer, universe, field reference |
| [workspace/docs/user-manual.md](workspace/docs/user-manual.md) | All slash commands, session patterns, troubleshooting |
| [workspace/research/feature-engineering-status.md](workspace/research/feature-engineering-status.md) | What's implemented vs stubbed, test counts |
| [workspace/research/weekly-progress.md](workspace/research/weekly-progress.md) | Current milestones (M0-M10), shipped/decided/learned/next |
| [workspace/research/research-journal.md](workspace/research/research-journal.md) | Session-by-session findings and decisions |

---

## Directory Structure

```
ml-vol-estimator/
├── AGENTS.md                  # Master project spec — constraints, skills, data, models
├── README.md                  # This file
├── vol                        # CLI wrapper — Linux (bash)
├── vol.cmd                    # CLI wrapper — Windows (handles uv, PATH, cwd)
├── data/                      # Cached data artifacts (parquet files, gitignored)
│   ├── raw/                   # Raw data by type: rv/, ohlcv/, iv_surface/, macro/, micro/
│   ├── processed/             # Derived feature matrices
│   ├── models/                # Trained model artifacts
│   └── external/              # External reference datasets
├── src/                       # Python package (volforecast)
│   ├── volforecast/
│   │   ├── cli/               # CLI entry points (run, ingest, progress)
│   │   ├── data/              # Data access (chunk_store, resample, tsdb, marquee)
│   │   ├── features/          # Feature layers (har, asymmetry, noise_robust, options, …)
│   │   ├── models/            # Model implementations (7 HAR baselines, LightGBM)
│   │   ├── evaluation/        # Metrics, statistical tests, tournament runner
│   │   ├── pipeline/          # Orchestration (feature build, train, evaluate)
│   │   ├── visualization/     # Plot functions (evaluation, RV, features)
│   │   └── reporting/         # Report generation
│   └── tests/                 # 720+ automated tests
├── memory/                    # CoALA knowledge files — tiered (P0–P3), loaded per task
│   ├── INDEX.md               # Memory map and priority lookup table
│   ├── person/                # User identity
│   ├── research/              # 25 distilled research cards (feature layers, evaluation, data access)
│   ├── slang/                 # Slang language reference (19 files)
│   ├── ref/                   # Technical reference (22 files: Python, SecDB, git, auth)
│   └── sys/                   # GS platform memory (9 files: Canvas, EngHub, eTask)
├── workspace/                 # Build artifacts, config, docs, research
│   ├── configs/               # Experiment YAML configs (baseline_har, tournament_har_dev, …)
│   ├── research/              # Research journal, weekly progress, open questions, 24 topic files
│   ├── docs/                  # User manual, data audit, architecture audit, vol-project-ref/
│   ├── lint/                  # 17 structural lint scripts (design_lint, validate_memory, …)
│   ├── notebooks/             # Jupyter exploration notebooks
│   ├── bin/                   # Shell utilities (secexpr-safe.cmd)
│   ├── config/                # App configuration (user.json)
│   └── tmp/                   # Ephemeral outputs — not committed (TTL-managed)
├── personas/                  # 18 reasoning styles (vol-researcher, model-builder, eval-sentinel, …)
├── skills/                    # 49 executable capabilities (7 ML + 42 infrastructure/Slang/SecDB)
├── workflows/                 # 20 orchestration workflows (research, execute, debug, review, …)
├── policy/                    # 13 global constraints (ML constraints, execution protocol, …)
└── .github/prompts/           # 48 slash commands for Copilot Chat
```

---

## Key Constraints

| Constraint | Rule |
|---|---|
| **Primary metric** | QLIKE (quasi-likelihood loss) — never MSE alone |
| **CV protocol** | Purged/blocked k-fold or expanding-window walk-forward — never random k-fold |
| **Training space** | Always log-RV, never raw RV |
| **Feature priority** | Feature engineering > model complexity |
| **COVID handling** | Feb–Jun 2020 requires explicit regime handling per experiment |

---

## Data Universe

- **34 symbols:** 30 mega-cap equities + 4 ETFs + E-mini S&P 500
- **11.3 years** of history (~2,800 daily obs/symbol)
- **Tick data:** L1 for all, L2 depth for E-mini (~4M ticks/day)
- **IV surface:** SPX only (Marquee ERDVOL)
- **Cross-asset:** Treasury yields, FX, commodities

---

## Model Architecture

**Baselines:** HAR, HARQ, SHAR, HAR-J, HAR-CJ, Ridge-HAR, Lasso-HAR
**ML:** LightGBM (QLIKE custom objective), LSTM/TCN (intraday E-mini sequences)
**Ensemble:** Prediction-level blending of HAR + LightGBM + LSTM
**Target:** 30–80 bps QLIKE improvement with economic value via IV-RV gap signal
