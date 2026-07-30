"""Regression tests for LSTM val purge — Bug 2.

Bug 2: When synthetic dates are used (one unique date per row, as created by
``pd.bdate_range("2000-01-01", periods=n_rows)``), the val_purge_gap operates
on individual rows instead of calendar dates × symbols.

With REAL pooled dates (e.g., 3 symbols sharing 50 dates = 150 rows), purging
5 dates should remove 5×3=15 rows from the train tail. But with synthetic
dates (150 unique dates for 150 rows), purging 5 "dates" = purging only 5 rows.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from volforecast.models.lstm import _split_train_val_by_date


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

N_DATES = 50
N_SYMBOLS = 3
N_ROWS = N_DATES * N_SYMBOLS
VAL_FRACTION = 0.2  # last 10 dates
VAL_PURGE_GAP = 5


def _make_real_pooled_dates() -> np.ndarray:
    """50 business dates × 3 symbols = 150 rows, each date repeated 3 times."""
    base_dates = pd.bdate_range("2020-01-01", periods=N_DATES)
    # Repeat each date N_SYMBOLS times (simulates pooled panel)
    return np.repeat(base_dates.values, N_SYMBOLS)


def _make_synthetic_dates() -> np.ndarray:
    """150 unique synthetic dates for 150 rows (mimics runner bug)."""
    return pd.bdate_range("2000-01-01", periods=N_ROWS).values


def _apply_purge(dates: np.ndarray, train_pos: np.ndarray, val_purge_gap: int) -> np.ndarray:
    """Replicate the purge logic from LSTMVolModel.fit() lines 925-937."""
    train_dates_arr = dates[train_pos]
    unique_train_dates = np.sort(np.unique(train_dates_arr))
    purge_n = min(int(val_purge_gap), len(unique_train_dates) // 2)
    if purge_n > 0:
        purge_dates = set(unique_train_dates[-purge_n:].tolist())
        keep_mask = np.array(
            [d not in purge_dates for d in train_dates_arr], dtype=bool
        )
        train_pos = train_pos[keep_mask]
    return train_pos


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestValPurgeWithRealDates:
    """Correct behavior: purge removes val_purge_gap dates × n_symbols rows."""

    def test_val_purge_with_real_dates_removes_dates_times_symbols(self):
        dates = _make_real_pooled_dates()
        assert dates.shape[0] == N_ROWS

        # Verify date structure: each unique date appears N_SYMBOLS times
        unique_dates = np.unique(dates)
        assert len(unique_dates) == N_DATES
        for d in unique_dates:
            assert np.sum(dates == d) == N_SYMBOLS

        # Split
        train_pos, val_pos = _split_train_val_by_date(dates, VAL_FRACTION)

        # val_fraction=0.2 of 50 dates = 10 val dates → 10×3=30 val rows
        assert len(val_pos) == 10 * N_SYMBOLS
        # train = 40 dates → 40×3=120 rows
        assert len(train_pos) == 40 * N_SYMBOLS

        # Apply purge
        train_pos_purged = _apply_purge(dates, train_pos, VAL_PURGE_GAP)

        # Purge should remove VAL_PURGE_GAP dates × N_SYMBOLS rows
        expected_removed = VAL_PURGE_GAP * N_SYMBOLS  # 5×3=15
        actual_removed = len(train_pos) - len(train_pos_purged)
        assert actual_removed == expected_removed, (
            f"Expected purge to remove {expected_removed} rows "
            f"({VAL_PURGE_GAP} dates × {N_SYMBOLS} symbols), "
            f"but removed {actual_removed}"
        )


class TestValPurgeWithSyntheticDates:
    """Bug 2: synthetic dates cause row-level purge instead of date-level."""

    @pytest.mark.xfail(
        reason="Bug 2: synthetic dates cause row-level purge instead of date-level — "
        "purge removes val_purge_gap rows instead of val_purge_gap × n_symbols rows",
        strict=True,
    )
    def test_val_purge_with_synthetic_dates_is_broken(self):
        """Synthetic dates (1 unique date per row) make purge per-row, not per-date.

        This test creates 150 rows that SHOULD represent 50 dates × 3 symbols,
        but wraps them with synthetic bdate_range dates (150 unique dates).
        The purge then only removes VAL_PURGE_GAP rows instead of
        VAL_PURGE_GAP × N_SYMBOLS rows.
        """
        # Synthetic dates: 150 unique dates for 150 rows
        dates = _make_synthetic_dates()
        assert dates.shape[0] == N_ROWS
        assert len(np.unique(dates)) == N_ROWS  # Every row is a unique "date"

        # Split — with 150 unique dates, val_fraction=0.2 → 30 val "dates" = 30 rows
        train_pos, val_pos = _split_train_val_by_date(dates, VAL_FRACTION)
        assert len(val_pos) == 30  # 0.2 × 150 = 30
        assert len(train_pos) == 120

        # Apply purge
        train_pos_purged = _apply_purge(dates, train_pos, VAL_PURGE_GAP)

        # With synthetic dates, purge removes exactly VAL_PURGE_GAP rows (5),
        # because each "date" is one row. The CORRECT behavior for a 50-date ×
        # 3-symbol panel would be to remove 5×3=15 rows.
        actual_removed = len(train_pos) - len(train_pos_purged)

        # This assertion demands the CORRECT behavior (15 rows removed).
        # It FAILS because synthetic dates cause only 5 rows to be removed.
        expected_correct = VAL_PURGE_GAP * N_SYMBOLS  # 15
        assert actual_removed == expected_correct, (
            f"Expected purge to remove {expected_correct} rows "
            f"({VAL_PURGE_GAP} dates × {N_SYMBOLS} symbols), "
            f"but with synthetic dates only removed {actual_removed} rows "
            f"(= val_purge_gap alone, proving Bug 2)"
        )
