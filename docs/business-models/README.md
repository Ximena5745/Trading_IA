# Lógica de Negocio - Modelos

> Modelos de datos, agentes de IA y motor de consenso

## Contenido

| Archivo | Descripción |
|---------|-------------|
| [data-models.md](data-models.md) | Modelos Pydantic del dominio |
| [agent-system.md](agent-system.md) | Sistema multi-agente IA |
| [consensus-engine.md](consensus-engine.md) | Motor de votación ponderada |

---

## Resumen de Modelos

### Modelo de Datos Central

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA MODELS                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MarketData ───────► FeatureSet ───────► AgentOutput            │
│  (OHLCV)              (17+ features)     (score, SHAP)         │
│                                                 │               │
│                                                 ▼               │
│                                           ConsensusOutput       │
│                                           (weighted vote)       │
│                                                 │               │
│                                                 ▼               │
│                                             Signal              │
│                                           (entry, SL, TP)      │
│                                                 │               │
│                                                 ▼               │
│                                              Order              │
│                                            (execution)          │
│                                                 │               │
│                                                 ▼               │
│                                            Position             │
│                                          (portfolio)            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Enumeraciones Principales

| Enum | Valores |
|------|---------|
| AssetClass | CRYPTO, FOREX, INDICES, COMMODITIES |
| MarketRegime | BULL_TRENDING, BEAR_TRENDING, SIDEWAYS_LOW_VOL, SIDEWAYS_HIGH_VOL, VOLATILE_CRASH |
| OrderStatus | PENDING, SUBMITTED, PARTIAL, FILLED, CANCELLED, REJECTED, EXPIRED |

---

*Volver al [índice principal](../README.md)*
