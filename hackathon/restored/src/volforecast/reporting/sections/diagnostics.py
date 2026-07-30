"""Diagnostics section: residuals, ACF, scatter, feature importance."""

from __future__ import annotations

import pandas as pd


def render(
    predictions: dict[str, dict[int, pd.DataFrame]],
    models: dict[str, dict[int, object]] | None = None,
) -> str:
    """Render the diagnostics section as an HTML fragment.

    Parameters
    ----------
    predictions : dict
        ``{symbol: {horizon: DataFrame}}`` with ``prediction`` column.
    models : dict, optional
        ``{symbol: {horizon: fitted_model}}`` for feature importance extraction.

    Returns
    -------
    str
        HTML ``<section>`` block containing:
        - Residual distribution (histogram + QQ plot)
        - Autocorrelation of forecast residuals (ACF/PACF bar chart)
        - Rolling-window QLIKE (63-day rolling) — spots regime-dependent failures
        - Scatter plot: predicted vs actual (with 45-degree reference line)
        - Feature importance bar chart (if model exposes .feature_importances_)
    """
    # TODO: implement — see workspace/plans/html-report.md § Section 9
    raise NotImplementedError("TODO: implement diagnostics section")
