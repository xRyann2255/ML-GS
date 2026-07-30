"""Prediction-level ensemble blending.

Combines forecasts from HAR-family baselines, LightGBM, and LSTM/TCN
into a single optimized prediction using:
- Simple averaging
- Inverse-QLIKE weighting
- Constrained linear combination (optimized on validation set)
- Stacking (meta-learner on cross-validated predictions)

Key classes:
    LightGBMBaggedSeeds      — Pipeline-compatible K-seed LightGBM bagging
    SimpleAverageEnsemble    — Equal-weight average of predictions
    InverseQLIKEEnsemble     — Weight by inverse QLIKE performance
    LinearBlendEnsemble      — Optimized linear combination
    StackingEnsemble         — Meta-learner on CV predictions
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from volforecast.models._base import _BaseModel
from volforecast.registry import register_model

logger = logging.getLogger(__name__)

# Fixed seed pool. The first 5 match the trial-047 reseed baseline so a
# bagged-5 ensemble can be compared directly against the single-seed envelope.
_DEFAULT_SEED_POOL = (42, 123, 456, 789, 2026, 1337, 7, 314159, 271828, 161803)


@register_model("lightgbm_bagged")
class LightGBMBaggedSeeds(_BaseModel):
    """K-seed bagging ensemble of LightGBM models with prediction averaging.

    Rationale
    ---------
    The trial-047 reseed baseline measured a 6.6 bps seed envelope at h=1
    on the trial-036 champion spec. Single-seed numbers are inside this noise
    floor, so feature-engineering deltas <~10 bps cannot be distinguished
    from seed shuffle. Averaging K predictions reduces prediction variance
    proportionally to K (under uncorrelated assumption; less in practice
    but always non-negative).

    Beyond QLIKE: a smoother h=1 forecast produces a smoother IV - RV_forecast
    gap, which means fewer GSVIVS01 signal flips per week, lower turnover,
    and a higher trading Sharpe even when QLIKE improvement is modest.

    Parameters
    ----------
    n_seeds : int
        Number of LightGBM members to train (default 5).
    seeds : list[int], optional
        Explicit seed list overriding the default pool. Length must equal
        n_seeds if provided.
    **kwargs
        Forwarded to every LightGBMVolModel member (n_estimators,
        learning_rate, num_leaves, base_model, drop_features, etc.).
        The `seed` key (if present) is ignored — per-member seeds are
        drawn from `seeds` / `_DEFAULT_SEED_POOL`.

    Notes
    -----
    - Members are fit sequentially. Tournament-level parallelism already
      spreads across models; per-member parallelism would deadlock the
      process pool.
    - Predict averages in log-RV space (LightGBM's training space).
      Averaging in log-space is the QLIKE-consistent choice because
      LightGBM optimizes log-QLIKE directly.
    - All members see the IDENTICAL X, y, and (for residual-init models)
      the IDENTICAL base linear fit. Only LightGBM's internal sampling
      (bagging_fraction, feature_fraction, tree split tiebreaks) varies.
    """

    REQUIRED_LAYERS = [
        "har_core",
        "asymmetry",
        "noise_robust",
        "options",
        "calendar",
        "tree_expansion",
    ]
    name = "lightgbm_bagged"
    supports_tuning = False

    def __init__(
        self,
        n_seeds: int = 5,
        seeds: list[int] | tuple[int, ...] | None = None,
        **kwargs: Any,
    ) -> None:
        if seeds is not None:
            seeds = tuple(int(s) for s in seeds)
            if len(seeds) != n_seeds:
                raise ValueError(
                    f"len(seeds)={len(seeds)} != n_seeds={n_seeds}. "
                    "Pass either n_seeds alone or seeds with matching length."
                )
            self.seeds = seeds
        else:
            if n_seeds < 1:
                raise ValueError(f"n_seeds must be >= 1, got {n_seeds}")
            if n_seeds > len(_DEFAULT_SEED_POOL):
                raise ValueError(
                    f"n_seeds={n_seeds} exceeds default pool size "
                    f"{len(_DEFAULT_SEED_POOL)}; pass explicit `seeds` to override."
                )
            self.seeds = _DEFAULT_SEED_POOL[:n_seeds]

        self.n_seeds = n_seeds
        # Strip any incoming `seed` — per-member seeds override.
        kwargs.pop("seed", None)
        self._member_kwargs = kwargs
        self._members: list[Any] = []

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        on_progress: Any | None = None,
    ) -> LightGBMBaggedSeeds:
        """Fit K LightGBM members with different seeds.

        Parameters
        ----------
        X, y : pd.DataFrame, pd.Series
            Training features and log-RV target.
        on_progress : callable, optional
            Forwarded to each member's fit() for per-round progress reporting.

        Returns
        -------
        self
        """
        from volforecast.models.lightgbm import LightGBMVolModel

        self._members = []
        for i, seed in enumerate(self.seeds):
            logger.info(
                "Bagging member %d/%d (seed=%d) on %d rows",
                i + 1,
                self.n_seeds,
                seed,
                len(X),
            )
            member = LightGBMVolModel(**{**self._member_kwargs, "seed": seed})
            # Don't propagate on_progress to every member — would spam the UI.
            # Forward only on the FIRST member so users see one progress stream.
            if on_progress is not None and i == 0:
                member.fit(X, y, on_progress=on_progress)
            else:
                member.fit(X, y)
            self._members.append(member)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Average member predictions in log-RV space.

        Returns
        -------
        np.ndarray
            Mean of K member predictions, shape (n_samples,).
        """
        if not self._members:
            raise RuntimeError("Model has not been fitted")
        preds = np.stack([m.predict(X) for m in self._members], axis=0)
        return preds.mean(axis=0)

    @property
    def summary(self) -> dict[str, float]:
        """Average feature-importance (gain) across members."""
        if not self._members:
            return {}
        per_member = [m.summary for m in self._members]
        if not per_member or not per_member[0]:
            return {}
        keys = set().union(*[s.keys() for s in per_member])
        return {k: float(np.mean([s.get(k, 0.0) for s in per_member])) for k in keys}

    def get_params(self) -> dict[str, Any]:
        """Cache-stable params for tuning replay (used by runner)."""
        out = dict(self._member_kwargs)
        out["n_seeds"] = self.n_seeds
        out["seeds"] = list(self.seeds)
        return out


class SimpleAverageEnsemble:
    """Equal-weight ensemble of model predictions."""

    name = "simple_average"

    def predict(self, predictions: dict[str, np.ndarray]) -> np.ndarray:
        """Average all model predictions.

        Parameters
        ----------
        predictions : dict[str, np.ndarray]
            Model name -> prediction array mapping.

        Returns
        -------
        np.ndarray
            Averaged predictions (log RV space).
        """
        raise NotImplementedError("TODO: implement")


class InverseQLIKEEnsemble:
    """Ensemble weighted by inverse QLIKE performance on validation set."""

    name = "inverse_qlike"

    def __init__(self) -> None:
        self.weights_: dict[str, float] | None = None

    def fit(
        self,
        predictions: dict[str, np.ndarray],
        y_true: np.ndarray,
    ) -> InverseQLIKEEnsemble:
        """Compute weights from validation QLIKE scores.

        Parameters
        ----------
        predictions : dict[str, np.ndarray]
            Model name -> validation predictions.
        y_true : np.ndarray
            True log(RV) values on validation set.

        Returns
        -------
        InverseQLIKEEnsemble
            Fitted ensemble (self).
        """
        raise NotImplementedError("TODO: implement")

    def predict(self, predictions: dict[str, np.ndarray]) -> np.ndarray:
        """Weighted average using fitted inverse-QLIKE weights.

        Parameters
        ----------
        predictions : dict[str, np.ndarray]
            Model name -> prediction array mapping.

        Returns
        -------
        np.ndarray
            Weighted predictions.
        """
        raise NotImplementedError("TODO: implement")


class LinearBlendEnsemble:
    """Optimized linear combination of model predictions.

    Solves: min_w QLIKE(y, sum(w_i * pred_i)) s.t. w_i >= 0, sum(w_i) = 1
    """

    name = "linear_blend"

    def __init__(self) -> None:
        self.weights_: np.ndarray | None = None
        self.model_names_: list[str] | None = None

    def fit(
        self,
        predictions: dict[str, np.ndarray],
        y_true: np.ndarray,
    ) -> LinearBlendEnsemble:
        """Optimize blend weights on validation data.

        Parameters
        ----------
        predictions : dict[str, np.ndarray]
            Model name -> validation predictions.
        y_true : np.ndarray
            True log(RV) values.

        Returns
        -------
        LinearBlendEnsemble
            Fitted ensemble (self).
        """
        raise NotImplementedError("TODO: implement")

    def predict(self, predictions: dict[str, np.ndarray]) -> np.ndarray:
        """Blend predictions using optimized weights.

        Parameters
        ----------
        predictions : dict[str, np.ndarray]
            Model name -> prediction array mapping.

        Returns
        -------
        np.ndarray
            Blended predictions.
        """
        raise NotImplementedError("TODO: implement")


class StackingEnsemble:
    """Stacking ensemble with meta-learner on CV predictions.

    First-level models generate out-of-fold predictions via purged k-fold.
    A meta-learner (Ridge regression) is trained on these OOF predictions.
    """

    name = "stacking"

    def __init__(self, meta_alpha: float = 1.0) -> None:
        self.meta_alpha = meta_alpha
        self.meta_model_ = None
        self.model_names_: list[str] | None = None

    def fit(
        self,
        oof_predictions: dict[str, np.ndarray],
        y_true: np.ndarray,
    ) -> StackingEnsemble:
        """Fit meta-learner on out-of-fold predictions.

        Parameters
        ----------
        oof_predictions : dict[str, np.ndarray]
            Model name -> OOF prediction arrays.
        y_true : np.ndarray
            True log(RV) values aligned with OOF predictions.

        Returns
        -------
        StackingEnsemble
            Fitted ensemble (self).
        """
        raise NotImplementedError("TODO: implement")

    def predict(self, predictions: dict[str, np.ndarray]) -> np.ndarray:
        """Generate meta-prediction from base model outputs.

        Parameters
        ----------
        predictions : dict[str, np.ndarray]
            Model name -> prediction array mapping.

        Returns
        -------
        np.ndarray
            Meta-learner predictions.
        """
        raise NotImplementedError("TODO: implement")
