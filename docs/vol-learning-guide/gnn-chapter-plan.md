# Implementation Plan: Chapter "Graph Neural Networks for Volatility"

**Date:** 2026-07-06 · **Design:** `gnn-chapter-design.md` (committed 50fadd6) · **Executor:** write-chapter pipeline, autonomous run.
**Chapter file:** `guides/vol-learning-guide/chapters/16-graph-neural-networks.tex` · **Label:** `ch:gnn` · **Length target:** ~2,800–3,200 lines LaTeX (≈45–55 pp).

## Ground truth on disk (Pass 0 — already complete)

- Distill article full text: `<scratchpad>/gnn-intro.txt` (structure + prose for Arc 1).
- 17 project-paper extracts: `<scratchpad>/paper-extracts/<slug>.md` — slugs: gnnhar, ghar-covariance, chen-robert-icaif, spotv2net, dcrnn-har, gsp-har, gnhar-boetti, gnar-harx, harx-null, wade-portfolios, stid-deflation, bgnn, lstm-gnn-hybrid, choi-kim-embeddings, emgnn, kumar-regime-gnn, h-ete-gnn. Each: bibliographic + ready BibTeX, exact equations w/ page anchors, results w/ table anchors, caveats, teaching bullets, [UNCERTAIN] tags.
- 7 fundamentals extracts: `fund-gcn-kipf-welling.md`, `fund-gat-velickovic.md`, `fund-mpnn-gilmer.md`, `fund-graph-networks-battaglia.md`, `fund-graphsage-hamilton.md`, `fund-gin-xu.md`, `fund-oversmoothing-li.md`; PDFs saved under `reference/papers/`.
- Deep-research briefs: `notes/deep-research/2026-07-06-gnn-cross-asset-vol.md`, `notes/deep-research/spx-rv-gnn-regime-pipeline.md`.

**Rule:** every equation and number in the chapter comes from an extract (or is re-read from the PDF); anything tagged [UNCERTAIN] in an extract is re-verified against the PDF before use or omitted.

## Chapter Contract

**SECTIONS** (write in this order; per-section extract reads listed):

| § | Title | Primary sources to (re)read just before writing |
|---|---|---|
| 16.1 | The Market as a Graph | gnn-intro.txt; fund-graph-networks-battaglia |
| 16.2 | Three Prediction Tasks on Graphs | gnn-intro.txt |
| 16.3 | Representing Graphs for Neural Networks | gnn-intro.txt (incl. matrix-multiply appendix section) |
| 16.4 | Building a GNN: From Per-Node MLPs to Message Passing | gnn-intro.txt; fund-gcn-kipf-welling; fund-mpnn-gilmer; fund-graph-networks-battaglia; fund-graphsage-hamilton |
| 16.5 | Attention on Graphs | fund-gat-velickovic; chen-robert-icaif (bridge para); spotv2net (attention-interp para) |
| 16.6 | Design Lessons: Depth, Aggregation, Expressiveness, Tiny Graphs | gnn-intro.txt (playground lessons); fund-gin-xu; fund-oversmoothing-li; gnnhar (foreshadow) |
| 16.7 | GHAR and GNNHAR: The Canonical Volatility Result | gnnhar; ghar-covariance |
| 16.8 | Graph Construction: The Contested Design Choice | gnar-harx; emgnn; gnhar-boetti; wade-portfolios; briefs (leakage benchmark, Cartea abstract) |
| 16.9 | Dynamic, Spectral, and Intraday Frontiers | dcrnn-har; gsp-har; emgnn; spotv2net; chen-robert-icaif |
| 16.10 | Hybrids and the Regime Frontier | bgnn; choi-kim-embeddings; lstm-gnn-hybrid; kumar-regime-gnn; h-ete-gnn |
| 16.11 | The Skeptic's Checklist | stid-deflation; gnhar-boetti; harx-null; wade-portfolios |
| 16.12 | Project Blueprint: What to Actually Build | both briefs (resolving experiments + code maps); gnnhar |
| 16.13 | Summary | — |

**NOTATION:** per design §5. Adjacency $\mathbf{A}$ (reconcile with ch14's $W$ in one sentence in §16.7); layer weights $\bW^{(l)}$; embeddings $\bh_i^{(l)}$; features $\bX$; neighborhood $\mathcal{N}(i)$; attention $e_{ij}, \alpha_{ij}$ (matches ch12); aggregation $\bigoplus$; existing macros `\RV \QLIKE \HAR \E \R \bW \bh \bx \bX \softmax \relu \diag` — no new preamble macros; no inline redefinitions.

**LABELS:** `sec:gnn:*`, `eq:gnn:*`, `fig:gnn:*`, `tab:gnn:*`; chapter `ch:gnn`. Grep confirms no `:gnn:` labels exist anywhere in the guide.

**CITATIONS map (claim ← source):** per design §4; page anchors from the extracts; GNNHAR anchors use arXiv pagination (design §8 anchor policy). Abstract-only sources (CarteaCucuringuFang2026, GongEtAl2025 ASTGCN) contribute qualitative/design claims only, flagged in prose.

## Step-by-step execution

1. **Bib work first** (isolated, testable): append ~24 new entries to `guides/vol-learning-guide/references.bib` from the extracts' ready-to-paste blocks; apply the 3 corrections (ChenRobert2022 metadata, ZhangCucuringuDong2023 stub→IJF, ZhangPuCucuringuDong2024 DOI). Distinct keys for the two Chi–Gao–Wang papers (`ChiGaoWang2026DCRNN`, `ChiGaoWang2024GSP`). Kumar cited as `KumarUmeorahAlochukwu2024` (arXiv v1 in hand).
2. **main.tex insertion:** `\input{chapters/16-graph-neural-networks}` after ch15's input, inside Part 5.
3. **Pass 1 — write the chapter** section-by-section in contract order, saving incrementally (Write for §16.1, then Edit-append). Every equation follows the mandatory pattern (setup → equation → symbols → plain-English intuition box → projectconnection box). Two worked examples (one-hop by hand, §16.3; GAT weights by hand, §16.5). Booktabs tables: GNNHAR Table-1 ratio grid (§16.7); the QLIKE-audit table (§16.9); expected-gains table (§16.12).
4. **Cross-edits (3 one-liners):** ch12 graph-transformer subsection, ch14 graph-methods opener, ch15 spillover-features close — each gains a `\Cref{ch:gnn}` pointer.
5. **First compile** to pagination fixpoint (`pdflatex` ×2 + `bibtex` + loop per CLAUDE.md recipe); fix LaTeX errors; confirm chapter renders and TOC shows the new ch16.
6. **Pass 2 (chapter-verifier) ∥ Pass 3 (chapter-condenser)** — dispatch both sub-agents in one message, prompts per the write-chapter skill (verifier checks every `\citep/\citet` claim and formula against the PDFs in `reference/`; condenser hunts true redundancy only).
7. **Consolidation:** apply verifier CRITICALs (re-reading PDFs where needed) and condenser edits.
8. **Pass 4 (chapter-naive-reader)** — dispatch; apply ALL feedback (add missing intuition/translations/diagrams).
9. **Diagram verification** (deviation from per-diagram-at-write-time, noted: single batch after the prose has settled avoids double verification when passes 2–4 move content): recompile, then run the `verify-diagram` skill for each of the 12 figures (fig:gnn:market-graph, tasks, permutation, simplest-layer, message-passing, gat, oversmoothing, graph-menu, gnnhar-arch, leakage-timeline, hybrid-wiring, build-order), passing guide root, caption/label substring, concept, and relationships. Loop fixes until both gates pass; a `needs-human` result blocks completion and is surfaced.
10. **Final compile** to fixpoint; check `Output written on` page count; skim the chapter's rendered pages (crop a few) for gross layout breakage.
11. **Markdown mirror:** run `convert-chapter-markdown` for the new chapter into `guides/vol-learning-guide/markdown/`.
12. **Docs & memory:** update `reference/project-papers/README.md` (nothing moved — but note the 7 foundational PDFs now in `reference/papers/`), `notes/features/cross-asset.md` (chapter pointer), `notes/research-journal.md` + `logs/progress.md` (progress-log skill), memory `project-status.md`.
13. **Commits** (pathspec-scoped; never sweep the pre-existing staged renames): (a) bib + chapter + main.tex + cross-edits; (b) compiled PDF; (c) markdown mirror; (d) notes/logs/plan docs.

## Diagram specs (for verify-diagram: concept + relationships)

| Fig | Concept | Relationships to encode |
|---|---|---|
| market-graph | the project universe is a graph with node/edge/global attributes | assets=nodes grouped by class; edges=spillover channels w/ weights; global box=regime/VIX attached to all |
| tasks | three prediction granularities on one graph | node→per-asset RV; edge→spillover strength; graph→regime label |
| permutation | one graph, many adjacency matrices | two orderings of same 4-node graph → two different matrices; equality arrow between graphs |
| simplest-layer | GNN layer = per-attribute MLPs, connectivity untouched | V/E/U lanes in → separate MLPs → V'/E'/U' out; same wiring both sides |
| message-passing | gather→aggregate→update for one node | neighbor embeddings flow into ⊕, then update fn, then new embedding; edge+global lanes shown |
| gat | attention weights differentiate neighbors | center node; α-labelled arrows of differing thickness from 3 neighbors; softmax box |
| oversmoothing | depth homogenizes embeddings | layer-0/1/2/3 rows of node colors converging to uniform |
| graph-menu | six routes from data to adjacency | returns/RV panel → {corr, GLASSO, DY-FEVD, Granger/TE, sector, learned} → A → GNN |
| gnnhar-arch | GNNHAR pipeline | HAR lags per node → GLASSO graph → 1 nonlinear hop → per-node RV forecasts; HAR = identity-A special case annotation |
| leakage-timeline | point-in-time graph estimation | rolling 1000-day estimation window → graph frozen → forecast month → slide; forbidden arrow from future |
| hybrid-wiring | blend vs stack vs joint | three mini-pipelines side by side: forecast-into-ensemble; embeddings-into-GBM; BGNN loop trees↔GNN gradients |
| build-order | staged project roadmap with gates | HAR-WLS harness → linear graph ablation → GNNHAR1L-QLIKE → STID control → hybrid arms → regime fusion; go/no-go diamonds |

## Acceptance checklist

- [ ] Chapter compiles clean (no undefined refs/citations); TOC fixpoint reached.
- [ ] Every equation has the 5-part pattern; every term bolded on first use.
- [ ] Every Arc 2 number carries a page/table-anchored citation; abstract-only sources flagged in prose.
- [ ] All 12 figures pass verify-diagram gates.
- [ ] Pass 2 verifier: zero unresolved CRITICALs. Pass 4: all flags addressed.
- [ ] 3 cross-edit pointers in ch12/ch14/ch15 present; bib corrections applied; no label collisions (grep `:gnn:` count matches chapter).
- [ ] Markdown mirror exists; journal/progress/memory updated; commits pathspec-scoped.
