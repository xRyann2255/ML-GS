"""Interactive config picker for `vol run` (no --config)."""

from __future__ import annotations

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


def _find_configs_dir() -> Path:
    """Resolve workspace/configs/ relative to the project root."""
    # __main__.py is always run from src/, project root is one level up
    root = Path(__file__).resolve().parents[3]
    configs_dir = root / "workspace" / "configs"
    if not configs_dir.is_dir():
        raise FileNotFoundError(f"Configs directory not found: {configs_dir}")
    return configs_dir


def _preview_callback(configs: list[Path]):
    """Return a preview function for TerminalMenu."""

    def preview(entry: str) -> str:
        # entry is the display string; extract filename (before the padding)
        name = entry.split()[0]
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
    max_name_len = max(len(f.name) for f, _ in yaml_files)
    entries: list[str] = []
    for f, mt in yaml_files:
        age = _relative_age(mt)
        padding = " " * (max_name_len - len(f.name) + 4)
        entries.append(f"{f.name}{padding}{age}")

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
