# Plan: Add `eval_symbols` Config Field

## Scope

Add an `eval_symbols` field to `ExperimentConfig` that separates the **training universe** (all symbols used to fit models) from the **evaluation universe** (symbols on which QLIKE/metrics/dashboards are computed). This lets you train pooled on 100 symbols but only measure performance on SPX — reducing noise in metrics and focusing the signal evaluation on what matters.

**Not in scope:** Filtering symbols at *training* time (that defeats pooling). The runner trains on all `universe` symbols regardless.

## Acceptance Criteria

1. `eval_symbols: [SPX]` can be added to any YAML config and round-trips through `from_yaml` / `to_yaml`.
2. When `eval_symbols` is `null` or absent, behavior is identical to today (evaluate on full universe).
3. Tournament QLIKE table, dashboard, and GSVIVS backtest metrics are computed only on `eval_symbols` when set.
4. Predictions are still generated for ALL training symbols (needed for cross-validation integrity) — filtering happens post-prediction.
5. All existing tests pass; new tests cover the field and the filtering.

## Architecture Decision

Filter predictions **after** `run_models_pooled` returns, before metrics computation — not inside the runner or the parallel workers. This keeps the training pipeline unchanged and the change minimal.

---

## Execution Plan

### Step 1 — Config field + YAML round-trip (subagent)

```yaml
subtask_id: "execute-1"
goal: "Add eval_symbols: list[str] | None = None field to ExperimentConfig with from_yaml/to_yaml support"
file_scope:
  - src/volforecast/config.py
  - src/tests/unit/test_config.py
write_scope:
  - src/volforecast/config.py
  - src/tests/unit/test_config.py
acceptance_criteria:
  - "ExperimentConfig has field eval_symbols defaulting to None"
  - "from_yaml reads eval_symbols from raw dict (optional)"
  - "to_yaml writes eval_symbols only when not None"
  - "Property effective_eval_symbols returns eval_symbols if set, else universe"
  - "New test_eval_symbols_round_trip passes"
  - "Existing test_round_trip_yaml still passes"
memory_refs: []
constraints:
  - "TDD: write failing test BEFORE implementation"
  - "Do not change behavior of any other field"
  - "Use ./vol test -x -q -k test_config to verify"
context_summary: |
  ExperimentConfig is a @dataclass in config.py with fields like universe (list[str]),
  date_range, horizons, etc. from_yaml reads raw dict at ~L711, to_yaml writes at ~L754.
  We need a new optional field eval_symbols that defaults to None. A property
  effective_eval_symbols should return self.eval_symbols or self.universe.
depends_on: []
```

### Step 2 — Tournament pooled post-prediction filter (subagent)

```yaml
subtask_id: "execute-2"
goal: "Filter predictions/actuals to eval_symbols after run_models_pooled returns, before QLIKE computation in _run_tournament_pooled"
file_scope:
  - src/volforecast/evaluation/tournament.py
  - src/volforecast/config.py
  - src/volforecast/evaluation/_parallel.py
write_scope:
  - src/volforecast/evaluation/tournament.py
acceptance_criteria:
  - "When config.eval_symbols is set, QLIKE table only includes those symbols"
  - "When config.eval_symbols is None, behavior unchanged (all symbols evaluated)"
  - "Predictions for non-eval symbols are still generated (CV integrity) but excluded from metrics"
  - "Dashboard available_symbols uses effective_eval_symbols"
memory_refs: []
constraints:
  - "TDD: write test that config with eval_symbols=[SPX] produces metrics for SPX only"
  - "Do NOT modify runner.py or _parallel.py — filter in tournament.py only"
  - "Filter point is AFTER run_models_pooled returns, BEFORE _compute_metrics"
  - "Use ./vol test -x -q -k tournament to verify"
context_summary: |
  _run_tournament_pooled (tournament.py ~L712) loads panel_data for all symbols, passes
  to run_models_pooled, gets back all_model_preds/all_actuals dicts keyed by
  model label → horizon → pd.Series with (date, symbol) MultiIndex. At ~L919
  available_symbols = list(panel_data.keys()) is used for per-symbol metrics.
  We need to filter the MultiIndex Series to only include rows where symbol is
  in config.effective_eval_symbols before computing QLIKE and building dashboard.
depends_on: ["execute-1"]
```

### Step 3 — Tournament per-symbol path filter (subagent)

```yaml
subtask_id: "execute-3"
goal: "Apply eval_symbols filter in _run_tournament_per_symbol path for metrics computation"
file_scope:
  - src/volforecast/evaluation/tournament.py
write_scope:
  - src/volforecast/evaluation/tournament.py
acceptance_criteria:
  - "Per-symbol tournament only trains+evaluates symbols in eval_symbols when set"
  - "When eval_symbols is None, all symbols are trained and evaluated (no change)"
  - "This is a genuine speedup: per-symbol training only happens for eval symbols"
memory_refs: []
constraints:
  - "TDD: add test for per-symbol path with eval_symbols"
  - "For per-symbol training_mode, eval_symbols restricts which symbols are trained (unlike pooled where all train)"
  - "Use ./vol test -x -q -k tournament to verify"
context_summary: |
  _run_tournament_per_symbol (tournament.py ~L379) iterates `for symbol in symbols`
  doing both data load and per-symbol fit+predict. For per-symbol mode, eval_symbols
  CAN genuinely skip training on non-eval symbols since each model is independent.
  This is different from pooled mode where all symbols contribute to one model.
depends_on: ["execute-1"]
```

### Step 4 — Integration test with trial config (subagent)

```yaml
subtask_id: "execute-4"
goal: "Add integration test proving eval_symbols works end-to-end with a mini tournament config"
file_scope:
  - src/tests/integration/test_kvar_integration.py
  - workspace/configs/trial_088_lstm_100sym.yaml
  - src/volforecast/evaluation/tournament.py
write_scope:
  - src/tests/integration/test_eval_symbols.py
acceptance_criteria:
  - "Integration test creates a mini 5-symbol config with eval_symbols=[SPY]"
  - "Runs a fast tournament (HAR only, 1 horizon, small date range)"
  - "Asserts metrics dict only contains SPY results"
  - "Test passes with ./vol test -x -q -k test_eval_symbols"
memory_refs: []
constraints:
  - "Test must complete in <30s (use tiny date range + HAR model only)"
  - "Do not modify any existing test files"
  - "Use fixtures/mocks for data if real data not available in CI"
context_summary: |
  The tournament entry point is run_har_tournament() in tournament.py. It accepts
  symbols, config path, and training_mode. An integration test should load a small
  config, call the tournament function, and assert the returned metrics only contain
  the eval_symbols. Use the pattern from test_kvar_integration.py as reference.
depends_on: ["execute-2", "execute-3"]
```

---

## Dependency Graph

```
Step 1 (config field) ──┬──→ Step 2 (pooled filter) ──┬──→ Step 4 (integration test)
                        └──→ Step 3 (per-symbol filter) ─┘
```

Steps 2 and 3 can run in parallel after Step 1. Step 4 waits for both.

---

## Config Example (post-implementation)

```yaml
name: trial_088_lstm_100sym
universe:
  - AAPL
  - ABBV
  - ...  # 100 symbols for training
  - XOM

eval_symbols: [SPX]  # ← NEW: only compute metrics for SPX

horizons: [1]
# ... rest unchanged
```
