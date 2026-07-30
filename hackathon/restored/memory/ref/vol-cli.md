---
created: 2026-06-12
updated: 2026-07-27
tags: [vol, cli, terminal, wrapper, reference]
status: active
priority: P1
relates:
  - ref/terminal-commands.md
---

# vol CLI Reference

> This file mirrors `./vol help` (34 commands — regenerated 2026-07, Plan 03; `lint_vol_parity.py` enforces parity from Plan 04). If commands seem wrong or missing, run `./vol help` to validate.

Descriptions are copied verbatim from the help heredoc in the [`vol`](../../vol) script. Sub-flag rows are indented under their parent command exactly as the heredoc shows them.

## Core (daily use)

| Command | Description |
|---------|-------------|
| `vol run --config <yaml>` | Run experiment (tournament + dashboard + metrics) |
| &nbsp;&nbsp;`--skip-ingest` | Skip data fetch, use cached parquets |
| &nbsp;&nbsp;`--tune` | Enable Optuna hyperparameter tuning |
| &nbsp;&nbsp;`--no-tune` | Disable tuning (override YAML) |
| &nbsp;&nbsp;`--n-trials N` | Number of Optuna trials |
| &nbsp;&nbsp;`--force-retrain` | Force retraining even if cached results exist |
| &nbsp;&nbsp;`--symbols X,Y` | Override YAML universe |
| &nbsp;&nbsp;`--parallel-models N` | Run N models concurrently |
| `vol test [args]` | Run pytest (serial), SKIPPING @pytest.mark.slow. Default agent inner-loop. Run `test-all` before committing. |
| `vol test-all [args]` | Run the full pytest suite (serial) |
| `vol testlf [args]` | Re-run only last-failed tests |
| `vol lint` | Ruff check (read-only) |
| `vol fmt` | Ruff format (auto-fix) |
| `vol exec <cmd...>` | Run command with output captured (signal-isolated). Prints `OUTPUT_FILE=<path>`. Read that file for results. |
| `vol bg <cmd...>` | Fire-and-forget: launch detached, return immediately. Poll OUTPUT_FILE for `EXIT_CODE=` sentinel when done. |
| `vol jobs` | List running/completed background jobs |

## Data & Ingestion

| Command | Description |
|---------|-------------|
| `vol status` | Show ingestion manifest (what's cached vs planned) |
| `vol audit [-q] [--no-report]` | Data integrity audit, updates manifest |
| `vol ingest-edrvol` | Fetch per-symbol IV + VVIX from TSDB edrvol |
| &nbsp;&nbsp;`--start/--end` | Date range (default 2015-01-02 to 2025-01-03) |
| &nbsp;&nbsp;`--symbols X,Y` | Comma-separated (default: all 25 with EDRVOL RIC) |
| &nbsp;&nbsp;`--force` | Re-fetch even if cache covers range |
| `vol ingest-ohlcv` | Fetch split-adjusted daily OHLCV from TSDB eqpad |
| &nbsp;&nbsp;`--start/--end` | Date range (default 2015-01-02 to 2024-12-31) |
| &nbsp;&nbsp;`--symbols X,Y` | Comma-separated (default: all equities + ETFs) |
| &nbsp;&nbsp;`--force` | Re-fetch even if cache covers range |
| `vol ingest-ticks` | Fetch tick data from Chunk Store, build daily RV panels |
| &nbsp;&nbsp;`--start/--end` | Date range (default 2015-01-02 to 2024-12-31) |
| &nbsp;&nbsp;`--symbols X,Y` | Comma-separated (default: full universe, 34 symbols) |
| &nbsp;&nbsp;`--force` | Re-fetch even if cache covers range |
| &nbsp;&nbsp;`--recompute` | Re-derive from cached bars (no network fetch) |
| &nbsp;&nbsp;`--mode bars\|ticks` | bars=fast (no RK), ticks=full RK + noise_gap |
| `vol ingest-iv` | Fetch per-symbol IV (unified: TSDB + optional Marquee) |
| &nbsp;&nbsp;`--start/--end` | Date range (default 2015-01-02 to 2025-01-03) |
| &nbsp;&nbsp;`--symbols X,Y` | Comma-separated (default: all with EDRVOL RIC) |
| &nbsp;&nbsp;`--force` | Re-fetch even if cache covers range |
| &nbsp;&nbsp;`--skip-market-wide` | Skip VVIX and market-wide signals |
| &nbsp;&nbsp;`--marquee` | Also fetch SPX deep surface from Marquee |
| `vol ingest-xasset` | Fetch cross-asset data (rates, FX vol, credit, commodity) |
| &nbsp;&nbsp;`--start/--end` | Date range (default 2015-01-02 to 2024-12-31) |
| &nbsp;&nbsp;`--groups X,Y` | Comma-separated (rates,fx_vol,credit,commodity) |
| &nbsp;&nbsp;`--force` | Re-fetch even if cache covers range |
| `vol ingest-corr` | Fetch SPX implied/realized correlation from Marquee EDR_INDEX |
| &nbsp;&nbsp;`--start/--end` | Date range (default 2010-01-02 to yesterday) |
| &nbsp;&nbsp;`--force` | Re-fetch even if cache covers range |
| `vol ingest-micro` | Fetch LeeReady signed-volume bars, build VPIN/OFI + 10s sequences |
| &nbsp;&nbsp;`--start/--end` | Date range (default 2015-01-02 to 2024-12-31) |
| &nbsp;&nbsp;`--symbols X,Y` | Comma-separated (default: full universe, 34 symbols) |
| &nbsp;&nbsp;`--force` | Re-fetch even if cache covers range |
| &nbsp;&nbsp;`--recompute` | Re-derive dailies from cached sequences (no network) |
| &nbsp;&nbsp;`--symbol-workers N` | Symbols to ingest concurrently (default 4) |
| &nbsp;&nbsp;`--batch-size N` | Trading days per API call (default 20) |
| `vol ingest-edrvs` | Fetch SPX 0DTE variance swap strike from Marquee EDRVS_EXPIRY |
| &nbsp;&nbsp;`--start/--end` | Date range (default 2022-05-01 to today) |
| &nbsp;&nbsp;`--force` | Re-fetch even if cache covers range |
| `vol ingest-vix-futures` | Fetch VIX futures continuous term structure (VX1/VX2/VX3) |
| &nbsp;&nbsp;`--start/--end` | Date range (default 2015-01-02 to yesterday) |
| &nbsp;&nbsp;`--force` | Re-fetch even if cache covers range |
| `vol ingest-gex` | Fetch SPX GEX (Gamma Exposure) from QSP OptionPrices |
| &nbsp;&nbsp;`--start/--end` | Date range (default 2015-01-02 to yesterday) |
| &nbsp;&nbsp;`--security-id ID` | QSP security identifier (default: 108105 for SPX) |
| &nbsp;&nbsp;`--force` | Re-fetch even if cache covers range |
| `vol refresh-ohlcv` | Re-fetch split-adjusted open/close into RV parquets |
| &nbsp;&nbsp;`--symbols X,Y` | Comma-separated (default: all cached) |
| &nbsp;&nbsp;`--dry-run` | Show corruption without fetching |
| &nbsp;&nbsp;`--force` | Re-fetch all, even if clean |
| `vol backfill-rk` | Backfill realized kernel + noise_gap from ticks |
| &nbsp;&nbsp;`--symbols X,Y` | Comma-separated (default: all cached) |
| &nbsp;&nbsp;`--dry-run` | Show NaN counts without fetching |

### Case-arm drift (not in help heredoc)

`vol` dispatches these arms but the help heredoc does not document them — verified 2026-07-27 against the live script. Descriptions cannot be copied verbatim; run `./vol <arm> --help` for the underlying `python -m volforecast <arm>` help text:

| Command | Note |
|---------|------|
| `vol ingest-allday` | Fetch SPX 0DTE mark Kvar (var-swap strike, pre-friction) from output.json execution data. |

## Experiment Management

| Command | Description |
|---------|-------------|
| `vol experiments` | List all trials from registry with QLIKE numbers |
| `vol new-experiment` | Create config from baseline |
| &nbsp;&nbsp;`--base <yaml>` | Baseline config to clone (required) |
| &nbsp;&nbsp;`--name <name>` | New experiment name (required) |
| &nbsp;&nbsp;`--set key=val` | Dot-notation override (repeatable) |
| &nbsp;&nbsp;`--force` | Overwrite existing config |
| `vol compare` | Compare two trials side-by-side (bps + DM stats) |
| &nbsp;&nbsp;`--experiment <id>` | Trial to evaluate (required) |
| &nbsp;&nbsp;`--baseline <id>` | Reference trial (required) |
| `vol forecast [args]` | Generate live RV forecast and IV-RV gap signal (LONG/SHORT/FLAT) |
| &nbsp;&nbsp;`--symbol <sym>` | Target symbol (default: SPY) |
| &nbsp;&nbsp;`--horizons <list>` | Forecast horizons, comma-separated (default: 1,5) |
| `vol kvar` | Compare GSVIVS signal results across cached IV sources |
| &nbsp;&nbsp;`--target <mode>` | both, same-day, or next-day (default: both) |
| &nbsp;&nbsp;`--edrvs-intraday-path <parquet>` | Optional raw EDRVS intraday parquet for 2-DTE rows |
| `vol cache-status` | List cached LSTM fold artifacts (per-fold training cache) |
| &nbsp;&nbsp;`--config <yaml>` | Filter to one experiment (default: all) |
| `vol cache-clear` | Delete cached LSTM fold artifacts |
| &nbsp;&nbsp;`--config <yaml>` | Clear one experiment's cache, OR |
| &nbsp;&nbsp;`--all` | Clear the entire fold cache root |
| &nbsp;&nbsp;`--yes` | Skip confirmation prompt |
| `vol dashboard` | Browse and download trial dashboards |
| &nbsp;&nbsp;`--trial <name>` | Skip picker, download directly by trial dir name |
| &nbsp;&nbsp;`--limit N` | Max dashboards to show (default: 30) |

## Presentation

| Command | Description |
|---------|-------------|
| `vol present` | Generate presentation HTML with swappable dashboard |
| &nbsp;&nbsp;`--dashboard-path` | Relative path to tournament_dashboard.html (required) |
| &nbsp;&nbsp;`--output` | Output path (default: workspace/presentation/presentation.html) |

## Environment

| Command | Description |
|---------|-------------|
| `vol sync` | Install/update dependencies (uv sync --frozen) |
| `vol shell [script]` | Python REPL or run script with volforecast importable |
| `vol typecheck` | Mypy type checking |
| `vol notebook` | Launch Jupyter notebook |
| `vol help` | Show this message |

`vol sync` and `vol notebook` remain Linux-only: `sync` drives `uv sync --frozen` against the Coder-workspace venv; `notebook` shells out to an externally-installed `jupyter` (AW-G8 residual caveat — the heredoc description is copied verbatim above).

## Common Patterns

```bash
# Run experiment (most common)
./vol run --config workspace/configs/trial_009_iv_fix_tree_expansion.yaml --skip-ingest

# Quick test cycle
./vol test -x -q -k test_lightgbm

# Isolated execution (for agents — avoids terminal collision)
./vol exec pytest tests/ -x -q
# Then read the OUTPUT_FILE path it prints

# Fire-and-forget (long-running, survives terminal death)
./vol bg python -m volforecast ingest-ticks --symbols AAPL
# Returns immediately. Poll OUTPUT_FILE for EXIT_CODE= line.

# Check background job status
./vol jobs

# Create new experiment from baseline
./vol new-experiment --base workspace/configs/trial_009_iv_fix_tree_expansion.yaml --name trial_014_test --set cv.train_size=1260
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

## Windows (S-A) subset — vol.cmd

`vol.cmd` (repo root) is the S-A dev-loop shim. It reproduces the sentinel protocol byte-compatibly with `./vol exec`/`bg` (prints `OUTPUT_FILE=<path>`, the file's last line is `EXIT_CODE=<rc>`). Descriptions are copied verbatim from the [`vol.cmd`](../../vol.cmd) `:do_help` block.

| Command | Description |
|---------|-------------|
| `vol.cmd test [args]` | pytest, skipping @pytest.mark.slow (mirror of ./vol test) |
| `vol.cmd test-all [args]` | full pytest suite |
| `vol.cmd testlf [args]` | re-run last-failed tests |
| `vol.cmd lint [args]` | ruff check . |
| `vol.cmd fmt [args]` | ruff format . |
| `vol.cmd typecheck [args]` | mypy volforecast/ |
| `vol.cmd exec <cmd...>` | run captured: prints OUTPUT_FILE=, file ends EXIT_CODE= |
| `vol.cmd bg <cmd...>` | fire-and-forget: poll OUTPUT_FILE for EXIT_CODE= sentinel |
| `vol.cmd jobs` | list background jobs (RUNNING/DONE by sentinel presence) |

Every other command: `vol.cmd` exits 2 with `GS Coder workspace only — run via ./vol on S-B`.
