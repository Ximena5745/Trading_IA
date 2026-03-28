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

SUPPORTED_SYMBOLS = ["BTCUSDT", "ETHUSDT"]

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
