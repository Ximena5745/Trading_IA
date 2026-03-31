"""
Module: app/pages/market_view.py
Responsibility: Real-time OHLCV chart + indicators - Professional Trading View
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

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .stApp { font-family: 'Inter', sans-serif; }
    h1, h2, h3, h4 { color: #d4af37 !important; font-weight: 600; }
    h1 { font-size: 1.8rem; }
    
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #12121a 0%, #1a1a2e 100%);
        border: 1px solid #2a2a3e;
        border-radius: 12px;
        padding: 16px;
    }
    div[data-testid="stMetric"] label { color: #8888a0 !important; font-size: 0.75rem; text-transform: uppercase; }
    div[data-testid="stMetric"] div { color: #fff !important; font-weight: 700; }
    
    .stSelectbox > div > div { background: #12121a !important; border: 1px solid #2a2a3e; }
    
    .stButton > button {
        background: linear-gradient(135deg, #d4af37 0%, #b8960b 100%);
        color: #0a0a0f; border: none; border-radius: 8px; font-weight: 600;
    }
    .stButton > button:hover { background: linear-gradient(135deg, #ffd700, #d4af37); }
    
    .stAlert { background: #12121a; border-left: 4px solid #4169e1; border-radius: 8px; }
    
    div[data-testid="stExpander"] {
        background: #12121a; border: 1px solid #2a2a3e; border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Vista de Mercado")

_SYMBOLS_BY_CLASS = {
    "💎 Crypto": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"],
    "💱 Forex": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD"],
    "📈 Índices": ["SPX500", "NAS100", "US30", "DE40", "UK100"],
    "🥇 Materias Primas": ["XAUUSD", "XAGUSD", "USOIL", "NATGAS"],
}

col0, col1, col2, col3 = st.columns([2, 2, 2, 1])
with col0:
    asset_class = st.selectbox("📁 Activo", list(_SYMBOLS_BY_CLASS.keys()), label_visibility="collapsed")
with col1:
    symbol = st.selectbox("💰 Símbolo", _SYMBOLS_BY_CLASS[asset_class], label_visibility="collapsed")
with col2:
    timeframe = st.selectbox("⏱️ TF", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3, label_visibility="collapsed")
with col3:
    limit = st.number_input("🔢", min_value=50, max_value=500, value=200, label_visibility="collapsed")

col_btn, = st.columns([1])
with col_btn:
    if st.button("🔄 Actualizar", use_container_width=True):
        st.rerun()


@st.cache_data(ttl=60)
def fetch_market_data(symbol: str, limit: int) -> pd.DataFrame:
    try:
        resp = requests.get(f"{API_URL}/market/{symbol}/data", params={"limit": limit}, 
                          headers={"Authorization": f"Bearer {API_TOKEN}"}, timeout=5)
        if resp.status_code == 200:
            return pd.DataFrame(resp.json().get("data", []))
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(ttl=60)
def fetch_features(symbol: str) -> dict:
    try:
        resp = requests.get(f"{API_URL}/market/{symbol}/features", 
                          headers={"Authorization": f"Bearer {API_TOKEN}"}, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


df = fetch_market_data(symbol, limit)
features = fetch_features(symbol)

if df.empty:
    st.warning("⚠️ Sin datos. Verifica que la API esté corriendo.")
    st.info("💡 Hint: Deploya la API y configura API_URL en Streamlit Cloud")
    st.stop()

fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, 
                    row_heights=[0.6, 0.2, 0.2], subplot_titles=(f"📈 {symbol}", "📊 Volumen", "📉 RSI"))

fig.add_trace(go.Candlestick(x=df["timestamp"], open=df["open"], high=df["high"], 
                           low=df["low"], close=df["close"], name="OHLCV",
                           increasing_line_color="#d4af37", decreasing_line_color="#4169e1"), row=1, col=1)

for ema, color in [("ema_9", "#ffd700"), ("ema_21", "#ff8c00"), ("ema_50", "#1e90ff"), ("ema_200", "#ff4500")]:
    if ema in df.columns:
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df[ema], name=ema.upper(), 
                               line=dict(color=color, width=1.5)), row=1, col=1)

colors = ["#26a69a" if c >= o else "#ef5350" for c, o in zip(df["close"], df["open"])]
fig.add_trace(go.Bar(x=df["timestamp"], y=df["volume"], name="Volume", marker_color=colors), row=2, col=1)

if "rsi_14" in df.columns:
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["rsi_14"], name="RSI", line=dict(color="#9b59b6", width=2)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#ff4444", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#44ff44", row=3, col=1)

fig.update_layout(height=700, template="plotly_dark", paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f",
                 font=dict(color="#fff"), showlegend=True, xaxis_rangeslider_visible=False,
                 legend=dict(orientation="h", y=1.02, x=1))
st.plotly_chart(fig, use_container_width=True)

if features:
    st.markdown("### 📐 Indicadores Técnicos")
    cols = st.columns(4)
    metrics = [("RSI 14", f"{features.get('rsi_14', 0):.1f}"), ("RSI 7", f"{features.get('rsi_7', 0):.1f}"),
               ("MACD", f"{features.get('macd_line', 0):.4f}"), ("ATR", f"{features.get('atr_14', 0):.2f}"),
               ("BB Width", f"{features.get('bb_width', 0):.4f}"), ("Vol Ratio", f"{features.get('volume_ratio', 0):.2f}x"),
               ("Trend", features.get("trend_direction", "—")), ("Volatility", features.get("volatility_regime", "—"))]
    for i, (label, val) in enumerate(metrics):
        cols[i % 4].metric(label, val)
