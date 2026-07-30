"""Two-state Markov-switching regime probabilities (PIT-safe).

Emits filtered (never smoothed) P[high-vol state] using monthly expanding
refits with frozen-parameter forward filtering to prevent lookahead bias.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from volforecast.registry import register_feature_layer

logger = logging.getLogger(__name__)


@register_feature_layer("regime")
class RegimeLayer:
    """Filtered 2-state MS probability of the high-volatility state (PIT-frozen)."""

    def __init__(self, refit_every: int = 21, min_history: int = 252) -> None:
        self.refit_every = refit_every
        self.min_history = min_history

    def compute(
        self, daily_data: pd.DataFrame, *, context: object = None
    ) -> pd.DataFrame:
        from statsmodels.tsa.regime_switching.markov_regression import (
            MarkovRegression,
        )

        log_rv = np.log(daily_data["rv"].clip(lower=1e-20))
        endog = log_rv.diff().shift(1).dropna()

        probs = pd.Series(np.nan, index=daily_data.index)
        params: np.ndarray | None = None
        high: int | None = None
        last_valid_prob: float | None = None

        refit_dates = range(self.min_history, len(endog), self.refit_every)
        for k in refit_dates:
            # --- Refit: estimate parameters on endog[:k] ---
            window = endog.iloc[:k].values
            try:
                model = MarkovRegression(
                    window, k_regimes=2, switching_variance=True
                )
                res = model.fit(disp=False)
                params = res.params
                # Identify high-vol state via variance parameters
                # param_names is on the model, not the result
                names = model.param_names
                sigma_indices = [
                    i for i, n in enumerate(names) if n.startswith("sigma2")
                ]
                if len(sigma_indices) == 2:
                    high = int(
                        np.argmax([params[sigma_indices[0]], params[sigma_indices[1]]])
                    )
                else:
                    # Fallback: last two params are variances
                    high = int(np.argmax(params[-2:]))
            except Exception:
                if params is None:
                    continue  # not yet estimable
                logger.warning(
                    "MS refit failed at k=%d; reusing previous params", k
                )

            # --- Frozen-parameter forward filtering over the block ---
            block_end = min(k + self.refit_every, len(endog))
            ext_endog = endog.iloc[:block_end].values
            try:
                ext_model = MarkovRegression(
                    ext_endog, k_regimes=2, switching_variance=True
                )
                filt_result = ext_model.filter(params)
                raw_probs = np.asarray(
                    filt_result.filtered_marginal_probabilities
                )
                # Shape may be (T,2), (T,1,2), etc. — flatten to (T, k_regimes)
                if raw_probs.ndim == 3:
                    raw_probs = raw_probs[:, 0, :]
                block_probs = np.clip(raw_probs[k:block_end, high], 0.0, 1.0)
                # Replace any NaN within the block with forward-fill
                for j, idx in enumerate(endog.index[k:block_end]):
                    if np.isfinite(block_probs[j]):
                        probs.loc[idx] = block_probs[j]
                        last_valid_prob = block_probs[j]
                    elif last_valid_prob is not None:
                        probs.loc[idx] = last_valid_prob
            except Exception:
                # Filter itself failed — forward-fill with last valid prob
                logger.warning(
                    "MS filter failed for block k=%d; forward-filling", k
                )
                if last_valid_prob is not None:
                    for idx in endog.index[k:block_end]:
                        probs.loc[idx] = last_valid_prob

        return pd.DataFrame(
            {
                "regime_prob_d": probs,
                "regime_prob_w": probs.rolling(5).mean(),
            },
            index=daily_data.index,
        )
