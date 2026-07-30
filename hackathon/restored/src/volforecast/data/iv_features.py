"""Transform raw IV surface cache into model-ready feature columns.

Takes the output of iv_ingest.ingest_iv_surface() and computes Layer 2
features with proper shift(1) causality and rolling window derivations.

Public API:
    build_iv_feature_panel — Transform raw IV → feature panel
    save_iv_features       — Persist feature panel to parquet
    load_iv_features       — Load cached feature panel (or None)
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from volforecast.data.edrvol import load_iv_cache
from volforecast.utils.paths import processed_dir
from volforecast.utils.targets import forward_log_rv

logger = logging.getLogger(__name__)

_FEATURES_CACHE_FILENAME = "iv_features_spx.parquet"


def _har_expected_rv(rv_panel: pd.DataFrame, h: int = 22) -> pd.Series:
    """Compute E_t[RV_{t+1:t+h}] using the existing HAR-CJ model (h=22).

    Reuses the registered HAR-CJ model from `models/har_family.py` to
    generate h-day-ahead forecasts. HAR-CJ is the best-performing model
    for h=22 in tournament evaluations.

    Trains on the full available sample (standard in VRP literature where
    the HAR coefficients are estimated once). Uses har_core + asymmetry
    feature layers — same as the tournament pipeline.

    Parameters
    ----------
    rv_panel : pd.DataFrame
        Daily RV panel with at minimum 'rv' column. Must also contain
        columns needed by har_core and asymmetry layers (bpv, jump_variation,
        continuous_variation, etc.).
    h : int
        Forecast horizon in trading days (default 22 = ~1 month).

    Returns
    -------
    pd.Series
        Expected annualized variance at each time step. NaN where
        features or target are unavailable.
    """
    from volforecast.models.har_family import HARCJModel
    from volforecast.registry import FEATURE_REGISTRY, ensure_registered

    ensure_registered()

    # Build features using existing layers (same code path as tournament)
    har_layer = FEATURE_REGISTRY["har_core"]()
    asym_layer = FEATURE_REGISTRY["asymmetry"]()
    X_har = har_layer.compute(rv_panel)
    X_asym = asym_layer.compute(rv_panel)
    X_all = pd.concat([X_har, X_asym], axis=1)

    # Build target: log(average RV over next h days) — Corsi (2009) spec
    # Must match tournament runner: log of arithmetic mean, NOT mean of logs.
    target = forward_log_rv(rv_panel["rv"], h)

    # Align features and target, drop NaN
    aligned = pd.concat([X_all, target.rename("target")], axis=1)
    aligned = aligned.replace([np.inf, -np.inf], np.nan).dropna()
    X = aligned.drop(columns=["target"])
    y = aligned["target"]

    if len(X) < 100:
        # Not enough data for HAR-CJ — fall back to simple rolling mean.
        # This is a naive E_t[RV] proxy (arithmetic mean of past 22 days,
        # annualized). The full Bollerslev et al. (2009) conditional VRP
        # requires HAR-CJ fitting which needs >= 100 observations.
        return rv_panel["rv"].rolling(22).mean() * 252.0

    # Fit HAR-CJ on full sample and predict
    model = HARCJModel()
    model.fit(X, y)

    # Generate forecast for all dates where features are available
    X_full = pd.concat([X_har, X_asym], axis=1).replace([np.inf, -np.inf], np.nan)
    # Only predict where HAR-CJ's required features are non-NaN
    har_cj_cols = HARCJModel._FEATURES
    X_pred = X_full[har_cj_cols].dropna()

    log_forecast = pd.Series(
        model.predict(X_pred),
        index=X_pred.index,
        dtype=float,
    )

    # Convert from log-space forecast to annualized variance
    expected_rv_annualized = np.exp(log_forecast) * 252.0

    return expected_rv_annualized.reindex(rv_panel.index)


def build_iv_feature_panel(
    iv_raw: pd.DataFrame,
    rv_panel: pd.DataFrame,
) -> pd.DataFrame:
    """Transform raw IV panel into model-ready features.

    All features are shifted by 1 day to enforce causality: the feature
    value at time t uses only information available at market close t-1.

    Parameters
    ----------
    iv_raw : pd.DataFrame
        Output of ingest_iv_surface(). Must contain columns:
        atm_iv_1m, atm_iv_3m, iv_put_25d_1m, iv_call_25d_1m, skew_1m, vix.
    rv_panel : pd.DataFrame
        Daily RV panel. Must contain column 'rv' (daily realized variance).
        Index must be DatetimeIndex aligned with iv_raw.

    Returns
    -------
    pd.DataFrame
        Feature panel indexed by rv_panel.index with columns:
        atm_iv_1m, atm_iv_3m, skew_1m, iv_put_25d, iv_call_25d,
        vrp, term_slope, butterfly_1m, iv_rv_gap,
        vix, vix_innovation, vol_of_vix, vts, forward_vol_1m3m.
        All shifted(1) for causality.
    """
    # Align IV to RV panel index
    iv = iv_raw.reindex(rv_panel.index)

    # --- Derived features (before shift) ---

    # VRP = IV^2 - E_t[RV_{t+1:t+22}]
    # Use HAR-CJ h=22 forecast as the conditional expectation (Bollerslev et al. 2009).
    # HAR-CJ is the best tournament model at h=22. Uses existing model infra
    # so any improvements to HAR-CJ flow automatically to VRP.
    har_forecast_22 = _har_expected_rv(rv_panel, h=22)
    vrp = iv["atm_iv_1m"] ** 2 - har_forecast_22

    # Term slope = ATM_3m - ATM_1m
    term_slope = iv["atm_iv_3m"] - iv["atm_iv_1m"]

    # Butterfly = 0.5*(put_25d + call_25d) - ATM
    butterfly = 0.5 * (iv["iv_put_25d_1m"] + iv["iv_call_25d_1m"]) - iv["atm_iv_1m"]

    # IV-RV gap = ATM_IV - sqrt(E_t[annualized RV])
    # Uses same HAR forecast for consistency with VRP
    iv_rv_gap = iv["atm_iv_1m"] - np.sqrt(har_forecast_22)

    # VIX series (used for innovation and fallback proxy)
    vix = iv["vix"]

    # Vol-of-VIX: use real VVIX index from cache if available, else proxy
    vvix_cache = load_iv_cache("_VVIX")
    if vvix_cache is not None and not vvix_cache.empty:
        vvix_series = vvix_cache.iloc[:, 0] if isinstance(vvix_cache, pd.DataFrame) else vvix_cache
        vvix_series.index = pd.DatetimeIndex(vvix_series.index)
        # VVIX is in index points (e.g. 80); convert to decimal vol for consistency
        vol_of_vix = (vvix_series / 100.0).reindex(rv_panel.index)
        logger.debug("Using real VVIX (%d non-NaN values)", vol_of_vix.notna().sum())
    else:
        # Fallback: realized vol-of-VIX proxy
        vix_log_ret = np.log(vix / vix.shift(1))
        vol_of_vix = np.sqrt(252.0 * (vix_log_ret**2).rolling(22).mean())
        logger.debug("VVIX cache unavailable, using realized proxy")

    # VIX innovation = VIX_t - VIX_{t-1}
    vix_innovation = vix - vix.shift(1)

    # VTS = ATM_3m / ATM_1m (VIX term structure proxy, Bennett 2014)
    # VTS > 1 = contango (calm), VTS < 1 = backwardation (crisis)
    vts = iv["atm_iv_3m"] / iv["atm_iv_1m"]

    # Forward implied vol (1m→3m) via additive variance rule
    # σ_{1m→3m} = sqrt(max(σ_3m² * T_3m - σ_1m² * T_1m, 0) / (T_3m - T_1m))
    t_1m = 1.0 / 12.0
    t_3m = 3.0 / 12.0
    total_var_diff = iv["atm_iv_3m"] ** 2 * t_3m - iv["atm_iv_1m"] ** 2 * t_1m
    forward_vol_1m3m = np.sqrt(np.maximum(total_var_diff, 0.0) / (t_3m - t_1m))

    # --- Assemble and apply shift(1) ---
    features = pd.DataFrame(
        {
            "atm_iv_1m": iv["atm_iv_1m"],
            "atm_iv_3m": iv["atm_iv_3m"],
            "skew_1m": iv["skew_1m"],
            "iv_put_25d": iv["iv_put_25d_1m"],
            "iv_call_25d": iv["iv_call_25d_1m"],
            "vrp": vrp,
            "term_slope": term_slope,
            "butterfly_1m": butterfly,
            "iv_rv_gap": iv_rv_gap,
            "vix": vix,
            "vix_innovation": vix_innovation,
            "vol_of_vix": vol_of_vix,
            "vts": vts,
            "forward_vol_1m3m": forward_vol_1m3m,
        },
        index=rv_panel.index,
    )

    # Shift all features by 1 day for causality
    features = features.shift(1)

    return features


def save_iv_features(features: pd.DataFrame, path: Path | None = None) -> Path:
    """Save feature panel to parquet.

    Parameters
    ----------
    features : pd.DataFrame
        Output of build_iv_feature_panel().
    path : Path, optional
        Target path. Defaults to data/processed/iv_features_spx.parquet.

    Returns
    -------
    Path
        Path where the file was saved.
    """
    if path is None:
        out_dir = processed_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / _FEATURES_CACHE_FILENAME

    path.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(path)
    logger.info(
        "IV features saved: %s (%d rows, %d cols)", path, len(features), len(features.columns)
    )
    return path


def load_iv_features(path: Path | None = None) -> pd.DataFrame | None:
    """Load cached IV feature panel from parquet.

    Parameters
    ----------
    path : Path, optional
        Source path. Defaults to data/processed/iv_features_spx.parquet.

    Returns
    -------
    pd.DataFrame or None
        The cached feature panel, or None if file doesn't exist.
    """
    if path is None:
        path = processed_dir() / _FEATURES_CACHE_FILENAME

    if not path.exists():
        return None

    panel = pd.read_parquet(path)
    logger.info("IV features loaded: %s (%d rows)", path, len(panel))
    return panel
