"""Unit tests for LSTM residual learning (trial-052 contract).

The LSTM model must accept an optional ``base_preds`` kwarg on ``fit`` and
``predict`` so it can be trained as a residual learner on top of a tabular
base forecast (HAR-IV at h=22, LightGBM CHAMPION at h=1/h=5).

Contract under test
-------------------
1. ``fit(seq, y, base_preds=b)``: model trains on ``y - b`` internally.
2. ``predict(seq, base_preds=b)``: model returns ``lstm_residual(seq) + b``.
3. A model fit WITH base_preds raises if ``predict`` is called without them.
4. A model fit WITHOUT base_preds raises if ``predict`` is called with them.
5. ``base_preds`` length must equal ``len(seq.dates)``; mismatch raises.
6. NaN handling: when ``y`` has NaN at some dates, ``base_preds`` is sliced
   with the SAME finite-mask so train alignment is preserved.
7. ``save``/``load`` round-trips the ``was_fit_with_base_preds`` flag and
   predictions remain bit-identical when given the same ``base_preds`` at
   predict time.
8. The residual path learns: when the LSTM is fit on a residual that has a
   recoverable signal, the final ``preds`` are CLOSER to ``y`` than the base
   alone — proves gradient flow through the residual path.

These tests will FAIL on current code: ``LSTMVolModel.fit`` does not accept
``base_preds`` and ``predict`` does not add a base back. That is intentional —
TDD step 1.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from volforecast.data.sequence_cache import SequenceTensor
from volforecast.models.lstm import LSTMVolModel

pytestmark = pytest.mark.slow


# ---------------------------------------------------------------------------
# Synthetic generator: target decomposes cleanly into base + residual
# ---------------------------------------------------------------------------


def _make_residual_dataset(
    n_dates: int = 120,
    max_bars: int = 24,
    n_features: int = 3,
    seed: int = 0,
) -> tuple[SequenceTensor, np.ndarray, np.ndarray]:
    """Construct (seq, y, base_preds) where::

        y[d] = base_preds[d] + residual[d]
        residual[d] = log(var(seq.tensor[d, :valid, 0]) + eps)

    The residual is a deterministic function of the sequence (same shape as
    ``test_lstm._make_synthetic_sequence``'s target). The base is a smooth
    autoregressive series that the LSTM has NO way to recover from the bars
    alone — so any improvement over base-only must come from the residual
    path.
    """
    rng = np.random.default_rng(seed)
    lengths = rng.integers(8, max_bars + 1, size=n_dates).astype(np.int64)

    tensor = np.zeros((n_dates, max_bars, n_features), dtype=np.float32)
    residual = np.zeros(n_dates, dtype=np.float32)
    for d in range(n_dates):
        n = int(lengths[d])
        latent = float(rng.normal(0.0, 1.0))
        scale = np.exp(latent * 0.5)
        x = rng.standard_normal((n, n_features)).astype(np.float32) * scale
        tensor[d, :n, :] = x
        residual[d] = float(np.log(np.var(x[:, 0]) + 1e-3))

    # Base: smooth AR(1) noise centred at -5 (log-RV-ish level), unrelated to
    # the per-day sequence content.
    base = np.zeros(n_dates, dtype=np.float32)
    base[0] = -5.0
    for t in range(1, n_dates):
        base[t] = 0.95 * base[t - 1] + 0.05 * (-5.0) + float(rng.normal(0.0, 0.1))

    y = base + residual

    dates = pd.bdate_range("2023-01-02", periods=n_dates)
    seq = SequenceTensor(
        symbol="SYN",
        tensor=torch.from_numpy(tensor),
        lengths=torch.from_numpy(lengths),
        dates=dates,
        feature_names=tuple(f"f{i}" for i in range(n_features)),
    )
    return seq, y.astype(np.float32), base.astype(np.float32)


def _fresh_model(**overrides) -> LSTMVolModel:
    """Default tiny CPU LSTM for unit tests; overrides win."""
    params = dict(
        input_dim=3,
        hidden_dim=16,
        n_layers=1,
        dropout=0.0,
        max_epochs=3,
        batch_size=16,
        device="cpu",
        loss="mse",
        val_fraction=0.0,
        early_stopping_rounds=0,
        seed=0,
    )
    params.update(overrides)
    return LSTMVolModel(**params)


# ---------------------------------------------------------------------------
# 1. fit accepts base_preds and trains on residual
# ---------------------------------------------------------------------------


class TestBasePredsContract:
    def test_fit_accepts_base_preds_kwarg(self):
        seq, y, base = _make_residual_dataset(n_dates=40, seed=1)
        m = _fresh_model()
        # Must not raise.
        m.fit(seq, pd.Series(y, index=seq.dates), base_preds=base)
        assert getattr(m, "was_fit_with_base_preds", False) is True

    def test_predict_accepts_base_preds_kwarg(self):
        seq, y, base = _make_residual_dataset(n_dates=40, seed=2)
        m = _fresh_model()
        m.fit(seq, pd.Series(y, index=seq.dates), base_preds=base)
        preds = m.predict(seq, base_preds=base)
        assert preds.shape == (len(seq),)
        assert np.isfinite(preds).all()

    def test_fit_without_base_preds_leaves_flag_false(self):
        seq, y, _ = _make_residual_dataset(n_dates=40, seed=3)
        m = _fresh_model()
        m.fit(seq, pd.Series(y, index=seq.dates))
        assert getattr(m, "was_fit_with_base_preds", False) is False


# ---------------------------------------------------------------------------
# 2. Residual addition: predict returns lstm_residual + base
# ---------------------------------------------------------------------------


class TestResidualAddition:
    def test_predict_adds_base_back(self):
        """Two identical models, one fit with base and one without — when
        predicting on the same sequence, the WITH-base model's output should
        equal the WITHOUT-base model's output PLUS the base."""
        seq, y, base = _make_residual_dataset(n_dates=60, seed=4)
        y_series = pd.Series(y, index=seq.dates)

        # Reference: train on y - base directly (no kwarg), predict, add back.
        m_ref = _fresh_model(seed=42)
        m_ref.fit(seq, pd.Series(y - base, index=seq.dates))
        preds_ref = m_ref.predict(seq) + base

        # Under test: pass base_preds through the new API.
        m_new = _fresh_model(seed=42)
        m_new.fit(seq, y_series, base_preds=base)
        preds_new = m_new.predict(seq, base_preds=base)

        # Same seed, same data → bit-identical predictions.
        np.testing.assert_allclose(preds_new, preds_ref, rtol=0, atol=1e-6)

    def test_residual_path_learns(self):
        """When base perfectly explains the slow component and the LSTM can
        recover the residual from the sequence, MSE(preds, y) must be much
        smaller than MSE(base, y)."""
        seq, y, base = _make_residual_dataset(n_dates=120, max_bars=20, seed=5)
        m = _fresh_model(
            hidden_dim=32, max_epochs=60, learning_rate=5e-3, seed=7
        )
        m.fit(seq, pd.Series(y, index=seq.dates), base_preds=base)
        preds = m.predict(seq, base_preds=base)

        mse_hybrid = float(np.mean((preds - y) ** 2))
        mse_base_only = float(np.mean((base - y) ** 2))
        assert mse_hybrid < 0.5 * mse_base_only, (
            f"residual path failed to add value: hybrid MSE {mse_hybrid:.4f} "
            f"vs base-only MSE {mse_base_only:.4f}"
        )


# ---------------------------------------------------------------------------
# 3. Fail-loud on inconsistent use
# ---------------------------------------------------------------------------


class TestFailLoud:
    def test_predict_without_base_after_fit_with_base_raises(self):
        seq, y, base = _make_residual_dataset(n_dates=40, seed=6)
        m = _fresh_model()
        m.fit(seq, pd.Series(y, index=seq.dates), base_preds=base)
        with pytest.raises(ValueError, match="base_preds"):
            m.predict(seq)

    def test_predict_with_base_after_fit_without_base_raises(self):
        seq, y, base = _make_residual_dataset(n_dates=40, seed=7)
        m = _fresh_model()
        m.fit(seq, pd.Series(y, index=seq.dates))  # no base
        with pytest.raises(ValueError, match="base_preds"):
            m.predict(seq, base_preds=base)

    def test_fit_base_preds_length_mismatch_raises(self):
        seq, y, base = _make_residual_dataset(n_dates=40, seed=8)
        m = _fresh_model()
        wrong = base[:30]  # too short
        with pytest.raises(ValueError, match="base_preds"):
            m.fit(seq, pd.Series(y, index=seq.dates), base_preds=wrong)

    def test_predict_base_preds_length_mismatch_raises(self):
        seq, y, base = _make_residual_dataset(n_dates=40, seed=9)
        m = _fresh_model()
        m.fit(seq, pd.Series(y, index=seq.dates), base_preds=base)
        # Predict on a subset of dates — base_preds must be subsetted too.
        subset_dates = seq.dates[[0, 5, 10]]
        sub_seq = seq.subset_by_dates(subset_dates)
        with pytest.raises(ValueError, match="base_preds"):
            # Passing full-length base for a length-3 subset must fail.
            m.predict(sub_seq, base_preds=base)


# ---------------------------------------------------------------------------
# 4. NaN target handling: base_preds must follow the same finite-mask
# ---------------------------------------------------------------------------


class TestNanAlignment:
    def test_nan_target_drops_matching_base_rows(self):
        """When the target has NaN at some dates, the LSTM internally drops
        those rows. ``base_preds`` MUST be sliced with the same mask so the
        residual ``y - base`` is well-defined on the kept rows.

        Behavioural assertion: fitting succeeds and produces finite preds.
        Crash-free is the floor; a regression would surface as a
        length-mismatch RuntimeError deep in pack_padded_sequence.
        """
        seq, y, base = _make_residual_dataset(n_dates=60, seed=10)
        y_nan = y.copy()
        y_nan[5] = np.nan
        y_nan[17] = np.nan
        y_nan[44] = np.nan

        m = _fresh_model(max_epochs=2)
        m.fit(seq, pd.Series(y_nan, index=seq.dates), base_preds=base)
        preds = m.predict(seq, base_preds=base)
        assert preds.shape == (len(seq),)
        assert np.isfinite(preds).all()


# ---------------------------------------------------------------------------
# 5. Save / load preserves residual contract
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_save_load_preserves_residual_flag_and_preds(self, tmp_path: Path):
        seq, y, base = _make_residual_dataset(n_dates=40, seed=11)
        m = _fresh_model()
        m.fit(seq, pd.Series(y, index=seq.dates), base_preds=base)
        preds_before = m.predict(seq, base_preds=base)

        path = tmp_path / "lstm_residual.pt"
        m.save(path)
        loaded = LSTMVolModel.load(path)
        assert getattr(loaded, "was_fit_with_base_preds", False) is True

        # Same base_preds → identical predictions across save/load.
        preds_after = loaded.predict(seq, base_preds=base)
        np.testing.assert_allclose(preds_after, preds_before, rtol=0, atol=0)

        # Loaded model still fails loud without base_preds.
        with pytest.raises(ValueError, match="base_preds"):
            loaded.predict(seq)
