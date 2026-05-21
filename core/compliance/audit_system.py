"""
Module: core/compliance/audit_system.py
Responsibility: Sistema de auditoría inmutable para todas las decisiones de trading.
  - Registro de cada decisión trazable
  - Export para contabilidad/impuestos
  - Reports automáticos de P&L por estrategia, activo y período
Dependencies: pandas, datetime, json
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import json

from core.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AuditEntry:
    """Entrada de auditoría inmutable."""
    timestamp: datetime
    user_id: str
    action_type: str
    details: dict
    entity_type: str
    entity_id: str
    result: str
    metadata: dict = field(default_factory=dict)


class AuditLog:
    """Log de auditoría inmutable."""

    def __init__(self, log_dir: str = "logs/audit"):
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._current_file = self._log_dir / f"audit_{datetime.utcnow().strftime('%Y%m')}.jsonl"

    def append(self, entry: AuditEntry) -> None:
        """Añadir entrada inmutable al log."""
        with open(self._current_file, "a") as f:
            f.write(json.dumps({
                "timestamp": entry.timestamp.isoformat(),
                "user_id": entry.user_id,
                "action_type": entry.action_type,
                "details": entry.details,
                "entity_type": entry.entity_type,
                "entity_id": entry.entity_id,
                "result": entry.result,
                "metadata": entry.metadata,
            }) + "\n")

    def query(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
        action_type: Optional[str] = None,
    ) -> list[AuditEntry]:
        """Consultar entradas de auditoría."""
        results = []

        for log_file in self._log_dir.glob("audit_*.jsonl"):
            with open(log_file, "r") as f:
                for line in f:
                    entry_data = json.loads(line)
                    entry = AuditEntry(
                        timestamp=datetime.fromisoformat(entry_data["timestamp"]),
                        user_id=entry_data["user_id"],
                        action_type=entry_data["action_type"],
                        details=entry_data["details"],
                        entity_type=entry_data["entity_type"],
                        entity_id=entry_data["entity_id"],
                        result=entry_data["result"],
                        metadata=entry_data.get("metadata", {}),
                    )

                    if start_date and entry.timestamp < start_date:
                        continue
                    if end_date and entry.timestamp > end_date:
                        continue
                    if user_id and entry.user_id != user_id:
                        continue
                    if action_type and entry.action_type != action_type:
                        continue

                    results.append(entry)

        return sorted(results, key=lambda e: e.timestamp)


class ComplianceAuditSystem:
    """
    Sistema de compliance y auditoría.

    M7.5: Compliance y auditoría.
    """

    def __init__(self):
        self._audit_log = AuditLog()

    def log_trade_decision(
        self,
        user_id: str,
        symbol: str,
        action: str,
        signal_data: dict,
        risk_validation: dict,
        result: str,
    ) -> None:
        """Registrar decisión de trading."""
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            action_type="TRADE_DECISION",
            details={
                "symbol": symbol,
                "action": action,
                "signal": signal_data,
                "risk_validation": risk_validation,
            },
            entity_type="signal",
            entity_id=signal_data.get("id", ""),
            result=result,
        )
        self._audit_log.append(entry)

    def log_order_execution(
        self,
        order_id: str,
        symbol: str,
        execution_data: dict,
    ) -> None:
        """Registrar ejecución de orden."""
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            user_id="system",
            action_type="ORDER_EXECUTED",
            details=execution_data,
            entity_type="order",
            entity_id=order_id,
            result="executed" if execution_data.get("status") == "filled" else "failed",
        )
        self._audit_log.append(entry)

    def log_risk_parameter_change(
        self,
        user_id: str,
        parameter: str,
        old_value: any,
        new_value: any,
    ) -> None:
        """Registrar cambio en parámetros de riesgo."""
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            action_type="RISK_PARAMETER_CHANGE",
            details={
                "parameter": parameter,
                "old_value": str(old_value),
                "new_value": str(new_value),
            },
            entity_type="risk_config",
            entity_id=parameter,
            result="approved" if new_value < old_value else "increased",
            metadata={"requires_approval": parameter in ["MAX_RISK_PER_TRADE_PCT", "DAILY_LOSS_LIMIT_PCT"]},
        )
        self._audit_log.append(entry)

    def log_kill_switch_trigger(
        self,
        triggered_by: str,
        reason: str,
        state: dict,
    ) -> None:
        """Registrar activación de kill switch."""
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            user_id="system",
            action_type="KILL_SWITCH_TRIGGERED",
            details={"reason": reason, "state": state},
            entity_type="kill_switch",
            entity_id="global",
            result="ACTIVATED",
        )
        self._audit_log.append(entry)

    def generate_pnl_report(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "strategy",
    ) -> pd.DataFrame:
        """Generar reporte de P&L."""
        entries = self._audit_log.query(
            start_date=start_date,
            end_date=end_date,
            action_type="ORDER_EXECUTED",
        )

        records = []
        for entry in entries:
            details = entry.details
            if details.get("result") == "executed":
                records.append({
                    "timestamp": entry.timestamp,
                    "symbol": details.get("symbol"),
                    "pnl": details.get("pnl", 0),
                    "commission": details.get("commission", 0),
                })

        df = pd.DataFrame(records)

        if group_by == "strategy":
            return df.groupby(df["timestamp"].dt.strftime("%Y-%m-%d")).agg({
                "pnl": "sum",
                "commission": "sum",
            })
        elif group_by == "symbol":
            return df.groupby("symbol").agg({
                "pnl": "sum",
                "commission": "sum",
            })

        return df

    def export_compliance_report(
        self,
        output_path: str,
        start_date: datetime,
        end_date: datetime,
    ) -> None:
        """Exportar reporte de compliance."""
        entries = self._audit_log.query(
            start_date=start_date,
            end_date=end_date,
        )

        report = {
            "period": f"{start_date.isoformat()} to {end_date.isoformat()}",
            "total_entries": len(entries),
            "action_breakdown": {},
            "risk_changes": [],
            "trade_decisions": 0,
        }

        for entry in entries:
            action = entry.action_type
            report["action_breakdown"][action] = report["action_breakdown"].get(action, 0) + 1

            if action == "RISK_PARAMETER_CHANGE":
                report["risk_changes"].append({
                    "timestamp": entry.timestamp.isoformat(),
                    "parameter": entry.details.get("parameter"),
                    "old": entry.details.get("old_value"),
                    "new": entry.details.get("new_value"),
                })

            if action == "TRADE_DECISION":
                report["trade_decisions"] += 1

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info("compliance_report_exported", path=output_path, entries=len(entries))