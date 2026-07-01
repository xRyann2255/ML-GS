"""EPSSP Test Coverage — fetch and report test coverage from EPSSP SSP page."""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EPSSP_URL = "https://www.epssp.site.gs.com/ssps/Current/Sensitive_Slang_Procedure"
DEFAULT_PREFIXES = ["_LIB", "_PROCM", "_UT"]
DEFAULT_OUT = "workspace/tmp/epssp_coverage_out.txt"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    return re.sub(r"<[^>]+>", "", html).strip()


def extract_name(html: str) -> str:
    """Extract visible script name from <a>...</a> HTML."""
    m = re.search(r">([^<]+)</a>", html)
    return m.group(1).strip() if m else strip_html(html)


def get_prefix(name: str) -> str:
    for p in ("_APP", "_CFG", "_LIB", "_PROCM", "_TYPE", "_UT", "Test:", "UFO"):
        if name.upper().startswith(p.upper()):
            return p
    return "Other"


def parse_int(val) -> int:
    """Parse an integer from a possibly comma-/space-padded string."""
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip().replace(",", "")
    return int(s) if s.isdigit() else 0


def sort_val(obj) -> float:
    """Extract numeric sort value from {sort, text} objects."""
    if isinstance(obj, dict):
        try:
            return float(obj.get("sort", 0))
        except (ValueError, TypeError):
            return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_epssp(procedure: str, proc_id: str, cache_file: str | None) -> dict:
    """Fetch scripts data from EPSSP via PowerShell (Kerberos auth)."""
    if cache_file and os.path.isfile(cache_file):
        print(f"[info] Loading cached data from {cache_file}", file=sys.stderr)
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    body_dict = {
        "action": "slang-scripts-tab-data",
        "procedure": procedure,
        "id": str(proc_id),
    }
    body_json = json.dumps(body_dict)

    # Use a temp file for the PowerShell output to avoid quoting issues
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    ps_script = (
        f'$body = \'{body_json}\'\n'
        f'$resp = Invoke-WebRequest -Uri "{EPSSP_URL}" '
        f'-Method POST -Body $body -ContentType "application/json" '
        f'-UseDefaultCredentials -UseBasicParsing\n'
        f'[System.IO.File]::WriteAllText("{tmp_path}", $resp.Content)\n'
    )

    print(f"[info] Fetching EPSSP data for {procedure} (id={proc_id}) ...", file=sys.stderr)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        print(f"[error] PowerShell fetch failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    with open(tmp_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    os.remove(tmp_path)

    # Optionally cache
    if cache_file:
        os.makedirs(os.path.dirname(cache_file) or ".", exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
        print(f"[info] Cached to {cache_file}", file=sys.stderr)

    return data


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(data: dict, prefixes: list[str], show_all: bool) -> str:
    """Analyze scripts and return formatted report."""
    scripts = data.get("scripts", [])
    if not scripts:
        return "ERROR: No scripts data found in response."

    lines = []
    lines.append("")

    # -- Summary --
    from collections import Counter

    type_counts = Counter(s["Script Type"] for s in scripts)
    testing_by_prefix: dict[str, Counter] = {}
    for s in scripts:
        name = extract_name(s["Script"])
        pfx = get_prefix(name)
        if pfx not in testing_by_prefix:
            testing_by_prefix[pfx] = Counter()
        testing_by_prefix[pfx][strip_html(s.get("StrTesting", ""))] += 1

    lines.append("SUMMARY")
    lines.append("-" * 70)
    lines.append(f"  Total scripts in procedure: {len(scripts)}")
    lines.append(f"  Script types: {', '.join(f'{t}({c})' for t, c in type_counts.most_common())}")
    lines.append("")
    for pfx in sorted(testing_by_prefix):
        cnt = testing_by_prefix[pfx]
        total = sum(cnt.values())
        parts = ", ".join(f"{k}: {v}" for k, v in cnt.most_common())
        lines.append(f"  {pfx:>8} ({total:>4}): {parts}")
    lines.append("")

    # -- Build records for target prefixes --
    records = []
    for s in scripts:
        name = extract_name(s["Script"])
        pfx = get_prefix(name)
        if pfx.upper() not in [p.upper() for p in prefixes]:
            continue

        lines_count = parse_int(s.get("Lines", 0))
        refs_direct = parse_int(s.get("Refs (Direct)", 0))
        refs_total = parse_int(s.get("Refs (Total)", 0))
        testing_status = strip_html(s.get("StrTesting", ""))
        testability = strip_html(s.get("StrTestability", ""))
        test_script_sort = sort_val(s.get("Test Script", {}))
        test_script_text = strip_html(s.get("Test Script", {}).get("text", "")) if isinstance(s.get("Test Script"), dict) else ""
        total_cov = sort_val(s.get("TotalCoverage", {}))
        func_cov = sort_val(s.get("FunctionCoverage", {}))
        tested_label = strip_html(s.get("Tested", {}).get("text", "")) if isinstance(s.get("Tested"), dict) else ""

        records.append({
            "name": name,
            "prefix": pfx,
            "lines": lines_count,
            "refs_direct": refs_direct,
            "refs_total": refs_total,
            "testing": testing_status,
            "testability": testability,
            "test_script": test_script_text,
            "test_sort": test_script_sort,
            "total_cov": total_cov,
            "func_cov": func_cov,
            "tested": tested_label,
        })

    # -- Filter: scripts missing tests or not tested --
    if show_all:
        missing = records
    else:
        missing = [r for r in records if r["testing"] in ("Not Tested", "Not Possible", "N/A")]

    # Sort by refs_total DESC, lines DESC
    missing.sort(key=lambda r: (-r["refs_total"], -r["lines"]))

    # -- Group by prefix --
    for pfx in prefixes:
        group = [r for r in missing if r["prefix"].upper() == pfx.upper()]
        if not group:
            continue

        status_dist = Counter(r["testing"] for r in group)
        status_str = ", ".join(f"{k}: {v}" for k, v in status_dist.most_common())

        lines.append(f"{pfx} SCRIPTS — NOT FULLY TESTED ({len(group)}) [{status_str}]")
        lines.append("-" * 110)
        hdr = f"{'#':>4}  {'Script':<48} {'Lines':>6} {'DRef':>5} {'TRef':>5} {'Testing':<14} {'TotCov':>7} {'TestScript'}"
        lines.append(hdr)
        lines.append("-" * 110)

        for i, r in enumerate(group, 1):
            cov_str = f"{r['total_cov']:.1f}%" if r["total_cov"] > 0 else "-"
            ts = r["test_script"][:30] if r["test_script"] and r["test_script"] != "N/A" else "-"
            lines.append(
                f"{i:>4}  {r['name']:<48} {r['lines']:>6} {r['refs_direct']:>5} {r['refs_total']:>5} "
                f"{r['testing']:<14} {cov_str:>7} {ts}"
            )

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="EPSSP Test Coverage Report")
    parser.add_argument("--args-file", help="JSON args file path")
    args = parser.parse_args()

    # Load args from file
    cfg = {}
    if args.args_file:
        with open(args.args_file, "r") as f:
            cfg = json.load(f)

    procedure = cfg.get("procedure", "Eq1D Brazil")
    proc_id = cfg.get("id", "503")
    out_file = cfg.get("out_file", DEFAULT_OUT)
    prefixes = cfg.get("prefixes", DEFAULT_PREFIXES)
    cache = cfg.get("cache_file", None)
    show_all = cfg.get("show_all", False)

    data = fetch_epssp(procedure, proc_id, cache)

    header = f"EPSSP Test Coverage Report — {procedure} (ID: {proc_id})"
    report = f"{header}\n{'=' * len(header)}\n"
    report += analyze(data, prefixes, show_all)

    # Write output
    os.makedirs(os.path.dirname(out_file) or ".", exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(report)
    print(f"\n[info] Report written to {out_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
