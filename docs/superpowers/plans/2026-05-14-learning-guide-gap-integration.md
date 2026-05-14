# Learning Guide Gap Integration -- Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add all vol-project-ref content missing from the vol-learning-guide -- one new Rashomon chapter plus additions to five existing chapters -- with every formula verified against source papers.

**Architecture:** Three phases: (1) update the write-chapter skill to add paper-verification passes, (2) add bib entries as a shared prerequisite, (3) dispatch six parallel subagents (one per chapter) using the modified skill's 5-pass pipeline. Each subagent reads source papers first (Pass 0), writes LaTeX (Pass 1), verifies citations (Pass 2), condenses (Pass 3), and runs naive-reader review (Pass 4).

**Tech Stack:** LaTeX (memoir/report class), natbib, tcolorbox, TikZ, booktabs. All subagents use Opus 4.6.

**Spec:** `docs/superpowers/specs/2026-05-14-learning-guide-gap-integration-design.md`

---

## Phase 1: Prerequisites (sequential)

### Task 1: Update Write-Chapter Skill

**Files:**
- Modify: `.claude/skills/write-chapter/SKILL.md`

- [ ] **Step 1: Add Pass 0 -- Source Extraction before Pass 1**

Insert this new section after the "## Pass 1" heading's preamble but logically before Pass 1 runs. The new section goes between the "Tone" subsection (line 49) and "## Pass 1" (line 51):

```markdown
## Pass 0 -- Source Extraction (runs before Pass 1)

Before writing begins, the agent reads the specified source papers and produces a structured extraction. For each paper:

1. Read only the specific pages/sections relevant to the chapter's topics (not full papers)
2. For each formula, definition, claim, or threshold found, record:

```
PAPER: [Author Year] ([short title])
PAGE: [page number]
TYPE: FORMULA | DEFINITION | CLAIM | THRESHOLD
CONTENT: [exact content from paper]
NOTATION: [symbol definitions as used in the paper]
GUIDE_NOTATION: [how to adapt notation to match learning guide conventions]
```

Rules:
- Every formula must include the exact equation number and page from the source
- Every quantitative claim (e.g., "5-15% QLIKE improvement") must have a paper source
- If a claim appears in the spec or vol-project-ref but has no paper backing it, flag it and do not include it in the chapter
- The extraction stays in the agent's context as ground truth for Pass 1. Do not save it as a file.
```

- [ ] **Step 2: Add Mid-Write Paper Discovery rule to Pass 1**

Append to the end of the Pass 1 numbered list (after item 4 "Save as..."):

```markdown
5. **Mid-write paper discovery:** If you encounter a concept that needs a citation or formula not in the Pass 0 extraction:
   a. Search `reference/project-papers/` and `reference/papers/` for relevant papers
   b. If found, read the relevant pages and extract the needed material
   c. If not found in the repo, search the web for the paper (arXiv, open-access proceedings, author websites)
   d. If available, download it to `reference/project-papers/` and extract the needed material
   e. If behind a paywall, note it as a gap and write around it -- never guess a formula
```

- [ ] **Step 3: Upgrade Pass 2 from Cross-referencer to Verifier**

Replace the Pass 2 sub-agent prompt with:

```markdown
## Pass 2 -- Verifier (parallel sub-agent)

Dispatch a sub-agent with this prompt:

> Read the draft chapter at [path]. For every `\citep{}` and `\citet{}` command in the chapter:
> 1. Find the cited paper in `reference/project-papers/` or `reference/papers/`
> 2. Read the specific pages referenced (or search for the relevant content)
> 3. Verify that every formula in the chapter matches the source paper (correct signs, terms, notation)
> 4. Verify that every quantitative claim matches what the paper actually reports
> 5. Flag any discrepancy as CRITICAL with: [chapter line, what it says, what the paper says, page in paper]
>
> Also search for papers NOT yet cited that are relevant to claims in the chapter, and suggest additional citations.
>
> Output:
> - A numbered list of verification results (PASS or CRITICAL for each citation)
> - A numbered list of suggested additional citations with line locations
```

- [ ] **Step 4: Update skill frontmatter and description**

Change the frontmatter description:

```markdown
---
name: write-chapter
description: Multi-pass pipeline for writing LaTeX learning guide chapters. 5 passes: source extraction → write → verify → condense → naive-reader review. Every formula verified against source papers.
---
```

Change the opening line:

```markdown
Write a complete LaTeX chapter using a 5-pass quality pipeline.
```

- [ ] **Step 5: Update Input section**

Change "Source papers (optional)" to:

```markdown
- **Source papers**: specific papers from `reference/` to read in Pass 0. For each paper, specify which pages/sections to extract (e.g., "Xin et al. 2022 pp.3-7: Rashomon set definition, enumeration algorithm")
```

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/write-chapter/SKILL.md
git commit -m "feat: upgrade write-chapter skill to 5-pass pipeline with source verification"
```

---

### Task 2: Add Bibliography Entries

**Files:**
- Modify: `vol-learning-guide/references.bib` (append at end)

- [ ] **Step 1: Add missing bib entries**

Append these entries at the end of `vol-learning-guide/references.bib` (after the last entry around line 1203). The following keys are NOT already in the bib: XinEtAl2022, DonnellyEtAl2023, DongRudin2020, VanDenBosEtAl2024, HeileBabbar2025, BabbarEtAl2025, Lundberg2017, EasleyLopezOHara2012, Ke2017, Optiver2021.

The following keys ARE already present and must NOT be duplicated: Kyle1985 (line 1155), Patton2011 (line 253), DieboldMariano1995 (line 275), Rebonato2004 (line 124), HARdToBeat2024 (line 860), ChristensenSiggaardVeliyev2023 (line 817), Kidger2021NeuralSDE (already in bib).

```bibtex

% ── New entries for learning guide gap integration (2026-05-14) ──

@inproceedings{XinEtAl2022,
  author    = {Xin, Rui and Zhong, Chudi and Chen, Zhi and Takagi, Takuya and Seltzer, Margo and Rudin, Cynthia},
  title     = {Exploring the Whole {Rashomon} Set of Sparse Decision Trees},
  booktitle = {Advances in Neural Information Processing Systems},
  volume    = {35},
  year      = {2022},
  note      = {Oral presentation; arXiv 2209.08040},
}

@inproceedings{DonnellyEtAl2023,
  author    = {Donnelly, Jon and Katta, Srikar and Rudin, Cynthia and Browne, Edward P.},
  title     = {{Rashomon} Importance Distributions},
  booktitle = {Advances in Neural Information Processing Systems},
  volume    = {36},
  year      = {2023},
}

@misc{DongRudin2020,
  author    = {Dong, Jiayun and Rudin, Cynthia},
  title     = {Exploring the Cloud of Variable Importance for the Set of All Good Models},
  year      = {2020},
  note      = {arXiv 1901.03209; Nature Machine Intelligence},
}

@inproceedings{VanDenBosEtAl2024,
  author    = {van den Bos, Mim and van der Linden, Jacobus G. M. and Demirovi\'{c}, Emir},
  title     = {{STreeD}: Piecewise-Linear and Piecewise-Constant Regression Trees},
  booktitle = {Proceedings of the 41st International Conference on Machine Learning (ICML)},
  year      = {2024},
}

@inproceedings{HeileBabbar2025,
  author    = {Heile, Zakk and Babbar, Varun and McTavish, Hayden and Rudin, Cynthia},
  title     = {Efficient {Rashomon} Set Approximation for Decision Tree Models},
  booktitle = {NeurIPS 2025 Workshop on ML x OR},
  year      = {2025},
}

@inproceedings{BabbarEtAl2025,
  author    = {Babbar, Varun and McTavish, Hayden and Rudin, Cynthia and Seltzer, Margo},
  title     = {Near-Optimal Decision Trees in a {SPLIT} Second},
  booktitle = {Proceedings of the 42nd International Conference on Machine Learning (ICML)},
  year      = {2025},
  note      = {Oral presentation; arXiv 2502.15988},
}

@inproceedings{Lundberg2017,
  author    = {Lundberg, Scott M. and Lee, Su-In},
  title     = {A Unified Approach to Interpreting Model Predictions},
  booktitle = {Advances in Neural Information Processing Systems},
  volume    = {30},
  year      = {2017},
}

@article{EasleyLopezOHara2012,
  author    = {David Easley and Marcos M. Lopez de Prado and Maureen O'Hara},
  title     = {Flow Toxicity and Liquidity in a High-Frequency World},
  journal   = {The Review of Financial Studies},
  volume    = {25},
  number    = {5},
  pages     = {1457--1493},
  year      = {2012},
  doi       = {10.1093/rfs/hhs053},
}

@inproceedings{Ke2017,
  author    = {Ke, Guolin and Meng, Qi and Finley, Thomas and Wang, Taifeng and Chen, Wei and Ma, Weidong and Ye, Qiwei and Liu, Tie-Yan},
  title     = {{LightGBM}: A Highly Efficient Gradient Boosting Decision Tree},
  booktitle = {Advances in Neural Information Processing Systems},
  volume    = {30},
  year      = {2017},
}

@misc{Optiver2021,
  author    = {{Optiver}},
  title     = {Optiver Realized Volatility Prediction},
  year      = {2021},
  note      = {Kaggle competition. \url{https://www.kaggle.com/c/optiver-realized-volatility-prediction}},
}
```

- [ ] **Step 2: Commit**

```bash
git add vol-learning-guide/references.bib
git commit -m "feat: add 10 bib entries for learning guide gap integration"
```

---

## Phase 2: Chapter Writing (all six tasks run in parallel)

Each task below is dispatched as an independent Opus 4.6 subagent. Each subagent follows the modified write-chapter skill (5-pass pipeline). The subagent prompt must include: the topic, the guide (`vol-learning-guide`), the source papers with page targets, the insertion point, and the "do NOT duplicate" constraints.

---

### Task 3: New Rashomon Chapter

**Files:**
- Create: `vol-learning-guide/chapters/12-rashomon-interpretable-trees.tex`

**Source papers for Pass 0:**
- `reference/project-papers/xin-et-al-2022-treefarms-rashomon-set.pdf` pp.1-12: Rashomon set definition (Def 1), TreeFARMS algorithm, set size bounds, objective function
- `reference/project-papers/donnelly-et-al-2023-rashomon-importance-distributions.pdf` pp.1-10: RID methodology, confidence intervals, finite-sample error rates
- `reference/project-papers/dong-rudin-2020-variable-importance-clouds.pdf` pp.1-15: VIC definition, overlap interpretation, cloud construction
- `reference/project-papers/vandenbos-et-al-2024-streed-piecewise-linear.pdf` pp.1-10: STreeD optimization objective, piecewise-linear leaf model, cost-complexity regularization
- `reference/project-papers/heile-babbar-2025-efficient-rashomon-approximation.pdf` pp.1-6: LicketyRESPLIT algorithm, runtime/memory improvements vs TreeFARMS
- `reference/project-papers/babbar-et-al-2025-split-near-optimal-decision-trees.pdf` pp.1-12: SPLIT algorithm, greedy+DP hybrid, speed benchmarks, Rashomon set extension
- `reference/project-papers/lundberg-lee-2017-shap.pdf` pp.1-5: SHAP value definition, Shapley axioms (for contrast)

**Chapter outline (from spec):**
1. Opening -- SHAP instability motivation (VIX vs ATM IV across refits)
2. Prerequisites box -- Ch.11 (tree methods), SHAP basics, feature importance
3. The Problem with Single-Model Explanations -- near-substitute features, importance instability
4. The Rashomon Set -- definition, epsilon tolerance, worked example (two small trees, different features, same accuracy)
5. Optimal Sparse Decision Trees (STreeD) -- piecewise-linear leaves, provably optimal, depth/leaf tradeoffs
6. Enumerating the Rashomon Set -- TreeFARMS exact, SPLIT/RESPLIT speedups, LicketyRESPLIT approximation, expected set sizes
7. What the Rashomon Set Reveals -- RID (stable importance, confidence intervals, contrast with bootstrapped SHAP) + VIC (min/max importance range, overlapping = substitutes, worked example VIX/VVIX/ATM IV)
8. Rashomon Analysis for Volatility Forecasting -- regime-stable selection, prediction multiplicity, novelty, GS defensibility

**Constraints:**
- Do NOT cover basic tree methods, gradient boosting, or SHAP computation (already in Ch.11)
- Do NOT cover feature engineering (Ch.10) -- reference features by name only
- New chapter file, no insertion into existing files

- [ ] **Step 1: Run Pass 0 -- read all 7 papers, extract formulas/definitions/claims**
- [ ] **Step 2: Run Pass 1 -- write complete chapter following outline and learning style requirements**
- [ ] **Step 3: Run Pass 2 (verifier) and Pass 3 (condenser) in parallel**
- [ ] **Step 4: Consolidate -- apply verification fixes and condensing edits**
- [ ] **Step 5: Run Pass 4 -- naive reader review**
- [ ] **Step 6: Apply Pass 4 feedback, final coherence check**
- [ ] **Step 7: Verify all TikZ diagrams via verify-diagram skill**
- [ ] **Step 8: Commit**

```bash
git add vol-learning-guide/chapters/12-rashomon-interpretable-trees.tex
git commit -m "feat(vol-guide): add Rashomon analysis chapter (new Ch.12)"
```

---

### Task 4: Ch.08 -- Butterfly Spread Section

**Files:**
- Modify: `vol-learning-guide/chapters/08-options-vol-surface.tex`
- Insert after: line ~569 (end of IV term structure discussion, before "The Full Surface" subsection)

**Source papers for Pass 0:**
- `reference/books/Rebonato2004` (if accessible): butterfly spread definition, convexity interpretation
- `guides/vol-project-ref/chapters/ch05_options_implied.tex`: verify butterfly formula and feature rationale

**Content scope:**
- New section: "The Butterfly Spread"
- Formula: $BF_t = \frac{1}{2}(\sigma_{25\Delta P} + \sigma_{25\Delta C}) - \sigma_{ATM}$
- What it captures vs skew: symmetric tail thickness (kurtosis demand) vs directional asymmetry
- Crisis detection: both wings bid up by portfolio insurance
- Forward reference to Ch.10 where butterfly is used as a vol forecasting feature
- ~2-3 pages

**Constraints:**
- Do NOT duplicate existing skew content (already thorough in prior subsections)
- Do NOT explain Black-Scholes or basic IV (covered earlier in same chapter)

- [ ] **Step 1: Run Pass 0 -- extract butterfly formula and interpretation from source**
- [ ] **Step 2: Run Pass 1 -- write section and insert at correct location**
- [ ] **Step 3: Run Pass 2 (verifier) and Pass 3 (condenser) in parallel**
- [ ] **Step 4: Consolidate**
- [ ] **Step 5: Run Pass 4 -- naive reader**
- [ ] **Step 6: Apply feedback, verify diagrams if any**
- [ ] **Step 7: Commit**

```bash
git add vol-learning-guide/chapters/08-options-vol-surface.tex
git commit -m "feat(vol-guide): add butterfly spread section to Ch.08"
```

---

### Task 5: Ch.10 -- Five Feature Engineering Additions

**Files:**
- Modify: `vol-learning-guide/chapters/10-feature-engineering.tex`

**Source papers for Pass 0:**
- `reference/project-papers/easley-lopezdeprado-ohara-2012-vpin.pdf` pp.1-15: VPIN algorithm, volume bucketing, buyer/seller classification
- `reference/project-papers/kyle-1985-continuous-auctions-insider-trading.pdf` pp.1-10: Kyle's lambda definition, regression specification, price impact interpretation
- `reference/project-papers/hard-to-beat-2024-ml-vs-linear-rv.pdf`: diminishing returns evidence, ML vs linear baselines by horizon
- `reference/project-papers/christensen-siggaard-veliyev-2023-ml-volatility-forecasting.pdf`: feature importance rankings, horizon-dependent feature value
- `guides/vol-project-ref/chapters/ch08_feature_composition.tex`: diminishing returns curve percentages, triple expansion definition, calendar proximity, memory features

**Five additions in reading order:**

**Addition 1: Triple Expansion {level, change, z-score}**
- Insert at: line ~93 (after Feature Taxonomy section, before "Lagged RV Transforms")
- New section explaining the systematic expansion technique
- Worked example: bid-ask spread -> 3 variants

**Addition 2: VPIN + Kyle's Lambda**
- Insert at: lines 432-434 (REPLACE the existing brief VPIN mention with thorough treatment)
- Expand within existing "Microstructure and Limit Order Book Features" section
- Add Kyle's lambda alongside

**Addition 3: Vol-of-Vol + Regime Duration**
- Insert at: within lines 611-707 (expand existing "Long-Memory Features" section)
- Add after fractional differencing content (do NOT repeat it)

**Addition 4: Calendar Proximity**
- Insert at: within lines 708-819 (expand existing "Calendar and Event Features" section)
- Extend existing skeleton with continuous proximity measures

**Addition 5: Diminishing Returns Curve (capstone)**
- Insert at: line ~985 (new section BEFORE the existing Summary section)
- TikZ staircase diagram showing L0 -> L0+L1 -> ... -> full pipeline
- Horizon-dependent table
- This is the punchline of the entire chapter

**Constraints:**
- Do NOT duplicate price acceleration (already thorough at lines 409-425)
- Do NOT repeat fractional differencing (d ~ 0.35-0.45 already covered at lines 618-705)
- Do NOT repeat existing calendar binary dummies (lines 713-724)
- Do NOT repeat event-implied vol formula (already at line 745)

- [ ] **Step 1: Run Pass 0 -- read all source papers, extract VPIN algorithm, Kyle's lambda, diminishing returns data**
- [ ] **Step 2: Read existing Ch.10 content at each insertion point to understand surrounding context**
- [ ] **Step 3: Run Pass 1 -- write all 5 additions, inserting at correct locations**
- [ ] **Step 4: Run Pass 2 (verifier) and Pass 3 (condenser) in parallel**
- [ ] **Step 5: Consolidate**
- [ ] **Step 6: Run Pass 4 -- naive reader on the modified sections**
- [ ] **Step 7: Apply feedback, verify TikZ diagrams**
- [ ] **Step 8: Commit**

```bash
git add vol-learning-guide/chapters/10-feature-engineering.tex
git commit -m "feat(vol-guide): add 5 feature engineering sections to Ch.10"
```

---

### Task 6: Ch.11 -- DART Boosting Subsection

**Files:**
- Modify: `vol-learning-guide/chapters/11-tree-methods-vol.tex`
- Insert at: line ~722 (after "Ensemble with HAR" section, before Summary)

**Source papers for Pass 0:**
- `reference/project-papers/ke-et-al-2017-lightgbm.pdf` pp.3-5: DART algorithm description, dropout mechanism for trees, comparison with standard GBDT

**Content scope:**
- New subsection: "DART: Dropout Regularization for Boosted Trees"
- Dropout in tree context: randomly drop previous trees during each boosting round
- Why it helps for vol: prevents over-reliance on early trees that capture the dominant HAR-like autoregressive signal, forces later trees to learn independently
- How it differs from standard learning-rate shrinkage
- ~1-2 pages

**Constraints:**
- Do NOT re-explain gradient boosting (already covered earlier in chapter)
- Do NOT re-explain LightGBM basics (already covered)

- [ ] **Step 1: Run Pass 0 -- extract DART algorithm from Ke et al. 2017**
- [ ] **Step 2: Run Pass 1 -- write subsection and insert**
- [ ] **Step 3: Run Pass 2 (verifier) and Pass 3 (condenser) in parallel**
- [ ] **Step 4: Consolidate**
- [ ] **Step 5: Run Pass 4 -- naive reader**
- [ ] **Step 6: Apply feedback**
- [ ] **Step 7: Commit**

```bash
git add vol-learning-guide/chapters/11-tree-methods-vol.tex
git commit -m "feat(vol-guide): add DART boosting subsection to Ch.11"
```

---

### Task 7: Ch.13 -- Ensemble Architecture Comparison Section

**Files:**
- Modify: `vol-learning-guide/chapters/13-hybrid-ensemble.tex`
- Insert at: line ~627 (after Stacking with Ridge Meta-Learner, before "When to Use Pure ML vs. Hybrid" decision section)

**Source papers for Pass 0:**
- `guides/vol-project-ref/chapters/ch16_architecture.tex`: three architecture comparison (feature stacking, residual stacking, prediction blending), tradeoff matrix
- `guides/vol-project-ref/chapters/ch11_ensemble.tex`: prediction blending rationale, Kaggle evidence

**Content scope:**
- New section: "Comparing Ensemble Architectures"
- Feature stacking: LSTM embedding concatenated into LightGBM input. Explain gradient isolation (LightGBM cannot backprop into LSTM, so embedding is never optimized for tree objective). Debugging harder.
- Residual stacking: extend existing HAR-SVR coverage (line 184) to 3-stage (HAR -> LightGBM -> LSTM on residuals). Each model has a distinct role by construction.
- Prediction blending: independent models, weighted average. Static vs regime-dependent weights. Kaggle evidence (Optiver, AmEx).
- Comparison table (booktabs): complexity, gradient flow, interpretability, fallback strategy, literature support
- ~4-5 pages

**Constraints:**
- Do NOT repeat existing HAR-SVR residual stacking content (lines 184-303) -- reference it with \ref and extend
- Do NOT repeat existing stacking with ridge meta-learner (lines 533-627) -- reference it
- Do NOT re-explain HAR or LightGBM basics

- [ ] **Step 1: Run Pass 0 -- extract architecture comparisons from vol-project-ref**
- [ ] **Step 2: Read existing Ch.13 residual stacking and meta-learner sections for context**
- [ ] **Step 3: Run Pass 1 -- write section and insert**
- [ ] **Step 4: Run Pass 2 (verifier) and Pass 3 (condenser) in parallel**
- [ ] **Step 5: Consolidate**
- [ ] **Step 6: Run Pass 4 -- naive reader**
- [ ] **Step 7: Apply feedback**
- [ ] **Step 8: Commit**

```bash
git add vol-learning-guide/chapters/13-hybrid-ensemble.tex
git commit -m "feat(vol-guide): add ensemble architecture comparison to Ch.13"
```

---

### Task 8: Ch.16 -- Retransformation Bias + Lookahead Taxonomy

**Files:**
- Modify: `vol-learning-guide/chapters/16-forecast-evaluation.tex`

**Source papers for Pass 0:**
- `reference/project-papers/patton-2011-volatility-forecast-comparison.pdf` pp.1-8: QLIKE robustness class definition, conditions for noise-robust ranking, retransformation
- `guides/vol-project-ref/chapters/ch13_evaluation.tex`: lookahead bias 4-source taxonomy, walk-forward protocol
- `guides/vol-project-ref/chapters/ch14_complete_pipeline.tex`: lookahead bias prevention table (4 sources with pitfalls and rules)

**Two additions:**

**Addition 1: Retransformation Bias**
- Insert at: line ~222 (after QLIKE comparison with MSE, before Mincer-Zarnowitz section at line 277)
- New subsection explaining the bias from exponentiating log-space forecasts
- Formula: $\widehat{RV}_{t+1} = \exp(\widehat{\log RV}_{t+1} + \hat{\sigma}^2/2)$
- Why this matters: without correction, every forecast is systematically biased low
- ~1-2 pages

**Addition 2: Lookahead Bias Taxonomy**
- Insert at: line ~859 (after existing lookahead warnings, before "Putting It All Together" workflow)
- Explicit enumeration of 4 sources, each with: what goes wrong, concrete example, prevention rule
  1. Realized measures: intraday returns from target day leaking into features
  2. Microstructure: full-day LOB features including close
  3. Options surface: intraday surface changes reflecting target-day info
  4. Cross-asset: mixed frequencies across asset classes
- ~2-3 pages

**Constraints:**
- Do NOT repeat existing QLIKE formula (lines 131-142) or gradient/Hessian (in Ch.11)
- Do NOT repeat purged CV content (already thorough at lines 686-689)
- Do NOT repeat existing event lookahead warning (lines 811-818)

- [ ] **Step 1: Run Pass 0 -- extract retransformation from Patton 2011, lookahead taxonomy from vol-project-ref**
- [ ] **Step 2: Read existing Ch.16 QLIKE and lookahead sections for context**
- [ ] **Step 3: Run Pass 1 -- write both additions and insert at correct locations**
- [ ] **Step 4: Run Pass 2 (verifier) and Pass 3 (condenser) in parallel**
- [ ] **Step 5: Consolidate**
- [ ] **Step 6: Run Pass 4 -- naive reader**
- [ ] **Step 7: Apply feedback**
- [ ] **Step 8: Commit**

```bash
git add vol-learning-guide/chapters/16-forecast-evaluation.tex
git commit -m "feat(vol-guide): add retransformation bias and lookahead taxonomy to Ch.16"
```

---

## Phase 3: Consolidation (sequential, after all Phase 2 tasks complete)

### Task 9: Update main.tex and Final Integration

**Files:**
- Modify: `vol-learning-guide/main.tex`

- [ ] **Step 1: Insert new Rashomon chapter into main.tex**

Add the `\input` line after Ch.11 (line 40), before current Ch.12 (line 41):

```latex
\input{chapters/11-tree-methods-vol}
\input{chapters/12-rashomon-interpretable-trees}
\input{chapters/12-deep-learning-vol}
```

- [ ] **Step 2: Verify LaTeX compiles**

```bash
cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex
```

Check for:
- No undefined references
- No missing citations
- Chapter numbering is correct (Rashomon appears as the right chapter number)
- All new sections appear in table of contents

- [ ] **Step 3: Fix any compilation errors**

Common issues to watch for:
- Missing `\label{}` references from new chapter
- Bib keys that don't match between chapter and references.bib
- TikZ package dependencies not in preamble

- [ ] **Step 4: Commit compiled PDF and any fixes**

```bash
git add vol-learning-guide/main.tex vol-learning-guide/main.pdf
git commit -m "feat(vol-guide): integrate Rashomon chapter into main.tex, recompile"
```

---

### Task 10: Cross-Chapter Reference Check

- [ ] **Step 1: Verify all forward/backward references**

Check that:
- Ch.08 butterfly section has forward ref to Ch.10
- Ch.10 triple expansion is referenced when expanded features appear later in Ch.10
- Ch.10 diminishing returns capstone references all 7 layers by their section labels
- New Rashomon chapter references Ch.11 for tree basics and Ch.10 for feature names
- Ch.13 ensemble section references existing HAR-SVR content (lines 184-303) properly
- Ch.16 retransformation bias references existing QLIKE section properly

- [ ] **Step 2: Final commit**

```bash
git add -A
git commit -m "chore: fix cross-chapter references after gap integration"
```
