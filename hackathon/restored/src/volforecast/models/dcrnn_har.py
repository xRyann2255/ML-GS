"""DCRNN-HAR: Diffusion Convolutional Recurrent Neural Network for volatility forecasting.

Implements DiffusionConv and DCGRUCell from Li et al. 2018 (DCRNN, eq. 2).
Bidirectional K-step diffusion convolution over a dense directed adjacency matrix.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from volforecast.models._base import _BaseModel
from volforecast.models.gnn import _LOSSES, _resolve_device, _resolve_precision
from volforecast.registry import register_model

logger = logging.getLogger(__name__)


class DiffusionConv(nn.Module):
    """Bidirectional K-step diffusion convolution (Li et al. 2018, DCRNN eq. 2)."""

    def __init__(self, in_dim: int, out_dim: int, k: int = 2) -> None:
        super().__init__()
        self.k = k
        # (2K+1) weight matrices: k=0 identity support, then fwd+bwd for steps 1..K
        self.weights = nn.ModuleList(
            [nn.Linear(in_dim, out_dim, bias=False) for _ in range(2 * k + 1)]
        )
        self.bias = nn.Parameter(torch.zeros(out_dim))

    @staticmethod
    def normalize(w: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Row-normalize: fwd = D_O^{-1} W, bwd = D_I^{-1} W^T. Zero-degree rows stay zero."""
        d_out = w.sum(1, keepdim=True).clamp(min=1e-12)
        d_in = w.sum(0, keepdim=True).clamp(min=1e-12).T
        return w / d_out, w.T / d_in

    def forward(self, x: torch.Tensor, fwd: torch.Tensor, bwd: torch.Tensor) -> torch.Tensor:
        out = self.weights[0](x)  # k=0 (identity support)
        xf, xb = x, x
        for step in range(1, self.k + 1):
            xf = fwd @ xf
            xb = bwd @ xb
            out = out + self.weights[2 * step - 1](xf) + self.weights[2 * step](xb)
        return out + self.bias


class DCGRUCell(nn.Module):
    """GRU cell with DiffusionConv replacing dense matmuls (Li et al. 2018)."""

    def __init__(self, in_dim: int, hidden_dim: int, k: int = 2) -> None:
        super().__init__()
        self.gates = DiffusionConv(in_dim + hidden_dim, 2 * hidden_dim, k)  # r, u
        self.cand = DiffusionConv(in_dim + hidden_dim, hidden_dim, k)

    def forward(
        self, x: torch.Tensor, h: torch.Tensor, fwd: torch.Tensor, bwd: torch.Tensor
    ) -> torch.Tensor:
        ru = torch.sigmoid(self.gates(torch.cat([x, h], -1), fwd, bwd))
        r, u = ru.chunk(2, dim=-1)
        c = torch.tanh(self.cand(torch.cat([x, r * h], -1), fwd, bwd))
        return u * h + (1.0 - u) * c


# ---------------------------------------------------------------------------
# _DCRNNHARModule: recurrent GCN + HAR skip connection
# ---------------------------------------------------------------------------


class _DCRNNHARModule(nn.Module):
    """Recurrent diffusion-conv encoder with jointly-trained HAR skip channel."""

    def __init__(self, n_nodes: int, input_dim: int, hidden_dim: int, k: int) -> None:
        super().__init__()
        self.cell = DCGRUCell(input_dim, hidden_dim, k)
        self.head = nn.Linear(hidden_dim, 1)
        self.har_skip = nn.Linear(input_dim, 1)  # jointly-trained plain-HAR channel
        self.alpha = nn.Parameter(torch.zeros(n_nodes))

    def forward_step(
        self, x: torch.Tensor, h: torch.Tensor, fwd: torch.Tensor, bwd: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Single recurrent step: advance hidden state and produce a prediction.

        Parameters
        ----------
        x : (N, F) node features for one timestep
        h : (N, hidden_dim) previous hidden state
        fwd, bwd : (N, N) normalized adjacency matrices

        Returns
        -------
        pred : (N,) per-node prediction
        h_new : (N, hidden_dim) updated hidden state
        """
        h_new = self.cell(x, h, fwd, bwd)
        pred = self.alpha + self.head(h_new).squeeze(-1) + self.har_skip(x).squeeze(-1)
        return pred, h_new

    def forward(
        self, xs: list[torch.Tensor], fwds: list[torch.Tensor], bwds: list[torch.Tensor]
    ) -> torch.Tensor:
        """Forward pass over a sequence of graph snapshots.

        Parameters
        ----------
        xs : list of (N, F) tensors, length = seq_len
        fwds, bwds : list of (N, N) normalized adj matrices

        Returns
        -------
        (N,) per-node predictions at the final time step.
        """
        h = torch.zeros(xs[0].shape[0], self.head.in_features, device=xs[0].device)
        for x, f, b in zip(xs, fwds, bwds):
            pred, h = self.forward_step(x, h, f, b)
        return pred


# ---------------------------------------------------------------------------
# Registered model class
# ---------------------------------------------------------------------------


@register_model("dcrnn_har")
class DCRNNHARVolModel(_BaseModel):
    """DCRNN-HAR: diffusion-conv recurrent encoder + HAR skip for vol forecasting.

    Set ``requires_graph = True`` so the pipeline runner dispatches graph dicts.
    The ``warmup`` attribute tells the runner to prepend train graphs for state.
    """

    REQUIRED_LAYERS: list[str] = ["har_core"]
    requires_sequences: bool = False
    requires_graph: bool = True
    supports_tuning: bool = False
    family: str = "gnn"
    description: str = "DCRNN-HAR: diffusion-conv recurrent + HAR skip channel"

    def __init__(
        self,
        *,
        input_dim: int,
        hidden_dim: int = 16,
        k: int = 2,
        seq_len: int = 22,
        tbptt_len: int | None = None,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        max_epochs: int = 200,
        early_stopping_rounds: int = 20,
        val_fraction: float = 0.15,
        loss: str = "qlike",
        device: str = "auto",
        precision: str = "auto",
        seed: int = 42,
    ) -> None:
        if loss not in _LOSSES:
            raise ValueError(f"Unknown loss {loss!r}; expected one of {list(_LOSSES)}")
        self.input_dim = int(input_dim)
        self.hidden_dim = int(hidden_dim)
        self.k = int(k)
        self.seq_len = int(seq_len)
        self.tbptt_len = int(tbptt_len) if tbptt_len is not None else self.seq_len
        self.learning_rate = float(learning_rate)
        self.weight_decay = float(weight_decay)
        self.max_epochs = int(max_epochs)
        self.early_stopping_rounds = int(early_stopping_rounds)
        self.val_fraction = float(val_fraction)
        self.loss = loss
        self.device = _resolve_device(device)
        self.precision = precision
        self.seed = int(seed)

        self.warmup: int = self.seq_len - 1
        self._module_: _DCRNNHARModule | None = None
        self._n_nodes: int | None = None
        self.epochs_run_: int = 0
        self.best_val_loss_: float | None = None

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _set_seed(self, seed: int) -> None:
        torch.manual_seed(seed)
        np.random.seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    def _build_adj(self, graph: dict[str, Any], n: int) -> tuple[torch.Tensor, torch.Tensor]:
        """Build dense directed adj and return (fwd, bwd) normalized matrices."""
        ei, ea = graph["edge_index"], graph["edge_attr"]
        a = torch.zeros(n, n)
        if ei.numel() > 0:
            a[ei[0], ei[1]] = ea.float()
        return DiffusionConv.normalize(a)

    # ------------------------------------------------------------------
    # fit
    # ------------------------------------------------------------------

    def fit(
        self,
        graphs: list[dict[str, Any]],
        y: Any | None = None,
        *,
        on_progress: Any | None = None,
    ) -> "DCRNNHARVolModel":
        if not graphs:
            raise ValueError("DCRNN-HAR: no graphs to fit")

        n = graphs[0]["x"].shape[0]
        f = self.input_dim
        self._n_nodes = n
        T = len(graphs)
        warmup = self.warmup
        tbptt_len = self.tbptt_len

        if T <= warmup:
            raise ValueError(
                f"DCRNN-HAR: not enough graphs ({T}) for seq_len={self.seq_len}"
            )

        # Precompute per-date data
        X_all = [
            torch.tensor(g["x"][:, :f], dtype=torch.float32) for g in graphs
        ]
        Y_all = torch.tensor(
            np.stack([g["y"] for g in graphs]), dtype=torch.float32
        )  # (T, N)
        adj_pairs = [self._build_adj(g, n) for g in graphs]

        # Temporal train/val split on dates (not windows)
        n_val = max(1, int(math.ceil((T - warmup) * self.val_fraction)))
        t_val_start = T - n_val  # first val date index

        # Move data to device
        dev = self.device
        X_dev = [x.to(dev) for x in X_all]
        Y_dev = Y_all.to(dev)
        adj_dev = [(fw.to(dev), bw.to(dev)) for fw, bw in adj_pairs]

        mask = torch.isfinite(Y_dev)

        amp_dtype = _resolve_precision(self.precision, dev)
        criterion = _LOSSES[self.loss]

        self._set_seed(self.seed)
        module = _DCRNNHARModule(n, f, self.hidden_dim, self.k).to(dev)
        optimizer = torch.optim.Adam(
            module.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay
        )

        best_val_loss = float("inf")
        patience_counter = 0
        best_state: dict[str, Any] | None = None

        for epoch in range(1, self.max_epochs + 1):
            # --- Single-pass TBPTT training ---
            module.train()
            h = torch.zeros(n, self.hidden_dim, device=dev)
            epoch_loss = 0.0
            train_count = 0
            chunk_loss = torch.tensor(0.0, device=dev)
            chunk_count = 0
            chunk_start = 0

            for t in range(t_val_start):
                with torch.autocast(
                    device_type=dev.split(":")[0],
                    dtype=amp_dtype,
                    enabled=amp_dtype is not None,
                ):
                    pred, h = module.forward_step(X_dev[t], h, adj_dev[t][0], adj_dev[t][1])

                    if t >= warmup:
                        m = mask[t]
                        if m.any():
                            chunk_loss = chunk_loss + criterion(pred[m], Y_dev[t][m])
                            chunk_count += 1

                # TBPTT: backprop and detach at chunk boundaries
                steps_in_chunk = t - chunk_start + 1
                if steps_in_chunk >= tbptt_len:
                    if chunk_count > 0:
                        optimizer.zero_grad()
                        (chunk_loss / chunk_count).backward()
                        torch.nn.utils.clip_grad_norm_(module.parameters(), 1.0)
                        optimizer.step()
                        epoch_loss += chunk_loss.item()
                        train_count += chunk_count
                    h = h.detach()
                    chunk_loss = torch.tensor(0.0, device=dev)
                    chunk_count = 0
                    chunk_start = t + 1

            # Flush any remaining partial chunk
            if chunk_count > 0:
                optimizer.zero_grad()
                (chunk_loss / chunk_count).backward()
                torch.nn.utils.clip_grad_norm_(module.parameters(), 1.0)
                optimizer.step()
                epoch_loss += chunk_loss.item()
                train_count += chunk_count

            # --- Validate: single-pass continuation, no gradients ---
            h = h.detach()
            module.eval()
            val_loss_sum = 0.0
            val_count = 0
            with torch.no_grad():
                for t in range(t_val_start, T):
                    with torch.autocast(
                        device_type=dev.split(":")[0],
                        dtype=amp_dtype,
                        enabled=amp_dtype is not None,
                    ):
                        pred, h = module.forward_step(
                            X_dev[t], h, adj_dev[t][0], adj_dev[t][1]
                        )
                        m = mask[t]
                        if m.any():
                            val_loss_sum += criterion(pred[m], Y_dev[t][m]).item()
                            val_count += 1

            val_loss = val_loss_sum / max(val_count, 1)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                best_state = {
                    k: v.detach().cpu().clone() for k, v in module.state_dict().items()
                }
            else:
                patience_counter += 1

            if on_progress is not None:
                on_progress(epoch, self.max_epochs)

            if patience_counter >= self.early_stopping_rounds:
                if on_progress is not None:
                    on_progress(self.max_epochs, self.max_epochs)
                break

        # Restore best weights
        if best_state is not None:
            module.load_state_dict(best_state)
            module.to(dev)
        module.eval()
        self._module_ = module
        self.epochs_run_ = epoch
        self.best_val_loss_ = best_val_loss
        return self

    # ------------------------------------------------------------------
    # predict
    # ------------------------------------------------------------------

    def predict(self, graphs: list[dict[str, Any]]) -> np.ndarray:
        """Predict log-RV for each node via single sequential forward pass.

        When called with (warmup + T_test) graphs, the first ``warmup`` steps
        build hidden state (no predictions emitted). Predictions are returned
        for the remaining T_test dates.

        Returns
        -------
        np.ndarray, shape ((len(graphs) - warmup) * N,) flattened node-major per date.
        """
        if self._module_ is None:
            raise RuntimeError("predict called before fit")
        n = self._n_nodes
        f = self.input_dim
        warmup = self.warmup
        T = len(graphs)
        dev = self.device

        X_all = [
            torch.tensor(g["x"][:, :f], dtype=torch.float32).to(dev) for g in graphs
        ]
        adj_pairs = [self._build_adj(g, n) for g in graphs]
        adj_dev = [(fw.to(dev), bw.to(dev)) for fw, bw in adj_pairs]

        preds = []
        self._module_.eval()
        h = torch.zeros(n, self.hidden_dim, device=dev)
        with torch.no_grad():
            for t in range(T):
                pred, h = self._module_.forward_step(
                    X_all[t], h, adj_dev[t][0], adj_dev[t][1]
                )
                if t >= warmup:
                    preds.append(pred.cpu().numpy())

        return np.concatenate(preds)  # ((T - warmup) * N,)

    # ------------------------------------------------------------------
    # params / summary
    # ------------------------------------------------------------------

    def get_params(self) -> dict[str, Any]:
        return {
            "input_dim": self.input_dim,
            "hidden_dim": self.hidden_dim,
            "k": self.k,
            "seq_len": self.seq_len,
            "tbptt_len": self.tbptt_len,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "max_epochs": self.max_epochs,
            "early_stopping_rounds": self.early_stopping_rounds,
            "val_fraction": self.val_fraction,
            "loss": self.loss,
            "device": self.device,
            "precision": self.precision,
            "seed": self.seed,
        }

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "epochs_run": self.epochs_run_,
            "best_val_loss": self.best_val_loss_,
            "n_nodes": self._n_nodes,
        }
