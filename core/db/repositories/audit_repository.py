"""
Module: core/db/repositories/audit_repository.py
Responsibility: Audit log persistence for compliance trail.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from core.db.session import get_pool
from core.observability.logger import get_logger

logger = get_logger(__name__)


class AuditRepository:
    async def log_action(
        self,
        action: str,
        user_id: str,
        changes: dict,
        resource_type: str = "system",
        entity_id: str | None = None,
        ip_address: str | None = None,
    ) -> None:
        sql = """
            INSERT INTO audit_log (timestamp, user_id, action, entity_type, entity_id, new_value)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        """
        payload = dict(changes)
        if ip_address:
            payload["ip_address"] = ip_address
        try:
            await get_pool().execute(
                sql,
                datetime.now(timezone.utc),
                user_id,
                action,
                resource_type,
                entity_id,
                json.dumps(payload),
            )
        except Exception as exc:
            logger.warning("audit_log_failed", action=action, error=str(exc))

    async def get_recent_by_action(self, action: str, limit: int = 100) -> list[dict]:
        sql = """
            SELECT action, user_id, entity_type, entity_id, new_value, timestamp
            FROM audit_log
            WHERE action = $1
            ORDER BY timestamp DESC
            LIMIT $2
        """
        try:
            rows = await get_pool().fetch(sql, action, limit)
            return [dict(r) for r in rows]
        except Exception as exc:
            logger.error("audit_fetch_failed", action=action, error=str(exc))
            return []
