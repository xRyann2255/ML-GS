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


class TestPanelAwareDM:
    """Tests for panel-aware Diebold-Mariano test."""

    def test_panel_dm_reduces_to_flat_when_none(self):
        """n_cross_sections=None gives identical result to old behavior."""
        rng = np.random.default_rng(42)
        n = 1000
        loss_1 = rng.uniform(0.01, 0.5, n)
        loss_2 = rng.uniform(0.01, 0.5, n)

        result_flat = diebold_mariano_test(loss_1, loss_2, horizon=1)
        result_none = diebold_mariano_test(loss_1, loss_2, horizon=1, n_cross_sections=None)

        assert result_flat["dm_stat"] == pytest.approx(result_none["dm_stat"])
        assert result_flat["p_value"] == pytest.approx(result_none["p_value"])

    def test_panel_dm_produces_wider_ci_than_naive(self):
        """Panel aggregation reduces |DM stat| vs naive pooling.

        With 20 symbols and 500 dates, naive pooling uses T=10000 obs,
        while panel-aware uses T_eff=500. Since SE scales as 1/sqrt(T),
        the panel-aware stat should be smaller in absolute value.
        """
        rng = np.random.default_rng(123)
        n_symbols = 20
        n_dates = 500
        n_total = n_symbols * n_dates

        # Create loss differentials with a small true difference
        # Symbol-major: all dates for sym1, then sym2, etc.
        loss_1 = rng.uniform(0.1, 0.5, n_total)
        loss_2 = loss_1 - 0.02 + rng.normal(0, 0.1, n_total)  # model 2 slightly better

        # Naive (no panel info)
        naive = diebold_mariano_test(loss_1, loss_2, horizon=1)

        # Panel-aware
        panel = diebold_mariano_test(
            loss_1, loss_2, horizon=1,
            n_cross_sections=n_symbols, panel_order="symbol_major",
        )

        # Panel-aware should have smaller |DM stat| because T_eff < T_pooled
        assert abs(panel["dm_stat"]) < abs(naive["dm_stat"])
        # Mean diff should be approximately the same (both measure the same average)
        assert panel["mean_diff"] == pytest.approx(naive["mean_diff"], rel=0.1)

    def test_panel_dm_symbol_major_vs_date_major_same_result(self):
        """Same data in different orderings gives same statistic."""
        rng = np.random.default_rng(77)
        n_symbols = 5
        n_dates = 200

        # Generate as (symbols, dates) matrix
        loss_matrix_1 = rng.uniform(0.1, 0.5, (n_symbols, n_dates))
        loss_matrix_2 = loss_matrix_1 - 0.01 + rng.normal(0, 0.05, (n_symbols, n_dates))

        # Symbol-major: flatten along symbols first
        loss_1_sym = loss_matrix_1.flatten()  # shape: (n_symbols * n_dates,) — sym1 dates, sym2 dates, ...
        loss_2_sym = loss_matrix_2.flatten()

        # Date-major: transpose then flatten
        loss_1_date = loss_matrix_1.T.flatten()  # shape: (n_dates * n_symbols,) — date1 syms, date2 syms, ...
        loss_2_date = loss_matrix_2.T.flatten()

        result_sym = diebold_mariano_test(
            loss_1_sym, loss_2_sym, horizon=1,
            n_cross_sections=n_symbols, panel_order="symbol_major",
        )
        result_date = diebold_mariano_test(
            loss_1_date, loss_2_date, horizon=1,
            n_cross_sections=n_symbols, panel_order="date_major",
        )

        assert result_sym["dm_stat"] == pytest.approx(result_date["dm_stat"], rel=1e-10)
        assert result_sym["p_value"] == pytest.approx(result_date["p_value"], rel=1e-10)


class TestPanelAwareMCS:
    """Tests for panel-aware Model Confidence Set."""

    def test_panel_mcs_backward_compatible(self):
        """n_cross_sections=None gives same result as before."""
        rng = np.random.default_rng(42)
        n = 500
        losses = {
            "model_a": rng.uniform(0.1, 0.3, n),
            "model_b": rng.uniform(0.1, 0.3, n),
            "model_c": rng.uniform(0.2, 0.5, n),  # clearly worse
        }

        result_old = model_confidence_set(losses, n_bootstrap=1000, seed=42)
        result_new = model_confidence_set(losses, n_bootstrap=1000, seed=42, n_cross_sections=None)

        assert result_old["included"] == result_new["included"]
        assert result_old["excluded"] == result_new["excluded"]

    def test_panel_mcs_uses_effective_T(self):
        """With n_cross_sections=20, block_length is based on sqrt(T_eff).

        For T_pooled=10000 and n_cross_sections=20: T_eff=500.
        Default block_length should be sqrt(500) ≈ 22, not sqrt(10000) = 100.
        We verify this indirectly: with the shorter effective T, the MCS
        should be more conservative (include more models) than naive pooling.
        """
        rng = np.random.default_rng(99)
        n_symbols = 20
        n_dates = 500
        n_total = n_symbols * n_dates

        # Model A is slightly better, model B slightly worse
        base = rng.uniform(0.1, 0.3, n_total)
        losses = {
            "model_a": base,
            "model_b": base + 0.005 + rng.normal(0, 0.02, n_total),
        }

        # Panel-aware should be more conservative (higher p-values, more inclusions)
        naive = model_confidence_set(losses, n_bootstrap=2000, seed=42)
        panel = model_confidence_set(
            losses, n_bootstrap=2000, seed=42,
            n_cross_sections=n_symbols, panel_order="symbol_major",
        )

        # Panel-aware MCS should include at least as many models
        assert len(panel["included"]) >= len(naive["included"])


class TestBaselineConfig:
    """Tests for baseline config field parsing."""

    def test_baseline_field_in_tournament_config(self):
        """TournamentConfig has baseline field with correct default."""
        from volforecast.config import TournamentConfig

        cfg = TournamentConfig()
        assert cfg.baseline == "har"

    def test_baseline_field_custom_value(self):
        """TournamentConfig accepts custom baseline."""
        from volforecast.config import TournamentConfig

        cfg = TournamentConfig(baseline="lgbm_hariv0dte_init")
        assert cfg.baseline == "lgbm_hariv0dte_init"

    def test_tournament_table_uses_baseline(self):
        """tournament_table respects the baseline parameter."""
        rng = np.random.default_rng(42)
        n = 200
        y_true = rng.normal(-8, 1, n)
        predictions = {
            "har": y_true + rng.normal(0, 0.5, n),
            "lgbm": y_true + rng.normal(0, 0.3, n),
            "xgb": y_true + rng.normal(0, 0.2, n),
        }

        # With baseline="har" (default), DM is computed vs har
        result_har = tournament_table(predictions, y_true, baseline="har", mcs_bootstrap=0)
        # With baseline="lgbm", DM is computed vs lgbm
        result_lgbm = tournament_table(predictions, y_true, baseline="lgbm", mcs_bootstrap=0)

        # har row should have dm_stat=0 when it's the baseline
        har_row_default = result_har[result_har["model"] == "har"].iloc[0]
        assert har_row_default["dm_stat"] == 0.0

        # lgbm row should have dm_stat=0 when it's the baseline
        lgbm_row_custom = result_lgbm[result_lgbm["model"] == "lgbm"].iloc[0]
        assert lgbm_row_custom["dm_stat"] == 0.0
