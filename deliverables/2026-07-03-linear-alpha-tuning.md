# Linear Alpha Tuning + Best-Linear-Model Tournament Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add leakage-safe, per-fold CV alpha selection for every regularized linear HAR model, then ship two trial configs (trial-077 tournament, trial-078 static alpha sweep) that settle which linear model is actually best per horizon.

**Architecture:** A new deterministic grid-search module (`linear_tuning.py`) scores (alpha, l1_ratio) combinations on an inner expanding-window CV using the exact QLIKE + Duan-correction protocol the outer runner uses. `_BaseOLS` gains a generic `tune_and_fit()` that plugs into the runner's *existing* tuning hooks (`supports_tuning` / `tune_every_n_folds` / `cached_params`), so no new fold-loop logic is needed. The factory that generates the ridge/lasso/elasticnet variants is fixed to accept and store alpha params (today it hardcodes defaults). Three runner gates that currently overload `supports_tuning` for unrelated behaviors (GPU param injection, `fit(on_progress=...)`, SHAP selection) are split onto dedicated capability flags so enabling tuning on linear models can't crash tree-model code paths.

**Tech Stack:** Python 3.12, scikit-learn 1.8.0 (Ridge/ElasticNet), pandas 3.0.2, numpy 2.2.6, pytest. No Optuna for linear tuning — exhaustive grid, deterministic.

## Global Constraints

- Code must run on the local Windows venv (`src/.venv/Scripts/python.exe`) AND the GS Linux box. No new dependencies.
- Real-data runs (`./vol run`) are **GS-only** (TSDB/Marquee). Everything local is synthetic-data unit/integration tests.
- Alpha selection must be leakage-safe: chosen only from inner folds inside the outer-fold training window, with a purge gap (project convention: `purge_gap: 10`).
- Determinism: identical inputs → identical chosen alpha. This requires adding `random_state=42` to every `ElasticNet(..., selection="random")` in `har_family.py`.
- Backward compatibility: with `tuning.enabled: false` (the default), every model must behave byte-identically to today. Default constructor alphas stay `ridge=1.0`, `lasso=(0.01, 0.95)`, `elasticnet=(0.01, 0.5)`.
- Registry model names are API — do not rename any model. Plain OLS models keep `supports_tuning = False`.
- Test commands run from repo root in Git Bash: `cd src && .venv/Scripts/python.exe -m pytest <path> -v`.
- 25 pre-existing test failures are environmental (gs_quant/pytickclient/menu/symlink) — the gate is **no NEW failures**, not zero failures.

## Background (read before Task 1)

- Trials 034/055/056 ran ridge/lasso/elasticnet HAR variants with **fixed** alphas (ridge α=1.0, lasso α=0.01/l1=0.95, enet α=0.01/l1=0.5). No alpha search ever ran, despite the trial-055 config comment claiming an "alpha sweep".
- Trial-055 recorded `ridge_har_cj_iv_0dte` h=1 QLIKE **0.13397**; trial-056 (different `feature_layers`, hence a different valid-row mask) recorded `lasso_shar_iv_0dte` **0.13663** as best, with the CJ family behind. The discrepancy is unresolved. Trial-077 settles it by running everything under one config (one row mask).
- The runner's tuning loop already exists (`src/volforecast/pipeline/runner.py:502-619`): if `config.tuning.enabled` and `model_cls.supports_tuning`, it calls `model_cls.tune_and_fit(X_train, y_train, self.config.tuning, base_params=model_params)` every `tune_every_n_folds` folds, caches `model.get_params()`, and re-instantiates `model_cls(**cached_params)` on in-between folds.
- **Bug you are fixing along the way:** the factory `_register_regularized_variants` (`src/volforecast/models/har_family.py:1637-1672`) generates `__init__(self)` with no params — so all 60 factory-generated regularized models (including every trial-055/056 winner) silently ignore any `params:` in YAML `model_configs` and cannot round-trip `get_params()`.
- **Gate overloads you must split (Task 4):** `runner.py:511` (SHAP selection), `runner.py:524` (GPU param injection — comment literally says "linear models don't accept GPU params"), `runner.py:610/616` (`fit(..., on_progress=...)` — linear `fit(X, y)` would raise TypeError; the pooled tournament passes `on_train_progress` callbacks, so this is a real crash, not theoretical).

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/volforecast/models/linear_tuning.py` | Create | Grid definitions + pure grid-search engine (no registry knowledge) |
| `src/volforecast/models/_base.py` | Modify | `_BaseOLS.get_params()`, `_BaseOLS.tune_and_fit()`, tuning-grid class attrs, capability flags on `_BaseModel` |
| `src/volforecast/models/har_family.py` | Modify | Factory accepts/stores alpha; post-registration flag rollout loop; `random_state=42` on ElasticNet |
| `src/volforecast/models/lightgbm.py`, `xgboost.py` | Modify | Set the three new capability flags True |
| `src/volforecast/pipeline/runner.py` | Modify | Re-key three gates off the new capability flags |
| `src/tests/unit/test_linear_tuning.py` | Create | Engine + `tune_and_fit` + factory + runner-integration tests |
| `workspace/configs/trial_077_linear_alpha_cv_tournament.yaml` | Create | The tuned linear tournament |
| `workspace/configs/trial_078_alpha_sensitivity_h1.yaml` | Create | Static outer-QLIKE alpha curve at h=1 |
| `workspace/research/trials.yaml` | Modify | Register trial-077 / trial-078 (`status: not_started`) |

---

### Task 0: Branch

- [ ] **Step 1: Create the working branch**

```bash
git checkout -b feat/linear-alpha-tuning
```

---

### Task 1: Grid-search engine (`linear_tuning.py`)

**Files:**
- Create: `src/volforecast/models/linear_tuning.py`
- Test: `src/tests/unit/test_linear_tuning.py`

**Interfaces:**
- Consumes: `volforecast.evaluation.metrics.qlike(y_true, y_pred)` (log-space default), `volforecast.utils.cv.ExpandingWindowCV(min_train_size, test_size, step_size, purge_gap)`.
- Produces (used by Task 2):
  - `RIDGE_ALPHA_GRID: list[float]`, `SPARSE_ALPHA_GRID: list[float]`, `ENET_L1_RATIO_GRID: list[float]`
  - `duan_correction(residuals: np.ndarray) -> float`
  - `tune_linear_alpha(model_cls, X_train: pd.DataFrame, y_train: pd.Series, param_grid: dict[str, list[float]], inner_cv_config) -> LinearTuningResult | None` where `LinearTuningResult` has `best_params: dict[str, float]`, `best_inner_qlike: float`, `grid_results: list[dict]`. Returns `None` when no inner fold could be scored (caller falls back to class defaults).

- [ ] **Step 1: Write the failing tests**

Create `src/tests/unit/test_linear_tuning.py`:

```python
"""Tests for deterministic linear-model alpha grid search (trial-077 infra)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.config import CVConfig


class _FakeRidge:
    """Minimal _BaseOLS-shaped model: predict = shrunken OLS on one feature.

    alpha=0 -> pure OLS slope; alpha -> inf -> slope shrunk to 0 (intercept only).
    Mimics sklearn Ridge on standardized X closely enough for ranking tests.
    """

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self._slope = 0.0
        self._intercept = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series):
        x = X.iloc[:, 0].values
        xc = x - x.mean()
        self._slope = float((xc @ (y.values - y.values.mean())) / (xc @ xc + self.alpha * len(x)))
        self._intercept = float(y.values.mean() - self._slope * x.mean())
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self._intercept + self._slope * X.iloc[:, 0].values


@pytest.fixture
def signal_data():
    """y strongly driven by x -> small alpha must win."""
    rng = np.random.default_rng(42)
    n = 400
    x = rng.normal(-8.0, 1.0, n)
    y = 0.9 * x + rng.normal(0.0, 0.1, n)
    return pd.DataFrame({"f": x}), pd.Series(y)


@pytest.fixture
def inner_cv():
    return CVConfig(method="expanding_window", purge_gap=5, train_size=150, test_size=50)


class TestDuanCorrection:
    def test_matches_runner_formula(self):
        from volforecast.models.linear_tuning import duan_correction

        resid = np.array([0.1, -0.2, 0.3, np.nan])
        valid = resid[~np.isnan(resid)]
        expected = float(np.log(np.mean(np.exp(np.clip(valid, -10.0, 10.0)))))
        assert duan_correction(resid) == pytest.approx(expected)

    def test_empty_returns_zero(self):
        from volforecast.models.linear_tuning import duan_correction

        assert duan_correction(np.array([np.nan, np.nan])) == 0.0


class TestTuneLinearAlpha:
    def test_prefers_small_alpha_on_strong_signal(self, signal_data, inner_cv):
        from volforecast.models.linear_tuning import tune_linear_alpha

        X, y = signal_data
        result = tune_linear_alpha(
            _FakeRidge, X, y, {"alpha": [1e-6, 1e6]}, inner_cv
        )
        assert result is not None
        assert result.best_params["alpha"] == 1e-6

    def test_one_grid_entry_per_combo(self, signal_data, inner_cv):
        from volforecast.models.linear_tuning import tune_linear_alpha

        X, y = signal_data
        result = tune_linear_alpha(
            _FakeRidge, X, y, {"alpha": [0.001, 1.0, 1000.0]}, inner_cv
        )
        assert len(result.grid_results) == 3
        assert all(np.isfinite(r["inner_qlike"]) for r in result.grid_results)
        assert all(r["n_folds"] >= 1 for r in result.grid_results)

    def test_deterministic(self, signal_data, inner_cv):
        from volforecast.models.linear_tuning import tune_linear_alpha

        X, y = signal_data
        r1 = tune_linear_alpha(_FakeRidge, X, y, {"alpha": [0.01, 1.0, 100.0]}, inner_cv)
        r2 = tune_linear_alpha(_FakeRidge, X, y, {"alpha": [0.01, 1.0, 100.0]}, inner_cv)
        assert r1.best_params == r2.best_params
        assert r1.best_inner_qlike == r2.best_inner_qlike

    def test_tie_breaks_toward_larger_alpha(self, inner_cv):
        from volforecast.models.linear_tuning import tune_linear_alpha

        # Pure-noise y with zero slope signal: shrinkage level is irrelevant,
        # so scores tie (or near-tie); ranking must still be deterministic and
        # documented: ties go to MORE regularization.
        rng = np.random.default_rng(0)
        n = 400
        X = pd.DataFrame({"f": np.zeros(n)})  # constant feature -> slope irrelevant
        y = pd.Series(rng.normal(-8.0, 0.5, n))
        result = tune_linear_alpha(_FakeRidge, X, y, {"alpha": [0.01, 100.0]}, inner_cv)
        assert result.best_params["alpha"] == 100.0

    def test_too_small_returns_none(self, inner_cv):
        from volforecast.models.linear_tuning import tune_linear_alpha

        X = pd.DataFrame({"f": np.zeros(50)})
        y = pd.Series(np.full(50, -8.0))
        # train_size=150 > 50 rows -> zero inner folds
        assert tune_linear_alpha(_FakeRidge, X, y, {"alpha": [1.0]}, inner_cv) is None
```

Note: `_FakeRidge` with a constant feature has `xc @ xc == 0`; guard in the fake by `+ self.alpha * len(x)` in the denominator already avoids division by zero for alpha > 0 (both grid values are > 0).

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd src && .venv/Scripts/python.exe -m pytest tests/unit/test_linear_tuning.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'volforecast.models.linear_tuning'`.

- [ ] **Step 3: Implement the module**

Create `src/volforecast/models/linear_tuning.py`:

```python
"""Deterministic alpha grid search for regularized linear (HAR-family) models.

Optuna-free hyperparameter search for Ridge/Lasso/ElasticNet HAR variants.
Called from _BaseOLS.tune_and_fit inside each outer CV fold: scores every
(alpha, l1_ratio) combination on an inner expanding-window CV using the same
QLIKE + Duan-correction protocol as the outer evaluation, then returns the
best parameters.

Kept separate from models/_base.py so the scoring logic is unit-testable
without touching the model registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any

import numpy as np
import pandas as pd

from volforecast.evaluation.metrics import qlike
from volforecast.utils.cv import ExpandingWindowCV

# Default grids. Features are standardized inside every regularized model's
# sklearn pipeline (StandardScaler) and targets are log-RV. With ~10k pooled
# training rows, meaningful ridge shrinkage needs large alphas; lasso/enet
# alphas live on the coordinate-descent scale where 0.1 already zeroes
# most coefficients.
RIDGE_ALPHA_GRID: list[float] = [
    0.01, 0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, 3000.0, 10000.0,
]
SPARSE_ALPHA_GRID: list[float] = [
    1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1,
]
ENET_L1_RATIO_GRID: list[float] = [0.2, 0.5, 0.8, 0.95]

# Inner folds with fewer scored rows than this are skipped (unstable QLIKE).
MIN_INNER_TEST_ROWS = 30


@dataclass
class LinearTuningResult:
    """Outcome of one grid search (one outer fold, one model class)."""

    best_params: dict[str, float]
    best_inner_qlike: float
    grid_results: list[dict[str, Any]]


def duan_correction(residuals: np.ndarray) -> float:
    """Log smearing factor. MUST match Pipeline._run_horizon (runner.py)."""
    valid = residuals[~np.isnan(residuals)]
    if len(valid) == 0:
        return 0.0
    return float(np.log(np.mean(np.exp(np.clip(valid, -10.0, 10.0)))))


def _score_combo(
    model_cls: type,
    params: dict[str, float],
    X: pd.DataFrame,
    y: pd.Series,
    folds: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[float, int]:
    """Mean inner-fold QLIKE (log space, Duan-corrected) for one param combo."""
    fold_scores: list[float] = []
    for train_idx, test_idx in folds:
        X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
        X_te, y_te = X.iloc[test_idx], y.iloc[test_idx]
        model = model_cls(**params)
        model.fit(X_tr, y_tr)
        corr = duan_correction(y_tr.values - model.predict(X_tr))
        preds = model.predict(X_te) + corr
        mask = ~(np.isnan(preds) | y_te.isna().values)
        if int(mask.sum()) < MIN_INNER_TEST_ROWS:
            continue
        fold_scores.append(qlike(y_te.values[mask], preds[mask]))
    if not fold_scores:
        return float("inf"), 0
    return float(np.mean(fold_scores)), len(fold_scores)


def tune_linear_alpha(
    model_cls: type,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    param_grid: dict[str, list[float]],
    inner_cv_config,
) -> LinearTuningResult | None:
    """Exhaustive grid search over param_grid on an inner expanding-window CV.

    Returns None when the training window is too small to build any inner
    fold (caller should fall back to class-default parameters). Ties are
    broken toward MORE regularization (larger alpha, then larger l1_ratio):
    when the data cannot distinguish shrinkage levels, prefer the more
    stable model.
    """
    cv = ExpandingWindowCV(
        min_train_size=inner_cv_config.train_size or max(252, len(X_train) // 2),
        test_size=inner_cv_config.test_size or 63,
        step_size=inner_cv_config.test_size or 63,
        purge_gap=inner_cv_config.purge_gap or 10,
    )
    folds = list(cv.split(X_train))
    if not folds:
        return None

    keys = sorted(param_grid)
    combos = [dict(zip(keys, vals)) for vals in product(*(param_grid[k] for k in keys))]

    grid_results: list[dict[str, Any]] = []
    for combo in combos:
        score, n_folds = _score_combo(model_cls, combo, X_train, y_train, folds)
        grid_results.append({"params": combo, "inner_qlike": score, "n_folds": n_folds})

    def _rank(entry: dict[str, Any]) -> tuple[float, float, float]:
        p = entry["params"]
        return (entry["inner_qlike"], -p.get("alpha", 0.0), -p.get("l1_ratio", 0.0))

    best = min(grid_results, key=_rank)
    if not np.isfinite(best["inner_qlike"]):
        return None
    return LinearTuningResult(
        best_params=dict(best["params"]),
        best_inner_qlike=float(best["inner_qlike"]),
        grid_results=grid_results,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd src && .venv/Scripts/python.exe -m pytest tests/unit/test_linear_tuning.py -v
```

Expected: all `TestDuanCorrection` + `TestTuneLinearAlpha` tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/volforecast/models/linear_tuning.py src/tests/unit/test_linear_tuning.py
git commit -m "feat(models): deterministic alpha grid-search engine for linear HAR models"
```

---

### Task 2: `_BaseOLS.tune_and_fit` + `get_params`

**Files:**
- Modify: `src/volforecast/models/_base.py`
- Test: `src/tests/unit/test_linear_tuning.py` (append)

**Interfaces:**
- Consumes: `tune_linear_alpha`, grids from Task 1; `TuningConfig` fields `search_space: dict[str, dict] | None`, `inner_cv: CVConfig | None` (already parsed from YAML at `config.py:631-647` — no config changes needed).
- Produces (used by Task 3 and the runner):
  - Class attrs on `_BaseOLS`: `_ALPHA_GRID: list[float] | None = None`, `_L1_RATIO_GRID: list[float] | None = None` (subclasses with a non-None `_ALPHA_GRID` are tunable).
  - `get_params(self) -> dict[str, float]` — returns `{"alpha": ...}` plus `l1_ratio` when the instance has one; `{}` for plain OLS. Must satisfy `cls(**model.get_params())` (the runner's cached-params round-trip at `runner.py:607-609`).
  - `tune_and_fit(cls, X_train, y_train, tuning_config, base_params=None) -> _BaseOLS` — fitted model with `model.tuning_result_` set (a `LinearTuningResult`, or `None` on fallback).
  - `search_space` YAML override format: `{"alpha": {"values": [..]}, "l1_ratio": {"values": [..]}}`. Keys the class doesn't support are ignored.

- [ ] **Step 1: Write the failing tests**

Append to `src/tests/unit/test_linear_tuning.py`:

```python
class _TunableOLS:
    """Registered-shape _BaseOLS subclass for tune_and_fit tests."""


def _make_tunable_cls():
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline as SKPipeline
    from sklearn.preprocessing import StandardScaler

    from volforecast.models._base import _BaseOLS

    class TunableRidge(_BaseOLS):
        _FEATURES = None
        _ALPHA_GRID = [1e-6, 1e6]

        supports_tuning = True

        def __init__(self, alpha: float = 1.0):
            pipe = SKPipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
            super().__init__(model=pipe)
            self.alpha = alpha

        def fit(self, X, y):
            self._fit(X, y)
            return self

    return TunableRidge


class TestBaseOLSTuneAndFit:
    def test_base_ols_not_tunable_by_default(self):
        from volforecast.models._base import _BaseOLS

        assert _BaseOLS.supports_tuning is False
        assert _BaseOLS._ALPHA_GRID is None

    def test_get_params_roundtrip(self):
        cls = _make_tunable_cls()
        m = cls(alpha=3.5)
        assert m.get_params() == {"alpha": 3.5}
        m2 = cls(**m.get_params())
        assert m2.alpha == 3.5

    def test_plain_ols_get_params_empty(self):
        from volforecast.models._base import _BaseOLS

        assert _BaseOLS().get_params() == {}

    def test_tune_and_fit_picks_grid_winner(self, signal_data, inner_cv):
        from volforecast.config import TuningConfig

        cls = _make_tunable_cls()
        X, y = signal_data
        cfg = TuningConfig(enabled=True, inner_cv=inner_cv)
        model = cls.tune_and_fit(X, y, cfg)
        assert model.alpha == 1e-6                      # strong signal -> min shrinkage
        assert model.coefficients_ is not None          # refit on full outer train
        assert model.tuning_result_ is not None
        assert len(model.tuning_result_.grid_results) == 2

    def test_search_space_override(self, signal_data, inner_cv):
        from volforecast.config import TuningConfig

        cls = _make_tunable_cls()
        X, y = signal_data
        cfg = TuningConfig(
            enabled=True,
            inner_cv=inner_cv,
            search_space={"alpha": {"values": [7.0]}},
        )
        model = cls.tune_and_fit(X, y, cfg)
        assert model.alpha == 7.0

    def test_fallback_to_defaults_when_train_too_small(self, inner_cv):
        from volforecast.config import TuningConfig

        cls = _make_tunable_cls()
        rng = np.random.default_rng(1)
        X = pd.DataFrame({"f": rng.normal(-8, 1, 60)})
        y = pd.Series(rng.normal(-8, 1, 60))
        cfg = TuningConfig(enabled=True, inner_cv=inner_cv)  # train_size=150 > 60
        model = cls.tune_and_fit(X, y, cfg)
        assert model.alpha == 1.0                       # constructor default
        assert model.tuning_result_ is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd src && .venv/Scripts/python.exe -m pytest tests/unit/test_linear_tuning.py::TestBaseOLSTuneAndFit -v
```

Expected: FAIL — `_BaseOLS` has no attribute `_ALPHA_GRID` / `get_params` returns AttributeError / `tune_and_fit` raises `NotImplementedError`.

- [ ] **Step 3: Implement in `_base.py`**

At the top of `src/volforecast/models/_base.py` add:

```python
import logging

logger = logging.getLogger(__name__)
```

In `_BaseModel`, directly under `supports_tuning: bool = False`, add the capability flags (defaults; Task 4 sets them True on the tree models):

```python
    # Capability flags — deliberately separate from supports_tuning, which
    # only means "tune_and_fit() exists". The runner keys these behaviours
    # off the flags below instead of overloading supports_tuning:
    supports_fit_progress: bool = False    # fit(X, y, on_progress=...) accepted
    supports_shap_selection: bool = False  # TreeSHAP feature selection is valid
    accepts_gpu_device: bool = False       # constructor accepts gpu_device_id
```

In `_BaseOLS`, add class attrs after `_FEATURES`:

```python
    # Alpha-tuning hooks. har_family.py sets these on every registered
    # ridge_/lasso_/elasticnet_ variant; None means "not tunable".
    _ALPHA_GRID: list[float] | None = None
    _L1_RATIO_GRID: list[float] | None = None
```

And add two methods to `_BaseOLS` (after `predict`):

```python
    def get_params(self) -> dict[str, float]:
        """Constructor-kwarg snapshot for the runner's cached-params re-fit."""
        params: dict[str, float] = {}
        for key in ("alpha", "l1_ratio"):
            val = getattr(self, key, None)
            if val is not None:
                params[key] = val
        return params

    @classmethod
    def tune_and_fit(
        cls,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        tuning_config,
        base_params: dict | None = None,
    ):
        """Grid-search (alpha, l1_ratio) on inner CV, refit best on full fold.

        Falls back to class-default parameters when the outer training
        window is too small to build inner folds.
        """
        from volforecast.config import CVConfig
        from volforecast.models.linear_tuning import tune_linear_alpha

        if cls._ALPHA_GRID is None:
            raise NotImplementedError(
                f"{cls.__name__} has no tunable parameters (set _ALPHA_GRID)."
            )

        search_space = tuning_config.search_space or {}

        def _grid(key: str, default: list[float] | None) -> list[float] | None:
            if default is None:
                return None
            override = search_space.get(key) or {}
            values = override.get("values")
            if values:
                return [float(v) for v in values]
            return list(default)

        param_grid: dict[str, list[float]] = {"alpha": _grid("alpha", cls._ALPHA_GRID)}
        l1_grid = _grid("l1_ratio", cls._L1_RATIO_GRID)
        if l1_grid is not None:
            param_grid["l1_ratio"] = l1_grid

        inner_cv = tuning_config.inner_cv or CVConfig(
            method="expanding_window",
            purge_gap=10,
            train_size=max(252, len(X_train) // 2),
            test_size=63,
        )
        result = tune_linear_alpha(cls, X_train, y_train, param_grid, inner_cv)
        if result is None:
            model = cls()
            model.tuning_result_ = None
        else:
            model = cls(**result.best_params)
            model.tuning_result_ = result
            logger.info(
                "%s: tuned %s (inner QLIKE %.5f over %d combos)",
                cls.__name__,
                result.best_params,
                result.best_inner_qlike,
                len(result.grid_results),
            )
        model.fit(X_train, y_train)
        return model
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd src && .venv/Scripts/python.exe -m pytest tests/unit/test_linear_tuning.py -v
```

Expected: all PASS (Task 1 tests still green).

- [ ] **Step 5: Commit**

```bash
git add src/volforecast/models/_base.py src/tests/unit/test_linear_tuning.py
git commit -m "feat(models): _BaseOLS.tune_and_fit + get_params for alpha CV selection"
```

---

### Task 3: Factory params + flag rollout in `har_family.py`

**Files:**
- Modify: `src/volforecast/models/har_family.py` (factory at :1637-1672; pipe helpers at :918-960; end-of-module rollout loop)
- Test: `src/tests/unit/test_linear_tuning.py` (append)

**Interfaces:**
- Consumes: grids from Task 1, `_ALPHA_GRID`/`_L1_RATIO_GRID`/`supports_tuning` semantics from Task 2.
- Produces: every registry model named `ridge_*`, `lasso_*`, `elasticnet_*` that subclasses `_BaseOLS` (60 factory + ~24 manual classes) has `supports_tuning=True`, correct grids, an alpha-accepting constructor, and deterministic coefficients. Plain OLS models unchanged.

- [ ] **Step 1: Write the failing tests**

Append to `src/tests/unit/test_linear_tuning.py`:

```python
class TestRegistryTuningFlags:
    @pytest.fixture(autouse=True)
    def _register(self):
        from volforecast.registry import ensure_registered

        ensure_registered()

    def test_factory_variants_accept_and_store_alpha(self):
        from volforecast.models import MODEL_REGISTRY

        m = MODEL_REGISTRY["ridge_har_cj_iv_0dte"](alpha=42.0)
        assert m.alpha == 42.0
        assert m.get_params() == {"alpha": 42.0}
        # alpha actually reaches the sklearn estimator
        assert m._model.named_steps["ridge"].alpha == 42.0

        m2 = MODEL_REGISTRY["lasso_shar_iv_0dte"](alpha=0.05, l1_ratio=0.9)
        assert m2.get_params() == {"alpha": 0.05, "l1_ratio": 0.9}

    def test_factory_defaults_unchanged(self):
        from volforecast.models import MODEL_REGISTRY

        assert MODEL_REGISTRY["ridge_har_cj_iv_0dte"]().alpha == 1.0
        lasso = MODEL_REGISTRY["lasso_shar_iv_0dte"]()
        assert (lasso.alpha, lasso.l1_ratio) == (0.01, 0.95)
        enet = MODEL_REGISTRY["elasticnet_shar_cj_iv_0dte"]()
        assert (enet.alpha, enet.l1_ratio) == (0.01, 0.5)

    def test_all_regularized_variants_flagged(self):
        from volforecast.models import MODEL_REGISTRY
        from volforecast.models._base import _BaseOLS
        from volforecast.models.linear_tuning import (
            ENET_L1_RATIO_GRID,
            RIDGE_ALPHA_GRID,
            SPARSE_ALPHA_GRID,
        )

        checked = 0
        for name, cls in MODEL_REGISTRY.items():
            if not (isinstance(cls, type) and issubclass(cls, _BaseOLS)):
                continue
            prefix = name.split("_", 1)[0]
            if prefix == "ridge":
                assert cls.supports_tuning is True, name
                assert cls._ALPHA_GRID == RIDGE_ALPHA_GRID, name
                assert cls._L1_RATIO_GRID is None, name
            elif prefix == "lasso":
                assert cls.supports_tuning is True, name
                assert cls._ALPHA_GRID == SPARSE_ALPHA_GRID, name
                assert cls._L1_RATIO_GRID is None, name
            elif prefix == "elasticnet":
                assert cls.supports_tuning is True, name
                assert cls._ALPHA_GRID == SPARSE_ALPHA_GRID, name
                assert cls._L1_RATIO_GRID == ENET_L1_RATIO_GRID, name
            else:
                assert cls.supports_tuning is False, f"OLS model {name} must stay untunable"
                continue
            # every tunable class round-trips its constructor
            inst = cls()
            cls(**inst.get_params())
            checked += 1
        assert checked >= 80  # 60 factory + >=20 manual regularized variants

    def test_elasticnet_fit_is_deterministic(self):
        from volforecast.models import MODEL_REGISTRY

        rng = np.random.default_rng(3)
        n = 300
        X = pd.DataFrame(
            {
                "log_rs_positive_d": rng.normal(-9, 0.5, n),
                "log_rs_negative_d": rng.normal(-9, 0.5, n),
                "log_rv_w": rng.normal(-8, 0.4, n),
                "log_rv_m": rng.normal(-8, 0.3, n),
                "log_atm_iv_0dte_d": rng.normal(-2, 0.2, n),
            }
        )
        y = pd.Series(X["log_rv_w"] * 0.6 + rng.normal(0, 0.3, n))
        m1 = MODEL_REGISTRY["lasso_shar_iv_0dte"]().fit(X, y)
        m2 = MODEL_REGISTRY["lasso_shar_iv_0dte"]().fit(X, y)
        np.testing.assert_array_equal(m1.coefficients_, m2.coefficients_)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd src && .venv/Scripts/python.exe -m pytest tests/unit/test_linear_tuning.py::TestRegistryTuningFlags -v
```

Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'alpha'` on the factory test; flag assertions fail on `supports_tuning is False`.

- [ ] **Step 3: Implement**

**(a)** In `_make_lasso_pipe` (har_family.py:926) and `_make_enet_pipe` (:944), add `random_state=42` to the `ElasticNet(...)` call, e.g.:

```python
                    alpha=alpha, l1_ratio=l1_ratio, max_iter=2000, tol=1e-3,
                    selection="random", random_state=42
```

Then grep for every other inline `selection="random"` in the file (the manual Lasso/ElasticNet class bodies, e.g. `LassoHARModel`, `LassoHARIVModel`, `ElasticNetHARIVModel`, `LassoHARIV0dteModel`, `ElasticNetHARIV0dteModel`, `LassoHARIVRateVolModel`, the `_1w` variants) and add `random_state=42` to each `ElasticNet(...)` constructor:

```bash
grep -n 'selection="random"' src/volforecast/models/har_family.py
```

Every hit must gain `random_state=42`.

**(b)** Replace `_register_regularized_variants` (:1637-1672) with:

```python
def _register_regularized_variants(
    base_name: str,
    features: list[str],
    required_layers: list[str],
) -> None:
    """Generate and register ridge/lasso/elasticnet variants of an OLS model.

    Constructors accept and store alpha (and l1_ratio for lasso/elasticnet)
    so YAML model_configs params reach the estimator and get_params()
    round-trips for the runner's tuning cache.
    """

    def _ridge_init(pfn):
        def __init__(self, alpha: float = 1.0):
            _BaseHAR.__init__(self, model=pfn(alpha))
            self.alpha = alpha
        return __init__

    def _sparse_init(pfn, default_l1: float):
        def __init__(self, alpha: float = 0.01, l1_ratio: float = default_l1):
            _BaseHAR.__init__(self, model=pfn(alpha, l1_ratio))
            self.alpha = alpha
            self.l1_ratio = l1_ratio
        return __init__

    def _make_fit():
        def fit(self, X, y):
            self._fit(X, y)
            return self
        return fit

    specs = [
        ("ridge", _ridge_init(_make_ridge_pipe)),
        ("lasso", _sparse_init(_make_lasso_pipe, 0.95)),
        ("elasticnet", _sparse_init(_make_enet_pipe, 0.5)),
    ]
    for prefix, init in specs:
        reg_name = f"{prefix}_{base_name}"
        cls = type(
            reg_name,
            (_BaseHAR,),
            {
                "REQUIRED_LAYERS": required_layers,
                "_FEATURES": list(features),
                "__init__": init,
                "fit": _make_fit(),
            },
        )
        register_model(reg_name)(cls)
```

**(c)** At the very end of `har_family.py` (after the `for _base, _feats, _layers in _NEW_HYBRID_SPECS:` loop), add the flag rollout:

```python
# ---------------------------------------------------------------------------
# Alpha-tuning flags: every registered ridge/lasso/elasticnet linear variant
# (manual or factory-generated) becomes grid-tunable via _BaseOLS.tune_and_fit.
# Plain OLS variants stay supports_tuning=False (nothing to tune).
# ---------------------------------------------------------------------------
from volforecast.models.linear_tuning import (  # noqa: E402
    ENET_L1_RATIO_GRID,
    RIDGE_ALPHA_GRID,
    SPARSE_ALPHA_GRID,
)
from volforecast.registry import MODEL_REGISTRY  # noqa: E402

for _name, _cls in list(MODEL_REGISTRY.items()):
    if not (isinstance(_cls, type) and issubclass(_cls, _BaseOLS)):
        continue
    _prefix = _name.split("_", 1)[0]
    if _prefix == "ridge":
        _cls.supports_tuning = True
        _cls._ALPHA_GRID = RIDGE_ALPHA_GRID
    elif _prefix == "lasso":
        _cls.supports_tuning = True
        _cls._ALPHA_GRID = SPARSE_ALPHA_GRID
    elif _prefix == "elasticnet":
        _cls.supports_tuning = True
        _cls._ALPHA_GRID = SPARSE_ALPHA_GRID
        _cls._L1_RATIO_GRID = ENET_L1_RATIO_GRID
```

(This runs at `har_family` import time; `har_family` itself registers every `ridge_/lasso_/elasticnet_` linear model, so the loop is complete by construction. `lasso_*` keeps `l1_ratio` fixed at its constructor default — only alpha is searched; l1_ratio≈0.95 is what makes it "lasso".)

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd src && .venv/Scripts/python.exe -m pytest tests/unit/test_linear_tuning.py -v
```

Expected: all PASS.

- [ ] **Step 5: Guard against collateral damage**

```bash
cd src && .venv/Scripts/python.exe -m pytest tests/unit -k "har or formulas or tournament or config" -q
```

Expected: same pass/fail set as before this task (compare against a pre-task run if unsure; the 25 known environmental failures don't overlap these filters except `config_picker` ×4 on Windows).

- [ ] **Step 6: Commit**

```bash
git add src/volforecast/models/har_family.py src/tests/unit/test_linear_tuning.py
git commit -m "feat(models): tunable alpha on all regularized HAR variants + deterministic ElasticNet"
```

---

### Task 4: Runner gate disambiguation + end-to-end tuning through `Pipeline._run_horizon`

**Files:**
- Modify: `src/volforecast/pipeline/runner.py:508-524, 610-616`
- Modify: `src/volforecast/models/lightgbm.py` (class `LightGBMVolModel`, near `supports_tuning = True` at :171)
- Modify: `src/volforecast/models/xgboost.py` (class `XGBoostVolModel`, near `supports_tuning = True` at :128)
- Test: `src/tests/unit/test_linear_tuning.py` (append)

**Why:** three runner behaviors currently key off `supports_tuning` and were written assuming "tunable == tree model". With linear models now tunable, each would misfire: SHAP selection (`:508-512`) would attempt TreeSHAP on OLS; GPU injection (`:524`) would pass `gpu_device_id` to constructors that reject it; `fit(X, y, on_progress=...)` (`:610/616`) would TypeError because linear `fit` has no `on_progress` — and pooled tournaments DO pass `on_train_progress` callbacks.

**Interfaces:**
- Consumes: capability flags added to `_BaseModel` in Task 2 (`supports_fit_progress`, `supports_shap_selection`, `accepts_gpu_device`, all default False).
- Produces: `LightGBMVolModel` and `XGBoostVolModel` set all three flags True; runner gates re-keyed. `supports_tuning` now means exactly "has tune_and_fit()".

- [ ] **Step 1: Write the failing tests**

Append to `src/tests/unit/test_linear_tuning.py`:

```python
class TestRunnerIntegration:
    @pytest.fixture(autouse=True)
    def _register(self):
        from volforecast.registry import ensure_registered

        ensure_registered()

    @pytest.fixture
    def hariv_panel(self):
        """Synthetic X with ridge_har_iv's exact _FEATURES + log-RV target."""
        rng = np.random.default_rng(7)
        n = 400
        X = pd.DataFrame(
            {
                "log_rv_d": rng.normal(-8, 1.0, n),
                "log_rv_w": rng.normal(-8, 0.5, n),
                "log_rv_m": rng.normal(-8, 0.3, n),
                "log_atm_iv_d": rng.normal(-2, 0.2, n),
            },
            index=pd.bdate_range("2022-01-03", periods=n),
        )
        y = pd.Series(
            0.5 * X["log_rv_d"] + 0.3 * X["log_rv_w"] + rng.normal(0, 0.3, n),
            index=X.index,
        )
        return X, y

    def _make_cfg(self, tmp_path, inner_cv):
        from volforecast.config import (
            CVConfig,
            ExperimentConfig,
            ModelConfig,
            TuningConfig,
        )

        return ExperimentConfig(
            name="tuning_it",
            universe=["TEST"],
            date_range=("2022-01-03", "2023-08-01"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="ridge_har_iv", params={}),
            cv=CVConfig(method="expanding_window", purge_gap=5, train_size=150, test_size=50),
            tuning=TuningConfig(
                enabled=True,
                tune_every_n_folds=2,
                min_train_size=100,
                inner_cv=inner_cv,
                search_space={"alpha": {"values": [0.1, 10.0]}},
            ),
            output_dir=tmp_path,
        )

    def test_tuned_linear_model_through_run_horizon(self, hariv_panel, inner_cv, tmp_path, monkeypatch):
        from volforecast.models import MODEL_REGISTRY
        from volforecast.pipeline.runner import Pipeline
        from volforecast.utils.cv import ExpandingWindowCV

        X, y = hariv_panel
        cfg = self._make_cfg(tmp_path, inner_cv)
        model_cls = MODEL_REGISTRY["ridge_har_iv"]

        tune_calls: list[int] = []
        orig = model_cls.tune_and_fit.__func__

        def spy(cls, *args, **kwargs):
            tune_calls.append(1)
            return orig(cls, *args, **kwargs)

        monkeypatch.setattr(model_cls, "tune_and_fit", classmethod(spy))

        progress_pings: list[tuple] = []
        result = Pipeline(cfg)._run_horizon(
            X,
            y,
            ExpandingWindowCV(min_train_size=150, test_size=50, step_size=50, purge_gap=5),
            model_cls,
            h=1,
            on_train_progress=lambda *a: progress_pings.append(a),
        )

        # 4 outer folds (n=400, start 150, step 50), tune_every=2 -> folds 1 and 3 tune
        assert len(tune_calls) == 2
        assert np.isfinite(result["metrics"]["qlike"])
        # linear models don't emit fit progress; the callback must simply not crash
        assert progress_pings == []
        # tuned alpha came from the search_space, and cached refits used it too
        assert result["model"].alpha in (0.1, 10.0)

    def test_capability_flags_on_tree_models(self):
        lgbm = pytest.importorskip("lightgbm")  # noqa: F841
        from volforecast.models.lightgbm import LightGBMVolModel

        assert LightGBMVolModel.supports_fit_progress is True
        assert LightGBMVolModel.supports_shap_selection is True
        assert LightGBMVolModel.accepts_gpu_device is True

    def test_capability_flags_on_xgboost(self):
        xgb = pytest.importorskip("xgboost")  # noqa: F841
        from volforecast.models.xgboost import XGBoostVolModel

        assert XGBoostVolModel.supports_fit_progress is True
        assert XGBoostVolModel.supports_shap_selection is True
        assert XGBoostVolModel.accepts_gpu_device is True

    def test_linear_models_do_not_accept_gpu(self):
        from volforecast.models import MODEL_REGISTRY

        cls = MODEL_REGISTRY["ridge_har_cj_iv_0dte"]
        assert cls.accepts_gpu_device is False
        assert cls.supports_fit_progress is False
        assert cls.supports_shap_selection is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd src && .venv/Scripts/python.exe -m pytest tests/unit/test_linear_tuning.py::TestRunnerIntegration -v
```

Expected: `test_tuned_linear_model_through_run_horizon` FAILS with `TypeError: fit() got an unexpected keyword argument 'on_progress'` (the :610 gate fires because ridge_har_iv now has `supports_tuning=True`); flag tests fail with AttributeError/False.

- [ ] **Step 3: Implement**

**(a)** `src/volforecast/models/lightgbm.py` — in `LightGBMVolModel`, next to `supports_tuning = True` (:171), add:

```python
    supports_fit_progress = True
    supports_shap_selection = True
    accepts_gpu_device = True
```

**(b)** `src/volforecast/models/xgboost.py` — in `XGBoostVolModel`, next to `supports_tuning = True` (:128), add the same three lines.

**(c)** `src/volforecast/pipeline/runner.py` — three replacements:

At :508-512, change the SHAP gate:

```python
        fs_enabled = (
            fs_config is not None
            and fs_config.enabled
            and getattr(model_cls, "supports_shap_selection", False)
        )
```

At :521-525, change the GPU-injection gate (keep the comment, update it):

```python
        # Pin this horizon to a specific GPU (for multi-GPU parallelism).
        # Only inject gpu_device_id for models whose constructors accept it
        # (tree models); linear models don't take GPU params.
        if gpu_device_id is not None and getattr(model_cls, "accepts_gpu_device", False):
            model_params["gpu_device_id"] = gpu_device_id
```

At :610 and :616, change both progress gates:

```python
                if on_train_progress and getattr(model_cls, "supports_fit_progress", False):
```

Leave `runner.py:502` (tuning gate) and `:2621-2624` (sequence-path HPO gate) untouched — those are genuine `supports_tuning` semantics.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd src && .venv/Scripts/python.exe -m pytest tests/unit/test_linear_tuning.py -v
```

Expected: all PASS.

- [ ] **Step 5: Regression check on the runner/tree-model surface**

```bash
cd src && .venv/Scripts/python.exe -m pytest tests/unit -k "xgboost or lightgbm or feature_selection or fold_cache or experiment" -q
```

Expected: same pass/fail set as before this task (LightGBM×5 optuna-symlink failures are pre-existing on Windows unless Developer Mode is on).

- [ ] **Step 6: Commit**

```bash
git add src/volforecast/pipeline/runner.py src/volforecast/models/lightgbm.py src/volforecast/models/xgboost.py src/volforecast/models/_base.py src/tests/unit/test_linear_tuning.py
git commit -m "fix(runner): split fit-progress/SHAP/GPU gates off supports_tuning; enable linear tuning path"
```

---

### Task 5: Trial-077 config — the tuned linear tournament

**Files:**
- Create: `workspace/configs/trial_077_linear_alpha_cv_tournament.yaml`
- Modify: `workspace/research/trials.yaml` (append entry)

**Design decisions baked into the YAML:**
- One config → one valid-row mask → the 055-vs-056 discrepancy cannot recur. `feature_layers` is the minimal union for the roster: `[iv_surface, har_core, asymmetry, noise_robust, options]` (no `cross_asset` — trial-055 had it and its data availability gated rows; no `calendar`/`tree_expansion` — linear models select only their `_FEATURES` columns).
- **No LightGBM/XGBoost in the roster.** With `tuning.enabled: true` global, any `supports_tuning` tree model would launch Optuna HPO — expensive and it would change the champion reference mid-comparison. Champion numbers come from trial-063/067 as usual.
- `tune_every_n_folds: 1` — linear grid search is milliseconds per fit; re-select alpha every outer fold.
- `inner_cv`: train 252 / test 63 / purge 10 → 3 inner folds inside each 504-row outer train window.
- `dh/vt/gsvivs` off: this is a pure QLIKE hunt; signal evaluation comes later for the winner.
- OLS twins stay in the roster untuned — they are the controls that isolate "alpha tuning" from "feature set".

- [ ] **Step 1: Write the config**

Create `workspace/configs/trial_077_linear_alpha_cv_tournament.yaml`:

```yaml
# Trial-077: Linear Tournament with Per-Fold CV Alpha Selection
#
# Hypothesis: (1) CV-selected alpha beats the fixed alphas used in trials
# 034/055/056 for at least some regularized HAR variants; (2) running the
# full 055+056 roster under ONE config (one valid-row mask) settles the
# unresolved h=1 discrepancy (055: ridge_har_cj_iv_0dte 0.13397 vs
# 056: lasso_shar_iv_0dte 0.13663) and identifies the true best linear
# model per horizon.
#
# Infra: tuning.enabled=true triggers _BaseOLS.tune_and_fit (deterministic
# grid search, no Optuna) for every ridge_/lasso_/elasticnet_ model. Grids:
#   ridge alpha:      0.01 .. 10000 (11 log-spaced)
#   lasso/enet alpha: 1e-5 .. 0.1   (9 log-spaced)
#   enet l1_ratio:    0.2 / 0.5 / 0.8 / 0.95
# OLS variants are untuned controls. NO tree models in this roster —
# global tuning would trigger Optuna HPO on them.
#
# Success criterion: any tuned variant beats its fixed-alpha 055/056
# QLIKE by >5 bps at the matching horizon, OR the tournament crowns a
# single h=1 winner with DM p<0.05 vs har_iv_0dte.
#
# Baseline for stats: har_iv (same as 055/056 registry entries).

name: trial_077_linear_alpha_cv_tournament

universe:
  - SPY
  - AAPL
  - MSFT
  - NVDA
  - AVGO
  - GOOGL
  - AMZN
  - V
  - MA
  - XOM
  - PG
  - JNJ
  - HD
  - NFLX
  - TSLA
  - CRM
  - UNH
  - BAC
  - ADBE
  - IWM
  - DIA

date_range: ["2015-01-02", "2026-05-30"]
horizons: [1, 5, 22]

# Minimal union for this roster. Deliberately excludes cross_asset (055) and
# calendar/tree_expansion (056) so the valid-row mask is identical for all
# models and comparable across both prior tournaments' feature sets.
feature_layers: [iv_surface, har_core, asymmetry, noise_robust, options]

# Primary model slot (placeholder — tournament runs the full roster)
model:
  name: ridge_har_cj_iv_0dte
  params: {}

cv:
  method: expanding_window
  purge_gap: 10
  train_size: 504
  test_size: 126

tuning:
  enabled: true
  tune_every_n_folds: 1     # linear fits are cheap; re-select alpha every fold
  min_train_size: 252
  inner_cv:
    method: expanding_window
    purge_gap: 10
    train_size: 252
    test_size: 63
  # search_space omitted -> per-class default grids from linear_tuning.py

tournament:
  gsvivs_enabled: false
  dh_enabled: false
  vt_enabled: false
  mcs_bootstrap: 10000
  parallel_models: 4
  baseline: har_iv
  models:
    # --- OLS controls (untuned) ---
    - har
    - har_iv
    - har_iv_1w
    - har_iv_0dte
    - shar_iv_0dte
    - har_cj_iv_0dte
    - shar_cj_iv_0dte
    - sharq_cj_iv_0dte
    - har_iv_freq
    - har_iv_freq_vrp
    - har_cj_iv_freq
    - har_cj_iv_freq_vrp
    - shar_iv_freq
    - shar_cj_iv_freq
    - shar_cj_iv_freq_vrp
    - sharq_cj_iv_freq
    - sharq_cj_iv_freq_vrp
    - har_iv_optimal
    - har_iv_2tenor
    - har_iv_noise
    - harq_iv
    - harq_iv_1w
    - shar_iv
    - shar_iv_1w

    # --- Tuned: simple HAR-IV family (trial-034 said fixed-alpha ridge = OLS;
    #     does TUNED alpha change that?) ---
    - ridge_har_iv
    - ridge_har_iv_1w
    - ridge_har_iv_0dte
    - lasso_har_iv
    - lasso_har_iv_1w
    - lasso_har_iv_0dte
    - elasticnet_har_iv
    - elasticnet_har_iv_1w
    - elasticnet_har_iv_0dte

    # --- Tuned: SHAR-IV family ---
    - ridge_shar_iv
    - ridge_shar_iv_1w
    - ridge_shar_iv_0dte
    - lasso_shar_iv
    - lasso_shar_iv_1w
    - lasso_shar_iv_0dte
    - elasticnet_shar_iv
    - elasticnet_shar_iv_1w
    - elasticnet_shar_iv_0dte

    # --- Tuned: HARQ-IV family ---
    - ridge_harq_iv
    - ridge_harq_iv_1w
    - lasso_harq_iv
    - lasso_harq_iv_1w
    - elasticnet_harq_iv
    - elasticnet_harq_iv_1w

    # --- Tuned: multi-tenor + noise ---
    - ridge_har_iv_2tenor
    - lasso_har_iv_2tenor
    - elasticnet_har_iv_2tenor
    - ridge_har_iv_noise
    - lasso_har_iv_noise
    - elasticnet_har_iv_noise

    # --- Tuned: CJ + IV (trial-055 h=1 winner family) ---
    - ridge_har_cj_iv_0dte
    - lasso_har_cj_iv_0dte
    - elasticnet_har_cj_iv_0dte

    # --- Tuned: combined decompositions ---
    - ridge_shar_cj_iv_0dte
    - lasso_shar_cj_iv_0dte
    - elasticnet_shar_cj_iv_0dte
    - ridge_sharq_cj_iv_0dte
    - lasso_sharq_cj_iv_0dte
    - elasticnet_sharq_cj_iv_0dte

    # --- Tuned: frequency-matched IV + VRP families ---
    - ridge_har_iv_freq
    - lasso_har_iv_freq
    - elasticnet_har_iv_freq
    - ridge_har_iv_freq_vrp
    - lasso_har_iv_freq_vrp
    - elasticnet_har_iv_freq_vrp
    - ridge_har_iv_optimal
    - lasso_har_iv_optimal
    - elasticnet_har_iv_optimal
    - ridge_shar_iv_freq
    - lasso_shar_iv_freq
    - elasticnet_shar_iv_freq
    - ridge_har_cj_iv_freq
    - lasso_har_cj_iv_freq
    - elasticnet_har_cj_iv_freq
    - ridge_har_cj_iv_freq_vrp
    - lasso_har_cj_iv_freq_vrp
    - elasticnet_har_cj_iv_freq_vrp
    - ridge_shar_cj_iv_freq
    - lasso_shar_cj_iv_freq
    - elasticnet_shar_cj_iv_freq
    - ridge_shar_cj_iv_freq_vrp
    - lasso_shar_cj_iv_freq_vrp
    - elasticnet_shar_cj_iv_freq_vrp
    - ridge_sharq_cj_iv_freq
    - lasso_sharq_cj_iv_freq
    - elasticnet_sharq_cj_iv_freq
    - ridge_sharq_cj_iv_freq_vrp
    - lasso_sharq_cj_iv_freq_vrp
    - elasticnet_sharq_cj_iv_freq_vrp

training_mode: pooled
seed: 42
output_dir: data/models/trial_077_linear_alpha_cv_tournament
```

- [ ] **Step 2: Local smoke test — config parses and every model resolves**

```bash
cd src && .venv/Scripts/python.exe -c "
from volforecast.config import ExperimentConfig
from volforecast.models import MODEL_REGISTRY
from volforecast.registry import ensure_registered
ensure_registered()
c = ExperimentConfig.from_yaml('../workspace/configs/trial_077_linear_alpha_cv_tournament.yaml')
missing = [m for m in c.tournament.models if m not in MODEL_REGISTRY]
assert not missing, f'unknown models: {missing}'
assert c.tuning.enabled and c.tuning.tune_every_n_folds == 1
assert c.tuning.inner_cv.train_size == 252
tuned = [m for m in c.tournament.models if MODEL_REGISTRY[m].supports_tuning]
print(f'{len(c.tournament.models)} models, {len(tuned)} tunable — OK')
"
```

Expected output: `105 models, 81 tunable — OK` (counts must match the roster; adjust the assertion message only if you deliberately changed the roster).

- [ ] **Step 3: Register the trial**

Append to `workspace/research/trials.yaml` (match the existing `status: not_started` entry style, e.g. trial-075):

```yaml
- id: trial-077
  date: '2026-07-03'
  config: trial_077_linear_alpha_cv_tournament.yaml
  hypothesis: Per-fold CV alpha selection (deterministic grid, inner expanding-window
    CV, QLIKE+Duan scoring) improves at least some regularized HAR variants over the
    fixed alphas used in trials 034/055/056, and running the full 055+056 roster under
    one config (one valid-row mask) settles the h=1 discrepancy (055 ridge_har_cj_iv_0dte
    0.13397 vs 056 lasso_shar_iv_0dte 0.13663) to crown the true best linear model
    per horizon.
  motivation: All prior regularized runs used fixed alphas (ridge 1.0, lasso 0.01/0.95,
    enet 0.01/0.5) — no alpha search ever ran. Trial-034 found regularization irrelevant
    for 4-param HAR-IV, but never tested tuned alphas on the richer 5-10 param CJ/SHAR
    decompositions where shrinkage has room to matter. The 055-vs-056 winner conflict
    is explained by different feature_layers gating different valid rows.
  baseline_config: trial_056_har_hybrid_tournament.yaml
  horizons: {}
  status: not_started
  priority: 1
```

- [ ] **Step 4: Commit**

```bash
git add workspace/configs/trial_077_linear_alpha_cv_tournament.yaml workspace/research/trials.yaml
git commit -m "feat(configs): trial-077 linear tournament with CV alpha selection"
```

---

### Task 6: Trial-078 config — static alpha-sensitivity curve at h=1

**Files:**
- Create: `workspace/configs/trial_078_alpha_sensitivity_h1.yaml`
- Modify: `workspace/research/trials.yaml` (append entry)

**Purpose:** trial-077 reports only the tuned result; it cannot show *how much* QLIKE the old fixed alphas left on the table, nor whether inner-CV selection lands near the outer optimum. Trial-078 pins alphas explicitly (tuning disabled) for the two h=1 contender families and traces the outer-QLIKE-vs-alpha curve. Depends on Task 3 (factory constructors must accept `alpha` for `model_configs` params to work — today they are silently ignored).

- [ ] **Step 1: Write the config**

Create `workspace/configs/trial_078_alpha_sensitivity_h1.yaml`:

```yaml
# Trial-078: Static Alpha Sensitivity at h=1 — outer-QLIKE curve
#
# Companion to trial-077. Pins alpha explicitly per tournament entry
# (tuning DISABLED) for the two h=1 contender families:
#   ridge_har_cj_iv_0dte  (trial-055 winner, ran at fixed alpha=1.0)
#   lasso_shar_iv_0dte    (trial-056 winner, ran at fixed alpha=0.01)
# plus an elasticnet cross-check on shar_cj_iv_0dte.
#
# Questions answered:
#   1. Shape of outer QLIKE vs alpha — was the fixed alpha near-optimal?
#   2. Validation of trial-077's inner-CV selection: the tuned QLIKE should
#      land within a few bps of this curve's minimum.
#
# NOTE: model_configs params only reach factory-generated variants after the
# Task-3 constructor fix (before it, {alpha: X} raised TypeError... nothing —
# it was silently impossible; the factory __init__ took no params).

name: trial_078_alpha_sensitivity_h1

universe:
  - SPY
  - AAPL
  - MSFT
  - NVDA
  - AVGO
  - GOOGL
  - AMZN
  - V
  - MA
  - XOM
  - PG
  - JNJ
  - HD
  - NFLX
  - TSLA
  - CRM
  - UNH
  - BAC
  - ADBE
  - IWM
  - DIA

date_range: ["2015-01-02", "2026-05-30"]
horizons: [1]

feature_layers: [iv_surface, har_core, asymmetry, noise_robust, options]

model:
  name: ridge_har_cj_iv_0dte
  params: {}

cv:
  method: expanding_window
  purge_gap: 10
  train_size: 504
  test_size: 126

tournament:
  gsvivs_enabled: false
  dh_enabled: false
  vt_enabled: false
  mcs_bootstrap: 10000
  parallel_models: 4
  baseline: har_iv_0dte
  models:
    # OLS anchors
    - har_iv_0dte
    - har_cj_iv_0dte
    - shar_iv_0dte
    - shar_cj_iv_0dte
    # ridge_har_cj_iv_0dte alpha curve (7 points; 1.0 = trial-055's fixed value)
    - ridge_cj_a0p01
    - ridge_cj_a0p1
    - ridge_cj_a1
    - ridge_cj_a10
    - ridge_cj_a100
    - ridge_cj_a1000
    - ridge_cj_a10000
    # lasso_shar_iv_0dte alpha curve (5 points; 0.01 = trial-056's fixed value)
    - lasso_shar_a1e5
    - lasso_shar_a1e4
    - lasso_shar_a1e3
    - lasso_shar_a1e2
    - lasso_shar_a1e1
    # elasticnet_shar_cj_iv_0dte cross-grid (alpha x l1_ratio)
    - enet_sharcj_a1e3_l02
    - enet_sharcj_a1e3_l08
    - enet_sharcj_a1e2_l02
    - enet_sharcj_a1e2_l08
  model_configs:
    ridge_cj_a0p01:
      name: ridge_har_cj_iv_0dte
      params: {alpha: 0.01}
    ridge_cj_a0p1:
      name: ridge_har_cj_iv_0dte
      params: {alpha: 0.1}
    ridge_cj_a1:
      name: ridge_har_cj_iv_0dte
      params: {alpha: 1.0}
    ridge_cj_a10:
      name: ridge_har_cj_iv_0dte
      params: {alpha: 10.0}
    ridge_cj_a100:
      name: ridge_har_cj_iv_0dte
      params: {alpha: 100.0}
    ridge_cj_a1000:
      name: ridge_har_cj_iv_0dte
      params: {alpha: 1000.0}
    ridge_cj_a10000:
      name: ridge_har_cj_iv_0dte
      params: {alpha: 10000.0}
    lasso_shar_a1e5:
      name: lasso_shar_iv_0dte
      params: {alpha: 0.00001}
    lasso_shar_a1e4:
      name: lasso_shar_iv_0dte
      params: {alpha: 0.0001}
    lasso_shar_a1e3:
      name: lasso_shar_iv_0dte
      params: {alpha: 0.001}
    lasso_shar_a1e2:
      name: lasso_shar_iv_0dte
      params: {alpha: 0.01}
    lasso_shar_a1e1:
      name: lasso_shar_iv_0dte
      params: {alpha: 0.1}
    enet_sharcj_a1e3_l02:
      name: elasticnet_shar_cj_iv_0dte
      params: {alpha: 0.001, l1_ratio: 0.2}
    enet_sharcj_a1e3_l08:
      name: elasticnet_shar_cj_iv_0dte
      params: {alpha: 0.001, l1_ratio: 0.8}
    enet_sharcj_a1e2_l02:
      name: elasticnet_shar_cj_iv_0dte
      params: {alpha: 0.01, l1_ratio: 0.2}
    enet_sharcj_a1e2_l08:
      name: elasticnet_shar_cj_iv_0dte
      params: {alpha: 0.01, l1_ratio: 0.8}

training_mode: pooled
seed: 42
output_dir: data/models/trial_078_alpha_sensitivity_h1
```

- [ ] **Step 2: Local smoke test — labels resolve and params reach constructors**

```bash
cd src && .venv/Scripts/python.exe -c "
from volforecast.config import ExperimentConfig
from volforecast.evaluation._model_utils import resolve_model
from volforecast.models import MODEL_REGISTRY
from volforecast.registry import ensure_registered
ensure_registered()
c = ExperimentConfig.from_yaml('../workspace/configs/trial_078_alpha_sensitivity_h1.yaml')
for label in c.tournament.models:
    reg, disp, params = resolve_model(label, model_configs=c.tournament.model_configs)
    inst = MODEL_REGISTRY[reg](**params)   # TypeError here = factory fix missing
    if params:
        assert inst.get_params()['alpha'] == params['alpha'], label
print(f'{len(c.tournament.models)} labels instantiate with pinned alphas — OK')
"
```

Expected output: `20 labels instantiate with pinned alphas — OK`.

- [ ] **Step 3: Register the trial**

Append to `workspace/research/trials.yaml`:

```yaml
- id: trial-078
  date: '2026-07-03'
  config: trial_078_alpha_sensitivity_h1.yaml
  hypothesis: The outer-QLIKE-vs-alpha curve at h=1 for ridge_har_cj_iv_0dte and
    lasso_shar_iv_0dte quantifies how much the fixed alphas of trials 055/056 left
    on the table, and trial-077's inner-CV-selected alpha lands within a few bps
    of this curve's minimum (validating the selection protocol).
  motivation: Trial-077 reports only the CV-selected point. A static sweep with
    pinned alphas (tuning disabled) traces the full sensitivity curve, separating
    "alpha tuning helps" from "alpha selection works". Requires the factory
    constructor fix — before it, model_configs params could not reach the
    factory-generated regularized variants at all.
  baseline_config: trial_077_linear_alpha_cv_tournament.yaml
  horizons: {}
  status: not_started
  priority: 2
  depends_on: trial-077
```

- [ ] **Step 4: Commit**

```bash
git add workspace/configs/trial_078_alpha_sensitivity_h1.yaml workspace/research/trials.yaml
git commit -m "feat(configs): trial-078 static alpha-sensitivity sweep at h=1"
```

---

### Task 7: Full regression gate + GS handoff

- [ ] **Step 1: Full non-slow suite**

```bash
cd src && .venv/Scripts/python.exe -m pytest tests/ -m "not slow" -q
```

Expected: **no NEW failures** versus the pre-existing environmental baseline (~25 failures on this Windows box: gs_quant/pytickclient absence, empty data cache, `simple-term-menu`, optuna symlink — see `ml-vol-estimator/local-dev/regression-baseline.txt` for the reference list). Any new failure traces back to Tasks 1-4 — fix before proceeding.

- [ ] **Step 2: Lint the touched files**

```bash
cd src && .venv/Scripts/python.exe -m ruff check volforecast/models/linear_tuning.py volforecast/models/_base.py volforecast/models/har_family.py volforecast/pipeline/runner.py tests/unit/test_linear_tuning.py
```

Expected: no NEW errors on the touched lines (the repo has 143 pre-existing lint errors; don't fix unrelated ones).

- [ ] **Step 3: Commit any fixes, then hand off**

GS-box execution steps (cannot run locally — document, don't attempt):

```bash
# On the GS box, after syncing the branch:
./vol run --config workspace/configs/trial_077_linear_alpha_cv_tournament.yaml
# then, after reviewing 077:
./vol run --config workspace/configs/trial_078_alpha_sensitivity_h1.yaml
```

Runtime estimate for 077: ~81 tunable models × 3 horizons × ~18 outer folds × (11-36 combos × 3 inner folds) small OLS fits — a few hours at `parallel_models: 4`. Chosen alphas appear in the run log as `RidgeHARCJ...: tuned {'alpha': ...}` INFO lines; per-fold grids live on each saved model's `tuning_result_`.

**Recording results:** fill in the trial-077/078 `horizons:` blocks in `workspace/research/trials.yaml` with `best_model`/`best_qlike`/`har_iv` reference per horizon (055/056 entry style), flip `status: completed`, and add a `key_insight` answering: (a) did tuned alpha beat fixed alpha by >5 bps anywhere, (b) which single linear model is the true h=1/h=5/h=22 best on the shared row mask, (c) does 055's 0.13397 replicate without `cross_asset` row-gating.

---

## Self-Review (completed during planning)

- **Spec coverage:** alpha-tuning infra (Tasks 1-4), configs to start the experiments (Tasks 5-6), true-best-linear question addressed via single-row-mask design + controls + sensitivity sweep. The 055/056 discrepancy is explicitly targeted.
- **Placeholder scan:** none — all code, YAML, and commands are complete.
- **Type consistency:** `tune_linear_alpha(model_cls, X_train, y_train, param_grid, inner_cv_config)` matches its Task-2 call site; `LinearTuningResult.best_params/grid_results` match Task-2's `tuning_result_` assertions; capability flag names identical across Tasks 2 and 4; `get_params()` round-trip matches `runner.py:607-609` usage.
- **Known risks:** (1) `ExperimentConfig` construction in the Task-4 test uses only fields with defaults beyond the six required ones — if a field was added since, mirror `_make_config` in `src/tests/unit/test_fold_cache.py`. (2) The Task-5 smoke-test counts (105/81) must be recomputed if the roster is edited. (3) `random_state=42` on ElasticNet shifts existing lasso/enet coefficients within numerical noise — expected, and required for the determinism test.
