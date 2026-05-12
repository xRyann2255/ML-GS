# Vol-Project-Ref (vol-learning-guide) Internal Audit

**Date:** 2026-05-12
**Scope:** All 17 chapters, 253 pages, full LaTeX source
**Method:** 5 parallel agents auditing by section + cross-chapter consistency
**Status:** ALL 20 ISSUES FIXED. Guide recompiled cleanly (268 pages, zero errors).

---

## Critical: Mathematical / Arithmetic Errors

### C1. Ch 6 p.84 -- Monthly RV sum is wrong

The HAR worked example (Section 6.2) lists 22 daily RV values and claims their sum is 32.70. The actual sum of the listed values (0.80 + 0.90 + 1.10 + ... + 1.90) is **34.40**.

This propagates: the monthly average should be 34.40/22 = 1.564 (not 1.486), and the final HAR forecast should be ~1.749 (not 1.727).

**Location:** `06-har-model.tex` line 246

---

### C2. Ch 15 p.224-225 -- Spillover index arithmetic has wrong denominator

The total spillover index worked example computes:

```
S = (25 + 15 + 30 + 15 + 20 + 10) / (3 x 3) x 100 = 115/9 x 100 = 38.3%
```

Two compounding errors:
- **Wrong denominator**: The formula (Eq. 15.5) divides by N, not N^2. Should be 115/3, not 115/9.
- **Double unit conversion**: The table entries are already percentages (rows sum to 100). Multiplying by 100 again would give 1277.8%, not 38.3%.

The correct answer (38.3%) requires: 115/3 = 38.3% (no x100), or 1.15/3 x 100 = 38.3% (fractions with x100). The written arithmetic reaches the right answer via the wrong path.

Steps 1-2 in the same example correctly use denominator N=3, then Step 4 switches to N x N = 9 without explanation.

**Location:** `15-spillovers-connectedness.tex` lines 310-315

---

### C3. Ch 5 p.71 -- Half-life formula is wrong

The GARCH(1,1) worked example claims: "it takes roughly 1/(1 - 0.98) = 50 days for the conditional variance to close half the gap to the long-run variance."

The quantity 1/(1 - alpha - beta) = 50 is the **mean lag** (time constant), not the half-life. The actual half-life is log(2)/(-log(0.98)) = ~34.3 days. The text describes the half-life but gives the mean-lag formula.

**Location:** `05-garch-family.tex` lines 337-339

---

## Critical: Missing Content (Broken Promises)

### C4. Ch 17 is truncated -- "five project directions" never defined

Chapter 1 (p.9) promises: "All five project directions (Chapter 17) start from the returns and variance foundations covered in this chapter."

**Chapter 17 contains only two sections** (215 lines of LaTeX, vs 800-1100 for peer chapters):
- 17.1 Volatility Targeting
- 17.2 Dealer Gamma and Structured Products Feedback

It has no Summary, no Key Results, and no enumeration of project directions. The chapter ends abruptly after Section 17.2.3 "Pin Risk at Expiry."

The five project directions referenced throughout the guide are:
1. HARQ-X + ML Residual (Ch 5, 6, 13, 17)
2. Intraday RV from LOB (Ch 3, 12)
3. Multivariate RC with GNNs (Ch 14, 15)
4. Rough Vol vs. Deep Learning (Ch 4, 7, 12)
5. VRP ML Trader (Ch 8, 9, 10)

These are referenced by number in **at least 10 chapters** but never formally defined or described anywhere. Stale "Project N" references appear in:
- Ch 1 line 8, Ch 3 lines 7+981, Ch 4 lines 7+874, Ch 5 line 10
- Ch 6 line 8, Ch 7 line 8, Ch 8 line 7, Ch 9 lines 6+770+811
- Ch 10 line 11, Ch 12 line 11, Ch 13 line 228
- Ch 14 lines 13+61+612, Ch 15 lines 12+81+200
- Ch 17 lines 75+195 (references "Project Direction 1" inline but never defines the full set)

---

## High: Factual Contradictions Between Chapters

### H1. Ch 11 vs Ch 13 -- HAR blend weight w contradicts

**Ch 11** (line 627-629): "Typical values: w in [0.2, 0.4], giving the tree model majority weight"

**Ch 13** (line 550-551 + "70/30 Rule" box at line 576): "set to w = 0.7 as a robust default" / "A 70/30 HAR/LightGBM blend is remarkably hard to beat"

Both define w as the HAR weight in the same formula. Ch 11 says HAR gets 20-40%; Ch 13 says HAR gets 70%. Direct contradiction.

---

### H2. Ch 11 vs Ch 12 -- Project 2 primary model disagrees

**Ch 11** line 11: "Projects 1, 2, and 5 all use tree ensembles as their primary model."

**Ch 12** line 11: "Project 2 (Intraday RV from LOB) and Project 4 (Rough Vol vs Deep Learning) use architectures from this chapter."

Ch 12 line 480 further says Project 2 "adapts DeepLOB" (a CNN+LSTM). Trees vs deep learning for the same project.

---

### H3. Ch 3 -- "Three main sources" of noise but lists four

**Ch 3** line 36 (p.35): "There are three main sources of microstructure noise."

The body then describes four: (1) bid-ask bounce, (2) discrete tick sizes, (3) price staleness, (4) adverse selection / information asymmetry.

The chapter Summary (line 998) lists only three (omitting adverse selection), so the count is internally inconsistent: the body has four, the intro/summary say three.

---

## High: Cross-Reference Errors

### H4. Ch 7 p.103 -- Section reference in wrong chapter

Text reads: "the microstructure noise discussed in Chapter 3 (Section 2.3)"

Section 2.3 is in Chapter 2, not Chapter 3. The LaTeX has `Chapter~\ref{ch:noise} (Section~\ref{sec:sampling-frequency})` where `ch:noise` = Ch 3 but `sec:sampling-frequency` is defined in Ch 2.

**Location:** `07-rough-volatility.tex` line 580

---

### H5. Ch 1 p.14 -- "Chapters 5-13" overstates forecasting range

Two instances (lines 268 and 773) describe "Chapters 5-13" as forecasting model chapters. But Chapters 8-9 (Options/Vol Surface and Variance Risk Premium) cover implied-volatility information and VRP, not forecasting models per se. More accurate: "Chapters 5-7 develop forecasting models; Chapters 8-9 add implied-volatility information; Chapters 10-13 apply ML methods."

---

## Moderate: Notation Inconsistencies

### M1. M vs n for number of intraday observations

| Convention | Chapters |
|-----------|----------|
| M | Ch 1 (line 275), Ch 14 (line 43) |
| n | Ch 2 (line 113), Ch 3 (line 160), Ch 4 (line 422), Ch 10 (lines 161-169) |

Ch 2 is the formal definition chapter for RV, so n is the canonical symbol. Ch 1 and Ch 14 are the outliers.

---

### M2. p vs N for number of assets (Ch 14 vs Ch 15)

Ch 14 uses p for the number of assets throughout. Ch 15 uses N. These are consecutive chapters in the same Part (V).

Worse, Ch 15 also uses p for VAR lag order ("fit a VAR(p)"), creating a **symbol collision**: a reader coming from Ch 14 sees p switch meaning without notice.

---

### M3. h_t vs sigma_t^2 undocumented switch

Ch 5 uses sigma_t^2 for conditional variance in GARCH/GJR-GARCH/EGARCH, then switches to h_t for Realized GARCH (line 668) without explaining the change. Ch 16 also uses h_t in the QLIKE formula. The comparison table at the end of Ch 5 shows both side by side, but no prose note bridges the transition.

---

### M4. FIGARCH d-parameter range potentially confusing

Ch 5 p.74: The prereq box says d in (0, 0.5) for ARIMA long memory. The FIGARCH definition immediately below says d in (0, 1). No note explains why the range differs (ARIMA stationarity vs FIGARCH's broader parameter space).

---

## Moderate: Structural Inconsistencies

### S1. Summary section numbering is split

| Pattern | Chapters |
|---------|----------|
| `\section*{Summary}` (unnumbered) | 1, 2, 3, 4, 6, 7, 9 |
| `\section{Summary}` (numbered) | 5, 8, 10, 11, 12, 13, 14, 15, 16 |
| No summary at all | 17 |

Appears to track writing chronology. Should be unified.

---

### S2. Ch 5 Summary + Key Results missing from TOC

Ch 5 uses `\section{Summary}` (numbered as 5.10) but without `\addcontentsline`. The TOC jumps from 5.9 to Chapter 6. Ch 6 and Ch 7 use `\section*{Summary}` with `\addcontentsline` and appear in the TOC correctly.

---

### S3. Key Results format varies across 3 patterns

| Pattern | Chapters |
|---------|----------|
| `\section*{Key Results}` (sometimes with `\addcontentsline`) | 5, 6, 7 |
| `\begin{keyresult}` environment (gold box) | 10, 13 |
| Inline table (no special section/environment) | 1, 2, 3, 4, 8, 9, 11, 12, 14, 15 |
| `\subsection{Key Results Recap}` | 16 |
| None | 17 |

---

### S4. Missing prereq boxes

CLAUDE.md says "Every chapter starts with a prereq box." In practice, ALL chapters open with an `\begin{application}` box first, and prereq boxes appear later (if at all).

**Chapters with NO prereq box anywhere:** 10, 13, 15

**Chapters where prereq box is deep inside the chapter** (not near the opening): 11 (line 138, inside Section 11.2), 14 (line 927, very late)

---

### S5. Opening application box titles inconsistent

| Pattern | Chapters |
|---------|----------|
| `[Why This Chapter]` | 1, 2, 3, 4, 6, 7 |
| `[Why This Chapter?]` | 5 |
| `[Why This Chapter Matters]` | 8, 9 |
| `[Where This Chapter Fits]` | 12 |
| `[From Components to Combinations]` | 13 |
| `[From One Asset to Many]` | 14 |
| `[Why This Chapter Is Non-Negotiable]` | 16 |
| (no title -- renders as "Application") | 10, 11, 15 |
| `[Why This Chapter]` | 17 |

---

## Low: Minor Issues

### L1. QLIKE macro vs plain text
Ch 16 uses `\QLIKE` macro; Ch 17 uses plain text "QLIKE".

### L2. Ch 15 "where:" lists displaced
Two instances where variable definition lists appear after intervening colored boxes instead of immediately after the equation (lines 36-62 and 456-486), breaking the guide's convention.

### L3. Ch 1 "Chapters 4 and 5 introduce models that accommodate fat tails"
Ch 4 identifies jumps as a source of fat tails but doesn't "accommodate" them in the modeling sense. Mild overstatement.

---

## Summary: Fix Priority

| Priority | Count | Key Items |
|----------|-------|-----------|
| **Critical** | 4 | Arithmetic errors in Ch 6 + Ch 15, half-life formula in Ch 5, Ch 17 truncated (missing 5 project directions) |
| **High** | 5 | Blend weight contradiction (Ch 11 vs 13), Project 2 model conflict (Ch 11 vs 12), noise source count (Ch 3), cross-ref error (Ch 7), overstated chapter range (Ch 1) |
| **Moderate** | 8 | M/n notation (2 ch), p/N notation (2 ch), h_t switch (Ch 5), FIGARCH range (Ch 5), Summary numbering (guide-wide), Ch 5 TOC gap, Key Results format (3 patterns), missing prereqs (3 ch) |
| **Low** | 3 | QLIKE macro, displaced where-lists, mild overstatement |

**Total: 20 distinct discrepancies found.**
