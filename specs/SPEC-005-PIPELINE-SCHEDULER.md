# SPEC — Pipeline Scheduler
**Fecha:** 2026-05-16 | **Versión:** 1.0 | **Estado:** DRAFT

---

## 1. RESUMEN EJECUTIVO

Sistema de pipeline autónomo que ejecuta el ciclo de trading completo de forma programada usando APScheduler. El pipeline incluye: fetch de datos, cálculo de features, ejecución de agentes, consenso, generación de señal, validación de riesgo, ejecución de órdenes y persistencia.

**Pertenece a:** Fase 1 - Secure Core Foundation | **Depende de:** SPEC-001, SPEC-002, SPEC-003, SPEC-004
**Bloquea:** Todas las fases siguientes

---

## 2. OBJETIVOS

| # | Objetivo | Métrica de éxito |
|---|----------|------------------|
| O1 | Ciclo completo ejecuta sin intervención | 100% autonomía |
| O2 | Frecuencia configurable (default 1h) | Intervalo editable |
| O3 | Graceful shutdown con cleanup | No tasks huérfanos |
| O4 | Logging completo de cada paso | Trazabilidad total |
| O5 | Métricas Prometheus expuestas | Observabilidad |

---

## 3. ESPECIFICACIÓN TÉCNICA

### 3.1 Ciclo de Pipeline

```
1. Fetch market data (Binance/OANDA)
2. Calculate features (FeatureEngine)
3. Run agents (Technical, Regime, Microstructure, AssetSpecific)
4. Consensus engine (voting → weighted score)
5. Signal engine (generate signal si gates pasan)
6. Risk manager (validate signal)
7. Execution engine (paper mode)
8. Persist to TimescaleDB
9. Prometheus metrics + structlog
```

### 3.2 Interfaz pública

```python
class PipelineScheduler:
    def start(self) -> None:
        """Inicia el scheduler."""
        ...

    def stop(self) -> None:
        """Detiene el scheduler gracefully."""
        ...

    def add_job(self, job_id: str, func: Callable, trigger: str, **kwargs) -> None:
        """Añade un job al scheduler."""
        ...

    def remove_job(self, job_id: str) -> None:
        """Elimina un job."""
        ...

    @property
    def is_running(self) -> bool:
        """Estado del scheduler."""
        ...
```

### 3.3 Configuración

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| schedule_interval | 3600 | Segundos entre ejecuciones |
| max_workers | 4 | Workers máximos |
| misfire_grace_time | 300 | Segundos de grace para jobs perdidos |

---

## 4. CRITERIOS DE ACEPTACIÓN

| ID | Criterio | Test asociado |
|----|----------|---------------|
| CA-1 | Pipeline ejecuta ciclo completo | tests/integration/test_pipeline.py::test_full_cycle |
| CA-2 | Shutdown no deja tareas huérfanas | tests/integration/test_pipeline.py::test_graceful_shutdown |
| CA-3 | Cada paso tiene logging estructurado | tests/unit/test_pipeline.py::test_logging |
| CA-4 | Métricas visibles en /metrics | tests/integration/test_prometheus.py |
| CA-5 | Frecuencia configurable via settings | tests/unit/test_pipeline.py::test_config |

---

## 5. TRAZABILIDAD

| Versión | Fecha | Cambios | Autor |
|---------|-------|---------|-------|
| 1.0 | 2026-05-16 | Versión inicial | TRADER AI |

**ESTADO:** APPROVED