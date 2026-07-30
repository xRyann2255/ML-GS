"""GSVIVS01 — Phase 3 quick probe: half-day detection via close_time + ES roll."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DAILY = REPO_ROOT / "data" / "external" / "gsvivs_daily.parquet"
TRADES = REPO_ROOT / "data" / "external" / "gsvivs_trades.parquet"
OUT = REPO_ROOT / "workspace" / "tmp" / "gsvivs_finding_halfdays_es_roll.md"
ET = ZoneInfo("America/New_York")


def to_et_hhmm(s):
    if not isinstance(s, str) or not s:
        return None
    try:
        return datetime.fromisoformat(
            s.replace("Z", "+00:00")
        ).astimezone(ET).strftime("%H:%M")
    except Exception:
        return None


def main() -> None:
    d = pd.read_parquet(DAILY)
    t = pd.read_parquet(TRADES)
    lines = ["# GSVIVS01 — Half-day + ES roll probe\n"]

    # ---- 1. close_time distribution (ET) -------------------------------
    d["close_time_et"] = d["close_time"].map(to_et_hhmm)
    counts = d["close_time_et"].value_counts(dropna=False)
    lines.append("## 1. Daily `close time` distribution in ET\n")
    for v, c in counts.items():
        lines.append(f"- {v!r}: {c}")

    # ---- 2. close_time != 17:00/18:00 ET (would suggest half-day) ------
    abnormal = d[~d["close_time_et"].isin(["17:00", "18:00"])]
    lines.append(f"\nDays with non-standard close time: {len(abnormal)}")
    if len(abnormal) > 0:
        for _, r in abnormal.head(40).iterrows():
            lines.append(f"- {r['date']}: close_time={r['close_time']} et={r['close_time_et']}")

    # ---- 3. Half-day suspects: known calendar dates --------------------
    # Day-after-Thanksgiving + Christmas Eve + July 3 of relevant years
    suspects = [
        "2022-07-01", "2022-11-25", "2022-12-23",  # not strict but close
        "2023-07-03", "2023-11-24", "2023-12-22",
        "2024-07-03", "2024-11-29", "2024-12-24",
        "2025-07-03", "2025-11-28", "2025-12-24",
    ]
    lines.append("\n## 2. Calendar half-day suspect days (Day-after-Thanksgiving, "
                 "Christmas Eve, July 3)\n")
    for s in suspects:
        row = d[d["date"] == s]
        if len(row) == 0:
            lines.append(f"- {s}: NOT IN DATA")
        else:
            r = row.iloc[0]
            lines.append(f"- {s}: close_time_et={r['close_time_et']}  "
                         f"index={r['index_value']:.4f}")

    # ---- 4. ES futures month/symbol distribution -----------------------
    lines.append("\n## 3. ES futures roll history\n")
    fut = t[t["kind"] == "FUT_HEDGE"]
    fut_months = fut.groupby("fut_month").agg(
        first_date=("date", "min"),
        last_date=("date", "max"),
        n_trades=("date", "count"),
    ).sort_values("first_date")
    for month, row in fut_months.iterrows():
        lines.append(f"- {month}: {row['first_date']} -> {row['last_date']}  "
                     f"(n={row['n_trades']})")

    # ---- 5. Strip size distribution per day ----------------------------
    lines.append("\n## 4. Strip size (opening leg count per day) distribution\n")
    n_open = t[t["kind"] == "OPT_OPEN"].groupby("date").size()
    lines.append(f"- mean: {n_open.mean():.1f}")
    lines.append(f"- median: {n_open.median():.0f}")
    lines.append(f"- std: {n_open.std():.1f}")
    lines.append(f"- min: {n_open.min()}")
    lines.append(f"- max: {n_open.max()}")
    lines.append(f"- 5th pct: {n_open.quantile(0.05):.0f}")
    lines.append(f"- 95th pct: {n_open.quantile(0.95):.0f}")
    lines.append(f"- days with no opening trades: {(n_open == 0).sum()}")

    # ---- 6. Per-day OPT_OPEN expiry == date sanity ---------------------
    lines.append("\n## 5. Are ALL OPT_OPEN trades 0DTE (expiry == trade date)?\n")
    opens = t[t["kind"] == "OPT_OPEN"].copy()
    opens["is_0dte"] = (opens["date"] == opens["expiry"])
    lines.append(f"- total OPT_OPEN legs: {len(opens)}")
    lines.append(f"- 0DTE (expiry == trade date): {opens['is_0dte'].sum()}")
    lines.append(f"- NOT 0DTE: {(~opens['is_0dte']).sum()}")
    if (~opens["is_0dte"]).any():
        ex = opens[~opens["is_0dte"]].head(20)
        lines.append("\nExamples of non-0DTE opens:")
        for _, r in ex.iterrows():
            lines.append(f"- date={r['date']} expiry={r['expiry']}")

    # ---- 7. Days without any trades (the 2 "Initial-only" days?) -------
    lines.append("\n## 6. Days with NO trades for date\n")
    all_dates = set(d["date"])
    trading_dates = set(t["date"])
    no_trade = sorted(all_dates - trading_dates)
    lines.append(f"Days with empty trade tape: {len(no_trade)}")
    for s in no_trade:
        r = d[d["date"] == s].iloc[0]
        lines.append(f"- {s}: index={r['index_value']:.4f} close_time={r['close_time']}")

    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
