"""Tests for cli/experiment.py.

Validates:
1. cmd_experiments lists trials correctly
2. cmd_new_experiment clones and patches configs
3. cmd_compare computes bps differences correctly
4. update_trial_from_metrics fills in NOT_STARTED trials
5. _load_trials handles missing registry gracefully
"""

from __future__ import annotations

import argparse
import json
from unittest.mock import patch

import pytest
import yaml

from volforecast.cli import experiment


@pytest.fixture
def trials_registry(tmp_path):
    """Create a temporary trials.yaml with test data."""
    trials_data = {
        "trials": [
            {
                "id": "trial-001",
                "date": "2026-01-15",
                "config": "trial_001_baseline.yaml",
                "hypothesis": "Baseline HAR model establishes QLIKE floor",
                "status": "completed",
                "horizons": {
                    "h1": {"qlike": 0.1600, "verdict": "BASELINE"},
                    "h5": {"qlike": 0.1350, "verdict": "BASELINE"},
                    "h22": {"qlike": 0.2100, "verdict": "BASELINE"},
                },
            },
            {
                "id": "trial-002",
                "date": "2026-02-01",
                "config": "trial_002_lgbm.yaml",
                "hypothesis": "LightGBM with all features beats HAR",
                "status": "completed",
                "baseline_config": "trial_001_baseline.yaml",
                "horizons": {
                    "h1": {"qlike": 0.1490, "verdict": "PASS"},
                    "h5": {"qlike": 0.1365, "verdict": "FAIL"},
                    "h22": {"qlike": 0.2079, "verdict": "PASS"},
                },
            },
            {
                "id": "trial-003",
                "config": "trial_003_pending.yaml",
                "hypothesis": "Test pending trial",
                "status": "NOT_STARTED",
                "baseline_config": "trial_001_baseline.yaml",
                "horizons": {},
            },
        ]
    }
    registry_path = tmp_path / "trials.yaml"
    registry_path.write_text(yaml.dump(trials_data, default_flow_style=False))
    return registry_path


@pytest.fixture
def base_config(tmp_path):
    """Create a baseline YAML config for cloning."""
    config = {
        "name": "baseline",
        "output_dir": "data/models/baseline",
        "universe": ["SPY", "AAPL"],
        "horizons": [1, 5, 22],
        "feature_layers": ["har_core", "asymmetry"],
        "model": {"name": "lightgbm", "params": {"n_estimators": 500, "learning_rate": 0.05}},
        "cv": {"method": "expanding_window", "n_splits": 5, "train_size": 756},
    }
    config_path = tmp_path / "baseline.yaml"
    config_path.write_text(yaml.dump(config, default_flow_style=False))
    return config_path


class TestLoadTrials:
    def test_loads_trials_from_yaml(self, trials_registry):
        with patch.object(experiment, "TRIALS_PATH", trials_registry):
            trials = experiment._load_trials()
        assert len(trials) == 3
        assert trials[0]["id"] == "trial-001"

    def test_exits_on_missing_file(self, tmp_path):
        missing = tmp_path / "nonexistent.yaml"
        with patch.object(experiment, "TRIALS_PATH", missing):
            with pytest.raises(SystemExit):
                experiment._load_trials()


class TestCmdExperiments:
    def test_lists_all_trials(self, trials_registry, capsys):
        with patch.object(experiment, "TRIALS_PATH", trials_registry):
            args = argparse.Namespace()
            ret = experiment.cmd_experiments(args)
        assert ret == 0
        out = capsys.readouterr().out
        assert "trial-001" in out
        assert "trial-002" in out
        assert "trial-003" in out
        assert "2 completed, 1 pending" in out

    def test_empty_registry(self, tmp_path, capsys):
        registry = tmp_path / "trials.yaml"
        registry.write_text(yaml.dump({"trials": []}, default_flow_style=False))
        with patch.object(experiment, "TRIALS_PATH", registry):
            ret = experiment.cmd_experiments(argparse.Namespace())
        assert ret == 0
        assert "No trials found" in capsys.readouterr().out

    def test_formats_qlike_values(self, trials_registry, capsys):
        with patch.object(experiment, "TRIALS_PATH", trials_registry):
            experiment.cmd_experiments(argparse.Namespace())
        out = capsys.readouterr().out
        assert "0.1600" in out
        assert "0.1350" in out


class TestCmdNewExperiment:
    def test_creates_config_from_baseline(self, base_config, tmp_path):
        configs_dir = tmp_path / "workspace" / "configs"
        with patch.object(experiment, "_PROJECT_ROOT", tmp_path):
            args = argparse.Namespace(
                base=str(base_config), name="trial_010_test", set=None, force=False
            )
            ret = experiment.cmd_new_experiment(args)

        assert ret == 0
        out_path = configs_dir / "trial_010_test.yaml"
        assert out_path.exists()

        with open(out_path) as f:
            result = yaml.safe_load(f)
        assert result["name"] == "trial_010_test"
        assert result["output_dir"] == "data/models/trial_010_test"
        assert result["universe"] == ["SPY", "AAPL"]

    def test_applies_set_overrides(self, base_config, tmp_path):
        with patch.object(experiment, "_PROJECT_ROOT", tmp_path):
            args = argparse.Namespace(
                base=str(base_config),
                name="trial_011_override",
                set=["cv.train_size=1260", "model.params.n_estimators=1000"],
                force=False,
            )
            ret = experiment.cmd_new_experiment(args)

        assert ret == 0
        configs_dir = tmp_path / "workspace" / "configs"
        out_path = configs_dir / "trial_011_override.yaml"
        with open(out_path) as f:
            result = yaml.safe_load(f)
        assert result["cv"]["train_size"] == 1260
        assert result["model"]["params"]["n_estimators"] == 1000

    def test_refuses_overwrite_without_force(self, base_config, tmp_path):
        configs_dir = tmp_path / "workspace" / "configs"
        configs_dir.mkdir(parents=True)
        (configs_dir / "existing.yaml").write_text("name: existing")

        with patch.object(experiment, "_PROJECT_ROOT", tmp_path):
            args = argparse.Namespace(base=str(base_config), name="existing", set=None, force=False)
            ret = experiment.cmd_new_experiment(args)
        assert ret == 1

    def test_force_overwrites(self, base_config, tmp_path):
        configs_dir = tmp_path / "workspace" / "configs"
        configs_dir.mkdir(parents=True)
        (configs_dir / "existing.yaml").write_text("name: old")

        with patch.object(experiment, "_PROJECT_ROOT", tmp_path):
            args = argparse.Namespace(base=str(base_config), name="existing", set=None, force=True)
            ret = experiment.cmd_new_experiment(args)
        assert ret == 0
        with open(configs_dir / "existing.yaml") as f:
            result = yaml.safe_load(f)
        assert result["name"] == "existing"

    def test_missing_base_config(self, tmp_path):
        with patch.object(experiment, "_PROJECT_ROOT", tmp_path):
            args = argparse.Namespace(
                base="/nonexistent/config.yaml", name="test", set=None, force=False
            )
            ret = experiment.cmd_new_experiment(args)
        assert ret == 1

    def test_set_boolean_parsing(self, base_config, tmp_path):
        with patch.object(experiment, "_PROJECT_ROOT", tmp_path):
            args = argparse.Namespace(
                base=str(base_config),
                name="trial_bool",
                set=["tuning.enabled=true"],
                force=False,
            )
            ret = experiment.cmd_new_experiment(args)
        assert ret == 0
        configs_dir = tmp_path / "workspace" / "configs"
        with open(configs_dir / "trial_bool.yaml") as f:
            result = yaml.safe_load(f)
        assert result["tuning"]["enabled"] is True

    def test_set_invalid_format(self, base_config, tmp_path):
        with patch.object(experiment, "_PROJECT_ROOT", tmp_path):
            args = argparse.Namespace(
                base=str(base_config), name="trial_bad", set=["no_equals_sign"], force=False
            )
            ret = experiment.cmd_new_experiment(args)
        assert ret == 1


class TestCmdCompare:
    def test_compares_two_trials(self, trials_registry, capsys):
        with patch.object(experiment, "TRIALS_PATH", trials_registry):
            args = argparse.Namespace(experiment="trial-002", baseline="trial-001")
            ret = experiment.cmd_compare(args)
        assert ret == 0
        out = capsys.readouterr().out
        assert "trial-002 vs trial-001" in out
        assert "h1" in out
        assert "h5" in out

    def test_missing_experiment(self, trials_registry, capsys):
        with patch.object(experiment, "TRIALS_PATH", trials_registry):
            args = argparse.Namespace(experiment="trial-999", baseline="trial-001")
            ret = experiment.cmd_compare(args)
        assert ret == 1

    def test_missing_baseline(self, trials_registry, capsys):
        with patch.object(experiment, "TRIALS_PATH", trials_registry):
            args = argparse.Namespace(experiment="trial-002", baseline="trial-999")
            ret = experiment.cmd_compare(args)
        assert ret == 1

    def test_bps_calculation(self, trials_registry, capsys):
        with patch.object(experiment, "TRIALS_PATH", trials_registry):
            args = argparse.Namespace(experiment="trial-002", baseline="trial-001")
            experiment.cmd_compare(args)
        out = capsys.readouterr().out
        # trial-002 h1 = 0.149, trial-001 h1 = 0.16
        # bps = (0.149 - 0.16) / 0.16 * 10000 = -687.5 → -687
        assert "-687" in out or "-688" in out


class TestUpdateTrialFromMetrics:
    def test_updates_not_started_trial(self, trials_registry, tmp_path):
        metrics = {
            "lightgbm": {
                "1": {"qlike": 0.1400, "dm_pvalue": 0.03},
                "5": {"qlike": 0.1200},
                "22": {"qlike": 0.1900},
            }
        }
        metrics_path = tmp_path / "metrics.json"
        metrics_path.write_text(json.dumps(metrics))

        with patch.object(experiment, "TRIALS_PATH", trials_registry):
            result = experiment.update_trial_from_metrics("trial_003_pending.yaml", metrics_path)

        assert result is True

        # Verify the registry was updated
        with open(trials_registry) as f:
            data = yaml.safe_load(f)
        trial_003 = next(t for t in data["trials"] if t["id"] == "trial-003")
        assert trial_003["status"] == "completed"
        assert trial_003["horizons"]["h1"]["qlike"] == 0.14
        assert trial_003["horizons"]["h5"]["qlike"] == 0.12
        assert trial_003["horizons"]["h22"]["qlike"] == 0.19

    def test_skips_completed_trial(self, trials_registry, tmp_path):
        metrics = {"lightgbm": {"1": {"qlike": 0.1}}}
        metrics_path = tmp_path / "metrics.json"
        metrics_path.write_text(json.dumps(metrics))

        with patch.object(experiment, "TRIALS_PATH", trials_registry):
            result = experiment.update_trial_from_metrics("trial_001_baseline.yaml", metrics_path)
        assert result is False

    def test_returns_false_for_missing_files(self, tmp_path):
        with patch.object(experiment, "TRIALS_PATH", tmp_path / "missing.yaml"):
            result = experiment.update_trial_from_metrics(
                "any.yaml", tmp_path / "missing_metrics.json"
            )
        assert result is False

    def test_computes_bps_vs_baseline(self, trials_registry, tmp_path):
        metrics = {
            "lightgbm": {
                "1": {"qlike": 0.1500},
                "5": {"qlike": 0.1300},
                "22": {"qlike": 0.2000},
            }
        }
        metrics_path = tmp_path / "metrics.json"
        metrics_path.write_text(json.dumps(metrics))

        with patch.object(experiment, "TRIALS_PATH", trials_registry):
            experiment.update_trial_from_metrics("trial_003_pending.yaml", metrics_path)

        with open(trials_registry) as f:
            data = yaml.safe_load(f)
        trial_003 = next(t for t in data["trials"] if t["id"] == "trial-003")
        # h1: (0.15 - 0.16) / 0.16 * 10000 = -625 bps
        assert trial_003["horizons"]["h1"]["vs_har_bps"] == -625
        assert trial_003["horizons"]["h1"]["verdict"] == "PASS"

    def test_includes_dm_pvalue(self, trials_registry, tmp_path):
        metrics = {"lightgbm": {"1": {"qlike": 0.14, "dm_pvalue": 0.023}}}
        metrics_path = tmp_path / "metrics.json"
        metrics_path.write_text(json.dumps(metrics))

        with patch.object(experiment, "TRIALS_PATH", trials_registry):
            experiment.update_trial_from_metrics("trial_003_pending.yaml", metrics_path)

        with open(trials_registry) as f:
            data = yaml.safe_load(f)
        trial_003 = next(t for t in data["trials"] if t["id"] == "trial-003")
        assert trial_003["horizons"]["h1"]["dm_p"] == 0.023
