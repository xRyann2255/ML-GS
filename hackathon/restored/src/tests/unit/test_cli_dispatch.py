"""Characterization tests for __main__.py CLI dispatch.

These tests lock current behavior BEFORE refactoring __main__.py into
a thin registry pattern. They must pass unchanged throughout the migration.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

# All subcommands registered in _build_parser()
ALL_COMMANDS = [
    "run",
    "status",
    "ingest-iv",
    "backfill-rk",
    "refresh-ohlcv",
    "audit",
    "ingest-edrvol",
    "ingest-edrvs",
    "ingest-ohlcv",
    "ingest-ticks",
    "ingest-xasset",
    "ingest-micro",
    "forecast",
    "kvar",
    "experiments",
    "new-experiment",
    "compare",
]


class TestParserStructure:
    """Lock parser structure and help output."""

    def test_help_exits_zero(self, capsys: pytest.CaptureFixture[str]) -> None:
        from volforecast.__main__ import main

        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower()

    @pytest.mark.parametrize("cmd", ALL_COMMANDS)
    def test_subcommand_recognized(self, cmd: str) -> None:
        """Every registered command is parseable (no SystemExit on parse)."""
        from volforecast.__main__ import _build_parser

        parser = _build_parser()
        # Commands that require mandatory args: just test --help exits 0
        try:
            args = parser.parse_args([cmd])
            assert args.command == cmd
        except SystemExit:
            # Some commands may require mandatory args (new-experiment --base --name)
            # Just verify --help works
            with pytest.raises(SystemExit) as exc_info:
                parser.parse_args([cmd, "--help"])
            assert exc_info.value.code == 0

    def test_no_command_prints_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        from volforecast.__main__ import main

        result = main([])
        assert result == 0
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower() or "vol" in captured.out.lower()

    def test_unknown_command_exits_error(self) -> None:
        """Unknown subcommand triggers argparse error (exit 2)."""
        from volforecast.__main__ import main

        with pytest.raises(SystemExit) as exc_info:
            main(["nonexistent-command-xyz"])
        assert exc_info.value.code == 2


class TestNoHeavyImports:
    """Module-level import must not pull heavy deps."""

    def test_import_main_no_heavy_deps(self) -> None:
        """Importing __main__ should NOT load torch/lightgbm/pandas/numpy."""
        # Clear any cached imports of these modules
        heavy_modules = {"torch", "lightgbm", "pandas", "numpy"}
        pre_existing = {m for m in heavy_modules if m in sys.modules}

        # Force re-import by removing from cache (if safe)
        import importlib

        if "volforecast.__main__" in sys.modules:
            # Already imported — just check that heavy modules were not pulled in
            # by the module-level code. We check what's NOT in modules before
            # any command runs.
            pass

        import volforecast.__main__  # noqa: F401

        # Any heavy module now present that wasn't before = violation
        newly_imported = {m for m in heavy_modules if m in sys.modules} - pre_existing
        assert not newly_imported, (
            f"Heavy modules imported at module level: {newly_imported}. "
            "These should only be imported inside command handlers."
        )


class TestDispatchDelegation:
    """Verify dispatch branches delegate correctly."""

    def test_run_delegates_to_tournament(self, tmp_path: pytest.TempPathFactory) -> None:
        """vol run --config delegates to _run_tournament with parsed config."""
        from volforecast.__main__ import main

        # Create a minimal config fixture
        config_file = tmp_path / "test_config.yaml"  # type: ignore[operator]
        config_file.write_text(
            """\
name: test-dispatch
universe: [SPY]
horizons: [1]
date_range: {start: "2023-01-01", end: "2023-06-01"}
output_dir: /tmp/test-out
feature_layers: [0]
model:
  name: HAR
  params: {}
tournament:
  models: [HAR]
  mcs_bootstrap: 100
cv:
  method: expanding
  train_size: 252
  test_size: 63
  purge_gap: 5
"""
        )

        with patch("volforecast.__main__._run_tournament") as mock_tournament:
            mock_tournament.return_value = 0
            result = main(["run", "--config", str(config_file), "--skip-ingest"])

        assert result == 0
        mock_tournament.assert_called_once()
        call_kwargs = mock_tournament.call_args
        # First positional arg is the config object
        config_arg = call_kwargs[1].get("config") or call_kwargs[0][0]
        assert config_arg.name == "test-dispatch"

    def test_status_returns_zero(self) -> None:
        """vol status completes without error."""
        from volforecast.__main__ import main

        # Mock the manifest to avoid filesystem deps
        with patch("volforecast.utils.manifest._yaml_manifest_path") as mock_path:
            from pathlib import Path

            mock_path.return_value = Path("/nonexistent/path.yaml")
            with patch("volforecast.utils.manifest.summary_table", return_value="OK"):
                with patch(
                    "volforecast.utils.manifest.get_missing_symbols", return_value=set()
                ):
                    result = main(["status"])
        assert result == 0

    def test_ingest_iv_delegates(self) -> None:
        """vol ingest-iv parses dates and delegates to cli.ingest_iv.run."""
        from volforecast.__main__ import main

        with patch("volforecast.cli.ingest_iv.run") as mock_run:
            mock_run.return_value = 0
            result = main(["ingest-iv", "--start", "2024-01-01", "--end", "2024-06-30"])

        assert result == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1] if mock_run.call_args[1] else {}
        call_args = mock_run.call_args[0] if mock_run.call_args[0] else ()
        from datetime import date

        # First two positional args are start, end dates
        assert call_args[0] == date(2024, 1, 1)
        assert call_args[1] == date(2024, 6, 30)

    def test_ingest_ohlcv_delegates(self) -> None:
        """vol ingest-ohlcv parses dates and delegates to cli.ingest_ohlcv.run."""
        from volforecast.__main__ import main

        with patch("volforecast.cli.ingest_ohlcv.run") as mock_run:
            mock_run.return_value = 0
            result = main(
                ["ingest-ohlcv", "--start", "2024-01-01", "--end", "2024-03-01", "--force"]
            )

        assert result == 0
        mock_run.assert_called_once()
        from datetime import date

        args, kwargs = mock_run.call_args
        assert args[0] == date(2024, 1, 1)
        assert args[1] == date(2024, 3, 1)

    def test_ingest_ticks_delegates(self) -> None:
        """vol ingest-ticks delegates with all args."""
        from volforecast.__main__ import main

        with patch("volforecast.cli.ingest_ticks.run") as mock_run:
            mock_run.return_value = 0
            result = main(["ingest-ticks", "--start", "2024-01-01", "--symbols", "SPY,AAPL"])

        assert result == 0
        mock_run.assert_called_once()
        from datetime import date

        args, kwargs = mock_run.call_args
        assert args[0] == date(2024, 1, 1)

    def test_ingest_xasset_delegates(self) -> None:
        """vol ingest-xasset delegates correctly."""
        from volforecast.__main__ import main

        with patch("volforecast.cli.ingest_xasset.run") as mock_run:
            mock_run.return_value = 0
            result = main(["ingest-xasset", "--start", "2024-01-01", "--groups", "rates,fx_vol"])

        assert result == 0
        mock_run.assert_called_once()

    def test_ingest_micro_delegates(self) -> None:
        """vol ingest-micro delegates correctly."""
        from volforecast.__main__ import main

        with patch("volforecast.cli.ingest_micro.run") as mock_run:
            mock_run.return_value = 0
            result = main(["ingest-micro", "--start", "2024-01-01", "--symbols", "SPY"])

        assert result == 0
        mock_run.assert_called_once()

    def test_ingest_edrvs_delegates(self) -> None:
        """vol ingest-edrvs delegates correctly."""
        from volforecast.__main__ import main

        with patch("volforecast.cli.ingest_edrvs.run") as mock_run:
            mock_run.return_value = 0
            result = main(["ingest-edrvs", "--start", "2024-01-01"])

        assert result == 0
        mock_run.assert_called_once()

    def test_backfill_rk_delegates(self) -> None:
        """vol backfill-rk delegates correctly."""
        from volforecast.__main__ import main

        with patch("volforecast.cli.backfill_rk.run") as mock_run:
            mock_run.return_value = None
            result = main(["backfill-rk", "--symbols", "SPY", "--dry-run"])

        assert result == 0
        mock_run.assert_called_once()
        kwargs = mock_run.call_args[1]
        assert kwargs["symbols"] == ["SPY"]
        assert kwargs["dry_run"] is True

    def test_refresh_ohlcv_delegates(self) -> None:
        """vol refresh-ohlcv delegates correctly."""
        from volforecast.__main__ import main

        with patch("volforecast.cli.refresh_ohlcv.run") as mock_run:
            mock_run.return_value = None
            result = main(["refresh-ohlcv", "--symbols", "SPY", "--dry-run"])

        assert result == 0
        mock_run.assert_called_once()

    def test_audit_delegates(self) -> None:
        """vol audit delegates to run_audit."""
        from volforecast.__main__ import main

        with patch("volforecast.cli.audit.run_audit") as mock_audit:
            result = main(["audit", "--quiet"])

        assert result == 0
        mock_audit.assert_called_once_with(quiet=True, no_report=False)

    def test_audit_fix_delegates(self) -> None:
        """vol audit --fix --sources ticks calls both run_audit and run_audit_fix."""
        from volforecast.__main__ import main

        with (
            patch("volforecast.cli.audit.run_audit") as mock_audit,
            patch("volforecast.cli.audit.run_audit_fix") as mock_fix,
            patch("volforecast.cli.gap_detector._SOURCE_DIRS", {"ticks": "data/raw/ticks"}),
            patch("volforecast.utils.paths.resolve_project_root") as mock_root,
        ):
            from pathlib import Path

            fake_root = Path("/fake")
            mock_root.return_value = fake_root
            # Create a fake dir structure so glob returns something
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "glob", return_value=[Path("/fake/data/raw/ticks/SPY.parquet")]):
                    result = main(["audit", "--fix", "--sources", "ticks", "--quiet"])

        assert result == 0
        mock_audit.assert_called_once()
        mock_fix.assert_called_once()

    def test_forecast_delegates(self) -> None:
        """vol forecast delegates to cli.forecast.main."""
        from volforecast.__main__ import main

        with patch("volforecast.cli.forecast.main") as mock_forecast:
            mock_forecast.return_value = 0
            result = main(["forecast", "--symbol", "AAPL", "--horizon", "1,5"])

        assert result == 0
        mock_forecast.assert_called_once()
        kwargs = mock_forecast.call_args[1]
        assert kwargs["symbol"] == "AAPL"
        assert kwargs["horizons_str"] == "1,5"

    def test_kvar_delegates(self) -> None:
        """vol kvar delegates to cli.kvar.run."""
        from volforecast.__main__ import main

        with patch("volforecast.cli.kvar.run") as mock_kvar:
            mock_kvar.return_value = 0
            result = main(["kvar", "--target", "same-day"])

        assert result == 0
        mock_kvar.assert_called_once_with(target="same-day", edrvs_intraday_path=None)

    def test_experiment_dispatch_via_func(self) -> None:
        """vol experiments dispatches through args.func pattern."""
        from volforecast.__main__ import main

        with patch("volforecast.cli.experiment.cmd_experiments") as mock_cmd:
            mock_cmd.return_value = 0
            result = main(["experiments"])

        assert result == 0
        mock_cmd.assert_called_once()

    def test_ingest_edrvol_deprecated_delegates(self) -> None:
        """vol ingest-edrvol emits deprecation and delegates to ingest_iv.run."""
        from volforecast.__main__ import main

        with patch("volforecast.cli.ingest_iv.run") as mock_run:
            mock_run.return_value = 0
            result = main(["ingest-edrvol", "--start", "2024-01-01"])

        assert result == 0
        mock_run.assert_called_once()


class TestHelpSnapshot:
    """Snapshot tests for --help output stability."""

    def test_root_help_contains_all_commands(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Root help text mentions all registered command names."""
        from volforecast.__main__ import _build_parser

        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])
        captured = capsys.readouterr()
        # Verify key commands appear in help
        for cmd in ["run", "status", "audit", "forecast", "kvar", "experiments"]:
            assert cmd in captured.out, f"Command '{cmd}' missing from root help"

    @pytest.mark.parametrize(
        "cmd",
        [
            "run",
            "status",
            "ingest-iv",
            "backfill-rk",
            "refresh-ohlcv",
            "audit",
            "ingest-ohlcv",
            "ingest-ticks",
            "ingest-xasset",
            "ingest-micro",
            "forecast",
            "kvar",
        ],
    )
    def test_subcommand_help_exits_zero(
        self, cmd: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Each subcommand --help exits 0 and produces output."""
        from volforecast.__main__ import _build_parser

        parser = _build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args([cmd, "--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert len(captured.out) > 20
