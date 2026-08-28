"""
Module: app/pages/simulator.py
Responsibility: Professional Historical Simulator — TRADER IA Design System v1.0
Dependencies: streamlit, plotly, pandas, requests
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
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Syne:wght@400;500;600;700');

    :root {
        --bg0:    #0a0d11;
        --bg1:    #0f1318;
        --bg2:    #151a22;
        --bg3:    #1c2330;
        --bg4:    #232c3b;
        --border:  rgba(255,255,255,0.07);
        --border2: rgba(255,255,255,0.13);
        --text1: #e8edf5;
        --text2: #8c99b0;
        --text3: #4d5a70;
        --green:  #00d084;
        --green2: rgba(0,208,132,0.12);
        --red:    #ff4757;
        --red2:   rgba(255,71,87,0.12);
        --blue:   #3d8ef8;
        --blue2:  rgba(61,142,248,0.12);
        --amber:  #f5a623;
        --amber2: rgba(245,166,35,0.12);
        --purple: #a78bfa;
        --mono: 'JetBrains Mono', monospace;
        --sans: 'Syne', sans-serif;
    }

    .stApp {
        background: var(--bg0);
        font-family: var(--sans);
        color: var(--text1);
    }

    #MainMenu, footer, header { visibility: hidden; }

    h1, h2, h3, h4, h5, h6 {
        font-family: var(--sans);
        font-weight: 600;
        color: var(--text1) !important;
    }
    h1 { font-size: 1.4rem; }
    h2 { font-size: 1.1rem; }
    h3 { font-size: 1rem; }

    [data-testid="stMetric"] {
        background: var(--bg2);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 14px 16px;
    }
    [data-testid="stMetric"] label {
        color: var(--text3) !important;
        font-family: var(--sans);
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--text1) !important;
        font-family: var(--mono);
        font-weight: 600;
        font-size: 22px;
    }

    .stButton > button {
        background: transparent;
        border: 1px solid var(--border);
        border-radius: 8px;
        color: var(--text2);
        font-family: var(--sans);
        font-weight: 500;
        font-size: 12px;
        padding: 8px 16px;
        transition: all 0.15s ease;
    }
    .stButton > button:hover {
        border-color: var(--blue);
        color: var(--blue);
        background: var(--blue2);
    }

    [data-testid="stSelectbox"] > div > div,
    [data-testid="stNumberInput"] > div > div {
        background: var(--bg4);
        border: 1px solid var(--border);
        border-radius: 6px;
        color: var(--text1);
        font-family: var(--mono);
        font-size: 11px;
    }

    [data-testid="stDataFrame"] {
        background: var(--bg2);
        border: 1px solid var(--border);
        border-radius: 10px;
    }

    [data-testid="stExpander"] {
        background: var(--bg2);
        border: 1px solid var(--border);
        border-radius: 10px;
    }

    .stAlert {
        background: var(--bg2);
        border-left: 3px solid var(--blue);
        border-radius: 6px;
    }

    hr { border-color: var(--border); }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg0); }
    ::-webkit-scrollbar-thumb { background: var(--bg3); border-radius: 3px; }

    .card {
        background: var(--bg2);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 16px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="font-family:var(--sans);font-size:1.4rem;font-weight:600;">Simulator</h1>', unsafe_allow_html=True)


def _fetch_strategies() -> list[dict]:
    try:
        r = requests.get(f"{API_URL}/strategies", headers=HEADERS, timeout=5)
        if r.status_code == 200:
            return r.json().get("strategies", [])
    except Exception:
        pass
    return []


def _fetch_symbols() -> list[str]:
    try:
        r = requests.get(f"{API_URL}/market/symbols", headers=HEADERS, timeout=5)
        if r.status_code == 200:
            return r.json().get("symbols", [])
    except Exception:
        pass
    return ["BTCUSDT", "ETHUSDT", "EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US500"]


strategies = _fetch_strategies()
symbols = _fetch_symbols()

col1, col2 = st.columns(2)
with col1:
    selected_strategy = st.selectbox(
        "Estrategia",
        [s.get("strategy_id", s.get("id")) for s in strategies] if strategies else ["ema_rsi_v1"],
        label_visibility="collapsed",
    )
with col2:
    selected_symbol = st.selectbox(
        "Símbolo",
        symbols[:8] if symbols else ["BTCUSDT"],
        label_visibility="collapsed",
    )

col3, col4 = st.columns(2)
with col3:
    start_date = st.date_input("Desde", datetime.now() - timedelta(days=90), label_visibility="collapsed")
with col4:
    end_date = st.date_input("Hasta", datetime.now(), label_visibility="collapsed")

initial_capital = st.number_input("Capital Inicial", value=10000.0, step=1000.0, label_visibility="collapsed")

if st.button("Ejecutar Simulación", use_container_width=True):
    payload = {
        "strategy_id": selected_strategy,
        "symbol": selected_symbol,
        "from_ts": start_date.isoformat(),
        "to_ts": end_date.isoformat(),
        "initial_capital": initial_capital,
    }
    try:
        resp = requests.post(f"{API_URL}/simulation/run", json=payload, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            results = resp.json()

            final_capital = results.get("final_capital", 0)
            return_pct = results.get("return_pct", 0)
            win_rate = results.get("win_rate", 0)
            total_trades = results.get("total_trades", 0)

            ret_color = "var(--green)" if return_pct >= 0 else "var(--red)"
            ret_sign = "+" if return_pct >= 0 else ""

            col1, col2, col3, col4 = st.columns(4)
            col1.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Capital Final</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:var(--text1);margin-top:4px;">${final_capital:,.2f}</div>
</div>
""", unsafe_allow_html=True)
            col2.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Retorno</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:{ret_color};margin-top:4px;">{ret_sign}{return_pct:.2f}%</div>
</div>
""", unsafe_allow_html=True)
            col3.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Win Rate</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:var(--green);margin-top:4px;">{win_rate*100:.1f}%</div>
</div>
""", unsafe_allow_html=True)
            col4.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Trades</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:var(--text1);margin-top:4px;">{total_trades}</div>
</div>
""", unsafe_allow_html=True)

            if "equity_curve" in results:
                df = pd.DataFrame(results["equity_curve"])
                if not df.empty:
                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(
                            x=df.get("timestamp", df.index),
                            y=df.get("capital", df.iloc[:, 0]),
                            mode="lines",
                            name="Capital",
                            line=dict(color="#3d8ef8", width=2),
                            fill="tozeroy",
                            fillcolor="rgba(61,142,248,0.15)",
                        )
                    )
                    fig.update_layout(
                        height=220,
                        paper_bgcolor="#151a22",
                        plot_bgcolor="#151a22",
                        font=dict(family="JetBrains Mono", color="#8c99b0", size=10),
                        margin=dict(l=50, r=10, t=0, b=30),
                        showlegend=False,
                    )
                    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)")
                    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", tickprefix="$")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"Error: {resp.text}")
    except Exception as e:
        st.error(f"Error: {e}")

st.markdown(f"""
<div class="card" style="text-align:center;padding:16px;">
    <div style="font-family:var(--mono);font-size:11px;color:var(--text3);">
        Analiza qué habría pasado con diferentes estrategias en el pasado.
    </div>
</div>
""", unsafe_allow_html=True)
