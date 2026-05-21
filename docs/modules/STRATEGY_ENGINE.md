# Módulo: Strategy Engine

> Motor de estrategias de trading con registry y builder

---

## 1. OBJETIVO

Proveer un sistema extensible de estrategias de trading que permita crear, registrar, ejecutar y monitorear estrategias algorítmicas con soporte para estrategias builtin y custom.

---

## 2. RESPONSABILIDADES

| Responsabilidad | Descripción |
|----------------|-------------|
| Strategy Registry | Catálogo de estrategias disponibles |
| Strategy Builder | Builder pattern para estrategias |
| Strategy Execution | Ejecución de señales |
| Strategy Rotation | Cambio automático de estrategia |

---

## 3. ARQUITECTURA INTERNA

```
┌─────────────────────────────────────────────────────────────────┐
│                     STRATEGY LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    BaseStrategy (ABC)                   │  │
│  │  - Interface común                                      │  │
│  │  - Entry/Exit logic                                     │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                      │
│  ┌──────────────────────┼───────────────────────────────────┐  │
│  │               StrategyRegistry                           │  │
│  │  - Registry de estrategias                               │  │
│  │  - Factory method                                        │  │
│  └──────────────────────┼───────────────────────────────────┘  │
│                         │                                      │
│  ┌──────────────────────┼───────────────────────────────────┐  │
│  │               StrategyBuilder                             │  │
│  │  - Builder pattern                                       │  │
│  │  - Configuration validation                              │  │
│  └──────────────────────┼───────────────────────────────────┘  │
│                         │                                      │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                   Builtin Strategies                      │ │
│  │  - EmaRsiStrategy                                        │ │
│  │  - MeanReversionStrategy                                 │ │
│  │  - BreakoutStrategy (future)                              │ │
│  │  - VolatilityStrategy (future)                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. COMPONENTES

### 4.1 BaseStrategy

**Archivo:** `core/strategies/base_strategy.py`

**Interfaz abstracta:**

```python
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    @property
    def name(self) -> str: ...
    
    @property
    def params(self) -> dict: ...
    
    @abstractmethod
    def generate_signal(
        self,
        df: pd.DataFrame,
        current_position: Position | None = None
    ) -> Signal | None: ...
    
    @abstractmethod
    def validate_params(self, params: dict) -> bool: ...
    
    def get_indicators(self) -> list[str]: ...
```

### 4.2 EmaRsiStrategy

**Archivo:** `core/strategies/builtin/ema_rsi.py`

**Descripción:** Estrategia de momentum basada en EMA crossover + RSI filter.

**Parámetros:**
| Parámetro | Default | Rango | Descripción |
|-----------|---------|-------|-------------|
| fast_ema | 9 | 5-21 | EMA rápido |
| slow_ema | 21 | 10-200 | EMA lento |
| rsi_period | 14 | 7-28 | Periodo RSI |
| rsi_overbought | 70 | 60-80 | Nivel sobrecompra |
| rsi_oversold | 30 | 20-40 | Nivel sobreventa |

**Lógica:**
```python
# BUY: EMA fast cruza sobre EMA slow + RSI < overbought
# SELL: EMA fast cruza bajo EMA slow + RSI > oversold
```

### 4.3 MeanReversionStrategy

**Archivo:** `core/strategies/builtin/mean_reversion.py`

**Descripción:** Estrategia de mean reversion basada en Bollinger Bands.

**Parámetros:**
| Parámetro | Default | Rango | Descripción |
|-----------|---------|-------|-------------|
| bb_period | 20 | 10-50 | Periodo Bollinger |
| bb_std | 2 | 1.5-3 | Desviación estándar |
| rsi_period | 14 | 7-21 | Periodo RSI |
| rsi_oversold | 30 | 20-40 | Nivel sobreventa |
| rsi_overbought | 70 | 60-80 | Nivel sobrecompra |

**Lógica:**
```python
# BUY: Precio toca lower band + RSI < oversold
# SELL: Precio toca upper band + RSI > overbought
```

### 4.4 StrategyRegistry

**Archivo:** `core/strategies/strategy_registry.py`

**Propósito:** Registro centralizado de estrategias disponibles.

```python
class StrategyRegistry:
    def register(self, strategy_class: type[BaseStrategy]) -> None: ...
    
    def get(self, name: str) -> type[BaseStrategy]: ...
    
    def list_strategies(self) -> list[str]: ...
    
    def get_metadata(self, name: str) -> StrategyMetadata: ...
```

### 4.5 StrategyBuilder

**Archivo:** `core/strategies/strategy_builder.py`

**Propósito:** Builder pattern para crear estrategias con validación.

```python
class StrategyBuilder:
    def with_name(self, name: str) -> StrategyBuilder: ...
    
    def with_params(self, params: dict) -> StrategyBuilder: ...
    
    def with_risk_profile(self, profile: str) -> StrategyBuilder: ...
    
    def build(self) -> BaseStrategy: ...
```

### 4.6 StrategyRotation

**Archivo:** `core/strategies/strategy_rotation.py`

**Propósito:** Rotación automática de estrategias basada en performance.

```python
class StrategyRotation:
    def select_best_strategy(
        self,
        strategies: list[str],
        lookback_days: int = 30
    ) -> str: ...
    
    def rebalance(
        self,
        allocations: dict[str, float]
    ) -> dict[str, float]: ...
```

---

## 5. EVENTOS

### 5.1 Eventos Publicados

| Evento | Descripción | Payload |
|--------|-------------|---------|
| `strategy.signal_generated` | Señal generada | `{strategy, signal}` |
| `strategy.error` | Error en estrategia | `{strategy, error}` |
| `strategy.rotation` | Rotación ejecutada | `{old, new, reason}` |

### 5.2 Eventos Consumidos

| Evento | Descripción |
|--------|-------------|
| `market_data.updated` | Trigger análisis |
| `position.updated` | Posición actual |

---

## 6. INPUTS/OUTPUTS

### 6.1 Inputs

| Input | Tipo | Descripción |
|-------|------|-------------|
| OHLCV Data | pd.DataFrame | Datos de mercado |
| Position actual | Position | Posición existente |
| Strategy params | dict | Parámetros |

### 6.2 Outputs

| Output | Destino | Descripción |
|--------|---------|-------------|
| Signal | Signal Engine | Señal generada |
| Performance stats | Metrics | Stats de estrategia |

---

## 7. CASOS EDGE

| Caso | Manejo |
|------|--------|
| Insufficient data | Return None, log warning |
| Invalid params | Raise ValueError con details |
| Strategy error | Catch + return HOLD |
| No signal | Return None |

---

## 8. RIESGOS

| Riesgo | Impacto | Mitigación |
|--------|---------|-------------|
| Overfitting | Alto | Walk-forward testing |
| Strategy conflict | Medio | Conflict resolution |
| Runtime errors | Alto | Try-except wrapper |

---

## 9. PERFORMANCE

| Métrica | Target |
|---------|--------|
| Signal generation time | < 50ms |
| Strategy registry lookup | < 1ms |
| Rotation computation | < 100ms |

---

## 10. OBSERVABILIDAD

### 10.1 Métricas

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `strategy.signals.total` | Counter | Total señales |
| `strategy.signals.by_type` | Counter | Por tipo (BUY/SELL/HOLD) |
| `strategy.execution.time` | Histogram | Tiempo de ejecución |
| `strategy.rotation.count` | Counter | Rotaciones |

### 10.2 Logs

```json
{
  "event": "signal_generated",
  "strategy": "ema_rsi",
  "symbol": "BTCUSDT",
  "action": "BUY",
  "confidence": 0.78,
  "price": 45000.0,
  "sl": 44000.0,
  "tp": 47000.0
}
```

---

## 11. EXTENDING STRATEGIES

### 11.1 Creating Custom Strategy

```python
from core.strategies.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    name = "my_custom"
    
    def __init__(self, param1: int = 10, param2: float = 1.5):
        self.param1 = param1
        self.param2 = param2
    
    @property
    def params(self) -> dict:
        return {"param1": self.param1, "param2": self.param2}
    
    def generate_signal(
        self,
        df: pd.DataFrame,
        current_position: Position | None = None
    ) -> Signal | None:
        # Implementar lógica
        pass
    
    def validate_params(self, params: dict) -> bool:
        return params.get("param1", 0) > 0
```

### 11.2 Registering Strategy

```python
from core.strategies.strategy_registry import StrategyRegistry

registry = StrategyRegistry()
registry.register(MyCustomStrategy)
```

---

## 12. TESTING REQUERIDO

| Test | Tipo | Cobertura objetivo |
|------|------|---------------------|
| test_signal_generation | Unit | 90% |
| test_params_validation | Unit | 90% |
| test_registry | Unit | 90% |
| test_walk_forward | Quant | 100% |

---

## 13. EJEMPLOS DE USO

```python
# Usar estrategia desde registry
registry = StrategyRegistry()
strategy_class = registry.get("ema_rsi")
strategy = strategy_class(fast_ema=9, slow_ema=21)

# Generar señal
signal = strategy.generate_signal(df_ohlcv, current_position)
```

---

## 14. KPIs

| KPI | Target |
|-----|--------|
| Strategies registered | 5+ |
| Signal accuracy | > 50% |
| Strategy uptime | 99.9% |

---

*Volver al [INDEX](../INDEX.md)*