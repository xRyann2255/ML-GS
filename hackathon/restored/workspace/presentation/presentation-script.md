# Presentation Script: Timing the Variance Seller

~23 minutes plus open Q&A, for the trading desk (traders and quants).
Deck: `workspace/presentation/presentation.html` (11 slides, self-contained). Q&A backstop: `qa-comprehensive.md`.

## Regeneration

```bash
# GS (real dashboard):
./vol present --dashboard-path '../../src/data/models/trial_036_drop_vrp_calendar/plots/tournament_dashboard.html'
# Local (mock dashboard):
cd ml-vol-estimator && ./vol shell ../../workspace/presentation/generate.py --dashboard-path tournament_dashboard_mock.html
```

## Before presenting (GS verification)

- Reconcile the stand-aside counts: the "33%" flat share, the ~120 transitions/year, and the max drawdown improvement must be consistent with the dashboard's xgb_hariv0dte_init [long_flat] row for h=1.
- Re-verify every number in the deck's NUMBERS dict (generate.py) against the live tournament dashboard; numbers were sourced from trial_067_xgboost_all_layers.
- Confirm the four dashboard tab names used in the cues (GSVIVS, Rankings, SHAP beeswarm, ALE) match the real dashboard's labels.
- Iframe focus: once you click inside the dashboard iframe, keyboard focus stays there and the deck's D and arrow keys stop responding. The on-screen Dashboard [D] button is the way back to the slides.
- Confirm the build printed `slide 2 chart: real dashboard data` (not `synthetic fallback`), and that the slide-2 endpoints and year span match the dashboard's GSVIVS tab ([baseline] always_long, h=1). A silent fallback means the dashboard template renamed `gsvivsPnlTraces`. If the real endpoints differ from the script's spoken numbers (100 to 138, 10.1 points a year, fifteen worst days), update Section 1's spoken text and the beat-sheet row 1-2 cells to match.

## Section 1: The product and its problem (slides 1 to 2, ~2.5 min)

> [SLIDE 1: Timing the Variance Seller]

Hi everyone. Just to introduce myself again, I'm an off-cycle intern and I have been working on an ML project to forecast realized vol for SPX. I'll first talk about an STS strategy that my realized vol predictions are directly applicable to.

GSVIVS01 is about the simplest short volatility product we run: every morning it sells the day, and every afternoon it finds out what the day cost.

Short variance pays a small premium on most days and hands you the tail on the worst ones. For the next twenty minutes I'm going to try to tell those days apart.

> [SLIDE 2: GSVIVS01 sells variance every single day]

Here's one day in the life of the index. At 09:30 it sells a strip of same-day SPX options that replicates a variance swap, hedges the delta through the session, and settles at the 16:00 close. Next morning it does the same thing again. Every day, same size, no view. Nothing carries overnight, each day stands on its own, and there's no timing anywhere in the product. That's what makes it simple, and it's also what makes it vulnerable.

Now the equity curve, and this is the actual index series, pulled from the same dashboard I'll show you in a minute, not a sketch. The index goes from 100 to 138 over four years. That's roughly 10.1 points a year, collected a few basis points at a time.

Look how smooth that line is. That smoothness isn't free; it's bought with the left tail.

The red ticks are real dates: the fifteen worst days in the window. Each one is a morning where the index sold a strike, and by the close realized variance had beaten it. And they aren't bad luck sprinkled at random: they're the mornings it should have stood aside, and it sold anyway.

A handful of mornings a year do most of the damage. And the index walks into every one of them, because it has nothing that tells one morning from another.

So the question this project answers is simple. Can we tell, before nine thirty, which mornings are the wrong mornings to sell?

## Section 2: The claim (slide 3, dashboard moment 1, ~1.5 min)

> [SLIDE 3: Every morning: compare the forecast to the strike]

Here's the decision we add. It happens at 09:10, twenty minutes before the strip goes out.

Overnight, the model produces a forecast of today's realized variance. The strike on offer is already pinned down by the previous close. At 09:10 we put the two numbers side by side. There's no look-ahead in either number. The forecast uses only what is known overnight, and the strike is last night's print.

If variance is rich, meaning the strike sits comfortably above the forecast, the index sells as usual. If the forecast comes in above the strike, we stand aside for the day. That is the entire rule. Short or flat, nothing in between, no sizing cleverness. A binary rule is easy to audit, and easy to overrule if the desk knows something the model doesn't.

The strike itself deserves thirty seconds. Kvar is the same out-of-the-money option integral the VIX is built on: puts below the forward, calls above, each weighted by one over strike squared. Because it integrates the whole wing, it inherits the skew. So the strike always sits above at-the-money implied vol.

That matters for honesty. If I benchmarked the forecast against ATM IV, the signal would look better than it is. We benchmark against the strike the index actually sells.

Now the headline. Layer that one rule onto the index, and the backtest goes from an annualized Sharpe of 2.09 as-is to 2.45 with the signal, measured May 2022 to June 2026.

> [DASHBOARD: GSVIVS tab, Sharpe column, then the stand-aside precision]

I'd rather show you than tell you, so here's the dashboard. Every backtest number you hear today comes off this screen, not off a slide. This is the GSVIVS tab, and the Sharpe column is the number I just quoted: 2.09 without the signal, 2.45 with it, same window.

The figure I trust even more sits next to it: max drawdown. The signal isn't twitchy. It stands aside on about 33% of days over this window, and cuts the worst peak-to-trough loss by 41%, from 5.1% to 3.0%.

That is the claim. The rest of the talk is me earning it.

## Section 3: The model (slides 4 to 6, ~5.5 min)

> [SLIDE 4: A linear spine and a tree overlay]

The model is two layers, and the first layer you already know.

The spine is HAR-IV: a four-parameter regression on today's realized variance, last week's average, last month's average, and implied vol. That model is a desk classic. It's been the benchmark in the vol-forecasting literature for years, and nothing about it is a black box. You can read its coefficients over coffee. On its own, it carries most of the forecast.

The second layer is LightGBM, a gradient-boosted tree ensemble. Why trees at all? Because vol responses are nonlinear and full of interactions. The same IV level means different things in different regimes, and trees capture that without me hand-writing every interaction.

But the design choice that matters is what the trees are allowed to learn. They don't start from zero. They start from the spine's prediction, passed in as the init score, and from there they learn only the residual: the part of the target the linear model leaves on the table.

That buys us a floor. If the trees find nothing, we're left holding the desk classic. Anything they do find is pure addition. And it keeps the machine learning honest, because the trees never have to re-learn what the spine already knows.

The whole stack trains end to end on the same loss we grade it on, so there's no training on one metric and reporting another.

One feature of this slide earned its own box: tenor matching. Each forecast horizon reads the implied vol that expires with it. The one-day forecast reads same-day IV. The five-day forecast reads one-week IV, and the twenty-two-day reads one-month.

That sounds obvious, and the early version still got it wrong. Feed one-week IV into a one-day forecast and you smuggle in four days of term premium that have nothing to do with today. Fixing that was one of the cleanest gains in the whole project.

> [SLIDE 5: Four things the market tells you]

So what do the trees actually see? Four families of inputs, and each one fits in a sentence.

Price history: how volatile we have actually been, with up-moves, down-moves and jumps counted separately, because down-vol and jump risk carry different information.

The options surface: what the market is paying for future vol right now, term slope, skew, vol of vol. That family is the market's own forecast, and the model treats it as testimony, not truth.

Measurement quality: how much of today's variance reading is signal and how much is microstructure noise, from noise-robust estimators and unusual tick counts.

And the calendar: what's scheduled, Fed meetings, payrolls, option expiries.

Count those up, then let every series also contribute its daily change and a z-score against its own recent history. You land at about 128 inputs.

Notice what's not on the list. No alternative data, no sentiment scraping, nothing exotic. It's the information this desk already watches, every day, on its own screens. The model's contribution is the weighting, not the ingredients.

Those are the ingredients. One more minute on how they're actually built, because the build is where the edge hides.

> [SLIDE 6: Layers 0, 1, 2: split the jumps from the flow]

The features come in numbered layers, and the first three do most of the work.

Layer zero is the HAR core: realized variance at daily, weekly and monthly lags, plus realized quarticity, which is the error bar on today's reading. The same information the spine uses; the trees see it too.

Layer one is the one I want you to remember, and it's the diagram on this slide. Each day's variance gets split two ways. First, how it arrived: continuous variation, estimated by bipower variation, versus jump variation, and a day only counts as a jump day when a formal statistical test says so, not when a threshold feels exceeded. Second, which direction: down-move semivariance versus up-move, with the signed jump as the difference.

Why bother? Because continuous vol mean-reverts and forecasts well, and jumps don't. Mash them into one number and the jumps poison the persistence estimate. Separate them, and each part gets priced for what it is. Down-vol and signed jumps also carry the leverage effect everyone here already trades on.

Layer two is the options surface read as features: term slope, skew, vol of vol, the variance risk premium. Layers three to five add microstructure, cross-asset spillovers and the calendar, and most of those families you met on the last slide.

That is the model. Here is why you should believe the numbers it produces.

## Section 4: Why trust the number (slide 7, dashboard moment 2, ~4.5 min)

> [SLIDE 7: Walk-forward with a moat, five seeds]

Every number in this talk is out of sample. I want to spend real time on what that means here, because with overlapping time series it's easy to claim out of sample and still leak. When a machine-learning result on financial data is wrong, this is usually where it went wrong. So this is the slide I most want to be boring.

The protocol is an expanding walk-forward. Train on everything up to a date, test on the block that follows, extend the window, repeat. There is no random shuffling anywhere; time-series data gets time-series splits. Each test block sits strictly in the model's future. By the time we're done, the whole backtest window has been predicted by models that never saw it.

Now the moat, the hatched gap on this diagram. Training always stops ten trading days before each test block, and resumes ten trading days after it. Purged, on every fold.

Why? Because the target itself overlaps days. A five-day realized variance measured on Monday shares four sessions with one measured on Tuesday. Let training run right up to the boundary, and the last training labels contain pieces of the first test answers. The model would be graded on questions it partly saw. The purge removes that channel completely. That gap is the first guard.

Second guard: the panel. We pool 21 symbols into one training panel, and splits are by date across all 21 at once. When a date is in test, it's in test for every name. So one symbol can never hand tomorrow's market to another.

Third guard, and this is the paranoid one: early stopping. The routine internal check that decides when the trees stop growing runs on its own validation slice, and that slice sits behind its own purge gap. Even the model's housekeeping never peeks across the boundary.

Now the scoreboard, because the metric matters as much as the protocol. We judge every forecast on QLIKE. Here it is in one line: a proportional loss, calm markets count as much as crises, underprediction hurts more than overprediction, and its rankings hold up even though measured RV is itself a noisy proxy. That asymmetry is exactly right for a variance seller. The forecast that says calm before a storm is the expensive one.

Last guard: seeds. LightGBM is stochastic. Change the random seed and you grow a different forest. We ran five seeds on the final configuration, and one lucky seed looked 6% better than the truth, where the truth is the five-seed mean. If I'd shown you that seed, you'd have believed a number that doesn't exist. So the rule is fixed. Every headline number today is a five-seed mean, never a best seed.

> [DASHBOARD: Rankings tab, QLIKE column, OOS window in the header]

Here is where those rules land. This is the Rankings tab, one row per model. The QLIKE column is the scoreboard, lower is better, and the raw levels live here rather than on the slides. The out-of-sample window is printed right in the header, so you can see exactly which period is being graded.

Two of these columns get one sentence each. DM is Diebold-Mariano, a paired test that the gap is real. MCS is the model confidence set, the set of models you can't statistically tell from the best. Both have full write-ups in the Q&A pack if you want to go deeper.

So the protocol is airtight. The next question is what the model actually learned.

## Section 5: What it learned (slide 8, dashboard moments 3 and 4, ~4 min)

> [SLIDE 8: Everything it learned has a name you know]

If the trees beat the spine, I want to know what they know. Two sentences on the tool. SHAP splits every individual forecast into named feature contributions that sum exactly to the prediction. We use it to audit what the trees add on top of the linear spine, day by day, feature by feature.

Twenty seconds on how to read the chart, using the guide on this slide. Each row is a feature, and each dot is one trading day. Rows are ranked by how much they move the forecast, so height on the page is importance. Dots to the right of the line pushed that day's forecast up. Dots to the left pushed it down. Color is the feature's own value, blue for low, red for high. So a clean feature reads like the top row: red dots on the right, blue on the left, high values push vol up.

> [DASHBOARD: SHAP beeswarm, h=1]

Now the real thing: the beeswarm for the one-day model. Let me take the top five features. Every one of them is a story you already trade.

First, and at the top of the list: the relationship between implied and realized, and how it shifts with regime. In calm tape, implied runs rich to realized, and the model discounts it. In stress the gap closes, and the model listens harder. That re-weighting by regime is what a vol trader does by instinct. The trees learned it from data.

Second: extremes of the variance risk premium, the spread between what options charge for variance and what variance actually delivers. When that premium is stretched far beyond its usual range, in either direction, snap-back becomes forecastable, and the model leans into it.

Third: Fed proximity. Vol has a schedule around FOMC, compression into the meeting and release after it, and the model prices that calendar the same way the desk does.

Fourth and fifth: the z-score flags. When a series runs unusually hot against its own recent history, the model reads it as stretched and expects mean reversion, not continuation.

Nothing on that list should surprise anyone in this room, and that's the point. The edge comes from pricing familiar effects with discipline, not from a mystery factor. If the top of the list were something nobody here could name, I'd trust this model less, not more.

One more view, because SHAP tells you what mattered, not the shape of the response.

> [DASHBOARD: ALE, h=1, same-day IV]

This is an ALE curve: the model's average response to a single input, with everything else held honest. This one is same-day implied vol against the one-day forecast.

The curve rises monotonically. No kinks, no nonsense, exactly what you'd demand of an IV response. And the slope steepens in the tail. Read that plainly: when IV is screaming, the model leans on it hardest. The information content is highest right when it matters, and the tail is where the stand-aside call gets made.

Which brings us to the honest scorecard.

## Section 6: Where it wins (slide 9, ~2.5 min)

> [SLIDE 9: Where it wins, and where it honestly doesn't]

Three horizons, three results. The bars are forecast-loss reductions, so taller is better, and one of them points the wrong way. I'll get to it. Everything on this slide is the same protocol you just audited: walk-forward, purged, five-seed means, out of sample.

At one day ahead, the model delivers about 13% lower forecast loss than the strongest linear baseline, across the full out-of-sample window. That baseline is the HAR-IV spine itself, so the trees are graded against their own starting point. And the gap is statistically significant on the paired test you just saw, not eyeballed off a chart.

At five days ahead, about 6% lower. Also significant, same window, same baseline.

At twenty-two days, the four-parameter linear model wins. I'm not going to bury that. I want to argue it's a feature. At a monthly horizon, the month-ahead option market has already done the work. One good implied vol carries the forecast, and the trees have nothing left to add. A model that knows when to stop is a model you can trust when it speaks. It also tells you the evaluation is honest, because a rigged pipeline doesn't hand a win to the four-parameter baseline. And remember what we're timing: a daily product. The one-day horizon is the one that pays.

One more result, and it's the punchline of the whole methodology. Take the identical model, identical features, identical protocol, and train it on MSE instead of QLIKE. We ran three seeds of each to make sure this isn't one lucky draw. The QLIKE-trained model averages Sharpe 2.45. The MSE-trained model averages 2.32. That gap is modest in Sharpe, but the max drawdown tells the real story: QLIKE averages 3.0% peak-to-trough, MSE averages 3.4%. The QLIKE model keeps you out of more of the bad days.

Why? Three properties. First, QLIKE penalizes underprediction harder than the same-sized overprediction. For a variance seller, underestimating tomorrow's vol is the expensive mistake, not overestimating it. MSE treats both errors the same, which is the wrong asymmetry for this product.

Second, QLIKE is scale-invariant. A two-times overestimate at ten percent vol costs the same as a two-times overestimate at forty percent vol. MSE penalizes absolute error, so COVID-era observations dominate everything and the model over-allocates capacity to extreme days at the expense of the calm ones where it actually trades.

Third, and this is a theorem not a heuristic: QLIKE produces consistent model rankings even though realized variance is a noisy proxy for true integrated variance. MSE rankings can flip depending on the noise realization. When you can't observe the true target, you want a loss function whose scoreboard is stable. Patton proved this in 2011.

The loss function is not a detail. The loss function is the product.

Three numbers I want you to leave with.

## Section 7: Three numbers (slide 10, ~1 min)

> [SLIDE 10: Three numbers]

Three numbers, slowly.

2.45. Annualized Sharpe with the signal, against 2.09 without it, May 2022 to June 2026.

33%. The share of days the signal stands aside. It sells most days, but it skips the risky ones.

41% smaller max drawdown. Peak-to-trough loss drops from 5.1% to 3.0% when the signal is applied.

Out of sample, purged, and five-seeded. No cherry picks. One more slide before I take questions: where this goes next.

## Section 8: Next steps and close (slide 11, ~1.5 min)

> [SLIDE 11: Where this goes next]

This model is a first release, not a finished product. Five directions are queued behind it, and each one attacks something you've already seen today.

Regime detection, with hidden Markov models. On slide 8 you watched the trees re-weight implied against realized by regime, but they only ever infer the regime implicitly. An HMM names the state outright, calm, stressed, transitioning, and hands everything downstream a clean switch instead of a guess.

Cross-asset spillovers, with graph neural networks. We already train on a 21-symbol panel, but each name still forecasts alone. Vol doesn't move like that; it travels through related names. A graph model lets one symbol's shock inform its neighbours' forecasts.

Sentiment. Earlier I told you there's no sentiment scraping in the model. That was a design choice, not a verdict. The calendar features know what's scheduled; sentiment is a read on what isn't. It's the one input family the model doesn't have yet.

Sequence models. Every input today is a lag or an average that I chose to build. An LSTM reads the path directly and decides for itself which parts of history matter.

And ensembles routed by regime. Slide 9 showed you the trees winning at short horizons and the linear spine winning at long ones. The best model already depends on where you're standing. Regime routing takes that seriously: a calm-market specialist, a stress specialist, and the detector decides which one speaks.

The last cell is the one I care most about. Nothing in this pipeline is specific to GSVIVS01. It's a daily realized-variance forecast with an honest confidence story, and timing one variance seller is just the first application. If there's a strategy on your desk where this signal is directly applicable, reach out. I'd genuinely like to hear about it.

And whether it's to dig into the methodology, argue with the purge windows, or just have a chat: message me on Teams. The floor is open.

## Beat Sheet (one page)

| # | Slide | Beats | Transition out (verbatim) | The number |
|---|-------|-------|---------------------------|------------|
| 1-2 | Title / The product | sells daily, no view; 09:30 strip, 16:00 settle; 100 to 138; smoothness bought with the left tail; red ticks = mornings it should have stood aside | "So the question this project answers is simple. Can we tell, before nine thirty, which mornings are the wrong mornings to sell?" | 10.1 pts/yr |
| 3 | The claim | 09:10 rule, forecast vs strike; binary, short or flat; Kvar = VIX-style integral, above ATM IV; dashboard: Sharpe column, then max DD | "That is the claim. The rest of the talk is me earning it." | 2.09 to 2.45 |
| 4 | The model | HAR-IV spine, desk classic; trees learn residual via init score; floor if trees find nothing; trained on the loss we grade on; tenor matching | (into features, same section) | 4 parameters |
| 5 | The features | 4 families in trader words: price history, options surface, measurement quality, calendar; change + z-score expansion; nothing exotic | "Those are the ingredients. One more minute on how they're actually built, because the build is where the edge hides." | ~128 inputs |
| 6 | Feature stack | layers 0/1/2; continuous (bipower) vs jump, formally tested; up/down semivariances; signed jump; jumps don't forecast, so keep the persistent part clean | "That is the model. Here is why you should believe the numbers it produces." | RV = continuous + jump |
| 7 | Why trust | purge moat, ten days both sides; panel splits by date, 21 symbols; QLIKE one-liner; 5 seeds, mean not best; dashboard: Rankings tab | "So the protocol is airtight. The next question is what the model actually learned." | 6% lucky seed |
| 8 | What it learned | SHAP in 2 sentences; beeswarm read guide; live tour of top 5; one ALE: same-day IV, monotone, steepens in tail | "Which brings us to the honest scorecard." | top-5 features |
| 9 | Results | 13% at 1d; 6% at 5d; linear wins at 22d, argued as a feature; MSE ablation: 3-seed QLIKE 2.45 vs MSE 2.32, asymmetric penalty, proxy-robust | "Three numbers I want you to leave with." | QLIKE 2.45 vs MSE 2.32 |
| 10 | Three numbers | Sharpe 2.45 vs 2.09; stands aside 33% of days; 41% smaller max drawdown; out of sample, purged, five-seeded | "One more slide before I take questions: where this goes next." | 2.45 / 33% / 41% DD |
| 11 | Next steps / close | HMM names the regime (slide 8 callback); GNN spillovers on the 21-symbol panel; sentiment as the missing family (slide 5 callback); LSTM reads the path; regime-routed ensembles (slide 9 callback); signal is portable, reach out; Teams CTA | "The floor is open." | 5 directions |
