"""Smoke test for the Pipeline class.

Validates end-to-end config → registry → train → evaluate flow
using synthetic daily data and the HAR model.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.integration

from volforecast.config import CVConfig, ExperimentConfig, ModelConfig
from volforecast.features.asymmetry import AsymmetryLayer  # noqa: F401 — triggers registration
from volforecast.features.har import HARCoreLayer  # noqa: F401 — triggers registration
from volforecast.models.har_family import HARModel  # noqa: F401 — triggers registration
from volforecast.pipeline.runner import Pipeline


@pytest.fixture
def synthetic_daily_data() -> pd.DataFrame:
    """Generate synthetic daily data with rv, rq columns (500 days)."""
    rng = np.random.default_rng(42)
    n = 500
    dates = pd.bdate_range("2020-01-02", periods=n)

    # AR(1) log-RV with mean-reversion
    log_rv = np.zeros(n)
    log_rv[0] = np.log(1e-4)
    for t in range(1, n):
        log_rv[t] = -0.5 + 0.6 * log_rv[t - 1] + 0.3 * rng.standard_normal()

    rv = np.exp(log_rv)
    rq = rv**2 * 3  # synthetic RQ proportional to RV^2

    return pd.DataFrame({"rv": rv, "rq": rq}, index=dates)


@pytest.fixture
def har_config() -> ExperimentConfig:
    return ExperimentConfig(
        name="smoke_test",
        universe=["SYNTHETIC"],
        date_range=("2020-01-02", "2022-01-01"),
        horizons=[1],
        feature_layers=["har_core"],
        model=ModelConfig(name="har"),
        cv=CVConfig(method="blocked_kfold", n_splits=3),
    )


class TestPipeline:
    def test_smoke_run(self, har_config, synthetic_daily_data):
        """Pipeline.run returns results with expected keys."""
        results = Pipeline(har_config).run(synthetic_daily_data)
        assert 1 in results
        assert "metrics" in results[1]
        assert "predictions" in results[1]
        assert "qlike" in results[1]["metrics"]
        assert "mse" in results[1]["metrics"]
        assert "r_squared" in results[1]["metrics"]

    def test_predictions_finite(self, har_config, synthetic_daily_data):
        results = Pipeline(har_config).run(synthetic_daily_data)
        preds = results[1]["predictions"]
        assert np.all(np.isfinite(preds.values))

    def test_unknown_model_raises(self, synthetic_daily_data):
        cfg = ExperimentConfig(
            name="bad_model",
            universe=["X"],
            date_range=("2020-01-01", "2021-01-01"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="nonexistent_model"),
        )
        with pytest.raises(ValueError, match="Unknown model"):
            Pipeline(cfg).run(synthetic_daily_data)

    def test_unknown_feature_raises(self, synthetic_daily_data):
        cfg = ExperimentConfig(
            name="bad_feature",
            universe=["X"],
            date_range=("2020-01-01", "2021-01-01"),
            horizons=[1],
            feature_layers=["nonexistent_layer"],
            model=ModelConfig(name="har"),
        )
        with pytest.raises(ValueError, match="Unknown feature layer"):
            Pipeline(cfg).run(synthetic_daily_data)

    def test_no_rv_column_raises(self, har_config):
        bad_data = pd.DataFrame({"close": [100.0, 101.0]})
        with pytest.raises(ValueError, match="rv"):
            Pipeline(har_config).run(bad_data)

    def test_pipeline_with_rv_panel_output(self):
        """Prove rv_panel output format is compatible with har_core + asymmetry layers."""
        rng = np.random.default_rng(123)
        n = 200
        dates = pd.bdate_range("2022-01-03", periods=n)

        # Simulate compute_daily_rv_from_ticks output columns
        rv = np.exp(-9.0 + 0.5 * rng.standard_normal(n))  # realistic RV range
        rq = rv**2 * (3 + rng.uniform(0, 1, n))
        bpv = rv * (0.8 + 0.1 * rng.standard_normal(n))
        bpv = np.clip(bpv, 1e-12, None)

        panel = pd.DataFrame(
            {
                "rv": rv,
                "rq": rq,
                "bpv": bpv,
                "rs_positive": rv * 0.5 * (1 + 0.1 * rng.standard_normal(n)),
                "rs_negative": rv * 0.5 * (1 - 0.1 * rng.standard_normal(n)),
                "jump_stat": rng.standard_normal(n),
                "jump_indicator": rng.integers(0, 2, n),
                "continuous_variation": bpv * 0.95,
                "jump_variation": rv - bpv * 0.95,
                "rk": rv * (1 + 0.05 * rng.standard_normal(n)),
                "noise_gap": 0.05 * rng.standard_normal(n),
                "n_ticks": rng.integers(3000, 8000, n),
                "n_bars": np.full(n, 78),
                "symbol": "SPY",
            },
            index=dates,
        )
        # Clip negatives that would fail the pipeline
        panel["rs_positive"] = panel["rs_positive"].clip(lower=1e-12)
        panel["rs_negative"] = panel["rs_negative"].clip(lower=1e-12)
        panel["continuous_variation"] = panel["continuous_variation"].clip(lower=1e-12)
        panel["jump_variation"] = panel["jump_variation"].clip(lower=0)

        cfg = ExperimentConfig(
            name="rv_panel_integration",
            universe=["SPY"],
            date_range=("2022-01-03", "2022-12-30"),
            horizons=[1, 5],
            feature_layers=["har_core", "asymmetry"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="blocked_kfold", n_splits=3),
        )
        results = Pipeline(cfg).run(panel)

        assert 1 in results
        assert 5 in results
        assert np.isfinite(results[1]["metrics"]["qlike"])
        assert np.isfinite(results[5]["metrics"]["qlike"])
        assert results[1]["metrics"]["qlike"] > 0


# ---------------------------------------------------------------------------
# Tests: CV purge gap enforcement per forecast horizon
# ---------------------------------------------------------------------------


class TestPurgeGapEnforcement:
    """Verify effective_purge = max(config.purge_gap, h) per horizon."""

    @pytest.fixture
    def multi_horizon_data(self) -> pd.DataFrame:
        """Synthetic daily data long enough for multi-horizon CV."""
        rng = np.random.default_rng(77)
        n = 800
        dates = pd.bdate_range("2019-01-02", periods=n)
        log_rv = np.zeros(n)
        log_rv[0] = np.log(1e-4)
        for t in range(1, n):
            log_rv[t] = -0.5 + 0.6 * log_rv[t - 1] + 0.3 * rng.standard_normal()
        rv = np.exp(log_rv)
        rq = rv**2 * 3
        return pd.DataFrame({"rv": rv, "rq": rq}, index=dates)

    def test_purge_increased_for_h22(self, multi_horizon_data, caplog):
        """For h=22 with purge_gap=5, effective purge should be 22."""
        import logging

        cfg = ExperimentConfig(
            name="purge_test_h22",
            universe=["SYN"],
            date_range=("2019-01-02", "2022-06-01"),
            horizons=[22],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="expanding_window", purge_gap=5, train_size=252, test_size=63),
        )
        with caplog.at_level(logging.WARNING, logger="volforecast.pipeline.runner"):
            results = Pipeline(cfg).run(multi_horizon_data)

        # Should have warned about purge gap increase
        assert any("Purge gap increased from 5 to 22" in msg for msg in caplog.messages)
        assert 22 in results
        assert results[22]["metrics"]["qlike"] > 0

    def test_purge_not_increased_for_h1(self, multi_horizon_data, caplog):
        """For h=1 with purge_gap=5, original gap is used (5 > 1)."""
        import logging

        cfg = ExperimentConfig(
            name="purge_test_h1",
            universe=["SYN"],
            date_range=("2019-01-02", "2022-06-01"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="expanding_window", purge_gap=5, train_size=252, test_size=63),
        )
        with caplog.at_level(logging.WARNING, logger="volforecast.pipeline.runner"):
            results = Pipeline(cfg).run(multi_horizon_data)

        # Should NOT warn (5 >= 1)
        assert not any("Purge gap increased" in msg for msg in caplog.messages)
        assert 1 in results

    def test_purge_not_increased_for_h5(self, multi_horizon_data, caplog):
        """For h=5 with purge_gap=5, original gap is used (5 >= 5)."""
        import logging

        cfg = ExperimentConfig(
            name="purge_test_h5",
            universe=["SYN"],
            date_range=("2019-01-02", "2022-06-01"),
            horizons=[5],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="expanding_window", purge_gap=5, train_size=252, test_size=63),
        )
        with caplog.at_level(logging.WARNING, logger="volforecast.pipeline.runner"):
            results = Pipeline(cfg).run(multi_horizon_data)

        # Should NOT warn (5 >= 5)
        assert not any("Purge gap increased" in msg for msg in caplog.messages)
        assert 5 in results


class TestPipelineContext:
    """Tests for the context kwarg in Pipeline.run()."""

    def test_run_with_context_none(self, har_config, synthetic_daily_data):
        """Pipeline.run() works with explicit context=None (backward compat)."""
        results = Pipeline(har_config).run(synthetic_daily_data, context=None)
        assert 1 in results
        assert "qlike" in results[1]["metrics"]

    def test_run_with_context_dict(self, har_config, synthetic_daily_data):
        """Pipeline.run() works with context containing a DataFrame."""
        ctx = {"iv_surface": pd.DataFrame({"atm_iv": [0.2, 0.3]})}
        results = Pipeline(har_config).run(synthetic_daily_data, context=ctx)
        assert 1 in results
        assert "qlike" in results[1]["metrics"]


class TestDevUniverse:
    """Tests for DEV_UNIVERSE constant."""

    def test_dev_universe_is_subset(self):
        from volforecast.constants import DEV_UNIVERSE, SYMBOL_UNIVERSE

        assert DEV_UNIVERSE.issubset(SYMBOL_UNIVERSE)

    def test_dev_universe_size(self):
        from volforecast.constants import DEV_UNIVERSE

        assert len(DEV_UNIVERSE) == 8


# ---------------------------------------------------------------------------
# Tests: Inf guard — ensures ±inf in features are treated as NaN
# ---------------------------------------------------------------------------


class TestInfGuard:
    """Verify that ±inf values in features are replaced with NaN before training."""

    def test_inf_in_features_dropped_not_fitted(self):
        """Rows with inf in features should be dropped, not passed to model."""
        rng = np.random.default_rng(55)
        n = 500
        dates = pd.bdate_range("2020-01-02", periods=n)

        log_rv = np.zeros(n)
        log_rv[0] = np.log(1e-4)
        for t in range(1, n):
            log_rv[t] = -0.5 + 0.6 * log_rv[t - 1] + 0.3 * rng.standard_normal()

        rv = np.exp(log_rv)
        rq = rv**2 * 3
        # Inject inf into rs_positive for first 10 rows (simulates SPY bug)
        rs_pos = rv * 0.5
        rs_pos[:10] = np.inf
        rs_neg = rv * 0.5

        data = pd.DataFrame(
            {
                "rv": rv,
                "rq": rq,
                "bpv": rv * 0.85,
                "rs_positive": rs_pos,
                "rs_negative": rs_neg,
                "jump_stat": rng.standard_normal(n),
                "jump_indicator": rng.integers(0, 2, n),
                "continuous_variation": rv * 0.85,
                "jump_variation": rv * 0.15,
            },
            index=dates,
        )

        cfg = ExperimentConfig(
            name="inf_guard_test",
            universe=["SYNTH"],
            date_range=("2020-01-02", "2022-01-01"),
            horizons=[1],
            feature_layers=["har_core", "asymmetry"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="blocked_kfold", n_splits=3),
        )
        results = Pipeline(cfg).run(data)

        # Pipeline should succeed and produce finite predictions
        assert 1 in results
        preds = results[1]["predictions"]
        assert np.all(np.isfinite(preds.values))
        # Fewer rows than without inf (10 rows with inf dropped)
        assert len(preds) < n - 22  # after rolling window + target shift


# ---------------------------------------------------------------------------
# Tests: Pooled (multi-symbol) Pipeline
# ---------------------------------------------------------------------------


class TestPooledPipeline:
    """Tests for Pipeline.run_pooled() — panel/multi-symbol training."""

    @pytest.fixture
    def panel_data(self) -> dict[str, pd.DataFrame]:
        """3 symbols of synthetic daily data (300 days each)."""
        rng = np.random.default_rng(99)
        n = 300
        dates = pd.bdate_range("2020-01-02", periods=n)
        result = {}
        for sym in ["SPY", "AAPL", "MSFT"]:
            log_rv = np.zeros(n)
            log_rv[0] = np.log(1e-4)
            for t in range(1, n):
                log_rv[t] = -0.5 + 0.6 * log_rv[t - 1] + 0.3 * rng.standard_normal()
            rv = np.exp(log_rv)
            rq = rv**2 * 3
            result[sym] = pd.DataFrame({"rv": rv, "rq": rq}, index=dates)
        return result

    @pytest.fixture
    def pooled_config(self) -> ExperimentConfig:
        return ExperimentConfig(
            name="pooled_smoke",
            universe=["SPY", "AAPL", "MSFT"],
            date_range=("2020-01-02", "2021-06-01"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="expanding_window", train_size=100, test_size=30),
            training_mode="pooled",
        )

    def test_run_pooled_returns_results(self, pooled_config, panel_data):
        """run_pooled returns dict keyed by horizon with expected structure."""
        results = Pipeline(pooled_config).run_pooled(panel_data)
        assert 1 in results
        assert "metrics" in results[1]
        assert "predictions" in results[1]
        assert "actuals" in results[1]
        assert "qlike" in results[1]["metrics"]

    def test_predictions_have_multiindex(self, pooled_config, panel_data):
        """OOS predictions are indexed by (date, symbol)."""
        results = Pipeline(pooled_config).run_pooled(panel_data)
        preds = results[1]["predictions"]
        assert isinstance(preds.index, pd.MultiIndex)
        assert preds.index.names == ["date", "symbol"]

    def test_all_symbols_in_predictions(self, pooled_config, panel_data):
        """Predictions contain all 3 symbols."""
        results = Pipeline(pooled_config).run_pooled(panel_data)
        preds = results[1]["predictions"]
        symbols_in_preds = preds.index.get_level_values("symbol").unique()
        assert set(symbols_in_preds) == {"SPY", "AAPL", "MSFT"}

    def test_predictions_finite(self, pooled_config, panel_data):
        """All OOS predictions are finite."""
        results = Pipeline(pooled_config).run_pooled(panel_data)
        preds = results[1]["predictions"]
        assert np.all(np.isfinite(preds.values))

    def test_pooled_has_more_training_rows(self, pooled_config, panel_data):
        """Pooled training should use 3x more rows than single-symbol."""
        # Run pooled
        pooled_results = Pipeline(pooled_config).run_pooled(panel_data)
        pooled_preds = pooled_results[1]["predictions"]

        # Run single symbol
        single_cfg = ExperimentConfig(
            name="single_smoke",
            universe=["SPY"],
            date_range=("2020-01-02", "2021-06-01"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="expanding_window", train_size=100, test_size=30),
            training_mode="per_symbol",
        )
        single_results = Pipeline(single_cfg).run(panel_data["SPY"])
        single_preds = single_results[1]["predictions"]

        # Pooled should have ~3x the predictions
        assert len(pooled_preds) > 2 * len(single_preds)

    def test_no_cross_symbol_target_contamination(self, panel_data, pooled_config):
        """Target for each symbol uses only its own RV (no cross-symbol rolling)."""
        # Give one symbol wildly different RV to detect contamination
        panel_data["MSFT"]["rv"] = panel_data["MSFT"]["rv"] * 100
        results = Pipeline(pooled_config).run_pooled(panel_data)
        preds = results[1]["predictions"]
        # MSFT predictions should be much larger than SPY/AAPL
        msft_preds = preds.xs("MSFT", level="symbol")
        spy_preds = preds.xs("SPY", level="symbol")
        # In log space, MSFT target ~ log(100) + SPY target = ~4.6 higher
        assert msft_preds.mean() > spy_preds.mean() + 2.0

    def test_multi_horizon(self, panel_data):
        """run_pooled works with multiple horizons."""
        cfg = ExperimentConfig(
            name="multi_h",
            universe=["SPY", "AAPL"],
            date_range=("2020-01-02", "2021-06-01"),
            horizons=[1, 5],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="expanding_window", train_size=100, test_size=30),
            training_mode="pooled",
        )
        results = Pipeline(cfg).run_pooled(
            {k: v for k, v in panel_data.items() if k in ["SPY", "AAPL"]}
        )
        assert 1 in results
        assert 5 in results
        assert results[5]["metrics"]["qlike"] > 0

    def test_pooled_handles_mismatched_columns(self, panel_data):
        """Pooled mode handles symbols with different feature columns (e.g. overnight_return
        dropped for one symbol due to corruption). Union columns used; OLS models
        gracefully produce NaN for rows with missing features."""
        # Give SPY clean open/close (overnight_return included)
        rng = np.random.default_rng(42)
        n = len(panel_data["SPY"])
        close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
        open_ = close * (1 + rng.normal(0, 0.003, n))
        panel_data["SPY"]["open"] = open_
        panel_data["SPY"]["close"] = close

        # Give AAPL corrupted open/close (overnight_return will be dropped)
        close2 = 150 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
        open2 = close2 * (1 + rng.normal(0, 0.003, n))
        open2[50] = close2[49] / 10  # simulate 10:1 split mismatch
        panel_data["AAPL"]["open"] = open2
        panel_data["AAPL"]["close"] = close2

        # MSFT has no open/close at all
        # Use HAR model (explicit _FEATURES) which ignores overnight_return
        cfg = ExperimentConfig(
            name="mismatch_cols",
            universe=["SPY", "AAPL", "MSFT"],
            date_range=("2020-01-02", "2021-06-01"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="har"),
            cv=CVConfig(method="expanding_window", train_size=100, test_size=30),
            training_mode="pooled",
        )
        # Should succeed — HAR only uses log_rv_d/w/m, ignores overnight_return
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            results = Pipeline(cfg).run_pooled(panel_data)
        assert 1 in results
        preds = results[1]["predictions"]
        assert np.all(np.isfinite(preds.values))


class TestNestedCVPipeline:
    """Tests for Pipeline with tuning.enabled=True (nested CV / Optuna per fold)."""

    lgb = pytest.importorskip("lightgbm")
    optuna = pytest.importorskip("optuna")

    @pytest.fixture
    def synthetic_lgbm_data(self) -> pd.DataFrame:
        """Synthetic data large enough for nested CV (800 days)."""
        rng = np.random.default_rng(42)
        n = 800
        dates = pd.bdate_range("2018-01-02", periods=n)
        log_rv = np.zeros(n)
        log_rv[0] = np.log(1e-4)
        for t in range(1, n):
            log_rv[t] = -0.5 + 0.6 * log_rv[t - 1] + 0.3 * rng.standard_normal()
        rv = np.exp(log_rv)
        rq = rv**2 * 3
        return pd.DataFrame({"rv": rv, "rq": rq}, index=dates)

    def test_nested_cv_produces_predictions(self, synthetic_lgbm_data):
        """Pipeline with tuning enabled produces valid OOS predictions."""
        from volforecast.config import TuningConfig
        from volforecast.models.lightgbm import LightGBMVolModel  # noqa: F401

        cfg = ExperimentConfig(
            name="nested_cv_smoke",
            universe=["SYNTHETIC"],
            date_range=("2018-01-02", "2021-01-01"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="lightgbm", params={"min_child_samples": 20}),
            cv=CVConfig(method="expanding_window", train_size=400, test_size=63, purge_gap=5),
            tuning=TuningConfig(enabled=True, n_trials=2, timeout=60, min_train_size=300),
        )
        results = Pipeline(cfg).run(synthetic_lgbm_data)
        assert 1 in results
        preds = results[1]["predictions"]
        assert len(preds) > 0
        assert np.all(np.isfinite(preds.values))

    def test_tuning_disabled_uses_default_params(self, synthetic_lgbm_data):
        """With tuning disabled, LightGBM uses config params (no Optuna)."""
        from unittest.mock import patch

        from volforecast.config import TuningConfig
        from volforecast.models.lightgbm import LightGBMVolModel  # noqa: F401

        cfg = ExperimentConfig(
            name="no_tune_smoke",
            universe=["SYNTHETIC"],
            date_range=("2018-01-02", "2021-01-01"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="lightgbm"),
            cv=CVConfig(method="expanding_window", train_size=400, test_size=63, purge_gap=5),
            tuning=TuningConfig(enabled=False),
        )

        with patch("volforecast.models.lightgbm.tune_hyperparameters") as mock_tune:
            results = Pipeline(cfg).run(synthetic_lgbm_data)
            mock_tune.assert_not_called()

        assert 1 in results
        assert results[1]["metrics"]["qlike"] > 0

    def test_min_train_size_skips_tuning(self, synthetic_lgbm_data):
        """When outer fold train < min_train_size, falls back to default params."""
        from unittest.mock import patch

        from volforecast.config import TuningConfig
        from volforecast.models.lightgbm import LightGBMVolModel  # noqa: F401

        cfg = ExperimentConfig(
            name="skip_tune_smoke",
            universe=["SYNTHETIC"],
            date_range=("2018-01-02", "2021-01-01"),
            horizons=[1],
            feature_layers=["har_core"],
            model=ModelConfig(name="lightgbm", params={"min_child_samples": 20}),
            cv=CVConfig(method="expanding_window", train_size=100, test_size=63, purge_gap=5),
            tuning=TuningConfig(enabled=True, n_trials=3, min_train_size=9999),
        )

        with patch("volforecast.models.lightgbm.LightGBMVolModel.tune_and_fit") as mock_tune:
            results = Pipeline(cfg).run(synthetic_lgbm_data)
            mock_tune.assert_not_called()

        assert 1 in results
