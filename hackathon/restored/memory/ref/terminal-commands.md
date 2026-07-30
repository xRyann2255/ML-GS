---
created: 2026-05-14
updated: 2026-05-19
tags: [terminal, cli, vol-cmd, python, environment]
status: active
relates:
  - ref/devtools.md
  - ref/python-setup.md
---

# Terminal Commands — Vol Project

**NEVER use raw `python`, `pytest`, `uv run`, or `ruff` directly.**

## Platform Detection

| Platform | Command | Notes |
|----------|---------|-------|
| **Windows** | `vol.cmd <cmd>` | Uses `H:\uv-env.cmd`, auto-activates venv |
| **Linux** | `./vol <cmd>` | Requires `uv` on PATH (via nix). `chmod +x` already set. |

Both wrappers handle env setup, cd to `src/`, and venv activation automatically. Run from any directory.

## Primary Command

```
vol run --config <yaml>
```

The YAML `mode` field determines what runs:

| mode | Behavior |
|------|----------|
| `pipeline` (default) | Ingest → Train → Evaluate |
| `tournament` | Multi-model QLIKE tournament + MCS/DM tests + dashboard |
| `ingest` | Data ingestion only |

### Overrides

| Flag | Purpose |
|------|---------|
| `--symbols SPY,AAPL` | Override YAML universe |
| `--skip-ingest` | Skip data fetch (pipeline mode) |
| `--workers 8` | Override thread count |

### Example Commands

```
vol run --config workspace/configs/tournament_multi21.yaml
vol run --config workspace/configs/baseline_har.yaml --skip-ingest
vol run --config workspace/configs/ingest_full_universe.yaml --symbols SPY,AAPL
```

## YAML Config Schema

```yaml
name: tournament_multi21      # experiment name
universe: [SPY, AAPL, ...]    # symbols
date_range: ["2015-01-02", "2024-12-31"]
horizons: [1, 5, 22]
feature_layers: [har_core, asymmetry]
model:
  name: har
  params: {}
cv:
  method: expanding_window
  purge_gap: 5
  train_size: 504
  test_size: 63
training_mode: pooled         # pooled | per_symbol
seed: 42
output_dir: data/models/tournament_multi21
tournament:
  models: [random_walk, historical_mean, ..., lasso_har]
  mcs_bootstrap: 10000
```

## Output

Every run prints an output summary at completion:
```
━━━ Output ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Dashboard:  H:\...\plots\tournament_dashboard.html
  Plots dir:  H:\...\plots
  Output dir: H:\...\data\models\tournament_multi21
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Other Commands

| Task | Command |
|------|---------|
| Show data status | `vol status` |
| Data integrity audit | `vol audit [--quiet] [--no-report]` |
| Run tests | `vol test [-k pattern] [-x] [-q] [--tb=short]` |
| Run a Python script | `vol shell path/to/script.py` |
| Python REPL | `vol shell` |
| Lint | `vol lint` |
| Format | `vol fmt` |
| Install deps | `vol sync` |
| Isolated exec | `vol exec <command> [args...]` |

## Linux-Specific Notes

- **`uv` must be on PATH.** Install via: `nix-env -iA nixpkgs.uv`
- **First run** auto-creates `.venv` via `uv sync` (resolves from `src/pyproject.toml`)
- **Skill tasks** use `.sh` wrappers (siblings of `.cmd` files). VS Code routes automatically via `"windows"` overrides in `.code-workspace`.
- **`run_task` works identically** on both platforms — VS Code handles dispatch.

## Terminal Isolation (Multi-Agent Safety)

**Problem:** `run_in_terminal(isBackground=false)` shares one persistent bash session. Multiple agents or rapid sequential calls see stale output from prior commands.

**Solution:** Always capture output to a unique file and read it via `read_file`.

### Pattern 1: `vol exec` (preferred)
```bash
./vol exec pytest tests/ -x -q
```
Prints `OUTPUT_FILE=<path>`. Read that file.

### Pattern 2: Manual redirect
```bash
_OUT="workspace/tmp/exec/test_$(date +%s).out"
./vol test -x -q > "$_OUT" 2>&1; echo "EXIT:$?" >> "$_OUT"
# Then: read_file on $_OUT
```

### Rules
1. Commands producing multi-line output (tests, lint, builds) MUST use file-based capture.
2. Quick read-only commands (`ls`, `cat`, `head`) can use terminal directly.
3. NEVER retry because "output looks stale" — redirect to file and read it.
4. Subagents MUST use unique filenames (include `$$` or `$(date +%s)` in path).
5. NEVER trust terminal buffer output when it shows content from a prior command.

---

## P1 Quick-Load Checklist

| Task type | Load these P1 files |
|-----------|---------------------|
| Python code | `ref/python-setup.md` + `ref/python-pyslang.md` |
| Data ingest/pipeline | `research/data-access.md` + `ref/python-chunk.md` + `ref/python-tsdb.md` |
| Feature engineering | `research/optimal-feature-set.md` + vol-project-ref feature chapter |
| Model training/eval | vol-learning-guide Ch16 + `research/evaluation-framework.md` |
| Slang script work | `slang/best-practices.md` + `slang/formatting.md` + `slang/lint-edit.md` |
| Git/MR | `ref/git-workflow.md` |

## Project State

<!-- Update when milestone changes. Source of truth: workspace/research/weekly-progress.md milestone table -->
**Current milestone:** M4 (Tournament) — 8 models x 3 horizons, DM p-values, MZ efficiency.
**Blocker:** h>1 target bug (spot RV instead of average). h=5/h=22 results invalid until fixed.
python -m volforecast tournament --symbols ... --models ... --horizons ... --training-mode pooled
python -m volforecast ingest --config <yaml>
python -m volforecast train --config <yaml>
python -m volforecast evaluate --config <yaml>
```

## Running standalone debug scripts

`vol shell ../workspace/tmp/my_script.py` — runs with full venv (volforecast + GS packages).

**Cwd caveat:** Inside the wrapper, cwd is `src/`. Scripts should use absolute paths for file I/O:

```python
from pathlib import Path
ROOT = Path(r"H:\ml-vol-estimator")
df = pd.read_parquet(ROOT / "data" / "raw" / "rv" / "SPY.parquet")
```

Or use the project's path resolver: `from volforecast.config import paths`

## What NOT to do

```powershell
# WRONG — these all fail or misbehave:
cmd /c "H:\uv-env.cmd && uv run python script.py"   # ignores project venv
python -m volforecast ingest ...                      # python not on PATH
cd src; pytest tests/ -k test_har                     # pytest not on PATH
```

## If vol.cmd is broken (Windows emergency only)

```powershell
cd H:\ml-vol-estimator\src
& .\.venv\Scripts\python.exe path\to\script.py
```

## If vol is broken (Linux emergency only)

```bash
cd /home/developer/ml-vol-estimator/src
source .venv/bin/activate
python path/to/script.py
```
