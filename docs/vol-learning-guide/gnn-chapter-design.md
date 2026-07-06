# Design: Chapter — "Graph Neural Networks for Volatility"

**Date:** 2026-07-06
**Status:** Design (autonomous run — user delegated approval; see goal directive of 2026-07-06)
**Target:** `guides/vol-learning-guide/chapters/16-graph-neural-networks.tex` (new), inserted at the end of Part 5 "Multivariate Volatility and Connectedness", after `15-spillovers-connectedness.tex`.
**Chapter label:** `\label{ch:gnn}`
**Source briefs:** `notes/deep-research/2026-07-06-gnn-cross-asset-vol.md` (25 verified sources) and `notes/deep-research/spx-rv-gnn-regime-pipeline.md` (15 verified sources); per-paper extractions in scratchpad `paper-extracts/` (17 project papers + 7 foundational papers, page-anchored).
**Pedagogical backbone (first half):** Sanchez-Lengeling, Reif, Pearce & Wiltschko (2021), "A Gentle Introduction to Graph Neural Networks", *Distill*, DOI 10.23915/distill.00033 — full text extracted to scratchpad. The user explicitly asked that the chapter's opening arc follow this article's teaching sequence.

---

## 1. Goal

Teach GNNs **from zero to the research frontier for volatility forecasting** in one chapter: what a graph is, how neural networks learn on graphs (message passing, GCN, GAT), what design choices matter (depth, aggregation, over-smoothing), and then — the second arc — everything the 2022–2026 literature knows about GNNs for realized-volatility forecasting: the canonical GHAR/GNNHAR result, the contested graph-construction question, dynamic/spectral/intraday variants, GNN–GBM hybrids, the regime×graph frontier, and the deflationary evidence a skeptic must weigh. It ends with a concrete build order for the reader's ML vol estimator project.

The chapter is the deep treatment that three earlier passages promised: ch12's "Graph Transformers for Cross-Asset Volatility" subsection, ch14's two-page "Graph-Based Methods" survey, and ch15's "Spillover Indices as Predictive Features" close. Each of those gets a one-line forward pointer to `\Cref{ch:gnn}`.

## 2. Why this placement (decision + alternatives weighed)

**Chosen: end of Part 5, after ch15.** Every dependency is then *behind* the reader:
- neural-net mechanics, attention/transformers → ch12 (`\Cref{sec:dl:transformers}` teaches QKV attention; GAT becomes a 2-page step, not a 10-page one),
- ensembles/blending → ch13 (the hybrid verdicts reference `\Cref{sec:hybrid:architectures}`),
- realized covariance, HAR-DRD → ch14 (GHAR-covariance extension builds on `\Cref{sec:multivariate:drd}`),
- Diebold–Yilmaz GFEVD spillover matrices → ch15 (`\Cref{sec:dy-spillover}`) — which is precisely the DCRNN-HAR adjacency input.

The chapter is also the natural *synthesis* of Parts 4 and 5: ch15 measures the network; this chapter learns on it. The user's placement instruction ("after the deep learning chapters") is satisfied — the chapter sits after all of them — and the alternative placements lose:
- **Between ch12 and ch13** (rejected): forces forward references to ch14 (covariance) and ch15 (DY adjacency), the two tools the vol arc leans on hardest. Forward references are poison in a linear teaching text.
- **Splitting into two chapters** — fundamentals in Part 4, applications in Part 5 (rejected): the user asked for one chapter; and the fundamentals-only half would dangle without its payoff.

Existing chapters 16–19 renumber to 17–20 automatically (all cross-refs are `\Cref`-based; no file renames).

## 3. Teaching philosophy (load-bearing)

- **Two arcs, one spine.** Arc 1 (§16.1–§16.6) is the distill.pub curriculum, re-told with market examples: the reader should *never* wonder why they are learning graph representation — every fundamental lands with a `projectconnection` box mapping it to the vol problem (nodes = assets, node features = HAR lags, edges = spillover channels, node-level regression = per-asset RV forecasting). Arc 2 (§16.7–§16.12) is the literature: every claim page-anchored, every missing QLIKE flagged.
- **Distill fidelity where it teaches, adaptation where it doesn't.** Keep distill's sequence (graphs → tasks → representation problem → simplest GNN → pooling → message passing → edge/global → attention → design lessons) and its best explanatory moves (images/text as graphs; "matrix multiply = one hop"; adjacency-permutation problem; the "more attributes communicating = better" lesson). Replace its interactive widgets with TikZ + worked numeric examples; replace molecule/Karate-club running examples with a cross-asset market graph (molecules and Othello stay as one-paragraph cameos — they are genuinely good intuition builders). Cite the article properly and prominently.
- **The equation pattern is mandatory** (write-chapter skill): setup sentence → equation → itemized symbols → `intuition` "In Plain English" box → `projectconnection` box. Applies to GCN/GAT/MPNN fundamentals as much as GNNHAR.
- **Evidence discipline is a theme, not a footnote.** The volatility-GNN literature's signature failure is MSE-only wins that die under QLIKE. The chapter teaches that as content: a recurring "does it survive QLIKE?" audit column, a Skeptic's Checklist section, and honest deflations (STID, GNAR-HARX, HARX-null). This mirrors the repo's research verdicts — the chapter must not oversell graphs.
- **One voice with the guide:** terms bolded on first use, `booktabs` tables, no vertical rules, intuition before algebra, worked examples only where they unlock theory (one-hop message passing by hand; GAT attention weights by hand).

## 4. Section-by-section design

### §16.1 The Market as a Graph *(Arc 1 opener)*
- **Open with a concrete question** (guide rule): "On 2026-04-03 crude oil crashed 8% and bank CDS spreads jumped; SPX itself barely moved. Your HAR model, which sees only SPX's own history, forecasts a quiet week. Should you believe it?" → volatility travels along economic linkages; the data structure that captures "entities + linkages" is a graph.
- **Teach:** graph = nodes + edges (+ global context); node/edge/global attributes; directed vs undirected edges (spillovers have direction — recall ch15's TO/FROM asymmetry); the market graph for the project's ~34-symbol cross-asset universe.
- **Distill cameos:** images-as-graphs (pixels, 8-neighbors) and text-as-graphs (token chain) — kept because they make one deep point: *CNNs and RNNs (ch12) are GNNs on rigid graphs; a Transformer is a GNN on a fully-connected token graph.* This single framing connects everything the reader already knows to everything in this chapter.
- **Boxes/figs:** `prereq` (chapter opener: ch12 NN + attention, ch14 covariance, ch15 DY, ch6 HAR); `intuition` (graph as "who can infect whom" — epidemiology of volatility); **Fig A `fig:gnn:market-graph`** — the project universe as an annotated graph (equity indices, rates, FX, commodities, credit; node attributes = RV lags/IV; edge attributes = spillover strength; global attribute = market regime/VIX).
- **Citations:** Sanchez-Lengeling et al. 2021 (structure + examples); Battaglia et al. 2018 (nodes/edges/global taxonomy).

### §16.2 Three Prediction Tasks on Graphs
- **Teach:** graph-level / node-level / edge-level tasks (distill's taxonomy) with immediate finance translation: **node-level regression = per-asset RV forecasting (our task)**; edge-level = predicting spillover strength / lead-lag links; graph-level = market-wide regime or aggregate-vol prediction. Distill's examples (molecule odor, Karate club, image scene graphs) compressed to one paragraph each.
- **Boxes/figs:** **Fig B `fig:gnn:tasks`** — one market graph, three prediction targets highlighted (a node, an edge, the whole graph); `projectconnection` (the estimator is node-level regression; but the regime detector is graph-level — the two project components live at two task levels).

### §16.3 Representing Graphs for Neural Networks
- **Teach (distill sequence, kept intact):** the four information types (nodes, edges, global, connectivity); why adjacency matrices are awkward inputs — $O(N^2)$ sparsity waste and, fatally, **permutation non-invariance** (many adjacency matrices encode one graph; an MLP on a flattened adjacency matrix learns node *order*); adjacency lists as the sparse fix.
- **Then the payoff distill buries in an appendix, promoted here because the vol arc needs it:** matrix multiplication **is** message passing — $\mathbf{B} = \mathbf{A}\bX$ gathers each node's neighbor features with sum aggregation; $\mathbf{A}^k$ counts $k$-step walks, so stacking hops = widening the information horizon. This is the bridge to GHAR (§16.7), which is *literally* $\gamma\,\mathbf{A}\,\mathrm{RV}_t$ — and to over-smoothing (§16.6).
- **Boxes/figs:** **Fig C `fig:gnn:permutation`** — same 4-node graph, two node orderings, two different adjacency matrices; `workedexample` — 3-asset one-hop by hand: $\mathbf{A}\bX$ with SPX/oil/banks numbers showing the oil shock arriving in SPX's aggregated features; `warning` (permutation invariance is not a nicety — a model that isn't invariant memorizes ticker order).
- **Citations:** Sanchez-Lengeling et al. 2021.

### §16.4 Building a GNN: From Per-Node MLPs to Message Passing
- **Teach (distill's build-up, the chapter's pedagogical core):**
  1. **Simplest GNN**: separate MLPs on node/edge/global attributes; connectivity unused inside layers — establishes "GNN layer = graph-in, graph-out, embeddings updated, connectivity untouched."
  2. **Pooling** ($\rho$): routing information between attribute types for prediction (edges→nodes etc.).
  3. **Message passing**: gather → aggregate (sum/mean/max) → update (learned NN); after $k$ layers a node has seen its $k$-hop neighborhood.
  4. **The GCN layer** (Kipf–Welling 2017): $\bh^{(l+1)} = \sigma(\tilde{\mathbf{D}}^{-1/2}\tilde{\mathbf{A}}\tilde{\mathbf{D}}^{-1/2}\bh^{(l)}\bW^{(l)})$ with the renormalization trick — taught as "the §16.3 matrix multiply + self-loops + degree normalization + learned weights + nonlinearity."
  5. **Edge features and global (master) node** — Graph Nets block (Battaglia et al. 2018): edge update → node update → global update; the global node as the "VIX of the graph."
  6. **MPNN umbrella** (Gilmer et al. 2017): message function $M_t$, update function $U_t$, readout $R$ — every architecture in this chapter is a choice of $(M, U, R)$.
- **Boxes/figs:** **Fig D `fig:gnn:simplest-layer`** (per-attribute MLPs); **Fig E `fig:gnn:message-passing`** (gather/aggregate/update with edge+node+global lanes — deeper than ch14's `fig:gnn-message`, which stays as the preview); `definition` boxes for GCN and MPNN equations with full symbol lists; `intuition` ("a GCN layer is a rumor mill: every asset averages its neighbors' stories, then rewrites its own"); `projectconnection` (one GCN layer on the DJIA graph = one spillover hop = GNNHAR's design).
- **Citations:** Kipf & Welling 2017 (eq. 2, plus one paragraph on the Chebyshev lineage); Gilmer et al. 2017 (eqs. 1–3); Battaglia et al. 2018 (block algorithm); Hamilton et al. 2017 (GraphSAGE aggregators — one subsection paragraph: sampling matters at web scale, *not* for 30-asset graphs); Sanchez-Lengeling et al. 2021.

### §16.5 Attention on Graphs
- **Teach:** GAT (Veličković et al. 2018): score $e_{ij} = \mathrm{LeakyReLU}(\mathbf{a}^\top[\bW\bh_i \,\Vert\, \bW\bh_j])$, softmax-normalized $\alpha_{ij}$, multi-head concat/average — presented as "ch12's attention (Eq. \ref{eq:attention}) masked to the graph neighborhood." Then the two-way bridge: a Transformer is a GAT on a fully-connected graph; a GAT is a Transformer whose attention is masked by $\mathbf{A}$. Attention weights as *learned, state-dependent spillover measures* — the interpretability hook (ASTGCN's tranquil-vs-turmoil attention shifts, cited qualitatively only — numbers are paywalled; SpotV2Net's attention usage from the extract).
- **Boxes/figs:** **Fig F `fig:gnn:gat`** — attention computation over one node's neighborhood, arrow thickness = $\alpha_{ij}$ (echoes ch12's FOMC attention figure deliberately); `workedexample` — 3-neighbor attention weights by hand; `warning` (attention weights are not causal spillovers; they are trained weights that co-move with regimes — cite the ASTGCN abstract-only status honestly).
- **Citations:** Veličković et al. 2018 (eqs. 1–6); ChenRobert2022 (existing bib key) for graph-transformer-for-vol; ASTGCN (J. Emp. Finance 2025, qualitative); Sanchez-Lengeling et al. 2021.

### §16.6 Design Lessons: Depth, Aggregation, Expressiveness — and Tiny Graphs
- **Teach:**
  1. Distill's playground lessons (message-passing breadth beats parameter count; more attribute types communicating → better mean performance; best models are often *shallow*).
  2. **Aggregation choice**: sum/mean/max trade-offs; GIN's result (Xu et al. 2019) — sum is maximally expressive (WL-test bound), mean/max lose multiset information; stated as a `keyidea` with the theorem cited, no proof.
  3. **Over-smoothing** (Li, Han & Wu 2018): repeated graph convolution = Laplacian smoothing; embeddings within a connected component converge; deep GNNs erase the differences they were built to exploit. Foreshadow: GNNHAR finds exactly this — 3 layers degrade, and the DJIA GLASSO graph has diameter 3.
  4. **The tiny-graph corollary (original synthesis, clearly framed as such):** vol graphs have 10–500 nodes and small diameters; web-scale GNN engineering (sampling, batching, Cluster-GCN) is irrelevant; over-smoothing arrives at 2–3 layers; parameter budgets must be small because $N \times T$ is tiny by deep-learning standards (echoes ch12's transformer warning).
- **Boxes/figs:** **Fig G `fig:gnn:oversmoothing`** — node embeddings converging as layers stack (colors blending across 1/2/3 layers); `keyidea` (sum > mean > max expressiveness); `warning` (your graph is tiny: most GNN blog advice assumes millions of nodes and does not transfer).
- **What we deliberately skip** (one honest paragraph): graph generative models, hypergraphs/multigraphs, graph duals, web-scale sampling — pointers to distill's "Into the Weeds" for the curious.
- **Citations:** Xu et al. 2019 (Theorem 3, Fig. 3 ranking); Li, Han & Wu 2018 (Theorem 1); Sanchez-Lengeling et al. 2021; Zhang et al. 2025 (foreshadow).

### §16.7 GHAR and GNNHAR: The Canonical Volatility Result *(Arc 2 opener)*
- **Bridge sentence:** ch15 ended by hand-crafting spillover features; the graph alternative is to *learn on the network directly*. Then the honest headline up front: the best rigorously-evaluated GNN gain over HAR is ~4% QLIKE at h=1, ~9% at h=5, gone by h=22 — worth having, not a revolution.
- **Teach (from the GNNHAR extract, all page-anchored):**
  1. **GHAR** — HAR + one linear graph-aggregation term per HAR lag (exact spec from the paper, correcting ch14's single-γ sketch); estimable by OLS; already captures roughly half the total gain.
  2. **GNNHAR** — replace linear aggregation with a one-/two-layer nonlinear message-passing hop; exact architecture (dims, activation) from the extract.
  3. **GLASSO graph construction** + rolling 1000-day window, monthly re-estimation (the clean point-in-time template).
  4. **The loss-function lever**: QLIKE-trained vs MSE-trained twins — QLIKE training wins at h≤5 on both metrics, but at h=22 costs 30–50% MSE (Table 1 grid reproduced as a booktabs table); turbulence split (Table 2 Panel B).
  5. **One hop is enough**: 2L vs 1L DM-significant for 1/27 stocks; 3L degrades (over-smoothing diagnosed — the §16.6 theory made empirical); graph diameter 3.
  6. **Covariance extension** (GHAR JFEC): −1.8% QLIKE vs HAR-DRD with MCS p = 1.000 on realized covariances — the cleanest graph win in the literature, on the *covariance* problem (cross-ref ch14 HAR-DRD; repo verdict: graphs help covariance more than univariate RV).
- **Boxes/figs:** **Fig H `fig:gnn:gnnhar-arch`** — data flow: HAR lags per node → GLASSO graph → 1 message-passing hop → per-node $\widehat{\RV}$; `keyresult` (the Table 1 ratio grid); `warning` (QLIKE training's h=22 MSE penalty — "always train with QLIKE" is scoped, not universal); `projectconnection` (GNNHAR's repo is the harness to port; HAR is the identity-adjacency special case).
- **Citations:** ZhangCucuringuDong2023 (existing key; IJF 41(1):377–397), ZhangPuCucuringuDong2024 (existing key; JFEC nbae026).

### §16.8 Graph Construction: The Contested Design Choice
- **Frame:** the frontier's real fight is not architecture, it's the adjacency matrix. Teach the menu, then the contradiction, then the leakage rules.
- **The menu (each: 1 definition + how estimated + 1-sentence verdict):** thresholded correlation; **GLASSO** partial-correlation (conditional-independence intuition box); **DY-FEVD spillover matrix** (recall ch15 — transposed GFEVD as adjacency, DCRNN-HAR's input); Granger/effective-transfer-entropy directed graphs (Boetti–Nunes GNHAR; H-ETE-GNN); sector/fundamental graphs and macro augmentation (Wade); **fully-connected** (let the network learn weights); **learned/evolving adjacency** (EMGNN); **factor-residual (idiosyncratic) networks** (Cartea–Cucuringu–Fang, abstract-only — flagged as such, design idea adopted, numbers not).
- **The contradiction, presented as live science:** GNNHAR: GLASSO beats identity (27 DJIA stocks). GNAR-HARX: fully-connected beats GLASSO on QLIKE *and* MSE (10 indices), GLASSO edge-instability diagnosed. EMGNN: learned-evolving beats learned-static (crypto). Plausible reconciliation: sparsification pays on larger single-class universes, not on 10 highly-correlated indices. **This is unresolved — and cheap to resolve on the project's own data** (the §16.12 ablation).
- **Leakage rules:** estimate graphs on training windows only (GNNHAR's rolling protocol as the clean template); the one-switch leakage benchmark's finding that full-sample graph estimation is a *second-order* sin (Sharpe inflation ~0.0–0.4) versus temporal/execution leaks (4–26) — prioritize hygiene accordingly, but still never look ahead.
- **Boxes/figs:** **Fig I `fig:gnn:graph-menu`** — flowchart from data → six construction routes → adjacency → GNN; **Fig J `fig:gnn:leakage-timeline`** — rolling graph-estimation timeline (estimation window, forecast date, re-estimation cadence); `keyidea` (GLASSO in plain English: an edge survives only if correlation remains after controlling for every other asset); `warning` (graph look-ahead: small inflation, still forbidden — and *centered features* are the real killer, cross-ref ch16-evaluation... now ch17).
- **Citations:** onuallain-2025 (Table 4 p.22, §5.5), zhang-et-al-2026 leakage benchmark (Table 1), EMGNN (Table 5), boetti-nunes-2026, wade-2026, Cartea SSRN abstract, GNNHAR.

### §16.9 Dynamic, Spectral, and Intraday Frontiers
- **Teach (compressed survey, one subsection each, every missing-QLIKE flagged in a running audit table):**
  1. **DCRNN-HAR** — dynamic DY adjacency via trading-day masks ($\tilde{\mathbf{A}}_t = \mathbf{E}^A_t \odot \mathbf{A}$); diffusion-convolution recurrence; best-in-48/48 scenarios on MSE/MAE + 75%-MCS, **no QLIKE, no DM**; vs nearest rival only ~4–11%.
  2. **GSP-HAR** — spectral lens: magnetic Laplacian on the directed DY matrix, graph Fourier transform, filtering in frequency space; the lightweight alternative to full ST-GNNs; MSE/MAE only.
  3. **EMGNN** — learned evolving multiscale adjacency (crypto); rel. MSFE 0.6527 vs MTGNN 0.7809, MCS p=1.000; not a clean static-vs-dynamic ablation.
  4. **SpotV2Net** (Brini & Toscano) — intraday spot vol via GAT over a fully-connected 30-node DJIA graph; node features = Fourier-estimated spot vol/co-vol, edge features = vol-of-vol/co-vol-of-vol; beats panel ARFIMA/XGBoost/LSTM on 30-minute-ahead spot vol (test MSE 4.885e-08 vs 5.487e-08) — but single split, no DM/MCS, training loss unstated. The project-relevant intraday exemplar *and* a mini-case of evidence hygiene.
  5. **GTN-VF (Chen & Robert 2022)** — the graph-transformer entry ch12 previewed: each (stock, time) pair is a graph node; data-driven similarity + sector + supply-chain edges; UniMP-style graph transformer on 1-second LOB features of 494 S&P 500 stocks; beats HAR/LightGBM/TabNet under RMSPE, *but only when relational edges are included*; no QLIKE/DM/MCS, and the paper never pins whether feature-correlation edges avoid look-ahead — teach both the architecture and the two caveats.
- **The horizon conflict, stated openly:** GNNHAR's gains fade by h=22; DCRNN-HAR's MSE gains *grow* with horizon. Different universes, targets, metric discipline — unresolved; QLIKE re-scoring is the arbiter (feeds §16.12).
- **Boxes:** `keyresult` (running audit table: model × loss × DM × MCS × verdict — the "does it survive QLIKE?" column mostly reads *unknown*); `warning` (MSE-only wins in this exact literature have repeatedly failed to transfer to QLIKE).
- **Citations:** chi-gao-wang DCRNN-HAR (J. Forecasting 2026) + GSP-HAR, zhou-et-al EMGNN, SpotV2Net, ChenRobert2022.

### §16.10 Hybrids and the Regime Frontier
- **Teach:**
  1. **Three wirings** for GNN+GBM/LSTM: (a) *prediction blending* (GNN forecast as one more column/ensemble member — cross-ref ch13); (b) *embedding stacking* (final-layer node embeddings → LightGBM features — Choi–Kim as the negative exemplar: 1024-d→UMAP-32→XGBoost, significant-but-tiny gains, **no leakage protocol documented**); (c) *joint training* (BGNN: trees fitted to GNN gradient updates, end-to-end beats two-stage by 4–14% RMSE — non-finance, and the reverse direction: GBDT feeds GNN).
  2. **The repo verdict, taught as a verdict:** no finance paper shows embedding-stacking beating simple prediction blending; blending stays the default until arm-B evidence exists (the §16.12 experiment).
  3. **LSTM‖GNN fusion wiring** (Sonani et al.): parallel branches → concatenate → dense head; −10.6% MSE vs LSTM on *price* (not vol), no HAR baseline — wiring worth knowing, evidence worth discounting.
  4. **Regime×GNN — the open frontier:** the entire published intersection is one impostor (Kumar et al. 2026: "regime-dependent" with no regime mechanism — piecewise-static train/val/test graphs, squared-return proxy) and one honest failure (H-ETE-GNN: Hurst-triggered graph swaps, causally clean, *loses to naive periodic retraining in both 2008 and 2020*). Regime-conditioning the *graph* is the lowest-priority component; regime-feature-into-HAR (cross-ref ch13's regime section) ranks first. The fusion layer has no credible incumbent — which makes it the project's novelty opportunity, to be attempted only after the boring layers work.
- **Boxes/figs:** **Fig K `fig:gnn:hybrid-wiring`** — three wiring diagrams side by side (blend / stack / joint); `keyidea` (why joint training helps: the GBM sees where the GNN's gradients point, not just its output); `warning` (Choi–Kim's missing leakage protocol as a checklist of what *must* be pinned before trusting an embedding pipeline).
- **Citations:** ivanov-prokhorenkova BGNN (ICLR 2021, Table 2 §4.1.2), choi-kim-2024 (Table 8), sonani-2025 (§3.5, §4.5), kumar-2026 (Table 3), cho-lee-2025 H-ETE-GNN (corrected Tables 6–11), fang-slepaczuk-2026 (one-line cross-ref for regime-feature ranking).

### §16.11 The Skeptic's Checklist
- **Teach — the five deflations, each 2–4 paragraphs:**
  1. **STID**: per-node identity embeddings + MLP match/beat STGNNs on standard benchmarks — "what graphs buy can often be bought with node IDs"; run it as a control before believing any GNN gain.
  2. **Linear networks match GNNs**: GHAR captures ~half of GNNHAR's gain; GNAR/GNHAR (Boetti–Nunes: −38% MAFE with a *linear* directed-graph model) — nonlinearity is the smaller lever; the graph is the bigger one.
  3. **Cross-asset terms can be worthless**: the HARX-ElasticNet null (RMSE identical to 4 decimals, 7/90 nonzero cross-coefficients) — with the smoothed-vol-target caveat that may manufacture the null.
  4. **Accuracy ≠ economic value**: Wade — best-MSE, best-RankIC, best-Sharpe are three different models; graph structure bought Sharpe (0.984 vs 0.635) while barely moving MSE; no QLIKE/DM/MCS, survivorship caveat.
  5. **The QLIKE survival question**: almost every headline ST-GNN number in this chapter is MSE/MAE; the one lineage with full discipline (GNNHAR) shows single-digit QLIKE gains. Default prior for any new paper: halve the headline, then ask for DM.
- **Boxes:** `keyidea` (the checklist itself, enumerated — usable as a referee report template); `projectconnection` (these five checks are the project's model-review gate).
- **Citations:** shao-et-al STID (Tables 2–3), boetti-nunes (Table 2 p.14), mallory (Table 3 p.17), wade (Tables 3/5), GNNHAR.

### §16.12 Project Blueprint: What to Actually Build
- **Teach — the evidence-ranked build order (synthesizes both deep-research briefs' resolving experiments):**
  0. Harness first: rolling HAR-WLS fair-fight baseline (JLDC spec), QLIKE + DM + MCS, purged CV (cross-ref ch on evaluation).
  1. **The graph ablation (cheapest, highest information):** GHAR-style *linear* aggregation on the project universe with identity vs fully-connected vs GLASSO vs rolling-DY adjacency, h ∈ {1,5,22} — all OLS-estimable; resolves §16.8's contested question on our data before any GNN is trained.
  2. **GNNHAR1L with QLIKE loss** (only if step 1's best graph beats identity with DM significance): one hop, small dims, monthly graph re-estimation.
  3. **STID control** in the same harness (node-ID embeddings + MLP) — if it matches the GNN, the graph isn't earning its complexity.
  4. **Hybrid arm test:** LightGBM(HAR features + GNN scalar forecast) vs LightGBM(+ 8/16/32-d node embeddings), purged k-fold with embargo — the blending-vs-stacking question, settled locally.
  5. **Regime fusion (novelty tier, last):** filtered regime probability as node/global feature vs regime-blended graphs — the published field is empty; expectations calibrated by H-ETE-GNN's failure.
- **Plus:** code map (chaozhang-ox/GNNHAR — QLIKE loss + MCS built in; MikeZChi/DCRNN-HAR + GSPHAR; nd7141/bgnn; jump-models — all on the GS machine); data realities (34 symbols, asynchronous closes across asset classes → refresh-time caveat, cross-ref ch14); expected effect sizes (single-digit QLIKE percent, concentrated at h≤5).
- **Boxes/figs:** **Fig L `fig:gnn:build-order`** — the five-step roadmap as a staged pipeline with go/no-go gates; `keyresult` (honest expected-gain table: what each step can win, per the literature); `warning` (asynchronicity across asset classes is *our* universe's extra problem — none of the papers face a 34-symbol multi-class book).

### §16.13 Summary
- Bullet recap: one per section, each pairing the concept with its number (e.g., "one nonlinear hop, trained under QLIKE: −4% QLIKE at h=1 — the honest ceiling").

## 5. Notation contract (chapter-level)

| Quantity | Symbol | Notes |
|---|---|---|
| Graph, nodes, edges | $G=(V,E)$, $N$ assets | define once in §16.1 |
| Adjacency matrix | $\mathbf{A}$ | ch14 used $W$ for its sketch — one reconciling sentence in §16.7; $W$ is reserved for learned weights here |
| Normalized adjacency w/ self-loops | $\tilde{\mathbf{A}}$, $\tilde{\mathbf{D}}$ | GCN renormalization |
| Node feature matrix / embedding | $\bX \in \R^{N\times d}$, $\bh_i^{(l)}$ | preamble macros `\bX`, `\bh` |
| Layer weights | $\bW^{(l)}$ | preamble `\bW` |
| Neighborhood | $\mathcal{N}(i)$ | inline `\mathcal{N}` |
| Attention coefficients | $e_{ij}$, $\alpha_{ij}$ | matches ch12 attention notation |
| Aggregation / pooling | $\bigoplus$, $\rho$ | $\bigoplus$ for generic aggregate |
| RV, QLIKE, HAR | `\RV`, `\QLIKE`, `\HAR` | existing preamble macros — never redefine |

No new preamble macros required.

## 6. Labels

Prefix scheme (verified against all sibling chapters — no collisions): sections `sec:gnn:*`, equations `eq:gnn:*`, figures `fig:gnn:*`, tables `tab:gnn:*`. Chapter label `ch:gnn`.

## 7. Cross-edits to existing chapters (minimal, 3 one-liners)

1. ch12 `\subsection{Graph Transformers for Cross-Asset Volatility}`: add "Chapter~\ref{ch:gnn} develops graph neural networks from first principles."
2. ch14 `\section{Graph-Based Methods}`: add "This section is a preview; Chapter~\ref{ch:gnn} is the full treatment."
3. ch15 end of `\section{Spillover Indices as Predictive Features}`: add the handoff sentence — hand-crafted spillover features vs learning on the network directly (Chapter~\ref{ch:gnn}).

## 8. Bibliography additions and corrections

New entries (natbib authoryear, matching references.bib house style): SanchezLengelingEtAl2021 (Distill, DOI 10.23915/distill.00033), KipfWelling2017, Velickovic2018GAT, Gilmer2017, Battaglia2018, Hamilton2017, XuHuLeskovecJegelka2019, LiHanWu2018, BriniToscano2024 (SpotV2Net), ChiGaoWang2026DCRNN (J. Forecasting version; PDF in hand is arXiv v3), ChiGaoWang2024GSP (distinct key — same authors both papers; a bare "ChiGaoWang2024" would collide), BoettiNunes2026, ONuallain2025, Mallory2026, Wade2026GNNPortfolios, ShaoZhangWang2022 (STID), IvanovProkhorenkova2021 (BGNN), SonaniBadiiMoin2025, ChoiKim2024, ZhouXieWangGongZhu2025 (EMGNN), KumarUmeorahAlochukwu2024 (cite the arXiv v1 we hold — the 2026 Mathematics journal version is a different, degraded artifact; note this explicitly in prose), LeeCho2025 (H-ETE-GNN), CarteaCucuringuFang2026 (SSRN, cited abstract-only), GongEtAl2025 (ASTGCN, cited qualitatively). Ready-to-paste entries live in the per-paper extracts.

**Corrections to existing entries (required — ch12 already cites one of them):**
1. `ChenRobert2022` — current entry has wrong authors ("Yuntong Chen and Stephen Roberts"), wrong title, wrong arXiv id (2209.09014). Replace with the corrected entry from the extract (Chen & Robert, "Multivariate Realized Volatility Forecasting with Graph Neural Network", ICAIF '22 / arXiv:2112.09015). This silently fixes ch12's citation too.
2. `ZhangCucuringuDong2023` — stub ("Working Paper", missing co-author Xingyue Pu). Replace with corrected entry (IJF 41(1):377–397; arXiv 2308.01419).
3. `ZhangPuCucuringuDong2024` — wrong DOI (nbad012 → nbae026) and phantom volume/issue. Correct per extract.

**Anchor policy:** the GNNHAR PDF in hand is the arXiv v1 preprint — all page anchors in the chapter use arXiv pagination (e.g., Table 1 arXiv p.15; over-smoothing is **Fig. 8, arXiv p.24** — the earlier brief's "Fig 6-7" was wrong; DJIA graph diameter 3, S&P 100 diameter 5, Table A.2 p.34).

## 9. Scope guards (YAGNI)

- No graph generative models, hypergraphs, duals, or web-scale sampling beyond the one "what we skip" paragraph.
- No reproduction of ch15's GFEVD derivation — recall by `\Cref` only.
- No regime-detection theory (jump models, MS-GARCH) — that belongs to ch13's regime section and the project-reference guide; §16.10 cites the ranking result only.
- Worked examples capped at two (one-hop by hand; GAT weights by hand) plus small numeric illustrations inside boxes.
- Abstract-only sources (Cartea et al., ASTGCN) may contribute *design ideas and qualitative claims only*, always flagged; no numeric deltas cited from them except the explicitly-abstract-verbatim 30% MSE figure with its caveat.

## 10. Risks & mitigations

- **PDF text-layer garbling of equations** → extraction agents tag [UNCERTAIN]; Pass 2 verifier re-reads sources; nothing uncertain ships.
- **Duplication with ch14/ch15** → division of labor stated explicitly in §16.7 opener + the three cross-edits; ch14 keeps the preview role.
- **Chapter length** (~45–55 pp target, the guide's largest) → the §16.9 survey and §16.11 checklist are deliberately compressed; condenser pass (write-chapter Pass 3) enforces.
- **Numbering shift of chapters 16–19 → 17–20** → all guide cross-refs are `\Cref`-based; verification-folder filenames keep their old numbers (they are historical artifacts, not live links); markdown mirror regenerated at finalize.
- **12 TikZ figures × verify-diagram loops** → figures kept structurally simple (block/flow styles from the preamble); verify-diagram runs after each.

## 11. Self-review (spec gate)

- Placeholder scan: none (extract-dependent details are named as "from extract" with the extract files already on disk — resolved at contract time, which is part of the plan, not an open TBD in scope).
- Consistency: placement (§2) matches cross-edits (§7); notation (§5) matches ch12/ch14 usage; every Arc 2 claim traces to a brief or extract.
- Scope: one chapter, one implementation plan — decomposition not needed; the write-chapter pipeline is the executor.
- Ambiguity: the only genuinely open call was placement, argued and closed in §2.
