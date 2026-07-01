"""Data ingestion manifest — YAML contract + state.

Two layers:
- **Contract** — what data SHOULD exist (expected_columns, value_bounds, nan_budget)
- **State** — what DOES exist (per-symbol ingestion metadata, integrity audit results)

Ingest commands update state.  ``vol audit`` validates state against contract.

Provides both:
- ``ManifestManager`` — new typed API (YAML, dataclasses)
- Legacy functions (``record_ingestion``, ``summary_table``, etc.) — thin wrappers
  over the old JSON manifest for backward compat during migration.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from volforecast.utils import paths
from volforecast.utils.manifest_schema import (
    Integrity,
    Lineage,
    ManifestData,
    ManifestMeta,
    SourceContract,
    SymbolState,
    SymbolStatus,
    Universe,
)

# ══════════════════════════════════════════════════════════════════════════
#  ManifestManager — new YAML-based manifest with typed models
# ══════════════════════════════════════════════════════════════════════════


def _dict_to_lineage(d: dict[str, Any] | None) -> Lineage:
    if not d:
        return Lineage()
    return Lineage(
        code_version=d.get("code_version", ""),
        formula_version=d.get("formula_version", ""),
        source_query=d.get("source_query", ""),
    )


def _dict_to_integrity(d: dict[str, Any] | None) -> Integrity:
    if not d:
        return Integrity()
    return Integrity(
        nan_pct_max=d.get("nan_pct_max", 0.0),
        nan_columns=d.get("nan_columns", {}),
        date_gaps=d.get("date_gaps", []),
        issues=d.get("issues", []),
        last_validated=d.get("last_validated", ""),
    )


def _dict_to_symbol_state(d: dict[str, Any]) -> SymbolState:
    raw_status = d.get("status", "missing")
    try:
        status = SymbolStatus(raw_status)
    except ValueError:
        status = SymbolStatus.MISSING
    return SymbolState(
        status=status,
        rows=d.get("rows", 0),
        start_date=d.get("start_date", ""),
        end_date=d.get("end_date", ""),
        file_size_bytes=d.get("file_size_bytes", 0),
        last_ingested=d.get("last_ingested", ""),
        lineage=_dict_to_lineage(d.get("lineage")),
        integrity=_dict_to_integrity(d.get("integrity")),
    )


def _dict_to_source(d: dict[str, Any]) -> SourceContract:
    symbols_raw = d.get("symbols", {})
    symbols = {
        name: _dict_to_symbol_state(sdata)
        for name, sdata in symbols_raw.items()
        if isinstance(sdata, dict)
    }
    return SourceContract(
        description=d.get("description", ""),
        directory=d.get("directory", ""),
        serves_layers=d.get("serves_layers", []),
        file_pattern=d.get("file_pattern", "{symbol}.parquet"),
        index_dtype=d.get("index_dtype", "datetime64[ns]"),
        expected_columns=d.get("expected_columns", []),
        value_bounds=d.get("value_bounds", {}),
        invariants=d.get("invariants", []),
        nan_budget_pct=d.get("nan_budget_pct", 1.0),
        formula_version=d.get("formula_version", "v1.0"),
        formula_changelog=d.get("formula_changelog", {}),
        symbols=symbols,
        files=d.get("files", {}),
        market_wide_files=d.get("market_wide_files", {}),
    )


def _dict_to_manifest(raw: dict[str, Any]) -> ManifestData:
    meta_raw = raw.get("meta", {})
    uni_raw = meta_raw.get("universe", {})
    dr_raw = meta_raw.get("date_range", {})
    from volforecast.utils.manifest_schema import DateRange

    meta = ManifestMeta(
        schema_version=meta_raw.get("schema_version", 2),
        last_full_audit=meta_raw.get("last_full_audit", ""),
        universe=Universe(
            symbols=uni_raw.get("symbols", []),
            count=uni_raw.get("count", 0),
        ),
        date_range=DateRange(
            start=dr_raw.get("start", "2014-01-02"),
            end=dr_raw.get("end", "2024-12-31"),
            trading_days=dr_raw.get("trading_days", 2767),
        ),
    )
    sources_raw = raw.get("sources", {})
    sources = {
        name: _dict_to_source(sdata)
        for name, sdata in sources_raw.items()
        if isinstance(sdata, dict)
    }
    return ManifestData(meta=meta, sources=sources)


def _symbol_status_representer(dumper: yaml.Dumper, data: SymbolStatus) -> Any:
    return dumper.represent_str(data.value)


yaml.add_representer(SymbolStatus, _symbol_status_representer)


def _manifest_to_dict(data: ManifestData) -> dict[str, Any]:
    """Convert ManifestData to a plain dict suitable for YAML serialization."""
    return asdict(data)


class ManifestManager:
    """Typed YAML manifest with contract + state.

    Parameters
    ----------
    path : Path
        Path to the manifest YAML file.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> ManifestData:
        """Load and parse the manifest YAML into typed dataclasses.

        Returns an empty ``ManifestData`` if the file does not exist.
        """
        if not self._path.exists():
            return ManifestData()
        with open(self._path) as f:
            raw = yaml.safe_load(f)
        if not raw:
            return ManifestData()
        return _dict_to_manifest(raw)

    def save(self, data: ManifestData) -> None:
        """Serialize and write the manifest atomically.

        Uses ``tempfile`` + ``os.replace`` so a crash mid-write never
        leaves a corrupted file on disk.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        raw = _manifest_to_dict(data)
        fd, tmp = tempfile.mkstemp(
            suffix=".yaml",
            dir=str(self._path.parent),
        )
        try:
            with os.fdopen(fd, "w") as f:
                yaml.dump(raw, f, default_flow_style=False, sort_keys=False)
            os.replace(tmp, str(self._path))
        except BaseException:
            # Clean up temp file on failure
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def update_symbol(self, source: str, symbol: str, state: SymbolState) -> None:
        """Insert or overwrite a symbol's state within a source.

        Raises ``KeyError`` if *source* is not declared in the manifest.
        """
        data = self.load()
        if source not in data.sources:
            raise KeyError(f"Source {source!r} not in manifest")
        data.sources[source].symbols[symbol] = state
        self.save(data)

    def get_status(self, source: str, symbol: str) -> SymbolStatus:
        """Return a symbol's effective status, accounting for stale detection.

        Raises ``KeyError`` if *source* is not in the manifest.
        """
        data = self.load()
        if source not in data.sources:
            raise KeyError(f"Source {source!r} not in manifest")
        src = data.sources[source]
        if symbol not in src.symbols:
            return SymbolStatus.MISSING
        sym = src.symbols[symbol]
        # Stale detection: symbol's formula_version behind source's
        if (
            sym.lineage.formula_version
            and src.formula_version
            and sym.lineage.formula_version != src.formula_version
        ):
            return SymbolStatus.STALE
        return sym.status

    def summary(self, source: str | None = None) -> str:
        """Human-readable summary of manifest state.

        Parameters
        ----------
        source : str or None
            Filter to a single source.  ``None`` shows all sources.
        """
        data = self.load()
        if not data.sources:
            return "No sources defined."

        sources_to_show = (
            {source: data.sources[source]} if source and source in data.sources else data.sources
        )
        lines: list[str] = []
        for name, src in sources_to_show.items():
            n_sym = len(src.symbols)
            n_complete = sum(1 for s in src.symbols.values() if s.status == SymbolStatus.COMPLETE)
            lines.append(f"\n[{name}] — {n_sym} symbol(s), {n_complete} complete")
            if src.symbols:
                lines.append(
                    f"  {'Symbol':<10} {'Status':<10} {'Rows':>6}"
                    f"  {'Start':<12} {'End':<12} {'Ingested'}"
                )
                lines.append(f"  {'─' * 10} {'─' * 10} {'─' * 6}  {'─' * 12} {'─' * 12} {'─' * 19}")
                for sym_name in sorted(src.symbols):
                    s = src.symbols[sym_name]
                    lines.append(
                        f"  {sym_name:<10} {s.status.value:<10} {s.rows:>6}"
                        f"  {s.start_date:<12} {s.end_date:<12}"
                        f"  {s.last_ingested}"
                    )
        return "\n".join(lines) if lines else "No sources defined."


# ══════════════════════════════════════════════════════════════════════════
#  Convenience helpers
# ══════════════════════════════════════════════════════════════════════════

# Source name mapping: old data_type keys → new YAML source names
_SOURCE_ALIASES: dict[str, str] = {
    "rv": "ticks",
    "iv_surface": "iv",
    "ohlcv": "ohlcv",
    "micro": "microstructure",
    "macro": "cross_asset",
}


def _yaml_manifest_path() -> Path:
    """Path to the YAML manifest: data/manifest.yaml."""
    return paths.resolve_project_root() / "data" / "manifest.yaml"


def record_ingestion_yaml(
    data_type: str,
    symbol: str,
    start_date: date,
    end_date: date,
    rows: int,
    file_size_bytes: int = 0,
) -> None:
    """Record a successful ingestion in the YAML manifest.

    Silently skips if manifest.yaml does not exist or the source is unknown.
    """
    yaml_path = _yaml_manifest_path()
    if not yaml_path.exists():
        return
    source = _SOURCE_ALIASES.get(data_type, data_type)
    mgr = ManifestManager(yaml_path)
    data = mgr.load()
    if source not in data.sources:
        return
    state = SymbolState(
        status=SymbolStatus.COMPLETE,
        rows=rows,
        start_date=str(start_date),
        end_date=str(end_date),
        file_size_bytes=file_size_bytes,
        last_ingested=datetime.now().isoformat(timespec="seconds"),
        lineage=Lineage(formula_version=data.sources[source].formula_version),
    )
    mgr.update_symbol(source, symbol, state)


# ══════════════════════════════════════════════════════════════════════════
#  Legacy JSON-based functions (backward compat — will be removed)
# ══════════════════════════════════════════════════════════════════════════


def _manifest_path() -> Path:
    """Path to the legacy manifest file: data/manifest.json."""
    return paths.resolve_project_root() / "data" / "manifest.json"


def load_manifest() -> dict[str, Any]:
    """Load the legacy JSON manifest from disk."""
    path = _manifest_path()
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def save_manifest(manifest: dict[str, Any]) -> Path:
    """Write the legacy JSON manifest to disk."""
    path = _manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    return path


def record_ingestion(
    data_type: str,
    symbol: str,
    start_date: date,
    end_date: date,
    rows: int,
    skipped_dates: list[tuple[date, str]] | None = None,
) -> None:
    """Record a successful ingestion in the legacy JSON manifest."""
    manifest = load_manifest()

    if data_type not in manifest:
        manifest[data_type] = {}

    entry = manifest[data_type].get(symbol, {})

    existing_start = entry.get("start_date")
    existing_end = entry.get("end_date")
    new_start = str(start_date)
    new_end = str(end_date)
    if existing_start:
        new_start = min(new_start, existing_start)
    if existing_end:
        new_end = max(new_end, existing_end)

    entry["start_date"] = new_start
    entry["end_date"] = new_end
    entry["rows"] = rows
    entry["last_updated"] = datetime.now().isoformat(timespec="seconds")

    if skipped_dates:
        existing_skips: dict[str, str] = {
            s["date"]: s["reason"] for s in entry.get("skipped_dates", [])
        }
        for skip_date, reason in skipped_dates:
            existing_skips[str(skip_date)] = reason
        entry["skipped_dates"] = [
            {"date": d, "reason": r} for d, r in sorted(existing_skips.items())
        ]

    manifest[data_type][symbol] = entry
    save_manifest(manifest)


def get_ingested_symbols(data_type: str) -> dict[str, dict[str, Any]]:
    """Return all symbols ingested for a given data type (legacy JSON)."""
    manifest = load_manifest()
    return manifest.get(data_type, {})


def get_missing_symbols(data_type: str, target_universe: set[str]) -> set[str]:
    """Return symbols not yet ingested for a data type (legacy JSON)."""
    ingested = set(get_ingested_symbols(data_type).keys())
    return target_universe - ingested


def summary_table(data_type: str | None = None) -> str:
    """Human-readable summary of ingestion status (legacy JSON)."""
    manifest = load_manifest()
    if not manifest:
        return "No data ingested yet."

    _META_KEYS = {"generated_at", "universe", "schema_groups", "layer_readiness"}
    if data_type:
        types_to_show = [data_type]
    else:
        types_to_show = sorted(k for k in manifest.keys() if k not in _META_KEYS)
    lines: list[str] = []

    for dtype in types_to_show:
        entries = manifest.get(dtype, {})
        if not isinstance(entries, dict):
            continue
        symbol_entries = {
            k: v for k, v in entries.items() if isinstance(v, dict) and "start_date" in v
        }
        if not symbol_entries:
            continue
        lines.append(f"\n[{dtype}] — {len(symbol_entries)} symbol(s)")
        lines.append(f"  {'Symbol':<10} {'Start':<12} {'End':<12} {'Rows':>6}  {'Updated'}")
        lines.append(f"  {'─' * 10} {'─' * 12} {'─' * 12} {'─' * 6}  {'─' * 19}")
        for sym in sorted(symbol_entries.keys()):
            e = symbol_entries[sym]
            lines.append(
                f"  {sym:<10} {e.get('start_date', '?'):<12} "
                f"{e.get('end_date', '?'):<12} {e.get('rows', '?'):>6}  "
                f"{e.get('last_updated', '?')}"
            )

    return "\n".join(lines) if lines else "No data ingested yet."
