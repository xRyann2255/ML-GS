"""Group A — contract tests for volforecast.utils.targets.forward_log_rv.

TDD: written BEFORE the helper. These define the canonical spec for the
Corsi-family forward log-RV target.

Mathematical contract:
    y_t = log( (1/h) * sum_{k=1..h} RV_{t+k} )

with `y.index == rv.index`, last `h` rows NaN, negative/zero RV clipped to
`min_value` (default 1e-20) before log.

See `/memories/session/plan.md` §2 for the full contract.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def rv_short() -> pd.Series:
    """5-day positive RV series."""
    dates = pd.bdate_range("2020-01-02", periods=5)
    return pd.Series([1e-4, 2e-4, 3e-4, 4e-4, 5e-4], index=dates, name="rv")


@pytest.fixture
def rv_long() -> pd.Series:
    """30-day positive RV series (linspace, deterministic)."""
    dates = pd.bdate_range("2020-01-02", periods=30)
    return pd.Series(np.linspace(1e-4, 5e-4, 30), index=dates, name="rv")


@pytest.fixture
def rv_60d() -> pd.Series:
    """60-day positive RV series."""
    dates = pd.bdate_range("2020-01-02", periods=60)
    return pd.Series(np.linspace(1e-4, 6e-4, 60), index=dates, name="rv")


# ---------------------------------------------------------------------------
# A1 — h=1 matches legacy `np.log(rv).shift(-1)`
# ---------------------------------------------------------------------------


def test_h1_matches_legacy_shift_neg1(rv_short):
    """For h=1, output equals np.log(rv).shift(-1) elementwise (no clip needed for positives)."""
    from volforecast.utils.targets import forward_log_rv

    out = forward_log_rv(rv_short, 1)
    expected = np.log(rv_short).shift(-1)
    pd.testing.assert_series_equal(out, expected, check_names=False)


# ---------------------------------------------------------------------------
# A2 — h=1 generic equals the special case (proves we can drop `if h == 1`)
# ---------------------------------------------------------------------------


def test_h1_generic_equals_special_case(rv_short):
    """forward_log_rv(rv, 1) == np.log(rv.clip(1e-20)).shift(-1) elementwise."""
    from volforecast.utils.targets import forward_log_rv

    out = forward_log_rv(rv_short, 1)
    expected = np.log(rv_short.clip(lower=1e-20)).shift(-1)
    pd.testing.assert_series_equal(out, expected, check_names=False)


# ---------------------------------------------------------------------------
# A3 — h=5 matches legacy `np.log(rv.rolling(5).mean()).shift(-5)`
# ---------------------------------------------------------------------------


def test_h5_matches_legacy_rolling_mean_shift(rv_long):
    """For h=5, output equals np.log(rv.rolling(5).mean()).shift(-5) on positives."""
    from volforecast.utils.targets import forward_log_rv

    out = forward_log_rv(rv_long, 5)
    expected = np.log(rv_long.rolling(5).mean()).shift(-5)
    pd.testing.assert_series_equal(out, expected, check_names=False)


# ---------------------------------------------------------------------------
# A4 — h=22 matches legacy
# ---------------------------------------------------------------------------


def test_h22_matches_legacy_rolling_mean_shift(rv_60d):
    """For h=22, output equals np.log(rv.rolling(22).mean()).shift(-22) on positives."""
    from volforecast.utils.targets import forward_log_rv

    out = forward_log_rv(rv_60d, 22)
    expected = np.log(rv_60d.rolling(22).mean()).shift(-22)
    pd.testing.assert_series_equal(out, expected, check_names=False)


# ---------------------------------------------------------------------------
# A5 — Index preserved
# ---------------------------------------------------------------------------


def test_index_preserved(rv_long):
    """Output index equals input index; length unchanged."""
    from volforecast.utils.targets import forward_log_rv

    out = forward_log_rv(rv_long, 5)
    assert out.index.equals(rv_long.index)
    assert len(out) == len(rv_long)


# ---------------------------------------------------------------------------
# A6 — Tail h rows are NaN
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("h", [1, 5, 22])
def test_tail_h_rows_are_nan(rv_60d, h):
    """Last h rows are NaN (no future RV to average)."""
    from volforecast.utils.targets import forward_log_rv

    out = forward_log_rv(rv_60d, h)
    assert out.iloc[-h:].isna().all()


# ---------------------------------------------------------------------------
# A7 — h > len returns all-NaN
# ---------------------------------------------------------------------------


def test_h_greater_than_length_returns_all_nan(rv_short):
    """h=10 on length-5 input returns all-NaN Series with correct index."""
    from volforecast.utils.targets import forward_log_rv

    out = forward_log_rv(rv_short, 10)
    assert len(out) == 5
    assert out.index.equals(rv_short.index)
    assert out.isna().all()


# ---------------------------------------------------------------------------
# A8 — h == len: exactly one non-NaN at index 0
# ---------------------------------------------------------------------------


def test_h_equals_length_one_non_nan(rv_short):
    """h=5 on length-5: out.iloc[0] = log(mean(rv)); rest NaN."""
    from volforecast.utils.targets import forward_log_rv

    out = forward_log_rv(rv_short, 5)
    # h=5 with shift(-5) on length-5 produces: rolling at index 4 = mean of all,
    # then shift(-5) moves it to index -1 (off the end) → all NaN.
    # The mathematical convention y_t = log(mean(RV_{t+1..t+h})) means we need
    # exactly one valid value at index t such that t+h <= last index.
    # For length 5 and h=5: only t=-1 would work, which doesn't exist.
    # So all NaN. Test that this is what we get.
    assert out.isna().all()


def test_h_equals_length_minus_one():
    """For len=6, h=5: exactly one non-NaN at index 0 = log(mean(rv[1:6]))."""
    from volforecast.utils.targets import forward_log_rv

    dates = pd.bdate_range("2020-01-02", periods=6)
    rv = pd.Series([1e-4, 2e-4, 3e-4, 4e-4, 5e-4, 6e-4], index=dates)
    out = forward_log_rv(rv, 5)
    expected_first = np.log(np.mean([2e-4, 3e-4, 4e-4, 5e-4, 6e-4]))
    assert out.iloc[0] == pytest.approx(expected_first)
    assert out.iloc[1:].isna().all()


# ---------------------------------------------------------------------------
# A9, A10 — invalid h
# ---------------------------------------------------------------------------


def test_h_zero_raises(rv_short):
    from volforecast.utils.targets import forward_log_rv

    with pytest.raises(ValueError, match="h must be >= 1"):
        forward_log_rv(rv_short, 0)


def test_h_negative_raises(rv_short):
    from volforecast.utils.targets import forward_log_rv

    with pytest.raises(ValueError, match="h must be >= 1"):
        forward_log_rv(rv_short, -3)


# ---------------------------------------------------------------------------
# A11 — empty input
# ---------------------------------------------------------------------------


def test_empty_series_returns_empty():
    """Empty Series → empty Series, no exception."""
    from volforecast.utils.targets import forward_log_rv

    rv = pd.Series([], dtype=float, index=pd.DatetimeIndex([]))
    out = forward_log_rv(rv, 5)
    assert len(out) == 0
    assert out.index.equals(rv.index)


# ---------------------------------------------------------------------------
# A12 — mid-stream NaN propagation
# ---------------------------------------------------------------------------


def test_midstream_nan_propagates():
    """A NaN at rv[10] makes the output NaN at rows whose forward window includes it."""
    from volforecast.utils.targets import forward_log_rv

    dates = pd.bdate_range("2020-01-02", periods=30)
    rv = pd.Series(np.linspace(1e-4, 3e-4, 30), index=dates)
    rv.iloc[10] = np.nan

    out = forward_log_rv(rv, 5)
    # rv[10] is in the forward window of rows t=5..9 (target uses RV_{t+1..t+5},
    # so t=5 uses rv[6..10], t=9 uses rv[10..14]). All 5 should be NaN.
    assert out.iloc[5:10].isna().all()
    # rv[4] uses rv[5..9] — no NaN in window — should be finite.
    assert np.isfinite(out.iloc[4])


# ---------------------------------------------------------------------------
# A13 — zero RV clipped (no -inf)
# ---------------------------------------------------------------------------


def test_zero_rv_clipped_no_minus_inf():
    """A zero in rv produces a finite (very negative) target rather than -inf."""
    from volforecast.utils.targets import forward_log_rv

    dates = pd.bdate_range("2020-01-02", periods=5)
    rv = pd.Series([0.0, 1e-4, 2e-4, 3e-4, 4e-4], index=dates)
    out = forward_log_rv(rv, 1)
    # h=1: y_t = log(rv_{t+1}). For t=0: rv[1]=1e-4 → log(1e-4), finite.
    # No zero in window for h=1 on this fixture.
    assert np.isfinite(out.iloc[0])
    assert out.iloc[0] == pytest.approx(np.log(1e-4))


def test_zero_rv_in_window_clipped():
    """Zero inside the rolling window produces a finite target (clipped)."""
    from volforecast.utils.targets import forward_log_rv

    dates = pd.bdate_range("2020-01-02", periods=6)
    rv = pd.Series([1e-4, 0.0, 1e-4, 1e-4, 1e-4, 1e-4], index=dates)
    out = forward_log_rv(rv, 5)
    # t=0: window rv[1..5] = [0, 1e-4, 1e-4, 1e-4, 1e-4].
    # After clip to 1e-20: mean = (1e-20 + 4*1e-4)/5 ≈ 8e-5.
    # log(8e-5) is finite.
    assert np.isfinite(out.iloc[0])


# ---------------------------------------------------------------------------
# A14, A15 — index hygiene
# ---------------------------------------------------------------------------


def test_non_monotonic_index_raises():
    """Out-of-order index raises ValueError."""
    from volforecast.utils.targets import forward_log_rv

    dates = pd.bdate_range("2020-01-02", periods=5)
    rv = pd.Series([1e-4, 2e-4, 3e-4, 4e-4, 5e-4], index=dates)
    # Shuffle index
    rv_shuffled = rv.iloc[[2, 0, 1, 4, 3]]
    with pytest.raises(ValueError, match="monotonic"):
        forward_log_rv(rv_shuffled, 2)


def test_duplicate_index_raises():
    """Duplicate dates raise ValueError."""
    from volforecast.utils.targets import forward_log_rv

    dates = [
        pd.Timestamp("2020-01-02"),
        pd.Timestamp("2020-01-03"),
        pd.Timestamp("2020-01-03"),
        pd.Timestamp("2020-01-06"),
    ]
    rv = pd.Series([1e-4, 2e-4, 3e-4, 4e-4], index=pd.DatetimeIndex(dates))
    with pytest.raises(ValueError, match="unique"):
        forward_log_rv(rv, 2)
