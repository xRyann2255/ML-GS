---
applyTo: "**/*.{py,ipynb}"
description: "Use when editing, reviewing, or creating Python scripts (.py) or Jupyter notebooks (.ipynb). Points to reference docs for PySlang setup, TSDB queries, and Chunk Store tick data — the three core data-access APIs used in the Python interpreter."
---

# Python Script Rules

**Before** writing or modifying Python code that accesses market data or Slang functions, read the relevant reference files from `memory/ref/`:

1. memory/ref/python-pyslang.md — PySlang setup (`pyslang.start()`), importing Slang user functions, subprocess mode, start/stop lifecycle
2. memory/ref/python-tsdb.md — TSDB daily & real-time wrappers, `TSDBSymbol` API, symbol naming, field dictionary
3. memory/ref/python-chunk.md — Chunk Store tick data (`pytickclient.query.chunk_query`), Level 1/Level 2 fields, timezone handling, VWAP/volume helpers

**For data pipeline work** (ingestion, fetching, symbol resolution, multi-day queries, debugging data issues), also read:

4. skills/PYTHON_MARKET_DATA/SKILL.md — Full API decision tree, Chunk Store patterns, RIC conventions, timezone handling, error recovery, multi-symbol fetch loops

**When modifying config or registry code** (`src/volforecast/config.py`, any `@register_feature_layer` or `@register_model` decorator), also update the canonical config example — see [.github/instructions/yaml-config.instructions.md](yaml-config.instructions.md).

---

## GS Python Environment

### Conda & Internal Packages

- GS uses **conda** environments managed centrally. The standard GS Python distribution includes pre-installed packages — do not `pip install` them.
- **Pre-installed** (no install needed): `pyslang`, `pytickclient`, `gs_quant`, `gs_quant_internal`, `gs_data`, `numpy`, `pandas`, `scipy`
- **User-managed** (install via `uv add` in `pyproject.toml`): `lightgbm`, `torch`, `statsmodels`, `scikit-learn`, `arch`
- For project-local Python:
  - **Windows:** `cmd /c "H:\uv-env.cmd && uv run python script.py"`
  - **Linux:** `./vol shell script.py` (or `uv run python script.py` from `src/`)
- Prefer `>=3.9` for compatibility with GS internal packages

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
from volforecast.utils.time_series import PurgedKFold

# --- Standard scientific stack ---
import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm
from sklearn.linear_model import Ridge, Lasso
import lightgbm as lgb
import torch
```

---

## Data Access Patterns

### Chunk Store — Tick Data (L1/L2)

```python
from pytickclient import query
import pytz

tz_eastern = pytz.timezone("US/Eastern")
chunkdb = "Eq"

# Timezone-aware datetimes are MANDATORY
st = tz_eastern.localize(datetime(2023, 6, 15, 9, 30, 0))
et = tz_eastern.localize(datetime(2023, 6, 15, 16, 0, 0))

# L1 fields: trades + BBO
fields_l1 = ["trade_price", "trade_size", "bid_price", "ask_price", "bid_size", "ask_size"]
df = pd.DataFrame(query.chunk_query(["SPY"], st, et, chunkdb, fields=fields_l1))

# L2 depth (E-mini only): append "m" suffix
fields_l2 = ["bid_price_1", "ask_price_1", "bid_size_1", "ask_size_1",
             "bid_price_2", "ask_price_2", "bid_size_2", "ask_size_2"]
df_l2 = pd.DataFrame(query.chunk_query(["ESm"], st, et, chunkdb, fields=fields_l2))
```

**Rules:**
- `pyslang.start()` must be called before `chunk_query` works
- Loop through each trading day individually for multi-day queries
- L2 depth is available for **E-mini (ES) only** — other symbols are L1

### TSDB — Daily OHLCV

```python
from gs_quant.session import GsSession
GsSession.use()
from gs_quant_internal.tsdb import TSDBSymbol
from datetime import date

# Daily close (adjusted) — no pyslang needed
data = TSDBSymbol("eqpad_SPY@close.adj.allincdiv").get_data(
    start=str(date(2020, 1, 1)), end=str(date(2024, 12, 31))
)
```

**Rules:**
- `GsSession.use()` must be called once before any `TSDBSymbol` call
- Returns `pd.Series` indexed by date strings
- Prefer `TSDBSymbol` for simple lookups — faster, no pyslang needed

### Marquee — IV Surface (SPX Only)

```python
from gs_quant.session import GsSession
GsSession.use()
from gs_quant.markets.securities import Asset, AssetIdentifier
from gs_quant.timeseries import GsDataApi

# Query ERDVOL_PERCENT_STANDARD for SPX
asset = Asset.get("SPX", AssetIdentifier.TICKER)
iv_data = GsDataApi.get_market_data(
    query={"entityId": asset.get_marquee_id(), "dataSetId": "ERDVOL_PERCENT_STANDARD"},
    start=date(2020, 1, 1), end=date(2024, 12, 31)
)
```

**Rules:**
- IV surface is available for **SPX only** via Marquee EDRVOL_PERCENT
- Fields include ATM IV, skew (25-delta), term structure, butterfly

### Data Caching Pattern

```python
from pathlib import Path
import pandas as pd

CACHE_DIR = Path("workspace/tmp/data")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def load_or_fetch(symbol: str, start: date, end: date, fetcher) -> pd.DataFrame:
    """Load from cache if available, otherwise fetch and cache."""
    cache_path = CACHE_DIR / f"{symbol}_{start}_{end}.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)
    df = fetcher(symbol, start, end)
    df.to_parquet(cache_path)
    return df
```

---

## ML Constraints (Non-Negotiable)

### QLIKE Loss Function

QLIKE is the **primary** loss function. MSE is secondary only.

$$QLIKE = \frac{1}{T} \sum_{t=1}^{T} \left( \frac{RV_t}{\hat{\sigma}_t^2} - \log\frac{RV_t}{\hat{\sigma}_t^2} - 1 \right)$$

```python
def qlike_loss(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute QLIKE loss. Inputs are in LEVEL space (not log)."""
    ratio = y_true / y_pred
    return np.mean(ratio - np.log(ratio) - 1)

# LightGBM custom objective (gradient and hessian in LOG space)
def qlike_objective(y_true: np.ndarray, y_pred: np.ndarray):
    """Custom QLIKE objective for LightGBM. y_pred is raw (log-space)."""
    pred_level = np.exp(y_pred)
    grad = -y_true / pred_level + 1       # dL/d(pred_level) * pred_level
    hess = y_true / pred_level             # d2L/d(pred_level)2 * pred_level^2
    return grad, hess
```

### Purged K-Fold CV (Never Random)

**Never use `sklearn.model_selection.KFold` or `cross_val_score` on time-series data.** Random k-fold causes catastrophic look-ahead bias.

```python
class PurgedKFold:
    """Time-series cross-validation with purge gap and embargo."""

    def __init__(self, n_splits: int = 5, purge_gap: int = 22, embargo_pct: float = 0.01):
        self.n_splits = n_splits
        self.purge_gap = purge_gap      # Days removed between train/test
        self.embargo_pct = embargo_pct  # Fraction of test size to embargo

    def split(self, X, y=None, groups=None):
        n = len(X)
        fold_size = n // self.n_splits
        embargo = int(fold_size * self.embargo_pct)

        for i in range(self.n_splits):
            test_start = i * fold_size
            test_end = min((i + 1) * fold_size, n)

            # Train: everything before (test_start - purge_gap) and after (test_end + embargo)
            train_before = list(range(0, max(0, test_start - self.purge_gap)))
            train_after = list(range(min(n, test_end + embargo), n))
            train_idx = train_before + train_after
            test_idx = list(range(test_start, test_end))

            yield np.array(train_idx), np.array(test_idx)
```

### Log-RV Space

**All models train in log-RV space.** Exponentiate only for final QLIKE evaluation.

```python
# Feature computation
log_rv = np.log(rv_daily)  # Always work in log space

# Model trains on log_rv as target
model.fit(X_train, log_rv_train)

# Predictions in log space
log_rv_pred = model.predict(X_test)

# Exponentiate ONLY for QLIKE evaluation
rv_pred = np.exp(log_rv_pred)
qlike = qlike_loss(rv_actual, rv_pred)
```

### Look-Ahead Bias Checklist

Before using any feature, verify:

- [ ] Feature at time $t$ uses **only** data from time $t$ and earlier
- [ ] Rolling windows use `.shift(1)` before aggregation (no peeking at current day)
- [ ] No future information in train/test split (purged CV, not random)
- [ ] Cross-asset features use **same-day or lagged** values only
- [ ] Event features (FOMC, earnings) use **scheduled dates**, not actual outcomes
- [ ] IV surface features use **prior close** IV, not intraday realizations

### COVID Regime Handling

**Every experiment must explicitly state COVID handling.** Feb–Jun 2020 is an extreme outlier.

```python
COVID_START = pd.Timestamp("2020-02-20")
COVID_END = pd.Timestamp("2020-06-30")

# Option 1: Exclude
df_no_covid = df[~df.index.to_series().between(COVID_START, COVID_END)]

# Option 2: Separate regime indicator
df["covid_regime"] = df.index.to_series().between(COVID_START, COVID_END).astype(int)

# Option 3: Include (document justification)
# "COVID included: testing regime robustness"
```

There is **no default** — the choice must be justified per experiment.

---

## Testing

### TDD Workflow

Enforced at the workflow level — see `policy/working-agreements.md` (Test-first gate) and `workflows/execute.md` / `workflows/fix.md` (TEST-FIRST gate in IMPLEMENT phase).

1. Write a **failing test** that defines expected behavior
2. **Implement** the minimum code to pass
3. **Refactor** while keeping tests green

### Naming Conventions

```python
# Test files: test_<module>.py
# test_har.py, test_metrics.py, test_statistical_tests.py

# Test functions: test_<what>_<condition>_<expected>
def test_qlike_loss_perfect_prediction_returns_zero(): ...
def test_har_features_no_lookahead_bias(): ...
def test_purged_kfold_no_overlap_between_train_test(): ...
```

### Data Fixtures

```python
import pytest
import numpy as np
import pandas as pd

@pytest.fixture
def sample_returns():
    """Simulated 5-min log returns for one trading day (78 intervals)."""
    np.random.seed(42)
    return np.random.normal(0, 0.001, size=78)

@pytest.fixture
def sample_rv_series():
    """252 days of simulated daily RV in log space."""
    np.random.seed(42)
    log_rv = np.random.normal(-8.5, 1.2, size=252)
    dates = pd.bdate_range("2023-01-01", periods=252)
    return pd.Series(log_rv, index=dates, name="log_rv")
```

---

## Key Rules (Always Apply)

### PySlang Lifecycle
- Always call `pyslang.start()` before importing any Slang user function
- Use `subprocess=True` in notebooks to avoid memory issues
- Call `pyslang.stop()` before `pyslang.start()` if restarting with different parameters
- Slang user functions are NOT local `.py` files — they are resolved at runtime from the Slang database

### TSDB
- Use `TSDBSymbol` for direct access — faster, no pyslang needed
- Refer to the field dictionary in `python-tsdb.md` for correct field names

### Chunk Store
- Start/end times **must** be timezone-aware (`pytz.localize`) — naive datetimes will fail
- Always use `chunkdb="Eq"` for equities, futures, and rates
- For multi-day queries, loop through each trading day individually
- L2 depth is available for E-mini only; all other symbols are L1

### Environment
- `pyslang`, `pytickclient`, `gs_quant`, `gs_quant_internal` are pre-installed — no `pip install`
- Wrap tool invocations with the env script: `cmd /c "H:\uv-env.cmd && uv run python script.py"`

### File Output (HARD RULE)
- ALL file writes (temp files, outputs, scripts, artifacts) MUST go to `workspace/tmp/` relative to repo root
- NEVER write to `/tmp/`, `~`, or any path outside the repository — this triggers manual approval prompts
- Never use `tempfile.mktemp()`, `tempfile.NamedTemporaryFile()`, or similar stdlib calls that write to system `/tmp/`
- If you need a scratch file, write it to `workspace/tmp/<descriptive-name>` and delete it when done
