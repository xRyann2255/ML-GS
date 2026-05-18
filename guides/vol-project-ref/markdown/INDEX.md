# Realized Volatility Forecasting: A Project Reference

**Everything needed to build and defend the vol forecasting system.**

Ryan Vincent

These markdown files are a faithful word-for-word conversion of `vol-project-ref/main.pdf`, with TikZ diagrams recreated as Mermaid. Intended for use on machines where the PDF is not easily readable by LLM tools (e.g., GitHub Copilot).

---

## Part I: The Project

| Ch. | Title | Summary |
|-----|-------|---------|
| [1](ch01-what-we-forecast.md) | What We're Forecasting | Target: log RV at h={1,5,22} days. Universe: 35 instruments. Primary metric: QLIKE. |
| [2](ch02-our-data.md) | Our Data | Six raw data sources: tick RV, OHLCV, E-mini L2, SPX IV surface, cross-asset, calendars. |

## Part II: The Feature Set

| Ch. | Title | Summary |
|-----|-------|---------|
| [3](ch03-har-core.md) | HAR Core and Measurement Quality | Layer 0: HAR baseline + HARQ with RQ interaction. Five features, 40--60% R-squared. |
| [4](ch04-asymmetry-jumps.md) | Asymmetry and Jumps | Layer 1: Signed RV, jump decomposition (BPV, C/J), leverage effect. |
| [5](ch05-options-implied.md) | Options-Implied Features | Layer 2: ATM IV, VRP, skew, term structure, VVIX. Forward-looking; strongest at h=5,22. |
| [6](ch06-microstructure.md) | Microstructure Features | Layer 3: Order book imbalance, VPIN, Kyle lambda, spread, price acceleration. |
| [7](ch07-cross-asset.md) | Cross-Asset Spillovers | Layer 4: Treasury slope, FX/commodity vol, DY spillover index, Graph-HAR. |
| [8](ch08-feature-composition.md) | Feature Composition and Selection | Layers 5--7 (calendar/memory/sentiment). Diminishing returns curve. Horizon-dependent selection. |

## Part III: Models

| Ch. | Title | Summary |
|-----|-------|---------|
| [9](ch09-lightgbm.md) | LightGBM for Tabular Volatility | Primary ML model. Custom QLIKE objective. DART boosting. SHAP interpretability. |
| [10](ch10-lstm-intraday.md) | LSTM for Intraday Sequences | Second branch: LSTM/TCN on E-mini 5-min bars + LOB. Independent next-day log RV forecast. |
| [11](ch11-ensemble.md) | The Ensemble | Two-branch architecture: prediction-level blending of LightGBM and LSTM/TCN outputs. |
| [12](ch12-rashomon.md) | Interpretable Trees and Rashomon Analysis | Optimal decision trees (STreeD). Rashomon set enumeration, RID, Variable Importance Clouds. Novel contribution. |

## Part IV: Making It Work

| Ch. | Title | Summary |
|-----|-------|---------|
| [13](ch13-evaluation.md) | Evaluation | QLIKE, retransformation bias, MZ regression, DM test, MCS, DSR. Purged CV, walk-forward, evaluation workflow pipeline. |
| [14](ch14-complete-pipeline.md) | The Complete Pipeline | End-to-end system diagram. Six-step implementation roadmap. Lookahead bias checklist. |

## Part V: The Build

| Ch. | Title | Summary |
|-----|-------|---------|
| [15](ch15-pipeline.md) | The Data-to-Feature Pipeline | Data lineage funnel. Complete feature matrix with source, derivation, and expansion for all layers. |
| [16](ch16-architecture.md) | System Architecture | Three ensemble architectures compared: feature stacking, residual stacking, prediction blending. |
| [17](ch17-modular-pipeline.md) | Modular Pipeline Design | Config-driven, registry-based software design. One YAML = one experiment. |
| [18](ch18-development-plan.md) | The Development Plan | Eleven milestones (M0--M10). Critical path: M3--M4--M8--M10. MVP = M3--M7. |

---

## Quick Reference

**Key numbers:**
- Universe: 35 instruments (30 mega-cap equities + 4 ETFs + E-mini ES)
- Features: 80--120 (after triple expansion of ~37--57 base features)
- Layers 0--2 (20 features) achieve 85% of attainable accuracy
- Target: 30--80 bps QLIKE improvement over HARQ baseline
- Training window: rolling 5 years

**Key models:** HAR, HARQ, SHAR, Ridge-HAR, LightGBM (primary), LSTM/TCN (intraday), STreeD (interpretable)

**Key metrics:** QLIKE (primary), MSE, MAE, Diebold--Mariano test, Model Confidence Set
