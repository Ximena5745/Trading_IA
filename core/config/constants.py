"""
Module: core/config/constants.py
Responsibility: Hard-coded risk limits and system constants
Dependencies: none
"""

# Hard limits — only modifiable here with code review, never via API
HARD_LIMITS = {
    "max_risk_per_trade_pct": 0.02,
    "max_portfolio_risk_pct": 0.15,
    "max_daily_loss_pct": 0.10,
    "max_drawdown_pct": 0.20,
    "max_consecutive_losses": 7,
    "min_risk_reward_ratio": 1.5,
    "max_position_single_symbol_pct": 0.30,
}

SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]

# ── Multi-asset symbol catalogue ────────────────────────────────────────────
# Symbols are grouped by asset class.
# Exchange adapters are responsible for translating these to native formats.

ASSET_CLASS_SYMBOLS: dict[str, list[str]] = {
    "crypto": [
        "BTCUSDT",   # Bitcoin
        "ETHUSDT",   # Ethereum
        "SOLUSDT",   # Solana
        "BNBUSDT",   # BNB
    ],
    "forex": [
        "EURUSD",    # Euro / US Dollar
        "GBPUSD",    # Pound / US Dollar
        "USDJPY",    # US Dollar / Japanese Yen
        "USDCHF",    # US Dollar / Swiss Franc
        "AUDUSD",    # Australian Dollar / US Dollar
        "USDCAD",    # US Dollar / Canadian Dollar
    ],
    "indices": [
        "SPX500",    # S&P 500
        "NAS100",    # Nasdaq 100
        "US30",      # Dow Jones
        "DE40",      # DAX (Germany)
        "UK100",     # FTSE 100 (UK)
        "JP225",     # Nikkei 225 (Japan)
    ],
    "commodities": [
        "XAUUSD",    # Gold / US Dollar
        "XAGUSD",    # Silver / US Dollar
        "USOIL",     # WTI Crude Oil
        "UKOIL",     # Brent Crude Oil
        "NATGAS",    # Natural Gas
        "WHEAT",     # Wheat
    ],
}

# Flat list for backward compatibility
SUPPORTED_SYMBOLS: list[str] = [
    sym for syms in ASSET_CLASS_SYMBOLS.values() for sym in syms
]

# Lookup: symbol → asset class
SYMBOL_ASSET_CLASS: dict[str, str] = {
    sym: cls
    for cls, syms in ASSET_CLASS_SYMBOLS.items()
    for sym in syms
}

# Default symbols shown in the dashboard (one per class)
DEFAULT_SYMBOLS_BY_CLASS: dict[str, str] = {
    "crypto":      "BTCUSDT",
    "forex":       "EURUSD",
    "indices":     "SPX500",
    "commodities": "XAUUSD",
}

# Minimum candles required for feature calculation
MIN_CANDLES_EMA200 = 200
MIN_CANDLES_BACKTEST = 1000

# Signal thresholds
SIGNAL_SCORE_THRESHOLD = 0.30
SIGNAL_CONSENSUS_THRESHOLD = 0.60

# ATR multipliers for stop loss / take profit
ATR_STOP_LOSS_MULTIPLIER = 2.0
ATR_TAKE_PROFIT_MULTIPLIER = 3.0

# Paper executor
PAPER_SLIPPAGE_PCT = 0.0005
PAPER_COMMISSION_PCT = 0.001
PAPER_LATENCY_MS_MIN = 50
PAPER_LATENCY_MS_MAX = 200
