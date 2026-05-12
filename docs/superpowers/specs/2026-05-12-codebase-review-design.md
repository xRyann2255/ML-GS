# Codebase Documentation Audit -- Design Spec

**Date:** 2026-05-12
**Input:** `notes/ml_vol_forecasting_docs.md` (1988 lines, 22 sections + 8 appendices)
**Output:** `notes/review-codebase-audit.md`
**Purpose:** Deep technical review of the ML vol forecasting codebase documentation, producing actionable findings that feed Session 2 (project ref update) and Session 3 (Copilot prompts).

---

## Audience and Format

**Audience:** Ryan (primary), also usable as a project artifact for mentor review or presentation prep.

**Format:** Single markdown file, organized by six review pillars. Each finding includes severity (Critical / Important / Minor), doc reference (section + line range), details with paper citations, and a specific recommendation.

**Validated scope exclusion:** The agentic workflow framework (16 personas, 46 skills, 16 workflows) is mentor-directed infrastructure for project handoff. It is not in scope for "wrong directions" critique.

---

## Output Structure

```
# Codebase Documentation Audit -- 2026-05-12

## Executive Summary
Top 5 prioritized actions for the next 16 weeks.
Each action references the pillar findings that support it.
Directly feeds Sessions 2 and 3.

## Pillar 1: Mathematical Correctness
## Pillar 2: Architecture Review
## Pillar 3: Wrong Directions
## Pillar 4: Missing Pieces
## Pillar 5: Architecture Debt Triage
## Pillar 6: Data Pipeline Gaps

## Appendix: Validated Items
```

---

## Pillar 1: Mathematical Correctness

Cross-reference every formula in the doc against the original papers. Sources: 19 PDFs in `reference/project-papers/`, ~80 entries in `reference/bibliography.md`, vol-project-ref guide chapters 1-14.

### Formulas to verify

| Formula | Paper | Doc Section |
|---------|-------|-------------|
| RV = sum(r_i^2) | Andersen-Bollerslev 2003 | 12, 17 |
| RQ = (N/3) * sum(r_i^4) | Barndorff-Nielsen-Shephard 2002 | 12, 17 |
| BPV = (pi/2) * sum(\|r_i\| * \|r_{i-1}\|) | Barndorff-Nielsen-Shephard 2004 | 13 |
| BNS z-stat including theta constant | Barndorff-Nielsen-Shephard 2006 | 13 |
| Realized tripower quarticity | Barndorff-Nielsen-Shephard 2006 | 13 |
| Lee-Mykland intraday jump test + Gumbel threshold | Lee-Mykland 2008 | 13 |
| Semivariances RS+/RS- | Patton-Sheppard 2015 | 13 |
| Signed jumps (Lee-Mykland partitioned) | Patton-Sheppard 2015 | 13 |
| Realized kernel with Parzen weights + bandwidth | Barndorff-Nielsen et al. 2008 | 14 |
| TSRV two-scale estimator | Zhang 2005 | 14 |
| Pre-averaged RV with triangular weights | Jacod et al. 2009 | 14 |
| Realized skewness/kurtosis | Amaya et al. 2015 | 13 |
| QLIKE in variance-space and log-space | Patton 2011 | 19 |
| Duan retransformation: exp(y + sigma^2/2) | Duan 1995 | 19 |
| HAR feature construction (avg in variance, then log) | Corsi 2009 | 12 |
| HARQ interaction term | Bollerslev et al. 2016 | 12 |

### What gets flagged

- Outright formula errors
- Correct formulas with ambiguous or inconsistent notation between sections
- Implementation details that diverge from the paper (e.g., RQ scaling conventions)
- Discrepancies between the doc and the vol-project-ref guide chapters

---

## Pillar 2: Architecture Review

### Software architecture scalability

- **Registry + Protocol pattern:** Does `FeatureLayer.compute(daily_data)` accommodate Layer 2 (Marquee data source) without internal data fetching?
- **VolModel protocol:** Assess whether `fit(X: DataFrame, y: Series)` narrowness is a simple extension or a deeper problem for LSTM/TCN 3D input.
- **Pipeline composability:** Can `Pipeline.run()` handle mixed tabular + sequence models? Can it support two-stage LSTM-embedding-to-LightGBM flow?
- **Config system:** Can `ExperimentConfig` express ensemble or stacking experiments, or is it single-model only?
- **CV splitters:** Do purge gaps scale correctly for h=22 (needs 22+ day purge) vs. h=1?

### ML experiment best practices

- **Experiment tracking:** Is config snapshot + metrics.json sufficient for comparing dozens of runs? What lightweight alternatives to MLflow/W&B work within GS infrastructure constraints (no cloud, no external services)?
- **Reproducibility:** Does seed + config YAML guarantee exact reproduction? Feature layer ordering, dependency version pinning, data cache staleness risks.
- **Hyperparameter search integration:** How does Optuna integrate with the pipeline? Where do search results live? How do you compare across HP search trials?
- **Scale test:** 7 models x 34 symbols x 3 horizons = 714 experiments. Does `workspace/models/{name}/{symbol}/` scale? Can results be queried across experiments?
- **Ideal end-to-end ML experiment flow:** What does best practice look like from hypothesis to result, and how close is the current pipeline?

---

## Pillar 3: Wrong Directions

- ~~Agentic workflow framework~~ -- validated by mentor, skip
- Evaluate whether stubbed modules represent wasted effort: TCN model, HTML reporting (6 stubbed sections), visualization module (8 stubbed functions)
- Are features being built that won't appear in the final presentation?
- Is the 34-symbol universe the right scope for a 20-week project, or should it be narrower?
- Is any current code over-engineered relative to the timeline?

---

## Pillar 4: Missing Pieces

### Deliverable gap analysis

- What's needed for the QLIKE tournament deliverable that isn't built or stubbed?
- What's needed for the tradeable signal deliverable (IV-RV gap, delta-hedged straddle, vol-targeting)?
- What's needed for the final presentation (visualizations, narrative, comparison tables)?

### Ensemble vs. Feature Stacking deep-dive

This is the most research-intensive component. The doc currently states "stacking at h=1/h=5, blending at h=22" but this needs rigorous validation.

**Internal cross-reference:** Search every paper in `reference/project-papers/` and `reference/bibliography.md` for discussion of:
- Ensemble methods for volatility forecasting
- LSTM/RNN embeddings as features for tree models
- Multi-horizon forecast strategies
- Prediction blending vs. feature stacking

**Independent research:** Web search for 2023-2026 literature on:
- LSTM-to-tree stacking vs. prediction blending for multi-horizon RV
- Whether optimal strategy differs by forecast horizon
- Embedding dimensionality and stability across walk-forward windows
- Evidence for or against stacking at long horizons (h=22)

**Specific questions to answer:**
1. Does the optimal ensemble strategy differ by horizon?
2. Does LSTM embedding dimensionality matter more at short horizons?
3. Does blending degrade at h=1 where signal-to-noise is highest?
4. Do any papers show stacking beating blending at h=22?
5. What embedding extraction approach is most stable for walk-forward retraining?
6. Is there a simpler approach that gets 80% of the benefit?

### Timeline feasibility

- Gap analysis against 16 remaining weeks
- What must be cut if time runs short?

---

## Pillar 5: Architecture Debt Triage

- Re-evaluate all 13 items from Appendix E against findings from Pillars 1-4
- Determine if any P1/P2 items are actually blocking the next implementation phase
- Identify new debt items not listed in the doc
- Produce revised priority ranking with justification

---

## Pillar 6: Data Pipeline Gaps

- Triage all items from Appendix F into "blocks a deliverable" vs. "nice to have"
- Cross-reference against which feature layers are actually needed for the final plan
- Earnings calendar: is hard-coding 30 names realistic?
- Single-stock IV (marked RESOLVED) -- verify this is actually unblocked
- Assess whether any gap requires a fallback strategy

---

## Executive Summary

Synthesize all six pillars into **Top 5 Actions for the Next 16 Weeks**, prioritized by impact on final deliverables. Each action references the pillar findings that support it. This section is designed to be directly copy-pasted into Session 2 and Session 3 prompts.

---

## Execution Method

The review will be executed by dispatching parallel research agents:
1. **Math verification agent:** Cross-references formulas against papers and vol-project-ref
2. **Architecture + ML practices agent:** Evaluates software patterns and experiment workflow
3. **Ensemble/stacking research agent:** Deep-dives the stacking vs. blending question with both internal papers and web research

Results are synthesized into the single output file with consistent severity ratings and the executive summary.
