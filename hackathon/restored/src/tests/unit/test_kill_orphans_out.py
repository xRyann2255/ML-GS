"""cleanup.py --out-file sentinel (Plan 03 wfo-03-7, AW-36)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from volforecast.utils.paths import resolve_project_root


def _load_cleanup():
    path = resolve_project_root() / "skills" / "KILL_ORPHANS" / "src" / "cleanup.py"
    spec = importlib.util.spec_from_file_location("ko_cleanup", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dry_run_with_out_file_writes_sentinel(tmp_path: Path) -> None:
    mod = _load_cleanup()
    out = tmp_path / "kill_orphans_out.txt"
    rc = mod.main(["--dry-run", "--out-file", str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert text.rstrip().splitlines()[-1] == "EXIT_CODE=0"
    assert "dry" in text.lower() or "would kill" in text.lower() or "no orphan" in text.lower()


def test_main_still_runs_without_out_file(capsys) -> None:
    mod = _load_cleanup()
    assert mod.main(["--dry-run"]) == 0
    assert capsys.readouterr().out  # summary still printed to console
