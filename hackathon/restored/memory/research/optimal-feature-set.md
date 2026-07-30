---
created: 2026-05-07
updated: 2026-05-11
tags: [features, feature-engineering, layers, architecture, LightGBM, LSTM]
status: active
priority: P1
source: workspace/research/optimal-feature-set.md
relates: [feature-composition, project-design, har-components, microstructure, implied-vol, cross-asset]
---

# Optimal Feature Set — Summary

## Layer Architecture (7 layers, ~80-120 features total)

**Layer 0 — HAR core + measurement quality (5 features):**
- log RV daily/weekly/monthly (Corsi 2009), Realized Quarticity RQ = (n/3)Σr⁴, RQ interaction = √RQ × RV_d
- RQ interaction is the **single most impactful HAR extension** (5-15% QLIKE gain, BPQ 2016)
- HARQ with 5 features often beats ML models with dozens of features lacking noise-awareness

**Layer 1 — Asymmetric volatility (6 features):**
- RS⁻ (negative semivariance) carries **2x predictive weight** of RS⁺ (Patton-Sheppard 2015)
- Continuous variation C_t = max(BPV, 0): persistent (ACF ~0.6-0.7)
- Jump variation J_t = max(RV - BPV, 0): unpredictable (ACF ~0.0-0.1) but regime-break signal
- 3-8% QLIKE improvement from this layer alone

**Layer 2 — Options-implied (9 features, SPX only):**
- ATM IV, VRP, 25d Risk Reversal, term slope, butterfly, VVIX, VIX term structure, IV-RV gap, event-implied vol
- At 1-day horizon: only 1-3% QLIKE. At weekly-monthly: **5-10% QLIKE** (options embed future events)
- GS edge: full SPX tenor×strike grid from Marquee ERDVOL

**Layer 3 — Microstructure (9 features, E-mini L2 only):**
- Price acceleration (log-return-of-log-return): **single most predictive micro feature** (Optiver evidence)
- OBI, depth ratio, market urgency, spread dynamics, signed volume, sub-window RV ratio, VPIN
- L2 depth is E-mini only; equities get L1 features (spread, price acceleration)

**Layer 4 — Cross-asset spillovers (8 features):**
- Treasury slope change, FX vol (USD/JPY), commodity vol (CL, GC), DY spillover index
- Sector-mean RV, VIX-equity correlation regime, cross-asset RV rank
- 1-5% QLIKE, concentrated in regime transitions

**Layer 5 — Calendar/event (8 features):**
- FOMC, NFP/CPI, OpEx, quarter-end, earnings proximity, event-implied vol, time-of-day, day-of-week
- Individually weak but tree models pick them up naturally

**Layer 6 — Long-memory/roughness (4 features):**
- Fractionally differenced RV (d ~ 0.35-0.45), rolling Hurst exponent, vol-of-vol, regime duration

## Architecture Decision

```
LightGBM (Layers 0-6 tabular) + LSTM (E-mini intraday sequences)
    → Feature stacking preferred at h=1 and h=5 (LSTM embeddings as LightGBM inputs)
    → Prediction blending as comparison baseline / preferred at h=22
```

### Evidence Cross-Reference

**For blending (from vol-project-ref.pdf Ch. 11, Optiver 2021):**
- PDF Section 11.2 explicitly advocates prediction-level blending: "Feature-level stacking breaks gradient isolation and couples model debugging"
- Optiver winners used blending, not stacking (confirmed in research journal May 6)
- Argument: LightGBM cannot backprop into LSTM, so embedding is never optimized for tabular objective
- Debuggability: each branch evaluable independently; degradation easier to diagnose
- Retraining independence: models retrain separately without sequential dependency

**For stacking (from research journal May 6, AmEx 2022, first-principles analysis):**
- AmEx 2022 1st place used GRU embeddings → GBDT (feature stacking) and won
- Our LSTM processes full-day E-mini sequences (~78 bars) — closer to AmEx's rich sequential data than Optiver's 10-min windows
- LSTM predicts a fundamentally different thing (intraday microstructure state) than LightGBM (daily tabular features)
- 32-dim embedding preserves conditional information (liquidity withdrawal, order flow clustering) that collapsing to a scalar discards
- Tree can learn conditional interactions (e.g., "when embedding dim 5 is high AND VIX in backwardation → vol spikes")
- Blending can only learn static weight; stacking enables state-dependent weighting

**Key nuance (PDF Section 10.2 hedges):**
- "Both approaches should be compared on our data"
- PDF Section 10.3 acknowledges "our full-day sequences are substantially richer and harder to summarize manually" — implicitly supports stacking

**No published academic paper tests LSTM-embedding → GBDT stacking for vol forecasting.** Evidence is entirely from Kaggle competitions in different domains.

### Horizon-Specific Recommendation

| Horizon | Preferred approach | Rationale |
|---|---|---|
| **h=1 (daily)** | **Feature stacking** | Intraday state directly predictive; conditional interactions with VRP/VIX; 95k pooled obs handles 32 extra dims easily |
| **h=5 (weekly)** | **Feature stacking** (reduced dims) | Regime type persists; embedding serves as regime classifier that interacts with VRP; PCA to 16 dims to manage noise |
| **h=22 (monthly)** | **Prediction blending or exclude LSTM** | Intraday micro irrelevant at this horizon; only ~4,300 effective pooled obs; overfitting risk from 32 noisy dims; options features dominate |

### Implementation Strategy

1. Train ONE LSTM on h=1 task (where it has strongest signal and most training signal)
2. Extract last-hidden-state embeddings (32-dim) from that h=1-trained LSTM for all horizons
3. At h=1 and h=5: feed embeddings into LightGBM (feature stacking)
4. At h=22: either exclude embeddings or PCA-reduce to 4-8 dims
5. Compare stacking vs blending at each horizon — if stacking wins, keep it; if not, blend is simpler

### Risks to Monitor

- **Embedding stability across retrains:** if embedding space rotates on walk-forward window shifts, tree features become unstable. Measure cosine similarity across retrains.
- **Lookahead through embeddings:** LSTM training window must end before LightGBM test window in walk-forward. Sequential training creates a temporal dependency.
- **Redundancy with L6 features:** vol-of-vol and regime duration may already capture what the embedding encodes. If L6 subsumes the regime information, stacking adds complexity without value.

- Engineering principle: for each base quantity compute {level, change, z-score} — triples count, trees handle redundancy via splits

## Diminishing Returns

| Stage | Features | Cumulative Accuracy |
|-------|----------|-------------------|
| L0 (HAR core) | 5 | 55% |
| +L1 (asymmetry) | 11 | 70% |
| +L2 (options) | 20 | 85% |
| +L3-L4 | 40 | 95% |
| +L5-L6 | 80-120 | 100% |

First 20 features (L0-L2) achieve 85% of attainable accuracy with Ridge regression alone.
