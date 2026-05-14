# The HAR Model and Its Extensions

> **Application: Why This Chapter**
> HAR is THE benchmark for volatility forecasting.
> Every ML model in Chapters [11](ch11-tree-methods-vol.md)--[13](ch13-hybrid-ensemble.md) must beat HAR to justify its complexity.
> This chapter must be crystal clear because every subsequent forecasting chapter references it.
> Projects 1, 4, and 5 all use HAR variants as their primary baseline.

[Chapter 5](ch05-garch-family.md) forecast volatility using only daily returns.
That approach works when intraday data is unavailable, but it uses a noisy proxy ($r^2_t$) for what actually happened during the day.
[Chapter 2](ch02-realized-volatility.md) showed that realized variance $\operatorname{RV}_t = \sum r^2_{t,i}$, computed from intraday returns, is a far more precise measure of daily volatility.
The natural next question: can you forecast tomorrow's $\operatorname{RV}$ directly from past $\operatorname{RV}$ values, without the latent-variable machinery of GARCH?

The answer is yes, and the model that does it is remarkably simple: three OLS coefficients.


## The Heterogeneous Market Hypothesis

> **Prereq: Mean Reversion**
> A quantity *mean-reverts* if it tends to return to a long-run average after being pushed away.
> If today's value is unusually high, mean reversion says tomorrow's value is more likely to be lower (and vice versa).
> The speed of mean reversion determines how long departures persist.

Start with an observation about who trades in financial markets.
Not everyone operates at the same frequency.
Day traders react to what happened in the last few hours.
Portfolio managers at mutual funds or pension funds rebalance weekly.
Large institutional allocators (sovereign wealth funds, endowments) adjust positions monthly or quarterly.

Each type of participant pays attention to volatility at their own characteristic horizon.
A day trader cares about yesterday's realized volatility.
A weekly rebalancer looks at the average volatility over the past week.
A monthly allocator responds to the volatility level over the past month.

Muller et al. (1993) formalized this as the *Heterogeneous Market Hypothesis* (HMH): the market is a superposition of participants operating at different time scales, and these participants interact.
When monthly allocators adjust positions, it creates volatility that daily traders react to, and vice versa.

> **Intuition: Three Clocks Running Simultaneously**
> Imagine three clocks ticking at different speeds.
> Clock 1 (daily) ticks every day and captures fast-moving volatility reactions: earnings surprises, Fed announcements, flash crashes.
> Clock 2 (weekly) ticks every week and captures medium-term dynamics: multi-day volatility clusters, the weekly options expiration cycle.
> Clock 3 (monthly) ticks every month and captures the slow-moving background volatility level: business-cycle shifts, prolonged risk-on/risk-off regimes.
> Observed volatility is a mixture of all three clocks.
> The HAR model puts one predictor per clock.

Figure 1 below illustrates how the three participant types feed into observed market volatility.

```mermaid
flowchart TD
    DT["Daily Traders\nhorizon: 1 day"]
    WR["Weekly Rebalancers\nhorizon: 1 week"]
    MA["Monthly Allocators\nhorizon: 1 month"]

    DRV["watches RV_(t-1)"]
    WRV["watches RV^(w)_(t-1)"]
    MRV["watches RV^(m)_(t-1)"]

    MKT["Observed Market\nVolatility RV_t"]

    DT --> DRV
    WR --> WRV
    MA --> MRV

    DRV --> MKT
    WRV --> MKT
    MRV --> MKT

    MKT -.->|feedback| DT
    MKT -.->|feedback| MA
```

*Figure 1: The Heterogeneous Market Hypothesis. Three types of market participants operate at different horizons, each responding to volatility averaged over their characteristic time scale. Their collective actions produce the observed realized volatility. Dashed arrows indicate feedback: today's volatility feeds back into each participant's future decisions.*

> **Key Idea: Why This Matters for Forecasting**
> If the market were homogeneous (all participants on the same clock), a simple AR(1) model would suffice.
> The heterogeneity means that volatility dynamics involve multiple time scales simultaneously.
> You need a model that captures daily, weekly, and monthly persistence in a single equation.
> That model is HAR.


## The HAR Model

> **Prereq: OLS Regression**
> Ordinary Least Squares (OLS) fits a linear equation $y = \beta_0 + \beta_1 x_1 + \cdots + \beta_k x_k + \varepsilon$ by choosing $\beta_0, \ldots, \beta_k$ to minimize the sum of squared residuals $\sum \varepsilon^2_t$.
> The resulting coefficients are the best linear unbiased estimators under standard assumptions (Gauss--Markov theorem).
> If you can set up a forecasting problem as a linear regression, OLS gives you the answer.

The insight from the previous section suggests three predictors: yesterday's $\operatorname{RV}$, the average $\operatorname{RV}$ over the past week, and the average $\operatorname{RV}$ over the past month.
Corsi (2009) turned this directly into a regression.
The key move is defining the weekly and monthly averages.

> **Definition: Weekly and Monthly Realized Variance**
> The weekly average realized variance on day $t$ is:
> $$\operatorname{RV}^{(w)}_{t} = \frac{1}{5}\sum_{i=0}^{4}\operatorname{RV}_{t-i}$$
> The monthly average realized variance on day $t$ is:
> $$\operatorname{RV}^{(m)}_{t} = \frac{1}{22}\sum_{i=0}^{21}\operatorname{RV}_{t-i}$$
> - $\operatorname{RV}^{(w)}_{t}$: the arithmetic mean of the five most recent daily realized variances (including today)
> - $\operatorname{RV}^{(m)}_{t}$: the arithmetic mean of the 22 most recent daily realized variances (including today)
> - 5 trading days = 1 week; 22 trading days $\approx$ 1 month
> - These are backward-looking averages, not forecasts

> **Intuition: In Plain English**
> These are just moving averages of past volatility over two different windows.
> $\operatorname{RV}^{(w)}$ smooths out the last five days to give a "medium-term" volatility reading, and $\operatorname{RV}^{(m)}$ smooths over the last 22 days to give a "long-term" reading.
> The daily value captures what happened yesterday; the averages capture what has been happening recently and over the past month.

> **Project Connection: Why This Matters**
> When you build your feature matrix for any ML model, you will always include these three inputs: daily, weekly average, and monthly average RV.
> They are the core HAR features, and every extension in this chapter simply adds to them.

Now the model.
The idea is as simple as it sounds: regress tomorrow's realized variance on yesterday's daily, weekly, and monthly values.

> **Definition: The HAR-RV Model (Corsi, 2009)**
> $$\operatorname{RV}_{t+1} = \beta_0 + \beta_d \, \operatorname{RV}_{t} + \beta_w \, \operatorname{RV}^{(w)}_{t} + \beta_m \, \operatorname{RV}^{(m)}_{t} + \varepsilon_{t+1}$$
> - $\operatorname{RV}_{t+1}$: tomorrow's realized variance (the target you are forecasting)
> - $\beta_0$: intercept, related to the long-run average level of $\operatorname{RV}$
> - $\beta_d$: coefficient on yesterday's daily $\operatorname{RV}$; captures the short-term reaction
> - $\operatorname{RV}_t$: yesterday's realized variance
> - $\beta_w$: coefficient on the weekly average; captures medium-term persistence
> - $\operatorname{RV}^{(w)}_{t}$: average of the five most recent daily $\operatorname{RV}$ values
> - $\beta_m$: coefficient on the monthly average; captures long-term persistence
> - $\operatorname{RV}^{(m)}_{t}$: average of the 22 most recent daily $\operatorname{RV}$ values
> - $\varepsilon_{t+1}$: forecast error
>
> Estimation: OLS.
> No maximum likelihood, no iterative optimization, no latent variables.

> **Intuition: HAR Mimics Long Memory with Three Coefficients**
> Volatility autocorrelations decay slowly ([Chapter 5](ch05-garch-family.md), FIGARCH section).
> A pure AR model would need many lags to capture this.
> HAR achieves the same effect with a trick: the weekly average $\operatorname{RV}^{(w)}$ implicitly includes lags 1 through 5, and the monthly average $\operatorname{RV}^{(m)}$ implicitly includes lags 1 through 22.
> Three coefficients, but through the averages, information from 22 past days enters the forecast.
> The result is autocorrelation decay that closely approximates a long-memory process, with none of the estimation complexity of FIGARCH (Corsi, 2009).

> **Project Connection: Why This Matters**
> HAR is YOUR primary baseline.
> Every ML model you build must beat HAR to be worth anything.
> It predicts tomorrow's vol from a weighted combination of yesterday's vol, last week's average vol, and last month's average vol.
> When you report results, your first table column is always HAR.

> **Warning: Log or Level?**
> Many papers estimate HAR on $\ln(\operatorname{RV})$ rather than $\operatorname{RV}$ in levels.
> As noted in [Chapter 2](ch02-realized-volatility.md), $\ln(\operatorname{RV}_t)$ is approximately Gaussian, which makes OLS residuals better behaved and guarantees positive forecasts (since $e^x > 0$).
> The log specification generally forecasts better.
> Throughout this chapter, all equations are written in levels for clarity; in practice, use logs unless you have a specific reason not to.

### Typical Coefficient Values

What do the coefficients look like on real data?
Corsi (2009) calibrates the HAR simulation with $\beta_d = 0.36$, $\beta_w = 0.28$, $\beta_m = 0.28$, values chosen to produce realistic dynamics; the empirical estimates on S&P 500 futures (1990--2007) are $\beta_d \approx 0.37$, $\beta_w \approx 0.34$, $\beta_m \approx 0.22$.
All three components contribute meaningfully.
The monthly term's coefficient is similar to the daily term's, confirming that long-horizon persistence matters.

The in-sample $R^2$ is typically 0.40--0.60 for daily-horizon forecasts on equity index $\operatorname{RV}$.
This is high for a financial time series, and it comes from just three predictors.

Figure 2 below summarizes the HAR cascade: how the three components at different time scales feed into a single forecast.

```mermaid
flowchart LR
    D["**Daily** RV_t\nlag 1 day"]
    W["**Weekly** RV^(w)_t\navg. of lags 1-5"]
    M["**Monthly** RV^(m)_t\navg. of lags 1-22"]

    BD["x β_d ≈ 0.36"]
    BW["x β_w ≈ 0.28"]
    BM["x β_m ≈ 0.28"]

    SUM["Σ + β_0"]
    FC["**Forecast**\nRV-hat_(t+1)"]

    D --> BD
    W --> BW
    M --> BM

    BD --> SUM
    BW --> SUM
    BM --> SUM

    SUM --> FC
```

*Figure 2: The HAR cascade. Three components at daily, weekly, and monthly time scales are weighted by OLS coefficients and summed to produce the forecast. Through the weekly and monthly averages, information from 22 past days enters the model with only three coefficients, approximating long-memory decay. Typical coefficient values are from Corsi (2009) on S&P 500 data.*


## HAR-J and HAR-CJ: Adding Jumps

The basic HAR uses total realized variance $\operatorname{RV}_t$ as the predictor.
But as discussed in [Chapter 2](ch02-realized-volatility.md), $\operatorname{RV}$ captures both the continuous component of price variation and any jumps that occurred during the day.
A natural question: do jumps and continuous variation have different forecasting power?

> **Prereq: Bipower Variation**
> *Bipower variation* (BPV) is an estimator of integrated variance that is robust to jumps.
> It is defined as:
> $$\operatorname{BPV}_t = \frac{\pi}{2} \sum_{i=2}^{n} |r_{t,i}|\,|r_{t,i-1}|$$
> - $|r_{t,i}|$: absolute value of the $i$-th intraday return
> - The product of consecutive absolute returns averages out jump contributions because it is unlikely that two consecutive intervals both contain a jump
> - $\pi/2$: a scaling constant that ensures $\operatorname{BPV}_t$ converges to integrated variance $\operatorname{IV}_t$ (not quadratic variation) as sampling frequency increases
>
> The key property: $\operatorname{BPV}_t \to \operatorname{IV}_t$ even when jumps are present, whereas $\operatorname{RV}_t \to \operatorname{IV}_t + \sum(\text{jumps})^2$.
> The difference $\operatorname{RV}_t - \operatorname{BPV}_t$ therefore isolates the jump component.
> BPV was introduced by Barndorff-Nielsen and Shephard (2004) and is covered in detail in [Chapter 4](ch04-jumps-continuous-variation.md).

> **Intuition: In Plain English**
> BPV estimates the "smooth" part of volatility by multiplying consecutive absolute returns together.
> The idea is that a genuine jump is a one-off spike that is unlikely to hit two adjacent intervals, so the product of neighbors filters jumps out while keeping the continuous volatility signal.

> **Project Connection: Why This Matters**
> BPV is the tool you use to separate continuous volatility from jumps when constructing features for HAR-J and HAR-CJ.
> If your data source provides intraday returns, computing BPV alongside RV gives you a richer feature set at zero additional model complexity.

### HAR-J

Andersen, Bollerslev, and Diebold (2007) proposed the HAR-J model, which adds a jump component as an additional predictor:

$$\operatorname{RV}_{t+1} = \beta_0 + \beta_d \, \operatorname{RV}_{t} + \beta_w \, \operatorname{RV}^{(w)}_{t} + \beta_m \, \operatorname{RV}^{(m)}_{t} + \beta_J \, J_t + \varepsilon_{t+1}$$

- $J_t = \max(\operatorname{RV}_t - \operatorname{BPV}_t, 0)$: the estimated jump component on day $t$; the $\max$ ensures non-negativity, since measurement error can make $\operatorname{RV}_t - \operatorname{BPV}_t$ slightly negative even on jumpless days
- $\beta_J$: coefficient on jumps; typically estimated as negative and small, meaning jumps have a weak or transient effect on future volatility
- All other terms are the same as in the HAR-RV equation

> **Intuition: In Plain English**
> HAR-J takes the standard HAR and adds one extra input: how much of yesterday's volatility came from jumps (sudden price spikes) rather than normal trading.
> If yesterday had a big jump, the model can treat that spike differently from steady high volatility, because jumps tend not to repeat.

> **Project Connection: Why This Matters**
> HAR-J adds the jump component as a separate feature.
> The continuous component is more persistent and predictable than jumps, so letting the model see them separately improves forecasts.
> In your ML pipeline, $J_t = \max(\operatorname{RV}_t - \operatorname{BPV}_t, 0)$ is a feature you should always compute when you have intraday data.

> **Key Result: Andersen, Bollerslev, and Diebold (2007) -- Jumps Matter Less Than You Expect**
> Andersen, Bollerslev, and Diebold (2007) find that the jump component $J_t$ is statistically significant but economically small in forecasting next-day $\operatorname{RV}$.
> Most of the predictive power comes from the continuous component.
> Jumps are largely transient: a jump on day $t$ does not meaningfully raise volatility on day $t+1$.

### HAR-CJ

Corsi, Pirino, and Reno (2010) take the separation further with the HAR-CJ model, which replaces total $\operatorname{RV}$ with the continuous and jump components at all three horizons:

$$\operatorname{RV}_{t+1} = \beta_0 + \beta^C_d C_t + \beta^C_w C^{(w)}_t + \beta^C_m C^{(m)}_t + \beta^J_d J_t + \beta^J_w J^{(w)}_t + \beta^J_m J^{(m)}_t + \varepsilon_{t+1}$$

- $C_t = \operatorname{BPV}_t$: the continuous component of day $t$'s variation
- $J_t = \max(\operatorname{RV}_t - \operatorname{BPV}_t, 0)$: the jump component of day $t$
- $C^{(w)}_t, C^{(m)}_t$: weekly and monthly averages of the continuous component, constructed like $\operatorname{RV}^{(w)}$ and $\operatorname{RV}^{(m)}$
- $J^{(w)}_t, J^{(m)}_t$: weekly and monthly averages of the jump component

The HAR-CJ model has six slope coefficients instead of three.
The empirical finding is consistent with HAR-J: continuous coefficients ($\beta^C$) are large and significant; jump coefficients ($\beta^J$) are small and often insignificant at weekly and monthly horizons (Corsi, Pirino, and Reno, 2010).

> **Intuition: In Plain English**
> HAR-CJ goes further than HAR-J by building separate daily, weekly, and monthly averages for the continuous part and the jump part.
> Instead of asking "how volatile was the market?" at each horizon, it asks two questions: "how volatile was the smooth trading activity?" and "how big were the jumps?"
> The consistent finding is that only the continuous answers matter for forecasting; the jump answers contribute almost nothing beyond the daily horizon.

> **Project Connection: Why This Matters**
> HAR-CJ gives you six features instead of three: $C_t, C^{(w)}_t, C^{(m)}_t, J_t, J^{(w)}_t, J^{(m)}_t$.
> When you feed these to an ML model, the model can learn that continuous components carry the forecasting signal and jumps are noise, rather than you having to hard-code that decision.

> **Key Idea: Jumps Are Noise for Forecasting**
> A large jump (e.g., from a surprise rate cut) spikes today's $\operatorname{RV}$ but typically does not persist into tomorrow.
> The continuous component, which reflects the background level of trading activity and uncertainty, is far more persistent and forecastable.
> This is why separating $C$ from $J$ can help: it prevents a one-day spike from inflating the forecast.

Figure 3 below shows how HAR-CJ decomposes realized variance before forecasting, compared to the standard HAR approach.

```mermaid
flowchart TD
    subgraph HAR
        RV["RV_t"]
        RVW["RV^(w)_t"]
        RVM["RV^(m)_t"]
        FC1["RV-hat_(t+1)"]
        RV --> FC1
        RVW --> FC1
        RVM --> FC1
    end

    subgraph HAR-CJ
        CD["C_t (continuous)"]
        CW["C^(w)_t"]
        CM["C^(m)_t"]
        JD["J_t (jump)"]
        JW["J^(w)_t"]
        JM["J^(m)_t"]
        FC2["RV-hat_(t+1)"]
        CD -->|strong signal| FC2
        CW -->|strong signal| FC2
        CM -->|strong signal| FC2
        JD -.->|weak signal| FC2
        JW -.->|weak signal| FC2
        JM -.->|weak signal| FC2
    end
```

*Figure 3: HAR vs. HAR-CJ. HAR feeds total RV at three horizons into the forecast (left). HAR-CJ first decomposes RV into continuous and jump components at each horizon (right). Thick arrows indicate strong forecasting power from continuous components; dashed arrows indicate the weak contribution of jumps.*


## SHAR: Good Volatility, Bad Volatility

HAR and its jump extensions treat all returns symmetrically: a large up move and a large down move both increase $\operatorname{RV}$ by the same amount (both $r^2$ terms are positive).
But [Chapter 5](ch05-garch-family.md) documented the leverage effect: negative returns increase volatility more than positive returns of the same magnitude.
Can you bring this asymmetry into the HAR framework?

> **Prereq: Realized Semivariance**
> *Realized semivariance* decomposes realized variance into contributions from positive and negative intraday returns:
> $$RS^+_t = \sum_{i=1}^{n} r^2_{t,i} \, \mathbf{1}_{\{r_{t,i} > 0\}}, \qquad RS^-_t = \sum_{i=1}^{n} r^2_{t,i} \, \mathbf{1}_{\{r_{t,i} < 0\}}$$
> - $RS^+_t$: positive semivariance, the sum of squared positive intraday returns
> - $RS^-_t$: negative semivariance, the sum of squared negative intraday returns
> - $\mathbf{1}_{\{r_{t,i} > 0\}}$: indicator function, equal to 1 if $r_{t,i} > 0$
> - $RS^+_t + RS^-_t = \operatorname{RV}_t$: the two halves sum to total realized variance

> **Intuition: In Plain English**
> Realized semivariance splits total volatility into "upside choppiness" and "downside choppiness."
> $RS^+$ measures how much the price bounced around on the way up during the day, while $RS^-$ measures how much it bounced around on the way down.
> Together they add up to total RV, but they carry different information about what comes next.

> **Key Result: Patton and Sheppard (2015) -- Bad Volatility Is More Persistent**
> Decomposing realized variance into positive semivariance $RS^+$ and negative semivariance $RS^-$ substantially improves forecasts.
> Bad volatility ($RS^-$, from downward price moves) is significantly more persistent than good volatility ($RS^+$, from upward moves).

The SHAR (Semivariance HAR) model replaces the daily $\operatorname{RV}$ term with $RS^+$ and $RS^-$:

$$\operatorname{RV}_{t+1} = \beta_0 + \beta^+_d \, RS^+_t + \beta^-_d \, RS^-_t + \beta_w \, \operatorname{RV}^{(w)}_t + \beta_m \, \operatorname{RV}^{(m)}_t + \varepsilon_{t+1}$$

- $RS^+_t$: yesterday's positive semivariance ("good" volatility)
- $RS^-_t$: yesterday's negative semivariance ("bad" volatility)
- $\beta^-_d > \beta^+_d$ is the typical finding: negative semivariance has a larger coefficient, meaning bad volatility predicts more future volatility
- The weekly and monthly components remain as total $\operatorname{RV}$ averages

> **Intuition: Why Downward Moves Are More Informative**
> Consider two days with identical $\operatorname{RV} = 2 \times 10^{-4}$.
> On Day A, most of the variation came from upward moves ($RS^+ = 1.6$, $RS^- = 0.4$): a rally day with choppy upward movement.
> On Day B, most came from downward moves ($RS^+ = 0.4$, $RS^- = 1.6$): a selloff with persistent downward pressure.
>
> Day B predicts higher future volatility.
> Why?
> Selloffs trigger margin calls, portfolio insurance rebalancing, stop-loss orders, and panic selling, all of which generate additional volatility.
> Rallies of the same magnitude do not create the same cascading effects.
> This asymmetry is the leverage effect operating at the intraday level.

> **Project Connection: Why This Matters**
> SHAR treats positive and negative semivariance differently, capturing the leverage effect within the HAR framework.
> For your project, $RS^+_t$ and $RS^-_t$ are two features that replace the single $\operatorname{RV}_t$ feature, and an ML model can learn the asymmetry automatically.
> SHAR is a strong baseline when forecasting equity index volatility, where the leverage effect is most pronounced.

Patton and Sheppard (2015) show that SHAR improves forecast accuracy relative to HAR across multiple asset classes, with the largest gains on equity indices where the leverage effect is strongest.


## HARQ: Handling Measurement Error

All the models so far treat every day's $\operatorname{RV}_t$ as equally reliable.
But it is not.
[Chapter 2](ch02-realized-volatility.md) showed that $\operatorname{RV}$ is an *estimate* of integrated variance, subject to estimation error that depends on how volatile volatility was during the day.

> **Prereq: Realized Quarticity**
> The precision of realized variance as an estimator of integrated variance depends on the *integrated quarticity*, the integral of $\sigma^4_s$ over the day (see the RV CLT in [Chapter 2](ch02-realized-volatility.md)).
> Realized quarticity ($RQ_t$) is a consistent estimator of this quantity:
> $$RQ_t = \frac{n}{3} \sum_{i=1}^{n} r^4_{t,i}$$
> - $r^4_{t,i}$: the fourth power of the $i$-th intraday return
> - $n/3$: a scaling constant that ensures consistency
> - High $RQ_t$ means that volatility itself was volatile during the day, making $\operatorname{RV}_t$ a noisy estimate of $\operatorname{IV}_t$
> - Low $RQ_t$ means volatility was stable, making $\operatorname{RV}_t$ precise

> **Intuition: In Plain English**
> Realized quarticity measures how much volatility itself jumped around during the day.
> If intraday volatility was steady, fourth powers of returns are small and $RQ$ is low, meaning your RV estimate is trustworthy.
> If intraday volatility spiked wildly (e.g., a flash crash followed by a recovery), $RQ$ is high, meaning your RV number is noisy and should be taken with a grain of salt.

> **Project Connection: Why This Matters**
> $RQ_t$ is the key ingredient that separates HARQ from plain HAR.
> When you compute your daily features, always compute $\sqrt{RQ_t}$ alongside $\operatorname{RV}_t$.
> It tells your model how much to trust yesterday's volatility reading, which is the core insight behind the HARQ paper your project builds on (Bollerslev, Patton, and Quaedvlieg, 2016).

The idea behind HARQ is simple: when yesterday's $\operatorname{RV}$ is noisy (high $RQ$), the model should rely less on it.
When it is precise (low $RQ$), the model should rely more on it.

> **Key Result: Bollerslev, Patton, and Quaedvlieg (2016) -- HARQ Adjusts for Measurement Error**
> Bollerslev, Patton, and Quaedvlieg (2016) allow the daily coefficient in the HAR model to vary with realized quarticity $RQ_t$.
> On noisy days (high $RQ$), the daily $\operatorname{RV}$ coefficient shrinks toward zero, down-weighting the unreliable estimate.
> On precise days (low $RQ$), the coefficient is large, fully exploiting the signal.
> This simple modification produces statistically significant forecast improvements.

$$\operatorname{RV}_{t+1} = \beta_0 + \bigl(\beta_d + \beta_{dQ}\sqrt{RQ_t}\bigr)\,\operatorname{RV}_t + \beta_w \, \operatorname{RV}^{(w)}_t + \beta_m \, \operatorname{RV}^{(m)}_t + \varepsilon_{t+1}$$

- $\beta_d$: baseline daily coefficient (the coefficient when $RQ_t = 0$, i.e., the hypothetical noise-free case)
- $\beta_{dQ}$: the adjustment coefficient; typically estimated as negative
- $\sqrt{RQ_t}$: square root of realized quarticity, a measure of how noisy $\operatorname{RV}_t$ is as an estimate
- $\beta_d + \beta_{dQ}\sqrt{RQ_t}$: the effective daily coefficient, which varies from day to day
- When $RQ_t$ is large (noisy day), $\beta_{dQ}\sqrt{RQ_t}$ is a large negative number, shrinking the effective coefficient toward zero
- When $RQ_t$ is small (precise day), the adjustment is negligible and the coefficient stays near $\beta_d$

> **Intuition: In Plain English**
> HARQ adds estimation uncertainty as a feature.
> On days when yesterday's RV estimate is noisy (high $RQ$), the model automatically relies less on it and shifts weight to the more stable weekly and monthly averages.
> On days when yesterday's RV is precise (low $RQ$), the model trusts it fully.
> It is a "confidence-weighted" version of HAR.

> **Project Connection: Why This Matters**
> HARQ is THE paper your project builds on.
> The idea that measurement quality should modulate how much weight the model gives to each input is exactly the kind of structure an ML model can generalize.
> Your project explores whether tree ensembles or neural networks can learn this adaptive weighting from data, potentially extending it to weekly and monthly coefficients or to other noise proxies beyond $RQ$.

The following diagram shows how the effective daily coefficient changes with measurement noise.

*[Figure: HARQ adaptive coefficient. The effective daily coefficient $\beta_d + \beta_{dQ}\sqrt{RQ_t}$ is plotted against $\sqrt{RQ_t}$ (measurement noise) over the range 0 to 5. The line starts near 0.40 when $\sqrt{RQ_t} = 0$ (precise day: rely on $\operatorname{RV}_t$) and decreases linearly to near 0 as noise increases (noisy day: down-weight $\operatorname{RV}_t$). A green dot marks an example precise day at approximately (0.5, 0.355) and a red dot marks an example noisy day at approximately (4.0, 0.04). Using $\beta_d = 0.40$, $\beta_{dQ} = -0.09$.]*

> **Key Idea: HARQ Is the Strongest Univariate RV Forecast**
> Among models that use only past RV and its measurement-error statistics, HARQ is the strongest in the literature (Bollerslev, Patton, and Quaedvlieg, 2016).
> It is the bar that any ML model must clear.
> If your tree ensemble or neural network cannot beat HARQ on out-of-sample $\operatorname{QLIKE}$ ([Chapter 16](ch16-forecast-evaluation.md)), you have not learned useful nonlinear structure; you have likely overfit.

> **Warning: HARQ Needs Realized Quarticity**
> HARQ requires computing $RQ_t$ from intraday returns.
> If your data source provides only daily $\operatorname{RV}$ without the underlying intraday returns, you cannot construct $RQ_t$ and HARQ is not available.
> In that case, fall back to SHAR or plain HAR as your benchmark.


## HAR-X and Beyond: Adding Exogenous Predictors

All HAR variants so far use only past $\operatorname{RV}$ (and its decompositions) as predictors.
But other variables contain information about future volatility: the VIX, lagged signed returns, macroeconomic indicators, trading volume, options-implied information.
The HAR-X framework adds these as extra regressors.

> **Definition: HAR-X**
> $$\operatorname{RV}_{t+1} = \beta_0 + \beta_d \, \operatorname{RV}_t + \beta_w \, \operatorname{RV}^{(w)}_t + \beta_m \, \operatorname{RV}^{(m)}_t + \sum_{j=1}^{p} \gamma_j \, X_{j,t} + \varepsilon_{t+1}$$
> - $X_{j,t}$: the $j$-th exogenous predictor observed on day $t$
> - $\gamma_j$: coefficient on the $j$-th predictor
> - $p$: number of exogenous predictors
> - Common choices for $X_{j,t}$: VIX level, VIX innovations ($\Delta$VIX), lagged daily return $r_t$ (signed, to capture leverage), overnight return, trading volume, implied--realized volatility spread

> **Intuition: In Plain English**
> HAR-X is just HAR with extra columns in the regression.
> The three core RV inputs stay, and you bolt on whatever other predictors you think contain information about future volatility: the VIX, yesterday's stock return, trading volume, macro surprises, and so on.
> Each additional predictor gets its own coefficient, so OLS tells you whether it helps after controlling for the core HAR terms.

> **Project Connection: Why This Matters**
> HAR-X is the linear version of what your ML model will do.
> Any feature you feed to a random forest or neural network, you should first test in a HAR-X regression to see whether it helps linearly.
> If it does, the ML question becomes: does the feature interact nonlinearly with other inputs?
> If it does not help even linearly, adding it to an ML model is unlikely to help and may cause overfitting.

Bollerslev et al. (2018) take this to a large scale in their "Risk Everywhere" paper, constructing a large cross-section of HAR-X type models with many macro and market predictors.

When $p$ is large, you face a classic overfitting problem: many predictors, limited data.
Audrino and Knaus (2016) propose the "Lassoing the HAR" approach, applying the Lasso (L1 regularization) to the HAR-X framework:

$$\min_{\beta, \gamma} \sum_{t} \left(\operatorname{RV}_{t+1} - \beta_0 - \beta_d \operatorname{RV}_t - \beta_w \operatorname{RV}^{(w)}_t - \beta_m \operatorname{RV}^{(m)}_t - \sum_j \gamma_j X_{j,t}\right)^2 + \lambda \sum_j |\gamma_j|$$

- $\lambda$: regularization penalty; larger $\lambda$ shrinks more coefficients to exactly zero
- The penalty applies to the exogenous coefficients $\gamma_j$, not the core HAR terms
- The Lasso selects which exogenous variables matter while keeping the core HAR structure intact

> **Intuition: In Plain English**
> When you have many candidate predictors, Lasso-HAR asks: "which of these extra variables actually help, and which are just adding noise?"
> It does this by penalizing the model for using too many variables.
> The penalty forces weak predictors' coefficients to exactly zero, automatically dropping them from the forecast, while keeping the core daily/weekly/monthly HAR terms intact.

> **Project Connection: Why This Matters**
> Lasso-HAR is the simplest regularized model in your toolbox and a natural stepping stone between plain HAR and full ML.
> If Lasso-HAR with 20 features beats HAR, you know the extra features carry signal.
> The next question, which your project addresses, is whether nonlinear models (trees, neural nets) can extract even more from those same features.

> **Prereq: Lasso Regularization**
> The Lasso (Least Absolute Shrinkage and Selection Operator) adds an L1 penalty ($\lambda \sum |\gamma_j|$) to the OLS objective.
> This has two effects: (1) it shrinks coefficients toward zero, reducing overfitting; (2) it sets some coefficients to exactly zero, performing automatic variable selection.
> The tuning parameter $\lambda$ controls the strength of the penalty and is chosen by cross-validation.

> **Key Idea: HAR-X Is the Bridge to ML**
> HAR-X with many predictors is effectively a linear ML model.
> Adding Lasso regularization makes it a penalized linear model with variable selection.
> [Chapters 11](ch11-tree-methods-vol.md)--[13](ch13-hybrid-ensemble.md) ask the next question: can *nonlinear* models (tree ensembles, neural networks) improve on this, or does the extra flexibility just lead to overfitting?
> The answer depends critically on the feature set and forecast horizon.


## Why HAR Is Hard to Beat

If HAR is so simple (three coefficients, OLS), why is it the benchmark rather than a stepping stone that ML quickly surpasses?
Three reasons.

**Reason 1: Volatility is highly persistent and approximately linear.**
The autocorrelation function of $\operatorname{RV}_t$ decays slowly and smoothly.
A model that captures the right decay rate with the right mixture of time scales gets most of the forecastable variation.
HAR does exactly this.
The residual nonlinearity is real but small relative to the linear component.

**Reason 2: The signal-to-noise ratio is low.**
Even though volatility is more predictable than returns, the day-to-day fluctuations in $\operatorname{RV}$ are large.
A model that tries to fit these fluctuations more precisely (e.g., by adding interaction terms, polynomial features, or deep layers) tends to fit noise rather than signal, especially with the relatively short samples typical in finance (10--20 years of daily data is 2,500--5,000 observations).

**Reason 3: Daily horizon, RV-only features.**
When you restrict the feature set to past RV values and forecast one day ahead, there is little nonlinear structure for ML to exploit.
The gains from ML come from two sources that HAR cannot access:

1. **Richer features**: options-implied volatility, cross-asset information, order flow, macroeconomic data, text/news sentiment ([Chapter 10](ch10-feature-engineering.md)).
2. **Longer horizons**: at weekly or monthly forecast horizons, nonlinear regime dynamics and mean-reversion patterns become more pronounced, giving tree-based models and neural networks more to work with.

> **Key Idea: The HAR Litmus Test**
> If your ML model does not beat HAR on the same features (past RV only) and the same forecast horizon (one day), you have not learned nonlinear structure; you have overfit noise.
> Always report HAR alongside your ML results.
> If you beat HAR, the follow-up question is: does the improvement come from richer features (good) or from fitting noise in RV (bad)?
> The answer determines whether the ML model has real economic value.

> **Project Connection: Why This Matters**
> This table is your strategic roadmap.
> If you use RV-only features at the daily horizon, HAR will probably tie or beat your ML model, and that is expected.
> Your project should aim for the bottom-right cell: richer features (e.g., VIX, signed returns, cross-asset vol) at weekly or monthly horizons, where both the feature advantage and the nonlinear structure advantage compound.
> Design your experiments accordingly.

The following table summarizes where ML has and has not consistently beaten HAR in the literature.

| **Setting** | **HAR vs. ML** | **Why** |
|---|---|---|
| Daily horizon, RV-only features | HAR wins or ties | Little nonlinear signal |
| Daily horizon, rich features | ML often wins | Extra features carry new info |
| Weekly/monthly horizon, RV-only | ML sometimes wins | Nonlinear regime effects |
| Weekly/monthly horizon, rich features | ML usually wins | Both advantages compound |

> **Warning: Publication Bias**
> Papers that fail to beat HAR are less likely to be published.
> The literature therefore overstates the frequency with which ML improves on HAR.
> Be skeptical of reported improvements below 5--10% in out-of-sample $\operatorname{QLIKE}$, and always check whether the improvement is statistically significant via a Diebold--Mariano test ([Chapter 16](ch16-forecast-evaluation.md)).


## Summary

- The **Heterogeneous Market Hypothesis** (Muller et al., 1993) posits that markets are driven by participants operating at daily, weekly, and monthly horizons, whose interactions produce the observed volatility dynamics.

- The **HAR model** (Corsi, 2009) translates this directly into a regression: $\operatorname{RV}_{t+1} = \beta_0 + \beta_d \operatorname{RV}_t + \beta_w \operatorname{RV}^{(w)}_t + \beta_m \operatorname{RV}^{(m)}_t + \varepsilon_{t+1}$, estimated by OLS.

- HAR **mimics long memory** with only three coefficients by embedding lags 1--22 through the weekly and monthly averages.

- **Typical $R^2$** for daily-horizon HAR on equity index RV: 0.40--0.60.

- **HAR-J** (Andersen, Bollerslev, and Diebold, 2007) adds a jump component $J_t = \max(\operatorname{RV}_t - \operatorname{BPV}_t, 0)$. Jumps are statistically significant but economically small predictors.

- **HAR-CJ** (Corsi, Pirino, and Reno, 2010) separates continuous and jump components at all three horizons. Continuous variation dominates the forecast; jumps are largely transient.

- **SHAR** (Patton and Sheppard, 2015) decomposes daily RV into positive ($RS^+$) and negative ($RS^-$) semivariance. Bad volatility ($RS^-$) is significantly more persistent, reflecting the leverage effect at the intraday level.

- **HARQ** (Bollerslev, Patton, and Quaedvlieg, 2016) allows the daily coefficient to vary with realized quarticity $RQ_t$, down-weighting $\operatorname{RV}_t$ on noisy days. It is the strongest univariate RV forecast in the literature.

- **HAR-X** adds exogenous predictors (VIX, returns, macro). With many predictors, Lasso regularization (Audrino and Knaus, 2016) prevents overfitting while preserving the core HAR structure.

- HAR is **extremely competitive** at the daily horizon with RV-only features. ML gains come from richer feature sets and longer horizons.

- The **HAR litmus test**: if your ML model cannot beat HAR on the same features and horizon, it has overfit noise, not learned nonlinear structure.

- All HAR variants are estimated by **OLS** (or penalized OLS), require no iterative optimization, and produce interpretable coefficients. This simplicity is a feature, not a limitation.

- Throughout this guide, HAR (or HARQ) is the **mandatory baseline** for every forecasting model.


## Key Results

| **Result** | **Source** | **Finding** |
|---|---|---|
| Heterogeneous Market Hypothesis | Muller et al. (1993) | Markets are driven by participants at multiple horizons; volatility dynamics are a superposition of time scales |
| HAR model | Corsi (2009) | Three OLS coefficients (daily, weekly, monthly RV) approximate long-memory dynamics; $R^2 \approx 0.40$--$0.60$ for daily equity index forecasts |
| HAR-J (jumps) | Andersen, Bollerslev, and Diebold (2007) | Adding jump component improves fit marginally; jumps are largely transient and do not persist into future volatility |
| HAR-CJ | Corsi, Pirino, and Reno (2010) | Full continuous/jump decomposition at all horizons; continuous variation dominates forecasting power |
| SHAR (semivariance) | Patton and Sheppard (2015) | Negative semivariance is more persistent than positive; capturing the leverage effect improves forecasts |
| HARQ (measurement error) | Bollerslev, Patton, and Quaedvlieg (2016) | Varying the daily coefficient with $\sqrt{RQ_t}$ down-weights noisy estimates; strongest univariate RV forecast |
| Lassoing the HAR | Audrino and Knaus (2016) | Lasso selects relevant exogenous predictors while preserving core HAR structure; prevents overfitting with many regressors |
| Risk Everywhere | Bollerslev et al. (2018) | Large-scale HAR-X with macro/market predictors; confirms predictability from multiple exogenous sources |
