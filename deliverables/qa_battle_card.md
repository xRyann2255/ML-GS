# Pitch Presentation -- Q&A Battle Card

Organized by the real concern behind the question. Answers are written for verbal delivery -- concise, direct, no hedging.

---

## 1. "Why this project?" -- Challenging the choice

### "If this is so obvious, why hasn't someone already done it?"

Maybe someone has -- I'd love to learn about it. But "obvious" and "done" are different things. The risk team uses these outputs for risk management -- monitoring limits, sizing hedges, stress testing. That's a fundamentally different objective function from asking "do aggregated changes in these outputs predict future returns across asset classes?" Same data, completely different question. A risk manager watching VaR utilization is asking "are we within limits?" -- not "does a spike in utilization predict forced deleveraging that creates a tradeable reversal three days later?"

### "Why should an intern do this instead of a full-time strat?"

Two reasons. First, this is a research question with uncertain payoff -- exactly the kind of thing you want an intern on, not a strat whose time has a higher opportunity cost. If it works, a strat can take it to production. If it doesn't, you've lost intern time, not strat time. Second, an intern with fresh eyes and no institutional assumptions is actually well-suited to look at existing data in a new way. I'm not building a risk system -- I'm asking a question about one that already exists.

### "Why not just use the public intermediary capital ratio? He-Kelly-Manela publish theirs."

Their factor is reconstructed from quarterly Fed Z.1 data with a 3-month lag. It captures the right concept but at the wrong frequency and with the wrong sign conventions. The whole point of doing this at GS is that SecDB has the daily, correctly-signed version. If the public factor were sufficient, I'd just download it and run the project on my laptop. The edge is the data, not the methodology.

### "Isn't this just academic research on the bank's clock?"

No, because the deliverables are directly useful. If the signals work, you get a tradeable signal with capacity estimates and transaction-cost analysis. If they don't, you get documented evidence that these risk outputs don't contain cross-asset predictive content -- which is also useful to know. And the infrastructure I build (validation stack, backtester, experiment tracker) is reusable for any future signal research on this desk. Either way you get something concrete, not a paper.

### "Why not one of the other project directions -- like the factor-neutral residual strategy?"

The factor-neutral strategy (Project 4) is the safest option and has the highest probability of a presentable result. But it can largely be done with public data and gs-quant. The "why does this need to be done at GS?" question is harder to answer. Risk as alpha is differentiated specifically because it uses proprietary data that external researchers can't access. The wow factor and the data moat are both stronger. And I have the factor-neutral strategy as an implicit fallback within Project 1 -- if the risk features work, I can always add public factors as controls and confound checks.

---

## 2. "Does this actually work?" -- Signal skepticism

### "Isn't this just saying 'when VaR is high, vol is high'?"

This is the most important challenge to answer cleanly. If internal VaR just correlates with VIX, there's no proprietary information and no reason to use SecDB. I handle this through explicit confound checks: every signal that shows predictive power gets re-tested with public factors -- VIX level, credit spreads, term slope -- added as controls. If the IC drops to zero with controls, it's redundant and gets documented as a negative result. The claim is only valid for signal that survives after controlling for what everyone can already see.

Beyond that, the theory predicts specific channels that go beyond "high VaR = high vol." VaR *utilization* (usage vs. limit, not level) predicts forced selling specifically in the most-concentrated asset class. Factor-VaR *concentration* (Herfindahl) predicts crowding-driven drawdowns. These are structurally different from "vol is high."

### "VaR is calculated using volatility. If you use VaR to predict vol, isn't that circular?"

The concern is valid -- but only for some targets, and the project handles it explicitly.

VaR (likely historical simulation at GS) correlates with vol because the historical return distribution widens during high-vol periods. So using VaR to predict realized vol is partly just saying "vol is persistent" -- which is trivially true. That's the weakest target for this exact reason.

But the features I care most about aren't vol proxies:
- **VaR utilization** (usage/limit) measures how constrained the dealer is relative to their limit. Two desks can face identical vol but have very different utilization. The constraint drives forced selling, not vol itself.
- **Factor concentration** (Herfindahl) measures portfolio structure -- how diversified or concentrated the risk exposures are. Nothing to do with vol.
- **Cross-asset flow** (component VaR migration between asset classes) measures capital rotation, not volatility levels.

And the other prediction targets (drawdowns, momentum reversals) aren't inputs to the VaR calculation. VaR doesn't "know about" future drawdowns.

The confound check handles this directly: add realized vol or VIX level as a control variable on every test. If the risk features' IC drops to zero with vol controlled for, then it was just a vol proxy and I document that as a negative result. The claim is only valid for signal that survives after controlling for what vol already tells you.

### "What IC are you realistically expecting?"

Honestly, somewhere between 0.02 and 0.06 if the signal exists. Cross-asset macro signals at daily frequency are noisy. For context, Gu-Kelly-Xiu (2020) report monthly ICs of 0.03-0.05 for the best ML models on 60 years of equity data. I'd be happy with anything that's statistically significant after the Deflated Sharpe adjustment. If I'm seeing ICs above 0.10, I'd be more worried about a bug than excited about a signal.

### "What if the signal is too weak to trade?"

Then I document it honestly and pivot. A signal with IC = 0.02 that survives purged CV and DSR adjustment is a real but modest finding -- it confirms the theory works at the daily frequency but may not be economically significant after costs. That's still a publishable research result and a useful input for the desk's thinking. Not every research project produces a live trading signal, but every rigorous one produces useful knowledge.

### "What if it only works in one regime -- like crises?"

That's actually an interesting and potentially useful result, not a failure. If the signal only works when VaR utilization is high and the system is stressed, that's consistent with the theory -- He-Krishnamurthy predicts nonlinear effects specifically at constraint boundaries. A crisis-only signal has lower capacity and can't run all the time, but it could be extremely valuable as a hedge-timing overlay. I build a regime decomposition (GMM on macro features) specifically to test this.

### "How do you know the signal won't just decay once you start trading it?"

McLean-Pontiff (2016) show published signals decay 30-50% post-publication. But this signal is based on proprietary data that isn't published. The decay mechanism for public signals is that arbitrageurs see the paper and trade against it. If the signal comes from internal risk data that only GS can see, the publication-decay channel doesn't apply. That said, if the signal is just correlated with something public, it will decay. That's why the confound checks matter.

---

## 3. "Can you actually execute this?" -- Feasibility

### "You only have ~1,250 daily observations. Isn't that too few for ML?"

It's tight. Bailey-Borwein-Lopez de Prado (2014) show that with 5 years of data, ~45 independent trials exhaust a Sharpe of 1.0. That's exactly why I track every experiment and apply the Deflated Sharpe Ratio -- it penalizes for the number of things tried. I also mitigate the sample size problem in three ways: (1) panel structure across multiple asset classes multiplies effective sample size, (2) theory-motivated features mean fewer features to test, not a data-mining exercise, and (3) the ridge baseline works well with small samples since it's heavily regularized.

### "Have you thought about VaR methodology changes over the lookback period?"

Yes. If the risk system switched from historical simulation to Monte Carlo, or changed the confidence level or lookback window during my sample period, that's a structural break in the features. It could create spurious signals or mask real ones. One of my first steps in the data audit is to interview the risk team about any methodology changes and document the dates. If there are breaks, I can either split the sample or include them as a control variable. Ignoring this would be a serious mistake.

### "What if you can't get the data at all?"

Then I calculate my own risk metrics from whatever position and market data I can access. Historical VaR from returns, my own factor decompositions, my own concentration metrics. It's a weaker version of the project -- my VaR won't match the desk's VaR, I can't compute real utilization without the limits, and I'll be testing the theory with a self-built proxy rather than the real measurement. But the methodology and the question stay the same. If the self-calculated version shows something, that's actually a strong argument for revisiting access later.

### "What Python packages do you need? Are they available internally?"

Core stack: LightGBM, scikit-learn, pandas, numpy, shap, matplotlib. These are standard and likely available. I also want mlfinlab (for triple-barrier labels and purged CV implementations), alphalens, and pyfolio. If any of these are blocked, I can implement the key algorithms myself from the academic papers -- triple-barrier labeling is ~50 lines, purged CV is ~100 lines. I'll audit package availability in the first week before building anything.

### "What happens if you fall behind schedule?"

The plan has built-in buffer. The signal testing phase (weeks 6-12) is 7 weeks for what could be done in 4-5 if the data is clean. If infrastructure takes longer, signal testing compresses. If signal testing takes longer, the Phase 4 deepening (regime overlay, cross-asset panel) is the first thing to cut -- it's additive, not essential. The minimum viable deliverable is: tested the priority signal families, documented results, applied rigorous validation. Everything after that is depth.

---

## 4. "Why ML specifically?" -- Methodology

### "Why not just run a regression?"

I do. Ridge regression is the mandatory baseline on every single test. It's the first model fitted on every feature set, and it appears alongside LightGBM on every chart. ML is only justified if it beats it.

The case for GBM over ridge is specifically about threshold effects and interactions. He-Krishnamurthy (2013) predicts risk premia rise nonlinearly when constraints bind. VaR utilization at 60% might mean nothing, but at 90% it could trigger forced deleveraging. That's a threshold a tree captures natively but a linear model can't. If ridge wins, I report that honestly -- it means the signal is linear, which is still a finding.

### "Why not deep learning?"

Three reasons: sample size, interpretability, and the literature. With ~1,250 observations, a neural net has more parameters than data points -- overfitting risk is extreme. SHAP on trees gives exact, fast feature attYributions; on neural nets it's approximate and unreliable. And Gu-Kelly-Xiu (2020) found neural nets only dominate with 60+ years of data and hundreds of thousands of observations. At this scale, trees win.

### "What if the ridge baseline beats LightGBM on everything?"

That's a valid and publishable result. It would mean: (a) the signal exists, (b) the relationship is linear, and (c) you don't need ML for it. Kozak-Nagel-Santosh (2020 JFE) showed exactly this on equity characteristics -- ridge-shrunk SDFs matched nonlinear ML. I'd report it honestly, document the features that drive the linear signal, and still have a useful predictive model. "Your risk outputs predict drawdowns with a linear model" is a perfectly good finding for the desk.

### "How do you handle feature selection with so few observations?"

I don't do unconstrained feature search. Every feature is theory-motivated -- I'm not scanning hundreds of random transformations looking for patterns. There are five feature families, each with 3-5 derived features, for maybe 15-25 total features. With theory-driven feature construction, the multiple-testing burden is manageable. And the Deflated Sharpe Ratio explicitly penalizes for the number of experiments run, so I can't hide the search even from myself.

---

## 5. "So what?" -- Practical trading concerns

### "What's the capacity?"

Depends on what the signal predicts. If it predicts index-level moves (VIX innovations, broad drawdowns), capacity is large -- you'd trade liquid futures, and the constraint is Sharpe degradation at size, not market impact. If it predicts single-name moves, capacity is smaller. I build an explicit capacity analysis: run the model at varying cost levels (0, 2, 5, 10, 20, 50 bps), find the breakeven cost, and estimate capital absorption. The Sharpe-vs-cost curve is one of my final deliverable charts. A signal with Sharpe 1.5 but $5M capacity is interesting research. A signal with Sharpe 0.6 but $500M capacity is a strategy. I'll be honest about which category the result falls into.

### "What's the turnover? Is this flipping positions daily?"

That depends on the prediction horizon and the signal's persistence. I test multiple horizons (1-day, 5-day, 21-day targets). A daily VIX innovation predictor will have high turnover; a 21-day realized vol predictor will have lower turnover. Transaction costs are baked into every backtest from the start, so high-turnover signals that get eaten by costs will show it immediately in the net Sharpe. If turnover is above ~50% daily, the signal is likely impractical regardless of gross performance.

### "What instruments would you actually trade?"

For VIX innovations: VIX futures, SPX variance swaps, SPX straddles. For asset-class drawdowns: futures in the relevant asset class (rates futures, equity index futures, FX majors). For momentum reversals: the same cross-asset momentum portfolios the literature studies (Asness-Moskowitz-Pedersen 2013). For realized vol: delta-hedged options, variance swaps. All liquid, all instruments the desk already has access to.

### "What happens in a crisis? Does the signal work when you need it most?"

The regime decomposition is specifically designed to answer this. I fit a GMM on macro features to identify crisis vs. steady-state regimes, then decompose signal performance by regime. If the signal only works in calm markets and fails in crises, that's important to know and I'll report it. If it works specifically in stressed markets (which the theory would predict -- constraints bind more when VaR utilization is high), that's extremely valuable as a hedge-timing tool.

### "Is this a standalone strategy or a signal overlay?"

Initially, I'm evaluating it as a standalone signal -- that's the cleanest way to measure whether the information content exists. But the practical use case is almost certainly as an overlay. If factor concentration is spiking in rates, you don't necessarily put on a new trade -- you might reduce an existing rates position or add a hedge. The signal tells you when risk is elevated in a specific asset class; how you act on it depends on what positions you already have. Risk management overlay is the natural use case.

### "How is this different from what the strats team already does?"

The strats team builds and maintains the risk models. They produce the VaR numbers, calibrate scenarios, design factor decompositions. This project doesn't touch any of that. It asks a second-order question: do the aggregated outputs of those models, viewed as a time series, contain cross-asset predictive information? The strats optimize within the risk framework. This project looks at the framework's outputs from outside and asks whether they predict things the intermediary asset pricing literature says they should.

---

## 6. Data access and compliance

### "What if the data reveals something about our positioning to competitors?"

It won't. The raw data never leaves the sandboxed environment. Every deliverable shows derived statistics -- information coefficients, Sharpe ratios, SHAP importance rankings. Not dollar amounts, not VaR levels, not position sizes. The research report says "factor concentration predicts drawdowns" -- it doesn't say "firm VaR was $2 billion on March 15th." I can structure the workflow so that nothing identifiable appears in any output.

### "Who else would see this work?"

That's your call. I assume this is internal-only unless you say otherwise. If there's any possibility of broader distribution (cross-desk, leadership, external), I'll initiate a compliance review by week 16-17 to make sure the final output is clean. I'd rather start that process early than have it block the week 20 deliverable.

### "Can you present results externally?"

Only with compliance approval and your sign-off. I'm not planning to publish or present externally. If the results are interesting enough that someone wants to, that's a future conversation with the appropriate approvals. Nothing I produce will be in a format that requires external disclosure.

### "What if you discover something material -- like the risk system has a bias?"

If I find something that looks like a risk model artifact rather than a real signal -- for example, a systematic bias in how the VaR methodology estimates tail risk -- I'd flag it to you and the risk team immediately. That's a different kind of valuable finding. The confound checks and the VaR methodology audit are designed to separate real signals from model artifacts.

---

## 7. Project management

### "How much of my time does this take?"

Minimal. I'm asking for a 30-minute check-in every 2-3 weeks, plus the Week 13 checkpoint meeting and a dry-run of the final presentation. Maybe 3-4 hours total over 20 weeks. I'll send a short written update by email between check-ins so you're never surprised.

### "Who's your backup if you're unavailable?"

I'd like to identify a backup reviewer during the first two weeks -- someone who can answer questions and review intermediate results if you're traveling or busy. Ideally someone on the desk who's familiar with the risk systems. I don't need them often, just for occasional ad hoc questions about data interpretation.

### "What happens after the internship? Who maintains this?"

The code is modular, tested, and documented. The research report stands on its own. If the signals work, a strat can take the validated model and integrate it into whatever production workflow makes sense. If they don't, the infrastructure (validation stack, backtester) is still reusable. I'm not building something that only works if I'm here.

### "What does the Week 13 checkpoint look like?"

A 1-2 page memo plus a short meeting. The memo documents: what was tested, what worked (IC, Sharpe, DSR-adjusted Sharpe for each signal family), what didn't, and my recommendation -- continue deepening Project 1, pivot to Book-Gamma, or a hybrid. I present the evidence and you decide. It's a data-driven decision, not a judgment call.

---

## 8. Deeper technical questions

### "VaR is a lagging indicator. By the time it spikes, the move has already happened. How do you predict with a lagging input?"

Good question, and it's partly why I test rates of change and z-scores, not just levels. The level of VaR might lag, but the *rate of change* -- utilization jumping from 70% to 85% in two days -- can lead the forced-selling event that happens when it hits the limit. Adrian-Shin (2010) found that the change in dealer risk exposure, not the level, forecasts VIX innovations. I'm testing dynamics, not snapshots.

Also, the point-in-time stamping explicitly accounts for the lag. If VaR for day T is computed in the overnight risk run and available on T+1 morning, I don't use it to predict T -- I use it to predict T+1 and beyond. The lag is built into the feature engineering.

### "How do you handle the fact that VaR limits themselves change?"

If I have access to utilization (usage/limit), and the limit changes, that's a feature, not a bug. A limit increase could mean the desk is being given more room to take risk -- that's a signal about risk appetite. A limit decrease could mean risk is being pulled. If I don't have access to limits and am computing my own utilization proxy, I can't capture this. That's one reason real utilization data is so valuable.

### "What if the signal is just picking up on the VaR model's own assumptions -- artifacts, not reality?"

This is why the VaR methodology audit matters. If the VaR model switched from historical simulation to Monte Carlo midway through my sample, I'd see a structural break in the features that has nothing to do with markets. I interview the risk team about methodology changes, document the dates, and either split the sample or control for it. I also test whether the signal persists across different sub-periods -- if it only exists in one regime or one time window, that's a red flag for artifacts.

### "What about correlation between your features? Factor concentration and VaR utilization probably move together."

Yes, and that's expected. I test each feature family independently first, then combine. If two families are highly correlated (say, correlation > 0.8), the combined model's SHAP analysis will show which one is actually carrying the signal. Multicollinearity doesn't bias tree predictions the way it biases regression coefficients -- LightGBM handles correlated features naturally by splitting on whichever is more informative at each node. But I'll check and report the correlation structure.

### "How do you distinguish between predicting returns and predicting volatility? Those are very different claims."

They are, and I treat them as separate targets with separate evaluations. Predicting realized volatility is a lower bar -- vol is more persistent and forecastable than returns. If the risk features predict vol but not returns, that's still useful (you can trade vol surfaces, variance swaps) but it's a weaker claim than return prediction. I won't conflate the two in the results. Each target gets its own IC, Sharpe, and DSR.

### "What's your view on the Asness et al. (2017) 'Contrarian Factor Timing' critique?"

I take it seriously. They showed that factor timing net of existing factor exposures usually subtracts value. If my signal is just a noisy version of "go long value when it's cheap," it adds nothing after accounting for existing exposures. The confound checks address this: I add standard factor exposures as controls and test whether the risk-system signal contributes marginal predictive power. If it doesn't survive controls, I document that honestly. A regime-conditional signal (works in crises, not in calm markets) faces this critique most directly.

### "What about survivorship bias in the risk data?"

Risk cubes cover the current book. If instruments were removed from the book (unwound, matured, defaulted), their historical VaR contribution may not be in the current data. This is less of a problem for firm-level aggregates (total VaR is what it was on that date regardless of what instruments composed it) but could matter for component VaR by asset class if the asset class mix has changed substantially. I'll check the stability of the asset class composition over the sample period and flag any large structural changes.

---

## 9. Curveball questions

### "What would make you abandon this project before Week 13?"

If the data audit reveals that the accessible risk outputs have less than 2 years of history, the sample size is too small for any meaningful ML test. I'd flag this immediately and pivot to the Book-Gamma direction or the factor-neutral strategy, both of which can work with different data sources. The Week 13 checkpoint is for "signal didn't work." A data availability problem should surface in Week 1-2 and trigger an immediate conversation.

### "Have you considered that we might not want to know this?"

I understand the concern. If risk outputs predict returns, it could complicate how the risk system is used -- people might start gaming VaR to capture the signal rather than using it for risk management. That's a valid concern, and it's above my pay grade. What I can say is: knowing whether this relationship exists is better than not knowing, even if the decision is to not trade it. And the deliverable is a research report, not a live trading system. What to do with the finding is a decision for the desk.

### "Why should I trust your ML skills?"

I'd point to the methodology, not to credentials. The validation framework I described -- purged CV, Deflated Sharpe, ridge baseline, point-in-time discipline -- is exactly what Lopez de Prado, Harvey-Liu, and the top quant shops recommend. I'm not inventing a new method; I'm applying the established standard rigorously. If the results are wrong, the validation stack will catch it. That's the point of building it first.

### "What's one thing that could go wrong that you haven't mentioned?"

The biggest risk I haven't stressed enough is non-stationarity. Financial relationships change over time. A signal that worked from 2020-2024 might not work in 2025-2026. The rolling-window stability check in Phase 5 tests for this explicitly, but if the relationship is truly non-stationary, even a good model will degrade. That's partly why the regime overlay exists -- if the signal only works in certain macro environments, I want to know that upfront rather than discovering it in live trading.

### "This sounds like a lot of infrastructure for a 20-week project. Are you going to spend 15 weeks building tools and 5 weeks on results?"

The infrastructure is 3 weeks (Weeks 3-5), not 15. And most of it is the validation stack, which is what separates a credible result from a homework assignment. The signal testing runs from Week 6-12 -- that's 7 weeks of actual experimentation. I'm spending 25% on infrastructure and 75% on research. If anything, most projects spend too little time on validation and end up with results they can't trust.

---

## 10. "What is X?" -- Definitions for every technical term in the slides

These are one-breath answers. If he asks, give the short version. Only elaborate if he asks a follow-up.

### "What is LightGBM?"

It's a machine learning algorithm that builds a sequence of small decision trees, where each tree corrects the mistakes of the previous one. Think of it like this: the first tree makes a rough prediction, the second tree focuses on where the first tree was wrong, the third tree focuses on where the first two were still wrong, and so on. After a few hundred of these, you have a strong predictor. It's called "gradient boosted" because each tree follows the gradient of the error. LightGBM is a specific implementation by Microsoft that's fast and handles small datasets well. It's the standard tool in quantitative finance for this type of structured data -- Gu, Kelly, and Xiu used it in their canonical 2020 paper.

### "What is ridge regression?"

Linear regression with a penalty that shrinks the coefficients toward zero. Regular regression can overfit badly when you have many features relative to observations -- it'll chase noise. Ridge adds a penalty proportional to the sum of squared coefficients, which forces the model to keep coefficients small and spread out across features rather than loading heavily on any single one. It's the simplest reasonable model for this type of problem, which is why I use it as the baseline. If a complex ML model can't beat a penalized linear regression on the same features, the complexity isn't earning its keep.

### "What is SHAP?"

It stands for SHapley Additive exPlanations. It's a method for explaining why a model made a specific prediction. For each prediction, SHAP gives every input feature a score: how much did this feature push the prediction up or down? The math comes from cooperative game theory -- Shapley values from the 1950s. In practice, it means I can say "the model predicted a VIX spike because VaR utilization was at 92% and factor concentration was elevated" rather than just "the model said so." It turns the model from a black box into something you can interrogate.

### "What is an Information Coefficient -- IC?"

It's the Spearman rank correlation between what the model predicted and what actually happened. If the model says "observation A will have a higher return than observation B" and it's right, the IC goes up. An IC of 1.0 means perfect foresight. An IC of 0.0 means the model is no better than random. In macro cross-asset signals at daily frequency, a realistic IC is 0.02 to 0.06 -- small, but potentially tradeable at scale. For context, even the best equity factor models rarely sustain ICs above 0.05.

### "What is the Deflated Sharpe Ratio?"

It adjusts a reported Sharpe ratio for how many things you tried before finding it. If you test one strategy and get a Sharpe of 1.5, that's impressive. If you tested 200 strategies and the best one had a Sharpe of 1.5, that's probably luck -- the more things you try, the more likely you are to find something that looks good by chance. The Deflated Sharpe Ratio, from Bailey and Lopez de Prado (2014), corrects for this. It also accounts for non-normality and sample length. It's the single most important guard against fooling yourself. On 5 years of daily data, about 45 independent trials are enough to exhaust a Sharpe of 1.0 purely by chance.

### "What is purged K-fold cross-validation with embargo?"

Standard cross-validation splits data into chunks, trains on some chunks, and tests on others. But with time-series data, that's dangerous: if your training data includes observations from March and your test data includes April, autocorrelation means the model has effectively seen the future. "Purged" means I remove any training observations that are close enough in time to the test set that they could leak information. "Embargo" means I add an extra buffer gap between training and test periods. This comes from Lopez de Prado's work. It's the right way to validate time-series models, as opposed to standard cross-validation which gives you falsely optimistic results on financial data.

### "What is a Herfindahl index?"

It's a concentration measure. You take the percentage share of each component, square them, and sum the squares. If risk is spread equally across 10 factors, the Herfindahl is 0.10 (low concentration). If 90% of risk is in one factor, it's around 0.81 (high concentration). It's the same index used to measure market concentration in antitrust -- the HHI. Here I apply it to factor-VaR shares to measure how concentrated or diversified the risk exposures are.

### "What is point-in-time stamping?"

It means every data point is tagged with when it was actually known and available, not when it applied. VaR for Monday is computed in the overnight risk run Monday night and available Tuesday morning. If I use Monday's VaR to predict Monday's return, that's cheating -- I couldn't have known Monday's VaR until Tuesday. Point-in-time stamping prevents this by enforcing that features only use information that was genuinely available at the time of the prediction. It's the most common source of inflated backtests in finance: people accidentally use data they couldn't have had.

### "What is gradient boosting?"

It's the general technique behind LightGBM. You build an ensemble of weak models (usually small decision trees) sequentially, where each new model specifically targets the errors the existing ensemble is still making. "Gradient" refers to how it identifies those errors -- it follows the gradient of the loss function, similar to how gradient descent works in other optimization problems. The final prediction is the sum of all the individual trees' predictions. It's currently the dominant method for structured numerical data in both industry and academic benchmarks.

### "What are VIX innovations?"

"Innovations" is the econometrics term for the unexpected component of a time series. VIX tomorrow = what you'd expect based on today's VIX + the unexpected change. The unexpected change is the innovation. I remove the predictable part (autocorrelation) and try to predict the residual. This is a cleaner target than predicting the VIX level, because VIX level is largely just "VIX yesterday plus a small change." The innovation is what's actually new information.

### "What is a GMM / Gaussian Mixture Model?"

It's a statistical method for identifying distinct regimes or clusters in data without labeling them in advance. You tell it "find 3-4 groups" and it identifies them from the data itself. I'd fit it on macro variables -- VIX level, yield curve slope, credit spreads -- and it would identify something like "calm markets, rising rates, stress/crisis, recovery." Then I can ask whether my signal works differently across these regimes. It's unsupervised, meaning I don't tell it what the regimes are -- it discovers them.

### "What is a panel structure?"

Instead of running one time-series regression, I stack multiple asset classes together -- rates, equities, credit, FX, commodities -- each with its own features and targets, and estimate a single model across all of them. This multiplies the effective sample size (instead of 1,250 daily observations, I might have 5 x 1,250 = 6,250 panel observations) and lets me test whether the same signal works across asset classes. Asset-class fixed effects control for level differences. It's the natural structure for testing a cross-asset theory.

### "What is walk-forward / out-of-sample testing?"

It's the final test of whether the model actually works. I reserve a chunk of recent data (the holdout) that the model has never seen during training or validation. No tuning, no peeking, no second chances. I run the model once on this holdout and whatever comes out is the honest result. Walk-forward means I do this in a rolling window, like: train on years 1-3, predict year 4. Then train on years 2-4, predict year 5. This simulates how the model would have performed if you'd actually been trading it.

### "What is a breakeven cost level?"

It's the transaction cost at which the strategy's Sharpe ratio hits zero. If the breakeven is 2 bps, you need extremely cheap execution. If it's 50 bps, the signal is robust enough to survive realistic trading costs. I run the backtest at multiple cost levels (0, 2, 5, 10, 20, 50 bps) and plot the Sharpe against cost. Where the curve crosses zero is the breakeven. It tells you how much execution friction the signal can absorb before it stops being worth trading.

### "What is a pricing kernel / SDF?"

You'd probably explain this better than I could, but in the context of these papers: a stochastic discount factor (SDF) is a single object that prices all assets simultaneously. He-Kelly-Manela (2017) showed that a single SDF based on intermediary leverage can price equities, options, CDS, bonds, FX, and commodities. That's the result that makes this a cross-asset project rather than an equities-only project -- one set of dealer constraints, one pricing mechanism, across all asset classes.

### "What is CPCV -- Combinatorially Purged Cross-Validation?"

It's an extension of purged CV from Lopez de Prado. Regular purged CV gives you one Sharpe ratio per fold. CPCV runs all possible train-test combinations and gives you a distribution of Sharpes. So instead of reporting "Sharpe = 1.2" you can say "median Sharpe across all combinations = 0.9 with a range of 0.4 to 1.5." It gives you a confidence interval rather than a point estimate. More conservative, more honest.

### "What is the Haircut Sharpe Ratio?"

From Harvey and Liu (2015). It's a multiple-testing correction applied to Sharpe ratios. Given that more than 300 factors have been tested in the published finance literature, the statistical bar for a new factor should be much higher than the traditional t > 2 threshold. Harvey-Liu estimate the hurdle is closer to t > 3. The Haircut Sharpe adjusts your reported Sharpe downward based on how many factors have been tested in the literature, using either Bonferroni or BHY false discovery rate correction. It's a stricter bar than the Deflated Sharpe, which only counts your own experiments.

### "What is feature importance / MDA?"

Mean Decrease Accuracy. For each feature, you randomly shuffle its values and see how much the model's accuracy drops. If shuffling VaR utilization causes a big drop in accuracy, it was important. If shuffling scenario P&L causes no drop, it wasn't contributing. I check this across all cross-validation folds: if a feature is important in fold 1 but irrelevant in fold 2 and flips sign in fold 3, it's unstable and I don't trust it. Stable importance across folds is a sign of a real signal.

---

## 11. If they say "no" to data access

### The graceful pivot

"I completely understand. Let me lay out what I can do with self-calculated risk metrics and come back in 2-3 weeks with preliminary results. If there's anything interesting, we can revisit the data access question with evidence rather than theory."

### What to calculate yourself

- Historical VaR from portfolio returns (parametric or historical simulation)
- Component VaR by asset class from position-level data if available
- Factor concentration from whatever factor decomposition you can build (PCA on returns, or using publicly available factor models)
- Rolling risk statistics (vol, correlation, drawdown) as proxies for scenario P&L
- You lose: real utilization (no limits), real scenario P&L (no standard shocks), and the correct dealer sign

### The silver lining argument

If self-calculated risk metrics show predictive power, that's actually a stronger pitch for real data access: "The crude version shows IC = 0.03. The real data should be even better. Can we try it?"
