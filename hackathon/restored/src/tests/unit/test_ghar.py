"""Unit tests for GHARVolModel (linear graph-HAR, Zhang et al. 2025 eq. 6).

TDD-first: these tests define the contract before implementation.
Shared fixtures (identity_graphs, spillover_graphs) live in conftest.py.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

from volforecast.models.ghar import GHARVolModel


def test_identity_nests_pooled_har(identity_graphs):
    m = GHARVolModel(input_dim=2).fit(identity_graphs)
    # direct pooled OLS on [one-hot | x] (gamma block absent)
    rows, ys = [], []
    for g in identity_graphs:
        for i in range(3):
            onehot = np.eye(3)[i]
            rows.append(np.concatenate([onehot, g["x"][i]]))
            ys.append(g["y"][i])
    beta_direct, *_ = np.linalg.lstsq(np.array(rows), np.array(ys), rcond=None)
    preds = m.predict(identity_graphs[:5])
    direct = np.array(rows[:15]) @ beta_direct
    np.testing.assert_allclose(preds, direct, atol=1e-8)
    np.testing.assert_allclose(m.coef_gamma_, 0.0, atol=1e-8)


def test_recovers_planted_spillover(spillover_graphs):
    m = GHARVolModel(input_dim=1).fit(spillover_graphs)
    assert m.coef_beta_[0] == pytest.approx(0.5, abs=0.05)
    assert m.coef_gamma_[0] == pytest.approx(0.3, abs=0.05)


def test_predict_is_node_major_flatten(identity_graphs):
    m = GHARVolModel(input_dim=2).fit(identity_graphs)
    preds = m.predict(identity_graphs[:2])
    assert preds.shape == (6,)
    single = m.predict(identity_graphs[:1])
    np.testing.assert_allclose(preds[:3], single)


def test_nan_targets_excluded_from_fit(identity_graphs):
    identity_graphs[0]["y"][1] = np.nan
    m = GHARVolModel(input_dim=2).fit(identity_graphs)
    assert np.isfinite(m.predict(identity_graphs[:1])).all()


def test_row_norm_for_directed(spillover_graphs):
    m = GHARVolModel(input_dim=1, w_norm="row").fit(spillover_graphs)
    assert np.isfinite(m.coef_gamma_).all()


def test_summary_names(identity_graphs):
    m = GHARVolModel(input_dim=2).fit(identity_graphs)
    s = m.summary
    assert {"alpha_mean", "beta_f0", "beta_f1", "gamma_f0", "gamma_f1"} <= set(s)


def test_registered():
    from volforecast.registry import MODEL_REGISTRY, ensure_registered

    ensure_registered()
    assert "ghar" in MODEL_REGISTRY
    assert MODEL_REGISTRY["ghar"].requires_graph is True
