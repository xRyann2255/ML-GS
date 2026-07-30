"""GSVIVS01 audit — Phase 3a: timestamp & DST verification.

Reads ``data/external/gsvivs_trades.parquet`` and answers:

1. After converting every UTC timestamp to America/New_York with DST awareness,
   what time-of-day buckets does each (kind, exec_type) fall into?
2. Are there days where the TWAP fills don't start at 09:30 ET? (Half-days,
   early-close days, FOMC-day shifts.)
3. Are there days where the MOC closing-leg has a meaningful timestamp
   (not just epoch sentinel)?
4. What is the actual time-of-day distribution of the FUT_HEDGE TWAP starts?
   When does delta-hedging actually run from / to in ET?

Output: ``workspace/tmp/gsvivs_finding_timestamps.md``
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
TRADES = REPO_ROOT / "data" / "external" / "gsvivs_trades.parquet"
OUT = REPO_ROOT / "workspace" / "tmp" / "gsvivs_finding_timestamps.md"

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


def to_et(ts_str):
    """ISO UTC string -> ET hh:mm string (and the full datetime)."""
    if not isinstance(ts_str, str) or not ts_str or ts_str.startswith("1970"):
        return pd.NA, pd.NA
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).astimezone(ET)
    except Exception:
        return pd.NA, pd.NA
    return dt.strftime("%H:%M"), dt.strftime("%H:%M %Z")


def main() -> None:
    t = pd.read_parquet(TRADES)
    print(f"Loaded {len(t)} trade legs")

    # ---- ET conversions ---------------------------------------------------
    for col in ("gen_time", "exec_start", "exec_end", "exec_time"):
        t[f"{col}_et"], t[f"{col}_et_full"] = zip(*t[col].map(to_et))

    lines: list[str] = ["# GSVIVS01 Audit — Phase 3a Timestamp Findings\n"]

    # ---- 1. time-of-day buckets per (kind, exec_type) ---------------------
    lines.append("## 1. Execution window times, ET (DST-aware)\n")
    lines.append("Grouped by `(kind, exec_type)`. Each cell shows the unique "
                 "set of `(exec_start_et, exec_end_et)` windows that occur, "
                 "with their counts.\n")
    g = t.groupby(["kind", "exec_type"], dropna=False)
    for (kind, etype), sub in g:
        windows = sub.groupby(["exec_start_et", "exec_end_et"], dropna=False).size()
        windows = windows.sort_values(ascending=False)
        lines.append(f"\n### kind={kind!r}  exec_type={etype!r}  (n={len(sub)})\n")
        head = windows.head(20)
        for (s, e), c in head.items():
            lines.append(f"- start={s}  end={e}  count={c}")
        if len(windows) > 20:
            lines.append(f"- ... +{len(windows) - 20} more rare windows")

    # ---- 2. half-day / early-close detection ------------------------------
    lines.append("\n## 2. Days where the OPENING option TWAP did NOT start at 09:30 ET\n")
    opens = t[t["kind"] == "OPT_OPEN"].copy()
    opens_by_day = opens.groupby("date")["exec_start_et"].agg(
        lambda s: sorted(set(s.dropna()))
    )
    abnormal = opens_by_day[opens_by_day.apply(lambda x: x != ["09:30"])]
    lines.append(f"Total days with non-09:30 opening TWAP: {len(abnormal)}\n")
    if len(abnormal) > 0:
        for date, win in abnormal.head(40).items():
            lines.append(f"- {date}: opens at {win}")
    else:
        lines.append("**All days open at 09:30 ET via TWAP. DST conversion is correct.**")

    # ---- 3. closing leg: any non-epoch gen_time? --------------------------
    lines.append("\n## 3. MOC closing-leg timestamp diagnostics\n")
    closes = t[t["kind"] == "OPT_CLOSE"]
    n_close = len(closes)
    n_epoch = int(closes["gen_time"].str.startswith("1970", na=False).sum())
    lines.append(f"Total OPT_CLOSE legs: {n_close}")
    lines.append(f"With gen_time epoch sentinel '1970-01-01': {n_epoch}")
    lines.append(f"With real gen_time: {n_close - n_epoch}")
    non_epoch = closes[~closes["gen_time"].str.startswith("1970", na=False)]
    if len(non_epoch) > 0:
        lines.append(f"\nExamples (first 5):\n")
        for _, row in non_epoch.head(5).iterrows():
            lines.append(f"- {row['date']}: gen={row['gen_time']} "
                         f"exec_type={row['exec_type']} "
                         f"trade_date={row['exec_trade_date']}")

    # Closing-leg execution type / windows
    close_etypes = closes["exec_type"].value_counts(dropna=False)
    lines.append(f"\nClosing-leg exec_types: {dict(close_etypes)}")
    close_starts = closes["exec_start_et"].value_counts(dropna=False).head(10)
    lines.append(f"Closing-leg exec_start_et (top 10, expect mostly NA = MOC has no window):")
    for v, c in close_starts.items():
        lines.append(f"  {v!r}: {c}")

    # ---- 4. opening-leg generation time distribution ---------------------
    lines.append("\n## 4. Opening-leg `gen_time` ET distribution\n")
    opens_gen = opens["gen_time_et"].value_counts(dropna=False).head(20)
    lines.append("(expect overwhelmingly 09:10 ET if signal-fire is uniform)\n")
    for v, c in opens_gen.items():
        lines.append(f"- gen_time_et={v!r}: {c}")

    # ---- 5. futures hedge start/end distribution -------------------------
    lines.append("\n## 5. Futures delta-hedge TWAP windows in ET\n")
    futs = t[t["kind"] == "FUT_HEDGE"].copy()
    fut_starts = futs["exec_start_et"].value_counts(dropna=False).sort_index()
    earliest = fut_starts.index.dropna().min()
    latest = fut_starts.index.dropna().max()
    lines.append(f"FUT_HEDGE TWAP start ET range: {earliest}  ..  {latest}")
    lines.append(f"FUT_HEDGE total legs: {len(futs)}")
    lines.append(f"Median legs/day: {futs.groupby('date').size().median():.0f}")
    # Per-day first and last hedge times
    fday = futs.groupby("date")["exec_start_et"].agg(["min", "max"])
    first_at_open = (fday["min"] == "09:30").sum()
    last_at_close = fday["max"].value_counts().head(5)
    lines.append(f"Days where FIRST hedge starts at 09:30 ET: "
                 f"{first_at_open} / {len(fday)}")
    lines.append(f"Top 5 last-hedge start times (ET):")
    for v, c in last_at_close.items():
        lines.append(f"  {v!r}: {c}")

    # ---- 6. TC records timestamp ----------------------------------------
    lines.append("\n## 6. TC record timestamps\n")
    tcs = t[t["kind"].isin(["TC_O", "TC_FW"])]
    tc_times = tcs["exec_time"].dropna().str[11:16].value_counts().head(5)
    lines.append("`execution_instructions.execution_time` (UTC hh:mm):")
    for v, c in tc_times.items():
        lines.append(f"  {v!r}: {c}")
    tc_et = tcs.assign(et=tcs["exec_time"].map(lambda s: to_et(s)[0])
                       )["et"].value_counts().head(5)
    lines.append("Converted to ET:")
    for v, c in tc_et.items():
        lines.append(f"  {v!r}: {c}")

    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
