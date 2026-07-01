# Formula Registry

Central audit file mapping every mathematical function to its source paper, implementation, and test.

**Last Full Audit:** 2026-05-29

---

## Verification Protocol

When adding a new formula to the codebase:

1. **Identify source paper** — Full citation (Author, Year, Journal, Volume, Pages)
2. **Record equation number** — Exact equation/theorem/definition reference
3. **Create gold values** — Hand-compute expected outputs for small inputs; record computation steps in JSON
4. **Write formula test** — In `tests/unit/formulas/test_<topic>_formulas.py` with `pytestmark = pytest.mark.formula`
5. **Add naive reference** — Pure-Python loop implementation as cross-check (for complex formulas)
6. **Update this registry** — Add row to the table below
7. **Run `pytest -m formula`** — All formula tests must pass

---

## Formula Table

| Function | Paper | Equation | Implementation | Test File | Gold Values |
|----------|-------|----------|----------------|-----------|-------------|
| `compute_realized_variance` | Andersen, Bollerslev, Diebold & Labys (2003) Econometrica 71(2) | Eq. (1) | `data/measures.py` | `test_rv_formulas.py` | `gold_values/rv.json` |
| `compute_rq` | Barndorff-Nielsen & Shephard (2002) JRSSB 64(2) | Definition 2 | `data/measures.py` | `test_quarticity_formulas.py` | `gold_values/rq_rtq.json` |
| `compute_bpv` | Barndorff-Nielsen & Shephard (2004) J. Fin. Econometrics 2(1) | Eq. (3) | `data/measures.py` | `test_bpv_formulas.py` | `gold_values/bpv.json` |
| `compute_semivariances` | Barndorff-Nielsen, Kinnebrock & Shephard (2010) OUP | Eq. (2.1) | `data/measures.py` | `test_semivariance_formulas.py` | `gold_values/semivariances.json` |
| `realized_kernel` | Barndorff-Nielsen, Hansen, Lunde & Shephard (2008) Econometrica 76(6) | Eq. (3.1) | `data/measures.py` | `test_realized_kernel_formulas.py` | `gold_values/realized_kernel.json` |
| `compute_realized_tripower_quarticity` | Barndorff-Nielsen & Shephard (2004) J. Fin. Econometrics 2(1) | Eq. (5) | `data/measures.py` | `test_quarticity_formulas.py` | `gold_values/rq_rtq.json` |
| `detect_jumps` | Barndorff-Nielsen & Shephard (2006) J. Fin. Econometrics 4(1) | Theorem 2 | `data/measures.py` | `test_jump_detection_formulas.py` | `gold_values/jump_detection.json` |
| `compute_realized_moments` | Amaya, Christoffersen, Jacobs & Vasquez (2015) JFE 118(1) | **GAP** | `data/measures.py` | `test_realized_moments_formulas.py` | `gold_values/realized_moments.json` |
| `qlike` | Patton (2011) J. Econometrics 160(1) | Eq. (5) | `evaluation/metrics.py` | `test_qlike_formulas.py` | `gold_values/qlike.json` |
| `diebold_mariano_test` | Diebold & Mariano (1995) JBES 13(3) | Section 2 | `evaluation/statistical_tests.py` | `test_dm_test_formulas.py` | `gold_values/dm_test.json` |
| `compute_vrp` | Carr & Wu (2009) RFS 22(3) | Ex-post proxy | `features/options.py` | `test_vrp_formulas.py` | `gold_values/vrp.json` |
| `noise_gap` | — (derived metric) | `(RK - RV) / RV` | `data/measures.py` | `test_realized_kernel_formulas.py` | — |

---

## Papers Referenced (Full Bibliography)

1. Amaya, D., Christoffersen, P., Jacobs, K. & Vasquez, A. (2015) "Does Realized Skewness Predict the Cross-Section of Equity Returns?", *Journal of Financial Economics*, 118(1), pp. 135-167. DOI: 10.1016/j.jfineco.2015.02.009

2. Andersen, T.G., Bollerslev, T., Diebold, F.X. & Labys, P. (2003) "Modeling and Forecasting Realized Volatility", *Econometrica*, 71(2), pp. 579-625. DOI: 10.1111/1468-0262.00418

3. Barndorff-Nielsen, O.E., Hansen, P.R., Lunde, A. & Shephard, N. (2008) "Designing Realized Kernels to Measure the Ex Post Variation of Equity Prices in the Presence of Noise", *Econometrica*, 76(6), pp. 1481-1536. DOI: 10.3982/ECTA6495

4. Barndorff-Nielsen, O.E., Kinnebrock, S. & Shephard, N. (2010) "Measuring Downside Risk - Realised Semivariance", in Bollerslev, T., Russell, J. & Watson, M. (eds) *Volatility and Time Series Econometrics: Essays in Honor of Robert Engle*, Oxford University Press.

5. Barndorff-Nielsen, O.E. & Shephard, N. (2002) "Econometric Analysis of Realized Volatility and its Use in Estimating Stochastic Volatility Models", *Journal of the Royal Statistical Society Series B*, 64(2), pp. 253-280. DOI: 10.1111/1467-9868.00336

6. Barndorff-Nielsen, O.E. & Shephard, N. (2004) "Power and Bipower Variation with Stochastic Volatility and Jumps", *Journal of Financial Econometrics*, 2(1), pp. 1-37. DOI: 10.1093/jjfinec/nbh001

7. Barndorff-Nielsen, O.E. & Shephard, N. (2006) "Econometrics of Testing for Jumps in Financial Economics Using Bipower Variation", *Journal of Financial Econometrics*, 4(1), pp. 1-30. DOI: 10.1093/jjfinec/nbh013

8. Bollerslev, T., Tauchen, G. & Zhou, H. (2009) "Expected Stock Returns and Variance Risk Premia", *Review of Financial Studies*, 22(11), pp. 4463-4492. DOI: 10.1093/rfs/hhp008

9. Carr, P. & Wu, L. (2009) "Variance Risk Premiums", *Review of Financial Studies*, 22(3), pp. 1311-1341. DOI: 10.1093/rfs/hhn038

10. Diebold, F.X. & Mariano, R.S. (1995) "Comparing Predictive Accuracy", *Journal of Business & Economic Statistics*, 13(3), pp. 253-263. DOI: 10.1080/07350015.1995.10524599

11. Patton, A.J. (2011) "Volatility Forecast Comparison Using Imperfect Volatility Proxies", *Journal of Econometrics*, 160(1), pp. 246-256. DOI: 10.1016/j.jeconom.2010.03.034

---

## Known Gaps

| Formula | Issue | Status |
|---------|-------|--------|
| `compute_realized_moments` | Exact equation number from Amaya et al. (2015) not verified against paper | **OPEN** — need to check original paper Table 1 or Section 2 |
| Conditional VRP (iv_features.py) | Uses HAR-based E[RV] as proxy for Bollerslev (2009) conditional expectation; fallback to rolling mean when data < 100 obs | Documented, tested in `test_iv_features.py` |
| DM test HAC bandwidth | Implementation uses floor(T^{1/3}); DM 1995 does not prescribe exact bandwidth formula | Documented, standard choice in econometrics |

---

## Tolerance Policy

| Category | Tolerance | Rationale |
|----------|-----------|-----------|
| Pure arithmetic (RV, RQ, BPV, semivariances) | `abs=1e-15` | Floating-point sum of products, no iteration |
| Functions using pi/gamma constants | `rel=1e-12` | Constants from `math`/`scipy.special` have machine precision |
| Convergence tests (RK, GBM -> IV) | `rel=0.30` max | Finite-sample bias, kernel tapering effects |
| Statistical tests (DM) | `abs=0.5` for stat | Sampling variability in HAC variance estimate |
| Cross-reference (naive vs vectorized) | `rel=1e-12` | Both should produce identical results |
