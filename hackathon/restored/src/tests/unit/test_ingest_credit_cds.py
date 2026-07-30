"""TDD: credit CDS ingestion wiring in ingest-iv CLI.

Verifies that ingest_iv.run() invokes fetch_credit_cds() and persists the
result via save_iv_cache("_CREDIT_CDS", df) when force=True.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import numpy as np
import pandas as pd


def _make_iv_dataframe(
    start: str = "2024-01-02",
    end: str = "2024-01-31",
) -> pd.DataFrame:
    """Create a minimal per-symbol IV DataFrame matching ingest_iv's expectations."""
    idx = pd.DatetimeIndex(pd.bdate_range(start, end), name="date")
    n = len(idx)
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "iv_1m_atm": 20.0 + rng.normal(0, 1, n),
            "iv_3m_atm": 22.0 + rng.normal(0, 1, n),
            "iv_1m_25dp": 24.0 + rng.normal(0, 1, n),
            "iv_1m_25dc": 18.0 + rng.normal(0, 1, n),
        },
        index=idx,
    )


def _make_credit_cds_df(
    start: str = "2024-01-02",
    end: str = "2024-01-31",
) -> pd.DataFrame:
    """Synthetic credit CDS panel with the expected columns."""
    idx = pd.DatetimeIndex(pd.bdate_range(start, end), name="date")
    return pd.DataFrame(
        {
            "credit_ig_5y": np.linspace(45.0, 47.0, len(idx)),
            "credit_hy_5y": np.linspace(325.0, 330.0, len(idx)),
        },
        index=idx,
    )


@patch("volforecast.data.edrvol.fetch_credit_cds")
@patch("volforecast.data.edrvol.compute_iv_dispersion")
@patch("volforecast.data.edrvol.fetch_treasury_yields")
@patch("volforecast.data.edrvol.fetch_ovx")
@patch("volforecast.data.edrvol.fetch_vix_index")
@patch("volforecast.data.edrvol.fetch_vvix")
@patch("volforecast.data.edrvol.fetch_edrvol")
@patch("volforecast.data.edrvol.load_iv_cache", return_value=None)
@patch("volforecast.data.edrvol.save_iv_cache")
def test_run_saves_credit_cds_cache(
    mock_save,
    mock_load,
    mock_fetch_edrvol,
    mock_vvix,
    mock_vix,
    mock_ovx,
    mock_tsy,
    mock_dispersion,
    mock_credit_cds,
    tmp_path,
):
    """When fetch_credit_cds returns non-empty data, save_iv_cache is called with '_CREDIT_CDS'."""
    # Also stub the GSVIVS block (uses _get_tsdb_data directly) so it doesn't touch TSDB
    with patch("volforecast.cli.ingest_iv._get_tsdb_data") as mock_tsdb, \
         patch("volforecast.cli.ingest_iv.save_gsvivs_cache"), \
         patch("volforecast.cli.ingest_iv.load_gsvivs_cache", return_value=None):
        from volforecast.cli.ingest_iv import run

        mock_fetch_edrvol.return_value = _make_iv_dataframe()
        mock_vvix.return_value = pd.Series(dtype=float, name="vvix")
        mock_vix.return_value = pd.Series(dtype=float, name="vix")
        mock_ovx.return_value = pd.Series(dtype=float, name="ovx")
        mock_tsy.return_value = pd.DataFrame()
        mock_dispersion.return_value = pd.Series(dtype=float)
        mock_tsdb.return_value = pd.Series(
            [100.0],
            index=pd.DatetimeIndex(["2024-01-02"], name="date"),
        )

        credit_df = _make_credit_cds_df()
        mock_credit_cds.return_value = credit_df

        run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 31),
            symbols=["SPY"],
            force=True,
            cache_dir=tmp_path,
        )

    # Assert fetch was called with the requested date range
    mock_credit_cds.assert_called_once()
    # Assert save was called with cache key "_CREDIT_CDS"
    credit_save_calls = [c for c in mock_save.call_args_list if c.args[0] == "_CREDIT_CDS"]
    assert len(credit_save_calls) == 1, (
        f"Expected exactly one save_iv_cache('_CREDIT_CDS', ...) call, "
        f"got {len(credit_save_calls)}. All calls: "
        f"{[c.args[0] for c in mock_save.call_args_list]}"
    )
    saved_df = credit_save_calls[0].args[1]
    assert list(saved_df.columns) == ["credit_ig_5y", "credit_hy_5y"]
    assert len(saved_df) == len(credit_df)


@patch("volforecast.data.edrvol.fetch_credit_cds")
@patch("volforecast.data.edrvol.compute_iv_dispersion")
@patch("volforecast.data.edrvol.fetch_treasury_yields")
@patch("volforecast.data.edrvol.fetch_ovx")
@patch("volforecast.data.edrvol.fetch_vix_index")
@patch("volforecast.data.edrvol.fetch_vvix")
@patch("volforecast.data.edrvol.fetch_edrvol")
@patch("volforecast.data.edrvol.load_iv_cache", return_value=None)
@patch("volforecast.data.edrvol.save_iv_cache")
def test_run_skips_save_when_credit_cds_empty(
    mock_save,
    mock_load,
    mock_fetch_edrvol,
    mock_vvix,
    mock_vix,
    mock_ovx,
    mock_tsy,
    mock_dispersion,
    mock_credit_cds,
    tmp_path,
):
    """Empty credit_cds DataFrame -> no _CREDIT_CDS cache write, no crash."""
    with patch("volforecast.cli.ingest_iv._get_tsdb_data") as mock_tsdb, \
         patch("volforecast.cli.ingest_iv.save_gsvivs_cache"), \
         patch("volforecast.cli.ingest_iv.load_gsvivs_cache", return_value=None):
        from volforecast.cli.ingest_iv import run

        mock_fetch_edrvol.return_value = _make_iv_dataframe()
        mock_vvix.return_value = pd.Series(dtype=float, name="vvix")
        mock_vix.return_value = pd.Series(dtype=float, name="vix")
        mock_ovx.return_value = pd.Series(dtype=float, name="ovx")
        mock_tsy.return_value = pd.DataFrame()
        mock_dispersion.return_value = pd.Series(dtype=float)
        mock_tsdb.return_value = pd.Series(
            [100.0],
            index=pd.DatetimeIndex(["2024-01-02"], name="date"),
        )

        # Simulate TSDB failure returning an empty frame with expected columns
        mock_credit_cds.return_value = pd.DataFrame(
            columns=["credit_ig_5y", "credit_hy_5y"],
            index=pd.DatetimeIndex([], name="date"),
        )

        # Should not raise
        run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 31),
            symbols=["SPY"],
            force=True,
            cache_dir=tmp_path,
        )

    # No save should happen for _CREDIT_CDS
    credit_save_calls = [c for c in mock_save.call_args_list if c.args[0] == "_CREDIT_CDS"]
    assert len(credit_save_calls) == 0
