"""Group B — characterization tests locking the equivalence between each
existing inline log-RV target construction and the new
``volforecast.utils.targets.forward_log_rv`` helper.

These tests must pass BOTH before migration (legacy inline expression == helper)
AND after migration (call-site now uses helper, but the recomputed legacy
expression still equals the helper). They are the regression guard for the
consolidation refactor.

Sites covered:

* Site 1: ``Pipeline.run`` single-symbol target — runner.py L297-L299
* Site 2: ``Pipeline.run_pooled`` per-symbol target — runner.py L450-L452
* Site 3: ``_run_one_horizon_sequences`` LSTM target — runner.py L715-L717
* Site 4: ``cli/forecast.py.run`` per-horizon target — forecast.py L276-L278
* Site 5: ``iv_features._har_expected_rv`` target — iv_features.py L66-L72

See ``/memories/session/plan.md`` for the full migration plan.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.utils.targets import forward_log_rv


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rv_504() -> pd.Series:
    """504-business-day positive RV series (deterministic AR(1)-like)."""
    rng = np.random.default_rng(0)
    n = 504
    dates = pd.bdate_range("2020-01-02", periods=n)
    log_rv = np.zeros(n)
    log_rv[0] = np.log(0.0001)
    for i in range(1, n):
        log_rv[i] = -4.5 + 0.6 * log_rv[i - 1] + 0.25 * rng.standard_normal()
    return pd.Series(np.exp(log_rv), index=dates, name="rv")


@pytest.fixture
def rv_panel_3sym(rv_504) -> dict[str, pd.DataFrame]:
    """3-symbol panel of daily DataFrames each containing an 'rv' column."""
    rng = np.random.default_rng(1)
    out: dict[str, pd.DataFrame] = {}
    for sym, seed in zip(["AAPL", "MSFT", "SPY"], [10, 20, 30]):
        # Independent realisation per symbol but same shape.
        local = np.random.default_rng(seed)
        n = 504
        dates = pd.bdate_range("2020-01-02", periods=n)
        log_rv = np.zeros(n)
        log_rv[0] = np.log(0.0001)
        for i in range(1, n):
            log_rv[i] = -4.5 + 0.6 * log_rv[i - 1] + 0.25 * local.standard_normal()
        out[sym] = pd.DataFrame({"rv": np.exp(log_rv)}, index=dates)
    _ = rng  # quiet linter; rng kept for future use
    return out


# ---------------------------------------------------------------------------
# Site 1 — Pipeline.run single-symbol target
#     runner.py L297-L299:
#         if h == 1:
#             log_target = np.log(daily_data["rv"]).shift(-1)
#         else:
#             log_target = np.log(daily_data["rv"].rolling(h).mean()).shift(-h)
# ---------------------------------------------------------------------------


def _legacy_single_series_target(rv: pd.Series, h: int) -> pd.Series:
    """Exact replica of sites 1, 3, 4 inline code (no zero-clip)."""
    if h == 1:
        return np.log(rv).shift(-1)
    return np.log(rv.rolling(h).mean()).shift(-h)


@pytest.mark.parametrize("h", [1, 5, 22])
def test_site1_pipeline_run_single_symbol_equivalent(rv_504, h):
    """Site 1 inline target equals helper output (no zero floor differences on positive RV)."""
    legacy = _legacy_single_series_target(rv_504, h)
    new = forward_log_rv(rv_504, h)
    pd.testing.assert_series_equal(legacy, new, check_names=False)


def test_site1_dropna_row_count_unchanged(rv_504):
    """Row count after the site's `dropna()` block is identical legacy vs helper."""
    h = 5
    legacy = _legacy_single_series_target(rv_504, h)
    new = forward_log_rv(rv_504, h)
    # Site 1 does: concat([X, target]).replace(±inf, NaN).dropna()
    # On positive RV with no inf, equivalence reduces to target NaN locations.
    assert legacy.notna().sum() == new.notna().sum()
    assert legacy.notna().equals(new.notna())


# ---------------------------------------------------------------------------
# Site 2 — Pipeline.run_pooled per-symbol target then MultiIndex stack
#     runner.py L450-L452: same inline expression as site 1, applied per
#     symbol inside a loop, then stacked into a (date, symbol) MultiIndex.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("h", [1, 5, 22])
def test_site2_pooled_per_symbol_target_equivalent(rv_panel_3sym, h):
    """Per-symbol helper output, stacked with the same MultiIndex, equals legacy y."""
    legacy_frames: list[pd.Series] = []
    new_frames: list[pd.Series] = []
    for sym, daily in rv_panel_3sym.items():
        legacy = _legacy_single_series_target(daily["rv"], h)
        new = forward_log_rv(daily["rv"], h)
        # Mirror site-2 MultiIndex construction (date, symbol).
        legacy.index = pd.MultiIndex.from_arrays(
            [legacy.index, [sym] * len(legacy)], names=["date", "symbol"]
        )
        new.index = pd.MultiIndex.from_arrays(
            [new.index, [sym] * len(new)], names=["date", "symbol"]
        )
        legacy_frames.append(legacy)
        new_frames.append(new)
    legacy_y = pd.concat(legacy_frames)
    new_y = pd.concat(new_frames)
    pd.testing.assert_series_equal(legacy_y, new_y, check_names=False)


def test_site2_tree_model_dropna_mask_unchanged(rv_panel_3sym):
    """Site-2 custom mask (target non-NaN) keeps the same rows for legacy and helper."""
    h = 5
    for sym, daily in rv_panel_3sym.items():
        legacy = _legacy_single_series_target(daily["rv"], h)
        new = forward_log_rv(daily["rv"], h)
        assert legacy.notna().equals(new.notna())


# ---------------------------------------------------------------------------
# Site 3 — _run_one_horizon_sequences (LSTM path)
#     runner.py L715-L717: same inline expression as site 1, then
#     `target_aligned = log_target.reindex(seq.dates)`.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("h", [1, 22])
def test_site3_sequence_reindex_equivalent(rv_504, h):
    """After reindexing to a subset of dates (mimicking seq.dates), legacy == helper."""
    # Subset: every 3rd date in the second half of the series.
    seq_dates = rv_504.index[252::3]
    legacy = _legacy_single_series_target(rv_504, h).reindex(seq_dates)
    new = forward_log_rv(rv_504, h).reindex(seq_dates)
    pd.testing.assert_series_equal(legacy, new, check_names=False)
    # The valid mask used by the call site is identical.
    assert legacy.notna().values.tolist() == new.notna().values.tolist()


def test_site3_dtype_preserved_for_tensor_path(rv_504):
    """LSTM site casts target.values to float32. dtype before cast must match."""
    h = 22
    legacy = _legacy_single_series_target(rv_504, h)
    new = forward_log_rv(rv_504, h)
    assert legacy.dtype == new.dtype


# ---------------------------------------------------------------------------
# Site 4 — cli/forecast.py.run per-horizon target
#     forecast.py L276-L278: identical inline expression to site 1.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("h", [1, 5])
def test_site4_forecast_cli_target_equivalent(rv_504, h):
    """cli/forecast.py legacy target equals helper output."""
    legacy = _legacy_single_series_target(rv_504, h)
    new = forward_log_rv(rv_504, h)
    pd.testing.assert_series_equal(legacy, new, check_names=False)


# ---------------------------------------------------------------------------
# Site 5 — iv_features._har_expected_rv target
#     iv_features.py L66-L72: legacy uses `rv.clip(lower=1e-10)` BEFORE log.
#     Helper uses min_value=1e-20. The two are equivalent on any row where
#     rv >= 1e-10 (true for all real SPX RV). The two diverge only on rows
#     with rv < 1e-10, which never occur in production.
# ---------------------------------------------------------------------------


def _legacy_iv_features_target(rv: pd.Series, h: int) -> pd.Series:
    """Exact replica of site 5 inline code."""
    rv_clipped = rv.clip(lower=1e-10)
    if h == 1:
        return np.log(rv_clipped).shift(-1)
    return np.log(rv_clipped.rolling(h).mean()).shift(-h)


@pytest.mark.parametrize("h", [1, 22])
def test_site5_iv_features_target_equivalent_on_positive_rv(rv_504, h):
    """On real-world positive RV (>> 1e-10), legacy clipped target equals helper."""
    legacy = _legacy_iv_features_target(rv_504, h)
    new = forward_log_rv(rv_504, h)
    pd.testing.assert_series_equal(legacy, new, check_names=False)


def test_site5_floor_divergence_only_below_1e10():
    """When rv is below the legacy 1e-10 floor, the helper does NOT clip
    (its floor is 1e-20). This documents the only intentional, behavior-
    changing aspect of the site-5 migration. No production row triggers
    this (SPX RV >> 1e-10), but we pin the divergence so a future
    regression is obvious.
    """
    dates = pd.bdate_range("2020-01-02", periods=3)
    # Pick a value between the two floors: 1e-15 is above the helper's
    # 1e-20 floor (no clip) and below the legacy 1e-10 floor (gets clipped up).
    rv = pd.Series([1e-15, 1e-15, 1e-15], index=dates)
    legacy = _legacy_iv_features_target(rv, 1)
    new = forward_log_rv(rv, 1)
    # Legacy clips up to 1e-10 → log(1e-10) ≈ -23.03.
    # Helper leaves 1e-15 untouched (> 1e-20) → log(1e-15) ≈ -34.54.
    assert legacy.iloc[0] == pytest.approx(np.log(1e-10))
    assert new.iloc[0] == pytest.approx(np.log(1e-15))

    # And when rv is below BOTH floors, each clips to its own floor.
    rv_tiny = pd.Series([1e-25, 1e-25, 1e-25], index=dates)
    legacy_tiny = _legacy_iv_features_target(rv_tiny, 1)
    new_tiny = forward_log_rv(rv_tiny, 1)
    assert legacy_tiny.iloc[0] == pytest.approx(np.log(1e-10))
    assert new_tiny.iloc[0] == pytest.approx(np.log(1e-20))
