"""Slang Copilot docs setup: clone/update the slang-copilot-code repo.

Usage:
    python copilot_setup.py clone
    python copilot_setup.py update
    python copilot_setup.py status
    python copilot_setup.py --args-file workspace/tmp/slang_copilot_args.json
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

REPO_URL = "https://gitlab.aws.site.gs.com/eq-tech/booking-controls/slang-copilot-code.git"

WORKSPACE_ROOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, os.pardir
)
DOCS_DIR = os.path.join(WORKSPACE_ROOT, "workspace", "docs", "slang")


def git(*args: str, cwd: str | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a git command."""
    return subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, cwd=cwd, timeout=timeout
    )


def cmd_clone() -> str:
    """Clone slang-copilot-code and copy .github contents to workspace/docs/slang/."""
    import tempfile
    tmp_dir = tempfile.mkdtemp(prefix="slang-copilot-")
    try:
        result = git("clone", "--depth=1", "--single-branch", REPO_URL, tmp_dir)
        if result.returncode != 0:
            return f"ERROR: git clone failed: {result.stderr.strip()}"

        # Copy .github contents to docs dir
        src = os.path.join(tmp_dir, ".github")
        if not os.path.isdir(src):
            # Fallback: copy entire repo content
            src = tmp_dir

        os.makedirs(DOCS_DIR, exist_ok=True)

        # Clear existing contents
        for item in os.listdir(DOCS_DIR):
            item_path = os.path.join(DOCS_DIR, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

        # Copy new contents
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(DOCS_DIR, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)

        # Count files
        count = sum(len(files) for _, _, files in os.walk(DOCS_DIR))
        return f"Cloned slang-copilot-code → {DOCS_DIR} ({count} files)"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def cmd_update() -> str:
    """Re-clone to update (shallow clone, no local state to fetch into)."""
    return cmd_clone()


def cmd_status() -> str:
    """Check if docs exist and report file count."""
    if not os.path.isdir(DOCS_DIR):
        return "NOT INSTALLED: workspace/docs/slang/ does not exist. Run 'clone'."
    count = sum(len(files) for _, _, files in os.walk(DOCS_DIR))
    dirs = [d for d in os.listdir(DOCS_DIR) if os.path.isdir(os.path.join(DOCS_DIR, d))]
    return f"INSTALLED: {DOCS_DIR}\n  Files: {count}\n  Dirs: {', '.join(sorted(dirs))}"


def main():
    parser = argparse.ArgumentParser(description="Slang Copilot docs setup")
    parser.add_argument("--args-file", help="JSON args file (overrides CLI)")
    parser.add_argument("command", nargs="?", choices=["clone", "update", "status"])
    parser.add_argument("--out-file", help="Write output to file")
    args = parser.parse_args()

    if args.args_file:
        with open(args.args_file) as f:
            jargs = json.load(f)
        command = jargs.get("command", args.command)
        out_file = jargs.get("out_file", args.out_file)
    else:
        command = args.command
        out_file = args.out_file

    if not command:
        parser.error("command is required (clone, update, status)")

    if command == "clone":
        output = cmd_clone()
    elif command == "update":
        output = cmd_update()
    elif command == "status":
        output = cmd_status()
    else:
        output = f"ERROR: unknown command {command}"

    if out_file:
        os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Output written to {out_file}")
    else:
        print(output)


if __name__ == "__main__":
    main()
