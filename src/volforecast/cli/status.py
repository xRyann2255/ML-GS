"""CLI handler for vol status — show ingestion manifest summary."""

from __future__ import annotations


def register(subparsers) -> None:
    """Register the status subcommand."""
    parser = subparsers.add_parser(
        "status", help="Show ingestion manifest — what's cached vs. planned"
    )
    parser.add_argument(
        "--type",
        type=str,
        default=None,
        help="Filter to a specific data type (e.g., rv, ohlcv)",
    )
    parser.set_defaults(func=handle)


def handle(args) -> int:
    """Execute vol status command. Return exit code."""
    from volforecast.utils.manifest import ManifestManager, _yaml_manifest_path

    yaml_path = _yaml_manifest_path()
    if yaml_path.exists():
        mgr = ManifestManager(yaml_path)
        print(mgr.summary(source=args.type))
        # Show missing symbols from universe
        data = mgr.load()
        if "ticks" in data.sources:
            universe = set(data.meta.universe.symbols)
            ingested = set(data.sources["ticks"].symbols.keys())
            missing = universe - ingested
            if missing:
                print(f"\nMissing from universe ({len(missing)}): {', '.join(sorted(missing))}")
    else:
        # Fallback to legacy JSON manifest
        from volforecast.constants import DEV_UNIVERSE
        from volforecast.utils.manifest import get_missing_symbols, summary_table

        print(summary_table(args.type))
        missing_set = get_missing_symbols("rv", DEV_UNIVERSE)
        if missing_set:
            syms = ", ".join(sorted(missing_set))
            print(f"\nMissing from dev universe ({len(missing_set)}): {syms}")
    return 0
