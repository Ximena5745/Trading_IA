"""
Module: core/ml/validation.py
Responsibility: Statistical validation with purged k-fold and walk-forward
Dependencies: sklearn, numpy, pandas
"""
from __future__ import annotations

from typing import Iterator

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold


class PurgedKFold:
    """
    Purged K-Fold with temporal embargo to prevent look-ahead bias.

    QWQ-3: Embargo temporal de 5 barras mínimo entre train y test.

    Uses forward-chaining (expanding window) for proper temporal validation.
    Each fold uses earlier data as train, later data as test.
    """

    def __init__(self, n_splits: int = 5, embargo_bars: int = 5):
        self.n_splits = n_splits
        self.embargo_bars = embargo_bars

    def split(self, X: pd.DataFrame | np.ndarray, y=None, groups=None) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        n_samples = len(X)
        indices = np.arange(n_samples)

        chunk_size = n_samples // (self.n_splits + 1)

        for i in range(self.n_splits):
            test_start = (i + 1) * chunk_size
            test_end = min((i + 2) * chunk_size, n_samples)

            train_end = test_start

            train_idx = indices[:train_end]
            test_idx = indices[test_start:test_end]

            embargo_boundary = test_start - self.embargo_bars

            if embargo_boundary > 0 and len(train_idx) > embargo_boundary:
                purged_train_idx = train_idx[:embargo_boundary]
            else:
                purged_train_idx = train_idx

            yield purged_train_idx, test_idx


class WalkForwardValidator:
    """
    Walk-forward validation with real retraining in each window.

    QWQ-10: Walk-forward con reentrenamiento real en cada ventana.
    """

    def __init__(
        self,
        train_window: int = 252 * 24,
        test_window: int = 30 * 24,
        step_size: int = 7 * 24,
    ):
        self.train_window = train_window
        self.test_window = test_window
        self.step_size = step_size

    def validate(
        self,
        model_factory,
        X: pd.DataFrame,
        y: pd.Series,
        metric_fn=None,
    ) -> dict:
        """
        Run walk-forward validation.

        Args:
            model_factory: Callable that returns a new model instance
            X: Feature DataFrame
            y: Target Series
            metric_fn: Callable(returns_true, returns_pred) -> float

        Returns:
            dict with oos_metrics, per_window_metrics
        """
        n_samples = len(X)
        results = []
        oos_returns = []
        oos_predictions = []

        i = 0
        while i + self.train_window + self.test_window <= n_samples:
            train_end = i + self.train_window
            test_end = train_end + self.test_window

            X_train = X.iloc[i:train_end]
            y_train = y.iloc[i:train_end]
            X_test = X.iloc[train_end:test_end]
            y_test = y.iloc[train_end:test_end]

            model = model_factory()
            model.fit(X_train, y_train)

            if hasattr(model, "predict"):
                preds = model.predict(X_test)
                oos_predictions.extend(preds)

            if metric_fn is not None and len(y_test) > 0:
                metric = metric_fn(y_test.values, preds if hasattr(model, "predict") else None)
                results.append({
                    "window_start": i,
                    "window_end": test_end,
                    "metric": metric,
                })

            i += self.step_size

        return {
            "n_windows": len(results),
            "per_window": results,
            "oos_predictions": oos_predictions,
        }