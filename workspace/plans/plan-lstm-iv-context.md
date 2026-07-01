# Plan: LSTM with IV Context Vector (Option A)

## Scope

Add a "daily context vector" pathway to the LSTM model. IV/options features observed at close of day T (forward-looking for T+1) are concatenated with the LSTM's pooled sequence representation before the MLP prediction head. This gives the LSTM access to the same implied-vol information that makes XGBoost dominant.

## Acceptance Criteria

1. `LSTMVolModel` accepts `context_dim` param and `context` tensor in `fit()`/`predict()`
2. `_LSTMBody.forward()` concatenates context vector with pooled output before head
3. Config supports `context_features: list[str]` specifying daily columns to use
4. Runner builds context array from panel data, normalises it, and passes to model
5. Backward compatible: `context_dim=0` (default) → identical to current behaviour
6. All existing LSTM tests pass unchanged
7. New test: context vector of dim=3 produces correct output shape and gradient flow
8. Trial-075 config created with `context_features: [atm_iv_1d, vrp, vvix, iv_skew_25d]`

## Architecture Diagram

```
Day T data for symbol S:
┌──────────────────────────────────────────────────────┐
│  5-min bars (78×12)              Daily IV features    │
│  ┌───────────────┐               ┌──────────┐       │
│  │ log_ret       │               │ atm_iv   │       │
│  │ abs_ret       │               │ vrp      │       │
│  │ vol_share ... │               │ vvix     │       │
│  └───────┬───────┘               │ iv_skew  │       │
│          │                        └────┬─────┘       │
│          ▼                             │             │
│  ┌───────────────┐                     │             │
│  │ BiLSTM(128)   │                     │             │
│  │ 2 layers      │                     │             │
│  └───────┬───────┘                     │             │
│          │                             │             │
│          ▼                             │             │
│  ┌───────────────┐                     │             │
│  │ Attention Pool │                    │             │
│  │ → (256,)      │                    │             │
│  └───────┬───────┘                     │             │
│          │                             │             │
│          ▼                             ▼             │
│  ┌─────────────────────────────────────────┐        │
│  │  concat(pooled_256, context_4) → (260,) │        │
│  └──────────────────┬──────────────────────┘        │
│                     │                                │
│                     ▼                                │
│  ┌─────────────────────────────────────────┐        │
│  │  MLP Head: Linear(260,260) → GELU       │        │
│  │            → Dropout → Linear(260,1)    │        │
│  └──────────────────┬──────────────────────┘        │
│                     │                                │
│                     ▼                                │
│              log_RV prediction                       │
└──────────────────────────────────────────────────────┘
```

## Implementation Steps

### Step 1: Modify `_LSTMBody` architecture (subagent)

```yaml
subtask_id: "execute-1"
goal: "Add context_dim parameter to _LSTMBody and concatenate context in forward()"
file_scope:
  - src/volforecast/models/lstm.py (lines 130-300)
write_scope:
  - src/volforecast/models/lstm.py
acceptance_criteria:
  - "_LSTMBody.__init__ accepts context_dim: int = 0"
  - "head input size is out_dim + context_dim when context_dim > 0"
  - "forward() accepts optional context tensor (B, context_dim)"
  - "forward_with_internals() also passes context through"
  - "context_dim=0 produces identical behaviour (no shape change)"
memory_refs: []
constraints:
  - "Do NOT change any existing parameter defaults"
  - "Do NOT break backward compat (context=None must work)"
context_summary: "_LSTMBody is a nn.Module at line 130 of lstm.py. It has LSTM → pool → head. The insertion point is between pool output (B, out_dim) and head input. When context_dim > 0, head's first Linear must be (out_dim + context_dim, out_dim) instead of (out_dim, out_dim)."
depends_on: []
```

### Step 2: Modify `LSTMVolModel` outer class (subagent)

```yaml
subtask_id: "execute-2"
goal: "Thread context_dim and context tensor through LSTMVolModel.fit() and predict()"
file_scope:
  - src/volforecast/models/lstm.py (lines 460-1100)
write_scope:
  - src/volforecast/models/lstm.py
acceptance_criteria:
  - "LSTMVolModel.__init__ accepts context_dim: int = 0"
  - "fit() accepts context: np.ndarray | None = None, shape (N, context_dim)"
  - "predict() accepts context: np.ndarray | None = None"
  - "Training loop slices context by train/val indices and passes to _compiled()"
  - "Prediction loop passes context batches to _compiled()"
  - "context is normalised (z-score) using train-only stats stored in self._context_mean/std"
memory_refs: []
constraints:
  - "Match existing pattern for base_preds (slice by train_pos/val_pos)"
  - "Store normalisation stats on self for predict() to reuse"
  - "context=None must be backward compatible"
context_summary: "LSTMVolModel wraps _LSTMBody. fit() handles train/val split, epoch loop, early stopping. predict() runs inference. Both need to slice and pass context arrays aligned to batch indices. The _compiled forward expects (x_batch, lengths_batch, sym_batch) currently — add context_batch as 4th arg."
depends_on: ["execute-1"]
```

### Step 3: Modify runner to build and pass context (subagent)

```yaml
subtask_id: "execute-3"
goal: "Build context array from panel data daily features, normalise, pass to LSTM fit/predict"
file_scope:
  - src/volforecast/pipeline/runner.py (lines 2450-2700, 2900-3100)
  - src/volforecast/config.py (lines 296-320)
write_scope:
  - src/volforecast/pipeline/runner.py
  - src/volforecast/config.py
acceptance_criteria:
  - "SequenceConfig gains context_features: list[str] = [] field"
  - "Runner reads context_features from config"
  - "Runner builds context_arr (N, C) aligned to same idx as tensor rows"
  - "Runner passes context to model.fit() and model.predict() per fold"
  - "Context is z-score normalised using train-fold stats only"
  - "Empty context_features → no context passed (backward compat)"
memory_refs: []
constraints:
  - "Context features come from the enriched daily panel (after feature layer compute)"
  - "Must handle NaN in context features (fill with 0 after normalisation)"
  - "Features must be available at prediction time (no look-ahead)"
context_summary: "The runner already builds panel_data per symbol with all daily features. In _run_one_horizon_sequences, it builds tensor/lengths/idx from sequences. It also has access to the full panel (used for base_model). Context features are daily columns from the same panel, aligned by (date, symbol) to the sequence rows."
depends_on: ["execute-2"]
```

### Step 4: Write tests (subagent)

```yaml
subtask_id: "execute-4"
goal: "Add unit tests for context vector pathway"
file_scope:
  - src/tests/unit/test_lstm.py
  - src/volforecast/models/lstm.py
write_scope:
  - src/tests/unit/test_lstm.py
acceptance_criteria:
  - "test_context_vector_shape: model with context_dim=4 accepts (B,4) context and produces (B,) output"
  - "test_context_gradient_flow: gradients flow through context → head"
  - "test_no_context_backward_compat: model with context_dim=0 matches old behaviour"
  - "test_context_fit_predict: full fit/predict cycle with synthetic context"
  - "All existing LSTM tests still pass"
memory_refs: []
constraints:
  - "Use synthetic data (no real data dependency)"
  - "Tests must be fast (<5s each)"
context_summary: "Existing LSTM tests are in src/tests/unit/test_lstm.py. They test fit/predict with synthetic sequences. New tests verify context vector flows correctly through the architecture."
depends_on: ["execute-2"]
```

### Step 5: Create trial-075 config (inline)

```yaml
subtask_id: "execute-5"
goal: "Create trial_075_lstm_iv_context_h1.yaml config"
file_scope:
  - workspace/configs/trial_074_lstm_maxwin_h1.yaml
write_scope:
  - workspace/configs/trial_075_lstm_iv_context_h1.yaml
acceptance_criteria:
  - "Config specifies context_features: [atm_iv_1d, vrp, vvix, iv_skew_25d]"
  - "Same universe/CV as trial-074 for direct comparison"
  - "Same LSTM architecture (hidden=128, bidir, attention pool)"
depends_on: ["execute-3"]
```

## Dependency Graph

```
Step 1 (LSTMBody arch) ──┐
                         ├──→ Step 2 (LSTMVolModel fit/predict) ──→ Step 3 (Runner + Config)
                         │                                    │            │
                         │                                    ▼            ▼
                         │                              Step 4 (Tests)  Step 5 (Config)
                         │
```

Steps 1 → 2 → 3 → 5 (sequential, each builds on prior)
Step 4 can start after Step 2 (doesn't need runner changes)

## Key Design Decisions

1. **Context at pool→head junction, NOT at input**: Feeding IV as extra bar features (Option B) would repeat the same value 78 times and waste LSTM capacity. Concatenating once after pooling is cleaner and matches the "condition the prediction on context" paradigm.

2. **Normalisation inside model**: Context z-score stats are stored on the model (like how base_preds work) so predict() can reuse them. This avoids leaking test stats.

3. **Feature names in config, not hardcoded**: `context_features` is a list of column names resolved from the daily panel at runtime. Can easily swap in different IV features without code changes.

4. **NaN handling**: Fill NaN with 0 post-normalisation (= "no signal from this feature today"). This is the standard approach for missing IV data (e.g., no options on some days).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| IV features have different date coverage than sequences | Medium | Low | NaN fill handles missing days |
| Context overpowers sequence (LSTM learns to ignore bars) | Low | Medium | Monitor attention weights; can add dropout on context if needed |
| No improvement over standalone LSTM | Medium | Low | Still have trial-074 baseline; context is cheap to add |
| Test failures from shape changes | Low | High | context_dim=0 default ensures backward compat |

## Estimated Complexity

- Step 1: ~30 lines changed in lstm.py (body)
- Step 2: ~50 lines changed in lstm.py (outer class)
- Step 3: ~40 lines changed in runner.py + 3 lines in config.py
- Step 4: ~80 lines new test code
- Step 5: ~10 lines (config YAML)

Total: ~210 lines of change across 4 files + 1 new config.
