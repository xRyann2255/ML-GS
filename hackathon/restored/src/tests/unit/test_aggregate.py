"""Unit tests for evaluation.aggregate — metrics persistence."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


class TestExtractMetricsDict:
    """Test pure extraction of metrics dict from tournament DataFrames."""

    def test_shape_matches_models_and_horizons(self):
        from volforecast.evaluation.aggregate import extract_metrics_dict

        rows = [
            {"model": "har", "qlike": 0.05, "mse": 0.1, "r2": 0.5, "dm_pvalue": 1.0},
            {"model": "harq", "qlike": 0.04, "mse": 0.09, "r2": 0.55, "dm_pvalue": 0.13},
        ]
        results = {1: pd.DataFrame(rows), 5: pd.DataFrame(rows)}
        metrics = extract_metrics_dict(results)

        assert "har" in metrics
        assert "harq" in metrics
        assert "1" in metrics["har"]
        assert "5" in metrics["har"]
        assert "1" in metrics["harq"]

    def test_nan_excluded(self):
        from volforecast.evaluation.aggregate import extract_metrics_dict

        rows = [{"model": "test", "qlike": 0.05, "mse": float("nan"), "dm_pvalue": 0.1}]
        results = {1: pd.DataFrame(rows)}
        metrics = extract_metrics_dict(results)

        entry = metrics["test"]["1"]
        assert "qlike" in entry
        assert "mse" not in entry  # NaN excluded
        assert "dm_pvalue" in entry

    def test_none_excluded(self):
        from volforecast.evaluation.aggregate import extract_metrics_dict

        rows = [{"model": "test", "qlike": 0.05, "mae": None, "dm_pvalue": 0.1}]
        results = {1: pd.DataFrame(rows)}
        metrics = extract_metrics_dict(results)

        entry = metrics["test"]["1"]
        assert "mae" not in entry

    def test_all_values_are_float(self):
        from volforecast.evaluation.aggregate import extract_metrics_dict

        rows = [{"model": "har", "qlike": 0.05, "mse": 0.1, "r2": 0.5, "dm_pvalue": 1.0}]
        results = {1: pd.DataFrame(rows)}
        metrics = extract_metrics_dict(results)

        for v in metrics["har"]["1"].values():
            assert isinstance(v, float)


class TestSavePooledMetrics:
    """Test JSON file persistence."""

    def test_writes_json_file(self, tmp_path):
        from volforecast.evaluation.aggregate import save_pooled_metrics

        rows = [{"model": "har", "qlike": 0.05, "mse": 0.1, "dm_pvalue": 1.0}]
        results = {1: pd.DataFrame(rows)}

        path = save_pooled_metrics(results, tmp_path)

        assert path.exists()
        assert path.name == "metrics.json"
        with open(path) as f:
            data = json.load(f)
        assert "har" in data

    def test_creates_output_dir(self, tmp_path):
        from volforecast.evaluation.aggregate import save_pooled_metrics

        out_dir = tmp_path / "nested" / "output"
        rows = [{"model": "har", "qlike": 0.05}]
        results = {1: pd.DataFrame(rows)}

        path = save_pooled_metrics(results, out_dir)
        assert path.exists()

    def test_output_matches_extract(self, tmp_path):
        from volforecast.evaluation.aggregate import extract_metrics_dict, save_pooled_metrics

        rows = [
            {"model": "har", "qlike": 0.05, "mse": 0.1, "dm_pvalue": 1.0},
            {"model": "harq", "qlike": 0.04, "mse": 0.09, "dm_pvalue": 0.13},
        ]
        results = {1: pd.DataFrame(rows), 5: pd.DataFrame(rows)}

        path = save_pooled_metrics(results, tmp_path)
        with open(path) as f:
            written = json.load(f)

        expected = extract_metrics_dict(results)
        assert written == expected
