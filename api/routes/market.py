"""
Module: api/routes/market.py
Responsibility: Market data endpoints
Dependencies: require_trader, feature_store, binance_client
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import require_trader
from core.config.settings import get_settings

router = APIRouter(prefix="/market", tags=["market"])
settings = get_settings()

# In-memory store for MVP — injected via lifespan in production
_market_data_cache: dict[str, list] = {}
_features_cache: dict[str, dict] = {}
_regime_cache: dict[str, dict] = {}


@router.get("/symbols")
async def get_symbols(_: dict = Depends(require_trader)):
    return settings.SUPPORTED_SYMBOLS


@router.get("/{symbol}/data")
async def get_market_data(
    symbol: str,
    limit: int = Query(default=100, le=500),
    _: dict = Depends(require_trader),
):
    symbol = symbol.upper()
    if symbol not in settings.SUPPORTED_SYMBOLS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Symbol {symbol} not supported")
    data = _market_data_cache.get(symbol, [])
    return {"symbol": symbol, "count": len(data), "data": data[-limit:]}


@router.get("/{symbol}/features")
async def get_features(
    symbol: str,
    _: dict = Depends(require_trader),
):
    symbol = symbol.upper()
    if symbol not in settings.SUPPORTED_SYMBOLS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Symbol {symbol} not supported")
    features = _features_cache.get(symbol)
    if not features:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No features available yet")
    return features


@router.get("/{symbol}/regime")
async def get_regime(
    symbol: str,
    _: dict = Depends(require_trader),
):
    symbol = symbol.upper()
    regime = _regime_cache.get(symbol)
    if not regime:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No regime data available yet")
    return regime


def update_market_data_cache(symbol: str, data: list) -> None:
    _market_data_cache[symbol] = data


def update_features_cache(symbol: str, features: dict) -> None:
    _features_cache[symbol] = features


def update_regime_cache(symbol: str, regime: dict) -> None:
    _regime_cache[symbol] = regime
