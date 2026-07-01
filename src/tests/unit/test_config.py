"""Tests for experiment configuration dataclasses and YAML serde.

Validates:
1. ExperimentConfig round-trips through YAML
2. Default values are applied correctly
3. ModelConfig / CVConfig construction
"""

from __future__ import annotations

import pytest

from volforecast.config import (
    BlendConfig,
    BlendSubModelConfig,
    CVConfig,
    ExperimentConfig,
    ModelConfig,
    TournamentConfig,
    TuningConfig,
)


@pytest.fixture
def sample_config() -> ExperimentConfig:
    return ExperimentConfig(
        name="test_experiment",
        universe=["SPY", "AAPL"],
        date_range=("2020-01-01", "2023-12-31"),
        horizons=[1, 5, 22],
        feature_layers=["har_core", "asymmetry"],
        model=ModelConfig(name="har", params={"alpha": 0.1}),
        cv=CVConfig(method="expanding_window", n_splits=5, purge_gap=5),
    )


class TestModelConfig:
    def test_defaults(self):
        cfg = ModelConfig(name="har")
        assert cfg.name == "har"
        assert cfg.params == {}

    def test_with_params(self):
        cfg = ModelConfig(name="lightgbm", params={"n_estimators": 100})
        assert cfg.params["n_estimators"] == 100


class TestCVConfig:
    def test_defaults(self):
        cfg = CVConfig()
        assert cfg.method == "expanding_window"
        assert cfg.n_splits == 5
        assert cfg.purge_gap == 5
        assert cfg.train_size is None
        assert cfg.test_size is None

    def test_cv_config_embargo_default_zero(self):
        """Phase 2.8: embargo defaults to 0 so no existing trial QLIKE moves."""
        cfg = CVConfig()
        assert cfg.embargo == 0


class TestExperimentConfig:
    def test_round_trip_yaml(self, sample_config, tmp_path):
        yaml_path = tmp_path / "test_config.yaml"
        sample_config.to_yaml(yaml_path)
        loaded = ExperimentConfig.from_yaml(yaml_path)

        assert loaded.name == sample_config.name
        assert loaded.universe == sample_config.universe
        assert loaded.date_range == tuple(sample_config.date_range)
        assert loaded.horizons == sample_config.horizons
        assert loaded.feature_layers == sample_config.feature_layers
        assert loaded.model.name == sample_config.model.name
        assert loaded.model.params == sample_config.model.params
        assert loaded.cv.method == sample_config.cv.method
        assert loaded.cv.n_splits == sample_config.cv.n_splits
        assert loaded.seed == sample_config.seed

    def test_defaults_applied(self):
        cfg = ExperimentConfig(
            name="minimal",
            universe=["SPY"],
            date_range=("2022-01-01", "2022-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
        )
        assert cfg.training_mode == "pooled"
        assert cfg.seed == 42
        assert cfg.cv.method == "expanding_window"

    def test_yaml_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c" / "config.yaml"
        cfg = ExperimentConfig(
            name="nested_test",
            universe=["SPY"],
            date_range=("2022-01-01", "2022-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
        )
        cfg.to_yaml(nested)
        assert nested.exists()


class TestTuningConfig:
    def test_defaults(self):
        cfg = TuningConfig()
        assert cfg.enabled is False
        assert cfg.n_trials == 50
        assert cfg.timeout == 600
        assert cfg.storage_dir is None
        assert cfg.inner_cv is None
        assert cfg.min_train_size == 252


class TestEffectiveModels:
    def test_effective_models_from_tournament_list(self):
        """When tournament.models is set, effective_models returns it."""
        from volforecast.config import TournamentConfig

        cfg = ExperimentConfig(
            name="test",
            universe=["SPY"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            tournament=TournamentConfig(models=["har", "ridge_har", "lasso_har"]),
        )
        assert cfg.effective_models == ["har", "ridge_har", "lasso_har"]

    def test_effective_models_inferred_from_model_name(self):
        """When tournament.models is empty, effective_models infers from model.name."""
        cfg = ExperimentConfig(
            name="test",
            universe=["SPY"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
        )
        assert cfg.effective_models == ["har"]

    def test_mode_pipeline_loads_without_error(self, tmp_path):
        """Config with mode: pipeline loads successfully (backward compat)."""
        yaml_content = """\
name: legacy_test
universe: [SPY]
date_range: ["2020-01-01", "2023-12-31"]
horizons: [1]
feature_layers: [har_core]
model:
  name: har
  params: {}
mode: pipeline
output_dir: data/models/test
"""
        yaml_path = tmp_path / "legacy.yaml"
        yaml_path.write_text(yaml_content)
        cfg = ExperimentConfig.from_yaml(yaml_path)
        assert cfg.name == "legacy_test"
        # mode is accepted but has no special runtime meaning anymore
        assert cfg.effective_models == ["har"]

    def test_round_trip_yaml_tuning_enabled(self, tmp_path):
        from pathlib import Path

        inner = CVConfig(method="expanding_window", train_size=300, test_size=50, purge_gap=5)
        cfg = ExperimentConfig(
            name="tuning_test",
            universe=["SPY"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1, 5],
            feature_layers=["har_core"],
            model=ModelConfig(name="lightgbm"),
            tuning=TuningConfig(
                enabled=True,
                n_trials=30,
                timeout=300,
                storage_dir=Path("/tmp/optuna"),
                inner_cv=inner,
                min_train_size=200,
            ),
        )
        yaml_path = tmp_path / "tuning.yaml"
        cfg.to_yaml(yaml_path)
        loaded = ExperimentConfig.from_yaml(yaml_path)

        assert loaded.tuning.enabled is True
        assert loaded.tuning.n_trials == 30
        assert loaded.tuning.timeout == 300
        assert loaded.tuning.storage_dir == Path("/tmp/optuna")
        assert loaded.tuning.inner_cv is not None
        assert loaded.tuning.inner_cv.train_size == 300
        assert loaded.tuning.inner_cv.test_size == 50
        assert loaded.tuning.min_train_size == 200

    def test_round_trip_yaml_tuning_disabled(self, tmp_path):
        cfg = ExperimentConfig(
            name="no_tuning",
            universe=["SPY"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
        )
        yaml_path = tmp_path / "no_tuning.yaml"
        cfg.to_yaml(yaml_path)
        loaded = ExperimentConfig.from_yaml(yaml_path)

        assert loaded.tuning.enabled is False
        assert loaded.tuning.n_trials == 50


class TestTournamentModelConfigs:
    """Tests for tournament.model_configs YAML round-trip."""

    def test_round_trip_with_model_configs(self, tmp_path):
        """model_configs serializes and deserializes correctly."""
        cfg = ExperimentConfig(
            name="multi_lgbm",
            universe=["SPY", "AAPL"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1, 5],
            feature_layers=["har_core", "asymmetry"],
            model=ModelConfig(name="lightgbm", params={"num_leaves": 16}),
            tournament=TournamentConfig(
                models=["har", "lightgbm", "lgbm_v2"],
                model_configs={
                    "lgbm_v2": {
                        "name": "lightgbm",
                        "params": {"num_leaves": 31, "max_depth": 6},
                    },
                },
            ),
        )
        yaml_path = tmp_path / "multi_lgbm.yaml"
        cfg.to_yaml(yaml_path)
        loaded = ExperimentConfig.from_yaml(yaml_path)

        assert loaded.tournament.models == ["har", "lightgbm", "lgbm_v2"]
        assert loaded.tournament.model_configs == {
            "lgbm_v2": {
                "name": "lightgbm",
                "params": {"num_leaves": 31, "max_depth": 6},
            },
        }

    def test_round_trip_without_model_configs(self, tmp_path):
        """Existing configs without model_configs still work."""
        cfg = ExperimentConfig(
            name="simple",
            universe=["SPY"],
            date_range=("2020-01-01", "2023-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            tournament=TournamentConfig(models=["har", "lightgbm"]),
        )
        yaml_path = tmp_path / "simple.yaml"
        cfg.to_yaml(yaml_path)
        loaded = ExperimentConfig.from_yaml(yaml_path)

        assert loaded.tournament.models == ["har", "lightgbm"]
        assert loaded.tournament.model_configs == {}

    def test_model_configs_defaults_empty(self):
        """TournamentConfig.model_configs defaults to empty dict."""
        cfg = TournamentConfig()
        assert cfg.model_configs == {}


class TestGsvivsSizingsConfig:
    """gsvivs_sizings: 3-mode toggle (binary | asym_long | zscore).

    Default = ``None`` (resolves to :data:`DEFAULT_GSVIVS_SIZING_SPECS` at
    runtime). Custom YAML can override with an explicit list of spec dicts.
    """

    def test_default_is_none(self):
        """TournamentConfig.gsvivs_sizings defaults to None so the runtime
        falls back to the project default (binary | asym_long L=2 | zscore L=1)."""
        cfg = TournamentConfig()
        assert cfg.gsvivs_sizings is None

    def test_yaml_omitted_means_default(self, tmp_path):
        """A YAML config that doesn't mention gsvivs_sizings parses to None."""
        from volforecast.config import ExperimentConfig, ModelConfig

        cfg = ExperimentConfig(
            name="x",
            universe=["SPY"],
            date_range=("2020-01-01", "2024-12-31"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            tournament=TournamentConfig(),
        )
        path = tmp_path / "no_sizings.yaml"
        cfg.to_yaml(path)
        loaded = ExperimentConfig.from_yaml(path)
        assert loaded.tournament.gsvivs_sizings is None

    def test_yaml_parses_explicit_sizings_list(self, tmp_path):
        """Explicit YAML list of sizing dicts roundtrips into TournamentConfig
        as a tuple of GsvivsSizingSpec instances."""
        import yaml

        from volforecast.config import ExperimentConfig
        from volforecast.evaluation.economic_value import GsvivsSizingSpec

        raw_yaml = {
            "name": "x",
            "universe": ["SPY"],
            "date_range": ["2020-01-01", "2024-12-31"],
            "horizons": [1],
            "feature_layers": ["har_core"],
            "model": {"name": "har"},
            "tournament": {
                "gsvivs_sizings": [
                    {"mode": "binary"},
                    {"mode": "asym_long", "max_leverage": 3.0, "lookback": 42},
                ],
            },
        }
        path = tmp_path / "with_sizings.yaml"
        path.write_text(yaml.safe_dump(raw_yaml))
        loaded = ExperimentConfig.from_yaml(path)
        sizings = loaded.tournament.gsvivs_sizings
        assert sizings is not None
        assert len(sizings) == 2
        assert isinstance(sizings[0], GsvivsSizingSpec)
        assert sizings[0].mode == "binary"
        assert sizings[1].mode == "asym_long"
        assert sizings[1].max_leverage == 3.0
        assert sizings[1].lookback == 42

    def test_yaml_string_shorthand_for_sizings(self, tmp_path):
        """YAML shorthand: a string entry maps to a spec with defaults."""
        import yaml

        from volforecast.config import ExperimentConfig

        raw_yaml = {
            "name": "x",
            "universe": ["SPY"],
            "date_range": ["2020-01-01", "2024-12-31"],
            "horizons": [1],
            "feature_layers": ["har_core"],
            "model": {"name": "har"},
            "tournament": {"gsvivs_sizings": ["binary", "zscore"]},
        }
        path = tmp_path / "shorthand_sizings.yaml"
        path.write_text(yaml.safe_dump(raw_yaml))
        loaded = ExperimentConfig.from_yaml(path)
        sizings = loaded.tournament.gsvivs_sizings
        assert sizings is not None
        assert [s.mode for s in sizings] == ["binary", "zscore"]


class TestGsvivsIvSources:
    """Config parsing for gsvivs_iv_sources field."""

    def test_default_is_exec_kvar(self):
        cfg = TournamentConfig()
        assert cfg.gsvivs_iv_sources == ["exec_kvar"]

    def test_parse_single_source(self, tmp_path):
        yaml_path = tmp_path / "cfg.yaml"
        yaml_path.write_text(
            "name: test\n"
            "universe: [SPY]\n"
            "date_range: ['2020-01-01', '2023-12-31']\n"
            "horizons: [1]\n"
            "feature_layers: [har_core]\n"
            "model:\n  name: har\n"
            "tournament:\n"
            "  gsvivs_iv_sources:\n"
            "    - exec_kvar\n"
        )
        cfg = ExperimentConfig.from_yaml(yaml_path)
        assert cfg.tournament.gsvivs_iv_sources == ["exec_kvar"]

    def test_parse_multiple_sources(self, tmp_path):
        yaml_path = tmp_path / "cfg.yaml"
        yaml_path.write_text(
            "name: test\n"
            "universe: [SPY]\n"
            "date_range: ['2020-01-01', '2023-12-31']\n"
            "horizons: [1]\n"
            "feature_layers: [har_core]\n"
            "model:\n  name: har\n"
            "tournament:\n"
            "  gsvivs_iv_sources:\n"
            "    - exec_kvar\n"
            "    - edrvs_prev_close_1dte\n"
            "    - spx_atm_iv_1w\n"
        )
        cfg = ExperimentConfig.from_yaml(yaml_path)
        assert cfg.tournament.gsvivs_iv_sources == ["exec_kvar", "edrvs_prev_close_1dte", "spx_atm_iv_1w"]

    def test_parse_absent_defaults_to_exec_kvar(self, tmp_path):
        yaml_path = tmp_path / "cfg.yaml"
        yaml_path.write_text(
            "name: test\n"
            "universe: [SPY]\n"
            "date_range: ['2020-01-01', '2023-12-31']\n"
            "horizons: [1]\n"
            "feature_layers: [har_core]\n"
            "model:\n  name: har\n"
            "tournament: {}\n"
        )
        cfg = ExperimentConfig.from_yaml(yaml_path)
        assert cfg.tournament.gsvivs_iv_sources == ["exec_kvar"]

    def test_parse_invalid_source_raises(self, tmp_path):
        yaml_path = tmp_path / "cfg.yaml"
        yaml_path.write_text(
            "name: test\n"
            "universe: [SPY]\n"
            "date_range: ['2020-01-01', '2023-12-31']\n"
            "horizons: [1]\n"
            "feature_layers: [har_core]\n"
            "model:\n  name: har\n"
            "tournament:\n"
            "  gsvivs_iv_sources:\n"
            "    - invalid_source\n"
        )
        with pytest.raises(ValueError, match="Unknown IV source"):
            ExperimentConfig.from_yaml(yaml_path)

    def test_parse_empty_list_defaults_to_exec_kvar(self, tmp_path):
        yaml_path = tmp_path / "cfg.yaml"
        yaml_path.write_text(
            "name: test\n"
            "universe: [SPY]\n"
            "date_range: ['2020-01-01', '2023-12-31']\n"
            "horizons: [1]\n"
            "feature_layers: [har_core]\n"
            "model:\n  name: har\n"
            "tournament:\n"
            "  gsvivs_iv_sources: []\n"
        )
        cfg = ExperimentConfig.from_yaml(yaml_path)
        assert cfg.tournament.gsvivs_iv_sources == ["exec_kvar"]


# ---------------------------------------------------------------------------
# BlendConfig dataclass parsing, validation, and YAML round-trip
# ---------------------------------------------------------------------------


def _minimal_experiment(**overrides) -> dict:
    """Return a minimal ExperimentConfig kwargs dict with optional overrides."""
    base = dict(
        name="blend_test",
        universe=["SPY"],
        date_range=("2020-01-01", "2023-12-31"),
        horizons=[1],
        feature_layers=["har_core"],
        model=ModelConfig(name="har"),
    )
    base.update(overrides)
    return base


def _minimal_yaml(**extra_keys) -> str:
    """Return minimal YAML string; caller can add extra top-level keys."""
    lines = [
        "name: blend_test",
        "universe: [SPY]",
        "date_range: ['2020-01-01', '2023-12-31']",
        "horizons: [1]",
        "feature_layers: [har_core]",
        "model:",
        "  name: har",
    ]
    for k, v in extra_keys.items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines) + "\n"


class TestBlendConfig:
    """Validation rules for BlendConfig dataclass."""

    def test_blend_config_none_by_default(self):
        """ExperimentConfig without blend should have blend = None."""
        cfg = ExperimentConfig(**_minimal_experiment())
        assert cfg.blend is None

    def test_blend_config_validation_min_models(self):
        """BlendConfig with < 2 models should raise ValueError."""
        with pytest.raises(ValueError, match="at least 2"):
            BlendConfig(
                models=[
                    BlendSubModelConfig(name="har"),
                ],
            )

    def test_blend_config_validation_fixed_weights_sum(self):
        """fixed weights not summing to 1.0 should raise ValueError."""
        with pytest.raises(ValueError, match="sum to 1"):
            BlendConfig(
                models=[
                    BlendSubModelConfig(name="har"),
                    BlendSubModelConfig(name="lightgbm"),
                ],
                weight_method="fixed",
                fixed_weights=[0.3, 0.3],
            )

    def test_blend_config_validation_invalid_method(self):
        """Invalid weight_method should raise ValueError."""
        with pytest.raises(ValueError, match="weight_method"):
            BlendConfig(
                models=[
                    BlendSubModelConfig(name="har"),
                    BlendSubModelConfig(name="lightgbm"),
                ],
                weight_method="magic",
            )

    def test_blend_config_validation_fixed_weights_length(self):
        """fixed weights with wrong length should raise ValueError."""
        with pytest.raises(ValueError, match="length"):
            BlendConfig(
                models=[
                    BlendSubModelConfig(name="har"),
                    BlendSubModelConfig(name="lightgbm"),
                ],
                weight_method="fixed",
                fixed_weights=[1.0],  # 1 weight but 2 models
            )

    def test_blend_config_validation_regime_needs_indicator(self):
        """regime_dependent without regime_indicator should raise ValueError."""
        with pytest.raises(ValueError, match="regime_indicator"):
            BlendConfig(
                models=[
                    BlendSubModelConfig(name="har"),
                    BlendSubModelConfig(name="lightgbm"),
                ],
                weight_method="regime_dependent",
                regime_indicator=None,
            )


class TestBlendConfigYAML:
    """YAML round-trip tests for BlendConfig."""

    def test_blend_none_when_absent(self, tmp_path):
        """YAML without blend key parses to ExperimentConfig.blend == None."""
        yaml_path = tmp_path / "no_blend.yaml"
        yaml_path.write_text(_minimal_yaml())
        cfg = ExperimentConfig.from_yaml(yaml_path)
        assert cfg.blend is None

    def test_blend_from_yaml_inverse_qlike(self, tmp_path):
        """YAML with inverse_qlike blend parses correctly."""
        yaml_path = tmp_path / "blend_iq.yaml"
        yaml_path.write_text(
            _minimal_yaml()
            + "blend:\n"
            "  weight_method: inverse_qlike\n"
            "  models:\n"
            "    - name: har\n"
            "      feature_layers: [har_core]\n"
            "    - name: lightgbm\n"
            "      feature_layers: [har_core, asymmetry]\n"
            "      params:\n"
            "        num_leaves: 16\n"
        )
        cfg = ExperimentConfig.from_yaml(yaml_path)
        assert cfg.blend is not None
        assert isinstance(cfg.blend, BlendConfig)
        assert cfg.blend.weight_method == "inverse_qlike"
        assert len(cfg.blend.models) == 2
        assert cfg.blend.models[0].name == "har"
        assert cfg.blend.models[1].name == "lightgbm"
        assert cfg.blend.models[1].params == {"num_leaves": 16}

    def test_blend_from_yaml_fixed_weights(self, tmp_path):
        """YAML with fixed weights parses correctly."""
        yaml_path = tmp_path / "blend_fixed.yaml"
        yaml_path.write_text(
            _minimal_yaml()
            + "blend:\n"
            "  weight_method: fixed\n"
            "  fixed_weights: [0.6, 0.4]\n"
            "  models:\n"
            "    - name: har\n"
            "    - name: shar\n"
        )
        cfg = ExperimentConfig.from_yaml(yaml_path)
        assert cfg.blend is not None
        assert cfg.blend.weight_method == "fixed"
        assert cfg.blend.fixed_weights == [0.6, 0.4]
        assert len(cfg.blend.models) == 2

    def test_blend_from_yaml_regime_dependent(self, tmp_path):
        """YAML with regime_dependent method parses correctly."""
        yaml_path = tmp_path / "blend_regime.yaml"
        yaml_path.write_text(
            _minimal_yaml()
            + "blend:\n"
            "  weight_method: regime_dependent\n"
            "  regime_indicator: vix_level\n"
            "  regime_threshold: 0.75\n"
            "  regime_threshold_type: percentile\n"
            "  models:\n"
            "    - name: har\n"
            "    - name: lightgbm\n"
        )
        cfg = ExperimentConfig.from_yaml(yaml_path)
        assert cfg.blend is not None
        assert cfg.blend.weight_method == "regime_dependent"
        assert cfg.blend.regime_indicator == "vix_level"
        assert cfg.blend.regime_threshold == 0.75
        assert cfg.blend.regime_threshold_type == "percentile"

    def test_blend_sub_model_with_sequences(self, tmp_path):
        """Sub-model with sequences block parses into SequenceConfig."""
        from volforecast.config import SequenceConfig

        yaml_path = tmp_path / "blend_seq.yaml"
        yaml_path.write_text(
            _minimal_yaml()
            + "blend:\n"
            "  weight_method: inverse_qlike\n"
            "  models:\n"
            "    - name: lstm\n"
            "      sequences:\n"
            "        features: [log_ret, vol_share]\n"
            "        max_bars: 500\n"
            "        source: parquet\n"
            "    - name: har\n"
        )
        cfg = ExperimentConfig.from_yaml(yaml_path)
        assert cfg.blend is not None
        lstm_sub = cfg.blend.models[0]
        assert lstm_sub.name == "lstm"
        assert isinstance(lstm_sub.sequences, SequenceConfig)
        assert lstm_sub.sequences.features == ["log_ret", "vol_share"]
        assert lstm_sub.sequences.max_bars == 500

    def test_blend_sub_model_with_base_model(self, tmp_path):
        """Sub-model with base_model block parses into BaseModelConfig."""
        from volforecast.config import BaseModelConfig

        yaml_path = tmp_path / "blend_base.yaml"
        yaml_path.write_text(
            _minimal_yaml()
            + "blend:\n"
            "  weight_method: inverse_qlike\n"
            "  models:\n"
            "    - name: lstm\n"
            "      base_model:\n"
            "        name: har_iv\n"
            "        feature_layers: [har_core, implied]\n"
            "        params:\n"
            "          alpha: 0.5\n"
            "    - name: har\n"
        )
        cfg = ExperimentConfig.from_yaml(yaml_path)
        assert cfg.blend is not None
        lstm_sub = cfg.blend.models[0]
        assert lstm_sub.name == "lstm"
        assert isinstance(lstm_sub.base_model, BaseModelConfig)
        assert lstm_sub.base_model.name == "har_iv"
        assert lstm_sub.base_model.feature_layers == ["har_core", "implied"]
        assert lstm_sub.base_model.params == {"alpha": 0.5}

    def test_blend_round_trip_yaml(self, tmp_path):
        """Write then read a config with blend, verify all fields survive."""
        blend = BlendConfig(
            models=[
                BlendSubModelConfig(
                    name="har",
                    feature_layers=["har_core"],
                ),
                BlendSubModelConfig(
                    name="lightgbm",
                    feature_layers=["har_core", "asymmetry"],
                    params={"num_leaves": 31},
                ),
            ],
            weight_method="inverse_qlike",
            val_fraction=0.25,
            val_purge_gap=15,
        )
        cfg = ExperimentConfig(**_minimal_experiment(blend=blend))
        yaml_path = tmp_path / "rt_blend.yaml"
        cfg.to_yaml(yaml_path)
        loaded = ExperimentConfig.from_yaml(yaml_path)

        assert loaded.blend is not None
        assert loaded.blend.weight_method == "inverse_qlike"
        assert loaded.blend.val_fraction == 0.25
        assert loaded.blend.val_purge_gap == 15
        assert len(loaded.blend.models) == 2
        assert loaded.blend.models[0].name == "har"
        assert loaded.blend.models[0].feature_layers == ["har_core"]
        assert loaded.blend.models[1].name == "lightgbm"
        assert loaded.blend.models[1].params == {"num_leaves": 31}
        assert loaded.blend.fixed_weights is None
        assert loaded.blend.regime_indicator is None
