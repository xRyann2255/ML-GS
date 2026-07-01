"""HAR-family baseline models (Layer 0 models).

Implements the standard HAR model family for realized volatility forecasting:
- HAR: Heterogeneous Autoregressive (Corsi 2009)
- HARQ: HAR with measurement quality (Bollerslev et al. 2016)
- SHAR: Semivariance HAR (Patton & Sheppard 2015)
- HAR-J: HAR with jump component
- HAR-CJ: HAR with continuous and jump components
- Ridge-HAR: L2-regularized HAR
- Lasso-HAR: L1-regularized HAR

All models operate in log-RV space and use OLS or regularized regression.
"""

from __future__ import annotations

import pandas as pd

from volforecast.models._base import _BaseOLS
from volforecast.registry import register_model

# _BaseHAR is now an alias for _BaseOLS (backward compat)
_BaseHAR = _BaseOLS


@register_model("har")
class HARModel(_BaseHAR):
    """Standard HAR(1,5,22) model.

    log(RV_{t+1}) = β₀ + β_d·log(RV_t) + β_w·log(RV_t^w) + β_m·log(RV_t^m)
    """

    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARModel:
        self._fit(X, y)
        return self


@register_model("harq")
class HARQModel(_BaseHAR):
    """HARQ model with RQ interaction terms (Bollerslev et al. 2016).

    Paper spec: log_rv_{t+1} = β0 + (β_d + β_dQ * sqrt(RQ_t)) * log_rv_d
                                    + β_w * log_rv_w + β_m * log_rv_m

    Uses 4 features (not 5): standalone sqrt_rq_d is excluded because it has
    ρ=-0.996 correlation with rq_rv_interaction_d, causing catastrophic
    multicollinearity in OLS.
    """

    _FEATURES = [
        "log_rv_d",
        "log_rv_w",
        "log_rv_m",
        "rq_rv_interaction_d",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARQModel:
        self._fit(X, y)
        return self


@register_model("shar")
class SHARModel(_BaseHAR):
    """Semivariance HAR (Patton & Sheppard 2015).

    Paper spec: only the DAILY term is decomposed into RS⁺/RS⁻.
    Weekly and monthly remain as total RV averages.
    RV_{t+1} = β0 + β⁺ RS⁺_t + β⁻ RS⁻_t + β_w RV^(w)_t + β_m RV^(m)_t
    """

    REQUIRED_LAYERS = ["har_core", "asymmetry"]
    _FEATURES = [
        "log_rs_positive_d",
        "log_rs_negative_d",
        "log_rv_w",
        "log_rv_m",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> SHARModel:
        self._fit(X, y)
        return self


@register_model("har_j")
class HARJModel(_BaseHAR):
    """HAR-J: HAR with jump variation as additional predictor."""

    REQUIRED_LAYERS = ["har_core", "asymmetry"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_jump_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARJModel:
        self._fit(X, y)
        return self


@register_model("har_cj")
class HARCJModel(_BaseHAR):
    """HAR-CJ: HAR with separate continuous and jump regressors."""

    REQUIRED_LAYERS = ["har_core", "asymmetry"]
    _FEATURES = ["log_cont_d", "log_cont_w", "log_rv_m", "log_jump_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARCJModel:
        self._fit(X, y)
        return self


@register_model("ridge_har")
class RidgeHARModel(_BaseHAR):
    """Ridge-regularized HAR model (L2 penalty) with feature standardization."""

    REQUIRED_LAYERS = ["har_core", "asymmetry"]
    # Explicit feature list: all HAR-family features from har_core + asymmetry.
    # Without this, pooled tournaments with extra layers (options, calendar)
    # feed 50+ irrelevant columns into the scaler, causing catastrophic
    # predictions during regime changes (e.g. COVID vol spike).
    _FEATURES = [
        # har_core
        "log_rv_d",
        "log_rv_w",
        "log_rv_m",
        "rq_rv_interaction_d",
        "sqrt_rq_d",
        "overnight_return",
        # asymmetry
        "log_rs_positive_d",
        "log_rs_positive_w",
        "log_rs_positive_m",
        "log_rs_negative_d",
        "log_rs_negative_w",
        "log_rs_negative_m",
        "log_bpv_d",
        "log_bpv_w",
        "log_jump_d",
        "log_cont_d",
        "log_cont_w",
        "signed_return_d",
    ]

    def __init__(self, alpha: float = 1.0) -> None:
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import Pipeline as SKPipeline
        from sklearn.preprocessing import StandardScaler

        pipe = SKPipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
        super().__init__(model=pipe)
        self.alpha = alpha

    def fit(self, X: pd.DataFrame, y: pd.Series) -> RidgeHARModel:
        self._fit(X, y)
        return self


@register_model("lasso_har")
class LassoHARModel(_BaseHAR):
    """Lasso-regularized HAR model (L1 penalty) with feature standardization.

    Uses ElasticNet with l1_ratio=0.95 (95% L1, 5% L2). The small L2
    component resolves multicollinearity in correlated log-RV features,
    dramatically improving convergence speed without meaningfully
    affecting sparsity. This is standard practice per Zou & Hastie (2005).
    """

    REQUIRED_LAYERS = ["har_core", "asymmetry"]
    # Same feature whitelist as RidgeHAR — restrict to HAR-family features
    # so extra layers in the tournament config don't contaminate predictions.
    _FEATURES = [
        # har_core
        "log_rv_d",
        "log_rv_w",
        "log_rv_m",
        "rq_rv_interaction_d",
        "sqrt_rq_d",
        "overnight_return",
        # asymmetry
        "log_rs_positive_d",
        "log_rs_positive_w",
        "log_rs_positive_m",
        "log_rs_negative_d",
        "log_rs_negative_w",
        "log_rs_negative_m",
        "log_bpv_d",
        "log_bpv_w",
        "log_jump_d",
        "log_cont_d",
        "log_cont_w",
        "signed_return_d",
    ]

    def __init__(self, alpha: float = 0.01, l1_ratio: float = 0.95) -> None:
        from sklearn.linear_model import ElasticNet
        from sklearn.pipeline import Pipeline as SKPipeline
        from sklearn.preprocessing import StandardScaler

        pipe = SKPipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "lasso",
                    ElasticNet(
                        alpha=alpha,
                        l1_ratio=l1_ratio,
                        max_iter=2000,
                        tol=1e-3,
                        selection="random",
                    ),
                ),
            ]
        )
        super().__init__(model=pipe)
        self.alpha = alpha
        self.l1_ratio = l1_ratio

    def fit(self, X: pd.DataFrame, y: pd.Series) -> LassoHARModel:
        self._fit(X, y)
        return self


@register_model("har_iv")
class HARIVModel(_BaseHAR):
    """HAR-IV: HAR augmented with per-symbol ATM implied volatility.

    log(RV_{t+h}) = β₀ + β_d·log(RV_t) + β_w·log(RV_t^w) + β_m·log(RV_t^m)
                        + β_iv·log(atm_iv_t)

    Motivation: ATM IV is the option market's consensus forecast of future RV.
    At h=22, naive IV (QLIKE 0.1925) beats HAR (0.2087) by 800 bps. This model
    tests whether linearly combining historical RV memory with the market's
    forward view closes that gap. If β_iv dominates at h=22 and β_d dominates
    at h=1, the model adapts optimally to each horizon.

    Requires options layer (which provides log_atm_iv_d).
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIVModel:
        self._fit(X, y)
        return self


@register_model("har_iv_1w")
class HARIV1wModel(_BaseHAR):
    """HAR-IV-1w: HAR augmented with 1-week ATM IV (horizon-matched for h=1/h=5).

    log(RV_{t+h}) = β₀ + β_d·log(RV_t) + β_w·log(RV_t^w) + β_m·log(RV_t^m)
                        + β_iv·log(atm_iv_1w_t)

    Motivation: 1w ATM IV is the closest available tenor to the h=1 (1-day) and
    h=5 (5-day = 1 week) forecast horizons. By tenor-matching, the IV signal
    reflects exactly the market's expectation for the forecast window rather than
    the 30-day average priced into 1m IV. At h=22, 1m IV remains optimal.

    Requires options layer with iv_1w_atm available in data.
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_1w_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIV1wModel:
        self._fit(X, y)
        return self


@register_model("har_iv_0dte")
class HARIV0dteModel(_BaseHAR):
    """HAR-IV-0DTE: HAR augmented with 0DTE ATM IV (exact tenor match for h=1).

    log(RV_{t+h}) = β₀ + β_d·log(RV_t) + β_w·log(RV_t^w) + β_m·log(RV_t^m)
                        + β_iv·log(atm_iv_0dte_t)

    Motivation: 0DTE ATM IV is the option market's exact pricing of next-day
    realized vol. For h=1 forecasting, this is the tightest tenor match — no
    term-premium contamination from longer expiries. EDRVOL_PERCENT_EXPIRY
    provides forward-looking 0DTE quotes (tomorrow's expiry observed at today's
    close).

    Requires options layer with iv_0dte_atm available in data.
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_0dte_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIV0dteModel:
        self._fit(X, y)
        return self


@register_model("har_iv_1dte")
class HARIV1dteModel(_BaseHAR):
    """HAR-IV-1DTE: HAR augmented with 1DTE ATM IV (tomorrow's expiry).

    log(RV_{t+h}) = β₀ + β_d·log(RV_t) + β_w·log(RV_t^w) + β_m·log(RV_t^m)
                        + β_iv·log(atm_iv_1dte_t)

    Motivation: 1DTE ATM IV is the option market's pricing of TOMORROW's
    realized vol observed at today's close. Unlike 0DTE (which prices
    today's remaining variance and may be stale/backward-looking by close),
    1DTE is purely forward-looking: its time value = E[variance over next
    trading day]. This is the correct apples-to-apples comparand for a
    model predicting RV_{t+1}.

    Requires options layer with iv_1dte_atm available in data.
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_1dte_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIV1dteModel:
        self._fit(X, y)
        return self


@register_model("har_iv_0dte_1dte")
class HARIV0dte1dteModel(_BaseHAR):
    """HAR-IV with BOTH 0DTE and 1DTE ATM IV (5 regressors).

    log(RV_{t+h}) = β₀ + β_d·log(RV_t) + β_w·log(RV_t^w) + β_m·log(RV_t^m)
                        + β_0dte·log(atm_iv_0dte_t) + β_1dte·log(atm_iv_1dte_t)

    Motivation: 0DTE IV at close is partly backward-looking (reflects today's
    realized intraday vol) while 1DTE is forward-looking (prices tomorrow's
    expected vol). Including both lets the model separately weight:
      - The "persistence" signal (0DTE ≈ proxy for today's actual vol regime)
      - The "expectation" signal (1DTE ≈ market's forward view of tomorrow)
    If the model assigns positive β_1dte and zero/negative β_0dte, that
    confirms 1DTE carries incremental forward signal beyond what log_rv_d
    and 0DTE already capture.

    Requires options layer with both iv_0dte_atm and iv_1dte_atm available.
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_0dte_d", "log_atm_iv_1dte_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIV0dte1dteModel:
        self._fit(X, y)
        return self


@register_model("har_iv_vvix")
class HARIVVvixModel(_BaseHAR):
    """HAR-IV + VVIX: adds vol-of-vol signal (strongest h=22 predictor in ablation)."""

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_d", "vvix_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIVVvixModel:
        self._fit(X, y)
        return self


@register_model("har_iv_skew")
class HARIVSkewModel(_BaseHAR):
    """HAR-IV + skew: adds risk-reversal (tail fear signal)."""

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_d", "iv_skew_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIVSkewModel:
        self._fit(X, y)
        return self


@register_model("har_iv_term")
class HARIVTermModel(_BaseHAR):
    """HAR-IV + term slope: adds IV term structure (3m-1m) for mean-reversion signal."""

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_d", "iv_term_slope_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIVTermModel:
        self._fit(X, y)
        return self


@register_model("har_iv_rich")
class HARIVRichModel(_BaseHAR):
    """HAR-IV-Rich: HAR + ATM IV + VVIX + skew + term slope (7 params).

    Tests if richer IV surface description adds beyond ATM IV alone.
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = [
        "log_rv_d",
        "log_rv_w",
        "log_rv_m",
        "log_atm_iv_d",
        "vvix_d",
        "iv_skew_d",
        "iv_term_slope_d",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIVRichModel:
        self._fit(X, y)
        return self


@register_model("har_iv_vrp")
class HARIVVrpModel(_BaseHAR):
    """HAR-IV-VRP: replaces raw ATM IV with VRP (IV^2 - RV*252).

    Tests if the premium signal (forward-looking minus backward-looking)
    is more informative than the level.
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "vrp_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIVVrpModel:
        self._fit(X, y)
        return self


@register_model("har_iv_kitchen")
class HARIVKitchenModel(_BaseHAR):
    """HAR-IV-Kitchen: all IV surface signals (8 params).

    HAR core + ATM IV + VVIX + skew + term slope + VRP.
    Maximum IV information content test.
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = [
        "log_rv_d",
        "log_rv_w",
        "log_rv_m",
        "log_atm_iv_d",
        "vvix_d",
        "iv_skew_d",
        "iv_term_slope_d",
        "vrp_d",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIVKitchenModel:
        self._fit(X, y)
        return self


@register_model("har_iv_freq")
class HARIVFreqModel(_BaseHAR):
    """HAR-IV-Freq: Busch, Christensen & Nielsen (2011) spec.

    Uses IV in matching frequency structure (d/w/m) alongside RV (d/w/m):
    log(RV_{t+h}) = β₀ + β_d·log(RV_d) + β_w·log(RV_w) + β_m·log(RV_m)
                        + γ_d·log(IV_d) + γ_w·log(IV_w) + γ_m·log(IV_m)

    This is the canonical HAR-IV from the literature. The key insight from
    Busch et al.: IV's frequency decomposition captures IV persistence/momentum
    independently from RV persistence. At longer horizons, IV_m (monthly avg IV)
    dominates because it smooths out microstructure noise in daily IV.

    6 parameters. Should dominate our simpler har_iv (4 params) if IV
    persistence carries independent signal beyond the level.
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = [
        "log_rv_d",
        "log_rv_w",
        "log_rv_m",
        "log_atm_iv_d",
        "log_atm_iv_w",
        "log_atm_iv_m",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIVFreqModel:
        self._fit(X, y)
        return self


@register_model("har_iv_freq_vrp")
class HARIVFreqVrpModel(_BaseHAR):
    """HAR-IV-Freq + VRP: Busch et al. (2011) + Bollerslev-Tauchen-Zhou (2009).

    Full frequency-matched IV lags + VRP as orthogonal predictor.
    VRP = (IV/100)^2 - RV*252 captures the risk premium spread, which predicts
    both returns AND future vol through mean-reversion of the premium.

    7 parameters. Tests if VRP adds beyond the IV frequency structure.
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = [
        "log_rv_d",
        "log_rv_w",
        "log_rv_m",
        "log_atm_iv_d",
        "log_atm_iv_w",
        "log_atm_iv_m",
        "vrp_d",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIVFreqVrpModel:
        self._fit(X, y)
        return self


@register_model("har_iv_optimal")
class HARIVOptimalModel(_BaseHAR):
    """HAR-IV-Optimal: best of literature combined.

    Busch et al. frequency structure + VRP (BTZ 2009) + term slope
    (regime indicator, inverts pre-crisis) + VVIX (vol-of-vol, strongest
    h=22 signal per trial-011 ablation).

    9 parameters. The maximal linear model before overfitting risk.
    This is the "if OLS could see everything options tell us" test.
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = [
        "log_rv_d",
        "log_rv_w",
        "log_rv_m",
        "log_atm_iv_d",
        "log_atm_iv_w",
        "log_atm_iv_m",
        "vrp_d",
        "iv_term_slope_d",
        "vvix_d",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIVOptimalModel:
        self._fit(X, y)
        return self


# ---------------------------------------------------------------------------
# HAR-IV + Cross-Asset models (trial-031c)
# ---------------------------------------------------------------------------


@register_model("har_iv_xasset")
class HARIVXAssetModel(_BaseHAR):
    """HAR-IV + Cross-Asset: linear model with market-wide signals.

    Tests whether cross-asset features (treasury slope, FX vol, commodity vol,
    VIX/RV ratio) improve on HAR-IV in a linear framework, where overfitting
    risk is lower than in LightGBM (trial-031b showed trees overfit to these).

    8 parameters: HAR core (3) + ATM IV (1) + cross-asset (4).
    """

    REQUIRED_LAYERS = ["har_core", "options", "cross_asset"]
    _FEATURES = [
        "log_rv_d",
        "log_rv_w",
        "log_rv_m",
        "log_atm_iv_d",
        "treasury_slope_d",
        "log_fx_vol_d",
        "log_commodity_vol_cl_d",
        "log_vix_rv_ratio_d",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIVXAssetModel:
        self._fit(X, y)
        return self


@register_model("ridge_har_iv")
class RidgeHARIVModel(_BaseHAR):
    """Ridge-regularized HAR-IV model (L2 penalty).

    Same features as har_iv (log_rv_d/w/m + log_atm_iv_d) but with Ridge
    regularization + StandardScaler. Ridge preserves all 4 terms (no sparsity)
    while damping collinear HAR components.
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_d"]

    def __init__(self, alpha: float = 1.0) -> None:
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import Pipeline as SKPipeline
        from sklearn.preprocessing import StandardScaler

        pipe = SKPipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
        super().__init__(model=pipe)
        self.alpha = alpha

    def fit(self, X: pd.DataFrame, y: pd.Series) -> RidgeHARIVModel:
        self._fit(X, y)
        return self


@register_model("ridge_har_iv_1w")
class RidgeHARIV1wModel(_BaseHAR):
    """Ridge-regularized HAR-IV-1w (1-week tenor, for h=1/h=5)."""

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_1w_d"]

    def __init__(self, alpha: float = 1.0) -> None:
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import Pipeline as SKPipeline
        from sklearn.preprocessing import StandardScaler

        pipe = SKPipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
        super().__init__(model=pipe)
        self.alpha = alpha

    def fit(self, X: pd.DataFrame, y: pd.Series) -> RidgeHARIV1wModel:
        self._fit(X, y)
        return self


@register_model("lasso_har_iv")
class LassoHARIVModel(_BaseHAR):
    """Lasso-regularized HAR-IV model (L1 penalty).

    Uses ElasticNet with l1_ratio=0.95 internally (5% L2 for convergence).
    On only 4 features the sparsity pressure may zero out weak terms,
    testing which of RV components vs IV carries the signal.
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_d"]

    def __init__(self, alpha: float = 0.01, l1_ratio: float = 0.95) -> None:
        from sklearn.linear_model import ElasticNet
        from sklearn.pipeline import Pipeline as SKPipeline
        from sklearn.preprocessing import StandardScaler

        pipe = SKPipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "lasso",
                    ElasticNet(
                        alpha=alpha,
                        l1_ratio=l1_ratio,
                        max_iter=2000,
                        tol=1e-3,
                        selection="random",
                    ),
                ),
            ]
        )
        super().__init__(model=pipe)
        self.alpha = alpha
        self.l1_ratio = l1_ratio

    def fit(self, X: pd.DataFrame, y: pd.Series) -> LassoHARIVModel:
        self._fit(X, y)
        return self


@register_model("lasso_har_iv_1w")
class LassoHARIV1wModel(_BaseHAR):
    """Lasso-regularized HAR-IV-1w (1-week tenor, for h=1/h=5)."""

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_1w_d"]

    def __init__(self, alpha: float = 0.01, l1_ratio: float = 0.95) -> None:
        from sklearn.linear_model import ElasticNet
        from sklearn.pipeline import Pipeline as SKPipeline
        from sklearn.preprocessing import StandardScaler

        pipe = SKPipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "lasso",
                    ElasticNet(
                        alpha=alpha,
                        l1_ratio=l1_ratio,
                        max_iter=2000,
                        tol=1e-3,
                        selection="random",
                    ),
                ),
            ]
        )
        super().__init__(model=pipe)
        self.alpha = alpha
        self.l1_ratio = l1_ratio

    def fit(self, X: pd.DataFrame, y: pd.Series) -> LassoHARIV1wModel:
        self._fit(X, y)
        return self


@register_model("elasticnet_har_iv")
class ElasticNetHARIVModel(_BaseHAR):
    """Elastic Net HAR-IV (50/50 L1+L2 blend).

    Balanced penalty: L1 enables sparsity (can zero weak terms) while L2
    handles collinearity in the HAR core. l1_ratio=0.5 is the canonical
    elastic net midpoint (Zou & Hastie 2005).
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_d"]

    def __init__(self, alpha: float = 0.01, l1_ratio: float = 0.5) -> None:
        from sklearn.linear_model import ElasticNet
        from sklearn.pipeline import Pipeline as SKPipeline
        from sklearn.preprocessing import StandardScaler

        pipe = SKPipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "enet",
                    ElasticNet(
                        alpha=alpha,
                        l1_ratio=l1_ratio,
                        max_iter=2000,
                        tol=1e-3,
                        selection="random",
                    ),
                ),
            ]
        )
        super().__init__(model=pipe)
        self.alpha = alpha
        self.l1_ratio = l1_ratio

    def fit(self, X: pd.DataFrame, y: pd.Series) -> ElasticNetHARIVModel:
        self._fit(X, y)
        return self


@register_model("elasticnet_har_iv_1w")
class ElasticNetHARIV1wModel(_BaseHAR):
    """Elastic Net HAR-IV-1w (1-week tenor, for h=1/h=5)."""

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_1w_d"]

    def __init__(self, alpha: float = 0.01, l1_ratio: float = 0.5) -> None:
        from sklearn.linear_model import ElasticNet
        from sklearn.pipeline import Pipeline as SKPipeline
        from sklearn.preprocessing import StandardScaler

        pipe = SKPipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "enet",
                    ElasticNet(
                        alpha=alpha,
                        l1_ratio=l1_ratio,
                        max_iter=2000,
                        tol=1e-3,
                        selection="random",
                    ),
                ),
            ]
        )
        super().__init__(model=pipe)
        self.alpha = alpha
        self.l1_ratio = l1_ratio

    def fit(self, X: pd.DataFrame, y: pd.Series) -> ElasticNetHARIV1wModel:
        self._fit(X, y)
        return self


@register_model("ridge_har_iv_0dte")
class RidgeHARIV0dteModel(_BaseHAR):
    """Ridge-regularized HAR-IV-0DTE (0DTE tenor, exact match for h=1)."""

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_0dte_d"]

    def __init__(self, alpha: float = 1.0) -> None:
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import Pipeline as SKPipeline
        from sklearn.preprocessing import StandardScaler

        pipe = SKPipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
        super().__init__(model=pipe)
        self.alpha = alpha

    def fit(self, X: pd.DataFrame, y: pd.Series) -> RidgeHARIV0dteModel:
        self._fit(X, y)
        return self


@register_model("lasso_har_iv_0dte")
class LassoHARIV0dteModel(_BaseHAR):
    """Lasso-regularized HAR-IV-0DTE (0DTE tenor, exact match for h=1)."""

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_0dte_d"]

    def __init__(self, alpha: float = 0.01, l1_ratio: float = 0.95) -> None:
        from sklearn.linear_model import ElasticNet
        from sklearn.pipeline import Pipeline as SKPipeline
        from sklearn.preprocessing import StandardScaler

        pipe = SKPipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "lasso",
                    ElasticNet(
                        alpha=alpha,
                        l1_ratio=l1_ratio,
                        max_iter=2000,
                        tol=1e-3,
                        selection="random",
                    ),
                ),
            ]
        )
        super().__init__(model=pipe)
        self.alpha = alpha
        self.l1_ratio = l1_ratio

    def fit(self, X: pd.DataFrame, y: pd.Series) -> LassoHARIV0dteModel:
        self._fit(X, y)
        return self


@register_model("elasticnet_har_iv_0dte")
class ElasticNetHARIV0dteModel(_BaseHAR):
    """Elastic Net HAR-IV-0DTE (0DTE tenor, exact match for h=1)."""

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_0dte_d"]

    def __init__(self, alpha: float = 0.01, l1_ratio: float = 0.5) -> None:
        from sklearn.linear_model import ElasticNet
        from sklearn.pipeline import Pipeline as SKPipeline
        from sklearn.preprocessing import StandardScaler

        pipe = SKPipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "enet",
                    ElasticNet(
                        alpha=alpha,
                        l1_ratio=l1_ratio,
                        max_iter=2000,
                        tol=1e-3,
                        selection="random",
                    ),
                ),
            ]
        )
        super().__init__(model=pipe)
        self.alpha = alpha
        self.l1_ratio = l1_ratio

    def fit(self, X: pd.DataFrame, y: pd.Series) -> ElasticNetHARIV0dteModel:
        self._fit(X, y)
        return self


@register_model("ridge_har_iv_xasset")
class RidgeHARIVXAssetModel(_BaseHAR):
    """Ridge HAR-IV + Cross-Asset: regularized version (13 parameters).

    Adds the full cross-asset feature set with Ridge regularization.
    More features than OLS variant — includes weekly smoothing + VIX levels.
    StandardScaler prevents scale-driven coefficient bias.

    13 parameters: HAR core (3) + ATM IV (1) + cross-asset (9).
    """

    REQUIRED_LAYERS = ["har_core", "options", "cross_asset"]
    _FEATURES = [
        "log_rv_d",
        "log_rv_w",
        "log_rv_m",
        "log_atm_iv_d",
        "treasury_slope_d",
        "treasury_slope_w",
        "log_fx_vol_d",
        "log_fx_vol_w",
        "log_commodity_vol_cl_d",
        "log_vix_d",
        "log_vix_w",
        "log_vix_m",
        "log_vix_rv_ratio_d",
    ]

    def __init__(self, alpha: float = 1.0) -> None:
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import Pipeline as SKPipeline
        from sklearn.preprocessing import StandardScaler

        pipe = SKPipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
        super().__init__(model=pipe)
        self.alpha = alpha

    def fit(self, X: pd.DataFrame, y: pd.Series) -> RidgeHARIVXAssetModel:
        self._fit(X, y)
        return self


# ---------------------------------------------------------------------------
# HAR-X IV Rich models (trial-035): tenor-matched IV + VIX + VRP + returns
# ---------------------------------------------------------------------------

# Common features shared by all HAR-X IV Rich variants (minus the IV tenor column)
_HARX_COMMON = [
    "log_rv_d",
    "log_rv_w",
    "log_rv_m",
    "log_vix_d",
    "vvix_innovation_d",
    "signed_return_d",
    "vrp_d",
]


def _make_ridge_pipe(alpha: float = 1.0):
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline as SKPipeline
    from sklearn.preprocessing import StandardScaler

    return SKPipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=alpha))])


def _make_lasso_pipe(alpha: float = 0.01, l1_ratio: float = 0.95):
    from sklearn.linear_model import ElasticNet
    from sklearn.pipeline import Pipeline as SKPipeline
    from sklearn.preprocessing import StandardScaler

    return SKPipeline(
        [
            ("scaler", StandardScaler()),
            (
                "lasso",
                ElasticNet(
                    alpha=alpha, l1_ratio=l1_ratio, max_iter=2000, tol=1e-3, selection="random"
                ),
            ),
        ]
    )


def _make_enet_pipe(alpha: float = 0.01, l1_ratio: float = 0.5):
    from sklearn.linear_model import ElasticNet
    from sklearn.pipeline import Pipeline as SKPipeline
    from sklearn.preprocessing import StandardScaler

    return SKPipeline(
        [
            ("scaler", StandardScaler()),
            (
                "enet",
                ElasticNet(
                    alpha=alpha, l1_ratio=l1_ratio, max_iter=2000, tol=1e-3, selection="random"
                ),
            ),
        ]
    )


# --- h=1: 0DTE IV ---


@register_model("harx_iv_h1")
class HARXIvH1Model(_BaseHAR):
    """HAR-X with 0DTE IV + VIX + VIX innovation + return + VRP (h=1 optimized)."""

    REQUIRED_LAYERS = ["har_core", "options", "asymmetry", "cross_asset"]
    _FEATURES = [*_HARX_COMMON, "log_atm_iv_0dte_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARXIvH1Model:
        self._fit(X, y)
        return self


@register_model("ridge_harx_iv_h1")
class RidgeHARXIvH1Model(_BaseHAR):
    """Ridge HAR-X with 0DTE IV (h=1)."""

    REQUIRED_LAYERS = ["har_core", "options", "asymmetry", "cross_asset"]
    _FEATURES = [*_HARX_COMMON, "log_atm_iv_0dte_d"]

    def __init__(self, alpha: float = 1.0) -> None:
        super().__init__(model=_make_ridge_pipe(alpha))
        self.alpha = alpha

    def fit(self, X: pd.DataFrame, y: pd.Series) -> RidgeHARXIvH1Model:
        self._fit(X, y)
        return self


@register_model("lasso_harx_iv_h1")
class LassoHARXIvH1Model(_BaseHAR):
    """Lasso HAR-X with 0DTE IV (h=1)."""

    REQUIRED_LAYERS = ["har_core", "options", "asymmetry", "cross_asset"]
    _FEATURES = [*_HARX_COMMON, "log_atm_iv_0dte_d"]

    def __init__(self, alpha: float = 0.01, l1_ratio: float = 0.95) -> None:
        super().__init__(model=_make_lasso_pipe(alpha, l1_ratio))
        self.alpha = alpha
        self.l1_ratio = l1_ratio

    def fit(self, X: pd.DataFrame, y: pd.Series) -> LassoHARXIvH1Model:
        self._fit(X, y)
        return self


@register_model("elasticnet_harx_iv_h1")
class ElasticNetHARXIvH1Model(_BaseHAR):
    """Elastic Net HAR-X with 0DTE IV (h=1)."""

    REQUIRED_LAYERS = ["har_core", "options", "asymmetry", "cross_asset"]
    _FEATURES = [*_HARX_COMMON, "log_atm_iv_0dte_d"]

    def __init__(self, alpha: float = 0.01, l1_ratio: float = 0.5) -> None:
        super().__init__(model=_make_enet_pipe(alpha, l1_ratio))
        self.alpha = alpha
        self.l1_ratio = l1_ratio

    def fit(self, X: pd.DataFrame, y: pd.Series) -> ElasticNetHARXIvH1Model:
        self._fit(X, y)
        return self


# --- h=5: 1-week IV ---


@register_model("harx_iv_h5")
class HARXIvH5Model(_BaseHAR):
    """HAR-X with 1-week IV + VIX + VIX innovation + return + VRP (h=5 optimized)."""

    REQUIRED_LAYERS = ["har_core", "options", "asymmetry", "cross_asset"]
    _FEATURES = [*_HARX_COMMON, "log_atm_iv_1w_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARXIvH5Model:
        self._fit(X, y)
        return self


@register_model("ridge_harx_iv_h5")
class RidgeHARXIvH5Model(_BaseHAR):
    """Ridge HAR-X with 1-week IV (h=5)."""

    REQUIRED_LAYERS = ["har_core", "options", "asymmetry", "cross_asset"]
    _FEATURES = [*_HARX_COMMON, "log_atm_iv_1w_d"]

    def __init__(self, alpha: float = 1.0) -> None:
        super().__init__(model=_make_ridge_pipe(alpha))
        self.alpha = alpha

    def fit(self, X: pd.DataFrame, y: pd.Series) -> RidgeHARXIvH5Model:
        self._fit(X, y)
        return self


@register_model("lasso_harx_iv_h5")
class LassoHARXIvH5Model(_BaseHAR):
    """Lasso HAR-X with 1-week IV (h=5)."""

    REQUIRED_LAYERS = ["har_core", "options", "asymmetry", "cross_asset"]
    _FEATURES = [*_HARX_COMMON, "log_atm_iv_1w_d"]

    def __init__(self, alpha: float = 0.01, l1_ratio: float = 0.95) -> None:
        super().__init__(model=_make_lasso_pipe(alpha, l1_ratio))
        self.alpha = alpha
        self.l1_ratio = l1_ratio

    def fit(self, X: pd.DataFrame, y: pd.Series) -> LassoHARXIvH5Model:
        self._fit(X, y)
        return self


@register_model("elasticnet_harx_iv_h5")
class ElasticNetHARXIvH5Model(_BaseHAR):
    """Elastic Net HAR-X with 1-week IV (h=5)."""

    REQUIRED_LAYERS = ["har_core", "options", "asymmetry", "cross_asset"]
    _FEATURES = [*_HARX_COMMON, "log_atm_iv_1w_d"]

    def __init__(self, alpha: float = 0.01, l1_ratio: float = 0.5) -> None:
        super().__init__(model=_make_enet_pipe(alpha, l1_ratio))
        self.alpha = alpha
        self.l1_ratio = l1_ratio

    def fit(self, X: pd.DataFrame, y: pd.Series) -> ElasticNetHARXIvH5Model:
        self._fit(X, y)
        return self


# --- h=22: 1-month IV ---


@register_model("harx_iv_h22")
class HARXIvH22Model(_BaseHAR):
    """HAR-X with 1-month IV + VIX + VIX innovation + return + VRP (h=22 optimized)."""

    REQUIRED_LAYERS = ["har_core", "options", "asymmetry", "cross_asset"]
    _FEATURES = [*_HARX_COMMON, "log_atm_iv_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARXIvH22Model:
        self._fit(X, y)
        return self


@register_model("ridge_harx_iv_h22")
class RidgeHARXIvH22Model(_BaseHAR):
    """Ridge HAR-X with 1-month IV (h=22)."""

    REQUIRED_LAYERS = ["har_core", "options", "asymmetry", "cross_asset"]
    _FEATURES = [*_HARX_COMMON, "log_atm_iv_d"]

    def __init__(self, alpha: float = 1.0) -> None:
        super().__init__(model=_make_ridge_pipe(alpha))
        self.alpha = alpha

    def fit(self, X: pd.DataFrame, y: pd.Series) -> RidgeHARXIvH22Model:
        self._fit(X, y)
        return self


@register_model("lasso_harx_iv_h22")
class LassoHARXIvH22Model(_BaseHAR):
    """Lasso HAR-X with 1-month IV (h=22)."""

    REQUIRED_LAYERS = ["har_core", "options", "asymmetry", "cross_asset"]
    _FEATURES = [*_HARX_COMMON, "log_atm_iv_d"]

    def __init__(self, alpha: float = 0.01, l1_ratio: float = 0.95) -> None:
        super().__init__(model=_make_lasso_pipe(alpha, l1_ratio))
        self.alpha = alpha
        self.l1_ratio = l1_ratio

    def fit(self, X: pd.DataFrame, y: pd.Series) -> LassoHARXIvH22Model:
        self._fit(X, y)
        return self


@register_model("elasticnet_harx_iv_h22")
class ElasticNetHARXIvH22Model(_BaseHAR):
    """Elastic Net HAR-X with 1-month IV (h=22)."""

    REQUIRED_LAYERS = ["har_core", "options", "asymmetry", "cross_asset"]
    _FEATURES = [*_HARX_COMMON, "log_atm_iv_d"]

    def __init__(self, alpha: float = 0.01, l1_ratio: float = 0.5) -> None:
        super().__init__(model=_make_enet_pipe(alpha, l1_ratio))
        self.alpha = alpha
        self.l1_ratio = l1_ratio

    def fit(self, X: pd.DataFrame, y: pd.Series) -> ElasticNetHARXIvH22Model:
        self._fit(X, y)
        return self


# ---------------------------------------------------------------------------
# HAR-IV-RateVol models: HAR + ATM IV + swaption rate_vol (trial-044)
# ---------------------------------------------------------------------------


@register_model("har_iv_ratevol")
class HARIVRateVolModel(_BaseHAR):
    """HAR-IV-RateVol: HAR + ATM IV + cross-asset swaption rate_vol (5 params).

    log(RV_{t+h}) = β₀ + β_d·log(RV_t) + β_w·log(RV_t^w) + β_m·log(RV_t^m)
                        + β_iv·log(atm_iv_t) + β_rv·log(rate_vol_t)

    Motivation: Lead-lag analysis (2026-06-08) showed rate_vol_1y10y carries
    massive forward-looking signal: +232 bps (h=5), +261 bps (h=22) above HAR-IV.
    Swaption IV captures term premium repricing in rates that LEADS equity vol.
    Adding this to the linear base model avoids LightGBM feature dilution.

    Requires options layer (log_atm_iv_d) and cross_asset_momentum layer (xasset_rate_vol).
    """

    REQUIRED_LAYERS = ["har_core", "options", "cross_asset_momentum"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_d", "xasset_rate_vol"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIVRateVolModel:
        self._fit(X, y)
        return self


@register_model("har_iv_1w_ratevol")
class HARIV1wRateVolModel(_BaseHAR):
    """HAR-IV-1w-RateVol: 1-week IV tenor + rate_vol (5 params, for h=1/h=5)."""

    REQUIRED_LAYERS = ["har_core", "options", "cross_asset_momentum"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_1w_d", "xasset_rate_vol"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIV1wRateVolModel:
        self._fit(X, y)
        return self


@register_model("ridge_har_iv_ratevol")
class RidgeHARIVRateVolModel(_BaseHAR):
    """Ridge-regularized HAR-IV-RateVol (5 params, L2 penalty)."""

    REQUIRED_LAYERS = ["har_core", "options", "cross_asset_momentum"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_d", "xasset_rate_vol"]

    def __init__(self, alpha: float = 1.0) -> None:
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import Pipeline as SKPipeline
        from sklearn.preprocessing import StandardScaler

        pipe = SKPipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
        super().__init__(model=pipe)
        self.alpha = alpha

    def fit(self, X: pd.DataFrame, y: pd.Series) -> RidgeHARIVRateVolModel:
        self._fit(X, y)
        return self


@register_model("lasso_har_iv_ratevol")
class LassoHARIVRateVolModel(_BaseHAR):
    """Lasso-regularized HAR-IV-RateVol (5 params, L1 penalty).

    Sparsity test: if rate_vol is redundant with IV, Lasso will zero it out.
    If both survive, the signal is orthogonal.
    """

    REQUIRED_LAYERS = ["har_core", "options", "cross_asset_momentum"]
    _FEATURES = ["log_rv_d", "log_rv_w", "log_rv_m", "log_atm_iv_d", "xasset_rate_vol"]

    def __init__(self, alpha: float = 0.01, l1_ratio: float = 0.95) -> None:
        from sklearn.linear_model import ElasticNet
        from sklearn.pipeline import Pipeline as SKPipeline
        from sklearn.preprocessing import StandardScaler

        pipe = SKPipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "lasso",
                    ElasticNet(
                        alpha=alpha,
                        l1_ratio=l1_ratio,
                        max_iter=2000,
                        tol=1e-3,
                        selection="random",
                    ),
                ),
            ]
        )
        super().__init__(model=pipe)
        self.alpha = alpha
        self.l1_ratio = l1_ratio

    def fit(self, X: pd.DataFrame, y: pd.Series) -> LassoHARIVRateVolModel:
        self._fit(X, y)
        return self


# ---------------------------------------------------------------------------
# Hybrid HAR variants: orthogonal RV-side enrichments + IV
# ---------------------------------------------------------------------------


@register_model("shar_iv")
class SHARIVModel(_BaseHAR):
    """SHAR-IV: Semivariance HAR + ATM IV (5 params).

    Replaces log_rv_d with RS⁺/RS⁻ decomposition (Patton & Sheppard 2015)
    while adding ATM IV. Captures leverage effect (downside vol predicts
    future vol more than upside vol) orthogonally to IV's forward view.
    """

    REQUIRED_LAYERS = ["har_core", "asymmetry", "options"]
    _FEATURES = [
        "log_rs_positive_d",
        "log_rs_negative_d",
        "log_rv_w",
        "log_rv_m",
        "log_atm_iv_d",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> SHARIVModel:
        self._fit(X, y)
        return self


@register_model("shar_iv_1w")
class SHARIV1wModel(_BaseHAR):
    """SHAR-IV-1w: Semivariance HAR + 1w ATM IV (5 params).

    Tenor-matched IV for h=1/h=5 forecasting combined with asymmetric RV.
    """

    REQUIRED_LAYERS = ["har_core", "asymmetry", "options"]
    _FEATURES = [
        "log_rs_positive_d",
        "log_rs_negative_d",
        "log_rv_w",
        "log_rv_m",
        "log_atm_iv_1w_d",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> SHARIV1wModel:
        self._fit(X, y)
        return self


@register_model("shar_iv_0dte")
class SHARIV0dteModel(_BaseHAR):
    """SHAR-IV-0DTE: Semivariance HAR + 0DTE ATM IV (5 params).

    Exact tenor match for h=1: asymmetric RV captures whether yesterday's
    vol was driven by downside moves (leverage effect), while 0DTE IV
    captures the market's exact next-day expectation.
    """

    REQUIRED_LAYERS = ["har_core", "asymmetry", "options"]
    _FEATURES = [
        "log_rs_positive_d",
        "log_rs_negative_d",
        "log_rv_w",
        "log_rv_m",
        "log_atm_iv_0dte_d",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> SHARIV0dteModel:
        self._fit(X, y)
        return self


@register_model("harq_iv")
class HARQIVModel(_BaseHAR):
    """HARQ-IV: HARQ + ATM IV (5 params).

    Adds RQ interaction to HAR-IV. When RQ is high (noisy RV day),
    the model conditionally downweights log_rv_d and implicitly
    upweights IV. Measurement quality is orthogonal to both RV and IV.
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = [
        "log_rv_d",
        "log_rv_w",
        "log_rv_m",
        "rq_rv_interaction_d",
        "log_atm_iv_d",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARQIVModel:
        self._fit(X, y)
        return self


@register_model("harq_iv_1w")
class HARQIV1wModel(_BaseHAR):
    """HARQ-IV-1w: HARQ + 1w ATM IV (5 params).

    Tenor-matched IV for short horizons + measurement quality conditioning.
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = [
        "log_rv_d",
        "log_rv_w",
        "log_rv_m",
        "rq_rv_interaction_d",
        "log_atm_iv_1w_d",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARQIV1wModel:
        self._fit(X, y)
        return self


@register_model("har_iv_2tenor")
class HARIV2TenorModel(_BaseHAR):
    """HAR-IV-2Tenor: HAR + both 1w and 1m ATM IV (5 params).

    Uses two IV tenors simultaneously. 1w IV captures near-term event
    pricing; 1m IV captures regime-level vol expectation. OLS finds
    the optimal blend per horizon, potentially dominating single-tenor
    models at all horizons.
    """

    REQUIRED_LAYERS = ["har_core", "options"]
    _FEATURES = [
        "log_rv_d",
        "log_rv_w",
        "log_rv_m",
        "log_atm_iv_1w_d",
        "log_atm_iv_d",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIV2TenorModel:
        self._fit(X, y)
        return self


@register_model("har_iv_noise")
class HARIVNoiseModel(_BaseHAR):
    """HAR-IV-Noise: HAR-IV + noise gap (5 params).

    Adds noise_gap_d (RV - RK) as a direct feature. When noise_gap is
    large, RV is contaminated by microstructure noise and the model
    should rely more on IV. Novel feature not in standard literature.
    """

    REQUIRED_LAYERS = ["har_core", "options", "noise_robust"]
    _FEATURES = [
        "log_rv_d",
        "log_rv_w",
        "log_rv_m",
        "log_atm_iv_d",
        "noise_gap_d",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARIVNoiseModel:
        self._fit(X, y)
        return self


@register_model("har_cj_iv_0dte")
class HARCJIVOdteModel(_BaseHAR):
    """HAR-CJ-IV-0DTE: HAR-CJ + 0DTE ATM IV (5 params).

    Combines continuous/jump decomposition with exact tenor-matched IV.
    Continuous variation captures diffusive vol dynamics; jump captures
    tail events; 0DTE IV prices next-day risk including expected jumps.
    The three signals are structurally orthogonal.
    """

    REQUIRED_LAYERS = ["har_core", "asymmetry", "options"]
    _FEATURES = [
        "log_cont_d",
        "log_cont_w",
        "log_rv_m",
        "log_jump_d",
        "log_atm_iv_0dte_d",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARCJIVOdteModel:
        self._fit(X, y)
        return self


@register_model("shar_cj_iv_0dte")
class SHARCJIVOdteModel(_BaseHAR):
    """SHAR-CJ-IV-0DTE: combined directional + type decomposition + IV (6 params).

    Daily decomposed by direction (RS⁺/RS⁻ — leverage effect).
    Weekly decomposed by type (continuous — strips jump noise).
    Monthly as total RV (robust aggregate).
    Jump as separate predictor (tail events).
    0DTE IV for forward-looking expectation.

    Each decomposition operates at a different time scale to minimize
    collinearity: direction at daily, type at weekly.
    """

    REQUIRED_LAYERS = ["har_core", "asymmetry", "options"]
    _FEATURES = [
        "log_rs_positive_d",
        "log_rs_negative_d",
        "log_cont_w",
        "log_rv_m",
        "log_jump_d",
        "log_atm_iv_0dte_d",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> SHARCJIVOdteModel:
        self._fit(X, y)
        return self


@register_model("sharq_cj_iv_0dte")
class SHARQCJIVOdteModel(_BaseHAR):
    """SHARQ-CJ-IV-0DTE: full kitchen sink — direction + type + quality + IV (7 params).

    All three orthogonal RV decompositions combined:
    - Direction: RS⁺/RS⁻ (leverage effect, Patton & Sheppard 2015)
    - Type: continuous/jump (BNS 2006)
    - Quality: RQ×RV interaction (Bollerslev et al. 2016)
    Plus 0DTE IV for the market's exact next-day expectation.

    7 parameters is aggressive for OLS but safe with 10k+ pooled obs.
    If any dimension is redundant given IV, OLS will zero its coefficient.
    """

    REQUIRED_LAYERS = ["har_core", "asymmetry", "options"]
    _FEATURES = [
        "log_rs_positive_d",
        "log_rs_negative_d",
        "log_cont_w",
        "log_rv_m",
        "log_jump_d",
        "rq_rv_interaction_d",
        "log_atm_iv_0dte_d",
    ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> SHARQCJIVOdteModel:
        self._fit(X, y)
        return self


# ---------------------------------------------------------------------------
# Frequency-matched IV + RV decomposition combos
# ---------------------------------------------------------------------------

_FREQ_IV = ["log_atm_iv_d", "log_atm_iv_w", "log_atm_iv_m"]


@register_model("shar_iv_freq")
class SHARIVFreqModel(_BaseHAR):
    """SHAR-IV-Freq: semivariance + frequency-matched IV (7 params).

    Daily RV decomposed by direction (leverage effect) + Busch et al. (2011)
    frequency structure on IV side.
    """

    REQUIRED_LAYERS = ["har_core", "asymmetry", "options"]
    _FEATURES = ["log_rs_positive_d", "log_rs_negative_d", "log_rv_w", "log_rv_m"] + _FREQ_IV

    def fit(self, X: pd.DataFrame, y: pd.Series) -> SHARIVFreqModel:
        self._fit(X, y)
        return self


@register_model("har_cj_iv_freq")
class HARCJIVFreqModel(_BaseHAR):
    """HAR-CJ-IV-Freq: continuous/jump + frequency-matched IV (7 params).

    RV decomposed by type (diffusive vs jump) + IV at 3 frequencies.
    """

    REQUIRED_LAYERS = ["har_core", "asymmetry", "options"]
    _FEATURES = ["log_cont_d", "log_cont_w", "log_rv_m", "log_jump_d"] + _FREQ_IV

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARCJIVFreqModel:
        self._fit(X, y)
        return self


@register_model("har_cj_iv_freq_vrp")
class HARCJIVFreqVrpModel(_BaseHAR):
    """HAR-CJ-IV-Freq-VRP: continuous/jump + frequency IV + VRP (8 params).

    Adds VRP as orthogonal predictor (risk premium mean-reversion signal)
    to the CJ + freq IV combination.
    """

    REQUIRED_LAYERS = ["har_core", "asymmetry", "options"]
    _FEATURES = ["log_cont_d", "log_cont_w", "log_rv_m", "log_jump_d"] + _FREQ_IV + ["vrp_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HARCJIVFreqVrpModel:
        self._fit(X, y)
        return self


@register_model("shar_cj_iv_freq")
class SHARCJIVFreqModel(_BaseHAR):
    """SHAR-CJ-IV-Freq: direction + type decomp + frequency IV (8 params).

    Daily by direction (RS⁺/RS⁻), weekly by type (continuous), monthly total,
    jump separate, IV at 3 frequencies. Maximum RV+IV decomposition without
    quality or VRP.
    """

    REQUIRED_LAYERS = ["har_core", "asymmetry", "options"]
    _FEATURES = [
        "log_rs_positive_d", "log_rs_negative_d", "log_cont_w", "log_rv_m", "log_jump_d",
    ] + _FREQ_IV

    def fit(self, X: pd.DataFrame, y: pd.Series) -> SHARCJIVFreqModel:
        self._fit(X, y)
        return self


@register_model("shar_cj_iv_freq_vrp")
class SHARCJIVFreqVrpModel(_BaseHAR):
    """SHAR-CJ-IV-Freq-VRP: direction + type + frequency IV + VRP (9 params).

    Adds VRP to the SHAR-CJ + freq IV combination.
    """

    REQUIRED_LAYERS = ["har_core", "asymmetry", "options"]
    _FEATURES = [
        "log_rs_positive_d", "log_rs_negative_d", "log_cont_w", "log_rv_m", "log_jump_d",
    ] + _FREQ_IV + ["vrp_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> SHARCJIVFreqVrpModel:
        self._fit(X, y)
        return self


@register_model("sharq_cj_iv_freq")
class SHARQCJIVFreqModel(_BaseHAR):
    """SHARQ-CJ-IV-Freq: direction + type + quality + frequency IV (9 params).

    All three RV decompositions (direction, type, quality) + IV at 3 frequencies.
    Lasso will reveal which dimensions survive under penalty.
    """

    REQUIRED_LAYERS = ["har_core", "asymmetry", "options"]
    _FEATURES = [
        "log_rs_positive_d", "log_rs_negative_d", "log_cont_w", "log_rv_m", "log_jump_d",
        "rq_rv_interaction_d",
    ] + _FREQ_IV

    def fit(self, X: pd.DataFrame, y: pd.Series) -> SHARQCJIVFreqModel:
        self._fit(X, y)
        return self


@register_model("sharq_cj_iv_freq_vrp")
class SHARQCJIVFreqVrpModel(_BaseHAR):
    """SHARQ-CJ-IV-Freq-VRP: full kitchen sink (10 params).

    Every orthogonal RV decomposition + frequency-matched IV + VRP.
    The maximal linear model. Lasso/ElasticNet variants are the key
    test — which features survive L1 penalty with 10k+ pooled obs.
    """

    REQUIRED_LAYERS = ["har_core", "asymmetry", "options"]
    _FEATURES = [
        "log_rs_positive_d", "log_rs_negative_d", "log_cont_w", "log_rv_m", "log_jump_d",
        "rq_rv_interaction_d",
    ] + _FREQ_IV + ["vrp_d"]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> SHARQCJIVFreqVrpModel:
        self._fit(X, y)
        return self


# ---------------------------------------------------------------------------
# Factory: Ridge / Lasso / ElasticNet variants for all new hybrid models
# ---------------------------------------------------------------------------

def _register_regularized_variants(
    base_name: str,
    features: list[str],
    required_layers: list[str],
) -> None:
    """Generate and register ridge/lasso/elasticnet variants of an OLS model."""

    for prefix, pipe_fn in [
        ("ridge", _make_ridge_pipe),
        ("lasso", _make_lasso_pipe),
        ("elasticnet", _make_enet_pipe),
    ]:
        reg_name = f"{prefix}_{base_name}"

        def _make_init(pfn):
            def __init__(self):
                _BaseHAR.__init__(self, model=pfn())
            return __init__

        def _make_fit(pfn):
            def fit(self, X, y):
                self._fit(X, y)
                return self
            return fit

        cls = type(
            reg_name,
            (_BaseHAR,),
            {
                "REQUIRED_LAYERS": required_layers,
                "_FEATURES": list(features),
                "__init__": _make_init(pipe_fn),
                "fit": _make_fit(pipe_fn),
            },
        )
        register_model(reg_name)(cls)


# Specs: (base_name, features, required_layers)
_NEW_HYBRID_SPECS = [
    ("shar_iv", SHARIVModel._FEATURES, SHARIVModel.REQUIRED_LAYERS),
    ("shar_iv_1w", SHARIV1wModel._FEATURES, SHARIV1wModel.REQUIRED_LAYERS),
    ("shar_iv_0dte", SHARIV0dteModel._FEATURES, SHARIV0dteModel.REQUIRED_LAYERS),
    ("harq_iv", HARQIVModel._FEATURES, HARQIVModel.REQUIRED_LAYERS),
    ("harq_iv_1w", HARQIV1wModel._FEATURES, HARQIV1wModel.REQUIRED_LAYERS),
    ("har_iv_2tenor", HARIV2TenorModel._FEATURES, HARIV2TenorModel.REQUIRED_LAYERS),
    ("har_iv_noise", HARIVNoiseModel._FEATURES, HARIVNoiseModel.REQUIRED_LAYERS),
    ("har_cj_iv_0dte", HARCJIVOdteModel._FEATURES, HARCJIVOdteModel.REQUIRED_LAYERS),
    ("shar_cj_iv_0dte", SHARCJIVOdteModel._FEATURES, SHARCJIVOdteModel.REQUIRED_LAYERS),
    ("sharq_cj_iv_0dte", SHARQCJIVOdteModel._FEATURES, SHARQCJIVOdteModel.REQUIRED_LAYERS),
    # Literature models (already registered as OLS, now get regularized variants)
    ("har_iv_freq", HARIVFreqModel._FEATURES, HARIVFreqModel.REQUIRED_LAYERS),
    ("har_iv_freq_vrp", HARIVFreqVrpModel._FEATURES, HARIVFreqVrpModel.REQUIRED_LAYERS),
    ("har_iv_optimal", HARIVOptimalModel._FEATURES, HARIVOptimalModel.REQUIRED_LAYERS),
    # Frequency-matched IV + RV decomposition combos
    ("shar_iv_freq", SHARIVFreqModel._FEATURES, SHARIVFreqModel.REQUIRED_LAYERS),
    ("har_cj_iv_freq", HARCJIVFreqModel._FEATURES, HARCJIVFreqModel.REQUIRED_LAYERS),
    ("har_cj_iv_freq_vrp", HARCJIVFreqVrpModel._FEATURES, HARCJIVFreqVrpModel.REQUIRED_LAYERS),
    ("shar_cj_iv_freq", SHARCJIVFreqModel._FEATURES, SHARCJIVFreqModel.REQUIRED_LAYERS),
    ("shar_cj_iv_freq_vrp", SHARCJIVFreqVrpModel._FEATURES, SHARCJIVFreqVrpModel.REQUIRED_LAYERS),
    ("sharq_cj_iv_freq", SHARQCJIVFreqModel._FEATURES, SHARQCJIVFreqModel.REQUIRED_LAYERS),
    ("sharq_cj_iv_freq_vrp", SHARQCJIVFreqVrpModel._FEATURES, SHARQCJIVFreqVrpModel.REQUIRED_LAYERS),
]

for _base, _feats, _layers in _NEW_HYBRID_SPECS:
    _register_regularized_variants(_base, _feats, _layers)
