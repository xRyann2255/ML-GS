"""GNNHAR: one-hop nonlinear graph HAR (Zhang, Pu, Cucuringu & Dong 2025, eqs. 7-8).

H^{l+1} = ReLU(W H^l Theta^l),  W = O^-1/2 A O^-1/2 with ZERO diagonal,  H^0 = X
y-hat   = alpha + X beta + H^L gamma      (alpha per asset; beta, gamma pooled)

The graph channel models spillovers only; own-lag dynamics stay linear (paper
footnote 8: nonlinearity in the own channel was found unhelpful). Empty graph
=> W = 0 => the model IS a QLIKE-trained pooled HAR — the nesting that lets the
Plan-04 experiment attribute gains to (a) the graph and (b) the nonlinearity.
Protocol extras from the paper: hidden dim 9, Adam + early stopping, and
prediction averaging over ``n_seeds`` seed-varied fits.
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

_MAX_OOM_RETRIES = 2


# ---------------------------------------------------------------------------
# Dense propagation matrix (spillover-only: zero diagonal)
# ---------------------------------------------------------------------------


def _build_w_batch(graphs: list[dict[str, Any]], n: int) -> torch.Tensor:
    """(T, N, N) stack of sym-normalized, zero-diagonal dense propagation matrices."""
    ws = torch.zeros(len(graphs), n, n)
    for t, g in enumerate(graphs):
        ei, ea = g["edge_index"], g["edge_attr"]
        if ei.numel() == 0:
            continue
        a = torch.zeros(n, n)
        a[ei[0], ei[1]] = ea.float()
        a.fill_diagonal_(0.0)  # spillover-only channel
        deg = a.sum(1)
        inv_sqrt = torch.where(deg > 0, deg.rsqrt(), torch.zeros_like(deg))
        ws[t] = inv_sqrt[:, None] * a * inv_sqrt[None, :]
    return ws


# ---------------------------------------------------------------------------
# PyTorch nn.Module
# ---------------------------------------------------------------------------


class _GNNHARModule(nn.Module):
    """GCN propagation layers + linear HAR readout."""

    def __init__(self, n_nodes: int, input_dim: int, hidden_dim: int, n_layers: int) -> None:
        super().__init__()
        dims = [input_dim] + [hidden_dim] * n_layers
        self.thetas = nn.ModuleList(
            nn.Linear(dims[k], dims[k + 1], bias=False) for k in range(n_layers)
        )
        self.alpha = nn.Parameter(torch.zeros(n_nodes))
        self.beta = nn.Linear(input_dim, 1, bias=False)
        self.gamma = nn.Linear(hidden_dim, 1, bias=False)

    def forward(
        self, x: torch.Tensor, w: torch.Tensor, *, return_embedding: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
        """Forward pass.

        Parameters
        ----------
        x : (T, N, F) node features
        w : (T, N, N) propagation matrices
        return_embedding : if True, also return H^L before readout

        Returns
        -------
        pred : (T, N) per-node predictions
        embedding : (T, N, hidden_dim) final hidden state (if return_embedding=True)
        """
        h = x
        for theta in self.thetas:
            h = torch.relu(torch.bmm(w, theta(h)))
        # Readout: alpha (per asset) + X beta (pooled) + H^L gamma (pooled)
        pred = self.alpha[None, :] + self.beta(x).squeeze(-1) + self.gamma(h).squeeze(-1)
        if return_embedding:
            return pred, h
        return pred


# ---------------------------------------------------------------------------
# Registered model class
# ---------------------------------------------------------------------------


@register_model("gnnhar")
class GNNHARVolModel(_BaseModel):
    """GNNHAR: no-self-loop GCN spillover channel + linear HAR channel.

    Set ``requires_graph = True`` so the pipeline runner dispatches graph dicts.
    """

    REQUIRED_LAYERS: list[str] = ["har_core"]
    requires_sequences: bool = False
    requires_graph: bool = True
    supports_tuning: bool = True
    family = "gnn"
    description = "GNNHAR: no-self-loop GCN spillover channel + linear HAR channel"

    def __init__(
        self,
        *,
        input_dim: int,
        hidden_dim: int = 9,
        n_layers: int = 1,
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
        self.n_layers = int(n_layers)
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

        self._modules_: list[_GNNHARModule] = []
        self._n_nodes: int | None = None
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
    ) -> "GNNHARVolModel":
        """Train GNNHAR on a list of graph snapshots.

        Parameters
        ----------
        graphs : list[dict]
            Each dict: "x" (N, F), "edge_index" (2, E), "edge_attr" (E,), "y" (N,), "date".
        y : ignored (targets in graph dicts)
        on_progress : callable(current_epoch, total_epochs), optional
        """
        if not graphs:
            raise ValueError("GNNHAR: no graphs to fit")

        n = graphs[0]["x"].shape[0]
        f = self.input_dim
        self._n_nodes = n

        # Stack data tensors
        X = torch.tensor(
            np.stack([g["x"][:, :f] for g in graphs]), dtype=torch.float32
        )  # (T, N, F)
        Y = torch.tensor(np.stack([g["y"] for g in graphs]), dtype=torch.float32)  # (T, N)
        W = _build_w_batch(graphs, n)  # (T, N, N)

        # Finite mask
        mask = torch.isfinite(Y)

        # Temporal val split
        t_total = len(graphs)
        n_val = max(1, int(math.ceil(t_total * self.val_fraction)))
        n_train = t_total - n_val

        X_tr, X_val = X[:n_train], X[n_train:]
        Y_tr, Y_val = Y[:n_train], Y[n_train:]
        W_tr, W_val = W[:n_train], W[n_train:]
        mask_tr, mask_val = mask[:n_train], mask[n_train:]

        # Move to device
        dev = self.device
        X_tr, X_val = X_tr.to(dev), X_val.to(dev)
        Y_tr, Y_val = Y_tr.to(dev), Y_val.to(dev)
        W_tr, W_val = W_tr.to(dev), W_val.to(dev)
        mask_tr, mask_val = mask_tr.to(dev), mask_val.to(dev)

        amp_dtype = _resolve_precision(self.precision, dev)
        criterion = _LOSSES[self.loss]
        total_epochs = self.n_seeds * self.max_epochs
        global_epoch = 0
        val_losses_all = []

        self._modules_ = []

        for s in range(self.n_seeds):
            self._set_seed(self.seed + s)
            module = _GNNHARModule(n, f, self.hidden_dim, self.n_layers).to(dev)
            optimizer = torch.optim.Adam(
                module.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay
            )

            best_val_loss = float("inf")
            patience_counter = 0
            best_state: dict[str, Any] | None = None
            _oom_retries = 0

            for epoch in range(1, self.max_epochs + 1):
                global_epoch += 1

                # --- Train ---
                module.train()
                optimizer.zero_grad()
                try:
                    with torch.autocast(
                        device_type=dev.split(":")[0],
                        dtype=amp_dtype,
                        enabled=amp_dtype is not None,
                    ):
                        pred = module(X_tr, W_tr)
                        loss = criterion(pred[mask_tr], Y_tr[mask_tr])
                    loss.backward()
                except torch.cuda.OutOfMemoryError:
                    _oom_retries += 1
                    if _oom_retries > _MAX_OOM_RETRIES:
                        raise
                    torch.cuda.empty_cache()
                    logger.warning(
                        "GNNHAR CUDA OOM at seed %d epoch %d (retry %d/%d)",
                        s, epoch, _oom_retries, _MAX_OOM_RETRIES,
                    )
                    continue
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
                        val_pred = module(X_val, W_val)
                        val_loss = criterion(val_pred[mask_val], Y_val[mask_val]).item()

                # Early stopping
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
                    # Advance global_epoch counter for remaining epochs (for progress reporting)
                    remaining = self.max_epochs - epoch
                    global_epoch += remaining
                    if on_progress is not None and remaining > 0:
                        on_progress(global_epoch, total_epochs)
                    break

            # Restore best weights
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
    # _graph_channel: spillover contribution only (for testing nesting)
    # ------------------------------------------------------------------

    def _graph_channel(self, graphs: list[dict[str, Any]]) -> np.ndarray:
        """Return only the gamma-channel output (zero on empty graphs)."""
        if not self._modules_:
            raise RuntimeError("_graph_channel called before fit")
        n = self._n_nodes
        f = self.input_dim
        X = torch.tensor(
            np.stack([g["x"][:, :f] for g in graphs]), dtype=torch.float32
        )
        W = _build_w_batch(graphs, n)
        dev = self.device
        X, W = X.to(dev), W.to(dev)

        contribs = []
        for module in self._modules_:
            module.eval()
            with torch.no_grad():
                h = X
                for theta in module.thetas:
                    h = torch.relu(torch.bmm(W, theta(h)))
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
        )
        W = _build_w_batch(graphs, n)
        dev = self.device
        X, W = X.to(dev), W.to(dev)

        preds = []
        for module in self._modules_:
            module.eval()
            with torch.no_grad():
                pred = module(X, W)
            preds.append(pred.cpu().numpy())
        # Mean over seeds, then flatten (T, N) -> (T*N,)
        return np.mean(preds, axis=0).reshape(-1)

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

        valid_outputs = {"prediction", "embedding"}
        invalid = set(outputs) - valid_outputs
        if invalid:
            raise ValueError(f"Invalid outputs: {invalid}. Valid: {valid_outputs}")

        result: dict[str, np.ndarray] = {}
        need_embedding = "embedding" in outputs

        if "prediction" in outputs and not need_embedding:
            result["prediction"] = self.predict(graphs)
        elif "prediction" in outputs or need_embedding:
            # Run forward with embedding to avoid duplicate forward passes
            if not self._modules_:
                raise RuntimeError("extract_features called before fit")
            n = self._n_nodes
            f = self.input_dim
            X = torch.tensor(
                np.stack([g["x"][:, :f] for g in graphs]), dtype=torch.float32
            )
            W = _build_w_batch(graphs, n)
            dev = self.device
            X, W = X.to(dev), W.to(dev)

            all_preds = []
            all_embeddings = []
            for module in self._modules_:
                module.eval()
                with torch.no_grad():
                    pred, h = module(X, W, return_embedding=True)
                all_preds.append(pred.cpu().numpy())
                all_embeddings.append(h.cpu().numpy())

            if "prediction" in outputs:
                result["prediction"] = np.mean(all_preds, axis=0).reshape(-1)
            if need_embedding:
                # Mean over seeds, then reshape (T, N, D) -> (T*N, D)
                mean_emb = np.mean(all_embeddings, axis=0)
                t, nn, d = mean_emb.shape
                result["embedding"] = mean_emb.reshape(t * nn, d).astype(np.float32)

        return result

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    def save(self, path: Path) -> Path:
        if not self._modules_:
            raise RuntimeError("GNNHARVolModel.save called before fit")
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
    def load(cls, path: Path) -> "GNNHARVolModel":
        payload = torch.load(Path(path), map_location="cpu", weights_only=False)
        instance = cls(**payload["init_kwargs"])
        instance._n_nodes = payload["n_nodes"]
        n = instance._n_nodes
        f = instance.input_dim
        instance._modules_ = []
        for sd in payload["state_dicts"]:
            module = _GNNHARModule(n, f, instance.hidden_dim, instance.n_layers)
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
            "n_layers": self.n_layers,
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
            "n_layers": self.n_layers,
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

    # ------------------------------------------------------------------
    # tune_and_fit: HPO then fit with best params
    # ------------------------------------------------------------------

    def tune_and_fit(
        self,
        graphs: list[dict[str, Any]],
        *,
        dates: list,
        y_panel: Any,
        symbols: list[str],
        node_cols: list[str],
        tuning_config: Any,
        cv_config: Any,
        progress_queue: Any | None = None,
        **kwargs: Any,
    ) -> "GNNHARVolModel":
        """Tune hyperparameters then fit with best params."""
        from volforecast.models.gnn_tuning import GNNHAR_SEARCH_SPACE, tune_gnn_hyperparameters

        search_space = getattr(tuning_config, "search_space", None) or GNNHAR_SEARCH_SPACE
        fixed = self.get_params()
        for key in search_space:
            fixed.pop(key, None)

        best = tune_gnn_hyperparameters(
            graphs_all=graphs,
            dates=dates,
            y_panel=y_panel,
            symbols=symbols,
            node_cols=node_cols,
            cv_config=cv_config,
            n_trials=tuning_config.n_trials,
            n_gpus=getattr(tuning_config, "n_gpus", 1),
            seed=self.seed,
            model_name="gnnhar",
            fixed_params=fixed,
            storage_dir=Path(tuning_config.storage_dir) if tuning_config.storage_dir else None,
            progress_queue=progress_queue,
            search_space=search_space,
        )
        for k, v in best.items():
            if hasattr(self, k):
                setattr(self, k, v)
        return self.fit(graphs, **kwargs)
