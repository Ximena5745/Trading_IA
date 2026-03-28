"""
Module: app/pages/backtesting.py
Responsibility: Backtesting interface with results visualization
Dependencies: streamlit, plotly, requests
"""
from __future__ import annotations

import os
import time

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_TOKEN = st.session_state.get("token", "")
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

st.title("🔁 Backtesting")

with st.form("backtest_form"):
    col1, col2 = st.columns(2)
    with col1:
        strategy_id = st.text_input("Strategy ID", value="ema_rsi_v1")
        symbol = st.selectbox("Símbolo", ["BTCUSDT", "ETHUSDT"])
    with col2:
        from_date = st.date_input("Desde")
        to_date = st.date_input("Hasta")
    walk_forward = st.checkbox("Walk-Forward", value=True)
    submitted = st.form_submit_button("▶️ Ejecutar Backtest")

if submitted:
    payload = {
        "strategy_id": strategy_id,
        "symbol": symbol,
        "from_ts": from_date.isoformat() + "T00:00:00",
        "to_ts": to_date.isoformat() + "T23:59:59",
        "walk_forward": walk_forward,
    }
    try:
        resp = requests.post(f"{API_URL}/backtest", json=payload, headers=HEADERS, timeout=10)
        if resp.status_code == 202:
            job = resp.json()
            job_id = job["job_id"]
            st.session_state["last_job_id"] = job_id
            st.success(f"Backtest enviado. Job ID: `{job_id}`")
        else:
            st.error(f"Error: {resp.json()}")
    except Exception as e:
        st.error(f"No se pudo conectar a la API: {e}")

# Poll results
if "last_job_id" in st.session_state:
    job_id = st.session_state["last_job_id"]
    with st.spinner("Esperando resultados..."):
        for _ in range(20):
            try:
                resp = requests.get(f"{API_URL}/backtest/{job_id}", headers=HEADERS, timeout=5)
                if resp.status_code == 200:
                    job_data = resp.json()
                    if job_data["status"] == "done":
                        results_resp = requests.get(f"{API_URL}/backtest/{job_id}/results", headers=HEADERS)
                        if results_resp.status_code == 200:
                            results = results_resp.json()
                            _show_results(results)  # noqa: F821 defined below
                        break
                    elif job_data["status"] == "failed":
                        st.error(f"Backtest fallido: {job_data.get('error')}")
                        break
            except Exception:
                pass
            time.sleep(1)


def _show_results(results: dict) -> None:
    st.subheader("📊 Resultados del Backtest")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Sharpe", f"{results.get('sharpe_ratio', '—')}")
    col2.metric("Sortino", f"{results.get('sortino_ratio', '—')}")
    col3.metric("Max Drawdown", f"{results.get('max_drawdown', 0):.1%}" if results.get('max_drawdown') else "—")
    col4.metric("Win Rate", f"{results.get('win_rate', 0):.1%}" if results.get('win_rate') else "—")

    col5, col6, col7 = st.columns(3)
    col5.metric("Trades", str(results.get("total_trades", 0)))
    col6.metric("Profit Factor", f"{results.get('profit_factor', '—')}")
    col7.metric("Capital Final", f"${results.get('final_capital', 0):,.2f}" if results.get('final_capital') else "—")
