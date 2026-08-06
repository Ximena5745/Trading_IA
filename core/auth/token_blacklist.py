"""
Module: core/auth/token_blacklist.py
Responsibility: JWT revocation (blacklist) tracking via Redis
Dependencies: redis, logger
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import redis

from core.observability.logger import get_logger

logger = get_logger(__name__)


class TokenBlacklist:
    """Tracks revoked JWT `jti`s in Redis with TTL-bounded entries.

    Fail-open by design: if Redis is unavailable, checks and writes are
    skipped rather than raising — a revoked token stays valid until its own
    expiry (bounded by the JWT's TTL: 60 min access / 7 days refresh).
    Failing closed here (rejecting all tokens without Redis) would take
    down authentication entirely on any Redis blip, a much larger blast
    radius than the bounded window this trades away.
    """

    def __init__(self, redis_url: str, redis_client: Optional[redis.Redis] = None):
        self._redis_url = redis_url
        self._redis = redis_client

    def _get_redis(self) -> Optional[redis.Redis]:
        if self._redis is None:
            try:
                self._redis = redis.from_url(self._redis_url, decode_responses=True)
                self._redis.ping()
            except Exception as exc:
                logger.warning("redis_not_available_for_blacklist", error=str(exc))
                return None
        return self._redis

    def is_blacklisted(self, jti: str) -> bool:
        redis_client = self._get_redis()
        if not redis_client:
            return False
        return bool(redis_client.exists(f"blacklist:{jti}"))

    def add(self, jti: str, exp_timestamp: float, max_ttl_seconds: int = 604800) -> bool:
        redis_client = self._get_redis()
        if not redis_client:
            return False
        try:
            ttl = max(int(exp_timestamp - datetime.utcnow().timestamp()), 1)
            redis_client.setex(f"blacklist:{jti}", min(ttl, max_ttl_seconds), "1")
            logger.info("token_blacklisted", jti=jti)
            return True
        except Exception as exc:
            logger.warning("blacklist_add_failed", error=str(exc))
            return False
