"""
Module: app/pages/signals.py
Responsibility: Active signals with XAI explanation visualization
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

st.title("⚡ Signals — Señales con Explicación XAI")

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    symbol_filter = st.selectbox("Símbolo", ["Todos", "BTCUSDT", "ETHUSDT"])
with col2:
    status_filter = st.selectbox("Estado", ["Todos", "pending", "executed", "cancelled"])
with col3:
    limit = st.number_input("Límite", 10, 200, 50)

if st.button("🔄 Actualizar"):
    st.cache_data.clear()


@st.cache_data(ttl=30)
def fetch_signals(symbol, sig_status, lim) -> list:
    params = {"limit": lim}
    if symbol != "Todos":
        params["symbol"] = symbol
    if sig_status != "Todos":
        params["status"] = sig_status
    try:
        resp = requests.get(f"{API_URL}/signals", params=params, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            return resp.json().get("signals", [])
    except Exception:
        pass
    return []


signals = fetch_signals(symbol_filter, status_filter, limit)

if not signals:
    st.info("No hay señales disponibles. El pipeline de señales se activará cuando haya datos.")
    st.stop()

st.markdown(f"**{len(signals)} señal(es) encontrada(s)**")

for sig in signals:
    action = sig.get("action", "")
    color = "🟢" if action == "BUY" else "🔴"
    conf = sig.get("confidence", 0)
    rr = sig.get("risk_reward_ratio", 0)

    with st.expander(
        f"{color} {action} — {sig.get('symbol')} | Confianza: {conf:.0%} | R:R {rr:.1f}x | {sig.get('timestamp', '')[:16]}"
    ):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Entrada", f"${sig.get('entry_price', 0):,.2f}")
        col2.metric("Stop Loss", f"${sig.get('stop_loss', 0):,.2f}")
        col3.metric("Take Profit", f"${sig.get('take_profit', 0):,.2f}")
        col4.metric("Estado", sig.get("status", "—").upper())

        # Summary
        st.info(f"📝 {sig.get('summary', '—')}")

        # XAI: SHAP bar chart
        explanation = sig.get("explanation", [])
        if explanation:
            st.subheader("🔍 Factores de la señal (XAI)")
            factors = sorted(explanation, key=lambda x: x.get("weight", 0), reverse=True)
            labels = [f.get("factor", "") for f in factors]
            weights = [
                f.get("weight", 0) if f.get("direction") == "bullish" else -f.get("weight", 0)
                for f in factors
            ]
            colors = ["#26a69a" if w > 0 else "#ef5350" for w in weights]

            fig = go.Figure(go.Bar(
                x=weights, y=labels,
                orientation="h",
                marker_color=colors,
            ))
            fig.update_layout(
                title="Contribución de cada factor (SHAP)",
                xaxis_title="Contribución",
                template="plotly_dark",
                height=300,
            )
            st.plotly_chart(fig, use_container_width=True)

            for f in factors[:3]:
                icon = "📈" if f.get("direction") == "bullish" else "📉"
                st.markdown(f"{icon} {f.get('description', '')}")
