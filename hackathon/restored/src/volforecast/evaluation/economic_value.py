"""Economic value testing of volatility signals.

Translates statistical forecasting improvements into economic metrics:
- Delta-hedged straddle P&L (trading the IV-RV gap)
- Vol-targeting portfolio (scaling exposure by inverse predicted vol)
- Sharpe ratio comparison vs buy-and-hold
- Maximum drawdown and VaR statistics

Key functions:
    iv_rv_gap_signal           — Generate IV-RV gap trading signal
    delta_hedged_straddle_pnl  — Backtest straddle P&L
    vol_targeting_pnl          — Backtest vol-targeting portfolio
    compute_sharpe             — Annualized Sharpe ratio
    compute_max_drawdown       — Maximum drawdown
    vol_targeting_sharpe       — One-shot: predictions + returns → Sharpe
    economic_value_summary     — Full economic value report
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np


def iv_tenor_for_horizon(horizon: int) -> tuple[str, int]:
    """Map forecast horizon to the appropriate IV column and tenor days.

    Uses the closest available tenor to match the forecast window:
      - h == 1:  iv_vs_0dte with tenor_days=1 (prev-close 1-DTE varswap
                 from EDRVS_EXPIRY_INTRADAY — correct measure for GSVIVS
                 signal. Captured at 16:00 ET day before, no lookahead.)
      - h <= 5:  iv_1w_atm with tenor_days=5 (weekly straddle)
      - h > 5:   iv_1m_atm with tenor_days=22 (monthly straddle)

    Returns (iv_column_name, tenor_days).
    """
    if horizon == 1:
        return "iv_vs_0dte", 1
    if horizon <= 5:
        return "iv_1w_atm", 5
    return "iv_1m_atm", 22


def normalize_exec_kvar_for_horizon(kvar: np.ndarray, tenor_days: int) -> np.ndarray:
    """No-op — Kvar is already in annualized vol and needs no horizon scaling.

    Previously this divided by sqrt(h) to convert the 24h-tenor Kvar into a
    multi-day proxy.  That was incorrect: both the Kvar (annualized from T=24h)
    and the RV forecast (annualized via sqrt(252 * daily_var)) are already in
    the same units regardless of forecast horizon h.  The sqrt(h) deflation
    artificially suppressed the implied-vol side of the IV-RV gap at h>1.

    Retained for backward compatibility — callers that still pass through this
    function get the identity (copy) back.
    """
    kvar = np.asarray(kvar, dtype=np.float64)
    return kvar.copy()


def iv_rv_gap_signal(
    iv_forecast: np.ndarray,
    rv_forecast: np.ndarray,
    threshold: float = 0.0,
    short_threshold: float | None = None,
    default_long: bool = False,
) -> np.ndarray:
    """Generate trading signal from IV-RV gap.

    Signal = +1 (sell vol) when IV > RV_forecast + threshold
    Signal = -1 (buy vol) when IV < RV_forecast - short_threshold
    Signal = 0 otherwise (or +1 if default_long=True).

    Both inputs must be in the same units (annualized variance or
    annualized volatility). Thresholds are in the same units.

    Parameters
    ----------
    iv_forecast : np.ndarray
        Implied volatility (annualized decimal, e.g. 0.20 for 20%).
    rv_forecast : np.ndarray
        Realized volatility forecasts (annualized decimal).
    threshold : float
        Signal threshold for sell-vol (+1) signal (default: 0).
    short_threshold : float or None
        Signal threshold for buy-vol (-1) signal. If None, uses
        ``threshold`` (symmetric). Set higher than threshold to require
        stronger conviction before buying vol (going against carry).
    default_long : bool
        If True, the default signal is +1 (always long) instead of 0
        (flat). Only flips to -1 when gap < -short_threshold.

    Returns
    -------
    np.ndarray
        Trading signals in {-1, 0, +1} (or {-1, +1} if default_long).
    """
    iv_forecast = np.asarray(iv_forecast, dtype=np.float64)
    rv_forecast = np.asarray(rv_forecast, dtype=np.float64)

    if short_threshold is None:
        short_threshold = threshold

    gap = iv_forecast - rv_forecast
    if default_long:
        signal = np.ones(len(gap), dtype=np.float64)
    else:
        signal = np.zeros(len(gap), dtype=np.float64)
        signal[gap > threshold] = 1.0  # IV expensive -> sell vol
    signal[gap < -short_threshold] = -1.0  # IV cheap -> buy vol
    return signal


def kvar_rv_gap_signal(
    kvar: np.ndarray,
    rv_forecast: np.ndarray,
    space: str = "vol",
    threshold: float = 0.0,
    is_calendar_ann: bool = True,
) -> np.ndarray:
    """Generate trading signal from prev-close 1-DTE varswap fair vol vs RV forecast.

    Signal = +1 (sell vol / stay long GSVIVS) when Kvar > RV + threshold.
    Signal = -1 (buy vol / go short GSVIVS) when RV > Kvar + threshold.

    The IV input is the previous day's close (~16:00 ET) of the varswap
    expiring today, from EDRVS_EXPIRY_INTRADAY. This is available well
    before the 09:10 ET signal decision — no lookahead bias.

    ANNUALIZATION NOTE: The EDRVS fairVolatility is in annualized vol%
    (calendar-hour convention). The RV forecast uses 252-trading-day
    annualization. This function converts Kvar to 252-space before
    comparing: kvar_252 = kvar * sqrt(252/365).

    Parameters
    ----------
    kvar : np.ndarray
        Execution Kvar in vol points (e.g. 15.0 = 15%, 365-calendar annualized).
    rv_forecast : np.ndarray
        Realized vol forecast in annualized decimal (e.g. 0.12 = 12%,
        252-trading-day annualized). This is RTH-only (intraday) RV.
    space : str
        "vol" — compare in volatility space: kvar_252/100 - rv_forecast.
        "variance" — compare in variance space: (kvar_252/100)^2 - rv_forecast^2.
    threshold : float
        Minimum gap before flipping signal. In vol space: annualized decimal
        (e.g. 0.01 = 1 vol point). In variance space: annualized variance units.
    is_calendar_ann : bool
        If True (default), kvar is in 365-calendar-day annualization and will be
        converted to 252-trading-day space. If False, kvar is already in
        252-trading-day convention (e.g. SPX ATM IV from EDRVOL).

    Returns
    -------
    np.ndarray
        Trading signals in {-1, +1}. Default long (+1) unless gap is negative
        beyond threshold. NaN kvar defaults to +1 (long).
    """
    kvar = np.asarray(kvar, dtype=np.float64)
    rv_forecast = np.asarray(rv_forecast, dtype=np.float64)

    # Convert Kvar from 365-calendar to 252-trading-day annualization
    if is_calendar_ann:
        _CAL_TO_TRADING = np.sqrt(252.0 / 365.0)  # ~0.831
        kvar_decimal = kvar / 100.0 * _CAL_TO_TRADING
    else:
        kvar_decimal = kvar / 100.0

    if space == "vol":
        gap = kvar_decimal - rv_forecast
    elif space == "variance":
        gap = kvar_decimal**2 - rv_forecast**2
    else:
        raise ValueError(f"space must be 'vol' or 'variance', got {space!r}")

    signal = np.ones(len(gap), dtype=np.float64)
    signal[gap < -threshold] = -1.0
    # NaN kvar => NaN gap => default long (np.ones already handles this since
    # NaN < -threshold is False)
    return signal


# ---------------------------------------------------------------------------
# Sized GSVIVS01 signal (sizing analysis 2026-06-15)
# ---------------------------------------------------------------------------

GSVIVS_SIZING_MODES = ("binary", "asym_long", "zscore", "long_flat")
DEFAULT_GSVIVS_SIZING_MODE = "asym_long"

# Modes that have no leverage knob (label omits ``L=...``).
_GSVIVS_UNLEVERED_MODES = ("binary", "long_flat")


@dataclass(frozen=True)
class GsvivsSizingSpec:
    """A single GSVIVS signal-sizing configuration.

    One spec drives one variant of the trading signal in the dashboard. The
    default 4-element list (:data:`DEFAULT_GSVIVS_SIZING_SPECS`) is the
    four-option toggle exposed on the GSVIVS table: ``binary``,
    ``asym_long`` (L=2), ``zscore`` (L=1), ``long_flat``.

    Notes
    -----
    ``max_leverage`` and ``lookback`` are ignored for ``mode == "binary"`` and
    ``mode == "long_flat"`` (both emit only un-sized {-1/0, +1} or {0, +1}
    positions).
    """

    mode: str
    max_leverage: float = 2.0
    lookback: int = 63

    def __post_init__(self) -> None:
        if self.mode not in GSVIVS_SIZING_MODES:
            raise ValueError(
                f"GsvivsSizingSpec.mode must be one of {GSVIVS_SIZING_MODES}, "
                f"got {self.mode!r}"
            )

    @property
    def label(self) -> str:
        """Human-readable row-name suffix, e.g. ``[asym_long L=2.0]``.

        For un-levered modes (``binary``, ``long_flat``) the leverage knob is
        meaningless, so the label omits it.
        """
        if self.mode in _GSVIVS_UNLEVERED_MODES:
            return f"[{self.mode}]"
        return f"[{self.mode} L={self.max_leverage:g}]"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to YAML-friendly dict (round-trips with :meth:`from_dict`)."""
        return {"mode": self.mode, "max_leverage": self.max_leverage, "lookback": self.lookback}

    @classmethod
    def from_dict(cls, raw: Any) -> GsvivsSizingSpec:
        """Build a spec from a YAML node.

        Accepts either:
          * a string shorthand — just the mode name; leverage/lookback default
          * a dict with ``mode`` (required) and optional ``max_leverage`` /
            ``lookback``
        """
        if isinstance(raw, str):
            return cls(mode=raw)
        if not isinstance(raw, dict):
            raise TypeError(
                f"GsvivsSizingSpec.from_dict expected str or dict, got {type(raw).__name__}"
            )
        if "mode" not in raw:
            raise ValueError("GsvivsSizingSpec dict requires a 'mode' key")
        kwargs: dict[str, Any] = {"mode": raw["mode"]}
        if "max_leverage" in raw:
            kwargs["max_leverage"] = float(raw["max_leverage"])
        if "lookback" in raw:
            kwargs["lookback"] = int(raw["lookback"])
        return cls(**kwargs)


# The 4-mode toggle surfaced in the GSVIVS dashboard table by default.
# Order matters: it is preserved in the rendered output (binary first as the
# reference baseline, then the recommended asym_long, then zscore, then
# long_flat as the long-side-only variant of binary).
DEFAULT_GSVIVS_SIZING_SPECS: tuple[GsvivsSizingSpec, ...] = (
    GsvivsSizingSpec(mode="binary"),
    GsvivsSizingSpec(mode="asym_long", max_leverage=2.0, lookback=63),
    GsvivsSizingSpec(mode="zscore", max_leverage=1.0, lookback=63),
    GsvivsSizingSpec(mode="long_flat"),
)


def parse_gsvivs_sizing_specs(raw: Any) -> tuple[GsvivsSizingSpec, ...]:
    """Parse a YAML list-of-specs into a tuple of GsvivsSizingSpec.

    ``None`` (key absent) returns the project default 3-mode list. An empty
    list is an explicit "no sizing variants" — returns an empty tuple.
    """
    if raw is None:
        return DEFAULT_GSVIVS_SIZING_SPECS
    if not isinstance(raw, list):
        raise TypeError(
            f"gsvivs_sizings must be a list, got {type(raw).__name__}"
        )
    return tuple(GsvivsSizingSpec.from_dict(item) for item in raw)



def _kvar_gap_for_sized(
    kvar: np.ndarray,
    rv_forecast: np.ndarray,
    *,
    space: str,
    is_calendar_ann: bool,
) -> np.ndarray:
    """Shared gap computation for sized signals (mirrors kvar_rv_gap_signal)."""
    kvar = np.asarray(kvar, dtype=np.float64)
    rv_forecast = np.asarray(rv_forecast, dtype=np.float64)
    if is_calendar_ann:
        _cal_to_trading = np.sqrt(252.0 / 365.0)
        kvar_decimal = kvar / 100.0 * _cal_to_trading
    else:
        kvar_decimal = kvar / 100.0
    if space == "vol":
        return kvar_decimal - rv_forecast
    if space == "variance":
        return kvar_decimal**2 - rv_forecast**2
    raise ValueError(f"space must be 'vol' or 'variance', got {space!r}")


def _rolling_std_expanding(gap: np.ndarray, lookback: int) -> np.ndarray:
    """Rolling std (ddof=1) over prior `lookback` observations, expanding when
    history is shorter. NaN values in the window are dropped before std.
    Std is returned as 1.0 for indices with <2 valid prior observations
    (avoids divide-by-zero and keeps the gap on its original scale)."""
    n = len(gap)
    out = np.full(n, 1.0)
    for i in range(1, n):
        lo = max(0, i - lookback)
        window = gap[lo:i]
        valid = window[~np.isnan(window)]
        if len(valid) < 2:
            continue
        s = float(np.std(valid, ddof=1))
        out[i] = s if s > 1e-12 else 1.0
    return out


def kvar_rv_sized_signal(
    kvar: np.ndarray,
    rv_forecast: np.ndarray,
    *,
    sizing_mode: str = DEFAULT_GSVIVS_SIZING_MODE,
    space: str = "vol",
    threshold: float = 0.0,
    is_calendar_ann: bool = True,
    max_leverage: float = 2.0,
    lookback: int = 63,
) -> np.ndarray:
    """Generate GSVIVS01 trading signal with configurable position sizing.

    Four sizing modes (the first three are empirically selected from sizing
    analysis workspace/tmp/sizing_*.csv on champion LightGBM predictions,
    2026-06-15; ``long_flat`` was added 2026-06-16 as a long-only variant of
    binary):

    - ``"binary"`` — bit-for-bit reproduction of :func:`kvar_rv_gap_signal`.
      Status quo, kept for backwards compatibility.
    - ``"asym_long"`` (default) — long side scales by clipped rolling-z-score in
      [+1, +max_leverage]; short side fixed at -1. Winner of the leaderboard
      (+30 to +41 bps Sharpe vs binary on h=1 SPY). Asymmetric because the
      signal's short-side conviction is unreliable: amplifying it consistently
      destroys Sharpe across every leverage tested.
    - ``"zscore"`` — symmetric clipped rolling-z-score in [-max_leverage,
      +max_leverage]. Drawdown-averse alternative: halves max DD vs binary
      and posts the tightest bootstrap CI lower bound, at the cost of lower
      absolute return.
    - ``"long_flat"`` — long-only variant of binary. Wherever binary would
      emit -1 (sell vol), this mode emits 0 (flat) instead. Output is in
      {0, +1}. Use when shorts are infeasible (no borrow/financing) or when
      the user wants to harvest only the long-side carry without taking the
      drawdown profile of a short-vol overlay. Ignores ``max_leverage`` and
      ``lookback``.

    Sharpe is invariant under uniform scaling, so the benefit of any sized
    mode comes from VARYING size with edge — confirmed empirically by the
    monotonic top-bucket calibration of the champion model.

    Parameters
    ----------
    kvar : np.ndarray
        Execution Kvar in vol points (365-calendar annualized by default).
    rv_forecast : np.ndarray
        RV forecast in annualized decimal (252-trading-day).
    sizing_mode : {"binary", "asym_long", "zscore", "long_flat"}
        Sizing scheme. Default ``"asym_long"``.
    space : {"vol", "variance"}
        Gap formulation. See :func:`kvar_rv_gap_signal`.
    threshold : float
        Dead-band threshold for binary mode (ignored by sized modes — they
        always position).
    is_calendar_ann : bool
        If True, kvar is converted from 365-day to 252-day annualization.
    max_leverage : float
        Position-size cap. Default 2.0 (per empirical recommendation).
    lookback : int
        Rolling window for z-score normalization. Default 63 trading days.

    Returns
    -------
    np.ndarray
        Position sizes. ``binary`` → {-1, +1}; ``asym_long`` → [-1, +max_leverage];
        ``zscore`` → [-max_leverage, +max_leverage]; ``long_flat`` → {0, +1}.
        NaN kvar defaults to +1 for ``binary``/``asym_long``/``long_flat``
        (matches kvar_rv_gap_signal contract) and 0 for ``zscore`` (no
        informed sizing → flat).
    """
    if sizing_mode not in GSVIVS_SIZING_MODES:
        raise ValueError(
            f"sizing_mode must be one of {GSVIVS_SIZING_MODES}, got {sizing_mode!r}"
        )

    if sizing_mode == "binary":
        return kvar_rv_gap_signal(
            kvar,
            rv_forecast,
            space=space,
            threshold=threshold,
            is_calendar_ann=is_calendar_ann,
        )

    if sizing_mode == "long_flat":
        # Long-only variant of binary: replace every -1 with 0 so the
        # strategy goes flat on what would have been short days. The +1 long
        # entries (including the NaN-default-long contract) carry through
        # unchanged.
        binary = kvar_rv_gap_signal(
            kvar,
            rv_forecast,
            space=space,
            threshold=threshold,
            is_calendar_ann=is_calendar_ann,
        )
        return np.where(binary > 0, 1.0, 0.0)

    gap = _kvar_gap_for_sized(
        kvar, rv_forecast, space=space, is_calendar_ann=is_calendar_ann
    )
    std = _rolling_std_expanding(gap, lookback=lookback)
    # Z-score with NaN-safe denominator. NaN gap stays NaN here; resolved per-mode.
    z = gap / std

    if sizing_mode == "zscore":
        out = np.clip(z, -max_leverage, max_leverage)
        # NaN gap → no informed sizing → flat
        out[np.isnan(z)] = 0.0
        return out

    # asym_long: short side fixed at -1, long side scales from +1 up to L.
    out = np.zeros_like(gap)
    nan_mask = np.isnan(z)
    long_mask = (~nan_mask) & (z > 0)
    short_mask = (~nan_mask) & (z <= 0)
    # Default-long contract for NaN kvar matches kvar_rv_gap_signal.
    out[nan_mask] = 1.0
    out[long_mask] = np.clip(z[long_mask], 1.0, max_leverage)
    out[short_mask] = -1.0
    return out


def delta_hedged_straddle_pnl(
    signal: np.ndarray,
    realized_var: np.ndarray,
    implied_vol: np.ndarray,
    spot_prices: np.ndarray,
    tenor_days: int = 30,
    cost_vol_points: float = 0.5,
    holding_period: int = 22,
) -> np.ndarray:
    """Compute daily P&L of delta-hedged straddle strategy.

    Uses the gamma P&L formula from Black-Scholes:
        PnL_t = direction_t * 0.5 * Gamma_t * S_t^2 * (RV_t - IV^2) * dt

    ATM straddle gamma (call + put):
        Gamma_t = 2 / (S_t * IV_t * sqrt(T))

    Transaction cost: `cost_vol_points` per leg (2 legs for straddle),
    amortized over the holding period.

    Parameters
    ----------
    signal : np.ndarray
        Trading signals: +1 (sell vol), -1 (buy vol), 0 (flat).
    realized_var : np.ndarray
        Daily realized variance (not annualized). E.g. sum of squared
        5-min returns for the day.
    implied_vol : np.ndarray
        ATM implied volatility (annualized decimal, e.g. 0.18 for 18%).
    spot_prices : np.ndarray
        Underlying spot prices.
    tenor_days : int
        Option tenor in trading days (default: 30, matching 1m ATM IV).
    cost_vol_points : float
        Transaction cost per option leg in vol points (default: 0.5).
    holding_period : int
        Days to amortize entry cost (default: 22 trading days).

    Returns
    -------
    np.ndarray
        Daily P&L as fraction of notional (spot^2 normalized out).
    """
    signal = np.asarray(signal, dtype=np.float64)
    realized_var = np.asarray(realized_var, dtype=np.float64)
    implied_vol = np.asarray(implied_vol, dtype=np.float64)
    spot_prices = np.asarray(spot_prices, dtype=np.float64)

    dt = 1.0 / 252.0
    T = tenor_days / 252.0

    # ATM straddle gamma: 2 / (S * IV * sqrt(T))
    iv_safe = np.maximum(implied_vol, 1e-8)
    gamma = 2.0 / (spot_prices * iv_safe * np.sqrt(T))

    # Daily gamma P&L: 0.5 * Gamma * S^2 * (realized_var_daily - iv^2 * dt)
    # realized_var is daily RV (not annualized), iv^2 * dt = annualized var * dt
    daily_implied_var = iv_safe**2 * dt
    raw_pnl = 0.5 * gamma * spot_prices**2 * (realized_var - daily_implied_var)

    # Direction: sell vol (signal=+1) profits when RV < IV (negate raw_pnl)
    # Buy vol (signal=-1) profits when RV > IV (keep raw_pnl sign)
    # Convention: raw_pnl > 0 means long-gamma profits. Signal=+1 means short.
    directed_pnl = -signal * raw_pnl

    # Normalize by spot to get "return on notional" (dollar P&L / spot)
    pnl_normalized = directed_pnl / np.maximum(spot_prices, 1e-8)

    # Transaction cost: cost_vol_points per leg, 2 legs, amortized over holding period.
    # Vega per ATM option ~ S * sqrt(T) * N'(0), where N'(0) ~ 0.3989.
    # Dollar cost per day = 2 * (cost_bps * vega) / holding_period.
    # Normalized by S this becomes:
    vega_norm = np.sqrt(T) * 0.3989  # vega/S for one ATM option
    daily_cost_norm = 2.0 * (cost_vol_points / 100.0) * vega_norm / holding_period
    cost_drag = np.abs(signal) * daily_cost_norm
    pnl_net = pnl_normalized - cost_drag

    return pnl_net


def vol_targeting_pnl(
    returns: np.ndarray,
    vol_forecast: np.ndarray,
    target_vol: float = 0.10,
    max_leverage: float = 2.0,
) -> np.ndarray:
    """Compute P&L of vol-targeting portfolio.

    Scales position size inversely with predicted volatility:
    w_t = min(target_vol / vol_forecast_t, max_leverage).

    Parameters
    ----------
    returns : np.ndarray
        Daily asset returns (simple or log).
    vol_forecast : np.ndarray
        Daily volatility forecasts (annualized, decimal).
    target_vol : float
        Target annualized volatility (default: 10%).
    max_leverage : float
        Maximum leverage cap (default: 2x).

    Returns
    -------
    np.ndarray
        Daily portfolio returns.
    """
    returns = np.asarray(returns, dtype=np.float64)
    vol_forecast = np.asarray(vol_forecast, dtype=np.float64)

    # Avoid division by zero: floor vol_forecast at a small positive value
    vol_safe = np.maximum(vol_forecast, 1e-8)
    weights = np.minimum(target_vol / vol_safe, max_leverage)
    return weights * returns


def compute_sharpe(
    returns: np.ndarray,
    risk_free_rate: float = 0.0,
    annualization: int = 252,
) -> float:
    """Compute annualized Sharpe ratio.

    Parameters
    ----------
    returns : np.ndarray
        Daily returns.
    risk_free_rate : float
        Annual risk-free rate (default: 0).
    annualization : int
        Trading days per year (default: 252).

    Returns
    -------
    float
        Annualized Sharpe ratio.
    """
    returns = np.asarray(returns, dtype=np.float64)
    if len(returns) < 2:
        return 0.0
    # Drop NaN values (e.g. from shift(-1) last obs per symbol in pooled arrays)
    valid = ~np.isnan(returns)
    returns = returns[valid]
    if len(returns) < 2:
        return 0.0
    daily_rf = risk_free_rate / annualization
    excess = returns - daily_rf
    std = np.std(excess, ddof=1)
    if std < 1e-12:
        return 0.0
    return float(np.mean(excess) / std * np.sqrt(annualization))


def compute_max_drawdown(cumulative_returns: np.ndarray) -> float:
    """Compute maximum drawdown from cumulative returns.

    Parameters
    ----------
    cumulative_returns : np.ndarray
        Cumulative wealth series (1 + r_1)(1 + r_2)...

    Returns
    -------
    float
        Maximum drawdown (negative number, e.g., -0.15 for 15% drawdown).
    """
    cumulative_returns = np.asarray(cumulative_returns, dtype=np.float64)
    if len(cumulative_returns) < 2:
        return 0.0
    peak = np.maximum.accumulate(cumulative_returns)
    drawdown = (cumulative_returns - peak) / np.maximum(peak, 1e-12)
    return float(np.min(drawdown))


def vol_targeting_sharpe(
    log_rv_predictions: np.ndarray,
    daily_returns: np.ndarray,
    target_vol: float = 0.10,
    max_leverage: float = 2.0,
) -> float:
    """Compute vol-targeting Sharpe from log-RV predictions and daily returns.

    Converts log-RV forecast to annualized vol, computes position weights,
    and returns the annualized Sharpe of the resulting strategy.

    Parameters
    ----------
    log_rv_predictions : np.ndarray
        Model's OOS predictions in log(RV) space (daily RV, not annualized).
    daily_returns : np.ndarray
        Daily log-returns of the underlying asset, aligned to predictions.
    target_vol : float
        Target annualized volatility (default: 10%).
    max_leverage : float
        Maximum leverage cap (default: 2x).

    Returns
    -------
    float
        Annualized Sharpe ratio of the vol-targeting strategy.
    """
    log_rv_predictions = np.asarray(log_rv_predictions, dtype=np.float64)
    daily_returns = np.asarray(daily_returns, dtype=np.float64)

    # Convert log-RV (daily) to annualized vol: sigma = sqrt(252 * exp(log_rv))
    daily_rv = np.exp(log_rv_predictions)
    annualized_vol = np.sqrt(252.0 * daily_rv)

    portfolio_returns = vol_targeting_pnl(
        daily_returns, annualized_vol, target_vol=target_vol, max_leverage=max_leverage
    )
    return compute_sharpe(portfolio_returns)


def delta_hedged_sharpe(
    log_rv_predictions: np.ndarray,
    implied_vol: np.ndarray,
    realized_var: np.ndarray,
    spot_prices: np.ndarray,
    threshold: float = 0.0,
    tenor_days: int = 30,
    cost_vol_points: float = 0.5,
    holding_period: int = 22,
) -> dict[str, float]:
    """Compute delta-hedged straddle metrics from log-RV predictions and IV.

    Converts predictions to annualized vol, computes the IV-RV gap signal,
    and backtests the delta-hedged straddle strategy.

    Parameters
    ----------
    log_rv_predictions : np.ndarray
        Model's OOS predictions in log(RV) space (daily RV, not annualized).
    implied_vol : np.ndarray
        ATM implied volatility (annualized decimal, e.g. 0.18 for 18%).
        Aligned to predictions.
    realized_var : np.ndarray
        Actual daily realized variance (not annualized), aligned to predictions.
    spot_prices : np.ndarray
        Underlying spot prices, aligned to predictions.
    threshold : float
        Signal threshold (annualized vol units, default: 0).
    tenor_days : int
        Option tenor in trading days (default: 30).
    cost_vol_points : float
        Per-leg cost in vol points (default: 0.5).
    holding_period : int
        Cost amortization period (default: 22 days).

    Returns
    -------
    dict[str, float]
        Keys: dh_sharpe, dh_pnl (cum % return), dh_max_dd (%), dh_hit_rate.
    """
    log_rv_predictions = np.asarray(log_rv_predictions, dtype=np.float64)
    implied_vol = np.asarray(implied_vol, dtype=np.float64)
    realized_var = np.asarray(realized_var, dtype=np.float64)
    spot_prices = np.asarray(spot_prices, dtype=np.float64)

    # Convert log-RV to annualized vol for signal comparison with IV
    forecast_ann_vol = np.sqrt(252.0 * np.exp(log_rv_predictions))

    # Generate signal: compare IV to forecasted vol
    signal = iv_rv_gap_signal(implied_vol, forecast_ann_vol, threshold=threshold)

    # Compute daily P&L
    pnl = delta_hedged_straddle_pnl(
        signal,
        realized_var,
        implied_vol,
        spot_prices,
        tenor_days=tenor_days,
        cost_vol_points=cost_vol_points,
        holding_period=holding_period,
    )

    # Metrics
    valid = ~np.isnan(pnl)
    pnl_clean = np.where(valid, pnl, 0.0)

    sharpe = compute_sharpe(pnl_clean)
    # Additive P&L: fixed-notional straddle, profits are summed not compounded
    cum_curve = np.cumsum(pnl_clean)
    cum_pnl = float(cum_curve[-1] * 100) if len(cum_curve) > 0 else 0.0
    # Max drawdown on cumulative-sum curve
    peak = np.maximum.accumulate(cum_curve)
    dd = cum_curve - peak  # negative values = drawdown
    max_dd = float(np.min(dd) * 100) if len(dd) > 0 else 0.0

    # Hit rate: fraction of active days with positive P&L
    active = np.abs(signal) > 0
    if active.any():
        hit_rate = float(np.mean(pnl_clean[active] > 0))
    else:
        hit_rate = 0.0

    # Annualized return and vol (additive P&L: mean*252, std*sqrt(252))
    ann_ret = float(np.mean(pnl_clean) * 252 * 100) if len(pnl_clean) > 1 else 0.0
    ann_vol = float(np.std(pnl_clean, ddof=1) * np.sqrt(252) * 100) if len(pnl_clean) > 1 else 0.0

    return {
        "dh_sharpe": sharpe,
        "dh_pnl": cum_pnl,
        "dh_max_dd": max_dd,
        "dh_hit_rate": hit_rate,
        "dh_ann_ret": ann_ret,
        "dh_ann_vol": ann_vol,
    }


def discrete_delta_hedged_sharpe(
    log_rv_predictions: np.ndarray,
    implied_vol: np.ndarray,
    realized_var: np.ndarray,
    spot_prices: np.ndarray,
    threshold: float = 0.0,
    tenor_days: int = 30,
    cost_vol_points: float = 0.5,
    holding_period: int = 22,
    rebalances_per_day: int = 26,
    spread_bps: float = 2.0,
) -> dict[str, float]:
    """Compute delta-hedged straddle metrics with discrete 15-min hedging.

    Same gamma P&L formula as simple mode, but adds the expected
    underlying hedge transaction cost from rebalancing delta every 15
    minutes (26 times/day) with a 15-minute lag. Each rebalance incurs
    a round-trip spread on the shares traded.

    Parameters
    ----------
    log_rv_predictions : np.ndarray
        Model's OOS predictions in log(RV) space (daily RV, not annualized).
    implied_vol : np.ndarray
        ATM implied volatility (annualized decimal, e.g. 0.18 for 18%).
    realized_var : np.ndarray
        Actual daily realized variance (not annualized).
    spot_prices : np.ndarray
        Underlying spot prices.
    threshold : float
        Signal threshold (annualized vol units, default: 0).
    tenor_days : int
        Option tenor in trading days (default: 30).
    cost_vol_points : float
        Per-leg option cost in vol points (default: 0.5).
    holding_period : int
        Option cost amortization period (default: 22 days).
    rebalances_per_day : int
        Number of discrete hedge rebalances per day (default: 26 = every 15 min).
    spread_bps : float
        Round-trip underlying spread in basis points (default: 2.0).

    Returns
    -------
    dict[str, float]
        Keys: dh_sharpe, dh_pnl, dh_max_dd, dh_hit_rate, dh_ann_ret, dh_ann_vol.
    """
    log_rv_predictions = np.asarray(log_rv_predictions, dtype=np.float64)
    implied_vol = np.asarray(implied_vol, dtype=np.float64)
    realized_var = np.asarray(realized_var, dtype=np.float64)
    spot_prices = np.asarray(spot_prices, dtype=np.float64)

    # Convert log-RV to annualized vol for signal comparison with IV
    forecast_ann_vol = np.sqrt(252.0 * np.exp(log_rv_predictions))

    # Generate signal
    signal = iv_rv_gap_signal(implied_vol, forecast_ann_vol, threshold=threshold)

    # Compute daily P&L (gamma P&L + option cost, same as simple mode)
    pnl = delta_hedged_straddle_pnl(
        signal,
        realized_var,
        implied_vol,
        spot_prices,
        tenor_days=tenor_days,
        cost_vol_points=cost_vol_points,
        holding_period=holding_period,
    )

    # Add underlying hedge cost: each rebalance trades |Δδ| shares at spread.
    # E[|Δδ|] per rebalance = Γ * S * σ * √(1/(252*N)) * √(2/π)
    # Daily cost = N * E[|Δδ|] * S * spread_bps / 10000
    T = tenor_days / 252.0
    iv_safe = np.maximum(implied_vol, 1e-8)
    gamma = 2.0 / (spot_prices * iv_safe * np.sqrt(T))

    dt_rebal = 1.0 / (252.0 * rebalances_per_day)
    sqrt_2_pi = np.sqrt(2.0 / np.pi)
    exp_abs_dd = gamma * spot_prices * iv_safe * np.sqrt(dt_rebal) * sqrt_2_pi
    daily_hedge_cost = rebalances_per_day * exp_abs_dd * spot_prices * (spread_bps / 10000.0)
    # Normalize by spot (same units as pnl)
    hedge_cost_norm = daily_hedge_cost / np.maximum(spot_prices, 1e-8)

    # Subtract hedge cost (only on active days)
    pnl_net = pnl - np.abs(signal) * hedge_cost_norm

    # Metrics
    valid = ~np.isnan(pnl_net)
    pnl_clean = np.where(valid, pnl_net, 0.0)

    sharpe = compute_sharpe(pnl_clean)
    cum_curve = np.cumsum(pnl_clean)
    cum_pnl = float(cum_curve[-1] * 100) if len(cum_curve) > 0 else 0.0
    peak = np.maximum.accumulate(cum_curve)
    dd = cum_curve - peak
    max_dd = float(np.min(dd) * 100) if len(dd) > 0 else 0.0

    # Hit rate
    active = np.abs(signal) > 0
    hit_rate = float(np.mean(pnl_clean[active] > 0)) if active.any() else 0.0

    # Annualized return and vol
    ann_ret = float(np.mean(pnl_clean) * 252 * 100) if len(pnl_clean) > 1 else 0.0
    ann_vol = float(np.std(pnl_clean, ddof=1) * np.sqrt(252) * 100) if len(pnl_clean) > 1 else 0.0

    return {
        "dh_sharpe": sharpe,
        "dh_pnl": cum_pnl,
        "dh_max_dd": max_dd,
        "dh_hit_rate": hit_rate,
        "dh_ann_ret": ann_ret,
        "dh_ann_vol": ann_vol,
    }


def economic_value_summary(
    signal: np.ndarray,
    realized_vol: np.ndarray,
    implied_vol: np.ndarray,
    spot_prices: np.ndarray,
    daily_returns: np.ndarray,
    vol_forecast: np.ndarray,
    model_name: str = "",
) -> dict[str, float]:
    """Generate comprehensive economic value report.

    Parameters
    ----------
    signal : np.ndarray
        IV-RV gap trading signals.
    realized_vol : np.ndarray
        Actual realized volatility.
    implied_vol : np.ndarray
        Implied volatility.
    spot_prices : np.ndarray
        Underlying spot prices.
    daily_returns : np.ndarray
        Daily asset returns.
    vol_forecast : np.ndarray
        Volatility forecasts for vol-targeting.
    model_name : str
        Model identifier for labeling.

    Returns
    -------
    dict[str, float]
        Keys: straddle_sharpe, straddle_max_dd, vol_target_sharpe,
        vol_target_max_dd, hit_rate, avg_pnl_per_trade.
    """
    daily_returns = np.asarray(daily_returns, dtype=np.float64)
    vol_forecast = np.asarray(vol_forecast, dtype=np.float64)

    # Vol-targeting metrics
    vt_returns = vol_targeting_pnl(daily_returns, vol_forecast)
    vt_sharpe = compute_sharpe(vt_returns)
    vt_cumulative = np.cumprod(1.0 + vt_returns)
    vt_max_dd = compute_max_drawdown(vt_cumulative)

    result = {
        "model": model_name,
        "vol_target_sharpe": vt_sharpe,
        "vol_target_max_dd": vt_max_dd,
    }

    # IV-RV gap metrics (only if IV data available)
    if signal is not None and implied_vol is not None and realized_vol is not None:
        signal = np.asarray(signal, dtype=np.float64)
        implied_vol = np.asarray(implied_vol, dtype=np.float64)
        realized_vol = np.asarray(realized_vol, dtype=np.float64)
        spot_prices = np.asarray(spot_prices, dtype=np.float64)

        dh_pnl = delta_hedged_straddle_pnl(signal, realized_vol, implied_vol, spot_prices)
        result["straddle_sharpe"] = compute_sharpe(dh_pnl)
        # Additive P&L: fixed-notional straddle, cumsum not cumprod
        cum_curve = np.cumsum(dh_pnl)
        peak = np.maximum.accumulate(cum_curve)
        result["straddle_max_dd"] = float(np.min(cum_curve - peak))
        active_days = np.abs(signal) > 0
        if active_days.any():
            result["hit_rate"] = float(np.mean(dh_pnl[active_days] > 0))
        else:
            result["hit_rate"] = 0.0

    return result


# ---------------------------------------------------------------------------
# Naive DH baselines (always-long, always-short, flat, random)
# ---------------------------------------------------------------------------


def naive_dh_baselines(
    realized_var: np.ndarray,
    implied_vol: np.ndarray,
    spot_prices: np.ndarray,
    dh_mode: str = "simple",
    seed: int = 42,
) -> dict[str, dict[str, float]]:
    """Compute delta-hedged straddle metrics for naive signal baselines.

    These baselines bypass the IV-RV gap signal and use fixed/random positions:
    - always_long: signal = +1 (always sell vol / short straddle)
    - always_short: signal = -1 (always buy vol / long straddle)
    - always_flat: signal = 0 (no position — sanity check)
    - random: signal = random {+1, -1} per day (fixed seed for reproducibility)

    Parameters
    ----------
    realized_var : np.ndarray
        Daily realized variance (not annualized).
    implied_vol : np.ndarray
        ATM implied volatility (annualized decimal).
    spot_prices : np.ndarray
        Underlying spot prices.
    dh_mode : str
        One of "simple", "discrete", "realistic".
    seed : int
        Random seed for the random baseline (default: 42).

    Returns
    -------
    dict[str, dict[str, float]]
        Mapping baseline name -> metrics dict with keys:
        dh_sharpe, dh_pnl, dh_max_dd, dh_hit_rate, dh_ann_ret, dh_ann_vol.
    """
    realized_var = np.asarray(realized_var, dtype=np.float64)
    implied_vol = np.asarray(implied_vol, dtype=np.float64)
    spot_prices = np.asarray(spot_prices, dtype=np.float64)
    n = len(realized_var)

    rng = np.random.default_rng(seed)
    random_signal = rng.choice([-1.0, 1.0], size=n)

    signals = {
        "always_long": np.ones(n, dtype=np.float64),
        "always_short": np.full(n, -1.0, dtype=np.float64),
        "always_flat": np.zeros(n, dtype=np.float64),
        "random": random_signal,
    }

    results = {}
    pnl_cache: dict[str, np.ndarray] = {}
    for name, signal in signals.items():
        pnl_clean, hedge_error_var = _compute_naive_pnl(
            signal, realized_var, implied_vol, spot_prices, dh_mode
        )
        results[name] = _pnl_to_metrics(pnl_clean, signal, hedge_error_var)
        pnl_cache[name] = pnl_clean

    # random_no_flip: average of always_long and always_short PnL
    # (random direction without the flip-cost artifact)
    avg_pnl = 0.5 * (pnl_cache["always_long"] + pnl_cache["always_short"])
    avg_signal = np.ones(n, dtype=np.float64)  # always active for hit_rate
    results["random_no_flip"] = _pnl_to_metrics(avg_pnl, avg_signal, None)

    return results


def _compute_naive_pnl(
    signal: np.ndarray,
    realized_var: np.ndarray,
    implied_vol: np.ndarray,
    spot_prices: np.ndarray,
    dh_mode: str,
    tenor_days: int = 30,
) -> tuple[np.ndarray, np.ndarray | None]:
    """Compute daily PnL for a fixed signal vector using the specified DH mode.

    Returns
    -------
    tuple[np.ndarray, np.ndarray | None]
        (pnl_clean, hedge_error_var). hedge_error_var is always returned
        (Boyle-Emanuel discrete hedging error) for an honest Sharpe denominator.
    """
    from volforecast.evaluation.realistic_straddle import compute_hedge_error_variance

    T = tenor_days / 252.0
    iv_safe = np.maximum(implied_vol, 1e-8)
    gamma = 2.0 / (spot_prices * iv_safe * np.sqrt(T))

    if dh_mode == "simple":
        pnl = delta_hedged_straddle_pnl(
            signal,
            realized_var,
            implied_vol,
            spot_prices,
        )
        # Boyle-Emanuel hedge error variance (kappa=4, N=26 rebalances/day)
        hedge_error_var = compute_hedge_error_variance(
            gamma,
            spot_prices,
            implied_vol,
            kappa=4.0,
            N=26,
        )
        hedge_error_var = hedge_error_var * signal**2
    elif dh_mode == "discrete":
        # Same as simple + hedge cost add-on
        pnl = delta_hedged_straddle_pnl(
            signal,
            realized_var,
            implied_vol,
            spot_prices,
        )
        # Add underlying hedge cost (mirrors discrete_delta_hedged_sharpe logic)
        rebalances_per_day = 26
        spread_bps = 2.0
        dt_rebal = 1.0 / (252.0 * rebalances_per_day)
        sqrt_2_pi = np.sqrt(2.0 / np.pi)
        exp_abs_dd = gamma * spot_prices * iv_safe * np.sqrt(dt_rebal) * sqrt_2_pi
        daily_hedge_cost = rebalances_per_day * exp_abs_dd * spot_prices * (spread_bps / 10000.0)
        hedge_cost_norm = daily_hedge_cost / np.maximum(spot_prices, 1e-8)
        pnl = pnl - np.abs(signal) * hedge_cost_norm
        # Boyle-Emanuel hedge error variance
        hedge_error_var = compute_hedge_error_variance(
            gamma,
            spot_prices,
            implied_vol,
            kappa=4.0,
            N=26,
        )
        hedge_error_var = hedge_error_var * signal**2
    elif dh_mode == "realistic":
        from volforecast.evaluation.realistic_straddle import realistic_straddle_pnl

        delta_spot = np.zeros(len(spot_prices))
        delta_spot[1:] = np.diff(spot_prices)
        delta_iv = np.zeros(len(implied_vol))
        delta_iv[1:] = np.diff(implied_vol)

        result = realistic_straddle_pnl(
            signal=signal,
            realized_var=realized_var,
            implied_vol=implied_vol,
            spot_prices=spot_prices,
            delta_spot=delta_spot,
            delta_iv=delta_iv,
            tenor_days=tenor_days,
        )
        pnl = result["pnl_net"]
        hedge_error_var = result["hedge_error_var"]
    else:
        pnl = delta_hedged_straddle_pnl(
            signal,
            realized_var,
            implied_vol,
            spot_prices,
            tenor_days=tenor_days,
        )

    valid = ~np.isnan(pnl)
    pnl_clean = np.where(valid, pnl, 0.0)
    return pnl_clean, hedge_error_var


def _pnl_to_metrics(
    pnl_clean: np.ndarray,
    signal: np.ndarray,
    hedge_error_var: np.ndarray | None = None,
    per_symbol_pnl_parts: list[np.ndarray] | None = None,
) -> dict[str, float]:
    """Convert a daily PnL series + signal into the standard DH metrics dict.

    If hedge_error_var is provided, dh_sharpe uses the adjusted denominator
    (inflated by hedge error variance per Boyle-Emanuel 1980).

    If per_symbol_pnl_parts is provided (list of per-symbol PnL arrays),
    cum P&L and max DD are computed per-symbol then averaged.
    """
    if hedge_error_var is not None and len(hedge_error_var) == len(pnl_clean):
        # Adjusted Sharpe: inflate std with hedge error variance
        observed_var = np.var(pnl_clean, ddof=1)
        mean_he_var = float(np.mean(hedge_error_var))
        total_std = np.sqrt(observed_var + mean_he_var)
        mean_pnl = float(np.mean(pnl_clean))
        sharpe = float(mean_pnl / total_std * np.sqrt(252.0)) if total_std > 1e-12 else 0.0
        ann_vol = float(total_std * np.sqrt(252) * 100) if len(pnl_clean) > 1 else 0.0
    else:
        sharpe = compute_sharpe(pnl_clean)
        ann_vol = (
            float(np.std(pnl_clean, ddof=1) * np.sqrt(252) * 100) if len(pnl_clean) > 1 else 0.0
        )

    cum_curve = np.cumsum(pnl_clean)
    cum_pnl = float(cum_curve[-1] * 100) if len(cum_curve) > 0 else 0.0
    peak = np.maximum.accumulate(cum_curve)
    dd = cum_curve - peak
    max_dd = float(np.min(dd) * 100) if len(dd) > 0 else 0.0

    # If per-symbol PnL parts provided, average cum PnL and max DD across symbols
    if per_symbol_pnl_parts is not None and len(per_symbol_pnl_parts) > 1:
        sym_cum_pnls = []
        sym_max_dds = []
        for sym_arr in per_symbol_pnl_parts:
            sc = np.cumsum(sym_arr)
            sym_cum_pnls.append(float(sc[-1] * 100))
            sp = np.maximum.accumulate(sc)
            sym_max_dds.append(float(np.min(sc - sp) * 100))
        cum_pnl = float(np.mean(sym_cum_pnls))
        max_dd = float(np.mean(sym_max_dds))

    active = np.abs(signal) > 0
    hit_rate = float(np.mean(pnl_clean[active] > 0)) if active.any() else 0.0

    ann_ret = float(np.mean(pnl_clean) * 252 * 100) if len(pnl_clean) > 1 else 0.0

    return {
        "dh_sharpe": sharpe,
        "dh_pnl": cum_pnl,
        "dh_max_dd": max_dd,
        "dh_hit_rate": hit_rate,
        "dh_ann_ret": ann_ret,
        "dh_ann_vol": ann_vol,
    }


# ---------------------------------------------------------------------------
# GSVIVS01 Variance Swap Signal Backtest
# ---------------------------------------------------------------------------


def gsvivs_signal_pnl(
    index_levels: np.ndarray,
    signal: np.ndarray,
) -> dict[str, float | str]:
    """Compute performance metrics for signal applied to GSVIVS01 index returns.

    Daily PnL = signal_t * (Index_{t+1} / Index_t - 1).

    Parameters
    ----------
    index_levels : np.ndarray
        Daily GSVIVS01 index levels (absolute values, not returns).
    signal : np.ndarray
        Trading signal array {-1, 0, +1}. Same length as index_levels.
        +1 = go long the short-vol index, -1 = go short it.

    Returns
    -------
    dict[str, float | str]
        Performance metrics:
        - sharpe_0rf: Annualized Sharpe (0% risk-free rate)
        - sharpe_5rf: Annualized Sharpe (5% risk-free rate)
        - ann_return: Annualized return (%)
        - ann_vol: Annualized volatility (%)
        - total_return: Cumulative return (%)
        - max_drawdown: Maximum drawdown (%, negative number)
        - positive_days: String "X/Y (Z%)"
        - hit_rate: Fraction of active days with positive PnL
        - precision: TP / (TP + FP) where positive class = long (+1)
        - recall: TP / (TP + FN) where positive class = long (+1)
        - f1: Harmonic mean of precision and recall
    """
    index_levels = np.asarray(index_levels, dtype=np.float64)
    signal = np.asarray(signal, dtype=np.float64)

    # Daily index returns (length n-1)
    daily_returns = index_levels[1:] / index_levels[:-1] - 1.0

    # Signal at t determines position for the t->t+1 return
    daily_pnl = signal[:-1] * daily_returns

    # Handle all-zero signal
    if np.all(np.abs(signal) < 1e-12):
        return {
            "sharpe_0rf": 0.0,
            "sharpe_5rf": 0.0,
            "ann_return": 0.0,
            "ann_vol": 0.0,
            "total_return": 0.0,
            "max_drawdown": 0.0,
            "positive_days": "0/0 (0.0%)",
            "hit_rate": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "mcc": 0.0,
            "flat_pct": 100.0,
        }

    # Annualized metrics
    mean_daily = float(np.mean(daily_pnl))
    std_daily = float(np.std(daily_pnl, ddof=1)) if len(daily_pnl) > 1 else 1e-12

    ann_return = mean_daily * 252 * 100
    ann_vol = std_daily * np.sqrt(252) * 100
    sharpe_0rf = (mean_daily / std_daily * np.sqrt(252)) if std_daily > 1e-12 else 0.0
    sharpe_5rf = (mean_daily - 0.05 / 252) / std_daily * np.sqrt(252) if std_daily > 1e-12 else 0.0

    # Cumulative return (compound)
    cum_wealth = np.cumprod(1.0 + daily_pnl)
    total_return = float((cum_wealth[-1] - 1.0) * 100)

    # Max drawdown
    peak = np.maximum.accumulate(cum_wealth)
    drawdown = (cum_wealth - peak) / peak
    max_drawdown = float(np.min(drawdown) * 100)

    # Hit rate (fraction of active days with positive PnL)
    active = np.abs(signal[:-1]) > 1e-12
    n_active = int(active.sum())
    n_pos_days = int(np.sum(daily_pnl[active] > 0)) if n_active > 0 else 0
    hit_rate = n_pos_days / n_active if n_active > 0 else 0.0

    # Precision / Recall / F1 (positive class = "not long", drawdown detection)
    # For binary signals {-1, +1}: "not long" = short (-1)
    # For long_flat signals {0, +1}: "not long" = flat (0)
    # For zscore/asym_long: "not long" = non-positive exposure
    # The classification question is: did we correctly avoid being long on a
    # down day? Threshold at 0 so any non-positive position counts as protective.
    # TP: not-long and index went down (correctly predicted drawdown)
    # FP: not-long and index went up (false alarm)
    # FN: long and index went down (missed a drawdown)
    # TN: long and index went up (correctly stayed long)
    sig = signal[:-1]
    short_mask = sig <= 0    # "not long": covers -1 (short), 0 (flat), negative fractional
    long_mask = sig > 0
    index_down = daily_returns < 0

    tp = float(np.sum(short_mask & index_down))
    fp = float(np.sum(short_mask & ~index_down))
    fn = float(np.sum(long_mask & index_down))

    tn = float(np.sum(long_mask & ~index_down))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # Matthews Correlation Coefficient
    mcc_denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = (tp * tn - fp * fn) / mcc_denom if mcc_denom > 0 else 0.0

    # Positive days — always use total evaluation days as denominator so all
    # models (including long_flat with varying flat-day counts) display against
    # the same base, making the comparison visually unambiguous.
    n_total = len(daily_pnl)
    n_pos_days_total = int(np.sum(daily_pnl > 0))
    pos_days_pct = n_pos_days_total / n_total * 100 if n_total > 0 else 0.0
    positive_days = f"{n_pos_days_total}/{n_total} ({pos_days_pct:.1f}%)"

    # Flat %: fraction of days signal is zero (flat / no position)
    n_flat = int(np.sum(np.abs(signal[:-1]) < 1e-12))
    flat_pct = n_flat / n_total * 100 if n_total > 0 else 0.0

    return {
        "sharpe_0rf": float(sharpe_0rf),
        "sharpe_5rf": float(sharpe_5rf),
        "ann_return": float(ann_return),
        "ann_vol": float(ann_vol),
        "total_return": float(total_return),
        "max_drawdown": float(max_drawdown),
        "positive_days": positive_days,
        "hit_rate": float(hit_rate),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "mcc": float(mcc),
        "flat_pct": float(flat_pct),
    }


def gsvivs_baseline_signals(n: int, seed: int = 42) -> dict[str, np.ndarray]:
    """Build the canonical set of GSVIVS01 baseline signal arrays of length n.

    Returns a mapping {baseline_name: signal_array}. Keeping signal generation
    in one place lets callers (metrics, equity curves, dashboards) share the
    same seed and definitions.
    """
    rng_random = np.random.default_rng(seed)
    rng_65 = np.random.default_rng(seed)
    return {
        "always_long": np.ones(n),
        "always_short": -np.ones(n),
        "always_random": rng_random.choice([-1.0, 1.0], size=n),
        "random_long_65": rng_65.choice([1.0, -1.0], size=n, p=[0.65, 0.35]),
    }


def gsvivs_baselines(
    index_levels: np.ndarray,
    seed: int = 42,
) -> dict[str, dict[str, float | str]]:
    """Compute GSVIVS01 metrics for passive baselines (always-long/short/random).

    Parameters
    ----------
    index_levels : np.ndarray
        Daily GSVIVS01 index levels.
    seed : int
        Random seed for the random baseline (default: 42).

    Returns
    -------
    dict[str, dict[str, float | str]]
        Mapping baseline name -> metrics dict.
    """
    index_levels = np.asarray(index_levels, dtype=np.float64)
    signals = gsvivs_baseline_signals(len(index_levels), seed=seed)
    return {name: gsvivs_signal_pnl(index_levels, sig) for name, sig in signals.items()}


# ---------------------------------------------------------------------------
# Args-file CLI — BACKTEST skill entry point (Plan 03 / AW-05).
# Mirrors the cli/*.py handle() shape: argv in, int out, sentinel out_file.
# Invoke: python -m volforecast.evaluation.economic_value --args-file <json>
# ---------------------------------------------------------------------------

_CLI_REQUIRED = ("vol_forecast", "daily_returns")
_CLI_OPTIONAL = ("realized_vol", "implied_vol", "spot", "signal")


def _cli_series(df: Any, columns: dict[str, str], key: str) -> np.ndarray | None:
    """Pull one mapped column as float64, or None if unmapped."""
    name = columns.get(key)
    if name is None:
        return None
    if name not in df.columns:
        raise KeyError(f"columns.{key} -> {name!r} not found in CSV")
    return df[name].to_numpy(dtype=np.float64)


def main(argv: list[str] | None = None) -> int:
    """Args-file CLI entry point (see module docstring of the companion test)."""
    import argparse
    import json
    import sys
    from pathlib import Path

    import pandas as pd

    parser = argparse.ArgumentParser(
        prog="volforecast.evaluation.economic_value",
        description="Economic-value backtest from a predictions CSV (BACKTEST skill).",
    )
    parser.add_argument("--args-file", required=True, type=Path)
    ns = parser.parse_args(argv)

    if not ns.args_file.is_file():
        print(f"ERROR: args file not found: {ns.args_file}", file=sys.stderr)
        return 1

    spec = json.loads(ns.args_file.read_text(encoding="utf-8"))
    out_file = Path(spec["out_file"])
    rc = 0
    try:
        columns: dict[str, str] = spec["columns"]
        df = pd.read_csv(Path(spec["csv"]))
        series = {k: _cli_series(df, columns, k) for k in (*_CLI_REQUIRED, *_CLI_OPTIONAL)}
        missing = [k for k in _CLI_REQUIRED if series[k] is None]
        if missing:
            raise KeyError(f"required columns mapping missing: {missing}")
        result = economic_value_summary(
            signal=series["signal"],  # type: ignore[arg-type]
            realized_vol=series["realized_vol"],  # type: ignore[arg-type]
            implied_vol=series["implied_vol"],  # type: ignore[arg-type]
            spot_prices=series["spot"],  # type: ignore[arg-type]
            daily_returns=series["daily_returns"],  # type: ignore[arg-type]
            vol_forecast=series["vol_forecast"],  # type: ignore[arg-type]
            model_name=spec.get("model_name", ""),
        )
        body = json.dumps(result, indent=2, default=float)
    except Exception as exc:  # noqa: BLE001 — every failure must reach the sentinel file
        rc = 1
        body = json.dumps({"error": f"{type(exc).__name__}: {exc}"})

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(f"{body}\nEXIT_CODE={rc}\n", encoding="utf-8")
    print(f"OUTPUT_FILE={out_file}")
    return rc


if __name__ == "__main__":  # pragma: no cover
    import sys

    sys.exit(main())
