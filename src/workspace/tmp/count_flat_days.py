import json, re, sys
from collections import Counter

# Read the dashboard HTML and extract gsvivsPnlTraces
html_path = "src/workspace/tmp/results/plots/tournament_dashboard.html"
with open(html_path, "r") as f:
    content = f.read()

# Find the gsvivsPnlTraces JSON
m = re.search(r'const gsvivsPnlTraces = ({.*?});', content, re.DOTALL)
if not m:
    print("ERROR: Could not find gsvivsPnlTraces"); sys.exit(1)

traces = json.loads(m.group(1))

# Focus on horizon 1 traces
for trace in traces.get("1", []):
    name = trace.get("name", "")
    if "xgboost" not in name and "har_iv_0dte" not in name:
        continue
    if "_signal_y" not in trace:
        continue
    
    signals = trace["_signal_y"]
    dates = trace["_signal_x"]
    total = len(signals)
    
    # Count flat days (signal == 0 for long_flat, signal == -1 for binary)
    c = Counter()
    for s in signals:
        if s == 0.0:
            c["flat"] += 1
        elif s == 1.0:
            c["long"] += 1
        elif s == -1.0:
            c["short"] += 1
        else:
            c["sized"] += 1  # fractional sizing

    # Date range
    start = dates[0]
    end = dates[-1]
    
    # Count by year
    from collections import defaultdict
    yearly = defaultdict(lambda: {"flat": 0, "long": 0, "short": 0, "sized": 0, "total": 0})
    for d, s in zip(dates, signals):
        yr = d[:4]
        yearly[yr]["total"] += 1
        if s == 0.0:
            yearly[yr]["flat"] += 1
        elif s == 1.0:
            yearly[yr]["long"] += 1
        elif s == -1.0:
            yearly[yr]["short"] += 1
        else:
            yearly[yr]["sized"] += 1
    
    print(f"\n=== {name} ===")
    print(f"Period: {start} to {end} ({total} trading days)")
    print(f"Overall: flat={c['flat']}, long={c['long']}, short={c['short']}, sized={c['sized']}")
    
    if "long_flat" in name:
        flat_pct = c['flat'] / total * 100
        print(f"Flat rate: {flat_pct:.1f}%")
    
    print(f"\nPer-year breakdown:")
    print(f"{'Year':>6} {'Total':>6} {'Flat':>6} {'Long':>6} {'Short':>6} {'Sized':>6} {'Flat%':>8}")
    for yr in sorted(yearly.keys()):
        y = yearly[yr]
        flat_pct = y['flat'] / y['total'] * 100 if y['total'] > 0 else 0
        print(f"{yr:>6} {y['total']:>6} {y['flat']:>6} {y['long']:>6} {y['short']:>6} {y['sized']:>6} {flat_pct:>7.1f}%")
    
    if "long_flat" in name:
        avg_flat = c['flat'] / len(yearly) if yearly else 0
        print(f"\nAverage flat days per year: {avg_flat:.1f}")
