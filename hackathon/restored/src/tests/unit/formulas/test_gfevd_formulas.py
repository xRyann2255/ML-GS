from __future__ import annotations

import numpy as np
import pytest

from volforecast.graphs.spillover import generalized_fevd_matrix

pytestmark = pytest.mark.formula


def test_gfevd_matches_bivariate_var1_gold(load_gold):
    gold = load_gold("gfevd_bivariate_var1.json")
    psi = [np.eye(2), np.array(gold["inputs"]["A"])]      # Psi_0 = I, Psi_1 = A for VAR(1), H=2
    sigma = np.array(gold["inputs"]["sigma"])
    theta = generalized_fevd_matrix(psi, sigma)
    np.testing.assert_allclose(theta, np.array(gold["expected"]["theta_normalized"]), rtol=1e-6)


def test_gfevd_rows_sum_to_one(load_gold):
    gold = load_gold("gfevd_bivariate_var1.json")
    theta = generalized_fevd_matrix(
        [np.eye(2), np.array(gold["inputs"]["A"])], np.array(gold["inputs"]["sigma"])
    )
    np.testing.assert_allclose(theta.sum(axis=1), 1.0, atol=1e-12)


def test_gfevd_total_spillover_index(load_gold):
    gold = load_gold("gfevd_bivariate_var1.json")
    theta = generalized_fevd_matrix(
        [np.eye(2), np.array(gold["inputs"]["A"])], np.array(gold["inputs"]["sigma"])
    )
    total = 100.0 * (theta.sum() - np.trace(theta)) / theta.shape[0]
    assert total == pytest.approx(gold["expected"]["total_spillover_pct"], rel=1e-6)
