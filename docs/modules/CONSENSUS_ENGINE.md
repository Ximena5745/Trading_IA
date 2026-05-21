# Módulo: Consensus Engine

> Motor de consenso multi-agente con votación ponderada

---

## 1. OBJETIVO

Proveer un sistema de consenso que combine señales de múltiples agentes IA usando votación ponderada, detecte conflictos y proporcione explicabilidad de la decisión final.

---

## 2. RESPONSABILIDADES

| Responsabilidad | Descripción |
|----------------|-------------|
| Agent voting | Combinar decisiones de agentes |
| Weight management | Pesos dinámicos por agente |
| Conflict detection | Detectar decisiones contradictorias |
| Explanation generation | Generar resumen de consenso |

---

## 3. ARQUITECTURA INTERNA

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONSENSUS LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    VotingEngine                           │ │
│  │  - Collect votes                                         │ │
│  │  - Apply weights                                         │ │
│  │  - Resolve consensus                                      │ │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                      │
│  ┌──────────────────────┼───────────────────────────────────┐  │
│  │            ConflictLogger                                 │  │
│  │  - Log conflicts                                          │  │
│  │  - Alert on high conflict                                 │  │
│  │  - Analysis                                               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
   ┌────────────┐   ┌────────────┐   ┌────────────┐
   │  Technical │   │   Regime   │   │ Microstruct│
   │   Agent    │   │   Agent    │   │   Agent    │
   └────────────┘   └────────────┘   └────────────┘
```

---

## 4. COMPONENTES

### 4.1 VotingEngine

**Archivo:** `core/consensus/voting_engine.py`

**Algoritmo:**

```python
class VotingEngine:
    def vote(
        self,
        agent_signals: dict[str, AgentSignal],
        weights: dict[str, float]
    ) -> ConsensusResult:
        """
        1. Agregar votes por dirección (BUY/SELL/HOLD)
        2. Ponderar por peso de agente
        3. Calcular confidence
        4. Generar explanation
        """
```

**Proceso:**
```
Input: {agent -> signal}

Step 1: Count votes
  BUY:   (Technical: 0.8 * 0.3) + (Regime: 0.7 * 0.2) = 0.38
  SELL:  (Microstructure: 0.6 * 0.25) = 0.15
  HOLD:  = 0

Step 2: Select winner
  WINNER = max(BUY, SELL, HOLD) = BUY (0.38)

Step 3: Calculate confidence
  confidence = 0.38 / (0.38 + 0.15) = 0.717

Step 4: Check conflict threshold
  if max_vote / total < 0.4 -> HIGH_CONFLICT
```

**Pesos por defecto:**
| Agent | Peso | Baseline accuracy |
|-------|------|-------------------|
| Technical | 0.35 | 55% |
| Regime | 0.25 | 60% |
| Microstructure | 0.25 | 52% |
| Fundamental | 0.15 | 48% |

### 4.2 ConflictLogger

**Archivo:** `core/consensus/conflict_logger.py`

**Niveles de conflicto:**
| Nivel | Descripción | Threshold |
|-------|-------------|------------|
| LOW | Ligera disagreement | 0.3 - 0.5 |
| MEDIUM | Significativa disagreement | 0.5 - 0.7 |
| HIGH | Fuerte disagreement | > 0.7 |

**Logging:**
```python
# Alta conflict -> investigar
{
    "event": "high_conflict",
    "agents": ["Technical", "Microstructure"],
    "votes": {"BUY": 2, "SELL": 2},
    "confidence": 0.5
}
```

### 4.3 AssetSpecificConsensus

**Archivo:** `core/consensus/asset_specific_consensus.py`

**Propósito:** Pesos adaptivos por tipo de asset.

```python
class AssetSpecificConsensus:
    WEIGHTS = {
        "crypto": {"Technical": 0.40, "Regime": 0.25, "Microstructure": 0.25, "Fundamental": 0.10},
        "forex": {"Technical": 0.30, "Regime": 0.30, "Microstructure": 0.20, "Fundamental": 0.20},
        "indices": {"Technical": 0.25, "Regime": 0.35, "Microstructure": 0.20, "Fundamental": 0.20},
    }
```

---

## 5. EVENTOS

### 5.1 Eventos Publicados

| Evento | Descripción | Payload |
|--------|-------------|---------|
| `consensus.reached` | Consenso alcanzado | `{signal, confidence, votes}` |
| `consensus.conflict` | Conflicto detectado | `{agents, level}` |

### 5.2 Eventos Consumidos

| Evento | Descripción |
|--------|-------------|
| `agent.signal` | Señal de agente individual |

---

## 6. INPUTS/OUTPUTS

### 6.1 Inputs

| Input | Tipo | Descripción |
|-------|------|-------------|
| Agent signals | dict[str, AgentSignal] | Señales de agentes |
| Agent weights | dict[str, float] | Pesos (opcional) |
| Asset class | str | crypto/forex/etc |

### 6.2 Outputs

| Output | Destino | Descripción |
|--------|---------|-------------|
| Consensus signal | Signal Engine | Señal consensuada |
| Explanation | XAI Module | Explicación SHAP |

---

## 7. ALGORITMOS DE CONSENSO

### 7.1 Weighted Majority

```python
# Simple weighted vote
result = sum(w_i * vote_i for each agent)
decision = "BUY" if result > threshold else "SELL"
```

### 7.2 Soft Voting (Probabilities)

```python
# Use probabilities
proba = weighted_average(agent_probabilities)
decision = argmax(proba)
```

### 7.3 Dynamic Weight Adjustment

```python
# Ajustar pesos basado en performance reciente
def adjust_weights(performance: dict[str, float]) -> dict[str, float]:
    # Normalizar performance a weights
    total = sum(performance.values())
    return {k: v/total for k, v in performance.items()}
```

---

## 8. CASOS EDGE

| Caso | Manejo |
|------|--------|
| Todos HOLD | Return HOLD |
| 2 BUY / 2 SELL | RETURN HOLD (alta indecisión) |
| Un agente unavailable | Usar pesos normalizados |
| Agent signal inválido | Skip agente + warning |

---

## 9. RIESGOS

| Riesgo | Impacto | Mitigación |
|--------|---------|-------------|
| Dominancia de agente | Medio | Weight limits |
| Failover cascada | Alto | Graceful degradation |
| Indecisión frecuente | Medio | Threshold tuning |

---

## 10. PERFORMANCE

| Métrica | Target |
|---------|--------|
| Consensus time | < 20ms |
| Conflict detection | < 5ms |
| Throughput | 1000/min |

---

## 11. OBSERVABILIDAD

### 11.1 Métricas

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `consensus.votes.total` | Counter | Total votaciones |
| `consensus.by_decision` | Counter | Por decisión |
| `consensus.conflicts` | Counter | Conflictos |
| `consensus.confidence` | Histogram | Distribución |
| `consensus.weight_drift` | Gauge | Cambio de pesos |

### 11.2 Logs

```json
{
  "event": "consensus_reached",
  "symbol": "BTCUSDT",
  "decision": "BUY",
  "confidence": 0.72,
  "votes": {"Technical": "BUY", "Regime": "BUY", "Microstructure": "HOLD"},
  "weights": {"Technical": 0.35, "Regime": 0.25, "Microstructure": 0.25},
  "time_ms": 12
}
```

---

## 12. TESTING REQUERIDO

| Test | Tipo | Cobertura objetivo |
|------|------|---------------------|
| test_voting | Unit | 95% |
| test_conflicts | Unit | 90% |
| test_weights | Unit | 90% |
| test_edge_cases | Unit | 90% |

---

## 13. EJEMPLOS DE USO

```python
# Consensus de señales
engine = VotingEngine()
consensus = engine.vote(
    agent_signals={
        "Technical": AgentSignal(action="BUY", confidence=0.8),
        "Regime": AgentSignal(action="BUY", confidence=0.7),
        "Microstructure": AgentSignal(action="HOLD", confidence=0.6),
    },
    weights={"Technical": 0.35, "Regime": 0.25, "Microstructure": 0.25}
)

# Resultado
print(consensus.action)      # BUY
print(consensus.confidence)  # 0.72
print(consensus.explanation) # "2 de 3 agentes votan BUY..."
```

---

## 14. KPIs

| KPI | Target |
|-----|--------|
| Consensus rate | > 90% |
| Conflict rate | < 15% |
| Decision quality | Correlación con P&L |

---

*Volver al [INDEX](../INDEX.md)*