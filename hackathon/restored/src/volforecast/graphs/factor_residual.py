"""Factor-residual (idiosyncratic) graphs: build edges on what the market can't explain.

Design idea from Cartea, Cucuringu & Fang (2026, SSRN 6333798, abstract): idiosyncratic
spillover networks beat raw/market-based networks. Per-symbol OLS strips the factor;
a base builder (corr / glasso) runs on the residual panel.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from volforecast.graphs.base import GraphSnapshot, empty_snapshot
from volforecast.graphs.correlation import CorrGraphBuilder
from volforecast.graphs.glasso import GlassoGraphBuilder
from volforecast.registry import register_graph

_BASES = {"corr": CorrGraphBuilder, "glasso": GlassoGraphBuilder}


@register_graph("factor_residual")
class FactorResidualGraphBuilder:
    """OLS-strip a market factor, then delegate to a base graph builder on residuals."""

    directed = False

    def __init__(self, base: str = "corr", factor: str = "mean", **base_params: Any) -> None:
        if base not in _BASES:
            raise ValueError(f"Unknown base {base!r}; expected one of {sorted(_BASES)}")
        self.base_name = base
        self.factor = factor
        self._base = _BASES[base](**base_params)

    def build(self, returns: pd.DataFrame, date: Any, symbols: list[str]) -> GraphSnapshot:
        data = returns[list(symbols)].dropna()
        if len(data) < 30:
            return empty_snapshot(symbols, date, method="factor_residual")
        if self.factor == "mean":
            f = data.mean(axis=1)
        elif self.factor in data.columns:
            f = data[self.factor]
        else:
            return empty_snapshot(symbols, date, method="factor_residual")
        f_c = f - f.mean()
        denom = float((f_c**2).sum())
        if denom <= 0:
            return empty_snapshot(symbols, date, method="factor_residual")
        resid = {}
        for sym in symbols:
            r = data[sym]
            beta = float(((r - r.mean()) * f_c).sum()) / denom
            resid[sym] = r - r.mean() - beta * f_c
        resid_panel = pd.DataFrame(resid, index=data.index)
        snap = self._base.build(resid_panel, date, symbols)
        return GraphSnapshot(
            edge_index=snap.edge_index,
            edge_weight=snap.edge_weight,
            symbols=snap.symbols,
            date=date,
            directed=False,
            method="factor_residual",
        )
