"""Phase 3: Evaluation rigor experiments (Steps 16-19).

Runs the four Ch18 experiments that validate the realistic DH straddle:
- Step 16: Cost-band Sharpe (timing-aware / effective / quoted)
- Step 17: Statistical-to-economic link (P&L regression on gap + error)
- Step 18: Sharpe aggregation + deflation + bootstrap CI
- Step 19: Hedging-error floor (a/N + b fit) + kappa sensitivity

References:
    - Muravyev & Pearson (2020): option cost bands
    - Bailey & Lopez de Prado (2014): deflated Sharpe ratio
    - Broden & Tankov (2010): jump floor in hedging error
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Step 16: Cost-band Sharpe experiment
# ---------------------------------------------------------------------------


def run_cost_band_experiment(
    pnl_gross: np.ndarray,
    gamma: np.ndarray,
    spot: np.ndarray,
    iv: np.ndarray,
    T_rem_days: np.ndarray,
    spread_bps: float = 2.0,
    rebalances: int = 26,
) -> dict[str, float | bool]:
    """Run cost-band Sharpe experiment (Ch18 Exp #2).

    Computes Sharpe at three cost levels with maturity adjustment:
    - timing_aware (0.5 vol pts): optimistic, 1/6 of quoted
    - effective (1.0 vol pts): empirically grounded
    - quoted (1.5 vol pts): pessimistic, full half-spread

    Parameters
    ----------
    pnl_gross : np.ndarray
        Gross P&L before option cost (gamma + vanna + volga - hedge cost).
    gamma : np.ndarray
        Straddle gamma per day.
    spot : np.ndarray
        Spot prices.
    iv : np.ndarray
        ATM implied vol (annualized).
    T_rem_days : np.ndarray
        Remaining tenor in trading days.
    spread_bps : float
        Underlying spread for hedge cost.
    rebalances : int
        Rebalances per day.

    Returns
    -------
    dict
        Keys: timing_aware, effective, quoted (Sharpe ratios),
        pass_effective (bool: SR > 0.5 at effective level).
    """
    from volforecast.evaluation.realistic_straddle import cost_band_sharpes

    result = cost_band_sharpes(
        pnl_gross,
        gamma,
        spot,
        iv,
        T_rem_days,
        spread_bps=spread_bps,
        rebalances=rebalances,
    )

    result["pass_effective"] = result.get("effective", 0.0) > 0.5
    return result


# ---------------------------------------------------------------------------
# Step 17: Statistical-to-economic link
# ---------------------------------------------------------------------------


def statistical_economic_link(
    pnl: np.ndarray,
    realized_var: np.ndarray,
    iv: np.ndarray,
    forecast_var: np.ndarray,
) -> dict[str, float]:
    """Regress P&L on realized gap and forecast error (Ch18 Exp #3).

    Model: PnL_t = alpha + beta_gap * gap_t + beta_error * error_t + eps_t

    where:
        gap_t = RV_t - IV_t^2/252  (realized volatility gap)
        error_t = RV_t - RV_hat_t  (forecast error)

    Parameters
    ----------
    pnl : np.ndarray
        Daily P&L series.
    realized_var : np.ndarray
        Daily realized variance.
    iv : np.ndarray
        ATM implied vol (annualized decimal).
    forecast_var : np.ndarray
        Forecasted daily variance.

    Returns
    -------
    dict
        Keys: alpha, beta_gap, beta_error, t_alpha, t_gap, t_error,
        r_squared, n_obs.
    """
    pnl = np.asarray(pnl, dtype=np.float64)
    realized_var = np.asarray(realized_var, dtype=np.float64)
    iv = np.asarray(iv, dtype=np.float64)
    forecast_var = np.asarray(forecast_var, dtype=np.float64)

    # Construct regressors
    iv_var_daily = iv**2 / 252.0
    gap = realized_var - iv_var_daily
    error = realized_var - forecast_var

    # OLS: y = X @ beta
    n = len(pnl)
    X = np.column_stack([np.ones(n), gap, error])
    y = pnl

    # Solve via normal equations
    XtX = X.T @ X
    Xty = X.T @ y

    # Add small ridge for numerical stability
    XtX_reg = XtX + 1e-12 * np.eye(3)
    beta = np.linalg.solve(XtX_reg, Xty)

    # Residuals and variance
    residuals = y - X @ beta
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1.0 - ss_res / max(ss_tot, 1e-20)

    # Standard errors (HAC would be better but OLS is sufficient for testing)
    dof = max(n - 3, 1)
    sigma2 = ss_res / dof
    cov_beta = sigma2 * np.linalg.inv(XtX_reg)
    se = np.sqrt(np.maximum(np.diag(cov_beta), 1e-20))

    t_stats = beta / se

    return {
        "alpha": float(beta[0]),
        "beta_gap": float(beta[1]),
        "beta_error": float(beta[2]),
        "t_alpha": float(t_stats[0]),
        "t_gap": float(t_stats[1]),
        "t_error": float(t_stats[2]),
        "r_squared": float(r_squared),
        "n_obs": n,
    }


# ---------------------------------------------------------------------------
# Step 18: Sharpe aggregation + deflation + bootstrap
# ---------------------------------------------------------------------------


def compute_sharpe_aggregation(
    pnl_by_symbol: dict[str, np.ndarray],
    N_trials: int = 10,
    n_bootstrap: int = 1000,
    bootstrap_seed: int = 42,
) -> dict:
    """Compute pooled and per-symbol Sharpe with DSR and bootstrap CI.

    Parameters
    ----------
    pnl_by_symbol : dict[str, np.ndarray]
        Daily P&L series per symbol.
    N_trials : int
        Number of strategy configurations tested (for DSR).
    n_bootstrap : int
        Number of bootstrap replications.
    bootstrap_seed : int
        Seed for bootstrap.

    Returns
    -------
    dict
        Keys: pooled_sharpe, per_symbol_sharpes, mean_per_symbol_sharpe,
        dsr, bootstrap_ci, n_obs.
    """
    from volforecast.evaluation.economic_value import compute_sharpe
    from volforecast.evaluation.realistic_straddle import (
        block_bootstrap_ci,
        deflated_sharpe_ratio,
    )

    # Pooled: concatenate all symbol P&L
    all_pnl = np.concatenate(list(pnl_by_symbol.values()))
    pooled_sharpe = compute_sharpe(all_pnl)

    # Per-symbol Sharpe
    per_symbol = {}
    for symbol, pnl in pnl_by_symbol.items():
        per_symbol[symbol] = compute_sharpe(pnl)
    mean_per_symbol = float(np.mean(list(per_symbol.values())))

    # DSR for pooled
    pnl_std = np.std(all_pnl, ddof=1)
    if pnl_std > 1e-12:
        mean_pnl = np.mean(all_pnl)
        standardized = (all_pnl - mean_pnl) / pnl_std
        skewness = float(np.mean(standardized**3))
        kurtosis = float(np.mean(standardized**4))
    else:
        skewness = 0.0
        kurtosis = 3.0

    dsr = deflated_sharpe_ratio(
        observed_sharpe=pooled_sharpe,
        T=len(all_pnl),
        skewness=skewness,
        kurtosis=kurtosis,
        N_trials=N_trials,
    )

    # Block-bootstrap CI
    ci_low, ci_high = block_bootstrap_ci(
        all_pnl,
        n_bootstrap=n_bootstrap,
        block_size=5,
        seed=bootstrap_seed,
    )

    return {
        "pooled_sharpe": pooled_sharpe,
        "per_symbol_sharpes": per_symbol,
        "mean_per_symbol_sharpe": mean_per_symbol,
        "dsr": dsr,
        "bootstrap_ci": (ci_low, ci_high),
        "n_obs": len(all_pnl),
    }


# ---------------------------------------------------------------------------
# Step 19: Hedging-error floor + kappa sensitivity
# ---------------------------------------------------------------------------


def run_hedging_error_floor_experiment(
    variances_by_n: dict[int, float],
    threshold: float = 0.1,
) -> dict[str, float | bool]:
    """Fit Var(hedge_error) = a/N + b and detect jump floor (Ch18 Exp #1).

    Parameters
    ----------
    variances_by_n : dict[int, float]
        Measured hedge error variance at each rebalance frequency N.
    threshold : float
        Threshold for b to be considered "material" (fraction of mean variance).

    Returns
    -------
    dict
        Keys: a, b, jump_floor_detected (bool), r_squared.
    """
    from volforecast.evaluation.discrete_straddle import (
        hedging_error_floor_experiment,
    )

    n_values = sorted(variances_by_n.keys())
    variances = [variances_by_n[n] for n in n_values]

    a, b = hedging_error_floor_experiment(n_values, variances)

    # Detect jump floor: b > threshold * mean(variances)
    mean_var = np.mean(variances)
    jump_floor_detected = bool(b > threshold * mean_var)

    # R-squared of fit
    x = np.array([1.0 / n for n in n_values])
    y = np.array(variances)
    y_pred = a * x + b
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1.0 - ss_res / max(ss_tot, 1e-20) if ss_tot > 1e-20 else 0.0

    return {
        "a": a,
        "b": b,
        "jump_floor_detected": jump_floor_detected,
        "r_squared": r_squared,
    }


def run_kappa_sensitivity(
    pnl: np.ndarray,
    gamma: np.ndarray,
    spot: np.ndarray,
    iv: np.ndarray,
    signal: np.ndarray,
    N_trials: int = 10,
    rebalances: int = 26,
) -> dict[str, dict[str, float]]:
    """Report DSR stability across kappa values (Ch18 Exp #1 extension).

    Parameters
    ----------
    pnl : np.ndarray
        Net P&L series.
    gamma : np.ndarray
        Straddle gamma.
    spot : np.ndarray
        Spot prices.
    iv : np.ndarray
        Implied vol.
    signal : np.ndarray
        Trading signal (for weighting hedge error).
    N_trials : int
        Number of strategies tested (for DSR).
    rebalances : int
        Rebalances per day.

    Returns
    -------
    dict
        Keys: kappa_3, kappa_4, kappa_6, each containing
        sharpe_adjusted and dsr.
    """
    from volforecast.evaluation.realistic_straddle import (
        compute_hedge_error_variance,
        deflated_sharpe_ratio,
    )

    pnl = np.asarray(pnl, dtype=np.float64)
    gamma = np.asarray(gamma, dtype=np.float64)
    spot = np.asarray(spot, dtype=np.float64)
    iv = np.asarray(iv, dtype=np.float64)
    signal = np.asarray(signal, dtype=np.float64)

    observed_var = np.var(pnl, ddof=1)
    mean_pnl = np.mean(pnl)

    result = {}
    for kappa in [3.0, 4.0, 6.0]:
        he_var = compute_hedge_error_variance(gamma, spot, iv, kappa=kappa, N=rebalances)
        he_var_weighted = he_var * signal**2
        total_std = np.sqrt(observed_var + np.mean(he_var_weighted))

        sharpe_adj = float(mean_pnl / total_std * np.sqrt(252.0)) if total_std > 1e-12 else 0.0

        # DSR
        pnl_std = np.std(pnl, ddof=1)
        if pnl_std > 1e-12:
            standardized = (pnl - mean_pnl) / pnl_std
            skewness = float(np.mean(standardized**3))
            kurtosis_stat = float(np.mean(standardized**4))
        else:
            skewness = 0.0
            kurtosis_stat = 3.0

        dsr = deflated_sharpe_ratio(
            observed_sharpe=sharpe_adj,
            T=len(pnl),
            skewness=skewness,
            kurtosis=kurtosis_stat,
            N_trials=N_trials,
        )

        result[f"kappa_{int(kappa)}"] = {
            "sharpe_adjusted": sharpe_adj,
            "dsr": dsr,
        }

    return result


# ---------------------------------------------------------------------------
# Combined report generator
# ---------------------------------------------------------------------------


def generate_phase3_report(
    pnl_by_symbol: dict[str, np.ndarray],
    realized_var: np.ndarray,
    iv: np.ndarray,
    forecast_var: np.ndarray,
    gamma: np.ndarray,
    spot: np.ndarray,
    T_rem: np.ndarray,
    signal: np.ndarray,
    N_trials: int = 10,
    n_bootstrap: int = 1000,
    spread_bps: float = 2.0,
    rebalances: int = 26,
) -> dict:
    """Generate complete Phase 3 evaluation report.

    Runs all four experiments and assembles results.

    Parameters
    ----------
    pnl_by_symbol : dict[str, np.ndarray]
        Daily P&L series per symbol.
    realized_var : np.ndarray
        Realized variance (pooled/representative).
    iv : np.ndarray
        ATM implied vol (annualized).
    forecast_var : np.ndarray
        Forecasted daily variance.
    gamma : np.ndarray
        Straddle gamma.
    spot : np.ndarray
        Spot prices.
    T_rem : np.ndarray
        Remaining tenor in days.
    signal : np.ndarray
        Trading signal.
    N_trials : int
        Number of strategy configs tested.
    n_bootstrap : int
        Bootstrap replications.
    spread_bps : float
        Underlying spread.
    rebalances : int
        Rebalances per day.

    Returns
    -------
    dict
        Keys: cost_band, stat_econ_link, sharpe_aggregation, kappa_sensitivity.
    """
    # Use pooled P&L for cost-band and kappa experiments
    all_pnl = np.concatenate(list(pnl_by_symbol.values()))

    # For experiments that need matched-length arrays, truncate to shortest
    n_common = min(len(all_pnl), len(gamma), len(spot), len(iv), len(T_rem))
    pnl_common = all_pnl[:n_common]
    gamma_c = (
        gamma[:n_common]
        if len(gamma) >= n_common
        else np.pad(gamma, (0, n_common - len(gamma)), constant_values=gamma[-1])
    )
    spot_c = (
        spot[:n_common]
        if len(spot) >= n_common
        else np.pad(spot, (0, n_common - len(spot)), constant_values=spot[-1])
    )
    iv_c = (
        iv[:n_common]
        if len(iv) >= n_common
        else np.pad(iv, (0, n_common - len(iv)), constant_values=iv[-1])
    )
    T_rem_c = (
        T_rem[:n_common]
        if len(T_rem) >= n_common
        else np.pad(T_rem, (0, n_common - len(T_rem)), constant_values=T_rem[-1])
    )
    signal_c = (
        signal[:n_common]
        if len(signal) >= n_common
        else np.pad(signal, (0, n_common - len(signal)), constant_values=signal[-1])
    )

    # Step 16: Cost-band
    cost_band = run_cost_band_experiment(
        pnl_gross=pnl_common,
        gamma=gamma_c,
        spot=spot_c,
        iv=iv_c,
        T_rem_days=T_rem_c,
        spread_bps=spread_bps,
        rebalances=rebalances,
    )

    # Step 17: Statistical-to-economic link
    n_stat = min(len(all_pnl), len(realized_var), len(iv), len(forecast_var))
    stat_econ = statistical_economic_link(
        pnl=all_pnl[:n_stat],
        realized_var=realized_var[:n_stat],
        iv=iv[:n_stat],
        forecast_var=forecast_var[:n_stat],
    )

    # Step 18: Sharpe aggregation + deflation
    sharpe_agg = compute_sharpe_aggregation(
        pnl_by_symbol=pnl_by_symbol,
        N_trials=N_trials,
        n_bootstrap=n_bootstrap,
    )

    # Step 19: Kappa sensitivity
    kappa_sens = run_kappa_sensitivity(
        pnl=pnl_common,
        gamma=gamma_c,
        spot=spot_c,
        iv=iv_c,
        signal=signal_c,
        N_trials=N_trials,
        rebalances=rebalances,
    )

    return {
        "cost_band": cost_band,
        "stat_econ_link": stat_econ,
        "sharpe_aggregation": sharpe_agg,
        "kappa_sensitivity": kappa_sens,
    }
