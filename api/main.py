"""
Module: api/main.py
Responsibility: FastAPI application with lifespan, CORS, rate limiting
Dependencies: fastapi, slowapi, routes
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.routes.auth import router as auth_router
from api.routes.backtesting import router as backtesting_router
from api.routes.dashboard import router as dashboard_router
from api.routes.execution import router as execution_router
from api.routes.market import (
    router as market_router,
    update_features_cache,
    update_market_data_cache,
    update_regime_cache,
)
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
from core.db.session import close_pool, init_pool
from core.features.indicators import calculate_all
from core.monitoring.alert_engine import AlertEngine
from core.notifications.telegram_bot import TelegramBot
from core.monitoring.performance_tracker import PerformanceTracker
from core.monitoring.prometheus_metrics import start_metrics_server
from core.observability.logger import configure_logging, get_logger
from core.portfolio.portfolio_manager import PortfolioManager
from core.risk.kill_switch import KillSwitch
from core.risk.risk_manager import RiskManager
from core.simulation.historical_simulator import HistoricalSimulator
from core.strategies.strategy_registry import StrategyRegistry

configure_logging()
logger = get_logger(__name__)
settings = get_settings()

limiter = Limiter(key_func=get_remote_address)


def _map_regime(row: pd.Series) -> str:
    trend = row.get("trend_direction", "sideways")
    vol = row.get("volatility_regime", "medium")
    if trend == "bullish":
        return "BULL TRENDING"
    if trend == "bearish":
        return "BEAR TRENDING"
    if vol == "extreme":
        return "VOLATILE_CRASH"
    return "SIDEWAYS"


def _load_parquet_data() -> None:
    """Load all available parquet files (all timeframes) into market data cache."""
    base_dir = Path("data/raw/parquet")
    if not base_dir.exists():
        logger.warning("parquet_data_dir_not_found", path=str(base_dir))
        return

    symbol_map = {
        "eurusd": "EURUSD", "gbpusd": "GBPUSD", "usdjpy": "USDJPY",
        "us30": "US30", "us500": "US500", "xauusd": "XAUUSD",
    }

    loaded_count = 0

    # Iterate through all timeframe directories
    for tf_dir in base_dir.iterdir():
        if not tf_dir.is_dir():
            continue
        
        tf = tf_dir.name  # Get timeframe from directory name (1wk, 1mo, etc.)

        for file in tf_dir.glob("*.parquet"):
            # Match filename to symbol (e.g., eurusd_1wk.parquet -> EURUSD)
            stem = file.stem.lower()  # e.g., "eurusd_1wk"
            
            symbol = None
            for prefix, sym in symbol_map.items():
                if stem.startswith(prefix):
                    symbol = sym
                    break
            
            if not symbol:
                logger.debug("parquet_skipped_unknown", file=file.name)
                continue
            
            try:
                df = pd.read_parquet(file)
                
                # Calculate indicators if not present
                if "rsi_14" not in df.columns:
                    df = calculate_all(df)

                records = df.to_dict(orient="records")
                cleaned = []
                for r in records:
                    clean = {}
                    for k, v in r.items():
                        if pd.isna(v):
                            clean[k] = None
                        elif hasattr(v, "item"):
                            clean[k] = v.item()
                        elif isinstance(v, pd.Timestamp):
                            clean[k] = v.isoformat()
                        else:
                            clean[k] = v
                    cleaned.append(clean)

                update_market_data_cache(symbol, cleaned, timeframe=tf)

                latest = df.iloc[-1]
                features = {
                    "rsi_14": float(latest.get("rsi_14", 50)),
                    "rsi_7": float(latest.get("rsi_7", 50)),
                    "macd_line": float(latest.get("macd_line", 0)),
                    "macd_signal": float(latest.get("macd_signal", 0)),
                    "macd_histogram": float(latest.get("macd_histogram", 0)),
                    "bb_upper": float(latest.get("bb_upper", 0)),
                    "bb_lower": float(latest.get("bb_lower", 0)),
                    "bb_width": float(latest.get("bb_width", 0)),
                    "atr_14": float(latest.get("atr_14", 0)),
                    "volume_ratio": float(latest.get("volume_ratio", 1)),
                    "technical_score": 0.3,
                    "regime_score": 0.5,
                    "micro_score": 0.1,
                    "regime": _map_regime(latest),
                    "fundamental_status": "CLEAR",
                    "consensus_score": 0.45,
                    "sl": float(latest.get("bb_lower", 0)),
                    "tp": float(latest.get("bb_upper", 0)),
                }
                update_features_cache(symbol, features)
                update_regime_cache(symbol, {"regime": features["regime"]})
                loaded_count += 1
                logger.info("parquet_loaded", symbol=symbol, timeframe=tf, rows=len(df))
            except Exception as exc:
                logger.error("parquet_load_failed", symbol=symbol, timeframe=tf, file=file.name, error=str(exc))

    logger.info("parquet_data_loading_complete", total_loaded=loaded_count)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Initialize core singletons ──────────────────────────────────────────
    portfolio_manager = PortfolioManager(
        settings=settings,
        initial_capital=10_000.0,
    )
    performance_tracker = PerformanceTracker()
    order_tracker = OrderTracker()
    kill_switch = KillSwitch(settings)
    risk_manager = RiskManager(settings=settings, kill_switch=kill_switch)
    strategy_registry = StrategyRegistry()
    telegram_bot = TelegramBot(
        token=settings.TELEGRAM_BOT_TOKEN,
        chat_id=settings.TELEGRAM_CHAT_ID,
    )
    alert_engine = AlertEngine(telegram_bot=telegram_bot)

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

    # ── Load real parquet data into cache ───────────────────────────────────
    _load_parquet_data()

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

    import asyncio as _asyncio2

    _asyncio2.create_task(
        alert_engine.on_system_restart("2.0.0", settings.EXECUTION_MODE)
    )

    # ── Start pipeline scheduler ────────────────────────────────────────────
    _scheduler = None
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        from scripts.run_pipeline import SCHEDULE, _build_components, _pipeline_cycle

        await init_pool(settings.DATABASE_URL)
        _pipeline_components = await _build_components(settings)

        _scheduler = AsyncIOScheduler(timezone="UTC")
        for symbol, minute_offset in SCHEDULE:
            _scheduler.add_job(
                _pipeline_cycle,
                trigger=CronTrigger(minute=minute_offset, timezone="UTC"),
                args=[symbol, _pipeline_components],
                id=f"pipeline_{symbol}",
                max_instances=1,
                coalesce=True,
                misfire_grace_time=120,
            )
        _scheduler.start()
        logger.info("pipeline_scheduler_started", jobs=len(SCHEDULE))
    except ImportError:
        logger.warning("apscheduler_not_installed", hint="pip install apscheduler")
    except Exception as exc:
        logger.error("pipeline_scheduler_failed", error=str(exc))

    yield

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    await close_pool()
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
    allow_origins=["http://localhost:8501", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve static dashboard ──────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Register all routers ────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(risk_router)
app.include_router(market_router)
app.include_router(signals_router)
app.include_router(backtesting_router)
app.include_router(dashboard_router)
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


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("static/dashboard.html")
