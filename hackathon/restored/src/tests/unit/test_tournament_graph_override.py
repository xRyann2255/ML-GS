"""Unit tests for per-label graph overrides in tournament model_configs.

Tests that a tournament entry can carry a 'graph' dict that overrides the
experiment-level graph block on its synthetic per-model ExperimentConfig.
"""

from __future__ import annotations

import pytest

from volforecast.config import (
    CVConfig,
    ExperimentConfig,
    GraphConfig,
    ModelConfig,
    TournamentConfig,
)
from volforecast.evaluation._parallel import build_tournament_model_config


@pytest.fixture
def cv_config():
    return CVConfig(method="expanding_window", purge_gap=5, train_size=504, test_size=126)


def test_label_graph_override_applied(cv_config):
    """model_configs entry with a 'graph' dict overrides experiment-level graph."""
    _, _, cfg = build_tournament_model_config(
        model_label="ghar_glasso",
        universe=["SPY", "AAPL"],
        date_range=("2020-01-01", "2021-01-01"),
        horizons=[1],
        feature_layers=["har_core"],
        cv_config=cv_config,
        tuning_config=None,
        model_params=None,
        model_configs={
            "ghar_glasso": {
                "name": "ghar",
                "params": {"input_dim": 3},
                "graph": {"method": "glasso", "window": 1000},
            },
        },
        horizon_overrides=None,
        sequences=None,
        base_model=None,
        graph=GraphConfig(method="corr", window=252),
    )
    assert cfg.graph is not None
    assert cfg.graph.method == "glasso"
    assert cfg.graph.window == 1000


def test_label_without_override_inherits_experiment_graph(cv_config):
    """model_configs entry without a 'graph' dict inherits the experiment-level graph."""
    _, _, cfg = build_tournament_model_config(
        model_label="ghar_full",
        universe=["SPY", "AAPL"],
        date_range=("2020-01-01", "2021-01-01"),
        horizons=[1],
        feature_layers=["har_core"],
        cv_config=cv_config,
        tuning_config=None,
        model_params=None,
        model_configs={
            "ghar_full": {"name": "ghar", "params": {"input_dim": 3}},
        },
        horizon_overrides=None,
        sequences=None,
        base_model=None,
        graph=GraphConfig(method="corr", window=252),
    )
    assert cfg.graph is not None
    assert cfg.graph.method == "corr"


def test_no_experiment_graph_no_override_is_none(cv_config):
    """Without experiment-level graph and no per-label override, graph stays None."""
    _, _, cfg = build_tournament_model_config(
        model_label="har",
        universe=["SPY", "AAPL"],
        date_range=("2020-01-01", "2021-01-01"),
        horizons=[1],
        feature_layers=["har_core"],
        cv_config=cv_config,
        tuning_config=None,
        model_params=None,
        model_configs=None,
        horizon_overrides=None,
        sequences=None,
        base_model=None,
        graph=None,
    )
    assert cfg.graph is None


def test_invalid_override_method_raises(cv_config):
    """Invalid graph method in override raises ValueError at config time."""
    with pytest.raises(ValueError, match="Unknown graph method"):
        build_tournament_model_config(
            model_label="ghar_bad",
            universe=["SPY", "AAPL"],
            date_range=("2020-01-01", "2021-01-01"),
            horizons=[1],
            feature_layers=["har_core"],
            cv_config=cv_config,
            tuning_config=None,
            model_params=None,
            model_configs={
                "ghar_bad": {
                    "name": "ghar",
                    "params": {"input_dim": 3},
                    "graph": {"method": "bogus"},
                },
            },
            horizon_overrides=None,
            sequences=None,
            base_model=None,
            graph=GraphConfig(method="corr"),
        )


def test_bare_label_gets_experiment_graph(cv_config):
    """A model label not in model_configs still gets the experiment-level graph."""
    _, _, cfg = build_tournament_model_config(
        model_label="har",
        universe=["SPY", "AAPL"],
        date_range=("2020-01-01", "2021-01-01"),
        horizons=[1],
        feature_layers=["har_core"],
        cv_config=cv_config,
        tuning_config=None,
        model_params=None,
        model_configs=None,
        horizon_overrides=None,
        sequences=None,
        base_model=None,
        graph=GraphConfig(method="corr", window=60),
    )
    assert cfg.graph is not None
    assert cfg.graph.method == "corr"
    assert cfg.graph.window == 60
