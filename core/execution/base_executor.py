"""
Module: core/execution/base_executor.py
Responsibility: Abstract interface for all executors (paper and live)
Dependencies: none
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class AbcExecutor(ABC):
    @abstractmethod
    async def execute(self, signal: dict, quantity: float) -> dict:
        """Execute a signal and return the resulting Order dict."""
        ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> dict:
        """Cancel a pending or submitted order."""
        ...

    @abstractmethod
    async def get_order_status(self, order_id: str) -> dict:
        """Fetch current status of an order."""
        ...
