"""STID: Spatial-Temporal Identity embedding deflation control (Shao et al. 2022).

y_hat_i = MLP(concat(x_i, embed[i]))

A mandatory deflation baseline: per-node learned identity embeddings + MLP,
consuming the same graph-dict harness but ignoring edges entirely. If STID
matches GNNHAR, the honest conclusion is "pooling + asset identity suffices",
not "spillovers matter".

``requires_graph = True`` deliberately — so it runs through the identical
Plan-02 harness, folds, and features as the GNN models.
"""

from __future__ import annotations

import logging
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from volforecast.models._base import _BaseModel
from volforecast.models.gnn import _LOSSES, _resolve_device, _resolve_precision
from volforecast.registry import register_model

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PyTorch nn.Module
# ---------------------------------------------------------------------------


class _STIDModule(nn.Module):
    """Per-node identity embedding + MLP."""

    def __init__(
        self,
        n_nodes: int,
        input_dim: int,
        embed_dim: int,
        hidden_dim: int,
        dropout: float = 0.1,
        dow_embed: bool = False,
    ) -> None:
        super().__init__()
        self.node_embed = nn.Embedding(n_nodes, embed_dim)
        self.dow_embed_layer = nn.Embedding(5, embed_dim) if dow_embed else None
        in_dim = input_dim + embed_dim + (embed_dim if dow_embed else 0)
        self.mlp = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
        )
        self.n_nodes = n_nodes

    def forward(self, x: torch.Tensor, dow: torch.Tensor | None = None) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x : (T, N, F) node features
        dow : (T,) int tensor of day-of-week (0=Mon, 4=Fri), optional

        Returns
        -------
        (T, N) per-node predictions
        """
        t_len, n, _ = x.shape
        node_ids = torch.arange(n, device=x.device)
        e = self.node_embed(node_ids).unsqueeze(0).expand(t_len, -1, -1)  # (T, N, E)
        parts = [x, e]
        if self.dow_embed_layer is not None and dow is not None:
            dow_e = self.dow_embed_layer(dow)[:, None, :].expand(-1, n, -1)  # (T, N, E)
            parts.append(dow_e)
        return self.mlp(torch.cat(parts, dim=-1)).squeeze(-1)


# ---------------------------------------------------------------------------
# Registered model class
# ---------------------------------------------------------------------------


@register_model("stid")
class STIDVolModel(_BaseModel):
    """STID deflation control: per-node identity + MLP, edges ignored.

    ``requires_graph = True`` so it runs through the identical pipeline
    harness, folds, and features as the GNN models it controls against.
    """

    REQUIRED_LAYERS: list[str] = ["har_core"]
    requires_sequences: bool = False
    requires_graph: bool = True
    supports_tuning: bool = False
    family = "gnn"
    description = "STID: per-node identity embedding + MLP (graph-invariant deflation control)"

    def __init__(
        self,
        *,
        input_dim: int,
        n_nodes: int | None = None,
        embed_dim: int = 16,
        hidden_dim: int = 64,
        dropout: float = 0.1,
        dow_embed: bool = False,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        max_epochs: int = 300,
        early_stopping_rounds: int = 25,
        val_fraction: float = 0.15,
        loss: str = "qlike",
        device: str = "auto",
        precision: str = "auto",
        seed: int = 42,
    ) -> None:
        if loss not in _LOSSES:
            raise ValueError(f"Unknown loss {loss!r}; expected one of {list(_LOSSES)}")
        self.input_dim = int(input_dim)
        self.n_nodes = n_nodes
        self.embed_dim = int(embed_dim)
        self.hidden_dim = int(hidden_dim)
        self.dropout = float(dropout)
        self.dow_embed = bool(dow_embed)
        self.learning_rate = float(learning_rate)
        self.weight_decay = float(weight_decay)
        self.max_epochs = int(max_epochs)
        self.early_stopping_rounds = int(early_stopping_rounds)
        self.val_fraction = float(val_fraction)
        self.loss = loss
        self.device = _resolve_device(device)
        self.precision = precision
        self.seed = int(seed)

        self._module: _STIDModule | None = None
        self._n_nodes: int | None = n_nodes
        self.epochs_run_: int = 0
        self.best_val_loss_: float | None = None

    def _set_seed(self) -> None:
        torch.manual_seed(self.seed)
        np.random.seed(self.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.seed)

    # ------------------------------------------------------------------
    # fit
    # ------------------------------------------------------------------

    def fit(
        self,
        graphs: list[dict[str, Any]],
        y: Any | None = None,
        *,
        on_progress: Any | None = None,
    ) -> "STIDVolModel":
        """Train STID on graph snapshots (ignoring edges).

        Parameters
        ----------
        graphs : list[dict]
            Same format as GNNHAR. edge_index/edge_attr are present but ignored.
        """
        if not graphs:
            raise ValueError("STID: no graphs to fit")

        self._set_seed()
        n = graphs[0]["x"].shape[0]
        f = self.input_dim
        self._n_nodes = n

        # Stack data tensors
        X = torch.tensor(
            np.stack([g["x"][:, :f] for g in graphs]), dtype=torch.float32
        )  # (T, N, F)
        Y = torch.tensor(np.stack([g["y"] for g in graphs]), dtype=torch.float32)  # (T, N)
        mask = torch.isfinite(Y)

        # Day of week (optional)
        dow = None
        if self.dow_embed:
            dow = torch.tensor(
                [g["date"].dayofweek for g in graphs], dtype=torch.long
            )

        # Temporal val split
        t_total = len(graphs)
        n_val = max(1, int(math.ceil(t_total * self.val_fraction)))
        n_train = t_total - n_val

        X_tr, X_val = X[:n_train], X[n_train:]
        Y_tr, Y_val = Y[:n_train], Y[n_train:]
        mask_tr, mask_val = mask[:n_train], mask[n_train:]
        dow_tr = dow[:n_train] if dow is not None else None
        dow_val = dow[n_train:] if dow is not None else None

        # Move to device
        dev = self.device
        X_tr, X_val = X_tr.to(dev), X_val.to(dev)
        Y_tr, Y_val = Y_tr.to(dev), Y_val.to(dev)
        mask_tr, mask_val = mask_tr.to(dev), mask_val.to(dev)
        if dow_tr is not None:
            dow_tr, dow_val = dow_tr.to(dev), dow_val.to(dev)

        self._module = _STIDModule(
            n, f, self.embed_dim, self.hidden_dim, self.dropout, self.dow_embed
        ).to(dev)

        optimizer = torch.optim.Adam(
            self._module.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay
        )
        criterion = _LOSSES[self.loss]
        amp_dtype = _resolve_precision(self.precision, dev)

        best_val_loss = float("inf")
        patience_counter = 0
        best_state: dict[str, Any] | None = None

        for epoch in range(1, self.max_epochs + 1):
            # --- Train ---
            self._module.train()
            optimizer.zero_grad()
            with torch.autocast(
                device_type=dev.split(":")[0],
                dtype=amp_dtype,
                enabled=amp_dtype is not None,
            ):
                pred = self._module(X_tr, dow_tr)
                loss = criterion(pred[mask_tr], Y_tr[mask_tr])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self._module.parameters(), 1.0)
            optimizer.step()

            # --- Validate ---
            self._module.eval()
            with torch.no_grad():
                with torch.autocast(
                    device_type=dev.split(":")[0],
                    dtype=amp_dtype,
                    enabled=amp_dtype is not None,
                ):
                    val_pred = self._module(X_val, dow_val)
                    val_loss = criterion(val_pred[mask_val], Y_val[mask_val]).item()

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                best_state = {
                    k: v.detach().cpu().clone() for k, v in self._module.state_dict().items()
                }
            else:
                patience_counter += 1

            if on_progress is not None:
                on_progress(epoch, self.max_epochs)

            if patience_counter >= self.early_stopping_rounds:
                break

        # Restore best weights
        if best_state is not None:
            self._module.load_state_dict(best_state)
            self._module.to(dev)
        self._module.eval()

        self.epochs_run_ = epoch
        self.best_val_loss_ = best_val_loss
        return self

    # ------------------------------------------------------------------
    # predict
    # ------------------------------------------------------------------

    def predict(self, graphs: list[dict[str, Any]]) -> np.ndarray:
        """Predict log-RV for each node (edges ignored)."""
        if self._module is None:
            raise RuntimeError("predict called before fit")
        n = self._n_nodes
        f = self.input_dim
        X = torch.tensor(
            np.stack([g["x"][:, :f] for g in graphs]), dtype=torch.float32
        )
        dow = None
        if self.dow_embed and self._module.dow_embed_layer is not None:
            dow = torch.tensor(
                [g["date"].dayofweek for g in graphs], dtype=torch.long
            )

        dev = self.device
        X = X.to(dev)
        if dow is not None:
            dow = dow.to(dev)

        self._module.eval()
        with torch.no_grad():
            pred = self._module(X, dow)
        return pred.cpu().numpy().reshape(-1)

    # ------------------------------------------------------------------
    # extract_features
    # ------------------------------------------------------------------

    def extract_features(
        self,
        graphs: list[dict[str, Any]],
        *,
        outputs: list[str] | None = None,
    ) -> dict[str, np.ndarray]:
        if outputs is None:
            outputs = ["prediction"]
        result: dict[str, np.ndarray] = {}
        if "prediction" in outputs:
            result["prediction"] = self.predict(graphs)
        return result

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    def save(self, path: Path) -> Path:
        if self._module is None:
            raise RuntimeError("STIDVolModel.save called before fit")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "init_kwargs": self.get_params(),
            "state_dict": {k: v.detach().cpu() for k, v in self._module.state_dict().items()},
            "n_nodes": self._n_nodes,
            "epochs_run": self.epochs_run_,
            "best_val_loss": self.best_val_loss_,
        }
        tmp = path.with_suffix(path.suffix + ".tmp")
        torch.save(payload, tmp)
        os.replace(tmp, path)
        return path

    @classmethod
    def load(cls, path: Path) -> "STIDVolModel":
        payload = torch.load(Path(path), map_location="cpu", weights_only=False)
        init_kwargs = payload["init_kwargs"]
        init_kwargs["n_nodes"] = payload["n_nodes"]
        instance = cls(**init_kwargs)
        instance._n_nodes = payload["n_nodes"]
        n = instance._n_nodes
        f = instance.input_dim
        instance._module = _STIDModule(
            n, f, instance.embed_dim, instance.hidden_dim, instance.dropout, instance.dow_embed
        )
        instance._module.load_state_dict(payload["state_dict"])
        instance._module.eval()
        instance.epochs_run_ = payload.get("epochs_run", 0)
        instance.best_val_loss_ = payload.get("best_val_loss")
        return instance

    # ------------------------------------------------------------------
    # params / summary
    # ------------------------------------------------------------------

    def get_params(self) -> dict[str, Any]:
        return {
            "input_dim": self.input_dim,
            "n_nodes": self._n_nodes,
            "embed_dim": self.embed_dim,
            "hidden_dim": self.hidden_dim,
            "dropout": self.dropout,
            "dow_embed": self.dow_embed,
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

    def get_arch_summary(self) -> dict[str, Any]:
        param_count = None
        if self._module is not None:
            param_count = sum(p.numel() for p in self._module.parameters())
        return {
            "embed_dim": self.embed_dim,
            "hidden_dim": self.hidden_dim,
            "dow_embed": self.dow_embed,
            "loss": self.loss,
            "epochs_trained": self.epochs_run_,
            "best_val_loss": self.best_val_loss_,
            "param_count": param_count,
        }

    @property
    def summary(self) -> dict[str, float]:
        s = self.get_arch_summary()
        return {k: float(v) for k, v in s.items() if v is not None and isinstance(v, (int, float))}
