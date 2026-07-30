"""Characterization + interface tests for the split tournament_table /
enrich_tournament_economics pair.

Workflow:
- Phase 0 fixtures (parquet files under src/tests/data/tournament_golden/) were
  generated from the legacy combined tournament_table(...) implementation.
- After the refactor, tournament_table returns ONLY stats columns and
  enrich_tournament_economics appends VT/DH columns + naive baseline rows.
- These tests assert that the composed output is bit-equal to the legacy
  golden parquets (rtol=1e-12) AND that the new signature is the minimal
  6-parameter stats-only API.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from volforecast.evaluation.statistical_tests import tournament_table
from volforecast.evaluation.tournament_economics import enrich_tournament_economics

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "data" / "tournament_golden"


# ---------------------------------------------------------------------------
# Shared fixture: must match workspace/tmp/generate_tournament_goldens.py
# ---------------------------------------------------------------------------


def _make_fixture_data(seed: int = 42, t_per_symbol: int = 300, n_symbols: int = 2):
    """Deterministic 3-model, 2-symbol fixture.

    Must produce byte-identical arrays to the script that generated the goldens.
    Do not change without regenerating src/tests/data/tournament_golden/*.parquet.
    """
    rng = np.random.default_rng(seed)
    T = t_per_symbol * n_symbols

    y_true = rng.normal(-8.0, 0.5, T)

    pred_har = y_true + rng.normal(0.0, 0.30, T)
    pred_harq = y_true + rng.normal(0.0, 0.25, T)
    pred_bad = y_true + rng.normal(0.0, 0.60, T)
    predictions = {"har": pred_har, "harq": pred_harq, "bad": pred_bad}

    daily_returns = rng.normal(0.0, 0.015, T)
    implied_vol = np.clip(0.20 + rng.normal(0.0, 0.03, T), 0.05, 0.60)

    spot_prices = np.empty(T)
    for s in range(n_symbols):
        seg = slice(s * t_per_symbol, (s + 1) * t_per_symbol)
        rets = rng.normal(0.0003, 0.012, t_per_symbol)
        spot_prices[seg] = 100.0 * np.exp(np.cumsum(rets))

    symbol_lengths = [t_per_symbol] * n_symbols
    return predictions, y_true, daily_returns, implied_vol, spot_prices, symbol_lengths


@pytest.fixture(scope="module")
def fixture_data():
    return _make_fixture_data()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_frame_close(actual: pd.DataFrame, expected: pd.DataFrame, rtol: float = 1e-12):
    """Cell-wise comparison: same shape, same columns, same string cells,
    floats close to rtol, NaN-positions preserved.
    """
    assert list(actual.columns) == list(expected.columns), (
        f"Columns differ.\n  actual:   {list(actual.columns)}\n  expected: {list(expected.columns)}"
    )
    assert len(actual) == len(expected), f"Row counts differ: {len(actual)} vs {len(expected)}"
    # Compare model column row-wise (preserves ordering check)
    assert actual["model"].tolist() == expected["model"].tolist(), "Row ordering changed"
    # Numeric / boolean columns
    for col in actual.columns:
        if col == "model":
            continue
        a = actual[col].to_numpy()
        e = expected[col].to_numpy()
        if a.dtype == bool or e.dtype == bool:
            assert np.array_equal(a, e), f"Boolean column {col!r} differs"
            continue
        # NaN positions must match
        a_nan = pd.isna(a)
        e_nan = pd.isna(e)
        assert np.array_equal(a_nan, e_nan), f"NaN pattern differs in column {col!r}"
        # Compare non-NaN values
        mask = ~a_nan
        if mask.any():
            np.testing.assert_allclose(
                a[mask].astype(np.float64),
                e[mask].astype(np.float64),
                rtol=rtol,
                atol=1e-15,
                err_msg=f"Numeric drift in column {col!r}",
            )


# ---------------------------------------------------------------------------
# Phase 0: Golden characterization tests — composed output equals legacy
# ---------------------------------------------------------------------------


class TestGoldenStatsOnly:
    def test_stats_only_matches_golden(self, fixture_data):
        preds, y_true, *_ = fixture_data
        actual = tournament_table(preds, y_true, baseline="har", horizon=1, mcs_bootstrap=200)
        expected = pd.read_parquet(GOLDEN_DIR / "stats_only.parquet")
        _assert_frame_close(actual, expected)


class TestGoldenWithVt:
    def test_vt_matches_golden(self, fixture_data):
        preds, y_true, daily_returns, _iv, _spot, sym_lengths = fixture_data
        stats = tournament_table(preds, y_true, baseline="har", horizon=1, mcs_bootstrap=200)
        actual = enrich_tournament_economics(
            stats,
            preds,
            y_true,
            daily_returns=daily_returns,
            symbol_lengths=sym_lengths,
        )
        expected = pd.read_parquet(GOLDEN_DIR / "with_vt.parquet")
        _assert_frame_close(actual, expected)


@pytest.mark.parametrize("mode", ["simple", "discrete", "realistic"])
class TestGoldenWithDh:
    def test_dh_matches_golden(self, fixture_data, mode):
        preds, y_true, _ret, iv, spot, sym_lengths = fixture_data
        stats = tournament_table(preds, y_true, baseline="har", horizon=1, mcs_bootstrap=200)
        actual = enrich_tournament_economics(
            stats,
            preds,
            y_true,
            implied_vol=iv,
            spot_prices=spot,
            symbol_lengths=sym_lengths,
            dh_mode=mode,
            horizon=1,
        )
        expected = pd.read_parquet(GOLDEN_DIR / f"with_dh_{mode}.parquet")
        _assert_frame_close(actual, expected)


class TestGoldenFull:
    """Load-bearing: composed VT+DH output matches the legacy combined call."""

    def test_full_matches_golden(self, fixture_data):
        preds, y_true, daily_returns, iv, spot, sym_lengths = fixture_data
        stats = tournament_table(preds, y_true, baseline="har", horizon=1, mcs_bootstrap=200)
        actual = enrich_tournament_economics(
            stats,
            preds,
            y_true,
            daily_returns=daily_returns,
            symbol_lengths=sym_lengths,
            implied_vol=iv,
            spot_prices=spot,
            dh_mode="realistic",
            horizon=1,
        )
        expected = pd.read_parquet(GOLDEN_DIR / "full.parquet")
        _assert_frame_close(actual, expected)


# ---------------------------------------------------------------------------
# Phase 1: New-interface specs
# ---------------------------------------------------------------------------


STATS_COLUMNS = [
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
]
VT_COLUMNS = ["vt_sharpe", "vt_pnl", "vt_max_dd", "vt_ann_ret", "vt_ann_vol"]
DH_COLUMNS = ["dh_sharpe", "dh_pnl", "dh_max_dd", "dh_hit_rate", "dh_ann_ret", "dh_ann_vol"]
NAIVE_BASELINE_NAMES = [
    "[baseline] always_long",
    "[baseline] always_short",
    "[baseline] always_flat",
    "[baseline] random",
    "[baseline] random_no_flip",
]


class TestTournamentTableSignature:
    def test_tournament_table_has_exactly_six_params(self):
        """The new tournament_table drops all 5 economic kwargs."""
        params = list(inspect.signature(tournament_table).parameters)
        assert params == [
            "predictions",
            "y_true",
            "baseline",
            "horizon",
            "mcs_alpha",
            "mcs_bootstrap",
            "n_cross_sections",
            "panel_order",
        ]

    def test_tournament_table_stats_only_columns(self, fixture_data):
        preds, y_true, *_ = fixture_data
        df = tournament_table(preds, y_true, baseline="har", horizon=1, mcs_bootstrap=200)
        assert list(df.columns) == STATS_COLUMNS
        assert len(df) == 3
        # No baseline rows, no economic columns
        assert not df["model"].str.startswith("[baseline]").any()

    def test_tournament_table_does_not_import_economics(self):
        """statistical_tests module must not import from economic_value or
        realistic_straddle (architectural invariant after the refactor)."""
        import volforecast.evaluation.statistical_tests as st_mod

        src = Path(st_mod.__file__).read_text()
        assert "economic_value" not in src, (
            "statistical_tests.py imports economic_value — should be moved to "
            "tournament_economics.py"
        )
        assert "realistic_straddle" not in src, (
            "statistical_tests.py imports realistic_straddle — should be moved to "
            "tournament_economics.py"
        )


class TestEnrichTournamentEconomics:
    def test_vt_only_adds_only_vt_cols(self, fixture_data):
        preds, y_true, daily_returns, _iv, _spot, sym_lengths = fixture_data
        stats = tournament_table(preds, y_true, baseline="har", horizon=1, mcs_bootstrap=200)
        out = enrich_tournament_economics(
            stats, preds, y_true, daily_returns=daily_returns, symbol_lengths=sym_lengths
        )
        assert list(out.columns) == STATS_COLUMNS + VT_COLUMNS
        # No DH cols, no baseline rows
        for col in DH_COLUMNS:
            assert col not in out.columns
        assert not out["model"].str.startswith("[baseline]").any()

    def test_dh_only_adds_dh_cols_and_five_baseline_rows(self, fixture_data):
        preds, y_true, _ret, iv, spot, sym_lengths = fixture_data
        stats = tournament_table(preds, y_true, baseline="har", horizon=1, mcs_bootstrap=200)
        out = enrich_tournament_economics(
            stats,
            preds,
            y_true,
            implied_vol=iv,
            spot_prices=spot,
            symbol_lengths=sym_lengths,
            dh_mode="simple",
            horizon=1,
        )
        assert list(out.columns) == STATS_COLUMNS + DH_COLUMNS
        # 3 model rows + 5 baseline rows
        assert len(out) == 8
        baseline_rows = out[out["model"].str.startswith("[baseline]")]
        assert baseline_rows["model"].tolist() == NAIVE_BASELINE_NAMES
        # Baseline rows have NaN stats, finite DH metrics
        for col in ["qlike", "mse", "r_squared", "mz_alpha", "dm_stat"]:
            assert baseline_rows[col].isna().all(), f"baseline {col!r} should be NaN"
        for col in DH_COLUMNS:
            assert np.isfinite(baseline_rows[col].to_numpy()).all(), (
                f"baseline {col!r} must be finite"
            )

    def test_empty_args_returns_input_unchanged(self, fixture_data):
        preds, y_true, *_ = fixture_data
        stats = tournament_table(preds, y_true, baseline="har", horizon=1, mcs_bootstrap=200)
        out = enrich_tournament_economics(stats, preds, y_true)
        assert list(out.columns) == STATS_COLUMNS
        assert len(out) == len(stats)
        _assert_frame_close(out, stats)

    def test_does_not_mutate_input_frame(self, fixture_data):
        preds, y_true, daily_returns, _iv, _spot, sym_lengths = fixture_data
        stats = tournament_table(preds, y_true, baseline="har", horizon=1, mcs_bootstrap=200)
        stats_before = stats.copy()
        _ = enrich_tournament_economics(
            stats, preds, y_true, daily_returns=daily_returns, symbol_lengths=sym_lengths
        )
        # Original frame must be untouched
        _assert_frame_close(stats, stats_before)

    def test_preserves_model_row_ordering(self, fixture_data):
        preds, y_true, daily_returns, iv, spot, sym_lengths = fixture_data
        stats = tournament_table(preds, y_true, baseline="har", horizon=1, mcs_bootstrap=200)
        model_order = stats["model"].tolist()
        out = enrich_tournament_economics(
            stats,
            preds,
            y_true,
            daily_returns=daily_returns,
            symbol_lengths=sym_lengths,
            implied_vol=iv,
            spot_prices=spot,
            dh_mode="simple",
            horizon=1,
        )
        # First N rows must preserve the stats sort; baselines append at bottom
        assert out["model"].iloc[: len(model_order)].tolist() == model_order
        assert out["model"].iloc[len(model_order) :].tolist() == NAIVE_BASELINE_NAMES
