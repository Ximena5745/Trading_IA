"""
Module: app/dashboard.py
Responsibility: Streamlit dashboard entry point — TRADER IA Design System v1.0
Dependencies: streamlit
"""
import streamlit as st

st.set_page_config(
    page_title="TRADER IA",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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
        letter-spacing: -0.01em;
    }
    h1 { font-size: 1.6rem; }
    h2 { font-size: 1.3rem; }
    h3 { font-size: 1.1rem; }

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
    [data-testid="stMetric"] [data-testid="stMetricDelta"] {
        font-family: var(--mono);
        font-size: 11px;
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

    [data-testid="stTextInput"] > div > div {
        background: var(--bg4);
        border: 1px solid var(--border);
        border-radius: 6px;
        color: var(--text1);
        font-family: var(--mono);
    }

    [data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 4px; }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        background: transparent;
        color: var(--text3);
        font-family: var(--sans);
        font-size: 11px;
        font-weight: 500;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        background: var(--bg3);
        color: var(--text1);
    }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg0); }
    ::-webkit-scrollbar-thumb { background: var(--bg3); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--bg4); }

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
    .badge-hold {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 3px;
        background: var(--bg3);
        color: var(--text3);
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.5px;
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
        letter-spacing: 0.5px;
    }
    .badge-paper {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 3px;
        background: var(--amber2);
        color: var(--amber);
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }

    .mono { font-family: var(--mono); }
    .sans { font-family: var(--sans); }
    .text1 { color: var(--text1); }
    .text2 { color: var(--text2); }
    .text3 { color: var(--text3); }
    .green { color: var(--green); }
    .red { color: var(--red); }
    .blue { color: var(--blue); }
    .amber { color: var(--amber); }
</style>
""", unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state.page = "home"

st.markdown("""
<div style="text-align: center; padding: 40px 20px;">
    <h1 style="font-family: 'JetBrains Mono', monospace; font-size: 2rem; font-weight: 600; color: #3d8ef8; letter-spacing: 2px; margin-bottom: 8px;">TRADER·IA</h1>
    <p style="color: #8c99b0; font-size: 1rem; font-family: 'Syne', sans-serif;">Plataforma de Trading Algorítmico con IA Explicable</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("""
<div class="card" style="text-align:center;">
    <div style="font-family:'Syne',sans-serif;font-size:10px;font-weight:600;color:#4d5a70;text-transform:uppercase;letter-spacing:0.8px;">MODO</div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:600;color:#f5a623;margin-top:4px;">PAPER</div>
</div>
""", unsafe_allow_html=True)
with col2:
    st.markdown("""
<div class="card" style="text-align:center;">
    <div style="font-family:'Syne',sans-serif;font-size:10px;font-weight:600;color:#4d5a70;text-transform:uppercase;letter-spacing:0.8px;">ESTRATEGIAS</div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:600;color:#e8edf5;margin-top:4px;">2</div>
</div>
""", unsafe_allow_html=True)
with col3:
    st.markdown("""
<div class="card" style="text-align:center;">
    <div style="font-family:'Syne',sans-serif;font-size:10px;font-weight:600;color:#4d5a70;text-transform:uppercase;letter-spacing:0.8px;">P&L DIARIO</div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:600;color:#e8edf5;margin-top:4px;">$0.00</div>
</div>
""", unsafe_allow_html=True)
with col4:
    st.markdown("""
<div class="card" style="text-align:center;">
    <div style="font-family:'Syne',sans-serif;font-size:10px;font-weight:600;color:#4d5a70;text-transform:uppercase;letter-spacing:0.8px;">KILL SWITCH</div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:600;color:#00d084;margin-top:4px;">OFF</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

col_info1, col_info2 = st.columns([2, 1])
with col_info1:
    st.markdown("""
<div class="card">
    <h3 style="margin-bottom:12px;font-family:'Syne',sans-serif;">Bienvenido a TRADER IA</h3>
    <p style="color:#8c99b0;line-height:1.8;font-family:'Syne',sans-serif;font-size:0.9rem;">
        Plataforma profesional de trading algorítmico con análisis de mercado en tiempo real,
        generación de señales con explicaciones XAI, gestión de riesgo y backtesting.
    </p>
    <div style="display:flex;gap:8px;margin-top:16px;flex-wrap:wrap;">
        <span class="badge-watch">Análisis Técnico</span>
        <span class="badge-watch">Señales IA</span>
        <span class="badge-watch">Gestión de Riesgo</span>
        <span class="badge-watch">Backtesting</span>
    </div>
</div>
""", unsafe_allow_html=True)

with col_info2:
    st.markdown("""
<div class="card">
    <h4 style="color:#3d8ef8;margin-bottom:12px;font-family:'Syne',sans-serif;">Acceso Rápido</h4>
    <p style="color:#8c99b0;font-size:0.85rem;margin-bottom:12px;font-family:'Syne',sans-serif;">
        Usa el menú lateral para navegar entre las páginas del dashboard.
    </p>
    <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#4d5a70;">
        v2.0.0 · Paper Trading
    </div>
</div>
""", unsafe_allow_html=True)

with st.expander("Acerca de TRADER IA"):
    st.markdown("""
| Característica | Descripción |
|---------------|-------------|
| **Versión** | 2.0.0 |
| **API** | FastAPI |
| **Dashboard** | Streamlit |
| **Base de Datos** | TimescaleDB (PostgreSQL) |
| **Caché** | Redis |
| **Modo de Ejecución** | Paper Trading |
""")
