"""Integration test configuration.

Integration tests exercise multi-component workflows with synthetic data.
They do NOT require network access or real data files.
"""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_rv_series():
    """500 business-day log-RV series with HAR-like dynamics."""
    rng = np.random.default_rng(42)
    n = 500
    log_rv = np.zeros(n)
    log_rv[0] = np.log(0.0002)
    for i in range(1, n):
        log_rv[i] = -8.5 + 0.4 * log_rv[i - 1] + rng.normal(0, 0.3)
    idx = pd.bdate_range("2022-01-03", periods=n)
    return pd.Series(np.exp(log_rv), index=idx, name="rv")
