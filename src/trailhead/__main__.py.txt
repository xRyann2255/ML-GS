"""Entry point for `py -3.11 -m trailhead …`.

Thin on purpose: the argparse surface and the stage driver live in `cli.py`
(plan §10). This file exists so the package is runnable and so the import of
`cli` is guarded — `cli.py` is written later in the build, and until it lands
`import trailhead` and every other module's tests must still work. A bare
`from trailhead import cli` at module scope would make `python -m trailhead`
a traceback instead of a message, which is a worse thing to hit on stage than
an exit code.
"""
import importlib.util
import inspect
import sys


def main(argv: list[str] | None = None) -> int:
    """Hand off to `cli.main`, or explain why we cannot.

    The absence of `cli.py` is detected with `find_spec` rather than by catching
    ImportError around the import. Catching would also swallow an ImportError
    raised *inside* a cli.py that does exist — a real bug reported as "not built
    yet", which is the worst possible message at hour 9.

    `cli.main` is then called with the argument vector if it takes one and with
    nothing if it does not. That is not cleverness for its own sake: `cli.py` is
    owned by another author working from the same plan, the plan's §10 pins the
    flags but not `main`'s arity, and a mismatch here would be a TypeError at
    the top of every run. Both shapes are ordinary and both work.
    """
    if argv is None:
        argv = sys.argv[1:]

    if importlib.util.find_spec("trailhead.cli") is None:
        sys.stderr.write(
            "trailhead: the CLI (src/trailhead/cli.py) is not built yet.\n"
            "Stages can still be driven directly, e.g.\n"
            '  py -3.11 -c "from trailhead import survey; ..."\n'
        )
        return 2

    from trailhead.cli import main as cli_main

    if inspect.signature(cli_main).parameters:
        return cli_main(argv)
    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
