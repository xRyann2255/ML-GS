"""Forward log-RV target construction (Corsi 2009 HAR-family).

This module owns the single canonical implementation of the forward log-RV
target used by every HAR/HARQ/LightGBM/LSTM model in the project.

Mathematical definition:

    y_t = log( (1/h) * sum_{k=1..h} RV_{t+k} )

i.e. the log of the *arithmetic mean* of the next ``h`` realized variances.
This is the Corsi (2009) HAR convention and matches the inline target
construction previously duplicated across pipeline, CLI, and IV-feature paths.

Contract notes (see plan in `/memories/session/plan.md` §2):

* Index of the output equals the input index (prediction-point dating: the
  value at index ``t`` is the target a model trained at decision time ``t``
  is asked to predict).
* The last ``h`` rows of the output are NaN (no future RV available).
* Negative or zero values in ``rv`` are clipped to ``min_value`` before the
  outer ``log`` is applied (no ``-inf`` is ever returned).
* Mid-stream NaN values in ``rv`` propagate per ``pandas.Series.rolling`` —
  any window of ``h`` consecutive days containing a NaN yields NaN.
* Input must be a single 1-D ``pandas.Series`` with a monotonic, unique
  index. Pooled / multi-symbol callers must loop per symbol and call this
  helper once per symbol.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def forward_log_rv(
    rv: pd.Series,
    h: int,
    *,
    min_value: float = 1e-20,
) -> pd.Series:
    """Return the Corsi-family forward log-RV target.

    Parameters
    ----------
    rv : pd.Series
        Daily realized variance (raw, not logged). Must have a monotonic,
        unique 1-D index.
    h : int
        Forecast horizon in trading days (must be >= 1).
    min_value : float, optional
        Floor applied to ``rv`` before the outer ``log`` to prevent ``-inf``.
        Defaults to ``1e-20``, matching ``volforecast.features.transforms.safe_log``.

    Returns
    -------
    pd.Series
        Log of the arithmetic mean of the next ``h`` RV values, indexed by
        ``rv.index``. Last ``h`` rows are NaN.

    Raises
    ------
    ValueError
        If ``h < 1``, or if ``rv.index`` is non-monotonic or contains
        duplicates.
    """
    if h < 1:
        raise ValueError("h must be >= 1")

    if len(rv) == 0:
        # Preserve index/dtype; rolling on empty input would also yield empty.
        return pd.Series([], dtype=float, index=rv.index, name=rv.name)

    if not rv.index.is_monotonic_increasing:
        raise ValueError("rv.index must be monotonic increasing")
    if not rv.index.is_unique:
        raise ValueError("rv.index must be unique")

    # Clip negatives / zeros so the outer log never returns -inf.
    # NaN values pass through unchanged (clip preserves NaN).
    rv_floored = rv.clip(lower=min_value)

    # Arithmetic mean of the next h values, then log, then align to the
    # prediction date (date of decision, not date of realization).
    # rolling(h).mean() at index i = mean(rv[i-h+1 .. i]).
    # shift(-h) moves the value at index i to index i-h, so y_{i-h} =
    # mean(rv[i-h+1 .. i]) = mean(RV_{t+1..t+h}) where t = i-h. ✓
    forward_mean = rv_floored.rolling(h).mean().shift(-h)
    return np.log(forward_mean)
