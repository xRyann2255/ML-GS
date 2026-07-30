"""skills/_shared/vf_entry.py — generic args-file adapter (Plan 03 wfo-03-4, AW-05).

Contract: wrapper sets _VF_MODULE (allowed volforecast entry point); args JSON is
{"argv": [...], "out_file": <path>}; adapter imports the module, calls main(argv),
captures stdout+stderr into out_file ending with EXIT_CODE=<rc>, and returns rc.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from volforecast.utils.paths import resolve_project_root


def _load_vf_entry():
    path = resolve_project_root() / "skills" / "_shared" / "vf_entry.py"
    spec = importlib.util.spec_from_file_location("vf_entry", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _args_file(tmp_path: Path, argv: list[str]) -> tuple[Path, Path]:
    out = tmp_path / "out.txt"
    af = tmp_path / "args.json"
    af.write_text(json.dumps({"argv": argv, "out_file": str(out)}), encoding="utf-8")
    return af, out


def test_routes_help_to_volforecast_main(tmp_path, monkeypatch):
    vf = _load_vf_entry()
    af, out = _args_file(tmp_path, ["--help"])
    monkeypatch.setenv("_VF_MODULE", "volforecast.__main__")
    rc = vf.main(["--args-file", str(af)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "usage" in text.lower()
    assert text.rstrip().splitlines()[-1] == "EXIT_CODE=0"


def test_disallowed_module_is_rejected(tmp_path, monkeypatch):
    vf = _load_vf_entry()
    af, out = _args_file(tmp_path, [])
    monkeypatch.setenv("_VF_MODULE", "os")
    rc = vf.main(["--args-file", str(af)])
    assert rc != 0
    assert "not an allowed entry point" in out.read_text(encoding="utf-8")


def test_missing_args_file_returns_one(tmp_path, monkeypatch):
    vf = _load_vf_entry()
    monkeypatch.setenv("_VF_MODULE", "volforecast.__main__")
    assert vf.main(["--args-file", str(tmp_path / "absent.json")]) == 1


def test_target_failure_reaches_sentinel(tmp_path, monkeypatch):
    vf = _load_vf_entry()
    af, out = _args_file(tmp_path, ["definitely-not-a-subcommand"])
    monkeypatch.setenv("_VF_MODULE", "volforecast.__main__")
    rc = vf.main(["--args-file", str(af)])
    assert rc != 0
    assert out.read_text(encoding="utf-8").rstrip().splitlines()[-1] == f"EXIT_CODE={rc}"
