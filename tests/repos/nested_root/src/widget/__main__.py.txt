"""`python -m widget` -- the console script named in pyproject [project.scripts]."""
import argparse

from widget.core.model import Widget
from widget.io.loader import load


def build_parser():
    p = argparse.ArgumentParser(prog="widget")
    sub = p.add_subparsers(dest="command")
    sub.add_parser("show", help="Describe one widget.")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    widget = load(args.command or "default")
    print(Widget.describe(widget))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
