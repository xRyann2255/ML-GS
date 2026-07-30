"""Tests for generic contract-based audit validators.

TDD: these tests define the expected behavior for validate_source().
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from volforecast.utils.manifest_schema import (
    FileAuditResult,
    SourceAuditResult,
    SourceContract,
    ViolationSeverity,
)

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Create a temporary project root with data directories."""
    (tmp_path / "data" / "raw" / "ticks").mkdir(parents=True)
    (tmp_path / "data" / "raw" / "iv").mkdir(parents=True)
    (tmp_path / "data" / "raw" / "ohlcv").mkdir(parents=True)
    (tmp_path / "data" / "raw" / "micro").mkdir(parents=True)
    (tmp_path / "data" / "raw" / "cross_asset").mkdir(parents=True)
    (tmp_path / "data" / "raw" / "correlation").mkdir(parents=True)
    return tmp_path


@pytest.fixture()
def ticks_contract() -> SourceContract:
    """Ticks source contract with schema + bounds."""
    return SourceContract(
        description="Test ticks",
        directory="data/raw/ticks",
        serves_layers=["L0", "L1"],
        file_pattern="{symbol}.parquet",
        expected_columns=["rv", "bpv", "rs_positive", "rs_negative"],
        value_bounds={
            "rv": {"min": 0.0, "max": 0.25},
            "bpv": {"min": 0.0},
            "rs_positive": {"min": 0.0},
            "rs_negative": {"min": 0.0},
        },
        invariants=["rs_positive + rs_negative ~ rv (within 1%)"],
        nan_budget_pct=1.0,
    )


@pytest.fixture()
def cross_asset_contract() -> SourceContract:
    """Cross-asset source contract (named files, not per-symbol)."""
    return SourceContract(
        description="Cross-asset spillovers",
        directory="data/raw/cross_asset",
        serves_layers=["L4"],
        file_pattern="*.parquet",
        expected_columns=[],
        files={
            "rates.parquet": {
                "expected_columns": ["yield_2y", "yield_5y", "yield_10y"],
                "status": "missing",
            },
            "fx_vol.parquet": {
                "expected_columns": ["fx_vol_usdjpy", "fx_vol_eurusd"],
                "status": "missing",
            },
        },
        nan_budget_pct=5.0,
    )


def _write_parquet(path: Path, df: pd.DataFrame) -> None:
    """Write a DataFrame as parquet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


def _make_ticks_df(n_rows: int = 100, *, has_nan: bool = False) -> pd.DataFrame:
    """Create a synthetic ticks dataframe that passes all checks."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2024-01-02", periods=n_rows, freq="B")
    rv = rng.uniform(0.001, 0.05, n_rows)
    rs_pos = rv * rng.uniform(0.4, 0.6, n_rows)
    rs_neg = rv - rs_pos
    df = pd.DataFrame(
        {
            "rv": rv,
            "bpv": rv * rng.uniform(0.7, 0.95, n_rows),
            "rs_positive": rs_pos,
            "rs_negative": rs_neg,
        },
        index=dates,
    )
    if has_nan:
        # Inject 5% NaN into rv (above 1% budget)
        nan_idx = rng.choice(n_rows, size=n_rows // 20, replace=False)
        df.iloc[nan_idx, 0] = np.nan
    return df


# ── Tests: validate_source for per-symbol sources ─────────────────────────


class TestValidateSourcePerSymbol:
    """Test validate_source with per-symbol file pattern."""

    def test_happy_path_all_present(self, project_root: Path, ticks_contract: SourceContract):
        """All symbols present with valid data -> no violations."""
        from volforecast.cli.validators import validate_source

        universe = ["AAPL", "MSFT", "GOOGL"]
        for sym in universe:
            _write_parquet(
                project_root / "data" / "raw" / "ticks" / f"{sym}.parquet",
                _make_ticks_df(),
            )
        # Use reference_date near the test data end so staleness isn't triggered
        result = validate_source(
            "ticks",
            ticks_contract,
            project_root,
            universe=universe,
            reference_date=date(2024, 5, 21),
        )

        assert isinstance(result, SourceAuditResult)
        assert result.source_name == "ticks"
        assert result.found_symbols == 3
        assert result.missing_symbols == []
        assert result.has_critical is False
        assert len(result.violations) == 0

    def test_missing_symbols_detected(self, project_root: Path, ticks_contract: SourceContract):
        """Missing symbols are reported."""
        from volforecast.cli.validators import validate_source

        universe = ["AAPL", "MSFT", "GOOGL"]
        # Only write AAPL
        _write_parquet(
            project_root / "data" / "raw" / "ticks" / "AAPL.parquet",
            _make_ticks_df(),
        )
        result = validate_source("ticks", ticks_contract, project_root, universe=universe)

        assert result.found_symbols == 1
        assert sorted(result.missing_symbols) == ["GOOGL", "MSFT"]

    def test_schema_violation_missing_column(
        self, project_root: Path, ticks_contract: SourceContract
    ):
        """Missing expected column -> CRITICAL violation."""
        from volforecast.cli.validators import validate_source

        # Write parquet missing 'bpv' column
        df = _make_ticks_df().drop(columns=["bpv"])
        _write_parquet(project_root / "data" / "raw" / "ticks" / "AAPL.parquet", df)

        result = validate_source("ticks", ticks_contract, project_root, universe=["AAPL"])

        assert result.has_critical is True
        file_result = result.file_results["AAPL"]
        assert "bpv" in file_result.missing_columns
        schema_violations = [v for v in file_result.violations if v.check == "schema"]
        assert len(schema_violations) >= 1
        assert schema_violations[0].severity == ViolationSeverity.CRITICAL

    def test_nan_budget_exceeded(self, project_root: Path, ticks_contract: SourceContract):
        """NaN rate exceeding budget -> CRITICAL violation."""
        from volforecast.cli.validators import validate_source

        df = _make_ticks_df(has_nan=True)
        _write_parquet(project_root / "data" / "raw" / "ticks" / "AAPL.parquet", df)

        result = validate_source("ticks", ticks_contract, project_root, universe=["AAPL"])

        assert result.has_critical is True
        file_result = result.file_results["AAPL"]
        nan_violations = [v for v in file_result.violations if v.check == "nan_budget"]
        assert len(nan_violations) >= 1
        assert nan_violations[0].severity == ViolationSeverity.CRITICAL

    def test_value_bounds_violation(self, project_root: Path, ticks_contract: SourceContract):
        """Value outside declared bounds -> CRITICAL violation."""
        from volforecast.cli.validators import validate_source

        df = _make_ticks_df()
        # Inject negative rv
        df.iloc[0, 0] = -0.01
        _write_parquet(project_root / "data" / "raw" / "ticks" / "AAPL.parquet", df)

        result = validate_source("ticks", ticks_contract, project_root, universe=["AAPL"])

        assert result.has_critical is True
        file_result = result.file_results["AAPL"]
        bounds_violations = [v for v in file_result.violations if v.check == "value_bounds"]
        assert len(bounds_violations) >= 1
        assert bounds_violations[0].column == "rv"

    def test_value_bounds_max_exceeded(self, project_root: Path, ticks_contract: SourceContract):
        """Value exceeding max bound -> CRITICAL violation."""
        from volforecast.cli.validators import validate_source

        df = _make_ticks_df()
        df.iloc[0, 0] = 0.5  # rv > 0.25 max
        _write_parquet(project_root / "data" / "raw" / "ticks" / "AAPL.parquet", df)

        result = validate_source("ticks", ticks_contract, project_root, universe=["AAPL"])

        assert result.has_critical is True
        file_result = result.file_results["AAPL"]
        bounds_violations = [v for v in file_result.violations if v.check == "value_bounds"]
        assert any(v.column == "rv" for v in bounds_violations)

    def test_date_gaps_detected(self, project_root: Path, ticks_contract: SourceContract):
        """Gaps > 5 calendar days are flagged as WARNING."""
        from volforecast.cli.validators import validate_source

        # Create df with a 10-day gap
        dates1 = pd.bdate_range("2024-01-02", periods=20, freq="B")
        dates2 = pd.bdate_range("2024-02-15", periods=20, freq="B")
        dates = dates1.append(dates2)
        rng = np.random.default_rng(42)
        n = len(dates)
        rv = rng.uniform(0.001, 0.05, n)
        rs_pos = rv * 0.5
        rs_neg = rv * 0.5
        df = pd.DataFrame(
            {
                "rv": rv,
                "bpv": rv * 0.8,
                "rs_positive": rs_pos,
                "rs_negative": rs_neg,
            },
            index=dates,
        )
        _write_parquet(project_root / "data" / "raw" / "ticks" / "AAPL.parquet", df)

        result = validate_source("ticks", ticks_contract, project_root, universe=["AAPL"])

        file_result = result.file_results["AAPL"]
        assert len(file_result.date_gaps) >= 1
        # Date gaps are warnings, not critical
        gap_violations = [v for v in file_result.violations if v.check == "date_gap"]
        assert all(v.severity == ViolationSeverity.WARNING for v in gap_violations)

    def test_empty_directory(self, project_root: Path, ticks_contract: SourceContract):
        """Empty source directory -> all symbols missing."""
        from volforecast.cli.validators import validate_source

        universe = ["AAPL", "MSFT"]
        result = validate_source("ticks", ticks_contract, project_root, universe=universe)

        assert result.found_symbols == 0
        assert sorted(result.missing_symbols) == ["AAPL", "MSFT"]
        assert result.has_critical is False  # Missing is not a violation, just state


# ── Tests: validate_source for named-file sources ─────────────────────────


class TestValidateSourceNamedFiles:
    """Test validate_source with named files (cross_asset, correlation)."""

    def test_named_files_present(self, project_root: Path, cross_asset_contract: SourceContract):
        """Named files present with correct columns -> no violations."""
        from volforecast.cli.validators import validate_source

        dates = pd.bdate_range("2024-01-02", periods=50, freq="B")
        rng = np.random.default_rng(42)

        rates_df = pd.DataFrame(
            {
                "yield_2y": rng.uniform(3.0, 5.0, 50),
                "yield_5y": rng.uniform(3.5, 5.5, 50),
                "yield_10y": rng.uniform(4.0, 6.0, 50),
            },
            index=dates,
        )
        _write_parquet(project_root / "data" / "raw" / "cross_asset" / "rates.parquet", rates_df)

        fx_df = pd.DataFrame(
            {
                "fx_vol_usdjpy": rng.uniform(5.0, 15.0, 50),
                "fx_vol_eurusd": rng.uniform(5.0, 12.0, 50),
            },
            index=dates,
        )
        _write_parquet(project_root / "data" / "raw" / "cross_asset" / "fx_vol.parquet", fx_df)

        result = validate_source("cross_asset", cross_asset_contract, project_root, universe=[])

        assert result.has_critical is False
        assert "rates.parquet" in result.named_file_results
        assert "fx_vol.parquet" in result.named_file_results
        assert result.named_file_results["rates.parquet"].exists is True
        assert result.named_file_results["fx_vol.parquet"].exists is True

    def test_named_files_missing(self, project_root: Path, cross_asset_contract: SourceContract):
        """Missing named files are reported."""
        from volforecast.cli.validators import validate_source

        result = validate_source("cross_asset", cross_asset_contract, project_root, universe=[])

        assert result.named_file_results["rates.parquet"].exists is False
        assert result.named_file_results["fx_vol.parquet"].exists is False

    def test_named_file_schema_mismatch(
        self, project_root: Path, cross_asset_contract: SourceContract
    ):
        """Named file with wrong columns -> CRITICAL violation."""
        from volforecast.cli.validators import validate_source

        dates = pd.bdate_range("2024-01-02", periods=50, freq="B")
        # Write rates file missing yield_10y
        rates_df = pd.DataFrame(
            {
                "yield_2y": np.random.uniform(3.0, 5.0, 50),
                "yield_5y": np.random.uniform(3.5, 5.5, 50),
                # missing yield_10y
            },
            index=dates,
        )
        _write_parquet(project_root / "data" / "raw" / "cross_asset" / "rates.parquet", rates_df)

        result = validate_source("cross_asset", cross_asset_contract, project_root, universe=[])

        assert result.has_critical is True
        fr = result.named_file_results["rates.parquet"]
        assert "yield_10y" in fr.missing_columns


# ── Tests: layer readiness derivation ─────────────────────────────────────


class TestLayerReadiness:
    """Test derive_layer_readiness from multiple source audit results."""

    def test_layer_ready_when_all_sources_present(self):
        """Layer is ready when all serving sources have data."""
        from volforecast.cli.validators import derive_layer_readiness

        results = {
            "ticks": SourceAuditResult(
                source_name="ticks",
                serves_layers=["L0", "L1"],
                found_symbols=25,
                expected_symbols=34,
                missing_symbols=["ABBV"] * 9,
            ),
            "iv": SourceAuditResult(
                source_name="iv",
                serves_layers=["L2"],
                found_symbols=25,
                expected_symbols=34,
                missing_symbols=["ABBV"] * 9,
            ),
        }

        readiness = derive_layer_readiness(results)

        assert "L0" in readiness
        assert readiness["L0"]["ready_symbols"] == 25
        assert readiness["L0"]["sources"] == ["ticks"]
        assert "L2" in readiness
        assert readiness["L2"]["ready_symbols"] == 25

    def test_layer_blocked_when_source_empty(self):
        """Layer is blocked when its source has no data."""
        from volforecast.cli.validators import derive_layer_readiness

        results = {
            "microstructure": SourceAuditResult(
                source_name="microstructure",
                serves_layers=["L3"],
                found_symbols=0,
                expected_symbols=34,
                missing_symbols=["AAPL"] * 34,
            ),
        }

        readiness = derive_layer_readiness(results)

        assert readiness["L3"]["ready_symbols"] == 0
        assert readiness["L3"]["blocked"] is True
        assert "vol ingest-micro" in readiness["L3"]["action"]

    def test_named_file_source_readiness(self):
        """Named-file sources report readiness based on file presence."""
        from volforecast.cli.validators import derive_layer_readiness

        results = {
            "cross_asset": SourceAuditResult(
                source_name="cross_asset",
                serves_layers=["L4"],
                found_symbols=0,
                expected_symbols=0,
                named_file_results={
                    "rates.parquet": FileAuditResult(name="rates.parquet", exists=True, rows=2515),
                    "fx_vol.parquet": FileAuditResult(name="fx_vol.parquet", exists=False),
                },
            ),
        }

        readiness = derive_layer_readiness(results)

        assert readiness["L4"]["blocked"] is True  # Not all named files present
        assert "vol ingest-xasset" in readiness["L4"]["action"]


# ── Tests: staleness detection ────────────────────────────────────────────


class TestStalenessDetection:
    """Test that validate_source detects stale data (end_date far behind today)."""

    def test_stale_symbol_flagged(self, project_root: Path, ticks_contract: SourceContract):
        """Symbol with end_date > threshold days behind reference date -> stale."""
        from volforecast.cli.validators import validate_source

        # Data ending 30 days ago should be flagged stale
        dates = pd.bdate_range("2024-01-02", periods=50, freq="B")
        df = _make_ticks_df(n_rows=50)
        df.index = dates  # Ends around 2024-03-12
        _write_parquet(project_root / "data" / "raw" / "ticks" / "AAPL.parquet", df)

        # Use reference_date far in the future relative to data
        ref_date = date(2024, 6, 1)  # ~80 days after data ends
        result = validate_source(
            "ticks",
            ticks_contract,
            project_root,
            universe=["AAPL"],
            reference_date=ref_date,
        )

        assert result.stale_symbols > 0
        # Should have a staleness violation
        stale_violations = [v for v in result.violations if v.check == "staleness"]
        assert len(stale_violations) >= 1
        assert stale_violations[0].severity == ViolationSeverity.WARNING

    def test_fresh_symbol_not_flagged(self, project_root: Path, ticks_contract: SourceContract):
        """Symbol with end_date within threshold of reference date -> not stale."""
        from volforecast.cli.validators import validate_source

        # Data ending yesterday is fresh
        ref_date = date(2024, 3, 14)
        dates = pd.bdate_range("2024-01-02", periods=50, freq="B")  # ends ~2024-03-12
        df = _make_ticks_df(n_rows=50)
        df.index = dates
        _write_parquet(project_root / "data" / "raw" / "ticks" / "AAPL.parquet", df)

        result = validate_source(
            "ticks",
            ticks_contract,
            project_root,
            universe=["AAPL"],
            reference_date=ref_date,
        )

        assert result.stale_symbols == 0
        stale_violations = [v for v in result.violations if v.check == "staleness"]
        assert len(stale_violations) == 0

    def test_default_reference_date_is_today(
        self, project_root: Path, ticks_contract: SourceContract
    ):
        """When reference_date not provided, defaults to today."""
        from volforecast.cli.validators import validate_source

        # Data from 2020 should be stale relative to today (2026)
        dates = pd.bdate_range("2020-01-02", periods=50, freq="B")
        df = _make_ticks_df(n_rows=50)
        df.index = dates
        _write_parquet(project_root / "data" / "raw" / "ticks" / "AAPL.parquet", df)

        result = validate_source(
            "ticks",
            ticks_contract,
            project_root,
            universe=["AAPL"],
            # No reference_date -> should default to today
        )

        # Data from 2020 is definitely stale in 2026
        assert result.stale_symbols > 0

    def test_staleness_threshold_default_5_days(
        self, project_root: Path, ticks_contract: SourceContract
    ):
        """Data within 5 calendar days of reference is not stale."""
        from volforecast.cli.validators import validate_source

        # Create data ending exactly 4 calendar days before reference
        dates = pd.bdate_range("2024-01-02", periods=50, freq="B")  # ends ~2024-03-12
        df = _make_ticks_df(n_rows=50)
        df.index = dates
        end_date = dates[-1].date()  # 2024-03-12 (approx)
        _write_parquet(project_root / "data" / "raw" / "ticks" / "AAPL.parquet", df)

        from datetime import timedelta

        # 4 days after end is within threshold
        ref_date = end_date + timedelta(days=4)
        result = validate_source(
            "ticks",
            ticks_contract,
            project_root,
            universe=["AAPL"],
            reference_date=ref_date,
        )
        assert result.stale_symbols == 0

        # 6 days after end exceeds threshold
        ref_date = end_date + timedelta(days=6)
        result = validate_source(
            "ticks",
            ticks_contract,
            project_root,
            universe=["AAPL"],
            reference_date=ref_date,
        )
        assert result.stale_symbols > 0
