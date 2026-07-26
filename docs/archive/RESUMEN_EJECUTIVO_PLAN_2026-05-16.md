# RESUMEN EJECUTIVO — PLAN MAESTRO ESPECIALIZADO
**Fecha:** 2026-05-16 · **Versión:** 2.1 · **Léase primero este documento**

---

## ¿QUÉ ES ESTE PLAN?

Un plan de implementación **detallado, específico y ejecutable** para TRADER AI que:
- ✅ Incluye los **28 activos reales** (crypto, forex, índices, commodities)
- ✅ Integra los **4 exchanges** ya configurados (Binance, OANDA, MT5, Bybit)
- ✅ Detalla las **4 estrategias builtin** existentes
- ✅ Proporciona **código exacto** para cada módulo (no solo lineamientos genéricos)
- ✅ Incluye **cronograma detallado** por semana y por exchange
- ✅ Define **quick wins ejecutables** (QW-TECH y QW-QUANT) con esfuerzo preciso

---

## EL ESTADO ACTUAL EN UNA IMAGEN

```
┌─────────────────────────────────────────────────────────┐
│ TRADER AI v2.0 — Estado Actual                          │
├─────────────────────────────────────────────────────────┤
│                                                           │
│ Arquitectura: ⭐⭐⭐⭐⭐ (bien diseñada)                   │
│ Implementación: ⭐⭐⭐ (50% avance)                       │
│ Seguridad: ⭐⭐ (CRÍTICA — JWT sin validar)             │
│ BD: ⭐ (nunca se inicializa)                            │
│ Pipeline: ⭐ (completamente comentado)                  │
│ Edge cuantitativo: ⭐⭐ (débil, features genéricas)      │
│                                                           │
│ Resultado: MVP ROTO (no opera como plataforma)          │
│           Score técnico: 5.3/10                          │
│           Score cuantitativo: 3.85/10                    │
└─────────────────────────────────────────────────────────┘
```

---

## LOS 4 PROBLEMAS BLOQUEANTES

| # | Blocker | Impacto | Semana Fix |
|---|---------|--------|-----------|
| 🔴 | **Base de datos nunca inicializa** — `init_pool` comentado | Sistema pierde TODO al reiniciar | Semana 2 (M1.1) |
| 🔴 | **Pipeline autónomo desactivado** — APScheduler comentado | Sistema NO opera, es un servidor estático | Semana 2-3 (M1.3) |
| 🔴 | **POST /execution falla en runtime** — Signal/dict mismatch + explanation=None | Imposible ejecutar órdenes | QW-TECH-2 (semana 1) |
| 🔴 | **JWT sin validación (`and False`)** — Tokens forjables | Cualquiera puede ejecutar trading | QW-TECH-1 (semana 1) |

**Impacto total:** Sistema no operativo hasta semana 3.  
**Solución:** Quick Wins (sem 1) → Fase 1 (sem 2-3) → primeras órdenes en papel en el día 20.

---

## HOJA DE RUTA (A VISTA DE PÁJARO)

```
SEMANA 1: 🟢 Quick Wins (21h tech + 15d quant)
│         ├── JWT, DB docker, execution fix, auth endpoints
│         ├── Features (retornos, target ternario, ADX, Hurst)
│         └── Resultado: sistema inicia sin errores críticos
│
SEMANA 2-3: 🟡 Fase 1 — Secure Core Foundation (56h)
│           ├── Database: migraciones, repositorios
│           ├── Auth: JWT + token blacklist + /auth/register
│           ├── Pipeline: APScheduler con 5 jobs automáticos
│           ├── Executor: simula fills para Binance + OANDA
│           └── Resultado: primera orden ejecutada en paper mode
│
SEMANA 4-6: 🟡 Fase 2 — Quant Infrastructure (90h)
│           ├── Features V2: 35+ indicadores sin look-ahead
│           ├── Feature Store: versionado con detección de drift
│           ├── Validación: purged k-fold + embargo + walk-forward
│           ├── Backtesting: costos reales, métricas correctas
│           └── I1 investigación: ¿existe edge real?
│
SEMANA 7-9: 🟡 Fase 3 — Quant Intelligence (116h)
│           ├── HMM: 8 estados en lugar de if/else
│           ├── Consensus: pesos dinámicos por agente
│           ├── Models: validación gate antes de deployment
│           └── Observabilidad: Grafana + alertas reales
│
SEMANA 10-24: 🔵 Fases 4-7 (solo si I1 demuestra edge)
              ├── Fase 4: Multi-estrategia + meta-agente
              ├── Fase 5: Risk Engine 2.0 (CVaR, correlaciones)
              ├── Fase 6: Adaptación automática + RL
              └── Fase 7: Live con capital limitado

⛔ GATE CRÍTICO: Si I1 (Sharpe OOS neto > 0.8) FALLA → replantear estrategia
```

---

## QUICK WINS — PRIMERAS 72 HORAS

Estos fixes desbloquean TODO lo demás. Hacer en paralelo:

### QW-TECH (Técnicos) — 21 horas

| ID | Fix | Tiempo | Beneficio inmediato |
|----|-----|--------|---------------------|
| **QWT-1** 🔴 | Eliminar `and False` en JWT validator | 1h | Sistema no puede forjar tokens |
| **QWT-2** 🔴 | Fix `explanation=None` en Signal | 2h | `POST /execution` funciona |
| **QWT-3** 🔴 | Fix `docker-compose.yml` (eliminar líneas duplicadas) | 1h | Docker compose parse correcto |
| **QWT-4 a 10** | Rate limiting, async fixes, auth endpoints | 16h | Sistema operativo base |

**Resultado:** "Hola, soy un servidor FastAPI que puedo recibir órdenes"

---

### QW-QUANT (Cuantitativos) — 15 días

| ID | Feature | Activos | Tiempo |
|----|---------|---------|--------|
| **QWQ-1,2,3** | Retornos lagged + target ternario + embargo | Todos | 1 semana |
| **QWQ-4,5** | ADX + Hurst exponent | Todos | 3 días |
| **QWQ-6,7,8** | SL/TP dinámicos + cooldown + risk real | Todos | 2 días |

**Resultado:** "Las señales tienen menos ruido y la validación detecta overfitting"

---

## EXCHANGES Y ACTIVOS — HOJA DE RUTA DETALLADA

### Fase 1 (Paper mode — todas las semanas 2-3)

```
Binance (Crypto — spot)
├── BTCUSDT  [BTC] — Bitcoin — Spread: 10 pips, Slippage: 0.1%
├── ETHUSDT  [ETH] — Ethereum
├── SOLUSDT  [SOL] — Solana
└── BNBUSDT  [BNB] — BNB

OANDA (Forex + Indices + Commodities)
├── EURUSD   — Euro/USD — Spread: 0.5 pips, Slippage: 0.01%
├── GBPUSD   — Pound/USD
├── USDJPY   — USD/Yen (point: 0.001)
├── SPX500   — S&P 500
├── XAUUSD   — Gold/USD
└── USOIL    — WTI Oil (muy volátil)

Totales Fase 1: 11 activos × 4 timeframes = 44 pares de entrenamiento
```

**Indicadores por activo (Fase 1):**

```
CRYPTO (Binance):
├── Features técnicas: EMA50, EMA200, RSI, MACD, ATR, Bollinger
├── Features cuantitativas (NEW): retornos lagged, Hurst, skewness, kurtosis
├── Estrategias: EMA+RSI, TSMOM, Vol Breakout
└── Validación: walk-forward en últimas 2 años de datos

FOREX (OANDA):
├── Features técnicas: todos (+ muchos resets diarios)
├── Features cuantitativas: ciclos hora del día (London, NY, Tokyo)
├── Estrategias: EMA+RSI, Mean Reversion, TSMOM
└── Validación: walk-forward en últimos 2-3 años

INDICES + COMMODITIES (OANDA):
├── Features técnicas: todas
├── Features cuantitativas: seasonal patterns (XAUUSD, USOIL)
├── Estrategias: Vol Breakout, TSMOM
└── Validación: walk-forward según disponibilidad histórica
```

---

## INVESTIGACIÓN CRÍTICA I1 — "¿EXISTE EDGE ESTADÍSTICO?"

**Cuándo:** Semana 5-6 (después de Fase 2)

**Pregunta:** ¿El sistema genera Sharpe > 0.8 NETO de costos de transacción?

**Método:**
```python
Backtest walk-forward:
├── Train: 252 barras (1 año 1h para crypto)
├── Test: 30 barras (1 mes)
├── Embargo: 5 barras entre train/test
├── Costos: commission + slippage reales por activo
├── Bootstrap: 1000 permutaciones para p-value
└── Resultado: Sharpe OOS + p-value + drawdown máximo

Criterio de éxito: Sharpe > 0.8, p-value < 0.05, DD < 20%
```

**¿Si falla?** → Replantear features, modelos y estrategias antes de continuar a Fase 4

**¿Si pasa?** → Proceder con confianza a multi-estrategia + meta-agente

---

## CRONOGRAMA REALISTA

```
HOY (Semana 1):
└── Lunes-Viernes: QW-TECH (21h) + QW-QUANT Fase 1 (4 días)
    Objetivo: Sistema CI verde, no hay crashes críticos

SEMANA 2:
└── Lunes-Viernes: Fase 1, Parte 1
    ├── Lunes: DB + migraciones Alembic (12h)
    ├── Martes: Auth JWT completa (8h)
    └── Miércoles: APScheduler pipeline (8h)
    Objetivo: Database persiste datos

SEMANA 3:
└── Lunes-Viernes: Fase 1, Parte 2
    ├── Lunes-Martes: Paper executor multi-exchange (8h)
    ├── Miércoles-Viernes: Redis + testing (16h)
    Objetivo: Primera orden ejecutada en BTC

SEMANA 4-6:
└── Fase 2: Quant Infrastructure + I1 investigación
    Objetivo: Sharpe OOS > 0.8 o plan B

DÍA 20: 🎉 HITO CRÍTICO: Primera orden en papel generada autónomamente desde el código
        (sin intervención manual, sin clicking buttons)
```

---

## MÉTRICAS DE ÉXITO POR FASE

| Fase | Semanas | Hito | Métrica de éxito |
|------|---------|------|-----------------|
| **Quick Wins** | 1 | Sistema operativo base | 0 errores críticos en CI |
| **Fase 1** | 2-3 | Pipeline autónomo | 10+ órdenes en papel/día |
| **Fase 2** | 4-6 | Edge verificado | Sharpe OOS > 0.8, p < 0.05 |
| **Fase 3** | 7-9 | Modelos productivos | HMM real + consensus dinámico |
| **Fase 4** | 10-12 | Multi-estrategia | Sharpe ensemble > 0.8 |
| **Fase 5** | 13-15 | Risk 2.0 | CVaR implementado, DD < 15% |
| **Fase 6** | 16-19 | Adaptación automática | Drift detection activo |
| **Fase 7** | 20-24 | Trading real | Sharpe > 1.0 en live 60 días |

---

## RECURSOS CLAVE

| Recurso | Ubicación | Propósito |
|---------|-----------|----------|
| **Plan maestro completo** | `docs/PLAN_MAESTRO_EJECUCION_2026-05-16.md` | Detalles técnicos de cada módulo |
| **Auditoría técnica** | `docs/AUDITORIA_TECNICA_2026-05-16.md` | Lista de 30+ bugs y hallazgos |
| **Auditoría cuantitativa** | `docs/AUDITORIA_CUANTITATIVA_CORE_2026-05-16.md` | Análisis de edge y estrategias |
| **Prompt maestro** | `TRADER_AI_PROMPT_MAESTRO.md` | Principios inviolables del proyecto |
| **Este documento** | `docs/RESUMEN_EJECUTIVO_PLAN_2026-05-16.md` | Visión de 30k pies |

---

## PREGUNTAS FRECUENTES

**P: ¿Cuánto tiempo hasta operar con capital real?**  
R: 24 semanas (~6 meses) si todo sale según plan. Incluye validación estadística rigurosa (sin atajos).

**P: ¿Y si I1 falla (edge real no existe)?**  
R: Replantear features, modelos y régimen detection. No saltarse a Fase 4 sin edge verificado (riesgo de pérdida real).

**P: ¿Puedo hacer live trading antes de Fase 7?**  
R: **NO.** El sistema no está validado. Espera a 60+ días de paper trading con Sharpe > 1.0 verificado.

**P: ¿Por qué tanto énfasis en validación estadística?**  
R: El 90% de sistemas de trading fracasan por overfitting silencioso. Este plan prioriza robustez sobre velocidad.

**P: ¿Qué pasa si una estrategia builtin falla?**  
R: Es normal. Se desactiva vía strategy_rotation_engine, se investiga en I3-I5, y se pivotea a otra.

**P: ¿Necesito capital para comenzar?**  
R: No, durante semanas 1-19 es todo paper mode (gratis, solo datos históricos). Capital real en Fase 7, cuando el sistema esté validado.

---

## SIGUIENTE PASO

1. **Lee esto completamente** ← estás aquí
2. **Lee el plan maestro completo** (`docs/PLAN_MAESTRO_EJECUCION_2026-05-16.md`)
3. **Comienza con QW-TECH-1, 2, 3** (3 horas, máximo impacto)
4. **En paralelo: QW-QUANT Fase 1** (features lagged + target ternario + embargo)
5. **En paralelo: Fase 0** (estructura, CI/CD, governance)
6. **Reporta progreso cada fin de semana**

---

**Generado:** 2026-05-16  
**Próxima revisión:** tras completar QW-TECH (fin de semana 1)  
**Preguntas:** consulta al PM o CTO  

**GO GO GO! 🚀**
