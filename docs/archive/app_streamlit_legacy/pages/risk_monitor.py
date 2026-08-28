"""
Module: app/pages/risk_monitor.py
Responsibility: Professional Risk Management Monitor — TRADER IA Design System v1.0
Dependencies: streamlit, plotly, requests
"""
from __future__ import annotations

import os

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

    .progress-bar {
        width: 100%;
        height: 4px;
        background: var(--bg3);
        border-radius: 2px;
        overflow: hidden;
        margin-top: 6px;
    }
    .progress-fill {
        height: 100%;
        border-radius: 2px;
        transition: width 0.3s ease;
    }

    .kill-switch-active {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .kill-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }

    .trigger-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid var(--border);
    }
    .trigger-row:last-child { border-bottom: none; }
    .trigger-label {
        font-family: var(--sans);
        font-size: 11px;
        color: var(--text2);
    }
    .trigger-status {
        font-family: var(--mono);
        font-size: 11px;
        font-weight: 600;
    }

    .limits-table {
        width: 100%;
        border-collapse: collapse;
        font-family: var(--mono);
        font-size: 11px;
    }
    .limits-table th {
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
    .limits-table td {
        padding: 8px;
        color: var(--text2);
        border-top: 1px solid var(--border);
    }

    .badge-ok {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 3px;
        background: var(--green2);
        color: var(--green);
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 600;
    }
    .badge-watch {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 3px;
        background: var(--amber2);
        color: var(--amber);
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 600;
    }
    .badge-danger {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 3px;
        background: var(--red2);
        color: var(--red);
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="font-family:var(--sans);font-size:1.4rem;font-weight:600;">Risk Monitor</h1>', unsafe_allow_html=True)


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
ks_active = ks.get("active", False)

col_ks, col_donut = st.columns([2, 1])

with col_ks:
    if ks_active:
        st.markdown(f"""
<div class="card">
    <div class="kill-switch-active">
        <div class="kill-dot" style="background:var(--red);"></div>
        <div style="font-family:var(--mono);font-size:13px;font-weight:600;color:var(--red);">ACTIVO</div>
    </div>
    <div style="font-family:var(--sans);font-size:11px;color:var(--text3);margin-top:8px;">
        Todas las órdenes están bloqueadas.
        <br>Disparado por: <span style="color:var(--text2);font-family:var(--mono);">{ks.get('triggered_by', '—')}</span>
        &nbsp;·&nbsp; {ks.get('triggered_at', '—')}
    </div>
</div>
""", unsafe_allow_html=True)
        if st.button("🔓 Reiniciar Kill Switch (Admin)", use_container_width=True):
            resp = requests.post(f"{API_URL}/risk/kill-switch/reset", headers=HEADERS)
            if resp.status_code == 200:
                st.success("Reiniciado correctamente")
                st.cache_data.clear()
            else:
                st.error(f"Error: {resp.json().get('detail', 'Unknown')}")
    else:
        st.markdown(f"""
<div class="card">
    <div class="kill-switch-active">
        <div class="kill-dot" style="background:var(--green);"></div>
        <div style="font-family:var(--mono);font-size:13px;font-weight:600;color:var(--green);">INACTIVO</div>
    </div>
    <div style="font-family:var(--sans);font-size:11px;color:var(--text3);margin-top:8px;">
        Sistema operando normalmente. Trading activo.
    </div>
</div>
""", unsafe_allow_html=True)
        if st.button("⚠️ Activar Kill Switch Manual", use_container_width=True):
            resp = requests.post(f"{API_URL}/risk/kill-switch/activate", headers=HEADERS)
            if resp.status_code == 200:
                st.warning("Kill Switch activado manualmente")
                st.cache_data.clear()
            else:
                st.error(f"Error: {resp.json().get('detail', 'Unknown')}")

    triggers = ks.get("triggers", {})
    if triggers:
        st.markdown('<h3 style="font-family:var(--sans);font-size:0.95rem;margin-top:12px;">Triggers</h3>', unsafe_allow_html=True)
        for name, t_status in triggers.items():
            ok = t_status.get("ok", True) if isinstance(t_status, dict) else True
            status_color = "var(--green)" if ok else "var(--red)"
            status_text = "OK" if ok else "TRIGGERED"
            st.markdown(f"""
<div class="trigger-row">
    <span class="trigger-label">{name}</span>
    <span class="trigger-status" style="color:{status_color};">{status_text}</span>
</div>
""", unsafe_allow_html=True)

with col_donut:
    exposure = status.get("exposure_by_symbol", {})
    total_exposure = status.get("total_exposure_pct", 0)

    labels = []
    values = []
    colors_donut = []
    symbol_colors = {
        "BTCUSDT": "rgba(0,208,132,0.8)",
        "ETHUSDT": "rgba(0,208,132,0.6)",
        "EURUSD": "rgba(255,71,87,0.8)",
        "GBPUSD": "rgba(255,71,87,0.6)",
        "XAUUSD": "rgba(245,166,35,0.8)",
        "US500": "rgba(61,142,248,0.8)",
        "USDJPY": "rgba(167,139,250,0.8)",
    }

    if isinstance(exposure, dict) and exposure:
        for sym, pct in exposure.items():
            labels.append(sym)
            values.append(pct * 100)
            colors_donut.append(symbol_colors.get(sym, "rgba(255,255,255,0.3)"))

    free = max(0, 100 - total_exposure * 100)
    if free > 0:
        labels.append("Libre")
        values.append(free)
        colors_donut.append("rgba(28,35,48,0.9)")

    if values:
        fig_donut = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.72,
                    marker_colors=colors_donut,
                    textinfo="label+percent",
                    textfont=dict(family="Syne", size=9, color="#8c99b0"),
                    hoverinfo="label+value",
                    pull=[0.02] * len(labels),
                )
            ]
        )
        fig_donut.update_layout(
            height=220,
            paper_bgcolor="#151a22",
            plot_bgcolor="#151a22",
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
        )
        st.plotly_chart(fig_donut, use_container_width=True)

st.markdown("---")

daily_loss = status.get("daily_loss_current", 0)
daily_limit = status.get("daily_loss_limit", 0.10)
drawdown = status.get("drawdown_current", 0)
drawdown_limit = status.get("max_drawdown_pct", 0.20)
consecutive = status.get("consecutive_losses", 0)
consecutive_limit = 7
total_exposure_pct = status.get("total_exposure_pct", 0)
exposure_limit = status.get("max_portfolio_risk_pct", 0.15)


def get_bar_color(current, limit):
    pct = current / limit if limit > 0 else 0
    if pct < 0.5:
        return "var(--green)"
    elif pct < 0.8:
        return "var(--amber)"
    else:
        return "var(--red)"


def get_bar_width(current, limit):
    return min((current / limit) * 100, 100) if limit > 0 else 0


col_r1, col_r2, col_r3, col_r4 = st.columns(4)

exp_color = get_bar_color(total_exposure_pct, exposure_limit)
exp_w = get_bar_width(total_exposure_pct, exposure_limit)
col_r1.markdown(f"""
<div class="card">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Exposición Total</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:{exp_color};margin-top:4px;">{total_exposure_pct*100:.1f}%</div>
    <div class="progress-bar"><div class="progress-fill" style="width:{exp_w}%;background:{exp_color};"></div></div>
    <div style="font-family:var(--mono);font-size:10px;color:var(--text3);margin-top:4px;">Límite: {exposure_limit*100:.0f}%</div>
</div>
""", unsafe_allow_html=True)

dl_color = get_bar_color(daily_loss, daily_limit)
dl_w = get_bar_width(daily_loss, daily_limit)
col_r2.markdown(f"""
<div class="card">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Pérdida Diaria</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:{dl_color};margin-top:4px;">{daily_loss*100:.1f}%</div>
    <div class="progress-bar"><div class="progress-fill" style="width:{dl_w}%;background:{dl_color};"></div></div>
    <div style="font-family:var(--mono);font-size:10px;color:var(--text3);margin-top:4px;">Límite: {daily_limit*100:.0f}%</div>
</div>
""", unsafe_allow_html=True)

dd_color = get_bar_color(drawdown, drawdown_limit)
dd_w = get_bar_width(drawdown, drawdown_limit)
col_r3.markdown(f"""
<div class="card">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Drawdown</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:{dd_color};margin-top:4px;">{drawdown*100:.1f}%</div>
    <div class="progress-bar"><div class="progress-fill" style="width:{dd_w}%;background:{dd_color};"></div></div>
    <div style="font-family:var(--mono);font-size:10px;color:var(--text3);margin-top:4px;">Límite: {drawdown_limit*100:.0f}%</div>
</div>
""", unsafe_allow_html=True)

cons_color = "var(--red)" if consecutive >= 5 else ("var(--amber)" if consecutive >= 3 else "var(--green)")
cons_w = (consecutive / consecutive_limit) * 100
col_r4.markdown(f"""
<div class="card">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Consecutivas</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:{cons_color};margin-top:4px;">{consecutive}</div>
    <div class="progress-bar"><div class="progress-fill" style="width:{cons_w}%;background:{cons_color};"></div></div>
    <div style="font-family:var(--mono);font-size:10px;color:var(--text3);margin-top:4px;">Límite: {consecutive_limit}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

st.markdown('<h3 style="font-family:var(--sans);font-size:1rem;">Hard Limits</h3>', unsafe_allow_html=True)

limits_resp = {}
try:
    resp = requests.get(f"{API_URL}/risk/limits", headers=HEADERS, timeout=5)
    if resp.status_code == 200:
        limits_resp = resp.json()
except Exception:
    pass

hard_limits = [
    ("Riesgo por Trade", limits_resp.get("MAX_RISK_PER_TRADE_PCT", 0.02), total_exposure_pct, "%"),
    ("Exposición Portfolio", limits_resp.get("MAX_PORTFOLIO_RISK_PCT", 0.15), total_exposure_pct, "%"),
    ("Pérdida Diaria", limits_resp.get("MAX_DAILY_LOSS_PCT", 0.10), daily_loss, "%"),
    ("Drawdown Máximo", limits_resp.get("MAX_DRAWDOWN_PCT", 0.20), drawdown, "%"),
    ("Consecutivas", 7, consecutive, ""),
]

table_html = """
<table class="limits-table">
    <thead>
        <tr>
            <th>Límite</th>
            <th>Configurado</th>
            <th>Actual</th>
            <th>Uso %</th>
            <th>Estado</th>
        </tr>
    </thead>
    <tbody>
"""

for name, configured, actual, unit in hard_limits:
    if unit == "%":
        configured_str = f"{configured*100:.1f}%"
        actual_str = f"{actual*100:.1f}%"
        usage = (actual / configured * 100) if configured > 0 else 0
    else:
        configured_str = str(configured)
        actual_str = str(actual)
        usage = (actual / configured * 100) if configured > 0 else 0

    usage = min(usage, 100)
    bar_color = "var(--green)" if usage < 50 else ("var(--amber)" if usage < 80 else "var(--red)")
    badge = "badge-ok" if usage < 50 else ("badge-watch" if usage < 80 else "badge-danger")
    badge_text = "OK" if usage < 50 else ("WATCH" if usage < 80 else "DANGER")

    table_html += f"""
        <tr>
            <td style="color:var(--text1);font-weight:500;">{name}</td>
            <td>{configured_str}</td>
            <td>{actual_str}</td>
            <td>
                <div style="display:flex;align-items:center;gap:6px;">
                    <div style="width:80px;height:4px;background:var(--bg3);border-radius:2px;overflow:hidden;">
                        <div style="width:{usage}%;height:100%;background:{bar_color};border-radius:2px;"></div>
                    </div>
                    <span style="font-family:var(--mono);font-size:10px;color:var(--text3);">{usage:.0f}%</span>
                </div>
            </td>
            <td><span class="{badge}">{badge_text}</span></td>
        </tr>
    """

table_html += """
    </tbody>
</table>
"""

st.markdown(table_html, unsafe_allow_html=True)

st.caption("Auto-refresco cada 10s")
