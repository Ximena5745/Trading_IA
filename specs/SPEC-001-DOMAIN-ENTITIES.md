# SPEC — Domain Entities
**Fecha:** 2026-05-16 | **Versión:** 1.0 | **Estado:** DRAFT

---

## 1. RESUMEN EJECUTIVO

Definir las entidades de dominio core del sistema de trading: Signal, Order, Portfolio y Position. Estas entidades son los objetos de negocio fundamentales que representan el estado del sistema y son compartidas por todas las capas de la aplicación.

**Pertenece a:** Fase 0 - Foundation | **Depende de:** Ninguno
**Bloquea:** SPEC-002 (Kill Switch), SPEC-003 (Auth), SPEC-004 (Database), SPEC-005 (Pipeline)

---

## 2. OBJETIVOS

| # | Objetivo | Métrica de éxito |
|---|----------|------------------|
| O1 | Definir Signal con validaciones de invariantes | stop_loss < entry (BUY), confidence [0,1] |
| O2 | Definir Order con estados y validación | quantity > 0, fill_price >= 0 |
| O3 | Definir Portfolio con invariantes | available_capital <= total_capital |
| O4 | Definir Position con risk levels | stop_loss y take_profit siempre presentes |

---

## 3. ESPECIFICACIÓN TÉCNICA

### 3.1 Interfaz pública

```python
# domain/entities/signal.py
class Signal(BaseModel):
    id: str
    idempotency_key: str
    timestamp: Optional[datetime] = None
    symbol: str
    action: str  # "BUY" | "SELL" | "HOLD"
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float  # 0.0 - 1.0
    # ... validaciones de invariantes
```

### 3.2 Tipos de datos

| Entidad | Descripción | Validador |
|---------|-------------|-----------|
| Signal | Señal de trading con niveles de riesgo | Pydantic con field_validator |
| Order | Orden con estados (pending, filled, etc.) | Pydantic con field_validator |
| Portfolio | Estado del portfolio con posiciones | Pydantic con field_validator |
| Position | Posición abierta con PnL | Pydantic con field_validator |

---

## 4. CRITERIOS DE ACEPTACIÓN

| ID | Criterio | Test asociado |
|----|----------|---------------|
| CA-1 | Signal con action=BUY tiene stop_loss < entry_price < take_profit | tests/unit/domain/test_signal.py::test_buy_invariants |
| CA-2 | Signal confidence está en rango [0, 1] | tests/unit/domain/test_signal.py::test_confidence_range |
| CA-3 | Order quantity > 0 siempre | tests/unit/domain/test_order.py::test_quantity_positive |
| CA-4 | Portfolio available_capital <= total_capital | tests/unit/domain/test_portfolio.py::test_capital_invariant |
| CA-5 | Position tiene stop_loss y take_profit | tests/unit/domain/test_position.py::test_risk_levels |

---

## 5. TRAZABILIDAD

| Versión | Fecha | Cambios | Autor |
|---------|-------|---------|-------|
| 1.0 | 2026-05-16 | Versión inicial | TRADER AI |

**ESTADO:** APPROVED