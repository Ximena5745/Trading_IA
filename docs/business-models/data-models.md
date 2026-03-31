# Modelos de Datos

> Definiciones Pydantic de todo el dominio de la aplicación

## Archivo Principal

`core/models.py` - Contiene todos los modelos compartidos

---

## Enumeraciones

### AssetClass

```python
class AssetClass(str, Enum):
    CRYPTO = "crypto"
    FOREX = "forex"
    INDICES = "indices"
    COMMODITIES = "commodities"
```

### MarketRegime

```python
class MarketRegime(str, Enum):
    BULL_TRENDING = "bull_trending"
    BEAR_TRENDING = "bear_trending"
    SIDEWAYS_LOW_VOL = "sideways_low_vol"
    SIDEWAYS_HIGH_VOL = "sideways_high_vol"
    VOLATILE_CRASH = "volatile_crash"
```

### OrderStatus

```python
class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
```

---

## Modelo: MarketData

### Definición

```python
class MarketData(BaseModel):
    timestamp: datetime
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    # Crypto-specific (opcional)
    quote_volume: Optional[Decimal] = None
    trades_count: Optional[int] = None
    taker_buy_volume: Optional[Decimal] = None
    # Metadata
    source: str = "unknown"
    asset_class: Optional[str] = None
    feature_version: str = "v1"
```

### Validaciones

```python
@model_validator(mode="after")
def validate_ohlc_consistency(self) -> "MarketData":
    if self.high < self.open:
        raise ValueError("high must be >= open")
    if self.low > self.open:
        raise ValueError("low must be <= open")
    return self
```

### Ejemplo

```json
{
    "timestamp": "2026-03-30T12:00:00Z",
    "symbol": "BTCUSDT",
    "open": 50000.00,
    "high": 50500.00,
    "low": 49800.00,
    "close": 50200.00,
    "volume": 1250.50,
    "source": "binance",
    "asset_class": "crypto"
}
```

---

## Modelo: FeatureSet

### Definición

```python
class FeatureSet(BaseModel):
    timestamp: datetime
    symbol: str
    version: str = "v1"
    asset_class: str = "crypto"

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

    # Microstructure (crypto only)
    bid_ask_spread: Optional[float] = None
    order_book_imbalance: Optional[float] = None

    # Raw close
    close: float = 0.0
```

### Ejemplo

```json
{
    "timestamp": "2026-03-30T12:00:00Z",
    "symbol": "BTCUSDT",
    "rsi_14": 42.5,
    "rsi_7": 38.2,
    "macd_line": 125.3,
    "macd_signal": 98.7,
    "macd_histogram": 26.6,
    "ema_9": 50150.0,
    "ema_21": 49800.0,
    "ema_50": 48500.0,
    "ema_200": 45000.0,
    "trend_direction": "bullish",
    "atr_14": 850.5,
    "bb_upper": 51200.0,
    "bb_lower": 48800.0,
    "bb_width": 0.048,
    "volatility_regime": "medium",
    "vwap": 50100.0,
    "volume_sma_20": 1200.0,
    "volume_ratio": 1.04,
    "obv": 450000.5,
    "close": 50200.0
}
```

---

## Modelo: AgentOutput

### Definición

```python
class AgentOutput(BaseModel):
    agent_id: str
    timestamp: datetime
    symbol: str
    direction: str        # "BUY" | "SELL" | "NEUTRAL"
    score: float          # -1.0 to +1.0
    confidence: float     # 0.0 to 1.0
    features_used: list[str]
    shap_values: dict[str, float]
    model_version: str
```

### Interpretación de Score

| Score | Significado |
|-------|-------------|
| +1.0 | Señal BUY máxima |
| +0.5 | Señal BUY moderada |
| 0.0 | Neutral |
| -0.5 | Señal SELL moderada |
| -1.0 | Señal SELL máxima |

### Ejemplo

```json
{
    "agent_id": "technical_v1",
    "timestamp": "2026-03-30T12:00:00Z",
    "symbol": "BTCUSDT",
    "direction": "BUY",
    "score": 0.65,
    "confidence": 0.78,
    "features_used": ["rsi_14", "macd_histogram", "ema_9", "ema_21"],
    "shap_values": {
        "rsi_14": 0.25,
        "macd_histogram": 0.18,
        "ema_9": 0.12,
        "ema_21": 0.08
    },
    "model_version": "v1.0.0"
}
```

---

## Modelo: ConsensusOutput

### Definición

```python
class ConsensusOutput(BaseModel):
    timestamp: datetime
    symbol: str
    final_direction: str           # "BUY" | "SELL" | "NEUTRAL"
    weighted_score: float          # -1.0 to +1.0
    agents_agreement: float        # 0.0 to 1.0
    blocked_by_regime: bool
    agent_outputs: list[AgentOutput]
    conflicts: list[str]
```

### Ejemplo

```json
{
    "timestamp": "2026-03-30T12:00:00Z",
    "symbol": "BTCUSDT",
    "final_direction": "BUY",
    "weighted_score": 0.52,
    "agents_agreement": 0.67,
    "blocked_by_regime": false,
    "agent_outputs": [...],
    "conflicts": []
}
```

---

## Modelo: Signal

### Definición

```python
class Signal(BaseModel):
    id: str
    idempotency_key: str
    timestamp: datetime
    symbol: str
    asset_class: str = "crypto"
    action: str                    # "BUY" | "SELL" | "HOLD"
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
```

### SignalExplanationFactor

```python
class SignalExplanationFactor(BaseModel):
    factor: str           # "RSI_14", "MACD_HISTOGRAM", etc.
    weight: float         # 0.0 to 1.0
    direction: str        # "BUY" | "SELL"
    description: str      # "RSI en sobreventa (28)"
```

### Ejemplo

```json
{
    "id": "uuid",
    "idempotency_key": "a1b2c3d4e5f6g7h8",
    "timestamp": "2026-03-30T12:00:00Z",
    "symbol": "BTCUSDT",
    "action": "BUY",
    "entry_price": 50000.0,
    "stop_loss": 49000.0,
    "take_profit": 53000.0,
    "risk_reward_ratio": 3.0,
    "confidence": 0.75,
    "explanation": [
        {
            "factor": "RSI_14",
            "weight": 0.35,
            "direction": "BUY",
            "description": "RSI en sobreventa (28)"
        },
        {
            "factor": "MACD_HISTOGRAM",
            "weight": 0.25,
            "direction": "BUY",
            "description": "MACD histogram positivo y creciente"
        }
    ],
    "summary": "Señal BUY por RSI en sobreventa + cruce alcista EMA",
    "regime": "bull_trending",
    "strategy_id": "ema_rsi_v1",
    "status": "pending"
}
```

---

## Modelo: Order

### Definición

```python
class Order(BaseModel):
    id: str
    exchange_order_id: Optional[str]
    idempotency_key: str
    signal_id: str
    symbol: str
    asset_class: str = "crypto"
    side: str                     # "BUY" | "SELL"
    order_type: str               # "MARKET" | "LIMIT"
    quantity: float
    price: Optional[float]        # Para LIMIT orders
    stop_loss: float
    take_profit: float
    status: OrderStatus
    fill_price: Optional[float]
    fill_quantity: Optional[float]
    commission: Optional[float]
    slippage: Optional[float]
    created_at: datetime
    updated_at: datetime
    execution_mode: str           # "paper" | "live"
    error_message: Optional[str]
```

### Ejemplo

```json
{
    "id": "uuid",
    "exchange_order_id": null,
    "idempotency_key": "a1b2c3d4e5f6g7h8",
    "signal_id": "signal-uuid",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "order_type": "MARKET",
    "quantity": 0.2,
    "stop_loss": 49000.0,
    "take_profit": 53000.0,
    "status": "filled",
    "fill_price": 50025.0,
    "fill_quantity": 0.2,
    "commission": 10.0,
    "slippage": 25.0,
    "created_at": "2026-03-30T12:00:00Z",
    "updated_at": "2026-03-30T12:00:01Z",
    "execution_mode": "paper"
}
```

---

## Modelo: Position

### Definición

```python
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
```

### Ejemplo

```json
{
    "symbol": "BTCUSDT",
    "asset_class": "crypto",
    "quantity": 0.2,
    "entry_price": 50000.0,
    "current_price": 52000.0,
    "unrealized_pnl": 400.0,
    "unrealized_pnl_pct": 0.04,
    "strategy_id": "ema_rsi_v1",
    "opened_at": "2026-03-30T10:00:00Z"
}
```

---

## Modelo: Portfolio

### Definición

```python
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
```

### Ejemplo

```json
{
    "id": "uuid",
    "total_capital": 10500.0,
    "available_capital": 8500.0,
    "positions": [...],
    "risk_exposure": 0.08,
    "daily_pnl": 150.0,
    "daily_pnl_pct": 0.015,
    "total_pnl": 500.0,
    "drawdown_current": 0.02,
    "drawdown_max": 0.05,
    "updated_at": "2026-03-30T12:00:00Z"
}
```

---

## Modelo: RegimeOutput

### Definición

```python
class RegimeOutput(BaseModel):
    timestamp: datetime
    symbol: str
    regime: MarketRegime
    confidence: float
    regime_duration_bars: int
    previous_regime: Optional[MarketRegime] = None
    signal_allowed: bool           # False en VOLATILE_CRASH
```

---

## Modelo: InstrumentConfig

### Definición

```python
class InstrumentConfig:
    symbol: str
    mt5_symbol: str
    asset_class: AssetClass
    pip_value: float               # USD por pip/lote
    lot_size: float                # Tamaño del contrato
    min_lots: float = 0.01
    lot_step: float = 0.01
    spread_pips: float = 0.0
    swap_long: float = 0.0
    swap_short: float = 0.0
    point: float = 0.00001
```

### Catálogo de Instrumentos

| Símbolo | Clase | Pip Value | Min Lots |
|---------|-------|-----------|----------|
| EURUSD | FOREX | $10.00 | 0.01 |
| GBPUSD | FOREX | $10.00 | 0.01 |
| USDJPY | FOREX | $9.09 | 0.01 |
| XAUUSD | COMMODITIES | $1.00 | 0.01 |
| US500 | INDICES | $1.00 | 1 |
| BTCUSD | CRYPTO | $1.00 | 1 |

---

## Helper Functions

### detect_asset_class

```python
def detect_asset_class(symbol: str) -> AssetClass:
    """
    Infieres asset class desde el símbolo:
    - Crypto: termina en USDT, USDC, BTC, ETH
    - Commodities: empieza con XAU, XAG
    - Indices: SPX500, NAS100, etc.
    - Forex: 6 chars alfanuméricos
    """
```

### get_instrument

```python
def get_instrument(symbol: str) -> Optional[InstrumentConfig]:
    """
    Retorna configuración del instrumento.
    None para crypto nativo de Binance.
    """
```

---

*Volver al [índice de modelos](README.md)*
