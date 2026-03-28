"""
Module: core/models.py
Responsibility: Shared Pydantic data models for the entire pipeline
Dependencies: pydantic
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, validator

# ---------------------------------------------------------------------------
# Market Data
# ---------------------------------------------------------------------------


class MarketData(BaseModel):
    timestamp: datetime
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    quote_volume: Decimal
    trades_count: int
    taker_buy_volume: Decimal
    source: str = "binance"
    feature_version: str = "v1"

    @validator("high")
    def high_gte_open(cls, v: Decimal, values: dict) -> Decimal:
        if "open" in values and v < values["open"]:
            raise ValueError("high must be >= open")
        return v

    @validator("low")
    def low_lte_open(cls, v: Decimal, values: dict) -> Decimal:
        if "open" in values and v > values["open"]:
            raise ValueError("low must be <= open")
        return v


# ---------------------------------------------------------------------------
# Feature Set
# ---------------------------------------------------------------------------


class FeatureSet(BaseModel):
    timestamp: datetime
    symbol: str
    version: str = "v1"

    # Momentum
    rsi_14: float
    rsi_7: float
    macd_line: float
    macd_signal: float
    macd_histogram: float

    # Trend
    ema_9: float
    ema_21: float
    ema_50: float
    ema_200: float
    trend_direction: str  # "bullish" | "bearish" | "sideways"

    # Volatility
    atr_14: float
    bb_upper: float
    bb_lower: float
    bb_width: float
    volatility_regime: str  # "low" | "medium" | "high" | "extreme"

    # Volume
    vwap: float
    volume_sma_20: float
    volume_ratio: float
    obv: float

    # Microstructure (optional)
    bid_ask_spread: float | None = None
    order_book_imbalance: float | None = None

    # Raw close for signal engine
    close: float = 0.0


# ---------------------------------------------------------------------------
# Market Regime
# ---------------------------------------------------------------------------


class MarketRegime(str, Enum):
    BULL_TRENDING = "bull_trending"
    BEAR_TRENDING = "bear_trending"
    SIDEWAYS_LOW_VOL = "sideways_low_vol"
    SIDEWAYS_HIGH_VOL = "sideways_high_vol"
    VOLATILE_CRASH = "volatile_crash"


class RegimeOutput(BaseModel):
    timestamp: datetime
    symbol: str
    regime: MarketRegime
    confidence: float
    regime_duration_bars: int
    previous_regime: MarketRegime | None = None
    signal_allowed: bool  # False in VOLATILE_CRASH or confidence < 0.5


# ---------------------------------------------------------------------------
# Agent Output
# ---------------------------------------------------------------------------


class AgentOutput(BaseModel):
    agent_id: str
    timestamp: datetime
    symbol: str
    direction: str  # "BUY" | "SELL" | "NEUTRAL"
    score: float  # -1.0 to +1.0
    confidence: float
    features_used: list[str]
    shap_values: dict[str, float]
    model_version: str


# ---------------------------------------------------------------------------
# Consensus Output
# ---------------------------------------------------------------------------


class ConsensusOutput(BaseModel):
    timestamp: datetime
    symbol: str
    final_direction: str
    weighted_score: float
    agents_agreement: float
    blocked_by_regime: bool
    agent_outputs: list[AgentOutput]
    conflicts: list[str]


# ---------------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------------


class SignalExplanationFactor(BaseModel):
    factor: str
    weight: float
    direction: str
    description: str


class Signal(BaseModel):
    id: str
    idempotency_key: str
    timestamp: datetime
    symbol: str
    action: str  # "BUY" | "SELL" | "HOLD"
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    confidence: float
    explanation: list[SignalExplanationFactor]
    summary: str
    regime: MarketRegime
    strategy_id: str
    status: str = "pending"


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Order(BaseModel):
    id: str
    exchange_order_id: str | None = None
    idempotency_key: str
    signal_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: float | None = None
    stop_loss: float
    take_profit: float
    status: OrderStatus
    fill_price: float | None = None
    fill_quantity: float | None = None
    commission: float | None = None
    slippage: float | None = None
    created_at: datetime
    updated_at: datetime
    execution_mode: str = "paper"
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------


class Position(BaseModel):
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    strategy_id: str
    opened_at: datetime


class Portfolio(BaseModel):
    id: str
    total_capital: float
    available_capital: float
    positions: list[Position]
    risk_exposure: float
    daily_pnl: float
    daily_pnl_pct: float
    total_pnl: float
    drawdown_current: float
    drawdown_max: float
    updated_at: datetime


# ---------------------------------------------------------------------------
# Kill Switch State
# ---------------------------------------------------------------------------


class KillSwitchStateModel(BaseModel):
    active: bool
    triggered_at: datetime | None = None
    triggered_by: str | None = None
    daily_loss_current: float
    daily_loss_limit: float
    consecutive_losses: int
    max_consecutive_losses: int
    reset_at: datetime | None = None
