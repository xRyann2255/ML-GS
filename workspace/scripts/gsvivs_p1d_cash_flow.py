"""GSVIVS01 audit — Phase 1d: is Execution Cash per-day or cumulative?

Test: does ``portfolio[Execution Cash] - portfolio[TC_O] - portfolio[TC_Fw] + 100``
equal ``index value`` exactly each day? And is the diff in Execution Cash from
T-1 to T anywhere near "37 per day" (prior audit's claim) or much smaller?

Also: do the OPT_TRADE records carry an execution price field anywhere we
haven't looked, or are prices ONLY available through the RISK_NODE baselines?
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = REPO_ROOT / "data" / "external" / "output.json"
OUT = REPO_ROOT / "workspace" / "tmp" / "gsvivs_cash_flow_check.txt"


def get_portfolio_cash(portfolio: list) -> dict:
    """Return {source: quantity} for cash entries in portfolio."""
    out = {}
    i = 0
    while i < len(portfolio) - 1:
        a, b = portfolio[i], portfolio[i + 1]
        if (isinstance(a, dict) and not isinstance(b, (dict, list))
                and a.get("instrument", {}).get("instrument type") == "C"):
            src = a.get("source", "?")
            out[src] = b
        i += 2 if isinstance(a, dict) else 1
    return out


def all_keys_recursive(obj, depth=0, found=None):
    """Collect every key encountered in a nested structure."""
    if found is None:
        found = set()
    if depth > 8:
        return found
    if isinstance(obj, dict):
        for k in obj.keys():
            found.add(k)
        for v in obj.values():
            all_keys_recursive(v, depth + 1, found)
    elif isinstance(obj, list):
        for v in obj:
            all_keys_recursive(v, depth + 1, found)
    return found


def main() -> None:
    with INPUT_FILE.open("r") as f:
        data = json.load(f)

    lines = []

    # Q1: does cash + initial + TCs = index value?
    lines.append("=" * 70)
    lines.append("Q1: Does Initial + ExecCash + TC_O + TC_Fw = index value?")
    lines.append("=" * 70)
    mismatch = 0
    for entry in data:
        v = entry["value"]
        cash = get_portfolio_cash(v.get("portfolio", []))
        index = v.get("index value")
        if index is None:
            continue
        total = sum(cash.values())
        diff = abs(total - index)
        if diff > 1e-6:
            mismatch += 1
            if mismatch <= 5:
                lines.append(f"  {entry['date']}: cash_sum={total:.6f} index={index:.6f} diff={diff:.2e}")
                lines.append(f"      cash dict: {cash}")
    lines.append(f"Total mismatches: {mismatch} / {len(data)}")
    lines.append("")

    # Q2: is Execution Cash level cumulative? Compare day-to-day diffs
    lines.append("=" * 70)
    lines.append("Q2: Day-to-day diff in Execution Cash (proxy for daily premium)")
    lines.append("=" * 70)
    prev_cash = None
    prev_date = None
    diffs = []
    sample = []
    for entry in data:
        v = entry["value"]
        cash = get_portfolio_cash(v.get("portfolio", []))
        ec = cash.get("Execution Cash")
        if ec is None:
            continue
        if prev_cash is not None:
            d = ec - prev_cash
            diffs.append(d)
            if len(sample) < 10:
                sample.append((prev_date, entry["date"], prev_cash, ec, d))
        prev_cash = ec
        prev_date = entry["date"]
    if diffs:
        import statistics
        lines.append(f"  n diffs            : {len(diffs)}")
        lines.append(f"  mean diff          : {statistics.mean(diffs):.4f}")
        lines.append(f"  median diff        : {statistics.median(diffs):.4f}")
        lines.append(f"  stdev diff         : {statistics.stdev(diffs):.4f}")
        lines.append(f"  min diff           : {min(diffs):.4f}")
        lines.append(f"  max diff           : {max(diffs):.4f}")
        lines.append(f"  ExecCash level mean: {statistics.mean(diffs)*len(diffs):.4f} approx end value")
    lines.append("\n  Sample (first 10 day-to-day diffs):")
    for prev_d, d, p, c, df in sample:
        lines.append(f"    {prev_d} -> {d}: ExecCash {p:.4f} -> {c:.4f}  (diff {df:+.4f})")
    lines.append("")

    # Q3: what keys ever appear inside an OPT_TRADE? do any contain prices?
    lines.append("=" * 70)
    lines.append("Q3: All keys ever seen inside a VSR 0b trade record (top-level)")
    lines.append("=" * 70)
    keys = set()
    n_with_price = 0
    n_total = 0
    for entry in data:
        for lst_key in ("trades for date",):
            for x in entry.get("value", {}).get(lst_key, []):
                if isinstance(x, dict) and x.get("source") == "VSR 0b":
                    n_total += 1
                    keys.update(x.keys())
                    # Are any keys containing 'price' anywhere?
                    if any("price" in k.lower() for k in all_keys_recursive(x)):
                        n_with_price += 1
    lines.append(f"  records examined         : {n_total}")
    lines.append(f"  top-level keys seen      : {sorted(keys)}")
    lines.append(f"  records with any 'price' key (recursive): {n_with_price}")
    lines.append("")

    # Q4: all keys recursive
    sample_trade = None
    for entry in data:
        for x in entry["value"].get("trades for date", []):
            if isinstance(x, dict) and x.get("source") == "VSR 0b":
                sample_trade = x
                break
        if sample_trade:
            break
    lines.append("  Recursive keys of sample VSR 0b trade:")
    lines.append(f"  {sorted(all_keys_recursive(sample_trade))}")
    lines.append("")

    # Q5: Execution Cash final value vs trial summary
    lines.append("=" * 70)
    lines.append("Q5: Cumulative cash flows from first to last day")
    lines.append("=" * 70)
    first = data[0]
    last = data[-1]
    f_cash = get_portfolio_cash(first["value"].get("portfolio", []))
    l_cash = get_portfolio_cash(last["value"].get("portfolio", []))
    lines.append(f"  First day {first['date']}: {f_cash}")
    lines.append(f"  Last  day {last['date']}: {l_cash}")
    lines.append("")

    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
