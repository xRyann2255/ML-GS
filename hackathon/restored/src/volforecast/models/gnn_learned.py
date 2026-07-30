"""GNN with learned adjacency (MTGNN graph-learning layer, Wu et al. 2020).

Learns A = relu(tanh(a*(M1@M2.T - M2@M1.T))) with M1 = tanh(a*E1@Th1),
M2 = tanh(a*E2@Th2), row-wise top-k sparsification, then a GNNHAR-style
one-hop body over the learned A. Input edges are ignored entirely —
the adjacency is learned end-to-end from node embeddings.

top_k=0 -> zero adjacency -> nests QLIKE-HAR (graph channel = 0).
top_k >= N-1 -> dense (no sparsification).
"""

from __future__ import annotations

import logging
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from volforecast.models._base import _BaseModel
from volforecast.models.gnn import _LOSSES, _resolve_device, _resolve_precision
from volforecast.registry import register_model

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Adaptive adjacency learning layer (MTGNN, Wu et al. 2020)
# ---------------------------------------------------------------------------


class _AdaptiveAdjacency(nn.Module):
    """Learn a directed sparse adjacency from node embeddings."""

    def __init__(
        self, n_nodes: int, embed_dim: int = 8, top_k: int = 5, alpha: float = 3.0
    ) -> None:
        super().__init__()
        self.e1 = nn.Parameter(torch.randn(n_nodes, embed_dim) * 0.1)
        self.e2 = nn.Parameter(torch.randn(n_nodes, embed_dim) * 0.1)
        self.th1 = nn.Linear(embed_dim, embed_dim, bias=False)
        self.th2 = nn.Linear(embed_dim, embed_dim, bias=False)
        self.top_k = top_k
        self.alpha = alpha
        self.n_nodes = n_nodes

    def forward(self) -> torch.Tensor:
        """Compute learned adjacency (N, N) with zero diagonal and row normalization."""
        m1 = torch.tanh(self.alpha * self.th1(self.e1))
        m2 = torch.tanh(self.alpha * self.th2(self.e2))
        a = torch.relu(torch.tanh(self.alpha * (m1 @ m2.T - m2 @ m1.T)))
        # Zero diagonal without inplace op (avoids autograd issue)
        mask = 1.0 - torch.eye(self.n_nodes, device=a.device)
        a = a * mask
        if self.top_k <= 0:
            return torch.zeros_like(a)
        if self.top_k < a.shape[0] - 1:
            thresh = a.topk(self.top_k, dim=1).values[:, -1:]
            a = a * (a >= thresh).float()
        # Row normalize
        deg = a.sum(1, keepdim=True).clamp(min=1e-12)
        return a / deg


# ---------------------------------------------------------------------------
# GNN body with learned adjacency
# ---------------------------------------------------------------------------


class _GNNLearnedModule(nn.Module):
    """Adaptive adjacency + one-hop GCN body + HAR skip."""

    def __init__(
        self,
        n_nodes: int,
        input_dim: int,
        hidden_dim: int,
        embed_dim: int,
        top_k: int,
        alpha: float,
    ) -> None:
        super().__init__()
        self.adj = _AdaptiveAdjacency(n_nodes, embed_dim, top_k, alpha)
        self.theta = nn.Linear(input_dim, hidden_dim, bias=False)
        self.alpha_param = nn.Parameter(torch.zeros(n_nodes))
        self.beta = nn.Linear(input_dim, 1, bias=False)
        self.gamma = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x : (T, N, F) node features

        Returns
        -------
        (T, N) per-node predictions
        """
        a = self.adj()  # (N, N)
        # One-hop: H = ReLU(A @ X @ Theta)
        h = torch.relu(torch.einsum("ij,tjf->tif", a, self.theta(x)))
        return self.alpha_param[None, :] + self.beta(x).squeeze(-1) + self.gamma(h).squeeze(-1)

    def learned_adj_numpy(self) -> np.ndarray:
        """Return the current learned adjacency as numpy (N, N)."""
        with torch.no_grad():
            return self.adj().detach().cpu().numpy()


# ---------------------------------------------------------------------------
# Registered model class
# ---------------------------------------------------------------------------


@register_model("gnn_learned")
class GNNLearnedAdjModel(_BaseModel):
    """GNN with end-to-end learned adjacency (MTGNN graph-learning layer).

    Input edges are ignored — the adjacency is learned from node embeddings.
    ``requires_graph = True`` so it runs through the identical pipeline
    harness as the other GNN models.
    """

    REQUIRED_LAYERS: list[str] = ["har_core"]
    requires_sequences: bool = False
    requires_graph: bool = True
    supports_tuning: bool = False
    family = "gnn"
    description = "GNN learned adjacency: MTGNN graph-learning + one-hop GCN body"

    def __init__(
        self,
        *,
        input_dim: int,
        hidden_dim: int = 9,
        embed_dim: int = 8,
        top_k: int = 5,
        alpha: float = 3.0,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        max_epochs: int = 300,
        early_stopping_rounds: int = 25,
        val_fraction: float = 0.15,
        loss: str = "qlike",
        n_seeds: int = 3,
        device: str = "auto",
        precision: str = "auto",
        seed: int = 42,
    ) -> None:
        if loss not in _LOSSES:
            raise ValueError(f"Unknown loss {loss!r}; expected one of {list(_LOSSES)}")
        self.input_dim = int(input_dim)
        self.hidden_dim = int(hidden_dim)
        self.embed_dim = int(embed_dim)
        self.top_k = int(top_k)
        self.alpha = float(alpha)
        self.learning_rate = float(learning_rate)
        self.weight_decay = float(weight_decay)
        self.max_epochs = int(max_epochs)
        self.early_stopping_rounds = int(early_stopping_rounds)
        self.val_fraction = float(val_fraction)
        self.loss = loss
        self.n_seeds = int(n_seeds)
        self.device = _resolve_device(device)
        self.precision = precision
        self.seed = int(seed)

        self._modules_: list[_GNNLearnedModule] = []
        self._n_nodes: int | None = None
        self._symbols: list[str] | None = None
        self.epochs_run_: int = 0
        self.best_val_loss_: float | None = None

    def _set_seed(self, seed: int) -> None:
        torch.manual_seed(seed)
        np.random.seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    # ------------------------------------------------------------------
    # fit
    # ------------------------------------------------------------------

    def fit(
        self,
        graphs: list[dict[str, Any]],
        y: Any | None = None,
        *,
        on_progress: Any | None = None,
    ) -> "GNNLearnedAdjModel":
        """Train GNN with learned adjacency on graph snapshots.

        Parameters
        ----------
        graphs : list[dict]
            Same format as GNNHAR. edge_index/edge_attr present but ignored.
        """
        if not graphs:
            raise ValueError("GNNLearnedAdj: no graphs to fit")

        n = graphs[0]["x"].shape[0]
        f = self.input_dim
        self._n_nodes = n

        # Stack data tensors (edges ignored)
        X = torch.tensor(
            np.stack([g["x"][:, :f] for g in graphs]), dtype=torch.float32
        )  # (T, N, F)
        Y = torch.tensor(np.stack([g["y"] for g in graphs]), dtype=torch.float32)  # (T, N)
        mask = torch.isfinite(Y)

        # Temporal val split
        t_total = len(graphs)
        n_val = max(1, int(math.ceil(t_total * self.val_fraction)))
        n_train = t_total - n_val

        X_tr, X_val = X[:n_train], X[n_train:]
        Y_tr, Y_val = Y[:n_train], Y[n_train:]
        mask_tr, mask_val = mask[:n_train], mask[n_train:]

        # Move to device
        dev = self.device
        X_tr, X_val = X_tr.to(dev), X_val.to(dev)
        Y_tr, Y_val = Y_tr.to(dev), Y_val.to(dev)
        mask_tr, mask_val = mask_tr.to(dev), mask_val.to(dev)

        amp_dtype = _resolve_precision(self.precision, dev)
        criterion = _LOSSES[self.loss]
        total_epochs = self.n_seeds * self.max_epochs
        global_epoch = 0
        val_losses_all = []

        self._modules_ = []

        for s in range(self.n_seeds):
            self._set_seed(self.seed + s)
            module = _GNNLearnedModule(
                n, f, self.hidden_dim, self.embed_dim, self.top_k, self.alpha
            ).to(dev)
            optimizer = torch.optim.Adam(
                module.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay
            )

            best_val_loss = float("inf")
            patience_counter = 0
            best_state: dict[str, Any] | None = None

            for epoch in range(1, self.max_epochs + 1):
                global_epoch += 1

                # --- Train ---
                module.train()
                optimizer.zero_grad()
                with torch.autocast(
                    device_type=dev.split(":")[0],
                    dtype=amp_dtype,
                    enabled=amp_dtype is not None,
                ):
                    pred = module(X_tr)
                    loss = criterion(pred[mask_tr], Y_tr[mask_tr])
                loss.backward()
                torch.nn.utils.clip_grad_norm_(module.parameters(), 1.0)
                optimizer.step()

                # --- Validate ---
                module.eval()
                with torch.no_grad():
                    with torch.autocast(
                        device_type=dev.split(":")[0],
                        dtype=amp_dtype,
                        enabled=amp_dtype is not None,
                    ):
                        val_pred = module(X_val)
                        val_loss = criterion(val_pred[mask_val], Y_val[mask_val]).item()

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    best_state = {
                        k: v.detach().cpu().clone() for k, v in module.state_dict().items()
                    }
                else:
                    patience_counter += 1

                if on_progress is not None:
                    on_progress(global_epoch, total_epochs)

                if patience_counter >= self.early_stopping_rounds:
                    remaining = self.max_epochs - epoch
                    global_epoch += remaining
                    if on_progress is not None and remaining > 0:
                        on_progress(global_epoch, total_epochs)
                    break

            if best_state is not None:
                module.load_state_dict(best_state)
                module.to(dev)
            module.eval()
            self._modules_.append(module)
            val_losses_all.append(best_val_loss)

        self.epochs_run_ = global_epoch
        self.best_val_loss_ = float(np.mean(val_losses_all))
        return self

    # ------------------------------------------------------------------
    # _graph_channel: learned-adjacency contribution (for nesting test)
    # ------------------------------------------------------------------

    def _graph_channel(self, graphs: list[dict[str, Any]]) -> np.ndarray:
        """Return only the gamma-channel output (zero when top_k=0)."""
        if not self._modules_:
            raise RuntimeError("_graph_channel called before fit")
        n = self._n_nodes
        f = self.input_dim
        X = torch.tensor(
            np.stack([g["x"][:, :f] for g in graphs]), dtype=torch.float32
        ).to(self.device)

        contribs = []
        for module in self._modules_:
            module.eval()
            with torch.no_grad():
                a = module.adj()
                h = torch.relu(torch.einsum("ij,tjf->tif", a, module.theta(X)))
                contrib = module.gamma(h).squeeze(-1)
            contribs.append(contrib.cpu().numpy())
        return np.mean(contribs, axis=0)

    # ------------------------------------------------------------------
    # predict
    # ------------------------------------------------------------------

    def predict(self, graphs: list[dict[str, Any]]) -> np.ndarray:
        """Predict log-RV for each node in each graph.

        Returns
        -------
        np.ndarray, shape (T*N,) — predictions flattened node-major per date.
        """
        if not self._modules_:
            raise RuntimeError("predict called before fit")
        n = self._n_nodes
        f = self.input_dim
        X = torch.tensor(
            np.stack([g["x"][:, :f] for g in graphs]), dtype=torch.float32
        ).to(self.device)

        preds = []
        for module in self._modules_:
            module.eval()
            with torch.no_grad():
                pred = module(X)
            preds.append(pred.cpu().numpy())
        return np.mean(preds, axis=0).reshape(-1)

    # ------------------------------------------------------------------
    # learned_adjacency inspection
    # ------------------------------------------------------------------

    def learned_adjacency(self, symbols: list[str] | None = None) -> pd.DataFrame:
        """Return the learned adjacency as a DataFrame (mean over seeds).

        Parameters
        ----------
        symbols : optional list of symbol names for index/columns.
        """
        if not self._modules_:
            raise RuntimeError("learned_adjacency called before fit")
        adjs = [m.learned_adj_numpy() for m in self._modules_]
        mean_adj = np.mean(adjs, axis=0)
        n = mean_adj.shape[0]
        if symbols is None:
            symbols = [f"node_{i}" for i in range(n)]
        return pd.DataFrame(mean_adj, index=symbols, columns=symbols)

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
        if not self._modules_:
            raise RuntimeError("GNNLearnedAdjModel.save called before fit")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "init_kwargs": self.get_params(),
            "state_dicts": [
                {k: v.detach().cpu() for k, v in m.state_dict().items()}
                for m in self._modules_
            ],
            "n_nodes": self._n_nodes,
            "epochs_run": self.epochs_run_,
            "best_val_loss": self.best_val_loss_,
        }
        tmp = path.with_suffix(path.suffix + ".tmp")
        torch.save(payload, tmp)
        os.replace(tmp, path)
        return path

    @classmethod
    def load(cls, path: Path) -> "GNNLearnedAdjModel":
        payload = torch.load(Path(path), map_location="cpu", weights_only=False)
        instance = cls(**payload["init_kwargs"])
        instance._n_nodes = payload["n_nodes"]
        n = instance._n_nodes
        f = instance.input_dim
        instance._modules_ = []
        for sd in payload["state_dicts"]:
            module = _GNNLearnedModule(
                n, f, instance.hidden_dim, instance.embed_dim,
                instance.top_k, instance.alpha,
            )
            module.load_state_dict(sd)
            module.eval()
            instance._modules_.append(module)
        instance.epochs_run_ = payload.get("epochs_run", 0)
        instance.best_val_loss_ = payload.get("best_val_loss")
        return instance

    # ------------------------------------------------------------------
    # params / summary
    # ------------------------------------------------------------------

    def get_params(self) -> dict[str, Any]:
        return {
            "input_dim": self.input_dim,
            "hidden_dim": self.hidden_dim,
            "embed_dim": self.embed_dim,
            "top_k": self.top_k,
            "alpha": self.alpha,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "max_epochs": self.max_epochs,
            "early_stopping_rounds": self.early_stopping_rounds,
            "val_fraction": self.val_fraction,
            "loss": self.loss,
            "n_seeds": self.n_seeds,
            "device": self.device,
            "precision": self.precision,
            "seed": self.seed,
        }

    def get_arch_summary(self) -> dict[str, Any]:
        param_count = None
        if self._modules_:
            param_count = sum(p.numel() for p in self._modules_[0].parameters())
        return {
            "hidden_dim": self.hidden_dim,
            "embed_dim": self.embed_dim,
            "top_k": self.top_k,
            "alpha": self.alpha,
            "n_seeds": self.n_seeds,
            "loss": self.loss,
            "epochs_trained": self.epochs_run_,
            "best_val_loss": self.best_val_loss_,
            "param_count": param_count,
        }

    @property
    def summary(self) -> dict[str, float]:
        s = self.get_arch_summary()
        return {k: float(v) for k, v in s.items() if v is not None and isinstance(v, (int, float))}
