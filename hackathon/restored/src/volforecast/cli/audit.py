"""Data integrity audit and manifest generation.

Audits all cached parquet files against their manifest contracts,
validates integrity, detects issues, assesses per-layer readiness,
and regenerates data/manifest.json + syncs data/manifest.yaml.

Usage:
    python -m volforecast.cli.audit [--quiet] [--no-report] [--no-journal]
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from volforecast.cli.validators import (
    SourceAuditResult,
    derive_layer_readiness,
    validate_source,
)
from volforecast.constants import SYMBOL_UNIVERSE
from volforecast.utils.manifest import ManifestManager
from volforecast.utils.manifest_schema import (
    Integrity,
    SymbolState,
    SymbolStatus,
    ViolationSeverity,
)

logger = logging.getLogger(__name__)

# Source directories to scan for on-disk symbols
_SYMBOL_SOURCE_DIRS = ("data/raw/ticks", "data/raw/iv", "data/raw/ohlcv", "data/raw/micro")

# Map source names to their ingest CLI commands
_SOURCE_COMMANDS: dict[str, str] = {
    "ticks": "vol ingest-ticks",
    "iv": "vol ingest-iv",
    "ohlcv": "vol ingest-ohlcv",
    "microstructure": "vol ingest-micro",
    "cross_asset": "vol ingest-xasset",
    "correlation": "vol ingest-corr",
}


def _find_project_root() -> Path:
    """Walk up from this file to find the project root (contains data/)."""
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "data" / "raw" / "ticks").is_dir():
            return parent
    # Fallback
    return Path("/home/developer/ml-vol-estimator")


def _discover_universe(root: Path) -> list[str]:
    """Discover the symbol universe from on-disk parquets + constants.

    Scans source directories for parquet files and merges with
    SYMBOL_UNIVERSE from constants.py.  Excludes underscore-prefixed
    files (e.g. _MARKET.parquet, _VIX.parquet).
    """
    on_disk: set[str] = set()
    for subdir in _SYMBOL_SOURCE_DIRS:
        src_dir = root / subdir
        if not src_dir.is_dir():
            continue
        for p in src_dir.glob("*.parquet"):
            stem = p.stem
            if not stem.startswith("_"):
                on_disk.add(stem)
    return sorted(on_disk | set(SYMBOL_UNIVERSE))


def _get_universe_fallback() -> list[str]:
    """Fallback universe when manifest has no symbols: use SYMBOL_UNIVERSE."""
    return sorted(SYMBOL_UNIVERSE)


def _get_universe_from_manifest(manifest_data: Any, root: Path | None = None) -> list[str]:
    """Build the audit universe dynamically.

    Uses on-disk discovery merged with SYMBOL_UNIVERSE from constants.
    The manifest's symbol list is ignored — the audit should discover
    what actually exists rather than relying on a stale manifest list.
    """
    if root is not None:
        return _discover_universe(root)
    return _get_universe_fallback()


# ══════════════════════════════════════════════════════════════════════════
#  Legacy compatibility: convert new audit results to old format
# ══════════════════════════════════════════════════════════════════════════


def _source_result_to_legacy_rv(result: SourceAuditResult) -> dict[str, Any]:
    """Convert SourceAuditResult for ticks to legacy rv manifest format."""
    rv_manifest: dict[str, Any] = {}
    schema_groups: dict[tuple, list[str]] = {}

    for sym, fr in result.file_results.items():
        if not fr.exists:
            continue
        cols_key = tuple(sorted(fr.columns))
        schema_groups.setdefault(cols_key, []).append(sym)

        issues = [v.message for v in fr.violations if v.check == "value_bounds"]
        rv_manifest[sym] = {
            "rows": fr.rows,
            "start_date": fr.start_date,
            "end_date": fr.end_date,
            "columns": fr.columns,
            "column_count": len(fr.columns),
            "missing_expected_columns": fr.missing_columns,
            "has_open_close": "open" in fr.columns and "close" in fr.columns,
            "rk_coverage_pct": 100.0 - fr.nan_columns.get("rk", 0.0),
            "noise_gap_coverage_pct": 100.0 - fr.nan_columns.get("noise_gap", 0.0),
            "date_gaps": fr.date_gaps,
            "nan_summary": {
                col: {"nan_count": 0, "nan_pct": pct} for col, pct in fr.nan_columns.items()
            },
            "issues": issues,
            "overnight_return_corrupt": False,
            "file_size_bytes": fr.file_size_bytes,
        }

    schema_info = [
        {"symbols": syms, "column_count": len(cols), "columns": list(cols)}
        for cols, syms in schema_groups.items()
    ]

    return {
        "found_symbols": sorted(rv_manifest.keys()),
        "missing_symbols": result.missing_symbols,
        "symbol_count": result.found_symbols,
        "rv": rv_manifest,
        "schema_groups": schema_info,
    }


def _legacy_layer_readiness(
    layer_readiness: dict[str, dict[str, Any]],
    source_results: dict[str, SourceAuditResult],
) -> dict[str, Any]:
    """Convert new layer readiness to the legacy format expected by report/journal."""
    readiness: dict[str, Any] = {}

    # HAR core (L0): from ticks source
    ticks_result = source_results.get("ticks")
    if ticks_result:
        ready = []
        degraded = []
        for sym, fr in ticks_result.file_results.items():
            if not fr.exists:
                continue
            has_rv = "rv" not in fr.nan_columns or fr.nan_columns["rv"] == 0
            has_open_close = "open" in fr.columns and "close" in fr.columns
            if has_rv:
                if has_open_close:
                    ready.append(sym)
                else:
                    degraded.append(sym)
        readiness["har_core"] = {
            "fully_ready": sorted(ready),
            "degraded_no_open_close": sorted(degraded),
        }
    else:
        readiness["har_core"] = {"fully_ready": [], "degraded_no_open_close": []}

    # Asymmetry (L1)
    l1_required = ["rs_positive", "rs_negative", "bpv", "jump_variation", "continuous_variation"]
    if ticks_result:
        l1_ready = []
        for sym, fr in ticks_result.file_results.items():
            if not fr.exists:
                continue
            if all(col not in fr.nan_columns or fr.nan_columns[col] == 0 for col in l1_required):
                l1_ready.append(sym)
        readiness["asymmetry"] = {"fully_ready": sorted(l1_ready)}
    else:
        readiness["asymmetry"] = {"fully_ready": []}

    # Noise-robust
    if ticks_result:
        nr_ready = []
        nr_partial = []
        nr_none = []
        for sym, fr in ticks_result.file_results.items():
            if not fr.exists:
                continue
            rk_nan_pct = fr.nan_columns.get("rk", 0.0)
            rk_cov = 100.0 - rk_nan_pct
            if rk_cov >= 50:
                nr_ready.append(sym)
            elif rk_cov > 0:
                nr_partial.append(sym)
            else:
                nr_none.append(sym)
        readiness["noise_robust"] = {
            "fully_ready_gte_50pct": sorted(nr_ready),
            "partial_lt_50pct": sorted(nr_partial),
            "no_coverage": sorted(nr_none),
        }
    else:
        readiness["noise_robust"] = {
            "fully_ready_gte_50pct": [],
            "partial_lt_50pct": [],
            "no_coverage": [],
        }

    # Options (L2): from iv source
    iv_result = source_results.get("iv")
    if iv_result and iv_result.found_symbols > 0:
        readiness["options"] = {"ready": True, "stale_cache": False, "issues": []}
    else:
        readiness["options"] = {"ready": False, "stale_cache": True, "issues": []}

    # Tree expansion: same as har_core
    hc = readiness["har_core"]
    readiness["tree_expansion"] = {
        "fully_ready": sorted(hc["fully_ready"] + hc["degraded_no_open_close"]),
    }

    return readiness


# ══════════════════════════════════════════════════════════════════════════
#  Report generation
# ══════════════════════════════════════════════════════════════════════════


def generate_report(
    source_results: dict[str, SourceAuditResult],
    layer_readiness: dict[str, dict[str, Any]],
    universe: list[str],
) -> str:
    """Generate human-readable Markdown audit report from new-style results."""
    lines = [
        "# Data Audit Report",
        "",
        f"**Generated:** {datetime.utcnow().isoformat()}Z",
        f"**Reference date:** {date.today().isoformat()}",
        "",
        "## Source Status Matrix",
        "",
        "| Source | Layers | Found | Missing | Stale | Violations | Status |",
        "|--------|--------|-------|---------|-------|------------|--------|",
    ]

    for name, result in sorted(source_results.items()):
        layers = ", ".join(result.serves_layers)
        n_violations = len(result.violations)
        status = "CRITICAL" if result.has_critical else ("OK" if n_violations == 0 else "WARN")

        if result.expected_symbols > 0:
            found_str = f"{result.found_symbols}/{result.expected_symbols}"
            missing_str = str(len(result.missing_symbols))
        else:
            # Named file source
            n_files = len(result.named_file_results)
            n_present = sum(1 for fr in result.named_file_results.values() if fr.exists)
            found_str = f"{n_present}/{n_files} files"
            missing_str = str(n_files - n_present)

        lines.append(
            f"| {name} | {layers} | {found_str} | {missing_str} "
            f"| {result.stale_symbols} | {n_violations} | {status} |"
        )

    # Layer Readiness
    lines.extend(
        [
            "",
            "## Layer Readiness",
            "",
            "| Layer | Sources | Ready | Blocked | Action |",
            "|-------|---------|-------|---------|--------|",
        ]
    )
    for layer, info in sorted(layer_readiness.items()):
        sources_str = ", ".join(info["sources"])
        ready_str = str(info["ready_symbols"]) if info["ready_symbols"] else "0"
        blocked_str = "YES" if info["blocked"] else "no"
        action_str = f"`{info['action']}`" if info["action"] else ""
        lines.append(f"| {layer} | {sources_str} | {ready_str} | {blocked_str} | {action_str} |")

    # Per-source detail
    for name, result in sorted(source_results.items()):
        lines.extend(["", f"## Source: {name}", ""])

        if result.file_results:
            lines.append("| Symbol | Rows | Start | End | NaN Max | Violations |")
            lines.append("|--------|------|-------|-----|---------|------------|")
            for sym in sorted(result.file_results.keys()):
                fr = result.file_results[sym]
                n_viol = len(fr.violations)
                viol_str = str(n_viol) if n_viol > 0 else "0"
                lines.append(
                    f"| {sym} | {fr.rows} | {fr.start_date} | {fr.end_date} "
                    f"| {fr.nan_pct_max:.1f}% | {viol_str} |"
                )

        if result.named_file_results:
            lines.append("| File | Exists | Rows | Columns | Violations |")
            lines.append("|------|--------|------|---------|------------|")
            for fname, fr in sorted(result.named_file_results.items()):
                exists_str = "YES" if fr.exists else "NO"
                cols_str = str(len(fr.columns)) if fr.exists else "-"
                n_viol = len(fr.violations) if fr.exists else 0
                lines.append(f"| {fname} | {exists_str} | {fr.rows} | {cols_str} | {n_viol} |")

        # Critical violations
        critical = [v for v in result.violations if v.severity == ViolationSeverity.CRITICAL]
        if critical:
            lines.extend(["", "**Critical violations:**", ""])
            for v in critical[:10]:
                col_str = f" [{v.column}]" if v.column else ""
                lines.append(f"- {v.check}{col_str}: {v.message}")

    # Recommended actions
    lines.extend(["", "## Recommended Actions", ""])
    actions = []
    for layer, info in sorted(layer_readiness.items()):
        if info["blocked"]:
            actions.append(f"**{layer} blocked:** Run `{info['action']}` to ingest data")
    for name, result in sorted(source_results.items()):
        if result.has_critical:
            actions.append(
                f"**{name} has critical issues:** {len(result.violations)} violations found"
            )
        if result.stale_symbols > 0:
            cmd = _SOURCE_COMMANDS.get(name, f"vol ingest-{name}")
            actions.append(
                f"**{name} is stale:** {result.stale_symbols} symbols behind current date. "
                f"Run `{cmd}` to refresh"
            )
    if not actions:
        actions.append("No critical actions needed.")
    for i, a in enumerate(actions, 1):
        lines.append(f"{i}. {a}")

    return "\n".join(lines)


def generate_journal_entry(
    source_results: dict[str, SourceAuditResult],
    layer_readiness: dict[str, dict[str, Any]],
    universe: list[str],
) -> str:
    """Generate a research journal entry summarizing data state."""
    from datetime import date

    today = date.today().isoformat()

    # Ticks summary (primary source)
    ticks = source_results.get("ticks")
    total_rows = 0
    if ticks:
        total_rows = sum(fr.rows for fr in ticks.file_results.values())

    total_sources = len(source_results)
    sources_with_data = sum(
        1
        for r in source_results.values()
        if r.found_symbols > 0 or any(fr.exists for fr in r.named_file_results.values())
    )

    lines = [
        f"## {today} -- Data Audit: {sources_with_data}/{total_sources} Sources Active",
        "",
        "**Question explored:** What is the current state of all cached data"
        " for the vol forecasting pipeline?",
        "",
        "### Source Status",
        "",
        "| Source | Found | Layers | Status |",
        "|--------|-------|--------|--------|",
    ]

    for name, result in sorted(source_results.items()):
        layers = ", ".join(result.serves_layers)
        if result.expected_symbols > 0:
            found_str = f"{result.found_symbols}/{result.expected_symbols}"
        else:
            n_present = sum(1 for fr in result.named_file_results.values() if fr.exists)
            n_total = len(result.named_file_results)
            found_str = f"{n_present}/{n_total} files"
        status = "CRITICAL" if result.has_critical else "OK"
        lines.append(f"| {name} | {found_str} | {layers} | {status} |")

    # Layer readiness summary
    lines.extend(["", "### Layer Readiness", ""])
    blocked_layers = [
        (layer, info) for layer, info in sorted(layer_readiness.items()) if info["blocked"]
    ]
    ready_layers = [
        (layer, info) for layer, info in sorted(layer_readiness.items()) if not info["blocked"]
    ]

    if ready_layers:
        lines.append(f"- **Ready:** {', '.join(lyr for lyr, _ in ready_layers)}")
    if blocked_layers:
        for layer, info in blocked_layers:
            lines.append(f"- **{layer} BLOCKED:** run `{info['action']}`")

    lines.extend(["", "### Implications", ""])
    if ticks:
        lines.append(
            f"- Pooled training with {ticks.found_symbols} symbols gives ~{total_rows:,} rows"
        )
    if blocked_layers:
        lines.append(f"- {len(blocked_layers)} feature layers blocked pending ingestion")

    lines.append("")
    return "\n".join(lines)


def update_research_journal(
    source_results: dict[str, SourceAuditResult],
    layer_readiness: dict[str, dict[str, Any]],
    universe: list[str],
    root: Path,
) -> None:
    """Append a data audit summary to the research journal."""
    journal_path = root / "workspace" / "research" / "research-journal.md"
    if not journal_path.exists():
        return

    entry = generate_journal_entry(source_results, layer_readiness, universe)

    content = journal_path.read_text()

    # Find the separator line before the first ## entry
    separator = "\n---\n"
    sep_idx = content.find(separator)
    if sep_idx == -1:
        content = content.rstrip() + "\n\n---\n\n" + entry
    else:
        header = content[: sep_idx + len(separator)]
        body = content[sep_idx + len(separator) :]
        content = header + "\n" + entry + "\n---\n\n" + body

    journal_path.write_text(content)


# ══════════════════════════════════════════════════════════════════════════
#  YAML manifest sync
# ══════════════════════════════════════════════════════════════════════════


def _sync_audit_to_yaml(
    source_results: dict[str, SourceAuditResult],
    root: Path,
    *,
    universe: list[str] | None = None,
    quiet: bool = False,
) -> None:
    """Sync audit results into data/manifest.yaml integrity entries."""
    yaml_path = root / "data" / "manifest.yaml"
    if not yaml_path.exists():
        if not quiet:
            print("  manifest.yaml not found, skipping YAML sync")
        return

    mgr = ManifestManager(yaml_path)
    data = mgr.load()
    now = datetime.utcnow().isoformat() + "Z"
    changed = False

    # Sync discovered universe back to manifest
    if universe is not None:
        if sorted(data.meta.universe.symbols) != universe:
            data.meta.universe.symbols = universe
            data.meta.universe.count = len(universe)
            changed = True

    for source_name, result in source_results.items():
        if source_name not in data.sources:
            continue
        src = data.sources[source_name]

        for sym, fr in result.file_results.items():
            if not fr.exists:
                continue
            if sym not in src.symbols:
                src.symbols[sym] = SymbolState(
                    status=SymbolStatus.COMPLETE,
                    rows=fr.rows,
                    start_date=fr.start_date,
                    end_date=fr.end_date,
                    file_size_bytes=fr.file_size_bytes,
                    last_ingested=now,
                )
                changed = True

            state = src.symbols[sym]
            state.integrity = Integrity(
                nan_pct_max=fr.nan_pct_max,
                nan_columns=fr.nan_columns,
                date_gaps=fr.date_gaps,
                issues=[v.message for v in fr.violations],
                last_validated=now,
            )
            state.rows = fr.rows
            state.start_date = fr.start_date
            state.end_date = fr.end_date
            state.file_size_bytes = fr.file_size_bytes
            changed = True

    if changed:
        data.meta.last_full_audit = now
        mgr.save(data)
        if not quiet:
            n_sources = sum(1 for r in source_results.values() if r.found_symbols > 0)
            print(f"  manifest.yaml updated: {n_sources} sources synced")


# ══════════════════════════════════════════════════════════════════════════
#  Main entry point
# ══════════════════════════════════════════════════════════════════════════


def run_audit(
    *, quiet: bool = False, no_report: bool = False, no_journal: bool = False
) -> dict[str, Any]:
    """Run the full data audit and update manifest.

    Returns the manifest dict (legacy format for backward compatibility).
    """
    root = _find_project_root()
    yaml_path = root / "data" / "manifest.yaml"
    manifest_path = root / "data" / "manifest.json"
    report_path = root / "workspace" / "tmp" / "data_audit_report.md"

    if not quiet:
        print("Running data audit...")

    # Load manifest contract
    mgr = ManifestManager(yaml_path)
    manifest_data = mgr.load()
    universe = _get_universe_from_manifest(manifest_data, root=root)

    # Validate each source against its contract
    source_results: dict[str, SourceAuditResult] = {}
    for source_name, contract in manifest_data.sources.items():
        if not quiet:
            print(f"  Auditing {source_name}...")
        source_universe = universe if "{symbol}" in contract.file_pattern else []
        result = validate_source(source_name, contract, root, universe=source_universe)
        source_results[source_name] = result

    # Derive layer readiness
    layer_readiness = derive_layer_readiness(source_results)

    # Legacy layer readiness (for backward compat in journal/reporting)
    legacy_lr = _legacy_layer_readiness(layer_readiness, source_results)

    # Build legacy manifest dict (for JSON output)
    ticks_result = source_results.get("ticks")
    rv_legacy = (
        _source_result_to_legacy_rv(ticks_result)
        if ticks_result
        else {
            "found_symbols": [],
            "missing_symbols": universe,
            "symbol_count": 0,
            "rv": {},
            "schema_groups": [],
        }
    )

    manifest: dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "universe": {
            "expected_symbols": len(universe),
            "cached_symbols": rv_legacy["symbol_count"],
            "missing_symbols": rv_legacy["missing_symbols"],
            "found_symbols": rv_legacy["found_symbols"],
        },
        "rv": rv_legacy["rv"],
        "schema_groups": rv_legacy["schema_groups"],
        "iv_surface": {"exists": False},
        "iv_features": {"exists": False, "stale": True},
        "layer_readiness": legacy_lr,
        # New fields
        "source_results_summary": {
            name: {
                "found": r.found_symbols,
                "missing": len(r.missing_symbols),
                "violations": len(r.violations),
                "has_critical": r.has_critical,
                "layers": r.serves_layers,
            }
            for name, r in source_results.items()
        },
        "layer_readiness_v2": layer_readiness,
    }

    # Write legacy JSON manifest
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    # Sync audit results into YAML manifest
    _sync_audit_to_yaml(source_results, root, universe=universe, quiet=quiet)

    if not quiet:
        print(f"\nManifest written: {manifest_path}")
        print(f"\n{'=' * 60}")
        print("SOURCE STATUS")
        print(f"{'=' * 60}")
        for name, result in sorted(source_results.items()):
            layers = ", ".join(result.serves_layers)
            status = "CRITICAL" if result.has_critical else "OK"
            stale_str = f"  ({result.stale_symbols} stale)" if result.stale_symbols else ""
            if result.expected_symbols > 0:
                print(
                    f"  {name:<16} [{layers}] "
                    f"{result.found_symbols}/{result.expected_symbols} symbols  {status}{stale_str}"
                )
            else:
                n_present = sum(1 for fr in result.named_file_results.values() if fr.exists)
                n_total = len(result.named_file_results)
                print(f"  {name:<16} [{layers}] {n_present}/{n_total} files  {status}{stale_str}")

        print(f"\n{'=' * 60}")
        print("LAYER READINESS")
        print(f"{'=' * 60}")
        for layer, info in sorted(layer_readiness.items()):
            blocked = " BLOCKED" if info["blocked"] else ""
            action = f" -> {info['action']}" if info["action"] else ""
            print(f"  {layer:<6} {info['ready_symbols']:>3} symbols ready{blocked}{action}")

    # Write report
    if not no_report:
        report = generate_report(source_results, layer_readiness, universe)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w") as f:
            f.write(report)
        if not quiet:
            print(f"\nReport written: {report_path}")

    # Update research journal
    if not no_journal:
        update_research_journal(source_results, layer_readiness, universe, root)
        if not quiet:
            print("Research journal updated with data audit summary.")

    return manifest


# ══════════════════════════════════════════════════════════════════════════
#  Gap-fill orchestrator (--fix mode)
# ══════════════════════════════════════════════════════════════════════════


@dataclass
class FixReport:
    """Summary of a gap-fix operation across sources."""

    total_missing_days: int = 0
    total_fixed_days: int = 0
    total_failed_days: int = 0
    sources_scanned: int = 0
    results: list[Any] = field(default_factory=list)


def run_audit_fix(
    *,
    sources: dict[str, list[str]],
    start_date: date,
    end_date: date,
    confirm: bool = False,
    project_root: Path | None = None,
    quiet: bool = False,
) -> FixReport:
    """Detect and optionally fill interior gaps across sources.

    Parameters
    ----------
    sources : dict[str, list[str]]
        Map of source → list of symbols (or group names for cross_asset).
    start_date : date
        Start of expected date range.
    end_date : date
        End of expected date range.
    confirm : bool
        If True, actually fetch missing data. If False, only report.
    project_root : Path, optional
        Project root directory.
    quiet : bool
        Suppress progress output.

    Returns
    -------
    FixReport
        Summary of detection and (optionally) fixing results.
    """
    from volforecast.cli.gap_detector import detect_gaps
    from volforecast.cli.gap_fixer import fix_gaps

    if project_root is None:
        project_root = _find_project_root()

    report = FixReport()

    if not sources:
        return report

    for source, symbols in sources.items():
        report.sources_scanned += 1
        for symbol in symbols:
            missing = detect_gaps(source, symbol, start_date, end_date, project_root=project_root)
            report.total_missing_days += len(missing)

            if not missing:
                continue

            if not quiet:
                from volforecast.cli.gap_detector import coalesce_dates

                ranges = coalesce_dates(missing)
                range_strs = [f"{s} to {e}" for s, e in ranges]
                print(
                    f"  {source}/{symbol}: {len(missing)} missing days "
                    f"({len(ranges)} ranges: {', '.join(range_strs[:3])}"
                    f"{'...' if len(ranges) > 3 else ''})"
                )

            if confirm:
                result = fix_gaps(
                    source,
                    symbol,
                    missing,
                    dry_run=False,
                    project_root=project_root,
                )
                report.total_fixed_days += result.days_filled
                report.total_failed_days += result.days_failed
                report.results.append(result)

                if not quiet:
                    status = "OK" if not result.errors else f"ERRORS: {len(result.errors)}"
                    print(
                        f"    -> filled {result.days_filled}/{result.days_planned} days [{status}]"
                    )

    if not quiet:
        if confirm:
            print(
                f"\nFix complete: {report.total_fixed_days} days filled, "
                f"{report.total_failed_days} failed"
            )
        else:
            print(
                f"\n{report.total_missing_days} total missing days detected. "
                f"Run with --confirm to fill gaps."
            )

    return report


def main() -> int:
    """CLI entry point."""
    quiet = "--quiet" in sys.argv or "-q" in sys.argv
    no_report = "--no-report" in sys.argv
    no_journal = "--no-journal" in sys.argv

    try:
        manifest = run_audit(quiet=quiet, no_report=no_report, no_journal=no_journal)
        # Exit with non-zero if there are critical issues
        has_critical = any(
            r.get("has_critical", False)
            for r in manifest.get("source_results_summary", {}).values()
        )
        if has_critical:
            if not quiet:
                print("\nWARNING: Critical issues detected (see report for details)")
            return 1
        return 0
    except Exception as e:
        logger.exception("Audit failed")
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


def register(subparsers) -> None:
    """Register the audit subcommand."""
    parser = subparsers.add_parser(
        "audit",
        help="Run comprehensive data integrity audit and update manifest",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output")
    parser.add_argument(
        "--no-report", action="store_true", help="Skip Markdown report generation"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Detect interior gaps using NYSE calendar and report missing days",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually fetch and fill detected gaps (requires --fix)",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated symbols to limit gap detection (default: all cached)",
    )
    parser.add_argument(
        "--sources",
        type=str,
        default=None,
        help="Comma-separated sources to scan (default: all). "
        "Valid: ticks,iv,ohlcv,microstructure,cross_asset",
    )
    parser.set_defaults(func=handle)


def handle(args) -> int:
    """Execute audit command. Return exit code."""
    from datetime import date as _date
    from pathlib import Path

    run_audit(quiet=args.quiet, no_report=args.no_report)

    if args.fix:
        # Determine sources to scan
        if args.sources:
            source_names = [s.strip() for s in args.sources.split(",")]
        else:
            source_names = ["ticks", "iv", "ohlcv", "microstructure", "cross_asset"]

        # Determine symbols per source
        symbols_filter = [s.strip() for s in args.symbols.split(",")] if args.symbols else None

        # Build source\u2192symbols map from cached parquets
        from volforecast.cli.gap_detector import _SOURCE_DIRS
        from volforecast.utils.paths import resolve_project_root

        root = resolve_project_root()
        sources_map: dict[str, list[str]] = {}
        for src_name in source_names:
            subdir = _SOURCE_DIRS.get(src_name)
            if subdir is None:
                continue
            src_dir = root / subdir
            if not src_dir.exists():
                continue
            parquets = sorted(src_dir.glob("*.parquet"))
            syms = [p.stem for p in parquets]
            if symbols_filter:
                syms = [s for s in syms if s in symbols_filter]
            if syms:
                sources_map[src_name] = syms

        # Detect date range from manifest or use defaults
        start = _date(2013, 1, 2)
        end = _date(2025, 1, 3)

        if not args.quiet:
            print(f"\n{'=' * 60}")
            print("GAP DETECTION (NYSE calendar)")
            print(f"{'=' * 60}")

        run_audit_fix(
            sources=sources_map,
            start_date=start,
            end_date=end,
            confirm=args.confirm,
            project_root=root,
            quiet=args.quiet,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
