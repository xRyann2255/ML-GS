# Codebase Documentation Audit -- 2026-05-12

**Input:** `notes/ml_vol_forecasting_docs.md` (1988 lines, 22 sections + 8 appendices)
**Methodology:** Three parallel research agents (math verification, architecture + ML practices, ensemble/stacking research) with synthesis. Cross-referenced against vol-project-ref guide, ~80 bibliography entries, 19 project papers, and independent web research.

---

## Executive Summary: Top 5 Actions for the Next 16 Weeks

### 1. Fix CV purge gap enforcement and QLIKE log-space sign convention (Week 5)
The CV splitter does not enforce `purge_gap >= max(horizons)`, causing silent data leakage for h=22. The QLIKE log-space formula may have a sign flip relative to Patton (2011). Both are correctness bugs that invalidate results if left unfixed. **See: Pillar 1 Finding 6, Pillar 2 Finding 2.4.**

### 2. Extend FeatureLayer protocol and fix P0 debt (Week 5-6)
The `FeatureLayer.compute(daily_data)` signature cannot serve Layers 2-5 which need external data sources. Add a `context` keyword argument. Also fix shared `safe_log` and extract the duplicated log/lag/rolling pattern. These four items (protocol, safe_log, dedup, purge gap) are the prerequisites for all subsequent implementation. **See: Pillar 2 Finding 2.1, Pillar 5 revised table.**

### 3. Build the QLIKE tournament pipeline (Weeks 6-10)
The most important deliverable. Critical path: LightGBM with custom QLIKE objective (1-2 sessions) + walk-forward evaluation loop (1-2 sessions) + Diebold-Mariano tests + tournament_table (2-3 sessions). Use an 8-symbol development universe for iteration speed, full 34 for the final run. Add SQLite experiment tracking alongside LightGBM for HP tuning. **See: Pillar 4 Finding 2.1.**

### 4. Implement Layer 2 options features and tradeable signal (Weeks 8-12)
Single-stock IV is confirmed unblocked via EDRVOL_PERCENT. Layer 2 (VRP, skew, term slope, butterfly) feeds both the LightGBM feature set and the IV-RV gap signal. Economic value functions (P&L, Sharpe, drawdown) are 2-3 sessions. Start Layer 2 in parallel with tournament work. **See: Pillar 4 Finding 2.2, Pillar 6 Finding 3.3.**

### 5. Use prediction blending at all horizons, not stacking (Weeks 13-16)
The doc's "stacking at h=1/h=5, blending at h=22" is not supported by evidence. Prediction blending (inverse-QLIKE weighted or linear blend) is simpler, more robust, and avoids the gradient-isolation problem. The LSTM branch is a stretch goal; minimum viable ensemble is simple blend of HAR-best + LightGBM. **See: Pillar 4 Finding 1.7.**

---

## Pillar 1: Mathematical Correctness

16 formulas checked across Sections 12-14, 17, and 19. Cross-referenced against vol-project-ref guide chapters 3, 4, 13 and original papers.

### 1.1 Semivariance indicator uses strict inequality instead of >= 0
**Severity:** Important
**Doc reference:** Section 13, lines 849-850
**Details:** The doc defines RS+ with `1(r > 0)` and RS- with `1(r < 0)`, meaning zero returns are excluded from both semivariances (RS+ + RS- < RV when any return is exactly zero). Patton & Sheppard (2015) use `>= 0` for RS+ and `< 0` for RS-, as does the vol-project-ref guide (ch04, line 26). The doc's formulation violates the decomposition identity RV = RS+ + RS-.
**Recommendation:** Change to `1(r >= 0)` for RS+ in both the doc and the implementation code.

### 1.2 BNS jump test uses RQ instead of realized tripower quarticity (RTQ) in denominator
**Severity:** Important
**Doc reference:** Section 13, lines 871-877
**Details:** The `detect_jumps(rv, bpv, rq, ...)` function takes RQ in the denominator: `Z = (RV - BPV) / sqrt(theta * RQ / N)`. However, BNS (2006) Theorem 2 derives the asymptotic variance using RTQ, not RQ. RTQ is jump-robust while RQ is not -- using RQ in the presence of jumps inflates the denominator and reduces test power (conservative bias). The doc defines RTQ separately (lines 863-869) but never connects it to the jump test.
**Recommendation:** Either use RTQ in the denominator (correct per BNS 2006) or document that RQ is a deliberate finite-sample approximation with a note about power loss.

### 1.3 HARQ interaction term inconsistency in vol-project-ref guide
**Severity:** Important
**Doc reference:** Guide: `ch03-har-core.tex`, line 33 vs. line 53
**Details:** The guide's feature table (line 33) lists the interaction as `sqrt(RQ) * RV_d` -- dropping the log. The guide's own HARQ equation (line 53) correctly shows `sqrt(RQ) * log(RV_d)`. The codebase doc (Section 12, line 817) is correct. This is an internal inconsistency within the guide only.
**Recommendation:** Fix the guide table to read `sqrt(RQ) * log(RV_d)`.

### 1.4 Realized kernel formula missing absolute value on kernel argument
**Severity:** Minor
**Doc reference:** Section 14, lines 968-972
**Details:** The RK summation `k(h/(H+1))` sums from h = -H to H, producing negative arguments. The Parzen kernel is defined only for x >= 0. BNHLS (2008) specifies the kernel is even, evaluated at `|h|/(H+1)`.
**Recommendation:** Change to `k(|h|/(H+1))` in the formula.

### 1.5 TSRV n_bar is undefined
**Severity:** Minor
**Doc reference:** Section 14, lines 980-982
**Details:** The TSRV formula uses `n_bar/n` as the bias correction but never defines n_bar. Per Zhang (2005), n_bar = (n - K + 1)/K is the average subsample size.
**Recommendation:** Add the definition inline.

### 1.6 QLIKE log-space formula sign convention may be reversed
**Severity:** Important
**Doc reference:** Section 19, line 1304
**Details:** The doc defines log-space QLIKE as `mean(exp(y - y_hat) - (y - y_hat) - 1)`. Deriving from the variance-space formula with sigma^2 = exp(y), we get `exp(y_hat - y) - (y_hat - y) - 1`, which has the opposite sign inside the exp. Both are valid quasi-likelihood losses minimized at y = y_hat, but they penalize asymmetrically in opposite directions. The doc's formula does not correspond to the standard Patton (2011) QLIKE after log transformation.
**Recommendation:** Verify which convention the actual code implements. If the code should match Patton (2011), change to `mean(exp(y_hat - y) - (y_hat - y) - 1)`. If the current convention is intentional, document the departure.

### 1.7 Summary
**Correct (no issues):** RV, RQ scaling, BPV summation range, theta constant (~0.609), RTQ formula and mu_{4/3} constant, Lee-Mykland test and Gumbel threshold, signed jumps partitioning, realized skewness/kurtosis scaling, QLIKE variance-space formula, Duan retransformation, pre-averaged RV weights, HAR weekly/monthly averaging order (variance then log), shift(1) consistency, Section 12 vs 17 internal consistency.

---

## Pillar 2: Architecture Review

### 2.1 FeatureLayer protocol cannot serve Layers 2-5
**Severity:** Critical
**Doc reference:** Section 8, lines 297-299; Section 11, lines 575-587
**Details:** `FeatureLayer.compute(daily_data: pd.DataFrame) -> pd.DataFrame` assumes all inputs are in the RV panel. Layer 2 needs Marquee IV surface data, Layer 3 needs L2 depth, Layer 4 needs TSDB Treasury/FX/commodity data. None of these are in `daily_data`. Adding a `context: dict[str, pd.DataFrame] | None = None` keyword argument is cleanest: backward-compatible (Layers 0-1 ignore it), keeps data-fetching in the pipeline orchestrator, and avoids bloating the main DataFrame.
**Recommendation:** Extend to `compute(daily_data, *, context=None)`. P0 -- blocks all Layer 2-5 work.

### 2.2 VolModel protocol too narrow for sequence models
**Severity:** Important
**Doc reference:** Section 18, lines 1269-1286; Appendix E item 8
**Details:** `fit(X: pd.DataFrame, y: pd.Series)` cannot accept 3D LSTM input. A separate `SequenceModel` protocol with `fit(X: np.ndarray, y: np.ndarray)` is the cleanest solution -- explicit type contract, no Union types, HAR family untouched. The pipeline dispatches based on `isinstance` against the runtime-checkable protocol.
**Recommendation:** Define `SequenceModel` protocol. Correctly prioritized at P2 -- does not block Steps 1-3.

### 2.3 Pipeline cannot compose ensembles or stacking
**Severity:** Important
**Doc reference:** Section 10, lines 528-544; Section 18, lines 1289-1295
**Details:** `Pipeline.run()` trains ONE model. `ExperimentConfig.model` is singular. It cannot train multiple models, collect OOF predictions for a meta-learner, or represent a stacking config. However, a pragmatic approach works: run base models as separate experiments, then write a standalone blending script that reads saved predictions.
**Recommendation:** Keep pipeline single-model for Steps 1-3. At Step 5, either add `models: list[ModelConfig]` to config or write a standalone blend script. The standalone approach is faster and sufficient for the internship.

### 2.4 CV splitters do not enforce horizon-aware purge gaps
**Severity:** Critical
**Doc reference:** Appendix B, lines 1547-1556; Section 9, lines 335-340
**Details:** `CVConfig.purge_gap` is a single integer (default 5). For h=22, purge gap must be >= 22 to prevent label leakage. Nothing enforces this. A user setting `purge_gap: 5` with `horizons: [1, 5, 22]` gets contaminated splits for h=22 -- silently inflated results.
**Recommendation:** Add validation: `purge_gap = max(purge_gap, h)` dynamically per horizon inside the training loop. P0 correctness bug.

### 2.5 Experiment tracking insufficient at scale
**Severity:** Important
**Doc reference:** Section 10, lines 547-571
**Details:** Config YAML + metrics.json per experiment directory cannot support cross-experiment queries. With 714 combinations (7 x 34 x 3), manual comparison is impractical. A lightweight SQLite experiment log (one row per run with config hash, hyperparameters, metrics, timestamp) is the right middle ground for GS constraints.
**Recommendation:** Add `workspace/experiments.db` with an `experiments` table. Extend `save_experiment_results()` to insert a row. Add `vol run compare` CLI command. Build alongside LightGBM implementation. ~100 lines of code.

### 2.6 Reproducibility gaps beyond seeds
**Severity:** Minor
**Doc reference:** Section 9, lines 328-354
**Details:** Seed + YAML covers model randomness but not: feature layer execution order (if non-deterministic), library version drift, data cache staleness. Config snapshots don't record `pip freeze` or cache file hashes.
**Recommendation:** Log `uv pip list` output alongside config.yaml in experiment directories. Document that feature layer order matters.

### 2.7 Hyperparameter search not integrated
**Severity:** Minor
**Doc reference:** Section 18, line 1280
**Details:** Optuna mentioned for LightGBM but not wired into pipeline or config. When implementing LightGBM, use Optuna's native SQLite storage to persist trials in the same `experiments.db`.
**Recommendation:** Add `optuna_config` section to ExperimentConfig. Share SQLite DB.

### 2.8 Gap from best-practice experiment flow
**Severity:** Minor
**Doc reference:** Sections 9-10
**Details:** Best practice: hypothesis -> config -> run -> evaluate -> compare -> decide. Current system covers config -> run -> evaluate. Missing: hypothesis recording, automated comparison with previous best, decision log.
**Recommendation:** Add `hypothesis` field to ExperimentConfig (free text). Maintain a decisions log in notes/. The `vol run compare` command should highlight current best.

---

## Pillar 3: Wrong Directions

### 3.1 34-symbol universe should use a dev subset
**Severity:** Important
**Doc reference:** Appendix C, lines 1563-1571
**Details:** Running all 34 symbols for every experiment during development is wasteful. A focused 8-symbol dev universe (SPY, AAPL, MSFT, NVDA, XOM, JPM, IWM, ES) covers diverse sectors and asset types. Use full 34 only for the final tournament.
**Recommendation:** Add `DEV_UNIVERSE` constant (8 symbols). Use as default during development. Cuts iteration time ~75%.

### 3.2 Stubbed modules: keep API contracts, defer implementation
**Severity:** Minor
**Doc reference:** Section 18, lines 1275-1295; Section 20, lines 1336-1378
**Details:** TCN model, 6 HTML report stubs, 8 visualization stubs. The API contracts (signatures, docstrings) are useful architectural documentation. The NotImplementedError bodies are harmless. The visualization/reporting infrastructure is over-engineered for the actual presentation need -- 3-4 targeted matplotlib functions in a notebook suffice.
**Recommendation:** Keep stubs. Do not implement the full reporting pipeline. Write targeted plot functions when results exist.

### 3.3 Rich progress display and Jinja2 reporting
**Severity:** Minor
**Doc reference:** Section 10, lines 512-519
**Details:** Rich progress is essential for long pipeline runs. Jinja2 HTML reporting is premature but harmless as a stub. Given the GS internship has a final presentation, polished reporting is a legitimate future deliverable.
**Recommendation:** Keep Rich progress. Defer HTML reporting until after Step 3.

### 3.4 LSTM/TCN for one symbol (E-mini)
**Severity:** Minor
**Doc reference:** Section 18, lines 1282-1286
**Details:** Only ES has L2 depth. The LSTM branch is correctly scoped as an independent experiment ("can L2 depth predict short-term vol for futures?"), not integrated into the tabular pipeline for all 34 symbols.
**Recommendation:** Correctly scoped. Treat as an independent experiment. If results are weak, drop and focus on tabular ensemble.

---

## Pillar 4: Missing Pieces

### 4.1 QLIKE tournament is 5-7 sessions from current state
**Severity:** Critical
**Doc reference:** Section 19, lines 1314-1321; Appendix A
**Details:** Critical path: LightGBM with QLIKE objective (1-2 sessions) + walk-forward evaluation loop (1-2 sessions) + DM tests + tournament_table (2-3 sessions). MCS (block bootstrap, 10K iterations) is a stretch goal. Minimum viable: HAR baselines + LightGBM + DM pairwise tests.
**Recommendation:** Start here. This is the single most important deliverable.

### 4.2 Tradeable signal is 4-6 sessions, depends on tournament
**Severity:** Critical
**Doc reference:** Section 19, lines 1323-1332
**Details:** Requires: Layer 2 options features (2-3 sessions, unblocked by EDRVOL_PERCENT resolution) + economic_value.py functions (2-3 sessions). Can only produce signal after having working RV forecasts.
**Recommendation:** Start Layer 2 in parallel with tournament work. Implement economic value functions after tournament pipeline is working.

### 4.3 Ensemble strategy: blend at all horizons, not stacking

**Severity:** Critical
**Doc reference:** Section 22, lines 1498-1503; Ch. 11 (ensemble.tex); Ch. 10 (lstm-intraday.tex)

**Details:** The doc's "stacking at h=1/h=5, blending at h=22" recommendation has three problems:

**The internal contradiction:** The doc (Section 22) says stack at h=1/h=5. Ch. 11 (ensemble guide) says "Blend Predictions, Not Features" universally, with a warning box explicitly titled "Do Not Stack Features." Ch. 10 hedges, saying "both should be compared." These three sources cannot all be the project plan.

**The evidence from internal papers:**
- Christensen, Siggaard, Veliyev (2023): ML gains over HAR *increase* with forecast horizon. This means the LSTM branch's marginal value is lowest at h=1 (where tabular features already capture most signal from daily autocorrelation) and highest at longer horizons.
- Bucci (2020): Forecast *combinations* outperform individual models across horizons.
- Fed (2025): ML vs. linear gaps are horizon-dependent, clearest at intermediate to long horizons.
- Optiver Kaggle (2021): Top solutions used prediction-level blending (weighted average), not feature stacking. Short-horizon task where hand-crafted features captured most signal.

**The evidence from independent research (2023-2026):**
- At h=1, signal-to-noise is highest and model errors are most correlated (all track strong daily autocorrelation). Blending's variance-reduction benefit is modest but stacking risks overfitting redundant information.
- At h=22, overfitting risk is highest (smallest effective sample size after walk-forward splitting). Simple averaging is the most robust combiner.
- No paper demonstrates feature stacking beating prediction blending at h=22 for RV.
- The gradient-isolation problem (Ch. 11's warning) is real: LightGBM cannot back-propagate into the LSTM, so embeddings are never optimized for the tabular objective.

**Per-horizon recommendation:**

| Horizon | Strategy | Method | Rationale |
|---------|----------|--------|-----------|
| h=1 | Prediction blending | Inverse-QLIKE weighted | Tabular features dominate; stacking risks overfitting redundant info |
| h=5 | Prediction blending | Linear blend (constrained optimization) | LSTM contribution rises but not enough to justify stacking complexity |
| h=22 | Prediction blending | Simple average or inverse-QLIKE | Overfitting risk highest; simple averaging most robust |

**The LSTM embedding question:** If the LSTM branch is pursued, use its scalar point forecast as a single extra LightGBM feature rather than high-dimensional embeddings. This is a degenerate "embedding" of dimension 1 that avoids all stability issues. Default embedding dimensionality: 32 if richer embeddings are needed.

**Minimum viable ensemble:** Simple average or inverse-QLIKE weighted blend of HAR-best + LightGBM. Skip the LSTM branch entirely if time is short.

**Recommendation:** Revise the doc to "prediction blending at all horizons." Resolve the Ch. 10/11/Section 22 contradiction. The LSTM branch is a stretch goal.

### 4.4 Visualization needs are simpler than stubbed
**Severity:** Important
**Doc reference:** Section 20, lines 1336-1378; Appendix A, lines 1541-1542
**Details:** For the presentation, you need: QLIKE comparison tables (pandas formatting), forecast vs. actual time-series plot, P&L equity curve, feature importance bar chart (LightGBM built-in). The 8 stubbed visualization functions and 7 stubbed report renderers are not needed.
**Recommendation:** Write 3-4 targeted matplotlib functions when results exist. Do not implement the full reporting pipeline.

### 4.5 Timeline feasibility (16 weeks remaining)

**Critical path:**

| Weeks | Phase | Key Deliverables |
|-------|-------|-----------------|
| 5-6 | P0 fixes + LightGBM | Fix purge gap, QLIKE sign, protocol extension, safe_log. Implement LightGBM with QLIKE objective. Walk-forward evaluation loop. |
| 7-8 | Layer 2 + Statistical tests | Options features (VRP, skew, term slope, butterfly). DM test, tournament_table. SQLite experiment tracking. |
| 9-10 | QLIKE tournament | Full tournament: 7 HAR + LightGBM, 3 horizons, dev universe. DM pairwise tests. |
| 11-12 | Tradeable signal | Economic value functions. IV-RV gap signal. P&L backtest with Sharpe/drawdown. |
| 13-14 | Stretch: LSTM + regime analysis | LSTM branch (E-mini only). Regime-conditional QLIKE. Full 34-symbol tournament run. |
| 15-16 | Ensemble + presentation | Prediction blending. MCS (if time). Final figures and presentation assembly. |

**Minimum viable at week 15:** QLIKE tournament (7 HAR + LightGBM, DM tests) + IV-RV gap signal with Sharpe/drawdown + 4-5 key figures. No LSTM, no MCS, no HTML reporting.

**Stretch goals by impact-per-effort:**
1. Regime-conditional QLIKE evaluation (low effort, high insight)
2. MCS implementation (moderate effort, high presentation value)
3. LSTM scalar forecast as extra LightGBM feature (high effort, moderate gain)
4. Layer 4 cross-asset features (moderate effort, moderate gain)
5. Full HTML reporting pipeline (high effort, low marginal value)

---

## Pillar 5: Architecture Debt Triage

Revised priority table incorporating all review findings:

| # | Issue | Original | Revised | Rationale |
|---|-------|----------|---------|-----------|
| 1 | No shared `safe_log` | P0 | **P0** | Unchanged. Blocks real-data work on illiquid symbols. |
| 2 | Duplicated log/lag/rolling pattern | P0 | **P0** | Unchanged. Every new layer copies this. Extract before Layer 2. |
| 9 | Inconsistent zero-floor protection | P2 | **P0** | Promoted. Same root cause as item 1; same fix addresses both. |
| **NEW** | FeatureLayer protocol needs context arg | -- | **P0** | Discovered in Pillar 2 Finding 2.1. Blocks all Layer 2-5 work. |
| **NEW** | CV purge_gap not enforced >= horizon | -- | **P0** | Discovered in Pillar 2 Finding 2.4. Silent data leakage for h=22. |
| 3 | 5 dead re-export shims | P1 | **P1** | Unchanged. |
| 4 | Dual-path constant access | P1 | **P1** | Unchanged. |
| 7 | Monolithic `__main__.py` | P1 | **P1** | Fix when adding ensemble or new stages. |
| **NEW** | SQLite experiment tracking | -- | **P1** | Discovered in Pillar 2 Finding 2.5. Important at Step 2 (LightGBM HP tuning). |
| 5 | Duplicated test files | P1 | **P2** | Demoted. Low impact on correctness. |
| 6 | Duplicated `_make_synthetic_ticks` | P1 | **P2** | Demoted. Schema is stable. |
| 8 | VolModel protocol too narrow | P2 | **P2** | Unchanged. Blocks Step 4 only (LSTM). |
| 10 | Loose top-level scripts | P3 | **P3** | Unchanged. |
| 11 | Stale `__pycache__` | P3 | **P3** | Unchanged. |
| 12 | `data/measures.py` facade | P3 | **P3** | Working as designed. |
| 13 | CV splitter duplication | P3 | **P3** | Unchanged. |

**Net changes:** 2 items promoted (items 9, NEW purge gap). 2 items demoted (items 5, 6). 3 new items added (FeatureLayer context, purge gap enforcement, SQLite tracking). Total: 16 items.

**P0 items (fix before Phase 6):** 5 items. Estimated total effort: 2-3 sessions.

---

## Pillar 6: Data Pipeline Gaps

### 6.1 Gap triage

| Data Gap | Classification | Impact |
|----------|---------------|--------|
| Broker trade attribution | Irrelevant | Structurally impossible. Volume imbalance workaround adequate. |
| L2 depth for equities | Nice to have | LSTM is E-mini only by design. No impact. |
| Pre-computed VWAP/spread | Nice to have | Already computed manually in `compute_daily_rv_from_ticks`. |
| Micro E-mini (MES) | Irrelevant | Full E-mini (ES) is correct instrument. |
| Fed Funds rate | Nice to have | 2Y Treasury proxy is standard. Affects 1 Layer 4 feature. |
| EUR/USD, GBP/USD | Nice to have | Marquee FXIVOL works for EUR/USD. Only GBP/USD truly missing (low priority). |
| Dollar Index (DXY) | Nice to have | Computable from component pairs. |
| Generic front futures | Nice to have | Manual roll is annoying but straightforward. |
| **Single-stock IV** | **RESOLVED** | **EDRVOL_PERCENT with ric parameter works. Unblocks Layer 2 for all 34 symbols.** |
| Earnings calendar | Nice to have | ~240 rows of data entry. Defer to weeks 13-14 as stretch goal. |

### 6.2 No data gaps block any deliverable
**Severity:** Minor (positive finding)
**Doc reference:** Appendix F, lines 1862-1876
**Details:** Every gap has a working workaround or is on a non-critical feature. The single-stock IV resolution is the most impactful finding -- it fully unblocks Layer 2 options features for all 34 symbols, which is the foundation for the tradeable signal deliverable.
**Recommendation:** Implement Layer 2 with confidence. Implement Layer 4 cross-asset features with workarounds for missing data. Defer earnings calendar to stretch goals.

---

## Appendix: Validated Items

These aspects of the codebase documentation are confirmed solid and should not be changed:

**Mathematical foundations (10 of 16 formulas correct with no issues):**
- RV, RQ definitions and scaling conventions
- BPV summation formula and range
- Theta constant (~0.609) for BNS test
- RTQ formula and mu_{4/3} constant
- Lee-Mykland test and Gumbel threshold
- Signed jumps partitioning
- Realized skewness/kurtosis scaling
- QLIKE variance-space formula
- Duan retransformation
- HAR feature construction order (variance then log) and shift(1) consistency

**Software architecture:**
- Registry + decorator pattern for models and feature layers
- Protocol definitions (`VolModel`, `FeatureLayer`) as runtime-checkable structural typing
- Constants centralization in one file
- Feature layer consistency (`compute(daily_data) -> DataFrame`)
- HAR family `_BaseHAR` template method pattern for 7 variants
- CLI/pipeline separation with composable ingest/train/evaluate steps
- Persistence layer with structured experiment output and config snapshots
- CWD-independent path resolution
- Lazy import pattern for CLI startup speed

**Agentic workflow framework:**
- 16 personas, 46 skills, 16 workflows, 48 slash commands
- Mentor-directed infrastructure for project handoff. Correctly scoped.

**Data pipeline:**
- Chunk Store integration with exponential backoff, batch grouping, parallel fetch
- E-mini contract roll logic
- Trading calendar with NYSE holiday handling
- RV panel builder with incremental caching and checkpoint resumability
- Resampling with previous-tick interpolation

---

*Audit conducted 2026-05-12. Three parallel research agents with synthesis.*
