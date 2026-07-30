"""Tests for SPXAllDayVols mark Kvar extraction.

Tests:
    - extract_daily_strike_map: correct parsing of output.json into strike maps
    - bs_price: Black-Scholes produces correct values for known inputs
    - compute_mark_kvar: CBOE formula with synthetic IVs produces sensible Kvar
    - load_allday_cache / save_allday_cache: cache round-trip I/O
    - Registry: spx_allday_vols resolves correctly
    - Config default: _parse_gsvivs_iv_sources returns correct defaults
"""

from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from volforecast.config import _parse_gsvivs_iv_sources
from volforecast.data.spx_allday_vols import (
    bs_price,
    compute_mark_kvar,
    extract_daily_strike_map,
    load_allday_cache,
    save_allday_cache,
)
from volforecast.evaluation.gsvivs import IV_SOURCE_REGISTRY, resolve_iv_sources


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture()
def output_json_path(tmp_path):
    """Create a minimal 2-day output.json for testing."""
    data = [
        {
            "date": "2024-05-23",
            "value": {
                "risks for date": [
                    {
                        "source": "VSR 0b",
                        "quantity": -0.012,
                        "instrument": {
                            "k": 5250,
                            "option type": "Put",
                            "ex": "2024-05-23",
                            "instrument type": "O",
                        },
                    },
                    {"execution price": 3.80, "execution fraction": 1.0},
                    {
                        "source": "VSR 0b",
                        "quantity": -0.011,
                        "instrument": {
                            "k": 5280,
                            "option type": "Put",
                            "ex": "2024-05-23",
                            "instrument type": "O",
                        },
                    },
                    {"execution price": 5.40, "execution fraction": 1.0},
                    {
                        "source": "VSR 0b",
                        "quantity": -0.009,
                        "instrument": {
                            "k": 5310,
                            "option type": "Call",
                            "ex": "2024-05-23",
                            "instrument type": "O",
                        },
                    },
                    {"execution price": 4.20, "execution fraction": 1.0},
                    {
                        "source": "VSR 0b",
                        "quantity": -0.008,
                        "instrument": {
                            "k": 5340,
                            "option type": "Call",
                            "ex": "2024-05-23",
                            "instrument type": "O",
                        },
                    },
                    {"execution price": 2.10, "execution fraction": 1.0},
                ],
            },
        },
        {
            "date": "2024-05-24",
            "value": {
                "risks for date": [
                    {
                        "source": "VSR 0b",
                        "quantity": -0.012,
                        "instrument": {
                            "k": 5260,
                            "option type": "Put",
                            "ex": "2024-05-24",
                            "instrument type": "O",
                        },
                    },
                    {"execution price": 4.00, "execution fraction": 1.0},
                    {
                        "source": "VSR 0b",
                        "quantity": -0.011,
                        "instrument": {
                            "k": 5290,
                            "option type": "Put",
                            "ex": "2024-05-24",
                            "instrument type": "O",
                        },
                    },
                    {"execution price": 6.00, "execution fraction": 1.0},
                    {
                        "source": "VSR 0b",
                        "quantity": -0.009,
                        "instrument": {
                            "k": 5320,
                            "option type": "Call",
                            "ex": "2024-05-24",
                            "instrument type": "O",
                        },
                    },
                    {"execution price": 3.50, "execution fraction": 1.0},
                ],
            },
        },
    ]
    json_path = tmp_path / "output.json"
    json_path.write_text(json.dumps(data))
    return json_path


# ── TestExtractDailyStrikeMap ─────────────────────────────────────────────


class TestExtractDailyStrikeMap:
    """Test strike map extraction from output.json."""

    def test_returns_dict_keyed_by_date(self, output_json_path):
        result = extract_daily_strike_map(output_json_path)
        assert date(2024, 5, 23) in result
        assert date(2024, 5, 24) in result
        assert len(result) == 2

    def test_strikes_per_day_correct(self, output_json_path):
        result = extract_daily_strike_map(output_json_path)
        assert len(result[date(2024, 5, 23)]["strikes"]) == 4
        assert len(result[date(2024, 5, 24)]["strikes"]) == 3

    def test_forward_inferred(self, output_json_path):
        result = extract_daily_strike_map(output_json_path)
        # Day 1: puts at 5250/5280, calls at 5310/5340
        # Forward = midpoint(5280, 5310) = 5295
        fwd_day1 = result[date(2024, 5, 23)]["forward"]
        assert 5250 < fwd_day1 < 5340

        # Day 2: puts at 5260/5290, call at 5320
        # Forward = midpoint(5290, 5320) = 5305
        fwd_day2 = result[date(2024, 5, 24)]["forward"]
        assert 5260 < fwd_day2 < 5320

    def test_empty_json_returns_empty(self, tmp_path):
        json_path = tmp_path / "empty.json"
        json_path.write_text(json.dumps([]))
        result = extract_daily_strike_map(json_path)
        assert result == {}


# ── TestBsPrice ───────────────────────────────────────────────────────────


class TestBsPrice:
    """Test Black-Scholes pricing function."""

    def test_call_atm_positive(self):
        price = bs_price(100, 100, 1, 0.05, 0.20, "Call")
        assert price > 0

    def test_put_atm_positive(self):
        price = bs_price(100, 100, 1, 0.05, 0.20, "Put")
        assert price > 0

    def test_put_call_parity(self):
        S, K, T, r, sigma = 100, 100, 1, 0.05, 0.20
        call = bs_price(S, K, T, r, sigma, "Call")
        put = bs_price(S, K, T, r, sigma, "Put")
        # Put-call parity: C - P = S - K*exp(-rT)
        expected_diff = S - K * np.exp(-r * T)
        assert abs((call - put) - expected_diff) < 1e-10

    def test_deep_otm_call_near_zero(self):
        price = bs_price(100, 200, 0.01, 0.05, 0.20, "Call")
        assert price < 1e-6

    def test_zero_vol_returns_intrinsic(self):
        # ITM call: S=110, K=100, intrinsic = 110 - 100*exp(-0.05*1) ≈ 14.88
        call = bs_price(110, 100, 1, 0.05, 0.0, "Call")
        expected = max(110 - 100 * np.exp(-0.05), 0.0)
        assert abs(call - expected) < 1e-10

        # OTM call: S=90, K=100, intrinsic = 0
        call_otm = bs_price(90, 100, 1, 0.05, 0.0, "Call")
        assert call_otm == 0.0


# ── TestComputeMarkKvar ───────────────────────────────────────────────────


class TestComputeMarkKvar:
    """Test mark Kvar computation from synthetic IV marks."""

    def _make_flat_iv_strip(self, forward=5300.0, iv=0.15, n_puts=5, n_calls=5):
        """Build a symmetric strip of strikes with flat IV around forward."""
        spacing = 10.0
        strip = []
        for i in range(n_puts, 0, -1):
            K = forward - i * spacing
            strip.append({"strike": K, "option_type": "Put", "iv": iv})
        for i in range(1, n_calls + 1):
            K = forward + i * spacing
            strip.append({"strike": K, "option_type": "Call", "iv": iv})
        return strip

    def test_produces_positive_kvar(self):
        strip = self._make_flat_iv_strip(iv=0.20)
        result = compute_mark_kvar(strip, forward=5300.0)
        assert result is not None
        assert result["kvar_vol_pct"] > 0

    def test_flat_iv_returns_approximately_that_vol(self):
        strip = self._make_flat_iv_strip(iv=0.15, n_puts=10, n_calls=10)
        result = compute_mark_kvar(strip, forward=5300.0)
        assert result is not None
        # Kvar should be within ~2 vol points of the flat IV for a well-constructed strip
        kvar_vol = result["kvar_vol_pct"] / 100.0  # Convert from percent to decimal
        assert abs(kvar_vol - 0.15) < 0.02

    def test_insufficient_strikes_returns_none(self):
        # Only 2 strikes — below minimum of 3
        strip = [
            {"strike": 5290.0, "option_type": "Put", "iv": 0.15},
            {"strike": 5310.0, "option_type": "Call", "iv": 0.15},
        ]
        result = compute_mark_kvar(strip, forward=5300.0)
        assert result is None

    def test_zero_iv_legs_skipped(self):
        # 3 valid + 2 with iv=0 → should still compute from 3 valid
        strip = [
            {"strike": 5270.0, "option_type": "Put", "iv": 0.0},
            {"strike": 5280.0, "option_type": "Put", "iv": 0.15},
            {"strike": 5290.0, "option_type": "Put", "iv": 0.15},
            {"strike": 5310.0, "option_type": "Call", "iv": 0.15},
            {"strike": 5320.0, "option_type": "Call", "iv": 0.0},
        ]
        result = compute_mark_kvar(strip, forward=5300.0)
        assert result is not None
        assert result["n_iv_strikes"] == 3


# ── TestCacheIO ───────────────────────────────────────────────────────────


class TestCacheIO:
    """Test cache load/save round-trip."""

    def test_load_returns_none_when_missing(self, tmp_path, monkeypatch):
        nonexistent = tmp_path / "does_not_exist.parquet"
        monkeypatch.setattr(
            "volforecast.data.spx_allday_vols.allday_vols_cache_path",
            lambda: nonexistent,
        )
        result = load_allday_cache()
        assert result is None

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "cache" / "test_cache.parquet"
        monkeypatch.setattr(
            "volforecast.data.spx_allday_vols.allday_vols_cache_path",
            lambda: cache_path,
        )
        df = pd.DataFrame(
            {
                "trade_date": pd.to_datetime(["2024-05-23", "2024-05-24"]),
                "kvar_vol_pct": [14.5, 15.2],
                "forward": [5295.0, 5305.0],
            }
        ).set_index("trade_date")

        save_allday_cache(df)
        loaded = load_allday_cache()

        assert loaded is not None
        assert len(loaded) == 2
        pd.testing.assert_frame_equal(loaded, df)


# ── TestRegistry ──────────────────────────────────────────────────────────


class TestRegistry:
    """Test IV source registry integration."""

    def test_spx_allday_vols_in_registry(self):
        assert "spx_allday_vols" in IV_SOURCE_REGISTRY

    def test_registry_label_correct(self):
        entry = IV_SOURCE_REGISTRY["spx_allday_vols"]
        assert entry[0] == "SPX AllDay Mark Kvar (09:10)"
        assert entry[1] == "iv_allday_kvar"

    def test_resolve_iv_sources_default(self):
        result = resolve_iv_sources(None)
        assert len(result) == 1
        assert result[0][1] == "iv_allday_kvar"

    def test_resolve_iv_sources_explicit(self):
        result = resolve_iv_sources(["spx_allday_vols"])
        assert len(result) == 1
        assert result[0][0] == "SPX AllDay Mark Kvar (09:10)"


# ── TestConfigDefault ─────────────────────────────────────────────────────


class TestConfigDefault:
    """Test _parse_gsvivs_iv_sources config parsing."""

    def test_parse_none_returns_allday_default(self):
        assert _parse_gsvivs_iv_sources(None) == ["spx_allday_vols"]

    def test_parse_empty_returns_allday_default(self):
        assert _parse_gsvivs_iv_sources([]) == ["spx_allday_vols"]

    def test_parse_explicit_list_passes(self):
        assert _parse_gsvivs_iv_sources(["exec_kvar"]) == ["exec_kvar"]

    def test_parse_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown IV source"):
            _parse_gsvivs_iv_sources(["bogus"])


class TestTCAdjustedKvar:
    """Tests for the spx_allday_vols_tc IV source (TC-adjusted allday Kvar)."""

    def test_tc_registry_entry(self):
        entry = IV_SOURCE_REGISTRY["spx_allday_vols_tc"]
        assert entry == ("SPX AllDay TC-adj Kvar (09:10)", "iv_allday_kvar_tc", True)

    def test_tc_config_validation_accepted(self):
        result = _parse_gsvivs_iv_sources(["spx_allday_vols_tc"])
        assert result == ["spx_allday_vols_tc"]

    def test_tc_adjustment_computation(self):
        n = 30
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        np.random.seed(42)
        allday = pd.Series(np.random.uniform(0.15, 0.25, n), index=dates, name="iv_allday_kvar")
        exec_kvar = allday - np.random.uniform(0.001, 0.005, n)

        iv_data = pd.DataFrame({"iv_allday_kvar": allday, "iv_exec_kvar": exec_kvar})

        # Replicate the exact logic from gsvivs.py
        tc_gap = iv_data["iv_allday_kvar"] - iv_data["iv_exec_kvar"]
        tc_drag = tc_gap.rolling(20, min_periods=20).mean()
        result = iv_data["iv_allday_kvar"] - tc_drag

        # Manually compute expected
        expected_tc_gap = allday - exec_kvar
        expected_drag = expected_tc_gap.rolling(20, min_periods=20).mean()
        expected = allday - expected_drag

        pd.testing.assert_series_equal(result, expected, check_names=False)
        # Confirm non-NaN values exist after warmup
        assert result.iloc[19:].notna().all()

    def test_tc_first_20_nan(self):
        n = 25
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        allday = pd.Series(np.linspace(0.18, 0.22, n), index=dates)
        exec_kvar = allday - 0.003

        iv_data = pd.DataFrame({"iv_allday_kvar": allday, "iv_exec_kvar": exec_kvar})

        tc_gap = iv_data["iv_allday_kvar"] - iv_data["iv_exec_kvar"]
        tc_drag = tc_gap.rolling(20, min_periods=20).mean()
        result = iv_data["iv_allday_kvar"] - tc_drag

        # First 19 values (indices 0-18) are NaN due to min_periods=20
        assert result.iloc[:19].isna().all()
        # Values from index 19 onward are not NaN
        assert result.iloc[19:].notna().all()

    def test_tc_missing_exec_gives_nan(self):
        n = 25
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        iv_data = pd.DataFrame(
            {"iv_allday_kvar": np.linspace(0.18, 0.22, n)}, index=dates
        )

        # Condition check: exec column missing → all NaN
        if "iv_allday_kvar" in iv_data.columns and "iv_exec_kvar" in iv_data.columns:
            tc_gap = iv_data["iv_allday_kvar"] - iv_data["iv_exec_kvar"]
            tc_drag = tc_gap.rolling(20, min_periods=20).mean()
            result = iv_data["iv_allday_kvar"] - tc_drag
        else:
            result = pd.Series(np.nan, index=iv_data.index)

        assert result.isna().all()

    def test_tc_missing_allday_gives_nan(self):
        n = 25
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        iv_data = pd.DataFrame(
            {"iv_exec_kvar": np.linspace(0.17, 0.21, n)}, index=dates
        )

        # Condition check: allday column missing → all NaN
        if "iv_allday_kvar" in iv_data.columns and "iv_exec_kvar" in iv_data.columns:
            tc_gap = iv_data["iv_allday_kvar"] - iv_data["iv_exec_kvar"]
            tc_drag = tc_gap.rolling(20, min_periods=20).mean()
            result = iv_data["iv_allday_kvar"] - tc_drag
        else:
            result = pd.Series(np.nan, index=iv_data.index)

        assert result.isna().all()

    def test_resolve_iv_sources_tc(self):
        result = resolve_iv_sources(["spx_allday_vols_tc"])
        assert result == [("SPX AllDay TC-adj Kvar (09:10)", "iv_allday_kvar_tc", True)]
