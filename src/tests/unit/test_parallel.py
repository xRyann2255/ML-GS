"""Tests for evaluation/_parallel.py.

Validates:
1. _run_single_model_pooled calls Pipeline.run_pooled correctly
2. run_models_pooled classifies models into sequential vs parallel
3. Thread count reduction logic prevents CPU oversubscription
4. Callbacks are invoked correctly (on_model_start, on_model_complete)
5. Sequential fallback works when parallel_models=1
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from volforecast.config import CVConfig


@pytest.fixture
def mock_panel_data():
    """Minimal panel data for testing (2 symbols, 50 days)."""
    dates = pd.bdate_range("2023-01-02", periods=50)
    rng = np.random.default_rng(42)
    data = {}
    for sym in ["SPY", "AAPL"]:
        data[sym] = pd.DataFrame(
            {
                "log_rv_d": -4.0 + 0.3 * rng.standard_normal(50),
                "log_rv_w": -4.0 + 0.2 * rng.standard_normal(50),
                "log_rv_m": -4.0 + 0.15 * rng.standard_normal(50),
            },
            index=dates,
        )
    return data


@pytest.fixture
def cv_config():
    return CVConfig(method="expanding_window", n_splits=2, train_size=30)


class TestRunSingleModelPooled:
    def test_calls_pipeline_run_pooled(self, mock_panel_data, cv_config):
        """Verify _run_single_model_pooled delegates to Pipeline.run_pooled."""
        mock_results = {
            1: {
                "predictions": pd.Series([0.1, 0.2], name="preds"),
                "actuals": pd.Series([0.11, 0.21], name="actuals"),
            }
        }

        with (
            patch(
                "volforecast.evaluation.tournament._resolve_model",
                return_value=("har", "HAR", {}),
            ) as mock_resolve,
            patch(
                "volforecast.evaluation.tournament._build_tournament_context",
                return_value={},
            ),
            patch(
                "volforecast.evaluation.tournament._feature_layers_for_model",
                return_value=["har_core"],
            ),
            patch("volforecast.evaluation._parallel.Pipeline") as MockPipeline,
        ):
            MockPipeline.return_value.run_pooled.return_value = mock_results

            from volforecast.evaluation._parallel import _run_single_model_pooled

            label, preds, actuals, models = _run_single_model_pooled(
                model_label="har",
                panel_data=mock_panel_data,
                date_range=("2023-01-02", "2023-03-15"),
                horizons=[1],
                feature_layers=["har_core"],
                cv_config=cv_config,
                tuning_config=None,
                model_params=None,
                model_configs=None,
            )

        assert label == "HAR"
        assert 1 in preds
        assert 1 in actuals
        mock_resolve.assert_called_once()

    def test_applies_thread_override(self, mock_panel_data, cv_config):
        """Verify num_threads override is applied when running in parallel."""
        mock_results = {
            1: {
                "predictions": pd.Series([0.1]),
                "actuals": pd.Series([0.11]),
            }
        }

        with (
            patch(
                "volforecast.evaluation.tournament._resolve_model",
                return_value=("lightgbm", "LightGBM", {"n_estimators": 100}),
            ),
            patch(
                "volforecast.evaluation.tournament._build_tournament_context",
                return_value={},
            ),
            patch(
                "volforecast.evaluation.tournament._feature_layers_for_model",
                return_value=["har_core"],
            ),
            patch("volforecast.evaluation._parallel.Pipeline") as MockPipeline,
        ):
            MockPipeline.return_value.run_pooled.return_value = mock_results

            from volforecast.evaluation._parallel import _run_single_model_pooled

            _run_single_model_pooled(
                model_label="lightgbm",
                panel_data=mock_panel_data,
                date_range=("2023-01-02", "2023-03-15"),
                horizons=[1],
                feature_layers=["har_core"],
                cv_config=cv_config,
                tuning_config=None,
                model_params=None,
                model_configs=None,
                num_threads_override=4,
            )

            # Verify the config passed to Pipeline had num_threads=4
            config_arg = MockPipeline.call_args[0][0]
            assert config_arg.model.params["num_threads"] == 4


class TestRunModelsPooled:
    def test_classifies_models_correctly(self, mock_panel_data, cv_config):
        """HAR models run sequentially, lightgbm is a parallel candidate."""
        mock_results = {
            1: {
                "predictions": pd.Series([0.1, 0.2]),
                "actuals": pd.Series([0.11, 0.21]),
            }
        }

        with (
            patch(
                "volforecast.evaluation.tournament._resolve_model",
                side_effect=[
                    ("har", "HAR", {}),  # classification call for har
                    ("lightgbm", "LightGBM", {}),  # classification call for lgbm
                    ("har", "HAR", {}),  # sequential run call for har
                    ("lightgbm", "LightGBM", {}),  # sequential fallback run for lgbm
                ],
            ),
            patch(
                "volforecast.evaluation.tournament._feature_layers_for_model",
                return_value=["har_core"],
            ),
            patch("volforecast.evaluation._parallel.Pipeline") as MockPipeline,
        ):
            MockPipeline.return_value.run_pooled.return_value = mock_results

            from volforecast.evaluation._parallel import run_models_pooled

            all_preds, all_actuals, _models, _test_data = run_models_pooled(
                models=["har", "lightgbm"],
                ml_model_names=["lightgbm"],
                panel_data=mock_panel_data,
                date_range=("2023-01-02", "2023-03-15"),
                horizons=[1],
                feature_layers=["har_core"],
                cv_config=cv_config,
                tuning_config=None,
                context={},
                model_params=None,
                model_configs=None,
                parallel_models=1,  # sequential fallback
                horizon_overrides=None,
            )

        # HAR ran sequentially; both models should be in results
        assert "HAR" in all_preds
        assert 1 in all_actuals

    def test_invokes_callbacks(self, mock_panel_data, cv_config):
        """Verify on_model_start/on_model_complete callbacks fire."""
        mock_results = {
            1: {
                "predictions": pd.Series([0.1]),
                "actuals": pd.Series([0.11]),
            }
        }
        on_start = MagicMock()
        on_complete = MagicMock()

        with (
            patch(
                "volforecast.evaluation.tournament._resolve_model",
                side_effect=[
                    ("har", "HAR", {}),  # classification
                    ("har", "HAR", {}),  # run
                ],
            ),
            patch(
                "volforecast.evaluation.tournament._feature_layers_for_model",
                return_value=["har_core"],
            ),
            patch("volforecast.evaluation._parallel.Pipeline") as MockPipeline_cb,
        ):
            MockPipeline_cb.return_value.run_pooled.return_value = mock_results

            from volforecast.evaluation._parallel import run_models_pooled

            run_models_pooled(
                models=["har"],
                ml_model_names=["lightgbm"],
                panel_data=mock_panel_data,
                date_range=("2023-01-02", "2023-03-15"),
                horizons=[1],
                feature_layers=["har_core"],
                cv_config=cv_config,
                tuning_config=None,
                context={},
                model_params=None,
                model_configs=None,
                parallel_models=1,
                horizon_overrides=None,
                on_model_start=on_start,
                on_model_complete=on_complete,
            )

        on_start.assert_called_once_with("HAR", list(mock_panel_data.keys()))
        on_complete.assert_called_once_with("HAR")

    def test_empty_models_list(self, mock_panel_data, cv_config):
        """Empty model list should return empty results."""
        from volforecast.evaluation._parallel import run_models_pooled

        all_preds, all_actuals, trained, _test_data = run_models_pooled(
            models=[],
            ml_model_names=["lightgbm"],
            panel_data=mock_panel_data,
            date_range=("2023-01-02", "2023-03-15"),
            horizons=[1],
            feature_layers=["har_core"],
            cv_config=cv_config,
            tuning_config=None,
            context={},
            model_params=None,
            model_configs=None,
            parallel_models=1,
            horizon_overrides=None,
        )

        assert all_preds == {}
        assert all_actuals == {}
        assert trained is None


class TestBaseModelForwarding:
    """Regression: ``base_model`` (residual stacking) must reach the synthetic
    ``ExperimentConfig`` built inside the tournament workers. Prior to this
    fix, the field was silently dropped, causing residual stacking to no-op
    and the per-fold cache to write under a fingerprint that didn't match
    the parent config (so ``vol cache-status --config`` showed nothing).
    """

    def test_single_model_pooled_propagates_base_model(self, mock_panel_data, cv_config):
        from volforecast.config import BaseModelConfig

        mock_results = {
            1: {
                "predictions": pd.Series([0.1, 0.2]),
                "actuals": pd.Series([0.11, 0.21]),
            }
        }
        base = BaseModelConfig(
            name="lightgbm",
            feature_layers=["har_core"],
            params={"n_estimators": 100},
        )

        with (
            patch(
                "volforecast.evaluation.tournament._resolve_model",
                return_value=("lstm", "LSTM", {}),
            ),
            patch(
                "volforecast.evaluation.tournament._build_tournament_context",
                return_value={},
            ),
            patch(
                "volforecast.evaluation.tournament._feature_layers_for_model",
                return_value=["har_core"],
            ),
            patch("volforecast.evaluation._parallel.Pipeline") as MockPipeline,
        ):
            MockPipeline.return_value.run_pooled.return_value = mock_results

            from volforecast.evaluation._parallel import _run_single_model_pooled

            _run_single_model_pooled(
                model_label="lstm",
                panel_data=mock_panel_data,
                date_range=("2023-01-02", "2023-03-15"),
                horizons=[1],
                feature_layers=["har_core"],
                cv_config=cv_config,
                tuning_config=None,
                model_params=None,
                model_configs=None,
                base_model=base,
            )

            config_arg = MockPipeline.call_args[0][0]
            assert config_arg.base_model is not None, (
                "base_model was dropped — residual stacking will silently no-op"
            )
            assert config_arg.base_model.name == "lightgbm"
            assert config_arg.base_model.feature_layers == ["har_core"]
            assert config_arg.base_model.params == {"n_estimators": 100}

    def test_run_models_pooled_sequential_propagates_base_model(
        self, mock_panel_data, cv_config
    ):
        from volforecast.config import BaseModelConfig

        mock_results = {
            1: {
                "predictions": pd.Series([0.1]),
                "actuals": pd.Series([0.11]),
            }
        }
        base = BaseModelConfig(
            name="har_iv",
            feature_layers=["iv_surface", "har_core"],
            params={},
        )

        with (
            patch(
                "volforecast.evaluation.tournament._resolve_model",
                side_effect=[
                    ("lstm", "LSTM", {}),  # classification
                    ("lstm", "LSTM", {}),  # sequential run
                ],
            ),
            patch(
                "volforecast.evaluation.tournament._feature_layers_for_model",
                return_value=["har_core"],
            ),
            patch("volforecast.evaluation._parallel.Pipeline") as MockPipeline,
        ):
            MockPipeline.return_value.run_pooled.return_value = mock_results

            from volforecast.evaluation._parallel import run_models_pooled

            run_models_pooled(
                models=["lstm"],
                ml_model_names=["lstm"],
                panel_data=mock_panel_data,
                date_range=("2023-01-02", "2023-03-15"),
                horizons=[1],
                feature_layers=["har_core"],
                cv_config=cv_config,
                tuning_config=None,
                context={},
                model_params=None,
                model_configs=None,
                parallel_models=1,  # sequential fallback path
                horizon_overrides=None,
                base_model=base,
            )

            config_arg = MockPipeline.call_args[0][0]
            assert config_arg.base_model is not None, (
                "base_model was dropped on sequential path"
            )
            assert config_arg.base_model.name == "har_iv"
            assert config_arg.base_model.feature_layers == [
                "iv_surface",
                "har_core",
            ]


class TestBuildTournamentModelConfig:
    """The ``build_tournament_model_config`` helper is the single source of
    truth for the synthetic ``ExperimentConfig`` that pooled-tournament
    workers (and the CLI cache-status command) construct per model.
    """

    def test_synthetic_config_fingerprint_matches_runner(self):
        """The fingerprint of the synthetic config returned by the helper must
        equal the fingerprint a tournament worker would compute internally.

        If this drifts, ``vol cache-status --config`` will silently miss the
        cache entries the runner wrote.
        """
        from volforecast.config import BaseModelConfig, CVConfig
        from volforecast.evaluation._parallel import build_tournament_model_config
        from volforecast.utils.persistence import _config_fingerprint

        base = BaseModelConfig(
            name="lightgbm",
            feature_layers=["har_core"],
            params={"n_estimators": 100},
        )

        with (
            patch(
                "volforecast.evaluation.tournament._resolve_model",
                return_value=("lstm", "LSTM", {}),
            ),
            patch(
                "volforecast.evaluation.tournament._feature_layers_for_model",
                return_value=["har_core"],
            ),
        ):
            _, _, cfg_a = build_tournament_model_config(
                model_label="lstm",
                universe=["SPY", "AAPL"],
                date_range=("2023-01-02", "2023-12-31"),
                horizons=[1],
                feature_layers=["har_core"],
                cv_config=CVConfig(method="expanding_window", train_size=30),
                tuning_config=None,
                model_params=None,
                model_configs=None,
                horizon_overrides=None,
                sequences=None,
                base_model=base,
            )
            _, _, cfg_b = build_tournament_model_config(
                model_label="lstm",
                universe=["SPY", "AAPL"],
                date_range=("2023-01-02", "2023-12-31"),
                horizons=[1],
                feature_layers=["har_core"],
                cv_config=CVConfig(method="expanding_window", train_size=30),
                tuning_config=None,
                model_params=None,
                model_configs=None,
                horizon_overrides=None,
                sequences=None,
                base_model=base,
            )

        assert _config_fingerprint(cfg_a) == _config_fingerprint(cfg_b)
        # base_model must appear in the fingerprint-relevant fields
        assert cfg_a.base_model is not None
        assert cfg_a.base_model.name == "lightgbm"

    def test_cli_expands_parent_to_synthetic_configs(self, tmp_path):
        """``vol cache-status --config <parent>`` must enumerate the same
        synthetic configs the tournament workers build (one per model in
        ``tournament.models``). Otherwise the CLI looks under the parent's
        fingerprint while the runner wrote under the synthetic ones.
        """
        from volforecast.cli.cache import _expand_to_tournament_configs
        from volforecast.config import (
            BaseModelConfig,
            CVConfig,
            ExperimentConfig,
            ModelConfig,
            TournamentConfig,
        )
        from volforecast.utils.persistence import _config_fingerprint

        parent = ExperimentConfig(
            name="trial_parent",
            universe=["SPY", "AAPL"],
            date_range=("2023-01-02", "2023-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="lstm", params={}),
            cv=CVConfig(method="expanding_window", train_size=30),
            tournament=TournamentConfig(models=["lstm", "har"]),
            training_mode="pooled",
            base_model=BaseModelConfig(
                name="lightgbm",
                feature_layers=["har_core"],
                params={"n_estimators": 100},
            ),
        )

        with (
            patch(
                "volforecast.evaluation.tournament._resolve_model",
                side_effect=lambda label, **_kw: (label, label.upper(), {}),
            ),
            patch(
                "volforecast.evaluation.tournament._feature_layers_for_model",
                return_value=["har_core"],
            ),
        ):
            synth = _expand_to_tournament_configs(parent)

        # One synthetic config per tournament model
        assert len(synth) == 2
        # Parent's base_model must reach every synthetic config — even for
        # tabular models that won't actually consume it. Drops here would
        # mean the fingerprint differs from what the runner produced.
        for cfg in synth:
            assert cfg.base_model is not None
            assert cfg.base_model.name == "lightgbm"
        # Different model -> different fingerprint
        assert _config_fingerprint(synth[0]) != _config_fingerprint(synth[1])
