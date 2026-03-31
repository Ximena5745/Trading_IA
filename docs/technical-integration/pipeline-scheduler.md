# Pipeline Automático

> Sistema de ejecución programada multi-activo

## Archivos Principales

| Archivo | Responsabilidad |
|---------|-----------------|
| `scripts/run_pipeline.py` | Pipeline completo con scheduler |
| `api/main.py` | Integración con FastAPI lifespan |

---

## Arquitectura del Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PIPELINE SCHEDULER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  APScheduler (UTC)                                                          │
│       │                                                                     │
│       ├── 00:00 → BTCUSDT                                                   │
│       ├── 05:00 → ETHUSDT                                                   │
│       ├── 10:00 → EURUSD                                                    │
│       ├── 15:00 → GBPUSD                                                    │
│       ├── 20:00 → USDJPY                                                    │
│       ├── 25:00 → AUDUSD                                                    │
│       ├── 30:00 → USDCHF                                                    │
│       ├── 35:00 → USDCAD                                                    │
│       ├── 40:00 → XAUUSD                                                    │
│       ├── 45:00 → US500                                                     │
│       ├── 50:00 → US30                                                      │
│       └── 55:00 → UK100                                                     │
│                                                                             │
│  Cada job ejecuta _pipeline_cycle(symbol, components)                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Programación de Símbolos

### Configuración del Schedule

```python
SCHEDULE: list[tuple[str, int]] = [
    # Crypto — Binance
    ("BTCUSDT", 0),     # :00
    ("ETHUSDT", 5),     # :05
    # Forex majors — MT5 / IC Markets
    ("EURUSD", 10),     # :10
    ("GBPUSD", 15),     # :15
    ("USDJPY", 20),     # :20
    ("AUDUSD", 25),     # :25
    ("USDCHF", 30),     # :30
    ("USDCAD", 35),     # :35
    # Commodity — MT5
    ("XAUUSD", 40),     # :40
    # Indices — MT5
    ("US500", 45),      # :45
    ("US30", 50),       # :50
    ("UK100", 55),      # :55
]
```

### Distribución por Hora

| Minuto | Símbolo | Clase | Exchange |
|--------|---------|-------|----------|
| :00 | BTCUSDT | Crypto | Binance |
| :05 | ETHUSDT | Crypto | Binance |
| :10 | EURUSD | Forex | MT5 |
| :15 | GBPUSD | Forex | MT5 |
| :20 | USDJPY | Forex | MT5 |
| :25 | AUDUSD | Forex | MT5 |
| :30 | USDCHF | Forex | MT5 |
| :35 | USDCAD | Forex | MT5 |
| :40 | XAUUSD | Commodity | MT5 |
| :45 | US500 | Index | MT5 |
| :50 | US30 | Index | MT5 |
| :55 | UK100 | Index | MT5 |

---

## Flujo del Pipeline Cycle

```
_pipeline_cycle(symbol)
         │
         ▼
┌─────────────────────────────────────────────────┐
│ GATE 1: ¿Mercado abierto?                       │
│ calendar.is_market_open(symbol)                 │
│ NO → SKIP                                       │
└────────────────────┬────────────────────────────┘
                     │ YES
                     ▼
┌─────────────────────────────────────────────────┐
│ GATE 2: ¿Evento macro? (solo non-crypto)        │
│ fund_agent.is_blocked_by_event(symbol)          │
│ SÍ → SKIP                                       │
└────────────────────┬────────────────────────────┘
                     │ NO
                     ▼
┌─────────────────────────────────────────────────┐
│ 1. FETCH OHLCV                                  │
│ BinanceClient / MT5Client                       │
│ 250 velas × 1h                                  │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│ 2. FEATURE ENGINEERING                          │
│ FeatureEngine.calculate(df)                     │
│ → FeatureSet con 17+ indicadores                │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│ 3. ORDER BOOK (crypto only)                     │
│ binance.get_order_book(symbol)                  │
│ MicrostructureAgent.analyze_order_book()        │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│ 4. AGENTS                                       │
│ ├─ TechnicalAgent.predict(features)             │
│ ├─ RegimeAgent.predict(features)                │
│ └─ MicrostructureAgent.predict(features)        │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│ 5. CONSENSUS ENGINE                             │
│ Weighted voting (asset-class conditional)       │
│ Regime gate + minimum agreement                 │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│ 6. SIGNAL ENGINE                                │
│ Generate signal with SL/TP                      │
│ R:R ratio validation                            │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│ 7. RISK VALIDATION                              │
│ Kill switch, drawdown, exposure, R:R            │
│ Position sizing (instrument-aware)              │
└────────────────────┬────────────────────────────┘
                     │ APPROVED
                     ▼
┌─────────────────────────────────────────────────┐
│ 8. EXECUTION                                    │
│ PaperExecutor (paper mode)                      │
│ MT5Executor (live mode, if configured)          │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│ 9. PORTFOLIO UPDATE                             │
│ open_position()                                 │
│ update_kill_switch()                            │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│ 10. PERSIST                                     │
│ ├─ FeatureStore (Redis)                         │
│ ├─ TradingRepository (PostgreSQL)               │
│ └─ Signal saved                                 │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│ 11. ALERT                                       │
│ AlertEngine.on_signal()                         │
│ → Telegram notification                         │
└─────────────────────────────────────────────────┘
```

---

## Componentes del Pipeline

### Inicialización

```python
async def _build_components(settings) -> dict:
    """
    Construye todos los componentes necesarios:
    
    1. BinanceClient (Crypto)
    2. MT5Client (Forex/Índices) - opcional
    3. MarketCalendar
    4. FeatureStore (Redis)
    5. KillSwitch
    6. PortfolioManager
    7. RiskManager
    8. TelegramBot + AlertEngine
    9. FundamentalAgent
    10. TechnicalAgent (×2: crypto + mt5)
    11. RegimeAgent
    12. MicrostructureAgent
    13. ConsensusEngine
    14. SignalEngine
    15. PaperExecutor
    16. MT5Executor (opcional)
    17. TradingRepository
    """
```

### Estructura de Components

```python
components = {
    "settings": Settings,
    "binance": BinanceClient,
    "mt5_client": Optional[MT5Client],
    "mt5_executor": Optional[MT5Executor],
    "calendar": MarketCalendar,
    "feature_engine": FeatureEngine,
    "tech_agent_crypto": TechnicalAgent,  # Model: technical_crypto_v1.pkl
    "tech_agent_mt5": TechnicalAgent,     # Model: technical_forex_v1.pkl
    "regime_agent": RegimeAgent,
    "micro_agent": MicrostructureAgent,
    "fund_agent": FundamentalAgent,
    "consensus": ConsensusEngine,
    "signal_engine": SignalEngine,
    "risk": RiskManager,
    "executor_paper": PaperExecutor,
    "portfolio": PortfolioManager,
    "feature_store": FeatureStore,
    "repo": TradingRepository,
    "alert": AlertEngine,
}
```

---

## Ejecución

### Modo Scheduler (Producción)

```bash
# Iniciar scheduler (ejecuta indefinidamente)
python scripts/run_pipeline.py

# O via FastAPI (se inicia automáticamente en lifespan)
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Modo One-Shot (Testing)

```bash
# Ejecutar un solo ciclo para un símbolo
python scripts/run_pipeline.py --once BTCUSDT
python scripts/run_pipeline.py --once EURUSD

# Salida esperada:
# ▶ Running single cycle for BTCUSDT...
# [INFO] cycle_start symbol=BTCUSDT asset_class=crypto
# [INFO] cycle_complete symbol=BTCUSDT signal=BUY confidence=0.75
```

---

## Logs del Pipeline

### Log de Inicio de Ciclo

```json
{
    "event": "cycle_start",
    "symbol": "BTCUSDT",
    "asset_class": "crypto",
    "timestamp": "2026-03-30T12:00:00Z"
}
```

### Log de Ciclo Completado

```json
{
    "event": "cycle_complete",
    "symbol": "BTCUSDT",
    "asset_class": "crypto",
    "signal": "BUY",
    "confidence": 0.75,
    "quantity": 0.02,
    "elapsed_s": 2.45,
    "timestamp": "2026-03-30T12:00:03Z"
}
```

### Log de Señal Rechazada

```json
{
    "event": "signal_rejected_by_risk",
    "symbol": "EURUSD",
    "reason": "R:R ratio too low (1.2 < 1.5)",
    "timestamp": "2026-03-30T12:10:01Z"
}
```

### Log de Error

```json
{
    "event": "cycle_error",
    "symbol": "BTCUSDT",
    "error": "Connection timeout",
    "timestamp": "2026-03-30T12:00:05Z"
}
```

---

## Calendar Refresh

### ForexFactory Calendar

```python
# Refresh automático cada 4 horas
scheduler.add_job(
    _refresh_calendar,
    trigger=CronTrigger(hour="0,4,8,12,16,20", minute=2),
    id="calendar_refresh"
)
```

### Eventos Monitoreados

| Evento | Impacto | Bloqueo |
|--------|---------|---------|
| NFP (US) | Alto | ±30 min |
| FOMC | Alto | ±60 min |
| ECB Rate | Alto | ±30 min |
| CPI | Medio | ±30 min |
| GDP | Medio | ±30 min |

---

## Configuración

### Variables de Entorno

```env
# Scheduler
PIPELINE_TIMEZONE=UTC
PIPELINE_STAGGER_MINUTES=5

# Data
HISTORY_CANDLES=250
FEATURE_VERSION=v1

# Model paths
MODEL_CRYPTO=data/models/technical_crypto_v1.pkl
MODEL_FOREX=data/models/technical_forex_v1.pkl
```

---

## Testing

### Tests Unitarios

```bash
# Tests del pipeline
pytest tests/unit/test_pipeline.py -v
```

### Tests de Integración

```bash
# Test completo del pipeline
pytest tests/integration/test_pipeline_paper.py -v
```

### Test Manual

```bash
# Test un ciclo
python scripts/run_pipeline.py --once BTCUSDT

# Ver logs
tail -f logs/pipeline.log
```

---

*Volver al [índice de integración técnica](README.md)*
