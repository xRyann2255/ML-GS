# Copilot Implementation Prompts -- ML Vol Estimator

11 self-contained prompts for GitHub Copilot on `H:\ml-vol-estimator`.
Max 2 prompts per phase. Each prompt starts with the `/command` line.
Copy everything from the `/command` line through the end into Copilot Chat.

## Handoff System

Prompts that feed into later prompts generate a handoff file at the end.
The next prompt reads that handoff for context continuity across sessions.

Handoff path convention: `workspace/tmp/handoff-{id}.md`

## Quick Reference

| #  | Phase | Title | Command | Reads Handoff | Writes Handoff |
|----|-------|-------|---------|---------------|----------------|
| 1  | P0 | Asymmetry math fixes (semivar + RTQ) | `/fix` | -- | handoff-p0a.md |
| 2  | P0 | Evaluation fixes (QLIKE + purge gap) | `/fix` | -- | handoff-p0b.md |
| 3  | P1 | Feature utilities (safe_log + dedup) | `/refactor` | handoff-p0a.md | handoff-p1a.md |
| 4  | P1 | Infrastructure (protocol + DEV_UNIVERSE) | `/refactor` | -- | handoff-p1b.md |
| 5  | P2 | Layer 2: Options-implied features | `/feature` | handoff-p1a.md, p1b.md | handoff-p2a.md |
| 6  | P2 | Layers 4+5: Cross-asset + Calendar | `/feature` | handoff-p1a.md, p1b.md | -- |
| 7  | P3 | LightGBM with QLIKE objective | `/execute` | handoff-p0b.md, p1a.md | handoff-p3a.md |
| 8  | P3 | Optuna hyperparameter tuning | `/execute` | handoff-p3a.md | -- |
| 9  | P4 | Statistical tests: DM + MZ | `/execute` | -- | handoff-p4a.md |
| 10 | P4 | MCS + tournament table | `/execute` | handoff-p4a.md | handoff-p4b.md |
| 11 | P5 | Full HAR baseline tournament | `/evaluate` | handoff-p0b.md, p4b.md | -- |

## Dependency Graph

```
Phase 0                     Phase 1                    Phase 2
 1 (asymmetry) ──h:p0a──► 3 (safe_log+dedup) ──h:p1a──► 5 (Layer 2)
                                                    ├──► 6 (Layer 4+5)
 2 (QLIKE+purge) ──h:p0b──────────────────────────────► 7 (LightGBM)
                   │        4 (protocol+dev) ──h:p1b──► 5, 6
                   │
                   │       Phase 3                   Phase 4
                   ├─────► 7 (LightGBM) ──h:p3a──► 8 (Optuna)
                   │
                   │                                 9 (DM+MZ) ──h:p4a──► 10 (MCS+table)
                   │                                                          │ h:p4b
                   │       Phase 5                                            │
                   └─────► 11 (Tournament) ◄──────────────────────────────────┘
```

---
---

## Phase 0: Correctness Bugs

---

### Prompt 1: Asymmetry Math Fixes (Semivariance + BNS RTQ)

```
/fix Fix two math correctness bugs in features/asymmetry.py and data/resample.py

## Context

Read these files first:
- src/volforecast/features/asymmetry.py (compute_semivariances, detect_jumps, compute_realized_tripower_quarticity)
- src/volforecast/data/resample.py (compute_daily_rv_from_ticks)
- src/volforecast/data/measures.py (re-export facade)
- tests/test_features.py
- tests/test_data_pipeline.py

## Bug 1: Semivariance indicator uses strict inequality

In compute_semivariances(), RS+ uses 1(r > 0) and RS- uses 1(r < 0). Zero returns are
excluded from both, violating the decomposition identity RS+ + RS- = RV.

Patton & Sheppard (2015) define RS+ with 1(r >= 0) and RS- with 1(r < 0).

Fix: change the RS+ indicator from `r > 0` to `r >= 0`. Keep RS- as `r < 0`.

## Bug 2: BNS jump test uses RQ instead of RTQ in denominator

detect_jumps(rv, bpv, rq, n_obs, alpha) uses RQ:
  Z = (RV - BPV) / sqrt(theta * RQ / N)

BNS (2006) Theorem 2 requires Realized Tripower Quarticity (RTQ), not RQ.
RTQ is jump-robust; RQ is not. Using RQ inflates the denominator when jumps
are present, reducing test power (conservative bias).

compute_realized_tripower_quarticity() already exists in asymmetry.py but is never
called in the daily pipeline.

### Fix for Bug 2 (3 files):

**asymmetry.py:** Change detect_jumps signature from `rq` to `rtq` parameter.
Update the formula to use rtq. Update docstring to reference BNS (2006) Theorem 2.
Also update build_asymmetry_features if it calls detect_jumps.

**resample.py:** In compute_daily_rv_from_ticks():
- Import compute_realized_tripower_quarticity via the measures facade
- Add: rtq = compute_realized_tripower_quarticity(returns)
- Change detect_jumps call to pass rtq instead of rq
- Add 'rtq' to the returned dict (keep 'rq' -- it's still needed for HARQ features)

**measures.py:** Add compute_realized_tripower_quarticity to the re-exports.

### Schema change note

This adds an 'rtq' column to daily parquet output (19 measures instead of 18).
Cached parquet files will need re-ingestion. The code should handle missing 'rtq'
gracefully (it's only needed by detect_jumps at compute time, not at feature time).

## Tests

In tests/test_features.py:
1. test_semivariance_decomposition: returns with exact zeros, assert RS+ + RS- == RV (1e-15 tol)
2. test_semivariance_zeros_go_to_positive: zero returns contribute to RS+ not RS-
3. test_rtq_positive: compute_realized_tripower_quarticity returns positive float
4. test_rtq_smaller_than_rq_with_jumps: on data with jumps, RTQ < RQ (jump-robust)
5. Update existing detect_jumps tests to pass RTQ not RQ

In tests/test_data_pipeline.py:
6. Verify compute_daily_rv_from_ticks output includes 'rtq' key
7. Verify RTQ is positive float

## Acceptance criteria
- [ ] RS+ uses >= 0, RS+ + RS- == RV always
- [ ] detect_jumps uses RTQ (not RQ) in denominator
- [ ] compute_daily_rv_from_ticks computes and returns RTQ
- [ ] RQ still computed and returned (needed for HARQ)
- [ ] RTQ added to measures.py re-exports
- [ ] 7+ new/updated tests pass
- [ ] vol test passes

## Handoff

After completing, write workspace/tmp/handoff-p0a.md with this template:

```markdown
# Handoff P0-A: Asymmetry Math Fixes

## Changes made
- [list files modified and what changed]
- detect_jumps signature: now takes `rtq` not `rq`
- Daily parquet schema: 19 columns (added 'rtq')

## Downstream impact
- Any code calling detect_jumps must pass RTQ
- Existing parquet caches missing 'rtq' column need re-ingestion
- safe_log in har.py still uses raw np.log (to be fixed in Prompt 3)

## Test results
[paste output of: vol test -k "semivariance or rtq or jump" --tb=short]
```
```

---

### Prompt 2: Evaluation Fixes (QLIKE Verification + CV Purge Gap)

```
/fix Verify QLIKE log-space sign convention and enforce CV purge_gap >= forecast horizon

## Context

Read these files first:
- src/volforecast/evaluation/metrics.py (qlike function)
- src/volforecast/pipeline/runner.py (training loop where horizons are iterated)
- src/volforecast/utils/cv.py (CV splitter classes)
- src/volforecast/config.py (CVConfig dataclass)
- tests/test_metrics.py
- tests/test_pipeline.py
- tests/test_cv_splitters.py

## Task A: Verify QLIKE sign convention

The current log-space QLIKE: mean(exp(y_true - y_pred) - (y_true - y_pred) - 1)

This IS correct per Patton (2011). Derivation:
  Variance-space: Q = sigma2/h - log(sigma2/h) - 1
  Log-space with y = log(sigma2), y_hat = log(h):
  Q = exp(y - y_hat) - (y - y_hat) - 1

Do NOT change the formula. Instead, add mathematical proof tests to VERIFY it.

### Tests to add in tests/test_metrics.py (class TestQLIKEMathProperties):

1. Minimization: QLIKE(y, y) == 0. QLIKE(y, y+offset) > 0 for all nonzero offsets.
   Test offsets: [-2, -1, -0.5, -0.1, 0, 0.1, 0.5, 1, 2]. Min at offset=0.

2. Asymmetry: QLIKE(y, y-delta) > QLIKE(y, y+delta) for delta in [0.5, 1.0, 2.0].
   Under-prediction penalized more than over-prediction (risk management convention).

3. Convexity: for fixed y_true, compute QLIKE at a grid of y_pred values.
   Second finite differences must be non-negative.

4. Cross-space consistency: log-space and variance-space QLIKE give same model ranking
   for 3 models with different quality levels.

## Task B: Enforce CV purge_gap >= forecast horizon

CVConfig.purge_gap is a single integer (default 5). For h=22, purge gap must be >= 22
to prevent label leakage. Nothing enforces this.

### Fix in pipeline/runner.py:

Inside the loop that iterates over config.horizons:

  effective_purge = max(config.cv.purge_gap, h)

Pass effective_purge to the CV splitter constructor instead of config.cv.purge_gap.

Add a warning (Python logging or Rich console) when purge_gap is auto-increased:
  f"Purge gap increased from {config.cv.purge_gap} to {h} for horizon h={h}"

### Tests to add:

5. Pipeline test: config with horizons=[1, 5, 22], purge_gap=5. For h=22, verify the
   actual purge used is 22. Check CV splits: max(train_idx) + 22 < min(test_idx).

6. Pipeline test: for h=1, original purge_gap=5 is used (5 > 1).

7. Pipeline test: for h=5, purge_gap=5 is used (5 >= 5).

## Acceptance criteria
- [ ] QLIKE formula NOT changed (verified correct)
- [ ] 4 mathematical proof tests for QLIKE pass
- [ ] effective_purge = max(config.cv.purge_gap, h) computed per horizon
- [ ] Warning logged when purge gap auto-increased
- [ ] No train/test overlap within h days for any horizon
- [ ] 7+ new tests pass
- [ ] vol test passes

## Handoff

After completing, write workspace/tmp/handoff-p0b.md:

```markdown
# Handoff P0-B: Evaluation Fixes

## QLIKE convention -- CONFIRMED CORRECT
- Formula: mean(exp(y_true - y_pred) - (y_true - y_pred) - 1)
- Verified: minimized at y_true=y_pred, convex, asymmetric (penalizes under-prediction more)
- For LightGBM gradient derivation:
  - gradient = 1 - exp(y_true - y_pred)
  - hessian = exp(y_true - y_pred)
  - Both verified by finite-difference in the proof tests

## CV purge gap fix
- Location: pipeline/runner.py, inside horizon loop
- Logic: effective_purge = max(config.cv.purge_gap, h)
- Warning logged when auto-increased

## Test results
[paste output of: vol test -k "qlike or purge or pipeline" --tb=short]
```
```

---
---

## Phase 1: Refactoring

---

### Prompt 3: Feature Utilities (safe_log + Deduplicate Log/Lag/Rolling)

```
/refactor Consolidate safe_log and extract duplicated log/lag/rolling pattern into shared utility usage

## Context

Read these files first:
- workspace/tmp/handoff-p0a.md (for awareness of RTQ/detect_jumps changes)
- src/volforecast/features/transforms.py (safe_log, lagged_log_features)
- src/volforecast/features/har.py (HARCoreLayer.compute -- look for raw np.log calls)
- src/volforecast/features/asymmetry.py (AsymmetryLayer.compute -- look for inline .clip + np.log)
- src/volforecast/features/noise_robust.py (NoiseRobustLayer.compute -- same pattern)
- tests/test_transforms.py
- tests/test_features.py

## Part A: Consolidate safe_log

Three different zero-handling strategies exist:
1. har.py: raw np.log(rv) with no protection -- produces -inf if RV is exactly 0
2. asymmetry.py: inline .clip(lower=1e-20) before np.log()
3. noise_robust.py: inline .clip(lower=1e-20) before np.log()

transforms.py already has safe_log(series, min_value=1e-20) but har.py doesn't use it.

### Fix:

1. In transforms.py: extend safe_log to handle scalars too:
   ```python
   def safe_log(x, min_value=1e-20):
       if isinstance(x, (pd.Series, pd.DataFrame)):
           return np.log(x.clip(lower=min_value))
       return np.log(max(x, min_value))
   ```

2. In har.py: replace all raw np.log() on RV/RQ series with safe_log() from transforms.

3. In asymmetry.py: replace inline .clip(lower=1e-20) + np.log() with safe_log().

4. In noise_robust.py: same as asymmetry.py.

### Verification:

Grep src/volforecast/features/ for `.clip(lower=1e-20)` -- should only be in transforms.py.
Grep for `np.log(` in feature files -- should only appear in safe_log itself or in math
functions operating on guaranteed-positive values (like squared returns in compute_rv).

## Part B: Deduplicate log/lag/rolling pattern

Three layers independently implement the same ~15-line transformation: take a daily series,
compute rolling 5-day and 22-day means, apply safe_log, shift by 1.

transforms.py already has lagged_log_features(series, name, windows=[5, 22]) that does this.

### Fix:

1. Read lagged_log_features carefully. Verify it does AVERAGE-THEN-LOG (variance space
   averaging before log transform, correct per Corsi 2009). If it does LOG-THEN-AVERAGE,
   that is wrong for HAR and must be fixed first.

2. Refactor AsymmetryLayer.compute(): replace manual rolling/log/shift with calls to
   lagged_log_features:
   ```python
   rs_pos_features = lagged_log_features(daily_data["rs_positive"], "rs_positive")
   rs_neg_features = lagged_log_features(daily_data["rs_negative"], "rs_negative")
   bpv_features = lagged_log_features(daily_data["bpv"], "bpv", windows=[5])
   ```
   Note: some features only need daily+weekly (windows=[5]), not monthly.

3. Refactor NoiseRobustLayer.compute(): same approach for rk and noise_gap.

4. For HARCoreLayer: only refactor if lagged_log_features matches the HAR convention
   (average-then-log). If the order is different, leave HARCoreLayer unchanged and
   only refactor asymmetry + noise_robust. This is the safer choice.

5. Before/after regression test: for each refactored layer, compute features on
   synthetic_daily_rv_series (existing fixture) before AND after refactoring. Assert
   outputs match within 1e-12 tolerance.

## Tests

In tests/test_transforms.py:
1. safe_log(pd.Series([0.0, 1e-25, 1.0, 100.0])) -- no -inf, no NaN
2. safe_log(0.0) for scalar -- returns log(1e-20), not -inf
3. safe_log(pd.Series([1.0, 2.0])) matches np.log exactly for normal values

In tests/test_features.py:
4. Regression: AsymmetryLayer output identical before/after refactor
5. Regression: NoiseRobustLayer output identical before/after refactor

## Acceptance criteria
- [ ] safe_log is the SINGLE source of truth for log-with-floor
- [ ] safe_log handles both pd.Series and scalar float
- [ ] har.py uses safe_log (no raw np.log on RV/RQ)
- [ ] asymmetry.py: no inline .clip(lower=1e-20)
- [ ] noise_robust.py: no inline .clip(lower=1e-20)
- [ ] At least AsymmetryLayer and NoiseRobustLayer use lagged_log_features
- [ ] No behavioral change (regression tests pass)
- [ ] vol test passes

## Handoff

After completing, write workspace/tmp/handoff-p1a.md:

```markdown
# Handoff P1-A: Feature Utilities Consolidated

## safe_log
- Location: src/volforecast/features/transforms.py
- Handles both pd.Series and scalar float
- All feature layers now use it (no inline clipping)

## lagged_log_features
- Location: src/volforecast/features/transforms.py
- Signature: lagged_log_features(series, name, windows=[5, 22], min_value=1e-20)
- Convention: [AVERAGE-THEN-LOG / LOG-THEN-AVERAGE] -- specify which
- Returns DataFrame with columns: log_{name}_d, log_{name}_w, log_{name}_m
- All shifted by 1

## What new feature layers should do
- Import safe_log and lagged_log_features from transforms
- For positive series: use lagged_log_features(series, name)
- For signed series (can be negative): use level values with .rolling().mean().shift(1)
- DO NOT duplicate the rolling/log/shift pattern

## HARCoreLayer status
- [Refactored to use lagged_log_features / Left unchanged because order mismatch]

## Test results
[paste vol test --tb=short output]
```
```

---

### Prompt 4: Infrastructure (Protocol Extension + DEV_UNIVERSE)

```
/refactor Extend FeatureLayer protocol with context kwarg and add DEV_UNIVERSE constant

## Context

Read these files first:
- src/volforecast/protocols.py (FeatureLayer protocol)
- src/volforecast/pipeline/runner.py (where feature layers are called)
- src/volforecast/constants.py (SYMBOL_UNIVERSE)
- src/volforecast/features/har.py (existing layer -- needs signature update)
- src/volforecast/features/asymmetry.py (same)
- src/volforecast/features/noise_robust.py (same)
- tests/test_protocols.py
- tests/test_pipeline.py

## Part A: FeatureLayer Protocol Extension

FeatureLayer.compute(daily_data) only accepts the RV panel. Layers 2-5 need external data:
- Layer 2: Marquee IV surface
- Layer 4: TSDB Treasury/FX/commodity
- Layer 3: L2 depth

### Fix (4 locations):

**1. protocols.py:** Change FeatureLayer:
```python
@runtime_checkable
class FeatureLayer(Protocol):
    def compute(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict[str, pd.DataFrame] | None = None,
    ) -> pd.DataFrame: ...
```

**2. pipeline/runner.py:** Change Pipeline.run() to accept and pass context:
```python
def run(self, daily_data, *, context=None, on_fold_complete=None, ...) -> dict[int, Any]:
    # In feature composition loop:
    features = layer.compute(daily_data, context=context)
```

**3. Existing layer classes** (har.py, asymmetry.py, noise_robust.py):
Add `*, context=None` to each compute() signature. They ignore it.

**4. CLI integration:** Check __main__.py and cli/ modules that call Pipeline.run().
Pass context=None for now.

## Part B: DEV_UNIVERSE Constant

Add to src/volforecast/constants.py:

```python
# 8-symbol subset for fast iteration (~75% less compute vs full 34)
# SPY/IWM: ETFs, AAPL/MSFT/NVDA: tech, XOM: energy, JPM: financials, ES: futures
DEV_UNIVERSE = frozenset({"SPY", "AAPL", "MSFT", "NVDA", "XOM", "JPM", "IWM", "ES"})
```

## Tests

In tests/test_protocols.py:
1. FeatureLayer isinstance check passes for class with new signature
2. Class without context kwarg fails isinstance check

In tests/test_pipeline.py:
3. Pipeline.run() works with context=None (backward compatible)
4. Pipeline.run() works with context={"test_key": some_dataframe}

In existing test file or new:
5. DEV_UNIVERSE is subset of SYMBOL_UNIVERSE
6. len(DEV_UNIVERSE) == 8

## Acceptance criteria
- [ ] FeatureLayer protocol has context: dict[str, pd.DataFrame] | None = None
- [ ] Pipeline.run() accepts and passes context to all layers
- [ ] All existing layers accept context=None
- [ ] DEV_UNIVERSE defined as frozenset of 8 symbols
- [ ] DEV_UNIVERSE subset of SYMBOL_UNIVERSE
- [ ] All existing tests pass
- [ ] vol test passes

## Handoff

After completing, write workspace/tmp/handoff-p1b.md:

```markdown
# Handoff P1-B: Protocol Extension + DEV_UNIVERSE

## FeatureLayer protocol
- New signature: compute(daily_data, *, context=None) -> pd.DataFrame
- context type: dict[str, pd.DataFrame] | None
- Existing layers (har_core, asymmetry, noise_robust) accept context=None and ignore it

## Pipeline.run()
- New parameter: context (keyword-only, default None)
- Passes context to each layer's compute() call

## How to use context in new layers
```python
class MyLayer:
    def compute(self, daily_data, *, context=None):
        if context is None or "my_key" not in context:
            raise ValueError("MyLayer requires context['my_key']")
        external_data = context["my_key"]
        # ... compute features ...
```

## DEV_UNIVERSE
- 8 symbols: SPY, AAPL, MSFT, NVDA, XOM, JPM, IWM, ES
- Import: from volforecast.constants import DEV_UNIVERSE

## Test results
[paste vol test --tb=short output]
```
```

---
---

## Phase 2: Feature Layers

---

### Prompt 5: Layer 2 -- Options-Implied Features

```
/feature Implement Layer 2 options-implied features: VRP, skew, term slope, butterfly

## Context

Read these handoff files first for upstream context:
- workspace/tmp/handoff-p1a.md (safe_log, lagged_log_features conventions)
- workspace/tmp/handoff-p1b.md (protocol extension, how to use context kwarg)

Then read these source files:
- src/volforecast/features/options.py (stubbed -- has function signatures and docstrings)
- src/volforecast/data/marquee.py (fetch_atm_iv, fetch_skew -- already implemented)
- src/volforecast/features/asymmetry.py (PATTERN: layer class structure)
- src/volforecast/features/transforms.py (lagged_log_features, safe_log)
- tests/test_features.py (test patterns)

## Data access reference

marquee.py provides:
- fetch_atm_iv(start, end, tenors=['1m','2m','3m','6m','1y']) -> DataFrame[date x tenor]
  Returns ATM IV in PERCENTAGE points (20.0 = 20%)
- fetch_skew(start, end, tenors) -> DataFrame[date x tenor]
  Returns 25-delta put-call IV spread
- Uses Dataset("EDRVOL_PERCENT_STANDARD") for SPX, Dataset("EDRVOL_PERCENT") with ric for single stocks

## Functions to implement

### compute_vrp(atm_iv: pd.Series, rv: pd.Series) -> pd.Series
Variance Risk Premium:
  VRP = (atm_iv / 100)^2 - rv * 252
- atm_iv in percentage (divide by 100), already annualized
- rv is daily (not annualized), multiply by 252
- CAN BE NEGATIVE. Do NOT log-transform.

### compute_skew(iv_put_25d: pd.Series, iv_call_25d: pd.Series) -> pd.Series
  skew = IV(25d put) - IV(25d call)
- Positive = put protection premium. CAN BE NEGATIVE.

### compute_term_slope(atm_short: pd.Series, atm_long: pd.Series) -> pd.Series
  slope = ATM_3m - ATM_1m
- Positive = contango. CAN BE NEGATIVE.

### compute_butterfly(iv_put_25d: pd.Series, iv_call_25d: pd.Series, iv_atm: pd.Series) -> pd.Series
  butterfly = 0.5 * (IV_25dP + IV_25dC) - IV_ATM
- Measures smile curvature / tail risk premium. Non-negative for well-behaved smiles.

### OptionsLayer.compute(daily_data, *, context=None) -> pd.DataFrame

Registered as "options" via @register_feature_layer("options").

1. Extract: iv_data = context["iv_surface"]. Raise ValueError if missing.
2. Compute all four features.
3. Transformation rules (from handoff-p1a.md):
   - ATM IV (always positive): use lagged_log_features(atm_iv_1m, "atm_iv")
     Produces: log_atm_iv_d, log_atm_iv_w, log_atm_iv_m
   - VRP, skew, term_slope (CAN BE NEGATIVE): use level with rolling means:
     vrp_d = vrp.shift(1)
     vrp_w = vrp.rolling(5).mean().shift(1)
     vrp_m = vrp.rolling(22).mean().shift(1)
   - Butterfly: butterfly_d = butterfly.shift(1)
4. All features shifted by 1 (no look-ahead).

## Tests (create tests/test_options.py)

Fixture:
```python
@pytest.fixture
def synthetic_iv_data():
    dates = pd.bdate_range("2020-01-01", periods=500, freq="B")
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "atm_iv_1m": 18.0 + rng.normal(0, 2, 500),
        "atm_iv_3m": 19.5 + rng.normal(0, 2, 500),
        "skew_1m": 4.0 + rng.normal(0, 1, 500),
    }, index=dates)
```

Tests:
1. test_vrp_positive_when_iv_above_rv: IV=30%, daily RV=0.0003. VRP > 0.
2. test_vrp_negative_when_rv_spikes: high RV, VRP goes negative.
3. test_skew_sign: put IV > call IV -> positive skew.
4. test_term_slope_sign: 3m > 1m -> positive slope.
5. test_butterfly_nonneg: well-behaved smile inputs -> butterfly >= 0.
6. test_no_lookahead: features at t use data from t-1 or earlier. result.iloc[0] is NaN.
7. test_requires_context: context=None raises ValueError.
8. test_column_names: verify expected output columns exist.

## Acceptance criteria
- [ ] All compute functions implemented (no stubs)
- [ ] OptionsLayer registered as "options" in FEATURE_REGISTRY
- [ ] Uses context["iv_surface"] -- raises ValueError if missing
- [ ] ATM IV log-transformed via lagged_log_features
- [ ] VRP, skew, term_slope use level (NOT log -- they can be negative)
- [ ] All features shifted by 1
- [ ] 8+ tests in test_options.py passing
- [ ] vol test passes

## Handoff

After completing, write workspace/tmp/handoff-p2a.md:

```markdown
# Handoff P2-A: Layer 2 Options Features

## OptionsLayer
- Registry key: "options"
- Requires context["iv_surface"] -- DataFrame with columns for ATM IV and skew by tenor
- Raises ValueError if context is None or key missing

## Features produced
- log_atm_iv_d, log_atm_iv_w, log_atm_iv_m (log-transformed, always positive)
- vrp_d, vrp_w, vrp_m (level, can be negative)
- iv_skew_d, iv_skew_w (level, can be negative)
- iv_term_slope_d (level, can be negative)
- iv_butterfly_d (level, non-negative)

## VRP formula
VRP = (atm_iv_pct / 100)^2 - rv_daily * 252

## Pattern for context population (caller's responsibility)
```python
from volforecast.data.marquee import fetch_atm_iv, fetch_skew
iv = fetch_atm_iv(start, end, tenors=["1m", "3m"])
skew = fetch_skew(start, end, tenors=["1m"])
context = {"iv_surface": pd.concat([iv, skew], axis=1)}
pipeline.run(daily_data, context=context)
```

## Test results
[paste vol test -k options --tb=short]
```
```

---

### Prompt 6: Layers 4+5 -- Cross-Asset + Calendar Features

```
/feature Implement Layer 4 (cross-asset) and Layer 5 (calendar/event) features

## Context

Read these handoff files first:
- workspace/tmp/handoff-p1a.md (safe_log, lagged_log_features conventions)
- workspace/tmp/handoff-p1b.md (protocol extension, context kwarg usage)

Then read:
- src/volforecast/features/cross_asset.py (stubbed)
- src/volforecast/features/calendar.py (stubbed)
- src/volforecast/data/tsdb.py (fetch_treasury_yields, fetch_fx_rates, fetch_commodity_prices, fetch_vix)
- src/volforecast/features/transforms.py (lagged_log_features, safe_log)
- src/volforecast/data/trading_calendar.py (get_trading_days)
- tests/test_tsdb.py (mock patterns)

---

## PART A: Layer 4 -- Cross-Asset Features

### Functions to implement in cross_asset.py

**compute_treasury_slope(long_tenor, short_tenor) -> pd.Series**
  slope = long_tenor_price - short_tenor_price
Input: Treasury close prices from TSDB (US10YT=RR, US2YT=RR). These are PRICES not yields.
The spread is a directional proxy. Can be negative.

**compute_fx_vol(fx_rates, window=22) -> pd.Series**
  log_returns = log(fx_t / fx_{t-1})
  fx_vol = sqrt(252 * rolling_mean(log_returns^2, window))
Annualized. Always positive.

**compute_commodity_vol(prices, window=22) -> pd.Series**
Same formula as FX vol. For crude oil (CL) and gold (GC).

**compute_vix_rv_ratio(vix, rv) -> pd.Series**
  ratio = (vix / 100)^2 / (rv * 252)
VIX in percentage points. Ratio > 1 = implied > realized (normal). Always positive.

**compute_dy_spillover(rv_matrix, h=10, p=4, window=200) -> pd.Series**

Diebold-Yilmaz (2012) total connectedness via rolling VAR FEVD:

For each rolling window of length `window`:
1. Fit VAR(p) to log-RV panel (use safe_log): `from statsmodels.tsa.api import VAR`
2. Compute h-step generalized FEVD: `fevd = model.fevd(h)`
3. Get FEVD matrix at final horizon. Normalize rows to sum to 1.
4. Total spillover = (sum of off-diagonal) / (sum of all) * 100

Return Series indexed by date. Range [0, 100].

Notes:
- Skip windows with < p+10 observations (return NaN)
- Catch LinAlgError from VAR and return NaN for that window
- For speed, compute every 5 days and forward-fill
- Use at least 3 assets (e.g., SPY, AAPL, JPM from daily_data or context["rv_panel"])

**CrossAssetLayer.compute(daily_data, *, context=None) -> pd.DataFrame**

Registered as "cross_asset". Expected context keys:
  context["treasury"] -- DataFrame with 2y, 10y columns
  context["fx"]       -- DataFrame with USD/JPY column
  context["commodity"] -- DataFrame with CL, GC columns
  context["vix"]      -- Series of VIX daily close
  context["rv_panel"] -- DataFrame of RV for multiple symbols (for DY spillover)

Features produced:
  treasury_slope_d, treasury_slope_w (level, shift 1)
  log_fx_vol_d, log_fx_vol_w (log, shift 1)
  log_commodity_vol_cl_d (log, shift 1)
  log_vix_d, log_vix_w, log_vix_m (log via lagged_log_features)
  log_vix_rv_ratio_d (log, shift 1)
  dy_spillover_d (level [0,100], shift 1)

---

## PART B: Layer 5 -- Calendar/Event Features

### Key design note
Calendar features are KNOWN IN ADVANCE. No .shift(1) needed.
day_of_week and month are CATEGORICAL (integer dtype for LightGBM).

### Helper functions in calendar.py

**_nth_weekday(year, month, weekday, n) -> date**
Return nth occurrence of weekday (0=Mon, 4=Fri) in month. Used for NFP and OpEx.

**_FOMC_DATES constant**
Hardcoded FOMC announcement dates 2015-2026. 8 per year (statement release day):
2015: Jan28,Mar18,Apr29,Jun17,Jul29,Sep17,Oct28,Dec16
2016: Jan27,Mar16,Apr27,Jun15,Jul27,Sep21,Nov2,Dec14
2017: Feb1,Mar15,May3,Jun14,Jul26,Sep20,Nov1,Dec13
2018: Jan31,Mar21,May2,Jun13,Aug1,Sep26,Nov8,Dec19
2019: Jan30,Mar20,May1,Jun19,Jul31,Sep18,Oct30,Dec11
2020: Jan29,Mar3,Mar15,Apr29,Jun10,Jul29,Sep16,Nov5,Dec16
2021: Jan27,Mar17,Apr28,Jun16,Jul28,Sep22,Nov3,Dec15
2022: Jan26,Mar16,May4,Jun15,Jul27,Sep21,Nov2,Dec14
2023: Feb1,Mar22,May3,Jun14,Jul26,Sep20,Nov1,Dec13
2024: Jan31,Mar20,May1,Jun12,Jul31,Sep18,Nov7,Dec18
2025: Jan29,Mar19,May7,Jun18,Jul30,Sep17,Oct29,Dec17
2026: Jan28,Mar18,Apr29,Jun17,Jul29,Sep16,Oct28,Dec16

### Functions

**compute_fomc_proximity(dates) -> DataFrame[days_to_fomc, fomc_week, fomc_day]**
- days_to_fomc: TRADING days to next FOMC (use np.busday_count or loop)
- fomc_week: 1 if days_to_fomc <= 5
- fomc_day: 1 if date IS an FOMC date

**compute_nfp_proximity(dates) -> DataFrame[days_to_nfp, nfp_week]**
NFP = first Friday of each month (algorithmic via _nth_weekday).

**compute_opex_proximity(dates) -> DataFrame[days_to_opex, opex_week]**
OpEx = third Friday of each month (algorithmic via _nth_weekday).

**compute_calendar_dummies(dates) -> DataFrame[day_of_week, month, quarter_end, year_end]**
- day_of_week: 0-4 (Mon-Fri), integer dtype
- month: 1-12, integer dtype
- quarter_end: 1 if last 5 trading days of quarter
- year_end: 1 if last 10 trading days of December

**CalendarLayer.compute(daily_data, *, context=None) -> pd.DataFrame**
Registered as "calendar". Context accepted but IGNORED.
Class attribute: CATEGORICAL_FEATURES = ["day_of_week", "month"]

---

## Tests

Create tests/test_cross_asset.py:
1. test_treasury_slope_sign: 10y > 2y -> positive
2. test_fx_vol_positive_and_reasonable: range 5-15% annualized for major pairs
3. test_vix_rv_ratio: > 1 when VIX > annualized RV
4. test_dy_spillover_range: output in [0, 100]
5. test_cross_asset_layer_requires_context: ValueError without context
6. test_cross_asset_no_lookahead: all features shifted by 1

Create tests/test_calendar.py:
7. test_nth_weekday_first_friday: verify known dates
8. test_nth_weekday_third_friday: verify known dates
9. test_fomc_on_fomc_day: days_to_fomc==0, fomc_day==1
10. test_nfp_rolls_to_next_month: day after NFP -> next month
11. test_calendar_dummies_types: day_of_week and month are int, not float
12. test_calendar_no_shift: features at date t reflect t's own position

## Acceptance criteria
- [ ] All cross-asset compute functions implemented (including DY spillover with VAR FEVD)
- [ ] CrossAssetLayer registered as "cross_asset", uses context
- [ ] All calendar compute functions implemented
- [ ] FOMC dates hardcoded 2015-2026, NFP/OpEx algorithmic
- [ ] CalendarLayer registered as "calendar", context ignored
- [ ] Calendar features: NO .shift(1), integer dtype for categoricals
- [ ] Positive series log-transformed, signed series kept as level
- [ ] 12+ tests across both test files
- [ ] vol test passes
```

---
---

## Phase 3: ML Model

---

### Prompt 7: LightGBM with Custom QLIKE Objective

```
/execute Implement LightGBM model with custom QLIKE objective (gradient + hessian in log-space)

## Context

Read these handoff files first:
- workspace/tmp/handoff-p0b.md (QLIKE convention CONFIRMED, gradient/hessian formulas)
- workspace/tmp/handoff-p1a.md (safe_log conventions)

Then read:
- src/volforecast/models/lightgbm.py (stubbed -- QLIKEObjective and LightGBMVolModel)
- src/volforecast/models/har_family.py (PATTERN: _BaseHAR for VolModel interface)
- src/volforecast/protocols.py (VolModel protocol)
- src/volforecast/registry.py (register_model decorator)
- src/volforecast/evaluation/metrics.py (qlike function)
- tests/test_models.py (model test patterns)

## Mathematical derivation (from handoff-p0b.md)

Log-space QLIKE loss: L = exp(y_true - y_pred) - (y_true - y_pred) - 1

For LightGBM custom objective (derivatives w.r.t. y_pred):
  gradient = 1 - exp(y_true - y_pred)
  hessian  = exp(y_true - y_pred)

Properties:
- Hessian > 0 always (strictly convex)
- Gradient = 0 at y_true = y_pred
- Under-prediction (y_true > y_pred): gradient < 0 -> push y_pred up
- Over-prediction (y_true < y_pred): gradient > 0 -> push y_pred down

## Implementation

### qlike_objective(y_pred, dtrain) -> (grad, hess)
```python
def qlike_objective(y_pred: np.ndarray, dtrain: lgb.Dataset) -> tuple[np.ndarray, np.ndarray]:
    y_true = dtrain.get_label()
    diff = np.clip(y_true - y_pred, -10.0, 10.0)  # prevent overflow
    exp_diff = np.exp(diff)
    grad = 1.0 - exp_diff
    hess = np.maximum(exp_diff, 1e-6)  # floor for numerical stability
    return grad, hess
```

### qlike_eval(y_pred, dtrain) -> (name, value, is_higher_better)
```python
def qlike_eval(y_pred: np.ndarray, dtrain: lgb.Dataset) -> tuple[str, float, bool]:
    y_true = dtrain.get_label()
    diff = y_true - y_pred
    loss = float(np.mean(np.exp(np.clip(diff, -10.0, 10.0)) - diff - 1.0))
    return "qlike", loss, False
```

### LightGBMVolModel class

@register_model("lightgbm"). Must satisfy VolModel protocol.

DEFAULT_PARAMS = {
    "num_leaves": 31, "learning_rate": 0.05, "feature_fraction": 0.8,
    "bagging_fraction": 0.8, "bagging_freq": 5, "verbose": -1, "seed": 42,
}

**fit(X, y):** Drop NaN rows. Split last 20% as validation for early stopping.
Create lgb.Dataset. Call lgb.train with fobj=qlike_objective, feval=qlike_eval,
early_stopping(50), log_evaluation(100). n_estimators default 1000.

**predict(X):** model.predict(X[self._feature_names])

**summary property:** feature importance (gain) as dict.

**feature_importance property:** feature importance (split) as dict.

**save(path)/load(path):** joblib roundtrip of model + feature_names + params.

## Tests (create tests/test_lightgbm.py)

Use: lgb = pytest.importorskip("lightgbm")

Fixture:
```python
@pytest.fixture
def synthetic_lgbm_data():
    rng = np.random.default_rng(42)
    n = 500
    X = pd.DataFrame({
        "log_rv_d": rng.normal(-8, 1, n),
        "log_rv_w": rng.normal(-8, 0.5, n),
        "log_rv_m": rng.normal(-8, 0.3, n),
    })
    y = pd.Series(X["log_rv_d"]*0.5 + X["log_rv_w"]*0.3 + rng.normal(0, 0.5, n))
    return X, y
```

Tests:
1. test_gradient_finite_difference: verify gradient matches (L(yp+eps)-L(yp-eps))/(2*eps)
2. test_gradient_zero_at_minimum: y_pred=y_true -> grad=0, hess=1
3. test_gradient_sign: under-prediction -> grad<0, over-prediction -> grad>0
4. test_hessian_positive: always > 0 for wide range of diff values
5. test_fit_predict: fit on synthetic, predict, verify shape and no NaN
6. test_protocol_conformance: isinstance(LightGBMVolModel(), VolModel)
7. test_save_load: fit, save, load, predictions match
8. test_feature_importance_names: keys match input columns
9. test_qlike_eval_matches_metrics: qlike_eval matches metrics.qlike for same data

## Acceptance criteria
- [ ] qlike_objective gradient matches finite-difference check
- [ ] Hessian always positive, gradient zero at minimum
- [ ] LightGBMVolModel satisfies VolModel protocol
- [ ] fit() uses custom objective + early stopping
- [ ] save/load roundtrip preserves predictions
- [ ] 9+ tests passing
- [ ] vol test -k lightgbm passes

## Handoff

After completing, write workspace/tmp/handoff-p3a.md:

```markdown
# Handoff P3-A: LightGBM Implementation

## Module: src/volforecast/models/lightgbm.py
- Registry key: "lightgbm"
- Custom objective: qlike_objective(y_pred, dtrain) -> (grad, hess)
- Custom eval: qlike_eval(y_pred, dtrain) -> ("qlike", loss, False)
- Early stopping: 50 rounds on last-20% validation split

## LightGBMVolModel interface
- fit(X: pd.DataFrame, y: pd.Series) -> Self
- predict(X: pd.DataFrame) -> np.ndarray
- summary -> dict[str, float] (gain importance)
- feature_importance -> dict[str, int] (split importance)
- save(path) / load(path)

## DEFAULT_PARAMS
num_leaves=31, learning_rate=0.05, feature_fraction=0.8,
bagging_fraction=0.8, bagging_freq=5, seed=42

## For Optuna tuning (next prompt)
These parameters should be in the search space:
num_leaves [15,255], learning_rate [0.01,0.3 log], min_child_samples [5,100],
feature_fraction [0.5,1.0], bagging_fraction [0.5,1.0], bagging_freq [0,10],
reg_alpha [1e-8,10 log], reg_lambda [1e-8,10 log], max_depth [-1,15],
n_estimators [100,2000]

## Test results
[paste vol test -k lightgbm --tb=short]
```
```

---

### Prompt 8: Optuna Hyperparameter Tuning for LightGBM

```
/execute Add Optuna hyperparameter tuning for LightGBM with walk-forward CV

## Context

Read this handoff first:
- workspace/tmp/handoff-p3a.md (LightGBMVolModel interface, default params, search space)

Then read:
- src/volforecast/models/lightgbm.py (LightGBMVolModel already implemented)
- src/volforecast/utils/cv.py (ExpandingWindowCV class)
- src/volforecast/config.py (CVConfig)
- src/volforecast/evaluation/metrics.py (qlike)

## Task

Add tune_hyperparameters() function and LightGBMVolModel.from_tuned() classmethod.
Each Optuna trial MUST use walk-forward CV (ExpandingWindowCV), NOT random k-fold.

## Implementation

Add to src/volforecast/models/lightgbm.py:

```python
def tune_hyperparameters(
    X: pd.DataFrame,
    y: pd.Series,
    cv_config: CVConfig | None = None,
    n_trials: int = 50,
    timeout: int | None = 3600,
    storage_path: Path | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    import optuna

    if cv_config is None:
        cv_config = CVConfig(method="expanding_window", n_splits=5,
                             purge_gap=5, train_size=500, test_size=63)

    storage = None
    if storage_path:
        storage = optuna.storages.RDBStorage(f"sqlite:///{storage_path}",
            engine_kwargs={"connect_args": {"timeout": 30}})

    def objective(trial):
        params = {
            "num_leaves": trial.suggest_int("num_leaves", 15, 255),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.5, 1.0),
            "bagging_fraction": trial.suggest_float("bagging_fraction", 0.5, 1.0),
            "bagging_freq": trial.suggest_int("bagging_freq", 0, 10),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            "max_depth": trial.suggest_int("max_depth", -1, 15),
            "n_estimators": trial.suggest_int("n_estimators", 100, 2000),
            "verbose": -1, "seed": seed,
        }
        splitter = ExpandingWindowCV(min_train_size=cv_config.train_size or 500,
            test_size=cv_config.test_size or 63,
            step_size=cv_config.test_size or 63,
            purge_gap=cv_config.purge_gap)

        scores = []
        for train_idx, test_idx in splitter.split(X, y):
            model = LightGBMVolModel(params=params)
            model.fit(X.iloc[train_idx], y.iloc[train_idx])
            pred = model.predict(X.iloc[test_idx])
            from volforecast.evaluation.metrics import qlike
            scores.append(qlike(y.iloc[test_idx].values, pred))
        return float(np.mean(scores))

    study = optuna.create_study(direction="minimize", study_name="lightgbm_qlike",
        storage=storage, load_if_exists=True,
        sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=n_trials, timeout=timeout)
    return study.best_params
```

Add classmethod:
```python
@classmethod
def from_tuned(cls, X, y, cv_config=None, n_trials=50, **kwargs) -> Self:
    best_params = tune_hyperparameters(X, y, cv_config, n_trials, **kwargs)
    model = cls(params=best_params)
    model.fit(X, y)
    return model
```

## Dependency note

Add `optuna` to pyproject.toml optional dependencies (same group as lightgbm) if not present.

## Tests (add to tests/test_lightgbm.py)

  optuna = pytest.importorskip("optuna")

1. test_tune_returns_valid_params: n_trials=3, verify dict has expected keys, values in range
2. test_tune_sqlite_storage: pass tmp_path/"test.db", verify file created
3. test_from_tuned_produces_fitted_model: n_trials=3, verify predict() works

## Acceptance criteria
- [ ] tune_hyperparameters uses ExpandingWindowCV (NOT random k-fold)
- [ ] 10 hyperparameters in search space
- [ ] TPE sampler with seed for reproducibility
- [ ] SQLite storage optional
- [ ] from_tuned() classmethod works
- [ ] 3+ tests passing
- [ ] vol test -k lightgbm passes
```

---
---

## Phase 4: Evaluation

---

### Prompt 9: Statistical Tests -- Diebold-Mariano + Mincer-Zarnowitz

```
/execute Implement Diebold-Mariano test (HAC for h>1) and Mincer-Zarnowitz efficiency regression

## Context

Read these files first:
- src/volforecast/evaluation/statistical_tests.py (stubbed)
- src/volforecast/evaluation/metrics.py (qlike, retransform_log_to_level)
- tests/test_metrics.py (test patterns)

## Part A: Diebold-Mariano Test

### Math

Loss differential: d_t = L_1(t) - L_2(t)
Test statistic: DM = d_bar / sqrt(var_hat / T)

For h = 1: var_hat = gamma_0 = (1/T) * sum((d_t - d_bar)^2)

For h > 1 (Newey-West HAC, Bartlett kernel, bandwidth = h-1):
  var_hat = gamma_0 + 2 * sum_{j=1}^{h-1} (1 - j/h) * gamma_j
  gamma_j = (1/T) * sum_{t=j+1}^{T} (d_t - d_bar)(d_{t-j} - d_bar)

Under H0: DM ~ N(0,1). Two-sided p-value.
Sign: positive DM = model 2 has lower loss (model 2 better).

### Implementation

```python
from scipy import stats

def diebold_mariano_test(
    loss_1: np.ndarray, loss_2: np.ndarray, horizon: int = 1
) -> dict[str, float]:
    T = len(loss_1)
    d = loss_1 - loss_2
    d_bar = np.mean(d)
    d_demean = d - d_bar

    gamma_0 = np.dot(d_demean, d_demean) / T
    var_d = gamma_0
    if horizon > 1:
        for j in range(1, horizon):
            gamma_j = np.dot(d_demean[j:], d_demean[:-j]) / T
            var_d += 2.0 * (1.0 - j / horizon) * gamma_j

    var_d = max(var_d, 1e-20)
    dm_stat = d_bar / np.sqrt(var_d / T)
    p_value = 2.0 * (1.0 - stats.norm.cdf(abs(dm_stat)))
    return {"dm_stat": float(dm_stat), "p_value": float(p_value), "mean_diff": float(d_bar)}
```

## Part B: Mincer-Zarnowitz Regression

### Math

sigma2_t = alpha + beta * sigma2_hat_t + epsilon_t

H0: alpha=0 AND beta=1 (jointly). OLS + joint F-test.

IMPORTANT: Inputs must be in VARIANCE space, not log space. Apply Duan retransformation
first if predictions are in log space.

### Implementation

```python
import statsmodels.api as sm

def mincer_zarnowitz(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    X = sm.add_constant(y_pred)
    result = sm.OLS(y_true, X).fit()
    # Joint F-test for alpha=0, beta=1
    hypotheses = "(const = 0, x1 = 1)"
    f_test = result.f_test(hypotheses)
    return {
        "alpha": float(result.params[0]),
        "beta": float(result.params[1]),
        "r_squared": float(result.rsquared),
        "alpha_se": float(result.bse[0]),
        "beta_se": float(result.bse[1]),
        "f_stat": float(f_test.fvalue),
        "f_pvalue": float(f_test.pvalue),
    }
```

## Tests (create tests/test_statistical_tests.py)

DM tests:
1. test_dm_identical_losses: DM ~ 0, p_value ~ 1.0
2. test_dm_clearly_different: loss_1=[0.5]*100, loss_2=[0.1]*100. DM > 0, p < 0.001
3. test_dm_hac_for_h5: verify var estimate changes vs h=1 on autocorrelated data
4. test_dm_sign: loss_2 < loss_1 -> DM > 0
5. test_dm_antisymmetric: DM(l1,l2) == -DM(l2,l1)

MZ tests:
6. test_mz_perfect: y_pred=y_true -> alpha~0, beta~1, R2~1, high f_pvalue
7. test_mz_biased: y_pred=y_true*0.5 -> beta != 1, low f_pvalue
8. test_mz_constant: y_pred=constant -> R2~0

## Acceptance criteria
- [ ] DM test uses Newey-West HAC for h > 1 (Bartlett kernel, bandwidth h-1)
- [ ] Positive DM = model 2 better
- [ ] MZ uses OLS with joint F-test for (alpha=0, beta=1)
- [ ] MZ inputs in variance space (documented)
- [ ] 8+ tests passing
- [ ] vol test passes

## Handoff

After completing, write workspace/tmp/handoff-p4a.md:

```markdown
# Handoff P4-A: DM Test + MZ Regression

## diebold_mariano_test(loss_1, loss_2, horizon=1) -> dict
- Location: src/volforecast/evaluation/statistical_tests.py
- Returns: dm_stat, p_value, mean_diff
- Sign convention: positive dm_stat = model 2 is better (lower loss)
- HAC bandwidth: horizon - 1 (Bartlett kernel)

## mincer_zarnowitz(y_true, y_pred) -> dict
- Returns: alpha, beta, r_squared, alpha_se, beta_se, f_stat, f_pvalue
- IMPORTANT: inputs must be variance space, not log space
- Joint F-test: H0 is alpha=0 AND beta=1

## Usage for tournament table
```python
from volforecast.evaluation.statistical_tests import diebold_mariano_test, mincer_zarnowitz
# Per-model QLIKE losses (element-wise, not aggregated):
losses_i = np.exp(y_true - pred_i) - (y_true - pred_i) - 1.0
dm = diebold_mariano_test(losses_baseline, losses_i, horizon=h)
mz = mincer_zarnowitz(np.exp(y_true), np.exp(pred_i))
```

## Test results
[paste vol test -k "diebold or mincer" --tb=short]
```
```

---

### Prompt 10: Model Confidence Set + Tournament Table

```
/execute Implement Model Confidence Set (Hansen 2011) and tournament_table aggregation function

## Context

Read this handoff first:
- workspace/tmp/handoff-p4a.md (DM test and MZ regression interfaces and usage patterns)

Then read:
- src/volforecast/evaluation/statistical_tests.py (DM and MZ already implemented)
- src/volforecast/evaluation/metrics.py (qlike, mse, r_squared, qlike_improvement_bps)
- tests/test_statistical_tests.py

## Part A: Model Confidence Set

### Algorithm (Hansen, Lunde, Nason 2011)

Input: losses dict {model_name: array of QLIKE losses, shape (T,)}

1. Start with all M models in set S.
2. For each pair (i,j) in S, compute t-statistic of mean loss differential d_ij_bar.
   Use HAC variance (same Newey-West as DM, bandwidth=1 for MCS).
3. Range statistic: T_R = max_{i,j in S} |t_ij|
4. Block bootstrap under H0:
   a) block_length = max(1, int(sqrt(T)))
   b) For each replicate b = 1..B:
      - Draw ceil(T/block_length) start positions uniformly from {0..T-1}
      - Concatenate blocks with wrap-around, trim to length T
      - Re-center: d_ij_star = d_ij[idx] - d_ij_bar
      - Compute T_R_star from re-centered differentials
   c) p_value = mean(T_R_star >= T_R)
5. If p_value < alpha:
   - Worst model: highest average relative loss (max_j t_ij for each i, take argmax)
   - Remove worst, record p-value, go to step 2
6. Remaining models = MCS at level alpha.

### Implementation

```python
def model_confidence_set(
    losses: dict[str, np.ndarray],
    alpha: float = 0.10,
    n_bootstrap: int = 10_000,
    block_length: int | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    """Returns: included, excluded, p_values, elimination_order"""
```

Block bootstrap helper:
```python
def _block_bootstrap_indices(T, block_length, rng):
    n_blocks = int(np.ceil(T / block_length))
    starts = rng.integers(0, T, size=n_blocks)
    indices = np.concatenate([np.arange(s, s + block_length) % T for s in starts])
    return indices[:T]
```

Edge cases: 1 model -> return immediately. 2 models -> degenerates to DM test.

## Part B: Tournament Table

```python
def tournament_table(
    predictions: dict[str, np.ndarray],  # model -> OOS predictions (LOG space)
    y_true: np.ndarray,                  # true values (LOG space)
    baseline: str = "har",
    horizon: int = 1,
    mcs_alpha: float = 0.10,
    mcs_bootstrap: int = 10_000,
) -> pd.DataFrame:
```

Steps:
1. Compute element-wise QLIKE losses per model:
   losses[name] = exp(y_true - pred) - (y_true - pred) - 1.0
2. Compute aggregate: qlike (mean loss), mse, r_squared per model
3. QLIKE improvement bps vs baseline
4. DM test vs baseline per model (use diebold_mariano_test from handoff-p4a.md)
5. MZ regression per model (variance space: np.exp(y_true), np.exp(pred))
6. MCS on all models
7. Assemble DataFrame sorted by QLIKE ascending:
   Columns: model, qlike, qlike_bps, mse, r_squared,
            mz_alpha, mz_beta, mz_f_pvalue,
            dm_stat, dm_pvalue, mcs_included, mcs_pvalue

Baseline model: dm_stat=0, dm_pvalue=1, qlike_bps=0.

## Tests (add to tests/test_statistical_tests.py)

MCS tests:
1. test_mcs_best_included: 3 models with clearly different loss levels.
   Best model always in MCS. Use n_bootstrap=1000.
2. test_mcs_single_model: returns that model included.
3. test_mcs_identical: all models included (can't distinguish).
4. test_mcs_structure: output has included, excluded, p_values, elimination_order.
5. test_mcs_elimination_worst_first: highest-loss model eliminated first.
6. test_mcs_reproducible: same seed -> same result.

Tournament table tests:
7. test_tournament_shape: 3 models -> 3 rows, all expected columns.
8. test_tournament_sorted: best QLIKE first.
9. test_tournament_baseline_dm_zero: baseline dm_stat=0, dm_pvalue=1.
10. test_tournament_mcs_boolean: mcs_included is boolean.

## Acceptance criteria
- [ ] MCS uses block bootstrap (not iid), block_length=sqrt(T)
- [ ] MCS sequential elimination with T_R range statistic
- [ ] Handles 1-model and 2-model edge cases
- [ ] tournament_table combines QLIKE, MSE, R2, DM, MZ, MCS
- [ ] Sorted by QLIKE ascending
- [ ] DM uses HAC for specified horizon
- [ ] MZ in variance space
- [ ] 10+ tests passing
- [ ] vol test passes

## Handoff

After completing, write workspace/tmp/handoff-p4b.md:

```markdown
# Handoff P4-B: MCS + Tournament Table

## model_confidence_set(losses, alpha=0.10, n_bootstrap=10000, block_length=None, seed=42)
- Input: {model_name: array of element-wise QLIKE losses}
- Output: included, excluded, p_values, elimination_order
- Block bootstrap with block_length=sqrt(T)

## tournament_table(predictions, y_true, baseline="har", horizon=1)
- Input: {model_name: OOS predictions in LOG space}, y_true in LOG space
- Output: DataFrame sorted by QLIKE with columns:
  model, qlike, qlike_bps, mse, r_squared,
  mz_alpha, mz_beta, mz_f_pvalue,
  dm_stat, dm_pvalue, mcs_included, mcs_pvalue

## Usage for final tournament
```python
from volforecast.evaluation.statistical_tests import tournament_table
table = tournament_table(
    predictions={"har": preds_har, "harq": preds_harq, ...},
    y_true=y_true_log,
    baseline="har",
    horizon=22,
)
print(table.to_string())
```

## Test results
[paste vol test -k "confidence or tournament" --tb=short]
```
```

---
---

## Phase 5: Tournament

---

### Prompt 11: Full HAR Baseline Tournament

```
/evaluate Run the full HAR baseline tournament: 7 models, dev universe, 3 horizons

## Context

Read these handoff files first:
- workspace/tmp/handoff-p0b.md (purge gap enforcement details)
- workspace/tmp/handoff-p4b.md (tournament_table interface and usage)

Then read:
- src/volforecast/models/har_family.py (7 models: har, harq, shar, har_j, har_cj, ridge_har, lasso_har)
- src/volforecast/pipeline/runner.py (Pipeline class)
- src/volforecast/evaluation/statistical_tests.py (tournament_table)
- src/volforecast/constants.py (DEV_UNIVERSE)
- src/volforecast/config.py (ExperimentConfig, CVConfig)
- src/volforecast/utils/persistence.py (save_experiment_results)
- workspace/configs/ (existing YAML examples)

## Task

Create a tournament runner module and execute it on the dev universe.

## Implementation

### 1. Create src/volforecast/evaluation/tournament.py

```python
from volforecast.constants import DEV_UNIVERSE
from volforecast.config import ExperimentConfig, ModelConfig, CVConfig
from volforecast.pipeline.runner import Pipeline
from volforecast.evaluation.statistical_tests import tournament_table
from volforecast.utils.persistence import save_experiment_results
from volforecast.utils.paths import raw_dir

HAR_MODELS = ["har", "harq", "shar", "har_j", "har_cj", "ridge_har", "lasso_har"]

def _feature_layers_for_model(model_name: str) -> list[str]:
    if model_name in ("shar", "har_j", "har_cj"):
        return ["har_core", "asymmetry"]
    if model_name in ("ridge_har", "lasso_har"):
        return ["har_core", "asymmetry", "noise_robust"]
    return ["har_core"]

def run_har_tournament(
    symbols: list[str] | None = None,
    date_range: tuple[str, str] = ("2015-01-02", "2024-12-31"),
    horizons: list[int] | None = None,
    models: list[str] | None = None,
    cv_config: CVConfig | None = None,
    output_dir: Path | None = None,
) -> dict[int, pd.DataFrame]:
    symbols = sorted(symbols or DEV_UNIVERSE)
    horizons = horizons or [1, 5, 22]
    models = models or HAR_MODELS
    cv_config = cv_config or CVConfig(
        method="expanding_window", purge_gap=5,
        train_size=504, test_size=63,
    )

    all_preds = {}   # (model, symbol, h) -> array
    all_actuals = {} # (symbol, h) -> array

    for model_name in models:
        for symbol in symbols:
            config = ExperimentConfig(
                name=f"tournament_{model_name}_{symbol}",
                universe=[symbol], date_range=date_range,
                horizons=horizons,
                feature_layers=_feature_layers_for_model(model_name),
                model=ModelConfig(name=model_name),
                cv=cv_config,
            )
            daily_data = pd.read_parquet(raw_dir() / f"{symbol}_rv_daily.parquet")
            pipeline = Pipeline(config)
            results = pipeline.run(daily_data)

            for h, res in results.items():
                all_preds[(model_name, symbol, h)] = res["predictions"]
                all_actuals[(symbol, h)] = res["actuals"]

            if output_dir:
                save_experiment_results(results, config, symbol)

    tournament_results = {}
    for h in horizons:
        model_preds = {}
        for m in models:
            preds = [all_preds[(m, s, h)] for s in symbols if (m, s, h) in all_preds]
            model_preds[m] = np.concatenate(preds)
        y_all = np.concatenate([all_actuals[(s, h)] for s in symbols if (s, h) in all_actuals])
        tournament_results[h] = tournament_table(
            model_preds, y_all, baseline="har", horizon=h
        )
    return tournament_results
```

### 2. Create workspace/configs/tournament_har_dev.yaml

```yaml
name: tournament_har_dev
universe: [SPY, AAPL, MSFT, NVDA, XOM, JPM, IWM, ES]
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
training_mode: per_symbol
seed: 42
output_dir: workspace/models/tournament_har_dev
```

### 3. Display with Rich

```python
from rich.console import Console
from rich.table import Table

def display_tournament(results: dict[int, pd.DataFrame]):
    console = Console()
    for h, df in sorted(results.items()):
        table = Table(title=f"QLIKE Tournament -- h={h}")
        for col in df.columns:
            table.add_column(col, justify="right" if col != "model" else "left")
        for _, row in df.iterrows():
            cells = []
            for col in df.columns:
                v = row[col]
                if isinstance(v, float):
                    cells.append(f"{v:.4f}" if abs(v) > 0.001 else f"{v:.2e}")
                else:
                    cells.append(str(v))
            table.add_row(*cells)
        console.print(table)
        console.print()
```

## Execution note

This prompt creates the infrastructure. Actually running the tournament requires real data
in workspace/raw/*.parquet. If data is not yet ingested, run:
  vol run ingest --config workspace/configs/tournament_har_dev.yaml
first.

Total experiments: 7 models x 8 symbols x 3 horizons = 168 pipeline runs.
Estimated time: ~10-30 minutes depending on data size and machine.

## Acceptance criteria
- [ ] tournament.py module created with run_har_tournament()
- [ ] _feature_layers_for_model correctly maps each HAR variant
- [ ] tournament_har_dev.yaml config created
- [ ] Rich display_tournament function works
- [ ] Code runs without error on synthetic data (mocked pipeline)
- [ ] vol test passes
```

---
---

## Implementation Notes

1. **Run order:** Follow the dependency graph. Each prompt reads its upstream handoffs.

2. **Handoff discipline:** After completing a prompt that writes a handoff, paste the
   actual test output and file changes into the handoff template. The next prompt's
   first instruction is to read that handoff.

3. **Session workflow:** Start each session with `/bootup`, then paste the prompt.
   After completing, write the handoff, then end the session.

4. **Data cache invalidation:** Prompt 1 adds RTQ to parquet schema. After implementing,
   delete workspace/raw/*.parquet and re-run ingest.

5. **Optional deps:** LightGBM and Optuna are optional. Tests use pytest.importorskip().
   Install with: uv sync --extra gpu

6. **Max 2 prompts per session.** If you finish one prompt quickly, you can start the
   next in the same session. But prioritize writing the handoff before starting the next.
