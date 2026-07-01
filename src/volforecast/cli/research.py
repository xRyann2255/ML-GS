"""CLI entry point for RESEARCH skill.

Manages structured research sessions: reads research journal,
presents open questions, guides exploration, and documents findings.

Usage:
    python -m volforecast.cli.research --config <args.json>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for research session."""
    parser = argparse.ArgumentParser(description="RESEARCH skill entry point")
    parser.add_argument("--config", type=Path, required=True, help="Path to args JSON file")
    return parser.parse_args(argv)


def load_research_context(
    journal_path: Path,
    open_questions_path: Path,
) -> dict[str, Any]:
    """Load research context (journal + open questions)."""
    raise NotImplementedError("TODO: implement")


def document_findings(
    topic: str,
    findings: str,
    journal_path: Path,
) -> None:
    """Append findings to research journal."""
    raise NotImplementedError("TODO: implement")


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    raise NotImplementedError("TODO: implement")


if __name__ == "__main__":
    sys.exit(main())
