"""QLIKE analysis section: heatmaps, improvement bars, rolling QLIKE."""

from __future__ import annotations

import pandas as pd


def render(
    metrics: dict[str, dict[str, dict[str, float]]],
    predictions: dict[str, dict[int, pd.DataFrame]] | None = None,
    baseline_metrics: dict[str, dict[str, dict[str, float]]] | None = None,
) -> str:
    """Render the QLIKE analysis section as an HTML fragment.

    Parameters
    ----------
    metrics : dict
        Nested dict: ``{symbol: {horizon: {metric_name: value}}}``.
    predictions : dict, optional
        For computing rolling QLIKE over time.
    baseline_metrics : dict, optional
        Baseline experiment metrics for computing QLIKE improvement (bps).

    Returns
    -------
    str
        HTML ``<section>`` block containing:
        - QLIKE heatmap: symbols (rows) x horizons (columns)
        - QLIKE improvement (bps) vs baseline (bar chart, if baseline provided)
        - Rolling QLIKE over time (line chart, if predictions provided)
    """
    # TODO: implement — see workspace/plans/html-report.md § Section 6
    raise NotImplementedError("TODO: implement QLIKE analysis section")
