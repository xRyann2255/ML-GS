"""Shared Rich console singleton.

All CLI modules import `console` from here to avoid multiple Console
instances conflicting with stderr/live displays.
"""

from __future__ import annotations

import logging

from rich.console import Console
from rich.logging import RichHandler

#: Global console instance. All CLI output goes through this.
console = Console(stderr=True)

#: Panel width for consistent right-edge alignment.
PANEL_WIDTH = 78


def setup_logging(level: int = logging.WARNING) -> None:
    """Configure root logger with RichHandler for inline log display."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, show_path=False, markup=True)],
        force=True,
    )
    # Suppress pyslang's own INFO handler which writes raw stderr during
    # Rich live progress rendering, causing the progress bars to redraw.
    logging.getLogger("goldmansachs.pyslang").setLevel(logging.WARNING)


def print_output_summary(output_dir: str, extra_files: dict[str, str] | None = None) -> None:
    """Print a clear output summary with file paths."""
    from pathlib import Path

    out = Path(output_dir)
    lines: list[tuple[str, str]] = []

    # Check for dashboard
    dashboard = out / "plots" / "tournament_dashboard.html"
    if dashboard.exists():
        lines.append(("Dashboard", str(dashboard.resolve())))

    # Check for metrics
    metrics_file = out / "metrics.json"
    if metrics_file.exists():
        lines.append(("Metrics", str(metrics_file.resolve())))

    # Check for predictions
    plots_dir = out / "plots"
    if plots_dir.exists():
        lines.append(("Plots dir", str(plots_dir.resolve())))

    # Extra files from caller
    if extra_files:
        for label, path in extra_files.items():
            lines.append((label, path))

    # Always show main output dir
    lines.append(("Output dir", str(out.resolve())))

    if lines:
        console.print("\n[bold cyan]━━━ Output ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")
        for label, path in lines:
            console.print(f"  [dim]{label}:[/dim]  {path}")
        console.print("[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]\n")
