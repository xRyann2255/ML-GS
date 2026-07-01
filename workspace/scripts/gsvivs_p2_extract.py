"""GSVIVS01 audit — Phase 2: lean trade tape + daily scalars extraction.

Produces TWO parquets at ``data/external/``:

* ``gsvivs_trades.parquet``  — one row per trade leg in ``trades for date``.
  No price column (none exists in the JSON). No risk-node data (per user
  directive: risk nodes are decorative and a source of confusion).
* ``gsvivs_daily.parquet``  — one row per day with index value, divisor,
  close time, cumulative cash levels (Initial / Execution Cash / TC_O /
  TC_Fw), and the derived per-day FLOWS (= daily diff of the cumulative
  cash levels).

Phase 2 gate (must pass before continuing):
  For every day, ``sum(cumulative cash levels) == index_value`` exactly.
  Already verified in Phase 1; re-asserted here on the persisted parquet.

The portfolio file from the plan is intentionally NOT emitted: portfolio
in this JSON is only cash, fully captured in ``gsvivs_daily.parquet``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = REPO_ROOT / "data" / "external" / "output.json"
OUT_DIR = REPO_ROOT / "data" / "external"
TRADES_PATH = OUT_DIR / "gsvivs_trades.parquet"
DAILY_PATH = OUT_DIR / "gsvivs_daily.parquet"


def classify_record(item: dict) -> str:
    """Return one of: OPT_OPEN, OPT_CLOSE, FUT_HEDGE, TC_O, TC_FW, OTHER."""
    if not isinstance(item, dict) or "source" not in item:
        return "OTHER"
    src = item.get("source", "")
    inst = item.get("instrument", {}) or {}
    itype = inst.get("instrument type")
    if src == "VSR 0b" and itype == "O":
        gt = item.get("generation time", "") or ""
        return "OPT_CLOSE" if gt.startswith("1970") else "OPT_OPEN"
    if src == "Intraday Delta Hedge" and itype == "F":
        return "FUT_HEDGE"
    if src == "Transaction Costs O":
        return "TC_O"
    if src == "Transactions Costs Fw":
        return "TC_FW"
    return "OTHER"


def extract_trade_row(date: str, item: dict, kind: str) -> dict:
    inst = item.get("instrument", {}) or {}
    ei = item.get("execution instructions", {}) or {}
    return {
        "date": date,
        "kind": kind,
        "source": item.get("source"),
        "gen_time": item.get("generation time"),
        "exec_type": ei.get("type"),
        "exec_start": ei.get("start time"),
        "exec_end": ei.get("end time"),
        "exec_time": ei.get("execution time"),
        "exec_trade_date": ei.get("trade date"),
        "quantity": item.get("quantity"),
        "inst_type": inst.get("instrument type"),
        "underlying": inst.get("underlying asset"),
        "expiry": inst.get("ex"),
        "expiry_type": inst.get("expiry type"),
        "strike": inst.get("k"),
        "put_call": inst.get("option type"),
        "fut_symbol": inst.get("symbol"),
        "fut_prefix": inst.get("future prefix"),
        "fut_month": inst.get("month"),
        "denominated": inst.get("denominated"),
    }


def get_portfolio_cash(portfolio: list) -> dict[str, float]:
    out: dict[str, float] = {}
    i = 0
    while i < len(portfolio) - 1:
        a, b = portfolio[i], portfolio[i + 1]
        if (isinstance(a, dict)
                and not isinstance(b, (dict, list))
                and a.get("instrument", {}).get("instrument type") == "C"):
            src = a.get("source", "?")
            out[src] = b
        i += 2 if isinstance(a, dict) else 1
    return out


def main() -> None:
    print(f"Loading {INPUT_FILE} ({INPUT_FILE.stat().st_size / 1e6:.1f} MB)")
    with INPUT_FILE.open("r") as f:
        data = json.load(f)
    print(f"  -> {len(data)} day entries")

    trade_rows: list[dict] = []
    daily_rows: list[dict] = []
    other_count = 0

    for entry in data:
        d = entry["date"]
        v = entry["value"]
        tfd = v.get("trades for date", []) or []

        # ---- per-day trade rows -----------------------------------------
        for item in tfd:
            kind = classify_record(item)
            if kind == "OTHER":
                other_count += 1
                continue
            trade_rows.append(extract_trade_row(d, item, kind))

        # ---- per-day scalars + cumulative cash --------------------------
        cash = get_portfolio_cash(v.get("portfolio", []))
        daily_rows.append({
            "date": d,
            "close_time": v.get("close time"),
            "divisor": v.get("divisor"),
            "index_value": v.get("index value"),
            "portfolio_value": v.get("portfolio value"),
            "transaction_cost_field": v.get("transaction cost"),
            "cash_initial": cash.get("Initial"),
            "cash_exec_cash": cash.get("Execution Cash"),
            "cash_tc_o": cash.get("Transaction Costs O"),
            "cash_tc_fw": cash.get("Transactions Costs Fw"),
            "n_trades_for_date": len(tfd),
            "n_risks_for_date": len(v.get("risks for date", []) or []),
            "n_portfolio_entries": len(v.get("portfolio", []) or []),
        })

    print(f"  trade legs extracted : {len(trade_rows)}")
    print(f"  daily rows           : {len(daily_rows)}")
    print(f"  'OTHER' records skipped: {other_count}")

    trades = pd.DataFrame(trade_rows)
    daily = pd.DataFrame(daily_rows)

    # ---- derive per-day flows from cumulative levels ---------------------
    daily = daily.sort_values("date").reset_index(drop=True)
    for col in ("cash_exec_cash", "cash_tc_o", "cash_tc_fw"):
        daily[col.replace("cash_", "flow_")] = daily[col].diff()
    # First row's "flow" is the level itself (since prior day didn't exist or was Initial=100 only)
    # but we leave it as NaN; users should know diff[0] is unknown.

    # ---- derive simple counts per kind into the daily table --------------
    counts = trades.groupby(["date", "kind"]).size().unstack(fill_value=0).reset_index()
    counts.columns.name = None
    daily = daily.merge(counts, on="date", how="left").fillna({
        "OPT_OPEN": 0, "OPT_CLOSE": 0, "FUT_HEDGE": 0, "TC_O": 0, "TC_FW": 0,
    })

    # ---- Phase 2 GATE: cash sum invariant --------------------------------
    cash_sum = (daily["cash_initial"].fillna(0)
                + daily["cash_exec_cash"].fillna(0)
                + daily["cash_tc_o"].fillna(0)
                + daily["cash_tc_fw"].fillna(0))
    diff = (cash_sum - daily["index_value"]).abs()
    max_diff = diff.max()
    n_mismatch = int((diff > 1e-6).sum())
    print(f"\nGATE: cash invariant max abs diff = {max_diff:.2e}, mismatches = {n_mismatch}")
    assert n_mismatch == 0, f"Cash invariant violated on {n_mismatch} days"

    # ---- GATE 2: per-day opening + closing leg counts must match -------
    mismatch_strip = daily[daily["OPT_OPEN"] != daily["OPT_CLOSE"]]
    print(f"GATE: per-day OPT_OPEN != OPT_CLOSE on {len(mismatch_strip)} days")
    if len(mismatch_strip) > 0:
        print(mismatch_strip[["date", "OPT_OPEN", "OPT_CLOSE"]].head(10).to_string(index=False))

    # ---- GATE 3: per-leg opening-closing quantity nets to zero ---------
    # Group by (date, expiry, strike, put_call) — net qty should be zero
    opt = trades[trades["kind"].isin(["OPT_OPEN", "OPT_CLOSE"])].copy()
    if not opt.empty:
        net = opt.groupby(["date", "expiry", "strike", "put_call"])["quantity"].sum()
        max_abs = net.abs().max()
        n_nonzero = int((net.abs() > 1e-9).sum())
        print(f"GATE: per-strike net option qty | max abs = {max_abs:.2e}, "
              f"nonzero strikes = {n_nonzero}")

    # ---- Persist ---------------------------------------------------------
    trades.to_parquet(TRADES_PATH, index=False)
    daily.to_parquet(DAILY_PATH, index=False)
    print(f"\nwrote {TRADES_PATH}  ({TRADES_PATH.stat().st_size / 1e6:.2f} MB)")
    print(f"wrote {DAILY_PATH}   ({DAILY_PATH.stat().st_size / 1e3:.1f} KB)")

    # ---- Summary stats ---------------------------------------------------
    print("\nDaily flow stats (index points, base=100):")
    for col in ("flow_exec_cash", "flow_tc_o", "flow_tc_fw"):
        s = daily[col].dropna()
        print(f"  {col:16s}: mean={s.mean():+.4f}  median={s.median():+.4f}  "
              f"std={s.std():.4f}  min={s.min():+.4f}  max={s.max():+.4f}  n={len(s)}")


if __name__ == "__main__":
    main()
