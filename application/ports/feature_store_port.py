"""
Port: IFeatureStorePort
Responsibility: Interface for feature storage and retrieval.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import pandas as pd


class IFeatureStorePort(ABC):
    """Abstract interface for feature store."""

    @abstractmethod
    async def save_features(
        self,
        symbol: str,
        interval: str,
        features: pd.DataFrame,
        version: str,
    ) -> bool:
        """Save computed features to store."""
        ...

    @abstractmethod
    async def get_features(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
        version: Optional[str] = None,
    ) -> pd.DataFrame:
        """Retrieve features from store."""
        ...

    @abstractmethod
    async def get_latest_features(
        self,
        symbol: str,
        interval: str,
        n: int = 1,
    ) -> pd.DataFrame:
        """Get the N most recent feature sets."""
        ...

    @abstractmethod
    async def list_versions(self, symbol: str, interval: str) -> list[str]:
        """List available feature versions."""
        ...

    @abstractmethod
    async def compute_hash(self, config: dict) -> str:
        """Compute hash of feature configuration."""
        ...

    @abstractmethod
    async def detect_drift(
        self,
        reference_features: pd.DataFrame,
        current_features: pd.DataFrame,
    ) -> dict:
        """Detect feature drift between reference and current."""
        ...