"""Tournament checkpoint I/O: save/load/list model-level checkpoints.

Each completed model's predictions and actuals are persisted atomically
so that interrupted tournament runs can resume from the last checkpoint.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

import pandas as pd

from volforecast.config import ExperimentConfig
from volforecast.utils.persistence import _config_fingerprint

logger = logging.getLogger(__name__)


def _sanitize_label(label: str) -> str:
    """Sanitize display_label for use as a directory name."""
    return re.sub(r"[^\w\-.]", "_", label)


def checkpoint_dir(output_dir: Path, config: ExperimentConfig) -> Path:
    """Return the checkpoint directory for the given config fingerprint."""
    fp = _config_fingerprint(config)[:16]
    return Path(output_dir) / "checkpoints" / fp


def save_model_checkpoint(
    output_dir: Path,
    config: ExperimentConfig,
    display_label: str,
    preds: dict[int, pd.Series],
    actuals: dict[int, pd.Series],
) -> None:
    """Persist a completed model's predictions and actuals atomically.

    Writes parquet files for each horizon plus a meta.json manifest.
    Uses write-to-tmp + os.replace() for crash safety.

    Skips saving if ALL horizons have empty predictions (failed model run)
    to prevent poisoning subsequent runs with stale empty checkpoints.
    """
    if all(len(s) == 0 for s in preds.values()):
        logger.warning(
            "Skipping checkpoint save for %s: all horizons have empty predictions",
            display_label,
        )
        return

    ckpt = checkpoint_dir(output_dir, config) / _sanitize_label(display_label)
    ckpt.mkdir(parents=True, exist_ok=True)

    horizons_written: list[int] = []

    for h, series in preds.items():
        target = ckpt / f"preds_h{h}.parquet"
        tmp = ckpt / f"preds_h{h}.parquet.tmp"
        series.to_frame().to_parquet(tmp)
        os.replace(tmp, target)
        horizons_written.append(h)

    for h, series in actuals.items():
        target = ckpt / f"actuals_h{h}.parquet"
        tmp = ckpt / f"actuals_h{h}.parquet.tmp"
        series.to_frame().to_parquet(tmp)
        os.replace(tmp, target)

    # Write manifest last — its presence signals a complete checkpoint
    meta = {"display_label": display_label, "horizons": sorted(horizons_written)}
    meta_target = ckpt / "meta.json"
    meta_tmp = ckpt / "meta.json.tmp"
    meta_tmp.write_text(json.dumps(meta))
    os.replace(meta_tmp, meta_target)


def load_model_checkpoint(
    output_dir: Path,
    config: ExperimentConfig,
    display_label: str,
) -> tuple[dict[int, pd.Series], dict[int, pd.Series]] | None:
    """Load a model's checkpoint if it exists and is complete.

    Returns (preds, actuals) dicts keyed by horizon, or None if missing/incomplete.
    """
    ckpt = checkpoint_dir(output_dir, config) / _sanitize_label(display_label)
    meta_path = ckpt / "meta.json"

    if not meta_path.exists():
        return None

    try:
        meta = json.loads(meta_path.read_text())
    except (json.JSONDecodeError, OSError):
        logger.warning("Corrupt checkpoint meta for %s, skipping", display_label)
        return None

    horizons = meta.get("horizons", [])
    preds: dict[int, pd.Series] = {}
    actuals: dict[int, pd.Series] = {}

    for h in horizons:
        pred_path = ckpt / f"preds_h{h}.parquet"
        actual_path = ckpt / f"actuals_h{h}.parquet"

        if not pred_path.exists() or not actual_path.exists():
            logger.warning(
                "Incomplete checkpoint for %s h=%d, skipping entirely",
                display_label,
                h,
            )
            return None

        try:
            pred_df = pd.read_parquet(pred_path)
            actual_df = pd.read_parquet(actual_path)
        except Exception:
            logger.warning(
                "Failed to read checkpoint parquet for %s h=%d",
                display_label,
                h,
                exc_info=True,
            )
            return None

        # Parquet stores as DataFrame; convert back to Series
        preds[h] = pred_df.iloc[:, 0]
        actuals[h] = actual_df.iloc[:, 0]

    # Reject checkpoints where ALL horizons have empty predictions
    # (from a previously failed model run).
    if all(len(s) == 0 for s in preds.values()):
        logger.warning(
            "Checkpoint for %s has empty predictions for all horizons; "
            "ignoring stale checkpoint",
            display_label,
        )
        return None

    return preds, actuals


def list_completed_models(output_dir: Path, config: ExperimentConfig) -> set[str]:
    """Return the set of display labels that have valid checkpoints."""
    ckpt_root = checkpoint_dir(output_dir, config)
    if not ckpt_root.exists():
        return set()

    completed: set[str] = set()
    for entry in ckpt_root.iterdir():
        if not entry.is_dir():
            continue
        meta_path = entry / "meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                label = meta.get("display_label")
                if label:
                    completed.add(label)
            except (json.JSONDecodeError, OSError):
                continue

    return completed
