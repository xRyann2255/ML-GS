"""Tests for cli/progress.py.

Validates:
1. StageState enum values
2. _format_elapsed produces human-readable strings
3. _StageInfo lifecycle (start, finish, fail)
4. ExperimentProgress context manager and stage transitions
5. StageProgress context manager for standalone commands
6. STAGE_COLORS mapping
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from volforecast.cli.progress import (
    STAGE_COLORS,
    ExperimentProgress,
    PipelineProgress,
    StageProgress,
    StageState,
    _format_elapsed,
    _StageInfo,
)


class TestStageState:
    def test_values(self):
        assert StageState.PENDING.value == "pending"
        assert StageState.RUNNING.value == "running"
        assert StageState.DONE.value == "done"
        assert StageState.ERROR.value == "error"


class TestFormatElapsed:
    def test_seconds(self):
        assert _format_elapsed(3.0) == "3s"
        assert _format_elapsed(0.5) == "0s"
        assert _format_elapsed(59.9) == "60s"

    def test_minutes(self):
        assert _format_elapsed(60.0) == "1m00s"
        assert _format_elapsed(90.0) == "1m30s"
        assert _format_elapsed(102.0) == "1m42s"
        assert _format_elapsed(3599.0) == "59m59s"

    def test_hours(self):
        assert _format_elapsed(3600.0) == "1h00m"
        assert _format_elapsed(7500.0) == "2h05m"


class TestStageInfo:
    def test_initial_state(self):
        stage = _StageInfo("INGEST", 1, 3)
        assert stage.name == "INGEST"
        assert stage.index == 1
        assert stage.total_stages == 3
        assert stage.state == StageState.PENDING
        assert stage.elapsed == 0.0
        assert stage.summary_lines == []

    def test_start(self):
        stage = _StageInfo("TRAIN", 2, 3)
        stage.start()
        assert stage.state == StageState.RUNNING
        assert stage._start_time > 0

    def test_finish(self):
        stage = _StageInfo("EVALUATE", 3, 3)
        stage.start()
        time.sleep(0.01)
        stage.finish("5 models evaluated")
        assert stage.state == StageState.DONE
        assert stage.elapsed > 0
        assert "5 models evaluated" in stage.summary_lines

    def test_finish_no_summary(self):
        stage = _StageInfo("TRAIN", 2, 3)
        stage.start()
        stage.finish()
        assert stage.state == StageState.DONE
        assert stage.summary_lines == []

    def test_fail(self):
        stage = _StageInfo("INGEST", 1, 3)
        stage.start()
        time.sleep(0.01)
        stage.fail()
        assert stage.state == StageState.ERROR
        assert stage.elapsed > 0

    def test_prefix(self):
        stage = _StageInfo("TRAIN", 2, 3)
        assert stage.prefix == "[2/3]"

    def test_color(self):
        stage = _StageInfo("INGEST", 1, 3)
        assert stage.color == "blue"
        unknown = _StageInfo("UNKNOWN", 1, 1)
        assert unknown.color == "white"


class TestStageColors:
    def test_known_stages(self):
        assert "INGEST" in STAGE_COLORS
        assert "TRAIN" in STAGE_COLORS
        assert "EVALUATE" in STAGE_COLORS
        assert "TOURNAMENT" in STAGE_COLORS

    def test_color_values_are_strings(self):
        for name, color in STAGE_COLORS.items():
            assert isinstance(color, str)


class TestExperimentProgress:
    def test_context_manager(self):
        """ExperimentProgress can be used as context manager without error."""
        with patch("volforecast.cli.progress.console"):
            pp = ExperimentProgress("test_exp", ["SPY", "AAPL"])
            with pp:
                pass  # Just enter/exit

    def test_default_stages(self):
        pp = ExperimentProgress("test_exp", ["SPY"])
        assert "INGEST" in pp._stages
        assert "TRAIN" in pp._stages
        assert "EVALUATE" in pp._stages

    def test_custom_stages(self):
        pp = ExperimentProgress("test_exp", ["SPY"], stages=["INGEST-IV", "TRAIN"])
        assert "INGEST-IV" in pp._stages
        assert "TRAIN" in pp._stages
        assert "EVALUATE" not in pp._stages

    def test_start_stage(self):
        pp = ExperimentProgress("test_exp", ["SPY"])
        pp.start_stage("INGEST")
        assert pp._stages["INGEST"].state == StageState.RUNNING

    def test_finish_stage(self):
        pp = ExperimentProgress("test_exp", ["SPY"])
        pp.start_stage("INGEST")
        time.sleep(0.01)
        pp.finish_stage("INGEST", "34 symbols loaded")
        assert pp._stages["INGEST"].state == StageState.DONE
        assert "34 symbols loaded" in pp._stages["INGEST"].summary_lines

    def test_fail_stage(self):
        pp = ExperimentProgress("test_exp", ["SPY"])
        pp.start_stage("TRAIN")
        pp.fail_stage("TRAIN")
        assert pp._stages["TRAIN"].state == StageState.ERROR

    def test_add_task_returns_key(self):
        pp = ExperimentProgress("test_exp", ["SPY"])
        pp._progress = MagicMock()
        pp._progress.add_task.return_value = 42
        key = pp.add_task("INGEST", total=10, description="symbols")
        assert key == "INGEST:symbols"

    def test_advance_task(self):
        pp = ExperimentProgress("test_exp", ["SPY"])
        pp._progress = MagicMock()
        pp._progress.add_task.return_value = 42
        key = pp.add_task("INGEST", total=10, description="symbols")
        pp.advance(key)
        pp._progress.advance.assert_called_once_with(42, 1)

    def test_advance_subtask(self):
        pp = ExperimentProgress("test_exp", ["SPY"])
        pp._progress = MagicMock()
        pp._progress.add_task.return_value = 99
        key = pp.add_subtask("INGEST", total=100, description="days")
        pp.advance(key, 5)
        pp._progress.advance.assert_called_with(99, 5)

    def test_remove_subtask(self):
        pp = ExperimentProgress("test_exp", ["SPY"])
        pp._progress = MagicMock()
        pp._progress.add_task.return_value = 99
        key = pp.add_subtask("INGEST", total=50, description="ticks")
        pp.remove_subtask(key)
        pp._progress.remove_task.assert_called_once_with(99)
        assert key not in pp._subtasks

    def test_log_appends_to_stage(self):
        pp = ExperimentProgress("test_exp", ["SPY"])
        pp._progress = MagicMock()
        pp._progress.console = MagicMock()
        pp.log("INGEST", "SPY: 2800 days")
        assert "SPY: 2800 days" in pp._stages["INGEST"].summary_lines


class TestStageProgress:
    def test_context_manager(self):
        """StageProgress can be used as context manager without error."""
        with patch("volforecast.cli.progress.console"):
            sp = StageProgress("ingest", "baseline_har", ["SPY", "AAPL"])
            with sp:
                pass

    def test_stage_name_uppercased(self):
        sp = StageProgress("ingest", "test_exp", ["SPY"])
        assert sp.stage_name == "INGEST"

    def test_color_from_mapping(self):
        sp = StageProgress("train", "test_exp", ["SPY"])
        assert sp.color == "green"

    def test_add_task(self):
        sp = StageProgress("evaluate", "test_exp", ["SPY"])
        sp._progress = MagicMock()
        sp._progress.add_task.return_value = 7
        key = sp.add_task(total=5, description="models")
        assert key == "main:models"

    def test_add_subtask(self):
        sp = StageProgress("ingest", "test_exp", ["SPY"])
        sp._progress = MagicMock()
        sp._progress.add_task.return_value = 8
        key = sp.add_subtask(total=100, description="SPY days")
        assert key == "sub:SPY days"

    def test_advance(self):
        sp = StageProgress("ingest", "test_exp", ["SPY"])
        sp._progress = MagicMock()
        sp._progress.add_task.return_value = 10
        key = sp.add_task(total=5, description="symbols")
        sp.advance(key, 2)
        sp._progress.advance.assert_called_with(10, 2)

    def test_remove_subtask(self):
        sp = StageProgress("ingest", "test_exp", ["SPY"])
        sp._progress = MagicMock()
        sp._progress.add_task.return_value = 11
        key = sp.add_subtask(total=50, description="days")
        sp.remove_subtask(key)
        sp._progress.remove_task.assert_called_once_with(11)

    def test_log(self):
        sp = StageProgress("ingest", "test_exp", ["SPY"])
        sp._progress = MagicMock()
        sp._progress.console = MagicMock()
        sp.log("SPY: 2800 days loaded")
        assert "SPY: 2800 days loaded" in sp._summary_lines

    def test_finish(self):
        sp = StageProgress("ingest", "test_exp", ["SPY"])
        sp._start_time = time.time() - 5.0
        sp._progress = MagicMock()
        sp._progress.console = MagicMock()
        # Should not raise
        sp.finish("2 symbols, 5600 days")


class TestPipelineProgressAlias:
    def test_alias_exists(self):
        assert PipelineProgress is ExperimentProgress
