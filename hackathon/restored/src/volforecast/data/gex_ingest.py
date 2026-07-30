"""QSP API client for GEX (Gamma Exposure) ingestion.

Fetches option chain data from the Quantum Service Portal (QSP) API,
computes per-strike and aggregate Gamma Exposure, and manages a parquet cache.

Public API:
    get_qsp_session           — Create authenticated session via GSSSO/Kerberos
    parse_option_prices_response — Extract contracts from nested QSP JSON
    fetch_spot_price          — Get underlying close from SecurityTimeseries
    fetch_option_chain        — Fetch full option chain with scrollId pagination
    aggregate_gex             — Compute net GEX from raw contract list
    fetch_gex_daily           — Orchestrate spot + chain + aggregation for one date
    load_gex_cache            — Load cached GEX DataFrame from parquet
    save_gex_cache            — Atomically write GEX DataFrame to parquet

GEX formula (dealer perspective):
    GEX_call = -OI × gamma × contractSize × spot × 0.01  (dealer short gamma)
    GEX_put  = +OI × gamma × contractSize × spot × 0.01  (dealer long gamma)
    Net GEX  = GEX_call + GEX_put
"""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://pwm.qsp.url.gs.com:7070/quantumServicePortal/rest/api"

_CACHE_FILENAME = "spx_gex_daily.parquet"

# Maximum pages to follow during scrollId pagination
_MAX_PAGES = 100


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def get_qsp_session() -> requests.Session:
    """Create an authenticated requests.Session with GSSSO cookie for QSP API.

    Uses ``gs_quant.session.GsSession.use()`` — the same auth mechanism as every
    other ingestion command in this project (TSDB, Marquee, Chunk Store) — to
    perform the full multi-step Kerberos/SPNEGO handshake, then extracts the
    resulting ``GSSSO`` cookie and pins it to a plain ``requests.Session`` for
    QSP API calls.

    Note: A direct Kerberos handshake against QSP or ``authn.web.gs.com`` does
    NOT work (they return 401 without a ``WWW-Authenticate: Negotiate`` header
    or 404 respectively). The GSSSO cookie must be minted via GsSession's
    internal auth flow.

    Raises:
        RuntimeError: If GsSession auth fails or no GSSSO cookie is available.
    """
    try:
        from gs_quant.session import GsSession
    except ImportError as exc:
        raise RuntimeError(
            "gs_quant not available. Run on GS desktop with active session."
        ) from exc

    try:
        GsSession.use()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"GsSession authentication failed: {exc}. "
            "Ensure Kerberos ticket is valid (kinit)."
        ) from exc

    # Extract the GSSSO cookie from the internal requests.Session used by GsSession
    gs_session = GsSession.current
    inner_session = getattr(gs_session, "_session", None)
    if inner_session is None or not hasattr(inner_session, "cookies"):
        raise RuntimeError(
            "GsSession did not expose an underlying requests session with cookies."
        )

    cookie_value = None
    for cookie in inner_session.cookies:
        if cookie.name == "GSSSO":
            cookie_value = cookie.value
            break

    if not cookie_value:
        raise RuntimeError(
            "GSSSO cookie not found in GsSession. "
            "Ensure Kerberos ticket is valid (kinit)."
        )

    session = requests.Session()
    session.verify = False
    session.cookies.set("GSSSO", cookie_value, domain=".gs.com")
    logger.info("QSP session created with GSSSO cookie (via GsSession)")
    return session


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def parse_option_prices_response(response: dict) -> list[dict]:
    """Extract flat list of option contracts from QSP OptionPrices response.

    Response structure:
        {"optionsPriceData": [{"data": [{"price": [...contracts...]}]}], "scrollId": ...}

    Returns:
        List of contract dicts with gamma, openInterest, strike, callPut, etc.
    """
    contracts: list[dict] = []
    for group in response.get("optionsPriceData", []):
        for data_item in group.get("data", []):
            contracts.extend(data_item.get("price", []))
    return contracts


# ---------------------------------------------------------------------------
# API fetchers
# ---------------------------------------------------------------------------


def fetch_spot_price(
    session: requests.Session,
    security_id: str,
    query_date: date,
) -> float | None:
    """Fetch underlying close price from QSP SecurityTimeseries.

    Returns:
        Close price as float, or None if unavailable.
    """
    url = f"{BASE_URL}/OptionMetricsSecurityTimeseries/4"
    date_str = query_date.isoformat()
    params = {
        "productKeys": security_id,
        "productType": "securityId",
        "fromDate": date_str,
        "toDate": date_str,
    }

    resp = session.get(url, params=params, timeout=60)
    if resp.status_code != 200:
        logger.warning("Spot price fetch failed: HTTP %d", resp.status_code)
        return None

    data = resp.json()
    for sec in data.get("securities", []):
        for d in sec.get("data", []):
            prices = d.get("securityPrices", [])
            if prices:
                return prices[0].get("closePrice")
    return None


def fetch_option_chain(
    session: requests.Session,
    security_id: str,
    query_date: date,
) -> list[dict]:
    """Fetch full option chain with scrollId pagination.

    Follows scrollId across pages until None/empty or duplicate ID detected.

    Returns:
        Flat list of all option contract dicts.
    """
    url = f"{BASE_URL}/OptionPrices/4"
    date_str = query_date.isoformat()
    params = {
        "productKeys": security_id,
        "productType": "securityId",
        "fromDate": date_str,
        "toDate": date_str,
    }

    resp = session.get(url, params=params, timeout=120)
    if resp.status_code != 200:
        logger.warning("Option chain fetch failed: HTTP %d", resp.status_code)
        return []

    data = resp.json()
    contracts = parse_option_prices_response(data)
    scroll_id = data.get("scrollId")

    prev_scroll_id = None
    page = 1
    while scroll_id and page < _MAX_PAGES:
        if scroll_id == prev_scroll_id:
            logger.warning("Duplicate scrollId detected, stopping pagination")
            break
        prev_scroll_id = scroll_id
        page += 1

        page_params = {**params, "scrollId": scroll_id}
        resp = session.get(url, params=page_params, timeout=120)
        if resp.status_code != 200:
            break

        page_data = resp.json()
        page_contracts = parse_option_prices_response(page_data)
        if not page_contracts:
            break

        contracts.extend(page_contracts)
        new_scroll_id = page_data.get("scrollId")
        if new_scroll_id == scroll_id:
            break
        scroll_id = new_scroll_id

    logger.info("Fetched %d contracts across %d page(s)", len(contracts), page)
    return contracts


# ---------------------------------------------------------------------------
# GEX aggregation
# ---------------------------------------------------------------------------


def aggregate_gex(contracts: list[dict], spot: float) -> dict:
    """Compute aggregate Gamma Exposure from raw option contracts.

    Filters out invalid contracts (gamma == -99.99 or None, OI == 0).
    Converts strikes from milli-dollars (÷1000) but uses spot for GEX calc.

    GEX formula (dealer perspective):
        call: gex = -gamma × OI × contractSize × spot × 0.01
        put:  gex = +gamma × OI × contractSize × spot × 0.01

    Returns:
        Dict with gex_net, gex_call, gex_put, gex_sign, spot,
        n_valid_contracts, oi_total, oi_pcr.
    """
    gex_call = 0.0
    gex_put = 0.0
    n_valid = 0
    oi_call = 0
    oi_put = 0

    for c in contracts:
        gamma = c.get("gamma")
        oi = c.get("openInterest", 0)

        # Filter invalid
        if gamma is None or gamma == -99.99:
            continue
        if oi <= 0:
            continue

        n_valid += 1
        contract_size = c.get("contractSize", 100)
        cp = c.get("callPut", "")

        # GEX per contract group
        gex_contribution = gamma * oi * contract_size * spot * 0.01

        if cp == "C":
            gex_call += -gex_contribution  # dealer short gamma on calls
            oi_call += oi
        elif cp == "P":
            gex_put += gex_contribution  # dealer long gamma on puts
            oi_put += oi

    gex_net = gex_call + gex_put
    gex_sign = 1 if gex_net > 0 else (-1 if gex_net < 0 else 0)
    oi_total = oi_call + oi_put
    oi_pcr = (oi_put / oi_call) if oi_call > 0 else 0.0

    return {
        "gex_net": gex_net,
        "gex_call": gex_call,
        "gex_put": gex_put,
        "gex_sign": gex_sign,
        "spot": spot,
        "n_valid_contracts": n_valid,
        "oi_total": oi_total,
        "oi_pcr": oi_pcr,
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def fetch_gex_daily(
    query_date: date,
    security_id: str,
    session: requests.Session,
) -> dict | None:
    """Fetch and compute GEX for a single date.

    Orchestrates spot price fetch, option chain fetch, and GEX aggregation.

    Returns:
        Aggregated GEX dict with 'date' field added, or None on failure.
    """
    spot = fetch_spot_price(session, security_id, query_date)
    if spot is None:
        logger.warning("No spot price for %s, skipping", query_date)
        return None

    contracts = fetch_option_chain(session, security_id, query_date)
    if not contracts:
        logger.warning("No option contracts for %s, skipping", query_date)
        return None

    result = aggregate_gex(contracts, spot)
    result["date"] = query_date
    return result


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------


def load_gex_cache(cache_dir: Path | None = None) -> pd.DataFrame:
    """Load cached GEX data from parquet.

    Returns:
        DataFrame with GEX history, or empty DataFrame if cache doesn't exist.
    """
    if cache_dir is None:
        from volforecast.utils.paths import data_path
        cache_dir = data_path("raw/options_oi")

    cache_file = cache_dir / _CACHE_FILENAME
    if not cache_file.exists():
        return pd.DataFrame()

    return pd.read_parquet(cache_file)


def save_gex_cache(df: pd.DataFrame, cache_dir: Path | None = None) -> None:
    """Atomically save GEX DataFrame to parquet cache.

    Uses tempfile + os.replace for atomic writes (no partial files on crash).
    """
    if cache_dir is None:
        from volforecast.utils.paths import data_path
        cache_dir = data_path("raw/options_oi")

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / _CACHE_FILENAME

    # Atomic write: write to temp, then rename
    fd, tmp_path = tempfile.mkstemp(
        suffix=".parquet", dir=str(cache_dir)
    )
    try:
        os.close(fd)
        df.to_parquet(tmp_path, index=False)
        os.replace(tmp_path, str(cache_file))
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
