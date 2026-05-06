# Deep Research Extraction Pipeline -- Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decompose `notes/deep-research-vol-papers.md` into the repo's existing structure: bibliography, feature notes, project proposals, and research index.

**Architecture:** Content extraction, not code. Each task reads specific line ranges from the source file and writes/appends to target files. The source file is trimmed last after all extractions are complete.

**Spec:** `docs/superpowers/specs/2026-05-06-research-extraction-design.md`

**Source file structure** (line ranges for reference):
- Lines 1-8: TL;DR (KEEP)
- Lines 10-14: Key Findings (KEEP)
- Lines 16-148: Part 1 Landscape Survey sections A-H (KEEP)
- Lines 150-215: Part 2 Project Proposals (EXTRACT to `notes/project-proposals.md`)
- Lines 218-319: Part 3 Annotated Bibliography sections A-K (EXTRACT to `reference/bibliography.md`)
- Lines 322-345: Recommendations (EXTRACT to `notes/project-proposals.md`)
- Lines 349-365: Caveats (EXTRACT to `notes/project-proposals.md`)

---

## Chunk 1: Independent file creations

### Task 1: Archive existing bibliography

**Files:**
- Read: `reference/bibliography.md`
- Create: `reference/bibliography-quant-trading-canon.md`

- [ ] **Step 1: Copy current bibliography to archive**

Copy the full content of `reference/bibliography.md` (currently ~330 lines of quant-trading canon) to `reference/bibliography-quant-trading-canon.md`. Add a note at the top:

```markdown
# Quant Trading Canon Bibliography (Archived)

> Archived from `reference/bibliography.md` on 2026-05-06. Replaced by vol-project bibliography.
> Original content preserved below.

---

[original content unchanged]
```

- [ ] **Step 2: Commit**

```bash
git add reference/bibliography-quant-trading-canon.md
git commit -m "chore: archive quant-trading bibliography before vol-project rewrite"
```

---

### Task 2: Create bibliography -- `reference/bibliography.md`

**Files:**
- Read: `notes/deep-research-vol-papers.md` (lines 218-319, Part 3 bibliography)
- Read: `reference/project-papers/README.md` (for PDF cross-references and stub entries)
- Create: `reference/bibliography.md`

This is the largest task. Extract every citation from Part 3 sections A-K and format each as a structured entry.

- [ ] **Step 1: Build the bibliography file**

Create `reference/bibliography.md` with this structure:

```markdown
# Bibliography -- ML for Realized Volatility Forecasting

Master catalog of papers, repos, and resources for the vol forecasting project. Optimized for LLM consumption: consistent fields, greppable, one heading per entry.

> **Slug IDs** use `authorlist-year` format (up to 3 authors). Disambiguated with title keyword when needed.
> **Quality**: essential / recommended / optional
> **Topics**: controlled vocabulary tags (see bottom of file)

## Table of Contents

- [A. RV Estimators and Theory](#a-rv-estimators-and-theory)
- [B. HAR Family and Econometric Baselines](#b-har-family-and-econometric-baselines)
- [C. Rough Volatility](#c-rough-volatility)
- [D. ML for Volatility (Empirical)](#d-ml-for-volatility-empirical)
- [E. LOB Deep Learning](#e-lob-deep-learning)
- [F. Variance Risk Premium and Options](#f-variance-risk-premium-and-options)
- [G. Forecast Evaluation and Validation](#g-forecast-evaluation-and-validation)
- [H. Rashomon Sets and Optimal Decision Trees](#h-rashomon-sets-and-optimal-decision-trees)
- [I. Deep Time-Series Architectures](#i-deep-time-series-architectures)
- [J. Code Repos and Data Sources](#j-code-repos-and-data-sources)
- [K. Practitioner and Industry Resources](#k-practitioner-and-industry-resources)
- [Topic Tag Vocabulary](#topic-tag-vocabulary)
```

Then extract each citation from the research file's Part 3 (lines 218-319) into the structured entry format. For each entry:

1. Parse the citation line from the research file
2. Generate a slug ID: `authorlist-year` with up to 3 last names, `etal` if more
3. Fill all fields: Title, Authors, Year, Venue, Quality (normalize to 3 values), Topics (from controlled vocabulary), PDF (cross-reference against `reference/project-papers/README.md`), Key finding, Relevance
4. Also include vol-relevant entries from the archived quant-trading canon: `lopez-de-prado-2018` (AFML), `bennett-2014` (Trading Volatility), `cartea-jaimungal-penalva-2015` (Algorithmic and HF Trading)

For papers that appear in `reference/project-papers/README.md` but NOT in the research file's bibliography (check the README for any that were missed), add stub entries:

```markdown
### stub-slug-id
- **Title**: [from README table]
- **Authors**: [from README table]
- **Year**: [from README table]
- **Venue**: [from README table]
- **Quality**: recommended
- **Topics**: [best guess from README category]
- **PDF**: `reference/project-papers/filename.pdf`
- **Key finding**: stub -- enrich from paper abstract
- **Relevance**: stub -- enrich from paper abstract
```

End the file with the controlled vocabulary:

```markdown
---

## Topic Tag Vocabulary

`rv-estimators`, `microstructure-noise`, `jump-detection`, `har`, `harq`, `har-extensions`, `garch`, `realized-garch`, `rough-vol`, `ml-vol`, `gradient-boosting`, `neural-nets`, `deep-learning`, `lstm`, `cnn-tcn`, `transformers`, `gnn`, `ensemble`, `rashomon`, `optimal-trees`, `lob`, `vrp`, `options-implied`, `cross-asset`, `spillovers`, `evaluation`, `qlike`, `mcs`, `validation`, `purged-cv`, `feature-engineering`, `long-memory`, `sentiment`, `regime`, `data-source`, `code-repo`, `foundational`
```

- [ ] **Step 2: Verify entry count**

Count the `###` headings in the new bibliography. Should be ~80-90 entries. Cross-check that every citation from Part 3 sections A-K has an entry, and that every PDF in `reference/project-papers/` has a corresponding entry.

- [ ] **Step 3: Commit**

```bash
git add reference/bibliography.md
git commit -m "feat: create LLM-parseable bibliography from deep research output (~80 entries)"
```

---

### Task 3: Create project proposals -- `notes/project-proposals.md`

**Files:**
- Read: `notes/deep-research-vol-papers.md` (lines 150-215 for proposals, 322-345 for recommendations, 349-365 for caveats)
- Create: `notes/project-proposals.md`

- [ ] **Step 1: Extract and assemble**

Create `notes/project-proposals.md` with this structure:

```markdown
# Project Direction Proposals

> Source: deep research survey (2026-05-06)
> Full landscape survey: `notes/deep-research-vol-papers.md`
> Bibliography: `reference/bibliography.md`

## Recommendation

[Extract the TL;DR's third bullet point (line 6) as the recommendation summary]

[Extract "Recommendations" section (lines 322-345) -- the staged next steps, decision points, and benchmarks]
```

Then extract each project proposal (lines 154-215) as its own section:

```markdown
## Project 1: HAR-X-Boost (Safe)
[lines 154-163, as-is]

## Project 2: Neural HAR with Rough-Vol Prior (Moderate)
[lines 165-174, as-is]

## Project 3: Rashomon Volatility (Recommended Flagship)
[lines 176-203, as-is]

## Project 4: Cross-Asset Volatility GNN (Ambitious)
[lines 205-215, as-is]
```

Then:

```markdown
## Caveats
[lines 349-365, all 8 caveats, as-is]
```

Fix internal cross-references: any occurrence of "See Project 3 in Part 2" or similar becomes "See Project 3 below."

- [ ] **Step 2: Verify extraction completeness**

Confirm the file contains: (a) all 4 project proposals with their full content (pitch, what it does, trading-floor relevance, data, ML, baseline, feasibility, risk, wow factor, novelty), (b) the recommendations section with staged next steps and decision benchmarks, (c) all 8 numbered caveats.

- [ ] **Step 3: Commit**

```bash
git add notes/project-proposals.md
git commit -m "feat: extract project proposals from deep research output"
```

---

### Task 4: Create calendar-events feature file -- `notes/features/calendar-events.md`

**Files:**
- Read: `notes/deep-research-vol-papers.md` (line 107 for calendar features)
- Create: `notes/features/calendar-events.md`

- [ ] **Step 1: Create the file**

```markdown
# Calendar and Event Features

Features related to scheduled events, macro releases, and their impact on volatility.

## Questions to Answer

- How much do FOMC dates, earnings, and macro releases improve vol forecasts beyond HAR?
- Is a simple binary calendar dummy sufficient, or do you need distance-to-event features?
- How do expiration dates (monthly/quarterly opex) affect next-day RV?

## Deep Research Findings (2026-05-06)

- Calendar/event features include: day of week, holiday proximity, FOMC dates, earnings announcement dates, macro release calendars
- Lee 2012 shows earnings announcements almost always trigger jumps -- earnings dates are among the most reliable event-driven vol signals
- These features are "Layer 5" in the optimal feature set -- important for regime-aware models but secondary to HAR core, asymmetry, and implied-vol features
```

- [ ] **Step 2: Commit**

```bash
git add notes/features/calendar-events.md
git commit -m "feat: add calendar-events feature exploration file"
```

---

### Task 5: Create research index -- `notes/research-index.md`

**Files:**
- Create: `notes/research-index.md`

- [ ] **Step 1: Create the file**

Write this file. The exact list of "Extracted to" targets should match all files actually modified/created in this plan:

```markdown
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
  - `notes/features/calendar-events.md` -- NEW: FOMC, earnings, macro releases, expiration dates
```

- [ ] **Step 2: Commit**

```bash
git add notes/research-index.md
git commit -m "feat: add research index for tracking deep research extractions"
```

---

## Chunk 2: Feature file appends

### Task 6: Append to `notes/features/har-components.md`

**Files:**
- Read + Append: `notes/features/har-components.md` (currently 13 lines)
- Source: `notes/deep-research-vol-papers.md` lines 99-108 (Section D items 1, 6), lines 94-97 (Section C6 horizon verdict)

- [ ] **Step 1: Append findings**

Append to the end of `notes/features/har-components.md`:

```markdown

## Deep Research Findings (2026-05-06)

**Realized higher moments as predictors:**
- Amaya, Christoffersen, Jacobs & Vasquez (2015, JFE): realized skewness and realized kurtosis have predictive power for future RV beyond the standard HAR components (`amaya-christoffersen-jacobs-etal-2015` in bibliography)
- Signed jump variation J = RS+ - RS- provides a directional decomposition of jump activity

**Long memory and fractional differencing:**
- Lopez de Prado (AFML Ch. 5): fractional differencing of RV series preserves long memory while ensuring stationarity -- important preprocessing step for ML models that assume stationarity (`lopez-de-prado-2018` in bibliography)
- Long memory is the core mechanism HAR exploits; ML models that approximate long memory well (gradient boosting, deep nets with dilated convolutions) show the largest gains at longer horizons

**ML horizon findings (Section C6 honest verdict):**
- Daily: HARQ + signed semivariances is very hard to beat by more than a few percent QLIKE
- Weekly/monthly: ML models with long memory start to show meaningful gains per Christensen-Siggaard-Veliyev 2023 (`christensen-siggaard-veliyev-2023` in bibliography)
- Intraday (10-30 min): ML + LOB features can produce real gains; this is the Optiver-Kaggle / DeepLOB regime
```

- [ ] **Step 2: Commit**

```bash
git add notes/features/har-components.md
git commit -m "docs: append deep research findings to har-components feature notes"
```

---

### Task 7: Append to `notes/features/implied-vol.md`

**Files:**
- Read + Append: `notes/features/implied-vol.md` (currently 14 lines)
- Source: `notes/deep-research-vol-papers.md` lines 104 (Section D item 2), lines 113-118 (Section E)

- [ ] **Step 1: Append findings**

Append to end of `notes/features/implied-vol.md`:

```markdown

## Deep Research Findings (2026-05-06)

**VRP construction and predictiveness:**
- Variance risk premium: VRP = IV^2 - RV^2 (approximated as VIX^2 - E_t[RV_{t+1,t+30}])
- Bollerslev, Tauchen & Zhou (2009, RFS): VRP explains >15% of S&P 500 quarterly excess return variation 1990-2005 (`bollerslev-tauchen-zhou-2009` in bibliography)
- Bekaert & Hoerova (2014, J. Econometrics): VRP decomposition into risk and uncertainty components
- VRP is predictive of both returns and future vol, but relatively under-explored with ML methods

**VIX term structure features:**
- VIX level, VIX term structure slope and curvature as features
- Risk-neutral skewness from Bakshi, Kapadia & Madan (2003) -- captures tail risk expectations
- VVIX (vol-of-vol): direct CBOE index; matters for delta-neutral options strategies (gamma scalping P&L variance)

**Rough vol and VRP:**
- Rough volatility models naturally generate steep IV skew and large VRP
- Cont & Das (2024) critique is the frontier -- observed roughness may be a microstructure noise artefact, not a property of true vol (`cont-das-2024` in bibliography)

**ML on VRP:**
- Relatively under-explored. Bali, Hu, Murray (2019) and others use RF/XGBoost on VRP-conditioned features for return prediction, but not VRP forecasting itself -- potential gap to exploit
```

- [ ] **Step 2: Commit**

```bash
git add notes/features/implied-vol.md
git commit -m "docs: append deep research findings to implied-vol feature notes"
```

---

### Task 8: Append to `notes/features/microstructure.md`

**Files:**
- Read + Append: `notes/features/microstructure.md` (currently 25 lines)
- Source: `notes/deep-research-vol-papers.md` lines 105 (Section D item 3), line 109 (Section D item 7 sentiment)

- [ ] **Step 1: Append findings**

Append to end of `notes/features/microstructure.md`:

```markdown

## Deep Research Findings (2026-05-06)

**LOB features -- strongest empirical evidence:**
- Rahimikia & Poon (2020): ML models with LOB features outperform HAR in 90% of OOS days for 23 NASDAQ tickers (2007-2016). Dominant features: mid prices, mean bids, and mean asks (`rahimikia-poon-2020` in bibliography)
- Exception: performance degrades during extreme volatility days
- Cont, Kukanov & Stoikov (2014): order flow imbalance as a predictor -- captures the information content of order arrivals

**Key microstructure features identified empirically:**
- Bid-ask spread, top-of-book depth imbalance, trade-arrival intensity
- Weighted-average price (WAP) volatility -- used heavily in Optiver Kaggle top solutions
- Amihud (2002) illiquidity, Kyle's lambda, microprice, queue imbalance

**Sentiment / NLP (brief note -- out of main project scope):**
- Rahimikia, Zohren & Poon (2024): FinText word embeddings on Dow Jones Newswires helpful especially on jump days (`rahimikia-zohren-poon-2024` in bibliography)
```

- [ ] **Step 2: Commit**

```bash
git add notes/features/microstructure.md
git commit -m "docs: append deep research findings to microstructure feature notes"
```

---

### Task 9: Append to `notes/features/cross-asset.md`

**Files:**
- Read + Append: `notes/features/cross-asset.md` (currently 14 lines)
- Source: `notes/deep-research-vol-papers.md` lines 106 (Section D item 4), lines 120-124 (Section F)

- [ ] **Step 1: Append findings**

Append to end of `notes/features/cross-asset.md`:

```markdown

## Deep Research Findings (2026-05-06)

**Volatility spillover framework:**
- Diebold & Yilmaz (2009, 2012, 2014): generalized forecast-error variance decomposition from a VAR of realized vols. Total connectedness index spikes during crises (`diebold-yilmaz-2012` in bibliography)
- Key cross-asset features: VIX, MOVE (rates vol), CDX/iTraxx credit spreads, USD index vol, gold vol

**GNN cross-asset findings:**
- Zhang, Pu, Cucuringu & Dong (2025, Int. J. Forecasting): graph attention networks for multivariate RV. Key findings: multi-hop spillovers add little; nonlinear one-hop spillover effects help short-horizon (<=1 week) forecasts; training with QLIKE loss substantially outperforms MSE training (`zhang-pu-cucuringu-dong-2025` in bibliography)
- SpotV2Net (Brini & Toscano 2025): vol-of-vol-informed graph attention for intraday spot vol (`brini-toscano-2025` in bibliography)

**Factor models for volatility:**
- Herskovic, Kelly, Lustig & Van Nieuwerburgh (2016, JFE): "common idiosyncratic volatility" -- can decompose realized vol into systematic and idiosyncratic components
- Andersen, Bollerslev, Diebold & Ebens (2001): factor structure in daily equity vol

**Realized covariance estimation:**
- BNHLS (2011) multivariate realized kernels; Hayashi-Yoshida (2005) refresh-time sampling for asynchronous assets
- HEAVY-MV (Noureldin, Shephard & Sheppard 2012) for multivariate realized measures
```

- [ ] **Step 2: Commit**

```bash
git add notes/features/cross-asset.md
git commit -m "docs: append deep research findings to cross-asset feature notes"
```

---

### Task 10: Append to `notes/features/leverage-effect.md`

**Files:**
- Read + Append: `notes/features/leverage-effect.md` (currently 14 lines)
- Source: `notes/deep-research-vol-papers.md` line 103 (Section D item 7 -- the feature list mentions leverage)

- [ ] **Step 1: Append findings**

Append to end of `notes/features/leverage-effect.md`:

```markdown

## Deep Research Findings (2026-05-06)

**Signed semivariance asymmetry (key empirical result):**
- Patton & Sheppard (2015, RES): "Good Volatility, Bad Volatility" -- negative semivariance has substantially more predictive power than positive semivariance for future RV. Negative jumps raise future RV; positive jumps lower it. Models exploiting this asymmetry deliver "significantly better out-of-sample forecast performance" (`patton-sheppard-2015` in bibliography)
- This is one of the most robust and replicable findings in the vol forecasting literature -- 3-8% QLIKE improvement per the vol learning guide
- HAR with signed semivariances (SHAR) is a stronger baseline than plain HAR -- ML models should be benchmarked against SHAR, not just HAR
```

- [ ] **Step 2: Commit**

```bash
git add notes/features/leverage-effect.md
git commit -m "docs: append deep research findings to leverage-effect feature notes"
```

---

### Task 11: Append to `notes/features/jump-detection.md`

**Files:**
- Read + Append: `notes/features/jump-detection.md` (currently 14 lines)
- Source: `notes/deep-research-vol-papers.md` lines 31-32 (Section A jump detection), line 107 (Section D item 5)

- [ ] **Step 1: Append findings**

Append to end of `notes/features/jump-detection.md`:

```markdown

## Deep Research Findings (2026-05-06)

**Jump component persistence and forecasting impact:**
- Andersen, Bollerslev & Diebold (2007, RES) "Roughing It Up": decompose RV = continuous + jump. The jump component is highly important but less persistent than the continuous component -- this drives the HAR-RV-J and HAR-RV-CJ extensions (`andersen-bollerslev-diebold-2007-roughing` in bibliography)
- Implication: jump features help short-horizon forecasts more than long-horizon

**Earnings and event-driven jumps:**
- Lee (2012): earnings announcements almost always trigger jumps -- one of the most reliable event-driven vol signals
- Lee-Mykland (2008, RFS) intraday jump test is the workhorse for academic event studies (`lee-mykland-2008` in bibliography)

**Standard tools:**
- BNS bipower variation test and Lee-Mykland (2008) intraday test are the two standard jump detection tools
- Ait-Sahalia & Jacod (2009, Annals of Statistics) provide alternative tests based on power variation ratios
```

- [ ] **Step 2: Commit**

```bash
git add notes/features/jump-detection.md
git commit -m "docs: append deep research findings to jump-detection feature notes"
```

---

### Task 12: Append to `notes/features/optimal-feature-set.md`

**Files:**
- Read + Append: `notes/features/optimal-feature-set.md` (currently 265 lines)
- Source: `notes/deep-research-vol-papers.md` line 111 (Section D Rashomon bullet), lines 126-136 (Section G pitfalls)

Check for overlap first. The file has no existing Rashomon content (verified). Append only genuinely new content.

- [ ] **Step 1: Append findings**

Append to end of `notes/features/optimal-feature-set.md`:

```markdown

## Deep Research Findings (2026-05-06)

**Rashomon-aware feature analysis (novel for finance):**
- With TreeFARMS/SPLIT, construct the Rashomon set of all near-optimal interpretable trees on the vol feature panel, then compute Variable Importance Clouds (Dong & Rudin 2020, Nature Machine Intelligence) (`dong-rudin-2020` in bibliography)
- VIC gives an interval [min, max] of importance for each feature across the Rashomon set
- Features with non-overlapping clouds = robustly important vs. accidentally selected by a single greedy CART
- Financial features are heavily redundant (RV-d, BV-d, RQ-d, WAP-vol-d are near-collinear) -- Rashomon analysis would reveal which are essential (appear in every near-optimal tree), interchangeable (substitutable), or useless (in no near-optimal tree)
- To our knowledge, this analysis has not been published for any financial time series problem

**Feature construction pitfalls (from Section G):**
- Lookahead bias: realized measures use intraday returns up to time t; features for predicting RV_{t+1} must use only information <= t. Microstructure features computed on the full day require careful timestamp alignment
- Model in log-RV space: log-RV is near-unit-root; differencing destroys signal. Use fractional differencing or model in log-RV directly
- Train with QLIKE loss, not MSE: Zhang et al. (2025 GNN paper) report this matters substantially; MSE is dominated by extreme vol days (`zhang-pu-cucuringu-dong-2025` in bibliography)
- Choice of fitting scheme for HAR matters more than ML model choice per Wilms et al. 2024 "HARd to Beat" (`wilms-etal-2024` in bibliography)
```

- [ ] **Step 2: Commit**

```bash
git add notes/features/optimal-feature-set.md
git commit -m "docs: append Rashomon feature analysis and pitfall findings to optimal-feature-set"
```

---

## Chunk 3: Source file trimming

### Task 13: Trim `notes/deep-research-vol-papers.md`

**Files:**
- Modify: `notes/deep-research-vol-papers.md`

This is the final task. All content has been extracted to its target locations. Now trim the source file.

- [ ] **Step 1: Add cross-reference block after TL;DR**

After line 8 (end of TL;DR section), insert:

```markdown

---
> **Bibliography**: extracted to `reference/bibliography.md`
> **Project proposals**: extracted to `notes/project-proposals.md`
> **Research index**: `notes/research-index.md`
---
```

- [ ] **Step 2: Remove extracted sections**

Delete the following line ranges (working bottom-up to preserve line numbers). Include separator lines (`---`) and blanks adjacent to deleted sections to avoid orphaned markup:
1. Lines 348-365: "Caveats" section + preceding separator (now in `notes/project-proposals.md`)
2. Lines 320-347: "Recommendations" section + preceding separator (now in `notes/project-proposals.md`)
3. Lines 216-319: "Details -- PART 3: ANNOTATED BIBLIOGRAPHY" + preceding separator (now in `reference/bibliography.md`)
4. Lines 150-215: "Details -- PART 2: PROJECT DIRECTION PROPOSALS" (now in `notes/project-proposals.md`)

What remains: TL;DR (with cross-reference block), Key Findings, and Part 1 Landscape Survey (sections A-H).

- [ ] **Step 3: Verify the trimmed file**

The file should now contain:
- Line 1: Title
- Lines 3-8: TL;DR
- Cross-reference block (inserted)
- Lines 10-14: Key Findings
- Lines 16-148: Part 1 Landscape Survey (A through H)
- Nothing after Section H

Total: ~155 lines (down from 365).

- [ ] **Step 4: Commit**

```bash
git add notes/deep-research-vol-papers.md
git commit -m "refactor: trim extracted sections from deep research output, add cross-references"
```

---

## Execution Notes

**Parallelization:** After Task 1 (archive) completes, Tasks 2-12 are all independent and can be run in parallel. Task 13 (trim) must run last.

**No tests:** This is a content extraction task. Verification is done by checking entry counts (Task 2), confirming no content falls through the cracks, and reading the trimmed source file to confirm it's coherent.

**Largest risk:** Task 2 (bibliography) is by far the most labor-intensive -- ~80 entries to format. Budget most of the time there.
