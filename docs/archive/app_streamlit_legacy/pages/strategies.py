"""
Module: app/pages/strategies.py
Responsibility: Professional Strategy Management Interface — TRADER IA Design System v1.0
Dependencies: streamlit, requests
"""
from __future__ import annotations

import json
import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_TOKEN = st.session_state.get("token", "")

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

    .badge-active {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 3px;
        background: var(--green2);
        color: var(--green);
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 600;
    }
    .badge-paused {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 3px;
        background: var(--amber2);
        color: var(--amber);
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 600;
    }
    .badge-disabled {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 3px;
        background: var(--bg3);
        color: var(--text3);
        font-family: var(--mono);
        font-size: 10px;
        font-weight: 600;
    }

    .strategy-card {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 14px 16px;
        border-bottom: 1px solid var(--border);
    }
    .strategy-card:last-child { border-bottom: none; }
    .strategy-info { flex: 1; }
    .strategy-name {
        font-family: var(--sans);
        font-size: 12px;
        font-weight: 600;
        color: var(--text1);
    }
    .strategy-desc {
        font-family: var(--sans);
        font-size: 11px;
        color: var(--text3);
        margin-top: 2px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="font-family:var(--sans);font-size:1.4rem;font-weight:600;">Strategies</h1>', unsafe_allow_html=True)


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
        r = requests.patch(
            f"{API_URL}/strategies/{strategy_id}/status",
            json={"status": new_status},
            headers=_get_headers(),
            timeout=5,
        )
        return r.status_code == 200
    except Exception:
        return False


data = _fetch("/strategies")
if not data:
    st.markdown(f"""
<div class="card" style="text-align:center;padding:40px;">
    <div style="font-family:var(--mono);font-size:12px;color:var(--amber);">⚠ SIN DATOS</div>
    <div style="font-family:var(--sans);font-size:11px;color:var(--text3);margin-top:8px;">
        No se pudieron cargar las estrategias. Verifica la API.
    </div>
</div>
""", unsafe_allow_html=True)
    st.stop()

strategies = data.get("strategies", [])
total = data.get("total", 0)
active_count = sum(1 for s in strategies if s.get("status") == "active")
paused_count = sum(1 for s in strategies if s.get("status") == "paused")

col1, col2, col3 = st.columns(3)
col1.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Total</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:var(--text1);margin-top:4px;">{total}</div>
</div>
""", unsafe_allow_html=True)
col2.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Activas</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:var(--green);margin-top:4px;">{active_count}</div>
</div>
""", unsafe_allow_html=True)
col3.markdown(f"""
<div class="card" style="text-align:center;">
    <div style="font-family:var(--sans);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.8px;">Pausadas</div>
    <div style="font-family:var(--mono);font-size:22px;font-weight:600;color:var(--amber);margin-top:4px;">{paused_count}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

st.markdown('<h3 style="font-family:var(--sans);font-size:1rem;">Estrategias Registradas</h3>', unsafe_allow_html=True)

if not strategies:
    st.markdown(f"""
<div class="card" style="text-align:center;padding:20px;">
    <div style="font-family:var(--mono);font-size:11px;color:var(--text3);">No hay estrategias registradas.</div>
</div>
""", unsafe_allow_html=True)
else:
    filter_status = st.multiselect("Filtrar", ["active", "paused", "disabled"], default=["active", "paused"])
    filtered = [s for s in strategies if s.get("status") in filter_status]

    for strategy in filtered:
        status = strategy.get("status", "unknown")
        badge_class = f"badge-{status}" if status in ("active", "paused", "disabled") else "badge-disabled"
        name = strategy.get("name", strategy.get("strategy_id", "—"))
        desc = strategy.get("description", "")
        sid = strategy.get("strategy_id", "")

        st.markdown(f"""
<div class="strategy-card">
    <div class="strategy-info">
        <div class="strategy-name">{name}</div>
        <div class="strategy-desc">{desc}</div>
    </div>
    <span class="{badge_class}">{status.upper()}</span>
</div>
""", unsafe_allow_html=True)

        new_statuses = [s for s in ["active", "paused", "disabled"] if s != status]
        col_act1, col_act2, col_act3 = st.columns([2, 2, 1])
        with col_act1:
            selected = st.selectbox("Cambiar estado", new_statuses, key=f"st_{sid}", label_visibility="collapsed")
        with col_act2:
            pass
        with col_act3:
            if st.button("✓", key=f"btn_{sid}"):
                if _patch_status(sid, selected):
                    st.success(f"Cambiado a {selected}")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Error al cambiar estado")

st.markdown("---")

st.markdown('<h3 style="font-family:var(--sans);font-size:1rem;">Crear Estrategia</h3>', unsafe_allow_html=True)

with st.form("custom_strategy_form"):
    col1, col2 = st.columns(2)
    with col1:
        strategy_id = st.text_input("ID", placeholder="mi_estrategia")
        name = st.text_input("Nombre", placeholder="Mi Estrategia")
    with col2:
        description = st.text_area("Descripción", placeholder="...", height=100)

    conditions_raw = st.text_area(
        "Condiciones Entrada (JSON)",
        value='[{"feature": "rsi_14", "operator": "lt", "value": 30}]',
        height=80,
    )
    exit_raw = st.text_area(
        "Condiciones Salida (JSON)",
        value='[{"feature": "rsi_14", "operator": "gt", "value": 70}]',
        height=80,
    )

    if st.form_submit_button("Crear Estrategia"):
        try:
            conditions = json.loads(conditions_raw)
            exit_conditions = json.loads(exit_raw)
            payload = {
                "strategy_id": strategy_id,
                "name": name,
                "description": description,
                "conditions": conditions,
                "exit_conditions": exit_conditions,
            }
            r = requests.post(
                f"{API_URL}/strategies/custom",
                json=payload,
                headers=_get_headers(),
                timeout=10,
            )
            if r.status_code == 201:
                st.success("Estrategia creada correctamente")
            else:
                st.error(f"Error {r.status_code}")
        except json.JSONDecodeError as e:
            st.error(f"JSON inválido: {e}")
