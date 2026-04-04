"""
Module: app/pages/signals.py
Responsibility: Active signals with XAI explanation — TRADER IA Design System v1.0
Dependencies: streamlit, plotly, pandas, requests
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

    [data-testid="stSelectbox"] > div > div {
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

    .badge-buy {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 3px;
        background: var(--green2);
        color: var(--green);
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .badge-sell {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 3px;
        background: var(--red2);
        color: var(--red);
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .badge-fill {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 3px;
        background: var(--green2);
        color: var(--green);
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 600;
    }
    .badge-reject {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 3px;
        background: var(--red2);
        color: var(--red);
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 600;
    }
    .badge-skip {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 3px;
        background: var(--amber2);
        color: var(--amber);
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 600;
    }
    .badge-pending {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 3px;
        background: var(--blue2);
        color: var(--blue);
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 600;
    }
    .badge-executed {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 3px;
        background: var(--green2);
        color: var(--green);
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 600;
    }

    .signal-table {
        width: 100%;
        border-collapse: collapse;
        font-family: var(--mono);
        font-size: 11px;
    }
    .signal-table th {
        font-family: var(--sans);
        font-size: 9px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: var(--text3);
        padding: 0 8px 8px;
        text-align: left;
        border-bottom: 1px solid var(--border);
    }
    .signal-table td {
        padding: 8px;
        color: var(--text2);
        border-top: 1px solid var(--border);
    }
    .signal-table tr:hover td {
        background: var(--bg3);
    }
    .signal-table .symbol-cell {
        color: var(--text1);
        font-weight: 600;
    }
    .signal-table .sl-cell { color: var(--red); }
    .signal-table .tp-cell { color: var(--green); }
    .signal-table .rr-cell { color: var(--amber); }

    .shap-bar-track {
        width: 100%;
        height: 6px;
        background: var(--bg3);
        border-radius: 3px;
        overflow: hidden;
        position: relative;
    }
    .shap-bar-fill-pos {
        height: 100%;
        background: var(--green);
        border-radius: 3px;
        transition: width 0.3s ease;
    }
    .shap-bar-fill-neg {
        height: 100%;
        background: var(--red);
        border-radius: 3px;
        transition: width 0.3s ease;
        margin-left: auto;
    }

    .xai-summary {
        background: var(--bg3);
        border-left: 3px solid var(--blue);
        border-radius: 6px;
        padding: 10px;
        margin-top: 12px;
    }
    .xai-summary-label {
        font-family: var(--sans);
        font-size: 10px;
        color: var(--text3);
        margin-bottom: 4px;
    }
    .xai-summary-text {
        font-family: var(--sans);
        font-size: 11px;
        color: var(--text2);
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="font-family:var(--sans);font-size:1.4rem;font-weight:600;">Signals</h1>', unsafe_allow_html=True)

_ALL_SYMBOLS = ["Todos", "BTCUSDT", "ETHUSDT", "EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US500"]

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    symbol_filter = st.selectbox("Símbolo", _ALL_SYMBOLS, label_visibility="collapsed")
with col2:
    status_filter = st.selectbox("Estado", ["Todos", "pending", "executed", "cancelled"], label_visibility="collapsed")
with col3:
    limit = st.number_input("Lim", 10, 200, 50, label_visibility="collapsed")

if st.button("↻ Actualizar", use_container_width=True):
    st.cache_data.clear()
    st.rerun()


@st.cache_data(ttl=30)
def fetch_signals(sym, sig_status, lim) -> list:
    params = {"limit": lim}
    if sym != "Todos":
        params["symbol"] = sym
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
    st.markdown(f"""
<div class="card" style="text-align:center;padding:40px;">
    <div style="font-family:var(--mono);font-size:12px;color:var(--amber);">⚠ SIN SEÑALES</div>
    <div style="font-family:var(--sans);font-size:11px;color:var(--text3);margin-top:8px;">
        Las señales se generan automáticamente cuando el pipeline está activo.
    </div>
</div>
""", unsafe_allow_html=True)
    st.stop()

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

total_signals = len(signals)
executed = sum(1 for s in signals if s.get("status") == "executed")
win_trades = sum(1 for s in signals if s.get("status") == "executed" and s.get("pnl", 0) > 0)
win_rate = (win_trades / executed * 100) if executed > 0 else 0
blocked = sum(1 for s in signals if s.get("status") in ("rejected", "skipped"))

col_m1.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Señales Hoy</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:var(--text1);margin-top:4px;">{total_signals}</div>
</div>
""", unsafe_allow_html=True)

col_m2.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Ejecutadas</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:var(--text1);margin-top:4px;">{executed}</div>
</div>
""", unsafe_allow_html=True)

wr_color = "var(--green)" if win_rate >= 50 else "var(--amber)"
col_m3.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Win Rate</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:{wr_color};margin-top:4px;">{win_rate:.0f}%</div>
    <div style="width:100%;height:2px;background:var(--bg3);border-radius:1px;margin-top:6px;">
        <div style="width:{win_rate}%;height:100%;background:{wr_color};border-radius:1px;"></div>
    </div>
</div>
""", unsafe_allow_html=True)

col_m4.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Bloqueadas</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:var(--amber);margin-top:4px;">{blocked}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

st.markdown(f'<h3 style="font-family:var(--sans);font-size:1rem;">{total_signals} Señal(es)</h3>', unsafe_allow_html=True)

table_html = """
<table class="signal-table">
    <thead>
        <tr>
            <th>Símbolo</th>
            <th>Señal</th>
            <th>Entrada</th>
            <th>SL</th>
            <th>TP</th>
            <th>R:R</th>
            <th>Confianza</th>
            <th>Estado</th>
        </tr>
    </thead>
    <tbody>
"""

for sig in signals:
    sym = sig.get("symbol", "—")
    action = sig.get("action", "HOLD")
    entry = sig.get("entry_price", 0)
    sl = sig.get("stop_loss", 0)
    tp = sig.get("take_profit", 0)
    rr = sig.get("risk_reward_ratio", 0)
    conf = sig.get("confidence", 0)
    status = sig.get("status", "pending")

    signal_badge = "badge-buy" if action == "BUY" else ("badge-sell" if action == "SELL" else "badge-hold")
    status_badge = "badge-executed" if status == "executed" else ("badge-reject" if status in ("rejected", "cancelled") else ("badge-skip" if status == "skipped" else "badge-pending"))

    table_html += f"""
        <tr>
            <td class="symbol-cell">{sym}</td>
            <td><span class="{signal_badge}">{action}</span></td>
            <td>{entry:,.2f}</td>
            <td class="sl-cell">{sl:,.2f}</td>
            <td class="tp-cell">{tp:,.2f}</td>
            <td class="rr-cell">{rr:.1f}x</td>
            <td>{conf:.0%}</td>
            <td><span class="{status_badge}">{status.upper()}</span></td>
        </tr>
    """

table_html += """
    </tbody>
</table>
"""

st.markdown(table_html, unsafe_allow_html=True)

st.markdown("---")

st.markdown('<h3 style="font-family:var(--sans);font-size:1rem;">Explicabilidad XAI — SHAP Values</h3>', unsafe_allow_html=True)

selected_signal = None
if signals:
    sel_col1, sel_col2 = st.columns([2, 1])
    with sel_col1:
        sig_options = [f"{s.get('symbol')} — {s.get('action')} ({s.get('confidence', 0):.0%})" for s in signals]
        sel_idx = st.selectbox("Señal", sig_options, label_visibility="collapsed")
        selected_signal = signals[sig_options.index(sel_idx)] if sel_idx in sig_options else None

if selected_signal:
    explanation = selected_signal.get("explanation", [])
    symbol = selected_signal.get("symbol", "—")
    action = selected_signal.get("action", "HOLD")

    st.markdown(f"""
<div style="font-family:var(--sans);font-size:11px;color:var(--text3);margin-bottom:12px;">
    Contribución de cada indicador a la señal <span class="{'badge-buy' if action == 'BUY' else 'badge-sell'}">{action}</span>
    &nbsp;·&nbsp; {symbol}
    &nbsp;·&nbsp; <span style="color:var(--blue);">TechnicalAgent</span>
    <br>(verde = pro-{action}, rojo = en contra)
</div>
""", unsafe_allow_html=True)

    if explanation:
        factors = sorted(explanation, key=lambda x: abs(x.get("weight", 0)), reverse=True)
        max_weight = max(abs(f.get("weight", 0)) for f in factors) if factors else 1

        for f in factors:
            label = f.get("factor", "—")
            weight = f.get("weight", 0)
            direction = f.get("direction", "neutral")
            val = weight if direction == "bullish" else -weight

            pct = (abs(weight) / max_weight) * 100 if max_weight > 0 else 0
            bar_color = "var(--green)" if val > 0 else "var(--red)"
            val_color = "var(--green)" if val > 0 else "var(--red)"

            if val >= 0:
                bar_html = f'<div class="shap-bar-fill-pos" style="width:{pct}%;"></div>'
            else:
                bar_html = f'<div class="shap-bar-fill-neg" style="width:{pct}%;"></div>'

            st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
    <div style="font-family:var(--mono);font-size:10px;color:var(--text2);width:100px;flex-shrink:0;">{label}</div>
    <div style="flex:1;">
        <div class="shap-bar-track">{bar_html}</div>
    </div>
    <div style="font-family:var(--mono);font-size:10px;color:{val_color};width:36px;text-align:right;font-weight:600;">{val:+.3f}</div>
</div>
""", unsafe_allow_html=True)

        summary_text = selected_signal.get("summary", "")
        if summary_text:
            st.markdown(f"""
<div class="xai-summary">
    <div class="xai-summary-label">Resumen XAI</div>
    <div class="xai-summary-text">{summary_text}</div>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div class="card" style="text-align:center;padding:20px;">
    <div style="font-family:var(--mono);font-size:11px;color:var(--text3);">Sin datos SHAP disponibles para esta señal.</div>
</div>
""", unsafe_allow_html=True)
