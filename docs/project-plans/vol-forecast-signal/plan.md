# Volatility Forecast + Signal Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modular Python package (`volforecast/`) that forecasts realized volatility with HAR + ML baselines, evaluates with QLIKE/DM/MCS, and generates a tradeable IV-RV gap signal with P&L backtest.

**Architecture:** Config-driven pipeline with pluggable feature layers and model interfaces. Each feature layer is a self-contained module. Intermediate artifacts saved as parquet. Expanding-window purged CV with 12-month final holdout. All internal quantities in annualized decimal variance.

**Tech Stack:** Python 3.10+, numpy, pandas, statsmodels (HAR/OLS), LightGBM, scipy, pytest. GS-internal: gs-quant/Marquee SDK, Chunk Store API.

**Spec:** `docs/project-plans/vol-forecast-signal/design.md`

---

## Chunk 1: Infrastructure and Sprint 1 -- Data Pipeline + Baselines

### Task 0: Package Skeleton and Infrastructure

**Files:**
- Create: `volforecast/volforecast/__init__.py`
- Create: `volforecast/volforecast/data/__init__.py`
- Create: `volforecast/volforecast/features/__init__.py`
- Create: `volforecast/volforecast/models/__init__.py`
- Create: `volforecast/volforecast/evaluation/__init__.py`
- Create: `volforecast/volforecast/signals/__init__.py`
- Create: `volforecast/volforecast/utils/__init__.py`
- Create: `volforecast/tests/__init__.py`
- Create: `volforecast/config/default.yaml`
- Create: `logs/progress.md`
- Create: `volforecast/results/tables/.gitkeep`
- Create: `volforecast/results/figures/.gitkeep`
- Create: `volforecast/pyproject.toml`
- Create: `.claude/skills/progress-log.md`

- [ ] **Step 1: Create package directory structure**

```bash
mkdir -p volforecast/{volforecast/{data,features,models,evaluation,signals,utils},tests,config,logs,results/{tables,figures},notebooks}
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[project]
name = "volforecast"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "numpy>=1.24",
    "pandas>=2.0",
    "statsmodels>=0.14",
    "scipy>=1.11",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
ml = ["lightgbm>=4.0", "shap>=0.43"]
dl = ["torch>=2.0"]
dev = ["pytest>=7.4", "pytest-cov"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Create all `__init__.py` files**

Each `__init__.py` is empty initially. Create for: `volforecast/volforecast/`, `data/`, `features/`, `models/`, `evaluation/`, `signals/`, `utils/`, and `tests/`.

- [ ] **Step 4: Create default config**

File: `volforecast/config/default.yaml`

```yaml
universe:
  # 30 mega-cap equities + 4 ETFs + E-mini
  # Populate with actual tickers during Sprint 1 data pipeline
  symbols: []
  emini_symbol: "ES"

dates:
  start: "2013-01-01"
  end: "2024-06-30"
  holdout_start: "2023-07-01"  # final 12 months reserved

horizons: [1, 5, 22]

rv:
  sampling_freq: "5min"  # 78 intervals per 6.5hr trading day
  annualization_factor: 252

feature_layers: ["rv"]  # start with Layer 0 only

models: ["har", "har_j", "har_cj", "shar", "harq"]

training_mode: "per_symbol"  # per_symbol | pooled | both

cv:
  method: "expanding_window_purged"
  n_splits: 5
  purge_days: "auto"  # set to h for each horizon
  embargo_days: 25

evaluation:
  primary_loss: "qlike"
  secondary_losses: ["mse"]
  dm_significance: 0.05
  mcs_significance: 0.10
```

- [ ] **Step 5: Create progress log with backfilled entries**

File: `logs/progress.md`

Backfill from git history for weeks 1-2 (April 21 - May 5). Include: learning guide writing, repo restructuring, project scoping, paper reading, direction decision.

- [ ] **Step 6: Create progress-log skill**

File: `.claude/skills/progress-log.md`

```markdown
---
name: progress-log
description: Update the daily progress log. Invoke after meaningful progress, decisions, or at session end.
---

Read `logs/progress.md`. Check if today's date has an existing entry.

**If post-commit (granular update):**
- Read the latest git diff/commit message
- Append a bullet to today's entry (create entry if none exists)
- Small commits (typo, formatting): one-line bullet
- Meaningful commits: 2-3 line bullet with what changed and why

**If post-session (daily summary):**
- Consolidate today's granular bullets into a clean summary
- Add a "Next:" line for tomorrow's plan
- Do not duplicate existing bullets

**Entry format:**
## YYYY-MM-DD

**Sprint:** N -- [Sprint Name]
**Focus:** [main topic]

- [bullet points]

**Next:** [tomorrow's plan]
```

- [ ] **Step 7: Configure hooks in settings**

Add to `.claude/settings.local.json`:
- Post-commit hook: invoke progress-log skill with "post-commit" context
- Post-session hook: invoke progress-log skill with "post-session" context

- [ ] **Step 8: Install package in editable mode**

```bash
cd volforecast && pip install -e ".[dev]"
```

This ensures `from volforecast import ...` works in both tests and notebooks.

- [ ] **Step 9: Commit infrastructure**

```bash
cd volforecast
git add -A
git commit -m "feat: initialize volforecast package skeleton and infrastructure"
```

---

### Task 1: Unit Conversions (`data/units.py`)

**Files:**
- Create: `volforecast/volforecast/data/units.py`
- Create: `volforecast/tests/test_units.py`

All internal quantities are annualized decimal variance. This module is the single source of truth for conversions.

- [ ] **Step 1: Write failing tests**

File: `volforecast/tests/test_units.py`

```python
import numpy as np
import pytest
from volforecast.data.units import (
    vix_to_variance,
    variance_to_vol_pct,
    daily_rv_to_annual,
    iv_pct_to_variance,
)


def test_vix_to_variance_scalar():
    # VIX=18 -> (18/100)^2 = 0.0324
    assert vix_to_variance(18.0) == pytest.approx(0.0324)


def test_vix_to_variance_array():
    result = vix_to_variance(np.array([18.0, 20.0]))
    expected = np.array([0.0324, 0.04])
    np.testing.assert_allclose(result, expected)


def test_variance_to_vol_pct():
    # 0.0324 -> 18.0%
    assert variance_to_vol_pct(0.0324) == pytest.approx(18.0, rel=1e-4)


def test_daily_rv_to_annual():
    # daily_var * 252
    daily = 0.0001  # single-day realized variance
    assert daily_rv_to_annual(daily) == pytest.approx(0.0252)


def test_daily_rv_to_annual_custom_factor():
    assert daily_rv_to_annual(0.0001, factor=365) == pytest.approx(0.0365)


def test_iv_pct_to_variance():
    # 20% -> (20/100)^2 = 0.04
    assert iv_pct_to_variance(20.0) == pytest.approx(0.04)


def test_roundtrip_vix():
    original = 22.5
    var = vix_to_variance(original)
    back = variance_to_vol_pct(var)
    assert back == pytest.approx(original, rel=1e-6)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd volforecast && python -m pytest tests/test_units.py -v
```

Expected: ModuleNotFoundError or ImportError.

- [ ] **Step 3: Implement units.py**

File: `volforecast/volforecast/data/units.py`

```python
"""Unit conversions for volatility quantities.

Internal convention: all quantities are annualized decimal variance.
Example: 18% annual vol = 0.0324 annualized variance.

Conversions happen at data loading boundaries and final display only.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike

_DEFAULT_ANNUAL_FACTOR = 252


def vix_to_variance(vix: ArrayLike) -> ArrayLike:
    """VIX (percentage vol, e.g. 18) -> annualized decimal variance."""
    v = np.asarray(vix, dtype=np.float64)
    return (v / 100.0) ** 2


def variance_to_vol_pct(variance: ArrayLike) -> ArrayLike:
    """Annualized decimal variance -> percentage vol (e.g. 18.0%)."""
    v = np.asarray(variance, dtype=np.float64)
    return np.sqrt(v) * 100.0


def daily_rv_to_annual(
    daily_var: ArrayLike, factor: int = _DEFAULT_ANNUAL_FACTOR
) -> ArrayLike:
    """Single-day realized variance -> annualized decimal variance."""
    return np.asarray(daily_var, dtype=np.float64) * factor


def iv_pct_to_variance(iv_pct: ArrayLike) -> ArrayLike:
    """Implied vol in percentage (e.g. 20%) -> annualized decimal variance."""
    v = np.asarray(iv_pct, dtype=np.float64)
    return (v / 100.0) ** 2
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd volforecast && python -m pytest tests/test_units.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add volforecast/data/units.py tests/test_units.py
git commit -m "feat(data): add unit conversion module with full test coverage"
```

---

### Task 2: RV Computation (`data/rv.py`)

**Files:**
- Create: `volforecast/volforecast/data/rv.py`
- Create: `volforecast/tests/test_rv.py`

Computes daily realized variance, bipower variation, realized quarticity, and jump component from intraday returns. Uses 5-min sampling (78 intervals per 6.5hr day). All outputs in annualized decimal variance.

- [ ] **Step 1: Write failing tests**

File: `volforecast/tests/test_rv.py`

```python
import numpy as np
import pandas as pd
import pytest
from volforecast.data.rv import (
    realized_variance,
    bipower_variation,
    realized_quarticity,
    jump_component,
    signed_semivariances,
    compute_daily_rv_measures,
)


def _make_intraday_returns(n: int = 78, seed: int = 42) -> np.ndarray:
    """Generate synthetic 5-min log returns for one day."""
    rng = np.random.default_rng(seed)
    # daily vol ~ 1.2%, so per-interval vol ~ 1.2%/sqrt(78) ~ 0.136%
    return rng.normal(0, 0.00136, size=n)


class TestRealizedVariance:
    def test_sum_of_squares(self):
        r = np.array([0.01, -0.005, 0.002, -0.008, 0.003])
        expected = np.sum(r**2)
        assert realized_variance(r) == pytest.approx(expected)

    def test_nonnegative(self):
        r = _make_intraday_returns()
        assert realized_variance(r) >= 0

    def test_annualized(self):
        r = _make_intraday_returns()
        rv_daily = realized_variance(r)
        rv_annual = realized_variance(r, annualize=True)
        assert rv_annual == pytest.approx(rv_daily * 252)


class TestBipowerVariation:
    def test_basic(self):
        r = np.array([0.01, -0.005, 0.002, -0.008, 0.003])
        # mu1^{-2} * sum |r_i| * |r_{i-1}| for i=1..n-1
        mu1_inv_sq = np.pi / 2
        adj_sum = np.sum(np.abs(r[1:]) * np.abs(r[:-1]))
        expected = mu1_inv_sq * adj_sum
        assert bipower_variation(r) == pytest.approx(expected)

    def test_less_than_rv_with_jump(self):
        r = _make_intraday_returns()
        r_with_jump = r.copy()
        r_with_jump[39] = 0.05  # inject a jump
        # BPV should be less than RV when jump present
        assert bipower_variation(r_with_jump) < realized_variance(r_with_jump)


class TestRealizedQuarticity:
    def test_nonnegative(self):
        r = _make_intraday_returns()
        assert realized_quarticity(r) >= 0

    def test_formula(self):
        r = np.array([0.01, -0.005, 0.002])
        n = len(r)
        expected = (n / 3) * np.sum(r**4)
        assert realized_quarticity(r) == pytest.approx(expected)


class TestJumpComponent:
    def test_no_jump_day(self):
        r = _make_intraday_returns()
        j = jump_component(r)
        # On a no-jump day, j should be near zero (floored at 0)
        assert j >= 0
        assert j < realized_variance(r) * 0.5

    def test_jump_day(self):
        r = _make_intraday_returns()
        r[39] = 0.05  # big jump
        j = jump_component(r)
        assert j > 0


class TestSignedSemivariances:
    def test_sum_equals_rv(self):
        r = _make_intraday_returns()
        rv_pos, rv_neg = signed_semivariances(r)
        assert rv_pos + rv_neg == pytest.approx(realized_variance(r))

    def test_nonnegative(self):
        r = _make_intraday_returns()
        rv_pos, rv_neg = signed_semivariances(r)
        assert rv_pos >= 0
        assert rv_neg >= 0


class TestComputeDailyMeasures:
    def test_returns_all_columns(self):
        # 3 days of 78 intraday returns
        dates = pd.date_range("2024-01-02", periods=3, freq="B")
        rng = np.random.default_rng(42)
        intraday = {
            d: rng.normal(0, 0.00136, size=78) for d in dates
        }
        result = compute_daily_rv_measures(intraday, annualize=True)
        assert isinstance(result, pd.DataFrame)
        expected_cols = {"rv", "bpv", "rq", "jump", "rv_pos", "rv_neg"}
        assert expected_cols.issubset(set(result.columns))
        assert len(result) == 3
        assert result["rv"].gt(0).all()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd volforecast && python -m pytest tests/test_rv.py -v
```

- [ ] **Step 3: Implement rv.py**

File: `volforecast/volforecast/data/rv.py`

```python
"""Realized volatility measures from intraday returns.

All functions accept a 1-D array of intraday log returns for a single day
and return scalar measures. compute_daily_rv_measures() wraps them for a
dict of {date: returns_array}.

References:
    - ABDL (2001, 2003): realized variance
    - BNS (2004, 2006): bipower variation, jump test
    - BPQ (2016): realized quarticity for HARQ
    - Patton-Sheppard (2015): signed semivariances
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_ANNUAL_FACTOR = 252


def realized_variance(
    returns: np.ndarray, annualize: bool = False
) -> float:
    rv = float(np.sum(returns**2))
    return rv * _ANNUAL_FACTOR if annualize else rv


def bipower_variation(
    returns: np.ndarray, annualize: bool = False
) -> float:
    mu1_inv_sq = np.pi / 2
    bpv = mu1_inv_sq * float(np.sum(np.abs(returns[1:]) * np.abs(returns[:-1])))
    return bpv * _ANNUAL_FACTOR if annualize else bpv


def realized_quarticity(
    returns: np.ndarray, annualize: bool = False
) -> float:
    n = len(returns)
    rq = (n / 3) * float(np.sum(returns**4))
    return rq * (_ANNUAL_FACTOR**2) if annualize else rq


def jump_component(
    returns: np.ndarray, annualize: bool = False
) -> float:
    rv = realized_variance(returns)
    bpv = bipower_variation(returns)
    j = max(rv - bpv, 0.0)
    return j * _ANNUAL_FACTOR if annualize else j


def signed_semivariances(
    returns: np.ndarray, annualize: bool = False
) -> tuple[float, float]:
    rv_pos = float(np.sum(returns[returns > 0] ** 2))
    rv_neg = float(np.sum(returns[returns <= 0] ** 2))
    if annualize:
        return rv_pos * _ANNUAL_FACTOR, rv_neg * _ANNUAL_FACTOR
    return rv_pos, rv_neg


def compute_daily_rv_measures(
    intraday_returns: dict[pd.Timestamp, np.ndarray],
    annualize: bool = True,
) -> pd.DataFrame:
    records = []
    for date in sorted(intraday_returns.keys()):
        r = intraday_returns[date]
        rv_p, rv_n = signed_semivariances(r, annualize=annualize)
        records.append(
            {
                "date": date,
                "rv": realized_variance(r, annualize=annualize),
                "bpv": bipower_variation(r, annualize=annualize),
                "rq": realized_quarticity(r, annualize=annualize),
                "jump": jump_component(r, annualize=annualize),
                "rv_pos": rv_p,
                "rv_neg": rv_n,
            }
        )
    return pd.DataFrame(records).set_index("date")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd volforecast && python -m pytest tests/test_rv.py -v
```

- [ ] **Step 5: Commit**

```bash
git add volforecast/data/rv.py tests/test_rv.py
git commit -m "feat(data): add realized volatility computation module"
```

---

### Task 3: Universe and Data Splits (`data/universe.py`)

**Files:**
- Create: `volforecast/volforecast/data/universe.py`
- Create: `volforecast/tests/test_universe.py`

Manages the symbol universe, date ranges, and train/holdout split. The holdout (final 12 months) is locked before any modeling.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_universe.py
import pandas as pd
import pytest
from volforecast.data.universe import Universe


class TestUniverse:
    def test_holdout_after_train(self):
        u = Universe(
            symbols=["SPY", "AAPL"],
            emini_symbol="ES",
            start="2013-01-01",
            end="2024-06-30",
            holdout_start="2023-07-01",
        )
        assert u.train_end < u.holdout_start

    def test_holdout_excluded_from_train(self):
        u = Universe(
            symbols=["SPY"],
            emini_symbol="ES",
            start="2013-01-01",
            end="2024-06-30",
            holdout_start="2023-07-01",
        )
        all_dates = pd.bdate_range("2013-01-01", "2024-06-30")
        train_dates = u.train_dates(all_dates)
        holdout_dates = u.holdout_dates(all_dates)
        assert len(set(train_dates) & set(holdout_dates)) == 0

    def test_symbols_list(self):
        u = Universe(
            symbols=["SPY", "AAPL"],
            emini_symbol="ES",
            start="2013-01-01",
            end="2024-06-30",
            holdout_start="2023-07-01",
        )
        assert u.emini_symbol == "ES"
        assert len(u.equity_symbols) == 2
        assert "ES" not in u.equity_symbols

    def test_all_symbols_includes_emini(self):
        u = Universe(
            symbols=["SPY", "AAPL"],
            emini_symbol="ES",
            start="2013-01-01",
            end="2024-06-30",
            holdout_start="2023-07-01",
        )
        assert "ES" in u.all_symbols
        assert len(u.all_symbols) == 3

    def test_from_config(self, tmp_path):
        import yaml
        cfg = {
            "universe": {
                "symbols": ["SPY", "AAPL"],
                "emini_symbol": "ES",
            },
            "dates": {
                "start": "2013-01-01",
                "end": "2024-06-30",
                "holdout_start": "2023-07-01",
            },
        }
        path = tmp_path / "test.yaml"
        path.write_text(yaml.dump(cfg))
        u = Universe.from_config(str(path))
        assert u.emini_symbol == "ES"
        assert u.start == pd.Timestamp("2013-01-01")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd volforecast && python -m pytest tests/test_universe.py -v
```

- [ ] **Step 3: Implement universe.py**

File: `volforecast/volforecast/data/universe.py`

```python
"""Universe and data split management.

The holdout (final 12 months) is locked before any modeling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml


@dataclass
class Universe:
    symbols: list[str]
    emini_symbol: str
    start: pd.Timestamp
    end: pd.Timestamp
    holdout_start: pd.Timestamp

    def __post_init__(self):
        self.start = pd.Timestamp(self.start)
        self.end = pd.Timestamp(self.end)
        self.holdout_start = pd.Timestamp(self.holdout_start)

    @property
    def train_end(self) -> pd.Timestamp:
        return self.holdout_start - pd.tseries.offsets.BDay(1)

    @property
    def equity_symbols(self) -> list[str]:
        return [s for s in self.symbols if s != self.emini_symbol]

    @property
    def all_symbols(self) -> list[str]:
        syms = list(self.symbols)
        if self.emini_symbol not in syms:
            syms.append(self.emini_symbol)
        return syms

    def train_dates(self, dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
        return dates[(dates >= self.start) & (dates < self.holdout_start)]

    def holdout_dates(self, dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
        return dates[(dates >= self.holdout_start) & (dates <= self.end)]

    @classmethod
    def from_config(cls, path: str | Path) -> Universe:
        with open(path) as f:
            cfg = yaml.safe_load(f)
        return cls(
            symbols=cfg["universe"]["symbols"],
            emini_symbol=cfg["universe"]["emini_symbol"],
            start=cfg["dates"]["start"],
            end=cfg["dates"]["end"],
            holdout_start=cfg["dates"]["holdout_start"],
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd volforecast && python -m pytest tests/test_universe.py -v
```

- [ ] **Step 5: Commit**

```bash
git add volforecast/data/universe.py tests/test_universe.py
git commit -m "feat(data): add universe and data split management"
```

---

### Task 4: Data Loaders (`data/loaders.py`)

**Files:**
- Create: `volforecast/volforecast/data/loaders.py`
- Create: `volforecast/tests/test_loaders.py`

Abstract loader interface with concrete implementations for Chunk Store (GS internal) and CSV (for testing/portability). The GS-specific code will be filled in on GS machines; tests use CSV loader with synthetic data.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_loaders.py
import pandas as pd
import numpy as np
import pytest
from volforecast.data.loaders import CSVLoader


@pytest.fixture
def sample_rv_parquet(tmp_path):
    """Create a minimal parquet file with daily RV data."""
    dates = pd.bdate_range("2023-01-02", periods=100)
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "rv": rng.exponential(0.02, 100),
        "bpv": rng.exponential(0.018, 100),
        "rq": rng.exponential(0.001, 100),
        "jump": np.maximum(rng.normal(0.002, 0.005, 100), 0),
        "rv_pos": rng.exponential(0.01, 100),
        "rv_neg": rng.exponential(0.01, 100),
    }, index=dates)
    path = tmp_path / "SPY_rv.parquet"
    df.to_parquet(path)
    return path


class TestCSVLoader:
    def test_load_rv(self, sample_rv_parquet):
        loader = CSVLoader(data_dir=sample_rv_parquet.parent)
        df = loader.load_rv("SPY")
        assert isinstance(df, pd.DataFrame)
        assert "rv" in df.columns
        assert len(df) == 100

    def test_missing_symbol_raises(self, sample_rv_parquet):
        loader = CSVLoader(data_dir=sample_rv_parquet.parent)
        with pytest.raises(FileNotFoundError):
            loader.load_rv("NONEXISTENT")
```

- [ ] **Step 2: Implement with abstract base + CSV concrete**

```python
# volforecast/data/loaders.py
from abc import ABC, abstractmethod
from pathlib import Path
import pandas as pd


class DataLoader(ABC):
    @abstractmethod
    def load_rv(self, symbol: str) -> pd.DataFrame: ...

    @abstractmethod
    def load_daily(self, symbol: str) -> pd.DataFrame: ...


class CSVLoader(DataLoader):
    """Loads pre-computed parquet/CSV files. Used for testing and portability."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)

    def load_rv(self, symbol: str) -> pd.DataFrame:
        path = self.data_dir / f"{symbol}_rv.parquet"
        if not path.exists():
            raise FileNotFoundError(f"No RV data for {symbol} at {path}")
        return pd.read_parquet(path)

    def load_daily(self, symbol: str) -> pd.DataFrame:
        path = self.data_dir / f"{symbol}_daily.parquet"
        if not path.exists():
            raise FileNotFoundError(f"No daily data for {symbol} at {path}")
        return pd.read_parquet(path)


# GS-specific loaders to be implemented on GS machines:
# class ChunkStoreLoader(DataLoader): ...
# class MarqueeLoader(DataLoader): ...
```

- [ ] **Step 3: Commit**

```bash
git add volforecast/data/loaders.py tests/test_loaders.py
git commit -m "feat(data): add data loader interface with CSV implementation"
```

---

### Task 4b: Multi-Horizon Target Construction (`data/targets.py`)

**Files:**
- Create: `volforecast/volforecast/data/targets.py`
- Create: `volforecast/tests/test_targets.py`

Constructs forward-looking target variables for h=1, 5, 22. Target at horizon h is the average daily RV over the next h days. This is required before any model fitting at h>1.

- [ ] **Step 1: Write failing tests**

File: `volforecast/tests/test_targets.py`

```python
import numpy as np
import pandas as pd
import pytest
from volforecast.data.targets import make_target


@pytest.fixture
def daily_rv():
    dates = pd.bdate_range("2023-01-02", periods=100)
    rng = np.random.default_rng(42)
    return pd.Series(rng.exponential(0.02, 100), index=dates, name="rv")


class TestMakeTarget:
    def test_h1_is_next_day(self, daily_rv):
        target = make_target(daily_rv, horizon=1)
        assert target.iloc[0] == pytest.approx(daily_rv.iloc[1])

    def test_h5_is_5day_mean(self, daily_rv):
        target = make_target(daily_rv, horizon=5)
        manual = daily_rv.iloc[1:6].mean()
        assert target.iloc[0] == pytest.approx(manual)

    def test_h22_is_22day_mean(self, daily_rv):
        target = make_target(daily_rv, horizon=22)
        manual = daily_rv.iloc[1:23].mean()
        assert target.iloc[0] == pytest.approx(manual)

    def test_last_h_rows_are_nan(self, daily_rv):
        target = make_target(daily_rv, horizon=5)
        assert target.iloc[-5:].isna().all()
        assert pd.notna(target.iloc[-6]) and np.isfinite(target.iloc[-6])

    def test_length_matches_input(self, daily_rv):
        target = make_target(daily_rv, horizon=22)
        assert len(target) == len(daily_rv)

    def test_all_horizons(self, daily_rv):
        for h in [1, 5, 22]:
            target = make_target(daily_rv, horizon=h)
            assert target.iloc[-h:].isna().all()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd volforecast && python -m pytest tests/test_targets.py -v
```

- [ ] **Step 3: Implement targets.py**

File: `volforecast/volforecast/data/targets.py`

```python
"""Multi-horizon target construction for volatility forecasting.

Target at horizon h is the average daily RV over the next h business days.
For h=1, this is simply next-day RV.
"""

from __future__ import annotations

import pandas as pd


def make_target(rv: pd.Series, horizon: int) -> pd.Series:
    """Construct forward-looking target for forecast horizon h.

    Returns a Series aligned with rv's index where target[t] = mean(rv[t+1:t+h+1]).
    Last h values are NaN (no complete forward window).
    """
    target = rv.shift(-1).rolling(window=horizon).mean().shift(-(horizon - 1))
    target.name = f"target_h{horizon}"
    return target
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd volforecast && python -m pytest tests/test_targets.py -v
```

- [ ] **Step 5: Commit**

```bash
git add volforecast/data/targets.py tests/test_targets.py
git commit -m "feat(data): add multi-horizon target construction for h=1,5,22"
```

---

### Task 5: Feature Layer Base + Layer 0 RV Features

**Files:**
- Create: `volforecast/volforecast/features/base.py`
- Create: `volforecast/volforecast/features/rv_features.py`
- Create: `volforecast/tests/test_features.py`

Layer 0 computes: RV_d, RV_w (5-day avg), RV_m (22-day avg), log transforms, RV_w/RV_d ratio, RQ, signed semivariances RV+/RV-, jump component. These are the HAR-family inputs.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_features.py
import numpy as np
import pandas as pd
import pytest
from volforecast.features.rv_features import RVFeatureLayer


@pytest.fixture
def sample_rv_df():
    """100 days of synthetic RV data."""
    dates = pd.bdate_range("2023-01-02", periods=100)
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "rv": rng.exponential(0.02, 100),
        "bpv": rng.exponential(0.018, 100),
        "rq": rng.exponential(0.001, 100),
        "jump": np.maximum(rng.normal(0.002, 0.005, 100), 0),
        "rv_pos": rng.exponential(0.01, 100),
        "rv_neg": rng.exponential(0.01, 100),
    }, index=dates)


class TestRVFeatureLayer:
    def test_compute_returns_dataframe(self, sample_rv_df):
        layer = RVFeatureLayer()
        result = layer.compute({"rv": sample_rv_df})
        assert isinstance(result, pd.DataFrame)

    def test_has_har_features(self, sample_rv_df):
        layer = RVFeatureLayer()
        result = layer.compute({"rv": sample_rv_df})
        for col in ["rv_d", "rv_w", "rv_m", "log_rv_d", "log_rv_w", "log_rv_m"]:
            assert col in result.columns, f"Missing {col}"

    def test_rv_w_is_5day_average(self, sample_rv_df):
        layer = RVFeatureLayer()
        result = layer.compute({"rv": sample_rv_df})
        # rv_w at index 30 should be mean of rv at indices 26-30
        manual = sample_rv_df["rv"].iloc[26:31].mean()
        assert result["rv_w"].iloc[30] == pytest.approx(manual, rel=1e-10)

    def test_rv_m_is_22day_average(self, sample_rv_df):
        layer = RVFeatureLayer()
        result = layer.compute({"rv": sample_rv_df})
        manual = sample_rv_df["rv"].iloc[9:31].mean()
        assert result["rv_m"].iloc[30] == pytest.approx(manual, rel=1e-10)

    def test_first_22_rows_are_nan(self, sample_rv_df):
        layer = RVFeatureLayer()
        result = layer.compute({"rv": sample_rv_df})
        assert result["rv_m"].iloc[:21].isna().all()

    def test_has_bpv_and_semivariances(self, sample_rv_df):
        layer = RVFeatureLayer()
        result = layer.compute({"rv": sample_rv_df})
        assert "bpv" in result.columns
        assert "rv_pos" in result.columns
        assert "rv_neg" in result.columns

    def test_describe_returns_paper_refs(self):
        layer = RVFeatureLayer()
        desc = layer.describe()
        assert "rv_d" in desc
        assert "Corsi" in desc["rv_d"]
```

- [ ] **Step 2: Implement base.py and rv_features.py**

```python
# volforecast/features/base.py
from abc import ABC, abstractmethod
import pandas as pd


class FeatureLayer(ABC):
    name: str
    requires: list[str]

    @abstractmethod
    def compute(self, data: dict) -> pd.DataFrame:
        """Returns date x feature DataFrame. Variance features in annualized decimal variance."""
        ...

    @abstractmethod
    def describe(self) -> dict[str, str]:
        """Returns {feature_name: paper_reference}."""
        ...
```

```python
# volforecast/features/rv_features.py
import numpy as np
import pandas as pd
from volforecast.features.base import FeatureLayer


class RVFeatureLayer(FeatureLayer):
    name = "rv"
    requires = ["rv"]

    def compute(self, data: dict) -> pd.DataFrame:
        rv_df = data["rv"]
        rv = rv_df["rv"]

        features = pd.DataFrame(index=rv.index)
        features["rv_d"] = rv
        features["rv_w"] = rv.rolling(5).mean()
        features["rv_m"] = rv.rolling(22).mean()
        features["log_rv_d"] = np.log(rv.clip(lower=1e-12))
        features["log_rv_w"] = np.log(features["rv_w"].clip(lower=1e-12))
        features["log_rv_m"] = np.log(features["rv_m"].clip(lower=1e-12))
        features["rv_ratio_wd"] = features["rv_w"] / features["rv_d"].clip(lower=1e-12)
        features["rq"] = rv_df["rq"]
        features["rq_sqrt"] = np.sqrt(rv_df["rq"].clip(lower=0))
        features["bpv"] = rv_df["bpv"]
        features["bpv_w"] = rv_df["bpv"].rolling(5).mean()
        features["bpv_m"] = rv_df["bpv"].rolling(22).mean()
        features["rv_pos"] = rv_df["rv_pos"]
        features["rv_neg"] = rv_df["rv_neg"]
        features["jump"] = rv_df["jump"]
        features["log_jump_plus1"] = np.log1p(rv_df["jump"])

        return features

    def describe(self) -> dict[str, str]:
        return {
            "rv_d": "Corsi (2009) HAR daily component",
            "rv_w": "Corsi (2009) HAR weekly component (5-day avg)",
            "rv_m": "Corsi (2009) HAR monthly component (22-day avg)",
            "log_rv_d": "Log transform for Gaussianity, ABDL (2003)",
            "log_rv_w": "Log transform, weekly",
            "log_rv_m": "Log transform, monthly",
            "rv_ratio_wd": "Weekly/daily RV ratio, persistence indicator",
            "bpv": "Bipower variation (daily continuous), BNS (2004, 2006)",
            "bpv_w": "Weekly avg BPV, for HAR-CJ decomposition",
            "bpv_m": "Monthly avg BPV, for HAR-CJ decomposition",
            "rq": "Realized quarticity, BPQ (2016)",
            "rq_sqrt": "sqrt(RQ) for HARQ interaction, BPQ (2016)",
            "rv_pos": "Positive semivariance, Patton-Sheppard (2015)",
            "rv_neg": "Negative semivariance, Patton-Sheppard (2015)",
            "jump": "Jump component max(RV-BPV, 0), BNS (2006)",
            "log_jump_plus1": "Log(1+jump) for stability",
        }
```

- [ ] **Step 3: Run tests, commit**

```bash
cd volforecast && python -m pytest tests/test_features.py -v
git add volforecast/features/base.py volforecast/features/rv_features.py tests/test_features.py
git commit -m "feat(features): add base interface and Layer 0 RV features"
```

---

### Task 6: HAR Model Family (`models/har.py`)

**Files:**
- Create: `volforecast/volforecast/models/base.py`
- Create: `volforecast/volforecast/models/har.py`
- Create: `volforecast/tests/test_models.py`

Implements HAR, HAR-J, HAR-CJ, SHAR, HARQ via OLS. Per-symbol fitting (low parameter count, ~2,800 obs sufficient).

- [ ] **Step 1: Write failing tests**

```python
# tests/test_models.py
import numpy as np
import pandas as pd
import pytest
from volforecast.models.har import (
    HARModel, HARJModel, HARCJModel, SHARModel, HARQModel,
)


@pytest.fixture
def synthetic_data():
    """Generate synthetic RV features + target for 500 days."""
    rng = np.random.default_rng(42)
    n = 500
    rv = rng.exponential(0.02, n)
    X = pd.DataFrame({
        "rv_d": rv,
        "rv_w": pd.Series(rv).rolling(5).mean().values,
        "rv_m": pd.Series(rv).rolling(22).mean().values,
        "rv_pos": rv * 0.5 + rng.normal(0, 0.001, n),
        "rv_neg": rv * 0.5 + rng.normal(0, 0.001, n),
        "rq_sqrt": np.sqrt(rng.exponential(0.001, n)),
        "jump": np.maximum(rv - rv * 0.9, 0),
        "bpv": rv * 0.9,
    }).iloc[22:]  # drop NaN rows
    y = X["rv_d"].shift(-1).iloc[:-1]  # next-day RV as target
    X = X.iloc[:-1]
    return X, y.values


class TestHAR:
    def test_fit_predict(self, synthetic_data):
        X, y = synthetic_data
        X_train, X_val = X.iloc[:300], X.iloc[300:]
        y_train, y_val = y[:300], y[300:]
        model = HARModel()
        model.fit(X_train, y_train, X_val, y_val)
        preds = model.predict(X_val)
        assert len(preds) == len(X_val)
        assert np.all(np.isfinite(preds))

    def test_uses_only_har_columns(self, synthetic_data):
        X, y = synthetic_data
        model = HARModel()
        model.fit(X.iloc[:300], y[:300], X.iloc[300:], y[300:])
        assert set(model._feature_cols) == {"rv_d", "rv_w", "rv_m"}

    def test_feature_importance_none(self, synthetic_data):
        X, y = synthetic_data
        model = HARModel()
        model.fit(X.iloc[:300], y[:300], X.iloc[300:], y[300:])
        assert model.feature_importance() is None


class TestHARJ:
    def test_uses_jump(self, synthetic_data):
        X, y = synthetic_data
        model = HARJModel()
        model.fit(X.iloc[:300], y[:300], X.iloc[300:], y[300:])
        assert "jump" in model._feature_cols
        assert set(model._feature_cols) == {"rv_d", "rv_w", "rv_m", "jump"}


class TestHARCJ:
    def test_uses_continuous_and_jump(self, synthetic_data):
        X, y = synthetic_data
        X["bpv_w"] = X["bpv"].rolling(5).mean()
        X["bpv_m"] = X["bpv"].rolling(22).mean()
        X = X.dropna()
        y = y[-len(X):]
        model = HARCJModel()
        model.fit(X.iloc[:250], y[:250], X.iloc[250:], y[250:])
        assert set(model._feature_cols) == {"bpv", "bpv_w", "bpv_m", "jump"}
        assert "rv_d" not in model._feature_cols


class TestSHAR:
    def test_uses_semivariances(self, synthetic_data):
        X, y = synthetic_data
        model = SHARModel()
        model.fit(X.iloc[:300], y[:300], X.iloc[300:], y[300:])
        assert "rv_pos" in model._feature_cols
        assert "rv_neg" in model._feature_cols
        assert set(model._feature_cols) == {"rv_pos", "rv_neg", "rv_w", "rv_m"}


class TestHARQ:
    def test_uses_rq_interaction(self, synthetic_data):
        X, y = synthetic_data
        model = HARQModel()
        model.fit(X.iloc[:300], y[:300], X.iloc[300:], y[300:])
        assert "harq_interaction" in model._feature_cols
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd volforecast && python -m pytest tests/test_models.py -v
```

- [ ] **Step 3: Implement base.py and har.py**

File: `volforecast/volforecast/models/base.py`

```python
"""Abstract base for all volatility forecast models."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class VolModel(ABC):
    name: str

    @abstractmethod
    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_val: pd.DataFrame,
        y_val: np.ndarray,
    ) -> None: ...

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray: ...

    def feature_importance(self) -> pd.Series | None:
        return None
```

File: `volforecast/volforecast/models/har.py`

```python
"""HAR-family models via OLS.

References:
    - Corsi (2009): HAR
    - Corsi-Pirino-Reno (2010): HAR-J, HAR-CJ
    - Patton-Sheppard (2015): SHAR
    - Bollerslev-Patton-Quaedvlieg (2016): HARQ
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from volforecast.models.base import VolModel


class _OLSModel(VolModel):
    _feature_cols: list[str]

    def __init__(self):
        self._results = None

    def _prepare_X(self, X: pd.DataFrame) -> pd.DataFrame:
        return sm.add_constant(X[self._feature_cols])

    def fit(self, X_train, y_train, X_val, y_val) -> None:
        Xc = self._prepare_X(X_train)
        self._results = sm.OLS(y_train, Xc).fit()

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        Xc = self._prepare_X(X)
        return np.maximum(self._results.predict(Xc), 1e-10)

    def feature_importance(self) -> pd.Series | None:
        return None


class HARModel(_OLSModel):
    name = "har"
    _feature_cols = ["rv_d", "rv_w", "rv_m"]


class HARJModel(_OLSModel):
    name = "har_j"
    _feature_cols = ["rv_d", "rv_w", "rv_m", "jump"]


class HARCJModel(_OLSModel):
    name = "har_cj"
    _feature_cols = ["bpv", "bpv_w", "bpv_m", "jump"]


class SHARModel(_OLSModel):
    name = "shar"
    _feature_cols = ["rv_pos", "rv_neg", "rv_w", "rv_m"]


class HARQModel(_OLSModel):
    name = "harq"
    _input_cols = ["rv_d", "rv_w", "rv_m", "rq_sqrt"]
    _feature_cols = ["rv_d", "rv_w", "rv_m", "harq_interaction"]

    def _prepare_X(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X[["rv_d", "rv_w", "rv_m"]].copy()
        df["harq_interaction"] = X["rv_d"] * X["rq_sqrt"]
        return sm.add_constant(df)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd volforecast && python -m pytest tests/test_models.py -v
```

- [ ] **Step 5: Commit**

```bash
git add volforecast/models/base.py volforecast/models/har.py tests/test_models.py
git commit -m "feat(models): add HAR, HAR-J, HAR-CJ, SHAR, HARQ baseline models"
```

---

### Task 7: Loss Functions (`evaluation/losses.py`)

**Files:**
- Create: `volforecast/volforecast/evaluation/losses.py`
- Create: `volforecast/tests/test_evaluation.py`

QLIKE and MSE loss functions per Patton (2011). These are the primary evaluation metrics.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_evaluation.py
import numpy as np
import pytest
from volforecast.evaluation.losses import qlike, mse, qlike_loss_lightgbm


class TestQLIKE:
    def test_perfect_forecast(self):
        actual = np.array([0.01, 0.02, 0.03])
        # QLIKE with perfect forecast: log(h) + sigma^2/h = log(actual) + 1
        result = qlike(actual, actual)
        expected = np.mean(np.log(actual) + 1.0)
        assert result == pytest.approx(expected)

    def test_underprediction_worse(self):
        actual = np.array([0.04, 0.04, 0.04])
        over = np.array([0.06, 0.06, 0.06])
        under = np.array([0.02, 0.02, 0.02])
        # QLIKE should penalize underprediction more
        assert qlike(actual, under) > qlike(actual, over)

    def test_scalar(self):
        result = qlike(np.array([0.03]), np.array([0.03]))
        assert np.isfinite(result)


class TestMSE:
    def test_perfect_forecast(self):
        actual = np.array([0.01, 0.02, 0.03])
        assert mse(actual, actual) == pytest.approx(0.0)

    def test_symmetric(self):
        actual = np.array([0.04, 0.04, 0.04])
        over = np.array([0.06, 0.06, 0.06])
        under = np.array([0.02, 0.02, 0.02])
        assert mse(actual, over) == pytest.approx(mse(actual, under))


class TestMincerZarnowitzDiagnostic:
    def test_perfect_forecast(self):
        from volforecast.evaluation.losses import mincer_zarnowitz
        actual = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
        result = mincer_zarnowitz(actual, actual)
        assert result["intercept"] == pytest.approx(0.0, abs=1e-6)
        assert result["slope"] == pytest.approx(1.0, abs=1e-6)
        assert result["r_squared"] == pytest.approx(1.0, abs=1e-6)

    def test_biased_forecast(self):
        from volforecast.evaluation.losses import mincer_zarnowitz
        actual = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
        forecast = actual * 0.5  # systematically under-predict
        result = mincer_zarnowitz(actual, forecast)
        assert result["slope"] != pytest.approx(1.0, abs=0.1)


class TestQLIKELightGBM:
    def test_gradient_at_perfect(self):
        y_true = np.array([0.04])
        y_pred = np.array([0.04])
        grad, hess = qlike_loss_lightgbm(y_true, y_pred)
        # At perfect forecast: grad = -RV/h^2 + 1/h = 0
        assert grad[0] == pytest.approx(0.0, abs=1e-10)
        assert hess[0] > 0  # hessian should be positive
```

- [ ] **Step 2: Implement losses.py**

```python
# volforecast/evaluation/losses.py
import numpy as np

_FLOOR = 1e-10


def qlike(actual: np.ndarray, forecast: np.ndarray) -> float:
    h = np.maximum(forecast, _FLOOR)
    return float(np.mean(np.log(h) + actual / h))


def mse(actual: np.ndarray, forecast: np.ndarray) -> float:
    return float(np.mean((actual - forecast) ** 2))


def qlike_loss_lightgbm(
    y_true: np.ndarray, y_pred: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Custom QLIKE objective for LightGBM. Returns (gradient, hessian)."""
    h = np.maximum(y_pred, _FLOOR)
    grad = -y_true / (h**2) + 1.0 / h
    hess = 2.0 * y_true / (h**3) - 1.0 / (h**2)
    hess = np.maximum(hess, _FLOOR)
    return grad, hess


def mincer_zarnowitz(
    actual: np.ndarray, forecast: np.ndarray
) -> dict[str, float]:
    """Mincer-Zarnowitz regression diagnostic.

    Regresses actual = alpha + beta * forecast + epsilon.
    Under forecast efficiency: alpha=0, beta=1.
    """
    import statsmodels.api as sm

    X = sm.add_constant(forecast)
    result = sm.OLS(actual, X).fit()
    return {
        "intercept": float(result.params[0]),
        "slope": float(result.params[1]),
        "r_squared": float(result.rsquared),
        "f_pvalue": float(result.f_pvalue),
    }
```

- [ ] **Step 3: Run tests, commit**

```bash
cd volforecast && python -m pytest tests/test_evaluation.py -v
git add volforecast/evaluation/losses.py tests/test_evaluation.py
git commit -m "feat(evaluation): add QLIKE, MSE, Mincer-Zarnowitz, and LightGBM QLIKE objective"
```

---

### Task 8: First Baseline Run (Sprint 1 Deliverable)

**Files:**
- Create: `volforecast/config/layer0_baselines.yaml`
- Create: `volforecast/notebooks/01_data_and_rv.ipynb`
- Create: `volforecast/notebooks/02_baselines.ipynb`

This task ties everything together: load data, compute features, fit HAR/SHAR/HARQ at h=1/5/22, evaluate on holdout with QLIKE/MSE, produce the first results table.

- [ ] **Step 1: Create baseline experiment config**

```yaml
# config/layer0_baselines.yaml
inherit: default.yaml

feature_layers: ["rv"]
models: ["har", "shar", "harq"]
training_mode: "per_symbol"

output:
  tables: "results/tables/sprint1_baselines.csv"
  figures: "results/figures/sprint1/"
```

- [ ] **Step 2: Create notebook 01_data_and_rv.ipynb**

Content outline:
1. Load RV parquet files for all 34 symbols
2. Summary statistics table (mean, std, min, max RV per symbol)
3. Volatility signature plot for one symbol (RV vs sampling frequency)
4. Time series plot of RV for SPY with crisis periods highlighted
5. Cross-symbol correlation heatmap of daily RV
6. Save summary stats to `results/tables/rv_summary.csv`

- [ ] **Step 3: Create notebook 02_baselines.ipynb**

Content outline:
1. Load RV features from Layer 0
2. Fit HAR, SHAR, HARQ per symbol on training data
3. Predict on holdout
4. Compute QLIKE and MSE per symbol per horizon
5. Produce headline table: mean QLIKE across symbols for each model x horizon
6. Box plot of per-symbol QLIKE distributions
7. Save to `results/tables/sprint1_baselines.csv`

- [ ] **Step 4: Run baseline experiment and verify results**

```bash
cd volforecast && jupyter nbconvert --execute notebooks/02_baselines.ipynb
```

- [ ] **Step 5: Commit Sprint 1 deliverable**

```bash
git commit -m "feat: Sprint 1 complete -- baseline QLIKE table for 34 symbols"
```

---

## Chunk 2: Sprint 2 -- First ML Comparison

### Task 9: LightGBM with Custom QLIKE Loss (`models/trees.py`)

**Files:**
- Create: `volforecast/volforecast/models/trees.py`
- Modify: `volforecast/tests/test_models.py`

LightGBM with custom QLIKE objective, constrained hyperparameters per Ch 11 of the learning guide. Supports both pooled and per-symbol training.

- [ ] **Step 1: Write failing tests**

Test that `LightGBMModel`:
- Accepts custom QLIKE objective
- Respects constrained hyperparameters (max_depth 3-5, min_child_samples 50-200)
- Produces non-negative predictions (variance must be positive)
- Returns feature importance as a pd.Series
- Works with `training_mode="pooled"` (multi-symbol DataFrame with symbol column)
- Works with `training_mode="per_symbol"` (single-symbol DataFrame)
- Early-stops on validation QLIKE

- [ ] **Step 2: Implement trees.py**

Key implementation details:
- Custom objective via `qlike_loss_lightgbm` from `evaluation/losses.py`
- Clip predictions to floor of 1e-10 (variance > 0)
- Default params: `max_depth=4, min_child_samples=100, learning_rate=0.03, n_estimators=1500, subsample=0.7, colsample_bytree=0.7, reg_lambda=5`
- Early stopping on validation set with patience=50

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "feat(models): add LightGBM with custom QLIKE objective"
```

---

### Task 10: Expanding-Window Purged CV (`evaluation/cv.py`)

**Files:**
- Create: `volforecast/volforecast/evaluation/cv.py`
- Modify: `volforecast/tests/test_evaluation.py`

Expanding-window purged cross-validation with horizon-scaled purge and fixed embargo.

- [ ] **Step 1: Write failing tests**

Test that `PurgedExpandingCV`:
- Creates 5 contiguous temporal folds
- For each test fold, training data is only from chronologically prior dates
- Purge window equals the horizon h (removes h days before each test fold start)
- Embargo removes 25 days after each test fold end from the next training set
- At h=22, data loss per boundary is ~47 days
- No date appears in both train and test for any fold
- Returns (train_idx, test_idx) tuples

- [ ] **Step 2: Implement cv.py**

Key: folds are contiguous time blocks. For fold k as test:
- Training = all dates strictly before `(fold_k_start - h - embargo)` where h = forecast horizon, embargo = 25 days
- The purge (h days) prevents label leakage: multi-day target windows at the boundary overlap with test dates
- The embargo (25 days) is an additional gap that guards against autocorrelation in *features* (e.g., rv_m uses 22-day rolling window, so features near the fold boundary still depend on test-period data). This is conservative but standard practice per de Prado (2018) Ch 7
- Net effect: training ends at `fold_k_start - h - 25` at the latest
- Data loss per fold boundary: h + 25 days (e.g., ~47 days at h=22, ~26 days at h=1)
- This is expanding-window: each successive fold sees a strictly larger training set

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "feat(evaluation): add expanding-window purged CV with horizon-scaled purge"
```

---

### Task 11: Diebold-Mariano Test (`evaluation/tests.py`)

**Files:**
- Create: `volforecast/volforecast/evaluation/tests.py`
- Modify: `volforecast/tests/test_evaluation.py`

Pairwise DM test with HAC standard errors (Newey-West) and Harvey-Leybourne-Newbold small-sample correction.

- [ ] **Step 1: Write failing tests**

Test that `diebold_mariano`:
- Returns DM statistic and p-value
- Detects significant difference between two forecasts with known properties (one systematically better)
- Returns p > 0.05 when forecasts are identical (plus noise)
- Uses t-distribution (HLN correction), not normal

- [ ] **Step 2: Implement tests.py**

DM test: compute loss differential series d_t = L(actual, forecast_A) - L(actual, forecast_B) using QLIKE loss. Estimate HAC variance with Newey-West, bandwidth = h - 1 (matches MA(h-1) structure in overlapping forecast errors, per West 1996). For h=1 bandwidth=0 (no HAC needed), h=5 bandwidth=4, h=22 bandwidth=21. DM stat = mean(d) / SE_HAC. Apply HLN correction: multiply by sqrt((T + 1 - 2h + h(h-1)/T) / T) and use t(T-1) distribution. Report one-sided p-value (testing whether model A improves over model B).

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "feat(evaluation): add Diebold-Mariano test with HAC and HLN correction"
```

---

### Task 12: Sprint 2 Deliverable -- ML vs HAR Comparison

**Files:**
- Create: `volforecast/config/layer0_ml.yaml`
- Modify: `volforecast/notebooks/02_baselines.ipynb`

- [ ] **Step 1: Configure experiment**

Layer 0 features + LightGBM (pooled and per-symbol) against HAR/SHAR/HARQ. Expanding-window purged CV on training data. DM test on holdout.

- [ ] **Step 2: Run experiment and produce comparison table**

QLIKE table: models (rows) x horizons (columns), with DM p-values vs HARQ. Separate rows for LightGBM pooled and per-symbol.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: Sprint 2 complete -- ML vs HAR comparison with DM significance"
```

---

## Chunk 3: Sprint 3-4 -- Feature Layers + Full Evaluation

### Task 13: Layer 1 -- Index Microstructure Features (`features/micro_features.py`)

**Files:**
- Create: `volforecast/volforecast/features/micro_features.py`
- Modify: `volforecast/tests/test_features.py`

E-mini index-level features: order flow imbalance (OFI), depth ratio, signed volume. These are market-level signals applied to all 34 symbols (see spec Section 2.2).

- [ ] **Step 1: Write failing tests**

Test that `MicroFeatureLayer`:
- Returns DataFrame with columns: `ofi`, `depth_ratio`, `signed_volume`
- All values are finite
- `describe()` references Cartea-Jaimungal-Penalva (2015)
- Uses E-mini data only (requires `emini_data` in data dict)

- [ ] **Step 2: Implement**

OFI = sum of signed volume at best bid/ask changes. Depth ratio = bid_depth / (bid_depth + ask_depth). Signed volume = sum(volume * sign(tick_direction)). Aggregate to daily frequency.

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "feat(features): add Layer 1 E-mini index microstructure features"
```

---

### Task 14: Layer 2 -- Options-Implied Features (`features/implied_features.py`)

**Files:**
- Create: `volforecast/volforecast/features/implied_features.py`
- Modify: `volforecast/tests/test_features.py`

IV surface features from ERDVOL: ATM IV, 25-delta skew, term slope, VRP proxy, VVIX.

- [ ] **Step 1: Write failing tests**

Test that `ImpliedFeatureLayer`:
- Returns: `atm_iv`, `skew_25d`, `term_slope`, `vrp_proxy`, `vvix`
- `atm_iv` is in annualized decimal variance (not percentage)
- `vrp_proxy` = VIX^2/10000 - trailing 22-day RV (requires both VIX and RV data)
- `term_slope` = 3m ATM IV - 1m ATM IV
- `describe()` references BTZ (2009), Bekaert-Hoerova (2014)

- [ ] **Step 2: Implement**

Load ERDVOL surface. Extract ATM IV at 30-day tenor. Compute 25-delta skew from the strike dimension. Term slope from the tenor dimension. VRP proxy from VIX and trailing RV.

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "feat(features): add Layer 2 options-implied features from ERDVOL"
```

---

### Task 15: Sprint 3 Deliverable -- Feature Layer Attribution

**Files:**
- Create: `volforecast/config/layer_attribution.yaml`
- Create: `volforecast/notebooks/03_feature_layers.ipynb`
- Output: `volforecast/results/tables/layer_attribution.csv`
- Output: `volforecast/results/figures/sprint3/`

- [ ] **Step 1: Run models with Layer 0 only, then 0+1, then 0+2, then 0+1+2**

Four experiment configs. Same models (HARQ + LightGBM pooled). Compare QLIKE on holdout.

- [ ] **Step 2: Produce attribution table**

Table: feature set (rows) x horizons (columns), showing QLIKE and delta-QLIKE vs Layer 0 baseline.

- [ ] **Step 3: Create notebook 03_feature_layers.ipynb**

- [ ] **Step 4: Commit**

```bash
git add config/layer_attribution.yaml notebooks/03_feature_layers.ipynb results/tables/layer_attribution.csv
git commit -m "feat: Sprint 3 complete -- feature layer QLIKE attribution"
```

---

### Task 16: Layer 3 -- Cross-Asset Features (`features/cross_features.py`)

**Files:**
- Create: `volforecast/volforecast/features/cross_features.py`
- Modify: `volforecast/tests/test_features.py`

Treasury curve features, FX/commodity vol, and Diebold-Yilmaz spillover index.

- [ ] **Step 1: Write failing tests**

Test that `CrossAssetFeatureLayer`:
- Returns: `yield_2y`, `yield_10y`, `term_spread_2s10s`, `fx_vol_usdjpy`, `commodity_vol_cl`, `dy_spillover_total`, `dy_spillover_from`, `dy_spillover_5d_chg`
- DY spillover computed from 200-day rolling VAR(1) on daily RV, generalized FEVD at H=10
- `dy_spillover_5d_chg` = 5-day change in total spillover index
- `describe()` references Diebold-Yilmaz (2012, 2014) -- 2014 paper for generalized FEVD

- [ ] **Step 2: Implement**

Treasury features: raw yields + term spread (10y-2y). FX/commodity: daily realized vol of returns. DY spillover: fit VAR(1) on 200-day rolling window of 34-symbol RV, compute generalized FEVD at H=10, extract total spillover index and directional FROM measures.

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "feat(features): add Layer 3 cross-asset and DY spillover features"
```

---

### Task 17: Model Confidence Set (`evaluation/tests.py`)

**Files:**
- Modify: `volforecast/volforecast/evaluation/tests.py`
- Modify: `volforecast/tests/test_evaluation.py`

Hansen-Lunde-Nason (2011) MCS procedure.

- [ ] **Step 1: Write failing tests**

Test that `model_confidence_set`:
- Returns set of surviving model names
- With one clearly dominated model and two close models, eliminates the dominated one
- Respects significance level (10%)
- Works on both per-symbol (returns per-symbol MCS) and pooled (returns one MCS)

- [ ] **Step 2: Implement**

MCS: iteratively eliminate the worst model (highest average loss relative to others) using the T_R (range) statistic and the equivalence test at significance alpha=0.10. Use stationary bootstrap (Politis-Romano) with 5,000 replications and mean block length = embargo period (25 days) to match the serial correlation structure. Stop when all remaining models are statistically indistinguishable.

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "feat(evaluation): add Model Confidence Set procedure"
```

---

### Task 18: SHAP Interpretability

**Files:**
- Create: `volforecast/volforecast/utils/interpretability.py`
- Create: `volforecast/tests/test_interpretability.py`

- [ ] **Step 1: Write failing tests**

Test that `SHAPAnalyzer`:
- Accepts a fitted LightGBM model and feature DataFrame
- Returns SHAP values as a DataFrame with same shape as input features
- `top_features(k=5)` returns the top k features by mean |SHAP|
- `stability_check(models_by_fold)` computes Kendall tau of top-5 rankings across CV folds and returns tau > 0.6 threshold
- `summary_plot()` and `importance_bar()` return matplotlib Figure objects

- [ ] **Step 2: Implement SHAP wrapper**

Wrapper around `shap.TreeExplainer` for the best-performing LightGBM model. Produces: SHAP summary plot, per-feature importance bar chart, ALE plots for top-3 features.

Follows Ch 10 importance stability protocol: compute across 5 CV folds, check top-5 ranking stability.

- [ ] **Step 3: Run tests, commit**

```bash
cd volforecast && python -m pytest tests/test_interpretability.py -v
git add volforecast/utils/interpretability.py tests/test_interpretability.py
git commit -m "feat(utils): add SHAP interpretability with stability protocol"
```

---

### Task 19: Sprint 4 Deliverable -- Full MCS Tournament

**Files:**
- Create: `volforecast/config/full_tournament.yaml`
- Create: `volforecast/notebooks/04_model_tournament.ipynb`
- Output: `volforecast/results/tables/mcs_membership.csv`
- Output: `volforecast/results/figures/sprint4/shap_summary.png`
- Output: `volforecast/results/figures/sprint4/importance_stability.png`

- [ ] **Step 1: Run all models x all feature layer combinations on holdout**

Combinations: {0}, {0+1}, {0+2}, {0+3}, {0+1+2}, {0+1+2+3}. Models: HARQ, LightGBM pooled.

- [ ] **Step 2: Produce MCS membership table (per-symbol and pooled)**
- [ ] **Step 3: Produce SHAP feature importance plots**
- [ ] **Step 4: Create notebook 04_model_tournament.ipynb**
- [ ] **Step 5: Commit**

```bash
git add config/full_tournament.yaml notebooks/04_model_tournament.ipynb results/
git commit -m "feat: Sprint 4 complete -- MCS membership table and SHAP interpretability"
```

---

## Chunk 4: Sprint 5-6 -- Signals and Economic Value

### Task 20: VRP Signal Construction (`signals/vrp.py`)

**Files:**
- Create: `volforecast/volforecast/signals/vrp.py`
- Create: `volforecast/tests/test_signals.py`

Three signal variants per spec Section 4.1.

- [ ] **Step 1: Write failing tests**

Test that:
- `signal_1_raw_gap(vix, rv_forecast_h22)` returns correct sign and magnitude
- Both inputs must be in annualized decimal variance
- `signal_2_term_structure(iv_surface, rv_forecasts)` computes gap at h=5 and h=22 (stubbed -- full implementation in Task 25)
- `signal_3_regime(signal2, regime_indicators)` scales position size down when regime is stressed (stubbed -- full implementation in Task 25)
- Regime indicators use trailing 252-day rolling percentiles: VVIX > 80th pct, VIX term structure in backwardation, model disagreement > 30% divergence

- [ ] **Step 2: Implement vrp.py**

Signal 1: `S1 = vix_var - rv_forecast_22` (fully implemented). Signal 2: stub returning NotImplementedError (completed in Task 25). Signal 3: stub returning NotImplementedError (completed in Task 25). Regime weight w = 1.0 normally, 0.3 when any indicator triggers (tunable parameter, not spec-pinned).

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "feat(signals): add VRP signal construction (3 variants)"
```

---

### Task 21: Vol-Targeting Position Sizing (`signals/sizing.py`)

**Files:**
- Create: `volforecast/volforecast/signals/sizing.py`
- Modify: `volforecast/tests/test_signals.py`

Moreira-Muir (2017) vol-targeting: w_t = sigma_target / sigma_hat_t.

- [ ] **Step 1: Write failing tests**

Test that:
- `vol_target_weights(forecasts, target=0.10)` returns correct weights
- Weight is >1 when forecast vol < target (lever up)
- Weight is <1 when forecast vol > target (reduce)
- Optional leverage cap at w_max=2.0
- EWMA baseline weights for comparison

- [ ] **Step 2: Implement sizing.py**

```python
def vol_target_weights(forecast_var, target_vol=0.10, max_leverage=2.0):
    forecast_vol = np.sqrt(np.maximum(forecast_var, 1e-10))
    weights = target_vol / forecast_vol
    return np.minimum(weights, max_leverage)
```

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "feat(signals): add vol-targeting position sizing"
```

---

### Task 22: Straddle Backtest (`signals/backtest.py` + `signals/costs.py`)

**Files:**
- Create: `volforecast/volforecast/signals/backtest.py`
- Create: `volforecast/volforecast/signals/costs.py`
- Modify: `volforecast/tests/test_signals.py`

Delta-hedged straddle P&L with daily gamma recomputation and transaction costs.

- [ ] **Step 1: Write failing tests**

Test that:
- `bs_gamma(S, K, T, r, sigma)` matches known Black-Scholes gamma values
- `straddle_pnl(signal, prices, iv, rv, r, direction)` accepts explicit `direction` parameter (+1 long, -1 short)
- Direction derived from signal sign: positive gap (IV > RV forecast) -> short vol (direction=-1)
- Transaction costs applied per-leg: straddle has 2 legs, total cost = 2 * cost_vol_points, amortized over holding period (22 trading days)
- P&L is reported net of costs
- Cost sensitivity: function accepts `cost_vol_points` parameter (default 0.5)

- [ ] **Step 2: Implement backtest.py and costs.py**

`costs.py`: flat cost model with configurable vol points per leg. For a straddle (2 legs), total entry cost = 2 * cost_vol_points (default 0.5 per leg = 1.0 total), amortized over holding period (22 trading days) so daily cost impact = total_cost / 22. `backtest.py`: daily loop computing `P&L_t = direction * 0.5 * Gamma_t * S_t^2 * (RV_daily_t - IV_annual/252) * dt` where `dt = 1/252` when using annualized quantities. Note: RV_daily_t is single-day realized variance (not annualized), IV_annual is annualized implied variance, and the `/ 252` converts IV to daily scale. Add a sanity test: daily P&L on $1 notional should be in the range of basis points to a few percent.

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "feat(signals): add straddle backtest with gamma recomputation and costs"
```

---

### Task 23: Economic Evaluation (`evaluation/economic.py`)

**Files:**
- Create: `volforecast/volforecast/evaluation/economic.py`
- Modify: `volforecast/tests/test_evaluation.py`

Sharpe, max drawdown, Calmar ratio, Deflated Sharpe Ratio.

- [ ] **Step 1: Write failing tests**

Test that:
- `sharpe_ratio(returns)` matches manual calculation
- `max_drawdown(returns)` correctly identifies worst peak-to-trough
- `calmar_ratio(returns)` = annualized_return / abs(max_drawdown)
- `deflated_sharpe(observed_sr, n_tests, T, skew, excess_kurt)` returns probability
- `excess_kurt` is excess kurtosis (scipy `kurtosis(fisher=True)`, normal=0)
- DSR < 0.95 when observed SR is below sqrt(2*ln(n_tests)) threshold
- Report both raw DSR and conservative DSR assuming all N=20 model comparisons are independent

- [ ] **Step 2: Implement economic.py**

DSR formula from Bailey-LdP (2014): DSR = Phi((SR - SR_0) * sqrt(T) / sqrt(1 - gamma_3*SR + gamma_4/4 * SR^2)) where SR_0 = sqrt(2*ln(N)), gamma_3 = skewness, gamma_4 = excess kurtosis. Note: `gamma_4` is EXCESS kurtosis (normal=0), not raw kurtosis.

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "feat(evaluation): add economic metrics (Sharpe, drawdown, Calmar, DSR)"
```

---

### Task 24: Sprint 5 Deliverable -- P&L Tables

- [ ] **Step 1: Run vol-targeting backtest** (EWMA vs HAR vs ML on SPX holdout)
- [ ] **Step 2: Run straddle backtest** (Signal 1 vs always-short-vol on SPX holdout)
- [ ] **Step 3: Run cost sensitivity** (0.25, 0.5, 1.0 vol points)
- [ ] **Step 4: Produce headline table** (per spec Section 4.3)
- [ ] **Step 5: Create notebook 05_signal_and_pnl.ipynb**
- [ ] **Step 6: Commit**

```bash
git commit -m "feat: Sprint 5 complete -- P&L table and cost sensitivity analysis"
```

---

### Task 25: Signal 2 + Signal 3 + Ensemble

**Files:**
- Modify: `volforecast/volforecast/signals/vrp.py` (Signal 2, 3 already stubbed)
- Create: `volforecast/volforecast/models/ensemble.py`

- [ ] **Step 1: Implement Signal 2** (term-structure-aware gap at h=5 and h=22)
- [ ] **Step 2: Implement Signal 3** (regime-conditional with trailing VVIX, VIX term structure, model disagreement)
- [ ] **Step 3: Implement HAR+Tree ensemble** (weighted blend with weight optimized on purged validation QLIKE)
- [ ] **Step 4: Test all, commit**

```bash
git commit -m "feat: add Signal 2/3 variants and HAR+Tree ensemble model"
```

---

### Task 26: Sprint 6 Deliverable -- Full Signal Comparison

- [ ] **Step 1: Run all three signal variants on holdout**
- [ ] **Step 2: Regime decomposition** (performance in calm vs stress periods, using Signal 3 regime indicators: VVIX > trailing 252-day 80th pct, VIX term structure backwardation, model disagreement > 30%)
- [ ] **Step 3: Produce signal comparison table and regime analysis plots**
- [ ] **Step 4: Update notebook 05_signal_and_pnl.ipynb with Signal 2/3 results**
- [ ] **Step 5: Commit**

```bash
git commit -m "feat: Sprint 6 complete -- full signal comparison and regime analysis"
```

---

## Dependency Graph

```
Task 0 (infrastructure)
  |
  +-> Task 1 (units) -> Task 2 (rv) -> Task 3 (universe) -> Task 4 (loaders)
  |                                                              |
  +-> Task 4b (targets) <---------------------------------------+
  |     |
  +-> Task 5 (Layer 0 features) <-------------------------------+
  |     |
  +-> Task 6 (HAR models) ----+
  |                            |
  +-> Task 7 (losses) --------+-> Task 8 (Sprint 1 deliverable)
                               |
  Task 9 (LightGBM) ----------+
  Task 10 (purged CV) --------+-> Task 12 (Sprint 2 deliverable)
  Task 11 (DM test) ----------+
                               |
  Task 13 (Layer 1) ----------+
  Task 14 (Layer 2) ----------+-> Task 15 (Sprint 3 deliverable)
                               |
  Task 16 (Layer 3) ----------+
  Task 17 (MCS) --------------+
  Task 18 (SHAP) -------------+-> Task 19 (Sprint 4 deliverable)
                               |
  Task 20 (VRP signal S1) ----+
  Task 21 (vol targeting) ----+
  Task 22 (straddle backtest)-+
  Task 23 (economic metrics) -+-> Task 24 (Sprint 5 deliverable)
                               |
  Task 25 (Signal 2/3, ensemble) -> Task 26 (Sprint 6 deliverable)
       (also depends on Tasks 6, 9 for HAR+Tree blend)
```

**Independent tasks that can be parallelized:**
- Tasks 1-4 are sequential (each depends on prior)
- Tasks 4b, 5, 6, 7 can run in parallel (all depend on Task 4)
- Tasks 9, 10, 11 can run in parallel (all depend on Task 8)
- Tasks 13, 14 can run in parallel (both depend on Task 12)
- Tasks 16, 17, 18 can run in parallel (depend on Task 15)
- Tasks 20, 21, 22, 23 can run in parallel (depend on Task 19)
