"""
Module: app/pages/simulator.py
Responsibility: Professional Historical Simulator - What-If Analysis
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_TOKEN = st.session_state.get("token", "")

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
    .stSelectbox > div > div, .stTextInput > div > div { background: #12121a !important; border: 1px solid #2a2a3e; }
    .stButton > button {
        background: linear-gradient(135deg, #d4af37 0%, #b8960b 100%);
        color: #0a0a0f; border: none; border-radius: 8px; font-weight: 600;
    }
    .stAlert { background: #12121a; border-left: 4px solid #4169e1; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.title("🎮 Simulador")

def _get_headers() -> dict:
    return {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}

def _fetch_strategies() -> list[dict]:
    try:
        r = requests.get(f"{API_URL}/strategies", headers=_get_headers(), timeout=5)
        if r.status_code == 200:
            return r.json().get("strategies", [])
    except Exception:
        pass
    return []

def _fetch_symbols() -> list[str]:
    try:
        r = requests.get(f"{API_URL}/market/symbols", headers=_get_headers(), timeout=5)
        if r.status_code == 200:
            return r.json().get("symbols", [])
    except Exception:
        pass
    return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "USOIL"]

strategies = _fetch_strategies()
symbols = _fetch_symbols()

col1, col2 = st.columns(2)
with col1:
    selected_strategy = st.selectbox("🧠 Estrategia", 
                                      [s.get("strategy_id", s.get("id")) for s in strategies] if strategies else ["ema_rsi_v1"])
with col2:
    selected_symbol = st.selectbox("💰 Símbolo", symbols[:8] if symbols else ["BTCUSDT"])

col3, col4 = st.columns(2)
with col3:
    start_date = st.date_input("📅 Desde", datetime.now() - timedelta(days=90))
with col4:
    end_date = st.date_input("📅 Hasta", datetime.now())

initial_capital = st.number_input("💵 Capital", value=10000.0, step=1000.0)

if st.button("▶️ Ejecutar Simulación"):
    payload = {"strategy_id": selected_strategy, "symbol": selected_symbol,
               "from_ts": start_date.isoformat(), "to_ts": end_date.isoformat(), "initial_capital": initial_capital}
    try:
        resp = requests.post(f"{API_URL}/simulation/run", json=payload, headers=_get_headers(), timeout=30)
        if resp.status_code == 200:
            results = resp.json()
            st.markdown("### 📊 Resultados")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💰 Final", f"${results.get('final_capital', 0):,.2f}")
            col2.metric("📈 Retorno", f"{results.get('return_pct', 0):.2f}%")
            col3.metric("🎯 Win Rate", f"{results.get('win_rate', 0):.1%}")
            col4.metric("🔢 Trades", results.get("total_trades", 0))
            
            if "equity_curve" in results:
                df = pd.DataFrame(results["equity_curve"])
                if not df.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df.get("timestamp", df.index), y=df.get("capital", df.iloc[:, 0]),
                                            mode="lines", name="Capital", line=dict(color="#d4af37", width=2),
                                            fill="tozeroy", fillcolor="rgba(212,175,55,0.1)"))
                    fig.update_layout(title="📈 Curva de Capital", template="plotly_dark", height=400,
                                    paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f", font=dict(color="#fff"))
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"Error: {resp.text}")
    except Exception as e:
        st.error(f"⚠️ {e}")

st.info("💡 Analiza qué habría pasado con diferentes estrategias en el pasado.")
