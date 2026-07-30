"""Test: per-symbol QLIKE decomposition produces consistent results.

Verifies that the per-symbol QLIKE analysis script logic is correct:
- Per-symbol QLIKE values weighted by obs count should equal pooled QLIKE
- Every symbol contributes a valid QLIKE > 0
- Improvement (bps) computation is arithmetic-correct
"""

import numpy as np
import pandas as pd

from volforecast.evaluation.metrics import qlike


def _make_predictions(n_symbols: int = 5, n_dates: int = 100, seed: int = 42):
    """Create synthetic MultiIndex predictions for testing."""
    rng = np.random.default_rng(seed)
    symbols = [f"SYM{i}" for i in range(n_symbols)]
    dates = pd.bdate_range("2020-01-01", periods=n_dates)

    # Build MultiIndex series
    idx_tuples = [(d, s) for s in symbols for d in dates]
    mi = pd.MultiIndex.from_tuples(idx_tuples, names=["date", "symbol"])

    # Actuals: log-RV with symbol-specific mean and variance
    actuals_vals = []
    for i, s in enumerate(symbols):
        mu = -8.0 + i * 0.5  # different vol levels
        actuals_vals.append(rng.normal(mu, 0.5, n_dates))
    actuals = pd.Series(np.concatenate(actuals_vals), index=mi)

    # HAR predictions: actuals + noise
    har_preds = actuals + rng.normal(0, 0.3, len(actuals))

    # LightGBM predictions: closer to actuals (better)
    lgbm_preds = actuals + rng.normal(0, 0.2, len(actuals))

    return actuals, har_preds, lgbm_preds, symbols


def test_pooled_equals_weighted_per_symbol():
    """Pooled QLIKE should equal observation-weighted mean of per-symbol QLIKEs."""
    actuals, har_preds, _, symbols = _make_predictions()

    # Pooled QLIKE
    pooled_q = qlike(actuals.values, har_preds.values, log_space=True)

    # Per-symbol QLIKE, then weighted average
    total_obs = 0
    weighted_sum = 0.0
    for sym in symbols:
        mask = actuals.index.get_level_values("symbol") == sym
        y_true_sym = actuals.values[mask]
        y_pred_sym = har_preds.values[mask]
        q_sym = qlike(y_true_sym, y_pred_sym, log_space=True)
        n = mask.sum()
        weighted_sum += q_sym * n
        total_obs += n

    weighted_avg = weighted_sum / total_obs

    # Should be exactly equal (same formula, same data, just different grouping)
    assert abs(pooled_q - weighted_avg) < 1e-12, (
        f"Pooled {pooled_q:.10f} != weighted avg {weighted_avg:.10f}"
    )


def test_per_symbol_improvement_bps():
    """Improvement in bps should be (baseline - model) / baseline * 10000."""
    actuals, har_preds, lgbm_preds, symbols = _make_predictions()

    for sym in symbols:
        mask = actuals.index.get_level_values("symbol") == sym
        y_true = actuals.values[mask]
        q_har = qlike(y_true, har_preds.values[mask], log_space=True)
        q_lgbm = qlike(y_true, lgbm_preds.values[mask], log_space=True)

        bps = (q_har - q_lgbm) / q_har * 10_000
        # LightGBM is better (lower noise), so bps should be positive
        assert bps > 0, f"{sym}: expected positive bps, got {bps:.1f}"


def test_all_symbols_have_valid_qlike():
    """Every symbol must produce QLIKE > 0."""
    actuals, har_preds, _, symbols = _make_predictions()

    for sym in symbols:
        mask = actuals.index.get_level_values("symbol") == sym
        q = qlike(actuals.values[mask], har_preds.values[mask], log_space=True)
        assert q > 0, f"{sym}: QLIKE must be > 0, got {q}"
        assert np.isfinite(q), f"{sym}: QLIKE must be finite, got {q}"


def test_unequal_symbol_counts():
    """Pooled metric should handle unequal obs counts per symbol correctly."""
    rng = np.random.default_rng(123)

    # Symbol A: 200 obs, Symbol B: 50 obs
    dates_a = pd.bdate_range("2020-01-01", periods=200)
    dates_b = pd.bdate_range("2020-01-01", periods=50)

    idx_a = pd.MultiIndex.from_arrays([dates_a, ["A"] * 200], names=["date", "symbol"])
    idx_b = pd.MultiIndex.from_arrays([dates_b, ["B"] * 50], names=["date", "symbol"])

    actuals_a = pd.Series(rng.normal(-8, 0.5, 200), index=idx_a)
    actuals_b = pd.Series(rng.normal(-7, 0.8, 50), index=idx_b)
    actuals = pd.concat([actuals_a, actuals_b])

    preds_a = actuals_a + rng.normal(0, 0.2, 200)
    preds_b = actuals_b + rng.normal(0, 0.5, 50)  # B is much worse
    preds = pd.concat([preds_a, preds_b])

    # Pooled QLIKE is dominated by A (200/250 = 80% weight)
    pooled_q = qlike(actuals.values, preds.values, log_space=True)
    q_a = qlike(actuals_a.values, preds_a.values, log_space=True)
    q_b = qlike(actuals_b.values, preds_b.values, log_space=True)

    # Verify weighting: pooled = (200*q_a + 50*q_b) / 250
    expected = (200 * q_a + 50 * q_b) / 250
    assert abs(pooled_q - expected) < 1e-12

    # Simple (unweighted) mean would be different
    simple_mean = (q_a + q_b) / 2
    # They shouldn't be equal since obs counts differ AND per-symbol QLIKE differs
    assert abs(pooled_q - simple_mean) > 1e-6
