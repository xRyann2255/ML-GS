"""GSVIVS01 strategy signal features (73 features).

Produces the feature set used by the GSVIVS01 short-variance strategy:
returns / realized volatility on SPX / VIX / VX1, VIX vol-of-vol dynamics,
VIX option skew, VIX term structure, SPX 1M put-skew dynamics, 1M/3M skew
term-structure ratios, and IG/HY credit CDS returns.

All inputs are read from ``daily_data`` (the enriched frame produced upstream
by ``IVSurfaceLayer``). No external data loading happens here.

Graceful degradation: if any required enriched column is missing, the derived
features that depend on it are returned as all-NaN. The output DataFrame
always has exactly 73 columns and shares ``daily_data``'s index.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from volforecast.registry import register_feature_layer

_SQRT_252 = np.sqrt(252)


def _series(daily_data: pd.DataFrame, col: str) -> pd.Series:
    """Return ``daily_data[col]`` if present, otherwise an all-NaN series.

    All downstream operations (``pct_change``, ``diff``, arithmetic, rolling)
    propagate NaN, so callers get all-NaN derived features "for free".
    """
    if col in daily_data.columns:
        return daily_data[col]
    return pd.Series(np.nan, index=daily_data.index, dtype=float)


def _return_realized_block(series: pd.Series, prefix: str) -> dict[str, pd.Series]:
    """3 pct_change horizons + 3 realized-vol horizons (abs, roll5 std, roll20 std)."""
    ret_1d = series.pct_change(1)
    return {
        f"{prefix}_ret_1d": ret_1d,
        f"{prefix}_ret_3d": series.pct_change(3),
        f"{prefix}_ret_5d": series.pct_change(5),
        f"{prefix}_rea_1d": ret_1d.abs() * _SQRT_252,
        f"{prefix}_rea_5d": ret_1d.rolling(5).std() * _SQRT_252,
        f"{prefix}_rea_20d": ret_1d.rolling(20).std() * _SQRT_252,
    }


def _skew_block(
    level: pd.Series,
    prefix: str,
    *,
    diff_lags: tuple[int, ...] = (1, 3, 5),
) -> dict[str, pd.Series]:
    """Return {prefix: level, f"{prefix}_diff_{lag}d": level.diff(lag), ...}."""
    out: dict[str, pd.Series] = {prefix: level}
    for lag in diff_lags:
        out[f"{prefix}_diff_{lag}d"] = level.diff(lag)
    return out


@register_feature_layer("gsvivs_signals")
class GsvivsSignalsLayer:
    """73 GSVIVS01-derived features consumed from the enriched daily frame."""

    name = "gsvivs_signals"

    def compute(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        idx = daily_data.index

        # --- Source series (all-NaN if missing) ---
        close = _series(daily_data, "close")
        vix = _series(daily_data, "vix")
        vx1 = _series(daily_data, "vx1")

        vix_iv_atm = _series(daily_data, "vix_iv_1m_atm")
        vix_iv_25 = _series(daily_data, "vix_iv_1m_25dc")
        vix_iv_5 = _series(daily_data, "vix_iv_1m_5dc")

        iv_1m_atm = _series(daily_data, "iv_1m_atm")
        iv_1m_25 = _series(daily_data, "iv_1m_25dp")
        iv_1m_5 = _series(daily_data, "iv_1m_5dp")

        iv_3m_atm = _series(daily_data, "iv_3m_atm")
        iv_3m_25 = _series(daily_data, "iv_3m_25dp")
        iv_3m_5 = _series(daily_data, "iv_3m_5dp")

        credit_ig = _series(daily_data, "credit_ig_5y")
        credit_hy = _series(daily_data, "credit_hy_5y")

        out: dict[str, pd.Series] = {}

        # --- Group 1: SPX returns/realized ---
        out.update(_return_realized_block(close, "spx"))

        # --- Group 2: VIX returns/realized ---
        out.update(_return_realized_block(vix, "vix"))

        # --- Group 3: VX1 returns/realized ---
        out.update(_return_realized_block(vx1, "vx1"))

        # --- Group 4: VIX vol-of-vol dynamics (pct_change + diff of VIX ATM IV) ---
        out["vix_vol_ret_1d"] = vix_iv_atm.pct_change(1)
        out["vix_vol_ret_3d"] = vix_iv_atm.pct_change(3)
        out["vix_vol_ret_5d"] = vix_iv_atm.pct_change(5)
        out["vix_vol_diff_1d"] = vix_iv_atm.diff(1)
        out["vix_vol_diff_3d"] = vix_iv_atm.diff(3)
        out["vix_vol_diff_5d"] = vix_iv_atm.diff(5)

        # --- Group 5: VIX option skew (12 = 3 skews x (level + 3 diffs)) ---
        out.update(_skew_block(vix_iv_atm - vix_iv_25, "vix_skew_50d25d"))
        out.update(_skew_block(vix_iv_atm - vix_iv_5, "vix_skew_50d5d"))
        out.update(_skew_block(vix_iv_25 - vix_iv_5, "vix_skew_25d5d"))

        # --- Group 6: VIX term structure (level + 3 diffs) ---
        vix_ts_level = vix / vx1 - 1.0
        out["vix_ts_level"] = vix_ts_level
        out["vix_ts_diff_1d"] = vix_ts_level.diff(1)
        out["vix_ts_diff_3d"] = vix_ts_level.diff(3)
        out["vix_ts_diff_5d"] = vix_ts_level.diff(5)

        # --- Group 7: SPX 1M put skew (12 = 3 skews x (level + 3 diffs)) ---
        skew_50_25_1m = iv_1m_atm - iv_1m_25
        skew_50_5_1m = iv_1m_atm - iv_1m_5
        skew_25_5_1m = iv_1m_25 - iv_1m_5
        out.update(_skew_block(skew_50_25_1m, "spx_skew_50d25d_1m"))
        out.update(_skew_block(skew_50_5_1m, "spx_skew_50d5d_1m"))
        out.update(_skew_block(skew_25_5_1m, "spx_skew_25d5d_1m"))

        # --- Group 8: SPX skew term structure (3M levels + 1M/3M ratios + ret dynamics) ---
        skew_50_25_3m = iv_3m_atm - iv_3m_25
        skew_50_5_3m = iv_3m_atm - iv_3m_5
        skew_25_5_3m = iv_3m_25 - iv_3m_5

        out["spx_skew_50d25d_3m"] = skew_50_25_3m
        out["spx_skew_50d5d_3m"] = skew_50_5_3m
        out["spx_skew_25d5d_3m"] = skew_25_5_3m

        ts_50_25 = skew_50_25_1m / skew_50_25_3m
        ts_50_5 = skew_50_5_1m / skew_50_5_3m
        ts_25_5 = skew_25_5_1m / skew_25_5_3m

        out["spx_skew_ts_50d25d"] = ts_50_25
        out["spx_skew_ts_50d25d_ret_1d"] = ts_50_25.pct_change(1)
        out["spx_skew_ts_50d25d_ret_3d"] = ts_50_25.pct_change(3)
        out["spx_skew_ts_50d25d_ret_5d"] = ts_50_25.pct_change(5)

        out["spx_skew_ts_50d5d"] = ts_50_5
        out["spx_skew_ts_50d5d_ret_1d"] = ts_50_5.pct_change(1)
        out["spx_skew_ts_50d5d_ret_3d"] = ts_50_5.pct_change(3)
        out["spx_skew_ts_50d5d_ret_5d"] = ts_50_5.pct_change(5)

        out["spx_skew_ts_25d5d"] = ts_25_5
        out["spx_skew_ts_25d5d_ret_1d"] = ts_25_5.pct_change(1)
        out["spx_skew_ts_25d5d_ret_3d"] = ts_25_5.pct_change(3)
        out["spx_skew_ts_25d5d_ret_5d"] = ts_25_5.pct_change(5)

        # --- Group 9: Credit CDS returns ---
        out["credit_ig_ret_1d"] = credit_ig.pct_change(1)
        out["credit_ig_ret_3d"] = credit_ig.pct_change(3)
        out["credit_ig_ret_5d"] = credit_ig.pct_change(5)
        out["credit_hy_ret_1d"] = credit_hy.pct_change(1)
        out["credit_hy_ret_3d"] = credit_hy.pct_change(3)
        out["credit_hy_ret_5d"] = credit_hy.pct_change(5)

        result = pd.DataFrame(out, index=idx)
        return result
