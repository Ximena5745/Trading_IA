"""
Module: app/pages/backtesting.py
Responsibility: Professional Backtesting Interface
"""
from __future__ import annotations

import os
import time

import pandas as pd
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
    .stSelectbox > div > div, .stTextInput > div > div { background: #12121a !important; border: 1px solid #2a2a3e; }
    .stButton > button {
        background: linear-gradient(135deg, #d4af37 0%, #b8960b 100%);
        color: #0a0a0f; border: none; border-radius: 8px; font-weight: 600;
    }
    .stAlert { background: #12121a; border-left: 4px solid #4169e1; border-radius: 8px; }
    .stForm { background: #12121a; border: 1px solid #2a2a3e; border-radius: 12px; padding: 20px; }
</style>
""", unsafe_allow_html=True)

st.title("🔁 Backtesting")

with st.form("backtest_form"):
    col1, col2 = st.columns(2)
    with col1:
        strategy_id = st.text_input("🆔 Estrategia", value="ema_rsi_v1")
        symbol = st.selectbox("💰 Símbolo", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "EURUSD", "GBPUSD", "USDJPY", "SPX500", "NAS100", "DE40", "XAUUSD", "USOIL"])
    with col2:
        from_date = st.date_input("📅 Desde")
        to_date = st.date_input("📅 Hasta")
    walk_forward = st.checkbox("🔄 Walk-Forward", value=True)
    submitted = st.form_submit_button("▶️ Ejecutar Backtest")

if submitted:
    payload = {"strategy_id": strategy_id, "symbol": symbol, 
               "from_ts": from_date.isoformat() + "T00:00:00", "to_ts": to_date.isoformat() + "T23:59:59",
               "walk_forward": walk_forward}
    try:
        resp = requests.post(f"{API_URL}/backtest", json=payload, headers=HEADERS, timeout=10)
        if resp.status_code == 202:
            job = resp.json()
            st.session_state["last_job_id"] = job["job_id"]
            st.success(f"✅ Job ID: `{job['job_id']}`")
        else:
            st.error(f"Error: {resp.json()}")
    except Exception as e:
        st.error(f"⚠️ {e}")

if "last_job_id" in st.session_state:
    job_id = st.session_state["last_job_id"]
    with st.spinner("⏳ Procesando..."):
        for _ in range(20):
            try:
                resp = requests.get(f"{API_URL}/backtest/{job_id}", headers=HEADERS, timeout=5)
                if resp.status_code == 200:
                    job_data = resp.json()
                    if job_data["status"] == "done":
                        results_resp = requests.get(f"{API_URL}/backtest/{job_id}/results", headers=HEADERS)
                        if results_resp.status_code == 200:
                            results = results_resp.json()
                            _show_results(results)
                        break
                    elif job_data["status"] == "failed":
                        st.error(f"❌ {job_data.get('error')}")
                        break
            except Exception:
                pass
            time.sleep(1)

def _show_results(results: dict) -> None:
    st.markdown("### 📊 Resultados")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📈 Sharpe", f"{results.get('sharpe_ratio', '—')}")
    col2.metric("📉 Sortino", f"{results.get('sortino_ratio', '—')}")
    col3.metric("🔻 DD", f"{results.get('max_drawdown', 0):.1%}" if results.get("max_drawdown") else "—")
    col4.metric("🎯 Win Rate", f"{results.get('win_rate', 0):.1%}" if results.get("win_rate") else "—")
    
    col5, col6, col7 = st.columns(3)
    col5.metric("🔢 Trades", str(results.get("total_trades", 0)))
    col6.metric("📊 PF", f"{results.get('profit_factor', '—')}")
    col7.metric("💵 Final", f"${results.get('final_capital', 0):,.2f}" if results.get("final_capital") else "—")
    
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
    st.json(results)
