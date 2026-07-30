"""Structural graph builders that need no estimation: identity, full, sector."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from volforecast.graphs.base import GraphSnapshot, empty_snapshot
from volforecast.registry import register_graph

#: GICS sector map for SYMBOL_UNIVERSE (GICS 2023: V/MA/PYPL are Financials).
SECTOR_MAP: dict[str, str] = {
    # Information Technology
    "AAPL": "it", "MSFT": "it", "NVDA": "it", "ADBE": "it", "CRM": "it",
    "CSCO": "it", "ACN": "it", "AVGO": "it", "ADI": "it", "AMAT": "it",
    "AMD": "it", "IBM": "it", "INTC": "it", "INTU": "it", "LRCX": "it",
    "MU": "it", "NOW": "it", "ORCL": "it", "PANW": "it", "QCOM": "it",
    "SNPS": "it", "TXN": "it",
    # Communication Services
    "GOOGL": "comm", "META": "comm", "NFLX": "comm", "DIS": "comm",
    "CMCSA": "comm", "T": "comm", "VZ": "comm",
    # Consumer Discretionary
    "AMZN": "cons_disc", "TSLA": "cons_disc", "HD": "cons_disc", "NKE": "cons_disc",
    "BKNG": "cons_disc", "F": "cons_disc", "GM": "cons_disc", "LOW": "cons_disc",
    "MCD": "cons_disc", "SBUX": "cons_disc", "TGT": "cons_disc", "TJX": "cons_disc",
    "UBER": "cons_disc",
    # Consumer Staples
    "PG": "cons_staples", "COST": "cons_staples", "KO": "cons_staples",
    "PEP": "cons_staples", "PM": "cons_staples", "WMT": "cons_staples",
    # Financials
    "JPM": "fin", "BAC": "fin", "V": "fin", "MA": "fin", "PYPL": "fin",
    "BRK.B": "fin", "AXP": "fin", "BLK": "fin", "GS": "fin", "MS": "fin",
    "SCHW": "fin", "SPGI": "fin", "USB": "fin", "WFC": "fin",
    # Health Care
    "JNJ": "health", "UNH": "health", "PFE": "health", "TMO": "health",
    "ABT": "health", "ABBV": "health", "AMGN": "health", "CI": "health",
    "DHR": "health", "ELV": "health", "GILD": "health", "ISRG": "health",
    "LLY": "health", "MRK": "health", "REGN": "health", "SYK": "health",
    "VRTX": "health",
    # Energy
    "XOM": "energy", "COP": "energy", "CVX": "energy", "SLB": "energy",
    # Industrials
    "BA": "industrials", "CAT": "industrials", "DE": "industrials",
    "GE": "industrials", "HON": "industrials", "RTX": "industrials",
    "UNP": "industrials", "UPS": "industrials",
    # Materials
    "LIN": "materials", "SHW": "materials",
    # Utilities
    "NEE": "utilities", "SO": "utilities",
    # Real Estate
    "PLD": "real_estate",
    # Broad-market index products share one sector (they co-move by construction)
    "SPY": "index", "QQQ": "index", "IWM": "index", "DIA": "index",
    "ES": "index", "SPX": "index",
}


@register_graph("identity")
class IdentityGraphBuilder:
    """No edges — the no-graph control. GHAR(identity) == plain pooled HAR."""

    directed = False

    def build(self, returns: pd.DataFrame, date: Any, symbols: list[str]) -> GraphSnapshot:
        return empty_snapshot(symbols, date, method="identity")


@register_graph("full")
class FullGraphBuilder:
    """Complete graph, uniform weight 1/(N-1): neighbor aggregate = mean of the others."""

    directed = False

    def build(self, returns: pd.DataFrame, date: Any, symbols: list[str]) -> GraphSnapshot:
        n = len(symbols)
        if n < 2:
            return empty_snapshot(symbols, date, method="full")
        src, dst = np.where(~np.eye(n, dtype=bool))
        weight = np.full(src.shape[0], 1.0 / (n - 1), dtype=np.float32)
        return GraphSnapshot(
            edge_index=np.stack([src, dst]).astype(np.int64),
            edge_weight=weight, symbols=tuple(symbols), date=date, method="full",
        )


@register_graph("sector")
class SectorGraphBuilder:
    """Binary edges between same-GICS-sector symbols; unknown symbols stay isolated."""

    directed = False

    def __init__(self, sector_map: dict[str, str] | None = None) -> None:
        self.sector_map = dict(sector_map or SECTOR_MAP)

    def build(self, returns: pd.DataFrame, date: Any, symbols: list[str]) -> GraphSnapshot:
        src_list: list[int] = []
        dst_list: list[int] = []
        for i, si in enumerate(symbols):
            for j, sj in enumerate(symbols):
                if i == j:
                    continue
                sec_i = self.sector_map.get(si)
                if sec_i is not None and sec_i == self.sector_map.get(sj):
                    src_list.append(i)
                    dst_list.append(j)
        if not src_list:
            return empty_snapshot(symbols, date, method="sector")
        return GraphSnapshot(
            edge_index=np.array([src_list, dst_list], dtype=np.int64),
            edge_weight=np.ones(len(src_list), dtype=np.float32),
            symbols=tuple(symbols), date=date, method="sector",
        )
