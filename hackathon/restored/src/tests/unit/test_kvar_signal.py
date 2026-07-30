"""Tests for execution Kvar-based GSVIVS signal.

Tests load_kvar_cache(), variance-space gap signal, and the integration
with _compute_gsvivs_stats when iv_source='execution_kvar'.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def kvar_parquet(tmp_path):
    """Create a minimal Kvar parquet for testing."""
    dates = pd.bdate_range("2023-01-02", periods=100, freq="B")
    rng = np.random.default_rng(42)
    kvar = 12.0 + rng.standard_normal(100) * 3.0  # ~12% vol mean
    kvar = np.clip(kvar, 3.0, 40.0)

    df = pd.DataFrame(
        {
            "kvar_1dte": kvar,
            "atm_vol_1dte": kvar * 0.98,
            "kvar_0dte": np.nan,  # all NaN so load_kvar_cache falls back to 1dte
            "atm_vol_0dte": np.nan,
            "forward": 4200.0 + rng.standard_normal(100) * 50.0,
            "index_value": 100.0 + np.cumsum(rng.standard_normal(100) * 0.1),
            "daily_return_bps": rng.standard_normal(100) * 20.0,
        },
        index=dates,
    )
    df.index.name = "date"
    path = tmp_path / "gsvivs_kvar_daily.parquet"
    df.to_parquet(path)
    return path


class TestLoadKvarCache:
    """Test load_kvar_cache function."""

    def test_loads_parquet_returns_series(self, kvar_parquet, monkeypatch):
        """load_kvar_cache returns a Series indexed by date with kvar_1dte values."""
        from volforecast.data.edrvol import load_kvar_cache

        monkeypatch.setattr(
            "volforecast.data.edrvol.processed_dir",
            lambda: kvar_parquet.parent,
        )
        result = load_kvar_cache()
        assert result is not None
        assert isinstance(result, pd.Series)
        assert result.name == "kvar_1dte"
        assert len(result) == 100
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_returns_none_when_missing(self, tmp_path, monkeypatch):
        """load_kvar_cache returns None when parquet doesn't exist."""
        from volforecast.data.edrvol import load_kvar_cache

        monkeypatch.setattr(
            "volforecast.data.edrvol.processed_dir",
            lambda: tmp_path,
        )
        result = load_kvar_cache()
        assert result is None

    def test_values_in_vol_points(self, kvar_parquet, monkeypatch):
        """Kvar values are in vol points (e.g., 15.0 = 15% annualized)."""
        from volforecast.data.edrvol import load_kvar_cache

        monkeypatch.setattr(
            "volforecast.data.edrvol.processed_dir",
            lambda: kvar_parquet.parent,
        )
        result = load_kvar_cache()
        # Should be in vol points, not decimals
        assert result.mean() > 1.0  # not 0.12 decimal
        assert result.mean() < 100.0  # not 1200 bps


class TestKvarSignalFormulations:
    """Test vol-space and variance-space gap signal formulations."""

    def test_vol_space_gap(self):
        """Vol-space gap: kvar_252 - rv_forecast where kvar_252 = kvar/100 * sqrt(252/365)."""
        from volforecast.evaluation.economic_value import kvar_rv_gap_signal

        # kvar in 365-calendar vol pts, rv_forecast in 252-trading decimal
        # After conversion: kvar_252 = kvar/100 * sqrt(252/365) ≈ kvar/100 * 0.831
        # [15*0.00831=0.1246, 12*0.00831=0.0997, 20*0.00831=0.1662, 10*0.00831=0.0831]
        kvar = np.array([15.0, 12.0, 20.0, 10.0])
        rv_forecast = np.array([0.10, 0.15, 0.10, 0.14])  # annualized decimal (252)

        signal = kvar_rv_gap_signal(kvar, rv_forecast, space="vol", threshold=0.0)
        # gap = [0.1246-0.10=+0.025, 0.0997-0.15=-0.050, 0.1662-0.10=+0.066, 0.0831-0.14=-0.057]
        # signal: [+1, -1, +1, -1]
        expected = np.array([1.0, -1.0, 1.0, -1.0])
        np.testing.assert_array_equal(signal, expected)

    def test_variance_space_gap(self):
        """Variance-space gap: kvar_252^2 - rv_forecast^2."""
        from volforecast.evaluation.economic_value import kvar_rv_gap_signal

        kvar = np.array([15.0, 12.0, 20.0, 10.0])
        rv_forecast = np.array([0.10, 0.15, 0.10, 0.14])

        signal = kvar_rv_gap_signal(kvar, rv_forecast, space="variance", threshold=0.0)
        # kvar_252 = [0.1246, 0.0997, 0.1662, 0.0831]
        # kvar_252^2 = [0.01553, 0.00994, 0.02762, 0.00691]
        # rv^2 = [0.01, 0.0225, 0.01, 0.0196]
        # gap = [+0.0055, -0.0126, +0.0176, -0.0127]
        # signal: [+1, -1, +1, -1]
        expected = np.array([1.0, -1.0, 1.0, -1.0])
        np.testing.assert_array_equal(signal, expected)

    def test_threshold_creates_dead_zone(self):
        """Threshold prevents short signals when gap is small."""
        from volforecast.evaluation.economic_value import kvar_rv_gap_signal

        # After 365->252 conversion: kvar_252 = kvar/100 * 0.831
        # [15*0.00831=0.1246, 12*0.00831=0.0997, 20*0.00831=0.1662, 13*0.00831=0.1080]
        kvar = np.array([15.0, 12.0, 20.0, 13.0])
        rv_forecast = np.array([0.130, 0.105, 0.10, 0.115])

        # gap = [0.1246-0.130=-0.005, 0.0997-0.105=-0.005, 0.1662-0.10=+0.066, 0.1080-0.115=-0.007]
        # With threshold=0.01: only go short if gap < -0.01
        # None of the negative gaps exceed -0.01
        signal = kvar_rv_gap_signal(kvar, rv_forecast, space="vol", threshold=0.01)
        expected = np.array([1.0, 1.0, 1.0, 1.0])
        np.testing.assert_array_equal(signal, expected)

    def test_nan_handling_defaults_long(self):
        """NaN in kvar defaults to long signal."""
        from volforecast.evaluation.economic_value import kvar_rv_gap_signal

        kvar = np.array([15.0, np.nan, 20.0, np.nan])
        rv_forecast = np.array([0.12, 0.15, 0.25, 0.14])

        signal = kvar_rv_gap_signal(kvar, rv_forecast, space="vol", threshold=0.0)
        # NaN kvar => default long (+1)
        assert signal[1] == 1.0
        assert signal[3] == 1.0


class TestKvar0dtePreference:
    """Test that load_kvar_cache prefers kvar_0dte when available."""

    def test_prefers_0dte_when_populated(self, tmp_path, monkeypatch):
        """load_kvar_cache returns kvar_0dte Series when it has non-NaN values."""
        from volforecast.data.edrvol import load_kvar_cache

        dates = pd.bdate_range("2023-01-02", periods=10, freq="B")
        df = pd.DataFrame(
            {
                "kvar_0dte": [25.0] * 10,
                "kvar_1dte": [15.0] * 10,
            },
            index=dates,
        )
        df.index.name = "date"
        path = tmp_path / "gsvivs_kvar_daily.parquet"
        df.to_parquet(path)

        monkeypatch.setattr("volforecast.data.edrvol.processed_dir", lambda: tmp_path)
        result = load_kvar_cache()
        assert result.name == "kvar_0dte"
        assert result.mean() == 25.0

    def test_falls_back_to_1dte_when_0dte_all_nan(self, tmp_path, monkeypatch):
        """load_kvar_cache falls back to kvar_1dte when kvar_0dte is all NaN."""
        from volforecast.data.edrvol import load_kvar_cache

        dates = pd.bdate_range("2023-01-02", periods=10, freq="B")
        df = pd.DataFrame(
            {
                "kvar_0dte": [np.nan] * 10,
                "kvar_1dte": [15.0] * 10,
            },
            index=dates,
        )
        df.index.name = "date"
        path = tmp_path / "gsvivs_kvar_daily.parquet"
        df.to_parquet(path)

        monkeypatch.setattr("volforecast.data.edrvol.processed_dir", lambda: tmp_path)
        result = load_kvar_cache()
        assert result.name == "kvar_1dte"
        assert result.mean() == 15.0

    def test_no_overnight_param_in_signal(self):
        """kvar_rv_gap_signal has no overnight_var parameter (removed)."""
        import inspect

        from volforecast.evaluation.economic_value import kvar_rv_gap_signal

        sig = inspect.signature(kvar_rv_gap_signal)
        assert "overnight_var" not in sig.parameters


class TestKvarRvSizedSignal:
    """Tests for the sized variant of the GSVIVS01 signal.

    Sizing analysis (workspace/tmp/sizing_*.csv, 2026-06-15) on champion
    LightGBM predictions found three viable modes:
      - "binary"    : status quo {-1, +1}
      - "asym_long" : long side scales by z-score in [+1, +max_leverage],
                      short side fixed at -1. Default winner (+30-41 bps Sharpe).
      - "zscore"    : symmetric clipped z-score (drawdown-averse).
    """

    def test_binary_mode_matches_kvar_rv_gap_signal(self):
        """sizing_mode='binary' must reproduce kvar_rv_gap_signal exactly."""
        from volforecast.evaluation.economic_value import (
            kvar_rv_gap_signal,
            kvar_rv_sized_signal,
        )

        rng = np.random.default_rng(0)
        kvar = rng.uniform(10.0, 30.0, 200)
        rv = rng.uniform(0.08, 0.25, 200)

        binary = kvar_rv_gap_signal(kvar, rv, space="vol", threshold=0.0)
        sized = kvar_rv_sized_signal(kvar, rv, sizing_mode="binary", space="vol", threshold=0.0)
        np.testing.assert_array_equal(binary, sized)

    def test_asym_long_caps_short_at_minus_one(self):
        """asym_long: short side is always exactly -1, long side scales up."""
        from volforecast.evaluation.economic_value import kvar_rv_sized_signal

        rng = np.random.default_rng(1)
        kvar = rng.uniform(5.0, 35.0, 300)
        rv = rng.uniform(0.05, 0.30, 300)

        sized = kvar_rv_sized_signal(
            kvar, rv, sizing_mode="asym_long", space="vol",
            max_leverage=2.0, lookback=63,
        )
        # All short positions must be exactly -1 (not -0.5 or -2)
        shorts = sized[sized < 0]
        assert len(shorts) > 0, "asym_long should still produce some short positions"
        np.testing.assert_allclose(shorts, -1.0)

    def test_asym_long_long_side_in_one_to_max_leverage(self):
        """asym_long: every long position lies in [+1, +max_leverage]."""
        from volforecast.evaluation.economic_value import kvar_rv_sized_signal

        rng = np.random.default_rng(2)
        kvar = rng.uniform(5.0, 35.0, 300)
        rv = rng.uniform(0.05, 0.30, 300)
        L = 2.0

        sized = kvar_rv_sized_signal(
            kvar, rv, sizing_mode="asym_long", space="vol",
            max_leverage=L, lookback=63,
        )
        longs = sized[sized > 0]
        assert len(longs) > 0
        assert longs.min() >= 1.0 - 1e-9
        assert longs.max() <= L + 1e-9

    def test_asym_long_size_increases_with_conviction(self):
        """asym_long: larger gap → larger long size (monotone in gap)."""
        from volforecast.evaluation.economic_value import kvar_rv_sized_signal

        # Construct kvar so that gap is strictly increasing
        # kvar_252 = kvar/100 * sqrt(252/365); rv held constant
        rv = np.full(150, 0.10)
        # First 100 days warm up the lookback; then ramp gap
        kvar_warm = np.full(100, 13.0)
        kvar_ramp = np.linspace(13.0, 30.0, 50)
        kvar = np.concatenate([kvar_warm, kvar_ramp])

        sized = kvar_rv_sized_signal(
            kvar, rv, sizing_mode="asym_long", space="vol",
            max_leverage=3.0, lookback=63,
        )
        # In the ramp region, size should be non-decreasing
        ramp_sizes = sized[100:]
        diffs = np.diff(ramp_sizes)
        # Allow ties but not decreases
        assert np.all(diffs >= -1e-9), f"asym_long not monotone in gap: diffs={diffs}"

    def test_zscore_symmetric_clip(self):
        """zscore: outputs clipped to [-max_leverage, +max_leverage], symmetric."""
        from volforecast.evaluation.economic_value import kvar_rv_sized_signal

        rng = np.random.default_rng(3)
        # Use a wide kvar range to push z-score past clip
        kvar = rng.uniform(5.0, 40.0, 400)
        rv = rng.uniform(0.05, 0.30, 400)
        L = 1.0

        sized = kvar_rv_sized_signal(
            kvar, rv, sizing_mode="zscore", space="vol",
            max_leverage=L, lookback=63,
        )
        assert sized.min() >= -L - 1e-9
        assert sized.max() <= L + 1e-9
        # Symmetry sanity: both signs present
        assert (sized > 0).sum() > 0
        assert (sized < 0).sum() > 0

    def test_nan_kvar_handling(self):
        """NaN kvar → asym_long defaults long (+1); zscore returns 0; binary +1;
        long_flat defaults long (+1) — inherits binary's default-long contract."""
        from volforecast.evaluation.economic_value import kvar_rv_sized_signal

        # Need warmup non-NaN data so lookback std is well-defined
        kvar = np.concatenate([np.full(80, 15.0), np.array([np.nan])])
        rv = np.concatenate([np.full(80, 0.10), np.array([0.10])])

        s_bin = kvar_rv_sized_signal(kvar, rv, sizing_mode="binary")
        s_asym = kvar_rv_sized_signal(kvar, rv, sizing_mode="asym_long",
                                        max_leverage=2.0, lookback=63)
        s_z = kvar_rv_sized_signal(kvar, rv, sizing_mode="zscore",
                                     max_leverage=1.0, lookback=63)
        s_lf = kvar_rv_sized_signal(kvar, rv, sizing_mode="long_flat")

        assert s_bin[-1] == 1.0
        assert s_asym[-1] == 1.0
        assert s_z[-1] == 0.0
        assert s_lf[-1] == 1.0

    def test_long_flat_replaces_shorts_with_zero(self):
        """long_flat: positions are exactly {0, +1}. Anywhere binary would
        emit -1 (sell vol), long_flat instead stays flat (0) — same long-side
        entries, no short exposure."""
        from volforecast.evaluation.economic_value import (
            kvar_rv_gap_signal,
            kvar_rv_sized_signal,
        )

        rng = np.random.default_rng(7)
        kvar = rng.uniform(5.0, 35.0, 400)
        rv = rng.uniform(0.05, 0.30, 400)

        binary = kvar_rv_gap_signal(kvar, rv, space="vol", threshold=0.0)
        lf = kvar_rv_sized_signal(kvar, rv, sizing_mode="long_flat", space="vol", threshold=0.0)

        # Output is strictly in {0, +1}.
        unique_vals = np.unique(lf)
        assert set(unique_vals.tolist()).issubset({0.0, 1.0}), (
            f"long_flat must emit only {{0, +1}}, got {unique_vals.tolist()}"
        )
        # Long days match binary's long days.
        long_mask = binary > 0
        np.testing.assert_array_equal(lf[long_mask], np.ones(long_mask.sum()))
        # Short days collapse to flat.
        short_mask = binary < 0
        assert short_mask.sum() > 0, "test setup should yield some shorts"
        np.testing.assert_array_equal(lf[short_mask], np.zeros(short_mask.sum()))

    def test_long_flat_threshold_honored(self):
        """long_flat respects the same threshold/space semantics as binary —
        only the short-side outcome is rewritten."""
        from volforecast.evaluation.economic_value import (
            kvar_rv_gap_signal,
            kvar_rv_sized_signal,
        )

        rng = np.random.default_rng(11)
        kvar = rng.uniform(5.0, 35.0, 200)
        rv = rng.uniform(0.05, 0.30, 200)

        for space, threshold in (("vol", 0.0), ("vol", 0.01), ("variance", 0.0)):
            binary = kvar_rv_gap_signal(kvar, rv, space=space, threshold=threshold)
            lf = kvar_rv_sized_signal(
                kvar, rv, sizing_mode="long_flat", space=space, threshold=threshold
            )
            expected = np.where(binary > 0, 1.0, 0.0)
            np.testing.assert_array_equal(lf, expected)

    def test_unknown_sizing_mode_raises(self):
        """Invalid sizing_mode raises ValueError."""
        from volforecast.evaluation.economic_value import kvar_rv_sized_signal

        kvar = np.array([15.0, 12.0])
        rv = np.array([0.10, 0.15])
        with pytest.raises(ValueError, match="sizing_mode"):
            kvar_rv_sized_signal(kvar, rv, sizing_mode="not_a_mode")

    def test_variance_space_works_in_sized(self):
        """Variance-space gap is honored in sized variants."""
        from volforecast.evaluation.economic_value import kvar_rv_sized_signal

        # Make signal strongly negative in vol space but small in variance
        kvar = np.full(100, 12.0)
        rv = np.full(100, 0.13)
        s_vol = kvar_rv_sized_signal(kvar, rv, sizing_mode="binary", space="vol")
        s_var = kvar_rv_sized_signal(kvar, rv, sizing_mode="binary", space="variance")
        # Both should be deterministic given constant inputs
        assert np.all(s_vol == s_vol[0])
        assert np.all(s_var == s_var[0])

    def test_default_sizing_mode_is_asym_long(self):
        """Default sizing_mode must be 'asym_long' (winner from 2026-06-15 analysis).

        Regression guard: if someone flips the default to binary, this test breaks
        and forces a deliberate update with rationale.
        """
        import inspect

        from volforecast.evaluation.economic_value import kvar_rv_sized_signal

        sig = inspect.signature(kvar_rv_sized_signal)
        assert sig.parameters["sizing_mode"].default == "asym_long"


class TestGsvivsSizingSpec:
    """Dataclass + default 3-mode list that drives the dashboard toggle."""

    def test_spec_exposes_mode_lev_lookback_label(self):
        from volforecast.evaluation.economic_value import GsvivsSizingSpec

        spec = GsvivsSizingSpec(mode="asym_long", max_leverage=2.0, lookback=63)
        assert spec.mode == "asym_long"
        assert spec.max_leverage == 2.0
        assert spec.lookback == 63
        # Label is used as the row-name suffix in the GSVIVS dashboard table.
        # Must be deterministic and human-readable.
        assert "asym_long" in spec.label
        assert "2" in spec.label  # leverage shows up
        assert spec.label.startswith("[") and spec.label.endswith("]")

    def test_binary_spec_label_omits_leverage(self):
        """Binary mode has no leverage knob — the label shouldn't fake one."""
        from volforecast.evaluation.economic_value import GsvivsSizingSpec

        spec = GsvivsSizingSpec(mode="binary")
        assert spec.label == "[binary]"

    def test_long_flat_spec_label_omits_leverage(self):
        """long_flat has no leverage knob either — label is just '[long_flat]'."""
        from volforecast.evaluation.economic_value import GsvivsSizingSpec

        spec = GsvivsSizingSpec(mode="long_flat")
        assert spec.label == "[long_flat]"

    def test_spec_validates_mode(self):
        from volforecast.evaluation.economic_value import GsvivsSizingSpec

        with pytest.raises(ValueError, match="sizing_mode|mode"):
            GsvivsSizingSpec(mode="bogus_sizer", max_leverage=2.0, lookback=63)

    def test_default_specs_match_dashboard_toggle(self):
        """The default list IS the dashboard toggle
        (binary | asym_long | zscore | long_flat).

        Values: asym_long L=2.0 (analysis-recommended), zscore L=1.0 (drawdown-
        averse), long_flat (long-side-only variant of binary: replaces all
        shorts with flat). Lookback 63 (one quarter, balances responsiveness
        vs stability).
        """
        from volforecast.evaluation.economic_value import (
            DEFAULT_GSVIVS_SIZING_SPECS,
            GsvivsSizingSpec,
        )

        assert isinstance(DEFAULT_GSVIVS_SIZING_SPECS, tuple)
        assert len(DEFAULT_GSVIVS_SIZING_SPECS) == 4
        modes = [s.mode for s in DEFAULT_GSVIVS_SIZING_SPECS]
        assert modes == ["binary", "asym_long", "zscore", "long_flat"]

        # Each entry is a frozen spec — immutable to avoid accidental mutation
        # of the shared default constant.
        binary, asym, zscore, long_flat = DEFAULT_GSVIVS_SIZING_SPECS
        assert isinstance(binary, GsvivsSizingSpec)
        assert asym.max_leverage == 2.0
        assert asym.lookback == 63
        assert zscore.max_leverage == 1.0
        assert zscore.lookback == 63
        assert long_flat.mode == "long_flat"

    def test_spec_to_dict_and_from_dict_roundtrip(self):
        """YAML parsing path: dict → spec, spec → dict, both stable."""
        from volforecast.evaluation.economic_value import GsvivsSizingSpec

        raw = {"mode": "asym_long", "max_leverage": 3.0, "lookback": 42}
        spec = GsvivsSizingSpec.from_dict(raw)
        assert spec.mode == "asym_long"
        assert spec.max_leverage == 3.0
        assert spec.lookback == 42
        # Round-trip preserves all knobs.
        assert spec.to_dict() == raw

    def test_from_dict_accepts_minimal_binary(self):
        """Binary mode YAML can omit leverage/lookback (they're ignored)."""
        from volforecast.evaluation.economic_value import GsvivsSizingSpec

        spec = GsvivsSizingSpec.from_dict({"mode": "binary"})
        assert spec.mode == "binary"
        assert spec.label == "[binary]"

    def test_from_dict_accepts_string_shorthand(self):
        """YAML shorthand: just the mode name uses sensible defaults."""
        from volforecast.evaluation.economic_value import GsvivsSizingSpec

        spec = GsvivsSizingSpec.from_dict("asym_long")
        assert spec.mode == "asym_long"
        assert spec.max_leverage == 2.0  # default
        assert spec.lookback == 63
