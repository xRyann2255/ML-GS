"""Unified progress display for the volforecast CLI.

Provides:
- ExperimentProgress: Full phase-box for experiments (shows all stages).
- StageProgress: Single-stage progress for standalone commands.

Design:
- Fixed PANEL_WIDTH ensures the right edge stays aligned as content changes.
- Unicode box drawing via rich.panel.Panel.
- Color scheme: blue=INGEST, green=TRAIN, yellow=EVALUATE.
- Non-TTY degrades gracefully (rich auto-detects).
"""

from __future__ import annotations

import time
from enum import Enum

from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from volforecast.cli.console import PANEL_WIDTH, console


class StageState(Enum):
    """Lifecycle state for a pipeline stage."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


# Color mapping per stage name
STAGE_COLORS = {
    "INGEST": "blue",
    "INGEST-IV": "cyan",
    "BACKFILL-RK": "bright_blue",
    "REFRESH-OHLCV": "bright_green",
    "TRAIN": "green",
    "EVALUATE": "yellow",
    "TOURNAMENT": "magenta",
}


def _format_elapsed(seconds: float) -> str:
    """Human-readable elapsed time (e.g. '1m42s', '3s', '2h05m')."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        m, s = divmod(int(seconds), 60)
        return f"{m}m{s:02d}s"
    else:
        h, remainder = divmod(int(seconds), 3600)
        m, _ = divmod(remainder, 60)
        return f"{h}h{m:02d}m"


class _StageInfo:
    """Internal state for one pipeline stage."""

    def __init__(self, name: str, index: int, total_stages: int) -> None:
        self.name = name
        self.index = index
        self.total_stages = total_stages
        self.state = StageState.PENDING
        self.elapsed: float = 0.0
        self.summary_lines: list[str] = []
        self._start_time: float = 0.0

    def start(self) -> None:
        self.state = StageState.RUNNING
        self._start_time = time.time()

    def finish(self, summary: str = "") -> None:
        self.elapsed = time.time() - self._start_time
        self.state = StageState.DONE
        if summary:
            self.summary_lines.append(summary)

    def fail(self) -> None:
        self.elapsed = time.time() - self._start_time
        self.state = StageState.ERROR

    @property
    def prefix(self) -> str:
        return f"[{self.index}/{self.total_stages}]"

    @property
    def color(self) -> str:
        return STAGE_COLORS.get(self.name, "white")


class ExperimentProgress:
    """Full experiment progress display with phase-level box.

    Shows all stages (INGEST, TRAIN, EVALUATE) simultaneously,
    transitioning from PENDING → RUNNING → DONE as work progresses.

    Usage::

        with ExperimentProgress("baseline_har", ["SPY", "AAPL"]) as pp:
            pp.start_stage("INGEST")
            task = pp.add_task("INGEST", total=34, description="symbols")
            for sym in universe:
                # ... do work ...
                pp.advance(task)
                pp.log("INGEST", f"{sym}: 2800 days [1m42s]")
            pp.finish_stage("INGEST")
            pp.start_stage("TRAIN")
            ...
    """

    def __init__(
        self,
        experiment_name: str,
        symbols: list[str],
        stages: list[str] | None = None,
    ) -> None:
        self.experiment_name = experiment_name
        self.symbols = symbols
        stage_names = stages or ["INGEST", "TRAIN", "EVALUATE"]
        self._stages: dict[str, _StageInfo] = {}
        for i, name in enumerate(stage_names, 1):
            self._stages[name] = _StageInfo(name, i, len(stage_names))

        # Rich progress instance for task bars within stages
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("<"),
            TimeRemainingColumn(),
            console=console,
            transient=True,
        )
        self._tasks: dict[str, TaskID] = {}
        self._subtasks: dict[str, TaskID] = {}

    def __enter__(self) -> ExperimentProgress:
        self._progress.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._progress.stop()
        # Print final summary panel
        self._print_final_panel()

    def start_stage(self, name: str) -> None:
        """Mark a stage as RUNNING."""
        self._stages[name].start()

    def finish_stage(self, name: str, summary: str = "") -> None:
        """Mark a stage as DONE with optional summary."""
        stage = self._stages[name]
        stage.finish(summary)
        # Remove progress tasks for this stage
        for key in list(self._tasks.keys()):
            if key.startswith(name):
                self._progress.remove_task(self._tasks.pop(key))
        for key in list(self._subtasks.keys()):
            if key.startswith(name):
                self._progress.remove_task(self._subtasks.pop(key))

    def fail_stage(self, name: str) -> None:
        """Mark a stage as ERROR."""
        self._stages[name].fail()

    def add_task(self, stage: str, total: int, description: str = "") -> str:
        """Add a progress task bar to a stage. Returns a task key."""
        key = f"{stage}:{description}"
        color = self._stages[stage].color
        desc = f"[{color}]{description}[/{color}]"
        task_id = self._progress.add_task(desc, total=total)
        self._tasks[key] = task_id
        return key

    def add_subtask(
        self,
        stage: str,
        total: int | None = None,
        description: str = "",
        *,
        indent: int = 1,
    ) -> str:
        """Add a nested subtask (e.g., day-level within a symbol).

        Parameters
        ----------
        stage : str
            Parent stage name.
        total : int or None
            Step count. ``None`` creates a pulsing indeterminate bar.
        description : str
            Label text.
        indent : int
            Nesting depth (1 = ``└─``, 2 = ``    └─``, etc.).
        """
        key = f"{stage}:sub:{description}"
        prefix = "    " * (indent - 1) + "  └─ "
        task_id = self._progress.add_task(f"{prefix}{description}", total=total, visible=True)
        self._subtasks[key] = task_id
        return key

    def advance(self, key: str, advance: int = 1) -> None:
        """Advance a task or subtask by N steps."""
        if key in self._tasks:
            self._progress.advance(self._tasks[key], advance)
        elif key in self._subtasks:
            self._progress.advance(self._subtasks[key], advance)

    def update_subtask(self, key: str, description: str, *, indent: int = 1) -> None:
        """Update the description of a subtask (status text)."""
        if key in self._subtasks:
            prefix = "    " * (indent - 1) + "  └─ "
            self._progress.update(self._subtasks[key], description=f"{prefix}{description}")

    def remove_subtask(self, key: str) -> None:
        """Remove a completed subtask bar."""
        if key in self._subtasks:
            self._progress.remove_task(self._subtasks.pop(key))

    def log(self, stage: str, message: str) -> None:
        """Add a log line to a stage's summary (printed below the bar)."""
        color = self._stages[stage].color
        self._stages[stage].summary_lines.append(message)
        self._progress.console.print(f"  [{color}][{stage.lower()}][/{color}] {message}")

    def _print_final_panel(self) -> None:
        """Print a final summary panel after all stages complete."""
        rows: list[str] = []
        for stage in self._stages.values():
            icon = {"done": "✓", "error": "✗", "pending": "○"}.get(stage.state.value, "●")
            color = stage.color
            elapsed = _format_elapsed(stage.elapsed) if stage.elapsed else ""
            state_text = stage.state.value
            if stage.state == StageState.DONE:
                state_text = f"done [{elapsed}]"
            row = f"  [{color}]{icon} {stage.prefix} {stage.name:<10}[/{color}]  {state_text}"
            rows.append(row)
            for line in stage.summary_lines[-3:]:
                rows.append(f"      {line}")

        sym_list = ", ".join(self.symbols[:5])
        if len(self.symbols) > 5:
            sym_list += f" +{len(self.symbols) - 5} more"
        title = f"experiment: {self.experiment_name} ({sym_list})"

        panel = Panel(
            "\n".join(rows),
            title=title,
            width=PANEL_WIDTH,
            border_style="dim",
        )
        console.print(panel)


# Backward-compat alias
PipelineProgress = ExperimentProgress


class StageProgress:
    """Single-stage progress display for standalone commands.

    Shows a styled header panel with progress bars inside.

    Usage::

        with StageProgress("ingest", "baseline_har", ["SPY", "AAPL"]) as sp:
            task = sp.add_task(total=2, description="symbols")
            for sym in ["SPY", "AAPL"]:
                sub = sp.add_subtask(total=2800, description=f"{sym} days")
                for day in days:
                    sp.advance(sub)
                sp.remove_subtask(sub)
                sp.advance(task)
                sp.log(f"{sym}: 2800 days [1m38s]")
            sp.finish("2 symbols, 5600 total days")
    """

    def __init__(
        self,
        stage_name: str,
        experiment_name: str,
        symbols: list[str],
    ) -> None:
        self.stage_name = stage_name.upper()
        self.experiment_name = experiment_name
        self.symbols = symbols
        self.color = STAGE_COLORS.get(self.stage_name, "white")
        self._start_time = 0.0
        self._summary_lines: list[str] = []

        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("<"),
            TimeRemainingColumn(),
            console=console,
            transient=True,
        )
        self._tasks: dict[str, TaskID] = {}
        self._subtasks: dict[str, TaskID] = {}

    def __enter__(self) -> StageProgress:
        self._start_time = time.time()
        # Print header
        sym_list = ", ".join(self.symbols[:5])
        if len(self.symbols) > 5:
            sym_list += f" +{len(self.symbols) - 5} more"
        title = f"{self.stage_name.lower()}: {self.experiment_name} ({sym_list})"
        console.print(
            Panel(
                f"[{self.color}]Starting {self.stage_name}...[/{self.color}]",
                title=title,
                width=PANEL_WIDTH,
                border_style=self.color,
            )
        )
        self._progress.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._progress.stop()

    def add_task(self, total: int, description: str = "") -> str:
        """Add a top-level progress task. Returns key."""
        key = f"main:{description}"
        desc = f"[{self.color}]{description}[/{self.color}]"
        task_id = self._progress.add_task(desc, total=total)
        self._tasks[key] = task_id
        return key

    def add_subtask(
        self,
        total: int | None = None,
        description: str = "",
        *,
        indent: int = 1,
    ) -> str:
        """Add a nested subtask bar (e.g., days within a symbol).

        Parameters
        ----------
        total : int or None
            Step count. ``None`` creates a pulsing indeterminate bar.
        description : str
            Label text.
        indent : int
            Nesting depth (1 = ``└─``, 2 = ``    └─``, etc.).
        """
        key = f"sub:{description}"
        prefix = "    " * (indent - 1) + "  └─ "
        task_id = self._progress.add_task(f"{prefix}{description}", total=total, visible=True)
        self._subtasks[key] = task_id
        return key

    def advance(self, key: str, advance: int = 1) -> None:
        """Advance a task or subtask."""
        if key in self._tasks:
            self._progress.advance(self._tasks[key], advance)
        elif key in self._subtasks:
            self._progress.advance(self._subtasks[key], advance)

    def update_subtask(self, key: str, description: str, *, indent: int = 1) -> None:
        """Update subtask description (status text rotation)."""
        if key in self._subtasks:
            prefix = "    " * (indent - 1) + "  └─ "
            self._progress.update(self._subtasks[key], description=f"{prefix}{description}")

    def remove_subtask(self, key: str) -> None:
        """Remove a completed subtask bar."""
        if key in self._subtasks:
            self._progress.remove_task(self._subtasks.pop(key))

    def log(self, message: str) -> None:
        """Print a log line above the progress bar (non-destructive)."""
        self._summary_lines.append(message)
        self._progress.print(
            f"  [{self.color}][{self.stage_name.lower()}][/{self.color}] {message}"
        )

    def finish(self, summary: str = "") -> None:
        """Print final summary with elapsed time."""
        elapsed = _format_elapsed(time.time() - self._start_time)
        msg = f"[{self.color}][{self.stage_name.lower()}][/{self.color}] "
        if summary:
            msg += f"Done: {summary} [{elapsed}]"
        else:
            msg += f"Done [{elapsed}]"
        console.print(f"\n{msg}")
