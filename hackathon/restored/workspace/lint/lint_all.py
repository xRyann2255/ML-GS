"""Run all workspace lint checks.

Usage:
    python workspace/lint/lint_all.py           # run all lints
    python workspace/lint/lint_all.py --quick    # fast lints only (skip slow checks)
    python workspace/lint/lint_all.py --fix      # pass --fix to lints that support it

Exit code: 0 if all pass, 1 if any fail.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Ensure UTF-8 output on Windows consoles (avoids cp1252 encode errors)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

PYTHON = sys.executable
TOOLS_DIR = Path(__file__).resolve().parent


class _Tee:
    """Tee stdout to a StringIO buffer for --out-file capture."""

    def __init__(self, original, buffer):
        self._orig = original
        self._buf = buffer

    def write(self, s):
        self._orig.write(s)
        self._buf.write(s)
        return len(s)

    def flush(self):
        self._orig.flush()

    @property
    def encoding(self):
        return getattr(self._orig, "encoding", "utf-8")

    def reconfigure(self, **kw):
        if hasattr(self._orig, "reconfigure"):
            self._orig.reconfigure(**kw)

# ── Lint registry ────────────────────────────────────────────────────────
# Each entry: (label, script_path, extra_args, is_slow, supports_fix)
LINTS: list[tuple[str, Path, list[str], bool, bool]] = [
    (
        "secexpr safety",
        TOOLS_DIR / "lint_secexpr_safety.py",
        [],
        False,
        False,
    ),
    (
        "hardcoded env",
        TOOLS_DIR / "lint_hardcoded_env.py",
        [],
        False,
        True,
    ),
    (
        "memory schema",
        TOOLS_DIR / "validate_memory.py",
        [],
        False,
        False,
    ),
    (
        "skills structure",
        TOOLS_DIR / "lint_skills_structure.py",
        [],
        False,
        False,
    ),
    (
        "forbidden patterns",
        TOOLS_DIR / "lint_forbidden_patterns.py",
        [],
        False,
        False,
    ),
    (
        "skills content",
        TOOLS_DIR / "validate_skills.py",
        [],
        False,
        True,
    ),
    (
        "memory priority",
        TOOLS_DIR / "lint_memory_priority.py",
        [],
        False,
        False,
    ),
    (
        "design rules",
        TOOLS_DIR / "design_lint.py",
        [],
        False,
        False,
    ),
    (
        "broken refs",
        TOOLS_DIR / "lint_broken_refs.py",
        [],
        False,
        False,
    ),
    (
        "memory index completeness",
        TOOLS_DIR / "lint_memory_index_completeness.py",
        [],
        False,
        False,
    ),
    (
        "doc safety",
        TOOLS_DIR / "lint_doc_safety.py",
        [],
        False,
        False,
    ),
    (
        "registry drift",
        TOOLS_DIR / "lint_registry_drift.py",
        [],
        False,
        False,
    ),
    (
        "vscode md compat",
        TOOLS_DIR / "lint_vscode_md.py",
        [],
        False,
        True,
    ),
    (
        "vscode tasks",
        TOOLS_DIR / "lint_vscode_tasks.py",
        [],
        False,
        False,
    ),
    (
        "secrets",
        TOOLS_DIR / "lint_secrets.py",
        [],
        False,
        False,
    ),
    (
        "args contract",
        TOOLS_DIR / "lint_args_contract.py",
        [],
        False,
        False,
    ),
    (
        "model pins",
        TOOLS_DIR / "lint_model_pins.py",
        [],
        False,
        False,
    ),
    (
        "wrapper targets",
        TOOLS_DIR / "lint_wrapper_targets.py",
        [],
        False,
        False,
    ),
    (
        "vol parity",
        TOOLS_DIR / "lint_vol_parity.py",
        [],
        False,
        False,
    ),
    (
        "prompts",
        TOOLS_DIR / "lint_prompts.py",
        [],
        False,
        False,
    ),
    (
        "canonical schema",
        TOOLS_DIR / "lint_canonical_schema.py",
        [],
        False,
        False,
    ),
]


def run_lint(label: str, script: Path, extra_args: list[str], fix: bool, supports_fix: bool) -> tuple[str, bool, float, list[str]]:
    """Run a single lint. Returns (label, passed, elapsed_seconds, output_lines)."""
    lines: list[str] = []

    if not script.is_file():
        lines.append(f"  SKIP  {label} — {script} not found")
        return label, True, 0.0, lines

    args = [PYTHON, str(script)] + extra_args
    if fix and supports_fix and "--fix" not in extra_args:
        args.append("--fix")

    t0 = time.time()
    proc = subprocess.run(args, capture_output=True, timeout=120)
    elapsed = time.time() - t0

    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")

    passed = proc.returncode == 0
    status = "PASS" if passed else "FAIL"
    lines.append(f"  {status}  {label}  ({elapsed:.1f}s)")

    for line in stdout.splitlines():
        if line.strip():
            lines.append(f"        {line}")
    if not passed and stderr.strip():
        for line in stderr.splitlines()[-5:]:
            lines.append(f"        [stderr] {line}")

    return label, passed, elapsed, lines


def _flush_out(buf: io.StringIO | None, orig_stdout, out_file: str | None) -> None:
    """Write captured tee buffer to out_file."""
    if buf and out_file:
        sys.stdout = orig_stdout
        p = Path(out_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(buf.getvalue(), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="Skip slow lint checks")
    ap.add_argument("--fix", action="store_true", help="Pass --fix to lints that support it")
    ap.add_argument("--jobs", "-j", type=int, default=4, help="Max parallel lint tasks (default: 4)")
    ap.add_argument("--args-file", help="Load args from JSON file")
    ap.add_argument("--out-file", help="Write output to file")
    ap.add_argument("--check", help="Run single check by label (e.g. 'memory')")
    args = ap.parse_args()

    # --args-file: load JSON and override defaults
    if args.args_file:
        with open(args.args_file, "r", encoding="utf-8") as f:
            fa = json.load(f)
        if fa.get("quick"):
            args.quick = True
        if fa.get("fix"):
            args.fix = True
        if "check" in fa:
            args.check = fa["check"]
        if fa.get("out_file") and not args.out_file:
            args.out_file = fa["out_file"]

    # Install tee for --out-file capture
    _buf = None
    _orig_stdout = sys.stdout
    if args.out_file:
        _buf = io.StringIO()
        sys.stdout = _Tee(_orig_stdout, _buf)

    max_workers = max(1, args.jobs)

    print("=" * 50)
    print(f"Running all lint checks (max {max_workers} parallel)")
    print("=" * 50)

    # Filter eligible lints
    _CHECK_ALIASES = {"memory": "memory schema"}
    if args.check:
        target = _CHECK_ALIASES.get(args.check, args.check)
        eligible = [
            (label, script, extra_args, supports_fix)
            for label, script, extra_args, is_slow, supports_fix in LINTS
            if label == target
        ]
        if not eligible:
            print(f"ERROR: Unknown check '{args.check}'")
            _flush_out(_buf, _orig_stdout, args.out_file)
            return 1
    else:
        eligible = [
            (label, script, extra_args, supports_fix)
            for label, script, extra_args, is_slow, supports_fix in LINTS
            if not (args.quick and is_slow)
        ]
        for label, script, extra_args, is_slow, supports_fix in LINTS:
            if args.quick and is_slow:
                print(f"  SKIP  {label}  (--quick)")

    # Run in parallel, show progress bar, print results in submission order
    results: list[tuple[str, bool]] = []
    total_time = 0.0
    total_eligible = len(eligible)
    completed_count = 0

    def _progress(done: int, total: int, label: str, *, final: bool = False) -> None:
        width = 20
        filled = int(width * done / total) if total else width
        bar = "#" * filled + "." * (width - filled)
        print(f"  [{bar}] {done}/{total} {label}", flush=True)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(run_lint, label, script, extra_args, fix=args.fix, supports_fix=supports_fix): label
            for label, script, extra_args, supports_fix in eligible
        }
        # Collect results as they complete, then print in original order
        done_map: dict[str, tuple[bool, float, list[str]]] = {}
        for future in as_completed(futures):
            label, passed, elapsed, lines = future.result()
            done_map[label] = (passed, elapsed, lines)
            completed_count += 1
            _progress(completed_count, total_eligible, label)

    _progress(total_eligible, total_eligible, "done", final=True)

    # Print in original registration order
    for label, _script, _extra, _sf in eligible:
        passed, elapsed, lines = done_map[label]
        for line in lines:
            print(line, flush=True)
        results.append((label, passed))
        total_time += elapsed

    print("=" * 50)
    failures = [name for name, ok in results if not ok]
    if failures:
        print(f"FAILED ({len(failures)}/{len(results)}): {', '.join(failures)}")
        print(f"Total: {total_time:.1f}s")
        rc = 1
    else:
        print(f"ALL PASSED ({len(results)} checks, {total_time:.1f}s)")
        rc = 0

    _flush_out(_buf, _orig_stdout, args.out_file)
    return rc


if __name__ == "__main__":
    sys.exit(main())
