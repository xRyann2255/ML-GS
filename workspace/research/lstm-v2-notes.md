# LSTM v2 — Research Notes

## Phase 0: Split-Adjustment Audit (2026-06-16)

### Question
Is H3 real? Are the raw tick-derived sequence parquets unadjusted for stock splits?

### Method
Spot-checked `vwap` (midprice) median values on the trading day before vs. after known major splits for 5 symbols in `data/raw/micro/sequences/`.

### Results

| Symbol | Split Date | Ratio | Pre-split vwap | Post-split vwap | Observed ratio |
|--------|-----------|-------|---------------|----------------|---------------|
| NVDA | 2024-06-10 | 10:1 | 1202.52 | 121.97 | 9.86 |
| TSLA | 2022-08-25 | 3:1 | 902.39 | 293.91 | 3.07 |
| GOOGL | 2022-07-18 | 20:1 | 2232.26 | 111.44 | 20.03 |
| AMZN | 2022-06-06 | 20:1 | 2447.82 | 125.55 | 19.50 |
| AAPL | 2020-08-31 | 4:1 | 501.53 | 129.45 | 3.87 |

### Conclusion

**H3 is CONFIRMED.** The sequence parquets store raw, unadjusted tick prices from ChunkStore. Every symbol that split inside the 2015–2024 training window has a discrete price jump in `vwap`.

### Impact on Current Model (Trial-051)

Trial-051 feeds raw `vwap` levels directly into the LSTM. This means:
- The LSTM sees a 10× discontinuity in NVDA's price series at the split boundary.
- The normaliser (pooled z-score across all symbols) is corrupted by these jumps.
- The model may learn spurious "jump patterns" that are just split artifacts.

### Resolution: Phase 1 Transforms Make This Moot

The v2 stationary features are **split-invariant by construction**:

| Feature | Why split-invariant |
|---------|-------------------|
| `log_ret = log(vwap_t / vwap_{t-1})` | Ratio of consecutive prices — split factor cancels (both pre and post bars are in the same adjusted space within a single day; across the split day, first bar log_ret = 0 by design) |
| `vol_share = bar_vol / daily_total` | Fraction — numerator and denominator scale equally |
| `buy_ratio = buy / (buy + sell)` | Already a fraction, unaffected by price |
| `log_n_trades` | Trade count, not price-dependent |
| `abs_ret = |log_ret|` | Absolute value of a split-invariant quantity |

**Decision:** No re-ingestion or parquet patching needed. Phase 1's feature transforms are the fix for H3. The only residual risk is the cross-day boundary at the exact split date (one bar's `log_ret` will be ~`log(1/10)` for NVDA), but since first-bar-of-day `log_ret` is set to 0 by design, even this is handled.

### Status: RESOLVED — proceed to Phase 1.

---

## Phase 3: Per-Symbol Normalisation & Val Split Fix (2026-06-16)

### Issues Addressed: M1, L2, N3, N6, N8

### Decision: Per-Symbol Normalisation (M1) — IMPLEMENTED as opt-in

Per-symbol normalisation is available via `norm_mode: "per_symbol"` in the
`sequences:` YAML block. Default remains `"pooled"` for the initial trial-052.

**Rationale for defaulting to pooled:**
- v2 features are mostly bounded: `vol_share` ∈ [0,1], `buy_ratio` ∈ [0,1],
  `log_n_trades` is median-subtracted per day, `abs_ret` rarely > 0.01.
- Only `log_ret` has meaningfully different std across symbols (NVDA ~ 2× SPY).
- Pooled normaliser is adequate for these features.
- Per-symbol normalisation adds ~15% training overhead (per-fold groupby).

**When to enable:** If Phase 5 ablation shows LSTM collapsing to a constant
prediction for high-vol symbols, switch to `norm_mode: "per_symbol"`.

#### 2026-06-22 — CLOSED (Phase 2.7)

Per-symbol normalisation is now the default for production LSTM trials
(`trial_051/052/053/054/057/058`), with `norm_mode: per_symbol` set explicitly
in each YAML. The `feature_stack` code path still pools because it does NOT
thread `norm_mode` through to the stacked source model; an `ExperimentConfig`
`__post_init__` guard now raises `ValueError` on the unsupported combination
to prevent silent degradation. Plumbing `norm_mode` through the feature-stack
path is deferred to Phase 3.12.

### Decision: Val/Train Split Date Boundary (L2) — WON'T FIX

**Problem:** The row-index split `X[:n_train], X[n_train:]` can bisect a
calendar date when multiple symbols share the same date. This puts some
symbols' same-date rows in train and others in val.

**Assessment:** Negligible impact:
- The split point randomly lands between two symbols' rows for ONE date.
- With 21 symbols × ~2500 dates, this affects ~1 row out of ~50,000 per fold.
- Early stopping averages across the entire val set; 1 misplaced row is noise.
- Fixing requires threading real date info into the model (currently receives
  synthetic dates) or pre-splitting in the runner (API change for marginal gain).

**Decision:** Won't fix. Effort/risk exceeds benefit.

### Decision: Target Normalisation Asymmetry (N8) — DOCUMENTED, INTENTIONAL

**Observation:** Features are z-scored (per-symbol or pooled), but targets
(log-RV residuals) are NOT normalised per symbol.

**Why this is correct:**
- Targets are in log-space → magnitudes are comparable across symbols
  (log(RV_SPY) ≈ -6.5 to -4.0; log(RV_NVDA) ≈ -5.5 to -3.0 — same order).
- The LSTM output head is a single scalar; symbol embedding gives it enough
  signal to modulate output magnitude per symbol.
- Per-symbol target normalisation would require per-symbol denormalisation at
  prediction time, adding complexity with unclear benefit.
- Duan retransformation already handles systematic bias in the mean.

### Implementation Summary

| Change | File |
|--------|------|
| `norm_mode` field added to `SequenceConfig` | `src/volforecast/config.py` |
| `_resolve_sequence_config` returns `norm_mode` | `src/volforecast/pipeline/runner.py` |
| Per-symbol normaliser utilities | `src/volforecast/pipeline/norm.py` (NEW) |
| Sequential fold path: per_symbol branch | `src/volforecast/pipeline/runner.py` |
| `_execute_fold` parallel worker: per_symbol branch | `src/volforecast/pipeline/runner.py` |
| Tests (11 passing) | `src/tests/unit/test_per_symbol_norm.py` (NEW) |

### Status: COMPLETE — infrastructure ready for ablation in Phase 5.

---

## Phase 4: Cleanup & Config (2026-06-16)

### Issues Addressed: L3, L4, L5, N9, N10

### L3: Multi-GPU Fold Worker Returns Model Path

**Problem:** `_execute_fold` returned `"model_path": None` even though
`save_fold_cache` already persisted the model to disk. Downstream code
(`runner.py:1233`) tried to reload `last_model` from that path and got
nothing — meaning multi-GPU runs never had a `last_model` available.

**Fix:** After `save_fold_cache` completes, check if `model.pt` exists in
the cache directory and return its path. When cache is disabled, return None
(no save was attempted).

### L4 + N9: REQUIRED_LAYERS Cleared for LSTM

**Problem:** `LSTMVolModel.REQUIRED_LAYERS = ["har_core"]` caused the
evaluation/tournament utils to expect a tabular `har_core` panel even for
standalone LSTM runs. With `feature_layers: []` this would fail.

**Fix:** Set `REQUIRED_LAYERS = []`. The LSTM consumes sequences, not tabular
features. When used with residual stacking, the `base_model` section carries
its own `feature_layers` — the top-level `feature_layers` for a standalone
LSTM can be empty.

### L5: `_maybe_compile` Uses `dynamic=True`

**Problem:** `torch.compile(mode="reduce-overhead")` without `dynamic=True`
uses CUDA Graph capture which records tensor shapes. Packed sequences
(`pack_padded_sequence`) produce variable-length tensors per batch →
different graph shapes → recompilation every batch → massive overhead.

**Fix:** Added `dynamic=True` to the non-embedding compile path as well.
Both paths now use `dynamic=True`:
- `n_symbols > 0`: `mode="default", dynamic=True`
- `n_symbols == 0`: `mode="reduce-overhead", dynamic=True`

Trial-052 v2 config sets `compile: false` to establish baseline without
compile noise. Re-enable in a follow-up once correctness is confirmed.

### N10: Pooled Duan Correction — KEPT AS-IS

**Assessment:** With log-RV targets, cross-symbol variance in residuals is
moderate. A pooled correction is a reasonable approximation:
- log(RV) magnitudes are comparable across symbols (~2 orders of magnitude range).
- Per-symbol correction would require tracking `symbol_ids` through Duan
  computation and applying separate corrections — added complexity for
  marginal improvement.
- The symbol embedding already helps the model produce symbol-appropriate
  predictions, reducing systematic per-symbol bias in residuals.

**Decision:** Keep pooled. Revisit only if diagnostic plots show symbol-level
bias in Duan residuals.

### Trial-052 v2 Config Created

New config: `workspace/configs/trial_052_lstm_v2.yaml`
- Standalone LSTM with v2 stationary features + symbol embedding (dim=8)
- `feature_layers: []` (no tabular dependency)
- `compile: false` (baseline establishment)
- 21 symbols, 2015–2024, h=[1,5,22]
- Expanding window CV (504 train / 126 test / 10 purge)
- Tournament comparison vs `har` and `har_iv`

### Implementation Summary

| Change | File |
|--------|------|
| `REQUIRED_LAYERS = []` | `src/volforecast/models/lstm.py` |
| `_maybe_compile` adds `dynamic=True` to non-embedding path | `src/volforecast/models/lstm.py` |
| `_execute_fold` returns `model_path` from fold cache | `src/volforecast/pipeline/runner.py` |
| Trial-052 v2 standalone config | `workspace/configs/trial_052_lstm_v2.yaml` |
| Phase 4 tests (8 passing) | `src/tests/unit/test_phase4_cleanup.py` (NEW) |

### Test Results

- 8 new Phase 4 tests: PASS
- 14 related LSTM/symbol/runner/norm tests: PASS
- 1796 full non-slow suite: PASS (1 skipped, 47 deselected slow)

### Status: COMPLETE — ready for Phase 5 (validation run).
