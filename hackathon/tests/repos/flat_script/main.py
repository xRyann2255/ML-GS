"""Command-line front door. Nothing imports this module."""
import argparse
import json
import sys


def build_parser():
    """Two subcommands, so add_parser() has literal names to harvest."""
    p = argparse.ArgumentParser(prog="flat", description="A flat little tool.")
    sub = p.add_subparsers(dest="command")
    sub.add_parser("summarise", help="Print a summary.")
    sub.add_parser("export", help="Write JSON to stdout.")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    json.dump({"command": args.command}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
