"""
Module: core/observability/decision_tracer.py
Responsibility: Full audit trail for every signal lifecycle + a retrievable
  per-correlation_id trace store shared between the worker (producer) and the
  API's GET /trace/{correlation_id} (consumer). SPEC-B04 / F-06.
Dependencies: logger, redis (optional)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from core.observability.logger import get_logger

logger = get_logger(__name__)

TRACE_KEY_PREFIX = "trace:"
TRACE_TTL_SECONDS = 7 * 24 * 3600
# Canonical ordered stages of one pipeline decision.
TRACE_STEPS = (
    "market_data",
    "features",
    "agent_output",
    "consensus",
    "signal",
    "risk_check",
    "execution",
    "portfolio",
)


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except Exception:  # noqa: BLE001
            return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)


class TraceStore:
    """Append-only, per-correlation_id trace. Redis-backed, in-memory fallback."""

    def __init__(self, redis_client: Any = None, redis_url: Optional[str] = None):
        self._redis = redis_client
        self._redis_url = redis_url
        self._mem: dict[str, list[dict]] = {}

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        if not self._redis_url:
            return None
        try:
            import redis

            client = redis.from_url(self._redis_url, decode_responses=True)
            client.ping()
            self._redis = client
            return client
        except Exception as exc:  # noqa: BLE001
            logger.warning("trace_store_redis_unavailable", error=str(exc))
            return None

    def record(self, correlation_id: str, step: str, data: Any = None) -> None:
        if not correlation_id:
            return
        entry = {
            "step": step,
            "ts": datetime.now(timezone.utc).isoformat(),
            "data": _jsonable(data if data is not None else {}),
        }
        client = self._get_redis()
        if client is not None:
            try:
                key = TRACE_KEY_PREFIX + correlation_id
                client.rpush(key, json.dumps(entry, default=str))
                client.expire(key, TRACE_TTL_SECONDS)
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("trace_store_write_failed", error=str(exc))
        self._mem.setdefault(correlation_id, []).append(entry)

    def get(self, correlation_id: str) -> list[dict]:
        client = self._get_redis()
        if client is not None:
            try:
                raw = client.lrange(TRACE_KEY_PREFIX + correlation_id, 0, -1)
                if raw:
                    return [json.loads(x) for x in raw]
            except Exception as exc:  # noqa: BLE001
                logger.warning("trace_store_read_failed", error=str(exc))
        return list(self._mem.get(correlation_id, []))


_STORE: Optional[TraceStore] = None


def get_trace_store() -> TraceStore:
    global _STORE
    if _STORE is None:
        try:
            from core.config.settings import get_settings

            _STORE = TraceStore(redis_url=get_settings().REDIS_URL)
        except Exception:  # noqa: BLE001
            _STORE = TraceStore()
    return _STORE


def set_trace_store(store: Optional[TraceStore]) -> None:
    """Test hook — inject or reset the module singleton."""
    global _STORE
    _STORE = store


class DecisionTracer:
    """Records the complete decision chain for each generated signal."""

    def trace(self, signal_id: str, step: str, **context) -> None:
        logger.info(
            "signal_lifecycle",
            signal_id=signal_id,
            step=step,
            ts=datetime.utcnow().isoformat(),
            **context,
        )

    def trace_market_data(self, signal_id: str, symbol: str, ohlcv: dict) -> None:
        self.trace(signal_id, "market_data_received", symbol=symbol, ohlcv=ohlcv)

    def trace_features(
        self, signal_id: str, feature_version: str, key_values: dict
    ) -> None:
        self.trace(
            signal_id,
            "features_calculated",
            feature_version=feature_version,
            key_values=key_values,
        )

    def trace_agent_output(
        self, signal_id: str, agent_id: str, score: float, confidence: float
    ) -> None:
        self.trace(
            signal_id,
            "agent_output",
            agent_id=agent_id,
            score=score,
            confidence=confidence,
        )

    def trace_consensus(
        self, signal_id: str, weighted_score: float, blocked: bool
    ) -> None:
        self.trace(
            signal_id,
            "consensus_result",
            weighted_score=weighted_score,
            blocked_by_regime=blocked,
        )

    def trace_signal(
        self, signal_id: str, action: str, entry: float, sl: float, tp: float
    ) -> None:
        self.trace(
            signal_id,
            "signal_generated",
            action=action,
            entry=entry,
            stop_loss=sl,
            take_profit=tp,
        )

    def trace_risk_check(self, signal_id: str, approved: bool, reason: str) -> None:
        self.trace(signal_id, "risk_check", approved=approved, reason=reason)

    def trace_execution(
        self, signal_id: str, fill_price: float, quantity: float, commission: float
    ) -> None:
        self.trace(
            signal_id,
            "execution_result",
            fill_price=fill_price,
            quantity=quantity,
            commission=commission,
        )
