"""
Module: api/main.py
Responsibility: FastAPI application with lifespan, CORS, rate limiting
Dependencies: fastapi, slowapi, routes
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.routes.auth import router as auth_router
from api.routes.backtesting import router as backtesting_router
from api.routes.execution import router as execution_router
from api.routes.market import router as market_router
from api.routes.marketplace import router as marketplace_router
from api.routes.portfolio import router as portfolio_router
from api.routes.risk import router as risk_router
from api.routes.signals import router as signals_router
from api.routes.simulation import router as simulation_router
from api.routes.strategies import router as strategies_router
from core.agents.fundamental_agent import FundamentalAgent
from core.config.settings import get_settings
from core.execution.order_tracker import OrderTracker
from core.marketplace.strategy_marketplace import StrategyMarketplace
from core.monitoring.alert_engine import AlertEngine
from core.monitoring.performance_tracker import PerformanceTracker
from core.monitoring.prometheus_metrics import start_metrics_server
from core.observability.logger import configure_logging, get_logger
from core.portfolio.portfolio_manager import PortfolioManager
from core.risk.risk_manager import RiskManager
from core.simulation.historical_simulator import HistoricalSimulator
from core.strategies.strategy_registry import StrategyRegistry

configure_logging()
logger = get_logger(__name__)
settings = get_settings()

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Initialize core singletons ──────────────────────────────────────────
    portfolio_manager = PortfolioManager(
        total_capital=settings.INITIAL_CAPITAL,
        max_risk_per_trade_pct=settings.MAX_RISK_PER_TRADE_PCT,
    )
    performance_tracker = PerformanceTracker()
    order_tracker = OrderTracker()
    risk_manager = RiskManager()
    strategy_registry = StrategyRegistry()
    alert_engine = AlertEngine()

    # ── Fase 5 singletons ──────────────────────────────────────────────────
    marketplace = StrategyMarketplace()
    simulator = HistoricalSimulator()
    fundamental_agent = FundamentalAgent()

    # ── Inject into API route modules ──────────────────────────────────────
    from api.routes import execution as execution_routes
    from api.routes import marketplace as marketplace_routes
    from api.routes import portfolio as portfolio_routes
    from api.routes import simulation as simulation_routes
    from api.routes import strategies as strategies_routes

    portfolio_routes.set_portfolio_manager(portfolio_manager)
    portfolio_routes.set_performance_tracker(performance_tracker)
    execution_routes.set_order_tracker(order_tracker)
    execution_routes.set_risk_manager(risk_manager)
    strategies_routes.set_strategy_registry(strategy_registry)
    marketplace_routes.set_marketplace(marketplace)
    simulation_routes.set_simulator(simulator)
    simulation_routes.set_strategy_registry(strategy_registry)

    # ── Store on app.state for access elsewhere ─────────────────────────────
    app.state.portfolio_manager = portfolio_manager
    app.state.performance_tracker = performance_tracker
    app.state.order_tracker = order_tracker
    app.state.risk_manager = risk_manager
    app.state.strategy_registry = strategy_registry
    app.state.alert_engine = alert_engine
    app.state.marketplace = marketplace
    app.state.simulator = simulator
    app.state.fundamental_agent = fundamental_agent

    # ── Start FundamentalAgent background refresh task ─────────────────────
    import asyncio as _asyncio

    async def _refresh_fundamental():
        while True:
            await fundamental_agent.refresh()
            await _asyncio.sleep(1800)  # refresh every 30 min

    _asyncio.create_task(_refresh_fundamental())

    # ── Start Prometheus metrics endpoint ───────────────────────────────────
    try:
        start_metrics_server(port=8001)
        logger.info("prometheus_metrics_server_started", port=8001)
    except Exception as exc:
        logger.warning("prometheus_metrics_server_failed", error=str(exc))

    logger.info(
        "trader_ai_startup",
        execution_mode=settings.EXECUTION_MODE,
        trading_enabled=settings.TRADING_ENABLED,
        version="2.0.0",
    )

    if settings.EXECUTION_MODE == "live" and not settings.TRADING_ENABLED:
        logger.warning("live_mode_but_trading_disabled")

    yield

    logger.info("trader_ai_shutdown")


app = FastAPI(
    title="TRADER AI API",
    version="2.0.0",
    description="Algorithmic trading platform with explainable AI signals",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register all routers ────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(risk_router)
app.include_router(market_router)
app.include_router(signals_router)
app.include_router(backtesting_router)
app.include_router(portfolio_router)
app.include_router(execution_router)
app.include_router(strategies_router)
# Fase 5
app.include_router(marketplace_router)
app.include_router(simulation_router)


@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "execution_mode": settings.EXECUTION_MODE,
        "trading_enabled": settings.TRADING_ENABLED,
    }


@app.get("/", tags=["system"], include_in_schema=False)
async def root():
    return {"message": "TRADER AI API v2.0.0 — see /docs"}
