"""GSVIVS01 drawdown classifier — binary LightGBM model for precision-optimized signals.

Trains a LightGBM classifier where:
    - Target = 1 if GSVIVS01 index goes DOWN the next day, 0 otherwise
    - Features = same tabular features used by the regression pipeline
    - Signal = go short (-1) when P(drawdown) > threshold, else long (+1)

The classifier is designed to maximize precision of the short signal:
    - scale_pos_weight < 1.0 penalizes false positives (predicted drawdown but index went up)
    - High threshold (e.g., 0.6-0.7) ensures only high-confidence shorts

Public API:
    build_gsvivs_classification_target — Convert index levels to binary labels
    GsvivsDrawdownClassifier           — LightGBM binary classifier with signal output
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def build_gsvivs_classification_target(
    index_levels: pd.Series,
) -> pd.Series:
    """Build binary classification target from GSVIVS01 index levels.

    Label = 1 if the next-day return is negative (drawdown), 0 otherwise.
    The label at time t predicts whether the index goes down from t to t+1.

    Parameters
    ----------
    index_levels : pd.Series
        Daily GSVIVS01 index levels with DatetimeIndex.

    Returns
    -------
    pd.Series
        Binary labels (int8): 1 = next-day drawdown, 0 = next-day gain/flat.
        Length = len(index_levels) - 1 (last day has no next-day return).
    """
    returns = index_levels.pct_change().shift(-1)
    # Drop the last row (NaN from shift)
    returns = returns.iloc[:-1]
    target = (returns < 0).astype(np.int8)
    return target


class GsvivsDrawdownClassifier:
    """LightGBM binary classifier for GSVIVS01 drawdown prediction.

    Optimized for precision: penalizes false positives (predicting drawdown
    when there isn't one) via scale_pos_weight < 1.0 and a high probability
    threshold for the short signal.

    Parameters
    ----------
    n_estimators : int
        Maximum number of boosting rounds.
    learning_rate : float
        Step size shrinkage.
    num_leaves : int
        Maximum number of leaves per tree.
    max_depth : int
        Maximum tree depth.
    min_child_samples : int
        Minimum samples per leaf.
    scale_pos_weight : float
        Weight of positive class (drawdown days). < 1.0 reduces false positives
        (precision-optimized). > 1.0 increases recall.
    threshold : float
        Probability threshold for the short signal. Only go short when
        P(drawdown) > threshold. Higher = fewer but more precise shorts.
    early_stopping_rounds : int
        Early stopping patience.
    reg_lambda : float
        L2 regularization.
    reg_alpha : float
        L1 regularization.
    feature_fraction : float
        Fraction of features used per tree.
    """

    def __init__(
        self,
        n_estimators: int = 3000,
        learning_rate: float = 0.01,
        num_leaves: int = 16,
        max_depth: int = 4,
        min_child_samples: int = 100,
        scale_pos_weight: float = 0.5,
        threshold: float = 0.6,
        early_stopping_rounds: int = 100,
        reg_lambda: float = 5.0,
        reg_alpha: float = 0.1,
        feature_fraction: float = 0.8,
        val_fraction: float = 0.15,
    ):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.max_depth = max_depth
        self.min_child_samples = min_child_samples
        self.scale_pos_weight = scale_pos_weight
        self.threshold = threshold
        self.early_stopping_rounds = early_stopping_rounds
        self.reg_lambda = reg_lambda
        self.reg_alpha = reg_alpha
        self.feature_fraction = feature_fraction
        self.val_fraction = val_fraction

        self._model = None
        self._feature_names: list[str] = []

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> GsvivsDrawdownClassifier:
        """Fit the binary classifier.

        Parameters
        ----------
        X : pd.DataFrame
            Feature matrix.
        y : pd.Series
            Binary target (0/1).

        Returns
        -------
        GsvivsDrawdownClassifier
            Fitted model (self).
        """
        import lightgbm as lgb

        self._feature_names = list(X.columns)

        params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "max_depth": self.max_depth,
            "min_child_samples": self.min_child_samples,
            "scale_pos_weight": self.scale_pos_weight,
            "reg_lambda": self.reg_lambda,
            "reg_alpha": self.reg_alpha,
            "feature_fraction": self.feature_fraction,
            "verbosity": -1,
        }

        if self.val_fraction > 0 and len(X) > 50:
            # Time-based split: last val_fraction for validation
            split_idx = int(len(X) * (1 - self.val_fraction))
            X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

            dtrain = lgb.Dataset(X_train, label=y_train)
            dval = lgb.Dataset(X_val, label=y_val, reference=dtrain)

            self._model = lgb.train(
                params=params,
                train_set=dtrain,
                num_boost_round=self.n_estimators,
                valid_sets=[dval],
                valid_names=["val"],
                callbacks=[
                    lgb.early_stopping(self.early_stopping_rounds, verbose=False),
                    lgb.log_evaluation(-1),
                ],
            )
        else:
            dtrain = lgb.Dataset(X, label=y)
            self._model = lgb.train(
                params=params,
                train_set=dtrain,
                num_boost_round=self.n_estimators,
                callbacks=[lgb.log_evaluation(-1)],
            )

        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probability of next-day drawdown.

        Parameters
        ----------
        X : pd.DataFrame
            Feature matrix.

        Returns
        -------
        np.ndarray
            P(drawdown) for each row, in [0, 1].
        """
        if self._model is None:
            raise RuntimeError("Model has not been fitted")
        return self._model.predict(X[self._feature_names])

    def predict_signal(self, X: pd.DataFrame) -> np.ndarray:
        """Generate trading signal from drawdown probability.

        Signal = -1 (short) when P(drawdown) > threshold, else +1 (long).

        Parameters
        ----------
        X : pd.DataFrame
            Feature matrix.

        Returns
        -------
        np.ndarray
            Signal array: +1 (long) or -1 (short).
        """
        proba = self.predict_proba(X)
        signal = np.ones(len(proba), dtype=np.float64)
        signal[proba > self.threshold] = -1.0
        return signal

    @property
    def feature_importances(self) -> dict[str, float]:
        """Return feature importance (gain) as a dict."""
        if self._model is None:
            return {}
        importance = self._model.feature_importance(importance_type="gain")
        return dict(zip(self._feature_names, importance))
