"""
Module: core/features/feature_store.py
Responsibility: Versioned in-memory + Redis feature storage
Dependencies: redis, models, logger
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

import redis.asyncio as aioredis

from core.models import FeatureSet
from core.observability.logger import get_logger

logger = get_logger(__name__)

FEATURE_STORE_KEY = "features:{symbol}:{version}"
FEATURE_HISTORY_KEY = "features_history:{symbol}"
MAX_HISTORY = 500


class FeatureStore:
    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None
        self._local_cache: dict[str, FeatureSet] = {}

    async def connect(self) -> None:
        self._redis = await aioredis.from_url(self._redis_url)

    async def save(self, features: FeatureSet) -> None:
        self._local_cache[features.symbol] = features
        if self._redis:
            key = FEATURE_STORE_KEY.format(symbol=features.symbol, version=features.version)
            await self._redis.set(key, features.model_dump_json(), ex=3600)
            history_key = FEATURE_HISTORY_KEY.format(symbol=features.symbol)
            await self._redis.lpush(history_key, features.model_dump_json())
            await self._redis.ltrim(history_key, 0, MAX_HISTORY - 1)
        logger.debug("features_saved", symbol=features.symbol, version=features.version)

    async def get_latest(self, symbol: str, version: str = "v1") -> Optional[FeatureSet]:
        if symbol in self._local_cache:
            return self._local_cache[symbol]
        if self._redis:
            key = FEATURE_STORE_KEY.format(symbol=symbol, version=version)
            data = await self._redis.get(key)
            if data:
                return FeatureSet.model_validate_json(data)
        return None

    async def get_history(self, symbol: str, limit: int = 100) -> list[FeatureSet]:
        if not self._redis:
            return []
        history_key = FEATURE_HISTORY_KEY.format(symbol=symbol)
        raw_list = await self._redis.lrange(history_key, 0, limit - 1)
        return [FeatureSet.model_validate_json(r) for r in raw_list]
