---
description: "Feature engineering — add new features to the pipeline registry and validate implementation"
argument-hint: "feature layer number (0-6) and feature name"
model: Claude Opus 4.6
---

You are in **feature engineering mode**. Add new features to the feature registry, implement computation code, and validate against paper formulas.

- `personas/vol-researcher.md`
- `personas/model-builder.md`

**Feature layers:**
- **0:** HAR core (log RV d/w/m, RQ, RQ interaction)
- **1:** Asymmetry (semivariances, BPV, jumps, continuous variation)
- **2:** Options-implied (ATM IV, VRP, skew, term slope, butterfly, VVIX)
- **3:** Microstructure (price accel, OBI, depth ratio, spread, VPIN — E-mini L2 only)
- **4:** Cross-asset (Treasury slope, FX vol, commodity vol, DY spillover)
- **5:** Calendar (FOMC, NFP, OpEx, earnings proximity)
- **6:** Interaction/derived (cross-layer interactions, regime indicators)

**Workflow:**

1. Confirm which layer and symbol(s) to compute.
2. Load the relevant P2 memory card for that layer (e.g., `memory/research/har-components.md` for Layer 0).
3. Fetch raw data via DATA_INGEST skill if not already available.
4. Compute features using `src/ml_vol_estimator/features/` modules. Follow paper formulas exactly.
5. Validate: check distributions (histograms, summary stats), look for NaN/inf, verify no look-ahead bias.
6. Save feature DataFrame to `workspace/tmp/` as parquet.

**Expected outputs:** Feature DataFrame (parquet), validation summary (distributions, NaN counts, date coverage).
