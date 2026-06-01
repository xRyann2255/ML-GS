# Research Index

Tracks deep research outputs: what was run, what was extracted, and where it lives.

## 2026-05-06: ML for Realized Volatility Forecasting

- **Source prompt**: `notes/deep-research-prompt.md`
- **Raw output**: `notes/deep-research-vol-papers.md` (trimmed to landscape survey after extraction)
- **Extracted to**:
  - `reference/bibliography.md` -- ~80 entries across 11 categories (A-K)
  - `notes/project-proposals.md` -- 4 project directions, recommendations, decision benchmarks, caveats
  - `notes/features/har-components.md` -- realized higher moments, signed jump variation, long memory / fractional differencing, ML horizon findings
  - `notes/features/implied-vol.md` -- VRP construction and predictiveness, VIX term structure, risk-neutral skewness, VVIX
  - `notes/features/microstructure.md` -- Rahimikia-Poon LOB findings, order flow imbalance, FinText sentiment (brief note)
  - `notes/features/cross-asset.md` -- Diebold-Yilmaz spillover framework, GNN cross-asset findings, common idiosyncratic vol
  - `notes/features/leverage-effect.md` -- signed semivariance asymmetry (Patton-Sheppard 2015)
  - `notes/features/jump-detection.md` -- jump persistence findings, earnings-trigger-jumps
  - `notes/features/optimal-feature-set.md` -- Variable Importance Clouds / Rashomon feature analysis, pitfall warnings
  - `notes/features/calendar-events.md` -- NEW: FOMC, earnings, macro releases

## 2026-05-07: State of the Art in Decision Trees

- **Source prompt**: `notes/deep-research-prompt-decision-trees.md`
- **Raw output**: `notes/deep-research-decision-trees.md` (trimmed to landscape survey after extraction)
- **Extracted to**:
  - `reference/bibliography.md` -- ~50 new entries in category H, 12 existing entries enriched, 8 new topic tags
  - `notes/project-proposals.md` -- decision tree methodology assessment, implementation roadmap, 10 caveats
  - `notes/features/optimal-feature-set.md` -- Rashomon pipeline design, feature interchangeability, novelty confirmation
  - `notes/features/har-components.md` -- accuracy comparison (optimal trees vs HAR vs LightGBM)

## 2026-05-31: What Beats HAR (2024-26 SOTA sweep)

- **Workflow**: `.claude/workflows/deep-research-distill.js` (reusable; Scope -> Harvest -> adversarial Verify -> Distill). Invoke with `args={question, slug, depth}`
- **Question**: What beats HAR for daily RV forecasting in 2024-26 under QLIKE? (transformers, TS foundation models, GNNs, LLMs, GBMs)
- **Raw output / brief**: `notes/deep-research/2026-05-31-what-beats-har-2024-26.md` (87 harvested, 11 verified and kept)
- **Headline**: univariate daily RV under QLIKE is HAR's turf; wins come from features (options/rough-Heston +5.8% QLIKE), covariance (GHAR, MCS p=1.000), or longer horizons. Every modern-architecture QLIKE claim so far fails the DM+MCS bar.
- **Corrections to prior notes**: killed a fabricated "XGBoost beats HAR daily" figure; fixed HARd-to-Beat window (630d, not 2.5-4y); flagged Fed FEDS regime-HAR as MSPE-only (vanishes under QLIKE)
- **Extracted to**: `notes/features/har-components.md`, `notes/features/implied-vol.md`, `notes/features/cross-asset.md`, `notes/open-questions.md` (univariate-vs-covariance decision)
- **Port target**: JLDC/HARd-to-Beat (GitHub) as the HAR+ML fair-fight harness; GHAR repo (chaozhang-ox/GNNHAR) has MCS testing built in
