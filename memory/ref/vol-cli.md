---
created: 2026-06-12
updated: 2026-06-22
tags: [vol, cli, terminal, wrapper, reference]
status: active
priority: P1
relates:
  - ref/terminal-commands.md
---

# vol CLI Reference

> This file mirrors `./vol help`. If commands seem wrong or missing, run `./vol help` to validate.

## Core (daily use)

| Command | Description |
|---------|-------------|
| `vol run --config <yaml>` | Run experiment (tournament + dashboard + metrics) |
| `vol run --config <yaml> --skip-ingest` | Same but skip data fetch (use cached parquets) |
| `vol run --config <yaml> --tune` | Enable Optuna HPO |
| `vol run --config <yaml> --force-retrain` | Force retraining even if cached |
| `vol test [args]` | Run pytest (`-x -q` for quick, `-k name` to filter) |
| `vol testlf` | Re-run last-failed tests only |
| `vol lint` | Ruff check (read-only) |
| `vol fmt` | Ruff format (auto-fix) |
| `vol exec <cmd...>` | Run any command with output captured to file (prints `OUTPUT_FILE=<path>`) |
| `vol bg <cmd...>` | Fire-and-forget: fully detached, returns immediately. Poll OUTPUT_FILE for `EXIT_CODE=` |
| `vol jobs` | List running/completed background jobs |

## Data & Ingestion

| Command | Description |
|---------|-------------|
| `vol status` | Show ingestion manifest (cached vs planned) |
| `vol audit` | Data integrity audit, updates manifest |
| `vol ingest-edrvol` | Fetch per-symbol IV + VVIX from TSDB |
| `vol refresh-ohlcv` | Re-fetch split-adjusted OHLCV into RV parquets |
| `vol backfill-rk` | Backfill realized kernel + noise_gap from ticks |

## Experiment Management

| Command | Description |
|---------|-------------|
| `vol experiments` | List all trials with QLIKE numbers |
| `vol new-experiment --base <yaml> --name <name> [--set k=v]` | Create config from baseline |
| `vol compare --experiment <id> --baseline <id>` | Compare trials (bps + DM stats) |

## Environment

| Command | Description |
|---------|-------------|
| `vol sync` | Install/update dependencies |
| `vol shell [script]` | Python REPL or run script with volforecast importable |
| `vol typecheck` | Mypy type checking |

## Common Patterns

```bash
# Run experiment (most common)
./vol run --config workspace/configs/trial_009_iv_fix_tree_expansion.yaml --skip-ingest

# Quick test cycle
./vol test -x -q -k test_lightgbm

# Isolated execution (signal-safe — immune to terminal SIGINT)
./vol exec pytest tests/ -x -q
# Then read_file on the OUTPUT_FILE path it prints

# Fire-and-forget (long-running jobs — survives terminal death)
./vol bg python -m volforecast ingest-ticks --symbols AAPL
# Returns immediately. Poll OUTPUT_FILE for EXIT_CODE= line.

# Check background job status
./vol jobs

# Create new experiment from baseline
./vol new-experiment --base workspace/configs/trial_009_iv_fix_tree_expansion.yaml --name trial_014 --set cv.train_size=1260
```

## Gotchas

- **Multiprocessing atexit pollution:** LightGBM pooled training spawns worker processes that inherit Python atexit hooks. Guard sweep/monkey-patch scripts with `if os.getpid() != _MAIN_PID: return`.
- **`vol bg` cwd is `src/`:** All `vol exec` and `vol bg` commands run from the `src/` directory. Use absolute paths for scripts outside `src/`.

## Terminal Isolation Notes

`./vol exec` and `./vol bg` handle signal isolation internally. Do NOT use `setsid`, `nohup`, `&`, `disown`, subshells, or `trap` — these are fragile and break output capture.

- Use `./vol bg` for any long-running job (>30s).
- Check status with `./vol jobs` (RUNNING/DONE).
- After reading an output file from `workspace/tmp/exec/`, delete it.
- "Terminal is blocked" or KeyboardInterrupt → use `./vol exec`. Do NOT retry.
