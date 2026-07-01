"""Fix a failing Slang RegTest: run, diagnose, lint, re-run, and submit code review.

Usage:
    python fix_regtest.py --db "~{kerberos}!clean" --test "Test: Eq1D Brazil Foo" \\
        --libs "_LIB Eq1D Brazil Foo" [--max-iterations 5] [--no-review]

Steps:
    1. Run the RegTest and capture output
    2. Read the test source (and optionally LIB sources)
    3. Lint the test script
    4. Run the RegTest again to verify
    5. Submit a code review with all changed scripts
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

# Import helpers from sibling skills
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
SLANG_EDIT_SRC = os.path.join(SKILL_DIR, "..", "..", "SLANG_EDIT", "src")
sys.path.insert(0, SLANG_EDIT_SRC)
from edit import slang_escape, build_read_expr, run_secexpr, run_secexpr_raw
sys.path.insert(0, os.path.join(SKILL_DIR, "..", "..", "_shared"))
from subprocess_utils import run_cmd  # noqa: E402

ENV_CMD = r"H:\all-languages-env.cmd"


# ---------------------------------------------------------------------------
# Step 1: Run RegTest
# ---------------------------------------------------------------------------


def run_regtest(db: str, test_name: str, output_path: str) -> dict:
    """Run a RegTest via secexpr and return parsed results."""
    fd, batch_path = tempfile.mkstemp(suffix=".cmd", prefix="regtest_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(f"@echo off\ncall {ENV_CMD} >nul 2>&1\n")
            f.write(
                f'secexpr NullDb --source "{db};PS" --safe -s "{test_name}"\n'
            )

        print(f"Running RegTest: {test_name} ...")
        result = run_cmd(
            ["cmd", "/c", batch_path],
            capture_output=True,
            timeout=600,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")

        full_output = stdout + "\n" + stderr
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_output)

        return parse_regtest_output(full_output)
    finally:
        os.unlink(batch_path)


def parse_regtest_output(output: str) -> dict:
    """Parse RegTest output into a structured result."""
    lines = output.splitlines()
    passed = []
    failed = []
    errors = []

    for line in lines:
        if "ASSERTION PASSED" in line:
            passed.append(line.strip())
        elif "ASSERTION FAILED" in line:
            failed.append(line.strip())
        elif "Slang Error" in line or "DT_MSG_IS_ERROR" in line:
            errors.append(line.strip())
        elif "failed @" in line:
            errors.append(line.strip())
        elif "SubDbDrvGetByName" in line:
            errors.append(line.strip())

    suite_completed = any("Suite took" in line for line in lines)

    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "suite_completed": suite_completed,
        "success": len(failed) == 0 and len(errors) == 0 and suite_completed,
        "passed_count": len(passed),
        "failed_count": len(failed),
        "error_count": len(errors),
    }


# ---------------------------------------------------------------------------
# Step 2: Read Script Source
# ---------------------------------------------------------------------------


def read_script_source(db: str, script_name: str) -> str:
    """Read a Slang script's source code from SecDB."""
    expr = build_read_expr(script_name)
    raw = run_secexpr_raw(db, expr, safe=True)
    return raw.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Step 3: Run Lint
# ---------------------------------------------------------------------------


def build_lint_wrapper(script_name: str, source: str) -> str:
    """Build a Slang expression that runs lint on the given source."""
    escaped = source.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f"""Link( "_LIB Slang Lint Fns" );
TestCode = "{escaped}";
Try( Ex )
{{
    Result = @LIBSlang::Lint(
        "{slang_escape(script_name)}",
        Expression := TestCode,
        Cache Results := False,
        Use Cached Results := False,
        Filter OK Status := True,
    );
    Print( Sprintf( "ISSUES: %d\\n", Size( Result ) ) );
    ForEach( Err, Result )
    {{
        S = Sprintf( "%g", Err.Status );
        T = "";
        Try( X1 ) {{ T = Err.Text; }} : {{}};
        Print( Sprintf( "  [%s] %s\\n", S, T ) );
    }};
}}
:
{{
    Print( Sprintf( "Exception: %s\\n", Ex.Describe() ) );
}};
"""


def run_lint(db: str, script_name: str, source: str, output_path: str) -> dict:
    """Run native Slang lint and return parsed results."""
    wrapper = build_lint_wrapper(script_name, source)

    fd, slang_path = tempfile.mkstemp(suffix=".slang", prefix="lint_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(wrapper)

        fd2, batch_path = tempfile.mkstemp(suffix=".cmd", prefix="lint_")
        try:
            with os.fdopen(fd2, "w") as f:
                f.write(f"@echo off\ncall {ENV_CMD} >nul 2>&1\n")
                f.write(
                    f'secexpr "Equity RO" --source ProdSource --safe -r -t '
                    f'< "{slang_path}"\n'
                )

            print(f"Running lint: {script_name} ...")
            result = run_cmd(
                ["cmd", "/c", batch_path],
                capture_output=True,
                timeout=600,
            )
            stdout = result.stdout.decode("utf-8", errors="replace")
            stderr = result.stderr.decode("utf-8", errors="replace")

            full_output = stdout + "\n" + stderr
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_output)

            return parse_lint_output(stdout)
        finally:
            os.unlink(batch_path)
    finally:
        os.unlink(slang_path)


def parse_lint_output(output: str) -> dict:
    """Parse lint output into structured results."""
    issues = []
    issue_count = 0

    for line in output.splitlines():
        m = re.match(r"ISSUES:\s*(\d+)", line)
        if m:
            issue_count = int(m.group(1))

        m = re.match(r"\s+\[(\S+)\]\s+(.*)", line)
        if m:
            status = float(m.group(1))
            text = m.group(2)
            issues.append({"status": status, "text": text})

    # Classify issues
    lint_errors = [i for i in issues if i["status"] == 1
                   and "Tests with 'Unknown' script" not in i["text"]]
    lint_warnings = [i for i in issues if i["status"] == 2]
    lint_info = [i for i in issues if i["status"] >= 3]

    return {
        "issue_count": issue_count,
        "errors": lint_errors,
        "warnings": lint_warnings,
        "info": lint_info,
        "clean": len(lint_errors) == 0 and len(lint_warnings) == 0,
    }


# ---------------------------------------------------------------------------
# Step 4: Submit Code Review (delegates to SLANG_REVIEW)
# ---------------------------------------------------------------------------


def submit_review(
    db: str,
    changed_scripts: list[str],
    subject: str,
    description: str,
    testing_description: str,
    output_path: str,
) -> str | None:
    """Submit a code review via the SLANG_REVIEW skill."""
    review_py = os.path.join(
        SKILL_DIR, "..", "..", "SLANG_REVIEW", "src", "review.py"
    )
    if not os.path.exists(review_py):
        print("ERROR: SLANG_REVIEW skill not found")
        return None

    cmd = [
        sys.executable,
        review_py,
        "--db", db,
        "--scripts", *changed_scripts,
        "--subject", subject,
        "--description", description,
        "--testing-description", testing_description,
    ]

    print(f"Submitting code review for: {', '.join(changed_scripts)}")
    result = run_cmd(cmd, capture_output=True, timeout=1800)
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")

    full_output = stdout + "\n" + stderr
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_output)

    print(stdout)

    for line in stdout.splitlines():
        if "REVIEW_URL=" in line:
            return line.split("REVIEW_URL=", 1)[1].strip()
    return None


# ---------------------------------------------------------------------------
# Main Workflow
# ---------------------------------------------------------------------------


def print_summary(header: str, result: dict):
    """Print a formatted summary of test or lint results."""
    print(f"\n{'=' * 60}")
    print(f"  {header}")
    print(f"{'=' * 60}")
    for key, value in result.items():
        if isinstance(value, list):
            print(f"  {key}: {len(value)}")
            for item in value[:10]:
                if isinstance(item, dict):
                    print(f"    [{item['status']}] {item['text']}")
                else:
                    print(f"    {item}")
            if len(value) > 10:
                print(f"    ... and {len(value) - 10} more")
        else:
            print(f"  {key}: {value}")
    print(f"{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Fix a failing Slang RegTest: run, lint, and submit review."
    )
    parser.add_argument(
        "--db",
        required=False,
        default="",
        help='SecDB database path (e.g. "~{kerberos}!clean")',
    )
    parser.add_argument(
        "--test",
        required=False,
        default="",
        help='RegTest script name (e.g. "Test: Eq1D Brazil Foo")',
    )
    parser.add_argument(
        "--libs",
        nargs="*",
        default=[],
        help='Library scripts the test depends on (e.g. "_LIB Eq1D Brazil Foo")',
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help='Output directory for result files (default: workspace/tmp)',
    )
    parser.add_argument(
        "--run-only",
        action="store_true",
        help="Only run the test and report results (skip lint/review)",
    )
    parser.add_argument(
        "--lint-only",
        action="store_true",
        help="Only run lint on the test script",
    )
    parser.add_argument(
        "--read-source",
        action="store_true",
        help="Read and print the test script source, then exit",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="Submit a code review after successful test and lint",
    )
    parser.add_argument(
        "--subject",
        default="",
        help="Code review subject",
    )
    parser.add_argument(
        "--description",
        default="",
        help="Code review description",
    )
    parser.add_argument(
        "--testing-description",
        default="",
        help="Code review testing description",
    )
    # --- Task-based execution (zero Allow) ---
    parser.add_argument("--args-file", default=None, metavar="PATH",
                        help="JSON file with arguments (keys mirror CLI flags)")
    parser.add_argument("--output-json", default=None, metavar="PATH",
                        help="Write machine-readable JSON results to PATH (with sentinel)")
    args = parser.parse_args()

    # ---------- Load from args-file if provided ----------
    if args.args_file:
        with open(args.args_file, "r", encoding="utf-8-sig") as af:
            af_data = json.load(af)
        if af_data.get("db") and not args.db:
            args.db = af_data["db"]
        elif af_data.get("db"):
            args.db = af_data["db"]
        if af_data.get("test") and not args.test:
            args.test = af_data["test"]
        if af_data.get("libs") and not args.libs:
            args.libs = af_data["libs"]
        if af_data.get("out_dir") and not args.out_dir:
            args.out_dir = af_data["out_dir"]
        if af_data.get("run_only"):
            args.run_only = True
        if af_data.get("lint_only"):
            args.lint_only = True
        if af_data.get("read_source"):
            args.read_source = True
        if af_data.get("review"):
            args.review = True
        if af_data.get("subject") and not args.subject:
            args.subject = af_data["subject"]
        if af_data.get("description") and not args.description:
            args.description = af_data["description"]
        if af_data.get("testing_description") and not args.testing_description:
            args.testing_description = af_data["testing_description"]
        if af_data.get("output_json") and not args.output_json:
            args.output_json = af_data["output_json"]
        if af_data.get("run_id"):
            args.run_id = af_data["run_id"]

    run_id = getattr(args, "run_id", None) or ""

    if not args.db:
        parser.error("--db is required (either via CLI or --args-file)")
    if not args.test:
        parser.error("--test is required (either via CLI or --args-file)")

    # Resolve output directory
    _REPO_ROOT = os.path.normpath(os.path.join(SKILL_DIR, "..", "..", ".."))
    out_dir = args.out_dir
    if not out_dir:
        out_dir = os.path.normpath(os.path.join(_REPO_ROOT, "workspace", "tmp"))
    os.makedirs(out_dir, exist_ok=True)

    # ---------- Write running sentinel ----------
    json_path = args.output_json
    if not json_path:
        json_path = os.path.join(_REPO_ROOT, "workspace", "tmp",
                                  "slang_regtest_fix_results.json")
    os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump({"status": "running", "run_id": run_id,
                   "test": args.test}, jf)

    # Sanitize test name for filenames
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", args.test)

    # Helper to write final results JSON
    def _write_result(gate: str, extra: dict | None = None):
        result_data = {
            "status": "done",
            "run_id": run_id,
            "test": args.test,
            "libs": args.libs,
            "gate": gate,
        }
        if extra:
            result_data.update(extra)
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(result_data, jf, indent=2)

    # ----- Read source -----
    if args.read_source:
        print(f"Reading source: {args.test}")
        source = read_script_source(args.db, args.test)
        print(source)
        _write_result("PASS", {"mode": "read_source"})
        return 0

    # ----- Lint only -----
    if args.lint_only:
        print(f"Reading source: {args.test}")
        source = read_script_source(args.db, args.test)
        lint_path = os.path.join(out_dir, f"lint_{safe_name}.txt")
        lint_result = run_lint(args.db, args.test, source, lint_path)
        print_summary("LINT RESULTS", lint_result)
        gate = "PASS" if lint_result["clean"] else "FAIL"
        _write_result(gate, {"mode": "lint_only", "lint": lint_result})
        return 0 if lint_result["clean"] else 1

    # ----- Run test -----
    test_output_path = os.path.join(out_dir, f"regtest_{safe_name}.txt")
    test_result = run_regtest(args.db, args.test, test_output_path)
    print_summary("TEST RESULTS", test_result)

    if args.run_only:
        gate = "PASS" if test_result["success"] else "FAIL"
        _write_result(gate, {"mode": "run_only", "test_result": test_result})
        return 0 if test_result["success"] else 1

    if not test_result["success"]:
        print("TEST FAILED — review the output and fix the issues.")
        print(f"Output saved to: {test_output_path}")
        print("\nRead the test source with:")
        print(f'  python fix_regtest.py --db "{args.db}" --test "{args.test}" --read-source')
        for lib in args.libs:
            print(f'\nRead the library source with:')
            print(f'  python fix_regtest.py --db "{args.db}" --test "{lib}" --read-source')
        _write_result("FAIL", {"mode": "full", "step": "test", "test_result": test_result})
        return 1

    # ----- Lint -----
    print(f"\nReading source for lint: {args.test}")
    source = read_script_source(args.db, args.test)
    lint_path = os.path.join(out_dir, f"lint_{safe_name}.txt")
    lint_result = run_lint(args.db, args.test, source, lint_path)
    print_summary("LINT RESULTS", lint_result)

    if not lint_result["clean"]:
        print("LINT ISSUES FOUND — fix errors/warnings before submitting review.")
        print(f"Output saved to: {lint_path}")
        _write_result("FAIL", {"mode": "full", "step": "lint", "lint": lint_result})
        return 1

    # ----- Code review -----
    if args.review:
        all_scripts = [args.test] + args.libs
        subject = args.subject or f"Fix RegTest {args.test}"
        description = args.description or f"Fixed failing RegTest {args.test}"
        testing_desc = args.testing_description or (
            f"RegTest {args.test} passes all assertions. Lint clean."
        )
        review_path = os.path.join(out_dir, f"review_{safe_name}.txt")
        review_name = submit_review(
            args.db, all_scripts, subject, description, testing_desc, review_path
        )
        if review_name:
            print(f"\n*** REVIEW: {review_name} ***")
        else:
            print("\nWARNING: Could not extract review URL")
            _write_result("FAIL", {"mode": "full", "step": "review"})
            return 1

    print("\nAll steps completed successfully.")
    extra = {"mode": "full", "test_result": test_result, "lint": lint_result}
    if args.review and review_name:
        extra["review_name"] = review_name
    _write_result("PASS", extra)
    return 0


if __name__ == "__main__":
    sys.exit(main())
