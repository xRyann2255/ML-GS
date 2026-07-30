"""Tests for --fix / --confirm CLI integration in vol audit.

TDD: these tests define expected behavior for the fix flow integration.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd


class TestAuditFixCLI:
    """Integration tests for the fix flag in run_audit."""

    def test_fix_without_confirm_no_side_effects(self, tmp_path: Path) -> None:
        """--fix alone detects gaps but does NOT fetch anything."""
        from volforecast.cli.audit import run_audit_fix

        # Create a minimal ohlcv cache with a gap
        from volforecast.data.trading_calendar import get_trading_days

        data_dir = tmp_path / "data" / "raw" / "ohlcv"
        data_dir.mkdir(parents=True)

        start, end = date(2024, 1, 2), date(2024, 1, 31)
        all_days = get_trading_days(start, end)
        # Remove 3 days to create gaps
        cached_days = [d for d in all_days if d not in {all_days[5], all_days[10], all_days[15]}]

        idx = pd.DatetimeIndex([pd.Timestamp(d) for d in cached_days], name="date")
        df = pd.DataFrame(
            np.ones((len(cached_days), 5)),
            index=idx,
            columns=["open", "high", "low", "close", "volume"],
        )
        df.to_parquet(data_dir / "AAPL.parquet")

        # run_audit_fix with confirm=False should NOT call any fetch
        with patch("volforecast.cli.gap_fixer.fix_gaps") as mock_fix:
            report = run_audit_fix(
                sources={"ohlcv": ["AAPL"]},
                start_date=start,
                end_date=end,
                confirm=False,
                project_root=tmp_path,
            )
            mock_fix.assert_not_called()

        # But it should report the gaps
        assert report.total_missing_days > 0
        assert report.sources_scanned == 1

    def test_fix_with_confirm_calls_fixer(self, tmp_path: Path) -> None:
        """--fix --confirm detects gaps AND calls fix_gaps."""
        from volforecast.cli.audit import run_audit_fix
        from volforecast.cli.gap_fixer import FixResult
        from volforecast.data.trading_calendar import get_trading_days

        data_dir = tmp_path / "data" / "raw" / "ohlcv"
        data_dir.mkdir(parents=True)

        start, end = date(2024, 1, 2), date(2024, 1, 31)
        all_days = get_trading_days(start, end)
        removed = {all_days[5], all_days[10]}
        cached_days = [d for d in all_days if d not in removed]

        idx = pd.DatetimeIndex([pd.Timestamp(d) for d in cached_days], name="date")
        df = pd.DataFrame(
            np.ones((len(cached_days), 5)),
            index=idx,
            columns=["open", "high", "low", "close", "volume"],
        )
        df.to_parquet(data_dir / "AAPL.parquet")

        mock_result = FixResult(
            source="ohlcv",
            symbol="AAPL",
            days_planned=2,
            days_filled=2,
            days_failed=0,
            errors=[],
            dry_run=False,
        )

        with patch("volforecast.cli.gap_fixer.fix_gaps", return_value=mock_result) as mock_fix:
            report = run_audit_fix(
                sources={"ohlcv": ["AAPL"]},
                start_date=start,
                end_date=end,
                confirm=True,
                project_root=tmp_path,
            )
            mock_fix.assert_called_once()
            call_args = mock_fix.call_args
            assert call_args.kwargs.get("dry_run") is False or (
                not call_args[1].get("dry_run", True)
                if call_args[1]
                else call_args[0][2] == sorted(removed)
            )

        assert report.total_fixed_days == 2

    def test_confirm_without_fix_is_noop(self) -> None:
        """--confirm without --fix should be rejected or ignored."""
        # This is enforced at the CLI layer (__main__.py), not in run_audit_fix
        # The test validates that run_audit_fix requires explicit sources
        from volforecast.cli.audit import run_audit_fix

        # Empty sources = nothing to do
        report = run_audit_fix(
            sources={},
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 31),
            confirm=True,
            project_root=Path("/nonexistent"),
        )
        assert report.total_missing_days == 0
        assert report.total_fixed_days == 0
