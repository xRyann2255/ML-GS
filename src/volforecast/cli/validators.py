"""Generic manifest-driven data validators.

Validates parquet files on disk against their source contracts declared
in data/manifest.yaml.  Used by ``vol audit`` to produce multi-source
readiness reports.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from volforecast.utils.manifest_schema import (
    FileAuditResult,
    SourceAuditResult,
    SourceContract,
    Violation,
    ViolationSeverity,
)

# Map source names to their ingest CLI commands
_SOURCE_COMMANDS: dict[str, str] = {
    "ticks": "vol ingest-ticks",
    "iv": "vol ingest-iv",
    "ohlcv": "vol ingest-ohlcv",
    "microstructure": "vol ingest-micro",
    "cross_asset": "vol ingest-xasset",
    "correlation": "vol ingest-corr",
}

# Gap threshold in calendar days
_DATE_GAP_THRESHOLD = 5

# Staleness threshold in calendar days — data ending more than this many
# days before the reference date is flagged as stale.
_STALENESS_THRESHOLD_DAYS = 5


def _is_per_symbol(contract: SourceContract) -> bool:
    """Determine if a source uses per-symbol files (vs named files)."""
    return "{symbol}" in contract.file_pattern


def _validate_parquet(
    path: Path,
    name: str,
    expected_columns: list[str],
    value_bounds: dict[str, dict[str, float]],
    nan_budget_pct: float,
) -> FileAuditResult:
    """Validate a single parquet file against contract expectations."""
    if not path.exists():
        return FileAuditResult(name=name, exists=False)

    df = pd.read_parquet(path)
    actual_cols = list(df.columns)

    # Schema checks
    missing_cols = sorted(set(expected_columns) - set(actual_cols))
    extra_cols = sorted(set(actual_cols) - set(expected_columns))

    violations: list[Violation] = []

    if missing_cols:
        violations.append(
            Violation(
                check="schema",
                severity=ViolationSeverity.CRITICAL,
                message=f"Missing columns: {missing_cols}",
                column=", ".join(missing_cols),
            )
        )

    # Date range
    dates = pd.to_datetime(df.index) if df.index.dtype == "object" else df.index
    dates_sorted = dates.sort_values()
    start_date = str(dates_sorted.min())[:10] if len(dates_sorted) > 0 else ""
    end_date = str(dates_sorted.max())[:10] if len(dates_sorted) > 0 else ""

    # Date gaps
    date_gaps: list[dict[str, str]] = []
    if len(dates_sorted) > 1:
        diffs = dates_sorted[1:] - dates_sorted[:-1]
        for i, d in enumerate(diffs):
            if d.days > _DATE_GAP_THRESHOLD:
                gap = {
                    "from": str(dates_sorted[i])[:10],
                    "to": str(dates_sorted[i + 1])[:10],
                    "calendar_days": str(int(d.days)),
                }
                date_gaps.append(gap)
                violations.append(
                    Violation(
                        check="date_gap",
                        severity=ViolationSeverity.WARNING,
                        message=f"Gap of {d.days} days: {gap['from']} to {gap['to']}",
                    )
                )

    # NaN budget
    nan_columns: dict[str, float] = {}
    nan_pct_max = 0.0
    for col in df.columns:
        nan_pct = float(df[col].isna().mean()) * 100
        if nan_pct > 0:
            nan_columns[col] = round(nan_pct, 2)
        nan_pct_max = max(nan_pct_max, nan_pct)
        if nan_pct > nan_budget_pct:
            violations.append(
                Violation(
                    check="nan_budget",
                    severity=ViolationSeverity.CRITICAL,
                    column=col,
                    message=f"NaN {nan_pct:.1f}% exceeds budget {nan_budget_pct}%",
                    value=round(nan_pct, 2),
                )
            )

    # Value bounds
    for col, bounds in value_bounds.items():
        if col not in df.columns:
            continue
        series = df[col].dropna()
        if len(series) == 0:
            continue
        col_min = float(series.min())
        col_max = float(series.max())
        if "min" in bounds and col_min < bounds["min"]:
            violations.append(
                Violation(
                    check="value_bounds",
                    severity=ViolationSeverity.CRITICAL,
                    column=col,
                    message=f"Min value {col_min:.6f} below bound {bounds['min']}",
                    value=col_min,
                )
            )
        if "max" in bounds and col_max > bounds["max"]:
            violations.append(
                Violation(
                    check="value_bounds",
                    severity=ViolationSeverity.CRITICAL,
                    column=col,
                    message=f"Max value {col_max:.6f} exceeds bound {bounds['max']}",
                    value=col_max,
                )
            )

    return FileAuditResult(
        name=name,
        exists=True,
        rows=len(df),
        start_date=start_date,
        end_date=end_date,
        columns=actual_cols,
        missing_columns=missing_cols,
        extra_columns=extra_cols,
        nan_pct_max=round(nan_pct_max, 2),
        nan_columns=nan_columns,
        date_gaps=date_gaps,
        violations=violations,
        file_size_bytes=int(path.stat().st_size),
    )


def validate_source(
    source_name: str,
    contract: SourceContract,
    root: Path,
    *,
    universe: list[str] | None = None,
    reference_date: date | None = None,
) -> SourceAuditResult:
    """Validate all files for a source against its manifest contract.

    Parameters
    ----------
    source_name : str
        Name of the source (e.g. "ticks", "iv", "cross_asset").
    contract : SourceContract
        The contract declaring expected schema/bounds/etc.
    root : Path
        Project root directory.
    universe : list[str] or None
        Symbol universe for per-symbol sources. If None, no per-symbol
        validation is performed (only named files).
    reference_date : date or None
        Date to check staleness against. Defaults to today.

    Returns
    -------
    SourceAuditResult
        Aggregated audit findings for the source.
    """
    if reference_date is None:
        reference_date = date.today()
    source_dir = root / contract.directory
    file_results: dict[str, FileAuditResult] = {}
    named_file_results: dict[str, FileAuditResult] = {}
    all_violations: list[Violation] = []
    found_symbols = 0
    missing_symbols: list[str] = []

    if _is_per_symbol(contract) and universe:
        # Per-symbol validation
        for sym in universe:
            filename = contract.file_pattern.replace("{symbol}", sym)
            path = source_dir / filename
            if not path.exists():
                missing_symbols.append(sym)
                continue
            found_symbols += 1
            result = _validate_parquet(
                path,
                sym,
                contract.expected_columns,
                contract.value_bounds,
                contract.nan_budget_pct,
            )
            file_results[sym] = result
            all_violations.extend(result.violations)
    elif not _is_per_symbol(contract) or contract.files:
        # Named-file validation (cross_asset, correlation)
        for filename, file_spec in contract.files.items():
            path = source_dir / filename
            expected_cols = file_spec.get("expected_columns", [])
            result = _validate_parquet(
                path,
                filename,
                expected_cols,
                contract.value_bounds,
                contract.nan_budget_pct,
            )
            named_file_results[filename] = result
            all_violations.extend(result.violations)

    # Also check market_wide_files if present (e.g., iv source)
    for mw_file, mw_cols in contract.market_wide_files.items():
        path = source_dir / mw_file
        result = _validate_parquet(
            path,
            mw_file,
            mw_cols,
            contract.value_bounds,
            contract.nan_budget_pct,
        )
        named_file_results[mw_file] = result
        all_violations.extend(result.violations)

    # Staleness check: flag files whose end_date is too far behind reference_date
    stale_count = 0
    all_file_results = {**file_results, **named_file_results}
    for name, fr in all_file_results.items():
        if not fr.exists or not fr.end_date:
            continue
        try:
            end_dt = date.fromisoformat(fr.end_date)
        except (ValueError, TypeError):
            continue
        days_behind = (reference_date - end_dt).days
        if days_behind > _STALENESS_THRESHOLD_DAYS:
            stale_count += 1
            all_violations.append(
                Violation(
                    check="staleness",
                    severity=ViolationSeverity.WARNING,
                    message=(
                        f"{name} ends {fr.end_date}, "
                        f"{days_behind} days behind {reference_date.isoformat()}"
                    ),
                )
            )

    has_critical = any(v.severity == ViolationSeverity.CRITICAL for v in all_violations)

    # Count statuses
    complete = sum(
        1 for r in file_results.values() if r.exists and not r.missing_columns and not r.violations
    )
    partial = sum(
        1 for r in file_results.values() if r.exists and (r.missing_columns or r.violations)
    )

    return SourceAuditResult(
        source_name=source_name,
        directory=contract.directory,
        serves_layers=contract.serves_layers,
        expected_symbols=len(universe) if universe else 0,
        found_symbols=found_symbols,
        missing_symbols=missing_symbols,
        complete_symbols=complete,
        partial_symbols=partial,
        stale_symbols=stale_count,
        file_results=file_results,
        violations=all_violations,
        has_critical=has_critical,
        named_file_results=named_file_results,
    )


def derive_layer_readiness(
    results: dict[str, SourceAuditResult],
) -> dict[str, dict[str, Any]]:
    """Derive per-layer readiness from source audit results.

    Returns a dict keyed by layer name (e.g. "L0", "L3") with:
    - ready_symbols: int — how many symbols can use this layer
    - sources: list[str] — which sources feed this layer
    - blocked: bool — whether the layer is completely unusable
    - action: str — recommended command to unblock (empty if not blocked)
    """
    # Collect all layers and their serving sources
    layer_sources: dict[str, list[str]] = {}
    for source_name, result in results.items():
        for layer in result.serves_layers:
            layer_sources.setdefault(layer, []).append(source_name)

    readiness: dict[str, dict[str, Any]] = {}

    for layer, sources in sorted(layer_sources.items()):
        # For per-symbol sources: ready_symbols = min across all serving sources
        # (a symbol is ready only if ALL sources serving a layer have data for it)
        per_symbol_counts = []
        has_named_files = False
        all_named_present = True

        for src_name in sources:
            src_result = results[src_name]
            if src_result.expected_symbols > 0:
                per_symbol_counts.append(src_result.found_symbols)
            if src_result.named_file_results:
                has_named_files = True
                if any(not fr.exists for fr in src_result.named_file_results.values()):
                    all_named_present = False

        ready_symbols = min(per_symbol_counts) if per_symbol_counts else 0

        # Blocked if zero symbols AND (no named files OR some named files missing)
        blocked = ready_symbols == 0 and (not has_named_files or not all_named_present)

        # Determine action
        action = ""
        if blocked:
            # Find the command for the first source that's empty
            for src_name in sources:
                cmd = _SOURCE_COMMANDS.get(src_name, f"vol ingest-{src_name}")
                action = cmd
                break

        readiness[layer] = {
            "ready_symbols": ready_symbols,
            "sources": sources,
            "blocked": blocked,
            "action": action,
        }

    return readiness
