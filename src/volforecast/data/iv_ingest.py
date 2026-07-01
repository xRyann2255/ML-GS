"""IV surface ingestion from Marquee EDRVOL_PERCENT.

Bulk-fetches the SPX implied volatility surface and VIX, assembles into
a daily panel suitable for Layer 2 feature computation.

Public API:
    ingest_iv_surface — Fetch and assemble raw IV panel
    save_iv_cache     — Persist panel to parquet
    load_iv_cache     — Load cached panel (or None if missing)
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from volforecast.utils.paths import iv_cache_dir

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TENORS = ["1m", "3m"]
_ATM_STRIKE = 1.0
_ATM_STRIKE_REF = "forward"
_PUT_25D_STRIKE = 0.75  # 75-delta call ≈ 25-delta put (call-delta convention)
_CALL_25D_STRIKE = 0.25  # 25-delta call
_WING_STRIKE_REF = "delta"  # Both wings use delta strikeReference

_RAW_CACHE_FILENAME = "iv_surface_spx.parquet"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fetch_raw_iv_surface(
    start_date: date, end_date: date, on_chunk: object = None
) -> pd.DataFrame:
    """Fetch filtered IV surface from Marquee (chunked internally).

    Only requests the tenors and strikes actually needed for Layer 2 features,
    reducing transferred data by ~92% vs fetching the full surface.
    """
    from volforecast.data.marquee import _query_erdvol

    return _query_erdvol(
        start_date,
        end_date,
        on_chunk=on_chunk,
        tenor=_TENORS,
        relativeStrike=[_ATM_STRIKE, _PUT_25D_STRIKE, _CALL_25D_STRIKE],
    )


def _fetch_vix_daily(start_date: date, end_date: date) -> pd.Series:
    """Fetch VIX daily close from TSDB.

    Returns pd.Series indexed by date.
    """
    try:
        from gs_quant_internal.tsdb import TSDBSymbol

        data = TSDBSymbol("eqpad_.VIX@close").get_data(
            start=start_date.isoformat(), end=end_date.isoformat()
        )
        if isinstance(data, pd.DataFrame):
            data = data.iloc[:, 0]
        data.index = pd.DatetimeIndex(data.index)
        data.name = "vix"
        return data
    except ImportError:
        raise ConnectionError(
            "gs_quant_internal not available. Run on GS desktop with active session."
        )


def _extract_atm_iv(raw: pd.DataFrame, tenor: str) -> pd.Series:
    """Extract ATM IV for a specific tenor from raw ERDVOL data.

    Filters: relativeStrike=1.0, strikeReference='forward', requested tenor.
    Returns one value per business day.
    """
    mask = (
        (raw["relativeStrike"] == _ATM_STRIKE)
        & (raw["strikeReference"] == _ATM_STRIKE_REF)
        & (raw["tenor"] == tenor)
    )
    filtered = raw.loc[mask, "impliedVolatility"]
    # Group by date in case of duplicates, take first
    return filtered.groupby(filtered.index).first()


def _extract_wing_iv(raw: pd.DataFrame, strike: float, tenor: str) -> pd.Series:
    """Extract wing IV (put or call) for a specific strike and tenor.

    Both wings use strikeReference='delta' (call-delta convention):
      - 25-delta put  = relativeStrike=0.75 (75-delta call)
      - 25-delta call = relativeStrike=0.25
    """
    mask = (
        (raw["relativeStrike"] == strike)
        & (raw["strikeReference"] == _WING_STRIKE_REF)
        & (raw["tenor"] == tenor)
    )
    filtered = raw.loc[mask, "impliedVolatility"]
    return filtered.groupby(filtered.index).first()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ingest_iv_surface(
    start_date: date,
    end_date: date,
    progress_callback=None,
    on_chunk=None,
) -> pd.DataFrame:
    """Fetch and assemble raw IV surface panel for SPX.

    Parameters
    ----------
    start_date : date
        Start of date range (inclusive).
    end_date : date
        End of date range (inclusive).
    progress_callback : callable, optional
        Called with (message: str) for progress updates.
    on_chunk : callable, optional
        Called with (chunks_done: int, total_chunks: int) after each API chunk.

    Returns
    -------
    pd.DataFrame
        Daily panel with columns:
        - atm_iv_1m: ATM IV 1-month (decimal, e.g., 0.15 = 15%)
        - atm_iv_3m: ATM IV 3-month (decimal)
        - iv_put_25d_1m: 25-delta put IV (decimal)
        - iv_call_25d_1m: 25-delta call IV (decimal)
        - skew_1m: put - call (decimal)
        - vix: VIX index level
        Index: DatetimeIndex (name='date')
    """
    if progress_callback:
        progress_callback("Fetching SPX IV surface from Marquee...")

    raw = _fetch_raw_iv_surface(start_date, end_date, on_chunk=on_chunk)

    if raw.empty:
        logger.warning("Empty IV surface returned from Marquee")
        return pd.DataFrame(
            columns=["atm_iv_1m", "atm_iv_3m", "iv_put_25d_1m", "iv_call_25d_1m", "skew_1m", "vix"]
        )

    if progress_callback:
        progress_callback(f"Processing {len(raw)} raw IV rows...")

    # Extract ATM IVs
    atm_1m = _extract_atm_iv(raw, "1m")
    atm_3m = _extract_atm_iv(raw, "3m")

    # Extract wing IVs for skew and butterfly
    put_25d = _extract_wing_iv(raw, _PUT_25D_STRIKE, "1m")
    call_25d = _extract_wing_iv(raw, _CALL_25D_STRIKE, "1m")

    # Assemble into panel
    panel = pd.DataFrame(
        {
            "atm_iv_1m": atm_1m,
            "atm_iv_3m": atm_3m,
            "iv_put_25d_1m": put_25d,
            "iv_call_25d_1m": call_25d,
        }
    )

    # Compute skew = put - call
    panel["skew_1m"] = panel["iv_put_25d_1m"] - panel["iv_call_25d_1m"]

    # Fetch VIX (single fast TSDB call, not parallelized — GsSession is not thread-safe)
    if progress_callback:
        progress_callback("Fetching VIX daily close...")

    vix = _fetch_vix_daily(start_date, end_date)
    panel["vix"] = vix.reindex(panel.index)

    # Clean up index
    panel.index = pd.DatetimeIndex(panel.index)
    panel.index.name = "date"
    panel = panel.sort_index()

    logger.info(
        "IV surface ingested: %d days, %s to %s",
        len(panel),
        panel.index[0].date() if len(panel) > 0 else "N/A",
        panel.index[-1].date() if len(panel) > 0 else "N/A",
    )

    return panel


def save_iv_cache(panel: pd.DataFrame, path: Path | None = None) -> Path:
    """Save raw IV panel to parquet.

    Parameters
    ----------
    panel : pd.DataFrame
        Output of ingest_iv_surface().
    path : Path, optional
        Target path. Defaults to data/raw/iv/iv_surface_spx.parquet.

    Returns
    -------
    Path
        Path where the file was saved.
    """
    if path is None:
        cache_dir = iv_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = cache_dir / _RAW_CACHE_FILENAME

    path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(path)
    logger.info("IV surface cache saved: %s (%d rows)", path, len(panel))
    return path


def load_iv_cache(path: Path | None = None) -> pd.DataFrame | None:
    """Load cached raw IV panel from parquet.

    Parameters
    ----------
    path : Path, optional
        Source path. Defaults to data/raw/iv/iv_surface_spx.parquet.

    Returns
    -------
    pd.DataFrame or None
        The cached panel, or None if the file doesn't exist.
    """
    if path is None:
        path = iv_cache_dir() / _RAW_CACHE_FILENAME

    if not path.exists():
        return None

    panel = pd.read_parquet(path)
    logger.info("IV surface cache loaded: %s (%d rows)", path, len(panel))
    return panel
