"""
Module: app/pages/portfolio.py
Responsibility: Professional Portfolio Dashboard with P&L and Performance
"""
from __future__ import annotations

import os

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_TOKEN = st.session_state.get("token", "")
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}

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
    .stDataFrame { border: 1px solid #2a2a3e; border-radius: 12px; }
    .stButton > button {
        background: linear-gradient(135deg, #d4af37 0%, #b8960b 100%);
        color: #0a0a0f; border: none; border-radius: 8px; font-weight: 600;
    }
    .stAlert { background: #12121a; border-left: 4px solid #4169e1; border-radius: 8px; }
    .stExpander { background: #12121a; border: 1px solid #2a2a3e; border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

st.title("💼 Portafolio")

def _fetch(path: str) -> dict | list | None:
    try:
        r = requests.get(f"{API_URL}{path}", headers=HEADERS, timeout=5)
        if r.status_code == 200:
            return r.json()
        st.warning(f"API {r.status_code}")
    except Exception as exc:
        st.error(f"Error: {exc}")
    return None

def render_equity_curve(snapshots: list[dict]) -> None:
    if not snapshots:
        st.info("Sin historial.")
        return
    df = pd.DataFrame(snapshots)
    df["timestamp"] = pd.to_datetime(df.get("captured_at", df.get("timestamp")))
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df.get("capital_total", df.get("total_capital", [])),
                            mode="lines", name="Capital", line=dict(color="#d4af37", width=2),
                            fill="tozeroy", fillcolor="rgba(212,175,55,0.1)"))
    fig.update_layout(title="📈 Curva de Capital", template="plotly_dark", height=320,
                    paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f", font=dict(color="#fff"),
                    margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)

def render_drawdown_chart(snapshots: list[dict]) -> None:
    if not snapshots:
        return
    df = pd.DataFrame(snapshots)
    df["timestamp"] = pd.to_datetime(df.get("captured_at", df.get("timestamp")))
    col = "max_drawdown_pct" if "max_drawdown_pct" in df.columns else "drawdown_current"
    if col not in df.columns:
        return
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["timestamp"], y=df[col] * -100, name="Drawdown", marker_color="#4169e1"))
    fig.update_layout(title="📉 Drawdown", template="plotly_dark", height=240,
                    paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f", font=dict(color="#fff"),
                    margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)

portfolio = _fetch("/portfolio")
if portfolio:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Total", f"${portfolio.get('total_capital', 0):,.2f}")
    col2.metric("📈 P&G", f"{portfolio.get('daily_pnl_pct', 0)*100:.2f}%", delta=f"${portfolio.get('daily_pnl', 0):.2f}")
    col3.metric("📉 DD", f"{portfolio.get('drawdown_current', 0)*100:.2f}%")
    col4.metric("🔢 Posiciones", len(portfolio.get("positions", {})))

st.markdown("---")

history = _fetch("/portfolio/history?limit=500")
if history:
    snapshots = history.get("snapshots", [])
    render_equity_curve(snapshots)
    render_drawdown_chart(snapshots)

st.markdown("---")

st.markdown("### 📋 Posiciones Abiertas")
positions_data = _fetch("/portfolio/positions")
if positions_data and positions_data.get("positions"):
    df_pos = pd.DataFrame(positions_data["positions"])
    cols = [c for c in ["symbol", "side", "size", "entry_price", "current_price", "unrealized_pnl"] if c in df_pos.columns]
    st.dataframe(df_pos[cols] if cols else df_pos, use_container_width=True)
else:
    st.info("Sin posiciones abiertas.")

st.markdown("---")

st.markdown("### 🏆 Rendimiento")
perf = _fetch("/portfolio/performance")
if perf and perf.get("strategies"):
    strategies = [s for s in perf["strategies"] if s.get("total_trades", 0) > 0]
    if strategies:
        df_perf = pd.DataFrame(strategies)
        st.dataframe(df_perf, use_container_width=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_perf["strategy_id"], y=df_perf.get("win_rate", [])*100,
                           name="Win Rate", marker_color="#d4af37"))
        fig.update_layout(title="📊 Win Rate %", template="plotly_dark", height=260,
                        paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f", font=dict(color="#fff"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin trades completados.")
else:
    st.info("Sin datos de estrategias.")
