# AUDIT F&lt;n&gt; — &lt;Título de la fase&gt;

> Plantilla estándar de auditoría de cierre de fase del `docs/PLAN_ELEVACION_MADUREZ_2026-08-28.md`.
> Copiar a `docs/audits/AUDIT_F<n>_<AAAA-MM-DD>.md` y completar. No cerrar una fase sin este documento y un veredicto.

- **Fase:** F&lt;n&gt; — &lt;nombre&gt;
- **Fecha de auditoría:** &lt;AAAA-MM-DD&gt;
- **Commit auditado:** `<hash>` (`<rama>`)
- **Auditor:** &lt;sesión / persona&gt;
- **Alcance:** &lt;rutas y módulos acotados a la fase&gt;
- **Baseline de comparación:** `docs/audits/BASELINE_2026-08-28.md` + `AUDIT_F<n-1>_*.md`

---

## Veredicto global

| Veredicto | | 
|---|---|
| **GO** / **GO CON CONDICIONES** / **NO-GO** | &lt;marcar&gt; |

**Resumen (3–5 líneas):** &lt;qué se cumplió, qué no, condición para avanzar&gt;

Si **GO CON CONDICIONES**: listar ≤2 hallazgos menores con fecha de cierre comprometida.
Si **NO-GO**: nombrar el criterio bloqueante incumplido y la acción correctiva.

---

## Parte 1 — Checklist objetivo

Comandos reproducibles con salida esperada. Cada fase define el suyo (ver el plan).

| # | Comando / verificación | Salida esperada | Resultado | OK? |
|---|---|---|---|---|
| 1 | `<comando>` | `<esperado>` | `<obtenido>` | ✅ / ❌ |
| 2 | | | | |

Tests que deben estar verdes (de la sección "Auditoría de cierre" de la fase):

| Test | Estado |
|---|---|
| `<ruta::test>` | ✅ / ❌ |

---

## Parte 2 — Pase de auditoría fresco

Sesión nueva de Claude Code aplicando `TRADER_AI_PROMPT_MAESTRO.md` acotado al alcance de la fase, **sin contexto de la implementación**, verificando contra el código.

- **Prompt/alcance usado:** &lt;texto&gt;
- **Hallazgos del pase fresco:**

| ID | Área | Hallazgo | Evidencia (`archivo:línea`) | Severidad | Veredicto |
|---|---|---|---|---|---|
| A-01 | | | | P0/P1/P2/P3 | Abierto / Aceptado / Falso positivo |

---

## Parte 3 — No-regresión

Re-verificar que ningún hallazgo `GO` previo se reabrió (auditorías 2026-05, 07, 08 y fases anteriores).

| Hallazgo previo | Fuente | Estado esperado | Estado actual | Evidencia |
|---|---|---|---|---|
| `<F-xx / D-xx / G-xx>` | `AUDITORIA_*` | Resuelto | Resuelto / **REABIERTO** | `archivo:línea` |

---

## Matriz de hallazgos (consolidada)

| ID | Área | Hallazgo | Evidencia | Severidad | Veredicto |
|---|---|---|---|---|---|
| | | | | | |

---

## Score de madurez por área (delta vs baseline)

| Área | Baseline | Objetivo de la fase | Medido | Δ |
|---|---|---|---|---|
| &lt;área&gt; | 0.0 | 0.0 | 0.0 | +0.0 |

**Score global:** baseline &lt;x&gt; → medido &lt;y&gt;.

---

## Anexos

- Salidas completas de comandos: &lt;enlace o bloque&gt;
- Artefactos generados: &lt;reportes, JSON, etc.&gt;
