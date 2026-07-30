"""Per-fold training cache for sequence models (LSTM/TCN).

Skips fold-level training when an identical fold has already been trained
under the same config + data + CV split + base-model predictions. Cache is
keyed on a deterministic fingerprint of every input that affects the trained
model's outputs, so any change (model params, sequence features, train dates,
base preds) invalidates the relevant entries automatically.

Storage layout (under ``data/models/lstm_cache/{config_fp16}/{cache_key}/``):
  - ``preds.npy``  — final test predictions (Duan correction already applied)
  - ``model.pt``   — fitted model state (best-effort; absent if save fails)
  - ``meta.json``  — fold metadata + Duan correction + diagnostic info

The runner consults this cache in ``_run_one_horizon_sequences``; CLI helpers
(``vol cache-status``/``vol cache-clear``) report and clear entries.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from volforecast.config import ExperimentConfig
from volforecast.utils.paths import models_dir

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------


def _hash_dates(dates: pd.DatetimeIndex) -> str:
    """Stable 16-hex hash of a date index (order-independent, dedup'd)."""
    unique_iso = sorted({pd.Timestamp(d).isoformat() for d in dates})
    payload = ";".join(unique_iso).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _hash_array(arr: np.ndarray | None) -> str:
    """Stable 16-hex hash of a numpy array (or ``"none"`` when ``arr is None``)."""
    if arr is None:
        return "none"
    arr = np.ascontiguousarray(np.asarray(arr, dtype=np.float64))
    return hashlib.sha256(arr.tobytes()).hexdigest()[:16]


def resolve_cache_root(
    config: ExperimentConfig | None = None,
    cache_root: Path | None = None,
) -> Path:
    """Resolve the on-disk cache root directory.

    Priority: explicit ``cache_root`` arg > ``config.fold_cache_dir`` >
    ``data/models/lstm_cache``.
    """
    if cache_root is not None:
        return Path(cache_root)
    if config is not None and getattr(config, "fold_cache_dir", None):
        return Path(config.fold_cache_dir)  # type: ignore[arg-type]
    return models_dir() / "lstm_cache"


def config_subdir(config: ExperimentConfig) -> str:
    """Short config-fingerprint directory name (groups all folds for one config)."""
    from volforecast.utils.persistence import _config_fingerprint

    return _config_fingerprint(config)[:16]


def compute_fold_cache_key(
    config: ExperimentConfig,
    h: int,
    fold_num: int,
    train_dates: pd.DatetimeIndex,
    test_dates: pd.DatetimeIndex,
    *,
    base_preds_train: np.ndarray | None = None,
    base_preds_test: np.ndarray | None = None,
) -> str:
    """Deterministic 24-hex key for one (config, horizon, fold, split) cell.

    Includes hashes of the per-fold base-model predictions (when residual
    stacking is active) so a change in the base model auto-invalidates the
    LSTM cache.
    """
    from volforecast.utils.persistence import _config_fingerprint

    payload = {
        "config_fp": _config_fingerprint(config),
        "h": int(h),
        "fold": int(fold_num),
        "train_dates": _hash_dates(train_dates),
        "test_dates": _hash_dates(test_dates),
        "base_train": _hash_array(base_preds_train),
        "base_test": _hash_array(base_preds_test),
    }
    canon = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:24]


def fold_cache_dir(
    config: ExperimentConfig, key: str, cache_root: Path | None = None
) -> Path:
    """Return the directory holding one fold's cached artifacts."""
    return resolve_cache_root(config, cache_root) / config_subdir(config) / key


# ---------------------------------------------------------------------------
# Atomic IO
# ---------------------------------------------------------------------------


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".tmp", dir=str(path.parent))
    try:
        os.close(fd)
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _serialize_npy(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    np.save(buf, arr)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------


@dataclass
class FoldCacheEntry:
    preds: np.ndarray  # final test predictions (Duan correction already applied)
    duan_correction: float
    model_path: Path | None
    meta: dict


def save_fold_cache(
    *,
    config: ExperimentConfig,
    key: str,
    preds: np.ndarray,
    duan_correction: float,
    model: object | None,
    train_dates: pd.DatetimeIndex,
    test_dates: pd.DatetimeIndex,
    h: int,
    fold_num: int,
    cache_root: Path | None = None,
) -> Path:
    """Persist one fold's artifacts. Best-effort: model save errors are logged but non-fatal."""
    target = fold_cache_dir(config, key, cache_root=cache_root)
    target.mkdir(parents=True, exist_ok=True)

    preds_arr = np.ascontiguousarray(np.asarray(preds, dtype=np.float64))
    _atomic_write_bytes(target / "preds.npy", _serialize_npy(preds_arr))

    meta: dict = {
        "key": key,
        "h": int(h),
        "fold": int(fold_num),
        "duan_correction": float(duan_correction),
        "n_test": int(preds_arr.shape[0]),
        "config_name": str(config.name),
        "model_name": str(config.model.name),
        "train_dates": {
            "first": pd.Timestamp(train_dates.min()).isoformat(),
            "last": pd.Timestamp(train_dates.max()).isoformat(),
            "n": int(pd.DatetimeIndex(train_dates).unique().shape[0]),
        },
        "test_dates": {
            "first": pd.Timestamp(test_dates.min()).isoformat(),
            "last": pd.Timestamp(test_dates.max()).isoformat(),
            "n": int(pd.DatetimeIndex(test_dates).unique().shape[0]),
        },
        "model_saved": False,
    }

    if model is not None and hasattr(model, "save"):
        model_path = target / "model.pt"
        try:
            model.save(model_path)
            meta["model_saved"] = True
            meta["epochs_run"] = getattr(model, "epochs_run_", None)
            meta["best_val_loss"] = getattr(model, "best_val_loss_", None)
        except Exception as exc:  # noqa: BLE001 — model save is best-effort
            meta["save_error"] = repr(exc)
            logger.warning("fold cache %s: model save failed (%s)", key, exc)

    _atomic_write_bytes(
        target / "meta.json",
        json.dumps(meta, indent=2, sort_keys=True, default=str).encode("utf-8"),
    )
    return target


def load_fold_cache(
    *,
    config: ExperimentConfig,
    key: str,
    cache_root: Path | None = None,
) -> FoldCacheEntry | None:
    """Return the cached entry for ``key``, or ``None`` on miss / corruption."""
    target = fold_cache_dir(config, key, cache_root=cache_root)
    meta_path = target / "meta.json"
    preds_path = target / "preds.npy"
    if not meta_path.exists() or not preds_path.exists():
        return None
    try:
        with open(meta_path) as f:
            meta = json.load(f)
        preds = np.load(preds_path)
    except Exception as exc:  # noqa: BLE001 — corrupt cache is a miss
        logger.warning("fold cache %s: load failed (%s); treating as miss", key, exc)
        return None
    model_path = target / "model.pt"
    return FoldCacheEntry(
        preds=preds,
        duan_correction=float(meta.get("duan_correction", 0.0)),
        model_path=model_path if (meta.get("model_saved") and model_path.exists()) else None,
        meta=meta,
    )


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------


def list_cached_folds(
    config: ExperimentConfig | None = None,
    cache_root: Path | None = None,
) -> list[dict]:
    """Inventory of cached fold entries (optionally filtered by config)."""
    root = resolve_cache_root(config, cache_root)
    if not root.exists():
        return []
    entries: list[dict] = []
    config_dirs = (
        [root / config_subdir(config)] if config is not None else list(root.iterdir())
    )
    for cdir in config_dirs:
        if not cdir.is_dir():
            continue
        for fdir in cdir.iterdir():
            meta_path = fdir / "meta.json"
            preds_path = fdir / "preds.npy"
            if not meta_path.exists():
                continue
            try:
                with open(meta_path) as f:
                    meta = json.load(f)
            except Exception:  # noqa: BLE001
                continue
            entries.append(
                {
                    "config_dir": cdir.name,
                    "key": fdir.name,
                    "h": meta.get("h"),
                    "fold": meta.get("fold"),
                    "config_name": meta.get("config_name"),
                    "model_name": meta.get("model_name"),
                    "n_test": meta.get("n_test"),
                    "duan_correction": meta.get("duan_correction"),
                    "preds_bytes": preds_path.stat().st_size if preds_path.exists() else 0,
                    "model_saved": bool(meta.get("model_saved")),
                    "path": str(fdir),
                }
            )
    return entries


def clear_fold_cache(
    config: ExperimentConfig | None = None,
    cache_root: Path | None = None,
) -> int:
    """Delete cached entries for ``config`` (or the whole cache when ``config`` is None).

    Returns the number of fold directories removed.
    """
    root = resolve_cache_root(config, cache_root)
    if not root.exists():
        return 0
    if config is None:
        n = sum(1 for c in root.glob("*/*/meta.json"))
        shutil.rmtree(root)
        return n
    cdir = root / config_subdir(config)
    if not cdir.exists():
        return 0
    n = sum(1 for _ in cdir.glob("*/meta.json"))
    shutil.rmtree(cdir)
    return n
