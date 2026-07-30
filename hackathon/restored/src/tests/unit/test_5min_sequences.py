"""Unit tests for _build_5min_sequences_df (TDD — function does not exist yet).

Tests define the contract for aggregating 10-second bars into 5-minute bars
with 12 enriched features. All tests use synthetic deterministic data so
expected values can be computed by hand.

Expected initial state: all tests FAIL with ImportError until the function
is implemented in volforecast.data.micro.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest
import torch

from volforecast.data.micro import _build_5min_sequences_df
from volforecast.data.sequence_cache import SequenceTensor
from volforecast.models.lstm import LSTMVolModel

# ε used in the production function for zero-division guards
EPS = 1e-10

EXPECTED_COLUMNS = [
    "date",
    "bar_idx",
    "log_ret",
    "abs_ret",
    "vol_share",
    "buy_ratio",
    "order_flow_imbalance",
    "rolling_vpin",
    "cum_rv",
    "session_frac",
    "price_accel",
    "log_n_trades",
    "intrabar_rv",
    "volume_surprise",
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_synthetic_10s_bars(
    n_bars: int,
    buy_vol: float = 100.0,
    sell_vol: float = 50.0,
    vwap_start: float = 100.0,
    vwap_step: float = 0.01,
    n_trades: int = 10,
) -> pd.DataFrame:
    """Return a DataFrame of synthetic 10-second bars.

    Columns: buy_vol, sell_vol, vwap, n_trades.
    VWAP walks linearly from *vwap_start* by *vwap_step* per bar.
    """
    return pd.DataFrame(
        {
            "buy_vol": np.full(n_bars, buy_vol, dtype=np.float64),
            "sell_vol": np.full(n_bars, sell_vol, dtype=np.float64),
            "vwap": vwap_start + np.arange(n_bars) * vwap_step,
            "n_trades": np.full(n_bars, n_trades, dtype=np.int64),
        }
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBasicAggregation:
    """90 synthetic 10s bars (3 × 30) → exactly 3 five-minute bars."""

    def test_basic_aggregation(self):
        day = date(2024, 1, 2)
        bars = _make_synthetic_10s_bars(90)
        result = _build_5min_sequences_df({day: bars})

        assert len(result) == 3
        assert (result["date"] == day).all()
        assert list(result["bar_idx"]) == [0, 1, 2]


class TestRemainderBars:
    """100 bars (3 × 30 + 10 remainder) → 4 five-minute bars."""

    def test_remainder_bars(self):
        day = date(2024, 1, 2)
        bars = _make_synthetic_10s_bars(100)
        result = _build_5min_sequences_df({day: bars})

        assert len(result) == 4
        assert list(result["bar_idx"]) == [0, 1, 2, 3]


class TestLogRetFormula:
    """log_ret = log(last_vwap / first_vwap) for each 5-min bar."""

    def test_log_ret_formula(self):
        day = date(2024, 1, 2)
        # 30 bars: vwap goes 100.0, 100.01, ..., 100.29
        bars = _make_synthetic_10s_bars(30, vwap_start=100.0, vwap_step=0.01)
        result = _build_5min_sequences_df({day: bars})

        assert len(result) == 1
        first_vwap = 100.0
        last_vwap = 100.0 + 29 * 0.01  # 100.29
        expected = np.log(last_vwap / first_vwap)
        assert result["log_ret"].iloc[0] == pytest.approx(expected, rel=1e-9)


class TestAbsRetFormula:
    """abs_ret = |log_ret|."""

    def test_abs_ret_formula(self):
        day = date(2024, 1, 2)
        # Use decreasing VWAP so log_ret is negative
        bars = _make_synthetic_10s_bars(30, vwap_start=100.0, vwap_step=-0.01)
        result = _build_5min_sequences_df({day: bars})

        log_ret = result["log_ret"].iloc[0]
        assert log_ret < 0, "negative log_ret expected for decreasing vwap"
        assert result["abs_ret"].iloc[0] == pytest.approx(abs(log_ret), rel=1e-12)


class TestBuyRatioFormula:
    """buy_ratio = sum(buy_vol) / (sum(buy_vol) + sum(sell_vol) + ε)."""

    def test_buy_ratio_formula(self):
        day = date(2024, 1, 2)
        # 30 bars, buy_vol=100, sell_vol=50 each
        bars = _make_synthetic_10s_bars(30, buy_vol=100.0, sell_vol=50.0)
        result = _build_5min_sequences_df({day: bars})

        total_buy = 30 * 100.0
        total_sell = 30 * 50.0
        expected = total_buy / (total_buy + total_sell + EPS)
        assert result["buy_ratio"].iloc[0] == pytest.approx(expected, rel=1e-9)


class TestIntrabarRV:
    """intrabar_rv = sum of (10s log_ret²) within the 5-min bar.

    This is the sum of squared log-returns of the *10-second* bars,
    NOT the square of the 5-minute log_ret.
    """

    def test_intrabar_rv(self):
        day = date(2024, 1, 2)
        # 30 bars with known vwap sequence
        vwap_start = 100.0
        vwap_step = 0.05
        bars = _make_synthetic_10s_bars(30, vwap_start=vwap_start, vwap_step=vwap_step)
        result = _build_5min_sequences_df({day: bars})

        # Compute expected: sum of (log(vwap[i]/vwap[i-1]))² for i=1..29
        vwaps = vwap_start + np.arange(30) * vwap_step
        log_rets_10s = np.log(vwaps[1:] / vwaps[:-1])
        expected_rv = np.sum(log_rets_10s**2)
        assert result["intrabar_rv"].iloc[0] == pytest.approx(expected_rv, rel=1e-9)


class TestCumRVMonotonic:
    """cum_rv is monotonically non-decreasing within a day."""

    def test_cum_rv_monotonic(self):
        day = date(2024, 1, 2)
        bars = _make_synthetic_10s_bars(90, vwap_step=0.02)
        result = _build_5min_sequences_df({day: bars})

        cum_rv = result["cum_rv"].values
        assert len(cum_rv) == 3
        assert all(cum_rv[i] <= cum_rv[i + 1] for i in range(len(cum_rv) - 1))


class TestSessionFracRange:
    """session_frac ∈ [0, 1] and last bar's session_frac ≈ 1.0."""

    def test_session_frac_range(self):
        day = date(2024, 1, 2)
        bars = _make_synthetic_10s_bars(90)
        result = _build_5min_sequences_df({day: bars})

        sf = result["session_frac"].values
        assert sf.min() >= 0.0
        assert sf.max() <= 1.0
        # First bar should be 0.0
        assert sf[0] == pytest.approx(0.0)
        # Last bar should be 1.0
        assert sf[-1] == pytest.approx(1.0)


class TestVolumeSurpriseNoNaN:
    """volume_surprise has no NaN — first bar uses expanding mean."""

    def test_volume_surprise_no_nan(self):
        day = date(2024, 1, 2)
        bars = _make_synthetic_10s_bars(90)
        result = _build_5min_sequences_df({day: bars})

        assert not result["volume_surprise"].isna().any(), "volume_surprise contains NaN"


class TestEmptyDay:
    """Empty day → 0 rows in output."""

    def test_empty_day(self):
        day = date(2024, 1, 2)
        empty_bars = pd.DataFrame(columns=["buy_vol", "sell_vol", "vwap", "n_trades"])
        result = _build_5min_sequences_df({day: empty_bars})

        assert len(result) == 0


class TestSingleBarDay:
    """Single 10s bar → 1 five-minute bar with 1 sub-bar."""

    def test_single_bar_day(self):
        day = date(2024, 1, 2)
        bars = _make_synthetic_10s_bars(1)
        result = _build_5min_sequences_df({day: bars})

        assert len(result) == 1
        # With a single bar, log_ret should be 0 (first == last vwap)
        assert result["log_ret"].iloc[0] == pytest.approx(0.0)
        # intrabar_rv should be 0 (no consecutive pairs)
        assert result["intrabar_rv"].iloc[0] == pytest.approx(0.0)
        # session_frac: single bar → 0/(1-1) is degenerate; accept 0.0 or 1.0
        sf = result["session_frac"].iloc[0]
        assert sf == pytest.approx(0.0) or sf == pytest.approx(1.0)


class TestOutputSchema:
    """Output DataFrame has exactly the expected column set."""

    def test_output_schema(self):
        day = date(2024, 1, 2)
        bars = _make_synthetic_10s_bars(30)
        result = _build_5min_sequences_df({day: bars})

        assert list(result.columns) == EXPECTED_COLUMNS


class TestOrderFlowImbalance:
    """OFI = (buy - sell) / (buy + sell + ε) with known values."""

    def test_order_flow_imbalance(self):
        day = date(2024, 1, 2)
        bars = _make_synthetic_10s_bars(30, buy_vol=200.0, sell_vol=100.0)
        result = _build_5min_sequences_df({day: bars})

        total_buy = 30 * 200.0
        total_sell = 30 * 100.0
        expected = (total_buy - total_sell) / (total_buy + total_sell + EPS)
        assert result["order_flow_imbalance"].iloc[0] == pytest.approx(expected, rel=1e-9)

    def test_ofi_balanced(self):
        """Equal buy and sell → OFI ≈ 0."""
        day = date(2024, 1, 2)
        bars = _make_synthetic_10s_bars(30, buy_vol=100.0, sell_vol=100.0)
        result = _build_5min_sequences_df({day: bars})

        assert result["order_flow_imbalance"].iloc[0] == pytest.approx(0.0, abs=1e-8)


class TestMultiDay:
    """Multiple days produce correct separate sequences."""

    def test_multi_day(self):
        day1 = date(2024, 1, 2)
        day2 = date(2024, 1, 3)
        bars1 = _make_synthetic_10s_bars(60)  # 2 five-min bars
        bars2 = _make_synthetic_10s_bars(30)  # 1 five-min bar

        result = _build_5min_sequences_df({day1: bars1, day2: bars2})

        assert len(result) == 3
        assert (result[result["date"] == day1]["bar_idx"].values == [0, 1]).all()
        assert (result[result["date"] == day2]["bar_idx"].values == [0]).all()

    def test_multi_day_independent_cum_rv(self):
        """cum_rv resets each day (not accumulated across days)."""
        day1 = date(2024, 1, 2)
        day2 = date(2024, 1, 3)
        bars1 = _make_synthetic_10s_bars(60, vwap_step=0.02)
        bars2 = _make_synthetic_10s_bars(60, vwap_step=0.02)

        result = _build_5min_sequences_df({day1: bars1, day2: bars2})

        rv_day1 = result[result["date"] == day1]["cum_rv"].values
        rv_day2 = result[result["date"] == day2]["cum_rv"].values
        # Both days have identical bars → identical cum_rv sequences
        np.testing.assert_allclose(rv_day1, rv_day2, rtol=1e-9)


# ---------------------------------------------------------------------------
# Integration tests — LSTM with 78 × 12 tensor
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestLSTM5MinIntegration:
    """Verify the LSTM accepts 78-bar × 12-feature tensors."""

    @staticmethod
    def _make_5min_synthetic(
        n_dates: int = 120,
        max_bars: int = 78,
        n_features: int = 12,
        seed: int = 42,
    ) -> tuple[SequenceTensor, np.ndarray]:
        """Build synthetic (sequence, target) pair mimicking 5-min enriched data."""
        rng = np.random.default_rng(seed)
        lengths = rng.integers(40, max_bars + 1, size=n_dates).astype(np.int64)

        tensor = np.zeros((n_dates, max_bars, n_features), dtype=np.float32)
        targets = np.zeros(n_dates, dtype=np.float32)
        for d in range(n_dates):
            n = int(lengths[d])
            latent = float(rng.normal(0.0, 1.0))
            scale = np.exp(latent * 0.5)
            x = rng.standard_normal((n, n_features)).astype(np.float32) * scale
            tensor[d, :n, :] = x
            targets[d] = float(np.log(np.var(x[:, 0]) + 1e-3))

        dates = pd.bdate_range("2023-01-02", periods=n_dates)
        seq = SequenceTensor(
            symbol="SYN5M",
            tensor=torch.from_numpy(tensor),
            lengths=torch.from_numpy(lengths),
            dates=dates,
            feature_names=tuple(f"f{i}" for i in range(n_features)),
        )
        return seq, targets

    def test_lstm_instantiation(self):
        """LSTMVolModel with input_dim=12 instantiates without error."""
        model = LSTMVolModel(
            input_dim=12, hidden_dim=64, n_layers=2,
            loss="qlike", pool_mode="attention", head_mode="mlp",
        )
        assert model is not None

    def test_lstm_fit_5min(self):
        """fit() on 78×12 synthetic data completes without error."""
        seq, y = self._make_5min_synthetic(n_dates=80, max_bars=78, n_features=12, seed=42)
        model = LSTMVolModel(
            input_dim=12, hidden_dim=64, n_layers=2,
            loss="qlike", pool_mode="attention", head_mode="mlp",
            max_epochs=5, batch_size=32, learning_rate=1e-3,
        )
        model.fit(seq, y)

    def test_lstm_predict_shape(self):
        """predict() returns array of length n_dates."""
        seq, y = self._make_5min_synthetic(n_dates=60, max_bars=78, n_features=12, seed=43)
        model = LSTMVolModel(
            input_dim=12, hidden_dim=64, n_layers=2,
            loss="qlike", pool_mode="attention", head_mode="mlp",
            max_epochs=3, batch_size=32,
        )
        model.fit(seq, y)
        preds = model.predict(seq)
        assert isinstance(preds, np.ndarray)
        assert preds.shape == (60,)

    def test_lstm_no_nan_loss(self):
        """Training for 3+ epochs produces no NaN loss (gradient flow works)."""
        seq, y = self._make_5min_synthetic(n_dates=80, max_bars=78, n_features=12, seed=44)
        model = LSTMVolModel(
            input_dim=12, hidden_dim=64, n_layers=2,
            loss="qlike", pool_mode="attention", head_mode="mlp",
            max_epochs=5, batch_size=32,
        )
        model.fit(seq, y)
        preds = model.predict(seq)
        assert not np.any(np.isnan(preds)), "NaN predictions indicate training divergence"

    def test_lstm_loss_decreases(self):
        """Train loss decreases between epoch 1 and final epoch (learning signal)."""
        seq, y = self._make_5min_synthetic(n_dates=120, max_bars=78, n_features=12, seed=45)
        model = LSTMVolModel(
            input_dim=12, hidden_dim=64, n_layers=2,
            loss="qlike", pool_mode="attention", head_mode="mlp",
            max_epochs=10, batch_size=32, val_fraction=0.0,
            early_stopping_rounds=0,
        )
        model.fit(seq, y)

        history = model.history_
        assert len(history) >= 2, "Need at least 2 epochs to check loss decrease"
        first_loss = history[0]["train_loss"]
        last_loss = history[-1]["train_loss"]
        assert last_loss < first_loss, (
            f"Loss should decrease: first={first_loss}, last={last_loss}"
        )
