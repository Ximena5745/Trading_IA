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

    # ── Crypto exchanges ────────────────────────────────────────────────────
    BINANCE_API_KEY: str = ""
    BINANCE_SECRET_KEY: str = ""
    BINANCE_TESTNET: bool = True

    BYBIT_API_KEY: str = ""
    BYBIT_SECRET_KEY: str = ""

    # ── Forex / CFD broker (OANDA) ──────────────────────────────────────────
    # OANDA offers forex, indices AND commodities via a single REST API.
    # Sign up at https://www.oanda.com/us-en/trading/
    OANDA_API_KEY: str = ""
    OANDA_ACCOUNT_ID: str = ""
    OANDA_ENVIRONMENT: str = "practice"  # "practice" | "live"

    # ── Market data providers ───────────────────────────────────────────────
    # Alpha Vantage — free tier: 25 req/day; paid: unlimited
    # https://www.alphavantage.co/support/#api-key
    ALPHA_VANTAGE_API_KEY: str = ""

    # ── Database ────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://trader:password@localhost:5432/trader_ai"
    REDIS_URL: str = "redis://localhost:6379"

    # ── Auth ────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # ── Risk limits — not editable at runtime by users ──────────────────────
    MAX_RISK_PER_TRADE_PCT: float = 0.01
    MAX_PORTFOLIO_RISK_PCT: float = 0.10
    DAILY_LOSS_LIMIT_PCT: float = 0.05
    MAX_CONSECUTIVE_LOSSES: int = 5
    MAX_DRAWDOWN_PCT: float = 0.15

    # ── Asset universe ──────────────────────────────────────────────────────
    FEATURE_VERSION: str = "v1"
    DEFAULT_TIMEFRAME: str = "1h"

    # Symbols to trade — loaded from constants by default; can be overridden
    # via env var as a JSON list: SUPPORTED_SYMBOLS='["EURUSD","XAUUSD"]'
    SUPPORTED_SYMBOLS: list[str] = [
        # Crypto
        "BTCUSDT", "ETHUSDT",
        # Forex
        "EURUSD", "GBPUSD", "USDJPY",
        # Indices
        "SPX500", "NAS100",
        # Commodities
        "XAUUSD", "USOIL",
    ]

    # ── MetaTrader 5 (FASE E) ────────────────────────────────────────────────
    MT5_SERVER:   str = "ICMarketsSC-Demo04"
    MT5_LOGIN:    int = 0
    MT5_PASSWORD: str = ""

    # ── Portfolio ───────────────────────────────────────────────────────────
    PORTFOLIO_BASE_CURRENCY: str = "USD"  # always USD — decision v2.4

    # ── Alerts ──────────────────────────────────────────────────────────────
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

    @validator("OANDA_ENVIRONMENT")
    def validate_oanda_env(cls, v: str) -> str:
        if v not in ("practice", "live"):
            raise ValueError("OANDA_ENVIRONMENT must be 'practice' or 'live'")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
