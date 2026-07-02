# Presentation Script: Timing the Variance Seller

**Duration:** ~20 minutes + open Q&A
**Audience:** trading desk (traders + quants)
**Deck:** `workspace/presentation/presentation.html` (9 slides, self-contained)
**Q&A backstop:** `qa-comprehensive.md`

## Regeneration

```bash
# GS (real dashboard):
./vol present --dashboard-path '../../src/data/models/trial_036_drop_vrp_calendar/plots/tournament_dashboard.html'
# Local (mock dashboard):
cd ml-vol-estimator && ./vol shell ../workspace/presentation/generate.py --dashboard-path tournament_dashboard_mock.html
```

## Section 1: The product and its problem (slides 1 to 2, ~2.5 min)

> [SLIDE 1: Timing the Variance Seller]

GSVIVS01 is about the simplest short volatility product we run: every morning it sells the day, and every afternoon it finds out what the day cost.

Everyone in this room knows the shape of that trade. Short variance pays a small premium on most days and hands you the tail on the worst ones. For the next twenty minutes I am going to try to tell those days apart.

> [SLIDE 2: GSVIVS01 sells variance every single day]

Here is one day in the life of the index. At 09:30 it sells a strip of same-day SPX options that replicates a variance swap, hedges the delta through the session, and settles at the 16:00 close. Next morning it does the same thing again. Every day, same size, no view. Nothing is carried overnight. Each day stands on its own. There is no timing anywhere in the product. That is what makes it simple, and it is also what makes it vulnerable.

Now the equity curve. The index goes from 100 to 138 over four years. That is roughly 9.6 points a year, collected a few basis points at a time.

Look how smooth that line is. The smoothness is not free. It is bought with the left tail.

The red ticks are the drawdown days. Each one is a morning where the index sold a strike, and by the close realized variance had beaten it. The drawdowns are not bad luck sprinkled at random. They are the mornings it should have stood aside, and it sold anyway.

A handful of mornings a year do most of the damage. And the index walks into every one of them, because it has nothing that tells one morning from another.

So the question this project answers is simple. Can we tell, before nine thirty, which mornings are the wrong mornings to sell?

## Section 2: The claim (slide 3, dashboard moment 1, ~1.5 min)

> [SLIDE 3: Every morning: compare the forecast to the strike]

Here is the decision we add. It happens at 09:10, twenty minutes before the strip goes out.

Overnight, the model produces a forecast of today's realized variance. The strike on offer is already pinned down by the previous close. At 09:10 we put the two numbers side by side. There is no look-ahead in either number. The forecast uses only what is known overnight, and the strike is last night's print.

If variance is rich, meaning the strike sits comfortably above the forecast, the index sells as usual. If the forecast comes in above the strike, we stand aside for the day. That is the entire rule. Short or flat, nothing in between, no sizing cleverness. A binary rule is easy to audit, and easy to overrule if the desk knows something the model does not.

The strike itself deserves thirty seconds. Kvar is the same out-of-the-money option integral the VIX is built on: puts below the forward, calls above, each weighted by one over strike squared. Because it integrates the whole wing, it inherits the skew. So the strike always sits above at-the-money implied vol.

That matters for honesty. If I benchmarked the forecast against ATM IV, the signal would look better than it is. We benchmark against the strike the index actually sells.

Now the headline. Layer that one rule onto the index, and the backtest goes from an annualized Sharpe of 1.60 as-is to 1.95 with the signal, measured May 2022 to June 2026.

> [DASHBOARD: GSVIVS tab, Sharpe column, then the stand-aside precision]

I would rather show you than tell you, so here is the dashboard. Every backtest number you hear today comes off this screen, not off a slide. This is the GSVIVS tab, and the Sharpe column is the number I just quoted: 1.60 without the signal, 1.95 with it, same window.

The figure I trust even more sits next to it: precision. The signal is not twitchy. It stands aside on about 2% of days over this window, and when it does, it tends to be right. 7 of the 10 stand-aside days preceded genuine drawdowns in the index.

That is the claim. The rest of the talk is me earning it.

## Section 3: The model (slides 4 to 5, ~4 min)

> [SLIDE 4: A linear spine and a tree overlay]

The model is two layers, and the first layer you already know.

The spine is HAR-IV: a four-parameter regression on today's realized variance, last week's average, last month's average, and implied vol. That model is a desk classic. It has been the benchmark in the vol-forecasting literature for years, and nothing about it is a black box. You can read its coefficients over coffee. On its own, it carries most of the forecast.

The second layer is LightGBM, a gradient-boosted tree ensemble. Why trees at all? Because vol responses are nonlinear and full of interactions. The same IV level means different things in different regimes, and trees capture that without me hand-writing every interaction.

But the design choice that matters is not the trees. It is what the trees are allowed to learn. They do not start from zero. They start from the spine's prediction, passed in as the init score. From there they learn only the residual: the part of the target the linear model leaves on the table.

That buys us a floor. If the trees find nothing, we are left holding the desk classic. Anything they do find is pure addition. And it keeps the machine learning honest, because the trees never have to re-learn what the spine already knows.

The whole stack trains end to end on the same loss we grade it on. There is no training on one metric and reporting another.

One feature of this slide earned its own box: tenor matching. Each forecast horizon reads the implied vol that expires with it. The one-day forecast reads same-day IV. The five-day forecast reads one-week IV, and the twenty-two-day reads one-month.

That sounds obvious, and the early version still got it wrong. Feed one-week IV into a one-day forecast and you smuggle in four days of term premium that have nothing to do with today. Fixing that was one of the cleanest gains in the whole project.

> [SLIDE 5: Four things the market tells you]

So what do the trees actually see? Four families of inputs, and each one fits in a sentence.

Price history: how volatile we have actually been, with up-moves, down-moves and jumps counted separately, because down-vol and jump risk carry different information.

The options surface: what the market is paying for future vol right now, term slope, skew, vol of vol. That family is the market's own forecast, and the model treats it as testimony, not truth.

Measurement quality: how much of today's variance reading is signal and how much is microstructure noise, from noise-robust estimators and unusual tick counts.

And the calendar: what is scheduled, Fed meetings, payrolls, option expiries.

Count those up, then let every series also contribute its daily change and a z-score against its own recent history. You land at about 128 inputs.

Notice what is not on the list. No alternative data, no sentiment scraping, nothing exotic. It is the information this desk already watches, every day, on its own screens. The model's contribution is the weighting, not the ingredients.

That is the model. Here is why you should believe the numbers it produces.

## Section 4: Why trust the number (slide 6, dashboard moment 2, ~4.5 min)

> [SLIDE 6: Walk-forward with a moat, five seeds]

Every number in this talk is out of sample. I want to spend real time on what that means here, because with overlapping time series it is easy to claim out of sample and still leak. When a machine-learning result on financial data is wrong, this is usually where it went wrong. So this is the slide I most want to be boring.

The protocol is an expanding walk-forward. Train on everything up to a date, test on the block that follows, extend the window, repeat. There is no random shuffling anywhere; time-series data gets time-series splits. Each test block sits strictly in the model's future. By the time we are done, the whole backtest window has been predicted by models that never saw it.

Now the moat, the hatched gap on this diagram. Training always stops ten trading days before each test block, and resumes ten trading days after it. Purged, on every fold.

Why? Because the target itself overlaps days. A five-day realized variance measured on Monday shares four sessions with one measured on Tuesday. Let training run right up to the boundary, and the last training labels contain pieces of the first test answers. The model would be graded on questions it partly saw. The purge removes that channel completely. That gap is the first guard.

Second guard: the panel. We pool 21 symbols into one training panel, and splits are by date across all 21 at once. When a date is in test, it is in test for every name. So one symbol can never hand tomorrow's market to another.

Third guard, and this is the paranoid one: early stopping. The routine internal check that decides when the trees stop growing runs on its own validation slice, and that slice sits behind its own purge gap. Even the model's housekeeping never peeks across the boundary.

Now the scoreboard, because the metric matters as much as the protocol. We judge every forecast on QLIKE. Here it is in one line: a proportional loss, calm markets count as much as crises, underprediction hurts more than overprediction, and its rankings hold up even though measured RV is itself a noisy proxy. That asymmetry is exactly right for a variance seller. The forecast that says calm before a storm is the expensive one.

Last guard: seeds. LightGBM is stochastic. Change the random seed and you grow a different forest. We ran five seeds on the final configuration, and one lucky seed looked 6% better than the truth, where the truth is the five-seed mean. If I had shown you that seed, you would have believed a number that does not exist. So the rule is fixed. Every headline number today is a five-seed mean, never a best seed.

> [DASHBOARD: Rankings tab, QLIKE column, OOS window in the header]

Here is where those rules land. This is the Rankings tab, one row per model. The QLIKE column is the scoreboard, lower is better, and the raw levels live here rather than on the slides. The out-of-sample window is printed right in the header, so you can see exactly which period is being graded.

Two of these columns get one sentence each. DM is Diebold-Mariano, a paired test that the gap is real. MCS is the model confidence set, the set of models you cannot statistically tell from the best. Both have full write-ups in the Q&A pack if you want to go deeper.

So the protocol is airtight. The next question is what the model actually learned.

## Section 5: What it learned (slide 7, dashboard moments 3 and 4, ~4 min)

> [SLIDE 7: Everything it learned has a name you know]

If the trees beat the spine, I want to know what they know. Two sentences on the tool. SHAP splits every individual forecast into named feature contributions that sum exactly to the prediction. We use it to audit what the trees add on top of the linear spine, day by day, feature by feature.

Twenty seconds on how to read the chart, using the guide on this slide. Each row is a feature, and each dot is one trading day. Rows are ranked by how much they move the forecast, so height on the page is importance. Dots to the right of the line pushed that day's forecast up. Dots to the left pushed it down. Color is the feature's own value, blue for low, red for high. So a clean feature reads like the top row: red dots on the right, blue on the left, high values push vol up.

> [DASHBOARD: SHAP beeswarm, h=1]

Now the real thing: the beeswarm for the one-day model. Let me take the top five features. Every one of them is a story you already trade.

First, and at the top of the list: the relationship between implied and realized, and how it shifts with regime. In calm tape, implied runs rich to realized, and the model discounts it. In stress the gap closes, and the model listens harder. That re-weighting by regime is what a vol trader does by instinct. The trees learned it from data.

Second: extremes of the variance risk premium, the spread between what options charge for variance and what variance actually delivers. When that premium is stretched far beyond its usual range, in either direction, snap-back becomes forecastable, and the model leans into it.

Third: Fed proximity. Vol has a schedule around FOMC, compression into the meeting and release after it, and the model prices that calendar the same way the desk does.

Fourth and fifth: the z-score flags. When a series runs unusually hot against its own recent history, the model reads it as stretched and expects mean reversion, not continuation.

Nothing on that list should surprise anyone in this room, and that is precisely the point. The edge comes from pricing familiar effects with discipline, not from a mystery factor. If the top of the list were something nobody here could name, I would trust this model less, not more.

One more view, because SHAP tells you what mattered, not the shape of the response.

> [DASHBOARD: ALE, h=1, same-day IV]

This is an ALE curve: the model's average response to a single input, with everything else held honest. This one is same-day implied vol against the one-day forecast.

The curve rises monotonically. No kinks, no nonsense, exactly what you would demand of an IV response. And the slope steepens in the tail. Read that plainly: when IV is screaming, the model leans on it hardest. The information content is highest exactly when it matters. And the tail is exactly where the stand-aside call gets made.

Which brings us to the honest scorecard.

## Section 6: Where it wins (slide 8, ~2.5 min)

> [SLIDE 8: Where it wins, and where it honestly doesn't]

Three horizons, three results. The bars are forecast-loss reductions, so taller is better, and one of them points the wrong way. I will get to it. Everything on this slide is the same protocol you just audited: walk-forward, purged, five-seed means, out of sample.

At one day ahead, the model delivers about 10% lower forecast loss than the strongest linear baseline, across the full out-of-sample window. That baseline is the HAR-IV spine itself, so the trees are graded against their own starting point. And the gap is statistically significant on the paired test you just saw, not eyeballed off a chart.

At five days ahead, about 11% lower. Also significant, same window, same baseline.

At twenty-two days, the four-parameter linear model wins. I am not going to bury that. I want to argue it is a feature. At a monthly horizon, the month-ahead option market has already done the work. One good implied vol carries the forecast, and the trees have nothing left to add. A model that knows when to stop is a model you can trust when it speaks. It also tells you the evaluation is honest, because a rigged pipeline does not hand a win to the four-parameter baseline. And remember what we are timing: a daily product. The one-day horizon is the one that pays.

One more result, and it is the punchline of the whole methodology. Take the identical model, identical features, identical protocol, and train it on MSE instead of QLIKE. It trades at a Sharpe of 0.3 on the same backtest, against 1.95 for the QLIKE version. Nothing else changed. Not one feature, not one fold. The mechanism is simple. MSE chases the big days and shrugs at the calm ones, and calm days are where a variance seller lives. Get the calm days wrong and the signal misfires all summer. The loss function is not a detail. The loss function is the product.

Three caveats before I stop, and then three numbers I want you to leave with.

## Section 7: Close (slide 9, ~1 min)

> [SLIDE 9: Three caveats, three numbers]

Caveat one: the backtest strike is a proxy built from the index's own marks. It tracks the real strike with correlation above 0.99, and the production feed exists. An engineering step, not a research risk.

Caveat two: the edge is concentrated. About ten signal changes a year, so each call carries real weight. That cuts both ways: little churn to manage, but every decision matters.

Caveat three: by construction, COVID enters training only from 2022 onward. The model learned 2020 as history. The backtest never traded through it, and a 2020-style regime would be new territory for the signal too.

Now the three numbers, slowly.

1.95. Annualized Sharpe with the signal, against 1.60 without it, May 2022 to June 2026.

2%. The share of days the signal stands aside. It sells almost every day. It just skips the wrong ones.

7 of 10. Of the ten days it stood aside, seven preceded genuine drawdowns.

No slideware claims, no cherry picks: everything you saw is out of sample, purged, and five-seeded. The floor is open.
