"""Interactive config picker for `vol run` (no --config)."""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path


def _relative_age(mtime: float) -> str:
    """Human-readable relative time string from mtime to now."""
    delta = time.time() - mtime
    if delta < 60:
        return "just now"
    if delta < 3600:
        m = int(delta // 60)
        return f"{m}m ago"
    if delta < 86400:
        h = int(delta // 3600)
        return f"{h}h ago"
    if delta < 604800:
        d = int(delta // 86400)
        return f"{d}d ago"
    w = int(delta // 604800)
    return f"{w}w ago"


def _find_project_root() -> Path:
    """Return the project root (three levels above this file)."""
    return Path(__file__).resolve().parents[3]


def _find_configs_dir() -> Path:
    """Resolve workspace/configs/ relative to the project root."""
    root = _find_project_root()
    configs_dir = root / "workspace" / "configs"
    if not configs_dir.is_dir():
        raise FileNotFoundError(f"Configs directory not found: {configs_dir}")
    return configs_dir


def _load_completed_stems(project_root: Path) -> set[str]:
    """Load config stems that have status=completed in trials.yaml."""
    trials_path = project_root / "workspace" / "research" / "trials.yaml"
    if not trials_path.exists():
        return set()
    try:
        import yaml

        with open(trials_path) as f:
            data = yaml.safe_load(f)
        stems: set[str] = set()
        for trial in data.get("trials", []):
            if (trial.get("status") or "").lower() == "completed":
                config = trial.get("config", "")
                if config:
                    stems.add(Path(config).stem)
        return stems
    except Exception:
        return set()


def _has_completed_run(config_path: Path, project_root: Path | None = None) -> bool:
    """Check if a config has been run (via trials.yaml or metrics.json on disk)."""
    if project_root is None:
        project_root = _find_project_root()
    # Check trials.yaml first (canonical source of truth)
    completed_stems = _load_completed_stems(project_root)
    if config_path.stem in completed_stems:
        return True
    # Fallback: check for metrics.json in output directory
    output_dir = "workspace/tmp/results"
    try:
        lines = config_path.read_text().splitlines()[:50]
    except OSError:
        return False
    for line in lines:
        m = re.search(r'^output_dir:\s*(.+)', line)
        if m:
            output_dir = m.group(1).strip().strip('"').strip("'")
            break
    resolved = project_root / output_dir
    return (resolved / "metrics.json").is_file()


def _preview_callback(configs: list[Path]):
    """Return a preview function for TerminalMenu."""

    def preview(entry: str) -> str:
        # entry is the display string; extract filename (before the padding)
        # If entry starts with tick prefix, filename is the second token
        parts = entry.split()
        name = parts[1] if parts and parts[0] == "\u2713" else parts[0]
        for cfg in configs:
            if cfg.name == name:
                try:
                    lines = cfg.read_text().splitlines()[:12]
                    return "\n".join(lines)
                except OSError:
                    return "(cannot read file)"
        return ""

    return preview


def pick_config(
    configs_dir: Path | None = None,
    limit: int = 20,
) -> Path | None:
    """Show interactive picker and return selected config path, or None if cancelled.

    Args:
        configs_dir: Directory to scan for YAML configs. Defaults to workspace/configs/.
        limit: Maximum number of configs to show (most recent first).

    Returns:
        Path to selected config, or None if user pressed Esc/q.
    """
    if not sys.stdin.isatty():
        from volforecast.cli.console import console

        console.print(
            "[red]Error:[/red] No interactive terminal available. "
            "Use [bold]--config <path>[/bold] to specify a config file."
        )
        sys.exit(1)

    if configs_dir is None:
        configs_dir = _find_configs_dir()

    # Gather YAML files sorted by modification time (newest first)
    yaml_files: list[tuple[Path, float]] = []
    for f in configs_dir.iterdir():
        if f.suffix in (".yaml", ".yml") and f.is_file():
            yaml_files.append((f, f.stat().st_mtime))

    if not yaml_files:
        from volforecast.cli.console import console

        console.print(f"[yellow]No YAML configs found in[/yellow] {configs_dir}")
        return None

    yaml_files.sort(key=lambda x: x[1], reverse=True)
    yaml_files = yaml_files[:limit]

    # Build display entries: filename padded + right-aligned age
    project_root = _find_project_root()
    completed_stems = _load_completed_stems(project_root)
    max_name_len = max(len(f.name) for f, _ in yaml_files)
    entries: list[str] = []
    for f, mt in yaml_files:
        age = _relative_age(mt)
        padding = " " * (max_name_len - len(f.name) + 4)
        prefix = "✓ " if f.stem in completed_stems else "  "
        entries.append(f"{prefix}{f.name}{padding}{age}")

    configs = [f for f, _ in yaml_files]

    try:
        from simple_term_menu import TerminalMenu
    except ImportError:
        from volforecast.cli.console import console

        console.print(
            "[red]Error:[/red] simple-term-menu not installed. "
            "Run [bold]./vol sync[/bold] to install dependencies."
        )
        sys.exit(1)

    menu = TerminalMenu(
        entries,
        title="\n  ⚡ Select experiment config\n",
        menu_cursor="  ❯ ",
        menu_cursor_style=("fg_cyan", "bold"),
        menu_highlight_style=("fg_cyan", "bold"),
        cycle_cursor=True,
        clear_screen=False,
        preview_command=_preview_callback(configs),
        preview_title="── Config Preview ──",
        preview_size=0.4,
        status_bar="↑/↓ navigate │ Enter select │ / search │ Esc cancel",
        status_bar_style=("fg_gray",),
    )

    idx = menu.show()

    if idx is None:
        return None

    selected = configs[idx]

    from volforecast.cli.console import console

    console.print(f"\n  [bold cyan]▶[/bold cyan] Running: [bold]{selected.name}[/bold]\n")
    return selected
