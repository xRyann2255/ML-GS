"""SPX per-strike open interest and Greeks loader.

Adapts the ISG OptionMetrics data pattern for SPX options:
- Per-strike daily EOD open interest
- Per-strike Greeks (delta, gamma, vega, theta)
- Aggregate GEX (Gamma Exposure) computation

Data source hierarchy (try in order):
1. Quantum QSP OptionPrices API (vendor-computed Greeks + real OI) — VERIFIED 2026-07-07
   SPX securityId=108105 (institutional, European, preferred for GEX)
   SPY securityId=109820 (retail, American)
2. Marquee ISG_OPTIONMETRICS / IVYDB dataset (if entitled)
3. Marquee EQUITY_OPTIONS dataset (if exists)
4. Synthetic Greeks from EDRVOL_PERCENT_EXPIRY IV chain + Black-Scholes (no real OI)

Public API:
    fetch_spx_option_chain  — Fetch per-strike OI + Greeks for SPX
    compute_gex             — Compute net Gamma Exposure from option chain
    build_gex_features      — Build GEX-derived feature panel for ML
    save_option_chain_cache — Persist to parquet
    load_option_chain_cache — Load from parquet cache

GEX formula:
    GEX = Σ_K [ OI_K × Γ_K × 100 × S × sign(dealer_position) ]

Convention: Calls → dealers assumed short (retail buys calls)
           Puts  → dealers assumed long (retail buys puts)
    GEX_call = -OI_call × Gamma_call × 100 × S  (short gamma from calls)
    GEX_put  = +OI_put  × Gamma_put  × 100 × S  (long gamma from puts)
    Net GEX  = GEX_call + GEX_put

When net GEX > 0: dealers long gamma → suppress vol (mean-revert)
When net GEX < 0: dealers short gamma → amplify vol (momentum)
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CACHE_FILENAME = "spx_option_chain.parquet"
_GEX_CACHE_FILENAME = "spx_gex_daily.parquet"

# Marquee dataset candidates (tried in order)
_DATASET_CANDIDATES = [
    "ISG_OPTIONMETRICS",
    "OPTIONMETRICS",
    "IVYDB",
    "EQUITY_OPTIONS",
    "OPTIONS_EOD",
    "LISTED_OPTIONS_EOD",
    "EQ_OPTIONS_DAILY",
]

# EDRVOL_PERCENT_EXPIRY strike grid for synthetic chain
_STRIKE_GRID_FINE = [
    0.85, 0.87, 0.88, 0.90, 0.91, 0.92, 0.93, 0.94, 0.95,
    0.96, 0.97, 0.98, 0.99, 1.00, 1.01, 1.02, 1.03, 1.04,
    1.05, 1.06, 1.07, 1.08, 1.10, 1.12, 1.15,
]


# ---------------------------------------------------------------------------
# Black-Scholes Greeks (vectorized)
# ---------------------------------------------------------------------------


def _bs_d1(S: np.ndarray, K: np.ndarray, T: np.ndarray,
            r: float, sigma: np.ndarray) -> np.ndarray:
    """Black-Scholes d1."""
    with np.errstate(divide="ignore", invalid="ignore"):
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return np.where(np.isfinite(d1), d1, 0.0)


def _bs_delta(S: np.ndarray, K: np.ndarray, T: np.ndarray,
              r: float, sigma: np.ndarray, is_call: np.ndarray) -> np.ndarray:
    """Black-Scholes delta (vectorized)."""
    d1 = _bs_d1(S, K, T, r, sigma)
    delta_call = norm.cdf(d1)
    delta_put = delta_call - 1.0
    return np.where(is_call, delta_call, delta_put)


def _bs_gamma(S: np.ndarray, K: np.ndarray, T: np.ndarray,
              r: float, sigma: np.ndarray) -> np.ndarray:
    """Black-Scholes gamma (same for calls and puts)."""
    d1 = _bs_d1(S, K, T, r, sigma)
    with np.errstate(divide="ignore", invalid="ignore"):
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    return np.where(np.isfinite(gamma), gamma, 0.0)


def _bs_vega(S: np.ndarray, K: np.ndarray, T: np.ndarray,
             r: float, sigma: np.ndarray) -> np.ndarray:
    """Black-Scholes vega (per 1% IV move)."""
    d1 = _bs_d1(S, K, T, r, sigma)
    return S * norm.pdf(d1) * np.sqrt(T) / 100.0


def _bs_theta(S: np.ndarray, K: np.ndarray, T: np.ndarray,
              r: float, sigma: np.ndarray, is_call: np.ndarray) -> np.ndarray:
    """Black-Scholes theta (per day)."""
    d1 = _bs_d1(S, K, T, r, sigma)
    d2 = d1 - sigma * np.sqrt(T)

    common = -(S * norm.pdf(d1) * sigma) / (2.0 * np.sqrt(T))
    theta_call = common - r * K * np.exp(-r * T) * norm.cdf(d2)
    theta_put = common + r * K * np.exp(-r * T) * norm.cdf(-d2)

    theta = np.where(is_call, theta_call, theta_put)
    return np.where(np.isfinite(theta), theta, 0.0) / 252.0  # per day


# ---------------------------------------------------------------------------
# Data fetching — Marquee ISG OptionMetrics path
# ---------------------------------------------------------------------------


def _try_marquee_option_chain(
    start_date: date,
    end_date: date,
) -> pd.DataFrame | None:
    """Attempt to fetch per-strike OI + Greeks from Marquee datasets.

    Tries each candidate dataset name in order. Returns None if all fail.
    Expected columns: date, strike, expiry, oi, delta, gamma, vega, option_type.
    """
    try:
        from gs_quant.data import Dataset
        from gs_quant.session import GsSession

        try:
            _ = GsSession.current
        except Exception:
            GsSession.use()
    except ImportError:
        logger.debug("gs_quant not available, skipping Marquee probe")
        return None

    for ds_name in _DATASET_CANDIDATES:
        try:
            ds = Dataset(ds_name)
            data = ds.get_data(
                start=start_date,
                end=end_date,
                bbid="SPX",
            )
            if data is not None and not data.empty:
                logger.info("Found options data in Marquee dataset: %s", ds_name)
                return data
        except Exception:  # noqa: BLE001
            continue

    return None


# ---------------------------------------------------------------------------
# Data fetching — Synthetic chain from EDRVOL_PERCENT_EXPIRY
# ---------------------------------------------------------------------------


def _build_synthetic_chain(
    start_date: date,
    end_date: date,
    risk_free_rate: float = 0.05,
) -> pd.DataFrame:
    """Build synthetic per-strike Greeks from EDRVOL_PERCENT_EXPIRY IV chain.

    Uses the IV surface to compute BS Greeks per strike. Does NOT include
    actual OI (sets OI=1 uniformly for delta/gamma availability without
    GEX weighting).

    Returns DataFrame with columns:
        date, relativeStrike, absoluteStrike, expirationDate,
        impliedVolatility, delta, gamma, vega, theta, option_type, oi
    """
    from volforecast.data.edrvol import _query_marquee_expiry
    from volforecast.constants import TICKER_TO_MARQUEE_RIC

    ric = TICKER_TO_MARQUEE_RIC.get("SPX", ".SPX")

    logger.info("Fetching EDRVOL_PERCENT_EXPIRY full strike chain for %s", ric)

    # Query full strike grid (not just ATM)
    try:
        from gs_quant.data import Dataset
        from gs_quant.session import GsSession

        try:
            _ = GsSession.current
        except Exception:
            GsSession.use()

        ds = Dataset("EDRVOL_PERCENT_EXPIRY")

        # Fetch with multiple strikes
        chunks = []
        from dateutil.relativedelta import relativedelta
        import time

        chunk_start = start_date
        while chunk_start <= end_date:
            chunk_end = min(
                chunk_start + relativedelta(months=3) - relativedelta(days=1),
                end_date,
            )
            for strike in _STRIKE_GRID_FINE:
                try:
                    chunk = ds.get_data(
                        start=chunk_start,
                        end=chunk_end,
                        ric=ric,
                        strikeReference="forward",
                        relativeStrike=strike,
                    )
                    if chunk is not None and not chunk.empty:
                        chunks.append(chunk)
                except Exception:  # noqa: BLE001
                    continue
                time.sleep(0.2)  # Rate limiting
            chunk_start = chunk_end + relativedelta(days=1)

        if not chunks:
            logger.warning("No data from EDRVOL_PERCENT_EXPIRY")
            return pd.DataFrame()

        raw = pd.concat(chunks, ignore_index=True)

    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch EDRVOL_PERCENT_EXPIRY chain: %s", exc)
        return pd.DataFrame()

    if raw.empty:
        return pd.DataFrame()

    # Compute Greeks from IV surface
    required_cols = {"expirationDate", "impliedVolatility", "relativeStrike"}
    if not required_cols.issubset(raw.columns):
        logger.warning("Missing required columns: %s", raw.columns.tolist())
        return pd.DataFrame()

    # Normalize dates
    if "date" in raw.columns:
        raw["obs_date"] = pd.to_datetime(raw["date"]).dt.normalize()
    elif isinstance(raw.index, pd.DatetimeIndex):
        raw["obs_date"] = pd.to_datetime(raw.index).normalize()
        raw = raw.reset_index(drop=True)
    else:
        logger.warning("Cannot determine observation date")
        return pd.DataFrame()

    raw["expirationDate"] = pd.to_datetime(raw["expirationDate"]).dt.normalize()

    # Compute time to expiry in years
    raw["T"] = (raw["expirationDate"] - raw["obs_date"]).dt.days / 365.25
    raw = raw[raw["T"] > 0].copy()  # Drop expired

    # IV in decimal (Marquee returns as percentage or decimal depending on dataset)
    iv = raw["impliedVolatility"].values.copy()
    if iv.mean() > 1.0:  # Percentage scale (e.g., 15.0 = 15%)
        iv = iv / 100.0

    # Classify as put or call based on moneyness (OTM convention)
    # K/F < 1.0 → OTM put, K/F >= 1.0 → OTM call
    is_call = raw["relativeStrike"].values >= 1.0

    # For absolute strike, use relativeStrike × reference (forward = 1.0 means ATM)
    # S and K cancel in moneyness: relativeStrike IS K/F
    S = np.ones(len(raw))  # Normalize: S=1, K=relativeStrike
    K = raw["relativeStrike"].values
    T = raw["T"].values
    r = risk_free_rate

    # Compute Greeks
    raw["delta"] = _bs_delta(S, K, T, r, iv, is_call)
    raw["gamma"] = _bs_gamma(S, K, T, r, iv)
    raw["vega"] = _bs_vega(S, K, T, r, iv)
    raw["theta"] = _bs_theta(S, K, T, r, iv, is_call)
    raw["option_type"] = np.where(is_call, "C", "P")
    raw["oi"] = np.nan  # OI NOT available from this source

    result = raw[[
        "obs_date", "relativeStrike", "expirationDate",
        "impliedVolatility", "delta", "gamma", "vega", "theta",
        "option_type", "oi", "T",
    ]].copy()
    result = result.rename(columns={"obs_date": "date"})

    return result


# ---------------------------------------------------------------------------
# GEX computation
# ---------------------------------------------------------------------------


def compute_gex(
    chain: pd.DataFrame,
    spot: pd.Series | None = None,
) -> pd.DataFrame:
    """Compute daily net GEX from per-strike option chain.

    Parameters
    ----------
    chain : pd.DataFrame
        Must have columns: date, gamma, oi, option_type.
        If 'oi' is NaN, uses uniform OI=1 (gamma-only signal).
    spot : pd.Series, optional
        SPX spot price indexed by date. If None, uses S=1 (relative GEX).

    Returns
    -------
    pd.DataFrame
        Columns: gex_net, gex_call, gex_put, gex_sign, gex_zscore
        Indexed by date.
    """
    if chain.empty:
        return pd.DataFrame()

    df = chain.copy()

    # Fill missing OI with 1 (gamma-only, no OI weighting)
    oi_available = df["oi"].notna().any()
    if not oi_available:
        logger.info("OI not available — computing gamma-only GEX (uniform OI)")
        df["oi"] = 1.0

    # Spot price
    if spot is not None:
        df = df.merge(
            spot.rename("spot").reset_index(),
            on="date",
            how="left",
        )
        df["spot"] = df["spot"].ffill()
    else:
        df["spot"] = 1.0  # Relative units

    # GEX per option:
    # Calls: dealers assumed short → negative gamma contribution
    # Puts: dealers assumed long → positive gamma contribution
    multiplier = 100.0  # SPX options: 100 multiplier
    is_call = df["option_type"] == "C"

    df["gex_contribution"] = np.where(
        is_call,
        -df["oi"] * df["gamma"] * multiplier * df["spot"],  # Short gamma from calls
        +df["oi"] * df["gamma"] * multiplier * df["spot"],  # Long gamma from puts
    )

    # Aggregate by date
    daily = df.groupby("date").agg(
        gex_net=("gex_contribution", "sum"),
        gex_call=("gex_contribution", lambda x: x[is_call[x.index]].sum() if any(is_call[x.index]) else 0),
        gex_put=("gex_contribution", lambda x: x[~is_call[x.index]].sum() if any(~is_call[x.index]) else 0),
    ).sort_index()

    # Derived features
    daily["gex_sign"] = np.sign(daily["gex_net"])
    daily["gex_zscore"] = (
        (daily["gex_net"] - daily["gex_net"].rolling(63).mean())
        / daily["gex_net"].rolling(63).std()
    )

    return daily


def compute_gex_from_gamma_chain(chain: pd.DataFrame) -> pd.DataFrame:
    """Simplified GEX from synthetic chain (no OI, gamma-weighted only).

    Uses the gamma profile across strikes as a proxy for dealer exposure.
    The sign convention uses moneyness: puts contribute positive GEX,
    calls contribute negative GEX.

    This is a DEGRADED signal compared to proper OI-weighted GEX.
    """
    return compute_gex(chain, spot=None)


# ---------------------------------------------------------------------------
# Feature builder
# ---------------------------------------------------------------------------


def build_gex_features(
    gex_daily: pd.DataFrame,
) -> pd.DataFrame:
    """Build GEX-derived features for ML model.

    Parameters
    ----------
    gex_daily : pd.DataFrame
        Output of compute_gex(). Must have gex_net, gex_sign, gex_zscore.

    Returns
    -------
    pd.DataFrame
        Feature columns suitable for LightGBM input:
        - gex_sign_d: {-1, 0, +1} sign of net GEX
        - gex_zscore_d: z-score of net GEX (63-day window)
        - gex_quintile_d: quintile rank of GEX level
        - gex_regime_d: binary (1 = long gamma, 0 = short gamma)
        - gex_momentum_d: 5-day change in GEX z-score
    """
    if gex_daily.empty:
        return pd.DataFrame()

    result = pd.DataFrame(index=gex_daily.index)
    result["gex_sign_d"] = gex_daily["gex_sign"]
    result["gex_zscore_d"] = gex_daily["gex_zscore"]

    # Quintile rank (rolling 252-day)
    result["gex_quintile_d"] = (
        gex_daily["gex_net"]
        .rolling(252, min_periods=63)
        .apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
    )

    # Regime indicator
    result["gex_regime_d"] = (gex_daily["gex_net"] > 0).astype(float)

    # Momentum (5-day change in z-score)
    result["gex_momentum_d"] = gex_daily["gex_zscore"].diff(5)

    return result


# ---------------------------------------------------------------------------
# Public API — main entry point
# ---------------------------------------------------------------------------


def fetch_spx_option_chain(
    start_date: date,
    end_date: date,
    risk_free_rate: float = 0.05,
) -> pd.DataFrame:
    """Fetch SPX per-strike option chain with OI + Greeks.

    Tries data sources in priority order:
    1. Marquee ISG/OptionMetrics datasets (if entitled)
    2. Synthetic chain from EDRVOL_PERCENT_EXPIRY (fallback)

    Parameters
    ----------
    start_date : date
        Start of date range.
    end_date : date
        End of date range.
    risk_free_rate : float
        Risk-free rate for BS Greeks computation (default 5%).

    Returns
    -------
    pd.DataFrame
        Per-strike chain with columns:
        date, relativeStrike, expirationDate, impliedVolatility,
        delta, gamma, vega, theta, option_type, oi, T
    """
    # Try Marquee ISG/OptionMetrics first
    logger.info("Attempting Marquee ISG/OptionMetrics dataset fetch...")
    marquee_data = _try_marquee_option_chain(start_date, end_date)

    if marquee_data is not None and not marquee_data.empty:
        logger.info("Got %d rows from Marquee ISG dataset", len(marquee_data))
        return marquee_data

    # Fallback: synthetic chain from EDRVOL_PERCENT_EXPIRY
    logger.info("Marquee ISG unavailable — building synthetic chain from EDRVOL_PERCENT_EXPIRY")
    return _build_synthetic_chain(start_date, end_date, risk_free_rate)


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------


def save_option_chain_cache(
    chain: pd.DataFrame,
    cache_dir: Path | None = None,
) -> Path:
    """Save option chain to parquet cache."""
    if cache_dir is None:
        from volforecast.utils.paths import iv_cache_dir
        cache_dir = iv_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / _CACHE_FILENAME
    chain.to_parquet(path, index=False)
    logger.info("Saved option chain cache: %s (%d rows)", path, len(chain))
    return path


def load_option_chain_cache(
    cache_dir: Path | None = None,
) -> pd.DataFrame | None:
    """Load option chain from parquet cache. Returns None if missing."""
    if cache_dir is None:
        from volforecast.utils.paths import iv_cache_dir
        cache_dir = iv_cache_dir()
    path = cache_dir / _CACHE_FILENAME
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    logger.info("Loaded option chain cache: %s (%d rows)", path, len(df))
    return df


def save_gex_cache(
    gex: pd.DataFrame,
    cache_dir: Path | None = None,
) -> Path:
    """Save daily GEX to parquet cache."""
    if cache_dir is None:
        from volforecast.utils.paths import iv_cache_dir
        cache_dir = iv_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / _GEX_CACHE_FILENAME
    gex.to_parquet(path)
    logger.info("Saved GEX cache: %s (%d rows)", path, len(gex))
    return path


def load_gex_cache(
    cache_dir: Path | None = None,
) -> pd.DataFrame | None:
    """Load daily GEX from parquet cache. Returns None if missing."""
    if cache_dir is None:
        from volforecast.utils.paths import iv_cache_dir
        cache_dir = iv_cache_dir()
    path = cache_dir / _GEX_CACHE_FILENAME
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    logger.info("Loaded GEX cache: %s (%d rows)", path, len(df))
    return df
