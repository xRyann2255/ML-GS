# Plan A: TCN on 5-Minute Raw Returns (DeepVol-Style)

**Date:** 2026-07-01
**Status:** EXECUTED — TCN underperforms HAR baseline (QLIKE 0.306 vs 0.204), as expected for raw-returns-only single-feature input. Value is in ensemble/stacking.
**Scope:** End-to-end TCN implementation — 5-min bar aggregation, model, pipeline integration, tests, validation run

---

## Problem Statement

All LSTM integration attempts (10+ trials) have failed. The root cause is bad input data: the LSTM consumed 2,340 bars of 10-second microstructure features that are contemporaneous (describe today's intraday dynamics), not forward-looking (predict tomorrow's RV). The sequence signal was noise dressed up as structure.

DeepVol (Moreno-Pino & Zohren 2022) achieved SOTA by feeding **raw 5-minute returns** into a TCN (Temporal Convolutional Network). The key insight: raw returns contain the volatility signal directly (RV is literally the sum of squared returns), and dilated causal convolutions capture multi-scale temporal patterns without the vanishing gradient issues of LSTMs.

**Target:** Implement DeepVol-style TCN on 5-min bars. Compare vs XGBoost champion (QLIKE 0.1292 at h=1). Even if TCN doesn't beat XGBoost standalone, it may provide complementary signal for ensemble/stacking.

---

## Dependency Graph

```
Step 1 (tests: 5-min agg)  ──→  Step 2 (impl: 5-min agg)  ──→  Step 5 (config + pipeline)
                                                                       │
Step 3 (tests: TCN model)  ──→  Step 4 (impl: TCN model)  ────────────┤
                                                                       │
                                                                       ↓
                                                               Step 6 (integration test)
                                                                       │
                                                                       ↓
                                                               Step 7 (validation run)
```

**Parallel opportunities:**
- Steps 1+3 are independent (both are test-writing) → **parallel**
- Steps 2+4 are independent after their tests pass → **parallel**
- Step 5 depends on both 2 and 4
- Step 6 depends on 5
- Step 7 depends on 6

---

## Acceptance Criteria (Overall)

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | 5-min bar aggregation produces 78 bars/day from 2,340 10s bars | Unit test: synthetic 2340-bar day → 78 5-min bars |
| AC-2 | `build_sequence_tensor` works with `max_bars=78` and 5-min source parquets | Unit test + integration test |
| AC-3 | `TCNVolModel.fit()` trains without error on synthetic data | Unit test: loss decreases over 10 epochs |
| AC-4 | `TCNVolModel.predict()` returns correct-shape output | Unit test: (N,) float array, one per date |
| AC-5 | Trial-070 config runs end-to-end on SPY, h=1 | Integration: produces QLIKE number, no crash |
| AC-6 | All existing tests pass (no regression) | `./vol test -x -q` green |
| AC-7 | TCN QLIKE is compared vs HAR baseline on SPY | Validation run outputs comparison |

---

## Implementation Steps

### Step 1: Write failing tests for 5-min bar aggregation
**Mode:** `subagent` — isolated file creation, no dependencies
**Complexity:** S

Write unit tests for a `aggregate_to_5min` function that groups 30 consecutive 10-second bars into one 5-minute bar. Tests define the contract before implementation.

```yaml
subtask_id: "plan-a-step-1"
goal: >
  Write unit tests for aggregate_to_5min() that converts 10-second bar
  DataFrames into 5-minute bar DataFrames. Tests must FAIL (function
  doesn't exist yet) — TDD.
file_scope:
  - src/volforecast/data/sequence_cache.py      # SequenceTensor, SequenceSpec, build_sequence_tensor
  - src/volforecast/data/micro.py               # existing micro module (lines 1-50, understand structure)
  - src/tests/unit/test_lstm.py                 # _make_synthetic_sequence pattern (lines 1-50)
write_scope:
  - src/tests/unit/test_5min_aggregation.py
acceptance_criteria:
  - "Test file exists with ≥6 test cases"
  - "Tests import from volforecast.data.resample (the module where aggregate_to_5min will live)"
  - "Test cases cover:"
  - "  1. Full day: 2340 10s bars → 78 5-min bars with correct log_ret (sum of sub-bar log_ret)"
  - "  2. Partial day: 1800 bars → 60 5-min bars (no partial trailing bar)"
  - "  3. Multiple dates: two days processed independently"
  - "  4. Output columns: date, bar_idx (0-77), log_ret, abs_ret, realized_vol (sum of squared log_ret per 5-min bar)"
  - "  5. Edge case: fewer than 30 bars in last group → dropped (no partial 5-min bars)"
  - "  6. Empty DataFrame → empty DataFrame"
  - "Tests FAIL when run (ImportError or AttributeError expected, NOT SyntaxError)"
memory_refs: []
constraints:
  - "Use ./vol test -x -q -k test_5min to verify syntactically valid"
  - "Do NOT implement the function — only tests"
  - "Input schema matches existing 10s parquets: columns [date, bar_idx, log_ret, abs_ret, vol_share, ...]"
  - "Output schema: [date, bar_idx, log_ret, abs_ret, rv_5min] where rv_5min = sum(log_ret^2) within the 5-min bar"
context_summary: >
  Existing 10s bar parquets live in data/raw/micro/sequences/{SYMBOL}.parquet with columns:
  date, bar_idx (0-2339), buy_vol, sell_vol, net_flow, vwap, n_trades, log_ret, vol_share,
  buy_ratio, log_n_trades, abs_ret, price_accel, rolling_vpin, cum_rv, session_frac.
  We need aggregate_to_5min(df: DataFrame) -> DataFrame that groups every 30
  consecutive bars (by bar_idx within each date) into one 5-min bar. The function
  will live in src/volforecast/data/resample.py (existing file — currently has
  daily OHLCV resampling logic).
depends_on: []
```

---

### Step 2: Implement 5-min bar aggregation
**Mode:** `subagent` — single-module implementation
**Complexity:** M

Implement `aggregate_to_5min()` in the resample module. This function converts 10-second bar DataFrames into 5-minute bars by grouping 30 consecutive bars per date.

```yaml
subtask_id: "plan-a-step-2"
goal: >
  Implement aggregate_to_5min() in src/volforecast/data/resample.py that
  converts 10s bars to 5-min bars. Make the tests from Step 1 pass.
file_scope:
  - src/volforecast/data/resample.py            # target module
  - src/volforecast/data/micro.py               # reference for 10s bar schema
  - src/tests/unit/test_5min_aggregation.py     # tests to satisfy
  - src/volforecast/data/sequence_cache.py      # build_sequence_tensor for integration context
write_scope:
  - src/volforecast/data/resample.py
acceptance_criteria:
  - "aggregate_to_5min(df: pd.DataFrame) -> pd.DataFrame exists and is importable"
  - "All tests in test_5min_aggregation.py pass"
  - "Function signature: aggregate_to_5min(df: pd.DataFrame, bar_interval_s: int = 10, target_interval_s: int = 300) -> pd.DataFrame"
  - "Groups bar_idx // (target_interval_s // bar_interval_s) within each date"
  - "Computes per 5-min bar: log_ret = sum(sub_log_ret), abs_ret = |log_ret|, rv_5min = sum(sub_log_ret^2)"
  - "Assigns new sequential bar_idx 0..N-1 per date"
  - "Drops incomplete trailing groups (< 30 bars)"
memory_refs: []
constraints:
  - "Vectorized pandas operations — no Python-level row loop"
  - "Do not modify any existing functions in resample.py"
  - "Run ./vol test -x -q -k test_5min to verify"
context_summary: >
  The 10s parquets have columns [date, bar_idx, log_ret, abs_ret, ...].
  bar_idx runs 0..2339 for a full day (2340 bars × 10s = 6.5h).
  Grouping 30 consecutive bars yields 78 five-minute bars per full day.
  log_ret is additive across sub-bars (log returns sum). rv_5min = Σ(log_ret²)
  within each 5-min window — this is the intra-bar realized variance that the
  TCN will learn to predict at the daily level.
depends_on:
  - "plan-a-step-1"
```

---

### Step 3: Write failing tests for TCN model
**Mode:** `subagent` — isolated test creation, no dependency on Step 1/2
**Complexity:** M

Write comprehensive unit tests for `TCNVolModel` covering forward pass, training loop, predict output, and save/load. Tests target the stub at `lstm.py:1421`.

```yaml
subtask_id: "plan-a-step-3"
goal: >
  Write unit tests for TCNVolModel: forward pass shape, gradient flow,
  fit with synthetic data (loss decreases), predict output shape, and
  save/load round-trip. Tests must FAIL (NotImplementedError) — TDD.
file_scope:
  - src/volforecast/models/lstm.py              # TCNVolModel stub (lines 1418-1460), LSTMVolModel for reference pattern
  - src/volforecast/models/_base.py             # _BaseModel interface
  - src/volforecast/data/sequence_cache.py      # SequenceTensor dataclass (lines 80-130)
  - src/tests/unit/test_lstm.py                 # reference test pattern (_make_synthetic_sequence, lines 1-70)
write_scope:
  - src/tests/unit/test_tcn.py
acceptance_criteria:
  - "Test file exists with ≥8 test cases"
  - "Tests import TCNVolModel from volforecast.models.lstm"
  - "Test cases cover:"
  - "  1. requires_sequences is True"
  - "  2. Forward pass: _TCNBody(input_dim=3, n_channels=[32,32,16]) on random (B,T,F) → output shape (B,)"
  - "  3. Gradient flow: loss.backward() produces non-zero .grad on conv weights"
  - "  4. Causal property: output at time t depends only on inputs ≤ t (perturbation test)"
  - "  5. fit() with synthetic data: loss at epoch 10 < loss at epoch 1"
  - "  6. predict() returns (N,) float array matching len(seq.dates)"
  - "  7. save/load round-trip: predictions are identical after reload"
  - "  8. QLIKE loss path trains and converges"
  - "  9. get_params() returns all constructor args"
  - "Tests use _make_synthetic_sequence helper (adapted from test_lstm.py)"
  - "Tests FAIL with NotImplementedError when run against the current stub"
memory_refs: []
constraints:
  - "Use ./vol test -x -q -k test_tcn to verify syntactically valid"
  - "Do NOT implement TCNVolModel — only tests"
  - "Mark module with pytestmark = pytest.mark.slow (matching test_lstm.py)"
  - "TCN forward pass test uses the nn.Module directly (_TCNBody), not the model wrapper"
  - "Synthetic data: use 78 max_bars (5-min bars), 3 features, 60 dates"
context_summary: >
  TCNVolModel stub at lstm.py:1421 has requires_sequences=True, constructor
  accepts input_dim, n_channels, kernel_size, dropout, learning_rate,
  max_epochs, batch_size. fit/predict raise NotImplementedError.
  The nn.Module will be called _TCNBody (analogous to _LSTMBody at lstm.py:145).
  It should be: input → [CausalConv1d + ReLU + Dropout] × L → global avg pool → linear → (B,).
  LSTMVolModel tests at test_lstm.py show the pattern: _make_synthetic_sequence,
  overfit test, predict shape test, save/load round-trip.
depends_on: []
```

---

### Step 4: Implement TCN model
**Mode:** `subagent` — largest implementation step, single file
**Complexity:** L

Fill in `TCNVolModel` with a dilated causal convolution stack. Reuse LSTM helper functions for device resolution, loss, train/val splitting, and length-bucketed batching.

```yaml
subtask_id: "plan-a-step-4"
goal: >
  Implement TCNVolModel in src/volforecast/models/lstm.py: replace the stub
  with a working dilated causal convolution model. Make all tests from
  Step 3 pass.
file_scope:
  - src/volforecast/models/lstm.py              # full file — TCN stub (1418-1460), LSTM reference (430-1418)
  - src/volforecast/models/_base.py             # _BaseModel save/load interface
  - src/volforecast/data/sequence_cache.py      # SequenceTensor (lines 80-130)
  - src/tests/unit/test_tcn.py                  # tests to satisfy
write_scope:
  - src/volforecast/models/lstm.py
acceptance_criteria:
  - "TCNVolModel.fit(seq, y) trains a TCN and stores self.model_ (nn.Module)"
  - "TCNVolModel.predict(seq) returns (N,) numpy array of log-RV predictions"
  - "All tests in test_tcn.py pass"
  - "Architecture: _TCNBody nn.Module with:"
  - "  - L residual blocks, each: CausalConv1d(dilation=2^l) → ReLU → Dropout → CausalConv1d → residual add"
  - "  - 1x1 conv for residual path when channel dims change"
  - "  - Global average pooling over valid timesteps (masked)"
  - "  - Linear head → scalar"
  - "Reuses from LSTM code: _resolve_device, _resolve_precision, _qlike_loss, _mse_loss, _split_train_val_by_date, _length_bucketed_perm"
  - "Supports: QLIKE and MSE loss, early stopping, batch training, val_fraction"
  - "save() and load() work via _BaseModel.save/load (joblib)"
  - "get_params() returns dict of all constructor hyperparameters"
memory_refs: []
constraints:
  - "Do NOT modify any LSTM code — only replace the TCN stub section"
  - "Do NOT add new dependencies — use only torch.nn"
  - "Causal convolution: pad left only (kernel_size - 1) * dilation zeros on the left, no right padding"
  - "Residual blocks: if input channels ≠ output channels, use 1x1 conv for skip connection"
  - "Weight initialization: Kaiming normal for conv layers"
  - "Run ./vol test -x -q -k test_tcn to verify all pass"
  - "Run ./vol test -x -q -k test_lstm to verify no LSTM regression"
context_summary: >
  The TCN stub starts at lstm.py:1421 after the LSTM implementation.
  Helper functions available in the same file:
    _resolve_device(device: str) → str                      (line 59)
    _resolve_precision(precision: str, device: str) → dtype  (line 73)
    _qlike_loss(pred, target) → Tensor                       (line 280)
    _mse_loss(pred, target) → Tensor                         (line 276)
    _LOSSES dict                                             (line 295)
    _split_train_val_by_date(dates, val_frac) → (train, val) (line 348)
    _length_bucketed_perm(L, batch_size, n_buckets, gen)     (line 393)
  
  LSTMVolModel reference (line 430-1418) shows the full pattern:
    - __init__ sets hyperparams + self._module = None
    - fit() builds _LSTMBody, runs training loop with AdamW + ReduceLROnPlateau
    - predict() runs inference in eval mode with no_grad
    - save/load via _BaseModel (joblib) — works if all state is in self.__dict__
  
  TCN architecture (DeepVol paper):
    Input: (B, T, F) where T=78 (5-min bars), F = small (1-3 features)
    → transpose to (B, F, T) for Conv1d
    → L residual blocks with dilations [1, 2, 4, 8, ...]
    → Each block: CausalConv1d → ReLU → Dropout → CausalConv1d → residual
    → Global average pool over T (masked for variable-length sequences)
    → Linear → scalar log-RV prediction
  
  Constructor should accept: input_dim, n_channels, kernel_size, dropout,
  learning_rate, weight_decay, max_epochs, batch_size, val_fraction,
  early_stopping_rounds, val_purge_gap, loss, device, precision, seed
depends_on:
  - "plan-a-step-3"
```

---

### Step 5: Config and pipeline integration
**Mode:** `subagent` — config wiring, touches multiple files lightly
**Complexity:** M

Wire 5-min aggregation into the sequence tensor pipeline and create the trial-070 config YAML. The key change: when `sequences.source = "parquet_5min"`, `build_sequence_tensor` should read from pre-aggregated 5-min parquets (or aggregate on-the-fly from 10s parquets).

```yaml
subtask_id: "plan-a-step-5"
goal: >
  Wire 5-min aggregation into the sequence cache pipeline and create
  trial-070 config YAML for TCN on SPY.
file_scope:
  - src/volforecast/data/sequence_cache.py      # build_sequence_tensor, load_sequence_tensor
  - src/volforecast/data/resample.py            # aggregate_to_5min (from Step 2)
  - src/volforecast/config.py                   # SequenceConfig dataclass (lines 234-270)
  - src/volforecast/pipeline/runner.py          # _run_pooled_sequences (line 2130), _resolve_sequence_config
  - workspace/configs/trial_065_rosenbaum_daily_lstm.yaml  # reference LSTM config
  - workspace/configs/trial_067_xgboost_all_layers.yaml    # reference XGBoost config
write_scope:
  - src/volforecast/data/sequence_cache.py
  - workspace/configs/trial_070_tcn_deepvol_h1.yaml
acceptance_criteria:
  - "build_sequence_tensor supports aggregation: when source parquet has bar_idx > max_bars and a resample flag is set, it aggregates 10s → 5-min before tensor construction"
  - "Alternative approach (preferred): add build_5min_sequence_tensor() that reads 10s parquets and aggregates inline, outputting (n_dates, 78, n_features) tensor"
  - "SequenceConfig gains no new fields — use existing max_bars=78 + a convention: max_bars ≤ 100 implies 5-min aggregation from 10s source"
  - "OR: add source='parquet_5min' to SequenceConfig.source enum"
  - "Trial-070 YAML is valid and parseable by ExperimentConfig"
  - "Trial-070 config:"
  - "  name: trial_070_tcn_deepvol_h1"
  - "  universe: [SPY]"
  - "  model.name: tcn"
  - "  model.params: input_dim=1, n_channels=[64,64,32], kernel_size=7, dropout=0.2"
  - "  sequences.features: [log_ret]"
  - "  sequences.max_bars: 78"
  - "  horizons: [1]"
  - "  cv: expanding_window, train_size=504, test_size=126, purge_gap=5"
memory_refs: []
constraints:
  - "Do NOT break existing 10s bar paths — max_bars=2340 must still work"
  - "Do NOT change SequenceConfig in a way that breaks existing configs"
  - "Minimize runner.py changes — prefer encapsulating aggregation in sequence_cache.py"
  - "Run ./vol test -x -q to verify no regressions"
context_summary: >
  _run_pooled_sequences (runner.py:2130) calls _resolve_sequence_config() to
  get (features, max_bars, sequences_dir, cache_dir, norm_mode, source), then
  builds SequenceSpec and calls load_sequence_tensor(). The simplest integration
  path: add a new builder function build_5min_sequence_tensor() that reads the
  10s parquet, calls aggregate_to_5min(), then pads/truncates to max_bars=78.
  
  The runner can detect TCN's need for 5-min bars via max_bars being small
  (≤100) or via a new source mode. Preferred: add source="parquet_5min" to
  SequenceConfig.source so the runner dispatches to the right builder.
  
  Trial-070 config follows the pattern of trial-065 (LSTM) but with:
    model.name: tcn
    sequences.source: parquet_5min  (or parquet with max_bars=78)
    sequences.features: [log_ret]   (DeepVol uses only raw returns)
    sequences.max_bars: 78
depends_on:
  - "plan-a-step-2"
  - "plan-a-step-4"
```

---

### Step 6: Integration test — full pipeline with TCN
**Mode:** `subagent` — test creation and verification
**Complexity:** M

Write an integration test that runs the full pipeline with TCN model on synthetic data, verifying end-to-end correctness from config parsing through fold execution to QLIKE output.

```yaml
subtask_id: "plan-a-step-6"
goal: >
  Write an integration test that runs Pipeline.run_pooled() with TCN model
  on synthetic sequence data. Verify the full path: config → sequence loading
  → TCN fit → TCN predict → QLIKE computation.
file_scope:
  - src/tests/unit/test_tcn.py                     # unit tests from Step 3
  - src/tests/integration/test_rv_pipeline.py       # existing pipeline integration test pattern
  - src/volforecast/pipeline/runner.py              # Pipeline.run_pooled (line 990)
  - src/volforecast/config.py                       # ExperimentConfig, SequenceConfig
  - src/volforecast/data/sequence_cache.py          # build_sequence_tensor, build_5min_sequence_tensor
write_scope:
  - src/tests/integration/test_tcn_pipeline.py
acceptance_criteria:
  - "Integration test creates a minimal ExperimentConfig with model.name='tcn'"
  - "Test uses synthetic 10s parquets (written to workspace/tmp/) or mocks sequence loading"
  - "Pipeline.run_pooled() completes without error"
  - "Output contains fold results with QLIKE values (numeric, not NaN)"
  - "Test cleans up any temp files in workspace/tmp/"
  - "Test is marked pytest.mark.slow"
memory_refs: []
constraints:
  - "Do NOT run against real market data — use synthetic data only"
  - "Use ./vol test -x -q -k test_tcn_pipeline to verify"
  - "Test must complete in < 60 seconds (small synthetic data)"
  - "All file writes to workspace/tmp/"
context_summary: >
  The integration test pattern from test_rv_pipeline.py: create ExperimentConfig
  programmatically, build panel_data dict, call Pipeline(config).run_pooled(panel_data).
  For TCN: need either mock SequenceTensors or real parquets in a temp dir.
  The simplest approach: create synthetic 10s parquet in workspace/tmp/,
  point SequenceConfig.sequences_dir at it, run pipeline.
depends_on:
  - "plan-a-step-5"
```

---

### Step 7: Single-symbol validation run (SPY, h=1)
**Mode:** `inline` — orchestrator runs the experiment and reads results
**Complexity:** S

Run TCN on SPY only with h=1, expanding window. Compare QLIKE vs HAR baseline. This is a smoke test on real data, not a full experiment.

**Rationale for inline:** This is a simple command execution + result reading. No code changes needed. The orchestrator runs `./vol exec` with the trial-070 config and reads the output.

**Execution plan:**
1. Run: `./vol exec python -m volforecast.cli workspace/configs/trial_070_tcn_deepvol_h1.yaml`
2. Read output file for QLIKE results
3. Compare vs known HAR baseline on SPY (~0.16-0.18 QLIKE at h=1)
4. Record finding in session memory

**Acceptance criteria:**
- Trial-070 runs to completion without error
- QLIKE value is produced (numeric, reasonable range 0.05-0.50)
- Result is compared to HAR baseline
- If QLIKE > 0.30: investigate (model may not be learning)
- If QLIKE < 0.20: promising signal, proceed to multi-symbol experiment

**Depends on:** `plan-a-step-6`

---

## Architecture Details

### 5-Minute Bar Aggregation

```
Input:  data/raw/micro/sequences/SPY.parquet
        columns: [date, bar_idx(0-2339), log_ret, abs_ret, vol_share, ...]
        
Aggregation:
        bar_group = bar_idx // 30   (30 × 10s = 5 min)
        per group per date:
            log_ret_5min = Σ log_ret        (log returns are additive)
            abs_ret_5min = |log_ret_5min|
            rv_5min      = Σ log_ret²       (realized variance of 5-min bar)
            vol_share    = Σ vol_share      (optional: total volume share)
            
Output: DataFrame with bar_idx 0..77, or SequenceTensor (n_dates, 78, n_features)
```

### TCN Architecture (`_TCNBody`)

```
Input: (B, 78, F)  where F = 1..3 features (log_ret minimum)
       ↓ transpose to (B, F, 78) for Conv1d
       
Block 0: CausalConv1d(F → 64, k=7, d=1) → ReLU → Dropout
          CausalConv1d(64 → 64, k=7, d=1) → residual add (1x1 conv for F→64)
          
Block 1: CausalConv1d(64 → 64, k=7, d=2) → ReLU → Dropout
          CausalConv1d(64 → 64, k=7, d=2) → residual add
          
Block 2: CausalConv1d(64 → 32, k=7, d=4) → ReLU → Dropout
          CausalConv1d(32 → 32, k=7, d=4) → residual add (1x1 conv for 64→32)
          
       ↓ masked global average pool → (B, 32)
       ↓ Linear(32, 1) → (B,) log-RV prediction
       
Receptive field: Σ_l 2 * (k-1) * d_l = 2 * 6 * (1+2+4) = 84 > 78 ✓
   (full sequence coverage with 3 blocks and kernel_size=7)
```

### Causal Convolution Implementation

```python
class _CausalConv1d(nn.Module):
    """Conv1d with left-only padding for causal (no future leakage)."""
    def __init__(self, in_ch, out_ch, kernel_size, dilation):
        self.pad = (kernel_size - 1) * dilation  # left padding
        self.conv = nn.Conv1d(in_ch, out_ch, kernel_size, dilation=dilation)
    
    def forward(self, x):  # x: (B, C, T)
        x = F.pad(x, (self.pad, 0))  # pad left only
        return self.conv(x)
```

### TCNVolModel API

```python
class TCNVolModel(_BaseModel):
    requires_sequences = True
    
    def __init__(self, *, input_dim, n_channels=[64,64,32], kernel_size=7,
                 dropout=0.2, learning_rate=1e-3, weight_decay=1e-4,
                 max_epochs=100, batch_size=32, val_fraction=0.15,
                 early_stopping_rounds=5, val_purge_gap=1,
                 loss="qlike", device="auto", precision="auto", seed=42):
        ...
    
    def fit(self, seq: SequenceTensor, y: pd.Series | np.ndarray, *,
            base_preds=None, symbol_ids=None, on_progress=None,
            on_batch_progress=None) -> None:
        # Mirrors LSTMVolModel.fit() structure:
        # 1. Validate input_dim vs seq.n_features
        # 2. Align targets (log-transform, NaN mask)
        # 3. Train/val date split
        # 4. Build _TCNBody, optimizer, scheduler
        # 5. Training loop: epoch → length-bucketed batches → loss → backward
        # 6. Early stopping on val QLIKE
        ...
    
    def predict(self, seq: SequenceTensor, *,
                base_preds=None, symbol_ids=None) -> np.ndarray:
        # eval mode, no_grad, batch inference
        ...
    
    def get_params(self) -> dict[str, Any]:
        ...
```

### Trial-070 Config (target)

```yaml
name: trial_070_tcn_deepvol_h1
universe: [SPY]
date_range: ["2015-01-02", "2024-12-31"]
horizons: [1]
feature_layers: [har_core]  # minimal — TCN uses raw returns, not computed features

model:
  name: tcn
  params:
    input_dim: 1
    n_channels: [64, 64, 32]
    kernel_size: 7
    dropout: 0.2
    learning_rate: 0.001
    weight_decay: 0.0001
    max_epochs: 100
    batch_size: 64
    val_fraction: 0.15
    early_stopping_rounds: 10
    loss: qlike
    device: auto
    precision: auto
    seed: 42

sequences:
  source: parquet_5min
  features: [log_ret]
  max_bars: 78
  norm_mode: pooled

cv:
  method: expanding_window
  purge_gap: 5
  train_size: 504
  test_size: 126

training_mode: pooled

tournament:
  dh_enabled: false
  vt_enabled: false
  gsvivs_enabled: false
  models:
    - tcn
    - har
```

---

## Risk Analysis

| Risk | Impact | Mitigation |
|------|--------|------------|
| TCN overfits on SPY-only (small dataset) | High | Start with dropout=0.2, early stopping, monitor train/val gap |
| 78 bars too short for dilated convolutions | Medium | Receptive field covers full sequence; can reduce kernel_size if needed |
| 5-min aggregation loses microstructure signal | Medium | This IS the DeepVol insight: raw returns > engineered features |
| Pipeline integration breaks existing LSTM path | High | Step 6 integration test + full regression suite |
| TCN doesn't beat HAR (returns are too noisy as single-day predictors) | Expected | TCN value is in ensemble/stacking, not standalone |

---

## Future Extensions (Out of Scope)

- Multi-day lookback: feed D days of 78 bars = D×78 sequence (DeepVol uses 20 days)
- Multi-symbol pooled training (like LSTM trials)
- Feature stacking: TCN prediction as feature for XGBoost
- Attention/interpretability: add attention weights for feature importance analysis
- Hyperparameter tuning via Optuna (tune_and_fit support)
