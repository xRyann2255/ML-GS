"""GSVIVS01 audit — Phase 1 schema probe.

Reads ``data/external/output.json`` with NO assumptions about its content.
Emits three artifacts under ``workspace/tmp/``:

* ``gsvivs_schema_keys_by_year.txt`` — for each top-level field path that ever
  appears in a day's ``value`` dict, the per-year count of days where the field
  is present. Catches zombie / renamed fields.
* ``gsvivs_schema_sample_<date>.txt`` — recursive type-tree dump for three
  sample days (early / mid / late).
* ``gsvivs_source_census.txt`` — full census of every ``source`` field value
  found anywhere in the document (trades, portfolio, risks). Counts per-year.

NO claims are derived here. This script only describes what is in the JSON.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = REPO_ROOT / "data" / "external" / "output.json"
OUT_DIR = REPO_ROOT / "workspace" / "tmp"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Sample days for full schema dump
SAMPLE_DATES = {"2022-06-01", "2024-01-03", "2026-05-29"}

MAX_DEPTH = 8
TRUNCATE_LIST_AT = 3


def type_tree(obj, depth: int = 0) -> str:
    """Recursive type tree dump. Truncates long lists, caps depth."""
    pad = "  " * depth
    if depth > MAX_DEPTH:
        return f"{pad}<truncated depth>"
    if isinstance(obj, dict):
        if not obj:
            return f"{pad}{{}} (empty dict)"
        lines = [f"{pad}{{"]
        for k, v in obj.items():
            sub = type_tree(v, depth + 1)
            lines.append(f"{pad}  {k!r}:")
            lines.append(sub)
        lines.append(f"{pad}}}")
        return "\n".join(lines)
    if isinstance(obj, list):
        n = len(obj)
        if n == 0:
            return f"{pad}[] (empty list)"
        lines = [f"{pad}[ (list, n={n})"]
        for i, item in enumerate(obj[:TRUNCATE_LIST_AT]):
            lines.append(f"{pad}  [{i}]:")
            lines.append(type_tree(item, depth + 1))
        if n > TRUNCATE_LIST_AT:
            lines.append(f"{pad}  ... +{n - TRUNCATE_LIST_AT} more")
        lines.append(f"{pad}]")
        return "\n".join(lines)
    if isinstance(obj, str):
        preview = obj if len(obj) <= 40 else obj[:37] + "..."
        return f"{pad}str: {preview!r}"
    if isinstance(obj, bool):
        return f"{pad}bool: {obj}"
    if isinstance(obj, (int, float)):
        return f"{pad}{type(obj).__name__}: {obj}"
    if obj is None:
        return f"{pad}None"
    return f"{pad}{type(obj).__name__}: {obj!r}"


def year_of(date_str: str) -> int:
    return int(date_str[:4])


def walk_sources(obj, sources: Counter) -> None:
    """Walk arbitrary nested structure and tally every dict-level 'source'."""
    if isinstance(obj, dict):
        if "source" in obj and isinstance(obj["source"], str):
            sources[obj["source"]] += 1
        for v in obj.values():
            walk_sources(v, sources)
    elif isinstance(obj, list):
        for v in obj:
            walk_sources(v, sources)


def main() -> None:
    print(f"Loading {INPUT_FILE} ({INPUT_FILE.stat().st_size / 1e6:.1f} MB)")
    with INPUT_FILE.open("r") as f:
        data = json.load(f)
    print(f"  -> {len(data)} day entries")

    # ---- Field coverage by year ------------------------------------------
    # Top-level field paths (one level into ``value``) and their per-year count
    keys_by_year: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    sources_by_year: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    duplicate_dates: Counter = Counter()
    date_seen: Counter = Counter()

    for entry in data:
        d = entry.get("date")
        date_seen[d] += 1
        if date_seen[d] > 1:
            duplicate_dates[d] += 1
        year = year_of(d)
        value = entry.get("value", {})
        if isinstance(value, dict):
            for k in value.keys():
                keys_by_year[k][year] += 1
        # source census walks the whole entry
        srcs: Counter = Counter()
        walk_sources(entry, srcs)
        for src, cnt in srcs.items():
            sources_by_year[src][year] += cnt

    years = sorted({y for d in keys_by_year.values() for y in d.keys()})

    # ---- Write field coverage --------------------------------------------
    out1 = OUT_DIR / "gsvivs_schema_keys_by_year.txt"
    with out1.open("w") as f:
        f.write(f"Source: {INPUT_FILE}\n")
        f.write(f"Total day entries: {len(data)}\n")
        f.write(f"Unique dates: {len(date_seen)}\n")
        f.write(f"Duplicate dates: {len(duplicate_dates)}\n")
        if duplicate_dates:
            for d, c in sorted(duplicate_dates.items()):
                f.write(f"  {d}: {c + 1} occurrences\n")
        f.write("\n")
        f.write("Per-field count of days present, by year\n")
        f.write("-" * 60 + "\n")
        header = ["field".ljust(35)] + [str(y).rjust(6) for y in years] + ["  total".rjust(8)]
        f.write("".join(header) + "\n")
        for field in sorted(keys_by_year.keys()):
            row = [field.ljust(35)]
            total = 0
            for y in years:
                c = keys_by_year[field].get(y, 0)
                row.append(str(c).rjust(6))
                total += c
            row.append(str(total).rjust(8))
            f.write("".join(row) + "\n")
    print(f"  wrote {out1}")

    # ---- Write source census ---------------------------------------------
    out2 = OUT_DIR / "gsvivs_source_census.txt"
    with out2.open("w") as f:
        f.write(f"Source: {INPUT_FILE}\n")
        f.write("Census of every 'source' field anywhere in the document\n")
        f.write("=" * 60 + "\n\n")
        header = ["source".ljust(40)] + [str(y).rjust(8) for y in years] + ["   total".rjust(10)]
        f.write("".join(header) + "\n")
        ranked = sorted(sources_by_year.items(),
                        key=lambda kv: -sum(kv[1].values()))
        for src, by_year in ranked:
            row = [src.ljust(40)]
            total = 0
            for y in years:
                c = by_year.get(y, 0)
                row.append(str(c).rjust(8))
                total += c
            row.append(str(total).rjust(10))
            f.write("".join(row) + "\n")
    print(f"  wrote {out2}")

    # ---- Write schema sample for 3 days ----------------------------------
    by_date = {e["date"]: e for e in data}
    actual_samples = []
    for want in sorted(SAMPLE_DATES):
        # Snap to nearest available date >= want
        snap = next((d for d in sorted(by_date) if d >= want), None)
        if snap is None:
            continue
        actual_samples.append(snap)
        out3 = OUT_DIR / f"gsvivs_schema_sample_{snap}.txt"
        with out3.open("w") as f:
            f.write(f"Schema sample for date {snap}\n")
            f.write("=" * 60 + "\n")
            f.write(type_tree(by_date[snap]))
        print(f"  wrote {out3}")

    print("\nDone. Inspect outputs in workspace/tmp/")


if __name__ == "__main__":
    main()
