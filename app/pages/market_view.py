"""
Module: app/pages/market_view.py
Responsibility: Real-time OHLCV chart + indicators
Dependencies: streamlit, plotly, requests
"""
from __future__ import annotations

import os

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_TOKEN = st.session_state.get("token", "")

st.title("📊 Market View")

# --- Asset class & symbol selector ---
_SYMBOLS_BY_CLASS = {
    "Crypto": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"],
    "Forex": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"],
    "Indices": ["SPX500", "NAS100", "US30", "DE40", "UK100", "JP225"],
    "Commodities": ["XAUUSD", "XAGUSD", "USOIL", "UKOIL", "NATGAS"],
}

col0, col1, col2, col3 = st.columns([2, 2, 2, 1])
with col0:
    asset_class = st.selectbox("Asset Class", list(_SYMBOLS_BY_CLASS.keys()))
with col1:
    symbol = st.selectbox("Symbol", _SYMBOLS_BY_CLASS[asset_class])
with col2:
    timeframe = st.selectbox(
        "Timeframe", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3
    )
with col3:
    limit = st.number_input("Candles", min_value=50, max_value=500, value=200)

if st.button("🔄 Refresh", use_container_width=True):
    st.rerun()


# --- Fetch data from API ---
@st.cache_data(ttl=60)
def fetch_market_data(symbol: str, limit: int) -> pd.DataFrame:
    try:
        resp = requests.get(
            f"{API_URL}/market/{symbol}/data",
            params={"limit": limit},
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            return pd.DataFrame(data)
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(ttl=60)
def fetch_features(symbol: str) -> dict:
    try:
        resp = requests.get(
            f"{API_URL}/market/{symbol}/features",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


df = fetch_market_data(symbol, limit)
features = fetch_features(symbol)

if df.empty:
    st.warning(
        "No market data available. Make sure the API is running and the ingestion pipeline is active."
    )
    st.stop()

# --- OHLCV Candlestick Chart ---
fig = make_subplots(
    rows=3,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.6, 0.2, 0.2],
    subplot_titles=(f"{symbol} OHLCV", "Volume", "RSI"),
)

fig.add_trace(
    go.Candlestick(
        x=df["timestamp"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="OHLCV",
    ),
    row=1,
    col=1,
)

# EMA lines
for ema, color in [
    ("ema_9", "#FFD700"),
    ("ema_21", "#FF8C00"),
    ("ema_50", "#1E90FF"),
    ("ema_200", "#FF4500"),
]:
    if ema in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df[ema],
                name=ema.upper(),
                line=dict(color=color, width=1),
            ),
            row=1,
            col=1,
        )

# Volume
colors = ["#26a69a" if c >= o else "#ef5350" for c, o in zip(df["close"], df["open"])]
fig.add_trace(
    go.Bar(x=df["timestamp"], y=df["volume"], name="Volume", marker_color=colors),
    row=2,
    col=1,
)

# RSI
if "rsi_14" in df.columns:
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"], y=df["rsi_14"], name="RSI 14", line=dict(color="#9B59B6")
        ),
        row=3,
        col=1,
    )
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

fig.update_layout(
    height=700,
    xaxis_rangeslider_visible=False,
    template="plotly_dark",
    showlegend=True,
)
st.plotly_chart(fig, use_container_width=True)

# --- Features Panel ---
if features:
    st.subheader("📐 Latest Features")
    cols = st.columns(4)
    metrics = [
        ("RSI 14", f"{features.get('rsi_14', 0):.1f}"),
        ("RSI 7", f"{features.get('rsi_7', 0):.1f}"),
        ("MACD", f"{features.get('macd_line', 0):.4f}"),
        ("ATR 14", f"{features.get('atr_14', 0):.2f}"),
        ("BB Width", f"{features.get('bb_width', 0):.4f}"),
        ("Volume Ratio", f"{features.get('volume_ratio', 0):.2f}x"),
        ("Trend", features.get("trend_direction", "—")),
        ("Volatility", features.get("volatility_regime", "—")),
    ]
    for i, (label, val) in enumerate(metrics):
        cols[i % 4].metric(label, val)
