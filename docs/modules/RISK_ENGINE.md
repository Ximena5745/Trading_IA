# Módulo: Risk Engine

> Gestión de riesgo, validación de señales y protecciones

---

## 1. OBJETIVO

Proveer un sistema completo de gestión de riesgo que valide señales contra límites, calcule position sizing, maneje el kill switch y proporcione protección contra drawdown.

---

## 2. RESPONSABILIDADES

| Responsabilidad | Descripción |
|----------------|-------------|
| Signal Validation | Validar SL/TP/RR antes de aceptar |
| Position Sizing | Calcular tamaño de posición |
| Kill Switch | Emergency stop automático |
| Drawdown Protection | Límites de drawdown |
| Risk Limits | Límites hard-coded |

---

## 3. ARQUITECTURA INTERNA

```
┌─────────────────────────────────────────────────────────────────┐
│                       RISK LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                      RiskManager                         │ │
│  │  - Signal validation                                      │ │
│  │  - Risk limits                                            │ │
│  │  - Decision making                                         │ │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                      │
│  ┌──────────────────────┼───────────────────────────────────┐  │
│  │     KillSwitch       │    PositionSizer                  │  │
│  │  - Daily loss        │    - Fixed fraction               │  │
│  │  - Drawdown          │    - Kelly criterion              │  │
│  │  - Consecutive       │    - Volatility based             │  │
│  │  - Manual            │                                    │  │
│  └──────────────────────┼───────────────────────────────────┘  │
│                         │                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ AutoAdaptation│ │ UserProfile  │ │ PortfolioRisk│        │
│  │              │ │   Engine     │ │    Engine    │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. COMPONENTES

### 4.1 RiskManager

**Archivo:** `core/risk/risk_manager.py`

**Propósito:** Validador central de señales contra reglas de riesgo.

```python
class RiskManager:
    async def validate_signal(
        self,
        signal: Signal,
        portfolio: Portfolio
    ) -> ValidationResult: ...
    
    async def calculate_position_size(
        self,
        signal: Signal,
        portfolio: Portfolio,
        risk_per_trade: float
    ) -> float: ...
    
    def check_limits(self, portfolio: Portfolio) -> LimitCheck: ...
```

**Validaciones:**
| Validación | Regla | Acción en fail |
|------------|-------|----------------|
| Max risk per trade | ≤ 2% | REJECT |
| Min risk-reward | ≥ 1.5 | REJECT |
| Max portfolio risk | ≤ 15% | REJECT |
| Max daily loss | ≤ 10% | KILL_SWITCH |
| Max drawdown | ≤ 20% | KILL_SWITCH |

### 4.2 KillSwitch

**Archivo:** `core/risk/kill_switch.py`

**Triggers automáticos:**
| Trigger | Condición | Recuperación |
|---------|-----------|--------------|
| Daily loss | > 10% | Auto a medianoche |
| Drawdown | > 20% | Manual |
| Consecutive losses | 7+ | Auto tras 1 win |
| Manual | Admin only | Manual |

**Estado:**
```python
class KillSwitchState:
    is_active: bool
    triggers: dict[str, datetime]
    last_reset: datetime
```

### 4.3 PositionSizer

**Archivo:** `core/risk/position_sizer.py`

**Métodos soportados:**

| Método | Descripción |
|--------|-------------|
| Fixed Fraction | % fijo del capital |
| Kelly Criterion | Fracción óptima de Kelly |
| Volatility Based | Basado en ATR |
| Equal Weight | Mismo tamaño para todos |

**Fórmula Kelly:**
```
f* = (bp - q) / b
donde:
  b = odds (risk-reward ratio)
  p = probabilidad de win
  q = 1 - p
```

### 4.4 AutoAdaptation

**Archivo:** `core/risk/auto_adaptation.py`

**Propósito:** Auto-tuning de parámetros basado en performance.

```python
class AutoAdaptation:
    async def adjust_params(
        self,
        strategy_id: str,
        performance: PerformanceMetrics
    ) -> dict: ...
    
    async def should_rebalance(
        self,
        portfolio: Portfolio
    ) -> bool: ...
```

### 4.5 UserProfileEngine

**Archivo:** `core/risk/user_profile_engine.py`

**Perfiles:**
| Perfil | Risk per Trade | Max Positions |
|--------|----------------|---------------|
| Conservative | 1% | 3 |
| Moderate | 2% | 5 |
| Aggressive | 3% | 10 |

### 4.6 PortfolioRiskEngine

**Archivo:** `core/risk/portfolio_risk_engine.py`

**Métricas:**
- VaR (Value at Risk)
- Expected shortfall
- Correlation-adjusted risk
- Sector exposure

### 4.7 VolatilityTargeting

**Archivo:** `core/risk/volatility_targeting.py`

**Propósito:** Mantener volatilidad del portfolio en target.

```python
class VolatilityTargeting:
    def calculate_position_scalar(
        self,
        current_vol: float,
        target_vol: float
    ) -> float: ...
```

---

## 5. HARD LIMITS

> Estos límites NO pueden modificarse sin code review.

```python
# core/config/constants.py
HARD_LIMITS = {
    "max_risk_per_trade_pct": 0.02,        # 2%
    "max_portfolio_risk_pct": 0.15,       # 15%
    "max_daily_loss_pct": 0.10,           # 10%
    "max_drawdown_pct": 0.20,             # 20%
    "max_consecutive_losses": 7,
    "min_risk_reward_ratio": 1.5,
    "max_positions": 10,
    "min_position_size": 10.0,            # USD
}
```

---

## 6. EVENTOS

### 6.1 Eventos Publicados

| Evento | Descripción | Payload |
|--------|-------------|---------|
| `risk.signal_validated` | Resultado validación | `{signal, result, reason}` |
| `risk.kill_switch_triggered` | Kill switch activado | `{trigger, value}` |
| `risk.position_resized` | Posición ajustada | `{original, new}` |
| `risk.limit_warning` | Cerca de límite | `{limit, current, threshold}` |

### 6.2 Eventos Consumidos

| Evento | Descripción |
|--------|-------------|
| `signal.generated` | Nueva señal |
| `order.filled` | Orden ejecutada (actualizar P&L) |
| `portfolio.updated` | Actualizar exposición |

---

## 7. INPUTS/OUTPUTS

### 7.1 Inputs

| Input | Tipo | Descripción |
|-------|------|-------------|
| Signal | Signal | Señal a validar |
| Portfolio | Portfolio | Estado actual |
| Market data | pd.DataFrame | Datos para sizing |
| User profile | str | Perfil de riesgo |

### 7.2 Outputs

| Output | Destino | Descripción |
|--------|---------|-------------|
| Validation result | Signal Engine | Aprobada/Rechazada |
| Position size | Execution | Tamaño calculado |
| Kill switch status | API | Estado actual |

---

## 8. CASOS EDGE

| Caso | Manejo |
|------|--------|
| Signal sin SL/TP | REJECT (requerido) |
| RR < 1.5 | REJECT |
| Portfolio risk > 15% | REJECT o reducir posición |
| Kill switch activo | REJECT todas las señales |
| Position < min | REJECT |

---

## 9. RIESGOS

| Riesgo | Impacto | Mitigación |
|--------|---------|-------------|
| Limits bypassed | Crítico | Hard-coded, no config |
| Calculation error | Alto | Try-except + defaults |
| Race conditions | Medio | Lock en estado |

---

## 10. PERFORMANCE

| Métrica | Target |
|---------|--------|
| Validation time | < 10ms |
| Kill switch check | < 1ms |
| Position calculation | < 5ms |

---

## 11. OBSERVABILIDAD

### 11.1 Métricas

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `risk.signals.validated` | Counter | Señales validadas |
| `risk.signals.rejected` | Counter | Señales rechazadas |
| `risk.rejection.reasons` | Counter | Razones de rechazo |
| `risk.kill_switch.triggered` | Counter | Activaciones |
| `risk.position_size` | Histogram | Tamaños calculados |

### 11.2 Logs

```json
{
  "event": "signal_validated",
  "signal_id": "sig_123",
  "result": "APPROVED",
  "risk_per_trade": 0.015,
  "portfolio_risk": 0.08,
  "processing_ms": 5
}
```

```json
{
  "event": "kill_switch_triggered",
  "trigger": "daily_loss",
  "current_value": 0.105,
  "limit": 0.10
}
```

---

## 12. TESTING REQUERIDO

| Test | Tipo | Cobertura objetivo |
|------|------|---------------------|
| test_validation | Unit | 95% |
| test_position_sizing | Unit | 90% |
| test_kill_switch | Unit | 100% |
| test_edge_cases | Unit | 90% |
| test_integration | Integration | 80% |

---

## 13. EJEMPLOS DE USO

```python
# Validar señal
manager = RiskManager()
result = await manager.validate_signal(signal, portfolio)

if result.approved:
    # Calcular tamaño
    size = await manager.calculate_position_size(
        signal, portfolio, risk_per_trade=0.02
    )
    # Ejecutar
    await executor.execute(signal, size)
else:
    log.warning(f"Signal rejected: {result.reason}")
```

---

## 14. KPIs

| KPI | Target |
|-----|--------|
| Validation coverage | 100% |
| False positives | < 5% |
| Kill switch accuracy | 100% |
| Position sizing accuracy | 100% |

---

*Volver al [INDEX](../INDEX.md)*