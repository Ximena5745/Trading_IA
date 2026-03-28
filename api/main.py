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
from api.routes.risk import router as risk_router
from core.config.settings import get_settings
from core.observability.logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)
settings = get_settings()

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("trader_ai_startup", execution_mode=settings.EXECUTION_MODE, trading_enabled=settings.TRADING_ENABLED)
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

app.include_router(auth_router)
app.include_router(risk_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "execution_mode": settings.EXECUTION_MODE,
        "trading_enabled": settings.TRADING_ENABLED,
    }
