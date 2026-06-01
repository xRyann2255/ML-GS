# Research Journal

Append-only log of what was explored and learned each session. Claude reads this at the start of every session to pick up where we left off.

Each entry captures understanding, not just activity. Focus on: what did we learn, what surprised us, what questions came up.

---

## 2026-05-06 -- Approach Reset

**Question explored:** Are we going about this project the wrong way?

**What we found:**
- In 8 days we went from project kickoff to a 27-task implementation plan, package skeleton, and "ready for Sprint 1" -- without ever touching real data
- The entire plan was built from literature surveys, not from exploring actual RV series, running baselines, or understanding feature behavior on our data
- The tooling (parallel agents, plan-execute skills) optimizes for shipping code fast, but research projects need explore-understand-build

**Key insight:**
- Feature engineering is the core value-add for vol forecasting, not model architecture. We should be spending weeks understanding what features capture and why, with hands-on data exploration, before writing any model code

**Decision:**
- Shift from sprint/task planning to research-first exploration
- Each session focuses on understanding one thing deeply
- Build the implementation plan from discoveries, not from literature alone

**Open threads for next sessions:**
- What does RV actually look like on our tick-level data? Distribution, autocorrelation, regime behavior
- Compute HAR on real data and see where it fails -- that's where ML features should focus
- What does the leverage effect look like empirically on our assets?

---

## 2026-05-06 -- Feature Engineering, Model Architecture, and Optiver Deep Dive

**Questions explored:**
- Given our data access (tick RV, OHLCV, E-mini L2, SPX IV surface, cross-asset), what features should we build?
- Should we use tree-based methods, deep learning, or a hybrid?
- What did the Optiver Kaggle winning solutions actually do?

### Optiver 2021: What Actually Happened

The competition (predicting 10-min-ahead RV from L2 order book + trade data, ~112 anonymized stocks, ~3,965 teams) was **dominated by LightGBM with exhaustive feature engineering**. Neural networks (LSTM, CNN, Transformer, MLP-Mixer) were tried extensively and **none beat well-tuned LightGBM**.

**1st place** won by reverse-engineering the chronological order of shuffled `time_id` values (KNN graph + Hamiltonian path on price tick sizes), then computing lagged features that were otherwise impossible. The model itself was plain LightGBM. This trick is competition-specific leakage and doesn't transfer to real-world research.

**Most instructive honest solution (91st place, well-documented):**
- Ensemble of 10 models: 2 LightGBM DART + 3 TabNet + stacking models
- ~600 engineered features from a 5-step pipeline: merge book+trade, generate second-level features, temporal aggregation (max/min/mean/std/sum/exponential decay), composite features via arithmetic, random Gaussian noise columns as overfitting detectors
- LightGBM DART config: lr=0.05, max_leaves=255, min_data_per_leaf=255, 10k estimators, 400 early stopping rounds

**Top features across solutions:**
- Tier 1 (highest importance): WAP log returns, realized volatility of observation window (lagged RV), **price acceleration** (log-return-of-log-return -- sum of squared accelerations was one of the single most predictive features), volume-weighted sub-window aggregations (first 5 min vs last 5 min)
- Tier 2: bid-ask spread dynamics (quoted spread, percentage spread, spread volatility, spread momentum), order book imbalance (bid_size - ask_size)/(bid_size + ask_size), market urgency (spread x liquidity_imbalance), trade flow (total volume, order count, mean trade size)
- Tier 3: per-minute RV breakdowns, exponentially weighted decay aggregations, cross-stock aggregations (mean/std across all stocks at the same time_id)

**The 2023 Optiver "Trading at the Close" competition confirmed the same pattern:** XGBoost at MAE ~4.60 beat standalone LSTM at ~6.45 (30% worse).

**Key correction to prior understanding:** The NN-as-feature-extractor-for-trees hybrid was **NOT** the pattern that won Optiver. Solutions that combined NNs and trees did so via prediction-level ensembling (blending outputs), not feature-level stacking (NN embeddings as tree inputs). The clearest Kaggle example of the feature-extraction hybrid is actually the **American Express Default Prediction (2022)**, where 1st place used GRU embeddings fed into GBDTs.

Meta-analysis from mlcontests.com (2021-2023): GBDTs dominate pure tabular problems ~4:1 over NNs. Ensembles of GBDTs + NNs are "probably best" for maximum performance. NNs succeed specifically when there is exploitable non-tabular structure (sequences, spatial data).

### Feature Engineering Strategy for Our Project

Mapped against our actual data access, organized into three tiers:

**Tier 1 -- HAR-family (from tick-level RV):**
- Daily/weekly/monthly RV (classic HAR)
- Signed components: realized semivariance RS+/RS- (Barndorff-Nielsen, Kinnebrock, Shephard 2010). RS- (bad vol) has substantially more predictive power
- Jump vs continuous: bipower variation to separate jumps from continuous vol
- Realized quarticity: feeds HARQ, tells model how much to trust today's RV reading
- Intraday periodicity features: U-shape patterns, overnight-vs-intraday return variance ratio

**Tier 2 -- VRP and regime (from IV surface + VIX term structure):**
- ATM IV at multiple tenors minus RV (the VRP itself, at different horizons)
- IV skew (25-delta put minus 25-delta call vol) -- crash risk pricing
- IV term structure slope -- contango/backwardation in vol expectations
- VIX futures basis (VIX vs front-month future)
- VIX term structure enables contango/backwardation regime classification

**Tier 3 -- Cross-asset and microstructure:**
- Treasury curve shape: 10y-2y spread (level and change), curve curvature
- Oil volatility (CL futures RV -- energy shocks transmit to equity vol)
- FX risk-on/risk-off: USD/JPY, EUR/USD moves
- E-mini microstructure (L2 data): order flow imbalance, depth ratio, Kyle's lambda (Cont, Kukanov, Stoikov 2014)

**Engineering principle:** For each base quantity, compute level/change/z-score systematically (from Chapter 9 of the guide). This triples feature count but captures fundamentally different information (state, direction, unusualness). Trees handle this naturally since they can split on "z-score > 2" without pre-specification.

### Model Architecture Decision

**Starting point: LightGBM on engineered features.** Data is fundamentally tabular (~30 features at daily frequency, ~2,800 obs over 11 years). Gu-Kelly-Xiu (2020) confirms trees are competitive with or beat DL on tabular financial data. Advantages: SHAP interpretability for GS presentation, fast iteration, lower trial count for DSR.

**Where DL could genuinely add value:** Our E-mini L2 tick data (4M ticks/day) is a much richer sequence than Optiver's 600-second windows. A full trading day of microstructure is hard to fully capture with pre-specified aggregations. A learned intraday representation could add signal.

**Recommended hybrid (if pursued):**
1. Train small LSTM/TCN on intraday E-mini sequences (5-min return bars within each day) to predict next-day RV
2. Extract the last-layer embedding as a fixed-length "intraday state" vector
3. Feed that embedding as additional features into LightGBM alongside hand-engineered features
4. The NN operates on high-frequency data where it has plenty of training signal; the tree handles the final tabular prediction

**Why this differs from Optiver:** Optiver had 10-min windows (short sequences, hand-engineered aggregations captured most information). Our setup has full-day tick sequences for next-day prediction -- longer, richer sequences where learned representations may genuinely add value.

**Critical constraint:** Don't hyperparameter-search the neural network. Pick one architecture from the literature (2-layer LSTM, 64 hidden units), train once, extract embedding, move on. Every variant counts as a trial for DSR.

**Progression for the project:**
1. HAR, HARQ, SHAR baselines (pure econometric)
2. Ridge on HAR features + VRP + cross-asset (linear baseline, Chapter 11 demands this)
3. LightGBM on same features (does tree beat ridge? if yes, nonlinear interactions exist)
4. LightGBM + LSTM embeddings from intraday data (does intraday component add IC?)

Each step has a clear scientific question and is independently reportable.

**Open threads:**
- Need to actually compute HAR on our data before any of this matters
- Price acceleration (log-return-of-log-return) was a top Optiver feature -- worth testing on daily data too
- The random Gaussian noise column trick from the 91st place solution is clever for detecting overfitting -- consider adding this

---

## 2026-05-12 -- Ensemble vs. Feature Stacking for Multi-Horizon RV

**Question explored:** Should we use feature stacking (LSTM embeddings fed to LightGBM) or prediction blending at each forecast horizon (h=1, h=5, h=22)?

**What we found:**
- Cross-referenced every relevant paper in the bibliography + independent web research (2023-2026)
- Christensen, Siggaard, Veliyev (2023): ML gains over HAR *increase* with forecast horizon. LSTM marginal value lowest at h=1 where tabular features already capture daily autocorrelation
- No paper demonstrates feature stacking beating prediction blending at h=22 for RV specifically
- At h=1, model errors are most correlated (all track strong daily autocorrelation), so stacking risks overfitting redundant information
- At h=22, smallest effective sample size after walk-forward splitting makes stacking's overfitting risk highest
- The gradient-isolation problem is real: LightGBM cannot back-propagate into the LSTM, so embeddings are never optimized for the tabular objective
- Optiver top solutions used prediction blending, not feature stacking

**What surprised us:**
- The doc's "stacking at h=1/h=5, blending at h=22" contradicts Ch. 11 of the vol-project-ref guide, which says "Do Not Stack Features" universally. Three internal sources disagree with each other.
- The simplest viable approach (LSTM scalar point forecast as one extra LightGBM feature) gets ~80% of any stacking benefit with near-zero implementation cost beyond the LSTM itself. Full embedding extraction (32-64 dim) adds complexity with minimal proven gain.
- Simple average ensemble is competitive with optimized blending at h=22, where overfitting risk dominates. The more sophisticated the blending method, the more it benefits from large sample sizes (which h=22 doesn't have).

**Recommendation:**
- Prediction blending at all horizons (inverse-QLIKE weighted at h=1, linear blend at h=5, simple average at h=22)
- LSTM branch is a stretch goal; minimum viable ensemble is HAR-best + LightGBM blend
- If LSTM is pursued, use its scalar forecast as one extra LightGBM feature, not high-dimensional embeddings

**Open threads:**
- Need to verify QLIKE log-space sign convention in actual code (may be reversed vs. Patton 2011)
- CV purge gap enforcement for h=22 is a correctness bug that must be fixed before any multi-horizon evaluation
- Does regime-conditional QLIKE evaluation reveal that ensemble benefits are concentrated in crisis periods?

---

## 2026-05-31 -- What Beats HAR? (2024-26 SOTA deep-research sweep)

**Question explored:** For daily realized-vol forecasting under QLIKE, does any modern method (transformers, TS foundation models, GNNs, LLMs, gradient boosting) actually beat HAR/HARQ out-of-sample with statistical significance?

**Method:** Built and ran a new deep-research workflow (`deep-research-distill`) -- 87 external sources harvested, 11 adversarially verified and kept. Full brief: `notes/deep-research/2026-05-31-what-beats-har-2024-26.md`

**What we found:**
- For daily, univariate, equity-index RV under QLIKE -- our exact cell -- essentially nothing beats a properly-fitted rolling HAR with significance. HARd-to-Beat (IJF 2025, 1,445 stocks): HAR-WLS QLIKE ~0.313 vs FNN 0.571; HAR in the MCS 85.5% vs FNN 36.4%
- ML/modern methods win reliably only when the problem changes: richer info sets (options-implied/rough-Heston spot vol: +5.8% QLIKE, DM p<0.01), multivariate realized covariance (GHAR +1.8% QLIKE, MCS p=1.000), or longer horizons (h=5/22)
- Christensen-Siggaard-Veliyev (ML beats HAR, gains rise with horizon) vs Branco-Rubesam-Zevallos (no nonlinear ML beats HAR-X) reconciles to: the win is in FEATURES, not architecture -- give the linear baseline every predictor the ML model gets (HAR-X) before claiming an edge

**What surprised us / corrections to prior notes:**
- Two "facts" in our notes are wrong: the "XGBoost 0.1219 vs HAR 0.1482 daily" figure does NOT appear in the Intraday-Commonality paper (it shows HAR-D >= XGBoost at h=1); HARd-to-Beat's window is 630 days (~1.7y), not the 2.5-4y previously noted
- The Fed FEDS regime-HAR superiority we'd logged is an MSPE result; the authors say it largely vanishes under QLIKE (our primary loss). MSPE-win != QLIKE-win is the single most common way the literature overstates ML
- Every 2025-26 transformer/foundation-model/LLM QLIKE claim so far is MSE-only, significance-free, low-tier-venue, or metric-ambiguous -- none clears the DM+MCS bar on daily equity-index RV yet

**Open threads:**
- Decision needed: univariate RV (HAR's fortress) vs realized covariance (where graph methods demonstrably win, and the desk may care more for portfolio risk) -- reshapes which SOTA is relevant
- Port target: JLDC/HARd-to-Beat (Python: rolling HAR-WLS + lasso/ffnn/gbt/rf + QLIKE losses) as the fair-fight baseline harness on the GS machine; adopt its 630-day/daily-re-estimate spec
- Ingest arXiv 2604.02743 (rough-Heston options augmentation) -- strongest grounded univariate win, validates the Tier-2 options/VRP layer
- Resolve the skill-score direction ambiguity in the foundation-model paper (arXiv 2505.11163) before citing any number

---
