"""CVS read-only operations: rlog, rdiff, rannot, rls, checkout-to-stdout.

Usage:
    python cvs.py rlog slang/lib/misc/SpgRebalanceFns.s
    python cvs.py rlog slang/lib/misc/SpgRebalanceFns.s --limit 5
    python cvs.py rdiff slang/lib/misc/SpgRebalanceFns.s -r 1.456 -r 1.457
    python cvs.py rdiff slang/lib/misc/SpgRebalanceFns.s --head-vs-prev
    python cvs.py rannot slang/lib/misc/SpgRebalanceFns.s
    python cvs.py rannot slang/lib/misc/SpgRebalanceFns.s -r 1.457
    python cvs.py rls slang/lib/misc/ --pattern rebalance
    python cvs.py co slang/lib/misc/SpgRebalanceFns.s -r 1.456
    python cvs.py --args-file workspace/tmp/cvs_args.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

WORKSPACE_TMP = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, os.pardir, "workspace", "tmp"
)


def run_cvs(args: list[str], timeout: int = 60) -> str:
    """Run a cvs command and return combined stdout+stderr."""
    result = subprocess.run(
        ["cvs"] + args,
        capture_output=True, text=True, timeout=timeout
    )
    output = result.stdout
    if result.stderr:
        output += result.stderr
    return output


def cmd_rlog(path: str, limit: int | None = None, local: bool = True) -> str:
    """Get revision log for a CVS path."""
    args = ["rlog"]
    if local:
        args.append("-l")
    args.append(path)
    output = run_cvs(args)
    if limit:
        lines = output.splitlines()
        revisions_seen = 0
        cut_lines = []
        for line in lines:
            cut_lines.append(line)
            if line.startswith("revision "):
                revisions_seen += 1
                if revisions_seen > limit:
                    break
        output = "\n".join(cut_lines)
    return output


def cmd_rdiff(path: str, rev1: str, rev2: str) -> str:
    """Unified diff between two revisions."""
    return run_cvs(["rdiff", "-u", "-r", rev1, "-r", rev2, path])


def cmd_rdiff_head_vs_prev(path: str) -> str:
    """Diff HEAD vs previous revision (auto-detects revisions)."""
    log_output = run_cvs(["rlog", "-l", path])
    revisions = re.findall(r"^revision ([\d.]+)", log_output, re.MULTILINE)
    if len(revisions) < 2:
        return f"ERROR: fewer than 2 revisions found for {path}"
    head, prev = revisions[0], revisions[1]
    diff = run_cvs(["rdiff", "-u", "-r", prev, "-r", head, path])
    return f"# Diff {prev} → {head}\n\n{diff}"


def cmd_rannot(path: str, rev: str | None = None) -> str:
    """Annotate (blame) a file."""
    args = ["rannot"]
    if rev:
        args += ["-r", rev]
    args.append(path)
    return run_cvs(args)


def cmd_rls(path: str, pattern: str | None = None) -> str:
    """List directory contents in CVS."""
    output = run_cvs(["rls", path])
    if pattern:
        lines = [l for l in output.splitlines() if re.search(pattern, l, re.IGNORECASE)]
        output = "\n".join(lines)
    return output


def cmd_co(path: str, rev: str | None = None) -> str:
    """Checkout a file to stdout (no working copy)."""
    args = ["co", "-p"]
    if rev:
        args += ["-r", rev]
    args.append(path)
    result = subprocess.run(
        ["cvs"] + args,
        capture_output=True, text=True, timeout=60
    )
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description="CVS read-only operations")
    parser.add_argument("--args-file", help="JSON args file (overrides CLI)")
    parser.add_argument("command", nargs="?", choices=["rlog", "rdiff", "rannot", "rls", "co"])
    parser.add_argument("path", nargs="?", help="CVS module path")
    parser.add_argument("-r", "--rev", action="append", help="Revision(s)")
    parser.add_argument("--limit", type=int, help="Limit revisions (rlog)")
    parser.add_argument("--head-vs-prev", action="store_true", help="Diff HEAD vs prev (rdiff)")
    parser.add_argument("--pattern", help="Filter pattern (rls)")
    parser.add_argument("--out-file", help="Write output to file")
    args = parser.parse_args()

    # Load from args-file if provided
    if args.args_file:
        with open(args.args_file) as f:
            jargs = json.load(f)
        command = jargs.get("command", args.command)
        path = jargs.get("path", args.path)
        revs = jargs.get("revisions", args.rev or [])
        limit = jargs.get("limit", args.limit)
        head_vs_prev = jargs.get("head_vs_prev", args.head_vs_prev)
        pattern = jargs.get("pattern", args.pattern)
        out_file = jargs.get("out_file", args.out_file)
    else:
        command = args.command
        path = args.path
        revs = args.rev or []
        limit = args.limit
        head_vs_prev = args.head_vs_prev
        pattern = args.pattern
        out_file = args.out_file

    if not command:
        parser.error("command is required")
    if not path:
        parser.error("path is required")

    # Dispatch
    if command == "rlog":
        output = cmd_rlog(path, limit=limit)
    elif command == "rdiff":
        if head_vs_prev:
            output = cmd_rdiff_head_vs_prev(path)
        elif len(revs) >= 2:
            output = cmd_rdiff(path, revs[0], revs[1])
        else:
            output = "ERROR: rdiff requires two -r revisions or --head-vs-prev"
    elif command == "rannot":
        rev = revs[0] if revs else None
        output = cmd_rannot(path, rev=rev)
    elif command == "rls":
        output = cmd_rls(path, pattern=pattern)
    elif command == "co":
        rev = revs[0] if revs else None
        output = cmd_co(path, rev=rev)
    else:
        output = f"ERROR: unknown command {command}"

    # Write output
    if out_file:
        os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Output written to {out_file}")
    else:
        print(output)


if __name__ == "__main__":
    main()
