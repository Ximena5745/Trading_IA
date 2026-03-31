"""
Module: app/dashboard.py
Responsibility: Streamlit dashboard entry point - Professional Trading Interface
Dependencies: streamlit
"""
import streamlit as st

st.set_page_config(
    page_title="TRADER AI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .stApp {
        background: linear-gradient(180deg, #0a0a0f 0%, #0d0d14 50%, #0f0f1a 100%);
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0a0f 0%, #12121a 100%);
        border-right: 1px solid #1a1a2e;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: #ffffff;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        color: #d4af37 !important;
        letter-spacing: -0.02em;
    }
    
    h1 { font-size: 2.2rem; }
    h2 { font-size: 1.6rem; }
    h3 { font-size: 1.3rem; }
    
    /* Metrics */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #12121a 0%, #1a1a2e 100%);
        border: 1px solid #2a2a3e;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    
    div[data-testid="stMetric"] label {
        color: #8888a0 !important;
        font-size: 0.85rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 700;
        font-size: 1.5rem;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #d4af37 0%, #b8960b 100%);
        color: #0a0a0f;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 12px 24px;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #ffd700 0%, #d4af37 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(212, 175, 55, 0.3);
    }
    
    /* Select boxes */
    .stSelectbox > div > div {
        background: #12121a;
        border: 1px solid #2a2a3e;
        border-radius: 8px;
        color: #ffffff;
    }
    
    /* DataFrames */
    [data-testid="stDataFrame"] {
        border: 1px solid #2a2a3e;
        border-radius: 12px;
        overflow: hidden;
    }
    
    /* Expanders */
    .stExpander {
        background: #12121a;
        border: 1px solid #2a2a3e;
        border-radius: 12px;
    }
    
    .stExpander > summary {
        color: #d4af37;
    }
    
    /* Alerts */
    .stAlert {
        background: #12121a;
        border-left: 4px solid #4169e1;
        border-radius: 8px;
    }
    
    /* Dividers */
    hr {
        border-color: #2a2a3e;
    }
    
    /* Input fields */
    .stTextInput > div > div {
        background: #12121a;
        border: 1px solid #2a2a3e;
        border-radius: 8px;
        color: #ffffff;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px 8px 0px 0px;
        color: #8888a0;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #d4af37 0%, #b8960b 100%);
        color: #0a0a0f;
    }
    
    /* Custom cards */
    .custom-card {
        background: linear-gradient(135deg, #12121a 0%, #1a1a2e 100%);
        border: 1px solid #2a2a3e;
        border-radius: 16px;
        padding: 24px;
        margin: 12px 0;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #0a0a0f;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #2a2a3e;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #3a3a4e;
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<div style="text-align: center; padding: 20px 0;">
    <h2 style="color: #d4af37 !important; margin-bottom: 4px;">📈 TRADER AI</h2>
    <p style="color: #8888a0; font-size: 0.85rem;">Algorithmic Trading Platform</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

menu_items = [
    {"icon": "📊", "label": "Vista de Mercado", "file": "pages/market_view.py"},
    {"icon": "⚡", "label": "Señales", "file": "pages/signals.py"},
    {"icon": "🧠", "label": "Estrategias", "file": "pages/strategies.py"},
    {"icon": "💼", "label": "Portafolio", "file": "pages/portfolio.py"},
    {"icon": "🔁", "label": "Backtesting", "file": "pages/backtesting.py"},
    {"icon": "🎮", "label": "Simulador", "file": "pages/simulator.py"},
    {"icon": "🛡️", "label": "Riesgo", "file": "pages/risk_monitor.py"},
]

for item in menu_items:
    st.sidebar.page_link(item["file"], label=f"{item['icon']} {item['label']}")

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="text-align: center; color: #5a5a70; font-size: 0.75rem;">
    <p>Version 2.0.0</p>
    <p>Trading Mode: <span style="color: #26a69a;">PAPER</span></p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align: center; padding: 40px 20px;">
    <h1 style="font-size: 3rem; margin-bottom: 8px;">📈 TRADER AI</h1>
    <p style="color: #8888a0; font-size: 1.2rem;">Plataforma de Trading Algorítmico con Inteligencia Artificial</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Modo", "PAPER", delta=None)
with col2:
    st.metric("Estrategias", "2")
with col3:
    st.metric("P&G Diario", "$0.00")
with col4:
    st.metric("Kill Switch", "OFF")

st.markdown("---")

col_info1, col_info2 = st.columns([2, 1])
with col_info1:
    st.markdown("""
    <div class="custom-card">
        <h3 style="margin-bottom: 16px;">🚀 Bienvenido a TRADER AI</h3>
        <p style="color: #aaa; line-height: 1.8;">
            Plataforma profesional de trading algorítmico con análisis de mercado en tiempo real,
            generación de señales con explicaciones XAI, gestión de riesgo y backtesting.
        </p>
        <div style="display: flex; gap: 12px; margin-top: 20px; flex-wrap: wrap;">
            <span style="background: #1a1a2e; padding: 8px 16px; border-radius: 20px; font-size: 0.85rem;">📊 Análisis Técnico</span>
            <span style="background: #1a1a2e; padding: 8px 16px; border-radius: 20px; font-size: 0.85rem;">⚡ Señales IA</span>
            <span style="background: #1a1a2e; padding: 8px 16px; border-radius: 20px; font-size: 0.85rem;">🛡️ Gestión de Riesgo</span>
            <span style="background: #1a1a2e; padding: 8px 16px; border-radius: 20px; font-size: 0.85rem;">🔁 Backtesting</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_info2:
    st.markdown("""
    <div class="custom-card">
        <h4 style="color: #d4af37 !important; margin-bottom: 12px;">⚡ Acciones Rápidas</h4>
        <p style="color: #8888a0; font-size: 0.9rem; margin-bottom: 16px;">
            Navega usando el menú lateral para acceder a las diferentes funcionalidades.
        </p>
    </div>
    """, unsafe_allow_html=True)

with st.expander("ℹ️ Acerca de TRADER AI"):
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
