"""CLI for GSVIVS IV source comparison tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from rich.table import Table

from volforecast.cli.console import console
from volforecast.evaluation.kvar_table import build_kvar_tables


def _render_table(title: str, table_df: pd.DataFrame) -> None:
    common_dates = int(table_df.attrs.get("common_dates", 0))
    console.print(f"\n[bold]{title}, common {common_dates} days:[/bold]\n")

    table = Table(show_header=True)
    for column in [
        "Model",
        "Sharpe",
        "Ann Ret",
        "Total",
        "MaxDD",
        "Short%",
        "Hit%",
        "Days",
        "Mean IV",
        "IV Std",
    ]:
        table.add_column(column, justify="left" if column == "Model" else "right")

    for _, row in table_df.iterrows():
        mean_iv = "-" if pd.isna(row["Mean IV"]) else f"{row['Mean IV']:.2f}"
        iv_std = "-" if pd.isna(row["IV Std"]) else f"{row['IV Std']:.2f}"
        table.add_row(
            str(row["Model"]),
            f"{row['Sharpe']:.2f}",
            f"{row['Ann Ret']:+.1f}%",
            f"{row['Total']:+.1f}%",
            f"{row['MaxDD']:.1f}%",
            f"{row['Short%']:.1f}%",
            f"{row['Hit%']:.1f}%",
            str(int(row["Days"])),
            mean_iv,
            iv_std,
        )
    console.print(table)


def run(target: str = "both", edrvs_intraday_path: str | None = None) -> int:
    tables = build_kvar_tables(
        edrvs_intraday_path=Path(edrvs_intraday_path) if edrvs_intraday_path else None,
    )

    if target in {"both", "same-day"}:
        _render_table("Same-Day RV (perfect foresight for today)", tables["Same-Day RV"])
    if target in {"both", "next-day"}:
        _render_table("Next-Day RV (forecasting target)", tables["Next-Day RV"])
    return 0


def register(subparsers) -> None:
    """Register the kvar subcommand."""
    parser = subparsers.add_parser(
        "kvar",
        help="Compare GSVIVS signal results across cached IV sources",
    )
    parser.add_argument(
        "--target",
        type=str,
        default="both",
        choices=["both", "same-day", "next-day"],
        help="Which RV target table(s) to print",
    )
    parser.add_argument(
        "--edrvs-intraday-path",
        type=str,
        default=None,
        help="Optional raw EDRVS expiry intraday parquet for 2-DTE rows",
    )
    parser.set_defaults(func=handle)


def handle(args) -> int:
    """Execute kvar command. Return exit code."""
    return run(
        target=args.target,
        edrvs_intraday_path=args.edrvs_intraday_path,
    )
