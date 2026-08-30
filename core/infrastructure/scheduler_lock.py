"""
Module: core/infrastructure/scheduler_lock.py
Responsibility: Redis-based single-owner lock for the pipeline scheduler.
  Guarantees that exactly one process runs the APScheduler even when the API
  is deployed with several uvicorn workers or several worker replicas exist.

  Semantics:
    - acquire(): SET <key> <owner_id> NX EX <ttl>  → True only for the winner.
    - renew():   compare-and-expire (Lua) — extends the TTL only while we still
                 own the key. Returns False if ownership was lost.
    - release(): compare-and-delete (Lua) — never deletes another owner's key.

  Fail behaviour: any Redis error is treated as "not acquired / not renewed".
  A scheduler that cannot reach Redis stays passive rather than risk running a
  second copy — consistent with ADR-005 (fail-safe for anything that drives
  execution).
Dependencies: redis
"""
from __future__ import annotations

import asyncio
import os
import socket
from typing import Awaitable, Callable, Optional
from uuid import uuid4

import redis

from core.observability.logger import get_logger

logger = get_logger(__name__)

DEFAULT_KEY = "trader:scheduler:owner"
DEFAULT_TTL_SECONDS = 90
DEFAULT_RENEW_SECONDS = 30
DEFAULT_RETRY_SECONDS = 15

# KEYS[1]=lock key, ARGV[1]=owner id, ARGV[2]=ttl seconds
_RENEW_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('expire', KEYS[1], ARGV[2])
else
    return 0
end
"""

# KEYS[1]=lock key, ARGV[1]=owner id
_RELEASE_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""


def _default_owner_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"


class SchedulerLock:
    """Single-owner lock backed by a Redis key with a bounded TTL."""

    def __init__(
        self,
        redis_url: str,
        *,
        key: str = DEFAULT_KEY,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        renew_seconds: int = DEFAULT_RENEW_SECONDS,
        retry_seconds: int = DEFAULT_RETRY_SECONDS,
        owner_id: Optional[str] = None,
        redis_client: Optional[redis.Redis] = None,
    ) -> None:
        if renew_seconds >= ttl_seconds:
            raise ValueError("renew_seconds must be smaller than ttl_seconds")
        self._redis_url = redis_url
        self._redis = redis_client
        self.key = key
        self.ttl_seconds = ttl_seconds
        self.renew_seconds = renew_seconds
        self.retry_seconds = retry_seconds
        self.owner_id = owner_id or _default_owner_id()

    # ── Redis handle ────────────────────────────────────────────────────────
    def _get_redis(self) -> Optional[redis.Redis]:
        if self._redis is None:
            try:
                client = redis.from_url(self._redis_url, decode_responses=True)
                client.ping()
                self._redis = client
            except Exception as exc:  # noqa: BLE001 — any failure ⇒ stay passive
                logger.warning("scheduler_lock_redis_unavailable", error=str(exc))
                return None
        return self._redis

    # ── Primitive operations ───────────────────────────────────────────────
    def acquire(self) -> bool:
        """Try to become the owner. True only for the single winner."""
        client = self._get_redis()
        if client is None:
            return False
        try:
            got = client.set(
                self.key, self.owner_id, nx=True, ex=self.ttl_seconds
            )
            return bool(got)
        except Exception as exc:  # noqa: BLE001
            logger.warning("scheduler_lock_acquire_failed", error=str(exc))
            self._redis = None
            return False

    def renew(self) -> bool:
        """Extend the TTL while we still own the key. False ⇒ ownership lost."""
        client = self._get_redis()
        if client is None:
            return False
        try:
            res = client.eval(
                _RENEW_LUA, 1, self.key, self.owner_id, self.ttl_seconds
            )
            return bool(res)
        except Exception as exc:  # noqa: BLE001
            logger.warning("scheduler_lock_renew_failed", error=str(exc))
            self._redis = None
            return False

    def release(self) -> None:
        """Delete the key only if we still own it. Best effort."""
        client = self._get_redis()
        if client is None:
            return
        try:
            client.eval(_RELEASE_LUA, 1, self.key, self.owner_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("scheduler_lock_release_failed", error=str(exc))

    def held_by_us(self) -> bool:
        client = self._get_redis()
        if client is None:
            return False
        try:
            return client.get(self.key) == self.owner_id
        except Exception:  # noqa: BLE001
            return False

    # ── Async orchestration helpers ────────────────────────────────────────
    async def wait_until_owner(
        self, *, on_standby: Optional[Callable[[int], None]] = None
    ) -> None:
        """Block until this process wins the lock, retrying in passive mode."""
        attempt = 0
        while not self.acquire():
            attempt += 1
            if on_standby is not None:
                on_standby(attempt)
            else:
                logger.info(
                    "scheduler_owner_standby",
                    owner_id=self.owner_id,
                    attempt=attempt,
                    retry_seconds=self.retry_seconds,
                )
            await asyncio.sleep(self.retry_seconds)
        logger.info("scheduler_owner_acquired", owner_id=self.owner_id, key=self.key)

    async def keep_renewed(
        self, *, on_lost: Optional[Callable[[], Awaitable[None]]] = None
    ) -> None:
        """Renew the lock forever; call ``on_lost`` and return if ownership drops."""
        while True:
            await asyncio.sleep(self.renew_seconds)
            if not self.renew():
                logger.critical(
                    "scheduler_owner_lost", owner_id=self.owner_id, key=self.key
                )
                if on_lost is not None:
                    await on_lost()
                return
