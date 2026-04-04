"""
Module: app/pages/portfolio.py
Responsibility: Professional Portfolio Dashboard — TRADER IA Design System v1.0
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

    .position-row {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 0;
        border-bottom: 1px solid var(--border);
    }
    .position-row:last-child { border-bottom: none; }
    .position-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .position-symbol {
        font-family: var(--sans);
        font-size: 11px;
        color: var(--text1);
        flex: 1;
    }
    .position-qty {
        font-family: var(--mono);
        font-size: 10px;
        color: var(--text3);
    }
    .position-pnl {
        font-family: var(--mono);
        font-size: 11px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="font-family:var(--sans);font-size:1.4rem;font-weight:600;">Portfolio</h1>', unsafe_allow_html=True)


def _fetch(path: str) -> dict | list | None:
    try:
        r = requests.get(f"{API_URL}{path}", headers=HEADERS, timeout=5)
        if r.status_code == 200:
            return r.json()
        st.warning(f"API {r.status_code}")
    except Exception as exc:
        st.error(f"Error: {exc}")
    return None


portfolio = _fetch("/portfolio")

if portfolio:
    total_capital = portfolio.get("total_capital", 0)
    daily_pnl = portfolio.get("daily_pnl", 0)
    daily_pnl_pct = portfolio.get("daily_pnl_pct", 0)
    drawdown = portfolio.get("drawdown_current", 0)
    positions = portfolio.get("positions", {})
    num_positions = len(positions) if isinstance(positions, dict) else 0

    pnl_color = "var(--green)" if daily_pnl >= 0 else "var(--red)"
    pnl_sign = "+" if daily_pnl >= 0 else ""

    col1, col2, col3, col4 = st.columns(4)

    col1.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Equity Total</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:var(--text1);margin-top:4px;">${total_capital:,.2f}</div>
</div>
""", unsafe_allow_html=True)

    col2.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">P&L Hoy</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:{pnl_color};margin-top:4px;">{pnl_sign}${daily_pnl:,.2f}</div>
    <div style="font-family:var(--mono);font-size:11px;color:{pnl_color};">{pnl_sign}{daily_pnl_pct*100:.2f}%</div>
</div>
""", unsafe_allow_html=True)

    sharpe = portfolio.get("sharpe_ratio", 0)
    sharpe_pct = min(sharpe / 3.0 * 100, 100)
    col3.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Sharpe Ratio</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:var(--blue);margin-top:4px;">{sharpe:.2f}</div>
    <div style="width:100%;height:2px;background:var(--bg3);border-radius:1px;margin-top:6px;">
        <div style="width:{sharpe_pct}%;height:100%;background:var(--blue);border-radius:1px;"></div>
    </div>
</div>
""", unsafe_allow_html=True)

    dd_pct = min(drawdown / 0.20 * 100, 100)
    dd_color = "var(--amber)"
    col4.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Max Drawdown</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:{dd_color};margin-top:4px;">{drawdown*100:.2f}%</div>
    <div style="width:100%;height:2px;background:var(--bg3);border-radius:1px;margin-top:6px;">
        <div style="width:{dd_pct}%;height:100%;background:{dd_color};border-radius:1px;"></div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

history = _fetch("/portfolio/history?limit=500")
if history:
    snapshots = history.get("snapshots", []) if isinstance(history, dict) else []
    if snapshots:
        df_eq = pd.DataFrame(snapshots)
        ts_col = "captured_at" if "captured_at" in df_eq.columns else "timestamp"
        if ts_col in df_eq.columns:
            df_eq[ts_col] = pd.to_datetime(df_eq[ts_col])

            cap_col = "capital_total" if "capital_total" in df_eq.columns else "total_capital"
            if cap_col not in df_eq.columns:
                cap_col = df_eq.columns[-1]

            fig_eq = go.Figure()
            fig_eq.add_trace(
                go.Scatter(
                    x=df_eq[ts_col],
                    y=df_eq[cap_col],
                    mode="lines+markers",
                    name="Equity",
                    line=dict(color="#3d8ef8", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(61,142,248,0.15)",
                    marker=dict(size=3, color="#3d8ef8"),
                )
            )

            sortino = portfolio.get("sortino_ratio", 0) if portfolio else 0
            profit_factor = portfolio.get("profit_factor", 0) if portfolio else 0

            fig_eq.update_layout(
                height=220,
                paper_bgcolor="#151a22",
                plot_bgcolor="#151a22",
                font=dict(family="JetBrains Mono", color="#8c99b0", size=10),
                margin=dict(l=50, r=10, t=30, b=30),
                showlegend=False,
            )
            fig_eq.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)")
            fig_eq.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", tickprefix="$")

            st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
    <div style="font-family:var(--sans);font-size:1rem;font-weight:600;">Equity Curve</div>
    <div style="display:flex;gap:16px;">
        <span style="font-family:var(--mono);font-size:11px;color:var(--text3);">Sortino: <span style="color:var(--green);">{sortino:.2f}</span></span>
        <span style="font-family:var(--mono);font-size:11px;color:var(--text3);">Profit Factor: <span style="color:var(--green);">{profit_factor:.2f}</span></span>
    </div>
</div>
""", unsafe_allow_html=True)
            st.plotly_chart(fig_eq, use_container_width=True)

st.markdown("---")

col_pos, col_pnl = st.columns(2)

with col_pos:
    st.markdown('<h3 style="font-family:var(--sans);font-size:1rem;">Posiciones Abiertas</h3>', unsafe_allow_html=True)
    positions_data = _fetch("/portfolio/positions")
    if positions_data and isinstance(positions_data, dict) and positions_data.get("positions"):
        total_open_pnl = 0
        for pos in positions_data["positions"]:
            sym = pos.get("symbol", "—")
            qty = pos.get("size", pos.get("quantity", 0))
            pnl = pos.get("unrealized_pnl", 0)
            total_open_pnl += pnl
            dot_color = "var(--green)" if pnl >= 0 else "var(--red)"
            pnl_color = "var(--green)" if pnl >= 0 else "var(--red)"

            st.markdown(f"""
<div class="position-row">
    <div class="position-dot" style="background:{dot_color};"></div>
    <div class="position-symbol">{sym}</div>
    <div class="position-qty">{qty}</div>
    <div class="position-pnl" style="color:{pnl_color};">${pnl:+,.2f}</div>
</div>
""", unsafe_allow_html=True)

        total_pnl_color = "var(--green)" if total_open_pnl >= 0 else "var(--red)"
        st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;padding-top:8px;border-top:1px solid var(--border);margin-top:4px;">
    <span style="font-family:var(--sans);font-size:11px;color:var(--text3);">P&L Abierto</span>
    <span style="font-family:var(--mono);font-size:11px;font-weight:600;color:{total_pnl_color};">${total_open_pnl:+,.2f}</span>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div class="card" style="text-align:center;padding:20px;">
    <div style="font-family:var(--mono);font-size:11px;color:var(--text3);">Sin posiciones abiertas</div>
</div>
""", unsafe_allow_html=True)

with col_pnl:
    st.markdown('<h3 style="font-family:var(--sans);font-size:1rem;">P&L por Símbolo</h3>', unsafe_allow_html=True)
    perf = _fetch("/portfolio/performance")
    if perf and isinstance(perf, dict) and perf.get("strategies"):
        strategies = [s for s in perf["strategies"] if s.get("total_trades", 0) > 0]
        if strategies:
            df_perf = pd.DataFrame(strategies)
            if "strategy_id" in df_perf.columns and "total_pnl" in df_perf.columns:
                fig_pnl = go.Figure()
                colors_pnl = ["#00d084" if v >= 0 else "#ff4757" for v in df_perf["total_pnl"]]
                fig_pnl.add_trace(
                    go.Bar(
                        x=df_perf["total_pnl"],
                        y=df_perf["strategy_id"],
                        orientation="h",
                        marker_color=colors_pnl,
                        marker_opacity=0.7,
                    )
                )
                fig_pnl.update_layout(
                    height=180,
                    paper_bgcolor="#151a22",
                    plot_bgcolor="#151a22",
                    font=dict(family="JetBrains Mono", color="#8c99b0", size=10),
                    margin=dict(l=80, r=10, t=0, b=20),
                    showlegend=False,
                    xaxis=dict(tickprefix="$", showgrid=True, gridcolor="rgba(255,255,255,0.04)"),
                    yaxis=dict(showgrid=False),
                )
                st.plotly_chart(fig_pnl, use_container_width=True)
            else:
                st.markdown(f"""
<div class="card" style="text-align:center;padding:20px;">
    <div style="font-family:var(--mono);font-size:11px;color:var(--text3);">Sin datos de P&L por símbolo</div>
</div>
""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
<div class="card" style="text-align:center;padding:20px;">
    <div style="font-family:var(--mono);font-size:11px;color:var(--text3);">Sin trades completados</div>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div class="card" style="text-align:center;padding:20px;">
    <div style="font-family:var(--mono);font-size:11px;color:var(--text3);">Sin datos de rendimiento</div>
</div>
""", unsafe_allow_html=True)
