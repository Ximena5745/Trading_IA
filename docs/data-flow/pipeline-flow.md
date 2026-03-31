# Flujo Completo del Pipeline

> Detalle paso a paso del flujo de datos en el sistema

## Visión General

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMPLETE PIPELINE FLOW                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 0: SCHEDULER (APScheduler)                                     │   │
│  │ Trigger: Cron every hour, staggered by symbol                       │   │
│  │ Schedule: BTCUSDT(:00), ETHUSDT(:05), EURUSD(:10), ...             │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 1: MARKET CALENDAR CHECK                                       │   │
│  │ if not calendar.is_market_open(symbol): SKIP                        │   │
│  │                                                                      │   │
│  │ Crypto: 24/7 always open                                            │   │
│  │ Forex: Mon-Fri 00:00-24:00 UTC                                      │   │
│  │ Indices: Regional trading hours                                      │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │ OPEN                                      │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 2: MACRO EVENT CHECK (non-crypto only)                         │   │
│  │ if fund_agent.is_blocked_by_event(symbol): SKIP                     │   │
│  │                                                                      │   │
│  │ Blocks during: NFP(±30min), FOMC(±60min), CPI(±30min)             │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │ NOT BLOCKED                               │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 3: FETCH OHLCV                                                 │   │
│  │                                                                      │   │
│  │ Crypto: BinanceClient.get_historical_klines("BTCUSDT", "1h", 250) │   │
│  │ Forex: MT5Client.get_historical_klines("EURUSD", "1h", 250)       │   │
│  │                                                                      │   │
│  │ Output: list[MarketData] with OHLCV                                │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 4: FEATURE ENGINEERING                                         │   │
│  │ FeatureEngine.calculate(df)                                         │   │
│  │                                                                      │   │
│  │ Input: pd.DataFrame (250 rows × OHLCV)                             │   │
│  │ Output: FeatureSet (17+ technical indicators)                       │   │
│  │                                                                      │   │
│  │ Indicators: RSI(7,14), MACD, EMAs(9,21,50,200), ATR, BB, VWAP     │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 5: ORDER BOOK ENRICHMENT (crypto only)                         │   │
│  │ if is_crypto:                                                       │   │
│  │     order_book = binance.get_order_book(symbol, depth=20)           │   │
│  │     micro_data = micro_agent.analyze_order_book(order_book)         │   │
│  │     features = features.model_copy(update=micro_data)               │   │
│  │                                                                      │   │
│  │ Adds: bid_ask_spread, order_book_imbalance                          │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 6: AGENTS EXECUTION                                            │   │
│  │                                                                      │   │
│  │ ┌─────────────────────────────────────────────────────────────────┐ │   │
│  │ │ TechnicalAgent.predict(features)                                 │ │   │
│  │ │ → AgentOutput(score=0.65, direction="BUY", shap_values={...})   │ │   │
│  │ └─────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │ ┌─────────────────────────────────────────────────────────────────┐ │   │
│  │ │ RegimeAgent.predict(features)                                    │ │   │
│  │ │ → AgentOutput(score=0.45, direction="BUY", confidence=0.72)     │ │   │
│  │ └─────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │ ┌─────────────────────────────────────────────────────────────────┐ │   │
│  │ │ MicrostructureAgent.predict(features)                            │ │   │
│  │ │ → AgentOutput(score=0.30, direction="BUY")                       │ │   │
│  │ └─────────────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 7: CONSENSUS ENGINE                                            │   │
│  │ Weighted voting (asset-class conditional)                           │   │
│  │                                                                      │   │
│  │ Crypto weights:    Technical 45% | Regime 35% | Micro 20%          │   │
│  │ MT5 weights:       Technical 55% | Regime 45% | Micro 0%           │   │
│  │                                                                      │   │
│  │ Checks:                                                             │   │
│  │ 1. Regime gate (VOLATILE_CRASH → block)                            │   │
│  │ 2. Minimum score (|weighted_score| ≥ 0.30)                         │   │
│  │ 3. Minimum agreement (≥ 60% agents agree)                          │   │
│  │                                                                      │   │
│  │ Output: ConsensusOutput(final_direction, weighted_score, ...)      │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 8: SIGNAL ENGINE                                               │   │
│  │ if consensus.final_direction == "NEUTRAL": return None             │   │
│  │                                                                      │   │
│  │ Calculate SL/TP:                                                    │   │
│  │ - SL = entry - ATR × 2.0                                            │   │
│  │ - TP = entry + ATR × 3.0                                            │   │
│  │                                                                      │   │
│  │ Validate R:R ≥ 1.5                                                  │   │
│  │ if R:R < 1.5: reject signal                                         │   │
│  │                                                                      │   │
│  │ Generate XAI explanation from SHAP values                           │   │
│  │                                                                      │   │
│  │ Output: Signal(entry, SL, TP, R:R, explanation, summary)           │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │ SIGNAL GENERATED                          │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 9: RISK VALIDATION                                             │   │
│  │                                                                      │   │
│  │ Checks (in order):                                                  │   │
│  │ 1. Kill Switch active? → REJECT                                     │   │
│  │ 2. Risk exposure > 15%? → REJECT                                    │   │
│  │ 3. Drawdown > 20%? → TRIGGER KILL + REJECT                         │   │
│  │ 4. R:R < 1.5? → REJECT                                             │   │
│  │ 5. Consecutive losses > 7? → TRIGGER KILL + REJECT                 │   │
│  │                                                                      │   │
│  │ Position sizing (instrument-aware):                                 │   │
│  │ - Crypto: qty = capital_risk / price_risk                           │   │
│  │ - Forex: lots = capital_risk / (stop_pips × pip_value)             │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │ APPROVED                                   │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 10: EXECUTION                                                  │   │
│  │                                                                      │   │
│  │ PaperExecutor (default):                                            │   │
│  │ - Apply slippage (0.05%)                                            │   │
│  │ - Apply commission (0.1%)                                           │   │
│  │ - Simulate latency (50-200ms)                                       │   │
│  │                                                                      │   │
│  │ MT5Executor (live mode, if configured):                             │   │
│  │ - Send MARKET order to IC Markets                                   │   │
│  │ - Wait for fill                                                     │   │
│  │                                                                      │   │
│  │ Output: Order(fill_price, commission, slippage, status="filled")   │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │ ORDER FILLED                               │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 11: PORTFOLIO UPDATE                                           │   │
│  │                                                                      │   │
│  │ portfolio.open_position(signal, quantity, fill_price)               │   │
│  │ - Deduct cost from available capital                                │   │
│  │ - Add position to active positions                                  │   │
│  │ - Update risk exposure                                              │   │
│  │                                                                      │   │
│  │ risk.update_kill_switch(portfolio, trades)                          │   │
│  │ - Check daily loss limit                                            │   │
│  │ - Check drawdown                                                    │   │
│  │ - Check consecutive losses                                          │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 12: PERSIST                                                    │   │
│  │                                                                      │   │
│  │ FeatureStore (Redis):                                               │   │
│  │ - Save features with 1-hour TTL                                     │   │
│  │                                                                      │   │
│  │ TradingRepository (PostgreSQL):                                     │   │
│  │ - Save signal                                                       │   │
│  │ - Save order                                                        │   │
│  │ - Save portfolio snapshot                                           │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 13: ALERT                                                      │   │
│  │                                                                      │   │
│  │ AlertEngine.on_signal(signal)                                       │   │
│  │                                                                      │   │
│  │ if telegram_bot.is_configured():                                    │   │
│  │     telegram_bot.send_signal_alert(signal)                          │   │
│  │                                                                      │   │
│  │ Alert includes:                                                     │   │
│  │ - Symbol, Action, Confidence                                        │   │
│  │ - Entry, SL, TP, R:R                                                │   │
│  │ - XAI Summary                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Almacenamiento por Tipo de Dato

### FeatureStore (Redis)

```python
# Key: features:{symbol}:{timestamp}
# Value: JSON FeatureSet
# TTL: 1 hora

await feature_store.save(features)
features = await feature_store.get(symbol, timestamp)
```

### TradingRepository (PostgreSQL)

```python
# Tablas:
# - signals: Señales generadas
# - orders: Órdenes ejecutadas
# - portfolio_snapshots: Estado del portafolio
# - candles: OHLCV histórico (TimescaleDB hypertable)

await repo.save_signal(signal)
await repo.save_order(order)
await repo.save_portfolio_snapshot(portfolio)
```

---

## Métricas del Pipeline

### Métricas por Ciclo

```python
logger.info(
    "cycle_complete",
    symbol=symbol,
    asset_class=asset_class.value,
    signal=signal.action,
    confidence=signal.confidence,
    quantity=quantity,
    elapsed_s=round(elapsed, 2),
)
```

### Métricas Prometheus

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| pipeline_cycles_total | Counter | Total de ciclos ejecutados |
| pipeline_signals_total | Counter | Total de señales generadas |
| pipeline_cycle_duration | Histogram | Duración del ciclo |
| pipeline_errors_total | Counter | Errores por símbolo |

---

## Error Handling

### En Cada Paso

```python
try:
    # Step logic
except Exception as exc:
    logger.error("cycle_error", symbol=symbol, error=str(exc), exc_info=True)
    await alert.on_critical_error("pipeline_cycle", f"{symbol}: {exc}")
```

### Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| Connection timeout | Exchange caído | Retry automático |
| No candles returned | Mercado cerrado | Verificar calendar |
| Feature calculation error | Datos incompletos | Validar OHLCV |
| Model not loaded | .pkl no existe | Usar fallback rule-based |
| MT5 not configured | Credenciales faltantes | Configurar .env |

---

## Testing

### Test Manual

```bash
# Un ciclo completo
python scripts/run_pipeline.py --once BTCUSDT

# Scheduler completo
python scripts/run_pipeline.py
```

### Tests de Integración

```bash
# Pipeline en modo paper
pytest tests/integration/test_pipeline_paper.py -v
```

---

## Configuración

### Variables de Entorno

```env
# Pipeline
PIPELINE_TIMEZONE=UTC
HISTORY_CANDLES=250
FEATURE_VERSION=v1

# Model paths
MODEL_CRYPTO=data/models/technical_crypto_v1.pkl
MODEL_FOREX=data/models/technical_forex_v1.pkl
```

---

*Volver al [índice de flujo de datos](README.md)*
