"""Forecast vs Actual section: THE MAIN CHART.

Interactive time-series plot of predicted log-RV vs realized log-RV
with horizon/symbol selectors and COVID period highlighting.
"""

from __future__ import annotations

import pandas as pd


def render(
    predictions: dict[str, dict[int, pd.DataFrame]],
    actuals: dict[str, pd.Series] | None = None,
) -> str:
    """Render the forecast-vs-actual section as an HTML fragment.

    Parameters
    ----------
    predictions : dict
        Nested dict: ``{symbol: {horizon: DataFrame}}``.
        Each DataFrame has a ``prediction`` column and DatetimeIndex.
    actuals : dict, optional
        ``{symbol: Series}`` of actual log-RV values. If None, actuals are
        loaded from the RV panel.

    Returns
    -------
    str
        HTML ``<section>`` block containing:
        - Plotly time-series chart: predicted vs actual log-RV
        - Dropdown to switch between horizons (h=1, h=5, h=22)
        - Dropdown to switch between symbols
        - COVID period shading (Feb-Jun 2020)
        - Hover tooltips: date, predicted, actual, error
        - Range slider for date navigation
    """
    # TODO: implement — see workspace/plans/html-report.md § Section 5
    #
    # Implementation notes:
    # - Use plotly.graph_objects.Scatter for each trace
    # - Use updatemenus for horizon/symbol dropdowns
    # - Add vrect shape for COVID period (constants.COVID_START to constants.COVID_END)
    # - Call plotly.io.to_html(fig, include_plotlyjs=False, full_html=False) for fragment
    raise NotImplementedError("TODO: implement forecast vs actual chart")
