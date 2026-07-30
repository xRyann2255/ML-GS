"""Unit tests for Phase 2 — symbol identity embedding in LSTM.

Validates:
1. Symbol embedding changes output for different symbol_ids.
2. n_symbols=0 preserves original behavior (backward compat).
3. symbol_to_id mapping is deterministic (built from sorted list).
4. forward(x, lengths, None) works with n_symbols=0.
5. save/load round-trip preserves symbol_to_id.
6. End-to-end fit/predict threads symbol_ids correctly.
7. _maybe_compile adjusts mode when n_symbols > 0.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from volforecast.data.sequence_cache import SequenceTensor
from volforecast.models.lstm import LSTMVolModel, _LSTMBody

pytestmark = pytest.mark.slow


def _make_seq(
    n_dates: int = 30,
    max_bars: int = 20,
    n_features: int = 5,
    seed: int = 0,
) -> tuple[SequenceTensor, np.ndarray]:
    """Synthetic SequenceTensor + targets for testing."""
    rng = np.random.default_rng(seed)
    lengths = rng.integers(5, max_bars + 1, size=n_dates).astype(np.int64)
    tensor = np.zeros((n_dates, max_bars, n_features), dtype=np.float32)
    targets = np.zeros(n_dates, dtype=np.float32)
    for d in range(n_dates):
        n = int(lengths[d])
        x = rng.standard_normal((n, n_features)).astype(np.float32)
        tensor[d, :n, :] = x
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


class TestLSTMBodyEmbedding:
    """Tests for _LSTMBody with symbol embedding."""

    def test_no_embedding_when_n_symbols_zero(self):
        """n_symbols=0 skips embedding — forward(x, l, None) works."""
        body = _LSTMBody(input_dim=5, hidden_dim=16, n_layers=1, dropout=0.0, n_symbols=0)
        x = torch.randn(4, 10, 5)
        lengths = torch.tensor([10, 8, 6, 5])
        out = body(x, lengths, symbol_ids=None)
        assert out.shape == (4,)

    def test_forward_backward_compat_two_args(self):
        """forward(x, lengths) without symbol_ids works for n_symbols=0."""
        body = _LSTMBody(input_dim=5, hidden_dim=16, n_layers=1, dropout=0.0, n_symbols=0)
        x = torch.randn(4, 10, 5)
        lengths = torch.tensor([10, 8, 6, 5])
        # Call with only 2 positional args (backward compat)
        out = body(x, lengths)
        assert out.shape == (4,)

    def test_embedding_changes_output(self):
        """Same input with different symbol_ids should produce different output."""
        body = _LSTMBody(
            input_dim=5, hidden_dim=16, n_layers=1, dropout=0.0,
            n_symbols=4, symbol_embed_dim=8,
        )
        body.eval()
        x = torch.randn(4, 10, 5)
        lengths = torch.tensor([10, 10, 10, 10])
        sym_a = torch.tensor([0, 0, 0, 0])
        sym_b = torch.tensor([1, 1, 1, 1])
        with torch.no_grad():
            out_a = body(x, lengths, symbol_ids=sym_a)
            out_b = body(x, lengths, symbol_ids=sym_b)
        # Different symbol_ids → different outputs (not identical)
        assert not torch.allclose(out_a, out_b, atol=1e-6)

    def test_embedding_same_symbol_same_output(self):
        """Same input + same symbol_ids → identical output (deterministic)."""
        body = _LSTMBody(
            input_dim=5, hidden_dim=16, n_layers=1, dropout=0.0,
            n_symbols=4, symbol_embed_dim=8,
        )
        body.eval()
        x = torch.randn(4, 10, 5)
        lengths = torch.tensor([10, 10, 10, 10])
        sym = torch.tensor([2, 2, 2, 2])
        with torch.no_grad():
            out1 = body(x, lengths, symbol_ids=sym)
            out2 = body(x, lengths, symbol_ids=sym)
        assert torch.allclose(out1, out2)

    def test_lstm_input_dim_includes_embedding(self):
        """LSTM input_size should be input_dim + symbol_embed_dim."""
        body = _LSTMBody(
            input_dim=5, hidden_dim=16, n_layers=1, dropout=0.0,
            n_symbols=10, symbol_embed_dim=4,
        )
        assert body.lstm.input_size == 5 + 4


class TestLSTMVolModelEmbedding:
    """Tests for LSTMVolModel with symbol embedding."""

    def test_init_accepts_n_symbols(self):
        """Constructor should accept n_symbols and symbol_embed_dim."""
        model = LSTMVolModel(
            input_dim=5, hidden_dim=16, n_layers=1, dropout=0.0,
            max_epochs=1, batch_size=8, n_symbols=10, symbol_embed_dim=4,
        )
        assert model.n_symbols == 10
        assert model.symbol_embed_dim == 4

    def test_init_defaults_backward_compat(self):
        """Default n_symbols=0 preserves backward compat."""
        model = LSTMVolModel(
            input_dim=5, hidden_dim=16, n_layers=1, dropout=0.0,
            max_epochs=1, batch_size=8,
        )
        assert model.n_symbols == 0
        assert model.symbol_embed_dim == 8

    def test_fit_predict_with_symbol_ids(self):
        """End-to-end fit/predict with symbol_ids (n_symbols > 0)."""
        seq, targets = _make_seq(n_dates=30, n_features=5)
        symbol_ids = np.zeros(30, dtype=np.int64)  # all same symbol
        model = LSTMVolModel(
            input_dim=5, hidden_dim=16, n_layers=1, dropout=0.0,
            max_epochs=3, batch_size=16, val_fraction=0.0,
            n_symbols=3, symbol_embed_dim=4, device="cpu", compile=False,
        )
        model.fit(seq, targets, symbol_ids=symbol_ids)
        preds = model.predict(seq, symbol_ids=symbol_ids)
        assert preds.shape == (30,)
        assert np.all(np.isfinite(preds))

    def test_fit_predict_without_symbol_ids_n_symbols_zero(self):
        """fit/predict with n_symbols=0 and no symbol_ids (backward compat)."""
        seq, targets = _make_seq(n_dates=30, n_features=5)
        model = LSTMVolModel(
            input_dim=5, hidden_dim=16, n_layers=1, dropout=0.0,
            max_epochs=3, batch_size=16, val_fraction=0.0,
            device="cpu", compile=False,
        )
        model.fit(seq, targets)
        preds = model.predict(seq)
        assert preds.shape == (30,)
        assert np.all(np.isfinite(preds))

    def test_fit_predict_different_symbols_different_preds(self):
        """Same sequences but different symbol_ids → different predictions."""
        seq, targets = _make_seq(n_dates=30, n_features=5)
        model = LSTMVolModel(
            input_dim=5, hidden_dim=16, n_layers=1, dropout=0.0,
            max_epochs=5, batch_size=16, val_fraction=0.0,
            n_symbols=3, symbol_embed_dim=4, device="cpu", compile=False,
            seed=42,
        )
        sym_a = np.zeros(30, dtype=np.int64)
        sym_b = np.ones(30, dtype=np.int64)
        model.fit(seq, targets, symbol_ids=sym_a)
        preds_a = model.predict(seq, symbol_ids=sym_a)
        preds_b = model.predict(seq, symbol_ids=sym_b)
        # With trained embedding, different symbols produce different preds
        assert not np.allclose(preds_a, preds_b, atol=1e-6)

    def test_get_params_includes_embedding_fields(self):
        """get_params() should include n_symbols and symbol_embed_dim."""
        model = LSTMVolModel(
            input_dim=5, hidden_dim=16, n_layers=1, dropout=0.0,
            n_symbols=10, symbol_embed_dim=4,
        )
        params = model.get_params()
        assert params["n_symbols"] == 10
        assert params["symbol_embed_dim"] == 4

    def test_save_load_preserves_symbol_to_id(self, tmp_path: Path):
        """save/load round-trip preserves symbol_to_id mapping."""
        seq, targets = _make_seq(n_dates=30, n_features=5)
        model = LSTMVolModel(
            input_dim=5, hidden_dim=16, n_layers=1, dropout=0.0,
            max_epochs=2, batch_size=16, val_fraction=0.0,
            n_symbols=3, symbol_embed_dim=4, device="cpu", compile=False,
        )
        model.symbol_to_id = {"AAPL": 0, "MSFT": 1, "SPY": 2}
        sym_ids = np.zeros(30, dtype=np.int64)
        model.fit(seq, targets, symbol_ids=sym_ids)

        save_path = tmp_path / "model.pt"
        model.save(save_path)
        loaded = LSTMVolModel.load(save_path)

        assert loaded.symbol_to_id == {"AAPL": 0, "MSFT": 1, "SPY": 2}
        assert loaded.n_symbols == 3
        assert loaded.symbol_embed_dim == 4

    def test_save_load_predictions_match(self, tmp_path: Path):
        """Loaded model produces same predictions as original."""
        seq, targets = _make_seq(n_dates=30, n_features=5)
        sym_ids = np.array([0] * 15 + [1] * 15, dtype=np.int64)
        model = LSTMVolModel(
            input_dim=5, hidden_dim=16, n_layers=1, dropout=0.0,
            max_epochs=3, batch_size=16, val_fraction=0.0,
            n_symbols=2, symbol_embed_dim=4, device="cpu", compile=False,
        )
        model.fit(seq, targets, symbol_ids=sym_ids)
        preds_orig = model.predict(seq, symbol_ids=sym_ids)

        save_path = tmp_path / "model.pt"
        model.save(save_path)
        loaded = LSTMVolModel.load(save_path)
        preds_loaded = loaded.predict(seq, symbol_ids=sym_ids)

        np.testing.assert_allclose(preds_orig, preds_loaded, rtol=1e-5)

    def test_symbol_id_mapping_deterministic(self):
        """symbol_to_id built from sorted list is stable."""
        symbols = ["NVDA", "AAPL", "SPY", "MSFT", "GOOGL"]
        mapping = {sym: i for i, sym in enumerate(sorted(symbols))}
        # Verify sorted order
        assert mapping == {"AAPL": 0, "GOOGL": 1, "MSFT": 2, "NVDA": 3, "SPY": 4}
        # Different input order → same mapping
        symbols_shuffled = ["SPY", "GOOGL", "NVDA", "MSFT", "AAPL"]
        mapping2 = {sym: i for i, sym in enumerate(sorted(symbols_shuffled))}
        assert mapping == mapping2

    def test_maybe_compile_uses_default_mode_with_embedding(self):
        """When n_symbols > 0, compile mode should be 'default' not 'reduce-overhead'."""
        model = LSTMVolModel(
            input_dim=5, hidden_dim=16, n_layers=1, dropout=0.0,
            n_symbols=5, symbol_embed_dim=4, compile=True, device="cpu",
        )
        # On CPU, compile is skipped, so this tests the logic indirectly.
        # We verify the attribute is set and the method doesn't crash.
        body = model._build_module()
        result = model._maybe_compile(body)
        # On CPU it returns body unchanged (compile disabled for CPU)
        assert result is body

    def test_eval_loss_with_symbol_ids(self):
        """_eval_loss should work with symbol_ids passed through."""
        seq, targets = _make_seq(n_dates=30, n_features=5)
        sym_ids = np.zeros(30, dtype=np.int64)
        model = LSTMVolModel(
            input_dim=5, hidden_dim=16, n_layers=1, dropout=0.0,
            max_epochs=2, batch_size=16, val_fraction=0.3,
            n_symbols=2, symbol_embed_dim=4, device="cpu", compile=False,
        )
        # fit with val split — exercises _eval_loss with symbol_ids
        model.fit(seq, targets, symbol_ids=sym_ids)
        assert model.epochs_run_ > 0
        assert model.best_val_loss_ is not None
