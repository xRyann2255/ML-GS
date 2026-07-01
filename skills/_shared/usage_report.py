"""Read workspace/tmp/skill_usage.log and print aggregated counts.

Usage:
    python skills/_shared/usage_report.py
    python skills/_shared/usage_report.py --since 2026-04-01
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

LOG = Path(__file__).resolve().parents[2] / "workspace" / "tmp" / "skill_usage.log"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", help="Only count entries on or after this date (YYYY-MM-DD)")
    args = ap.parse_args()

    if not LOG.exists():
        print("No usage log found at", LOG)
        return 1

    counts: Counter[str] = Counter()
    for line in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue
        if args.since and parts[0][:10] < args.since:
            continue
        counts[parts[1]] += 1

    if not counts:
        print("No entries found.")
        return 0

    print(f"{'Skill':<30} {'Count':>6}")
    print("-" * 38)
    for skill, count in counts.most_common():
        print(f"{skill:<30} {count:>6}")
    print("-" * 38)
    print(f"{'TOTAL':<30} {sum(counts.values()):>6}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
