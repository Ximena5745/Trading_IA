"""
Module: app/pages/market_view.py
Responsibility: Real-time OHLCV chart + indicators — TRADER IA Design System v1.0
Dependencies: streamlit, plotly, pandas, requests
"""
from __future__ import annotations

import os

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

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

    .symbol-btn {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 4px;
        font-family: var(--mono);
        font-size: 10px;
        letter-spacing: 0.5px;
        cursor: pointer;
        transition: all 0.15s ease;
        border: 1px solid var(--border);
        background: transparent;
        color: var(--text2);
    }
    .symbol-btn.active {
        border-color: var(--blue);
        background: var(--blue2);
        color: var(--blue);
    }

    .regime-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 4px;
        font-family: var(--mono);
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .regime-bull { background: var(--green2); border: 1px solid var(--green); color: var(--green); }
    .regime-bear { background: var(--red2); border: 1px solid var(--red); color: var(--red); }
    .regime-sideways { background: var(--bg3); color: var(--text2); }
    .regime-crash { background: var(--red2); border: 1px solid var(--red); color: var(--red); }

    .agent-row {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 0;
        border-bottom: 1px solid var(--border);
    }
    .agent-row:last-child { border-bottom: none; }
    .agent-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .agent-name {
        font-family: var(--sans);
        font-size: 11px;
        color: var(--text1);
        flex: 1;
    }
    .agent-score-bar {
        width: 80px;
        height: 4px;
        background: var(--bg3);
        border-radius: 2px;
        overflow: hidden;
    }
    .agent-score-fill {
        height: 100%;
        border-radius: 2px;
        transition: width 0.5s ease;
    }
    .agent-value {
        font-family: var(--mono);
        font-size: 11px;
        font-weight: 600;
        min-width: 40px;
        text-align: right;
    }

    .badge-clear {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 3px;
        background: var(--green2);
        color: var(--green);
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 600;
    }
    .badge-blocked {
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

SYMBOLS = ["BTCUSDT", "ETHUSDT", "EURUSD", "GBPUSD", "XAUUSD", "US500", "USDJPY"]

st.markdown('<h1 style="font-family:var(--sans);font-size:1.4rem;font-weight:600;">Market View</h1>', unsafe_allow_html=True)

col_sym, col_tf, col_btn = st.columns([4, 1, 1])
with col_sym:
    cols_btn = st.columns(len(SYMBOLS))
    if "selected_symbol" not in st.session_state:
        st.session_state.selected_symbol = "BTCUSDT"
    for i, sym in enumerate(SYMBOLS):
        with cols_btn[i]:
            is_active = st.session_state.selected_symbol == sym
            if st.button(sym, key=f"sym_{sym}", use_container_width=True):
                st.session_state.selected_symbol = sym
                st.cache_data.clear()

with col_tf:
    timeframe = st.selectbox("TF", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3, label_visibility="collapsed")
with col_btn:
    if st.button("↻", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

symbol = st.session_state.selected_symbol


@st.cache_data(ttl=60)
def fetch_market_data(sym: str, tf: str, limit: int = 250) -> pd.DataFrame:
    try:
        resp = requests.get(
            f"{API_URL}/market/candles/{sym}",
            params={"timeframe": tf, "limit": limit},
            headers=HEADERS,
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            if data:
                return pd.DataFrame(data)
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(ttl=60)
def fetch_features(sym: str) -> dict:
    try:
        resp = requests.get(
            f"{API_URL}/market/quote/{sym}",
            headers=HEADERS,
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


df = fetch_market_data(symbol, timeframe)
features = fetch_features(symbol)

if df.empty:
    st.markdown(f"""
<div class="card" style="text-align:center;padding:40px;">
    <div style="font-family:var(--mono);font-size:12px;color:var(--amber);">⚠ SIN DATOS — {symbol}</div>
    <div style="font-family:var(--sans);font-size:11px;color:var(--text3);margin-top:8px;">
        Verifica que la API esté corriendo en {API_URL}
    </div>
</div>
""", unsafe_allow_html=True)
    st.stop()

last_close = df["close"].iloc[-1]
prev_close = df["close"].iloc[-2] if len(df) > 1 else last_close
change_pct = ((last_close - prev_close) / prev_close) * 100
change_color = "var(--green)" if change_pct >= 0 else "var(--red)"
arrow = "▲" if change_pct >= 0 else "▼"

st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;">
    <div>
        <span style="font-family:var(--mono);font-size:15px;font-weight:600;color:var(--text1);">{symbol}</span>
        <span style="font-family:var(--mono);font-size:12px;color:var(--text3);margin-left:8px;">{timeframe} · {len(df)} velas</span>
    </div>
    <div>
        <span style="font-family:var(--mono);font-size:12px;color:{change_color};">{last_close:,.2f} {arrow} {change_pct:+.2f}%</span>
    </div>
</div>
""", unsafe_allow_html=True)

fig = make_subplots(
    rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
    row_heights=[0.6, 0.2, 0.2],
)

colors_up = ["#00d084"] * len(df)
colors_down = ["#ff4757"] * len(df)
vol_colors = [
    "rgba(0,208,132,0.4)" if c >= o else "rgba(255,71,87,0.4)"
    for c, o in zip(df["close"], df["open"])
]

fig.add_trace(
    go.Candlestick(
        x=df.get("timestamp", df.index),
        open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_fillcolor="#00d084", increasing_line_color="#00d084",
        decreasing_fillcolor="#ff4757", decreasing_line_color="#ff4757",
        name="OHLCV",
    ),
    row=1, col=1,
)

for ema_name, color, dash in [
    ("ema_9", "#3d8ef8", "solid"),
    ("ema_21", "#a78bfa", "dash"),
]:
    if ema_name in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.get("timestamp", df.index),
                y=df[ema_name],
                name=ema_name.upper(),
                line=dict(color=color, width=1.5, dash=dash),
                showlegend=False,
            ),
            row=1, col=1,
        )

fig.add_trace(
    go.Bar(
        x=df.get("timestamp", df.index),
        y=df["volume"],
        name="Volume",
        marker_color=vol_colors,
        showlegend=False,
    ),
    row=2, col=1,
)

if "rsi_14" in df.columns:
    fig.add_trace(
        go.Scatter(
            x=df.get("timestamp", df.index),
            y=df["rsi_14"],
            name="RSI",
            line=dict(color="#f5a623", width=1.5),
            fill="tozeroy",
            fillcolor="rgba(245,166,35,0.08)",
            showlegend=False,
        ),
        row=3, col=1,
    )
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(255,71,87,0.5)", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(0,208,132,0.5)", row=3, col=1)

fig.update_layout(
    height=400,
    paper_bgcolor="#151a22",
    plot_bgcolor="#151a22",
    font=dict(family="JetBrains Mono", color="#8c99b0", size=10),
    xaxis_rangeslider_visible=False,
    margin=dict(l=0, r=0, t=0, b=0),
    showlegend=False,
)

fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", row=1, col=1)
fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", row=2, col=1)
fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", row=3, col=1)
fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", row=1, col=1)
fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", row=2, col=1)
fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", row=3, col=1)

st.plotly_chart(fig, use_container_width=True)

if features or not df.empty:
    rsi_val = features.get("rsi_14", df["rsi_14"].iloc[-1] if "rsi_14" in df.columns else 50)
    macd_line = features.get("macd_line", df["macd_line"].iloc[-1] if "macd_line" in df.columns else 0)
    macd_hist = features.get("macd_histogram", df["macd_histogram"].iloc[-1] if "macd_histogram" in df.columns else 0)
    bb_upper = features.get("bb_upper", df["bb_upper"].iloc[-1] if "bb_upper" in df.columns else 0)
    bb_lower = features.get("bb_lower", df["bb_lower"].iloc[-1] if "bb_lower" in df.columns else 0)

    col_rsi, col_macd, col_bb = st.columns(3)

    with col_rsi:
        rsi_color = "var(--red)" if rsi_val > 70 else ("var(--green)" if rsi_val < 30 else "var(--amber)")
        st.markdown(f"""
<div class="card">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">RSI (14)</div>
    <div style="font-family:var(--mono);font-size:13px;font-weight:600;color:{rsi_color};margin-top:4px;">{rsi_val:.1f}</div>
    <div style="display:flex;justify-content:space-between;font-family:var(--mono);font-size:9px;color:var(--text3);margin-top:4px;">
        <span>30</span><span>70</span>
    </div>
</div>
""", unsafe_allow_html=True)

    with col_macd:
        macd_color = "var(--green)" if macd_hist >= 0 else "var(--red)"
        st.markdown(f"""
<div class="card">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">MACD</div>
    <div style="font-family:var(--mono);font-size:13px;font-weight:600;color:{macd_color};margin-top:4px;">{macd_line:.4f}</div>
    <div style="font-family:var(--mono);font-size:9px;color:var(--text3);margin-top:2px;">Hist: {macd_hist:.4f}</div>
</div>
""", unsafe_allow_html=True)

    with col_bb:
        st.markdown(f"""
<div class="card">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Bollinger</div>
    <div style="font-family:var(--mono);font-size:11px;color:var(--green);margin-top:4px;">Low {bb_lower:,.2f}</div>
    <div style="font-family:var(--mono);font-size:11px;color:var(--red);">Up {bb_upper:,.2f}</div>
</div>
""", unsafe_allow_html=True)

col_agents, col_consensus = st.columns([2, 1])

with col_agents:
    st.markdown('<h3 style="font-family:var(--sans);font-size:1rem;">Agentes IA</h3>', unsafe_allow_html=True)

    regime = features.get("regime", "BULL TRENDING")
    regime_class = "regime-bull" if "BULL" in regime else ("regime-bear" if "BEAR" in regime else ("regime-crash" if "CRASH" in regime else "regime-sideways"))

    st.markdown(f'<span class="regime-badge {regime_class}">{regime}</span>', unsafe_allow_html=True)

    agents = [
        {"name": "TechnicalAgent", "color": "var(--blue)", "score": features.get("technical_score", 0.3)},
        {"name": "RegimeAgent", "color": "var(--purple)", "score": features.get("regime_score", 0.5)},
        {"name": "MicrostructureAgent", "color": "var(--amber)", "score": features.get("micro_score", 0.1)},
    ]

    for agent in agents:
        score = agent["score"]
        pct = max(0, min(100, (score + 1) * 50))
        score_color = "var(--green)" if score > 0 else "var(--red)"
        st.markdown(f"""
<div class="agent-row">
    <div class="agent-dot" style="background:{agent['color']};"></div>
    <div class="agent-name">{agent['name']}</div>
    <div class="agent-score-bar">
        <div class="agent-score-fill" style="width:{pct}%;background:{agent['color']};"></div>
    </div>
    <div class="agent-value" style="color:{score_color};">{score:+.2f}</div>
</div>
""", unsafe_allow_html=True)

    fund_status = features.get("fundamental_status", "CLEAR")
    fund_badge = "badge-clear" if fund_status == "CLEAR" else "badge-blocked"
    st.markdown(f"""
<div class="agent-row">
    <div class="agent-dot" style="background:var(--text3);"></div>
    <div class="agent-name">FundamentalAgent</div>
    <span class="{fund_badge}">{fund_status}</span>
</div>
""", unsafe_allow_html=True)

with col_consensus:
    consensus_score = features.get("consensus_score", 0.45)
    signal = "BUY" if consensus_score > 0.1 else ("SELL" if consensus_score < -0.1 else "HOLD")
    signal_badge = "badge-buy" if signal == "BUY" else ("badge-sell" if signal == "SELL" else "badge-hold")

    gauge_pct = max(0, min(100, (consensus_score + 1) * 50))
    gauge_color = "var(--green)" if signal == "BUY" else ("var(--red)" if signal == "SELL" else "var(--text3)")

    circumference = 2 * 3.14159 * 45
    offset = circumference * (1 - gauge_pct / 100)

    st.markdown(f"""
<div class="card" style="text-align:center;">
    <svg width="120" height="120" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r="45" fill="none" stroke="var(--bg3)" stroke-width="10"/>
        <circle cx="60" cy="60" r="45" fill="none" stroke="{gauge_color}" stroke-width="10"
            stroke-dasharray="{circumference}" stroke-dashoffset="{offset}"
            stroke-linecap="round" transform="rotate(-90 60 60)"
            style="transition:stroke-dashoffset 0.5s ease;"/>
        <text x="60" y="55" text-anchor="middle" fill="var(--text1)" font-family="JetBrains Mono" font-size="20" font-weight="600">{consensus_score:+.2f}</text>
        <text x="60" y="72" text-anchor="middle" fill="var(--text3)" font-family="JetBrains Mono" font-size="9">CONSENSUS</text>
    </svg>
    <div style="margin-top:8px;">
        <span class="{signal_badge}">{signal}</span>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px;background:var(--bg3);border-radius:6px;padding:8px;">
        <div style="font-family:var(--mono);font-size:11px;color:var(--red);">SL {features.get('sl', '—'):,.2f}</div>
        <div style="font-family:var(--mono);font-size:11px;color:var(--green);">TP {features.get('tp', '—'):,.2f}</div>
    </div>
</div>
""", unsafe_allow_html=True)
