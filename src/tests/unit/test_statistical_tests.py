"""Tests for statistical tests (Diebold-Mariano, Mincer-Zarnowitz, MCS, Tournament)."""

from __future__ import annotations

import numpy as np
import pytest

from volforecast.evaluation.statistical_tests import (
    diebold_mariano_test,
    mincer_zarnowitz,
    model_confidence_set,
    tournament_table,
)


class TestDieboldMariano:
    """Tests for the Diebold-Mariano test."""

    def test_dm_identical_losses(self):
        """Identical losses -> DM ~ 0, p_value ~ 1."""
        rng = np.random.default_rng(42)
        losses = rng.uniform(0.01, 0.5, 200)
        result = diebold_mariano_test(losses, losses, horizon=1)
        assert abs(result["dm_stat"]) < 1e-10
        assert result["p_value"] == pytest.approx(1.0, abs=0.01)
        assert result["mean_diff"] == pytest.approx(0.0, abs=1e-12)

    def test_dm_clearly_different(self):
        """Constant loss difference -> large DM, p ~ 0."""
        loss_1 = np.full(100, 0.5)
        loss_2 = np.full(100, 0.1)
        result = diebold_mariano_test(loss_1, loss_2, horizon=1)
        assert result["dm_stat"] > 0  # model 2 better
        assert result["p_value"] < 0.001
        assert result["mean_diff"] == pytest.approx(0.4, abs=1e-10)

    def test_dm_hac_for_h5(self):
        """HAC variance estimate differs from h=1 on autocorrelated data."""
        rng = np.random.default_rng(99)
        # Generate autocorrelated loss differential via AR(1) process
        n = 500
        d = np.zeros(n)
        d[0] = rng.normal(0.1, 0.3)
        for t in range(1, n):
            d[t] = 0.7 * d[t - 1] + rng.normal(0.1, 0.3)

        loss_1 = np.abs(d) + 0.5
        loss_2 = loss_1 - d

        result_h1 = diebold_mariano_test(loss_1, loss_2, horizon=1)
        result_h5 = diebold_mariano_test(loss_1, loss_2, horizon=5)

        # HAC with h=5 should give a different (typically smaller abs) DM stat
        # because variance estimate increases with autocorrelation
        assert result_h1["dm_stat"] != pytest.approx(result_h5["dm_stat"], rel=0.01)

    def test_dm_sign(self):
        """loss_2 < loss_1 -> DM > 0 (model 2 is better)."""
        rng = np.random.default_rng(7)
        loss_1 = rng.uniform(0.3, 0.7, 150)
        loss_2 = loss_1 - 0.1  # model 2 always better by 0.1
        result = diebold_mariano_test(loss_1, loss_2, horizon=1)
        assert result["dm_stat"] > 0
        assert result["mean_diff"] > 0

    def test_dm_antisymmetric(self):
        """DM(l1, l2) == -DM(l2, l1)."""
        rng = np.random.default_rng(55)
        loss_1 = rng.uniform(0.1, 0.5, 200)
        loss_2 = rng.uniform(0.1, 0.5, 200)
        r_12 = diebold_mariano_test(loss_1, loss_2, horizon=1)
        r_21 = diebold_mariano_test(loss_2, loss_1, horizon=1)
        assert r_12["dm_stat"] == pytest.approx(-r_21["dm_stat"], abs=1e-10)
        assert r_12["p_value"] == pytest.approx(r_21["p_value"], abs=1e-10)

    def test_dm_length_mismatch_raises(self):
        """Mismatched array lengths raise ValueError."""
        with pytest.raises(ValueError, match="same length"):
            diebold_mariano_test(np.ones(10), np.ones(12))

    def test_dm_invalid_horizon_raises(self):
        """horizon < 1 raises ValueError."""
        with pytest.raises(ValueError, match="horizon"):
            diebold_mariano_test(np.ones(10), np.ones(10), horizon=0)


class TestMincerZarnowitz:
    """Tests for the Mincer-Zarnowitz efficiency regression."""

    def test_mz_perfect(self):
        """Near-perfect forecast: alpha~0, beta~1, cannot reject H0."""
        rng = np.random.default_rng(123)
        # Construct: y_true = y_pred + epsilon (forecast is efficient)
        y_pred = rng.uniform(0.0001, 0.001, 500)
        y_true = y_pred + rng.normal(0, 5e-5, 500)
        result = mincer_zarnowitz(y_true, y_pred)
        assert result["beta"] == pytest.approx(1.0, abs=0.3)
        assert result["r_squared"] > 0.5
        # Key: F-test should NOT reject H0 (alpha=0, beta=1)
        assert result["f_pvalue"] > 0.05

    def test_mz_biased(self):
        """Biased forecast (y_pred = y_true * 0.5) -> beta != 1, low f_pvalue."""
        rng = np.random.default_rng(77)
        y_true = rng.uniform(0.0001, 0.001, 300)
        y_pred = y_true * 0.5  # systematic bias
        result = mincer_zarnowitz(y_true, y_pred)
        assert result["beta"] == pytest.approx(2.0, rel=0.01)
        # Should reject joint H0
        assert result["f_pvalue"] < 0.01

    def test_mz_constant(self):
        """Constant forecast -> R2 ~ 0."""
        rng = np.random.default_rng(33)
        y_true = rng.uniform(0.0001, 0.001, 200)
        y_pred = np.full(200, np.mean(y_true))
        result = mincer_zarnowitz(y_true, y_pred)
        assert result["r_squared"] < 0.01

    def test_mz_length_mismatch_raises(self):
        """Mismatched array lengths raise ValueError."""
        with pytest.raises(ValueError, match="same length"):
            mincer_zarnowitz(np.ones(10), np.ones(12))


class TestModelConfidenceSet:
    """Tests for the Hansen et al. (2011) Model Confidence Set."""

    def test_mcs_best_included(self):
        """Best model (lowest loss) is always in the MCS."""
        rng = np.random.default_rng(42)
        T = 500
        losses = {
            "best": rng.uniform(0.01, 0.05, T),
            "mid": rng.uniform(0.08, 0.15, T),
            "worst": rng.uniform(0.20, 0.40, T),
        }
        result = model_confidence_set(losses, alpha=0.10, n_bootstrap=1000, seed=42)
        assert "best" in result["included"]

    def test_mcs_single_model(self):
        """Single model is trivially included."""
        losses = {"only": np.random.default_rng(1).uniform(0.01, 0.1, 100)}
        result = model_confidence_set(losses, alpha=0.10, n_bootstrap=100, seed=1)
        assert result["included"] == ["only"]
        assert result["excluded"] == []
        assert result["elimination_order"] == []
        assert result["p_values"]["only"] == 1.0

    def test_mcs_identical(self):
        """Identical losses -> all models included (cannot distinguish)."""
        rng = np.random.default_rng(99)
        shared = rng.uniform(0.01, 0.1, 300)
        losses = {"a": shared.copy(), "b": shared.copy(), "c": shared.copy()}
        result = model_confidence_set(losses, alpha=0.10, n_bootstrap=1000, seed=99)
        assert set(result["included"]) == {"a", "b", "c"}
        assert result["excluded"] == []

    def test_mcs_structure(self):
        """Output has all required keys with correct types."""
        rng = np.random.default_rng(7)
        T = 200
        losses = {
            "m1": rng.uniform(0.01, 0.05, T),
            "m2": rng.uniform(0.10, 0.20, T),
        }
        result = model_confidence_set(losses, alpha=0.10, n_bootstrap=500, seed=7)
        assert "included" in result
        assert "excluded" in result
        assert "p_values" in result
        assert "elimination_order" in result
        assert isinstance(result["included"], list)
        assert isinstance(result["excluded"], list)
        assert isinstance(result["p_values"], dict)
        assert isinstance(result["elimination_order"], list)

    def test_mcs_elimination_worst_first(self):
        """Highest-loss model is eliminated first."""
        rng = np.random.default_rng(55)
        T = 500
        losses = {
            "good": rng.uniform(0.01, 0.03, T),
            "ok": rng.uniform(0.05, 0.10, T),
            "bad": rng.uniform(0.20, 0.40, T),
        }
        result = model_confidence_set(losses, alpha=0.10, n_bootstrap=1000, seed=55)
        if result["elimination_order"]:
            assert result["elimination_order"][0] == "bad"

    def test_mcs_reproducible(self):
        """Same seed produces same result."""
        rng = np.random.default_rng(10)
        T = 300
        losses = {
            "a": rng.uniform(0.01, 0.05, T),
            "b": rng.uniform(0.02, 0.06, T),
            "c": rng.uniform(0.10, 0.20, T),
        }
        r1 = model_confidence_set(losses, alpha=0.10, n_bootstrap=500, seed=123)
        r2 = model_confidence_set(losses, alpha=0.10, n_bootstrap=500, seed=123)
        assert r1["included"] == r2["included"]
        assert r1["excluded"] == r2["excluded"]
        assert r1["p_values"] == r2["p_values"]


class TestTournamentTable:
    """Tests for the tournament table aggregation function."""

    def _make_predictions(self, rng, T=300):
        """Helper: generate 3 models with different quality."""
        y_true = rng.normal(-8.0, 0.5, T)  # log-RV ~ log(0.0003)
        pred_har = y_true + rng.normal(0, 0.3, T)
        pred_harq = y_true + rng.normal(0, 0.25, T)  # better
        pred_bad = y_true + rng.normal(0, 0.6, T)  # worse
        return {
            "har": pred_har,
            "harq": pred_harq,
            "bad_model": pred_bad,
        }, y_true

    def test_tournament_shape(self):
        """3 models -> 3 rows, all expected columns present."""
        rng = np.random.default_rng(42)
        preds, y_true = self._make_predictions(rng)
        table = tournament_table(preds, y_true, baseline="har", mcs_bootstrap=200)
        assert len(table) == 3
        expected_cols = {
            "model",
            "qlike",
            "qlike_bps",
            "mse",
            "r_squared",
            "mz_alpha",
            "mz_beta",
            "mz_f_pvalue",
            "dm_stat",
            "dm_pvalue",
            "mcs_included",
            "mcs_pvalue",
        }
        assert expected_cols.issubset(set(table.columns))

    def test_tournament_sorted(self):
        """Table is sorted by QLIKE ascending (best first)."""
        rng = np.random.default_rng(77)
        preds, y_true = self._make_predictions(rng)
        table = tournament_table(preds, y_true, baseline="har", mcs_bootstrap=200)
        qlike_vals = table["qlike"].tolist()
        assert qlike_vals == sorted(qlike_vals)

    def test_tournament_baseline_dm_zero(self):
        """Baseline model has dm_stat=0, dm_pvalue=1."""
        rng = np.random.default_rng(33)
        preds, y_true = self._make_predictions(rng)
        table = tournament_table(preds, y_true, baseline="har", mcs_bootstrap=200)
        baseline_row = table[table["model"] == "har"].iloc[0]
        assert baseline_row["dm_stat"] == 0.0
        assert baseline_row["dm_pvalue"] == 1.0

    def test_tournament_mcs_boolean(self):
        """mcs_included column is boolean."""
        rng = np.random.default_rng(11)
        preds, y_true = self._make_predictions(rng)
        table = tournament_table(preds, y_true, baseline="har", mcs_bootstrap=200)
        assert table["mcs_included"].dtype == bool
