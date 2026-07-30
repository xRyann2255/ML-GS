"""End-to-end integration test for the generic HARX model.

Loads workspace/configs/example_harx.yaml via ExperimentConfig.from_yaml,
runs the tournament runner (Pipeline) against a synthetic SPY panel that
matches the schema ingest writes, and verifies:

  1. The metrics dataframe (built from Pipeline.run's return dict, the
     in-memory equivalent of the persisted metrics parquet) contains a
     row for model=='harx' with a finite QLIKE.
  2. The fitted HARX model has _feature_names length == HAR core (3) +
     len(extra_features), i.e. extras threaded via model.params.extra_features
     landed in the design matrix without any runner-side changes.

Proves execute-2's HARXModel works end-to-end through the actual runner
without any runner modifications (packet execute-3 constraint).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def harx_config_path() -> Path:
    """Absolute path to the example_harx.yaml config."""
    from volforecast.utils.paths import resolve_project_root

    return resolve_project_root() / "workspace" / "configs" / "example_harx.yaml"


@pytest.fixture
def synthetic_spy_panel() -> pd.DataFrame:
    """Synthetic SPY RV panel matching compute_daily_rv_from_ticks output.

    Covers the config's date_range (2021-01-04 → 2021-07-30, ~145 bdays).
    Includes the columns the har_core and asymmetry feature layers consume,
    notably `bpv` (asymmetry emits log_bpv_d from it).
    """
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2021-01-04", "2021-07-30")
    n = len(dates)

    rv = np.exp(-9.0 + 0.5 * rng.standard_normal(n))
    rq = rv**2 * (3 + rng.uniform(0, 1, n))
    bpv = rv * (0.8 + 0.1 * np.abs(rng.standard_normal(n)))
    bpv = np.clip(bpv, 1e-12, None)

    return pd.DataFrame(
        {
            "rv": rv,
            "log_rv": np.log(rv),
            "rq": rq,
            "bpv": bpv,
            "rs_positive": rv * 0.5 * (1 + 0.1 * np.abs(rng.standard_normal(n))),
            "rs_negative": rv * 0.5 * (1 + 0.1 * np.abs(rng.standard_normal(n))),
            "jump_variation": np.abs(rng.standard_normal(n)) * 1e-5,
            "continuous_variation": bpv * 0.95,
            "close": 450.0 + np.cumsum(rng.standard_normal(n) * 2),
            "symbol": "SPY",
        },
        index=dates,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHARXEndToEnd:
    def test_example_config_parses(self, harx_config_path: Path) -> None:
        """example_harx.yaml round-trips through ExperimentConfig.from_yaml."""
        from volforecast.config import ExperimentConfig

        assert harx_config_path.exists(), (
            f"example_harx.yaml missing at {harx_config_path}"
        )
        cfg = ExperimentConfig.from_yaml(harx_config_path)

        assert cfg.name == "example_harx"
        assert cfg.universe == ["SPY"]
        assert cfg.horizons == [1]
        assert cfg.model is not None
        assert cfg.model.name == "harx"
        assert cfg.model.params["extra_features"] == ["log_bpv_d"]
        assert "har_core" in cfg.feature_layers
        assert "asymmetry" in cfg.feature_layers

    def test_harx_tournament_end_to_end(
        self,
        harx_config_path: Path,
        synthetic_spy_panel: pd.DataFrame,
    ) -> None:
        """Load YAML → run Pipeline → assert metrics + fitted feature count."""
        from volforecast.config import ExperimentConfig
        from volforecast.pipeline.runner import Pipeline

        cfg = ExperimentConfig.from_yaml(harx_config_path)

        results = Pipeline(cfg).run(synthetic_spy_panel)

        # Pipeline.run returns dict[horizon] -> {metrics, predictions, model}.
        # Assert the tournament produced output for h=1.
        assert 1 in results, "harx tournament produced no h=1 result"

        # ---- Assertion 1: metrics dataframe has a harx row with finite QLIKE
        # The in-memory equivalent of the persisted metrics parquet: one row
        # per (model, horizon) with the same fields save_experiment_results
        # writes.
        metrics_df = pd.DataFrame(
            [
                {
                    "model": cfg.model.name,
                    "horizon": h,
                    **results[h]["metrics"],
                }
                for h in results
            ]
        )
        harx_rows = metrics_df[metrics_df["model"] == "harx"]
        assert len(harx_rows) == 1, (
            f"expected exactly one harx row, got {len(harx_rows)}: {metrics_df}"
        )
        qlike = float(harx_rows.iloc[0]["qlike"])
        assert np.isfinite(qlike), f"harx QLIKE not finite: {qlike}"
        assert qlike > 0, f"harx QLIKE must be positive, got {qlike}"

        # ---- Assertion 2: fitted feature count == HAR core + extras
        fitted_model = results[1]["model"]
        assert fitted_model is not None
        assert hasattr(fitted_model, "_feature_names")

        # HARXModel exposes the target feature list on the instance;
        # _BaseOLS._fit copies X.columns into _feature_names at fit time.
        n_core = 3  # log_rv_d, log_rv_w, log_rv_m
        n_extras = len(cfg.model.params["extra_features"])
        expected = n_core + n_extras
        assert len(fitted_model._feature_names) == expected, (
            f"fitted _feature_names has {len(fitted_model._feature_names)} cols, "
            f"expected HAR core ({n_core}) + extras ({n_extras}) = {expected}. "
            f"Actual: {fitted_model._feature_names}"
        )
        # The HAR core columns must appear before the YAML-declared extras.
        assert fitted_model._feature_names[:n_core] == [
            "log_rv_d",
            "log_rv_w",
            "log_rv_m",
        ]
        assert "log_bpv_d" in fitted_model._feature_names
