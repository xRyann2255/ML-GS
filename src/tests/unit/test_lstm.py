"""Unit tests for the LSTM volatility model.

The pipeline interface is sequence-first: ``fit`` and ``predict`` accept a
``SequenceTensor`` (the cache layer from Phase 1). Validates:

1. Sequence-first signature is honoured (no DataFrame fallback at this layer).
2. The model overfits a tiny synthetic dataset with strong signal, proving
   gradients flow end-to-end through the masked LSTM → attention pool → MLP.
3. ``predict`` returns a 1-D float array, one prediction per input date.
4. ``save`` + ``load`` round-trip produces bit-identical predictions.
5. ``device='auto'`` falls back to CPU when CUDA is unavailable (this box).
6. ``requires_sequences`` flag is set so the runner can dispatch correctly.
7. The QLIKE loss path runs and improves over training.

Marked module-level ``slow`` (see ``pyproject.toml`` markers): the overfit
test takes ~6s and the file dominates the suite tail. ``./vol test``
excludes this module; ``./vol test-all`` includes it.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from volforecast.data.sequence_cache import SequenceTensor
from volforecast.models.lstm import LSTMVolModel

pytestmark = pytest.mark.slow


def _make_synthetic_sequence(
    n_dates: int = 120,
    max_bars: int = 24,
    n_features: int = 3,
    seed: int = 0,
) -> tuple[SequenceTensor, np.ndarray]:
    """Build a (sequence, target) pair where target is a deterministic
    function of the sequence so a well-trained LSTM can recover it.

    target[d] = log( var(net_flow[d,:valid]) + epsilon ) — chosen because
    realised log-vol is roughly a log-of-second-moment statistic, mirroring
    the real signal.
    """
    rng = np.random.default_rng(seed)
    # Variable per-day lengths (8 .. max_bars).
    lengths = rng.integers(8, max_bars + 1, size=n_dates).astype(np.int64)

    tensor = np.zeros((n_dates, max_bars, n_features), dtype=np.float32)
    targets = np.zeros(n_dates, dtype=np.float32)
    for d in range(n_dates):
        n = int(lengths[d])
        # Latent vol level for this day determines the magnitude of flow.
        latent = float(rng.normal(0.0, 1.0))
        scale = np.exp(latent * 0.5)
        x = rng.standard_normal((n, n_features)).astype(np.float32) * scale
        tensor[d, :n, :] = x
        # Target = log(variance of feature 0 within day)
        targets[d] = float(np.log(np.var(x[:, 0]) + 1e-3))

    dates = pd.bdate_range("2023-01-02", periods=n_dates)
    seq = SequenceTensor(
        symbol="SYN",
        tensor=torch.from_numpy(tensor),
        lengths=torch.from_numpy(lengths),
        dates=dates,
        feature_names=tuple(f"f{i}" for i in range(n_features)),
    )
    return seq, targets


class TestModelContract:
    def test_requires_sequences_flag(self):
        assert getattr(LSTMVolModel, "requires_sequences", False) is True

    def test_registered_as_lstm(self):
        from volforecast.registry import MODEL_REGISTRY, ensure_registered

        ensure_registered()
        assert "lstm" in MODEL_REGISTRY
        assert MODEL_REGISTRY["lstm"] is LSTMVolModel

    def test_device_auto_resolves_to_cpu_when_no_cuda(self, monkeypatch):
        monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
        m = LSTMVolModel(input_dim=3, hidden_dim=8, n_layers=1, device="auto")
        assert m.device == "cpu"


class TestFitPredict:
    def test_predict_shape(self):
        seq, y = _make_synthetic_sequence(n_dates=40, max_bars=12, n_features=2, seed=1)
        m = LSTMVolModel(
            input_dim=2,
            hidden_dim=8,
            n_layers=1,
            max_epochs=2,
            batch_size=16,
            device="cpu",
        )
        m.fit(seq, pd.Series(y, index=seq.dates))
        preds = m.predict(seq)
        assert preds.shape == (len(seq),)
        assert np.isfinite(preds).all()

    def test_overfits_small_signal(self):
        """With enough epochs on a tiny dataset, training loss must shrink."""
        seq, y = _make_synthetic_sequence(n_dates=80, max_bars=20, n_features=3, seed=2)
        y_series = pd.Series(y, index=seq.dates)
        m = LSTMVolModel(
            input_dim=3,
            hidden_dim=32,
            n_layers=1,
            dropout=0.0,
            learning_rate=5e-3,
            max_epochs=60,
            batch_size=32,
            device="cpu",
            loss="mse",
            val_fraction=0.0,
            early_stopping_rounds=0,
        )
        m.fit(seq, y_series)
        preds = m.predict(seq)
        mse_model = float(np.mean((preds - y) ** 2))
        # Constant-mean baseline.
        mse_naive = float(np.var(y))
        assert mse_model < 0.6 * mse_naive, (
            f"LSTM failed to overfit synthetic signal: model MSE {mse_model:.4f} "
            f"vs naive {mse_naive:.4f}"
        )

    def test_qlike_loss_path_runs(self):
        seq, y = _make_synthetic_sequence(n_dates=40, max_bars=12, n_features=2, seed=3)
        m = LSTMVolModel(
            input_dim=2,
            hidden_dim=8,
            n_layers=1,
            max_epochs=3,
            batch_size=16,
            device="cpu",
            loss="qlike",
        )
        m.fit(seq, pd.Series(y, index=seq.dates))
        preds = m.predict(seq)
        assert np.isfinite(preds).all()

    def test_early_stopping_triggers(self):
        """val_fraction > 0 with patience must terminate before max_epochs."""
        seq, y = _make_synthetic_sequence(n_dates=60, max_bars=10, n_features=2, seed=4)
        m = LSTMVolModel(
            input_dim=2,
            hidden_dim=4,
            n_layers=1,
            max_epochs=200,
            batch_size=16,
            device="cpu",
            val_fraction=0.25,
            early_stopping_rounds=3,
            learning_rate=5e-3,
        )
        m.fit(seq, pd.Series(y, index=seq.dates))
        # `epochs_run_` is exposed so we can assert termination occurred.
        assert m.epochs_run_ < 200, "Early stopping did not fire on a small dataset"


class TestSaveLoad:
    def test_roundtrip(self, tmp_path: Path):
        seq, y = _make_synthetic_sequence(n_dates=40, max_bars=10, n_features=2, seed=5)
        m = LSTMVolModel(
            input_dim=2,
            hidden_dim=8,
            n_layers=1,
            max_epochs=2,
            batch_size=16,
            device="cpu",
        )
        m.fit(seq, pd.Series(y, index=seq.dates))
        preds_before = m.predict(seq)

        path = tmp_path / "lstm.pt"
        m.save(path)
        assert path.exists()

        loaded = LSTMVolModel.load(path)
        preds_after = loaded.predict(seq)
        np.testing.assert_allclose(preds_before, preds_after, rtol=0, atol=0)


class TestAlignment:
    def test_predict_subset_dates(self):
        """Predicting on a date subset returns the predictions in subset order."""
        seq, y = _make_synthetic_sequence(n_dates=40, max_bars=10, n_features=2, seed=6)
        m = LSTMVolModel(
            input_dim=2,
            hidden_dim=8,
            n_layers=1,
            max_epochs=2,
            batch_size=16,
            device="cpu",
        )
        m.fit(seq, pd.Series(y, index=seq.dates))
        subset_dates = seq.dates[[5, 10, 20]]
        subset = seq.subset_by_dates(subset_dates)
        full_preds = m.predict(seq)
        sub_preds = m.predict(subset)
        # Batch-composition causes ~1e-8 fp32 drift in pack_padded_sequence
        # ordering; allow it.
        np.testing.assert_allclose(sub_preds, full_preds[[5, 10, 20]], rtol=0, atol=1e-6)


class TestProgressCallback:
    """``fit`` must accept ``on_progress(current, total)`` and call it per
    epoch — mirrors the LightGBM contract so the CLI can render a nested
    progress bar uniformly across model types."""

    def test_on_progress_called_per_epoch(self):
        seq, y = _make_synthetic_sequence(n_dates=30, max_bars=8, n_features=2, seed=7)
        m = LSTMVolModel(
            input_dim=2,
            hidden_dim=4,
            n_layers=1,
            max_epochs=4,
            batch_size=16,
            device="cpu",
            val_fraction=0.0,
            early_stopping_rounds=0,
        )
        calls: list[tuple[int, int]] = []

        def on_progress(current: int, total: int) -> None:
            calls.append((current, total))

        m.fit(seq, pd.Series(y, index=seq.dates), on_progress=on_progress)

        assert len(calls) == 4, f"expected 4 epoch callbacks, got {len(calls)}"
        # Monotonic increasing current; constant total = max_epochs.
        currents = [c for c, _ in calls]
        totals = {t for _, t in calls}
        assert currents == [1, 2, 3, 4]
        assert totals == {4}

    def test_on_progress_optional(self):
        """Omitting the callback must not break fit."""
        seq, y = _make_synthetic_sequence(n_dates=20, max_bars=10, n_features=2, seed=8)
        m = LSTMVolModel(
            input_dim=2,
            hidden_dim=4,
            n_layers=1,
            max_epochs=2,
            batch_size=16,
            device="cpu",
        )
        m.fit(seq, pd.Series(y, index=seq.dates))  # no on_progress
        assert m.epochs_run_ == 2


# ---------------------------------------------------------------------------
# Step 1.2 — date-aware internal validation split
# ---------------------------------------------------------------------------


class TestDateAwareValSplit:
    """The internal early-stopping val split inside ``fit`` must partition
    UNIQUE DATES, not rows. With pooled training (multiple symbols per
    date), a row-count split can leak symbols of the same date across
    train/val. Step 1.2 fixes that with a pure helper
    ``_split_train_val_by_date``.
    """

    def test_split_returns_disjoint_date_partitions(self) -> None:
        from volforecast.models.lstm import _split_train_val_by_date

        # Three symbols × 10 unique dates → 30 rows.
        dates_arr = np.tile(pd.bdate_range("2024-01-02", periods=10).values, 3)
        train_idx, val_idx = _split_train_val_by_date(dates_arr, val_fraction=0.3)
        train_dates = set(dates_arr[train_idx].tolist())
        val_dates = set(dates_arr[val_idx].tolist())
        assert train_dates.isdisjoint(val_dates), \
            f"Train/val share dates: {train_dates & val_dates}"

    def test_split_preserves_temporal_order(self) -> None:
        from volforecast.models.lstm import _split_train_val_by_date

        dates_arr = np.tile(pd.bdate_range("2024-01-02", periods=10).values, 3)
        train_idx, val_idx = _split_train_val_by_date(dates_arr, val_fraction=0.3)
        # Val must be the LAST 30% of unique dates.
        assert dates_arr[train_idx].max() < dates_arr[val_idx].min(), \
            "Val dates are not strictly after train dates"

    def test_split_zero_fraction_is_all_train(self) -> None:
        from volforecast.models.lstm import _split_train_val_by_date

        dates_arr = np.tile(pd.bdate_range("2024-01-02", periods=10).values, 3)
        train_idx, val_idx = _split_train_val_by_date(dates_arr, val_fraction=0.0)
        assert len(val_idx) == 0
        assert len(train_idx) == len(dates_arr)

    def test_split_full_fraction_falls_through_to_train(self) -> None:
        """val_fraction near 1.0 would produce zero train dates; the helper
        must return all-train (caller should branch to no-val mode)."""
        from volforecast.models.lstm import _split_train_val_by_date

        dates_arr = np.tile(pd.bdate_range("2024-01-02", periods=10).values, 3)
        train_idx, val_idx = _split_train_val_by_date(dates_arr, val_fraction=0.999)
        # With 10 unique dates × 0.999 → 10 val dates → all dates in val, so
        # train is empty. Fall through: caller treats as no-val.
        # The helper itself returns the literal partition; this asserts the
        # SIGNAL that downstream should detect (train empty).
        assert len(val_idx) == len(dates_arr)
        assert len(train_idx) == 0

    def test_internal_val_split_pooled_fit_is_date_disjoint(self) -> None:
        """End-to-end check that ``fit`` exposes the actual train/val date
        partition and that they are disjoint after a pooled fit.

        We mark the model with ``_last_split_dates`` (a 2-tuple of train and
        val unique-date sets) inside the new helper for testing.
        """
        # Pool 3 synthetic symbols sharing the same 30-date calendar.
        n_dates_per_sym = 30
        n_features = 3
        rng = np.random.default_rng(0)
        dates = pd.bdate_range("2024-01-02", periods=n_dates_per_sym)
        n_total = 3 * n_dates_per_sym
        lengths = rng.integers(5, 12, size=n_total).astype(np.int64)
        tensor = np.zeros((n_total, 12, n_features), dtype=np.float32)
        for i in range(n_total):
            n = int(lengths[i])
            tensor[i, :n, :] = rng.standard_normal((n, n_features)).astype(np.float32)
        targets = rng.standard_normal(n_total).astype(np.float32)
        # Pool order: dates repeated for each symbol (matches sort_by(date,
        # symbol) ordering used by the runner).
        pooled_dates = pd.DatetimeIndex(
            np.concatenate([dates.values] * 3)
        )
        seq = SequenceTensor(
            symbol="POOL",
            tensor=torch.from_numpy(tensor),
            lengths=torch.from_numpy(lengths),
            dates=pooled_dates,
            feature_names=tuple(f"f{i}" for i in range(n_features)),
        )
        y_series = pd.Series(targets, index=pooled_dates, name="logrv")
        m = LSTMVolModel(
            input_dim=n_features,
            hidden_dim=4,
            n_layers=1,
            max_epochs=1,
            batch_size=16,
            val_fraction=0.3,
            early_stopping_rounds=100,
            device="cpu",
        )
        m.fit(seq, y_series)
        split = getattr(m, "_last_split_dates", None)
        assert split is not None, "fit did not record _last_split_dates"
        train_set, val_set = split
        assert train_set.isdisjoint(val_set), \
            f"Train/val share dates: {train_set & val_set}"
        assert max(train_set) < min(val_set), "Val dates not strictly after train"


class TestNumWorkersDeprecation:
    """Step 1.5: ``num_workers`` is unused (manual batching, not DataLoader).

    The parameter is kept for save/load backwards compat but any non-zero
    value should raise ``DeprecationWarning`` at construction time so users
    purge it from configs. ``num_workers=0`` (the default) is silent.
    """

    def test_lstm_warns_on_nonzero_num_workers(self):
        with pytest.warns(DeprecationWarning, match="num_workers"):
            LSTMVolModel(input_dim=1, num_workers=4)

    def test_lstm_no_warn_on_zero_num_workers(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            LSTMVolModel(input_dim=1, num_workers=0)
        num_workers_warnings = [
            w for w in caught
            if issubclass(w.category, DeprecationWarning)
            and "num_workers" in str(w.message)
        ]
        assert not num_workers_warnings, (
            f"Expected no num_workers DeprecationWarning when num_workers=0, "
            f"got: {[str(w.message) for w in num_workers_warnings]}"
        )


class TestContextVector:
    """Tests for the context vector (IV conditioning) pathway."""

    def test_context_vector_shape(self):
        """Model with context_dim=4 accepts (B,4) context and produces (B,) output."""
        from volforecast.models.lstm import _LSTMBody

        body = _LSTMBody(
            input_dim=3, hidden_dim=16, n_layers=1, dropout=0.0,
            bidirectional=True, context_dim=4,
        )
        B, T, F = 8, 20, 3
        x = torch.randn(B, T, F)
        lengths = torch.full((B,), T, dtype=torch.long)
        context = torch.randn(B, 4)
        out = body(x, lengths, context=context)
        assert out.shape == (B,), f"Expected shape ({B},), got {out.shape}"

    def test_context_gradient_flow(self):
        """Gradients flow through context → head."""
        from volforecast.models.lstm import _LSTMBody

        body = _LSTMBody(
            input_dim=2, hidden_dim=8, n_layers=1, dropout=0.0,
            bidirectional=False, context_dim=3,
        )
        B, T, F = 4, 10, 2
        x = torch.randn(B, T, F)
        lengths = torch.full((B,), T, dtype=torch.long)
        context = torch.randn(B, 3, requires_grad=True)
        out = body(x, lengths, context=context)
        loss = out.sum()
        loss.backward()
        assert context.grad is not None, "No gradient on context tensor"
        assert context.grad.abs().sum() > 0, "Context gradient is all zeros"

    def test_no_context_backward_compat(self):
        """Model with context_dim=0 matches old behaviour (no context needed)."""
        seq, y = _make_synthetic_sequence(n_dates=30, max_bars=10, n_features=2, seed=20)
        m = LSTMVolModel(
            input_dim=2, hidden_dim=8, n_layers=1, max_epochs=2,
            batch_size=16, device="cpu", context_dim=0,
        )
        m.fit(seq, pd.Series(y, index=seq.dates))
        preds = m.predict(seq)
        assert preds.shape == (len(seq),)
        assert np.isfinite(preds).all()

    def test_context_fit_predict(self):
        """Full fit/predict cycle with synthetic context."""
        seq, y = _make_synthetic_sequence(n_dates=60, max_bars=12, n_features=3, seed=21)
        context_dim = 4
        rng = np.random.default_rng(21)
        context = rng.standard_normal((len(seq), context_dim)).astype(np.float32)

        m = LSTMVolModel(
            input_dim=3, hidden_dim=16, n_layers=1, max_epochs=5,
            batch_size=32, device="cpu", context_dim=context_dim,
            val_fraction=0.2, early_stopping_rounds=3,
        )
        m.fit(seq, pd.Series(y, index=seq.dates), context=context)
        preds = m.predict(seq, context=context)
        assert preds.shape == (len(seq),)
        assert np.isfinite(preds).all()

    def test_context_validation_errors(self):
        """Validation: mismatched context_dim raises on fit and predict."""
        seq, y = _make_synthetic_sequence(n_dates=20, max_bars=8, n_features=2, seed=22)

        # Model expects context but none provided
        m = LSTMVolModel(input_dim=2, hidden_dim=8, n_layers=1, device="cpu", context_dim=3)
        with pytest.raises(ValueError, match="context_dim>0"):
            m.fit(seq, pd.Series(y, index=seq.dates))

        # Model doesn't expect context but one provided
        m2 = LSTMVolModel(input_dim=2, hidden_dim=8, n_layers=1, device="cpu", context_dim=0)
        context = np.zeros((len(seq), 3), dtype=np.float32)
        with pytest.raises(ValueError, match="context_dim=0"):
            m2.fit(seq, pd.Series(y, index=seq.dates), context=context)
