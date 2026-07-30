"""Tests for time-series cross-validation splitters.

Validates:
1. No overlap between train and test indices
2. Purge gap is respected (no indices within gap of test boundaries)
3. Correct number of splits produced
4. All indices are within bounds
5. Expanding/rolling windows grow/move correctly
"""

import numpy as np
import pandas as pd
import pytest

from volforecast.utils.cv import (
    BlockedKFoldCV,
    ExpandingWindowCV,
    PanelExpandingWindowCV,
    PurgedKFoldCV,
    RollingWindowCV,
)


@pytest.fixture
def df_1000():
    """1000-row DataFrame for CV testing."""
    return pd.DataFrame({"x": np.arange(1000)})


@pytest.fixture
def df_2000():
    """2000-row DataFrame for expanding/rolling window tests."""
    return pd.DataFrame({"x": np.arange(2000)})


# ---------------------------------------------------------------------------
# PurgedKFoldCV
# ---------------------------------------------------------------------------


class TestPurgedKFoldCV:
    def test_no_overlap_train_test(self, df_1000):
        cv = PurgedKFoldCV(n_splits=5, purge_gap=5)
        for train_idx, test_idx in cv.split(df_1000):
            overlap = np.intersect1d(train_idx, test_idx)
            assert len(overlap) == 0, f"Overlap found: {overlap}"

    def test_purge_gap_respected(self, df_1000):
        purge_gap = 10
        cv = PurgedKFoldCV(n_splits=5, purge_gap=purge_gap)
        for train_idx, test_idx in cv.split(df_1000):
            test_min, test_max = test_idx.min(), test_idx.max()
            # No train index within purge_gap before test start
            close_before = train_idx[(train_idx >= test_min - purge_gap) & (train_idx < test_min)]
            assert len(close_before) == 0, (
                f"Train indices {close_before} within purge gap before test"
            )
            # No train index within purge_gap after test end
            close_after = train_idx[(train_idx > test_max) & (train_idx <= test_max + purge_gap)]
            assert len(close_after) == 0, f"Train indices {close_after} within purge gap after test"

    def test_number_of_splits(self, df_1000):
        cv = PurgedKFoldCV(n_splits=5, purge_gap=5)
        splits = list(cv.split(df_1000))
        assert len(splits) == 5

    def test_all_indices_in_bounds(self, df_1000):
        cv = PurgedKFoldCV(n_splits=5, purge_gap=5)
        n = len(df_1000)
        for train_idx, test_idx in cv.split(df_1000):
            assert train_idx.min() >= 0
            assert train_idx.max() < n
            assert test_idx.min() >= 0
            assert test_idx.max() < n

    def test_test_sets_cover_all_data(self, df_1000):
        cv = PurgedKFoldCV(n_splits=5, purge_gap=0)
        all_test = np.concatenate([test for _, test in cv.split(df_1000)])
        assert len(np.unique(all_test)) == len(df_1000)

    def test_larger_purge_reduces_train_size(self, df_1000):
        cv_small = PurgedKFoldCV(n_splits=5, purge_gap=2)
        cv_large = PurgedKFoldCV(n_splits=5, purge_gap=20)
        splits_small = list(cv_small.split(df_1000))
        splits_large = list(cv_large.split(df_1000))
        # Larger purge -> fewer training samples
        assert len(splits_small[0][0]) > len(splits_large[0][0])


# ---------------------------------------------------------------------------
# BlockedKFoldCV
# ---------------------------------------------------------------------------


class TestBlockedKFoldCV:
    def test_no_overlap_train_test(self, df_1000):
        cv = BlockedKFoldCV(n_splits=5)
        for train_idx, test_idx in cv.split(df_1000):
            overlap = np.intersect1d(train_idx, test_idx)
            assert len(overlap) == 0

    def test_number_of_splits(self, df_1000):
        cv = BlockedKFoldCV(n_splits=5)
        splits = list(cv.split(df_1000))
        assert len(splits) == 5

    def test_test_blocks_are_contiguous(self, df_1000):
        cv = BlockedKFoldCV(n_splits=5)
        for _, test_idx in cv.split(df_1000):
            # Contiguous = consecutive integers
            assert np.all(np.diff(test_idx) == 1)

    def test_test_sets_cover_all_data(self, df_1000):
        cv = BlockedKFoldCV(n_splits=5)
        all_test = np.concatenate([test for _, test in cv.split(df_1000)])
        assert len(np.unique(all_test)) == len(df_1000)

    def test_train_size_consistent(self, df_1000):
        """Each fold's train size should be ~80% of data (4/5 blocks)."""
        cv = BlockedKFoldCV(n_splits=5)
        for train_idx, _ in cv.split(df_1000):
            assert len(train_idx) == pytest.approx(800, abs=1)


# ---------------------------------------------------------------------------
# ExpandingWindowCV
# ---------------------------------------------------------------------------


class TestExpandingWindowCV:
    def test_no_overlap_train_test(self, df_2000):
        cv = ExpandingWindowCV(min_train_size=500, test_size=63, step_size=63, purge_gap=5)
        for train_idx, test_idx in cv.split(df_2000):
            overlap = np.intersect1d(train_idx, test_idx)
            assert len(overlap) == 0

    def test_purge_gap_respected(self, df_2000):
        purge_gap = 5
        cv = ExpandingWindowCV(min_train_size=500, test_size=63, step_size=63, purge_gap=purge_gap)
        for train_idx, test_idx in cv.split(df_2000):
            train_max = train_idx.max()
            test_min = test_idx.min()
            # Gap between last train obs and first test obs
            assert test_min - train_max > purge_gap

    def test_training_window_expands(self, df_2000):
        cv = ExpandingWindowCV(min_train_size=500, test_size=63, step_size=63, purge_gap=5)
        splits = list(cv.split(df_2000))
        train_sizes = [len(train) for train, _ in splits]
        # Each successive train set should be larger (expanding)
        for i in range(1, len(train_sizes)):
            assert train_sizes[i] > train_sizes[i - 1]

    def test_min_train_size_respected(self, df_2000):
        min_train = 500
        cv = ExpandingWindowCV(min_train_size=min_train, test_size=63, step_size=63, purge_gap=5)
        for train_idx, _ in cv.split(df_2000):
            assert len(train_idx) >= min_train

    def test_test_size_consistent(self, df_2000):
        test_size = 63
        cv = ExpandingWindowCV(min_train_size=500, test_size=test_size, step_size=63, purge_gap=5)
        splits = list(cv.split(df_2000))
        for _, test_idx in splits[:-1]:
            assert len(test_idx) == test_size
        # Last fold (stub) may be smaller
        assert 0 < len(splits[-1][1]) <= test_size

    def test_produces_splits(self, df_2000):
        cv = ExpandingWindowCV(min_train_size=500, test_size=63, step_size=63, purge_gap=5)
        splits = list(cv.split(df_2000))
        assert len(splits) > 0

    def test_no_tail_gap(self):
        """All indices beyond min_train_size+purge_gap are in at least one test fold."""
        n = 2000
        df = pd.DataFrame({"x": np.arange(n)})
        # Use step > test to guarantee a remainder
        cv = ExpandingWindowCV(min_train_size=500, test_size=126, step_size=126, purge_gap=10)
        splits = list(cv.split(df))
        all_test = set()
        for _, test_idx in splits:
            all_test.update(test_idx.tolist())
        expected = set(range(500 + 10, n))
        missing = expected - all_test
        assert len(missing) == 0, f"{len(missing)} tail indices missing from test folds"


# ---------------------------------------------------------------------------
# RollingWindowCV
# ---------------------------------------------------------------------------


class TestRollingWindowCV:
    def test_no_overlap_train_test(self, df_2000):
        cv = RollingWindowCV(train_size=756, test_size=63, step_size=63, purge_gap=5)
        for train_idx, test_idx in cv.split(df_2000):
            overlap = np.intersect1d(train_idx, test_idx)
            assert len(overlap) == 0

    def test_purge_gap_respected(self, df_2000):
        purge_gap = 5
        cv = RollingWindowCV(train_size=756, test_size=63, step_size=63, purge_gap=purge_gap)
        for train_idx, test_idx in cv.split(df_2000):
            train_max = train_idx.max()
            test_min = test_idx.min()
            assert test_min - train_max > purge_gap

    def test_fixed_train_size(self, df_2000):
        train_size = 756
        cv = RollingWindowCV(train_size=train_size, test_size=63, step_size=63, purge_gap=5)
        for train_idx, _ in cv.split(df_2000):
            assert len(train_idx) == train_size

    def test_test_size_consistent(self, df_2000):
        test_size = 63
        cv = RollingWindowCV(train_size=756, test_size=test_size, step_size=63, purge_gap=5)
        for _, test_idx in cv.split(df_2000):
            assert len(test_idx) == test_size

    def test_window_rolls_forward(self, df_2000):
        cv = RollingWindowCV(train_size=756, test_size=63, step_size=63, purge_gap=5)
        splits = list(cv.split(df_2000))
        train_starts = [train[0] for train, _ in splits]
        # Each train start should advance by step_size
        for i in range(1, len(train_starts)):
            assert train_starts[i] == train_starts[i - 1] + 63

    def test_produces_splits(self, df_2000):
        cv = RollingWindowCV(train_size=756, test_size=63, step_size=63, purge_gap=5)
        splits = list(cv.split(df_2000))
        assert len(splits) > 0


# ---------------------------------------------------------------------------
# PanelExpandingWindowCV
# ---------------------------------------------------------------------------


class TestPanelExpandingWindowCV:
    """Tests for date-based panel CV splitter."""

    @pytest.fixture
    def panel_df(self):
        """Panel DataFrame: 3 symbols × 200 dates = 600 rows."""
        dates = pd.bdate_range("2020-01-02", periods=200)
        frames = []
        for sym in ["SPY", "AAPL", "MSFT"]:
            df = pd.DataFrame({"x": np.arange(200), "symbol": sym}, index=dates)
            frames.append(df)
        return pd.concat(frames).sort_index(kind="mergesort")

    def test_splits_are_date_based(self, panel_df):
        """All rows for a given date land in the same fold (train or test)."""
        cv = PanelExpandingWindowCV(min_train_dates=100, test_dates=20, step_dates=20, purge_gap=5)
        for train_idx, test_idx in cv.split(panel_df):
            train_dates = set(panel_df.index[train_idx])
            test_dates = set(panel_df.index[test_idx])
            # No date should appear in both train and test
            assert train_dates.isdisjoint(test_dates)

    def test_no_overlap_train_test(self, panel_df):
        """Train and test row indices don't overlap."""
        cv = PanelExpandingWindowCV(min_train_dates=100, test_dates=20, step_dates=20, purge_gap=5)
        for train_idx, test_idx in cv.split(panel_df):
            overlap = np.intersect1d(train_idx, test_idx)
            assert len(overlap) == 0

    def test_purge_gap_on_dates(self, panel_df):
        """Purge gap operates on dates: gap between last train date and first test date."""
        purge_gap = 5
        cv = PanelExpandingWindowCV(
            min_train_dates=100, test_dates=20, step_dates=20, purge_gap=purge_gap
        )
        unique_dates = panel_df.index.unique().sort_values()
        for train_idx, test_idx in cv.split(panel_df):
            train_dates = panel_df.index[train_idx].unique().sort_values()
            test_dates = panel_df.index[test_idx].unique().sort_values()
            last_train_pos = unique_dates.get_loc(train_dates[-1])
            first_test_pos = unique_dates.get_loc(test_dates[0])
            assert first_test_pos - last_train_pos > purge_gap

    def test_all_symbols_present_per_fold(self, panel_df):
        """Each test fold should contain rows from all symbols."""
        cv = PanelExpandingWindowCV(min_train_dates=100, test_dates=20, step_dates=20, purge_gap=5)
        for _, test_idx in cv.split(panel_df):
            test_symbols = panel_df.iloc[test_idx]["symbol"].unique()
            assert set(test_symbols) == {"SPY", "AAPL", "MSFT"}

    def test_training_window_expands(self, panel_df):
        """Training window should grow with each fold."""
        cv = PanelExpandingWindowCV(min_train_dates=100, test_dates=20, step_dates=20, purge_gap=5)
        splits = list(cv.split(panel_df))
        train_sizes = [len(train) for train, _ in splits]
        for i in range(1, len(train_sizes)):
            assert train_sizes[i] > train_sizes[i - 1]

    def test_test_size_matches_dates(self, panel_df):
        """Test fold should contain exactly test_dates × n_symbols rows (stub may be smaller)."""
        n_symbols = 3
        test_dates = 20
        cv = PanelExpandingWindowCV(
            min_train_dates=100, test_dates=test_dates, step_dates=20, purge_gap=5
        )
        splits = list(cv.split(panel_df))
        for _, test_idx in splits[:-1]:
            assert len(test_idx) == test_dates * n_symbols
        # Last fold (stub) may cover fewer dates
        assert 0 < len(splits[-1][1]) <= test_dates * n_symbols

    def test_min_train_dates_respected(self, panel_df):
        """First fold should have at least min_train_dates unique dates."""
        min_train = 100
        cv = PanelExpandingWindowCV(
            min_train_dates=min_train, test_dates=20, step_dates=20, purge_gap=5
        )
        splits = list(cv.split(panel_df))
        first_train_idx = splits[0][0]
        first_train_dates = panel_df.index[first_train_idx].nunique()
        assert first_train_dates >= min_train

    def test_produces_splits(self, panel_df):
        """Produces at least one split."""
        cv = PanelExpandingWindowCV(min_train_dates=100, test_dates=20, step_dates=20, purge_gap=5)
        splits = list(cv.split(panel_df))
        assert len(splits) > 0

    def test_indices_in_bounds(self, panel_df):
        """All returned indices are within DataFrame bounds."""
        cv = PanelExpandingWindowCV(min_train_dates=100, test_dates=20, step_dates=20, purge_gap=5)
        n = len(panel_df)
        for train_idx, test_idx in cv.split(panel_df):
            assert train_idx.min() >= 0
            assert train_idx.max() < n
            assert test_idx.min() >= 0
            assert test_idx.max() < n

    def test_no_tail_gap_all_dates_covered(self):
        """All dates beyond min_train_dates+purge_gap are in at least one test fold.

        Regression: step_dates > 1 used to leave orphan tail dates with no OOS predictions.
        """
        # 300 dates, step=126, test=126, purge=10: (300-510) won't divide evenly
        # Use params that create a guaranteed remainder
        dates = pd.bdate_range("2020-01-02", periods=300)
        frames = []
        for sym in ["A", "B"]:
            frames.append(pd.DataFrame({"x": np.arange(300), "symbol": sym}, index=dates))
        panel = pd.concat(frames).sort_index(kind="mergesort")

        cv = PanelExpandingWindowCV(
            min_train_dates=100, test_dates=126, step_dates=126, purge_gap=10
        )
        splits = list(cv.split(panel))
        # Collect all test dates
        all_test_dates = set()
        for _, test_idx in splits:
            all_test_dates.update(panel.index[test_idx].unique())

        # Every date beyond min_train_dates + purge_gap should appear in test
        unique_dates = panel.index.unique().sort_values()
        expected_test_dates = set(unique_dates[100 + 10 :])
        missing = expected_test_dates - all_test_dates
        assert len(missing) == 0, f"{len(missing)} tail dates missing from test folds"

    def test_stub_fold_respects_purge_gap(self):
        """The stub fold (if emitted) maintains the purge gap — no lookahead."""
        dates = pd.bdate_range("2020-01-02", periods=300)
        frames = []
        for sym in ["A", "B"]:
            frames.append(pd.DataFrame({"x": np.arange(300), "symbol": sym}, index=dates))
        panel = pd.concat(frames).sort_index(kind="mergesort")

        purge_gap = 10
        cv = PanelExpandingWindowCV(
            min_train_dates=100, test_dates=126, step_dates=126, purge_gap=purge_gap
        )
        unique_dates = panel.index.unique().sort_values()

        for train_idx, test_idx in cv.split(panel):
            train_dates = panel.index[train_idx].unique().sort_values()
            test_dates_fold = panel.index[test_idx].unique().sort_values()
            last_train_pos = unique_dates.get_loc(train_dates[-1])
            first_test_pos = unique_dates.get_loc(test_dates_fold[0])
            assert first_test_pos - last_train_pos > purge_gap, (
                f"Purge gap violated: last_train={last_train_pos}, first_test={first_test_pos}"
            )

    def test_stub_fold_no_lookahead_bias(self):
        """Train dates in any fold (including stub) are strictly before test dates."""
        dates = pd.bdate_range("2020-01-02", periods=300)
        frames = []
        for sym in ["A", "B"]:
            frames.append(pd.DataFrame({"x": np.arange(300), "symbol": sym}, index=dates))
        panel = pd.concat(frames).sort_index(kind="mergesort")

        cv = PanelExpandingWindowCV(
            min_train_dates=100, test_dates=126, step_dates=126, purge_gap=10
        )

        for train_idx, test_idx in cv.split(panel):
            train_max_date = panel.index[train_idx].max()
            test_min_date = panel.index[test_idx].min()
            assert train_max_date < test_min_date, (
                f"Lookahead! train_max={train_max_date}, test_min={test_min_date}"
            )


# ---------------------------------------------------------------------------
# Embargo (Phase 2.8) — post-test exclusion of subsequent fold train sets
# ---------------------------------------------------------------------------
#
# Definition: embargo=k excludes rows/dates in [test_end, test_end + k) from
# the train sets of ALL SUBSEQUENT folds. Independent of purge_gap (which is
# a pre-test exclusion). Default 0 = no behaviour change.


@pytest.fixture
def panel_df():
    """Module-level panel fixture for embargo tests (3 symbols × 200 dates)."""
    dates = pd.bdate_range("2020-01-02", periods=200)
    frames = []
    for sym in ["SPY", "AAPL", "MSFT"]:
        df = pd.DataFrame({"x": np.arange(200), "symbol": sym}, index=dates)
        frames.append(df)
    return pd.concat(frames).sort_index(kind="mergesort")


def _assert_embargo_respected_idx(splits, embargo):
    """For every fold k>=1, no train index lies in any prior fold's embargo zone."""
    prior_zones = []  # list of (start_inclusive, end_exclusive)
    for train_idx, test_idx in splits:
        for zs, ze in prior_zones:
            in_zone = train_idx[(train_idx >= zs) & (train_idx < ze)]
            assert len(in_zone) == 0, (
                f"Train indices {in_zone} fall in embargo zone [{zs}, {ze})"
            )
        test_end = int(test_idx.max()) + 1
        prior_zones.append((test_end, test_end + embargo))


def _assert_embargo_respected_dates(splits, df, embargo):
    """For every fold k>=1, no train DATE falls in any prior fold's embargoed date positions.

    Embargo is measured in unique-date positions, not row indices.
    """
    unique_dates = df.index.unique().sort_values()
    prior_zones = []  # list of (pos_start_inclusive, pos_end_exclusive) in unique_dates
    for train_idx, test_idx in splits:
        train_dates = df.index[train_idx].unique()
        train_positions = unique_dates.get_indexer(train_dates)
        for zs, ze in prior_zones:
            offenders = train_positions[(train_positions >= zs) & (train_positions < ze)]
            assert len(offenders) == 0, (
                f"Train date positions {offenders} fall in embargo zone [{zs}, {ze})"
            )
        test_dates = df.index[test_idx].unique()
        test_positions = unique_dates.get_indexer(test_dates)
        test_end_pos = int(test_positions.max()) + 1
        prior_zones.append((test_end_pos, test_end_pos + embargo))


# --- PurgedKFoldCV --------------------------------------------------------


class TestEmbargoPurgedKFoldCV:
    def test_embargo_excludes_post_test_dates(self, df_1000):
        cv = PurgedKFoldCV(n_splits=5, purge_gap=2, embargo=10)
        splits = list(cv.split(df_1000))
        _assert_embargo_respected_idx(splits, embargo=10)

    def test_embargo_zero_preserves_behaviour(self, df_1000):
        cv_default = PurgedKFoldCV(n_splits=5, purge_gap=5)
        cv_zero = PurgedKFoldCV(n_splits=5, purge_gap=5, embargo=0)
        a = [(t.tolist(), s.tolist()) for t, s in cv_default.split(df_1000)]
        b = [(t.tolist(), s.tolist()) for t, s in cv_zero.split(df_1000)]
        assert a == b


# --- BlockedKFoldCV -------------------------------------------------------


class TestEmbargoBlockedKFoldCV:
    def test_embargo_excludes_post_test_dates(self, df_1000):
        cv = BlockedKFoldCV(n_splits=5, embargo=10)
        splits = list(cv.split(df_1000))
        _assert_embargo_respected_idx(splits, embargo=10)

    def test_embargo_zero_preserves_behaviour(self, df_1000):
        cv_default = BlockedKFoldCV(n_splits=5)
        cv_zero = BlockedKFoldCV(n_splits=5, embargo=0)
        a = [(t.tolist(), s.tolist()) for t, s in cv_default.split(df_1000)]
        b = [(t.tolist(), s.tolist()) for t, s in cv_zero.split(df_1000)]
        assert a == b


# --- ExpandingWindowCV ----------------------------------------------------


class TestEmbargoExpandingWindowCV:
    def test_embargo_excludes_post_test_dates(self, df_2000):
        cv = ExpandingWindowCV(
            min_train_size=500, test_size=63, step_size=63, purge_gap=5, embargo=10
        )
        splits = list(cv.split(df_2000))
        _assert_embargo_respected_idx(splits, embargo=10)

    def test_embargo_zero_preserves_behaviour(self, df_2000):
        cv_default = ExpandingWindowCV(
            min_train_size=500, test_size=63, step_size=63, purge_gap=5
        )
        cv_zero = ExpandingWindowCV(
            min_train_size=500, test_size=63, step_size=63, purge_gap=5, embargo=0
        )
        a = [(t.tolist(), s.tolist()) for t, s in cv_default.split(df_2000)]
        b = [(t.tolist(), s.tolist()) for t, s in cv_zero.split(df_2000)]
        assert a == b


# --- RollingWindowCV ------------------------------------------------------


class TestEmbargoRollingWindowCV:
    def test_embargo_excludes_post_test_dates(self, df_2000):
        cv = RollingWindowCV(
            train_size=500, test_size=63, step_size=63, purge_gap=5, embargo=10
        )
        splits = list(cv.split(df_2000))
        _assert_embargo_respected_idx(splits, embargo=10)

    def test_embargo_zero_preserves_behaviour(self, df_2000):
        cv_default = RollingWindowCV(
            train_size=500, test_size=63, step_size=63, purge_gap=5
        )
        cv_zero = RollingWindowCV(
            train_size=500, test_size=63, step_size=63, purge_gap=5, embargo=0
        )
        a = [(t.tolist(), s.tolist()) for t, s in cv_default.split(df_2000)]
        b = [(t.tolist(), s.tolist()) for t, s in cv_zero.split(df_2000)]
        assert a == b


# --- PanelExpandingWindowCV ----------------------------------------------


class TestEmbargoPanelExpandingWindowCV:
    def test_embargo_excludes_post_test_dates(self, panel_df):
        cv = PanelExpandingWindowCV(
            min_train_dates=100, test_dates=20, step_dates=20, purge_gap=5, embargo=10
        )
        splits = list(cv.split(panel_df))
        _assert_embargo_respected_dates(splits, panel_df, embargo=10)

    def test_embargo_zero_preserves_behaviour(self, panel_df):
        cv_default = PanelExpandingWindowCV(
            min_train_dates=100, test_dates=20, step_dates=20, purge_gap=5
        )
        cv_zero = PanelExpandingWindowCV(
            min_train_dates=100, test_dates=20, step_dates=20, purge_gap=5, embargo=0
        )
        a = [(t.tolist(), s.tolist()) for t, s in cv_default.split(panel_df)]
        b = [(t.tolist(), s.tolist()) for t, s in cv_zero.split(panel_df)]
        assert a == b

    def test_embargo_with_panel_dates(self, panel_df):
        """For any embargoed date, ALL 3 symbols' rows are excluded from next fold's train."""
        embargo = 5
        cv = PanelExpandingWindowCV(
            min_train_dates=100, test_dates=20, step_dates=20, purge_gap=5, embargo=embargo
        )
        splits = list(cv.split(panel_df))
        assert len(splits) >= 2, "Need at least 2 folds for embargo to apply"

        unique_dates = panel_df.index.unique().sort_values()
        # Fold 0 test ends at position 100+5+20 = 125. Embargo zone = [125, 130).
        # Inspect fold 1's train set: must not include any row whose date is in
        # unique_dates[125:130], for ANY symbol.
        _, test0 = splits[0]
        test0_positions = unique_dates.get_indexer(panel_df.index[test0].unique())
        embargo_start = int(test0_positions.max()) + 1
        embargo_end = embargo_start + embargo
        embargoed_dates = set(unique_dates[embargo_start:embargo_end])

        train1, _ = splits[1]
        train1_date_set = set(panel_df.index[train1])
        leaked = embargoed_dates & train1_date_set
        assert not leaked, f"Embargoed dates {leaked} leaked into fold 1 train"

        # And specifically: all 3 symbols are absent for those dates
        fold1_rows = panel_df.iloc[train1]
        for d in embargoed_dates:
            if d in panel_df.index:
                rows_at_d = fold1_rows.loc[fold1_rows.index == d]
                assert len(rows_at_d) == 0, (
                    f"Embargoed date {d} had {len(rows_at_d)} rows in fold 1 train"
                )


# --- Runner integration ---------------------------------------------------


class TestRunnerThreadsEmbargo:
    def test_runner_threads_embargo(self):
        """_build_cv_splitter must pass cv_config.embargo through to the splitter."""
        from volforecast.config import CVConfig
        from volforecast.pipeline.runner import _build_cv_splitter

        cfg = CVConfig(method="expanding_window", embargo=3)
        splitter = _build_cv_splitter(cfg)
        assert splitter.embargo == 3

        cfg2 = CVConfig(method="purged_kfold", embargo=7)
        splitter2 = _build_cv_splitter(cfg2)
        assert splitter2.embargo == 7

        cfg3 = CVConfig(method="rolling_window", embargo=4)
        splitter3 = _build_cv_splitter(cfg3)
        assert splitter3.embargo == 4

        cfg4 = CVConfig(method="blocked_kfold", embargo=2)
        splitter4 = _build_cv_splitter(cfg4)
        assert splitter4.embargo == 2
