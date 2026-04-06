"""
Module: core/models.py
Responsibility: Shared Pydantic data models for the entire pipeline
Dependencies: pydantic
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator


# ---------------------------------------------------------------------------
# Asset Class
# ---------------------------------------------------------------------------


class AssetClass(str, Enum):
    CRYPTO = "crypto"
    FOREX = "forex"
    INDICES = "indices"
    COMMODITIES = "commodities"


class InstrumentConfig:
    """
    Per-instrument configuration for position sizing and cost modeling.
    Use mt5_symbol for the exact name in the IC Markets terminal.
    Verified IC Markets symbols — section 1.2 of PROYECTO.md v2.4.
    """

    __slots__ = (
        "symbol",
        "mt5_symbol",
        "asset_class",
        "pip_value",
        "lot_size",
        "min_lots",
        "lot_step",
        "spread_pips",
        "swap_long",
        "swap_short",
        "point",
    )

    def __init__(
        self,
        symbol: str,
        mt5_symbol: str,
        asset_class: "AssetClass",
        pip_value: float,  # USD value of 1 pip per standard lot
        lot_size: float,  # contract size (e.g. 100_000 for forex majors)
        min_lots: float = 0.01,
        lot_step: float = 0.01,
        spread_pips: float = 0.0,
        swap_long: float = 0.0,  # populated at runtime via MT5Client.get_symbol_info()
        swap_short: float = 0.0,
        point: float = 0.00001,
    ):
        self.symbol = symbol
        self.mt5_symbol = mt5_symbol
        self.asset_class = asset_class
        self.pip_value = pip_value
        self.lot_size = lot_size
        self.min_lots = min_lots
        self.lot_step = lot_step
        self.spread_pips = spread_pips
        self.swap_long = swap_long
        self.swap_short = swap_short
        self.point = point


# ── Instrument catalogue — IC Markets verified (PROYECTO.md §1.2) ──────────
# swap_long/swap_short are set to 0.0 here; MT5Client.get_symbol_info()
# refreshes them at runtime from the live broker feed.
INSTRUMENT_CONFIGS: dict[str, InstrumentConfig] = {
    # Forex majors — pip = 0.0001, lot = 100,000 units, pip_value ≈ $10/lot
    "EURUSD": InstrumentConfig(
        "EURUSD",
        "EURUSD",
        AssetClass.FOREX,
        pip_value=10.0,
        lot_size=100_000,
        spread_pips=0.6,
        swap_long=-0.5,  # typical IC Markets overnight rate (USD per lot per night)
        swap_short=-0.3,
    ),
    "GBPUSD": InstrumentConfig(
        "GBPUSD",
        "GBPUSD",
        AssetClass.FOREX,
        pip_value=10.0,
        lot_size=100_000,
        spread_pips=0.9,
    ),
    "AUDUSD": InstrumentConfig(
        "AUDUSD",
        "AUDUSD",
        AssetClass.FOREX,
        pip_value=10.0,
        lot_size=100_000,
        spread_pips=0.8,
    ),
    "USDJPY": InstrumentConfig(
        "USDJPY",
        "USDJPY",
        AssetClass.FOREX,
        pip_value=9.09,
        lot_size=100_000,
        spread_pips=0.7,
        point=0.001,
    ),
    "USDCHF": InstrumentConfig(
        "USDCHF",
        "USDCHF",
        AssetClass.FOREX,
        pip_value=10.94,
        lot_size=100_000,
        spread_pips=0.8,
    ),
    "USDCAD": InstrumentConfig(
        "USDCAD",
        "USDCAD",
        AssetClass.FOREX,
        pip_value=7.47,
        lot_size=100_000,
        spread_pips=0.8,
    ),
    # Commodity
    "XAUUSD": InstrumentConfig(
        "XAUUSD",
        "XAUUSD",
        AssetClass.COMMODITIES,
        pip_value=1.0,
        lot_size=100,
        spread_pips=0.25,
        point=0.01,
    ),
    # Indices CFD — point value varies; spread in index points
    "US500": InstrumentConfig(
        "US500",
        "US500",
        AssetClass.INDICES,
        pip_value=1.0,
        lot_size=1,
        spread_pips=0.4,
        point=0.1,
    ),
    "US30": InstrumentConfig(
        "US30",
        "US30",
        AssetClass.INDICES,
        pip_value=1.0,
        lot_size=1,
        spread_pips=2.0,
        point=1.0,
    ),
    "UK100": InstrumentConfig(
        "UK100",
        "UK100",
        AssetClass.INDICES,
        pip_value=1.0,
        lot_size=1,
        spread_pips=1.0,
        point=1.0,
    ),
    # Crypto CFD via MT5
    "BTCUSD": InstrumentConfig(
        "BTCUSD",
        "BTCUSD",
        AssetClass.CRYPTO,
        pip_value=1.0,
        lot_size=1,
        spread_pips=15.0,
        point=1.0,
    ),
}


def get_instrument(symbol: str) -> Optional["InstrumentConfig"]:
    """Return InstrumentConfig for a symbol, or None for Binance-native crypto."""
    return INSTRUMENT_CONFIGS.get(symbol.upper())


def detect_asset_class(symbol: str) -> AssetClass:
    """Infer asset class from symbol name heuristics."""
    s = symbol.upper()
    # Crypto: ends in USDT, USDC, BTC, ETH, BNB
    if s.endswith(("USDT", "USDC", "BUSD", "BTC", "ETH", "BNB")):
        return AssetClass.CRYPTO
    # Precious metals
    if s.startswith(("XAU", "XAG", "XPT", "XPD")):
        return AssetClass.COMMODITIES
    # Energy & agricultural commodities
    if s in ("USOIL", "UKOIL", "NATGAS", "WHEAT", "CORN", "SOYB"):
        return AssetClass.COMMODITIES
    # Equity indices
    if s in (
        "SPX500",
        "NAS100",
        "US500",
        "US30",
        "DE40",
        "UK100",
        "JP225",
        "AUS200",
        "HK50",
        "FR40",
    ):
        return AssetClass.INDICES
    # Forex: 6-char currency pairs (EURUSD, GBPUSD, etc.)
    # Note: precious metals like XAUUSD are already caught above before this branch
    if len(s) == 6 and s.isalpha():
        return AssetClass.FOREX
    # Default fallback
    return AssetClass.CRYPTO


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
    # Crypto-specific fields — optional so forex/indices/commodities work too
    quote_volume: Optional[Decimal] = None
    trades_count: Optional[int] = None
    taker_buy_volume: Optional[Decimal] = None
    # Metadata
    source: str = "unknown"  # e.g. "binance", "oanda", "alpha_vantage"
    asset_class: Optional[str] = None  # populated by the adapter
    feature_version: str = "v1"

    @model_validator(mode="after")
    def validate_ohlc_consistency(self) -> "MarketData":
        if self.high is not None and self.open is not None and self.high < self.open:
            raise ValueError("high must be >= open")
        if self.low is not None and self.open is not None and self.low > self.open:
            raise ValueError("low must be <= open")
        return self


# ---------------------------------------------------------------------------
# Feature Set
# ---------------------------------------------------------------------------


class FeatureSet(BaseModel):
    timestamp: datetime
    symbol: str
    version: str = "v1"
    asset_class: str = "crypto"  # inferred by FeatureEngine if not set

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

    # Microstructure (crypto-specific — optional for other asset classes)
    bid_ask_spread: Optional[float] = None
    order_book_imbalance: Optional[float] = None

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
    previous_regime: Optional[MarketRegime] = None
    signal_allowed: bool  # False in VOLATILE_CRASH or confidence < 0.5


# ---------------------------------------------------------------------------
# Agent Output
# ---------------------------------------------------------------------------


class AgentOutput(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

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
    asset_class: str = "crypto"
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
    exchange_order_id: Optional[str] = None
    idempotency_key: str
    signal_id: str
    symbol: str
    asset_class: str = "crypto"
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_loss: float
    take_profit: float
    status: OrderStatus
    fill_price: Optional[float] = None
    fill_quantity: Optional[float] = None
    commission: Optional[float] = None
    slippage: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    execution_mode: str = "paper"
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------


class Position(BaseModel):
    symbol: str
    asset_class: str = "crypto"
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


# Rebuild Portfolio model now that Position is fully defined
Portfolio.model_rebuild()


# ---------------------------------------------------------------------------
# Kill Switch State
# ---------------------------------------------------------------------------


class KillSwitchStateModel(BaseModel):
    active: bool
    triggered_at: Optional[datetime] = None
    triggered_by: Optional[str] = None
    daily_loss_current: float
    daily_loss_limit: float
    consecutive_losses: int
    max_consecutive_losses: int
    reset_at: Optional[datetime] = None
