"""Tests for graph-diagnostics and spillover panels in the tournament dashboard.

Two published failure modes must be visible per graph experiment:
- corr-graph crisis density explosion (Wade 2026 Table 2)
- GLASSO refit instability, consecutive-refit Jaccard < 0.8 (O Nuallain 2025 §5.5)
- GSP-HAR graph signal energy (Chi, Gao & Wang 2024)

Plus the Plan-05 learned attention-spillover table when the winning graph model
exposes ``spillover_matrix``.

These tests assert on the Plotly figure dict structure — NOT on rendered HTML —
so the dashboard can evolve visually without breaking the contract.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from volforecast.evaluation.tournament_dashboard import (
    build_graph_quality_figure,
    build_spillover_heatmap,
    load_graph_panels,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def diagnostics_df() -> pd.DataFrame:
    """Synthetic schedule_stability + energy DataFrame (5 refits)."""
    return pd.DataFrame(
        {
            "refit_date": pd.date_range("2022-01-03", periods=5, freq="21B"),
            "density": [0.10, 0.15, 0.42, 0.20, 0.12],  # crisis density spike
            "jaccard_vs_previous": [np.nan, 0.85, 0.62, 0.71, 0.78],
            "signal_energy": [1.2, 1.5, 4.8, 2.1, 1.4],
        }
    )


@pytest.fixture
def spillover_matrix_df() -> pd.DataFrame:
    """Synthetic 4x4 row-stochastic attention spillover matrix."""
    symbols = ["AAA", "BBB", "CCC", "DDD"]
    m = np.array(
        [
            [0.0, 0.4, 0.3, 0.3],
            [0.5, 0.0, 0.2, 0.3],
            [0.2, 0.6, 0.0, 0.2],
            [0.1, 0.4, 0.5, 0.0],
        ],
        dtype=np.float64,
    )
    return pd.DataFrame(m, index=symbols, columns=symbols)


# ---------------------------------------------------------------------------
# build_graph_quality_figure
# ---------------------------------------------------------------------------


class TestGraphQualityFigure:
    def test_returns_plotly_figure(self, diagnostics_df):
        fig = build_graph_quality_figure(diagnostics_df)
        # Duck-type: must have to_dict() returning {data, layout}
        d = fig.to_dict()
        assert "data" in d
        assert "layout" in d

    def test_three_traces_density_jaccard_energy(self, diagnostics_df):
        fig = build_graph_quality_figure(diagnostics_df)
        d = fig.to_dict()
        trace_names = {tr.get("name", "") for tr in d["data"]}
        assert "density" in trace_names
        assert "jaccard_vs_previous" in trace_names
        assert "signal_energy" in trace_names

    def test_x_axis_uses_refit_dates(self, diagnostics_df):
        fig = build_graph_quality_figure(diagnostics_df)
        # Traverse fig.data directly — to_dict() base64-encodes numpy arrays.
        for tr in fig.data:
            if getattr(tr, "name", None) == "density":
                assert len(tr.x) == len(diagnostics_df)
                assert list(tr.y) == diagnostics_df["density"].tolist()
                break
        else:
            pytest.fail("density trace not found")

    def test_title_mentions_graph_quality(self, diagnostics_df):
        fig = build_graph_quality_figure(diagnostics_df)
        d = fig.to_dict()
        title = d["layout"].get("title", {})
        title_text = title.get("text", "") if isinstance(title, dict) else str(title)
        assert "graph" in title_text.lower() and "quality" in title_text.lower()


# ---------------------------------------------------------------------------
# build_spillover_heatmap
# ---------------------------------------------------------------------------


class TestSpilloverHeatmap:
    def test_returns_plotly_figure(self, spillover_matrix_df):
        fig = build_spillover_heatmap(spillover_matrix_df)
        d = fig.to_dict()
        assert "data" in d
        assert "layout" in d

    def test_heatmap_trace_type(self, spillover_matrix_df):
        fig = build_spillover_heatmap(spillover_matrix_df)
        d = fig.to_dict()
        assert len(d["data"]) >= 1
        assert d["data"][0]["type"] == "heatmap"

    def test_nxn_shape_and_symbol_labels(self, spillover_matrix_df):
        fig = build_spillover_heatmap(spillover_matrix_df)
        tr = fig.data[0]
        assert list(tr.x) == list(spillover_matrix_df.columns)
        assert list(tr.y) == list(spillover_matrix_df.index)
        z = np.asarray(tr.z)
        assert z.shape == (4, 4)

    def test_not_causal_caveat_in_subtitle(self, spillover_matrix_df):
        fig = build_spillover_heatmap(spillover_matrix_df)
        d = fig.to_dict()
        layout = d["layout"]
        # Search title text + annotations for the required caveat
        haystack = []
        title = layout.get("title", {})
        if isinstance(title, dict):
            haystack.append(title.get("text", "") or "")
        else:
            haystack.append(str(title))
        for ann in layout.get("annotations", []) or []:
            haystack.append(ann.get("text", "") or "")
        blob = " ".join(haystack).lower()
        assert "not identified causal spillovers" in blob
        assert "learned attention" in blob
        assert "co-moves with regimes" in blob


# ---------------------------------------------------------------------------
# load_graph_panels — detection + characterization
# ---------------------------------------------------------------------------


class TestLoadGraphPanels:
    def test_empty_dir_returns_no_panels(self, tmp_path):
        panels = load_graph_panels(tmp_path)
        assert panels == []

    def test_only_diagnostics_returns_graph_quality_panel(
        self, tmp_path, diagnostics_df
    ):
        diagnostics_df.to_parquet(tmp_path / "graph_diagnostics.parquet")
        panels = load_graph_panels(tmp_path)
        assert len(panels) == 1
        assert panels[0]["kind"] == "graph_quality"
        fig_dict = panels[0]["figure"].to_dict()
        names = {tr.get("name", "") for tr in fig_dict["data"]}
        assert {"density", "jaccard_vs_previous", "signal_energy"} <= names

    def test_only_spillover_returns_spillover_panel(
        self, tmp_path, spillover_matrix_df
    ):
        spillover_matrix_df.to_parquet(tmp_path / "spillover_matrix.parquet")
        panels = load_graph_panels(tmp_path)
        assert len(panels) == 1
        assert panels[0]["kind"] == "spillover"
        d = panels[0]["figure"].to_dict()
        assert d["data"][0]["type"] == "heatmap"

    def test_both_present_returns_both_panels(
        self, tmp_path, diagnostics_df, spillover_matrix_df
    ):
        diagnostics_df.to_parquet(tmp_path / "graph_diagnostics.parquet")
        spillover_matrix_df.to_parquet(tmp_path / "spillover_matrix.parquet")
        panels = load_graph_panels(tmp_path)
        kinds = [p["kind"] for p in panels]
        assert "graph_quality" in kinds
        assert "spillover" in kinds
        assert len(panels) == 2

    def test_per_horizon_diagnostics_files_are_picked_up(
        self, tmp_path, diagnostics_df
    ):
        """Runner may emit per-horizon files: graph_diagnostics_h1.parquet, etc."""
        diagnostics_df.to_parquet(tmp_path / "graph_diagnostics_h1.parquet")
        diagnostics_df.to_parquet(tmp_path / "graph_diagnostics_h5.parquet")
        panels = load_graph_panels(tmp_path)
        # At least one graph_quality panel per horizon file
        gq_panels = [p for p in panels if p["kind"] == "graph_quality"]
        assert len(gq_panels) >= 2


# ---------------------------------------------------------------------------
# Runner persistence — graph_diagnostics.parquet is written for graph experiments
# ---------------------------------------------------------------------------


class TestRunnerPersistsGraphDiagnostics:
    """Characterization: runner writes graph_diagnostics.parquet when running a
    graph experiment; non-graph runs are unaffected."""

    def test_runner_writes_graph_diagnostics_parquet(self, tmp_path):
        pytest.importorskip("torch")
        from volforecast.config import (
            CVConfig,
            ExperimentConfig,
            GraphConfig,
            ModelConfig,
        )
        from volforecast.pipeline.runner import Pipeline
        from volforecast.registry import MODEL_REGISTRY, register_model

        @register_model("_fake_graph_dashpanel")
        class _FakeGraphDash:
            REQUIRED_LAYERS: list[str] = []
            requires_sequences = False
            requires_graph = True
            supports_tuning = False
            family = "gnn"
            description = "test double"

            def __init__(self, *, input_dim: int, seed: int = 42, **kwargs):
                self.input_dim = input_dim
                self.seed = seed
                self._mean = 0.0

            def fit(self, graphs, y=None, *, on_progress=None):
                ys = np.concatenate([g["y"] for g in graphs])
                self._mean = float(np.nanmean(ys))
                return self

            def predict(self, graphs):
                n = sum(g["x"].shape[0] for g in graphs)
                return np.full(n, self._mean)

            def get_params(self):
                return {"input_dim": self.input_dim, "seed": self.seed}

        try:
            rng = np.random.default_rng(0)
            dates = pd.bdate_range("2022-01-03", periods=320)
            panel = {}
            for k, sym in enumerate(["AAA", "BBB", "CCC"]):
                log_rv = np.zeros(len(dates))
                log_rv[0] = -9.0
                for t in range(1, len(dates)):
                    log_rv[t] = -9.0 * 0.05 + 0.95 * log_rv[t - 1] + rng.normal(0, 0.3)
                df = pd.DataFrame({"rv": np.exp(log_rv)}, index=dates)
                df.index.name = "date"
                panel[sym] = df

            output_dir = tmp_path / "out"
            output_dir.mkdir()
            cfg = ExperimentConfig(
                name="t_graph_dash",
                universe=["AAA", "BBB", "CCC"],
                date_range=("2022-01-03", "2023-03-31"),
                horizons=[1],
                feature_layers=["har_core"],
                model=ModelConfig(name="_fake_graph_dashpanel", params={}),
                cv=CVConfig(
                    method="expanding_window",
                    purge_gap=5,
                    train_size=150,
                    test_size=50,
                ),
                graph=GraphConfig(
                    method="full", input="log_rv", node_features=["log_rv_d"]
                ),
                fold_cache_enabled=False,
                checkpoint_enabled=False,
                output_dir=output_dir,
            )
            Pipeline(cfg).run_pooled(panel)

            # Look for graph_diagnostics.parquet or a per-horizon variant
            matches = list(output_dir.glob("graph_diagnostics*.parquet"))
            assert matches, f"no graph_diagnostics parquet under {output_dir}"
            df = pd.read_parquet(matches[0])
            for col in ("refit_date", "density", "jaccard_vs_previous", "signal_energy"):
                assert col in df.columns, f"missing column {col}"
            # For a `full` graph on 3 nodes, density should be 1.0 on refits
            # after min_history is met (earlier snapshots may be empty).
            assert (df["density"] > 0.0).any()
        finally:
            MODEL_REGISTRY.pop("_fake_graph_dashpanel", None)
