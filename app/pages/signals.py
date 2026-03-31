"""
Module: app/pages/signals.py
Responsibility: Active signals with XAI explanation - Professional Trading Signals
Dependencies: streamlit, plotly, requests
"""
from __future__ import annotations

import os

import plotly.graph_objects as go
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_TOKEN = st.session_state.get("token", "")
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    .stApp { font-family: 'Inter', sans-serif; }
    h1, h2, h3 { color: #d4af37 !important; font-weight: 600; }
    h1 { font-size: 1.8rem; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #12121a 0%, #1a1a2e 100%);
        border: 1px solid #2a2a3e; border-radius: 12px; padding: 16px;
    }
    div[data-testid="stMetric"] label { color: #8888a0 !important; font-size: 0.75rem; text-transform: uppercase; }
    div[data-testid="stMetric"] div { color: #fff !important; font-weight: 700; }
    .stSelectbox > div > div { background: #12121a !important; border: 1px solid #2a2a3e; }
    .stButton > button {
        background: linear-gradient(135deg, #d4af37 0%, #b8960b 100%);
        color: #0a0a0f; border: none; border-radius: 8px; font-weight: 600;
    }
    .stAlert { background: #12121a; border-left: 4px solid #4169e1; border-radius: 8px; }
    .stExpander { background: #12121a; border: 1px solid #2a2a3e; border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Señales de Trading")

_ALL_SYMBOLS = ["Todos", "BTCUSDT", "ETHUSDT", "SOLUSDT", "EURUSD", "GBPUSD", "USDJPY", "SPX500", "NAS100", "DE40", "XAUUSD", "USOIL"]

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    symbol_filter = st.selectbox("💰 Símbolo", _ALL_SYMBOLS, label_visibility="collapsed")
with col2:
    status_filter = st.selectbox("📊 Estado", ["Todos", "pending", "executed", "cancelled"], label_visibility="collapsed")
with col3:
    limit = st.number_input("📝", 10, 200, 50, label_visibility="collapsed")

if st.button("🔄 Actualizar Señales"):
    st.cache_data.clear()

@st.cache_data(ttl=30)
def fetch_signals(symbol, sig_status, lim) -> list:
    params = {"limit": lim}
    if symbol != "Todos": params["symbol"] = symbol
    if sig_status != "Todos": params["status"] = sig_status
    try:
        resp = requests.get(f"{API_URL}/signals", params=params, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            return resp.json().get("signals", [])
    except Exception:
        pass
    return []

signals = fetch_signals(symbol_filter, status_filter, limit)

if not signals:
    st.warning("⚠️ No hay señales disponibles.")
    st.info("💡 Las señales se generan automáticamente cuando el pipeline está activo.")
    st.stop()

st.markdown(f"### 📊 {len(signals)} Señal(es) Encontrada(s)")

for sig in signals:
    action = sig.get("action", "")
    color = "🟢" if action == "BUY" else "🔴"
    conf = sig.get("confidence", 0)
    rr = sig.get("risk_reward_ratio", 0)

    with st.expander(f"{color} {action} — {sig.get('symbol')} | Conf: {conf:.0%} | R:R {rr:.1f}x"):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📥 Entrada", f"${sig.get('entry_price', 0):,.2f}")
        col2.metric("🛡️ SL", f"${sig.get('stop_loss', 0):,.2f}")
        col3.metric("🎯 TP", f"${sig.get('take_profit', 0):,.2f}")
        col4.metric("📊 Estado", sig.get("status", "—").upper())

        st.info(f"📝 **Resumen:** {sig.get('summary', '—')}")

        explanation = sig.get("explanation", [])
        if explanation:
            st.markdown("### 🔍 Análisis XAI")
            factors = sorted(explanation, key=lambda x: x.get("weight", 0), reverse=True)
            labels = [f.get("factor", "") for f in factors]
            weights = [f.get("weight", 0) if f.get("direction") == "bullish" else -f.get("weight", 0) for f in factors]
            colors = ["#d4af37" if w > 0 else "#4169e1" for w in weights]

            fig = go.Figure(go.Bar(x=weights, y=labels, orientation="h", marker_color=colors))
            fig.update_layout(title="📊 Contribución de Factores", template="plotly_dark", height=300,
                            paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f", font=dict(color="#fff"))
            st.plotly_chart(fig, use_container_width=True)

            for f in factors[:3]:
                icon = "📈" if f.get("direction") == "bullish" else "📉"
                st.markdown(f"**{icon}** {f.get('description', '')}")
