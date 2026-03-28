"""
Module: core/auth/api_key_manager.py
Responsibility: Secure storage and retrieval of exchange API keys
Dependencies: settings
"""

from __future__ import annotations

from core.config.settings import Settings
from core.observability.logger import get_logger

logger = get_logger(__name__)


class ApiKeyManager:
    def __init__(self, settings: Settings):
        self._settings = settings

    def get_binance_credentials(self) -> tuple[str, str]:
        """Returns (api_key, secret_key). Raises if not configured."""
        api_key = self._settings.BINANCE_API_KEY
        secret_key = self._settings.BINANCE_SECRET_KEY
        if not api_key or not secret_key:
            raise ValueError("Binance API credentials are not configured")
        return api_key, secret_key

    def is_testnet(self) -> bool:
        return self._settings.BINANCE_TESTNET
