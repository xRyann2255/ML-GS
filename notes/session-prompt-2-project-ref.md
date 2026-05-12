# Session 2: Two New Chapters for Vol-Project-Ref

I need to add potentially **two new chapters** (if you suggest something better, let me know - I just don't want to repeat any information) to the vol-project-ref guide.

---

## Chapter A: Data Sources and Feature Transformation Pipeline

A complete, self-contained reference for every data source used in the project and exactly how raw data is transformed into the final feature matrix that feeds the models.

### Before writing, ASK ME:

1. **Layer 2-5 data sources:** The docs show stubbed API contracts for options (Marquee), cross-asset (TSDB), microstructure (L2 depth), and calendar features. Have I actually tested all of these on the GS machine? Which ones work, which ones have issues?

2. **Feature selection:** With all 6 layers producing features, the design matrix could get wide. Am I planning to use all features for LightGBM and a subset for HAR? What's the feature selection strategy?

3. **Transformation decisions:** The docs show triple expansion (level/change/zscore) for tree models but not for OLS baselines. Are there any other transformations I'm considering? Rolling windows other than 5/22?

4. **Target variable:** The docs say log(RV) shifted forward by h days. Is this still the plan for all models? Any consideration of multi-step targets or direct variance-space targets?

### After getting answers, the chapter should cover:

1. **Raw data source inventory:** Every data source as a row in a table: source name, GS API/system, fields extracted, frequency, history depth, universe coverage, access status (confirmed/untested/broken). Group by: tick-level, daily, options surface, cross-asset, calendar/event.

2. **Source-to-measure pipeline:** For each raw source, the exact transformation chain that produces daily scalar measures. Show the math at each step (e.g., L1 ticks -> previous-tick interpolation -> 5-min bars -> 77 log returns -> RV = sum of squared returns). Include the 18 daily measures already computed and the measures needed from Layers 2-5.

3. **Measure-to-feature pipeline:** How daily measures become model-ready features. Cover: the lagged log d/w/m rolling pattern, the shift(1) for no-look-ahead, the triple expansion for tree models, and any feature-specific transformations (e.g., noise_gap is a ratio, not log-transformed).

4. **Complete feature matrix schema:** A single table listing every feature that will exist in the final design matrix, grouped by layer. Columns: feature name, formula, source measure(s), lag structure, which models use it (HAR/SHAR/HARQ/LightGBM/LSTM).

5. **Target variable specification:** Exact definition of y for each horizon (h=1, h=5, h=22), including the log transform, the forward shift, and the Duan (1995) retransformation for final evaluation.

6. **Data quality and edge cases:** How zeros are handled (safe_log), how missing days work (NaN propagation vs. forward-fill), minimum history requirements (22 days for monthly window), COVID period treatment.

Required boxes: prereq, keyidea for each transformation step, workedexample showing one symbol's data flowing from raw ticks through to a single row of the feature matrix (with actual numbers), warning for look-ahead bias risks and data quality traps, projectconnection linking to specific code files.

---

## Chapter B: Project Plan and End-to-End Development Roadmap

This chapter serves as the **overall project plan and end-to-end development roadmap** for the ML realized volatility forecasting internship project (~20 weeks, May-Sep 2026).

This is NOT a retrospective of what's been done. This is a forward-looking plan: what is the best path from where I am now to the final deliverable (QLIKE tournament + tradeable signal + presentation)?

### Before writing, ASK ME:

1. **Scope:** Which of the 5 originally scoped directions (HARQ-X hybrid, intraday LOB, multivariate GNN, rough vol, VRP trader) am I actually pursuing now that I have real data? Has my thinking changed since the docs were written?

2. **Timeline constraints:** How many weeks remain? Are there any mid-internship checkpoints, presentations, or deadlines I need to hit before the final presentation?

3. **Priority ranking:** Between academic rigor (QLIKE, MCS, DM tests), trading signal (IV-RV gap P&L), and model novelty (ensemble, LSTM), which matters most for my audience? What does the desk care about vs. what makes a good paper?

4. **Feature layers:** Layers 2-5 are all stubbed. Which ones do I actually think will matter most? Should any be cut to save time?

5. **Data reality:** Now that I've worked with real Chunk Store data for a few weeks, are there any data quality issues, latency problems, or coverage gaps that change the plan?

6. **Ensemble strategy:** The docs mention feature stacking at h=1/h=5 and prediction blending at h=22. Is this still the plan? Has anything changed?

7. **What's the minimum viable deliverable?** If I ran out of time at week 15, what absolutely must be done by then?

### After getting answers, the chapter should cover:

1. **Project objectives and success criteria:** What "done" looks like, with specific quantitative targets (QLIKE improvement in bps, Sharpe ratio threshold, etc.)

2. **End-to-end development plan:** Phased roadmap from current state to final deliverable. Each phase should have: objectives, specific tasks, dependencies on prior phases, estimated duration, and concrete acceptance criteria.

3. **Critical path analysis:** What are the sequential dependencies? What can be parallelized? Where are the highest-risk items (things that might not work and need a fallback)?

4. **Minimum viable deliverable:** The subset that must be done by ~week 15 to guarantee a presentable result, even if stretch goals fail.

5. **Stretch goals:** Things that would make the presentation exceptional but aren't required. Ordered by impact-per-effort.

Required boxes: prereq at chapter start, keyidea for each major phase, warning for timeline risks and dependencies, projectconnection boxes linking phases to specific code modules, workedexample for the critical path timeline.

---

## Existing vol-project-ref structure (for reference)

The guide lives at `guides/vol-project-ref/` and currently has 14 chapters in 4 parts:

**Part I: The Project (ch01-02)**
1. What We're Forecasting -- target definitions (log RV at h=1, 5, 22)
2. Our Data -- data sources inventory (11.3 years)

**Part II: The Feature Set (ch03-08)**
3. HAR Core and Measurement Quality (Layer 0)
4. Asymmetric Volatility (Layer 1)
5. Options-Implied Features (Layer 2)
6. Microstructure Features (Layer 3)
7. Cross-Asset Spillovers (Layer 4)
8. Feature Composition and Selection (Layers 0-7 synthesis)

**Part III: Models (ch09-12)**
9. LightGBM for Tabular Volatility
10. LSTM for Intraday Sequences
11. The Ensemble (two-branch blending)
12. Interpretable Trees and Rashomon Analysis

**Part IV: Making It Work (ch13-14)**
13. Evaluation (metrics, model comparison)
14. The Complete Pipeline (end-to-end assembly, implementation roadmap)

The new chapters should match this brief, straight-to-the-point style. The existing guide reads as a quick reference, not a textbook. Keep that tone.

---

## Shared context for both chapters

- Read notes/ml_vol_forecasting_docs.md to understand the current state of the implementation (what's built, what's stubbed, what's missing)
- Read the findings from Session 1 (the review) to understand what needs fixing and what's on the wrong track
- The existing vol-project-ref guide is at guides/vol-project-ref/ (read main.tex and a few chapter files to match style)
- Both chapters should follow the exact same LaTeX style as existing chapters (memoir class, tcolorbox environments, booktabs tables, natbib citations)
- Cross-reference the bibliography for all papers that motivated specific choices
- No em dashes in the text
