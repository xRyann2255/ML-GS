# Chapter 14: Multivariate Volatility -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 71
**Verified:** 0/71
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 37 | defining-formula | Realized covariance matrix: $\mathbf{RC}_t = \sum_{i=1}^{M} \mathbf{r}_{t,i}\,\mathbf{r}_{t,i}^\top \in \mathbb{R}^{p \times p}$ | BarndorffNielsenHansenLundeShephard2011 | | | Standard definition; outer-product form |
| 2 | 43 | numerical-fact | 78 five-minute intervals in a 6.5-hour trading day | [uncited] | | | 6.5 hours = 390 min; 390/5 = 78 |
| 3 | 50-52 | qualitative | Under no noise and synchronous trading, RC converges to integrated covariance matrix as $M \to \infty$ | BarndorffNielsenHansenLundeShephard2011 | | | Consistency result |
| 4 | 59 | numerical-fact | For $p = 50$ assets, $p(p+1)/2 = 1{,}275$ unique entries | [uncited] | | | Arithmetic: 50*51/2 = 1275 |
| 5 | 152-153 | qualitative | If you ignore missing observations from non-synchronous trading, you bias realized covariance toward zero (the "Epps effect") | [uncited] | | | Classic result, attributed to Epps (1979) but not cited here |
| 6 | 193-195 | defining-formula | Refresh-time formula: $\tau_k = \max_{j=1,\ldots,p} \min\{t_{j,n} : t_{j,n} > \tau_{k-1}\}$ with $\tau_0 = 0$ | [uncited] | | | Standard refresh-time definition |
| 7 | 200 | attribution | Hayashi--Yoshida estimator proposed by Hayashi and Yoshida (2005) | HayashiYoshida2005 | | | Check that 2005 is correct publication year |
| 8 | 209-215 | defining-formula | Hayashi--Yoshida estimator: $\hat{\sigma}_{AB,t}^{HY} = \sum_i \sum_j r_{t,i}^{(A)} r_{t,j}^{(B)} \mathbf{1}\{[t_{i-1}^A, t_i^A) \cap [t_{j-1}^B, t_j^B) \neq \emptyset\}$ | HayashiYoshida2005 | | | Core formula |
| 9 | 219 | qualitative | HY estimator is unbiased and consistent for integrated covariance under mild conditions | HayashiYoshida2005 | | | Check paper for stated conditions |
| 10 | 220 | qualitative | HY estimator is not guaranteed positive semi-definite (PSD) for $p > 2$ | HayashiYoshida2005 | | | Check paper or follow-up literature |
| 11 | 248-254 | numerical-fact | Worked example return computations: $r_1^A = \ln(101/100) \approx 0.00995$; $r_2^A = \ln(99/101) \approx -0.02005$; $r_3^A = \ln(100.5/99) \approx 0.01511$; $r_1^B = \ln(50.5/50) \approx 0.00995$; $r_2^B = \ln(49.8/50.5) \approx -0.01399$; $r_3^B = \ln(50.2/49.8) \approx 0.00802$ | [uncited] | | | Six log-return calculations to verify |
| 12 | 258-271 | numerical-fact | Overlap table: $[0,2) \cap [0,3)$ = Yes; $[0,2) \cap [3,6)$ = No; $[2,5) \cap [0,3)$ = Yes; $[2,5) \cap [3,6)$ = Yes; $[5,8) \cap [3,6)$ = Yes; $[5,8) \cap [6,8)$ = Yes | [uncited] | | | Six interval-overlap determinations |
| 13 | 274-281 | numerical-fact | Worked example HY products: $(0.00995)(0.00995) = 9.90 \times 10^{-5}$; $(−0.02005)(0.00995) = −1.99 \times 10^{-4}$; $(−0.02005)(−0.01399) = 2.81 \times 10^{-4}$; $(0.01511)(−0.01399) = −2.11 \times 10^{-4}$; $(0.01511)(0.00802) = 1.21 \times 10^{-4}$; sum $\approx 9.1 \times 10^{-5}$ | [uncited] | | | Five products and final sum to verify |
| 14 | 288-289 | qualitative | For $p = 2$, the Hayashi--Yoshida estimator is always PSD (it is a scalar covariance) | [uncited] | | | Logical claim: 1x1 real number squared is non-negative, but HY covariance can be negative; check if this is about the 2x2 matrix |
| 15 | 289-290 | qualitative | For $p \geq 3$, the matrix assembled from pairwise HY estimates can have negative eigenvalues | [uncited] | | | Known result in HF covariance literature |
| 16 | 313 | attribution | Multivariate realized kernel defined by Barndorff-Nielsen, Hansen, Lunde, and Shephard (2011) | BarndorffNielsenHansenLundeShephard2011 | | | Check publication year |
| 17 | 315-318 | defining-formula | Multivariate realized kernel: $\mathbf{K}_t = \sum_{h=-H}^{H} k\!\left(\frac{h}{H+1}\right) \bm{\Gamma}_h$ | BarndorffNielsenHansenLundeShephard2011 | | | Core formula |
| 18 | 321 | supporting-formula | Cross-autocovariance matrix: $\bm{\Gamma}_h = \sum_i \mathbf{r}_{t,i} \mathbf{r}_{t,i+h}^\top$ | BarndorffNielsenHansenLundeShephard2011 | | | Component definition |
| 19 | 323 | qualitative | Kernel function satisfies $k(0) = 1$, $k(1) = 0$ (e.g., Parzen kernel) | BarndorffNielsenHansenLundeShephard2011 | | | Standard kernel conditions |
| 20 | 332-333 | qualitative | Multivariate realized kernel with non-negative kernel function (e.g., Parzen) is guaranteed PSD by construction, even with non-synchronous trading and microstructure noise | BarndorffNielsenHansenLundeShephard2011 | | | Key theoretical result |
| 21 | 335 | qualitative | Rate of convergence of multivariate realized kernel is $M^{-1/5}$ (slower than noise-free $M^{-1/2}$) | BarndorffNielsenHansenLundeShephard2011 | | | Convergence rate claim |
| 22 | 336 | qualitative | The $M^{-1/5}$ rate is the same price paid in the univariate case | BarndorffNielsenHansenLundeShephard2011 | | | Cross-reference with univariate realized kernel rate |
| 23 | 387 | attribution | DCC model attributed to Engle (2002) | Engle2002DCC | | | Check publication year |
| 24 | 400-403 | defining-formula | DCC quasi-correlation dynamics: $Q_t = (1 - \alpha - \beta)\bar{Q} + \alpha \mathbf{z}_{t-1}\mathbf{z}_{t-1}^\top + \beta Q_{t-1}$ | Engle2002DCC | | | Core DCC equation |
| 25 | 399 | supporting-formula | Standardized residuals: $\mathbf{z}_t = D_t^{-1} \mathbf{r}_t$ | Engle2002DCC | | | Component definition |
| 26 | 412 | methodological | Stationarity condition: $\alpha + \beta < 1$ | Engle2002DCC | | | Check exact condition in Engle (2002) |
| 27 | 416 | supporting-formula | Correlation matrix rescaling: $R_t = \mathrm{diag}(Q_t)^{-1/2} Q_t \mathrm{diag}(Q_t)^{-1/2}$ | Engle2002DCC | | | Standard DCC rescaling step |
| 28 | 418 | supporting-formula | Conditional covariance: $\Sigma_t = D_t R_t D_t$ | Engle2002DCC | | | DCC output formula |
| 29 | 425-426 | qualitative | DCC scales well to large $p$ because Step 1 is embarrassingly parallel (one GARCH per asset) and Step 2 has only two free parameters ($\alpha$, $\beta$) regardless of dimension | Engle2002DCC | | | Scalability claim |
| 30 | 430-431 | qualitative | DCC correlations follow a single $(\alpha, \beta)$ dynamic for all pairs | [uncited] | | | Known DCC limitation; check if scalar DCC is the only version presented |
| 31 | 434 | qualitative | DCC uses daily returns, not intraday data | [uncited] | | | Characterization of standard DCC |
| 32 | 436 | qualitative | DCC two-step estimation is not fully efficient but is consistent | [uncited] | | | Check Engle (2002) or Engle and Sheppard (2001) for efficiency discussion |
| 33 | 462-463 | defining-formula | WAR model: $\mathbf{RC}_{t+1} = C + A\,\mathbf{RC}_t\,A^\top + E_{t+1}$ with $E_{t+1}$ Wishart-distributed | [uncited] | | | Check WAR literature (Gourieroux, Jasiak, Sufana 2009 or similar) |
| 34 | 472 | qualitative | The Wishart distribution is the matrix generalization of the chi-squared distribution and is the natural distribution for covariance matrices | [uncited] | | | Standard statistical fact |
| 35 | 476-484 | supporting-formula | HAR-style WAR variant: $\mathbf{RC}_{t+1} = C + A_d\,\mathbf{RC}_t\,A_d^\top + A_w\,\overline{\mathbf{RC}}_t^{(w)}\,A_w^\top + A_m\,\overline{\mathbf{RC}}_t^{(m)}\,A_m^\top + E_{t+1}$ with weekly/monthly averages over 5 and 22 trading days | [uncited] | | | WAR-HAR extension |
| 36 | 500 | numerical-fact | With $p = 50$ assets, coefficient matrix $A$ alone has 2,500 parameters | [uncited] | | | Arithmetic: $50^2 = 2500$ |
| 37 | 508-509 | numerical-fact | With daily, weekly, and monthly lags for $p = 50$, that is 7,500 parameters plus the intercept | [uncited] | | | Arithmetic: $3 \times 2500 = 7500$ |
| 38 | 510-511 | numerical-fact | Typical sample sizes are 1,000--3,000 trading days | [uncited] | | | Empirical range claim |
| 39 | 512 | qualitative | WAR is practical only for small $p$ (say, $p \leq 5$) unless you impose strong structure | [uncited] | | | Practical guidance |
| 40 | 524 | attribution | DRD decomposition attributed to Bollerslev, Patton, and Quaedvlieg (2018) | BollerslevPattonQuaedvlieg2018 | | | Check publication year |
| 41 | 526-527 | defining-formula | DRD decomposition: $\mathbf{RC}_t = D_t R_t D_t$ where $D_t = \mathrm{diag}(\sqrt{[\mathbf{RC}_t]_{11}}, \ldots, \sqrt{[\mathbf{RC}_t]_{pp}})$ and $R_t = D_t^{-1} \mathbf{RC}_t D_t^{-1}$ | BollerslevPattonQuaedvlieg2018 | | | Core decomposition |
| 42 | 542-543 | methodological | Correlations modeled using Fisher $z$-transform to map $[-1,1]$ to $(-\infty, \infty)$ | BollerslevPattonQuaedvlieg2018 | | | Check if BPQ 2018 specifically use Fisher z-transform |
| 43 | 618-624 | qualitative | BPQ (2018) show that DRD decomposition with separate HAR regressions significantly outperforms both (a) direct vech-HAR on all elements jointly and (b) DCC-GARCH | BollerslevPattonQuaedvlieg2018 | | | Key empirical result; verify in paper |
| 44 | 621-623 | qualitative | HARQ variant (adding $\sqrt{RQ}$ interactions) further improves variance forecasts, especially on high-noise days | BollerslevPattonQuaedvlieg2018 | | | Check if this result is in BPQ 2018 or in the original HARQ paper |
| 45 | 631-637 | numerical-fact | Worked example DRD: from $\mathbf{RC}_t$ with entries $(0.00040, 0.00012; 0.00012, 0.00025)$, get $D_t = \mathrm{diag}(0.0200, 0.0158)$ and $R_t$ with off-diagonal 0.379 | [uncited] | | | $\sqrt{0.00040} = 0.02$; $\sqrt{0.00025} \approx 0.01581$; $\rho = 0.00012/(0.02 \times 0.01581) \approx 0.3795$ |
| 46 | 643 | numerical-fact | Fisher z-transform: $z = \frac{1}{2}\ln(\frac{1+0.379}{1-0.379}) \approx 0.399$ | [uncited] | | | Arithmetic: $\frac{1}{2}\ln(1.379/0.621) = \frac{1}{2}\ln(2.2206) = \frac{1}{2}(0.7975) \approx 0.399$ |
| 47 | 655-656 | qualitative | Nearest correlation matrix projection via alternating projections algorithm of Higham (2002) | [uncited] | | | Attribution to Higham (2002); check exact reference |
| 48 | 667 | attribution | Cholesky-HAR attributed to Chiriac and Voev (2011) | ChiriacVoev2011 | | | Check publication year |
| 49 | 668-669 | qualitative | Every PSD matrix has a unique Cholesky decomposition $\mathbf{RC}_t = L_t L_t^\top$ where $L_t$ is lower triangular with positive diagonal entries | ChiriacVoev2011 | | | Standard linear algebra fact; uniqueness requires strictly positive definite |
| 50 | 696-700 | numerical-fact | Worked example Cholesky: from same RC matrix, $l_{11} = \sqrt{0.00040} = 0.02$; $l_{21} = 0.00012/0.02 = 0.006$; $l_{22} = \sqrt{0.00025 - 0.006^2} = \sqrt{0.000214} \approx 0.01470$ | [uncited] | | | Arithmetic: $0.006^2 = 0.000036$; $0.00025 - 0.000036 = 0.000214$; $\sqrt{0.000214} \approx 0.01463$ -- check if 0.01470 is correct |
| 51 | 703 | numerical-fact | Log-transform diagonal: $\ln(0.02) \approx -3.912$; $\ln(0.01470) \approx -4.220$ | [uncited] | | | $\ln(0.02) = -3.912$; $\ln(0.01470) \approx -4.220$ -- verify |
| 52 | 710-719 | numerical-fact | Worked example Cholesky forecast reassembly: from $(-3.900, 0.0058, -4.210)$, get $\hat{l}_{11} = e^{-3.900} \approx 0.02020$, $\hat{l}_{22} = e^{-4.210} \approx 0.01483$; final matrix entries $(0.000408, 0.000117; 0.000117, 0.000254)$ | [uncited] | | | Multiple exponentiations and matrix multiplication to verify |
| 53 | 766 | attribution | Graph-HAR attributed to Zhang, Pu, Cucuringu, and Dong (2024) | ZhangPuCucuringuDong2024 | | | Check publication year and author list |
| 54 | 770-776 | defining-formula | Graph-HAR: $\mathrm{RV}_{j,t+1} = \beta_0 + \beta_d \mathrm{RV}_{j,t} + \beta_w \mathrm{RV}_{j,t}^{(w)} + \beta_m \mathrm{RV}_{j,t}^{(m)} + \gamma \sum_{k \neq j} W_{jk} \mathrm{RV}_{k,t} + \varepsilon_{j,t+1}$ | ZhangPuCucuringuDong2024 | | | Core Graph-HAR formula |
| 55 | 781 | qualitative | The term $\sum_{k \neq j} W_{jk} \mathrm{RV}_{k,t}$ is exactly one step of graph diffusion | ZhangPuCucuringuDong2024 | | | Mathematical characterization |
| 56 | 784-785 | methodological | Adjacency matrix $W$ typically from thresholded correlation or LASSO partial correlation | ZhangPuCucuringuDong2024 | | | Check what graph construction methods the paper actually uses |
| 57 | 808 | attribution | GNN for covariance attributed to Zhang, Cucuringu, and Dong (2023) | ZhangCucuringuDong2023 | | | Check publication year and author list |
| 58 | 976-977 | defining-formula | Affine-invariant Riemannian metric: $d(\Sigma_A, \Sigma_B) = \|\log(\Sigma_A^{-1/2} \Sigma_B \Sigma_A^{-1/2})\|_F$ | [uncited] | | | Standard SPD metric from differential geometry literature |
| 59 | 979-980 | qualitative | This distance is affine-invariant: $d(A\Sigma_A A^\top, A\Sigma_B A^\top) = d(\Sigma_A, \Sigma_B)$ for any invertible $A$ | [uncited] | | | Standard property of the AIRM |
| 60 | 989-990 | qualitative | BiMap layer: $\Sigma \mapsto W\Sigma W^\top$; if $\Sigma \succ 0$ and $W$ has full row rank, then $W\Sigma W^\top \succ 0$. Also reduces dimension from $p$ to $d$ | [uncited] | | | Linear algebra fact: congruence preserves positive definiteness under full rank |
| 61 | 993-995 | defining-formula | ReEig layer: eigendecompose $\Sigma = U\Lambda U^\top$, then $\Sigma \mapsto U \max(\Lambda, \epsilon I) U^\top$ | [uncited] | | | SPDNet architecture component |
| 62 | 997-999 | defining-formula | LogEig layer: $\Sigma \mapsto U \log(\Lambda) U^\top$, maps from SPD manifold to tangent space (symmetric matrices) | [uncited] | | | SPDNet architecture component |
| 63 | 1006-1009 | qualitative | SPDNet is the only deep learning architecture for covariance forecasting with a built-in PSD guarantee (every layer maps PSD inputs to PSD outputs) | [uncited] | | | Strong uniqueness claim; verify against literature |
| 64 | 1064 | qualitative | Eigenvalue clipping gives the nearest PSD matrix in Frobenius norm | [uncited] | | | Standard result; technically this is the nearest PSD matrix only under specific conditions |
| 65 | 1066 | qualitative | For correlation matrices, the Higham (2002) alternating projection algorithm additionally enforces unit diagonal | [uncited] | | | Second reference to Higham (2002); check exact paper |
| 66 | 1039 | qualitative | DCC-GARCH has PSD guarantee by construction (via $D_t R_t D_t$ and rescaling) | Engle2002DCC | | | Check that standard DCC guarantees PSD |
| 67 | 1040 | qualitative | WAR does not guarantee PSD; requires post-hoc projection | [uncited] | | | Check WAR literature |
| 68 | 1041 | qualitative | HAR-DRD does not guarantee PSD; requires post-hoc projection on $\hat{R}_{t+1}$ | BollerslevPattonQuaedvlieg2018 | | | Check if BPQ discuss this |
| 69 | 1042 | qualitative | Cholesky-HAR guarantees PSD by construction via $\hat{L}\hat{L}^\top$ | ChiriacVoev2011 | | | Correct by linear algebra |
| 70 | 1129 | qualitative | WAR has $O(p^4)$ parameters | [uncited] | | | Summary table claim; check: WAR(1) has $p^2$ (for A) + $p(p+1)/2$ (for C); with HAR-style 3 lags, $3p^2 + p(p+1)/2$, which is $O(p^2)$ not $O(p^4)$ -- potential error |
| 71 | 1071-1072 | qualitative | For small $p$ (2--5 assets), PSD violations are rare and small; for large $p$ (50--500), they are common and can be severe | [uncited] | | | Empirical characterization; check literature |
