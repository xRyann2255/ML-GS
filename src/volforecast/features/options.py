"""Options-implied features (Layer 2).

Extracts forward-looking information from the SPX IV surface:
- ATM implied volatility at multiple tenors
- Variance risk premium (VRP = IV^2 - RV)
- Volatility skew (25-delta risk reversal)
- Term structure slope
- Butterfly spread

Key functions:
    compute_vrp        — Variance risk premium
    compute_skew       — 25-delta skew (risk reversal)
    compute_term_slope — IV term structure slope
    compute_butterfly  — Butterfly spread (convexity)
"""

from __future__ import annotations

import pandas as pd

from volforecast.features.transforms import lagged_log_features, safe_log
from volforecast.registry import register_feature_layer


def compute_vrp(atm_iv: pd.Series, rv: pd.Series) -> pd.Series:
    """Compute ex-post variance risk premium (Carr & Wu 2009 proxy).

    VRP = (atm_iv_pct / 100)^2 - rv_daily * 252

    This is the "realized" or "ex-post" VRP proxy that uses contemporaneous
    realized variance. For the conditional VRP (Bollerslev, Tauchen & Zhou
    2009, RFS), use iv_features.build_iv_feature_panel which substitutes
    E_t[RV_{t+1:t+22}] from a HAR-CJ model.

    Parameters
    ----------
    atm_iv : pd.Series
        ATM implied volatility in percentage points (e.g., 20.0 = 20%).
    rv : pd.Series
        Daily realized variance (not annualized).

    Returns
    -------
    pd.Series
        Variance risk premium. Can be negative.
    """
    return (atm_iv / 100.0) ** 2 - rv * 252.0


def compute_skew(iv_put_25d: pd.Series, iv_call_25d: pd.Series) -> pd.Series:
    """Compute 25-delta risk reversal (skew).

    Skew = IV(25d put) - IV(25d call).
    Positive skew indicates higher demand for downside protection.

    Parameters
    ----------
    iv_put_25d : pd.Series
        25-delta put IV.
    iv_call_25d : pd.Series
        25-delta call IV.

    Returns
    -------
    pd.Series
        Skew. Can be negative.
    """
    return iv_put_25d - iv_call_25d


def compute_term_slope(atm_short: pd.Series, atm_long: pd.Series) -> pd.Series:
    """Compute IV term structure slope.

    Slope = ATM_3m - ATM_1m.
    Positive = contango (normal). Negative = backwardation (stress).

    Parameters
    ----------
    atm_short : pd.Series
        Short-tenor ATM IV (e.g., 1m).
    atm_long : pd.Series
        Long-tenor ATM IV (e.g., 3m).

    Returns
    -------
    pd.Series
        Term slope. Can be negative.
    """
    return atm_long - atm_short


def compute_butterfly(
    iv_put_25d: pd.Series, iv_call_25d: pd.Series, iv_atm: pd.Series
) -> pd.Series:
    """Compute butterfly spread (convexity of smile).

    Butterfly = 0.5 * (IV_25dP + IV_25dC) - IV_ATM.
    Measures kurtosis premium / tail risk pricing.

    Parameters
    ----------
    iv_put_25d : pd.Series
        25-delta put IV.
    iv_call_25d : pd.Series
        25-delta call IV.
    iv_atm : pd.Series
        ATM IV.

    Returns
    -------
    pd.Series
        Butterfly spread. Non-negative for well-behaved smiles.
    """
    return 0.5 * (iv_put_25d + iv_call_25d) - iv_atm


@register_feature_layer("options")
class OptionsLayer:
    """Options-implied feature layer (Layer 2).

    Reads IV columns from daily_data (pre-merged by IVSurfaceLayer) or from
    the legacy context["iv_surface"] path. Computes derived features:
    VRP, skew, term slope, IV-RV gap, VVIX-derived, VIX interaction.

    Expected daily_data columns (from IVSurfaceLayer):
    - iv_1m_atm, iv_3m_atm: ATM IV in vol points (e.g., 15.0 = 15%)
    - iv_1m_25dp: 25-delta put IV in vol points
    - vvix: CBOE VVIX index points
    - iv_dispersion: cross-sectional IV std

    daily_data must also contain 'rv' column (daily realized variance).
    context parameter kept for interface compatibility (unused by new path).
    """

    name = "options"

    def compute(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict | None = None,
    ) -> pd.DataFrame:
        """Compute options-implied features.

        Returns columns:
        - log_atm_iv_d, log_atm_iv_w, log_atm_iv_m (log-transformed ATM IV)
        - vrp_d, vrp_w, vrp_m (variance risk premium)
        - iv_rv_gap_d (IV minus sqrt annualized RV)
        - iv_term_slope_d, iv_term_slope_w (3m - 1m ATM)
        - iv_skew_d, iv_skew_w (25dp - ATM)
        - iv_momentum_d (daily ATM IV change)
        - vvix_d (VVIX in decimal)
        - vvix_innovation_d (daily VVIX change)
        - realized_vol_of_vix_d (22-day rolling vol of log VIX returns)
        - vvix_rp_d (VVIX/100 - realized_vol_of_vix)
        - atm_iv_x_log_rv_d/w/m (ATM IV × log(RV) at daily/weekly/monthly)
        - vix_x_log_rv_d/w/m (VIX × log(RV) at daily/weekly/monthly)
        - iv_dispersion_d (cross-sectional IV std)
        """
        # --- New path: read from daily_data (IVSurfaceLayer pre-merged) ---
        if "iv_1m_atm" in daily_data.columns:
            return self._compute_from_daily_data(daily_data)

        # --- Legacy path: read from context["iv_surface"] ---
        if context is not None and "iv_surface" in context:
            return self._compute_from_context(daily_data, context["iv_surface"])

        # --- Graceful degradation: no IV data available ---
        return pd.DataFrame(index=daily_data.index)

    def _compute_from_daily_data(self, daily_data: pd.DataFrame) -> pd.DataFrame:
        """Per-symbol IV path: IV[T] aligned to rv[T] by IVSurfaceLayer (no shift)."""
        import numpy as np

        result = pd.DataFrame(index=daily_data.index)

        atm_iv = daily_data["iv_1m_atm"]

        # --- log ATM IV (d/w/m) ---
        atm_features = lagged_log_features(atm_iv, "atm_iv")
        result = pd.concat([result, atm_features], axis=1)

        # --- 1w ATM IV: horizon-matched tenor for short-horizon forecasting ---
        if "iv_1w_atm" in daily_data.columns:
            atm_iv_1w = daily_data["iv_1w_atm"]
            result["log_atm_iv_1w_d"] = safe_log(atm_iv_1w)
            # Short-term slope: 1m - 1w (positive = contango, negative = stress)
            result["iv_term_slope_1w1m_d"] = atm_iv - atm_iv_1w

        # --- 0DTE ATM IV: exact tenor match for h=1 forecasting ---
        if "iv_0dte_atm" in daily_data.columns:
            atm_iv_0dte = daily_data["iv_0dte_atm"]
            result["log_atm_iv_0dte_d"] = safe_log(atm_iv_0dte)

        # --- 1DTE ATM IV: forward-looking 1-day tenor (tomorrow's expiry) ---
        if "iv_1dte_atm" in daily_data.columns:
            atm_iv_1dte = daily_data["iv_1dte_atm"]
            result["log_atm_iv_1dte_d"] = safe_log(atm_iv_1dte)
            # Ultra-short-term slope: 1w - 0dte (positive = contango, negative = inversion)
            if "iv_1w_atm" in daily_data.columns:
                result["iv_term_slope_0dte1w_d"] = daily_data["iv_1w_atm"] - atm_iv_0dte
                # Log-ratio: de-biased event-intensity signal (pcorr=0.24 with fwd RV)
                # Strips VRP bias by construction; captures when near-term vol
                # pricing diverges from 1W surface (event days, gamma spikes)
                result["log_iv_0dte_1w_ratio_d"] = safe_log(atm_iv_0dte) - safe_log(
                    daily_data["iv_1w_atm"]
                )
            # IV acceleration: 0dte deviation from 5-day moving average
            # Positive = IV spiking above recent norm (stress signal)
            iv_0dte_ma5 = atm_iv_0dte.rolling(5, min_periods=1).mean()
            result["iv_0dte_accel_d"] = atm_iv_0dte - iv_0dte_ma5

        # --- VRP: (IV/100)^2 - RV*252 ---
        # Use variance swap strike (iv_vs_0dte) when available — correct measure
        # for GSVIVS signal. Falls back to ATM IV (iv_1m_atm) when unavailable.
        if "rv" in daily_data.columns:
            rv = daily_data["rv"]
            if "iv_vs_0dte" in daily_data.columns:
                vrp_iv = daily_data["iv_vs_0dte"]
            else:
                vrp_iv = atm_iv
            vrp = compute_vrp(vrp_iv, rv)
            result["vrp_d"] = vrp
            result["vrp_w"] = vrp.rolling(5).mean()
            result["vrp_m"] = vrp.rolling(22).mean()

        # --- IV-RV gap: atm_iv - sqrt(rv*252)*100 ---
        if "rv" in daily_data.columns:
            rv = daily_data["rv"]
            result["iv_rv_gap_d"] = atm_iv - np.sqrt(rv * 252) * 100

        # --- Term slope: 3m - 1m ---
        if "iv_3m_atm" in daily_data.columns:
            ts = compute_term_slope(atm_iv, daily_data["iv_3m_atm"])
            result["iv_term_slope_d"] = ts
            result["iv_term_slope_w"] = ts.rolling(5).mean()

        # --- Skew: true risk-reversal = 25dp - 25dc ---
        if "iv_1m_25dp" in daily_data.columns and "iv_1m_25dc" in daily_data.columns:
            skew = daily_data["iv_1m_25dp"] - daily_data["iv_1m_25dc"]
            result["iv_skew_d"] = skew
            result["iv_skew_w"] = skew.rolling(5).mean()
        elif "iv_1m_25dp" in daily_data.columns:
            # Fallback: put wing - ATM (approximate, missing call wing)
            skew = daily_data["iv_1m_25dp"] - atm_iv
            result["iv_skew_d"] = skew
            result["iv_skew_w"] = skew.rolling(5).mean()

        # --- Butterfly: 0.5*(25dp + 25dc) - ATM ---
        if "iv_1m_25dp" in daily_data.columns and "iv_1m_25dc" in daily_data.columns:
            butterfly = 0.5 * (daily_data["iv_1m_25dp"] + daily_data["iv_1m_25dc"]) - atm_iv
            result["iv_butterfly_d"] = butterfly
            result["iv_butterfly_w"] = butterfly.rolling(5).mean()

        # --- IV momentum ---
        result["iv_momentum_d"] = atm_iv - atm_iv.shift(1)

        # --- VVIX features (separate columns to avoid NaN cascade) ---
        if "vvix" in daily_data.columns:
            vvix = daily_data["vvix"]
            result["vvix_d"] = vvix / 100.0  # decimal

            # VVIX innovation
            result["vvix_innovation_d"] = vvix - vvix.shift(1)

            # VVIX acceleration: deviation from 5-day moving average
            vvix_ma5 = vvix.rolling(5, min_periods=1).mean()
            result["vvix_accel_d"] = vvix - vvix_ma5

            # Realized vol-of-VIX from actual VIX log-returns
            if "vix" in daily_data.columns:
                vix = daily_data["vix"]
                log_ret_vix = np.log(vix / vix.shift(1))
                rvol_vix = np.sqrt(252 * (log_ret_vix**2).rolling(22).mean())
                result["realized_vol_of_vix_d"] = rvol_vix

                # VVIX risk premium: implied vol-of-vol minus realized vol-of-VIX
                result["vvix_rp_d"] = vvix / 100.0 - rvol_vix

        # --- IV × log(RV) interactions (CSV 2023: #1 ML gain source) ---
        if "rv" in daily_data.columns:
            log_rv_d = np.log(daily_data["rv"].clip(lower=1e-10))
            # Weekly/monthly log-RV: use pre-computed from HAR layer if available,
            # otherwise compute locally from rv.
            if "log_rv_w" in daily_data.columns:
                log_rv_w = daily_data["log_rv_w"]
            else:
                log_rv_w = np.log(daily_data["rv"].rolling(5).mean().clip(lower=1e-10))
            if "log_rv_m" in daily_data.columns:
                log_rv_m = daily_data["log_rv_m"]
            else:
                log_rv_m = np.log(daily_data["rv"].rolling(22).mean().clip(lower=1e-10))

            # Per-symbol ATM IV × log(RV): varies across all 21 symbols in
            # pooled training — each symbol gets its own IV level × RV signal.
            result["atm_iv_x_log_rv_d"] = atm_iv * log_rv_d
            result["atm_iv_x_log_rv_w"] = atm_iv * log_rv_w
            result["atm_iv_x_log_rv_m"] = atm_iv * log_rv_m
            # Market-wide VIX × log(RV): captures systematic fear × RV.
            if "vix" in daily_data.columns:
                result["vix_x_log_rv_d"] = daily_data["vix"] * log_rv_d
                result["vix_x_log_rv_w"] = daily_data["vix"] * log_rv_w
                result["vix_x_log_rv_m"] = daily_data["vix"] * log_rv_m

        # --- IV dispersion (market-wide) ---
        if "iv_dispersion" in daily_data.columns:
            result["iv_dispersion_d"] = daily_data["iv_dispersion"]

        # --- VIX change × absolute return interaction ---
        if "vix" in daily_data.columns and "abs_ret_d" in daily_data.columns:
            vix_change = daily_data["vix"] - daily_data["vix"].shift(1)
            result["vix_change_x_abs_ret"] = vix_change * daily_data["abs_ret_d"]

        return result

    def _compute_from_context(
        self, daily_data: pd.DataFrame, iv_data: pd.DataFrame
    ) -> pd.DataFrame:
        """Legacy path: read from context['iv_surface'] (Marquee-sourced SPX IV)."""
        import numpy as np

        result = pd.DataFrame(index=daily_data.index)

        # --- ATM IV: always positive, use lagged_log_features ---
        atm_iv_1m = iv_data["atm_iv_1m"].reindex(daily_data.index)
        atm_features = lagged_log_features(atm_iv_1m, "atm_iv")
        result = pd.concat([result, atm_features], axis=1)

        # --- VRP ---
        if "vrp" in iv_data.columns:
            vrp = iv_data["vrp"].reindex(daily_data.index)
        else:
            rv = daily_data["rv"]
            vrp = compute_vrp(atm_iv_1m, rv)
        result["vrp_d"] = vrp
        result["vrp_w"] = vrp.rolling(5).mean()
        result["vrp_m"] = vrp.rolling(22).mean()

        # --- Skew ---
        if "skew_1m" in iv_data.columns:
            skew = iv_data["skew_1m"].reindex(daily_data.index)
            result["iv_skew_d"] = skew
            result["iv_skew_w"] = skew.rolling(5).mean()

        # --- Term slope ---
        if "term_slope" in iv_data.columns:
            ts = iv_data["term_slope"].reindex(daily_data.index)
        elif "atm_iv_3m" in iv_data.columns:
            atm_iv_3m = iv_data["atm_iv_3m"].reindex(daily_data.index)
            ts = compute_term_slope(atm_iv_1m, atm_iv_3m)
        else:
            ts = None
        if ts is not None:
            result["iv_term_slope_d"] = ts
            result["iv_term_slope_w"] = ts.rolling(5).mean()

        # --- Butterfly ---
        if "butterfly_1m" in iv_data.columns:
            bf = iv_data["butterfly_1m"].reindex(daily_data.index)
        elif "iv_put_25d" in iv_data.columns and "iv_call_25d" in iv_data.columns:
            put_25d = iv_data["iv_put_25d"].reindex(daily_data.index)
            call_25d = iv_data["iv_call_25d"].reindex(daily_data.index)
            bf = compute_butterfly(put_25d, call_25d, atm_iv_1m)
        else:
            bf = None
        if bf is not None:
            result["iv_butterfly_d"] = bf
            result["iv_butterfly_w"] = bf.rolling(5).mean()

        # --- IV-RV gap ---
        if "iv_rv_gap" in iv_data.columns:
            gap = iv_data["iv_rv_gap"].reindex(daily_data.index)
            result["iv_rv_gap_d"] = gap
            result["iv_rv_gap_w"] = gap.rolling(5).mean()

        # --- VIX level ---
        if "vix" in iv_data.columns:
            result["vix_d"] = iv_data["vix"].reindex(daily_data.index)

        # --- VIX innovation ---
        if "vix_innovation" in iv_data.columns:
            result["vix_innovation_d"] = iv_data["vix_innovation"].reindex(daily_data.index)

        # --- Vol-of-VIX ---
        if "vol_of_vix" in iv_data.columns:
            result["vol_of_vix_d"] = iv_data["vol_of_vix"].reindex(daily_data.index)

        # --- VTS ---
        if "vts" in iv_data.columns:
            result["vts_d"] = iv_data["vts"].reindex(daily_data.index)

        # --- Forward vol ---
        if "forward_vol_1m3m" in iv_data.columns:
            result["forward_vol_1m3m_d"] = iv_data["forward_vol_1m3m"].reindex(daily_data.index)

        # --- VIX × log-RV interaction ---
        if "vix" in iv_data.columns and "rv" in daily_data.columns:
            vix = iv_data["vix"].reindex(daily_data.index)
            log_rv_d = np.log(daily_data["rv"].clip(lower=1e-10))
            if "log_rv_w" in daily_data.columns:
                log_rv_w = daily_data["log_rv_w"]
            else:
                log_rv_w = np.log(daily_data["rv"].rolling(5).mean().clip(lower=1e-10))
            if "log_rv_m" in daily_data.columns:
                log_rv_m = daily_data["log_rv_m"]
            else:
                log_rv_m = np.log(daily_data["rv"].rolling(22).mean().clip(lower=1e-10))
            result["vix_x_log_rv_d"] = vix * log_rv_d
            result["vix_x_log_rv_w"] = vix * log_rv_w
            result["vix_x_log_rv_m"] = vix * log_rv_m

        return result
