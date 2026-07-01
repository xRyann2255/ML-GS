"""CLI commands for experiment management.

Provides:
    vol experiments          — List all trials from registry
    vol new-experiment       — Create a new experiment config from baseline
    vol compare              — Compare two trials side-by-side
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Registry lives at project root
_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # src/volforecast/cli -> project root
TRIALS_PATH = _PROJECT_ROOT / "workspace" / "research" / "trials.yaml"


def _load_trials() -> list[dict]:
    """Load trials from YAML registry."""
    import yaml

    if not TRIALS_PATH.exists():
        print(f"ERROR: Trial registry not found at {TRIALS_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(TRIALS_PATH) as f:
        data = yaml.safe_load(f)

    return data.get("trials", [])


def cmd_experiments(args: argparse.Namespace) -> int:
    """List all experiments from the trial registry."""
    trials = _load_trials()

    if not trials:
        print("No trials found in registry.")
        return 0

    # Header
    print(
        f"{'ID':<12} {'Date':<12} {'Status':<14} {'h1 QLIKE':<10} {'h5 QLIKE':<10} {'h22 QLIKE':<10} {'Hypothesis'}"
    )
    print("-" * 100)

    for t in trials:
        trial_id = t.get("id", "?")
        date = t.get("date") or "-"
        status = t.get("status", "?")
        horizons = t.get("horizons", {})

        h1 = horizons.get("h1", {}).get("qlike", "-")
        h5 = horizons.get("h5", {}).get("qlike", "-")
        h22 = horizons.get("h22", {}).get("qlike", "-")

        h1_str = f"{h1:.4f}" if isinstance(h1, (int, float)) else str(h1)
        h5_str = f"{h5:.4f}" if isinstance(h5, (int, float)) else str(h5)
        h22_str = f"{h22:.4f}" if isinstance(h22, (int, float)) else str(h22)

        hypothesis = t.get("hypothesis", "")[:40]

        print(
            f"{trial_id:<12} {date:<12} {status:<14} {h1_str:<10} {h5_str:<10} {h22_str:<10} {hypothesis}"
        )

    # Summary
    completed = [t for t in trials if t.get("status") == "completed"]
    not_started = [t for t in trials if t.get("status") == "NOT_STARTED"]
    print(f"\n{len(completed)} completed, {len(not_started)} pending")

    return 0


def cmd_new_experiment(args: argparse.Namespace) -> int:
    """Create a new experiment config by cloning and patching a baseline."""
    import yaml

    # Resolve base config
    base_path = Path(args.base)
    if not base_path.is_absolute():
        base_path = _PROJECT_ROOT / base_path

    if not base_path.exists():
        print(f"ERROR: Base config not found: {base_path}", file=sys.stderr)
        return 1

    with open(base_path) as f:
        config = yaml.safe_load(f)

    # Apply --set overrides (key=value pairs, dot-notation)
    if args.set:
        for kv in args.set:
            if "=" not in kv:
                print(f"ERROR: --set expects key=value, got: {kv}", file=sys.stderr)
                return 1
            key, value = kv.split("=", 1)

            # Try to parse value as number/bool
            parsed_value: object
            if value.lower() in ("true", "false"):
                parsed_value = value.lower() == "true"
            else:
                try:
                    parsed_value = int(value)
                except ValueError:
                    try:
                        parsed_value = float(value)
                    except ValueError:
                        parsed_value = value

            # Navigate dot-notation path
            parts = key.split(".")
            target = config
            for part in parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]
            target[parts[-1]] = parsed_value

    # Determine output path
    configs_dir = _PROJECT_ROOT / "workspace" / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    out_path = configs_dir / f"{args.name}.yaml"

    if out_path.exists() and not args.force:
        print(f"ERROR: Config already exists: {out_path}", file=sys.stderr)
        print("  Use --force to overwrite.", file=sys.stderr)
        return 1

    # Auto-update name and output_dir to match new experiment name
    config["name"] = args.name
    config["output_dir"] = f"data/models/{args.name}"

    with open(out_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"Created: {out_path}")
    print(f"Base: {base_path}")
    if args.set:
        print(f"Overrides: {', '.join(args.set)}")
    print(f"\nRun with: ./vol run --config {out_path.relative_to(_PROJECT_ROOT)}")

    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Compare two trials from the registry."""
    trials = _load_trials()

    # Find the two trials
    trial_map = {t["id"]: t for t in trials}

    if args.experiment not in trial_map:
        print(f"ERROR: Trial '{args.experiment}' not found in registry.", file=sys.stderr)
        return 1
    if args.baseline not in trial_map:
        print(f"ERROR: Trial '{args.baseline}' not found in registry.", file=sys.stderr)
        return 1

    exp = trial_map[args.experiment]
    base = trial_map[args.baseline]

    if exp.get("status") != "completed":
        print(f"WARNING: {args.experiment} status is '{exp.get('status')}' (not completed)")
    if base.get("status") != "completed":
        print(f"WARNING: {args.baseline} status is '{base.get('status')}' (not completed)")

    print(f"\nComparing: {args.experiment} vs {args.baseline} (baseline)")
    print(f"  Experiment: {exp.get('hypothesis', 'N/A')}")
    print(f"  Baseline:   {base.get('hypothesis', 'N/A')}")
    print()

    # Compare horizons
    print(f"{'Horizon':<10} {'Experiment':<12} {'Baseline':<12} {'Diff (bps)':<12} {'Verdict'}")
    print("-" * 60)

    for h in ["h1", "h5", "h22"]:
        exp_h = exp.get("horizons", {}).get(h, {})
        base_h = base.get("horizons", {}).get(h, {})

        exp_qlike = exp_h.get("qlike")
        base_qlike = base_h.get("qlike")

        if exp_qlike is not None and base_qlike is not None:
            # Negative bps = improvement (lower QLIKE is better)
            diff_bps = int((exp_qlike - base_qlike) / base_qlike * 10000)
            verdict = exp_h.get("verdict", "?")
            print(f"{h:<10} {exp_qlike:<12.4f} {base_qlike:<12.4f} {diff_bps:>+8}     {verdict}")
        else:
            print(f"{h:<10} {'N/A':<12} {'N/A':<12} {'N/A':<12}")

    # Key insight
    if exp.get("key_insight"):
        print(f"\nKey insight: {exp['key_insight']}")

    return 0


def register_experiment_parsers(subparsers: argparse._SubParsersAction) -> None:
    """Register experiment subcommands on an existing argparse subparsers object."""
    # vol experiments
    exp_list = subparsers.add_parser(
        "experiments", help="List all trials from the experiment registry"
    )
    exp_list.set_defaults(func=cmd_experiments)

    # vol new-experiment
    new_exp = subparsers.add_parser(
        "new-experiment",
        help="Create a new experiment config from a baseline",
        description="Clone a baseline config, apply parameter overrides, and save.",
    )
    new_exp.add_argument("--base", required=True, help="Path to baseline YAML config")
    new_exp.add_argument("--name", required=True, help="Name for the new config (without .yaml)")
    new_exp.add_argument(
        "--set",
        nargs="*",
        metavar="KEY=VALUE",
        help="Parameter overrides in dot.notation=value format",
    )
    new_exp.add_argument("--force", action="store_true", help="Overwrite existing config")
    new_exp.set_defaults(func=cmd_new_experiment)

    # vol compare
    compare = subparsers.add_parser("compare", help="Compare two trials side-by-side")
    compare.add_argument("--experiment", required=True, help="Trial ID to evaluate")
    compare.add_argument("--baseline", required=True, help="Trial ID to compare against")
    compare.set_defaults(func=cmd_compare)


def update_trial_from_metrics(config_basename: str, metrics_path: Path) -> bool:
    """Update a NOT_STARTED trial in the registry with results from metrics.json.

    Finds the trial whose config field matches config_basename. If found and
    status is NOT_STARTED, fills in horizons and marks as completed.

    Returns True if a trial was updated, False otherwise.
    """
    import json
    from datetime import date

    import yaml

    if not TRIALS_PATH.exists() or not metrics_path.exists():
        return False

    with open(TRIALS_PATH) as f:
        data = yaml.safe_load(f)

    trials = data.get("trials", [])
    updated = False

    with open(metrics_path) as f:
        metrics = json.load(f)

    # Find matching trial by config basename (with or without .yaml)
    for trial in trials:
        trial_config = trial.get("config")
        if not trial_config:
            continue
        # Match on filename (strip path, compare with and without .yaml)
        trial_config_stem = Path(trial_config).stem
        config_stem = Path(config_basename).stem
        if trial_config_stem != config_stem:
            continue
        if trial.get("status") != "NOT_STARTED":
            continue

        # Found a matching NOT_STARTED trial — fill in results
        # Use the first model's metrics (primary model in single-model experiments)
        # or all models if multiple
        model_names = list(metrics.keys())
        if not model_names:
            continue

        # For the primary model (first one), extract per-horizon metrics
        primary_model = model_names[0]
        model_metrics = metrics[primary_model]

        # Find baseline trial for bps comparison
        baseline_config = trial.get("baseline_config")
        baseline_qlike: dict[str, float] = {}
        if baseline_config:
            for t in trials:
                if t.get("config") == baseline_config and t.get("status") == "completed":
                    for h_key, h_data in t.get("horizons", {}).items():
                        if isinstance(h_data, dict) and "qlike" in h_data:
                            baseline_qlike[h_key] = h_data["qlike"]
                    break

        horizons: dict[str, dict] = {}
        for h_str, h_metrics in model_metrics.items():
            qlike = h_metrics.get("qlike")
            if qlike is None:
                continue
            h_key = f"h{h_str}"
            h_result: dict = {"qlike": round(qlike, 4)}

            # Compute bps vs baseline if available
            base_q = baseline_qlike.get(h_key)
            if base_q and base_q > 0:
                bps = int((qlike - base_q) / base_q * 10000)
                h_result["vs_har_bps"] = bps
                # Verdict: PASS if QLIKE improved (negative bps)
                h_result["verdict"] = "PASS" if bps < 0 else "FAIL"
            else:
                h_result["verdict"] = "COMPLETED"

            # Include DM p-value if available
            dm_p = h_metrics.get("dm_pvalue")
            if dm_p is not None and dm_p < 1.0:
                h_result["dm_p"] = round(dm_p, 4)

            horizons[h_key] = h_result

        trial["horizons"] = horizons
        trial["status"] = "completed"
        trial["date"] = date.today().isoformat()
        updated = True
        break  # Only update first match

    if updated:
        with open(TRIALS_PATH, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        print(f"\n  Trial registry updated: {config_basename} → completed")

    return updated
