# Architecture Decision Records

Decisiones arquitectónicas del sistema. Formato: `Estado · Contexto · Decisión · Consecuencias · Alternativas consideradas`.
Origen del proceso: `docs/PLAN_ELEVACION_MADUREZ_2026-08-28.md` (F0) y `docs/governance/README.md` §4.2.

| ADR | Título | Estado | Fase |
|---|---|---|---|
| ADR-001 | Monolito modular con 2 procesos (API + worker), no microservicios | Pendiente | F3 (3.4) |
| ADR-002 | `core/` como paquete único de dominio+aplicación; se elimina `domain/application/infrastructure/interfaces` | Pendiente | F3 (3.1) |
| [ADR-003](ADR-003-decision-pipeline-y-estrategias.md) | El core de decisión es "agentes + consenso"; las estrategias son parametrizaciones validadas por el gate I1 | Aceptado | F0 |
| [ADR-004](ADR-004-universo-activos-canonico.md) | Universo de activos canónico y nomenclatura de índices | Aceptado | F0 |
| [ADR-005](ADR-005-fail-safe-y-fail-open.md) | Kill switch fail-safe obligatorio; blacklist de JWT fail-open aceptada | Aceptado | F0 |
| ADR-006 | Trace de decisión por `correlation_id` persistido en todas las tablas | Pendiente | F3 (3.4) |
| ADR-007 | Ruta a producción: Backtest → OOS → Stress → Paper ≥4 semanas → Capital limitado supervisado | Pendiente | F3 (3.4) |
| ADR-008 | (condicional) Saca forex/índices/oro del alcance si no pasaron el GATE F2 | Pendiente | F4 (4.2) |
