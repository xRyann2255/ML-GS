"""Tests for temporal_holdout_split utility."""

from __future__ import annotations

from volforecast.models._base import temporal_holdout_split


class TestTemporalHoldoutSplit:
    """Unit tests for the shared temporal holdout split function."""

    def test_returns_indices_for_normal_case(self):
        # 1000 rows, 20% holdout, 10 gap → train_end=800, holdout_start=810
        result = temporal_holdout_split(n=1000, fraction=0.20, purge_gap=10)
        assert result is not None
        train_end, holdout_start = result
        assert train_end == 800
        assert holdout_start == 810

    def test_returns_none_when_insufficient_data(self):
        # 100 rows, 15% holdout → train_end=85, holdout_start=95
        # Only 5 rows left (< min_holdout=20) → None
        result = temporal_holdout_split(n=100, fraction=0.15, purge_gap=10)
        assert result is None

    def test_purge_gap_respected(self):
        # Verify gap between train end and holdout start
        result = temporal_holdout_split(n=500, fraction=0.20, purge_gap=25)
        assert result is not None
        train_end, holdout_start = result
        assert holdout_start - train_end == 25

    def test_edge_exactly_min_holdout(self):
        # n=100, fraction=0.5, gap=10 → train_end=50, holdout_start=60
        # 40 rows in holdout (100-60=40), min_holdout=40 → boundary case
        # holdout_start(60) >= n-min_holdout(60) → None (need strictly more)
        result = temporal_holdout_split(n=100, fraction=0.5, purge_gap=10, min_holdout=40)
        assert result is None

        # One more row of data makes it work
        result = temporal_holdout_split(n=101, fraction=0.5, purge_gap=10, min_holdout=40)
        assert result is not None

    def test_edge_one_short_of_min_holdout(self):
        # n=100, fraction=0.5, gap=10 → holdout_start=60, 40 rows left
        # min_holdout=41 → fails (holdout_start=60 >= 100-41=59)
        result = temporal_holdout_split(n=100, fraction=0.5, purge_gap=10, min_holdout=41)
        assert result is None

    def test_zero_purge_gap(self):
        result = temporal_holdout_split(n=200, fraction=0.20, purge_gap=0)
        assert result is not None
        train_end, holdout_start = result
        assert train_end == holdout_start  # no gap

    def test_custom_min_holdout(self):
        # 200 rows, 10% holdout, gap=5 → train_end=180, holdout_start=185
        # 15 rows left, min_holdout=50 → None
        result = temporal_holdout_split(n=200, fraction=0.10, purge_gap=5, min_holdout=50)
        assert result is None

        # Same but min_holdout=10 → succeeds
        result = temporal_holdout_split(n=200, fraction=0.10, purge_gap=5, min_holdout=10)
        assert result is not None
