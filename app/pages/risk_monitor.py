"""
Module: app/pages/risk_monitor.py
Responsibility: Kill switch status and risk limits monitor
Dependencies: streamlit, requests
"""
from __future__ import annotations

import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_TOKEN = st.session_state.get("token", "")
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

st.title("🛡️ Risk Monitor")


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

# Kill switch panel
active = ks.get("active", False)
color = "🔴" if active else "🟢"
st.subheader(f"{color} Kill Switch — {'ACTIVE' if active else 'INACTIVE'}")

if active:
    st.error(
        f"**Triggered by:** {ks.get('triggered_by', '—')}  |  **At:** {ks.get('triggered_at', '—')}"
    )
    if st.button("🔓 Reset Kill Switch (Admin only)", type="primary"):
        resp = requests.post(f"{API_URL}/risk/kill-switch/reset", headers=HEADERS)
        if resp.status_code == 200:
            st.success("Kill switch reset.")
            st.cache_data.clear()
        else:
            st.error(f"Error: {resp.json().get('detail')}")
else:
    st.success("Trading is allowed. No circuit breakers triggered.")
    if st.button("⚠️ Manual Kill Switch Activate", type="secondary"):
        resp = requests.post(f"{API_URL}/risk/kill-switch/activate", headers=HEADERS)
        if resp.status_code == 200:
            st.warning("Kill switch manually activated.")
            st.cache_data.clear()

st.markdown("---")

# Risk metrics
col1, col2, col3 = st.columns(3)
col1.metric("Daily Loss", f"{status.get('daily_loss_current', 0):.2%}", delta=None)
col2.metric("Daily Loss Limit", f"{status.get('daily_loss_limit', 0):.2%}")
col3.metric("Consecutive Losses", str(status.get("consecutive_losses", 0)))

# Risk limits
limits_resp = {}
try:
    resp = requests.get(f"{API_URL}/risk/limits", headers=HEADERS, timeout=5)
    if resp.status_code == 200:
        limits_resp = resp.json()
except Exception:
    pass

if limits_resp:
    st.subheader("⚙️ Risk Limits")
    cols = st.columns(3)
    cols[0].metric(
        "Max Risk / Trade", f"{limits_resp.get('MAX_RISK_PER_TRADE_PCT', 0):.1%}"
    )
    cols[1].metric(
        "Max Portfolio Risk", f"{limits_resp.get('MAX_PORTFOLIO_RISK_PCT', 0):.1%}"
    )
    cols[2].metric("Max Drawdown", f"{limits_resp.get('MAX_DRAWDOWN_PCT', 0):.1%}")

st.caption("Auto-refreshes every 10 seconds. F5 to force reload.")
