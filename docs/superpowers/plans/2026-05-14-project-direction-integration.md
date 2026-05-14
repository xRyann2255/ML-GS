# Project Direction Integration into vol-learning-guide

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update all "Project Direction N" references in the vol-learning-guide to reflect the user's chosen project direction, and mirror every LaTeX change in the corresponding markdown file.

**Architecture:** The learning guide currently references 5 undecided project directions. The user has fully committed to one: "Layered Information and Realized Volatility: Where ML Adds Value Beyond HAR" -- a LightGBM-based progressive feature layering approach (L0-L7) with prediction-level ensemble blending, Rashomon analysis for interpretability, and an IV-RV gap signal for economic value. All project connection boxes must be updated to reference this specific approach.

**Approach:** Each task edits one LaTeX chapter file and its markdown mirror. No new conceptual content is needed (gap analysis confirmed the learning guide already covers QLIKE gradient/Hessian in ch11 and fractional differencing in ch10). The edits are project-direction descriptions, not paper-backed claims, so paper verification is not required.

---

## Project Direction Summary (for replacement text)

**Core approach:** Progressive feature layering (Layers 0-7) with LightGBM as primary model, custom QLIKE loss
**Baselines:** HAR, HAR-J, HAR-CJ, SHAR, HARQ (econometric)
**ML model:** LightGBM with custom QLIKE objective (gradient + Hessian)
**Ensemble:** Prediction-level blending (LightGBM + optional LSTM for intraday sequences)
**Interpretability:** Rashomon analysis with optimal sparse trees (STreeD, TreeFARMS)
**Economic value:** IV-RV gap signal, vol-targeting backtest, straddle P&L
**Universe:** 34 instruments (30 mega-cap + 4 ETFs + E-mini), 11.3 years
**Evaluation:** QLIKE (primary), Diebold-Mariano tests, Model Confidence Set
**Data edge:** GS tick data, full SPX IV surface, E-mini L2 depth, cross-asset

---

## Edit Inventory

9 locations across 5 LaTeX files, each with a markdown mirror:

| # | File | Lines | Current Reference | Replacement Theme |
|---|------|-------|-------------------|-------------------|
| 1 | ch01 | 8 | "All five project directions" | Singular: your internship project |
| 2 | ch13 | 227-233 | "Project Direction 1 (HARQ-X + ML residual)" | HAR/HARQ as baselines; LightGBM learns nonlinear patterns from full feature set |
| 3 | ch14 | 55-62 | "Project Direction 3 (Multivariate RC with GNNs)" | Univariate RV for 34 instruments; cross-asset covariance feeds Layer 4 spillover features |
| 4 | ch14 | 607-615 | "Project Direction 3 (GNN)" | Layer 4 cross-asset features distill cross-sectional structure into scalar LightGBM inputs |
| 5 | ch14 | 799-806 | "Project Direction 3 (GNNs)" | Graph-HAR mechanism captured via Layer 4 spillover features for LightGBM |
| 6 | ch15 | 79-84 | "Project Direction 3" | Impulse-response matrices underpin DY spillover index in Layer 4 |
| 7 | ch15 | 195-203 | "Project Direction 3 (GNNs)" | DY measures become scalar Layer 4 features; value concentrated in regime transitions |
| 8 | ch17 | 74-78 | "Project Direction 1: HARQ-X + ML residual" | LightGBM with Layers 0-7 and custom QLIKE |
| 9 | ch17 | 193-196 | "Project Direction 1 or 2" | LightGBM feature set |

---

### Task 1: Update ch01 (opening reference)

**Files:**
- Modify: `vol-learning-guide/chapters/01-returns-variance-volatility.tex:8`
- Modify: `vol-learning-guide/markdown/ch01-returns-variance-volatility.md` (corresponding line)

- [ ] **Step 1: Edit LaTeX line 8**

Replace:
```latex
All five project directions (Chapter~\ref{ch:applications}) start from the returns and variance foundations covered in this chapter.
```
With:
```latex
Your internship project---forecasting realized volatility with progressive feature layering and ML (Chapter~\ref{ch:applications})---starts from the returns and variance foundations covered in this chapter.
```

- [ ] **Step 2: Edit markdown mirror**

Find the corresponding line in `ch01-returns-variance-volatility.md` and apply the same change.

- [ ] **Step 3: Verify no other "project direction" references in ch01**

Grep ch01 for any remaining "Project Direction" or "five project" references.

---

### Task 2: Update ch13 (ensemble backbone)

**Files:**
- Modify: `vol-learning-guide/chapters/13-hybrid-ensemble.tex:227-233`
- Modify: `vol-learning-guide/markdown/ch13-hybrid-ensemble.md` (corresponding block)

- [ ] **Step 1: Edit LaTeX projectconnection box**

Replace:
```latex
\begin{projectconnection}[Why This Matters]
This two-step decomposition is the backbone of Project Direction~1
(HARQ-X + ML residual).  Because HARQ already adapts its
coefficients to measurement-error regimes, its residuals are
even cleaner than plain HAR residuals, giving the downstream ML
model a higher signal-to-noise starting point.
\end{projectconnection}
```
With:
```latex
\begin{projectconnection}[Why This Matters]
This two-step decomposition underpins your project's model comparison.
HAR and HARQ serve as econometric baselines; LightGBM then learns
nonlinear patterns from the full feature set (Layers~0--7).  Because
HARQ already adapts its coefficients to measurement-error regimes,
comparing LightGBM's QLIKE against HARQ tells you exactly how much
the ML model's nonlinearity adds beyond what the noise-adaptive
linear baseline already captures.
\end{projectconnection}
```

- [ ] **Step 2: Edit markdown mirror**

Find and update the corresponding project connection block in `ch13-hybrid-ensemble.md`.

---

### Task 3: Update ch14 (three multivariate boxes)

**Files:**
- Modify: `vol-learning-guide/chapters/14-multivariate-volatility.tex:55-62, 607-615, 799-806`
- Modify: `vol-learning-guide/markdown/ch14-multivariate-volatility.md` (three corresponding blocks)

- [ ] **Step 1: Edit first projectconnection box (lines 55-62)**

Replace:
```latex
This is the starting point for Project Direction~3 (Multivariate RC with GNNs).
```
With:
```latex
Your project forecasts univariate RV for 34 instruments, but the cross-asset
covariance structure feeds directly into the Layer~4 spillover features that
enter LightGBM as scalar inputs.
```

- [ ] **Step 2: Edit second projectconnection box (lines 607-615)**

Replace:
```latex
days. If Project Direction~3 (GNN) is to justify its complexity, it must beat
HAR-DRD on QLIKE across the full covariance matrix, not just on individual
variances.
```
With:
```latex
days. Your project uses univariate forecasting per instrument, but the
cross-sectional structure that HAR-DRD captures is exactly what your Layer~4
cross-asset features (sector-mean RV, Diebold-Yilmaz spillover index) distill
into scalar inputs for LightGBM.
```

- [ ] **Step 3: Edit third projectconnection box (lines 799-806)**

Replace full box:
```latex
\begin{projectconnection}[Why This Matters]
This is the linear foundation for Project Direction~3 (GNNs). Graph-HAR adds
one cross-asset spillover term and already improves on standard HAR. The GNN
extension (below) replaces this linear weighted average with learnable nonlinear
message passing, potentially capturing richer interaction patterns. Your project
contribution: show whether the nonlinear GNN spillover term yields statistically
significant QLIKE gains over the linear Graph-HAR spillover on real equity data.
\end{projectconnection}
```
With:
```latex
\begin{projectconnection}[Why This Matters]
Graph-HAR demonstrates that cross-asset spillover information improves univariate
vol forecasts.  Your project captures this same mechanism through Layer~4
cross-asset features: sector-mean RV, the Diebold-Yilmaz spillover index, and
cross-asset RV rank.  These scalar features distill the neighbor-weighted-average
idea into inputs that LightGBM can exploit without requiring a full graph
learning framework.
\end{projectconnection}
```

- [ ] **Step 4: Edit all three corresponding blocks in markdown mirror**

Find and update the three project connection blocks in `ch14-multivariate-volatility.md`.

---

### Task 4: Update ch15 (two spillover boxes)

**Files:**
- Modify: `vol-learning-guide/chapters/15-spillovers-connectedness.tex:79-84, 195-203`
- Modify: `vol-learning-guide/markdown/ch15-spillovers-connectedness.md` (two corresponding blocks)

- [ ] **Step 1: Edit first projectconnection box (lines 79-84)**

Replace:
```latex
\begin{projectconnection}[Why This Matters]
The MA representation is what lets you decompose forecast errors into contributions
from each asset.  For GNN-based vol forecasting (Project Direction 3), the impulse-response
matrices $\bm{\Phi}_h$ define the effective ``edge weights'' of the spillover graph
at each horizon.
\end{projectconnection}
```
With:
```latex
\begin{projectconnection}[Why This Matters]
The MA representation is what lets you decompose forecast errors into contributions
from each asset.  In your project, the impulse-response matrices $\bm{\Phi}_h$
underpin the Diebold-Yilmaz spillover index that enters Layer~4 of your feature
pipeline.  The total spillover index $S^{(H)}_t$ becomes a scalar regime indicator
for LightGBM, while directional spillovers identify which assets are currently
transmitting or receiving volatility shocks.
\end{projectconnection}
```

- [ ] **Step 2: Edit second projectconnection box (lines 195-203)**

Replace:
```latex
\begin{projectconnection}[Why This Matters]
These four measures are the feature engineering payoff of the DY framework.  Total
spillover $S^{(H)}_t$ is a regime indicator (high = crisis = different vol dynamics).
Directional FROM measures how ``vulnerable'' an asset is to imported vol.  Net
spillover identifies transmitters vs.\ receivers.  All three become columns in your
feature matrix.  For Project Direction 3 (GNNs), the pairwise entries form the
adjacency matrix of the volatility graph, and time-varying versions define dynamic
graph structure.
\end{projectconnection}
```
With:
```latex
\begin{projectconnection}[Why This Matters]
These four measures are the feature engineering payoff of the DY framework.  Total
spillover $S^{(H)}_t$ is a regime indicator (high = crisis = different vol dynamics).
Directional FROM measures how ``vulnerable'' an asset is to imported vol.  Net
spillover identifies transmitters vs.\ receivers.  All three become columns in your
Layer~4 feature matrix, entering LightGBM as scalar cross-asset signals.  Their
value is concentrated in regime transitions---precisely the forecasts where
single-asset features alone break down.
\end{projectconnection}
```

- [ ] **Step 3: Edit both corresponding blocks in markdown mirror**

Find and update both project connection blocks in `ch15-spillovers-connectedness.md`.

---

### Task 5: Update ch17 (two application boxes)

**Files:**
- Modify: `vol-learning-guide/chapters/17-applications-projects.tex:74-78, 193-196`
- Modify: `vol-learning-guide/markdown/ch17-applications-projects.md` (two corresponding blocks)

- [ ] **Step 1: Edit first projectconnection box (lines 74-78)**

Replace:
```latex
\begin{projectconnection}[Why This Matters]
This formula is the direct economic-value test for your internship project (Project Direction 1: HARQ-X + ML residual).
Every QLIKE improvement in your forecast translates into a tighter $\hat\sigma_t$, which means more precise position sizing and higher Sharpe.
The vol-targeting backtest is your primary deliverable for demonstrating that statistical accuracy creates real P\&L.
\end{projectconnection}
```
With:
```latex
\begin{projectconnection}[Why This Matters]
This formula is the direct economic-value test for your internship project.
Your LightGBM model, trained with custom QLIKE loss on Layers~0--7, produces a
forecast $\hat\sigma_t$ that feeds directly into this position-sizing equation.
Every QLIKE improvement translates into more precise position sizing and higher
Sharpe.  The vol-targeting backtest is your primary deliverable for demonstrating
that statistical accuracy creates real P\&L.
\end{projectconnection}
```

- [ ] **Step 2: Edit second projectconnection box (lines 193-196)**

Replace:
```latex
\begin{projectconnection}[Why This Matters]
GEX provides a feature that captures a fundamentally different mechanism from any return-based or RV-based predictor.
Including it in your HAR-X specification (Project Direction 1 or 2) demonstrates market microstructure awareness and gives your model an edge that purely statistical approaches miss.
\end{projectconnection}
```
With:
```latex
\begin{projectconnection}[Why This Matters]
GEX provides a feature that captures a fundamentally different mechanism from any return-based or RV-based predictor.
Including it in your LightGBM feature set demonstrates market microstructure awareness and gives your model an edge that purely statistical approaches miss.
\end{projectconnection}
```

- [ ] **Step 3: Edit both corresponding blocks in markdown mirror**

Find and update both project connection blocks in `ch17-applications-projects.md`.

---

### Task 6: Final sweep and verification

- [ ] **Step 1: Grep entire vol-learning-guide for remaining "Project Direction" references**

```bash
grep -rn "Project Direction" vol-learning-guide/
```

Should return zero results.

- [ ] **Step 2: Grep for "five project" or "five directions"**

```bash
grep -rn "five project\|five direction" vol-learning-guide/
```

Should return zero results.

- [ ] **Step 3: Verify markdown files match LaTeX content**

Spot-check each edited markdown file to confirm the project connection blocks match.
