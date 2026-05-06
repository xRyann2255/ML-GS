# Project Direction Proposals

> Source: deep research survey (2026-05-06)
> Full landscape survey: `notes/deep-research-vol-papers.md`
> Bibliography: `reference/bibliography.md`

## Recommendation

A hybrid HAR-augmented gradient-boosted model with options-implied + LOB + cross-asset features evaluated by Patton-robust QLIKE under Lopez-de-Prado purged CV, with one of two flagship "wow" extensions -- either (a) a Rashomon-set analysis using TreeFARMS/SPLIT to enumerate near-optimal interpretable trees and produce *Variable Importance Clouds* (genuinely novel in finance, intellectually substantial, directly usable by a desk), or (b) a graph-neural-net cross-asset spillover forecaster (Zhang-Pu-Cucuringu-Dong 2025). See Project 3 below.

**Staged, concrete next steps**:

1. **Weeks 1-2 (immediately, regardless of project chosen)**: Set up the core data pipeline. Pull the Oxford-Man Realized Library archive (via the `bvhar` R package or your internal mirror), VIX/VVIX/MOVE from CBOE, FRED macro data. Implement HAR, HARQ (BPQ 2016), and HAR-CJ (Andersen-Bollerslev-Diebold 2007) baselines using the `arch` Python package. Reproduce the HARQ S&P 500 numbers (R^2 ~ 0.56, QLIKE ~ 0.136) as a sanity check before touching ML.

2. **Week 3**: Implement Patton's QLIKE loss as a custom objective and a Hansen-Lunde-Nason MCS routine. This is foundational for everything that follows; without it, you cannot honestly compare models. Set up Lopez-de-Prado purged k-fold CV with a 1-day embargo for the daily-RV setting (longer for multi-step targets).

3. **Week 4 -- decision point -- choose a project**:
   - If desk feedback emphasises **interpretability and credibility on the floor**, pick **Project 3 (Rashomon Volatility)** -- this is the recommended flagship.
   - If desk feedback emphasises **multi-asset coverage** (a cross-asset risk team), pick **Project 4 (GNN)**.
   - If you want the **safest delivery with concrete options-trading P&L attribution**, pick **Project 1 (HAR-X-Boost)**.
   - If you have access to **internally-curated tick data and the team has rough-vol interest**, pick **Project 2 (HARNet++ with rough-vol prior)**.

4. **Weeks 5-10**: Execute the chosen project per the timelines below.

5. **Weeks 11-12**: Two deliverables -- the presentation, and a short internal write-up structured as: (a) econometric baseline numbers, (b) ML model numbers, (c) MCS / DM tests, (d) feature importance / interpretability analysis, (e) one concrete "would-this-make-money" application case study (e.g. SPX variance-swap markup adjustment from your forecast residuals).

**Benchmarks that would change the recommendation**:
- If by **week 4** TreeFARMS/SPLIT cannot enumerate even depth-3 Rashomon sets in <30 minutes on your binarised vol panel, **fall back to Project 1** (LightGBM with SHAP) -- Project 3's compute risk is too high.
- If your LightGBM beats HARQ by less than 2% QLIKE on the validation set with the full feature set by **week 6**, the upper-bound on any ML approach for that information set is small and you should pivot to either (a) expanding the information set materially (LOB or options-implied features) or (b) Project 2's HARNet, which exploits architecture rather than features.
- If a desk strat or trader cannot read your final model and explain it to a colleague in 60 seconds, you have built something the floor will not use -- strip back to the simplest model that meets your QLIKE bar.

**For a Goldman Sachs floor specifically**: prioritise (i) absolutely rigorous validation (purged CV + MCS + DM; explicit OOS period including 2020 COVID and 2022 rates regime), (ii) interpretable feature attribution (SHAP minimum, Variable Importance Clouds ideal), (iii) one slide tying the forecast improvement to a concrete trading P&L (variance-swap markup, dispersion P&L, or vol-target Sharpe).

---

## Project 1: HAR-X-Boost (Safe)

- **Pitch**: Beat HAR(Q) on S&P 500 daily RV forecasting with a tabular gradient-boosting model on a richer feature set, evaluated rigorously.
- **What it does**: Take the Oxford-Man / yfinance / FRED stack. Compute RV, BV, RQ, RS+/RS-, signed jump variation. Add VIX, VVIX, IV slope/curvature from CBOE, MOVE, DXY-vol, FRED macro releases. Train LightGBM/XGBoost vs HAR/HARQ/HAR-X baselines. Evaluate via QLIKE, MSE under the Hansen-Lunde-Nason MCS, with purged-k-fold CV (Lopez de Prado).
- **Trading-floor relevance**: Direct input to vol-targeting and ETF options books; SHAP feature importance gives portfolio managers an interpretable story.
- **Data**: Oxford-Man Realized Library; CBOE VIX historical; FRED macro releases; yfinance for SPX returns; OptionMetrics if available internally.
- **ML**: LightGBM with QLIKE custom objective; SHAP for explainability; combinatorial purged CV.
- **Baseline**: HAR, HARQ, HAR-X with same features as linear model.
- **Feasibility (10-12 wk)**: Wks 1-2 data pipeline; 3-4 features + HAR baselines; 5-7 LightGBM tuning + custom QLIKE; 8-9 MCS / DM tests; 10 SHAP, ablations; 11-12 writeup, options-trading P&L sim.
- **Risk**: HAR-X may not be statistically beaten -- write the project so a *null result with rigour* (per Branco et al. 2024) is itself the deliverable.
- **Wow factor**: Medium. **Novelty**: Low.

## Project 2: Neural HAR with Rough-Vol Prior (Moderate)

- **Pitch**: Reproduce HARNet (Reisenhofer-Bayer-Hautsch 2022) and extend with rough-vol-derived features and signed semi-variance inputs across multiple asset classes.
- **What it does**: Re-implement HARNet (TensorFlow GitHub mdsunivie/HARNet exists) for SPX. Add (a) Hurst exponent estimated rolling per Cont-Das (2024) p-variation method, (b) RFSV one-parameter forecast as additional input or a residual-modelling target, (c) signed semivariances and VIX. Compare to plain HARNet, HAR, HARQ, and the RFSV forecast. Test on SPX, FTSE, DJI, plus extension to FX (EUR/USD) and rates futures (TY).
- **Trading-floor relevance**: Validates rough-vol's forecasting claims; produces a single forecaster usable across asset classes; resolves rough-vol-vs-microstructure debate empirically.
- **Data**: Oxford-Man for daily RV/RK; high-frequency tick data from LOBSTER (free academic AAPL/INTC samples) or Refinitiv if available; truefx.com for FX.
- **ML**: HARNet + dilated TCN; train under QLIKE; compare initialisation strategies (HAR-init dominates per Reisenhofer et al.).
- **Baseline**: HAR, HARQ, RFSV (Gatheral et al. 2018), HARNet.
- **Feasibility**: Tight in 10 wk; 12 wk comfortable. Wks 1-3 reproduce HARNet; 4-5 implement Hurst rolling estimator; 6-8 ablations across asset classes; 9-10 writeup.
- **Risk**: HARNet improvements may not generalise outside SPX; rough-vol features may not add value, especially given the Cont-Das critique.
- **Wow factor**: High intellectual content; speaks to the rough-vol controversy. **Novelty**: Moderate.

## Project 3: Rashomon Volatility (Recommended Flagship)

- **Pitch**: First rigorous Rashomon-set analysis applied to financial time-series forecasting: enumerate *all* near-optimal interpretable decision trees for realized volatility, compute Variable Importance Clouds, and use the structure to (a) identify essential vs. redundant features, (b) generate a portfolio of forecasters that disagree only on uncertain regions of feature space.
- **What it does**:
  1. Build a feature panel for daily RV forecasting on S&P 500 (and DJIA constituents) -- HAR features, BV, RQ, RS+/RS-, VIX/VVIX/IV slope, microstructure proxies, cross-asset vols.
  2. Use **GOSDT** / **TreeFARMS** / **SPLIT/RESPLIT** to enumerate the Rashomon set R(epsilon) of trees within epsilon of the optimal training-loss tree, at depths 3-5.
  3. Compute **Variable Importance Clouds** (Dong & Rudin 2020) on R(epsilon): for each feature, [min, max] of permutation importance across trees in R(epsilon). Features with strictly positive lower bound are *essential*; features with overlapping clouds are *interchangeable*.
  4. Construct a **Rashomon ensemble** -- uniform / loss-weighted average of forecasts from R(epsilon); compare to LightGBM, HAR, HARQ.
  5. **Predictive multiplicity analysis** (Marx et al. 2020; McTavish-Boner-Donnelly-Seltzer-Rudin 2025 ICML "Leveraging Predictive Equivalence"): identify which days have the highest disagreement across R(epsilon) -- these are the days the desk should *not* trust a single point forecast.
- **Trading-floor relevance**:
  - **Interpretability**: every model in R(epsilon) is a sparse decision tree with <=16 leaves -- a desk strat or trader can read it in 30 seconds. Compliance-friendly.
  - **Feature curation**: tells you definitively which microstructure / options features are redundant on the panel -- can prune feature pipelines.
  - **Risk gauge**: high Rashomon-set forecast variance on a given day is itself a tradable signal of model uncertainty (analogous to VVIX as model-vol-of-vol).
  - **Genuinely novel**: I am not aware of any published application of formal Rashomon-set enumeration to financial time series.
- **Data**: Oxford-Man daily realized library; VIX and VVIX from CBOE; FRED for macro; LOBSTER samples for microstructure; OptionMetrics if available internally.
- **ML stack**: GOSDT (PyGOSDT), TreeFARMS (Python), SPLIT-ICML repo (`github.com/VarunBabbar/SPLIT-ICML`), shap, scikit-learn for baselines, LightGBM for accuracy benchmark.
- **Econometric baseline**: HAR, HARQ, HAR-X with same features; LightGBM as ML upper bound. The interesting finding is *whether a single optimal sparse tree (<=8 leaves) can match LightGBM on this panel* -- Rudin et al. (2024) argue this is often the case.
- **Feasibility (10-12 wk)**:
  - Wk 1-2: data pipeline + HAR baselines.
  - Wk 3-4: GOSDT/TreeFARMS first runs (depth 3-4); compute Rashomon ratio for vol panel.
  - Wk 5-6: SPLIT/RESPLIT for deeper trees; Variable Importance Clouds.
  - Wk 7-8: Rashomon ensemble forecast vs LightGBM/HAR; MCS evaluation.
  - Wk 9-10: predictive multiplicity -> "model uncertainty" signal; case studies (e.g. COVID Mar 2020, GFC).
  - Wk 11-12: presentation, write paper draft.
- **Risk factors**:
  - **Computational scaling**: TreeFARMS struggles past depth 4 with >50 binarised features. Mitigation: SPLIT/RESPLIT (orders of magnitude faster per Babbar et al. 2025); restrict to depth-4 with thresholded continuous features (~30-60 binarised features).
  - **Regression vs classification**: TreeFARMS/GOSDT are formally classification methods. Either bin the target (RV quantile classification -- useful as a "vol regime" forecaster) or use STreeD/regression-tree extensions; an alternative is to forecast log-RV residuals from HARQ binned into 3-5 quantiles (a *vol surprise* classifier).
  - **Rashomon set may be small** for low-noise tabular data -- Semenova-Rudin-Parr (2022) actually predict large Rashomon sets are typical for noisy financial data, which makes this a *meaningful* finding either way.
- **Wow factor**: Very high. **Novelty**: High -- likely first finance application.

## Project 4: Cross-Asset Volatility GNN (Ambitious)

- **Pitch**: Build a graph attention network forecasting next-day RV jointly across 30+ assets (S&P 500 sectors, single names, FX majors, rates futures, commodities), trained with QLIKE loss to handle vol heteroscedasticity, and compare to univariate HAR / multivariate HEAVY-MV.
- **What it does**: Replicate and extend Zhang-Pu-Cucuringu-Dong (2025). Construct a sparse asset graph from rolling-window correlations or estimated Granger-causality; nodes are assets, edge weights are spillover strengths. Each asset's RV evolution depends on its own HAR features plus a graph-attention aggregation of neighbour vols. Train with QLIKE.
- **Trading-floor relevance**: Direct input to dispersion books, risk-parity portfolios, and multi-asset risk models. Identifies *which* asset's vol leads which -- actionable for vol-arb desks.
- **Data**: Oxford-Man for the cross-asset vol panel; FRED / yfinance for returns.
- **ML**: PyTorch Geometric GAT/GCN, torch_geometric.nn.GATv2Conv; QLIKE loss; rolling refits.
- **Baseline**: Univariate HAR per asset; HEAVY-MV; multivariate Realized GARCH.
- **Feasibility**: Tight in 10 wk because of multi-asset data pipeline and graph engineering. Doable in 12 if scope is restricted to (say) 20 SPX sector ETFs + 5 FX + 5 rates.
- **Risk**: Zhang et al. show multi-hop adds little; the gains are modest. Risk that effort/payoff is unfavourable.
- **Wow factor**: High (visualisations of inferred volatility-spillover graphs are striking). **Novelty**: Moderate -- extends published work.

---

## Caveats

1. **No definitive answer on whether ML beats HAR.** Christensen-Siggaard-Veliyev (2023) say yes; Branco-Rubesam-Zevallos (2024) say no. Reconciliation: ML tends to win at longer horizons (>=1 week) and with truly new information (LOB, news), and ties or loses at the daily horizon when given HAR-X-style information. Calibrate expectations accordingly: a daily-RV deliverable that beats HARQ by 3-5% QLIKE is a *strong* result, not a mediocre one.

2. **Rough volatility is openly contested.** Cont & Das (2024) provide a serious challenge to the empirical foundation of rough volatility, arguing that observed roughness in realized volatility may be a microstructure-noise artefact rather than a property of true volatility. Forecasting projects that critically depend on H ~ 0.1 should explicitly stress-test against the Cont-Das p-variation diagnostics and not over-claim.

3. **Translating QLIKE improvement into desk P&L is application-specific.** No general theorem exists relating forecast loss to PnL. Project deliverables should explicitly link a forecast metric to a concrete trade -- variance swap markup, dispersion book mark-to-market noise, or risk-targeted Sharpe -- not stop at the loss number. Beware of QLIKE/MSE improvements that come from over-fitting to high-vol regimes which dominate the loss but are hedged anyway by traders.

4. **Rashomon sets in finance are unexplored.** Project 3 is genuinely novel -- that is the upside. The downside is there is no published roadmap for handling time-series targets, and TreeFARMS/SPLIT computational scaling beyond ~50 binarised features at depth 5 remains untested in this domain. Have a Plan B (LightGBM + SHAP) ready by week 4.

5. **Out-of-sample stability across regimes.** Most academic studies stop at 2020 or 2021. Performance during the 2022 rates regime change, the 2024 dispersion environment, and the 2025 macro vol cycle is under-studied. Reserve at least the 2022-2025 segment as a held-out test and report results separately from earlier OOS periods.

6. **Dataset access caveats.** The Oxford-Man Realized Library was discontinued around 2022; the canonical archived dataset accessible via the `bvhar` R package or academic mirrors covers up to 2019/2020 depending on series. For post-2020 daily realized measures you will need to compute them yourself from intraday data (Refinitiv tick history internally, or LOBSTER samples). OptionMetrics IvyDB IV surface data is internally available at GS but not free externally -- note this in your reproducibility section.

7. **Single-paper claims are flagged as "suggestive, not settled" throughout this report** (e.g. the Souto-Moradi NBEATSx 13%/8% improvement, the Taneva-Angelova-Granchev Transformer findings). Treat these as motivation for replication on your own data, not as established results. A useful internship deliverable is precisely to test whether a single-paper finding generalises.

8. **The Optiver Kaggle 2021 evaluation metric (RMSPE on 10-min realized vol) is not the same as daily-RV QLIKE forecasting.** The Kaggle competition is closer to an intraday vol *nowcasting* task. The feature-engineering ideas transfer; the evaluation conclusions do not.
