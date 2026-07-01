"""GSVIVS01 audit — Phase 1c raw record inspection.

Dump a few specific records verbatim so we know the EXACT JSON structure of
each kind we'll need to parse in Phase 2.
"""

from __future__ import annotations

import json
from pathlib import Path
from pprint import pformat

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = REPO_ROOT / "data" / "external" / "output.json"
OUT = REPO_ROOT / "workspace" / "tmp" / "gsvivs_raw_records.txt"


def main() -> None:
    with INPUT_FILE.open("r") as f:
        data = json.load(f)
    # Use 2024-01-03 (a regular Wed)
    day = next(e for e in data if e["date"] == "2024-01-03")
    val = day["value"]
    tfd = val["trades for date"]
    rfd = val["risks for date"]

    sections: list[tuple[str, list]] = []

    # First option trade with real gen_time + the next 2 records
    for i, item in enumerate(tfd):
        if (isinstance(item, dict) and "source" in item
                and item.get("source") == "VSR 0b"
                and not (item.get("generation time") or "").startswith("1970")):
            sections.append((f"trades[{i}]  OPT_TRADE (open, real gen_time)", [item]))
            sections.append((f"trades[{i+1}]  next record (probable fill leg)",
                             [tfd[i + 1]]))
            if i + 2 < len(tfd):
                sections.append((f"trades[{i+2}]  record after that",
                                 [tfd[i + 2]]))
            break

    # First option trade with epoch gen_time (settlement)
    for i, item in enumerate(tfd):
        if (isinstance(item, dict) and "source" in item
                and item.get("source") == "VSR 0b"
                and (item.get("generation time") or "").startswith("1970")):
            sections.append((f"trades[{i}]  OPT_TRADE (epoch gen_time = settlement?)",
                             [item]))
            sections.append((f"trades[{i+1}]  next record",
                             [tfd[i + 1]]))
            break

    # First futures trade + next record
    for i, item in enumerate(tfd):
        if (isinstance(item, dict) and "source" in item
                and item.get("source") == "Intraday Delta Hedge"):
            sections.append((f"trades[{i}]  FUT_TRADE", [item]))
            sections.append((f"trades[{i+1}]  next record (fill leg)",
                             [tfd[i + 1]]))
            break

    # First CASH_RECORD
    for i, item in enumerate(tfd):
        if (isinstance(item, dict) and "source" in item
                and item.get("instrument", {}).get("instrument type") == "C"):
            sections.append((f"trades[{i}]  CASH_RECORD", [item]))
            sections.append((f"trades[{i+1}]  next record",
                             [tfd[i + 1]] if i + 1 < len(tfd) else []))
            break

    # First OPTION_DEF (today's expiry) from risks + RISK_NODE pair
    for i, item in enumerate(rfd):
        if (isinstance(item, dict)
                and "instrument type" in item
                and item.get("instrument type") == "O"
                and item.get("ex") == "2024-01-03"):
            sections.append((f"risks[{i}]  OPTION_DEF (today expiry)",
                             [item]))
            sections.append((f"risks[{i+1}]  pair: RISK_NODE",
                             [rfd[i + 1]]))
            break

    # First OPTION_DEF (NEXT-day expiry) from risks
    for i, item in enumerate(rfd):
        if (isinstance(item, dict)
                and "instrument type" in item
                and item.get("instrument type") == "O"
                and item.get("ex") == "2024-01-04"):
            sections.append((f"risks[{i}]  OPTION_DEF (next-day expiry, reference)",
                             [item]))
            sections.append((f"risks[{i+1}]  pair: RISK_NODE",
                             [rfd[i + 1]]))
            break

    # Full portfolio
    sections.append(("portfolio (full)", val["portfolio"]))

    # Compare: futures trade count in trades vs risks
    def count(items, src):
        return sum(1 for x in items
                   if isinstance(x, dict) and x.get("source") == src)
    counts_str = (
        f"trades for date: VSR 0b OPT={count(tfd, 'VSR 0b')}  "
        f"FUT={count(tfd, 'Intraday Delta Hedge')}\n"
        f"risks for date:  VSR 0b OPT={count(rfd, 'VSR 0b')}  "
        f"FUT={count(rfd, 'Intraday Delta Hedge')}\n"
    )

    # First few FUT_TRADE gen_times from risks for date - any from previous day?
    fut_gens_risks = [
        x.get("generation time") for x in rfd
        if isinstance(x, dict) and x.get("source") == "Intraday Delta Hedge"
    ]
    fut_gens_trades = [
        x.get("generation time") for x in tfd
        if isinstance(x, dict) and x.get("source") == "Intraday Delta Hedge"
    ]
    risks_min = min((g for g in fut_gens_risks if g and not g.startswith("1970")),
                    default="")
    risks_max = max((g for g in fut_gens_risks if g and not g.startswith("1970")),
                    default="")
    trades_min = min((g for g in fut_gens_trades if g and not g.startswith("1970")),
                     default="")
    trades_max = max((g for g in fut_gens_trades if g and not g.startswith("1970")),
                     default="")
    counts_str += (
        f"\nFUT_TRADE gen_time range:\n"
        f"  trades for date: {trades_min}  ..  {trades_max}\n"
        f"  risks  for date: {risks_min}  ..  {risks_max}\n"
    )

    with OUT.open("w") as f:
        f.write(counts_str)
        f.write("\n" + "=" * 70 + "\n")
        for label, items in sections:
            f.write(f"\n--- {label} ---\n")
            for x in items:
                f.write(pformat(x, width=110) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
