"""
Module: core/config/settings.py
Responsibility: Application settings with Pydantic validation
Dependencies: pydantic-settings
"""
from __future__ import annotations

from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings

from core.config.constants import TRADED_UNIVERSE


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
    # Public self-registration. OFF by default (SPEC-A01 / F-01). When ON, the
    # public endpoint only ever creates a `viewer`.
    REGISTRATION_ENABLED: bool = False
    # Escape hatch for the JWT secret validator — tests only.
    ALLOW_INSECURE_JWT: bool = False

    # ── Risk limits — not editable at runtime by users ──────────────────────
    MAX_RISK_PER_TRADE_PCT: float = 0.01
    MAX_PORTFOLIO_RISK_PCT: float = 0.10
    DAILY_LOSS_LIMIT_PCT: float = 0.05
    MAX_CONSECUTIVE_LOSSES: int = 5
    MAX_DRAWDOWN_PCT: float = 0.15

    # ── Asset universe ──────────────────────────────────────────────────────
    FEATURE_VERSION: str = "v1"
    DEFAULT_TIMEFRAME: str = "1h"

    # Symbols to trade — THE single source is core.config.constants.TRADED_UNIVERSE
    # (ADR-004 / SPEC-B03). Can still be narrowed via env var as a JSON list:
    # SUPPORTED_SYMBOLS='["EURUSD","XAUUSD"]'
    SUPPORTED_SYMBOLS: list[str] = list(TRADED_UNIVERSE)

    # ── MetaTrader 5 (FASE E) ────────────────────────────────────────────────
    MT5_SERVER: str = "ICMarketsSC-Demo04"
    MT5_LOGIN: int = 0
    MT5_PASSWORD: str = ""

    # ── Portfolio ───────────────────────────────────────────────────────────
    PORTFOLIO_BASE_CURRENCY: str = "USD"  # always USD — decision v2.4

    # ── Alerts ──────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("EXECUTION_MODE")
    @classmethod
    def validate_execution_mode(cls, v: str) -> str:
        if v not in ("paper", "live"):
            raise ValueError("EXECUTION_MODE must be 'paper' or 'live'")
        return v

    @field_validator("DAILY_LOSS_LIMIT_PCT")
    @classmethod
    def validate_daily_loss_limit(cls, v: float) -> float:
        if v > 0.10:
            raise ValueError("Daily loss limit cannot exceed 10%")
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Always enforced (SPEC-A01 / F-08): ≥32 chars and not the default,
        unless ALLOW_INSECURE_JWT=true (env) — for tests only."""
        import os

        if os.getenv("ALLOW_INSECURE_JWT", "").strip().lower() in ("1", "true", "yes"):
            return v
        if v == "change-me-in-production":
            raise ValueError("JWT_SECRET_KEY must be changed from the default value")
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("OANDA_ENVIRONMENT")
    @classmethod
    def validate_oanda_env(cls, v: str) -> str:
        if v not in ("practice", "live"):
            raise ValueError("OANDA_ENVIRONMENT must be 'practice' or 'live'")
        return v


def get_settings() -> Settings:
    return Settings()
