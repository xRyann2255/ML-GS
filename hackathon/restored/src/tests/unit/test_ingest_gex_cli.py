"""Tests for vol ingest-gex CLI.

TDD: Tests written first — will fail with ImportError until CLI module is implemented.
Mocks all data-layer calls (no live API).
"""

from __future__ import annotations

import argparse
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_gex_row(query_date: date) -> dict:
    """Create a synthetic GEX result dict for one date."""
    return {
        "date": query_date,
        "gex_net": 1_500_000_000.0,
        "gex_call": -2_000_000_000.0,
        "gex_put": 3_500_000_000.0,
        "gex_sign": 1,
        "spot": 5400.0,
        "n_valid_contracts": 8500,
        "oi_total": 3_200_000,
        "oi_pcr": 0.85,
    }


def _make_gex_cache(dates: list[date]) -> pd.DataFrame:
    """Build a synthetic GEX cache DataFrame."""
    rows = [_make_gex_row(d) for d in dates]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Tests: register()
# ---------------------------------------------------------------------------


class TestRegister:
    """Test that register() correctly configures the argparse subcommand."""

    def test_register_adds_subparser(self):
        """register() should add 'ingest-gex' to subparsers."""
        from volforecast.cli.ingest_gex import register

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register(subparsers)

        # Parse a valid command line — should not raise
        args = parser.parse_args(["ingest-gex"])
        assert hasattr(args, "func")

    def test_register_accepts_start_end_flags(self):
        """register() should accept --start and --end date arguments."""
        from volforecast.cli.ingest_gex import register

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register(subparsers)

        args = parser.parse_args(["ingest-gex", "--start", "2024-01-02", "--end", "2024-06-30"])
        assert args.start == "2024-01-02"
        assert args.end == "2024-06-30"

    def test_register_accepts_security_id_flag(self):
        """register() should accept --security-id argument."""
        from volforecast.cli.ingest_gex import register

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register(subparsers)

        args = parser.parse_args(["ingest-gex", "--security-id", "999999"])
        assert args.security_id == "999999"

    def test_register_accepts_force_flag(self):
        """register() should accept --force boolean flag."""
        from volforecast.cli.ingest_gex import register

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register(subparsers)

        args = parser.parse_args(["ingest-gex", "--force"])
        assert args.force is True

    def test_register_defaults(self):
        """Default security_id should be '108105', force=False."""
        from volforecast.cli.ingest_gex import register

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register(subparsers)

        args = parser.parse_args(["ingest-gex"])
        assert args.security_id == "108105"
        assert args.force is False


# ---------------------------------------------------------------------------
# Tests: handle()
# ---------------------------------------------------------------------------


class TestHandle:
    """Test that handle() parses args and delegates to run()."""

    @patch("volforecast.cli.ingest_gex.run", return_value=0)
    def test_handle_calls_run_with_parsed_dates(self, mock_run):
        """handle() should convert string dates and call run()."""
        from volforecast.cli.ingest_gex import handle

        args = argparse.Namespace(
            start="2024-03-01",
            end="2024-03-31",
            security_id="108105",
            force=False,
        )
        exit_code = handle(args)

        assert exit_code == 0
        mock_run.assert_called_once_with(
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 31),
            security_id="108105",
            force=False,
        )

    @patch("volforecast.cli.ingest_gex.run", return_value=1)
    def test_handle_propagates_failure_exit_code(self, mock_run):
        """handle() should return the exit code from run()."""
        from volforecast.cli.ingest_gex import handle

        args = argparse.Namespace(
            start="2024-01-02",
            end="2024-01-31",
            security_id="108105",
            force=False,
        )
        exit_code = handle(args)

        assert exit_code == 1


# ---------------------------------------------------------------------------
# Tests: run() — success path
# ---------------------------------------------------------------------------


class TestRunSuccess:
    """Test run() happy path with mocked data layer."""

    @patch("volforecast.cli.ingest_gex.record_ingestion_yaml")
    @patch("volforecast.cli.ingest_gex.save_gex_cache")
    @patch("volforecast.cli.ingest_gex.load_gex_cache", return_value=pd.DataFrame())
    @patch("volforecast.cli.ingest_gex.get_qsp_session")
    @patch("volforecast.cli.ingest_gex.fetch_gex_daily")
    def test_run_fetches_and_saves(
        self,
        mock_fetch,
        mock_session,
        mock_load,
        mock_save,
        mock_record,
    ):
        """run() should fetch each trading day, save cache, and return 0."""
        from volforecast.cli.ingest_gex import run

        # Two business days
        mock_fetch.side_effect = [
            _make_gex_row(date(2024, 1, 2)),
            _make_gex_row(date(2024, 1, 3)),
        ]
        mock_session.return_value = MagicMock()

        exit_code = run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 3),
            security_id="108105",
            force=False,
        )

        assert exit_code == 0
        assert mock_fetch.call_count == 2
        mock_save.assert_called_once()
        mock_record.assert_called_once()

    @patch("volforecast.cli.ingest_gex.record_ingestion_yaml")
    @patch("volforecast.cli.ingest_gex.save_gex_cache")
    @patch("volforecast.cli.ingest_gex.load_gex_cache")
    @patch("volforecast.cli.ingest_gex.get_qsp_session")
    @patch("volforecast.cli.ingest_gex.fetch_gex_daily")
    def test_run_skips_cached_dates(
        self,
        mock_fetch,
        mock_session,
        mock_load,
        mock_save,
        mock_record,
    ):
        """run() should skip dates already in cache (unless --force)."""
        from volforecast.cli.ingest_gex import run

        # Cache already has Jan 2
        cached = _make_gex_cache([date(2024, 1, 2)])
        mock_load.return_value = cached
        mock_fetch.return_value = _make_gex_row(date(2024, 1, 3))
        mock_session.return_value = MagicMock()

        exit_code = run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 3),
            security_id="108105",
            force=False,
        )

        assert exit_code == 0
        # Only Jan 3 should be fetched (Jan 2 is cached)
        assert mock_fetch.call_count == 1


# ---------------------------------------------------------------------------
# Tests: run() — force flag
# ---------------------------------------------------------------------------


class TestRunForce:
    """Test that --force re-fetches all dates regardless of cache."""

    @patch("volforecast.cli.ingest_gex.record_ingestion_yaml")
    @patch("volforecast.cli.ingest_gex.save_gex_cache")
    @patch("volforecast.cli.ingest_gex.load_gex_cache")
    @patch("volforecast.cli.ingest_gex.get_qsp_session")
    @patch("volforecast.cli.ingest_gex.fetch_gex_daily")
    def test_force_refetches_cached_dates(
        self,
        mock_fetch,
        mock_session,
        mock_load,
        mock_save,
        mock_record,
    ):
        """With force=True, run() should fetch even cached dates."""
        from volforecast.cli.ingest_gex import run

        cached = _make_gex_cache([date(2024, 1, 2), date(2024, 1, 3)])
        mock_load.return_value = cached
        mock_fetch.side_effect = [
            _make_gex_row(date(2024, 1, 2)),
            _make_gex_row(date(2024, 1, 3)),
        ]
        mock_session.return_value = MagicMock()

        exit_code = run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 3),
            security_id="108105",
            force=True,
        )

        assert exit_code == 0
        # Both dates fetched despite being in cache
        assert mock_fetch.call_count == 2


# ---------------------------------------------------------------------------
# Tests: run() — failure path
# ---------------------------------------------------------------------------


class TestRunFailure:
    """Test run() behavior when fetch_gex_daily returns None (failure)."""

    @patch("volforecast.cli.ingest_gex.record_ingestion_yaml")
    @patch("volforecast.cli.ingest_gex.save_gex_cache")
    @patch("volforecast.cli.ingest_gex.load_gex_cache", return_value=pd.DataFrame())
    @patch("volforecast.cli.ingest_gex.get_qsp_session")
    @patch("volforecast.cli.ingest_gex.fetch_gex_daily")
    def test_run_returns_1_on_partial_failure(
        self,
        mock_fetch,
        mock_session,
        mock_load,
        mock_save,
        mock_record,
    ):
        """run() returns 1 when some dates fail (fetch returns None)."""
        from volforecast.cli.ingest_gex import run

        # First date succeeds, second fails
        mock_fetch.side_effect = [
            _make_gex_row(date(2024, 1, 2)),
            None,
        ]
        mock_session.return_value = MagicMock()

        exit_code = run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 3),
            security_id="108105",
            force=False,
        )

        assert exit_code == 1

    @patch("volforecast.cli.ingest_gex.record_ingestion_yaml")
    @patch("volforecast.cli.ingest_gex.save_gex_cache")
    @patch("volforecast.cli.ingest_gex.load_gex_cache", return_value=pd.DataFrame())
    @patch("volforecast.cli.ingest_gex.get_qsp_session")
    @patch("volforecast.cli.ingest_gex.fetch_gex_daily")
    def test_run_returns_1_on_total_failure(
        self,
        mock_fetch,
        mock_session,
        mock_load,
        mock_save,
        mock_record,
    ):
        """run() returns 1 when all dates fail."""
        from volforecast.cli.ingest_gex import run

        mock_fetch.return_value = None
        mock_session.return_value = MagicMock()

        exit_code = run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 3),
            security_id="108105",
            force=False,
        )

        assert exit_code == 1
        # save_gex_cache should still be called (with whatever partial data exists)
        # or not called if no data — implementation decides

    @patch("volforecast.cli.ingest_gex.record_ingestion_yaml")
    @patch("volforecast.cli.ingest_gex.save_gex_cache")
    @patch("volforecast.cli.ingest_gex.load_gex_cache", return_value=pd.DataFrame())
    @patch("volforecast.cli.ingest_gex.get_qsp_session")
    @patch("volforecast.cli.ingest_gex.fetch_gex_daily")
    def test_run_handles_exception_gracefully(
        self,
        mock_fetch,
        mock_session,
        mock_load,
        mock_save,
        mock_record,
    ):
        """run() should catch exceptions from fetch_gex_daily and continue."""
        from volforecast.cli.ingest_gex import run

        mock_fetch.side_effect = [
            RuntimeError("Network timeout"),
            _make_gex_row(date(2024, 1, 3)),
        ]
        mock_session.return_value = MagicMock()

        exit_code = run(
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 3),
            security_id="108105",
            force=False,
        )

        # Partial failure → exit 1, but second date still fetched
        assert exit_code == 1
        assert mock_fetch.call_count == 2
