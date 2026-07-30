"""Statistical tests for model comparison.

Implements formal hypothesis tests for comparing volatility forecasts:
- Diebold-Mariano (DM) test for pairwise forecast comparison
- Model Confidence Set (MCS) for identifying the set of best models
- Mincer-Zarnowitz regression for forecast efficiency
- Conditional (turbulence-split) QLIKE and DM per GNNHAR / Fang-Slepaczuk

Key functions:
    diebold_mariano_test        — Pairwise DM test for forecast comparison
    model_confidence_set        — Hansen et al. (2011) MCS procedure
    mincer_zarnowitz            — Forecast efficiency regression
    tournament_table            — Multi-model QLIKE comparison table
    conditional_qlike_split     — Top-decile market-RV QLIKE split (Zhang 2025)
    conditional_dm              — Median/top-25% bucketed DM (Fang 2026)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def diebold_mariano_test(
    loss_1: np.ndarray,
    loss_2: np.ndarray,
    horizon: int = 1,
    alternative: str = "two-sided",
    n_cross_sections: int | None = None,
    panel_order: str = "symbol_major",
) -> dict[str, float]:
    """Diebold-Mariano test for equal predictive accuracy.

    Tests H0: E[d_t] = 0 where d_t = L(e_1t) - L(e_2t).
    Uses Newey-West HAC standard errors (Bartlett kernel, bandwidth h-1)
    for multi-step forecasts per Diebold & Mariano (1995, JBES).

    Note: does NOT include the Harvey, Leybourne & Newbold (1997) small-sample
    correction factor sqrt((T + 1 - 2h + h(h-1)/T) / T). For T > 200 this
    correction is negligible.

    Sign convention: positive DM statistic means model 2 has lower loss
    (model 2 is better).

    Parameters
    ----------
    loss_1 : np.ndarray
        Loss series for model 1 (e.g., element-wise QLIKE values).
    loss_2 : np.ndarray
        Loss series for model 2.
    horizon : int
        Forecast horizon for HAC correction (default: 1).
        Bandwidth = horizon - 1.
    alternative : str
        'two-sided', 'less' (model 1 better), or 'greater' (model 2 better).
    n_cross_sections : int | None
        Number of cross-sectional units (symbols) in a panel. When provided
        and > 1, loss differentials are averaged per date before computing HAC
        variance, preventing Newey-West lags from crossing symbol boundaries.
    panel_order : str
        Layout of the pooled loss arrays when n_cross_sections is set.
        'symbol_major' — first T obs belong to symbol 1, next T to symbol 2, etc.
        'date_major' — first N obs are all symbols on date 1, next N on date 2, etc.

    Returns
    -------
    dict[str, float]
        Keys: 'dm_stat', 'p_value', 'mean_diff'.

    Raises
    ------
    ValueError
        If arrays have different lengths or horizon < 1.
    """
    from scipy import stats

    loss_1 = np.asarray(loss_1, dtype=np.float64)
    loss_2 = np.asarray(loss_2, dtype=np.float64)

    if len(loss_1) != len(loss_2):
        raise ValueError(f"Loss arrays must have same length, got {len(loss_1)} and {len(loss_2)}")
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")

    d = loss_1 - loss_2

    # Panel-aware date aggregation: average loss differentials per date
    if n_cross_sections is not None and n_cross_sections > 1:
        T_eff = len(d) // n_cross_sections
        if panel_order == "symbol_major":
            d = d[: n_cross_sections * T_eff].reshape(n_cross_sections, T_eff).mean(axis=0)
        elif panel_order == "date_major":
            d = d[: T_eff * n_cross_sections].reshape(T_eff, n_cross_sections).mean(axis=1)
        else:
            raise ValueError(
                f"panel_order must be 'symbol_major' or 'date_major', got '{panel_order}'"
            )
        T = T_eff
    else:
        T = len(d)

    d_bar = np.mean(d)
    d_demean = d - d_bar

    # Autocovariance at lag 0
    gamma_0 = np.dot(d_demean, d_demean) / T
    var_d = gamma_0

    # Newey-West HAC with Bartlett kernel (bandwidth = h-1)
    if horizon > 1:
        for j in range(1, horizon):
            gamma_j = np.dot(d_demean[j:], d_demean[:-j]) / T
            weight = 1.0 - j / horizon  # Bartlett kernel
            var_d += 2.0 * weight * gamma_j

    # Floor variance to avoid division by zero
    var_d = max(var_d, 1e-20)
    dm_stat = d_bar / np.sqrt(var_d / T)

    if alternative == "two-sided":
        p_value = 2.0 * (1.0 - stats.norm.cdf(abs(dm_stat)))
    elif alternative == "less":
        p_value = stats.norm.cdf(dm_stat)
    elif alternative == "greater":
        p_value = 1.0 - stats.norm.cdf(dm_stat)
    else:
        raise ValueError(
            f"alternative must be 'two-sided', 'less', or 'greater', got '{alternative}'"
        )

    return {
        "dm_stat": float(dm_stat),
        "p_value": float(p_value),
        "mean_diff": float(d_bar),
    }


def model_confidence_set(
    losses: dict[str, np.ndarray],
    alpha: float = 0.10,
    n_bootstrap: int = 10_000,
    block_length: int | None = None,
    seed: int = 42,
    n_cross_sections: int | None = None,
    panel_order: str = "symbol_major",
) -> dict[str, any]:
    """Hansen et al. (2011) Model Confidence Set.

    Identifies the set of models that contains the best model
    with (1-alpha) confidence via sequential elimination using the
    range statistic T_R and block bootstrap.

    Parameters
    ----------
    losses : dict[str, np.ndarray]
        Model name -> array of element-wise losses (shape (T,)).
    alpha : float
        Significance level (default: 0.10 for 90% MCS).
    n_bootstrap : int
        Number of bootstrap replications (default: 10000).
    block_length : int, optional
        Block bootstrap length. If None, uses max(1, int(sqrt(T))).
    seed : int
        Random seed for reproducibility.
    n_cross_sections : int, optional
        Number of cross-sectional units (symbols) in a panel-pooled loss
        array. When provided and > 1, losses are reshaped and averaged
        across cross-sections to produce date-level means before running
        the bootstrap. This prevents blocks from wrapping across symbol
        boundaries.
    panel_order : str
        Layout of the pooled loss array when n_cross_sections is used.
        - "symbol_major": array is [sym1_dates, sym2_dates, ...],
          reshaped to (n_cross_sections, T_eff) and averaged over axis=0.
        - "date_major": array is [date1_syms, date2_syms, ...],
          reshaped to (T_eff, n_cross_sections) and averaged over axis=1.
        Default: "symbol_major".

    Returns
    -------
    dict[str, any]
        Keys:
        - 'included': list of model names in the MCS
        - 'excluded': list of eliminated model names (first out first)
        - 'p_values': dict of model name -> MCS p-value
        - 'elimination_order': list of model names in elimination order
    """
    import logging

    logger = logging.getLogger(__name__)

    models = list(losses.keys())
    T = len(next(iter(losses.values())))

    # Edge case: single model
    if len(models) == 1:
        return {
            "included": list(models),
            "excluded": [],
            "p_values": {models[0]: 1.0},
            "elimination_order": [],
        }

    # Panel aggregation: average losses per date across cross-sections
    if n_cross_sections is not None and n_cross_sections > 1:
        T_eff = T // n_cross_sections
        aggregated = {}
        for m in models:
            arr = np.asarray(losses[m], dtype=np.float64)
            if panel_order == "symbol_major":
                arr = arr.reshape(n_cross_sections, T_eff).mean(axis=0)
            else:  # date_major
                arr = arr.reshape(T_eff, n_cross_sections).mean(axis=1)
            aggregated[m] = arr
        losses = aggregated
        T = T_eff

    if block_length is None:
        block_length = max(1, int(np.sqrt(T)))

    rng = np.random.default_rng(seed)

    # Convert to matrix for fast indexing
    loss_matrix = np.column_stack([np.asarray(losses[m], dtype=np.float64) for m in models])

    surviving = list(range(len(models)))
    p_values = {}
    elimination_order = []

    logger.info(
        "MCS: T=%d, %d models, %d bootstrap reps (block_length=%d)",
        T,
        len(models),
        n_bootstrap,
        block_length,
    )

    round_num = 0
    while len(surviving) > 1:
        round_num += 1
        n_surv = len(surviving)
        sub_losses = loss_matrix[:, surviving]  # (T, n_surv)

        # Vectorized pairwise mean loss differentials and t-statistics
        pairs_i, pairs_j = np.triu_indices(n_surv, k=1)
        n_pairs = len(pairs_i)

        # All pairwise differences: (T, n_pairs)
        d_all = sub_losses[:, pairs_i] - sub_losses[:, pairs_j]
        d_bar_all = d_all.mean(axis=0)  # (n_pairs,)

        # Variance (gamma_0 only, bandwidth=1 means no lags)
        d_demean_all = d_all - d_bar_all
        gamma_0_all = (d_demean_all * d_demean_all).sum(axis=0) / T  # (n_pairs,)
        var_all = np.maximum(gamma_0_all, 1e-20)
        se_all = np.sqrt(var_all / T)  # (n_pairs,)

        # t-statistics for all pairs
        t_all = d_bar_all / se_all  # (n_pairs,)

        # Range statistic: max |t_ij|
        T_R = np.max(np.abs(t_all))

        # Block bootstrap p-value — batched vectorized with early stopping
        count_ge = 0
        n_blocks = int(np.ceil(T / block_length))

        # Batch size: balance memory vs vectorization gain
        # Memory per batch: batch_size * T * n_pairs * 8 bytes
        max_mem_bytes = 512 * 1024 * 1024  # 512 MB cap
        elem_bytes = T * n_pairs * 8
        batch_size = min(500, n_bootstrap, max(1, max_mem_bytes // max(elem_bytes, 1)))

        # Pre-compute block offsets (shared across all batches)
        offsets = np.arange(block_length, dtype=np.intp)

        # Early stopping: check at batch boundaries
        z_conf = 2.807  # z for 99.75% one-sided (Bonferroni for two checks)

        stopped_early = False
        n_done = 0
        for batch_start in range(0, n_bootstrap, batch_size):
            curr_batch = min(batch_size, n_bootstrap - batch_start)

            # Generate all block starts for this batch: (curr_batch, n_blocks)
            starts_batch = rng.integers(0, T, size=(curr_batch, n_blocks))

            # Build boot indices vectorized — no Python loop over blocks
            # raw_indices: (curr_batch, n_blocks, block_length)
            raw_indices = (starts_batch[:, :, None] + offsets[None, None, :]) % T
            # Flatten blocks and truncate to T: (curr_batch, T)
            boot_indices = raw_indices.reshape(curr_batch, -1)[:, :T]

            # Gather bootstrap samples: (curr_batch, T, n_pairs)
            d_boot_batch = d_all[boot_indices]

            # Batch means: (curr_batch, n_pairs)
            means_b = d_boot_batch.mean(axis=1)
            d_star_bar = means_b - d_bar_all[None, :]

            # Variance via E[X^2] - E[X]^2: (curr_batch, n_pairs)
            sq_means = np.einsum("bij,bij->bj", d_boot_batch, d_boot_batch) / T
            gamma_0_star = sq_means - means_b * means_b
            np.maximum(gamma_0_star, 1e-20, out=gamma_0_star)
            se_star = np.sqrt(gamma_0_star / T)

            # Range statistics: (curr_batch,)
            T_R_stars = np.max(np.abs(d_star_bar / se_star), axis=1)
            count_ge += int((T_R_stars >= T_R).sum())
            n_done += curr_batch

            # Early stopping check at batch boundary
            if n_done >= batch_size * 2:  # need at least 2 batches
                p_hat = count_ge / n_done
                se_p = np.sqrt(max(p_hat * (1.0 - p_hat), 1e-10) / n_done)
                if p_hat + z_conf * se_p < alpha:
                    stopped_early = True
                    break
                if p_hat - z_conf * se_p >= alpha:
                    stopped_early = True
                    break

        n_effective = n_done
        p_value = count_ge / n_effective

        if p_value < alpha:
            # Reconstruct full t-stats matrix for worst-model identification
            t_stats = np.zeros((n_surv, n_surv))
            for idx_p, (i, j) in enumerate(zip(pairs_i, pairs_j)):
                t_stats[i, j] = t_all[idx_p]
                t_stats[j, i] = -t_all[idx_p]

            # Eliminate worst model: highest max_j(t_ij)
            worst_score = t_stats.max(axis=1)
            worst_idx = int(np.argmax(worst_score))
            worst_model = models[surviving[worst_idx]]
            p_values[worst_model] = p_value
            elimination_order.append(worst_model)
            surviving.pop(worst_idx)
            logger.info(
                "MCS round %d: %d models, p=%.4f, %d/%d boot → eliminated %s",
                round_num,
                n_surv,
                p_value,
                n_effective,
                n_bootstrap,
                worst_model,
            )
        else:
            logger.info(
                "MCS round %d: %d models, p=%.4f, %d/%d boot → MCS formed",
                round_num,
                n_surv,
                p_value,
                n_effective,
                n_bootstrap,
            )
            # Cannot reject H0 — remaining models form the MCS
            break

    # Assign p-value = 1.0 (or last p-value) to surviving models
    for idx in surviving:
        p_values[models[idx]] = max(p_value if len(surviving) > 1 else 1.0, alpha)

    included = [models[i] for i in surviving]
    excluded = list(elimination_order)

    return {
        "included": included,
        "excluded": excluded,
        "p_values": p_values,
        "elimination_order": elimination_order,
    }


def mincer_zarnowitz(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    horizon: int = 1,
) -> dict[str, float]:
    """Mincer-Zarnowitz forecast efficiency regression.

    Regresses realized values on forecasts:
        sigma2_t = alpha + beta * sigma2_hat_t + epsilon_t

    An efficient forecast has alpha=0 and beta=1 (jointly).
    Uses Newey-West HAC standard errors for the joint F-test (H0: alpha=0, beta=1)
    because volatility forecast errors are serially correlated.

    IMPORTANT: Inputs must be in VARIANCE space (not log space).
    Apply Duan retransformation first if predictions are in log space.

    Parameters
    ----------
    y_true : np.ndarray
        Realized variance values (variance space).
    y_pred : np.ndarray
        Forecast variance values (variance space).
    horizon : int
        Forecast horizon (used for HAC bandwidth: max(horizon, T^{1/3})).

    Returns
    -------
    dict[str, float]
        Keys: 'alpha', 'beta', 'r_squared', 'alpha_se', 'beta_se',
        'f_stat', 'f_pvalue'.

    Raises
    ------
    ValueError
        If arrays have different lengths.
    """
    import statsmodels.api as sm

    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)

    if len(y_true) != len(y_pred):
        raise ValueError(f"Arrays must have same length, got {len(y_true)} and {len(y_pred)}")

    # Constant predictions make the design matrix singular (const + constant col
    # are linearly dependent). Return degenerate result — forecast has no skill.
    if np.ptp(y_pred) == 0:
        return {
            "alpha": float(np.mean(y_true)),
            "beta": 0.0,
            "r_squared": 0.0,
            "alpha_se": float("nan"),
            "beta_se": float("nan"),
            "f_stat": float("nan"),
            "f_pvalue": 1.0,
        }

    X = sm.add_constant(y_pred, has_constant="add")

    # Fit with Newey-West HAC standard errors.
    # Bandwidth: max(horizon, T^{1/3}) — accounts for both MA(h-1) structure
    # in multi-step forecasts and residual ARCH clustering.
    T = len(y_true)
    maxlags = max(horizon, int(np.ceil(T ** (1.0 / 3.0))))
    result = sm.OLS(y_true, X).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})

    # Joint F-test for H0: alpha=0, beta=1
    # Wald stat = (beta_hat - q)' [HAC_Cov]^{-1} (beta_hat - q) / num_restrictions
    from scipy import stats as sp_stats

    beta_hat = result.params
    cov_beta = result.cov_params()
    diff = beta_hat - np.array([0.0, 1.0])  # deviation from H0
    try:
        f_stat = float(diff @ np.linalg.solve(cov_beta, diff) / 2.0)
    except np.linalg.LinAlgError:
        f_stat = float("nan")
    df_resid = result.df_resid
    f_pvalue = float(1.0 - sp_stats.f.cdf(f_stat, 2, df_resid)) if np.isfinite(f_stat) else 1.0

    return {
        "alpha": float(result.params[0]),
        "beta": float(result.params[1]),
        "r_squared": float(result.rsquared),
        "alpha_se": float(result.bse[0]),
        "beta_se": float(result.bse[1]),
        "f_stat": f_stat,
        "f_pvalue": f_pvalue,
    }


def tournament_table(
    predictions: dict[str, np.ndarray],
    y_true: np.ndarray,
    baseline: str = "har",
    horizon: int = 1,
    mcs_alpha: float = 0.10,
    mcs_bootstrap: int = 10_000,
    n_cross_sections: int | None = None,
    panel_order: str = "symbol_major",
) -> pd.DataFrame:
    """Generate multi-model QLIKE tournament comparison table (pure stats).

    Combines QLIKE, MSE, R-squared, Diebold-Mariano test, Mincer-Zarnowitz
    regression, and Model Confidence Set into a single ranked table.

    For economic-value enrichment (vol-targeting Sharpe, delta-hedged straddle
    metrics, naive DH baselines), compose with
    :func:`volforecast.evaluation.tournament_economics.enrich_tournament_economics`.

    Parameters
    ----------
    predictions : dict[str, np.ndarray]
        Model name -> OOS prediction array (LOG space).
    y_true : np.ndarray
        True log(RV) values.
    baseline : str
        Name of baseline model for DM test and bps comparison.
    horizon : int
        Forecast horizon for HAC correction in DM test.
    mcs_alpha : float
        Significance level for MCS (default: 0.10).
    mcs_bootstrap : int
        Number of bootstrap replicates for MCS.

    Returns
    -------
    pd.DataFrame
        Sorted by QLIKE ascending (best first). Columns:
        model, qlike, qlike_bps, mse, r_squared,
        mz_alpha, mz_beta, mz_f_pvalue,
        dm_stat, dm_pvalue, mcs_included, mcs_pvalue.
    """
    from volforecast.evaluation.metrics import (
        mse as mse_fn,
    )
    from volforecast.evaluation.metrics import (
        qlike as qlike_fn,
    )
    from volforecast.evaluation.metrics import (
        qlike_improvement_bps,
    )
    from volforecast.evaluation.metrics import (
        r_squared as r2_fn,
    )

    y_true = np.asarray(y_true, dtype=np.float64)

    # Fall back to first model if named baseline is not in predictions
    if baseline not in predictions:
        baseline = next(iter(predictions))

    # Step 1: Compute element-wise QLIKE losses per model
    losses = {}
    for name, pred in predictions.items():
        pred = np.asarray(pred, dtype=np.float64)
        diff = y_true - pred
        # Clamp to prevent overflow in exp() for extreme predictions
        diff_clamped = np.clip(diff, -500.0, 500.0)
        losses[name] = np.exp(diff_clamped) - diff - 1.0

    # Step 2: Aggregate metrics per model
    qlike_baseline = qlike_fn(y_true, np.asarray(predictions[baseline]), log_space=True)

    rows = []
    for name, pred in predictions.items():
        pred = np.asarray(pred, dtype=np.float64)
        q = qlike_fn(y_true, pred, log_space=True)
        m = mse_fn(y_true, pred)
        r2 = r2_fn(y_true, pred)
        q_bps = qlike_improvement_bps(qlike_baseline, q)

        # Step 4: DM test vs baseline
        if name == baseline:
            dm_stat, dm_pvalue = 0.0, 1.0
        else:
            dm_result = diebold_mariano_test(
                losses[baseline], losses[name], horizon=horizon,
                n_cross_sections=n_cross_sections, panel_order=panel_order,
            )
            dm_stat = dm_result["dm_stat"]
            dm_pvalue = dm_result["p_value"]

        # Step 5: MZ regression (variance space with non-parametric Duan smearing)
        # Non-parametric: E[exp(e)] estimated directly from residuals.
        # This is distribution-free and correct for fat-tailed residuals
        # (parametric exp(sigma^2/2) underestimates when kurtosis > 0).
        residuals = y_true - pred
        # Clamp to prevent overflow in exp() for extreme residuals
        residuals_clamped = np.clip(residuals, -500.0, 500.0)
        smearing_factor = float(np.mean(np.exp(residuals_clamped)))
        pred_clamped = np.clip(pred, -500.0, 500.0)
        h_level = np.exp(pred_clamped) * smearing_factor
        # Guard against inf/nan in h_level before passing to MZ regression
        finite_mask = np.isfinite(h_level) & np.isfinite(np.exp(y_true))
        if finite_mask.sum() < 10:
            mz = {"intercept": np.nan, "slope": np.nan, "joint_pvalue": np.nan}
        else:
            mz = mincer_zarnowitz(
                np.exp(y_true)[finite_mask], h_level[finite_mask], horizon=horizon
            )

        rows.append(
            {
                "model": name,
                "qlike": q,
                "qlike_bps": q_bps,
                "mse": m,
                "r_squared": r2,
                "mz_alpha": mz["alpha"],
                "mz_beta": mz["beta"],
                "mz_f_pvalue": mz["f_pvalue"],
                "dm_stat": dm_stat,
                "dm_pvalue": dm_pvalue,
            }
        )

    # Step 6: MCS
    if mcs_bootstrap and mcs_bootstrap > 0:
        mcs_result = model_confidence_set(
            losses, alpha=mcs_alpha, n_bootstrap=mcs_bootstrap,
            n_cross_sections=n_cross_sections, panel_order=panel_order,
        )
    else:
        mcs_result = {"included": set(losses.keys()), "p_values": {n: 1.0 for n in losses}}

    # Step 7: Assemble and sort
    for row in rows:
        row["mcs_included"] = row["model"] in mcs_result["included"]
        row["mcs_pvalue"] = mcs_result["p_values"].get(row["model"], 0.0)

    df = pd.DataFrame(rows)
    df = df.sort_values("qlike", ascending=True).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Conditional (turbulence-split) diagnostics
# ---------------------------------------------------------------------------


def _turb_calm_date_masks(
    market_rv: pd.Series, quantile: float, mode: str
) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    """Return (turbulent_dates, calm_dates) index tuples for a market_rv Series.

    mode='top' (used by ``conditional_qlike_split``): turbulent = market_rv >=
    quantile threshold; calm = market_rv < threshold.

    mode='median' (used by ``conditional_dm`` split='median'):
    turbulent = market_rv > threshold; calm = market_rv <= threshold. Ties on
    the median go to the calm bucket by convention.

    mode='q75' (used by ``conditional_dm`` split='q75'):
    turbulent = market_rv >= threshold; calm = market_rv < threshold.
    """
    mrv = market_rv.dropna()
    thresh = mrv.quantile(quantile)
    if mode == "top" or mode == "q75":
        turb = mrv.index[mrv >= thresh]
        calm = mrv.index[mrv < thresh]
    elif mode == "median":
        turb = mrv.index[mrv > thresh]
        calm = mrv.index[mrv <= thresh]
    else:
        raise ValueError(f"unknown mode {mode!r}")
    return turb, calm


def conditional_qlike_split(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    dates,
    market_rv: pd.Series,
    quantile: float = 0.9,
) -> dict[str, float]:
    """Split QLIKE into calm and turbulent buckets by market-RV date bucket.

    Bucket membership is decided on DATES: an observation is turbulent if its
    date's market RV is in the top ``quantile`` of all dates. All symbols on a
    turbulent date share the turbulent bucket. This implements the Zhang
    et al. (2025) "GNNHAR" Table 2 protocol (top-decile SPY-RV split).

    Parameters
    ----------
    y_true, y_pred : np.ndarray
        Log-space realized RV and forecast, length N (panel-flattened OK).
    dates : array-like or pd.Index
        Date labels aligned to ``y_true`` (length N). Multiple rows may share
        a date in a panel; a date's bucket is set once and applied uniformly.
    market_rv : pd.Series
        Date-indexed market RV (typically SPY RV in variance space).
    quantile : float, default 0.9
        Turbulence threshold — dates with market_rv >= this quantile are
        turbulent (default: top decile per Zhang et al. 2025).

    Returns
    -------
    dict[str, float]
        Keys ``qlike_calm``, ``qlike_turb``, ``n_turb``. Bucket QLIKE is NaN
        when the bucket is empty; ``n_turb`` is the count of TURBULENT
        observations (not dates).

    References
    ----------
    Zhang et al. (2025), "GNNHAR: Graph Neural Network HAR", Table 2 —
    top-decile SPY-RV date split for regime-conditional QLIKE.
    """
    from volforecast.evaluation.metrics import qlike as qlike_fn

    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    if len(y_true) != len(y_pred):
        raise ValueError(
            f"y_true and y_pred must have same length: {len(y_true)} vs {len(y_pred)}"
        )

    dates_idx = pd.DatetimeIndex(pd.to_datetime(np.asarray(dates)))
    turb_dates, calm_dates = _turb_calm_date_masks(market_rv, quantile, mode="top")
    turb_mask = dates_idx.isin(turb_dates)
    calm_mask = dates_idx.isin(calm_dates)

    qt = (
        qlike_fn(y_true[turb_mask], y_pred[turb_mask], log_space=True)
        if turb_mask.any()
        else float("nan")
    )
    qc = (
        qlike_fn(y_true[calm_mask], y_pred[calm_mask], log_space=True)
        if calm_mask.any()
        else float("nan")
    )
    return {
        "qlike_calm": float(qc),
        "qlike_turb": float(qt),
        "n_turb": int(turb_mask.sum()),
    }


def conditional_dm(
    loss_a: np.ndarray,
    loss_b: np.ndarray,
    dates,
    market_rv: pd.Series,
    split: str = "median",
    horizon: int = 1,
    n_cross_sections: int | None = None,
    panel_order: str = "date_major",
) -> dict[str, float]:
    """Bucketed Diebold-Mariano test conditional on market-RV regime.

    Splits observations by their date's market-RV bucket, then runs the same
    panel-aware date-averaged HAC DM test used unconditionally
    (:func:`diebold_mariano_test`) on each bucket independently.

    Parameters
    ----------
    loss_a, loss_b : np.ndarray
        Element-wise loss series for the two models being compared (length N,
        panel-flattened). Sign convention matches ``diebold_mariano_test``:
        positive DM statistic means model B has lower loss (model B better).
    dates : array-like
        Date labels aligned to the loss arrays (length N).
    market_rv : pd.Series
        Date-indexed market RV (typically SPY RV) used for bucket assignment.
    split : {'median', 'q75'}, default 'median'
        - 'median': turbulent = market_rv > median; calm = market_rv <= median.
        - 'q75':    turbulent = market_rv >= 75th percentile; calm = below.
        Follows Fang & Slepaczuk (2026) Table 4 protocol.
    horizon : int, default 1
        Forecast horizon — used for the Newey-West HAC bandwidth
        (bandwidth = horizon - 1). Passed through to ``diebold_mariano_test``.
    n_cross_sections : int | None
        Number of symbols in the panel. When provided and > 1, the underlying
        ``diebold_mariano_test`` averages loss differentials PER DATE before
        computing HAC variance — the same panel-aware machinery used
        unconditionally. The turbulent/calm masks filter whole dates (all
        cross-sections of a date share a bucket), so the filtered arrays
        remain a clean panel with the same ``n_cross_sections`` and
        ``panel_order``.
    panel_order : {'date_major', 'symbol_major'}, default 'date_major'
        Layout of the pooled loss arrays. Passed through unchanged; whole-date
        filtering preserves both layouts.

    Returns
    -------
    dict[str, float]
        Keys: ``dm_stat_turb``, ``p_value_turb``, ``dm_stat_calm``,
        ``p_value_calm``, ``n_turb``, ``n_calm``. DM outputs are NaN when a
        bucket is empty.

    References
    ----------
    Fang & Slepaczuk (2026), Table 4 — median-split and top-25% conditional
    Diebold-Mariano tests for volatility forecast comparison.
    """
    loss_a = np.asarray(loss_a, dtype=np.float64)
    loss_b = np.asarray(loss_b, dtype=np.float64)
    if len(loss_a) != len(loss_b):
        raise ValueError(
            f"loss_a and loss_b must have same length: {len(loss_a)} vs {len(loss_b)}"
        )

    if split == "median":
        quantile = 0.5
        mode = "median"
    elif split == "q75":
        quantile = 0.75
        mode = "q75"
    else:
        raise ValueError(f"split must be 'median' or 'q75', got {split!r}")

    dates_idx = pd.DatetimeIndex(pd.to_datetime(np.asarray(dates)))
    turb_dates, calm_dates = _turb_calm_date_masks(market_rv, quantile, mode=mode)
    turb_mask = dates_idx.isin(turb_dates)
    calm_mask = dates_idx.isin(calm_dates)

    def _run(mask: np.ndarray) -> dict[str, float]:
        if not mask.any():
            return {"dm_stat": float("nan"), "p_value": float("nan")}
        # Whole-date filtering preserves clean panel layout: n_cross_sections
        # and panel_order flow through to the same HAC machinery as the
        # unconditional test.
        return diebold_mariano_test(
            loss_a[mask],
            loss_b[mask],
            horizon=horizon,
            n_cross_sections=n_cross_sections,
            panel_order=panel_order,
        )

    turb_res = _run(turb_mask)
    calm_res = _run(calm_mask)

    return {
        "dm_stat_turb": float(turb_res["dm_stat"]),
        "p_value_turb": float(turb_res["p_value"]),
        "dm_stat_calm": float(calm_res["dm_stat"]),
        "p_value_calm": float(calm_res["p_value"]),
        "n_turb": int(turb_mask.sum()),
        "n_calm": int(calm_mask.sum()),
    }
