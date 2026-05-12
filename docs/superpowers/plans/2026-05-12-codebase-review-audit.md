# Codebase Documentation Audit -- Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a severity-rated technical review of `notes/ml_vol_forecasting_docs.md` across 6 pillars, with a Top 5 Actions executive summary that feeds Sessions 2 and 3.

**Architecture:** Three parallel research agents (math, architecture, ensemble research) produce raw findings. A synthesis task merges them into a single output file at `notes/review-codebase-audit.md` with consistent formatting and the executive summary.

**Tech Stack:** Markdown output. Research uses repo files (papers, bibliography, vol-project-ref chapters), plus web search for the ensemble/stacking deep-dive.

---

## Chunk 1: Parallel Research Agents

Three independent research tasks that can run simultaneously. Each agent produces raw findings in a structured format (severity, doc reference, details, recommendation) that the synthesis task will merge.

### Task 1: Mathematical Correctness (Pillar 1)

**Files to read:**
- `notes/ml_vol_forecasting_docs.md` -- Sections 12-14, 17, 19 (all formulas)
- `guides/vol-project-ref/chapters/ch03-har-core.tex` -- HAR/HARQ formulas
- `guides/vol-project-ref/chapters/ch04-asymmetry-jumps.tex` -- BPV, BNS, semivariances
- `guides/vol-project-ref/chapters/ch05-options-implied.tex` -- VRP, skew
- `guides/vol-project-ref/chapters/ch13-evaluation.tex` -- QLIKE formula
- `reference/bibliography.md` -- Paper citations for cross-reference
- `reference/project-papers/*.pdf` -- Original papers (where needed for ambiguous formulas)

**Output:** Raw findings for Pillar 1 section of the audit document.

- [ ] **Step 1: Read all formulas in the codebase doc**

Read `notes/ml_vol_forecasting_docs.md` sections 12 (HAR Core), 13 (Asymmetric Volatility), 14 (Noise-Robust), 17 (Raw Data Sources), and 19 (Evaluation Suite). Extract every mathematical formula with its doc line number.

- [ ] **Step 2: Cross-reference Layer 0 formulas against papers**

Verify against Corsi 2009, Bollerslev et al. 2016, Barndorff-Nielsen-Shephard 2002:
- RV = sum(r_i^2) -- check scaling convention (some papers use 1/N normalization)
- RQ = (N/3) * sum(r_i^4) -- check the N/3 prefactor against BNS 2002 (some papers use N * mu_1^{-4})
- HAR feature construction: weekly/monthly averaging in variance space before log transform (Corsi 2009 Section 2)
- HARQ interaction term: sqrt(RQ) * log(RV) (Bollerslev et al. 2016, Equation 4)

Also cross-check against `guides/vol-project-ref/chapters/ch03-har-core.tex` for consistency.

- [ ] **Step 3: Cross-reference Layer 1 formulas against papers**

Verify against Barndorff-Nielsen-Shephard 2004/2006, Lee-Mykland 2008, Patton-Sheppard 2015, Amaya et al. 2015:
- BPV = (pi/2) * sum(|r_i| * |r_{i-1}|) -- check summation index range (i=2 to N)
- BNS z-stat: (RV - BPV) / sqrt(theta * RQ / N) where theta = (pi^2/4 + pi - 5) -- verify theta numerically (~0.609)
- Realized tripower quarticity: N * mu_{4/3}^{-3} * sum(|r_i|^{4/3} * |r_{i-1}|^{4/3} * |r_{i-2}|^{4/3}) -- verify mu_{4/3} constant
- Lee-Mykland: local BPV window, Gumbel threshold formula, default window=156
- Semivariances: RS+ = sum(r_i^2 * 1(r_i > 0)) -- check if Patton-Sheppard uses > or >= for zero returns
- Signed jumps: verify partitioning of Lee-Mykland detected jumps into J+ = sum(r_i^2 * 1(r_i > 0, jump_i)) and J- components per Patton-Sheppard 2015. This is distinct from both the raw Lee-Mykland test and the semivariances.
- Realized skewness/kurtosis: verify scaling factors sqrt(N) and N against Amaya et al. 2015

Also cross-check against `guides/vol-project-ref/chapters/ch04-asymmetry-jumps.tex`.

- [ ] **Step 4: Cross-reference noise-robust estimator formulas**

Verify against Barndorff-Nielsen et al. 2008, Zhang 2005, Jacod et al. 2009:
- Realized kernel: Parzen kernel function definition, bandwidth H proportional to n^{3/5}, autocovariance formula
- TSRV: RV_slow - (n_bar/n) * RV_all -- check subsampling notation
- Pre-averaged RV: triangular weight function g(x) = min(x, 1-x), block length L proportional to sqrt(n)
- Noise gap: (RK - RV_5min) / RV_5min -- check sign convention

- [ ] **Step 5: Cross-reference evaluation formulas**

Verify against Patton 2011, Duan 1995:
- QLIKE variance-space: mean(sigma_hat^2 / sigma^2 - log(sigma_hat^2 / sigma^2) - 1)
- QLIKE log-space: the doc says mean(exp(y - y_hat) - (y - y_hat) - 1) -- verify this is the correct transformation from variance-space
- Duan retransformation: exp(y_hat + sigma^2/2) -- verify this is the smearing estimator, check if sigma^2 is residual variance or prediction variance

Also cross-check QLIKE formula against `guides/vol-project-ref/chapters/ch13-evaluation.tex`.

- [ ] **Step 6: Check for internal consistency**

Compare formulas between:
- Section 12 vs. Section 17 (both define RV, RQ -- are they identical?)
- Section 13 vs. Section 17 (both define Layer 1 features)
- Codebase doc vs. vol-project-ref guide chapters (any notation differences?)
- Check that all shifted features use `.shift(1)` consistently (no look-ahead)

- [ ] **Step 7: Write Pillar 1 findings**

For each issue found, write a finding with: severity (Critical/Important/Minor), doc section + line range, details with paper citation, and specific recommendation.

---

### Task 2: Architecture + ML Practices + Wrong Directions + Debt Triage (Pillars 2, 3, 5)

**Files to read:**
- `notes/ml_vol_forecasting_docs.md` -- Sections 8-10 (package architecture, config, CLI pipeline), 18 (models), Appendix E (debt register)
- `guides/vol-project-ref/chapters/ch14-complete-pipeline.tex` -- Pipeline architecture in the guide

**Output:** Raw findings for Pillars 2, 3, and 5 sections of the audit document.

- [ ] **Step 1: Evaluate Registry + Protocol pattern scalability**

Read Section 8 (package architecture). Assess:
- Does `FeatureLayer.compute(daily_data: pd.DataFrame) -> pd.DataFrame` work for Layer 2 (options-implied)? Layer 2 needs Marquee IV surface data that isn't in the daily RV panel. Options: (a) Layer 2 fetches its own data internally, (b) the pipeline pre-fetches and passes it in `daily_data`, (c) `compute()` signature needs an additional data argument.
- Same question for Layer 4 (cross-asset) which needs TSDB Treasury/FX/commodity data.
- Is the registry `dict[str, type]` sufficient, or should it store metadata (required columns, data sources)?

- [ ] **Step 2: Evaluate VolModel protocol for sequence models**

Read Section 18 (models) and debt item #8. Assess:
- The `fit(X: pd.DataFrame, y: pd.Series)` signature assumes 2D tabular input. LSTM needs 3D `np.ndarray` (samples x timesteps x features).
- Options: (a) Protocol union type `X: pd.DataFrame | np.ndarray`, (b) separate `SequenceModel` protocol, (c) wrapper that reshapes DataFrame to 3D.
- Which approach minimizes disruption to existing HAR models while enabling LSTM/TCN?
- Does the `predict()` method have the same problem?

- [ ] **Step 3: Evaluate pipeline composability for ensemble/stacking**

Read Section 10 (pipeline). Assess:
- `Pipeline.run()` iterates feature layers then trains one model. Can it handle:
  - Two-stage stacking (LSTM produces embeddings, LightGBM consumes them)?
  - Ensemble (multiple models trained independently, predictions blended)?
- Does `ExperimentConfig` support specifying multiple models or a stacking configuration?
- What architectural changes are needed for the ensemble/stacking workflow?

- [ ] **Step 4: Evaluate CV splitter correctness for multi-horizon**

Read Appendix B (CV splitters). Assess:
- For h=22 target (y = log(RV).shift(-22)), the purge gap must be >= 22 days to prevent label leakage. Does the config enforce this?
- Does `ExpandingWindowCV` handle different purge gaps per horizon, or is it fixed at config time?
- If running multiple horizons in one experiment, does each horizon get its own CV split?

- [ ] **Step 5: Evaluate ML experiment workflow against best practices**

Read Sections 9-10 (config, pipeline). Research and assess:
- **Experiment tracking:** Config snapshot + metrics.json vs. structured experiment database. What lightweight alternatives work without cloud services? (e.g., SQLite-backed experiment log, structured CSV/parquet of all results, sacred/neptune-lite)
- **Reproducibility gaps:** Seed + YAML covers model randomness. What about: feature layer execution order (if non-deterministic), pandas/numpy version differences, data cache changes between runs?
- **Hyperparameter search:** Optuna is mentioned for LightGBM but not integrated into the pipeline. Where should HP search results (trials, best params, search history) be persisted? How to compare across search runs?
- **Scale:** 714 experiments (7 models x 34 symbols x 3 horizons). Can results be queried/compared across experiments? Does the flat directory structure work at this scale?
- **Ideal flow:** Research what a well-structured ML experiment lifecycle looks like (hypothesis -> config -> run -> evaluate -> compare -> decide) and identify gaps in the current pipeline.

- [ ] **Step 6: Evaluate wrong directions (Pillar 3)**

Assess each of the following:
- **Stubbed modules:** TCN model (models/lstm.py), HTML reporting (6 stubbed sections in reporting/sections/), visualization module (8 stubbed functions in visualization/). Are these worth the API contract definitions, or is the stub code dead weight?
- **34-symbol universe:** Is running all 34 symbols necessary for the final presentation, or would a focused 5-10 symbol subset be more rigorous and faster to iterate on?
- **Over-engineering:** Rich progress display system (PipelineProgress + StageProgress), Jinja2 HTML reporting with Plotly CDN -- are these presentation-quality or premature polish?
- **LSTM/TCN for E-mini only:** Only 1 symbol has L2 depth data. Is building a full sequence model infrastructure for one symbol justified?

- [ ] **Step 7: Re-triage architecture debt (Pillar 5)**

Read Appendix E (13 debt items). For each item:
- Does it block any work identified in Pillars 1-4?
- Should its priority change based on review findings?
- Are there new debt items discovered during this review?

Produce a revised priority table with justification for any changes.

- [ ] **Step 8: Write Pillars 2, 3, 5 findings**

For each issue, write a finding with: severity, doc section + line range, details, and recommendation.

---

### Task 3: Ensemble vs. Stacking Research + Missing Pieces + Data Gaps (Pillars 4, 6)

**Files to read:**
- `notes/ml_vol_forecasting_docs.md` -- Sections 18 (models), 22 (open questions), Appendix A (status), Appendix F (data gaps)
- `reference/bibliography.md` -- All entries mentioning ensemble, stacking, LSTM, multi-horizon
- `reference/project-papers/*.pdf` -- Papers that discuss ensemble or multi-horizon approaches
- `guides/vol-project-ref/chapters/ch11-ensemble.tex` -- Ensemble chapter in guide
- `guides/vol-project-ref/chapters/ch10-lstm-intraday.tex` -- LSTM chapter in guide

**Output:** Raw findings for Pillars 4 and 6, including the ensemble vs. stacking deep-dive.

- [ ] **Step 1: Internal paper cross-reference for ensemble/stacking**

Search `reference/bibliography.md` for every entry that discusses:
- Ensemble methods for volatility forecasting
- LSTM/RNN embeddings as features for tree models
- Multi-horizon forecast strategies (h=1 vs h=5 vs h=22)
- Prediction blending vs. feature stacking
- Model combination in financial forecasting

For each relevant paper, extract: what approach they used, what horizons they tested, what they found about ensemble vs. stacking, and any horizon-dependent conclusions.

Also read `guides/vol-project-ref/chapters/ch11-ensemble.tex` and `ch10-lstm-intraday.tex` for what the guide already claims.

- [ ] **Step 2: Search project papers for ensemble evidence**

Read or scan each PDF in `reference/project-papers/` for ensemble/stacking discussion:
- `christensen-siggaard-veliyev-2023-ml-volatility-forecasting.pdf` -- likely discusses model combination
- `hard-to-beat-2024-ml-vs-linear-rv.pdf` -- may compare ensemble vs. individual models
- `fed-2025-linear-nonlinear-rv-forecasting.pdf` -- likely compares linear + nonlinear combination
- `bucci-2020-rv-forecasting-neural-networks.pdf` -- neural network approach, may discuss stacking
- `rahimikia-poon-2020-ml-rv-forecasting.pdf` -- ML approach, likely discusses feature importance
- `moreno-pino-zohren-2022-deepvol.pdf` -- deep learning for vol
- `spotv2net-2024-intraday-vol-gat.pdf` -- graph attention for vol, may discuss multi-horizon

Extract specific findings about: stacking vs. blending, horizon-dependent strategies, embedding approaches.

- [ ] **Step 3: Independent web research on ensemble vs. stacking**

Web search for 2023-2026 literature on:
- "LSTM embedding features LightGBM volatility forecasting"
- "feature stacking vs prediction blending multi-horizon forecasting"
- "ensemble methods realized volatility forecasting"
- "two-stage model stacking time series forecasting"
- "LSTM hidden state features gradient boosting"

Answer the six specific questions from the spec:
1. Does the optimal ensemble strategy differ by horizon?
2. Does LSTM embedding dimensionality matter more at short horizons?
3. Does blending degrade at h=1 where signal-to-noise is highest?
4. Do any papers show stacking beating blending at h=22?
5. What embedding extraction approach is most stable for walk-forward retraining?
6. Is there a simpler approach that gets 80% of the benefit?

- [ ] **Step 4: Synthesize ensemble vs. stacking recommendation**

Combine internal and external research into a clear recommendation:
- What strategy for h=1?
- What strategy for h=5?
- What strategy for h=22?
- Does the doc's current claim ("stacking at h=1/h=5, blending at h=22") hold up?
- What's the minimum viable ensemble approach if time is short?

- [ ] **Step 5: Deliverable gap analysis (Pillar 4)**

Compare what's built (Appendix A status) against three deliverables:

**QLIKE tournament:** Needs implemented: statistical tests (DM, MCS), LightGBM with QLIKE objective, tournament_table function, at least one non-HAR model to compare. What's the minimum path?

**Tradeable signal:** Needs implemented: IV-RV gap signal (requires Layer 2 options features), delta-hedged straddle P&L, vol-targeting P&L, Sharpe/drawdown computation. All in `evaluation/economic_value.py` (currently stubbed). What's the minimum path?

**Final presentation:** Needs: comparison tables, forecast plots, P&L charts, summary statistics. What visualization/reporting infrastructure is actually needed vs. what's stubbed but unnecessary?

- [ ] **Step 6: Timeline feasibility assessment**

Map the minimum required work against 16 remaining weeks:
- What's the critical path (sequential dependencies)?
- What can be parallelized?
- What's the minimum viable deliverable at week 15 (safety buffer)?
- What are stretch goals ordered by impact-per-effort?

- [ ] **Step 7: Data pipeline gap triage (Pillar 6)**

Read Appendix F. For each known gap, classify as:
- **Blocks a deliverable:** Required for QLIKE tournament, tradeable signal, or presentation
- **Nice to have:** Would improve results but not required
- **Irrelevant:** Not needed given the current plan

Specific assessments:
- Earnings calendar (hard-code 30 names): realistic in timeline? Worth it for the signal?
- Single-stock IV (RESOLVED): verify the resolution actually unblocks Layer 2
- L2 depth for equities (not available): does this kill the LSTM plan or just scope it to E-mini?
- Missing cross-asset data (EUR/USD, DXY, Fed Funds): how many Layer 4 features does this affect?

- [ ] **Step 8: Write Pillars 4, 6 findings**

For each issue, write a finding with: severity, doc section + line range, details, and recommendation. The ensemble/stacking deep-dive gets its own subsection with the full evidence trail.

---

## Chunk 2: Synthesis and Output

Depends on all three Task outputs from Chunk 1.

### Task 4: Merge findings and write final document

**Files to write:**
- `notes/review-codebase-audit.md` -- Final output

- [ ] **Step 1: Collect all raw findings from Tasks 1-3**

Gather the outputs from the three parallel research agents. Check for:
- Contradictions between agents (e.g., math agent says formula is correct but architecture agent flags the same code for different reasons)
- Duplicate findings that should be merged
- Gaps where no agent covered a spec requirement

- [ ] **Step 2: Assign consistent severity ratings**

Apply consistent severity criteria across all findings:
- **Critical:** Blocks a deliverable, formula error that would produce wrong results, architectural problem that requires redesign
- **Important:** Will cause pain in the next 2-3 months, should be addressed before Phase 6 (ML training)
- **Minor:** Technical debt, style issue, or optimization that can wait

- [ ] **Step 3: Write Pillar sections**

Write each of the 6 pillar sections with findings in severity order (Critical first). Each finding gets:
```
### [Finding title]
**Severity:** Critical / Important / Minor
**Doc reference:** Section X, lines Y-Z
**Details:** [What's wrong or missing, with paper citations]
**Recommendation:** [Specific action to take]
```

- [ ] **Step 4: Write Appendix -- Validated Items**

List things the review confirmed are solid and don't need changing. This builds confidence about what's done right and prevents unnecessary rework. Draw from both the doc's own "What's Actually Good" (Appendix E) and anything the review found to be correct/well-designed.

- [ ] **Step 5: Write Executive Summary -- Top 5 Actions**

Synthesize all 6 pillars into exactly 5 prioritized actions. Each action:
- States what to do in one sentence
- References the pillar findings that support it (e.g., "See Pillar 1, Finding 3; Pillar 5, Finding 1")
- Estimates effort (days/weeks)
- States why it's higher priority than items below it

These 5 actions are the primary input for Session 2 (project roadmap) and Session 3 (Copilot prompts).

- [ ] **Step 6: Write the complete file**

Assemble all sections into `notes/review-codebase-audit.md` following the output structure from the spec.

- [ ] **Step 7: Self-review**

Read the complete document and verify:
- Every formula from the spec's table was checked (16 formulas)
- All 6 specific ensemble/stacking questions were answered
- All 13 debt items from Appendix E were re-triaged
- All data gaps from Appendix F were classified
- Executive summary has exactly 5 actions
- No findings reference the agentic workflow framework negatively
- Severity ratings are consistent across pillars

- [ ] **Step 8: Commit**

```bash
git add notes/review-codebase-audit.md
git commit -m "docs: add codebase documentation audit (6-pillar review)"
```
