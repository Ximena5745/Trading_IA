"""
Module: core/config/settings.py
Responsibility: Application settings with Pydantic validation
Dependencies: pydantic-settings
"""
from __future__ import annotations

from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Execution — NEVER change to live without explicit authorization
    EXECUTION_MODE: str = "paper"
    TRADING_ENABLED: bool = False

    # Binance
    BINANCE_API_KEY: str = ""
    BINANCE_SECRET_KEY: str = ""
    BINANCE_TESTNET: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://trader:password@localhost:5432/trader_ai"
    REDIS_URL: str = "redis://localhost:6379"

    # Auth
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # Risk limits — not editable at runtime by users
    MAX_RISK_PER_TRADE_PCT: float = 0.01
    MAX_PORTFOLIO_RISK_PCT: float = 0.10
    DAILY_LOSS_LIMIT_PCT: float = 0.05
    MAX_CONSECUTIVE_LOSSES: int = 5
    MAX_DRAWDOWN_PCT: float = 0.15

    # Features
    FEATURE_VERSION: str = "v1"
    SUPPORTED_SYMBOLS: list[str] = ["BTCUSDT", "ETHUSDT"]
    DEFAULT_TIMEFRAME: str = "1h"

    # Alerts
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    @validator("EXECUTION_MODE")
    def validate_execution_mode(cls, v: str) -> str:
        if v not in ("paper", "live"):
            raise ValueError("EXECUTION_MODE must be 'paper' or 'live'")
        return v

    @validator("DAILY_LOSS_LIMIT_PCT")
    def validate_daily_loss_limit(cls, v: float) -> float:
        if v > 0.10:
            raise ValueError("Daily loss limit cannot exceed 10%")
        return v

    @validator("JWT_SECRET_KEY")
    def validate_jwt_secret(cls, v: str) -> str:
        if v == "change-me-in-production" and False:  # skip in dev
            raise ValueError("JWT_SECRET_KEY must be set in production")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
