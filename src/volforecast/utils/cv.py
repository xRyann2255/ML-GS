"""Time-series cross-validation utilities.

Implements proper CV protocols for time-series forecasting:
- Purged k-fold CV (with gap to prevent leakage)
- Blocked k-fold CV (contiguous blocks, no shuffling)
- Expanding window (walk-forward) CV
- Rolling window CV

CRITICAL: Never use random k-fold on time-series data.
Random k-fold causes catastrophic look-ahead bias.

Key classes:
    PurgedKFoldCV     — K-fold with purge gap between train/test
    BlockedKFoldCV    — Contiguous block k-fold (no shuffling)
    ExpandingWindowCV — Expanding training window, fixed test size
    RollingWindowCV   — Fixed-size rolling training window
"""

from __future__ import annotations

from collections.abc import Generator

import numpy as np
import pandas as pd


class _BaseCVSplitter:
    """Common interface for time-series CV splitters."""

    def split(
        self,
        X: pd.DataFrame,
        y: pd.Series | None = None,
    ) -> Generator[tuple[np.ndarray, np.ndarray], None, None]:
        """Generate train/test index arrays."""
        n = len(X)
        for train_idx, test_idx in self._generate_splits(n):
            if len(train_idx) > 0 and len(test_idx) > 0:
                yield train_idx, test_idx

    def _generate_splits(self, n: int) -> Generator[tuple[np.ndarray, np.ndarray], None, None]:
        raise NotImplementedError


class PurgedKFoldCV(_BaseCVSplitter):
    """Purged k-fold cross-validation for time series.

    Splits data into k contiguous folds and purges observations
    within a gap window between training and test sets to prevent
    information leakage from overlapping RV windows.

    ``embargo`` (Phase 2.8): rows in ``[test_end, test_end + embargo)`` are also
    excluded from the train sets of all SUBSEQUENT folds. Default 0 (no-op).
    """

    def __init__(
        self,
        n_splits: int = 5,
        purge_gap: int = 5,
        embargo: int = 0,
    ) -> None:
        self.n_splits = n_splits
        self.purge_gap = purge_gap
        self.embargo = embargo

    def _generate_splits(self, n: int) -> Generator[tuple[np.ndarray, np.ndarray], None, None]:
        indices = np.arange(n)
        fold_size = n // self.n_splits
        embargo_mask = np.zeros(n, dtype=bool)

        for i in range(self.n_splits):
            test_start = i * fold_size
            test_end = (i + 1) * fold_size if i < self.n_splits - 1 else n
            test_idx = indices[test_start:test_end]

            # Purge: remove observations within purge_gap of test boundaries
            train_mask = np.ones(n, dtype=bool)
            train_mask[test_start:test_end] = False
            purge_start = max(0, test_start - self.purge_gap)
            train_mask[purge_start:test_start] = False
            purge_end = min(n, test_end + self.purge_gap)
            train_mask[test_end:purge_end] = False

            # Embargo: drop indices that fell in the post-test window of any
            # prior fold from this fold's train set.
            if self.embargo > 0:
                train_mask &= ~embargo_mask

            train_idx = indices[train_mask]
            yield train_idx, test_idx

            if self.embargo > 0:
                embargo_end = min(n, test_end + self.embargo)
                embargo_mask[test_end:embargo_end] = True


class BlockedKFoldCV(_BaseCVSplitter):
    """Blocked k-fold CV (contiguous blocks, no shuffling).

    Each fold is a contiguous time block. Training uses all
    blocks except the test block. No purge gap (simpler but
    may have mild leakage at boundaries).

    ``embargo`` (Phase 2.8): rows in ``[test_end, test_end + embargo)`` are also
    excluded from the train sets of all SUBSEQUENT folds. Default 0 (no-op).
    """

    def __init__(self, n_splits: int = 5, embargo: int = 0) -> None:
        self.n_splits = n_splits
        self.embargo = embargo

    def _generate_splits(self, n: int) -> Generator[tuple[np.ndarray, np.ndarray], None, None]:
        indices = np.arange(n)
        fold_size = n // self.n_splits
        embargo_mask = np.zeros(n, dtype=bool)

        for i in range(self.n_splits):
            test_start = i * fold_size
            test_end = (i + 1) * fold_size if i < self.n_splits - 1 else n
            test_idx = indices[test_start:test_end]

            train_mask = np.ones(n, dtype=bool)
            train_mask[test_start:test_end] = False
            if self.embargo > 0:
                train_mask &= ~embargo_mask
            train_idx = indices[train_mask]
            yield train_idx, test_idx

            if self.embargo > 0:
                embargo_end = min(n, test_end + self.embargo)
                embargo_mask[test_end:embargo_end] = True


class ExpandingWindowCV(_BaseCVSplitter):
    """Expanding window (walk-forward) cross-validation.

    Training window starts at the beginning and expands forward.
    Test window is a fixed-size block following the training end.

    ``embargo`` (Phase 2.8): rows in ``[test_end, test_end + embargo)`` are also
    excluded from the train sets of all SUBSEQUENT folds. Default 0 (no-op).
    """

    def __init__(
        self,
        min_train_size: int = 500,
        test_size: int = 63,
        step_size: int = 63,
        purge_gap: int = 5,
        embargo: int = 0,
    ) -> None:
        self.min_train_size = min_train_size
        self.test_size = test_size
        self.step_size = step_size
        self.purge_gap = purge_gap
        self.embargo = embargo

    def _generate_splits(self, n: int) -> Generator[tuple[np.ndarray, np.ndarray], None, None]:
        indices = np.arange(n)
        start = self.min_train_size
        last_test_end = 0
        embargo_mask = np.zeros(n, dtype=bool)

        while start + self.purge_gap + self.test_size <= n:
            train_end = start
            test_start = start + self.purge_gap
            test_end = test_start + self.test_size

            if self.embargo > 0:
                train_mask = np.zeros(n, dtype=bool)
                train_mask[:train_end] = True
                train_mask &= ~embargo_mask
                train_idx = indices[train_mask]
            else:
                train_idx = indices[:train_end]
            test_idx = indices[test_start:test_end]

            last_test_end = test_end
            yield train_idx, test_idx
            start += self.step_size

            if self.embargo > 0:
                embargo_end = min(n, test_end + self.embargo)
                embargo_mask[test_end:embargo_end] = True

        # Stub fold: cover remaining indices that didn't fill a full test window.
        # Uses the same expanding-window logic — train on all data before the
        # purge gap, test on the remainder. No lookahead bias.
        if last_test_end < n:
            train_end = start
            test_start = start + self.purge_gap
            if test_start < n:
                if self.embargo > 0:
                    train_mask = np.zeros(n, dtype=bool)
                    train_mask[:train_end] = True
                    train_mask &= ~embargo_mask
                    train_idx = indices[train_mask]
                else:
                    train_idx = indices[:train_end]
                test_idx = indices[test_start:n]
                yield train_idx, test_idx


class PanelExpandingWindowCV:
    """Expanding window CV for panel (multi-symbol) DataFrames.

    Splits are defined on **unique dates** in the index, then mapped
    to all rows sharing those dates. This ensures all symbols for a
    given date land in the same fold, preventing cross-temporal leakage.

    ``embargo`` (Phase 2.8): dates in ``[test_end, test_end + embargo)``
    (positions in the unique-date sequence) are excluded from the train sets
    of all SUBSEQUENT folds. All symbols sharing an embargoed date are
    dropped together. Default 0 (no-op).
    """

    def __init__(
        self,
        min_train_dates: int = 500,
        test_dates: int = 63,
        step_dates: int = 63,
        purge_gap: int = 5,
        embargo: int = 0,
    ) -> None:
        self.min_train_dates = min_train_dates
        self.test_dates = test_dates
        self.step_dates = step_dates
        self.purge_gap = purge_gap
        self.embargo = embargo

    def split(
        self,
        X: pd.DataFrame,
        y: pd.Series | None = None,
    ) -> Generator[tuple[np.ndarray, np.ndarray], None, None]:
        """Generate train/test index arrays based on unique dates."""
        unique_dates = X.index.unique().sort_values()
        n_dates = len(unique_dates)
        row_indices = np.arange(len(X))
        start = self.min_train_dates
        last_test_end = 0
        embargo_mask = np.zeros(n_dates, dtype=bool)

        while start + self.purge_gap + self.test_dates <= n_dates:
            train_end = start  # exclusive
            test_start = start + self.purge_gap
            test_end = test_start + self.test_dates

            if self.embargo > 0:
                train_pos_mask = np.zeros(n_dates, dtype=bool)
                train_pos_mask[:train_end] = True
                train_pos_mask &= ~embargo_mask
                train_dates = unique_dates[train_pos_mask]
            else:
                train_dates = unique_dates[:train_end]
            test_dates_slice = unique_dates[test_start:test_end]

            train_mask = X.index.isin(train_dates)
            test_mask = X.index.isin(test_dates_slice)

            train_idx = row_indices[train_mask]
            test_idx = row_indices[test_mask]

            last_test_end = test_end
            yield train_idx, test_idx
            start += self.step_dates

            if self.embargo > 0:
                embargo_end = min(n_dates, test_end + self.embargo)
                embargo_mask[test_end:embargo_end] = True

        # Stub fold: cover remaining dates that didn't fill a full test window.
        # Same expanding-window logic — train on all data before the purge gap,
        # test on the remainder. No lookahead bias.
        if last_test_end < n_dates:
            train_end = start
            test_start = start + self.purge_gap
            if test_start < n_dates:
                if self.embargo > 0:
                    train_pos_mask = np.zeros(n_dates, dtype=bool)
                    train_pos_mask[:train_end] = True
                    train_pos_mask &= ~embargo_mask
                    train_dates = unique_dates[train_pos_mask]
                else:
                    train_dates = unique_dates[:train_end]
                test_dates_slice = unique_dates[test_start:n_dates]

                train_mask = X.index.isin(train_dates)
                test_mask = X.index.isin(test_dates_slice)

                train_idx = row_indices[train_mask]
                test_idx = row_indices[test_mask]

                if len(train_idx) > 0 and len(test_idx) > 0:
                    yield train_idx, test_idx


class RollingWindowCV(_BaseCVSplitter):
    """Fixed-size rolling window cross-validation.

    Both training and test windows have fixed sizes.
    The window rolls forward by step_size each iteration.

    ``embargo`` (Phase 2.8): rows in ``[test_end, test_end + embargo)`` are also
    excluded from the train sets of all SUBSEQUENT folds. Default 0 (no-op).
    """

    def __init__(
        self,
        train_size: int = 756,
        test_size: int = 63,
        step_size: int = 63,
        purge_gap: int = 5,
        embargo: int = 0,
    ) -> None:
        self.train_size = train_size
        self.test_size = test_size
        self.step_size = step_size
        self.purge_gap = purge_gap
        self.embargo = embargo

    def _generate_splits(self, n: int) -> Generator[tuple[np.ndarray, np.ndarray], None, None]:
        indices = np.arange(n)
        start = self.train_size
        embargo_mask = np.zeros(n, dtype=bool)

        while start + self.purge_gap + self.test_size <= n:
            train_start = start - self.train_size
            train_end = start
            test_start = start + self.purge_gap
            test_end = test_start + self.test_size

            if self.embargo > 0:
                train_mask = np.zeros(n, dtype=bool)
                train_mask[train_start:train_end] = True
                train_mask &= ~embargo_mask
                train_idx = indices[train_mask]
            else:
                train_idx = indices[train_start:train_end]
            test_idx = indices[test_start:test_end]

            yield train_idx, test_idx
            start += self.step_size

            if self.embargo > 0:
                embargo_end = min(n, test_end + self.embargo)
                embargo_mask[test_end:embargo_end] = True
