"""Regime-blend graph: split estimation window into calm/stress, build per-regime graphs."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from volforecast.graphs.base import GraphSnapshot, empty_snapshot
from volforecast.graphs.correlation import CorrGraphBuilder
from volforecast.graphs.glasso import GlassoGraphBuilder
from volforecast.registry import register_graph

_BASES = {"corr": CorrGraphBuilder, "glasso": GlassoGraphBuilder}


@register_graph("regime_blend")
class RegimeBlendGraphBuilder:
    """Build a base graph on calm/stress subsets, blend by window-end regime state."""

    directed = False

    def __init__(
        self,
        base: str = "corr",
        quantile: float = 0.75,
        blend: str = "hard",
        min_rows: int = 60,
        **base_params: Any,
    ) -> None:
        if base not in _BASES:
            raise ValueError(f"Unknown base {base!r}; expected one of {sorted(_BASES)}")
        self.base_name = base
        self.quantile = float(quantile)
        self.blend = blend
        self.min_rows = int(min_rows)
        self._base_params = base_params
        self._base_cls = _BASES[base]

    def build(
        self, returns: pd.DataFrame, date: Any, symbols: list[str]
    ) -> GraphSnapshot:
        data = returns[list(symbols)].dropna(how="all")
        if len(data) < 22:
            return empty_snapshot(symbols, date, method="regime_blend")

        # Observable-state regime classification (fully PIT)
        trailing_disp = data.pow(2).mean(axis=1).rolling(22).mean()
        trailing_disp = trailing_disp.dropna()
        if len(trailing_disp) < 2:
            return empty_snapshot(symbols, date, method="regime_blend")

        threshold = trailing_disp.quantile(self.quantile)
        stress_mask = trailing_disp > threshold
        calm_mask = ~stress_mask

        stress_dates = stress_mask.index[stress_mask]
        calm_dates = calm_mask.index[calm_mask]

        # Fallback: if either regime has insufficient data, use full window
        if len(stress_dates) < self.min_rows or len(calm_dates) < self.min_rows:
            base_builder = self._base_cls(**self._base_params)
            snap = base_builder.build(data, date, symbols)
            return GraphSnapshot(
                edge_index=snap.edge_index,
                edge_weight=snap.edge_weight,
                symbols=snap.symbols,
                date=date,
                directed=False,
                method="regime_blend",
            )

        base_builder = self._base_cls(**self._base_params)
        snap_calm = base_builder.build(data.loc[calm_dates], date, symbols)
        snap_stress = base_builder.build(data.loc[stress_dates], date, symbols)

        # Window-end state: is the last trailing_disp date stress or calm?
        window_end_stress = bool(stress_mask.iloc[-1])

        if self.blend == "hard":
            chosen = snap_stress if window_end_stress else snap_calm
            return GraphSnapshot(
                edge_index=chosen.edge_index,
                edge_weight=chosen.edge_weight,
                symbols=tuple(symbols),
                date=date,
                directed=False,
                method="regime_blend",
            )

        # Default fallback (unknown blend mode) — treat as hard
        chosen = snap_stress if window_end_stress else snap_calm
        return GraphSnapshot(
            edge_index=chosen.edge_index,
            edge_weight=chosen.edge_weight,
            symbols=tuple(symbols),
            date=date,
            directed=False,
            method="regime_blend",
        )
