"""EngHub documentation management: clone, update, list, search repos.

Usage:
    python enghub.py clone-all
    python enghub.py clone-one sdlc-global/cicd-platform-docs
    python enghub.py update-all
    python enghub.py update-one cicd-platform-docs
    python enghub.py list
    python enghub.py search --pattern "pricing"
    python enghub.py --args-file workspace/tmp/enghub_args.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

BASE_URL = "https://gitlab.aws.site.gs.com"

WORKSPACE_ROOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, os.pardir
)
ENGHUB_DIR = os.path.join(WORKSPACE_ROOT, "workspace", "knowledge", "enghub")

# Default repos to clone
DEFAULT_REPOS = [
    "sdlc-global/cicd-platform-docs",
    "developer-experience/enghub-happy-paths/set-up-infrastructure",
    "developer-experience/enghub-happy-paths/working-with-python",
    "developer-experience/enghub-happy-paths/enghub-solutions",
    "developer-experience/well-architected/well-architected-platform-docs",
    "iam/iam-docs",
    "developer-experience/enghub-happy-paths/application-entitlement-management",
    "developer-experience/enghub-happy-paths/demise-webid",
    "derun/sky/cloud-platform-docs",
    "infra/container-runtime/fi-docs",
    "foundational-infra/dynamic-computing/dc-enghub",
    "foundational-infra/computing-and-development-platform-engineering/converge-docs",
    "foundational-infra/inventory-management/inventory-central-enghub",
    "derun/unixeng/linux-image-enghub-docs",
    "infra/luma/luma-enghub",
    "derun/dev-desktop/dev-desktop-docs",
]


def git(*args: str, cwd: str | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a git command."""
    return subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, cwd=cwd, timeout=timeout
    )


def clone_or_update(gitlab_path: str, target_name: str | None = None) -> str:
    """Clone or update a single repo. Returns status message."""
    repo_name = target_name or os.path.basename(gitlab_path)
    target = os.path.join(ENGHUB_DIR, repo_name)

    os.makedirs(ENGHUB_DIR, exist_ok=True)

    if os.path.isdir(os.path.join(target, ".git")):
        result = git("fetch", "--depth=1", "--quiet", cwd=target)
        if result.returncode != 0:
            return f"FAIL update {repo_name}: {result.stderr.strip()}"
        result = git("reset", "--hard", "origin/HEAD", "--quiet", cwd=target)
        if result.returncode != 0:
            return f"FAIL reset {repo_name}: {result.stderr.strip()}"
        return f"Updated {repo_name}"
    else:
        url = f"{BASE_URL}/{gitlab_path}.git"
        result = git("clone", "--depth=1", "--single-branch", url, target)
        if result.returncode != 0:
            return f"FAIL clone {repo_name}: {result.stderr.strip()}"
        return f"Cloned {repo_name}"


def cmd_clone_all() -> str:
    """Clone or update all default repos."""
    results = []
    for repo in DEFAULT_REPOS:
        results.append(clone_or_update(repo))
    return "\n".join(results)


def cmd_clone_one(gitlab_path: str, target_name: str | None = None) -> str:
    """Clone or update a single repo."""
    return clone_or_update(gitlab_path, target_name)


def cmd_update_all() -> str:
    """Update all repos that exist locally."""
    if not os.path.isdir(ENGHUB_DIR):
        return "No enghub directory found. Run clone-all first."
    results = []
    for entry in sorted(os.listdir(ENGHUB_DIR)):
        target = os.path.join(ENGHUB_DIR, entry)
        if os.path.isdir(os.path.join(target, ".git")):
            result = git("fetch", "--depth=1", "--quiet", cwd=target)
            if result.returncode == 0:
                git("reset", "--hard", "origin/HEAD", "--quiet", cwd=target)
                results.append(f"Updated {entry}")
            else:
                results.append(f"FAIL {entry}: {result.stderr.strip()}")
    return "\n".join(results) if results else "No repos found to update."


def cmd_update_one(repo_name: str) -> str:
    """Update a specific repo by directory name."""
    target = os.path.join(ENGHUB_DIR, repo_name)
    if not os.path.isdir(os.path.join(target, ".git")):
        return f"ERROR: {repo_name} not found in {ENGHUB_DIR}"
    result = git("fetch", "--depth=1", "--quiet", cwd=target)
    if result.returncode != 0:
        return f"FAIL fetch: {result.stderr.strip()}"
    git("reset", "--hard", "origin/HEAD", "--quiet", cwd=target)
    return f"Updated {repo_name}"


def cmd_list() -> str:
    """List all cloned repos."""
    if not os.path.isdir(ENGHUB_DIR):
        return "No enghub directory found."
    repos = sorted(
        e for e in os.listdir(ENGHUB_DIR)
        if os.path.isdir(os.path.join(ENGHUB_DIR, e, ".git"))
    )
    return "\n".join(repos) if repos else "No repos cloned."


def cmd_search(pattern: str) -> str:
    """Search across all cloned repos for a pattern in .md files."""
    if not os.path.isdir(ENGHUB_DIR):
        return "No enghub directory found."
    matches = []
    for root, _, files in os.walk(ENGHUB_DIR):
        for fname in files:
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            rel = os.path.relpath(fpath, ENGHUB_DIR)
                            matches.append(f"{rel}:{i}: {line.rstrip()}")
            except OSError:
                continue
    return "\n".join(matches[:200]) if matches else f"No matches for '{pattern}'"


def main():
    parser = argparse.ArgumentParser(description="EngHub documentation management")
    parser.add_argument("--args-file", help="JSON args file (overrides CLI)")
    parser.add_argument("command", nargs="?",
                        choices=["clone-all", "clone-one", "update-all", "update-one", "list", "search"])
    parser.add_argument("path", nargs="?", help="GitLab path or repo name")
    parser.add_argument("--target", help="Target directory name (clone-one)")
    parser.add_argument("--pattern", help="Search pattern (search)")
    parser.add_argument("--out-file", help="Write output to file")
    args = parser.parse_args()

    if args.args_file:
        with open(args.args_file) as f:
            jargs = json.load(f)
        command = jargs.get("command", args.command)
        path = jargs.get("path", args.path)
        target = jargs.get("target", args.target)
        pattern = jargs.get("pattern", args.pattern)
        out_file = jargs.get("out_file", args.out_file)
    else:
        command = args.command
        path = args.path
        target = args.target
        pattern = args.pattern
        out_file = args.out_file

    if not command:
        parser.error("command is required")

    if command == "clone-all":
        output = cmd_clone_all()
    elif command == "clone-one":
        if not path:
            output = "ERROR: path (gitlab path) required for clone-one"
        else:
            output = cmd_clone_one(path, target)
    elif command == "update-all":
        output = cmd_update_all()
    elif command == "update-one":
        if not path:
            output = "ERROR: path (repo name) required for update-one"
        else:
            output = cmd_update_one(path)
    elif command == "list":
        output = cmd_list()
    elif command == "search":
        if not pattern:
            output = "ERROR: --pattern required for search"
        else:
            output = cmd_search(pattern)
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
