"""
Module: app/pages/strategies.py
Responsibility: Streamlit strategy management — list, status control, custom builder
"""

from __future__ import annotations

import requests
import streamlit as st

API_BASE = "http://localhost:8000"

STATUS_COLORS = {
    "active": "🟢",
    "paused": "🟡",
    "disabled": "🔴",
}


def _get_headers() -> dict:
    token = st.session_state.get("access_token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _fetch(path: str) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}{path}", headers=_get_headers(), timeout=5)
        if r.status_code == 200:
            return r.json()
        st.warning(f"API {r.status_code}: {r.text[:120]}")
    except Exception as exc:
        st.error(str(exc))
    return None


def _patch_status(strategy_id: str, new_status: str) -> bool:
    try:
        r = requests.patch(
            f"{API_BASE}/strategies/{strategy_id}/status",
            json={"status": new_status},
            headers=_get_headers(),
            timeout=5,
        )
        return r.status_code == 200
    except Exception:
        return False


def render_strategy_card(strategy: dict) -> None:
    status = strategy.get("status", "unknown")
    icon = STATUS_COLORS.get(status, "⚪")
    with st.container(border=True):
        col1, col2, col3 = st.columns([3, 1, 2])
        with col1:
            st.markdown(
                f"**{icon} {strategy.get('name', strategy.get('strategy_id'))}**"
            )
            st.caption(strategy.get("description", ""))
        with col2:
            st.markdown(f"`{status}`")
        with col3:
            sid = strategy.get("strategy_id", "")
            new_statuses = [s for s in ["active", "paused", "disabled"] if s != status]
            selected = st.selectbox(
                "Change to",
                new_statuses,
                key=f"status_sel_{sid}",
                label_visibility="collapsed",
            )
            if st.button("Update", key=f"btn_status_{sid}"):
                if _patch_status(sid, selected):
                    st.success(f"Status updated to **{selected}**")
                    st.rerun()
                else:
                    st.error("Update failed")


def render_custom_builder() -> None:
    st.subheader("🔧 Custom Strategy Builder")
    st.markdown("Build a strategy from JSON conditions (admin only).")

    with st.form("custom_strategy_form"):
        strategy_id = st.text_input("Strategy ID", placeholder="my_custom_strategy")
        name = st.text_input("Name", placeholder="My Custom Strategy")
        description = st.text_area("Description", placeholder="Optional description...")

        st.markdown("**Entry Conditions** (JSON array):")
        conditions_raw = st.text_area(
            "conditions",
            value='[{"feature": "rsi_14", "operator": "lt", "value": 30}]',
            height=120,
            label_visibility="collapsed",
        )

        st.markdown("**Exit Conditions** (JSON array):")
        exit_raw = st.text_area(
            "exit_conditions",
            value='[{"feature": "rsi_14", "operator": "gt", "value": 70}]',
            height=120,
            label_visibility="collapsed",
        )

        submitted = st.form_submit_button("🚀 Create Strategy")

    if submitted:
        import json

        try:
            conditions = json.loads(conditions_raw)
            exit_conditions = json.loads(exit_raw)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
            return

        payload = {
            "strategy_id": strategy_id,
            "name": name,
            "description": description,
            "conditions": conditions,
            "exit_conditions": exit_conditions,
        }

        try:
            r = requests.post(
                f"{API_BASE}/strategies/custom",
                json=payload,
                headers=_get_headers(),
                timeout=10,
            )
            if r.status_code == 201:
                st.success(f"Strategy **{name}** created successfully!")
                st.json(r.json())
            else:
                st.error(f"Error {r.status_code}: {r.text}")
        except Exception as exc:
            st.error(str(exc))


def render():
    st.title("⚙️ Strategy Management")

    # ── Active strategies summary ──────────────────────────────────────────
    data = _fetch("/strategies")
    if not data:
        st.error("Could not load strategies.")
        return

    strategies = data.get("strategies", [])
    total = data.get("total", 0)
    active_count = sum(1 for s in strategies if s.get("status") == "active")
    paused_count = sum(1 for s in strategies if s.get("status") == "paused")

    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Total Strategies", total)
    col2.metric("🟢 Active", active_count)
    col3.metric("🟡 Paused", paused_count)

    st.divider()

    # ── Strategy list ──────────────────────────────────────────────────────
    st.subheader("📋 Registered Strategies")

    if not strategies:
        st.info("No strategies registered.")
    else:
        filter_status = st.multiselect(
            "Filter by status",
            options=["active", "paused", "disabled"],
            default=["active", "paused"],
        )
        filtered = [s for s in strategies if s.get("status") in filter_status]

        for strategy in filtered:
            render_strategy_card(strategy)

    st.divider()

    # ── Custom strategy builder ────────────────────────────────────────────
    render_custom_builder()


render()
