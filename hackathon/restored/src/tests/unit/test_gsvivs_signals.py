"""Failing tests for GsvivsSignalsLayer (plan 096, Step 3 — TDD).

These tests define the contract for a yet-to-be-implemented feature layer
that reproduces the 73 features used by the GSVIVS01 short-variance strategy.

Until Step 4 lands, importing ``volforecast.features.gsvivs_signals`` raises
``ModuleNotFoundError`` and every test in this module fails at collection.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.features.gsvivs_signals import GsvivsSignalsLayer
from volforecast.registry import FEATURE_REGISTRY

# ---------------------------------------------------------------------------
# Expected feature spec (73 total = 6+6+6+6+12+4+12+15+6)
# ---------------------------------------------------------------------------

SPX_RETURN_COLS = [
    "spx_ret_1d",
    "spx_ret_3d",
    "spx_ret_5d",
    "spx_rea_1d",
    "spx_rea_5d",
    "spx_rea_20d",
]
VIX_RETURN_COLS = [
    "vix_ret_1d",
    "vix_ret_3d",
    "vix_ret_5d",
    "vix_rea_1d",
    "vix_rea_5d",
    "vix_rea_20d",
]
VX1_RETURN_COLS = [
    "vx1_ret_1d",
    "vx1_ret_3d",
    "vx1_ret_5d",
    "vx1_rea_1d",
    "vx1_rea_5d",
    "vx1_rea_20d",
]
VIX_VOL_COLS = [
    "vix_vol_ret_1d",
    "vix_vol_ret_3d",
    "vix_vol_ret_5d",
    "vix_vol_diff_1d",
    "vix_vol_diff_3d",
    "vix_vol_diff_5d",
]
VIX_SKEW_COLS = [
    "vix_skew_50d25d",
    "vix_skew_50d25d_diff_1d",
    "vix_skew_50d25d_diff_3d",
    "vix_skew_50d25d_diff_5d",
    "vix_skew_50d5d",
    "vix_skew_50d5d_diff_1d",
    "vix_skew_50d5d_diff_3d",
    "vix_skew_50d5d_diff_5d",
    "vix_skew_25d5d",
    "vix_skew_25d5d_diff_1d",
    "vix_skew_25d5d_diff_3d",
    "vix_skew_25d5d_diff_5d",
]
VIX_TS_COLS = [
    "vix_ts_level",
    "vix_ts_diff_1d",
    "vix_ts_diff_3d",
    "vix_ts_diff_5d",
]
SPX_1M_SKEW_COLS = [
    "spx_skew_50d25d_1m",
    "spx_skew_50d25d_1m_diff_1d",
    "spx_skew_50d25d_1m_diff_3d",
    "spx_skew_50d25d_1m_diff_5d",
    "spx_skew_50d5d_1m",
    "spx_skew_50d5d_1m_diff_1d",
    "spx_skew_50d5d_1m_diff_3d",
    "spx_skew_50d5d_1m_diff_5d",
    "spx_skew_25d5d_1m",
    "spx_skew_25d5d_1m_diff_1d",
    "spx_skew_25d5d_1m_diff_3d",
    "spx_skew_25d5d_1m_diff_5d",
]
SPX_SKEW_TS_COLS = [
    "spx_skew_50d25d_3m",
    "spx_skew_50d5d_3m",
    "spx_skew_25d5d_3m",
    "spx_skew_ts_50d25d",
    "spx_skew_ts_50d25d_ret_1d",
    "spx_skew_ts_50d25d_ret_3d",
    "spx_skew_ts_50d25d_ret_5d",
    "spx_skew_ts_50d5d",
    "spx_skew_ts_50d5d_ret_1d",
    "spx_skew_ts_50d5d_ret_3d",
    "spx_skew_ts_50d5d_ret_5d",
    "spx_skew_ts_25d5d",
    "spx_skew_ts_25d5d_ret_1d",
    "spx_skew_ts_25d5d_ret_3d",
    "spx_skew_ts_25d5d_ret_5d",
]
CREDIT_COLS = [
    "credit_ig_ret_1d",
    "credit_ig_ret_3d",
    "credit_ig_ret_5d",
    "credit_hy_ret_1d",
    "credit_hy_ret_3d",
    "credit_hy_ret_5d",
]

ALL_EXPECTED_COLS = (
    SPX_RETURN_COLS
    + VIX_RETURN_COLS
    + VX1_RETURN_COLS
    + VIX_VOL_COLS
    + VIX_SKEW_COLS
    + VIX_TS_COLS
    + SPX_1M_SKEW_COLS
    + SPX_SKEW_TS_COLS
    + CREDIT_COLS
)
assert len(ALL_EXPECTED_COLS) == 73, "Test spec bug: expected 73 columns"


# ---------------------------------------------------------------------------
# Fixture — synthetic enriched daily data with every column the layer needs
# ---------------------------------------------------------------------------

_ENRICHED_COLUMNS = [
    "close",
    "vix",
    "vx1",
    "vix_iv_1m_atm",
    "vix_iv_1m_25dc",
    "vix_iv_1m_5dc",
    "iv_1m_atm",
    "iv_1m_25dp",
    "iv_1m_5dp",
    "iv_3m_atm",
    "iv_3m_25dp",
    "iv_3m_5dp",
    "credit_ig_5y",
    "credit_hy_5y",
]


@pytest.fixture
def daily_data() -> pd.DataFrame:
    """~100 business days of synthetic enriched data with realistic ranges."""
    rng = np.random.RandomState(42)
    dates = pd.bdate_range("2023-01-02", periods=100, freq="B")
    n = len(dates)

    # SPX random walk ~4000-5000
    spx = 4500.0 + np.cumsum(rng.normal(0.0, 20.0, n))

    # VIX and VX1 around 12-30
    vix = 18.0 + rng.normal(0.0, 3.0, n)
    vix = np.clip(vix, 10.0, 40.0)
    vx1 = vix + rng.normal(1.0, 0.5, n)  # front-month usually slight contango

    # VIX option IV surface (vol points, upward call skew for VIX)
    vix_iv_atm = 90.0 + rng.normal(0.0, 5.0, n)  # VVIX-like, ~90
    vix_iv_25dc = vix_iv_atm + rng.uniform(2.0, 8.0, n)
    vix_iv_5dc = vix_iv_25dc + rng.uniform(2.0, 8.0, n)

    # SPX put skew — deeper OTM puts have higher IV
    iv_1m_atm = 15.0 + rng.normal(0.0, 2.0, n)
    iv_1m_25dp = iv_1m_atm + rng.uniform(1.5, 4.0, n)
    iv_1m_5dp = iv_1m_25dp + rng.uniform(2.0, 6.0, n)

    iv_3m_atm = iv_1m_atm + rng.uniform(0.5, 2.0, n)
    iv_3m_25dp = iv_3m_atm + rng.uniform(1.0, 3.0, n)
    iv_3m_5dp = iv_3m_25dp + rng.uniform(1.5, 4.0, n)

    # Credit spreads in bps
    credit_ig = 80.0 + rng.normal(0.0, 5.0, n)
    credit_hy = 400.0 + rng.normal(0.0, 20.0, n)

    return pd.DataFrame(
        {
            "close": spx,
            "vix": vix,
            "vx1": vx1,
            "vix_iv_1m_atm": vix_iv_atm,
            "vix_iv_1m_25dc": vix_iv_25dc,
            "vix_iv_1m_5dc": vix_iv_5dc,
            "iv_1m_atm": iv_1m_atm,
            "iv_1m_25dp": iv_1m_25dp,
            "iv_1m_5dp": iv_1m_5dp,
            "iv_3m_atm": iv_3m_atm,
            "iv_3m_25dp": iv_3m_25dp,
            "iv_3m_5dp": iv_3m_5dp,
            "credit_ig_5y": credit_ig,
            "credit_hy_5y": credit_hy,
        },
        index=dates,
    )


def _compute(daily_data: pd.DataFrame) -> pd.DataFrame:
    """Call the layer's compute() the same way OptionsLayer is called."""
    layer = GsvivsSignalsLayer()
    return layer.compute(daily_data)


# ---------------------------------------------------------------------------
# Registration + shape contract
# ---------------------------------------------------------------------------


class TestGsvivsSignalsContract:
    def test_registration(self):
        """Importing the module registers 'gsvivs_signals' in FEATURE_REGISTRY."""
        # The top-level import above already triggers registration via the
        # @register_feature_layer decorator.
        assert "gsvivs_signals" in FEATURE_REGISTRY
        assert FEATURE_REGISTRY["gsvivs_signals"] is GsvivsSignalsLayer

    def test_feature_count(self, daily_data):
        result = _compute(daily_data)
        assert isinstance(result, pd.DataFrame)
        assert result.shape[1] == 73
        assert len(result) == len(daily_data)
        assert result.index.equals(daily_data.index)

    def test_feature_names(self, daily_data):
        result = _compute(daily_data)
        assert sorted(result.columns) == sorted(ALL_EXPECTED_COLS)


# ---------------------------------------------------------------------------
# Group 1 — SPX returns / realized
# ---------------------------------------------------------------------------


class TestSpxReturns:
    def test_spx_returns(self, daily_data):
        result = _compute(daily_data)
        close = daily_data["close"]

        pd.testing.assert_series_equal(
            result["spx_ret_1d"], close.pct_change(1), check_names=False
        )
        pd.testing.assert_series_equal(
            result["spx_ret_3d"], close.pct_change(3), check_names=False
        )
        pd.testing.assert_series_equal(
            result["spx_ret_5d"], close.pct_change(5), check_names=False
        )

        ret_1d = close.pct_change(1)
        pd.testing.assert_series_equal(
            result["spx_rea_1d"], ret_1d.abs() * np.sqrt(252), check_names=False
        )
        pd.testing.assert_series_equal(
            result["spx_rea_5d"], ret_1d.rolling(5).std() * np.sqrt(252), check_names=False
        )
        pd.testing.assert_series_equal(
            result["spx_rea_20d"], ret_1d.rolling(20).std() * np.sqrt(252), check_names=False
        )


# ---------------------------------------------------------------------------
# Group 2 — VIX returns / realized
# ---------------------------------------------------------------------------


class TestVixReturns:
    def test_vix_returns(self, daily_data):
        result = _compute(daily_data)
        vix = daily_data["vix"]

        pd.testing.assert_series_equal(result["vix_ret_1d"], vix.pct_change(1), check_names=False)
        pd.testing.assert_series_equal(result["vix_ret_3d"], vix.pct_change(3), check_names=False)
        pd.testing.assert_series_equal(result["vix_ret_5d"], vix.pct_change(5), check_names=False)

        ret_1d = vix.pct_change(1)
        pd.testing.assert_series_equal(
            result["vix_rea_1d"], ret_1d.abs() * np.sqrt(252), check_names=False
        )
        pd.testing.assert_series_equal(
            result["vix_rea_5d"], ret_1d.rolling(5).std() * np.sqrt(252), check_names=False
        )
        pd.testing.assert_series_equal(
            result["vix_rea_20d"], ret_1d.rolling(20).std() * np.sqrt(252), check_names=False
        )


# ---------------------------------------------------------------------------
# Group 3 — VX1 returns / realized
# ---------------------------------------------------------------------------


class TestVx1Returns:
    def test_vx1_returns(self, daily_data):
        result = _compute(daily_data)
        vx1 = daily_data["vx1"]

        pd.testing.assert_series_equal(result["vx1_ret_1d"], vx1.pct_change(1), check_names=False)
        pd.testing.assert_series_equal(result["vx1_ret_3d"], vx1.pct_change(3), check_names=False)
        pd.testing.assert_series_equal(result["vx1_ret_5d"], vx1.pct_change(5), check_names=False)

        ret_1d = vx1.pct_change(1)
        pd.testing.assert_series_equal(
            result["vx1_rea_1d"], ret_1d.abs() * np.sqrt(252), check_names=False
        )
        pd.testing.assert_series_equal(
            result["vx1_rea_5d"], ret_1d.rolling(5).std() * np.sqrt(252), check_names=False
        )
        pd.testing.assert_series_equal(
            result["vx1_rea_20d"], ret_1d.rolling(20).std() * np.sqrt(252), check_names=False
        )


# ---------------------------------------------------------------------------
# Group 4 — VIX vol-of-vol dynamics
# ---------------------------------------------------------------------------


class TestVixVolDynamics:
    def test_vix_vol_dynamics(self, daily_data):
        result = _compute(daily_data)
        s = daily_data["vix_iv_1m_atm"]

        pd.testing.assert_series_equal(
            result["vix_vol_ret_1d"], s.pct_change(1), check_names=False
        )
        pd.testing.assert_series_equal(
            result["vix_vol_ret_3d"], s.pct_change(3), check_names=False
        )
        pd.testing.assert_series_equal(
            result["vix_vol_ret_5d"], s.pct_change(5), check_names=False
        )

        pd.testing.assert_series_equal(result["vix_vol_diff_1d"], s.diff(1), check_names=False)
        pd.testing.assert_series_equal(result["vix_vol_diff_3d"], s.diff(3), check_names=False)
        pd.testing.assert_series_equal(result["vix_vol_diff_5d"], s.diff(5), check_names=False)


# ---------------------------------------------------------------------------
# Group 5 — VIX skew
# ---------------------------------------------------------------------------


class TestVixSkew:
    def test_vix_skew(self, daily_data):
        result = _compute(daily_data)
        atm = daily_data["vix_iv_1m_atm"]
        d25 = daily_data["vix_iv_1m_25dc"]
        d5 = daily_data["vix_iv_1m_5dc"]

        skew_50_25 = atm - d25
        skew_50_5 = atm - d5
        skew_25_5 = d25 - d5

        pd.testing.assert_series_equal(result["vix_skew_50d25d"], skew_50_25, check_names=False)
        pd.testing.assert_series_equal(result["vix_skew_50d5d"], skew_50_5, check_names=False)
        pd.testing.assert_series_equal(result["vix_skew_25d5d"], skew_25_5, check_names=False)

        for lag in (1, 3, 5):
            pd.testing.assert_series_equal(
                result[f"vix_skew_50d25d_diff_{lag}d"], skew_50_25.diff(lag), check_names=False
            )
            pd.testing.assert_series_equal(
                result[f"vix_skew_50d5d_diff_{lag}d"], skew_50_5.diff(lag), check_names=False
            )
            pd.testing.assert_series_equal(
                result[f"vix_skew_25d5d_diff_{lag}d"], skew_25_5.diff(lag), check_names=False
            )


# ---------------------------------------------------------------------------
# Group 6 — VIX term structure
# ---------------------------------------------------------------------------


class TestVixTermStructure:
    def test_vix_ts(self, daily_data):
        result = _compute(daily_data)
        vix = daily_data["vix"]
        vx1 = daily_data["vx1"]

        level = vix / vx1 - 1.0
        pd.testing.assert_series_equal(result["vix_ts_level"], level, check_names=False)
        for lag in (1, 3, 5):
            pd.testing.assert_series_equal(
                result[f"vix_ts_diff_{lag}d"], level.diff(lag), check_names=False
            )


# ---------------------------------------------------------------------------
# Group 7 — SPX 1M skew
# ---------------------------------------------------------------------------


class TestSpx1mSkew:
    def test_spx_1m_skew(self, daily_data):
        result = _compute(daily_data)
        atm = daily_data["iv_1m_atm"]
        p25 = daily_data["iv_1m_25dp"]
        p5 = daily_data["iv_1m_5dp"]

        skew_50_25 = atm - p25
        skew_50_5 = atm - p5
        skew_25_5 = p25 - p5

        pd.testing.assert_series_equal(
            result["spx_skew_50d25d_1m"], skew_50_25, check_names=False
        )
        pd.testing.assert_series_equal(result["spx_skew_50d5d_1m"], skew_50_5, check_names=False)
        pd.testing.assert_series_equal(result["spx_skew_25d5d_1m"], skew_25_5, check_names=False)

        for lag in (1, 3, 5):
            pd.testing.assert_series_equal(
                result[f"spx_skew_50d25d_1m_diff_{lag}d"],
                skew_50_25.diff(lag),
                check_names=False,
            )
            pd.testing.assert_series_equal(
                result[f"spx_skew_50d5d_1m_diff_{lag}d"],
                skew_50_5.diff(lag),
                check_names=False,
            )
            pd.testing.assert_series_equal(
                result[f"spx_skew_25d5d_1m_diff_{lag}d"],
                skew_25_5.diff(lag),
                check_names=False,
            )


# ---------------------------------------------------------------------------
# Group 8 — SPX skew term structure (1M/3M ratios)
# ---------------------------------------------------------------------------


class TestSpxSkewTermStructure:
    def test_spx_skew_ts(self, daily_data):
        result = _compute(daily_data)

        atm_1m = daily_data["iv_1m_atm"]
        p25_1m = daily_data["iv_1m_25dp"]
        p5_1m = daily_data["iv_1m_5dp"]

        atm_3m = daily_data["iv_3m_atm"]
        p25_3m = daily_data["iv_3m_25dp"]
        p5_3m = daily_data["iv_3m_5dp"]

        skew_50_25_3m = atm_3m - p25_3m
        skew_50_5_3m = atm_3m - p5_3m
        skew_25_5_3m = p25_3m - p5_3m

        pd.testing.assert_series_equal(
            result["spx_skew_50d25d_3m"], skew_50_25_3m, check_names=False
        )
        pd.testing.assert_series_equal(
            result["spx_skew_50d5d_3m"], skew_50_5_3m, check_names=False
        )
        pd.testing.assert_series_equal(
            result["spx_skew_25d5d_3m"], skew_25_5_3m, check_names=False
        )

        ts_50_25 = (atm_1m - p25_1m) / skew_50_25_3m
        ts_50_5 = (atm_1m - p5_1m) / skew_50_5_3m
        ts_25_5 = (p25_1m - p5_1m) / skew_25_5_3m

        pd.testing.assert_series_equal(
            result["spx_skew_ts_50d25d"], ts_50_25, check_names=False
        )
        pd.testing.assert_series_equal(result["spx_skew_ts_50d5d"], ts_50_5, check_names=False)
        pd.testing.assert_series_equal(result["spx_skew_ts_25d5d"], ts_25_5, check_names=False)

        for lag in (1, 3, 5):
            pd.testing.assert_series_equal(
                result[f"spx_skew_ts_50d25d_ret_{lag}d"],
                ts_50_25.pct_change(lag),
                check_names=False,
            )
            pd.testing.assert_series_equal(
                result[f"spx_skew_ts_50d5d_ret_{lag}d"],
                ts_50_5.pct_change(lag),
                check_names=False,
            )
            pd.testing.assert_series_equal(
                result[f"spx_skew_ts_25d5d_ret_{lag}d"],
                ts_25_5.pct_change(lag),
                check_names=False,
            )


# ---------------------------------------------------------------------------
# Group 9 — Credit CDS returns
# ---------------------------------------------------------------------------


class TestCreditReturns:
    def test_credit_returns(self, daily_data):
        result = _compute(daily_data)
        ig = daily_data["credit_ig_5y"]
        hy = daily_data["credit_hy_5y"]

        for lag in (1, 3, 5):
            pd.testing.assert_series_equal(
                result[f"credit_ig_ret_{lag}d"], ig.pct_change(lag), check_names=False
            )
            pd.testing.assert_series_equal(
                result[f"credit_hy_ret_{lag}d"], hy.pct_change(lag), check_names=False
            )


# ---------------------------------------------------------------------------
# Graceful degradation — missing enrichment columns should not crash
# ---------------------------------------------------------------------------


class TestMissingColumnsGraceful:
    def test_missing_columns_graceful(self, daily_data):
        """Dropping VIX option columns → VIX skew features all-NaN, no crash,
        output still has all 73 columns and the same index."""
        stripped = daily_data.drop(
            columns=["vix_iv_1m_atm", "vix_iv_1m_25dc", "vix_iv_1m_5dc"]
        )
        result = _compute(stripped)

        assert isinstance(result, pd.DataFrame)
        assert result.shape[1] == 73
        assert sorted(result.columns) == sorted(ALL_EXPECTED_COLS)
        assert result.index.equals(stripped.index)

        # All VIX skew + VIX vol-of-vol features should be entirely NaN
        vix_dependent = VIX_SKEW_COLS + VIX_VOL_COLS
        for col in vix_dependent:
            assert result[col].isna().all(), f"Expected all-NaN for {col} when inputs missing"

        # But features that do NOT depend on the dropped columns must still be
        # populated (at least partially — pct_change leaves NaN at head).
        assert result["spx_ret_1d"].notna().any()
        assert result["vix_ret_1d"].notna().any()
        assert result["credit_ig_ret_1d"].notna().any()
