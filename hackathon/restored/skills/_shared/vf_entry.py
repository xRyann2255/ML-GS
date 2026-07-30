"""Generic args-file adapter: routes a skill task to a real volforecast entry point.

The calling wrapper pins the target via the _VF_MODULE env var; the args-file JSON
supplies {"argv": [...], "out_file": "workspace/tmp/<skill>_out.txt"}. Output protocol
matches ./vol exec: everything captured into out_file, final line EXIT_CODE=<rc>.
Plan 03 wfo-03-4 (AW-05). Do not add modules to ALLOWED without a SKILL.md owner.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ALLOWED = {
    "volforecast.__main__",       # MODEL_TRAIN / FEATURE_BUILD / EVALUATE (run/experiments/compare)
    "volforecast.cli.ingest",     # DATA_INGEST
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vf_entry")
    parser.add_argument("--args-file", required=True, type=Path)
    ns = parser.parse_args(argv)

    if not ns.args_file.is_file():
        print(f"ERROR: args file not found: {ns.args_file}", file=sys.stderr)
        return 1
    spec = json.loads(ns.args_file.read_text(encoding="utf-8"))
    out_file = Path(spec["out_file"])
    module = os.environ.get("_VF_MODULE", "")
    mod_argv = [str(a) for a in spec.get("argv", [])]

    sys.path.insert(0, str(ROOT / "src"))  # volforecast importable from any H:\venv interpreter
    buf = io.StringIO()
    if module not in ALLOWED:
        rc = 1
        buf.write(f"ERROR: {module!r} is not an allowed entry point (allowed: {sorted(ALLOWED)})")
    else:
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                rc = int(importlib.import_module(module).main(mod_argv) or 0)
        except SystemExit as exc:  # argparse --help / parser errors
            rc = int(exc.code or 0)
        except Exception as exc:  # noqa: BLE001 — must reach the sentinel
            buf.write(f"\n{type(exc).__name__}: {exc}")
            rc = 1

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(f"{buf.getvalue()}\nEXIT_CODE={rc}\n", encoding="utf-8")
    print(f"OUTPUT_FILE={out_file}")
    return rc


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
