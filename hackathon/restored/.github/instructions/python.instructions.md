---
applyTo: "src/**/*.py"
description: "Use when editing, reviewing, or creating ML/data-access Python in src/volforecast/. Routes to reference docs for PySlang, TSDB, and Chunk Store; does not restate the data-access APIs or the ML Key Constraints — those live in memory/ref/ and AGENTS.md."
---

# Python Script Rules (src/volforecast/**)

Scope: this file applies to `src/**/*.py` only. Helper-script rules for `skills/` and
`workspace/` live in [python-helpers.instructions.md](python-helpers.instructions.md).

**Before** writing or modifying Python code that touches market data, Slang, CV, or evaluation,
read the relevant reference from `memory/ref/` — on demand, not eagerly:

1. `memory/ref/python-pyslang.md` — PySlang setup (`pyslang.start()`), importing Slang user functions, subprocess mode, start/stop lifecycle
2. `memory/ref/python-tsdb.md` — TSDB daily & real-time wrappers, `TSDBSymbol` API, symbol naming, field dictionary
3. `memory/ref/python-chunk.md` — Chunk Store tick data (`pytickclient.query.chunk_query`), L1/L2 fields, timezone handling, VWAP/volume helpers
4. `skills/PYTHON_MARKET_DATA/SKILL.md` — full API decision tree, RIC conventions, timezone handling, error recovery, multi-symbol fetch loops
5. `policy/ml-constraints.md` — non-negotiable ML constraints (purged CV with purge window ≥ forecast horizon, QLIKE formula, log-RV space, COVID regime handling)

**When modifying config or registry code** (`src/volforecast/config.py`, any `@register_feature_layer`
or `@register_model` decorator), also update the canonical config example — see
[yaml-config.instructions.md](yaml-config.instructions.md).

**ML Key Constraints** (QLIKE primary, purged/blocked CV, log-RV space, COVID handling,
reproducibility, TDD, progress log): the canonical one-line-per-rule table lives in
[AGENTS.md](../../AGENTS.md) → "Key Constraints". Do not restate it here or in code — link to it.

---

## GS Python Environment

- GS uses **conda** environments managed centrally. Pre-installed (do not `pip install`):
  `pyslang`, `pytickclient`, `gs_quant`, `gs_quant_internal`, `gs_data`, `numpy`, `pandas`,
  `scipy`.
- User-managed (add to `src/pyproject.toml`, install via `./vol sync`): `lightgbm`, `torch`,
  `statsmodels`, `scikit-learn`, `arch`.
- Interpreter: never invoke a bare `python`/`pytest`/`uv`. Use `./vol shell script.py` (S-B) or
  the `run_task` label / `vol.cmd` equivalent (S-A). See
  [.github/copilot-instructions.md](../copilot-instructions.md) Rules 2 & 8.

### Package Import Conventions

```python
# --- GS internal (pre-installed) ---
from gs_quant.session import GsSession
from gs_quant_internal.tsdb import TSDBSymbol
from pytickclient import query
import goldmansachs.pyslang as pyslang

# --- Project package ---
from volforecast.features import har, asymmetry, options
from volforecast.evaluation import metrics, statistical_tests
from volforecast.utils.cv import PurgedKFoldCV

# --- Standard scientific stack ---
import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm
from sklearn.linear_model import Ridge, Lasso
import lightgbm as lgb
import torch
```

The CV splitter lives at `src/volforecast/utils/cv.py` (`class PurgedKFoldCV`). Configured
`purge_gap` / `embargo` come from the experiment YAML — do not hard-code them in call sites.

---

## Data Access

Data-access APIs are documented once; this file does not restate them. Load on demand:

- Chunk Store tick data (L1/L2, timezone-aware `chunk_query`) — see `memory/ref/python-chunk.md`.
- TSDB daily / real-time (`TSDBSymbol`) — see `memory/ref/python-tsdb.md`.
- Marquee IV surface (`ERDVOL_PERCENT_STANDARD`, SPX only) and the full API decision tree —
  see `skills/PYTHON_MARKET_DATA/SKILL.md`.

If you find yourself pasting a `chunk_query` / `TSDBSymbol` / Marquee example into this file
again, stop — update the ref instead.

### Local caching

Persist fetched data to `data/raw/<source>/<symbol>_<start>_<end>.parquet` (or the equivalent
under `data/processed/`). Scratch / ephemeral outputs go to `workspace/tmp/` per
[.github/copilot-instructions.md](../copilot-instructions.md) Rule 1.

---

## Testing (src/tests/)

TDD is enforced at the workflow level — see
[.github/copilot-instructions.md](../copilot-instructions.md) Rule 5 and
`policy/working-agreements.md`. This section covers project-local conventions only.

Naming:

```
# test_<module>.py
def test_<what>_<condition>_<expected>(): ...
```

Examples:

```python
def test_qlike_loss_perfect_prediction_returns_zero(): ...
def test_har_features_no_lookahead_bias(): ...
def test_purged_kfold_no_overlap_between_train_test(): ...
```

Fixtures for RV / returns series live in `src/tests/conftest.py`; reuse them rather than
respawning `np.random.seed(...)` fixtures per file.
