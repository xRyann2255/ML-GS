"""Typed data models for the YAML manifest.

The manifest has two layers:
- **Contract** — what data SHOULD exist (expected_columns, value_bounds, nan_budget)
- **State** — what DOES exist (per-symbol ingestion metadata, integrity audit results)

Ingest commands update state.  ``vol audit`` validates state against contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SymbolStatus(str, Enum):
    """Lifecycle status of a symbol's data within a source."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSING = "missing"
    STALE = "stale"


# ── Per-symbol state ──────────────────────────────────────────────────────


@dataclass
class Lineage:
    """Provenance of the data that produced a parquet file."""

    code_version: str = ""
    formula_version: str = ""
    source_query: str = ""


@dataclass
class Integrity:
    """Audit results written by ``vol audit``, never by ingest commands."""

    nan_pct_max: float = 0.0
    nan_columns: dict[str, float] = field(default_factory=dict)
    date_gaps: list[dict[str, str]] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    last_validated: str = ""


@dataclass
class SymbolState:
    """Per-symbol ingestion state within a source."""

    status: SymbolStatus = SymbolStatus.MISSING
    rows: int = 0
    start_date: str = ""
    end_date: str = ""
    file_size_bytes: int = 0
    last_ingested: str = ""
    lineage: Lineage = field(default_factory=Lineage)
    integrity: Integrity = field(default_factory=Integrity)


# ── Source contract ───────────────────────────────────────────────────────


@dataclass
class SourceContract:
    """Declares what a data source SHOULD contain and tracks per-symbol state."""

    description: str = ""
    directory: str = ""
    serves_layers: list[str] = field(default_factory=list)
    file_pattern: str = "{symbol}.parquet"
    index_dtype: str = "datetime64[ns]"
    expected_columns: list[str] = field(default_factory=list)
    value_bounds: dict[str, dict[str, float]] = field(default_factory=dict)
    invariants: list[str] = field(default_factory=list)
    nan_budget_pct: float = 1.0
    formula_version: str = "v1.0"
    formula_changelog: dict[str, str] = field(default_factory=dict)
    symbols: dict[str, SymbolState] = field(default_factory=dict)
    # Named files for non-per-symbol sources (cross_asset, correlation)
    files: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Market-wide files for sources with both per-symbol and market-wide data (iv)
    market_wide_files: dict[str, list[str]] = field(default_factory=dict)


# ── Top-level manifest ────────────────────────────────────────────────────


@dataclass
class DateRange:
    """Expected date range for the data universe."""

    start: str = "2014-01-02"
    end: str = "2024-12-31"
    trading_days: int = 2767


@dataclass
class Universe:
    """Target symbol universe."""

    symbols: list[str] = field(default_factory=list)
    count: int = 0


@dataclass
class ManifestMeta:
    """Top-level metadata."""

    schema_version: int = 2
    last_full_audit: str = ""
    universe: Universe = field(default_factory=Universe)
    date_range: DateRange = field(default_factory=DateRange)


@dataclass
class ManifestData:
    """Complete manifest: metadata + sources."""

    meta: ManifestMeta = field(default_factory=ManifestMeta)
    sources: dict[str, SourceContract] = field(default_factory=dict)


# ── Audit results ─────────────────────────────────────────────────────────


class ViolationSeverity(str, Enum):
    """Severity of a contract violation."""

    CRITICAL = "critical"  # Schema mismatch, NaN > budget, negative RV
    WARNING = "warning"  # Date gaps, partial coverage, stale formula


@dataclass
class Violation:
    """A single contract violation found during audit."""

    column: str = ""
    check: str = ""  # e.g. "value_bounds", "nan_budget", "schema", "invariant"
    severity: ViolationSeverity = ViolationSeverity.WARNING
    message: str = ""
    value: float | str = ""


@dataclass
class FileAuditResult:
    """Audit result for a single parquet file (per-symbol or named file)."""

    name: str = ""  # Symbol name or filename
    exists: bool = False
    rows: int = 0
    start_date: str = ""
    end_date: str = ""
    columns: list[str] = field(default_factory=list)
    missing_columns: list[str] = field(default_factory=list)
    extra_columns: list[str] = field(default_factory=list)
    nan_pct_max: float = 0.0
    nan_columns: dict[str, float] = field(default_factory=dict)
    date_gaps: list[dict[str, str]] = field(default_factory=list)
    violations: list[Violation] = field(default_factory=list)
    file_size_bytes: int = 0


@dataclass
class SourceAuditResult:
    """Aggregated audit result for an entire source."""

    source_name: str = ""
    directory: str = ""
    serves_layers: list[str] = field(default_factory=list)
    expected_symbols: int = 0
    found_symbols: int = 0
    missing_symbols: list[str] = field(default_factory=list)
    complete_symbols: int = 0
    partial_symbols: int = 0
    stale_symbols: int = 0
    file_results: dict[str, FileAuditResult] = field(default_factory=dict)
    violations: list[Violation] = field(default_factory=list)
    has_critical: bool = False
    # Named file results (cross_asset, correlation)
    named_file_results: dict[str, FileAuditResult] = field(default_factory=dict)
