# IV–RV Straddle Capstone Chapter — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author `vol-learning-guide/chapters/18-ivrv-straddle.tex` — the Part 6 capstone chapter teaching the realistic, evaluable delta-hedged IV–RV-gap straddle — to the spec in `docs/vol-learning-guide/ivrv-straddle-chapter-design.md`, wire it into the book, compile cleanly, and produce the markdown mirror.

**Architecture:** This is a LaTeX prose+math authoring task, so the TDD rhythm is adapted: each task drafts one or two sections of the chapter, then "tests" by compiling (`pdflatex`/`bibtex`) and checking for undefined references/citations and figure errors, then commits. The chapter is written through the project's `write-chapter` pipeline (Pass 0 source extraction → Chapter Contract → Pass 1 writer → Pass 2 verifier + Pass 3 condenser → Pass 4 naive-reader → Final), decomposed here into reviewable per-section tasks. Every TikZ figure is gated by the `verify-diagram` skill. The markdown mirror is produced by `convert-chapter-markdown`.

**Tech Stack:** LaTeX (`report` class, `tcolorbox`, `tikz`, `pgfplots`, `natbib`/`bibtex`, `cleveref`); the existing `vol-learning-guide` preamble; project skills `write-chapter`, `verify-diagram`, `convert-chapter-markdown`. Compile on Windows via the Bash tool (Git Bash has TeX Live + `&&` chaining).

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `vol-learning-guide/chapters/18-ivrv-straddle.tex` | Create | The chapter. One file, ~30–40 pp., sections §18.1–§18.12. |
| `vol-learning-guide/references.bib` | Modify | Add 22 new citation entries (append at end). |
| `vol-learning-guide/preamble.tex` | Modify | Add `\Vega`, `\Vanna`, `\Volga` math macros (after the volatility-specific block, ~line 130). |
| `vol-learning-guide/main.tex` | Modify | Add `\input{chapters/18-ivrv-straddle}` after line 51 (`17-applications-projects`), inside `\part{Evaluation and Practice}`. |
| `vol-learning-guide/markdown/ch18-ivrv-straddle.md` | Create | Faithful markdown mirror for LLM consumption. |
| `vol-learning-guide/main.pdf` + aux | Regenerate | Compiled output (already tracked in the repo). |
| `~/.claude/.../memory/project_status.md`, `notes/research-journal.md` | Modify | Record chapter completion (final task). |

**Quality bar applied to every drafting task (from `write-chapter` + CLAUDE.md):**
- **Mandatory equation pattern:** (1) setup sentence → (2) the equation → (3) itemized symbol definitions → (4) `\begin{intuition}[In Plain English]` box ("what the whole equation DOES") → (5) `\begin{projectconnection}` box (why it matters for the RV-forecast project).
- Open the chapter with a concrete question, not a definition; first box is `prereq`.
- Define every term in **bold** on first use. No em dashes. `booktabs` tables only.
- Every displayed formula carries its source anchor in prose ("Boyle–Emanuel 1980, Eq. 7, p. 9 via Anagnou–Hodges 2007") and a `% SOURCE:` LaTeX comment.
- Cross-reference ch08/09/16/17 with `\Cref{...}`; never re-derive material owned by those chapters (see spec §8).
- **Label scheme (no collisions):** chapter `ch:ivrv-straddle`; sections `sec:ivrv:<slug>`; equations `eq:ivrv:<slug>`; figures `fig:ivrv:<slug>`; algorithm `alg:ivrv:backtest`; definitions `def:ivrv:<slug>`.

**Compile commands (run from repo root via the Bash tool):**
- Quick single-pass error check: `cd vol-learning-guide && pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null; echo EXIT=$?`
- Full resolve (refs + cites): `cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex`
- Undefined-ref/cite check: `cd vol-learning-guide && grep -E "Reference .* undefined|Citation .* undefined" main.log || echo "NONE"`

---

## Task 1: Add the 22 new bibliography entries

**Files:**
- Modify: `vol-learning-guide/references.bib` (append at end-of-file)

- [ ] **Step 1: Append the entries.** Add the following block at the end of `references.bib`. Use `\citep`/`\citet` keys exactly as written (they are referenced verbatim by later tasks).

```bibtex
% ── Chapter 18: IV–RV Straddle (VRP strategy, hedging error, option costs) ──

@article{AhmadWilmott2005,
  author = {Ahmad, Riaz and Wilmott, Paul},
  title  = {Which Free Lunch Would You Like Today, Sir?: Delta Hedging, Volatility Arbitrage and Optimal Portfolios},
  journal= {Wilmott Magazine},
  year   = {2005},
  pages  = {64--79}
}
@incollection{CarrMadan2002,
  author    = {Carr, Peter and Madan, Dilip},
  title     = {Towards a Theory of Volatility Trading},
  booktitle = {Volatility: New Estimation Techniques for Pricing Derivatives},
  editor    = {Jarrow, Robert A.},
  publisher = {Risk Books},
  year      = {2002}
}
@article{CarrLee2009,
  author = {Carr, Peter and Lee, Roger},
  title  = {Volatility Derivatives},
  journal= {Annual Review of Financial Economics},
  volume = {1},
  pages  = {319--339},
  year   = {2009},
  doi    = {10.1146/annurev.financial.050808.114304}
}
@article{BertsimasKoganLo2000,
  author = {Bertsimas, Dimitris and Kogan, Leonid and Lo, Andrew W.},
  title  = {When Is Time Continuous?},
  journal= {Journal of Financial Economics},
  volume = {55},
  number = {2},
  pages  = {173--204},
  year   = {2000},
  doi    = {10.1016/S0304-405X(99)00049-5}
}
@article{BoyleEmanuel1980,
  author = {Boyle, Phelim P. and Emanuel, David},
  title  = {Discretely Adjusted Option Hedges},
  journal= {Journal of Financial Economics},
  volume = {8},
  number = {3},
  pages  = {259--282},
  year   = {1980},
  doi    = {10.1016/0304-405X(80)90003-3}
}
@misc{AnagnouHodges2007,
  author = {Anagnou-Basioudis, Iliana and Hodges, Stewart},
  title  = {Derivatives Hedging Errors and Volatility},
  year   = {2007},
  note   = {EFMA Annual Meeting paper}
}
@misc{BrodenTankov2010,
  author = {Brod{\'e}n, Mats and Tankov, Peter},
  title  = {Tracking Errors from Discrete Hedging in Exponential {L\'evy} Models},
  year   = {2010},
  note   = {arXiv preprint arXiv:1003.0709}
}
@article{Leland1985,
  author = {Leland, Hayne E.},
  title  = {Option Pricing and Replication with Transactions Costs},
  journal= {The Journal of Finance},
  volume = {40},
  number = {5},
  pages  = {1283--1301},
  year   = {1985},
  doi    = {10.1111/j.1540-6261.1985.tb02383.x}
}
@misc{ZhaoZiemba2007,
  author = {Zhao, Yonggan and Ziemba, William T.},
  title  = {Hedging Errors with {Leland's} Option Model in the Presence of Transaction Costs},
  year   = {2007},
  note   = {Working paper}
}
@article{KabanovSafarian1997,
  author = {Kabanov, Yuri M. and Safarian, Mher M.},
  title  = {On Leland's Strategy of Option Pricing with Transactions Costs},
  journal= {Finance and Stochastics},
  volume = {1},
  number = {3},
  pages  = {239--250},
  year   = {1997},
  doi    = {10.1007/s007800050023}
}
@article{LepinetteKabanov2010,
  author = {L{\'e}pinette, Emmanuel and Kabanov, Yuri},
  title  = {Mean Square Error for the {Leland--Lott} Hedging Strategy: Convex Pay-offs},
  journal= {Finance and Stochastics},
  volume = {14},
  number = {4},
  pages  = {625--667},
  year   = {2010},
  doi    = {10.1007/s00780-010-0130-z}
}
@misc{ArzelLehdili2026,
  author = {Arzel, Pierre and Lehdili, Noureddine},
  title  = {Bridging Stochastic Control and Deep Hedging: Structural Priors for No-Transaction Band Networks},
  year   = {2026},
  note   = {arXiv preprint arXiv:2603.29994}
}
@misc{BrugiereTurinici2025,
  author = {Brugi{\`e}re, Pierre and Turinici, Gabriel},
  title  = {Model-Free Deep Hedging with Transaction Costs and Light Data Requirements},
  year   = {2025},
  note   = {arXiv preprint arXiv:2505.22836}
}
@misc{WysockiSlepaczuk2024,
  author = {Wysocki, Micha{\l} and {\'S}lepaczuk, Robert},
  title  = {Construction and Hedging of Equity Index Options Portfolios},
  year   = {2024},
  note   = {arXiv preprint arXiv:2407.13908}
}
@misc{FrancoisEtAl2025,
  author = {Fran{\c c}ois, Pascal and Gauthier, Genevi{\`e}ve and Godin, Fr{\'e}d{\'e}ric and P{\'e}rez Mendoza, Carlos},
  title  = {Deep Hedging with Options Using the Implied Volatility Surface},
  year   = {2025},
  note   = {arXiv preprint arXiv:2504.06208}
}
@article{MuravyevPearson2020,
  author = {Muravyev, Dmitriy and Pearson, Neil D.},
  title  = {Options Trading Costs Are Lower Than You Think},
  journal= {The Review of Financial Studies},
  volume = {33},
  number = {11},
  pages  = {4973--5014},
  year   = {2020},
  doi    = {10.1093/rfs/hhaa010}
}
@misc{DoshiPariShamsuddin2025,
  author = {Doshi, Hitesh and Pari, and Shamsuddin, },
  title  = {Risky Intraday Order Flow and Option Liquidity},
  year   = {2025},
  note   = {Working paper}
}
@article{AmayaEtAl2015,
  author = {Amaya, Diego and Christoffersen, Peter and Jacobs, Kris and Vasquez, Aurelio},
  title  = {Does Realized Skewness Predict the Cross-Section of Equity Returns?},
  journal= {Journal of Financial Economics},
  volume = {118},
  number = {1},
  pages  = {135--167},
  year   = {2015},
  doi    = {10.1016/j.jfineco.2015.02.009}
}
@article{AhadzieJeyasreedharan2020,
  author = {Ahadzie, Richard M. and Jeyasreedharan, Nagaratnam},
  title  = {Effects of Intervaling on High-Frequency Realized Higher-Order Moments},
  journal= {Quantitative Finance},
  volume = {20},
  number = {7},
  pages  = {1169--1184},
  year   = {2020},
  doi    = {10.1080/14697688.2020.1726455}
}
@article{BakshiKapadia2003,
  author = {Bakshi, Gurdip and Kapadia, Nikunj},
  title  = {Delta-Hedged Gains and the Negative Market Volatility Risk Premium},
  journal= {The Review of Financial Studies},
  volume = {16},
  number = {2},
  pages  = {527--566},
  year   = {2003},
  doi    = {10.1093/rfs/hhg002}
}
@article{LiWu2026,
  author = {Li, B. and Wu, C.},
  title  = {Beyond Delta Neutrality: Confidence-Scaled Hedging with Machine Learning Forecasts},
  journal= {Finance Research Letters},
  volume = {87},
  pages  = {109098},
  year   = {2026},
  doi    = {10.1016/j.frl.2025.109098}
}
@misc{Pollok2025,
  author = {Pollok, },
  title  = {Predicting Realized Variance Out of Sample: Can Anything Beat the Benchmark?},
  year   = {2025},
  note   = {arXiv preprint arXiv:2506.07928}
}
```

- [ ] **Step 2: Verify author/year/venue/pages against the source PDFs.** For each entry, open the matching PDF in `reference/project-papers/` (filenames listed in the brief's "Papers Acquired" section) and confirm the author list (fill the blank first names: `Pollok`, the `Doshi/Pari/Shamsuddin` and `Arzel/Lehdili`/`Wysocki/Słepaczuk` first names), year, venue, and `ZhaoZiemba2007` year. Correct any field that disagrees with the PDF title page. Do not invent a name you cannot confirm; if unconfirmable, leave the surname only.

- [ ] **Step 3: Syntax check.** Run: `cd vol-learning-guide && bibtex --help >/dev/null; awk 'BEGIN{b=0} /@/{c++} {o+=gsub(/{/,"{"); cl+=gsub(/}/,"}")} END{print "entries="c, "braces_balanced="(o==cl)}' references.bib`
  Expected: `braces_balanced=1`. (Full resolution is checked when sections cite these keys.)

- [ ] **Step 4: Commit.**

```bash
git add vol-learning-guide/references.bib
git commit -m "refs(vol-guide): add 22 sources for IV-RV straddle chapter"
```

---

## Task 2: Add preamble macros for the new Greeks

**Files:**
- Modify: `vol-learning-guide/preamble.tex` (after the volatility-specific macro block, ~line 129, before the TikZ Styles block)

- [ ] **Step 1: Add the macros.**

```latex
% ── Math Shortcuts (options Greeks used in ch18) ──
\newcommand{\Vega}{\operatorname{\mathcal{V}}}
\newcommand{\Vanna}{\operatorname{Vanna}}
\newcommand{\Volga}{\operatorname{Volga}}
```

- [ ] **Step 2: Compile to confirm no macro clash.** Run the quick single-pass check. Expected: `EXIT=0` (a clash would error with "command already defined").

- [ ] **Step 3: Commit.**

```bash
git add vol-learning-guide/preamble.tex
git commit -m "style(vol-guide): add Vega/Vanna/Volga macros for ch18"
```

---

## Task 3: Pass 0 source extraction + Chapter Contract (no file written)

This is the `write-chapter` pre-draft step. Its output stays in the executing agent's context as ground truth; do **not** save it as a file.

- [ ] **Step 1: Extract formulas from the acquired PDFs.** For each source below, read only the cited pages in `reference/project-papers/` and record the exact formula, its equation number/page, and the paper's notation. The spec (`docs/vol-learning-guide/ivrv-straddle-chapter-design.md`, §5 and §8) lists the target formulas and anchors; confirm each against the PDF:
  - `ahmad-wilmott-2005-which-free-lunch.pdf` — Eq. 1 p. 67 (daily MTM), Eq. 2 p. 67 (dollar-gamma), §4.2 Eq. 10 p. 70 (Result 2 = continuous-hedge variance, **no 1/N, no kurtosis** — confirm this absence directly).
  - `bertsimas-kogan-lo-2000-when-time-continuous.pdf` — Thm 1(c) Eq. 2.13 pp. 10–11, granularity Eq. 2.18 p. 13, Thm 2 Eq. 2.17 p. 12.
  - `anagnou-hodges-2007-derivatives-hedging-errors.pdf` — Eq. 7 p. 9 (Boyle–Emanuel per-step error), χ² statement pp. 12–13, `var(u²)=2`.
  - `carr-madan-2002-theory-volatility-trading.pdf` + `broden-tankov-2010-tracking-errors-levy.pdf` (log contract; jump limit `lim n·E[ε²]>0`).
  - `zhao-...-leland-option-hedging-costs.pdf` — Eq. 5 (Leland modified vol), the √(2/π) half-normal mean.
  - `kabanov-safarian-1997-leland-strategy.pdf`, `lepinette-kabanov-2010-leland-lott-mse.pdf` (Thm 1.2 Eq. 1.11 / Thm 1.3 Eq. 1.16).
  - `muravyev-pearson-2015-option-trading-costs.pdf` (8.1¢/6.2¢/1.3¢; 22.7%→3.9%), `doshi-pari-shamsuddin-2025-...pdf` (Table 2 p. 46 schedule).
  - `amaya-...-2015` / `francois-et-al-2025` / `predicting-realized-variance-benchmark-2025.pdf` (Pollok protocol; **note §6 numbers are unrendered — do not cite magnitudes**), `bailey-lopezdeprado-2014-deflated-sharpe.pdf` (Eq. 1 p. 7, Eq. 2 p. 8), `bakshi-kapadia-2003-delta-hedged-gains.pdf`.
- [ ] **Step 2: Lock the Chapter Contract** in context: the SECTIONS order = spec §5 (§18.1→§18.12); NOTATION = preamble macros (`\RV`,`\IVol`,`\VRP`,`\QLIKE`,`\SR`,`\DSR`,`\Var`,`\E`,`\N`,`\Vega`,`\Vanna`,`\Volga`); LABELS = the `sec:ivrv:` / `eq:ivrv:` / `fig:ivrv:` scheme; CITATIONS = the key→claim map from Task 1's keys. Confirm every claim traces to a Pass 0 anchor; if any does not, drop it.
- [ ] **Step 3: No commit** (nothing written). Proceed to Task 4.

---

## Task 4: §18.1 The strategy in one picture + chapter scaffold + Fig A

**Files:**
- Create: `vol-learning-guide/chapters/18-ivrv-straddle.tex`
- Modify: `vol-learning-guide/main.tex:51`

- [ ] **Step 1: Create the chapter file with the opener, prereq box, and §18.1.** Structure (fill prose per the quality bar; the opening must be the concrete hook "Your model beats HAR by 40 bps of QLIKE — does it make money?"):

```latex
\chapter{From Forecast to P\&L: A Realistic, Evaluable IV--RV Straddle}
\label{ch:ivrv-straddle}

\begin{application}[Why This Chapter]
% the capstone framing: forecast -> VRP signal -> realistic backtest -> evaluation
\end{application}

% concrete hook paragraph here (no abstract definition)

\begin{prereq}[Background]
% point to \Cref{sec:greeks}, \Cref{sec:var-swap} (ch08);
% \Cref{sec:vrp-definition}, \Cref{sec:gamma-pnl} (ch09);
% \Cref{sec:eval-qlike}, \Cref{sec:eval-dsr}, \Cref{sec:eval-dm} (ch16);
% \Cref{sec:net-econ-value} (ch17)
\end{prereq}

\section{The Strategy in One Picture}
\label{sec:ivrv:picture}
% intuition box: insurance-seller analogy (reference ch09, do not re-derive VRP)
% keyidea box: the rule -- short if IV_{t-1} > RV_hat_t, long if below
% Figure A below
```

- [ ] **Step 2: Add Fig A (pipeline flow diagram, TikZ)** using the preamble `flowblock`/`decisionblock` styles: forecast → signal $X_{t-1}$ → trade decision → delta-hedge → daily MTM → evaluate. Label `fig:ivrv:pipeline`.
- [ ] **Step 3: Wire into the book.** In `main.tex`, after line 51 (`\input{chapters/17-applications-projects}`) add: `\input{chapters/18-ivrv-straddle}`
- [ ] **Step 4: Compile (full resolve)** with the full-resolve command, then the undefined-ref/cite check.
  Expected: `EXIT=0`; the undefined check prints only labels not yet created (acceptable mid-draft) — confirm `ch:ivrv-straddle` and `sec:ivrv:picture` are now defined and the chapter shows in `main.toc`.
- [ ] **Step 5: Verify Fig A** with the `verify-diagram` skill — pass the guide root `vol-learning-guide`, a unique caption substring, concept ("the end-to-end straddle backtest pipeline"), and relationships (the arrow chain forecast→signal→trade→hedge→MTM→evaluate). Loop fix→re-verify until both gates pass. If it returns `needs-human`, stop and surface defects.
- [ ] **Step 6: Commit.**

```bash
git add vol-learning-guide/chapters/18-ivrv-straddle.tex vol-learning-guide/main.tex
git commit -m "feat(ch18): scaffold + 18.1 strategy overview + pipeline figure"
```

---

## Task 5: §18.2 The signal and the anti-lookahead protocol

**Files:** Modify `vol-learning-guide/chapters/18-ivrv-straddle.tex`

- [ ] **Step 1: Draft §18.2** (`\section{The Signal and the Anti-Lookahead Protocol}\label{sec:ivrv:signal}`). Follow the equation pattern. Content from spec §18.2:
  - Signal equation `\label{eq:ivrv:signal}`: $X_{t-1} = f(\widehat{\RV}_t, \IVol_{t-1})$, $f \in \{x-y,\ x/y,\ \ln(x/y)\}$ — `\citet{Pollok2025}`.
  - Unit alignment: $\IVol/\sqrt{250}$ to daily RV units.
  - `keyidea` box: the lookahead-safe timeline (predictor in $\mathcal F_t^{3:55}$, trade pre-close, return $t{+}1$) — `\citep{Pollok2025}`.
  - Sizing: `\citet{LiWu2026}` graded > binary, with the caveat box (directional single-ETF result; cite only for "moderate scaling wins").
  - `warning` box: lookahead traps via `\Cref{sec:eval-lookahead-taxonomy}`, `\Cref{tab:lookahead-taxonomy}`; VRP via `\Cref{eq:vrp-operational}` (do not redefine VRP).
- [ ] **Step 2: Compile (quick single-pass)** → `EXIT=0`.
- [ ] **Step 3: Undefined-cite check** → confirm `Pollok2025`, `LiWu2026` resolve after a full-resolve pass (run it once here). Expected: NONE undefined.
- [ ] **Step 4: Commit.** `git commit -am "feat(ch18): 18.2 signal + anti-lookahead protocol"`

---

## Task 6: §18.3 The P&L engine: the gamma identity + Fig B

**Files:** Modify `vol-learning-guide/chapters/18-ivrv-straddle.tex`

- [ ] **Step 1: Draft §18.3** (`\label{sec:ivrv:pnl-engine}`). Equation pattern for each:
  - `\label{eq:ivrv:aw-daily}`: $\,d\Pi = \tfrac{1}{2}(\sigma^2-\tilde\sigma^2)\,S^2\,\Gamma^{i}\,dt\,$ — `\citep[Eq.~1, p.~67]{AhmadWilmott2005}`; $\sigma$ realized vol, $\tilde\sigma$ implied vol, $\Gamma^i$ gamma at implied vol.
  - `\label{eq:ivrv:aw-total}`: $\,\Pi = \tfrac12\!\int_{t_0}^{T} e^{-r(t-t_0)}(\sigma^2-\tilde\sigma^2)S^2\Gamma^{i}\,dt\,$ ("always positive but path-dependent").
  - `\label{eq:ivrv:daily-discrete}`: $\,\text{PnL}_t \approx \tfrac12\Gamma_t S_t^2(\RV_t - \IVol^2/252)\,$, $\RV_t$ = day-$t$ realized **variance**.
  - **Notation reconciliation paragraph + footnote** mapping to ch09's vol-form `\Cref{eq:gamma-pnl-simple}` ($\RV^2$ there = variance here). This is the most error-prone seam (spec §12) — be explicit.
  - `\citep{CarrMadan2002}` for the variance-swap contrast; cross-ref `\Cref{sec:var-swap}` (do not re-derive the log contract).
  - `workedexample`: 3-day delta-hedged straddle P&L.
- [ ] **Step 2: Add Fig B** (`fig:ivrv:dollar-gamma`, pgfplots): dollar-gamma weight $S^2\Gamma$ vs spot, peaking ATM and decaying in the wings.
- [ ] **Step 3: Compile (full resolve)** → `EXIT=0`; undefined-cite check → NONE.
- [ ] **Step 4: Verify Fig B** with `verify-diagram` (concept: "where the variance bet is concentrated in spot"; relationship: single-peak at ATM, decay in both wings). Loop until pass.
- [ ] **Step 5: Commit.** `git commit -am "feat(ch18): 18.3 gamma-PnL engine + dollar-gamma figure"`

---

## Task 7: §18.4 Where the clean identity breaks (vanna, volga, jumps, discreteness)

**Files:** Modify `vol-learning-guide/chapters/18-ivrv-straddle.tex`

- [ ] **Step 1: Draft §18.4** (`\label{sec:ivrv:breaks}`). Equation pattern:
  - `\label{eq:ivrv:vanna}` **Vanna** $=\dfrac{\partial^2 V}{\partial S\,\partial\sigma}=-e^{-q\tau}N'(d_1)\dfrac{d_2}{\sigma}$ (define on first use; standard BS Greek).
  - `\label{eq:ivrv:volga}` **Volga** $=\dfrac{\partial^2 V}{\partial\sigma^2}=\Vega\cdot\dfrac{d_1 d_2}{\sigma}$.
  - `\label{eq:ivrv:bkl-rmse}` $\,\text{RMSE}=g/\sqrt{N}+O(1/N)\,$, with the mixed-normal limit and granularity $g$ — `\citep[Thm~1c Eq.~2.13; Eq.~2.18]{BertsimasKoganLo2000}`; note vanilla payoffs use **Thm 2 (Eq. 2.17)**.
  - `\citep{CarrLee2009}` for the third-order jump error; `warning` box: "a single straddle is not a clean variance bet off-strike."
- [ ] **Step 2: Compile (full resolve)** → `EXIT=0`; undefined-cite check → NONE (`BertsimasKoganLo2000`, `CarrLee2009`).
- [ ] **Step 3: Commit.** `git commit -am "feat(ch18): 18.4 vanna/volga/jumps and continuous-vs-discrete"`

---

## Task 8: §18.5 Option transaction costs + Fig D

**Files:** Modify `vol-learning-guide/chapters/18-ivrv-straddle.tex`

- [ ] **Step 1: Draft §18.5** (`\label{sec:ivrv:option-costs}`). Equation pattern:
  - `\label{eq:ivrv:vega-cost}` $\,c_{\text{opt}}=\Vega\cdot\tfrac12(\sigma_{\text{ask}}-\sigma_{\text{bid}})\,$, charged on entry/flip/exit only.
  - Facts with anchors: `\citet{MuravyevPearson2020}` (8.1¢ / 6.2¢ / 1.3¢; long–short straddle 22.7%→3.9%/mo at quoted); `\citet{DoshiPariShamsuddin2025}` (≈2% at 21–48 DTE → ≈9% at 0DTE; roll-date spike; cross-venue routing); `\citet{FrancoisEtAl2025}` (κ₂∈{0.5–2}% per change); `\citet{WysockiSlepaczuk2024}` (midpoint + half-spread per execution).
  - `warning` box: make-or-break, report a cost band; cross-ref ch17 `\Cref{sec:net-econ-value}` for the turnover/Sharpe-drag mechanics (do not repeat).
- [ ] **Step 2: Add Fig D** (`fig:ivrv:cost-band`, pgfplots): pooled Sharpe vs cost assumption (quoted / effective / timing-aware) as a band.
- [ ] **Step 3: Compile (full resolve)** → `EXIT=0`; undefined-cite check → NONE.
- [ ] **Step 4: Verify Fig D** with `verify-diagram` (concept: "how much of the edge survives each cost assumption"; relationship: Sharpe monotonically falls quoted<effective<timing-aware... i.e. lowest under quoted). Loop until pass.
- [ ] **Step 5: Commit.** `git commit -am "feat(ch18): 18.5 option transaction costs + cost-band figure"`

---

## Task 9: §18.6 Delta-hedge costs: Leland and its modern critique

**Files:** Modify `vol-learning-guide/chapters/18-ivrv-straddle.tex`

- [ ] **Step 1: Draft §18.6** (`\label{sec:ivrv:leland}`). Equation pattern:
  - `\label{eq:ivrv:leland-vol}` $\,\hat\sigma^2=\sigma^2\!\big(1+\sqrt{\tfrac{2}{\pi}}\,\tfrac{k}{\sigma\sqrt{dt}}\big)\,$ — `\citep[Eq.~5]{ZhaoZiemba2007}` (orig. `\citet{Leland1985}`); explain $\sqrt{2/\pi}\approx0.798$ as the half-normal mean $\E|\Delta H|$.
  - `\citet{KabanovSafarian1997}`: constant costs ⇒ non-vanishing, negative error (under-hedging). `\citet{LepinetteKabanov2010}`: $k_n=k_0 n^{-1/2}\Rightarrow$ MSE $\propto n^{-1}$ for convex payoffs.
  - `\label{eq:ivrv:ww-band}` Whalley–Wilmott band $\,h_{WW}=\big(\tfrac{3\lambda\delta S\Gamma^2}{2\gamma}\big)^{1/3}\,$ — `\citep{ArzelLehdili2026}`; one-line `\citep{BrugiereTurinici2025}` NN-beats-Leland note.
  - `warning`: "Leland is a deterministic cost-line inflator, not the optimal policy." Cross-ref ch17 `\Cref{eq:turnover-vt}`, `\Cref{eq:sharpe-drag}`.
- [ ] **Step 2: Compile (full resolve)** → `EXIT=0`; undefined-cite check → NONE (`Leland1985`,`ZhaoZiemba2007`,`KabanovSafarian1997`,`LepinetteKabanov2010`,`ArzelLehdili2026`,`BrugiereTurinici2025`).
- [ ] **Step 3: Commit.** `git commit -am "feat(ch18): 18.6 Leland hedging cost and its modern critique"`

---

## Task 10: §18.7 Discrete-hedging-error variance (signature section) + Fig C

**Files:** Modify `vol-learning-guide/chapters/18-ivrv-straddle.tex`

- [ ] **Step 1: Draft §18.7** (`\label{sec:ivrv:hedging-error}`). Equation pattern, with the κ-derivation shown in full:
  - `\label{eq:ivrv:boyle-emanuel}` per-step $\,H_i=\tfrac12\Gamma S^2\sigma^2 dt\,(x_i^2-1)\,$, $x_i\sim\N(0,1)$, $x_i^2\sim\chi^2_1$; total std $\propto\tfrac12 S^2\sigma^2(T-t)\Gamma\sqrt{1/N}$ — `\citep[Eq.~7]{AnagnouHodges2007}` (orig. Boyle–Emanuel 1980 `\citep{BoyleEmanuel1980}`); Gaussian $\Var(x_i^2)=2$.
  - `keyresult` box `\label{eq:ivrv:kappa-inflation}` — **derive in full** (spec §12 risk note): $\Var(H_i)=(\tfrac12\Gamma S^2\sigma^2 dt)^2(\kappa-1)$, with $dt=T/N$ summing $N$ steps ⇒ total variance $=(\tfrac12\Gamma S^2\sigma^2)^2 T^2(\kappa-1)/N \propto \sigma^4(\kappa-1)/N$. Label this **your own leptokurtic extension — not in Boyle–Emanuel, Anagnou–Hodges, or Ahmad–Wilmott**.
  - **Prominent `warning` (the misattribution):** Ahmad–Wilmott Result 2 `\label{eq:ivrv:aw-result2}` $=G(S_0,t_0)-F(S_0,t_0)^2$ (`\citep[§4.2 Eq.~10, p.~70]{AhmadWilmott2005}`) is a continuous-hedge stock-path variance with **no 1/N, no kurtosis** — do not attribute the discrete formula to it.
  - `\label{eq:ivrv:bennett}` Bennett vega-form $\,\sigma_{\text{P\&L}}=\Vega\,\sigma\sqrt{\pi/(4N)}\,$ — `\citep[p.~95]{Bennett2014}` (context-only); note the $\sqrt{\pi/4}\approx0.886$ vs $1/\sqrt2\approx0.707$ coefficient tension.
  - `\citep{BrodenTankov2010}`: jump lower-bound ($\lim n\E[\varepsilon^2]>0$, may be ∞).
- [ ] **Step 2: Add Fig C** (`fig:ivrv:error-vs-n`, pgfplots): hedging-error std vs $N$, the $1/\sqrt N$ curve with a Broden–Tankov jump floor overlaid.
- [ ] **Step 3: Compile (full resolve)** → `EXIT=0`; undefined-cite check → NONE (incl. reused `Bennett2014`).
- [ ] **Step 4: Verify Fig C** with `verify-diagram` (concept: "discrete-hedging error shrinks as 1/√N but a jump floor stops it reaching zero"; relationship: decreasing curve asymptoting to a positive floor, not to zero). Loop until pass.
- [ ] **Step 5: Commit.** `git commit -am "feat(ch18): 18.7 discrete-hedging-error variance + kappa extension + figure"`

---

## Task 11: §18.8 Calibrating kurtosis κ from 5-minute data

**Files:** Modify `vol-learning-guide/chapters/18-ivrv-straddle.tex`

- [ ] **Step 1: Draft §18.8** (`\label{sec:ivrv:kurtosis}`). Equation pattern:
  - `\label{eq:ivrv:realized-kurtosis}` $\,RK_t=\dfrac{n\sum_i r_{t,i}^4}{(\sum_i r_{t,i}^2)^2}\,$ — `\citet{AmayaEtAl2015}`; robust to noise (RV is the noise-sensitive moment, not RM4).
  - `\citet{AhadzieJeyasreedharan2020}`: interval-variance, 5→15-min CLT is a convention; κ=4.0 conservative but cross-sectionally heterogeneous.
  - `warning` box ("κ=4 is a convention, estimate per symbol, stress it"); `workedexample`: an $RK$ number from a toy day.
- [ ] **Step 2: Compile (full resolve)** → `EXIT=0`; undefined-cite check → NONE.
- [ ] **Step 3: Commit.** `git commit -am "feat(ch18): 18.8 kurtosis calibration from 5-min data"`

---

## Task 12: §18.9 Assembling the backtest (algorithm) + Fig E

**Files:** Modify `vol-learning-guide/chapters/18-ivrv-straddle.tex`

- [ ] **Step 1: Draft §18.9** (`\label{sec:ivrv:algorithm}`). A numbered `keyidea` **algorithm box** `\label{alg:ivrv:backtest}` per (symbol, day): measure $\widehat{\RV}_t,\IVol_{t-1}$ pre-3:55 → form $X_{t-1}$, decide short/long/flat + graded size (§18.2) → charge $c_{\text{opt}}$ on entry/flip/exit (§18.5) → intraday delta-hedge $N$ times charging hedge cost (§18.6) → daily MTM via `\Cref{eq:ivrv:daily-discrete}` → accumulate per-(symbol,day) P&L + attach hedging-error variance `\Cref{eq:ivrv:kappa-inflation}` with calibrated κ (§18.8). Reference each prior section by `\Cref`.
- [ ] **Step 2: Add Fig E** (`fig:ivrv:waterfall`): P&L-attribution waterfall (gross gamma P&L − option cost − hedge cost − hedging-error drag = net).
- [ ] **Step 3: Compile (full resolve)** → `EXIT=0`; undefined-ref check → confirm all `\Cref` targets resolve.
- [ ] **Step 4: Verify Fig E** with `verify-diagram` (concept: "where the gross edge leaks before reaching net P&L"; relationship: descending bars gross→net through three cost deductions). Loop until pass.
- [ ] **Step 5: Commit.** `git commit -am "feat(ch18): 18.9 backtest algorithm + PnL-attribution waterfall"`

---

## Task 13: §18.10 Evaluation: from QLIKE to deflated Sharpe

**Files:** Modify `vol-learning-guide/chapters/18-ivrv-straddle.tex`

- [ ] **Step 1: Draft §18.10** (`\label{sec:ivrv:evaluation}`). Equation pattern:
  - Pooled vs per-symbol Sharpe; block-bootstrap by **day**. Cross-ref the DSR closed form `\Cref{eq:dsr}` and SR₀ `\Cref{eq:expected-max-sr}` (restate, do not re-derive) — `\citet{Bailey2014DSR}`.
  - **`warning` (three traps):** denominator uses observed $\widehat{\SR}$ not $\SR_0$; non-annualized inputs, $T$=#obs; $\SR_0=\sqrt{2\ln 20}=2.45$ for $N=20$. **Disambiguate $\gamma_{EM}$ (Euler–Mascheroni ≈0.5772) from $\gamma_3,\gamma_4$ (skew/kurtosis)** explicitly (spec §12).
  - QLIKE→economic bridge — `\citet{Pollok2025}` (qualitative only; Pollok uses no DM/MCS); cross-ref `\Cref{sec:eval-qlike}`, `\Cref{sec:eval-dm}`, `\Cref{sec:eval-mcs}`.
  - Economic foundation — `\citet{BakshiKapadia2003}` (negative VRP); cross-ref ch09.
  - `application` box: the QLIKE→money punchline.
- [ ] **Step 2: Compile (full resolve)** → `EXIT=0`; undefined-cite check → NONE (`Bailey2014DSR`,`Pollok2025`,`BakshiKapadia2003`).
- [ ] **Step 3: Commit.** `git commit -am "feat(ch18): 18.10 evaluation -- pooled & deflated Sharpe, QLIKE bridge"`

---

## Task 14: §18.11 Four experiments + §18.12 Summary & caveats

**Files:** Modify `vol-learning-guide/chapters/18-ivrv-straddle.tex`

- [ ] **Step 1: Draft §18.11** (`\label{sec:ivrv:experiments}`) as a `projectconnection` box with the 4 experiments, each with its explicit pass criterion (spec §18.11): (1) hedging-error floor sim $N\in\{1..26\}$, fit $\Var=a/N+b$, κ∈{3,4,6}; (2) cost-band Sharpe (a/b/c); (3) PnL regressed on $(\RV-\IVol^2/252)$ and forecast error, DM-significance; (4) pooled vs per-symbol + DSR with honest $N$.
- [ ] **Step 2: Draft §18.12** (`\label{sec:ivrv:summary}`): `keyresult` recap + the single biggest `warning` caveat (every economic source is daily 1993–2023; intraday mechanics must be simulated).
- [ ] **Step 3: Compile (full resolve)** → `EXIT=0`; undefined-ref/cite check → NONE.
- [ ] **Step 4: Commit.** `git commit -am "feat(ch18): 18.11 experiments + 18.12 summary and caveats"`

---

## Task 15: Pass 2 (verifier) + Pass 3 (condenser) — parallel subagents

- [ ] **Step 1: Dispatch the verifier subagent** (`model: opus`) with the `write-chapter` Pass 2 prompt against `vol-learning-guide/chapters/18-ivrv-straddle.tex`: for every `\citep`/`\citet`, find the paper in `reference/project-papers/`, read the cited pages, and verify every formula (signs, terms, notation) and every quantitative claim matches the source; flag discrepancies as CRITICAL with [chapter line, claim, source says, page]. Pay special attention to: the Ahmad–Wilmott "no 1/N, no kurtosis" claim, the BKL Thm 2 attribution, the Boyle–Emanuel per-step form, the Leland √(2/π), and the DSR denominator (observed SR̂).
- [ ] **Step 2: Dispatch the condenser subagent** (`model: opus`) with the `write-chapter` Pass 3 prompt (flag true redundancy only; do NOT flag intuition/projectconnection boxes).
- [ ] **Step 3: Consolidate.** Apply verifier corrections (fix any formula/claim mismatch; add citations + bib entries if suggested) and condenser cuts. Re-compile (full resolve) → `EXIT=0`, undefined check → NONE.
- [ ] **Step 4: Commit.** `git commit -am "fix(ch18): apply Pass 2 verification + Pass 3 condensing"`

---

## Task 16: Pass 4 (naive-reader) — sequential subagent

- [ ] **Step 1: Dispatch the naive-reader subagent** (`model: opus`) with the `write-chapter` Pass 4 prompt against the chapter: flag every equation lacking a plain-English "what it means" box or a vol-forecasting connection (CRITICAL), every undefined term, every logical jump, every place a diagram would help.
- [ ] **Step 2: Apply ALL feedback** — add plain-English translations, project connections, and any diagrams flagged (verify any new TikZ with `verify-diagram`). Confirm every equation follows the mandatory 5-part pattern.
- [ ] **Step 3: Compile (full resolve)** → `EXIT=0`; undefined-ref/cite check → NONE.
- [ ] **Step 4: Commit.** `git commit -am "fix(ch18): apply Pass 4 naive-reader clarifications"`

---

## Task 17: Final clean compile + acceptance check

- [ ] **Step 1: Full clean compile.** `cd vol-learning-guide && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex; echo EXIT=$?`  Expected `EXIT=0`.
- [ ] **Step 2: Zero undefined refs/cites.** Run the undefined-ref/cite check → `NONE`. Also `grep -c "Citation .* undefined" main.log` → 0.
- [ ] **Step 3: Acceptance scan (spec §11).** Confirm: all 7 components present; every equation has intuition + projectconnection boxes; the AW misattribution warning and the κ-derivation are present; zero forward references (all `\Cref` point to ch08/09/16/17 or earlier in ch18); algorithm box + 4 experiments + 5 figures present; chapter in TOC.
- [ ] **Step 4: Commit the compiled PDF + aux.** `git add vol-learning-guide/main.pdf vol-learning-guide/main.aux vol-learning-guide/main.toc vol-learning-guide/main.out; git commit -m "build(vol-guide): compile with ch18 IV-RV straddle"`

---

## Task 18: Markdown mirror via convert-chapter-markdown

**Files:** Create `vol-learning-guide/markdown/ch18-ivrv-straddle.md`

- [ ] **Step 1: Invoke `convert-chapter-markdown`** with: source `vol-learning-guide/chapters/18-ivrv-straddle.tex`; output `vol-learning-guide/markdown/ch18-ivrv-straddle.md`; preamble `vol-learning-guide/preamble.tex`; omit `workedexample` boxes (skill default). Recreate Fig A and Fig E as Mermaid flowcharts; describe pgfplots Figs B/C/D in italicized prose with key values.
- [ ] **Step 2: Run the skill's Step 4 verification checklist** (no dropped content, math `$`/`$$` balanced, boxes labeled, Mermaid valid, cross-refs resolve to the right `chXX-*.md` filenames per `main.tex` order, no em dashes).
- [ ] **Step 3: Update the markdown INDEX** if one exists in `vol-learning-guide/markdown/` (add the ch18 entry).
- [ ] **Step 4: Commit.** `git add vol-learning-guide/markdown/ch18-ivrv-straddle.md; git commit -m "docs(vol-guide): markdown mirror of ch18"`

---

## Task 19: Record completion in memory + research journal

- [ ] **Step 1: Update memory** `project_status.md` (note ch18 authored, on branch `research/ivrv-straddle-backtest`).
- [ ] **Step 2: Append a session entry** to `notes/research-journal.md` summarizing the chapter and linking the spec/plan and the deep-research brief.
- [ ] **Step 3: Commit.** `git add notes/research-journal.md; git commit -m "docs: journal entry for ch18 IV-RV straddle"`

---

## Self-Review

**1. Spec coverage** (every spec §5 section → a task): §18.1→T4, §18.2→T5, §18.3→T6, §18.4→T7, §18.5→T8, §18.6→T9, §18.7→T10, §18.8→T11, §18.9→T12, §18.10→T13, §18.11+§18.12→T14. Spec §6 figures A–E → T4/T6/T8/T10/T12. Spec §7 bib → T1 (corrected to **22** keys: spec omitted `FrancoisEtAl2025`, added here). Spec §9 macros → T2. Quality passes (write-chapter Pass 2/3/4) → T15/T16. Compile + markdown mirror + memory → T17/T18/T19. No gaps.

**2. Placeholder scan:** Bib entries are concrete (Task 1) with a source-verification step for unconfirmable author first names — not placeholders. Section tasks carry the exact equations, labels, and citation keys; connecting prose is generated at execution per the stated equation pattern (this is a writing task, so prose is the deliverable, not plan content). No "TBD/TODO/handle edge cases."

**3. Type/label consistency:** Label scheme `sec:ivrv:` / `eq:ivrv:` / `fig:ivrv:` / `alg:ivrv:` used uniformly; equation keys referenced in later tasks (`eq:ivrv:daily-discrete` in T12, `eq:ivrv:kappa-inflation` in T12) are defined in earlier tasks (T6, T10). Cross-ref targets (`sec:greeks`, `sec:var-swap`, `sec:vrp-definition`, `sec:gamma-pnl`, `eq:gamma-pnl-simple`, `eq:qlike`, `eq:dm-stat`, `eq:dsr`, `eq:expected-max-sr`, `sec:eval-lookahead-taxonomy`, `tab:lookahead-taxonomy`, `sec:net-econ-value`, `eq:turnover-vt`, `eq:sharpe-drag`) are all verified-present labels from the exploration of ch08/09/16/17. Bib keys cited in tasks all appear in Task 1 or are confirmed-existing (`Bailey2014DSR`, `Bennett2014`).
