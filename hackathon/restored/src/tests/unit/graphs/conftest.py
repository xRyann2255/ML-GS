"""Shared fixtures for graph-builder tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_returns_panel() -> pd.DataFrame:
    """300 bdays x 8 symbols with two independent 4-symbol correlation blocks.

    Block A (A1..A4) loads on factor f1, block B (B1..B4) on f2.
    Intra-block correlation ~0.85; cross-block ~0. Any sane graph builder
    should recover the block structure.
    """
    rng = np.random.default_rng(42)
    n = 300
    dates = pd.bdate_range("2022-01-03", periods=n)
    f1 = rng.normal(0.0, 0.010, n)
    f2 = rng.normal(0.0, 0.010, n)
    cols: dict[str, np.ndarray] = {}
    for sym in ["A1", "A2", "A3", "A4"]:
        cols[sym] = 0.9 * f1 + rng.normal(0.0, 0.004, n)
    for sym in ["B1", "B2", "B3", "B4"]:
        cols[sym] = 0.9 * f2 + rng.normal(0.0, 0.004, n)
    return pd.DataFrame(cols, index=dates)


@pytest.fixture
def symbols8(synthetic_returns_panel) -> list[str]:
    return list(synthetic_returns_panel.columns)
