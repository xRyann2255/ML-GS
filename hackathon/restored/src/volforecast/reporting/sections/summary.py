"""Summary section: experiment metadata and aggregated metric tables."""

from __future__ import annotations


def render(
    config_snapshot: dict,
    metrics: dict[str, dict[str, dict[str, float]]],
) -> str:
    """Render the summary section as an HTML fragment.

    Parameters
    ----------
    config_snapshot : dict
        Experiment config as a plain dict (loaded from config.yaml).
    metrics : dict
        Nested dict: ``{symbol: {horizon: {metric_name: value}}}``.

    Returns
    -------
    str
        HTML ``<section>`` block containing:
        - Experiment name, date range, universe, model, CV method, feature layers
        - Aggregated metric table (QLIKE / MSE / R² per horizon, averaged across symbols)
        - Per-symbol metric table (collapsible)
    """
    # TODO: implement — see workspace/plans/html-report.md § Section 4
    raise NotImplementedError("TODO: implement summary section")
