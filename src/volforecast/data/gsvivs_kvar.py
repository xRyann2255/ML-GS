"""Extract true execution Kvar from GSVIVS01 output.json.

Parses option fill prices from the strategy's trade records and applies the
CBOE discrete variance swap formula to compute the exact Kvar sold each day.

Public API:
    parse_day_opening_legs  — Extract opening leg fills for a single day record
    parse_day_transaction_costs — Extract option and futures transaction-cost cash
    compute_kvar_from_legs  — Apply CBOE formula to a set of (strike, price) pairs
    extract_all_exec_kvar   — End-to-end: load output.json → DataFrame of daily Kvar
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _compute_delta_k(strikes: np.ndarray) -> np.ndarray:
    """Discrete strike spacing using the standard midpoint rule."""
    n = len(strikes)
    delta_k = np.zeros(n, dtype=np.float64)
    for i in range(n):
        if i == 0:
            delta_k[i] = strikes[1] - strikes[0]
        elif i == n - 1:
            delta_k[i] = strikes[-1] - strikes[-2]
        else:
            delta_k[i] = (strikes[i + 1] - strikes[i - 1]) / 2.0
    return delta_k


def _infer_replication_scale(strikes: np.ndarray, quantities: np.ndarray) -> tuple[float, float]:
    """Infer the strip scale N from |q_i| ≈ N * ΔK_i / K_i².

    Returns
    -------
    tuple[float, float]
        (replication_scale, coefficient_of_variation_of_scale_ratios)
    """
    delta_k = _compute_delta_k(strikes)
    weights = delta_k / strikes**2
    abs_qty = np.abs(quantities)

    valid = (weights > 0) & (abs_qty > 0)
    if valid.sum() < 3:
        return 0.0, np.inf

    scale_ratios = abs_qty[valid] / weights[valid]
    scale = float(np.median(scale_ratios))
    mean_ratio = float(np.mean(scale_ratios))
    if mean_ratio <= 0:
        return 0.0, np.inf
    cv = float(np.std(scale_ratios) / mean_ratio)
    return scale, cv


def parse_day_opening_legs(
    risks: list[dict],
) -> list[dict]:
    """Extract opening option legs with execution prices from a day's risks list.

    Each VSR 0b trade has an `instrument` dict containing the option definition
    (strike, type, expiry) directly. The next entry in the list is the execution
    fill with `execution price` (space-separated key).

    Parameters
    ----------
    risks : list[dict]
        The `risks for date` list from one day record in output.json.

    Returns
    -------
    list[dict]
        Each dict: {strike, option_type, exec_price, quantity}
        Only includes opening option legs (source=VSR 0b, qty < 0).
    """
    legs: list[dict] = []

    i = 0
    while i < len(risks):
        entry = risks[i]

        # Found a VSR 0b opening trade (selling the strip)
        if (
            entry.get("source") == "VSR 0b"
            and isinstance(entry.get("quantity"), (int, float))
            and entry["quantity"] < 0
        ):
            # The instrument field contains the option def directly
            instr = entry.get("instrument")
            if isinstance(instr, dict) and "k" in instr:
                # The next entry is the execution fill
                if i + 1 < len(risks):
                    exec_entry = risks[i + 1]
                    # Field name has a space: "execution price"
                    exec_price = exec_entry.get(
                        "execution price", exec_entry.get("execution_price")
                    )
                    if exec_price is not None:
                        option_type = instr.get("option type", "")
                        # Skip Forward-type entries (synthetic, not traded)
                        if option_type in ("Put", "Call"):
                            legs.append(
                                {
                                    "strike": instr["k"],
                                    "option_type": option_type,
                                    "exec_price": exec_price,
                                    "quantity": entry["quantity"],
                                }
                            )
                i += 2  # Skip past the exec entry
                continue

        i += 1

    return legs


def parse_day_transaction_costs(risks: list[dict]) -> dict[str, float]:
    """Extract transaction-cost cash lines from a day's risks list.

    The raw JSON books option and futures transaction costs as separate cash
    entries with zero execution price. Quantities are already in index-point
    cash units.
    """
    option_tc_cash = 0.0
    futures_tc_cash = 0.0

    i = 0
    while i < len(risks):
        entry = risks[i]
        source = entry.get("source")
        if source in ("Transaction Costs O", "Transactions Costs Fw"):
            cash = float(entry.get("quantity", 0.0) or 0.0)
            if source == "Transaction Costs O":
                option_tc_cash += cash
            else:
                futures_tc_cash += cash
            i += 2
            continue
        i += 1

    return {
        "option_tc_cash": option_tc_cash,
        "futures_tc_cash": futures_tc_cash,
        "all_tc_cash": option_tc_cash + futures_tc_cash,
    }


def parse_day_trade_cashflows(risks: list[dict]) -> dict[str, float]:
    """Decompose daily trading cash into option open/close and futures hedge cash."""
    option_open_cash = 0.0
    option_close_cash = 0.0
    futures_hedge_cash = 0.0

    i = 0
    while i < len(risks):
        entry = risks[i]
        source = entry.get("source")
        if source not in ("VSR 0b", "Intraday Delta Hedge"):
            i += 1
            continue

        exec_entry = risks[i + 1] if i + 1 < len(risks) else {}
        quantity = float(entry.get("quantity", 0.0) or 0.0)
        exec_price = float(
            exec_entry.get("execution price", exec_entry.get("execution_price", 0.0)) or 0.0
        )
        cash = -quantity * exec_price
        instrument = entry.get("instrument", {})

        if source == "Intraday Delta Hedge" or instrument.get("instrument type") == "F":
            futures_hedge_cash += cash
        elif quantity < 0:
            option_open_cash += cash
        else:
            option_close_cash += cash

        i += 2

    return {
        "option_open_cash": option_open_cash,
        "option_close_cash": option_close_cash,
        "futures_hedge_cash": futures_hedge_cash,
    }


# Default T: 24 hours so the extracted IV is on the same daily horizon as
# the empirical RV series used downstream in IV-RV comparisons.
# Calendar-year convention (hours / 8760) to match EDRVS/CBOE units.
_T_0DTE_DEFAULT = 24.0 / 8760.0


def compute_kvar_from_legs(
    legs: list[dict],
    forward: float,
    T: float = _T_0DTE_DEFAULT,
    r: float = 0.05,
    tc_cash: float = 0.0,
) -> dict | None:
    """Compute execution Kvar from opening leg fills using the CBOE formula.

    Parameters
    ----------
    legs : list[dict]
        Output of parse_day_opening_legs. Each has: strike, option_type, exec_price.
    forward : float
        Forward price (from risk node or inferred from put/call boundary).
    T : float
        Time to expiry in years (calendar-year convention: hours / 8760).
        Default: 24 hours / 8760 = ~0.002740 years.
    r : float
        Risk-free rate (annualized). Effect is negligible at 0-DTE T.

    Returns
    -------
    dict or None
        Includes gross and friction-adjusted Kvar estimates plus diagnostics.
        or None if insufficient data.
    """
    if len(legs) < 3:
        return None

    # Sort by strike
    sorted_legs = sorted(legs, key=lambda x: x["strike"])
    strikes = np.array([leg["strike"] for leg in sorted_legs])
    prices = np.array([leg["exec_price"] for leg in sorted_legs])
    quantities = np.array([leg["quantity"] for leg in sorted_legs])

    n = len(strikes)

    # Compute delta_K (midpoint rule)
    delta_K = _compute_delta_k(strikes)

    # For each strike, use the OTM option price:
    # - Put if K < F
    # - Call if K >= F
    # The execution prices should already be OTM prices based on the strip
    # construction, but we verify using the forward.
    # At ATM: both put and call may appear — use whichever is in the data.
    Q = np.zeros(n)
    for i in range(n):
        Q[i] = prices[i]

    # K0 = first strike at or below forward. If none, use nearest strike.
    below_fwd = strikes[strikes <= forward]
    if len(below_fwd) == 0:
        # All strikes above forward — use the closest one
        K0 = strikes[np.argmin(np.abs(strikes - forward))]
    else:
        K0 = below_fwd[-1]

    # CBOE formula
    discount = np.exp(r * T)
    curve_variance = (2.0 / T) * np.sum(delta_K / strikes**2 * discount * Q)

    # Forward correction term
    correction = (1.0 / T) * (forward / K0 - 1.0) ** 2
    curve_variance = curve_variance - correction

    # Quantity-aware cash inference. For a variance strip, |q_i| should be
    # proportional to ΔK_i / K_i² with a common strip scale N.
    replication_scale, weight_fit_cv = _infer_replication_scale(strikes, quantities)
    gross_premium_cash = float(np.sum(-quantities * prices))

    if replication_scale > 0:
        cash_gross_variance = (2.0 / T) * discount * (
            gross_premium_cash / replication_scale
        ) - correction
        cash_net_variance = (2.0 / T) * discount * (
            (gross_premium_cash + tc_cash) / replication_scale
        ) - correction
    else:
        cash_gross_variance = np.nan
        cash_net_variance = np.nan

    if not np.isfinite(cash_net_variance) and curve_variance <= 0:
        return None

    if np.isfinite(cash_net_variance) and cash_net_variance > 0:
        kvar_variance_ann = float(cash_net_variance)
    elif curve_variance > 0:
        kvar_variance_ann = float(curve_variance)
    else:
        return None

    kvar_vol = np.sqrt(kvar_variance_ann)
    kvar_vol_pct = kvar_vol * 100.0

    curve_kvar_vol_pct = float(np.sqrt(curve_variance) * 100.0) if curve_variance > 0 else np.nan
    cash_gross_kvar_vol_pct = (
        float(np.sqrt(cash_gross_variance) * 100.0)
        if np.isfinite(cash_gross_variance) and cash_gross_variance > 0
        else np.nan
    )
    cash_net_kvar_vol_pct = (
        float(np.sqrt(cash_net_variance) * 100.0)
        if np.isfinite(cash_net_variance) and cash_net_variance > 0
        else np.nan
    )

    strip_width_pct = (strikes[-1] - strikes[0]) / forward * 100.0

    return {
        "kvar_vol_pct": kvar_vol_pct,
        "kvar_variance_ann": kvar_variance_ann,
        "kvar_curve_vol_pct": curve_kvar_vol_pct,
        "kvar_curve_variance_ann": float(curve_variance) if curve_variance > 0 else np.nan,
        "kvar_cash_gross_vol_pct": cash_gross_kvar_vol_pct,
        "kvar_cash_gross_variance_ann": float(cash_gross_variance)
        if np.isfinite(cash_gross_variance) and cash_gross_variance > 0
        else np.nan,
        "kvar_cash_net_vol_pct": cash_net_kvar_vol_pct,
        "kvar_cash_net_variance_ann": float(cash_net_variance)
        if np.isfinite(cash_net_variance) and cash_net_variance > 0
        else np.nan,
        "gross_premium_cash": gross_premium_cash,
        "net_premium_cash": gross_premium_cash + tc_cash,
        "replication_scale": replication_scale,
        "weight_fit_cv": weight_fit_cv,
        "tc_cash": tc_cash,
        "forward": forward,
        "n_strikes": n,
        "strip_width_pct": strip_width_pct,
    }


def _infer_forward_from_legs(legs: list[dict]) -> float | None:
    """Infer the forward price from the put/call boundary in the strip.

    The forward is at the ATM strike where both a put and call exist,
    or the midpoint between the highest put strike and lowest call strike.
    This is more reliable than risk node fwd which can be from wrong expiry.
    """
    if not legs:
        return None

    sorted_legs = sorted(legs, key=lambda x: x["strike"])
    put_strikes = [l["strike"] for l in sorted_legs if l["option_type"] == "Put"]
    call_strikes = [l["strike"] for l in sorted_legs if l["option_type"] == "Call"]

    if not put_strikes or not call_strikes:
        # All one type — can't infer forward, use midpoint of strip
        all_strikes = [l["strike"] for l in sorted_legs]
        return (all_strikes[0] + all_strikes[-1]) / 2.0

    # Check for ATM strike (both put and call present)
    put_set = set(put_strikes)
    call_set = set(call_strikes)
    atm_strikes = put_set & call_set
    if atm_strikes:
        return float(max(atm_strikes))  # Use the highest ATM strike

    # Otherwise, midpoint between highest put and lowest call
    return (max(put_strikes) + min(call_strikes)) / 2.0


def _find_forward_for_day(
    risks: list[dict], trade_date: str, legs: list[dict] | None = None
) -> float | None:
    """Find the forward price for today's 0-DTE expiry.

    Strategy:
    1. Infer from legs (put/call boundary) — most reliable
    2. Risk node fwd for today's expiry — fallback
    3. Any risk node fwd — last resort
    """
    # Best: infer from the traded strip itself
    if legs:
        inferred = _infer_forward_from_legs(legs)
        if inferred is not None:
            return inferred

    # Fallback: risk node for today's expiry
    last_option_expiry: str | None = None
    for entry in risks:
        if "ex" in entry:
            last_option_expiry = entry["ex"]
        elif "baseline risks" in entry:
            br = entry["baseline risks"]
            fwd = br.get("fwd")
            if fwd and fwd > 0 and last_option_expiry == trade_date:
                return float(fwd)

    # Last resort: any non-None fwd
    for entry in risks:
        if "baseline risks" in entry:
            br = entry["baseline risks"]
            fwd = br.get("fwd")
            if fwd and fwd > 0:
                return float(fwd)

    return None


def extract_all_exec_kvar(
    json_path: str | Path,
    T: float = _T_0DTE_DEFAULT,
    r: float = 0.05,
) -> pd.DataFrame:
    """Extract execution Kvar for all days from output.json.

    Parameters
    ----------
    json_path : str or Path
        Path to output.json.
    T : float
        Time horizon in calendar-year fraction for IV-RV comparison.
        Default: 24h / 8760 so extracted IV is comparable to daily RV.
    r : float
        Risk-free rate.

    Returns
    -------
    pd.DataFrame
        Columns: trade_date, kvar_vol_pct, kvar_variance_ann, forward,
        n_strikes, strip_width_pct.
    """
    import json

    json_path = Path(json_path)
    with open(json_path) as f:
        data = json.load(f)

    results: list[dict] = []

    for day_record in data:
        trade_date = day_record.get("date")
        if not trade_date:
            continue

        value = day_record.get("value", {})
        risks = value.get("risks for date", [])
        if not risks:
            continue

        # Parse opening legs
        legs = parse_day_opening_legs(risks)
        if len(legs) < 3:
            logger.debug("Day %s: only %d opening legs, skipping", trade_date, len(legs))
            continue

        # Find forward (use legs for reliable put/call boundary inference)
        forward = _find_forward_for_day(risks, trade_date, legs=legs)
        if forward is None:
            logger.warning("Day %s: no forward found, skipping", trade_date)
            continue

        tc = parse_day_transaction_costs(risks)
        cashflows = parse_day_trade_cashflows(risks)

        # Compute gross, option-TC-adjusted, and full-friction effective Kvar.
        gross_result = compute_kvar_from_legs(legs, forward, T=T, r=r, tc_cash=0.0)
        option_tc_result = compute_kvar_from_legs(
            legs, forward, T=T, r=r, tc_cash=tc["option_tc_cash"]
        )
        full_result = compute_kvar_from_legs(legs, forward, T=T, r=r, tc_cash=tc["all_tc_cash"])

        result = full_result
        if result is None:
            logger.warning("Day %s: Kvar computation failed (negative variance)", trade_date)
            continue

        result["kvar_gross_vol_pct"] = (
            gross_result["kvar_vol_pct"] if gross_result is not None else np.nan
        )
        result["kvar_gross_variance_ann"] = (
            gross_result["kvar_variance_ann"] if gross_result is not None else np.nan
        )
        result["kvar_option_tc_vol_pct"] = (
            option_tc_result["kvar_vol_pct"] if option_tc_result is not None else np.nan
        )
        result["kvar_option_tc_variance_ann"] = (
            option_tc_result["kvar_variance_ann"] if option_tc_result is not None else np.nan
        )
        result["option_tc_cash"] = tc["option_tc_cash"]
        result["futures_tc_cash"] = tc["futures_tc_cash"]
        result["all_tc_cash"] = tc["all_tc_cash"]
        result.update(cashflows)
        result["full_day_pnl_cash"] = (
            cashflows["option_open_cash"]
            + cashflows["option_close_cash"]
            + cashflows["futures_hedge_cash"]
            + tc["all_tc_cash"]
        )
        result["trade_date"] = trade_date
        results.append(result)

    if not results:
        return pd.DataFrame(
            columns=[
                "trade_date",
                "kvar_vol_pct",
                "kvar_variance_ann",
                "forward",
                "n_strikes",
                "strip_width_pct",
            ]
        )

    df = pd.DataFrame(results)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.set_index("trade_date").sort_index()
    return df
