"""IV Surface feature layer — merges per-symbol IV data into daily_data.

Loads per-symbol ATM IV, skew, and market-wide VVIX/dispersion from
data/raw/iv/ parquets. No shift applied — IV[T] is observed at
close of day T, same moment as rv[T]. The prediction point is close-of-day T
targeting rv[T+1], so using IV[T] is consistent with HAR features using rv[T].

This layer runs BEFORE OptionsLayer in the feature_layers config so that
IV columns are available in daily_data for downstream computation.

Config example:
    feature_layers: [iv_surface, har_core, asymmetry, options]
"""

from __future__ import annotations

import logging

import pandas as pd

from volforecast.data.edrvol import load_iv_cache
from volforecast.registry import register_feature_layer

logger = logging.getLogger(__name__)


@register_feature_layer("iv_surface")
class IVSurfaceLayer:
    """Merge per-symbol IV data + market-wide VVIX into daily_data.

    Loads from data/raw/iv/{symbol}.parquet, _VVIX.parquet,
    and _MARKET.parquet. No shift applied — IV[T] and rv[T] are both
    observed at close of day T; the target is rv[T+1].

    Returns DataFrame with columns: iv_1m_atm, iv_3m_atm, iv_1m_25dp,
    vvix, iv_dispersion. Returns empty DataFrame if IV data unavailable
    (graceful degradation for symbols without IV coverage).

    Requires context["symbol"] to identify which symbol's data to load.
    """

    name = "iv_surface"
    _enrichment_only = True  # Output enriches daily_data for downstream layers

    def compute(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict | None = None,
    ) -> pd.DataFrame:
        """Load and merge per-symbol IV + market-wide VVIX/dispersion."""
        result = pd.DataFrame(index=daily_data.index)

        # Determine symbol from context
        symbol = None
        if context is not None:
            symbol = context.get("symbol")

        if symbol is None:
            logger.debug("IVSurfaceLayer: no symbol in context, returning empty")
            return result

        # --- Per-symbol IV ---
        iv_data = load_iv_cache(symbol)
        if iv_data is not None and not iv_data.empty:
            iv_data.index = pd.DatetimeIndex(iv_data.index)
            # No shift: IV[T] is observed at close of day T, same moment as rv[T].
            # The prediction point is close-of-day T, targeting rv[T+1].
            # Using IV[T] is consistent with HAR features using rv[T].
            for col in iv_data.columns:
                result[col] = iv_data[col].reindex(daily_data.index)
        else:
            logger.debug("IVSurfaceLayer: no IV data for %s", symbol)

        # --- SPY fallback: use VIX as iv_1m_atm when per-symbol cache is
        # inadequate.  VIX = 30-day ATM IV on SPX ≈ SPY 1m ATM IV.
        if symbol == "SPY":
            iv_1m_valid = result.get("iv_1m_atm")
            coverage = 0 if iv_1m_valid is None else iv_1m_valid.notna().sum()
            if coverage < len(daily_data) * 0.5:
                vix_data = load_iv_cache("_VIX")
                if vix_data is not None and not vix_data.empty:
                    vix_data.index = pd.DatetimeIndex(vix_data.index)
                    vix_col = (
                        vix_data.iloc[:, 0] if isinstance(vix_data, pd.DataFrame) else vix_data
                    )
                    result["iv_1m_atm"] = vix_col.reindex(daily_data.index)
                    logger.info(
                        "IVSurfaceLayer: using VIX as SPY iv_1m_atm fallback (%d/%d coverage)",
                        result["iv_1m_atm"].notna().sum(),
                        len(daily_data),
                    )

        # --- Market-wide VVIX ---
        vvix_data = load_iv_cache("_VVIX")
        if vvix_data is not None and not vvix_data.empty:
            vvix_data.index = pd.DatetimeIndex(vvix_data.index)
            vvix_col = vvix_data.iloc[:, 0] if isinstance(vvix_data, pd.DataFrame) else vvix_data
            result["vvix"] = vvix_col.reindex(daily_data.index)

        # --- VIX index (market-wide) ---
        vix_data = load_iv_cache("_VIX")
        if vix_data is not None and not vix_data.empty:
            vix_data.index = pd.DatetimeIndex(vix_data.index)
            vix_col = vix_data.iloc[:, 0] if isinstance(vix_data, pd.DataFrame) else vix_data
            result["vix"] = vix_col.reindex(daily_data.index)

        # --- OVX (CBOE Crude Oil Volatility Index, market-wide) ---
        ovx_data = load_iv_cache("_OVX")
        if ovx_data is not None and not ovx_data.empty:
            ovx_data.index = pd.DatetimeIndex(ovx_data.index)
            ovx_col = ovx_data.iloc[:, 0] if isinstance(ovx_data, pd.DataFrame) else ovx_data
            result["ovx"] = ovx_col.reindex(daily_data.index)

        # --- Treasury yields (market-wide) ---
        tsy_data = load_iv_cache("_TREASURY_YIELDS")
        if tsy_data is not None and not tsy_data.empty:
            tsy_data.index = pd.DatetimeIndex(tsy_data.index)
            for col in tsy_data.columns:
                result[f"tsy_yield_{col}"] = tsy_data[col].reindex(daily_data.index)

        # --- IV dispersion (cross-sectional) ---
        mkt_data = load_iv_cache("_MARKET")
        if mkt_data is not None and not mkt_data.empty:
            mkt_data.index = pd.DatetimeIndex(mkt_data.index)
            disp_col = mkt_data.iloc[:, 0] if isinstance(mkt_data, pd.DataFrame) else mkt_data
            result["iv_dispersion"] = disp_col.reindex(daily_data.index)

        # --- 0DTE ATM IV (SPX, market-wide) ---
        # Convert from decimal (0.17) to vol points (17.0) to match other IV columns.
        from volforecast.data.edrvol import fetch_0dte_iv, fetch_1dte_iv

        try:
            iv_0dte = fetch_0dte_iv("SPX", daily_data.index[0].date(), daily_data.index[-1].date())
        except Exception:
            iv_0dte = None
        if iv_0dte is not None and not iv_0dte.empty:
            result["iv_0dte_atm"] = iv_0dte.reindex(daily_data.index) * 100.0
        elif "iv_0dte" in result.columns:
            # Fallback: per-symbol iv_0dte already loaded (decimal), convert
            result["iv_0dte_atm"] = result["iv_0dte"] * 100.0

        # --- 1DTE ATM IV (SPX, market-wide) ---
        # Options expiring TOMORROW observed at today's close — the correct
        # forward-looking 1-day IV for h=1 forecasting.
        try:
            iv_1dte = fetch_1dte_iv("SPX", daily_data.index[0].date(), daily_data.index[-1].date())
        except Exception:
            iv_1dte = None
        if iv_1dte is not None and not iv_1dte.empty:
            result["iv_1dte_atm"] = iv_1dte.reindex(daily_data.index) * 100.0
        elif "iv_1dte" in result.columns:
            # Fallback: per-symbol iv_1dte already loaded (decimal), convert
            result["iv_1dte_atm"] = result["iv_1dte"] * 100.0

        # --- 0DTE Variance Swap Strike (SPX, from EDRVS_EXPIRY cache) ---
        # This is the correct IV for GSVIVS signal: captures skew premium.
        # Already in vol points (13.57 = 13.57% annualized).
        from volforecast.data.edrvol import load_edrvs_cache

        edrvs_data = load_edrvs_cache()
        if edrvs_data is not None and not edrvs_data.empty:
            edrvs_data.index = pd.DatetimeIndex(edrvs_data.index)
            result["iv_vs_0dte"] = edrvs_data.reindex(daily_data.index)

        return result
