# Project FAQ

## Why "Risk as Alpha"? Why risk-system outputs specifically?

**The data moat argument.** Every project direction needs to answer "why does this need to be done at GS?" If the answer is "it doesn't," you're doing academic research on a bank's clock. Risk-system outputs — daily firm-level VaR, component VaR by asset class, factor-VaR concentration, scenario P&L, VaR utilization — are proprietary. External researchers reconstruct crude proxies from quarterly Fed Z.1 tables (published with a 3-month lag) or Compstat leverage ratios. SecDB has the real thing, daily, cross-asset, with correct dealer sign.

**The theory already exists and is well-tested.** Intermediary asset pricing (He-Krishnamurthy 2013) proves mathematically that risk premia rise nonlinearly when dealer balance-sheet constraints bind. Adrian-Etula-Muir (2014) show a single-factor intermediary-leverage SDF explains R²=77% of 41 test portfolios. He-Kelly-Manela (2017) extend this to a single pricing kernel across equities, options, CDS, bonds, FX, and commodities. Adrian-Shin (2010) show dealer repos forecast VIX innovations. The theory is strong — the bottleneck has always been data quality, not methodology.

**Risk outputs are the direct measurement of what theory predicts matters.** The theory says dealer balance-sheet constraints drive asset prices. VaR utilization (usage vs. limit) is literally a measurement of how constrained the balance sheet is. Factor-VaR concentration is a measurement of crowding. Scenario P&L dispersion measures tail exposure. These aren't proxies — they're the thing itself.

**Cross-asset desk is the perfect home.** The intermediary asset pricing literature is fundamentally about cross-asset effects (one firm's constraints ripple across all markets). A rates-only or equities-only desk would limit you to within-asset tests. XA lets you test the full theory.

**The alternatives are weaker on the "why GS?" question:**
- Project 4 (factor-neutral ML residuals) — safest, but could largely be done with public data + gs-quant. Less differentiated.
- Project 2 (book-gamma) — strong, which is why it's the fallback. But Baltussen et al. (2021) already published the core result; you'd be confirming with better data rather than testing something new.
- Project 3 (calibration residuals) — novel, but narrower scope (vol surfaces only).
- Project 5 (GP smoothing) — clean deliverable, but a desk tool, not a signal.

**The pitch framing is strongest with risk.** "I'm not claiming my black box found alpha — I'm testing whether the risk system you already run contains predictive information that theory says it should." That framing makes it a scientific hypothesis test, not a fishing expedition. Trading desks trust this framing far more than "my neural net found a pattern."

---

## "If risk outputs predict returns, wouldn't the risk team already know that?"

Not necessarily, and it doesn't matter if they do. The risk team uses these outputs for risk *management* — monitoring limits, sizing hedges, stress testing. That's a fundamentally different objective function from asking "do changes in these outputs predict future returns?" A risk manager watching VaR utilization is asking "are we within limits?" — not "does a spike in utilization predict forced deleveraging that creates a tradeable reversal in the most-concentrated asset class three days later?" Same data, completely different question.

It's also possible that the predictive content is real but too small or too noisy for a human to act on intuitively. That's exactly the scenario where ML on tabular data (LightGBM) earns its keep — finding systematic, modest-magnitude relationships across many features that a person watching a dashboard wouldn't notice.

---

## "Isn't this just saying 'when VaR is high, vol is high'?"

This is the most important challenge to have a clean answer for. If internal VaR just correlates with VIX — which is public — then there's no proprietary information content and no reason to use SecDB for this.

The project handles this through confound checks: every signal that shows predictive power is re-tested with public factors (VIX level, credit spreads, term slope, realized correlation) added as controls. If the signal's IC drops to zero with controls included, it's redundant with public information and gets documented as a negative result. The claim is only valid for signal that survives *after* controlling for what everyone can already see.

The theory also predicts specific channels that go beyond "high VaR = high vol." For example: VaR *utilization* (usage vs. limit, not level) predicts forced selling specifically in the most-concentrated asset class. Factor-VaR *concentration* (Herfindahl) predicts crowding-driven drawdowns. Scenario P&L *dispersion* measures tail asymmetry. These are structurally different from "vol is high."

---

## "What's the capacity?"

This is always the first question from a trader and the honest answer is: "it depends on what the signal predicts, and I'll quantify it explicitly."

If the signal predicts index-level or macro moves (VIX innovations, broad asset-class drawdowns), capacity is large — you'd express it through liquid futures and the constraint is more about Sharpe degradation at size than market impact. If it predicts single-name or illiquid instruments, capacity may be small.

The project includes an explicit capacity and transaction-cost analysis (Phase 4A, Task 19): run the best model at varying cost levels (0, 2, 5, 10, 20, 50 bps), find the breakeven cost where Sharpe hits zero, and estimate order-of-magnitude capital absorption before market impact degrades returns. The Sharpe-vs-cost curve is one of the final presentation charts.

A signal with Sharpe 1.5 but $5M capacity is an interesting research finding. A signal with Sharpe 0.6 but $500M capacity is a tradeable strategy. The presentation will be honest about which category the result falls into.

---

## "How is this different from what the strats team already does?"

Strats build and maintain the risk models — they produce the VaR numbers, calibrate the scenarios, design the factor decompositions. This project doesn't touch any of that. Instead, it asks a second-order question: do the *aggregated outputs* of those models, viewed as a time series, contain cross-asset predictive information?

Think of it this way: a weather station measures temperature, pressure, and humidity. Meteorologists use those readings to forecast weather. But you could separately ask: "does the *pattern* of readings across all stations predict stock market volatility?" That's a different question from weather forecasting, even though it uses the same instruments. Similarly, this project uses risk-system outputs as features in a prediction problem that the risk team was never trying to solve.

The strats team optimizes within the risk framework. This project looks at the risk framework from the outside and asks whether its outputs, when aggregated across desks and asset classes in ways the intermediary asset pricing literature suggests, predict things the theory says they should.

---

## "What data goes into the model, why that data, and what does the model output?"

### Model Inputs (Features)

The model ingests five families of daily time series pulled from SecDB risk cubes. Each family maps to a specific mechanism predicted by intermediary asset pricing theory:

| Feature Family | What It Measures | Raw Inputs from SecDB | Why This Data |
|---|---|---|---|
| **VaR utilization** *(priority)* | How constrained the balance sheet is right now | VaR usage as % of limit, rate of change of utilization | When utilization approaches the limit, theory predicts forced deleveraging and fire sales (Coval-Stafford 2007). This is the most direct measurement of the constraint that drives the entire intermediary asset pricing framework. |
| **Factor concentration** *(priority)* | How crowded the book's risk exposures are | Factor-VaR Herfindahl index, top-3 factor share | Low dispersion across factors = hidden concentration. When risk is concentrated in a few factors and utilization is high, theory predicts correlated unwinding across desks holding the same exposures (He-Kelly-Manela 2017). |
| **VaR dynamics** | Aggregate dealer risk appetite | Firm-level delta VaR, component VaR by asset class, VaR rate-of-change | Rising VaR signals expanding risk appetite; falling VaR signals contraction. Adrian-Shin (2010) show the *change* in dealer risk exposure forecasts VIX innovations — the direction and speed of the move matters, not just the level. |
| **Scenario P&L** | Tail risk awareness and directional exposure | Stress-scenario P&L rank and dispersion, worst-case scenario identity | Wide scenario P&L dispersion means asymmetric tail exposure. The identity of the worst-case scenario reveals what the risk system thinks the book is most vulnerable to — a change in worst-case identity signals a regime shift in risk exposure. |
| **Cross-asset flow** | Capital rotation across asset classes | Component VaR shifts between asset classes over time | If component VaR is migrating from rates to credit, the balance sheet is being reallocated. Theory predicts that capital flowing *out* of an asset class tightens constraints there and loosens them elsewhere — a cross-asset transmission mechanism. |

Each feature is further transformed into z-scores, rates of change, and rolling statistics to capture dynamics, not just levels. Features are point-in-time stamped (when the data was *known*, not when it *applied*) to prevent lookahead bias.

### Why This Data Specifically

Three reasons compound:

1. **It's the direct measurement.** Intermediary asset pricing theory says dealer balance-sheet constraints drive risk premia. These features don't *proxy* for constraints — VaR utilization literally *is* the constraint. External researchers use quarterly Fed Z.1 tables or Compstat leverage ratios, which are stale, aggregated, and lack dealer sign. SecDB provides the real thing daily.

2. **Each feature has a pre-registered theoretical hypothesis.** This isn't data-mining. Before any model is trained, each feature family has a specific, citable theoretical prediction about *why* it should predict the target. VaR utilization predicts forced selling (Coval-Stafford). Factor concentration predicts crowding-driven drawdowns (He-Kelly-Manela). VaR dynamics predict volatility innovations (Adrian-Shin). The model is testing whether these theories hold with real data, not searching for patterns.

3. **The priority ordering is theory-driven, not data-driven.** VaR utilization and factor concentration are tested first because their theoretical backing is strongest and most specific. The remaining three families are tested second. If the priority pair shows nothing, the others are unlikely to either — and the project pivots rather than continuing to search.

### Model Outputs (Targets)

The model predicts four targets, each chosen because theory makes a specific prediction about it:

| Target | What It Is | Why This Target |
|---|---|---|
| **VIX innovations** | Unexpected changes in VIX (residual after removing autocorrelation) | Cleanest single target. Adrian-Shin (2010) directly demonstrate that dealer repo positions forecast VIX innovations. This is the most replicated result in the intermediary asset pricing literature. |
| **Drawdowns in the most-concentrated asset class** | Whether the asset class with the highest factor-VaR concentration draws down over the next 1-21 days | Tests the specific Coval-Stafford (2007) fire-sale mechanism: when risk is concentrated and utilization is high, forced selling should hit the most-concentrated asset class first. |
| **Cross-asset momentum reversals** | Whether crowded momentum factors reverse | He-Kelly-Manela (2017) predicts that when dealer constraints bind, momentum strategies across asset classes mean-revert simultaneously. VaR utilization spikes should predict these coordinated reversals. |
| **Realized volatility** | Forward 1/5/21-day realized volatility across asset classes | Simpler than return prediction, higher signal-to-noise ratio. If risk-system outputs predict anything, volatility is the lowest bar — and still tradeable (vol surfaces, variance swaps). |

### What the Model Actually Produces

The model outputs a **continuous score** (not a binary signal) for each target, representing the predicted magnitude. In practice:

- **Ridge regression** produces a linear weighted combination of features → a predicted value for each target
- **LightGBM** produces a nonlinear prediction → same predicted value, potentially capturing threshold effects (e.g., VaR utilization at 90% matters more than at 60%)
- Both models are run on **identical features** so the comparison is purely about whether nonlinearity adds value
- Predictions are evaluated by **information coefficient (IC)** — rank correlation between predicted and realized values — not by P&L directly
- The backtesting engine then translates predictions into simulated positions and computes P&L, Sharpe, turnover, and transaction costs

The model does *not* output trade recommendations, position sizes, or portfolio weights directly. It outputs a predictive score that the backtesting engine converts into a signal, which is then evaluated for economic significance after transaction costs.

---

## "Why ML? Why not just run a regression?"

You *do* run a regression first. The ridge baseline is mandatory on every test — it's the first model fitted on every feature set, and it appears alongside LightGBM on every chart. ML is only justified if it beats it.

This is grounded in Kozak-Nagel-Santosh (2020 JFE), which showed that ridge-shrunk SDFs on principal components of characteristics match or beat nonlinear ML in the cross-section of equity returns. If the relationship between risk-system outputs and future returns is linear, ridge will capture it and GBM will add nothing. That's a valid finding — it means the signal exists but doesn't need ML.

The case for GBM over ridge is specifically about **nonlinear interactions and threshold effects.** Theory predicts these: He-Krishnamurthy (2013) shows risk premia rise *nonlinearly* when balance-sheet constraints bind. VaR utilization at 60% might mean nothing, but at 90% it could trigger forced deleveraging. That's a threshold effect that ridge can't capture but a tree-based model can. Similarly, the interaction between factor concentration *and* VaR utilization (highly concentrated *and* near the limit) might matter more than either alone.

So the answer is: "I'm not claiming ML is necessary. I'm testing whether it adds anything. If ridge wins, that's the result and it's still publishable. If GBM wins, I'll show you exactly where the nonlinearity is using SHAP."

---

## "Why decision trees? Why LightGBM specifically?"

### Why decision trees for financial data

The data in this project is **tabular** — rows of daily observations, columns of numerical risk features. This is not images, not text, not sequences. For structured tabular data, gradient-boosted decision trees (GBDTs) are the empirically dominant method. This isn't opinion — it's the consistent finding across large-scale benchmarks:

- **Gu, Kelly, Xiu (2020 RFS)** — the canonical ML horse-race on 60 years of US equity returns. Tested neural nets, random forests, GBDTs, elastic net, PCA regression, and more. Trees and shallow neural nets led; deep nets did not systematically dominate on tabular financial data.
- **Grinsztajn, Oyallon, Varoquaux (2022, NeurIPS)** — "Why do tree-based models still outperform deep learning on tabular data?" Benchmarked across 45 datasets. Trees won on medium-sized tabular data, which is exactly what this project has (~1,250 daily observations × 15-30 features).
- **Shwartz-Ziv and Ariel (2022)** — confirmed trees outperform deep learning on tabular data in most settings, especially with limited sample sizes.

Decision trees also have structural advantages for this problem:

1. **Threshold effects are native.** A tree split at VaR utilization = 90% directly captures "nothing happens below 90%, everything happens above 90%." Ridge regression can only model this as a linear slope. He-Krishnamurthy (2013) explicitly predicts nonlinear responses at constraint boundaries — trees are the natural model for this.

2. **Interactions are automatic.** A tree that splits on VaR utilization at the first level and factor concentration at the second level has learned the interaction "high utilization AND high concentration → danger" without you having to manually specify it. Ridge would need you to create a `utilization × concentration` interaction term and guess the right form.

3. **Robust to feature scale and outliers.** Trees split on rank order, not magnitude. A VaR spike from 100 to 500 doesn't distort the model the way it would pull a linear regression. Financial risk data is fat-tailed — this matters.

4. **No distributional assumptions.** Ridge assumes a linear relationship with Gaussian errors. Trees assume nothing about the functional form. Given that the theory predicts specifically *nonlinear* responses (risk premia rising convexly as constraints bind), imposing linearity is a strong and potentially wrong assumption.

### Why LightGBM specifically (vs. XGBoost, CatBoost, random forest)

LightGBM is a specific implementation of gradient boosting. The choice over alternatives:

**LightGBM vs. XGBoost:** Both are GBDTs. LightGBM uses leaf-wise tree growth (grows the leaf with the highest loss reduction) vs. XGBoost's level-wise growth (grows all leaves at the same depth). In practice, LightGBM trains 5-10x faster on the same data, uses less memory, and produces comparable or slightly better results. On a dataset of ~1,250 rows this speed difference is trivial, but LightGBM is also slightly better at handling small datasets because leaf-wise growth allocates model capacity more efficiently. Either would work — LightGBM is the default in most quant ML pipelines (Gu-Kelly-Xiu used both).

**LightGBM vs. CatBoost:** CatBoost is strongest when you have many categorical features (its ordered target encoding is best-in-class). This project's features are almost entirely continuous numerical data (VaR %, Herfindahl index, z-scores). CatBoost's main advantage doesn't apply here. The one categorical feature — worst-case scenario identity — is a single column easily handled by LightGBM's native categorical support.

**LightGBM vs. Random Forest:** Random forests average many independent trees (bagging). Gradient boosting builds trees sequentially, where each tree corrects the errors of the previous ones. Boosting typically achieves higher accuracy for the same number of trees because it focuses capacity on the hardest examples. For a small dataset where every bit of signal matters, boosting is preferred. Random forests are better when you want a quick, hard-to-overfit baseline — but that's what ridge already provides in this project.

### Why not deep learning?

Deep learning (neural networks with many layers) excels on unstructured data — images, text, audio, sequences — where the model needs to learn its own feature representations. For tabular data with engineered features, deep nets typically offer no advantage and introduce several costs:

1. **Sample size.** Deep nets are data-hungry. With ~1,250 daily observations (5 years), a deep net has far more parameters than data points. Overfitting risk is extreme. LightGBM with `max_depth=4` and `n_estimators=200` has far fewer effective parameters.

2. **Interpretability.** SHAP on a tree-based model gives exact, fast, theoretically grounded feature attributions. SHAP on a neural net requires approximate methods (DeepSHAP, GradientSHAP) that are slower and less reliable. When the desk asks "why did your model predict this?", you need a crisp answer.

3. **Reproducibility and stability.** Tree models are deterministic given a random seed. Neural nets are sensitive to initialization, learning rate schedules, and batch ordering. On 1,250 rows, the same architecture can give meaningfully different results across runs — making validation unreliable.

4. **The literature says so.** Gu-Kelly-Xiu (2020) found neural nets performed well on *60 years* of equity data (~700,000 stock-months). On the time-series scale of this project, the advantage disappears. Kelly-Xiu (2023) explicitly note that the benefits of deep learning in finance scale with dataset size and feature complexity — neither is large here.

If this project succeeds and moves to production with more data (longer history, intraday frequency, many more features), deep learning becomes worth revisiting. For a 20-week research project on ~1,250 observations, LightGBM is the right tool.
