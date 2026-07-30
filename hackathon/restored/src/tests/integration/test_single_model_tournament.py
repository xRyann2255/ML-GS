"""Tests for single-model tournament execution.

Verifies that the tournament path works correctly with just 1 model:
- Dashboard HTML is produced
- DM/MCS don't crash (trivial/degenerate results)
- Stats table has exactly 1 row
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.integration

from volforecast.config import CVConfig, ExperimentConfig, ModelConfig, TournamentConfig


@pytest.fixture
def single_model_config(tmp_path: Path) -> ExperimentConfig:
    """Config with a single model in tournament.models."""
    return ExperimentConfig(
        name="test_single_model",
        universe=["SYNTH"],
        date_range=("2020-01-02", "2022-01-01"),
        horizons=[1],
        feature_layers=["har_core"],
        model=ModelConfig(name="har"),
        cv=CVConfig(method="expanding_window", purge_gap=5, train_size=252, test_size=63),
        tournament=TournamentConfig(models=["har"]),
        output_dir=tmp_path / "output",
    )


@pytest.fixture
def synthetic_rv_panel() -> pd.DataFrame:
    """Synthetic RV panel for testing."""
    rng = np.random.default_rng(42)
    n = 500
    dates = pd.bdate_range("2020-01-02", periods=n)
    rv = np.exp(-9.0 + 0.5 * rng.standard_normal(n))
    rq = rv**2 * (3 + rng.uniform(0, 1, n))
    return pd.DataFrame({"rv": rv, "rq": rq}, index=dates)


@pytest.fixture
def setup_rv_cache(monkeypatch, tmp_path, synthetic_rv_panel):
    """Set up synthetic RV panel in cache."""
    from volforecast.utils import paths

    monkeypatch.setattr(paths, "resolve_project_root", lambda: tmp_path)
    raw = tmp_path / "data" / "raw" / "ticks"
    raw.mkdir(parents=True)
    synthetic_rv_panel.to_parquet(raw / "SYNTH.parquet")
    return tmp_path


class TestSingleModelTournament:
    def test_tournament_table_one_model(self):
        """tournament_table with 1 model produces a 1-row DataFrame."""
        from volforecast.evaluation.statistical_tests import tournament_table

        rng = np.random.default_rng(42)
        y = rng.normal(-9.0, 0.5, 200)
        preds = {"har": y + rng.normal(0, 0.1, 200)}

        table = tournament_table(preds, y, baseline="har", horizon=1)
        assert len(table) == 1
        assert table.iloc[0]["model"] == "har"
        assert bool(table.iloc[0]["mcs_included"]) is True

    def test_dm_mcs_trivial_with_one_model(self):
        """DM stat is 0 and MCS includes the sole model."""
        from volforecast.evaluation.statistical_tests import tournament_table

        rng = np.random.default_rng(42)
        y = rng.normal(-9.0, 0.5, 200)
        preds = {"har": y + rng.normal(0, 0.1, 200)}

        table = tournament_table(preds, y, baseline="har", horizon=1)
        assert table.iloc[0]["dm_stat"] == 0.0
        assert table.iloc[0]["dm_pvalue"] == 1.0
        assert table.iloc[0]["mcs_pvalue"] == 1.0

    def test_single_model_tournament_runner(self, setup_rv_cache, single_model_config):
        """run_har_tournament with 1 model returns results with 1-row table."""
        from volforecast.evaluation.tournament import run_har_tournament

        results = run_har_tournament(
            symbols=["SYNTH"],
            date_range=("2020-01-02", "2022-01-01"),
            horizons=[1],
            models=["har"],
            cv_config=single_model_config.cv,
            output_dir=single_model_config.output_dir,
        )

        assert 1 in results
        table = results[1]
        assert len(table) == 1
        assert table.iloc[0]["model"] == "har"

    def test_single_model_produces_dashboard(self, setup_rv_cache, single_model_config):
        """Single-model tournament produces dashboard HTML."""
        from volforecast.evaluation.tournament import run_har_tournament

        output_dir = single_model_config.output_dir
        run_har_tournament(
            symbols=["SYNTH"],
            date_range=("2020-01-02", "2022-01-01"),
            horizons=[1],
            models=["har"],
            cv_config=single_model_config.cv,
            output_dir=output_dir,
        )

        dashboard = output_dir / "plots" / "tournament_dashboard.html"
        assert dashboard.exists(), f"Dashboard not found at {dashboard}"
