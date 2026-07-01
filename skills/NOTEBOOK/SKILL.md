---
name: NOTEBOOK
description: "Jupyter notebook workflow for ML vol forecasting exploration and visualization. USE FOR: creating structured notebooks, interactive data exploration, visualization, presentation-ready figures. DO NOT USE FOR: production feature building (use FEATURE_BUILD), model training (use MODEL_TRAIN), bulk data pulls (use DATA_INGEST)."
---

# NOTEBOOK — Jupyter Notebook Workflow

> **Purpose:** Create, manage, and run Jupyter notebooks for interactive exploration and visualization in the ML vol forecasting project. Enforces cell structure conventions and visualization standards.

**Out of scope:** Production feature building (use FEATURE_BUILD), model training at scale (use MODEL_TRAIN), bulk data ingestion (use DATA_INGEST).

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `NOTEBOOK` |
| **Scope** | Jupyter notebook creation and management |
| **Inputs** | JSON args: notebook name, kernel, template |
| **Outputs** | Jupyter notebook (.ipynb) in `workspace/notebooks/` |
| **Authority** | Create/edit notebooks, run cells interactively |

## When to Use

- Creating a new exploration notebook for a research session
- Interactive data visualization (distributions, time series plots)
- Prototyping feature computations before moving to production modules
- Creating presentation-ready figures for capstone
- Quick ad-hoc analysis that doesn't warrant a full skill invocation

## When NOT to Use

- Building production features — prototype here, then implement in FEATURE_BUILD
- Training models at scale — use MODEL_TRAIN
- Running the evaluation suite — use EVALUATE

## Cell Structure Conventions

Every notebook should follow this structure:

### Standard Template

```
Cell 1: [Markdown] Title + purpose + date
Cell 2: [Code] Imports and environment setup
Cell 3: [Markdown] Data loading section header
Cell 4: [Code] Load data (from workspace/tmp/data or via DATA_INGEST)
Cell 5: [Markdown] Analysis section header(s)
Cell 6+: [Code] Analysis cells (one logical step per cell)
Cell N-1: [Markdown] Findings summary
Cell N: [Code] Save artifacts (figures, DataFrames) to workspace/tmp/
```

### Cell Conventions

1. **One logical operation per cell** — don't combine data loading with computation
2. **Markdown headers before each section** — makes the notebook self-documenting
3. **Print shapes and dtypes** after loading data — catches issues early
4. **Save figures explicitly** — `fig.savefig("workspace/tmp/figures/...")` in addition to inline display
5. **Log-RV space** — all RV analysis in log space unless explicitly exploring raw distributions

## Visualization Standards

### Figure Conventions

- **Size:** `figsize=(12, 6)` for time series, `(8, 6)` for distributions
- **DPI:** 150 for exploration, 300 for presentation
- **Color palette:** Use `seaborn` defaults or a consistent 5-color palette
- **Labels:** Always label axes, include units where applicable
- **Title:** Descriptive, include date range and symbol
- **Grid:** Light grid on by default (`plt.grid(alpha=0.3)`)

### Standard Plot Types

| Plot | Use Case |
|------|----------|
| Time series | RV over time, feature evolution |
| Histogram / KDE | Feature distributions, log-RV normality check |
| Scatter | Feature vs target correlation |
| Heatmap | Correlation matrix, feature importance across folds |
| Box plot | Cross-symbol feature comparison |
| ACF/PACF | Autocorrelation analysis for RV persistence |

## Args File Format

Write JSON to `workspace/tmp/notebook_args.json`:

```json
{
  "name": "har_baseline_exploration",
  "kernel": "python3",
  "template": "research",
  "out_dir": "workspace/notebooks",
  "out_file": "workspace/tmp/notebook_out.txt"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Notebook filename (without .ipynb extension) |
| `kernel` | No | Jupyter kernel (default: `python3`) |
| `template` | No | Template to use: `research`, `feature_exploration`, `model_comparison`, `blank` |
| `out_dir` | No | Directory for notebook (default: `workspace/notebooks`) |
| `out_file` | No | Path for creation log |

## Templates

### `research` — General Research Session

Pre-populated cells for: imports, data loading, exploratory analysis, findings summary.

### `feature_exploration` — Feature Layer Investigation

Pre-populated cells for: imports, feature loading, distribution analysis, correlation with target, temporal stability, cross-symbol comparison.

### `model_comparison` — Model Result Visualization

Pre-populated cells for: imports, load predictions, QLIKE computation, tournament table, residual analysis, time-varying performance.

### `blank` — Empty Notebook

Just the title cell and imports.

## Import Boilerplate

Standard imports for ML vol notebooks:

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Project imports
from ml_vol_estimator.features import har, asymmetry
from ml_vol_estimator.evaluation import metrics

# Settings
plt.style.use('seaborn-v0_8-whitegrid')
pd.set_option('display.max_columns', 50)
pd.set_option('display.float_format', '{:.6f}'.format)

DATA_DIR = Path('workspace/tmp/data')
FIG_DIR = Path('workspace/tmp/figures')
FIG_DIR.mkdir(exist_ok=True)
```

## Task-Based Execution

1. **Write args file** to `workspace/tmp/notebook_args.json`
2. **Run task:** `run_task("notebook", workspaceFolder: "h:\ml-vol-estimator")`
3. **Read output:** Check `workspace/tmp/notebook_out.txt` for notebook path

Note: For interactive notebook work, prefer using the VS Code notebook tools (`run_notebook_cell`, `edit_notebook_file`) directly after the notebook is created.

## Links

- memory/research/project-design.md — notebook sequence and presentation plan
- workspace/docs/data-audit.md — data query cookbook with runnable snippets for notebook data loading
