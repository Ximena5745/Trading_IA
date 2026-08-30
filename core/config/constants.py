"""
Module: core/config/constants.py
Responsibility: Hard-coded risk limits and system constants
Dependencies: stdlib only (pathlib)
"""
from pathlib import Path

# Hard limits — only modifiable here with code review, never via API
HARD_LIMITS = {
    "max_risk_per_trade_pct": 0.02,
    "max_portfolio_risk_pct": 0.15,
    "max_daily_loss_pct": 0.10,
    "max_drawdown_pct": 0.20,
    "max_consecutive_losses": 7,
    "min_risk_reward_ratio": 1.5,
    "max_position_single_symbol_pct": 0.20,
}

SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]

# ── Multi-asset symbol catalogue ────────────────────────────────────────────
# Symbols are grouped by asset class.
# Exchange adapters are responsible for translating these to native formats.

ASSET_CLASS_SYMBOLS: dict[str, list[str]] = {
    "crypto": [
        "BTCUSDT",  # Bitcoin
        "ETHUSDT",  # Ethereum
        "SOLUSDT",  # Solana
        "BNBUSDT",  # BNB
    ],
    "forex": [
        "EURUSD",  # Euro / US Dollar
        "GBPUSD",  # Pound / US Dollar
        "USDJPY",  # US Dollar / Japanese Yen
        "USDCHF",  # US Dollar / Swiss Franc
        "AUDUSD",  # Australian Dollar / US Dollar
        "USDCAD",  # US Dollar / Canadian Dollar
    ],
    "indices": [
        "US500",  # S&P 500  (canonical nomenclature — ADR-004; was "SPX500")
        "NAS100",  # Nasdaq 100
        "US30",  # Dow Jones
        "DE40",  # DAX (Germany)
        "UK100",  # FTSE 100 (UK)
        "JP225",  # Nikkei 225 (Japan)
    ],
    "commodities": [
        "XAUUSD",  # Gold / US Dollar
        "XAGUSD",  # Silver / US Dollar
        "USOIL",  # WTI Crude Oil
        "UKOIL",  # Brent Crude Oil
        "NATGAS",  # Natural Gas
        "WHEAT",  # Wheat
    ],
}

# Flat catalogue of every known symbol (the *reference* universe). This is NOT
# what the system trades — see TRADED_UNIVERSE below.
SUPPORTED_SYMBOLS: list[str] = [
    sym for syms in ASSET_CLASS_SYMBOLS.values() for sym in syms
]

# Lookup: symbol → asset class
SYMBOL_ASSET_CLASS: dict[str, str] = {
    sym: cls for cls, syms in ASSET_CLASS_SYMBOLS.items() for sym in syms
}

# Default symbols shown in the dashboard (one per class)
DEFAULT_SYMBOLS_BY_CLASS: dict[str, str] = {
    "crypto": "BTCUSDT",
    "forex": "EURUSD",
    "indices": "US500",
    "commodities": "XAUUSD",
}

# ── TRADED_UNIVERSE — the single source of truth (ADR-004, SPEC-B03) ─────────
# The only symbols the system may evaluate and trade. `settings.SUPPORTED_SYMBOLS`,
# `scripts/run_pipeline.SCHEDULE` and `i1_gate_validator.PIPELINE_SYMBOLS` all
# derive from this list — do not redefine a symbol set anywhere else.
# A symbol only actually trades once it has an approved data/models/i1_params/
# <symbol>.json (ADR-003, fail-safe quant).
TRADED_UNIVERSE: list[str] = [
    "BTCUSDT",
    "ETHUSDT",
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "US500",
    "US30",
    "XAUUSD",
]

# Canonical symbol → native broker symbol. Exchange adapters translate ONLY
# through this map (no per-exchange if/elif elsewhere).
BROKER_SYMBOL_MAP: dict[str, dict[str, str]] = {
    "BTCUSDT": {"binance": "BTCUSDT"},
    "ETHUSDT": {"binance": "ETHUSDT"},
    "EURUSD": {"mt5": "EURUSD"},
    "GBPUSD": {"mt5": "GBPUSD"},
    "USDJPY": {"mt5": "USDJPY"},
    "US500": {"mt5": "US500"},
    "US30": {"mt5": "US30"},
    "XAUUSD": {"mt5": "XAUUSD"},
}

# ── Data availability ──────────────────────────────────────────────────────────
RAW_DATA_1H_DIR = Path("data/raw/parquet/1h")


def has_raw_data(symbol: str) -> bool:
    """True if a 1h parquet exists for `symbol` under data/raw/."""
    return (RAW_DATA_1H_DIR / f"{symbol.lower()}_1h.parquet").exists()


def has_market_data(symbol: str) -> bool:
    """True if the pipeline has a usable data source for `symbol`.

    Crypto streams live from Binance (always available); everything else needs a
    historical 1h parquet in data/raw/. Symbols failing this are skipped by the
    pipeline with an explicit log (SPEC-B03).
    """
    if SYMBOL_ASSET_CLASS.get(symbol) == "crypto":
        return True
    return has_raw_data(symbol)


def data_available_map() -> dict[str, bool]:
    """{symbol: data_available} over the traded universe."""
    return {sym: has_market_data(sym) for sym in TRADED_UNIVERSE}

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
