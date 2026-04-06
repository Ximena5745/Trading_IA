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
    limit: int = Query(default=100, le=500),
):
    symbol = symbol.upper()
    if symbol not in settings.SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symbol {symbol} not supported",
        )
    tf_data = _market_data_cache.get(symbol, {})
    data = tf_data.get(timeframe, [])
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(data),
        "data": data[-limit:],
    }


@router.get("/{symbol}/features")
async def get_features(
    symbol: str,
):
    symbol = symbol.upper()
    if symbol not in settings.SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symbol {symbol} not supported",
        )
    features = _features_cache.get(symbol)
    if not features:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No features available yet"
        )
    return features


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


def update_market_data_cache(symbol: str, data: list, timeframe: str = "1wk") -> None:
    if symbol not in _market_data_cache:
        _market_data_cache[symbol] = {}
    _market_data_cache[symbol][timeframe] = data


def update_features_cache(symbol: str, features: dict) -> None:
    _features_cache[symbol] = features


def update_regime_cache(symbol: str, regime: dict) -> None:
    _regime_cache[symbol] = regime
