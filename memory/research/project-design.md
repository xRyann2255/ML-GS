---
created: 2026-05-07
updated: 2026-05-11
tags: [architecture, design, pipeline, models, training, pooling]
status: active
priority: P1
source: workspace/research/project-design.md (archived)
relates: [complete-pipeline, optimal-feature-set, evaluation-framework, data-access]
---

# Project Design — Summary

## Project Identity

**Title:** Layered Information and Realized Volatility: Where ML Adds Value Beyond HAR
**Thesis:** Progressively enriching HAR-family baselines with microstructure, options-implied, and cross-asset features via gradient boosting → statistically significant QLIKE improvements → tradeable IV-RV gap signal.
**Extends CSV (2023)** with: GS tick data (34 symbols), Marquee IV surface, E-mini L2, cross-asset macro, and economic value translation.

## Key Design Decisions

**Feature Layer Interface:**
```python
class FeatureLayer(ABC):
    name: str
    requires: list[str]
    def compute(self, data: dict) -> pd.DataFrame:  # date × feature
    def describe(self) -> dict[str, str]:  # feature_name: paper_reference
```

**Model Interface:**
```python
class VolModel(ABC):
    def fit(self, X_train, y_train, X_val, y_val) -> None
    def predict(self, X) -> np.ndarray
    def feature_importance(self) -> pd.Series | None
```

**Pooled vs Per-Symbol Training (first-class experimental variable):**
- HAR family: per-symbol (low parameter, 2,800 obs sufficient)
- Trees: pooled across 34 symbols (~95,000 training obs) with symbol fixed effects
- Config: `training_mode: pooled | per_symbol | both`

**E-mini as Market-Level Signal:**
- E-mini L2 features enter as market-regime conditioning (same for all 34 symbols on a given date)
- Analogous to VIX — index microstructure, not per-stock

**Config-Driven Experiments:**
- YAML configs specify: universe, dates, horizons, feature layers, models, CV method
- Adding a feature layer = write one module + update config

## Package Structure (volforecast/)

```
volforecast/
├── config/          # YAML experiment configs
├── volforecast/
│   ├── data/        # rv.py, features.py, loaders.py, universe.py, units.py
│   ├── features/    # base.py, rv_features.py, micro_features.py, implied_features.py, cross_features.py, calendar.py
│   ├── models/      # base.py, har.py, garch.py, trees.py, ensemble.py, lstm.py
│   ├── evaluation/  # losses.py, tests.py, cv.py, economic.py
│   ├── signals/     # vrp.py, sizing.py, backtest.py, costs.py
│   └── utils/       # plotting.py, logging.py
├── notebooks/       # 01-06 presentation story
├── tests/
└── results/         # tables/ + figures/
```

## Forecast Horizons

- h=1 day (primary), h=5 days, h=22 days
- Multi-day: RV_{t+1:t+h} = h⁻¹ × Σ RV_{t+j}
- Target: log(RV_{t+h}) — always work in log space

## Model Progression

1. HAR, HARQ, SHAR baselines (pure econometric)
2. Ridge on HAR features + VRP + cross-asset (linear ML baseline)
3. LightGBM on same features (tests for nonlinear interactions)
4. LSTM on E-mini intraday sequences → next-day log-RV (standalone h=1 model; 2-layer LSTM, 64 hidden, single architecture from literature, no hyperparameter search)
5. Ensemble comparison (the key architectural experiment):
   - 5a: LightGBM + 32-dim LSTM embeddings as features (stacking) — favored at h=1, h=5
   - 5b: LightGBM + LSTM scalar prediction blend (static weight on validation QLIKE)
   - 5c: At h=5, test PCA-reduced (16-dim) embeddings vs full 32-dim
   - 5d: At h=22, test excluding LSTM entirely vs PCA-reduced (4-8 dim) vs blend
   - Compare QLIKE across all variants per horizon; DM test significance

**Rationale:** Feature stacking is favored because the LSTM captures a fundamentally different signal (full-day intraday microstructure state from ~78 bars) that a scalar prediction discards. AmEx 2022 (GRU → GBDT) is the closest analogy. Optiver evidence for blending does not transfer (10-min windows, not full-day). But the PDF (vol-project-ref.pdf Ch. 11) argues for blending on debuggability and gradient isolation grounds. Both must be tested. The hypothesis is stacking wins at h=1,5 and blending wins/ties at h=22 where intraday signal decays.

**LSTM training strategy:** Train ONE LSTM for h=1 only. Extract embeddings from this single model for use at all horizons. The h=1 embedding represents "yesterday's intraday microstructure state" — a general-purpose regime descriptor. Each horizon's tree decides how much to rely on it.

Each step has a clear scientific question and is independently reportable.
