# 📋 ÍNDICE MAESTRO — PLAN DE EJECUCIÓN TRADER AI 2026
**Fecha de generación:** 2026-05-16  
**Últimas auditorías:** Técnica + Cuantitativa · 2026-05-16  
**Estado del sistema:** MVP roto (5.3/10 técnico, 3.85/10 cuantitativo)  
**Propósito:** Plan ejecutable, específico y detallado (NO genérico)

---

## 🚀 COMIENZA AQUÍ

### Para gestores/stakeholders (visión 30k pies)
👉 **Lee:** `RESUMEN_EJECUTIVO_PLAN_2026-05-16.md`
- Qué es el plan
- Por qué está roto el sistema
- Hoja de ruta a 24 semanas
- FAQs

⏱️ **Tiempo:** 10 minutos

---

### Para desarrolladores (implementación detallada)
👉 **Lee:** `PLAN_MAESTRO_EJECUCION_2026-05-16.md`
- Configuración real (28 activos, 4 exchanges)
- Quick Wins con código exacto (QW-TECH + QW-QUANT)
- Fases 0-7 con módulos específicos
- Investigaciones críticas (I1-I8)

⏱️ **Tiempo:** 1-2 horas (reference guide)

---

### Para esta semana (ejecución inmediata)
👉 **Lee:** `CHECKLIST_SEMANA1_2026-05-16.md`
- Tareas de lunes a viernes
- Qué arreglar primero (4 blockers críticos)
- Quick Wins prioritizados
- Commits sugeridos

⏱️ **Tiempo:** Seguir checklist mientras codeas

---

## 📑 DOCUMENTOS DISPONIBLES

| Documento | Tamaño | Propósito | Audience |
|-----------|--------|----------|----------|
| **RESUMEN_EJECUTIVO_PLAN_2026-05-16.md** | 12 KB | Visión ejecutiva | PMs, CTOs, Stakeholders |
| **PLAN_MAESTRO_EJECUCION_2026-05-16.md** | 84 KB | Detalles técnicos completos | Desarrolladores |
| **CHECKLIST_SEMANA1_2026-05-16.md** | 12 KB | Tareas diarias lunes-viernes | DevOps, Backend engineers |
| **AUDITORIA_TECNICA_2026-05-16.md** | (existente) | 30+ bugs identificados | QA, Architects |
| **AUDITORIA_CUANTITATIVA_CORE_2026-05-16.md** | (existente) | Edge + estrategias análisis | Quants, ML engineers |

---

## 🎯 LOS 4 PROBLEMAS BLOQUEANTES

### 🔴 Blocker 1: Base de datos nunca se inicializa
- **Problema:** `init_pool()` comentado en `api/main.py`
- **Impacto:** Sistema pierde TODOS los datos (órdenes, señales, portfolio) al reiniciar
- **Solución:** Semana 2 (M1.1) — Activar BD + migraciones Alembic
- **Referencia:** PLAN_MAESTRO §M1.1

### 🔴 Blocker 2: Pipeline autónomo desactivado
- **Problema:** `APScheduler` comentado en `api/main.py`
- **Impacto:** Sistema es un servidor estático, no ejecuta trading automáticamente
- **Solución:** Semana 2-3 (M1.3) — Reactivar APScheduler con 5 jobs
- **Referencia:** PLAN_MAESTRO §M1.3

### 🔴 Blocker 3: POST /execution falla en runtime
- **Problema:** `explanation=None` no válido + Signal/dict mismatch
- **Impacto:** Imposible ejecutar órdenes, endpoint crashea
- **Solución:** Semana 1 (QW-TECH-2) — 2 horas, fix de tipo
- **Referencia:** CHECKLIST Martes 2026-05-17

### 🔴 Blocker 4: JWT sin validación en producción
- **Problema:** `and False` desactiva validador de JWT secret
- **Impacto:** Cualquiera puede forjar tokens JWT con secret conocido
- **Solución:** Semana 1 (QW-TECH-1) — 1 hora, eliminar `and False`
- **Referencia:** CHECKLIST Lunes 2026-05-16

---

## 📊 CRONOGRAMA A VISTA DE PÁJARO

```
SEMANA 1  (Hoy - 2026-05-22)
├── Lunes:     QWT-1,3,5,7           (JWT, Docker, Binance, async)
├── Martes:    QWT-2,4,10            (execution fix, user_id, validate_signal)
├── Miércoles: QWT-6,8               (rate limiting, parquet async)
├── Jueves:    QWT-9 + QWQ-1,2       (auth, features lagged, target ternario)
├── Viernes:   QWQ-3,4,5,6,7,8,9     (embargo, ADX, Hurst, SL/TP, cooldown, risk, annualization)
└── Resultado: ✅ Sistema operativo base, 0 crashes críticos

SEMANA 2-3 (Fase 1 — Secure Core Foundation)
├── Lunes-Martes:   M1.1 Database + Alembic (12h)
├── Martes-Miércoles: M1.2 Auth JWT completa (8h)
├── Miércoles-Viernes: M1.3 APScheduler pipeline (16h)
├── Siguiente:      M1.4 Paper executor (8h) + M1.5 Redis (8h)
└── Resultado: ✅ Primera orden ejecutada en paper mode

SEMANA 4-6 (Fase 2 — Quant Infrastructure)
├── Features V2, Feature Store, validación, backtesting
├── Investigación I1: ¿Existe edge real? (Sharpe OOS > 0.8)
└── Resultado: ✅ Sharpe OOS neto > 0.8 O pivotear

SEMANA 7-9 (Fase 3 — Quant Intelligence)
├── HMM real, consensus dinámico, model validation gate
└── Resultado: ✅ Modelos con validación estadística correcta

SEMANA 10-24 (Fases 4-7 — SOLO si I1 pasa)
├── Multi-estrategia, risk 2.0, RL, live trading
└── Resultado: ✅ Sharpe > 1.0 verificado 60 días en live
```

---

## 🎓 MÉTRICAS DE ÉXITO

| Fase | Cuándo | Hito | Métrica |
|------|--------|------|---------|
| **Quick Wins** | Semana 1 | Sistema operativo | 0 crashes, CI verde |
| **Fase 1** | Semana 3 | Pipeline autónomo | 10+ órdenes/día en papel |
| **Fase 2** | Semana 6 | Edge verificado | Sharpe OOS > 0.8, p < 0.05 |
| **Fase 3** | Semana 9 | Modelos productivos | HMM + consensus dinámico |
| **Fase 4** | Semana 12 | Multi-estrategia | Sharpe ensemble > 0.8 |
| **Fase 5** | Semana 15 | Risk 2.0 | CVaR activo, DD < 15% |
| **Fase 6** | Semana 19 | Auto-adaptación | Drift detection activo |
| **Fase 7** | Semana 24 | Trading real | Sharpe > 1.0 en 60 días |

---

## 🚨 GATE CRÍTICO: INVESTIGACIÓN I1

**Cuándo:** Fin de semana 5-6 (después de Fase 2)

**Pregunta:** ¿El sistema genera **Sharpe neto > 0.8** después de costos reales de transacción?

**Método:**
```
Walk-forward validation con:
├── Embargo temporal: 5 barras mínimo
├── Purged K-Fold: eliminar data leak
├── Costos reales: commission + slippage por exchange/activo
├── Bootstrap: 1000 permutaciones para p-value
└── Resultado: Sharpe OOS + p-value + max drawdown
```

**¿Si pasa (Sharpe > 0.8)?** → Continúa a Fase 4 con confianza  
**¿Si falla (Sharpe ≤ 0.8)?** → **STOP** — replantear features, modelos, estrategias ANTES de invertir más tiempo en Fase 4-7

---

## 🌍 ECOSISTEMA: 4 EXCHANGES × 28 ACTIVOS

### Exchanges
```
✅ Binance         (Crypto spot, futures)  → BTC, ETH, SOL, BNB
✅ OANDA          (Forex + Indices + Commodities) → 40+ pares
✅ MetaTrader 5   (Forex IC Markets + Commodities) → 20+ pares
✅ Bybit          (Crypto perps)  → BTC, ETH, SOL, BNB futures
```

### Activos
```
Crypto (4):        BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT
Forex (6):         EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD
Indices (6):       SPX500, NAS100, US30, DE40, UK100, JP225
Commodities (6):   XAUUSD, XAGUSD, USOIL, UKOIL, NATGAS, WHEAT
```

### Estrategias builtin (4)
```
✅ EMA+RSI         (trend confirmation)
✅ Mean Reversion  (oversold/overbought)
✅ TSMOM          (time-series momentum)
✅ Vol Breakout   (post-consolidation breakouts)
```

---

## 💾 RUTAS IMPORTANTES

| Recurso | Ruta |
|---------|------|
| Plan maestro detallado | `docs/PLAN_MAESTRO_EJECUCION_2026-05-16.md` |
| Resumen ejecutivo | `docs/RESUMEN_EJECUTIVO_PLAN_2026-05-16.md` |
| Checklist semana 1 | `docs/CHECKLIST_SEMANA1_2026-05-16.md` |
| Auditoría técnica | `docs/AUDITORIA_TECNICA_2026-05-16.md` |
| Auditoría cuantitativa | `docs/AUDITORIA_CUANTITATIVA_CORE_2026-05-16.md` |
| Prompt maestro | `TRADER_AI_PROMPT_MAESTRO.md` |
| Configuración del sistema | `core/config/settings.py`, `constants.py` |
| Modelos de datos | `core/models.py` |
| Estrategias | `core/strategies/builtin/` |

---

## 🆘 PREGUNTAS FRECUENTES

**P: ¿Comienzo por dónde?**  
R: Lee RESUMEN_EJECUTIVO (10 min) → sigue CHECKLIST_SEMANA1 (hoy) → luego PLAN_MAESTRO para detalles.

**P: ¿Cuánto tiempo hasta primeras órdenes en papel?**  
R: ~20 días (Quick Wins + Fase 1) si el equipo es dedicado full-time.

**P: ¿Y si tengo un bug diferente a los listados?**  
R: Documenta el bug, agrégalo a la auditoría técnica, prioriza según impacto.

**P: ¿Puedo saltarme Fase 2 (validación estadística)?**  
R: **NO.** La Fase 2 detecta si hay edge real. Sin ella, el sistema probablemente falla en live.

**P: ¿Cuál es el riesgo más grande?**  
R: **Overfitting silencioso.** Por eso la Fase 2 es crítica. I1 lo detectará.

---

## 📞 CONTACTO Y ESCALACIÓN

| Rol | Responsabilidad | Escalación |
|-----|-----|-----------|
| **CTO / Lead Architect** | Autorizar todos los cambios de Fase 0 | Cambios en estructura de DB |
| **Quant Lead** | Validar investigaciones I1-I8 | Descubrir que edge no existe |
| **DevOps** | Desplegar migraciones, CI/CD gates | Problemas de infra, secrets |
| **QA Lead** | Verificar que PR cumplen quality gates | Tests fallando en CI |

---

## ✅ PRÓXIMO PASO

1. **Abre:** `RESUMEN_EJECUTIVO_PLAN_2026-05-16.md` (10 min)
2. **Luego:** `CHECKLIST_SEMANA1_2026-05-16.md` (comienza QW-TECH-1)
3. **Esta noche:** Merge de QWT-1 (JWT validator fix)
4. **Mañana:** QWT-2,3,5 (execution fix, docker, binance)
5. **Viernes:** 10/10 Quick Wins completados
6. **Próxima semana:** Fase 1 inicia

---

**Plan maestro creado:** 2026-05-16 por auditorías técnica + cuantitativa  
**Versión:** 2.1 (especializado con exchanges, activos, código exacto)  
**Estado:** ✅ LISTO PARA IMPLEMENTAR

🚀 **¡QUE EMPIECE LA REVOLUCIÓN!**
