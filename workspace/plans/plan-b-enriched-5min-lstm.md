# Plan B: LSTM with Enriched 5-Minute Features

## Problem Statement

All LSTM integration attempts failed because the LSTM consumed 2,340 bars of 10-second data with only 5 weak features (`log_ret`, `vol_share`, `buy_ratio`, `log_n_trades`, `abs_ret`). The sequence is too long (vanishing gradients, excessive padding for short days) and the features are too thin (contemporaneous microstructure, not forward-looking).

**Key insight:** more features per bar, fewer bars per day. Replace 2,340 × 5 with 78 × 12+.

## Hypothesis

Switching from 2,340 10s bars × 5 features to 78 5-min bars × 12 enriched features produces a sequence short enough for clean gradient flow and rich enough per timestep to capture intraday volatility dynamics. Target: standalone LSTM QLIKE within 50 bps of XGBoost champion (0.1292 at h=1), enabling effective stacking.

## Current Architecture (Unchanged)

The LSTM model at `src/volforecast/models/lstm.py` is fully implemented and battle-tested:

- `masked LSTM (pack_padded_sequence) → attention pool → 2-layer MLP head → scalar log-RV`
- `LSTMVolModel.__init__`: input_dim, hidden_dim=64, n_layers=2, dropout=0.1, bidirectional=False, learning_rate=1e-3, weight_decay=1e-4, max_epochs=50, batch_size=64, loss="qlike", pool_mode="attention", head_mode="mlp"
- `SequenceConfig` at `config.py:234`: features list, max_bars, norm_mode, source
- `SequenceSpec` at `sequence_cache.py:44`: frozen dataclass → hash-based cache key
- `build_sequence_tensor` at `sequence_cache.py:224`: parquet → grouped by date → padded tensor (n_dates, max_bars, n_features)
- `_build_sequences_df` at `micro.py:496`: computes v2/v3 features from raw 10s bars
- Pipeline dispatches via `requires_sequences = True` on the model class

## Scope Assessment

- **Files to modify:** 3 (`micro.py`, `sequence_cache.py`, `config.py`)
- **Files to create:** 3 (test file, trial config YAML, 5-min parquets via ingestion)
- **No model changes:** The LSTM, attention pool, MLP head, loss functions are all untouched
- **Risk:** Low — the change is entirely in the data layer; the model sees `(n_dates, 78, 12)` instead of `(n_dates, 2340, 5)`

---

## Enriched 5-Minute Feature Specification

Each 5-min bar is formed by grouping 30 consecutive 10-second bars. A standard RTH session has 2,340 10s bars → 78 5-min bars (2340 / 30 = 78). If a day has fewer than 2,340 bars, the last 5-min bar may contain fewer than 30 sub-bars; this is handled naturally by the aggregation.

### Feature Channels (12)

| # | Feature | Formula | Rationale |
|---|---------|---------|-----------|
| 1 | `log_ret` | `log(close_5m / open_5m)` where open=first vwap, close=last vwap | Directional return per bar |
| 2 | `abs_ret` | `|log_ret|` | Unsigned volatility proxy |
| 3 | `vol_share` | `bar_volume / daily_total_volume` | Relative volume (U-shaped intraday) |
| 4 | `buy_ratio` | `buy_vol / (buy_vol + sell_vol + ε)` | Order flow direction |
| 5 | `order_flow_imbalance` | `(buy_vol - sell_vol) / (buy_vol + sell_vol + ε)` | Signed OFI — toxic flow indicator |
| 6 | `rolling_vpin` | rolling `Σ|buy-sell|` / `Σ(buy+sell)` over 10-bar window | Informed trading pressure |
| 7 | `cum_rv` | `cumsum(log_ret²)` within day | Intraday realized variance path |
| 8 | `session_frac` | `bar_position / 77` in [0, 1] | Time-of-day encoding |
| 9 | `price_accel` | `diff(log_ret)`, first bar = 0 | Momentum of returns (2nd derivative) |
| 10 | `log_n_trades` | `log1p(n_trades) - median(log1p(n_trades))` | Detrended activity |
| 11 | `intrabar_rv` | `sum(10s_log_ret²)` within the 5-min bar | Vol-of-vol: how volatile is the bar internally |
| 12 | `volume_surprise` | `bar_vol / rolling_mean(bar_vol, window=10)` | Volume anomaly detector |

**ε = 1e-10** throughout for numerical stability.

---

## Implementation Steps

### Step 1: 5-Minute Bar Aggregation Function
**Mode: subagent** · **Complexity: Medium** · **Est. lines: ~120**

Add a new function `_build_5min_sequences_df` in `src/volforecast/data/micro.py` that:

1. Takes the same `bars_by_date: dict[date, pd.DataFrame]` input as `_build_sequences_df`
2. Groups every 30 consecutive 10s bars into one 5-min bar
3. Computes OHLC from vwap: `open=first`, `close=last`, `high=max`, `low=min`
4. Aggregates: `total_buy_vol = sum(buy_vol)`, `total_sell_vol = sum(sell_vol)`, `total_n_trades = sum(n_trades)`
5. Computes all 12 enriched features per 5-min bar (see table above)
6. Returns DataFrame with schema: `[date, bar_idx, <12 feature columns>]`

The function sits alongside `_build_sequences_df` (which remains untouched for backward compat). A `bar_interval` parameter on the public ingestion API selects which builder to call.

```yaml
subtask_id: "execute-1"
goal: "Implement _build_5min_sequences_df in micro.py to aggregate 10s bars into 5-min bars with 12 enriched features"
file_scope:
  - src/volforecast/data/micro.py (lines 490-620: existing _build_sequences_df for pattern reference)
  - src/volforecast/constants.py (MICRO_BAR_INTERVAL = 10.0)
write_scope:
  - src/volforecast/data/micro.py
acceptance_criteria:
  - "_build_5min_sequences_df exists and accepts bars_by_date: dict[date, pd.DataFrame]"
  - "Groups every 30 consecutive 10s bars into one 5-min bar (last bar may have <30 sub-bars)"
  - "Computes all 12 features: log_ret, abs_ret, vol_share, buy_ratio, order_flow_imbalance, rolling_vpin, cum_rv, session_frac, price_accel, log_n_trades, intrabar_rv, volume_surprise"
  - "intrabar_rv = sum of (10s log_ret²) within the 5-min bar (not from 5-min log_ret)"
  - "volume_surprise uses rolling mean with window=10, first bars use expanding mean"
  - "rolling_vpin uses 10-bar rolling window on 5-min aggregated buy/sell volumes"
  - "Output schema: [date, bar_idx, log_ret, abs_ret, vol_share, buy_ratio, order_flow_imbalance, rolling_vpin, cum_rv, session_frac, price_accel, log_n_trades, intrabar_rv, volume_surprise]"
  - "Empty days produce 0 rows (consistent with existing builder)"
  - "No changes to _build_sequences_df or any other existing function"
memory_refs: []
constraints:
  - "Place function immediately after _build_sequences_df in micro.py"
  - "Use numpy vectorised operations (no Python-level loops over bars)"
  - "ε = 1e-10 for all divisions"
  - "nan_to_num on log_ret (same pattern as _build_sequences_df)"
  - "Do NOT modify constants.py or any other file"
context_summary: |
  _build_sequences_df at micro.py:496 is the template. It takes bars_by_date (dict mapping date → DataFrame with columns: buy_vol, sell_vol, vwap, n_trades). Each value is a DataFrame of 10-second bars for that day (typically ~2340 rows). The function loops over sorted dates, computes per-bar features using numpy, and builds a flat DataFrame with date + bar_idx + feature columns.

  For the 5-min version: first group every 30 rows into one bar (numpy reshape or manual slicing for the remainder), then compute the 12 enriched features on those aggregated bars. Key difference: intrabar_rv requires the original 10s log_ret² values summed within each 5-min group.

  Existing v3 features in _build_sequences_df (price_accel, rolling_vpin, cum_rv, session_frac) use the same formulas but at 10s granularity — the 5-min version recomputes them at 5-min granularity. rolling_vpin window changes from 50 (50×10s = 500s) to 10 (10×5min = 50min) to maintain similar time coverage.
depends_on: []
```

### Step 2: Wire Aggregation into Sequence Ingestion
**Mode: subagent** · **Complexity: Low** · **Est. lines: ~40**

Modify `save_sequences_cache` and/or the ingestion path so that 5-min sequences can be written to a separate directory (e.g., `data/raw/micro/sequences_5min/`). This keeps 10s and 5-min caches independent.

```yaml
subtask_id: "execute-2"
goal: "Add bar_interval parameter to sequence ingestion so 5-min sequences are saved alongside 10s sequences"
file_scope:
  - src/volforecast/data/micro.py (save_sequences_cache at ~line 640, ingest_symbol_micro)
  - src/volforecast/utils/paths.py (micro_sequences_dir)
  - src/volforecast/data/sequence_cache.py (build_sequence_tensor, lines 224-310)
write_scope:
  - src/volforecast/data/micro.py
  - src/volforecast/data/sequence_cache.py
  - src/volforecast/config.py
acceptance_criteria:
  - "SequenceConfig gets a new optional field: bar_interval: int = 10 (seconds)"
  - "When bar_interval=300 (5 min), build_sequence_tensor reads from sequences_5min/ subdirectory"
  - "When bar_interval=10 (default), existing behavior is unchanged"
  - "SequenceSpec.hash includes bar_interval so 10s and 5-min caches never collide"
  - "save_sequences_cache accepts bar_interval param and writes to appropriate directory"
  - "No breaking changes to existing 10s pipeline"
memory_refs: []
constraints:
  - "bar_interval is an integer in seconds (10 or 300)"
  - "SequenceSpec is a frozen dataclass — add bar_interval with default=10 for backward compat"
  - "Hash must change when bar_interval changes (include in hash payload string)"
  - "Directory resolution: if bar_interval != 10, append _5min suffix to sequences dir"
  - "Keep build_sequence_tensor signature backward-compatible (bar_interval comes from spec)"
context_summary: |
  SequenceSpec at sequence_cache.py:44 is a frozen dataclass with features (tuple[str,...]) and max_bars (int). Its hash property is sha1 of features + max_bars. Adding bar_interval: int = 10 maintains backward compat (existing specs hash identically).

  build_sequence_tensor at sequence_cache.py:224 takes symbol + spec + optional sequences_dir. It reads {symbol}.parquet from sequences_dir. For 5-min, we need it to resolve sequences_dir based on spec.bar_interval when sequences_dir is None.

  SequenceConfig at config.py:234 is the YAML-facing config. It has features, max_bars, sequences_dir, cache_dir, norm_mode, source. Adding bar_interval: int = 10 lets the YAML override it.

  The pipeline (runner.py:1011) constructs SequenceSpec from SequenceConfig. bar_interval flows: YAML → SequenceConfig → SequenceSpec → build_sequence_tensor → directory resolution.
depends_on: ["execute-1"]
```

### Step 3: 5-Minute Sequence Ingestion Script
**Mode: subagent** · **Complexity: Low** · **Est. lines: ~50**

Create a CLI command or script that reads existing 10s parquets from `data/raw/micro/sequences/`, passes them through `_build_5min_sequences_df`, and saves to `data/raw/micro/sequences_5min/`. This is a one-time data prep step.

```yaml
subtask_id: "execute-3"
goal: "Create a script/CLI entry to generate 5-min sequence parquets from existing 10s parquets"
file_scope:
  - src/volforecast/data/micro.py (_build_5min_sequences_df from Step 1)
  - src/volforecast/data/micro.py (save_sequences_cache, load_sequences_cache)
  - data/raw/micro/sequences/ (existing 10s parquets)
write_scope:
  - workspace/scripts/build_5min_sequences.py
acceptance_criteria:
  - "Script reads each {SYMBOL}.parquet from data/raw/micro/sequences/"
  - "For each symbol: loads 10s bars, groups by date, calls _build_5min_sequences_df, saves to data/raw/micro/sequences_5min/{SYMBOL}.parquet"
  - "Script is idempotent (safe to re-run, overwrites existing output)"
  - "Reports per-symbol stats: n_dates, n_bars_total, n_bars_per_day (mean/min/max)"
  - "Runs via ./vol shell workspace/scripts/build_5min_sequences.py"
memory_refs: []
constraints:
  - "Output directory: data/raw/micro/sequences_5min/"
  - "Preserve exact same parquet schema as _build_5min_sequences_df output"
  - "Use atomic write (write to tmp, rename) — same pattern as save_sequences_cache"
  - "Process only symbols that have existing 10s parquets"
context_summary: |
  Existing 10s parquets in data/raw/micro/sequences/ have columns: date, bar_idx, buy_vol, sell_vol, net_flow, vwap, n_trades, log_ret, vol_share, buy_ratio, log_n_trades, abs_ret, price_accel, rolling_vpin, cum_rv, session_frac.

  The script needs to: (1) read each parquet, (2) reconstruct bars_by_date dict by grouping on date column, (3) call _build_5min_sequences_df(bars_by_date), (4) save result to sequences_5min/ directory.

  For _build_5min_sequences_df, the input bars need: buy_vol, sell_vol, vwap, n_trades (the v1 columns). The v2/v3 columns (log_ret etc.) in the parquet are the 10s-level features — the 5-min function recomputes them at 5-min granularity from the raw v1 columns plus the 10s log_ret for intrabar_rv.
depends_on: ["execute-1"]
```

### Step 4: Unit Tests — 5-Min Aggregation
**Mode: subagent** · **Complexity: Medium** · **Est. lines: ~150**

TDD: write tests BEFORE implementing Step 1. Tests define the contract, then Step 1 implements to satisfy them.

```yaml
subtask_id: "execute-4"
goal: "Write unit tests for _build_5min_sequences_df covering aggregation correctness, feature formulas, and edge cases"
file_scope:
  - src/volforecast/data/micro.py (existing _build_sequences_df for pattern reference)
  - src/tests/unit/test_lstm.py (test patterns and synthetic data helpers)
write_scope:
  - src/tests/unit/test_5min_sequences.py
acceptance_criteria:
  - "Test: 90 synthetic 10s bars (3 × 30) produce exactly 3 5-min bars"
  - "Test: 100 synthetic 10s bars (3 × 30 + 10 remainder) produce 4 bars, last has 10 sub-bars"
  - "Test: log_ret = log(last_vwap / first_vwap) for each 5-min bar"
  - "Test: abs_ret = |log_ret|"
  - "Test: buy_ratio = sum(buy_vol) / (sum(buy_vol) + sum(sell_vol) + ε)"
  - "Test: intrabar_rv = sum of (10s log_ret²) within the 5-min bar"
  - "Test: cum_rv is monotonically non-decreasing within a day"
  - "Test: session_frac ∈ [0, 1] and session_frac[-1] = 1.0 (or close)"
  - "Test: volume_surprise first bar uses expanding mean (no NaN)"
  - "Test: empty day → 0 rows (edge case)"
  - "Test: single bar day → 1 5-min bar with 1 sub-bar"
  - "Test: output schema matches expected column list exactly"
  - "All tests run via ./vol test -k test_5min_sequences"
memory_refs: []
constraints:
  - "Use synthetic data (deterministic, no randomness)"
  - "Tests must be self-contained — no dependency on real parquets"
  - "Follow pytest patterns from existing test_lstm.py"
  - "Tests should FAIL initially (TDD) — they define the contract before implementation"
context_summary: |
  Create synthetic bars_by_date: a dict with 1-3 dates, each mapping to a DataFrame with columns (buy_vol, sell_vol, vwap, n_trades). Use known values so expected outputs can be computed by hand.

  Example: 60 bars (2 × 30), vwap linearly increasing from 100 to 101, buy_vol = 100 per bar, sell_vol = 50 per bar. Then:
  - 5-min bar 0: open=100.0, close=vwap[29], log_ret=log(vwap[29]/100)
  - buy_ratio = 100*30 / (100*30 + 50*30 + ε) = 3000/4500 ≈ 0.6667
  - intrabar_rv = sum of log(vwap[i+1]/vwap[i])² for i in 0..28
depends_on: []
```

### Step 5: Integration Test — LSTM with 78 × 12 Tensor
**Mode: subagent** · **Complexity: Low** · **Est. lines: ~60**

Verify the LSTM model accepts and trains on the new tensor shape without errors.

```yaml
subtask_id: "execute-5"
goal: "Write integration test verifying LSTM fit/predict with 78-bar × 12-feature synthetic sequences"
file_scope:
  - src/tests/unit/test_lstm.py (_make_synthetic_sequence helper for pattern reference)
  - src/volforecast/models/lstm.py (LSTMVolModel)
  - src/volforecast/data/sequence_cache.py (SequenceTensor)
write_scope:
  - src/tests/unit/test_5min_sequences.py (append to file from Step 4)
acceptance_criteria:
  - "Test: LSTMVolModel(input_dim=12, hidden_dim=64, n_layers=2, loss='qlike') instantiates without error"
  - "Test: fit() on synthetic SequenceTensor(n_dates=120, max_bars=78, n_features=12) completes without error"
  - "Test: predict() returns array of length n_dates"
  - "Test: model trains for at least 3 epochs (gradient flow works — no NaN loss)"
  - "Test: QLIKE loss decreases between epoch 1 and final epoch (learning signal exists)"
  - "All tests run via ./vol test -k test_5min_sequences"
memory_refs: []
constraints:
  - "Reuse _make_synthetic_sequence pattern from test_lstm.py but with max_bars=78, n_features=12"
  - "Use small n_dates (60-120) and max_epochs=10 for speed"
  - "Append to the test file created in Step 4"
context_summary: |
  test_lstm.py has a _make_synthetic_sequence helper that builds SequenceTensor with variable lengths, where target = log(var(feature_0)). The LSTM should overfit this. For the 5-min test, create the same structure but with max_bars=78, n_features=12. The key validation is that the LSTM architecture (hidden_dim=64, n_layers=2, attention pool) handles the shorter/wider tensor without shape errors.

  LSTMVolModel.fit() signature: fit(seq: SequenceTensor, y: np.ndarray, *, symbol_ids: np.ndarray | None = None, on_progress: Callable | None = None) → self
  LSTMVolModel.predict() signature: predict(seq: SequenceTensor, *, symbol_ids: np.ndarray | None = None) → np.ndarray
depends_on: ["execute-4"]
```

### Step 6: Trial Config YAML
**Mode: inline** · **Complexity: Low**

Create `workspace/configs/trial_071_lstm_5min_enriched_h1.yaml` — standalone LSTM on 5-min enriched sequences, SPY only, h=1, expanding window.

```yaml
# Trial-071: Standalone LSTM on 5-min enriched sequences (Plan B)
#
# Hypothesis: 78 bars × 12 features (5-min enriched) produces better
# standalone LSTM QLIKE than 2340 × 5 (trial-051) because:
#   - Shorter sequence → cleaner gradient flow, less padding
#   - Richer features per bar → more signal per timestep
#   - intrabar_rv and volume_surprise add vol-of-vol information
#
# Baseline comparison:
#   - HAR h=1: ~0.1368
#   - Trial-051 LSTM (2340×5): failed / weak
#   - XGBoost champion h=1: 0.1292

name: trial_071_lstm_5min_enriched_h1
universe: [SPY]
date_range: ["2015-01-02", "2026-05-30"]
horizons: [1]

feature_layers: [har_core]

model:
  name: lstm
  params:
    hidden_dim: 64
    n_layers: 2
    dropout: 0.1
    bidirectional: false
    learning_rate: 0.001
    weight_decay: 1.0e-4
    max_epochs: 50
    batch_size: 64
    val_fraction: 0.15
    early_stopping_rounds: 5
    loss: qlike
    device: auto
    precision: auto
    compile: false
    seed: 42
    pool_mode: attention
    head_mode: mlp

sequences:
  features:
    - log_ret
    - abs_ret
    - vol_share
    - buy_ratio
    - order_flow_imbalance
    - rolling_vpin
    - cum_rv
    - session_frac
    - price_accel
    - log_n_trades
    - intrabar_rv
    - volume_surprise
  max_bars: 78
  bar_interval: 300
  norm_mode: per_symbol
  source: parquet

cv:
  method: expanding_window
  purge_gap: 10
  train_size: 1260
  test_size: 252

training_mode: pooled
seed: 42

tournament:
  dh_enabled: false
  vt_enabled: false
  gsvivs_enabled: false
  baseline: lstm_5min
  models:
    - har
    - har_iv
    - lstm

output_dir: data/models/trial_071_lstm_5min_enriched
```

### Step 7: Validation Run
**Mode: inline** · **Complexity: Low**

Run trial-071 on SPY h=1 and compare QLIKE against baselines.

**Acceptance criteria:**
- Trial runs end-to-end without errors
- QLIKE score reported for all CV folds
- Compare vs HAR baseline (~0.1368) and XGBoost champion (0.1292)
- DM test vs HAR baseline (at minimum)
- If QLIKE is within 100 bps of XGBoost champion → Plan B is viable for stacking

---

## Dependency Graph

```
Step 4 (unit tests — TDD) ──────────────────────────────────┐
                                                             │
Step 1 (5-min aggregation function) ◄────── depends on 4 ───┘
    │
    ├──→ Step 2 (sequence cache + config wiring)
    │         │
    │         └──→ Step 6 (trial config YAML)
    │                   │
    │                   └──→ Step 7 (validation run)
    │
    └──→ Step 3 (ingestion script) ──→ Step 7 (needs parquets)
                                            │
Step 5 (integration test — LSTM shape) ─────┘
```

**Execution order:**
1. **Step 4** (unit tests — TDD, write failing tests first)
2. **Step 1** (implement aggregation to make tests pass)
3. **Steps 2, 3, 5** in parallel (cache wiring, ingestion script, integration test)
4. **Step 6** (trial config — needs bar_interval in SequenceConfig from Step 2)
5. **Step 7** (validation — needs parquets from Step 3, config from Step 6)

**Parallelizable groups:**
- Group A: Steps 4 → 1 (sequential, TDD)
- Group B: Steps 2, 3, 5 (parallel after Step 1)
- Group C: Step 6 (after Step 2)
- Group D: Step 7 (after Steps 3 + 6)

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| 78 bars still too long for LSTM gradient flow | Medium | Low | 78 is well within LSTM's sweet spot (10-200). pack_padded_sequence eliminates padding overhead. |
| 5-min features correlated / redundant | Low | Medium | Feature importance from attention weights will diagnose. Can drop channels later. |
| Remainder bars (last group <30 sub-bars) produce noisy features | Low | Medium | intrabar_rv and volume_surprise normalize by count. log_ret from OHLC is well-defined even for 1-bar groups. |
| 10s parquet schema varies across symbols | Medium | Low | _build_5min_sequences_df validates required columns (buy_vol, sell_vol, vwap, n_trades) upfront. |
| Cache collision between 10s and 5-min | High | Low | SequenceSpec.hash includes bar_interval. Separate directories (sequences/ vs sequences_5min/). Belt-and-suspenders. |
| Standalone LSTM still can't beat HAR | Medium | Medium | This is expected — the goal is to make the LSTM good enough for stacking, not to beat XGBoost standalone. If QLIKE < 0.16, stacking is worth trying. |

---

## Success Criteria

| Metric | Threshold | Assessment |
|--------|-----------|------------|
| Trial-071 runs end-to-end | No errors | **Gate** — must pass |
| Unit tests pass | `./vol test -k test_5min_sequences` green | **Gate** — must pass |
| Standalone LSTM QLIKE h=1 | < 0.16 | **Strong success** — viable for stacking |
| Standalone LSTM QLIKE h=1 | < 0.14 | **Exceptional** — competitive with tree models |
| DM test vs HAR | p < 0.05 | **Statistical significance** |
| QLIKE improvement over trial-051 (2340×5) | Any improvement | **Directional validation** of Plan B thesis |

## Failure Criteria

- QLIKE > 0.18: The enriched features don't help. Root-cause: likely the LSTM can't learn the mapping from intraday sequences to next-day RV. Pivot to stacking-only (use LSTM embeddings, not predictions).
- Training diverges (NaN loss): Feature scaling issue. Fix: add batch normalization or tighter norm_mode.
- Tests fail on real data but pass on synthetic: Feature computation bug. Debug with single-day trace.

---

## Files Modified/Created Summary

| File | Action | Step |
|------|--------|------|
| `src/volforecast/data/micro.py` | Add `_build_5min_sequences_df` | 1 |
| `src/volforecast/data/sequence_cache.py` | Add `bar_interval` to `SequenceSpec`, update `build_sequence_tensor` dir resolution | 2 |
| `src/volforecast/config.py` | Add `bar_interval` to `SequenceConfig` | 2 |
| `workspace/scripts/build_5min_sequences.py` | Create ingestion script | 3 |
| `src/tests/unit/test_5min_sequences.py` | Create unit + integration tests | 4, 5 |
| `workspace/configs/trial_071_lstm_5min_enriched_h1.yaml` | Create trial config | 6 |

---

## Recommended Execution

`/execute` with this plan. Step 4 first (TDD), then Step 1 to pass the tests, then Steps 2+3+5 in parallel, then Step 6, then Step 7.
