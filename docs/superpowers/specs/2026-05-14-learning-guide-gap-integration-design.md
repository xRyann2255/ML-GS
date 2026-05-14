# Learning Guide Gap Integration Design

**Date:** 2026-05-14
**Goal:** Add all content from vol-project-ref that is missing from the vol-learning-guide, with zero theory mistakes guaranteed by a paper-reading-first approach.

---

## Context

A comprehensive audit compared the vol-project-ref (18-chapter project implementation guide) against the vol-learning-guide (17-chapter pedagogical textbook). The audit identified 14 content gaps -- topics the project reference covers that the learning guide either omits entirely or covers too briefly for the reader to understand *why* something is done.

## Constraints

- No duplicating content already in the learning guide (audit verified what exists)
- Every formula, definition, and claim must be verified against the source paper before writing
- Follow existing guide conventions (memoir class, tcolorbox types, natbib, booktabs)
- Use the modified write-chapter skill (5-pass pipeline with Pass 0 source extraction)

---

## Deliverable 1: Modified Write-Chapter Skill

Update `.claude/skills/write-chapter/SKILL.md` to add:

### Pass 0 -- Source Extraction (new, runs before Pass 1)

Before writing begins, the agent reads the specified source papers and produces a structured extraction for each:

```
PAPER: [Author Year] ([short title])
PAGE: [page number]
TYPE: FORMULA | DEFINITION | CLAIM | THRESHOLD
CONTENT: [exact content from paper]
NOTATION: [symbol definitions as used in the paper]
GUIDE_NOTATION: [how to adapt notation to match learning guide conventions]
```

Rules:
- Read only the specific pages/sections relevant to the chapter's topics (not full papers)
- Every formula must include the exact equation number and page from the source
- Every quantitative claim (e.g., "5-15% QLIKE improvement") must have a source
- If a claim appears in vol-project-ref but has no paper backing it, flag it and do not include it

### Mid-Write Paper Discovery (new rule in Pass 1)

If the writer encounters a concept that needs a citation or formula not in the Pass 0 extraction:
1. Search `reference/project-papers/` and `reference/papers/` for relevant papers
2. If found, read the relevant pages and extract the needed material
3. If not found in the repo, search the web for the paper
4. If available (arXiv, open-access proceedings, author websites), download it to `reference/project-papers/`
5. Extract the needed material and continue writing
6. If the paper is behind a paywall and unavailable, note it as a gap and write around it

### Pass 2 Upgrade -- Cross-referencer becomes Verifier

In addition to suggesting citations, the cross-referencer now:
- Re-reads each cited paper's relevant pages
- Verifies every formula in the chapter matches the source (correct signs, terms, notation)
- Flags any discrepancy as CRITICAL
- Checks that quantitative claims match what the paper actually reports

---

## Deliverable 2: New Rashomon Chapter

**File:** `vol-learning-guide/chapters/12-rashomon-interpretable-trees.tex`
**Insert:** After Ch.11 in `main.tex`, before current Ch.12 (Deep Learning)
**LaTeX auto-numbers:** Existing chapter files keep their filenames unchanged.

### Source Papers (Pass 0 reads these)

| Paper | Key Extractions Needed |
|---|---|
| Xin et al. 2022 (TreeFARMS) | Rashomon set definition, enumeration algorithm, set size bounds |
| Donnelly et al. 2023 (RID) | Rashomon Importance Distribution methodology, confidence intervals |
| Dong & Rudin 2020 (VIC) | Variable Importance Clouds definition, overlap interpretation |
| Van den Bos et al. 2024 (STreeD) | Piecewise-linear leaf model, optimization objective |
| Heile & Babbar 2025 (LicketyRESPLIT) | Approximation algorithm, runtime/memory improvements |
| Babbar et al. 2025 (SPLIT) | Near-optimal tree algorithm, speed benchmarks |
| Lundberg & Lee 2017 (SHAP) | SHAP methodology (for contrast with Rashomon approaches) |

### Chapter Outline

1. **Opening** -- Motivate with SHAP instability: VIX vs ATM IV as "most important" feature across refits
2. **Prerequisites box** -- Ch.11 (tree methods), SHAP basics, feature importance concepts
3. **The Problem with Single-Model Explanations** -- Why SHAP importance is unreliable with near-substitute features
4. **The Rashomon Set** -- Definition, epsilon tolerance, "near-optimal" concept. Worked example: two small trees, different features, same accuracy
5. **Optimal Sparse Decision Trees (STreeD)** -- Piecewise-linear leaves vs piecewise-constant. Provably optimal. Depth/leaf tradeoffs. Interpretability advantage over ensemble of 10,000 trees
6. **Enumerating the Rashomon Set** -- TreeFARMS algorithm. SPLIT/RESPLIT speedups. LicketyRESPLIT approximation. Expected set sizes for vol data
7. **Rashomon Importance Distributions (RID)** -- Stable importance across entire set. Confidence intervals. Contrast with bootstrapped SHAP
8. **Variable Importance Clouds (VIC)** -- [min, max] importance range per feature. Non-overlapping = robustly distinct. Overlapping = substitutes. Worked example: VIX/VVIX/ATM IV
9. **Application to Volatility Forecasting** -- Regime-stable feature selection. Prediction multiplicity. Novelty: no published financial time-series application
10. **Project Connection** -- GS defensibility, feature stability, model-choice uncertainty quantification

### Bib Entries to Add

```bibtex
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
```

(XinEtAl2022, DonnellyEtAl2023, DongRudin2020, VanDenBosEtAl2024, Lundberg2017 already in vol-project-ref bib; copy entries to vol-learning-guide bib.)

---

## Deliverable 3: Additions to Existing Chapters

### Ch.08 (Options & Vol Surface) -- 1 new section

**Butterfly Spread as a Volatility Feature**
- Formula: $BF_t = \frac{1}{2}(\sigma_{25\Delta P} + \sigma_{25\Delta C}) - \sigma_{ATM}$
- What it captures vs skew: symmetric tail thickness (kurtosis demand) vs directional asymmetry
- Crisis detection: both wings bid up by portfolio insurance
- Source: verify formula against Rebonato 2004 (in repo)
- Insert after existing smile/skew discussion
- Do NOT duplicate skew content already present

### Ch.10 (Feature Engineering) -- 5 additions

**1. Diminishing Returns Curve** (new section after feature catalog)
- 55% -> 70% -> 85% -> 95% -> 100% staircase across layers L0-L7
- Horizon-dependent table: what dominates at h=1, h=5, h=22
- Key implication: perfect L0-L2 before chasing marginal features
- Sources: HARdToBeat2024 (in repo), ChristensenSiggaardVeliyev2023 (in repo)
- Do NOT repeat individual feature descriptions already in Ch.10

**2. Triple Expansion {level, change, z-score}** (new section in feature construction area)
- Why each variant captures different info: state, momentum, anomaly
- Which features get expanded (continuous) vs not (categorical)
- Tree interaction: no multicollinearity concern
- Worked example: spread -> 3 variants
- Do NOT duplicate any existing feature transforms in Ch.10

**3. VPIN Construction + Kyle's Lambda** (expand existing microstructure subsection)
- VPIN: volume-bucketing algorithm, buyer/seller classification, imbalance
- Kyle's lambda: regress mid-price change on signed volume, slope = price impact
- Sources: Easley et al. 2012 (in repo), Kyle 1985 (in repo)
- Do NOT duplicate price acceleration coverage (already thorough)
- Do NOT duplicate VPIN brief mention -- replace it with thorough treatment

**4. Vol-of-Vol + Regime Duration** (expand existing memory subsection)
- Vol-of-vol: std(RV) over 22 days
- Regime duration: days since last 2-sigma spike, mean-reversion clock
- Complement existing fractional differencing coverage
- Do NOT repeat fractional differencing (d ~ 0.35-0.45 already covered thoroughly)

**5. Calendar Proximity Measures** (expand existing calendar subsection)
- Continuous proximity (days-to-event) vs binary dummies
- FOMC compression/expansion, OpEx gamma unwind, earnings proximity
- Do NOT repeat existing calendar skeleton -- extend it

### Ch.11 (Tree Methods) -- 1 new subsection

**DART Boosting**
- Dropout in tree context: randomly drop previous trees during boosting
- Why it helps for vol: prevents over-reliance on early HAR-signal trees
- Difference from standard shrinkage
- Source: Ke et al. 2017 (in repo)
- Small subsection, ~1-2 pages

### Ch.13 (Hybrid/Ensemble) -- 1 new section

**Comparing Ensemble Architectures**
- Feature stacking: LSTM embedding into LightGBM, gradient isolation problem
- Residual stacking: extend existing coverage to 3-stage (HAR -> LightGBM -> LSTM)
- Prediction blending: independent models, weighted average, Kaggle evidence
- Comparison table: complexity, gradient flow, interpretability, fallback, literature support
- Static vs regime-dependent weights
- Do NOT repeat existing residual stacking content -- reference and extend
- Sources: Optiver2021 (competition evidence), existing Ch.13 content

### Ch.16 (Forecast Evaluation) -- 2 additions

**1. Retransformation Bias** (new subsection near QLIKE discussion)
- Problem: log-space forecast -> exp() introduces systematic downward bias
- Fix: $\widehat{RV}_{t+1} = \exp(\widehat{\log RV}_{t+1} + \hat{\sigma}^2/2)$
- Source: Patton 2011 (in repo)
- Do NOT repeat existing QLIKE formula or gradient/Hessian (already thorough)

**2. Lookahead Bias Taxonomy** (expand existing section)
- Enumerate 4 specific sources with concrete examples:
  1. Realized measures: target-day intraday returns leaking into features
  2. Microstructure: full-day LOB features including close
  3. Options surface: intraday surface changes reflecting target-day info
  4. Cross-asset: mixed frequencies across asset classes
- Each gets: what goes wrong, the rule to prevent it
- Do NOT repeat purged CV content (already thorough)

---

## Paper-to-Deliverable Matrix

| Paper | Rashomon Ch. | Ch.08 | Ch.10 | Ch.11 | Ch.13 | Ch.16 |
|---|---|---|---|---|---|---|
| Xin et al. 2022 (TreeFARMS) | PRIMARY | | | | | |
| Donnelly et al. 2023 (RID) | PRIMARY | | | | | |
| Dong & Rudin 2020 (VIC) | PRIMARY | | | | | |
| Van den Bos et al. 2024 (STreeD) | PRIMARY | | | | | |
| Heile & Babbar 2025 (LicketyRESPLIT) | PRIMARY | | | | | |
| Babbar et al. 2025 (SPLIT) | PRIMARY | | | | | |
| Lundberg & Lee 2017 (SHAP) | CONTRAST | | | | | |
| Rebonato 2004 | | verify | | | | |
| HARdToBeat2024 | | | source | | | |
| Christensen et al. 2023 | | | source | | | |
| Easley et al. 2012 (VPIN) | | | source | | | |
| Kyle 1985 | | | source | | | |
| Ke et al. 2017 (LightGBM) | | | | source | | |
| Patton 2011 | | | | | | source |
| Optiver 2021 | | | | | evidence | |

---

## Execution Strategy

All chapters/additions written via subagent-driven development using Opus 4.6 subagents. Each deliverable is independent and can run in parallel:

1. Modify write-chapter skill (prerequisite for all others)
2. Dispatch parallel subagents for each chapter/addition using modified skill
3. Each subagent runs the full 5-pass pipeline (Pass 0 extraction -> Pass 1 write -> Pass 2 verify -> Pass 3 condense -> Pass 4 naive reader -> Final)
4. Main agent consolidates, updates main.tex, updates references.bib, commits

### Parallelization Groups

All are independent and can run simultaneously:
- New Rashomon chapter
- Ch.08 butterfly section
- Ch.10 additions (all 5 as one unit -- they're in the same file)
- Ch.11 DART subsection
- Ch.13 ensemble architecture section
- Ch.16 additions (both as one unit -- same file)
