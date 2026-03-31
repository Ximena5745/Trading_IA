# Estrategias de Trading

> Framework extensible de estrategias con implementaciones builtin

## Archivos Principales

| Archivo | Responsabilidad |
|---------|-----------------|
| `core/strategies/base_strategy.py` | Interfaz abstracta |
| `core/strategies/strategy_builder.py` | Builder dinámico desde JSON |
| `core/strategies/strategy_registry.py` | Registro de estrategias |
| `core/strategies/builtin/ema_rsi.py` | EMA + RSI crossover |
| `core/strategies/builtin/mean_reversion.py` | Bollinger Bands reversion |

---

## Arquitectura

```
              AbcStrategy (ABC)
                     │
       ┌─────────────┼─────────────┐
       │             │             │
  EmaRsiStrategy  MeanReversion  BuiltStrategy
       │           Strategy          │
       │                             │
       └─────────────┬───────────────┘
                     │
                     ▼
            StrategyRegistry
           (Catálogo activo)
```

---

## Base Strategy

### Interfaz Abstracta

```python
class AbcStrategy(ABC):
    strategy_id: str
    name: str
    version: str
    
    @abstractmethod
    def should_enter(self, features: FeatureSet) -> Optional[dict]:
        """
        Evalúa condiciones de entrada.
        
        Returns:
            dict con action, entry_price, stop_loss, take_profit
            None si no debe entrar
        """
        pass
    
    @abstractmethod
    def should_exit(self, features: FeatureSet, position: dict) -> bool:
        """
        Evalúa condiciones de salida.
        
        Returns:
            True si debe cerrar posición
        """
        pass
    
    def to_dict(self) -> dict:
        """Retorna metadata de la estrategia."""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "version": self.version,
        }
```

---

## EMA RSI Strategy

### Ubicación
`core/strategies/builtin/ema_rsi.py`

### Descripción
Estrategia de趋势 following basada en cruces de EMA con confirmación RSI.

### Condiciones de Entrada

```python
class EmaRsiStrategy(AbcStrategy):
    """
    Entry rules:
      BUY:  EMA9 > EMA21 AND EMA50 > EMA200 AND RSI14 < 65 AND RSI14 > 30
      SELL: EMA9 < EMA21 AND EMA50 < EMA200 AND RSI14 > 35 AND RSI14 < 70
    
    Exit rules:
      - RSI14 crosses opposite extreme (>70 for BUY, <30 for SELL)
      - EMA crossover reverses
    """
    
    strategy_id = "ema_rsi_v1"
    name = "EMA Crossover + RSI"
```

### Implementación

```python
def should_enter(self, features: FeatureSet) -> Optional[dict]:
    # Filtros
    if features.volume_ratio < self.min_volume_ratio:
        return None
    if features.volatility_regime == "extreme":
        return None
    
    # BUY signal
    if self._is_buy(features):
        entry = features.close
        sl = entry - ATR_STOP_LOSS_MULTIPLIER * features.atr_14
        tp = entry + ATR_TAKE_PROFIT_MULTIPLIER * features.atr_14
        return {
            "action": "BUY",
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit": tp,
        }
    
    # SELL signal
    if self._is_sell(features):
        entry = features.close
        sl = entry + ATR_STOP_LOSS_MULTIPLIER * features.atr_14
        tp = entry - ATR_TAKE_PROFIT_MULTIPLIER * features.atr_14
        return {
            "action": "SELL",
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit": tp,
        }
    
    return None

def _is_buy(self, f: FeatureSet) -> bool:
    return (
        f.ema_9 > f.ema_21          # Cruce alcista corto plazo
        and f.ema_50 > f.ema_200    # Tendencia alcista largo plazo
        and self.rsi_oversold < f.rsi_14 < 65  # RSI no sobrecomprado
        and f.macd_histogram > 0    # Momentum positivo
    )

def _is_sell(self, f: FeatureSet) -> bool:
    return (
        f.ema_9 < f.ema_21          # Cruce bajista corto plazo
        and f.ema_50 < f.ema_200    # Tendencia bajista largo plazo
        and 35 < f.rsi_14 < self.rsi_overbought  # RSI no sobrevendido
        and f.macd_histogram < 0    # Momentum negativo
    )
```

### Condiciones de Salida

```python
def should_exit(self, features: FeatureSet, position: dict) -> bool:
    side = position.get("side", "BUY")
    if side == "BUY":
        return (
            features.rsi_14 > self.rsi_overbought  # Sobrecompra
            or features.ema_9 < features.ema_21    # Cruce bajista
        )
    return (
        features.rsi_14 < self.rsi_oversold  # Sobreventa
        or features.ema_9 > features.ema_21  # Cruce alcista
    )
```

### Parámetros

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| rsi_oversold | 30.0 | RSI mínima para BUY |
| rsi_overbought | 70.0 | RSI máxima para SELL |
| min_volume_ratio | 1.2 | Volumen mínimo vs media |

### Símbolos Soportados

```python
symbols = [
    "BTCUSDT", "ETHUSDT",      # Crypto
    "EURUSD", "GBPUSD", "USDJPY",  # Forex
    "SPX500", "NAS100",        # Indices
    "XAUUSD", "USOIL",         # Commodities
]
```

### Configuración de Riesgo

```python
max_capital_pct = 0.20      # Max 20% del capital
risk_per_trade_pct = 0.01   # 1% riesgo por trade
```

---

## Mean Reversion Strategy

### Ubicación
`core/strategies/builtin/mean_reversion.py`

### Descripción
Estrategia de reversión a la media usando Bollinger Bands.

### Condiciones de Entrada

```python
class MeanReversionStrategy(AbcStrategy):
    """
    Entry rules:
      BUY:  close < bb_lower AND RSI14 < rsi_oversold AND volume_ratio > min_vol
      SELL: close > bb_upper AND RSI14 > rsi_overbought AND volume_ratio > min_vol
    
    Exit: price returns to VWAP or midband
    """
    
    strategy_id = "mean_reversion_v1"
    name = "Bollinger Bands Mean Reversion"
```

### Implementación

```python
def should_enter(self, features: FeatureSet) -> Optional[dict]:
    if features.volume_ratio < self.min_volume_ratio:
        return None
    if features.volatility_regime == "extreme":
        return None
    
    if self._is_buy(features):
        entry = features.close
        sl = entry - ATR_STOP_LOSS_MULTIPLIER * features.atr_14
        tp = features.vwap  # Target: revertir a VWAP
        if tp <= entry:
            return None
        return {
            "action": "BUY",
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit": tp,
        }
    
    if self._is_sell(features):
        entry = features.close
        sl = entry + ATR_STOP_LOSS_MULTIPLIER * features.atr_14
        tp = features.vwap  # Target: revertir a VWAP
        if tp >= entry:
            return None
        return {
            "action": "SELL",
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit": tp,
        }
    
    return None

def _is_buy(self, f: FeatureSet) -> bool:
    return (
        f.close < f.bb_lower           # Precio bajo BB Lower
        and f.rsi_14 < self.rsi_oversold  # Sobreventa
        and f.volume_ratio >= self.min_volume_ratio  # Volumen confirmación
    )

def _is_sell(self, f: FeatureSet) -> bool:
    return (
        f.close > f.bb_upper              # Precio sobre BB Upper
        and f.rsi_14 > self.rsi_overbought  # Sobrecompra
        and f.volume_ratio >= self.min_volume_ratio  # Volumen confirmación
    )
```

### Condiciones de Salida

```python
def should_exit(self, features: FeatureSet, position: dict) -> bool:
    side = position.get("side", "BUY")
    midband = (features.bb_upper + features.bb_lower) / 2
    
    if side == "BUY":
        return features.close >= midband or features.rsi_14 > 55
    return features.close <= midband or features.rsi_14 < 45
```

### Parámetros

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| rsi_oversold | 28.0 | RSI mínima para BUY |
| rsi_overbought | 72.0 | RSI máxima para SELL |
| min_volume_ratio | 1.0 | Volumen mínimo vs media |

### Símbolos Soportados

```python
symbols = [
    "BTCUSDT", "ETHUSDT",      # Crypto (alta volatilidad)
    "XAUUSD", "XAGUSD", "USOIL",  # Commodities (mean-reverting)
    "EURUSD", "GBPUSD", "USDCHF",  # Forex (range-bound)
]
```

### Configuración de Riesgo

```python
max_capital_pct = 0.15      # Max 15% del capital
risk_per_trade_pct = 0.01   # 1% riesgo por trade
```

---

## Strategy Builder

### Ubicación
`core/strategies/strategy_builder.py`

### Descripción
Construye estrategias dinámicamente desde configuración JSON (no-code).

### Uso

```python
from core.strategies.strategy_builder import StrategyBuilder

builder = StrategyBuilder()

config = {
    "id": "my_rsi_macd_v1",
    "name": "RSI + MACD Strategy",
    "entry_conditions": [
        {"feature": "rsi_14", "operator": "lt", "value": 30},
        {"feature": "macd_histogram", "operator": "gt", "value": 0},
        {"feature": "volume_ratio", "operator": "gte", "value": 1.2}
    ],
    "exit_conditions": [
        {"feature": "rsi_14", "operator": "gt", "value": 70}
    ],
    "default_action": "BUY"
}

strategy = builder.build(config)
```

### Operadores Soportados

| Operador | Función | Descripción |
|----------|---------|-------------|
| `lt` | `a < b` | Menor que |
| `gt` | `a > b` | Mayor que |
| `lte` | `a <= b` | Menor o igual |
| `gte` | `a >= b` | Mayor o igual |
| `eq` | `a == b` | Igual |

### Referencia a Features

```python
# Valor directo
{"feature": "rsi_14", "operator": "lt", "value": 30}

# Referencia a otro feature
{"feature": "close", "operator": "gt", "value": "vwap"}
```

### Validación

```python
# Requeridos:
# - id
# - name
# - entry_conditions (no vacío)

# Operadores deben ser válidos
# confirmation_timeframe (opcional) debe ser soportado
```

---

## Strategy Registry

### Ubicación
`core/strategies/strategy_registry.py`

### Descripción
Catálogo de estrategias activas con gestión de ciclo de vida.

### Uso

```python
from core.strategies.strategy_registry import StrategyRegistry

registry = StrategyRegistry()

# Listar todas
strategies = registry.list_all()

# Obtener una
strategy = registry.get("ema_rsi_v1")

# Cambiar estado
registry.set_status("ema_rsi_v1", "paused")

# Registrar custom
registry.register(my_custom_strategy)

# Eliminar
registry.unregister("my_custom_strategy")
```

### Estados

| Estado | Descripción |
|--------|-------------|
| active | Estrategia activa, generando señales |
| paused | Pausada, no genera señales |
| disabled | Deshabilitada por admin |

### Builtins Cargados

```python
def _load_builtins(self) -> None:
    self.register(EmaRsiStrategy())
    self.register(MeanReversionStrategy())
```

---

## API de Estrategias

### Listar Estrategias

```http
GET /strategies
Response: {
    "strategies": [...],
    "total": 2,
    "active": 2
}
```

### Crear Custom

```http
POST /strategies/custom
Body: {
    "strategy_id": "my_custom",
    "name": "My Custom",
    "entry_conditions": [...],
    "exit_conditions": [...]
}
```

### Cambiar Estado

```http
PATCH /strategies/{id}/status
Body: {"status": "paused"}
```

---

## Testing

### Tests Unitarios

```bash
# Tests de estrategias
pytest tests/unit/test_strategies.py -v

# Tests de strategy builder
pytest tests/unit/test_strategy_builder.py -v

# Tests de registry
pytest tests/unit/test_strategy_registry.py -v
```

### Test Manual

```python
from core.strategies.builtin.ema_rsi import EmaRsiStrategy
from core.models import FeatureSet

strategy = EmaRsiStrategy()

# Crear features de prueba
features = FeatureSet(
    timestamp=datetime.utcnow(),
    symbol="BTCUSDT",
    rsi_14=28.0,  # Sobreventa
    rsi_7=25.0,
    ema_9=50100.0,
    ema_21=49800.0,
    ema_50=48500.0,
    ema_200=45000.0,
    macd_histogram=15.0,  # Positivo
    atr_14=800.0,
    volume_ratio=1.5,  # Alto volumen
    volatility_regime="medium",
    close=50000.0,
    # ... otros campos
)

# Evaluar entrada
signal = strategy.should_enter(features)
print(signal)  # {'action': 'BUY', 'entry_price': 50000.0, ...}
```

---

*Volver al [índice de estrategias e indicadores](README.md)*
