"""CLI entry point for FEATURE_BUILD skill.

Orchestrates feature computation across layers 0-6.
Reads raw data from workspace/tmp/, computes features,
and writes feature DataFrames to workspace/tmp/.

Usage:
    python -m volforecast.cli.build_features --config <args.json>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for feature building."""
    parser = argparse.ArgumentParser(description="FEATURE_BUILD skill entry point")
    parser.add_argument("--config", type=Path, required=True, help="Path to args JSON file")
    return parser.parse_args(argv)


def build_layer(
    layer: int,
    symbol: str,
    start_date: str,
    end_date: str,
    data_dir: Path,
) -> pd.DataFrame:
    """Build features for a specific layer.

    Parameters
    ----------
    layer : int
        Feature layer (0-6).
    symbol : str
        Ticker symbol.
    start_date : str
        Start date (YYYY-MM-DD).
    end_date : str
        End date (YYYY-MM-DD).
    data_dir : Path
        Directory containing input data files.

    Returns
    -------
    pd.DataFrame
        Feature DataFrame with date index and feature columns.

    Raises
    ------
    ValueError
        If layer is not in 0-6.
    """
    raise NotImplementedError("TODO: implement")


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    raise NotImplementedError("TODO: implement")


if __name__ == "__main__":
    sys.exit(main())
