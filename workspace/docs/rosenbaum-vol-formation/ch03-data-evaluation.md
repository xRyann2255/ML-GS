# 3 Data and evaluation metrics

Our dataset contains 5-minutes intraday prices of Russell 1000 and STOXX Europe 600 constituents, for years between 2010 and 2020. After removing the ones with considerable missing or abnormal data, we get 862 names from the US market and 503 names from the European market. Figure 3.1 gives their distribution by associated sectors following the Global Industry Classification Standard (GICS)<sup>2</sup>, where we can see a diversity of involved sectors. The daily realized volatility is estimated by

$$\sigma_t = \sqrt{\sum_i r_{t,i}^2},$$

where $r_{t,i}$ is defined by the $i$-th 5-minutes intraday return after removing the first and last 30 minutes of the daily trading period. The return of day $t$ is defined as

$$r_t = \frac{P_t - P_{t-1}}{P_{t-1}},$$

where $P_t$ is the closing price of day $t$. To make the data of different stocks have similar scale, we perform the following scaling for each stock:

$$\sigma_t = \frac{\sigma_t}{\sqrt{\langle \sigma_t^2 \rangle}}, \qquad r_t = \frac{r_t - \langle r_t \rangle}{\sqrt{\langle (r_t - \langle r_t \rangle)^2 \rangle}}$$

where $\langle \cdot \rangle$ refers to the average over $t$.

---

### Figure 3.1: Count of stocks by GICS Sector

| GICS Sector              | US  | EU  |
|--------------------------|-----|-----|
| Energy                   | 45  | 14  |
| Materials                | 51  | 52  |
| Industrials              | 131 | 93  |
| Consumer discretionary   | 109 | 111 |
| Consumer staples         | 59  | 47  |
| Health care              | 111 | 38  |
| Financials               | 143 | 70  |
| Information technology   | 140 | 39  |
| Communication services   | 64  | 31  |
| Utilities                | 40  | 31  |
| Real estate              | 33  | 35  |

> *Figure 3.1: Bar chart with two bars per sector (US blue, EU orange) showing the count of stocks by GICS Sector.*

---

We focus mostly on the US market, and the data of the European market is used for an out-of-sample double-check. We use the pooled dataset of 862 stocks over years 2010 – 2015 to train the LSTM network. The period 2016 – 2020<sup>3</sup> is used for out-of-sample evaluation. For the parametric models introduced above, sliding window fit of size 1000 is applied, which means, the model is recalibrated with the last 1000 data points for every new forecast. We employ MSE as the model evaluation metric, which is defined as follows:

$$\text{MSE}(\sigma, \hat{\sigma}) = \frac{1}{T}\sum_{t=1}^{T} (\hat{\sigma}_t - \sigma_t)^2,$$

where $T$ is the number of trading days of the out-of-sample period. MSE is widely used in forecasting-like tasks. According to [25], it is a robust and homogeneous metric for model comparison of volatility forecasting. In this work, we focus more on each model's relative performance compared to that of the HAR model so that we compute instead $(\text{MSE}_m / \text{MSE}_{\text{HAR}})$, for $m \in \{\text{AR}(22), \text{RFSV}, \text{LSTM}\}$.

---

**Footnotes:**

<sup>2</sup> https://www.msci.com/our-solutions/indexes/gics

<sup>3</sup> As in this work we focus on the endogenous volatility feedback effect, the period 2020-02-01 – 2020-06-01 is excluded from the test set, which is conceived to be largely perturbed by exogenous information.
