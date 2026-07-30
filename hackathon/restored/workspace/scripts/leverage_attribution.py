"""Leverage-effect attribution: data assembly.

Produces aligned daily DataFrame with SPX/VIX features, ML signal, and GSVIVS returns.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_MODELS = ROOT / "data" / "models"
OUTPUT_PATH = ROOT / "workspace" / "tmp" / "leverage_aligned_data.parquet"

CAL_TO_TRADING = np.sqrt(252.0 / 365.0)  # ~0.831


def load_spx() -> pd.Series:
    """Load SPX close prices with DatetimeIndex."""
    df = pd.read_parquet(DATA_RAW / "ohlcv" / "SPX.parquet")
    df.index = pd.to_datetime(df.index)
    return df["close"].sort_index()


def load_vix() -> pd.Series:
    """Load VIX close prices with DatetimeIndex."""
    df = pd.read_parquet(DATA_RAW / "iv" / "_VIX.parquet")
    df.index = pd.to_datetime(df.index)
    return df["vix"].sort_index()


def load_gsvivs() -> pd.Series:
    """Load GSVIVS01 index levels with DatetimeIndex."""
    df = pd.read_parquet(DATA_RAW / "cross_asset" / "gsvivs01.parquet")
    df.index = pd.to_datetime(df.index)
    return df["gsvivs01"].sort_index()


def load_exec_kvar() -> pd.Series:
    """Load execution Kvar (annualized vol %, 365-day convention)."""
    df = pd.read_parquet(DATA_PROCESSED / "gsvivs_exec_kvar.parquet")
    # trade_date is a column, not the index
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.set_index("trade_date").sort_index()
    return df["kvar_vol_pct"]


def load_har_predictions() -> pd.DataFrame:
    """Load HAR model OOS predictions (log-variance space)."""
    df = pd.read_csv(
        DATA_MODELS / "tournament_har_SPY" / "SPY" / "predictions_h1.csv",
        parse_dates=["date"],
        index_col="date",
    )
    return df.sort_index()


def compute_ml_signal(kvar_pct: pd.Series, har_pred: pd.Series) -> pd.Series:
    """Compute binary ML signal from Kvar and HAR RV forecast.

    Parameters
    ----------
    kvar_pct : annualized vol % (365-day calendar convention)
    har_pred : log(daily variance) from HAR model

    Returns
    -------
    signal : 1 = short vol (gap >= 0), 0 = flat (gap < 0)
    """
    # Convert HAR prediction from log(daily_variance) to annualized vol decimal
    # pred = log(daily_var), so annualized_vol = sqrt(exp(pred) * 252)
    rv_vol_decimal = np.sqrt(np.exp(har_pred) * 252)

    # Convert Kvar from pct (365-day) to trading-day annualized decimal
    kvar_decimal = kvar_pct / 100.0 * CAL_TO_TRADING

    gap = kvar_decimal - rv_vol_decimal
    signal = (gap >= 0).astype(int)
    return signal


def assemble_leverage_data() -> pd.DataFrame:
    """Assemble aligned daily DataFrame for leverage attribution analysis.

    Returns DataFrame with columns:
        - spx_return_t1: SPX return on T-1
        - vix_change_t1: VIX level change on T-1
        - rolling_corr_21d: 21-day rolling correlation (up to T-1)
        - ml_signal: binary signal for day T
        - gsvivs_daily_return: GSVIVS01 return on day T
    """
    # Load all data sources
    spx_close = load_spx()
    vix_close = load_vix()
    gsvivs = load_gsvivs()
    exec_kvar = load_exec_kvar()
    har_df = load_har_predictions()

    # --- SPX features ---
    spx_return = spx_close.pct_change()  # return on day d = close[d]/close[d-1] - 1

    # --- VIX features ---
    vix_change = vix_close.diff()  # change on day d = vix[d] - vix[d-1]

    # --- Rolling correlation (SPX returns vs VIX changes) ---
    # Align on common dates for correlation computation
    corr_df = pd.DataFrame({"spx_ret": spx_return, "vix_chg": vix_change}).dropna()
    rolling_corr = corr_df["spx_ret"].rolling(21, min_periods=21).corr(
        corr_df["vix_chg"]
    )

    # --- GSVIVS daily return ---
    gsvivs_return = gsvivs.pct_change()

    # --- ML signal ---
    # TIMING FIX: exec_kvar trade_date=T is the FILL PRICE at 09:30-10:00 ET on
    # day T (not known until after execution). The honest signal available at
    # 09:10 ET uses yesterday's exec_kvar as the best prior for today's strip.
    # shift(1) ensures signal[T] uses kvar[T-1] (known before T's open).
    har_pred = har_df["prediction"]
    signal = compute_ml_signal(exec_kvar.shift(1), har_pred)

    # --- Assemble into single DataFrame ---
    # spx_return_t1[T] = spx_return[T-1], i.e. shift forward by 1
    # vix_change_t1[T] = vix_change[T-1], i.e. shift forward by 1
    # rolling_corr_21d[T] = rolling_corr[T-1], i.e. shift forward by 1
    result = pd.DataFrame(
        {
            "spx_return_t1": spx_return.shift(1),  # T-1 return available at T
            "vix_change_t1": vix_change.shift(1),  # T-1 change available at T
            "rolling_corr_21d": rolling_corr.shift(1),  # corr up to T-1
            "ml_signal": signal,
            "gsvivs_daily_return": gsvivs_return,
        }
    )

    # Restrict to GSVIVS backtest period (2022-05 onwards)
    result = result.loc["2022-05-01":]

    # Drop rows with any NaN (first few rows lack rolling window)
    result = result.dropna()

    return result


def main() -> Path:
    """Run assembly and save to parquet. Returns output path."""
    df = assemble_leverage_data()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PATH)
    print(f"Saved {len(df)} rows to {OUTPUT_PATH}")
    print(f"Date range: {df.index.min()} to {df.index.max()}")
    print(f"Columns: {list(df.columns)}")
    print(f"Signal distribution: short={int((df['ml_signal'] == 1).sum())}, "
          f"flat={int((df['ml_signal'] == 0).sum())}")
    return OUTPUT_PATH


# ---------------------------------------------------------------------------
# Step 2: Leverage Attribution Analysis
# ---------------------------------------------------------------------------

ATTRIBUTION_OUTPUT = ROOT / "workspace" / "tmp" / "leverage_attribution.txt"


def _sharpe(daily_pnl: pd.Series) -> float:
    """Annualized Sharpe ratio (0% RF)."""
    if daily_pnl.std() == 0:
        return 0.0
    return float(daily_pnl.mean() / daily_pnl.std() * np.sqrt(252))


def compute_attribution(df: pd.DataFrame) -> str:
    """Compute leverage attribution metrics and return formatted summary.

    Parameters
    ----------
    df : DataFrame with columns spx_return_t1, vix_change_t1, rolling_corr_21d,
         ml_signal, gsvivs_daily_return (DatetimeIndex).

    Returns
    -------
    Formatted summary string.
    """
    n = len(df)
    date_start = df.index.min().strftime("%Y-%m-%d")
    date_end = df.index.max().strftime("%Y-%m-%d")

    # --- Construct signals ---
    ml_signal = df["ml_signal"].astype(int)

    # Simple leverage rule: stand aside when SPX fell yesterday
    simple_lev = (df["spx_return_t1"] >= 0).astype(int)

    # Correlated leverage rule: stand aside when SPX fell AND correlation < -0.5
    corr_lev = (~((df["spx_return_t1"] < 0) & (df["rolling_corr_21d"] < -0.5))).astype(int)

    # --- Loss days ---
    loss = df["gsvivs_daily_return"] < 0
    n_loss = int(loss.sum())
    loss_pct = 100.0 * n_loss / n

    # --- Per-signal metrics ---
    signals = {"ML Signal": ml_signal, "Simple Lev": simple_lev, "Corr Lev": corr_lev}
    metrics: dict[str, dict[str, float]] = {}

    for name, sig in signals.items():
        stand_aside = sig == 0
        n_aside = int(stand_aside.sum())

        # Firing rate
        firing_rate = 100.0 * n_aside / n

        # Precision of stand-aside
        if n_aside > 0:
            precision = 100.0 * (stand_aside & loss).sum() / n_aside
        else:
            precision = 0.0

        # Overall hit rate
        correct = ((sig == 1) & ~loss) | ((sig == 0) & loss)
        hit_rate = 100.0 * correct.sum() / n

        # Sharpe
        daily_pnl = sig * df["gsvivs_daily_return"]
        sharpe = _sharpe(daily_pnl)

        metrics[name] = {
            "firing_rate": firing_rate,
            "precision": precision,
            "hit_rate": hit_rate,
            "sharpe": sharpe,
        }

    # --- Baselines ---
    always_short_sharpe = _sharpe(df["gsvivs_daily_return"])
    combined_simple = ((ml_signal == 1) & (simple_lev == 1)).astype(int)
    combined_corr = ((ml_signal == 1) & (corr_lev == 1)).astype(int)
    combined_simple_sharpe = _sharpe(combined_simple * df["gsvivs_daily_return"])
    combined_corr_sharpe = _sharpe(combined_corr * df["gsvivs_daily_return"])

    # --- Disagreement Analysis ---
    def _disagreement(sig_a: pd.Series, sig_b: pd.Series, name_a: str, name_b: str) -> str:
        """Compute disagreement stats between two signals."""
        # A stands aside, B says fine
        a_aside_b_fine = (sig_a == 0) & (sig_b == 1)
        n_ab = int(a_aside_b_fine.sum())
        if n_ab > 0:
            prec_ab = 100.0 * (a_aside_b_fine & loss).sum() / n_ab
            avg_ret_ab = 100.0 * df.loc[a_aside_b_fine, "gsvivs_daily_return"].mean()
        else:
            prec_ab = 0.0
            avg_ret_ab = 0.0

        # B stands aside, A says fine
        b_aside_a_fine = (sig_b == 0) & (sig_a == 1)
        n_ba = int(b_aside_a_fine.sum())
        if n_ba > 0:
            prec_ba = 100.0 * (b_aside_a_fine & loss).sum() / n_ba
            avg_ret_ba = 100.0 * df.loc[b_aside_a_fine, "gsvivs_daily_return"].mean()
        else:
            prec_ba = 0.0
            avg_ret_ba = 0.0

        lines = [
            f"ML=stand-aside, {name_b}=fine: {n_ab} days",
            f"  → ML precision on these days: {prec_ab:.1f}% (loss days / total in this bucket)",
            f"  → Avg GSVIVS return: {avg_ret_ab:.3f}%",
            f"{name_b}=stand-aside, ML=fine: {n_ba} days",
            f"  → {name_b} precision on these days: {prec_ba:.1f}% (loss days / total in this bucket)",
            f"  → Avg GSVIVS return: {avg_ret_ba:.3f}%",
        ]
        return "\n".join(lines)

    disagree_simple = _disagreement(ml_signal, simple_lev, "ML", "Lev")
    disagree_corr = _disagreement(ml_signal, corr_lev, "ML", "CorrLev")

    # --- Interpretation ---
    ml_sharpe = metrics["ML Signal"]["sharpe"]
    interpretation_parts = []
    if ml_sharpe > always_short_sharpe:
        interpretation_parts.append(
            f"The ML signal improves Sharpe from {always_short_sharpe:.3f} (always-short) "
            f"to {ml_sharpe:.3f}"
        )
    else:
        interpretation_parts.append(
            f"The ML signal ({ml_sharpe:.3f}) does not improve over always-short ({always_short_sharpe:.3f})"
        )

    simple_sharpe = metrics["Simple Lev"]["sharpe"]
    if simple_sharpe > always_short_sharpe:
        interpretation_parts.append(
            f"The simple leverage rule also adds value (Sharpe {simple_sharpe:.3f})"
        )
    else:
        interpretation_parts.append(
            f"The simple leverage rule alone does not beat always-short (Sharpe {simple_sharpe:.3f})"
        )

    if combined_simple_sharpe > ml_sharpe:
        interpretation_parts.append(
            f"Combining ML with simple leverage improves further to {combined_simple_sharpe:.3f}, "
            "suggesting the leverage rule captures information the ML signal misses"
        )
    else:
        interpretation_parts.append(
            "Combining ML with leverage does not improve over ML alone, "
            "suggesting the ML signal already captures the leverage effect"
        )

    interpretation = ". ".join(interpretation_parts) + "."

    # --- Format output ---
    m = metrics
    output = f"""\
===========================================================
LEVERAGE ATTRIBUTION: ML Signal vs Leverage Rule
===========================================================
Period: {date_start} to {date_end} ({n} trading days)
Loss days (GSVIVS return < 0): {n_loss} ({loss_pct:.1f}%)

--- Signal Comparison ---
                          ML Signal  Simple Lev  Corr Lev
Stand-aside firing rate      {m['ML Signal']['firing_rate']:5.1f}%      {m['Simple Lev']['firing_rate']:5.1f}%    {m['Corr Lev']['firing_rate']:5.1f}%
Stand-aside precision        {m['ML Signal']['precision']:5.1f}%      {m['Simple Lev']['precision']:5.1f}%    {m['Corr Lev']['precision']:5.1f}%
Overall hit rate             {m['ML Signal']['hit_rate']:5.1f}%      {m['Simple Lev']['hit_rate']:5.1f}%    {m['Corr Lev']['hit_rate']:5.1f}%
Annualized Sharpe            {m['ML Signal']['sharpe']:5.3f}      {m['Simple Lev']['sharpe']:5.3f}    {m['Corr Lev']['sharpe']:5.3f}

--- Baselines ---
Always-short Sharpe: {always_short_sharpe:.3f}
Combined (ML OR simple) Sharpe: {combined_simple_sharpe:.3f}
Combined (ML OR corr) Sharpe: {combined_corr_sharpe:.3f}

--- Disagreement Analysis (vs Simple Leverage Rule) ---
{disagree_simple}

--- Disagreement Analysis (vs Correlated Leverage Rule) ---
{disagree_corr}

--- Interpretation ---
{interpretation}
===========================================================
"""
    return output


def main_attribution() -> Path:
    """Load aligned data from Step 1 and run attribution analysis."""
    df = pd.read_parquet(OUTPUT_PATH)
    df.index = pd.to_datetime(df.index)
    summary = compute_attribution(df)
    ATTRIBUTION_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    ATTRIBUTION_OUTPUT.write_text(summary)
    print(summary)
    return ATTRIBUTION_OUTPUT


if __name__ == "__main__":
    main()
    main_attribution()
