"""Graph adjacency builder for GNN volatility model.

Computes rolling realized correlation matrices and converts them to
PyTorch Geometric sparse edge_index + edge_weight tensors.

Causal guarantee: correlation at date T uses returns [T-window+1, ..., T]
only (same convention as realized_correlation feature layer).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import torch

logger = logging.getLogger(__name__)

# Module-level cache: (date_ns, window, threshold) → (edge_index, edge_weight)
_ADJACENCY_CACHE: dict[tuple[int, int, float], tuple[torch.Tensor, torch.Tensor]] = {}


def clear_adjacency_cache() -> None:
    """Clear the adjacency cache (useful between experiments)."""
    _ADJACENCY_CACHE.clear()


def build_adjacency(
    panel_returns: pd.DataFrame,
    date: pd.Timestamp,
    window: int = 60,
    threshold: float = 0.3,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Build sparse adjacency for a single date from rolling correlation.

    Results are cached in-memory keyed by (date, window, threshold).

    Parameters
    ----------
    panel_returns : pd.DataFrame
        Wide DataFrame, index=dates, columns=symbols, values=daily log returns.
    date : pd.Timestamp
        Target date. Correlation uses returns [date-window+1, ..., date].
    window : int
        Rolling window in trading days for correlation estimation.
    threshold : float
        Minimum |correlation| to include an edge.

    Returns
    -------
    edge_index : torch.Tensor, shape (2, E)
        COO-format edge indices (undirected: both (i,j) and (j,i) included).
    edge_weight : torch.Tensor, shape (E,)
        Absolute correlation values for each edge.
    """
    # Cache lookup — use date as nanoseconds int for hashability
    cache_key = (date.value, window, threshold)
    cached = _ADJACENCY_CACHE.get(cache_key)
    if cached is not None:
        return cached

    # Find the date position in the index
    date_loc = panel_returns.index.get_loc(date)
    if isinstance(date_loc, slice):
        date_loc = date_loc.stop - 1

    start = max(0, date_loc - window + 1)
    window_data = panel_returns.iloc[start : date_loc + 1]

    # Require at least half the window for meaningful correlation
    min_periods = max(window // 2, 5)
    corr_matrix = window_data.corr(min_periods=min_periods)

    if corr_matrix.empty:
        return torch.zeros(2, 0, dtype=torch.long), torch.zeros(0, dtype=torch.float32)

    n = corr_matrix.shape[0]
    values = corr_matrix.values

    # Extract edges above threshold (excluding diagonal / self-loops)
    src_list = []
    dst_list = []
    weight_list = []

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            val = values[i, j]
            if np.isnan(val):
                continue
            if abs(val) >= threshold:
                src_list.append(i)
                dst_list.append(j)
                weight_list.append(abs(val))

    if not src_list:
        result = (torch.zeros(2, 0, dtype=torch.long), torch.zeros(0, dtype=torch.float32))
        _ADJACENCY_CACHE[cache_key] = result
        return result

    edge_index = torch.tensor([src_list, dst_list], dtype=torch.long)
    edge_weight = torch.tensor(weight_list, dtype=torch.float32)

    result = (edge_index, edge_weight)
    _ADJACENCY_CACHE[cache_key] = result
    return result


def build_adjacency_series(
    panel_returns: pd.DataFrame,
    dates: pd.DatetimeIndex | list[pd.Timestamp],
    window: int = 60,
    threshold: float = 0.3,
) -> dict[pd.Timestamp, tuple[torch.Tensor, torch.Tensor]]:
    """Build adjacency graphs for a series of dates.

    Efficiently computes rolling correlation for each date in the series.

    Parameters
    ----------
    panel_returns : pd.DataFrame
        Wide DataFrame, index=dates, columns=symbols, values=daily log returns.
    dates : sequence of Timestamps
        Dates for which to compute adjacency. Must be subset of panel_returns.index.
    window : int
        Rolling window for correlation.
    threshold : float
        Minimum |correlation| for edge inclusion.

    Returns
    -------
    dict mapping date → (edge_index, edge_weight)
        Dates not in panel_returns or with insufficient history return empty tensors.
    """
    result = {}
    n_symbols = panel_returns.shape[1]

    for date in dates:
        if date not in panel_returns.index:
            result[date] = (
                torch.zeros(2, 0, dtype=torch.long),
                torch.zeros(0, dtype=torch.float32),
            )
            continue

        edge_index, edge_weight = build_adjacency(
            panel_returns, date, window=window, threshold=threshold
        )
        result[date] = (edge_index, edge_weight)

    return result


def panel_returns_from_ohlcv(ohlcv_cache_dir) -> pd.DataFrame:
    """Load panel log-returns from OHLCV cache (same logic as realized_correlation layer).

    Parameters
    ----------
    ohlcv_cache_dir : Path
        Directory containing per-symbol OHLCV parquets.

    Returns
    -------
    pd.DataFrame
        Wide DataFrame, index=date, columns=symbol, values=daily log returns.
    """
    from pathlib import Path

    cache_dir = Path(ohlcv_cache_dir)
    files = sorted(cache_dir.glob("*.parquet"))
    if not files:
        return pd.DataFrame()

    closes = {}
    for f in files:
        if f.stem.startswith("_"):
            continue
        try:
            df = pd.read_parquet(f, columns=["close"])
        except Exception:
            continue
        if "close" not in df.columns or df["close"].isna().all():
            continue
        closes[f.stem] = df["close"]

    if not closes:
        return pd.DataFrame()

    wide = pd.concat(closes, axis=1).sort_index()
    wide.columns.name = "symbol"
    return np.log(wide / wide.shift(1))
