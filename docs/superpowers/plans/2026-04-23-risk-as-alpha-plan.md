# Risk as Alpha — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test whether SecDB risk-system outputs (VaR, scenario P&L, factor decompositions) predict cross-asset returns, volatility, and drawdowns — turning risk controls into alpha signals.

**Architecture:** Shared validation/backtesting infrastructure feeding two potential signal pipelines (risk-system features and book-level Greeks), with a data-driven checkpoint at week 13 to decide depth vs. pivot. All signals evaluated against a ridge baseline with rigorous anti-overfitting methodology (purged CV, DSR, CPCV).

**Tech Stack:** Python, LightGBM, scikit-learn (Ridge/ElasticNet), gs-quant, Slang/SecDB, mlfinlab, alphalens, pyfolio, shap, MLflow/W&B

**Spec:** `docs/superpowers/specs/2026-04-23-risk-as-alpha-design.md`

---

## Chunk 1: Phase 0 — Pitch & Alignment (Weeks 1-2)

### Task 1: Environment & Package Audit

**Files:**
- Create: `environment/package_audit.md`
- Create: `environment/requirements.txt`

- [ ] **Step 1: Audit Python environment**

Document which Python version and package manager is available on GS compute. Run:
```bash
python --version
pip list | grep -E "lightgbm|xgboost|scikit-learn|shap|pandas|numpy"
```

- [ ] **Step 2: Test availability of external packages**

Attempt to install or confirm presence of each required package:
```bash
pip install --dry-run lightgbm shap mlfinlab alphalens-reloaded pyfolio-reloaded
```
Document which succeed and which are blocked. For blocked packages, identify internal equivalents or plan to vendor the code.

- [ ] **Step 3: Test gs-quant access**

```python
from gs_quant.session import GsSession, Environment
from gs_quant.markets import PricingContext, HistoricalPricingContext
from gs_quant.data import Dataset

# Confirm session initializes
GsSession.use(Environment.PROD, client_id='...', client_secret='...')
print("gs-quant session OK")
```

- [ ] **Step 4: Write requirements.txt**

Pin versions for all confirmed-available packages. Document any internal substitutions.

- [ ] **Step 5: Document findings in package_audit.md**

Record: available packages, blocked packages, internal equivalents, compute constraints (memory, GPU, job scheduler).

---

### Task 2: Data Access Audit

**Files:**
- Create: `data/access_audit.md`
- Create: `notebooks/00_data_exploration.ipynb`

- [ ] **Step 1: Enumerate accessible risk cube nodes**

Using Slang or the Python-SecDB bridge, list all risk cube outputs you have read entitlements for. Focus on:
- Firm-level VaR (daily)
- Component VaR by asset class
- Factor-VaR decomposition
- Scenario P&L (standard stress scenarios)
- VaR utilization (usage vs. limit)

```python
# Pseudocode — adapt to actual SecDB/Slang API
risk_nodes = secdb.query("risk_cube", desk="XA", measures=["VaR", "ComponentVaR", "ScenarioPnL"])
print(f"Available nodes: {len(risk_nodes)}")
for node in risk_nodes:
    print(f"  {node.name}: {node.frequency}, {node.history_start} to {node.history_end}")
```

- [ ] **Step 2: Pull sample data for each accessible measure**

For each confirmed measure, pull 5 business days of data to verify:
- Schema (columns, types, granularity)
- Frequency (daily vs. intraday)
- History depth (how far back does it go?)
- Timestamp semantics (when is this data *known*? T+0 EOD? T+1 morning?)

- [ ] **Step 3: Check the Minimum Viable Data Gate**

Confirm you have at minimum:
- (a) Daily firm-level or desk-level VaR with component breakdown by asset class
- (b) At least one of: scenario P&L, factor-VaR decomposition, or VaR utilization

If FAIL: document what's missing, discuss with sponsor before proceeding.

- [ ] **Step 4: Investigate risk-model methodology changes**

Interview the risk team or review documentation:
- Has the VaR methodology changed in the lookback period? (Historical sim → Monte Carlo, window changes)
- Any regime breaks in the risk-model that would create spurious features?
- Document dates of any known methodology changes.

- [ ] **Step 5: Document findings in access_audit.md**

Record for each measure: name, frequency, history depth, timestamp semantics, granularity (firm/desk/book), any known methodology breaks. Flag any surprises.

- [ ] **Step 6: Document in exploration notebook**

Create `notebooks/00_data_exploration.ipynb` with sample pulls, basic summary stats (mean, std, autocorrelation, missing data %), and time-series plots of each accessible measure. This notebook is a living reference.

---

### Task 3: Pitch Document

**Files:**
- Create: `deliverables/pitch.md`

- [ ] **Step 1: Draft the pitch**

1-2 pages structured as:
1. **The opportunity** (2-3 sentences): intermediary asset pricing theory predicts X; we have the data to test it daily, cross-asset, with real dealer sign.
2. **What the literature shows** (3-4 sentences): He-Krishnamurthy, Adrian-Etula-Muir, He-Kelly-Manela — all use stale quarterly data. Adrian-Shin shows dealer repos forecast VIX. Theory is strong; data has been the bottleneck.
3. **What I'll build** (3-4 sentences): extract daily risk-system features, test predictive power for cross-asset returns/vol/drawdowns using LightGBM with rigorous validation (purged CV, DSR). Ridge baseline on all tests.
4. **Timeline** (bullet points): 20-week plan with checkpoint at week 13.
5. **What I need** (bullet points): confirmed read access to [specific measures from Task 2], compute for ML training, weekly 30-min check-in.

- [ ] **Step 2: Review with sponsor**

Present the pitch. Get explicit sign-off on:
- The project direction
- Data access (any additional entitlements needed?)
- Compliance constraints on documentation/output
- Week 13 checkpoint meeting scheduled
- Backup reviewer identified

- [ ] **Step 3: Update pitch.md with sponsor feedback**

Record any scope adjustments, additional data sources suggested, or constraints imposed.

---

### Task 4: Holdout Reservation & Experiment Log

**Files:**
- Create: `data/holdout_config.json`
- Create: `experiments/experiment_log.csv`

- [ ] **Step 1: Define holdout period**

Based on history depth found in Task 2, reserve the most recent 3-6 months as true OOS:

```json
{
  "holdout_start": "2026-01-01",
  "holdout_end": "2026-04-23",
  "reason": "True out-of-sample for Phase 5 walk-forward test. DO NOT USE for feature engineering, model training, or validation until Phase 5.",
  "defined_date": "2026-04-23"
}
```

- [ ] **Step 2: Initialize experiment log**

```csv
experiment_id,date,description,features,target,model,cv_method,sharpe_raw,sharpe_dsr,ic_mean,ic_std,notes
```

Every model run gets logged here. This is the input for honest DSR adjustment — the total number of trials matters.

---

## Chunk 2: Phase 1 — Shared Infrastructure (Weeks 3-5)

### Task 5: Data Pipeline Module

**Files:**
- Create: `src/data/pipeline.py`
- Create: `src/data/point_in_time.py`
- Create: `tests/data/test_pipeline.py`
- Create: `tests/data/test_point_in_time.py`

- [ ] **Step 1: Write failing test for point-in-time stamping**

```python
# tests/data/test_point_in_time.py
import pandas as pd
from src.data.point_in_time import stamp_knowledge_time

def test_pit_stamps_with_knowledge_date():
    """Feature values should be stamped with when they were KNOWN, not when they applied."""
    raw = pd.DataFrame({
        "date": pd.to_datetime(["2025-01-02", "2025-01-03"]),
        "var_total": [100.0, 105.0],
    })
    # VaR for date T is known at T+1 morning (after nightly risk run)
    result = stamp_knowledge_time(raw, date_col="date", lag_days=1)
    assert "knowledge_date" in result.columns
    assert result["knowledge_date"].iloc[0] == pd.Timestamp("2025-01-03")
    assert result["knowledge_date"].iloc[1] == pd.Timestamp("2025-01-06")  # skips weekend

def test_pit_rejects_future_knowledge():
    """Cannot use a feature before its knowledge date."""
    raw = pd.DataFrame({
        "date": pd.to_datetime(["2025-01-02"]),
        "knowledge_date": pd.to_datetime(["2025-01-04"]),
        "var_total": [100.0],
    })
    # Trying to align with a signal date before knowledge_date should drop the row
    from src.data.point_in_time import align_to_signal_date
    result = align_to_signal_date(raw, signal_date=pd.Timestamp("2025-01-03"))
    assert len(result) == 0
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
pytest tests/data/test_point_in_time.py -v
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement point_in_time.py**

```python
# src/data/point_in_time.py
import pandas as pd
from pandas.tseries.offsets import BDay

def stamp_knowledge_time(df: pd.DataFrame, date_col: str = "date", lag_days: int = 1) -> pd.DataFrame:
    result = df.copy()
    result["knowledge_date"] = result[date_col] + BDay(lag_days)
    return result

def align_to_signal_date(df: pd.DataFrame, signal_date: pd.Timestamp) -> pd.DataFrame:
    return df[df["knowledge_date"] <= signal_date].copy()
```

- [ ] **Step 4: Run test — confirm it passes**

```bash
pytest tests/data/test_point_in_time.py -v
```
Expected: PASS

- [ ] **Step 5: Write failing test for data pipeline pull**

```python
# tests/data/test_pipeline.py
import pandas as pd
from src.data.pipeline import RiskCubePipeline

def test_pipeline_returns_pit_stamped_dataframe():
    """Pipeline output must have knowledge_date and no future data."""
    # Use a mock/fixture that returns known data
    pipeline = RiskCubePipeline(source="mock")
    df = pipeline.pull(start="2025-01-01", end="2025-03-31")
    assert "knowledge_date" in df.columns
    assert "date" in df.columns
    assert df["knowledge_date"].min() > df["date"].min()  # lag exists
    assert not df.isnull().all(axis=1).any()  # no all-null rows

def test_pipeline_respects_holdout():
    """Pipeline must refuse to return data in the holdout period."""
    pipeline = RiskCubePipeline(source="mock", holdout_start="2025-03-01")
    df = pipeline.pull(start="2025-01-01", end="2025-03-31")
    assert df["date"].max() < pd.Timestamp("2025-03-01")
```

- [ ] **Step 6: Implement pipeline.py**

```python
# src/data/pipeline.py
import pandas as pd
from src.data.point_in_time import stamp_knowledge_time

class RiskCubePipeline:
    def __init__(self, source: str = "secdb", holdout_start: str = None):
        self.source = source
        self.holdout_start = pd.Timestamp(holdout_start) if holdout_start else None

    def pull(self, start: str, end: str) -> pd.DataFrame:
        raw = self._fetch(start, end)
        stamped = stamp_knowledge_time(raw, date_col="date", lag_days=1)
        if self.holdout_start:
            stamped = stamped[stamped["date"] < self.holdout_start]
        return stamped

    def _fetch(self, start: str, end: str) -> pd.DataFrame:
        if self.source == "mock":
            return self._mock_data(start, end)
        return self._fetch_secdb(start, end)

    def _fetch_secdb(self, start: str, end: str) -> pd.DataFrame:
        # Adapt to actual SecDB/Slang API — placeholder
        raise NotImplementedError("Wire up SecDB access here")

    def _mock_data(self, start: str, end: str) -> pd.DataFrame:
        dates = pd.bdate_range(start, end)
        import numpy as np
        rng = np.random.default_rng(42)
        return pd.DataFrame({
            "date": dates,
            "var_total": rng.normal(100, 10, len(dates)),
            "var_rates": rng.normal(40, 5, len(dates)),
            "var_equities": rng.normal(35, 5, len(dates)),
            "var_fx": rng.normal(25, 3, len(dates)),
        })
```

- [ ] **Step 7: Run tests — confirm pass**

```bash
pytest tests/data/ -v
```

- [ ] **Step 8: Commit**

```bash
git add src/data/ tests/data/
git commit -m "feat: data pipeline with point-in-time stamping and holdout enforcement"
```

---

### Task 6: Label Construction Module

**Files:**
- Create: `src/labels/triple_barrier.py`
- Create: `src/labels/returns.py`
- Create: `tests/labels/test_triple_barrier.py`
- Create: `tests/labels/test_returns.py`

- [ ] **Step 1: Write failing test for standard return labels**

```python
# tests/labels/test_returns.py
import pandas as pd
import numpy as np
from src.labels.returns import forward_returns

def test_forward_returns_1d():
    prices = pd.Series([100, 102, 101, 103, 105], 
                       index=pd.bdate_range("2025-01-01", periods=5))
    ret = forward_returns(prices, horizon=1)
    assert len(ret) == 4  # last row has no forward return
    np.testing.assert_almost_equal(ret.iloc[0], 0.02)

def test_forward_returns_handles_nan():
    prices = pd.Series([100, np.nan, 101], 
                       index=pd.bdate_range("2025-01-01", periods=3))
    ret = forward_returns(prices, horizon=1)
    assert pd.isna(ret.iloc[0])
```

- [ ] **Step 2: Run test — confirm fail**

- [ ] **Step 3: Implement returns.py**

```python
# src/labels/returns.py
import pandas as pd

def forward_returns(prices: pd.Series, horizon: int = 1) -> pd.Series:
    return prices.shift(-horizon) / prices - 1
```

- [ ] **Step 4: Run test — confirm pass**

- [ ] **Step 5: Write failing test for triple-barrier labeling**

```python
# tests/labels/test_triple_barrier.py
import pandas as pd
import numpy as np
from src.labels.triple_barrier import triple_barrier_labels

def test_triple_barrier_upper_hit():
    """Price rises above upper barrier -> label = 1."""
    prices = pd.Series([100, 101, 102, 104, 103],
                       index=pd.bdate_range("2025-01-01", periods=5))
    vol = pd.Series([0.01] * 5, index=prices.index)
    labels = triple_barrier_labels(
        prices, vol, pt_sl=(2.0, 2.0), max_holding=3, min_return=0.0
    )
    assert labels.iloc[0] == 1  # hit upper barrier (2 * 0.01 * 100 = 2.0 barrier, price reached 104)

def test_triple_barrier_vertical_hit():
    """Price stays flat -> vertical barrier hit -> label based on return sign."""
    prices = pd.Series([100, 100.1, 99.9, 100.05, 100.02],
                       index=pd.bdate_range("2025-01-01", periods=5))
    vol = pd.Series([0.10] * 5, index=prices.index)  # wide barriers, won't be hit
    labels = triple_barrier_labels(
        prices, vol, pt_sl=(2.0, 2.0), max_holding=3, min_return=0.0
    )
    # After 3 days: price is 100.05, return is +0.05% -> label = 1
    assert labels.iloc[0] == 1
```

- [ ] **Step 6: Implement triple_barrier.py**

Use `mlfinlab` if available, otherwise implement from AFML Ch. 3. The implementation should:
- Accept a price series, rolling volatility, profit-taking/stop-loss multipliers, max holding period
- Return labels: +1 (upper barrier hit), -1 (lower barrier hit), 0 (vertical barrier, near-zero return)
- Volatility-scale the barriers per asset class

- [ ] **Step 7: Run tests — confirm pass**

- [ ] **Step 8: Write failing test for meta-labeling scaffold**

```python
# tests/labels/test_meta_labeling.py
import pandas as pd
import numpy as np
from src.labels.meta_labeling import meta_label

def test_meta_label_filters_low_confidence():
    """Meta-labeling: secondary model predicts size/confidence, filtering low-confidence trades."""
    primary_signals = pd.Series([1, -1, 1, -1, 1],
                                 index=pd.bdate_range("2025-01-01", periods=5))
    returns = pd.Series([0.02, -0.01, -0.03, 0.01, 0.05],
                         index=primary_signals.index)
    # Meta-label: 1 if primary was correct, 0 if not
    labels = meta_label(primary_signals, returns)
    assert labels.iloc[0] == 1   # primary said +1, return was +0.02 -> correct
    assert labels.iloc[2] == 0   # primary said +1, return was -0.03 -> incorrect
```

- [ ] **Step 9: Implement meta_labeling.py**

```python
# src/labels/meta_labeling.py
import pandas as pd
import numpy as np

def meta_label(primary_signals: pd.Series, returns: pd.Series) -> pd.Series:
    correct = (np.sign(primary_signals) == np.sign(returns)).astype(int)
    return correct
```

- [ ] **Step 10: Run all label tests — confirm pass**

```bash
pytest tests/labels/ -v
```

- [ ] **Step 11: Commit**

```bash
git add src/labels/ tests/labels/
git commit -m "feat: label construction — triple-barrier, forward returns, meta-labeling scaffold"
```

---

### Task 7: Validation Stack

**Files:**
- Create: `src/validation/purged_cv.py`
- Create: `src/validation/cpcv.py`
- Create: `src/validation/deflated_sharpe.py`
- Create: `src/validation/haircut_sharpe.py`
- Create: `src/validation/baseline.py`
- Create: `tests/validation/test_purged_cv.py`
- Create: `tests/validation/test_cpcv.py`
- Create: `tests/validation/test_deflated_sharpe.py`
- Create: `tests/validation/test_haircut_sharpe.py`
- Create: `tests/validation/test_baseline.py`

- [ ] **Step 1: Write failing test for purged K-fold CV**

```python
# tests/validation/test_purged_cv.py
import numpy as np
import pandas as pd
from src.validation.purged_cv import PurgedKFoldCV

def test_purged_cv_no_train_test_overlap():
    """Train and test sets must not overlap, including embargo period."""
    n = 100
    dates = pd.bdate_range("2025-01-01", periods=n)
    cv = PurgedKFoldCV(n_splits=5, embargo_pct=0.02)
    X = pd.DataFrame({"f1": np.random.randn(n)}, index=dates)
    y = pd.Series(np.random.randn(n), index=dates)
    
    for train_idx, test_idx in cv.split(X):
        train_dates = X.index[train_idx]
        test_dates = X.index[test_idx]
        # No overlap
        assert len(set(train_dates) & set(test_dates)) == 0
        # Embargo: no train date within 2 days after any test date
        for td in test_dates:
            embargo_end = td + pd.BDay(2)
            violating = train_dates[(train_dates > td) & (train_dates <= embargo_end)]
            assert len(violating) == 0, f"Embargo violated: train date {violating[0]} too close to test date {td}"

def test_purged_cv_all_samples_tested():
    """Every sample must appear in exactly one test fold."""
    n = 100
    dates = pd.bdate_range("2025-01-01", periods=n)
    cv = PurgedKFoldCV(n_splits=5, embargo_pct=0.02)
    X = pd.DataFrame({"f1": np.random.randn(n)}, index=dates)
    
    all_test = []
    for _, test_idx in cv.split(X):
        all_test.extend(test_idx)
    assert sorted(all_test) == list(range(n))
```

- [ ] **Step 2: Run test — confirm fail**

- [ ] **Step 3: Implement purged_cv.py**

Use `mlfinlab.cross_validation.PurgedKFold` if available. Otherwise implement from AFML Ch. 7:
- Purge: remove training observations whose labels overlap with test period
- Embargo: additional buffer after test period excluded from training
- Return sklearn-compatible (train_idx, test_idx) splits

- [ ] **Step 4: Run test — confirm pass**

- [ ] **Step 5: Write failing test for CPCV**

```python
# tests/validation/test_cpcv.py
import numpy as np
import pandas as pd
from src.validation.cpcv import CombinatorialPurgedCV

def test_cpcv_produces_sharpe_distribution():
    """CPCV should produce multiple Sharpe estimates from a single history."""
    n = 252
    dates = pd.bdate_range("2025-01-01", periods=n)
    X = pd.DataFrame({"f1": np.random.randn(n)}, index=dates)
    y = pd.Series(np.random.randn(n), index=dates)
    
    cpcv = CombinatorialPurgedCV(n_splits=6, n_test_groups=2, embargo_pct=0.02)
    sharpe_dist = cpcv.sharpe_distribution(X, y, model_factory=lambda: __import__('sklearn.linear_model', fromlist=['Ridge']).Ridge())
    assert len(sharpe_dist) > 1  # multiple paths
    assert isinstance(sharpe_dist, list)

def test_cpcv_more_splits_more_paths():
    """More splits should produce more combinatorial paths."""
    cpcv_small = CombinatorialPurgedCV(n_splits=4, n_test_groups=2)
    cpcv_large = CombinatorialPurgedCV(n_splits=6, n_test_groups=2)
    assert cpcv_large.n_paths() > cpcv_small.n_paths()
```

- [ ] **Step 6: Implement cpcv.py**

From AFML Ch. 12. Use `mlfinlab.cross_validation.CombinatorialPurgedKFold` if available. Otherwise implement:
- Generate all C(n_splits, n_test_groups) combinatorial test/train partitions
- Apply purging and embargo to each partition
- For each path, train model and compute Sharpe on the test set
- Return the distribution of Sharpes across all paths

```python
# src/validation/cpcv.py
import numpy as np
import pandas as pd
from itertools import combinations
from src.validation.purged_cv import PurgedKFoldCV
from math import comb

class CombinatorialPurgedCV:
    def __init__(self, n_splits: int = 6, n_test_groups: int = 2, embargo_pct: float = 0.02):
        self.n_splits = n_splits
        self.n_test_groups = n_test_groups
        self.embargo_pct = embargo_pct

    def n_paths(self) -> int:
        return comb(self.n_splits, self.n_test_groups)

    def sharpe_distribution(self, X, y, model_factory) -> list:
        n = len(X)
        group_size = n // self.n_splits
        sharpes = []
        for test_groups in combinations(range(self.n_splits), self.n_test_groups):
            test_mask = np.zeros(n, dtype=bool)
            for g in test_groups:
                start = g * group_size
                end = min((g + 1) * group_size, n)
                test_mask[start:end] = True
            train_idx = np.where(~test_mask)[0]
            test_idx = np.where(test_mask)[0]
            embargo = max(1, int(n * self.embargo_pct))
            for ti in test_idx:
                train_idx = train_idx[~((train_idx > ti) & (train_idx <= ti + embargo))]
            model = model_factory()
            model.fit(X.iloc[train_idx], y.iloc[train_idx])
            preds = model.predict(X.iloc[test_idx])
            pnl = pd.Series(preds) * y.iloc[test_idx].values
            sharpe = pnl.mean() / pnl.std() * np.sqrt(252) if pnl.std() > 0 else 0.0
            sharpes.append(sharpe)
        return sharpes
```

- [ ] **Step 7: Run CPCV test — confirm pass**

- [ ] **Step 8: Write failing test for Deflated Sharpe Ratio**

```python
# tests/validation/test_deflated_sharpe.py
import numpy as np
from src.validation.deflated_sharpe import deflated_sharpe_ratio

def test_dsr_penalizes_many_trials():
    """More trials should reduce the DSR for the same raw Sharpe."""
    returns = np.random.randn(252) * 0.01 + 0.0005  # slight positive drift
    raw_sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
    
    dsr_few = deflated_sharpe_ratio(raw_sharpe, num_trials=5, sample_length=252,
                                     skewness=0, kurtosis=3)
    dsr_many = deflated_sharpe_ratio(raw_sharpe, num_trials=50, sample_length=252,
                                      skewness=0, kurtosis=3)
    assert dsr_few > dsr_many  # more trials -> lower DSR

def test_dsr_zero_sharpe_gives_low_probability():
    """A Sharpe of zero should have DSR near 0 regardless of trials."""
    dsr = deflated_sharpe_ratio(0.0, num_trials=10, sample_length=252,
                                 skewness=0, kurtosis=3)
    assert dsr < 0.5
```

- [ ] **Step 6: Implement deflated_sharpe.py**

From Bailey-Lopez de Prado (2014):
```python
# src/validation/deflated_sharpe.py
import numpy as np
from scipy.stats import norm

def deflated_sharpe_ratio(observed_sharpe: float, num_trials: int, 
                           sample_length: int, skewness: float, 
                           kurtosis: float) -> float:
    e_max_sharpe = expected_max_sharpe(num_trials, sample_length)
    sharpe_std = np.sqrt(
        (1 - skewness * observed_sharpe + (kurtosis - 1) / 4 * observed_sharpe**2) 
        / sample_length
    )
    test_stat = (observed_sharpe - e_max_sharpe) / sharpe_std
    return norm.cdf(test_stat)

def expected_max_sharpe(num_trials: int, sample_length: int) -> float:
    from scipy.stats import norm as sp_norm
    emc = 0.5772156649  # Euler-Mascheroni constant
    e_max = (1 - emc) * sp_norm.ppf(1 - 1/num_trials) + emc * sp_norm.ppf(1 - 1/(num_trials * np.e))
    return e_max / np.sqrt(sample_length) * np.sqrt(252)  # annualize
```

- [ ] **Step 7: Run DSR test — confirm pass**

- [ ] **Step 8: Write failing test for Haircut Sharpe**

```python
# tests/validation/test_haircut_sharpe.py
import numpy as np
from src.validation.haircut_sharpe import haircut_sharpe

def test_haircut_reduces_sharpe():
    """Multiple-testing correction should reduce the reported Sharpe."""
    raw_sharpe = 1.5
    haircut = haircut_sharpe(raw_sharpe, num_tests=20, method="bonferroni")
    assert haircut < raw_sharpe

def test_bhy_less_conservative_than_bonferroni():
    """BHY correction should be less conservative than Bonferroni."""
    raw_sharpe = 1.5
    bonf = haircut_sharpe(raw_sharpe, num_tests=20, method="bonferroni")
    bhy = haircut_sharpe(raw_sharpe, num_tests=20, method="bhy")
    assert bhy > bonf  # BHY is less conservative

def test_single_test_no_haircut():
    """With only 1 test, Bonferroni should not reduce the Sharpe."""
    raw_sharpe = 1.5
    haircut = haircut_sharpe(raw_sharpe, num_tests=1, method="bonferroni")
    np.testing.assert_almost_equal(haircut, raw_sharpe, decimal=1)
```

- [ ] **Step 9: Implement haircut_sharpe.py**

From Harvey-Liu (2015). Apply Bonferroni/Holm/BHY-FDR multiple-testing corrections:

```python
# src/validation/haircut_sharpe.py
import numpy as np
from scipy.stats import norm

def haircut_sharpe(observed_sharpe: float, num_tests: int,
                   sample_length: int = 252, method: str = "bhy") -> float:
    p_value = 2 * (1 - norm.cdf(abs(observed_sharpe)))
    
    if method == "bonferroni":
        adjusted_p = min(p_value * num_tests, 1.0)
    elif method == "holm":
        adjusted_p = min(p_value * num_tests, 1.0)  # simplified single-test Holm
    elif method == "bhy":
        c_m = sum(1.0 / i for i in range(1, num_tests + 1))
        adjusted_p = min(p_value * num_tests * c_m / 1, 1.0)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    if adjusted_p >= 1.0:
        return 0.0
    adjusted_t = norm.ppf(1 - adjusted_p / 2)
    return adjusted_t

```

- [ ] **Step 10: Run Haircut Sharpe test — confirm pass**

- [ ] **Step 11: Write failing test for ridge baseline**

```python
# tests/validation/test_baseline.py
import numpy as np
import pandas as pd
from src.validation.baseline import ridge_baseline

def test_ridge_baseline_returns_metrics():
    """Ridge baseline should return IC, Sharpe, and predictions."""
    np.random.seed(42)
    n = 500
    X = pd.DataFrame({"f1": np.random.randn(n), "f2": np.random.randn(n)},
                      index=pd.bdate_range("2023-01-01", periods=n))
    y = pd.Series(X["f1"] * 0.5 + np.random.randn(n) * 0.1, index=X.index)
    
    result = ridge_baseline(X, y, n_splits=5)
    assert "ic_mean" in result
    assert "sharpe" in result
    assert "predictions" in result
    assert result["ic_mean"] > 0  # f1 has signal, should be captured
```

- [ ] **Step 9: Implement baseline.py**

```python
# src/validation/baseline.py
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from src.validation.purged_cv import PurgedKFoldCV

def ridge_baseline(X: pd.DataFrame, y: pd.Series, n_splits: int = 5,
                   alpha: float = 1.0) -> dict:
    cv = PurgedKFoldCV(n_splits=n_splits, embargo_pct=0.02)
    predictions = pd.Series(index=X.index, dtype=float)
    
    for train_idx, test_idx in cv.split(X):
        model = Ridge(alpha=alpha)
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        predictions.iloc[test_idx] = model.predict(X.iloc[test_idx])
    
    ic = predictions.corr(y)
    daily_pnl = predictions.shift(1) * y  # simple signal * return
    sharpe = daily_pnl.mean() / daily_pnl.std() * np.sqrt(252) if daily_pnl.std() > 0 else 0.0
    
    return {"ic_mean": ic, "sharpe": sharpe, "predictions": predictions}
```

- [ ] **Step 10: Run all validation tests — confirm pass**

```bash
pytest tests/validation/ -v
```

- [ ] **Step 11: Commit**

```bash
git add src/validation/ tests/validation/
git commit -m "feat: validation stack — purged CV, deflated sharpe, ridge baseline"
```

---

### Task 8: Backtesting Engine

**Files:**
- Create: `src/backtest/engine.py`
- Create: `src/backtest/metrics.py`
- Create: `src/backtest/reporting.py`
- Create: `tests/backtest/test_engine.py`
- Create: `tests/backtest/test_metrics.py`

- [ ] **Step 1: Write failing test for metrics module**

```python
# tests/backtest/test_metrics.py
import numpy as np
import pandas as pd
from src.backtest.metrics import compute_metrics

def test_compute_metrics_returns_all_fields():
    np.random.seed(42)
    daily_pnl = pd.Series(np.random.randn(252) * 0.01 + 0.0003,
                           index=pd.bdate_range("2025-01-01", periods=252))
    predictions = pd.Series(np.random.randn(252), index=daily_pnl.index)
    actuals = pd.Series(np.random.randn(252), index=daily_pnl.index)
    
    m = compute_metrics(daily_pnl, predictions, actuals)
    required = {"sharpe", "sortino", "ic_mean", "ic_std", "hit_rate", 
                "turnover", "max_drawdown", "total_return"}
    assert required.issubset(set(m.keys()))

def test_sharpe_positive_for_positive_drift():
    daily_pnl = pd.Series([0.001] * 252,
                           index=pd.bdate_range("2025-01-01", periods=252))
    predictions = pd.Series([1.0] * 252, index=daily_pnl.index)
    actuals = pd.Series([0.001] * 252, index=daily_pnl.index)
    m = compute_metrics(daily_pnl, predictions, actuals)
    assert m["sharpe"] > 0
```

- [ ] **Step 2: Run test — confirm fail**

- [ ] **Step 3: Implement metrics.py**

```python
# src/backtest/metrics.py
import numpy as np
import pandas as pd

def compute_metrics(daily_pnl: pd.Series, predictions: pd.Series, 
                    actuals: pd.Series, cost_bps: float = 0.0) -> dict:
    net_pnl = daily_pnl - abs(predictions.diff().fillna(0)) * cost_bps / 10000
    sharpe = net_pnl.mean() / net_pnl.std() * np.sqrt(252) if net_pnl.std() > 0 else 0.0
    downside = net_pnl[net_pnl < 0].std()
    sortino = net_pnl.mean() / downside * np.sqrt(252) if downside > 0 else 0.0
    ic = predictions.corr(actuals)
    rolling_ic = predictions.rolling(63).corr(actuals)
    cum = (1 + net_pnl).cumprod()
    drawdown = cum / cum.cummax() - 1
    turnover = predictions.diff().abs().mean()
    
    return {
        "sharpe": sharpe,
        "sortino": sortino,
        "ic_mean": ic,
        "ic_std": rolling_ic.std(),
        "hit_rate": (np.sign(predictions) == np.sign(actuals)).mean(),
        "turnover": turnover,
        "max_drawdown": drawdown.min(),
        "total_return": cum.iloc[-1] - 1,
    }
```

- [ ] **Step 4: Run test — confirm pass**

- [ ] **Step 5: Write failing test for backtest engine**

```python
# tests/backtest/test_engine.py
import numpy as np
import pandas as pd
from src.backtest.engine import Backtester

def test_backtester_produces_results():
    np.random.seed(42)
    n = 500
    dates = pd.bdate_range("2024-01-01", periods=n)
    features = pd.DataFrame({"f1": np.random.randn(n)}, index=dates)
    returns = pd.Series(features["f1"] * 0.001 + np.random.randn(n) * 0.01, index=dates)
    
    bt = Backtester(model_type="ridge", cost_bps=5.0)
    results = bt.run(features, returns, n_splits=5)
    
    assert "metrics" in results
    assert "predictions" in results
    assert results["metrics"]["sharpe"] is not None

def test_backtester_cost_reduces_sharpe():
    np.random.seed(42)
    n = 500
    dates = pd.bdate_range("2024-01-01", periods=n)
    features = pd.DataFrame({"f1": np.random.randn(n)}, index=dates)
    returns = pd.Series(features["f1"] * 0.002 + np.random.randn(n) * 0.01, index=dates)
    
    bt_free = Backtester(model_type="ridge", cost_bps=0.0)
    bt_costly = Backtester(model_type="ridge", cost_bps=20.0)
    
    r_free = bt_free.run(features, returns, n_splits=5)
    r_costly = bt_costly.run(features, returns, n_splits=5)
    
    assert r_free["metrics"]["sharpe"] > r_costly["metrics"]["sharpe"]
```

- [ ] **Step 6: Implement engine.py**

```python
# src/backtest/engine.py
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from lightgbm import LGBMRegressor
from src.validation.purged_cv import PurgedKFoldCV
from src.backtest.metrics import compute_metrics

class Backtester:
    def __init__(self, model_type: str = "ridge", cost_bps: float = 5.0, **model_kwargs):
        self.model_type = model_type
        self.cost_bps = cost_bps
        self.model_kwargs = model_kwargs

    def _make_model(self):
        if self.model_type == "ridge":
            return Ridge(alpha=self.model_kwargs.get("alpha", 1.0))
        elif self.model_type == "lgbm":
            return LGBMRegressor(
                n_estimators=self.model_kwargs.get("n_estimators", 200),
                max_depth=self.model_kwargs.get("max_depth", 4),
                learning_rate=self.model_kwargs.get("learning_rate", 0.05),
                verbose=-1,
            )
        raise ValueError(f"Unknown model type: {self.model_type}")

    def run(self, features: pd.DataFrame, returns: pd.Series, n_splits: int = 5) -> dict:
        cv = PurgedKFoldCV(n_splits=n_splits, embargo_pct=0.02)
        predictions = pd.Series(index=features.index, dtype=float)
        
        for train_idx, test_idx in cv.split(features):
            model = self._make_model()
            model.fit(features.iloc[train_idx], returns.iloc[train_idx])
            predictions.iloc[test_idx] = model.predict(features.iloc[test_idx])
        
        daily_pnl = predictions.shift(1) * returns
        metrics = compute_metrics(daily_pnl, predictions, returns, cost_bps=self.cost_bps)
        
        return {"metrics": metrics, "predictions": predictions}
```

- [ ] **Step 7: Implement reporting.py (chart generation)**

```python
# src/backtest/reporting.py
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def single_claim_chart(daily_pnl: pd.Series, title: str, 
                       ridge_pnl: pd.Series = None, save_path: str = None):
    fig, ax = plt.subplots(figsize=(10, 5))
    cum = (1 + daily_pnl).cumprod()
    ax.plot(cum.index, cum.values, label="Model", linewidth=1.5)
    if ridge_pnl is not None:
        cum_ridge = (1 + ridge_pnl).cumprod()
        ax.plot(cum_ridge.index, cum_ridge.values, label="Ridge baseline", 
                linewidth=1.5, linestyle="--", alpha=0.7)
    ax.set_title(title)
    ax.legend()
    ax.set_ylabel("Cumulative Return")
    if save_path:
        fig.savefig(save_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return fig
```

- [ ] **Step 8: Run all tests — confirm pass**

```bash
pytest tests/ -v
```

- [ ] **Step 9: Commit**

```bash
git add src/backtest/ tests/backtest/
git commit -m "feat: backtesting engine with metrics, transaction costs, and reporting"
```

---

### Task 9: Experiment Tracker Integration

**Files:**
- Create: `src/tracking/tracker.py`
- Create: `tests/tracking/test_tracker.py`

- [ ] **Step 1: Write failing test for experiment tracking**

```python
# tests/tracking/test_tracker.py
import os
import pandas as pd
from src.tracking.tracker import ExperimentTracker

def test_tracker_logs_experiment(tmp_path):
    tracker = ExperimentTracker(log_path=str(tmp_path / "experiments.csv"))
    tracker.log(
        experiment_id="exp_001",
        description="VaR utilization -> VIX innovation",
        features="var_util,var_util_roc",
        target="vix_innovation_1d",
        model="ridge",
        cv_method="purged_5fold",
        sharpe_raw=0.85,
        sharpe_dsr=0.42,
        ic_mean=0.03,
        ic_std=0.02,
    )
    df = pd.read_csv(tmp_path / "experiments.csv")
    assert len(df) == 1
    assert df.iloc[0]["experiment_id"] == "exp_001"
    assert df.iloc[0]["sharpe_dsr"] == 0.42

def test_tracker_counts_trials(tmp_path):
    tracker = ExperimentTracker(log_path=str(tmp_path / "experiments.csv"))
    for i in range(10):
        tracker.log(experiment_id=f"exp_{i:03d}", description="test",
                    features="f1", target="t1", model="ridge",
                    cv_method="purged", sharpe_raw=0.5, sharpe_dsr=0.3,
                    ic_mean=0.01, ic_std=0.01)
    assert tracker.total_trials() == 10
```

- [ ] **Step 2: Run test — confirm fail**

- [ ] **Step 3: Implement tracker.py**

```python
# src/tracking/tracker.py
import os
import pandas as pd
from datetime import datetime

class ExperimentTracker:
    def __init__(self, log_path: str = "experiments/experiment_log.csv"):
        self.log_path = log_path
        if not os.path.exists(log_path):
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            pd.DataFrame(columns=[
                "experiment_id", "date", "description", "features", "target",
                "model", "cv_method", "sharpe_raw", "sharpe_dsr", "ic_mean", "ic_std", "notes"
            ]).to_csv(log_path, index=False)

    def log(self, experiment_id: str, description: str, features: str,
            target: str, model: str, cv_method: str, sharpe_raw: float,
            sharpe_dsr: float, ic_mean: float, ic_std: float, notes: str = "") -> None:
        row = pd.DataFrame([{
            "experiment_id": experiment_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "description": description,
            "features": features,
            "target": target,
            "model": model,
            "cv_method": cv_method,
            "sharpe_raw": sharpe_raw,
            "sharpe_dsr": sharpe_dsr,
            "ic_mean": ic_mean,
            "ic_std": ic_std,
            "notes": notes,
        }])
        row.to_csv(self.log_path, mode="a", header=False, index=False)

    def total_trials(self) -> int:
        return len(pd.read_csv(self.log_path))
```

- [ ] **Step 4: Run test — confirm pass**

- [ ] **Step 5: Commit**

```bash
git add src/tracking/ tests/tracking/
git commit -m "feat: experiment tracker for honest DSR trial counting"
```

---

### Task 10: Infrastructure Smoke Test

**Files:**
- Create: `notebooks/01_smoke_test.ipynb`

- [ ] **Step 1: Build smoke test notebook**

Run the full validation stack on a known-good signal using mock or public data:
1. Generate synthetic data where `f1` has known predictive power for `y`
2. Run `Backtester` with model_type="ridge" and model_type="lgbm"
3. Verify: LightGBM Sharpe >= Ridge Sharpe (known nonlinear signal should give ML uplift)
4. Compute DSR — should remain positive with few trials
5. Generate a `single_claim_chart` with both model curves
6. Log both experiments to the tracker

```python
# Key assertions in the smoke test:
assert results_lgbm["metrics"]["sharpe"] > 0, "Smoke test: LightGBM should find signal in synthetic data"
assert results_ridge["metrics"]["sharpe"] > 0, "Smoke test: Ridge should find signal in synthetic data"
assert tracker.total_trials() == 2, "Smoke test: should have logged 2 experiments"
print("SMOKE TEST PASSED — infrastructure is working")
```

- [ ] **Step 2: Run the notebook end-to-end and verify output**

- [ ] **Step 3: Commit**

```bash
git add notebooks/01_smoke_test.ipynb
git commit -m "feat: smoke test validates full infrastructure stack on synthetic data"
```

---

## Chunk 3: Phase 2 — Project 1 Core (Weeks 6-12)

### Task 11: Feature Engineering — Priority Features

**Files:**
- Create: `src/features/var_utilization.py`
- Create: `src/features/factor_concentration.py`
- Create: `tests/features/test_var_utilization.py`
- Create: `tests/features/test_factor_concentration.py`

- [ ] **Step 1: Write failing test for VaR utilization features**

```python
# tests/features/test_var_utilization.py
import pandas as pd
import numpy as np
from src.features.var_utilization import compute_var_utilization_features

def test_var_utilization_features():
    dates = pd.bdate_range("2025-01-01", periods=60)
    raw = pd.DataFrame({
        "date": dates,
        "var_usage": np.random.uniform(50, 95, 60),
        "var_limit": [100.0] * 60,
    })
    features = compute_var_utilization_features(raw)
    assert "var_util_pct" in features.columns  # usage / limit
    assert "var_util_roc" in features.columns  # rate of change
    assert "var_util_zscore" in features.columns  # z-score over rolling window
    assert features["var_util_pct"].max() <= 1.0
    assert not features.isnull().all(axis=1).any()
```

- [ ] **Step 2: Run test — confirm fail**

- [ ] **Step 3: Implement var_utilization.py**

```python
# src/features/var_utilization.py
import pandas as pd
import numpy as np

def compute_var_utilization_features(df: pd.DataFrame, window: int = 21) -> pd.DataFrame:
    result = df.copy()
    result["var_util_pct"] = df["var_usage"] / df["var_limit"]
    result["var_util_roc"] = result["var_util_pct"].pct_change()
    rolling_mean = result["var_util_pct"].rolling(window).mean()
    rolling_std = result["var_util_pct"].rolling(window).std()
    result["var_util_zscore"] = (result["var_util_pct"] - rolling_mean) / rolling_std
    return result.dropna()
```

- [ ] **Step 4: Run test — confirm pass**

- [ ] **Step 5: Write failing test for factor concentration features**

```python
# tests/features/test_factor_concentration.py
import pandas as pd
import numpy as np
from src.features.factor_concentration import compute_concentration_features

def test_herfindahl_index():
    dates = pd.bdate_range("2025-01-01", periods=10)
    # 4 factors, one dominates
    raw = pd.DataFrame({
        "date": dates,
        "factor_var_1": [80.0] * 10,
        "factor_var_2": [10.0] * 10,
        "factor_var_3": [5.0] * 10,
        "factor_var_4": [5.0] * 10,
    })
    features = compute_concentration_features(raw, factor_cols=["factor_var_1", "factor_var_2", "factor_var_3", "factor_var_4"])
    assert "herfindahl" in features.columns
    assert "top3_share" in features.columns
    # Concentrated portfolio: Herfindahl should be high
    assert features["herfindahl"].iloc[0] > 0.5

def test_equal_weight_low_concentration():
    dates = pd.bdate_range("2025-01-01", periods=10)
    raw = pd.DataFrame({
        "date": dates,
        "f1": [25.0] * 10, "f2": [25.0] * 10,
        "f3": [25.0] * 10, "f4": [25.0] * 10,
    })
    features = compute_concentration_features(raw, factor_cols=["f1", "f2", "f3", "f4"])
    assert features["herfindahl"].iloc[0] == 0.25  # 4 equal weights -> HHI = 0.25
```

- [ ] **Step 6: Implement factor_concentration.py**

```python
# src/features/factor_concentration.py
import pandas as pd
import numpy as np

def compute_concentration_features(df: pd.DataFrame, factor_cols: list) -> pd.DataFrame:
    result = df.copy()
    factor_vals = df[factor_cols].abs()
    total = factor_vals.sum(axis=1)
    shares = factor_vals.div(total, axis=0)
    result["herfindahl"] = (shares ** 2).sum(axis=1)
    result["top3_share"] = shares.apply(lambda row: row.nlargest(3).sum(), axis=1)
    result["max_factor_share"] = shares.max(axis=1)
    return result
```

- [ ] **Step 7: Run tests — confirm pass**

- [ ] **Step 8: Commit**

```bash
git add src/features/ tests/features/
git commit -m "feat: priority feature families — VaR utilization and factor concentration"
```

---

### Task 12: Feature Engineering — Remaining Families

**Files:**
- Create: `src/features/var_dynamics.py`
- Create: `src/features/scenario_pnl.py`
- Create: `src/features/cross_asset_flow.py`
- Create: `tests/features/test_var_dynamics.py`
- Create: `tests/features/test_scenario_pnl.py`
- Create: `tests/features/test_cross_asset_flow.py`

- [ ] **Step 1: Implement and test VaR dynamics features**

Features: firm-level delta VaR, component VaR by asset class, VaR rate-of-change, VaR momentum (5d, 21d changes).

- [ ] **Step 2: Implement and test scenario P&L features**

Features: stress-scenario P&L rank, dispersion across scenarios (std of P&Ls), worst-case scenario identity (categorical → one-hot or label-encoded), scenario P&L skewness.

- [ ] **Step 3: Implement and test cross-asset flow features**

Features: component VaR share shifts between asset classes (rates_share_5d_change, equities_share_5d_change), cross-asset VaR correlation (rolling 21d correlation of component VaR changes between asset classes).

- [ ] **Step 4: Run all feature tests**

```bash
pytest tests/features/ -v
```

- [ ] **Step 5: Commit**

```bash
git add src/features/ tests/features/
git commit -m "feat: remaining feature families — VaR dynamics, scenario P&L, cross-asset flow"
```

---

### Task 13: Target Construction

**Files:**
- Create: `src/targets/targets.py`
- Create: `tests/targets/test_targets.py`

- [ ] **Step 1: Write failing tests for each prediction target**

```python
# tests/targets/test_targets.py
import pandas as pd
import numpy as np
from src.targets.targets import (
    vix_innovation, 
    asset_class_drawdown, 
    realized_vol,
    momentum_reversal,
)

def test_vix_innovation():
    vix = pd.Series([20, 21, 19, 22, 18], index=pd.bdate_range("2025-01-01", periods=5))
    innov = vix_innovation(vix, horizon=1)
    assert len(innov) == 4
    np.testing.assert_almost_equal(innov.iloc[0], 1.0)  # 21 - 20

def test_realized_vol():
    prices = pd.Series(np.exp(np.cumsum(np.random.randn(63) * 0.01)),
                       index=pd.bdate_range("2025-01-01", periods=63))
    rv = realized_vol(prices, window=21)
    assert len(rv.dropna()) == 63 - 21 + 1
    assert (rv.dropna() > 0).all()
```

- [ ] **Step 2: Implement targets.py**

- [ ] **Step 3: Run tests — confirm pass**

- [ ] **Step 4: Commit**

```bash
git add src/targets/ tests/targets/
git commit -m "feat: prediction targets — VIX innovation, drawdown, realized vol, momentum reversal"
```

---

### Task 14: Signal Testing — Priority Features × Targets

**Files:**
- Create: `notebooks/02_var_utilization_signal.ipynb`
- Create: `notebooks/03_factor_concentration_signal.ipynb`

- [ ] **Step 1: VaR utilization signal test notebook**

For each target (VIX innovation, realized vol, asset-class drawdown):
1. Pull VaR utilization features
2. Run ridge baseline via `Backtester`
3. Run LightGBM via `Backtester`
4. Compute DSR for both
5. SHAP analysis on LightGBM
6. Generate single-claim charts (model vs. ridge)
7. Log all experiments to tracker

Key question: does VaR utilization spike predict next-period VIX innovation or realized vol? Theory (Coval-Stafford) says high utilization → forced selling → drawdowns.

- [ ] **Step 2: Factor concentration signal test notebook**

Same structure as Step 1 but with factor concentration features. Key question: does Herfindahl spike predict drawdowns in the most-concentrated asset class?

- [ ] **Step 3: Document initial findings**

Create a 1-page summary: which signal family × target combinations show IC > 0 after purged CV? Which survive DSR? Any surprises?

- [ ] **Step 4: Commit**

```bash
git add notebooks/
git commit -m "feat: priority signal tests — VaR utilization and factor concentration"
```

---

### Task 15: Signal Testing — Remaining Features & Combined Model

**Files:**
- Create: `notebooks/04_remaining_signals.ipynb`
- Create: `notebooks/05_combined_model.ipynb`

- [ ] **Step 1: Test remaining signal families individually**

VaR dynamics, scenario P&L, cross-asset flow — each tested against the surviving target(s) from Task 14.

- [ ] **Step 2: Confound checks**

For any signal family that shows IC > 0, test whether it's just correlated with known public factors:
```python
# Add VIX level, credit spread, term slope as controls
features_with_controls = pd.concat([signal_features, public_factors], axis=1)
result_with_controls = backtester.run(features_with_controls, target)
result_without_controls = backtester.run(signal_features, target)
# If IC drops to zero with controls, signal is redundant
```

- [ ] **Step 3: Build combined model**

Combine all surviving signal families into a single feature set:
1. Ridge baseline on combined features
2. LightGBM on combined features
3. SHAP to identify which families contribute most
4. MDA across CV folds — check stability

- [ ] **Step 4: Panel structure test**

Run the combined model as a panel (multiple asset classes × time) with asset-class fixed effects. Does pooling improve sample size and signal quality?

- [ ] **Step 5: Log all experiments, document findings**

- [ ] **Step 6: Commit**

```bash
git add notebooks/
git commit -m "feat: remaining signal tests, confound checks, combined model"
```

---

## Chunk 4: Phase 3 — Checkpoint (Week 13)

### Task 16: Checkpoint Assessment

**Files:**
- Create: `deliverables/checkpoint_memo.md`

- [ ] **Step 1: Compile results summary**

Review experiment log. For each signal family × target combination:
- IC mean and std across CV folds
- Ridge Sharpe vs. LightGBM Sharpe (does ML add anything?)
- DSR-adjusted Sharpe
- MDA stability (does feature importance flip across folds?)

- [ ] **Step 2: Apply decision criteria**

**Continue Project 1 if:** at least one signal family has IC > 0 after purged CV, GBM beats ridge, DSR > 0.5, MDA stable.

**Pivot to Project 2 if:** all flat/unstable, GBM ≤ ridge, DSR kills Sharpe.

**Hybrid if:** partial success — keep working features, add Greeks.

- [ ] **Step 3: Write checkpoint memo**

1-2 pages: what was tested, what worked, what didn't, decision and rationale. Include key charts. This becomes an appendix in the final report.

- [ ] **Step 4: Present to sponsor**

Use the scheduled Week 13 meeting. Get sign-off on the chosen path (4A, 4B, or hybrid).

- [ ] **Step 5: Commit**

```bash
git add deliverables/checkpoint_memo.md
git commit -m "docs: week 13 checkpoint memo — go/pivot decision"
```

---

## Chunk 5: Phase 4A — Deepen Project 1 (Weeks 14-17)

*Only if checkpoint passes. If pivot, skip to Chunk 6.*

### Task 17: Regime Overlay

**Files:**
- Create: `src/regime/gmm_regime.py`
- Create: `tests/regime/test_gmm_regime.py`
- Create: `notebooks/06_regime_analysis.ipynb`

- [ ] **Step 1: Write failing test for GMM regime classification**

```python
# tests/regime/test_gmm_regime.py
import numpy as np
import pandas as pd
from src.regime.gmm_regime import fit_regime_model, classify_regimes

def test_gmm_finds_distinct_regimes():
    np.random.seed(42)
    n = 500
    # Generate data from 2 clearly separated regimes
    regime_1 = np.random.multivariate_normal([0, 0], [[1, 0], [0, 1]], n // 2)
    regime_2 = np.random.multivariate_normal([5, 5], [[1, 0], [0, 1]], n // 2)
    data = pd.DataFrame(
        np.vstack([regime_1, regime_2]), columns=["vix", "credit_spread"]
    )
    model = fit_regime_model(data, n_regimes=2)
    labels = classify_regimes(model, data)
    assert labels.nunique() == 2
    assert len(labels) == n

def test_regime_labels_are_interpretable():
    """Regime with higher VIX should be labeled 'Crisis'."""
    np.random.seed(42)
    crisis = pd.DataFrame({"vix": [30, 35, 40], "credit_spread": [5, 6, 7]})
    calm = pd.DataFrame({"vix": [12, 13, 14], "credit_spread": [1, 1.5, 2]})
    data = pd.concat([calm, crisis]).reset_index(drop=True)
    model = fit_regime_model(data, n_regimes=2)
    labels = classify_regimes(model, data)
    # The regime assigned to high-VIX rows should differ from low-VIX rows
    assert labels.iloc[0] != labels.iloc[3]
```

- [ ] **Step 2: Run test — confirm fail**

- [ ] **Step 3: Implement gmm_regime.py**

```python
# src/regime/gmm_regime.py
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

def fit_regime_model(features: pd.DataFrame, n_regimes: int = 3) -> dict:
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features)
    gmm = GaussianMixture(n_components=n_regimes, covariance_type="full", 
                           n_init=10, random_state=42)
    gmm.fit(X_scaled)
    return {"model": gmm, "scaler": scaler, "feature_names": list(features.columns)}

def classify_regimes(model_dict: dict, features: pd.DataFrame) -> pd.Series:
    X_scaled = model_dict["scaler"].transform(features)
    labels = model_dict["model"].predict(X_scaled)
    return pd.Series(labels, index=features.index, name="regime")
```

- [ ] **Step 4: Run test — confirm pass**

- [ ] **Step 5: Regime decomposition notebook**

In `notebooks/06_regime_analysis.ipynb`:
1. Fit GMM on macro features (VIX, credit spread, term slope, USD, realized correlation)
2. Label regimes by their macro characteristics (Crisis, Steady State, etc.)
3. Decompose the Project 1 signal's performance by regime
4. Generate per-regime charts: cumulative P&L, IC, Sharpe by regime
5. Key finding: is the signal regime-conditional or works broadly?

- [ ] **Step 6: Commit**

```bash
git add src/regime/ tests/regime/ notebooks/06_regime_analysis.ipynb
git commit -m "feat: GMM regime overlay — classify and decompose signal by macro regime"
```

---

### Task 18: Cross-Asset Panel Extension

**Files:**
- Create: `notebooks/07_cross_asset_panel.ipynb`

- [ ] **Step 1: Restructure features as panel data**

Move from firm-level aggregates to asset-class-level:
- Component VaR for each asset class (rates, equities, FX, credit, commodities)
- Asset-class-specific returns as targets
- Panel: (date × asset_class) observations with asset-class fixed effects

- [ ] **Step 2: Within-class vs. cross-prediction tests**

Test:
- Does rates component VaR predict rates returns? (within-class)
- Does rates component VaR predict equity drawdowns? (cross-class)
- Is there a single pricing kernel across asset classes? (He-Kelly-Manela test)

```python
# Within-class test
for asset_class in ["rates", "equities", "fx", "credit"]:
    X = features_by_asset[asset_class]
    y = returns_by_asset[asset_class]
    result = backtester.run(X, y, n_splits=5)
    tracker.log(experiment_id=f"within_{asset_class}", ...)

# Cross-prediction test
for source in ["rates", "equities"]:
    for target in ["rates", "equities", "fx", "credit"]:
        if source == target: continue
        X = features_by_asset[source]
        y = returns_by_asset[target]
        result = backtester.run(X, y, n_splits=5)
        tracker.log(experiment_id=f"cross_{source}_to_{target}", ...)
```

- [ ] **Step 3: Panel regression with clustered standard errors**

```python
import statsmodels.api as sm
# Fixed effects panel regression
# y_{i,t} = alpha_i + beta * X_{i,t} + epsilon_{i,t}
# Clustered standard errors by time to handle cross-sectional correlation
```

- [ ] **Step 4: Document findings**

- [ ] **Step 5: Commit**

```bash
git add notebooks/07_cross_asset_panel.ipynb
git commit -m "feat: cross-asset panel tests — within-class vs. cross-prediction"
```

---

### Task 19: Capacity & Transaction Cost Analysis

**Files:**
- Create: `notebooks/08_capacity_analysis.ipynb`

- [ ] **Step 1: Transaction cost sensitivity**

Re-run the best model at varying cost levels:
```python
for cost in [0, 2, 5, 10, 20, 50]:
    bt = Backtester(model_type="lgbm", cost_bps=cost)
    result = bt.run(best_features, best_target, n_splits=5)
    print(f"Cost={cost}bps: Sharpe={result['metrics']['sharpe']:.2f}")
```

Find the breakeven cost level where Sharpe → 0.

- [ ] **Step 2: Turnover analysis**

Compute daily turnover of the signal. If turnover is high (> 50% daily), the signal may be impractical despite good gross Sharpe.

- [ ] **Step 3: Capacity estimation**

Estimate how much capital the signal can absorb before market impact degrades returns. This is necessarily rough — use order-of-magnitude reasoning based on typical bid-ask spreads and daily volumes in the traded instruments.

- [ ] **Step 4: Document for presentation**

Create charts: Sharpe vs. transaction cost curve, cumulative P&L at different cost assumptions.

- [ ] **Step 5: Commit**

```bash
git add notebooks/08_capacity_analysis.ipynb
git commit -m "feat: capacity and transaction cost analysis"
```

---

### Task 19B: Initiate Compliance Review (Week 16-17)

- [ ] **Step 1: Identify compliance constraints**

Determine which outputs require compliance review:
- Internal-only presentation to desk: typically lighter review
- Broader internal distribution (e.g., cross-desk, senior leadership): may require more scrutiny
- Any external-facing output: full compliance review required

- [ ] **Step 2: Submit draft report for compliance review**

Share an early draft of the research report (even if incomplete) with the appropriate compliance/legal team. Start this process no later than Week 17 to ensure it completes before the Week 20 presentation.

- [ ] **Step 3: Document any compliance constraints on final output**

Record restrictions on: data shown, specificity of results, distribution scope. Adjust the final report and presentation accordingly.

---

## Chunk 6: Phase 4B — Book-Gamma Pivot (Weeks 14-17)

*Only if checkpoint fails. Skip if taking Phase 4A.*

### Task 20: Greeks Feature Engineering

**Files:**
- Create: `src/features/dealer_greeks.py`
- Create: `tests/features/test_dealer_greeks.py`

- [ ] **Step 1: Write failing tests for dealer Greeks aggregation**

```python
# tests/features/test_dealer_greeks.py
import pandas as pd
import numpy as np
from src.features.dealer_greeks import aggregate_dealer_greeks

def test_aggregate_greeks_produces_net_gamma():
    trades = pd.DataFrame({
        "date": pd.to_datetime(["2025-01-02"] * 4),
        "instrument": ["ES", "ES", "TY", "TY"],
        "gamma": [100, -150, 200, -80],
        "vega": [50, -30, 80, -40],
        "vanna": [10, -5, 15, -8],
    })
    agg = aggregate_dealer_greeks(trades, group_by=["date", "instrument"])
    assert "net_gamma" in agg.columns
    es = agg[agg["instrument"] == "ES"]
    assert es["net_gamma"].iloc[0] == -50  # 100 + (-150)
```

- [ ] **Step 2: Implement dealer_greeks.py**

Aggregate book-level Greeks from SecDB into daily net dealer gamma, vega, vanna, charm per instrument class. Compute gamma-flip level (where net gamma crosses zero) and distance-to-flip.

- [ ] **Step 3: Run tests — confirm pass**

- [ ] **Step 4: Commit**

```bash
git add src/features/dealer_greeks.py tests/features/test_dealer_greeks.py
git commit -m "feat: dealer Greeks aggregation from SecDB book data"
```

---

### Task 21: Book-Gamma Signal Testing

**Files:**
- Create: `notebooks/09_book_gamma_signal.ipynb`

- [ ] **Step 1: Replicate Baltussen et al. (2021) with real data**

Test: does aggregate net gamma sign predict last-30-minute intraday momentum across rates futures, G10 FX, credit indices?

- [ ] **Step 2: Cross-instrument linkage**

Does the gamma signal in rates predict anything in FX (dealer balance-sheet linkage)?

- [ ] **Step 3: Muravyev-Pearson-Pollet controls**

If touching equities, add short interest and borrow cost as controls.

- [ ] **Step 4: Run validation stack**

Purged CV, DSR, ridge baseline, SHAP — same discipline as Project 1.

- [ ] **Step 5: Compare to published result**

Does real book data improve on the Baltussen et al. result, or just confirm it?

- [ ] **Step 6: Document and commit**

```bash
git add notebooks/09_book_gamma_signal.ipynb
git commit -m "feat: book-gamma intraday momentum signal with SecDB Greeks"
```

---

## Chunk 7: Phase 5 — Consolidation & Presentation (Weeks 18-20)

### Task 22: Walk-Forward Out-of-Sample Test

**Files:**
- Create: `notebooks/10_oos_walkforward.ipynb`

- [ ] **Step 1: Unfreeze the holdout period**

Load the reserved holdout data (3-6 months). This is the first and only time this data is used.

- [ ] **Step 2: Walk-forward test**

Retrain the best model on all pre-holdout data, predict into holdout, compute metrics. Do NOT iterate on this — one shot only. If it fails OOS, that is the result.

```python
# Train on all data before holdout
model.fit(X_train_all, y_train_all)
predictions_oos = model.predict(X_holdout)
metrics_oos = compute_metrics(predictions_oos * y_holdout, predictions_oos, y_holdout)
print(f"OOS Sharpe: {metrics_oos['sharpe']:.2f}")
print(f"OOS IC: {metrics_oos['ic_mean']:.3f}")
```

- [ ] **Step 3: Rolling-window stability check**

Retrain on 6-month rolling windows, check that feature importance doesn't rotate drastically across windows.

- [ ] **Step 4: Final DSR and Haircut Sharpe**

Apply DSR with the total trial count from the experiment log. Apply Harvey-Liu haircut. These are the final reported numbers.

- [ ] **Step 5: Commit**

```bash
git add notebooks/10_oos_walkforward.ipynb
git commit -m "feat: walk-forward OOS test on held-out data"
```

---

### Task 23: Final Research Report

**Files:**
- Create: `deliverables/research_report.md`

- [ ] **Step 1: Write the report**

Sections:
1. **Hypothesis** — one paragraph
2. **Data** — what was pulled, time range, point-in-time discipline, known methodology breaks
3. **Methodology** — validation framework (purged CV, DSR, CPCV, ridge baseline)
4. **Results** — IC, Sharpe, Sortino, hit rate, turnover, max drawdown, P&L by regime. One chart per claim. Ridge alongside GBM on every chart.
5. **What didn't work** — documented negative results from experiment log
6. **Capacity and transaction-cost sensitivity** — breakeven cost, turnover, capacity estimate
7. **Next steps** — what a full-time quant could do with more time

- [ ] **Step 2: Generate all charts**

Use `src/backtest/reporting.py` to produce publication-quality charts:
- Cumulative P&L (model vs. ridge) per signal family
- SHAP waterfall for top 3 predictions
- IC time series
- P&L by regime
- Sharpe vs. transaction cost curve

- [ ] **Step 3: Internal review**

Share with sponsor for feedback before presentation. Start compliance review if needed (should have begun in Week 16).

- [ ] **Step 4: Commit**

```bash
git add deliverables/research_report.md deliverables/charts/
git commit -m "docs: final research report with all charts"
```

---

### Task 24: Presentation

**Files:**
- Create: `deliverables/presentation_outline.md`

- [ ] **Step 1: Build slide outline**

One slide per claim:
1. Title + thesis (1 slide)
2. "What theory predicts" (1 slide — He-Krishnamurthy, Adrian-Etula-Muir)
3. "What we tested" (1 slide — data, features, methodology)
4. Results per surviving signal family (1 slide each)
5. Ridge vs. GBM comparison (1 slide)
6. Regime decomposition (1 slide)
7. Cross-asset panel results (1 slide)
8. Capacity and cost (1 slide)
9. What didn't work (1 slide)
10. Next steps (1 slide)

- [ ] **Step 2: Prepare for anticipated questions**

Document answers to:
- "What's the capacity?"
- "What's the turnover?"
- "Does this survive transaction costs?"
- "What happens in a crisis?"
- "Why not just a linear model?"
- "How is this different from [public factor X]?"

- [ ] **Step 3: Dry run with sponsor**

Present before the full desk. Iterate based on feedback.

- [ ] **Step 4: Commit**

```bash
git add deliverables/presentation_outline.md
git commit -m "docs: presentation outline and Q&A preparation"
```

---

## Project Directory Structure

```
ML/
├── CLAUDE.md
├── Signal Discovery.pdf
├── data/
│   ├── access_audit.md
│   └── holdout_config.json
├── deliverables/
│   ├── pitch.md
│   ├── checkpoint_memo.md
│   ├── research_report.md
│   ├── presentation_outline.md
│   └── charts/
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-04-23-risk-as-alpha-design.md
│       └── plans/
│           └── 2026-04-23-risk-as-alpha-plan.md
├── environment/
│   ├── package_audit.md
│   └── requirements.txt
├── experiments/
│   └── experiment_log.csv
├── notebooks/
│   ├── 00_data_exploration.ipynb
│   ├── 01_smoke_test.ipynb
│   ├── 02_var_utilization_signal.ipynb
│   ├── 03_factor_concentration_signal.ipynb
│   ├── 04_remaining_signals.ipynb
│   ├── 05_combined_model.ipynb
│   ├── 06_regime_analysis.ipynb
│   ├── 07_cross_asset_panel.ipynb
│   ├── 08_capacity_analysis.ipynb
│   ├── 09_book_gamma_signal.ipynb (if pivot)
│   └── 10_oos_walkforward.ipynb
├── src/
│   ├── __init__.py
│   ├── backtest/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── metrics.py
│   │   └── reporting.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   └── point_in_time.py
│   ├── features/
│   │   ├── __init__.py
│   │   ├── var_utilization.py
│   │   ├── factor_concentration.py
│   │   ├── var_dynamics.py
│   │   ├── scenario_pnl.py
│   │   ├── cross_asset_flow.py
│   │   └── dealer_greeks.py (if pivot)
│   ├── labels/
│   │   ├── __init__.py
│   │   ├── triple_barrier.py
│   │   ├── meta_labeling.py
│   │   └── returns.py
│   ├── regime/
│   │   ├── __init__.py
│   │   └── gmm_regime.py
│   ├── targets/
│   │   ├── __init__.py
│   │   └── targets.py
│   ├── tracking/
│   │   ├── __init__.py
│   │   └── tracker.py
│   └── validation/
│       ├── __init__.py
│       ├── purged_cv.py
│       ├── cpcv.py
│       ├── deflated_sharpe.py
│       ├── haircut_sharpe.py
│       └── baseline.py
└── tests/
    ├── backtest/
    │   ├── test_engine.py
    │   └── test_metrics.py
    ├── data/
    │   ├── test_pipeline.py
    │   └── test_point_in_time.py
    ├── features/
    │   ├── test_var_utilization.py
    │   ├── test_factor_concentration.py
    │   ├── test_var_dynamics.py
    │   ├── test_scenario_pnl.py
    │   ├── test_cross_asset_flow.py
    │   └── test_dealer_greeks.py (if pivot)
    ├── labels/
    │   ├── test_triple_barrier.py
    │   ├── test_meta_labeling.py
    │   └── test_returns.py
    ├── regime/
    │   └── test_gmm_regime.py
    ├── targets/
    │   └── test_targets.py
    ├── tracking/
    │   └── test_tracker.py
    └── validation/
        ├── test_purged_cv.py
        ├── test_cpcv.py
        ├── test_deflated_sharpe.py
        ├── test_haircut_sharpe.py
        └── test_baseline.py
```
