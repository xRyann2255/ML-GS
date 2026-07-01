"""Tests for the vol kvar CLI helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd


def test_parser_accepts_kvar_command():
    from volforecast.__main__ import _build_parser

    parser = _build_parser()
    args = parser.parse_args(["kvar"])

    assert args.command == "kvar"
    assert args.target == "both"
    assert args.edrvs_intraday_path is None


def test_build_kvar_tables_includes_iv_summary_columns_and_optional_2dte(tmp_path, monkeypatch):
    from volforecast.evaluation.kvar_table import build_kvar_tables

    dates = pd.bdate_range("2024-01-02", periods=6, freq="B")
    gsvivs = pd.Series([100.0, 101.0, 99.0, 102.0, 101.0, 103.0], index=dates, name="gsvivs01")

    iv_cache = pd.DataFrame(
        {
            "iv_1w_atm": [14.0, 14.5, 13.8, 14.2, 14.9, 15.1],
        },
        index=dates,
    )
    exec_kvar = pd.Series([16.0, 16.5, 15.8, 16.2, 16.8, 17.0], index=dates, name="kvar_vol_pct")
    edrvs_prev = pd.Series([15.0, 15.4, 14.9, 15.2, 15.6, 15.9], index=dates, name="iv_vs_0dte")
    edrvs_morning = pd.Series(
        [15.2, 15.6, 15.0, 15.3, 15.8, 16.0], index=dates, name="iv_morning_1dte"
    )
    spx_rv = pd.DataFrame(
        {
            "rv": [0.0064, 0.0081, 0.0072, 0.0100, 0.0090, 0.0085],
        },
        index=dates,
    )

    raw_rows = []
    for ts, vol_1d, vol_2d in zip(
        dates,
        [15.1, 15.5, 15.0, 15.4, 15.7, 16.1],
        [15.8, 16.0, 15.6, 15.9, 16.2, 16.4],
        strict=True,
    ):
        raw_rows.append(
            {
                "time": pd.Timestamp(ts).tz_localize("UTC") + pd.Timedelta(hours=13, minutes=35),
                "expirationDate": pd.Timestamp(ts) + pd.offsets.BDay(1),
                "fairVolatility": vol_1d,
            }
        )
        raw_rows.append(
            {
                "time": pd.Timestamp(ts).tz_localize("UTC") + pd.Timedelta(hours=13, minutes=35),
                "expirationDate": pd.Timestamp(ts) + pd.offsets.BDay(2),
                "fairVolatility": vol_2d,
            }
        )
        raw_rows.append(
            {
                "time": pd.Timestamp(ts).tz_localize("UTC") + pd.Timedelta(hours=19),
                "expirationDate": pd.Timestamp(ts) + pd.offsets.BDay(1),
                "fairVolatility": vol_1d - 0.3,
            }
        )
        raw_rows.append(
            {
                "time": pd.Timestamp(ts).tz_localize("UTC") + pd.Timedelta(hours=19),
                "expirationDate": pd.Timestamp(ts) + pd.offsets.BDay(2),
                "fairVolatility": vol_2d - 0.2,
            }
        )
    raw = pd.DataFrame(raw_rows).set_index("time")
    intraday_path = tmp_path / "edrvs_expiry_intraday_raw.parquet"
    raw.to_parquet(intraday_path)

    monkeypatch.setattr("volforecast.data.edrvol.fetch_gsvivs_index", lambda: gsvivs)
    monkeypatch.setattr("volforecast.data.edrvol.load_iv_cache", lambda symbol: iv_cache)
    monkeypatch.setattr("volforecast.data.edrvol.load_exec_kvar_cache", lambda: exec_kvar)
    monkeypatch.setattr("volforecast.data.edrvol.load_edrvs_cache", lambda: edrvs_prev)
    monkeypatch.setattr("volforecast.data.edrvol.load_edrvs_morning_cache", lambda: edrvs_morning)

    original_read_parquet = pd.read_parquet

    def fake_read_parquet(path, *args, **kwargs):
        if str(path).endswith("SPX.parquet"):
            return spx_rv.copy()
        return original_read_parquet(path, *args, **kwargs)

    monkeypatch.setattr("pandas.read_parquet", fake_read_parquet)

    tables = build_kvar_tables(edrvs_intraday_path=intraday_path)

    assert set(tables) == {"Same-Day RV", "Next-Day RV"}
    next_day = tables["Next-Day RV"]
    assert "Mean IV" in next_day.columns
    assert "IV Std" in next_day.columns
    assert "Exec Kvar (true fill)" in next_day["Model"].values
    assert "EDRVS morning 2-DTE" in next_day["Model"].values
    assert "EDRVS prev-close 2-DTE" in next_day["Model"].values

    exec_row = next_day.loc[next_day["Model"] == "Exec Kvar (true fill)"].iloc[0]
    assert exec_row["Mean IV"] > exec_kvar.min()
    assert exec_row["Mean IV"] < exec_kvar.max()
    assert exec_row["IV Std"] > 0.0

    baseline_row = next_day.loc[next_day["Model"] == "[baseline] always_long"].iloc[0]
    assert np.isnan(baseline_row["Mean IV"])
    assert np.isnan(baseline_row["IV Std"])


def test_build_kvar_tables_skips_sparse_variants_without_blocking_full_rows(monkeypatch):
    from volforecast.evaluation.kvar_table import build_kvar_tables

    dates = pd.bdate_range("2024-01-02", periods=6, freq="B")
    gsvivs = pd.Series([100.0, 101.0, 99.0, 102.0, 101.0, 103.0], index=dates, name="gsvivs01")
    iv_cache = pd.DataFrame({"iv_1w_atm": [14.0, 14.5, 13.8, 14.2, 14.9, 15.1]}, index=dates)
    exec_kvar = pd.Series([16.0, 16.5, 15.8, 16.2, 16.8, 17.0], index=dates, name="kvar_vol_pct")
    edrvs_prev = pd.Series([15.0, 15.4, 14.9, 15.2, 15.6, 15.9], index=dates, name="iv_vs_0dte")
    sparse_morning = pd.Series([15.2], index=dates[:1], name="iv_morning_1dte")
    spx_rv = pd.DataFrame({"rv": [0.0064, 0.0081, 0.0072, 0.0100, 0.0090, 0.0085]}, index=dates)

    monkeypatch.setattr("volforecast.data.edrvol.fetch_gsvivs_index", lambda: gsvivs)
    monkeypatch.setattr("volforecast.data.edrvol.load_iv_cache", lambda symbol: iv_cache)
    monkeypatch.setattr("volforecast.data.edrvol.load_exec_kvar_cache", lambda: exec_kvar)
    monkeypatch.setattr("volforecast.data.edrvol.load_edrvs_cache", lambda: edrvs_prev)
    monkeypatch.setattr("volforecast.data.edrvol.load_edrvs_morning_cache", lambda: sparse_morning)

    original_read_parquet = pd.read_parquet

    def fake_read_parquet(path, *args, **kwargs):
        if str(path).endswith("SPX.parquet"):
            return spx_rv.copy()
        return original_read_parquet(path, *args, **kwargs)

    monkeypatch.setattr("pandas.read_parquet", fake_read_parquet)

    tables = build_kvar_tables()
    next_day = tables["Next-Day RV"]

    assert "Exec Kvar (true fill)" in next_day["Model"].values
    assert "EDRVS prev-close 1-DTE" in next_day["Model"].values
    assert "EDRVS morning 1-DTE" not in next_day["Model"].values
