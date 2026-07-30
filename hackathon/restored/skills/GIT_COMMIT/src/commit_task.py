"""GIT_COMMIT skill: auto-group changed files and commit by concern.

Analyzes git status, groups files by directory-based heuristics,
generates conventional commit messages, and executes commits + push.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DENIED_PREFIXES = (
    "workspace/docs/enghub/",
    "workspace/tmp/",
    "__pycache__/",
    ".git/",
)

DENIED_SUFFIXES = (".pyc",)

# Ordered list of (path prefix, group_key, default_scope, default_type)
# First match wins.  Order matters — more specific prefixes first.
GROUP_RULES: list[tuple[str, str, str | None, str]] = [
    ("src/volforecast/features/", "features", "features", "feat"),
    ("src/volforecast/models/", "models", "models", "feat"),
    ("src/volforecast/evaluation/", "evaluation", "eval", "feat"),
    ("src/volforecast/pipeline/", "pipeline", "pipeline", "feat"),
    ("src/volforecast/cli/", "cli", "cli", "feat"),
    ("src/volforecast/data/", "data", "data", "feat"),
    ("src/volforecast/utils/", "utils", "utils", "chore"),
    ("src/volforecast/visualization/", "viz", "viz", "feat"),
    ("src/volforecast/reporting/", "reporting", "reporting", "feat"),
    ("src/volforecast/scripts/", "scripts", "scripts", "feat"),
    ("src/volforecast/", "src", "src", "feat"),
    ("src/tests/", "tests", None, "test"),
    ("src/data/", "artifacts", None, "chore"),
    ("src/", "src", "src", "feat"),
    ("tests/", "tests", None, "test"),
    ("memory/research/", "research-mem", "memory", "docs"),
    ("memory/", "memory", "memory", "docs"),
    ("workspace/research/", "research", "research", "docs"),
    ("workspace/configs/", "config", "config", "chore"),
    ("workspace/docs/", "docs", None, "docs"),
    ("skills/", "skills", "skills", "feat"),
    ("policy/", "framework", "framework", "chore"),
    ("workflows/", "framework", "framework", "chore"),
    ("personas/", "framework", "framework", "chore"),
    (".github/", "ci", "ci", "chore"),
    ("data/", "data-files", "data", "chore"),
]

# Files at repo root get special handling
ROOT_FILE_RULES: dict[str, tuple[str, str | None, str]] = {
    "AGENTS.md": ("root-docs", None, "docs"),
    "README.md": ("root-docs", None, "docs"),
    "vol": ("root-infra", None, "chore"),
    "vol.cmd": ("root-infra", None, "chore"),
    "ml-vol-estimator.code-workspace": ("root-infra", None, "chore"),
}

# Commit ordering: source first, tests second, docs/config last
GROUP_ORDER = {
    "features": 0, "models": 1, "evaluation": 2, "pipeline": 3,
    "cli": 4, "data": 5, "utils": 6, "viz": 7, "reporting": 8,
    "scripts": 9, "src": 10,
    "tests": 20,
    "skills": 30,
    "memory": 40, "research-mem": 41, "research": 42,
    "docs": 43, "config": 44, "data-files": 45,
    "root-docs": 46, "root-infra": 47, "artifacts": 48,
    "framework": 50, "ci": 51,
    "misc": 99,
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FileEntry:
    """A file from git status with its status code and path."""
    status: str  # e.g. "M", "A", "??", "D", "R"
    path: str
    orig_path: str | None = None  # for renames


@dataclass
class CommitGroup:
    """A logical grouping of files to be committed together."""
    key: str
    scope: str | None
    commit_type: str
    files: list[FileEntry] = field(default_factory=list)
    message: str = ""


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def run_git(*args: str, cwd: str | None = None) -> tuple[int, str]:
    """Run a git command and return (exit_code, combined_output)."""
    cmd = ["git"] + list(args)
    # Prevent git from opening an editor (commit -m provides message directly)
    env = os.environ.copy()
    env["GIT_EDITOR"] = "true"
    env["GIT_MERGE_AUTOEDIT"] = "no"
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd,
        encoding="utf-8", errors="replace", env=env,
    )
    output = result.stdout
    if result.stderr:
        output += result.stderr
    return result.returncode, output.strip()


def get_status(cwd: str) -> list[FileEntry]:
    """Parse git status --porcelain=v1 into FileEntry list."""
    rc, output = run_git("status", "--porcelain", cwd=cwd)
    if rc != 0:
        print(f"ERROR: git status failed: {output}", file=sys.stderr)
        sys.exit(1)
    entries = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        # Porcelain v1: XY <path> or XY <path> -> <orig>
        xy = line[:2].strip()
        rest = line[3:]
        # Handle renames: "R  old -> new"
        if " -> " in rest:
            parts = rest.split(" -> ", 1)
            entries.append(FileEntry(status=xy, path=parts[1].strip(), orig_path=parts[0].strip()))
        else:
            entries.append(FileEntry(status=xy, path=rest.strip()))
    return entries


def get_current_branch(cwd: str) -> str:
    """Get the current branch name."""
    rc, output = run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd)
    if rc != 0:
        return "HEAD"
    return output.strip()


def get_diff_stat(files: list[str], cwd: str) -> dict[str, tuple[int, int]]:
    """Get insertions/deletions per file for tracked modified files."""
    if not files:
        return {}
    rc, output = run_git("diff", "--numstat", "--", *files, cwd=cwd)
    stats: dict[str, tuple[int, int]] = {}
    if rc != 0:
        return stats
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            ins = int(parts[0]) if parts[0] != "-" else 0
            dels = int(parts[1]) if parts[1] != "-" else 0
            stats[parts[2]] = (ins, dels)
    return stats


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def is_denied(path: str) -> bool:
    """Check if a file path should be excluded from staging."""
    normalized = path.replace("\\", "/")
    for prefix in DENIED_PREFIXES:
        if normalized.startswith(prefix) or f"/{prefix}" in normalized:
            return True
    for suffix in DENIED_SUFFIXES:
        if normalized.endswith(suffix):
            return True
    return False


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------

def classify_file(path: str) -> tuple[str, str | None, str]:
    """Classify a file path into (group_key, scope, commit_type)."""
    normalized = path.replace("\\", "/")
    # Check root file special rules first
    basename = PurePosixPath(normalized).name
    if "/" not in normalized and basename in ROOT_FILE_RULES:
        return ROOT_FILE_RULES[basename]
    for prefix, key, scope, ctype in GROUP_RULES:
        if normalized.startswith(prefix):
            return key, scope, ctype
    return "misc", None, "chore"


def group_files(entries: list[FileEntry]) -> list[CommitGroup]:
    """Group FileEntry list into CommitGroups by directory concern."""
    groups: dict[str, CommitGroup] = {}
    for entry in entries:
        key, scope, ctype = classify_file(entry.path)
        if key not in groups:
            groups[key] = CommitGroup(key=key, scope=scope, commit_type=ctype)
        groups[key].files.append(entry)
    # Sort by defined order
    sorted_groups = sorted(groups.values(), key=lambda g: GROUP_ORDER.get(g.key, 99))
    return sorted_groups


def apply_overrides(
    groups: list[CommitGroup],
    overrides: list[dict],
    all_entries: list[FileEntry],
) -> list[CommitGroup]:
    """Apply agent-specified override groups, removing those files from auto groups."""
    if not overrides:
        return groups

    override_files: set[str] = set()
    override_groups: list[CommitGroup] = []

    for ovr in overrides:
        files_list = ovr.get("files", [])
        message = ovr.get("message", "")
        override_files.update(files_list)
        # Build a CommitGroup from the override
        og = CommitGroup(key="override", scope=None, commit_type="feat")
        og.message = message
        for entry in all_entries:
            if entry.path in files_list:
                og.files.append(entry)
        if og.files:
            override_groups.append(og)

    # Remove overridden files from auto groups
    for group in groups:
        group.files = [f for f in group.files if f.path not in override_files]

    # Remove empty groups
    groups = [g for g in groups if g.files]

    # Prepend overrides (they come first)
    return override_groups + groups


# ---------------------------------------------------------------------------
# Message generation
# ---------------------------------------------------------------------------

def _stem_name(path: str) -> str:
    """Extract a human-readable name from a file path."""
    p = PurePosixPath(path.replace("\\", "/"))
    stem = p.stem
    # Strip leading underscores and common prefixes
    stem = stem.lstrip("_")
    # Convert snake_case/kebab-case to space-separated, collapse whitespace
    name = stem.replace("_", " ").replace("-", " ")
    return " ".join(name.split())


def _all_new(files: list[FileEntry]) -> bool:
    return all(f.status in ("A", "??") for f in files)


def _all_modified(files: list[FileEntry]) -> bool:
    return all(f.status in ("M", "MM") for f in files)


def _all_deleted(files: list[FileEntry]) -> bool:
    return all(f.status == "D" for f in files)


def _pick_type(group: CommitGroup) -> str:
    """Determine commit type from file statuses and group defaults."""
    if group.key == "tests":
        return "test"
    if _all_deleted(group.files):
        return "chore"
    if _all_new(group.files):
        if group.commit_type == "docs":
            return "docs"
        return "feat"
    if _all_modified(group.files):
        if group.commit_type in ("docs", "chore"):
            return group.commit_type
        return "fix"
    # Mixed new + modified
    if group.commit_type == "docs":
        return "docs"
    return "feat"


def _describe_files(files: list[FileEntry], group_key: str) -> str:
    """Generate a descriptive subject from file names and statuses."""
    names = [_stem_name(f.path) for f in files]

    if _all_deleted(files):
        if len(names) == 1:
            return f"remove {names[0]}"
        if len(names) <= 3:
            return "remove " + ", ".join(names)
        return f"remove {len(names)} unused files"

    if len(names) == 1:
        verb = "add" if files[0].status in ("A", "??") else "update"
        return f"{verb} {names[0]}"

    if len(names) == 2:
        if _all_new(files):
            return f"add {names[0]} and {names[1]}"
        if _all_modified(files):
            return f"update {names[0]} and {names[1]}"
        return f"update {names[0]} and add {names[1]}"

    if len(names) <= 4:
        # List key items
        new_names = [n for f, n in zip(files, names) if f.status in ("A", "??")]
        mod_names = [n for f, n in zip(files, names) if f.status in ("M", "MM")]
        if new_names and not mod_names:
            return "add " + ", ".join(new_names[:3])
        if mod_names and not new_names:
            return "update " + ", ".join(mod_names[:3])
        # Mixed
        parts = []
        if new_names:
            parts.append("add " + ", ".join(new_names[:2]))
        if mod_names:
            parts.append("update " + ", ".join(mod_names[:2]))
        return " and ".join(parts)

    # 5+ files — use first 2-3 most salient names with summary
    new_files = [f for f in files if f.status in ("A", "??")]
    mod_files = [f for f in files if f.status in ("M", "MM")]
    del_files = [f for f in files if f.status == "D"]

    # Pick the most recognizable names (new files first, then modified)
    salient = new_files[:2] or mod_files[:2]
    salient_names = [_stem_name(f.path) for f in salient]

    if new_files and mod_files:
        return f"add {salient_names[0]} and update {len(mod_files)} {group_key} files"
    if new_files and not mod_files:
        if len(new_files) <= 3:
            return "add " + ", ".join(_stem_name(f.path) for f in new_files)
        return f"add {salient_names[0]} and {len(new_files) - 1} more {group_key} files"
    if del_files and mod_files:
        return f"update {len(mod_files)} and remove {len(del_files)} {group_key} files"
    # All modified
    return f"update {', '.join(salient_names)} and {len(files) - len(salient)} more"


def generate_message(group: CommitGroup) -> str:
    """Generate a conventional commit message for a group."""
    # If override provided a message, use it directly
    if group.message:
        return group.message

    ctype = _pick_type(group)
    description = _describe_files(group.files, group.key)
    scope = group.scope

    if scope:
        msg = f"{ctype}({scope}): {description}"
    else:
        msg = f"{ctype}: {description}"

    # Enforce 72-char limit by truncating description if needed
    if len(msg) > 72:
        # Try without listing all items
        n = len(group.files)
        short_desc = f"update {n} files" if not _all_new(group.files) else f"add {n} files"
        if scope:
            msg = f"{ctype}({scope}): {short_desc}"
        else:
            msg = f"{ctype}: {short_desc}"

    return msg


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def execute_commits(
    groups: list[CommitGroup],
    cwd: str,
    push: bool,
    branch: str | None,
    dry_run: bool,
) -> list[str]:
    """Execute git add + commit for each group, then push. Returns log lines."""
    log: list[str] = []
    total = len(groups)

    if dry_run:
        log.append(f"=== GIT_COMMIT: {total} commits planned (DRY RUN) ===")
    else:
        log.append(f"=== GIT_COMMIT: {total} commits planned ===")
    log.append("")

    for i, group in enumerate(groups, 1):
        msg = generate_message(group)
        group.message = msg

        # Display plan
        log.append(f"[{i}/{total}] {msg}")
        for f in group.files:
            status_label = {
                "A": "new", "??": "new", "M": "modified", "MM": "modified",
                "D": "deleted", "R": "renamed",
            }.get(f.status, f.status)
            log.append(f"  -> {f.path} ({status_label})")
        log.append("")

        if dry_run:
            continue

        # Stage files
        paths = [f.path for f in group.files if f.status != "D"]
        deleted_paths = [f.path for f in group.files if f.status == "D"]

        if paths:
            rc, out = run_git("add", "--", *paths, cwd=cwd)
            if rc != 0:
                log.append(f"  ERROR staging files: {out}")
                return log

        if deleted_paths:
            rc, out = run_git("rm", "--cached", "--", *deleted_paths, cwd=cwd)
            if rc != 0:
                # Try git add for deleted files (handles already-tracked deletions)
                rc, out = run_git("add", "--", *deleted_paths, cwd=cwd)
                if rc != 0:
                    log.append(f"  ERROR staging deleted files: {out}")
                    return log

        # Commit
        rc, out = run_git("commit", "-m", msg, cwd=cwd)
        if rc != 0:
            log.append(f"  ERROR committing: {out}")
            return log

        # Extract short SHA
        sha_match = re.search(r"\[[\w/]+ ([a-f0-9]+)\]", out)
        sha = sha_match.group(1) if sha_match else "?"
        log.append(f"[{i}/{total}] committed ({sha})")

    if dry_run:
        log.append("=== DRY RUN complete — no changes made ===")
        return log

    # Push
    if push:
        log.append("")
        actual_branch = branch or get_current_branch(cwd)
        if actual_branch == "master":
            log.append("SKIPPED push — refusing to push directly to master")
        else:
            log.append(f"Push -> origin/{actual_branch}")
            rc, out = run_git("push", "origin", actual_branch, cwd=cwd)
            if rc != 0:
                # Try force-with-lease (for rebased branches)
                log.append(f"  Push failed, trying --force-with-lease: {out}")
                rc, out = run_git("push", "--force-with-lease", "origin", actual_branch, cwd=cwd)
                if rc != 0:
                    log.append(f"  ERROR pushing: {out}")
                    return log
            log.append("Push complete")

    # Summary
    log.append("")
    total_files = sum(len(g.files) for g in groups)
    branch_name = branch or get_current_branch(cwd)
    if push and branch_name != "master":
        log.append(f"Done: {total} commits, {total_files} files, pushed to {branch_name}")
    else:
        log.append(f"Done: {total} commits, {total_files} files")

    return log


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Parse --args-file from CLI
    args_file = None
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--args-file" and i < len(sys.argv) - 1:
            args_file = sys.argv[i + 1]
            break

    if not args_file:
        print("ERROR: --args-file is required", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args_file):
        print(f"ERROR: args file not found: {args_file}", file=sys.stderr)
        sys.exit(1)

    with open(args_file, encoding="utf-8") as f:
        args = json.load(f)

    push = args.get("push", True)
    branch = args.get("branch")
    dry_run = args.get("dry_run", False)
    overrides = args.get("overrides", [])
    out_file = args.get("out_file")

    # Determine repo root (walk up from this script's location)
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    cwd = str(repo_root)

    # Resolve out_file relative to repo root
    if out_file and not os.path.isabs(out_file):
        out_file = str(repo_root / out_file)

    # Get status
    entries = get_status(cwd)
    if not entries:
        msg = "Nothing to commit — working tree clean"
        print(msg)
        if out_file:
            Path(out_file).parent.mkdir(parents=True, exist_ok=True)
            Path(out_file).write_text(msg, encoding="utf-8")
        return

    # Filter denied paths
    entries = [e for e in entries if not is_denied(e.path)]
    if not entries:
        msg = "Nothing to commit — all changed files are on the deny list"
        print(msg)
        if out_file:
            Path(out_file).parent.mkdir(parents=True, exist_ok=True)
            Path(out_file).write_text(msg, encoding="utf-8")
        return

    # Group
    groups = group_files(entries)

    # Apply overrides
    groups = apply_overrides(groups, overrides, entries)

    if not groups:
        msg = "Nothing to commit after grouping"
        print(msg)
        if out_file:
            Path(out_file).parent.mkdir(parents=True, exist_ok=True)
            Path(out_file).write_text(msg, encoding="utf-8")
        return

    # Generate messages
    for group in groups:
        if not group.message:
            group.message = generate_message(group)

    # Execute
    log = execute_commits(groups, cwd, push, branch, dry_run)

    # Output
    output_text = "\n".join(log)
    print(output_text)

    if out_file:
        Path(out_file).parent.mkdir(parents=True, exist_ok=True)
        Path(out_file).write_text(output_text, encoding="utf-8")


if __name__ == "__main__":
    main()
