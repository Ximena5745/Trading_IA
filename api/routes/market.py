"""
Module: api/routes/market.py
Responsibility: Market data endpoints (public read-only GET)
Dependencies: feature_store, binance_client
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from core.config.settings import get_settings

router = APIRouter(prefix="/market", tags=["market"])
settings = get_settings()

# In-memory store: {symbol: {timeframe: [records]}}
_market_data_cache: dict[str, dict[str, list]] = {}
_features_cache: dict[str, dict] = {}
_regime_cache: dict[str, dict] = {}


@router.get("/symbols")
async def get_symbols():
    return settings.SUPPORTED_SYMBOLS


@router.get("/{symbol}/data")
async def get_market_data(
    symbol: str,
    timeframe: str = Query(default="1wk", pattern="^(1d|1h|4h|1wk|1mo|6mo)$"),
    limit: int = Query(default=100, le=20000),  # Increased from 500 to 20000 to allow large datasets
):
    try:
        symbol = symbol.upper()
        if symbol not in settings.SUPPORTED_SYMBOLS:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "count": 0,
                "data": [],
                "error": f"Symbol {symbol} not supported"
            }
        tf_data = _market_data_cache.get(symbol, {})
        data = tf_data.get(timeframe, [])
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "count": len(data),
            "data": data[-limit:] if data else [],
        }
    except Exception as e:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "count": 0,
            "data": [],
            "error": str(e)
        }


@router.get("/{symbol}/features")
async def get_features(
    symbol: str,
):
    try:
        symbol = symbol.upper()
        if symbol not in settings.SUPPORTED_SYMBOLS:
            return {
                "symbol": symbol,
                "error": f"Symbol {symbol} not supported",
                "rsi_14": 50, "rsi_7": 50, "macd_line": 0, "macd_signal": 0,
                "macd_histogram": 0, "bb_upper": 0, "bb_lower": 0, "bb_width": 0,
                "atr_14": 0, "volume_ratio": 1, "technical_score": 0.5,
                "regime_score": 0.5, "micro_score": 0.5, "regime": "SIDEWAYS",
                "fundamental_status": "UNKNOWN", "consensus_score": 0.5
            }
        features = _features_cache.get(symbol)
        if not features:
            return {
                "symbol": symbol,
                "rsi_14": 50, "rsi_7": 50, "macd_line": 0, "macd_signal": 0,
                "macd_histogram": 0, "bb_upper": 0, "bb_lower": 0, "bb_width": 0,
                "atr_14": 0, "volume_ratio": 1, "technical_score": 0.5,
                "regime_score": 0.5, "micro_score": 0.5, "regime": "SIDEWAYS",
                "fundamental_status": "CLEAR", "consensus_score": 0.5
            }
        return features
    except Exception as e:
        return {
            "symbol": symbol,
            "error": str(e),
            "rsi_14": 50, "rsi_7": 50, "macd_line": 0, "macd_signal": 0,
            "macd_histogram": 0, "bb_upper": 0, "bb_lower": 0, "bb_width": 0,
            "atr_14": 0, "volume_ratio": 1, "technical_score": 0.5,
            "regime_score": 0.5, "micro_score": 0.5, "regime": "SIDEWAYS",
            "fundamental_status": "CLEAR", "consensus_score": 0.5
        }


_MTF_TIMEFRAMES = ("1h", "4h", "1d")


def _trend_from_record(rec: dict) -> dict:
    """Derive a trend read from a cached candle record.

    Indicator columns (trend_score/trend_direction/rsi_14/...) are precomputed by
    core.features.indicators.calculate_all at ingestion; when they are missing we
    fall back to a close/EMA comparison so the panel still says something useful.
    """
    close = rec.get("close")
    ema_50 = rec.get("ema_50")
    ema_200 = rec.get("ema_200")
    score = rec.get("trend_score")
    direction = rec.get("trend_direction")

    if score is None and None not in (close, ema_50, ema_200):
        score = (0.5 if ema_50 > ema_200 else -0.5) + (0.5 if close > ema_50 else -0.5)

    if direction is None:
        if score is None:
            direction = "unknown"
        elif score > 0.3:
            direction = "bullish"
        elif score < -0.3:
            direction = "bearish"
        else:
            direction = "sideways"

    return {
        "direction": direction,
        "trend_score": round(float(score), 3) if score is not None else None,
        "rsi_14": rec.get("rsi_14"),
        "macd_histogram": rec.get("macd_histogram"),
        "close": close,
        "timestamp": rec.get("timestamp"),
    }


@router.get("/{symbol}/mtf-alignment")
async def get_mtf_alignment(symbol: str):
    """Multi-timeframe trend alignment (1h / 4h / 1d) for a symbol.

    Reads the latest cached candle on each timeframe and reports the trend
    direction there, plus whether the timeframes agree. Timeframes without cached
    data come back as direction "unknown" — the dashboard shows those explicitly
    rather than guessing. The cache is populated from data/raw/parquet/<tf>/ at
    startup, so 1h/4h/1d are available for the symbols shipped with parquet data.
    """
    symbol = symbol.upper()
    tf_data = _market_data_cache.get(symbol, {})

    per_tf: dict[str, dict] = {}
    for tf in _MTF_TIMEFRAMES:
        candles = tf_data.get(tf) or []
        if candles:
            per_tf[tf] = _trend_from_record(candles[-1])
        else:
            per_tf[tf] = {
                "direction": "unknown", "trend_score": None, "rsi_14": None,
                "macd_histogram": None, "close": None, "timestamp": None,
            }

    known = [r["direction"] for r in per_tf.values() if r["direction"] != "unknown"]
    bull = known.count("bullish")
    bear = known.count("bearish")

    if not known:
        alignment = "no_data"
        score = 0.0
    elif bull == len(known):
        alignment = "aligned_bullish"
        score = 1.0
    elif bear == len(known):
        alignment = "aligned_bearish"
        score = -1.0
    else:
        alignment = "mixed"
        score = (bull - bear) / len(known)

    return {
        "symbol": symbol,
        "timeframes": per_tf,
        "alignment": alignment,
        "alignment_score": round(score, 3),
        "available_timeframes": [tf for tf in _MTF_TIMEFRAMES if tf_data.get(tf)],
    }


@router.get("/{symbol}/support-resistance")
async def get_support_resistance(
    symbol: str,
    timeframe: str = Query(default="1d", pattern="^(1d|1h|4h|1wk|1mo|6mo)$"),
    lookback: int = Query(default=300, ge=50, le=2000),
    pivot_window: int = Query(default=3, ge=2, le=10),
    max_levels: int = Query(default=8, ge=1, le=20),
):
    """Algorithmic support/resistance from swing pivots on cached candles.

    A swing high/low is a candle whose high/low is the extreme within
    ±pivot_window bars. Pivot prices are clustered (tolerance ~0.4% of the last
    close); each cluster becomes a level with a `touches` count (strength). Levels
    are tagged support/resistance relative to the last close. Fully functional
    from the market-data cache — returns `levels: []` when the symbol/timeframe
    has no cached candles.
    """
    symbol = symbol.upper()
    candles = (_market_data_cache.get(symbol, {}) or {}).get(timeframe) or []
    candles = candles[-lookback:]
    if len(candles) < 2 * pivot_window + 5:
        return {"symbol": symbol, "timeframe": timeframe, "levels": [],
                "available_candles": len(candles)}

    highs = [c.get("high") for c in candles]
    lows = [c.get("low") for c in candles]
    closes = [c.get("close") for c in candles]
    last_close = next((c for c in reversed(closes) if c is not None), None)
    if last_close is None or last_close <= 0:
        return {"symbol": symbol, "timeframe": timeframe, "levels": []}

    w = pivot_window
    pivots: list[float] = []
    for i in range(w, len(candles) - w):
        hi, lo = highs[i], lows[i]
        if hi is not None and hi == max(h for h in highs[i - w:i + w + 1] if h is not None):
            pivots.append(hi)
        if lo is not None and lo == min(l for l in lows[i - w:i + w + 1] if l is not None):
            pivots.append(lo)

    if not pivots:
        return {"symbol": symbol, "timeframe": timeframe, "levels": []}

    tol = last_close * 0.004
    pivots.sort()
    clusters: list[list[float]] = [[pivots[0]]]
    for p in pivots[1:]:
        if p - clusters[-1][-1] <= tol:
            clusters[-1].append(p)
        else:
            clusters.append([p])

    levels = []
    for cl in clusters:
        price = sum(cl) / len(cl)
        levels.append({
            "price": round(price, 6),
            "touches": len(cl),
            "kind": "resistance" if price >= last_close else "support",
            "distance_pct": round((price - last_close) / last_close * 100, 3),
        })
    levels.sort(key=lambda x: (-x["touches"], abs(x["distance_pct"])))
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "last_close": round(last_close, 6),
        "levels": levels[:max_levels],
    }


@router.get("/{symbol}/regime")
async def get_regime(
    symbol: str,
):
    symbol = symbol.upper()
    regime = _regime_cache.get(symbol)
    if not regime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No regime data available yet"
        )
    return regime


def get_market_data_cache(symbol: str, timeframe: str = "1wk") -> list:
    """Latest cached candles for WebSocket streaming."""
    symbol = symbol.upper()
    tf_data = _market_data_cache.get(symbol, {})
    return tf_data.get(timeframe, [])


def update_market_data_cache(symbol: str, data: list, timeframe: str = "1wk") -> None:
    if symbol not in _market_data_cache:
        _market_data_cache[symbol] = {}
    _market_data_cache[symbol][timeframe] = data


def update_features_cache(symbol: str, features: dict) -> None:
    _features_cache[symbol] = features


def update_regime_cache(symbol: str, regime: dict) -> None:
    _regime_cache[symbol] = regime
