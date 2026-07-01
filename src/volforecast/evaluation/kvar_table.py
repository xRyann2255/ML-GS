"""Build GSVIVS IV comparison tables from cached data sources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from volforecast.evaluation.economic_value import (
    gsvivs_baselines,
    gsvivs_signal_pnl,
    kvar_rv_gap_signal,
)
from volforecast.utils.paths import ticks_cache_path, tmp_dir


@dataclass(frozen=True)
class IVVariant:
    label: str
    series: pd.Series
    is_calendar_ann: bool


def _normalize_series(series: pd.Series, name: str | None = None) -> pd.Series:
    normalized = series.copy()
    normalized.index = pd.DatetimeIndex(normalized.index).normalize()
    normalized = normalized.sort_index().astype(float)
    if name is not None:
        normalized.name = name
    return normalized


def _default_edrvs_intraday_path() -> Path:
    return tmp_dir() / "edrvs_expiry_intraday_raw.parquet"


def _load_edrvs_intraday_variants(path: Path | None) -> list[IVVariant]:
    intraday_path = path or _default_edrvs_intraday_path()
    if not intraday_path.exists():
        return []

    raw = pd.read_parquet(intraday_path)
    if raw.empty:
        return []

    raw = raw.copy()
    raw.index = pd.DatetimeIndex(raw.index, tz="UTC")
    raw["obs_date"] = raw.index.normalize()
    raw["hour"] = raw.index.hour
    raw["minute"] = raw.index.minute
    raw["expirationDate"] = pd.to_datetime(raw["expirationDate"])
    if raw["expirationDate"].dt.tz is not None:
        raw["expirationDate"] = raw["expirationDate"].dt.tz_localize(None)
    raw["expirationDate"] = raw["expirationDate"].dt.normalize()

    morning_2dte: dict[pd.Timestamp, float] = {}
    prev_close_2dte: dict[pd.Timestamp, float] = {}

    for obs_dt, day_data in raw.groupby("obs_date"):
        obs_naive = obs_dt.tz_localize(None) if obs_dt.tzinfo else obs_dt
        obs_naive = obs_naive.normalize()
        two_bday = (obs_naive + pd.offsets.BDay(2)).normalize()
        next_bday = (obs_naive + pd.offsets.BDay(1)).normalize()

        morning = day_data[
            (day_data["hour"] == 13) & (day_data["minute"] >= 30) & (day_data["minute"] <= 40)
        ]
        if not morning.empty:
            hit_2dte = morning[morning["expirationDate"] == two_bday]
            if not hit_2dte.empty:
                morning_2dte[obs_naive] = float(hit_2dte.iloc[0]["fairVolatility"])

        close = day_data[day_data["hour"] >= 19]
        if close.empty:
            close = day_data[day_data["hour"] >= 18]
        if not close.empty:
            hit_2dte = close[close["expirationDate"] == two_bday]
            if not hit_2dte.empty:
                prev_close_2dte[next_bday] = float(hit_2dte.iloc[-1]["fairVolatility"])

    variants: list[IVVariant] = []
    if morning_2dte:
        variants.append(
            IVVariant(
                label="EDRVS morning 2-DTE",
                series=_normalize_series(pd.Series(morning_2dte), "iv_morning_2dte"),
                is_calendar_ann=True,
            )
        )
    if prev_close_2dte:
        variants.append(
            IVVariant(
                label="EDRVS prev-close 2-DTE",
                series=_normalize_series(pd.Series(prev_close_2dte), "iv_prev_close_2dte"),
                is_calendar_ann=True,
            )
        )
    return variants


def load_iv_variants(edrvs_intraday_path: Path | None = None) -> list[IVVariant]:
    from volforecast.data.edrvol import (
        load_edrvs_cache,
        load_edrvs_morning_cache,
        load_exec_kvar_cache,
        load_iv_cache,
    )

    iv_cache = load_iv_cache("SPX")
    if iv_cache is None:
        iv_cache = load_iv_cache("SPY")

    variants: list[IVVariant] = []

    exec_kvar = load_exec_kvar_cache()
    if exec_kvar is not None and not exec_kvar.empty:
        variants.append(
            IVVariant(
                label="Exec Kvar (true fill)",
                series=_normalize_series(exec_kvar, "kvar_vol_pct"),
                is_calendar_ann=True,
            )
        )

    edrvs_morning = load_edrvs_morning_cache()
    if edrvs_morning is not None and not edrvs_morning.empty:
        variants.append(
            IVVariant(
                label="EDRVS morning 1-DTE",
                series=_normalize_series(edrvs_morning, "iv_morning_1dte"),
                is_calendar_ann=True,
            )
        )

    edrvs_prev_close = load_edrvs_cache()
    if edrvs_prev_close is not None and not edrvs_prev_close.empty:
        variants.append(
            IVVariant(
                label="EDRVS prev-close 1-DTE",
                series=_normalize_series(edrvs_prev_close, "iv_vs_0dte"),
                is_calendar_ann=True,
            )
        )

    if iv_cache is not None and not iv_cache.empty and "iv_1w_atm" in iv_cache.columns:
        variants.append(
            IVVariant(
                label="SPX ATM IV (1w)",
                series=_normalize_series(iv_cache["iv_1w_atm"], "iv_1w_atm"),
                is_calendar_ann=False,
            )
        )

    if iv_cache is not None and not iv_cache.empty and "iv_0dte" in iv_cache.columns:
        # iv_0dte is decimal (e.g. 0.17 = 17%); convert to vol points
        variants.append(
            IVVariant(
                label="SPX ATM IV (0-DTE)",
                series=_normalize_series(iv_cache["iv_0dte"] * 100.0, "iv_0dte_atm"),
                is_calendar_ann=False,
            )
        )

    variants.extend(_load_edrvs_intraday_variants(edrvs_intraday_path))
    return variants


def _load_gsvivs_series() -> pd.Series:
    from volforecast.data.edrvol import fetch_gsvivs_index

    gsvivs = fetch_gsvivs_index()
    if gsvivs is None or gsvivs.empty:
        raise ValueError("GSVIVS01 index cache is unavailable")
    return _normalize_series(gsvivs, "gsvivs01")


def _load_spx_same_day_rv() -> pd.Series:
    rv_panel = pd.read_parquet(ticks_cache_path("SPX"))
    if "rv" not in rv_panel.columns:
        raise ValueError("SPX RV cache is missing 'rv' column")
    rv_panel.index = pd.DatetimeIndex(rv_panel.index).normalize()
    same_day = np.sqrt(rv_panel["rv"].astype(float) * 252.0)
    same_day.name = "same_day_rv"
    return same_day.sort_index()


def _days_from_metrics(metrics: dict[str, float | str]) -> int:
    positive_days = str(metrics["positive_days"])
    return int(positive_days.split("/")[1].split()[0])


def _build_rows(gsvivs: pd.Series, rv_series: pd.Series, variants: list[IVVariant]) -> pd.DataFrame:
    anchor_common = gsvivs.index.intersection(rv_series.dropna().index).sort_values()

    if len(anchor_common) < 2:
        raise ValueError("Not enough common dates to build Kvar comparison table")

    rows: list[dict[str, float | int | str]] = []
    for variant in variants:
        common = anchor_common.intersection(variant.series.dropna().index).sort_values()
        if len(common) < 2:
            continue

        aligned_gsvivs = gsvivs.loc[common]
        aligned_rv = rv_series.loc[common].astype(float)
        aligned_iv = variant.series.loc[common].astype(float)
        signal = kvar_rv_gap_signal(
            aligned_iv.values,
            aligned_rv.values,
            space="vol",
            threshold=0.0,
            is_calendar_ann=variant.is_calendar_ann,
        )
        metrics = gsvivs_signal_pnl(aligned_gsvivs.values, signal)
        rows.append(
            {
                "Model": variant.label,
                "Sharpe": float(metrics["sharpe_0rf"]),
                "Ann Ret": float(metrics["ann_return"]),
                "Total": float(metrics["total_return"]),
                "MaxDD": float(metrics["max_drawdown"]),
                "Short%": float(np.mean(signal[:-1] < 0.0) * 100.0),
                "Hit%": float(metrics["hit_rate"] * 100.0),
                "Days": _days_from_metrics(metrics),
                "Mean IV": float(aligned_iv.iloc[:-1].mean()),
                "IV Std": float(aligned_iv.iloc[:-1].std(ddof=1)),
            }
        )

    if not rows:
        raise ValueError("No IV variants have enough common dates to build Kvar comparison table")

    all_baselines = gsvivs_baselines(gsvivs.loc[anchor_common].values)

    baseline = all_baselines["always_long"]
    rows.append(
        {
            "Model": "[baseline] always_long",
            "Sharpe": float(baseline["sharpe_0rf"]),
            "Ann Ret": float(baseline["ann_return"]),
            "Total": float(baseline["total_return"]),
            "MaxDD": float(baseline["max_drawdown"]),
            "Short%": 0.0,
            "Hit%": float(baseline["hit_rate"] * 100.0),
            "Days": _days_from_metrics(baseline),
            "Mean IV": np.nan,
            "IV Std": np.nan,
        }
    )

    baseline_random = all_baselines["always_random"]
    rows.append(
        {
            "Model": "[baseline] always_random",
            "Sharpe": float(baseline_random["sharpe_0rf"]),
            "Ann Ret": float(baseline_random["ann_return"]),
            "Total": float(baseline_random["total_return"]),
            "MaxDD": float(baseline_random["max_drawdown"]),
            "Short%": 50.0,
            "Hit%": float(baseline_random["hit_rate"] * 100.0),
            "Days": _days_from_metrics(baseline_random),
            "Mean IV": np.nan,
            "IV Std": np.nan,
        }
    )

    baseline_long_65 = all_baselines["random_long_65"]
    rows.append(
        {
            "Model": "[baseline] random_long_65",
            "Sharpe": float(baseline_long_65["sharpe_0rf"]),
            "Ann Ret": float(baseline_long_65["ann_return"]),
            "Total": float(baseline_long_65["total_return"]),
            "MaxDD": float(baseline_long_65["max_drawdown"]),
            "Short%": 35.0,
            "Hit%": float(baseline_long_65["hit_rate"] * 100.0),
            "Days": _days_from_metrics(baseline_long_65),
            "Mean IV": np.nan,
            "IV Std": np.nan,
        }
    )

    table = (
        pd.DataFrame(rows)
        .sort_values("Sharpe", ascending=False, kind="stable")
        .reset_index(drop=True)
    )
    table.attrs["common_dates"] = len(anchor_common)
    return table


def build_kvar_tables(edrvs_intraday_path: Path | None = None) -> dict[str, pd.DataFrame]:
    """Build the same-day and next-day GSVIVS IV comparison tables."""
    gsvivs = _load_gsvivs_series()
    same_day_rv = _load_spx_same_day_rv()
    variants = load_iv_variants(edrvs_intraday_path)
    if not variants:
        raise ValueError("No IV variants are available from cache")

    return {
        "Same-Day RV": _build_rows(gsvivs, same_day_rv, variants),
        "Next-Day RV": _build_rows(gsvivs, same_day_rv.shift(-1), variants),
    }
