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


class TestRegisterNewTrial:
    """Tests for register_new_trial — auto-creates trial entries from completed runs."""

    @pytest.fixture
    def registry_with_trials(self, tmp_path):
        """Registry with trial-001 through trial-003."""
        trials_data = {
            "trials": [
                {
                    "id": "trial-001",
                    "date": "2026-01-15",
                    "config": "trial_001_baseline.yaml",
                    "status": "completed",
                    "horizons": {"h1": {"qlike": 0.16}},
                },
                {
                    "id": "trial-002",
                    "date": "2026-02-01",
                    "config": "trial_002_lgbm.yaml",
                    "status": "completed",
                    "horizons": {"h1": {"qlike": 0.149}},
                },
                {
                    "id": "trial-003",
                    "date": "2026-03-10",
                    "config": "trial_003_pending.yaml",
                    "status": "NOT_STARTED",
                    "horizons": {},
                },
            ]
        }
        registry_path = tmp_path / "trials.yaml"
        registry_path.write_text(yaml.dump(trials_data, default_flow_style=False))
        return registry_path

    def test_registers_new_trial(self, registry_with_trials, tmp_path):
        """No matching completed trial → creates a new entry with correct fields."""
        from datetime import date

        from volforecast.cli.experiment import register_new_trial

        metrics_path = tmp_path / "metrics.json"
        metrics_path.write_text(json.dumps({
            "lightgbm": {"1": {"qlike": 0.13}, "5": {"qlike": 0.11}, "22": {"qlike": 0.18}}
        }))

        fake_date = type("FakeDate", (), {"today": staticmethod(lambda: date(2026, 7, 7)), "isoformat": date.isoformat})

        with patch.object(experiment, "TRIALS_PATH", registry_with_trials), \
             patch.object(experiment, "date", fake_date):
            result = register_new_trial("trial_050_new_features.yaml", metrics_path)

        assert result is True

        with open(registry_with_trials) as f:
            data = yaml.safe_load(f)
        new_trial = next(
            t for t in data["trials"] if t["config"] == "trial_050_new_features.yaml"
        )
        assert new_trial["status"] == "completed"
        assert new_trial["date"] == "2026-07-07"

    def test_idempotent_no_duplicate(self, registry_with_trials, tmp_path):
        """Completed trial already exists for this config → returns False, no new entry."""
        from volforecast.cli.experiment import register_new_trial

        metrics_path = tmp_path / "metrics.json"
        metrics_path.write_text(json.dumps({"lightgbm": {"1": {"qlike": 0.15}}}))

        with patch.object(experiment, "TRIALS_PATH", registry_with_trials):
            result = register_new_trial("trial_001_baseline.yaml", metrics_path)

        assert result is False

        # Verify no extra entry was added
        with open(registry_with_trials) as f:
            data = yaml.safe_load(f)
        matching = [t for t in data["trials"] if t["config"] == "trial_001_baseline.yaml"]
        assert len(matching) == 1

    def test_assigns_next_trial_id(self, registry_with_trials, tmp_path):
        """Registry has trial-003 as max → new entry gets trial-004."""
        from volforecast.cli.experiment import register_new_trial

        metrics_path = tmp_path / "metrics.json"
        metrics_path.write_text(json.dumps({"lightgbm": {"1": {"qlike": 0.12}}}))

        with patch.object(experiment, "TRIALS_PATH", registry_with_trials):
            register_new_trial("trial_099_experiment.yaml", metrics_path)

        with open(registry_with_trials) as f:
            data = yaml.safe_load(f)
        new_trial = next(
            t for t in data["trials"] if t["config"] == "trial_099_experiment.yaml"
        )
        assert new_trial["id"] == "trial-004"

    def test_fills_horizons_from_metrics(self, registry_with_trials, tmp_path):
        """Verifies qlike values end up in horizons dict correctly."""
        from volforecast.cli.experiment import register_new_trial

        metrics_path = tmp_path / "metrics.json"
        metrics_path.write_text(json.dumps({
            "lightgbm": {
                "1": {"qlike": 0.1350, "dm_pvalue": 0.04},
                "5": {"qlike": 0.1180},
                "22": {"qlike": 0.1900},
            }
        }))

        with patch.object(experiment, "TRIALS_PATH", registry_with_trials):
            register_new_trial("trial_060_horizons.yaml", metrics_path)

        with open(registry_with_trials) as f:
            data = yaml.safe_load(f)
        new_trial = next(
            t for t in data["trials"] if t["config"] == "trial_060_horizons.yaml"
        )
        assert new_trial["horizons"]["h1"]["qlike"] == 0.135
        assert new_trial["horizons"]["h5"]["qlike"] == 0.118
        assert new_trial["horizons"]["h22"]["qlike"] == 0.19


class TestCaseInsensitiveStatus:
    """update_trial_from_metrics must match status case-insensitively."""

    def test_case_insensitive_status_in_update(self, tmp_path):
        """Trial with lowercase 'not_started' should still be updated."""
        trials_data = {
            "trials": [
                {
                    "id": "trial-010",
                    "config": "trial_010_lower.yaml",
                    "status": "not_started",
                    "baseline_config": "trial_001_baseline.yaml",
                    "horizons": {},
                },
                {
                    "id": "trial-001",
                    "date": "2026-01-15",
                    "config": "trial_001_baseline.yaml",
                    "status": "completed",
                    "horizons": {
                        "h1": {"qlike": 0.1600, "verdict": "BASELINE"},
                        "h5": {"qlike": 0.1350, "verdict": "BASELINE"},
                        "h22": {"qlike": 0.2100, "verdict": "BASELINE"},
                    },
                },
            ]
        }
        registry_path = tmp_path / "trials.yaml"
        registry_path.write_text(yaml.dump(trials_data, default_flow_style=False))

        metrics = {"lightgbm": {"1": {"qlike": 0.14}, "5": {"qlike": 0.12}, "22": {"qlike": 0.19}}}
        metrics_path = tmp_path / "metrics.json"
        metrics_path.write_text(json.dumps(metrics))

        with patch.object(experiment, "TRIALS_PATH", registry_path):
            result = experiment.update_trial_from_metrics("trial_010_lower.yaml", metrics_path)

        assert result is True

        with open(registry_path) as f:
            data = yaml.safe_load(f)
        trial_010 = next(t for t in data["trials"] if t["id"] == "trial-010")
        assert trial_010["status"] == "completed"
        assert trial_010["horizons"]["h1"]["qlike"] == 0.14
