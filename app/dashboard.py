"""
Module: app/dashboard.py
Responsibility: Streamlit MVP dashboard entry point
Dependencies: streamlit
"""
import streamlit as st

st.set_page_config(
    page_title="TRADER AI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("📈 TRADER AI")
st.sidebar.markdown("---")
st.sidebar.page_link("pages/market_view.py", label="📊 Market View", icon="📊")
st.sidebar.page_link("pages/signals.py", label="⚡ Signals", icon="⚡")
st.sidebar.page_link("pages/strategies.py", label="🧠 Strategies", icon="🧠")
st.sidebar.page_link("pages/portfolio.py", label="💼 Portfolio", icon="💼")
st.sidebar.page_link("pages/backtesting.py", label="🔁 Backtesting", icon="🔁")
st.sidebar.page_link("pages/risk_monitor.py", label="🛡️ Risk Monitor", icon="🛡️")

st.title("📈 TRADER AI — Dashboard")
st.markdown("Welcome to the **TRADER AI** algorithmic trading platform.")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Mode", "PAPER", delta=None)
with col2:
    st.metric("Active Strategies", "—")
with col3:
    st.metric("Daily P&L", "—")
with col4:
    st.metric("Kill Switch", "OFF", delta=None)

st.info("Navigate using the sidebar to explore market data, signals, and portfolio.")
