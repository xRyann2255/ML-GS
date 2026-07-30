"""SPXAllDayVols mark Kvar extraction.

Queries SPXAllDayVols vol marks from ChunkStore at 09:10 ET for the
exact strikes in each day's variance swap strip (from output.json),
then computes mark Kvar using the CBOE discrete variance swap formula.

This gives a "morning mark Kvar" — the fair variance swap level at signal
decision time (09:10 ET), without execution slippage.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from volforecast.constants import TZ
from volforecast.data.gsvivs_kvar import (
    _find_forward_for_day,
    _T_0DTE_DEFAULT,
    compute_kvar_from_legs,
    parse_day_opening_legs,
)
from volforecast.utils.paths import allday_vols_cache_path, data_path

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────

ALLDAY_CHUNKDB = "_CFG Arctic NYC Eq Flow::nyc_eq_vol_vmrk"
ALLDAY_SYMBOL = "SPXAllDayVols"
SNAPSHOT_HOUR = 9
SNAPSHOT_MINUTE = 10
SNAPSHOT_BUFFER_SECONDS = 30


# ── Black-Scholes pricing ─────────────────────────────────────────────────


def bs_price(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str
) -> float:
    """Black-Scholes option price from implied volatility.

    Parameters
    ----------
    S : float
        Underlying (forward) price.
    K : float
        Strike price.
    T : float
        Time to expiry in years.
    r : float
        Risk-free rate (annualized, continuous compounding).
    sigma : float
        Implied volatility (annualized, decimal — e.g. 0.20 for 20%).
    option_type : str
        "Call" or "Put".

    Returns
    -------
    float
        Black-Scholes option price.
    """
    if sigma <= 0 or T <= 0:
        # Intrinsic value only
        if option_type == "Call":
            return max(S - K * np.exp(-r * T), 0.0)
        return max(K * np.exp(-r * T) - S, 0.0)

    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    if option_type == "Call":
        return float(S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))
    else:  # Put
        return float(K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1))


# ── Strike map extraction from output.json ────────────────────────────────


def extract_daily_strike_map(
    json_path: str | Path | None = None,
) -> dict[date, dict]:
    """Extract per-day strike lists and forward prices from output.json.

    Returns dict mapping trade_date -> {
        "strikes": [{"strike": K, "option_type": "Put"/"Call"}, ...],
        "forward": float,
    }

    Uses parse_day_opening_legs for strike extraction and
    _find_forward_for_day for forward price inference.

    Parameters
    ----------
    json_path : str, Path, or None
        Path to output.json. Defaults to data/external/output.json.

    Returns
    -------
    dict[date, dict]
        Keyed by trade_date (datetime.date). Each value has:
        - "strikes": list of {"strike": float, "option_type": str}
        - "forward": float
    """
    if json_path is None:
        json_path = data_path("external", "output.json")
    json_path = Path(json_path)

    with open(json_path) as f:
        data = json.load(f)

    result: dict[date, dict] = {}

    for day_record in data:
        trade_date_str = day_record.get("date")
        if not trade_date_str:
            continue

        value = day_record.get("value", {})
        risks = value.get("risks for date", [])
        if not risks:
            continue

        legs = parse_day_opening_legs(risks)
        if len(legs) < 3:
            logger.debug(
                "Day %s: only %d opening legs, skipping strike map",
                trade_date_str,
                len(legs),
            )
            continue

        forward = _find_forward_for_day(risks, trade_date_str, legs=legs)
        if forward is None:
            logger.warning("Day %s: no forward found, skipping", trade_date_str)
            continue

        trade_date_obj = date.fromisoformat(trade_date_str)
        strikes = [
            {"strike": leg["strike"], "option_type": leg["option_type"]} for leg in legs
        ]

        result[trade_date_obj] = {
            "strikes": strikes,
            "forward": forward,
        }

    logger.info("Extracted strike maps for %d days from %s", len(result), json_path.name)
    return result


# ── ChunkStore fetch ──────────────────────────────────────────────────────


def fetch_allday_vols_snapshot(
    trade_date: date, strikes: list[dict] | None = None
) -> pd.DataFrame | None:
    """Query SPXAllDayVols marks from ChunkStore at 09:10 ET ± 30s.

    Parameters
    ----------
    trade_date : date
        The trading day to query.
    strikes : list[dict] or None
        Optional list of {"strike": K, "option_type": str} to filter.
        If None, returns all available strikes for the snapshot window.

    Returns
    -------
    pd.DataFrame or None
        DataFrame of per-strike IV marks at 09:10 ET, or None if
        the query fails or returns no data. Schema is data-dependent
        since this is a vol mark surface with potentially unknown format.
    """
    try:
        from pytickclient import query as ptc_query
    except ImportError:
        logger.error(
            "pytickclient not available — cannot fetch SPXAllDayVols. "
            "Run on a GS network machine with pytickclient installed."
        )
        return None

    # Build tz-aware snapshot window: 09:09:30 to 09:10:30 ET
    snapshot_time = datetime(
        trade_date.year,
        trade_date.month,
        trade_date.day,
        SNAPSHOT_HOUR,
        SNAPSHOT_MINUTE,
        0,
        tzinfo=TZ,
    )
    st = snapshot_time - timedelta(seconds=SNAPSHOT_BUFFER_SECONDS)
    et = snapshot_time + timedelta(seconds=SNAPSHOT_BUFFER_SECONDS)

    logger.info(
        "Fetching %s for %s [%s → %s]",
        ALLDAY_SYMBOL,
        trade_date.isoformat(),
        st.strftime("%H:%M:%S"),
        et.strftime("%H:%M:%S"),
    )

    try:
        raw = ptc_query.chunk_query([ALLDAY_SYMBOL], st, et, ALLDAY_CHUNKDB)
    except Exception:
        logger.exception("ChunkStore query failed for %s on %s", ALLDAY_SYMBOL, trade_date)
        return None

    if raw is None:
        logger.warning("No data returned for %s on %s", ALLDAY_SYMBOL, trade_date)
        return None

    df = pd.DataFrame(raw)
    if df.empty:
        logger.warning("No data returned for %s on %s", ALLDAY_SYMBOL, trade_date)
        return None

    logger.info(
        "Got %d rows, columns: %s", len(df), list(df.columns)
    )

    return df


# ── Mark Kvar computation ─────────────────────────────────────────────────


def compute_mark_kvar(
    strike_ivs: list[dict],
    forward: float,
    T: float = _T_0DTE_DEFAULT,
    r: float = 0.05,
) -> dict | None:
    """Compute mark Kvar from IV marks using Black-Scholes + CBOE formula.

    Converts per-strike IVs to option prices via Black-Scholes, then
    feeds them into compute_kvar_from_legs (the same CBOE discrete
    variance swap formula used for execution Kvar).

    Parameters
    ----------
    strike_ivs : list[dict]
        Each dict: {"strike": K, "option_type": "Put"/"Call", "iv": sigma}.
        IV should be in decimal form (e.g. 0.20 for 20%).
    forward : float
        Forward price for the underlying.
    T : float
        Time to expiry in years (calendar-year convention).
    r : float
        Risk-free rate (annualized).

    Returns
    -------
    dict or None
        Same structure as compute_kvar_from_legs output, plus:
        - "source": "allday_vols_mark"
        - "n_iv_strikes": number of strikes with valid IVs
        Returns None if insufficient data or computation fails.
    """
    if not strike_ivs:
        return None

    # Convert IVs to BS prices and build legs for the CBOE formula
    legs: list[dict] = []
    for entry in strike_ivs:
        K = entry["strike"]
        option_type = entry["option_type"]
        iv = entry.get("iv")

        if iv is None or iv <= 0:
            logger.debug("Skipping strike %.1f: invalid IV=%s", K, iv)
            continue

        price = bs_price(S=forward, K=K, T=T, r=r, sigma=iv, option_type=option_type)
        if price <= 0:
            logger.debug("Skipping strike %.1f: BS price=%.6f <= 0", K, price)
            continue

        legs.append({
            "strike": K,
            "option_type": option_type,
            "exec_price": price,
            "quantity": -1.0,  # Synthetic short for variance swap replication
        })

    if len(legs) < 3:
        logger.warning(
            "Only %d valid legs after IV→price conversion (need ≥3)", len(legs)
        )
        return None

    result = compute_kvar_from_legs(legs, forward, T=T, r=r, tc_cash=0.0)
    if result is None:
        return None

    result["source"] = "allday_vols_mark"
    result["n_iv_strikes"] = len(legs)
    return result


# ── Cache I/O ─────────────────────────────────────────────────────────────


def load_allday_cache() -> pd.DataFrame | None:
    """Load cached SPX AllDay Vols mark Kvar parquet if it exists.

    Returns
    -------
    pd.DataFrame or None
        Cached DataFrame with trade_date index and mark Kvar columns,
        or None if cache file doesn't exist.
    """
    path = allday_vols_cache_path()
    if not path.exists():
        logger.debug("AllDay Vols cache not found at %s", path)
        return None

    df = pd.read_parquet(path)
    logger.info("Loaded AllDay Vols cache: %d rows from %s", len(df), path)
    return df


def save_allday_cache(df: pd.DataFrame) -> Path:
    """Save mark Kvar DataFrame to the cache parquet.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with mark Kvar results (typically trade_date indexed).

    Returns
    -------
    Path
        The path where the cache was saved.
    """
    path = allday_vols_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=True)
    logger.info("Saved AllDay Vols cache: %d rows → %s", len(df), path)
    return path
