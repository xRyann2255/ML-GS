"""Metrics aggregation and persistence for tournament results.

Extracts per-model, per-horizon metrics from tournament DataFrames and
persists them as structured JSON. This module is a pure data transformation
layer — no parquet reads, no model execution.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Columns to extract from tournament DataFrames.
# APPEND-ONLY: adding new keys is backward-compatible with metrics.json readers;
# NaN/missing values are skipped by extract_metrics_dict.
_METRIC_COLUMNS = (
    "qlike",
    "mse",
    "mae",
    "r2",
    "qlike_improvement_bps",
    "dm_pvalue",
    # Turbulence-split diagnostics (Plan 10 Task 1):
    "qlike_calm",
    "qlike_turb",
    "dm_p_turb",
)


def extract_metrics_dict(
    tournament_results: dict[int, pd.DataFrame],
) -> dict[str, dict[str, dict[str, float]]]:
    """Extract structured metrics dict from tournament result DataFrames.

    Parameters
    ----------
    tournament_results : dict[int, DataFrame]
        Keys are horizons, values are tournament tables (from statistical_tests.tournament_table).

    Returns
    -------
    dict[str, dict[str, dict[str, float]]]
        Nested: model_name -> horizon_str -> metric_name -> value.
        NaN and None values are excluded.
    """
    metrics: dict[str, dict[str, dict[str, float]]] = {}

    for h, df in tournament_results.items():
        for _, row in df.iterrows():
            model_name = row.get("model", "unknown")
            if model_name not in metrics:
                metrics[model_name] = {}
            h_metrics: dict[str, float] = {}
            for col in _METRIC_COLUMNS:
                if col in row and row[col] is not None:
                    val = row[col]
                    if isinstance(val, (int, float)) and not (
                        isinstance(val, float) and np.isnan(val)
                    ):
                        h_metrics[col] = float(val)
            metrics[model_name][str(h)] = h_metrics

    return metrics


def save_pooled_metrics(
    tournament_results: dict[int, pd.DataFrame],
    output_dir: Path,
) -> Path:
    """Persist metrics.json from tournament results.

    Writes a structured JSON with per-model, per-horizon metrics
    extracted from the tournament DataFrames.

    Parameters
    ----------
    tournament_results : dict[int, DataFrame]
        Keys are horizons, values are tournament tables.
    output_dir : Path
        Directory to write metrics.json into.

    Returns
    -------
    Path
        Path to the written metrics.json file.
    """
    metrics = extract_metrics_dict(tournament_results)

    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info("Saved pooled metrics to %s", metrics_path)
    return metrics_path
