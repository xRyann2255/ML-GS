from __future__ import annotations

import numpy as np
import pytest

from volforecast.graphs.glasso import GlassoGraphBuilder


def _block_of(sym: str) -> str:
    return sym[0]


def test_glasso_no_cross_block_edges(synthetic_returns_panel, symbols8):
    snap = GlassoGraphBuilder(alpha=0.2).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    src, dst = snap.edge_index
    for i, j in zip(src, dst):
        assert _block_of(symbols8[i]) == _block_of(symbols8[j])


def test_glasso_finds_intra_block_structure(synthetic_returns_panel, symbols8):
    snap = GlassoGraphBuilder(alpha=0.2).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    src = snap.edge_index[0]
    blocks = {_block_of(symbols8[i]) for i in src}
    assert blocks == {"A", "B"}


def test_glasso_edges_are_binary_and_symmetric(synthetic_returns_panel, symbols8):
    snap = GlassoGraphBuilder(alpha=0.2).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    np.testing.assert_allclose(snap.edge_weight, 1.0)
    pairs = {(int(i), int(j)) for i, j in zip(*snap.edge_index)}
    assert all((j, i) in pairs for (i, j) in pairs)
    assert all(i != j for (i, j) in pairs)  # zero diagonal


def test_glasso_cv_mode_runs(synthetic_returns_panel, symbols8):
    snap = GlassoGraphBuilder(alpha=None).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    assert snap.method == "glasso"  # CV mode completes and returns a snapshot


def test_glasso_degenerate_window_falls_back_empty(synthetic_returns_panel, symbols8):
    tiny = synthetic_returns_panel.iloc[:5]
    snap = GlassoGraphBuilder(alpha=0.2).build(tiny, tiny.index[-1], symbols8)
    assert snap.n_edges == 0


def test_glasso_nonfinite_precision_returns_empty(synthetic_returns_panel, symbols8, monkeypatch):
    """When GLASSO produces a non-finite precision matrix, return empty graph."""
    import sklearn.covariance

    _orig_fit = sklearn.covariance.GraphicalLasso.fit

    def _poison_fit(self, X, y=None):
        _orig_fit(self, X, y)
        self.precision_[0, 0] = np.nan
        return self

    monkeypatch.setattr(sklearn.covariance.GraphicalLasso, "fit", _poison_fit)
    snap = GlassoGraphBuilder(alpha=0.2).build(
        synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
    )
    assert snap.n_edges == 0


def test_glasso_convergence_warning_suppressed(synthetic_returns_panel, symbols8):
    """ConvergenceWarning from sklearn should not propagate."""
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        # alpha=None triggers GraphicalLassoCV which may warn on small data;
        # with our fix, no warning should escape.
        snap = GlassoGraphBuilder(alpha=0.2).build(
            synthetic_returns_panel, synthetic_returns_panel.index[-1], symbols8
        )
    assert snap.method == "glasso"
