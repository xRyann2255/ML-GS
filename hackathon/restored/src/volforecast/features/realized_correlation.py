"""Realized correlation feature layer — cross-symbol panel correlation.

Produces forward-looking REGIME features by measuring how synchronously
the universe of stocks has been moving recently. When average pairwise
correlation across the panel spikes (idiosyncratic dispersion collapses
into systemic moves), market-wide volatility typically follows within
1-3 days (Diebold-Yilmaz 2012 spillover index intuition).

Unlike VIX or per-symbol IV, this signal is constructed purely from
realized returns -- no options/market-data dependency. It is therefore
robust to options-data outages and serves as a complement (not substitute)
to IV-based forward-looking signals.

Computed once at first call and cached at class level (the panel is the
same for every per-symbol call within a tournament run).

Features produced (broadcast to every symbol's daily_data, same value
on a given date for all symbols -- the model can still use them via
interactions with per-symbol features):

    panel_corr_22d    -- rolling 22d average off-diagonal correlation
    panel_corr_5d     -- rolling 5d average off-diagonal correlation
    panel_corr_d      -- d/d change in panel_corr_22d (innovation signal)
    panel_corr_z      -- 60d z-score of panel_corr_22d (regime indicator)

Lookahead safety: correlation at date T uses returns r[T-N+1] ... r[T],
all observed at close of day T. The model predicts rv[T+h], so this is
strictly causal (same convention as log_rv_d using r[T]).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from volforecast.registry import register_feature_layer
from volforecast.utils.paths import ohlcv_cache_dir

logger = logging.getLogger(__name__)

# Z-score window (60 trading days ~= 3 months: captures regime, not noise)
_ZSCORE_WINDOW = 60
# Min number of symbols in panel required to compute meaningful correlation
_MIN_PANEL_SIZE = 5


def _load_panel_returns(cache_dir: Path) -> pd.DataFrame:
    """Load all OHLCV parquets from cache_dir and return wide log-returns DataFrame.

    Returns
    -------
    pd.DataFrame
        Wide DataFrame, index=date, columns=symbol, values=daily log returns.
        Returns empty DataFrame if no files found or none have a 'close' column.
    """
    files = sorted(cache_dir.glob("*.parquet"))
    if not files:
        logger.warning("realized_correlation: no parquets in %s", cache_dir)
        return pd.DataFrame()

    closes = {}
    for f in files:
        # Skip market-wide files (start with underscore by convention)
        if f.stem.startswith("_"):
            continue
        try:
            df = pd.read_parquet(f, columns=["close"])
        except Exception as exc:
            logger.debug("realized_correlation: skip %s (%s)", f.name, exc)
            continue
        if "close" not in df.columns or df["close"].isna().all():
            continue
        closes[f.stem] = df["close"]

    if not closes:
        logger.warning("realized_correlation: no usable close prices in %s", cache_dir)
        return pd.DataFrame()

    wide = pd.concat(closes, axis=1).sort_index()
    wide.columns.name = "symbol"
    log_returns = np.log(wide / wide.shift(1))
    return log_returns


def _rolling_mean_pairwise_corr(
    returns: pd.DataFrame,
    window: int,
    min_pairs: int = 10,
) -> pd.Series:
    """Compute rolling mean of off-diagonal pairwise correlations.

    For each date t, takes the upper-triangular (excluding diagonal)
    entries of corr(returns[t-window+1 : t+1]) and averages them.

    Parameters
    ----------
    returns : pd.DataFrame
        Wide log-returns, index=date, columns=symbol.
    window : int
        Rolling window in trading days.
    min_pairs : int
        Minimum number of valid pairs required; NaN otherwise.

    Returns
    -------
    pd.Series
        Index=date, values=mean off-diagonal correlation (in [-1, 1]).
    """
    if returns.empty or returns.shape[1] < _MIN_PANEL_SIZE:
        return pd.Series(dtype=float, name=f"panel_corr_{window}d")

    n = len(returns)
    dates = returns.index
    out = np.full(n, np.nan, dtype=np.float64)

    # Number of unique pairs in the panel = n*(n-1)/2
    n_sym = returns.shape[1]
    n_pairs_total = n_sym * (n_sym - 1) // 2

    for i in range(window - 1, n):
        window_slice = returns.iloc[i - window + 1 : i + 1]
        # corr requires at least 2 non-NaN observations per column pair
        corr = window_slice.corr(min_periods=max(window // 2, 5))
        if corr.empty:
            continue
        # Upper triangle excluding diagonal
        values = corr.values
        mask = np.triu(np.ones_like(values, dtype=bool), k=1)
        pairs = values[mask]
        valid = pairs[~np.isnan(pairs)]
        if len(valid) >= min_pairs and len(valid) >= n_pairs_total * 0.3:
            out[i] = float(valid.mean())

    return pd.Series(out, index=dates, name=f"panel_corr_{window}d")


@lru_cache(maxsize=1)
def _compute_panel_corr_features(cache_dir_str: str) -> pd.DataFrame:
    """Compute panel correlation features once per cache_dir (process-level cache).

    Returns DataFrame with columns:
    panel_corr_22d, panel_corr_5d, panel_corr_d, panel_corr_z.
    Index is union of dates from all loaded symbols.
    """
    returns = _load_panel_returns(Path(cache_dir_str))
    if returns.empty:
        return pd.DataFrame(
            columns=["panel_corr_22d", "panel_corr_5d", "panel_corr_d", "panel_corr_z"]
        )

    corr_22d = _rolling_mean_pairwise_corr(returns, window=22)
    corr_5d = _rolling_mean_pairwise_corr(returns, window=5)
    corr_change = corr_22d.diff(1).rename("panel_corr_d")
    rolling_mean = corr_22d.rolling(_ZSCORE_WINDOW).mean()
    rolling_std = corr_22d.rolling(_ZSCORE_WINDOW).std()
    corr_z = ((corr_22d - rolling_mean) / rolling_std).rename("panel_corr_z")

    out = pd.concat([corr_22d, corr_5d, corr_change, corr_z], axis=1)
    logger.info(
        "realized_correlation: built panel correlation series, "
        "%d dates, %d symbols, mean corr=%.3f",
        len(out),
        returns.shape[1],
        float(corr_22d.dropna().mean()) if corr_22d.notna().any() else float("nan"),
    )
    return out


@register_feature_layer("realized_correlation")
class RealizedCorrelationLayer:
    """Cross-symbol realized correlation features (market-wide, broadcast per-symbol).

    Loads daily close prices from data/raw/ohlcv/*.parquet (excluding
    underscore-prefixed market-wide files), computes the rolling mean
    off-diagonal correlation of daily log-returns, and broadcasts the
    resulting series onto each symbol's daily_data index.

    This layer is forward-looking in the regime sense: rising correlation
    flags systemic-risk repricing that typically precedes vol spikes.

    Output columns: panel_corr_22d, panel_corr_5d, panel_corr_d, panel_corr_z.
    """

    name = "realized_correlation"

    def compute(
        self,
        daily_data: pd.DataFrame,
        *,
        context: dict | None = None,
    ) -> pd.DataFrame:
        """Reindex pre-computed panel correlation series onto daily_data.index."""
        panel_features = _compute_panel_corr_features(str(ohlcv_cache_dir()))
        if panel_features.empty:
            return pd.DataFrame(index=daily_data.index)

        target_index = daily_data.index
        if not isinstance(target_index, pd.DatetimeIndex):
            target_index = pd.DatetimeIndex(target_index)

        result = panel_features.reindex(target_index)
        result.index = daily_data.index
        return result
