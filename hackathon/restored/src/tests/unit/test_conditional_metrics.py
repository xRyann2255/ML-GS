"""Unit tests for conditional (turbulence-split) QLIKE and Diebold-Mariano.

Protocols:
- ``conditional_qlike_split`` implements the Zhang et al. (2025) "GNNHAR"
  Table 2 protocol: split observations by top-decile market-RV dates.
- ``conditional_dm`` implements the Fang & Slepaczuk (2026) Table 4 protocol:
  median-split (calm vs turbulent) or top-25% quantile split.

Both use panel-aware machinery — bucket membership is decided on DATES
(all cross-sections of a date share a bucket).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.evaluation.statistical_tests import (
    conditional_dm,
    conditional_qlike_split,
    diebold_mariano_test,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _synthetic_market_rv(n_dates: int = 100, seed: int = 7) -> pd.Series:
    """Date-indexed market RV. Values grow monotonically so the top decile
    is exactly the last 10% of dates (makes bucket assertions deterministic).
    """
    dates = pd.bdate_range("2022-01-03", periods=n_dates, freq="B")
    values = np.linspace(0.0001, 0.001, n_dates)
    return pd.Series(values, index=dates, name="market_rv")


# ---------------------------------------------------------------------------
# conditional_qlike_split
# ---------------------------------------------------------------------------


class TestConditionalQlikeSplit:
    def test_returns_expected_keys(self):
        mrv = _synthetic_market_rv(100)
        rng = np.random.default_rng(0)
        y_true = rng.normal(-8.0, 0.5, 100)
        y_pred = y_true + rng.normal(0.0, 0.2, 100)

        out = conditional_qlike_split(
            y_true, y_pred, dates=mrv.index, market_rv=mrv, quantile=0.9
        )
        assert set(out.keys()) == {"qlike_calm", "qlike_turb", "n_turb"}

    def test_top_decile_threshold_and_count(self):
        """With monotonically increasing market RV, top decile = last 10 dates."""
        mrv = _synthetic_market_rv(100)
        rng = np.random.default_rng(1)
        y_true = rng.normal(-8.0, 0.5, 100)
        y_pred = y_true + rng.normal(0.0, 0.2, 100)

        out = conditional_qlike_split(
            y_true, y_pred, dates=mrv.index, market_rv=mrv, quantile=0.9
        )
        # Top 10% of 100 monotonically-increasing values = 10 turbulent dates
        assert out["n_turb"] == 10

    def test_panel_bucket_by_date_all_symbols_same_bucket(self):
        """In a panel (3 symbols × 50 dates), turbulent bucket must contain
        3 × n_turb_dates observations — bucket membership is by date, not by row.
        """
        mrv = _synthetic_market_rv(50)
        n_syms = 3
        # date_major panel: rows for each date come as N symbol observations in a row
        dates_panel = np.repeat(mrv.index.values, n_syms)
        rng = np.random.default_rng(2)
        y_true = rng.normal(-8.0, 0.5, len(dates_panel))
        y_pred = y_true + rng.normal(0.0, 0.2, len(dates_panel))

        out = conditional_qlike_split(
            y_true, y_pred, dates=dates_panel, market_rv=mrv, quantile=0.9
        )
        # Top 10% of 50 dates = 5 turbulent dates × 3 symbols = 15 obs
        assert out["n_turb"] == 15

    def test_planted_turbulent_only_edge(self):
        """Model A beats B ONLY on turbulent dates → qlike_turb(A) < qlike_turb(B),
        qlike_calm(A) ≈ qlike_calm(B).
        """
        mrv = _synthetic_market_rv(200)
        turb_thresh = mrv.quantile(0.9)
        turb_mask = (mrv >= turb_thresh).values  # bool array, len 200

        rng = np.random.default_rng(3)
        y_true = rng.normal(-8.0, 0.5, 200)

        # Calm dates: both A and B use the same noisy prediction
        common_noise = rng.normal(0.0, 0.30, 200)
        pred_a = y_true + common_noise
        pred_b = y_true + common_noise

        # Turbulent dates: A predicts perfectly, B is very noisy
        pred_a_turb = y_true.copy()
        pred_b_turb = y_true + rng.normal(0.0, 0.80, 200)
        pred_a = np.where(turb_mask, pred_a_turb, pred_a)
        pred_b = np.where(turb_mask, pred_b_turb, pred_b)

        out_a = conditional_qlike_split(y_true, pred_a, mrv.index, mrv, quantile=0.9)
        out_b = conditional_qlike_split(y_true, pred_b, mrv.index, mrv, quantile=0.9)

        # A strictly better on turbulent
        assert out_a["qlike_turb"] < out_b["qlike_turb"]
        # A and B tied on calm (identical predictions there)
        assert out_a["qlike_calm"] == pytest.approx(out_b["qlike_calm"], rel=1e-9)


# ---------------------------------------------------------------------------
# conditional_dm
# ---------------------------------------------------------------------------


class TestConditionalDm:
    def _build_losses(self, n=300, seed=42):
        mrv = _synthetic_market_rv(n)
        rng = np.random.default_rng(seed)
        loss_a = np.abs(rng.normal(0.05, 0.02, n))
        loss_b = np.abs(rng.normal(0.06, 0.02, n))
        return loss_a, loss_b, mrv

    def test_median_split_returns_expected_keys(self):
        loss_a, loss_b, mrv = self._build_losses()
        out = conditional_dm(
            loss_a, loss_b, dates=mrv.index, market_rv=mrv, split="median", horizon=1
        )
        for k in ("dm_stat_turb", "p_value_turb", "dm_stat_calm", "p_value_calm",
                  "n_turb", "n_calm"):
            assert k in out
        # Both buckets have observations
        assert out["n_turb"] > 0
        assert out["n_calm"] > 0

    def test_q75_split_uses_top_quartile(self):
        loss_a, loss_b, mrv = self._build_losses(n=400)
        out = conditional_dm(
            loss_a, loss_b, dates=mrv.index, market_rv=mrv, split="q75", horizon=1
        )
        # Top quartile of 400 monotonic values = 100 turbulent
        assert out["n_turb"] == 100
        assert out["n_calm"] == 300

    def test_invalid_split_raises(self):
        loss_a, loss_b, mrv = self._build_losses()
        with pytest.raises(ValueError):
            conditional_dm(
                loss_a, loss_b, dates=mrv.index, market_rv=mrv, split="bogus"
            )

    def test_n_cross_sections_plumbed_to_hac(self):
        """When n_cross_sections is set, the conditional DM must date-average
        the loss differentials before HAC — same behavior as the unconditional
        panel-aware test.

        We construct a small panel and check that conditional_dm on the full
        (non-filtered) window matches diebold_mariano_test with the same
        n_cross_sections.
        """
        n_dates = 60
        n_syms = 4
        mrv = _synthetic_market_rv(n_dates)
        rng = np.random.default_rng(101)

        # date_major panel: date0[s0..s3], date1[s0..s3], ...
        dates_panel = np.repeat(mrv.index.values, n_syms)
        loss_a = np.abs(rng.normal(0.05, 0.02, n_dates * n_syms))
        loss_b = np.abs(rng.normal(0.055, 0.02, n_dates * n_syms))

        # Push the median so ALL dates fall into the turbulent bucket for split='median'.
        # We do this by constructing a market_rv where every value equals the median
        # threshold plus epsilon → q75 has some in, some out, but we test something
        # cleaner: apply conditional_dm and check turb+calm counts add to n_syms*n_dates.
        out = conditional_dm(
            loss_a, loss_b, dates=dates_panel, market_rv=mrv,
            split="median", horizon=1, n_cross_sections=n_syms,
            panel_order="date_major",
        )
        # All observations accounted for (calm + turb + ties on median = total,
        # ties on median get bucketed as calm by convention)
        assert out["n_turb"] + out["n_calm"] == n_dates * n_syms

        # Now verify n_cross_sections plumbing: build the unconditional DM
        # from the same losses using diebold_mariano_test with n_cross_sections
        # set, and compare with the "no-op split" scenario (whole panel = one bucket).
        # We use a market_rv that puts every date on the same side of the split.
        mrv_all_low = pd.Series(
            np.full(n_dates, 1e-9), index=mrv.index, name="market_rv"
        )
        out_all_calm = conditional_dm(
            loss_a, loss_b, dates=dates_panel, market_rv=mrv_all_low,
            split="q75", horizon=1, n_cross_sections=n_syms,
            panel_order="date_major",
        )
        # No date can exceed q75 threshold (all identical) → strict >= means
        # ties on q75 are the whole panel; since split='q75' uses >= threshold,
        # count depends on tie handling. Instead of asserting on counts,
        # assert that the DM stat for whichever bucket got all obs equals
        # the unconditional panel DM stat.
        ref = diebold_mariano_test(
            loss_a, loss_b, horizon=1, n_cross_sections=n_syms,
            panel_order="date_major",
        )
        # Pick whichever bucket got all obs
        if out_all_calm["n_turb"] == n_dates * n_syms:
            assert out_all_calm["dm_stat_turb"] == pytest.approx(ref["dm_stat"], rel=1e-9)
        else:
            assert out_all_calm["n_calm"] == n_dates * n_syms
            assert out_all_calm["dm_stat_calm"] == pytest.approx(ref["dm_stat"], rel=1e-9)
