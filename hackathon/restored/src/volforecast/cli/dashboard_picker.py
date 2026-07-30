"""Interactive dashboard picker for `vol dashboard`.

Lists completed trials that have a tournament_dashboard.html artifact,
sorted by last-updated. Copies the selected dashboard to workspace/tmp/dashboards/
and opens it in the VS Code editor for easy download.
"""

from __future__ import annotations

import json
import shutil
import subprocess
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


def _find_models_dir() -> Path:
    """Resolve src/data/models/ relative to the project root."""
    root = _find_project_root()
    models_dir = root / "src" / "data" / "models"
    if not models_dir.is_dir():
        raise FileNotFoundError(f"Models directory not found: {models_dir}")
    return models_dir


def _load_trial_metadata(project_root: Path) -> dict[str, dict]:
    """Load trial metadata from trials.yaml, keyed by config stem or trial dir name."""
    trials_path = project_root / "workspace" / "research" / "trials.yaml"
    if not trials_path.exists():
        return {}
    try:
        import yaml

        with open(trials_path) as f:
            data = yaml.safe_load(f)
        meta: dict[str, dict] = {}
        for trial in data.get("trials", []):
            trial_id = trial.get("id", "")
            config = trial.get("config", "")
            status = (trial.get("status") or "").lower()
            # Key by config stem (matches directory naming convention)
            if config:
                meta[Path(config).stem] = trial
            # Also key by trial id (e.g. "trial-001")
            if trial_id:
                meta[trial_id] = trial
            # Key by output dir name pattern (trial_NNN_name)
            # Config stems like "trial_036_CHAMPION" map to dirs like "trial_036_lgbm_0dte_tenor_matched"
            # So we also store by trial id variant with underscore
            if trial_id:
                meta[trial_id.replace("-", "_")] = trial
        return meta
    except Exception:
        return {}


def _metrics_preview(metrics_path: Path) -> str:
    """Format a short preview from metrics.json."""
    try:
        data = json.loads(metrics_path.read_text())
        lines = []
        # Show QLIKE per horizon
        for key, val in data.items():
            if isinstance(val, dict) and "qlike" in val:
                qlike = val["qlike"]
                lines.append(f"  {key}: QLIKE={qlike:.4f}")
            elif key == "qlike" and isinstance(val, (int, float)):
                lines.append(f"  QLIKE={val:.4f}")
        if not lines:
            # Fallback: show first few key-value pairs
            for i, (k, v) in enumerate(data.items()):
                if i >= 8:
                    break
                if isinstance(v, (int, float)):
                    lines.append(f"  {k}: {v:.4f}")
                elif isinstance(v, str):
                    lines.append(f"  {k}: {v}")
        return "\n".join(lines[:10]) if lines else "(no metrics summary)"
    except Exception:
        return "(cannot read metrics)"


def _discover_dashboards(models_dir: Path) -> list[tuple[Path, float]]:
    """Find all tournament_dashboard.html files, return (path, mtime) pairs."""
    dashboards: list[tuple[Path, float]] = []
    for trial_dir in models_dir.iterdir():
        if not trial_dir.is_dir():
            continue
        dashboard = trial_dir / "plots" / "tournament_dashboard.html"
        if dashboard.is_file():
            dashboards.append((dashboard, dashboard.stat().st_mtime))
    return dashboards


def _download_dir(project_root: Path) -> Path:
    """Return the download staging directory."""
    dl_dir = project_root / "workspace" / "tmp" / "dashboards"
    dl_dir.mkdir(parents=True, exist_ok=True)
    return dl_dir


def copy_dashboard(dashboard_path: Path, project_root: Path | None = None) -> Path:
    """Copy a dashboard HTML to the download staging directory.

    Returns the destination path.
    """
    if project_root is None:
        project_root = _find_project_root()
    dl_dir = _download_dir(project_root)
    trial_name = dashboard_path.parent.parent.name
    dest = dl_dir / f"{trial_name}_dashboard.html"
    shutil.copy2(dashboard_path, dest)
    return dest


def _open_in_editor(path: Path) -> bool:
    """Open a file in the VS Code editor via the code CLI.

    Returns True if successful, False otherwise.
    """
    try:
        result = subprocess.run(
            ["code", str(path)],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def pick_and_download_dashboard(
    trial_name: str | None = None,
    limit: int = 30,
) -> Path | None:
    """Show interactive picker or directly copy a named trial's dashboard.

    Args:
        trial_name: If provided, skip TUI and copy this trial's dashboard directly.
        limit: Maximum number of dashboards to show in the picker.

    Returns:
        Path to the copied dashboard file, or None if cancelled/not found.
    """
    project_root = _find_project_root()
    models_dir = _find_models_dir()

    # Discover all dashboards
    dashboards = _discover_dashboards(models_dir)

    if not dashboards:
        from volforecast.cli.console import console

        console.print("[yellow]No dashboards found in[/yellow] src/data/models/")
        return None

    # Sort by mtime (newest first)
    dashboards.sort(key=lambda x: x[1], reverse=True)

    # Non-interactive mode: direct trial name lookup
    if trial_name is not None:
        for dash_path, _ in dashboards:
            if dash_path.parent.parent.name == trial_name:
                dest = copy_dashboard(dash_path, project_root)
                opened = _open_in_editor(dest)
                from volforecast.cli.console import console

                if opened:
                    console.print(
                        f"\n  [bold green]\u2713[/bold green] Dashboard opened in editor\n"
                        f"    [dim]{dest}[/dim]\n"
                        f"\n  Right-click editor tab \u2192 Download to save locally\n"
                    )
                else:
                    console.print(
                        f"\n  [bold green]\u2713[/bold green] Dashboard copied to:\n"
                        f"    [bold]{dest}[/bold]\n"
                    )
                return dest
        from volforecast.cli.console import console

        console.print(
            f"[red]Error:[/red] No dashboard found for trial [bold]{trial_name}[/bold]"
        )
        return None

    # Interactive mode requires a TTY
    if not sys.stdin.isatty():
        from volforecast.cli.console import console

        console.print(
            "[red]Error:[/red] No interactive terminal available. "
            "Use [bold]--trial <name>[/bold] to specify a trial."
        )
        sys.exit(1)

    # Limit entries
    dashboards = dashboards[:limit]

    # Load trial metadata for enrichment
    trial_meta = _load_trial_metadata(project_root)

    # Build display entries
    entries: list[str] = []
    trial_names: list[str] = []
    max_name_len = max(len(d.parent.parent.name) for d, _ in dashboards)

    for dash_path, mt in dashboards:
        name = dash_path.parent.parent.name
        trial_names.append(name)
        age = _relative_age(mt)
        padding = " " * (max_name_len - len(name) + 4)

        # Check if this trial is marked completed in trials.yaml
        meta = trial_meta.get(name, {})
        status = (meta.get("status") or "").lower()
        if status == "completed":
            prefix = "✓ "
        elif meta:
            prefix = "● "  # known but not completed
        else:
            prefix = "  "  # not in registry

        entries.append(f"{prefix}{name}{padding}{age}")

    # Preview: show metrics.json content
    def _preview_callback(entry: str) -> str:
        parts = entry.split()
        # Skip prefix symbol
        if parts and parts[0] in ("✓", "●"):
            name = parts[1]
        else:
            name = parts[0]
        metrics_path = models_dir / name / "metrics.json"
        if metrics_path.exists():
            return _metrics_preview(metrics_path)
        # Fallback: show trial metadata from registry
        meta = trial_meta.get(name, {})
        if meta:
            lines = []
            if meta.get("hypothesis"):
                lines.append(f"  Hypothesis: {meta['hypothesis']}")
            if meta.get("key_insight"):
                lines.append(f"  Insight: {meta['key_insight']}")
            horizons = meta.get("horizons", {})
            for h, vals in horizons.items():
                if isinstance(vals, dict) and "qlike" in vals:
                    lines.append(f"  {h}: QLIKE={vals['qlike']}")
            return "\n".join(lines) if lines else "(no preview available)"
        return "(no metrics or registry data)"

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
        title="\n  📊 Select trial dashboard to download\n",
        menu_cursor="  ❯ ",
        menu_cursor_style=("fg_cyan", "bold"),
        menu_highlight_style=("fg_cyan", "bold"),
        cycle_cursor=True,
        clear_screen=False,
        preview_command=_preview_callback,
        preview_title="── Metrics Preview ──",
        preview_size=0.4,
        status_bar="↑/↓ navigate │ Enter select │ / search │ Esc cancel",
        status_bar_style=("fg_gray",),
    )

    idx = menu.show()

    if idx is None:
        return None

    selected_name = trial_names[idx]
    selected_path = dashboards[idx][0]

    dest = copy_dashboard(selected_path, project_root)
    opened = _open_in_editor(dest)

    from volforecast.cli.console import console

    if opened:
        console.print(
            f"\n  [bold green]\u2713[/bold green] Dashboard opened in editor\n"
            f"    [dim]{dest}[/dim]\n"
            f"\n  Right-click editor tab \u2192 Download to save locally\n"
        )
    else:
        console.print(
            f"\n  [bold green]\u2713[/bold green] Dashboard copied to:\n"
            f"    [bold]{dest}[/bold]\n"
        )
    return dest


def register(subparsers) -> None:
    """Register the dashboard subcommand."""
    parser = subparsers.add_parser(
        "dashboard",
        help="Browse and download trial dashboards",
        description=(
            "Interactive picker for trial dashboards. Lists all completed trials\n"
            "that have a tournament_dashboard.html, sorted by last updated.\n"
            "Copies the selected dashboard to workspace/tmp/dashboards/ for download."
        ),
        formatter_class=__import__("argparse").RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--trial",
        type=str,
        default=None,
        help="Trial directory name (skip interactive picker)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Maximum number of dashboards to show (default: 30)",
    )
    parser.set_defaults(func=handle)


def handle(args) -> int:
    """Execute vol dashboard command."""
    result = pick_and_download_dashboard(
        trial_name=args.trial,
        limit=args.limit,
    )
    return 0 if result is not None else 1
