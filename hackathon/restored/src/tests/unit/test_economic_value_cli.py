"""Args-file CLI for evaluation/economic_value.py (Plan 03 wfo-03-3, AW-05 BACKTEST variant).

Contract: python -m volforecast.evaluation.economic_value --args-file <json>
  args JSON: {"csv": <path>, "columns": {<summary-kwarg>: <csv-column>, ...},
              "model_name": <str>, "out_file": <path>}
  columns required: vol_forecast, daily_returns.
  columns optional: realized_vol, implied_vol, spot, signal (absent -> vol-targeting-only).
  out_file: JSON summary body, then a final line EXIT_CODE=<rc>.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def _write_inputs(tmp_path: Path, *, full: bool = True) -> tuple[Path, Path]:
    rng = np.random.default_rng(42)
    n = 300
    data = {
        "fc": np.abs(rng.normal(0.15, 0.03, n)),
        "ret": rng.normal(0.0, 0.01, n),
    }
    columns = {"vol_forecast": "fc", "daily_returns": "ret"}
    if full:
        data.update(
            rv=np.abs(rng.normal(0.15, 0.03, n)),
            iv=np.abs(rng.normal(0.17, 0.03, n)),
            spot=100.0 + np.cumsum(rng.normal(0.0, 1.0, n)),
            sig=rng.choice([-1.0, 0.0, 1.0], n),
        )
        columns.update(realized_vol="rv", implied_vol="iv", spot="spot", signal="sig")
    csv = tmp_path / "preds.csv"
    pd.DataFrame(data).to_csv(csv, index=False)
    out = tmp_path / "backtest_out.json"
    args_file = tmp_path / "backtest_args.json"
    args_file.write_text(
        json.dumps(
            {"csv": str(csv), "columns": columns, "model_name": "har", "out_file": str(out)}
        ),
        encoding="utf-8",
    )
    return args_file, out


def _parse_out(out: Path) -> tuple[dict, str]:
    lines = out.read_text(encoding="utf-8").rstrip().splitlines()
    return json.loads("\n".join(lines[:-1])), lines[-1]


class TestEconomicValueCli:
    def test_full_columns_returns_zero_and_writes_summary(self, tmp_path: Path) -> None:
        from volforecast.evaluation.economic_value import main

        args_file, out = _write_inputs(tmp_path, full=True)
        rc = main(["--args-file", str(args_file)])
        assert rc == 0
        body, sentinel = _parse_out(out)
        assert sentinel == "EXIT_CODE=0"
        assert body["model"] == "har"
        for key in ("vol_target_sharpe", "vol_target_max_dd", "straddle_sharpe", "hit_rate"):
            assert key in body

    def test_vol_targeting_only_when_optional_columns_absent(self, tmp_path: Path) -> None:
        from volforecast.evaluation.economic_value import main

        args_file, out = _write_inputs(tmp_path, full=False)
        assert main(["--args-file", str(args_file)]) == 0
        body, sentinel = _parse_out(out)
        assert sentinel == "EXIT_CODE=0"
        assert "vol_target_sharpe" in body
        assert "straddle_sharpe" not in body

    def test_missing_args_file_returns_one(self, tmp_path: Path) -> None:
        from volforecast.evaluation.economic_value import main

        assert main(["--args-file", str(tmp_path / "absent.json")]) == 1

    def test_missing_required_column_writes_error_and_sentinel_one(self, tmp_path: Path) -> None:
        from volforecast.evaluation.economic_value import main

        args_file, out = _write_inputs(tmp_path, full=False)
        spec = json.loads(args_file.read_text(encoding="utf-8"))
        del spec["columns"]["daily_returns"]
        args_file.write_text(json.dumps(spec), encoding="utf-8")
        assert main(["--args-file", str(args_file)]) == 1
        body, sentinel = _parse_out(out)
        assert sentinel == "EXIT_CODE=1"
        assert "error" in body
