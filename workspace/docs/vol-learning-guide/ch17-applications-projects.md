# Chapter 17. Practical Applications and Project Directions

A model that beats HAR by 8% on QLIKE is scientifically interesting. But a desk head wants to know: how much Sharpe does that buy me? How much P&L does it add to my book?

## Volatility Targeting: The Simplest Economic Value Test

> **Prereq: Background**
>
> This section requires familiarity with portfolio returns and the Sharpe ratio (any introductory finance text), as well as realized volatility forecasts from Chapters [6](ch06-har-model.md) through [13](ch13-hybrid-ensemble.md).

**Volatility targeting** is the simplest and most widely used application of a vol forecast in systematic investing. The idea: size your position inversely proportional to forecast vol, so that portfolio risk stays roughly constant over time.

### The EWMA Baseline

The workhorse volatility estimate used by the vast majority of systematic funds for position sizing is not GARCH, not HAR, but plain **exponentially weighted moving average (EWMA)** smoothing:

$$\hat\sigma^2_t = (1-\delta)\,r_{t-1}^2 + \delta\,\hat\sigma^2_{t-1},$$

where $\delta$ is chosen so the half-life matches approximately 20 to 60 trading days. Its popularity stems from simplicity, low latency, and the fact that it requires exactly one parameter.

> **Intuition: In Plain English**
>
> Tomorrow's variance estimate is a weighted blend of today's squared return (the "news") and today's variance estimate (the "memory"). A high $\delta$ means slow adaptation (the estimate barely moves day-to-day); a low $\delta$ means it jumps quickly with every new return, reacting fast but also picking up noise.

### The Volatility-Targeting Formula

Given a forecast $\hat\sigma_t$ (annualized), the **volatility-targeted weight** is:

$$w_t = \frac{\sigma_{\text{target}}}{\hat\sigma_t}.$$

The portfolio return is then $r_t^{\text{VT}} = w_t \cdot r_t$. When forecast vol is high, $w_t < 1$ (reduce position). When forecast vol is low, $w_t > 1$ (lever up). The result is a return stream with approximately constant realized volatility equal to $\sigma_{\text{target}}$.

> **Intuition: Why Vol-Targeting Adds Sharpe**
>
> Moreira and Muir (2017) showed that vol-targeting adds approximately 0.3 Sharpe ratio across equity indices, currencies, and commodities. The mechanism: by reducing exposure before drawdowns, vol-targeting truncates the left tail. A better vol forecast means you cut exposure earlier and more precisely.

### Connection to Time-Series Momentum

Moskowitz, Ooi, and Pedersen (2012) use a related framework for time-series momentum across 58 futures: signal $=$ sign of 12-month return, position size $= 40\%/\hat\sigma_t$. The vol forecast enters the denominator. Every percentage improvement in your forecast precision tightens the position-sizing, reducing both crash risk and unnecessary leverage. This is the mechanism by which better QLIKE translates to better risk-adjusted returns in a TSMOM book.

> **Warning: Forecast Failure in Crises**
>
> Vol targeting assumes volatility is predictable but returns are not. If your forecast systematically underpredicts during crises (all ML models trained on normal data underpredict COVID-style jumps), vol targeting will keep positions too large going into the drawdown. Mitigation: ensemble your ML forecast with a simple $\max(\text{ML},\; 1.5 \times \text{EWMA})$ floor during high-uncertainty regimes, or cap $w_t$ at a maximum leverage ratio (e.g., $w_t \leq 2.0$).

> **Application: The Key Deliverable Table**
>
> For your internship deliverable, the key table is:
>
> 1. Run vol-targeted long-SPX using each model.
> 2. Report annualized return, vol, Sharpe, max drawdown, and Calmar ratio.
> 3. Compute Sharpe improvement per 1% QLIKE improvement.
>
> This single table communicates economic value in the language every systematic desk speaks.

## Trading Costs, Turnover, and Net Economic Value

> **Prereq: Background**
>
> This section builds directly on the vol-targeting strategy of the Volatility Targeting section and the weight $w_t = \sigma_{\text{target}}/\hat\sigma_t$ from the volatility-targeted weight equation above. It also assumes the QLIKE loss and Diebold-Mariano test from [Chapter 16](ch16-forecast-evaluation.md) (the QLIKE and Diebold-Mariano sections). One **basis point** (bp) $= 0.01\% = 0.0001$; a $5$ bp cost means you pay $0.05\%$ of the traded notional each time you adjust the position.

> **Intuition: What a Sharpe Ratio Means**
>
> The $0.76$ vs. $0.88$ gap below is a meaningful but not enormous edge (the full Sharpe definition is collected in the performance-metrics table below).

The Sharpe ratios in the worked-example table of the Volatility Targeting section ($0.76$ for EWMA, $0.88$ for ML) were all computed *gross*: they ignored the cost of trading. [Chapter 16](ch16-forecast-evaluation.md) required that a real QLIKE improvement "survive transaction costs" and that turnover be reported alongside any economic-value claim. It answers the question a desk head asks the instant you show a Sharpe improvement: *how much of that survives once I have to pay the spread every time the forecast moves the position?*

The tension: the extra reactivity that wins on QLIKE is exactly what raises trading, so a jumpier forecast can win gross and lose net.

### Net P&L on the Vol-Targeting Weight

The gross return of the vol-targeted strategy, from the Volatility-Targeting Formula section, is $r_t^{\text{VT}} = w_t \cdot r_t$, where $w_t = \sigma_{\text{target}}/\hat\sigma_t$ and $r_t$ is the underlying SPX return. Trading costs are proportional to the *change* in the weight, because you only pay the spread on the notional you actually buy or sell:

$$\text{PnL}_t^{\text{net}} \;=\; \underbrace{w_t \cdot r_t}_{\text{gross return}} \;-\; \underbrace{|w_t - w_{t-1}| \cdot c}_{\text{cost of rebalancing}},$$

where:

- $w_t = \sigma_{\text{target}}/\hat\sigma_t$ --- the vol-targeted weight held through day $t$ (set at the close of day $t-1$ from information up to $t-1$, so no look-ahead).
- $|w_t - w_{t-1}|$ --- the absolute change in the weight, i.e. the fraction of notional you must trade to move from yesterday's position to today's.
- $c$ --- the **half-spread cost** per unit of traded notional, expressed in the same units as $r_t$. A full round-trip (out and back) costs $2c$.

If the forecast is unchanged, $w_t = w_{t-1}$ and you pay nothing. If a vol spike pushes the weight down over several days --- as the ML model did in the Volatility Targeting section, from $0.82$ on day 13 to $0.36$ on day 16 --- the cost is charged on each day's move, not on the cumulative drop. The largest single-day cut in that table is on day 14 ($|0.54 - 0.82| = 0.28$ of notional, costing $0.28\,c$); the day-16 move itself is only $|0.36 - 0.45| = 0.09$.

### Turnover and the Sharpe Drag

The single number that summarizes how expensive a forecast is to run is its **turnover**: the average amount of notional it forces you to trade per day. For the vol-targeting weight, daily turnover is the absolute day-on-day change in the weight,

$$\bar\tau \;=\; \frac{1}{T}\sum_{t=1}^{T} |w_t - w_{t-1}|,
\qquad
\text{annualized turnover} \;=\; 252 \times \bar\tau,$$

where:

- $|w_t - w_{t-1}|$ --- one day's traded notional, as a fraction of the book.
- $T$ --- the number of days in the backtest.
- the factor $252$ --- the number of trading days per year, converting a daily average into an annual trading volume.

A strategy with $\bar\tau = 0.05$ resizes $5\%$ of its position on an average day; over $252$ trading days that adds up to $252 \times 0.05 = 12.6$ times the size of the whole book traded in a year.

Turnover matters because it converts, almost mechanically, into a deduction from the Sharpe ratio. Annualizing the cost term of the net P&L equation and dividing by the volatility of the strategy's returns gives the **Sharpe drag**:

$$\operatorname{SR}^{\text{net}} \;\approx\; \underbrace{\operatorname{SR}^{\text{gross}}}_{\text{paper Sharpe}} \;-\; \underbrace{\frac{252 \cdot \bar\tau \cdot c}{\sigma_{\text{ret}}}}_{\text{cost drag}},$$

where:

- $\operatorname{SR}^{\text{gross}}$ --- the annualized Sharpe of the gross vol-targeted return stream $w_t r_t$.
- $\bar\tau$ --- average daily turnover from the turnover equation above.
- $c$ --- the half-spread cost per unit notional.
- $\sigma_{\text{ret}}$ --- the annualized volatility of the gross returns (for a vol-targeted book this is approximately $\sigma_{\text{target}}$ by construction).

> **Intuition: In Plain English**
>
> Where does the exact shape come from? Sharpe is average return $\div$ volatility. Costs lower the average return by (annual turnover $\times$ cost per trade) $= 252\,\bar\tau\,c$ each year, but barely touch the volatility. So the Sharpe falls by exactly that cost amount divided by the same $\sigma_{\text{ret}}$ you were already dividing by --- which is the second term. The $\sqrt{252}$ in the Sharpe definition is absorbed because both the numerator (now a per-year cost) and $\sigma_{\text{ret}}$ are on an annual footing.

### The Sharpe-vs-Cost Curve and Breakeven Cost

A single net Sharpe number hides where the strategy dies. The right object to report is the **Sharpe-vs-cost curve**: net Sharpe evaluated across a grid of cost levels, $c \in \{0, 1, 2, 5, 10, 20\}$ bp, with all three forecasts plotted on the same axes (see the deliverable guidance in the Performance-Metric Reference section). By the Sharpe-drag equation this is a straight line in $c$. Read it as a graph with cost $c$ on the horizontal axis and net Sharpe on the vertical: the line starts at the gross Sharpe when cost is zero (its *intercept*, $\operatorname{SR}^{\text{gross}}$) and slides downward as cost rises, with the steepness of that downward slide (its *slope*, $-252\,\bar\tau/\sigma_{\text{ret}}$) set by how much you trade. The point where the line crosses zero is the **breakeven cost** $c^\ast$, the half-spread at which the strategy stops making money:

$$c^\ast \;=\; \frac{\operatorname{SR}^{\text{gross}} \cdot \sigma_{\text{ret}}}{252 \cdot \bar\tau},$$

where every symbol is as defined for the Sharpe-drag equation.

> **Intuition: In Plain English**
>
> The breakeven cost answers "how expensive could trading get before this forecast is worthless?" A forecast that needs cheap execution to make money has a low $c^\ast$; a robust forecast keeps a positive Sharpe even when spreads widen. Two forecasts with identical gross Sharpe can have very different $c^\ast$: the smoother one (lower $\bar\tau$) survives to a higher cost. So $c^\ast$ rewards exactly the property --- forecast smoothness --- that raw QLIKE and gross Sharpe are blind to.

Report $\operatorname{SR}^{\text{net}}(c)$ for all three forecasts on the same axes rather than a single number; the schematic below shows what the plot looks like.

*Schematic Sharpe-vs-cost curves. Each forecast is a straight line of net Sharpe (vertical axis) against half-spread cost $c$ in bp (horizontal axis, 0 to 90). Each line starts at its gross Sharpe (intercept at $c = 0$): the ML line at $0.88$ with slope $-0.88/39$, the HAR line at $0.82$ with slope $-0.82/81$, and the EWMA baseline at $0.76$ with slope $-0.76/95$. Each slides down a straight line whose steepness is its turnover; where a line hits zero is its breakeven cost $c^\ast$ (ML at $\approx 39$ bp, HAR at $\approx 81$ bp). The reactive ML forecast has the highest gross Sharpe but the steepest slope, so it crosses zero first. A dashed vertical line marks the realistic SPX cost ($\approx 1$ bp); at that cost all three are comfortably positive and the higher gross Sharpe wins.*

### What SPX Futures Actually Cost

The cost grid above is a stress test; for the instrument your project actually trades it is worth knowing the realistic number. The strategy in the Volatility Targeting section sizes exposure to the S&P 500, implemented through **E-mini** or **Micro E-mini S&P 500 futures** --- among the most liquid exchange-traded instruments in the world. For a single E-mini contract the bid-ask spread is typically one **tick** ($0.25$ index points), and each E-mini contract is worth $50 \times$ the index level (the contract multiplier). Walk the chain at an index level of $\approx 5000$: the contract is worth $50 \times 5000 = \$250{,}000$, and one tick is worth $50 \times 0.25 = \$12.50$, so the full spread is $12.5 / 250{,}000 \approx 0.5$ bp --- a **half-spread of well under $1$ bp** (half the round-trip spread defined above) in normal conditions. Adding exchange and clearing fees, a realistic all-in round-trip cost for vol-targeting rebalances is on the order of **$1$ to $2$ bp**, widening in stressed markets.

> **Warning: Use One Instrument's Real Cost, Then Stress It**
>
> Do not paste a generic cross-asset cost table into a vol-targeting report. The strategy trades one thing --- SPX futures --- so anchor on its real half-spread ($\lesssim 1$ bp) and then sweep upward through the $\{1,2,5,10,20\}$ bp grid to show robustness, not to suggest you trade twenty-basis-point instruments. The grid is there to expose how a high-turnover ML forecast would fare *if* costs rose, e.g. in a liquidity crunch when spreads on even E-minis widen.

### Performance-Metric Reference

The vol-targeting deliverable table (the Volatility Targeting section) should report a consistent set of metrics for each forecast. The table below collects the definitions in one place. Every metric is computed on the *net* return stream $\text{PnL}_t^{\text{net}}$ from the net P&L equation.

*Performance metrics for a vol-targeting backtest. All computed on net-of-cost returns. Annualization uses $252$ trading days.*

| Metric | Formula / Description | What It Tells You |
|---|---|---|
| Sharpe ratio | $\operatorname{SR} = (\mu_{\text{ret}} / \sigma_{\text{ret}}) \times \sqrt{252}$ | Risk-adjusted return; the headline number |
| Sortino ratio | $(\mu_{\text{ret}} / \sigma_{\text{downside}}) \times \sqrt{252}$ | Like Sharpe but $\sigma_{\text{downside}}$ counts only the volatility of losing days; use when returns are skewed |
| Hit rate | $\#\{\text{PnL}_t > 0\} / T$ | Fraction of profitable days; aim $> 50\%$ |
| Max drawdown | $\max_{s \le t}(\text{cumPnL}_s - \text{cumPnL}_t)$ | How far the running total fell from its highest previous point --- the deepest hole the strategy dug; the survival metric |
| Calmar ratio | Annualized return $/$ max drawdown | Return per unit of worst-case pain |
| Turnover | $\bar\tau = \tfrac{1}{T}\sum |w_t - w_{t-1}|$ | Trading intensity; the cost driver |
| Breakeven cost | $c^\ast$ where $\operatorname{SR}^{\text{net}}(c^\ast) = 0$ | Tradeability threshold; the desk's first question |

> **Key Idea: Lead with Net Sharpe and Breakeven, Support with the Rest**
>
> Never report a single net Sharpe. Plot $\operatorname{SR}^{\text{net}}(c)$ across the $\{0, 1, 2, 5, 10, 20\}$ bp grid for the ML forecast, the HAR forecast, and the EWMA baseline (the EWMA Baseline section) on *identical* axes (the Sharpe-vs-cost curve schematic). In your deliverable, lead with net Sharpe at the realistic SPX cost ($\approx 1$ bp) and the breakeven cost $c^\ast$ where each line hits zero --- the single number a systematic desk cares about most. What matters is whether the ML curve sits *above* HAR across the whole plausible cost range, not just at $c = 0$. Support with max drawdown, Calmar, and turnover. If the desk asks one question it will be about $c^\ast$; if they ask two, the second is about max drawdown.

### Fragility: Where Does the P&L Come From?

A strong net Sharpe can still hide a fragile strategy. The vol-targeting Sharpe gain comes from cutting exposure before drawdowns, so a natural worry is that *all* of the edge is concentrated in one or two crisis episodes. Aggregate metrics will not reveal this; a P&L-source decomposition will.

> **Key Idea: The Fragility Rule of Thumb**
>
> If more than $70\%$ of the strategy's cumulative net P&L comes from days that make up less than $30\%$ of the sample, the strategy is **fragile**: it is a regime bet (a **regime** being a market environment such as a calm stretch or a crisis period), not a robust earner. These figures are a heuristic, not a law --- the idea is simply that if most of your profit comes from a small handful of unusual days, you are really betting on those days recurring. If net P&L accrues roughly in proportion to time spent in each state, the strategy is **broad-based** --- which is what you want for a deliverable that claims a forecast adds steady economic value.

A cheap and informative version of this check, available before any regime model, is a **VIX-tercile decomposition**. Split the backtest days into low, medium, and high VIX terciles, and sum net P&L within each:

- If the vol-targeting edge over EWMA is concentrated entirely in the high-VIX tercile, the ML forecast is really a *crisis detector* --- valuable, but you should say so, because a desk that does not want concentrated crisis exposure will read that Sharpe differently.
- If the edge is spread across terciles, the better forecast is improving position sizing in ordinary conditions too, and the Sharpe gain is more durable.

Report the tercile split alongside the headline table. It costs one extra row and pre-empts the desk's sharpest question about where the money comes from.

## Dealer Gamma and Structured Products Feedback

Beyond statistical forecasting, volatility is shaped by the mechanical hedging behavior of options dealers. When dealers hold large gamma positions, their hedging creates predictable effects on realized vol. Understanding this mechanism gives you both a novel feature and a deeper appreciation for what your model is capturing.

### How Dealer Hedging Amplifies or Suppresses Vol

When dealers are **long gamma** (they own options), they delta-hedge by selling into rallies and buying dips. This mean-reversion pressure suppresses realized volatility below what pure news flow would generate. Conversely, when dealers are **short gamma** (common after selling structured products like autocallables), they hedge by buying into rallies and selling into dips, amplifying moves and increasing realized vol.

> **Key Idea: GEX as a Volatility Feature**
>
> **Gamma Exposure (GEX)** estimates the net dealer gamma across all strikes from publicly available options open interest data. The estimate is approximate but directionally informative:
>
> $$\text{GEX} \approx \sum_{\text{strikes}\,K} \text{OI}_K \times \Gamma_K \times 100 \times S$$
>
> - Positive GEX (dealers long gamma): expect lower-than-forecast RV (mean reversion).
> - Negative GEX (dealers short gamma): expect higher-than-forecast RV (momentum/amplification).
>
> Adding $\text{sign}(\text{GEX})$ or GEX-quintile as a feature to HAR-X is a novel extension not yet thoroughly explored in the academic literature (Bennett, 2014).

### Structured Products and the Short-Gamma Overhang

The primary source of dealer short-gamma exposure is structured products (autocallables, barrier options, worst-of notes). These products embed knock-in/knock-out barriers near current spot levels. As spot approaches a barrier, the product's gamma becomes very negative, forcing dealers to hedge aggressively. The systematic issuance of these products (estimated at hundreds of billions of notional globally) creates a permanent structural short-gamma overhang in equity index markets.

### Pin Risk at Expiry

Near options expiry, large open interest at specific strikes creates **pinning** effects: the stock gravitates toward the strike as dealers' gamma hedging intensifies near that level. This suppresses realized vol on expiry days, a calendar effect (see the Calendar and Event Features section of [Chapter 10](ch10-feature-engineering.md)) with a mechanical explanation.

> **Application: Novel HAR-X Features from Dealer Positioning**
>
> Beyond GEX, distance to nearest barrier level and net open interest by strike are publicly computable dealer-positioning features worth testing for incremental predictive power in a HAR-X model.

## Communicating Volatility Forecasting Results

> **Prereq: Background**
>
> This section assumes you have results to present: a QLIKE comparison and Diebold-Mariano test from [Chapter 16](ch16-forecast-evaluation.md) (the QLIKE and Diebold-Mariano sections), the vol-targeting economic-value test from the Volatility Targeting and Net Economic Value sections, and the overfitting controls from [Chapter 16](ch16-forecast-evaluation.md) (the Deflated Sharpe Ratio, purged cross-validation, and look-ahead taxonomy sections). The skill here is not generating results --- it is communicating them so a volatility desk trusts the work in twenty minutes.

You have built a forecast that beats HAR on QLIKE and adds net Sharpe in a vol-targeting test. The remaining risk is entirely in the telling. A desk audience decides in the first minute whether to engage with your hypothesis or to start hunting for the **overfitting** that they assume is hiding behind any ML result. (Overfitting means a model looks good on the data it was built from but fails on new data --- and the more feature combinations you try, the more likely one looks good by pure chance, which is why a desk hearing "47 features" immediately distrusts the result.) This section is about controlling that first minute and the nineteen that follow.

### Frame It as a Hypothesis Test, Not a Fishing Expedition

The question that decides your reception is: *did you start from an economic reason to expect this feature to help, or did you feed everything into a tree and report what stuck?* There are two ways to open, and they trigger opposite reactions.

- **Good (grounded hypothesis):** "The leverage effect ([Chapter 6](ch06-har-model.md)) says negative returns predict higher future volatility, so we added a signed-return / semivariance feature to HAR. It improves QLIKE by $4\%$ with a Diebold-Mariano $t$-statistic of $2.9$ (a $t$ above $\approx 2$ means the accuracy gap is unlikely to be luck)."
- **Bad (fishing expedition):** "We fed $47$ features into a LightGBM model and it forecasts RV better than HAR."

The first framing invites engagement: there is a well-grounded mechanism --- the leverage effect, or the variance risk premium ([Chapter 9](ch09-variance-risk-premium.md)) --- and modern tools were used to test it. The audience evaluates the hypothesis, then checks whether the test is clean. The second framing invites the question "how many features did you try?" and a reach for the Deflated Sharpe Ratio (the Deflated Sharpe Ratio section of [Chapter 16](ch16-forecast-evaluation.md); a Sharpe adjusted downward for how many things you tried, so that staying positive means the edge survives that penalty).

> **Key Idea: The ML Is the Test, Not the Story**
>
> Lead with the volatility mechanism, not the model: the economic theory provides the *why*, the ML ([Chapter 11](ch11-tree-methods-vol.md)) provides the *how much better than HAR*, and the forecast is judged against the HAR baseline, not by its raw $R^2$.

> **Warning: Never Open with Model Architecture**
>
> If the first thing the desk hears is "a $500$-tree LightGBM ensemble with Bayesian hyperparameter search," you have lost them. They will spend the rest of the talk looking for overfitting instead of listening to results. Model complexity is a *liability* until you have shown that the HAR baseline ([Chapter 6](ch06-har-model.md)) cannot do the job --- which is exactly why HAR appears on every chart. Save the architecture for the methodology slide.

### One Slide Per Claim

The discipline that keeps a desk presentation tight is **one slide per claim**. Each slide communicates exactly one takeaway, and the structure is fixed:

- **Title = the claim.** Not "Results" but "A semivariance feature beats HAR on QLIKE by $4\%$ ($\text{DM } t = 2.9$)." The title is the takeaway.
- **Body = one chart.** One chart proves the claim. No multi-chart slides --- they split attention and invite the audience to study the wrong panel while you talk about the right one.
- **Footer = the metric.** A single line with the key numbers: "$\operatorname{QLIKE}_{\text{ML}} = 0.241$ vs. $\operatorname{QLIKE}_{\text{HAR}} = 0.251$; DM $t = 2.9$; net $\operatorname{SR} = 0.84$; $n = 1{,}250$."

The same discipline governs chart **captions** in the written report: a caption must make the chart self-explaining. The contrast is stark.

- **Vacuous caption:** "Figure 3: Forecast comparison."
- **Self-explaining caption:** "Figure 3: The HAR-plus-semivariance model lowers out-of-sample QLIKE by $4\%$ relative to HAR (Diebold-Mariano $t = 2.9$, see the Diebold-Mariano section of [Chapter 16](ch16-forecast-evaluation.md)). Solid line: ML forecast; dashed line: HAR baseline."

The second caption states the claim, the magnitude, the significance test, and which line is which. A reader who sees only the figure and its caption should be able to reconstruct your point.

> **Key Idea: If They Only Read the Titles**
>
> Write slide titles so that reading them in sequence tells the whole story. Test it: list your titles and hand them to a colleague. If they can reconstruct the argument from titles alone --- hypothesis, QLIKE result, DM significance, net economic value, what failed --- the deck is well structured. If they cannot, rewrite the titles until they can.

### Negative Results Are a Credibility Signal

A presentation that reports only wins triggers the audience's overfitting alarm. One that says "we tested four feature families against HAR; two beat it, two did not" signals intellectual honesty --- and honesty is what buys belief in the wins.

Report which feature families *failed* to beat the HAR baseline, and why. Useful negatives for a volatility project look like:

- "Cross-asset RV spillover features added no QLIKE improvement over HAR after purged cross-validation (the purged cross-validation section of [Chapter 16](ch16-forecast-evaluation.md); cross-validation that removes train/test windows that overlap in time, so nothing leaks); the Diebold-Mariano test could not reject equal accuracy ($t = 0.4$)."
- "A jump-component split (HAR-J) helped in-sample but the gain did not survive walk-forward evaluation (training only on the past and testing on the next block, rolling forward) --- consistent with the difficulty of forecasting the jump part of RV."
- "LightGBM did not beat ridge-HAR (a HAR regression with ridge regularization, i.e. a penalty that shrinks the coefficients) on the same features. The RV-to-RV mapping appears close to linear in our sample ([Chapter 11](ch11-tree-methods-vol.md), the honest-results section), so we report the linear model."

Each of these tells the desk what the *data* look like, not just what the model found. Put them on one slide titled honestly, e.g. "Feature families that did not beat HAR," as a compact table of family, QLIKE-vs-HAR, DM $t$-statistic, and the reason.

> **Intuition: Negatives Build Trust Because They Are Costly**
>
> Reporting failures costs scarce presentation time and exposes the limits of your work. The audience knows this. The fact that you are *willing* to pay that cost signals that the positive results are real. A presenter who shows only successes is optimizing for impression, not information --- and an experienced desk head can tell the difference instantly.

### The Written Report and Its Page Budget

The written deliverable is a desk-ready report, not slides. Page budgets enforce discipline --- they stop you from burying the result in methodology. A workable structure:

1. **Executive summary** ($1$ page). Hypothesis, headline QLIKE/DM result, net economic value. A busy desk head reads only this page.
2. **Hypothesis and motivation** ($1$ to $2$ pages). The volatility mechanism --- leverage effect ([Chapter 6](ch06-har-model.md)), variance risk premium ([Chapter 9](ch09-variance-risk-premium.md)) --- that motivates the feature.
3. **Data and features** ($2$ to $3$ pages). RV construction, HAR components, the candidate feature families, sample period, and the reserved holdout (data locked away and never looked at during model-building).
4. **Methodology** ($2$ to $3$ pages). QLIKE loss, purged cross-validation, look-ahead controls (all from [Chapter 16](ch16-forecast-evaluation.md)), model specifications.
5. **Results, with the HAR baseline** ($3$ to $5$ pages). One subsection per feature family. Each: QLIKE table vs. HAR, Diebold-Mariano test, and the vol-targeting net-Sharpe table from the Net Economic Value section, always plotted against HAR.
6. **Negative results** ($1$ page). Which families did not beat HAR, and why.
7. **Robustness** ($1$ to $2$ pages). DSR after the honest trial count (the Deflated Sharpe Ratio section of [Chapter 16](ch16-forecast-evaluation.md)), walk-forward stability, feature stability across regimes (per the regime-stable feature-selection discussion in [Chapter 12](ch12-rashomon-interpretable-trees.md) and your own subsamples).
8. **Economic value** ($1$ page). Sharpe-vs-cost curve, breakeven cost $c^\ast$, turnover, VIX-tercile P&L decomposition (the Net Economic Value section).
9. **Limitations and next steps** ($1$ page). Sample-size caveats, crisis-underprediction risk (the Time-Series Momentum connection section), proposed extensions.

Every chart in the report supports exactly one claim, stated in its caption (the One Slide Per Claim section).

> **Warning: Do Not Iterate After Unblinding the Holdout**
>
> [Chapter 16](ch16-forecast-evaluation.md) made this point under the look-ahead taxonomy; it bears repeating here. The out-of-sample test on the reserved holdout is a *one-shot* exercise. You run it once, report the result, and do not return to re-tune. "In-sample QLIKE improvement $5\%$, out-of-sample $3\%$" is a legitimate, honest result. "We re-optimized on the holdout until the out-of-sample number improved" is not a result --- it is the bias the whole evaluation framework exists to prevent.

### Handling Desk Questions

> **Prereq: Know Your Backup Slides**
>
> For every question below, prepare a backup slide with the detailed chart or table. Your verbal answer should be two sentences; if they want more, flip to the backup. Prepare five to eight backups covering these scenarios.

The following questions come up in almost every desk presentation of a volatility forecast. The discipline: cross-reference the analysis already in your deck rather than re-deriving it on the whiteboard.

**"Is your model really beating HAR, or is it noise?"**

*Answer:* "Out-of-sample QLIKE improves by $4\%$, and the Diebold-Mariano test (the Diebold-Mariano section of [Chapter 16](ch16-forecast-evaluation.md)) rejects equal accuracy at $t = 2.9$. The improvement holds in walk-forward, not just one split."

*Backup slide:* QLIKE-vs-HAR table with DM $t$-statistics per feature family.

**"What happens in a crisis --- does it underpredict?"**

*Answer:* "Like all models trained on mostly-calm data, it underpredicts the largest jumps; we show this in the VIX-tercile decomposition (the Net Economic Value section). The vol-targeting book floors leverage during high-uncertainty regimes (the Time-Series Momentum connection section) to bound the damage."

*Backup slide:* VIX-tercile net-P&L table plus the crisis-underprediction note.

**"Why not just use HAR --- is the nonlinearity real?"**

*Answer:* "We tested ridge-HAR on identical features; where the tree wins, SHAP (a tool that quantifies how much each feature pushed a given prediction) attributes the win to a threshold effect --- the model behaving differently above versus below a vol level --- which a straight-line (linear) model, by definition, cannot represent ([Chapter 11](ch11-tree-methods-vol.md)). Where ridge ties the tree, we report the linear model as production."

*Backup slide:* HAR vs. ridge-HAR vs. LightGBM QLIKE bar chart (the honest-results section of [Chapter 11](ch11-tree-methods-vol.md)).

**"Are the features stable across regimes?"**

*Answer:* "We re-estimated feature importance in calm and stressed subsamples; the top HAR components and the leverage feature stay dominant in both, while the cross-asset features are unstable (which is why we dropped them). The regime split is in the robustness section."

*Backup slide:* feature-importance-by-regime comparison.

**"How do you know there's no look-ahead?"**

*Answer:* "Every feature is built point-in-time and every label uses the next period's RV; the look-ahead taxonomy in [Chapter 16](ch16-forecast-evaluation.md) lists each control. Purged cross-validation (also [Chapter 16](ch16-forecast-evaluation.md)) removes overlap between train and test windows."

*Backup slide:* timeline diagram of feature/label alignment and the purge/embargo windows.

**"Is this overfit --- how many things did you try?"**

*Answer:* "We logged $N$ experiments; the Deflated Sharpe Ratio (the Deflated Sharpe Ratio section of [Chapter 16](ch16-forecast-evaluation.md)) stays positive after correcting for that count. Walk-forward out-of-sample QLIKE is consistent with the cross-validation estimate."

*Backup slide:* DSR computation with the trial count and the walk-forward QLIKE series.

> **Warning: Never Say "I Don't Know" Without a Follow-Up**
>
> If you genuinely have not tested something, say: "I haven't run that specific test. My best estimate from [related analysis] is [X], and I can run it and follow up by [date]." This is honest, shows you know which test would answer the question, and commits to a deliverable. Never just say "I don't know" and move on.
