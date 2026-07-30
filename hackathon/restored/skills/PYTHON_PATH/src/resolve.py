"""Resolve the Python interpreter path (cross-platform).

Checks workspace/config/user.json for python_path.
Falls back to platform-specific scanning if not configured.

Usage: python resolve.py [--workspace-root PATH]
"""

import json
import shutil
import sys
from pathlib import Path


def _default_workspace_root() -> Path:
    """Walk up from this script to find the repo root."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "AGENTS.md").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return Path.cwd()


def _find_python_linux() -> str | None:
    """Find Python on Linux: check project venv, then system."""
    # 1. Project venv
    root = _default_workspace_root()
    venv_python = root / "src" / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)

    # 2. System python3.11, python3, python
    for name in ("python3.11", "python3", "python"):
        path = shutil.which(name)
        if path:
            return path

    return None


def _find_python_windows() -> str | None:
    """Find Python on Windows: scan H:\\venv* directories."""
    import glob

    candidates = sorted(
        glob.glob(r"H:\venv*\Scripts\python.exe"), reverse=True
    )
    if candidates:
        return candidates[0]

    # Fallback: check PATH
    path = shutil.which("python")
    if path:
        return path

    return None


def resolve(workspace_root: Path | None = None) -> str:
    """Resolve python_path from config or platform scanning.

    Returns the resolved path string. Updates user.json if auto-detected.
    """
    if workspace_root is None:
        workspace_root = _default_workspace_root()

    config_path = workspace_root / "workspace" / "config" / "user.json"
    resolved = None

    # 1. Try user.json
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            if cfg.get("python_path"):
                resolved = cfg["python_path"]
        except (json.JSONDecodeError, OSError):
            print(f"WARN: Failed to parse {config_path} - using fallback",
                  file=sys.stderr)

    # 2. Validate
    if resolved and Path(resolved).exists():
        return resolved

    if resolved:
        print(f"WARN: Configured python not found at {resolved} - scanning...",
              file=sys.stderr)

    # 3. Auto-detect
    if sys.platform == "win32":
        found = _find_python_windows()
    else:
        found = _find_python_linux()

    if not found:
        print("ERROR: No Python installation found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found Python at: {found}", file=sys.stderr)

    # 4. Update user.json
    _update_config(config_path, workspace_root, found)

    return found


def _update_config(config_path: Path, workspace_root: Path, python_path: str) -> None:
    """Write discovered python_path back to user.json."""
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            cfg["python_path"] = python_path
            config_path.write_text(
                json.dumps(cfg, indent=4) + "\n", encoding="utf-8"
            )
            print(f"Updated {config_path} with python_path = {python_path}",
                  file=sys.stderr)
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARN: Could not update config - {e}", file=sys.stderr)
    else:
        # Try creating from template
        template_path = workspace_root / "workspace" / "config" / "user.json.template"
        try:
            if template_path.exists():
                cfg = json.loads(template_path.read_text(encoding="utf-8"))
            else:
                cfg = {}
            cfg["python_path"] = python_path
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                json.dumps(cfg, indent=4) + "\n", encoding="utf-8"
            )
            print(f"Created {config_path} with python_path = {python_path}",
                  file=sys.stderr)
        except OSError as e:
            print(f"WARN: Could not create config - {e}", file=sys.stderr)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Resolve Python interpreter path")
    parser.add_argument("--workspace-root", type=Path, default=None,
                        help="Path to repo root (auto-detected if omitted)")
    args = parser.parse_args()

    result = resolve(args.workspace_root)
    print(result)


if __name__ == "__main__":
    main()
