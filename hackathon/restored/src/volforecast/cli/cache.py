"""CLI handlers for the per-fold LSTM training cache.

Subcommands:
- ``vol cache-status [--config <yaml>]`` — list cached folds and disk usage.
- ``vol cache-clear  [--config <yaml> | --all]`` — delete cached folds.

The cache is populated automatically by ``vol run --config`` whenever
``fold_cache_enabled: true`` (the default) and the runner trains a sequence
model fold. See ``src/volforecast/pipeline/fold_cache.py`` for the storage
layout.

When ``--config`` points at a tournament config (i.e. ``tournament.models`` is
set or ``model.requires_sequences`` is True), the CLI expands the parent into
the per-model SYNTHETIC configs that the pooled tournament workers build at
runtime. The cache is fingerprinted on those synthetic configs (not the
parent), so naive parent-config lookups would always show ``(no cached
folds)``. See ``volforecast.evaluation._parallel.build_tournament_model_config``.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def register(subparsers) -> None:
    status_p = subparsers.add_parser(
        "cache-status",
        help="List cached fold artifacts (per-fold LSTM training cache)",
    )
    status_p.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Filter to one experiment config (YAML); default = all configs.",
    )
    status_p.set_defaults(func=_handle_status)

    clear_p = subparsers.add_parser(
        "cache-clear",
        help="Delete cached fold artifacts (use --all for the entire cache)",
    )
    group = clear_p.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Clear cache entries for one experiment config (YAML).",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Clear the entire fold cache root.",
    )
    clear_p.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt.",
    )
    clear_p.set_defaults(func=_handle_clear)


def _load_config(path: Path):
    from volforecast.config import ExperimentConfig

    return ExperimentConfig.from_yaml(path)


def _expand_to_tournament_configs(parent) -> list:
    """Return the list of synthetic configs the pooled tournament workers will
    build for ``parent`` (one per model in ``parent.effective_models``).

    Each synthetic config has the same training-relevant fields as a worker's
    ``ExperimentConfig`` and therefore the same fold-cache fingerprint.

    Falls back to ``[parent]`` for per-symbol training or when no models are
    configured (treat the parent itself as the lookup target).
    """
    from volforecast.evaluation._parallel import build_tournament_model_config

    if parent.training_mode != "pooled":
        return [parent]

    models = list(parent.effective_models)
    if not models:
        return [parent]

    synth: list = []
    model_params = (
        {parent.model.name: parent.model.params} if parent.model.params else None
    )
    model_configs = parent.tournament.model_configs or None
    for label in models:
        try:
            _, _, cfg = build_tournament_model_config(
                model_label=label,
                universe=parent.universe,
                date_range=parent.date_range,
                horizons=parent.horizons,
                feature_layers=parent.feature_layers,
                cv_config=parent.cv,
                tuning_config=parent.tuning,
                model_params=model_params,
                model_configs=model_configs,
                horizon_overrides=parent.horizon_overrides,
                sequences=parent.sequences,
                base_model=parent.base_model,
            )
        except Exception as exc:  # noqa: BLE001 — best-effort enumeration
            print(f"  (warning: could not build synthetic config for {label!r}: {exc})")
            continue
        synth.append(cfg)
    return synth


def _handle_status(args: argparse.Namespace) -> int:
    from volforecast.pipeline.fold_cache import list_cached_folds, resolve_cache_root

    parent = _load_config(args.config) if args.config else None
    root = resolve_cache_root(parent)
    print(f"Cache root: {root}")

    if parent is None:
        entries = list_cached_folds(None)
    else:
        entries = []
        seen_keys: set[tuple[str, str]] = set()
        for cfg in _expand_to_tournament_configs(parent):
            for e in list_cached_folds(cfg):
                k = (str(e.get("config_dir")), str(e.get("key")))
                if k in seen_keys:
                    continue
                seen_keys.add(k)
                entries.append(e)

    if not entries:
        print("(no cached folds)")
        return 0

    total_bytes = sum(int(e.get("preds_bytes", 0) or 0) for e in entries)
    print(f"Cached folds: {len(entries)} ({total_bytes / 1024:.1f} KiB preds)")
    print(
        f"  {'config':<18}  {'key':<26}  {'model':<14}  h  fold  n_test  duan       "
    )
    for e in sorted(
        entries,
        key=lambda x: (str(x.get("config_dir")), int(x.get("h") or 0), int(x.get("fold") or 0)),
    ):
        print(
            f"  {str(e.get('config_dir'))[:18]:<18}  "
            f"{str(e.get('key'))[:26]:<26}  "
            f"{str(e.get('model_name') or ''):<14}  "
            f"{e.get('h')}  {e.get('fold'):>4}  {e.get('n_test'):>6}  "
            f"{float(e.get('duan_correction') or 0.0):+.4f}"
        )
    return 0


def _handle_clear(args: argparse.Namespace) -> int:
    from volforecast.pipeline.fold_cache import clear_fold_cache, resolve_cache_root

    if args.all:
        root = resolve_cache_root(None)
        target_desc = f"the ENTIRE fold cache at {root}"
        configs_to_clear: list | None = None
    else:
        parent = _load_config(args.config)
        root = resolve_cache_root(parent)
        configs_to_clear = _expand_to_tournament_configs(parent)
        n_synth = len(configs_to_clear)
        target_desc = (
            f"fold cache entries for {n_synth} tournament-model "
            f"config{'s' if n_synth != 1 else ''} under {parent.name!r} at {root}"
        )

    if not args.yes:
        resp = input(f"Delete {target_desc}? [y/N] ").strip().lower()
        if resp not in ("y", "yes"):
            print("Aborted.")
            return 1

    if configs_to_clear is None:
        n = clear_fold_cache(None)
    else:
        n = 0
        for cfg in configs_to_clear:
            n += clear_fold_cache(cfg)
    print(f"Cleared {n} cached fold entries.")
    return 0
