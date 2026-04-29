# ML Signal Discovery — Internship Project Scratchpad

## Purpose
This repo is a scratchpad for thinking, brainstorming, and planning an ML internship project focused on developing market signals using Goldman Sachs SecDB. It is not a production codebase.

## Contents
- `Signal Discovery.pdf` — comprehensive 17-page research document covering SecDB architecture, ML method hierarchy, validation frameworks, 5 candidate project directions, and an annotated bibliography of ~80 papers
- `docs/superpowers/specs/2026-04-23-risk-as-alpha-design.md` — full 20-week design spec (approved)
- `docs/superpowers/plans/2026-04-23-risk-as-alpha-plan.md` — detailed implementation plan with 24 tasks across 7 chunks (approved)

## Key Context
- **Internship scope**: 20 weeks (~5 months), cross-asset (XA) desk, active now (April 2026)
- **Access**: Read access to SecDB risk cubes (VaR, scenario P&L, factor decompositions) confirmed
- **Core thesis**: Turn risk-system outputs (VaR, scenario P&L, Greeks, factor decompositions) into alpha signals, not just risk controls
- **ML method hierarchy**: LightGBM/XGBoost > regularized linear (ridge/lasso) > autoencoders as feature extractors > deep learning (mostly oversold for this domain)
- **Validation is non-negotiable**: Purged K-fold CV with embargo, Deflated Sharpe Ratio, CPCV, transaction-cost-aware backtesting, ridge baseline on identical features
- **Presentation framing**: Causal hypothesis + ML testing, not "black box found alpha." Lead with IC/Sharpe/turnover, include SHAP, always show ridge baseline

---

## Design Spec Summary

**File:** `docs/superpowers/specs/2026-04-23-risk-as-alpha-design.md`

### Project Structure
Layered build — Project 1 ("Risk as Alpha") as primary deliverable with shared infrastructure enabling Project 2 ("Book-Gamma Intraday Momentum") as fallback or extension. Data-driven checkpoint at week 13.

### Thesis
Intermediary asset pricing theory (He-Krishnamurthy 2013, Adrian-Etula-Muir 2014, He-Kelly-Manela 2017) proves dealer balance-sheet constraints price risk across asset classes. External researchers use stale quarterly Fed Z.1 data. SecDB provides daily, cross-asset risk outputs with correct dealer sign. Test whether these predict returns, volatility, and drawdowns.

### Phases

**Phase 0: Pitch & Alignment (Weeks 1-2)**
- Get sponsor buy-in with 1-2 page pitch document
- Data access audit: confirm pullable risk cube outputs (delta VaR, component VaR, factor-VaR concentration, scenario P&L, VaR utilization)
- Minimum viable data gate: need (a) daily VaR with component breakdown + (b) at least one of scenario P&L / factor-VaR / VaR utilization
- Confirm Python package availability, schedule Week 13 checkpoint, identify backup reviewer

**Phase 1: Shared Infrastructure (Weeks 3-5)**
- Data pipeline with point-in-time stamping and holdout reservation (3-6 months reserved for OOS)
- Label construction: triple-barrier (AFML Ch. 3), meta-labeling scaffold, standard return labels
- Validation stack: purged K-fold CV with embargo, CPCV, Deflated Sharpe Ratio, Harvey-Liu Haircut Sharpe, ridge/elastic-net baseline
- Backtesting engine: transaction-cost-aware P&L, full reporting suite (IC, Sharpe, Sortino, hit rate, turnover, max drawdown), SHAP integration
- Smoke test on toy problem before proceeding
- Tooling: mlfinlab, alphalens, pyfolio, shap, MLflow/W&B

**Phase 2: Project 1 Core — Risk as Alpha (Weeks 6-12)**
- Five signal families from risk cubes:
  1. VaR dynamics (firm-level delta VaR, component VaR, rate-of-change)
  2. Factor concentration (Herfindahl index, top-3 factor share) — **priority**
  3. Scenario P&L (rank, dispersion, worst-case identity)
  4. VaR utilization (usage/limit %, rate of change) — **priority**
  5. Cross-asset flow (component VaR shifts between asset classes)
- Priority order: VaR utilization and factor concentration first (strongest theory: Coval-Stafford fire sales, He-Kelly-Manela crowding)
- Four prediction targets: VIX innovations, asset-class drawdowns, cross-asset momentum reversals, realized volatility
- Modeling: ridge baseline first, then LightGBM; SHAP + MDA stability; confound checks against public factors; panel structure with asset-class fixed effects
- Key risk: sample size (~1,250 daily obs for 5yr). Track every experiment for DSR. Prefer theory-motivated features.

**Phase 3: Checkpoint & Decision (Week 13)**
- Continue Project 1 if: IC > 0 after purged CV, GBM beats ridge, DSR > 0, MDA stable
- Pivot to Project 2 if: all flat/unstable, GBM ≤ ridge, DSR kills Sharpe
- Hybrid if: partial success — keep working features, add Greeks as additional inputs into same model
- Deliverable: 1-2 page memo documenting results and decision rationale

**Phase 4A: Deepen Project 1 (Weeks 14-17) — if checkpoint passes**
- Regime overlay: GMM on macro features (Two Sigma template), 3-4 regimes, decompose signal by regime
- Cross-asset panel extension: within-class vs. cross-prediction, He-Kelly-Manela single-kernel test
- Capacity & transaction cost sensitivity: breakeven cost level, turnover analysis
- Initiate compliance review (Week 16-17)

**Phase 4B: Pivot to Book-Gamma (Weeks 14-17) — if checkpoint fails**
- Aggregate dealer gamma/vega/vanna/charm from SecDB book Greeks across rates futures, G10 FX, credit indices
- Test Baltussen-Da-Lammers-Martens (2021): net gamma sign predicts last-30-min intraday momentum
- SecDB advantage: real book-level sign (public GEX ~30% wrong)
- Muravyev-Pearson-Pollet (2022) caveat: control for short interest if touching equities

**Phase 5: Consolidation & Presentation (Weeks 18-20)**
- Walk-forward OOS test on reserved holdout (one shot, no iteration)
- Rolling-window stability check
- Final DSR and Haircut Sharpe on all reported numbers
- Research report: hypothesis, data, methodology, results (one chart per claim, ridge alongside GBM), negatives, capacity, next steps
- Presentation: frame as causal hypothesis testing, lead with IC/Sharpe, prepare for desk Q&A

### Risk Register
| Risk | Mitigation |
|---|---|
| Signal doesn't exist | Week 13 checkpoint; Project 2 fallback |
| Sample size too small | Panel structure; theory-motivated features |
| Overfitting / data snooping | DSR; experiment tracking; ridge baseline; purged CV |
| Entitlements block data | Phase 0 audit |
| Feature importance unstable | MDA across folds |
| Transaction costs eat signal | Cost-aware backtesting from day 1 |
| Risk-model methodology breaks | Interview risk team about VaR model changes |
| Compliance review delays | Start review Week 16 |
| Sponsor unavailability | Backup reviewer identified Phase 0 |
| Package restrictions | Package audit Phase 0 |

---

## Implementation Plan Summary

**File:** `docs/superpowers/plans/2026-04-23-risk-as-alpha-plan.md`

24 tasks across 7 chunks, with TDD (test-first) discipline and frequent commits.

### Chunk 1: Phase 0 — Pitch & Alignment (Weeks 1-2)
| Task | What It Does |
|---|---|
| Task 1: Environment & Package Audit | Confirm Python env, test package availability, document compute constraints |
| Task 2: Data Access Audit | Enumerate accessible risk cube nodes, pull sample data, check data gate, investigate risk-model methodology changes |
| Task 3: Pitch Document | Draft 1-2 page pitch, present to sponsor, get sign-off |
| Task 4: Holdout Reservation & Experiment Log | Reserve 3-6 months OOS, initialize experiment tracking CSV |

### Chunk 2: Phase 1 — Shared Infrastructure (Weeks 3-5)
| Task | What It Does |
|---|---|
| Task 5: Data Pipeline Module | `src/data/pipeline.py`, `src/data/point_in_time.py` — point-in-time stamping, holdout enforcement, SecDB bridge |
| Task 6: Label Construction | `src/labels/triple_barrier.py`, `src/labels/returns.py`, `src/labels/meta_labeling.py` |
| Task 7: Validation Stack | `src/validation/purged_cv.py`, `src/validation/cpcv.py`, `src/validation/deflated_sharpe.py`, `src/validation/haircut_sharpe.py`, `src/validation/baseline.py` |
| Task 8: Backtesting Engine | `src/backtest/engine.py`, `src/backtest/metrics.py`, `src/backtest/reporting.py` — ridge + LightGBM, transaction costs, SHAP, charts |
| Task 9: Experiment Tracker | `src/tracking/tracker.py` — logs every experiment for honest DSR trial counting |
| Task 10: Smoke Test | `notebooks/01_smoke_test.ipynb` — validate full stack on synthetic data before Phase 2 |

### Chunk 3: Phase 2 — Project 1 Core (Weeks 6-12)
| Task | What It Does |
|---|---|
| Task 11: Priority Features | `src/features/var_utilization.py`, `src/features/factor_concentration.py` — Herfindahl, VaR util %, z-scores |
| Task 12: Remaining Features | `src/features/var_dynamics.py`, `src/features/scenario_pnl.py`, `src/features/cross_asset_flow.py` |
| Task 13: Target Construction | `src/targets/targets.py` — VIX innovation, drawdown, realized vol, momentum reversal |
| Task 14: Signal Testing — Priority | `notebooks/02-03` — test VaR utilization and factor concentration against all targets, SHAP, document |
| Task 15: Signal Testing — Combined | `notebooks/04-05` — test remaining families, confound checks, combined model, panel structure |

### Chunk 4: Phase 3 — Checkpoint (Week 13)
| Task | What It Does |
|---|---|
| Task 16: Checkpoint Assessment | Compile results, apply decision criteria, write memo, present to sponsor |

### Chunk 5: Phase 4A — Deepen Project 1 (Weeks 14-17)
| Task | What It Does |
|---|---|
| Task 17: Regime Overlay | `src/regime/gmm_regime.py` — GMM on macro features, decompose signal by regime |
| Task 18: Cross-Asset Panel | `notebooks/07` — within-class vs. cross-prediction, panel regression, He-Kelly-Manela test |
| Task 19: Capacity & Costs | `notebooks/08` — Sharpe vs. cost curve, turnover, capacity estimates |
| Task 19B: Compliance Review | Initiate compliance review at Week 16-17 |

### Chunk 6: Phase 4B — Book-Gamma Pivot (Weeks 14-17)
| Task | What It Does |
|---|---|
| Task 20: Greeks Features | `src/features/dealer_greeks.py` — aggregate gamma/vega/vanna/charm from SecDB |
| Task 21: Book-Gamma Signal | `notebooks/09` — replicate Baltussen et al. with real book data, cross-instrument tests |

### Chunk 7: Phase 5 — Consolidation (Weeks 18-20)
| Task | What It Does |
|---|---|
| Task 22: Walk-Forward OOS | `notebooks/10` — unfreeze holdout, one-shot test, rolling stability, final DSR/Haircut |
| Task 23: Research Report | `deliverables/research_report.md` — full desk-ready report with charts |
| Task 24: Presentation | `deliverables/presentation_outline.md` — one slide per claim, Q&A prep, dry run |

### Project Directory Structure
```
ML/
├── CLAUDE.md
├── Signal Discovery.pdf
├── data/                          # data audit docs and holdout config
├── deliverables/                  # pitch, checkpoint memo, report, presentation
├── docs/superpowers/specs/        # design spec
├── docs/superpowers/plans/        # implementation plan
├── environment/                   # package audit, requirements.txt
├── experiments/                   # experiment log CSV
├── notebooks/                     # 00-10, one per analysis step
├── src/
│   ├── backtest/                  # engine, metrics, reporting
│   ├── data/                      # pipeline, point-in-time
│   ├── features/                  # var_utilization, factor_concentration, var_dynamics,
│   │                              #   scenario_pnl, cross_asset_flow, dealer_greeks
│   ├── labels/                    # triple_barrier, returns, meta_labeling
│   ├── regime/                    # gmm_regime
│   ├── targets/                   # targets
│   ├── tracking/                  # experiment tracker
│   └── validation/                # purged_cv, cpcv, deflated_sharpe, haircut_sharpe, baseline
└── tests/                         # mirrors src/ structure
```

---

## Key Literature (Quick Reference)

### Essential
- Lopez de Prado, *AFML* (2018) — validation bible
- Gu, Kelly, Xiu (2020 RFS) — canonical ML horse-race
- Kelly, Xiu (2023 NBER WP 31502) — ML-finance survey
- Bailey, Lopez de Prado (2014) — Deflated Sharpe Ratio
- Harvey, Liu (2015) — Haircut Sharpe

### Project 1 Theory
- He, Krishnamurthy (2013 AER) — intermediary asset pricing
- Adrian, Etula, Muir (2014 JF) — intermediary-leverage SDF
- He, Kelly, Manela (2017 JFE) — single kernel across asset classes
- Adrian, Shin (2010 JFI) — dealer repos forecast VIX
- Coval, Stafford (2007 JFE) — forced selling → reversals

### Project 2 Theory (if pivot)
- Baltussen, Da, Lammers, Martens (2021 JFE) — dealer gamma → intraday momentum
- Barbon, Buraschi (2021) — gamma fragility

### Critical Caveats
- Muravyev, Pearson, Pollet (2022) — IVS/skew proxy for borrow fees; control for short interest
- Published signals decay 30-50% post-publication (McLean-Pontiff 2016)
- Asness et al. (2017) — factor timing net of exposures often subtracts value
- Bailey-Borwein-LdP (2014) — ~45 trials exhaust Sharpe 1.0 on 5yr data

---

## Conventions
- This is a planning repo — markdown files and infrastructure code
- Use `docs/superpowers/specs/` for formal design documents
- Use `docs/superpowers/plans/` for implementation plans
- Notes and scratch thinking can go anywhere at the top level
- All code follows TDD: failing test → implement → pass → commit
- Every experiment logged to `experiments/experiment_log.csv` for honest DSR
