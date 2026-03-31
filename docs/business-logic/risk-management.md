# Sistema de Gestión de Riesgos

> Módulo crítico que valida todas las señales antes de ejecución

## Archivos Principales

| Archivo | Responsabilidad |
|---------|-----------------|
| `core/risk/risk_manager.py` | Validación central de señales |
| `core/risk/kill_switch.py` | Frenos de emergencia automáticos |
| `core/risk/position_sizer.py` | Cálculo de tamaño de posición |
| `core/config/constants.py` | Límites hardcodeados |

---

## RiskManager

### Ubicación
`core/risk/risk_manager.py`

### Responsabilidad
Validar cada señal contra todos los límites de riesgo antes de permitir ejecución.

### Método Principal

```python
def validate_signal(signal: dict, portfolio: dict) -> tuple[bool, str]:
    """
    Retorna (approved, rejection_reason).
    Evalúa 6 checks en orden de prioridad.
    """
```

### Checks de Validación (en orden)

| # | Check | Límite | Acción si falla |
|---|-------|--------|-----------------|
| 1 | Kill Switch activo | - | REJECT |
| 2 | Exposición portafolio | 15% máximo | REJECT |
| 3 | Drawdown actual | 20% máximo | TRIGGER KILL + REJECT |
| 4 | R:R ratio | ≥ 1.5 | REJECT |
| 5 | Pérdidas consecutivas | ≤ 7 | TRIGGER KILL + REJECT |

### Position Sizing

```python
def calculate_position_size(
    signal: dict,
    portfolio: dict,
    instrument: Optional[InstrumentConfig] = None
) -> float:
    """
    Calcula cantidad según clase de activo:
    - Crypto: qty = (capital * risk%) / (entry - sl)
    - Forex: lots = (capital * risk%) / (stop_pips * pip_value)
    """
```

### Fórmulas por Clase de Activo

#### Crypto
```
qty = (total_capital × max_risk%) / (entry_price - stop_loss)

Ejemplo:
  Capital = $10,000
  Riesgo = 2%
  Entry = $50,000
  SL = $49,000
  
  qty = (10000 × 0.02) / (50000 - 49000)
      = 200 / 1000
      = 0.2 BTC
```

#### Forex
```
lots = (total_capital × max_risk%) / (stop_loss_pips × pip_value_per_lot)

Ejemplo:
  Capital = $10,000
  Riesgo = 2%
  Stop = 50 pips
  Pip value = $10/lot (EURUSD)
  
  lots = (10000 × 0.02) / (50 × 10)
       = 200 / 500
       = 0.4 lots
```

---

## Kill Switch

### Ubicación
`core/risk/kill_switch.py`

### Responsabilidad
Freno de emergencia que detiene TODO trading automático.

### Triggers Automáticos

| Trigger | Threshold | Reset |
|---------|-----------|-------|
| Pérdida diaria | > 10% | Automático al día siguiente |
| Drawdown total | > 20% | Manual (admin) |
| Pérdidas consecutivas | > 7 | Automático después de 1 win |

### Estado del Kill Switch

```python
class KillSwitchStateModel(BaseModel):
    active: bool
    triggered_at: Optional[datetime]
    triggered_by: Optional[str]    # 'daily_loss', 'drawdown', 'consecutive', 'manual'
    daily_loss_current: float
    daily_loss_limit: float
    consecutive_losses: int
    max_consecutive_losses: int
    reset_at: Optional[datetime]
```

### Reset del Kill Switch

| Trigger Type | Reset Method |
|--------------|--------------|
| `daily_loss` | Automático a medianoche UTC |
| `consecutive` | Automático tras primer trade ganador |
| `drawdown` | Solo manual via API `POST /risk/kill-switch/reset` |
| `manual` | Solo manual via API |

### API de Reset

```http
POST /risk/kill-switch/reset
Authorization: Bearer <admin_token>

Response:
{
    "status": "reset",
    "reset_by": "admin",
    "reset_at": "2026-03-30T12:00:00Z"
}
```

---

## Position Sizer

### Ubicación
`core/risk/position_sizer.py`

### Responsabilidad
Calcular el tamaño de posición óptimo según la clase de activo.

### Lógica por Clase de Activo

#### Crypto (Binance)

```python
def _calculate_crypto(self, available: float, entry: float, sl: float) -> float:
    risk_amount = available * self._settings.MAX_RISK_PER_TRADE_PCT
    price_risk = abs(entry - sl)
    qty = risk_amount / price_risk if price_risk > 0 else 0
    return qty
```

#### Forex / Commodities (MT5)

```python
def _calculate_forex(self, instrument: InstrumentConfig, stop_pips: float) -> float:
    risk_amount = available * self._settings.MAX_RISK_PER_TRADE_PCT
    pip_value = instrument.pip_value  # $10/lot para EURUSD
    lots = risk_amount / (stop_pips * pip_value)
    
    # Validar mínimos del broker
    lots = max(lots, instrument.min_lots)  # 0.01 mínimo
    lots = round(lots / instrument.lot_step) * instrument.lot_step
    
    return lots
```

#### Indices CFD (MT5)

```python
def _calculate_index(self, instrument: InstrumentConfig, stop_points: float) -> float:
    risk_amount = available * self._settings.MAX_RISK_PER_TRADE_PCT
    point_value = instrument.pip_value  # $1/point para US500
    contracts = risk_amount / (stop_points * point_value)
    
    return max(contracts, 1.0)  # mínimo 1 contrato
```

### InstrumentConfig Reference

```python
class InstrumentConfig:
    symbol: str              # Ej: "EURUSD"
    mt5_symbol: str          # Nombre exacto en IC Markets
    asset_class: AssetClass  # FOREX, CRYPTO, INDICES, COMMODITIES
    pip_value: float         # Valor en USD de 1 pip/lote
    lot_size: float          # Tamaño del contrato
    min_lots: float          # Lote mínimo (0.01 para forex)
    lot_step: float          # Incremento de lote (0.01)
    spread_pips: float       # Spread típico
    point: float             # Valor del point
```

### Catálogo de Instrumentos

| Símbolo | Clase | Pip Value | Min Lots | Point |
|---------|-------|-----------|----------|-------|
| EURUSD | FOREX | $10.00 | 0.01 | 0.00001 |
| GBPUSD | FOREX | $10.00 | 0.01 | 0.00001 |
| USDJPY | FOREX | $9.09 | 0.01 | 0.001 |
| XAUUSD | COMMODITIES | $1.00 | 0.01 | 0.01 |
| US500 | INDICES | $1.00 | 1 | 0.1 |
| BTCUSD | CRYPTO | $1.00 | 1 | 1.0 |

---

## Hard Limits (No Modificables via API)

```python
# core/config/constants.py

HARD_LIMITS = {
    "max_risk_per_trade_pct": 0.02,        # 2% por trade
    "max_portfolio_risk_pct": 0.15,         # 15% exposición total
    "max_daily_loss_pct": 0.10,             # 10% pérdida diaria
    "max_drawdown_pct": 0.20,               # 20% drawdown máximo
    "max_consecutive_losses": 7,            # 7 pérdidas consecutivas
    "min_risk_reward_ratio": 1.5,           # R:R mínimo
    "max_position_single_symbol_pct": 0.20, # 20% por símbolo
}
```

> ⚠️ Estos límites solo pueden modificarse con code review y commit explícito.

---

## Flujo de Decisión

```
Signal arrives
     │
     ▼
┌────────────────────────────────────────┐
│ Check 1: Kill Switch                   │
│ if kill_switch.is_active(): REJECT     │
└────────────────┬───────────────────────┘
                 │ OK
                 ▼
┌────────────────────────────────────────┐
│ Check 2: Portfolio Risk Exposure       │
│ if risk_exposure >= 15%: REJECT        │
└────────────────┬───────────────────────┘
                 │ OK
                 ▼
┌────────────────────────────────────────┐
│ Check 3: Current Drawdown              │
│ if drawdown >= 20%: KILL + REJECT      │
└────────────────┬───────────────────────┘
                 │ OK
                 ▼
┌────────────────────────────────────────┐
│ Check 4: Risk:Reward Ratio             │
│ if R:R < 1.5: REJECT                   │
└────────────────┬───────────────────────┘
                 │ OK
                 ▼
┌────────────────────────────────────────┐
│ Calculate Position Size                │
│ (instrument-aware)                     │
└────────────────┬───────────────────────┘
                 │
                 ▼
              EXECUTE
```

---

## API Endpoints

### Ver Estado del Riesgo

```http
GET /risk/status
Authorization: Bearer <token>

Response:
{
    "kill_switch_active": false,
    "daily_loss_pct": 0.02,
    "daily_loss_limit": 0.10,
    "drawdown_current": 0.05,
    "drawdown_limit": 0.20,
    "risk_exposure": 0.08,
    "risk_exposure_limit": 0.15,
    "consecutive_losses": 2,
    "max_consecutive_losses": 7
}
```

### Reset Kill Switch (Admin Only)

```http
POST /risk/kill-switch/reset
Authorization: Bearer <admin_token>

Response:
{
    "status": "reset",
    "previous_state": {
        "triggered_by": "drawdown",
        "triggered_at": "2026-03-30T10:30:00Z"
    },
    "reset_at": "2026-03-30T12:00:00Z"
}
```

### Forzar Kill Switch

```http
POST /risk/kill-switch/trigger
Authorization: Bearer <admin_token>
Body:
{
    "reason": "manual_override",
    "message": "Maintenance window"
}

Response:
{
    "status": "triggered",
    "triggered_by": "manual",
    "triggered_at": "2026-03-30T12:00:00Z"
}
```

---

## Testing

### Tests Unitarios

```bash
# Tests de RiskManager
pytest tests/unit/test_risk_manager.py -v

# Tests de Kill Switch
pytest tests/unit/test_kill_switch.py -v

# Tests de Position Sizer
pytest tests/unit/test_position_sizer_multiasset.py -v
```

### Tests de Integración

```bash
# Test completo de validación de riesgo
pytest tests/integration/test_api_execution.py -v
```

---

## Configuración de Riesgo

### Variables de Entorno

```env
# Riesgo
MAX_RISK_PER_TRADE_PCT=0.02
MAX_PORTFOLIO_RISK_PCT=0.15
MAX_DAILY_LOSS_PCT=0.10
MAX_DRAWDOWN_PCT=0.20
MAX_CONSECUTIVE LOSSES=7
MIN_RISK_REWARD_RATIO=1.5
```

---

*Volver al [índice de lógica empresarial](README.md)*
