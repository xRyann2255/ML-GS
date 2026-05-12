# Vol-Project-Ref Part V Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Part V ("The Build") to the vol-project-ref LaTeX guide with three new chapters (ch15: pipeline, ch16: architecture, ch17: development plan) and a detailed development plan markdown file.

**Architecture:** Three new `.tex` chapter files created from scratch, one markdown plan file, and a small modification to `main.tex`. All LaTeX follows existing guide conventions (report class, booktabs, TikZ, tcolorbox keyidea/warning boxes only, natbib). Design spec: `docs/superpowers/specs/2026-05-12-vol-project-ref-part-v-design.md`.

**Tech Stack:** LaTeX (report class, booktabs, longtable, TikZ, tcolorbox, natbib), Markdown

---

## File Structure

### Files to Create

| File | Responsibility |
|---|---|
| `guides/vol-project-ref/chapters/ch15-pipeline.tex` | Data-to-feature pipeline: lineage funnel diagram + complete feature matrix table |
| `guides/vol-project-ref/chapters/ch16-architecture.tex` | System architecture: three ensemble architectures compared (feature stacking, residual stacking, prediction blending) |
| `guides/vol-project-ref/chapters/ch17-development-plan.tex` | Development plan: milestones M1-M7, critical path diagram, minimum viable deliverable |
| `docs/project-plans/development-plan.md` | Detailed development plan: task-level breakdowns for each milestone, used to generate session prompts |

### Files to Modify

| File | Change |
|---|---|
| `guides/vol-project-ref/main.tex:66` | Insert Part V block with three `\input{}` lines before `\bibliographystyle` |

---

## Chunk 1: main.tex + ch15-pipeline.tex

### Task 1: Add Part V to main.tex

**Files:**
- Modify: `guides/vol-project-ref/main.tex:66`

- [ ] **Step 1: Insert Part V block**

Add the following immediately before the `\bibliographystyle{plainnat}` line (currently line 66):

```latex
% ══════════════════════════════════════════════════════════════
% Part V — The Build
% ══════════════════════════════════════════════════════════════

\part{The Build}

\input{chapters/ch15-pipeline}
\input{chapters/ch16-architecture}
\input{chapters/ch17-development-plan}

```

After editing, the file should read `\part{The Build}` followed by the three `\input` lines, then a blank line, then `\bibliographystyle{plainnat}`.

- [ ] **Step 2: Commit**

```bash
git add guides/vol-project-ref/main.tex
git commit -m "feat(vol-ref): add Part V structure to main.tex"
```

---

### Task 2: Write ch15-pipeline.tex

**Files:**
- Create: `guides/vol-project-ref/chapters/ch15-pipeline.tex`

**Context:** This chapter maps feature lineage: raw data source to daily measure to model-ready feature. It does NOT repeat measure formulas (ch03-07), source descriptions (ch02), selection rationale (ch08), or model configuration (ch09). It answers one question: "how does raw data become this feature?"

- [ ] **Step 1: Write the complete chapter**

Create `guides/vol-project-ref/chapters/ch15-pipeline.tex` with exactly this content:

```latex
\chapter{The Data-to-Feature Pipeline}
\label{ch:pipeline}

Every feature in the model traces back to one of the six raw data sources in Chapter~\ref{ch:our-data}.
This chapter maps that lineage: source to measure to feature.
For measure formulas, see Chapters~\ref{ch:har-core}--\ref{ch:cross-asset}.
For selection rationale, see Chapter~\ref{ch:feature-composition}.


%% ──────────────────────────────────────────────
\section{Data Lineage}
\label{sec:data-lineage}
%% ──────────────────────────────────────────────

Figure~\ref{fig:data-funnel} shows how data narrows and expands through the pipeline.
Six raw sources produce approximately 18 daily scalar measures.
These measures pass through lagging, rolling-window aggregation, and triple expansion to produce the final 80--120 feature matrix.

\begin{figure}[htbp]
\centering
\resizebox{\textwidth}{!}{%
\begin{tikzpicture}[
  node distance=0.4cm and 1.0cm,
  >=Stealth,
  stage/.style={draw, rounded corners, minimum height=1.2cm, minimum width=2.6cm,
    align=center, font=\small},
  arrow/.style={-{Stealth[length=2.5mm]}, thick},
  countlabel/.style={font=\small\bfseries, text=defblue},
]
  \node[stage, fill=blue!8] (src) {Raw Sources};
  \node[stage, fill=green!8, right=1.2cm of src] (meas) {Daily Measures};
  \node[stage, fill=green!8, right=1.2cm of meas] (lag) {Lag \& Window\\d / w / m + shift(1)};
  \node[stage, fill=orange!8, right=1.2cm of lag] (exp) {Triple Expansion\\level / $\Delta$ / $z$};
  \node[stage, fill=orange!8, right=1.2cm of exp] (feat) {Feature Matrix};

  \draw[arrow] (src) -- (meas);
  \draw[arrow] (meas) -- (lag);
  \draw[arrow] (lag) -- (exp);
  \draw[arrow] (exp) -- (feat);

  \node[countlabel, above=0.2cm of src] {6};
  \node[countlabel, above=0.2cm of meas] {$\sim$18};
  \node[countlabel, above=0.2cm of lag] {$\sim$30--40};
  \node[countlabel, above=0.2cm of exp] {$\times\,3$};
  \node[countlabel, above=0.2cm of feat] {80--120};
\end{tikzpicture}%
}
\caption{Data lineage funnel.
Blue: raw inputs (Ch.~\ref{ch:our-data}).
Green: intermediate measures (Chs.~\ref{ch:har-core}--\ref{ch:cross-asset}).
Orange: model-ready features.
Counts show approximate dimensionality at each stage.}
\label{fig:data-funnel}
\end{figure}


%% ──────────────────────────────────────────────
\section{Complete Feature Matrix}
\label{sec:feature-matrix}
%% ──────────────────────────────────────────────

Table~\ref{tab:feature-matrix} lists every feature in the planned feature set.
Read across any row to trace a feature from its source measure through to its final form.
Features with d/w/m variants share the same derivation pattern and are collapsed into one row.

{\scriptsize
\begin{longtable}{@{}cl p{2.4cm} p{4.6cm} l@{}}
\caption{Complete feature matrix with source lineage.
Features marked d/w/m apply the same derivation at daily, weekly (5d), and monthly (22d) horizons.}
\label{tab:feature-matrix} \\
\toprule
\textbf{Layer} & \textbf{Feature} & \textbf{Source Measure} & \textbf{Derivation} & \textbf{Expansion} \\
\midrule
\endfirsthead
\multicolumn{5}{c}{\small Table~\ref{tab:feature-matrix} (continued)} \\
\toprule
\textbf{Layer} & \textbf{Feature} & \textbf{Source Measure} & \textbf{Derivation} & \textbf{Expansion} \\
\midrule
\endhead
\midrule \multicolumn{5}{r}{\small Continued on next page} \\
\endfoot
\bottomrule
\endlastfoot

% ── Layer 0: HAR Core ──
0 & \texttt{log\_rv\_d/w/m} & rv & $\log$ [+ rolling mean 5d/22d], shift(1) & --- \\
0 & \texttt{sqrt\_rq\_d} & rq & $\sqrt{\cdot}$, shift(1) & --- \\
0 & \texttt{rq\_rv\_interaction} & rq, rv & $\sqrt{\text{rq}} \cdot \log(\text{rv})$, shift(1) & --- \\
0 & \texttt{overnight\_return} & open, close (TSDB) & $\log(\text{open}_t / \text{close}_{t-1})$, shift(1) & --- \\
\midrule

% ── Layer 1: Asymmetry & Jumps ──
1 & \texttt{log\_rs\_positive\_d/w/m} & rs\_positive & $\log$ [+ rolling mean 5d/22d], shift(1) & --- \\
1 & \texttt{log\_rs\_negative\_d/w/m} & rs\_negative & $\log$ [+ rolling mean 5d/22d], shift(1) & --- \\
1 & \texttt{log\_bpv\_d/w} & bpv & $\log$ [+ rolling mean 5d], shift(1) & --- \\
1 & \texttt{log\_jump\_variation\_d} & jump\_variation & $\log$, shift(1) & --- \\
1 & \texttt{log\_continuous\_var\_d/w} & continuous\_variation & $\log$ [+ rolling mean 5d], shift(1) & --- \\
1 & \texttt{signed\_return\_d} & close (TSDB) & $\log(\text{close}_t / \text{close}_{t-1})$, shift(1) & --- \\
\midrule

% ── NR: Noise-Robust Estimators ──
NR & \texttt{log\_rk\_d/w} & rk (tick prices) & $\log$ [+ rolling mean 5d], shift(1) & --- \\
NR & \texttt{noise\_gap\_d/w} & noise\_gap & [rolling mean 5d], shift(1) & --- \\
\midrule

% ── Layer 2: Options-Implied ──
2 & \texttt{atm\_iv\_1m, \_3m} & atm\_iv (Marquee) & shift(1) & lev/$\Delta$/$z$ \\
2 & \texttt{vrp} & atm\_iv, rv & $\text{IV}^2 - \RV$, shift(1) & lev/$\Delta$/$z$ \\
2 & \texttt{skew\_1m} & skew (Marquee) & shift(1) & lev/$\Delta$/$z$ \\
2 & \texttt{term\_slope} & atm\_iv (3m, 1m) & ATM$_{3m}$ $-$ ATM$_{1m}$, shift(1) & lev/$\Delta$/$z$ \\
2 & \texttt{butterfly\_1m} & skew, atm\_iv & $0.5(\text{IV}_{25\delta P} {+} \text{IV}_{25\delta C}) {-} \text{IV}_{\text{ATM}}$, shift(1) & lev/$\Delta$/$z$ \\
2 & \texttt{vvix} & VVIX (TSDB) & shift(1) & lev/$\Delta$/$z$ \\
2 & \texttt{iv\_rv\_gap} & atm\_iv, rv & $\text{IV} - \sqrt{\RV \times 252}$, shift(1) & lev/$\Delta$/$z$ \\
2 & \texttt{stock\_atm\_iv} & EDRVOL (Marquee) & shift(1) & lev/$\Delta$/$z$ \\
2 & \texttt{stock\_vrp} & stock\_atm\_iv, rv & stock $\text{IV}^2 - \RV$, shift(1) & lev/$\Delta$/$z$ \\
\midrule

% ── Layer 3: Microstructure ──
3 & \texttt{price\_acceleration} & E-mini mid-price & 2nd derivative (win=50), daily agg, shift(1) & lev/$\Delta$/$z$ \\
3 & \texttt{obi} & E-mini L2 bid/ask & $(\Sigma\text{bid} {-} \Sigma\text{ask})/(\Sigma\text{bid} {+} \Sigma\text{ask})$, daily agg, shift(1) & lev/$\Delta$/$z$ \\
3 & \texttt{depth\_ratio} & E-mini L2 depth & $\log(\text{bid depth}/\text{ask depth})$, daily agg, shift(1) & lev/$\Delta$/$z$ \\
3 & \texttt{spread\_mean/std} & E-mini bid/ask & mean/std spread (bps), shift(1) & lev/$\Delta$/$z$ \\
3 & \texttt{vpin} & E-mini trades & VPIN algorithm, shift(1) & lev/$\Delta$/$z$ \\
3 & \texttt{kyle\_lambda} & E-mini trades & regress($\Delta$mid, signed vol), shift(1) & lev/$\Delta$/$z$ \\
\midrule

% ── Layer 4: Cross-Asset ──
4 & \texttt{treasury\_slope} & 10y, 2y yields & 10y $-$ 2y (bps), shift(1) & lev/$\Delta$/$z$ \\
4 & \texttt{fx\_vol} & USD/JPY, EUR/USD & annualized rolling RV (22d), shift(1) & lev/$\Delta$/$z$ \\
4 & \texttt{commodity\_vol} & CL, GC (TSDB) & annualized rolling RV (22d), shift(1) & lev/$\Delta$/$z$ \\
4 & \texttt{vix\_level} & VIX close (TSDB) & shift(1) & lev/$\Delta$/$z$ \\
4 & \texttt{vix\_futures\_slope} & VX1, VX2 (TSDB) & VX2 $-$ VX1, shift(1) & lev/$\Delta$/$z$ \\
4 & \texttt{dy\_spillover} & panel of RVs (35) & DY FEVD ($h{=}10$, $p{=}4$), shift(1) & lev/$\Delta$/$z$ \\
\midrule

% ── Layer 5: Calendar ──
5 & \texttt{fomc\_proximity} & FOMC calendar & days to next FOMC, shift(1) & --- \\
5 & \texttt{nfp\_proximity} & NFP calendar & days to next NFP, shift(1) & --- \\
5 & \texttt{opex\_proximity} & calendar math & days to next monthly OpEx, shift(1) & --- \\
5 & \texttt{earnings\_proximity} & earnings calendar & days to next earnings, shift(1) & --- \\
5 & \texttt{day\_of\_week} & date & categorical encoding & --- \\
5 & \texttt{month} & date & categorical encoding & --- \\
\midrule

% ── Layer 6: Memory ──
6 & \texttt{frac\_diff\_rv} & rv & $(1-L)^d$, $d \approx 0.35$--$0.45$, shift(1) & lev/$\Delta$/$z$ \\
6 & \texttt{hurst\_exponent} & rv & rolling Hurst (22d), shift(1) & lev/$\Delta$/$z$ \\
6 & \texttt{vol\_of\_vol} & rv & std($\RV$) over 22d, shift(1) & lev/$\Delta$/$z$ \\
6 & \texttt{regime\_duration} & rv & days since last $2\sigma$ spike, shift(1) & --- \\
\midrule

% ── Layer 7: Sentiment ──
7 & \texttt{finbert\_sentiment} & news text & daily FinBERT score, shift(1) & lev/$\Delta$/$z$ \\
7 & \texttt{negative\_news\_count} & news text & count of negative articles, shift(1) & --- \\

\end{longtable}
}

\noindent
\textbf{Notes.}\enspace
``NR'' = noise-robust estimators computed from tick-level log prices, not 5-min bars.
``Expansion'' shows which features receive the \{level, change, $z$-score\} triple expansion for LightGBM (Chapter~\ref{ch:feature-composition}).
Features marked ``---'' are used as-is.
Rolling means compute the average in variance space first, then take log \citep{Corsi2009}.
\texttt{noise\_gap} is a ratio, not log-transformed.
Deferred features (event-implied vol, sector-mean RV, cross-asset RV rank, WAP log returns, signed volume flow) can be added in later iterations.
For layer-level summaries and feature counts per model family, see Chapter~\ref{ch:lightgbm} Table~9.1.


%% ──────────────────────────────────────────────
%% Boxes
%% ──────────────────────────────────────────────

\begin{keyidea}[Every Row Traces Back to Source]
The feature matrix is the blueprint.
To understand any feature, read across: the source measure tells you where the data comes from (Chapter~\ref{ch:our-data}), the derivation tells you the transformation chain, and the expansion column tells you what LightGBM sees.
\end{keyidea}

\begin{warning}[Look-Ahead Lives in the Derivation Column]
Every derivation must include shift(1) or equivalent.
Any feature whose derivation does not include an explicit lag uses information from the forecast target period.
The most subtle violations come from rolling windows that include day $t$ when predicting day $t{+}1$.
\end{warning}
```

- [ ] **Step 2: Verify the file was created correctly**

Run: `wc -l guides/vol-project-ref/chapters/ch15-pipeline.tex`
Expected: approximately 150--180 lines.

- [ ] **Step 3: Commit**

```bash
git add guides/vol-project-ref/chapters/ch15-pipeline.tex
git commit -m "feat(vol-ref): add ch15 data-to-feature pipeline chapter"
```

---

## Chunk 2: ch16-architecture.tex + ch17-development-plan.tex

### Task 3: Write ch16-architecture.tex

**Files:**
- Create: `guides/vol-project-ref/chapters/ch16-architecture.tex`

**Context:** This chapter presents feature stacking and residual stacking as alternatives to ch11's prediction blending. It does NOT re-describe prediction blending (ch11), model internals (ch09-10), or the system-level pipeline (ch14). The three-panel TikZ diagram is the centerpiece.

- [ ] **Step 1: Write the complete chapter**

Create `guides/vol-project-ref/chapters/ch16-architecture.tex` with exactly this content:

```latex
\chapter{System Architecture}
\label{ch:architecture}

Chapter~\ref{ch:ensemble} presents prediction blending: two independent model branches combined at the forecast level.
This chapter presents two alternative ensemble architectures, feature stacking and residual stacking, and compares all three.


%% ──────────────────────────────────────────────
\section{Three Architectures}
\label{sec:three-architectures}
%% ──────────────────────────────────────────────

Figure~\ref{fig:architecture-comparison} shows the data and prediction flow for each architecture side by side.

\begin{figure}[htbp]
\centering
\resizebox{\textwidth}{!}{%
\begin{tikzpicture}[
  node distance=0.6cm and 0.3cm,
  >=Stealth,
  block/.style={draw, rounded corners, minimum height=0.7cm, minimum width=2.2cm,
    align=center, font=\scriptsize},
  data/.style={block, fill=blue!8},
  comp/.style={block, fill=green!8},
  model/.style={block, fill=orange!8},
  output/.style={block, fill=orange!12, font=\scriptsize\bfseries},
  arrow/.style={-{Stealth[length=2mm]}, thick},
  panellabel/.style={font=\small\bfseries, text=defblue},
]

% ── Panel A: Feature Stacking ──
\begin{scope}[xshift=0cm]
  \node[panellabel] at (1.5,5.2) {(A) Feature Stacking};
  \node[data] (a-seq) at (0,4) {E-mini L2\\Sequences};
  \node[model] (a-lstm) at (0,3) {LSTM};
  \node[comp] (a-emb) at (0,2) {Embedding\\($k$-dim)};
  \node[data] (a-tab) at (3,4) {Tabular\\Features (L0--7)};
  \node[comp] (a-concat) at (1.5,1) {Concatenate};
  \node[model] (a-lgbm) at (1.5,0) {LightGBM};
  \node[output] (a-out) at (1.5,-1) {Forecast};

  \draw[arrow] (a-seq) -- (a-lstm);
  \draw[arrow] (a-lstm) -- (a-emb);
  \draw[arrow] (a-emb) -- (a-concat);
  \draw[arrow] (a-tab) |- (a-concat);
  \draw[arrow] (a-concat) -- (a-lgbm);
  \draw[arrow] (a-lgbm) -- (a-out);
\end{scope}

% ── Panel B: Residual Stacking ──
\begin{scope}[xshift=7cm]
  \node[panellabel] at (1.5,5.2) {(B) Residual Stacking};
  \node[data] (b-tab) at (1.5,4) {Tabular\\Features};
  \node[model] (b-har) at (1.5,3) {HAR};
  \node[comp] (b-res1) at (1.5,2) {Residuals$_1$};
  \node[model] (b-lgbm) at (1.5,1) {LightGBM};
  \node[comp] (b-res2) at (1.5,0) {Residuals$_2$};
  \node[model, dashed] (b-lstm) at (1.5,-1) {LSTM (opt.)};
  \node[output] (b-out) at (1.5,-2) {$\sum$ Forecasts};

  \draw[arrow] (b-tab) -- (b-har);
  \draw[arrow] (b-har) -- (b-res1);
  \draw[arrow] (b-res1) -- (b-lgbm);
  \draw[arrow] (b-lgbm) -- (b-res2);
  \draw[arrow, dashed] (b-res2) -- (b-lstm);
  \draw[arrow] (b-lstm) -- (b-out);
  \draw[arrow, gray] (b-tab.east) -- ++(0.8,0) |- (b-lgbm.east);
  % E-mini sequences feed optional LSTM
  \node[data] (b-seq) at (-0.5,-1) {E-mini\\Sequences};
  \draw[arrow, dashed] (b-seq) -- (b-lstm);
\end{scope}

% ── Panel C: Prediction Blending (Ch.11) ──
\begin{scope}[xshift=13cm]
  \node[panellabel] at (1.5,5.2) {(C) Prediction Blending};
  \node[data] (c-tab) at (0,4) {Tabular\\Features};
  \node[data] (c-seq) at (3,4) {E-mini\\Sequences};
  \node[model] (c-lgbm) at (0,2.5) {LightGBM};
  \node[model] (c-lstm) at (3,2.5) {LSTM};
  \node[comp] (c-blend) at (1.5,1) {Weighted\\Average};
  \node[output] (c-out) at (1.5,0) {Forecast};

  \draw[arrow] (c-tab) -- (c-lgbm);
  \draw[arrow] (c-seq) -- (c-lstm);
  \draw[arrow] (c-lgbm) -- (c-blend);
  \draw[arrow] (c-lstm) -- (c-blend);
  \draw[arrow] (c-blend) -- (c-out);
  \node[font=\tiny, text=gray, anchor=north] at (1.5,-0.5) {(Ch.~\ref{ch:ensemble})};
\end{scope}

\end{tikzpicture}%
}
\caption{Three ensemble architectures.
(A)~LSTM embedding concatenated with tabular features for a single LightGBM.
(B)~Each model trains on residuals from the prior stage; final forecast is the sum.
(C)~Independent models blended at prediction level (Chapter~\ref{ch:ensemble}).}
\label{fig:architecture-comparison}
\end{figure}


%% ──────────────────────────────────────────────
\section{Feature Stacking}
\label{sec:feature-stacking}
%% ──────────────────────────────────────────────

The LSTM processes E-mini L2 5-min bars and LOB features (78 time steps per day) and produces a $k$-dimensional embedding vector (default $k=32$, or $k=1$ for a scalar forecast).
This embedding is concatenated with the ${\sim}$80--120 tabular features from Layers~0--7 to form a single expanded feature set.
LightGBM then trains on the combined input.

The approach has one fundamental problem: LightGBM cannot back-propagate gradients through the LSTM, so the embedding is never optimized for the tree's $\QLIKE$ objective.
The LSTM learns representations that minimize its own loss, which may not be what the tree needs.

\begin{table}[htbp]
\centering
\caption{Feature stacking: pros and cons.}
\label{tab:feature-stacking}
\small
\begin{tabular}{@{}lp{10cm}@{}}
\toprule
\textbf{Pros} & Single training pass; LSTM learns representations the tree can exploit \\
\midrule
\textbf{Cons} & Gradient isolation (tree cannot backprop into LSTM); embedding not optimized for tree objective; debugging harder; no RV literature demonstrates this beating alternatives \\
\bottomrule
\end{tabular}
\end{table}


%% ──────────────────────────────────────────────
\section{Residual Stacking}
\label{sec:residual-stacking}
%% ──────────────────────────────────────────────

Stage~1: HAR baseline (OLS) produces a forecast and residuals.
Stage~2: LightGBM trains on Stage~1 residuals with the full tabular feature set.
Stage~3 (optional): LSTM trains on Stage~2 residuals from E-mini sequences.
The final forecast is the sum of all stage forecasts.

Each model specializes by construction.
HAR captures the multi-scale autoregressive structure that dominates at all horizons.
LightGBM captures nonlinear patterns the HAR misses (regime interactions, jump-asymmetry effects).
The LSTM, if used, captures whatever sequential dynamics remain in the residuals.

\begin{table}[htbp]
\centering
\caption{Residual stacking: pros and cons.}
\label{tab:residual-stacking}
\small
\begin{tabular}{@{}lp{10cm}@{}}
\toprule
\textbf{Pros} & Each model has a distinct role; no gradient isolation; clean residual targets; aligns with HARQ-X direction; supported by recent RV literature \\
\midrule
\textbf{Cons} & Sequential training (each stage depends on prior); residual signal may be weak at later stages \\
\bottomrule
\end{tabular}
\end{table}


%% ──────────────────────────────────────────────
\section{Comparison}
\label{sec:architecture-comparison}
%% ──────────────────────────────────────────────

\begin{table}[htbp]
\centering
\caption{Three-way architecture comparison.}
\label{tab:architecture-comparison}
\small
\begin{tabular}{@{}lp{3.2cm}p{3.2cm}p{3.8cm}@{}}
\toprule
\textbf{Dimension} & \textbf{Feature Stacking} & \textbf{Residual Stacking} & \textbf{Pred.\ Blending (Ch.~\ref{ch:ensemble})} \\
\midrule
Complexity &
  High (joint training) &
  Moderate (sequential) &
  Low (independent) \\[6pt]
Gradient flow &
  Broken (tree cannot backprop into LSTM) &
  Clean (residual targets) &
  N/A (independent) \\[6pt]
Literature &
  Weak (no RV paper) &
  Strong (HARQ-X, recent lit.) &
  Strong \citep{Optiver2021, Bucci2020} \\[6pt]
Fallback &
  Must retrain tree without embedding &
  Drop Stage~3; keep HAR + LightGBM &
  Drop one model; keep the other \\[6pt]
Interpretability &
  Opaque (embedding) &
  Clear (stage contributions) &
  Clear (individual forecasts) \\
\bottomrule
\end{tabular}
\end{table}


%% ──────────────────────────────────────────────
%% Boxes
%% ──────────────────────────────────────────────

\begin{keyidea}[Residual Stacking Gives Each Model a Distinct Role]
HAR captures multi-scale $\RV$ persistence.
LightGBM captures nonlinear patterns the HAR misses.
LSTM (if used) captures whatever regime dynamics remain.
Each model trains on residuals from the prior stage, so roles are distinct by construction.
\end{keyidea}

\begin{warning}[No Evidence for Feature Stacking in RV Forecasting]
No paper in the RV literature demonstrates LSTM-embedding-to-GBDT feature stacking beating prediction blending or residual stacking at any forecast horizon.
The gradient isolation problem (Chapter~\ref{ch:ensemble}) compounds this: embeddings are never optimized for the tree objective.
\end{warning}
```

- [ ] **Step 2: Verify the file was created correctly**

Run: `wc -l guides/vol-project-ref/chapters/ch16-architecture.tex`
Expected: approximately 150--175 lines.

- [ ] **Step 3: Commit**

```bash
git add guides/vol-project-ref/chapters/ch16-architecture.tex
git commit -m "feat(vol-ref): add ch16 system architecture chapter"
```

---

### Task 4: Write ch17-development-plan.tex

**Files:**
- Create: `guides/vol-project-ref/chapters/ch17-development-plan.tex`

**Context:** This chapter gives the actual project build order (not the logical feature-layering order from ch14). It includes foundation fixes (not in ch14), reorders based on priority (trading signal first), identifies the critical path, and defines the minimum viable deliverable. It does NOT repeat evaluation methodology (ch13), success criteria numbers (ch01/ch13), or implementation step details (ch14).

- [ ] **Step 1: Write the complete chapter**

Create `guides/vol-project-ref/chapters/ch17-development-plan.tex` with exactly this content:

```latex
\chapter{The Development Plan}
\label{ch:development-plan}

Chapter~\ref{ch:complete-pipeline} gives the logical order for layering features and models.
This chapter gives the actual build order: what to implement first given project priorities and foundation work that must happen before anything else.
Priority ordering: trading signal $>$ academic rigor $>$ model novelty.


%% ──────────────────────────────────────────────
\section{Milestones}
\label{sec:milestones}
%% ──────────────────────────────────────────────

Table~\ref{tab:milestones} defines seven milestones with acceptance criteria and dependencies.

\begin{table}[htbp]
\centering
\caption{Development milestones. M1--M5 form the minimum viable deliverable.}
\label{tab:milestones}
\small
\begin{tabular}{@{}clp{4.8cm}p{4.2cm}l@{}}
\toprule
\textbf{M\#} & \textbf{Milestone} & \textbf{Acceptance Criteria} & \textbf{Key Tasks} & \textbf{Deps} \\
\midrule
1 & Fix Foundation &
  Purge gap $\geq h$ enforced; $\QLIKE$ sign matches \citet{Patton2011}; context kwarg added; all existing tests pass &
  CV fix, $\QLIKE$ fix, protocol extension, safe\_log dedup &
  --- \\[8pt]
2 & LightGBM &
  Custom $\QLIKE$ objective converges; Optuna finds improved params; walk-forward OOS predictions for 3 horizons &
  $\QLIKE$ gradient/hessian, model class, Optuna, walk-forward &
  M1 \\[8pt]
3 & Tournament &
  8 models $\times$ 3 horizons table with DM $p$-values on dev universe &
  Run baselines, DM test, tournament table &
  M2 \\[8pt]
4 & Layer~2 Options &
  Options features produce daily values with no look-ahead; $\QLIKE$ lift documented &
  OptionsLayer, IV surface wiring, validation &
  M1 \\[8pt]
5 & Signal &
  IV--RV gap signal; equity curve; positive OOS Sharpe &
  Signal logic, P\&L backtest, performance metrics &
  M3, M4 \\[8pt]
6 & Ensemble &
  Residual stacking and prediction blending tested; 10-model tournament table &
  Residual stacking, inverse-$\QLIKE$ blending &
  M3 \\[8pt]
7 & Stretch &
  Ordered by impact: regime $\QLIKE$, MCS, LSTM feature, full universe, figures, Rashomon &
  Each task independent &
  M3--M6 \\
\bottomrule
\end{tabular}
\end{table}


%% ──────────────────────────────────────────────
\section{Critical Path}
\label{sec:critical-path}
%% ──────────────────────────────────────────────

Figure~\ref{fig:critical-path} shows milestone dependencies.
The critical path (M1 $\to$ M2 $\to$ M3 $\to$ M6 $\to$ M7) is highlighted.
M4 branches from M1 and runs in parallel with M2--M3.
M5 and M6 can run in parallel after M3 completes.

\begin{figure}[htbp]
\centering
\begin{tikzpicture}[
  node distance=0.8cm and 1.6cm,
  >=Stealth,
  milestone/.style={draw, rounded corners, minimum height=0.9cm, minimum width=2.4cm,
    align=center, font=\small, fill=blue!8},
  critical/.style={milestone, line width=1.5pt, fill=orange!12},
  arrow/.style={-{Stealth[length=2.5mm]}, thick},
  critarrow/.style={arrow, line width=1.5pt, color=defblue},
]
  % Critical path
  \node[critical] (m1) {M1\\Foundation};
  \node[critical, right=of m1] (m2) {M2\\LightGBM};
  \node[critical, right=of m2] (m3) {M3\\Tournament};
  \node[critical, right=of m3] (m6) {M6\\Ensemble};
  \node[critical, right=of m6] (m7) {M7\\Stretch};

  \draw[critarrow] (m1) -- (m2);
  \draw[critarrow] (m2) -- (m3);
  \draw[critarrow] (m3) -- (m6);
  \draw[critarrow] (m6) -- (m7);

  % Parallel track
  \node[milestone, below=1.2cm of m2] (m4) {M4\\Options};
  \node[milestone, below=1.2cm of m6] (m5) {M5\\Signal};

  \draw[arrow] (m1) -- (m4);
  \draw[arrow] (m4) -| (m5);
  \draw[arrow] (m3) |- (m5);
\end{tikzpicture}
\caption{Milestone dependencies.
Bold path: critical path (M1--M2--M3--M6--M7).
M4 runs in parallel with M2--M3.
M5 requires both M3 (forecasts) and M4 (options features).}
\label{fig:critical-path}
\end{figure}


%% ──────────────────────────────────────────────
%% Boxes
%% ──────────────────────────────────────────────

\begin{keyidea}[M1--M5 Is the Minimum Viable Deliverable]
A $\QLIKE$ tournament (7~HAR variants + LightGBM, DM tests) plus a tradeable IV--RV signal with P\&L backtest is a presentable result.
Everything in M6--M7 is upside.
If time runs out after M5, the project has a defensible outcome.
\end{keyidea}

\begin{warning}[M1 Is Non-Negotiable]
The purge gap bug causes silent data leakage for $h=22$.
The $\QLIKE$ sign convention determines whether the loss function penalizes over-prediction or under-prediction correctly.
All results produced before M1 is complete are potentially invalid.
Do not skip ahead.
\end{warning}
```

- [ ] **Step 2: Verify the file was created correctly**

Run: `wc -l guides/vol-project-ref/chapters/ch17-development-plan.tex`
Expected: approximately 110--130 lines.

- [ ] **Step 3: Commit**

```bash
git add guides/vol-project-ref/chapters/ch17-development-plan.tex
git commit -m "feat(vol-ref): add ch17 development plan chapter"
```

---

## Chunk 3: development-plan.md + compilation

### Task 5: Write development-plan.md

**Files:**
- Create: `docs/project-plans/development-plan.md`

**Context:** This is the detailed task-level development plan for the ML vol forecasting project. It provides enough detail for each milestone to generate a session prompt. It is the document that Session 3 reads.

- [ ] **Step 1: Write the complete development plan**

Create `docs/project-plans/development-plan.md` with exactly this content:

```markdown
# ML Realized Volatility Forecasting: Development Plan

**Project:** GS ML Internship, ~20 weeks (May--Sep 2026)
**Priority ordering:** Trading signal > Academic rigor > Model novelty
**Dev universe:** SPY, AAPL, MSFT, NVDA, XOM, JPM, IWM, ES (8 symbols)
**Full universe:** 35 instruments (30 equities + 4 ETFs + 1 E-mini)

---

## M1: Fix Foundation

**Objective:** Eliminate correctness bugs that invalidate all downstream results. Unblock Layer 2--5 implementation.

**Prerequisites:** None.

### Tasks

#### 1.1 Fix CV purge gap enforcement

- **File:** `src/volforecast/utils/cv.py`
- **Change:** Add validation in each splitter that enforces `purge_gap = max(purge_gap, h)` per horizon. Applied dynamically inside the training loop, not as a global config.
- **Tests:**
  - `purge_gap=5, horizon=22` produces splits with gap >= 22
  - `purge_gap=30, horizon=5` keeps gap at 30 (does not shrink)
  - No train sample appears within h days of any test sample
  - All existing CV tests still pass
- **Done when:** Impossible to create a split where train data is within h days of test data.

#### 1.2 Verify and fix QLIKE log-space sign convention

- **File:** `src/volforecast/evaluation/metrics.py`
- **Change:** Derive correct log-space QLIKE from Patton (2011). Current code has `exp(y - y_hat) - (y - y_hat) - 1`. Correct Patton derivation: `exp(y_hat - y) - (y_hat - y) - 1`. Verify which the code implements, fix if wrong.
- **Key decision:** Must match Patton (2011) so results are comparable to literature.
- **Tests:**
  - QLIKE minimized when y_hat = y
  - Over-prediction penalized more heavily than under-prediction (Patton convention)
  - Synthetic data with known correct ranking
- **Done when:** QLIKE matches Patton (2011), documented in code comment.

#### 1.3 Add context kwarg to FeatureLayer protocol

- **File:** `src/volforecast/protocols.py`, all Layer 0--1 compute methods
- **Change:** Extend `FeatureLayer.compute(daily_data)` to `compute(daily_data, *, context=None)`. Update HARCoreLayer, AsymmetryLayer, NoiseRobustLayer to accept and ignore the kwarg.
- **Key decision:** Backward-compatible (context=None default). Layer 2+ will use context to receive IV surface, L2 depth, Treasury data.
- **Tests:**
  - All existing Layer 0--1 tests pass unchanged
  - Calling `.compute(data, context={"iv_surface": df})` works without error
  - Protocol check: layer with context still satisfies `isinstance(layer, FeatureLayer)`
- **Done when:** Layer 2 can be implemented using `context["iv_surface"]` without changing the protocol.

#### 1.4 Extract shared safe_log and consolidate zero-floor handling

- **File:** `src/volforecast/features/transforms.py` (safe_log already exists here)
- **Change:** Audit all feature modules for duplicated safe_log or ad-hoc `log(max(x, eps))` patterns. Replace with single `safe_log` import. Ensure consistent `min_value=1e-20`.
- **Tests:**
  - Grep for all `log(` and `np.log(` calls in features/; each should use safe_log or have explicit reason
  - `safe_log(0)` returns `log(1e-20)`, not `-inf`
  - All existing tests pass
- **Done when:** No duplicated log-safety patterns in features/.

**Fallback:** None. These are mandatory correctness fixes.
**Papers:** Patton (2011) for QLIKE.

---

## M2: LightGBM with Custom QLIKE Objective

**Objective:** First ML model. Produces genuine ML-vs-baseline comparison.

**Prerequisites:** M1.

### Tasks

#### 2.1 Implement custom QLIKE objective

- **File:** `src/volforecast/models/lightgbm.py`
- **What to build:** `QLIKEObjective` class with `.gradient(y_pred, y_true)` and `.hessian(y_pred, y_true)` methods returning arrays. Both operate in log-RV space.
- **Key decision:** Gradient = `exp(y_hat - y) - 1`, hessian = `exp(y_hat - y)`. Derived from Patton (2011) log-space QLIKE (as fixed in M1).
- **Tests:**
  - Numerical gradient check: analytical vs finite-difference (tol 1e-5)
  - Same for hessian
  - Objective is convex (hessian > 0 everywhere)
  - Train on synthetic data where true relationship is known; model converges
- **Done when:** LightGBM trains with custom QLIKE and converges.

#### 2.2 Implement LightGBMVolModel

- **File:** `src/volforecast/models/lightgbm.py`
- **What to build:** Model class satisfying `VolModel` protocol. Wraps `lgb.train()` with custom objective, early stopping, DART boosting. Config from ch09 Table 9.2 as defaults.
- **Key decision:** Register as `"lightgbm"` in MODEL_REGISTRY. DART boosting. Early stopping on validation QLIKE.
- **Tests:**
  - `.fit(X, y)` runs on 1000-row synthetic data
  - `.predict(X)` returns correct-length array
  - `.save()` / `.load()` round-trips
  - Predictions improve over training (QLIKE decreases)
  - Satisfies `isinstance(model, VolModel)`
- **Done when:** `vol run train --config lightgbm_config.yaml` completes.

#### 2.3 Wire Optuna hyperparameter tuning

- **File:** `src/volforecast/models/lightgbm.py` or new `models/tuning.py`
- **What to build:** Optuna study tuning learning_rate, num_leaves, min_data_in_leaf, n_estimators, reg_alpha, reg_lambda. SQLite storage at `workspace/experiments.db`.
- **Tests:**
  - 10-trial study completes on synthetic data
  - Best trial has lower QLIKE than defaults
  - SQLite DB contains trial records
- **Done when:** `vol run tune --config ...` finds improved hyperparameters.

#### 2.4 Implement walk-forward evaluation loop

- **File:** `src/volforecast/pipeline/runner.py` (extend existing)
- **What to build:** Rolling 5-year train window, step forward by test_size days, collect all OOS predictions. May already be partially implemented via expanding_window CV splitter.
- **Tests:**
  - Windows don't overlap illegally
  - Total OOS predictions cover expected date range
  - No look-ahead: max train date < min test date - purge_gap for each fold
- **Done when:** Walk-forward produces OOS predictions for all 3 horizons on dev universe.

#### 2.5 Select 8-symbol dev universe

- **File:** `src/volforecast/constants.py`
- **What to build:** `DEV_UNIVERSE = ["SPY", "AAPL", "MSFT", "NVDA", "XOM", "JPM", "IWM", "ES"]`
- **Key decision:** Use DEV_UNIVERSE for all iteration. Full 34-symbol universe only for final tournament.
- **Tests:** All 8 symbols have cached RV panels. Dev runs complete in <25% of full-universe time.
- **Done when:** Constant exists, baseline experiment runs on dev universe.

**Data sources:** Chunk Store L1 (confirmed), cached RV panels.
**Fallback:** If custom QLIKE objective is numerically unstable, fall back to MSE objective with QLIKE as eval metric only.
**Papers:** Patton (2011), Ke et al. (2017), Optiver 2021.

---

## M3: QLIKE Tournament

**Objective:** The most important deliverable. Definitive model comparison across all baselines and horizons.

**Prerequisites:** M2.

### Tasks

#### 3.1 Run full baseline tournament

- **What to build:** Script/CLI command that trains all 8 models (HAR, HARQ, SHAR, HAR-J, HAR-CJ, Ridge-HAR, Lasso-HAR, LightGBM) on dev universe across 3 horizons using walk-forward.
- **Key decision:** 8 models x 8 symbols x 3 horizons = 192 runs. Save all predictions.
- **Tests:**
  - All 192 runs complete
  - OOS predictions exist for every model/symbol/horizon
  - QLIKE scores finite and positive
- **Done when:** All predictions saved to workspace/models/.

#### 3.2 Implement Diebold-Mariano test

- **File:** `src/volforecast/evaluation/statistical_tests.py`
- **What to build:** `diebold_mariano_test(loss_1, loss_2, horizon)` returning test statistic and p-value. HAC standard errors (Newey-West) for h > 1.
- **Tests:**
  - Identical loss series returns p=1.0
  - loss_1 = loss_2 + large constant returns p~0
  - HAC correction differs from OLS for h=22
- **Done when:** `diebold_mariano_test()` passes all tests.

#### 3.3 Build tournament_table output

- **File:** `src/volforecast/evaluation/statistical_tests.py`
- **What to build:** `tournament_table(predictions_dict, y_true, baseline_key)` producing DataFrame with QLIKE scores, improvement bps vs baseline, and DM p-values.
- **Key decision:** Baseline = HARQ. Columns: QLIKE (h=1/5/22), bps improvement (h=1/5/22), DM p-value vs HARQ (h=1/5/22).
- **Tests:**
  - Table dimensions correct (8 models x 9 columns)
  - Baseline row shows 0 bps improvement
  - p-values between 0 and 1
- **Done when:** Tournament table prints cleanly for dev universe.

**Fallback:** If DM is slow, use simplified version without HAC for h=1.
**Papers:** Diebold & Mariano (1995), Patton (2011).

---

## M4: Layer 2 Options Features

**Objective:** Add the most impactful feature layer and unblock the tradeable signal.

**Prerequisites:** M1 (FeatureLayer context arg).

### Tasks

#### 4.1 Implement OptionsLayer.compute()

- **File:** `src/volforecast/features/options.py`
- **What to build:** Fill in stubbed `compute()`. Use `context["iv_surface"]` for Marquee data. Compute: atm_iv (1m, 3m), vrp, skew, term_slope, butterfly, iv_rv_gap. Single-stock: stock_atm_iv, stock_vrp via EDRVOL_PERCENT.
- **Key decision:** SPX features = market-wide regime signals. Single-stock IV confirmed working for all 34 symbols.
- **Tests:**
  - Features produce daily values for 1-year test period
  - VRP sign correct on average (IV > RV)
  - No NaN propagation from missing surface days
  - shift(1) applied to all features
- **Done when:** `OptionsLayer.compute(data, context={"iv_surface": df})` returns features.

#### 4.2 Wire IV surface fetching into pipeline

- **File:** `src/volforecast/pipeline/runner.py`
- **What to build:** Before calling feature layers, fetch IV surface via `marquee.fetch_iv_surface()` and single-stock IV via `marquee.fetch_atm_iv()`. Pass as context dict.
- **Key decision:** Fetch once per pipeline run.
- **Tests:**
  - Pipeline runs with `feature_layers: [har_core, asymmetry, options]`
  - Context dict contains expected DataFrames
- **Done when:** Full pipeline runs with Layer 2 active.

#### 4.3 Validate QLIKE improvement

- Run LightGBM with and without Layer 2 on dev universe. Compute QLIKE lift.
- **Key decision:** Expect 5--10% QLIKE improvement at h=5 and h=22 based on ch08 horizon priority table.
- **Done when:** QLIKE comparison documented.

**Data sources:** Marquee IV surface (confirmed), EDRVOL_PERCENT single-stock (confirmed for all 34 symbols).
**Fallback:** If single-stock IV has gaps, fall back to SPX-only IV as market-regime signal.
**Papers:** Christensen et al. (2023), Bollerslev et al. (2009).

---

## M5: Tradeable Signal

**Objective:** The priority deliverable. Prove the forecasts can make money.

**Prerequisites:** M3 (RV forecasts), M4 (options features for IV-RV gap).

### Tasks

#### 5.1 Implement IV-RV gap signal

- **File:** `src/volforecast/evaluation/economic_value.py`
- **What to build:** `iv_rv_gap_signal(iv_forecast, rv_forecast, threshold)` returning signal in {-1, 0, +1}. Long vol when RV forecast > IV (vol cheap). Short when IV > RV forecast (vol expensive).
- **Key decision:** Use ATM 1m IV. Threshold calibrated on training data (1 sigma of historical gap).
- **Tests:**
  - Signal direction matches expected
  - Signal is -1, 0, or +1 only
  - Random forecasts produce ~zero P&L
- **Done when:** Signal function produces daily signals for dev universe.

#### 5.2 Implement P&L backtesting

- **File:** `src/volforecast/evaluation/economic_value.py`
- **What to build:** `delta_hedged_straddle_pnl(signal, rv, iv, spot)` and `vol_targeting_pnl(returns, vol_forecast, target)`. Both return daily P&L series.
- **Key decision:** Straddle P&L primary. Vol-targeting secondary/simpler.
- **Tests:**
  - P&L zero when signal always neutral
  - Cumulative P&L monotonically increasing on synthetic correct-signal data
  - Transaction cost sensitivity: P&L positive under 1--2 bps costs
- **Done when:** P&L series computed for dev universe.

#### 5.3 Implement performance metrics and equity curve

- **File:** `src/volforecast/evaluation/economic_value.py`
- **What to build:** `compute_sharpe(returns)`, `compute_max_drawdown(cum_returns)`, equity curve matplotlib plot.
- **Tests:**
  - Sharpe of zero-mean returns is ~0
  - Max drawdown of monotonically increasing series is 0
  - Plot renders without error
- **Done when:** Sharpe > 0 OOS, equity curve saved.

**Fallback:** If straddle P&L weak, fall back to vol-targeting overlay. Negative result is still publishable.
**Papers:** Bollerslev et al. (2009), Corsi (2009), Moreira & Muir (2017).

---

## M6: Ensemble Experiments

**Objective:** Test whether combining models improves forecasts.

**Prerequisites:** M3 (tournament baseline). Does NOT depend on M5.

### Tasks

#### 6.1 Implement residual stacking

- **File:** `src/volforecast/models/ensemble.py`
- **What to build:** Script/class that: (a) loads HAR OOS predictions, (b) computes residuals, (c) trains LightGBM on residuals with full feature set, (d) sums forecasts.
- **Key decision:** Residual stacking is primary. Train models separately, blend post-hoc.
- **Tests:**
  - Stage 1 residuals have approximately zero mean
  - Stage 2 QLIKE on residuals is positive (model captures signal)
  - Combined forecast QLIKE <= best standalone QLIKE
- **Done when:** Residual stacking forecast exists for dev universe.

#### 6.2 Implement prediction blending

- **File:** `src/volforecast/models/ensemble.py`
- **What to build:** `InverseQLIKEEnsemble` weighting predictions inversely proportional to validation QLIKE. Fallback: equal-weight average.
- **Tests:**
  - Weights sum to 1
  - Lower QLIKE model gets higher weight
  - Blended QLIKE <= worst individual QLIKE
- **Done when:** Blended forecast exists for dev universe.

#### 6.3 Re-run tournament with ensemble entries

- Add residual stacking and prediction blending to tournament table.
- **Done when:** Tournament table has 10 rows (8 standalone + 2 ensemble), DM tests run.

**Fallback:** If neither ensemble beats standalone, document the finding.
**Papers:** Bucci (2020).

---

## M7: Stretch Goals

**Objective:** Polish and extend. Ordered by impact-per-effort.

### Tasks (each independent)

#### 7.1 Regime-conditional QLIKE

Split walk-forward evaluation by VIX regime (low/medium/high terciles). Show how model rankings change across regimes. **Deps:** M6.

#### 7.2 Model Confidence Set

Hansen et al. (2011) block bootstrap. Returns set of models not significantly worse than the best. **Deps:** M6.

#### 7.3 LSTM scalar forecast as LightGBM feature

Train LSTM on E-mini intraday sequences. Scalar point forecast as 1 extra LightGBM feature. Requires `SequenceModel` protocol. **Deps:** M2.

#### 7.4 Full 34-symbol tournament

Re-run M3 on full universe. Cross-sectional analysis of which stocks benefit most from ML. **Deps:** M3.

#### 7.5 Presentation figures

4--5 key plots: QLIKE table, forecast vs actual, P&L curve, feature importance bar chart. **Deps:** M5.

#### 7.6 Rashomon analysis

Interpretable trees on same feature set. Feature importance stability across near-optimal model set. **Deps:** M3.

---

## Architecture Decisions Log

| Decision | Choice | Rationale |
|---|---|---|
| Ensemble approach | Residual stacking (primary), prediction blending (fallback) | No RV paper supports feature stacking. Residual stacking gives each model a distinct role. |
| Dev universe | 8 symbols (SPY, AAPL, MSFT, NVDA, XOM, JPM, IWM, ES) | ~75% speedup. Full 34 for final tournament only. |
| Experiment tracking | SQLite `experiments.db` | Lightweight, Optuna native storage. |
| FeatureLayer protocol | Add `context` kwarg | Backward-compatible. Data-fetching stays in orchestrator. |
| LSTM scope | E-mini only, scalar forecast, stretch goal | Only 1 symbol has L2 depth. High effort, moderate gain. |
| QLIKE convention | Patton (2011) log-space derivation | Industry standard. |
| Pipeline architecture | Standalone blend stage | Train models independently, blend post-hoc. Maximum flexibility. |
| Priority ordering | Trading signal > academic rigor > model novelty | Desk cares about P&L first. |
```

- [ ] **Step 2: Verify the file was created correctly**

Run: `wc -l docs/project-plans/development-plan.md`
Expected: approximately 250--300 lines.

- [ ] **Step 3: Commit**

```bash
git add docs/project-plans/development-plan.md
git commit -m "feat: add detailed development plan for vol forecasting project"
```

---

### Task 6: Compile and verify

**Files:**
- All files created/modified in Tasks 1--5

- [ ] **Step 1: Compile the LaTeX guide**

Run from `guides/vol-project-ref/`:

```bash
cd guides/vol-project-ref && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex && cd ../..
```

Expected: Compilation succeeds with no errors (warnings about overfull hboxes or undefined references on first pass are acceptable and resolved by the triple-pass).

- [ ] **Step 2: Verify output**

Check that:
- The PDF includes Part V with chapters 15, 16, 17
- Table of contents lists all three new chapters
- Figure 15.1 (data lineage funnel) renders correctly
- Table 15.1 (feature matrix) spans correctly across pages
- Figure 16.1 (three-panel architecture) renders with all three panels
- Figure 17.1 (critical path diagram) renders with bold critical path
- All cross-references resolve (no "??" in the PDF)
- All citations resolve (no "[?]" in the PDF)

If compilation fails, check for:
- Missing `\_` in monospace text (underscore needs escaping in LaTeX)
- Unclosed environments
- Missing packages (all required packages are in `preamble.tex`)
- TikZ node positioning errors (adjust coordinates)

- [ ] **Step 3: Fix any compilation issues and re-compile**

If errors were found in Step 2, fix them in the relevant `.tex` file and re-run the compilation command.

- [ ] **Step 4: Final commit**

```bash
git add -A guides/vol-project-ref/
git commit -m "feat(vol-ref): complete Part V - The Build (ch15-17)"
```

---

## Subagent Diagram Review

After all chapters are written (Tasks 2--4) but before the final compilation commit, dispatch a subagent to independently review each TikZ diagram for:

1. **Correctness of data flow:** No arrows pointing the wrong way
2. **No overlap with existing diagrams:** ch11 Figure 11.1 (prediction blending only), ch14 Figure 14.1 (system-level pipeline)
3. **Visual consistency:** Same color scheme (blue=data, green=computation, orange=models), same node styles
4. **Completeness:** All nodes labeled, all connections shown, counts/annotations present
5. **LaTeX correctness:** TikZ syntax compiles without errors

The reviewer should read:
- `guides/vol-project-ref/chapters/ch15-pipeline.tex` (Figure 15.1)
- `guides/vol-project-ref/chapters/ch16-architecture.tex` (Figure 16.1)
- `guides/vol-project-ref/chapters/ch17-development-plan.tex` (Figure 17.1)
- `guides/vol-project-ref/chapters/ch11-ensemble.tex` (existing Figure 11.1, for overlap check)
- `guides/vol-project-ref/chapters/ch14-complete-pipeline.tex` (existing Figure 14.1, for overlap check)
