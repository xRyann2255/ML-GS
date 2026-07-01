"""Cross-asset spillover features (Layer 4).

Captures volatility transmission and risk spillovers from other asset classes:
- Treasury yield curve slope (10y-2y)
- FX volatility (USD/JPY realized vol)
- Commodity volatility (CL, GC realized vol)
- VIX/RV ratio
- DY spillover index (Diebold-Yilmaz connectedness)

Key functions:
    compute_treasury_slope — Price spread (10y-2y)
    compute_rolling_vol    — Annualized rolling RV for any price series
    compute_fx_vol         — Alias for compute_rolling_vol
    compute_commodity_vol  — Alias for compute_rolling_vol
    compute_vix_rv_ratio   — VIX^2 / annualized RV ratio
    compute_dy_spillover   — Diebold-Yilmaz spillover index
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from volforecast.features.transforms import lagged_log_features, safe_log
from volforecast.registry import register_feature_layer


def compute_treasury_slope(
    long_tenor: pd.Series,
    short_tenor: pd.Series,
) -> pd.Series:
    """Compute treasury slope as price spread.

    Parameters
    ----------
    long_tenor : pd.Series
        10-year treasury price series.
    short_tenor : pd.Series
        2-year treasury price series.

    Returns
    -------
    pd.Series
        Slope = long - short. Can be negative.
    """
    return long_tenor - short_tenor


def compute_rolling_vol(
    prices: pd.Series,
    window: int = 22,
) -> pd.Series:
    """Compute annualized realized volatility from a daily price series.

    vol = sqrt(252 * rolling_mean(log_returns^2, window))

    Works for any asset class (FX, commodities, equities).

    Parameters
    ----------
    prices : pd.Series
        Daily price series (FX rates, commodity prices, etc.).
    window : int
        Rolling window in trading days (default: 22).

    Returns
    -------
    pd.Series
        Annualized realized vol. Always positive.
    """
    log_ret = np.log(prices / prices.shift(1))
    return np.sqrt(252.0 * (log_ret**2).rolling(window).mean())


# Backwards-compatible aliases
compute_fx_vol = compute_rolling_vol
compute_commodity_vol = compute_rolling_vol


def compute_vix_rv_ratio(
    vix: pd.Series,
    rv: pd.Series,
) -> pd.Series:
    """Compute VIX-to-realized variance ratio.

    ratio = (VIX / 100)^2 / (rv * 252)

    Parameters
    ----------
    vix : pd.Series
        VIX daily close in percentage points (e.g., 20.0 = 20%).
    rv : pd.Series
        Daily realized variance (not annualized).

    Returns
    -------
    pd.Series
        Ratio > 1 means implied > realized (normal). Always positive.
    """
    implied_var = (vix / 100.0) ** 2
    annualized_rv = rv * 252.0
    return implied_var / annualized_rv


def compute_dy_spillover(
    rv_matrix: pd.DataFrame,
    h: int = 10,
    p: int = 4,
    window: int = 200,
) -> pd.Series:
    """Compute Diebold-Yilmaz (2012) total connectedness index.

    Rolling VAR(p) on log-RV panel, generalized FEVD at horizon h.
    Total spillover = sum(off-diagonal FEVD) / sum(all FEVD) * 100.

    Parameters
    ----------
    rv_matrix : pd.DataFrame
        Panel of daily RV (columns: symbols, rows: dates). At least 3 columns.
    h : int
        Forecast horizon for FEVD (default: 10).
    p : int
        VAR lag order (default: 4).
    window : int
        Rolling window length (default: 200).

    Returns
    -------
    pd.Series
        Total spillover index [0, 100], indexed by date.
    """
    from statsmodels.tsa.api import VAR

    log_rv = safe_log(rv_matrix)
    n_obs = len(log_rv)
    dates = log_rv.index
    spillover = pd.Series(np.nan, index=dates)

    # Compute every 5 days for speed, forward-fill
    compute_indices = range(window, n_obs, 5)

    for i in compute_indices:
        window_data = log_rv.iloc[i - window : i].dropna()
        if len(window_data) < p + 10:
            continue
        try:
            model = VAR(window_data)
            fitted = model.fit(maxlags=p, verbose=False)
            fevd = fitted.fevd(h)
            # FEVD decomp matrix: shape (n_vars, n_vars) at final horizon
            decomp = fevd.decomp[:, :, -1]  # last horizon step
            # Normalize rows to sum to 1
            row_sums = decomp.sum(axis=1, keepdims=True)
            row_sums[row_sums == 0] = 1.0
            normalized = decomp / row_sums
            # Total spillover = off-diagonal / total * 100
            diag_sum = np.trace(normalized)
            total = normalized.sum()
            off_diag = total - diag_sum
            spillover.iloc[i] = (off_diag / total) * 100.0
        except (np.linalg.LinAlgError, ValueError):
            continue

    # Forward-fill computed values
    spillover = spillover.ffill()
    return spillover


# ---------------------------------------------------------------------------
# FeatureLayer wrapper
# ---------------------------------------------------------------------------


@register_feature_layer("cross_asset")
class CrossAssetLayer:
    """Cross-asset spillover feature layer (Layer 4).

    Requires context with keys:
    - "treasury": DataFrame with '2y', '10y' columns
    - "fx": DataFrame with FX pair column(s)
    - "commodity": DataFrame with CL, GC columns
    - "vix": Series of VIX daily close
    - "rv_panel": DataFrame of RV for multiple symbols (for DY spillover)
    """

    name = "cross_asset"

    def compute(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict[str, pd.DataFrame] | None = None,
    ) -> pd.DataFrame:
        """Compute cross-asset features."""
        if context is None:
            raise ValueError(
                "CrossAssetLayer requires context with keys: treasury, fx, commodity, vix"
            )

        result = pd.DataFrame(index=daily_data.index)

        # --- Treasury slope: prefer yields from IVSurfaceLayer, fallback to context prices ---
        if "tsy_yield_10y" in daily_data.columns and "tsy_yield_5y" in daily_data.columns:
            # True yield spread (percentage points: 10y - 5y)
            slope = daily_data["tsy_yield_10y"] - daily_data["tsy_yield_5y"]
            result["treasury_slope_d"] = slope
            result["treasury_slope_w"] = slope.rolling(5).mean()
        elif "treasury" in context:
            tsy = context["treasury"].reindex(daily_data.index)
            if "10y" in tsy.columns and "2y" in tsy.columns:
                slope = compute_treasury_slope(tsy["10y"], tsy["2y"])
                result["treasury_slope_d"] = slope
                result["treasury_slope_w"] = slope.rolling(5).mean()

        # --- FX vol: always positive, log-transform ---
        if "fx" in context:
            fx = context["fx"].reindex(daily_data.index)
            # Take first column as primary FX pair
            fx_col = fx.columns[0] if len(fx.columns) > 0 else None
            if fx_col is not None:
                fx_vol = compute_fx_vol(fx[fx_col])
                fx_features = lagged_log_features(fx_vol, "fx_vol", windows=[5])
                result = pd.concat([result, fx_features], axis=1)

        # --- Commodity vol: prefer OVX from IVSurfaceLayer, fallback to realized ---
        if "ovx" in daily_data.columns:
            # OVX is CBOE Oil Volatility Index (implied, forward-looking)
            result["log_commodity_vol_cl_d"] = safe_log(daily_data["ovx"])
        elif "commodity" in context:
            comm = context["commodity"].reindex(daily_data.index)
            if "CL" in comm.columns:
                cl_vol = compute_commodity_vol(comm["CL"])
                result["log_commodity_vol_cl_d"] = safe_log(cl_vol)

        # --- VIX level features (log_vix_d/w/m, log_vix_rv_ratio_d) ---
        # These capture the LEVEL of implied vol — the market's direct forecast
        # of future realized vol. Complementary to OptionsLayer's VIX-derived
        # features (vix_x_log_rv_d = interaction, realized_vol_of_vix_d = vol-of-vol).
        vix = None
        if "vix" in daily_data.columns:
            vix = daily_data["vix"]
        elif "vix" in context:
            vix = context["vix"].reindex(daily_data.index)

        if vix is not None:
            vix_features = lagged_log_features(vix, "vix")
            result = pd.concat([result, vix_features], axis=1)

            # VIX/RV ratio: always positive, log-transform
            if "rv" in daily_data.columns:
                ratio = compute_vix_rv_ratio(vix, daily_data["rv"])
                result["log_vix_rv_ratio_d"] = safe_log(ratio)

        # --- DY spillover: [0,100] level ---
        if "rv_panel" in context:
            rv_panel = context["rv_panel"].reindex(daily_data.index)
            if rv_panel.shape[1] >= 3:
                spillover = compute_dy_spillover(rv_panel)
                result["dy_spillover_d"] = spillover

        return result
