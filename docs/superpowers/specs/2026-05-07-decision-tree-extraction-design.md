# Design: Decision Tree Deep Research Extraction Pipeline

**Date**: 2026-05-07
**Source**: Brainstorming session on extracting decision tree research output
**Prior art**: `docs/superpowers/specs/2026-05-06-research-extraction-design.md` (vol extraction)

---

## Problem

`notes/deep-research-decision-trees.md` is a 337-line deep research output covering the state of the art in optimal decision trees, Rashomon sets, and their applicability to financial time-series regression. It contains ~60 inline paper citations, an applicability assessment for the vol forecasting project, staged recommendations, and caveats. This content needs to be decomposed into the repo's existing structure: bibliography entries appended, feature findings routed to the right files, project proposals enriched, and the research index updated.

Unlike the vol extraction (which had a standalone Part 3 annotated bibliography), all citations here are inline within the landscape survey prose. The bibliography already exists with ~89 entries from the vol extraction; this extraction appends to it rather than rewriting.

## Approach

One-pass decomposition mirroring the vol extraction pipeline: append new bibliography entries, enrich existing stubs, append feature findings, update project proposals, update research index, trim source file.

## Outputs

### 1. Bibliography -- append to `reference/bibliography.md`

**Action**: Append new entries to existing category H ("Rashomon Sets and Optimal Sparse Decision Trees"), enrich existing stubs with deeper detail from this research, add new topic tags to the controlled vocabulary.

**No archiving needed**: the bibliography is already the vol-project version (quant-trading canon was archived on 2026-05-06).

#### Existing H entries to enrich (12 entries)

These entries were created during the vol extraction with less detail than this research provides. Update their fields (Key finding, Relevance, Topics, Venue) with the richer information from the decision tree research:

| Slug | What to update |
|---|---|
| `lin-etal-2020-gosdt` | Add: continuous features via threshold guessing, depth limit (2022), GOSDT-Guesses connection, `pip install gosdt`, 57 GitHub stars |
| `aglin-etal-2020-demirovic-2022` | **Split into two entries**: `aglin-etal-2020-dl85` (DL8.5, AAAI 2020, caching branch-and-bound) and `demirovic-etal-2022-murtree` (MurTree, JMLR 2022, depth-2 specialized solver, 10pp greedy-optimal gap). These are different papers at different venues. Remove the original combined entry. |
| `van-der-linden-etal-2023-streed` | Add: separable-objective framework (necessary and sufficient conditions for DP), subsumes classification/regression/fairness/survival/policy. Venues: NeurIPS 2023, ICML 2024, AAAI 2025. `pip install pystreed` |
| `babbar-etal-2025-split` | Add: Theorem A.1 (provably >= greedy), Corollary 6.3 (O(k^((d-1)/2) * (d/2)!) speedup), Theorem 6.5 (existence of distributions where SPLIT >> greedy). LicketySPLIT polynomial O(\|R\|*n*k^3*d^3). RESPLIT for Rashomon sets. 100x faster than GOSDT. Verify title against ICML 2025 camera-ready before changing. |
| `heile-etal-2025-licketyresplit` | Add: polynomial-time approximation, ~74x faster than TreeFARMS on Bike, ~17x on Spambase, recovers nearly the full Rashomon set |
| `arslan-etal-2025-sorted` | Fix title to "SORTeD: Anytime Enumeration of Rashomon Trees in Objective Order". Add: ordered enumeration (best trees first), anytime termination, 100x faster than TreeFARMS/RESPLIT, supports any separable objective (works for regression/survival via STreeD) |
| `semenova-rudin-parr-2022` | Fix title to "On the Existence of Simpler Machine Learning Models". Add: Rashomon ratio definition, large ratio guarantees simpler models exist |
| `xin-etal-2022-treefarms` | Enrich Key finding with: first complete enumeration of any non-trivial hypothesis class; trie-based data structure; outperforms BART/MCMC samplers by orders of magnitude; applications to VIC, derived-metric Rashomon sets, bootstrap Rashomon sets. Add `pip install treefarms`, 47 GitHub stars |
| `dong-rudin-2020` | Enrich Key finding with: maps every variable to Model Reliance importance for every good model; used with TreeFARMS reveals interchangeable vs. uniquely important features. Add Shapley-VIC extension (Ning et al. 2022) |
| `rudin-etal-2024-position` | Enrich with the six specific benefits: (1) simpler-yet-accurate models, (2) fairness/monotonicity flexibility, (3) uncertainty quantification, (4) reliable variable importance, (5) algorithm-choice diagnostics, (6) public-policy applications. Reframes ML as feasibility problem |
| `mctavish-etal-2025` | Enrich with: predictive equivalence via boolean-logical canonicalization; two trees can encode same decision boundary but differ in evaluation order, affecting variable importance and missing-value handling. Topics: add `interpretability` |
| `marx-calmon-ustun-2020` | Enrich Key finding with: formalizes predictive multiplicity as degree to which competing models disagree on individual predictions; proposes metrics (ambiguity, discrepancy) |

#### New entries (~50 papers)

Extract inline citations from sections A-H and Part 2 that are not already in the bibliography. Each entry uses the same format as existing entries (slug ID, Title, Authors, Year, Venue, Quality, Topics, PDF, Key finding, Relevance).

**Slug ID rules** (same as vol extraction): `authorlist-year` with up to 3 last names, `etal` if more. Disambiguate with title keyword if needed. For hyphenated surnames (e.g., Carreira-Perpinan, Barndorff-Nielsen), treat the full hyphenated name as one author name in the slug.

Papers to add, grouped by topic within category H:

**Greedy baselines and NP-hardness:**
- `hyafil-rivest-1976` -- NP-completeness of optimal binary decision trees
- `breiman-etal-1984-cart` -- CART (Classification and Regression Trees)
- `quinlan-1993-c45` -- C4.5
- `murthy-salzberg-1995` -- empirical documentation of greedy myopia

**Early exact methods (MIP, CP, SAT):**
- `bertsimas-dunn-2017` -- OCT (MIP with oblique splits)
- `verwer-zhang-2019` -- BinOCT (binary linear program)
- `verhaeghe-etal-2020` -- Constraint Programming for decision trees
- `narodytska-etal-2018` -- MaxSAT-based decision trees
- `hu-siala-etal-2020` -- MaxSAT IJCAI variant

**Modern optimal-tree algorithms:**
- `hu-rudin-seltzer-2019-osdt` -- OSDT (first practical optimal sparse decision tree)
- `mctavish-etal-2022-gosdt-guesses` -- GOSDT-Guesses (threshold guessing, distillation)
- `demirovic-hebrard-jean-2023-blossom` -- Blossom (anytime, depth-first expansion)
- `mazumder-meng-wang-2022` -- Quant-BnB (BnB on quantiles)
- `zhang-xin-seltzer-rudin-2023-osrt` -- OSRT (optimal sparse regression trees)
- `zhang-xin-seltzer-rudin-2024-survival` -- Optimal Sparse Survival Trees
- `sullivan-tiwari-thrun-2024` -- MAPTree (Bayesian MAP via AND/OR search)
- `aghaei-gomez-vayanos-2024` -- Strong Optimal Classification Trees (max-flow MIP)
- `van-der-linden-etal-2025-benchmark` -- Definitive 180-dataset benchmark (arXiv:2409.12788)
- `brita-van-der-linden-demirovic-2025` -- ConTree (continuous features without binarization)

**STreeD extensions:**
- `van-den-bos-van-der-linden-demirovic-2024` -- Piecewise-linear regression trees (elastic-net leaves)
- `huisman-van-der-linden-demirovic-2024` -- Optimal Survival Trees
- `van-der-linden-etal-2022-fair` -- Fair STreeD (group-fairness Pareto front)
- `van-der-linden-etal-2023-policy` -- Prescriptive policy trees
- `demirovic-stuckey-2021` -- Cost-sensitive classification via DP

**Rashomon additions:**
- `semenova-chen-parr-rudin-2023` -- Noise inflates Rashomon ratio (NeurIPS 2023)
- `donnelly-katta-rudin-browne-2023` -- RID: Rashomon Importance Distribution (NeurIPS 2023)
- `ning-etal-2022` -- Shapley-VIC (Patterns 2022)
- `zhong-etal-2023-gam` -- Sparse GAM Rashomon sets (NeurIPS 2023)
- `liu-etal-2022-fasterrisk` -- FasterRisk sparse risk scores (NeurIPS 2022)
- `coker-rudin-king-2021` -- Linear model Rashomon sets (Management Science)
- `donnelly-etal-2025-cvpr` -- Prototype-part network Rashomon sets (CVPR 2025)
- `hsu-calmon-2022` -- Rashomon Capacity (NeurIPS 2022)

**Ensemble methods and tabular ML:**
- `chen-guestrin-2016` -- XGBoost
- `ke-etal-2017` -- LightGBM (GOSS, EFB)
- `prokhorenkova-etal-2018` -- CatBoost (ordered boosting, oblivious trees)
- `grinsztajn-oyallon-varoquaux-2022` -- Why trees beat deep learning on tabular data (NeurIPS 2022)
- `carreira-perpinnan-tavallali-2018` -- TAO (Tree Alternating Optimization)
- `carreira-perpinnan-tavallali-2023-fao` -- FAO: Forest Alternating Optimization (CVPR 2023)

**Interpretability:**
- `rudin-2019` -- "Stop Explaining Black Box Models" (Nature MI)
- `rudin-etal-2022-survey` -- Interpretable ML survey (Statistics Surveys)
- `costa-pedreira-2023` -- Tree interpretability survey (Information Fusion)
- `aghaei-azizi-vayanos-2019` -- FairTree (MIP-based)
- `jo-etal-2023` -- FAccT fairness trees

**Neural-tree hybrids:**
- `popov-morozov-babenko-2020` -- NODE (Neural Oblivious Decision Ensembles, ICLR)
- `arik-pfister-2021` -- TabNet (AAAI)

**Regression trees and predecessors:**
- `quinlan-1992-m5` -- M5/Cubist greedy linear-leaf trees (predecessor to STreeD piecewise-linear)
- `meinshausen-2006` -- Quantile Regression Forests (JMLR)
- `lemaire-aglin-nijssen-2024` -- Optimal interpretable quantile regression trees (IDA)
- `chatterjee-goswami-2021` -- Dyadic CART optimal rates (Annals of Statistics)
- `donoho-1997` -- Dyadic CART theoretical risk bounds (piecewise-constant, bounded-variation)

**Foundational (cited but historical):**
- `nijssen-fromont-2007` -- DL8 (KDD 2007, ancestor of DL8.5)

**Theory (parameterized complexity):**
- `komusiewicz-etal-2023` -- Optimal tree ensembles parameterized complexity (ICML)
- `ordyniak-szeider-2021` -- FPT results for decision trees
- `eiben-etal-2023` -- Parameterized complexity of tree learning
- `gahlawat-zehavi-2024` -- W-hardness results

**New topic tags** to add to controlled vocabulary: `regression-trees`, `interpretability`, `tabular-ml`, `fairness`, `distillation`, `survival-trees`, `quantile-trees`, `np-hardness`

#### Deduplication rules

- Do **not** create entries for papers already in the bibliography under a different slug. Cross-check the existing ~89 entries before adding.
- The following entries already exist in the bibliography and must NOT be duplicated. They are listed in the "Existing H entries to enrich" table above and should be enriched in-place:
  - `xin-etal-2022-treefarms` (category H, line 681)
  - `dong-rudin-2020` (category H, line 736)
  - `rudin-etal-2024-position` (category H, line 747)
  - `mctavish-etal-2025` (category H, line 758) -- covers predictive equivalence; do NOT create a separate `mctavish-boner-etal-2025-equiv` entry
  - `marx-calmon-ustun-2020` (category H, line 769)
- The `christensen-siggaard-veliyev-2023` entry already exists in category D -- do not duplicate it in H, but reference its slug in feature file appends.
- `lopez-de-prado-2018` already exists in category G -- do not duplicate.
- `breiman-2001` already exists in category H -- do not duplicate.
- The combined `aglin-etal-2020-demirovic-2022` entry must be split into two new entries; the original combined entry is removed.

### 2. Feature findings -- append to `notes/features/*.md`

#### `notes/features/optimal-feature-set.md` -- Append

**Check for overlap first.** The file already has a `## Deep Research Findings (2026-05-06)` section (lines 267-281) covering VIC basics and feature construction pitfalls. The new content from the decision tree research is **more detailed and specific** on Rashomon applications. Append as a separate dated section.

New section `## Deep Research Findings (2026-05-07)`:

| Source (decision tree research) | Content to append |
|---|---|
| Part 2 Section 2.2 "Where Rashomon-set analysis adds value" | Feature interchangeability detection: VIX/V2X/VVIX/MOVE near-substitutes; RID delivers stable importance distribution; VIC visualizes substitution structure directly |
| Part 2 Section 2.2 | Regime-stable model selection: train TreeFARMS/RESPLIT on rolling-window data; intersect Rashomon sets across regimes for robust non-stationary models |
| Part 2 Section 2.2 | Ex-ante stress testing: prediction multiplicity quantifies range across defensible models |
| Part 2 Section 2.2 | Constraint satisfaction post-hoc: filter Rashomon set for monotonicity (VIX up -> RV up) without retraining |
| Part 2 Section 2.4 | 7-step pipeline: feature engineering -> binarization (GOSDT-Guesses, ~300 binary) -> log(RV) target -> STreeD piecewise-linear depth <=5 -> Rashomon analysis (epsilon=2% MSE) -> walk-forward evaluation -> production |
| Part 2 Section 2.5 | Novelty confirmation: no published application of optimal trees or Rashomon sets to financial time-series as of May 2026 |

#### `notes/features/har-components.md` -- Append

Brief addition to contextualize where interpretable optimal trees sit relative to HAR and ensemble baselines:

| Source | Content to append |
|---|---|
| Part 2 Section 2.3 | Christensen et al. 2023: bagging at relative MSE 0.891 vs HAR 1.000; gradient boosting 0.958; RF 0.986. With full features: RF 0.901, NN ensembles 0.885-0.944 |
| Part 2 Section 2.3 | Best estimate for optimal trees: depth-4-5 STreeD piecewise-linear should achieve ~2-5% higher MSE than tuned LightGBM, while remaining a single inspectable 8-32 leaf tree |
| Part 2 Section 2.3 | Interpretable optimal tree should comfortably beat HAR (bagging beats HAR by ~10% on 5-min RV) |

### 3. Project proposals -- append to `notes/project-proposals.md`

**Append** a new section at the end of the file enriching Project 3 (Rashomon Volatility) with the decision tree research's applicability assessment and implementation roadmap.

New section `## Decision Tree Methodology Assessment (2026-05-07)`:

| Source | Content |
|---|---|
| Part 2 Section 2.1 | Recommended methods priority: (1) STreeD piecewise-linear regression, (2) OSRT, (3) STreeD piecewise-constant, (4) ConTree for classification framings, (5) SPLIT/LicketySPLIT. Avoid: pure MIP, pure SAT, Quant-BnB beyond depth 3 |
| Part 2 Section 2.1 | Binarization recipe: GOSDT-Guesses LightGBM threshold guesser, cap ~300 binary features |
| Recommendations | 4-stage roadmap: baseline & feasibility (week 1-2) -> optimal-tree drop-in (week 2-4) -> Rashomon-set analysis (week 4-8) -> paper/production. With escalation thresholds |
| Recommendations | Default if time-constrained: STreeD piecewise-linear depth 4 + monotonicity + TreeFARMS RID = 80% value at <20% effort |
| Caveats | All 10 caveats from decision tree research (complement the 8 from vol research) |

### 4. Research index -- append to `notes/research-index.md`

Add a new entry below the existing 2026-05-06 entry:

```markdown
## 2026-05-07: State of the Art in Decision Trees

- **Source prompt**: `notes/deep-research-prompt-decision-trees.md`
- **Raw output**: `notes/deep-research-decision-trees.md` (trimmed to landscape survey after extraction)
- **Extracted to**:
  - `reference/bibliography.md` -- ~50 new entries in category H, 12 existing entries enriched, 8 new topic tags
  - `notes/project-proposals.md` -- decision tree methodology assessment, implementation roadmap, 10 caveats
  - `notes/features/optimal-feature-set.md` -- Rashomon pipeline design, feature interchangeability, novelty confirmation
  - `notes/features/har-components.md` -- accuracy comparison (optimal trees vs HAR vs LightGBM)
```

### 5. Source file trimming -- `notes/deep-research-decision-trees.md`

**Kept**: Executive Summary (lines 1-11), separator (line 13), Sections A-H landscape survey (lines 15-224).

**Removed**: Everything from the `---` separator before Part 2 onwards (lines 226-337): Part 2 "Applicability Assessment" (starts line 228), "Recommendations" (starts line 312), "Caveats" (starts line 326). Work bottom-up to preserve line numbers.

**Added** after Executive Summary:

```markdown
---
> **Bibliography**: entries appended to `reference/bibliography.md` (category H)
> **Project proposals**: methodology assessment appended to `notes/project-proposals.md`
> **Research index**: `notes/research-index.md`
---
```

## Files created or modified

| File | Action |
|---|---|
| `reference/bibliography.md` | **Modify** -- enrich 12 existing H entries, add ~50 new entries, add topic tags |
| `notes/features/optimal-feature-set.md` | **Append** |
| `notes/features/har-components.md` | **Append** |
| `notes/project-proposals.md` | **Append** |
| `notes/research-index.md` | **Append** |
| `notes/deep-research-decision-trees.md` | **Trim** (remove extracted sections, add cross-references) |

## Execution order

1. Bibliography modifications (largest piece -- enrich existing + add new entries + update tags)
2. Feature file appends (independent of each other, read each first to check overlap)
3. Project proposals append (independent)
4. Research index append (independent)
5. Trim source file (last, after everything is extracted)

Steps 1-4 are independent and can be parallelized (after verifying no file conflicts). Assumption: feature file appends do not reference any slug being renamed or split by step 1. This holds for the current spec (feature appends reference `christensen-siggaard-veliyev-2023` which is in category D, untouched by the H-category enrichments).

## Decisions

- Existing bibliography entries are enriched in-place rather than duplicated. The combined `aglin-etal-2020-demirovic-2022` entry is split into two separate entries.
- No new bibliography categories beyond H are created -- all decision tree content belongs in H. Ensemble methods (XGBoost, LightGBM, CatBoost) are placed in H because they appear as comparison baselines for optimal trees, not as standalone vol methods.
- Feature file appends use a separate dated heading (`2026-05-07`) from the existing vol extraction findings (`2026-05-06`).
- The `christensen-siggaard-veliyev-2023` entry already exists in category D and is not duplicated -- referenced by slug only in feature appends.
- The accuracy cost estimate (2-5% MSE penalty) is explicitly marked as extrapolated/speculative in both the feature append and the project proposals update.
