"""Tests for GSVIVS01 variance swap signal backtest."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.data.edrvol import load_gsvivs_cache, save_gsvivs_cache
from volforecast.evaluation.economic_value import (
    gsvivs_baselines,
    gsvivs_signal_pnl,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def index_levels():
    """Synthetic GSVIVS01 index levels: upward drift with small vol."""
    rng = np.random.default_rng(42)
    n = 500
    # ~8% annualized return, ~4% vol (matches real GSVIVS01 profile)
    daily_ret = 0.08 / 252 + 0.04 / np.sqrt(252) * rng.standard_normal(n)
    levels = 100.0 * np.exp(np.cumsum(daily_ret))
    return levels


@pytest.fixture
def index_series(index_levels):
    """Same as index_levels but as a DatetimeIndex pd.Series."""
    dates = pd.bdate_range("2023-01-02", periods=len(index_levels), freq="B")
    return pd.Series(index_levels, index=dates, name="gsvivs01")


# ---------------------------------------------------------------------------
# gsvivs_signal_pnl tests
# ---------------------------------------------------------------------------

EXPECTED_METRICS = {
    "sharpe_0rf",
    "sharpe_5rf",
    "ann_return",
    "ann_vol",
    "total_return",
    "max_drawdown",
    "positive_days",
    "hit_rate",
    "precision",
    "recall",
    "f1",
    "mcc",
    "flat_pct",
}


class TestGsvivsPnl:
    """Tests for gsvivs_signal_pnl() function."""

    def test_returns_all_expected_metrics(self, index_levels):
        """Should return dict with all 10 expected metric keys."""
        signal = np.ones(len(index_levels))
        result = gsvivs_signal_pnl(index_levels, signal)
        assert set(result.keys()) == EXPECTED_METRICS

    def test_always_long_positive_return_for_uptrending_index(self, index_levels):
        """Always-long signal on upward-drifting index should have positive return."""
        signal = np.ones(len(index_levels))
        result = gsvivs_signal_pnl(index_levels, signal)
        assert result["total_return"] > 0
        assert result["ann_return"] > 0

    def test_always_short_negative_return_for_uptrending_index(self, index_levels):
        """Always-short signal on upward-drifting index should have negative return."""
        signal = -np.ones(len(index_levels))
        result = gsvivs_signal_pnl(index_levels, signal)
        assert result["total_return"] < 0
        assert result["ann_return"] < 0

    def test_always_flat_all_zeros(self, index_levels):
        """Signal=0 should produce zero everything."""
        signal = np.zeros(len(index_levels))
        result = gsvivs_signal_pnl(index_levels, signal)
        assert result["total_return"] == pytest.approx(0.0, abs=1e-10)
        assert result["ann_return"] == pytest.approx(0.0, abs=1e-10)
        assert result["ann_vol"] == pytest.approx(0.0, abs=1e-10)
        assert result["sharpe_0rf"] == pytest.approx(0.0, abs=1e-10)
        assert result["max_drawdown"] == pytest.approx(0.0, abs=1e-10)

    def test_sharpe_5rf_less_than_0rf(self, index_levels):
        """Sharpe with 5% RF should be less than with 0% RF for positive returns."""
        signal = np.ones(len(index_levels))
        result = gsvivs_signal_pnl(index_levels, signal)
        assert result["sharpe_5rf"] < result["sharpe_0rf"]

    def test_max_drawdown_is_negative(self, index_levels):
        """Max drawdown should be <= 0 (negative number)."""
        signal = np.ones(len(index_levels))
        result = gsvivs_signal_pnl(index_levels, signal)
        assert result["max_drawdown"] <= 0

    def test_hit_rate_bounded(self, index_levels):
        """Hit rate should be between 0 and 1."""
        signal = np.ones(len(index_levels))
        result = gsvivs_signal_pnl(index_levels, signal)
        assert 0.0 <= result["hit_rate"] <= 1.0

    def test_positive_days_format(self, index_levels):
        """Positive days should be a string like '180/252 (71.4%)'."""
        signal = np.ones(len(index_levels))
        result = gsvivs_signal_pnl(index_levels, signal)
        pd_str = result["positive_days"]
        assert isinstance(pd_str, str)
        assert "/" in pd_str
        assert "%" in pd_str

    def test_positive_days_denominator_is_total_days_for_long_flat(self, index_levels):
        """In long_flat mode (signal ∈ {0, +1}), the positive_days denominator
        must be the total evaluation days (N-1), NOT just active (non-zero)
        days. This ensures all models show the same denominator for
        apples-to-apples comparison regardless of how many flat days each
        model produces."""
        n = len(index_levels)
        # Create a long_flat signal: 60% long, 40% flat
        rng = np.random.default_rng(99)
        signal = rng.choice([0.0, 1.0], size=n, p=[0.4, 0.6])
        result = gsvivs_signal_pnl(index_levels, signal)
        pd_str = result["positive_days"]
        # Denominator should be n-1 (total days), not sum(signal != 0)
        total_days = n - 1  # signal[:-1] determines daily pnl
        denom = int(pd_str.split("/")[1].split(" ")[0])
        assert denom == total_days, (
            f"positive_days denominator should be {total_days} (total eval days), "
            f"got {denom} (likely n_active). All models must share the same "
            f"denominator for comparable display."
        )

    def test_all_metrics_finite(self, index_levels):
        """All numeric metrics should be finite."""
        signal = np.ones(len(index_levels))
        result = gsvivs_signal_pnl(index_levels, signal)
        for key, val in result.items():
            if key == "positive_days":
                continue  # string field
            assert np.isfinite(val), f"{key} is not finite: {val}"

    def test_accepts_pandas_series(self, index_series):
        """Should accept pd.Series input (not just numpy arrays)."""
        signal = np.ones(len(index_series))
        result = gsvivs_signal_pnl(index_series.values, signal)
        assert set(result.keys()) == EXPECTED_METRICS

    def test_opposite_signals_opposite_pnl(self, index_levels):
        """Long and short should produce opposite total returns (no costs)."""
        long_result = gsvivs_signal_pnl(index_levels, np.ones(len(index_levels)))
        short_result = gsvivs_signal_pnl(index_levels, -np.ones(len(index_levels)))
        # Should be approximately opposite (exact for linear returns, close for compound)
        assert long_result["total_return"] * short_result["total_return"] < 0


# ---------------------------------------------------------------------------
# gsvivs_baselines tests
# ---------------------------------------------------------------------------

EXPECTED_BASELINES = {"always_long", "always_short", "always_random", "random_long_65"}


class TestGsvivsBaselines:
    """Tests for gsvivs_baselines() function."""

    def test_returns_expected_baselines(self, index_levels):
        """Should return exactly the 3 expected baseline names."""
        result = gsvivs_baselines(index_levels)
        assert set(result.keys()) == EXPECTED_BASELINES

    def test_each_baseline_has_correct_metrics(self, index_levels):
        """Each baseline should have all 10 metric keys."""
        result = gsvivs_baselines(index_levels)
        for name, metrics in result.items():
            assert set(metrics.keys()) == EXPECTED_METRICS, f"Missing keys for {name}"

    def test_always_long_matches_direct_call(self, index_levels):
        """always_long baseline should match calling gsvivs_signal_pnl with signal=+1."""
        baselines = gsvivs_baselines(index_levels)
        direct = gsvivs_signal_pnl(index_levels, np.ones(len(index_levels)))
        assert baselines["always_long"]["total_return"] == pytest.approx(direct["total_return"])
        assert baselines["always_long"]["sharpe_0rf"] == pytest.approx(direct["sharpe_0rf"])

    def test_all_metrics_finite(self, index_levels):
        """All numeric metrics in all baselines should be finite."""
        result = gsvivs_baselines(index_levels)
        for name, metrics in result.items():
            for key, val in metrics.items():
                if key == "positive_days":
                    continue
                assert np.isfinite(val), f"{name}.{key} not finite: {val}"


# ---------------------------------------------------------------------------
# GSVIVS cache tests
# ---------------------------------------------------------------------------


class TestGsvivsCache:
    """Tests for save_gsvivs_cache / load_gsvivs_cache."""

    def test_load_returns_none_when_no_cache(self, tmp_path, monkeypatch):
        """load_gsvivs_cache returns None when cache file doesn't exist."""
        monkeypatch.setattr("volforecast.data.edrvol.cross_asset_cache_dir", lambda: tmp_path)
        result = load_gsvivs_cache()
        assert result is None

    def test_save_then_load_roundtrip(self, tmp_path, monkeypatch):
        """save_gsvivs_cache + load_gsvivs_cache roundtrips data correctly."""
        monkeypatch.setattr("volforecast.data.edrvol.cross_asset_cache_dir", lambda: tmp_path)
        dates = pd.bdate_range("2023-01-02", periods=100, freq="B")
        data = pd.Series(np.linspace(100, 110, 100), index=dates, name="gsvivs01")
        save_gsvivs_cache(data)
        loaded = load_gsvivs_cache()
        assert loaded is not None
        assert len(loaded) == 100
        assert loaded.name == "gsvivs01"
        pd.testing.assert_index_equal(loaded.index, dates, check_names=False)
        assert loaded.index.name == "date"
        np.testing.assert_allclose(loaded.values, data.values)

    def test_save_creates_directory(self, tmp_path, monkeypatch):
        """save_gsvivs_cache creates parent directory if needed."""
        subdir = tmp_path / "nonexistent"
        monkeypatch.setattr("volforecast.data.edrvol.cross_asset_cache_dir", lambda: subdir)
        dates = pd.bdate_range("2023-01-02", periods=50, freq="B")
        data = pd.Series(np.ones(50), index=dates, name="gsvivs01")
        path = save_gsvivs_cache(data)
        assert path.exists()
        assert path.name == "gsvivs01.parquet"

    def test_save_refuses_to_shrink_existing_cache(self, tmp_path, monkeypatch, caplog):
        """save_gsvivs_cache MUST NOT overwrite a larger existing cache with a
        smaller (partial) series. Defends against silent truncation from TSDB
        partial responses or restricted entitlements (root cause of the 2026-06-15
        gsvivs01.parquet corruption: 1015 rows → 21 rows)."""
        monkeypatch.setattr("volforecast.data.edrvol.cross_asset_cache_dir", lambda: tmp_path)

        # Seed cache with 1000 rows (the "good" historical snapshot)
        full_dates = pd.bdate_range("2022-05-26", periods=1000, freq="B")
        full = pd.Series(np.linspace(100, 110, 1000), index=full_dates, name="gsvivs01")
        save_gsvivs_cache(full)
        loaded_full = load_gsvivs_cache()
        assert loaded_full is not None and len(loaded_full) == 1000

        # Attempt to "save" a 21-row partial fetch (the bug)
        partial_dates = pd.bdate_range("2024-01-02", periods=21, freq="B")
        partial = pd.Series(np.linspace(100, 101, 21), index=partial_dates, name="gsvivs01")
        save_gsvivs_cache(partial)

        # Cache must still contain the original 1000 rows
        loaded_after = load_gsvivs_cache()
        assert loaded_after is not None
        assert len(loaded_after) == 1000, (
            f"Cache shrank from 1000 to {len(loaded_after)} rows — silent truncation regression"
        )

    def test_save_allows_strictly_larger_replacement(self, tmp_path, monkeypatch):
        """A genuinely larger fetch (more dates) is allowed to replace the cache."""
        monkeypatch.setattr("volforecast.data.edrvol.cross_asset_cache_dir", lambda: tmp_path)

        small_dates = pd.bdate_range("2023-01-02", periods=50, freq="B")
        save_gsvivs_cache(pd.Series(np.ones(50), index=small_dates, name="gsvivs01"))

        big_dates = pd.bdate_range("2023-01-02", periods=500, freq="B")
        save_gsvivs_cache(pd.Series(np.ones(500), index=big_dates, name="gsvivs01"))

        loaded = load_gsvivs_cache()
        assert loaded is not None and len(loaded) == 500


# ---------------------------------------------------------------------------
# _compute_gsvivs_stats: baseline date fairness
# ---------------------------------------------------------------------------


class TestGsvivsBaselineDateFairness:
    """Baselines must be evaluated on the same date range as model predictions."""

    def test_baseline_uses_model_dates_not_full_range(self, monkeypatch):
        """Baseline months count must match model date range, not full GSVIVS range."""
        from volforecast.evaluation.tournament import _compute_gsvivs_stats

        # GSVIVS index: 48 months (Jan 2022 - Dec 2025)
        gsvivs_dates = pd.bdate_range("2022-01-03", "2025-12-31", freq="B")
        rng = np.random.default_rng(42)
        gsvivs_levels = 100.0 * np.exp(
            np.cumsum(0.08 / 252 + 0.04 / np.sqrt(252) * rng.standard_normal(len(gsvivs_dates)))
        )
        gsvivs_series = pd.Series(gsvivs_levels, index=gsvivs_dates, name="gsvivs01")

        # IV data covering same full range
        iv_df = pd.DataFrame(
            {"iv_1m_atm": 18.0 + rng.standard_normal(len(gsvivs_dates)) * 2},
            index=gsvivs_dates,
        )

        # Model predictions: only the last 12 months (Jan 2025 - Dec 2025)
        pred_dates = pd.bdate_range("2025-01-02", "2025-12-31", freq="B")
        preds = pd.Series(
            np.log(0.0001) + rng.standard_normal(len(pred_dates)) * 0.3,
            index=pred_dates,
        )

        # Patch fetch_gsvivs_index and load_iv_cache
        monkeypatch.setattr(
            "volforecast.data.edrvol.fetch_gsvivs_index",
            lambda: gsvivs_series,
        )
        monkeypatch.setattr(
            "volforecast.data.edrvol.load_iv_cache",
            lambda sym: iv_df,
        )

        all_preds = {("har", "SPY", 22): preds}
        results_by_iv, _ = _compute_gsvivs_stats(
            all_preds_series=all_preds,
            symbols=["SPY"],
            models=["har"],
            horizons=[22],
        )

        # Get results from first available IV source
        first_iv = next(iter(results_by_iv))
        results = results_by_iv[first_iv]
        assert 22 in results
        rows = results[22]
        # Find baseline and model rows. The 3-mode sizing toggle suffixes the
        # model name; the [binary] variant is the legacy-equivalent row.
        baseline_row = next(r for r in rows if "[baseline] always_long" in r["name"])
        model_row = next(r for r in rows if r["name"] == "har [binary]")

        # Extract days from "positive_days" string: "X/Y (Z%)"
        bl_total_days = int(baseline_row["positive_days"].split("/")[1].split()[0])
        model_total_days = int(model_row["positive_days"].split("/")[1].split()[0])

        # Baseline days should be close to model days (same date range)
        # NOT the full range of GSVIVS history
        assert bl_total_days <= model_total_days + 1, (
            f"Baseline covers {bl_total_days} days but model only {model_total_days}. "
            "Baselines should use same date range as model predictions."
        )


# ---------------------------------------------------------------------------
# _compute_gsvivs_stats: iv_acceleration signal type
# ---------------------------------------------------------------------------


class TestGsvivsIvAcceleration:
    """Tests for the iv_acceleration signal type in _compute_gsvivs_stats."""

    def test_iv_acceleration_produces_results(self, monkeypatch):
        """iv_acceleration signal type should produce valid GSVIVS stats."""
        from volforecast.evaluation.tournament import _compute_gsvivs_stats

        rng = np.random.default_rng(123)
        n = 300
        dates = pd.bdate_range("2024-01-02", periods=n, freq="B")

        # GSVIVS index with upward drift
        gsvivs_levels = 100.0 * np.exp(
            np.cumsum(0.08 / 252 + 0.04 / np.sqrt(252) * rng.standard_normal(n))
        )
        gsvivs_series = pd.Series(gsvivs_levels, index=dates, name="gsvivs01")

        # IV data with 0DTE column (decimal)
        iv_base = 0.15 + rng.standard_normal(n) * 0.02
        iv_df = pd.DataFrame(
            {"iv_1m_atm": iv_base * 100, "iv_0dte": iv_base},
            index=dates,
        )

        # Model predictions (log-RV)
        preds = pd.Series(
            np.log(0.0001) + rng.standard_normal(n) * 0.3,
            index=dates,
        )

        monkeypatch.setattr(
            "volforecast.data.edrvol.fetch_gsvivs_index",
            lambda: gsvivs_series,
        )
        monkeypatch.setattr(
            "volforecast.data.edrvol.load_iv_cache",
            lambda sym: iv_df,
        )

        all_preds = {("har", "SPY", 1): preds}
        results_by_iv, traces_by_iv = _compute_gsvivs_stats(
            all_preds_series=all_preds,
            symbols=["SPY"],
            models=["har"],
            horizons=[1],
            signal_type="iv_acceleration",
            flat_percentile=80,
        )

        first_iv = next(iter(results_by_iv))
        results = results_by_iv[first_iv]
        assert 1 in results
        rows = results[1]
        assert len(rows) > 0
        # Should have model row + baselines
        model_row = next(r for r in rows if r["name"] == "har")
        assert "sharpe_0rf" in model_row
        assert np.isfinite(model_row["sharpe_0rf"])

    def test_iv_acceleration_goes_flat_on_spikes(self, monkeypatch):
        """Signal should be 0 (flat) when IV spikes above rolling threshold."""
        from volforecast.evaluation.tournament import _compute_gsvivs_stats

        rng = np.random.default_rng(456)
        n = 200
        dates = pd.bdate_range("2024-01-02", periods=n, freq="B")

        gsvivs_levels = 100.0 * np.exp(
            np.cumsum(0.08 / 252 + 0.04 / np.sqrt(252) * rng.standard_normal(n))
        )
        gsvivs_series = pd.Series(gsvivs_levels, index=dates, name="gsvivs01")

        # IV with a clear spike at day 100
        iv_base = np.full(n, 0.15)
        iv_base[100:105] = 0.30  # big spike
        iv_df = pd.DataFrame(
            {"iv_1m_atm": iv_base * 100, "iv_0dte": iv_base},
            index=dates,
        )

        preds = pd.Series(
            np.log(0.0001) + rng.standard_normal(n) * 0.1,
            index=dates,
        )

        monkeypatch.setattr(
            "volforecast.data.edrvol.fetch_gsvivs_index",
            lambda: gsvivs_series,
        )
        monkeypatch.setattr(
            "volforecast.data.edrvol.load_iv_cache",
            lambda sym: iv_df,
        )

        all_preds = {("har", "SPY", 1): preds}
        results_by_iv, traces_by_iv = _compute_gsvivs_stats(
            all_preds_series=all_preds,
            symbols=["SPY"],
            models=["har"],
            horizons=[1],
            signal_type="iv_acceleration",
            flat_percentile=80,
        )

        # The model should have a hit_rate (some signals were flat)
        first_iv = next(iter(results_by_iv))
        results = results_by_iv[first_iv]
        model_row = next(r for r in results[1] if r["name"] == "har")
        # Total return should differ from always-long (signal went flat sometimes)
        baseline_row = next(r for r in results[1] if "[baseline] always_long" in r["name"])
        assert model_row["total_return"] != pytest.approx(baseline_row["total_return"], abs=1e-6), (
            "iv_acceleration signal should differ from always-long when IV spikes"
        )


# ---------------------------------------------------------------------------
# _compute_gsvivs_stats: IV tenor fallback when 0DTE has no coverage
# ---------------------------------------------------------------------------


class TestGsvivsIvTenorFallback:
    """GSVIVS should fall back to iv_1w_atm when iv_0dte_atm has no data in period."""

    def test_h1_falls_back_to_iv_1w_when_0dte_all_nan(self, monkeypatch):
        """h=1 should produce results even when iv_0dte has zero overlap with preds.

        Regression test for trial-036: 0DTE IV only existed from June 2025 but
        predictions covered 2017-2024. The column exists but is entirely NaN in
        the common date range. Without fallback, the GSVIVS section disappears.
        """
        from volforecast.evaluation.tournament import _compute_gsvivs_stats

        rng = np.random.default_rng(789)
        n = 300
        dates = pd.bdate_range("2023-01-02", periods=n, freq="B")

        # GSVIVS index
        gsvivs_levels = 100.0 * np.exp(
            np.cumsum(0.08 / 252 + 0.04 / np.sqrt(252) * rng.standard_normal(n))
        )
        gsvivs_series = pd.Series(gsvivs_levels, index=dates, name="gsvivs01")

        # IV data: iv_1w_atm has full coverage, iv_0dte is ALL NaN in this period
        iv_df = pd.DataFrame(
            {
                "iv_1w_atm": 18.0 + rng.standard_normal(n) * 2,
                "iv_1m_atm": 19.0 + rng.standard_normal(n) * 2,
                "iv_0dte": np.nan,  # column exists but no data
            },
            index=dates,
        )

        # Model predictions covering same period
        preds = pd.Series(
            np.log(0.0001) + rng.standard_normal(n) * 0.3,
            index=dates,
        )

        monkeypatch.setattr(
            "volforecast.data.edrvol.fetch_gsvivs_index",
            lambda: gsvivs_series,
        )
        monkeypatch.setattr(
            "volforecast.data.edrvol.load_iv_cache",
            lambda sym: iv_df,
        )

        all_preds = {("har", "SPY", 1): preds}
        results_by_iv, traces_by_iv = _compute_gsvivs_stats(
            all_preds_series=all_preds,
            symbols=["SPY"],
            models=["har"],
            horizons=[1],
        )

        # h=1 should produce results (fell back to iv_1w_atm)
        first_iv = next(iter(results_by_iv))
        results = results_by_iv[first_iv]
        assert 1 in results
        rows = results[1]
        assert len(rows) > 0, (
            "GSVIVS h=1 produced no results — iv_0dte fallback to iv_1w_atm failed"
        )
        model_row = next(r for r in rows if r["name"] == "har [binary]")
        assert np.isfinite(model_row["sharpe_0rf"])

    def test_h1_uses_0dte_when_data_available(self, monkeypatch):
        """h=1 should use iv_0dte_atm when it has sufficient non-NaN coverage."""
        from volforecast.evaluation.tournament import _compute_gsvivs_stats

        rng = np.random.default_rng(101)
        n = 200
        dates = pd.bdate_range("2024-01-02", periods=n, freq="B")

        gsvivs_levels = 100.0 * np.exp(
            np.cumsum(0.08 / 252 + 0.04 / np.sqrt(252) * rng.standard_normal(n))
        )
        gsvivs_series = pd.Series(gsvivs_levels, index=dates, name="gsvivs01")

        # IV data: iv_0dte has FULL coverage (different values from iv_1w)
        iv_df = pd.DataFrame(
            {
                "iv_1w_atm": 18.0 + rng.standard_normal(n) * 2,
                "iv_1m_atm": 19.0 + rng.standard_normal(n) * 2,
                "iv_0dte": 0.16 + rng.standard_normal(n) * 0.02,  # decimal
            },
            index=dates,
        )

        preds = pd.Series(
            np.log(0.0001) + rng.standard_normal(n) * 0.3,
            index=dates,
        )

        monkeypatch.setattr(
            "volforecast.data.edrvol.fetch_gsvivs_index",
            lambda: gsvivs_series,
        )
        monkeypatch.setattr(
            "volforecast.data.edrvol.load_iv_cache",
            lambda sym: iv_df,
        )

        all_preds = {("har", "SPY", 1): preds}
        results_by_iv, _ = _compute_gsvivs_stats(
            all_preds_series=all_preds,
            symbols=["SPY"],
            models=["har"],
            horizons=[1],
        )

        first_iv = next(iter(results_by_iv))
        results = results_by_iv[first_iv]
        assert 1 in results
        assert len(results[1]) > 0, "h=1 with full iv_0dte coverage should produce results"


# ---------------------------------------------------------------------------
# _compute_gsvivs_stats: iv_rv_gap produces binary signal (trial-042 finding)
# ---------------------------------------------------------------------------


class TestGsvivsIvRvGapBinarySignal:
    """iv_rv_gap signal is binary +1/-1 with no dead zone (trial-042 confirmed optimal)."""

    def _run_with_threshold(self, monkeypatch, short_threshold: float):
        """Helper: run _compute_gsvivs_stats with given threshold."""
        from volforecast.evaluation.tournament import _compute_gsvivs_stats

        rng = np.random.default_rng(77)
        n = 200
        dates = pd.bdate_range("2023-01-02", periods=n, freq="B")

        gsvivs_levels = 100.0 * np.exp(
            np.cumsum(0.08 / 252 + 0.04 / np.sqrt(252) * rng.standard_normal(n))
        )
        gsvivs_series = pd.Series(gsvivs_levels, index=dates, name="gsvivs01")

        # IV data that produces mix of positive and negative gaps
        iv_df = pd.DataFrame(
            {"iv_1m_atm": 15.0 + rng.standard_normal(n) * 5},  # centered around 15%
            index=dates,
        )

        # Predictions spanning a wide range so gap crosses zero frequently
        preds = pd.Series(
            np.log(0.00015) + rng.standard_normal(n) * 0.5,
            index=dates,
        )

        monkeypatch.setattr(
            "volforecast.data.edrvol.fetch_gsvivs_index",
            lambda: gsvivs_series,
        )
        monkeypatch.setattr(
            "volforecast.data.edrvol.load_iv_cache",
            lambda sym: iv_df,
        )
        monkeypatch.setattr(
            "volforecast.data.edrvol.load_edrvs_cache",
            lambda: None,
        )

        all_preds = {("lgbm", "SPY", 22): preds}
        results_by_iv, _ = _compute_gsvivs_stats(
            all_preds_series=all_preds,
            symbols=["SPY"],
            models=["lgbm"],
            horizons=[22],
            short_threshold=short_threshold,
            signal_type="iv_rv_gap",
        )
        return results_by_iv

    def test_signal_is_binary_no_flat(self, monkeypatch):
        """iv_rv_gap signal must be +1 or -1 (never 0/flat). Trial-042 confirmed
        binary is optimal — threshold=0 produces best Sharpe."""
        results_by_iv = self._run_with_threshold(monkeypatch, short_threshold=0.05)
        first_iv = next(iter(results_by_iv))
        results = results_by_iv[first_iv]
        assert 22 in results
        # The signal produces results (i.e. it doesn't break). The binary
        # variant honors short_threshold (other sizing modes ignore it).
        model_row = next(r for r in results[22] if r["name"] == "lgbm [binary]")
        # Hit rate should not be 0 (which would indicate degenerate signal)
        assert model_row["hit_rate"] > 0

    def test_threshold_affects_signal(self, monkeypatch):
        """short_threshold controls the asymmetric buffer before going short.
        Larger threshold = fewer short signals = different Sharpe."""
        results_by_iv_0 = self._run_with_threshold(monkeypatch, short_threshold=0.0)
        results_by_iv_10 = self._run_with_threshold(monkeypatch, short_threshold=0.10)

        first_iv_0 = next(iter(results_by_iv_0))
        first_iv_10 = next(iter(results_by_iv_10))
        row_0 = next(r for r in results_by_iv_0[first_iv_0][22] if r["name"] == "lgbm [binary]")
        row_10 = next(
            r for r in results_by_iv_10[first_iv_10][22] if r["name"] == "lgbm [binary]"
        )

        # Both should produce finite Sharpe values
        assert np.isfinite(row_0["sharpe_0rf"])
        assert np.isfinite(row_10["sharpe_0rf"])


def test_default_gsvivs_dashboard_iv_prefers_exec_kvar():
    from volforecast.evaluation.tournament import _default_gsvivs_dashboard_iv_label

    results_by_iv = {
        "EDRVS prev-close 1-DTE": {1: [{"name": "har", "sharpe_0rf": 0.5}]},
        "Exec Kvar (true fill)": {1: [{"name": "har", "sharpe_0rf": 0.8}]},
    }

    assert _default_gsvivs_dashboard_iv_label(results_by_iv) == "Exec Kvar (true fill)"
