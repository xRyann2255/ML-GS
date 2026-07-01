"""Naive baseline models (zero-parameter or single-parameter).

These implement the fit/predict interface but require no training or minimal
training (just computing a mean). They provide a floor for QLIKE comparison:
any useful model must beat these.

All predictions are in log-RV space (same convention as HAR family).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from volforecast.models._base import _BaseModel
from volforecast.registry import register_model


class _BaseNaive(_BaseModel):
    """Naive model base — overrides summary to return type marker."""

    @property
    def summary(self) -> dict[str, float]:
        return {"type": "naive"}


@register_model("same_day_rv")
@register_model("random_walk")
class RandomWalkModel(_BaseNaive):
    """Random walk: predict log_rv[t+h] = log_rv[t] (most recent available).

    Uses the 'log_rv_d' feature which is log(RV_t) (today's realized vol).
    This is the fairest naive baseline — it uses only the same information
    set (data up to t) as all other models in the pipeline.
    """

    def fit(self, X: pd.DataFrame, y: pd.Series) -> RandomWalkModel:
        self._feature_names = list(X.columns)
        self.coefficients_ = np.array([])
        self.intercept_ = 0.0
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if "log_rv_d" not in X.columns:
            raise ValueError("RandomWalkModel requires 'log_rv_d' in features")
        return X["log_rv_d"].values


SameDayRVModel = RandomWalkModel


@register_model("historical_mean")
class HistoricalMeanModel(_BaseNaive):
    """Unconditional mean: predict log_rv[t+h] = mean(log_rv) from training set.

    This is the weakest reasonable baseline — it predicts a constant regardless
    of recent market conditions. Any model that can't beat this is useless.
    """

    def __init__(self) -> None:
        super().__init__()
        self._mean: float = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HistoricalMeanModel:
        self._feature_names = list(X.columns)
        self._mean = float(y.dropna().mean())
        self.intercept_ = self._mean
        self.coefficients_ = np.array([])
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.full(len(X), self._mean)

    @property
    def summary(self) -> dict[str, float]:
        return {"type": "naive", "mean": self._mean}


@register_model("rolling_mean")
class RollingMeanModel(_BaseNaive):
    """22-day rolling mean: predict log_rv[t+h] = log(mean(RV over past 22d)).

    Uses the 'log_rv_m' feature which is log(22-day rolling mean of RV).
    """

    def fit(self, X: pd.DataFrame, y: pd.Series) -> RollingMeanModel:
        self._feature_names = list(X.columns)
        self.coefficients_ = np.array([])
        self.intercept_ = 0.0
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if "log_rv_m" not in X.columns:
            raise ValueError("RollingMeanModel requires 'log_rv_m' in features")
        return X["log_rv_m"].values


@register_model("median_rv")
class MedianRVModel(_BaseNaive):
    """Expanding median: predict log_rv[t+h] = median(log_rv) from training set.

    Like historical_mean but uses median — more robust to jumps/COVID.
    QLIKE penalizes overprediction, so median (below the mean for right-skewed
    distributions) can score surprisingly well.
    """

    def __init__(self) -> None:
        super().__init__()
        self._median: float = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> MedianRVModel:
        self._feature_names = list(X.columns)
        self._median = float(y.dropna().median())
        self.intercept_ = self._median
        self.coefficients_ = np.array([])
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.full(len(X), self._median)

    @property
    def summary(self) -> dict[str, float]:
        return {"type": "naive", "median": self._median}


@register_model("ewma")
class EWMAModel(_BaseNaive):
    """EWMA (RiskMetrics): exponentially weighted moving average of log-RV.

    Uses lambda=0.94 (JP Morgan 1996 standard). At each test point, the
    forecast is: ewma_t = lambda * ewma_{t-1} + (1 - lambda) * log_rv_{t-1}.

    During fit, computes the EWMA series on training y and stores the last
    value as the seed for test predictions. During predict, recursively
    updates using log_rv_d (yesterday's actual log-RV from features).
    """

    def __init__(self, lam: float = 0.94) -> None:
        super().__init__()
        self._lam = lam
        self._last_ewma: float = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> EWMAModel:
        self._feature_names = list(X.columns)
        self.coefficients_ = np.array([])
        self.intercept_ = 0.0
        # Compute EWMA on training targets (log-RV)
        y_clean = y.dropna()
        # pandas EWM with alpha = 1 - lambda
        ewma_series = y_clean.ewm(alpha=1 - self._lam, adjust=False).mean()
        self._last_ewma = float(ewma_series.iloc[-1])
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if "log_rv_d" not in X.columns:
            raise ValueError("EWMAModel requires 'log_rv_d' in features")
        # Recursively compute EWMA for the test period
        log_rv_d = X["log_rv_d"].values
        preds = np.empty(len(X))
        ewma = self._last_ewma
        for i in range(len(X)):
            preds[i] = ewma
            # Update with the actual observed log-RV (available at prediction time)
            ewma = self._lam * ewma + (1 - self._lam) * log_rv_d[i]
        return preds

    @property
    def summary(self) -> dict[str, float]:
        return {"type": "naive", "lambda": self._lam, "last_ewma": self._last_ewma}


@register_model("ar1")
class AR1Model(_BaseNaive):
    """AR(1) on log-RV: log_rv[t+h] = c + phi * log_rv[t].

    Two parameters (intercept + slope). Simpler than HAR (which uses 3 lags
    at different frequencies). Tests whether HAR's weekly/monthly decomposition
    adds value over a single autoregressive lag.
    """

    def __init__(self) -> None:
        super().__init__()
        self._intercept: float = 0.0
        self._phi: float = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> AR1Model:
        if "log_rv_d" not in X.columns:
            raise ValueError("AR1Model requires 'log_rv_d' in features")
        self._feature_names = list(X.columns)
        # OLS: y = c + phi * log_rv_d
        x = X["log_rv_d"]
        mask = ~(x.isna() | y.isna())
        x_clean = x[mask].values
        y_clean = y[mask].values
        # Closed-form OLS for single regressor
        x_mean = x_clean.mean()
        y_mean = y_clean.mean()
        self._phi = float(
            np.sum((x_clean - x_mean) * (y_clean - y_mean)) / np.sum((x_clean - x_mean) ** 2)
        )
        self._intercept = float(y_mean - self._phi * x_mean)
        self.intercept_ = self._intercept
        self.coefficients_ = np.array([self._phi])
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if "log_rv_d" not in X.columns:
            raise ValueError("AR1Model requires 'log_rv_d' in features")
        return self._intercept + self._phi * X["log_rv_d"].values

    @property
    def summary(self) -> dict[str, float]:
        return {"type": "naive", "intercept": self._intercept, "phi": self._phi}


@register_model("vix_implied")
class VIXImpliedModel(_BaseNaive):
    """VIX-implied: predict RV from VIX^2/252 (option market's consensus).

    Zero parameters fitted to RV data — uses VIX directly as a vol forecast.
    Requires 'log_vix_d' in features (from cross_asset layer, shifted by 1).
    The forecast: log_rv = 2*log(VIX/100) - log(252).

    Falls back to log_rv_m if log_vix_d is unavailable (graceful degradation).
    """

    def __init__(self) -> None:
        super().__init__()
        self._has_vix: bool = False
        self._fallback_mean: float = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> VIXImpliedModel:
        self._feature_names = list(X.columns)
        self.coefficients_ = np.array([])
        self.intercept_ = 0.0
        self._has_vix = "log_vix_d" in X.columns
        if not self._has_vix:
            # Graceful fallback: use training mean (like historical_mean)
            self._fallback_mean = float(y.dropna().mean())
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self._has_vix and "log_vix_d" in X.columns:
            # log_vix_d = log(VIX_close).shift(1) from cross_asset layer
            # VIX is annualized vol in %, so daily variance = (VIX/100)^2 / 252
            # log(daily_var) = 2*log(VIX/100) - log(252) = 2*(log_vix - log(100)) - log(252)
            # But log_vix_d is just log(VIX), so:
            log_252 = np.log(252)
            log_100 = np.log(100)
            return 2 * (X["log_vix_d"].values - log_100) - log_252
        return np.full(len(X), self._fallback_mean)

    @property
    def summary(self) -> dict[str, float]:
        return {"type": "naive", "has_vix": float(self._has_vix)}


@register_model("atm_iv_implied")
class ATMIVImpliedModel(_BaseNaive):
    """Per-symbol ATM IV implied: predict RV from symbol's own 1-month ATM IV.

    Zero parameters fitted — converts per-symbol ATM IV directly to a daily
    variance forecast in log space. This is the "option market knows best"
    benchmark: if HAR/LightGBM can't beat this, the models add no value.

    Uses 'log_atm_iv_d' from the options layer (= log(iv_1m_atm) where
    iv_1m_atm is in vol points, e.g., 20.0 = 20% annualized).

    Forecast: log(daily_var) = 2*(log(IV/100)) - log(252)
            = 2*(log_atm_iv_d - log(100)) - log(252)

    Note: IV is a biased predictor of RV (variance risk premium), so this
    will systematically over-predict. QLIKE penalizes under-prediction more,
    so the bias direction may actually help this benchmark.
    """

    def __init__(self) -> None:
        super().__init__()
        self._has_iv: bool = False
        self._fallback_mean: float = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> ATMIVImpliedModel:
        self._feature_names = list(X.columns)
        self.coefficients_ = np.array([])
        self.intercept_ = 0.0
        self._has_iv = "log_atm_iv_d" in X.columns
        if not self._has_iv:
            self._fallback_mean = float(y.dropna().mean())
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self._has_iv and "log_atm_iv_d" in X.columns:
            # log_atm_iv_d = log(iv_1m_atm) where iv is in vol points
            # daily_var = (iv/100)^2 / 252
            # log(daily_var) = 2*(log(iv) - log(100)) - log(252)
            #                = 2*(log_atm_iv_d - log(100)) - log(252)
            log_252 = np.log(252)
            log_100 = np.log(100)
            return 2 * (X["log_atm_iv_d"].values - log_100) - log_252
        return np.full(len(X), self._fallback_mean)

    @property
    def summary(self) -> dict[str, float]:
        return {"type": "naive", "has_iv": float(self._has_iv)}
