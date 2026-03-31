# Componentes del Sistema

> Detalle de cada componente y sus responsabilidades

---

## Core Components

### Agent System

| Componente | Archivo | Responsabilidad |
|------------|---------|-----------------|
| BaseAgent | `core/agents/base_agent.py` | Interfaz abstracta |
| TechnicalAgent | `core/agents/technical_agent.py` | LightGBM + SHAP |
| RegimeAgent | `core/agents/regime_agent.py` | Market regime classification |
| MicrostructureAgent | `core/agents/microstructure_agent.py` | Order book analysis |
| FundamentalAgent | `core/agents/fundamental_agent.py` | Events & sentiment |

### Consensus & Signals

| Componente | Archivo | Responsabilidad |
|------------|---------|-----------------|
| ConsensusEngine | `core/consensus/voting_engine.py` | Weighted voting |
| ConflictLogger | `core/consensus/conflict_logger.py` | Conflict detection |
| SignalEngine | `core/signals/signal_engine.py` | Signal generation |
| XAIModule | `core/signals/xai_module.py` | Explainability |

### Risk Management

| Componente | Archivo | Responsabilidad |
|------------|---------|-----------------|
| RiskManager | `core/risk/risk_manager.py` | Signal validation |
| KillSwitch | `core/risk/kill_switch.py` | Emergency stop |
| PositionSizer | `core/risk/position_sizer.py` | Position sizing |

### Portfolio & Execution

| Componente | Archivo | Responsabilidad |
|------------|---------|-----------------|
| PortfolioManager | `core/portfolio/portfolio_manager.py` | Capital management |
| Rebalancer | `core/portfolio/rebalancer.py` | Strategy rebalancing |
| PaperExecutor | `core/execution/paper_executor.py` | Paper trading |
| LiveExecutor | `core/execution/live_executor.py` | Live trading (Binance) |
| MT5Executor | `core/execution/mt5_executor.py` | MT5 execution |
| OrderTracker | `core/execution/order_tracker.py` | Order tracking |

### Data & Features

| Componente | Archivo | Responsabilidad |
|------------|---------|-----------------|
| FeatureEngine | `core/features/feature_engineering.py` | Calculate indicators |
| FeatureStore | `core/features/feature_store.py` | Redis cache |
| FeatureValidator | `core/features/feature_validator.py` | Data validation |

### Ingestion

| Componente | Archivo | Responsabilidad |
|------------|---------|-----------------|
| BinanceClient | `core/ingestion/binance_client.py` | Binance API |
| BybitClient | `core/ingestion/bybit_client.py` | Bybit API |
| MT5Client | `core/ingestion/providers/mt5_client.py` | MT5 API |
| ExchangeAdapter | `core/ingestion/exchange_adapter.py` | Unified interface |
| WebSocketStream | `core/ingestion/websocket_stream.py` | Real-time streaming |
| MarketCalendar | `core/ingestion/market_calendar.py` | Market hours |
| DataValidator | `core/ingestion/data_validator.py` | Data integrity |

### Strategies

| Componente | Archivo | Responsabilidad |
|------------|---------|-----------------|
| BaseStrategy | `core/strategies/base_strategy.py` | Interfaz abstracta |
| EmaRsiStrategy | `core/strategies/builtin/ema_rsi.py` | EMA + RSI |
| MeanReversionStrategy | `core/strategies/builtin/mean_reversion.py` | Bollinger Bands |
| StrategyBuilder | `core/strategies/strategy_builder.py` | Dynamic builder |
| StrategyRegistry | `core/strategies/strategy_registry.py` | Strategy catalog |

---

## API Components

| Componente | Archivo | Responsabilidad |
|------------|---------|-----------------|
| Main App | `api/main.py` | FastAPI app + lifespan |
| Dependencies | `api/dependencies.py` | Auth dependencies |
| Auth Routes | `api/routes/auth.py` | Authentication |
| Market Routes | `api/routes/market.py` | Market data |
| Signal Routes | `api/routes/signals.py` | Signal management |
| Strategy Routes | `api/routes/strategies.py` | Strategy management |
| Portfolio Routes | `api/routes/portfolio.py` | Portfolio |
| Risk Routes | `api/routes/risk.py` | Risk management |
| Execution Routes | `api/routes/execution.py` | Order execution |
| Backtest Routes | `api/routes/backtesting.py` | Backtesting |
| Simulation Routes | `api/routes/simulation.py` | Simulation |
| Marketplace Routes | `api/routes/marketplace.py` | Marketplace |

---

## Dashboard Components

| Componente | Archivo | Responsabilidad |
|------------|---------|-----------------|
| Main Dashboard | `app/dashboard.py` | Entry point |
| Market View | `app/pages/market_view.py` | Market data |
| Signals | `app/pages/signals.py` | Signal history |
| Strategies | `app/pages/strategies.py` | Strategy management |
| Portfolio | `app/pages/portfolio.py` | Portfolio view |
| Backtesting | `app/pages/backtesting.py` | Backtest results |
| Risk Monitor | `app/pages/risk_monitor.py` | Risk monitoring |
| Simulator | `app/pages/simulator.py` | Historical simulator |

---

## Scripts

| Script | Responsabilidad |
|--------|-----------------|
| `scripts/run_pipeline.py` | Main pipeline scheduler |
| `scripts/run_backtest.py` | Backtesting runner |
| `scripts/retrain.py` | Model retraining |
| `scripts/download_data.py` | Data download |
| `scripts/seed_data.py` | Initial data seeding |
| `scripts/seed_admin.py` | Admin user creation |
| `scripts/backup_db.py` | Database backup |
| `scripts/ci_backtest_gate.py` | CI quality gate |

---

*Volver al [índice de arquitectura](README.md)*
