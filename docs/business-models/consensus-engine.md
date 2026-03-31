# Motor de Consenso

> Sistema de votación ponderada entre agentes con gate de régimen

## Archivos Principales

| Archivo | Responsabilidad |
|---------|-----------------|
| `core/consensus/voting_engine.py` | Votación ponderada |
| `core/consensus/conflict_logger.py` | Logging de conflictos |

---

## ConsensusEngine

### Ubicación
`core/consensus/voting_engine.py`

### Responsabilidad
Agrega outputs de todos los agentes en una decisión final usando votación ponderada.

### Definición

```python
class ConsensusEngine:
    def __init__(self) -> None:
        self._conflict_logger = ConflictLogger()
    
    def aggregate(
        self,
        agent_outputs: list[AgentOutput],
        regime: RegimeOutput,
    ) -> ConsensusOutput:
        """
        1. Detectar conflictos entre agentes
        2. Aplicar gate de régimen
        3. Calcular weighted score
        4. Verificar acuerdo mínimo
        5. Retornar ConsensusOutput
        """
```

---

## Pesos por Clase de Activo

### Crypto

```python
AGENT_WEIGHTS_CRYPTO: dict[str, float] = {
    "technical_v1": 0.45,        # 45%
    "regime_v1": 0.35,           # 35%
    "microstructure_v1": 0.20,   # 20%
}
```

### Forex/Indices/Commodities (MT5)

```python
AGENT_WEIGHTS_MT5: dict[str, float] = {
    "technical_v1": 0.55,        # 55%
    "regime_v1": 0.45,           # 45%
    "microstructure_v1": 0.00,   # 0% (no L2 data)
}
```

### Selección Automática

```python
def _weights_for_symbol(symbol: str) -> dict[str, float]:
    asset_class = detect_asset_class(symbol)
    if asset_class == AssetClass.CRYPTO:
        return AGENT_WEIGHTS_CRYPTO
    return AGENT_WEIGHTS_MT5
```

---

## Umbrales

```python
MIN_CONSENSUS_SCORE = 0.30    # Score mínimo para dirección
MIN_AGENTS_AGREEING = 0.60    # 60% de agentes deben estar de acuerdo
```

---

## Flujo de Agregación

```
agent_outputs + regime
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Detect Conflictos                                   │
│ ConflictLogger.detect_conflicts(agent_outputs)              │
│ → Lista de conflictos (ej: "technical_v1:BUY vs regime:SELL")
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Regime Gate                                         │
│ if not regime.signal_allowed:                               │
│     return NEUTRAL (blocked_by_regime=True)                 │
│                                                             │
│ Bloquea en:                                                 │
│ - VOLATILE_CRASH                                            │
│ - confidence < 0.50                                         │
│ - score ≤ -0.9                                              │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Weighted Score                                      │
│                                                             │
│ weighted_score = Σ(score_i × weight_i) / Σ(weight_i)       │
│                                                             │
│ Solo incluye agentes con weight > 0                         │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Agreement Check                                     │
│                                                             │
│ if abs(weighted_score) ≥ MIN_CONSENSUS_SCORE:               │
│     dominant = "BUY" if score > 0 else "SELL"               │
│     agreeing = count(agentes con misma dirección)           │
│     agreement = agreeing / total_agentes                    │
│                                                             │
│ if agreement < MIN_AGENTS_AGREEING:                         │
│     dominant = "NEUTRAL"                                    │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Minimum Score Check                                 │
│                                                             │
│ if abs(weighted_score) < MIN_CONSENSUS_SCORE:               │
│     dominant = "NEUTRAL"                                    │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
    ConsensusOutput
```

---

## Ejemplos de Cálculo

### Ejemplo 1: Crypto - Señal BUY

```
Agentes:
- TechnicalAgent: score=0.65, weight=0.45
- RegimeAgent: score=0.45, weight=0.35
- MicrostructureAgent: score=0.30, weight=0.20

Regime: BULL_TRENDING, signal_allowed=True

Cálculo:
weighted_score = (0.65×0.45 + 0.45×0.35 + 0.30×0.20) / (0.45+0.35+0.20)
               = (0.2925 + 0.1575 + 0.06) / 1.0
               = 0.51

Agreement:
- Direction: BUY (score > 0)
- Technical: BUY ✓
- Regime: BUY ✓
- Microstructure: BUY ✓
- agreement = 3/3 = 1.0

Resultado:
- final_direction: "BUY"
- weighted_score: 0.51
- agents_agreement: 1.0
- blocked_by_regime: false
```

### Ejemplo 2: Crypto - Conflicto

```
Agentes:
- TechnicalAgent: score=0.65, weight=0.45
- RegimeAgent: score=-0.55, weight=0.35
- MicrostructureAgent: score=-0.40, weight=0.20

Regime: SIDEWAYS, signal_allowed=True

Cálculo:
weighted_score = (0.65×0.45 + (-0.55)×0.35 + (-0.40)×0.20) / 1.0
               = (0.2925 - 0.1925 - 0.08)
               = 0.02

Agreement:
- Score < MIN_CONSENSUS_SCORE (0.30)
- dominant = "NEUTRAL"

Resultado:
- final_direction: "NEUTRAL"
- weighted_score: 0.02
- agents_agreement: 0.0
- conflicts: ["technical_v1:BUY vs regime_v1:SELL", ...]
```

### Ejemplo 3: Forex - Microstructure Sin Peso

```
Symbol: EURUSD (Forex)
Pesos: Technical 55%, Regime 45%, Micro 0%

Agentes:
- TechnicalAgent: score=0.40, weight=0.55
- RegimeAgent: score=0.35, weight=0.45
- MicrostructureAgent: score=0.80, weight=0.00  ← Ignorado

Cálculo:
weighted_score = (0.40×0.55 + 0.35×0.45 + 0.80×0.00) / (0.55+0.45+0.00)
               = (0.22 + 0.1575) / 1.0
               = 0.3775

Nota: MicrostructureAgent score es ignorado completamente.

Resultado:
- final_direction: "BUY"
- weighted_score: 0.38
```

### Ejemplo 4: Regime Gate Bloquea

```
Regime: VOLATILE_CRASH, signal_allowed=False

Todos los agentes dan BUY con scores altos...

Resultado:
- final_direction: "NEUTRAL"
- weighted_score: 0.0
- blocked_by_regime: true
- conflicts: []
```

---

## ConflictLogger

### Ubicación
`core/consensus/conflict_logger.py`

### Responsabilidad
Detectar y registrar conflictos entre agentes.

### Detección

```python
def detect_conflicts(self, agent_outputs: list[AgentOutput]) -> list[str]:
    """
    Detecta conflictos:
    - Agentes con direcciones opuestas (BUY vs SELL)
    - Diferencias de score > 0.5
    - Agentes con baja confidence
    """
```

### Formato de Conflicto

```python
conflicts = [
    "technical_v1:BUY(score=0.65) vs regime_v1:SELL(score=-0.55)",
    "microstructure_v1:NEUTRAL(score=0.05) with low confidence(0.30)"
]
```

---

## ConsensusOutput

### Definición

```python
class ConsensusOutput(BaseModel):
    timestamp: datetime
    symbol: str
    final_direction: str           # "BUY" | "SELL" | "NEUTRAL"
    weighted_score: float          # -1.0 to +1.0
    agents_agreement: float        # 0.0 to 1.0
    blocked_by_regime: bool
    agent_outputs: list[AgentOutput]
    conflicts: list[str]
```

### Ejemplo Completo

```json
{
    "timestamp": "2026-03-30T12:00:00Z",
    "symbol": "BTCUSDT",
    "final_direction": "BUY",
    "weighted_score": 0.51,
    "agents_agreement": 1.0,
    "blocked_by_regime": false,
    "agent_outputs": [
        {
            "agent_id": "technical_v1",
            "direction": "BUY",
            "score": 0.65,
            "confidence": 0.78
        },
        {
            "agent_id": "regime_v1",
            "direction": "BUY",
            "score": 0.45,
            "confidence": 0.72
        },
        {
            "agent_id": "microstructure_v1",
            "direction": "BUY",
            "score": 0.30,
            "confidence": 0.65
        }
    ],
    "conflicts": []
}
```

---

## Integración con Signal Engine

```
ConsensusOutput
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ SignalEngine.generate(consensus, features, strategy_id)     │
│                                                             │
│ 1. Si consensus.final_direction == "NEUTRAL":               │
│    → return None (no genera señal)                          │
│                                                             │
│ 2. Calcular SL/TP:                                          │
│    - SL = entry - ATR × 2.0                                 │
│    - TP = entry + ATR × 3.0                                 │
│                                                             │
│ 3. Validar R:R ≥ 1.5                                        │
│    - Si R:R < 1.5: rechazar señal                           │
│                                                             │
│ 4. Generar explicación XAI                                  │
│    - Usar SHAP values de agentes                            │
│                                                             │
│ 5. Retornar Signal                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Testing

### Tests Unitarios

```bash
# Voting Engine
pytest tests/unit/test_voting_engine.py -v

# Voting Engine MT5 (multi-asset)
pytest tests/unit/test_voting_engine_mt5.py -v

# Signal Engine
pytest tests/unit/test_signal_engine.py -v
```

### Test Manual

```python
from core.consensus.voting_engine import ConsensusEngine
from core.models import AgentOutput, RegimeOutput

engine = ConsensusEngine()

# Crear outputs de agentes
tech_output = AgentOutput(
    agent_id="technical_v1",
    timestamp=datetime.utcnow(),
    symbol="BTCUSDT",
    direction="BUY",
    score=0.65,
    confidence=0.78,
    features_used=[...],
    shap_values={...},
    model_version="v1.0.0"
)

# ... crear otros agentes

# Crear regime output
regime = RegimeOutput(
    timestamp=datetime.utcnow(),
    symbol="BTCUSDT",
    regime=MarketRegime.BULL_TRENDING,
    confidence=0.72,
    regime_duration_bars=10,
    signal_allowed=True
)

# Ejecutar consenso
result = engine.aggregate([tech_output, regime_output, micro_output], regime)

print(f"Direction: {result.final_direction}")
print(f"Score: {result.weighted_score}")
print(f"Agreement: {result.agents_agreement}")
```

---

*Volver al [índice de modelos](README.md)*
