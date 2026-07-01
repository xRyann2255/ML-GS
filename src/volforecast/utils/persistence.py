"""Experiment result persistence: models, predictions, metrics, config.

Saves experiment artifacts to a structured directory under data/models/.
Includes fingerprinting to detect config/data changes and skip retraining.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from volforecast.config import ExperimentConfig
from volforecast.utils.paths import models_dir


def experiment_dir(config: ExperimentConfig) -> Path:
    """Return the experiment output directory (absolute)."""
    return models_dir() / config.name


def save_experiment_results(
    results: dict[int, Any],
    config: ExperimentConfig,
    symbol: str,
) -> Path:
    """Persist pipeline results for one symbol.

    Writes:
      - {experiment_dir}/{symbol}/{model}_h{horizon}.joblib (fitted model)
      - {experiment_dir}/{symbol}/predictions_h{horizon}.csv (OOS preds + actuals)
      - Updates {experiment_dir}/metrics.json with this symbol's metrics

    Parameters
    ----------
    results : dict[int, Any]
        Output from Pipeline.run() — keys are horizon ints.
    config : ExperimentConfig
        The experiment configuration (used for naming).
    symbol : str
        Ticker symbol this result corresponds to.

    Returns
    -------
    Path
        The symbol's output directory.
    """
    exp_dir = experiment_dir(config)
    sym_dir = exp_dir / symbol
    sym_dir.mkdir(parents=True, exist_ok=True)

    # Save config snapshot (once per experiment)
    config_path = exp_dir / "config.yaml"
    if not config_path.exists():
        config.to_yaml(config_path)

    # Per-horizon artifacts
    all_metrics: dict[str, dict[str, dict[str, float]]] = _load_metrics(exp_dir)
    if symbol not in all_metrics:
        all_metrics[symbol] = {}

    for h, result in results.items():
        # Save model
        model = result["model"]
        if hasattr(model, "save"):
            model.save(sym_dir / f"{config.model.name}_h{h}.joblib")

        # Save predictions + actuals
        preds = result["predictions"]
        pred_data = {"prediction": preds.values}
        if "actuals" in result:
            pred_data["actual"] = result["actuals"].values
        pred_df = pd.DataFrame(pred_data, index=preds.index)
        pred_df.index.name = "date"
        pred_df.to_csv(sym_dir / f"predictions_h{h}.csv")

        # Collect metrics
        all_metrics[symbol][str(h)] = result["metrics"]

    # Write consolidated metrics
    _save_metrics(all_metrics, exp_dir)

    return sym_dir


def load_predictions(config: ExperimentConfig, symbol: str, horizon: int) -> pd.DataFrame:
    """Load saved OOS predictions for a symbol/horizon.

    Returns DataFrame with 'prediction' and 'actual' columns and date index.
    """
    path = experiment_dir(config) / symbol / f"predictions_h{horizon}.csv"
    if not path.exists():
        raise FileNotFoundError(f"No predictions found at {path}")
    df = pd.read_csv(path, index_col="date", parse_dates=True)
    return df


def load_all_metrics(config: ExperimentConfig) -> dict[str, dict[str, dict[str, float]]]:
    """Load the consolidated metrics.json for an experiment."""
    return _load_metrics(experiment_dir(config))


def _load_metrics(exp_dir: Path) -> dict[str, dict[str, dict[str, float]]]:
    """Load metrics.json or return empty dict."""
    metrics_path = exp_dir / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path) as f:
            return json.load(f)
    return {}


def _save_metrics(metrics: dict, exp_dir: Path) -> None:
    """Write metrics.json with pretty formatting."""
    exp_dir.mkdir(parents=True, exist_ok=True)
    with open(exp_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2, default=_json_default)


def _json_default(obj):
    """Handle numpy types in JSON serialization."""
    if isinstance(obj, (np.floating, np.integer)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# ─── Fingerprinting: detect config/data changes to skip retraining ───


def _canon_sequences(sequences) -> dict | None:
    """Canonical representation of SequenceConfig (or raw dict / None) for hashing."""
    if sequences is None:
        return None
    if isinstance(sequences, dict):
        # Raw-dict path (occasionally seen in older tests): normalise keys.
        return {
            "features": list(sequences.get("features", []) or []),
            "max_bars": int(sequences.get("max_bars", 0) or 0),
        }
    return {
        "features": list(getattr(sequences, "features", []) or []),
        "max_bars": int(getattr(sequences, "max_bars", 0) or 0),
    }


def _canon_base_model(base_model) -> dict | None:
    """Canonical representation of BaseModelConfig for hashing."""
    if base_model is None:
        return None
    return {
        "name": str(base_model.name),
        "feature_layers": sorted(base_model.feature_layers or []),
        "params": dict(base_model.params or {}),
    }


def _canon_horizon_overrides(overrides: dict) -> dict:
    """Canonical representation of horizon_overrides (preserve nested structure)."""
    canon: dict = {}
    for h, ov in sorted((overrides or {}).items(), key=lambda kv: int(kv[0])):
        entry: dict = {}
        if "model" in ov:
            entry["model"] = {
                "params": dict((ov["model"] or {}).get("params", {}) or {}),
            }
        if "cv" in ov:
            entry["cv"] = dict(ov["cv"] or {})
        if "base_model" in ov:
            bm = ov["base_model"] or {}
            entry["base_model"] = {
                "name": bm.get("name"),
                "feature_layers": sorted(bm.get("feature_layers", []) or []),
                "params": dict(bm.get("params", {}) or {}),
            }
        canon[int(h)] = entry
    return canon


def _config_fingerprint(config: ExperimentConfig) -> str:
    """Compute a stable hash of all training-relevant config fields.

    Excludes output_dir, ingest, and cache-control settings since they don't
    affect model training. Includes sequence spec, base model, and horizon
    overrides so sequence-model and stacked-model runs invalidate the cache
    correctly.
    """
    # Build a canonical dict of training-relevant fields
    relevant = {
        "name": config.name,
        "universe": sorted(config.universe),
        "date_range": list(config.date_range),
        "horizons": sorted(config.horizons),
        "feature_layers": sorted(config.feature_layers),
        "model_name": config.model.name,
        "model_params": config.model.params,
        "cv_method": config.cv.method,
        "cv_n_splits": config.cv.n_splits,
        "cv_purge_gap": config.cv.purge_gap,
        "cv_train_size": config.cv.train_size,
        "cv_test_size": config.cv.test_size,
        "tuning_enabled": config.tuning.enabled,
        "tuning_n_trials": config.tuning.n_trials,
        "tuning_min_train_size": config.tuning.min_train_size,
        "tuning_tune_every_n_folds": config.tuning.tune_every_n_folds,
        "training_mode": config.training_mode,
        "seed": config.seed,
        "sequences": _canon_sequences(config.sequences),
        "base_model": _canon_base_model(config.base_model),
        "horizon_overrides": _canon_horizon_overrides(config.horizon_overrides),
    }
    canon = json.dumps(relevant, sort_keys=True, default=str)
    return hashlib.sha256(canon.encode()).hexdigest()


def _data_fingerprint(symbol: str) -> str:
    """Compute a hash of a symbol's data file (size + mtime + first/last bytes).

    Uses file metadata + content sample for speed (avoids hashing multi-MB files).
    """
    from volforecast.utils.paths import rv_cache_path

    path = rv_cache_path(symbol)
    if not path.exists():
        return "missing"

    stat = path.stat()
    # Read first and last 4KB for a content sample
    with open(path, "rb") as f:
        head = f.read(4096)
        f.seek(max(0, stat.st_size - 4096))
        tail = f.read(4096)

    content = f"{stat.st_size}:{stat.st_mtime_ns}".encode() + head + tail
    return hashlib.sha256(content).hexdigest()


def compute_fingerprint(config: ExperimentConfig, symbols: list[str]) -> dict[str, str]:
    """Compute a full experiment fingerprint (config + per-symbol data).

    Returns a dict with 'config' hash and per-symbol data hashes.
    """
    fp: dict[str, str] = {"config": _config_fingerprint(config)}
    for sym in sorted(symbols):
        fp[f"data:{sym}"] = _data_fingerprint(sym)
    return fp


def save_fingerprint(config: ExperimentConfig, symbols: list[str]) -> Path:
    """Save fingerprint to the experiment directory."""
    exp_dir = experiment_dir(config)
    exp_dir.mkdir(parents=True, exist_ok=True)
    fp = compute_fingerprint(config, symbols)
    fp_path = exp_dir / "fingerprint.json"
    with open(fp_path, "w") as f:
        json.dump(fp, f, indent=2)
    return fp_path


def load_fingerprint(config: ExperimentConfig) -> dict[str, str] | None:
    """Load a previously saved fingerprint, or None if not found."""
    fp_path = experiment_dir(config) / "fingerprint.json"
    if not fp_path.exists():
        return None
    with open(fp_path) as f:
        return json.load(f)


def check_fingerprint(config: ExperimentConfig, symbols: list[str]) -> tuple[bool, str]:
    """Check if the current config+data matches the saved fingerprint.

    Returns
    -------
    (matches, reason) : tuple[bool, str]
        matches=True if fingerprints are identical.
        reason explains what changed if matches=False.
    """
    saved = load_fingerprint(config)
    if saved is None:
        return False, "no previous fingerprint found"

    current = compute_fingerprint(config, symbols)

    # Check config hash
    if saved.get("config") != current.get("config"):
        return False, "config changed"

    # Check per-symbol data hashes
    for key in current:
        if key.startswith("data:"):
            if saved.get(key) != current[key]:
                sym = key.split(":", 1)[1]
                return False, f"data changed for {sym}"

    # Check if saved had symbols not in current (universe shrank)
    for key in saved:
        if key.startswith("data:") and key not in current:
            sym = key.split(":", 1)[1]
            return False, f"symbol {sym} removed from universe"

    return True, "config and data unchanged"


def has_trained_artifacts(config: ExperimentConfig, symbol: str) -> bool:
    """Check if a symbol has complete trained artifacts (predictions for all horizons)."""
    exp_dir = experiment_dir(config)
    sym_dir = exp_dir / symbol
    if not sym_dir.exists():
        return False
    for h in config.horizons:
        if not (sym_dir / f"predictions_h{h}.csv").exists():
            return False
    return True
