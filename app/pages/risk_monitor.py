"""
Module: app/pages/risk_monitor.py
Responsibility: Professional Risk Management Monitor
"""
from __future__ import annotations

import os

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
    .stButton > button {
        background: linear-gradient(135deg, #d4af37 0%, #b8960b 100%);
        color: #0a0a0f; border: none; border-radius: 8px; font-weight: 600;
    }
    .stAlert { background: #12121a; border-left: 4px solid #4169e1; border-radius: 8px; }
    .stExpander { background: #12121a; border: 1px solid #2a2a3e; border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Monitor de Riesgo")

@st.cache_data(ttl=10)
def fetch_risk_status() -> dict:
    try:
        resp = requests.get(f"{API_URL}/risk/status", headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}

status = fetch_risk_status()
ks = status.get("kill_switch", {})
active = ks.get("active", False)
color = "🔴" if active else "🟢"
st.markdown(f"### {color} Kill Switch — **{'ACTIVO' if active else 'INACTIVO'}**")

if active:
    st.error(f"**Disparado:** {ks.get('triggered_by', '—')} | **Hora:** {ks.get('triggered_at', '—')}")
    if st.button("🔓 Reiniciar (Admin)"):
        resp = requests.post(f"{API_URL}/risk/kill-switch/reset", headers=HEADERS)
        if resp.status_code == 200:
            st.success("✓ Reiniciado")
            st.cache_data.clear()
        else:
            st.error(f"Error: {resp.json().get('detail')}")
else:
    st.success("✅ Trading activo")
    if st.button("⚠️ Activar Manual"):
        resp = requests.post(f"{API_URL}/risk/kill-switch/activate", headers=HEADERS)
        if resp.status_code == 200:
            st.warning("✓ Activado")
            st.cache_data.clear()

st.markdown("---")

col1, col2, col3 = st.columns(3)
col1.metric("📉 Pérdida Diaria", f"{status.get('daily_loss_current', 0):.2%}")
col2.metric("⛔ Límite", f"{status.get('daily_loss_limit', 0):.2%}")
col3.metric("🔢 Consecutivas", str(status.get("consecutive_losses", 0)))

limits_resp = {}
try:
    resp = requests.get(f"{API_URL}/risk/limits", headers=HEADERS, timeout=5)
    if resp.status_code == 200:
        limits_resp = resp.json()
except Exception:
    pass

if limits_resp:
    st.markdown("### ⚙️ Límites")
    cols = st.columns(3)
    cols[0].metric("🎯 Riesgo/Trade", f"{limits_resp.get('MAX_RISK_PER_TRADE_PCT', 0):.1%}")
    cols[1].metric("💼 Portfolio", f"{limits_resp.get('MAX_PORTFOLIO_RISK_PCT', 0):.1%}")
    cols[2].metric("📊 DD Máx", f"{limits_resp.get('MAX_DRAWDOWN_PCT', 0):.1%}")

st.caption("⏱️ Auto-refresco cada 10s")
