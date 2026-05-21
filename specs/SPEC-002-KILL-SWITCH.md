# SPEC — Kill Switch System
**Fecha:** 2026-05-16 | **Versión:** 1.0 | **Estado:** DRAFT

---

## 1. RESUMEN EJECUTIVO

Sistema de emergencia que detiene completamente la operativa del sistema de trading cuando se alcanzan umbrales de riesgo predefinidos. Es el gate obligatorio antes de cualquier función de ejecución y tiene precedencia absoluta sobre cualquier otra lógica.

**Pertenece a:** Fase 1 - Secure Core Foundation | **Depende de:** SPEC-001 (Domain Entities)
**Bloquea:** SPEC-005 (Pipeline Scheduler)

---

## 2. OBJETIVOS

| # | Objetivo | Métrica de éxito |
|---|----------|------------------|
| O1 | Detectar pérdida diaria excesiva (>5%) | Activación en < 100ms |
| O2 | Detectar drawdown máximo (>15%) | Activación en < 100ms |
| O3 | Detectar pérdidas consecutivas (>5 trades) | Activación en < 100ms |
| O4 | Permitir reset manual por admin | Estado cambia a inactive |
| O5 | Persistir estado en Redis | Estado survive restart |

---

## 3. ESPECIFICACIÓN TÉCNICA

### 3.1 Interfaz pública

```python
class KillSwitch:
    def is_active(self) -> bool:
        """Retorna True si el kill switch está activo."""
        ...

    def check_and_trigger(
        self,
        daily_pnl_pct: float,
        drawdown_current: float,
        recent_trades: list,
    ) -> None:
        """Evalúa condiciones y activa si es necesario."""
        ...

    def reset(self, admin_token: str) -> None:
        """Reinicia el kill switch (solo admin)."""
        ...

    @property
    def state(self) -> KillSwitchState:
        """Estado actual del kill switch."""
        ...
```

### 3.2 Triggers

| Trigger | Condición | Acción |
|---------|-----------|--------|
| Daily Loss | daily_pnl_pct < -DAILY_LOSS_LIMIT_PCT | Activar |
| Max Drawdown | drawdown_current > MAX_DRAWDOWN_PCT | Activar |
| Consecutive Losses | consecutive_losses > MAX_CONSECUTIVE_LOSSES | Activar |

### 3.3 Estados

- **INACTIVE**: Operativa normal
- **ACTIVE**: Trading bloqueado, sin nuevas posiciones

---

## 4. CRITERIOS DE ACEPTACIÓN

| ID | Criterio | Test asociado |
|----|----------|---------------|
| CA-1 | Activación cuando daily loss > 5% | tests/unit/test_kill_switch.py::test_daily_loss_trigger |
| CA-2 | Activación cuando drawdown > 15% | tests/unit/test_kill_switch.py::test_drawdown_trigger |
| CA-3 | Activación cuando 5+ pérdidas consecutivas | tests/unit/test_kill_switch.py::test_consecutive_trigger |
| CA-4 | Solo admin puede resetear | tests/unit/test_kill_switch.py::test_admin_reset |
| CA-5 | Estado persiste en Redis | tests/integration/test_kill_switch_redis.py |

---

## 5. TRAZABILIDAD

| Versión | Fecha | Cambios | Autor |
|---------|-------|---------|-------|
| 1.0 | 2026-05-16 | Versión inicial | TRADER AI |

**ESTADO:** APPROVED