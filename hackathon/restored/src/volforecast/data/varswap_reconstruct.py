"""Reconstruct 0DTE variance swap strike from EDRVOL_PERCENT_EXPIRY option chain.

Fallback path: when EDRVS_EXPIRY is unavailable, we reconstruct the model-free
implied variance from the full IV strike grid using the CBOE VIX discrete formula.

The variance swap strike (model-free implied variance) is:
    σ² = (2/T) Σᵢ (ΔKᵢ/Kᵢ²) × e^(rT) × Q(Kᵢ)

where Q(K) is the OTM option price (put for K < F, call for K ≥ F).

Public API:
    compute_varswap_strike_from_chain  — Compute from arrays of strikes/IVs
    reconstruct_0dte_varswap_strike    — End-to-end: query Marquee + compute
"""

from __future__ import annotations

import logging
import time
from datetime import date

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

_EXPIRY_DATASET_ID = "EDRVOL_PERCENT_EXPIRY"
_CHUNK_MONTHS = 3
_MAX_RETRIES = 3
_RETRY_BACKOFF = (2.0, 4.0, 8.0)

# Strike grid for reconstruction (relative to forward)
_STRIKE_GRID = [
    0.85,
    0.87,
    0.90,
    0.92,
    0.93,
    0.94,
    0.95,
    0.96,
    0.97,
    0.98,
    0.99,
    1.00,
    1.01,
    1.02,
    1.03,
    1.04,
    1.05,
    1.06,
    1.07,
    1.08,
    1.10,
    1.12,
    1.15,
]


def _black_scholes_price(
    K: float,
    F: float,
    T: float,
    sigma: float,
    r: float,
    is_call: bool,
) -> float:
    """Compute Black-Scholes option price given forward.

    Parameters
    ----------
    K : float
        Strike price (absolute or relative — just be consistent with F).
    F : float
        Forward price.
    T : float
        Time to expiry in years.
    sigma : float
        Implied volatility as decimal (e.g., 0.20 for 20%).
    r : float
        Risk-free rate (annualized decimal).
    is_call : bool
        True for call, False for put.

    Returns
    -------
    float
        Option price.
    """
    from scipy.stats import norm

    if T <= 0 or sigma <= 0:
        return 0.0

    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    discount = np.exp(-r * T)
    if is_call:
        return discount * (F * norm.cdf(d1) - K * norm.cdf(d2))
    else:
        return discount * (K * norm.cdf(-d2) - F * norm.cdf(-d1))


def compute_varswap_strike_from_chain(
    strikes_rel: np.ndarray,
    ivs: np.ndarray,
    T: float,
    forward: float = 1.0,
    r: float = 0.05,
) -> float | None:
    """Compute model-free implied variance from a discrete option chain.

    Implements the CBOE VIX discrete formula:
        σ² = (2/T) Σᵢ (ΔKᵢ/Kᵢ²) × e^(rT) × Q(Kᵢ)

    where Q(Kᵢ) is the OTM option price:
    - Put for Kᵢ < F (forward)
    - Call for Kᵢ ≥ F (forward)

    Parameters
    ----------
    strikes_rel : np.ndarray
        Relative strikes (e.g., 0.95 = 95% of forward). Must be sorted.
    ivs : np.ndarray
        Implied volatilities in percentage points (e.g., 20.0 = 20%).
    T : float
        Time to expiry in years (e.g., 1/252 for 1 day).
    forward : float
        Forward price level (default 1.0 for relative strikes).
    r : float
        Risk-free rate (annualized decimal).

    Returns
    -------
    float or None
        Variance swap strike as annualized vol in percentage points.
        Returns None if insufficient data.
    """
    if T <= 0:
        return None

    strikes_rel = np.asarray(strikes_rel, dtype=np.float64)
    ivs = np.asarray(ivs, dtype=np.float64)

    # Filter out NaN/invalid
    valid = ~(np.isnan(strikes_rel) | np.isnan(ivs) | (ivs <= 0))
    strikes_rel = strikes_rel[valid]
    ivs = ivs[valid]

    if len(strikes_rel) < 3:
        return None

    # Sort by strike
    sort_idx = np.argsort(strikes_rel)
    strikes_rel = strikes_rel[sort_idx]
    ivs = ivs[sort_idx]

    # Convert relative strikes to absolute
    K_abs = strikes_rel * forward

    # Compute OTM option prices using Black-Scholes
    prices = np.zeros(len(K_abs))
    for i, (K, iv_pct) in enumerate(zip(K_abs, ivs)):
        sigma = iv_pct / 100.0  # Convert to decimal
        is_call = K >= forward
        prices[i] = _black_scholes_price(K, forward, T, sigma, r, is_call)

    # Compute ΔK for each strike (midpoint rule)
    delta_K = np.zeros(len(K_abs))
    for i in range(len(K_abs)):
        if i == 0:
            delta_K[i] = K_abs[1] - K_abs[0]
        elif i == len(K_abs) - 1:
            delta_K[i] = K_abs[-1] - K_abs[-2]
        else:
            delta_K[i] = (K_abs[i + 1] - K_abs[i - 1]) / 2.0

    # CBOE formula: σ² = (2/T) Σ (ΔK/K²) × e^(rT) × Q(K)
    variance = (2.0 / T) * np.sum(delta_K / K_abs**2 * np.exp(r * T) * prices)

    # Subtract the forward correction term: -(1/T)(F/K0 - 1)²
    # K0 = first strike below forward (ATM pivot)
    k0_idx = np.searchsorted(K_abs, forward) - 1
    k0_idx = max(0, min(k0_idx, len(K_abs) - 1))
    K0 = K_abs[k0_idx]
    correction = (1.0 / T) * (forward / K0 - 1.0) ** 2
    variance = variance - correction

    if variance <= 0:
        return None

    # Convert to annualized vol in percentage points
    vol_pct = np.sqrt(variance) * 100.0
    return float(vol_pct)


# ---------------------------------------------------------------------------
# Marquee query helpers for multi-strike chain
# ---------------------------------------------------------------------------


def _query_expiry_chain(
    start_date: date,
    end_date: date,
    strikes: list[float] | None = None,
) -> pd.DataFrame:
    """Query EDRVOL_PERCENT_EXPIRY for multiple strikes (full chain).

    Returns raw DataFrame with columns: date, expirationDate,
    relativeStrike, impliedVolatility, strikeReference.
    """
    from volforecast.data.edrvol import _ensure_expiry_session

    _ensure_expiry_session()

    try:
        from gs_quant.data import Dataset
    except ImportError:
        raise ConnectionError("gs_quant not available.")

    if strikes is None:
        strikes = _STRIKE_GRID

    ds = Dataset(_EXPIRY_DATASET_ID)
    all_chunks: list[pd.DataFrame] = []

    for strike in strikes:
        # Chunk long ranges
        chunk_start = start_date
        while chunk_start <= end_date:
            chunk_end = min(
                chunk_start + relativedelta(months=_CHUNK_MONTHS) - relativedelta(days=1),
                end_date,
            )
            for attempt in range(_MAX_RETRIES):
                try:
                    chunk = ds.get_data(
                        start=chunk_start,
                        end=chunk_end,
                        ric=".SPX",
                        strikeReference="forward",
                        relativeStrike=strike,
                    )
                    if chunk is not None and not chunk.empty:
                        all_chunks.append(chunk)
                    break
                except Exception:  # noqa: BLE001
                    if attempt < _MAX_RETRIES - 1:
                        time.sleep(_RETRY_BACKOFF[attempt])
                    else:
                        logger.debug(
                            "Failed strike=%.2f chunk %s-%s",
                            strike,
                            chunk_start,
                            chunk_end,
                        )
            chunk_start = chunk_end + relativedelta(days=1)

    if not all_chunks:
        return pd.DataFrame()

    return pd.concat(all_chunks, ignore_index=True)


def reconstruct_0dte_varswap_strike(
    start_date: date,
    end_date: date,
    r: float = 0.05,
) -> pd.Series:
    """Reconstruct 0DTE variance swap strike from EDRVOL_PERCENT_EXPIRY chain.

    Queries the full strike grid from Marquee, then applies the CBOE VIX
    discrete formula for each observation date to compute model-free
    implied variance.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).
    r : float
        Risk-free rate assumption (annualized decimal).

    Returns
    -------
    pd.Series
        Named 'iv_vs_0dte_reconstructed', indexed by observation date.
        Values in vol points (annualized %). Empty series on failure.
    """
    col_name = "iv_vs_0dte_reconstructed"
    empty = pd.Series(dtype=float, name=col_name)
    empty.index.name = "date"

    try:
        raw = _query_expiry_chain(start_date, end_date)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to query option chain for reconstruction: %s", exc)
        return empty

    if raw is None or raw.empty:
        return empty

    # Normalize dates
    if "date" in raw.columns:
        raw["obs_date"] = pd.to_datetime(raw["date"]).dt.normalize()
    elif isinstance(raw.index, pd.DatetimeIndex):
        raw["obs_date"] = raw.index.normalize()
    else:
        return empty

    if "expirationDate" in raw.columns:
        raw["expirationDate"] = pd.to_datetime(raw["expirationDate"]).dt.normalize()

    # For each observation date, select 0DTE chain and compute variance
    results: dict[pd.Timestamp, float] = {}
    T = 1.0 / 252.0  # 0DTE ≈ 1 trading day

    for obs_date, group in raw.groupby("obs_date"):
        # Select nearest expiry (prefer same-day for 0DTE)
        if "expirationDate" in group.columns:
            same_day = group[group["expirationDate"] == obs_date]
            if not same_day.empty:
                chain = same_day
            else:
                future = group[group["expirationDate"] > obs_date]
                if future.empty:
                    continue
                nearest_exp = future["expirationDate"].min()
                chain = future[future["expirationDate"] == nearest_exp]
        else:
            chain = group

        if "relativeStrike" not in chain.columns or "impliedVolatility" not in chain.columns:
            continue

        strikes = chain["relativeStrike"].values
        ivs = chain["impliedVolatility"].values

        vol = compute_varswap_strike_from_chain(strikes, ivs, T, forward=1.0, r=r)
        if vol is not None and not np.isnan(vol):
            results[obs_date] = vol

    if not results:
        return empty

    series = pd.Series(results, name=col_name)
    series.index = pd.DatetimeIndex(series.index)
    series.index.name = "date"
    return series.sort_index()
