from __future__ import annotations

import textwrap

import pytest

from volforecast.config import ExperimentConfig, GraphConfig


def _yaml(tmp_path, graph_block: str):
    cfg = textwrap.dedent(f"""\
        name: t
        universe: [SPY, AAPL]
        date_range: ["2020-01-01", "2021-01-01"]
        horizons: [1]
        feature_layers: [har_core]
        model: {{name: har, params: {{}}}}
        {graph_block}
    """)
    p = tmp_path / "t.yaml"
    p.write_text(cfg)
    return p


def test_graph_config_defaults():
    g = GraphConfig()
    assert (g.method, g.window, g.refit_every, g.min_history, g.input) == (
        "corr", 252, 21, 60, "returns"
    )
    assert g.params == {}


def test_from_yaml_parses_graph_block(tmp_path):
    p = _yaml(tmp_path, "graph: {method: glasso, window: 504, refit_every: 21, params: {alpha: 0.1}}")
    cfg = ExperimentConfig.from_yaml(p)
    assert isinstance(cfg.graph, GraphConfig)
    assert cfg.graph.method == "glasso"
    assert cfg.graph.window == 504
    assert cfg.graph.params == {"alpha": 0.1}


def test_from_yaml_graph_absent_is_none(tmp_path):
    cfg = ExperimentConfig.from_yaml(_yaml(tmp_path, ""))
    assert cfg.graph is None


def test_graph_method_changes_fingerprint(tmp_path):
    from volforecast.utils.persistence import _config_fingerprint

    c1 = ExperimentConfig.from_yaml(_yaml(tmp_path, "graph: {method: glasso}"))
    c2 = ExperimentConfig.from_yaml(_yaml(tmp_path, "graph: {method: dy, input: log_rv}"))
    c3 = ExperimentConfig.from_yaml(_yaml(tmp_path, ""))
    fps = {_config_fingerprint(c) for c in (c1, c2, c3)}
    assert len(fps) == 3


def test_unknown_graph_method_rejected_at_parse(tmp_path):
    with pytest.raises(ValueError, match="Unknown graph method"):
        ExperimentConfig.from_yaml(_yaml(tmp_path, "graph: {method: nonexistent_method}"))
