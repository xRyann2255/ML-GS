"""Tests for volforecast.cli.config_picker."""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from volforecast.cli.config_picker import _relative_age, pick_config


class TestRelativeAge:
    """Tests for the _relative_age helper."""

    def test_just_now(self):
        assert _relative_age(time.time() - 30) == "just now"

    def test_minutes(self):
        assert _relative_age(time.time() - 300) == "5m ago"

    def test_hours(self):
        assert _relative_age(time.time() - 7200) == "2h ago"

    def test_days(self):
        assert _relative_age(time.time() - 172800) == "2d ago"

    def test_weeks(self):
        assert _relative_age(time.time() - 1209600) == "2w ago"


class TestPickConfig:
    """Tests for pick_config with mocked TerminalMenu."""

    @pytest.fixture()
    def configs_dir(self, tmp_path: Path) -> Path:
        """Create a temp dir with some fake YAML configs."""
        now = time.time()
        for i, name in enumerate(
            ["trial_033_locked.yaml", "trial_032_xasset.yaml", "baseline_har.yaml"]
        ):
            f = tmp_path / name
            f.write_text(f"# Config {name}\nmodel:\n  name: test_{i}\n")
            # Set mtimes so trial_033 is newest, baseline is oldest
            os.utime(f, (now - i * 86400, now - i * 86400))
        return tmp_path

    def _run_with_mock_menu(self, configs_dir: Path, menu_return: int | None, **kwargs):
        """Helper: run pick_config with a mocked TerminalMenu."""
        mock_menu = MagicMock()
        mock_menu.show.return_value = menu_return
        mock_menu_cls = MagicMock(return_value=mock_menu)

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("simple_term_menu.TerminalMenu", mock_menu_cls),
        ):
            result = pick_config(configs_dir=configs_dir, **kwargs)
        return result, mock_menu_cls

    def test_selection_returns_path(self, configs_dir: Path):
        """Selecting index 0 returns the newest config."""
        result, _ = self._run_with_mock_menu(configs_dir, menu_return=0)
        assert result is not None
        assert result.name == "trial_033_locked.yaml"

    def test_cancel_returns_none(self, configs_dir: Path):
        """Pressing Esc (show() returns None) yields None."""
        result, _ = self._run_with_mock_menu(configs_dir, menu_return=None)
        assert result is None

    def test_mtime_ordering(self, configs_dir: Path):
        """Configs are ordered by mtime descending (newest first)."""
        result, _ = self._run_with_mock_menu(configs_dir, menu_return=2)
        assert result is not None
        assert result.name == "baseline_har.yaml"

    def test_empty_dir_returns_none(self, tmp_path: Path):
        """Empty configs dir returns None gracefully."""
        with patch("sys.stdin.isatty", return_value=True):
            result = pick_config(configs_dir=tmp_path)
        assert result is None

    def test_non_tty_exits(self, configs_dir: Path):
        """Non-TTY stdin exits with code 1."""
        with patch("sys.stdin.isatty", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                pick_config(configs_dir=configs_dir)
            assert exc_info.value.code == 1

    def test_limit_respected(self, tmp_path: Path):
        """Only `limit` configs are shown even if more exist."""
        now = time.time()
        for i in range(10):
            f = tmp_path / f"config_{i:02d}.yaml"
            f.write_text(f"# Config {i}\n")
            os.utime(f, (now - i * 3600, now - i * 3600))

        _, mock_menu_cls = self._run_with_mock_menu(tmp_path, menu_return=0, limit=5)

        # Check that TerminalMenu was called with exactly 5 entries
        call_args = mock_menu_cls.call_args
        entries = call_args[0][0]
        assert len(entries) == 5


class TestHasCompletedRun:
    """Tests for _has_completed_run — checks if a config's output_dir has metrics.json."""

    def test_returns_true_when_metrics_exists(self, tmp_path: Path):
        """Config with output_dir pointing to a dir containing metrics.json → True."""
        from volforecast.cli.config_picker import _has_completed_run

        output_dir = tmp_path / "data" / "models" / "trial_042"
        output_dir.mkdir(parents=True)
        (output_dir / "metrics.json").write_text('{"lgbm": {}}')

        config_path = tmp_path / "trial_042.yaml"
        config_path.write_text(f"output_dir: data/models/trial_042\nmodel:\n  name: lgbm\n")

        assert _has_completed_run(config_path, project_root=tmp_path) is True

    def test_returns_false_when_no_metrics(self, tmp_path: Path):
        """Config with output_dir but no metrics.json file → False."""
        from volforecast.cli.config_picker import _has_completed_run

        output_dir = tmp_path / "data" / "models" / "trial_043"
        output_dir.mkdir(parents=True)

        config_path = tmp_path / "trial_043.yaml"
        config_path.write_text("output_dir: data/models/trial_043\nmodel:\n  name: lgbm\n")

        assert _has_completed_run(config_path, project_root=tmp_path) is False

    def test_fallback_output_dir(self, tmp_path: Path):
        """Config with no output_dir field → falls back to workspace/tmp/results."""
        from volforecast.cli.config_picker import _has_completed_run

        fallback_dir = tmp_path / "workspace" / "tmp" / "results"
        fallback_dir.mkdir(parents=True)
        (fallback_dir / "metrics.json").write_text("{}")

        config_path = tmp_path / "trial_044.yaml"
        config_path.write_text("model:\n  name: lgbm\nhorizons: [1, 5, 22]\n")

        assert _has_completed_run(config_path, project_root=tmp_path) is True

    def test_green_tick_in_entries(self, tmp_path: Path):
        """pick_config prepends ✓ to entries where config stem is in completed set."""
        now = time.time()
        for i, name in enumerate(["done.yaml", "pending.yaml"]):
            f = tmp_path / name
            f.write_text(f"model:\n  name: test_{i}\n")
            os.utime(f, (now - i * 3600, now - i * 3600))

        mock_menu = MagicMock()
        mock_menu.show.return_value = 0
        mock_menu_cls = MagicMock(return_value=mock_menu)

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("simple_term_menu.TerminalMenu", mock_menu_cls),
            patch(
                "volforecast.cli.config_picker._load_completed_stems",
                return_value={"done"},
            ),
        ):
            pick_config(configs_dir=tmp_path)

        call_args = mock_menu_cls.call_args
        entries = call_args[0][0]
        # The "done.yaml" entry (newest) should have a green tick
        assert any("✓" in e for e in entries)
        # The "pending.yaml" entry should NOT have a green tick
        pending_entries = [e for e in entries if "pending" in e]
        assert all("✓" not in e for e in pending_entries)
