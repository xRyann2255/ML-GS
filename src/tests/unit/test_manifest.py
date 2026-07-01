"""Tests for ManifestManager — YAML manifest with contract + state.

TDD: these tests are written BEFORE the implementation.
They define the public API contract for ManifestManager.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
import yaml

from volforecast.utils.manifest_schema import (
    Integrity,
    Lineage,
    ManifestData,
    SourceContract,
    SymbolState,
    SymbolStatus,
    Universe,
)

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_manifest(tmp_path: Path) -> Path:
    """Return path to a temporary manifest.yaml (does not exist yet)."""
    return tmp_path / "manifest.yaml"


@pytest.fixture()
def minimal_yaml(tmp_path: Path) -> Path:
    """Create a minimal valid manifest YAML and return its path."""
    data = {
        "meta": {
            "schema_version": 2,
            "last_full_audit": "",
            "universe": {"symbols": ["AAPL", "SPY"], "count": 2},
            "date_range": {
                "start": "2015-01-02",
                "end": "2024-12-31",
                "trading_days": 2515,
            },
        },
        "sources": {
            "ticks": {
                "description": "Daily RV panel",
                "directory": "data/raw/ticks",
                "serves_layers": ["L0", "L1"],
                "file_pattern": "{symbol}.parquet",
                "index_dtype": "datetime64[ns]",
                "expected_columns": ["rv", "log_rv", "rq", "bpv"],
                "value_bounds": {"rv": {"min": 0.0, "max": 0.25}},
                "invariants": [],
                "nan_budget_pct": 1.0,
                "formula_version": "v1.0",
                "formula_changelog": {"v1.0": "initial"},
                "symbols": {
                    "AAPL": {
                        "status": "complete",
                        "rows": 2515,
                        "start_date": "2015-01-02",
                        "end_date": "2024-12-31",
                        "file_size_bytes": 420000,
                        "last_ingested": "2026-05-22T10:00:00",
                        "lineage": {
                            "code_version": "git:abc1234",
                            "formula_version": "v1.0",
                            "source_query": "ChunkStore EQ",
                        },
                        "integrity": {
                            "nan_pct_max": 0.0,
                            "nan_columns": {},
                            "date_gaps": [],
                            "issues": [],
                            "last_validated": "2026-05-22T10:00:00",
                        },
                    }
                },
            }
        },
    }
    p = tmp_path / "manifest.yaml"
    with open(p, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False)
    return p


# ── Schema dataclass tests ────────────────────────────────────────────────


class TestManifestSchema:
    def test_symbol_status_values(self):
        assert SymbolStatus.COMPLETE.value == "complete"
        assert SymbolStatus.PARTIAL.value == "partial"
        assert SymbolStatus.MISSING.value == "missing"
        assert SymbolStatus.STALE.value == "stale"

    def test_symbol_state_defaults(self):
        s = SymbolState()
        assert s.status == SymbolStatus.MISSING
        assert s.rows == 0
        assert s.start_date == ""

    def test_lineage_defaults(self):
        lin = Lineage()
        assert lin.code_version == ""
        assert lin.formula_version == ""

    def test_integrity_defaults(self):
        integ = Integrity()
        assert integ.nan_pct_max == 0.0
        assert integ.date_gaps == []
        assert integ.issues == []

    def test_source_contract_defaults(self):
        sc = SourceContract()
        assert sc.nan_budget_pct == 1.0
        assert sc.formula_version == "v1.0"
        assert sc.symbols == {}

    def test_manifest_data_defaults(self):
        md = ManifestData()
        assert md.meta.schema_version == 2
        assert md.sources == {}


# ── ManifestManager tests ─────────────────────────────────────────────────


class TestManifestManagerLoad:
    def test_load_missing_file_returns_empty(self, tmp_manifest: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(tmp_manifest)
        data = mgr.load()
        assert isinstance(data, ManifestData)
        assert data.sources == {}

    def test_load_minimal_yaml(self, minimal_yaml: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(minimal_yaml)
        data = mgr.load()
        assert data.meta.schema_version == 2
        assert data.meta.universe.symbols == ["AAPL", "SPY"]
        assert "ticks" in data.sources
        src = data.sources["ticks"]
        assert src.expected_columns == ["rv", "log_rv", "rq", "bpv"]
        assert "AAPL" in src.symbols
        assert src.symbols["AAPL"].status == SymbolStatus.COMPLETE
        assert src.symbols["AAPL"].rows == 2515
        assert src.symbols["AAPL"].lineage.code_version == "git:abc1234"

    def test_load_preserves_value_bounds(self, minimal_yaml: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(minimal_yaml)
        data = mgr.load()
        assert data.sources["ticks"].value_bounds == {"rv": {"min": 0.0, "max": 0.25}}


class TestManifestManagerSave:
    def test_save_creates_file(self, tmp_manifest: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(tmp_manifest)
        data = ManifestData()
        data.meta.universe = Universe(symbols=["AAPL"], count=1)
        mgr.save(data)
        assert tmp_manifest.exists()

    def test_save_roundtrip(self, tmp_manifest: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(tmp_manifest)
        original = ManifestData()
        original.meta.universe = Universe(symbols=["AAPL", "SPY"], count=2)
        original.sources["ticks"] = SourceContract(
            description="Test",
            directory="data/raw/ticks",
            expected_columns=["rv", "bpv"],
            formula_version="v1.0",
        )
        original.sources["ticks"].symbols["AAPL"] = SymbolState(
            status=SymbolStatus.COMPLETE,
            rows=100,
            start_date="2020-01-02",
            end_date="2020-12-31",
            lineage=Lineage(code_version="git:deadbeef", formula_version="v1.0"),
        )
        mgr.save(original)

        loaded = mgr.load()
        assert loaded.meta.universe.symbols == ["AAPL", "SPY"]
        assert loaded.sources["ticks"].expected_columns == ["rv", "bpv"]
        sym = loaded.sources["ticks"].symbols["AAPL"]
        assert sym.status == SymbolStatus.COMPLETE
        assert sym.rows == 100
        assert sym.lineage.code_version == "git:deadbeef"

    def test_save_atomic_no_corrupt_on_content(self, tmp_manifest: Path):
        """Save should use atomic write (tempfile + os.replace)."""
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(tmp_manifest)
        data = ManifestData()
        data.meta.universe = Universe(symbols=["SPY"], count=1)
        mgr.save(data)

        # File should be valid YAML (not corrupted mid-write)
        with open(tmp_manifest) as f:
            raw = yaml.safe_load(f)
        assert raw["meta"]["universe"]["symbols"] == ["SPY"]

    def test_save_creates_parent_dirs(self, tmp_path: Path):
        from volforecast.utils.manifest import ManifestManager

        nested = tmp_path / "sub" / "dir" / "manifest.yaml"
        mgr = ManifestManager(nested)
        mgr.save(ManifestData())
        assert nested.exists()


class TestManifestManagerUpdateSymbol:
    def test_update_new_symbol(self, tmp_manifest: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(tmp_manifest)
        # Start with empty manifest
        data = ManifestData()
        data.sources["ticks"] = SourceContract(
            directory="data/raw/ticks",
            formula_version="v1.0",
        )
        mgr.save(data)

        state = SymbolState(
            status=SymbolStatus.COMPLETE,
            rows=2515,
            start_date="2015-01-02",
            end_date="2024-12-31",
            last_ingested=datetime.now().isoformat(timespec="seconds"),
            lineage=Lineage(
                code_version="git:abc1234",
                formula_version="v1.0",
                source_query="ChunkStore EQ",
            ),
        )
        mgr.update_symbol("ticks", "AAPL", state)

        reloaded = mgr.load()
        assert "AAPL" in reloaded.sources["ticks"].symbols
        assert reloaded.sources["ticks"].symbols["AAPL"].rows == 2515

    def test_update_existing_symbol_overwrites(self, tmp_manifest: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(tmp_manifest)
        data = ManifestData()
        data.sources["ticks"] = SourceContract(directory="data/raw/ticks")
        data.sources["ticks"].symbols["AAPL"] = SymbolState(status=SymbolStatus.COMPLETE, rows=100)
        mgr.save(data)

        new_state = SymbolState(status=SymbolStatus.COMPLETE, rows=200)
        mgr.update_symbol("ticks", "AAPL", new_state)

        reloaded = mgr.load()
        assert reloaded.sources["ticks"].symbols["AAPL"].rows == 200

    def test_update_idempotent(self, tmp_manifest: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(tmp_manifest)
        data = ManifestData()
        data.sources["ticks"] = SourceContract(directory="data/raw/ticks")
        mgr.save(data)

        state = SymbolState(status=SymbolStatus.COMPLETE, rows=2515)
        mgr.update_symbol("ticks", "AAPL", state)
        mgr.update_symbol("ticks", "AAPL", state)

        reloaded = mgr.load()
        assert reloaded.sources["ticks"].symbols["AAPL"].rows == 2515

    def test_update_unknown_source_raises(self, tmp_manifest: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(tmp_manifest)
        mgr.save(ManifestData())  # no sources defined

        with pytest.raises(KeyError):
            mgr.update_symbol("nonexistent", "AAPL", SymbolState())


class TestManifestManagerGetStatus:
    def test_complete_symbol(self, minimal_yaml: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(minimal_yaml)
        assert mgr.get_status("ticks", "AAPL") == SymbolStatus.COMPLETE

    def test_missing_symbol(self, minimal_yaml: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(minimal_yaml)
        assert mgr.get_status("ticks", "NVDA") == SymbolStatus.MISSING

    def test_missing_source_raises(self, minimal_yaml: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(minimal_yaml)
        with pytest.raises(KeyError):
            mgr.get_status("nonexistent", "AAPL")


class TestStaleDetection:
    def test_stale_when_formula_behind(self, tmp_manifest: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(tmp_manifest)
        data = ManifestData()
        data.sources["ticks"] = SourceContract(
            directory="data/raw/ticks",
            formula_version="v2.0",  # source advanced to v2.0
        )
        data.sources["ticks"].symbols["AAPL"] = SymbolState(
            status=SymbolStatus.COMPLETE,
            rows=2515,
            lineage=Lineage(formula_version="v1.0"),  # still v1.0
        )
        mgr.save(data)

        assert mgr.get_status("ticks", "AAPL") == SymbolStatus.STALE

    def test_not_stale_when_formula_matches(self, tmp_manifest: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(tmp_manifest)
        data = ManifestData()
        data.sources["ticks"] = SourceContract(
            directory="data/raw/ticks",
            formula_version="v1.0",
        )
        data.sources["ticks"].symbols["AAPL"] = SymbolState(
            status=SymbolStatus.COMPLETE,
            rows=2515,
            lineage=Lineage(formula_version="v1.0"),
        )
        mgr.save(data)

        assert mgr.get_status("ticks", "AAPL") == SymbolStatus.COMPLETE


class TestManifestManagerSummary:
    def test_summary_empty(self, tmp_manifest: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(tmp_manifest)
        mgr.save(ManifestData())
        text = mgr.summary()
        assert isinstance(text, str)

    def test_summary_shows_source_and_counts(self, minimal_yaml: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(minimal_yaml)
        text = mgr.summary()
        assert "ticks" in text
        assert "AAPL" in text

    def test_summary_filter_by_source(self, minimal_yaml: Path):
        from volforecast.utils.manifest import ManifestManager

        mgr = ManifestManager(minimal_yaml)
        text = mgr.summary(source="ticks")
        assert "ticks" in text


# ── Backward-compat wrappers ──────────────────────────────────────────────


class TestBackwardCompat:
    """Old API functions should still work as thin wrappers."""

    def test_record_ingestion_callable(self):
        from volforecast.utils.manifest import record_ingestion

        assert callable(record_ingestion)

    def test_get_ingested_symbols_callable(self):
        from volforecast.utils.manifest import get_ingested_symbols

        assert callable(get_ingested_symbols)

    def test_summary_table_callable(self):
        from volforecast.utils.manifest import summary_table

        assert callable(summary_table)

    def test_get_missing_symbols_callable(self):
        from volforecast.utils.manifest import get_missing_symbols

        assert callable(get_missing_symbols)
