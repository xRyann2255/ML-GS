# Chapter 12-R: Rashomon Sets and Interpretable Trees -- Verification Log

**Status:** Extraction complete
**Claims extracted:** 79 (87 rows; multi-source claims split into sub-rows)
**Verified:** 0/79
**Errors found:** 0

## Claims

| # | Line | Type | Claim/Formula | Cited source | Verified? | Paper page | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 63 | attribution | SHAP values were introduced/proposed by Lundberg and Lee | \citep{Lundberg2017} | | | |
| 2 | 68-72 | defining-formula | SHAP value formula: $\phi_i(f,x) = \sum_{S \subseteq F \setminus \{i\}} \frac{\|S\|!(|F|-|S|-1)!}{|F|!}[f_x(S \cup \{i\}) - f_x(S)]$ | \citep{Lundberg2017} | | | |
| 3 | 65-66 | qualitative | SHAP value for feature $i$ is the unique additive attribution satisfying local accuracy, missingness, and consistency | \citep{Lundberg2017} | | | |
| 4 | 122-123 | attribution | The idea of many equally-good models was articulated by Leo Breiman, who called it the "Rashomon effect" | [uncited] | | | Breiman's original paper not cited |
| 5 | 123-125 | qualitative | The Rashomon effect is a reference to the Akutagawa story (and Kurosawa film) in which multiple witnesses give contradictory but individually plausible accounts of the same event | [uncited] | | | |
| 6 | 135-144 | defining-formula | $\epsilon$-Rashomon set definition: $\mathcal{R}(\epsilon, f^*, \mathcal{F}) = \{f \in \mathcal{F} \mid L(f) \leq (1+\epsilon) L(f^*)\}$ | \citep{XinEtAl2022} | | | |
| 7 | 149-151 | qualitative | Typical values of $\epsilon$ in the literature range from 0.01 to 0.10 | \citep{XinEtAl2022} | | | |
| 8 | 165-166 | qualitative | For decision trees specifically, Xin et al. define the objective function as the misclassification loss plus a sparsity penalty | \citep{XinEtAl2022} | | | |
| 9 | 168-172 | defining-formula | Tree objective: $\operatorname{Obj}(t, \mathbf{X}, \mathbf{y}) = \frac{1}{n}\sum_{i=1}^{n}\mathbb{1}[\hat{y}_i \neq y_i] + \lambda H_t$ | \citep{XinEtAl2022} | | | |
| 10 | 177 | qualitative | $H_t$ is the number of leaves in tree $t$ | \citep{XinEtAl2022} | | | |
| 11 | 181-184 | supporting-formula | Rashomon set threshold: $\theta_\epsilon = (1+\epsilon) \times \operatorname{Obj}(t_{\text{ref}}, \mathbf{X}, \mathbf{y})$ | \citep{XinEtAl2022} | | | |
| 12 | 198-199 | numerical-fact | For trees of depth at most 4 with only 10 binary features, the number of possible trees exceeds $9.3 \times 10^{20}$ | \citep{XinEtAl2022} | | | |
| 13 | 203-206 | numerical-fact | On the COMPAS dataset with $\lambda = 0.005$ and a 15% Rashomon threshold, the set contains approximately $10^{12}$ trees | \citep{XinEtAl2022} | | | |
| 14 | 205-206 | numerical-fact | On smaller datasets (Monk2, Bar), Rashomon sets of $10^5$ to $10^8$ trees are typical | \citep{XinEtAl2022} | | | |
| 15 | 206-209 | qualitative | Natural baselines (BART, Random Forest, CART + sampling) find at best a tiny sliver of the Rashomon set -- they recover only hundreds to thousands of trees when the true set contains millions or more | \citep{XinEtAl2022} | | | |
| 16 | 254 | attribution | CART was introduced by Breiman et al. | \citep{Breiman1984} | | | |
| 17 | 254-255 | qualitative | CART and other greedy algorithms build trees top-down, choosing the best split at each node independently | \citep{Breiman1984} | | | |
| 18 | 255-256 | supporting-formula | CART runtime is $O(npd)$ for $n$ samples, $p$ features, depth $d$ | [uncited] | | | |
| 19 | 256-258 | numerical-fact | Greedy methods exhibit an average gap of 1--2 percentage points from the optimum, and on some datasets (e.g., COMPAS) the gap can reach 10 percentage points | \citep{BabbarEtAl2025} | | | |
| 20 | 268-271 | defining-formula | Optimal tree problem: $\mathcal{L}^*(D,d,\lambda) = \min_{T \in \mathcal{T}} L(T,D,\lambda)$ s.t. $\operatorname{depth}(T) \leq d$ | \citep{BabbarEtAl2025} | | | |
| 21 | 273-275 | defining-formula | Regularized loss: $L(T,D,\lambda) = \frac{1}{N}\sum_{i=1}^{N}\ell(T(\mathbf{x}_i),y_i) + \lambda S(T)$ where $S(T)$ is the number of leaves | \citep{BabbarEtAl2025} | | | |
| 22 | 293-296 | qualitative | A crucial empirical observation by Babbar et al. is that greedy splits near the leaves are almost always optimal, while greedy splits near the root often deviate from the optimum | \citep{BabbarEtAl2025} | | | |
| 23 | 300-301 | attribution | SPLIT (Sparse Lookahead for Interpretable Trees) was introduced by Babbar et al. | \citep{BabbarEtAl2025} | | | |
| 24 | 301-304 | methodological | SPLIT takes a lookahead depth parameter $d_l < d$ and performs full branch-and-bound optimization for splits up to depth $d_l$, then switches to greedy splitting for the remaining $d - d_l$ levels | \citep{BabbarEtAl2025} | | | |
| 25 | 310-312 | defining-formula | SPLIT runtime: $\mathcal{O}(n(d-d_l)k^{d_l+1} + nk^{d-d_l})$ | \citep{BabbarEtAl2025} | | | Algorithm 2 cited |
| 26 | 313-315 | defining-formula | LicketySPLIT runtime: $O(nk^2 d^2)$ -- polynomial time | \citep{BabbarEtAl2025} | | | |
| 27 | 314-315 | supporting-formula | Worst case of fully optimal methods is $\mathcal{O}((2k)^d)$ | \citep{BabbarEtAl2025} | | | |
| 28 | 335-337 | attribution | STreeD (STreeD Regression Trees) was introduced by Van den Bos et al. -- a DP framework extending optimal regression trees to piecewise-linear leaf models | \citep{VanDenBosEtAl2024} | | | |
| 29 | 337-338 | qualitative | Van den Bos et al. develop three methods of increasing expressiveness (SRT-C, SRT-SL, SRT-L) | \citep{VanDenBosEtAl2024} | | | |
| 30 | 341-344 | qualitative | SRT-C: An improved DP algorithm for constant-leaf regression trees with a specialized depth-two solver that achieves orders-of-magnitude speedups over previous optimal methods (e.g., 18x faster than OSRT on average) | \citep{VanDenBosEtAl2024} | | | |
| 31 | 346-350 | qualitative | SRT-SL: The first optimal method for piecewise simple linear regression trees. Each leaf fits a one-variable linear model $y = \hat{\beta}_0 + \hat{\beta}_j x_j$, selecting the single best feature $j$ for that leaf. Ridge regularization prevents overfitting | \citep{VanDenBosEtAl2024} | | | |
| 32 | 352-355 | qualitative | SRT-L: The first optimal method for piecewise multiple linear regression trees. Each leaf fits a full linear model with elastic net regularization ($\ell_1 + \ell_2$ penalty), solved via coordinate descent | \citep{VanDenBosEtAl2024} | | | |
| 33 | 362-367 | defining-formula | SRT-SL leaf objective: $\min_{j,\hat{\beta}_0,\hat{\beta}_j} \sum_{(x,b,y) \in \mathcal{D}} (y - \hat{\beta}_0 - x_j \hat{\beta}_j)^2 + \gamma \hat{\beta}_j^2$ | \citep{VanDenBosEtAl2024} | | | |
| 34 | 381-383 | defining-formula | SRT-SL closed-form slope: $\hat{\beta}_j = \frac{n\sum x_j y - \sum y \sum x_j}{n\sum x_j^2 - (\sum x_j)^2 + n\gamma}$ | \citep{VanDenBosEtAl2024} | | | |
| 35 | 385-386 | defining-formula | SRT-SL closed-form intercept: $\hat{\beta}_0 = \frac{\sum y}{n} - \hat{\beta}_j \frac{\sum x_j}{n}$ | \citep{VanDenBosEtAl2024} | | | |
| 36 | 402-411 | qualitative | The depth-two algorithm is the key to STreeD's performance advantage. By precomputing per-instance costs the depth-two solver avoids redundant traversals of the data. Fitting SRT-SL costs almost nothing extra compared to SRT-C because additional statistics can be accumulated in the same pass | \citep{VanDenBosEtAl2024} | | | |
| 37 | 442-443 | attribution | TreeFARMS (Trees FAst RashoMon Sets) was introduced by Xin et al. and was the first algorithm to completely enumerate the Rashomon set for sparse decision trees | \citep{XinEtAl2022} | | | |
| 38 | 443-444 | qualitative | TreeFARMS builds on the GOSDT branch-and-bound framework | \citep{XinEtAl2022} | | | |
| 39 | 449-453 | methodological | TreeFARMS modification 1: Rashomon pruning -- prunes subproblems whose lower bound exceeds the Rashomon threshold $\theta_\epsilon$ instead of optimal objective | \citep{XinEtAl2022} | | | |
| 40 | 455-457 | methodological | TreeFARMS modification 2: Returns all models stored in a compact Model Set data structure | \citep{XinEtAl2022} | | | |
| 41 | 460-467 | qualitative | The Model Set exploits shared subtree components. The loss function for decision trees takes on approximately $n$ distinct values for $n$ training samples, while the number of trees can be orders of magnitude larger. By grouping trees with the same objective, TreeFARMS avoids massive data duplication | \citep{XinEtAl2022} | | | |
| 42 | 480-482 | numerical-fact | On the Bike dataset ($n \approx 17{,}000$, $k = 60$ binary features, depth 5), TreeFARMS requires approximately 700 seconds and over 50 GB of memory | \citep{HeileBabbar2025} | | | |
| 43 | 487-488 | attribution | RESPLIT was introduced by Babbar et al. as an extension of SPLIT to Rashomon set computation | \citep{BabbarEtAl2025} | | | |
| 44 | 495-498 | qualitative | On six benchmark datasets, the Pearson correlation between variable importances computed from the RESPLIT-approximated Rashomon set and the full Rashomon set is nearly 1.0 | \citep{BabbarEtAl2025} | | | |
| 45a | 505 | numerical-fact | COMPAS: Full enumeration 152s, RESPLIT 18s, speedup 8x, correlation 1.000 | \citep{BabbarEtAl2025} | | | Table 1 cited |
| 45b | 506 | numerical-fact | Spambase: Full 2,659s, RESPLIT 154s, speedup 17x, correlation 0.930 | \citep{BabbarEtAl2025} | | | Table 1 cited |
| 45c | 507 | numerical-fact | Netherlands: Full 4,255s, RESPLIT 216s, speedup 20x, correlation 0.932 | \citep{BabbarEtAl2025} | | | Table 1 cited |
| 45d | 508 | numerical-fact | HELOC: Full 5,564s, RESPLIT 337s, speedup 17x, correlation 0.979 | \citep{BabbarEtAl2025} | | | Table 1 cited |
| 45e | 509 | numerical-fact | HIV: Full 9,273s, RESPLIT 388s, speedup 24x, correlation 0.959 | \citep{BabbarEtAl2025} | | | Table 1 cited |
| 45f | 510 | numerical-fact | Bike: Full 14,330s, RESPLIT 194s, speedup 74x, correlation 0.999 | \citep{BabbarEtAl2025} | | | Table 1 cited |
| 46 | 514-516 | methodological | RESPLIT table parameters: 10 bootstrapped datasets, $\lambda = 0.02$, $\epsilon = 0.01$, depth 5, lookahead depth 3 | \citep{BabbarEtAl2025} | | | |
| 47 | 528-529 | attribution | LicketyRESPLIT was introduced by Heile and Babbar | \citep{HeileBabbar2025} | | | |
| 48 | 542-544 | defining-formula | LicketyRESPLIT runtime: $\mathcal{O}(\|R\| n k^3 d^3)$, polynomial in $n$, $k$, $d$, and linear in $|R|$ | \citep{HeileBabbar2025} | | | |
| 49 | 545-546 | defining-formula | LicketyRESPLIT memory: $\mathcal{O}(nk + \sum_{f \in R} S(f))$, proportional to input size plus output size | \citep{HeileBabbar2025} | | | |
| 50a | 559 | numerical-fact | Bike: LicketyRESPLIT 18.8s / 438 MB, TreeFARMS 685s / 51 GB, RESPLIT 184s / 528 MB | \citep{HeileBabbar2025} | | | Table 1 cited |
| 50b | 560 | numerical-fact | Bank: LicketyRESPLIT 123s / 776 MB, TreeFARMS OOM, RESPLIT 238s / 2 GB | \citep{HeileBabbar2025} | | | Table 1 cited |
| 50c | 561 | numerical-fact | Covertype: LicketyRESPLIT 507s / 1.8 GB, TreeFARMS 1819s / 68 GB, RESPLIT 1295s / 3 GB | \citep{HeileBabbar2025} | | | Table 1 cited |
| 50d | 562 | numerical-fact | Student: LicketyRESPLIT 1.7s / 370 MB, TreeFARMS 351s / 4.7 GB, RESPLIT 4.0s / 382 MB | \citep{HeileBabbar2025} | | | Table 1 cited |
| 51 | 566-567 | methodological | LicketyRESPLIT table parameters: $\lambda = 0.01$, $\epsilon_{\text{mult}} = 0.01$, max depth = 5 | \citep{HeileBabbar2025} | | | |
| 52 | 571-572 | numerical-fact | On six benchmark datasets, LicketyRESPLIT precision is $\geq 0.91$ and recall is $\geq 0.90$ across all tested configurations | \citep{HeileBabbar2025} | | | |
| 53 | 620 | attribution | TreeFARMS was published at NeurIPS 2022 | [uncited] | | | Stated in TikZ diagram |
| 54 | 621 | attribution | RESPLIT was published at ICML 2025 | [uncited] | | | Stated in TikZ diagram |
| 55 | 622 | attribution | LicketyRESPLIT was published at NeurIPS 2025 Workshop | [uncited] | | | Stated in TikZ diagram |
| 56 | 640 | attribution | Model Class Reliance (MCR) was introduced by Dong and Rudin (building on the concept from Fisher et al., 2019) | \citep{DongRudin2020} | | | Fisher et al. 2019 not separately cited |
| 57 | 650-652 | defining-formula | Model reliance (ratio form): $mr_j^{\text{ratio}}(f) = \frac{L(f; [X_{\setminus j}, \bar{X}_j], Y)}{L(f; X, Y)}$ | \citep{DongRudin2020} | | | |
| 58 | 671-674 | defining-formula | MCR min/max: $\text{MCR}_{-}(j) = \min_{f \in \mathcal{R}} mr_j(f)$ and $\text{MCR}_{+}(j) = \max_{f \in \mathcal{R}} mr_j(f)$ | \citep{DongRudin2020} | | | |
| 59 | 687-689 | qualitative | TreeFARMS enables exact MCR computation for decision trees by directly calculating variable importance for every tree in the set | \citep{XinEtAl2022} | | | |
| 60 | 695-696 | attribution | Variable Importance Clouds (VIC) were introduced by Dong and Rudin | \citep{DongRudin2020} | | | |
| 61 | 697-707 | defining-formula | VIC definition: $\operatorname{VIC}(\mathcal{R}) = \{MR(f) : f \in \mathcal{R}\}$ where $MR(f) = (mr_1(f), \ldots, mr_p(f))$ | \citep{DongRudin2020} | | | |
| 62 | 711-712 | attribution | Dong and Rudin project the VIC onto pairs of features, producing Variable Importance Diagrams (VIDs) | \citep{DongRudin2020} | | | |
| 63 | 715-717 | qualitative | Non-overlapping VID projections along one axis: the two features have robustly distinct importance levels | \citep{DongRudin2020} | | | |
| 64 | 718-719 | qualitative | Overlapping VID projections: the features are substitutes | \citep{DongRudin2020} | | | |
| 65 | 720-724 | qualitative | Negative slope in the 2D VID projection: the features are direct substitutes -- as one's importance increases the other's decreases. This is the signature of correlated features competing for the same splits | \citep{DongRudin2020} | | | |
| 66 | 775-777 | qualitative | Both the Rashomon set size and the MCR range can vary wildly across bootstrap resamples of the same data, making MCR and VIC unstable summaries of feature importance | \citep{DonnellyEtAl2023} | | | |
| 67 | 778-779 | attribution | Rashomon Importance Distribution (RID) was proposed by Donnelly et al. | \citep{DonnellyEtAl2023} | | | |
| 68 | 780-782 | qualitative | RID combines bootstrap resampling with Rashomon set analysis in a two-level procedure that captures both sources of uncertainty simultaneously | \citep{DonnellyEtAl2023} | | | |
| 69 | 784-785 | attribution | The five-step RID pipeline is illustrated in Figure 2 of Donnelly et al. | \citep{DonnellyEtAl2023} | | | |
| 70 | 811-818 | defining-formula | RID formal definition: $\text{RID}_j(k) = \mathbb{E}_{\mathcal{D}_b^{(n)} \sim \mathcal{P}_n}\left[\frac{\|\{f \in \mathcal{R}_{\mathcal{D}_b}^\varepsilon : \phi_j(f, \mathcal{D}_b^{(n)}) \leq k\}\|}{\|\mathcal{R}_{\mathcal{D}_b}^\varepsilon\|}\right]$ | \citep{DonnellyEtAl2023} | | | |
| 71 | 835-841 | supporting-formula | Empirical RID estimator: $\widehat{\text{RID}}_j(k) = \frac{1}{B}\sum_{b=1}^{B}\frac{\|\{f \in \mathcal{R}_{\mathcal{D}_b}^\varepsilon : \phi_j(f, \mathcal{D}_b^{(n)}) \leq k\}\|}{\|\mathcal{R}_{\mathcal{D}_b}^\varepsilon\|}$ | \citep{DonnellyEtAl2023} | | | |
| 72 | 853-858 | qualitative | Donnelly et al. define the Rashomon set using an additive threshold: $\mathcal{R}^\varepsilon = \{f \in \mathcal{F} : \ell(f) \leq \min_{f'}\ell(f') + \varepsilon\}$, contrasting with the multiplicative threshold of Xin et al. | \citep{DonnellyEtAl2023} | | | |
| 73 | 874-877 | numerical-fact | For one variable on the Monk 3 dataset, the MCR range is $[-0.1, 0.33]$ on one resample and $[0.33, 0.36]$ on another -- contradictory conclusions from the same underlying data | \citep{DonnellyEtAl2023} | | | |
| 74 | 897-905 | defining-formula | RID convergence guarantee (Theorem 2): $\|\widehat{\text{RID}}_j(k) - \text{RID}_j(k)\| \leq t$ for all $k$, with probability $\geq 1 - \delta$, when $B \geq \frac{1}{2t^2}\ln\frac{2}{\delta}$ | \citep{DonnellyEtAl2023} | | | |
| 75 | 906-908 | numerical-fact | $B = 471$ bootstraps guarantees that the estimated RID is within $t = 0.075$ of the true value with 90% confidence | \citep{DonnellyEtAl2023} | | | Derived from Theorem 2 |
| 76 | 910-913 | qualitative | RID works with any variable importance metric $\phi_j$ -- permutation importance, SHAP, model reliance, conditional model reliance, or any other metric with a bounded range. The framework treats $\phi_j$ as a black box | \citep{DonnellyEtAl2023} | | | |
| 77 | 917-920 | numerical-fact | On four synthetic data-generating processes, RID achieves a median Jaccard similarity of 0.69 across independently generated datasets, compared to below 0.55 for both MCR and VIC | \citep{DonnellyEtAl2023} | | | |
| 78 | 943-944 | qualitative | No published work has applied Rashomon set analysis to financial time-series forecasting (as of writing) | [uncited] | | | |
| 79 | 1017-1019 | qualitative | The tools (TreeFARMS, RESPLIT, LicketyRESPLIT) have been demonstrated on tabular classification datasets (COMPAS, FICO, UCI benchmarks) | [uncited] | | | |
