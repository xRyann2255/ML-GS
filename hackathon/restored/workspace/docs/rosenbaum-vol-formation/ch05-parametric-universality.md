# 5 Uncovering the universal volatility formation process

The above results confirm a universal volatility formation mechanism across assets, relating past volatilities and returns to current volatilities, from a nonparametric perspective. We wonder now whether we can disclose this universal nature with a parsimonious parametric formulation, while keeping similar level of forecasting performance as that of the LSTM network. The RFSV model gives a parametric view of the universal link between past and current volatilities. The results in Figure 4.2 and 4.9 shows that the RFSV model can get similar out-of-sample forecasting performance as the LSTMs trained with past volatilities data. The recently introduced QRH model encodes strong Zumbach effect describing the feedback effect of price trends on volatility, which is missing in the RFSV model. In the following, we first verify the universality of both models. For each model, we will see that similar forecasting performance can be obtained with properly fixed parameters as in the case where parameters are calibrated on each stock. Then we evaluate a simple combination of these two universal parametric forecasting devices, comparing its performance with the universal LSTM.

---

## RFSV

As shown in (2.3), forecasting volatility in the RFSV model involves two parameters, $H$ and $\nu^2$, where the impact of $\nu^2$ is imposed only through the $c$ defined in (2.4). Figure 5.1 shows the estimation results of $H$ and $c$ with data of 2012–2015 of US market, by following the method introduced in Section 2.1. The deviations across stocks do not seem to be large for both $H$ and $c$. Other methods can be tested in the future trying to reduce the estimation errors. Here for illustrating the idea, we fix $H$ and $c$ with the observed medians, i.e. $H = 0.055$, $c = 1.03$, for the forecasting of all the stocks considered, including those of the European market. Figure 5.2 gives its out-of-sample MSE relative to those fitted on each stock based on a sliding window of 1000 days. Interestingly, the device with predetermined parameters performs slightly better than the asset-specific ones, which could be impacted more by estimation errors due to limited data. This suggests the universality of the RFSV method in the sense that the same parameters work for all stocks.

> **[Figure 5.1]:** Distribution of $H$ and $c$ calibrated with data of 2012–2015 of US market, with medians $\text{Median}(H) \sim 0.055$ and $\text{Median}(c) \sim 1.03$. Two histograms. Left: distribution of estimated $H$ across US stocks, tight distribution centered around 0.055. Right: distribution of $c$, tight distribution centered around 1.03.

> **[Figure 5.2]:** Out-of-sample MSE of the RFSV forecast with fixed parameters, relative to that of calibration on each stock. Two histograms. (a) US market: distribution centered slightly below 1.0. (b) European market: same, also around 1.0. Fixed parameters perform slightly better than asset-specific calibration.

---

## QRH

Following the idea on Zumbach effect of the QRH model, we propose the following forecasting device:

$$\hat{\sigma}_t^2 = a(Z_{t-1} - b)^2 + c \,,\tag{5.1}$$

$$Z_t = \sum_{i=1}^{n} c_i^d \, Z_{i,t} \,,$$

$$Z_{i,t} = e^{-\gamma_i^d} Z_{i,t-1} + r_t, \qquad Z_{i,0} = z_{i,0}, \qquad i = 1, \ldots, n \,,\tag{5.2}$$

where $a, b, c > 0$ and $(c_i^d, \gamma_i^d)_{i=1,\ldots,n}$ are given by the same multi-factor approximation of the rough kernel function

$$K(t) := \frac{t^{H-1/2}}{\Gamma(H+1/2)}$$

as that used in [28][^4]. Given some $H$ and the number of factors $n$ for the approximation, we recall that $(c_i^d, \gamma_i^d)_{i=1,\ldots,n}$ are not free parameters to calibrate. Equations (5.1, 5.2) can be seen as a multi-factor discretization of the process[^5]

$$Z_t = \int_{-\infty}^{t} \frac{(t-s)^{H-1/2}}{\Gamma(H+1/2)} \sigma_s \, dW_s \,,$$

which is essentially a moving average of past returns. The above model is not very sensitive to $(z_{i,0})_{i=1,\ldots,n}$ because of the exponential decay. In practice given a time series $(r_t, \sigma_t)_{t=1,\ldots,T}$ of length $T$, we can take $z_{i,0} = 0$ and compute $(Z_{i,t})_{t=1,\ldots,T}$ following (5.2). Then we can simply discard the $N$ initial samples $(Z_{i,t}, \sigma_t)_{t=1,\ldots,N}$ from the original data history. With the remaining data, we search for the $(a, b, c)$ minimizing the error

$$\sum_{t=N+1}^{T} (\hat{\sigma}_t - \sigma_t)^2$$

using some optimization algorithm[^6].

Figure 5.3 shows the resulting distributions of calibrated $a$, $b$ and $c$ with data of 2012–2015 of US market. The deviations across stocks seem to be large, especially for $b$. In fact as indicated in Figure 4.4, the impact of past returns on current volatilities is not as apparent as that of past volatilities, it is not surprising to get noisy estimations of $(a, b, c)$. We are interested in how the forecasting performance evolves when we use fixed $(a, b, c)$ for all stocks. Similarly as above, we test with their median observations. Figure 5.4 shows its resulting out-of-sample MSE, along with that of stock-specific calibrations where $(a, b, c)$ are fitted on each stock based on a sliding window of 1000 days. We do not remark that the forecasting with fixed parameters performs significantly worse than the other. Note that the QRH forecast is outperformed by the HAR as the former does not use past volatilities.

> **[Figure 5.3]:** Distribution of $a$, $b$, and $c$ calibrated with data of 2012–2015 of US market, with medians $\text{Median}(a) \sim 0.043$, $\text{Median}(b) \sim 0.74$ and $\text{Median}(c) \sim 0.55$. Three histograms. $a$: moderate spread around 0.043. $b$: large spread (up to 14), median at 0.74. $c$: moderate spread around 0.55.

> **[Figure 5.4]:** Out-of-sample MSE of the QRH forecast with calibration on each stock and with fixed parameters, relative to the HAR forecast. Two histograms. (a) US market: single-stock calibration (blue) vs fixed parameters (orange), both relative to HAR. QRH underperforms HAR (ratios 1–6). (b) European market: same pattern. Fixed parameters not significantly worse than stock-specific.

[^4]: With daily data we use $c_i^d = \frac{c_i}{\sum_i c_i}$, $\gamma_i^d = \frac{\gamma_i}{250}$, where $c_i$ and $\gamma_i$ follow the same definition as in [28].

[^5]: Applying the multi-factor approximation avoids choosing a predetermined $\Delta$ to compute $Z_t \approx \int_{t-\Delta}^{t} \frac{(t-s)^{H-1/2}}{\Gamma(H+1/2)} \sigma_s \, dW_s$. Long-range information can be well captured by the one-step update of $(Z_{i,\cdot})_{i=1,\ldots,n}$ following (5.2).

[^6]: Or one can simply regress $\sigma_t^2$ against $(Z_t, Z_t^2)$.

---

## RFSV + QRH

We have seen that for the RFSV and QRH forecasts, fixing properly the parameters can obtain similar performance as allowing the parameters to be fitted on each stock. Since they do not depend on the same data for the forecast, we use the following combination as the final forecast:

$$(1 - \lambda)\hat{\sigma}^{RFSV} + \lambda \hat{\sigma}^{QRH} \,,$$

where $\lambda \in (0, 1)$, $\hat{\sigma}^{RFSV}$ and $\hat{\sigma}^{QRH}$ stand for the RFSV and QRH forecasts respectively. We evaluate this mixed forecast for different $\lambda$, with the other parameters fixed to the same values as above, i.e.

$$H = 0.055, \quad c = 1.03, \quad a = 0.043, \quad b = 0.74, \quad c = 0.55 \,.$$

Figure 5.5 and 5.6 show their forecasting performance relative to that of $\text{LSTM}^{us}_{ret}$ in US and European markets respectively. We remark that with $\lambda \sim 0.1$, the blended forecast can benefit from the complementary characteristic given by the RFSV and QRH forecasts, leading to the same level of performance as the universal nonparametric $\text{LSTM}^{us}_{ret}$.

> **[Figure 5.5]:** Out-of-sample performance of the forecast $(1 - \lambda)\hat{\sigma}^{RFSV} + \lambda\hat{\sigma}^{QRH}$ relative to $\text{LSTM}^{us}_{ret}$ in the US market. Boxplot showing ratios for $\lambda = 0.0, 0.05, 0.1, 0.2, 0.3$. At $\lambda \approx 0.1$, the blend achieves same performance as LSTM (median $\sim 100\%$).

> **[Figure 5.6]:** Out-of-sample performance of the forecast $(1 - \lambda)\hat{\sigma}^{RFSV} + \lambda\hat{\sigma}^{QRH}$ relative to $\text{LSTM}^{eu}_{ret}$ in the European market. Same pattern — $\lambda \approx 0.1$ matches LSTM performance.

Basically, the future volatility is made of two components depending respectively on past volatilities and past price trends. The first one describes the expected future log-volatility from a linear combination of past log-volatilities. The associated coefficients depend only on the roughness parameter $H$. A universal $H$ works for all stocks. The second component corresponds to the feedback effect of past price trends on volatility. The past price trends are built with a rough kernel, and their impact is expressed in a quadratic form, with essentially constant parameters across assets.
