"""
Port: IModelPort
Responsibility: Interface for ML model loading and inference.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional

import numpy as np
import pandas as pd


class IModelPort(ABC):
    """Abstract interface for ML models."""

    @abstractmethod
    def load(self, path: str) -> bool:
        """Load model from path."""
        ...

    @abstractmethod
    def save(self, path: str) -> bool:
        """Save model to path."""
        ...

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions on input features."""
        ...

    @abstractmethod
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict class probabilities."""
        ...

    @abstractmethod
    def get_feature_importance(self) -> dict[str, float]:
        """Get feature importance scores."""
        ...

    @abstractmethod
    def get_params(self) -> dict[str, Any]:
        """Get model hyperparameters."""
        ...

    @property
    @abstractmethod
    def model_type(self) -> str:
        """Type of model (e.g., 'lightgbm', 'xgboost', 'sklearn')."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Model version identifier."""
        ...