"""
Module: core/models/asset_specific_models/features.py
Responsibility: Feature-set configuration per asset class
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FeatureConfig:
    """Configuración de features específica por activo."""

    # Features técnicas base
    technical_indicators: list[str] = field(default_factory=list)

    # Features de tiempo (críticas para Forex)
    time_features: list[str] = field(default_factory=list)

    # Features de mercado/estructura
    market_structure: list[str] = field(default_factory=list)

    # Features de volatilidad
    volatility_features: list[str] = field(default_factory=list)

    # Features de retornos
    return_features: list[str] = field(default_factory=list)

    # Features de microestructura
    microstructure: list[str] = field(default_factory=list)

    # Features macro (para commodities)
    macro_features: list[str] = field(default_factory=list)

    # Features específicas del activo
    asset_specific: list[str] = field(default_factory=list)

    @property
    def all_features(self) -> list[str]:
        """Retorna todas las features combinadas."""
        return (
            self.technical_indicators +
            self.time_features +
            self.market_structure +
            self.volatility_features +
            self.return_features +
            self.microstructure +
            self.macro_features +
            self.asset_specific
        )


# Configuraciones específicas por tipo de activo
CRYPTO_FEATURES = FeatureConfig(
    technical_indicators=[
        "rsi_14", "rsi_7", "rsi_21",
        "ema_9", "ema_21", "ema_50", "ema_200",
        "macd_line", "macd_signal", "macd_histogram",
        "bb_upper", "bb_lower", "bb_width", "bb_percent_b",
        "atr_14", "atr_21",
        "vwap", "vwap_std",
        "volume_sma_20", "volume_ratio", "obv", "volume_ema",
    ],
    time_features=[
        "hour", "day_of_week", "is_weekend",
    ],
    market_structure=[
        "higher_highs", "lower_lows", "swing_high", "swing_low",
        "break_of_structure", "order_blocks",
    ],
    volatility_features=[
        "atr_percentile", "volatility_regime", "volatility_zscore",
        "bollinger_squeeze", "keltner_width",
    ],
    return_features=[
        "ret_1", "ret_3", "ret_6", "ret_12", "ret_24",
        "ret_1_vol_adj", "ret_3_vol_adj",
    ],
    microstructure=[
        "bid_ask_spread", "order_book_imbalance", "volume_delta",
        "liquidity_gaps", "bid_ask_pressure", "trade_flow_imbalance",
    ],
    asset_specific=[
        "btc_dominance", "eth_btc_ratio", "funding_rate",
        "open_interest", "liquidations", "exchange_inflows",
    ],
)

FOREX_FEATURES = FeatureConfig(
    technical_indicators=[
        "rsi_14", "rsi_7",
        "ema_9", "ema_21", "ema_50", "ema_200",
        "macd_line", "macd_signal", "macd_histogram",
        "bb_upper", "bb_lower", "bb_width",
        "atr_14", "atr_7",
        "vwap", "vwap_daily",
        "pivot_points", "pivot_support", "pivot_resistance",
    ],
    time_features=[
        "hour", "minute",
        "is_london_session", "is_ny_session", "is_asian_session",
        "session_overlap", "day_of_week", "is_nfp_day",
        "is_fomc_week", "month", "quarter_end",
    ],
    market_structure=[
        "higher_highs", "lower_lows", "swing_points",
        "support_level", "resistance_level", "break_of_structure",
    ],
    volatility_features=[
        "atr_percentile", "volatility_regime", "session_volatility",
        "daily_range", "range_percentile",
    ],
    return_features=[
        "ret_1", "ret_4", "ret_8", "ret_12", "ret_24",
        "session_return", "overnight_return",
    ],
    microstructure=[
        "bid_ask_spread", "spread_percentile", "tick_volume",
    ],
    macro_features=[
        "dxy_index", "vix_index", "yield_spread_10y_2y",
    ],
)

INDICES_FEATURES = FeatureConfig(
    technical_indicators=[
        "rsi_14", "rsi_21",
        "ema_9", "ema_21", "ema_50", "ema_200",
        "sma_50", "sma_200",
        "macd_line", "macd_signal", "macd_histogram",
        "bb_upper", "bb_lower", "bb_width",
        "atr_14", "atr_21",
        "adx", "adx_plus_di", "adx_minus_di",
        "vwap", "vwap_monthly",
    ],
    time_features=[
        "hour", "day_of_week", "is_month_start", "is_month_end",
        "quarter", "days_to_expiry", "is_opm_week",
    ],
    market_structure=[
        "higher_highs", "lower_lows", "trend_strength",
        "ema_cross_9_21", "ema_cross_50_200", "golden_cross", "death_cross",
    ],
    volatility_features=[
        "atr_percentile", "vix_level", "vix_regime",
        "volatility_contraction", "volatility_expansion",
    ],
    return_features=[
        "ret_1", "ret_3", "ret_6", "ret_12", "ret_24", "ret_48",
        "gap", "gap_filled",
    ],
    macro_features=[
        "vix_index", "dxy_index", "ten_year_yield",
        "credit_spread", "advance_decline_line",
    ],
)

COMMODITIES_FEATURES = FeatureConfig(
    technical_indicators=[
        "rsi_14", "rsi_21", "rsi_50",
        "ema_9", "ema_21", "ema_50", "ema_200",
        "macd_line", "macd_signal", "macd_histogram",
        "bb_upper", "bb_lower", "bb_width", "bb_squeeze",
        "atr_14", "atr_21", "atr_50",
        "vwap", "vwap_weekly",
    ],
    time_features=[
        "hour", "day_of_week", "month", "season",
    ],
    market_structure=[
        "higher_highs", "lower_lows", "break_of_structure",
        "key_levels", "support_zones", "resistance_zones",
    ],
    volatility_features=[
        "atr_percentile", "volatility_regime", "volatility_breakout",
        "bollinger_bandwidth", "keltner_channels",
    ],
    return_features=[
        "ret_1", "ret_3", "ret_6", "ret_12", "ret_24",
        "intraday_range", "range_expansion",
    ],
    macro_features=[
        "dxy_index", "real_yield", "inflation_expectations",
        "gold_futures_oi", "etf_flows", "central_bank_activity",
        "geopolitical_risk_index",
    ],
    asset_specific=[
        "gold_silver_ratio", "gold_dxy_correlation",
    ],
)
