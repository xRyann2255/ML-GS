"""Tests for options_oi module (SPX per-strike OI + Greeks loader).

Tests the Black-Scholes Greeks computation, GEX aggregation,
and feature builder logic. Does NOT require live API access.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest


class TestBSGreeks:
    """Test Black-Scholes Greeks computations."""

    def test_delta_call_atm(self):
        """ATM call delta should be ~0.5."""
        from volforecast.data.options_oi import _bs_delta

        S = np.array([1.0])
        K = np.array([1.0])
        T = np.array([30 / 365.25])  # 30 days
        r = 0.05
        sigma = np.array([0.20])  # 20% vol
        is_call = np.array([True])

        delta = _bs_delta(S, K, T, r, sigma, is_call)
        assert 0.45 < delta[0] < 0.60, f"ATM call delta should be ~0.5, got {delta[0]}"

    def test_delta_put_atm(self):
        """ATM put delta should be ~-0.5."""
        from volforecast.data.options_oi import _bs_delta

        S = np.array([1.0])
        K = np.array([1.0])
        T = np.array([30 / 365.25])
        r = 0.05
        sigma = np.array([0.20])
        is_call = np.array([False])

        delta = _bs_delta(S, K, T, r, sigma, is_call)
        assert -0.60 < delta[0] < -0.40, f"ATM put delta should be ~-0.5, got {delta[0]}"

    def test_gamma_positive(self):
        """Gamma should always be positive."""
        from volforecast.data.options_oi import _bs_gamma

        S = np.array([1.0, 1.0, 1.0])
        K = np.array([0.90, 1.00, 1.10])
        T = np.array([30 / 365.25] * 3)
        r = 0.05
        sigma = np.array([0.20, 0.20, 0.20])

        gamma = _bs_gamma(S, K, T, r, sigma)
        assert all(g >= 0 for g in gamma), f"Gamma must be non-negative: {gamma}"

    def test_gamma_peaks_at_atm(self):
        """Gamma should be highest at ATM."""
        from volforecast.data.options_oi import _bs_gamma

        S = np.array([1.0, 1.0, 1.0])
        K = np.array([0.90, 1.00, 1.10])
        T = np.array([30 / 365.25] * 3)
        r = 0.05
        sigma = np.array([0.20, 0.20, 0.20])

        gamma = _bs_gamma(S, K, T, r, sigma)
        assert gamma[1] > gamma[0], "ATM gamma should exceed OTM put gamma"
        assert gamma[1] > gamma[2], "ATM gamma should exceed OTM call gamma"

    def test_vega_positive(self):
        """Vega should always be positive."""
        from volforecast.data.options_oi import _bs_vega

        S = np.array([1.0])
        K = np.array([1.0])
        T = np.array([30 / 365.25])
        r = 0.05
        sigma = np.array([0.20])

        vega = _bs_vega(S, K, T, r, sigma)
        assert vega[0] > 0, f"Vega must be positive: {vega[0]}"


class TestGEXComputation:
    """Test GEX aggregation logic."""

    @pytest.fixture
    def synthetic_chain(self) -> pd.DataFrame:
        """Create a minimal synthetic option chain for testing."""
        dates = pd.date_range("2024-01-02", periods=5, freq="B")
        rows = []
        for d in dates:
            # 3 puts + 3 calls
            for strike, otype in [
                (0.95, "P"), (0.97, "P"), (0.99, "P"),
                (1.01, "C"), (1.03, "C"), (1.05, "C"),
            ]:
                rows.append({
                    "date": d,
                    "relativeStrike": strike,
                    "expirationDate": d + pd.Timedelta(days=7),
                    "impliedVolatility": 0.18,
                    "delta": 0.5 if otype == "C" else -0.5,
                    "gamma": 0.05 - abs(strike - 1.0) * 0.3,  # Peak at ATM
                    "vega": 0.01,
                    "theta": -0.005,
                    "option_type": otype,
                    "oi": 1000.0,
                    "T": 7 / 365.25,
                })
        return pd.DataFrame(rows)

    def test_gex_net_sign(self, synthetic_chain):
        """Net GEX should be deterministic given known OI distribution."""
        from volforecast.data.options_oi import compute_gex

        gex = compute_gex(synthetic_chain)
        assert not gex.empty
        assert "gex_net" in gex.columns
        assert "gex_sign" in gex.columns
        assert len(gex) == 5  # 5 trading days

    def test_gex_without_oi(self, synthetic_chain):
        """GEX should still compute with NaN OI (uniform assumption)."""
        from volforecast.data.options_oi import compute_gex

        chain_no_oi = synthetic_chain.copy()
        chain_no_oi["oi"] = np.nan

        gex = compute_gex(chain_no_oi)
        assert not gex.empty
        assert gex["gex_net"].notna().all()

    def test_gex_calls_negative_puts_positive(self, synthetic_chain):
        """Calls should contribute negative GEX, puts positive."""
        from volforecast.data.options_oi import compute_gex

        # All calls → net negative GEX
        calls_only = synthetic_chain[synthetic_chain["option_type"] == "C"].copy()
        gex_calls = compute_gex(calls_only)
        assert (gex_calls["gex_net"] <= 0).all(), "All-call chain should give negative GEX"

        # All puts → net positive GEX
        puts_only = synthetic_chain[synthetic_chain["option_type"] == "P"].copy()
        gex_puts = compute_gex(puts_only)
        assert (gex_puts["gex_net"] >= 0).all(), "All-put chain should give positive GEX"


class TestGEXFeatures:
    """Test feature builder from GEX daily series."""

    @pytest.fixture
    def gex_daily(self) -> pd.DataFrame:
        """Create realistic GEX daily data."""
        dates = pd.bdate_range("2023-01-02", periods=300)
        np.random.seed(42)
        gex_net = np.cumsum(np.random.randn(300)) * 1e6
        return pd.DataFrame({
            "gex_net": gex_net,
            "gex_call": -abs(gex_net) * 0.6,
            "gex_put": abs(gex_net) * 0.4,
            "gex_sign": np.sign(gex_net),
            "gex_zscore": (gex_net - pd.Series(gex_net).rolling(63).mean())
                          / pd.Series(gex_net).rolling(63).std(),
        }, index=dates)

    def test_feature_columns(self, gex_daily):
        """Feature builder should produce expected columns."""
        from volforecast.data.options_oi import build_gex_features

        features = build_gex_features(gex_daily)
        expected = {"gex_sign_d", "gex_zscore_d", "gex_quintile_d",
                    "gex_regime_d", "gex_momentum_d"}
        assert expected.issubset(features.columns)

    def test_feature_sign_values(self, gex_daily):
        """GEX sign should be in {-1, 0, 1}."""
        from volforecast.data.options_oi import build_gex_features

        features = build_gex_features(gex_daily)
        valid_signs = {-1.0, 0.0, 1.0}
        actual_signs = set(features["gex_sign_d"].dropna().unique())
        assert actual_signs.issubset(valid_signs)

    def test_feature_regime_binary(self, gex_daily):
        """GEX regime should be binary {0, 1}."""
        from volforecast.data.options_oi import build_gex_features

        features = build_gex_features(gex_daily)
        valid_regimes = {0.0, 1.0}
        actual_regimes = set(features["gex_regime_d"].dropna().unique())
        assert actual_regimes.issubset(valid_regimes)

    def test_empty_input(self):
        """Empty input should return empty DataFrame."""
        from volforecast.data.options_oi import build_gex_features

        features = build_gex_features(pd.DataFrame())
        assert features.empty
