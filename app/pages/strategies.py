"""
Module: app/pages/strategies.py
Responsibility: Professional Strategy Management Interface
"""
from __future__ import annotations

import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_TOKEN = st.session_state.get("token", "")

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
    .stExpander { background: #12121a; border: 1px solid #2a2a3e; border-radius: 12px; }
    .stContainer { border: 1px solid #2a2a3e; border-radius: 12px; padding: 16px; background: #12121a; }
</style>
""", unsafe_allow_html=True)

st.title("🧠 Gestión de Estrategias")

STATUS_COLORS = {"active": "🟢", "paused": "🟡", "disabled": "🔴"}

def _get_headers() -> dict:
    return {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}

def _fetch(path: str) -> dict | None:
    try:
        r = requests.get(f"{API_URL}{path}", headers=_get_headers(), timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def _patch_status(strategy_id: str, new_status: str) -> bool:
    try:
        r = requests.patch(f"{API_URL}/strategies/{strategy_id}/status", json={"status": new_status},
                          headers=_get_headers(), timeout=5)
        return r.status_code == 200
    except Exception:
        return False

def render_strategy_card(strategy: dict) -> None:
    status = strategy.get("status", "unknown")
    icon = STATUS_COLORS.get(status, "⚪")
    with st.container(border=True):
        col1, col2, col3 = st.columns([3, 1, 2])
        with col1:
            st.markdown(f"**{icon} {strategy.get('name', strategy.get('strategy_id'))}**")
            st.caption(strategy.get("description", ""))
        with col2:
            st.markdown(f"`{status}`")
        with col3:
            sid = strategy.get("strategy_id", "")
            new_statuses = [s for s in ["active", "paused", "disabled"] if s != status]
            selected = st.selectbox("Cambiar", new_statuses, key=f"st_{sid}", label_visibility="collapsed")
            if st.button("✓", key=f"btn_{sid}"):
                if _patch_status(sid, selected):
                    st.success(f"✓ {selected}")
                    st.rerun()
                else:
                    st.error("✗")

data = _fetch("/strategies")
if not data:
    st.error("⚠️ No se pudieron cargar las estrategias.")
    st.stop()

strategies = data.get("strategies", [])
total = data.get("total", 0)
active_count = sum(1 for s in strategies if s.get("status") == "active")
paused_count = sum(1 for s in strategies if s.get("status") == "paused")

col1, col2, col3 = st.columns(3)
col1.metric("📦 Total", total)
col2.metric("🟢 Activas", active_count)
col3.metric("🟡 Pausadas", paused_count)

st.markdown("---")
st.markdown("### 📋 Estrategias Registradas")

if not strategies:
    st.info("No hay estrategias registradas.")
else:
    filter_status = st.multiselect("Filtrar", ["active", "paused", "disabled"], default=["active", "paused"])
    filtered = [s for s in strategies if s.get("status") in filter_status]
    for strategy in filtered:
        render_strategy_card(strategy)

st.markdown("---")

st.markdown("### 🔧 Crear Estrategia")
with st.form("custom_strategy_form"):
    col1, col2 = st.columns(2)
    with col1:
        strategy_id = st.text_input("ID", placeholder="mi_estrategia")
        name = st.text_input("Nombre", placeholder="Mi Estrategia")
    with col2:
        description = st.text_area("Descripción", placeholder="...", height=100)
    
    conditions_raw = st.text_area("Condiciones Entrada (JSON)", value='[{"feature": "rsi_14", "operator": "lt", "value": 30}]', height=80)
    exit_raw = st.text_area("Condiciones Salida (JSON)", value='[{"feature": "rsi_14", "operator": "gt", "value": 70}]', height=80)
    
    if st.form_submit_button("🚀 Crear"):
        import json
        try:
            conditions = json.loads(conditions_raw)
            exit_conditions = json.loads(exit_raw)
            payload = {"strategy_id": strategy_id, "name": name, "description": description, 
                      "conditions": conditions, "exit_conditions": exit_conditions}
            r = requests.post(f"{API_URL}/strategies/custom", json=payload, headers=_get_headers(), timeout=10)
            if r.status_code == 201:
                st.success("✓ Estrategia creada")
            else:
                st.error(f"Error {r.status_code}")
        except json.JSONDecodeError as e:
            st.error(f"JSON inválido: {e}")
