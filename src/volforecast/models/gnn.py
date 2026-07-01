"""Graph Attention Network (GAT) for multi-symbol realized volatility forecasting.

Architecture (Zhang, Pu, Cucuringu & Dong 2025):
  - Each training sample = one graph snapshot (N nodes × F features)
  - Nodes = symbols in the universe
  - Edges = rolling correlation above threshold (from gnn_adjacency module)
  - 2-layer GATv2Conv with multi-head attention
  - Per-node MLP head → log-RV prediction

Key design choices:
  - One-hop only (multi-hop adds noise per Zhang et al.)
  - QLIKE loss (substantially outperforms MSE per Zhang et al.)
  - Node features are same daily features used by LSTM (log_rv_d/w/m, etc.)
  - Integrates with feature_stack pipeline via extract_features()

Unlike LSTM (temporal sequences), GNN operates on spatial (cross-asset)
structure. Each date produces one graph; the model learns how volatility
propagates across the asset network.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from volforecast.models._base import _BaseModel
from volforecast.registry import register_model

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Loss functions (same as LSTM for consistency)
# ---------------------------------------------------------------------------


def _mse_loss(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    return torch.mean((pred - target) ** 2)


def _qlike_loss(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """QLIKE in log-RV space: exp(y - y_hat) - (y - y_hat) - 1."""
    diff = target - pred
    diff = torch.clamp(diff, min=-10.0, max=10.0)
    return torch.mean(torch.exp(diff) - diff - 1.0)


_LOSSES = {"mse": _mse_loss, "qlike": _qlike_loss}


# ---------------------------------------------------------------------------
# Device / precision helpers (shared with lstm.py pattern)
# ---------------------------------------------------------------------------


def _resolve_device(device: str) -> str:
    if device != "auto":
        return device
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _resolve_precision(precision: str, device: str) -> torch.dtype | None:
    if precision == "fp32" or device == "cpu":
        return None
    if precision == "bf16":
        return torch.bfloat16
    if precision == "fp16":
        return torch.float16
    if precision == "auto":
        if device == "cuda":
            return torch.bfloat16
        return None
    raise ValueError(f"Unknown precision: {precision!r}")


# ---------------------------------------------------------------------------
# PyTorch Geometric nn.Module
# ---------------------------------------------------------------------------


class _GATModule(nn.Module):
    """2-layer GATv2 + per-node MLP head."""

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 32,
        n_heads: int = 4,
        dropout: float = 0.1,
        edge_dim: int = 1,
    ) -> None:
        super().__init__()
        from torch_geometric.nn import GATv2Conv

        # Layer 1: input_dim → hidden_dim * n_heads (concat heads)
        self.conv1 = GATv2Conv(
            input_dim,
            hidden_dim,
            heads=n_heads,
            dropout=dropout,
            edge_dim=edge_dim,
            concat=True,
        )
        # Layer 2: hidden_dim * n_heads → hidden_dim (average heads)
        self.conv2 = GATv2Conv(
            hidden_dim * n_heads,
            hidden_dim,
            heads=n_heads,
            dropout=dropout,
            edge_dim=edge_dim,
            concat=False,  # average over heads → output is hidden_dim
        )
        # Per-node MLP head: hidden_dim → hidden_dim//2 → 1
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
        )
        self.dropout = nn.Dropout(dropout)
        self.elu = nn.ELU()

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor | None = None,
        return_attention: bool = False,
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        """Forward pass.

        Parameters
        ----------
        x : (N, F) node features
        edge_index : (2, E) edge COO indices
        edge_attr : (E, 1) edge weights (optional)

        Returns
        -------
        out : (N, 1) per-node predictions
        attn_weights : (E, H) attention weights from layer 2 (if return_attention=True)
        """
        # Layer 1
        h = self.conv1(x, edge_index, edge_attr=edge_attr)
        h = self.elu(h)
        h = self.dropout(h)

        # Layer 2 — optionally return attention weights
        if return_attention:
            h, (edge_idx_out, attn_weights) = self.conv2(
                h, edge_index, edge_attr=edge_attr, return_attention_weights=True
            )
        else:
            h = self.conv2(h, edge_index, edge_attr=edge_attr)
            attn_weights = None

        h = self.elu(h)
        h = self.dropout(h)

        # Per-node prediction
        out = self.head(h)
        return out, attn_weights


# ---------------------------------------------------------------------------
# Registered model class
# ---------------------------------------------------------------------------


@register_model("gnn")
class GNNVolModel(_BaseModel):
    """Graph Attention Network for multi-symbol RV forecasting.

    Operates on graph snapshots: each date = one graph with N nodes
    (symbols) and edges from rolling correlation. Integrates with the
    feature_stack pipeline via extract_features().

    Set ``requires_graph = True`` so the pipeline runner can detect
    graph-mode and dispatch appropriately.
    """

    REQUIRED_LAYERS: list[str] = []
    requires_sequences: bool = False  # Does NOT use SequenceTensor
    requires_graph: bool = True  # New flag for pipeline detection
    supports_tuning: bool = False
    name = "gnn"
    family = "gnn"
    description = "Graph Attention Network with cross-asset spillover learning"

    def __init__(
        self,
        *,
        input_dim: int,
        hidden_dim: int = 32,
        n_heads: int = 4,
        n_layers: int = 2,
        dropout: float = 0.1,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        max_epochs: int = 200,
        batch_size: int = 32,
        val_fraction: float = 0.15,
        early_stopping_rounds: int = 15,
        loss: str = "qlike",
        adj_window: int = 60,
        adj_threshold: float = 0.3,
        device: str = "auto",
        precision: str = "auto",
        seed: int = 42,
        use_scheduler: bool = True,
        grad_accumulation_steps: int = 1,
        compile: bool = False,  # PyG ops are dynamic; compile causes CUDA Graph warnings
    ) -> None:
        if loss not in _LOSSES:
            raise ValueError(f"Unknown loss {loss!r}; expected one of {list(_LOSSES)}")

        self.input_dim = int(input_dim)
        self.hidden_dim = int(hidden_dim)
        self.n_heads = int(n_heads)
        self.n_layers = int(n_layers)
        self.dropout = float(dropout)
        self.learning_rate = float(learning_rate)
        self.weight_decay = float(weight_decay)
        self.max_epochs = int(max_epochs)
        self.batch_size = int(batch_size)
        self.val_fraction = float(val_fraction)
        self.early_stopping_rounds = int(early_stopping_rounds)
        self.loss = loss
        self.adj_window = int(adj_window)
        self.adj_threshold = float(adj_threshold)
        self.device = _resolve_device(device)
        self.precision = precision
        self.seed = int(seed)
        self.use_scheduler = bool(use_scheduler)
        self.grad_accumulation_steps = max(1, int(grad_accumulation_steps))
        self.compile = bool(compile)

        self._module: _GATModule | None = None
        self.epochs_run_: int = 0
        self.best_val_loss_: float | None = None
        self.history_: list[dict[str, float]] = []
        # Symbol ordering (set during fit, required for predict)
        self._symbol_order: list[str] | None = None

    def _set_seed(self) -> None:
        torch.manual_seed(self.seed)
        np.random.seed(self.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.seed)

    def _build_module(self) -> _GATModule:
        return _GATModule(
            input_dim=self.input_dim,
            hidden_dim=self.hidden_dim,
            n_heads=self.n_heads,
            dropout=self.dropout,
            edge_dim=1,
        )

    # ------------------------------------------------------------------
    # fit: train on graph snapshots
    # ------------------------------------------------------------------

    def fit(
        self,
        graphs: list[dict[str, Any]],
        y: np.ndarray | None = None,
        *,
        on_progress: Any | None = None,
    ) -> "GNNVolModel":
        """Train GNN on a list of graph snapshots.

        Parameters
        ----------
        graphs : list[dict]
            Each dict represents one date's graph:
            - "x": np.ndarray (N, F) node features
            - "edge_index": torch.Tensor (2, E)
            - "edge_attr": torch.Tensor (E,) edge weights
            - "y": np.ndarray (N,) per-node log-RV targets
            - "date": pd.Timestamp (optional, for logging)
        y : ignored (targets are in each graph dict)
        on_progress : callable, optional
            Called as on_progress(epoch, max_epochs) per epoch.
        """
        from torch_geometric.data import Data
        from torch_geometric.loader import DataLoader as PyGLoader

        self._set_seed()
        if self.device.startswith("cuda"):
            torch.set_float32_matmul_precision("high")

        # 4a: Accept pre-built Data objects — skip conversion if already Data
        _is_pyg = len(graphs) > 0 and hasattr(graphs[0], "x")

        # Filter out graphs with no valid targets (keep graphs with 0 edges
        # — isolated nodes can still learn via the MLP head)
        valid_graphs = []
        for g in graphs:
            y_g = g.y.numpy() if _is_pyg else g["y"]
            if np.all(np.isnan(y_g)):
                continue
            valid_graphs.append(g)

        if not valid_graphs:
            raise ValueError("No valid graphs for training (all have NaN targets)")

        n_total = len(valid_graphs)
        n_val = max(1, int(n_total * self.val_fraction))
        n_train = n_total - n_val

        # Temporal split: most recent dates as validation
        train_graphs = valid_graphs[:n_train]
        val_graphs = valid_graphs[n_train:]

        # Convert to PyG Data objects (skip if already Data)
        def _to_pyg(g: dict) -> Data:
            x = torch.tensor(g["x"], dtype=torch.float32)
            edge_index = g["edge_index"].clone()
            edge_attr = g["edge_attr"].clone().unsqueeze(-1)  # (E,) → (E, 1)
            y_t = torch.tensor(g["y"], dtype=torch.float32)
            mask = ~torch.isnan(y_t)
            return Data(x=x, edge_index=edge_index, edge_attr=edge_attr, y=y_t, mask=mask)

        if _is_pyg:
            train_data = list(train_graphs)
            val_data = list(val_graphs)
        else:
            train_data = [_to_pyg(g) for g in train_graphs]
            val_data = [_to_pyg(g) for g in val_graphs]

        # 4b: Batching strategy — for small graph datasets (typical in vol
        # forecasting: ~2800 dates × 21 nodes), pre-batch ALL data onto GPU
        # to eliminate DataLoader/IPC/transfer overhead that dominates for tiny models.
        # Only fall back to DataLoader for large datasets (>10K graphs).
        _use_dataloader = len(train_data) > 10000

        if _use_dataloader:
            train_loader = PyGLoader(
                train_data, batch_size=self.batch_size, shuffle=True,
                pin_memory=False, num_workers=0,
            )
            val_loader = PyGLoader(
                val_data, batch_size=self.batch_size, shuffle=False,
                pin_memory=False, num_workers=0,
            )
        else:
            # Pre-batch everything and move to device ONCE
            # This eliminates per-epoch CPU→GPU transfer overhead
            from torch_geometric.data import Batch as _Batch

            _all_train_batch = _Batch.from_data_list(train_data).to(self.device)
            _all_val_batch = _Batch.from_data_list(val_data).to(self.device) if val_data else None
            # Build batch index lists for mini-batch slicing within the mega-batch
            # (shuffle per epoch by permuting graph indices)
            _n_train_graphs = len(train_data)
            _n_val_graphs = len(val_data)
            train_loader = None  # signal to use pre-batched path
            val_loader = None

        # Build model
        self._module = self._build_module().to(self.device)

        logger.info(
            "GNN: training on device=%s, %d train graphs, %d val graphs",
            self.device, len(train_data), len(val_data),
        )

        # 4e: torch.compile on CUDA with graceful fallback
        # NOTE: PyG's message-passing ops are dynamic (variable nodes/edges per
        # batch). torch.compile may emit CUDA Graph warnings. Disabled by default.
        if self.compile and self.device.startswith("cuda"):
            _torch_major = int(torch.__version__.split(".")[0])
            if _torch_major >= 2:
                try:
                    self._module = torch.compile(self._module, mode="default")
                    logger.info("GNN: torch.compile enabled (default mode)")
                except Exception as exc:
                    logger.warning("GNN: torch.compile failed, using eager mode: %s", exc)

        optimizer = torch.optim.AdamW(
            self._module.parameters(),
            lr=self.learning_rate,
            weight_decay=self.weight_decay,
        )

        # 4c: OneCycleLR scheduler (per-step)
        scheduler = None
        if self.use_scheduler:
            steps_per_epoch = max(1, len(train_loader)) if train_loader is not None else 1
            scheduler = torch.optim.lr_scheduler.OneCycleLR(
                optimizer,
                max_lr=self.learning_rate,
                epochs=self.max_epochs,
                steps_per_epoch=steps_per_epoch,
            )

        criterion = _LOSSES[self.loss]
        amp_dtype = _resolve_precision(self.precision, self.device)

        best_val_loss = float("inf")
        patience_counter = 0
        best_state = None
        accum = self.grad_accumulation_steps

        for epoch in range(1, self.max_epochs + 1):
            # ---- Train ----
            self._module.train()
            train_losses = []

            if train_loader is not None:
                # DataLoader path (large datasets only)
                optimizer.zero_grad()
                for batch_idx, batch in enumerate(train_loader):
                    batch = batch.to(self.device)
                    with torch.autocast(
                        device_type=self.device.split(":")[0],
                        dtype=amp_dtype,
                        enabled=amp_dtype is not None,
                    ):
                        pred, _ = self._module(batch.x, batch.edge_index, batch.edge_attr)
                        pred = pred.squeeze(-1)
                        mask = batch.mask
                        loss = criterion(pred[mask], batch.y[mask])
                        scaled_loss = loss / accum

                    scaled_loss.backward()

                    if (batch_idx + 1) % accum == 0 or (batch_idx + 1) == len(train_loader):
                        torch.nn.utils.clip_grad_norm_(self._module.parameters(), 1.0)
                        optimizer.step()
                        if scheduler is not None:
                            scheduler.step()
                        optimizer.zero_grad()

                    train_losses.append(loss.item())
            else:
                # Pre-batched path: ALL training data already on GPU as one mega-batch.
                # Process in one forward pass (58K nodes is tiny for H100).
                optimizer.zero_grad()
                with torch.autocast(
                    device_type=self.device.split(":")[0],
                    dtype=amp_dtype,
                    enabled=amp_dtype is not None,
                ):
                    pred, _ = self._module(
                        _all_train_batch.x, _all_train_batch.edge_index, _all_train_batch.edge_attr
                    )
                    pred = pred.squeeze(-1)
                    mask = _all_train_batch.mask
                    loss = criterion(pred[mask], _all_train_batch.y[mask])

                loss.backward()
                torch.nn.utils.clip_grad_norm_(self._module.parameters(), 1.0)
                optimizer.step()
                if scheduler is not None:
                    scheduler.step()
                optimizer.zero_grad()
                train_losses.append(loss.item())

            # ---- Validate ----
            self._module.eval()
            val_losses = []
            with torch.no_grad():
                if val_loader is not None:
                    for batch in val_loader:
                        batch = batch.to(self.device)
                        with torch.autocast(
                            device_type=self.device.split(":")[0],
                            dtype=amp_dtype,
                            enabled=amp_dtype is not None,
                        ):
                            pred, _ = self._module(batch.x, batch.edge_index, batch.edge_attr)
                            pred = pred.squeeze(-1)
                            mask = batch.mask
                            loss = criterion(pred[mask], batch.y[mask])
                        val_losses.append(loss.item())
                elif _all_val_batch is not None:
                    with torch.autocast(
                        device_type=self.device.split(":")[0],
                        dtype=amp_dtype,
                        enabled=amp_dtype is not None,
                    ):
                        pred, _ = self._module(
                            _all_val_batch.x, _all_val_batch.edge_index, _all_val_batch.edge_attr
                        )
                        pred = pred.squeeze(-1)
                        mask = _all_val_batch.mask
                        loss = criterion(pred[mask], _all_val_batch.y[mask])
                    val_losses.append(loss.item())

            train_loss = float(np.mean(train_losses))
            val_loss = float(np.mean(val_losses)) if val_losses else train_loss

            self.history_.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss})

            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                best_state = {k: v.detach().cpu().clone() for k, v in self._module.state_dict().items()}
            else:
                patience_counter += 1

            if patience_counter >= self.early_stopping_rounds:
                logger.info(
                    "GNN early stopping at epoch %d (best val_loss=%.6f at epoch %d)",
                    epoch,
                    best_val_loss,
                    epoch - patience_counter,
                )
                break

            if on_progress is not None:
                on_progress(epoch, self.max_epochs)

        # Restore best weights
        if best_state is not None:
            self._module.load_state_dict(best_state)
            self._module.to(self.device)

        self.epochs_run_ = epoch
        self.best_val_loss_ = best_val_loss
        return self

    # ------------------------------------------------------------------
    # predict: per-node log-RV predictions
    # ------------------------------------------------------------------

    def predict(
        self,
        graphs: list[dict[str, Any]],
    ) -> np.ndarray:
        """Predict log-RV for each node in each graph.

        Parameters
        ----------
        graphs : list[dict]
            Same format as fit (but "y" key is optional/ignored).

        Returns
        -------
        np.ndarray, shape (total_nodes,)
            Predictions flattened in graph order: [graph0_node0, ..., graph0_nodeN,
            graph1_node0, ...]. Caller must know N_nodes_per_graph to unflatten.
        """
        from torch_geometric.data import Batch as _Batch, Data
        from torch_geometric.loader import DataLoader as PyGLoader

        if self._module is None:
            raise RuntimeError("predict called before fit")

        # 4a: Accept pre-built Data objects
        _is_pyg = len(graphs) > 0 and hasattr(graphs[0], "x")

        self._module.eval()
        amp_dtype = _resolve_precision(self.precision, self.device)

        # Convert dicts to Data if needed (inference: no y/mask needed)
        if _is_pyg:
            data_list = list(graphs)
        else:
            data_list = []
            for g in graphs:
                x = torch.tensor(g["x"], dtype=torch.float32)
                edge_index = g["edge_index"].clone()
                edge_attr = g["edge_attr"].clone().unsqueeze(-1)
                data_list.append(Data(x=x, edge_index=edge_index, edge_attr=edge_attr))

        # Single mega-batch on GPU for small data (eliminates transfer overhead)
        mega_batch = _Batch.from_data_list(data_list).to(self.device)
        with torch.no_grad():
            with torch.autocast(
                device_type=self.device.split(":")[0],
                dtype=amp_dtype,
                enabled=amp_dtype is not None,
            ):
                pred, _ = self._module(mega_batch.x, mega_batch.edge_index, mega_batch.edge_attr)

        return pred.squeeze(-1).cpu().float().numpy()

    # ------------------------------------------------------------------
    # extract_features: for feature_stack pipeline
    # ------------------------------------------------------------------

    def extract_features(
        self,
        graphs: list[dict[str, Any]],
        *,
        outputs: list[str] | None = None,
    ) -> dict[str, np.ndarray]:
        """Extract features for stacking into downstream tree model.

        Parameters
        ----------
        graphs : list[dict]
            Same format as fit/predict.
        outputs : list[str]
            Which features to extract:
            - "prediction": per-node log-RV forecast
            - "node_attention": mean attention weight received per node

        Returns
        -------
        dict[str, np.ndarray]
            Keys are output names, values are arrays of shape (total_nodes,).
        """
        from torch_geometric.data import Batch as _Batch, Data

        if self._module is None:
            raise RuntimeError("extract_features called before fit")
        if outputs is None:
            outputs = ["prediction"]

        valid_outputs = {"prediction", "node_attention"}
        invalid = set(outputs) - valid_outputs
        if invalid:
            raise ValueError(f"Invalid outputs: {invalid}. Valid: {valid_outputs}")

        need_attention = "node_attention" in outputs

        # 4a: Accept pre-built Data objects
        _is_pyg = len(graphs) > 0 and hasattr(graphs[0], "x")

        if _is_pyg:
            data_list = list(graphs)
        else:
            data_list = []
            for g in graphs:
                x = torch.tensor(g["x"], dtype=torch.float32)
                edge_index = g["edge_index"].clone()
                edge_attr = g["edge_attr"].clone().unsqueeze(-1)
                data_list.append(Data(x=x, edge_index=edge_index, edge_attr=edge_attr))

        # Single mega-batch on GPU (eliminates per-batch transfer overhead)
        mega_batch = _Batch.from_data_list(data_list).to(self.device)

        self._module.eval()
        amp_dtype = _resolve_precision(self.precision, self.device)

        with torch.no_grad():
            with torch.autocast(
                device_type=self.device.split(":")[0],
                dtype=amp_dtype,
                enabled=amp_dtype is not None,
            ):
                pred, attn_weights = self._module(
                    mega_batch.x, mega_batch.edge_index, mega_batch.edge_attr,
                    return_attention=need_attention,
                )

        all_preds = pred.squeeze(-1).cpu().float().numpy()

        result: dict[str, np.ndarray] = {}
        if "prediction" in outputs:
            result["prediction"] = all_preds

        if need_attention and attn_weights is not None:
            attn_mean = attn_weights.mean(dim=-1).cpu().float()
            total_nodes = mega_batch.x.shape[0]
            node_attn = torch.zeros(total_nodes)
            edge_dst = mega_batch.edge_index[1].cpu()
            node_attn.scatter_add_(0, edge_dst, attn_mean)
            in_degree = torch.zeros(total_nodes)
            in_degree.scatter_add_(0, edge_dst, torch.ones_like(attn_mean))
            in_degree = in_degree.clamp(min=1.0)
            node_attn = node_attn / in_degree
            result["node_attention"] = node_attn.numpy()
        elif "node_attention" in outputs:
            result["node_attention"] = np.zeros(all_preds.shape[0])

        return result

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    def save(self, path: Path) -> Path:
        if self._module is None:
            raise RuntimeError("GNNVolModel.save called before fit")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "init_kwargs": self.get_params(),
            "state_dict": {k: v.detach().cpu() for k, v in self._module.state_dict().items()},
            "epochs_run": self.epochs_run_,
            "best_val_loss": self.best_val_loss_,
            "symbol_order": self._symbol_order,
        }
        tmp = path.with_suffix(path.suffix + ".tmp")
        torch.save(payload, tmp)
        os.replace(tmp, path)
        return path

    @classmethod
    def load(cls, path: Path) -> "GNNVolModel":
        payload = torch.load(Path(path), map_location="cpu", weights_only=False)
        instance = cls(**payload["init_kwargs"])
        instance._module = instance._build_module()
        instance._module.load_state_dict(payload["state_dict"])
        instance.epochs_run_ = payload.get("epochs_run", 0)
        instance.best_val_loss_ = payload.get("best_val_loss")
        instance._symbol_order = payload.get("symbol_order")
        return instance

    # ------------------------------------------------------------------
    # params / summary
    # ------------------------------------------------------------------

    def get_params(self) -> dict[str, Any]:
        return {
            "input_dim": self.input_dim,
            "hidden_dim": self.hidden_dim,
            "n_heads": self.n_heads,
            "n_layers": self.n_layers,
            "dropout": self.dropout,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "max_epochs": self.max_epochs,
            "batch_size": self.batch_size,
            "val_fraction": self.val_fraction,
            "early_stopping_rounds": self.early_stopping_rounds,
            "loss": self.loss,
            "adj_window": self.adj_window,
            "adj_threshold": self.adj_threshold,
            "device": self.device,
            "precision": self.precision,
            "seed": self.seed,
            "use_scheduler": self.use_scheduler,
            "grad_accumulation_steps": self.grad_accumulation_steps,
            "compile": self.compile,
        }

    def get_arch_summary(self) -> dict[str, Any]:
        return {
            "hidden_dim": self.hidden_dim,
            "n_heads": self.n_heads,
            "n_layers": self.n_layers,
            "dropout": self.dropout,
            "loss": self.loss,
            "adj_window": self.adj_window,
            "adj_threshold": self.adj_threshold,
            "use_scheduler": self.use_scheduler,
            "grad_accumulation_steps": self.grad_accumulation_steps,
            "compile": self.compile,
            "epochs_trained": self.epochs_run_,
            "best_val_loss": self.best_val_loss_,
            "param_count": (
                sum(p.numel() for p in self._module.parameters()) if self._module else None
            ),
        }
