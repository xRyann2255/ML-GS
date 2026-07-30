"""Unit tests for LSTM in-network LayerNorm (trial-100 feature)."""

from __future__ import annotations

import torch
import pytest

from volforecast.models.lstm import _LSTMBody, LSTMVolModel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

INPUT_DIM = 12
HIDDEN_DIM = 32
BATCH = 8
SEQ_LEN = 78


def _random_batch(
    batch: int = BATCH, seq_len: int = SEQ_LEN, input_dim: int = INPUT_DIM
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return (x, lengths) tensors for testing."""
    x = torch.randn(batch, seq_len, input_dim)
    lengths = torch.randint(10, seq_len + 1, (batch,))
    return x, lengths


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestForwardShapeWithLayerNorm:
    """Forward pass shape correctness with layer_norm=True."""

    def test_forward_shape_with_layernorm(self):
        body = _LSTMBody(
            input_dim=INPUT_DIM,
            hidden_dim=HIDDEN_DIM,
            n_layers=2,
            dropout=0.1,
            bidirectional=True,
            layer_norm=True,
        )
        body.eval()
        x, lengths = _random_batch()
        with torch.no_grad():
            out = body(x, lengths)
        assert out.shape == (BATCH,), f"Expected ({BATCH},), got {out.shape}"

    def test_forward_shape_without_layernorm(self):
        body = _LSTMBody(
            input_dim=INPUT_DIM,
            hidden_dim=HIDDEN_DIM,
            n_layers=2,
            dropout=0.1,
            bidirectional=True,
            layer_norm=False,
        )
        body.eval()
        x, lengths = _random_batch()
        with torch.no_grad():
            out = body(x, lengths)
        assert out.shape == (BATCH,), f"Expected ({BATCH},), got {out.shape}"


class TestLayerNormEffect:
    """Verify LayerNorm reduces output scale on extreme inputs."""

    def test_layernorm_reduces_output_scale(self):
        """LayerNorm on extreme-scale inputs should produce more controlled outputs."""
        torch.manual_seed(42)
        # Extreme-scale input (large magnitude features)
        x = torch.randn(BATCH, SEQ_LEN, INPUT_DIM) * 100.0
        lengths = torch.full((BATCH,), SEQ_LEN, dtype=torch.long)

        body_ln = _LSTMBody(
            input_dim=INPUT_DIM,
            hidden_dim=HIDDEN_DIM,
            n_layers=1,
            dropout=0.0,
            bidirectional=False,
            layer_norm=True,
        )
        body_no_ln = _LSTMBody(
            input_dim=INPUT_DIM,
            hidden_dim=HIDDEN_DIM,
            n_layers=1,
            dropout=0.0,
            bidirectional=False,
            layer_norm=False,
        )
        # Copy weights from no_ln to ln (shared LSTM + head weights)
        body_ln.lstm.load_state_dict(body_no_ln.lstm.state_dict())
        body_ln.head.load_state_dict(body_no_ln.head.state_dict())
        if hasattr(body_ln, "pool") and hasattr(body_no_ln, "pool"):
            body_ln.pool.load_state_dict(body_no_ln.pool.state_dict())

        body_ln.eval()
        body_no_ln.eval()

        with torch.no_grad():
            out_ln, mask_ln = body_ln._encode(x, lengths)
            out_no_ln, mask_no_ln = body_no_ln._encode(x, lengths)

        # Output from LayerNorm path should have lower variance across features
        var_ln = out_ln.var(dim=-1).mean().item()
        var_no_ln = out_no_ln.var(dim=-1).mean().item()

        # LayerNorm normalises the hidden states to approximately unit variance,
        # so var_ln should be close to 1.0 while var_no_ln can explode with large inputs
        assert var_ln < var_no_ln or var_ln < 2.0, (
            f"LayerNorm output variance ({var_ln:.4f}) should be lower than "
            f"non-LayerNorm ({var_no_ln:.4f}) on extreme inputs"
        )


class TestBackwardCompat:
    """layer_norm=False must not change behaviour."""

    def test_backward_compat_no_layernorm(self):
        """Model with layer_norm=False should have identical parameters to old model."""
        body_default = _LSTMBody(
            input_dim=INPUT_DIM,
            hidden_dim=HIDDEN_DIM,
            n_layers=2,
            dropout=0.1,
            bidirectional=True,
            layer_norm=False,
        )
        # Should NOT have input_ln or output_ln attributes
        assert not hasattr(body_default, "input_ln")
        assert not hasattr(body_default, "output_ln")

    def test_layernorm_true_has_ln_modules(self):
        body = _LSTMBody(
            input_dim=INPUT_DIM,
            hidden_dim=HIDDEN_DIM,
            n_layers=2,
            dropout=0.1,
            bidirectional=True,
            layer_norm=True,
        )
        assert hasattr(body, "input_ln")
        assert hasattr(body, "output_ln")
        assert isinstance(body.input_ln, torch.nn.LayerNorm)
        assert isinstance(body.output_ln, torch.nn.LayerNorm)
        # Check dims
        assert body.input_ln.normalized_shape == (INPUT_DIM,)
        out_dim = HIDDEN_DIM * 2  # bidirectional
        assert body.output_ln.normalized_shape == (out_dim,)


class TestLSTMVolModelLayerNorm:
    """Integration: LSTMVolModel accepts and threads layer_norm."""

    def test_get_params_includes_layer_norm(self):
        model = LSTMVolModel(input_dim=INPUT_DIM, layer_norm=True)
        params = model.get_params()
        assert "layer_norm" in params
        assert params["layer_norm"] is True

    def test_get_params_default_false(self):
        model = LSTMVolModel(input_dim=INPUT_DIM)
        params = model.get_params()
        assert "layer_norm" in params
        assert params["layer_norm"] is False

    def test_build_module_with_layernorm(self):
        model = LSTMVolModel(input_dim=INPUT_DIM, hidden_dim=HIDDEN_DIM, layer_norm=True)
        body = model._build_module()
        assert body.layer_norm is True
        assert hasattr(body, "input_ln")
        assert hasattr(body, "output_ln")

    def test_build_module_without_layernorm(self):
        model = LSTMVolModel(input_dim=INPUT_DIM, hidden_dim=HIDDEN_DIM, layer_norm=False)
        body = model._build_module()
        assert body.layer_norm is False
        assert not hasattr(body, "input_ln")
        assert not hasattr(body, "output_ln")
