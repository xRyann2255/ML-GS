# Chapter 1: Returns, Variance, and Why Volatility Matters

> **Application: Why This Chapter**
>
> Volatility is the central quantity in quantitative finance. Options pricing, risk management, portfolio construction, and trade execution all depend on accurate volatility estimates. Every chapter in this guide builds on the concepts introduced here. All five project directions ([Chapter 17](ch17-applications-projects.md)) start from the returns and variance foundations covered in this chapter.

Financial markets produce a stream of prices. To do anything quantitative with those prices, you first need to convert them into *returns*, measure how much those returns vary, and understand *why* that variation matters. This chapter covers that ground.

## What Are Returns?

A stock price on its own tells you almost nothing about performance. Knowing that Apple closed at $187 today is useless without knowing where it closed yesterday. *Returns* solve this: they express price changes as fractions (or percentages), making different assets and time periods comparable.

To compare price movements across different assets and time periods, we need to express changes as fractions rather than absolute dollar amounts. There are two standard ways to do this.

> **Prereq: Natural Logarithm Properties**
>
> The natural logarithm $\ln(\cdot)$ is the inverse of the exponential function: $\ln(e^x) = x$. Three properties matter here:
>
> - $\ln(A/B) = \ln A - \ln B$ (quotients become differences)
> - $\ln(AB) = \ln A + \ln B$ (products become sums)
> - For small $x$: $\ln(1+x) \approx x$ (so log returns $\approx$ simple returns when returns are small)

### Simple Returns

We want a single number that tells us "what fraction of my investment did I gain or lose in one period?" The simple (arithmetic) return does exactly this:

$$R_t = \frac{P_t - P_{t-1}}{P_{t-1}}$$

- $R_t$: simple return from period $t-1$ to $t$
- $P_t$: price at the end of period $t$
- $P_{t-1}$: price at the end of the previous period

> **Intuition: In Plain English**
>
> This equation says: "take the price change (today minus yesterday) and divide by yesterday's price to get the fractional change." The result is a dimensionless number: 0.02 means a 2% gain, $-0.03$ means a 3% loss. It's the same calculation as "what percentage did my investment grow?"

> **Project Connection: Why This Matters**
>
> Returns are the raw input to everything in this project. Realized volatility is computed by summing *squared* returns, so every RV estimate you build in later chapters starts from this quantity. If you don't understand what a return measures, the entire volatility pipeline won't make sense.

A simple return of $0.05$ means the price rose by 5%.

### Log Returns

The simple return works fine in many contexts, but for volatility research we almost always use a different version: the log return. Instead of computing the fractional change directly, we take the natural logarithm of the price ratio:

$$r_t = \ln\!\left(\frac{P_t}{P_{t-1}}\right) = \ln P_t - \ln P_{t-1}$$

- $r_t$: log return from period $t-1$ to $t$
- $\ln(\cdot)$: natural logarithm

> **Intuition: In Plain English**
>
> This equation says: "take the ratio of today's price to yesterday's price, then take the natural log of that ratio." For small price changes (under ~5%), the log return is almost identical to the simple return. The reason we use it instead is purely mathematical convenience: log returns add up over time, which makes the math for volatility much cleaner.

> **Project Connection: Why This Matters**
>
> Every volatility model in this guide uses log returns as its input. When you compute realized volatility in [Chapter 2](ch02-realized-volatility.md), you will square log returns and sum them. The time-additivity property below is what makes realized volatility estimators mathematically valid.

> **Key Idea: Why Log Returns?**
>
> Log returns have two properties that make them the default in volatility research:
>
> 1. **Time additivity.** The multi-period log return is the sum of single-period log returns: $r_{1:T} = r_1 + r_2 + \cdots + r_T$.
>
>    *Why this works:* the 2-day log return is $\ln(P_2/P_0) = \ln\bigl((P_1/P_0)\cdot(P_2/P_1)\bigr) = \ln(P_1/P_0) + \ln(P_2/P_1) = r_1 + r_2$. The log property $\ln(AB) = \ln A + \ln B$ does all the work. Simple returns compound multiplicatively instead: the 2-day simple return is $(1+R_1)(1+R_2) - 1$, not $R_1 + R_2$, which makes variance formulas much more complicated.
>
> 2. **Approximate symmetry.** If you gain $+0.05$ log return and then lose $-0.05$ log return, the total is $\ln(P_{\text{final}}/P_{\text{start}}) = 0.05 + (-0.05) = 0$, meaning $P_{\text{final}} = P_{\text{start}}$ exactly. Simple returns don't cancel this way: $\$100 \times 1.05 \times 0.95 = \$99.75 \neq \$100$.
>
> Throughout this guide, $r_t$ always means the log return unless stated otherwise.

## Variance and Standard Deviation

With returns in hand, the next question is: how spread out are they? Variance answers this by measuring the average squared deviation from the mean return.

> **Prereq: Expected Value Notation**
>
> Throughout this guide, $\mathbb{E}[X]$ means the **expected value** of $X$: the long-run average you would get if you could observe $X$ infinitely many times. For example, $\mathbb{E}[r_t]$ is the average return you'd observe over an infinite number of trading days. When you see $\mathbb{E}[\cdot]$ in a formula, read it as "the average of what's inside the brackets."

> **Definition: Sample Variance and Standard Deviation**
>
> Given $T$ log returns $r_1, r_2, \ldots, r_T$ with sample mean $\bar{r} = \frac{1}{T}\sum_{t=1}^T r_t$, we want a single number that captures "how spread out are these returns?" The sample variance answers this by measuring the average squared distance of each return from the mean:
>
> $$\hat{\sigma}^2 = \frac{1}{T-1}\sum_{t=1}^{T}\bigl(r_t - \bar{r}\bigr)^2$$
>
> - $\hat{\sigma}^2$: sample variance (the hat denotes an estimate)
> - $T$: number of observations
> - $r_t$: log return at time $t$
> - $\bar{r}$: sample mean of returns
> - $T-1$: Bessel's correction (dividing by $T-1$ instead of $T$ gives an unbiased estimate)
>
> **Intuition: In Plain English**
>
> This equation says: "for each return, measure how far it is from the average return, square that distance (so negatives don't cancel positives), then average all those squared distances." A large variance means returns are spread far from the mean (volatile); a small variance means they cluster tightly around the mean (calm). Squaring is what makes this sensitive to outliers: one large move contributes disproportionately.
>
> **Project Connection: Why This Matters**
>
> Variance is the quantity you are forecasting in this entire project. Realized volatility ([Chapter 2](ch02-realized-volatility.md)) is essentially this formula applied to high-frequency returns within a single day. Every model from GARCH to deep learning is trying to predict tomorrow's version of this number.
>
> The sample standard deviation is $\hat{\sigma} = \sqrt{\hat{\sigma}^2}$.

> **Prereq: Why $T-1$?**
>
> Dividing by $T-1$ instead of $T$ corrects for the fact that you estimated $\bar{r}$ from the same data. Using $\bar{r}$ instead of the true mean $\mu$ systematically shrinks the deviations, so dividing by the smaller number $T-1$ compensates. This is called Bessel's correction. For large $T$ the difference is negligible.

### Annualizing Volatility

Raw daily standard deviations are tiny numbers (around 0.01 for a typical equity index), so practitioners report volatility on an annual scale. The key insight: if daily returns are independent, variances add. The $n$-day return is $r_1 + r_2 + \cdots + r_n$ (time additivity), and for independent random variables, $\operatorname{Var}(r_1 + r_2 + \cdots + r_n) = \operatorname{Var}(r_1) + \operatorname{Var}(r_2) + \cdots + \operatorname{Var}(r_n) = n\sigma^2$. Taking the square root: the $n$-day standard deviation is $\sqrt{n}\,\sigma$.

$$\hat{\sigma}_{\text{annual}} = \hat{\sigma}_{\text{daily}} \times \sqrt{252}$$

- $252$: approximate number of trading days per year in U.S. equity markets
- $\sqrt{252} \approx 15.87$

> **Intuition: In Plain English**
>
> This equation says: "multiply the daily volatility by about 16 to get the annual volatility." The $\sqrt{252}$ comes from the fact that if daily returns are independent, variances add over time (252 trading days), so standard deviations scale by the square root. A stock with 1% daily volatility has roughly 16% annual volatility.

> **Project Connection: Why This Matters**
>
> Practitioners quote volatility in annualized terms. When someone says "the VIX is at 20," they mean 20% annualized volatility. Your model's output (daily RV forecasts) will need to be converted to this scale for comparison with implied volatility and industry benchmarks.

> **Warning: The Square-Root-of-Time Rule**
>
> The $\sqrt{252}$ scaling assumes returns are independent and identically distributed. When volatility clusters (Section 1.4 below), this assumption fails, and multi-day volatility may be higher or lower than the square-root rule predicts. [Chapter 5](ch05-garch-family.md) and [Chapter 6](ch06-har-model.md) develop models that handle this.

## Why Volatility Matters

You now know how to compute returns and measure their spread. The next question: why does that spread matter so much? Variance and standard deviation sit at the center of four major problems in finance.

> **Prereq: Finance Concepts Preview**
>
> The following four applications are covered briefly here to motivate the rest of the guide. You do not need to understand them fully yet; each connects to a later chapter.

**Options pricing.** An option gives the holder the right (not obligation) to buy or sell an asset at a fixed price by a future date. The value of this right depends critically on how much the underlying price might move, which is volatility. The Black-Scholes model (Black and Scholes, 1973) takes volatility as an *input* and produces an option price as output. If your volatility estimate is wrong, your price is wrong. [Chapter 8](ch08-options-vol-surface.md) explores this connection.

**Risk management.** Value-at-Risk ($\operatorname{VaR}$) estimates the worst-case loss over a holding period at a given confidence level. In the simplest version, VaR is directly proportional to volatility: if volatility doubles, your risk bound roughly doubles. For a 99% daily VaR, the worst expected loss is about 2.33 times the daily volatility (e.g., if daily vol is 1%, the worst-case daily loss at 99% confidence is roughly 2.33%).

**Portfolio construction.** Mean-variance optimization (Markowitz, 1952) and risk-parity strategies both require a covariance matrix as input. Volatility is the diagonal of that matrix. Better volatility forecasts produce better-diversified portfolios.

**Trade execution.** When a desk needs to buy a large position, it splits the order over time to reduce market impact. The participation rate (fraction of daily volume per time slice) depends on intraday volatility: higher volatility means wider price swings, which changes optimal execution speed.

> **Key Idea: What Makes Volatility Special**
>
> Volatility is one of the few quantities in finance that is (a) directly observable from intraday data ([Chapter 2](ch02-realized-volatility.md)), (b) economically central to pricing, hedging, and risk control, and (c) forecastable with meaningful accuracy ([Chapter 5](ch05-garch-family.md) through [Chapter 13](ch13-hybrid-ensemble.md)). That combination makes it the right place to apply ML carefully.

> **Prereq: Preview: What Is Realized Volatility?**
>
> The central concept of this guide is **realized volatility** (RV): the sum of squared intraday returns over one day, $\text{RV}_t = \sum_{i=1}^{M} r_{t,i}^2$, where $M$ is the number of intraday observations (e.g., 78 five-minute returns per trading day). Instead of using a model to *estimate* what volatility was, RV directly *measures* it from high-frequency data. [Chapter 2](ch02-realized-volatility.md) develops this fully; for now, just know that RV gives you a daily number that tells you "how volatile was the market today," and your project's goal is to forecast tomorrow's RV given today's information.

## Stylized Facts of Financial Returns

Before building models, you need to know what patterns actually appear in return data. Cont (2001) catalogued a set of "stylized facts": statistical regularities observed across equities, foreign exchange, and commodities, across decades and geographies. Four of these facts matter most for volatility modeling.

### Fact 1: Returns Are Approximately Uncorrelated

> **Prereq: Autocorrelation**
>
> **Autocorrelation** at lag $k$ measures how correlated a time series is with itself shifted $k$ periods into the past. A value near $+1$ means "if it was high today, it will tend to be high $k$ days from now"; near $0$ means "no relationship"; near $-1$ means "high today predicts low $k$ days later." When we say "return autocorrelations are zero," we mean knowing today's return tells you nothing about tomorrow's.

Daily return autocorrelations are statistically indistinguishable from zero for lags beyond a few minutes (Cont, 2001). In plain terms: knowing today's return tells you almost nothing about tomorrow's return. This is consistent with market efficiency; if returns were predictable, traders would exploit the pattern until it disappeared.

> **Intuition: No Free Lunch in Means**
>
> If positive returns reliably followed positive returns, everyone would buy after an up day, driving the price up immediately and eliminating the pattern. Competition among traders keeps return autocorrelations near zero. Volatility, by contrast, is *not* a quantity you can directly trade on the same way, so its autocorrelation can persist.

### Fact 2: Volatility Clusters

Although returns themselves are uncorrelated, *squared* returns and *absolute* returns show strong, slowly decaying positive autocorrelation (Cont, 2001; Mandelbrot, 1963). Large moves tend to follow large moves, and calm periods tend to follow calm periods.

Engle (1982) formalized this observation with the ARCH model: the variance of next period's return depends on recent squared returns. [Chapter 5](ch05-garch-family.md) develops this family of models in detail.

> **Key Result: Cont (2001), Stylized Fact: Volatility Clustering**
>
> The autocorrelation of absolute returns remains significantly positive over lags of several weeks and decays slowly (approximately as a power law with exponent $\beta \in [0.2, 0.4]$), a pattern that is remarkably stable across asset classes and time periods.

> **Intuition: What "Power Law Decay" Means**
>
> A **power law decay** means the autocorrelation drops as $\text{lag}^{-\beta}$ --- much more slowly than exponential decay. With $\beta \approx 0.3$, the autocorrelation at lag 100 is still about $100^{-0.3} \approx 0.25$: volatility 100 days ago is still informative about today's volatility. This "long memory" is why simple models that only look at yesterday fail. The HAR model ([Chapter 6](ch06-har-model.md)) addresses this by explicitly including weekly and monthly vol averages as predictors.

*[Figure: Simulated daily log returns exhibiting volatility clustering. Calm periods have returns within $\pm 0.5\%$ (days 1--100, 221--350, 421--500); turbulent periods reach $\pm 3\%$ (days 101--220, 351--420). The clustering is visible by eye: large returns beget large returns.]*

*[Figure: Autocorrelation functions for returns and squared returns based on representative daily equity index data. Left panel (returns): all autocorrelation bars at lags 1--20 fall within $\pm 0.063$ (95% significance bands), showing no significant autocorrelation at any lag. Right panel (squared returns): autocorrelations start at 0.38 at lag 1 and decay slowly to 0.06 at lag 20, all remaining above the significance band, reflecting persistent volatility clustering.]*

### Fact 3: Fat Tails

If returns were normally distributed, a daily move of 4 standard deviations would occur about once every 63 years. In practice, moves this large happen several times per year. The return distribution has "fat tails" (also called heavy tails): extreme returns are far more frequent than a Gaussian model predicts.

Mandelbrot (1963) first documented this for cotton prices, proposing that returns follow a stable Paretian distribution rather than a Gaussian. Fama (1965) confirmed the finding for stock returns, observing leptokurtic (heavy-tailed) distributions across U.S. equities.

> **Definition: Kurtosis**
>
> We need a way to measure "how fat are the tails?" compared to a normal distribution. Kurtosis does this by looking at the fourth power of deviations (which amplifies extreme values even more than squaring):
>
> $$\kappa = \frac{\mathbb{E}\bigl[(r_t - \mu)^4\bigr]}{\bigl(\mathbb{E}\bigl[(r_t - \mu)^2\bigr]\bigr)^2}$$
>
> - $\kappa$: kurtosis
> - $\mu = \mathbb{E}[r_t]$: population mean
> - For a normal distribution, $\kappa = 3$
> - *Excess kurtosis* $= \kappa - 3$; values above zero indicate fatter tails than normal
>
> **Intuition: In Plain English**
>
> This equation says: "take each return's deviation from the mean, raise it to the 4th power (which massively amplifies outliers), average those, and normalize by the squared variance." The 4th power is the key: if extreme returns are rare (thin tails), raising them to the 4th power doesn't add much. If extreme returns are common (fat tails), the 4th power blows them up and the ratio exceeds 3. The further above 3, the fatter the tails.
>
> **Project Connection: Why This Matters**
>
> Fat tails mean that extreme vol events (crashes, spikes) are far more likely than a normal model predicts. Your vol forecasting model must handle these outliers gracefully: if you assume normality, you will systematically underestimate the risk of large moves, and your model will appear to work in calm markets but fail catastrophically during crises.
>
> Typical daily equity index returns have excess kurtosis in the range 5--10 (Cont, 2001).

Figure below illustrates fat tails with a **Q--Q (quantile-quantile) plot**. Here is how it works: sort your actual returns from smallest to largest, then ask "if these returns *were* normally distributed, what values would I expect at each position in the sorted list?" Plot the expected-if-normal values on the $x$-axis and the actual values on the $y$-axis. If the data is truly normal, expected equals actual at every point, so you get a straight diagonal line. When the dots curve away from the line at the extremes, it means the tails of your actual distribution are fatter than normal: extreme moves happen more often than the bell curve predicts.

*[Figure: Q--Q plot of representative daily equity returns against a normal distribution. The dashed diagonal is the normal reference line. The data points form a slight S-shape: both the lower tail (departing below the line, reaching $-5.8\%$ actual vs. $-3.85\%$ expected at the extreme) and the upper tail (departing above the line, reaching $+5.8\%$ actual vs. $+3.85\%$ expected at the extreme) are heavier than normal. First documented by Fama (1965), the S-shaped departure shows that extreme moves (positive and negative) occur much more often than a Gaussian model predicts.]*

> **Warning: Why Fat Tails Matter for Models**
>
> Any model that assumes normally distributed returns will underestimate the probability of large moves. This affects risk management (VaR breaches), option pricing (mispricing of out-of-the-money options), and backtesting (understating drawdowns). [Chapter 4](ch04-jumps-continuous-variation.md) and [Chapter 5](ch05-garch-family.md) introduce models that accommodate fat tails.

### Fact 4: The Leverage Effect

Negative returns tend to increase future volatility more than positive returns of the same magnitude. Black (1976) first noted this asymmetry and proposed a mechanism: when a stock price falls, the firm's equity value shrinks relative to its debt, so leverage (debt/equity) rises, making the stock riskier and more volatile.

> **Definition: Leverage Effect**
>
> The leverage effect is the negative correlation between an asset's return and changes in its subsequent volatility:
>
> $$\operatorname{Corr}(r_t,\, \sigma_{t+1}^2) < 0$$
>
> - $r_t$: return at time $t$
> - $\sigma_{t+1}^2$: conditional variance at time $t+1$
> - The negative sign means: price drops $\to$ volatility rises
>
> **Intuition: In Plain English**
>
> This equation says: "when today's return is negative (a price drop), tomorrow's volatility tends to be higher; when today's return is positive (a price rise), tomorrow's volatility tends to be lower." The relationship is asymmetric: markets get more volatile when they fall, but don't calm down as much when they rise. Think of it as "fear is louder than greed": a crash makes everyone nervous, but a rally doesn't make everyone equally calm.
>
> **Project Connection: Why This Matters**
>
> The leverage effect means your vol forecasting model should treat negative and positive returns differently. A symmetric model (basic GARCH) that treats $+2\%$ and $-2\%$ as equally informative about tomorrow's vol will systematically underpredict vol after selloffs and overpredict after rallies. This is why GJR-GARCH and EGARCH ([Chapter 5](ch05-garch-family.md)) add an asymmetry term, and why it often improves forecast accuracy.

In equity markets, the leverage effect is pronounced. In foreign exchange and commodity markets, the asymmetry is weaker or sometimes reversed (Cont, 2001). [Chapter 5](ch05-garch-family.md) introduces GJR-GARCH and EGARCH models that capture this asymmetry directly.

### Summary of Stylized Facts

> **Key Idea: Four Facts That Shape Every Volatility Model**
>
> 1. **Uncorrelated returns:** tomorrow's return direction is unpredictable from today's.
> 2. **Volatility clustering:** large moves follow large moves, small follow small.
> 3. **Fat tails:** extreme returns occur far more often than a Gaussian model predicts.
> 4. **Leverage effect:** negative returns raise future volatility more than positive returns.
>
> Any useful volatility model must reproduce (at minimum) facts 2 and 3. A good model also captures fact 4.

## Conditional vs. Unconditional Volatility

Everything so far has treated volatility as a single number: the standard deviation of the full return sample. That number is the *unconditional* volatility. It answers the question "what is the typical size of a daily return, averaging over all market conditions?"

Traders need a different answer: given what has happened up to today, how volatile will the market be *tomorrow*? That is the *conditional* volatility.

> **Definition: Unconditional vs. Conditional Variance**
>
> **Unconditional variance:**
>
> $$\sigma^2 = \operatorname{Var}(r_t)$$
>
> A single number, constant over time. It is the long-run average variance.
>
> **Conditional variance:**
>
> $$\sigma_t^2 = \operatorname{Var}(r_t \mid \mathcal{F}_{t-1})$$
>
> - $\sigma_t^2$: variance of the return at time $t$, conditional on past information
> - $\mathcal{F}_{t-1}$: the **information set** available at time $t-1$. Read this as "everything you could possibly know as of yesterday": all past returns, prices, volumes, news, and any other observable data up through time $t-1$. The fancy script-$\mathcal{F}$ notation comes from probability theory (where it is called a "filtration"); all it means in practice is "given what we knew yesterday." This notation appears throughout the entire guide whenever a quantity is conditioned on past information.
>
> The conditional variance changes from day to day as new information arrives.

> **Intuition: Weather Analogy**
>
> Unconditional volatility is like the average annual rainfall for your city: a useful summary, but it does not tell you whether to carry an umbrella tomorrow. Conditional volatility is the weather forecast: it uses recent data (yesterday's pressure, today's cloud cover) to predict tomorrow's conditions. This guide is about building the forecast, not computing the average.

> **Project Connection: Why This Matters**
>
> Your entire project is about forecasting *conditional* variance: given everything you know up to today, what will volatility be tomorrow? The unconditional variance is just a naive baseline (always predict the long-run average). Every model you build, from HAR to neural networks, is trying to produce a better estimate of $\sigma_t^2$ than that naive baseline by using the information in $\mathcal{F}_{t-1}$.

The unconditional variance and conditional variance are connected by a standard probability result called the **law of total variance**. You do not need to derive it; just understand what it says about how the long-run average relates to the time-varying quantity:

$$\sigma^2 = \mathbb{E}[\sigma_t^2] + \operatorname{Var}\bigl(\mathbb{E}[r_t \mid \mathcal{F}_{t-1}]\bigr)$$

- $\mathbb{E}[\sigma_t^2]$: average of the conditional variances over time
- $\operatorname{Var}\bigl(\mathbb{E}[r_t \mid \mathcal{F}_{t-1}]\bigr)$: variance of the conditional mean (small for equities, since expected returns are nearly constant at daily frequency)

> **Intuition: In Plain English**
>
> This equation says: "the long-run average variance equals the average of all the daily conditional variances, plus a small correction for the fact that expected returns also fluctuate slightly." For equities at daily frequency, the second term is negligible because expected returns barely change day to day. So in practice: the unconditional variance is just what you get if you average all the conditional variances over a long period.

> **Project Connection: Why This Matters**
>
> This equation tells you that the long-run average vol is a meaningful "anchor" for your forecasts. Many models (GARCH, HAR) build in mean-reversion: after a vol spike, forecasts should gradually drift back toward this long-run level. If your model's forecasts don't average out to something close to the unconditional variance over long horizons, something is likely wrong.

When the conditional mean is approximately constant (a reasonable assumption for daily equity returns), the unconditional variance is simply the time average of the conditional variances. The gap between the two is what makes volatility modeling interesting.

*[Figure: Conditional vs. unconditional volatility over 250 trading days. The unconditional volatility (dashed red line) sits flat at 17% annualized throughout. The conditional volatility (solid blue line) starts around 14%, drifts down to a calm regime near 10--11% around day 50, then spikes sharply up to a crisis peak of 41% around day 100, before mean-reverting back down to roughly 12--15% for the remainder of the sample. The gap between the two lines illustrates the forecasting opportunity: knowing which regime you are in today dramatically changes the prediction for tomorrow.]*

> **Key Idea: The Central Goal of This Guide**
>
> The goal of every model in [Chapter 5](ch05-garch-family.md) through [Chapter 13](ch13-hybrid-ensemble.md) is to produce accurate estimates of the conditional variance $\sigma_t^2$. [Chapter 2](ch02-realized-volatility.md) shows how to measure the realized conditional variance from high-frequency data. [Chapter 5](ch05-garch-family.md) through [Chapter 13](ch13-hybrid-ensemble.md) show how to forecast it. [Chapter 16](ch16-forecast-evaluation.md) shows how to tell whether your forecasts are any good.

## Summary

- **Returns** convert raw prices into comparable, analyzable quantities. Log returns ($r_t = \ln P_t - \ln P_{t-1}$) are preferred because they are additive over time.

- **Simple vs. log returns** are nearly identical for small magnitudes (daily equities); they diverge for large moves.

- **Sample variance** ($\hat{\sigma}^2$) measures dispersion around the mean return; standard deviation ($\hat{\sigma}$) is its square root.

- **Annualized volatility** scales daily volatility by $\sqrt{252}$, assuming independent returns.

- **Volatility matters** because it is a direct input to options pricing, risk management (VaR), portfolio optimization, and trade execution.

- **Stylized fact 1:** Returns are approximately uncorrelated (no predictability in the mean).

- **Stylized fact 2:** Squared and absolute returns are strongly autocorrelated (volatility clusters).

- **Stylized fact 3:** Return distributions have fat tails (excess kurtosis of 5--10 for daily equity returns).

- **Stylized fact 4:** The leverage effect makes volatility respond asymmetrically to negative vs. positive returns.

- The **unconditional** variance is a single long-run number; the **conditional** variance $\sigma_t^2$ varies over time and is what we want to forecast.

- The **central goal** of this guide is to estimate and forecast the conditional variance $\sigma_t^2$ using both classical and ML methods.

- Cont (2001) provides the canonical reference for stylized facts across asset classes.

- Mandelbrot (1963) and Fama (1965) established that financial returns have fat tails, not Gaussian distributions.

- Engle (1982) introduced ARCH, the first formal model of time-varying conditional variance, covered in [Chapter 5](ch05-garch-family.md).

## Key Results

| Paper | Result | Relevance |
|---|---|---|
| Mandelbrot (1963) | Daily commodity returns follow a stable Paretian (fat-tailed) distribution, not Gaussian; sample variance does not converge. | First evidence that normal-distribution assumptions fail for financial data. |
| Fama (1965) | Confirmed fat tails (leptokurtosis) in daily U.S. stock returns via S-shaped Q--Q departures from normality. | Extended Mandelbrot's finding to equities; supported the stable distribution hypothesis. |
| Black (1976) | Documented negative correlation between stock returns and subsequent volatility changes (the leverage effect). | Motivates asymmetric volatility models (GJR-GARCH, EGARCH) in [Chapter 5](ch05-garch-family.md). |
| Engle (1982) | Introduced ARCH: conditional variance is a function of past squared residuals; applied to UK inflation. | Founded the entire field of conditional volatility modeling ([Chapter 5](ch05-garch-family.md)). |
| Cont (2001) | Canonical enumeration of stylized facts (absence of return autocorrelation, volatility clustering with slow power-law decay, fat tails, leverage effect) across equities, FX, and commodities. | Benchmark reference for the empirical properties any volatility model must match. |
