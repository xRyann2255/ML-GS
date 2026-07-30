"""GSVIVS01 audit — Phase 1b record taxonomy.

For ONE representative day, classify every entry in ``trades for date`` and
``risks for date`` by what kind of record it is:

* ``OPTION_DEF``  — a bare instrument definition (no trade fields)
* ``RISK_NODE``   — a "baseline risks" / "risk node type" payload
* ``OPT_TRADE``   — a real option trade (has source + quantity + instrument)
* ``FUT_TRADE``   — a real futures trade (delta hedge)

Within each kind, report:
* counts and date ranges of execution windows / generation times
* unique expiries / strikes / sources
* whether they pair with each other (OPTION_DEF followed by RISK_NODE etc.)

This script characterizes WHAT IS IN the two daily lists — not WHAT THEY MEAN.
That interpretation comes in Phase 3.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = REPO_ROOT / "data" / "external" / "output.json"
OUT_DIR = REPO_ROOT / "workspace" / "tmp"

# Probe these days: first real trade day, mid, recent, and a Friday (weekend handling)
PROBE_DATES = ["2022-05-26", "2024-01-03", "2026-05-29", "2024-08-30"]


def classify(item) -> str:
    """Return one of: OPTION_DEF, RISK_NODE, OPT_TRADE, FUT_TRADE, OTHER."""
    if not isinstance(item, dict):
        return "PRIMITIVE"
    if "risk node type" in item or "baseline risks" in item:
        return "RISK_NODE"
    if "source" in item:
        inst = item.get("instrument", {})
        itype = inst.get("instrument type")
        if itype == "O":
            return "OPT_TRADE"
        if itype == "F":
            return "FUT_TRADE"
        if itype == "C":
            return "CASH_RECORD"
        return f"TRADE_{itype}"
    if "instrument type" in item:
        # bare instrument def
        if item.get("instrument type") == "O":
            return "OPTION_DEF"
        if item.get("instrument type") == "F":
            return "FUTURE_DEF"
        return "INST_DEF_OTHER"
    return "UNKNOWN"


def summarize_records(items, label: str) -> list[str]:
    lines: list[str] = []
    n = len(items)
    kinds = Counter(classify(x) for x in items)
    lines.append(f"\n--- {label}  (n={n}) ---")
    for k, c in kinds.most_common():
        lines.append(f"  {k:20s} : {c}")

    # Adjacent-pair patterns (i, i+1) -> diagnose pairing
    pair_counts: Counter = Counter()
    for i in range(n - 1):
        a = classify(items[i])
        b = classify(items[i + 1])
        pair_counts[(a, b)] += 1
    lines.append(f"\n  Adjacent (i, i+1) patterns:")
    for (a, b), c in pair_counts.most_common(10):
        lines.append(f"    {a:18s} -> {b:18s} : {c}")

    # For each OPT_TRADE / FUT_TRADE, dump trade-date vs expiry-date and source
    opt_trades = [(i, x) for i, x in enumerate(items) if classify(x) == "OPT_TRADE"]
    fut_trades = [(i, x) for i, x in enumerate(items) if classify(x) == "FUT_TRADE"]

    if opt_trades:
        sources = Counter(x.get("source") for _, x in opt_trades)
        expiries = Counter(x.get("instrument", {}).get("ex") for _, x in opt_trades)
        gen_times = Counter(x.get("generation time", "")[:16] for _, x in opt_trades)
        exec_windows: Counter = Counter()
        for _, x in opt_trades:
            ei = x.get("execution instructions", {}) or {}
            s = (ei.get("start time") or "")[:16]
            e = (ei.get("end time") or "")[:16]
            exec_windows[(s, e)] += 1
        epoch_count = sum(1 for _, x in opt_trades
                          if (x.get("generation time") or "").startswith("1970"))
        lines.append(f"\n  OPT_TRADES: {len(opt_trades)}")
        lines.append(f"    sources         : {dict(sources)}")
        lines.append(f"    unique expiries : {dict(expiries)}")
        lines.append(f"    epoch gen_time  : {epoch_count}")
        lines.append(f"    unique gen_time : {len(gen_times)}")
        for gt, c in gen_times.most_common(5):
            lines.append(f"      gen={gt}  count={c}")
        lines.append(f"    unique exec windows: {len(exec_windows)}")
        for (s, e), c in exec_windows.most_common(5):
            lines.append(f"      start={s} end={e} count={c}")

    if fut_trades:
        sources = Counter(x.get("source") for _, x in fut_trades)
        gen_times = sorted({(x.get("generation time") or "")[:16] for _, x in fut_trades})
        lines.append(f"\n  FUT_TRADES: {len(fut_trades)}")
        lines.append(f"    sources         : {dict(sources)}")
        lines.append(f"    gen_time range  : {gen_times[0]}  ..  {gen_times[-1]}")
        lines.append(f"    n unique gen_time: {len(gen_times)}")

    # OPTION_DEF inventory
    opt_defs = [(i, x) for i, x in enumerate(items) if classify(x) == "OPTION_DEF"]
    if opt_defs:
        expiries = Counter(x.get("ex") for _, x in opt_defs)
        lines.append(f"\n  OPTION_DEF: {len(opt_defs)}")
        lines.append(f"    expiries: {dict(expiries)}")

    return lines


def summarize_portfolio(portfolio) -> list[str]:
    """Portfolio is a flat list alternating {meta-dict, scalar-quantity}."""
    lines = []
    lines.append(f"\n--- portfolio  (n={len(portfolio)}) ---")
    # Pull dict entries and their following scalar
    holdings = []
    i = 0
    while i < len(portfolio) - 1:
        a = portfolio[i]
        b = portfolio[i + 1]
        if isinstance(a, dict) and not isinstance(b, (dict, list)):
            inst = a.get("instrument", {})
            holdings.append({
                "source": a.get("source", "?"),
                "type": inst.get("instrument type", "?"),
                "expiry": inst.get("ex", ""),
                "strike": inst.get("k", ""),
                "qty": b,
            })
            i += 2
        else:
            i += 1
    for h in holdings:
        lines.append(f"  src={h['source']:25s} type={h['type']:3s}  qty={h['qty']:.6f}  "
                     f"exp={h['expiry']} k={h['strike']}")
    return lines


def main() -> None:
    print(f"Loading {INPUT_FILE}")
    with INPUT_FILE.open("r") as f:
        data = json.load(f)
    by_date = {e["date"]: e for e in data}
    print(f"  {len(data)} day entries")

    out = OUT_DIR / "gsvivs_record_taxonomy.txt"
    with out.open("w") as f:
        for d in PROBE_DATES:
            if d not in by_date:
                f.write(f"\n!!!! {d} not in data, skipping\n")
                continue
            entry = by_date[d]
            value = entry["value"]
            f.write(f"\n{'=' * 70}\nDATE: {d}    close: {value.get('close time')}\n")
            f.write(f"index_value: {value.get('index value')}\n")
            for lst_key in ("trades for date", "risks for date"):
                items = value.get(lst_key, [])
                for line in summarize_records(items, lst_key):
                    f.write(line + "\n")
            for line in summarize_portfolio(value.get("portfolio", [])):
                f.write(line + "\n")

    print(f"wrote {out}")


if __name__ == "__main__":
    main()
