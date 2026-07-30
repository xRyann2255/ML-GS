"""CLI entry point for live RV forecast and IV-RV gap signal.

Config-driven multi-model ensemble. Loads a YAML config specifying which
models to run, trains each on full available history, predicts next-day
RV, compares to current ATM IV, and outputs weighted LONG/SHORT/FLAT.

Usage:
    vol forecast
    vol forecast --config workspace/configs/forecast_live.yaml
    vol forecast --symbol SPY --horizon 1,5
    vol forecast --live-iv 18.5
    vol forecast --threshold 1.0
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from volforecast.utils.targets import forward_log_rv

logger = logging.getLogger(__name__)

# Default config path (relative to project root)
_DEFAULT_CONFIG = "workspace/configs/forecast_live.yaml"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def _load_rv_data(symbol: str) -> pd.DataFrame:
    """Load tick-derived RV panel from cache."""
    from volforecast.utils.paths import ticks_cache_path

    path = ticks_cache_path(symbol)
    if not path.exists():
        raise FileNotFoundError(f"No RV data for {symbol} at {path}")
    df = pd.read_parquet(path)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"
    return df


def _fetch_live_iv(symbol: str) -> float | None:
    """Attempt to fetch current ATM IV from TSDB.

    Returns IV in vol points (e.g. 18.5 = 18.5%) or None if unavailable.
    """
    try:
        from gs_quant.session import GsSession

        GsSession.use()
        from gs_quant_internal.tsdb import TSDBSymbol

        from volforecast.constants import TICKER_TO_EDRVOL_RIC

        ric = TICKER_TO_EDRVOL_RIC.get(symbol)
        if ric is None:
            return None

        # edrvol_ namespace: 1m ATM IV (field is "1matms")
        tsdb_symbol = f"edrvol_{ric}@1matms"
        data = TSDBSymbol(tsdb_symbol).get_data(
            start=str(date.today()),
            end=str(date.today()),
        )
        if data is not None and len(data) > 0:
            return float(data.iloc[-1])

        # Fallback: fetch yesterday's value
        from datetime import timedelta

        yesterday = date.today() - timedelta(days=3)  # 3 days back for weekends
        data = TSDBSymbol(tsdb_symbol).get_data(
            start=str(yesterday),
            end=str(date.today()),
        )
        if data is not None and len(data) > 0:
            return float(data.iloc[-1])
    except Exception as e:
        logger.warning("TSDB IV fetch failed: %s", e)
    return None


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def load_forecast_config(config_path: str | None = None) -> dict[str, Any]:
    """Load forecast YAML config."""
    from volforecast.utils.paths import resolve_project_root

    if config_path is None:
        config_path = _DEFAULT_CONFIG

    path = Path(config_path)
    if not path.is_absolute():
        path = resolve_project_root() / path

    if not path.exists():
        raise FileNotFoundError(f"Forecast config not found: {path}")

    with open(path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Feature building (reuses pipeline feature layers)
# ---------------------------------------------------------------------------


def _build_features_for_symbol(
    symbol: str,
    feature_layers: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build full feature matrix for a single symbol using pipeline layers.

    Returns (daily_data, X) where X is the feature matrix.
    """
    from volforecast.registry import FEATURE_REGISTRY, ensure_registered

    ensure_registered()

    daily_data = _load_rv_data(symbol)
    context = {"symbol": symbol}

    feature_frames = []
    enriched_data = daily_data.copy()

    for layer_name in feature_layers:
        if layer_name not in FEATURE_REGISTRY:
            logger.warning("Unknown feature layer: %s, skipping", layer_name)
            continue
        layer_cls = FEATURE_REGISTRY[layer_name]
        layer = layer_cls()

        if getattr(layer, "_needs_base_features", False):
            base_df = pd.concat(feature_frames, axis=1) if feature_frames else None
            output = layer.compute(enriched_data, context=context, base_features=base_df)
        else:
            output = layer.compute(enriched_data, context=context)

        if not output.empty:
            enriched_data = pd.concat([enriched_data, output], axis=1)

        if not getattr(layer, "_enrichment_only", False):
            feature_frames.append(output)

    X = (
        pd.concat(feature_frames, axis=1)
        if feature_frames
        else pd.DataFrame(index=daily_data.index)
    )
    return daily_data, X


# ---------------------------------------------------------------------------
# Model training + prediction
# ---------------------------------------------------------------------------


def _train_and_predict_model(
    model_name: str,
    model_type: str,
    model_params: dict[str, Any],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_predict: pd.DataFrame,
) -> float | None:
    """Train a single model on full data and predict the last row.

    Returns log(RV) prediction or None if model fails.
    """
    from volforecast.registry import MODEL_REGISTRY, ensure_registered

    ensure_registered()

    if model_type not in MODEL_REGISTRY:
        logger.warning("Unknown model type: %s", model_type)
        return None

    model_cls = MODEL_REGISTRY[model_type]

    try:
        model = model_cls(**model_params)
        model.fit(X_train, y_train)
        pred = model.predict(X_predict)
        if pred is not None and len(pred) > 0 and not np.isnan(pred[0]):
            return float(pred[0])
    except Exception as e:
        logger.warning("Model %s failed: %s", model_name, e)

    return None


# ---------------------------------------------------------------------------
# Core forecast logic
# ---------------------------------------------------------------------------


def run(
    symbol: str = "SPY",
    horizons: list[int] | None = None,
    threshold: float = 0.0,
    live_iv: float | None = None,
    config_path: str | None = None,
) -> dict[str, dict]:
    """Run multi-model forecast ensemble and produce signal.

    Parameters
    ----------
    symbol : str
        Target symbol for signal generation (default: SPY).
    horizons : list[int]
        Forecast horizons in days. Overrides config if specified.
    threshold : float
        IV-RV gap threshold for signal (vol points).
    live_iv : float, optional
        Manual ATM IV override (vol points). If None, auto-fetches.
    config_path : str, optional
        Path to forecast YAML config.

    Returns
    -------
    dict
        Keys like "h1", "h5" with sub-dicts containing model predictions,
        ensemble forecast, and signal.
    """
    from volforecast.data.edrvol import load_iv_cache

    # Load config
    config = load_forecast_config(config_path)

    if horizons is None:
        horizons = config.get("horizons", [1, 5])
    if threshold == 0.0:
        threshold = config.get("threshold", 0.0)

    feature_layers = config.get("feature_layers", ["har_core", "options"])
    models_config = config.get("models", {})
    horizon_models = config.get("horizon_models", {})
    horizon_overrides = config.get("horizon_overrides", {})
    ref_qlike = config.get("reference_qlike", {})

    # Build features for target symbol
    daily_data, X = _build_features_for_symbol(symbol, feature_layers)
    rv = daily_data["rv"]

    # Get current IV for signal comparison
    if live_iv is not None:
        current_iv = live_iv
    else:
        fetched = _fetch_live_iv(symbol)
        if fetched is not None:
            current_iv = fetched
        else:
            iv_data = load_iv_cache(symbol)
            if iv_data is not None and "iv_1m_atm" in iv_data.columns:
                last_iv = iv_data["iv_1m_atm"].dropna().iloc[-1]
                current_iv = float(last_iv)
                logger.info("Using cached IV: %.2f%%", current_iv)
            else:
                raise ValueError("No IV data available and --live-iv not specified")

    results = {}
    for h in horizons:
        # Build target — see volforecast.utils.targets.forward_log_rv
        log_target = forward_log_rv(rv, h)

        # Which models to run for this horizon
        h_models = horizon_models.get(str(h), horizon_models.get(h, list(models_config.keys())))

        model_predictions: dict[str, float] = {}
        model_details: dict[str, dict] = {}

        for model_name in h_models:
            if model_name not in models_config:
                logger.warning("Model %s not in config, skipping", model_name)
                continue

            mcfg = models_config[model_name]
            model_type = mcfg["type"]
            model_params = dict(mcfg.get("params", {}))

            # Apply horizon overrides
            h_override = horizon_overrides.get(str(h), horizon_overrides.get(h, {}))
            if model_name in h_override:
                override_params = h_override[model_name].get("params", {})
                model_params.update(override_params)

            # Get model's required features
            from volforecast.registry import MODEL_REGISTRY, ensure_registered

            ensure_registered()
            if model_type not in MODEL_REGISTRY:
                continue
            model_cls = MODEL_REGISTRY[model_type]
            model_instance = model_cls(**model_params)
            required_features = getattr(model_instance, "_FEATURES", None)

            # For LightGBM, use all available features
            if required_features is None:
                X_subset = X
            else:
                missing = [f for f in required_features if f not in X.columns]
                if missing:
                    logger.info(
                        "h=%d %s: missing features %s, skipping",
                        h,
                        model_name,
                        missing,
                    )
                    continue
                X_subset = X[required_features]

            # Align and clean
            aligned = pd.concat([X_subset, log_target.rename("target")], axis=1)
            aligned = aligned.replace([np.inf, -np.inf], np.nan)

            # LightGBM handles NaN natively; OLS models cannot.
            # Only dropna across all features for models with _FEATURES (OLS).
            if required_features is not None:
                aligned = aligned.dropna()
            else:
                # For tree models: only require target to be non-NaN
                aligned = aligned.dropna(subset=["target"])

            X_clean = aligned.drop(columns=["target"])
            y_clean = aligned["target"]

            if len(X_clean) < 100:
                logger.info(
                    "h=%d %s: only %d rows, skipping",
                    h,
                    model_name,
                    len(X_clean),
                )
                continue

            # Predict using last available feature row
            last_row = X_subset.iloc[[-1]]

            pred = _train_and_predict_model(
                model_name,
                model_type,
                model_params,
                X_clean,
                y_clean,
                last_row,
            )

            if pred is not None:
                rv_ann = np.sqrt(np.exp(pred) * 252) * 100
                model_predictions[model_name] = rv_ann
                model_details[model_name] = {
                    "log_rv_pred": pred,
                    "rv_forecast_ann": rv_ann,
                    "train_size": len(X_clean),
                    "last_date": str(X_clean.index[-1].date()),
                }

        if not model_predictions:
            logger.warning("h=%d: no models produced predictions", h)
            continue

        # Weighted ensemble: inverse-QLIKE weights
        h_ref = ref_qlike.get(str(h), ref_qlike.get(h, {}))
        weights = {}
        for name, rv_ann in model_predictions.items():
            qlike_val = h_ref.get(name, 0.15)  # default weight
            # Lower QLIKE = better model = higher weight
            weights[name] = 1.0 / qlike_val

        total_weight = sum(weights.values())
        ensemble_rv = sum(
            model_predictions[name] * (weights[name] / total_weight) for name in model_predictions
        )

        # Signal from ensemble
        gap = current_iv - ensemble_rv
        if gap > threshold:
            signal = "LONG"
        elif gap < -threshold:
            signal = "SHORT"
        else:
            signal = "FLAT"

        results[f"h{h}"] = {
            "ensemble_rv_ann": float(ensemble_rv),
            "current_iv": float(current_iv),
            "gap": float(gap),
            "signal": signal,
            "model_predictions": model_predictions,
            "model_details": model_details,
            "weights": {k: v / total_weight for k, v in weights.items()},
            "n_models": len(model_predictions),
        }

    return results


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


def display_results(results: dict[str, dict], symbol: str) -> None:
    """Pretty-print forecast results to console."""
    print(f"\n{'=' * 60}")
    print(f"  VOL FORECAST: {symbol}")
    print(f"  Date: {date.today()} (signal for afternoon session)")
    print(f"{'=' * 60}")

    if not results:
        print("  No valid forecasts produced.")
        return

    for key, r in results.items():
        sig_icon = {"LONG": "↑", "SHORT": "↓", "FLAT": "–"}[r["signal"]]
        print(
            f"\n  {key}:  Ensemble RV={r['ensemble_rv_ann']:.1f}%  |  "
            f"IV={r['current_iv']:.1f}%  |  "
            f"Gap={r['gap']:+.1f}%  |  "
            f"{sig_icon} {r['signal']}"
        )
        print(f"  {'─' * 50}")
        for name, rv_ann in r["model_predictions"].items():
            w = r["weights"][name]
            detail = r["model_details"][name]
            print(
                f"    {name:20s}  RV={rv_ann:5.1f}%  "
                f"(w={w:.2f}, n={detail['train_size']}, "
                f"to {detail['last_date']})"
            )

    print(f"\n{'=' * 60}\n")


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------


def main(
    symbol: str = "SPY",
    horizons_str: str = "1,5",
    threshold: float = 0.0,
    live_iv: float | None = None,
    config: str | None = None,
) -> int:
    """CLI entry point."""
    from volforecast.cli.console import setup_logging

    setup_logging()

    horizons = [int(h.strip()) for h in horizons_str.split(",")]

    results = run(
        symbol=symbol,
        horizons=horizons,
        threshold=threshold,
        live_iv=live_iv,
        config_path=config,
    )
    display_results(results, symbol)
    return 0


def register(subparsers) -> None:
    """Register the forecast subcommand."""
    parser = subparsers.add_parser(
        "forecast",
        help="Generate live RV forecast and IV-RV gap signal (LONG/SHORT/FLAT)",
    )
    parser.add_argument(
        "--symbol", type=str, default="SPY", help="Target symbol (default: SPY)"
    )
    parser.add_argument(
        "--horizon",
        type=str,
        default="1,5",
        help="Forecast horizons, comma-separated (default: 1,5)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="IV-RV gap threshold in vol points for signal (default: 0)",
    )
    parser.add_argument(
        "--live-iv",
        type=float,
        default=None,
        help="Manual ATM IV override in vol points (e.g. 18.5). If omitted, auto-fetches from TSDB",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to forecast YAML config (default: workspace/configs/forecast_live.yaml)",
    )
    parser.set_defaults(func=handle)


def handle(args) -> int:
    """Execute forecast command. Return exit code."""
    return main(
        symbol=args.symbol,
        horizons_str=args.horizon,
        threshold=args.threshold,
        live_iv=getattr(args, "live_iv", None),
        config=getattr(args, "config", None),
    )
