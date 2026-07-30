"""Microstructure features (Layer 3).

Computes daily features from two cached data sources:
1. Daily aggregates (data/raw/micro/{SYM}.parquet):
   - signed_volume_ratio, vpin, order_flow_imbalance, volumes
2. Intraday 10s bar sequences (data/raw/micro/sequences/{SYM}.parquet):
   - Kyle's lambda, Amihud illiquidity, volume concentration,
     intraday vol ratio, flow persistence

Key functions:
    compute_kyle_lambda         — Price impact (OLS slope of Δprice on net_flow)
    compute_amihud              — Amihud (2002) illiquidity ratio
    compute_volume_concentration — Herfindahl of volume across time bins
    compute_intraday_vol_ratio  — RV(first half) / RV(second half)
    compute_flow_persistence    — AR(1) coefficient of net order flow
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from volforecast.data.micro import load_micro_cache, load_sequences_cache
from volforecast.features.transforms import safe_log
from volforecast.registry import register_feature_layer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Intraday feature computation functions
# ---------------------------------------------------------------------------


def compute_kyle_lambda(
    price_changes: np.ndarray,
    net_flow: np.ndarray,
) -> float:
    """Compute Kyle's lambda (price impact coefficient).

    OLS regression: Δprice_i = λ * net_flow_i + ε_i
    λ = Cov(Δp, Q) / Var(Q)

    Higher λ indicates more price impact per unit of signed volume,
    implying more informed trading or less liquidity.

    Parameters
    ----------
    price_changes : ndarray
        Per-bar price changes (log returns or absolute).
    net_flow : ndarray
        Per-bar signed volume (buy - sell).

    Returns
    -------
    float
        Kyle's lambda. NaN if net_flow has zero variance.
    """
    price_changes = np.asarray(price_changes, dtype=np.float64)
    net_flow = np.asarray(net_flow, dtype=np.float64)

    # Remove NaN pairs
    mask = np.isfinite(price_changes) & np.isfinite(net_flow)
    if mask.sum() < 10:
        return float("nan")

    dp = price_changes[mask]
    q = net_flow[mask]

    var_q = np.var(q)
    if var_q < 1e-20:
        return float("nan")

    cov_dp_q = np.cov(dp, q, ddof=1)[0, 1]
    return float(cov_dp_q / var_q)


def compute_amihud(
    returns: np.ndarray,
    volumes: np.ndarray,
) -> float:
    """Compute Amihud (2002) illiquidity ratio.

    ILLIQ = mean(|r_i| / volume_i)

    Higher values indicate less liquid markets (larger price impact per
    unit volume).

    Parameters
    ----------
    returns : ndarray
        Per-bar or per-period returns.
    volumes : ndarray
        Per-bar or per-period dollar volumes.

    Returns
    -------
    float
        Amihud illiquidity. NaN if all volumes are zero.
    """
    returns = np.asarray(returns, dtype=np.float64)
    volumes = np.asarray(volumes, dtype=np.float64)

    mask = (volumes > 0) & np.isfinite(returns) & np.isfinite(volumes)
    if mask.sum() == 0:
        return float("nan")

    ratios = np.abs(returns[mask]) / volumes[mask]
    return float(np.mean(ratios))


def compute_volume_concentration(
    bar_volumes: np.ndarray,
    n_bins: int = 10,
) -> float:
    """Compute Herfindahl index of volume concentration across time bins.

    Divides the trading day into n_bins equal time slots and computes
    the Herfindahl-Hirschman Index (HHI) of volume shares.

    HHI = Σ (share_i)^2, where share_i = volume_in_bin_i / total_volume.

    Values close to 1/n_bins indicate uniform distribution; close to 1.0
    indicates extreme concentration in one period.

    Parameters
    ----------
    bar_volumes : ndarray
        Volume per intraday bar (must be non-negative).
    n_bins : int
        Number of time-of-day bins (default: 10).

    Returns
    -------
    float
        HHI in [1/n_bins, 1]. NaN if total volume is zero.
    """
    bar_volumes = np.asarray(bar_volumes, dtype=np.float64)
    total = bar_volumes.sum()
    if total <= 0:
        return float("nan")

    n_bars = len(bar_volumes)
    bin_size = max(1, n_bars // n_bins)

    # Sum volume into bins
    bin_volumes = np.zeros(n_bins)
    for i in range(n_bins):
        start = i * bin_size
        end = start + bin_size if i < n_bins - 1 else n_bars
        bin_volumes[i] = bar_volumes[start:end].sum()

    shares = bin_volumes / total
    hhi = float(np.sum(shares**2))
    return hhi


def compute_intraday_vol_ratio(
    prices: np.ndarray,
) -> float:
    """Compute ratio of first-half to second-half realized variance.

    RV_ratio = RV(first half) / RV(second half)

    High values indicate more information arrival in the morning (open
    auction, overnight news digestion). Literature shows this is
    predictive of next-day volatility.

    Parameters
    ----------
    prices : ndarray
        Intraday price series (e.g., VWAP per bar).

    Returns
    -------
    float
        Ratio of first-half RV to second-half RV. NaN if insufficient data.
    """
    prices = np.asarray(prices, dtype=np.float64)
    n = len(prices)
    if n < 4:
        return float("nan")

    mid = n // 2
    returns_first = np.diff(np.log(prices[:mid]))
    returns_second = np.diff(np.log(prices[mid:]))

    rv_first = float(np.sum(returns_first**2))
    rv_second = float(np.sum(returns_second**2))

    if rv_second < 1e-20:
        return float("nan")

    return rv_first / rv_second


def compute_flow_persistence(
    net_flows: np.ndarray,
) -> float:
    """Compute AR(1) coefficient of net order flow.

    persistence = Corr(flow_t, flow_{t-1})

    High persistence indicates herding or momentum in order flow;
    low persistence indicates mean-reversion or balanced trading.

    Parameters
    ----------
    net_flows : ndarray
        Per-bar signed volume (buy - sell).

    Returns
    -------
    float
        AR(1) coefficient in [-1, 1]. NaN if insufficient data.
    """
    net_flows = np.asarray(net_flows, dtype=np.float64)
    mask = np.isfinite(net_flows)
    flows = net_flows[mask]

    if len(flows) < 10:
        return float("nan")

    x = flows[:-1]
    y = flows[1:]

    var_x = np.var(x)
    if var_x < 1e-20:
        return float("nan")

    corr = np.corrcoef(x, y)[0, 1]
    return float(np.clip(corr, -1.0, 1.0))


# ---------------------------------------------------------------------------
# Per-day intraday feature extraction from sequences
# ---------------------------------------------------------------------------


def _compute_intraday_features_for_day(day_bars: pd.DataFrame) -> dict[str, float]:
    """Compute all intraday features for a single day's 10s bars.

    Parameters
    ----------
    day_bars : DataFrame
        Columns: buy_vol, sell_vol, net_flow, vwap, n_trades.

    Returns
    -------
    dict
        Keys: kyle_lambda_d, amihud_d, volume_concentration_d,
        intraday_vol_ratio_d, flow_persistence_d.
    """
    buy_vol = day_bars["buy_vol"].values.astype(np.float64)
    sell_vol = day_bars["sell_vol"].values.astype(np.float64)
    net_flow = day_bars["net_flow"].values.astype(np.float64)
    vwap = day_bars["vwap"].values.astype(np.float64)

    total_vol = buy_vol + sell_vol

    # Price changes (log returns of VWAP)
    valid_vwap = vwap[vwap > 0]
    if len(valid_vwap) > 1:
        log_prices = np.log(valid_vwap)
        price_changes = np.diff(log_prices)
    else:
        price_changes = np.array([])

    # Kyle's lambda
    if len(price_changes) > 10 and len(net_flow) > 10:
        # Align: price_changes has one fewer element than net_flow
        kyle = compute_kyle_lambda(price_changes, net_flow[1 : len(price_changes) + 1])
    else:
        kyle = float("nan")

    # Amihud: use bar returns and bar dollar volume
    if len(price_changes) > 1:
        bar_volumes = total_vol[1 : len(price_changes) + 1] * vwap[1 : len(price_changes) + 1]
        amihud = compute_amihud(price_changes, bar_volumes)
    else:
        amihud = float("nan")

    # Volume concentration (HHI across 10 time-of-day bins)
    vol_conc = compute_volume_concentration(total_vol, n_bins=10)

    # Intraday vol ratio (first half vs second half)
    if len(valid_vwap) > 4:
        vol_ratio = compute_intraday_vol_ratio(valid_vwap)
    else:
        vol_ratio = float("nan")

    # Flow persistence (AR(1) of net_flow)
    flow_persist = compute_flow_persistence(net_flow)

    return {
        "kyle_lambda_d": kyle,
        "amihud_d": amihud,
        "volume_concentration_d": vol_conc,
        "intraday_vol_ratio_d": vol_ratio,
        "flow_persistence_d": flow_persist,
    }


def _build_intraday_features(
    sequences: pd.DataFrame,
    index: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Compute per-day intraday features from sequence bars.

    Parameters
    ----------
    sequences : DataFrame
        Full sequences with columns: date, bar_idx, buy_vol, sell_vol,
        net_flow, vwap, n_trades.
    index : DatetimeIndex
        Target index to align output.

    Returns
    -------
    DataFrame
        Daily features aligned to target index.
    """
    # Group by date and compute features
    records: list[dict] = []

    for day_str, grp in sequences.groupby("date"):
        feats = _compute_intraday_features_for_day(grp)
        feats["date"] = pd.Timestamp(day_str)
        records.append(feats)

    if not records:
        cols = [
            "kyle_lambda_d",
            "amihud_d",
            "volume_concentration_d",
            "intraday_vol_ratio_d",
            "flow_persistence_d",
        ]
        return pd.DataFrame(columns=cols, index=index)

    df = pd.DataFrame(records).set_index("date")
    df.index = pd.DatetimeIndex(df.index)
    return df.reindex(index)


# ---------------------------------------------------------------------------
# FeatureLayer wrapper (Tier 2)
# ---------------------------------------------------------------------------


@register_feature_layer("microstructure")
class MicrostructureLayer:
    """Microstructure feature layer (Layer 3).

    Loads per-symbol daily aggregates and intraday sequences from cache,
    then computes rolling and derived features. Requires context["symbol"].

    Output features:
    - log_svr_d, log_svr_w: log signed volume ratio (daily + 5d)
    - log_vpin_d, log_vpin_w: log VPIN (daily + 5d)
    - ofi_d, ofi_w: order flow imbalance (daily + 5d)
    - volume_surprise_d: log(volume / SMA_22(volume))
    - kyle_lambda_d: Kyle's price impact
    - amihud_d: Amihud illiquidity
    - volume_concentration_d: HHI of volume across time bins
    - intraday_vol_ratio_d: first-half / second-half RV
    - flow_persistence_d: AR(1) of net order flow
    """

    name = "microstructure"

    def compute(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict | None = None,
    ) -> pd.DataFrame:
        """Compute microstructure features for one symbol."""
        result = pd.DataFrame(index=daily_data.index)

        # Determine symbol from context
        symbol = None
        if context is not None:
            symbol = context.get("symbol")

        if symbol is None:
            logger.debug("MicrostructureLayer: no symbol in context, returning empty")
            return result

        # --- Load daily aggregates ---
        micro_daily = load_micro_cache(symbol)
        if micro_daily is None or micro_daily.empty:
            logger.debug("MicrostructureLayer: no daily micro data for %s", symbol)
            return result

        # Align index
        micro_daily.index = pd.DatetimeIndex(micro_daily.index)
        micro = micro_daily.reindex(daily_data.index)

        # --- Daily ratio features ---
        # SVR: in [0, 1], log-transform
        if "signed_volume_ratio" in micro.columns:
            svr = micro["signed_volume_ratio"]
            result["log_svr_d"] = safe_log(svr)
            result["log_svr_w"] = safe_log(svr.rolling(5).mean())

        # VPIN: in [0, 1], log-transform
        if "vpin" in micro.columns:
            vpin = micro["vpin"]
            result["log_vpin_d"] = safe_log(vpin)
            result["log_vpin_w"] = safe_log(vpin.rolling(5).mean())

        # OFI: in [-1, 1], no log (signed)
        if "order_flow_imbalance" in micro.columns:
            ofi = micro["order_flow_imbalance"]
            result["ofi_d"] = ofi
            result["ofi_w"] = ofi.rolling(5).mean()

        # Volume surprise: log(today / SMA_22)
        if "total_volume" in micro.columns:
            vol = micro["total_volume"]
            vol_ma22 = vol.rolling(22).mean()
            result["volume_surprise_d"] = safe_log(vol / vol_ma22)

        # --- Intraday features from sequences ---
        sequences = load_sequences_cache(symbol)
        if sequences is not None and not sequences.empty:
            intraday_feats = _build_intraday_features(sequences, daily_data.index)
            result = pd.concat([result, intraday_feats], axis=1)
        else:
            logger.debug("MicrostructureLayer: no sequences for %s", symbol)

        return result
