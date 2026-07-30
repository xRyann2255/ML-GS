"""Statistical tests section: DM test, MCS membership, Mincer-Zarnowitz.

Gracefully handles NotImplementedError from statistical_tests.py stubs
by rendering a placeholder message.
"""

from __future__ import annotations

import pandas as pd


def render(
    predictions: dict[str, dict[int, pd.DataFrame]],
    baseline_predictions: dict[str, dict[int, pd.DataFrame]] | None = None,
) -> str:
    """Render the statistical tests section as an HTML fragment.

    Parameters
    ----------
    predictions : dict
        ``{symbol: {horizon: DataFrame}}`` with ``prediction`` column.
    baseline_predictions : dict, optional
        Baseline model predictions for DM test comparison.

    Returns
    -------
    str
        HTML ``<section>`` block containing:
        - Diebold-Mariano test results table (statistic, p-value, significance)
        - Model Confidence Set membership table
        - Mincer-Zarnowitz regression (alpha, beta, R², joint test p-value)
        - p-value dot plot for DM tests
        - Placeholder message if underlying tests are not yet implemented
    """
    # TODO: implement — see workspace/plans/html-report.md § Section 7
    # Note: wrap calls to volforecast.evaluation.statistical_tests in try/except
    # NotImplementedError to show "Statistical tests not yet implemented" placeholder
    raise NotImplementedError("TODO: implement statistical tests section")
