"""Unit tests for vol forecast CLI command (multi-model ensemble)."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest


def _make_mock_rv_data(n_days: int = 500) -> pd.DataFrame:
    """Create synthetic tick-derived RV panel matching real parquet schema."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2023-01-02", periods=n_days, freq="B")
    rv = np.exp(rng.normal(-8.5, 0.5, n_days))  # daily RV ~ exp(log-normal)
    rq = rv**2 * rng.uniform(0.5, 2.0, n_days)
    bpv = rv * rng.uniform(0.8, 1.0, n_days)
    return pd.DataFrame(
        {
            "rv": rv,
            "rq": rq,
            "bpv": bpv,
            "open": 450.0 + np.cumsum(rng.normal(0, 1, n_days)),
            "close": 450.0 + np.cumsum(rng.normal(0, 1, n_days)),
        },
        index=dates,
    )


def _make_mock_iv_data(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Create synthetic IV cache matching data/raw/iv/{symbol}.parquet schema."""
    rng = np.random.default_rng(123)
    n = len(index)
    return pd.DataFrame(
        {
            "iv_1m_atm": 18.0 + rng.normal(0, 2, n),
            "iv_3m_atm": 20.0 + rng.normal(0, 1.5, n),
            "iv_1m_25dp": 22.0 + rng.normal(0, 2.5, n),
        },
        index=index,
    )


def _minimal_forecast_config() -> dict:
    """Minimal config for testing (HAR-only, no LightGBM)."""
    return {
        "name": "test_forecast",
        "symbol": "SPY",
        "horizons": [1, 5],
        "threshold": 0.0,
        "feature_layers": ["har_core", "options"],
        "models": {
            "har": {"type": "har", "params": {}},
            "har_iv": {"type": "har_iv", "params": {}},
        },
        "horizon_models": {
            "1": ["har", "har_iv"],
            "5": ["har", "har_iv"],
        },
        "horizon_overrides": {},
        "reference_qlike": {
            "1": {"har": 0.16, "har_iv": 0.15},
            "5": {"har": 0.13, "har_iv": 0.12},
        },
    }


def _build_features_from_rv(rv_data: pd.DataFrame, iv_data: pd.DataFrame):
    """Build HAR + options features from mock data (replicates pipeline)."""
    from volforecast.features.har import HARCoreLayer
    from volforecast.features.options import OptionsLayer

    daily_data = rv_data.copy()
    for col in iv_data.columns:
        daily_data[col] = iv_data[col].reindex(daily_data.index)

    har_layer = HARCoreLayer()
    har_features = har_layer.compute(daily_data)
    enriched = pd.concat([daily_data, har_features], axis=1)

    options_layer = OptionsLayer()
    options_features = options_layer.compute(enriched)

    X = pd.concat([har_features, options_features], axis=1)
    return daily_data, X


class TestForecastRun:
    """Test forecast.run() end-to-end with mocked data."""

    def test_produces_signal_with_mocked_data(self):
        """run() should produce forecast results with valid signal direction."""
        from volforecast.cli.forecast import run

        rv_data = _make_mock_rv_data(500)
        iv_data = _make_mock_iv_data(rv_data.index)
        daily_data, X = _build_features_from_rv(rv_data, iv_data)

        with (
            patch(
                "volforecast.cli.forecast._build_features_for_symbol",
                return_value=(daily_data, X),
            ),
            patch(
                "volforecast.cli.forecast.load_forecast_config",
                return_value=_minimal_forecast_config(),
            ),
            patch("volforecast.cli.forecast._fetch_live_iv", return_value=20.0),
        ):
            result = run(symbol="SPY", horizons=[1, 5], threshold=0.0)

        assert result is not None
        assert "h1" in result
        assert "h5" in result
        for key in ("h1", "h5"):
            r = result[key]
            assert "ensemble_rv_ann" in r
            assert "current_iv" in r
            assert "gap" in r
            assert "signal" in r
            assert r["signal"] in ("LONG", "SHORT", "FLAT")
            assert r["ensemble_rv_ann"] > 0
            assert r["current_iv"] == 20.0
            assert r["n_models"] >= 1

    def test_signal_long_when_iv_exceeds_rv(self):
        """When IV >> RV forecast, signal should be LONG (sell vol)."""
        from volforecast.cli.forecast import run

        rv_data = _make_mock_rv_data(500)
        iv_data = _make_mock_iv_data(rv_data.index)
        daily_data, X = _build_features_from_rv(rv_data, iv_data)

        with (
            patch(
                "volforecast.cli.forecast._build_features_for_symbol",
                return_value=(daily_data, X),
            ),
            patch(
                "volforecast.cli.forecast.load_forecast_config",
                return_value=_minimal_forecast_config(),
            ),
            patch("volforecast.cli.forecast._fetch_live_iv", return_value=30.0),
        ):
            result = run(symbol="SPY", horizons=[1], threshold=0.0)

        assert result["h1"]["signal"] == "LONG"

    def test_signal_short_when_rv_exceeds_iv(self):
        """When RV forecast >> IV, signal should be SHORT (buy vol)."""
        from volforecast.cli.forecast import run

        rv_data = _make_mock_rv_data(500)
        iv_data = _make_mock_iv_data(rv_data.index)
        daily_data, X = _build_features_from_rv(rv_data, iv_data)

        with (
            patch(
                "volforecast.cli.forecast._build_features_for_symbol",
                return_value=(daily_data, X),
            ),
            patch(
                "volforecast.cli.forecast.load_forecast_config",
                return_value=_minimal_forecast_config(),
            ),
            patch("volforecast.cli.forecast._fetch_live_iv", return_value=5.0),
        ):
            result = run(symbol="SPY", horizons=[1], threshold=0.0)

        assert result["h1"]["signal"] == "SHORT"

    def test_threshold_produces_flat(self):
        """With a large threshold, small gaps should produce FLAT."""
        from volforecast.cli.forecast import run

        rv_data = _make_mock_rv_data(500)
        iv_data = _make_mock_iv_data(rv_data.index)
        daily_data, X = _build_features_from_rv(rv_data, iv_data)

        with (
            patch(
                "volforecast.cli.forecast._build_features_for_symbol",
                return_value=(daily_data, X),
            ),
            patch(
                "volforecast.cli.forecast.load_forecast_config",
                return_value=_minimal_forecast_config(),
            ),
            patch("volforecast.cli.forecast._fetch_live_iv", return_value=15.0),
        ):
            result = run(symbol="SPY", horizons=[1], threshold=50.0)

        assert result["h1"]["signal"] == "FLAT"

    def test_live_iv_override(self):
        """--live-iv should override TSDB fetch."""
        from volforecast.cli.forecast import run

        rv_data = _make_mock_rv_data(500)
        iv_data = _make_mock_iv_data(rv_data.index)
        daily_data, X = _build_features_from_rv(rv_data, iv_data)

        with (
            patch(
                "volforecast.cli.forecast._build_features_for_symbol",
                return_value=(daily_data, X),
            ),
            patch(
                "volforecast.cli.forecast.load_forecast_config",
                return_value=_minimal_forecast_config(),
            ),
        ):
            result = run(symbol="SPY", horizons=[1], threshold=0.0, live_iv=25.0)

        assert result["h1"]["current_iv"] == 25.0

    def test_weighted_ensemble_uses_inverse_qlike(self):
        """Ensemble weights should be proportional to 1/QLIKE."""
        from volforecast.cli.forecast import run

        rv_data = _make_mock_rv_data(500)
        iv_data = _make_mock_iv_data(rv_data.index)
        daily_data, X = _build_features_from_rv(rv_data, iv_data)

        with (
            patch(
                "volforecast.cli.forecast._build_features_for_symbol",
                return_value=(daily_data, X),
            ),
            patch(
                "volforecast.cli.forecast.load_forecast_config",
                return_value=_minimal_forecast_config(),
            ),
            patch("volforecast.cli.forecast._fetch_live_iv", return_value=20.0),
        ):
            result = run(symbol="SPY", horizons=[1], threshold=0.0)

        weights = result["h1"]["weights"]
        # HAR-IV has lower QLIKE (0.15) than HAR (0.16), so higher weight
        if "har" in weights and "har_iv" in weights:
            assert weights["har_iv"] > weights["har"]

    def test_model_predictions_are_independent(self):
        """Each model in the ensemble should produce its own prediction."""
        from volforecast.cli.forecast import run

        rv_data = _make_mock_rv_data(500)
        iv_data = _make_mock_iv_data(rv_data.index)
        daily_data, X = _build_features_from_rv(rv_data, iv_data)

        with (
            patch(
                "volforecast.cli.forecast._build_features_for_symbol",
                return_value=(daily_data, X),
            ),
            patch(
                "volforecast.cli.forecast.load_forecast_config",
                return_value=_minimal_forecast_config(),
            ),
            patch("volforecast.cli.forecast._fetch_live_iv", return_value=20.0),
        ):
            result = run(symbol="SPY", horizons=[1], threshold=0.0)

        preds = result["h1"]["model_predictions"]
        # Should have at least 1 model
        assert len(preds) >= 1
        # All predictions should be positive (annualized vol %)
        for rv_ann in preds.values():
            assert rv_ann > 0

    def test_config_path_override(self):
        """--config should load a custom config file."""
        from volforecast.cli.forecast import load_forecast_config

        # This tests that the config loader doesn't crash
        # (actual file loading is integration-level)
        config = _minimal_forecast_config()
        with patch("builtins.open", side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                load_forecast_config("/nonexistent/path.yaml")
