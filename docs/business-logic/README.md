# Lógica Empresarial - Business Logic

> Sistema de gestión de riesgos, portafolio y ejecución de órdenes

## Contenido

| Archivo | Descripción |
|---------|-------------|
| [risk-management.md](risk-management.md) | Sistema completo de gestión de riesgos |
| [portfolio-management.md](portfolio-management.md) | Gestión de capital y posiciones |
| [execution-engine.md](execution-engine.md) | Motores de ejecución Paper/Live |

---

## Flujo de Validación de Riesgo

```
┌─────────────────────────────────────────────────────────────────┐
│                  RISK VALIDATION FLOW                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Signal Received                                                │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────┐                   │
│  │ 1. Kill Switch Active?                  │                   │
│  │    YES → REJECT (reason: kill_switch)   │                   │
│  └─────────────────┬───────────────────────┘                   │
│                    │ NO                                         │
│                    ▼                                            │
│  ┌─────────────────────────────────────────┐                   │
│  │ 2. Daily Loss > 10%?                    │                   │
│  │    YES → TRIGGER KILL SWITCH + REJECT   │                   │
│  └─────────────────┬───────────────────────┘                   │
│                    │ NO                                         │
│                    ▼                                            │
│  ┌─────────────────────────────────────────┐                   │
│  │ 3. Drawdown > 20%?                      │                   │
│  │    YES → TRIGGER KILL SWITCH + REJECT   │                   │
│  └─────────────────┬───────────────────────┘                   │
│                    │ NO                                         │
│                    ▼                                            │
│  ┌─────────────────────────────────────────┐                   │
│  │ 4. Risk Exposure > 15%?                 │                   │
│  │    YES → REJECT (reason: max_exposure)  │                   │
│  └─────────────────┬───────────────────────┘                   │
│                    │ NO                                         │
│                    ▼                                            │
│  ┌─────────────────────────────────────────┐                   │
│  │ 5. R:R Ratio < 1.5?                     │                   │
│  │    YES → REJECT (reason: low_rr)        │                   │
│  └─────────────────┬───────────────────────┘                   │
│                    │ NO                                         │
│                    ▼                                            │
│  ┌─────────────────────────────────────────┐                   │
│  │ 6. Consecutive Losses > 7?              │                   │
│  │    YES → TRIGGER KILL SWITCH + REJECT   │                   │
│  └─────────────────┬───────────────────────┘                   │
│                    │ NO                                         │
│                    ▼                                            │
│              ✅ APPROVED                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Límites Configurados

```python
HARD_LIMITS = {
    "max_risk_per_trade_pct": 0.02,      # 2% por trade
    "max_portfolio_risk_pct": 0.15,       # 15% exposición total
    "max_daily_loss_pct": 0.10,           # 10% pérdida diaria
    "max_drawdown_pct": 0.20,             # 20% drawdown máximo
    "max_consecutive_losses": 7,          # 7 pérdidas consecutivas
    "min_risk_reward_ratio": 1.5,         # R:R mínimo
    "max_position_single_symbol_pct": 0.20, # 20% por símbolo
}
```

---

*Volver al [índice principal](../README.md)*
